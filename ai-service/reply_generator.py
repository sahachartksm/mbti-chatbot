"""
Reply Generator for FAB Chat — Smart version.

กฎเหล็ก:
  1. ห้ามถามคำถามเดิมซ้ำกับที่เคยถามไปแล้วใน chat history
  2. ถ้าได้ข้อมูล dimension ใดครบแล้ว (resolved) → ข้ามไป dimension ถัดไปทันที
  3. ถ้าครบทุก dimension หรือ confidence สูงพอ → หยุดถามแล้วให้ผล

ลำดับ dimension ที่ถามตามลำดับความสำคัญ (สังเกตได้ง่ายที่สุดก่อน):
  EI → JP → TF → SN
"""

import random
from typing import List, Dict, Optional, Set

# ── ชุดคำถาม: แต่ละ dimension มีหลาย variant ────────────────────────────────
# key = dimension, value = list of question strings (แต่ละอันไม่ซ้ำกัน)
FOLLOW_UP_QUESTIONS: Dict[str, List[str]] = {
    "EI": [
        "ช่วงสุดสัปดาห์คุณชอบทำอะไร? อยู่บ้านหรือออกไปข้างนอกมากกว่า?",
        "ถ้าเหนื่อยหรือเครียด คุณมักจะทำอะไรเพื่อผ่อนคลาย?",
        "คุณชอบทำงานคนเดียวหรือทำงานเป็นทีมมากกว่ากัน?",
    ],
    "JP": [
        "คุณชอบวางแผนล่วงหน้าหรือปล่อยให้ทุกอย่างดำเนินไปตามสถานการณ์?",
        "ถ้าแผนเปลี่ยนกะทันหัน คุณรู้สึกอย่างไร — รำคาญหรือตื่นเต้น?",
        "คุณชอบมี to-do list และตารางเวลา หรือเดินตามสัญชาตญาณ?",
    ],
    "TF": [
        "เวลาเพื่อนมาปรึกษาปัญหา คุณมักให้คำแนะนำแก้ปัญหาหรือรับฟังและเข้าใจก่อน?",
        "คุณตัดสินใจโดยใช้เหตุผลหรือความรู้สึกเป็นหลักมากกว่า?",
        "ระหว่างความยุติธรรมกับความเห็นอกเห็นใจ อะไรสำคัญกว่าสำหรับคุณ?",
    ],
    "SN": [
        "เวลาเรียนสิ่งใหม่ คุณชอบเริ่มจากทฤษฎีก่อนหรือลงมือทำก่อนเลย?",
        "คุณมักคิดถึงอนาคตมากกว่าปัจจุบันไหม หรือชอบโฟกัสสิ่งที่อยู่ตรงหน้า?",
        "คุณสนใจแนวคิดกว้างๆ หรือรายละเอียดที่จับต้องได้มากกว่า?",
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

READY_HINT = "\n\n✨ ฉันได้ข้อมูลจากการสนทนาของเราพอสมควรแล้ว กดปุ่ม 'ดูผล MBTI' ได้เลยนะ!"

ALL_DONE_HINT = "\n\n🎯 ฉันได้ข้อมูลครบทุกด้านแล้ว! กดปุ่ม 'ดูผล MBTI' เพื่อดูผลได้เลย"


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
