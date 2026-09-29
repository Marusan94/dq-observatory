from pydantic import BaseModel
from typing import Any


class ErrorModel(BaseModel):
    code: str
    message: str
    details: dict = {}
    request_id: str = ""


class DatasetOut(BaseModel):
    id: str
    name: str
    rows: int = 0
    columns: int = 0
    file_format: str = ""
    quality_score: float | None = None


class CleaningRequest(BaseModel):
    operation: str
    column: str | None = None
    params: dict[str, Any] = {}
    preview_only: bool = False


class ValidationRuleIn(BaseModel):
    name: str
    column: str
    operator: str
    value: Any = None
    severity: str = "MEDIUM"
