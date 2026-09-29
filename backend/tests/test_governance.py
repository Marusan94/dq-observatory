import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./storage/test_dq.db")
os.environ.setdefault("STORAGE_PATH", "./storage_test")
import pandas as pd
from fastapi.testclient import TestClient
import app.models.entities  # noqa: F401
import app.services.scheduler_service  # noqa: F401
import app.models.rbac  # noqa: F401
import app.models.contracts  # noqa: F401
from app.main import app
from app.models.base import Base, engine


def _client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def _upload(c):
    df = pd.DataFrame({"id": [1, 2, 3], "email": ["a@x.com", "bad", "c@x.com"], "age": [25, 30, 22]})
    r = c.post("/api/v1/datasets", files={"file": ("t.csv", df.to_csv(index=False).encode(), "text/csv")})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_contract_crud_and_check():
    c = _client()
    with c:
        ds = _upload(c)
        body = {"dataset_id": ds, "name": "c1",
                "schema": {"id": {"physical_type": "int64", "required": True},
                           "email": {"physical_type": "object", "required": True},
                           "ghost": {"physical_type": "object", "required": True}},
                "rules": [], "sla": {}}
        r = c.post("/api/v1/contracts", json=body, headers={"X-Role": "editor"})
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        # viewer cannot create
        r2 = c.post("/api/v1/contracts", json=body, headers={"X-Role": "viewer"})
        assert r2.status_code == 403
        # list + get
        assert any(x["id"] == cid for x in c.get("/api/v1/contracts").json())
        assert c.get(f"/api/v1/contracts/{cid}").json()["name"] == "c1"
        # check: ghost column missing -> violation, passed False
        chk = c.post(f"/api/v1/contracts/{cid}/check").json()
        assert chk["passed"] is False
        assert any(v["column"] == "ghost" for v in chk["violations"])
        # checks history
        hist = c.get(f"/api/v1/contracts/{cid}/checks").json()
        assert len(hist) >= 1
        # update bumps version
        u = c.patch(f"/api/v1/contracts/{cid}", json={"status": "DEPRECATED"},
                    headers={"X-Role": "editor"}).json()
        assert u["version"] == 2 and u["status"] == "DEPRECATED"


def test_auto_rules_creates_validation_rules():
    c = _client()
    with c:
        ds = _upload(c)
        # viewer forbidden
        r = c.post(f"/api/v1/{ds}/auto-rules", headers={"X-Role": "viewer"})
        assert r.status_code == 403
        r = c.post(f"/api/v1/{ds}/auto-rules?max_rules=10", headers={"X-Role": "editor"}).json()
        assert r["created"] >= 1
        assert all(set(x) >= {"name", "column", "operator", "value"} for x in r["rules"])
        ops = {x["operator"] for x in r["rules"]}
        assert ops <= {"not_null", "unique", "between", "gte", "lte", "eq", "in", "regex", "valid_email", "valid_date"}


def test_lineage_graph_and_websocket():
    c = _client()
    with c:
        ds = _upload(c)
        g = c.get(f"/api/v1/datasets/{ds}/lineage/graph").json()
        assert g["dataset_id"] == ds
        assert len(g["nodes"]) >= 1
        assert isinstance(g["edges"], list)
        assert c.get("/api/v1/datasets/nope/lineage/graph").status_code == 404
        # websocket snapshot
        with c.websocket_connect(f"/api/v1/stream/quality/{ds}") as ws:
            import json as _json
            msg = _json.loads(ws.receive_text())
            assert msg["type"] == "snapshot" and msg["dataset_id"] == ds
            assert len(msg["versions"]) >= 1
