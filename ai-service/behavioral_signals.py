"""
Behavioral Signal Extractor for FAB Chat MBTI analysis.
สกัด MBTI dimension signals จาก free-text conversation turns
ใช้ 3 วิธีประกอบกัน: SBERT cosine, keyword matching, linguistic style
"""

from __future__ import annotations
import re
from typing import List, Dict, Optional
import numpy as np

# ── Keyword signals (ไทย + อังกฤษ) ────────────────────────────────────────
KEYWORD_SIGNALS: Dict[str, List[str]] = {
    "E": ["เพื่อน", "งานปาร์ตี้", "ชอบคุย", "ไปกับคน", "สังสรรค์", "ออกไปข้างนอก",
          "ชอบเจอคน", "meet people", "social", "party", "friends", "outgoing", "people"],
    "I": ["คนเดียว", "เงียบ", "ชาร์จพลัง", "อยู่บ้าน", "ไม่ชอบสังสรรค์", "พักคนเดียว",
          "อยู่คนเดียว", "introvert", "alone", "solitude", "quiet", "recharge", "by myself"],
    "S": ["รายละเอียด", "ข้อเท็จจริง", "ลงมือทำ", "ประสบการณ์จริง", "ใช้งานได้จริง", "เป็นรูปธรรม",
          "practical", "concrete", "facts", "detail", "experience", "realistic", "hands-on"],
    "N": ["แนวคิด", "ภาพรวม", "จินตนาการ", "ไอเดีย", "อนาคต", "ความเป็นไปได้", "ทฤษฎี",
          "abstract", "vision", "idea", "concept", "future", "imagine", "pattern", "theory"],
    "T": ["วิเคราะห์", "ตรรกะ", "เหตุผล", "หลักการ", "ความจริง", "ประสิทธิภาพ", "ข้อเท็จจริง",
          "logic", "analyze", "objective", "reason", "think", "efficient", "rational"],
    "F": ["รู้สึก", "ห่วงใย", "ความสัมพันธ์", "เห็นอกเห็นใจ", "ความรู้สึก", "ให้ความสำคัญ",
          "empathy", "care", "feel", "feeling", "harmony", "values", "people matter"],
    "J": ["วางแผน", "ตารางเวลา", "เป้าหมาย", "เป็นระเบียบ", "ตัดสินใจ", "ชัดเจน", "กำหนดการ",
          "plan", "organize", "schedule", "structure", "decide", "deadline", "order"],
    "P": ["ยืดหยุ่น", "ตามสบาย", "แล้วแต่สถานการณ์", "ปรับตัว", "เปิดรับ", "ไม่วางแผน",
          "flexible", "spontaneous", "adapt", "open", "improvise", "go with the flow"],
}

# ── Linguistic style patterns (regex) ────────────────────────────────────────
STYLE_PATTERNS: Dict[str, List[str]] = {
    "J": [
        r"(วางแผน|plan).{0,30}(ก่อน|first)",
        r"(ต้องการ|need).{0,20}(ชัดเจน|clear|structure)",
        r"\bstep\s*\d\b",
        r"(ตาราง|schedule|deadline|to-do)",
        r"(เสร็จ|finish|complete).{0,20}(ก่อน|first)",
    ],
    "P": [
        r"(แล้วแต่|depends|it depends)",
        r"(ปล่อย|ไหล|go with)",
        r"(ยืดหยุ่น|flexible|spontan)",
        r"(ค่อย|later|sometime)",
    ],
    "T": [
        r"(เพราะ|because).{0,40}(ดังนั้น|therefore|so)",
        r"(ข้อดี|pros).{0,20}(ข้อเสีย|cons)",
        r"(วิเคราะห์|analyz|logic|เหตุผล)",
        r"(ประสิทธิภาพ|efficient|optimal)",
    ],
    "F": [
        r"(รู้สึก(ว่า)?|i feel|makes me)",
        r"(ทำให้|makes).{0,20}(เสียใจ|sad|happy|upset|hurt)",
        r"(ห่วง|care|concern).{0,20}(คน|people|others)",
        r"(ความสัมพันธ์|relationship|connect)",
    ],
}


class BehavioralSignalExtractor:
    """
    วิเคราะห์ user turns และสกัด MBTI signal โดยใช้:
    1) SBERT cosine similarity กับ anchor phrases (ถ้า SBERT โหลดสำเร็จ)
    2) Keyword matching ไทย/อังกฤษ
    3) Linguistic style regex patterns

    เมื่อ SBERT ไม่พร้อมใช้ → ใช้ 2 + 3 เท่านั้น (ยังทำงานได้)
    """

    def __init__(self, sbert_model=None, anchor_embeddings: Optional[Dict[str, np.ndarray]] = None):
        self.sbert = sbert_model
        self.anchor_embeddings = anchor_embeddings  # pre-computed vectors จาก predictor.py

    def extract(self, user_texts: List[str]) -> Dict[str, Dict[str, int]]:
        """
        รับ list of user messages → คืน normalized signals ต่อ dimension

        Returns:
            {
              "EI": {"E": 35, "I": 65},
              "SN": {"S": 50, "N": 50},
              "TF": {"T": 60, "F": 40},
              "JP": {"J": 70, "P": 30},
            }
        """
        raw: Dict[str, float] = {pole: 0.0 for pole in "EISNTFJP"}

        for text in user_texts:
            text_lower = text.lower()

            # ── Method 1: SBERT cosine (weight 0.5 per unit) ────────────
            if self.sbert is not None and self.anchor_embeddings:
                try:
                    vec = self.sbert.encode([text], normalize_embeddings=True)[0]
                    for pole, anchor_vec in self.anchor_embeddings.items():
                        cos = float(np.dot(vec, anchor_vec))
                        raw[pole] += max(0.0, cos) * 0.5
                except Exception:
                    pass  # graceful fallback

            # ── Method 2: Keyword matching (weight 0.3 per hit) ──────────
            for pole, keywords in KEYWORD_SIGNALS.items():
                hits = sum(1 for kw in keywords if kw in text_lower)
                raw[pole] += hits * 0.3

            # ── Method 3: Linguistic style regex (weight 0.2 per hit) ────
            for pole, patterns in STYLE_PATTERNS.items():
                hits = sum(
                    1 for p in patterns
                    if re.search(p, text, re.IGNORECASE)
                )
                raw[pole] += hits * 0.2

        return self._normalize(raw)

    @staticmethod
    def _normalize(raw: Dict[str, float]) -> Dict[str, Dict[str, int]]:
        result: Dict[str, Dict[str, int]] = {}
        for dim, (p1, p2) in [("EI", ("E", "I")), ("SN", ("S", "N")),
                               ("TF", ("T", "F")), ("JP", ("J", "P"))]:
            a, b = raw[p1], raw[p2]
            total = a + b if (a + b) > 0.0 else 1.0
            pct_a = round(a / total * 100)
            result[dim] = {p1: pct_a, p2: 100 - pct_a}
        return result
