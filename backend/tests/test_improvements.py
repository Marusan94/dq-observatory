import os
os.environ["DATABASE_URL"] = "sqlite:///./storage/test_dq2.db"
os.environ["STORAGE_PATH"] = "./storage_test2"
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app
from app.models.base import Base, engine


def _client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_improvements():
    c = _client()
    with c:
        df = pd.DataFrame({"customer_id": ["C1", "C2"], "email": ["a@x.com", "bad"], "age": [25, 30]})
        r = c.post("/api/v1/datasets", files={"file": ("t.csv", df.to_csv(index=False).encode(), "text/csv")})
        assert r.status_code == 200, r.text
        ds = r.json()["id"]
        q = c.post(f"/api/v1/datasets/{ds}/quality/run", json={})
        assert q.status_code == 200, q.text
        # trend
        t = c.get(f"/api/v1/datasets/{ds}/quality/trend")
        assert t.status_code == 200 and len(t.json()["versions"]) >= 1
        # column detail
        col = c.get(f"/api/v1/datasets/{ds}/columns/email")
        assert col.status_code == 200 and col.json()["column"]["name"] == "email"
        assert c.get(f"/api/v1/datasets/{ds}/columns/nope").status_code == 404
        # demo seed
        d = c.post("/api/v1/datasets/demo/seed")
        assert d.status_code == 200, d.text
        assert d.json()["issues_count"] > 5
