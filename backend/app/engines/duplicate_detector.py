import pandas as pd
from app.engines.base import EngineResult


def analyze(df: pd.DataFrame, config: dict | None = None) -> EngineResult:
    config = config or {}
    exact = int(df.duplicated(keep="first").sum())
    issues = []
    if exact > 0:
        issues.append({"severity": "HIGH" if exact / max(1, len(df)) > 0.05 else "MEDIUM",
                       "category": "UNIQUENESS", "column": None, "row_count": exact,
                       "percentage": round(exact / max(1, len(df)) * 100, 2),
                       "description": f"{exact} exact duplicate rows detected.",
                       "examples": df[df.duplicated(keep=False)].head(5).astype(str).to_dict(orient="records"),
                       "rule": "UNIQUE", "auto_fix_available": True})
    subset_issues = []
    id_cols = [c for c in df.columns if "id" in str(c).lower()]
    if id_cols:
        for c in id_cols[:3]:
            d = int(df.duplicated(subset=[c]).sum())
            if d > 0:
                subset_issues.append({"column": str(c), "duplicates": d})
                issues.append({"severity": "HIGH", "category": "INTEGRITY", "column": str(c),
                               "row_count": d, "percentage": round(d / max(1, len(df)) * 100, 2),
                               "description": f"Duplicate identifiers in '{c}': {d} rows.",
                               "examples": [], "rule": "IDENTIFIER_COMPLETENESS", "auto_fix_available": False})
    return EngineResult(engine="duplicates", metrics={
        "exact_duplicates": exact,
        "exact_duplicate_rate": round(exact / max(1, len(df)), 4),
        "subset": subset_issues}, issues=issues)
