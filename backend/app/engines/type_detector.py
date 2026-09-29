import re
import pandas as pd
from app.engines.base import EngineResult

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")
URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.I)
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
CURRENCY_RE = re.compile(r"^[$€£¥]?\s?[\d,.]+\s?[$€£¥]?$")
PERCENT_RE = re.compile(r"^-?[\d,.]+\s?%$")
BOOL_TOKENS = {"true", "false", "yes", "no", "y", "n", "1", "0", "t", "f", "si", "sí"}


def _ratio(series: pd.Series, pred) -> float:
    s = series.dropna()
    s = s[s.astype(str).str.strip() != ""]
    if len(s) == 0:
        return 0.0
    return float(sum(1 for v in s.astype(str) if pred(str(v).strip())) / len(s))


def infer_column(series: pd.Series, name: str = "") -> dict:
    """Return {physical_type, semantic_type, confidence} without trusting pandas dtypes alone."""
    dtype = str(series.dtype)
    non_null = series.dropna()
    if len(non_null) == 0:
        return {"physical_type": dtype, "semantic_type": "unknown", "confidence": 0.0}
    sample = non_null.astype(str).head(200)
    email_r = _ratio(series, lambda v: bool(EMAIL_RE.match(v)))
    url_r = _ratio(series, lambda v: bool(URL_RE.match(v)))
    uuid_r = _ratio(series, lambda v: bool(UUID_RE.match(v)))
    phone_r = _ratio(series, lambda v: bool(PHONE_RE.match(v)) and sum(c.isdigit() for c in v) >= 7)
    pct_r = _ratio(series, lambda v: bool(PERCENT_RE.match(v)))
    cur_r = _ratio(series, lambda v: bool(CURRENCY_RE.match(v)) and any(c.isdigit() for c in v))
    bool_r = _ratio(series, lambda v: v.strip().lower() in BOOL_TOKENS)
    # numeric coercion
    num_coerced = pd.to_numeric(non_null.astype(str).str.replace(r"[$€£¥,%\s]", "", regex=True).str.replace(",", ".", regex=False), errors="coerce")
    num_r = float(num_coerced.notna().mean()) if len(num_coerced) else 0.0
    # date coercion (format=mixed silences per-element fallback warnings on pandas>=2.0)
    try:
        date_coerced = pd.to_datetime(non_null.astype(str), errors="coerce", utc=False, format="mixed")
    except TypeError:
        date_coerced = pd.to_datetime(non_null.astype(str), errors="coerce", utc=False)
    date_r = float(date_coerced.notna().mean()) if len(date_coerced) else 0.0
    uniq_ratio = float(series.nunique(dropna=True) / max(1, len(series)))
    n_unique = int(series.nunique(dropna=True))

    semantic, conf = "string", 0.5
    candidates = [
        ("email", email_r), ("url", url_r), ("uuid", uuid_r), ("phone", phone_r),
        ("percentage", pct_r), ("currency", cur_r), ("boolean", bool_r),
        ("date", date_r),
    ]
    best, best_r = max(candidates, key=lambda x: x[1])
    if best_r >= 0.7:
        semantic, conf = best, round(min(0.99, best_r), 2)
    elif num_r >= 0.8:
        # integer vs float
        try:
            vals = num_coerced.dropna()
            is_int = bool(((vals % 1) == 0).all()) if len(vals) else False
            semantic = "integer" if is_int else "float"
        except Exception:
            semantic = "numeric"
        conf = round(num_r, 2)
    elif n_unique <= max(20, len(series) * 0.02) and n_unique >= 1 and uniq_ratio < 0.2:
        semantic, conf = "categorical", 0.75
    elif uniq_ratio > 0.95 and n_unique > 20:
        lname = name.lower()
        if any(k in lname for k in ("id", "uuid", "key", "code")):
            semantic, conf = "identifier", 0.9
        else:
            semantic, conf = "text", 0.6
    elif date_r >= 0.5:
        semantic, conf = "date", round(date_r, 2)
    # detect long free text
    avg_len = float(sample.str.len().mean()) if len(sample) else 0
    if semantic == "string" and avg_len > 60:
        semantic, conf = "text", 0.65
    return {"physical_type": dtype, "semantic_type": semantic, "confidence": conf}


def analyze(df: pd.DataFrame, config: dict | None = None) -> EngineResult:
    columns = {}
    for col in df.columns:
        columns[str(col)] = infer_column(df[col], str(col))
    return EngineResult(engine="type_detector", metrics={"columns": columns}, metadata={"count": len(columns)})
