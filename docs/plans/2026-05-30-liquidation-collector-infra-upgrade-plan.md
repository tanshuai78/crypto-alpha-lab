# Liquidation Collector Infra Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在部署到服务器前，把 liquidation 采集链路升级成“raw event archive 优先、可研究、可恢复、可派生”的长期基础设施，稳定沉淀原始 liquidation 事件，并持续派生 `1m / 5m / 1h` 数据，同时保持现有 watchlist 链路兼容。

**Architecture:** 保留现有 `trend-forceorder` WebSocket 采集器，不重写采集入口；先固化 raw event schema、写入安全语义和去重语义，再从 raw 事件按 canonical timestamp 派生 `1m / 5m / 1h` 聚合文件。研究用 `1m / 5m` 文件必须支持 zero-fill，健康检查必须直接回答“当前 archive 是否足够支撑后续 1m shock event study”。

**Tech Stack:** Python 3.11, pytest, ruff, JSONL, Binance forceOrder WebSocket, standalone scripts, Docker deployment, cron-based server aggregation.

---

## Context

当前系统已经具备两个基础能力：

- [collect_trend_regime_force_orders.py](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/scripts/collect_trend_regime_force_orders.py) 已支持写入：
  - `trend_regime_liquidation_cache.json`
  - `trend_regime_force_orders_raw.jsonl`
- [aggregate_trend_regime_liquidations.py](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/scripts/aggregate_trend_regime_liquidations.py) 已支持从 raw 聚合 `1h` 文件

但当前仍缺 9 个关键约束：

1. raw event schema 没有固化；
2. raw writer 没有 append-only / flush / fsync 语义；
3. 没有稳定 `event_id`，重连重复事件无法可靠去重；
4. 聚合器没有明确的 `1m / 5m / 1h` 输出 schema；
5. `1m / 5m` 研究文件不支持 zero-fill；
6. 健康检查不能回答 `research_ready_1m_24h`；
7. 部署文档没有写清楚定期派生机制；
8. raw rotation 仍是临时操作，不是长期 archive policy；
9. 没有 24h 部署后验收标准。

本计划只处理 **采集基础设施升级**，不继续推进新策略研究。

---

## Task 1: Lock Raw Event Schema And Writer Contract

**Files:**
- Modify: `scripts/collect_trend_regime_force_orders.py`
- Modify: `tests/scripts/test_collect_trend_regime_force_orders.py`
- Modify: `docs/ops/2026-06-05-trend-liquidation-phase1a-server_CN.md`

**Step 1: Write the failing tests**

Add tests covering:

1. raw event row contains required research fields
2. raw event includes stable `schema_version`
3. raw event includes stable `event_id`
4. raw writer emits one valid JSON line per event
5. parser accepts `--fsync-raw` and `--raw-schema-version`

Minimum raw schema contract to lock in tests:

```python
REQUIRED_RAW_KEYS = {
    "schema_version",
    "source",
    "event_id",
    "symbol",
    "exchange_symbol",
    "event_time_ms",
    "trade_time_ms",
    "side",
    "liquidated_position_side",
    "liquidation_side",
    "price",
    "quantity",
    "notional_usdt",
    "raw_payload",
}
```

Example tests:

