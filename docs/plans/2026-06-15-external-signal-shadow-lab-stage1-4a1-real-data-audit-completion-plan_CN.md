# External Signal Shadow Lab Stage 1.4A.1 Real Data Audit Completion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task.

**Goal:** 把 Stage 1.4A 从 `fixture_smoke_only` 推进到真实数据可行性审计：用 Binance Vision `daily/metrics` 补足 OI history，用 Binance public REST 分页补足 funding / futures klines，用本地 forceOrder archive 或 manifest audit 补 liquidation source 语义，最后生成非 fixture 的 Stage 1.4A review。

**Architecture:** 继续沿用 Stage 1.4A 的 source-specific audit 架构，不进入 Stage 1.4B replay。新增一个 Binance Vision OI metrics downloader/converter；增强 live public readonly probe 的分页能力；修正 local archive symbol normalization；把 Binance Vision liquidationSnapshot manifest 当作 manifest availability 审计对象，而不是伪造 liquidation event row。所有阈值仍集中在 `configs/base.py`。

**Tech Stack:** Python 3.11、标准库、pytest、ruff、现有 `configs/base.py`、Binance public REST、Binance Vision public ZIP。

---

## 审核后决策

```text
decision = approved_with_required_fixes
scope = stage1_4a1_real_data_audit_completion
stage1_4b_candidate_replay_allowed = false_by_default
forward_return_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
```

执行前必须修入本计划的防假审计约束：

```text
1. Binance Vision metrics interval 必须从 rows 推断，不能假设 hourly / 5m。
2. metrics create_time 必须按 UTC 解析。
3. data/external_signal_shadow/derivatives_stress/ 必须被 .gitignore 忽略。
4. funding pagination 必须去重、排序、过滤 end_ms 之后记录，并防 stall。
5. futures klines pagination/parser 必须处理 malformed rows、duplicate open_time、interval mismatch。
6. local forceOrder archive 必须兼容 flat 和 Binance nested o.* payload。
7. liquidation manifest audit 必须审计 date-range coverage，不只是单个 HEAD 成功。
8. review 必须输出 per-symbol / per-source blocker table。
```

额外工程约束：

```text
ruff: 禁止使用单字母变量 l，liquidation audit 变量命名必须用 liq 或 liquidation_audit。
ops: rsync 远程同步需要 SSH 凭证，必须由用户手动执行，AI agent 不得自动运行。
rate limit: public REST / Binance Vision 下载必须使用 EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC 做 polite delay。
```

---

## 0. 硬边界

本计划仍然只做 Stage 1.4A 数据可行性审计，不做策略、不做收益、不做 replay。

禁止实现：

```text
long_liquidation_exhaustion_reversal
short_liquidation_exhaustion_reversal
liquidation_trend_continuation
funding_oi_crowding_unwind
Stage 1.4B candidate replay
```

禁止计算：

```text
forward return
MFE / MAE
PnL
hit rate
random baseline
alpha score
```

禁止接入：

```text
API key
.env
private endpoint
account / order / position private data
paper trading
live trading
execution intent
wallet payload
```

所有 real network 行为必须显式参数触发：

```bash
--live-public-readonly
```

所有 Binance Vision 下载也必须是 public readonly，不读取环境变量、不读取 secrets。

---

## 1. 这份补丁计划是否包含上一轮提出的事项

必须包含，且优先级如下：

```text
P0: 新增 Binance Vision daily/metrics OI downloader/converter
P1: 修 live probe 分页：funding + futures klines 拉满 >=90d
P2: 修 local archive symbol normalization
P3: 修 liquidation manifest audit，不把 manifest 当事件 row
P4: 跑一次 --live-public-readonly，得到真实 public-only 结论
P5: 如本地服务器 liquidation archive 已同步，再跑 mixed audit
```

注意：`--live-public-readonly` 的真实 public-only 结论大概率仍是 `stage1_4_data_degraded`，因为 liquidation 可能只有 CM manifest proxy，不是 USD-M complete tape。这不是失败，是真实可行性审计结论。

---

## 2. Source 事实与语义约束

### 2.1 OI 数据源

不要使用以下路径作为主实现：

```text
data/futures/um/monthly/openInterest/
data/futures/um/daily/openInterest/
```

实测这些路径对样例 `BTCUSDT 2024-01` 返回 404。

应使用：

