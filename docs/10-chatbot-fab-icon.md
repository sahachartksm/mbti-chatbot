# 10 — Chatbot MBTI Interactive Icon (FAB Chat Mode)

> ระบบนี้ใช้ **Hybrid Approach**: ถามคำถาม MBTI ตายตัว 10 ข้อจาก Fixed Question Bank
> โดย AI ทำหน้าที่วิเคราะห์เนื้อหาคำตอบและอัปเดต scores เท่านั้น — ไม่สร้างคำถามเอง

> **Implementation Status:** ✅ Implemented & Updated (2026-04-24)
> ไฟล์ที่สร้าง/แก้ไข: `ai-service/gemini_client.py`, `ai-service/chat_predictor.py`, `ai-service/app.py`, `ai-service/mbti_questions.py`, `ai-service/requirements.txt`, `ai-service/.env.example`, `backend/ai/client.go`, `backend/handlers/chat.go`, `frontend/.../fab-chat.component.ts`, `frontend/.../fab-chat.service.ts`

---

## 🎯 ภาพรวม Feature

```
┌─────────────────────────────────────────────────────────┐
│                  Browser (Angular SPA)                   │
│  ┌──────────────────────────────────────┐               │
│  │  🧠 MBTI AI Chat        ⚙️  ✕        │               │
│  ├──────────────────────────────────────┤               │
│  │ [Settings Panel — API Key input]     │  ← toggle ⚙️  │
│  ├──────────────────────────────────────┤               │
│  │  AI: สวัสดี! เล่าให้ฟังหน่อยได้ไหม │               │
│  │  User: [วางแผนเป๊ะๆ]  ← Quick Reply │               │
│  │  AI: เข้าใจแล้ว! ข้อต่อไป...        │               │
│  │  ...                                 │               │
│  │  ┌────────────────────────────────┐  │               │
│  │  │  Inline Result Card (INTJ ...)  │  │               │
│  │  └────────────────────────────────┘  │               │
│  ├──────────────────────────────────────┤               │
│  │ ✅ วิเคราะห์เสร็จแล้ว               │  ← complete   │
│  │ [✨ ดูผลลัพธ์ MBTI ของคุณ]         │     footer    │
│  └──────────────────────────────────────┘               │
│                                                          │
│                                     ┌──────┐            │
│                                     │  🧠  │  ← FAB    │
│                                     └──────┘            │
└─────────────────────────────────────────────────────────┘
```

---

## 🖱️ UI/UX — Floating Action Button (FAB)

### Angular Component Structure

```
frontend/src/app/components/fab-chat/
└── fab-chat.component.ts   ← single-file: FAB + chat window + styles (inline)

frontend/src/app/services/
└── fab-chat.service.ts     ← HTTP calls + session/API key state (Signal)
```

> ใช้ single-file component (template + styles inline ใน `.ts`) — ไม่มี `.html` / `.scss` แยก

ใส่ `<app-fab-chat />` ใน `app.component.ts` ครั้งเดียว — แสดงทุก route

### 3 States ของ Chat Footer

| สถานะ | เงื่อนไข | แสดง |
|--------|----------|------|
| **กำลังคุย** | `!chatCompleted && !mbtiResult` | Input bar + ปุ่มส่ง + Quick Reply buttons |
| **วิเคราะห์เสร็จ** | `chatCompleted && !mbtiResult` | ปุ่ม "✨ ดูผลลัพธ์ MBTI" เต็มความกว้าง |
| **แสดงผลแล้ว** | `mbtiResult` | Inline Result Card (input ซ่อน) |

### Settings Panel (API Key)

กดไอคอน ⚙️ ใน header เพื่อเปิด settings panel:
- ช่อง input (type=password) สำหรับกรอก Gemini API Key
- บันทึกลง `localStorage` ด้วย key `mbti_gemini_api_key`
- แสดง 8 ตัวอักษรแรกของ key ที่บันทึกอยู่ พร้อมปุ่มลบ
- ถ้าไม่กรอก → ระบบ fallback ใช้ key จาก `.env` ของ server

---

## 💬 Core Concept — Hybrid Approach

### เปรียบเทียบ 3 โหมด

| | โหมดเดิม (Quiz) | Free-text Chat | **Hybrid (ปัจจุบัน)** |
|--|-----------------|----------------|-----------------------|
| **วิธีตอบ** | เลือก a/b/c ทีละข้อ | พิมพ์คุยอิสระ | **ปุ่ม Quick Reply (ตายตัว)** |
| **คำถาม** | 20 ข้อ fixed | AI สร้างเอง | **10 ข้อ fixed จาก Question Bank** |
| **บทบาท AI** | — | สร้างคำถาม + วิเคราะห์ | **วิเคราะห์เนื้อหาเท่านั้น** |
| **Engine หลัก** | rule-based + LogReg | Gemini (free-form) | **Gemini (analysis only)** |
| **Engine สำรอง** | — | SBERT + keyword | SBERT + keyword |
| **จำนวนรอบ** | 20 ข้อ (คงที่) | ≥5 turns | **10 คำถาม (คงที่)** |
| **เกณฑ์สรุปผล** | ครบ 20 ข้อ | AI + keyword | **ครบ 10 คำถาม → show_result** |

