# AI Service (MBTI Predictor)

FastAPI service ที่ predict MBTI type จากคำตอบ 20 ข้อ + (optional) free text

## 📦 ส่วนประกอบ

| ไฟล์ | หน้าที่ |
|---|---|
| `app.py` | FastAPI entrypoint, endpoints `/health`, `/predict` |
| `predictor.py` | Logic: rule-based + ML (LogReg) + (optional) SBERT free-text |
| `train.py` | Train 4 LogReg models (EI/SN/TF/JP) จาก synthetic data |
| `questions_map.py` | Mapping question → dimension + choice → direction/weight |
| `type_info.py` | รายละเอียด 16 MBTI types (TH) |
| `data/training_data_generator.py` | สร้าง synthetic data (default 20,000 samples) |
| `models/mbti_model.pkl` | (สร้างจาก `train.py`) bundle ของ scaler + 4 classifiers |
| `models/metrics.json` | (สร้างจาก `train.py`) รายงาน accuracy/precision/recall |

## 🚀 Quick start (Windows — cmd)

```cmd
cd ai-service

REM 1) สร้าง venv + activate
python -m venv venv
venv\Scripts\activate

REM 2) ติดตั้ง dependencies
pip install -r requirements.txt

REM 3) เทรนโมเดล (สร้าง models/mbti_model.pkl + metrics.json)
python train.py

REM 4) รัน service (port 8000)
uvicorn app:app --reload --port 8000
```

### หากไม่อยากใช้ SBERT (ประหยัดเวลา/RAM/disk ~400MB)
ตั้ง env var ก่อนรัน (หรือใน `.env` ของ backend ก็ได้):

```cmd
set USE_SENTENCE_TRANSFORMER=false
uvicorn app:app --reload --port 8000
```

หรือจะลบ `sentence-transformers` และ `torch` ออกจาก `requirements.txt` ไปเลย

## 🔌 API

### `GET /health`
```json
{
  "status": "ok",
  "model_loaded": true,
  "sbert_loaded": true,
  "sbert_enabled": true
}
```

### `POST /predict`
Request:
```json
{
  "answers": [
    { "question_id": 1, "choice_id": "a" },
    { "question_id": 2, "choice_id": "b" },
    ...
    { "question_id": 20, "choice_id": "a" }
  ],
  "free_text": "I love spending time alone thinking about big ideas."
}
```

Response:
```json
{
  "mbti_type": "INTJ",
  "nickname": "The Architect (สถาปนิก)",
  "dimensions": { "E": 20, "I": 80, "S": 30, "N": 70, "T": 75, "F": 25, "J": 65, "P": 35 },
  "confidence": 0.525,
  "description": "...",
  "strengths": ["..."],
  "weaknesses": ["..."],
  "careers": ["..."],
  "famous_people": ["..."],
  "compatible_types": ["ENFP", "ENTP"]
}
```

## 🧠 การเทรน

- **Synthetic data:** จำลองคนแต่ละ MBTI type ตอบคำถาม 20 ข้อ (noise 15% = โอกาสตอบผิดทาง)
- **โมเดล:** Logistic Regression 4 ตัว (EI, SN, TF, JP) — binary classification แต่ละ dimension
- **Scaler:** StandardScaler (shared across 4 dims)
- **Default config:** `n_samples=20000, noise=0.15, random_state=42`

### ปรับ hyperparameters

แก้ใน `train.py`:
```python
if __name__ == "__main__":
    train(n_samples=50000, noise=0.10)   # ข้อมูลมากขึ้น + noise น้อยลง = accuracy สูงขึ้น
```

### ผลที่คาดหวัง (default config)
- Per-dimension test accuracy: ~0.95+
- Overall 16-type accuracy: ~0.80+
- ดูได้ใน `models/metrics.json` หลัง train เสร็จ

## 🔄 Blend Logic ใน `predictor.py`

```
per dimension:
  rule_score     = sum of weights ตามคำตอบ
  ml_prob_first  = LogReg P(first letter)
  text_sim       = (optional) cosine sim กับ anchor ของแต่ละ pole

  blend:
    ถ้าไม่มี free_text:   70% rule + 30% ML
    ถ้ามี free_text:      56% rule + 24% ML + 20% text
```

## 🧪 Manual test

```cmd
curl -X POST http://localhost:8000/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"answers\":[{\"question_id\":1,\"choice_id\":\"a\"},...],\"free_text\":\"\"}"
```

หรือเปิด Swagger UI: http://localhost:8000/docs
