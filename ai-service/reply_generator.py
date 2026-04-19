"""
Reply Generator for FAB Chat — Psychometrics Expert Fallback.

ใช้เมื่อ Gemini ไม่พร้อม (ไม่มี API key หรือ call ล้มเหลว)
ถามเจาะลึก Cognitive Functions, อย่างน้อย 10 รอบ ก่อนสรุปผล

กฎเหล็ก:
  1. ห้ามถามคำถามเดิมซ้ำ
  2. ข้าม dimension ที่ resolved แล้ว
  3. สรุปได้เมื่อ ≥ 10 รอบ AND ทุก dimension resolved
"""

import random
from typing import List, Dict, Optional, Set

# ── ชุดคำถามเจาะลึก Cognitive Functions ──────────────────────────────────────
FOLLOW_UP_QUESTIONS: Dict[str, List[str]] = {
    "EI": [
        "หลังจากงานสังสรรค์หรือประชุมยาวๆ คุณรู้สึกได้พลังเพิ่มขึ้นหรือหมดแรง?",
        "เวลาต้องตัดสินใจสำคัญ คุณชอบคิดคนเดียวก่อน หรือชอบพูดคุยกับคนอื่นเพื่อระดมความคิด?",
        "คุณมักคิด 'ออกเสียง' (พูดเพื่อเรียบเรียงความคิด) หรือคิดในหัวจนชัดก่อนแล้วค่อยพูด?",
        "เวลาอยู่กับคนหมู่มาก คุณรู้สึกกระฉับกระเฉงหรืออยากหาที่เงียบๆ?",
    ],
    "JP": [
        "คุณรู้สึกโล่งใจมากกว่าเมื่อ: ตัดสินใจเสร็จและปิดเรื่อง หรือยังมีตัวเลือกเปิดอยู่?",
        "เวลาวางแผนท่องเที่ยว คุณชอบจองทุกอย่างล่วงหน้า หรือรู้สึกสนุกกับการ improvise?",
        "ถ้าแผนเปลี่ยนกะทันหัน คุณรู้สึกอย่างไร — รำคาญหรือตื่นเต้นกับโอกาสใหม่?",
        "คุณมักทำงานให้เสร็จก่อน deadline หรือ deadline คือแรงผลักดันสำคัญที่ทำให้ทำเสร็จ?",
    ],
    "TF": [
        "เวลาเพื่อนมาปรึกษาปัญหา คุณรู้สึกอยากหาทางออกที่ดีที่สุด หรืออยากให้เขาเล่าจนรู้สึกว่าถูกเข้าใจก่อน?",
        "เวลาตัดสินใจ ความสอดคล้องกับหลักการและตรรกะ หรือผลกระทบต่อคนรอบข้าง สำคัญกว่าสำหรับคุณ?",
        "ระหว่างความยุติธรรมกับความเห็นอกเห็นใจ ถ้าต้องเลือก คุณจะเลือกอะไร?",
        "เวลารู้สึกขัดแย้งกับเพื่อน คุณวิเคราะห์ว่าใครถูกก่อน หรือพยายามรักษาความสัมพันธ์ก่อน?",
    ],
    "SN": [
        "เวลาจำเหตุการณ์ในอดีต คุณจำรายละเอียดเล็กน้อย (สี เสียง ความรู้สึกทางกาย) หรือจำความหมายและบทเรียนของเหตุการณ์?",
        "เวลาแก้ปัญหา คุณมักมองที่ข้อมูลและข้อเท็จจริงที่มีอยู่ หรือมองหาภาพรวมและแบบแผนที่ซ่อนอยู่?",
        "เวลาระดมไอเดีย คุณมักได้ไอเดียหลายอย่างพร้อมกัน หรือเห็นภาพชัดๆ ว่าควรไปทิศทางไหน?",
        "คุณเชื่อมั่นในประสบการณ์จริงมากกว่า หรือเชื่อมั่นในสัญชาตญาณและการคาดการณ์มากกว่า?",
    ],
}

# ลำดับที่ถามก่อน-หลัง (ถามง่าย → ถามยาก)
DIM_ORDER = ["EI", "JP", "TF", "SN"]

ACKNOWLEDGEMENTS: List[str] = [
    "เข้าใจแล้ว!",
    "น่าสนใจมากเลย",
    "ขอบคุณที่เล่าให้ฟัง",
    "โอเค ฉันเข้าใจคุณมากขึ้นแล้ว",
    "ดีมากเลย",
    "เยี่ยมเลย",
]

GREETING = (
    "สวัสดี! ฉันคือ AI ที่จะช่วยวิเคราะห์บุคลิกภาพ MBTI ของคุณผ่านการสนทนา "
    "ไม่ต้องตอบแบบทดสอบนะ แค่เล่าให้ฟังแบบธรรมชาติเลย 😊 "
    "เริ่มเลยได้เลย — วันนี้คุณเป็นยังไงบ้าง? หรืออยากเล่าอะไรให้ฟังก็ได้!"
)