### Hybrid Approach ทำงานอย่างไร

```
Python เลือกคำถาม (Fixed Question Bank)
       ↓
User ตอบผ่านปุ่ม Quick Reply หรือพิมพ์เอง
       ↓
Gemini วิเคราะห์เฉพาะเนื้อหาคำตอบ:
  - is_valid (ตอบถูกต้องไหม)
  - acknowledge (ตอบรับสั้นๆ 1-2 ประโยค)
  - partial_scores (E/I/S/N/T/F/J/P)
  - dimension_confidence
       ↓
Python ประกอบ reply = acknowledge + MBTI_QUESTIONS[next_idx]["reply"]
       ↓
suggested_choices = MBTI_QUESTIONS[next_idx]["suggested_choices"]
```

---

## ⚙️ Technical Logic — Data Flow รายขั้น

```
User พิมพ์ข้อความ (หรือกดปุ่ม Quick Reply)
       │
       ▼
[Angular FAB Component]
  - เก็บ conversation history (local state)
  - ส่ง POST /api/chat/message  {session_id, text, api_key?}
       │
       ▼
[Go Backend — /api/chat/message]
  - validate request
  - นับ userTurnCount (valid turns ที่บันทึกแล้ว + turn ใหม่)
  - ส่ง full history ไป AI Service  POST /chat/analyze
       │
       ▼
[Python AI Service — /chat/analyze]
  ┌── Layer 0: Quick Reply Bypass ──────────────────────────┐
  │  ถ้า user_text ตรงกับ suggested_choices ของคำถามก่อนหน้า │
  │  → ข้ามการ validate ทั้งหมด (is_choice_bypass = True)   │
  └─────────────────────────────────────────────────────────┘
  ┌── Layer 1: Python Gibberish Gate ───────────────────────┐
  │  validate_user_input() — ตรวจ keyboard mashing          │
  │  (ไทย/QWERTY home row, สระซ้อน, พยัญชนะต่อกัน ≥5)     │
  │  → False: return redirect + repeat คำถามเดิม           │
  └─────────────────────────────────────────────────────────┘
  ┌── Primary (ถ้ามี GEMINI_API_KEY) ───────────────────────┐
  │  Gemini วิเคราะห์เนื้อหาเท่านั้น:                      │
  │  → is_valid, acknowledge, partial_scores, dim_conf      │
  │  Python ประกอบ reply = acknowledge + MBTI_QUESTIONS[n]  │
  │  suggested_choices = MBTI_QUESTIONS[n]["suggested_choices"]│
  └─────────────────────────────────────────────────────────┘
  ┌── Fallback (ไม่มี Gemini) ──────────────────────────────┐
  │  BehavioralSignalExtractor: SBERT + keyword + regex     │
  │  คำนวณ partial_scores + dimension_confidence            │
  └─────────────────────────────────────────────────────────┘
  ┌── show_result Decision ─────────────────────────────────┐
  │  next_q_idx = user_turn_count - 1                       │
  │  show_result = True ถ้า next_q_idx >= 10                │
  │  (ตอบครบ 10 คำถามแล้ว → Python บังคับ)                 │
  └─────────────────────────────────────────────────────────┘
  ┌── Final Safety Gate (app.py) ───────────────────────────┐
  │  ถ้า reply มีคำว่า "ดูผล"/"วิเคราะห์ครบ" ฯลฯ          │
  │  แต่ show_result ยังเป็น false → บังคับ true            │
  └─────────────────────────────────────────────────────────┘
  - return: {is_valid, reply, suggested_choices, partial_scores,
             dimension_confidence, confidence, show_result}
       │
       ▼
[Go Backend]
  - ถ้า is_valid=true → บันทึก userTurn + aiTurn ลง MongoDB
  - ถ้า is_valid=false → บันทึกเฉพาะ aiTurn (redirect) — ไม่บันทึก userTurn
  - ส่ง {reply, show_result_button, is_completed, is_valid, turn_count}
       │
       ▼
[Angular]
  - แสดง reply ใน chat bubble + Quick Reply buttons
  - ถ้า is_completed=true → chatCompleted.set(true)
    → ซ่อน input bar
    → แสดงปุ่ม "✨ ดูผลลัพธ์ MBTI ของคุณ"
       │
       ▼ (user กดปุ่ม)
[Angular → Go → AI /chat/final]
  → Gemini สรุป MBTI type + cognitive_stack + reasoning
  → แสดง inline result card
```

