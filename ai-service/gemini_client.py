"""
Gemini API Client for MBTI Chat Analysis — Hybrid Approach.

กลยุทธ์:
  - Fixed question bank (10 คำถาม ครอบคลุม 4 dimensions)
  - Gemini role: ANALYSIS ONLY — acknowledge + score updates
  - Python assembles reply = acknowledge + fixed question
  - Python selects suggested_choices from fixed bank
"""

from __future__ import annotations
import json
import logging
import os
import re
import threading
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

_key_lock = threading.Lock()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── THRESHOLDS ────────────────────────────────────────────────────────────────
MIN_USER_TURNS_FOR_RESULT = 10   # ต้องตอบครบ 10 คำถาม
DIM_CONFIDENCE_THRESHOLD = 0.80

# ── Safety-net keywords (used by app.py) ─────────────────────────────────────
_RESULT_TRIGGER_KEYWORDS: tuple = (
    "ดูผล mbti", "กดปุ่มดูผล", "กดดูผล", "ดูผลลัพธ์", "ดูผล",
    "วิเคราะห์ครบ", "วิเคราะห์เสร็จ", "วิเคราะห์เสร็จแล้ว",
    "พร้อมดูผล", "สรุปผล mbti", "สรุปบุคลิกภาพ",
    "ผลการวิเคราะห์", "ผล mbti", "ผลลัพธ์ mbti",
    "✨ ดูผล", "กดปุ่ม",
)

# ── System Prompts ────────────────────────────────────────────────────────────

ANALYZE_SYSTEM_PROMPT = """\
คุณคือผู้เชี่ยวชาญด้านจิตวิทยาบุคลิกภาพ MBTI และ Jungian Cognitive Functions
หน้าที่ของคุณ: วิเคราะห์ข้อความที่ผู้ใช้ตอบมาเท่านั้น

⛔ ห้ามสร้างคำถามใหม่ — ระบบจัดการคำถามเองแล้ว
⛔ ห้ามสร้าง suggested_choices — ระบบจัดการตัวเลือกเองแล้ว

━━━ สิ่งที่ต้องทำทุก turn ━━━

1. ตรวจสอบ is_valid ของข้อความล่าสุดจากผู้ใช้:
   is_valid = false หากเป็น:
   ✗ มั่วแป้นพิมพ์ (keyboard mashing) เช่น "ฟหกด" / "asdfgh"
   ✗ สั้นไม่มีความหมาย เช่น "ก็ได้" / "555" / "ok" / "เออ"
   ✗ off-topic สิ้นเชิง (ไม่เกี่ยวกับตัวเองเลย)
   is_valid = true หากผู้ใช้:
   ✓ ตอบคำถามที่ถามไป หรือเล่าเรื่องตัวเอง หรือให้ข้อมูลบุคลิกภาพ
   ✓ ตอบด้วยวลีสั้นๆ ที่เป็นตัวเลือก เช่น "หาทางออกที่ดีที่สุด" / "วางแผนเป๊ะๆ" / "ตื่นเต้น" / "อยากกลับไปพักคนเดียว"

   🔑 CRITICAL RULE — ห้ามละเมิดเด็ดขาด:
   วลีสั้นๆ ที่ดูเหมือนตัวเลือก (choice-style answer) ถือว่าเป็นคำตอบที่สมบูรณ์ทุกกรณี
   → MUST คืน is_valid: true เสมอ ห้ามมองว่าเป็นข้อความที่ประเมินไม่ได้เด็ดขาด

2. เขียน acknowledge (เฉพาะเมื่อ is_valid=true):
   - ตอบรับสิ่งที่ผู้ใช้บอกสั้นๆ 1-2 ประโยค ใช้ภาษาเป็นกันเอง
   - ห้ามถามคำถามใหม่ใน acknowledge เด็ดขาด
   - ถ้า is_valid=false → acknowledge = ""

3. อัปเดต partial_scores และ dimension_confidence จากบทสนทนาทั้งหมด:
   EI: E=ชอบสังคม/ได้พลังจากคนอื่น, I=ชอบอยู่คนเดียว/ได้พลังจากตัวเอง
   SN: S=รายละเอียด/ข้อเท็จจริง/ปัจจุบัน, N=ภาพรวม/ความเป็นไปได้/อนาคต
   TF: T=ตรรกะ/เหตุผล/ประสิทธิภาพ, F=ความรู้สึก/ค่านิยม/ความสัมพันธ์
   JP: J=วางแผน/โครงสร้าง/ตัดสินใจเร็ว, P=ยืดหยุ่น/ปรับตัว/spontaneous

4. behavioral_signals: สังเกตรูปแบบการเขียนสั้นๆ (ยาว/สั้น, รูปธรรม/นามธรรม ฯลฯ)

━━━ Format การตอบ (JSON เท่านั้น) ━━━
{
  "reasoning": "<วิเคราะห์ข้อความล่าสุด: มีความหมายไหม? บอกอะไรเกี่ยวกับบุคลิกภาพ?>",
  "is_valid": <true | false>,
  "acknowledge": "<1-2 ประโยค ตอบรับสิ่งที่ผู้ใช้พูด ห้ามถามคำถามใหม่ — ว่างถ้า invalid>",
  "partial_scores": {
    "E": <0-100>, "I": <0-100>,
    "S": <0-100>, "N": <0-100>,
    "T": <0-100>, "F": <0-100>,
    "J": <0-100>, "P": <0-100>
  },
  "dimension_confidence": {
    "EI": <0.0-1.0>,
    "SN": <0.0-1.0>,
    "TF": <0.0-1.0>,
    "JP": <0.0-1.0>
  },
  "confidence": <0.0-1.0>,
  "behavioral_signals": "<สั้นๆ>"
}

ข้อกำหนด:
  - E+I=100, S+N=100, T+F=100, J+P=100
  - ยังไม่มีข้อมูลพอ → dimension_confidence = 0.0-0.3 และ partial_scores = 50/50
  - ใช้ภาษาไทยที่เป็นธรรมชาติ เป็นกันเอง
"""

