from abc import ABC, abstractmethod
from typing import Any


class BrokerService(ABC):
    """Interface for a future broker that can explicitly support trading."""

    @abstractmethod
    async def get_account(self, user_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_positions(self, user_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def place_order(self, user_id: str, order: dict[str, Any]) -> dict[str, Any]: ...


class UnavailableBrokerService(BrokerService):
    async def get_account(self, user_id: str) -> dict[str, Any]:
        return {"status": "unavailable", "trading_enabled": False}

    async def get_positions(self, user_id: str) -> list[dict[str, Any]]:
        return []

    async def place_order(self, user_id: str, order: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("No trading broker is configured")


broker_service = UnavailableBrokerService()
