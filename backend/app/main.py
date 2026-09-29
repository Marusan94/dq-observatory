import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.models.base import Base, engine, DATABASE_URL, SessionLocal
from app.models import entities  # noqa: F401  (register tables)
from app.services import scheduler_service  # noqa: F401  (register scheduled_jobs/webhooks/job_runs)
from app.models import rbac  # noqa: F401  (register users/workspaces/RBAC tables)
from app.models import ai  # noqa: F401  (register AI tables)
from app.models import contracts  # noqa: F401  (register data contracts tables)
from app.api.routes import health, datasets, profiling, quality, cleaning, validation, reports, exports, search, advanced, ai, contracts, stream

settings = get_settings()
setup_logging(settings.log_level)
log = get_logger("dq")

# Ensure tables exist even if lifespan is not triggered (e.g. TestClient without context)
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

_scheduler = None


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    Base.metadata.create_all(bind=engine)
    log.info("startup", engine_version=settings.engine_version, db=str(DATABASE_URL)[:80])
    
    # Start scheduler
    db = SessionLocal()
    try:
        _scheduler = scheduler_service.create_scheduler(lambda: SessionLocal())
        from app.services.quality_service import compute_score
        from app.services.profiling_service import profile_dataframe
        from app.services.storage_service import StorageService
        import pandas as pd
        import os
        
        def quality_run_handler(db, job):
            storage = StorageService()
            if job.dataset_id:
                datasets = [job.dataset_id]
            else:
                from app.models.entities import Dataset
                datasets = [d.id for d in db.query(Dataset.id).all()]
            
            total_issues = 0
            scores = {}
            for ds_id in datasets:
                # Get latest version
                from app.models.entities import DatasetVersion
                vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == ds_id).order_by(
                    DatasetVersion.version_number.desc()).first()
                if not vers:
                    continue
                # Load dataframe
                for ext in ("parquet", "csv"):
                    path = storage.version_path(ds_id, vers.id, ext)
                    if os.path.exists(path):
                        if ext == "parquet":
                            df = pd.read_parquet(path)
                        else:
                            df = pd.read_csv(path, low_memory=False)
                        break
                else:
                    continue
                profile = profile_dataframe(df)
                score = compute_score(profile, len(df))
                scores[ds_id] = score["overall"]
                total_issues += sum(1 for _ in score["dimensions"])
            return {"score": scores, "issues_count": total_issues}
        
        _scheduler.register_handler("quality_run", quality_run_handler)
        _scheduler.start()
    finally:
        db.close()
    
    yield
    
    # Shutdown
    if _scheduler:
        _scheduler.stop()


app = FastAPI(title="DQ Observatory", version=settings.app_version, lifespan=lifespan,
              description="Profile, validate, clean and audit CSV/XLSX datasets with a transparent quality engine.")

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    try:
        resp = await call_next(request)
    except Exception as e:
        log.error("unhandled", request_id=rid, path=request.url.path, error=str(e))
        return JSONResponse({"code": "INTERNAL_ERROR", "message": "Unexpected error. Check logs with request_id.",
                             "details": {}, "request_id": rid}, status_code=500)
    resp.headers["X-Request-ID"] = rid
    return resp


prefix = settings.api_v1_prefix
app.include_router(health.router, tags=["health"])
app.include_router(datasets.router, prefix=f"{prefix}/datasets", tags=["datasets"])
app.include_router(profiling.router, prefix=f"{prefix}/datasets", tags=["profiling"])
app.include_router(quality.router, prefix=f"{prefix}/datasets", tags=["quality"])
app.include_router(cleaning.router, prefix=f"{prefix}/datasets", tags=["cleaning"])
app.include_router(validation.router, prefix=f"{prefix}/datasets", tags=["validation"])
app.include_router(reports.router, prefix=f"{prefix}/datasets", tags=["reports"])
app.include_router(exports.router, prefix=f"{prefix}/datasets", tags=["exports"])
app.include_router(search.router, prefix=f"{prefix}", tags=["search"])
app.include_router(advanced.router, prefix=f"{prefix}", tags=["advanced"])
app.include_router(ai.router, prefix=f"{prefix}", tags=["ai"])
app.include_router(contracts.router, prefix=f"{prefix}", tags=["contracts"])
app.include_router(stream.router, prefix=f"{prefix}", tags=["stream"])
# issue fix route mounted under datasets prefix already contains /issues/... — expose alias
app.include_router(cleaning.router, prefix=f"{prefix}", tags=["cleaning"])


@app.get("/", summary="Root")
def root():
    return {"service": "DQ Observatory", "version": settings.app_version,
            "engine": settings.engine_version, "docs": "/docs"}
