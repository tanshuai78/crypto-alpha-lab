# External Signal Shadow Lab Stage 1.4A Derivatives Stress Data Feasibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Stage 1.4A Derivatives Stress Data Feasibility Audit：用公开只读 live probe 和本地 archive scan 审计 `liquidation + funding + OI + futures price` 数据是否足够支持后续 Stage 1.4B replay；不计算收益、不做候选事件、不输出 alpha 结论。

**Architecture:** 在 `src/research/external_signal_shadow/` 下新增 Stage 1.4A 审计模块，明确拆分 source-specific audit、coverage continuity、decision gate、CLI 和 review。脚本放在 `scripts/external_signal_shadow/`。测试全部使用 fixture/mock；真实 Binance public probe 必须显式传 `--live-public-readonly`。

**Tech Stack:** Python 3.11、标准库、pytest、现有 `configs/base.py`。第一版不引入 pandas / numpy / ccxt / SDK / private API / API key。

---

## 0. 硬边界

本计划只做 Stage 1.4A 数据可行性审计。

禁止实现：

```text
long_liquidation_exhaustion_reversal
short_liquidation_exhaustion_reversal
liquidation_trend_continuation
funding_oi_crowding_unwind
oi_expansion_trend_confirmation
```

禁止计算：

```text
forward return
MFE / MAE
random baseline
PnL
hit rate
alpha score
```

禁止接入：

```text
paper trading
live trading
execution intent
wallet payload
API key
.env
private endpoint
account / order / position private data
```

Stage 1.4A 的有效结论只有：

```text
stage1_4_data_feasible
stage1_4_data_degraded
stage1_4_data_unavailable
```

`stage1_4_data_degraded` 是默认预期，不是工程失败。

---

## 1. 审计顺序与 source 范围

固定审计顺序：

```text
1. Binance funding history: /fapi/v1/fundingRate
2. Binance OI history: /futures/data/openInterestHist，实测可用跨度
3. Local OI archive: 用户或系统已有本地 OI JSONL/glob
4. Local forceOrder archive: 本地 forceOrder 原始或聚合 JSONL/glob
5. Binance Vision COIN-M liquidationSnapshot manifest probe
6. Third-party: 只记录为 documented external option，不实现接入
```

第一版 live public-readonly audit 必须具体实现：

```text
Task 10A: probe Binance funding history endpoint
Task 10B: probe Binance OI history endpoint and detect max lookback days
Task 10C: probe Binance USD-M futures klines endpoint coverage
Task 10D: probe Binance Vision CM liquidationSnapshot manifest availability
Task 10E: scan local forceOrder archive path/glob if provided
Task 10F: scan local OI archive path/glob if provided
```

每个 probe 输出统一 audit block：

```json
{
  "source": "...",
  "network_mode": "live_public_readonly|fixture|local_archive",
  "request_count": 0,
  "success_count": 0,
  "failure_count": 0,
  "history_days": 0.0,
  "time_coverage_ratio": 0.0,
  "field_coverage_ratio": 0.0,
  "source_quality": "...",
  "usable": false,
  "primary_blocker": "..."
}
```

Fixture summary 只能是 smoke artifact：

```json
{
  "fixture_run": true,
  "research_result_valid": false
}
```

如果只运行 fixture，不得声称“完成真实 Stage 1.4A data feasibility audit”。

---

## 2. 必须新增/修改的文件

新增代码：

```text
src/research/external_signal_shadow/stage1_4a_coverage.py
src/research/external_signal_shadow/stage1_4a_funding.py
src/research/external_signal_shadow/stage1_4a_oi.py
src/research/external_signal_shadow/stage1_4a_price.py
src/research/external_signal_shadow/stage1_4a_liquidation.py
src/research/external_signal_shadow/stage1_4a_public_client.py
src/research/external_signal_shadow/stage1_4a_orchestrator.py
src/research/external_signal_shadow/stage1_4a_summary.py
```

新增脚本：

```text
scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py
scripts/external_signal_shadow/review_stage1_4a_derivatives_stress_data_feasibility.py
```

新增测试：

