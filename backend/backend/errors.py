import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class ProviderError(AppError):
    pass


class RateLimitError(ProviderError):
    pass


def _payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict):
            message = exc.detail.get("message", "Request failed")
            details = exc.detail
        else:
            message = str(exc.detail)
            details = None
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload("http_error", message, details),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError):
        safe_errors = []
        for error in exc.errors():
            safe_errors.append({key: value for key, value in error.items() if key != "ctx"})
        return JSONResponse(
            status_code=422,
            content=_payload(
                "validation_error",
                "Request validation failed",
                safe_errors,
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_request: Request, exc: SQLAlchemyError):
        logger.exception("Database operation failed", exc_info=exc)
        return JSONResponse(
            status_code=503,
            content=_payload(
                "database_unavailable",
                "The database is temporarily unavailable",
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_request: Request, exc: Exception):
        logger.exception("Unhandled API error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_payload("internal_error", "An unexpected error occurred"),
        )
