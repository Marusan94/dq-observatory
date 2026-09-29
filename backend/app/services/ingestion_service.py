import os
import pandas as pd
from app.utils.file_validation import validate_extension, validate_size
from app.utils.hashing import sha256_file, safe_filename


def detect_encoding(path: str) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                f.read(8192)
            return enc
        except Exception:
            continue
    return "utf-8"


def read_tabular(path: str, ext: str) -> pd.DataFrame:
    if ext == ".csv":
        enc = detect_encoding(path)
        # try sniffing separator via first chunk
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            return pd.read_csv(path, encoding=enc, sep=";", low_memory=False)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path, engine="openpyxl" if ext == ".xlsx" else None)
    if ext == ".json":
        df = pd.read_json(path)
        if isinstance(df, pd.DataFrame):
            return df
        return pd.json_normalize(df)
    raise ValueError(f"Unsupported format {ext}")


def ingest_upload(tmp_path: str, original_filename: str, max_mb: int) -> dict:
    validate_size(tmp_path, max_mb)
    ext = validate_extension(original_filename)
    file_hash = sha256_file(tmp_path)
    df = read_tabular(tmp_path, ext)
    return {"ext": ext, "hash": file_hash, "df": df,
            "rows": len(df), "columns": len(df.columns),
            "safe_name": safe_filename(original_filename)}
