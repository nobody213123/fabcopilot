from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FABCOPILOT_",
        extra="ignore",
    )

    database_url: str
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "FABCOPILOT_OPENAI_API_KEY",
            "OPENAI_API_KEY",
        ),
    )
    openai_model: str = "gpt-5.6-terra"

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def empty_openai_key_is_not_configured(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value
