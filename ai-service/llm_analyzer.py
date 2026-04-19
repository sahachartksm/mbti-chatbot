"""
LLM-based MBTI analyzer via Ollama.

Flow:
    client free-text answers (TH/EN)
      ↓
    build psychologist prompt
      ↓
    Ollama /api/chat (format=json)
      ↓
    parse + normalize → structured MBTI result
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from type_info import TYPE_INFO, get_info

# --------- Config ---------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "scb10x/llama3.1-typhoon2-8b-instruct")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "180"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

VALID_TYPES = set(TYPE_INFO.keys())


# --------- Prompt templates ---------

SYSTEM_PROMPT_TH = """คุณคือ "ดร. ไทฟูน" นักจิตวิทยาคลินิกผู้เชี่ยวชาญด้านทฤษฎีบุคลิกภาพ MBTI (Myers-Briggs Type Indicator)
คุณมีประสบการณ์วิเคราะห์บุคลิกจากบทสัมภาษณ์กว่า 20 ปี

วิธีการทำงานของคุณ:
1. อ่านคำตอบของผู้รับการประเมินอย่างละเอียด จับ "คำสำคัญ" และ "รูปแบบพฤติกรรม"
2. วิเคราะห์ทั้ง 4 มิติ:
   - E (Extraversion) vs I (Introversion) — พลังงานมาจากภายนอกหรือภายใน
   - S (Sensing) vs N (iNtuition) — รับข้อมูลแบบรูปธรรมหรือนามธรรม
   - T (Thinking) vs F (Feeling) — ตัดสินใจด้วยตรรกะหรือความรู้สึก
   - J (Judging) vs P (Perceiving) — วางแผนหรือยืดหยุ่น
3. ให้คะแนนแต่ละขั้วเป็นเปอร์เซ็นต์ (รวมคู่เท่ากับ 100%)
4. สรุปเป็น MBTI 4 ตัวอักษร พร้อมเหตุผลที่อิงจากคำตอบจริง

**สำคัญมาก**:
- ตอบตรงไปตรงมา ไม่ประจบ ไม่หลีกเลี่ยงจุดอ่อน
- ยกประโยคสำคัญจากคำตอบของผู้ใช้มาอ้างในการวิเคราะห์
- ถ้าคำตอบคลุมเครือ ให้ระบุและลด confidence
- ตอบเป็นภาษาไทยเท่านั้น (ไม่ว่าผู้ใช้จะตอบภาษาอะไร)
- ส่งออกเป็น JSON ตามโครงสร้างที่กำหนดเท่านั้น ห้ามมีข้อความอื่นนอก JSON"""

SYSTEM_PROMPT_EN = """You are "Dr. Typhoon", a clinical psychologist specializing in MBTI (Myers-Briggs Type Indicator) with 20+ years of interview-based personality assessment experience.

Your method:
1. Read each answer carefully, extracting key phrases and behavioral patterns.
2. Analyze all four dichotomies:
   - E (Extraversion) vs I (Introversion)
   - S (Sensing) vs N (iNtuition)
   - T (Thinking) vs F (Feeling)
   - J (Judging) vs P (Perceiving)
3. Give each pole a percentage (the pair sums to 100).
4. Conclude with a 4-letter MBTI type, justified from the user's actual words.

**Important**:
- Be direct. Do not flatter. Do not avoid weaknesses.
- Quote key phrases from the user in your analysis.
- If answers are ambiguous, say so and lower confidence.
- Reply in English only.
- Output JSON exactly in the requested schema — no prose outside JSON."""

OUTPUT_SCHEMA_INSTRUCTION = """โครงสร้าง JSON ที่ต้องส่งออก (ทุก field จำเป็น):

