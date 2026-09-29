import re
import pandas as pd

OPERATORS = {"not_null", "unique", "between", "gte", "lte", "eq", "in", "regex", "valid_email", "valid_date"}
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def evaluate(df: pd.DataFrame, rules: list[dict]) -> list[dict]:
    """Structured DSL only — never eval/exec. Rule: {column, operator, value, severity, name}."""
    results = []
    for r in rules:
        col, op = r.get("column"), r.get("operator")
        if op not in OPERATORS or col not in df.columns:
            results.append({**r, "passed": 0, "failed": 0, "status": "ERROR", "detail": "unknown operator or column"})
            continue
        s = df[col]
        if op == "not_null":
            failed = int(s.isna().sum() + (s.astype(str).str.strip() == "").sum())
        elif op == "unique":
            failed = int(s.duplicated(keep=False).sum())
        elif op == "between":
            lo, hi = (r.get("value") or [None, None]) if isinstance(r.get("value"), list) else (None, None)
            num = pd.to_numeric(s, errors="coerce")
            failed = int(((num < lo) | (num > hi) | num.isna()).sum()) if lo is not None else int(s.isna().sum())
        elif op == "gte":
            num = pd.to_numeric(s, errors="coerce")
            failed = int(((num < r.get("value")) | num.isna()).sum())
        elif op == "lte":
            num = pd.to_numeric(s, errors="coerce")
            failed = int(((num > r.get("value")) | num.isna()).sum())
        elif op == "eq":
            failed = int((s.astype(str) != str(r.get("value"))).sum())
        elif op == "in":
            allowed = set(map(str, r.get("value") or []))
            failed = int((~s.astype(str).isin(allowed)).sum())
        elif op == "regex":
            pat = re.compile(str(r.get("value")))
            failed = int((~s.astype(str).str.match(pat)).sum())
        elif op == "valid_email":
            failed = int((~s.astype(str).str.lower().str.match(EMAIL_RE)).sum())
        elif op == "valid_date":
            try:
                _parsed = pd.to_datetime(s.astype(str), errors="coerce", format="mixed")
            except TypeError:
                _parsed = pd.to_datetime(s.astype(str), errors="coerce")
            failed = int(_parsed.isna().sum())
        else:
            failed = 0
        results.append({**r, "passed": len(df) - failed, "failed": failed,
                        "status": "PASS" if failed == 0 else "FAIL"})
    return results
