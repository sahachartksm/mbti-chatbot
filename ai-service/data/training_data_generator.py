"""
สร้าง synthetic training data สำหรับเทรน Logistic Regression
แนวคิด:
  1. สุ่ม MBTI "true type" สำหรับแต่ละ sample
  2. จำลองการตอบของคนที่เป็น type นั้น โดยมี noise (โอกาสตอบผิดทาง ~15%)
  3. Encode เป็น feature vector (20 dim) + label

Output: pandas DataFrame with columns [q1, q2, ..., q20, label_EI, label_SN, label_TF, label_JP]
"""

from __future__ import annotations
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# allow run from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from questions_map import QUESTION_MAP, QUESTION_CHOICES, TOTAL_QUESTIONS  # noqa: E402


ALL_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP",
]

# dimension → index ใน MBTI type string
DIM_IDX = {"EI": 0, "SN": 1, "TF": 2, "JP": 3}


def simulate_answer(qid: int, true_type: str, noise: float = 0.15) -> str:
    """
    ให้คนที่เป็น true_type ตอบคำถาม qid
    - หาคำตอบที่ตรงกับ direction ของเขา (ตัวอักษรตำแหน่ง dimension)
    - มี noise prob% ที่จะเลือกตอบตรงข้าม
    """
    q = QUESTION_MAP[qid]
    dim = q["dim"]                       # e.g. "EI"
    pos = DIM_IDX[dim]
    preferred_letter = true_type[pos]    # e.g. "I"

    # แยก choices ตาม direction
    match_choices = [c for c, (direction, _) in q["choices"].items()
                     if direction == preferred_letter]
    other_choices = [c for c in q["choices"].keys() if c not in match_choices]

    if random.random() < noise:
        # answer against preference
        pool = other_choices or match_choices
    else:
        pool = match_choices or other_choices

    return random.choice(pool)


def encode_feature(answers: dict[int, str]) -> np.ndarray:
    """
    Encode answers → feature vector (20 dim)
    Each feature = index ของ choice ใน sorted list / (num_choices - 1)
    → normalize to [0, 1]
    """
    features = []
    for qid in range(1, TOTAL_QUESTIONS + 1):
        choices = QUESTION_CHOICES[qid]
        chosen = answers[qid]
        idx = choices.index(chosen)
        max_idx = max(len(choices) - 1, 1)
        features.append(idx / max_idx)
    return np.array(features, dtype=np.float32)


def label_from_type(mbti: str) -> dict[str, int]:
    """Return {dim: 0/1} label map. 0 = first letter (E,S,T,J), 1 = second (I,N,F,P)"""
    m = {}
    for dim, pos in DIM_IDX.items():
        letter = mbti[pos]
        first = dim[0]  # "E"|"S"|"T"|"J"
        m[f"label_{dim}"] = 0 if letter == first else 1
    return m


def generate(n_samples: int = 10000, noise: float = 0.15, seed: int = 42) -> pd.DataFrame:
    random.seed(seed)
    np.random.seed(seed)

    rows = []
    for _ in range(n_samples):
        true_type = random.choice(ALL_TYPES)
        answers = {qid: simulate_answer(qid, true_type, noise) for qid in range(1, TOTAL_QUESTIONS + 1)}
        feats = encode_feature(answers)
        row = {f"q{i+1}": float(feats[i]) for i in range(TOTAL_QUESTIONS)}
        row.update(label_from_type(true_type))
        row["true_type"] = true_type
        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate(n_samples=10000)
    out = Path(__file__).parent / "synthetic_train.csv"
    df.to_csv(out, index=False)
    print(f"✓ Generated {len(df)} samples → {out}")
    print(df.head())
    print("\nLabel distribution:")
    for dim in DIM_IDX:
        print(f"  {dim}: {df[f'label_{dim}'].value_counts().to_dict()}")
