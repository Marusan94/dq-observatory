"""RBAC models for multi-tenancy and access control."""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.models.base import Base


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(str, Enum):
    # Dataset permissions
    DATASET_CREATE = "dataset:create"
    DATASET_READ = "dataset:read"
    DATASET_UPDATE = "dataset:update"
    DATASET_DELETE = "dataset:delete"
    DATASET_EXPORT = "dataset:export"
    
    # Quality permissions
    QUALITY_RUN = "quality:run"
    QUALITY_READ = "quality:read"
    
    # Cleaning permissions
    CLEANING_PREVIEW = "cleaning:preview"
    CLEANING_APPLY = "cleaning:apply"
    
    # Validation permissions
    VALIDATION_RUN = "validation:run"
    VALIDATION_READ = "validation:read"
    VALIDATION_RULE_CREATE = "validation:rule:create"
    
    # Settings permissions
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    
    # Admin permissions
    USER_MANAGE = "user:manage"
    ROLE_MANAGE = "role:manage"
    WEBHOOK_MANAGE = "webhook:manage"
    SCHEDULE_MANAGE = "schedule:manage"
    
    # System
    SYSTEM_ADMIN = "system:admin"


ROLE_PERMISSIONS = {
    Role.OWNER: [p.value for p in Permission],
    Role.ADMIN: [
        Permission.DATASET_CREATE.value, Permission.DATASET_READ.value,
        Permission.DATASET_UPDATE.value, Permission.DATASET_DELETE.value,
        Permission.DATASET_EXPORT.value, Permission.QUALITY_RUN.value,
        Permission.QUALITY_READ.value, Permission.CLEANING_PREVIEW.value,
        Permission.CLEANING_APPLY.value, Permission.VALIDATION_RUN.value,
        Permission.VALIDATION_READ.value, Permission.VALIDATION_RULE_CREATE.value,
        Permission.SETTINGS_READ.value, Permission.SETTINGS_WRITE.value,
        Permission.USER_MANAGE.value, Permission.ROLE_MANAGE.value,
        Permission.WEBHOOK_MANAGE.value, Permission.SCHEDULE_MANAGE.value,
    ],
    Role.EDITOR: [
        Permission.DATASET_CREATE.value, Permission.DATASET_READ.value,
        Permission.DATASET_UPDATE.value, Permission.DATASET_EXPORT.value,
        Permission.QUALITY_RUN.value, Permission.QUALITY_READ.value,
        Permission.CLEANING_PREVIEW.value, Permission.CLEANING_APPLY.value,
        Permission.VALIDATION_RUN.value, Permission.VALIDATION_READ.value,
        Permission.VALIDATION_RULE_CREATE.value, Permission.SETTINGS_READ.value,
    ],
    Role.VIEWER: [
        Permission.DATASET_READ.value, Permission.DATASET_EXPORT.value,
        Permission.QUALITY_READ.value, Permission.VALIDATION_READ.value,
        Permission.SETTINGS_READ.value,
    ],
}


# Association tables
workspace_members = Table(
    "workspace_members",
    Base.metadata,
    Column("workspace_id", String, ForeignKey("workspaces.id"), primary_key=True),
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
    Column("role", String, default=Role.VIEWER.value),
    Column("joined_at", DateTime, default=datetime.utcnow),
)

dataset_permissions = Table(
    "dataset_permissions",
    Base.metadata,
    Column("dataset_id", String, ForeignKey("datasets.id"), primary_key=True),
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
    Column("permission", String, primary_key=True),
    Column("granted_at", DateTime, default=datetime.utcnow),
    Column("granted_by", String, ForeignKey("users.id")),
)


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # For future auth
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    owned_workspaces = relationship("Workspace", back_populates="owner", foreign_keys="Workspace.owner_id")
    memberships = relationship("Workspace", secondary=workspace_members, back_populates="members")
    # RBAC explícito vía tabla dataset_permissions con queries directas
    # (sin relationship ORM para evitar ambigüedad user_id/granted_by)


class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    settings = Column(Text, default="{}")  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="owned_workspaces", foreign_keys=[owner_id])
    members = relationship("User", secondary=workspace_members, back_populates="memberships")
    datasets = relationship("Dataset", back_populates="workspace", foreign_keys="Dataset.workspace_id")


# Update existing Dataset model to add workspace and permissions
# (This would be merged into models/entities.py in practice)
# class Dataset(Base):
#     ...
#     workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)
#     workspace = relationship("Workspace", back_populates="datasets")
#     explicit_permissions = relationship("User", secondary=dataset_permissions, back_populates="dataset_permissions")


def has_permission(user: User, permission: Permission, dataset_id: str = None, workspace_id: str = None) -> bool:
    """Check if user has a specific permission."""
    if user.is_superuser:
        return True
    
    if not user.is_active:
        return False
    
    # Check workspace role
    if workspace_id:
        for membership in user.memberships:
            if membership.id == workspace_id:
                role_perms = ROLE_PERMISSIONS.get(Role(membership.role), [])
                if permission.value in role_perms:
                    return True
    
    # Check explicit dataset permissions
    if dataset_id:
        # This would require a query in practice
        pass
    
    return False


def get_user_role_in_workspace(user: User, workspace_id: str) -> str:
    """Get user's role in a workspace."""
    for membership in user.memberships:
        if membership.id == workspace_id:
            return membership.role
    return None