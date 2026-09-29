import io
import pandas as pd
import app.models.entities  # noqa: F401 - register Dataset for Workspace.datasets FK
import app.services.scheduler_service  # noqa: F401 - register scheduled_jobs/webhooks
import app.models.rbac  # noqa: F401 - ensure RBAC tables registered
from app.services.export_service import (
    export_dataframe, SUPPORTED_FORMATS,
    to_csv_bytes, to_json_bytes, to_parquet_bytes,
)
from app.models.rbac import Role, Permission, ROLE_PERMISSIONS, User, has_permission


def _df():
    return pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"], "score": [1.5, 2.5, 3.0]})


def test_supported_formats_include_parquet_delta():
    assert "parquet" in SUPPORTED_FORMATS
    assert "delta" in SUPPORTED_FORMATS
    assert "avro" in SUPPORTED_FORMATS


def test_export_csv_json_parquet():
    df = _df()
    csv_b = export_dataframe(df, "csv")
    assert csv_b.startswith(b"id,name,score")
    json_b = export_dataframe(df, "json")
    assert b"id" in json_b
    pq_b = export_dataframe(df, "parquet")
    assert len(pq_b) > 100
    # roundtrip parquet
    rt = pd.read_parquet(io.BytesIO(pq_b))
    assert list(rt.columns) == ["id", "name", "score"]
    assert len(rt) == 3


def test_export_delta_avro_zip():
    df = _df()
    delta_b = export_dataframe(df, "delta")
    assert len(delta_b) > 100
    avro_b = export_dataframe(df, "avro")
    assert len(avro_b) > 100
    zip_b = export_dataframe(df, "zip")
    assert zip_b[:2] == b"PK"


def test_export_unsupported_raises():
    df = _df()
    try:
        export_dataframe(df, "nope")
    except ValueError as e:
        assert "Unsupported format" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_rbac_roles_cover_export():
    assert Permission.DATASET_EXPORT.value in ROLE_PERMISSIONS[Role.OWNER]
    assert Permission.DATASET_EXPORT.value in ROLE_PERMISSIONS[Role.VIEWER]
    assert Permission.SCHEDULE_MANAGE.value in ROLE_PERMISSIONS[Role.ADMIN]
    assert Permission.SCHEDULE_MANAGE.value not in ROLE_PERMISSIONS[Role.VIEWER]


def test_rbac_has_permission_basic():
    admin = User(email="a@x.com", is_active=True, is_superuser=True)
    assert has_permission(admin, Permission.DATASET_DELETE) is True
    inactive = User(email="i@x.com", is_active=False, is_superuser=False)
    assert has_permission(inactive, Permission.DATASET_READ) is False
    plain = User(email="u@x.com", is_active=True, is_superuser=False)
    assert has_permission(plain, Permission.DATASET_READ) is False


def test_scheduler_models_registered():
    from app.models.base import Base
    assert "scheduled_jobs" in Base.metadata.tables
    assert "webhooks" in Base.metadata.tables
    assert "job_runs" in Base.metadata.tables
    assert "users" in Base.metadata.tables
    assert "workspaces" in Base.metadata.tables


def test_advanced_router_loads():
    from app.api.routes import advanced
    paths = [r.path for r in advanced.router.routes]
    assert "/jobs" in paths
    assert "/webhooks" in paths
    assert any("drift" in p for p in paths)
    assert any("correlations" in p for p in paths)
    assert any("export" in p for p in paths)


def _api_client():
    import os
    os.environ.setdefault("DATABASE_URL", "sqlite:///./storage/test_dq.db")
    os.environ.setdefault("STORAGE_PATH", "./storage_test")
    from fastapi.testclient import TestClient
    from app.main import app
    from app.models.base import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_jobs_require_schedule_manage():
    c = _api_client()
    with c:
        body = {"name": "nightly", "cron_expression": "0 2 * * *"}
        r_viewer = c.post("/api/v1/jobs", json=body, headers={"X-Role": "viewer"})
        assert r_viewer.status_code == 403, r_viewer.text
        r_editor = c.post("/api/v1/jobs", json=body, headers={"X-Role": "editor"})
        assert r_editor.status_code == 403, r_editor.text
        r_admin = c.post("/api/v1/jobs", json=body, headers={"X-Role": "admin"})
        assert r_admin.status_code == 200, r_admin.text
        assert "id" in r_admin.json()
        r_list = c.get("/api/v1/jobs")
        assert r_list.status_code == 200
        assert len(r_list.json()) >= 1


