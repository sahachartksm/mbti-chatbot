# 07 — Training Walkthrough (เจาะลึกทุกบรรทัดของ `train.py`)

> **เขียนเมื่อ:** 2026-04-18 เวลา 16:14 (UTC+07:00)
> **Context:** pair-programming session กับ Cascade — ปรับปรุง `ai-service/` ให้พร้อมเทรนจริง
> เอกสารนี้เสริมจาก `02-ai-model.md` (ภาพรวมสูง) โดยเจาะลง flow การเทรนทีละขั้น

---

## 📋 Progress log — session นี้ทำอะไรไปบ้าง

### 2026-04-18 (รอบแรก)

| เวลา | สิ่งที่ทำ | ไฟล์ที่ถูกแตะ |
|---|---|---|
| 15:48 | ตอบคำถาม monorepo vs multi-repo | — |
| 15:50 | แนะนำคำสั่ง `git init` | — |
| 15:56 | เริ่มปรับปรุง AI service | `ai-service/` |
| ~16:00 | Rewrite `train.py` — shared train/test split, metrics (precision/recall/f1), save `metrics.json`, ลบ dead code, default `n_samples` 10k → 20k | `ai-service/train.py` |
| ~16:00 | ปรับ `predictor.py` — ใช้ `_sbert_failed` flag แทน sentinel `_sbert = False`, ใช้ `clf.classes_` defensive lookup index ของ class 0 | `ai-service/predictor.py` |
| ~16:00 | เขียน README ของ AI service (quick start, API, hyperparameters, blend logic) | `ai-service/README.md` |
| 16:05 | แก้ `requirements.txt` — ลบตัวอักษรไทย + em-dash (pip cp874 decode fail), เปลี่ยน pin เป็น `>=` เพื่อรองรับ Python 3.13 (bump `torch>=2.5.0`, `numpy>=2.1.0`, `sentence-transformers>=3.3.0`) | `ai-service/requirements.txt` |
| 16:14 | เขียนเอกสารนี้ — อธิบายการเทรน + progress log | `docs/07-training-walkthrough.md` |

### 2026-04-18 (รอบสอง — Docker unification)

| เวลา | สิ่งที่ทำ | ไฟล์ที่ถูกแตะ |
|---|---|---|
| 16:20 | แก้ `requirements.txt` encoding (cp874 decode) + bump versions support Py3.13 | `ai-service/requirements.txt` |
| 16:29 | แก้ Angular 17 `@else if (...; as r)` → `@else { @if (...; as r) }` | `frontend/.../result.component.ts` |
| 16:35 | แนะนำ `go mod tidy` (go.sum missing) | — |
| 16:41 | อธิบายบทบาท MongoDB | — |
| ~16:45 | **สร้าง Dockerfile ของ 3 services** (ai/backend/frontend) + `.dockerignore` + ขยาย `docker-compose.yml` เพิ่ม services + healthcheck + depends_on chain + shared network + named volumes สำหรับ cache | `ai-service/Dockerfile`, `backend/Dockerfile`, `frontend/Dockerfile`, `*/.dockerignore`, `docker-compose.yml` |

### Status ปัจจุบัน
- ✅ โค้ดพร้อมเทรน (ทั้งแบบ native และ docker)
- ✅ `docker compose up` รันทั้ง stack ได้ (4 services + mongo-express UI)
- ✅ Volume mount hot reload (source แก้ บน host → container เห็นทันที)
- ⏳ รอ user ทดสอบ `docker compose up --build`
- ⏳ ยังไม่มีไฟล์ `models/mbti_model.pkl` (entrypoint ของ ai container จะ train ครั้งแรกอัตโนมัติ)

---

## 🧠 การเทรนโมเดลเกิดอะไรขึ้นบ้าง — ภาพรวม

