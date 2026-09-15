from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_version: str = "0.2.0"
    allowed_origins: str = "http://localhost:3000"
    debug_log_raw: bool = False
    demo_mode: bool = False
    max_document_chars: int = 4000
    rate_limit_per_minute: int = 10
    prompt_version: str = "normalization-v1"
    rules_version: str = "longitudinal-rules-v2"
    dataset_version: str = "synthetic-eval-v1"
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5-20251001"
    daily_request_limit: int = 250
    confidence_threshold: float = 0.70
    rxnorm_enabled: bool = False
    rxnorm_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    rxnorm_timeout_seconds: float = 4.0

    @cached_property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
