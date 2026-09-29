"""Predictive Scoring Service - ML-based score prediction after fixes."""
import json
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "predictive"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODEL_DIR / "score_predictor.pkl"
METADATA_PATH = MODEL_DIR / "metadata.json"


FEATURE_COLUMNS = [
    "rows", "cols", "missing_percentage", "exact_duplicate_rate",
    "validity_issue_count", "consistency_issue_count", "completeness_issue_count",
    "uniqueness_issue_count", "integrity_issue_count",
    "pii_column_count", "high_cardinality_count", "constant_column_count",
    "proposed_fix_count", "proposed_fix_confidence_avg",
]


def extract_features(profile: Dict, issues: List[Dict], proposed_fixes: List[Dict]) -> np.ndarray:
    """Extract feature vector from profile + issues + proposed fixes."""
    # Profile metrics
    missing_pct = profile.get("missing_percentage", 0)
    dup_rate = profile.get("exact_duplicate_rate", 0)
    pii_cols = len(profile.get("pii", []))
    high_card = sum(1 for c in profile.get("columns", []) if c.get("high_cardinality", False))
    const_cols = sum(1 for c in profile.get("columns", []) if c.get("constant", False))

    # Issue counts by category
    issue_counts = {"VALIDITY": 0, "CONSISTENCY": 0, "COMPLETENESS": 0, "UNIQUENESS": 0, "INTEGRITY": 0}
    for issue in issues:
        cat = issue.get("category", "").upper()
        if cat in issue_counts:
            issue_counts[cat] += issue.get("row_count", 0)

    # Proposed fixes
    fix_count = len(proposed_fixes)
    avg_conf = np.mean([f.get("confidence", 0.5) for f in proposed_fixes]) if proposed_fixes else 0

    features = [
        profile.get("rows", 0),
        profile.get("columns", 0),
        missing_pct,
        dup_rate,
        issue_counts["VALIDITY"],
        issue_counts["CONSISTENCY"],
        issue_counts["COMPLETENESS"],
        issue_counts["UNIQUENESS"],
        issue_counts["INTEGRITY"],
        pii_cols,
        high_card,
        const_cols,
        fix_count,
        avg_conf,
    ]
    return np.array(features, dtype=np.float32).reshape(1, -1)


def train_model(
    profiles: List[Dict],
    issues_list: List[List[Dict]],
    fixes_list: List[List[Dict]],
    score_before: List[float],
    score_after: List[float],
) -> Dict:
    """Train XGBoost model to predict score delta."""
    if not XGB_AVAILABLE:
        return {"error": "xgboost not installed"}

    X = np.vstack([
        extract_features(p, i, f) for p, i, f in zip(profiles, issues_list, fixes_list)
    ])
    y = np.array([a - b for a, b in zip(score_after, score_before)], dtype=np.float32)  # delta

    if len(X) < 10:
        return {"error": "Insufficient training data (need ≥10 samples)"}

    # Train/test split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    # Feature importance
    importance = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]

    # Save model
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    metadata = {
        "mae": float(mae),
        "rmse": float(rmse),
        "n_samples": len(X),
        "features": FEATURE_COLUMNS,
        "top_features": top_features,
        "trained_at": pd.Timestamp.now().isoformat(),
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    return {"mae": mae, "rmse": rmse, "top_features": top_features, "metadata": metadata}


def load_model() -> Optional[Any]:
    """Load trained model."""
    if not XGB_AVAILABLE:
        return None
    if not MODEL_PATH.exists():
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_score_ml(
    profile: Dict,
    issues: List[Dict],
    proposed_fixes: List[Dict],
) -> Dict:
    """Predict score after fixes using trained ML model."""
    model = load_model()
    if model is None:
        raise RuntimeError("Model not trained or xgboost unavailable")

    X = extract_features(profile, issues, proposed_fixes)
    delta = float(model.predict(X)[0])
    current = profile.get("quality_score", {}).get("overall", 50) if isinstance(profile.get("quality_score"), dict) else profile.get("score", 50)
    predicted = np.clip(current + delta, 0, 100)

    # Estimate confidence interval (rough)
    ci_width = 8  # ±8 points
    ci = [max(0, predicted - ci_width), min(100, predicted + ci_width)]

    # Feature importance
    try:
        importance = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))
        top = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
    except Exception:
        top = []

    return {
        "predicted_score": round(predicted, 1),
        "delta": round(delta, 1),
        "confidence_interval": [round(ci[0], 1), round(ci[1], 1)],
        "top_features": [{"feature": k, "impact": round(v, 4)} for k, v in top],
    }


def get_model_status() -> Dict:
    """Get model status and metadata."""
    if not XGB_AVAILABLE:
        return {"status": "unavailable", "reason": "xgboost not installed"}
    if not MODEL_PATH.exists():
        return {"status": "not_trained", "reason": "Model not trained yet"}
    try:
        with open(METADATA_PATH, "r") as f:
            meta = json.load(f)
        return {"status": "ready", "metadata": meta}
    except Exception as e:
        return {"status": "error", "reason": str(e)}