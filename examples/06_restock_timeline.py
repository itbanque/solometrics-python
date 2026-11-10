"""Show when a retail SKU went in and out of stock, per store location.

Collapses the raw stock history into level changes, so a restock reads as
``OOS -> HIGH`` with a timestamp, and also reports price changes.

    python examples/06_restock_timeline.py DICKS 11943996 --days 30

Find retailer SKUs with ``client.inventory.search(style_color="...")``.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Dict, List

from solometrics import Client
from solometrics.types import SkuHistoryRecord


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("retailer", help="e.g. DICKS")
    parser.add_argument("retailer_sku", help="the retailer's own SKU id")
    parser.add_argument("--days", type=int, default=7, help="look-back window, max 365 (default 7)")
    args = parser.parse_args()

    with Client() as client:
        data = client.inventory.history(args.retailer, args.retailer_sku, hours=min(args.days * 24, 8760))

    sku = data.get("sku", {})
    print(
        f"{sku.get('brand', '')} {sku.get('model_name', '')}  {sku.get('style_color', '')}  size {sku.get('size', '')}"
    )
    print(f"{data.get('count', 0)} records since {data.get('cutoff_ts', '?')}\n")

    # history is newest first; walk it oldest first and keep only changes
    by_location: Dict[str, List[SkuHistoryRecord]] = defaultdict(list)
    for rec in reversed(data.get("history", [])):
        by_location[rec.get("location", "?")].append(rec)

    for location, records in sorted(by_location.items()):
        print(f"[{location}]")
        prev_level = prev_price = None
        for rec in records:
            level, price = rec.get("stock_level"), rec.get("price")
            notes = []
            if level != prev_level:
                notes.append(f"{prev_level or 'start'} -> {level}")
            if price is not None and price != prev_price and prev_price is not None:
                notes.append(f"price {prev_price:g} -> {price:g}")
            if notes:
                print(f"  {rec.get('record_created_at', '')}  {'; '.join(notes)}")
            prev_level, prev_price = level, price if price is not None else prev_price
        print()

    if data.get("has_more"):
        print("(more history exists than was returned; narrow --days)")


if __name__ == "__main__":
    main()
