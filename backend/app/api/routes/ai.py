"""AI Assistant API routes."""
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_storage, load_version_df
from app.api.rbac_deps import require_dataset_read, require_schedule_manage
from app.models.entities import DatasetVersion
from app.services.storage_service import StorageService
from app.services.llm_service import LLMService
from app.engines.nl_to_filter import NLToFilterEngine
from app.engines.auto_fix import AutoFixEngine
from app.services.predictive_scoring import predict_score_ml, get_model_status, train_model
from app.services.profiling_service import profile_dataframe
from app.services.quality_service import compute_score
from app.utils.serialize import to_jsonable

router = APIRouter()

# ---- Schemas ----
class AskRequest(BaseModel):
    question: str
    dataset_id: Optional[str] = None
    stream: bool = False


class SuggestFixRequest(BaseModel):
    issue_id: Optional[str] = None
    issue: Optional[dict] = None


class PreviewFixRequest(BaseModel):
    dataset_id: str
    version_id: Optional[str] = None
    operation: str
    column: str
    params: dict = {}


class PredictScoreRequest(BaseModel):
    dataset_id: str
    version_id: Optional[str] = None
    proposed_fixes: List[dict] = []


class TrainModelRequest(BaseModel):
    pass  # Uses historical data


# ---- AI Chat ----
@router.post("/ask", summary="Ask AI about dataset or data quality")
async def ai_ask(
    req: AskRequest,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: str = Depends(require_dataset_read),
):
    """Chat with AI about dataset. Returns JSON or streams tokens."""
    llm = LLMService()
    
    dataset_context = None
    if req.dataset_id:
        # Load dataset schema for context
        vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == req.dataset_id).order_by(
            DatasetVersion.version_number.desc()
        ).all()
        if vers:
            v = vers[0]
            df = load_version_df(storage, req.dataset_id, v.id)
            schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
            sample = {col: df[col].dropna().head(3).tolist() for col in df.columns}
            dataset_context = {
                "dataset_name": v.dataset.name if v.dataset else req.dataset_id,
                "rows": len(df),
                "cols": len(df.columns),
                "schema_json": json.dumps(schema, ensure_ascii=False),
                "sample_json": json.dumps(sample, ensure_ascii=False),
                "profile_summary": "Perfil disponible vía /quality/run",
            }

    if req.stream:
        async def token_generator():
            try:
                async for token in await llm.chat(req.question, dataset_context, stream=True):
                    yield f"data: {json.dumps({'token': token})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(token_generator(), media_type="text/event-stream")

    result = await llm.chat(req.question, dataset_context)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(500, result["error"])
    
    # Log chat
    from app.models.ai import AIChatLog
    log = AIChatLog(
        id=str(uuid.uuid4()),
        dataset_id=req.dataset_id,
        user_role="editor",  # TODO: from auth
        question=req.question,
        answer=result.content if hasattr(result, 'content') else str(result),
        tokens_used=getattr(result, 'tokens_used', 0),
        latency_ms=getattr(result, 'latency_ms', 0),
        model=getattr(result, 'model', 'unknown'),
    )
    db.add(log)
    db.commit()

    return to_jsonable({
        "answer": result.content if hasattr(result, 'content') else str(result),
        "tokens_used": getattr(result, 'tokens_used', 0),
        "latency_ms": getattr(result, 'latency_ms', 0),
        "model": getattr(result, 'model', 'unknown'),
    })


# ---- NL to Filter ----
class NLFilterRequest(BaseModel):
    question: str
    dataset_id: str
    version_id: Optional[str] = None


@router.post("/nl-to-filter", summary="Convert natural language to filter JSON")
async def nl_to_filter(
    req: NLFilterRequest,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: str = Depends(require_dataset_read),
):
    """Convert natural language question to validated filter JSON."""
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == req.dataset_id).order_by(
        DatasetVersion.version_number.desc()
    ).all()
    if not vers:
        raise HTTPException(404, "No versions")
    v = next((x for x in vers if x.id == req.version_id), vers[0]) if req.version_id else vers[0]
    df = load_version_df(storage, req.dataset_id, v.id)

    engine = NLToFilterEngine()
    result = await engine.convert(
        question=req.question,
        df_columns=list(df.columns),
        sample_values={col: df[col].dropna().head(3).tolist() for col in df.columns},
        dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
    )
    return to_jsonable({"filter_json": result})


# ---- Auto-Fix Suggestion ----
@router.post("/suggest-fix", summary="Suggest fix operations for an issue")
async def suggest_fix(
    req: SuggestFixRequest,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: str = Depends(require_dataset_read),
):
    """Get AI-suggested fix operations for a quality issue."""
    issue = None
    if req.issue_id:
        from app.models.entities import QualityIssue
        issue = db.query(QualityIssue).filter(QualityIssue.id == req.issue_id).first()
        if not issue:
            raise HTTPException(404, "Issue not found")
        issue_dict = {
            "id": issue.id,
            "severity": issue.severity,
            "category": issue.category,
            "column": issue.column,
            "description": issue.description,
            "examples": json.loads(issue.examples or "[]")[:5],
            "row_count": issue.row_count,
        }
    elif req.issue:
        issue_dict = req.issue
    else:
        raise HTTPException(400, "Provide issue_id or issue object")

    # Get column type and samples
    col_type = "string"
    col_samples = []
    if issue_dict.get("column"):
        # Load latest version to get samples
        vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == issue.dataset_id).order_by(
            DatasetVersion.version_number.desc()
        ).first()
        if vers:
            df = load_version_df(storage, issue.dataset_id, vers.id)
            if issue_dict["column"] in df.columns:
                col = issue_dict["column"]
                col_samples = df[col].dropna().head(5).tolist()
                col_type = str(df[col].dtype)

    engine = AutoFixEngine()
    suggestions = await engine.suggest(issue_dict, col_type, col_samples)

    # Log suggestion
    from app.models.ai import AIFixSuggestion
    for s in suggestions:
        log = AIFixSuggestion(
            id=str(uuid.uuid4()),
            issue_id=issue_dict.get("id", ""),
            operation=s["operation"],
            column=s.get("column", issue_dict.get("column", "")),
            params=json.dumps(s.get("params", {})),
            confidence=s.get("confidence", 0.5),
            reasoning=s.get("reasoning", ""),
        )
        db.add(log)
    db.commit()

    return to_jsonable({"suggestions": suggestions})


