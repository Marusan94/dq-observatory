import pandas as pd
from app.engines.base import EngineResult

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y.%m.%d", "%B %d %Y", "%d %B %Y"]


def analyze(df: pd.DataFrame, type_info: dict, config: dict | None = None) -> EngineResult:
    issues, metrics = [], {}
    future = pd.Timestamp.now()
    for col in df.columns:
        sem = type_info.get(str(col), {}).get("semantic_type", "")
        if sem != "date" and "date" not in str(col).lower():
            continue
        s = df[col].dropna().astype(str)
        try:
            parsed = pd.to_datetime(s, errors="coerce", utc=False, format="mixed")
        except TypeError:
            parsed = pd.to_datetime(s, errors="coerce", utc=False)
        invalid = int(parsed.isna().sum())
        metrics[str(col)] = {"invalid_dates": invalid}
        if invalid:
            issues.append({"severity": "MEDIUM", "category": "VALIDITY", "column": str(col),
                           "row_count": invalid, "percentage": round(invalid / max(1, len(df)) * 100, 2),
                           "description": f"Unparseable dates in '{col}': {invalid} rows.",
                           "examples": s[parsed.isna()].head(5).tolist(), "rule": "VALID_DATE",
                           "auto_fix_available": False})
        # ambiguous like 03/04/2026
        amb = int(s.str.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$").sum())
        if amb > 0:
            issues.append({"severity": "LOW", "category": "FORMAT", "column": str(col), "row_count": amb,
                           "percentage": round(amb / max(1, len(df)) * 100, 2),
                           "description": f"Ambiguous date format in '{col}' (DD/MM vs MM/DD). Configure date format explicitly.",
                           "examples": s[s.str.match(r'^\\d{1,2}/\\d{1,2}/\\d{2,4}$')].head(3).tolist(),
                           "rule": "STANDARD_FORMAT", "auto_fix_available": False})
        try:
            fut = int((parsed > future).sum())
            if fut > 0 and "birth" not in str(col).lower():
                issues.append({"severity": "LOW", "category": "VALIDITY", "column": str(col), "row_count": fut,
                               "percentage": round(fut / max(1, len(df)) * 100, 2),
                               "description": f"Future dates in '{col}': {fut} rows.",
                               "examples": [], "rule": "VALID_DATE", "auto_fix_available": False})
        except Exception:
            pass
    return EngineResult(engine="dates", metrics=metrics, issues=issues)
