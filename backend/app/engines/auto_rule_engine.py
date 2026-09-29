"""AutoML rule generation: profile + issues -> validation DSL rules."""
from typing import Any


def generate_rules(profile: dict, issues: list, max_rules: int = 20) -> list:
    """Deterministic rule synthesis from profile signals. Returns validation DSL rules."""
    rules = []

    def add(column, operator, value, name, severity="MEDIUM"):
        if len(rules) >= max_rules:
            return
        rules.append({"column": column, "operator": operator, "value": value,
                      "name": name, "severity": severity})

    columns = profile.get("columns", []) or []
    by_col_issues: dict = {}
    for iss in issues or []:
        by_col_issues.setdefault(iss.get("column"), []).append(iss)

    for col in columns:
        name = col.get("name")
        if not name:
            continue
        sem = (col.get("semantic_type") or "").lower()
        miss = col.get("missing_rate", 0) or 0
        uniq_rate = col.get("unique_rate", 0) or 0

        if miss > 0.5:
            add(name, "not_null", True, f"auto_completeness_{name}", "HIGH")
        if "email" in sem or "email" in name.lower():
            add(name, "valid_email", True, f"auto_email_{name}", "HIGH")
        if "date" in sem:
            add(name, "valid_date", True, f"auto_date_{name}", "MEDIUM")
        if uniq_rate > 0.95 and (col.get("rows", 0) or 0) > 10:
            add(name, "unique", True, f"auto_unique_{name}", "MEDIUM")
        top = col.get("top_values") or {}
        if isinstance(top, dict) and 1 < len(top) <= 20:
            add(name, "in", list(top.keys()), f"auto_allowed_{name}", "LOW")

    # numeric ranges from stats when present
    for col in columns:
        name = col.get("name")
        stats = col.get("stats") or {}
        lo, hi = stats.get("min"), stats.get("max")
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo < hi:
            add(name, "between", [lo, hi], f"auto_range_{name}", "LOW")

    # issue-driven: any column with validity issues but no rule yet -> generic guard
    covered = {r["column"] for r in rules}
    for col, iss_list in (by_col_issues or {}).items():
        if col and col not in covered and any((i.get("category") or "").upper() == "VALIDITY" for i in iss_list):
            add(col, "not_null", True, f"auto_guard_{col}", "LOW")

    return rules
