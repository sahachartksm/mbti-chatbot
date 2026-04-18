package handlers

import (
	"encoding/json"
	"errors"
	"math/rand"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/mbti-chatbot/backend/ai"
	"github.com/mbti-chatbot/backend/db"
	"github.com/mbti-chatbot/backend/models"
	"github.com/mbti-chatbot/backend/questions"
	"github.com/oklog/ulid/v2"
)

type Handler struct {
	Repo db.Repository
	AI   ai.Client
}

func New(repo db.Repository, aiClient ai.Client) *Handler {
	return &Handler{Repo: repo, AI: aiClient}
}

// ------------- Helpers -------------

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, status int, msg string, extra map[string]any) {
	body := map[string]any{"error": msg}
	for k, v := range extra {
		body[k] = v
	}
	writeJSON(w, status, body)
}

// ------------- Session endpoints -------------

type startReq struct {
	Lang string `json:"lang"`
}

// POST /api/session/start
func (h *Handler) StartSession(w http.ResponseWriter, r *http.Request) {
	var req startReq
	_ = json.NewDecoder(r.Body).Decode(&req)
	if req.Lang != "en" {
		req.Lang = "th"
	}

	sid := "sess_" + ulid.MustNew(ulid.Timestamp(time.Now()), ulid.Monotonic(rand.New(rand.NewSource(time.Now().UnixNano())), 0)).String()

	s := &models.Session{
		SessionID: sid,
		Lang:      req.Lang,
		Answers:   []models.Answer{},
		CreatedAt: time.Now().UTC(),
	}
	if err := h.Repo.CreateSession(r.Context(), s); err != nil {
		writeErr(w, 500, "cannot create session: "+err.Error(), nil)
		return
	}
	writeJSON(w, 200, map[string]any{
		"session_id": sid,
		"lang":       req.Lang,
		"questions":  questions.ToClientView(req.Lang),
		"total":      questions.Total(),
	})
}

// GET /api/session/:id
func (h *Handler) GetSession(w http.ResponseWriter, r *http.Request) {
	sid := chi.URLParam(r, "id")
	s, err := h.Repo.GetSession(r.Context(), sid)
	if errors.Is(err, db.ErrNotFound) {
		writeErr(w, 404, "session not found", nil)
		return
	}
	if err != nil {
		writeErr(w, 500, err.Error(), nil)
		return
	}
	writeJSON(w, 200, s)
}

type answerReq struct {
	QuestionID int    `json:"question_id"`
	ChoiceID   string `json:"choice_id"`
}

// POST /api/session/:id/answer
func (h *Handler) AddAnswer(w http.ResponseWriter, r *http.Request) {
	sid := chi.URLParam(r, "id")
	var req answerReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, 400, "invalid json", nil)
		return
	}
	// validate question/choice
	if req.QuestionID < 1 || req.QuestionID > questions.Total() {
		writeErr(w, 400, "invalid question_id", nil)
		return
	}
	if questions.FindChoice(req.QuestionID, req.ChoiceID) == nil {
		writeErr(w, 400, "invalid choice_id", nil)
		return
	}

	s, err := h.Repo.AddAnswer(r.Context(), sid, models.Answer{QuestionID: req.QuestionID, ChoiceID: req.ChoiceID})
	if errors.Is(err, db.ErrNotFound) {
		writeErr(w, 404, "session not found", nil)
		return
	}
	if err != nil {
		writeErr(w, 500, err.Error(), nil)
		return
	}
	writeJSON(w, 200, map[string]any{
		"ok":             true,
		"answered_count": len(s.Answers),
		"total":          questions.Total(),
	})
}
