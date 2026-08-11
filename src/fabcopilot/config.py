from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FABCOPILOT_",
        extra="ignore",
    )

    database_url: str
    redis_url: str
    app_env: str = "development"
    log_level: str = "INFO"
    diagnostic_cache_ttl_seconds: int = 300
    embedding_provider: str = "hashing"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_cache_dir: str | None = None
    api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "FABCOPILOT_OPENAI_API_KEY",
            "OPENAI_API_KEY",
        ),
    )
    openai_model: str = "gpt-5.6-terra"

    @field_validator("openai_api_key", "api_key", mode="before")
    @classmethod
    def empty_secret_is_not_configured(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("embedding_provider")
    @classmethod
    def supported_embedding_provider(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized not in {"hashing", "fastembed"}:
            raise ValueError("embedding_provider must be 'hashing' or 'fastembed'")
        return normalized
