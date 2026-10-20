"""Train Linear Regression and Logistic Regression on ml_training_data.csv.

- Groups snapshots by billing_period_id to avoid leakage across related snapshots.
- Fits preprocessing on training data only.
- Saves pipelines and reports metrics computed at runtime.
- Does NOT retrain automatically.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from datetime import datetime
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error,
    precision_score, recall_score, f1_score, confusion_matrix,
)

from config import PROCESSED_DIR, MODELS_DIR, FEATURES

REG_PATH = MODELS_DIR / "linear_regression.joblib"
CLF_PATH = MODELS_DIR / "logistic_regression.joblib"
META_PATH = MODELS_DIR / "model_metadata.json"


def make_regressor():
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LinearRegression()),
    ])


def make_classifier():
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])


def main():
    df = pd.read_csv(PROCESSED_DIR / "ml_training_data.csv")
    if df.empty:
        raise SystemExit("ml_training_data.csv is empty — run build_training_data first.")

    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(gss.split(df, groups=df["billing_period_id"]))
    train_df, test_df = df.iloc[train_idx], df.iloc[test_idx]

    # ---- regression ----
    reg = make_regressor()
    reg.fit(train_df[FEATURES], train_df["actual_final_units"])
    reg_pred = reg.predict(test_df[FEATURES])
    reg_mae = mean_absolute_error(test_df["actual_final_units"], reg_pred)
    reg_rmse = float(np.sqrt(mean_squared_error(test_df["actual_final_units"], reg_pred)))

    # ---- baseline (average_daily_units * period_days) ----
    baseline_pred = test_df["average_daily_units"] * test_df["period_days"]
    base_mae = mean_absolute_error(test_df["actual_final_units"], baseline_pred)
    base_rmse = float(np.sqrt(mean_squared_error(test_df["actual_final_units"], baseline_pred)))

    # ---- classification ----
    clf = make_classifier()
    clf.fit(train_df[FEATURES], train_df["target_exceeded"])
    clf_proba = clf.predict_proba(test_df[FEATURES])[:, 1]
    clf_pred = (clf_proba >= 0.5).astype(int)

    precision = precision_score(test_df["target_exceeded"], clf_pred, zero_division=0)
    recall = recall_score(test_df["target_exceeded"], clf_pred, zero_division=0)
    f1 = f1_score(test_df["target_exceeded"], clf_pred, zero_division=0)
    cm = confusion_matrix(test_df["target_exceeded"], clf_pred).tolist()

    joblib.dump(reg, REG_PATH)
    joblib.dump(clf, CLF_PATH)

    metadata = {
        "trained_at": datetime.utcnow().isoformat(timespec="seconds"),
        "data_source": "synthetic",
        "n_train_rows": int(len(train_df)),
        "n_test_rows": int(len(test_df)),
        "n_train_periods": int(train_df["billing_period_id"].nunique()),
        "n_test_periods": int(test_df["billing_period_id"].nunique()),
        "features": FEATURES,
        "regression": {
            "linear_regression": {"mae": reg_mae, "rmse": reg_rmse},
            "baseline_projection": {"mae": base_mae, "rmse": base_rmse},
        },
        "classification": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "confusion_matrix": cm,
        },
        "limitations": (
            "Model trained on SYNTHETIC data. Metrics describe only this synthetic "
            "distribution. Do not present as real-world accuracy. "
            "Models are NOT retrained on user input; retraining is a separate process."
        ),
    }
    META_PATH.write_text(json.dumps(metadata, indent=2))

    print("Training complete.")
    print(json.dumps(metadata["regression"], indent=2))
    print(json.dumps(metadata["classification"], indent=2))


if __name__ == "__main__":
    main()