```
┌──────────────────────────────────────────────────────────────────┐
│                    python train.py                               │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  1. Generate synthetic data (20,000 rows)                        │
│     สุ่ม MBTI type → จำลองการตอบคำถาม 20 ข้อ (มี noise 15%)    │
│     → DataFrame [q1..q20, label_EI, label_SN, label_TF, label_JP]│
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  2. Train/test split 80/20 (stratify ตาม true_type)             │
│     idx_tr (16,000) + idx_te (4,000)                             │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  3. StandardScaler (fit บน train set เท่านั้น → transform ทั้งคู่)│
│     feature mean=0, std=1                                        │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  4. Train 4 Logistic Regression (1 ต่อ 1 dimension)             │
│     - clf_EI.fit(X_tr, y_EI)                                     │
│     - clf_SN.fit(X_tr, y_SN)                                     │
│     - clf_TF.fit(X_tr, y_TF)                                     │
│     - clf_JP.fit(X_tr, y_JP)                                     │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  5. Evaluate                                                     │
│     - per-dim: accuracy / precision / recall / f1                │
│     - overall 16-type accuracy (รวม 4 dims → tyoe)               │
│     - per-type accuracy (16 types × diag of confusion matrix)    │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  6. Save                                                         │
│     - models/mbti_model.pkl   (scaler + 4 classifiers via joblib)│
│     - models/metrics.json     (รายงานผล)                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔬 ขั้นที่ 1: สร้าง Synthetic Data

**ไฟล์:** `ai-service/data/training_data_generator.py`

### ทำไมต้อง synthetic?

MBTI dataset ของจริงที่ labeled ถูกต้องหายาก (MBTI test ไม่มี ground truth เพราะเป็น self-report) — เราจึง **จำลอง** โดยสมมติว่า:

> "ถ้าคนเป็น INTJ ตอบ 20 ข้อ เขาจะมีแนวโน้ม ~85% เลือกช้อยส์ที่ชี้ไปทาง I, N, T, J"

### Algorithm ของ `simulate_answer(qid, true_type, noise=0.15)`

```
given:
  qid        = 3        (ข้อ 3)
  true_type  = "INTJ"
  noise      = 0.15     (โอกาสตอบผิดทาง 15%)

step 1: หาว่าข้อนี้ทดสอบ dimension ไหน
  q = QUESTION_MAP[3] = {"dim": "EI", "choices": {"a": ("E", 1.0), "b": ("I", 1.0)}}
  dim = "EI"
  pos = DIM_IDX["EI"] = 0

step 2: หา preferred letter ของคนเป็น INTJ ใน dim นี้
  preferred_letter = "INTJ"[0] = "I"

step 3: แยก choices ที่ตรง / ตรงข้าม
  match_choices = ["b"]          # ("I", 1.0)
  other_choices = ["a"]          # ("E", 1.0)

step 4: สุ่มตามความน่าจะเป็น
  if random() < 0.15:  answer = "a"   (noise — ตรงข้าม)
  else:                answer = "b"   (ตรงกับ type)

return "b"  (85% ของเวลา)
```

### Encode เป็น feature vector

แต่ละข้อ → 1 feature (float 0..1) โดยใช้ index ของ choice ที่เลือกหารด้วย `n_choices - 1`:

```
QUESTION_CHOICES[1] = ["a", "b", "c"]   (3 choices)
ถ้าตอบ "a" → feat = 0 / 2 = 0.0
ถ้าตอบ "b" → feat = 1 / 2 = 0.5
ถ้าตอบ "c" → feat = 2 / 2 = 1.0
```

**ผลลัพธ์:** 20-dim vector ต่อคน + 4 binary labels (0 = first letter, 1 = second letter)

### Output ของ `generate(n_samples=20000)`

```
pandas DataFrame shape (20000, 25):
  q1      q2    ...  q20   label_EI  label_SN  label_TF  label_JP  true_type
  0.0     0.5        1.0   0         0         0         0         ESTJ
  0.5     1.0        0.5   1         1         1         1         INFP
  ...
