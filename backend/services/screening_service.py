import asyncio
import logging
import time
from typing import Any

from backend.config import settings
from backend.errors import AppError
from backend.schemas.screen import ScreeningCriteria, ScreenRequest, ScreenResponse
from backend.services.cache import CacheService, cache_service
from backend.services.finnhub_service import FinnhubService, finnhub_service
from backend.services.scoring_service import score_equity

logger = logging.getLogger(__name__)


SCREENING_RULES = {
    "min_score": ("score", "overall_score", "greater_than_or_equal"),
    "max_pe_ratio": ("metrics", "pe_ratio", "less_than_or_equal"),
    "min_revenue_growth": (
        "metrics",
        "revenue_growth",
        "greater_than_or_equal",
    ),
    "min_eps_growth": ("metrics", "eps_growth", "greater_than_or_equal"),
    "min_profit_margin": (
        "metrics",
        "profit_margin",
        "greater_than_or_equal",
    ),
    "min_return_on_equity": (
        "metrics",
        "return_on_equity",
        "greater_than_or_equal",
    ),
    "min_current_ratio": (
        "metrics",
        "current_ratio",
        "greater_than_or_equal",
    ),
}


def evaluate_screening_criteria(
    metrics: dict[str, Any],
    score: dict[str, Any],
    criteria: dict[str, float],
) -> tuple[list, list, list]:
    passed, failed, unavailable = [], [], []
    for criterion, required_value in criteria.items():
        source, value_key, comparison = SCREENING_RULES[criterion]
        actual_value = (score if source == "score" else metrics).get(value_key)
        if actual_value is None:
            unavailable.append(
                {
                    "criterion": criterion,
                    "required_value": required_value,
                    "reason": f"{value_key} is unavailable",
                }
            )
            continue
        criterion_passed = (
            actual_value >= required_value
            if comparison == "greater_than_or_equal"
            else actual_value <= required_value
        )
        if criterion_passed:
            passed.append(criterion)
        else:
            failed.append(
                {
                    "criterion": criterion,
                    "comparison": comparison,
                    "required_value": required_value,
                    "actual_value": actual_value,
                }
            )
    return passed, failed, unavailable


class ScreeningService:
    def __init__(self, market_data: FinnhubService, cache: CacheService) -> None:
        self.market_data = market_data
        self.cache = cache

    async def _analyze_one(
        self,
        ticker: str,
        request: ScreenRequest,
        criteria: dict[str, float],
    ) -> dict[str, Any]:
        try:
            metrics = await self.market_data.get_clean_metrics(ticker)
            score = score_equity(metrics, request.weights)
            passed, failed, unavailable = evaluate_screening_criteria(metrics, score, criteria)

            if score["overall_score"] is None:
                return {
                    "kind": "unavailable",
                    "ticker": ticker,
                    "status": "insufficient_data",
                    "reason": "No scorable financial data was available",
                    "missing_criteria": unavailable,
                }

            stock = {
                "ticker": ticker,
                "metrics": metrics,
                "score": score,
                "passed_criteria": passed,
            }
            if failed:
                return {
                    "kind": "rejected",
                    **stock,
                    "failed_criteria": failed,
                    "unevaluated_criteria": unavailable,
                }
            if unavailable:
                return {
                    "kind": "unavailable",
                    "ticker": ticker,
                    "status": "insufficient_data",
                    "reason": "One or more required criteria could not be evaluated",
                    "missing_criteria": unavailable,
                }
            return {"kind": "matching", **stock}
        except AppError as exc:
            return {
                "kind": "unavailable",
                "ticker": ticker,
                "status": "error",
                "reason": exc.message,
                "missing_criteria": [],
            }
        except Exception:
            logger.exception("Unexpected stock analysis failure ticker=%s", ticker)
            return {
                "kind": "unavailable",
                "ticker": ticker,
                "status": "error",
                "reason": "Stock analysis failed unexpectedly",
                "missing_criteria": [],
            }

    async def screen(self, request: ScreenRequest) -> ScreenResponse:
        started_at = time.perf_counter()
        before_cache = self.cache.stats()
        criteria_data = request.model_dump(exclude={"tickers", "weights"}, exclude_none=True)
        tasks = {
            asyncio.create_task(self._analyze_one(ticker, request, criteria_data)): ticker
            for ticker in request.tickers
        }
        done, pending = await asyncio.wait(
            tasks,
            timeout=settings.scan_timeout_seconds,
        )

        by_ticker: dict[str, dict[str, Any]] = {}
        for task in done:
            result = task.result()
            by_ticker[result["ticker"]] = result
        for task in pending:
            ticker = tasks[task]
            task.cancel()
            by_ticker[ticker] = {
                "kind": "unavailable",
                "ticker": ticker,
                "status": "error",
                "reason": "Stock scan timed out",
                "missing_criteria": [],
            }
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        matching, rejected, unavailable = [], [], []
        for ticker in request.tickers:
            result = by_ticker[ticker]
            kind = result.pop("kind")
            if kind == "matching":
                matching.append(result)
            elif kind == "rejected":
                rejected.append(result)
            else:
                unavailable.append(result)

        elapsed = time.perf_counter() - started_at
        after_cache = self.cache.stats()
        analyzed_count = len(matching) + len(rejected)
        unavailable_count = sum(item["status"] == "insufficient_data" for item in unavailable)
        error_count = sum(item["status"] == "error" for item in unavailable)
        attempted = len(request.tickers)
        failed_count = len(unavailable)
        summary = {
            "total_requested": attempted,
            "successfully_analyzed": analyzed_count,
            "matched": len(matching),
            "rejected": len(rejected),
            "unavailable": unavailable_count,
            "errored": error_count,
        }
        performance = {
            "duration_seconds": round(elapsed, 4),
            "stocks_attempted": attempted,
            "stocks_successfully_analyzed": analyzed_count,
            "stocks_failed": failed_count,
            "average_processing_seconds": round(elapsed / attempted, 6),
            "successful_stocks_per_second": round(analyzed_count / elapsed if elapsed else 0, 4),
            "failure_percentage": round((failed_count / attempted) * 100 if attempted else 0, 2),
            "cache_hits": after_cache["hits"] - before_cache["hits"],
            "cache_misses": after_cache["misses"] - before_cache["misses"],
        }

        return ScreenResponse.model_validate(
            {
                "criteria": ScreeningCriteria(**criteria_data),
                "summary": summary,
                "performance": performance,
                "matching_stocks": matching,
                "rejected_stocks": rejected,
                "unavailable_stocks": unavailable,
            }
        )


screening_service = ScreeningService(finnhub_service, cache_service)
