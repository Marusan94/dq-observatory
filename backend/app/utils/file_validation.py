import os

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}
ALLOWED_MIME = {
    "text/csv", "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/json", "text/plain", "application/octet-stream",
}
CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def validate_extension(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported extension '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")
    return ext


def validate_size(path: str, max_mb: int) -> None:
    size = os.path.getsize(path)
    if size > max_mb * 1024 * 1024:
        raise ValueError(f"File too large ({size/1e6:.1f} MB > {max_mb} MB)")


def sanitize_excel_value(value):
    """Neutralize CSV/Excel formula injection on export (OWASP)."""
    if isinstance(value, str) and value.startswith(CSV_INJECTION_PREFIXES):
        return "'" + value
    return value