```python
def test_forceorder_raw_event_contains_required_research_fields():
    record = normalize_forceorder_event(sample_payload)
    assert REQUIRED_RAW_KEYS.issubset(record)
    assert record["schema_version"] == 1


def test_raw_event_id_is_stable_for_same_exchange_event():
    record_a = normalize_forceorder_event(sample_payload)
    record_b = normalize_forceorder_event(sample_payload)
    assert record_a["event_id"] == record_b["event_id"]


def test_parse_args_accepts_raw_fsync_and_schema_version():
    args = parse_args(["--raw-output", "x.jsonl", "--fsync-raw", "--raw-schema-version", "1"])
    assert args.fsync_raw is True
    assert args.raw_schema_version == 1
```

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_collect_trend_regime_force_orders.py -k "raw_event or fsync_raw or schema_version"
```
Expected: FAIL.

**Step 3: Write minimal implementation**

In `collect_trend_regime_force_orders.py`:
- introduce explicit raw event normalization helper
- compute `event_id` from a stable tuple such as:

```python
f"{source}|{symbol}|{event_time_ms}|{trade_time_ms}|{side}|{price}|{quantity}"
```

- add CLI args:
  - `--fsync-raw`
  - `--raw-schema-version`
- make raw writer explicitly:
  - append-only
  - one JSON line per event
  - `flush()` after write
  - optional `os.fsync()` when `--fsync-raw`
- keep cache behavior unchanged

**Step 4: Run tests to verify they pass**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_collect_trend_regime_force_orders.py -k "raw_event or fsync_raw or schema_version"
```
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/collect_trend_regime_force_orders.py tests/scripts/test_collect_trend_regime_force_orders.py docs/ops/2026-06-05-trend-liquidation-phase1a-server_CN.md
git commit -m "feat: lock raw liquidation event archive schema"
```

---

## Task 2: Add Canonical Multi-Granularity Aggregation With Dedup

**Files:**
- Modify: `scripts/aggregate_trend_regime_liquidations.py`
- Modify: `tests/scripts/test_aggregate_trend_regime_liquidations.py`

**Step 1: Write the failing tests**

Add tests for:

1. unsupported bucket raises `ValueError`
2. bucket timestamp uses canonical event timestamp priority
3. duplicate raw rows deduplicate by `event_id`
4. `1m` output uses `bar_start_ms` schema
5. `5m` output uses `bar_start_ms` schema
6. `1h` output preserves legacy `hour_bucket_ms` schema

Example tests:

```python
def test_aggregate_raw_to_bucket_rejects_unsupported_bucket():
    with pytest.raises(ValueError):
        aggregate_raw_to_bucket([], bucket="10m")


def test_aggregate_prefers_event_time_over_stale_hour_bucket():
    rows = aggregate_raw_to_bucket([record_with_wrong_hour_bucket], bucket="1h")
    assert rows[0]["hour_bucket_ms"] == expected_from_event_time


def test_aggregate_raw_to_bucket_deduplicates_by_event_id():
    rows = aggregate_raw_to_bucket([record, duplicate_of_record], bucket="1m")
    assert rows[0]["event_count_1m"] == 1
```

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_aggregate_trend_regime_liquidations.py
```
Expected: FAIL.

**Step 3: Write minimal implementation**

In `aggregate_trend_regime_liquidations.py`:
- add canonical timestamp priority:
  - `event_time_ms`
  - `trade_time_ms`
  - `E`
  - `T`
  - `timestamp_ms`
- fallback to legacy bucket only if none of the above exists, and count:
  - `fallback_to_legacy_hour_bucket_count`
  - `missing_timestamp_count`
- validate `bucket in {"1m", "5m", "1h"}`
- dedup by `event_id` before aggregation
- explicitly emit separate schemas:

`1m`
```json
{
  "symbol": "BTC/USDT",
  "bar_start_ms": 1780000000000,
  "long_liquidation_notional_1m_usdt": 100000.0,
  "short_liquidation_notional_1m_usdt": 0.0,
  "total_liquidation_notional_1m_usdt": 100000.0,
  "event_count_1m": 3,
  "source": "binance_forceorder_raw_archive"
}
```

`5m`
```json
{
  "symbol": "BTC/USDT",
  "bar_start_ms": 1780000200000,
  "long_liquidation_notional_5m_usdt": 500000.0,
  "short_liquidation_notional_5m_usdt": 20000.0,
  "total_liquidation_notional_5m_usdt": 520000.0,
  "event_count_5m": 8,
  "source": "binance_forceorder_raw_archive"
}
```

`1h legacy`
```json
{
  "symbol": "BTC/USDT",
  "hour_bucket_ms": 1780000000000,
  "liquidation_notional_1h_usdt": 1230000.0,
  "long_liquidation_notional_1h_usdt": 700000.0,
  "short_liquidation_notional_1h_usdt": 530000.0
}
```

