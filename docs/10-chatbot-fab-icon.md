# 10 — Chatbot MBTI Interactive Icon (FAB Chat Mode)

> ระบบนี้เปลี่ยนโหมดการทดสอบจาก "เลือกตอบทีละข้อ" → **"พูดคุยกับ AI แบบ Free-text"**
> AI วิเคราะห์บุคลิกภาพ MBTI จากบทสนทนาเองโดยไม่ต้องถามทีละคำถาม

> **Implementation Status:** ✅ Implemented & Updated (2026-04-20)
> ไฟล์ที่สร้าง/แก้ไข: `ai-service/gemini_client.py`, `ai-service/chat_predictor.py`, `ai-service/app.py`, `ai-service/requirements.txt`, `ai-service/.env.example`, `backend/ai/client.go`, `backend/handlers/chat.go`, `frontend/.../fab-chat.component.ts`, `frontend/.../fab-chat.service.ts`

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
│  │  User: วันนี้ผมชอบ...               │               │
│  │  AI: เข้าใจแล้ว! ขอถามเพิ่ม...      │               │
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
| **กำลังคุย** | `!chatCompleted && !mbtiResult` | Input bar + ปุ่มส่ง |
| **วิเคราะห์เสร็จ** | `chatCompleted && !mbtiResult` | ปุ่ม "✨ ดูผลลัพธ์ MBTI" เต็มความกว้าง |
| **แสดงผลแล้ว** | `mbtiResult` | Inline Result Card (input ซ่อน) |

### Settings Panel (API Key)

กดไอคอน ⚙️ ใน header เพื่อเปิด settings panel:
- ช่อง input (type=password) สำหรับกรอก Gemini API Key
- บันทึกลง `localStorage` ด้วย key `mbti_gemini_api_key`
- แสดง 8 ตัวอักษรแรกของ key ที่บันทึกอยู่ พร้อมปุ่มลบ
- ถ้าไม่กรอก → ระบบ fallback ใช้ key จาก `.env` ของ server

---

## 💬 Core Concept — Free-text Chat

### เปรียบเทียบ 2 โหมด

| | โหมดเดิม (Quiz) | โหมดใหม่ (FAB Chat) |
|--|-----------------|---------------------|
| **วิธีตอบ** | เลือก a/b/c ทีละข้อ | พิมพ์คุยอิสระ |
| **ข้อมูลที่ได้** | structured choices 20 ข้อ | free-text หลาย turn |
| **ประสบการณ์ผู้ใช้** | ทำแบบทดสอบ | คุยกับ AI เป็นธรรมชาติ |
| **Engine หลัก** | rule-based + LogReg | **Google Gemini API (LLM)** |
| **Engine สำรอง** | — | SBERT + keyword + behavioral signals |
| **จำนวนรอบขั้นต่ำ** | 20 ข้อ (คงที่) | 5 รอบ (sanity guard) |
| **เกณฑ์สรุปผล** | ครบ 20 ข้อ | Gemini วิเคราะห์ครบ + safety-net keywords |

---

## ⚙️ Technical Logic — Data Flow รายขั้น

