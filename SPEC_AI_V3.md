# AI Assistant V3 — SPEC

## Objetivo
Añadir capa de inteligencia conversacional y predictiva al DQ Observatory:
- **Chat** (`/api/v1/ai/ask`): lenguaje natural → filtros, reglas, exports, insights
- **Auto-fix sugerido** (`/api/v1/ai/suggest-fix`): dado un issue, propone operación de limpieza + preview
- **Scoring predictivo** (`/api/v1/ai/predict-score`): dado dataset + perfil, estima score tras limpieza sugerida

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                  │
├─────────────────────────────────────────────────────────────┤
│  /api/v1/ai/ask          /api/v1/ai/suggest-fix             │
│  /api/v1/ai/predict-score /api/v1/ai/preview-fix            │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ LLM Service   │    │ NL→Filter     │    │ ML Scoring    │
│ (Ollama/      │    │ Engine        │    │ Service       │
│  vLLM/OpenAI) │    │ (schema-aware)│    │ (XGBoost)     │
└───────────────┘    └───────────────┘    └───────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
                    ┌───────────────┐
                    │ Dataset/      │
                    │ Profile Store │
                    │ (SQLite/PG)   │
                    └───────────────┘
```

---

## Componentes

### 1. LLM Service (`app/services/llm_service.py`)
- **Abstracción** sobre proveedores: Ollama (local), vLLM, OpenAI, Anthropic
- **Config** vía env: `LLM_PROVIDER=ollama`, `LLM_MODEL=llama3.1:8b`, `LLM_BASE_URL=http://localhost:11434`
- **Prompt templates** versionados en `app/prompts/`:
  - `chat_system.txt` — system prompt con contexto de esquema
  - `nl_to_filter.txt` — few-shot NL→JSON filter
  - `suggest_fix.txt` — issue→operation mapping
  - `predict_score.txt` — few-shot profile→score delta
- **Retry/timeout** configurables, streaming opcional

### 2. NL→Filter Engine (`app/engines/nl_to_filter.py`)
- **Input**: pregunta usuario + schema actual (columnas, tipos, sample values)
- **Output**: JSON filter válido para `/export` o `/issues`:
  ```json
  {
    "filter_col": "email",
    "filter_op": "contains",
    "filter_val": "@",
    "columns": ["id", "email", "name"],
    "date_start": "2024-01-01",
    "date_end": "2024-12-31",
    "date_column": "created_at"
  }
  ```
- **Few-shot examples** en prompt (10-15 casos cubriendo ops, rangos, columnas múltiples)
- **Validación** contra schema real antes de devolver

### 3. Auto-Fix Suggestion (`app/engines/auto_fix.py`)
- **Input**: issue object (severity, category, column, description, examples)
- **Output**: lista de operaciones candidatas con preview:
  ```json
  [
    {
      "operation": "normalize_email",
      "column": "email",
      "params": {},
      "preview_rows": 5,
      "estimated_fixed": 23,
      "confidence": 0.92,
      "reasoning": "Issue category VALIDITY + examples show uppercase/trailing spaces"
    }
  ]
  ```
- **Heurísticas determinísticas** primero (rápidas, sin LLM):
  - VALIDITY + email → `normalize_email`
  - VALIDITY + phone → `normalize_phone`
  - CONSISTENCY + whitespace → `trim`
  - VALIDITY + numeric-as-text → `cast_numeric`
- **Fallback LLM** para issues complejos (regex personalizado, multi-columna)

### 4. Predictive Scoring (`app/services/predictive_scoring.py`)
- **Modelo**: XGBoost regressor entrenado offline con historial de `quality_runs`
- **Features**: profile metrics (missing%, duplicate%, type_confidence, pii_count, cardinality, etc.) + issue counts por categoría
- **Target**: `score_overall` tras limpieza real (del historial)
- **Serving**: ONNX Runtime o joblib pickle cargado en memoria
- **Endpoint**: `/predict-score` devuelve `{predicted_score, delta, confidence_interval, feature_importance}`