# ---- Preview Fix ----
@router.post("/preview-fix", summary="Preview fix operation on dataset")
async def preview_fix(
    req: PreviewFixRequest,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: str = Depends(require_dataset_read),
):
    """Preview the effect of a cleaning operation."""
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == req.dataset_id).order_by(
        DatasetVersion.version_number.desc()
    ).all()
    if not vers:
        raise HTTPException(404, "No versions")
    v = next((x for x in vers if x.id == req.version_id), vers[0]) if req.version_id else vers[0]
    df = load_version_df(storage, req.dataset_id, v.id)

    engine = AutoFixEngine()
    result = engine.preview_fix(df, req.operation, req.column, req.params)
    return to_jsonable(result)


# ---- Predict Score ----
@router.post("/predict-score", summary="Predict quality score after fixes")
async def predict_score(
    req: PredictScoreRequest,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage),
    _: str = Depends(require_dataset_read),
):
    """Predict quality score after applying proposed fixes."""
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == req.dataset_id).order_by(
        DatasetVersion.version_number.desc()
    ).all()
    if not vers:
        raise HTTPException(404, "No versions")
    v = next((x for x in vers if x.id == req.version_id), vers[0]) if req.version_id else vers[0]
    df = load_version_df(storage, req.dataset_id, v.id)

    profile = profile_dataframe(df)
    current_score = compute_score(profile, len(df))
    issues = profile.get("all_issues", [])

    # Use ML model if available
    try:
        result = predict_score_ml(profile, issues, req.proposed_fixes)
    except Exception:
        # Fallback to LLM
        llm = LLMService()
        result = await llm.predict_score(profile, issues, req.proposed_fixes)

    return to_jsonable({
        "current_score": current_score["overall"],
        "predicted_score": result.get("predicted_score", 0),
        "delta": result.get("delta", 0),
        "confidence_interval": result.get("confidence_interval", [0, 0]),
        "top_features": result.get("top_features", []),
    })


# ---- Model Status & Training ----
@router.get("/model-status", summary="Get predictive model status")
async def model_status(
    _: str = Depends(require_schedule_manage),
):
    """Get predictive model status and metadata."""
    return to_jsonable(get_model_status())


@router.post("/train-model", summary="Train predictive scoring model")
async def train_model_endpoint(
    _: str = Depends(require_schedule_manage),
):
    """Train predictive model from historical quality runs."""
    # This would need historical data - for now return status
    return to_jsonable({"message": "Training endpoint - implement with historical data", "status": "not_implemented"})


# ---- Chat Logs ----
@router.get("/chat-logs", summary="Get AI chat logs for dataset")
async def chat_logs(
    dataset_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: str = Depends(require_dataset_read),
):
    from app.models.ai import AIChatLog
    query = db.query(AIChatLog).order_by(AIChatLog.created_at.desc())
    if dataset_id:
        query = query.filter(AIChatLog.dataset_id == dataset_id)
    logs = query.limit(limit).all()
    return to_jsonable([{
        "id": l.id,
        "dataset_id": l.dataset_id,
        "user_role": l.user_role,
        "question": l.question,
        "answer": l.answer[:200] + "..." if len(l.answer) > 200 else l.answer,
        "tokens_used": l.tokens_used,
        "latency_ms": l.latency_ms,
        "model": l.model,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    } for l in logs])


# ---- Fix Suggestion Logs ----
@router.get("/fix-suggestions", summary="Get AI fix suggestions for issue")
async def fix_suggestions(
    issue_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_dataset_read),
):
    from app.models.ai import AIFixSuggestion
    suggestions = db.query(AIFixSuggestion).filter(AIFixSuggestion.issue_id == issue_id).order_by(
        AIFixSuggestion.created_at.desc()
    ).all()
    return to_jsonable([{
        "id": s.id,
        "operation": s.operation,
        "column": s.column,
        "params": json.loads(s.params or "{}"),
        "preview_json": json.loads(s.preview_json or "{}"),
        "confidence": s.confidence,
        "reasoning": s.reasoning,
        "accepted": s.accepted,
        "applied_at": s.applied_at.isoformat() if s.applied_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    } for s in suggestions])


@router.patch("/fix-suggestions/{suggestion_id}/accept", summary="Mark fix suggestion as accepted")
async def accept_fix_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_schedule_manage),
):
    from app.models.ai import AIFixSuggestion
    s = db.query(AIFixSuggestion).filter(AIFixSuggestion.id == suggestion_id).first()
    if not s:
        raise HTTPException(404, "Suggestion not found")
    s.accepted = 1
    s.applied_at = datetime.utcnow()
    db.commit()
    return to_jsonable({"accepted": True})