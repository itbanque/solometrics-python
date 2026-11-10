# 示例

[English](README.md) | **简体中文**

用 SDK 完成日常倒卖工作的可运行脚本。每个脚本都是单个文件，支持 `--help`。

```bash
pip install solometrics
export SOLOMETRICS_API_KEY=sr_live_...   # 在 https://www.sneakers.itbanque.com/account → API Keys 生成
python examples/01_compare_markets.py DZ5485-612
```

| 脚本 | 用途 | 套餐（plan） |
|---|---|---|
| [01_compare_markets.py](#01-stockx-与-goat-分尺码比价) | StockX 与 GOAT 分尺码比价，标出更便宜的平台 | market data |
| [02_retail_arbitrage.py](#02-找出值得倒卖的零售鞋款) | 找出有货、且在 StockX 卖出到手价高于零售价的鞋 | data |
| [03_reprice_listings.py](#03-压低价抢最低卖价但不低于成本底线) | 把你的挂单压到比最低卖价更低，但绝不低于成本加利润 | basic |
| [04_bulk_upload.py](#04-用-csv-批量挂单) | 校验 CSV、批量挂单、跟踪进度、报告未匹配的行 | advanced |
| [05_sales_report.py](#05-销售报表) | 销售额、趋势、热卖商品和订单状态，可导出 CSV | advanced |
| [06_restock_timeline.py](#06-补货时间线) | 某个零售 SKU 在各门店何时断货、何时补货 | data |

> **下面的示例输出来自虚构数据。** 价格、ID 和销售数字仅作演示，你的实际结果会不同。

## 01. StockX 与 GOAT 分尺码比价

[`01_compare_markets.py`](01_compare_markets.py) 用 `AsyncClient` 并发查询多个款号，把两个平台的价格并排列出。没有绑定 GOAT 账户时只显示 StockX。

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

## 02. 找出值得倒卖的零售鞋款

[`02_retail_arbitrage.py`](02_retail_arbitrage.py) 用 `inventory.iter_search` 逐页遍历零售库存，跳过所有门店都缺货的尺码，每个款号只查一次 StockX 最低卖价。利润 = `lowestAsk × (1 − fee) − 零售价`；用 `--fee` 设成你实际的费率（默认 0.12）。

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

## 03. 压低价抢最低卖价，但不低于成本底线

[`03_reprice_listings.py`](03_reprice_listings.py) 把每个在售挂单改到 `lowestAsk − step`，除非这会低于 `cost × (1 + min_margin)`。默认只打印计划，加 `--apply` 才会真正改价。

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

`plan` = 将会改价，`ok` = 已经是最低卖价，`hold` = 受成本底线限制不改，`skip` = 没有成本记录或没有报价。

## 04. 用 CSV 批量挂单

[`04_bulk_upload.py`](04_bulk_upload.py) 先校验文件，再启动任务，通过 `wait_for_upload(on_progress=...)` 打印进度，最后列出没匹配到 StockX variant 的行。CSV 列为 `sku, size, quantity, amount, cost`，参考 [`data/listings.sample.csv`](data/listings.sample.csv)。请先用 `--validate-only` 跑一遍：正式运行会真的挂单。

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

## 05. 销售报表

[`05_sales_report.py`](05_sales_report.py) 读取指定日期范围的 `orders.analytics`，并用 `orders.iter_list` 把范围内所有订单写入 CSV。加 `--sync` 会先从 StockX 拉取最新订单。

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

## 06. 补货时间线

[`06_restock_timeline.py`](06_restock_timeline.py) 把 `inventory.history` 整理成每个门店的库存等级变化和价格变化。零售商 SKU 可以用 `client.inventory.search(style_color=...)` 查到。

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

## 说明

- 读取账户数据的脚本使用默认的 StockX 账户。要用其他账户，创建客户端时传 `Client(connection_id=...)`。
- 费率、利润率和尺码匹配规则都是示例默认值。根据这些数字操作之前，请先对照你自己的账户核实。