```text
tests/research/external_signal_shadow/test_stage1_4a_config.py
tests/research/external_signal_shadow/test_stage1_4a_coverage.py
tests/research/external_signal_shadow/test_stage1_4a_funding.py
tests/research/external_signal_shadow/test_stage1_4a_oi.py
tests/research/external_signal_shadow/test_stage1_4a_price.py
tests/research/external_signal_shadow/test_stage1_4a_liquidation.py
tests/research/external_signal_shadow/test_stage1_4a_public_client.py
tests/research/external_signal_shadow/test_stage1_4a_orchestrator.py
tests/research/external_signal_shadow/test_stage1_4a_summary.py
tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py
tests/scripts/external_signal_shadow/test_review_stage1_4a_derivatives_stress_data_feasibility.py
```

新增 fixture/report/review：

```text
tests/fixtures/external_signal_shadow/stage1_4a_degraded_fixture_summary.json
reports/external_signal_shadow/stage1_4_derivatives_stress_data_feasibility_summary.json
docs/reviews/2026-06-14-external-signal-shadow-lab-stage1-4-derivatives-stress-data-feasibility-review_CN.md
```

---

## 3. Task 0：预检工作区

Run:

```bash
git status --short --branch
PYTHONPATH=src uv run python - <<'PY'
import importlib
for name in [
    'research.external_signal_shadow.models',
    'research.external_signal_shadow.stage1_3_orchestrator',
]:
    mod = importlib.import_module(name)
    print('IMPORT_OK', name, mod.__name__)
PY
test -d scripts/external_signal_shadow && echo SCRIPT_DIR_OK
```

Expected:

```text
IMPORT_OK ...
SCRIPT_DIR_OK
```

如果分支不是 `feature/external-signal-shadow-stage1`，先停下确认。

---

## 4. Task 1：配置常量

**Modify:** `configs/base.py`  
**Create:** `tests/research/external_signal_shadow/test_stage1_4a_config.py`

必须新增常量，且每个常量有注释：

```python
EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_PREFERRED = 180
EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN = 90
EXTERNAL_SIGNAL_STAGE1_4_MIN_USABLE_SYMBOLS = 3

EXTERNAL_SIGNAL_STAGE1_4_BAR_COVERAGE_MIN_RATIO = 0.95
EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_FIELD_COVERAGE_MIN_RATIO = 0.90
EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_TIME_COVERAGE_MIN_RATIO = 0.90
EXTERNAL_SIGNAL_STAGE1_4_FUNDING_FIELD_COVERAGE_MIN_RATIO = 0.95
EXTERNAL_SIGNAL_STAGE1_4_FUNDING_SETTLEMENT_COVERAGE_MIN_RATIO = 0.95
EXTERNAL_SIGNAL_STAGE1_4_OI_FIELD_COVERAGE_MIN_RATIO = 0.90
EXTERNAL_SIGNAL_STAGE1_4_OI_TIME_COVERAGE_MIN_RATIO = 0.90

EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_FUNDING_INTERVAL_MS = 8 * 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_OI_INTERVAL_MS = 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_PRICE_INTERVAL_MS = 15 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_4_FUNDING_PUBLISH_LAG_MS = 15 * 60 * 1000

EXTERNAL_SIGNAL_STAGE1_4_PREVIEW_MIN_COMPOSITE_OVERLAP_WINDOWS = 50
EXTERNAL_SIGNAL_STAGE1_4_PREVIEW_MIN_COMPOSITE_OVERLAP_DAYS = 15

EXTERNAL_SIGNAL_STAGE1_4_BINANCE_FAPI_BASE_URL = "https://fapi.binance.com"
EXTERNAL_SIGNAL_STAGE1_4_FUNDING_RATE_PATH = "/fapi/v1/fundingRate"
EXTERNAL_SIGNAL_STAGE1_4_OPEN_INTEREST_HIST_PATH = "/futures/data/openInterestHist"
EXTERNAL_SIGNAL_STAGE1_4_CURRENT_OPEN_INTEREST_PATH = "/fapi/v1/openInterest"
EXTERNAL_SIGNAL_STAGE1_4_FUTURES_KLINES_PATH = "/fapi/v1/klines"
EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_BASE_URL = "https://data.binance.vision"
EXTERNAL_SIGNAL_STAGE1_4_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC = 0.2

EXTERNAL_SIGNAL_STAGE1_4_LOCAL_OI_ARCHIVE_GLOB = "data/external_signal_shadow/derivatives_stress/oi/*.jsonl"
EXTERNAL_SIGNAL_STAGE1_4_LOCAL_FORCE_ORDER_ARCHIVE_GLOB = "data/trend_regime_force_orders_raw.jsonl"

EXTERNAL_SIGNAL_STAGE1_4_CM_TO_UM_SYMBOL_MAP = {
    "BTCUSD_PERP": "BTCUSDT",
    "ETHUSD_PERP": "ETHUSDT",
    "SOLUSD_PERP": "SOLUSDT",
    "XRPUSD_PERP": "XRPUSDT",
    "DOGEUSD_PERP": "DOGEUSDT",
}
```

