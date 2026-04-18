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

func (c *httpClient) Predict(ctx context.Context, req PredictRequest) (*PredictResponse, error) {
	buf, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/predict", bytes.NewReader(buf))
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
	var out PredictResponse
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}
