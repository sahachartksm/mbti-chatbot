# 04 — Code Walkthrough (ไล่โค้ดทีละไฟล์)

> อ่านไฟล์นี้เพื่อเข้าใจว่า **โค้ดแต่ละส่วนทำอะไร** + ควรเริ่มแก้ตรงไหน

---

## 🟩 Backend (Go) — ไล่ตามลำดับ

### 1. `backend/main.go` — entrypoint
- Load config (env)
- Connect MongoDB (`db.NewMongo`)
- Ping AI service (`ai.NewClient` + health check)
- Register handlers
- Start HTTP server :8080
- Graceful shutdown (SIGTERM)

### 2. `backend/config/config.go` — โหลด env
- อ่าน `MONGO_URI`, `BACKEND_PORT`, `AI_SERVICE_URL`, `CORS_ORIGINS`
- ใช้ `os.Getenv` + default fallback — ไม่ต้อง lib ใหญ่

### 3. `backend/models/models.go` — data models
```go
Session { ID, Lang, Answers[], CreatedAt, Analyzed }
Answer  { QuestionID, ChoiceID }
Result  { SessionID, MBTIType, Dimensions, ... }
```
ใช้กับทั้ง JSON (API) + BSON (Mongo) — struct tag ครอบทั้ง 2

### 4. `backend/db/mongo.go` — Repository
- `type Repository interface { CreateSession, GetSession, AddAnswer, SaveResult, ... }`
- Implementation: `MongoRepo` — ห่อ `*mongo.Client`
- ทำไม interface? — **test mock ง่าย** + swap engine ได้ (Redis, Postgres)

### 5. `backend/questions/questions.go` — question bank
```go
var Questions = []Question{
  {ID:1, Text:{th: "ในงานปาร์ตี้...", en:"At a party..."}, 
   Choices: []Choice{...},
   Mapping: []Mapping{{Choice:"a", Dim:"EI", Direction:"E", Weight:1.0}, ...},
  },
  // ... 20 ข้อ
}
```
- `Mapping` = กติกา: ถ้าตอบ choice "a" ให้ +1 ฝั่ง E ของ dimension E/I
- คลุม 4 dimensions: **EI, SN, TF, JP** (แต่ละ dim 5 คำถาม)

### 6. `backend/handlers/`
- `session.go`:
  - `StartSession` — สร้าง session_id (ULID) + return questions
  - `GetSession` — คืน state
  - `AddAnswer` — validate + save
- `analyze.go`:
  - `Analyze` — load answers → call AI client → save result → return

### 7. `backend/ai/client.go` — HTTP client → Python
```go
type Client interface { Predict(ctx, answers, text) (*Prediction, error) }
```
- Use `http.Client` with timeout 10s
- JSON marshal/unmarshal

### 8. `backend/middleware/` (ถ้ามี)
- CORS
- Logging (request_id)

### ไฟล์ที่ควรแก้บ่อย
- เพิ่มคำถาม → `questions/questions.go` (+ re-train AI)
- เปลี่ยน port / env → `config/config.go`
- เพิ่ม endpoint → `handlers/` + `main.go` (router register)

---

## 🐍 AI Service (Python) — ไล่ตามลำดับ

### 1. `ai-service/app.py` — FastAPI
- `/health` — check
- `/predict` — รับ answers → call `predictor.predict` → return
- Load model + SBERT ครั้งเดียวตอน startup (global singleton)
- CORS allow Go backend

### 2. `ai-service/predictor.py` — business logic
```python
def predict(answers, free_text=None):
    # Step 1: rule-based score
    scores = rule_based_score(answers)   # {E:4, I:2, S:1, N:5, ...}
    
    # Step 2: ML validation
    features = answers_to_features(answers)
    ml_probs = model.predict_proba([features])
    
    # Step 3: (optional) text blend
    if free_text and sbert:
        text_scores = sbert_score(free_text)
        scores = blend(scores, text_scores, weight=0.3)
    
    # Step 4: pick type + confidence
    mbti = pick_type(scores)
    confidence = calculate_confidence(scores, ml_probs)
    
    return {"mbti_type": mbti, "dimensions": scores, ...}
```

### 3. `ai-service/questions_map.py` — คัดลอก mapping จาก Go
> ⚠️ ต้อง sync กับ `backend/questions/questions.go` ถ้าเพิ่มคำถาม
Format:
```python
QUESTION_MAP = {
  1: {
    "dim": "EI",
    "choices": {
      "a": ("E", 1.0),
      "b": ("I", 1.0),
      "c": ("I", 0.5),
    }
  },
  # ...
}
```

