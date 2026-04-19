package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/mbti-chatbot/backend/ai"
	"github.com/mbti-chatbot/backend/db"
	"github.com/mbti-chatbot/backend/models"
	"github.com/mbti-chatbot/backend/questions"
)

// analyzeReq — optional payload: frontend can submit all answers atomically here
// instead of calling /answer per question. If Answers is empty, we use whatever
// was already saved in the session.
type analyzeReq struct {
	Answers []analyzeAnswer `json:"answers"`
}

type analyzeAnswer struct {
	QuestionID int    `json:"question_id"`
	Text       string `json:"text"`
}

// POST /api/session/:id/analyze
func (h *Handler) Analyze(w http.ResponseWriter, r *http.Request) {
	sid := chi.URLParam(r, "id")

	var req analyzeReq
	_ = json.NewDecoder(r.Body).Decode(&req)

	s, err := h.Repo.GetSession(r.Context(), sid)
	if errors.Is(err, db.ErrNotFound) {
		writeErr(w, 404, "session not found", nil)
		return
	}
	if err != nil {
		writeErr(w, 500, err.Error(), nil)
		return
	}

	// If the frontend sent all answers in this call, persist them first.
	if len(req.Answers) > 0 {
		for _, a := range req.Answers {
			if questions.FindByID(a.QuestionID) == nil {
				continue
			}
			ans := models.Answer{
				QuestionID: a.QuestionID,
				Question:   questions.TextFor(a.QuestionID, s.Lang),
				Text:       strings.TrimSpace(a.Text),
			}
			if _, err := h.Repo.AddAnswer(r.Context(), sid, ans); err != nil {
				writeErr(w, 500, "cannot save answer: "+err.Error(), nil)
				return
			}
		}
		// reload session with all fresh answers
		s, err = h.Repo.GetSession(r.Context(), sid)
		if err != nil {
			writeErr(w, 500, err.Error(), nil)
			return
		}
	}

	// Require at least the expected number of non-empty answers.
	nonEmpty := 0
	for _, a := range s.Answers {
		if strings.TrimSpace(a.Text) != "" {
			nonEmpty++
		}
	}
	if nonEmpty < questions.Total() {
		writeErr(w, 409, "please answer all questions", map[string]any{
			"answered": nonEmpty,
			"total":    questions.Total(),
		})
		return
	}

	// Build QA list in questionID order.
	qa := make([]ai.QA, 0, len(s.Answers))
	ordered := make(map[int]models.Answer, len(s.Answers))
	for _, a := range s.Answers {
		ordered[a.QuestionID] = a
	}
	for _, q := range questions.Questions {
		a, ok := ordered[q.ID]
		if !ok {
			continue
		}
		question := a.Question
		if question == "" {
			question = questions.TextFor(q.ID, s.Lang)
		}
		qa = append(qa, ai.QA{Question: question, Answer: a.Text})
	}

	// Call LLM. Generous timeout — first call can be slow (model warm-up).
	ctx, cancel := context.WithTimeout(r.Context(), 200*time.Second)
	defer cancel()
	pred, err := h.AI.AnalyzeLLM(ctx, ai.AnalyzeLLMRequest{QA: qa, Lang: s.Lang})
	if err != nil {
		writeErr(w, 502, "AI service error: "+err.Error(), nil)
		return
	}

	result := &models.Result{
		SessionID:       sid,
		MBTIType:        pred.MBTIType,
		Nickname:        pred.Nickname,
		Dimensions:      pred.Dimensions,
		Confidence:      pred.Confidence,
		Description:     pred.Description,
		Analysis:        pred.Analysis,
		Strengths:       pred.Strengths,
		Weaknesses:      pred.Weaknesses,
		Careers:         pred.Careers,
		FamousPeople:    pred.FamousPeople,
		CompatibleTypes: pred.CompatibleTypes,
		AnalyzedAt:      time.Now().UTC(),
	}
	if err := h.Repo.SaveResult(r.Context(), result); err != nil {
		writeErr(w, 500, "cannot save result: "+err.Error(), nil)
		return
	}
	_ = h.Repo.MarkAnalyzed(r.Context(), sid)

	writeJSON(w, 200, result)
}

// GET /api/session/:id/result
func (h *Handler) GetResult(w http.ResponseWriter, r *http.Request) {
	sid := chi.URLParam(r, "id")
	res, err := h.Repo.GetResult(r.Context(), sid)
	if errors.Is(err, db.ErrNotFound) {
		writeErr(w, 404, "result not found", nil)
		return
	}
	if err != nil {
		writeErr(w, 500, err.Error(), nil)
		return
	}
	writeJSON(w, 200, res)
}

// GET /api/stats
func (h *Handler) Stats(w http.ResponseWriter, r *http.Request) {
	dist, err := h.Repo.TypeDistribution(r.Context())
	if err != nil {
		writeErr(w, 500, err.Error(), nil)
		return
	}
	writeJSON(w, 200, map[string]any{
		"type_distribution": dist,
	})
}
