package ai

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/mbti-chatbot/backend/models"
)

type Client interface {
	Health(ctx context.Context) error
	Predict(ctx context.Context, req PredictRequest) (*PredictResponse, error)
	ChatAnalyze(ctx context.Context, req ChatAnalyzeRequest) (*ChatAnalyzeResponse, error)
	ChatFinal(ctx context.Context, req ChatFinalRequest) (*PredictResponse, error)
}

// ── Chat request/response types ───────────────────────────────────────────────

type ChatTurnDTO struct {
	Role string `json:"role"`
	Text string `json:"text"`
}

type ChatAnalyzeRequest struct {
	SessionID     string        `json:"session_id"`
	Turns         []ChatTurnDTO `json:"turns"`
	UserTurnCount int           `json:"user_turn_count"`
}

type ChatAnalyzeResponse struct {
	Reply         string         `json:"reply"`
	PartialScores map[string]int `json:"partial_scores"`
	Confidence    float64        `json:"confidence"`
	ShowResult    bool           `json:"show_result"`
}

type ChatFinalRequest struct {
	SessionID string        `json:"session_id"`
	Turns     []ChatTurnDTO `json:"turns"`
}

type PredictRequest struct {
	Answers  []models.Answer `json:"answers"`
	FreeText string          `json:"free_text,omitempty"`
}

type PredictResponse struct {
	MBTIType        string            `json:"mbti_type"`
	Nickname        string            `json:"nickname"`
	Dimensions      models.Dimensions `json:"dimensions"`
	Confidence      float64           `json:"confidence"`
	Description     string            `json:"description"`
	Strengths       []string          `json:"strengths"`
	Weaknesses      []string          `json:"weaknesses"`
	Careers         []string          `json:"careers"`
	FamousPeople    []string          `json:"famous_people"`
	CompatibleTypes []string          `json:"compatible_types"`
}

type httpClient struct {
	baseURL string
	http    *http.Client
}

func NewClient(baseURL string) Client {
	return &httpClient{
		baseURL: baseURL,
		http:    &http.Client{Timeout: 15 * time.Second},
	}
}

func (c *httpClient) Health(ctx context.Context) error {
	req, _ := http.NewRequestWithContext(ctx, "GET", c.baseURL+"/health", nil)
	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("ai health %d", resp.StatusCode)
	}
	return nil
}

func (c *httpClient) post(ctx context.Context, path string, body any, out any) error {
	buf, err := json.Marshal(body)
	if err != nil {
		return err
	}
	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+path, bytes.NewReader(buf))
	if err != nil {
		return err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	resp, err := c.http.Do(httpReq)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return errors.New("ai error: " + string(raw))
	}
	return json.Unmarshal(raw, out)
}

func (c *httpClient) ChatAnalyze(ctx context.Context, req ChatAnalyzeRequest) (*ChatAnalyzeResponse, error) {
	var out ChatAnalyzeResponse
	if err := c.post(ctx, "/chat/analyze", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *httpClient) ChatFinal(ctx context.Context, req ChatFinalRequest) (*PredictResponse, error) {
	var out PredictResponse
	if err := c.post(ctx, "/chat/final", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *httpClient) Predict(ctx context.Context, req PredictRequest) (*PredictResponse, error) {
	var out PredictResponse
	if err := c.post(ctx, "/predict", req, &out); err != nil {
		return nil, err
	}
	return &out, nil
}
