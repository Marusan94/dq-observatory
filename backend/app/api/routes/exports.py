import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_storage, load_version_df
from app.api.routes.reports import _assemble
from app.services.export_service import to_csv_bytes, to_xlsx_bytes, build_zip
from app.services.storage_service import StorageService

router = APIRouter()


@router.get("/{dataset_id}/export", summary="Export cleaned dataset / report / bundle")
def export(dataset_id: str, format: str = "csv", db: Session = Depends(get_db),
           storage: StorageService = Depends(get_storage)):
    report, df, profile = _assemble(db, storage, dataset_id)
    fmt = format.lower()
    if fmt == "csv":
        return Response(to_csv_bytes(df), media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={dataset_id}-cleaned.csv"})
    if fmt == "xlsx":
        return Response(to_xlsx_bytes(df),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f"attachment; filename={dataset_id}-cleaned.xlsx"})
    if fmt == "json":
        return Response(json.dumps(report, indent=2, default=str), media_type="application/json",
                        headers={"Content-Disposition": f"attachment; filename={dataset_id}-report.json"})
    if fmt == "zip":
        issues = report.get("top_issues", [])
        data = build_zip(df, report, issues, report.get("transformations", []),
                         {"columns": profile.get("columns", [])})
        return Response(data, media_type="application/zip",
                        headers={"Content-Disposition": f"attachment; filename={dataset_id}-bundle.zip"})
    raise HTTPException(400, "format must be csv|xlsx|json|zip")
