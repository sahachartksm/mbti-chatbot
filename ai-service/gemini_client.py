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
import threading
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Serialise calls that reconfigure the global Gemini client
_key_lock = threading.Lock()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── THRESHOLDS ────────────────────────────────────────────────────────────────
MIN_USER_TURNS_FOR_RESULT = 5    # Absolute minimum (sanity guard); AI may finish earlier
DIM_CONFIDENCE_THRESHOLD = 0.80  # แต่ละ dimension ต้องมั่นใจ > 80%

# ── Safety-net keywords ───────────────────────────────────────────────────────
# ถ้า Gemini ใส่คำเหล่านี้ใน reply แต่ลืมตั้ง show_result=true → Python บังคับให้
_RESULT_TRIGGER_KEYWORDS: tuple = (
    "ดูผล mbti", "กดปุ่มดูผล", "กดดูผล", "ดูผลลัพธ์", "ดูผล",
    "วิเคราะห์ครบ", "วิเคราะห์เสร็จ", "วิเคราะห์เสร็จแล้ว",
    "พร้อมดูผล", "สรุปผล mbti", "สรุปบุคลิกภาพ",
    "ผลการวิเคราะห์", "ผล mbti", "ผลลัพธ์ mbti",
    "✨ ดูผล", "กดปุ่ม",
)

# ── System Prompts ────────────────────────────────────────────────────────────

