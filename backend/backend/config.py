import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(value: str, default: bool) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str, default: str) -> list[str]:
    return [item.strip() for item in (value or default).split(",") if item.strip()]


def _database_url() -> str:
    value = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(PROJECT_ROOT / 'investment_app.db').as_posix()}",
    )
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Investment Research API")
    environment: str = os.getenv("APP_ENV", "development").lower()
    database_url: str = _database_url()
    secret_key: str = os.getenv("SECRET_KEY", "development-only-change-me-at-least-32-bytes")
    plaid_encryption_key: str = os.getenv("PLAID_ENCRYPTION_KEY", "")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    finnhub_api_key: str = os.getenv("FINNHUB_API_KEY", "").strip()
    finnhub_base_url: str = os.getenv("FINNHUB_BASE_URL", "https://finnhub.io/api/v1").rstrip("/")
    finnhub_timeout_seconds: float = float(os.getenv("FINNHUB_TIMEOUT_SECONDS", "10"))
    finnhub_max_concurrency: int = int(os.getenv("FINNHUB_MAX_CONCURRENCY", "5"))
    finnhub_max_retries: int = int(os.getenv("FINNHUB_MAX_RETRIES", "3"))
    metrics_cache_ttl_seconds: int = int(os.getenv("METRICS_CACHE_TTL_SECONDS", "900"))

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()

    plaid_client_id: str = os.getenv("PLAID_CLIENT_ID", "").strip()
    plaid_secret: str = os.getenv("PLAID_SECRET", "").strip()
    plaid_environment: str = os.getenv("PLAID_ENV", "sandbox").lower()

    demo_mode: bool = _as_bool(os.getenv("DEMO_MODE", "true"), True)
    auto_create_database: bool = _as_bool(os.getenv("AUTO_CREATE_DATABASE", "true"), True)
    max_scan_tickers: int = int(os.getenv("MAX_SCAN_TICKERS", "1000"))
    scan_timeout_seconds: float = float(os.getenv("SCAN_TIMEOUT_SECONDS", "120"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    cors_origins: list[str] = field(
        default_factory=lambda: _as_list(
            os.getenv("CORS_ORIGINS", ""),
            "http://localhost:3000,http://127.0.0.1:3000",
        )
    )
    trusted_hosts: list[str] = field(
        default_factory=lambda: _as_list(
            os.getenv("TRUSTED_HOSTS", ""),
            "localhost,127.0.0.1,testserver",
        )
    )

    def validate(self) -> None:
        if self.finnhub_max_concurrency < 1:
            raise ValueError("FINNHUB_MAX_CONCURRENCY must be at least 1")
        if self.max_scan_tickers < 1:
            raise ValueError("MAX_SCAN_TICKERS must be at least 1")
        if self.environment == "production":
            if self.secret_key == "development-only-change-me-at-least-32-bytes":
                raise ValueError("SECRET_KEY must be configured in production")
            if not self.plaid_encryption_key:
                raise ValueError("PLAID_ENCRYPTION_KEY is required in production")
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must contain at least 32 characters")
            if self.database_url.startswith("sqlite"):
                raise ValueError("A production DATABASE_URL must not use SQLite")


settings = Settings()
settings.validate()
