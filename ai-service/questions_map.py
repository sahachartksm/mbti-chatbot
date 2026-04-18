"""
Mapping of question → dimension + choice → direction + weight.
⚠️ ต้อง sync กับ backend/questions/questions.go
รูปแบบ: QUESTION_MAP[qid] = {"dim": "EI"|"SN"|"TF"|"JP", "choices": {choice_id: (direction, weight)}}
"""

QUESTION_MAP = {
    # --- EI ---
    1: {"dim": "EI", "choices": {"a": ("E", 1.0), "b": ("I", 0.5), "c": ("I", 1.0)}},
    2: {"dim": "EI", "choices": {"a": ("E", 1.0), "b": ("I", 1.0)}},
    3: {"dim": "EI", "choices": {"a": ("E", 1.0), "b": ("I", 1.0)}},
    4: {"dim": "EI", "choices": {"a": ("E", 1.0), "b": ("I", 0.3), "c": ("I", 1.0)}},
    5: {"dim": "EI", "choices": {"a": ("E", 1.0), "b": ("I", 1.0)}},
    # --- SN ---
    6: {"dim": "SN", "choices": {"a": ("S", 1.0), "b": ("N", 1.0)}},
    7: {"dim": "SN", "choices": {"a": ("S", 1.0), "b": ("N", 1.0)}},
    8: {"dim": "SN", "choices": {"a": ("S", 1.0), "b": ("N", 1.0), "c": ("N", 0.3)}},
    9: {"dim": "SN", "choices": {"a": ("S", 1.0), "b": ("N", 1.0)}},
    10: {"dim": "SN", "choices": {"a": ("S", 1.0), "b": ("N", 1.0)}},
    # --- TF ---
    11: {"dim": "TF", "choices": {"a": ("T", 1.0), "b": ("F", 1.0)}},
    12: {"dim": "TF", "choices": {"a": ("T", 1.0), "b": ("F", 1.0)}},
    13: {"dim": "TF", "choices": {"a": ("T", 1.0), "b": ("F", 1.0)}},
    14: {"dim": "TF", "choices": {"a": ("T", 1.0), "b": ("F", 1.0), "c": ("T", 0.4)}},
    15: {"dim": "TF", "choices": {"a": ("T", 1.0), "b": ("F", 1.0)}},
    # --- JP ---
    16: {"dim": "JP", "choices": {"a": ("J", 1.0), "b": ("P", 1.0)}},
    17: {"dim": "JP", "choices": {"a": ("J", 1.0), "b": ("P", 1.0), "c": ("P", 0.4)}},
    18: {"dim": "JP", "choices": {"a": ("J", 1.0), "b": ("P", 1.0)}},
    19: {"dim": "JP", "choices": {"a": ("J", 1.0), "b": ("P", 1.0)}},
    20: {"dim": "JP", "choices": {"a": ("J", 1.0), "b": ("P", 1.0)}},
}

TOTAL_QUESTIONS = len(QUESTION_MAP)
DIMENSIONS = ["EI", "SN", "TF", "JP"]

# List of choice IDs per question (order matters for feature encoding)
QUESTION_CHOICES = {qid: sorted(q["choices"].keys()) for qid, q in QUESTION_MAP.items()}
