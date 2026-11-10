"""Monthly-style sales report from your synced StockX orders, plus a CSV export.

Prints totals, the sales trend and top sellers for a date range, and writes
every order in that range to a CSV you can open in a spreadsheet.

    python examples/05_sales_report.py --from 2026-01-01 --to 2026-06-30 --csv orders.csv
    python examples/05_sales_report.py --sync      # pull fresh orders from StockX first

Requires the advanced plan.
"""

from __future__ import annotations

import argparse
import csv
import time
from datetime import date, timedelta

from solometrics import Client

ORDER_COLUMNS = [
    "order_number",
    "order_created_at",
    "status",
    "style_id",
    "product_name",
    "variant_value",
    "sale_price",
    "total_payout",
    "total_adjustments",
    "payout_currency",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="from_date", default=str(date.today() - timedelta(days=90)))
    parser.add_argument("--to", dest="to_date", default=str(date.today()))
    parser.add_argument("--granularity", choices=["daily", "weekly", "monthly"], default="weekly")
    parser.add_argument("--csv", help="also export the orders to this file")
    parser.add_argument("--sync", action="store_true", help="start an order sync and wait a bit before reporting")
    args = parser.parse_args()

    with Client() as client:
        if args.sync:
            client.stockx.orders.sync()
            # The sync runs in the background and has no status endpoint.
            print("Order sync started; waiting 30s for it to catch up...")
            time.sleep(30)

        stats = client.stockx.orders.analytics(
            from_date=args.from_date, to_date=args.to_date, granularity=args.granularity
        )
        s = stats.get("summary", {})
        print(f"Sales {args.from_date} .. {args.to_date}")
        print(
            f"  orders {s.get('total_orders', 0)}   revenue {s.get('total_revenue', 0):,.2f}   "
            f"avg payout {s.get('avg_payout', 0):,.2f}   fees {s.get('total_fees', 0):,.2f}"
        )

        trend = stats.get("sales_trend", [])
        if trend:
            peak = max(p.get("revenue", 0) for p in trend) or 1
            print(f"\n{args.granularity.capitalize()} revenue")
            for p in trend:
                bar = "#" * round(30 * p.get("revenue", 0) / peak)
                print(f"  {p.get('period', ''):<12} {p.get('units', 0):>4} pairs {p.get('revenue', 0):>11,.2f}  {bar}")

        print("\nTop products")
        for t in stats.get("top_products", [])[:10]:
            print(
                f"  {t.get('units_sold', 0):>4} x {t.get('product_name', '')[:50]:<50} {t.get('total_revenue', 0):>11,.2f}"
            )

        print("\nBy status")
        for b in stats.get("status_breakdown", []):
            print(f"  {b.get('status', ''):<24} {b.get('count', 0)}")

        if args.csv:
            n = 0
            with open(args.csv, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=ORDER_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                for order in client.stockx.orders.iter_list(from_date=args.from_date, to_date=args.to_date):
                    writer.writerow(order)
                    n += 1
            print(f"\nWrote {n} orders to {args.csv}")


if __name__ == "__main__":
    main()
