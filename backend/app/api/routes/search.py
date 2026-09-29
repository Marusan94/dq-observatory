from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.entities import Dataset, DatasetVersion, QualityIssue, ValidationRule
from app.utils.serialize import to_jsonable

router = APIRouter()


@router.get("/search", summary="Global search: datasets, columns, issues, rules")
def search(q: str = Query(..., min_length=1, max_length=100), limit: int = Query(10, ge=1, le=50),
           db: Session = Depends(get_db)):
    like = f"%{q}%"
    datasets = db.query(Dataset).filter(Dataset.name.ilike(like)).limit(limit).all()
    # columns live in stored dataframes — searchable via issue/rule column names
    issue_cols = [r[0] for r in db.query(QualityIssue.column).filter(QualityIssue.column.ilike(like)).distinct().limit(limit).all()]
    rule_cols = [r[0] for r in db.query(ValidationRule.column).filter(ValidationRule.column.ilike(like)).distinct().limit(limit).all()]
    issues = db.query(QualityIssue).filter(QualityIssue.description.ilike(like)).limit(limit).all()
    rules = db.query(ValidationRule).filter(ValidationRule.name.ilike(like)).limit(limit).all()
    return to_jsonable({
        "datasets": [{"id": d.id, "name": d.name, "rows": d.rows} for d in datasets],
        "columns": sorted(set([c for c in (issue_cols + rule_cols) if c]))[:limit],
        "issues": [{"id": i.id, "dataset_id": i.dataset_id, "column": i.column,
                    "description": i.description[:160]} for i in issues],
        "rules": [{"id": r.id, "dataset_id": r.dataset_id, "name": r.name, "column": r.column} for r in rules],
    })
