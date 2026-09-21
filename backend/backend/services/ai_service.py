import asyncio
import json
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from backend.config import settings
from backend.errors import AppError, ProviderError
from backend.schemas.screen import MatchingStock, ScreeningCriteria


class AIService:
    def __init__(self) -> None:
        self._client = (
            AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        )
        self._semaphore = asyncio.Semaphore(3)

    def _require_client(self) -> AsyncOpenAI:
        if self._client is None:
            raise AppError(
                "openai_not_configured",
                "OPENAI_API_KEY is not configured",
                503,
            )
        return self._client

    async def parse_screening_query(self, query: str) -> ScreeningCriteria:
        client = self._require_client()
        try:
            async with self._semaphore:
                response = await client.responses.parse(
                    model=settings.openai_model,
                    instructions=(
                        "Translate the user's investment preferences into only the "
                        "provided screening fields. Use null for criteria the user did "
                        "not request. Do not choose stocks and do not add facts."
                    ),
                    input=query,
                    text_format=ScreeningCriteria,
                )
            if response.output_parsed is None:
                raise ProviderError(
                    "invalid_ai_criteria",
                    "AI did not return screening criteria",
                    502,
                )
            return ScreeningCriteria.model_validate(response.output_parsed)
        except ValidationError as exc:
            raise ProviderError(
                "invalid_ai_criteria",
                "AI returned screening criteria that failed validation",
                502,
            ) from exc
        except AppError:
            raise
        except Exception as exc:
            raise ProviderError(
                "openai_unavailable",
                "AI criteria interpretation is unavailable",
                502,
            ) from exc

    async def explain_screen_match(
        self,
        stock: MatchingStock,
        criteria: ScreeningCriteria,
    ) -> str:
        client = self._require_client()
        evidence = {
            "ticker": stock.ticker,
            "metrics": stock.metrics.model_dump(by_alias=True),
            "category_scores": stock.score.categories,
            "overall_score": stock.score.overall_score,
            "screening_criteria": criteria.model_dump(exclude_none=True),
            "criteria_passed": stock.passed_criteria,
            "missing_information": [
                key
                for key, value in stock.metrics.model_dump(by_alias=True).items()
                if value is None
            ],
            "major_strengths_and_weaknesses": stock.score.reasons,
        }
        try:
            async with self._semaphore:
                response = await client.responses.create(
                    model=settings.openai_model,
                    instructions=(
                        "Explain concisely why the stock matched. Use only the supplied "
                        "evidence. Mention material missing data. Never invent company "
                        "news, products, management information, future earnings, or "
                        "future prices. Do not recommend buying or selling."
                    ),
                    input=json.dumps(evidence),
                )
            return response.output_text
        except Exception as exc:
            raise ProviderError("openai_unavailable", "AI explanation is unavailable", 502) from exc

    async def explain_portfolio(self, evidence: dict[str, Any]) -> str:
        client = self._require_client()
        try:
            async with self._semaphore:
                response = await client.responses.create(
                    model=settings.openai_model,
                    instructions=(
                        "Explain portfolio concentration, diversification, asset mix, "
                        "and missing information using only the supplied calculations. "
                        "Do not invent holdings or recommend trades."
                    ),
                    input=json.dumps(evidence),
                )
            return response.output_text
        except Exception as exc:
            raise ProviderError(
                "openai_unavailable", "AI portfolio explanation is unavailable", 502
            ) from exc


ai_service = AIService()
