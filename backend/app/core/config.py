from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables.

    Swapping the local Ollama model for a hosted provider is a config-only
    change, e.g. LLM_MODEL=gpt-4o + LLM_API_KEY=sk-... (no LLM_API_BASE needed).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LiteLLM model string, always "<provider>/<model>" (e.g. "anthropic/claude-sonnet-4-5").
    llm_model: str = Field(
        default="ollama_chat/llama3.2",
        validation_alias=AliasChoices("LLM_MODEL"),
    )
    # OLLAMA_HOST is accepted as an alias so the existing docker-compose keeps working.
    llm_api_base: str | None = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("LLM_API_BASE"),
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY"),
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        validation_alias=AliasChoices("CORS_ORIGINS"),
    )

    auth_session_ttl_seconds: int = Field(
        default=1800,
        ge=1,
        validation_alias=AliasChoices("AUTH_SESSION_TTL_SECONDS"),
    )
    otp_ttl_seconds: int = Field(
        default=300,
        ge=1,
        validation_alias=AliasChoices("OTP_TTL_SECONDS"),
    )
    otp_max_attempts: int = Field(
        default=5,
        ge=1,
        validation_alias=AliasChoices("OTP_MAX_ATTEMPTS"),
    )
    otp_resend_cooldown_seconds: int = Field(
        default=45,
        ge=1,
        validation_alias=AliasChoices("OTP_RESEND_COOLDOWN_SECONDS"),
    )
    auth_session_cleanup_interval_seconds: int = Field(
        default=60,
        ge=1,
        validation_alias=AliasChoices("AUTH_SESSION_CLEANUP_INTERVAL_SECONDS"),
    )
    sms_provider: str = Field(
        default="console",
        validation_alias=AliasChoices("SMS_PROVIDER"),
    )
