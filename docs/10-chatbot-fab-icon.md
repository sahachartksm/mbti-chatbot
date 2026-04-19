# 10 — Chatbot MBTI Interactive Icon (FAB Chat Mode)

> ระบบนี้เปลี่ยนโหมดการทดสอบจาก "เลือกตอบทีละข้อ" → **"พูดคุยกับ AI แบบ Free-text"**
> AI วิเคราะห์บุคลิกภาพ MBTI จากบทสนทนาเองโดยไม่ต้องถามทีละคำถาม

> **Implementation Status:** ✅ Implemented (2026-04-19)
> ไฟล์ที่สร้าง/แก้ไข: `ai-service/gemini_client.py`, `ai-service/behavioral_signals.py`, `ai-service/reply_generator.py`, `ai-service/chat_predictor.py`, `ai-service/app.py`, `ai-service/requirements.txt`, `ai-service/.env.example`, `backend/models/models.go`, `backend/db/mongo.go`, `backend/ai/client.go`, `backend/handlers/chat.go`, `backend/main.go`, `frontend/.../fab-chat.component.ts`, `frontend/.../fab-chat.service.ts`, `frontend/app.component.ts`

---

## 🎯 ภาพรวม Feature

```
┌─────────────────────────────────────────────────────────┐
│                  Browser (Angular SPA)                   │
│                                                          │
│   ┌──────────────────────────────┐                      │
│   │  Chat Window (slide-up)      │                      │
│   │  ┌──────────────────────┐   │          [✕]         │
│   │  │ AI: สวัสดี! เล่าให้  │   │                      │
│   │  │ ฟังหน่อยได้ไหมว่า    │   │                      │
│   │  │ วันนี้คุณทำอะไร?    │   │                      │
│   │  └──────────────────────┘   │                      │
│   │  ┌──────────────────────┐   │                      │
│   │  │ User: วันนี้ผมชอบ... │   │                      │
│   │  └──────────────────────┘   │                      │
│   │  ─────────────────────────  │                      │
│   │  [พิมพ์ข้อความ...] [ส่ง]   │                      │
│   └──────────────────────────────┘                      │
│                                                          │
│                                      ┌──────┐           │
│                                      │  🧠  │  ← FAB   │
│                                      └──────┘           │
└─────────────────────────────────────────────────────────┘
```

---

## 🖱️ UI/UX — Floating Action Button (FAB)

### ตำแหน่งและ Layout

FAB อยู่มุมขวาล่างของ viewport — fixed position ไม่ขยับตาม scroll

```scss
// fab-chat.component.scss

.fab-container {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 1000;       // ลอยเหนือ content ทุกอย่าง
}

.fab-button {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
  cursor: pointer;
  border: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    transform: scale(1.1);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.7);
  }

  &.is-open {
    transform: rotate(45deg);   // ไอคอนหมุนเป็น ✕ เมื่อ window เปิด
  }
}

.fab-icon {
  font-size: 28px;              // emoji หรือ SVG icon สมอง/ฟอง
}
```

### Animation — Chat Window Slide Up

```scss
.chat-window {
  position: fixed;
  bottom: 100px;       // ลอยเหนือ FAB
  right: 28px;
  width: 360px;
  height: 520px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;

  // เริ่มต้น: ซ่อน + เลื่อนลงข้างล่าง
  opacity: 0;
  transform: translateY(20px) scale(0.95);
  transform-origin: bottom right;
  pointer-events: none;
  transition: opacity 0.25s ease, transform 0.25s ease;

  &.is-visible {
    opacity: 1;
    transform: translateY(0) scale(1);
    pointer-events: all;
  }
}
```

### Angular Component Structure

```
frontend/src/app/components/fab-chat/
└── fab-chat.component.ts        ← single-file: FAB + chat window + styles (inline)

frontend/src/app/services/
└── fab-chat.service.ts          ← HTTP calls + session state (Signal)
```

> **Note:** ใช้ single-file component (template + styles inline ใน `.ts`) ตามสไตล์ project นี้ — ไม่มีไฟล์ `.html` / `.scss` แยก

ใส่ `<app-fab-chat />` ใน `app.component.ts` ครั้งเดียว — แสดงทุกหน้า

```html
<!-- app.component.ts template -->
<router-outlet />
<app-fab-chat />   <!-- FAB ลอยอยู่ทุก route -->
```

---

## 💬 Core Concept — Free-text Chat (ไม่ใช่ Multiple Choice)

### เปรียบเทียบ 2 โหมด

