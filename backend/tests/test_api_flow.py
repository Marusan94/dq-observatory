import os
os.environ["DATABASE_URL"] = "sqlite:///./storage/test_dq.db"
os.environ["STORAGE_PATH"] = "./storage_test"
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app
from app.models.base import Base, engine


def _client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_full_flow():
    client = _client()
    with client:
        df = pd.DataFrame({"customer_id": ["C1", "C2", "C2"], "email": ["A@X.COM ", "bad", "a@x.com"], "age": [25, -5, 30]})
        buf = df.to_csv(index=False).encode()
        r = client.post("/api/v1/datasets", files={"file": ("t.csv", buf, "text/csv")})
        assert r.status_code == 200, r.text
        ds = r.json()["id"]
        assert client.get(f"/api/v1/datasets/{ds}").status_code == 200
        assert client.post(f"/api/v1/datasets/{ds}/profile", json={}).status_code == 200
        qr = client.post(f"/api/v1/datasets/{ds}/quality/run", json={})
        assert qr.status_code == 200, qr.text
        q = qr.json()
        assert q["score"]["overall"] > 0
        assert q["issues_count"] > 0
        iss = client.get(f"/api/v1/datasets/{ds}/issues", params={"severity": "HIGH"}).json()
        assert "total" in iss
        pv = client.post(f"/api/v1/datasets/{ds}/clean",
                         json={"operation": "remove_exact_duplicates", "preview_only": True}).json()
        assert "preview_data" in pv
        ap = client.post(f"/api/v1/datasets/{ds}/clean",
                         json={"operation": "remove_exact_duplicates"}).json()
        assert ap["applied"] is True
        assert client.post(f"/api/v1/datasets/{ds}/validate", json={}).status_code == 200
        assert client.get(f"/api/v1/datasets/{ds}/report").status_code == 200
        assert client.get(f"/api/v1/datasets/{ds}/export", params={"format": "csv"}).status_code == 200
        assert client.get(f"/api/v1/datasets/{ds}/export", params={"format": "zip"}).status_code == 200
        assert client.get("/health").status_code == 200
