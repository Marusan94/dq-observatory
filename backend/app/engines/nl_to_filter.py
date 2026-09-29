"""NL to Filter Engine - converts natural language to API filter JSON with schema validation."""
import json
import re
from typing import Any, Dict, List, Optional

from app.services.llm_service import LLMService


class NLToFilterEngine:
    """Converts natural language questions to validated API filter JSON."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()
        self._operator_map = {
            "igual": "eq", "es": "eq", "===": "eq",
            "distinto": "ne", "no es": "ne", "!=": "ne",
            "mayor": "gt", ">": "gt",
            "mayor o igual": "gte", ">=": "gte",
            "menor": "lt", "<": "lt",
            "menor o igual": "lte", "<=": "lte",
            "contiene": "contains", "contiene el": "contains",
            "en": "in", "entre": "in",
        }

    def _build_schema_context(self, df_columns: List[str], sample_values: Dict[str, List], dtypes: Dict[str, str]) -> Dict:
        """Build schema context for LLM."""
        schema = {}
        for col in df_columns:
            schema[col] = {
                "type": dtypes.get(col, "string"),
                "sample_values": sample_values.get(col, [])[:3],
            }
        return schema

    def _build_sample_context(self, sample_values: Dict[str, List]) -> Dict:
        """Build sample values context."""
        return {col: vals[:3] for col, vals in sample_values.items()}

    async def convert(
        self,
        question: str,
        df_columns: List[str],
        sample_values: Dict[str, List],
        dtypes: Dict[str, str],
    ) -> Dict:
        """
        Convert natural language to filter JSON.
        Returns validated filter dict ready for API.
        """
        # Try LLM first
        schema_context = self._build_schema_context(df_columns, {}, {})
        sample_context = self._build_sample_context(sample_values)
        
        try:
            from app.services.llm_service import LLMService
            llm = LLMService()
            result = await llm.nl_to_filter(
                question=question,
                schema=schema,
                sample_values=sample_context,
            )
            if result:
                return self._validate_and_normalize(result, df_columns)
        except Exception:
            pass  # Fall through to deterministic

        # Deterministic fallback
        return self._deterministic_parse(question, df_columns, sample_values, dtypes)

    def _validate_and_normalize(self, raw: Dict, valid_columns: List[str]) -> Dict:
        """Validate and normalize filter dict."""
        valid = set(valid_columns)
        result = {}

        # columns
        cols = raw.get("columns")
        if cols:
            if isinstance(cols, list):
                result["columns"] = [c for c in cols if c in valid]
            elif isinstance(cols, str):
                result["columns"] = [c.strip() for c in cols.split(",") if c.strip() in valid]

        # filter_col
        fcol = raw.get("filter_col")
        if fcol and fcol in valid:
            result["filter_col"] = fcol

        # filter_op
        fop = raw.get("filter_op")
        if fop in ("eq", "ne", "gt", "gte", "lt", "lte", "in", "contains"):
            result["filter_op"] = fop

        # filter_val
        if "filter_val" in raw:
            result["filter_val"] = raw["filter_val"]

        # date range
        for k in ("date_start", "date_end", "date_column"):
            if k in raw:
                result[k] = raw[k]

        return result

    def _deterministic_parse(
        self,
        question: str,
        df_columns: List[str],
        sample_values: Dict[str, List],
        dtypes: Dict[str, str],
    ) -> Dict:
        """Deterministic keyword-based parsing as fallback."""
        q = question.lower().strip()
        result = {}

        # Column selection
        col_keywords = {
            "solo": True, "solo ": True, "muestra": True, "columnas": True,
            "column": True, "fields": True, "atributos": True,
        }
        if any(k in q for k in col_keywords):
            # Try to extract column names after keywords
            for kw in ["solo", "muestra", "columnas", "column", "fields", "atributos"]:
                if kw in q:
                    after = q.split(kw, 1)[1].strip()
                    # Split by common separators
                    parts = re.split(r'[,y\s]+', after)
                    cols = [p.strip() for p in parts if p.strip() in df_columns]
                    if cols:
                        result["columns"] = cols[:10]
                    break

        # Filter patterns
        for col in df_columns:
            col_lower = col.lower()
            if col_lower in q or any(alias in q for alias in [col_lower.replace("_", " "), col_lower.replace("_", "")]):
                # Found column reference
                result.setdefault("filter_col", col)
                
                # Operator detection
                for kw, op in self._operator_map.items():
                    if kw in q:
                        result["filter_op"] = op
                        # Extract value after operator
                        pattern = rf'{re.escape(kw)}\s+([^,\.]+)'
                        match = re.search(pattern, q)
                        if match:
                            val = match.group(1).strip().strip('"\'')
                            # Type conversion
                            dt = dtypes.get(col, "string")
                            if dt in ("int64", "int32", "float64", "float32"):
                                try:
                                    if "." in val:
                                        result["filter_val"] = float(val)
                                    else:
                                        result["filter_val"] = int(val)
                                except ValueError:
                                    result["filter_val"] = val
                            else:
                                result["filter_val"] = val
                        break

        # Date range patterns
        date_patterns = [
            (r"desde\s+(\d{4}-\d{2}-\d{2})", "date_start"),
            (r"hasta\s+(\d{4}-\d{2}-\d{2})", "date_end"),
            (r"entre\s+(\d{4}-\d{2}-\d{2})\s+y\s+(\d{4}-\d{2}-\d{2})", "date_range"),
            (r"en\s+(\d{4})", "year"),
        ]
        for pattern, key in date_patterns:
            match = re.search(pattern, q)
            if match:
                if key == "date_range":
                    result["date_start"] = match.group(1)
                    result["date_end"] = match.group(2)
                elif key == "year":
                    result["date_start"] = f"{match.group(1)}-01-01"
                    result["date_end"] = f"{match.group(1)}-12-31"
                else:
                    result[key] = match.group(1)
                # Find date column
                date_cols = [c for c in df_columns if "date" in c.lower() or "time" in c.lower() or "created" in c.lower() or "updated" in c.lower()]
                if date_cols:
                    result["date_column"] = date_cols[0]
                break

        # "in" operator with multiple values
        if " en " in q or " entre " in q:
            # Try to extract list
            for sep in [" en ", " entre "]:
                if sep in q:
                    after = q.split(sep, 1)[1].strip()
                    parts = [p.strip().strip('"\'') for p in re.split(r'[,y\s]+', after) if p.strip()]
                    if len(parts) > 1:
                        result["filter_op"] = "in"
                        result["filter_val"] = parts
                        break

        return result