Tests must assert these constants and `RISK_LIVE_TRADING_ENABLED is False`.

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_config.py -q
```

Expected: PASS after implementation.

---

## 5. Task 2：通用 time coverage 工具

**Create:**

```text
src/research/external_signal_shadow/stage1_4a_coverage.py
tests/research/external_signal_shadow/test_stage1_4a_coverage.py
```

必须实现：

```python
def compute_time_coverage(timestamps_ms: list[int], expected_interval_ms: int) -> dict:
    ...
```

输出：

```json
{
  "history_days": 0.0,
  "expected_bucket_count": 0,
  "actual_unique_bucket_count": 0,
  "time_coverage_ratio": 0.0,
  "gap_count": 0,
  "max_gap_ms": 0
}
```

测试必须覆盖：

```text
连续 1h 数据 coverage = 1.0
缺一根 1h 数据 coverage < 1.0
duplicate timestamp 不增加 actual_unique_bucket_count
空输入返回 0，不抛 ZeroDivisionError
```

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_coverage.py -q
```

---

## 6. Task 3：Funding audit，必须检查 8h settlement cadence

**Create:**

```text
src/research/external_signal_shadow/stage1_4a_funding.py
tests/research/external_signal_shadow/test_stage1_4a_funding.py
```

必须实现：

```python
def audit_funding_history_rows(rows: list[dict], expected_symbol: str) -> dict: ...
def funding_state_at_event(rows: list[dict], event_available_at_ms: int, funding_publish_lag_ms: int) -> dict | None: ...
```

`audit_funding_history_rows()` 输出必须区分：

```json
{
  "funding_source": "binance_fapi_fundingRate",
  "funding_record_count": 0,
  "funding_history_days": 0.0,
  "funding_field_coverage_ratio": 0.0,
  "funding_settlement_coverage_ratio": 0.0,
  "missing_settlement_count": 0,
  "max_settlement_gap_ms": 0,
  "source_quality": "public_settled_funding_history",
  "usable": false
}
```

测试必须覆盖：

```text
test_funding_settlement_coverage_detects_missing_8h_records
test_funding_field_coverage_counts_valid_rates_only
test_funding_asof_policy_uses_latest_record_before_available_minus_lag
test_funding_asof_policy_does_not_use_future_record
```

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_funding.py -q
```

---

## 7. Task 4：OI audit，必须检查时间连续性，不只是字段非空

**Create:**

```text
src/research/external_signal_shadow/stage1_4a_oi.py
tests/research/external_signal_shadow/test_stage1_4a_oi.py
```

必须实现：

```python
def audit_open_interest_history_rows(rows: list[dict], expected_symbol: str, expected_interval_ms: int) -> dict: ...
```

输出必须包含：

```json
{
  "oi_source": "binance_openInterestHist_or_local_archive",
  "oi_record_count": 0,
  "oi_history_days": 0.0,
  "oi_field_coverage_ratio": 0.0,
  "oi_time_coverage_ratio": 0.0,
  "expected_bucket_count": 0,
  "actual_unique_bucket_count": 0,
  "gap_count": 0,
  "max_gap_ms": 0,
  "oi_history_limit_detected_days": 0.0,
  "oi_blocks_full_composite": true,
  "source_quality": "public_history|local_archive|missing",
  "usable": false
}
```

硬规则：

```text
if oi_history_days < 90 -> oi_blocks_full_composite = true
if oi_time_coverage_ratio < 0.90 -> oi_blocks_full_composite = true
if oi_field_coverage_ratio < 0.90 -> oi_blocks_full_composite = true
```

测试必须覆盖：

```text
test_oi_history_below_90d_blocks_full_composite
test_oi_time_coverage_counts_expected_interval_buckets
test_oi_field_coverage_is_separate_from_time_coverage
test_oi_gap_count_and_max_gap_ms_are_reported
```

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_oi.py -q
```

