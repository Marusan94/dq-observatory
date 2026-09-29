"""Transparent quality score. Weights: completeness 25, validity 25, consistency 20, uniqueness 15, integrity 15."""
WEIGHTS = {"completeness": 25, "validity": 25, "consistency": 20, "uniqueness": 15, "integrity": 15}


def compute_score(profile: dict, total_rows: int) -> dict:
    miss_pct = profile.get("missing_percentage", 0)
    completeness = max(0, 100 - miss_pct * 2)  # 50% missing -> 0

    issues = profile.get("all_issues", [])
    def rate(cat_list):
        rows = sum(i.get("row_count", 0) for i in issues if i.get("category") in cat_list)
        return min(1.0, rows / max(1, total_rows * max(1, len(profile.get("columns", []))))) if total_rows else 0

    validity_rows = sum(i.get("row_count", 0) for i in issues if i.get("category") == "VALIDITY")
    consistency_rows = sum(i.get("row_count", 0) for i in issues if i.get("category") in ("CONSISTENCY", "FORMAT", "TYPE", "SEMANTIC"))
    validity = max(0, 100 - (validity_rows / max(1, total_rows)) * 100)
    consistency = max(0, 100 - (consistency_rows / max(1, total_rows)) * 100)

    dup_rate = profile.get("engines", {}).get("duplicates", {}).get("metrics", {}).get("exact_duplicate_rate", 0)
    uniqueness = max(0, 100 - dup_rate * 100 * 3)

    integrity_rows = sum(i.get("row_count", 0) for i in issues if i.get("category") == "INTEGRITY")
    integrity = max(0, 100 - (integrity_rows / max(1, total_rows)) * 100)

    dims = {"completeness": round(completeness, 1), "validity": round(validity, 1),
            "consistency": round(consistency, 1), "uniqueness": round(uniqueness, 1),
            "integrity": round(integrity, 1)}
    total = round(sum(dims[k] * WEIGHTS[k] / 100 for k in WEIGHTS), 1)
    contributions = {k: {"score": dims[k], "weight": WEIGHTS[k],
                         "contribution": round(dims[k] * WEIGHTS[k] / 100, 2)} for k in WEIGHTS}
    return {"overall": total, "dimensions": dims, "weights": WEIGHTS,
            "contributions": contributions,
            "note": "Indicador calculado segun las reglas configuradas. No es una verdad absoluta."}


QUALITY_PROFILES = {
    "general": {"rules": ["NOT_NULL", "VALID_EMAIL", "VALID_PHONE", "VALID_DATE", "UNIQUE"]},
    "crm": {"rules": ["IDENTIFIER_COMPLETENESS", "VALID_EMAIL", "VALID_PHONE", "VALID_DATE", "CATEGORY_ALLOWED_VALUES"]},
    "sales": {"rules": ["IDENTIFIER_COMPLETENESS", "NUMERIC_RANGE", "VALID_DATE", "NOT_NULL"]},
    "education": {"rules": ["IDENTIFIER_COMPLETENESS", "NUMERIC_RANGE", "NOT_NULL", "CATEGORY_ALLOWED_VALUES"]},
}


def recommendations(profile: dict, score: dict) -> list[str]:
    recs = []
    if score["dimensions"]["completeness"] < 70:
        recs.append("Review whether columns with >30% missing should be retained.")
    dup = profile.get("exact_duplicates", 0)
    rows = profile.get("rows", 1)
    if rows and dup / rows > 0.05:
        recs.append("Review duplicate records before downstream use.")
    for c in profile.get("columns", [])[:50]:
        if c.get("missing_rate", 0) > 0.3:
            recs.append(f"Column '{c['name']}' is {c['missing_rate']*100:.0f}% missing — confirm source collection.")
            break
    if not recs:
        recs.append("Dataset passes configured rules. Schedule periodic re-scans to detect drift.")
    return recs