---

## 📥 Angular — FAB Component

### Signals & State

```typescript
// fab-chat.component.ts

export class FabChatComponent implements AfterViewChecked {
  readonly fabChat = inject(FabChatService);

  isOpen          = signal(false);
  messages        = signal<ChatMessage[]>([]);
  inputText       = '';
  isStarting      = signal(false);
  isLoading       = signal(false);
  isLoadingResult = signal(false);
  mbtiResult      = signal<Result | null>(null);
  error           = signal<string | null>(null);
  chatCompleted   = signal(false);      // ← ระดับ component (ไม่ใช่ per-message)
  showSettings    = signal(false);      // ← settings panel toggle
  apiKeyDraft     = '';
  apiKeySaved     = signal(false);
}
```

### Template — Footer Logic

```html
<!-- ─── Complete Footer: แสดงเมื่อแชทจบ ─── -->
@if (chatCompleted() && !mbtiResult()) {
  <div class="complete-footer">
    <div class="complete-hint">✅ วิเคราะห์บุคลิกภาพเสร็จแล้ว</div>
    <button class="view-result-btn" (click)="showResult()" [disabled]="isLoadingResult()">
      @if (isLoadingResult()) {
        <span class="btn-spinner"></span> กำลังประมวลผล...
      } @else {
        ✨ ดูผลลัพธ์ MBTI ของคุณ
      }
    </button>
  </div>
}

<!-- ─── Input Bar: แสดงเฉพาะขณะยังคุยอยู่ ─── -->
@if (!chatCompleted() && !mbtiResult()) {
  <div class="input-bar">
    <input class="chat-input" [(ngModel)]="inputText" (keyup.enter)="sendMessage()" />
    <button class="send-btn" (click)="sendMessage()">ส่ง</button>
  </div>
}
```

### sendMessage() — จุด set chatCompleted

```typescript
async sendMessage() {
  const resp = await this.fabChat.sendMessage(text);
  this.messages.update(msgs => [...msgs, {
    role: 'ai',
    text: resp.reply,
    timestamp: new Date(),
  }]);
  // is_completed คือชื่อ canonical; show_result_button คือ legacy alias
  if (resp.is_completed || resp.show_result_button) {
    console.log('[FabChat] Chat completed — showing result button');
    this.chatCompleted.set(true);
  }
}
```

### restart()

```typescript
restart() {
  this.messages.set([]);
  this.mbtiResult.set(null);
  this.error.set(null);
  this.chatCompleted.set(false);   // ← reset completion state
  this.fabChat.reset();
  this.startConversation();
}
```

---

## 🔌 Angular — FAB Service

```typescript
// fab-chat.service.ts

export interface ChatMessage {
  role: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

export interface SendMessageResponse {
  reply: string;
  is_completed: boolean;      // canonical — แชทจบแล้ว แสดงปุ่มดูผล
  show_result_button: boolean; // legacy alias
  is_valid: boolean;
  session_id: string;
  turn_count: number;
}

const STORAGE_KEY = 'mbti_gemini_api_key';

@Injectable({ providedIn: 'root' })
export class FabChatService {
  sessionId = signal<string | null>(null);
  apiKey    = signal<string>(localStorage.getItem(STORAGE_KEY) ?? '');

  saveApiKey(key: string) {
    const trimmed = key.trim();
    this.apiKey.set(trimmed);
    trimmed
      ? localStorage.setItem(STORAGE_KEY, trimmed)
      : localStorage.removeItem(STORAGE_KEY);
  }

  async sendMessage(text: string): Promise<SendMessageResponse> {
    const body: Record<string, unknown> = { session_id: this.sessionId(), text };
    if (this.apiKey()) body['api_key'] = this.apiKey();
    const resp = await firstValueFrom(
      this.http.post<SendMessageResponse>(`${this.base}/chat/message`, body)
    );
    console.log('[FabChat] /chat/message response:', resp);  // Debug: F12 → Console
    return resp;
  }

  async getResult(): Promise<Result> {
    const body: Record<string, unknown> = { session_id: this.sessionId() };
    if (this.apiKey()) body['api_key'] = this.apiKey();
    return firstValueFrom(this.http.post<Result>(`${this.base}/chat/result`, body));
  }
}
```

---

## 🔀 Go Backend

### Endpoints

| Method | Path | ทำอะไร |
|--------|------|---------|
| `POST` | `/api/chat/start` | สร้าง session + บันทึก greeting turn |
| `POST` | `/api/chat/message` | รับ turn → เรียก AI → บันทึก (valid turns เท่านั้น) → ส่ง reply |
| `POST` | `/api/chat/result` | โหลด session → AI finalize → บันทึก result |

