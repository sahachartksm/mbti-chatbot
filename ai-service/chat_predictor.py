"""
Chat-mode MBTI predictor — Hybrid Approach (Fixed Questions + AI Analysis).

ลำดับ:
  1. Python pre-validation (gibberish gate)
  2. Gemini API วิเคราะห์ (acknowledge + scores)
  3. Python ประกอบ reply = acknowledge + MBTI_QUESTIONS[next_q_idx]["reply"]
  4. suggested_choices = MBTI_QUESTIONS[next_q_idx]["suggested_choices"]
  5. Fallback (ไม่มี Gemini): keyword/SBERT scores + fixed questions

Indexing:
  user_turn_count (1-indexed, รวม turn ปัจจุบัน):
    1  → show question index 0
    2  → show question index 1
    ...
    10 → show question index 9 (last)
    11 → show_result = True
"""

from __future__ import annotations
import re
from typing import List, Dict, Set

import gemini_client
from behavioral_signals import BehavioralSignalExtractor
from reply_generator import generate_reply
from predictor import load_sbert
from type_info import get_info
from mbti_questions import MBTI_QUESTIONS, TOTAL_QUESTIONS, COMPLETE_MESSAGE

# ── Fallback thresholds (ใช้เมื่อ Gemini ไม่พร้อม) ───────────────────────────
MIN_USER_TURNS   = 10
CONFIDENCE_THRESHOLD = 0.80
RESOLVED_CLARITY = 0.30

_INVALID_TOKENS: set = {
    "ก็ได้", "ไม่รู้", "อาจจะ", "555", "5555", "ok", "okay", "เออ", "อ่อ",
    "ครับ", "ค่ะ", "นะ", "...", "ใช่", "ไม่", "เฉยๆ", "ปกติ", "ก็", "เออนะ",
    "ไม่แน่ใจ", "ไม่รู้สิ", "ไม่ทราบ", "pass", "ผ่าน", "next", "ต่อไป",
}

_THAI_VOWEL_CHARS: frozenset = frozenset(
    'ะัาำิีึืฺุู'
    'เแโใไ'
    '็'
    '่้๊๋'
    '์'
)

_QWERTY_ROWS: tuple = (
    frozenset('qwertyuiop'),
    frozenset('asdfghjkl'),
    frozenset('zxcvbnm'),
)

_THAI_KB_ROWS: tuple = (
    frozenset('ฟหกดเ้่าสวง'),
    frozenset('ๆไำพะัีรนยบล'),
    frozenset('ผปแอิืทมใฝ'),
)

_STARTS_WITH_SARA_RE = re.compile(r'^[ะาิีึืุูัำ็่้๊๋์]')
_HOME_ROW_BLACKLIST: frozenset = frozenset({
    'ฟหกด', 'หกดส', 'กดสว', 'ดสวง',
    'ฟดหก', 'ฟดกห', 'หดฟก', 'กฟหด',
    'ผปแอ', 'ทมใฝ',
})


# ── Validation ────────────────────────────────────────────────────────────────

