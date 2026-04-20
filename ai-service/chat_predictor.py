"""
Chat-mode MBTI predictor — Psychometrics Expert Mode.

ลำดับ:
  1. Gemini API (ถ้ามี GEMINI_API_KEY) — ใช้ Cognitive Functions + Behavioral Signals
  2. Keyword fallback — ถ้าไม่มี Gemini
"""

from __future__ import annotations
import re
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

# Thai vowel / tone-mark codepoints — real Thai words ALWAYS contain at least one
# Gibberish keyboard mashing (home row: ฟหกดเ / ผปแอ / etc.) produces consonants only
_THAI_VOWEL_CHARS: frozenset = frozenset(
    # sara above/below/following: ะ ั า ำ ิ ี ึ ื ุ ู ฺ
    '\u0e30\u0e31\u0e32\u0e33\u0e34\u0e35\u0e36\u0e37\u0e38\u0e39\u0e3a'
    # leading standalone vowels: เ แ โ ใ ไ
    '\u0e40\u0e41\u0e42\u0e43\u0e44'
    # ็ (mai tai khu — vowel shortener)
    '\u0e47'
    # tone marks: ่ ้ ๊ ๋
    '\u0e48\u0e49\u0e4a\u0e4b'
    # ์ (thanthakhat — silent-consonant marker, appears in real words)
    '\u0e4c'
)

# English QWERTY keyboard rows — to catch row-mashing (asdfgh, qwerty, etc.)
_QWERTY_ROWS: tuple = (
    frozenset('qwertyuiop'),
    frozenset('asdfghjkl'),
    frozenset('zxcvbnm'),
)

# Thai Kedmanee keyboard rows — to catch Thai row-mashing (e.g. "หกฟด่าส" = asdf+jkl)
# Row A (asdfghjkl;'): ฟหกดเ้่าสวง
# Row Q (qwertyuiop[]): ๆไำพะัีรนยบล
# Row Z (zxcvbnm,./):  ผปแอิืทมใฝ
_THAI_KB_ROWS: tuple = (
    frozenset('ฟหกดเ้่าสวง'),
    frozenset('ๆไำพะัีรนยบล'),
    frozenset('ผปแอิืทมใฝ'),
)

# Thai text that starts with a following-sara, sara am, or tone mark = always invalid input
# ำ (sara am) included: legitimate Thai sentences never begin with it
_STARTS_WITH_SARA_RE = re.compile(r'^[ะาิีึืุูัำ็่้๊๋์]')
# Explicit home-row blacklist — pure-consonant runs that are never real Thai words
# Subset only (other patterns already caught by row/consonant-run rules above)
_HOME_ROW_BLACKLIST: frozenset = frozenset({
    # Row A consecutive consonant substrings (asdf / asdfg / etc.)
    'ฟหกด', 'หกดส', 'กดสว', 'ดสวง',
    # Row A scrambled versions
    'ฟดหก', 'ฟดกห', 'หดฟก', 'กฟหด',
    # Row Z runs
    'ผปแอ', 'ทมใฝ',
})


# ── Fallback helpers ──────────────────────────────────────────────────────────

def _is_valid_response(text: str) -> bool:
    """ตรวจสอบข้อความใน fallback mode — คัดกรองคำตอบที่สั้น/ไม่มีความหมาย"""
    stripped = text.strip()
    if len(stripped) < 5:
        return False
    if stripped.lower() in _INVALID_TOKENS:
        return False
    return True


