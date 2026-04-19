"""
Chat-mode MBTI predictor.
วิเคราะห์บุคลิกภาพ MBTI จากบทสนทนา free-text

กฎเหล็ก (implemented ที่นี่):
  1. ไม่ถามคำถามซ้ำ  → reply_generator.py ดูแล
  2. ข้าม dimension ที่ resolved แล้ว  → compute_resolved_dims()
  3. ครบทุก dim หรือ confidence สูงพอ → show_result = True ทันที
"""

from __future__ import annotations
from typing import List, Dict, Set

from behavioral_signals import BehavioralSignalExtractor
from reply_generator import generate_reply, get_asked_dims
from predictor import load_sbert
from type_info import get_info

# ── Thresholds ───────────────────────────────────────────────────────────────
MIN_USER_TURNS = 3          # จำนวน user turns ขั้นต่ำก่อนจะ show_result
CONFIDENCE_THRESHOLD = 0.55 # confidence ขั้นต่ำ (ลดลงเพราะมีการ track resolved dims แล้ว)
RESOLVED_CLARITY = 0.20     # |pole_a - pole_b| / 100 > 0.20 → dimension นั้น "resolved"


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def _compute_confidence(signals: Dict[str, Dict[str, int]], user_turn_count: int) -> float:
    """
    confidence = avg clarity × turn_factor

    clarity  = |pole_a - pole_b| / 100  (0 = 50/50, 1 = 100/0)
    turn_factor ≈ 0.625 ที่ 3 turns, ≈ 0.71 ที่ 5 turns, ≈ 1.0 ที่ 12+ turns
    """
    clarity_scores = [
        abs(list(poles.values())[0] - list(poles.values())[1]) / 100.0
        for poles in signals.values()
    ]
    avg_clarity = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0.0
    turn_factor = min(1.0, user_turn_count / 12.0) * 0.5 + 0.5
    return round(avg_clarity * turn_factor, 3)


def _compute_resolved_dims(signals: Dict[str, Dict[str, int]]) -> Set[str]:
    """
    คืน set ของ dimension ที่มีข้อมูลชัดพอ (clarity > RESOLVED_CLARITY)
    dimension เหล่านี้จะถูกข้ามใน reply_generator
    """
    resolved: Set[str] = set()
    for dim, poles in signals.items():
        vals = list(poles.values())
        clarity = abs(vals[0] - vals[1]) / 100.0
        if clarity > RESOLVED_CLARITY:
            resolved.add(dim)
    return resolved


def _flatten_scores(signals: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for poles in signals.values():
        out.update(poles)
    return out


# ── Public API ───────────────────────────────────────────────────────────────

def analyze(turns: List[Dict], user_turn_count: int) -> Dict:
    """
    เรียกทุกครั้งที่ user ส่งข้อความใหม่

    Logic:
    1. Extract signals จาก user texts ทั้งหมด
    2. Compute resolved dims (ข้ามในการถามคำถาม)
    3. show_result = True ถ้า:
       - ครบทุก 4 dimension (resolved_dims == 4)  ← กฎข้อ 3
       - หรือ user turns ≥ MIN_USER_TURNS AND confidence ≥ threshold
    4. สร้าง reply โดย:
       - ไม่ถามคำถามเดิมซ้ำ  ← กฎข้อ 1
       - ข้าม resolved dims  ← กฎข้อ 2
    """
    user_texts = [t["text"] for t in turns if t["role"] == "user"]

    if user_texts:
        signals = _make_extractor().extract(user_texts)
    else:
        signals = _default_signals()

    confidence = _compute_confidence(signals, user_turn_count)
    resolved_dims = _compute_resolved_dims(signals)

    # กฎข้อ 3: ครบทุก dimension หรือ confidence สูงพอ → show_result ทันที
    all_resolved = len(resolved_dims) >= 4
    enough_turns = user_turn_count >= MIN_USER_TURNS and confidence >= CONFIDENCE_THRESHOLD
    show_result = all_resolved or enough_turns

    reply = generate_reply(
        resolved_dims=resolved_dims,
        all_turns=turns,
        show_result=show_result,
    )

    return {
        "reply": reply,
        "partial_scores": _flatten_scores(signals),
        "confidence": confidence,
        "show_result": show_result,
        "resolved_dims": list(resolved_dims),   # debug info (optional)
    }


def finalize(turns: List[Dict]) -> Dict:
    """
    เรียกเมื่อ user กดปุ่ม 'ดูผล MBTI' — สรุป type สุดท้าย
    """
    user_texts = [t["text"] for t in turns if t["role"] == "user"]

    if user_texts:
        signals = _make_extractor().extract(user_texts)
    else:
        signals = _default_signals()

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
        "strengths": info["strengths"],
        "weaknesses": info["weaknesses"],
        "careers": info["careers"],
        "famous_people": info["famous_people"],
        "compatible_types": info["compatible"],
    }
