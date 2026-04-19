"""
FastAPI app — MBTI personality analyzer.

Endpoints:
  GET  /health        — service health + LLM reachability
  POST /analyze-llm   — primary: free-text Q&A → LLM psychologist → MBTI
  POST /predict       — legacy: multiple-choice → rule/ML/SBERT (kept for compat)
"""

import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import llm_analyzer


# --------- Legacy (MC) request schema ---------
class AnswerItem(BaseModel):
    question_id: int = Field(..., ge=1, le=20)
    choice_id: str


class PredictRequest(BaseModel):
    answers: List[AnswerItem]
    free_text: Optional[str] = None


# --------- LLM (free-text) request schema ---------
class QAItem(BaseModel):
    question: str
    answer: str = ""


class AnalyzeLLMRequest(BaseModel):
    qa: List[QAItem] = Field(..., min_length=1)
    lang: str = "th"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # LLM health probe (non-blocking)
    try:
        info = llm_analyzer.ollama_health()
        if info.get("reachable") and info.get("model_present"):
            print(f"✓ Ollama reachable; model '{info['model']}' present")
        elif info.get("reachable"):
            print(f"⚠ Ollama reachable but model '{info['model']}' NOT pulled. "
                  f"Run: ollama pull {info['model']}")
        else:
            print(f"⚠ Ollama not reachable at {info.get('url')}: {info.get('error')}")
    except Exception as e:
        print(f"⚠ Ollama health probe failed: {e}")
    yield


app = FastAPI(
    title="MBTI AI Service",
    version="2.0.0",
    description="LLM-based MBTI analyzer (primary) + legacy ML predictor.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # internal service — called by Go backend only
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check. Reports Ollama / LLM readiness."""
    info = llm_analyzer.ollama_health()
    return {
        "status": "ok",
        "llm_reachable": info.get("reachable", False),
        "llm_model_present": info.get("model_present", False),
        "llm_model": info.get("model"),
        "llm_url": info.get("url"),
        "llm_ready": info.get("reachable", False) and info.get("model_present", False),
    }


@app.post("/analyze-llm")
def analyze_llm(req: AnalyzeLLMRequest):
    """Primary endpoint: free-text Q&A → LLM psychologist → structured MBTI."""
    qa = [{"question": q.question, "answer": q.answer} for q in req.qa]
    try:
        result = llm_analyzer.analyze(qa, lang=req.lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"invalid LLM output: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")
    return result


@app.post("/predict")
def do_predict(req: PredictRequest):
    """Legacy multi-choice predictor (kept for backward compat; not used by new frontend)."""
    try:
        from predictor import predict
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"legacy predictor unavailable: {e}")

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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AI_PORT", "8000"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