| | โหมดเดิม (Quiz) | โหมดใหม่ (FAB Chat) |
|--|-----------------|---------------------|
| **วิธีตอบ** | เลือก a/b/c ทีละข้อ | พิมพ์คุยอิสระ |
| **ข้อมูลที่ได้** | structured choices 20 ข้อ | free-text หลาย turn |
| **ประสบการณ์ผู้ใช้** | ทำแบบทดสอบ | คุยกับ AI เป็นธรรมชาติ |
| **Engine หลัก** | rule-based + LogReg | **Google Gemini API (LLM)** |
| **Engine สำรอง** | — | SBERT + keyword + behavioral signals |
| **จำนวนรอบ** | 20 ข้อ (คงที่) | อย่างน้อย 10-15 รอบ |
| **เกณฑ์สรุปผล** | ครบ 20 ข้อ | ≥10 รอบ AND dim_confidence ทุกด้าน ≥ 80% |

### ปรัชญาการออกแบบ — Psychometrics Expert Mode

> "อย่าถามตรงๆ ว่าคุณเป็น I หรือ E — ให้สังเกตจากวิธีที่เขาพูดถึงตัวเอง"

AI ใช้บทสนทนาเป็น **ข้อมูลพฤติกรรม** ผ่าน Cognitive Functions Framework:

- ถามเจาะลึก **Se/Si** (รายละเอียดจริง vs ความหมาย/บทเรียน) → signal S/N
- ถามเจาะลึก **Ne/Ni** (ไอเดียหลากหลาย vs วิสัยทัศน์ชัดเจน) → signal S/N
- ถามเจาะลึก **Te/Ti** (ตรรกะภายนอก/ระบบ vs หลักการภายใน) → signal T/F
- ถามเจาะลึก **Fe/Fi** (บรรยากาศกลุ่ม vs ค่านิยมส่วนตัว) → signal T/F
- สังเกต **Behavioral Signals** จากรูปแบบการเขียน (ความยาว, คำนามธรรม, โครงสร้าง)

---

## ⚙️ Technical Logic — Data Flow รายขั้น

### ภาพรวม

```
User พิมพ์ข้อความ
       │
       ▼
[Angular FAB Component]
  - เก็บ conversation history (local state)
  - ส่ง POST /api/chat/message
       │
       ▼
[Go Backend — /api/chat/]
  - validate + บันทึก user turn ลง MongoDB
  - นับ userTurnCount (รวม turn ใหม่)
  - เรียก AI Service POST /chat/analyze (ส่ง full history)
       │
       ▼
[Python AI Service — port 8000]
  ┌── Primary (ถ้ามี GEMINI_API_KEY) ──────────────────┐
  │  1) format full history เป็น text context           │
  │  2) ส่งไป Google Gemini API (gemini-2.0-flash)     │
  │  3) Gemini วิเคราะห์ Cognitive Functions           │
  │  4) Gemini ส่ง reply ธรรมชาติ + dimension_confidence│
  │  5) ตรวจสอบเงื่อนไข show_result                   │
  └────────────────────────────────────────────────────┘
  ┌── Fallback (ถ้าไม่มี Gemini) ──────────────────────┐
  │  1) BehavioralSignalExtractor: SBERT + keyword + regex│
  │  2) คำนวณ confidence + resolved_dims               │
  │  3) ReplyGenerator: เลือก follow-up question       │
  └────────────────────────────────────────────────────┘
  - return: {reply, partial_scores, dimension_confidence, confidence, show_result}
       │
       ▼
[Go Backend]
  - บันทึก AI reply turn ลง MongoDB
  - ส่ง show_result_button ตาม aiResp.ShowResult จาก AI service (ไม่ได้คำนวณซ้ำ)
       │
       ▼
[Angular]
  - แสดง reply ใน chat bubble
  - ถ้า show_result_button = true → แสดงปุ่ม "ดูผลลัพธ์ MBTI ของคุณ"
```

---

## 📥 Step 1 — รับ Input จาก User (Angular)