---

## 8. Task 5：Price audit，必须计算真实 history_days，不能再写 999.0

**Create:**

```text
src/research/external_signal_shadow/stage1_4a_price.py
tests/research/external_signal_shadow/test_stage1_4a_price.py
```

必须实现：

```python
def audit_price_source_rows(rows: list[dict], expected_symbol: str, source_kind: str) -> dict: ...
```

输出：

```json
{
  "price_source_preference": "futures_klines_preferred",
  "price_source": "futures_klines|spot_klines_proxy",
  "price_venue_proxy_used": false,
  "price_history_days": 0.0,
  "price_bar_count": 0,
  "price_bar_coverage_ratio": 0.0,
  "time_coverage_ratio": 0.0,
  "gap_count": 0,
  "max_gap_ms": 0
}
```

测试必须覆盖：

```text
test_price_history_days_is_computed_not_stubbed
test_price_coverage_below_min_can_block_summary
test_price_source_defaults_to_futures_klines
test_spot_proxy_is_marked_as_proxy
```

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_price.py -q
```

---

## 9. Task 6：Liquidation audit，必须真正审计 rows/archive/manifest

**Create:**

```text
src/research/external_signal_shadow/stage1_4a_liquidation.py
tests/research/external_signal_shadow/test_stage1_4a_liquidation.py
```

必须实现：

```python
def map_force_order_side_to_liquidation_side(side: str) -> str: ...
def audit_cm_to_um_symbol_mapping(cm_symbols: list[str]) -> dict: ...
def audit_liquidation_notional_conversion(metadata: dict | None) -> dict: ...
def audit_force_order_archive_rows(rows: list[dict], expected_symbols: tuple[str, ...]) -> dict: ...
def audit_liquidation_snapshot_rows(rows: list[dict], expected_symbols: tuple[str, ...]) -> dict: ...
def audit_binance_vision_manifest_entries(entries: list[dict], expected_symbols: tuple[str, ...]) -> dict: ...
```

Side 映射硬规则：

```text
SELL -> long_liquidation
BUY -> short_liquidation
```

Notional conversion enum：

```text
unavailable
metadata_present_unverified
estimated
verified_by_sample
```

只有 `verified_by_sample` 才可能支持 full feasibility。

CM proxy 默认不能解锁 full composite replay：

```json
{
  "liquidation_source_quality": "cm_liquidation_snapshot_proxy",
  "liquidation_proxy_accepted_for_full_replay": false
}
```

输出必须包含：

```json
{
  "liquidation_source": "...",
  "liquidation_source_quality": "cm_liquidation_snapshot_proxy|force_order_archive|missing",
  "liquidation_history_days": 0.0,
  "liquidation_field_coverage_ratio": 0.0,
  "liquidation_time_coverage_ratio": 0.0,
  "liquidation_nonzero_window_count": 0,
  "liquidation_symbol_mapping_quality": "proxy|exact|missing",
  "cm_to_um_proxy_used": false,
  "liquidation_proxy_accepted_for_full_replay": false,
  "notional_conversion_required": true,
  "notional_conversion_quality": "unavailable|metadata_present_unverified|estimated|verified_by_sample"
}
```

测试必须覆盖：

```text
test_force_order_side_maps_sell_to_long_liquidation
test_force_order_side_maps_buy_to_short_liquidation
test_cm_proxy_does_not_allow_full_composite_without_explicit_acceptance
test_notional_conversion_quality_requires_verified_by_sample
test_liquidation_rows_audit_reports_history_days_and_nonzero_windows
test_liquidation_field_coverage_below_min_blocks_summary_later
```

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_liquidation.py -q
```

