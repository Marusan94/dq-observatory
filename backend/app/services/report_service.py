import json
from datetime import datetime


def build_report(dataset: dict, version: dict, profile: dict, score: dict, issues: list,
                 transformations: list, validation: list, engine_version: str, ruleset: str) -> dict:
    return {
        "tool": "DQ Observatory", "engine_version": engine_version, "ruleset_version": ruleset,
        "generated_at": datetime.utcnow().isoformat(),
        "dataset": dataset, "version": version,
        "summary": {"rows": profile.get("rows"), "columns": profile.get("columns"),
                    "quality_score": score.get("overall"), "dimensions": score.get("dimensions"),
                    "issues": len(issues)},
        "quality_score": score, "profile": profile,
        "top_issues": sorted(issues, key=lambda x: ({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(x.get("severity"), 5)),)[:20],
        "transformations": transformations, "validation": validation,
        "recommendations": [],
        "methodology": "Deterministic engines: type/missing/duplicate/pattern/category/date/numeric/outlier. Score = weighted mean (completeness 25, validity 25, consistency 20, uniqueness 15, integrity 15).",
    }


def to_html(report: dict) -> str:
    s = report["quality_score"]["overall"]
    rows = "".join(f"<tr><td>{i.get('severity')}</td><td>{i.get('column')}</td><td>{i.get('description','')[:120]}</td><td>{i.get('row_count')}</td></tr>" for i in report["top_issues"][:20])
    return f"""<html><head><meta charset='utf-8'><title>DQ Report - {report['dataset'].get('name')}</title>
<style>body{{font-family:Arial;background:#0b0b0c;color:#e8e8e8}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #333;padding:6px;font-size:12px}}.card{{background:#141416;border:1px solid #26262a;border-radius:10px;padding:16px;margin:12px 0}}</style>
</head><body><h1>Data Quality Report — {report['dataset'].get('name')}</h1>
<div class='card'><h2>Quality Score: {s}/100</h2><p>{report['quality_score'].get('note','')}</p>
<p>Dimensions: {json.dumps(report['quality_score']['dimensions'])}</p></div>
<div class='card'><h2>Top issues ({len(report['top_issues'])})</h2><table><tr><th>Severity</th><th>Column</th><th>Description</th><th>Rows</th></tr>{rows}</table></div>
<div class='card'><h2>Methodology</h2><p>{report['methodology']}</p></div>
</body></html>"""
