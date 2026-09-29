from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_storage, load_version_df
from app.models.entities import DatasetVersion
from app.services.profiling_service import profile_dataframe
from app.services.storage_service import StorageService
from app.utils.serialize import to_jsonable

router = APIRouter()


def _latest_version(db: Session, dataset_id: str, version_id: str | None):
    q = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id)
    vers = q.order_by(DatasetVersion.version_number.desc()).all()
    if not vers:
        raise HTTPException(404, "No versions for dataset")
    if version_id:
        v = next((x for x in vers if x.id == version_id), None)
        if not v:
            raise HTTPException(404, "Version not found")
        return v
    return vers[0]


@router.post("/{dataset_id}/profile", summary="Run profiling (sync for small/medium)")
def run_profile(dataset_id: str, payload: dict | None = None, db: Session = Depends(get_db),
                storage: StorageService = Depends(get_storage)):
    payload = payload or {}
    v = _latest_version(db, dataset_id, payload.get("version_id"))
    df = load_version_df(storage, dataset_id, v.id)
    # safety cap: sample for very large frames for sync path
    profile = profile_dataframe(df, payload.get("config", {}))
    return to_jsonable({"dataset_id": dataset_id, "version_id": v.id, "profile": profile})


@router.get("/{dataset_id}/profile", summary="Get cached profile (recompute)")
def get_profile(dataset_id: str, version_id: str | None = None, db: Session = Depends(get_db),
                storage: StorageService = Depends(get_storage)):
    v = _latest_version(db, dataset_id, version_id)
    df = load_version_df(storage, dataset_id, v.id)
    return to_jsonable({"dataset_id": dataset_id, "version_id": v.id, "profile": profile_dataframe(df, {})})


@router.get("/{dataset_id}/columns/{column}", summary="Column detail: type, stats, patterns, issues")
def column_detail(dataset_id: str, column: str, version_id: str | None = None,
                  db: Session = Depends(get_db), storage: StorageService = Depends(get_storage)):
    from app.models.entities import QualityIssue
    import json as _json
    v = _latest_version(db, dataset_id, version_id)
    df = load_version_df(storage, dataset_id, v.id)
    if column not in df.columns:
        raise HTTPException(404, f"Column '{column}' not found")
    profile = profile_dataframe(df, {})
    col = next((c for c in profile["columns"] if c["name"] == column), None)
    issues = db.query(QualityIssue).filter(
        QualityIssue.dataset_id == dataset_id, QualityIssue.column == column).limit(50).all()
    return to_jsonable({"dataset_id": dataset_id, "version_id": v.id, "column": col,
            "issues": [{"severity": i.severity, "category": i.category, "description": i.description,
                        "row_count": i.row_count, "percentage": i.percentage, "rule": i.rule,
                        "examples": _json.loads(i.examples or "[]")} for i in issues] or
                       [i for i in profile["all_issues"] if i.get("column") == column]})
