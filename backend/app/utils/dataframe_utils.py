import pandas as pd

MISSING_TOKENS = {"", "n/a", "na", "null", "none", "unknown", "-", "?", "nan", "nil", "n.a.", "na."}


def is_missing_like(value) -> tuple[bool, str]:
    """Return (is_missing, category). Categories: null/empty/whitespace/placeholder/unknown."""
    if value is None:
        return True, "null"
    try:
        if pd.isna(value):
            return True, "null"
    except Exception:
        pass
    if isinstance(value, str):
        if value == "":
            return True, "empty"
        if value.strip() == "":
            return True, "whitespace"
        low = value.strip().lower()
        if low in MISSING_TOKENS:
            if low in {"unknown", "?"}:
                return True, "unknown"
            if low == "-":
                return True, "not_applicable?"
            return True, "placeholder"
    return False, ""


def paginate_df(df: pd.DataFrame, page: int, page_size: int) -> dict:
    page = max(1, page)
    page_size = min(max(1, page_size), 500)
    total = len(df)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "page": page, "page_size": page_size, "total_rows": total,
        "rows": df.iloc[start:end].astype(object).where(pd.notnull(df.iloc[start:end]), None).to_dict(orient="records"),
    }
