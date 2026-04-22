"""
FastAPI app — wraps predictor.
Run:  uvicorn app:app --reload --port 8000

env vars:
  GEMINI_API_KEY     → เปิดใช้ Google Gemini สำหรับ chat mode (แนะนำ)
  GEMINI_MODEL       → ชื่อ model (default: gemini-2.0-flash)
  USE_SENTENCE_TRANSFORMER → true/false (default: true)
  AI_PORT            → port (default: 8000)
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from predictor import predict, load_model, load_sbert, USE_SBERT
import gemini_client
import chat_predictor

logger = logging.getLogger(__name__)

# ── Final-gate keywords (app.py layer — last resort before sending to Go) ────
# If the AI reply contains any of these, show_result is forced True regardless
# of what lower layers decided.
_SHOW_RESULT_GATE: tuple = (
    "ดูผล", "กดปุ่ม", "วิเคราะห์ครบ", "วิเคราะห์เสร็จ",
    "ผลลัพธ์", "ผลการวิเคราะห์", "ดูผลลัพธ์", "สรุปผล",
)


# ── Pydantic Models ───────────────────────────────────────────────────────────

class AnswerItem(BaseModel):
    question_id: int = Field(..., ge=1, le=20)
    choice_id: str


class PredictRequest(BaseModel):
    answers: List[AnswerItem]
    free_text: Optional[str] = None


class ChatTurnItem(BaseModel):
    role: str   # "user" | "ai"
    text: str


class ChatAnalyzeRequest(BaseModel):
    session_id: str
    turns: List[ChatTurnItem]
    user_turn_count: int = 0
    api_key: Optional[str] = None


class ChatFinalRequest(BaseModel):
    session_id: str
    turns: List[ChatTurnItem]
    api_key: Optional[str] = None


class ChatAnalyzeResponse(BaseModel):
    """Response model สำหรับ /chat/analyze — ป้องกัน FastAPI ตัด field ทิ้ง"""
    model_config = {"extra": "allow"}   # preserve fields ที่ไม่ได้ระบุ (partial_scores ฯลฯ)

    is_valid:           bool       = True
    reply:              str        = ""
    suggested_choices:  List[str]  = Field(default_factory=list)
    confidence:         float      = 0.0
    show_result:        bool       = False


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Gemini (chat mode primary engine)
    if gemini_client.init_gemini():
        print("✓ Gemini API ready")
    else:
        print("⚠ Gemini unavailable — chat mode will use keyword fallback")
        # 2. Fallback: load ML model + SBERT
        try:
            load_model()
            print("✓ ML model loaded (fallback)")
        except Exception as e:
            print(f"⚠ ML model not loaded: {e}")
        if USE_SBERT:
            try:
                load_sbert()
                print("✓ Sentence-transformer loaded (fallback)")
            except Exception as e:
                print(f"⚠ SBERT not loaded: {e}")
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="MBTI AI Service",
    version="2.0.0",
    description=(
        "MBTI analysis via Google Gemini (chat mode) "
        "or Rule-based + ML (quiz mode / fallback)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    model_loaded = True
    try:
        load_model()
    except Exception:
        model_loaded = False
    sbert, _ = load_sbert()
    return {
        "status": "ok",
        "chat_engine": "gemini" if gemini_client.is_available() else "keyword_fallback",
        "gemini_enabled": gemini_client.is_available(),
        "gemini_model": gemini_client.GEMINI_MODEL if gemini_client.is_available() else None,
        "min_turns_for_result": gemini_client.MIN_USER_TURNS_FOR_RESULT,
        "dim_confidence_threshold": gemini_client.DIM_CONFIDENCE_THRESHOLD,
        "ml_model_loaded": model_loaded,
        "sbert_loaded": sbert is not None,
        "sbert_enabled": USE_SBERT,
    }


# ── Quiz mode: Rule-based + ML (ยังคงใช้ classifier เดิม) ────────────────────

@app.post("/predict")
def do_predict(req: PredictRequest):
    """
    Quiz mode — วิเคราะห์จาก 20 คำตอบ (rule-based + Logistic Regression)
    ยังคง engine เดิมเพราะ structured answers ทำงานได้ดีกว่า LLM
    """
    if len(req.answers) < 20:
        raise HTTPException(
            status_code=400,
            detail=f"Expected 20 answers, got {len(req.answers)}",
        )
    answers = [{"question_id": a.question_id, "choice_id": a.choice_id} for a in req.answers]
    try:
        result = predict(answers, free_text=req.free_text)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"predict error: {e}")
    return result


# ── Chat mode: Gemini LLM (fallback: keyword) ─────────────────────────────────

@app.post("/chat/analyze")
def chat_analyze(req: ChatAnalyzeRequest) -> Dict[str, Any]:
    """
    Chat mode — รับ full chat history → Gemini วิเคราะห์ทั้งหมด
    คืน: reply (natural) + partial_scores + confidence + show_result flag + suggested_choices

    Engine: Gemini API (ถ้ามี GEMINI_API_KEY) หรือ keyword fallback
    """
    try:
        turns = [{"role": t.role, "text": t.text} for t in req.turns]
        result = chat_predictor.analyze(turns, req.user_turn_count, api_key=req.api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat analyze error: {e}")

    # ── Final safety gate (app.py) ─────────────────────────────────────────
    if not result.get("show_result", False):
        reply_lower = str(result.get("reply", "")).lower()
        if any(kw in reply_lower for kw in _SHOW_RESULT_GATE):
            logger.warning(
                "Final-gate [app.py]: keyword in reply but show_result=False — forcing True. "
                f"reply[:80]={result.get('reply','')[:80]!r}"
            )
            result["show_result"] = True

    return result


@app.post("/chat/final")
def chat_final(req: ChatFinalRequest):
    """
    Chat mode — สรุป MBTI type สุดท้ายจากบทสนทนาทั้งหมด
    คืน format เดียวกับ /predict

    Engine: Gemini API (ถ้ามี GEMINI_API_KEY) หรือ keyword fallback
    """
    try:
        turns = [{"role": t.role, "text": t.text} for t in req.turns]
        result = chat_predictor.finalize(turns, api_key=req.api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat final error: {e}")
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AI_PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
