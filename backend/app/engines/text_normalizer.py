import re
import unicodedata
import pandas as pd

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def trim(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def normalize_email(v: str) -> str:
    return trim(str(v)).lower()


def normalize_phone(v: str, default_country: str = "US") -> str:
    digits = re.sub(r"\D", "", str(v))
    if len(digits) == 10 and default_country in ("US", "CO"):
        # keep national digits; canonical +digits when original had +
        return ("+" + digits) if "+" in str(v) else digits
    if len(digits) > 10:
        return "+" + digits
    return digits


def normalize_name(v: str) -> str:
    v = trim(str(v))
    v = "".join(c for c in unicodedata.normalize("NFKD", v) if not unicodedata.combining(c)) if False else v
    return v.title()


def normalize_text(v, mode: str = "trim") -> str:
    s = str(v)
    if mode == "lower":
        return trim(s).lower()
    if mode == "upper":
        return trim(s).upper()
    if mode == "title":
        return trim(s).title()
    return trim(s)


def classify_email(v: str) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return "missing"
    s = str(v).strip()
    if " " in s or s.count("@") != 1:
        return "invalid"
    if bool(EMAIL_RE.match(s.lower())):
        if s != s.lower() or s != s.strip():
            return "suspicious"
        return "valid"
    return "invalid"
