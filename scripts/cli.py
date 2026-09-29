"""Enhanced CLI tools for DQ Observatory."""
import click
import json
import sys
import os
from pathlib import Path
import pandas as pd
from app.services.ingestion_service import ingest_upload
from app.services.profiling_service import profile_dataframe
from app.services.quality_service import compute_score, recommendations
from app.services.export_service import to_csv_bytes, to_xlsx_bytes, build_zip
from app.services.report_service import build_report, to_html
from app.services.validation_service import evaluate
from app.utils.file_validation import validate_extension
from app.utils.hashing import sha256_file


@click.group()
def cli():
    """DQ Observatory CLI - Data Quality & Profiling Platform"""
    pass


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--output', '-o', default='.', help='Output directory')
@click.option('--format', '-f', type=click.Choice(['csv', 'xlsx', 'json', 'zip', 'all']), default='all')
@click.option('--ruleset', '-r', default='general-v1', help='Quality ruleset')
@click.option('--sample', type=int, help='Sample size for large files')
@click.option('--parallel/--no-parallel', default=True, help='Use parallel processing')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def analyze(file_path, output, format, ruleset, sample, parallel, verbose):
    """Analyze a CSV/XLSX/JSON file and generate quality report."""
    click.echo(f"Analyzing {file_path}...")
    
    try:
        ext = validate_extension(file_path)
        file_hash = sha256_file(file_path)
        
        if verbose:
            click.echo(f"  Format: {ext}")
            click.echo(f"  Hash: {file_hash[:16]}...")
        
        # Load data
        if ext == '.csv':
            df = pd.read_csv(file_path, low_memory=False, nrows=sample)
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(file_path, nrows=sample)
        elif ext == '.json':
            df = pd.read_json(file_path)
            if not isinstance(df, pd.DataFrame):
                df = pd.json_normalize(df)
        else:
            raise ValueError(f"Unsupported format: {ext}")
        
        if verbose:
            click.echo(f"  Rows: {len(df)}, Columns: {len(df.columns)}")
        
        # Profile
        config = {"sample_size": sample} if sample else {}
        profile = profile_dataframe(df, config)
        
        if verbose:
            click.echo(f"  Missing cells: {profile['missing_cells']}")
            click.echo(f"  Duplicates: {profile['exact_duplicates']}")
            click.echo(f"  Issues found: {len(profile['all_issues'])}")
        
        # Quality score
        score = compute_score(profile, len(df))
        recs = recommendations(profile, score)
        
        click.echo(f"\n  Quality Score: {score['overall']}/100")
        for dim, val in score['dimensions'].items():
            click.echo(f"    {dim}: {val}")
        
        # Generate outputs
        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(file_path).stem
        
        formats = [format] if format != 'all' else ['csv', 'xlsx', 'json', 'zip']
        
        for fmt in formats:
            if fmt == 'csv':
                out_path = out_dir / f"{base_name}_cleaned.csv"
                out_path.write_bytes(df.to_csv(index=False).encode('utf-8'))
                click.echo(f"  CSV: {out_path}")
            elif fmt == 'xlsx':
                out_path = out_dir / f"{base_name}_cleaned.xlsx"
                from app.services.export_service import to_xlsx_bytes
                out_path.write_bytes(to_xlsx_bytes(df))
                click.echo(f"  XLSX: {out_path}")
            elif fmt == 'json':
                out_path = out_dir / f"{base_name}_report.json"
                report = build_report(
                    {"name": base_name, "rows": len(df), "columns": len(df.columns)},
                    {"id": "cli", "label": "CLI Analysis", "rows": len(df)},
                    profile, score, profile['all_issues'], [], [],
                    "cli-1.0", ruleset
                )
                out_path.write_text(json.dumps(report, indent=2, default=str))
                click.echo(f"  JSON: {out_path}")
            elif fmt == 'zip':
                out_path = out_dir / f"{base_name}_bundle.zip"
                report = build_report(
                    {"name": base_name, "rows": len(df), "columns": len(df.columns)},
                    {"id": "cli", "label": "CLI Analysis", "rows": len(df)},
                    profile, score, profile['all_issues'], [], [],
                    "cli-1.0", ruleset
                )
                from app.services.export_service import build_zip
                out_path.write_bytes(build_zip(df, report, profile['all_issues'], [], 
                                               {"columns": profile['columns']}))
                click.echo(f"  ZIP: {out_path}")
        
        if recs:
            click.echo("\n  Recommendations:")
            for r in recs:
                click.echo(f"    - {r}")
        
        click.echo(f"\n✓ Analysis complete. Outputs in {out_dir}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('file1', type=click.Path(exists=True))
@click.argument('file2', type=click.Path(exists=True))
@click.option('--output', '-o', default='.', help='Output directory')
def drift(file1, file2, output):
    """Detect data drift between two dataset versions."""
    click.echo(f"Analyzing drift between {file1} and {file2}...")
    
    try:
        # Load both datasets
        ext1 = validate_extension(file1)
        ext2 = validate_extension(file2)
        
        def load_df(path, ext):
            if ext == '.csv':
                return pd.read_csv(path, low_memory=False)
            elif ext in ('.xlsx', '.xls'):
                return pd.read_excel(path)
            elif ext == '.json':
                df = pd.read_json(path)
                return df if isinstance(df, pd.DataFrame) else pd.json_normalize(df)
        
        df1 = load_df(file1, ext1)
        df2 = load_df(file2, ext2)
        
        click.echo(f"  Dataset 1: {len(df1)} rows, {len(df1.columns)} cols")
        click.echo(f"  Dataset 2: {len(df2)} rows, {len(df2.columns)} cols")
        
        # Import drift detector
        from app.engines.drift_detector import analyze_drift
        from app.engines.type_detector import analyze as type_analyze
        
        # Get type info
        type1 = type_analyze(df1, {}).metrics.get("columns", {})
        type2 = type_analyze(df2, {}).metrics.get("columns", {})
        
        # Run drift analysis
        result = analyze_drift(df1, df2, type1, type2)
        
        click.echo(f"\n  Drift Analysis Results:")
        click.echo(f"    Total drifts: {result.metrics['total_drifts']}")
        click.echo(f"    Columns affected: {result.metrics['columns_affected']}")
        click.echo(f"    By type: {result.metrics['by_type']}")
        click.echo(f"    By severity: {result.metrics['by_severity']}")
        
        # Show details
        for issue in result.issues[:10]:
            click.echo(f"    [{issue['severity']}] {issue['column']}: {issue['description']}")
        
        # Save detailed report
        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "drift_report.json"
        
        report = {
            "dataset1": file1,
            "dataset2": file2,
            "drift_analysis": {
                "metrics": result.metrics,
                "issues": result.issues,
                "metadata": result.metadata,
            }
        }
        out_path.write_text(json.dumps(report, indent=2, default=str))
        click.echo(f"\n  Report saved: {out_path}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--host', default='0.0.0.0')
@click.option('--port', default=8000)
def serve(host, port):
    """Start the API server."""
    import uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--rules', help='JSON rules file')
@click.option('--output', '-o', default='.')
def validate(file_path, rules, output):
    """Validate dataset against rules."""
    click.echo(f"Validating {file_path}...")
    
    try:
        ext = validate_extension(file_path)
        if ext == '.csv':
            df = pd.read_csv(file_path, low_memory=False)
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(file_path)
        elif ext == '.json':
            df = pd.read_json(file_path)
            if not isinstance(df, pd.DataFrame):
                df = pd.json_normalize(df)
        
        if rules:
            rule_list = json.loads(Path(rules).read_text())
        else:
            rule_list = [
                {"name": f"{c} not null", "column": c, "operator": "not_null", "value": None, "severity": "LOW"}
                for c in df.columns[:20]
            ]
        
        results = evaluate(df, rule_list)
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = len(results) - passed
        
        click.echo(f"  Rules: {len(results)}, Passed: {passed}, Failed: {failed}")
        
        for r in results:
            if r["status"] == "FAIL":
                click.echo(f"  ✗ {r['name']}: {r['failed']} failures")
        
        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "validation_results.json"
        out_path.write_text(json.dumps({"results": results, "passed": passed, "failed": failed}, indent=2))
        click.echo(f"\n  Results: {out_path}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--count', '-c', default=5000)
@click.option('--output', '-o', default='data/demo/customers_sales.csv')
def generate_demo(count, output):
    """Generate demo dataset with realistic chaos."""
    click.echo(f"Generating {count} rows of demo data...")
    os.system(f"python scripts/generate_demo_data.py")
    click.echo(f"✓ Generated: {output}")


if __name__ == '__main__':
    cli()