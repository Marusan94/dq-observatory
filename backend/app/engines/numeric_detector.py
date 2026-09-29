import re
import pandas as pd
import numpy as np
from app.engines.base import EngineResult


def parse_numeric_token(v: str):
    s = str(v).strip().replace(" ", "")
    is_pct = s.endswith("%")
    s = s.rstrip("%")
    s = re.sub(r"[$€£¥]", "", s)
    # 1.200,50 -> 1200.50 ; 1,000.25 -> 1000.25
    if re.match(r"^-?[\d.]+,\d+$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s), is_pct
    except Exception:
        return None, False


def analyze(df: pd.DataFrame, type_info: dict, config: dict | None = None) -> EngineResult:
    issues, metrics = [], {}
    for col in df.columns:
        sem = type_info.get(str(col), {}).get("semantic_type", "")
        s = df[col].dropna().astype(str)
        if len(s) == 0:
            continue
        as_text = 0
        for v in s.head(500):
            val, _ = parse_numeric_token(v)
            if val is not None and not re.match(r"^-?[\d.]+$", v.strip()):
                as_text += 1
        if as_text > 0 and sem in ("string", "currency", "percentage", "integer", "float", "numeric"):
            issues.append({"severity": "LOW", "category": "TYPE", "column": str(col), "row_count": as_text,
                           "percentage": round(as_text / max(1, min(len(s), 500)) * 100, 2),
                           "description": f"Numeric values stored as text in '{col}' (currency/symbols). Deterministic parsing available.",
                           "examples": s.head(5).tolist(), "rule": "NUMERIC_RANGE", "auto_fix_available": True})
        metrics[str(col)] = {"numeric_as_text_sample": as_text}
    return EngineResult(engine="numeric", metrics=metrics, issues=issues)
