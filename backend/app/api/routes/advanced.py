import json
import uuid
from datetime import datetime
from typing import List, Optional

import croniter
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage, load_version_df
from app.models.entities import DatasetVersion
from app.services.storage_service import StorageService
from app.engines.drift_detector import analyze_drift
from app.engines.correlation_analyzer import analyze_correlations
from app.engines.type_detector import analyze as type_analyze
from app.services.scheduler_service import ScheduledJob, Webhook, JobRun, JobStatus
from app.services.export_service import export_dataframe
from app.api.rbac_deps import require_dataset_read, require_schedule_manage, require_webhook_manage, require_permission
from app.models.rbac import Permission
require_editor = require_permission(Permission.DATASET_UPDATE)
from app.utils.serialize import to_jsonable

router = APIRouter()


# ---- Scheduler schemas ----
class JobCreate(BaseModel):
    name: str
    description: str = ""
    cron_expression: str
    dataset_id: Optional[str] = None
    ruleset: str = "general-v1"
    config: dict = {}


class JobUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    dataset_id: Optional[str] = None
    ruleset: Optional[str] = None
    config: Optional[dict] = None
    enabled: Optional[bool] = None


class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[str]
    secret: str = ""
    headers: dict = {}


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    secret: Optional[str] = None
    headers: Optional[dict] = None
    active: Optional[bool] = None


async def execute_job_async(run_id: str, job_id: str):
    """Background task to execute job (DB session managed by caller context)."""
    return None


def _next_run(cron_expression: str, base: Optional[datetime] = None) -> datetime:
    cron = croniter.croniter(cron_expression, base or datetime.utcnow())
    return cron.get_next(datetime)


# ---- Jobs & webhooks FIRST (avoid /{dataset_id} shadowing) ----
@router.post("/jobs", summary="Create scheduled job")
def create_job(job: JobCreate, db: Session = Depends(get_db),
               _: str = Depends(require_schedule_manage)):
    try:
        next_run = _next_run(job.cron_expression)
    except Exception as e:
        raise HTTPException(400, f"Invalid cron expression: {e}")
    sj = ScheduledJob(
        name=job.name,
        description=job.description,
        cron_expression=job.cron_expression,
        dataset_id=job.dataset_id,
        ruleset=job.ruleset,
        config=json.dumps(job.config),
        next_run=next_run,
        status=JobStatus.PENDING.value,
    )
    db.add(sj)
    db.commit()
    db.refresh(sj)
    return {"id": sj.id, "next_run": sj.next_run.isoformat() if sj.next_run else None}


@router.get("/jobs", summary="List scheduled jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(ScheduledJob).order_by(ScheduledJob.created_at.desc()).all()
    return [{"id": j.id, "name": j.name, "cron": j.cron_expression, "dataset_id": j.dataset_id,
             "enabled": j.enabled, "status": j.status,
             "next_run": j.next_run.isoformat() if j.next_run else None} for j in jobs]


@router.get("/jobs/{job_id}", summary="Get job details")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    runs = db.query(JobRun).filter(JobRun.job_id == job_id).order_by(JobRun.started_at.desc()).limit(10).all()
    return {
        "id": job.id, "name": job.name, "cron": job.cron_expression, "dataset_id": job.dataset_id,
        "enabled": job.enabled, "status": job.status,
        "next_run": job.next_run.isoformat() if job.next_run else None,
        "recent_runs": [{"id": r.id, "status": r.status, "started": r.started_at.isoformat(),
                         "issues": r.issues_found, "score": r.quality_score} for r in runs],
    }


@router.patch("/jobs/{job_id}", summary="Update job")
def update_job(job_id: str, update: JobUpdate, db: Session = Depends(get_db),
               _: str = Depends(require_schedule_manage)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        if field == "config" and value is not None:
            value = json.dumps(value)
        if field == "cron_expression" and value is not None:
            try:
                job.next_run = _next_run(value)
            except Exception as e:
                raise HTTPException(400, f"Invalid cron: {e}")
        setattr(job, field, value)
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"updated": job_id}


@router.post("/jobs/{job_id}/run", summary="Trigger job manually")
def trigger_job(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db),
                _: str = Depends(require_schedule_manage)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    run = JobRun(
        id=str(uuid.uuid4()),
        job_id=job.id,
        dataset_id=job.dataset_id,
        status=JobStatus.PENDING.value,
        triggered_by="manual",
    )
    db.add(run)
    db.commit()
    background_tasks.add_task(execute_job_async, run.id, job.id)
    return {"run_id": run.id, "status": "started"}


@router.post("/jobs/{job_id}/pause", summary="Pause scheduled job")
def pause_job(job_id: str, db: Session = Depends(get_db),
              _: str = Depends(require_schedule_manage)):
    from app.services.scheduler_service import JobScheduler
    # We need to access the scheduler instance - for now use DB directly
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status == JobStatus.PAUSED.value:
        raise HTTPException(400, "Job already paused")
    job.status = JobStatus.PAUSED.value
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"paused": job_id, "status": job.status}


