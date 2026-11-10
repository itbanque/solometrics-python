# Examples

Runnable scripts that use the SDK for everyday reseller tasks. Each one is a single file with `--help`.

```bash
pip install solometrics
export SOLOMETRICS_API_KEY=sr_live_...   # https://www.sneakers.itbanque.com/account → API Keys
python examples/01_compare_markets.py DZ5485-612
```

| Script | What it does | Plan |
|---|---|---|
| [01_compare_markets.py](#01-stockx-vs-goat-per-size) | StockX vs GOAT prices per size, with the cheaper market marked | market data |
| [02_retail_arbitrage.py](#02-retail-pairs-worth-flipping) | In-stock retail pairs whose StockX payout beats the retail price | data |
| [03_reprice_listings.py](#03-undercut-the-lowest-ask-with-a-cost-floor) | Undercut the lowest ask on your listings, never below cost + margin | basic |
| [04_bulk_upload.py](#04-bulk-listing-from-a-csv) | Validate a CSV, list it in bulk, follow progress, report misses | advanced |
| [05_sales_report.py](#05-sales-report) | Revenue, trend, top products and order statuses, plus a CSV export | advanced |
| [06_restock_timeline.py](#06-restock-timeline) | When a retail SKU went in and out of stock at each store | data |

> **The sample output below comes from made-up data.** Prices, IDs and sales figures are illustrative; your numbers will differ.

## 01. StockX vs GOAT per size

[`01_compare_markets.py`](01_compare_markets.py) fetches several styles concurrently with `AsyncClient` and puts both markets side by side. Without a linked GOAT account it shows StockX only.

```console
$ python examples/01_compare_markets.py DZ5485-612 U9060JBR
DZ5485-612  (StockX quotes as of 2026-11-10T14:32:07Z)
  size |   SX ask   SX bid | GOAT ask | cheapest
     7 |      318      262 |      309 | GOAT (-9)
     8 |      296      251 |      301 | StockX (-5)
   8.5 |      289      248 |      294 | StockX (-5)
     9 |      281      240 |      272 | GOAT (-9)
   9.5 |      276      238 |      280 | StockX (-4)
    10 |      268      231 |      275 | StockX (-7)
  10.5 |      271      229 |      262 | GOAT (-9)
    11 |      284      236 |      291 | StockX (-7)
    12 |      305      247 |      299 | GOAT (-6)
    13 |      338        - |        - |
    14 |        -        - |      362 |

U9060JBR  (StockX quotes as of 2026-11-10T14:32:07Z)
  size |   SX ask   SX bid | GOAT ask | cheapest
     8 |      162      131 |      168 | StockX (-6)
     9 |      158      129 |      151 | GOAT (-7)
   9.5 |      171      133 |      166 | GOAT (-5)
    10 |      165      130 |      170 | StockX (-5)
    11 |        -      126 |        - |
```

## 02. Retail pairs worth flipping

[`02_retail_arbitrage.py`](02_retail_arbitrage.py) pages through retail inventory with `inventory.iter_search`, skips sizes that are out of stock everywhere, and looks up each style's StockX lowest ask once. Profit is `lowestAsk × (1 − fee) − retail price`; set `--fee` to your real rate (default 0.12).

```console
$ python examples/02_retail_arbitrage.py --min-profit 30
Scanned 9 SKUs across 4 styles; 6 worth flipping:

FV5029-141     9.0  DICKS      retail   99.97  ask  214.00  profit   88.35  [TX-0320]
DZ5485-612    11.0  DICKS      retail  180.00  ask  284.00  profit   69.92  [NJ-0233]
DZ5485-612    10.0  DICKS      retail  180.00  ask  268.00  profit   55.84  [PA-0412, OH-0178]
FV5029-141    10.0  DICKS      retail  125.00  ask  205.00  profit   55.40  [TX-0320]
U9060JBR       9.5  FOOTLOCKER retail  109.99  ask  171.00  profit   40.49  [NY-1102, NY-1180, NJ-0907]
U9060JBR      10.0  FOOTLOCKER retail  109.99  ask  165.00  profit   35.21  [NY-1102]
```

## 03. Undercut the lowest ask, with a cost floor

[`03_reprice_listings.py`](03_reprice_listings.py) moves each active listing to `lowestAsk − step`, unless that would go under `cost × (1 + min_margin)`. It only prints the plan; add `--apply` to change prices.

```console
$ python examples/03_reprice_listings.py --step 1 --min-margin 0.10
plan  7c1f9e02  DZ5485-612      9: 289 -> 280  (lowest 281, cost 180)
ok    b83e5a17  DZ5485-612     10: 268 is already the lowest ask
plan  e2d40c6f  DZ5485-612   10.5: 295 -> 270  (lowest 271, cost 180)
hold  4a9b7d31  U9060JBR        9: undercutting 158 would go under the floor 165
plan  0f6c2e84  U9060JBR       10: 179 -> 164  (lowest 165, cost 125)
skip  9d5e1b70  FV5029-141     10: no cost record, can't compute a floor

would reprice 3, left 3 unchanged  (re-run with --apply)
```

`plan` = would reprice, `ok` = already the lowest ask, `hold` = the floor stops it, `skip` = no cost record or no quote.

## 04. Bulk listing from a CSV

[`04_bulk_upload.py`](04_bulk_upload.py) validates the file, starts the job, prints progress through `wait_for_upload(on_progress=...)`, and lists the rows that matched no StockX variant. Columns are `sku, size, quantity, amount, cost`; see [`data/listings.sample.csv`](data/listings.sample.csv). Run with `--validate-only` first: the real run places asks.

```console
$ python examples/04_bulk_upload.py examples/data/listings.sample.csv
listings.sample.csv: 4 rows, 4 valid, 0 invalid, 0 duplicates
Started job 3f8e2a91-6c04-4b7d-a1e5-c09d72b84f16 (4 rows)
  [PENDING]
  [STARTED] total=4  listed=2  failed=0
  [STARTED] total=4  listed=3  failed=0
  [SUCCESS] total=4  listed=3  failed=1
Job finished: SUCCESS

Unmatched rows (1), not listed:
  {'sku': 'U9060JBR', 'size': '9.5', 'reason': 'size not found'}
```

## 05. Sales report

[`05_sales_report.py`](05_sales_report.py) reads `orders.analytics` for a date range and writes every order in it to CSV with `orders.iter_list`. Add `--sync` to pull fresh orders from StockX first.

```console
$ python examples/05_sales_report.py --from 2026-09-01 --to 2026-11-10 --granularity monthly --csv orders.csv
Sales 2026-09-01 .. 2026-11-10
  orders 47   revenue 11,284.00   avg payout 240.09   fees 1,365.40

Monthly revenue
  2026-09        11 pairs    2,512.00  ################
  2026-10        19 pairs    4,630.00  ##############################
  2026-11        17 pairs    4,142.00  ###########################

Top products
    14 x Jordan 1 Retro High OG Chicago Lost and Found         3,906.00
    12 x New Balance 9060 Sea Salt                             1,908.00
     9 x Nike Dunk Low Retro White Black Panda                 1,035.00
     7 x Jordan 4 Retro White Cement (2025)                    2,338.00
     5 x Nike Air Max 1 '86 OG Big Bubble                        897.00

By status
  COMPLETED                41
  AUTHENTICATING           3
  SHIPPED                  2
  CANCELED                 1

Wrote 47 orders to orders.csv
```

## 06. Restock timeline

[`06_restock_timeline.py`](06_restock_timeline.py) turns `inventory.history` into stock-level and price changes per store. Find retailer SKUs with `client.inventory.search(style_color=...)`.

```console
$ python examples/06_restock_timeline.py DICKS 11943996 --days 7
Jordan Air Jordan 1 Retro High OG  DZ5485-612  size 10
8 records since 2026-11-03T14:32:07Z

[OH-0178]
  2026-11-03T07:00Z  start -> LOW
  2026-11-05T11:30Z  LOW -> OOS
  2026-11-09T21:05Z  OOS -> MEDIUM; price 180 -> 144

[PA-0412]
  2026-11-03T07:00Z  start -> OOS
  2026-11-06T07:00Z  OOS -> HIGH
  2026-11-08T09:12Z  HIGH -> MEDIUM
  2026-11-08T16:40Z  price 180 -> 144
  2026-11-09T21:05Z  MEDIUM -> LOW
```

## Notes

- Scripts that read your account use the default StockX connection. For another one, create the client with `Client(connection_id=...)`.
- Fees, margins and size matching are example defaults. Check them against your own account before acting on the numbers.
