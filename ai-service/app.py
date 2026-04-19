"""
FastAPI app — wraps predictor.
Run:  uvicorn app:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from predictor import predict, load_model, load_sbert, USE_SBERT
import chat_predictor


class AnswerItem(BaseModel):
    question_id: int = Field(..., ge=1, le=20)
    choice_id: str


class PredictRequest(BaseModel):
    answers: List[AnswerItem]
    free_text: Optional[str] = None


# ── Chat mode models ──────────────────────────────────────────────────────────

class ChatTurnItem(BaseModel):
    role: str   # "user" | "ai"
    text: str


class ChatAnalyzeRequest(BaseModel):
    session_id: str
    turns: List[ChatTurnItem]
    user_turn_count: int = 0


class ChatFinalRequest(BaseModel):
    session_id: str
    turns: List[ChatTurnItem]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm-up on startup
    try:
        load_model()
        print("✓ ML model loaded")
    except Exception as e:
        print(f"⚠ Model not loaded: {e}")
    if USE_SBERT:
        try:
            load_sbert()
            print("✓ Sentence-transformer loaded")
        except Exception as e:
            print(f"⚠ SBERT not loaded: {e}")
    yield


app = FastAPI(
    title="MBTI AI Service",
    version="1.0.0",
    description="Predicts MBTI personality type from questionnaire answers (optional free text).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # internal service — Go only
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check"""
    model_loaded = True
    try:
        load_model()
    except Exception:
        model_loaded = False
    sbert, _ = load_sbert()
    return {
        "status": "ok",
        "model_loaded": model_loaded,
        "sbert_loaded": sbert is not None,
        "sbert_enabled": USE_SBERT,
    }


@app.post("/predict")
def do_predict(req: PredictRequest):
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


# ── Chat endpoints ────────────────────────────────────────────────────────────

@app.post("/chat/analyze")
def chat_analyze(req: ChatAnalyzeRequest):
    """
    รับ turns ทั้งหมดของ session → วิเคราะห์ behavioral signals
    → คืน reply + partial_scores + confidence + show_result flag
    """
    try:
        turns = [{"role": t.role, "text": t.text} for t in req.turns]
        result = chat_predictor.analyze(turns, req.user_turn_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat analyze error: {e}")
    return result


@app.post("/chat/final")
def chat_final(req: ChatFinalRequest):
    """
    สรุป MBTI type สุดท้ายจากบทสนทนาทั้งหมด
    คืน format เดียวกับ /predict
    """
    try:
        turns = [{"role": t.role, "text": t.text} for t in req.turns]
        result = chat_predictor.finalize(turns)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat final error: {e}")
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AI_PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