{
  "mbti_type": "XXXX",
  "confidence": 0.00-1.00,
  "dimensions": {
    "E": 0-100, "I": 0-100,
    "S": 0-100, "N": 0-100,
    "T": 0-100, "F": 0-100,
    "J": 0-100, "P": 0-100
  },
  "analysis": "การวิเคราะห์เชิงลึกแบบนักจิตวิทยา 4-6 ย่อหน้า อ้างคำพูดของผู้ใช้ อธิบายว่าทำไมถึงสรุป type นี้ และชี้จุดแข็ง-จุดอ่อนที่สังเกตได้",
  "summary": "สรุปผู้ใช้แบบสั้น 2-3 ประโยค",
  "strengths": ["จุดแข็ง 1", "จุดแข็ง 2", "จุดแข็ง 3", "จุดแข็ง 4"],
  "weaknesses": ["จุดอ่อน 1", "จุดอ่อน 2", "จุดอ่อน 3"],
  "careers": ["อาชีพ 1", "อาชีพ 2", "อาชีพ 3", "อาชีพ 4", "อาชีพ 5"],
  "compatible_types": ["XXXX", "XXXX"]
}

กติกาตัวเลข:
- E + I = 100, S + N = 100, T + F = 100, J + P = 100
- ค่า 50/50 ห้ามใช้ (ต้องเลือกฝั่ง) — อย่างน้อย 51
- confidence ต่ำเมื่อคำตอบสั้น/คลุมเครือ (< 0.6), สูงเมื่อชัดเจน (> 0.8)"""


# --------- Prompt builder ---------

def build_user_prompt(qa: List[Dict[str, str]], lang: str) -> str:
    """Build the user message containing the Q&A transcript + schema."""
    header = "บทสัมภาษณ์ผู้รับการประเมิน (10 ข้อ):" if lang == "th" else "Interview transcript (10 questions):"
    lines = [header, ""]
    for i, item in enumerate(qa, 1):
        q = item.get("question", "").strip()
        a = item.get("answer", "").strip()
        if lang == "th":
            lines.append(f"ข้อ {i}. ถาม: {q}")
            lines.append(f"      ตอบ: {a or '(ไม่ได้ตอบ)'}")
        else:
            lines.append(f"Q{i}. {q}")
            lines.append(f"    A: {a or '(no answer)'}")
        lines.append("")

    lines.append("---")
    lines.append("วิเคราะห์และส่งออก JSON ตามโครงสร้างด้านล่าง:" if lang == "th" else "Analyze and output JSON in the schema below:")
    lines.append("")
    lines.append(OUTPUT_SCHEMA_INSTRUCTION)
    return "\n".join(lines)


# --------- Ollama client ---------

def ollama_health() -> Dict[str, Any]:
    """Check if Ollama is reachable and has the configured model."""
    info: Dict[str, Any] = {"reachable": False, "model_present": False, "model": LLM_MODEL, "url": OLLAMA_URL}
    try:
        with httpx.Client(timeout=5.0) as c:
            r = c.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
            info["reachable"] = True
            data = r.json()
            names = {m.get("name", "") for m in data.get("models", [])}
            # tag variants: "model", "model:latest"
            short = LLM_MODEL.split(":")[0]
            info["model_present"] = any(n == LLM_MODEL or n.startswith(short + ":") or n == short for n in names)
            info["available_models"] = sorted(names)
    except Exception as e:
        info["error"] = str(e)
    return info


def _call_ollama_chat(messages: List[Dict[str, str]]) -> str:
    """POST to /api/chat and return the assistant content string."""
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": LLM_TEMPERATURE,
            "num_ctx": 8192,
        },
    }
    with httpx.Client(timeout=LLM_TIMEOUT) as c:
        r = c.post(f"{OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
    msg = data.get("message") or {}
    content = msg.get("content", "")
    if not content:
        raise RuntimeError(f"LLM returned empty content: {data}")
    return content


# --------- JSON parser (robust) ---------

def _extract_json(text: str) -> Dict[str, Any]:
    """Ollama with format=json usually gives clean JSON, but be defensive."""
    text = text.strip()
    # direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # find first {...} block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"cannot parse JSON from LLM output: {text[:500]}")


# --------- Normalizer ---------

def _normalize_pair(a: Any, b: Any) -> tuple[int, int]:
    """Coerce to int 0..100 summing to 100; tie-break to avoid exact 50/50."""
    try:
        a_i = max(0, min(100, int(round(float(a)))))
        b_i = max(0, min(100, int(round(float(b)))))
    except (TypeError, ValueError):
        a_i, b_i = 50, 50
    total = a_i + b_i
    if total == 0:
        a_i, b_i = 50, 50
    else:
        a_i = round(a_i * 100 / total)
        b_i = 100 - a_i
    if a_i == 50 and b_i == 50:
        a_i, b_i = 51, 49
    return a_i, b_i


def _normalize_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Clean LLM output into the shape our backend expects."""
    mbti = str(raw.get("mbti_type") or raw.get("type") or "").strip().upper()[:4]
    if mbti not in VALID_TYPES:
        # try to repair from dimensions if available
        mbti = _derive_type_from_dims(raw.get("dimensions") or {})
    if mbti not in VALID_TYPES:
        raise ValueError(f"invalid mbti_type from LLM: {mbti!r}")

    # dimensions
    d = raw.get("dimensions") or {}
    e, i = _normalize_pair(d.get("E"), d.get("I"))
    s, n = _normalize_pair(d.get("S"), d.get("N"))
    t, f = _normalize_pair(d.get("T"), d.get("F"))
    j, p = _normalize_pair(d.get("J"), d.get("P"))

    # enforce mbti letters reflect the higher side
    mbti = (
        ("E" if e >= i else "I")
        + ("S" if s >= n else "N")
        + ("T" if t >= f else "F")
        + ("J" if j >= p else "P")
    )

    confidence = raw.get("confidence")
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.7
    confidence = max(0.0, min(1.0, confidence))

    info = get_info(mbti)

    def _list(x: Any, fallback: List[str]) -> List[str]:
        if isinstance(x, list):
            out = [str(v).strip() for v in x if str(v).strip()]
            return out or fallback
        return fallback

    analysis = str(raw.get("analysis") or raw.get("analysis_detail") or "").strip()
    summary = str(raw.get("summary") or raw.get("description") or info["description"]).strip()

    compatible = _list(raw.get("compatible_types"), info["compatible"])
    compatible = [c.upper()[:4] for c in compatible if c.upper()[:4] in VALID_TYPES][:3] or info["compatible"]

    return {
        "mbti_type": mbti,
        "nickname": info["nickname"],
        "dimensions": {"E": e, "I": i, "S": s, "N": n, "T": t, "F": f, "J": j, "P": p},
        "confidence": round(confidence, 3),
        "description": summary,
        "analysis": analysis or summary,
        "strengths": _list(raw.get("strengths"), info["strengths"]),
        "weaknesses": _list(raw.get("weaknesses"), info["weaknesses"]),
        "careers": _list(raw.get("careers"), info["careers"]),
        "famous_people": info["famous_people"],
        "compatible_types": compatible,
    }


