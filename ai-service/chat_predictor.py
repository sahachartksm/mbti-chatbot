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

# ข้อความสั้น/ไม่มีความหมายที่ใช้คัดกรองใน fallback mode
_INVALID_TOKENS: set = {
    "ก็ได้", "ไม่รู้", "อาจจะ", "555", "5555", "ok", "okay", "เออ", "อ่อ",
    "ครับ", "ค่ะ", "นะ", "...", "ใช่", "ไม่", "เฉยๆ", "ปกติ", "ก็", "เออนะ",
    "ไม่แน่ใจ", "ไม่รู้สิ", "ไม่ทราบ", "pass", "ผ่าน", "next", "ต่อไป",
}


# ── Fallback helpers ──────────────────────────────────────────────────────────

def _is_valid_response(text: str) -> bool:
    """ตรวจสอบข้อความใน fallback mode — คัดกรองคำตอบที่สั้น/ไม่มีความหมาย"""
    stripped = text.strip()
    if len(stripped) < 5:
        return False
    if stripped.lower() in _INVALID_TOKENS:
        return False
    return True


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

def analyze(turns: List[Dict], user_turn_count: int, api_key: str | None = None) -> Dict:
    """
    วิเคราะห์บทสนทนา → reply + scores + confidence

    Gemini mode:
      - รับ full history → Cognitive Functions analysis
      - show_result = true เมื่อ turns ≥ 10 AND ทุก dim confidence ≥ 80%

    Fallback mode:
      - keyword/SBERT → show_result เมื่อ turns ≥ 10 AND confidence ≥ 80%
    """
    # ── เส้นทาง Gemini ──────────────────────────────────────────────────────
    gemini_result = gemini_client.chat_analyze(turns, user_turn_count, api_key=api_key)
    if gemini_result is not None:
        return gemini_result

    # ── เส้นทาง Fallback ────────────────────────────────────────────────────
    # ตรวจสอบข้อความล่าสุดของผู้ใช้ก่อน
    last_user_text = next((t["text"] for t in reversed(turns) if t["role"] == "user"), "")
    is_valid = _is_valid_response(last_user_text)

    if not is_valid:
        # ดึงคำถามล่าสุดของ AI เพื่อทวนซ้ำ
        last_ai_text = next((t["text"] for t in reversed(turns) if t["role"] == "ai"), "")
        redirect = (
            "ขอโทษนะ ฉันต้องการข้อมูลเกี่ยวกับตัวคุณเพื่อวิเคราะห์ MBTI ให้แม่นยำ 😊\n\n"
            f"กลับมาที่คำถามก่อนหน้านี้นะ: {last_ai_text}"
        )
        # คืน scores จากประวัติก่อนหน้า (ไม่นับข้อความนี้)
        valid_turns = [t for t in turns if t["role"] != "user" or t["text"] != last_user_text]
        valid_texts = [t["text"] for t in valid_turns if t["role"] == "user"]
        signals = _make_extractor().extract(valid_texts) if valid_texts else _default_signals()
        dim_conf = _dim_confidence_from_signals(signals, max(0, user_turn_count - 1))
        return {
            "is_valid": False,
            "reply": redirect,
            "partial_scores": _flatten_scores(signals),
            "dimension_confidence": dim_conf,
            "confidence": _compute_confidence(signals, max(0, user_turn_count - 1)),
            "show_result": False,
        }

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
        "is_valid": True,
        "reply": reply,
        "partial_scores": _flatten_scores(signals),
        "dimension_confidence": dim_conf,
        "confidence": confidence,
        "show_result": show_result,
        "resolved_dims": list(resolved_dims),
    }


def finalize(turns: List[Dict], api_key: str | None = None) -> Dict:
    """
    สรุป MBTI type สุดท้าย พร้อม reasoning

    Gemini: personalized + cognitive stack + reasoning จากการสนทนาจริง
    Fallback: keyword/SBERT + type_info
    """
    # ── เส้นทาง Gemini ──────────────────────────────────────────────────────
    gemini_result = gemini_client.chat_finalize(turns, api_key=api_key)
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
