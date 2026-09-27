from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    # Nur für ältere Supabase-Projekte mit HS256-Secret. Neue Projekte nutzen
    # asymmetrische Schlüssel, die über JWKS geladen werden.
    supabase_jwt_secret: str = ""

    frontend_origins: list[str] = ["http://localhost:3000"]

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