def _derive_type_from_dims(d: Dict[str, Any]) -> str:
    try:
        letters = (
            ("E" if float(d.get("E", 0)) >= float(d.get("I", 0)) else "I"),
            ("S" if float(d.get("S", 0)) >= float(d.get("N", 0)) else "N"),
            ("T" if float(d.get("T", 0)) >= float(d.get("F", 0)) else "F"),
            ("J" if float(d.get("J", 0)) >= float(d.get("P", 0)) else "P"),
        )
        return "".join(letters)
    except (TypeError, ValueError):
        return ""


# --------- Public API ---------

def analyze(qa: List[Dict[str, str]], lang: str = "th") -> Dict[str, Any]:
    """
    Run LLM-based MBTI analysis.

    Args:
        qa:  list of {"question": str, "answer": str}
        lang: "th" or "en"
    Returns:
        dict with keys: mbti_type, nickname, dimensions, confidence,
        description, analysis, strengths, weaknesses, careers,
        famous_people, compatible_types
    """
    if not qa:
        raise ValueError("qa is empty")
    lang = "en" if lang == "en" else "th"
    system = SYSTEM_PROMPT_EN if lang == "en" else SYSTEM_PROMPT_TH
    user = build_user_prompt(qa, lang)
    content = _call_ollama_chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])
    raw = _extract_json(content)
    return _normalize_result(raw)