### Request/Response Structs (`ai/client.go`)

```go
type ChatAnalyzeRequest struct {
    SessionID     string        `json:"session_id"`
    Turns         []ChatTurnDTO `json:"turns"`
    UserTurnCount int           `json:"user_turn_count"`
    APIKey        string        `json:"api_key,omitempty"`
}

type ChatAnalyzeResponse struct {
    IsValid       bool           `json:"is_valid"`
    Reply         string         `json:"reply"`
    PartialScores map[string]int `json:"partial_scores"`
    Confidence    float64        `json:"confidence"`
    ShowResult    bool           `json:"show_result"`
}
```

### Handler Logic — `/api/chat/message` (`handlers/chat.go`)

```go
func (h *Handler) ChatMessage(w http.ResponseWriter, r *http.Request) {
    var req chatMsgReq  // { session_id, text, api_key? }

    // 1. โหลด session จาก MongoDB
    sess, _ := h.Repo.GetChatSession(r.Context(), req.SessionID)

    // 2. นับ user turns จาก valid turns ที่บันทึกไว้ (รวม turn ใหม่)
    userTurnCount := 1
    for _, t := range sess.Turns {
        if t.Role == "user" { userTurnCount++ }
    }

    // 3. ส่ง full history + api_key ไป AI Service
    aiResp, _ := h.AI.ChatAnalyze(ctx, ai.ChatAnalyzeRequest{
        SessionID:     req.SessionID,
        Turns:         dtos,
        UserTurnCount: userTurnCount,
        APIKey:        req.APIKey,
    })

    // 4. บันทึกเฉพาะ valid turns — invalid turns ไม่บันทึกลง history
    turnsToSave := []models.ChatTurn{aiTurn}
    if aiResp.IsValid {
        turnsToSave = []models.ChatTurn{userTurn, aiTurn}
    }
    h.Repo.AppendChatTurns(r.Context(), req.SessionID, turnsToSave)

    // 5. ส่ง response กลับ Angular
    writeJSON(w, 200, map[string]any{
        "reply":              aiResp.Reply,
        "show_result_button": aiResp.ShowResult,  // legacy
        "is_completed":       aiResp.ShowResult,  // canonical
        "is_valid":           aiResp.IsValid,
        "session_id":         req.SessionID,
        "turn_count":         userTurnCount,
    })
}
```

> **สำคัญ:** `show_result_button` / `is_completed` มาจาก AI service โดยตรง — Go ไม่คำนวณซ้ำ

---

## 🧠 Python AI Service

### `mbti_questions.py` — Fixed Question Bank (10 ข้อ)

```python
# ai-service/mbti_questions.py

MBTI_QUESTIONS = [
    # Index 0 — EI: Energy source after social interaction
    { "dimension": "EI",
      "reply": "หลังจากใช้เวลากับคนอื่นทั้งวัน คุณมักรู้สึกอย่างไร — พลังงานเพิ่มขึ้น หรือ อยากกลับไปพักคนเดียว?",
      "suggested_choices": ["พลังงานเพิ่มขึ้น", "อยากกลับไปพักคนเดียว", "แล้วแต่สถานการณ์"] },
    # Index 1 — JP: Planning vs spontaneous travel
    # Index 2 — TF: Reaction to unexpected plan changes
    # Index 3 — TF: Helping friends (Fe vs Te)
    # Index 4 — EI: Decision-making style
    # Index 5 — SN: Learning style
    # Index 6 — SN: Memory style (Si vs Ni)
    # Index 7 — JP: Daily structure
    # Index 8 — TF: Conflict resolution
    # Index 9 — SN: Work autonomy
]

TOTAL_QUESTIONS = len(MBTI_QUESTIONS)  # = 10

COMPLETE_MESSAGE = (
    "ขอบคุณที่ตอบทุกคำถามนะครับ 😊 "
    "ตอนนี้ฉันวิเคราะห์บุคลิกภาพของคุณครบแล้ว — "
    "กดปุ่มด้านล่างเพื่อดูผล MBTI ของคุณได้เลยครับ! ✨"
)
```

ครอบคลุม dimension: EI(×2), SN(×3), TF(×3), JP(×2) รวม 10 ข้อ

### `app.py` — Endpoints + Final Safety Gate

```python
# ai-service/app.py  (v2.0.0)

# Keywords ที่บ่งชี้ว่าการวิเคราะห์เสร็จสิ้น (last resort)
_SHOW_RESULT_GATE: tuple = (
    "ดูผล", "กดปุ่ม", "วิเคราะห์ครบ", "วิเคราะห์เสร็จ",
    "ผลลัพธ์", "ผลการวิเคราะห์", "ดูผลลัพธ์", "สรุปผล",
)

@app.post("/chat/analyze")
def chat_analyze(req: ChatAnalyzeRequest):
    turns = [{"role": t.role, "text": t.text} for t in req.turns]
    result = chat_predictor.analyze(turns, req.user_turn_count, api_key=req.api_key)

    # ── Final Safety Gate ──────────────────────────────────────────────
    if not result.get("show_result", False):
        reply_lower = str(result.get("reply", "")).lower()
        if any(kw in reply_lower for kw in _SHOW_RESULT_GATE):
            result["show_result"] = True

    return result
```

