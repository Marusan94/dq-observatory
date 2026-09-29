"""Data Contracts for governance: schema + rules + SLA per dataset."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey
from app.models.base import Base


def _uuid():
    return str(uuid.uuid4())


class DataContract(Base):
    __tablename__ = "data_contracts"

    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    schema_json = Column(Text, default="{}")  # {col: {physical_type, semantic_type, required}}
    rules_json = Column(Text, default="[]")  # validation rules snapshot
    sla_json = Column(Text, default="{}")  # {freshness_hours, min_score, max_missing_rate}
    status = Column(String, default="ACTIVE")  # ACTIVE | DEPRECATED
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContractCheck(Base):
    __tablename__ = "contract_checks"

    id = Column(String, primary_key=True, default=_uuid)
    contract_id = Column(String, ForeignKey("data_contracts.id"), nullable=False, index=True)
    version_id = Column(String, ForeignKey("dataset_versions.id"), nullable=True)
    passed = Column(Integer, default=0)  # 0/1
    violations_json = Column(Text, default="[]")
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def check_breaking_change(contract_schema: dict, live_columns: dict) -> list:
    """Compare contract schema vs live profile columns. Returns violations."""
    violations = []
    for col, spec in (contract_schema or {}).items():
        live = (live_columns or {}).get(col)
        if live is None:
            if spec.get("required", True):
                violations.append({"type": "column_removed", "column": col, "severity": "HIGH"})
            continue
        exp_type = spec.get("physical_type")
        got_type = live.get("physical_type")
        if exp_type and got_type and exp_type != got_type:
            violations.append({"type": "type_changed", "column": col, "severity": "MEDIUM",
                               "expected": exp_type, "got": got_type})
    return violations
