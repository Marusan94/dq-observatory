import time
import pandas as pd
from app.engines import type_detector, missing_detector, duplicate_detector, outlier_detector
from app.engines import pattern_detector, category_detector, date_detector, numeric_detector
from app.engines.parallel_profiler import ParallelProfiler, ProfilingConfig


def profile_dataframe(df: pd.DataFrame, config: dict | None = None) -> dict:
    config = config or {}
    t0 = time.time()
    warnings: list[str] = []
    engines_out = {}

    # Use ParallelProfiler for large datasets (>10000 rows) to avoid overhead on small data
    use_parallel = len(df) > 10000
    parallel = ParallelProfiler(ProfilingConfig(chunk_size=5000, sampling_strategy="systematic")) if use_parallel else None

    def run(name, fn, *args):
        try:
            if use_parallel and name in ("missing", "duplicates", "numeric", "outliers", "patterns", "categories", "dates"):
                # These engines support parallel execution
                if name == "missing":
                    r = parallel.run_missing(config)
                elif name == "duplicates":
                    r = parallel.run_duplicates(config)
                elif name == "numeric":
                    r = parallel.run_numeric(engines_out["types"]["metrics"].get("columns", {}), config)
                elif name == "outliers":
                    r = parallel.run_outliers(config)
                elif name == "patterns":
                    r = parallel.run_patterns(engines_out["types"]["metrics"].get("columns", {}), config)
                elif name == "categories":
                    r = parallel.run_categories(engines_out["types"]["metrics"].get("columns", {}), config)
                elif name == "dates":
                    r = parallel.run_dates(engines_out["types"]["metrics"].get("columns", {}), config)
                else:
                    r = fn(*args)
            else:
                r = fn(*args)
            engines_out[name] = {"metrics": r.metrics, "issues": r.issues, "warnings": r.warnings, "metadata": r.metadata}
        except Exception as e:  # partial failure — never kill whole analysis
            warnings.append(f"{name} unavailable: {e}")
            engines_out[name] = {"metrics": {}, "issues": [], "warnings": [str(e)], "metadata": {}}

    run("types", type_detector.analyze, df, config)
    type_info = engines_out["types"]["metrics"].get("columns", {})
    run("missing", missing_detector.analyze, df, config)
    run("duplicates", duplicate_detector.analyze, df, config)
    run("patterns", pattern_detector.analyze_patterns, df, type_info, config)
    run("categories", category_detector.analyze, df, type_info, config)
    run("dates", date_detector.analyze, df, type_info, config)
    run("numeric", numeric_detector.analyze, df, type_info, config)
    run("outliers", outlier_detector.analyze, df, config)

    # column profiles
    columns = []
    miss_by_col = engines_out["missing"]["metrics"].get("by_column", {})
    for col in df.columns:
        s = df[col]
        ti = type_info.get(str(col), {})
        m = miss_by_col.get(str(col), {})
        uniq = int(s.nunique(dropna=True))
        columns.append({
            "name": str(col), "physical_type": ti.get("physical_type"),
            "semantic_type": ti.get("semantic_type"), "confidence": ti.get("confidence"),
            "rows": len(df), "non_null": int(s.notna().sum()),
            "missing": m.get("missing", int(s.isna().sum())),
            "missing_rate": m.get("missing_rate", 0),
            "unique": uniq, "unique_rate": round(uniq / max(1, len(df)), 4),
            "top_values": s.value_counts(dropna=True).head(5).to_dict(),
            "constant": uniq <= 1,
            "high_cardinality": (uniq / max(1, len(df))) > 0.9 and len(df) > 50,
            "potential_identifier": (uniq / max(1, len(df))) > 0.95,
        })

    # column name quality
    name_issues = []
    seen = set()
    for col in df.columns:
        c = str(col)
        if c.strip() == "" or c != c.strip() or " " in c or c.lower() != c and c.upper() != c:
            pass
        if c in seen:
            name_issues.append(c)
        seen.add(c)

    all_issues = []
    for e in engines_out.values():
        all_issues.extend(e["issues"])

    duration = int((time.time() - t0) * 1000)
    return {
        "rows": len(df), "columns": len(df.columns),
        "memory_mb": round(float(df.memory_usage(deep=True).sum()) / 1e6, 2),
        "missing_cells": engines_out["missing"]["metrics"].get("missing_cells", 0),
        "missing_percentage": engines_out["missing"]["metrics"].get("missing_percentage", 0),
        "exact_duplicates": engines_out["duplicates"]["metrics"].get("exact_duplicates", 0),
        "columns": columns,
        "engines": engines_out,
        "all_issues": all_issues,
        "warnings": warnings,
        "duration_ms": duration,
        "pii": engines_out["patterns"]["metadata"].get("pii", []),
    }