ANALYZE_SYSTEM_PROMPT = """\
🚫 ZERO TOLERANCE — ห้ามประมวลผล GIBBERISH (บังคับก่อนทุกอย่างในทุก turn):
ห้ามทำตัวเป็นผู้ช่วยที่พยายาม "เข้าใจ" หรือ "ตีความ" ข้อความที่ไม่มีความหมายเด็ดขาด!

⛔ ห้ามใช้คำต่อไปนี้ใน reply เมื่อ is_valid=false — เด็ดขาด ไม่มีข้อยกเว้น:
   "เข้าใจแล้ว" / "ขอบคุณ" / "เยี่ยมเลย" / "ดีมาก" / "น่าสนใจ" / "โอเค" / "เข้าใจ" / "ออเออ"
   → reply ที่ถูกต้องเมื่อ is_valid=false: "ขออภัยครับ ฉันอ่านข้อความนี้ไม่เข้าใจ
     รบกวนพิมพ์อธิบายใหม่อีกครั้งได้ไหมครับ?" แล้วทวนคำถามเดิมซ้ำ

ถ้าข้อความล่าสุดของผู้ใช้เข้าข่ายกรณีใดกรณีหนึ่งด้านล่าง → MUST ตั้ง is_valid=false ทันที:
  ✗ มั่วแป้นพิมพ์ไทย: "กดใดใก" / "ฟหกด" / "หกฟด่าส" / "ฟดสาก" / "ดาฟฟดาส"
    → สังเกต: ตัวอักษรไม่ประกอบเป็นคำจริง ไม่สามารถอ่านออกเสียงได้อย่างมีความหมาย
  ✗ มั่วแป้นพิมพ์ EN: "asdfgh" / "qwerty" / "zxcvbn" / "hjkl"
  ✗ สั้น/ไม่มีความหมาย: "ก็ได้" / "ไม่รู้" / "555" / "ok" / "เออ"
  ✗ Off-topic สิ้นเชิง: ขอให้ AI ทำงาน / ถามข่าว / ขอเกม (ไม่เกี่ยวกับตัวผู้ใช้เลย)

เมื่อ is_valid=false: "reply" = (① ตักเตือนสุภาพ ห้ามขอบคุณ/ออเออ) + (② ทวนคำถามเดิมซ้ำทันที)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

คุณคือผู้เชี่ยวชาญด้านจิตวิทยาบุคลิกภาพ MBTI และ Jungian Cognitive Functions
มีประสบการณ์ประเมิน MBTI กว่า 20 ปี และมีความแม่นยำสูง

━━━ ภารกิจ ━━━
ชวนผู้ใช้สนทนาอย่างเป็นธรรมชาติ เพื่อวิเคราะห์บุคลิกภาพ MBTI ที่แท้จริง
โดยอาศัยข้อมูลเชิงลึกจากกระบวนการคิด พฤติกรรม และค่านิยม ไม่ใช่แค่ความชอบผิวเผิน

━━━ กฎเหล็ก (ต้องปฏิบัติเคร่งครัด) ━━━
1. ห้ามด่วนสรุปก่อน 5 รอบ: ต้องรวบรวมข้อมูลให้เพียงพออย่างน้อย 5 รอบสนทนา
2. ห้ามถามซ้ำ: ตรวจสอบ Chat History ทุกครั้ง อย่าถามประเด็นเดิมที่ได้ข้อมูลไปแล้ว
3. ถามเจาะลึก Cognitive Functions เท่านั้น — ไม่ถามผิวเผิน
4. วิเคราะห์ Behavioral Signals จากรูปแบบการเขียนด้วย (ดูรายละเอียดด้านล่าง)
5. เมื่อวิเคราะห์ครบทุก dimension แล้ว ไม่ต้องรอครบ 10 รอบ — สรุปผลได้ทันที (Early Exit)

🚨 CRITICAL RULE — อ่านและปฏิบัติตามทุกครั้ง:
   ทันทีที่ "reply" ของคุณมีข้อความใดก็ตามที่เชิญผู้ใช้ดูผลลัพธ์ กดปุ่ม หรือบอกว่าวิเคราะห์เสร็จแล้ว
   คุณ MUST ตั้งค่า "show_result": true ใน JSON เสมอ
   ห้ามตั้ง "show_result": false ในกรณีนี้ เด็ดขาด ไม่ว่ากรณีใดทั้งสิ้น
   → ตัวอย่าง: ถ้า reply มีคำว่า "ดูผล" / "กดปุ่ม" / "วิเคราะห์ครบ" / "ผลลัพธ์" → show_result ต้อง true

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

━━━ ขั้นตอนที่ 1: ประเมินข้อความล่าสุด (Strict Answer Validation) ━━━
ข้อความล่าสุดของผู้ใช้จะถูกระบุชัดเจนในส่วน ⚠️ ของ prompt — ให้ประเมินโดยอิงกฎด้านล่างนี้เป็นอันดับแรก

🚨 บังคับ is_valid = false ทันที ถ้าพบกรณีใดกรณีหนึ่งต่อไปนี้:

  ❌ กรณีที่ 1 — มั่วแป้นพิมพ์ (Gibberish / Keyboard Mashing):
     ข้อความที่ไม่ใช่คำจริงในภาษาไทยหรืออังกฤษ ตัวอักษรสลับกันไม่มีรูปแบบภาษา อ่านออกเสียงไม่ได้
     ตัวอย่าง: "อีหกาดฟ้าดาฟ" / "ฟดสากหล" / "asdfghjk" / "ฟหกดเาสว" / "qwerty1234" / "ดาฟฟดาส"
     → วิธีสังเกต: ไม่มีคำที่มีความหมายปรากฏในประโยคนั้นเลยแม้แต่คำเดียว

  ❌ กรณีที่ 2 — คำหยาบ/สบถ (Profanity):
     ข้อความที่มีคำหยาบ คำสบถ หรือภาษาที่ไม่สุภาพ ไม่ว่าจะในบริบทใดก็ตาม

  ❌ กรณีที่ 3 — สั้นเกินไป/ไม่มีความหมาย (Too Short / Meaningless):
     เช่น "ก็ได้" / "ไม่รู้" / "อาจจะ" / "555" / "ok" / "เออ" / "ใช่" / "ครับ" / "ค่ะ" / "ก็"

  ❌ กรณีที่ 4 — ตอบผิดบริบทสิ้นเชิง (Completely Off-topic):
     ข้อความที่ไม่เกี่ยวกับตัวเองเลย วิเคราะห์ MBTI ไม่ได้เลย
     เช่น: "ช่วยเขียนโค้ดหน่อย" / "แนะนำร้านอาหาร" / "ข่าวบอลวันนี้เป็นยังไง"
     ข้อยกเว้น: ถ้าตอบนอกเรื่องบ้าง แต่ยังแอบบอกบุคลิก/นิสัยตัวเอง = valid ได้

ตั้งค่า is_valid = true ถ้าข้อความ:
  ✓ ตอบคำถามที่ AI ถามไปก่อนหน้า หรือให้ข้อมูลเกี่ยวกับตัวเองที่วิเคราะห์ได้
  ✓ เล่าเรื่องราว พฤติกรรม ความคิด หรือความรู้สึกของตัวเอง
  ✓ แม้จะนอกเรื่องบ้าง แต่ยังให้เบาะแสชีวิตจริงที่อนุมาน MBTI ได้

━━━ ขั้นตอนที่ 2: สร้าง Reply ตามผล Validation ━━━

เมื่อ is_valid = true:
  → วิเคราะห์ข้อมูลทั้งหมดในประวัติการสนทนา
  → ตอบรับสิ่งที่ผู้ใช้พูด + ถามเจาะลึก Cognitive Functions ต่อไป
  → อัปเดต partial_scores และ dimension_confidence ตามข้อมูลใหม่

เมื่อ is_valid = false — MUST ทำเสมอ ห้ามเบี่ยงเบน:
  ① "reply" ต้องประกอบด้วย 2 ส่วนนี้เท่านั้น:
     ส่วน A: ตักเตือนสุภาพ 1-2 ประโยค (บอกว่าต้องการข้อมูลอะไร เพราะอะไร)
     ส่วน B: ทวนคำถามเดิมที่ AI ถามไปครั้งล่าสุดซ้ำทันที (copy คำถามมาได้เลย)
  ② ห้ามดำเนินสนทนาต่อหรือถามเรื่องใหม่โดยเด็ดขาด
  ③ "show_result" ต้อง false เสมอ
  ④ "partial_scores" ใช้ค่าจากการสนทนาก่อนหน้าเท่านั้น ห้ามรวมข้อความ invalid นี้

━━━ Chain of Thought — คิดก่อนตอบ (บังคับทุก turn) ━━━
ก่อนตัดสินใจ is_valid ทุกครั้ง ต้องเขียน "reasoning" ลงใน JSON ก่อนเสมอ:
  → วิเคราะห์: ข้อความนี้มีคำจริงในภาษาไทย/อังกฤษหรือไม่? เป็น keyboard mashing หรือไม่? เพราะอะไร?
  → reasoning ต้องสอดคล้องกับ is_valid เสมอ — ห้าม reasoning บอกว่า gibberish แต่ is_valid=true

━━━ Format การตอบ (JSON เท่านั้น) ━━━
{
  "reasoning": "<คิดก่อนตอบ — วิเคราะห์ข้อความล่าสุดของผู้ใช้ก่อน: มีความหมายไหม? gibberish ไหม? เพราะอะไร?>",
  "is_valid": <true | false>,
  "reply": "<ถ้า valid: ตอบรับ+ถามต่อ / ถ้า invalid: ห้ามขอบคุณ/ออเออ — ใช้แค่ 'ขออภัยครับ...' + ทวนคำถามเดิม>",
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
  - show_result = true ได้เมื่อ: is_valid=true AND วิเคราะห์ครบทุก dimension
  - ไม่จำเป็นต้องรอครบ 10 รอบ — ถ้าข้อมูลพอแล้วให้จบได้เลย (Early Exit)
  - ⚠️ ถ้า reply บอกให้ผู้ใช้กดปุ่มดูผล → show_result ต้อง true เสมอ ห้ามตั้ง false
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

def _models_for_key(api_key: Optional[str]):
    """
    Return (analyze_model, finalize_model) for the given key.
    When api_key is provided it takes precedence over the server env key;
    the global client is reconfigured under a lock so concurrent requests
    don't interfere with each other.
    """
    import google.generativeai as genai
    key = (api_key or "").strip()
    if not key:
        return _model_analyze, _model_finalize

    with _key_lock:
        genai.configure(api_key=key)
        gen_cfg = {"response_mime_type": "application/json"}
        m_analyze = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=ANALYZE_SYSTEM_PROMPT,
            generation_config=gen_cfg,
        )
        m_finalize = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=FINALIZE_SYSTEM_PROMPT,
            generation_config=gen_cfg,
        )
        # Restore server key so the global models stay valid after this call
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
        return m_analyze, m_finalize


def chat_analyze(turns: List[Dict], user_turn_count: int, api_key: Optional[str] = None) -> Optional[Dict]:
    """
    ส่ง full chat history → Gemini วิเคราะห์ → reply + scores + confidence

    api_key: ถ้าผู้ใช้ส่ง key มาเองจาก frontend จะใช้ key นั้น
             ถ้าไม่มีจะ fallback ไปใช้ GEMINI_API_KEY จาก .env

    show_result = true เมื่อ:
      - user_turn_count >= MIN_USER_TURNS_FOR_RESULT (10)
      - AND dimension_confidence ทุกด้าน >= 0.80
    """
    user_key = (api_key or "").strip()
    if user_key:
        model_analyze, _ = _models_for_key(user_key)
    else:
        if not is_available():
            return None
        model_analyze = _model_analyze

    # Separate last user message so Gemini evaluates it explicitly before proceeding
    last_user_msg = ""
    last_user_idx = -1
    for i in range(len(turns) - 1, -1, -1):
        if turns[i]["role"] == "user":
            last_user_msg = turns[i]["text"]
            last_user_idx = i
            break

    # History = all turns except the last user message
    prev_turns = [t for i, t in enumerate(turns) if i != last_user_idx]
    history_text = _format_history(prev_turns)
    prev_user_count = len([t for t in prev_turns if t["role"] == "user"])

    prompt = (
        f"บทสนทนาก่อนหน้า ({prev_user_count} รอบจากผู้ใช้):\n"
        f"{'─' * 50}\n"
        f"{history_text if history_text else '(ยังไม่มีบทสนทนาก่อนหน้า)'}\n"
        f"{'─' * 50}\n\n"
        f"⚠️  ข้อความล่าสุดจากผู้ใช้ที่ต้องประเมิน Validation ก่อน:\n"
        f"「{last_user_msg}」\n\n"
        f"ผู้ใช้ส่งข้อความมาแล้ว {user_turn_count} ครั้ง\n"
        f"ขั้นต่ำที่ต้องสนทนา: {MIN_USER_TURNS_FOR_RESULT} รอบ\n\n"
        f"ขั้นตอน:\n"
        f"1. ประเมิน is_valid ของ「{last_user_msg}」ตาม STRICT VALIDATION RULES ก่อนเสมอ\n"
        f"2. ถ้า is_valid=false → reply = ตักเตือนสุภาพ + ทวนคำถามเดิมจากบทสนทนาก่อนหน้า\n"
        f"3. ถ้า is_valid=true → วิเคราะห์บทสนทนาทั้งหมดและถามเจาะลึกต่อ\n"
        f"ตอบตาม JSON format ที่กำหนดเท่านั้น"
    )

    result = _call(model_analyze, prompt)
    if result is None:
        return None

    # ── is_valid: default True เมื่อ Gemini ไม่ส่งมา (safe fallback)
    is_valid: bool = bool(result.get("is_valid", True))
    result["is_valid"] = is_valid

    # ── Validate + fix scores
    result["partial_scores"] = _fix_pairs(result.get("partial_scores", {}))
    dim_conf = result.get("dimension_confidence", {"EI": 0.0, "SN": 0.0, "TF": 0.0, "JP": 0.0})
    result["dimension_confidence"] = dim_conf
    result.setdefault("confidence", sum(dim_conf.values()) / 4)
    result.setdefault("behavioral_signals", "")

    # ── Normalise reply field ─────────────────────────────────────────────────
    # Gemini sometimes uses "reply_message" or "message" instead of "reply"
    if "reply" not in result:
        result["reply"] = (
            result.pop("reply_message", None)
            or result.pop("message", None)
            or "เล่าต่อได้เลยนะ 😊"
        )
    elif not result["reply"]:
        result["reply"] = "เล่าต่อได้เลยนะ 😊"

    # ── show_result decision: 3-layer logic ──────────────────────────────────
    #
    # Layer 1 — Gemini JSON flag (primary)
    gemini_flag = bool(result.get("show_result", False))
    #
    # Layer 2 — Safety-net keyword check (fallback when Gemini sets flag incorrectly)
    # Read the normalised reply field — guaranteed to exist at this point
    reply_text = result["reply"].lower()
    keyword_triggered = any(kw in reply_text for kw in _RESULT_TRIGGER_KEYWORDS)
    if keyword_triggered and not gemini_flag:
        logger.warning(
            "Safety-net [gemini_client]: keyword detected but show_result=false — forcing true. "
            f"reply[:80]={result['reply'][:80]!r}"
        )
    #
    # Layer 3 — Hard guards: is_valid AND minimum turns (sanity check only)
    enough_turns = user_turn_count >= MIN_USER_TURNS_FOR_RESULT
    #
    result["show_result"] = is_valid and enough_turns and (gemini_flag or keyword_triggered)

    return result


def chat_finalize(turns: List[Dict], api_key: Optional[str] = None) -> Optional[Dict]:
    """
    ส่ง full chat history → Gemini สรุป MBTI type พร้อม reasoning

    api_key: ถ้าผู้ใช้ส่ง key มาเองจาก frontend จะใช้ key นั้น
             ถ้าไม่มีจะ fallback ไปใช้ GEMINI_API_KEY จาก .env
    """
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
