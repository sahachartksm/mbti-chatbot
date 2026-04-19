# 10 — Chatbot MBTI Interactive Icon (FAB Chat Mode)

> ระบบนี้เปลี่ยนโหมดการทดสอบจาก "เลือกตอบทีละข้อ" → **"พูดคุยกับ AI แบบ Free-text"**
> AI วิเคราะห์บุคลิกภาพ MBTI จากบทสนทนาเองโดยไม่ต้องถามทีละคำถาม

> **Implementation Status:** ✅ Implemented (2026-04-19)
> ไฟล์ที่สร้าง/แก้ไข: `ai-service/behavioral_signals.py`, `ai-service/reply_generator.py`, `ai-service/chat_predictor.py`, `ai-service/app.py`, `backend/models/models.go`, `backend/db/mongo.go`, `backend/ai/client.go`, `backend/handlers/chat.go`, `backend/main.go`, `frontend/.../fab-chat.component.ts`, `frontend/.../fab-chat.service.ts`, `frontend/app.component.ts`

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
├── fab-chat.component.ts        ← ตัว FAB + toggle logic
├── fab-chat.component.html      ← template: button + chat-window
├── fab-chat.component.scss      ← styles ทั้งหมด
└── fab-chat.service.ts          ← เรียก API / manage conversation state
```

ใส่ `<app-fab-chat>` ใน `app.component.html` ครั้งเดียว — แสดงทุกหน้า

```html
<!-- app.component.html -->
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
| **การวิเคราะห์** | rule-based + LogReg | NLP + SBERT + behavioral signals |
| **เวลา** | ~3-5 นาที | ~5-10 นาที (ขึ้นกับการสนทนา) |
| **ความแม่นยำ** | 85-92% per dim | ขึ้นกับความลึกของการสนทนา |

### ปรัชญาการออกแบบ

> "อย่าถามตรง ๆ ว่าคุณเป็น I หรือ E — ให้สังเกตจากวิธีที่เขาพูดถึงตัวเอง"

AI ใช้บทสนทนาเป็น **ข้อมูลพฤติกรรม** ไม่ใช่คำตอบโดยตรง:

- ผู้ใช้พูดถึง *การอยู่คนเดียว/อยู่กับคนอื่น* → signal E/I
- ผู้ใช้ใช้คำ *รู้สึก/คิดว่า/รู้สึกว่า/วิเคราะห์* → signal T/F
- ผู้ใช้พูดถึง *แผน/ปล่อยไป/ยืดหยุ่น* → signal J/P
- ผู้ใช้เน้น *รายละเอียด/แนวคิดกว้าง* → signal S/N

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
  - validate + save turn ลง MongoDB
  - เรียก AI Service POST /chat/analyze
       │
       ▼
[Python AI Service — port 8000]
  - NLP pipeline:
    1) Tokenize + preprocess (th/en)
    2) SBERT encode → embedding
    3) Behavioral Signal Extractor
    4) Dimension Score Accumulator
    5) AI Reply Generator
  - return: {reply, partial_scores, turn_count}
       │
       ▼
[Go Backend]
  - ถ้า turn_count >= MIN_TURNS และ confidence สูงพอ
    → trigger final analysis
  - return: {reply, show_result_button?}
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

  constructor(private fabChatService: FabChatService) {}

  toggleChat() {
    this.isOpen.update(v => !v);
    // ครั้งแรกที่เปิด → สร้าง chat session + ส่ง greeting
    if (this.isOpen() && this.messages().length === 0) {
      this.startConversation();
    }
  }

  async sendMessage() {
    const text = this.inputText().trim();
    if (!text || this.isLoading()) return;

    // 1. แสดง user bubble ทันที (optimistic UI)
    this.messages.update(msgs => [...msgs, {
      role: 'user',
      text,
      timestamp: new Date()
    }]);
    this.inputText.set('');
    this.isLoading.set(true);

    try {
      // 2. ส่งไป Backend
      const response = await this.fabChatService.sendMessage(text);

      // 3. แสดง AI reply
      this.messages.update(msgs => [...msgs, {
        role: 'ai',
        text: response.reply,
        showResultButton: response.show_result_button,
        timestamp: new Date()
      }]);

      // 4. Auto-scroll ลงล่าง
      this.scrollToBottom();

    } finally {
      this.isLoading.set(false);
    }
  }
}
```

```typescript
// fab-chat.service.ts

