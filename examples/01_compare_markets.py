"""Compare StockX and GOAT prices size by size, for several styles at once.

Fetches both markets concurrently with ``AsyncClient`` and prints, per size, the
StockX lowest ask / highest bid next to the GOAT lowest ask, marking the
cheaper place to buy.

    export SOLOMETRICS_API_KEY=sr_live_...
    python examples/01_compare_markets.py DZ5485-612 U9060JBR

GOAT prices need a linked GOAT account; without one the script shows StockX only.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Dict, List, Optional, Tuple

from solometrics import AsyncClient, ConflictError, PermissionDeniedError, SolometricsError
from solometrics.types import MarketSearchResponse, MarketVariant


def by_size(quotes: Optional[MarketSearchResponse]) -> Dict[str, MarketVariant]:
    return {v["size"]: v for v in (quotes or {}).get("variants", [])}


def fmt(price: Optional[float]) -> str:
    return "-" if price is None else f"{price:,.0f}"


def size_key(size: str) -> Tuple[int, float, str]:
    """Sort "4", "10", "10.5", "W 8" in a human order."""
    digits = "".join(c for c in size if c.isdigit() or c == ".")
    try:
        return (0, float(digits), size)
    except ValueError:
        return (1, 0.0, size)


async def goat_or_none(client: AsyncClient, style_id: str) -> Optional[MarketSearchResponse]:
    try:
        return await client.goat.market.search(style_id)
    except (ConflictError, PermissionDeniedError):
        return None  # no linked GOAT account / not in plan: StockX only


async def compare(client: AsyncClient, style_id: str, sem: asyncio.Semaphore) -> None:
    async with sem:
        try:
            stockx, goat = await asyncio.gather(
                client.stockx.market.search(style_id),
                goat_or_none(client, style_id),
            )
        except SolometricsError as e:
            print(f"\n{style_id}: lookup failed: {e}")
            return

    sx, gt = by_size(stockx), by_size(goat)
    print(f"\n{style_id}  (StockX quotes as of {stockx.get('fetched_at', '?')})")
    print(f"{'size':>6} | {'SX ask':>8} {'SX bid':>8} | {'GOAT ask':>8} | cheapest")
    rows: List[str] = []
    for size in sorted(set(sx) | set(gt), key=size_key):
        sx_ask = sx.get(size, {}).get("lowestAsk")
        sx_bid = sx.get(size, {}).get("highestBid")
        gt_ask = gt.get(size, {}).get("lowestAsk")
        best = ""
        if sx_ask is not None and gt_ask is not None:
            best = "StockX" if sx_ask <= gt_ask else "GOAT"
            best += f" (-{abs(sx_ask - gt_ask):,.0f})"
        rows.append(f"{size:>6} | {fmt(sx_ask):>8} {fmt(sx_bid):>8} | {fmt(gt_ask):>8} | {best}")
    print("\n".join(rows) or "   no sizes quoted")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("styles", nargs="+", help="style codes, e.g. DZ5485-612")
    parser.add_argument("--concurrency", type=int, default=4, help="styles fetched in parallel (default 4)")
    args = parser.parse_args()

    sem = asyncio.Semaphore(args.concurrency)
    async with AsyncClient() as client:
        await asyncio.gather(*(compare(client, s, sem) for s in args.styles))


if __name__ == "__main__":
    asyncio.run(main())