### `chat_predictor.py` — Fixed Question Routing + Validation

```python
# ai-service/chat_predictor.py

def analyze(turns, user_turn_count, api_key=None) -> Dict:
    next_q_idx   = user_turn_count - 1   # คำถามถัดไปที่จะแสดง
    repeat_q_idx = max(0, next_q_idx - 1) # คำถามที่ต้องทวนซ้ำหาก invalid

    last_user_text = ...

    # ── Quick Reply Bypass ────────────────────────────────────────────
    # ถ้า user text ตรงกับ suggested_choices ของคำถามก่อนหน้า → valid เสมอ
    prev_q_idx       = user_turn_count - 2
    is_choice_bypass = (
        0 <= prev_q_idx < TOTAL_QUESTIONS
        and last_user_text.strip() in MBTI_QUESTIONS[prev_q_idx]["suggested_choices"]
    )

    # ── Python Gibberish Gate (ข้ามถ้า bypass) ───────────────────────
    if not is_choice_bypass and not validate_user_input(last_user_text):
        # ทวนคำถามเดิม, ไม่นับ turn
        return { "is_valid": False, "reply": "...", ... }

    # ── Gemini Analysis ───────────────────────────────────────────────
    gemini_result = gemini_client.chat_analyze(turns, user_turn_count, api_key)
    # is_choice_bypass overrides Gemini's is_valid decision

    # ── show_result: ครบ 10 คำถาม (Python บังคับ ไม่ขึ้นกับ AI) ──────
    if next_q_idx >= TOTAL_QUESTIONS:
        return {
            "is_valid": True,
            "reply": COMPLETE_MESSAGE,
            "suggested_choices": [],
            "show_result": True,
            ...
        }

    # ── Valid: combine acknowledge + next fixed question ──────────────
    q     = MBTI_QUESTIONS[next_q_idx]
    reply = (acknowledge + "\n\n" + q["reply"]) if acknowledge else q["reply"]
    return {
        "is_valid":          True,
        "reply":             reply,
        "suggested_choices": q["suggested_choices"],
        "show_result":       False,
        ...
    }
```

### `gemini_client.py` — ANALYZE_SYSTEM_PROMPT (Hybrid Mode)

```
หน้าที่ของ Gemini: วิเคราะห์ข้อความที่ผู้ใช้ตอบมาเท่านั้น

⛔ ห้ามสร้างคำถามใหม่ — ระบบจัดการคำถามเองแล้ว
⛔ ห้ามสร้าง suggested_choices — ระบบจัดการตัวเลือกเองแล้ว

สิ่งที่ต้องทำทุก turn:
1. ประเมิน is_valid ของข้อความล่าสุด
   🔑 CRITICAL: วลีสั้นๆ แบบ choice-style → is_valid: true เสมอ

2. เขียน acknowledge (1-2 ประโยค ตอบรับ ห้ามถามคำถามใหม่)

3. อัปเดต partial_scores และ dimension_confidence

Output JSON:
{
  "reasoning": "...",
  "is_valid": true/false,
  "acknowledge": "...",
  "partial_scores": { "E": 0-100, "I": 0-100, ... },
  "dimension_confidence": { "EI": 0.0-1.0, ... },
  "confidence": 0.0-1.0,
  "behavioral_signals": "..."
}
```

### `gemini_client.py` — FINALIZE_SYSTEM_PROMPT (Confidence Rules)

```
━━━ CRITICAL RULE FOR CONFIDENCE SCORE ━━━

ผู้ใช้ตอบผ่านปุ่ม Quick Reply ที่ออกแบบมาวัด MBTI อย่างเป็นระบบ
ห้ามหักคะแนน confidence เพราะคำตอบสั้น

กฎ confidence (int 0-100):
  - pole ชนะ > 65%  → confidence = 80-95
  - pole ชนะ 51-65% → confidence = 65-79
  - ห้ามต่ำกว่า 60 หากตอบครบ 10 คำถาม
  - ส่งเป็น int เสมอ (85 ไม่ใช่ 0.85)
```

### `chat_finalize()` — Post-processing Confidence