---

## 10. Task 7：Summary decision gates 必须覆盖 history、coverage、proxy、preview density

**Create:**

```text
src/research/external_signal_shadow/stage1_4a_summary.py
tests/research/external_signal_shadow/test_stage1_4a_summary.py
```

Decision engine 必须按顺序检查：

```text
1. safety/scope violation
2. fixture_run -> research_result_valid=false
3. usable_symbol_count
4. notional_conversion_quality
5. CM proxy without explicit full replay acceptance
6. OI history >=90d
7. OI time coverage >=0.90
8. OI field coverage >=0.90
9. funding history >=90d
10. funding settlement coverage >=0.95
11. funding field coverage >=0.95
12. liquidation history >=90d
13. liquidation time coverage >=0.90
14. liquidation field coverage >=0.90
15. price history >=90d
16. price coverage >=0.95
17. preview_composite_overlap_window_count >=50
18. preview_composite_overlap_event_days >=15
```

新增测试必须包括：

```text
test_summary_degraded_when_funding_coverage_below_min
test_summary_degraded_when_liquidation_coverage_below_min
test_summary_degraded_when_price_coverage_below_min
test_summary_degraded_when_preview_overlap_below_min
test_cm_proxy_does_not_allow_full_composite_without_explicit_acceptance
test_fixture_run_is_research_result_invalid
test_summary_feasible_only_when_all_sources_pass_and_proxy_accepted
```

关键规则：

```text
fixture_run = true -> research_result_valid = false
CM proxy default -> stage1_4_data_degraded unless liquidation_proxy_accepted_for_full_replay=true and notional_conversion_quality=verified_by_sample
preview density insufficient -> density_failure, not alpha failure
```

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_summary.py -q
```

---

## 11. Task 8：Orchestrator 必须使用真实 audit fields，不允许 stub

**Create:**

```text
src/research/external_signal_shadow/stage1_4a_orchestrator.py
tests/research/external_signal_shadow/test_stage1_4a_orchestrator.py
```

必须聚合：

```text
funding_audits -> funding history/coverage
OI audits -> OI history/time/field coverage
liquidation_audit -> liquidation history/time/field/proxy/notional
price_audits -> price_history_days/coverage/proxy
preview_counts -> preview density only
```

禁止：

```text
"price": 999.0
hardcoded history_days
hardcoded coverage pass
```

测试必须覆盖：

```text
test_orchestrator_uses_price_history_days_not_stub
test_orchestrator_marks_preview_not_alpha_and_no_replay
test_orchestrator_degraded_when_oi_blocks_full_composite
test_orchestrator_degraded_when_preview_density_below_min
```

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_orchestrator.py -q
```

---

## 12. Task 9：Public client 与安全边界

**Create:**

```text
src/research/external_signal_shadow/stage1_4a_public_client.py
tests/research/external_signal_shadow/test_stage1_4a_public_client.py
```

只允许 public paths：

```text
/fapi/v1/fundingRate
/futures/data/openInterestHist
/fapi/v1/klines
/fapi/v1/openInterest
```

必须拒绝：

```text
/order
/account
/positionRisk
/wallet
/withdraw
/sapi
```

测试必须覆盖：

