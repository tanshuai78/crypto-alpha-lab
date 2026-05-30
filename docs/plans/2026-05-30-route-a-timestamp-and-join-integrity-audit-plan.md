# Route A Timestamp And Join Integrity Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 查清 Route A 的 `2024` 时间戳来源，验证当前 forceOrder→raw→hourly→replay 链路的 canonical timestamp 与小时桶完整性，并落地最小修复、审计产物与回归测试。

**Architecture:** 本计划不改策略定义，不碰 execution/live trading 逻辑，只审计并修复 Route A 的数据面完整性。重点不是“把旧 bucket floor 一下”，而是明确 raw 记录的 canonical timestamp source，识别并记录 event timestamp 与 provided bucket 的冲突，再分别加固 raw→hourly 聚合与 hourly→replay join，最后用干净产物重新验证 Route A 是否仍存在旧 artifact、聚合缺口或 collector regression。

**Tech Stack:** Python 3.11, pytest, JSONL, Docker runtime context, Binance forceOrder WebSocket raw records, hourly aggregation, replay join summaries, review markdown + integrity snapshot JSON.

---

## Background

当前证据已经表明：

- `Route B` 已打通，`joined_count = 2393`，不再是主阻塞。
- `Route A` 当前服务器文件不可信：`trend_regime_force_orders_raw.jsonl` 仅 1 行、`trend_regime_liquidation_hourly.jsonl` 仅 1 行，且该 hourly 记录对应 `2024-05-27T23:20:00Z`，不符合当前 2026 replay 窗口。
- 现有代码审计显示两个真实风险点：
  - `scripts/aggregate_trend_regime_liquidations.py` 直接信任输入 `hour_bucket_ms`，没有基于 canonical event timestamp 重算 bucket。
  - `scripts/replay_trend_regime_shadow.py` 的 `apply_hourly_liquidation_history(...)` 对 hourly 侧 bucket 缺少 defensive floor 和 invalid bucket 计数。
- 仅对旧 bucket 做 floor 不能解释 `2024` 问题。必须确认 raw 里哪个时间字段才是可信主源，并记录 provided bucket 与 computed bucket 的 mismatch。

本计划的目标不是继续解释旧脏数据，而是把 Route A 数据链路的完整性查清、加固，并输出后续 agent 可以直接消费的 JSON 审计快照。

---

### Task 1: Establish Failing Audit Tests For Canonical Timestamp And Bucket Integrity

**Files:**
- Modify: `tests/scripts/test_aggregate_trend_regime_liquidations.py`
- Modify: `tests/scripts/test_replay_trend_regime_shadow.py`

**Step 1: Add failing test for aggregator floor behavior using a truly non-hour-aligned bucket**

Add a test that feeds `aggregate_raw_to_hourly(...)` a raw record with a clearly non-hour-aligned bucket and asserts the output is floored to the UTC hour.

```python
def test_aggregate_raw_to_hourly_floors_non_hour_bucket_ms():
    records = [
        {
            "symbol": "BTC/USDT",
            "hour_bucket_ms": 1716852300000,  # explicit non-hour-aligned bucket
            "notional_usdt": 34000.0,
            "liquidation_side": "long_liquidation",
        }
    ]

    rows = aggregate_raw_to_hourly(records)

    assert rows[0]["hour_bucket_ms"] == 1716850800000
```

**Step 2: Run the failing test**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_aggregate_trend_regime_liquidations.py -k floors_non_hour_bucket_ms
```
Expected: FAIL because aggregator currently preserves the incoming raw bucket.

**Step 3: Add failing test that the audit wrapper prefers canonical event timestamp over stale bucket**

Add a test where the raw record contains both a stale `hour_bucket_ms` and a valid current `timestamp_ms`. Assert the audit-enabled helper uses the event timestamp-derived hour bucket, not the stale provided bucket.

```python
def test_aggregate_raw_to_hourly_with_audit_prefers_event_timestamp_over_stale_hour_bucket_ms():
    records = [
        {
            "symbol": "BTC/USDT",
            "timestamp_ms": 1780001100000,
            "hour_bucket_ms": 1716852300000,
            "notional_usdt": 34000.0,
            "liquidation_side": "long_liquidation",
        }
    ]

    rows, audit = aggregate_raw_to_hourly_with_audit(records)

    assert rows[0]["hour_bucket_ms"] == 1780000800000
    assert audit["bucket_event_time_mismatch_count"] == 1
