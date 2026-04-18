# 05 — MBTI Theory (เข้าใจก่อนอ่าน AI)

## 🎯 MBTI คืออะไร

**Myers-Briggs Type Indicator** = personality framework แบ่งคนเป็น **16 types** จาก **4 dimensions** (คู่ตรงข้าม)

> Note: MBTI เป็นเครื่องมือ popular แต่ทางวิชาการมีข้อถกเถียง — ในโปรเจคนี้ใช้เป็น framework ในการสอน ML/engineering ไม่ใช่ diagnostic tool

## 🧭 4 Dimensions

### 1. Energy: **E** (Extraversion) vs **I** (Introversion)
- **E** — ชาร์จพลังจากการอยู่กับผู้คน, ชอบ action, พูดก่อนคิด
- **I** — ชาร์จจากการอยู่คนเดียว, ชอบ reflect, คิดก่อนพูด

### 2. Information: **S** (Sensing) vs **N** (iNtuition)
- **S** — ให้ความสำคัญกับข้อเท็จจริง, รายละเอียด, ปัจจุบัน
- **N** — ให้ความสำคัญกับ pattern, ความเป็นไปได้, อนาคต

### 3. Decisions: **T** (Thinking) vs **F** (Feeling)
- **T** — ตัดสินใจด้วย logic, ความยุติธรรม, วิเคราะห์
- **F** — ตัดสินใจด้วยคุณค่า, ผลต่อคน, เห็นใจ

### 4. Lifestyle: **J** (Judging) vs **P** (Perceiving)
- **J** — ชอบ plan, โครงสร้าง, ตัดสินใจเร็ว
- **P** — ยืดหยุ่น, เปิดรับตัวเลือก, spontaneous

## 🧬 16 Types

| Analysts (NT) | Diplomats (NF) | Sentinels (SJ) | Explorers (SP) |
|---|---|---|---|
| **INTJ** — Architect | **INFJ** — Advocate | **ISTJ** — Logistician | **ISTP** — Virtuoso |
| **INTP** — Logician | **INFP** — Mediator | **ISFJ** — Defender | **ISFP** — Adventurer |
| **ENTJ** — Commander | **ENFJ** — Protagonist | **ESTJ** — Executive | **ESTP** — Entrepreneur |
| **ENTP** — Debater | **ENFP** — Campaigner | **ESFJ** — Consul | **ESFP** — Entertainer |

## 🧮 Scoring Logic (วิธีคำนวณ)

ในโปรเจคนี้ ใช้วิธีคลาสสิกผสม ML:

### Step 1 — Question → Dimension mapping
แต่ละคำถามถูก "ติด" ว่าวัด dimension ไหน + choice ไหนชี้ไปทิศทางใด

ตัวอย่าง:
```
Q: ในงานปาร์ตี้ คุณมักจะ...
   A) เข้าหาและพูดคุยกับคนใหม่ ๆ    [E +1]
   B) รอให้คนอื่นเข้าหา              [I +1]
   C) อยู่กับคนที่รู้จักเท่านั้น      [I +0.5]
```

### Step 2 — Aggregate scores
รวม 20 คำถาม:
```
E_score = 4, I_score = 2    → E (Extroversion)
S_score = 1, N_score = 5    → N (iNtuition)
T_score = 3, F_score = 2    → T (Thinking)  
J_score = 2, P_score = 3    → P (Perceiving)

→ Type = ENTP
```

### Step 3 — Normalize เป็น % (0-100)
```
E% = E_score / (E_score + I_score) * 100 = 66.7%
```
> ใช้แสดงบน radar chart

### Step 4 — ML validation (LogReg)
Feature vector = 20 คำตอบ → predict 4 dimensions อีกครั้ง → ถ้าต่างจาก rule-based มาก ให้แสดงทั้ง 2 type (ambivert / borderline) — ใน code เรียกว่า `confidence`

### Step 5 — (Optional) Free-text analysis
ถ้า user เขียน "บอกเล่าตัวเอง" เพิ่มท้ายแบบทดสอบ:
- ใช้ **sentence-transformers** embed เป็น vector 384-dim
- Cosine similarity กับ anchor sentence ของแต่ละ dimension
- Blend กับ rule-based score (weight 30%)

## 📝 ตัวอย่าง trait description

แต่ละ type มี description (rule-based template):
```
INTJ — The Architect
- เชิงกลยุทธ์, เป็นระบบ, เห็นภาพรวม
- ทำงานคนเดียวได้ดี, มุ่งเป้า, แม่นยำ
- อาจ: ขาดความอบอุ่น, ใจร้อนกับคนที่ไม่ทำตามแผน
- งานที่เหมาะ: นักวิทยาศาสตร์, ที่ปรึกษา, นักยุทธศาสตร์
```

## 🔍 Cognitive Functions (advanced)

MBTI ลึกกว่าแค่ 4 ตัวอักษร — มี 8 cognitive functions (Ni, Ne, Si, Se, Ti, Te, Fi, Fe) เรียงเป็น function stack ต่อ type

ในโปรเจคนี้ **ไม่ได้ใช้** (เก็บไว้ขยายต่อ) — scoring อยู่ใน 4 dimensions

## 📚 References

- Myers-Briggs Foundation: <https://www.myersbriggs.org/>
- 16personalities: <https://www.16personalities.com/> (Neris Type Explorer — แนวใกล้ MBTI)
- ทางวิชาการ: Big Five (OCEAN) — ยอมรับมากกว่า

---

👉 ต่อ: [02-ai-model.md](./02-ai-model.md) — รายละเอียด model + training
