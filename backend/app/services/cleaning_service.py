import pandas as pd
from app.engines.text_normalizer import normalize_email, normalize_phone, trim
from app.engines.numeric_detector import parse_numeric_token

AUTO_OPS = {"trim_whitespace", "normalize_email", "normalize_phone", "remove_exact_duplicates",
            "standardize_missing", "parse_numeric", "standardize_categories"}


def preview_op(df: pd.DataFrame, operation: str, column: str | None = None, params: dict | None = None) -> dict:
    params = params or {}
    if operation == "trim_whitespace" and column:
        before = df[column].astype(str).head(5).tolist()
        after = [trim(v) for v in before]
        return {"before": before, "after": after, "affected_rows": int((df[column].astype(str) != df[column].astype(str).apply(trim)).sum())}
    if operation == "normalize_email" and column:
        s = df[column].astype(str)
        after = s.apply(lambda v: normalize_email(v))
        return {"before": s.head(5).tolist(), "after": after.head(5).tolist(),
                "affected_rows": int((s != after).sum())}
    if operation == "remove_exact_duplicates":
        return {"before": len(df), "after": len(df) - int(df.duplicated().sum()),
                "affected_rows": int(df.duplicated().sum())}
    return {"before": None, "after": None, "affected_rows": 0, "note": "Estimated preview"}


def apply_op(df: pd.DataFrame, operation: str, column: str | None = None, params: dict | None = None) -> tuple[pd.DataFrame, int]:
    params = params or {}
    out = df.copy()
    affected = 0
    if operation == "trim_whitespace" and column and column in out.columns:
        before = out[column].astype(str)
        out[column] = out[column].apply(lambda v: trim(str(v)) if isinstance(v, str) else v)
        affected = int((before != out[column].astype(str)).sum())
    elif operation == "normalize_email" and column and column in out.columns:
        before = out[column].astype(str)
        out[column] = out[column].apply(lambda v: normalize_email(v) if isinstance(v, str) and "@" in v else (trim(v) if isinstance(v, str) else v))
        affected = int((before != out[column].astype(str)).sum())
    elif operation == "normalize_phone" and column and column in out.columns:
        country = params.get("country", "US")
        before = out[column].astype(str)
        out[column] = out[column].apply(lambda v: normalize_phone(v, country) if isinstance(v, str) and v.strip() else v)
        affected = int((before != out[column].astype(str)).sum())
    elif operation == "remove_exact_duplicates":
        before = len(out)
        out = out.drop_duplicates(keep="first").reset_index(drop=True)
        affected = before - len(out)
    elif operation == "standardize_missing" and column and column in out.columns:
        tokens = set(params.get("tokens", ["N/A", "NA", "null", "unknown", "-", "?", ""]))
        mask = out[column].astype(str).apply(lambda v: v.strip() in tokens or v.strip().lower() in {t.lower() for t in tokens})
        affected = int(mask.sum())
        out.loc[mask, column] = pd.NA
    elif operation == "parse_numeric" and column and column in out.columns:
        def _p(v):
            val, _ = parse_numeric_token(v)
            return val if val is not None else v
        before = out[column].copy()
        out[column] = out[column].apply(_p)
        affected = int((before.astype(str) != out[column].astype(str)).sum())
    elif operation == "standardize_categories" and column and column in out.columns:
        import unicodedata
        def canon(v):
            s = str(v).strip().lower()
            s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
            return " ".join(s.split()).title()
        before = out[column].astype(str)
        out[column] = out[column].apply(lambda v: canon(v) if isinstance(v, str) and v.strip() else v)
        affected = int((before != out[column].astype(str)).sum())
    return out, affected