def _is_valid_response(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 5:
        return False
    if stripped.lower() in _INVALID_TOKENS:
        return False
    return True


def validate_user_input(text: str) -> bool:
    """
    Hard gate ก่อนส่ง Gemini — ตรวจจับ keyboard mashing ด้วย Python ล้วนๆ
    True = ผ่านเกณฑ์, False = gibberish
    """
    stripped = text.strip()

    if len(stripped) < 2:
        return False
    if stripped.lower() in _INVALID_TOKENS:
        return False
    if re.search(r'(.)\1{3,}', stripped):
        return False
    if len(set(stripped.replace(' ', ''))) <= 2 and len(stripped) > 5:
        return False

    thai_chars = [c for c in stripped if '฀' <= c <= '๿']
    has_thai   = bool(thai_chars)
    has_latin  = any(c.isalpha() and ord(c) < 128 for c in stripped)
    has_digits = any(c.isdigit() for c in stripped)

    if has_thai and (has_latin or has_digits) and len(stripped) >= 6:
        if any(pat in stripped for pat in _HOME_ROW_BLACKLIST):
            return False
        return True

    if has_thai and len(thai_chars) >= 4:
        if sum(1 for c in thai_chars if c in _THAI_VOWEL_CHARS) == 0:
            return False
        if any(set(thai_chars).issubset(row) for row in _THAI_KB_ROWS):
            return False
        consonant_run = 0
        for c in thai_chars:
            if c not in _THAI_VOWEL_CHARS:
                consonant_run += 1
                if consonant_run >= 5:
                    return False
            else:
                consonant_run = 0
        if _STARTS_WITH_SARA_RE.search(stripped):
            return False

    if has_latin and not has_thai:
        alpha_only = [c.lower() for c in stripped if c.isalpha() and ord(c) < 128]
        if len(alpha_only) >= 4:
            if any(set(alpha_only).issubset(row) for row in _QWERTY_ROWS):
                return False

    if any(pat in stripped for pat in _HOME_ROW_BLACKLIST):
        return False

    return True


# ── Fallback score helpers ────────────────────────────────────────────────────

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


def _default_partial_scores() -> Dict[str, int]:
    return {"E": 50, "I": 50, "S": 50, "N": 50, "T": 50, "F": 50, "J": 50, "P": 50}


def _default_dim_conf() -> Dict[str, float]:
    return {"EI": 0.0, "SN": 0.0, "TF": 0.0, "JP": 0.0}


def _compute_confidence(signals: Dict, user_turn_count: int) -> float:
    clarity_scores = [
        abs(list(p.values())[0] - list(p.values())[1]) / 100.0
        for p in signals.values()
    ]
    avg_clarity = sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0.0
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
    result = {}
    turn_factor = min(1.0, user_turn_count / 15.0)
    for dim, poles in signals.items():
        clarity = abs(list(poles.values())[0] - list(poles.values())[1]) / 100.0
        result[dim] = round(clarity * turn_factor, 3)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def analyze(turns: List[Dict], user_turn_count: int, api_key: str | None = None) -> Dict:
    """
    Hybrid Approach: Fixed Questions + AI Analysis

    user_turn_count: 1-indexed (รวม turn ปัจจุบัน)
    next_q_idx = user_turn_count - 1
      0..9  → show MBTI_QUESTIONS[next_q_idx]
      ≥ 10  → show_result=True + COMPLETE_MESSAGE
    """
    next_q_idx   = user_turn_count - 1
    # Question the user was currently answering (shown in previous AI turn).
    # When is_valid=False the invalid turn is NOT saved by Go, so next request
    # will have the same user_turn_count → repeat the same question, not the next one.
    repeat_q_idx = max(0, next_q_idx - 1)

    last_user_text = next((t["text"] for t in reversed(turns) if t["role"] == "user"), "")

    # ── Exact-match bypass: quick reply buttons are always valid ─────────────
    # Check whether the user's text matches one of the choices from the previous
    # question (i.e. they tapped a Quick Reply button).  If so, skip ALL
    # validation — neither the Python gibberish gate nor Gemini's is_valid check
    # should reject a choice the system itself offered.
    prev_q_idx      = user_turn_count - 2
    is_choice_bypass = (
        0 <= prev_q_idx < TOTAL_QUESTIONS
        and last_user_text.strip() in MBTI_QUESTIONS[prev_q_idx]["suggested_choices"]
    )

    # ── Python gibberish gate (skip when bypass applies) ─────────────────────
    if not is_choice_bypass and not validate_user_input(last_user_text):
        valid_turns = [t for t in turns if not (t["role"] == "user" and t["text"] == last_user_text)]
        valid_texts = [t["text"] for t in valid_turns if t["role"] == "user"]
        signals  = _make_extractor().extract(valid_texts) if valid_texts else _default_signals()
        dim_conf = _dim_confidence_from_signals(signals, max(0, user_turn_count - 1))

        # Repeat the question the user was supposed to answer, NOT the next one
        if 0 <= repeat_q_idx < TOTAL_QUESTIONS:
            question_repeat = "\n\n" + MBTI_QUESTIONS[repeat_q_idx]["reply"]
            choices         = MBTI_QUESTIONS[repeat_q_idx]["suggested_choices"]
        else:
            question_repeat = ""
            choices         = []

        return {
            "is_valid":          False,
            "reply":             (
                "ระบบตรวจพบข้อความที่ไม่สามารถประเมินผลได้ "
                "รบกวนพิมพ์เป็นประโยคหรืออธิบายเพิ่มเติมอีกนิดนะครับ 😅"
                + question_repeat
            ),
            "suggested_choices": choices,
            "partial_scores":    _flatten_scores(signals),
            "dimension_confidence": dim_conf,
            "confidence":        _compute_confidence(signals, max(0, user_turn_count - 1)),
            "show_result":       False,
        }

    # ── Gemini analysis ───────────────────────────────────────────────────────
    gemini_result = gemini_client.chat_analyze(turns, user_turn_count, api_key=api_key)

    # Extract from Gemini (with fallbacks)
    if gemini_result is not None:
        is_valid = bool(gemini_result.get("is_valid", True))
        # Choice bypass overrides Gemini's decision — the choice came from the system
        if is_choice_bypass:
            is_valid = True
        acknowledge   = gemini_result.get("acknowledge", "") if is_valid else ""
        partial_scores = gemini_result.get("partial_scores", _default_partial_scores())
        dim_conf      = gemini_result.get("dimension_confidence", _default_dim_conf())
        confidence    = float(gemini_result.get("confidence", 0.0))
    else:
        # Gemini unavailable — compute scores via keyword fallback
        user_texts    = [t["text"] for t in turns if t["role"] == "user"]
        signals       = _make_extractor().extract(user_texts) if user_texts else _default_signals()
        is_valid      = True
        acknowledge   = ""
        partial_scores = _flatten_scores(signals)
        dim_conf      = _dim_confidence_from_signals(signals, user_turn_count)
        confidence    = _compute_confidence(signals, user_turn_count)

    # ── show_result: all questions answered ───────────────────────────────────
    if next_q_idx >= TOTAL_QUESTIONS:
        return {
            "is_valid":          True,
            "reply":             COMPLETE_MESSAGE,
            "suggested_choices": [],
            "partial_scores":    partial_scores,
            "dimension_confidence": dim_conf,
            "confidence":        confidence,
            "show_result":       True,
        }

    q = MBTI_QUESTIONS[next_q_idx]

    # ── Gemini says invalid ───────────────────────────────────────────────────
    if not is_valid:
        # Repeat the question the user was supposed to answer (repeat_q_idx),
        # not the next one (next_q_idx) — invalid turns are NOT saved by Go,
        # so the turn counter won't advance anyway.
        rq = MBTI_QUESTIONS[repeat_q_idx] if 0 <= repeat_q_idx < TOTAL_QUESTIONS else q
        return {
            "is_valid":          False,
            "reply":             (
                "ขออภัยครับ ฉันอ่านข้อความนี้ไม่เข้าใจ "
                "รบกวนพิมพ์ใหม่อีกครั้งได้ไหมครับ?\n\n" + rq["reply"]
            ),
            "suggested_choices": rq["suggested_choices"],
            "partial_scores":    partial_scores,
            "dimension_confidence": dim_conf,
            "confidence":        confidence,
            "show_result":       False,
        }

    # ── Valid: combine acknowledge + next fixed question ──────────────────────
    reply = (acknowledge + "\n\n" + q["reply"]) if acknowledge else q["reply"]
    return {
        "is_valid":          True,
        "reply":             reply,
        "suggested_choices": q["suggested_choices"],
        "partial_scores":    partial_scores,
        "dimension_confidence": dim_conf,
        "confidence":        confidence,
        "show_result":       False,
    }


def finalize(turns: List[Dict], api_key: str | None = None) -> Dict:
    """สรุป MBTI type สุดท้าย"""
    gemini_result = gemini_client.chat_finalize(turns, api_key=api_key)
    if gemini_result is not None:
        return gemini_result

    # Fallback: keyword/SBERT
    user_texts = [t["text"] for t in turns if t["role"] == "user"]
    signals    = _make_extractor().extract(user_texts) if user_texts else _default_signals()

    mbti = ""
    dimensions: Dict[str, int] = {}
    for dim in ["EI", "SN", "TF", "JP"]:
        poles = signals[dim]
        keys  = list(poles.keys())
        a, b  = poles[keys[0]], poles[keys[1]]
        dimensions[keys[0]] = a
        dimensions[keys[1]] = b
        mbti += keys[0] if a >= b else keys[1]

    confidence = _compute_confidence(signals, len(user_texts))
    info = get_info(mbti)

    return {
        "mbti_type":        mbti,
        "nickname":         info["nickname"],
        "dimensions":       dimensions,
        "confidence":       round(confidence, 3),
        "description":      info["description"],
        "reasoning":        "วิเคราะห์จาก keyword signals (fallback mode — ไม่มี Gemini API)",
        "strengths":        info["strengths"],
        "weaknesses":       info["weaknesses"],
        "careers":          info["careers"],
        "famous_people":    info["famous_people"],
        "compatible_types": info["compatible"],
    }
