"""Undercut the lowest ask on your active StockX listings, never below a cost floor.

For each ACTIVE listing: if someone else is asking less than you, move your
price to ``lowestAsk - step``, unless that is below ``cost * (1 + min_margin)``,
in which case the listing keeps its price. Listings with no cost record are
left alone.

Dry run by default; it only prints the plan. Add ``--apply`` to reprice.

    python examples/03_reprice_listings.py --style DZ5485-612
    python examples/03_reprice_listings.py --step 1 --min-margin 0.15 --apply
"""

from __future__ import annotations

import argparse
import math
from typing import Any, Dict, Iterator, Optional

from solometrics import APIStatusError, Client, NotFoundError
from solometrics.types import MarketSearchResponse


def iter_active_listings(client: Client, style: Optional[str]) -> Iterator[Dict[str, Any]]:
    page = 1
    while True:
        data = client.stockx.listings.list(page_number=page, page_size=100, listing_statuses="ACTIVE", sku=style)
        yield from data.get("listings") or []
        if not data.get("hasNextPage"):
            return
        page += 1


def to_float(value: Any) -> Optional[float]:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--style", help="only listings of this style code")
    parser.add_argument("--step", type=float, default=1, help="how far below the lowest ask to go (default 1)")
    parser.add_argument("--min-margin", type=float, default=0.10, help="floor = cost * (1 + this) (default 0.10)")
    parser.add_argument("--apply", action="store_true", help="actually update prices (default: dry run)")
    args = parser.parse_args()

    market_cache: Dict[str, Dict[str, float]] = {}
    changed = skipped = 0

    with Client() as client:
        for listing in iter_active_listings(client, args.style):
            listing_id = listing.get("listingId")
            style = (listing.get("product") or {}).get("styleId")
            size = (listing.get("variant") or {}).get("variantValue")
            amount, cost = to_float(listing.get("amount")), to_float(listing.get("cost"))
            label = f"{str(listing_id)[:8]}  {style:<11} {size:>5}"
            if not (listing_id and style and size and amount):
                continue
            if cost is None:
                print(f"skip  {label}: no cost record, can't compute a floor")
                skipped += 1
                continue

            if style not in market_cache:
                quotes: MarketSearchResponse
                try:
                    quotes = client.stockx.market.search(style)
                except NotFoundError:
                    quotes = {}
                market_cache[style] = {}
                for v in quotes.get("variants", []):
                    ask = v.get("lowestAsk")
                    if ask is not None:
                        market_cache[style][v["size"]] = ask
            lowest = market_cache[style].get(str(size))
            if lowest is None:
                print(f"skip  {label}: no StockX quote for this size")
                skipped += 1
                continue
            if amount <= lowest:
                print(f"ok    {label}: {amount:g} is already the lowest ask")
                skipped += 1
                continue

            floor = math.ceil(cost * (1 + args.min_margin))
            target = math.floor(lowest - args.step)
            if target < floor:  # can't win the lowest ask profitably; keep the current price
                print(f"hold  {label}: undercutting {lowest:g} would go under the floor {floor}")
                skipped += 1
                continue

            print(
                f"{'set ' if args.apply else 'plan'}  {label}: {amount:g} -> {target}  (lowest {lowest:g}, cost {cost:g})"
            )
            if args.apply:
                try:
                    client.stockx.listings.update(listing_id, amount=target)
                except APIStatusError as e:
                    print(f"      failed: {e.status_code} {e.detail}")
                    continue
            changed += 1

    verb = "repriced" if args.apply else "would reprice"
    print(f"\n{verb} {changed}, left {skipped} unchanged" + ("" if args.apply else "  (re-run with --apply)"))


if __name__ == "__main__":
    main()
