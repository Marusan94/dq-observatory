import unicodedata
import pandas as pd
from app.engines.base import EngineResult


def _canon(v: str) -> str:
    s = str(v).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return " ".join(s.split())


def analyze(df: pd.DataFrame, type_info: dict, config: dict | None = None) -> EngineResult:
    issues, metrics = [], {}
    for col in df.columns:
        sem = type_info.get(str(col), {}).get("semantic_type", "")
        if sem not in ("categorical", "string", "text") and "city" not in str(col).lower() and "country" not in str(col).lower() and "status" not in str(col).lower() and "segment" not in str(col).lower():
            continue
        s = df[col].dropna().astype(str)
        if len(s) == 0 or s.nunique() > 100:
            continue
        groups: dict[str, list[str]] = {}
        for v in s.unique():
            groups.setdefault(_canon(v), []).append(v)
        merged = {k: v for k, v in groups.items() if len(v) > 1}
        metrics[str(col)] = {"variant_groups": len(merged)}
        if merged:
            top = sorted(merged.items(), key=lambda x: -len(x[1]))[:3]
            mask = s.apply(lambda x: _canon(x) in merged)
            issues.append({"severity": "MEDIUM", "category": "CONSISTENCY", "column": str(col),
                           "row_count": int(mask.sum()),
                           "percentage": round(float(mask.mean()) * 100, 2),
                           "description": f"Inconsistent categories in '{col}': {len(merged)} groups with spelling/case variants.",
                           "examples": [{"canonical_candidate": max(v, key=lambda x: (s == x).sum()), "variants": v} for _, v in top],
                           "rule": "STANDARD_CASE", "auto_fix_available": True})
    return EngineResult(engine="categories", metrics=metrics, issues=issues)