```

---

## 🔬 ขั้นที่ 2: Train/Test Split

```python
idx_tr, idx_te = train_test_split(
    idx_all, test_size=0.2, random_state=42, stratify=true_types
)
```

### จุดสำคัญ

1. **แบ่ง index ครั้งเดียว** — ใช้ชุดเดียวกันทั้ง 4 dimensions → fair comparison
2. **`stratify=true_types`** — 16 types กระจายเท่า ๆ กันทั้งใน train และ test (แทนที่จะเสี่ยงว่า test จะไม่มีบาง type)
3. **`random_state=42`** — reproducible ทุกครั้ง

### ผลลัพธ์
- `idx_tr.shape = (16000,)`
- `idx_te.shape = (4000,)`

---

## 🔬 ขั้นที่ 3: StandardScaler

```python
scaler = StandardScaler()
X_tr = scaler.fit_transform(X[idx_tr])   # fit บน train เท่านั้น!
X_te = scaler.transform(X[idx_te])       # ใช้ params จาก train
```

### ทำอะไร

แต่ละ feature (`q1..q20`) จะถูก normalize เป็น:
```
z = (x - mean_train) / std_train
```
ผลลัพธ์: ทุก feature มี mean ≈ 0, std ≈ 1

### ทำไมต้อง scale?

Logistic Regression ใช้ gradient descent — features ที่ scale ไม่เท่ากัน → converge ช้า / ค่า regularization (`C`) มีผลไม่เท่ากันในแต่ละ feature

### ทำไม fit แค่ train?

ถ้า fit บน test → **data leakage** (ข้อมูล test รั่วเข้า train) → metrics ที่ได้จะ **overoptimistic**

---

## 🔬 ขั้นที่ 4: Logistic Regression (หัวใจของ ML ตรงนี้)

### Math สั้น ๆ

สำหรับแต่ละ dimension (เช่น EI):
```
z  = w₁·q1 + w₂·q2 + ... + w₂₀·q20 + b
P(y=1 | x) = σ(z) = 1 / (1 + exp(-z))
```
- `w₁..w₂₀, b` = parameters ที่ sklearn หามาจาก data
- `P(y=1)` = P(second letter) = P(I) ในกรณี EI dim
- `P(y=0)` = 1 - P(y=1) = P(first letter) = P(E)

### `fit()` ทำอะไร

หา `w, b` ที่ทำให้ **log-likelihood** สูงสุด (= loss ต่ำสุด):
```
loss = -Σ [ y·log(p) + (1-y)·log(1-p) ]  +  regularization term
```
- `C=1.0` คือ inverse of regularization strength (ยิ่งน้อย → regularize มาก → weights เล็ก)
- `max_iter=1000` — iterations ของ L-BFGS solver (default)

### ทำไม 4 models แยก ไม่รวมเป็น 1 ตัว 16-class?

- **Interpretable:** แต่ละ dim อิสระ — อ่าน weight ของ `clf_EI` → รู้ว่าคำถามไหนมีผลต่อ EI มาก
- **Easier labeling:** synthetic data สร้าง 4 binary labels ได้ตรง ๆ
- **Less class imbalance:** 2-class ทำง่ายกว่า 16-class
- **Composable:** blend กับ rule-based ได้ง่าย (ทั้งคู่ให้คะแนนต่อ pole)

### รันจริงใน `train.py`

```python
for dim in DIM_IDX:  # ["EI", "SN", "TF", "JP"]
    y_tr = df.iloc[idx_tr][f"label_{dim}"].values    # shape (16000,)
    y_te = df.iloc[idx_te][f"label_{dim}"].values    # shape (4000,)

    clf = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    clf.fit(X_tr, y_tr)         # 👈 trains weights
```

หลัง `fit()` — `clf.coef_` คือ weight vector (shape `(1, 20)`), `clf.intercept_` คือ bias

---

## 🔬 ขั้นที่ 5: Metrics

### Per-dimension metrics

สำหรับแต่ละ dim (EI, SN, TF, JP):

| Metric | ความหมาย | คำนวณจาก |
|---|---|---|
| **train accuracy** | ถูกกี่ %ใน train set | `clf.score(X_tr, y_tr)` |
| **test accuracy** | ถูกกี่ %ใน test set (สำคัญที่สุด) | `clf.score(X_te, y_te)` |
| **precision** | พยากรณ์ว่าเป็น pole นี้ แล้วถูกจริงกี่ % | TP / (TP+FP) |
| **recall** | คนที่เป็น pole นี้ จับได้กี่ % | TP / (TP+FN) |
| **f1** | Harmonic mean ของ precision + recall | 2·P·R / (P+R) |

ค่าที่คาดหวัง (noise=0.15): **~0.92-0.96** ทั้ง 4 metrics

### Overall 16-type accuracy

```python
pred_type = ""
for dim in ["EI", "SN", "TF", "JP"]:
    p_first = clf[dim].predict_proba(x)[0][idx_class_0]
    pred_type += dim[0] if p_first >= 0.5 else dim[1]
