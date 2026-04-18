# 01 — Architecture

## 🏛️ สถาปัตยกรรมภาพรวม

```
┌──────────────────┐
│   Browser        │
│ (Angular 17 SPA) │
└────────┬─────────┘
         │ HTTPS/HTTP, JSON REST
         ▼
┌──────────────────┐          ┌────────────────┐
│  Go API Backend  │◀─────────│   MongoDB 7    │
│   (port 8080)    │ mongo    │  (port 27017)  │
│                  │ driver   │  docker-compose│
└────────┬─────────┘          └────────────────┘
         │ HTTP
         ▼
┌──────────────────┐
│  Python FastAPI  │
│   AI Service     │
│   (port 8000)    │
│                  │
│ ┌──────────────┐ │
│ │ Logistic Reg │ │ ← เทรนด้วย synthetic data
│ └──────────────┘ │
│ ┌──────────────┐ │
│ │ SentenceBERT │ │ ← (optional) วิเคราะห์ free-text
│ └──────────────┘ │
└──────────────────┘
```

## 🔄 Data Flow: ทำแบบทดสอบ 1 รอบ

```
User → Angular:          POST /api/session/start
Angular → Go:            POST /api/session/start
Go → Mongo:              insert session {id, started_at}
Go → Angular:            {session_id, questions[20]}
Angular → User:          แสดงคำถามทีละข้อ

[loop ตอบคำถาม]
User → Angular:          เลือกคำตอบข้อ 1
Angular → Go:            POST /api/session/:id/answer {question_id, answer}
Go → Mongo:              update session.answers
Go → Angular:            {next_question | done}

[เมื่อตอบครบ]
User → Angular:          กด "ดูผลลัพธ์"
Angular → Go:            POST /api/session/:id/analyze
Go → Mongo:              load session + answers
Go → AI (HTTP):          POST /predict {answers}
AI:                      
  1) score 4 dimensions (E/I, S/N, T/F, J/P)
  2) LogReg validates
  3) (optional) text analysis via SBERT
  4) return type + scores + description
Go → Mongo:              save result
Go → Angular:            {mbti_type, dimensions, description, traits}
Angular → User:          แสดงหน้าผลลัพธ์
```

## 🧩 ส่วนประกอบแต่ละ Service

### Frontend (Angular 17 — standalone components)
- **ChatComponent** — UI ถามตอบทีละข้อ (chat-like)
- **ResultComponent** — แสดง MBTI + radar chart
- **ChatService** — เรียก backend API (HttpClient)
- ใช้ **signals** สำหรับ reactive state (Angular 17)

### Backend (Go — net/http + chi)
- `main.go` — bootstrap, DI, HTTP server
- `config/` — load env
- `db/mongo.go` — connect & repository
- `handlers/` — HTTP handlers
- `models/` — struct ของ session, answer, result
- `ai/client.go` — HTTP client → AI service
- `questions/questions.go` — question bank (20 ข้อ) พร้อม mapping

### AI Service (Python — FastAPI)
- `app.py` — FastAPI endpoints: `/predict`, `/health`
- `predictor.py` — business logic (scoring + ML)
- `train.py` — สร้าง synthetic data + train LogReg + save pkl
- `questions_map.py` — map question_id → (dimension, direction, weight)
- `data/training_data_generator.py` — simulate users → label

### MongoDB
- `sessions` — เก็บ session แต่ละ user (answers รายข้อ)
- `results` — เก็บผล MBTI + metadata เก็บเพื่อ analytics

## 🎯 เหตุผลของ design นี้

| ตัวเลือก | เหตุผล |
|---------|--------|
| **แยก AI เป็น service** | ML stack ต่างจาก Go — แยกให้ scale/deploy อิสระ + เปลี่ยน model ได้โดยไม่แตะ backend |
| **Go เป็น gateway** | เร็ว, type-safe, จัดการ DB + auth ดี — เป็น single entry point ของ frontend |
| **MongoDB** | schema-flexible ของ session/answers — เพิ่ม field ง่าย, ไม่ต้อง migration |
| **Angular Standalone + Signals** | modern (17+) — ไม่ต้อง NgModule, code สั้นลง |
| **Docker เฉพาะ Mongo** | ส่วนอื่น dev ด้วย native tool เร็ว + hot reload สะดวก |

## 🔐 การแยก Layer

```
backend/
├── main.go              ← Composition root: wire ทุกอย่าง
├── handlers/            ← HTTP layer (parse req, call services, return resp)
├── ai/                  ← AI client (HTTP)
├── db/                  ← Data layer (Mongo)
├── models/              ← Pure data structs (ไม่รู้จัก HTTP/DB)
└── questions/           ← Static data (question bank)
```
Handlers ไม่เรียก Mongo driver ตรง ๆ → ใช้ `db.Repository` interface → test ง่าย

## 📊 Concurrency

- Go: ทุก request = goroutine (net/http default)
- MongoDB driver: pool (default 100)
- AI HTTP client: timeout 10s + retry 1 ครั้ง
- Python uvicorn: workers=1 dev, หลายตัวตอน prod

## 🚀 Production considerations (ไว้อ่านเพิ่ม)

- Frontend build → static → serve ด้วย Nginx / S3 + CloudFront
- Backend → Docker image → Kubernetes / Cloud Run
- AI service → GPU node (ถ้า model ใหญ่) / CPU node (ใช้ model เล็ก — ตอนนี้คือ case นี้)
- MongoDB → Atlas managed
- ใส่ JWT auth + rate limit + HTTPS
- Observability: Prometheus + OpenTelemetry tracing

ในโปรเจคนี้เน้น **dev locally + ใช้งานได้** — production hardening ไม่ครอบคลุม

---

👉 ต่อ: [05-mbti-theory.md](./05-mbti-theory.md) แนะนำอ่านก่อน model (เพื่อเข้าใจว่าเทรนอะไร)
