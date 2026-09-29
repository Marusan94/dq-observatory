import uuid
from fastapi import Request
from sqlalchemy.orm import Session
from app.models.base import SessionLocal
from app.services.storage_service import StorageService
import pandas as pd
import os


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_storage() -> StorageService:
    return StorageService()


def request_id(req: Request) -> str:
    return req.headers.get("X-Request-ID", str(uuid.uuid4()))


def load_version_df(storage: StorageService, dataset_id: str, version_id: str) -> pd.DataFrame:
    for ext in ("parquet", "csv"):
        p = storage.version_path(dataset_id, version_id, ext)
        if os.path.exists(p):
            if ext == "parquet":
                try:
                    return pd.read_parquet(p)
                except Exception:
                    continue
            return pd.read_csv(p, low_memory=False)
    raise FileNotFoundError("version data not found")


def save_version_df(storage: StorageService, dataset_id: str, version_id: str, df: pd.DataFrame) -> str:
    path = storage.version_path(dataset_id, version_id, "parquet")
    try:
        df.to_parquet(path, index=False)
        return path
    except Exception:
        path = storage.version_path(dataset_id, version_id, "csv")
        df.to_csv(path, index=False)
        return path