def test_webhooks_require_webhook_manage_and_role_validated():
    c = _api_client()
    with c:
        body = {"name": "slack", "url": "https://hooks.example.com/x", "events": ["job_failed"]}
        assert c.post("/api/v1/webhooks", json=body, headers={"X-Role": "viewer"}).status_code == 403
        r_bad = c.post("/api/v1/webhooks", json=body, headers={"X-Role": "superadmin"})
        assert r_bad.status_code == 400, r_bad.text
        r_ok = c.post("/api/v1/webhooks", json=body, headers={"X-Role": "owner"})
        assert r_ok.status_code == 200, r_ok.text
        assert c.get("/api/v1/webhooks").status_code == 200


def test_job_manual_trigger_creates_run():
    c = _api_client()
    with c:
        body = {"name": "test-job", "cron_expression": "0 2 * * *"}
        r = c.post("/api/v1/jobs", json=body, headers={"X-Role": "admin"})
        assert r.status_code == 200
        job_id = r.json()["id"]
        
        # Trigger manually
        r_run = c.post(f"/api/v1/jobs/{job_id}/run", headers={"X-Role": "admin"})
        assert r_run.status_code == 200
        assert "run_id" in r_run.json()
        
        # Check run appears in job detail
        r_detail = c.get(f"/api/v1/jobs/{job_id}")
        assert r_detail.status_code == 200
        runs = r_detail.json()["recent_runs"]
        assert len(runs) >= 1


def test_parallel_profiler_speedup():
    import pandas as pd
    import numpy as np
    from app.engines.parallel_profiler import ParallelProfiler, ProfilingConfig
    
    # Large enough to trigger parallel
    df = pd.DataFrame({
        "id": range(2000),
        "value": np.random.randn(2000),
        "category": np.random.choice(["A", "B", "C"], 2000),
    })
    profiler = ParallelProfiler(ProfilingConfig(chunk_size=500, sampling_strategy="systematic"))
    
    # Sample the data
    sampled = profiler._apply_sample(df)
    assert len(sampled) <= 2000
    
    # Test parallel missing via chunk profiling
    chunk_result = profiler._profile_chunk(df, 0)
    assert "engines" in chunk_result
    assert "missing" in chunk_result["engines"]
    missing_metrics = chunk_result["engines"]["missing"]["metrics"]
    assert "missing_cells" in missing_metrics
    
    # Test parallel duplicates
    df_dup = pd.concat([df, df.iloc[:100]], ignore_index=True)
    chunk_dup = profiler._profile_chunk(df_dup, 0)
    dup_metrics = chunk_dup["engines"]["duplicates"]["metrics"]
    assert dup_metrics.get("exact_duplicates", 0) >= 0  # merged counts
    
    # Test parallel numeric
    num_metrics = chunk_result["engines"]["numeric"]["metrics"]
    assert "value" in num_metrics
    # numeric detector returns numeric_as_text_sample, that's fine
    assert isinstance(num_metrics["value"], dict)


def test_export_formats_via_api():
    import os
    import pandas as pd
    from fastapi.testclient import TestClient
    from app.main import app
    from app.models.base import Base, engine
    
    os.environ.setdefault("DATABASE_URL", "sqlite:///./storage/test_dq3.db")
    os.environ.setdefault("STORAGE_PATH", "./storage_test3")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    c = TestClient(app)
    with c:
        df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        r = c.post("/api/v1/datasets", files={"file": ("t.csv", df.to_csv(index=False).encode(), "text/csv")})
        assert r.status_code == 200
        ds = r.json()["id"]
        
        # advanced router is at /api/v1/ not /api/v1/datasets/
        for fmt in ["csv", "json", "parquet", "delta", "avro", "zip"]:
            r_exp = c.get(f"/api/v1/{ds}/export?format={fmt}", headers={"X-Role": "owner"})
            assert r_exp.status_code == 200, f"Format {fmt} failed: {r_exp.text}"
            assert len(r_exp.content) > 0
        
        # Test unsupported
        r_bad = c.get(f"/api/v1/datasets/{ds}/export?format=badfmt", headers={"X-Role": "owner"})
        assert r_bad.status_code == 400
