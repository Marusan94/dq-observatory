import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


def _uuid():
    return str(uuid.uuid4())


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_hash = Column(String, index=True)
    file_size = Column(Integer, default=0)
    file_format = Column(String, default="csv")
    rows = Column(Integer, default=0)
    columns = Column(Integer, default=0)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True)
    owner_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    versions = relationship("DatasetVersion", back_populates="dataset", cascade="all, delete-orphan")
    workspace = relationship("Workspace", back_populates="datasets", foreign_keys=[workspace_id])
    # RBAC explícito vía tabla dataset_permissions con queries directas
    # (sin relationship ORM para evitar ambigüedad granted_by/user_id)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    label = Column(String, default="v1 Original")
    parent_version_id = Column(String, nullable=True)
    storage_path = Column(String, nullable=False)
    rows = Column(Integer, default=0)
    quality_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    dataset = relationship("Dataset", back_populates="versions")


class QualityRun(Base):
    __tablename__ = "quality_runs"
    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id"), index=True)
    version_id = Column(String, ForeignKey("dataset_versions.id"), index=True)
    status = Column(String, default="COMPLETED")
    score = Column(Float, nullable=True)
    dimensions = Column(Text, default="{}")
    warnings = Column(Text, default="[]")
    duration_ms = Column(Integer, default=0)
    engine_version = Column(String, default="")
    ruleset = Column(String, default="general-v1")
    created_at = Column(DateTime, default=datetime.utcnow)


class QualityIssue(Base):
    __tablename__ = "quality_issues"
    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id"), index=True)
    version_id = Column(String, ForeignKey("dataset_versions.id"), index=True)
    run_id = Column(String, ForeignKey("quality_runs.id"), index=True)
    severity = Column(String, default="LOW")
    category = Column(String, default="VALIDITY")
    column = Column(String, nullable=True)
    row_count = Column(Integer, default=0)
    percentage = Column(Float, default=0.0)
    description = Column(Text, default="")
    examples = Column(Text, default="[]")
    rule = Column(String, default="")
    auto_fix_available = Column(Integer, default=0)
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)


class CleaningOperation(Base):
    __tablename__ = "cleaning_operations"
    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id"), index=True)
    from_version_id = Column(String, nullable=True)
    to_version_id = Column(String, nullable=True)
    operation = Column(String, nullable=False)
    column = Column(String, nullable=True)
    params = Column(Text, default="{}")
    affected_rows = Column(Integer, default=0)
    actor = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)


class ValidationRule(Base):
    __tablename__ = "validation_rules"
    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, ForeignKey("datasets.id"), index=True, nullable=True)
    name = Column(String, nullable=False)
    column = Column(String, nullable=False)
    operator = Column(String, nullable=False)
    value = Column(Text, default="{}")
    severity = Column(String, default="MEDIUM")
    ruleset = Column(String, default="custom")
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String, primary_key=True, default=_uuid)
    dataset_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False)
    detail = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