```
User พิมพ์ข้อความ
       │
       ▼
[Angular FAB Component]
  - เก็บ conversation history (local state)
  - ส่ง POST /api/chat/message  {session_id, text, api_key?}
       │
       ▼
[Go Backend — /api/chat/message]
  - validate request
  - นับ userTurnCount (valid turns เท่านั้น + turn ใหม่)
  - ส่ง full history ไป AI Service  POST /chat/analyze
       │
       ▼
[Python AI Service — /chat/analyze]
  ┌── Layer 0: Answer Validation ───────────────────────────┐
  │  ตรวจสอบข้อความล่าสุดว่าวิเคราะห์ MBTI ได้ไหม          │
  │  → is_valid: true/false (Gemini) หรือ keyword check     │
  └─────────────────────────────────────────────────────────┘
  ┌── Primary (ถ้ามี GEMINI_API_KEY) ───────────────────────┐
  │  1) Normalize reply field (check reply/reply_message)   │
  │  2) ส่ง full history ไป Gemini API                      │
  │  3) Gemini วิเคราะห์ Cognitive Functions + reply        │
  │  4) 3-layer show_result decision (ดูด้านล่าง)          │
  └─────────────────────────────────────────────────────────┘
  ┌── Fallback (ไม่มี Gemini) ──────────────────────────────┐
  │  1) _is_valid_response() check (keyword tokens)         │
  │  2) BehavioralSignalExtractor: SBERT + keyword + regex  │
  │  3) คำนวณ confidence + resolved_dims                    │
  │  4) ReplyGenerator: เลือก follow-up question            │
  └─────────────────────────────────────────────────────────┘
  ┌── Final Safety Gate (app.py) ───────────────────────────┐
  │  ถ้า reply มีคำว่า "ดูผล"/"วิเคราะห์ครบ" ฯลฯ          │
  │  แต่ show_result ยังเป็น false → บังคับ true            │
  └─────────────────────────────────────────────────────────┘
  - return: {is_valid, reply, partial_scores, dimension_confidence,
             confidence, show_result}
       │
       ▼
[Go Backend]
  - ถ้า is_valid=true → บันทึก userTurn + aiTurn ลง MongoDB
  - ถ้า is_valid=false → บันทึกเฉพาะ aiTurn (redirect) — ไม่บันทึก userTurn
  - ส่ง {reply, show_result_button, is_completed, is_valid, turn_count}
       │
       ▼
[Angular]
  - แสดง reply ใน chat bubble
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
  chatCompleted   = signal(false);      // ← ใหม่: ระดับ component (ไม่ใช่ per-message)
  showSettings    = signal(false);      // ← ใหม่: settings panel toggle
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
    APIKey        string        `json:"api_key,omitempty"`  // ← ใหม่: user key
}

type ChatAnalyzeResponse struct {
    IsValid       bool           `json:"is_valid"`       // ← ใหม่
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
    # ถ้า show_result ยังเป็น False แต่ reply มีคำ trigger → บังคับ True
    # (ป้องกัน Gemini ตั้ง JSON flag ผิดแต่ข้อความถูก)
    if not result.get("show_result", False):
        reply_lower = str(result.get("reply", "")).lower()
        if any(kw in reply_lower for kw in _SHOW_RESULT_GATE):
            logger.warning("Final-gate: keyword in reply but show_result=False — forcing True")
            result["show_result"] = True

    return result
```

### `gemini_client.py` — 3-Layer show_result Decision

```python
# ai-service/gemini_client.py

MIN_USER_TURNS_FOR_RESULT = 5    # sanity guard เท่านั้น — AI finish ก่อนได้ (Early Exit)
DIM_CONFIDENCE_THRESHOLD  = 0.80  # อ้างอิงใน fallback mode

# Safety-net keywords — ถ้า Gemini ลืมตั้ง flag แต่พิมพ์คำเหล่านี้ใน reply
_RESULT_TRIGGER_KEYWORDS: tuple = (
    "ดูผล mbti", "กดปุ่มดูผล", "กดดูผล", "ดูผลลัพธ์", "ดูผล",
    "วิเคราะห์ครบ", "วิเคราะห์เสร็จ", "วิเคราะห์เสร็จแล้ว",
    "พร้อมดูผล", "สรุปผล mbti", "สรุปบุคลิกภาพ",
    "ผลการวิเคราะห์", "ผล mbti", "ผลลัพธ์ mbti",
    "✨ ดูผล", "กดปุ่ม",
)

def chat_analyze(turns, user_turn_count, api_key=None) -> Optional[Dict]:
    result = _call(model_analyze, prompt)

    # is_valid — default True ถ้า Gemini ไม่ส่งมา
    is_valid = bool(result.get("is_valid", True))
    result["is_valid"] = is_valid

    # Normalize reply field — Gemini บางครั้งใช้ "reply_message" หรือ "message"
    if "reply" not in result:
        result["reply"] = (
            result.pop("reply_message", None)
            or result.pop("message", None)
            or "เล่าต่อได้เลยนะ 😊"
        )

    # ── show_result: 3 layers ─────────────────────────────────────────
    # Layer 1: Gemini JSON flag (primary)
    gemini_flag = bool(result.get("show_result", False))

    # Layer 2: keyword safety-net (fallback เมื่อ Gemini ตั้ง flag ผิด)
    keyword_triggered = any(kw in result["reply"].lower()
                            for kw in _RESULT_TRIGGER_KEYWORDS)

    # Layer 3: hard guards (sanity only)
    enough_turns = user_turn_count >= MIN_USER_TURNS_FOR_RESULT

    result["show_result"] = is_valid and enough_turns and (gemini_flag or keyword_triggered)
    return result
```