interface ChatMessage {
  role: 'user' | 'ai';
  text: string;
  showResultButton?: boolean;
  timestamp: Date;
}

interface SendMessageResponse {
  reply: string;
  show_result_button: boolean;
  session_id: string;
  turn_count: number;
}

@Injectable({ providedIn: 'root' })
export class FabChatService {
  private sessionId = signal<string | null>(null);

  async startSession(): Promise<string> {
    const res = await firstValueFrom(
      this.http.post<{ session_id: string; greeting: string }>(
        '/api/chat/start', {}
      )
    );
    this.sessionId.set(res.session_id);
    return res.greeting;
  }

  async sendMessage(text: string): Promise<SendMessageResponse> {
    return firstValueFrom(
      this.http.post<SendMessageResponse>('/api/chat/message', {
        session_id: this.sessionId(),
        text
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
}
```

---

## 🔀 Step 2 — Go Backend รับ Request และ Orchestrate

### Endpoint ใหม่ที่ต้องเพิ่ม

| Method | Path | ทำอะไร |
|--------|------|---------|
| `POST` | `/api/chat/start` | สร้าง chat session ใหม่ ส่ง greeting กลับ |
| `POST` | `/api/chat/message` | รับ turn ใหม่ → เรียก AI → ส่ง reply กลับ |
| `POST` | `/api/chat/result` | สรุป MBTI จาก session ทั้งหมด |

### Handler Logic — `/api/chat/message`

```go
// backend/handlers/chat.go

func (h *ChatHandler) Message(w http.ResponseWriter, r *http.Request) {
    var req struct {
        SessionID string `json:"session_id"`
        Text      string `json:"text"`
    }
    json.NewDecoder(r.Body).Decode(&req)

    // 1. โหลด session จาก Mongo
    session, err := h.db.GetChatSession(r.Context(), req.SessionID)
    if err != nil { http.Error(w, "session not found", 404); return }

    // 2. เพิ่ม turn ใหม่ลงใน session
    turn := models.ChatTurn{
        Role:      "user",
        Text:      req.Text,
        Timestamp: time.Now(),
    }
    session.Turns = append(session.Turns, turn)

    // 3. ส่งทุก turn ไปให้ AI วิเคราะห์
    aiResp, err := h.aiClient.ChatAnalyze(r.Context(), &ai.ChatAnalyzeRequest{
        SessionID:  req.SessionID,
        Turns:      session.Turns,
        TurnCount:  len(session.Turns),
    })
    if err != nil { http.Error(w, "ai error", 502); return }

    // 4. บันทึก AI reply + partial scores กลับลง Mongo
    session.Turns = append(session.Turns, models.ChatTurn{
        Role:          "ai",
        Text:          aiResp.Reply,
        PartialScores: aiResp.PartialScores,
        Timestamp:     time.Now(),
    })
    h.db.SaveChatSession(r.Context(), session)

    // 5. ตัดสินว่าพร้อมสรุปผลหรือยัง
    //    เงื่อนไข: user พูดอย่างน้อย MIN_USER_TURNS และ confidence > threshold
    userTurns := countUserTurns(session.Turns)
    showResult := userTurns >= MIN_USER_TURNS &&
                  aiResp.Confidence > CONFIDENCE_THRESHOLD

    json.NewEncoder(w).Encode(map[string]any{
        "reply":              aiResp.Reply,
        "show_result_button": showResult,
        "session_id":         req.SessionID,
        "turn_count":         userTurns,
    })
}
```

```go
// constants
const (
    MIN_USER_TURNS       = 5     // ต้องคุยอย่างน้อย 5 ข้อความ
    CONFIDENCE_THRESHOLD = 0.65  // confidence จาก AI ≥ 65%
)
```

### Data Model — Chat Session

```go
// backend/models/models.go (เพิ่ม)

type ChatSession struct {
    ID        string     `bson:"_id"      json:"session_id"`
    CreatedAt time.Time  `bson:"created_at"`
    Turns     []ChatTurn `bson:"turns"    json:"turns"`
    Result    *MBTIResult `bson:"result"  json:"result,omitempty"`
}

type ChatTurn struct {
    Role          string          `bson:"role"    json:"role"`   // "user" | "ai"
    Text          string          `bson:"text"    json:"text"`
    Timestamp     time.Time       `bson:"ts"      json:"timestamp"`
    PartialScores map[string]float64 `bson:"partial_scores,omitempty"`
}
```

---

## 🧠 Step 3 — AI Service: NLP Pipeline (Python)

### Endpoint ใหม่ที่เพิ่มใน `ai-service/app.py`

```python
# ai-service/app.py (เพิ่ม)

@app.post("/chat/analyze")
async def chat_analyze(req: ChatAnalyzeRequest):
    result = chat_predictor.analyze(req.turns, req.turn_count)
    return result

@app.post("/chat/final")
async def chat_final(req: ChatFinalRequest):
    result = chat_predictor.finalize(req.turns)
    return result
```

### `chat_predictor.py` — Pipeline หลัก

```python
# ai-service/chat_predictor.py

import re
from sentence_transformers import SentenceTransformer, util
from behavioral_signals import BehavioralSignalExtractor
from reply_generator import ReplyGenerator

sbert = SentenceTransformer('all-MiniLM-L6-v2')
signal_extractor = BehavioralSignalExtractor(sbert)
reply_gen = ReplyGenerator()

def analyze(turns: list[dict], turn_count: int) -> dict:
    """
    รับ turns ทั้งหมดของ session → วิเคราะห์ → ส่ง reply + partial scores กลับ
    """
    # ดึงเฉพาะ user turns
    user_texts = [t["text"] for t in turns if t["role"] == "user"]
    
    # Step A: SBERT encode ทุก user turn
    embeddings = sbert.encode(user_texts, convert_to_tensor=True)
    
    # Step B: Behavioral Signals
    signals = signal_extractor.extract(user_texts, embeddings)
    # signals = {
    #   "EI": {"E": 0.3, "I": 0.7},
    #   "SN": {"S": 0.4, "N": 0.6},
    #   "TF": {"T": 0.6, "F": 0.4},
    #   "JP": {"J": 0.7, "P": 0.3},
    # }
    
    # Step C: คำนวณ confidence (ยิ่งคุยเยอะ ยิ่งมั่นใจ)
    confidence = compute_confidence(signals, turn_count)
    
    # Step D: เลือก follow-up question ที่จะเพิ่ม signal ที่ยังไม่ชัด
    weakest_dim = find_weakest_dimension(signals)
    reply = reply_gen.generate(weakest_dim, turns[-1]["text"])
    
    return {
        "reply": reply,
        "partial_scores": flatten_scores(signals),
        "confidence": confidence,
    }

def finalize(turns: list[dict]) -> dict:
    """
    สรุปผล MBTI สุดท้ายเมื่อ user กดดูผล
    """
    user_texts = [t["text"] for t in turns if t["role"] == "user"]
    full_text = " ".join(user_texts)
    
    embeddings = sbert.encode(user_texts, convert_to_tensor=True)
    signals = signal_extractor.extract(user_texts, embeddings)
    
    mbti_type = pick_type(signals)
    dimensions = format_dimensions(signals)
    confidence = compute_confidence(signals, len(user_texts))
    
    return {
        "mbti_type": mbti_type,
        "dimensions": dimensions,
        "confidence": confidence,
        "source": "chat_nlp",
    }
```

---

## 🔍 Step 4 — Behavioral Signal Extractor (หัวใจของระบบ)

```python
# ai-service/behavioral_signals.py

class BehavioralSignalExtractor:
    """
    วิเคราะห์ข้อความแต่ละ turn และสกัด MBTI signal ออกมา
    ใช้ 3 วิธีประกอบกัน:
      1) Keyword matching  — คำตรงๆ
      2) SBERT cosine      — ความหมายใกล้เคียง anchor
      3) Linguistic style  — รูปแบบการเขียน
    """

    # ── Anchor phrases สำหรับแต่ละ dimension pole ──────────────────────
    ANCHORS = {
        "E": [
            "I love spending time with people",
            "I get energy from social interactions",
            "I enjoy parties and meeting new people",
            "I like being around others",
        ],
        "I": [
            "I prefer being alone to recharge",
            "I enjoy quiet time by myself",
            "I feel drained after socializing",
            "I need solitude to feel recharged",
        ],
        "S": [
            "I focus on facts and details",
            "I prefer concrete and practical things",
            "I trust what I can see and touch",
        ],
        "N": [
            "I love exploring ideas and possibilities",
            "I think about the big picture",
            "I enjoy abstract concepts and theories",
        ],
        "T": [
            "I make decisions based on logic and analysis",
            "I value objective reasoning over feelings",
            "I prefer facts over emotions",
        ],
        "F": [
            "I care deeply about how others feel",
            "I make decisions based on values and harmony",
            "I prioritize empathy and connection",
        ],
        "J": [
            "I like having a plan and sticking to it",
            "I prefer structure and organization",
            "I feel comfortable with clear deadlines",
        ],
        "P": [
            "I prefer to keep options open",
            "I enjoy spontaneity and flexibility",
            "I adapt to situations as they come",
        ],
    }

    # ── Keyword signals (ไทย + อังกฤษ) ────────────────────────────────
    KEYWORD_SIGNALS = {
        "E": ["เพื่อน", "งานปาร์ตี้", "ชอบคุย", "ไปกับคน", "meet people", "social"],
        "I": ["คนเดียว", "เงียบ", "ชาร์จพลัง", "introvert", "alone", "solitude"],
        "S": ["รายละเอียด", "ข้อเท็จจริง", "ลงมือทำ", "practical", "concrete"],
        "N": ["แนวคิด", "ภาพรวม", "จินตนาการ", "ไอเดีย", "abstract", "vision"],
        "T": ["วิเคราะห์", "ตรรกะ", "เหตุผล", "logic", "analyze", "objective"],
        "F": ["รู้สึก", "ห่วงใย", "empathy", "ความสัมพันธ์", "care", "feeling"],
        "J": ["วางแผน", "ตารางเวลา", "เป้าหมาย", "plan", "organize", "schedule"],
        "P": ["ยืดหยุ่น", "ตามสบาย", "spontaneous", "flexible", "improvise"],
    }

    # ── Linguistic style signals ────────────────────────────────────────
    # (วิเคราะห์โครงสร้างประโยค ไม่ใช่เนื้อหา)
    STYLE_SIGNALS = {
        "J": [
            r"\bก่อน\b.*\bแล้วค่อย\b",     # "วางแผนก่อน แล้วค่อยทำ"
            r"\bต้องการ\b.*\bชัดเจน\b",
            r"first.*then", r"step \d",
        ],
        "P": [
            r"\bแล้วแต่\b", r"\bปล่อยไป\b",
            r"depends", r"it depends", r"go with the flow",
        ],
        "T": [
            r"\bเพราะ\b.*\bดังนั้น\b",       # เหตุผลชัดเจน
            r"\bข้อดี\b.*\bข้อเสีย\b",
            r"because.*therefore", r"pros.*cons",
        ],
        "F": [
            r"\bรู้สึกว่า\b", r"\bทำให้\b.*\bเสียใจ\b",
            r"I feel", r"it makes me", r"emotionally",
        ],
    }

    def __init__(self, sbert_model):
        self.model = sbert_model
        # Pre-encode anchors ครั้งเดียวตอน init (ไม่ต้อง encode ซ้ำ)
        self.anchor_embeddings = {
            pole: self.model.encode(phrases, convert_to_tensor=True).mean(0)
            for pole, phrases in self.ANCHORS.items()
        }

    def extract(self, user_texts: list[str], embeddings) -> dict:
        scores = {pole: 0.0 for pole in "EISNTFJP"}

        for i, text in enumerate(user_texts):
            emb = embeddings[i]

            # ── Method 1: SBERT Cosine (weight: 0.5) ────────────────
            for pole, anchor_emb in self.anchor_embeddings.items():
                cos_sim = float(util.cos_sim(emb, anchor_emb))
                scores[pole] += cos_sim * 0.5

            # ── Method 2: Keyword Matching (weight: 0.3) ─────────────
            text_lower = text.lower()
            for pole, keywords in self.KEYWORD_SIGNALS.items():
                hits = sum(1 for kw in keywords if kw in text_lower)
                scores[pole] += hits * 0.3

            # ── Method 3: Linguistic Style (weight: 0.2) ─────────────
            for pole, patterns in self.STYLE_SIGNALS.items():
                hits = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
                scores[pole] += hits * 0.2

        # Normalize เป็น percentage ต่อ dimension
        return self._normalize(scores)

    def _normalize(self, scores: dict) -> dict:
        result = {}
        for dim, (p1, p2) in [("EI","EI"), ("SN","SN"), ("TF","TF"), ("JP","JP")]:
            a, b = scores[p1[0]], scores[p2[0]]  # ← แก้ให้ชัด
            total = a + b if (a + b) > 0 else 1
            result[dim] = {p1[0]: round(a/total * 100), p2[0]: round(b/total * 100)}
        return result
```

---

## 🤖 Step 5 — Reply Generator (AI ถามต่อ)

AI ไม่ได้แค่รับข้อมูล — มันถาม follow-up เพื่อดึง signal ที่ยังไม่ชัด

```python
# ai-service/reply_generator.py

class ReplyGenerator:
    """
    เลือก follow-up question ที่ target dimension ที่ยังไม่ชัดเจน
    เพื่อสะสม signal ให้ครบทุก dimension ก่อนสรุปผล
    """

    FOLLOW_UP_QUESTIONS = {
        "EI": [
            "ช่วงสุดสัปดาห์คุณชอบทำอะไร? ชอบออกไปข้างนอกหรืออยู่บ้าน?",
            "ถ้าเครียดหรือเหนื่อย คุณมักจะทำอะไรเพื่อผ่อนคลาย?",
            "คุณชอบทำงานคนเดียวหรือทำงานเป็นทีมมากกว่า?",
        ],
        "SN": [
            "เวลาเรียนรู้สิ่งใหม่ คุณชอบเริ่มจากทฤษฎีหรือลงมือทำเลย?",
            "คุณมักจะคิดถึงอนาคตมากกว่าปัจจุบันไหม?",
            "คุณสนใจไอเดียแปลกใหม่หรือสิ่งที่พิสูจน์แล้วว่าใช้ได้?",
        ],
        "TF": [
            "เวลาเพื่อนมาปรึกษาปัญหา คุณมักให้คำแนะนำหรือรับฟังก่อน?",
            "คุณตัดสินใจโดยใช้เหตุผลหรือความรู้สึกเป็นหลัก?",
            "ความยุติธรรมกับความเห็นอกเห็นใจ อะไรสำคัญกว่าสำหรับคุณ?",
        ],
        "JP": [
            "คุณชอบวางแผนล่วงหน้าหรือปล่อยให้สิ่งต่าง ๆ ดำเนินไปเอง?",
            "ถ้าแผนเปลี่ยนกะทันหัน คุณรู้สึกอย่างไร?",
            "คุณชอบมี to-do list หรือแค่จำไว้ในหัว?",
        ],
    }

    GREETING = (
        "สวัสดี! ฉันเป็น AI ที่จะช่วยวิเคราะห์บุคลิกภาพ MBTI ของคุณผ่านการสนทนา "
        "ไม่ต้องตอบแบบทดสอบ แค่เล่าให้ฟังแบบธรรมชาติ 😊 "
        "เริ่มเลยนะ — วันนี้คุณทำอะไรมาบ้าง หรืออยากเล่าอะไรก็ได้เลย!"
    )

    def generate(self, weakest_dim: str, last_user_text: str) -> str:
        import random
        questions = self.FOLLOW_UP_QUESTIONS.get(weakest_dim, [])
        if not questions:
            return "เล่าต่อได้เลยนะ ฉันกำลังฟังอยู่ 😊"
        
        # ตอบรับก่อนแล้วค่อยถามต่อ (ไม่ตัดบทผู้ใช้)
        ack = self._acknowledge(last_user_text)
        follow_up = random.choice(questions)
        return f"{ack} {follow_up}"

    def _acknowledge(self, text: str) -> str:
        """สร้างประโยคตอบรับสั้น ๆ เพื่อให้การสนทนาเป็นธรรมชาติ"""
        acks = [
            "เข้าใจแล้ว!",
            "น่าสนใจมากเลย!",
            "ขอบคุณที่เล่าให้ฟัง",
            "โอเค ฉันเข้าใจคุณมากขึ้นแล้ว",
        ]
        import random
        return random.choice(acks)
```

---

## 📊 Step 6 — Confidence Scoring และการตัดสินใจสรุปผล

```python
# ai-service/chat_predictor.py

def _compute_confidence(signals: dict, user_turn_count: int) -> float:
    """
    confidence = avg clarity × turn_factor

    clarity  = |pole_a - pole_b| / 100  (0 = 50/50, 1 = 100/0)
    turn_factor ≈ 0.625 ที่ 3 turns, ≈ 0.71 ที่ 5 turns, ≈ 1.0 ที่ 12+ turns
    """
    clarity_scores = [abs(list(p.values())[0] - list(p.values())[1]) / 100.0
                      for p in signals.values()]
    avg_clarity = sum(clarity_scores) / len(clarity_scores)
    turn_factor = min(1.0, user_turn_count / 12.0) * 0.5 + 0.5
    return round(avg_clarity * turn_factor, 3)


def _compute_resolved_dims(signals: dict) -> set:
    """
    dimension ที่ clarity > RESOLVED_CLARITY (0.20) = "resolved"
    → ข้ามใน reply_generator ไม่ถามซ้ำ
    """
    RESOLVED_CLARITY = 0.20
    return {
        dim for dim, poles in signals.items()
        if abs(list(poles.values())[0] - list(poles.values())[1]) / 100.0 > RESOLVED_CLARITY
    }
```

### กฎเหล็ก 3 ข้อ (Smart Reply Logic)

```
กฎข้อ 1 — ห้ามถามซ้ำ:
  AI ตรวจ text ใน AI turns ทั้งหมด → exclude คำถามที่เคยส่งไปแล้ว

กฎข้อ 2 — ข้าม dimension ที่ resolved:
  dimension "resolved" = |pole_a - pole_b| > 20 จุด (RESOLVED_CLARITY = 0.20)
  ลำดับที่ถาม: EI → JP → TF → SN (ง่ายก่อน → ยากทีหลัง)

กฎข้อ 3 — หยุดถามและสรุปทันที ถ้า:
  - ครบทุก 4 dimension (all_resolved) → show_result ทันที ไม่รอ MIN_USER_TURNS
  - หรือ user_turns ≥ 3 AND confidence ≥ 0.55

Constants:
  MIN_USER_TURNS    = 3
  CONFIDENCE_THRESHOLD = 0.55
  RESOLVED_CLARITY  = 0.20
```

ผลลัพธ์แสดง **inline** ใน FAB chat window (ไม่ navigate ออกไป)

### ผลลัพธ์แสดง Inline ใน Chat Window

ในการ implement จริง ผลลัพธ์ MBTI แสดงเป็น mini result card **ภายใน FAB chat window** แทนการ navigate ไปหน้าใหม่:

```
┌────────────────────────────┐
│ 🧠 MBTI AI Chat        ✕  │
├────────────────────────────┤
│  [AI bubble: ...]          │
│  [User bubble: ...]        │
│  ┌──────────────────────┐  │  ← Inline Result Card
│  │      I N T J         │  │
│  │   The Architect      │  │
│  │  ความมั่นใจ: 73%     │  │
│  │  E ████░░░░░░ I      │  │
│  │  S ███░░░░░░░ N      │  │
│  │  T ███████░░ F       │  │
│  │  J ████████░ P       │  │
│  │  [🔄 ทำใหม่อีกครั้ง]  │  │
│  └──────────────────────┘  │
└────────────────────────────┘
```

ข้อดีของ inline display: ผู้ใช้เห็นผลทันที ไม่เสีย context — กด "ทำใหม่" เพื่อ reset session

---

## 🗃️ MongoDB — Collection ใหม่

```javascript
// Collection: chat_sessions

{
  "_id": "chat_01HW8...",
  "created_at": ISODate("2025-04-18T03:00:00Z"),
  "turns": [
    {
      "role": "ai",
      "text": "สวัสดี! เล่าให้ฟังหน่อยได้ไหมว่าวันนี้คุณทำอะไร?",
      "ts": ISODate("2025-04-18T03:00:01Z"),
      "partial_scores": null
    },
    {
      "role": "user",
      "text": "วันนี้ผมชอบอยู่บ้านคนเดียว อ่านหนังสือ ไม่ค่อยอยากออกไปไหน",
      "ts": ISODate("2025-04-18T03:00:15Z"),
      "partial_scores": null
    },
    {
      "role": "ai",
      "text": "เข้าใจแล้ว! คุณชอบวางแผนล่วงหน้าหรือปล่อยให้สิ่งต่าง ๆ ดำเนินไปเอง?",
      "ts": ISODate("2025-04-18T03:00:16Z"),
      "partial_scores": { "E": 25, "I": 75, "S": 45, "N": 55, "T": 50, "F": 50, "J": 50, "P": 50 }
    }
    // ...
  ],
  "result": {                           // null จนกว่าจะ finalize
    "mbti_type": "INTJ",
    "dimensions": { "E": 22, "I": 78, "S": 38, "N": 62, "T": 68, "F": 32, "J": 72, "P": 28 },
    "confidence": 0.81,
    "source": "chat_nlp",
    "finalized_at": ISODate("2025-04-18T03:05:00Z")
  }
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

> **Note:** ใช้ single-file component (template + styles inline) ตามสไตล์ project นี้

### Go Backend
| ไฟล์ | สถานะ | สิ่งที่ทำ |
|------|--------|-----------|
| `handlers/chat.go` | ✅ สร้างใหม่ | `ChatStart`, `ChatMessage`, `ChatResult` handlers |
| `models/models.go` | ✅ แก้ไข | เพิ่ม `ChatSession`, `ChatTurn` struct |
| `db/mongo.go` | ✅ แก้ไข | `chatSessions` collection + `CreateChatSession`, `GetChatSession`, `AppendChatTurns` |
| `ai/client.go` | ✅ แก้ไข | เพิ่ม `ChatAnalyze()`, `ChatFinal()` + refactor ใช้ `post()` helper |
| `main.go` | ✅ แก้ไข | Register `/api/chat/start`, `/api/chat/message`, `/api/chat/result` |

### Python AI Service
| ไฟล์ | สถานะ | สิ่งที่ทำ |
|------|--------|-----------|
| `chat_predictor.py` | ✅ สร้างใหม่ | `analyze()` + `finalize()` |
| `behavioral_signals.py` | ✅ สร้างใหม่ | `BehavioralSignalExtractor` — SBERT + keyword + style |
| `reply_generator.py` | ✅ สร้างใหม่ | `generate_reply()` — follow-up questions ต่อ dimension |
| `app.py` | ✅ แก้ไข | `/chat/analyze`, `/chat/final` endpoints + Pydantic models |

---

## 🧪 ทดสอบ

```bash
# 1. Start chat session
curl -X POST http://localhost:8080/api/chat/start \
  -H "Content-Type: application/json" \
  -d '{}' | jq .

# 2. ส่งข้อความ (replace CHAT_SID)
CSID=chat_xxx
curl -X POST http://localhost:8080/api/chat/message \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$CSID\",\"text\":\"วันนี้ผมชอบอยู่บ้านอ่านหนังสือคนเดียว\"}" | jq .

# 3. ดูผลเมื่อ confidence สูงพอ
curl -X POST http://localhost:8080/api/chat/result \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$CSID\"}" | jq .

# ทดสอบ AI โดยตรง
curl -X POST http://localhost:8000/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "turns": [
      {"role": "user", "text": "ผมชอบอยู่คนเดียว คิดคนเดียว ไม่ค่อยชอบงานสังสรรค์"}
    ],
    "turn_count": 1
  }' | jq .
```

---

## 🎓 สรุป Logic ทั้งระบบ

```
User พิมพ์ข้อความ (free-text)
       ↓
Angular: เก็บ + แสดง bubble + ส่ง POST /api/chat/message
       ↓
Go: บันทึก turn → ส่งทุก turn ไป AI
       ↓
Python AI Pipeline:
  ① SBERT encode ทุก user turn → 384-dim vectors
  ② cosine similarity เทียบ anchor ทุก dimension pole (E,I,S,N,T,F,J,P)
  ③ keyword scan ภาษาไทย/อังกฤษ เพิ่ม score
  ④ regex pattern ดู linguistic style
  ⑤ normalize → {EI: {E:30, I:70}, SN: {S:45, N:55}, ...}
  ⑥ compute confidence = clarity × turn_factor
  ⑦ หา weakest dim → เลือก follow-up question
  ⑧ return reply + partial_scores + confidence
       ↓
Go: ถ้า turns≥5 AND confidence≥0.65 → set show_result_button=true
       ↓
Angular: แสดง reply + (ถ้าพร้อม) ปุ่ม "ดูผลลัพธ์ MBTI ของคุณ"
       ↓
User กด "ดูผลลัพธ์"
       ↓
Go → AI /chat/final → MBTI type + dimensions → บันทึก + ส่ง Angular
       ↓
Angular: แสดงผลลัพธ์ใน chat window (หรือเปิดหน้า result)
```

---

👉 เกี่ยวข้องกับ: [02-ai-model.md](./02-ai-model.md) — model ที่ใช้, [03-api.md](./03-api.md) — API เดิม, [04-code-walkthrough.md](./04-code-walkthrough.md) — ไล่โค้ด
