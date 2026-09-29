import hashlib
import os
import re
from pathlib import Path

SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def sha256_file(path: str, chunk_size: int = 8192) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str, max_len: int = 120) -> str:
    base = os.path.basename(name or "upload")
    base = base.replace("..", "_")
    base = SAFE_FILENAME_RE.sub("_", base)
    return base[:max_len] or "upload"


def ensure_dir(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def is_within_directory(base: str, target: str) -> bool:
    try:
        Path(target).resolve().relative_to(Path(base).resolve())
        return True
    except ValueError:
        return False