### System Prompt — ANALYZE_SYSTEM_PROMPT (กฎหลัก)

```
กฎเหล็ก:
1. ห้ามด่วนสรุปก่อน 5 รอบ — รวบรวมข้อมูลให้พอ
2. ห้ามถามซ้ำ — ตรวจ Chat History ทุกครั้ง
3. ถามเจาะลึก Cognitive Functions เท่านั้น
4. วิเคราะห์ Behavioral Signals จากรูปแบบการเขียนด้วย
5. Early Exit — วิเคราะห์ครบทุก dim แล้ว จบได้ทันที ไม่ต้องรอ 10 รอบ

🚨 CRITICAL RULE:
   ทันทีที่ reply มีเนื้อหาเชิญให้ดูผลหรือกดปุ่ม
   ต้องตั้ง "show_result": true ใน JSON เสมอ
   ห้ามตั้ง false เด็ดขาด ไม่ว่ากรณีใดทั้งสิ้น
```

### `chat_predictor.py` — Answer Validation + Routing

```python
# ai-service/chat_predictor.py

_INVALID_TOKENS: set = {
    "ก็ได้", "ไม่รู้", "อาจจะ", "555", "ok", "เออ", "อ่อ",
    "ครับ", "ค่ะ", "นะ", "...", "ใช่", "ไม่", "เฉยๆ", ...
}

def _is_valid_response(text: str) -> bool:
    """Fallback mode — คัดกรองคำตอบที่สั้น/ไม่มีความหมาย"""
    stripped = text.strip()
    if len(stripped) < 5: return False
    if stripped.lower() in _INVALID_TOKENS: return False
    return True

def analyze(turns, user_turn_count, api_key=None) -> Dict:
    # ── Primary: Google Gemini (is_valid, reply, show_result รวมอยู่ใน result)
    gemini_result = gemini_client.chat_analyze(turns, user_turn_count, api_key=api_key)
    if gemini_result is not None:
        return gemini_result

    # ── Fallback: Keyword/SBERT
    last_user_text = next((t["text"] for t in reversed(turns) if t["role"] == "user"), "")
    is_valid = _is_valid_response(last_user_text)

    if not is_valid:
        # ดึงคำถามล่าสุดของ AI เพื่อทวนซ้ำ
        last_ai = next((t["text"] for t in reversed(turns) if t["role"] == "ai"), "")
        return {
            "is_valid": False,
            "reply": f"ขอโทษนะ ต้องการข้อมูลเกี่ยวกับตัวคุณ 😊\n\n{last_ai}",
            "partial_scores": ...,   # ใช้ scores จาก valid turns ก่อนหน้า
            "show_result": False,
        }

    # ... วิเคราะห์ตามปกติ
    return {
        "is_valid": True,
        "reply": reply,
        "partial_scores": _flatten_scores(signals),
        "dimension_confidence": dim_conf,
        "confidence": confidence,
        "show_result": show_result,
    }
```

---

## 🛡️ Answer Validation System

ระบบคัดกรองข้อความผู้ใช้ก่อนบันทึกลง Chat History

### เกณฑ์ `is_valid = false`

| ประเภท | ตัวอย่าง |
|--------|---------|
| สั้นเกินไป (< 5 ตัวอักษร) | "ก็ได้", "ok", "555", "เออ" |
| นอกเรื่องโดยสิ้นเชิง | ถามเรื่องหนัง, ข่าว, ให้ AI ช่วยงาน |
| ถาม AI กลับโดยไม่ให้ข้อมูล | "คุณคิดยังไง?", "ทำไมถึงถาม?" |

