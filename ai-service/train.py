"""
Train Logistic Regression models (4 ตัว สำหรับ 4 dimensions)
Run: python train.py
Output:
  - models/mbti_model.pkl         (dict ของ 4 classifiers + scaler)
  - models/metrics.json           (รายงานผลการเทรน)
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from data.training_data_generator import DIM_IDX, generate
from questions_map import TOTAL_QUESTIONS

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / "mbti_model.pkl"
METRICS_PATH = MODEL_DIR / "metrics.json"

RANDOM_STATE = 42


def train(n_samples: int = 20000, noise: float = 0.15) -> dict:
    """
    เทรน LogReg 4 ตัว (EI, SN, TF, JP) จาก synthetic data.
    คืนค่า dict ของ metrics.
    """
    print(f"🔧 Generating synthetic data (n={n_samples}, noise={noise}) ...")
    df = generate(n_samples=n_samples, noise=noise, seed=RANDOM_STATE)
    print(f"  dataset shape: {df.shape}")

    feature_cols = [f"q{i+1}" for i in range(TOTAL_QUESTIONS)]
    X = df[feature_cols].values
    true_types = df["true_type"].values

    # แบ่ง train/test ครั้งเดียว ให้ทุก dimension ใช้ชุดเดียวกัน
    idx_all = np.arange(len(df))
    idx_tr, idx_te = train_test_split(
        idx_all, test_size=0.2, random_state=RANDOM_STATE, stratify=true_types
    )

    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X[idx_tr])
    X_te = scaler.transform(X[idx_te])

    models: dict[str, LogisticRegression] = {}
    per_dim_metrics: dict[str, dict] = {}

    print("\n📊 Per-dimension metrics")
    print(f"  {'dim':<4} {'train':>8} {'test':>8} {'precision':>10} {'recall':>8} {'f1':>6}")
    for dim in DIM_IDX:
        y_tr = df.iloc[idx_tr][f"label_{dim}"].values
        y_te = df.iloc[idx_te][f"label_{dim}"].values

        clf = LogisticRegression(max_iter=1000, C=1.0, random_state=RANDOM_STATE)
        clf.fit(X_tr, y_tr)

        tr_acc = clf.score(X_tr, y_tr)
        te_acc = clf.score(X_te, y_te)
        y_pred = clf.predict(X_te)

        report = classification_report(y_te, y_pred, output_dict=True, zero_division=0)
        weighted = report["weighted avg"]

        print(
            f"  {dim:<4} {tr_acc:>8.3f} {te_acc:>8.3f} "
            f"{weighted['precision']:>10.3f} {weighted['recall']:>8.3f} {weighted['f1-score']:>6.3f}"
        )

        models[dim] = clf
        per_dim_metrics[dim] = {
            "train_accuracy": round(tr_acc, 4),
            "test_accuracy": round(te_acc, 4),
            "precision": round(weighted["precision"], 4),
            "recall": round(weighted["recall"], 4),
            "f1_score": round(weighted["f1-score"], 4),
        }

    # -------- Overall 16-type accuracy --------
    # ทำนายทุก dimension พร้อมกันบน test set เดียวกัน
    pred_types = np.array(
        [
            "".join(
                dim[0] if models[dim].predict_proba(X_te[i : i + 1])[0][0] >= 0.5 else dim[1]
                for dim in DIM_IDX
            )
            for i in range(len(X_te))
        ]
    )
    true_types_te = true_types[idx_te]
    overall_acc = accuracy_score(true_types_te, pred_types)
    print(f"\n🎯 Overall 16-type test accuracy: {overall_acc:.3f}")

    # Confusion: จำนวน type ที่ทำนายถูก/ผิด
    unique_types = sorted(set(true_types_te))
    cm = confusion_matrix(true_types_te, pred_types, labels=unique_types)
    per_type_acc = {
        t: round(float(cm[i, i] / cm[i].sum()), 4) if cm[i].sum() > 0 else 0.0
        for i, t in enumerate(unique_types)
    }

    # -------- Save bundle & metrics --------
    bundle = {
        "scaler": scaler,
        "models": models,
        "n_features": TOTAL_QUESTIONS,
        "dimensions": list(DIM_IDX.keys()),
    }
    joblib.dump(bundle, MODEL_PATH)
    print(f"\n✅ Saved model → {MODEL_PATH}")

    metrics = {
        "n_samples": n_samples,
        "noise": noise,
        "train_size": int(len(idx_tr)),
        "test_size": int(len(idx_te)),
        "per_dimension": per_dim_metrics,
        "overall_16type_accuracy": round(float(overall_acc), 4),
        "per_type_accuracy": per_type_acc,
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Saved metrics → {METRICS_PATH}")

    return metrics


if __name__ == "__main__":
    train()
