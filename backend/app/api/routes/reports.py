import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_storage, load_version_df
from app.models.entities import Dataset, DatasetVersion, QualityRun, QualityIssue, CleaningOperation, ValidationRule
from app.services.profiling_service import profile_dataframe
from app.services.quality_service import compute_score
from app.services.report_service import build_report, to_html
from app.services.validation_service import evaluate
from app.services.storage_service import StorageService
from app.core.config import get_settings
from app.utils.serialize import to_jsonable

router = APIRouter()
settings = get_settings()


def _assemble(db: Session, storage: StorageService, dataset_id: str):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(404, "Dataset not found")
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number.desc()).all()
    v = vers[0]
    df = load_version_df(storage, dataset_id, v.id)
    profile = profile_dataframe(df, {})
    score = compute_score(profile, len(df))
    run = db.query(QualityRun).filter(QualityRun.dataset_id == dataset_id).order_by(QualityRun.created_at.desc()).first()
    issues = [{"severity": i.severity, "column": i.column, "description": i.description,
               "row_count": i.row_count, "percentage": i.percentage, "rule": i.rule}
              for i in db.query(QualityIssue).filter(QualityIssue.dataset_id == dataset_id).limit(200).all()] or profile.get("all_issues", [])
    ops = [{"operation": o.operation, "column": o.column, "affected_rows": o.affected_rows}
           for o in db.query(CleaningOperation).filter(CleaningOperation.dataset_id == dataset_id).all()]
    rules = [{"column": r.column, "operator": r.operator, "value": json.loads(r.value or "null")}
             for r in db.query(ValidationRule).filter(ValidationRule.dataset_id == dataset_id).all()]
    validation = evaluate(df, [{"column": r["column"], "operator": r["operator"], "value": r["value"],
                                "name": r["column"], "severity": "MEDIUM"} for r in rules]) if rules else []
    report = build_report({"name": ds.name, "rows": ds.rows, "columns": ds.columns},
                          {"id": v.id, "label": v.label, "rows": len(df)},
                          profile, score, issues, ops, validation,
                          settings.engine_version, settings.ruleset_version)
    # before/after: v1 vs current
    first = vers[-1]
    report["before_after"] = {"before_version": first.label, "before_rows": first.rows,
                              "after_version": v.label, "after_rows": len(df),
                              "before_score": first.quality_score, "after_score": score["overall"]}
    report["executive_summary"] = {
        "overall": score["overall"],
        "main_concerns": [i["description"][:120] for i in issues[:3]],
        "note": "Observed facts only — no invented business causes."}
    return report, df, profile


@router.get("/{dataset_id}/report", summary="Quality report JSON")
def get_report(dataset_id: str, db: Session = Depends(get_db), storage: StorageService = Depends(get_storage)):
    report, _, _ = _assemble(db, storage, dataset_id)
    return to_jsonable(report)


@router.get("/{dataset_id}/report.html", response_class=HTMLResponse, summary="Quality report HTML")
def get_report_html(dataset_id: str, db: Session = Depends(get_db), storage: StorageService = Depends(get_storage)):
    report, _, _ = _assemble(db, storage, dataset_id)
    return to_html(report)


@router.get("/{dataset_id}/lineage/graph", summary="Lineage DAG nodes/edges")
def lineage_graph(dataset_id: str, db: Session = Depends(get_db)):
    """DAG of versions (nodes) linked by cleaning operations (edges)."""
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(
        DatasetVersion.version_number.asc()).all()
    if not vers:
        raise HTTPException(404, "Dataset not found")
    nodes = [{"id": v.id, "n": v.version_number, "label": v.label, "rows": v.rows,
              "score": v.quality_score,
              "at": v.created_at.isoformat() if v.created_at else None} for v in vers]
    by_id = {v.id for v in vers}
    edges = []
    incoming: set = set()
    for o in db.query(CleaningOperation).filter(CleaningOperation.dataset_id == dataset_id).all():
        if o.from_version_id in by_id and o.to_version_id in by_id:
            edges.append({"from": o.from_version_id, "to": o.to_version_id,
                          "op": o.operation, "column": o.column, "affected": o.affected_rows})
            incoming.add(o.to_version_id)
    for prev, cur in zip(vers, vers[1:]):
        if cur.id not in incoming:
            edges.append({"from": prev.id, "to": cur.id, "op": "derived",
                          "column": None, "affected": 0})
    return to_jsonable({"dataset_id": dataset_id, "nodes": nodes, "edges": edges})