### ผลของ `is_valid = false`

```
Gemini สร้าง reply = "ตักเตือนสุภาพ + ทวนคำถามเดิม"
Python: show_result = false (บังคับ)
Go: บันทึกเฉพาะ aiTurn (redirect) — ไม่บันทึก userTurn ลง MongoDB
Frontend: แสดง redirect message แต่ turn_count ไม่นับ
```

---

## 📊 Thresholds

| ค่า | Gemini Mode | Fallback Mode |
|-----|-------------|---------------|
| `MIN_USER_TURNS_FOR_RESULT` | **5** (sanity guard, `gemini_client.py`) | **10** (`chat_predictor.py`) |
| Early Exit | ✅ ได้ — Gemini วิเคราะห์ครบเมื่อไหรก็จบได้ | ❌ ต้องครบ 10 รอบ |
| `DIM_CONFIDENCE_THRESHOLD` | 0.80 (แจ้ง Gemini ใน prompt) | 0.80 (overall) |
| `RESOLVED_CLARITY` | — | 0.30 (clarity per dim) |

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
  "reply": "เข้าใจแล้ว! ขอถามเพิ่มเติม — เวลาต้องตัดสินใจสำคัญ...",
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
  "behavioral_signals": "ตอบสั้น, ใช้คำรูปธรรม, มีโครงสร้างประโยคชัด"
}
```

เมื่อ `is_valid = false`:
```json
{
  "is_valid": false,
  "reply": "ขอโทษนะ ฉันต้องการข้อมูลเกี่ยวกับตัวคุณ 😊\n\nกลับมาที่คำถาม: ...",
  "partial_scores": { "E": 30, "I": 70, ... },
  "show_result": false
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
  "turn_count": 7
}
```

เมื่อแชทเสร็จ:
```json
{
  "reply": "วิเคราะห์ครบทุกด้านแล้ว! ✨ กดปุ่มดูผล MBTI ของคุณได้เลย",
  "show_result_button": true,
  "is_completed": true,
  "is_valid": true,
  "turn_count": 12
}
```

### `/chat/final` Response (เหมือนเดิม)

```json
{
  "mbti_type": "INTJ",
  "nickname": "The Architect (สถาปนิก)",
  "cognitive_stack": "Ni > Te > Fi > Se",
  "dimensions": {"E": 25, "I": 75, "S": 35, "N": 65, "T": 68, "F": 32, "J": 72, "P": 28},
  "dimension_confidence": {"EI": 0.88, "SN": 0.85, "TF": 0.82, "JP": 0.90},
  "confidence": 0.8625,
  "description": "คุณมีวิสัยทัศน์ที่ชัดเจน...",
  "reasoning": "1. คุณพูดว่า... 2. สังเกตว่า...",
  "behavioral_evidence": "ใช้คำนามธรรมมาก, ตอบยาวและเชื่อมโยงหลายแนวคิด",
  "strengths": [...],
  "weaknesses": [...],
  "careers": [...],
  "famous_people": [...],
  "compatible_types": ["ENFP", "ENTP"]
}
```

---

## 🗃️ MongoDB — chat_sessions

```javascript
{
  "_id": "chat_01HW8...",
  "created_at": ISODate("2026-04-20T03:00:00Z"),
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
      "text": "วันนี้ผมชอบอยู่บ้านคนเดียว อ่านหนังสือ",
      "ts": ISODate("..."),
      "partial_scores": null
    },
    {
      "role": "ai",
      "text": "เข้าใจแล้ว! ขอถามเพิ่ม...",
      "ts": ISODate("..."),
      "partial_scores": {"E": 25, "I": 75, ...}
    }
    // ... (อย่างน้อย 5 valid user turns ก่อน show_result=true)
  ]
}
```

---

## 🔧 ไฟล์ที่เพิ่ม/แก้ (Implemented ✅)

### Angular (Frontend)
| ไฟล์ | สิ่งที่ทำ |
|------|-----------|
| `components/fab-chat/fab-chat.component.ts` | FAB + chat window + settings panel + completion footer + inline result card |
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
| `gemini_client.py` | Primary engine — Gemini API, 3-layer show_result, reply normalization, keyword safety-net, per-request api_key, `load_dotenv` |
| `chat_predictor.py` | Router: Gemini → fallback, Answer Validation (`_is_valid_response`), `api_key` passthrough |
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
#   "min_turns_for_result": 5,
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

# 2. ส่งข้อความ (ตรวจ is_completed และ is_valid ใน response)
CSID=chat_xxx
curl -X POST http://localhost:8080/api/chat/message \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$CSID\",\"text\":\"วันนี้ผมชอบอยู่บ้านอ่านหนังสือคนเดียว\"}" | jq .

# 3. ดูผลเมื่อ is_completed = true
curl -X POST http://localhost:8080/api/chat/result \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$CSID\"}" | jq .

# 4. ทดสอบ Final Safety Gate โดยตรง (ส่ง reply ที่มีคำ trigger)
curl -X POST http://localhost:8000/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "turns": [
      {"role": "ai",   "text": "สวัสดี!"},
      {"role": "user", "text": "ผมชอบอยู่คนเดียว คิดคนเดียว"}
    ],
    "user_turn_count": 6
  }' | jq '{reply, show_result, is_valid}'

# 5. ทดสอบ Answer Validation (invalid response)
curl -X POST http://localhost:8000/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "turns": [
      {"role": "ai",   "text": "คุณชอบอยู่คนเดียวหรือกับเพื่อน?"},
      {"role": "user", "text": "ไม่รู้"}
    ],
    "user_turn_count": 2
  }' | jq '{is_valid, reply}'
# expected: is_valid=false, reply มีคำขอโทษ + ทวนคำถาม
```

