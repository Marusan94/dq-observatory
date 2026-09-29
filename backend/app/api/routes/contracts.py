"""Data Contracts CRUD + breaking-change checks."""
import json
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage, load_version_df
from app.api.rbac_deps import require_dataset_read, require_permission
from app.models.rbac import Permission
from app.models.contracts import DataContract, ContractCheck, check_breaking_change
from app.models.entities import Dataset, DatasetVersion
from app.services.storage_service import StorageService
from app.engines.type_detector import analyze as type_analyze
from app.utils.serialize import to_jsonable

router = APIRouter()
require_editor = require_permission(Permission.DATASET_UPDATE)


class ContractCreate(BaseModel):
    dataset_id: str
    name: str
    schema_def: dict = Field(default={}, alias="schema")
    rules: list = []
    sla: dict = {}
    created_by: str = ""


class ContractUpdate(BaseModel):
    name: Optional[str] = None
    schema_def: Optional[dict] = Field(default=None, alias="schema")
    rules: Optional[list] = None
    sla: Optional[dict] = None
    status: Optional[str] = None


def _dump(c: DataContract) -> dict:
    return {"id": c.id, "dataset_id": c.dataset_id, "name": c.name, "version": c.version,
            "schema": json.loads(c.schema_json or "{}"), "rules": json.loads(c.rules_json or "[]"),
            "sla": json.loads(c.sla_json or "{}"), "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None}


@router.post("/contracts", summary="Create data contract")
def create_contract(body: ContractCreate, db: Session = Depends(get_db),
                   _: str = Depends(require_editor)):
    ds = db.query(Dataset).filter(Dataset.id == body.dataset_id).first()
    if not ds:
        raise HTTPException(404, "Dataset not found")
    c = DataContract(id=str(uuid.uuid4()), dataset_id=body.dataset_id, name=body.name,
                     schema_json=json.dumps(body.schema_def), rules_json=json.dumps(body.rules),
                     sla_json=json.dumps(body.sla), created_by=body.created_by)
    db.add(c)
    db.commit()
    db.refresh(c)
    return to_jsonable(_dump(c))


@router.get("/contracts", summary="List contracts")
def list_contracts(dataset_id: Optional[str] = None, db: Session = Depends(get_db),
                   _: str = Depends(require_dataset_read)):
    q = db.query(DataContract).order_by(DataContract.created_at.desc())
    if dataset_id:
        q = q.filter(DataContract.dataset_id == dataset_id)
    return to_jsonable([_dump(c) for c in q.all()])


@router.get("/contracts/{contract_id}", summary="Get contract")
def get_contract(contract_id: str, db: Session = Depends(get_db),
                 _: str = Depends(require_dataset_read)):
    c = db.query(DataContract).filter(DataContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "Contract not found")
    return to_jsonable(_dump(c))


@router.patch("/contracts/{contract_id}", summary="Update contract (new version)")
def update_contract(contract_id: str, body: ContractUpdate, db: Session = Depends(get_db),
                    _: str = Depends(require_editor)):
    c = db.query(DataContract).filter(DataContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "Contract not found")
    if body.name is not None:
        c.name = body.name
    if body.schema_def is not None:
        c.schema_json = json.dumps(body.schema_def)
    if body.rules is not None:
        c.rules_json = json.dumps(body.rules)
    if body.sla is not None:
        c.sla_json = json.dumps(body.sla)
    if body.status is not None:
        if body.status not in ("ACTIVE", "DEPRECATED"):
            raise HTTPException(400, "status must be ACTIVE|DEPRECATED")
        c.status = body.status
    c.version += 1
    c.updated_at = datetime.utcnow()
    db.commit()
    return to_jsonable(_dump(c))


@router.post("/contracts/{contract_id}/check", summary="Run breaking-change check on latest version")
def check_contract(contract_id: str, version_id: Optional[str] = None,
                   db: Session = Depends(get_db), storage: StorageService = Depends(get_storage),
                   _: str = Depends(require_dataset_read)):
    c = db.query(DataContract).filter(DataContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "Contract not found")
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == c.dataset_id).order_by(
        DatasetVersion.version_number.desc()).all()
    if not vers:
        raise HTTPException(404, "No versions")
    v = next((x for x in vers if x.id == version_id), vers[0]) if version_id else vers[0]
    df = load_version_df(storage, c.dataset_id, v.id)
    live = type_analyze(df, {}).metrics.get("columns", {})
    violations = check_breaking_change(json.loads(c.schema_json or "{}"), live)
    # SLA: min_score
    sla = json.loads(c.sla_json or "{}")
    min_score = sla.get("min_score")
    if min_score is not None and v.quality_score is not None and v.quality_score < min_score:
        violations.append({"type": "sla_min_score", "severity": "HIGH",
                           "expected": min_score, "got": v.quality_score})
    passed = 1 if not violations else 0
    chk = ContractCheck(id=str(uuid.uuid4()), contract_id=c.id, version_id=v.id,
                        passed=passed, violations_json=json.dumps(violations), score=v.quality_score)
    db.add(chk)
    db.commit()
    return to_jsonable({"contract_id": c.id, "version_id": v.id, "passed": bool(passed),
                        "violations": violations})


@router.get("/contracts/{contract_id}/checks", summary="List contract checks")
def list_checks(contract_id: str, limit: int = Query(20, ge=1, le=100),
                db: Session = Depends(get_db), _: str = Depends(require_dataset_read)):
    rows = db.query(ContractCheck).filter(ContractCheck.contract_id == contract_id).order_by(
        ContractCheck.created_at.desc()).limit(limit).all()
    return to_jsonable([{"id": r.id, "version_id": r.version_id, "passed": bool(r.passed),
                         "violations": json.loads(r.violations_json or "[]"), "score": r.score,
                         "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows])
