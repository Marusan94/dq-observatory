"""Auto-Fix Suggestion Engine - suggests cleaning operations for quality issues."""
from typing import Any, Dict, List, Optional

from app.services.llm_service import LLMService


class AutoFixEngine:
    """Suggests cleaning operations for quality issues."""

    # Deterministic mappings for common patterns
    HEURISTIC_MAP = {
        ("VALIDITY", "email"): [
            {"operation": "normalize_email", "params": {}, "confidence": 0.95, "reasoning": "Emails con mayúsculas/espacios se normalizan automáticamente"}
        ],
        ("VALIDITY", "phone"): [
            {"operation": "normalize_phone", "params": {"country": "US"}, "confidence": 0.9, "reasoning": "Teléfonos en múltiples formatos se estandarizan a E.164"}
        ],
        ("VALIDITY", "url"): [
            {"operation": "normalize_url", "params": {}, "confidence": 0.85, "reasoning": "URLs malformadas se corrigen añadiendo protocolo"}
        ],
        ("VALIDITY", "date"): [
            {"operation": "cast_date", "params": {"formats": ["ISO", "DD/MM/YYYY", "MM/DD/YYYY"]}, "confidence": 0.9, "reasoning": "Fechas en formatos mixtos se parsean automáticamente"}
        ],
        ("VALIDITY", "numeric"): [
            {"operation": "cast_numeric", "params": {}, "confidence": 0.9, "reasoning": "Números como texto se convierten a numérico"}
        ],
        ("CONSISTENCY", "whitespace"): [
            {"operation": "trim", "params": {}, "confidence": 0.98, "reasoning": "Espacios en blanco al inicio/fin se eliminan"}
        ],
        ("CONSISTENCY", "case"): [
            {"operation": "lowercase", "params": {}, "confidence": 0.8, "reasoning": "Texto inconsistente se normaliza a minúsculas"},
            {"operation": "uppercase", "params": {}, "confidence": 0.8, "reasoning": "Texto inconsistente se normaliza a mayúsculas"}
        ],
        ("CONSISTENCY", "format"): [
            {"operation": "replace_pattern", "params": {"pattern": r"\s+", "replacement": " "}, "confidence": 0.85, "reasoning": "Espacios múltiples se normalizan a uno solo"}
        ],
        ("COMPLETENESS", "missing"): [
            {"operation": "fill_missing", "params": {"strategy": "mode"}, "confidence": 0.7, "reasoning": "Valores nulos se rellenan con la moda"},
            {"operation": "drop_rows", "params": {}, "confidence": 0.6, "reasoning": "Filas con nulos se eliminan (pierde datos)"}
        ],
        ("UNIQUENESS", "duplicate"): [
            {"operation": "deduplicate", "params": {"subset": None}, "confidence": 0.95, "reasoning": "Duplicados exactos se eliminan manteniendo la primera ocurrencia"}
        ],
    }

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()

    def _match_heuristic(self, issue: Dict) -> List[Dict]:
        """Match issue to heuristic suggestions."""
        category = issue.get("category", "").upper()
        column = issue.get("column", "").lower()
        description = issue.get("description", "").lower()
        row_count = issue.get("row_count", 0)

        suggestions = []

        # Direct category+column match
        key = (category, column)
        if key in self.HEURISTIC_MAP:
            for s in self.HEURISTIC_MAP[key]:
                s = s.copy()
                s["estimated_fixed"] = row_count
                suggestions.append(s)

        # Description-based matching
        desc_lower = description.lower()
        if "email" in desc_lower or "mail" in desc_lower:
            key = ("VALIDITY", "email")
            if key in self.HEURISTIC_MAP:
                for s in self.HEURISTIC_MAP[key]:
                    s = s.copy()
                    s["estimated_fixed"] = row_count
                    suggestions.append(s)
        elif "phone" in desc_lower or "tel" in desc_lower:
            key = ("VALIDITY", "phone")
            if key in self.HEURISTIC_MAP:
                for s in self.HEURISTIC_MAP[key]:
                    s = s.copy()
                    s["estimated_fixed"] = row_count
                    suggestions.append(s)
        elif "space" in desc_lower or "trim" in desc_lower or "whitespace" in desc_lower:
            key = ("CONSISTENCY", "whitespace")
            if key in self.HEURISTIC_MAP:
                for s in self.HEURISTIC_MAP[key]:
                    s = s.copy()
                    s["estimated_fixed"] = row_count
                    suggestions.append(s)
        elif "duplicate" in desc_lower or "duplicad" in desc_lower:
            key = ("UNIQUENESS", "duplicate")
            if key in self.HEURISTIC_MAP:
                for s in self.HEURISTIC_MAP[key]:
                    s = s.copy()
                    s["estimated_fixed"] = row_count
                    suggestions.append(s)
        elif "missing" in desc_lower or "nulo" in desc_lower or "null" in desc_lower:
            key = ("COMPLETENESS", "missing")
            if key in self.HEURISTIC_MAP:
                for s in self.HEURISTIC_MAP[key]:
                    s = s.copy()
                    s["estimated_fixed"] = row_count
                    suggestions.append(s)
        elif "numeric" in desc_lower or "númer" in desc_lower or "number" in desc_lower:
            key = ("VALIDITY", "numeric")
            if key in self.HEURISTIC_MAP:
                for s in self.HEURISTIC_MAP[key]:
                    s = s.copy()
                    s["estimated_fixed"] = row_count
                    suggestions.append(s)

        # Deduplicate by operation
        seen = set()
        unique = []
        for s in suggestions:
            op_key = (s["operation"], tuple(s.get("params", {}).items()))
            if op_key not in seen:
                seen.add(op_key)
                unique.append(s)

        # Add estimated_fixed if missing
        for s in unique:
            s.setdefault("estimated_fixed", 0)
            s.setdefault("confidence", 0.8)
            s.setdefault("reasoning", "Sugerencia basada en heurísticas")

        return unique[:3]

    async def suggest(
        self,
        issue: Dict,
        column_type: str,
        column_samples: List,
        llm_service: Optional[Any] = None,
    ) -> List[Dict]:
        """Generate fix suggestions for an issue."""
        # Try deterministic first
        heuristic = self._match_heuristic(issue)
        
        # If we have good heuristic matches, return them
        if heuristic and any(s["confidence"] > 0.85 for s in heuristic):
            return heuristic[:3]

        # Try LLM for complex cases
        llm = llm_service or LLMService()
        try:
            llm_suggestions = await llm.suggest_fix(issue, column_type, column_samples)
            if llm_suggestions:
                # Merge: LLM first, then heuristic
                merged = llm_suggestions + heuristic
                # Deduplicate by operation
                seen = set()
                merged_unique = []
                for s in merged:
                    op_key = (s["operation"], tuple(s.get("params", {}).items()))
                    if op_key not in seen:
                        seen.add(op_key)
                        merged_unique.append(s)
                return merged_unique[:3]
        except Exception:
            pass

        return heuristic[:3]

    def preview_fix(
        self,
        df,
        operation: str,
        column: str,
        params: Dict,
        limit: int = 10,
    ) -> Dict:
        """Generate preview of fix operation on dataframe."""
        from app.services.cleaning_service import apply_op
        
        try:
            preview_df, meta = apply_op(df, operation, column, params)
            preview_rows = preview_df.head(limit).to_dict("records")
            return {
                "operation": operation,
                "column": column,
                "params": params,
                "preview_rows": preview_rows,
                "rows_affected": meta.get("rows_affected", 0),
                "success": True,
            }
        except Exception as e:
            return {
                "operation": operation,
                "column": column,
                "params": params,
                "error": str(e),
                "success": False,
            }