### 4. `ai-service/train.py` — train logistic regression
- เรียก `training_data_generator.generate()`
- Split train/test
- Fit `LogisticRegression` × 4
- Save `models/mbti_model.pkl`

### 5. `ai-service/data/training_data_generator.py`
- วนลูป 10000 ครั้ง: random true type → simulate answers (noise 15%) → save
- Output: array shape `(10000, 21)` = 20 answers + 1 label (16-class encoded)

### 6. `ai-service/type_info.py` — description แต่ละ type
```python
TYPE_INFO = {
  "INTJ": {
    "nickname": "The Architect",
    "description": "...",
    "strengths": [...],
    "weaknesses": [...],
    "careers": [...],
    "famous_people": [...],
    "compatible": ["ENFP", "ENTP"]
  },
  # ... 16 types
}
```

### ไฟล์ที่ควรแก้บ่อย
- เพิ่มคำถาม → `questions_map.py` + re-train
- แก้ description → `type_info.py`
- เปลี่ยน model → `train.py` + `predictor.py`

---

## 🅰️ Frontend (Angular) — ไล่ตามลำดับ

### 1. `frontend/src/main.ts` — bootstrap
```typescript
bootstrapApplication(AppComponent, appConfig);
```

### 2. `frontend/src/app/app.config.ts` — providers
- `provideRouter`, `provideHttpClient`

### 3. `frontend/src/app/app.routes.ts` — routes
```typescript
/            → ChatComponent
/result/:id  → ResultComponent
```

### 4. `frontend/src/app/services/chat.service.ts`
- `startSession(lang)` → POST
- `answer(sid, qid, choice)` → POST
- `analyze(sid, freeText?)` → POST
- ใช้ `signal` เก็บ state local + `HttpClient`

### 5. `frontend/src/app/components/chat/chat.component.ts`
- On init → call `chat.startSession('th')`
- แสดง question ปัจจุบัน (จาก signal)
- On choice → call `chat.answer()` → next question
- ตอบครบ → navigate `/result/:sid`

### 6. `frontend/src/app/components/result/result.component.ts`
- On init → call `chat.analyze(sid)` → แสดง type + dimensions
- Radar chart (ใช้ CSS เอง — ไม่ใช้ chart lib เพื่อความเบา)
- ปุ่ม "ทำใหม่" → navigate `/`

### 7. `frontend/src/styles.scss`
- Tailwind-like utility + theme สี
- Gradient background, chat bubble

### ไฟล์ที่ควรแก้บ่อย
- เพิ่ม UI feature → `components/`
- เปลี่ยน API URL → `environments/environment.ts`
- Theme → `styles.scss`

---

## 🔗 การ sync ระหว่าง service

### 🎯 จุดที่ต้องระวัง (single source of truth issues)

| Item | อยู่ที่ | ต้อง sync กับ |
|------|---------|--------------|
| Question bank | `backend/questions/questions.go` | `ai-service/questions_map.py` |
| Port | `.env` + code default | ต้องตรงกันทุกที่ |
| Question → dimension mapping | Go + Python | sync ทั้งสอง |

**Future improvement**: generate `questions_map.py` จาก Go ด้วย script หรือใช้ protobuf/JSON file ร่วม (ตอนนี้เก็บคู่กันเพื่อความชัดเจนในการเรียน)

---

## 🧪 Test quickly

```bash
# Backend
cd backend && go test ./...

# AI
cd ai-service && pytest tests/   # ถ้ามี
python -c "from predictor import predict; print(predict([{'question_id':i+1,'choice_id':'a'} for i in range(20)]))"

# Frontend
cd frontend && npm test
```

---

## 🐛 Debug tips

- **Go**: ใส่ `log.Printf` + ดูใน terminal ที่รัน `go run .`
- **Python**: `uvicorn --reload` → แก้ code = restart อัตโนมัติ
- **Angular**: Chrome DevTools + Angular extension; `ng serve` hot reload
- **Network calls**: Chrome Network tab → ดู request/response JSON
- **MongoDB**: เปิด <http://localhost:8081> (mongo-express UI)

---

👉 ต่อ: [06-troubleshooting.md](./06-troubleshooting.md) — ปัญหาที่เจอบ่อย
