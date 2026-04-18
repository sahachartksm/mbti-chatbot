"""
Train Logistic Regression models (4 ตัว สำหรับ 4 dimensions)
Run: python train.py
Output: models/mbti_model.pkl (dict ของ 4 classifiers + scaler)
"""

from pathlib import Path
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from data.training_data_generator import generate, DIM_IDX
from questions_map import TOTAL_QUESTIONS

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / "mbti_model.pkl"


def train(n_samples: int = 10000, noise: float = 0.15):
    print(f"🔧 Generating synthetic data (n={n_samples}, noise={noise}) ...")
    df = generate(n_samples=n_samples, noise=noise)
    print(f"  shape: {df.shape}")

    X = df[[f"q{i+1}" for i in range(TOTAL_QUESTIONS)]].values
    print(f"  feature shape: {X.shape}")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    models = {}
    for dim in DIM_IDX:
        y = df[f"label_{dim}"].values
        X_tr, X_te, y_tr, y_te = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)
        clf = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
        clf.fit(X_tr, y_tr)
        tr_acc = clf.score(X_tr, y_tr)
        te_acc = clf.score(X_te, y_te)
        print(f"  [{dim}] train={tr_acc:.3f}  test={te_acc:.3f}")
        models[dim] = clf

    # test overall 16-type accuracy (majority vote from dims)
    preds = np.zeros(len(df), dtype=int)
    letters = ""
    # Evaluate on test split replicate
    _, X_te_all, _, idx_te = train_test_split(
        X_scaled, np.arange(len(df)), test_size=0.2, random_state=42
    )
    correct = 0
    for i, row_idx in enumerate(idx_te):
        pred_type = ""
        for dim, pos in DIM_IDX.items():
            prob = models[dim].predict_proba(X_te_all[i : i + 1])[0]
            pred_type += dim[0] if prob[0] > prob[1] else dim[1]
        true_type = df.iloc[row_idx]["true_type"]
        if pred_type == true_type:
            correct += 1
    print(f"  overall 16-type test accuracy: {correct/len(idx_te):.3f}")

    bundle = {"scaler": scaler, "models": models, "n_features": TOTAL_QUESTIONS}
    joblib.dump(bundle, MODEL_PATH)
    print(f"✅ Saved model → {MODEL_PATH}")


if __name__ == "__main__":
    train()