```python
def chat_finalize(turns, api_key=None) -> Optional[Dict]:
    result = _call(model_finalize, prompt)
    result["dimensions"] = _fix_pairs(result["dimensions"])

    # Normalize confidence → int (0-100) + minimum floor
    conf = result.get("confidence", 60)
    if isinstance(conf, float) and conf <= 1.0:
        conf = round(conf * 100)   # 0.85 → 85
    conf = int(conf)
    user_turn_count = len([t for t in turns if t["role"] == "user"])
    if user_turn_count >= MIN_USER_TURNS_FOR_RESULT:
        conf = max(60, conf)       # floor 60 ถ้าตอบครบ
    result["confidence"] = max(0, min(100, conf))
    return result
```

---

## 🛡️ Answer Validation System

### ลำดับการตรวจสอบ

```
1. Quick Reply Bypass (ข้าม validate ทั้งหมด)
   ↓ (ไม่ใช่ quick reply)
2. Python Gibberish Gate — validate_user_input()
   ↓ (ผ่าน)
3. Gemini is_valid check (override ถ้า is_choice_bypass=True)
```

### `validate_user_input()` — ตรวจ Keyboard Mashing

| เงื่อนไข | ผล |
|----------|-----|
| ความยาว < 2 ตัวอักษร | False |
| อยู่ใน `_INVALID_TOKENS` | False |
| อักขระซ้ำ ≥ 4 ครั้งติดกัน (`aaaa`) | False |
| unique chars ≤ 2 และยาว > 5 | False |
| Thai chars ไม่มีสระเลย (≥ 4 ตัว) | False |
| ตัวอักษรทั้งหมดอยู่ใน home row เดียว | False |
| พยัญชนะต่อกัน ≥ 5 ตัว (ไม่มีสระคั่น) | False |
| เริ่มต้นด้วยสระ (`ะ`, `า`, `ิ`, ฯลฯ) | False |
| อื่นๆ | True |

### ผลของ `is_valid = false`

```
Python Gate: return redirect + repeat คำถามเดิม (repeat_q_idx)
Gemini Gate: acknowledge = "", Python ใช้ repeat คำถามเดิม
Go: บันทึกเฉพาะ aiTurn (redirect) — ไม่บันทึก userTurn ลง MongoDB
Frontend: แสดง redirect message, turn_count ไม่นับ
```

---

## 📊 Thresholds

| ค่า | Gemini Mode | Fallback Mode |
|-----|-------------|---------------|
| `MIN_USER_TURNS_FOR_RESULT` | **10** (`gemini_client.py`) | **10** (`chat_predictor.py`) |
| `TOTAL_QUESTIONS` | 10 (`mbti_questions.py`) | 10 |
| `show_result` trigger | ครบ 10 คำถาม (Python) | ครบ 10 คำถาม |
| `DIM_CONFIDENCE_THRESHOLD` | 0.80 (ใช้ใน fallback) | 0.80 |
| `RESOLVED_CLARITY` | — | 0.30 (clarity per dim) |
| `confidence` floor (finalize) | **60** (ถ้าตอบครบ 10 ข้อ) | — |

---

## 🔑 API Key Management

### Priority Order

```
1. User key จาก Frontend (ส่งมาใน request body เป็น "api_key")
2. Server key จาก ai-service/.env  →  GEMINI_API_KEY=...
3. ไม่มีทั้งคู่  →  Fallback mode (keyword/SBERT)
```

### Flow ของ User Key

```
Angular (localStorage)
  → FabChatService.sendMessage() → body["api_key"] = key
  → Go ChatMessage handler → req.APIKey
  → AI Service ChatAnalyzeRequest → api_key field
  → gemini_client._models_for_key(key)
    → genai.configure(api_key=key)  [under threading.Lock]
    → create temporary model instances
    → restore server key after call
```

---

## 📋 JSON Response Schemas

### `/chat/analyze` Response

```json
{
  "is_valid": true,
  "reply": "เข้าใจแล้ว! ตอนนี้ขอถามข้อต่อไปนะ...\n\nเวลาไปเที่ยว คุณชอบแบบไหน — วางแผนเป๊ะๆ หรือ ด้นสดหน้างาน?",
  "suggested_choices": ["วางแผนเป๊ะๆ", "ด้นสดหน้างาน", "ผสมผสาน"],
  "partial_scores": {
    "E": 30, "I": 70,
    "S": 45, "N": 55,
    "T": 65, "F": 35,
    "J": 60, "P": 40
  },
  "dimension_confidence": {
    "EI": 0.85, "SN": 0.32, "TF": 0.72, "JP": 0.61
  },
  "confidence": 0.625,
  "show_result": false,
  "behavioral_signals": "ตอบสั้น, ใช้คำรูปธรรม"
}
```

เมื่อ `is_valid = false`:
```json
{
  "is_valid": false,
  "reply": "ระบบตรวจพบข้อความที่ไม่สามารถประเมินผลได้...\n\n[ทวนคำถามเดิม]",
  "suggested_choices": ["ตัวเลือกเดิม", ...],
  "show_result": false
}
```

