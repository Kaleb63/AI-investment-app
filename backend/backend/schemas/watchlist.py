from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from backend.schemas.common import normalize_ticker


class WatchlistCreate(BaseModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        return normalize_ticker(value)


class WatchlistResponse(BaseModel):
    id: str
    ticker: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
