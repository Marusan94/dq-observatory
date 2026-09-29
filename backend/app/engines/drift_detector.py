"""Data drift detection between dataset versions."""
import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from app.engines.base import EngineResult


@dataclass
class DriftResult:
    column: str
    drift_type: str  # distribution, schema, statistical
    severity: str    # LOW, MEDIUM, HIGH, CRITICAL
    score: float     # 0-1 drift score
    details: Dict[str, Any]
    recommendation: str


def _psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """Population Stability Index for numerical drift."""
    try:
        # Create buckets based on expected percentiles
        percentiles = np.linspace(0, 100, buckets + 1)
        bins = np.percentile(expected, percentiles)
        bins = np.unique(bins)
        if len(bins) < 2:
            return 0.0
        
        expected_hist, _ = np.histogram(expected, bins=bins)
        actual_hist, _ = np.histogram(actual, bins=bins)
        
        expected_pct = expected_hist / len(expected)
        actual_pct = actual_hist / len(actual)
        
        # Avoid division by zero
        expected_pct = np.where(expected_pct == 0, 0.0001, expected_pct)
        actual_pct = np.where(actual_pct == 0, 0.0001, actual_pct)
        
        psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        return float(psi)
    except Exception:
        return 0.0


def _kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """KL divergence for categorical drift."""
    p = p / p.sum() if p.sum() > 0 else p
    q = q / q.sum() if q.sum() > 0 else q
    p = np.where(p == 0, 0.0001, p)
    q = np.where(q == 0, 0.0001, q)
    return float(np.sum(p * np.log(p / q)))


def _schema_drift(df_old: pd.DataFrame, df_new: pd.DataFrame) -> List[DriftResult]:
    """Detect schema changes."""
    results = []
    old_cols = set(df_old.columns)
    new_cols = set(df_new.columns)
    
    # Added columns
    for col in new_cols - old_cols:
        results.append(DriftResult(
            column=col,
            drift_type="schema",
            severity="HIGH",
            score=1.0,
            details={"change": "column_added", "dtype": str(df_new[col].dtype)},
            recommendation=f"New column '{col}' added. Review data source changes."
        ))
    
    # Removed columns
    for col in old_cols - new_cols:
        results.append(DriftResult(
            column=col,
            drift_type="schema",
            severity="CRITICAL",
            score=1.0,
            details={"change": "column_removed"},
            recommendation=f"Column '{col}' removed. Downstream processes may break."
        ))
    
    # Type changes
    for col in old_cols & new_cols:
        old_dtype = str(df_old[col].dtype)
        new_dtype = str(df_new[col].dtype)
        if old_dtype != new_dtype:
            results.append(DriftResult(
                column=col,
                drift_type="schema",
                severity="HIGH",
                score=0.8,
                details={"change": "dtype_changed", "old": old_dtype, "new": new_dtype},
                recommendation=f"Column '{col}' dtype changed from {old_dtype} to {new_dtype}. Check parsing logic."
            ))
    
    return results


