# 03 — API Reference

## 🌐 Base URL

- Go Backend (public API): `http://localhost:8080/api`
- Python AI (internal): `http://localhost:8000` — frontend ไม่เรียกตรง

---

## 📘 Backend (Go) — `/api`

### `GET /api/health`
Health check

**Response 200**
```json
{
  "status": "ok",
  "mongo": "up",
  "ai": "up",
  "uptime_seconds": 123.4
}
```

---

### `POST /api/session/start`
เริ่ม session ใหม่ + ได้ชุดคำถาม

**Request body** (optional)
```json
{ "lang": "th" }   // "th" | "en" (default "th")
```

**Response 200**
```json
{
  "session_id": "sess_01HW8...",
  "questions": [
    {
      "id": 1,
      "text": "ในงานปาร์ตี้ คุณมักจะ...",
      "choices": [
        { "id": "a", "text": "เข้าหาและพูดคุยกับคนใหม่ ๆ" },
        { "id": "b", "text": "รอให้คนอื่นเข้าหา" },
        { "id": "c", "text": "อยู่กับคนที่รู้จักเท่านั้น" }
      ]
    },
    // ... 20 ข้อ
  ]
}
```

---

### `POST /api/session/:id/answer`
บันทึกคำตอบ 1 ข้อ

**Path**: `:id` = session_id

**Request body**
```json
{
  "question_id": 1,
  "choice_id": "a"
}
```

**Response 200**
```json
{
  "ok": true,
  "answered_count": 1,
  "total": 20
}
```

**Errors**
- `404` — session not found
- `400` — invalid question/choice

---

### `POST /api/session/:id/analyze`
วิเคราะห์ผลลัพธ์ MBTI

**Request body** (optional)
```json
{
  "free_text": "ฉันชอบอยู่คนเดียว ชอบคิดเยอะก่อนพูด..."
}
```

**Response 200**
```json
{
  "session_id": "sess_01HW8...",
  "mbti_type": "INTJ",
  "nickname": "The Architect",
  "dimensions": {
    "E": 28, "I": 72,
    "S": 35, "N": 65,
    "T": 70, "F": 30,
    "J": 68, "P": 32
  },
  "confidence": 0.82,
  "description": "คุณเป็นคนเชิงกลยุทธ์...",
  "strengths": ["มองภาพรวม", "วางแผนเป็นระบบ", "มุ่งเป้า"],
  "weaknesses": ["ขาดความอบอุ่นทางอารมณ์", "ใจร้อน"],
  "careers": ["นักวิทยาศาสตร์", "สถาปนิก", "ที่ปรึกษา"],
  "famous_people": ["Elon Musk (debated)", "Nikola Tesla"],
  "compatible_types": ["ENFP", "ENTP"],
  "analyzed_at": "2025-04-18T03:42:01Z"
}
```

**Errors**
- `404` — session not found
- `409` — ตอบไม่ครบ 20 ข้อ (`{"error":"answers incomplete","answered":12,"total":20}`)
- `502` — AI service ล่ม

---

### `GET /api/session/:id`
ดู state ของ session ปัจจุบัน

**Response 200**
```json
{
  "session_id": "sess_01HW8...",
  "answered": [
    { "question_id": 1, "choice_id": "a" }
  ],
  "created_at": "...",
  "analyzed": false
}
```

---

### `GET /api/stats` (bonus)
สถิติรวม (สำหรับ admin/dev)

**Response 200**
```json
{
  "total_sessions": 1234,
  "total_analyzed": 987,
  "type_distribution": {
    "INTJ": 123, "ENTP": 98, ...
  }
}
```

---

## 🐍 AI Service (Python) — `:8000`

> frontend ไม่เรียกตรง — Go เท่านั้น (internal)

### `GET /health`
```json
{ "status": "ok", "model_loaded": true, "sbert_loaded": true }
```

### `POST /predict`
**Request**
```json
{
  "answers": [
    { "question_id": 1, "choice_id": "a" },
    { "question_id": 2, "choice_id": "b" }
  ],
  "free_text": "optional text"
}
```

**Response**
```json
{
  "mbti_type": "INTJ",
  "dimensions": { "E": 28, "I": 72, ... },
  "confidence": 0.82,
  "source": "rule+ml",
  "ml_agree": true
}
```

---

## 🧪 ทดสอบด้วย curl

```bash
# 1. Start session
curl -X POST http://localhost:8080/api/session/start \
  -H "Content-Type: application/json" \
  -d '{"lang":"th"}' | jq .

# 2. Answer (replace SESSION_ID)
SID=sess_xxx
curl -X POST http://localhost:8080/api/session/$SID/answer \
  -H "Content-Type: application/json" \
  -d '{"question_id":1,"choice_id":"a"}'

# ... (ตอบทั้ง 20 ข้อ) ...

# 3. Analyze
curl -X POST http://localhost:8080/api/session/$SID/analyze \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

หรือใช้ Swagger UI ของ AI service: <http://localhost:8000/docs>

---

## 🔒 CORS

Backend อนุญาต origin จาก env `CORS_ORIGINS` (default `http://localhost:4200`)

## 🛡️ ข้อจำกัดปัจจุบัน

- ไม่มี auth (demo use)
- ไม่มี rate limit (เพิ่มได้ด้วย middleware)
- session ไม่หมดอายุ (production ควร TTL 24h ใน MongoDB)

---

👉 ต่อ: [04-code-walkthrough.md](./04-code-walkthrough.md) — ไล่โค้ดทีละส่วน