```typescript
// fab-chat.component.ts

export class FabChatComponent {
  isOpen = signal(false);
  messages = signal<ChatMessage[]>([]);
  inputText = signal('');
  isLoading = signal(false);
  mbtiResult = signal<MBTIResult | null>(null);

  constructor(private fabChat: FabChatService) {}

  toggleChat() {
    this.isOpen.update(v => !v);
    // ครั้งแรกที่เปิด → สร้าง chat session + รับ greeting
    if (this.isOpen() && this.messages().length === 0) {
      this.startConversation();
    }
  }

  async sendMessage() {
    const text = this.inputText().trim();
    if (!text || this.isLoading()) return;

    // 1. แสดง user bubble ทันที (optimistic UI)
    this.messages.update(msgs => [...msgs, {
      role: 'user', text, timestamp: new Date()
    }]);
    this.inputText.set('');
    this.isLoading.set(true);

    try {
      // 2. ส่งไป Backend
      const response = await this.fabChat.sendMessage(text);

      // 3. แสดง AI reply
      this.messages.update(msgs => [...msgs, {
        role: 'ai',
        text: response.reply,
        showResultButton: response.show_result_button,
        timestamp: new Date()
      }]);

      this.scrollToBottom();

    } finally {
      this.isLoading.set(false);
    }
  }

  async showResult() {
    const result = await this.fabChat.getResult();
    this.mbtiResult.set(result);   // แสดง inline result card
  }

  restart() {
    this.fabChat.reset();
    this.messages.set([]);
    this.mbtiResult.set(null);
    this.startConversation();
  }
}
```

```typescript
// fab-chat.service.ts

@Injectable({ providedIn: 'root' })
export class FabChatService {
  private sessionId = signal<string | null>(null);

  async startSession(): Promise<string> {
    const res = await firstValueFrom(
      this.http.post<{ session_id: string; greeting: string }>('/api/chat/start', {})
    );
    this.sessionId.set(res.session_id);
    return res.greeting;
  }

  async sendMessage(text: string): Promise<{
    reply: string;
    show_result_button: boolean;
    session_id: string;
    turn_count: number;
  }> {
    return firstValueFrom(
      this.http.post('/api/chat/message', {
        session_id: this.sessionId(), text
      })
    );
  }

  async getResult(): Promise<MBTIResult> {
    return firstValueFrom(
      this.http.post<MBTIResult>('/api/chat/result', {
        session_id: this.sessionId()
      })
    );
  }

  reset() { this.sessionId.set(null); }
}
```

---

## 🔀 Step 2 — Go Backend รับ Request และ Orchestrate

### Endpoints

| Method | Path | ทำอะไร |
|--------|------|---------|
| `POST` | `/api/chat/start` | สร้าง chat session ใหม่ + บันทึก greeting turn ลง MongoDB |
| `POST` | `/api/chat/message` | รับ turn ใหม่ → เรียก AI → บันทึก → ส่ง reply กลับ |
| `POST` | `/api/chat/result` | โหลด session ทั้งหมด → เรียก AI finalize → บันทึก result |

### Handler Logic — `/api/chat/message`

```go
// backend/handlers/chat.go

func (h *Handler) ChatMessage(w http.ResponseWriter, r *http.Request) {
    var req chatMsgReq  // { session_id, text }
    json.NewDecoder(r.Body).Decode(&req)

    // 1. โหลด session จาก Mongo
    sess, err := h.Repo.GetChatSession(r.Context(), req.SessionID)
    // ...

    // 2. นับ user turns (รวม turn ใหม่ที่กำลังส่ง)
    userTurnCount := 1
    for _, t := range sess.Turns {
        if t.Role == "user" { userTurnCount++ }
    }

    // 3. รวม turn ใหม่ต่อท้าย history → ส่ง full history ไป AI
    allTurns := append(sess.Turns, userTurn)
    aiResp, err := h.AI.ChatAnalyze(ctx, ai.ChatAnalyzeRequest{
        SessionID:     req.SessionID,
        Turns:         dtos,        // full history รวม turn ใหม่
        UserTurnCount: userTurnCount,
    })

    // 4. บันทึก user turn + ai turn ลง MongoDB (atomic $push $each)
    h.Repo.AppendChatTurns(r.Context(), req.SessionID,
        []models.ChatTurn{userTurn, aiTurn})

    // 5. show_result_button มาจาก AI service โดยตรง (Go ไม่คำนวณซ้ำ)
    json.NewEncoder(w).Encode(map[string]any{
        "reply":              aiResp.Reply,
        "show_result_button": aiResp.ShowResult,   // ← มาจาก AI service
        "session_id":         req.SessionID,
        "turn_count":         userTurnCount,
    })
}
```

> **สำคัญ:** Go backend **ไม่ได้** ตัดสิน `show_result` เอง — รับค่ามาจาก AI service โดยตรงผ่าน `aiResp.ShowResult`

### Data Model — Chat Session

```go
// backend/models/models.go

type ChatSession struct {
    ID        string      `bson:"_id"      json:"session_id"`
    CreatedAt time.Time   `bson:"created_at"`
    Turns     []ChatTurn  `bson:"turns"    json:"turns"`
}

type ChatTurn struct {
    Role          string            `bson:"role"    json:"role"`   // "user" | "ai"
    Text          string            `bson:"text"    json:"text"`
    Timestamp     time.Time         `bson:"ts"      json:"timestamp"`
    PartialScores map[string]int    `bson:"partial_scores,omitempty"`
}
```

