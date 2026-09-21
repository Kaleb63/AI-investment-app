from fastapi import APIRouter, Query

from backend.config import settings
from backend.demo_data import DEMO_HOLDINGS
from backend.errors import AppError
from backend.services.portfolio_service import portfolio_service

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get(
    "/portfolio_analysis",
    summary="Analyze a clearly marked simulated portfolio",
)
async def demo_portfolio_analysis(include_ai: bool = Query(default=False)):
    if not settings.demo_mode:
        raise AppError("demo_disabled", "Demo mode is disabled", 404)
    return await portfolio_service.analyze(
        DEMO_HOLDINGS,
        simulated=True,
        include_ai=include_ai,
    )
