"""Run measured Finnhub screening benchmarks without inventing throughput claims."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.errors import AppError
from backend.schemas.screen import ScreenRequest
from backend.services.screening_service import screening_service
from backend.services.stock_universe_service import stock_universe_service


async def run_benchmark(sizes: list[int]) -> dict[str, Any]:
    largest_size = max(sizes)
    universe = await stock_universe_service.list_symbols(
        asset_type="equity",
        limit=largest_size,
    )
    available_tickers = [item["ticker"] for item in universe["symbols"]]
    runs = []
    for size in sizes:
        if len(available_tickers) < size:
            runs.append(
                {
                    "requested_size": size,
                    "status": "skipped",
                    "reason": f"Only {len(available_tickers)} equities were available",
                }
            )
            continue
        result = await screening_service.screen(ScreenRequest(tickers=available_tickers[:size]))
        runs.append(
            {
                "requested_size": size,
                "status": "completed",
                "summary": result.summary.model_dump(),
                "performance": result.performance.model_dump(),
            }
        )
    return {
        "measured_at": datetime.now(UTC).isoformat(),
        "provider": universe["source"],
        "configuration": {
            "sizes": sizes,
            "note": "Results depend on API plan, provider latency, network, and cache state.",
        },
        "runs": runs,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[10],
        help="Scan sizes, for example: --sizes 10 100 500 1000",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if any(size < 1 for size in args.sizes):
        raise SystemExit("Every benchmark size must be positive")
    try:
        result = asyncio.run(run_benchmark(args.sizes))
    except AppError as exc:
        result = {
            "measured_at": datetime.now(UTC).isoformat(),
            "status": "failed",
            "error": {"code": exc.code, "message": exc.message},
            "configuration": {"sizes": args.sizes},
        }
    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if result.get("status") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
