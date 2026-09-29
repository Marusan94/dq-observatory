import os
from pathlib import Path
from app.core.config import get_settings


class StorageService:
    """Abstraction — MVP local, future S3CompatibleStorage."""
    def __init__(self, base: str | None = None):
        raw = base or get_settings().storage_path
        p = Path(raw)
        if not p.is_absolute():
            root = Path(__file__).resolve().parents[3]
            p = root / raw
        self.base = str(p.resolve())
        Path(self.base).mkdir(parents=True, exist_ok=True)

    def dataset_dir(self, dataset_id: str) -> str:
        p = os.path.join(self.base, "datasets", dataset_id)
        Path(p).mkdir(parents=True, exist_ok=True)
        return p

    def version_path(self, dataset_id: str, version_id: str, ext: str = "parquet") -> str:
        return os.path.join(self.dataset_dir(dataset_id), f"{version_id}.{ext}")