---

## 🧠 Step 3 — AI Service: Gemini Primary + Fallback (Python)

### Architecture: Gemini-First

```python
# ai-service/chat_predictor.py

def analyze(turns: List[Dict], user_turn_count: int) -> Dict:
    # ── Primary: Google Gemini API ─────────────────────────────
    gemini_result = gemini_client.chat_analyze(turns, user_turn_count)
    if gemini_result is not None:
        return gemini_result   # ← จบที่นี่ถ้า Gemini พร้อม

    # ── Fallback: Keyword/SBERT (ถ้าไม่มี GEMINI_API_KEY) ─────
    user_texts = [t["text"] for t in turns if t["role"] == "user"]
    signals = BehavioralSignalExtractor(...).extract(user_texts)
    confidence = _compute_confidence(signals, user_turn_count)
    resolved_dims = _compute_resolved_dims(signals)

    all_resolved = len(resolved_dims) >= 4
    enough_turns = user_turn_count >= MIN_USER_TURNS and confidence >= CONFIDENCE_THRESHOLD
    show_result = all_resolved and enough_turns

    reply = generate_reply(resolved_dims, turns, show_result)
    return {
        "reply": reply,
        "partial_scores": _flatten_scores(signals),
        "dimension_confidence": dim_conf,
        "confidence": confidence,
        "show_result": show_result,
        "resolved_dims": list(resolved_dims),
    }
```

### Thresholds

| ค่า | Gemini Mode | Fallback Mode |
|-----|-------------|---------------|
| `MIN_USER_TURNS_FOR_RESULT` | 10 (ใน `gemini_client.py`) | 10 (ใน `chat_predictor.py`) |
| `DIM_CONFIDENCE_THRESHOLD` | 0.80 ต่อ dimension | 0.80 (overall) |
| `RESOLVED_CLARITY` | — | 0.30 (clarity per dim) |

### Endpoints ใน `app.py`

```python
# ai-service/app.py  (v2.0.0)

@app.post("/chat/analyze")
def chat_analyze(req: ChatAnalyzeRequest):
    turns = [{"role": t.role, "text": t.text} for t in req.turns]
    return chat_predictor.analyze(turns, req.user_turn_count)

@app.post("/chat/final")
def chat_final(req: ChatFinalRequest):
    turns = [{"role": t.role, "text": t.text} for t in req.turns]
    return chat_predictor.finalize(turns)
```

---

## 🤖 Step 4 — Gemini Client: Psychometrics Expert Mode

### `gemini_client.py` — Logic หลัก

```python
# ai-service/gemini_client.py

MIN_USER_TURNS_FOR_RESULT = 10   # ต้องคุยอย่างน้อย 10 รอบ
DIM_CONFIDENCE_THRESHOLD  = 0.80  # ทุก dimension ต้องมั่นใจ ≥ 80%

def chat_analyze(turns, user_turn_count) -> Optional[Dict]:
    # 1. Format full history → text prompt
    history_text = _format_history(turns)

    # 2. ส่ง prompt ไป Gemini (response_mime_type="application/json")
    result = _call(_model_analyze, prompt)

    # 3. Fix pairs: E+I=100, S+N=100, T+F=100, J+P=100
    result["partial_scores"] = _fix_pairs(result.get("partial_scores", {}))

    # 4. กฎ: show_result = true เมื่อครบเงื่อนไขเท่านั้น
    enough_turns  = user_turn_count >= MIN_USER_TURNS_FOR_RESULT       # ≥ 10
    all_confident = _all_dims_confident(dim_conf, DIM_CONFIDENCE_THRESHOLD)  # ทุกด้าน ≥ 0.80
    result["show_result"] = enough_turns and all_confident

    return result
```

### System Prompt — ANALYZE_SYSTEM_PROMPT (สรุป)

Gemini ได้รับ instruction ให้:
- ชวนสนทนาอย่างน้อย **10-15 รอบ** ก่อนสรุป
- ถามเจาะลึก Cognitive Functions (Se/Si/Ne/Ni/Te/Ti/Fe/Fi) ไม่ถามผิวเผิน
- ตรวจสอบ chat history ทุกครั้ง **ห้ามถามซ้ำ**
- วิเคราะห์ Behavioral Signals จากรูปแบบการเขียน
- ตอบ JSON พร้อม `dimension_confidence` ต่อ dimension

---

## 🔍 Step 5 — Behavioral Signal Extractor (Fallback)

