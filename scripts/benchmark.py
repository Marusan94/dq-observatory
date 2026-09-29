"""Simple benchmark: profiling+quality timing vs rows. Run: python scripts/benchmark.py"""
import time
import pandas as pd
from pathlib import Path
from app.services.profiling_service import profile_dataframe
from app.services.quality_service import compute_score

demo = Path(__file__).resolve().parents[1] / "data" / "demo" / "customers_sales.csv"
df_full = pd.read_csv(demo, low_memory=False)
for n in (1000, 10000, len(df_full)):
    df = df_full.head(n)
    t0 = time.time()
    prof = profile_dataframe(df, {})
    score = compute_score(prof, len(df))
    dt = time.time() - t0
    mem = round(float(df.memory_usage(deep=True).sum()) / 1e6, 2)
    print(f"rows={len(df)} cols={len(df.columns)} time={dt:.2f}s mem={mem}MB score={score['overall']} issues={len(prof['all_issues'])} warnings={len(prof['warnings'])}")