เมื่อตอบครบ 10 คำถาม:
```json
{
  "is_valid": true,
  "reply": "ขอบคุณที่ตอบทุกคำถามนะครับ 😊 ... กดปุ่มด้านล่าง ✨",
  "suggested_choices": [],
  "show_result": true
}
```

### `/api/chat/message` Response (Go → Angular)

```json
{
  "reply": "เข้าใจแล้ว! ...",
  "show_result_button": false,
  "is_completed": false,
  "is_valid": true,
  "session_id": "chat_01ARZ...",
  "turn_count": 3
}
```

เมื่อแชทเสร็จ (ครบ 10 คำถาม):
```json
{
  "reply": "ขอบคุณที่ตอบทุกคำถาม ... ✨",
  "show_result_button": true,
  "is_completed": true,
  "is_valid": true,
  "turn_count": 11
}
```

### `/chat/final` Response

> `confidence` เป็น **int (0-100)** เสมอ — ไม่ใช่ float

```json
{
  "mbti_type": "INTJ",
  "nickname": "The Architect (สถาปนิก)",
  "cognitive_stack": "Ni > Te > Fi > Se",
  "dimensions": {"E": 25, "I": 75, "S": 35, "N": 65, "T": 68, "F": 32, "J": 72, "P": 28},
  "dimension_confidence": {"EI": 0.88, "SN": 0.85, "TF": 0.82, "JP": 0.90},
  "confidence": 86,
  "description": "คุณมีวิสัยทัศน์ที่ชัดเจน...",
  "reasoning": "1. คุณเลือก 'คิดคนเดียวก่อน'... 2. เลือก 'เข้าใจภาพรวมก่อน'...",
  "behavioral_evidence": "ตอบด้วย choice-style, ชัดเจน ไม่ลังเล",
  "strengths": ["...", "...", "...", "..."],
  "weaknesses": ["...", "...", "..."],
  "careers": ["...", "...", "...", "..."],
  "famous_people": ["...", "..."],
  "compatible_types": ["ENFP", "ENTP"]
}
```

---

## 🗃️ MongoDB — chat_sessions

```javascript
{
  "_id": "chat_01HW8...",
  "created_at": ISODate("2026-04-24T03:00:00Z"),
  "turns": [
    {
      "role": "ai",
      "text": "สวัสดี! ฉันคือ AI ที่จะช่วยวิเคราะห์บุคลิกภาพ MBTI...",
      "ts": ISODate("..."),
      "partial_scores": null
    },
    // ← user turns ที่ is_valid=false จะ ไม่ถูกบันทึก
    {
      "role": "user",
      "text": "อยากกลับไปพักคนเดียว",   // ← Quick Reply choice
      "ts": ISODate("..."),
      "partial_scores": null
    },
    {
      "role": "ai",
      "text": "เข้าใจแล้ว! ข้อต่อไป: เวลาไปเที่ยว...",
      "ts": ISODate("..."),
      "partial_scores": {"E": 25, "I": 75, ...}
    }
    // ... ครบ 10 user turns → show_result = true
  ]
}
```

---

## 🔧 ไฟล์ที่เพิ่ม/แก้ (Implemented ✅)

### Angular (Frontend)
| ไฟล์ | สิ่งที่ทำ |
|------|-----------|
| `components/fab-chat/fab-chat.component.ts` | FAB + chat window + Quick Reply buttons + settings panel + completion footer + inline result card |
| `services/fab-chat.service.ts` | HTTP calls + session/apiKey state (signal) + localStorage + console.log debug |
| `app.component.ts` | import FabChatComponent + `<app-fab-chat />` |

### Go Backend
| ไฟล์ | สิ่งที่ทำ |
|------|-----------|
| `handlers/chat.go` | `ChatStart`, `ChatMessage`, `ChatResult` — conditional save (is_valid), forward api_key, ส่ง is_completed |
| `ai/client.go` | เพิ่ม `APIKey`, `IsValid` ใน structs |
| `models/models.go` | `ChatSession`, `ChatTurn` struct |
| `db/mongo.go` | `chat_sessions` collection CRUD |
| `main.go` | Register `/api/chat/*` routes |

