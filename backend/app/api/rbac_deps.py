"""Basic header-based RBAC enforcement (JWT/OAuth-ready placeholder).

Clients send `X-Role: owner|admin|editor|viewer` (default: viewer).
Mutations on jobs/webhooks require manage permissions; reads require
dataset/quality read permissions that every role has. Replace get_role
with JWT claims when auth is integrated.
"""
from fastapi import Request, HTTPException
from app.models.rbac import Role, Permission, ROLE_PERMISSIONS


def get_role(request: Request) -> Role:
    raw = (request.headers.get("X-Role") or "viewer").lower()
    try:
        return Role(raw)
    except ValueError:
        raise HTTPException(400, f"Invalid X-Role '{raw}'. Use owner|admin|editor|viewer.")


def require_permission(permission: Permission):
    def _check(request: Request) -> str:
        role = get_role(request)
        if permission.value not in ROLE_PERMISSIONS[role]:
            raise HTTPException(
                403, f"Role '{role.value}' lacks permission '{permission.value}'.")
        return role.value
    return _check


require_dataset_read = require_permission(Permission.DATASET_READ)
require_schedule_manage = require_permission(Permission.SCHEDULE_MANAGE)
require_webhook_manage = require_permission(Permission.WEBHOOK_MANAGE)
