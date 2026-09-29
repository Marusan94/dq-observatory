from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings


def _resolve_db_url(url: str) -> str:
    if url.startswith("sqlite:"):
        # sqlite:///./storage/dq.db or sqlite:////abs/path or :memory:
        if ":memory:" in url:
            return url
        prefix = "sqlite:///"
        path_part = url[len(prefix):]
        p = Path(path_part)
        if not p.is_absolute():
            # resolve relative to project root (dq-observatory/)
            root = Path(__file__).resolve().parents[3]
            p = (root / path_part).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}{p.as_posix()}"
    return url


settings = get_settings()
DATABASE_URL = _resolve_db_url(settings.database_url)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
