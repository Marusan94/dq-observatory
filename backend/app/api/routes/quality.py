import json
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_storage, load_version_df
from app.models.entities import DatasetVersion, QualityRun, QualityIssue
from app.services.profiling_service import profile_dataframe
from app.services.quality_service import compute_score, recommendations
from app.services.storage_service import StorageService
from app.utils.serialize import to_jsonable

router = APIRouter()
SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def _latest(db: Session, dataset_id: str, version_id: str | None):
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number.desc()).all()
    if not vers:
        raise HTTPException(404, "No versions")
    if version_id:
        v = next((x for x in vers if x.id == version_id), None)
        if not v:
            raise HTTPException(404, "Version not found")
        return v
    return vers[0]


@router.post("/{dataset_id}/quality/run", summary="Run quality analysis")
def run_quality(dataset_id: str, payload: dict | None = None, db: Session = Depends(get_db),
                storage: StorageService = Depends(get_storage)):
    from app.core.config import get_settings
    payload = payload or {}
    t0 = time.time()
    v = _latest(db, dataset_id, payload.get("version_id"))
    df = load_version_df(storage, dataset_id, v.id)
    profile = profile_dataframe(df, payload.get("config", {}))
    score = compute_score(profile, len(df))
    recs = recommendations(profile, score)
    run = QualityRun(id=str(uuid.uuid4()), dataset_id=dataset_id, version_id=v.id,
                     status="COMPLETED", score=score["overall"],
                     dimensions=json.dumps(score), warnings=json.dumps(profile.get("warnings", [])),
                     duration_ms=int((time.time() - t0) * 1000),
                     engine_version=get_settings().engine_version,
                     ruleset=payload.get("ruleset", get_settings().ruleset_version))
    db.add(run)
    db.flush()
    for iss in profile.get("all_issues", []):
        db.add(QualityIssue(id=str(uuid.uuid4()), dataset_id=dataset_id, version_id=v.id,
                            run_id=run.id, severity=iss.get("severity", "LOW"),
                            category=iss.get("category", "VALIDITY"), column=str(iss.get("column")) if iss.get("column") else None,
                            row_count=int(iss.get("row_count", 0)), percentage=float(iss.get("percentage", 0)),
                            description=iss.get("description", "")[:2000],
                            examples=json.dumps(iss.get("examples", [])[:5], default=str),
                            rule=iss.get("rule", ""), auto_fix_available=1 if iss.get("auto_fix_available") else 0,
                            status="OPEN"))
    v.quality_score = score["overall"]
    db.commit()
    return to_jsonable({"run_id": run.id, "dataset_id": dataset_id, "version_id": v.id,
            "score": score, "issues_count": len(profile.get("all_issues", [])),
            "recommendations": recs, "warnings": profile.get("warnings", [])})


@router.get("/{dataset_id}/quality", summary="Get latest quality run")
def get_quality(dataset_id: str, version_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(QualityRun).filter(QualityRun.dataset_id == dataset_id)
    if version_id:
        q = q.filter(QualityRun.version_id == version_id)
    run = q.order_by(QualityRun.created_at.desc()).first()
    if not run:
        raise HTTPException(404, "No quality run yet. POST quality/run first.")
    return {"run_id": run.id, "score": run.score, "dimensions": json.loads(run.dimensions),
            "warnings": json.loads(run.warnings), "status": run.status,
            "created_at": run.created_at, "ruleset": run.ruleset}


@router.get("/{dataset_id}/quality/trend", summary="Quality trend across versions (observability)")
def quality_trend(dataset_id: str, db: Session = Depends(get_db)):
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number).all()
    if not vers:
        raise HTTPException(404, "No versions")
    runs = db.query(QualityRun).filter(QualityRun.dataset_id == dataset_id).order_by(QualityRun.created_at).all()
    return to_jsonable({"dataset_id": dataset_id,
            "versions": [{"version_number": v.version_number, "label": v.label, "rows": v.rows,
                          "quality_score": v.quality_score, "created_at": v.created_at} for v in vers],
            "runs": [{"score": r.score, "created_at": r.created_at, "ruleset": r.ruleset} for r in runs]})


@router.get("/{dataset_id}/issues", summary="List issues with filters + pagination")
def list_issues(dataset_id: str, severity: str | None = None, category: str | None = None,
                column: str | None = None, status: str | None = None,
                auto_fix: bool | None = None, search: str | None = None,
                page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
                db: Session = Depends(get_db)):
    q = db.query(QualityIssue).filter(QualityIssue.dataset_id == dataset_id)
    if severity:
        q = q.filter(QualityIssue.severity == severity.upper())
    if category:
        q = q.filter(QualityIssue.category == category.upper())
    if column:
        q = q.filter(QualityIssue.column == column)
    if status:
        q = q.filter(QualityIssue.status == status.upper())
    if auto_fix is not None:
        q = q.filter(QualityIssue.auto_fix_available == (1 if auto_fix else 0))
    if search:
        q = q.filter(QualityIssue.description.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"page": page, "page_size": page_size, "total": total,
            "items": [{"id": i.id, "severity": i.severity, "category": i.category, "column": i.column,
                       "row_count": i.row_count, "percentage": i.percentage, "description": i.description,
                       "examples": json.loads(i.examples or "[]"), "rule": i.rule,
                       "auto_fix_available": bool(i.auto_fix_available), "status": i.status} for i in items]}
