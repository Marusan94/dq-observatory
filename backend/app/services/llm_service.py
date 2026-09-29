"""LLM Service abstraction for multiple providers (Ollama, vLLM, OpenAI, Anthropic)."""
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from app.core.config import get_settings


@dataclass
class LLMResponse:
    content: str
    tokens_used: int
    latency_ms: int
    model: str


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        pass


class OllamaProvider(LLMProvider):
    """Ollama local provider."""

    def __init__(self, base_url: str, model: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        t0 = time.time()
        if stream:
            return self._stream_complete(payload, t0)
        async with self.client.stream("POST", f"{self.base_url}/api/chat", json=payload, timeout=self.timeout) as resp:
            resp.raise_for_status()
            data = await resp.aread()
            result = json.loads(data)
            latency = int((time.time() - t0) * 1000)
            return LLMResponse(
                content=result["message"]["content"],
                tokens_used=result.get("eval_count", 0) + result.get("prompt_eval_count", 0),
                latency_ms=latency,
                model=self.model,
            )

    async def _stream_complete(self, payload: Dict, t0: float) -> AsyncGenerator[str, None]:
        async with self.client.stream("POST", f"{self.base_url}/api/chat", json=payload, timeout=self.timeout) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
                    except json.JSONDecodeError:
                        pass

    def count_tokens(self, text: str) -> int:
        # Rough approximation for Ollama
        return len(text) // 4


class OpenAIProvider(LLMProvider):
    """OpenAI / compatible provider."""

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.openai.com/v1", timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        t0 = time.time()
        if stream:
            return self._stream_complete(payload, t0)
        resp = await self.client.post(f"{self.base_url}/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency = int((time.time() - t0) * 1000)
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            tokens_used=data["usage"]["total_tokens"],
            latency_ms=latency,
            model=self.model,
        )

    async def _stream_complete(self, payload: Dict, t0: float) -> AsyncGenerator[str, None]:
        async with self.client.stream("POST", f"{self.base_url}/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        chunk = json.loads(line[6:])
                        if chunk["choices"][0]["delta"].get("content"):
                            yield chunk["choices"][0]["delta"]["content"]
                    except (json.JSONDecodeError, KeyError):
                        pass

    def count_tokens(self, text: str) -> int:
        # Rough approximation
        return len(text) // 4


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.anthropic.com/v1", timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        # Convert messages to Anthropic format
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]
        
        payload = {
            "model": self.model,
            "system": system,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        t0 = time.time()
        if stream:
            return self._stream_complete(payload, t0)
        resp = await self.client.post(f"{self.base_url}/messages", json=payload)
        resp.raise_for_status()
        data = resp.json()
        latency = int((time.time() - t0) * 1000)
        return LLMResponse(
            content=data["content"][0]["text"],
            tokens_used=data["usage"]["input_tokens"] + data["usage"]["output_tokens"],
            latency_ms=latency,
            model=self.model,
        )

    async def _stream_complete(self, payload: Dict, t0: float) -> AsyncGenerator[str, None]:
        async with self.client.stream("POST", f"{self.base_url}/messages", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        if chunk.get("type") == "content_block_delta":
                            yield chunk["delta"]["text"]
                    except (json.JSONDecodeError, KeyError):
                        pass

    def count_tokens(self, text: str) -> int:
        return len(text) // 4


class VLLMProvider(OpenAIProvider):
    """vLLM OpenAI-compatible provider."""

    def __init__(self, base_url: str, model: str, api_key: str = "dummy", timeout: int = 60):
        super().__init__(api_key=api_key, model=model, base_url=base_url, timeout=timeout)


def create_llm_provider() -> LLMProvider:
    """Factory to create LLM provider from settings."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    model = settings.llm_model
    base_url = settings.llm_base_url
    timeout = settings.llm_timeout

    if provider == "ollama":
        return OllamaProvider(base_url, model, timeout)
    elif provider == "vllm":
        return VLLMProvider(base_url, settings.llm_model, settings.llm_api_key, timeout)
    elif provider == "openai":
        return OpenAIProvider(settings.llm_api_key, model, base_url, timeout)
    elif provider == "anthropic":
        return AnthropicProvider(settings.llm_api_key, model, "https://api.anthropic.com/v1", timeout)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


class LLMService:
    """High-level LLM service with prompt templates, retries, token budget."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or create_llm_provider()
        self.settings = get_settings()
        self._token_usage_this_month = 0
        self._load_token_usage()

    def _load_token_usage(self):
        # TODO: persist to DB/Redis
        pass

    def _save_token_usage(self):
        # TODO: persist to DB/Redis
        pass

    def _check_budget(self, estimated_tokens: int) -> bool:
        return (self._token_usage_this_month + estimated_tokens) <= self.settings.ai_monthly_token_limit

    def _mask_pii(self, text: str) -> str:
        """Simple PII masking for logs/prompts."""
        import re
        # Email
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        # Phone (basic)
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        # Credit card (basic)
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', text)
        return text

    def _load_prompt(self, name: str) -> str:
        path = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{name}.txt")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _render_prompt(self, template: str, **kwargs) -> str:
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template

    async def chat(
        self,
        question: str,
        dataset_context: Optional[Dict] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """General chat with dataset context."""
        system = system_prompt or self._load_prompt("chat_system")
        if dataset_context:
            system = self._render_prompt(system, **dataset_context)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]

        estimated = sum(self.provider.count_tokens(m["content"]) for m in messages) + 500
        if not self._check_budget(estimated):
            raise RuntimeError("AI token budget exceeded for this month")

        result = await self._with_retry(messages, stream=stream)
        if not stream and isinstance(result, LLMResponse):
            self._token_usage_this_month += result.tokens_used
            self._save_token_usage()
        return result

    async def nl_to_filter(
        self,
        question: str,
        schema: Dict,
        sample_values: Dict,
    ) -> Dict:
        """Convert natural language to filter JSON."""
        template = self._load_prompt("nl_to_filter")
        prompt = self._render_prompt(template, schema_json=json.dumps(schema, ensure_ascii=False), sample_json=json.dumps(sample_values, ensure_ascii=False), question=question)
        messages = [{"role": "user", "content": prompt}]
        
        result = await self._with_retry(messages)
        if isinstance(result, LLMResponse):
            try:
                # Extract JSON from response
                content = result.content.strip()
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback: try to find JSON in text
                import re
                match = re.search(r'\{.*\}', result.content, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise ValueError(f"LLM returned invalid JSON: {result.content}")
        return {}

    async def suggest_fix(
        self,
        issue: Dict,
        column_type: str,
        column_samples: List,
    ) -> List[Dict]:
        """Suggest fix operations for an issue."""
        template = self._load_prompt("suggest_fix")
        prompt = self._render_prompt(
            template,
            severity=issue.get("severity", "MEDIUM"),
            category=issue.get("category", "VALIDITY"),
            column=issue.get("column", ""),
            description=issue.get("description", ""),
            examples=json.dumps(issue.get("examples", [])[:5], ensure_ascii=False),
            col_type=column_type,
            col_samples=json.dumps(column_samples[:5], ensure_ascii=False),
        )
        messages = [{"role": "user", "content": prompt}]
        result = await self._with_retry(messages)
        if isinstance(result, LLMResponse):
            try:
                content = result.content.strip()
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                data = json.loads(content)
                return data.get("fix_suggestions", [])
            except json.JSONDecodeError:
                pass
        # Fallback deterministic
        return self._deterministic_fix_fallback(issue)

    def _deterministic_fix_fallback(self, issue: Dict) -> List[Dict]:
        """Heuristic fallback when LLM unavailable."""
        cat = issue.get("category", "").upper()
        col = issue.get("column", "")
        row_count = issue.get("row_count", 0)
        suggestions = []

        if cat == "VALIDITY" and col:
            col_lower = col.lower()
            if "email" in col_lower:
                suggestions.append({"operation": "normalize_email", "column": col, "params": {}, "estimated_fixed": row_count, "confidence": 0.95, "reasoning": "Emails con mayúsculas/espacios se normalizan automáticamente"})
            elif "phone" in col_lower or "tel" in col_lower:
                suggestions.append({"operation": "normalize_phone", "column": col, "params": {"country": "US"}, "estimated_fixed": row_count, "confidence": 0.9, "reasoning": "Teléfonos en múltiples formatos se estandarizan a E.164"})

        if "whitespace" in issue.get("description", "").lower() or "space" in issue.get("description", "").lower():
            suggestions.append({"operation": "trim", "column": col, "params": {}, "estimated_fixed": row_count, "confidence": 0.98, "reasoning": "Espacios en blanco al inicio/fin se eliminan"})

        return suggestions[:3]

    async def predict_score(
        self,
        profile: Dict,
        issues: List,
        proposed_fixes: List,
    ) -> Dict:
        """Predict score after fixes using LLM fallback (model preferred)."""
        # Try ML model first (implemented separately)
        try:
            from app.services.predictive_scoring import predict_score_ml
            return predict_score_ml(profile, issues, proposed_fixes)
        except Exception:
            pass

        # LLM fallback
        template = self._load_prompt("predict_score")
        prompt = self._render_prompt(
            template,
            profile_json=json.dumps(profile, ensure_ascii=False),
            issues_summary=json.dumps([{"cat": i.get("category"), "count": i.get("row_count")} for i in issues], ensure_ascii=False),
            proposed_fixes=json.dumps(proposed_fixes, ensure_ascii=False),
        )
        messages = [{"role": "user", "content": prompt}]
        result = await self._with_retry(messages)
        if isinstance(result, LLMResponse):
            try:
                content = result.content.strip()
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                return json.loads(content)
            except json.JSONDecodeError:
                pass
        return {"predicted_score": 0, "delta": 0, "confidence_interval": [0, 0], "top_features": []}

    async def _with_retry(self, messages: List[Dict], stream: bool = False) -> LLMResponse | AsyncGenerator[str, None]:
        last_exc = None
        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                return await self.provider.complete(
                    messages,
                    temperature=self.settings.llm_temperature,
                    max_tokens=self.settings.llm_max_tokens,
                    stream=stream,
                )
            except Exception as e:
                last_exc = e
                if attempt < self.settings.llm_max_retries:
                    await __import__("asyncio").sleep(2 ** attempt)
                else:
                    raise RuntimeError(f"LLM failed after {self.settings.llm_max_retries + 1} attempts: {last_exc}")
        raise RuntimeError(f"LLM failed: {last_exc}")