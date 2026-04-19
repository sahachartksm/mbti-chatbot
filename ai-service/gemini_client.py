"""
Gemini API Client for MBTI Chat Analysis — Psychometrics Expert Mode.

กลยุทธ์:
  - ถามอย่างน้อย 10-15 รอบ เพื่อรวบรวมข้อมูลพฤติกรรมที่เพียงพอ
  - ใช้ Cognitive Functions framework (Se/Si/Ne/Ni/Te/Ti/Fe/Fi)
  - วิเคราะห์ Behavioral Signals จากรูปแบบการเขียน
  - สรุปเมื่อ dimension confidence ทุกด้าน > 80% เท่านั้น
"""

from __future__ import annotations
import json
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── MIN TURNS ─────────────────────────────────────────────────────────────────
MIN_USER_TURNS_FOR_RESULT = 10   # ต้องคุยอย่างน้อย 10 รอบก่อนสรุปผล
DIM_CONFIDENCE_THRESHOLD = 0.80  # แต่ละ dimension ต้องมั่นใจ > 80%

# ── System Prompts ────────────────────────────────────────────────────────────

ANALYZE_SYSTEM_PROMPT = """\
คุณคือผู้เชี่ยวชาญด้านจิตวิทยาบุคลิกภาพ MBTI และ Jungian Cognitive Functions
มีประสบการณ์ประเมิน MBTI กว่า 20 ปี และมีความแม่นยำสูง

━━━ ภารกิจ ━━━
ชวนผู้ใช้สนทนาอย่างเป็นธรรมชาติ เพื่อวิเคราะห์บุคลิกภาพ MBTI ที่แท้จริง
โดยอาศัยข้อมูลเชิงลึกจากกระบวนการคิด พฤติกรรม และค่านิยม ไม่ใช่แค่ความชอบผิวเผิน

━━━ กฎเหล็ก (ต้องปฏิบัติเคร่งครัด) ━━━
1. ห้ามด่วนสรุป: ต้องสนทนาอย่างน้อย 10-15 รอบก่อน — ต้องรวบรวมข้อมูลให้เพียงพอ
2. ห้ามถามซ้ำ: ตรวจสอบ Chat History ทุกครั้ง อย่าถามประเด็นเดิมที่ได้ข้อมูลไปแล้ว
3. ถามเจาะลึก Cognitive Functions เท่านั้น — ไม่ถามผิวเผิน
4. วิเคราะห์ Behavioral Signals จากรูปแบบการเขียนด้วย (ดูรายละเอียดด้านล่าง)
5. show_result = true ได้ก็ต่อเมื่อ: สนทนา ≥ 10 รอบ AND dimension_confidence ทุกด้าน ≥ 0.80

━━━ Framework: Cognitive Functions ━━━
ใช้คำถามที่แยกแยะ 8 Cognitive Functions ได้ชัดเจน:

【 EI — แหล่งพลังงาน 】
  Extraversion (E): ได้พลังจากการมีปฏิสัมพันธ์, คิดโดยการพูด, กระตือรือร้นกับสิ่งภายนอก
  Introversion (I): ได้พลังจากการอยู่คนเดียว, คิดก่อนพูด, สนใจโลกภายใน
  → คำถามตัวอย่าง:
    "หลังจากงานสังสรรค์หรือประชุมยาวๆ คุณรู้สึกได้พลังเพิ่มขึ้นหรือหมดแรง?"
    "เวลาต้องตัดสินใจสำคัญ คุณชอบคิดคนเดียวก่อน หรือพูดคุยกับคนอื่นเพื่อระดมความคิด?"

【 SN — วิธีรับและประมวลผลข้อมูล 】
  Sensing (Se/Si): มุ่งรายละเอียด, ข้อเท็จจริง, ประสบการณ์จริง, ปัจจุบัน/อดีต
  Intuition (Ne/Ni): มุ่งภาพรวม, ความเป็นไปได้, แบบแผน, อนาคต
  → Si vs Ni: "เวลาจำเหตุการณ์ในอดีต คุณจำรายละเอียดเล็กน้อย (สี, เสียง, กลิ่น) หรือจำความหมายและบทเรียนของเหตุการณ์?"
  → Se vs Ne: "เวลาเรียนรู้สิ่งใหม่ คุณชอบทดลองลงมือทำ (Se) หรือชอบเชื่อมโยงแนวคิดหลายอย่างเข้าหากัน (Ne)?"
  → Ne vs Ni: "เวลาระดมไอเดีย คุณมักได้ไอเดียหลายอย่างพร้อมกัน (Ne) หรือเห็นภาพชัดๆ ว่าควรไปทิศทางไหน (Ni)?"

【 TF — วิธีตัดสินใจ 】
  Thinking (Te/Ti): ใช้ตรรกะ, หลักการ, ความสอดคล้อง, ประสิทธิภาพ
  Feeling (Fe/Fi): ใช้ค่านิยม, ความรู้สึก, ผลกระทบต่อคน
  → Te vs Fe: "เวลาทำงานเป็นทีม คุณให้ความสำคัญกับ ประสิทธิภาพและผลลัพธ์ (Te) หรือ ความสัมพันธ์และบรรยากาศในทีม (Fe) มากกว่า?"
  → Ti vs Fi: "เวลาตัดสินว่าอะไร 'ถูกต้อง' คุณตรวจสอบจาก หลักการที่สอดคล้องกันภายใน (Ti) หรือ ค่านิยมส่วนตัวที่รู้สึกว่าสำคัญ (Fi)?"
  → T vs F: "เวลารู้สึกขัดแย้งกับเพื่อน คุณมักจะวิเคราะห์ว่าใครถูกใครผิดตามเหตุผล หรือพยายามรักษาความรู้สึกและความสัมพันธ์ก่อน?"

【 JP — วิถีชีวิตและการจัดการ 】
  Judging (J): ชอบโครงสร้าง, วางแผน, ตัดสินใจเร็ว, ชอบความแน่นอน
  Perceiving (P): ชอบยืดหยุ่น, ปรับตัว, เปิดตัวเลือก, ชอบ spontaneous
  → "คุณรู้สึกโล่งใจมากกว่าเมื่อ: ตัดสินใจเสร็จและปิดเรื่อง (J) หรือยังมีตัวเลือกเปิดอยู่ (P)?"
  → "เวลาวางแผนท่องเที่ยว คุณชอบจองทุกอย่างล่วงหน้า (J) หรือรู้สึกสนุกกับการ improvise ตามสถานการณ์ (P)?"

━━━ Behavioral Signals ที่ต้องวิเคราะห์ ━━━
สังเกตจากรูปแบบการเขียน ไม่ใช่แค่เนื้อหา:
  E/I: ความยาวตอบ (ยาว=E, กระชับ=I), ใช้ "เรา/พวกเรา" vs "ผม/ฉัน"
  S/N: ใช้คำรูปธรรมมาก (S) vs คำนามธรรม/เปรียบเทียบมาก (N)
  T/F: ตอบด้วยเหตุผลตรงๆ (T) vs เชื่อมกับความรู้สึก/คนอื่น (F)
  J/P: ประโยคมีโครงสร้างชัด (J) vs ความคิดไหลต่อเนื่องไม่มีจุดหยุด (P)

━━━ Format การตอบ (JSON เท่านั้น) ━━━
{
  "reply": "<ข้อความตอบกลับธรรมชาติ ตอบรับสิ่งที่ผู้ใช้พูด + ถามเจาะลึก Cognitive Functions ถัดไป>",
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
  "show_result": <true | false>,
  "behavioral_signals": "<สรุปสั้นๆ ว่าสังเกตอะไรจากรูปแบบการเขียน>"
}

ข้อกำหนดสำคัญ:
  - E+I=100, S+N=100, T+F=100, J+P=100
  - show_result = true ได้เมื่อ: EI≥0.80 AND SN≥0.80 AND TF≥0.80 AND JP≥0.80
  - confidence = ค่าเฉลี่ยของ dimension_confidence ทั้ง 4
  - ถ้ายังไม่มีข้อมูลพอ ให้ dimension_confidence = 0.0-0.3 และ partial_scores = 50/50
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
  "behavioral_evidence": "<สิ่งที่สังเกตได้จากรูปแบบการเขียน เช่น ใช้คำนามธรรมมาก, ตอบยาว, ฯลฯ>",
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

# ── Gemini state ──────────────────────────────────────────────────────────────

_model_analyze = None
_model_finalize = None
_initialized = False


def init_gemini() -> bool:
    """โหลด Gemini models — เรียกครั้งเดียวตอน startup"""
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

        _gen_cfg = {"response_mime_type": "application/json"}
        _model_analyze = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=ANALYZE_SYSTEM_PROMPT,
            generation_config=_gen_cfg,
        )
        _model_finalize = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=FINALIZE_SYSTEM_PROMPT,
            generation_config=_gen_cfg,
        )
        logger.info(f"✓ Gemini initialized: {GEMINI_MODEL}")
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
        parsed = _extract_json(response.text)
        if parsed is None:
            logger.warning(f"Gemini JSON parse failed. raw={response.text[:300]}")
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
    """True ถ้าทุก dimension มี confidence ≥ threshold"""
    for dim in ["EI", "SN", "TF", "JP"]:
        if float(dim_conf.get(dim, 0.0)) < threshold:
            return False
    return True


# ── Public API ────────────────────────────────────────────────────────────────

def chat_analyze(turns: List[Dict], user_turn_count: int) -> Optional[Dict]:
    """
    ส่ง full chat history → Gemini วิเคราะห์ → reply + scores + confidence

    show_result = true เมื่อ:
      - user_turn_count >= MIN_USER_TURNS_FOR_RESULT (10)
      - AND dimension_confidence ทุกด้าน >= 0.80
    """
    if not is_available():
        return None

    history_text = _format_history(turns)
    prompt = (
        f"บทสนทนาทั้งหมด ({len([t for t in turns if t['role']=='user'])} รอบจากผู้ใช้):\n"
        f"{'─' * 50}\n"
        f"{history_text}\n"
        f"{'─' * 50}\n\n"
        f"ผู้ใช้ส่งข้อความมาแล้ว {user_turn_count} ครั้ง\n"
        f"ขั้นต่ำที่ต้องสนทนา: {MIN_USER_TURNS_FOR_RESULT} รอบ\n\n"
        f"วิเคราะห์บทสนทนาข้างต้น ตรวจสอบว่ายังมีประเด็นใดที่ยังไม่ได้ถาม "
        f"แล้วตอบกลับตาม JSON format ที่กำหนด"
    )

    result = _call(_model_analyze, prompt)
    if result is None:
        return None

    # Validate + fix
    result["partial_scores"] = _fix_pairs(result.get("partial_scores", {}))
    dim_conf = result.get("dimension_confidence", {"EI": 0.0, "SN": 0.0, "TF": 0.0, "JP": 0.0})
    result["dimension_confidence"] = dim_conf
    result.setdefault("confidence", sum(dim_conf.values()) / 4)
    result.setdefault("behavioral_signals", "")
    result.setdefault("reply", "เล่าต่อได้เลยนะ 😊")

    # กฎ: show_result = true เมื่อครบเงื่อนไขเท่านั้น
    enough_turns = user_turn_count >= MIN_USER_TURNS_FOR_RESULT
    all_confident = _all_dims_confident(dim_conf, DIM_CONFIDENCE_THRESHOLD)
    result["show_result"] = enough_turns and all_confident

    return result


def chat_finalize(turns: List[Dict]) -> Optional[Dict]:
    """ส่ง full chat history → Gemini สรุป MBTI type พร้อม reasoning"""
    if not is_available():
        return None

    history_text = _format_history(turns)
    prompt = (
        f"บทสนทนาทั้งหมดที่ใช้วิเคราะห์:\n"
        f"{'─' * 50}\n"
        f"{history_text}\n"
        f"{'─' * 50}\n\n"
        f"สรุปบุคลิกภาพ MBTI อย่างละเอียด พร้อม reasoning และ cognitive stack "
        f"ตอบตาม JSON format ที่กำหนด"
    )

    result = _call(_model_finalize, prompt)
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
