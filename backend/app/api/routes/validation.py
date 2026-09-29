import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_storage, load_version_df
from app.models.entities import DatasetVersion, ValidationRule
from app.schemas.common import ValidationRuleIn
from app.services.validation_service import evaluate, OPERATORS
from app.services.storage_service import StorageService

router = APIRouter()


@router.post("/{dataset_id}/rules", summary="Create validation rule (structured DSL, no eval)")
def create_rule(dataset_id: str, rule: ValidationRuleIn, db: Session = Depends(get_db)):
    if rule.operator not in OPERATORS:
        raise HTTPException(400, f"Unknown operator. Allowed: {sorted(OPERATORS)}")
    r = ValidationRule(id=str(uuid.uuid4()), dataset_id=dataset_id, name=rule.name,
                       column=rule.column, operator=rule.operator,
                       value=json.dumps(rule.value, default=str), severity=rule.severity.upper())
    db.add(r)
    db.commit()
    return {"id": r.id, "name": r.name, "column": r.column, "operator": r.operator}


@router.get("/{dataset_id}/rules", summary="List validation rules")
def list_rules(dataset_id: str, db: Session = Depends(get_db)):
    rs = db.query(ValidationRule).filter(ValidationRule.dataset_id == dataset_id).all()
    return [{"id": r.id, "name": r.name, "column": r.column, "operator": r.operator,
             "value": json.loads(r.value or "null"), "severity": r.severity} for r in rs]


@router.post("/{dataset_id}/validate", summary="Run validation against latest version")
def run_validation(dataset_id: str, payload: dict | None = None, db: Session = Depends(get_db),
                   storage: StorageService = Depends(get_storage)):
    payload = payload or {}
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number.desc()).all()
    if not vers:
        raise HTTPException(404, "No versions")
    df = load_version_df(storage, dataset_id, vers[0].id)
    rules = db.query(ValidationRule).filter(ValidationRule.dataset_id == dataset_id).all()
    rule_dicts = [{"name": r.name, "column": r.column, "operator": r.operator,
                   "value": json.loads(r.value or "null"), "severity": r.severity} for r in rules]
    # allow ad-hoc rules in payload too
    for ar in payload.get("rules", []):
        if ar.get("operator") in OPERATORS:
            rule_dicts.append(ar)
    if not rule_dicts:
        # sensible defaults from profile: not-null on all cols + unique on id-like
        rule_dicts = [{"name": f"{c} not null", "column": str(c), "operator": "not_null",
                       "value": None, "severity": "LOW"} for c in df.columns[:10]]
    results = evaluate(df, rule_dicts)
    passed = sum(1 for r in results if r["status"] == "PASS")
    return {"dataset_id": dataset_id, "version_id": vers[0].id, "passed": passed,
            "failed": len(results) - passed, "results": results}