```text
data/futures/um/daily/metrics/{SYMBOL}/{SYMBOL}-metrics-{YYYY-MM-DD}.zip
```

该 CSV 包含：

```csv
create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio
```

转换目标 JSONL schema：

```json
{
  "symbol": "BTCUSDT",
  "sumOpenInterest": "74006.26600000",
  "sumOpenInterestValue": "3131493738.89740000",
  "timestamp": 1704067200000,
  "source": "binance_vision_um_daily_metrics",
  "source_file": "BTCUSDT-metrics-2024-01-01.zip"
}
```

注意：

```text
Binance Vision metrics 是 daily ZIP file，但 ZIP 内 CSV 的行频率必须从实际 timestamp delta 推断。
不要假设每小时一行，也不要假设每 5m 一行。
OI audit 的 expected_bucket_count 必须基于 inferred interval。
```

`create_time` 必须用 UTC timezone-aware 解析：

```python
datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
```

禁止使用 naive `datetime.timestamp()`，否则在非 UTC 机器上会发生时区偏移。

### 2.2 Funding 数据源

使用 Binance public REST：

```text
/fapi/v1/fundingRate
```

必须分页覆盖至少 `EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN = 90` 天，preferred 为 180 天。不能再只取 `limit=100`。

### 2.3 Futures price 数据源

使用 Binance USD-M futures klines：

```text
/fapi/v1/klines
interval=15m
```

必须分页覆盖至少 90 天。

### 2.4 Liquidation 数据源

第一版支持两类：

```text
A. local forceOrder archive：可作为 force_order_archive proxy
B. Binance Vision CM liquidationSnapshot manifest：只能作为 manifest availability / CM proxy audit
```

manifest HEAD 成功不能构造 synthetic liquidation row。禁止再写入：

```json
{"side":"SELL","price":50000.0,"qty":1.0,"time":...}
```

正确做法是记录：

```json
{
  "symbol": "BTCUSD_PERP",
  "um_symbol": "BTCUSDT",
  "manifest_url": "...",
  "manifest_available": true,
  "source_quality": "cm_liquidation_snapshot_manifest_only",
  "cm_to_um_proxy_used": true,
  "notional_conversion_quality": "unavailable"
}
```

manifest-only 不允许 full composite replay。

---

## 3. Task 1：补配置常量

**Files:**

- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a_config.py`

**Step 1: 写失败测试**

在 `tests/research/external_signal_shadow/test_stage1_4a_config.py` 增加：

```python
def test_stage1_4a1_binance_vision_metrics_config_exists():
    from configs import base

    assert base.EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_METRICS_DAILY_PATH_TEMPLATE == (
        "/data/futures/um/daily/metrics/{symbol}/{symbol}-metrics-{date}.zip"
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_OI_OUTPUT_JSONL.endswith(".jsonl")
    assert base.EXTERNAL_SIGNAL_STAGE1_4_PUBLIC_REST_PAGE_LIMIT > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_4_PUBLIC_REST_PAGE_LIMIT <= 1500
```

**Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_config.py::test_stage1_4a1_binance_vision_metrics_config_exists -q
```

Expected: FAIL，常量不存在。

**Step 3: 实现最小配置**

在 `configs/base.py` Stage 1.4 区域增加带注释常量：

```python
# Binance Vision daily metrics ZIP path template for USD-M futures OI archive.
# This is the public historical source for sum_open_interest and sum_open_interest_value.
EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_METRICS_DAILY_PATH_TEMPLATE = (
    "/data/futures/um/daily/metrics/{symbol}/{symbol}-metrics-{date}.zip"
)

# Local JSONL output path for converted Binance Vision metrics OI rows.
# Runtime data should remain ignored by git unless explicitly reviewed.
EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_OI_OUTPUT_JSONL = (
    "data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl"
)

# Public REST page limit used by Stage 1.4A funding/price historical probes.
# Safe range: 500-1500; do not exceed Binance endpoint limits.
EXTERNAL_SIGNAL_STAGE1_4_PUBLIC_REST_PAGE_LIMIT = 1000

# Preferred Stage 1.4A real audit history window.
# Must be >= EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN.
EXTERNAL_SIGNAL_STAGE1_4_REAL_AUDIT_HISTORY_DAYS = 180
```

**Step 4: 跑测试确认通过**

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_config.py -q
```

Expected: PASS。

---

## 3.5 Task 1.5：确认 derivatives_stress runtime data 被 gitignore

**Files:**

- Modify if needed: `.gitignore`
- Check: shell command

**Step 1: 检查 runtime path 是否被忽略**

```bash
git check-ignore data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl
```

Expected: exit `0`，输出该路径。

**Step 2: 如果未被忽略，追加规则**

在 `.gitignore` 追加：

```gitignore
data/external_signal_shadow/derivatives_stress/
```

**Step 3: 复查**

```bash
git check-ignore data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl
```

Expected: exit `0`。

---

## 4. Task 2：实现 Binance Vision daily metrics OI downloader/converter

**Files:**

- Create: `scripts/external_signal_shadow/build_stage1_4a_binance_vision_oi_metrics_archive.py`
- Test: `tests/scripts/external_signal_shadow/test_build_stage1_4a_binance_vision_oi_metrics_archive.py`

**Step 1: 写失败测试：URL 构造使用 daily metrics，不使用 openInterest**

```python
def test_build_metrics_url_uses_daily_metrics_path():
    from scripts.external_signal_shadow.build_stage1_4a_binance_vision_oi_metrics_archive import build_metrics_zip_url

    url = build_metrics_zip_url(
        base_url="https://data.binance.vision",
        symbol="BTCUSDT",
        date_str="2024-01-01",
    )

    assert "/data/futures/um/daily/metrics/BTCUSDT/" in url
    assert "BTCUSDT-metrics-2024-01-01.zip" in url
    assert "openInterest" not in url
```

**Step 2: 写失败测试：CSV 转 JSONL schema**

```python
def test_convert_metrics_csv_rows_to_stage1_4_oi_rows():
    from scripts.external_signal_shadow.build_stage1_4a_binance_vision_oi_metrics_archive import convert_metrics_csv_line

    header = "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio"
    line = "2024-01-01 00:00:00,BTCUSDT,74006.26600000,3131493738.89740000,1.36,1.25,1.50,1.31"

    row = convert_metrics_csv_line(header.split(","), line.split(","), source_file="BTCUSDT-metrics-2024-01-01.zip")

    assert row["symbol"] == "BTCUSDT"
    assert row["sumOpenInterest"] == "74006.26600000"
    assert row["sumOpenInterestValue"] == "3131493738.89740000"
    assert row["timestamp"] == 1704067200000
    assert row["source"] == "binance_vision_um_daily_metrics"
```

**Step 3: 写失败测试：create_time 必须按 UTC 解析**

```python
def test_metrics_create_time_parsed_as_utc_ms():
    from scripts.external_signal_shadow.build_stage1_4a_binance_vision_oi_metrics_archive import parse_metrics_create_time_ms

    assert parse_metrics_create_time_ms("2024-01-01 00:00:00") == 1704067200000
```

实现必须使用 `timezone.utc`，不能依赖本地时区。

**Step 4: 写失败测试：interval 必须从 rows 推断**

```python
def test_metrics_interval_inferred_from_rows():
    from scripts.external_signal_shadow.build_stage1_4a_binance_vision_oi_metrics_archive import infer_interval_ms

    rows = [
        {"timestamp": 1704067200000},
        {"timestamp": 1704067500000},
        {"timestamp": 1704067800000},
    ]

    assert infer_interval_ms(rows) == 300_000
```

该测试只证明可以推断 5m；不要在生产逻辑中写死 5m。

**Step 5: 写失败测试：mock ZIP 输入生成 JSONL**

构造临时 ZIP，里面放一个 CSV。调用 converter，断言输出 JSONL 有行且字段正确。

**Step 6: 跑测试确认失败**

```bash
PYTHONPATH=src uv run pytest tests/scripts/external_signal_shadow/test_build_stage1_4a_binance_vision_oi_metrics_archive.py -q
```

Expected: FAIL，脚本不存在。

**Step 7: 实现脚本**

脚本功能：

```text
--symbols BTCUSDT ETHUSDT SOLUSDT XRPUSDT DOGEUSDT
--days 180
--end-date YYYY-MM-DD，可选，默认 UTC today
--output data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl
--live-public-readonly 必须显式传，否则拒绝联网
--mock-zip-dir tests/fixtures/... 可用于测试
```

实现要求：

- 只用标准库：`urllib.request`, `zipfile`, `csv`, `json`, `datetime`, `time`。
- 不读 `os.environ`。
- 不读 `.env`。
- `create_time` 按 UTC 解析。
- `metrics_interval_ms` 从实际 rows 的 median timestamp delta 推断。
- 下载失败的日包记录到 summary，不 crash。
- 输出 JSONL 按 `symbol,timestamp` 排序。
- 去重键：`symbol + timestamp`。
- 每次下载之间执行 `time.sleep(EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC)`。
- summary 输出：

```json
{
  "source": "binance_vision_um_daily_metrics",
  "requested_symbol_count": 5,
  "requested_days": 180,
  "download_success_count": 0,
  "download_failure_count": 0,
  "row_count": 0,
  "symbol_row_counts": {},
  "history_days_by_symbol": {},
  "inferred_interval_ms_by_symbol": {},
  "duplicate_row_count": 0,
  "malformed_row_count": 0,
  "output_file": "...",
  "live_trading_allowed": false,
  "api_key_used": false
}
```

**Step 8: 跑测试确认通过**

```bash
PYTHONPATH=src uv run pytest tests/scripts/external_signal_shadow/test_build_stage1_4a_binance_vision_oi_metrics_archive.py -q
```

---

## 5. Task 3：修 funding public REST 分页，拉满 >=90d

**Files:**

- Modify: `scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py`

**Step 1: 写失败测试**

```python
def test_live_funding_probe_paginates_requested_history(tmp_path):
    # mock safe_http_get to return two funding pages based on startTime/endTime
    # assert generated request URLs include startTime/endTime and limit=1000
    # assert summary symbol_audits["BTCUSDT"]["funding"]["funding_record_count"] > 100
```

继续补分页边界测试：

```python
def test_funding_pagination_dedupes_and_stops_on_stall(): ...
def test_funding_pagination_filters_records_after_end_ms(): ...
```

**Step 2: 实现分页函数**

建议新增内部函数：

```python
def fetch_funding_history_pages(symbol: str, start_ms: int, end_ms: int) -> list[dict]: ...
```

规则：

- path 使用 `EXTERNAL_SIGNAL_STAGE1_4_FUNDING_RATE_PATH`。
- query 包含 `symbol`, `startTime`, `endTime`, `limit=1000`。
- 每页按返回最大 `fundingTime + 1` 推进。
- 空页停止。
- 返回 rows 可能未排序，必须先按 `fundingTime` 排序。
- 按 `fundingTime` 去重。
- 过滤 `fundingTime > end_ms` 的记录。
- 如果 `next_start <= current_start`，停止并标记 `funding_pagination_stalled = true`，避免死循环。
- 不得无限循环，最多按 `ceil(days * 3 / limit) + reserve` 估计上限。
- 网络错误写 failure summary。
- 每页请求之间执行 `time.sleep(EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC)`。

summary 必须增加：

```json
{
  "funding_pagination_page_count": 0,
  "funding_duplicate_record_count": 0,
  "funding_pagination_stalled": false
}
```

**Step 3: 测试**

```bash
PYTHONPATH=src uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py::test_live_funding_probe_paginates_requested_history -q
```

---

## 6. Task 4：修 futures klines public REST 分页，拉满 >=90d

**Files:**

- Modify: `scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py`

**Step 1: 写失败测试**

```python
def test_live_futures_kline_probe_paginates_requested_history(tmp_path):
    # mock safe_http_get to return multiple /fapi/v1/klines pages
    # assert query includes interval=15m, startTime, endTime, limit=1000
    # assert price audit has price_bar_count > 100
```

继续补 parser 边界测试：

```python
def test_futures_klines_parser_rejects_malformed_rows(): ...
def test_futures_klines_dedupes_open_time(): ...
def test_futures_klines_reports_interval_mismatch(): ...
```

**Step 2: 实现分页函数**

```python
def fetch_futures_kline_pages(symbol: str, start_ms: int, end_ms: int) -> list[list]: ...
```

规则：

- path 使用 `EXTERNAL_SIGNAL_STAGE1_4_FUTURES_KLINES_PATH`。
- `interval=15m`。
- 每页按最后一根 `open_time + interval_ms` 推进。
- 去重 open_time。
- 过滤 `open_time >= end_ms` 的记录。
- Binance kline row 是数组，不是 dict；必须验证至少包含：
  - `open_time`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`
  - `close_time`
  - `quote_asset_volume`
- 验证 `close_time` 与 15m interval 对齐；异常计入 `price_interval_mismatch_count`。
- malformed row 计入 `price_malformed_kline_count`，不得静默当作有效 bar。
- duplicate `open_time` 计入 `price_duplicate_open_time_count`。
- 每页请求之间执行 `time.sleep(EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC)`。
- 输出给 `audit_price_source_rows()`。

summary 必须增加：

```json
{
  "price_malformed_kline_count": 0,
  "price_duplicate_open_time_count": 0,
  "price_interval_mismatch_count": 0
}
```

**Step 3: 测试**

```bash
PYTHONPATH=src uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py::test_live_futures_kline_probe_paginates_requested_history -q
```

---

## 7. Task 5：修 local archive symbol normalization

**Files:**

- Modify: `scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py`

**Context:** 现有 forceOrder / liquidation archive 可能使用 `BTC/USDT`，Stage 1.4A 使用 `BTCUSDT`。不 normalize 会把本地 archive 误判为空。

**Step 1: 写失败测试**

```python
def test_local_force_order_archive_normalizes_ccxt_symbol(tmp_path):
    archive_file = tmp_path / "force_orders.jsonl"
    archive_file.write_text(json.dumps({
        "symbol": "BTC/USDT",
        "side": "SELL",
        "price": 50000.0,
        "origQty": 1.0,
        "time": 1704067200000,
    }) + "\n", encoding="utf-8")

    output = tmp_path / "summary.json"
    rc = main(["--local-force-order-archive", str(archive_file), "--output-summary", str(output)])

    assert rc == 0
    summary = json.loads(output.read_text())
    assert summary["symbol_audits"]["BTCUSDT"]["liquidation"]["liquidation_nonzero_window_count"] == 1
```

继续补 Binance nested `forceOrder` schema 测试：

```python
def test_local_force_order_archive_parses_nested_binance_force_order_payload(tmp_path):
    archive_file = tmp_path / "force_orders.jsonl"
    archive_file.write_text(json.dumps({
        "e": "forceOrder",
        "E": 1704067200123,
        "o": {
            "s": "BTCUSDT",
            "S": "SELL",
            "p": "50000.0",
            "q": "1.0",
            "T": 1704067200000,
        },
    }) + "\n", encoding="utf-8")

    output = tmp_path / "summary.json"
    rc = main(["--local-force-order-archive", str(archive_file), "--output-summary", str(output)])

    assert rc == 0
    summary = json.loads(output.read_text())
    liq = summary["symbol_audits"]["BTCUSDT"]["liquidation"]
    assert liq["long_liquidation_notional"] > 0
    assert liq["liquidation_unknown_schema_count"] == 0
```

**Step 2: 实现 normalize helper**

```python
def normalize_derivatives_symbol(symbol: str) -> str:
    return str(symbol).upper().replace("/", "").replace(":USDT", "")
```

不要过度泛化。第一版只支持：

```text
BTCUSDT
BTC/USDT
BTC/USDT:USDT
```

**Step 3: 同时应用到 local OI archive**

OI archive 也可能有 `BTC/USDT`，同样 normalize。

**Step 4: 支持 flat 与 nested forceOrder payload**

local forceOrder parser 至少支持两种结构：

```text
flat:
  symbol, side, price, origQty, time

nested Binance forceOrder:
  o.s / o.S / o.p / o.q / o.T
```

side 映射必须保持：

```text
SELL -> long_liquidation
BUY  -> short_liquidation
```

无法识别 schema 的行不得静默丢弃，必须计入：

```json
{
  "liquidation_parse_error_count": 0,
  "liquidation_unknown_schema_count": 0
}
```

---

## 8. Task 6：修 liquidation manifest audit，不把 manifest 当事件 row

**Files:**

- Modify: `scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py`
- Modify: `src/research/external_signal_shadow/stage1_4a_liquidation.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a_liquidation.py`

**Step 1: 写失败测试**

```python
def test_manifest_head_success_records_manifest_not_liquidation_event(tmp_path):
    # safe_http_head returns True
    # safe_http_get returns [] for funding/OI/price
    # assert liquidation_field_coverage_ratio == 0.0
    # assert liquidation_manifest_available_count > 0
    # assert liquidation_nonzero_window_count == 0
```

继续补 date-range coverage 测试：

```python
def test_liquidation_manifest_audit_reports_available_days_by_symbol(tmp_path):
    # mock HEAD for BTCUSD_PERP available on 2 of 3 requested dates
    # assert liquidation_manifest_requested_days == 3
    # assert liquidation_manifest_available_days_by_symbol["BTCUSDT"] == 2
    # assert liquidation_manifest_coverage_ratio_by_symbol["BTCUSDT"] == pytest.approx(2 / 3)
```

**Step 2: 实现 manifest audit schema**

在 liquidation audit 中允许 manifest-only block：

```json
{
  "liquidation_source": "binance_vision_cm_liquidation_snapshot_manifest",
  "liquidation_source_quality": "cm_liquidation_snapshot_manifest_only",
  "liquidation_manifest_available_count": 1,
  "liquidation_history_days": 0.0,
  "liquidation_field_coverage_ratio": 0.0,
  "liquidation_time_coverage_ratio": 0.0,
  "liquidation_nonzero_window_count": 0,
  "cm_to_um_proxy_used": true,
  "liquidation_proxy_accepted_for_full_replay": false,
  "notional_conversion_quality": "unavailable"
}
```

**Step 3: 保持 full composite 阻塞**

manifest-only 永远不能让：

```json
"composite_replay_allowed": true
```

**Step 4: manifest audit 必须按 symbol/date 范围统计**

manifest HEAD 成功只证明某一天某个 COIN-M proxy ZIP 存在，不证明 liquidation tape 已下载或解析。
实现必须按 `requested_days × requested_symbols` 生成 date-range probe，并输出：

```json
{
  "liquidation_manifest_requested_days": 180,
  "liquidation_manifest_available_days_by_symbol": {},
  "liquidation_manifest_history_days_by_symbol": {},
  "liquidation_manifest_coverage_ratio_by_symbol": {}
}
```

如果只抽样 HEAD 少数 URL，不得声称 `liquidation_history_days >= 90`。

---

## 9. Task 7：把 Binance Vision OI archive 接入 Stage 1.4A audit

**Files:**

- Modify: `scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py`

**Step 1: 写测试：传入转换后的 OI JSONL 可提升 OI history**

构造临时 JSONL，覆盖 91 天。测试数据可以用 5m 或 1h 间隔，但 assertion 不能写死生产数据频率；audit 必须从 rows 的 timestamp delta 推断 interval。

断言：

```python
summary["symbol_audits"]["BTCUSDT"]["oi"]["oi_history_days"] >= 90
summary["symbol_audits"]["BTCUSDT"]["oi"]["oi_blocks_full_composite"] is False
```

继续补 coverage interval 测试：

```python
def test_oi_time_coverage_uses_inferred_metrics_interval(tmp_path):
    # build rows with 5m interval and one missing bucket
    # assert expected_bucket_count is derived from 300_000ms
    # assert oi_time_coverage_ratio < 1.0
```

**Step 2: 实现读取兼容**

当前 `audit_open_interest_history_rows()` 需要字段：

```text
symbol
sumOpenInterest
sumOpenInterestValue
timestamp
```

确保 converter 输出正好兼容。

**Step 3: OI time coverage 不得使用 fixed hourly assumption**

`audit_open_interest_history_rows()` 必须区分：

```text
oi_field_coverage_ratio = valid_value_rows / total_rows
oi_time_coverage_ratio = actual_unique_timestamp_buckets / expected_bucket_count
```

其中：

```text
interval_ms = median positive delta between sorted timestamps
expected_bucket_count = floor((max_ts - min_ts) / interval_ms) + 1
```

如果 rows 不足以推断 interval，`oi_time_coverage_ratio = 0.0`，并输出 blocker：

```text
oi_interval_unavailable
```

---

## 10. Task 8：真实 public-only audit 命令

**Files:**

- Runtime output: `reports/external_signal_shadow/stage1_4_derivatives_stress_data_feasibility_summary.json`
- Runtime output: `docs/reviews/2026-06-15-external-signal-shadow-lab-stage1-4a1-real-data-audit-review_CN.md`

**Step 1: 下载并转换 OI metrics**

```bash
PYTHONPATH=src uv run python scripts/external_signal_shadow/build_stage1_4a_binance_vision_oi_metrics_archive.py \
  --symbols BTCUSDT ETHUSDT SOLUSDT XRPUSDT DOGEUSDT \
  --days 180 \
  --live-public-readonly \
  --output data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl \
  --output-summary reports/external_signal_shadow/stage1_4a1_binance_vision_oi_metrics_summary.json
```

Expected:

```text
row_count > 0
history_days_by_symbol >= 90 for at least BTC/ETH/SOL if available
api_key_used = false
```

**Step 2: 跑 public-only Stage 1.4A audit**

```bash
PYTHONPATH=src uv run python scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py \
  --live-public-readonly \
  --local-oi-archive 'data/external_signal_shadow/derivatives_stress/oi/*.jsonl' \
  --output-summary reports/external_signal_shadow/stage1_4_derivatives_stress_data_feasibility_summary.json
```

Expected:

```text
fixture_run = false
research_result_valid = true
network_mode = live_public_readonly
OI should no longer be 0 if metrics archive exists
outcome likely stage1_4_data_degraded unless liquidation source passes
funding_pagination_page_count > 0
price_malformed_kline_count is present
price_duplicate_open_time_count is present
```

**Step 3: 生成 review**

```bash
PYTHONPATH=src uv run python scripts/external_signal_shadow/review_stage1_4a_derivatives_stress_data_feasibility.py \
  --summary reports/external_signal_shadow/stage1_4_derivatives_stress_data_feasibility_summary.json \
  --output-review docs/reviews/2026-06-15-external-signal-shadow-lab-stage1-4a1-real-data-audit-review_CN.md
```

---

## 11. Task 9：如服务器 liquidation 已同步，跑 mixed audit

**Files:**

- Runtime input: `data/route_c1_live/trend_regime_force_orders_raw.jsonl`
- Runtime output: `reports/external_signal_shadow/stage1_4a1_mixed_data_feasibility_summary.json`
- Runtime output: `docs/reviews/2026-06-15-external-signal-shadow-lab-stage1-4a1-mixed-data-feasibility-review_CN.md`

**Step 1: 用户手动同步服务器 liquidation archive**

该步骤需要 SSH 凭证，AI agent 不得自动执行。由用户在本地终端手动运行：

```bash
SERVER=root@47.82.4.85
mkdir -p data/route_c1_live
rsync -avzP $SERVER:/root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl ./data/route_c1_live/
rsync -avzP $SERVER:/root/crypto-alpha-lab/data/trend_regime_liquidation_1m.jsonl ./data/route_c1_live/ || true
rsync -avzP $SERVER:/root/crypto-alpha-lab/data/trend_regime_liquidation_hourly.jsonl ./data/route_c1_live/ || true
```

实现要求：

- CLI 必须容忍 `data/route_c1_live/` 不存在。
- `--local-force-order-archive` 指向不存在文件时，不得 crash。
- 缺失本地 archive 时写入 degraded 结论：

```json
{
  "local_force_order_archive_found": false,
  "liquidation_source": "missing",
  "primary_blocker": "local_force_order_archive_missing"
}
```

新增测试：

```python
def test_missing_local_force_order_archive_degrades_without_crash(tmp_path): ...
```

**Step 2: 跑 mixed audit**

```bash
PYTHONPATH=src uv run python scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py \
  --live-public-readonly \
  --local-oi-archive 'data/external_signal_shadow/derivatives_stress/oi/*.jsonl' \
  --local-force-order-archive data/route_c1_live/trend_regime_force_orders_raw.jsonl \
  --output-summary reports/external_signal_shadow/stage1_4a1_mixed_data_feasibility_summary.json
```

**Step 3: 生成 mixed review**

```bash
PYTHONPATH=src uv run python scripts/external_signal_shadow/review_stage1_4a_derivatives_stress_data_feasibility.py \
  --summary reports/external_signal_shadow/stage1_4a1_mixed_data_feasibility_summary.json \
  --output-review docs/reviews/2026-06-15-external-signal-shadow-lab-stage1-4a1-mixed-data-feasibility-review_CN.md
```

**解释规则：**

- 如果 forceOrder archive <90d，full composite 仍不允许。
- 如果 forceOrder coverage 达不到门槛，输出 `data_degraded`。
- 如果 OI/funding/price 都过，但 liquidation archive 不足，只能进入 partial diagnostic，不进入 full Stage 1.4B。

---

## 12. Task 10：Review 文案必须解释 outcome

**Files:**

- Modify: `scripts/external_signal_shadow/review_stage1_4a_derivatives_stress_data_feasibility.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_4a_derivatives_stress_data_feasibility.py`

Review 必须明确区分：

```text
public-only audit
mixed audit with local liquidation archive
fixture smoke
```

Review 必须解释：

```text
为什么 OI 从 Binance Vision metrics 获得，而不是 openInterest 目录
为什么 liquidation manifest-only 不能当成 liquidation event
为什么 forceOrder 是 proxy，不是完整 tape
为什么 data_degraded 可能是正确结论
```

Review 必须输出 per-symbol / per-source blocker table，最低包含：

```text
symbol | funding_days | oi_days | price_days | liquidation_days | blockers | full_composite_usable
```

表格语义：

- `funding_days` / `oi_days` / `price_days` / `liquidation_days` 必须来自真实 audit 字段，不得用占位值。
- `blockers` 必须能说明 `data_degraded` 的来源，例如 `oi_time_coverage_below_min`、`liquidation_archive_missing`、`cm_proxy_unaccepted`。
- `full_composite_usable = Yes` 只允许在 funding / OI / price / liquidation 全部满足 Stage 1.4A 门槛时出现。
- fixture run 必须显示 `research_result_valid = false`。

实现注意：

- 不要使用小写单字母 `l` 作为变量名，避免 Ruff `E741`；使用 `liq` 或 `liquidation_audit`。

新增测试：

```python
def test_review_explains_binance_vision_metrics_oi_source(): ...
def test_review_explains_manifest_only_not_event_data(): ...
def test_review_explains_force_order_proxy_limitations(): ...
def test_review_renders_per_symbol_source_blocker_table(): ...
```

---

## 13. 验证命令

Runtime data ignore check:

```bash
git check-ignore data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl
```

Expected: exit `0` and prints the path.

Focused tests:

```bash
PYTHONPATH=src uv run pytest \
  tests/research/external_signal_shadow/test_stage1_4a_config.py \
  tests/research/external_signal_shadow/test_stage1_4a_coverage.py \
  tests/research/external_signal_shadow/test_stage1_4a_funding.py \
  tests/research/external_signal_shadow/test_stage1_4a_liquidation.py \
  tests/research/external_signal_shadow/test_stage1_4a_oi.py \
  tests/research/external_signal_shadow/test_stage1_4a_orchestrator.py \
  tests/research/external_signal_shadow/test_stage1_4a_price.py \
  tests/research/external_signal_shadow/test_stage1_4a_public_client.py \
  tests/research/external_signal_shadow/test_stage1_4a_summary.py \
  tests/scripts/external_signal_shadow/test_build_stage1_4a_binance_vision_oi_metrics_archive.py \
  tests/scripts/external_signal_shadow/test_review_stage1_4a_derivatives_stress_data_feasibility.py \
  tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py -q
```

External signal suite:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow tests/scripts/external_signal_shadow -q
```

Ruff:

```bash
uv run ruff check src/research/external_signal_shadow scripts/external_signal_shadow tests/research/external_signal_shadow tests/scripts/external_signal_shadow
```

Full pytest:

```bash
PYTHONPATH=src uv run pytest -q
```

---

## 14. 完成标准

Stage 1.4A.1 完成后，必须能给出至少一份非 fixture review：

```json
{
  "fixture_run": false,
  "research_result_valid": true,
  "symbol_audits": {
    "BTCUSDT": {
      "funding": {...},
      "oi": {...},
      "liquidation": {...},
      "price": {...}
    }
  }
}
```

如果 outcome 是 `stage1_4_data_degraded`，也可以算完成，只要 blocker 是真实数据结论，例如：

```text
liquidation_history_insufficient
liquidation_time_coverage_insufficient
cm_proxy_unaccepted
insufficient_preview_density
```

不能算完成的情况：

```text
fixture_smoke_only
symbol_audits = {}
Per-Source table 全 0
review 写 Usable Yes 但没有 source data
```

---

## 15. 最终允许结论

允许输出：

```text
Stage 1.4A.1 real data audit completed.
Funding / OI / price / liquidation source feasibility was audited with public/local data.
Outcome is feasible/degraded/unavailable based on source coverage.
```

禁止输出：

```text
liquidation/funding/OI 有 alpha
可以进入 paper/live
可以交易 derivatives stress event
Stage 1.4B 已通过
```

只有当：

```json
{
  "stage1_4b_candidate_replay_allowed": true,
  "composite_replay_allowed": true
}
```

才允许下一步写 Stage 1.4B candidate replay design。否则只能写 partial diagnostic 或继续补数据源。
