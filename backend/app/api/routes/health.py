from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health check")
def health():
    return {"status": "ok", "service": "dq-observatory", "version": "0.1.0"}


@router.get("/ready", summary="Readiness probe")
def ready():
    return {"ready": True}