ใช้เมื่อ Gemini ไม่พร้อม (ไม่มี API key หรือ call ล้มเหลว)

```python
# ai-service/behavioral_signals.py

class BehavioralSignalExtractor:
    """
    3 วิธีประกอบกัน:
      1) SBERT cosine similarity กับ anchor phrases (weight 0.5) — ถ้า SBERT โหลดสำเร็จ
      2) Keyword matching ไทย/อังกฤษ              (weight 0.3)
      3) Linguistic style regex patterns            (weight 0.2)
    """

    def __init__(self, sbert_model=None, anchor_embeddings=None):
        self.sbert = sbert_model
        self.anchor_embeddings = anchor_embeddings  # pre-computed vectors

    def extract(self, user_texts: List[str]) -> Dict[str, Dict[str, int]]:
        raw = {pole: 0.0 for pole in "EISNTFJP"}

        for text in user_texts:
            # Method 1: SBERT (optional — graceful fallback ถ้า SBERT ไม่ได้โหลด)
            if self.sbert and self.anchor_embeddings:
                vec = self.sbert.encode([text], normalize_embeddings=True)[0]
                for pole, anchor_vec in self.anchor_embeddings.items():
                    raw[pole] += max(0.0, np.dot(vec, anchor_vec)) * 0.5

            # Method 2: Keyword
            for pole, keywords in KEYWORD_SIGNALS.items():
                hits = sum(1 for kw in keywords if kw in text.lower())
                raw[pole] += hits * 0.3

            # Method 3: Regex style
            for pole, patterns in STYLE_PATTERNS.items():
                hits = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
                raw[pole] += hits * 0.2

        return self._normalize(raw)   # → {"EI": {"E": 35, "I": 65}, ...}
```

---

## 🗣️ Step 6 — Reply Generator (Fallback)

ใช้เมื่อ Gemini ไม่พร้อม — ถามคำถาม Cognitive Functions แบบ module-level functions

```python
# ai-service/reply_generator.py  (module-level functions, ไม่ใช่ class)

# ลำดับถาม: EI → JP → TF → SN
DIM_ORDER = ["EI", "JP", "TF", "SN"]

# คำถามเจาะลึก Cognitive Functions (4 ข้อต่อ dimension)
FOLLOW_UP_QUESTIONS = {
    "EI": [
        "หลังจากงานสังสรรค์หรือประชุมยาวๆ คุณรู้สึกได้พลังเพิ่มขึ้นหรือหมดแรง?",
        "เวลาต้องตัดสินใจสำคัญ คุณชอบคิดคนเดียวก่อน หรือชอบพูดคุยกับคนอื่นเพื่อระดมความคิด?",
        # ...
    ],
    # SN, TF, JP เหมือนกัน
}

def get_asked_questions(ai_turns) -> Set[str]:
    """ดึงคำถามที่ AI เคยถามไปแล้วทั้งหมด — เพื่อป้องกันถามซ้ำ"""

def pick_next_question(resolved_dims, asked_questions, ai_turns) -> Optional[tuple]:
    """เลือก (dimension, question) ถัดไป — ข้าม dimension ที่ resolved + คำถามที่ถามแล้ว"""
    for dim in DIM_ORDER:
        if dim in resolved_dims: continue      # กฎข้อ 2: ข้าม resolved dim
        available = [q for q in FOLLOW_UP_QUESTIONS[dim] if q not in asked_questions]
        if available:
            return dim, random.choice(available)
    return None  # ครบทุก dimension แล้ว

def generate_reply(resolved_dims, all_turns, show_result) -> str:
    """
    กฎ 3 ข้อ:
      1. ไม่ถามคำถามซ้ำ (ดูจาก asked_questions)
      2. ข้าม dimension ที่ resolved แล้ว
      3. ถ้าครบทุก dimension / show_result → hint ให้กดดูผล
    """
    if len(resolved_dims) >= 4:
        return f"{ack} {ALL_DONE_HINT}"    # ทุก dim ครบ → หยุดถาม
    if show_result:
        return f"{ack} {next_question}{READY_HINT}"  # พร้อมดูผลแล้ว
    return f"{ack} {next_question}"        # ยังถามต่อ
```

---

## 📊 Step 7 — Confidence Scoring และการตัดสินใจสรุปผล

### Fallback Mode (keyword signals)

