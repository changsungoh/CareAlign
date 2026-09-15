from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_version: str = "0.1.0"
    allowed_origins: str = "http://localhost:3000"
    debug_log_raw: bool = False
    demo_mode: bool = False
    max_document_chars: int = 4000
    rate_limit_per_minute: int = 10
    prompt_version: str = "normalization-v0"
    rules_version: str = "conflict-rules-v0"
    dataset_version: str = "synthetic-eval-v0"

    @cached_property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