---

## Endpoints API

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|-------------|
| `/api/v1/ai/ask` | POST | X-Role: editor+ | Chat libre. Body: `{question, dataset_id?, context?}`. Stream opcional. |
| `/api/v1/ai/suggest-fix` | POST | X-Role: editor+ | Body: `{issue_id}` o `{issue_obj}`. Devuelve lista de fixes con preview. |
| `/api/v1/ai/preview-fix` | POST | X-Role: editor+ | Body: `{dataset_id, operation, column, params}`. Devuelve preview (primeras 10 filas). |
| `/api/v1/ai/predict-score` | POST | X-Role: viewer+ | Body: `{dataset_id}` o `{profile}`. Devuelve `{predicted, delta, ci, features}`. |

---

## Modelos de Datos (nuevos)

```python
# app/models/ai.py
class AIChatLog(Base):
    id, dataset_id, user_role, question, answer, tokens_used, latency_ms, created_at

class AIFixSuggestion(Base):
    id, issue_id, operation, column, params, preview_json, confidence, reasoning, accepted, created_at

class PredictiveModelVersion(Base):
    version, model_path, features_json, metrics_json (MAE, RMSE), trained_at, is_active
```

---

## Frontend (React)

| Componente | Ubicación | Descripción |
|------------|-----------|-------------|
| `AIChatDrawer` | `src/components/AIChatDrawer.tsx` | Side drawer fijo derecha, historial, streaming, botón copiar |
| `AIFixCard` | `src/components/AIFixCard.tsx` | En Issues: botón "🤖 Sugerir fix" → modal con operaciones, preview, botón "Aplicar" |
| `PredictiveScoreBadge` | `src/components/PredictiveScoreBadge.tsx` | En Overview/Reports: badge "Predicho: 78 (+12)" con tooltip feature importance |
| `AIContextProvider` | `src/context/AIContext.tsx` | Estado global: historial chat, fix sugeridos, score predictivo |

---

## Dependencias Nuevas

```
# backend/requirements.txt
ollama-python==0.3.0        # o openai==1.30, anthropic==0.25
xgboost==2.1.0
onnxruntime==1.18.0         # opcional para serving
scikit-learn==1.5.0
joblib==1.4.0
```

---

## Entrenamiento Offline (script)

```bash
# scripts/train_predictive_model.py
# 1. Lee quality_runs + profiles históricos
# 2. Construye features (50+ métricas)
# 3. Target: score_overall tras limpieza (diferencia entre versiones)
# 4. Entrena XGBoost con CV, guarda modelo + metadata
# 5. Registra versión en PredictiveModelVersion
```

---

## Seguridad / Costes

- **Sin ejecución de código** generado por LLM (solo JSON filters/ops predefinidas)
- **Rate limit** por usuario/rol (ej. 30 req/min editor, 10 viewer)
- **Budget tokens**: límite mensual configurable, alerta Slack
- **PII masking** en prompts (hash emails/nombres antes de enviar)
- **Fallback**: si LLM no disponible → solo heurísticas determinísticas

---

## Métricas de Éxito

| Métrica | Target |
|---------|--------|
| Latencia `/ask` (p95) | < 3s (streaming first token < 500ms) |
| Precisión auto-fix (accepted/suggested) | > 70% |
| MAE scoring predictivo | < 5 puntos |
| Adopción (usuarios activos/semana) | > 40% editores |

---

## Próximos Pasos

1. **Infra**: levantar Ollama local (`docker run -d -p 11434:11434 ollama/ollama && ollama pull llama3.1:8b`)
2. **Backend**: implementar `LLMService` + `NLToFilterEngine` + tests unitarios
3. **API**: endpoints `/ai/*` con RBAC
4. **Frontend**: `AIChatDrawer` + integración en Issues/Overview
5. **Entrenamiento**: correr script offline, activar modelo v1
6. **E2E**: tests Playwright para chat + fix suggestion