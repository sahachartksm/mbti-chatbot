package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"math/rand"
	"net/http"
	"time"

	"github.com/mbti-chatbot/backend/ai"
	"github.com/mbti-chatbot/backend/db"
	"github.com/mbti-chatbot/backend/models"
	"github.com/oklog/ulid/v2"
)

const greeting = "สวัสดี! ฉันคือ AI ที่จะช่วยวิเคราะห์บุคลิกภาพ MBTI ของคุณผ่านการสนทนา " +
	"ไม่ต้องตอบแบบทดสอบนะ แค่เล่าให้ฟังแบบธรรมชาติเลย 😊 " +
	"เริ่มเลยได้เลย — วันนี้คุณเป็นยังไงบ้าง?"

// POST /api/chat/start
func (h *Handler) ChatStart(w http.ResponseWriter, r *http.Request) {
	sid := "chat_" + ulid.MustNew(
		ulid.Timestamp(time.Now()),
		ulid.Monotonic(rand.New(rand.NewSource(time.Now().UnixNano())), 0),
	).String()

	firstTurn := models.ChatTurn{
		Role:      "ai",
		Text:      greeting,
		Timestamp: time.Now().UTC(),
	}
	sess := &models.ChatSession{
		ID:        sid,
		CreatedAt: time.Now().UTC(),
		Turns:     []models.ChatTurn{firstTurn},
	}
	if err := h.Repo.CreateChatSession(r.Context(), sess); err != nil {
		writeErr(w, 500, "cannot create chat session: "+err.Error(), nil)
		return
	}
	writeJSON(w, 200, map[string]any{
		"session_id": sid,
		"greeting":   greeting,
	})
}

type chatMsgReq struct {
	SessionID string `json:"session_id"`
	Text      string `json:"text"`
}

// POST /api/chat/message
func (h *Handler) ChatMessage(w http.ResponseWriter, r *http.Request) {
	var req chatMsgReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Text == "" || req.SessionID == "" {
		writeErr(w, 400, "invalid request", nil)
		return
	}

	sess, err := h.Repo.GetChatSession(r.Context(), req.SessionID)
	if errors.Is(err, db.ErrNotFound) {
		writeErr(w, 404, "chat session not found", nil)
		return
	}
	if err != nil {
		writeErr(w, 500, err.Error(), nil)
		return
	}

	userTurn := models.ChatTurn{
		Role:      "user",
		Text:      req.Text,
		Timestamp: time.Now().UTC(),
	}

	// นับ user turns (รวม turn ใหม่ที่กำลังจะเพิ่ม)
	userTurnCount := 1
	for _, t := range sess.Turns {
		if t.Role == "user" {
			userTurnCount++
		}
	}

	// สร้าง turns list รวม turn ใหม่สำหรับส่งไป AI
	allTurns := append(sess.Turns, userTurn)
	dtos := make([]ai.ChatTurnDTO, len(allTurns))
	for i, t := range allTurns {
		dtos[i] = ai.ChatTurnDTO{Role: t.Role, Text: t.Text}
	}

	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()

	aiResp, err := h.AI.ChatAnalyze(ctx, ai.ChatAnalyzeRequest{
		SessionID:     req.SessionID,
		Turns:         dtos,
		UserTurnCount: userTurnCount,
	})
	if err != nil {
		writeErr(w, 502, "AI service error: "+err.Error(), nil)
		return
	}

	aiTurn := models.ChatTurn{
		Role:          "ai",
		Text:          aiResp.Reply,
		Timestamp:     time.Now().UTC(),
		PartialScores: aiResp.PartialScores,
	}

	// บันทึกทั้ง user turn + ai turn ลง MongoDB
	_ = h.Repo.AppendChatTurns(r.Context(), req.SessionID, []models.ChatTurn{userTurn, aiTurn})

	writeJSON(w, 200, map[string]any{
		"reply":              aiResp.Reply,
		"show_result_button": aiResp.ShowResult,
		"session_id":         req.SessionID,
		"turn_count":         userTurnCount,
	})
}

type chatResultReq struct {
	SessionID string `json:"session_id"`
}

// POST /api/chat/result
func (h *Handler) ChatResult(w http.ResponseWriter, r *http.Request) {
	var req chatResultReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.SessionID == "" {
		writeErr(w, 400, "invalid request", nil)
		return
	}

	sess, err := h.Repo.GetChatSession(r.Context(), req.SessionID)
	if errors.Is(err, db.ErrNotFound) {
		writeErr(w, 404, "chat session not found", nil)
		return
	}
	if err != nil {
		writeErr(w, 500, err.Error(), nil)
		return
	}

	dtos := make([]ai.ChatTurnDTO, len(sess.Turns))
	for i, t := range sess.Turns {
		dtos[i] = ai.ChatTurnDTO{Role: t.Role, Text: t.Text}
	}

	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()

	pred, err := h.AI.ChatFinal(ctx, ai.ChatFinalRequest{
		SessionID: req.SessionID,
		Turns:     dtos,
	})
	if err != nil {
		writeErr(w, 502, "AI service error: "+err.Error(), nil)
		return
	}

	result := &models.Result{
		SessionID:       req.SessionID,
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
	// บันทึกผลลง results collection (non-fatal)
	_ = h.Repo.SaveResult(r.Context(), result)

	writeJSON(w, 200, result)
}