@router.post("/jobs/{job_id}/resume", summary="Resume paused job")
def resume_job(job_id: str, db: Session = Depends(get_db),
               _: str = Depends(require_schedule_manage)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.PAUSED.value:
        raise HTTPException(400, "Job is not paused")
    job.status = JobStatus.PENDING.value
    try:
        cron = croniter.croniter(job.cron_expression, datetime.utcnow())
        job.next_run = cron.get_next(datetime)
    except Exception as e:
        raise HTTPException(400, f"Invalid cron: {e}")
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"resumed": job_id, "status": job.status, "next_run": job.next_run.isoformat() if job.next_run else None}


@router.post("/webhooks", summary="Create webhook")
def create_webhook(wh: WebhookCreate, db: Session = Depends(get_db),
                   _: str = Depends(require_webhook_manage)):
    w = Webhook(name=wh.name, url=wh.url, events=json.dumps(wh.events),
                secret=wh.secret, headers=json.dumps(wh.headers))
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"id": w.id}


@router.get("/webhooks", summary="List webhooks")
def list_webhooks(db: Session = Depends(get_db)):
    whs = db.query(Webhook).order_by(Webhook.created_at.desc()).all()
    return [{"id": w.id, "name": w.name, "url": w.url, "events": json.loads(w.events or "[]"),
             "active": w.active,
             "last_triggered": w.last_triggered.isoformat() if w.last_triggered else None} for w in whs]


@router.patch("/webhooks/{webhook_id}", summary="Update webhook")
def update_webhook(webhook_id: str, update: WebhookUpdate, db: Session = Depends(get_db),
                   _: str = Depends(require_webhook_manage)):
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(404, "Webhook not found")
    for field, value in update.model_dump(exclude_unset=True).items():
        if field in ("events", "headers") and value is not None:
            value = json.dumps(value)
        setattr(wh, field, value)
    db.commit()
    return {"updated": webhook_id}


@router.delete("/webhooks/{webhook_id}", summary="Delete webhook")
def delete_webhook(webhook_id: str, db: Session = Depends(get_db),
                   _: str = Depends(require_webhook_manage)):
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(404, "Webhook not found")
    db.delete(wh)
    db.commit()
    return {"deleted": webhook_id}


# ---- Dataset-scoped endpoints (after specific routes) ----
@router.get("/{dataset_id}/drift", summary="Detect drift between versions")
def get_drift(
    dataset_id: str,
    from_version: str = Query(..., description="Base version ID"),
    to_version: str = Query(..., description="Compare version ID"),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: str = Depends(require_dataset_read),
):
    """Compare two versions for data drift."""
    from_version_obj = db.query(DatasetVersion).filter(
        DatasetVersion.id == from_version, DatasetVersion.dataset_id == dataset_id
    ).first()
    to_version_obj = db.query(DatasetVersion).filter(
        DatasetVersion.id == to_version, DatasetVersion.dataset_id == dataset_id
    ).first()
    if not from_version_obj or not to_version_obj:
        raise HTTPException(404, "Version not found")
    df_from = load_version_df(storage, dataset_id, from_version)
    df_to = load_version_df(storage, dataset_id, to_version)
    type_from = type_analyze(df_from, {}).metrics.get("columns", {})
    type_to = type_analyze(df_to, {}).metrics.get("columns", {})
    result = analyze_drift(df_from, df_to, type_from, type_to)
    return to_jsonable({"dataset_id": dataset_id, "from_version": from_version, "to_version": to_version,
                        "drift": result.metrics, "issues": result.issues, "metadata": result.metadata})


