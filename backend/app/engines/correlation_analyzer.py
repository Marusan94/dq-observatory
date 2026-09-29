"""Advanced correlation analysis and statistical profiling."""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from app.engines.base import EngineResult


@dataclass
class CorrelationResult:
    column_x: str
    column_y: str
    method: str  # pearson, spearman, kendall, cramers_v, theil_u
    correlation: float
    p_value: float
    significance: str  # significant, not_significant
    interpretation: str


def _cramers_v(confusion_matrix: np.ndarray) -> float:
    """Cramér's V for categorical-categorical association."""
    chi2, _, _, _ = stats.chi2_contingency(confusion_matrix)
    n = confusion_matrix.sum()
    min_dim = min(confusion_matrix.shape) - 1
    if n == 0 or min_dim == 0:
        return 0.0
    return float(np.sqrt(chi2 / (n * min_dim)))


def _theil_u(x: pd.Series, y: pd.Series) -> float:
    """Theil's U (uncertainty coefficient) for categorical-categorical."""
    # H(Y|X) / H(Y) - asymmetry
    from scipy.stats import entropy
    
    # Joint distribution
    joint = pd.crosstab(x, y, normalize=True)
    px = joint.sum(axis=1)
    py = joint.sum(axis=0)
    
    # H(Y)
    hy = entropy(py)
    if hy == 0:
        return 0.0
    
    # H(Y|X)
    hyx = 0
    for xi, px_val in px.items():
        if px_val > 0:
            cond = joint.loc[xi] / px_val
            hyx += px_val * entropy(cond)
    
    return float((hy - hyx) / hy) if hy > 0 else 0.0


def _correlation_ratio(continuous: pd.Series, categorical: pd.Series) -> float:
    """Correlation ratio (eta) for continuous-categorical."""
    from scipy.stats import f_oneway
    
    groups = [continuous[categorical == cat].dropna().values 
              for cat in categorical.unique() if len(continuous[categorical == cat].dropna()) > 1]
    
    if len(groups) < 2:
        return 0.0
    
    try:
        f_stat, p_val = f_oneway(*groups)
        if f_stat > 0:
            return float(np.sqrt(f_stat / (f_stat + len(categorical.dropna()) - 1)))
    except Exception:
        pass
    return 0.0