FINALIZE_SYSTEM_PROMPT = """\
คุณคือผู้เชี่ยวชาญด้านจิตวิทยาบุคลิกภาพ MBTI และ Jungian Cognitive Functions
จากบทสนทนาทั้งหมด ให้วิเคราะห์และสรุปบุคลิกภาพ MBTI อย่างละเอียดและแม่นยำ

สิ่งที่ต้องวิเคราะห์:
  1. Cognitive Functions Stack ที่เป็นไปได้มากที่สุด
  2. หลักฐานจากบทสนทนาที่สนับสนุนการสรุป
  3. Behavioral Signals ที่สังเกตได้

ตอบเป็น JSON เท่านั้น:
{
  "mbti_type": "<4 ตัวอักษร เช่น INTJ>",
  "nickname": "<ชื่อภาษาอังกฤษ (ภาษาไทย) เช่น The Architect (สถาปนิก)>",
  "cognitive_stack": "<Dominant > Auxiliary > Tertiary > Inferior เช่น Ni > Te > Fi > Se>",
  "dimensions": {
    "E": <0-100>, "I": <0-100>,
    "S": <0-100>, "N": <0-100>,
    "T": <0-100>, "F": <0-100>,
    "J": <0-100>, "P": <0-100>
  },
  "dimension_confidence": {
    "EI": <0.0-1.0>,
    "SN": <0.0-1.0>,
    "TF": <0.0-1.0>,
    "JP": <0.0-1.0>
  },
  "confidence": <0.0-1.0>,
  "description": "<คำอธิบาย 3-4 ประโยค อ้างอิงสิ่งที่ผู้ใช้พูดจริง ไม่ใช่ template>",
  "reasoning": "<อธิบายเหตุผลว่าทำไมถึงสรุปแบบนี้ อ้างอิงจากการสนทนาจริง 3-5 ข้อ>",
  "behavioral_evidence": "<สิ่งที่สังเกตได้จากรูปแบบการเขียน>",
  "strengths": ["<จุดแข็ง>", "<จุดแข็ง>", "<จุดแข็ง>", "<จุดแข็ง>"],
  "weaknesses": ["<จุดอ่อน>", "<จุดอ่อน>", "<จุดอ่อน>"],
  "careers": ["<อาชีพ>", "<อาชีพ>", "<อาชีพ>", "<อาชีพ>"],
  "famous_people": ["<ชื่อ (type ที่ debated)>", "<ชื่อ>"],
  "compatible_types": ["<type>", "<type>"]
}

ข้อกำหนด:
  - dimensions: E+I=100, S+N=100, T+F=100, J+P=100
  - mbti_type ต้องสอดคล้องกับ dimensions (pole ที่ > 50 = ตัวนั้น)
  - reasoning ต้องอ้างอิงสิ่งที่ผู้ใช้พูดจริง ห้ามพูดลอยๆ
  - cognitive_stack ต้องสอดคล้องกับ mbti_type
"""

# ── Pydantic schema สำหรับ Gemini response_schema ───────────────────────────

