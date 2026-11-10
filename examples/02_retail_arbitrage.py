"""Find in-stock retail pairs that resell on StockX for a profit.

Walks the retail inventory (filtered by brand / retailer / style), skips sizes
that are out of stock everywhere, looks up the StockX lowest ask for each
style once, and prints the pairs whose estimated payout beats the retail price.

    python examples/02_retail_arbitrage.py --brand Jordan --retailer DICKS --min-profit 40

Payout is estimated as ``lowestAsk * (1 - fee)``; set ``--fee`` to your real
StockX seller fee + payment processing rate.
"""

from __future__ import annotations

import argparse
from typing import Dict, List, Optional, Tuple

from solometrics import Client, NotFoundError
from solometrics.types import InventoryItem, MarketSearchResponse

IN_STOCK = {"HIGH", "MEDIUM", "LOW", "IN_STOCK"}


def normalize_size(size: str) -> str:
    """Retailers and StockX may write sizes differently ("10.0" vs "10")."""
    s = size.strip().upper().removeprefix("US ").removeprefix("M ")
    try:
        return f"{float(s):g}"
    except ValueError:
        return s


def lowest_asks(quotes: MarketSearchResponse) -> Dict[str, float]:
    """{normalized size: lowest ask} for the sizes that have an ask."""
    out: Dict[str, float] = {}
    for v in quotes.get("variants", []):
        ask = v.get("lowestAsk")
        if ask is not None:
            out[normalize_size(v["size"])] = ask
    return out


def stocked_locations(item: InventoryItem) -> List[str]:
    return [loc["location_code"] for loc in item.get("inventory", []) if loc.get("stock_level") in IN_STOCK]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--brand")
    parser.add_argument("--retailer")
    parser.add_argument("--style", help="style color, partial match (e.g. DZ5485)")
    parser.add_argument("--fee", type=float, default=0.12, help="StockX fee + processing as a fraction (default 0.12)")
    parser.add_argument("--min-profit", type=float, default=20, help="only show pairs above this profit (default 20)")
    parser.add_argument("--max-skus", type=int, default=500, help="stop after scanning this many SKUs (default 500)")
    args = parser.parse_args()

    # style code -> {normalized size -> lowest ask}; one market lookup per style
    asks: Dict[str, Optional[Dict[str, float]]] = {}
    deals: List[Tuple[float, str]] = []

    with Client() as client:
        items = client.inventory.iter_search(
            brand=args.brand, retailer=args.retailer, style_color=args.style, page_size=100
        )
        scanned = 0
        for item in items:
            if scanned >= args.max_skus:
                break
            scanned += 1
            sku, product = item.get("sku", {}), item.get("product", {})
            price, style = sku.get("price"), product.get("style_color")
            if not price or not style or not stocked_locations(item):
                continue

            if style not in asks:
                try:
                    quotes = client.stockx.market.search(style)
                    asks[style] = lowest_asks(quotes)
                except NotFoundError:
                    asks[style] = None  # not on StockX
            ask = (asks[style] or {}).get(normalize_size(sku.get("size", "")))
            if ask is None:
                continue

            profit = ask * (1 - args.fee) - price
            if profit >= args.min_profit:
                where = ", ".join(stocked_locations(item)[:3])
                line = (
                    f"{style:<12} {sku.get('size', ''):>5}  {sku.get('retailer', ''):<10} "
                    f"retail {price:>7.2f}  ask {ask:>7.2f}  profit {profit:>7.2f}  [{where}]"
                )
                deals.append((profit, line))

    print(f"Scanned {scanned} SKUs across {len(asks)} styles; {len(deals)} worth flipping:\n")
    for _, line in sorted(deals, reverse=True):
        print(line)


if __name__ == "__main__":
    main()