def analyze_correlations(df: pd.DataFrame, type_info: Dict = None, 
                         config: Dict = None) -> EngineResult:
    """Comprehensive correlation analysis between all column pairs."""
    config = config or {}
    min_correlation = config.get("min_correlation", 0.3)
    max_pairs = config.get("max_pairs", 100)
    
    results = []
    correlations = []
    
    # Get column types
    type_map = {}
    if type_info:
        type_map = {k: v.get("semantic_type", "unknown") 
                    for k, v in type_info.get("columns", {}).items()}
    else:
        for col in df.columns:
            type_map[col] = df[col].dtype.name
    
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in df.columns if df[c].dtype == 'object' or 
                        pd.api.types.is_categorical_dtype(df[c])]
    
    pair_count = 0
    
    # Numeric-Numeric: Pearson, Spearman, Kendall
    for i, col_x in enumerate(numeric_cols):
        for col_y in numeric_cols[i+1:]:
            if pair_count >= max_pairs:
                break
            
            x = pd.to_numeric(df[col_x], errors='coerce').dropna()
            y = pd.to_numeric(df[col_y], errors='coerce').dropna()
            
            # Align indices
            common_idx = x.index.intersection(y.index)
            if len(common_idx) < 30:
                continue
            
            x = x.loc[common_idx]
            y = y.loc[common_idx]
            
            # Pearson
            pearson_r, pearson_p = stats.pearsonr(x, y)
            # Spearman
            spearman_r, spearman_p = stats.spearmanr(x, y)
            # Kendall
            kendall_r, kendall_p = stats.kendalltau(x, y)
            
            for method, corr, p_val in [
                ("pearson", pearson_r, pearson_p),
                ("spearman", spearman_r, spearman_p),
                ("kendall", kendall_r, kendall_p)
            ]:
                if abs(corr) >= min_correlation and p_val < 0.05:
                    corr_result = CorrelationResult(
                        column_x=col_x,
                        column_y=col_y,
                        method=method,
                        correlation=float(corr),
                        p_value=float(p_val),
                        significance="significant",
                        interpretation=f"Strong {method} correlation ({corr:.3f})"
                    )
                    correlations.append({
                        "column_x": corr_result.column_x,
                        "column_y": corr_result.column_y,
                        "method": corr_result.method,
                        "correlation": corr_result.correlation,
                        "p_value": corr_result.p_value,
                        "significance": corr_result.significance,
                        "interpretation": corr_result.interpretation,
                    })
                    pair_count += 1
    
    # Categorical-Categorical: Cramér's V, Theil's U
    for i, col_x in enumerate(categorical_cols):
        for col_y in categorical_cols[i+1:]:
            if pair_count >= max_pairs:
                break
            
            # Only if cardinality is reasonable
            if df[col_x].nunique() > 50 or df[col_y].nunique() > 50:
                continue
            
            confusion = pd.crosstab(df[col_x], df[col_y])
            if confusion.shape[0] < 2 or confusion.shape[1] < 2:
                continue
            
            v = _cramers_v(confusion.values)
            u = _theil_u(df[col_x], df[col_y])
            
            if v >= min_correlation:
                correlations.append({
                    "column_x": col_x,
                    "column_y": col_y,
                    "method": "cramers_v",
                    "correlation": float(v),
                    "p_value": 0.0,
                    "significance": "significant" if v >= min_correlation else "not_significant",
                    "interpretation": f"Cramér's V = {v:.3f} (moderate to strong association)"
                })
                pair_count += 1
            
            if u >= min_correlation:
                correlations.append({
                    "column_x": col_x,
                    "column_y": col_y,
                    "method": "theil_u",
                    "correlation": float(u),
                    "p_value": 0.0,
                    "significance": "significant" if u >= min_correlation else "not_significant",
                    "interpretation": f"Theil's U = {u:.3f} (predictive power)"
                })
                pair_count += 1
    
    # Continuous-Categorical: Correlation ratio (eta)
    for cont_col in numeric_cols:
        for cat_col in categorical_cols:
            if pair_count >= max_pairs:
                break
            
            if df[cat_col].nunique() > 20:
                continue
            
            x = pd.to_numeric(df[cont_col], errors='coerce')
            y = df[cat_col]
            
            common = x.notna() & y.notna()
            if common.sum() < 30:
                continue
            
            eta = _correlation_ratio(x[common], y[common])
            
            if eta >= min_correlation:
                correlations.append({
                    "column_x": cont_col,
                    "column_y": cat_col,
                    "method": "correlation_ratio",
                    "correlation": float(eta),
                    "p_value": 0.0,
                    "significance": "significant",
                    "interpretation": f"Eta = {eta:.3f} ({cont_col} varies by {cat_col})"
                })
                pair_count += 1
    
    # Sort by absolute correlation
    correlations.sort(key=lambda x: -abs(x["correlation"]))
    correlations = correlations[:max_pairs]
    
    # Find highly correlated groups (for feature selection)
    high_corr_pairs = [c for c in correlations if abs(c["correlation"]) > 0.9]
    
    issues = []
    for c in high_corr_pairs:
        issues.append({
            "severity": "MEDIUM",
            "category": "CORRELATION",
            "column": f"{c['column_x']} <-> {c['column_y']}",
            "row_count": 0,
            "percentage": round(abs(c["correlation"]) * 100, 2),
            "description": f"Very high {c['method']} correlation ({c['correlation']:.3f}) between {c['column_x']} and {c['column_y']}",
            "examples": [],
            "rule": f"HIGH_{c['method'].upper()}",
            "auto_fix_available": False,
            "details": c,
        })
    
    metrics = {
        "total_pairs_analyzed": pair_count,
        "significant_correlations": len(correlations),
        "high_correlations_90": len(high_corr_pairs),
        "methods_used": list(set(c["method"] for c in correlations)),
    }
    
    return EngineResult(
        engine="correlation_analyzer",
        metrics=metrics,
        issues=issues,
        warnings=[],
        metadata={"correlations": correlations[:50]}  # Top 50
    )