```

**Step 4: Add failing test for missing timestamp handling on the audit wrapper**

```python
def test_aggregate_raw_to_hourly_with_audit_skips_missing_all_timestamps():
    records = [{
        "symbol": "BTC/USDT",
        "notional_usdt": 34000.0,
        "liquidation_side": "long_liquidation",
    }]

    rows, audit = aggregate_raw_to_hourly_with_audit(records)

    assert rows == []
    assert audit["missing_timestamp_count"] == 1
```

**Step 5: Add failing test for replay join defensive floor**

Add a test that feeds `apply_hourly_liquidation_history(...)` an hourly record with a non-hour-aligned bucket and a market row in the matching hour, and assert join still succeeds.

```python
def test_apply_hourly_liquidation_history_floors_hourly_bucket_before_join():
    rows = [{
        "symbol": "BTC/USDT",
        "timestamp_ms": 1716851100000,
    }]
    hourly = [{
        "symbol": "BTC/USDT",
        "hour_bucket_ms": 1716852300000,
        "liquidation_notional_1h_usdt": 34000.0,
        "long_liquidation_notional_1h_usdt": 34000.0,
        "short_liquidation_notional_1h_usdt": 0.0,
    }]

    patched, summary = apply_hourly_liquidation_history(rows, hourly)

    assert patched[0]["liquidation_notional_1h_usdt"] == 34000.0
    assert summary["liquidation_rows_joined_count"] == 1
```

**Step 6: Add failing test for invalid hourly bucket skip accounting**

```python
def test_apply_hourly_liquidation_history_skips_invalid_hourly_bucket():
    rows = [{"symbol": "BTC/USDT", "timestamp_ms": 1716851100000}]
    hourly = [{
        "symbol": "BTC/USDT",
        "hour_bucket_ms": 0,
        "liquidation_notional_1h_usdt": 34000.0,
    }]

    patched, summary = apply_hourly_liquidation_history(rows, hourly)

    assert summary["invalid_hourly_bucket_count"] == 1
    assert summary["liquidation_rows_joined_count"] == 0
    assert "liquidation_notional_1h_usdt" not in patched[0]
```

**Step 7: Run the failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_aggregate_trend_regime_liquidations.py \
  tests/scripts/test_replay_trend_regime_shadow.py
```
Expected: FAIL on the new Route A integrity cases.

**Step 8: Commit red tests**

```bash
git add tests/scripts/test_aggregate_trend_regime_liquidations.py tests/scripts/test_replay_trend_regime_shadow.py
git commit -m "test: add route-a timestamp integrity audit cases"
```

---

### Task 2: Fix Route A Aggregation And Replay Join Using Canonical Timestamp Rules

**Files:**
- Modify: `scripts/aggregate_trend_regime_liquidations.py`
- Modify: `scripts/replay_trend_regime_shadow.py`
- Test: `tests/scripts/test_aggregate_trend_regime_liquidations.py`
- Test: `tests/scripts/test_replay_trend_regime_shadow.py`

**Step 1: Add canonical timestamp resolver to aggregator**

Introduce a helper that resolves the best available event timestamp in this order:

```python
def canonical_liquidation_timestamp_ms(rec: dict[str, Any]) -> int | None:
    for key in ("event_time_ms", "trade_time_ms", "E", "T", "timestamp_ms"):
        value = _int_or_none(rec.get(key))
        if value and value > 0:
            return value
    fallback = _int_or_none(rec.get("hour_bucket_ms"))
    return fallback if fallback and fallback > 0 else None
```

**Step 2: Change aggregation to recompute bucket from canonical event timestamp**

Do not use provided `hour_bucket_ms` as the primary source. Use it only for mismatch auditing / fallback.

Required behavior:
- Parse any provided `hour_bucket_ms` or legacy `hour_bucket_utc` into a comparable bucket when available
- Compute `bucket_ms = floor_hour_ms(canonical_event_ts_ms)`
- Record mismatch if provided bucket exists and differs from computed bucket
- Skip records with no usable timestamp and increment `missing_timestamp_count`

Expected implementation shape:

