# 02 — AI Model: เลือกอะไร + เทรนอย่างไร

## 🎯 สรุปก่อน (TL;DR)

| ส่วน | เลือกใช้ | เหตุผล |
|------|---------|--------|
| **Primary predictor** | Rule-based scoring | MBTI เป็น questionnaire มีกติกาคำนวณตรงไปตรงมา — เร็ว, อธิบายได้, ไม่ต้อง train |
| **ML validator** | **Logistic Regression** (scikit-learn) | ตรวจสอบ/เสริม rule-based, ใช้ confidence score, light |
| **Text embedding** (ถ้าเปิดใช้) | **sentence-transformers `all-MiniLM-L6-v2`** (22MB) | เล็ก, เร็ว, รัน CPU ได้, multi-lingual |
| **ไม่ใช้ LLM ใหญ่** (GPT, Llama, ฯลฯ) | MBTI task แค่ classification 4-bit ไม่ต้องการ LLM — overkill + แพง + ช้า |

## 🤔 ทำไมไม่ใช้ LLM เลย?

ตอนแรกผมพิจารณา 3 ทาง:

### Option A: LLM API (OpenAI, Claude)
```
User answers → LLM prompt: "Given these answers, predict MBTI" → return type
```
- ✅ ง่าย เขียน prompt อย่างเดียว
- ❌ ต้อง API key + ค่าใช้จ่าย
- ❌ latency 1-3 วินาที ต่อ request
- ❌ consistency ต่ำ (อาจได้คำตอบไม่เหมือนเดิม)
- ❌ ต้องต่อ internet

### Option B: Local LLM (Llama 3 8B ผ่าน Ollama)
- ✅ offline, free
- ❌ ต้อง GPU 8GB+ หรือ CPU inference ช้ามาก
- ❌ overkill สำหรับ classification 4-bit

### Option C: Lightweight ML (เลือกใช้) ⭐
- Rule-based + LogReg + (optional) SentenceBERT
- ✅ รัน laptop ปกติ < 100ms ต่อ predict
- ✅ อธิบายได้ (interpretable)
- ✅ no external API
- ✅ train ในไม่กี่วินาที
- ❌ ไม่ฉลาดกับ free-text เท่า LLM — แต่เราใช้ embedding-based matching พอ

**→ เลือก Option C** เป็นจุดที่ engineering-optimal สำหรับ scope นี้

## 🧠 Model Architecture (รายละเอียด)

### Component 1: Rule-based Scorer (predictor.py → `score_dimensions`)
```
คำตอบข้อ 1 → (dimension=E/I, direction=E, weight=1.0)
คำตอบข้อ 2 → (dimension=S/N, direction=N, weight=0.5)
...

สะสมคะแนน 4 dimensions:
  E_score, I_score, S_score, N_score, T_score, F_score, J_score, P_score

Normalize → percentage per pole
Pick letter ของด้านที่สูงกว่า → "ENTP"
```

### Component 2: Logistic Regression Validator
**ทำไมต้องมี?** — เพื่อ cross-check rule-based และให้ **confidence score**

**Input features** (20 dim):
```
[q1_answer_idx / max_choices, q2_answer_idx / max_choices, ..., q20]
= vector ของ choice index normalize 0-1
```

**Output**: 4 ตัว classifier (one per dimension)
```
clf_EI:  P(E) ∈ [0,1]
clf_SN:  P(S) ∈ [0,1]
clf_TF:  P(T) ∈ [0,1]
clf_JP:  P(J) ∈ [0,1]
```

**Training data** — สร้างแบบ **synthetic**:
```python
# pseudo:
for _ in range(10000):
    true_type = random 16 types
    # จำลอง user ที่เป็น type นี้ตอบคำถาม (มี noise 15%)
    answers = simulate_answers(true_type, noise=0.15)
    training.append((answers, true_type))
```
ดู `ai-service/data/training_data_generator.py`

**ทำไม synthetic?** — MBTI labeled dataset ของจริงหายาก + มี bias + เราต้องการคุม distribution ให้ smooth

**Metric**:
- Accuracy per dimension ~85-92% (on held-out synthetic)
- Per full 16-type: ~55-70% (cross-check rule-based ทันที)