---

## 🎓 สรุป Logic ทั้งระบบ

```
User พิมพ์ข้อความ (free-text)
       ↓
Angular: เก็บ bubble + ส่ง POST /api/chat/message {session_id, text, api_key?}
       ↓
Go: นับ valid turns → ส่ง full history + api_key ไป Python
       ↓
Python:
  [Answer Validation]
  ① Gemini ประเมิน is_valid (หรือ _is_valid_response() ใน fallback)
  ② ถ้า invalid → reply = redirect, show_result = false → return

  [Gemini Mode — มี API Key]
  ① Normalize reply field (reply / reply_message / message)
  ② Gemini วิเคราะห์ Cognitive Functions + สร้าง reply
  ③ 3-layer show_result:
     L1: Gemini JSON flag
     L2: keyword safety-net ใน reply
     L3: is_valid AND turns≥5
  ④ Final Safety Gate ที่ app.py — override ถ้า keyword ใน reply

  [Fallback Mode — ไม่มี Gemini]
  ① keyword token validation
  ② SBERT + keyword + regex → behavioral signals
  ③ confidence + resolved_dims → show_result (ต้องครบ 10 รอบ)
       ↓
Go:
  - is_valid=true  → บันทึก userTurn + aiTurn
  - is_valid=false → บันทึกเฉพาะ aiTurn (redirect)
  - ส่ง {reply, is_completed, is_valid, turn_count}
       ↓
Angular:
  - แสดง AI reply ใน bubble
  - is_completed=true → chatCompleted.set(true)
    → ซ่อน input bar
    → แสดง "✅ วิเคราะห์เสร็จแล้ว" + ปุ่ม "✨ ดูผลลัพธ์"
       ↓ (user กดปุ่ม)
Go → AI /chat/final → MBTI type + cognitive_stack + reasoning
       ↓
Angular: แสดง inline result card ใน chat window
```

---

👉 เกี่ยวข้องกับ: [02-ai-model.md](./02-ai-model.md) — model ที่ใช้, [03-api.md](./03-api.md) — API เดิม, [04-code-walkthrough.md](./04-code-walkthrough.md) — ไล่โค้ด
