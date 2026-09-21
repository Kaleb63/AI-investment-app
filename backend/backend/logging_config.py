import logging
import os


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Provider clients may include query strings in request logs. Finnhub places
    # its API token in the query string, so only warnings and errors are allowed.
    for noisy_or_sensitive_logger in ("httpx", "httpcore", "openai"):
        logging.getLogger(noisy_or_sensitive_logger).setLevel(logging.WARNING)