@router.get("/{dataset_id}/correlations", summary="Analyze column correlations")
def get_correlations(
    dataset_id: str,
    version_id: Optional[str] = None,
    min_correlation: float = Query(0.3, ge=0, le=1),
    max_pairs: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: str = Depends(require_dataset_read),
):
    """Analyze correlations between columns."""
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(
        DatasetVersion.version_number.desc()
    ).all()
    if not vers:
        raise HTTPException(404, "No versions")
    v = next((x for x in vers if x.id == version_id), vers[0]) if version_id else vers[0]
    df = load_version_df(storage, dataset_id, v.id)
    type_info = type_analyze(df, {}).metrics.get("columns", {})
    config = {"min_correlation": min_correlation, "max_pairs": max_pairs}
    result = analyze_correlations(df, type_info, config)
    return to_jsonable({"dataset_id": dataset_id, "version_id": v.id, "correlations": result.metrics,
                        "issues": result.issues,
                        "correlation_details": result.metadata.get("correlations", [])})


@router.get("/{dataset_id}/export", summary="Export dataset in various formats with filtering options")
def export_dataset(
    dataset_id: str,
    format: str = Query("csv", pattern="^(csv|xlsx|json|parquet|delta|avro|zip)$"),
    version_id: Optional[str] = None,
    columns: Optional[str] = Query(None, description="Comma-separated list of columns to include"),
    filter_col: Optional[str] = Query(None, description="Column to filter on"),
    filter_op: Optional[str] = Query(None, description="Filter operator: eq, ne, gt, gte, lt, lte, in, contains"),
    filter_val: Optional[str] = Query(None, description="Filter value"),
    date_start: Optional[str] = Query(None, description="Start date for date range filter (ISO format)"),
    date_end: Optional[str] = Query(None, description="End date for date range filter (ISO format)"),
    date_column: Optional[str] = Query(None, description="Date column for date range filter"),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: str = Depends(require_dataset_read),
):
    """Export cleaned dataset in various formats with optional filtering and column selection."""
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(
        DatasetVersion.version_number.desc()
    ).all()
    if not vers:
        raise HTTPException(404, "No versions")
    v = next((x for x in vers if x.id == version_id), vers[0]) if version_id else vers[0]
    df = load_version_df(storage, dataset_id, v.id)
    
    # Parse optional parameters
    cols = columns.split(",") if columns else None
    filters = None
    if filter_col and filter_op and filter_val is not None:
        filters = {filter_col: {"op": filter_op, "value": filter_val}}
    date_range = None
    if date_start and date_end and date_column:
        date_range = (date_start, date_end)
    
    try:
        data = export_dataframe(df, format, columns=cols, filters=filters, date_range=date_range, date_column=date_column)
    except ImportError as e:
        raise HTTPException(400, f"Format '{format}' requires additional dependencies: {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    media_types = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
        "parquet": "application/octet-stream",
        "delta": "application/zip",
        "avro": "application/octet-stream",
        "zip": "application/zip",
    }
    ext = "zip" if format == "delta" else format
    return Response(
        data,
        media_type=media_types.get(format, "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename={dataset_id}_v{v.version_number}.{ext}"},
    )


@router.post("/{dataset_id}/auto-rules", summary="Generate validation rules from profile (AutoML)")
def auto_rules(
    dataset_id: str,
    max_rules: int = Query(20, ge=1, le=100),
    version_id: Optional[str] = None,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: str = Depends(require_editor),
):
    """Synthesize validation DSL rules from profile signals and persist them (ruleset=automl)."""
    from app.models.entities import ValidationRule
    from app.engines.auto_rule_engine import generate_rules
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(
        DatasetVersion.version_number.desc()).all()
    if not vers:
        raise HTTPException(404, "No versions")
    v = next((x for x in vers if x.id == version_id), vers[0]) if version_id else vers[0]
    df = load_version_df(storage, dataset_id, v.id)
    from app.services.profiling_service import profile_dataframe as _profile
    full = _profile(df)
    rules = generate_rules(full, full.get("all_issues", []), max_rules)
    created = []
    for r in rules:
        vr = ValidationRule(id=str(uuid.uuid4()), dataset_id=dataset_id, name=r["name"],
                            column=r["column"], operator=r["operator"],
                            value=json.dumps(r["value"]), severity=r.get("severity", "MEDIUM"),
                            ruleset="automl")
        db.add(vr)
        created.append({"name": r["name"], "column": r["column"], "operator": r["operator"],
                        "value": r["value"], "severity": r.get("severity", "MEDIUM")})
    db.commit()
    return to_jsonable({"dataset_id": dataset_id, "version_id": v.id,
                        "created": len(created), "rules": created})
