"""
Predictor: ผสม rule-based + ML + (optional) text embedding
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Optional

import joblib
import numpy as np

from questions_map import QUESTION_MAP, QUESTION_CHOICES, TOTAL_QUESTIONS, DIMENSIONS
from type_info import get_info

# --------- Paths ---------
MODEL_PATH = Path(__file__).parent / "models" / "mbti_model.pkl"

# --------- Global ML state ---------
_bundle = None
_sbert = None
_sbert_failed = False
_sbert_anchors: Optional[Dict[str, np.ndarray]] = None

USE_SBERT = os.getenv("USE_SENTENCE_TRANSFORMER", "true").lower() == "true"


# --------- Anchors for free-text similarity ---------
ANCHORS = {
    "E": [
        "I enjoy being around people and feel energized by social interaction.",
        "I love parties and meeting new people.",
    ],
    "I": [
        "I recharge by spending time alone and prefer deep one-on-one conversations.",
        "I need solitude to think clearly.",
    ],
    "S": [
        "I focus on facts, concrete details, and practical experience.",
        "I trust what I can see, hear, and touch.",
    ],
    "N": [
        "I see patterns, possibilities, and future potential.",
        "I love abstract ideas and imagining what could be.",
    ],
    "T": [
        "I make decisions based on logic, reason, and objective analysis.",
        "Fairness and consistency matter most.",
    ],
    "F": [
        "I make decisions based on values, empathy, and how they affect people.",
        "Harmony and care for others drive my choices.",
    ],
    "J": [
        "I prefer structure, planning, and making decisions quickly.",
        "I love finishing things and keeping to schedules.",
    ],
    "P": [
        "I prefer flexibility, spontaneity, and keeping options open.",
        "I thrive in unpredictable situations.",
    ],
}


def load_model():
    """Load LogReg bundle lazily."""
    global _bundle
    if _bundle is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found: {MODEL_PATH}\n"
                f"Run `python train.py` first to generate it."
            )
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def load_sbert():
    """Load sentence-transformers lazily (heavy). Safe to call many times."""
    global _sbert, _sbert_anchors, _sbert_failed
    if not USE_SBERT or _sbert_failed:
        return None, None
    if _sbert is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sbert = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            _sbert_anchors = {
                letter: _sbert.encode(texts, normalize_embeddings=True).mean(axis=0)
                for letter, texts in ANCHORS.items()
            }
        except Exception as e:
            print(f"⚠ Could not load sentence-transformers: {e}. Proceeding without.")
            _sbert = None
            _sbert_failed = True
            return None, None
    return _sbert, _sbert_anchors


# ---------- Rule-based scoring ----------

def rule_based_score(answers: List[Dict]) -> Dict[str, float]:
    """
    Returns raw scores: {"E": x, "I": y, "S": ..., ...}
    """
    scores = {"E": 0.0, "I": 0.0, "S": 0.0, "N": 0.0, "T": 0.0, "F": 0.0, "J": 0.0, "P": 0.0}
    for a in answers:
        qid = a["question_id"]
        choice = a["choice_id"]
        if qid not in QUESTION_MAP:
            continue
        mapping = QUESTION_MAP[qid]["choices"]
        if choice not in mapping:
            continue
        direction, weight = mapping[choice]
        scores[direction] += weight
    return scores


def answers_to_features(answers: List[Dict]) -> np.ndarray:
    """Convert answers → feature vector (matches training encoding)."""
    # default 0 if missing (shouldn't happen if 20 answers given)
    feats = np.zeros(TOTAL_QUESTIONS, dtype=np.float32)
    by_qid = {a["question_id"]: a["choice_id"] for a in answers}
    for i, qid in enumerate(range(1, TOTAL_QUESTIONS + 1)):
        if qid not in by_qid:
            continue
        choices = QUESTION_CHOICES[qid]
        chosen = by_qid[qid]
        if chosen not in choices:
            continue
        idx = choices.index(chosen)
        max_idx = max(len(choices) - 1, 1)
        feats[i] = idx / max_idx
    return feats


# ---------- Text scoring (optional) ----------

def text_scores(free_text: str) -> Optional[Dict[str, float]]:
    """Cosine similarity ระหว่าง free_text กับ anchor แต่ละ pole"""
    sbert, anchors = load_sbert()
    if sbert is None or not anchors or not free_text.strip():
        return None
    vec = sbert.encode([free_text], normalize_embeddings=True)[0]
    out = {}
    for letter, anchor_vec in anchors.items():
        out[letter] = float(np.dot(vec, anchor_vec))  # cosine (both normalized)
    return out


# ---------- Blend & finalize ----------

def normalize_pair(a: float, b: float) -> tuple[int, int]:
    """Convert raw (a, b) → int percentages that sum to 100"""
    s = a + b
    if s <= 0:
        return 50, 50
    pa = round(a / s * 100)
    return pa, 100 - pa


def pick_dimension(a_score: float, b_score: float, first_letter: str, second_letter: str) -> str:
    """Return letter of the winning pole"""
    return first_letter if a_score >= b_score else second_letter


def predict(answers: List[Dict], free_text: Optional[str] = None) -> Dict:
    """
    Main entrypoint.
    answers: [{"question_id": int, "choice_id": str}, ...]
    free_text: optional string
    """
    # 1. Rule-based
    rule = rule_based_score(answers)

    # 2. ML
    bundle = load_model()
    feats = answers_to_features(answers).reshape(1, -1)
    X = bundle["scaler"].transform(feats)
    ml_probs = {}   # dim -> P(first letter) (E / S / T / J)
    for dim, clf in bundle["models"].items():
        p = clf.predict_proba(X)[0]
        # labels: 0 = first letter (E,S,T,J), 1 = second (I,N,F,P)
        # ใช้ clf.classes_ หา index ของ class 0 เพื่อ defensive กับ sklearn เวอร์ชันต่างๆ
        idx_first = int(np.where(clf.classes_ == 0)[0][0])
        ml_probs[dim] = float(p[idx_first])

    # 3. Text (optional)
    text_sc = text_scores(free_text) if free_text else None

    # 4. Blend per dimension
    final_scores = {}    # e.g. {"E": 60, "I": 40, ...}
    mbti = ""
    confidences = []

    pairs = [("EI", "E", "I"), ("SN", "S", "N"), ("TF", "T", "F"), ("JP", "J", "P")]
    for dim, first, second in pairs:
        r_first = rule[first]
        r_second = rule[second]

        # ml: P(first)
        ml_first = ml_probs[dim]
        ml_second = 1.0 - ml_first

        # scale ml to similar range (multiply by (r_first+r_second) as weight)
        total_rule = r_first + r_second if (r_first + r_second) > 0 else 1.0
        ml_first_scaled = ml_first * total_rule
        ml_second_scaled = ml_second * total_rule

        # weight: 70% rule, 30% ml
        blend_first = 0.7 * r_first + 0.3 * ml_first_scaled
        blend_second = 0.7 * r_second + 0.3 * ml_second_scaled

        # include text if available (weight 20%, reducing others to 56/24)
        if text_sc:
            t_first = max(0.0, text_sc[first]) * total_rule
            t_second = max(0.0, text_sc[second]) * total_rule
            blend_first = 0.56 * r_first + 0.24 * ml_first_scaled + 0.20 * t_first
            blend_second = 0.56 * r_second + 0.24 * ml_second_scaled + 0.20 * t_second

        pa, pb = normalize_pair(blend_first, blend_second)
        final_scores[first] = pa
        final_scores[second] = pb
        mbti += pick_dimension(blend_first, blend_second, first, second)

        # confidence = |diff| / 100 (0..1)
        confidences.append(abs(pa - pb) / 100.0)

    # overall confidence = average of 4 dims
    confidence = float(np.mean(confidences))

    info = get_info(mbti)

    return {
        "mbti_type": mbti,
        "nickname": info["nickname"],
        "dimensions": final_scores,
        "confidence": round(confidence, 3),
        "description": info["description"],
        "strengths": info["strengths"],
        "weaknesses": info["weaknesses"],
        "careers": info["careers"],
        "famous_people": info["famous_people"],
        "compatible_types": info["compatible"],
    }