def validate_user_input(text: str) -> bool:
    """
    Hard gate ก่อนส่ง Gemini — ตรวจจับ keyboard mashing ด้วย Python ล้วนๆ
    Return True  = ผ่านเกณฑ์ → ส่งให้ Gemini ประมวลผลต่อ
    Return False = ขยะ/gibberish → คืน error ทันที ไม่เรียก Gemini เด็ดขาด

    Design principle: ดักเฉพาะสิ่งที่ชัวร์ 100% ว่าเป็น gibberish
    ข้อความที่ยาวพอและไม่ชัดเจน → ส่ง Gemini ต่อ (Gemini ประเมินได้ดีกว่า Python regex)
    """
    stripped = text.strip()

    # 1. Too short to be meaningful
    if len(stripped) < 2:
        return False

    # 2. Known meaningless single-token responses
    if stripped.lower() in _INVALID_TOKENS:
        return False

    # 3. Repeated char spam — 4+ same chars in a row (กกกก, 5555, aaaa)
    if re.search(r'(.)\1{3,}', stripped):
        return False

    # 4. Only 1–2 distinct non-space chars across a long string
    if len(set(stripped.replace(' ', ''))) <= 2 and len(stripped) > 5:
        return False

    thai_chars = [c for c in stripped if '\u0e00' <= c <= '\u0e7f']
    has_thai = bool(thai_chars)
    has_latin = any(c.isalpha() and ord(c) < 128 for c in stripped)
    has_digits = any(c.isdigit() for c in stripped)

    # Whitelist: mixed Thai + English/numbers ที่ยาวพอ
    # คำตอบจริงมักผสมภาษา เช่น "ทำเสร็จก่อน deadline", "ทำงาน part time"
    # → ตรวจแค่ blacklist แล้วส่ง Gemini ต่อ ไม่ต้องผ่าน Thai-structure rules
    if has_thai and (has_latin or has_digits) and len(stripped) >= 6:
        if any(pat in stripped for pat in _HOME_ROW_BLACKLIST):
            return False
        return True

    # ── Thai-only checks ──────────────────────────────────────────────────────

    if has_thai and len(thai_chars) >= 4:
        # 5. Zero vowels/tone-marks = pure consonant gibberish
        if sum(1 for c in thai_chars if c in _THAI_VOWEL_CHARS) == 0:
            return False

        # 6. All Thai chars from a single Kedmanee keyboard row = row-mashing
        if any(set(thai_chars).issubset(row) for row in _THAI_KB_ROWS):
            return False

        # 10. 5+ consecutive Thai consonants without any vowel break
        #     Valid Thai (even loanwords) rarely exceeds 3–4; 5+ = gibberish
        consonant_run = 0
        for c in thai_chars:
            if c not in _THAI_VOWEL_CHARS:
                consonant_run += 1
                if consonant_run >= 5:
                    return False
            else:
                consonant_run = 0

        # 12. Starts with following-sara, sara am, or tone mark
        #     Valid Thai input always starts with a consonant or leading vowel (เแโใไ)
        if _STARTS_WITH_SARA_RE.search(stripped):
            return False

    # ── Latin-only checks ─────────────────────────────────────────────────────

    if has_latin and not has_thai:
        alpha_only = [c.lower() for c in stripped if c.isalpha() and ord(c) < 128]
        # 9. QWERTY keyboard-row mashing (asdfgh, qwerty, zxcvb, etc.)
        if len(alpha_only) >= 4:
            if any(set(alpha_only).issubset(row) for row in _QWERTY_ROWS):
                return False

    # 14. Explicit home-row substring blacklist — final safety net
    if any(pat in stripped for pat in _HOME_ROW_BLACKLIST):
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
    # ── Hard gate: Python pre-validation ก่อนเรียก Gemini ───────────────────────
    # ไม่ผ่าน validate_user_input → return ทันที ไม่แตะ Gemini API เลย
    last_user_text = next((t["text"] for t in reversed(turns) if t["role"] == "user"), "")
    if not validate_user_input(last_user_text):
        last_ai_text = next((t["text"] for t in reversed(turns) if t["role"] == "ai"), "")
        # Compute scores from valid history only — exclude this invalid message
        valid_turns = [t for t in turns if not (t["role"] == "user" and t["text"] == last_user_text)]
        valid_texts = [t["text"] for t in valid_turns if t["role"] == "user"]
        signals = _make_extractor().extract(valid_texts) if valid_texts else _default_signals()
        dim_conf = _dim_confidence_from_signals(signals, max(0, user_turn_count - 1))
        prev_q = f"\n\nกลับมาที่คำถามนี้เลยนะ: {last_ai_text}" if last_ai_text else ""
        return {
            "is_valid": False,
            "reply": (
                "ระบบตรวจพบข้อความที่ไม่สามารถประเมินผลได้ "
                "รบกวนพิมพ์เป็นประโยคหรืออธิบายเพิ่มเติมอีกนิดนะครับ 😅"
                + prev_q
            ),
            "partial_scores": _flatten_scores(signals),
            "dimension_confidence": dim_conf,
            "confidence": _compute_confidence(signals, max(0, user_turn_count - 1)),
            "show_result": False,
        }

    # ── เส้นทาง Gemini ──────────────────────────────────────────────────────
    gemini_result = gemini_client.chat_analyze(turns, user_turn_count, api_key=api_key)
    if gemini_result is not None:
        return gemini_result

    # ── เส้นทาง Fallback ────────────────────────────────────────────────────
    # last_user_text already set above
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