# เช่น "ISTJ"

overall_acc = accuracy_score(true_types_te, pred_types)
```

**คาดหวัง ~0.80-0.85** — ต่ำกว่า per-dim เพราะต้องถูกทั้ง 4 dims พร้อมกัน (0.95⁴ ≈ 0.81)

### Per-type accuracy

สำหรับแต่ละ type (16 types) — ในกลุ่มที่ true_type = นี้ ทายถูกกี่ %
```python
per_type_acc["INTJ"] = TP_INTJ / total_INTJ
```
ถ้าบาง type accuracy ต่ำผิดปกติ → แสดงว่า synthetic data หรือ question mapping ของ type นั้นไม่ดีพอ

---

## 🔬 ขั้นที่ 6: Save artifacts

```python
bundle = {
    "scaler": scaler,
    "models": {"EI": clf_EI, "SN": clf_SN, "TF": clf_TF, "JP": clf_JP},
    "n_features": 20,
    "dimensions": ["EI", "SN", "TF", "JP"],
}
joblib.dump(bundle, "models/mbti_model.pkl")
```

- **`joblib`** (ไม่ใช้ pickle) — เร็วกว่าและดีกว่าสำหรับ numpy arrays
- **`metrics.json`** — human-readable + version control ได้

### ตอน `predictor.py` โหลด

```python
bundle = joblib.load(MODEL_PATH)
scaler = bundle["scaler"]
clf_EI = bundle["models"]["EI"]
# ...
```

**สำคัญ:** ใช้ scaler จาก bundle เพื่อ transform input ใหม่ด้วย mean/std เดียวกันกับตอนเทรน

---

## 🎯 สรุป: กลไกหลักที่ทำให้โมเดลใช้งานได้จริง

1. **Synthetic data quality** — noise model จำลองคนจริงได้แค่ไหน = upper bound ของ accuracy
2. **Question mapping** (`questions_map.py`) — ถ้า choice_id ↔ dimension ไม่ตรง → ทุกอย่างพัง
3. **Scaler consistency** — train/predict ต้องใช้ scaler เดียวกัน (เก็บใน bundle)
4. **Blend ใน `predict()`** — rule 70% + ML 30% ทำให้ output สเถียร แม้ ML แกว่ง

---

## 🔁 เทรนใหม่เมื่อไหร่?

| เหตุการณ์ | ต้อง retrain? |
|---|---|
| เพิ่ม/ลด/แก้คำถามใน `questions_map.py` | ✅ **ต้อง** — feature shape เปลี่ยน |
| แก้ weight ใน choice mapping | ✅ **ต้อง** — label distribution เปลี่ยน |
| แก้ blend weight ใน `predictor.py` | ❌ ไม่ต้อง — ใช้โมเดลเดิมได้ |
| แก้ `type_info.py` (nickname/description) | ❌ ไม่ต้อง |
| Deploy production | ✅ **ควร** — เทรนด้วย n_samples ใหญ่ขึ้น เช่น 100,000 |

---

## 🚀 ต่อไป (TODO สำหรับ session หน้า)

- [ ] รัน `python train.py` ให้สำเร็จ → ได้ `mbti_model.pkl` + `metrics.json`
- [ ] เขียน smoke test: ส่งคำตอบชัด ๆ แบบ INTJ → ตรวจว่าได้ "INTJ"
- [ ] เพิ่ม `Dockerfile` ของ AI service (สำหรับ deploy จริง)
- [ ] (optional) fine-tune anchors สำหรับ Thai free-text

---

👉 อ้างอิง: [02-ai-model.md](./02-ai-model.md) สำหรับภาพรวมและเหตุผลของ design
