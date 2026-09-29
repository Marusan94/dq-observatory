import re
import pandas as pd
import numpy as np
from app.engines.base import EngineResult
from app.engines.text_normalizer import EMAIL_RE, classify_email

PHONE_DIGITS_RE = re.compile(r"\D")


def analyze_patterns(df: pd.DataFrame, type_info: dict, config: dict | None = None) -> EngineResult:
    config = config or {}
    issues, metrics = [], {}
    for col in df.columns:
        sem = type_info.get(str(col), {}).get("semantic_type", "")
        s = df[col].dropna().astype(str)
        if sem == "email" or "email" in str(col).lower():
            invalid = sum(1 for v in s if classify_email(v) == "invalid")
            if invalid:
                issues.append({"severity": "HIGH" if invalid > len(df) * 0.05 else "MEDIUM",
                               "category": "VALIDITY", "column": str(col), "row_count": invalid,
                               "percentage": round(invalid / max(1, len(df)) * 100, 2),
                               "description": f"Invalid email format in '{col}': {invalid} rows.",
                               "examples": [v for v in s if classify_email(v) == "invalid"][:5],
                               "rule": "VALID_EMAIL", "auto_fix_available": True})
            metrics[str(col)] = {"invalid_email": invalid}
        if sem == "phone" or "phone" in str(col).lower():
            bad = 0
            for v in s:
                digits = PHONE_DIGITS_RE.sub("", v)
                if not (7 <= len(digits) <= 15):
                    bad += 1
            if bad:
                issues.append({"severity": "MEDIUM", "category": "VALIDITY", "column": str(col),
                               "row_count": bad, "percentage": round(bad / max(1, len(df)) * 100, 2),
                               "description": f"Inconsistent phone values in '{col}': {bad} rows.",
                               "examples": s.head(5).tolist(), "rule": "VALID_PHONE", "auto_fix_available": True})
            metrics[str(col)] = {"invalid_phone": bad}
    # PII hints
    pii = []
    for col in df.columns:
        lname = str(col).lower()
        sem = type_info.get(str(col), {}).get("semantic_type", "")
        if sem in ("email", "phone") or any(k in lname for k in ("email", "phone", "address", "name", "card", "ssn", "cedula", "document")):
            pii.append({"column": str(col), "pattern": sem or "name-like", "confidence": 0.8,
                        "note": "Potential sensitive field — verify handling."})
    return EngineResult(engine="patterns", metrics=metrics, issues=issues, metadata={"pii": pii})
