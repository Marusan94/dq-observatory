import os
import tempfile
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_storage
from app.core.config import get_settings
from app.models.entities import Dataset, DatasetVersion, AuditLog
from app.services.ingestion_service import ingest_upload
from app.services.storage_service import StorageService
from app.utils.dataframe_utils import paginate_df
from app.api.deps import load_version_df
from app.utils.serialize import to_jsonable

router = APIRouter()
settings = get_settings()


@router.post("/demo/seed", summary="One-click demo: load customers_sales.csv + run quality")
def seed_demo(db: Session = Depends(get_db), storage: StorageService = Depends(get_storage)):
    import pandas as pd
    from pathlib import Path
    demo = Path(__file__).resolve().parents[4] / "data" / "demo" / "customers_sales.csv"
    if not demo.exists():
        raise HTTPException(404, "Demo file missing. Run scripts/generate_demo_data.py first.")
    df = pd.read_csv(demo, low_memory=False)
    ds = Dataset(id=str(uuid.uuid4()), name="customers_sales (demo)",
                 original_filename="customers_sales.csv", file_hash="demo",
                 file_size=int(demo.stat().st_size), file_format="csv",
                 rows=len(df), columns=len(df.columns))
    db.add(ds)
    db.flush()
    from app.api.deps import save_version_df
    ver_id = str(uuid.uuid4())
    path = save_version_df(storage, ds.id, ver_id, df)
    ver = DatasetVersion(id=ver_id, dataset_id=ds.id, version_number=1,
                         label="v1 Original (demo)", storage_path=path, rows=len(df))
    db.add(ver)
    db.add(AuditLog(dataset_id=ds.id, action="demo_seeded", detail=f'{{"rows": {len(df)}}}'))
    db.commit()
    # run quality inline so the demo tells its story immediately
    from app.services.profiling_service import profile_dataframe
    from app.services.quality_service import compute_score
    import json as _json
    from app.models.entities import QualityRun, QualityIssue
    profile = profile_dataframe(df, {})
    score = compute_score(profile, len(df))
    run = QualityRun(id=str(uuid.uuid4()), dataset_id=ds.id, version_id=ver_id,
                     status="COMPLETED", score=score["overall"],
                     dimensions=_json.dumps(score), warnings=_json.dumps(profile.get("warnings", [])),
                     duration_ms=0, engine_version=settings.engine_version, ruleset=settings.ruleset_version)
    db.add(run)
    db.flush()
    for iss in profile.get("all_issues", []):
        db.add(QualityIssue(id=str(uuid.uuid4()), dataset_id=ds.id, version_id=ver_id, run_id=run.id,
                            severity=iss.get("severity", "LOW"), category=iss.get("category", "VALIDITY"),
                            column=str(iss.get("column")) if iss.get("column") else None,
                            row_count=int(iss.get("row_count", 0)), percentage=float(iss.get("percentage", 0)),
                            description=iss.get("description", "")[:2000],
                            examples=_json.dumps(iss.get("examples", [])[:5], default=str),
                            rule=iss.get("rule", ""),
                            auto_fix_available=1 if iss.get("auto_fix_available") else 0, status="OPEN"))
    ver.quality_score = score["overall"]
    db.commit()
    return to_jsonable({"id": ds.id, "version_id": ver_id, "rows": len(df),
                        "score": score["overall"], "issues_count": len(profile.get("all_issues", []))})


@router.post("", summary="Upload CSV/XLSX/JSON dataset")
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db),
                         storage: StorageService = Depends(get_storage)):
    if not file.filename:
        raise HTTPException(400, "Missing filename")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="_" + file.filename)
    try:
        content = await file.read()
        if len(content) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(413, f"File exceeds {settings.max_upload_size_mb} MB")
        tmp.write(content)
        tmp.close()
        try:
            ing = ingest_upload(tmp.name, file.filename, settings.max_upload_size_mb)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception:
            raise HTTPException(422, "Unable to parse file. Try exporting the worksheet as CSV.")
        ds = Dataset(id=str(uuid.uuid4()), name=ing["safe_name"].rsplit(".", 1)[0],
                     original_filename=file.filename, file_hash=ing["hash"],
                     file_size=len(content), file_format=ing["ext"].lstrip("."),
                     rows=ing["rows"], columns=len(ing["df"].columns))
        db.add(ds)
        db.flush()
        ver_id = str(uuid.uuid4())
        from app.api.deps import save_version_df
        path = save_version_df(storage, ds.id, ver_id, ing["df"])
        ver = DatasetVersion(id=ver_id, dataset_id=ds.id, version_number=1,
                             label="v1 Original", storage_path=path, rows=ing["rows"])
        db.add(ver)
        db.add(AuditLog(dataset_id=ds.id, action="dataset_uploaded",
                        detail=f'{{"rows": {ing["rows"]}, "hash": "{ing["hash"][:12]}"}}'))
        db.commit()
        return {"id": ds.id, "name": ds.name, "rows": ds.rows, "columns": ds.columns,
                "file_format": ds.file_format, "version_id": ver_id, "file_hash": ing["hash"]}
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


@router.get("", summary="List datasets")
def list_datasets(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db)):
    q = db.query(Dataset).order_by(Dataset.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"page": page, "page_size": page_size, "total": total,
            "items": [{"id": d.id, "name": d.name, "rows": d.rows, "columns": d.columns,
                       "file_format": d.file_format, "created_at": d.created_at} for d in items]}


@router.get("/{dataset_id}", summary="Get dataset + versions")
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(404, "Dataset not found")
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number).all()
    return {"id": ds.id, "name": ds.name, "original_filename": ds.original_filename,
            "rows": ds.rows, "columns": ds.columns, "file_format": ds.file_format,
            "file_hash": ds.file_hash,
            "versions": [{"id": v.id, "version_number": v.version_number, "label": v.label,
                          "rows": v.rows, "quality_score": v.quality_score,
                          "created_at": v.created_at} for v in vers]}


@router.delete("/{dataset_id}", summary="Delete dataset")
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(404, "Dataset not found")
    db.delete(ds)
    db.commit()
    return {"deleted": dataset_id}


@router.get("/{dataset_id}/preview", summary="Paginated data preview (never full dump)")
def preview(dataset_id: str, version_id: str | None = None, page: int = Query(1, ge=1),
            page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db),
            storage: StorageService = Depends(get_storage)):
    vers = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number.desc()).all()
    if not vers:
        raise HTTPException(404, "No versions")
    v = next((x for x in vers if x.id == version_id), vers[0]) if version_id else vers[0]
    df = load_version_df(storage, dataset_id, v.id)
    data = paginate_df(df, page, page_size)
    data["columns"] = [str(c) for c in df.columns]
    data["version_id"] = v.id
    return to_jsonable(data)
