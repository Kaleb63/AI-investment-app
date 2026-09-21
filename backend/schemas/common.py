import re

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,14}$")


def normalize_ticker(value: str) -> str:
    normalized = value.strip().upper()
    if not TICKER_PATTERN.fullmatch(normalized):
        raise ValueError(f"invalid ticker: {value}")
    return normalized