### Python AI Service
| ไฟล์ | สิ่งที่ทำ |
|------|-----------|
| `mbti_questions.py` | Fixed Question Bank 10 ข้อ, `TOTAL_QUESTIONS`, `COMPLETE_MESSAGE` |
| `gemini_client.py` | Hybrid Approach — Gemini วิเคราะห์เนื้อหาเท่านั้น, FINALIZE confidence rules (int 0-100), post-processing floor 60, per-request api_key |
| `chat_predictor.py` | Fixed question routing, Quick Reply bypass, `validate_user_input()` (keyboard mashing), show_result จากการนับ question |
| `app.py` | FastAPI endpoints, Final Safety Gate (`_SHOW_RESULT_GATE`), `load_dotenv` |
| `behavioral_signals.py` | Fallback — `BehavioralSignalExtractor`: SBERT + keyword + regex |
| `reply_generator.py` | Fallback — `generate_reply()`: no-repeat, skip resolved dim |
| `requirements.txt` | `google-generativeai>=0.8.0`, `python-dotenv>=1.0.0` |
| `.env.example` | `GEMINI_API_KEY`, `GEMINI_MODEL`, `AI_PORT`, `USE_SENTENCE_TRANSFORMER` |

---

## 🔧 Setup

```bash
# ตั้งค่า Gemini API Key (server-level)
cp ai-service/.env.example ai-service/.env
# แก้ไข GEMINI_API_KEY=your_key_here

# รันด้วย Docker
docker compose up

# หรือรัน AI service โดยตรง
cd ai-service
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
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

# 2. ส่งข้อความ (Quick Reply style)
CSID=chat_xxx
curl -X POST http://localhost:8080/api/chat/message \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$CSID\",\"text\":\"อยากกลับไปพักคนเดียว\"}" | jq .

# 3. ดูผลเมื่อ is_completed = true (หลังตอบครบ 10 คำถาม)
curl -X POST http://localhost:8080/api/chat/result \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$CSID\"}" | jq '{mbti_type, confidence}'
# expected: confidence เป็น int (เช่น 85) ไม่ใช่ float

# 4. ทดสอบ Quick Reply Bypass
curl -X POST http://localhost:8000/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "turns": [
      {"role": "ai",   "text": "หลังจากใช้เวลากับคนอื่นทั้งวัน..."},
      {"role": "user", "text": "อยากกลับไปพักคนเดียว"}
    ],
    "user_turn_count": 2
  }' | jq '{is_valid, reply}'
# expected: is_valid=true (bypass เพราะตรงกับ suggested_choices)

# 5. ทดสอบ Answer Validation (invalid response)
curl -X POST http://localhost:8000/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "turns": [
      {"role": "ai",   "text": "หลังจากใช้เวลากับคนอื่น..."},
      {"role": "user", "text": "ฟหกด"}
    ],
    "user_turn_count": 2
  }' | jq '{is_valid, reply}'
# expected: is_valid=false (keyboard mashing)
```

---

## 🎓 สรุป Logic ทั้งระบบ

```
User กดปุ่ม Quick Reply (หรือพิมพ์เอง)
       ↓
Angular: เก็บ bubble + ส่ง POST /api/chat/message {session_id, text, api_key?}
       ↓
Go: นับ valid turns → ส่ง full history + api_key ไป Python
       ↓
Python:
  [Quick Reply Bypass]
  ① ถ้า text ∈ suggested_choices ของคำถามก่อนหน้า → ข้าม validate ทั้งหมด

  [Python Gibberish Gate]
  ② validate_user_input() → False: return redirect + repeat คำถามเดิม

  [Gemini Analysis — Hybrid Mode]
  ③ Gemini วิเคราะห์เนื้อหาเท่านั้น (ไม่สร้างคำถาม)
     → is_valid, acknowledge, partial_scores, dimension_confidence
  ④ Python ประกอบ reply = acknowledge + MBTI_QUESTIONS[next_q_idx]["reply"]
  ⑤ suggested_choices = MBTI_QUESTIONS[next_q_idx]["suggested_choices"]

  [show_result Decision]
  ⑥ next_q_idx ≥ 10 → show_result=True (COMPLETE_MESSAGE)
  ⑦ Final Safety Gate (app.py) — override ถ้ามี keyword ใน reply

  [Fallback — ไม่มี Gemini]
  ⑧ SBERT + keyword → behavioral signals + scores
       ↓
Go:
  - is_valid=true  → บันทึก userTurn + aiTurn
  - is_valid=false → บันทึกเฉพาะ aiTurn (redirect)
  - ส่ง {reply, is_completed, is_valid, turn_count}
       ↓
Angular:
  - แสดง AI reply ใน bubble + Quick Reply buttons
  - is_completed=true → chatCompleted.set(true)
    → ซ่อน input bar
    → แสดง "✅ วิเคราะห์เสร็จแล้ว" + ปุ่ม "✨ ดูผลลัพธ์"
       ↓ (user กดปุ่ม)
Go → AI /chat/final → MBTI type + confidence (int 0-100, floor 60)
       ↓
Angular: แสดง inline result card ใน chat window
```

---

👉 เกี่ยวข้องกับ: [02-ai-model.md](./02-ai-model.md) — model ที่ใช้, [03-api.md](./03-api.md) — API เดิม, [04-code-walkthrough.md](./04-code-walkthrough.md) — ไล่โค้ด
