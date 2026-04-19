// Package ai — HTTP client for the Python AI service.
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

// Client — abstract AI service (test-friendly).
type Client interface {
	Health(ctx context.Context) error
	AnalyzeLLM(ctx context.Context, req AnalyzeLLMRequest) (*AnalyzeResponse, error)
}

// QA — one question/answer pair sent to the LLM.
type QA struct {
	Question string `json:"question"`
	Answer   string `json:"answer"`
}

// AnalyzeLLMRequest — payload for /analyze-llm.
type AnalyzeLLMRequest struct {
	QA   []QA   `json:"qa"`
	Lang string `json:"lang"`
}

// AnalyzeResponse — shape returned by /analyze-llm (and legacy /predict).
type AnalyzeResponse struct {
	MBTIType        string            `json:"mbti_type"`
	Nickname        string            `json:"nickname"`
	Dimensions      models.Dimensions `json:"dimensions"`
	Confidence      float64           `json:"confidence"`
	Description     string            `json:"description"`
	Analysis        string            `json:"analysis"`
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

// NewClient — construct AI service HTTP client.
// Timeout is generous because LLM inference can be slow on CPU.
func NewClient(baseURL string) Client {
	return &httpClient{
		baseURL: baseURL,
		http:    &http.Client{Timeout: 200 * time.Second},
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

// AnalyzeLLM — send free-text Q&A to AI service; receive structured MBTI.
func (c *httpClient) AnalyzeLLM(ctx context.Context, req AnalyzeLLMRequest) (*AnalyzeResponse, error) {
	buf, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/analyze-llm", bytes.NewReader(buf))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return nil, errors.New("ai error: " + string(body))
	}
	var out AnalyzeResponse
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}