```python
# ai-service/chat_predictor.py

MIN_USER_TURNS     = 10    # ต้องคุยอย่างน้อย 10 รอบ
CONFIDENCE_THRESHOLD = 0.80  # confidence รวม ≥ 80%
RESOLVED_CLARITY   = 0.30  # ต้องมี clarity > 30% จึงนับว่า resolved

def _compute_confidence(signals, user_turn_count) -> float:
    """
    confidence = avg_clarity × turn_factor
    turn_factor = min(1.0, user_turn_count / 15.0) * 0.6 + 0.4
    clarity     = |pole_a - pole_b| / 100
    """
    clarity_scores = [abs(list(p.values())[0] - list(p.values())[1]) / 100.0
                      for p in signals.values()]
    avg_clarity = sum(clarity_scores) / len(clarity_scores)
    turn_factor = min(1.0, user_turn_count / 15.0) * 0.6 + 0.4
    return round(avg_clarity * turn_factor, 3)

def _compute_resolved_dims(signals) -> Set[str]:
    """clarity > 0.30 = resolved"""
    return {
        dim for dim, poles in signals.items()
        if abs(list(poles.values())[0] - list(poles.values())[1]) / 100.0 > RESOLVED_CLARITY
    }
```

### กฎเหล็ก 5 ข้อ (Psychometrics Expert Mode)

```
กฎข้อ 1 — ห้ามด่วนสรุป:
  ต้องสนทนาอย่างน้อย 10-15 รอบ
  MIN_USER_TURNS_FOR_RESULT = 10  (gemini_client.py)
  MIN_USER_TURNS = 10             (chat_predictor.py fallback)

กฎข้อ 2 — ถามเจาะลึก Cognitive Functions:
  EI: พลังงานจาก E(ภายนอก) vs I(ภายใน) — ถาม Se/Si, Ni/Ne
  SN: ข้อมูล S(รายละเอียด/ข้อเท็จจริง) vs N(ภาพรวม/แบบแผน)
  TF: ตัดสินใจ T(ตรรกะ/Te/Ti) vs F(ค่านิยม/Fe/Fi)
  JP: ชีวิต J(โครงสร้าง/ปิดเรื่อง) vs P(ยืดหยุ่น/เปิดตัวเลือก)
  ลำดับถาม (fallback): EI → JP → TF → SN

กฎข้อ 3 — วิเคราะห์ Behavioral Signals:
  E/I: ความยาวตอบ (ยาว=E, กระชับ=I), "เรา/พวกเรา" vs "ผม/ฉัน"
  S/N: คำรูปธรรม (S) vs คำนามธรรม/เปรียบเทียบ (N)
  T/F: ตอบด้วยเหตุผลตรงๆ (T) vs เชื่อมกับความรู้สึก/คนอื่น (F)
  J/P: ประโยคมีโครงสร้างชัด (J) vs ความคิดไหลต่อเนื่อง (P)

กฎข้อ 4 — ห้ามถามซ้ำ:
  Gemini: ได้รับ full history ใน prompt → วิเคราะห์เองว่ายังไม่ได้ถามอะไร
  Fallback: get_asked_questions() scan AI turns ทุกครั้ง → exclude คำถามที่ถามแล้ว

กฎข้อ 5 — สรุปเมื่อมั่นใจ ≥ 80%:
  show_result = true เมื่อ (คำนวณใน AI service เท่านั้น):
    user_turns ≥ 10
    AND dimension_confidence["EI"] ≥ 0.80
    AND dimension_confidence["SN"] ≥ 0.80
    AND dimension_confidence["TF"] ≥ 0.80
    AND dimension_confidence["JP"] ≥ 0.80
```

### JSON Response Schema — `/chat/analyze`

```json
{
  "reply": "เข้าใจแล้ว! ขอถามเพิ่มเติมสักเรื่อง — เวลาคุณต้องตัดสินใจสำคัญ...",
  "partial_scores": {"E": 30, "I": 70, "S": 45, "N": 55, "T": 65, "F": 35, "J": 60, "P": 40},
  "dimension_confidence": {"EI": 0.85, "SN": 0.32, "TF": 0.72, "JP": 0.61},
  "confidence": 0.625,
  "show_result": false,
  "behavioral_signals": "ตอบสั้น, ใช้คำรูปธรรม, มีโครงสร้างประโยคชัด"
}
```

### JSON Response Schema — `/chat/final`

```json
{
  "mbti_type": "INTJ",
  "nickname": "The Architect (สถาปนิก)",
  "cognitive_stack": "Ni > Te > Fi > Se",
  "dimensions": {"E": 25, "I": 75, "S": 35, "N": 65, "T": 68, "F": 32, "J": 72, "P": 28},
  "dimension_confidence": {"EI": 0.88, "SN": 0.85, "TF": 0.82, "JP": 0.90},
  "confidence": 0.8625,
  "description": "คุณมีวิสัยทัศน์ที่ชัดเจนและมักมองเห็น...",
  "reasoning": "1. คุณพูดว่า... 2. สังเกตว่า... 3. เมื่อถามเรื่อง TF...",
  "behavioral_evidence": "ใช้คำนามธรรมมาก, ตอบยาวและเชื่อมโยงหลายแนวคิด",
  "strengths": ["..."],
  "weaknesses": ["..."],
  "careers": ["..."],
  "famous_people": ["..."],
  "compatible_types": ["ENFP", "ENTP"]
}
```