```text
test_build_binance_fapi_url_uses_public_base_and_query
test_private_or_account_paths_are_rejected
test_allowed_public_paths_pass
test_public_client_does_not_require_or_accept_api_key
```

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_4a_public_client.py -q
```

---

## 13. Task 10：CLI 必须支持 fixture、live public-readonly、本地 archive

**Create/Modify:**

```text
scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py
tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py
```

CLI 参数：

```text
--fixture-summary-input PATH
--live-public-readonly
--local-oi-archive PATH_OR_GLOB
--local-force-order-archive PATH_OR_GLOB
--output-summary PATH
```

互斥/组合规则：

```text
fixture-summary-input 不能和 live-public-readonly 同时使用
fixture-summary-input 不能声称 research_result_valid=true
live-public-readonly 可与 local archives 一起使用
无 fixture、无 live、无 local archive -> data_unavailable
```

测试必须覆盖：

```text
test_cli_requires_live_fixture_or_local_archive
test_cli_rejects_fixture_and_live_flag_together
test_cli_fixture_summary_round_trip_marks_research_invalid
test_cli_accepts_local_oi_archive_path
test_cli_accepts_local_force_order_archive_path
test_live_public_readonly_path_does_not_read_env
```

`test_live_public_readonly_path_does_not_read_env` 可允许网络失败，但必须检查：

```python
monkeypatch.setenv("BINANCE_API_KEY", "LEAK_CHECK")
rc = main(["--live-public-readonly", "--output-summary", str(summary)])
if summary.exists():
    text = summary.read_text(encoding="utf-8")
    assert "LEAK_CHECK" not in text
    assert json.loads(text)["live_trading_allowed"] is False
```

Live public-readonly path 必须具体实现，不能再返回 `live_public_readonly_not_implemented_until_task_10`。

最小 live probes：

```text
funding endpoint probe: request fundingRate for each symbol, infer history_days/field coverage from returned rows
OI endpoint probe: request openInterestHist for each symbol, infer detected history_days/time coverage
futures klines probe: request /fapi/v1/klines for each symbol, infer price coverage from returned rows
Binance Vision CM manifest probe: HEAD or lightweight URL probe for mapped CM symbols/months, no bulk download
```

本地 archive scan：

```text
--local-oi-archive -> read JSONL/glob, audit OI rows
--local-force-order-archive -> read JSONL/glob, audit forceOrder rows
```

Summary 必须包含：

```json
{
  "local_oi_archive_found": false,
  "local_force_order_archive_found": false,
  "network_mode": "live_public_readonly|fixture|local_archive|mixed",
  "fixture_run": false,
  "research_result_valid": true
}
```

静态安全检查：

```bash
! rg -n "os\.environ|dotenv|BINANCE_API_KEY|BINANCE_SECRET|apiKey|secret|/order|/account|positionRisk" \
  scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py \
  src/research/external_signal_shadow/stage1_4a_public_client.py
```

---

## 14. Task 11：Review 必须输出 per-source audit table

**Create:**

```text
scripts/external_signal_shadow/review_stage1_4a_derivatives_stress_data_feasibility.py
tests/scripts/external_signal_shadow/test_review_stage1_4a_derivatives_stress_data_feasibility.py
```

Review 必须包含：

```text
1. decision / primary_blocker / research_result_valid
2. safety boundary
3. per-source audit table
4. source semantics notes
5. preview density explanation
6. next action
```

Per-source table 字段：

```text
source
history_days
time_coverage_ratio
field_coverage_ratio
symbol_count
source_quality
proxy_used
blocker
usable_for_1_4b
```

必须解释：

```text
funding 是否满足 90d
OI 是否不足 90d 或 coverage 不足
liquidation 是否是 CM proxy / forceOrder archive / missing
price 是否 futures klines，spot proxy 是否使用
preview 不是 alpha
fixture_run=true 时 research_result_valid=false
```

测试必须覆盖：

```text
test_review_renders_source_audit_table
test_review_marks_fixture_as_not_research_valid
test_review_mentions_cm_proxy_not_complete_tape
test_review_mentions_oi_blocks_full_composite
```

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_4a_derivatives_stress_data_feasibility.py -q
```

---

## 15. Task 12：生成 fixture smoke artifact，不作为研究结论

**Create:**

```text
tests/fixtures/external_signal_shadow/stage1_4a_degraded_fixture_summary.json
reports/external_signal_shadow/stage1_4_derivatives_stress_data_feasibility_summary.json
docs/reviews/2026-06-14-external-signal-shadow-lab-stage1-4-derivatives-stress-data-feasibility-review_CN.md
```

