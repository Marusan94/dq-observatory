import io
import json
import zipfile
import pandas as pd
from app.utils.file_validation import sanitize_excel_value


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    safe = df.map(sanitize_excel_value)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        safe.to_excel(w, index=False, sheet_name="cleaned")
    return buf.getvalue()


def to_json_bytes(df: pd.DataFrame, orient: str = "records") -> bytes:
    return df.to_json(orient=orient, date_format="iso").encode("utf-8")


def to_parquet_bytes(df: pd.DataFrame) -> bytes:
    """Export to Parquet format (efficient columnar)."""
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, compression="snappy")
    return buf.getvalue()


def to_delta_bytes(df: pd.DataFrame) -> bytes:
    """Export to Delta Lake format (requires deltalake package)."""
    try:
        from deltalake import write_deltalake
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = os.path.join(tmpdir, "delta_table")
            write_deltalake(table_path, df, mode="overwrite")
            
            # Zip the delta table
            import zipfile
            import io
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(table_path):
                    for file in files:
                        filepath = os.path.join(root, file)
                        arcname = os.path.relpath(filepath, tmpdir)
                        z.write(filepath, arcname)
            return buf.getvalue()
    except ImportError:
        raise ImportError("Delta Lake export requires 'deltalake' package. Install with: pip install deltalake")


def to_avro_bytes(df: pd.DataFrame) -> bytes:
    """Export to Avro format (requires fastavro)."""
    try:
        import fastavro
        import io
        
        # Convert to records
        records = df.astype(object).where(pd.notnull(df), None).to_dict('records')
        
        # Infer schema
        schema = {
            "type": "record",
            "name": "DataRecord",
            "fields": []
        }
        
        for col, dtype in df.dtypes.items():
            if pd.api.types.is_integer_dtype(dtype):
                avro_type = ["null", "long"]
            elif pd.api.types.is_float_dtype(dtype):
                avro_type = ["null", "double"]
            elif pd.api.types.is_bool_dtype(dtype):
                avro_type = ["null", "boolean"]
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                avro_type = ["null", {"type": "long", "logicalType": "timestamp-millis"}]
            else:
                avro_type = ["null", "string"]
            
            schema["fields"].append({"name": str(col), "type": avro_type})
        
        buf = io.BytesIO()
        fastavro.writer(buf, schema, records)
        return buf.getvalue()
    except ImportError:
        raise ImportError("Avro export requires 'fastavro' package. Install with: pip install fastavro")


def build_zip(df: pd.DataFrame, report: dict, issues: list, transformations: list, schema: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("cleaned_dataset.csv", to_csv_bytes(df))
        z.writestr("quality_report.json", json.dumps(report, indent=2, default=str))
        z.writestr("issues.csv", pd.DataFrame(issues).to_csv(index=False) if issues else "no issues")
        z.writestr("transformations.csv", pd.DataFrame(transformations).to_csv(index=False) if transformations else "no transformations")
        z.writestr("schema.json", json.dumps(schema, indent=2, default=str))
        z.writestr("README.txt", "DQ Observatory export. See quality_report.json for methodology.\n")
    buf.seek(0)
    return buf.read()


def export_dataframe(
    df: pd.DataFrame, 
    format: str,
    columns: list[str] | None = None,
    filters: dict | None = None,
    date_range: tuple[str, str] | None = None,
    date_column: str | None = None
) -> bytes:
    """Unified export function with filtering and column selection."""
    # Apply column selection
    if columns:
        valid_cols = [c for c in columns if c in df.columns]
        if valid_cols:
            df = df[valid_cols]
    
    # Apply filters
    if filters:
        for col, filter_config in filters.items():
            if col not in df.columns:
                continue
            op = filter_config.get("op", "eq")
            val = filter_config.get("value")
            if op == "eq":
                df = df[df[col] == val]
            elif op == "ne":
                df = df[df[col] != val]
            elif op == "gt":
                df = df[df[col] > val]
            elif op == "gte":
                df = df[df[col] >= val]
            elif op == "lt":
                df = df[df[col] < val]
            elif op == "lte":
                df = df[df[col] <= val]
            elif op == "in":
                df = df[df[col].isin(val)]
            elif op == "contains":
                df = df[df[col].astype(str).str.contains(str(val), na=False)]
    
    # Apply date range
    if date_range and date_column and date_column in df.columns:
        start, end = date_range
        df = df[(df[date_column] >= start) & (df[date_column] <= end)]
    
    format = format.lower()
    if format == "csv":
        return to_csv_bytes(df)
    elif format == "xlsx":
        return to_xlsx_bytes(df)
    elif format == "json":
        return to_json_bytes(df)
    elif format == "parquet":
        return to_parquet_bytes(df)
    elif format == "delta":
        return to_delta_bytes(df)
    elif format == "avro":
        return to_avro_bytes(df)
    elif format == "zip":
        return build_zip(df, {}, [], [], {"columns": list(df.columns)})
    else:
        raise ValueError(f"Unsupported format: {format}. Supported: csv, xlsx, json, parquet, delta, avro, zip")


SUPPORTED_FORMATS = ["csv", "xlsx", "json", "parquet", "delta", "avro", "zip"]