### ผลลัพธ์แสดง Inline ใน Chat Window

```
┌────────────────────────────┐
│ 🧠 MBTI AI Chat        ✕  │
├────────────────────────────┤
│  [AI bubble: ...]          │
│  [User bubble: ...]        │
│  ┌──────────────────────┐  │  ← Inline Result Card
│  │      I N T J         │  │
│  │   The Architect      │  │
│  │  ความมั่นใจ: 86%     │  │
│  │  E ████░░░░░░ I      │  │
│  │  S ███░░░░░░░ N      │  │
│  │  T ███████░░ F       │  │
│  │  J ████████░ P       │  │
│  │  [🔄 ทำใหม่อีกครั้ง]  │  │
│  └──────────────────────┘  │
└────────────────────────────┘
```

---

## 🗃️ MongoDB — Collection ใหม่

```javascript
// Collection: chat_sessions

{
  "_id": "chat_01HW8...",
  "created_at": ISODate("2026-04-19T03:00:00Z"),
  "turns": [
    {
      "role": "ai",
      "text": "สวัสดี! ฉันคือ AI ที่จะช่วยวิเคราะห์บุคลิกภาพ MBTI...",
      "ts": ISODate("2026-04-19T03:00:01Z"),
      "partial_scores": null
    },
    {
      "role": "user",
      "text": "วันนี้ผมชอบอยู่บ้านคนเดียว อ่านหนังสือ ไม่ค่อยอยากออกไปไหน",
      "ts": ISODate("2026-04-19T03:00:15Z"),
      "partial_scores": null
    },
    {
      "role": "ai",
      "text": "เข้าใจแล้ว! ขอถามเพิ่มเติม — หลังจากประชุมหรืองานสังสรรค์ยาวๆ คุณรู้สึกอย่างไร?",
      "ts": ISODate("2026-04-19T03:00:16Z"),
      "partial_scores": {"E": 25, "I": 75, "S": 50, "N": 50, "T": 50, "F": 50, "J": 50, "P": 50}
    }
    // ... (ต้องอย่างน้อย 10 user turns ก่อนที่ show_result = true)
  ]
}
```

---

## 🔌 ไฟล์ที่เพิ่ม/แก้ (Implemented ✅)

### Angular (Frontend)
| ไฟล์ | สถานะ | สิ่งที่ทำ |
|------|--------|-----------|
| `components/fab-chat/fab-chat.component.ts` | ✅ สร้างใหม่ | FAB + chat window + inline result card (single-file) |
| `services/fab-chat.service.ts` | ✅ สร้างใหม่ | HTTP calls `/api/chat/*` + session state (signal) |
| `app.component.ts` | ✅ แก้ไข | import FabChatComponent + `<app-fab-chat />` |

### Go Backend
| ไฟล์ | สถานะ | สิ่งที่ทำ |
|------|--------|-----------|
| `handlers/chat.go` | ✅ สร้างใหม่ | `ChatStart`, `ChatMessage`, `ChatResult` — pass-through `show_result` จาก AI |
| `models/models.go` | ✅ แก้ไข | เพิ่ม `ChatSession`, `ChatTurn` struct |
| `db/mongo.go` | ✅ แก้ไข | `chatSessions` collection + `CreateChatSession`, `GetChatSession`, `AppendChatTurns` |
| `ai/client.go` | ✅ แก้ไข | เพิ่ม `ChatAnalyze()`, `ChatFinal()` + refactor ใช้ `post()` helper |
| `main.go` | ✅ แก้ไข | Register `/api/chat/start`, `/api/chat/message`, `/api/chat/result` |

