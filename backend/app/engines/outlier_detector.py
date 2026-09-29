import pandas as pd
import numpy as np
from app.engines.base import EngineResult


def analyze(df: pd.DataFrame, config: dict | None = None) -> EngineResult:
    config = config or {}
    method = config.get("method", "iqr")
    issues, metrics = [], {}
    num_cols = []
    for col in df.columns:
        coerced = pd.to_numeric(df[col].astype(str).str.replace(r"[$€£¥,%\s]", "", regex=True).str.replace(",", "", regex=False), errors="coerce")
        if coerced.notna().mean() is not None and float(coerced.notna().mean()) > 0.7:
            num_cols.append((str(col), coerced))
    for col, s in num_cols:
        vals = s.dropna()
        if len(vals) < 10:
            continue
        if method == "zscore":
            mu, sigma = float(vals.mean()), float(vals.std() or 1)
            z = ((vals - mu) / sigma).abs()
            mask = z > 3
        else:  # iqr
            q1, q3 = float(vals.quantile(0.25)), float(vals.quantile(0.75))
            iqr = q3 - q1 or 1.0
            mask = (vals < q1 - 1.5 * iqr) | (vals > q3 + 1.5 * iqr)
        count = int(mask.sum())
        metrics[col] = {"outliers": count, "method": method}
        if count > 0:
            issues.append({"severity": "LOW", "category": "ANOMALY", "column": col, "row_count": count,
                           "percentage": round(count / max(1, len(df)) * 100, 2),
                           "description": f"Potential outliers in '{col}' ({method}): {count} rows. Review required — not auto-removed.",
                           "examples": vals[mask].head(5).tolist(), "rule": "OUTLIER", "auto_fix_available": False})
    return EngineResult(engine="outliers", metrics=metrics, issues=issues)
