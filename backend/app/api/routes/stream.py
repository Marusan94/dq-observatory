"""Real-time quality push over WebSocket."""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.base import SessionLocal
from app.models.entities import DatasetVersion

router = APIRouter()


def _snapshot(dataset_id: str) -> dict:
    db = SessionLocal()
    try:
        vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(
            DatasetVersion.version_number.desc()).all()
        if not vers:
            return {"type": "snapshot", "dataset_id": dataset_id, "versions": []}
        return {"type": "snapshot", "dataset_id": dataset_id,
                "versions": [{"id": v.id, "n": v.version_number, "label": v.label,
                              "rows": v.rows, "score": v.quality_score,
                              "at": v.created_at.isoformat() if v.created_at else None} for v in vers[:10]]}
    finally:
        db.close()


@router.websocket("/stream/quality/{dataset_id}")
async def quality_stream(ws: WebSocket, dataset_id: str):
    await ws.accept()
    try:
        await ws.send_text(json.dumps(_snapshot(dataset_id), default=str))
        while True:
            try:
                # client ping keeps alive; push fresh snapshot on any message
                await asyncio.wait_for(ws.receive_text(), timeout=10.0)
                await ws.send_text(json.dumps(_snapshot(dataset_id), default=str))
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "heartbeat"}, default=str))
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await ws.close()
        except Exception:
            pass