### Python AI Service
| ไฟล์ | สถานะ | สิ่งที่ทำ |
|------|--------|-----------|
| `gemini_client.py` | ✅ สร้างใหม่ | **Primary engine** — Gemini API, cognitive functions prompt, `show_result` logic |
| `chat_predictor.py` | ✅ สร้างใหม่ | Router: Gemini → fallback, thresholds `MIN=10`, `CONF=0.80`, `CLARITY=0.30` |
| `behavioral_signals.py` | ✅ สร้างใหม่ | **Fallback** — `BehavioralSignalExtractor`: SBERT + keyword + regex |
| `reply_generator.py` | ✅ สร้างใหม่ | **Fallback** — `generate_reply()`: no-repeat, skip resolved dim, 5-rule |
| `app.py` | ✅ แก้ไข | v2.0 — Gemini lifespan init, chat endpoints, health แสดง engine + thresholds |
| `requirements.txt` | ✅ แก้ไข | เพิ่ม `google-generativeai>=0.8.0` |
| `.env.example` | ✅ สร้างใหม่ | `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-2.0-flash`, `AI_PORT=8000` |

---

## 🔧 Setup

```bash
# ตั้งค่า Gemini API Key
cp ai-service/.env.example ai-service/.env
# แก้ไข GEMINI_API_KEY=your_key_here

# รันด้วย Docker
docker compose up

# หรือรัน AI service โดยตรง
cd ai-service
GEMINI_API_KEY=your_key uvicorn app:app --reload --port 8000
```

### Health Check

```bash
curl http://localhost:8000/health | jq .
# {
#   "status": "ok",
#   "chat_engine": "gemini",
#   "gemini_enabled": true,
#   "gemini_model": "gemini-2.0-flash",
#   "min_turns_for_result": 10,
#   "dim_confidence_threshold": 0.80,
#   ...
# }
```

---

## 🧪 ทดสอบ

```bash
# 1. Start chat session
curl -X POST http://localhost:8080/api/chat/start \
  -H "Content-Type: application/json" -d '{}' | jq .

# 2. ส่งข้อความ (ต้องส่ง ≥ 10 ครั้ง จึงจะ show_result = true)
CSID=chat_xxx
curl -X POST http://localhost:8080/api/chat/message \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$CSID\",\"text\":\"วันนี้ผมชอบอยู่บ้านอ่านหนังสือคนเดียว\"}" | jq .

# 3. ดูผลเมื่อ show_result_button = true
curl -X POST http://localhost:8080/api/chat/result \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$CSID\"}" | jq .

# ทดสอบ AI โดยตรง
curl -X POST http://localhost:8000/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "turns": [
      {"role": "ai",   "text": "สวัสดี! เล่าให้ฟังหน่อยได้ไหม..."},
      {"role": "user", "text": "ผมชอบอยู่คนเดียว คิดคนเดียว ไม่ค่อยชอบงานสังสรรค์"}
    ],
    "user_turn_count": 1
  }' | jq .
```

---

## 🎓 สรุป Logic ทั้งระบบ

```
User พิมพ์ข้อความ (free-text)
       ↓
Angular: เก็บ + แสดง bubble + ส่ง POST /api/chat/message
       ↓
Go: บันทึก user turn → ส่ง full history ไป AI (พร้อม user_turn_count)
       ↓
Python AI Service:
  [Gemini Mode — มี GEMINI_API_KEY]
  ① format full history → text prompt
  ② Gemini วิเคราะห์ Cognitive Functions จาก context ทั้งหมด
  ③ Gemini สร้าง reply ธรรมชาติ + dimension_confidence ต่อ dim
  ④ ตรวจ: user_turns≥10 AND ทุก dim_confidence≥0.80 → show_result

  [Fallback Mode — ไม่มี Gemini]
  ① SBERT encode user turns → cosine sim กับ anchor
  ② keyword scan ไทย/อังกฤษ
  ③ regex linguistic style patterns
  ④ normalize → {EI:{E:30,I:70}, SN:{S:45,N:55}, ...}
  ⑤ compute confidence = clarity × turn_factor (÷15, ×0.6+0.4)
  ⑥ pick_next_question: EI→JP→TF→SN, ข้ามที่ resolved+ถามแล้ว
  ⑦ ตรวจ: user_turns≥10 AND confidence≥0.80 AND all_resolved → show_result
       ↓
Go: ส่ง show_result_button = aiResp.ShowResult (ไม่คำนวณซ้ำ)
       ↓
Angular: แสดง reply + (ถ้าพร้อม) ปุ่ม "ดูผลลัพธ์ MBTI ของคุณ"
       ↓
User กด "ดูผลลัพธ์"
       ↓
Go → AI /chat/final → MBTI type + cognitive_stack + reasoning
       ↓
Angular: แสดง inline result card ใน chat window (ไม่ navigate ออกไป)
```

---

👉 เกี่ยวข้องกับ: [02-ai-model.md](./02-ai-model.md) — model ที่ใช้, [03-api.md](./03-api.md) — API เดิม, [04-code-walkthrough.md](./04-code-walkthrough.md) — ไล่โค้ด
