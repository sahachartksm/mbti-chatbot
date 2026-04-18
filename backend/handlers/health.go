package handlers

import (
	"net/http"
	"time"
)

var startedAt = time.Now()

// GET /api/health
func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	mongoStatus := "up"
	if err := h.Repo.Ping(r.Context()); err != nil {
		mongoStatus = "down: " + err.Error()
	}
	aiStatus := "up"
	if err := h.AI.Health(r.Context()); err != nil {
		aiStatus = "down: " + err.Error()
	}
	writeJSON(w, 200, map[string]any{
		"status":         "ok",
		"mongo":          mongoStatus,
		"ai":             aiStatus,
		"uptime_seconds": time.Since(startedAt).Seconds(),
	})
}
