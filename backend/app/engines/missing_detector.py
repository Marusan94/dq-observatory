import pandas as pd
from app.engines.base import EngineResult
from app.utils.dataframe_utils import is_missing_like


def analyze(df: pd.DataFrame, config: dict | None = None) -> EngineResult:
    config = config or {}
    total_cells = df.shape[0] * max(1, df.shape[1])
    missing_cells = 0
    by_column = {}
    for col in df.columns:
        flags = [is_missing_like(v) for v in df[col].tolist()]
        count = sum(1 for m, _ in flags if m)
        missing_cells += count
        cats: dict[str, int] = {}
        for m, c in flags:
            if m:
                cats[c or "null"] = cats.get(c or "null", 0) + 1
        by_column[str(col)] = {
            "missing": count,
            "missing_rate": round(count / max(1, len(df)), 4),
            "categories": cats,
            "examples": [i for i, (m, _) in enumerate(flags) if m][:5],
        }
    issues = []
    for col, m in by_column.items():
        if m["missing_rate"] >= 0.3:
            issues.append({"severity": "HIGH" if m["missing_rate"] >= 0.5 else "MEDIUM",
                           "category": "COMPLETENESS", "column": col, "row_count": m["missing"],
                           "percentage": round(m["missing_rate"]*100, 2),
                           "description": f"Column '{col}' has {m['missing_rate']*100:.1f}% missing values.",
                           "examples": m["examples"], "rule": "MAX_NULL_PERCENTAGE", "auto_fix_available": True})
        elif m["missing"] > 0:
            issues.append({"severity": "LOW", "category": "COMPLETENESS", "column": col,
                           "row_count": m["missing"], "percentage": round(m["missing_rate"]*100, 2),
                           "description": f"Column '{col}' has {m['missing']} missing values.",
                           "examples": m["examples"], "rule": "NOT_NULL", "auto_fix_available": True})
    return EngineResult(engine="missing", metrics={
        "missing_cells": missing_cells,
        "missing_percentage": round(missing_cells / max(1, total_cells) * 100, 3),
        "by_column": by_column}, issues=issues)