```python
event_ts_ms = canonical_liquidation_timestamp_ms(rec)
if event_ts_ms is None:
    audit["missing_timestamp_count"] += 1
    continue

computed_bucket_ms = hour_bucket_ms(event_ts_ms)
provided_bucket_ms = ...  # parsed from hour_bucket_ms or hour_bucket_utc if present
if provided_bucket_ms is not None and provided_bucket_ms != computed_bucket_ms:
    audit["bucket_event_time_mismatch_count"] += 1
```

**Step 3: Ensure aggregator never emits non-hour-aligned buckets**

All emitted `hour_bucket_ms` values must be floored computed buckets, never passthrough stale values.

**Step 4: Add a backward-compatible audit wrapper instead of changing the existing return signature**

Do **not** change the return type of `aggregate_raw_to_hourly(...)`, because existing tests and the CLI already consume it as `rows = aggregate_raw_to_hourly(...)`.

Required interface strategy:
- keep `aggregate_raw_to_hourly(...) -> rows` unchanged
- add `aggregate_raw_to_hourly_with_audit(...) -> (rows, audit)`

The audit-enabled helper must expose:
- `missing_timestamp_count`
- `bucket_event_time_mismatch_count`
- `non_hour_aligned_bucket_count`
- optional `bad_records_sample`

`aggregate_raw_to_hourly(...)` should become a thin compatibility wrapper around the new helper.

**Step 5: Harden replay join bucket handling**

In `apply_hourly_liquidation_history(...)`:
- skip invalid / zero / missing hourly buckets
- increment `invalid_hourly_bucket_count`
- floor all incoming hourly buckets before lookup
- preserve current market-row-side flooring

Expected implementation shape:

```python
raw_bucket = _number_or_none(rec.get("hour_bucket_ms"))
if raw_bucket is None or raw_bucket <= 0:
    invalid_hourly_bucket_count += 1
    continue
bucket = int(raw_bucket) // 3_600_000 * 3_600_000
```

**Step 6: Run targeted tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_aggregate_trend_regime_liquidations.py \
  tests/scripts/test_replay_trend_regime_shadow.py
```
Expected: PASS for the new cases and no regressions.

**Step 7: Keep CLI and legacy tests on the compatibility path**

Ensure:
- existing tests that call `aggregate_raw_to_hourly(...)` remain unchanged unless they explicitly need audit data
- CLI `main()` either keeps calling `aggregate_raw_to_hourly(...)` or explicitly switches to the new helper and discards audit when writing hourly JSONL
- no existing caller breaks due to a tuple return value

**Step 8: Commit the fix**

```bash
git add scripts/aggregate_trend_regime_liquidations.py scripts/replay_trend_regime_shadow.py tests/scripts/test_aggregate_trend_regime_liquidations.py tests/scripts/test_replay_trend_regime_shadow.py
git commit -m "fix: harden route-a timestamp sourcing and replay joins"
```

---

### Task 3: Audit The 2024 Artifact Source And Emit Machine-Readable Snapshot

**Files:**
- Create: `docs/reviews/2026-05-30-route-a-timestamp-and-join-integrity-audit-review.md`
- Create: `reports/trend_regime/2026-05-30_route_a_integrity_snapshot.json`
- Reference: `scripts/collect_trend_regime_force_orders.py`
- Reference: `scripts/aggregate_trend_regime_liquidations.py`
- Reference: `data/trend_regime_force_orders_raw.jsonl` (local if available)
- Reference: `data/trend_regime_liquidation_hourly.jsonl` (local if available)

**Step 1: Add a forensic checklist section to the review**

Document the exact checks required to explain the `2024` record:
- Is the old hourly file generated by current code or a stale artifact?
- Does the old raw file already contain non-hour bucket values?
- Is `provided_hour_bucket_ms` consistent with canonical event timestamp?
- Is the file from a previous deployment / previous format?

**Step 2: Define the integrity snapshot JSON schema**

The snapshot must capture machine-readable facts, e.g.:

```json
{
  "route": "A",
  "audit_date": "2026-05-30",
  "raw_file": {
    "path": "data/trend_regime_force_orders_raw.jsonl",
    "line_count": 1,
    "min_event_time_ms": null,
    "max_event_time_ms": null,
    "min_hour_bucket_ms": 1716852000000,
    "max_hour_bucket_ms": 1716852000000,
    "non_hour_aligned_bucket_count": 1,
    "bucket_event_time_mismatch_count": 0
  },
  "hourly_file": {
    "path": "data/trend_regime_liquidation_hourly.jsonl",
    "line_count": 1,
    "non_hour_aligned_bucket_count": 1
  },
  "replay_join": {
    "liquidation_rows_joined_count": 0,
    "invalid_hourly_bucket_count": 0
  },
  "decision": "route_a_old_artifact_only"
}
```

**Step 3: Record current known evidence in both markdown and JSON**

Include the currently established facts:
- raw file line count was `1`
- hourly file line count was `1`
- hourly timestamp mapped to `2024-05-27T23:20:00Z`
- current collector code floors hour bucket on raw write
- therefore old file is not sufficient evidence that current collector still emits bad buckets

**Step 4: Commit the review draft and snapshot skeleton**

```bash
git add docs/reviews/2026-05-30-route-a-timestamp-and-join-integrity-audit-review.md reports/trend_regime/2026-05-30_route_a_integrity_snapshot.json
git commit -m "docs: add route-a timestamp integrity review and snapshot"
```

---

### Task 4: Reproduce And Verify With Clean Route A Artifacts

**Files:**
- Reference: `scripts/collect_trend_regime_force_orders.py`
- Reference: `scripts/aggregate_trend_regime_liquidations.py`
- Reference: `scripts/review_trend_liquidation_cascade.py`
- Update: `docs/reviews/2026-05-30-route-a-timestamp-and-join-integrity-audit-review.md`
- Update: `reports/trend_regime/2026-05-30_route_a_integrity_snapshot.json`

**Step 1: Define a forensics-safe server reset procedure**

Commands to run on server must preserve evidence before rotation:

```bash
docker stop trend-watchlist trend-forceorder

