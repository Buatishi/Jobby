from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(
        default="",
        alias="SUPABASE_SERVICE_ROLE_KEY",
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    lemonsqueezy_api_key: str = Field(default="", alias="LEMONSQUEEZY_API_KEY")
    lemonsqueezy_store_id: str = Field(default="", alias="LEMONSQUEEZY_STORE_ID")
    lemonsqueezy_webhook_secret: str = Field(
        default="",
        alias="LEMONSQUEEZY_WEBHOOK_SECRET",
    )
    lemonsqueezy_premium_variant_id: str = Field(
        default="",
        alias="LEMONSQUEEZY_PREMIUM_VARIANT_ID",
    )
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    public_app_url: str = Field(
        default="http://localhost:3000",
        alias="NEXT_PUBLIC_APP_URL",
    )

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