**Step 4: Run tests to verify they pass**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_aggregate_trend_regime_liquidations.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/aggregate_trend_regime_liquidations.py tests/scripts/test_aggregate_trend_regime_liquidations.py
git commit -m "feat: add canonical liquidation aggregation with dedup"
```

---

## Task 3: Add Zero-Fill Research Derivation For 1m And 5m

**Files:**
- Modify: `scripts/aggregate_trend_regime_liquidations.py`
- Modify: `tests/scripts/test_aggregate_trend_regime_liquidations.py`

**Step 1: Write the failing tests**

Add tests proving research aggregates can zero-fill empty buckets when requested.

Example tests:

```python
def test_aggregate_zero_fills_empty_1m_buckets_when_requested():
    rows = aggregate_raw_to_bucket(
        records,
        bucket="1m",
        fill_empty_buckets=True,
        start_ms=start_ms,
        end_ms=end_ms,
        symbols=["BTC/USDT"],
    )
    assert any(row["filled_empty_bucket"] is True for row in rows)


def test_aggregate_zero_fills_empty_5m_buckets_when_requested():
    ...
```

Also add a parser test for:
- `--fill-empty-buckets`
- `--start-ms`
- `--end-ms`
- `--symbols`

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_aggregate_trend_regime_liquidations.py -k fill_empty
```
Expected: FAIL.

**Step 3: Write minimal implementation**

In `aggregate_trend_regime_liquidations.py`:
- support optional zero-fill for `1m / 5m`
- zero-fill only when caller provides bounded time range and symbol set
- emit rows such as:

```json
{
  "symbol": "BTC/USDT",
  "bar_start_ms": 1780000000000,
  "long_liquidation_notional_1m_usdt": 0.0,
  "short_liquidation_notional_1m_usdt": 0.0,
  "total_liquidation_notional_1m_usdt": 0.0,
  "event_count_1m": 0,
  "source": "binance_forceorder_raw_archive",
  "filled_empty_bucket": true
}
```

Do not zero-fill `1h` legacy output by default.

**Step 4: Run tests to verify they pass**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_aggregate_trend_regime_liquidations.py -k fill_empty
```
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/aggregate_trend_regime_liquidations.py tests/scripts/test_aggregate_trend_regime_liquidations.py
git commit -m "feat: add zero-filled research liquidation buckets"
```

---

## Task 4: Add Health Check With Raw Integrity And Research Readiness

**Files:**
- Modify: `scripts/check_liquidation_collector_health.py` (create if absent)
- Create: `tests/scripts/test_check_liquidation_collector_health.py`

**Step 1: Write the failing tests**

Add tests covering:

1. invalid JSON line count
2. last line validity
3. duplicate event count or duplicate rate
4. aggregate `1m` coverage ratio over trailing 24h
5. aggregate `1m` max gap minutes over trailing 24h
6. `research_ready_1m_24h` false when continuity is insufficient

Example tests:

```python
def test_health_check_reports_invalid_json_lines(tmp_path):
    summary = inspect_liquidation_collector_health(tmp_path)
    assert summary["raw_invalid_json_line_count"] == 1


def test_health_check_reports_1m_coverage_ratio_and_max_gap(tmp_path):
    summary = inspect_liquidation_collector_health(tmp_path)
    assert "aggregate_1m_coverage_ratio_24h" in summary
    assert "aggregate_1m_max_gap_minutes_24h" in summary


def test_health_check_marks_research_ready_false_without_24h_coverage(tmp_path):
    summary = inspect_liquidation_collector_health(tmp_path)
    assert summary["research_ready_1m_24h"] is False
```

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_check_liquidation_collector_health.py
```
Expected: FAIL.

**Step 3: Write minimal implementation**

Create or extend `check_liquidation_collector_health.py` so output includes at least:

```json
{
  "raw_exists": true,
  "raw_row_count": 10000,
  "raw_invalid_json_line_count": 0,
  "raw_last_line_valid": true,
  "raw_duplicate_event_count": 23,
  "raw_time_span_hours": 26.4,
  "raw_recent_event_count_1h": 12,
  "raw_recent_event_count_24h": 488,
  "aggregate_1m_exists": true,
  "aggregate_1m_row_count": 1440,
  "aggregate_1m_coverage_ratio_24h": 0.997,
  "aggregate_1m_missing_bucket_count_24h": 4,
  "aggregate_1m_max_gap_minutes_24h": 2,
  "aggregate_5m_exists": true,
  "aggregate_1h_exists": true,
  "research_ready_1m_24h": true
}
```

Document duplicate metric scope explicitly if you scan only the active file or a trailing window.

**Step 4: Run tests to verify they pass**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_check_liquidation_collector_health.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/check_liquidation_collector_health.py tests/scripts/test_check_liquidation_collector_health.py
git commit -m "feat: add liquidation archive integrity and readiness health check"
```