docker ps --format '{{.Names}}' | rg 'trend-forceorder|trend-watchlist' && exit 1 || true

cd /root/crypto-alpha-lab
ts=$(date +%Y%m%d_%H%M%S)
mkdir -p data/route_a_backups/$ts
cp -a data/trend_regime_liquidation_cache.json data/route_a_backups/$ts/ 2>/dev/null || true
cp -a data/trend_regime_force_orders_raw.jsonl data/route_a_backups/$ts/ 2>/dev/null || true
cp -a data/trend_regime_liquidation_hourly.jsonl data/route_a_backups/$ts/ 2>/dev/null || true
sha256sum data/route_a_backups/$ts/* > data/route_a_backups/$ts/SHA256SUMS 2>/dev/null || true

[ -f data/trend_regime_liquidation_cache.json ] && mv data/trend_regime_liquidation_cache.json data/trend_regime_liquidation_cache.json.$ts.disabled
[ -f data/trend_regime_force_orders_raw.jsonl ] && mv data/trend_regime_force_orders_raw.jsonl data/trend_regime_force_orders_raw.jsonl.$ts.disabled
[ -f data/trend_regime_liquidation_hourly.jsonl ] && mv data/trend_regime_liquidation_hourly.jsonl data/trend_regime_liquidation_hourly.jsonl.$ts.disabled

docker start trend-forceorder trend-watchlist
```

**Step 2: Define the first-event validation commands**

Once a real event appears:

```bash
wc -l /root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl
sed -n '1,5p' /root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl
PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime_force_orders_raw.jsonl \
  --output data/trend_regime_liquidation_hourly.jsonl
tail -n 5 /root/crypto-alpha-lab/data/trend_regime_liquidation_hourly.jsonl
```

**Step 3: Update the integrity snapshot after fresh regeneration**

Fill in:
- fresh raw line count
- min/max event timestamp
- min/max hour bucket
- non-hour-aligned counts
- mismatch counts
- replay join invalid bucket count
- final Route A state decision

**Step 4: Define acceptance rules**

Route A integrity is accepted only if:
- new raw file event timestamps are current-window timestamps, not 2024 residue
- new hourly rows use UTC hour floor, not minute-level buckets
- replay join with a matching test row succeeds after defensive flooring
- no new collector-side `2024` or stale-year timestamps are observed in freshly generated raw events

If new artifacts still show 2024 or stale-year raw timestamps, escalate to collector-side root cause investigation rather than resuming Route C.

**Step 5: Commit the execution checklist updates**

```bash
git add docs/reviews/2026-05-30-route-a-timestamp-and-join-integrity-audit-review.md reports/trend_regime/2026-05-30_route_a_integrity_snapshot.json
git commit -m "docs: add route-a clean reproduction checklist"
```

---

### Task 5: Final Verification And Acceptance

**Files:**
- Verify: `scripts/aggregate_trend_regime_liquidations.py`
- Verify: `scripts/replay_trend_regime_shadow.py`
- Verify: `tests/scripts/test_collect_trend_regime_force_orders.py`
- Verify: `tests/scripts/test_aggregate_trend_regime_liquidations.py`
- Verify: `tests/scripts/test_replay_trend_regime_shadow.py`
- Verify: `tests/scripts/test_review_trend_liquidation_cascade.py`
- Verify: `docs/reviews/2026-05-30-route-a-timestamp-and-join-integrity-audit-review.md`
- Verify: `reports/trend_regime/2026-05-30_route_a_integrity_snapshot.json`

**Step 1: Run full targeted verification**

```bash
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_collect_trend_regime_force_orders.py \
  tests/scripts/test_aggregate_trend_regime_liquidations.py \
  tests/scripts/test_replay_trend_regime_shadow.py \
  tests/scripts/test_review_trend_liquidation_cascade.py
```
Expected: all pass.

**Step 2: Verify review doc has no placeholders**

```bash
rg -n 'TODO|TBD|XXX|\[ \]' docs/reviews/2026-05-30-route-a-timestamp-and-join-integrity-audit-review.md
```
Expected: no matches.

**Step 3: Verify snapshot JSON exists and is populated**

```bash
cat reports/trend_regime/2026-05-30_route_a_integrity_snapshot.json
```
Expected: valid JSON with route/raw/hourly/replay_join/decision fields.

**Step 4: Verify final git diff scope**

```bash
git status --short
```
Expected: only Route A audit / fix files are modified.

**Step 5: Final commit**

```bash
git add scripts/aggregate_trend_regime_liquidations.py \
  scripts/replay_trend_regime_shadow.py \
  tests/scripts/test_aggregate_trend_regime_liquidations.py \
  tests/scripts/test_replay_trend_regime_shadow.py \
  docs/reviews/2026-05-30-route-a-timestamp-and-join-integrity-audit-review.md \
  reports/trend_regime/2026-05-30_route_a_integrity_snapshot.json

git commit -m "fix: audit and harden route-a timestamp integrity"
```

---

## Done Definition

This plan is complete only when all of the following are true:

- Route A aggregation uses canonical event timestamp as primary source for computing hourly bucket.
- `aggregate_raw_to_hourly(...)` remains backward-compatible for existing callers, while a dedicated audit-enabled helper exposes `(rows, audit)`.
- Aggregator records bucket/event timestamp mismatch counts and never emits non-hour-aligned `hour_bucket_ms`.
- Replay join floors hourly buckets defensively and records invalid-hourly-bucket counts.
- New regression tests exist and pass for canonical timestamp sourcing, mismatch accounting, bucket flooring, and replay skip behavior.
- A markdown review artifact exists that explains why the `2024` record cannot be trusted as current Route A behavior without fresh regeneration.
- A machine-readable integrity snapshot JSON exists and captures raw/hourly/join evidence.
- The server reset / fresh artifact validation procedure is documented with evidence-preserving backup steps.

## Done Decision

After completion, Route A should be classified into one of five states:

1. `route_a_old_artifact_only`
   - Old 2024 record explained as residue; fresh generation not yet observed.

2. `route_a_current_code_clean_waiting_for_events`
   - Code path verified clean; Route A still waiting on real forceOrder events.

3. `route_a_raw_timestamp_clean_aggregator_fixed`
   - Fresh raw timestamps are current and clean; issue traced to old aggregator / old artifact handling.

4. `route_a_replay_join_fixed_but_no_live_overlap`
   - Bucket integrity and replay join are fixed, but Route A still lacks enough real overlap with replay window.

5. `route_a_collector_regression_confirmed`
   - Freshly generated raw artifacts still show stale-year timestamps or malformed hour buckets; collector path needs deeper bugfix.
