from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "DQ Observatory"
    app_version: str = "0.1.0"
    engine_version: str = "dq-engine-0.1.0"
    ruleset_version: str = "general-v1"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./storage/dq.db"
    storage_path: str = "./storage"
    max_upload_size_mb: int = 100
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    app_env: str = "local"
    app_env: str = "local"
    default_country_phone: str = "US"
    default_date_format: str = "ISO"
    # LLM / AI
    llm_provider: str = "ollama"  # ollama | vllm | openai | anthropic
    llm_model: str = "llama3.1:8b"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str = ""
    llm_timeout: int = 60
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.1
    llm_max_retries: int = 2
    # AI Budget
    ai_monthly_token_limit: int = 1000000
    ai_alert_webhook: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
