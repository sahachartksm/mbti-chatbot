package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/mbti-chatbot/backend/ai"
	"github.com/mbti-chatbot/backend/db"
	"github.com/mbti-chatbot/backend/models"
	"github.com/mbti-chatbot/backend/questions"
)

type analyzeReq struct {
	FreeText string `json:"free_text,omitempty"`
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

	if len(s.Answers) < questions.Total() {
		writeErr(w, 409, "answers incomplete", map[string]any{
			"answered": len(s.Answers),
			"total":    questions.Total(),
		})
		return
	}

	// call AI
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	pred, err := h.AI.Predict(ctx, ai.PredictRequest{Answers: s.Answers, FreeText: req.FreeText})
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