Fixture 必须包含：

```json
{
  "fixture_run": true,
  "research_result_valid": false,
  "expected_default_outcome": "stage1_4_data_degraded",
  "preview_not_alpha": true,
  "candidate_replay_implemented": false,
  "forward_return_computed": false,
  "random_baseline_computed": false
}
```

生成命令：

```bash
PYTHONPATH=src uv run python scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py \
  --fixture-summary-input tests/fixtures/external_signal_shadow/stage1_4a_degraded_fixture_summary.json \
  --output-summary reports/external_signal_shadow/stage1_4_derivatives_stress_data_feasibility_summary.json

PYTHONPATH=src uv run python scripts/external_signal_shadow/review_stage1_4a_derivatives_stress_data_feasibility.py \
  --summary reports/external_signal_shadow/stage1_4_derivatives_stress_data_feasibility_summary.json \
  --output-review docs/reviews/2026-06-14-external-signal-shadow-lab-stage1-4-derivatives-stress-data-feasibility-review_CN.md
```

Review 必须写明：

```text
本 artifact 是 fixture smoke，不证明真实 derivatives stress data availability。
```

---

## 16. Task 13：可选真实 public-readonly audit run

如果用户明确要求真实探测，运行：

```bash
PYTHONPATH=src uv run python scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py \
  --live-public-readonly \
  --local-oi-archive "data/external_signal_shadow/derivatives_stress/oi/*.jsonl" \
  --local-force-order-archive "data/trend_regime_force_orders_raw.jsonl" \
  --output-summary reports/external_signal_shadow/stage1_4_derivatives_stress_data_feasibility_summary.json
```

如果本地 archive 不存在，不应 crash。Summary 应输出：

```json
{
  "local_oi_archive_found": false,
  "local_force_order_archive_found": false
}
```

注意：这一步可能联网。必须由用户确认或在本环境允许网络时显式执行。

---

## 17. Verification

Focused tests:

```bash
PYTHONPATH=src uv run pytest \
  tests/research/external_signal_shadow/test_stage1_4a_config.py \
  tests/research/external_signal_shadow/test_stage1_4a_coverage.py \
  tests/research/external_signal_shadow/test_stage1_4a_funding.py \
  tests/research/external_signal_shadow/test_stage1_4a_oi.py \
  tests/research/external_signal_shadow/test_stage1_4a_price.py \
  tests/research/external_signal_shadow/test_stage1_4a_liquidation.py \
  tests/research/external_signal_shadow/test_stage1_4a_public_client.py \
  tests/research/external_signal_shadow/test_stage1_4a_orchestrator.py \
  tests/research/external_signal_shadow/test_stage1_4a_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py \
  tests/scripts/external_signal_shadow/test_review_stage1_4a_derivatives_stress_data_feasibility.py \
  -q
```

External signal suite:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow tests/scripts/external_signal_shadow -q
```

Ruff:

```bash
uv run ruff check \
  src/research/external_signal_shadow \
  scripts/external_signal_shadow \
  tests/research/external_signal_shadow \
  tests/scripts/external_signal_shadow
```

Full pytest:

```bash
PYTHONPATH=src uv run pytest -q
```

Completion requires actual command outputs. Do not claim pass without fresh verification.

---

## 18. Expected final interpretation

如果只生成 fixture artifact：

```text
Stage 1.4A feasibility framework implemented.
真实 derivatives stress data availability 尚未审计。
research_result_valid = false
```

如果运行 live/local audit：

```text
Stage 1.4A data feasibility actually audited.
根据 OI/liquidation/funding/price coverage 输出 feasible/degraded/unavailable。
```

无论哪种情况，仍不能推出：

```text
liquidation/funding/OI 有 alpha
可以进入 Stage 1.4B replay
可以进入 paper/live
可以写交易策略
```

只有当 summary 同时满足：

```text
research_result_valid = true
stage1_4_data_feasible
stage1_4b_candidate_replay_allowed = true
composite_replay_allowed = true
```

才允许下一步写 Stage 1.4B candidate replay design。

Do not commit unless user explicitly asks.
