"""
Chat-mode MBTI predictor — Psychometrics Expert Mode.

ลำดับ:
  1. Gemini API (ถ้ามี GEMINI_API_KEY) — ใช้ Cognitive Functions + Behavioral Signals
  2. Keyword fallback — ถ้าไม่มี Gemini
"""

from __future__ import annotations
from typing import List, Dict, Set

import gemini_client
from behavioral_signals import BehavioralSignalExtractor
from reply_generator import generate_reply
from predictor import load_sbert
from type_info import get_info

# ── Fallback thresholds (ใช้เมื่อ Gemini ไม่พร้อม) ───────────────────────────
MIN_USER_TURNS = 10          # ต้องคุยอย่างน้อย 10 รอบ (สอดคล้องกับ Gemini mode)
CONFIDENCE_THRESHOLD = 0.80  # confidence ≥ 80% ทุก dimension
RESOLVED_CLARITY = 0.30      # เพิ่มจาก 0.20 เพื่อให้แม่นยำขึ้น


# ── Fallback helpers ──────────────────────────────────────────────────────────

def _make_extractor() -> BehavioralSignalExtractor:
    sbert, anchors = load_sbert()
    return BehavioralSignalExtractor(sbert_model=sbert, anchor_embeddings=anchors)


def _default_signals() -> Dict[str, Dict[str, int]]:
    return {
        "EI": {"E": 50, "I": 50},
        "SN": {"S": 50, "N": 50},
        "TF": {"T": 50, "F": 50},
        "JP": {"J": 50, "P": 50},
    }


def _compute_confidence(signals: Dict, user_turn_count: int) -> float:
    clarity_scores = [
        abs(list(p.values())[0] - list(p.values())[1]) / 100.0
        for p in signals.values()
    ]
    avg_clarity = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0.0
    # เพิ่มน้ำหนัก turn_count ให้สูงขึ้น (ต้องคุยเยอะ)
    turn_factor = min(1.0, user_turn_count / 15.0) * 0.6 + 0.4
    return round(avg_clarity * turn_factor, 3)


def _compute_resolved_dims(signals: Dict) -> Set[str]:
    return {
        dim for dim, poles in signals.items()
        if abs(list(poles.values())[0] - list(poles.values())[1]) / 100.0 > RESOLVED_CLARITY
    }


def _flatten_scores(signals: Dict) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for poles in signals.values():
        out.update(poles)
    return out


def _dim_confidence_from_signals(signals: Dict, user_turn_count: int) -> Dict[str, float]:
    """สร้าง per-dimension confidence จาก keyword signals"""
    result = {}
    turn_factor = min(1.0, user_turn_count / 15.0)
    for dim, poles in signals.items():
        clarity = abs(list(poles.values())[0] - list(poles.values())[1]) / 100.0
        result[dim] = round(clarity * turn_factor, 3)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def analyze(turns: List[Dict], user_turn_count: int) -> Dict:
    """
    วิเคราะห์บทสนทนา → reply + scores + confidence

    Gemini mode:
      - รับ full history → Cognitive Functions analysis
      - show_result = true เมื่อ turns ≥ 10 AND ทุก dim confidence ≥ 80%

    Fallback mode:
      - keyword/SBERT → show_result เมื่อ turns ≥ 10 AND confidence ≥ 80%
    """
    # ── เส้นทาง Gemini ──────────────────────────────────────────────────────
    gemini_result = gemini_client.chat_analyze(turns, user_turn_count)
    if gemini_result is not None:
        return gemini_result

    # ── เส้นทาง Fallback ────────────────────────────────────────────────────
    user_texts = [t["text"] for t in turns if t["role"] == "user"]
    signals = _make_extractor().extract(user_texts) if user_texts else _default_signals()

    confidence = _compute_confidence(signals, user_turn_count)
    resolved_dims = _compute_resolved_dims(signals)
    dim_conf = _dim_confidence_from_signals(signals, user_turn_count)

    all_resolved = len(resolved_dims) >= 4
    enough_turns = user_turn_count >= MIN_USER_TURNS and confidence >= CONFIDENCE_THRESHOLD
    show_result = all_resolved and enough_turns

    reply = generate_reply(
        resolved_dims=resolved_dims,
        all_turns=turns,
        show_result=show_result,
    )

    return {
        "reply": reply,
        "partial_scores": _flatten_scores(signals),
        "dimension_confidence": dim_conf,
        "confidence": confidence,
        "show_result": show_result,
        "resolved_dims": list(resolved_dims),
    }


def finalize(turns: List[Dict]) -> Dict:
    """
    สรุป MBTI type สุดท้าย พร้อม reasoning

    Gemini: personalized + cognitive stack + reasoning จากการสนทนาจริง
    Fallback: keyword/SBERT + type_info
    """
    # ── เส้นทาง Gemini ──────────────────────────────────────────────────────
    gemini_result = gemini_client.chat_finalize(turns)
    if gemini_result is not None:
        return gemini_result

    # ── เส้นทาง Fallback ────────────────────────────────────────────────────
    user_texts = [t["text"] for t in turns if t["role"] == "user"]
    signals = _make_extractor().extract(user_texts) if user_texts else _default_signals()

    mbti = ""
    dimensions: Dict[str, int] = {}
    for dim in ["EI", "SN", "TF", "JP"]:
        poles = signals[dim]
        keys = list(poles.keys())
        a, b = poles[keys[0]], poles[keys[1]]
        dimensions[keys[0]] = a
        dimensions[keys[1]] = b
        mbti += keys[0] if a >= b else keys[1]

    confidence = _compute_confidence(signals, len(user_texts))
    info = get_info(mbti)

    return {
        "mbti_type": mbti,
        "nickname": info["nickname"],
        "dimensions": dimensions,
        "confidence": round(confidence, 3),
        "description": info["description"],
        "reasoning": "วิเคราะห์จาก keyword signals (fallback mode — ไม่มี Gemini API)",
        "strengths": info["strengths"],
        "weaknesses": info["weaknesses"],
        "careers": info["careers"],
        "famous_people": info["famous_people"],
        "compatible_types": info["compatible"],
    }
