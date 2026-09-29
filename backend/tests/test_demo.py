import pandas as pd
from pathlib import Path
from app.services.profiling_service import profile_dataframe
from app.services.quality_service import compute_score

DEMO = Path(__file__).resolve().parents[2] / "data" / "demo" / "customers_sales.csv"


def test_demo_ranges():
    assert DEMO.exists(), "run scripts/generate_demo_data.py first"
    df = pd.read_csv(DEMO, low_memory=False)
    assert 4900 <= len(df) <= 5500
    assert len(df.columns) == 17
    dups = int(df.duplicated().sum())
    assert 100 <= dups <= 300, f"dups={dups}"
    bad = int((~df["email"].astype(str).str.contains("@", na=False)).sum())
    assert 20 <= bad <= 250, f"bad emails={bad}"
    assert int(df.isna().sum().sum()) > 100
    prof = profile_dataframe(df.head(2000), {})
    score = compute_score(prof, 2000)["overall"]
    assert 0 < score < 100  # real score, never magic 100/0
    assert len(prof["all_issues"]) > 5
