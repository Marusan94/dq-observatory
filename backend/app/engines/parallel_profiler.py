"""Parallel profiling engine with chunked processing and sampling strategies."""
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List
from app.engines import type_detector, missing_detector, duplicate_detector, outlier_detector
from app.engines import pattern_detector, category_detector, date_detector, numeric_detector
from app.engines.base import EngineResult
import time


@dataclass
class ProfilingConfig:
    max_workers: int = 4
    chunk_size: int = 50000
    sample_size: Optional[int] = None
    sampling_strategy: str = "systematic"  # systematic, random, stratified
    enable_streaming: bool = False
    streaming_buffer: int = 10000


class SamplingStrategy:
    @staticmethod
    def systematic(df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
        if len(df) <= sample_size:
            return df
        step = len(df) // sample_size
        return df.iloc[::step].head(sample_size)

    @staticmethod
    def random(df: pd.DataFrame, sample_size: int, seed: int = 42) -> pd.DataFrame:
        if len(df) <= sample_size:
            return df
        return df.sample(n=sample_size, random_state=seed)

    @staticmethod
    def stratified(df: pd.DataFrame, sample_size: int, strata_col: str = None, seed: int = 42) -> pd.DataFrame:
        if len(df) <= sample_size:
            return df
        if strata_col and strata_col in df.columns:
            # Proportional stratified sampling
            frac = sample_size / len(df)
            return df.groupby(strata_col, group_keys=False).apply(
                lambda x: x.sample(frac=frac, random_state=seed)
            ).head(sample_size)
        return SamplingStrategy.random(df, sample_size, seed)


class ParallelProfiler:
    """Parallel profiling with chunked processing and intelligent sampling."""

    def __init__(self, config: ProfilingConfig = None):
        self.config = config or ProfilingConfig()

    def _apply_sample(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.config.sample_size and len(df) > self.config.sample_size:
            strategy = self.config.sampling_strategy
            if strategy == "systematic":
                return SamplingStrategy.systematic(df, self.config.sample_size)
            elif strategy == "random":
                return SamplingStrategy.random(df, self.config.sample_size)
            elif strategy == "stratified":
                # Use first categorical column as strata
                cat_cols = [c for c in df.columns if df[c].dtype == 'object']
                strata = cat_cols[0] if cat_cols else None
                return SamplingStrategy.stratified(df, self.config.sample_size, strata)
        return df

    def _profile_chunk(self, chunk: pd.DataFrame, chunk_id: int) -> Dict[str, Any]:
        """Profile a single chunk."""
        # Apply engines to chunk
        engines_out = {}
        
        def run(name, fn, *args):
            try:
                r = fn(*args)
                engines_out[name] = {"metrics": r.metrics, "issues": r.issues, "warnings": r.warnings, "metadata": r.metadata}
            except Exception as e:
                engines_out[name] = {"metrics": {}, "issues": [], "warnings": [str(e)], "metadata": {}}

        # Type detection on first chunk only (for schema)
        if chunk_id == 0:
            run("types", type_detector.analyze, chunk, {})
        
        type_info = engines_out.get("types", {}).get("metrics", {}).get("columns", {})
        
        run("missing", missing_detector.analyze, chunk, {})
        run("duplicates", duplicate_detector.analyze, chunk, {})
        run("patterns", pattern_detector.analyze_patterns, chunk, type_info, {})
        run("categories", category_detector.analyze, chunk, type_info, {})
        run("dates", date_detector.analyze, chunk, type_info, {})
        run("numeric", numeric_detector.analyze, chunk, type_info, {})
        run("outliers", outlier_detector.analyze, chunk, {})

        return {"chunk_id": chunk_id, "rows": len(chunk), "engines": engines_out}

    def _merge_results(self, chunk_results: List[Dict], total_rows: int) -> Dict[str, Any]:
        """Merge chunk profiling results."""
        merged_engines = {}
        all_issues = []
        
        for cr in chunk_results:
            for engine_name, engine_data in cr["engines"].items():
                if engine_name not in merged_engines:
                    merged_engines[engine_name] = {"metrics": {}, "issues": [], "warnings": [], "metadata": {}}
                
                # Merge metrics (sum counts, average rates)
                for key, value in engine_data.get("metrics", {}).items():
                    if key not in merged_engines[engine_name]["metrics"]:
                        merged_engines[engine_name]["metrics"][key] = value
                    elif isinstance(value, dict):
                        # Merge nested dicts
                        for k, v in value.items():
                            if k not in merged_engines[engine_name]["metrics"][key]:
                                merged_engines[engine_name]["metrics"][key][k] = v
                            elif isinstance(v, (int, float)):
                                merged_engines[engine_name]["metrics"][key][k] = (
                                    merged_engines[engine_name]["metrics"][key][k] + v
                                )
                
                # Merge issues (deduplicate by column+rule)
                for issue in engine_data.get("issues", []):
                    all_issues.append(issue)
                
                merged_engines[engine_name]["warnings"].extend(engine_data.get("warnings", []))
        
        # Deduplicate issues
        seen = set()
        unique_issues = []
        for issue in all_issues:
            key = (issue.get("column"), issue.get("rule"), issue.get("category"))
            if key not in seen:
                seen.add(key)
                # Scale row_count proportionally
                issue["row_count"] = int(issue.get("row_count", 0) * total_rows / sum(cr["rows"] for cr in chunk_results))
                unique_issues.append(issue)
        
        # Build column profiles
        columns = []
        if "types" in merged_engines:
            type_info = merged_engines["types"]["metrics"].get("columns", {})
            miss_by_col = merged_engines.get("missing", {}).get("metrics", {}).get("by_column", {})
            # Use first chunk's data for column stats (approximation)
            for col_name, col_info in type_info.items():
                m = miss_by_col.get(col_name, {})
                columns.append({
                    "name": col_name,
                    "physical_type": col_info.get("physical_type"),
                    "semantic_type": col_info.get("semantic_type"),
                    "confidence": col_info.get("confidence"),
                    "missing": m.get("missing", 0),
                    "missing_rate": m.get("missing_rate", 0),
                    "sample_size": sum(cr["rows"] for cr in chunk_results),
                })
        
        return {
            "rows": total_rows,
            "engines": merged_engines,
            "all_issues": unique_issues,
            "warnings": [w for cr in chunk_results for w in cr.get("warnings", [])],
            "columns": columns,
        }

    def profile(self, df: pd.DataFrame, config: Dict = None) -> Dict[str, Any]:
        """Main profiling entry point with parallel processing."""
        t0 = time.time()
        config = config or {}
        
        # Apply sampling if needed
        df = self._apply_sample(df)
        total_rows = len(df)
        
        # Determine chunking
        if self.config.enable_streaming and total_rows > self.config.chunk_size:
            # Process in chunks
            chunks = [df.iloc[i:i + self.config.chunk_size] for i in range(0, total_rows, self.config.chunk_size)]
            
            chunk_results = []
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = {executor.submit(self._profile_chunk, chunk, i): i for i, chunk in enumerate(chunks)}
                for future in as_completed(futures):
                    chunk_results.append(future.result())
            
            # Sort by chunk_id
            chunk_results.sort(key=lambda x: x["chunk_id"])
            
            result = self._merge_results(chunk_results, total_rows)
        else:
            # Single chunk processing
            result = self._profile_chunk(df, 0)
            result = self._merge_results([result], total_rows)
        
        result["duration_ms"] = int((time.time() - t0) * 1000)
        result["processing_mode"] = "streaming" if (self.config.enable_streaming and total_rows > self.config.chunk_size) else "single"
        result["chunks_processed"] = len(chunk_results) if 'chunk_results' in locals() else 1
        
        return result


def profile_dataframe_parallel(df: pd.DataFrame, config: Dict = None) -> Dict[str, Any]:
    """Drop-in replacement for profiling_service.profile_dataframe with parallel processing."""
    profiler = ParallelProfiler()
    return profiler.profile(df, config)