### Component 3: Sentence-Transformer (optional, เปิด/ปิดด้วย env `USE_SENTENCE_TRANSFORMER`)

**Model**: `sentence-transformers/all-MiniLM-L6-v2`
- 22MB, 384-dim embeddings
- รองรับหลายภาษา (แต่ดีที่สุดคืออังกฤษ)
- Download ครั้งแรกจาก HuggingFace (~80MB incl. tokenizer)

**Use case**: user เขียนเพิ่มเติมตัวเอง
```
text = "ผมชอบคิดคนเดียวก่อนตัดสินใจ และวางแผนทุกอย่าง"

embed(text) = vec_384

เทียบกับ anchor:
  anchors = {
    "I":  embed("I enjoy time alone and reflection"),
    "E":  embed("I enjoy being with people and action"),
    "S":  ...
    ...
  }

score_I = cosine(vec, anchors["I"])
score_E = cosine(vec, anchors["E"])

→ blend กับ rule-based คะแนน (weight 30% text, 70% questionnaire)
```

## 🏋️ วิธีเทรน (train.py)

### Step 1: Generate synthetic data
```bash
cd ai-service
python data/training_data_generator.py  # (เรียกใน train.py อัตโนมัติ)
```
Output: `data/synthetic_train.csv` (10,000 rows)

### Step 2: Train
```bash
python train.py
```
Output:
```
Loading synthetic data (10000, 21)...
Splitting train/test (80/20)...
Training Logistic Regression × 4 dimensions...
  Dim E/I: train_acc=0.91, test_acc=0.89
  Dim S/N: train_acc=0.88, test_acc=0.87
  Dim T/F: train_acc=0.90, test_acc=0.88
  Dim J/P: train_acc=0.86, test_acc=0.84
Saving to models/mbti_model.pkl
✓ Done
```

### Step 3: (ครั้งแรกเท่านั้น) download SBERT
ครั้งแรกที่ import `sentence_transformers` + เรียก `SentenceTransformer('all-MiniLM-L6-v2')` จะ download model จาก HuggingFace อัตโนมัติเก็บที่ `~/.cache/huggingface/`

### Step 4: ทดสอบ
```bash
python -c "from predictor import predict; print(predict([0,1,1,0,2,1,0,1,1,2,0,1,1,2,0,1,1,0,2,1]))"
```

## 🔁 Re-train เมื่อไหร่?

- เปลี่ยน question bank → **ต้อง re-train** (feature shape เปลี่ยน)
- เปลี่ยน weight mapping → **ต้อง re-train**
- ปกติ: **ไม่ต้อง re-train**

## 📊 Metrics + Validation

ดูได้จาก log ของ `train.py` + ทดสอบด้วย:
```bash
python -m pytest tests/  # ถ้าเขียน test
```
หรือ manual:
```python
from predictor import predict
# simulate: คนตอบแบบ INTJ ชัดเจน
answers = [...]  # answer ที่ map ไป I, N, T, J
result = predict(answers)
assert result["mbti_type"] == "INTJ"
```

## 🧪 Advanced: ถ้าอยาก upgrade

1. **ใช้ real MBTI dataset**: Kaggle "MBTI Personality Type" (mbti_1.csv) — แต่เป็น text ไม่ใช่ questionnaire — ต้อง fine-tune text classifier แทน
2. **Transformer fine-tuning**: BERT/DistilBERT head classification 16 ways
3. **Multi-task learning**: 1 model → 4 output heads (sharing trunk)
4. **Calibration**: Platt scaling ให้ probability น่าเชื่อถือขึ้น
5. **LLM path**: Llama 3 + few-shot prompt ใช้กรณีมี free-text เยอะ

## 🎓 Summary สำหรับตอบสัมภาษณ์

> "เลือกใช้ Rule-based + Logistic Regression เพราะ MBTI เป็น structured questionnaire ไม่ต้องการ LLM ใหญ่ — ได้ latency < 100ms, interpretable, train ฟรี, รัน CPU ได้ ส่วน free-text ใช้ sentence-transformers `all-MiniLM-L6-v2` embed + cosine เทียบ anchor แต่ละ dimension blend กับ rule-based 30/70"

---

👉 ต่อ: [03-api.md](./03-api.md) — API reference
