"""List many pairs on StockX from a CSV: validate, upload, follow progress, report misses.

The CSV needs the columns ``sku, size, quantity, amount, cost``; see
``examples/data/listings.sample.csv``.

    python examples/04_bulk_upload.py examples/data/listings.sample.csv --validate-only
    python examples/04_bulk_upload.py examples/data/listings.sample.csv

Requires the advanced plan. Listing jobs place real asks; validate first.
"""

from __future__ import annotations

import argparse
import sys

from solometrics import Client, JobTimeoutError
from solometrics.types import JobStatus


def show_progress(status: JobStatus) -> None:
    result = status.get("result") or {}
    counters = "  ".join(f"{k}={v}" for k, v in result.items() if isinstance(v, (int, float, str)))
    print(f"  [{status.get('status')}] {counters}".rstrip(), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", help="path to the listings CSV")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=1800, help="seconds to wait for the job (default 1800)")
    parser.add_argument("--validate-only", action="store_true", help="check the file, list nothing")
    args = parser.parse_args()

    with Client() as client:
        report = client.stockx.listings.validate_upload(args.csv)
        print(
            f"{report.get('filename')}: {report.get('total_rows')} rows, {report.get('valid_rows')} valid, "
            f"{report.get('invalid_rows')} invalid, {report.get('duplicate_rows')} duplicates"
        )
        if report.get("invalid_rows"):
            print("Fix the invalid rows before uploading.")
            return 1
        if args.validate_only:
            return 0

        job = client.stockx.listings.upload(args.csv, batch_size=args.batch_size)
        print(f"Started job {job['taskId']} ({job.get('processedRows')} rows)")

        try:
            final = client.stockx.listings.wait_for_upload(
                job["taskId"], poll_interval=5, timeout=args.timeout, on_progress=show_progress
            )
        except JobTimeoutError:
            print(f"Still running after {args.timeout:.0f}s; check later with upload_status({job['taskId']!r}).")
            return 2

        print(f"Job finished: {final['status']}")
        unmatched = client.stockx.listings.unmatched().get("items") or []
        if unmatched:
            print(f"\nUnmatched rows ({len(unmatched)}), not listed:")
            for row in unmatched:
                print(" ", row)
        return 0 if final["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
