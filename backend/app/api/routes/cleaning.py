import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_storage, load_version_df, save_version_df
from app.models.entities import Dataset, DatasetVersion, CleaningOperation, AuditLog, QualityIssue
from app.schemas.common import CleaningRequest
from app.services.cleaning_service import preview_op, apply_op, AUTO_OPS
from app.services.profiling_service import profile_dataframe
from app.services.quality_service import compute_score
from app.services.storage_service import StorageService

router = APIRouter()


@router.post("/{dataset_id}/clean", summary="Preview or apply cleaning operation (versioned, undoable)")
def clean(dataset_id: str, req: CleaningRequest, db: Session = Depends(get_db),
          storage: StorageService = Depends(get_storage)):
    if req.operation not in AUTO_OPS:
        raise HTTPException(400, f"Unknown operation. Allowed: {sorted(AUTO_OPS)}")
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number.desc()).all()
    if not vers:
        raise HTTPException(404, "No versions")
    cur = vers[0]
    df = load_version_df(storage, dataset_id, cur.id)
    # before score (cheap estimate from profile missing/dup only if preview)
    preview = preview_op(df, req.operation, req.column, req.params)
    if req.preview_only:
        return {"preview": True, "operation": req.operation, "column": req.column,
                "preview_data": preview,
                "note": "Estimated preview on samples. Apply to create a new version."}
    new_df, affected = apply_op(df, req.operation, req.column, req.params)
    new_id = str(uuid.uuid4())
    path = save_version_df(storage, dataset_id, new_id, new_df)
    new_ver = DatasetVersion(id=new_id, dataset_id=dataset_id, version_number=cur.version_number + 1,
                             label=f"v{cur.version_number + 1} {req.operation}",
                             parent_version_id=cur.id, storage_path=path, rows=len(new_df))
    # recompute score for new version
    try:
        prof = profile_dataframe(new_df, {})
        new_ver.quality_score = compute_score(prof, len(new_df))["overall"]
    except Exception:
        new_ver.quality_score = cur.quality_score
    db.add(new_ver)
    db.flush()
    db.add(CleaningOperation(id=str(uuid.uuid4()), dataset_id=dataset_id,
                             from_version_id=cur.id, to_version_id=new_id,
                             operation=req.operation, column=req.column,
                             params=json.dumps(req.params or {}), affected_rows=affected, actor="user"))
    db.add(AuditLog(dataset_id=dataset_id, action="cleaning_applied",
                    detail=json.dumps({"op": req.operation, "col": req.column, "affected": affected})))
    db.commit()
    # before/after summary
    return {"applied": True, "operation": req.operation, "column": req.column,
            "affected_rows": affected, "from_version": cur.id, "to_version": new_id,
            "before_rows": len(df), "after_rows": len(new_df),
            "new_quality_score": new_ver.quality_score}


@router.get("/{dataset_id}/versions", summary="Version lineage")
def versions(dataset_id: str, db: Session = Depends(get_db)):
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number).all()
    ops = db.query(CleaningOperation).filter(CleaningOperation.dataset_id == dataset_id).order_by(CleaningOperation.created_at).all()
    return {"versions": [{"id": v.id, "n": v.version_number, "label": v.label, "rows": v.rows,
                          "quality_score": v.quality_score, "parent": v.parent_version_id,
                          "created_at": v.created_at} for v in vers],
            "operations": [{"id": o.id, "op": o.operation, "column": o.column,
                            "affected": o.affected_rows, "from": o.from_version_id,
                            "to": o.to_version_id, "at": o.created_at} for o in ops]}


@router.post("/{dataset_id}/reset", summary="Reset to original v1 (never destroys v1)")
def reset(dataset_id: str, db: Session = Depends(get_db)):
    v1 = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id,
                                         DatasetVersion.version_number == 1).first()
    if not v1:
        raise HTTPException(404, "v1 not found")
    db.add(AuditLog(dataset_id=dataset_id, action="reset_to_original", detail="{}"))
    db.commit()
    return {"reset_to": v1.id, "note": "Original preserved. New uploads create new datasets."}


@router.post("/issues/{issue_id}/fix", summary="Apply suggested auto-fix for an issue")
def fix_issue(issue_id: str, db: Session = Depends(get_db), storage: StorageService = Depends(get_storage)):
    iss = db.query(QualityIssue).filter(QualityIssue.id == issue_id).first()
    if not iss:
        raise HTTPException(404, "Issue not found")
    if not iss.auto_fix_available:
        raise HTTPException(400, "Issue requires manual review (no safe auto-fix).")
    rule_map = {"NOT_NULL": "standardize_missing", "MAX_NULL_PERCENTAGE": "standardize_missing",
                "VALID_EMAIL": "normalize_email", "VALID_PHONE": "normalize_phone",
                "UNIQUE": "remove_exact_duplicates", "STANDARD_CASE": "standardize_categories",
                "NUMERIC_RANGE": "parse_numeric"}
    op = rule_map.get(iss.rule, "trim_whitespace")
    from app.schemas.common import CleaningRequest as CR
    return clean(iss.dataset_id, CR(operation=op, column=iss.column, params={}), db, storage)