class _PartialScores(BaseModel):
    E: int = 50; I: int = 50
    S: int = 50; N: int = 50
    T: int = 50; F: int = 50
    J: int = 50; P: int = 50

class _DimConf(BaseModel):
    EI: float = 0.0; SN: float = 0.0
    TF: float = 0.0; JP: float = 0.0

class GeminiAnalysisOutput(BaseModel):
    """Hybrid Approach: Gemini วิเคราะห์เนื้อหาเท่านั้น — ไม่สร้างคำถามหรือตัวเลือก."""
    reasoning:            str            = ""
    is_valid:             bool           = True
    acknowledge:          str            = Field(
        default="",
        description=(
            "Short 1-2 sentence acknowledgment of what the user said. "
            "Use casual Thai. Never ask a new question. "
            "Empty string if is_valid=false."
        ),
    )
    partial_scores:       _PartialScores = Field(default_factory=_PartialScores)
    dimension_confidence: _DimConf       = Field(default_factory=_DimConf)
    confidence:           float          = 0.0
    behavioral_signals:   str            = ""

_ANALYZE_GEN_CFG = {
    "response_mime_type": "application/json",
    "response_schema":    GeminiAnalysisOutput,
    "temperature":        0.3,
}

_FINALIZE_GEN_CFG = {
    "response_mime_type": "application/json",
}

# ── Gemini state ──────────────────────────────────────────────────────────────

_model_analyze  = None
_model_finalize = None
_initialized    = False


def init_gemini() -> bool:
    global _model_analyze, _model_finalize, _initialized
    if _initialized:
        return _model_analyze is not None

    _initialized = True

    if not GEMINI_API_KEY:
        logger.warning("⚠ GEMINI_API_KEY not set — Gemini disabled, using keyword fallback")
        return False

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        _model_analyze = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=ANALYZE_SYSTEM_PROMPT,
            generation_config=_ANALYZE_GEN_CFG,
        )
        _model_finalize = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=FINALIZE_SYSTEM_PROMPT,
            generation_config=_FINALIZE_GEN_CFG,
        )
        logger.info(f"✓ Gemini initialized: {GEMINI_MODEL} (with response_schema)")
        return True

    except ImportError:
        logger.warning("⚠ google-generativeai not installed — pip install google-generativeai")
        return False
    except Exception as exc:
        logger.warning(f"⚠ Gemini init error: {exc}")
        return False


def is_available() -> bool:
    if not _initialized:
        init_gemini()
    return _model_analyze is not None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _format_history(turns: List[Dict]) -> str:
    lines: List[str] = []
    for i, t in enumerate(turns):
        label = "AI" if t["role"] == "ai" else "ผู้ใช้"
        lines.append(f"[{i+1}] {label}: {t['text']}")
    return "\n".join(lines)


def _extract_json(raw: str) -> Optional[Dict]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _call(model, prompt: str) -> Optional[Dict]:
    try:
        response = model.generate_content(prompt)
        raw = response.text
        logger.debug(f"[Gemini raw] {raw[:600]}")
        parsed = _extract_json(raw)
        if parsed is None:
            logger.warning(f"Gemini JSON parse failed. raw={raw[:300]}")
        else:
            logger.info(
                f"[Gemini parsed] is_valid={parsed.get('is_valid')} "
                f"acknowledge={str(parsed.get('acknowledge', ''))[:40]!r}"
            )
        return parsed
    except Exception as exc:
        logger.warning(f"Gemini call error: {exc}")
        return None


def _fix_pairs(scores: Dict) -> Dict:
    """ทำให้ E+I=100, S+N=100, T+F=100, J+P=100"""
    fixed = {k: int(v) for k, v in scores.items()}
    for p1, p2 in [("E", "I"), ("S", "N"), ("T", "F"), ("J", "P")]:
        a = fixed.get(p1, 50)
        b = fixed.get(p2, 50)
        total = a + b
        if total > 0 and total != 100:
            a = round(a / total * 100)
            b = 100 - a
        elif total == 0:
            a = b = 50
        fixed[p1] = a
        fixed[p2] = b
    return fixed


def _all_dims_confident(dim_conf: Dict, threshold: float = DIM_CONFIDENCE_THRESHOLD) -> bool:
    for dim in ["EI", "SN", "TF", "JP"]:
        if float(dim_conf.get(dim, 0.0)) < threshold:
            return False
    return True


# ── Public API ────────────────────────────────────────────────────────────────