---

## Task 5: Preserve Watchlist Compatibility And Existing Route Outputs

**Files:**
- Modify: `tests/scripts/test_run_trend_regime_watchlist.py`
- Modify: `tests/scripts/test_fetch_third_party_liquidation_history.py` (only if needed for regression guard)
- Modify: `scripts/run_trend_regime_watchlist.py` (only if required)

**Step 1: Write the failing tests**

Add regression tests proving:

1. watchlist still reads `trend_regime_liquidation_cache.json` unchanged
2. 1m collector upgrade does not alter existing Route B `1h` behavior
3. new raw / aggregate namespace does not leak into watchlist cache contract

Example tests:

```python
def test_watchlist_still_reads_liquidation_cache_contract(tmp_path):
    ...
    assert row["liquidation_notional_1h_usdt"] == expected


def test_existing_1h_route_b_flow_is_unchanged():
    ...
```

**Step 2: Run tests to verify they fail or are missing**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_run_trend_regime_watchlist.py -k liquidation_cache \
  tests/scripts/test_fetch_third_party_liquidation_history.py
```
Expected: missing regression tests or FAIL if compatibility drift exists.

**Step 3: Write minimal implementation**

Prefer tests-only if compatibility is already intact. Only modify runtime watchlist code if new archive semantics accidentally broke the cache contract.

**Step 4: Run tests to verify they pass**

Run the same command above and expect PASS.

**Step 5: Commit**

```bash
git add tests/scripts/test_run_trend_regime_watchlist.py tests/scripts/test_fetch_third_party_liquidation_history.py scripts/run_trend_regime_watchlist.py
git commit -m "test: lock liquidation archive compatibility boundaries"
```

---

## Task 6: Update Ops Docs, Rotation Policy, And Aggregation Schedule

**Files:**
- Modify: `docs/ops/2026-06-05-trend-liquidation-phase1a-server_CN.md`
- Modify: `docs/reviews/2026-05-30-route-a-timestamp-and-join-integrity-audit-review.md`
- Modify: `docs/plans/2026-05-30-liquidation-collector-infra-upgrade-checklist.md` (if wording must match final implementation)

**Step 1: Update deployment docs**

Document all of the following explicitly:

1. raw archive is the primary fact source
2. cache is legacy compatibility only
3. derived outputs and their semantics:
   - `trend_regime_liquidation_1m.jsonl`
   - `trend_regime_liquidation_5m.jsonl`
   - `trend_regime_liquidation_hourly.jsonl`
4. cron-based derivation schedule
5. backup + checksum + rotate sequence
6. active raw file vs backup directory
7. storage / IOPS warning for `1m` zero-filled files
8. 24h post-deploy acceptance checklist

Use cron as the default minimal ops mechanism:

```cron
*/1 * * * * cd /root/crypto-alpha-lab && PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py --bucket 1m --fill-empty-buckets ...
*/5 * * * * cd /root/crypto-alpha-lab && PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py --bucket 5m --fill-empty-buckets ...
5 * * * * cd /root/crypto-alpha-lab && PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py --bucket 1h ...
```

Also document checksum-backed rotation:

```bash
sha256sum old_file > old_file.sha256
```

**Step 2: Verify docs are internally consistent**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
rg -n "raw archive|fill-empty-buckets|research_ready_1m_24h|cron|sha256|IOPS|1m" docs/ops docs/reviews docs/plans
```
Expected: new operational terms appear in the right docs.