READY_HINT = (
    "\n\n✨ ฉันได้ข้อมูลจากการสนทนาของเราพอสมควรแล้ว "
    "และสนทนาครบ 10 รอบแล้ว กดปุ่ม 'ดูผล MBTI' ได้เลยนะ!"
)

ALL_DONE_HINT = (
    "\n\n🎯 ฉันวิเคราะห์ครบทุกด้านของบุคลิกภาพแล้ว "
    "กดปุ่ม 'ดูผล MBTI' เพื่อดูผลการวิเคราะห์โดยละเอียดได้เลย!"
)


def get_asked_questions(ai_turns: List[Dict]) -> Set[str]:
    """
    ดึงชุดคำถามที่เคยถามไปแล้วจาก AI turns
    เทียบกับทุก variant ใน FOLLOW_UP_QUESTIONS
    """
    asked: Set[str] = set()
    all_q: List[str] = [q for qs in FOLLOW_UP_QUESTIONS.values() for q in qs]
    for turn in ai_turns:
        if turn.get("role") != "ai":
            continue
        text = turn.get("text", "")
        for q in all_q:
            if q in text:
                asked.add(q)
    return asked


def get_asked_dims(ai_turns: List[Dict]) -> Set[str]:
    """
    ดู dimension ไหนบ้างที่ถูกถามไปแล้วอย่างน้อย 1 คำถาม
    """
    asked_qs = get_asked_questions(ai_turns)
    asked_dims: Set[str] = set()
    for dim, questions in FOLLOW_UP_QUESTIONS.items():
        if any(q in asked_qs for q in questions):
            asked_dims.add(dim)
    return asked_dims


def pick_next_question(
    resolved_dims: Set[str],
    asked_questions: Set[str],
    ai_turns: List[Dict],
) -> Optional[tuple[str, str]]:
    """
    เลือก (dimension, question) ที่เหมาะสมถัดไป:
    - ข้าม dimension ที่ resolved แล้ว
    - ข้ามคำถามที่เคยถามแล้ว
    - ถ้าหมด dimension → return None (signal ให้สรุปผล)

    Returns:
        (dim, question_text) หรือ None ถ้าครบแล้ว
    """
    for dim in DIM_ORDER:
        if dim in resolved_dims:
            continue  # กฎข้อ 2: ข้าม dimension ที่ได้ข้อมูลครบแล้ว
        # หาคำถามที่ยังไม่เคยถาม
        available = [q for q in FOLLOW_UP_QUESTIONS[dim] if q not in asked_questions]
        if available:
            return dim, random.choice(available)
        # ถ้า exhaust คำถามทุกอันใน dim นี้แล้ว → ข้ามไปอันถัดไป

    return None  # ครบทุก dimension แล้ว


def generate_reply(
    resolved_dims: Set[str],
    all_turns: List[Dict],
    show_result: bool,
) -> str:
    """
    สร้าง AI reply โดยปฏิบัติตามกฎเหล็กทั้ง 3:
    1. ไม่ถามคำถามซ้ำ (ดูจาก asked_questions)
    2. ข้าม dimension ที่ resolved แล้ว
    3. ถ้าครบ → หยุดถามและบอก hint ให้ดูผล

    Args:
        resolved_dims: set ของ dimension ที่มีข้อมูลชัดเจนพอแล้ว
        all_turns:     ทุก turn ใน session (ใช้ดึง asked_questions)
        show_result:   flag จาก confidence calculation

    Returns:
        reply string
    """
    ai_turns = [t for t in all_turns if t.get("role") == "ai"]
    asked_questions = get_asked_questions(ai_turns)
    last_user_text = next(
        (t["text"] for t in reversed(all_turns) if t.get("role") == "user"), ""
    )
    ack = random.choice(ACKNOWLEDGEMENTS)

    # กฎข้อ 3: ถ้าทุก dimension resolved หรือ show_result → สรุปผลทันที
    all_resolved = len(resolved_dims) >= 4
    if all_resolved:
        return f"{ack} {ALL_DONE_HINT}"

    if show_result:
        # ยังถามต่อได้ แต่แนะนำให้ดูผล
        result = pick_next_question(resolved_dims, asked_questions, ai_turns)
        if result is None:
            return f"{ack} {ALL_DONE_HINT}"
        _, question = result
        return f"{ack} {question}{READY_HINT}"

    # ยังไม่ show_result → ถาม follow-up ต่อตามปกติ
    result = pick_next_question(resolved_dims, asked_questions, ai_turns)
    if result is None:
        # ไม่มีคำถามเหลือแล้ว → บังคับ show result
        return f"{ack} {ALL_DONE_HINT}"

    _, question = result
    return f"{ack} {question}"
