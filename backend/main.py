from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from backend.config import settings
from backend.database import init_database
from backend.errors import register_error_handlers
from backend.logging_config import configure_logging
from backend.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from backend.routes import auth, demo, health, plaid, screener, stocks, watchlist
from backend.services.finnhub_service import finnhub_service
from backend.services.scoring_service import score_equity

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_create_database:
        init_database()
    yield
    await finnhub_service.close()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Backend APIs for deterministic stock research, portfolio analysis, "
            "Plaid account connectivity, natural-language screening, and watchlists. "
            "AI interprets and explains evidence but never decides screening outcomes."
        ),
        lifespan=lifespan,
        contact={"name": "AI Investment App"},
        license_info={"name": "Private project"},
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RateLimitMiddleware)
    register_error_handlers(application)

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(stocks.router)
    application.include_router(screener.router)
    application.include_router(plaid.router)
    application.include_router(watchlist.router)
    application.include_router(demo.router)
    return application


app = create_app()


async def get_clean_metrics(ticker: str):
    """Compatibility export for code that imported the original helper."""

    return await finnhub_service.get_clean_metrics(ticker)


__all__ = ["app", "create_app", "get_clean_metrics", "score_equity"]