def _distribution_drift(df_old: pd.DataFrame, df_new: pd.DataFrame, 
                        type_info: Dict = None) -> List[DriftResult]:
    """Detect statistical distribution drift."""
    results = []
    common_cols = set(df_old.columns) & set(df_new.columns)
    
    for col in common_cols:
        old_series = df_old[col].dropna()
        new_series = df_new[col].dropna()
        
        if len(old_series) < 30 or len(new_series) < 30:
            continue
        
        old_dtype = str(df_old[col].dtype)
        new_dtype = str(df_new[col].dtype)
        
        # Numerical drift
        if pd.api.types.is_numeric_dtype(old_series) and pd.api.types.is_numeric_dtype(new_series):
            old_vals = pd.to_numeric(old_series, errors='coerce').dropna().values
            new_vals = pd.to_numeric(new_series, errors='coerce').dropna().values
            
            if len(old_vals) > 30 and len(new_vals) > 30:
                # KS test
                ks_stat, ks_p = stats.ks_2samp(old_vals, new_vals)
                # PSI
                psi = _psi(old_vals, new_vals)
                # Mean/std shift
                mean_shift = abs(np.mean(new_vals) - np.mean(old_vals)) / (np.std(old_vals) + 1e-10)
                std_ratio = np.std(new_vals) / (np.std(old_vals) + 1e-10)
                
                # Determine severity
                severity = "LOW"
                if ks_p < 0.01 or psi > 0.2:
                    severity = "HIGH"
                elif ks_p < 0.05 or psi > 0.1:
                    severity = "MEDIUM"
                
                score = max(psi, 1 - ks_p, min(mean_shift, 1.0))
                
                if severity != "LOW" or score > 0.1:
                    results.append(DriftResult(
                        column=col,
                        drift_type="distribution",
                        severity=severity,
                        score=min(score, 1.0),
                        details={
                            "ks_statistic": float(ks_stat),
                            "ks_p_value": float(ks_p),
                            "psi": psi,
                            "mean_shift": float(mean_shift),
                            "std_ratio": float(std_ratio),
                            "old_mean": float(np.mean(old_vals)),
                            "new_mean": float(np.mean(new_vals)),
                        },
                        recommendation=f"Numerical distribution drift detected in '{col}'. Consider retraining models or investigating data source changes."
                    ))
        
        # Categorical drift
        elif old_dtype == 'object' or pd.api.types.is_categorical_dtype(old_series):
            old_counts = old_series.value_counts()
            new_counts = new_series.value_counts()
            
            # Align categories
            all_cats = set(old_counts.index) | set(new_counts.index)
            old_p = np.array([old_counts.get(c, 0) for c in all_cats])
            new_p = np.array([new_counts.get(c, 0) for c in all_cats])
            
            if old_p.sum() > 0 and new_p.sum() > 0:
                kl = _kl_divergence(old_p / old_p.sum(), new_p / new_p.sum())
                
                # Chi-square test
                try:
                    contingency = np.array([old_p, new_p])
                    chi2, chi2_p, _, _ = stats.chi2_contingency(contingency)
                except Exception:
                    chi2, chi2_p = 0, 1
                
                severity = "LOW"
                if chi2_p < 0.01 or kl > 0.5:
                    severity = "HIGH"
                elif chi2_p < 0.05 or kl > 0.2:
                    severity = "MEDIUM"
                
                score = max(min(kl, 1.0), 1 - chi2_p)
                
                # Find new categories
                new_cats = set(new_counts.index) - set(old_counts.index)
                lost_cats = set(old_counts.index) - set(new_counts.index)
                
                if severity != "LOW" or score > 0.1 or new_cats or lost_cats:
                    results.append(DriftResult(
                        column=col,
                        drift_type="distribution",
                        severity=severity,
                        score=min(score, 1.0),
                        details={
                            "kl_divergence": kl,
                            "chi2_p_value": float(chi2_p) if 'chi2_p' in locals() else 1.0,
                            "new_categories": list(new_cats),
                            "lost_categories": list(lost_cats),
                            "top_old": old_counts.head(5).to_dict(),
                            "top_new": new_counts.head(5).to_dict(),
                        },
                        recommendation=f"Categorical distribution drift in '{col}'. New categories: {list(new_cats)[:5] if new_cats else 'none'}."
                    ))
    
    return results


def analyze_drift(df_old: pd.DataFrame, df_new: pd.DataFrame, 
                  type_info_old: Dict = None, type_info_new: Dict = None) -> EngineResult:
    """Comprehensive drift analysis between two dataset versions."""
    all_results = []
    
    # Schema drift
    all_results.extend(_schema_drift(df_old, df_new))
    
    # Distribution drift
    all_results.extend(_distribution_drift(df_old, df_new, type_info_old))
    
    # Convert to EngineResult format
    issues = []
    for r in all_results:
        issues.append({
            "severity": r.severity,
            "category": "DRIFT",
            "column": r.column,
            "row_count": 0,  # Drift affects entire column
            "percentage": round(r.score * 100, 2),
            "description": f"Data drift detected: {r.drift_type} ({r.severity})",
            "examples": [],
            "rule": f"DRIFT_{r.drift_type.upper()}",
            "auto_fix_available": False,
            "drift_details": r.details,
            "recommendation": r.recommendation,
        })
    
    # Summary metrics
    metrics = {
        "total_drifts": len(issues),
        "by_type": {},
        "by_severity": {},
        "columns_affected": len(set(r.column for r in all_results)),
    }
    
    for r in all_results:
        metrics["by_type"][r.drift_type] = metrics["by_type"].get(r.drift_type, 0) + 1
        metrics["by_severity"][r.severity] = metrics["by_severity"].get(r.severity, 0) + 1
    
    return EngineResult(
        engine="drift_detector",
        metrics=metrics,
        issues=issues,
        warnings=[],
        metadata={"columns_compared": list(set(df_old.columns) & set(df_new.columns))}
    )