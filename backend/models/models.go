package models

import "time"

// ChatTurn — 1 turn ในการสนทนา (role: "user" | "ai")
type ChatTurn struct {
	Role          string         `json:"role"                     bson:"role"`
	Text          string         `json:"text"                     bson:"text"`
	Timestamp     time.Time      `json:"timestamp"                bson:"ts"`
	PartialScores map[string]int `json:"partial_scores,omitempty" bson:"partial_scores,omitempty"`
}

// ChatSession — session ของ FAB chat mode (เก็บใน collection "chat_sessions")
type ChatSession struct {
	ID        string     `json:"session_id" bson:"_id"`
	CreatedAt time.Time  `json:"created_at" bson:"created_at"`
	Turns     []ChatTurn `json:"turns"      bson:"turns"`
}

// Answer — คำตอบ 1 ข้อ
type Answer struct {
	QuestionID int    `json:"question_id" bson:"question_id"`
	ChoiceID   string `json:"choice_id"   bson:"choice_id"`
}

// Session — เก็บ state ของ 1 ผู้ทำแบบทดสอบ
type Session struct {
	SessionID  string    `json:"session_id"  bson:"session_id"`
	Lang       string    `json:"lang"        bson:"lang"`
	Answers    []Answer  `json:"answers"     bson:"answers"`
	CreatedAt  time.Time `json:"created_at"  bson:"created_at"`
	Analyzed   bool      `json:"analyzed"    bson:"analyzed"`
	AnalyzedAt time.Time `json:"analyzed_at,omitempty" bson:"analyzed_at,omitempty"`
}

// Dimensions — คะแนน % ของแต่ละขั้ว
type Dimensions struct {
	E int `json:"E" bson:"E"`
	I int `json:"I" bson:"I"`
	S int `json:"S" bson:"S"`
	N int `json:"N" bson:"N"`
	T int `json:"T" bson:"T"`
	F int `json:"F" bson:"F"`
	J int `json:"J" bson:"J"`
	P int `json:"P" bson:"P"`
}

// Result — ผลวิเคราะห์
type Result struct {
	SessionID       string     `json:"session_id"       bson:"session_id"`
	MBTIType        string     `json:"mbti_type"        bson:"mbti_type"`
	Nickname        string     `json:"nickname"         bson:"nickname"`
	Dimensions      Dimensions `json:"dimensions"       bson:"dimensions"`
	Confidence      float64    `json:"confidence"       bson:"confidence"`
	Description     string     `json:"description"      bson:"description"`
	Strengths       []string   `json:"strengths"        bson:"strengths"`
	Weaknesses      []string   `json:"weaknesses"       bson:"weaknesses"`
	Careers         []string   `json:"careers"          bson:"careers"`
	FamousPeople    []string   `json:"famous_people"    bson:"famous_people"`
	CompatibleTypes []string   `json:"compatible_types" bson:"compatible_types"`
	AnalyzedAt      time.Time  `json:"analyzed_at"      bson:"analyzed_at"`
}