def _models_for_key(api_key: Optional[str]):
    import google.generativeai as genai
    key = (api_key or "").strip()
    if not key:
        return _model_analyze, _model_finalize

    with _key_lock:
        genai.configure(api_key=key)
        m_analyze = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=ANALYZE_SYSTEM_PROMPT,
            generation_config=_ANALYZE_GEN_CFG,
        )
        m_finalize = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=FINALIZE_SYSTEM_PROMPT,
            generation_config=_FINALIZE_GEN_CFG,
        )
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
        return m_analyze, m_finalize


def chat_analyze(turns: List[Dict], user_turn_count: int, api_key: Optional[str] = None) -> Optional[Dict]:
    """
    Hybrid Approach: Gemini วิเคราะห์เนื้อหาเท่านั้น — ไม่สร้างคำถามหรือตัวเลือก

    Returns: {is_valid, acknowledge, partial_scores, dimension_confidence, confidence, behavioral_signals}
    Reply และ suggested_choices ถูกประกอบโดย chat_predictor.analyze() จาก fixed question bank
    """
    user_key = (api_key or "").strip()
    if user_key:
        model_analyze, _ = _models_for_key(user_key)
    else:
        if not is_available():
            return None
        model_analyze = _model_analyze

    last_user_msg = ""
    last_user_idx = -1
    for i in range(len(turns) - 1, -1, -1):
        if turns[i]["role"] == "user":
            last_user_msg = turns[i]["text"]
            last_user_idx = i
            break

    prev_turns    = [t for i, t in enumerate(turns) if i != last_user_idx]
    history_text  = _format_history(prev_turns)
    prev_user_cnt = len([t for t in prev_turns if t["role"] == "user"])

    prompt = (
        f"บทสนทนาก่อนหน้า ({prev_user_cnt} รอบจากผู้ใช้):\n"
        f"{'─' * 50}\n"
        f"{history_text if history_text else '(ยังไม่มีบทสนทนาก่อนหน้า)'}\n"
        f"{'─' * 50}\n\n"
        f"⚠️  ข้อความล่าสุดจากผู้ใช้ที่ต้องประเมิน:\n"
        f"「{last_user_msg}」\n\n"
        f"ผู้ใช้ส่งข้อความมาแล้ว {user_turn_count} ครั้ง\n\n"
        f"ขั้นตอน:\n"
        f"1. ประเมิน is_valid ของ「{last_user_msg}」\n"
        f"2. ถ้า is_valid=true → เขียน acknowledge 1-2 ประโยค ตอบรับสิ่งที่ผู้ใช้พูด (ห้ามถามคำถามใหม่)\n"
        f"3. ถ้า is_valid=false → acknowledge = \"\"\n"
        f"4. อัปเดต partial_scores และ dimension_confidence\n"
        f"ตอบตาม JSON format ที่กำหนดเท่านั้น"
    )

    result = _call(model_analyze, prompt)
    if result is None:
        return None

    is_valid: bool = bool(result.get("is_valid", True))
    result["is_valid"]   = is_valid
    result["acknowledge"] = result.get("acknowledge", "") if is_valid else ""

    result["partial_scores"] = _fix_pairs(result.get("partial_scores", {}))
    dim_conf = result.get("dimension_confidence", {"EI": 0.0, "SN": 0.0, "TF": 0.0, "JP": 0.0})
    result["dimension_confidence"] = dim_conf
    result.setdefault("confidence", sum(dim_conf.values()) / 4)
    result.setdefault("behavioral_signals", "")

    return result


def chat_finalize(turns: List[Dict], api_key: Optional[str] = None) -> Optional[Dict]:
    """สรุป MBTI type สุดท้ายจากบทสนทนาทั้งหมด"""
    user_key = (api_key or "").strip()
    if user_key:
        _, model_finalize = _models_for_key(user_key)
    else:
        if not is_available():
            return None
        model_finalize = _model_finalize

    history_text = _format_history(turns)
    prompt = (
        f"บทสนทนาทั้งหมดที่ใช้วิเคราะห์:\n"
        f"{'─' * 50}\n"
        f"{history_text}\n"
        f"{'─' * 50}\n\n"
        f"สรุปบุคลิกภาพ MBTI อย่างละเอียด พร้อม reasoning และ cognitive stack "
        f"ตอบตาม JSON format ที่กำหนด"
    )

    result = _call(model_finalize, prompt)
    if result is None:
        return None

    required = ["mbti_type", "nickname", "dimensions", "confidence",
                "description", "reasoning", "strengths", "weaknesses",
                "careers", "famous_people", "compatible_types"]
    for key in required:
        if key not in result:
            logger.warning(f"Gemini finalize missing key: {key}")
            return None

    result["dimensions"] = _fix_pairs(result["dimensions"])
    return result