**Step 3: Commit**

```bash
git add docs/ops/2026-06-05-trend-liquidation-phase1a-server_CN.md docs/reviews/2026-05-30-route-a-timestamp-and-join-integrity-audit-review.md docs/plans/2026-05-30-liquidation-collector-infra-upgrade-checklist.md
git commit -m "docs: finalize liquidation collector infra runbook"
```

---

## Task 7: Full Verification Before Server Deployment

**Files:**
- No new files

**Step 1: Run focused test suite**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_collect_trend_regime_force_orders.py \
  tests/scripts/test_aggregate_trend_regime_liquidations.py \
  tests/scripts/test_check_liquidation_collector_health.py \
  tests/scripts/test_run_trend_regime_watchlist.py \
  tests/scripts/test_fetch_third_party_liquidation_history.py
```
Expected: PASS.

**Step 2: Run lint/format verification**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
ruff check scripts tests/scripts
ruff format --check scripts tests/scripts
```
Expected: PASS.

**Step 3: Run local smoke tests**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime_force_orders_raw.jsonl \
  --bucket 1m \
  --fill-empty-buckets \
  --start-ms 1780000000000 \
  --end-ms 1780086400000 \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --output /tmp/trend_regime_liquidation_1m.jsonl

PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime_force_orders_raw.jsonl \
  --bucket 5m \
  --fill-empty-buckets \
  --start-ms 1780000000000 \
  --end-ms 1780086400000 \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --output /tmp/trend_regime_liquidation_5m.jsonl

PYTHONPATH=src uv run python scripts/check_liquidation_collector_health.py --data-dir data
```
Expected:
- `1m` and `5m` aggregation succeed
- health check prints JSON with readiness keys

**Step 4: Commit verification-only adjustments if needed**

```bash
git add .
git commit -m "chore: verify liquidation collector infra upgrade"
```

---

## Server Deployment Handoff

Only after all tasks above are green, use this deployment sequence on the server:

1. sync code to server
2. rebuild `crypto-alpha-lab:latest`
3. stop `trend-forceorder` and `trend-watchlist`
4. back up and rotate old files with checksum:
   - `trend_regime_force_orders_raw.jsonl`
   - `trend_regime_liquidation_cache.json`
   - `trend_regime_liquidation_hourly.jsonl`
5. remove old containers
6. run new containers
7. install/enable cron derivation jobs
8. run `check_liquidation_collector_health.py`
9. verify raw starts accumulating in a clean state
10. wait for a 24h acceptance window before reusing the archive for `1m` event research

---

## 24h Acceptance Gate

Do not declare deployment successful immediately after restart. After at least 24h, require a health summary equivalent to:

```json
{
  "raw_time_span_hours": 24.0,
  "raw_invalid_json_line_count": 0,
  "raw_duplicate_event_count": 0,
  "aggregate_1m_exists": true,
  "aggregate_1m_coverage_ratio_24h": 0.99,
  "aggregate_1m_max_gap_minutes_24h": 1,
  "aggregate_5m_exists": true,
  "aggregate_1h_exists": true,
  "watchlist_cache_updated": true,
  "research_ready_1m_24h": true
}
```

If this gate fails, do not restart `liquidation_shock_event_study` work.

---

## Done Definition

This plan is complete only when all of the following are true:

- raw event schema is explicit and versioned
- raw writer is append-only and supports flush / optional fsync
- `event_id` exists and aggregation deduplicates by it
- aggregation supports `1m / 5m / 1h`
- `1m / 5m` research files support zero-fill when requested
- watchlist cache compatibility is preserved
- health check reports both archive integrity and `research_ready_1m_24h`
- cron-based derivation is documented
- focused tests pass
- lint/format checks pass
- ops docs are updated
- the repo is ready for container rebuild and server restart

If these conditions are not met, do not rotate files or restart containers.
