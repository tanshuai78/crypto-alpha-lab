# Binance Liquidation Snapshot Event Study Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 下载并规范化 Binance `2024-01 / 2024-02 / 2024-03` 的 `1m` 价格与 historical `liquidationSnapshot` 样本，在保持现有 `1m shock -> fixed 5/10/15m response` 研究定义尽量不变的前提下，完成一次严格的数据源替换验证。

**Architecture:** 本计划优先复用现有 `src/research/liquidation_shock_event_study/` 的事件定义、shock detection、response map 与 review 逻辑，只新增 Binance Vision manifest probe、下载、checksum 校验、日频 liquidation snapshot 适配、严格的价格连续性审计以及跨月拼接 adapter。执行顺序严格是：先验证真实路径和 schema，再下载与解压，再做 continuity + zero-fill，再构建跨月统一 dataset，最后复用既有 event-study 链路输出 review。

**Post-Review Corrections:** 在执行与代码检查后，本计划补充三条必须保持的实现约束：

1. **Manifest-gated downloader**
   - downloader 不能只“兼容 manifest”，而必须默认消费 manifest probe 的结论。
   - `liquidation mode` 默认应由 manifest 驱动，而不是静态假设。
2. **Gap-reset lookback protection**
   - 若某个 symbol 的中间月份 continuity 失败，后续月份不得继续复用失败月份之前的历史行作为 `24h` lookback。
   - shock detection 必须按连续时序段分开运行。
3. **Reduced-universe downgrade**
   - 只要 required symbol-month coverage 不完整，最终 review 就不能输出 confirmed 类结论。
   - reduced universe 只能输出降级后的 `not_confirmed` 结论。

**Tech Stack:** Python 3.11, pytest, ruff, ZIP/CSV ingestion, Binance public data files, existing liquidation shock event-study modules, standalone scripts, JSON/JSONL, markdown review.

---

## Context

当前要验证的是：

- 如果把 `1m liquidation` 数据源从 Coinalyze 换成 Binance 公开 historical snapshot，
- 在尽量不修改既有研究定义的前提下，
- 是否能得到更可靠的 continuity / event density / structure 结论。

本计划默认：

- Exchange: `Binance-only`
- Symbols: `BTC / ETH / SOL / XRP / DOGE`
- Months: `2024-01`, `2024-02`, `2024-03`
- Inputs:
  - `1m klines`
  - `liquidationSnapshot`

但必须先承认两条数据语义边界：

1. `liquidationSnapshot` 不是完整强平逐笔 tape，而是 snapshot proxy。
2. `2024-01 ~ 2024-03` 是特定窗口，只能回答：
   - `structure_exists_in_this_archived_window`
   - 不能外推成全周期 liquidation alpha。

---

## Repository Boundary

本计划只允许新增或修改：

- `scripts/`
- `src/research/liquidation_shock_event_study/`
- `tests/scripts/`
- `tests/research/`
- `docs/reviews/`
- `reports/liquidation_shock_event_study/`
- `configs/base.py`

本计划不做：

- 新策略开发
- `src/strategies/` 修改
- live execution 逻辑
- collector infra 再次改造

---

## Data Layout Target

Phase 1 完成后，建议至少形成如下文件结构：

- `data/binance_liquidation_snapshot/raw/klines/monthly/2024-01/...zip`
- `data/binance_liquidation_snapshot/raw/klines/monthly/2024-02/...zip`
- `data/binance_liquidation_snapshot/raw/klines/monthly/2024-03/...zip`
- `data/binance_liquidation_snapshot/raw/liquidationSnapshot/daily/2024-01/...zip`
- `data/binance_liquidation_snapshot/raw/liquidationSnapshot/daily/2024-02/...zip`
- `data/binance_liquidation_snapshot/raw/liquidationSnapshot/daily/2024-03/...zip`
- `data/binance_liquidation_snapshot/extracted/...csv`
- `data/binance_liquidation_snapshot/processed/binance_snapshot_dataset.jsonl`
- `reports/liquidation_shock_event_study/binance_snapshot_manifest_probe.json`
- `reports/liquidation_shock_event_study/binance_snapshot_fetch_summary.json`
- `reports/liquidation_shock_event_study/binance_snapshot_continuity_summary.json`
- `reports/liquidation_shock_event_study/binance_snapshot_event_density_summary.json`
- `reports/liquidation_shock_event_study/binance_snapshot_dataset_summary.json`
- `reports/liquidation_shock_event_study/2026-05-31_binance_snapshot_event_study_summary.json`
- `docs/reviews/2026-05-31-binance-liquidation-snapshot-event-study-review.md`

Do not commit:

- `data/**/*.zip`
- extracted CSVs
- processed dataset JSONL

Only commit:

- `reports/*.json`
- `docs/reviews/*.md`
- tests / scripts / config changes

---

## Data Source Semantics

All summaries and reviews in this branch must explicitly carry:

- `data_source = binance_vision_liquidation_snapshot`
- `liquidation_data_semantics = binance_forceorder_largest_order_snapshot_per_symbol_per_1000ms`
- `not_complete_liquidation_tape = true`
- `notional_interpretation = snapshot_notional_proxy_not_total_market_liquidation`
- `sample_window = 2024-01_to_2024-03`
- `known_window_bias = Q1_2024_trending_crypto_market`
- `generalization_allowed = false`

This is mandatory. Without it, event density and shock notional will be misread as full-market liquidation volume.

---

## Task 1: Add Binance Snapshot Config And Path Contracts

**Files:**
- Modify: `configs/base.py`
- Create: `tests/test_binance_liquidation_snapshot_config.py`

**Step 1: Write the failing config test**

Add tests asserting the following constants exist and have sane types:

- `BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS`
- `BINANCE_LIQUIDATION_SNAPSHOT_MONTHS`
- `BINANCE_LIQUIDATION_SNAPSHOT_RAW_DIR`
- `BINANCE_LIQUIDATION_SNAPSHOT_EXTRACTED_DIR`
- `BINANCE_LIQUIDATION_SNAPSHOT_PROCESSED_DIR`
- `BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MIN_COVERAGE_RATIO`
- `BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MAX_GAP_MINUTES`
- `BINANCE_LIQUIDATION_SNAPSHOT_MIN_TOTAL_EVENTS`
- `BINANCE_LIQUIDATION_SNAPSHOT_MIN_EVENTS_PER_MONTH`

**Step 2: Run test to verify it fails**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/test_binance_liquidation_snapshot_config.py
```
Expected: FAIL.

**Step 3: Add minimal config**

Add exact constants to `configs/base.py`. Use baseline defaults:

- symbols = `("BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT")`
- months = `("2024-01", "2024-02", "2024-03")`
- continuity thresholds = `0.99`, `1`
- event density thresholds as Phase 1 defaults only

**Step 4: Re-run test**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/test_binance_liquidation_snapshot_config.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add configs/base.py tests/test_binance_liquidation_snapshot_config.py
git commit -m "feat: add Binance snapshot event-study config"
```

---

## Task 2: Add Binance Vision Manifest Probe Before Downloader Work

**Files:**
- Create: `scripts/probe_binance_liquidation_snapshot_manifest.py`
- Create: `tests/scripts/test_probe_binance_liquidation_snapshot_manifest.py`
- Generate: `reports/liquidation_shock_event_study/binance_snapshot_manifest_probe.json`

**Step 1: Write the failing tests**

Add tests asserting the probe reports:

- `source = binance_vision`
- `market = futures_um`
- `symbols`
- `months`
- `kline_monthly_available`
- `liquidation_monthly_available`
- `liquidation_daily_available`
- `selected_liquidation_download_mode`
- `missing_symbol_months`
- `decision`

Also add tests asserting:

- kline monthly may be selected directly
- liquidation must prefer daily when monthly is unavailable

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_probe_binance_liquidation_snapshot_manifest.py
```
Expected: FAIL.

**Step 3: Implement the manifest probe**

The probe must validate real Binance Vision file availability before downloader execution:

- monthly `1m klines`
- monthly `liquidationSnapshot` if present
- daily `liquidationSnapshot` as primary fallback
- sample ZIP existence
- sample `.CHECKSUM` existence
- sample CSV header parseability

Allowed decisions:

- `proceed_with_daily_liquidation`
- `proceed_with_monthly_liquidation`
- `data_unavailable`

**Step 4: Re-run tests**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_probe_binance_liquidation_snapshot_manifest.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/probe_binance_liquidation_snapshot_manifest.py tests/scripts/test_probe_binance_liquidation_snapshot_manifest.py reports/liquidation_shock_event_study/binance_snapshot_manifest_probe.json
git commit -m "feat: add Binance snapshot manifest probe"
```

---

## Task 3: Build Downloader With Daily Liquidation Fallback And Checksum Verification

**Files:**
- Create: `scripts/fetch_binance_liquidation_snapshot_history.py`
- Create: `tests/scripts/test_fetch_binance_liquidation_snapshot_history.py`

**Step 1: Write the failing tests**

Add tests covering:

- URL construction for monthly `1m` kline ZIPs
- URL construction for daily `liquidationSnapshot` ZIPs
- manifest-controlled liquidation mode selection
- dry-run summary output
- checksum-aware download summary

Example coverage:

- `test_builds_binance_um_monthly_kline_zip_url`
- `test_builds_binance_um_daily_liquidation_snapshot_zip_url`
- `test_manifest_selects_daily_liquidation_when_monthly_missing`
- `test_download_summary_requires_checksum_verification_for_phase1_inputs`

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_fetch_binance_liquidation_snapshot_history.py
```
Expected: FAIL.

**Step 3: Implement minimal downloader**

The script should support:

- `--symbols`
- `--months`
- `--raw-dir`
- `--extracted-dir`
- `--dry-run`
- `--skip-existing`

It should:

- download monthly `1m` kline ZIPs
- download daily `liquidationSnapshot` ZIPs by default
- only use monthly `liquidationSnapshot` if the manifest probe confirms it
- default to `manifest-selected` liquidation mode when no explicit override is passed
- fail closed if manifest reports `data_unavailable`
- download `.CHECKSUM` files
- verify checksums when available
- mark files as `checksum_unverified` when checksum is missing
- extract ZIPs into a deterministic directory layout

If checksum is missing or verification fails:

- allow quarantine / diagnostic status
- do not silently promote such files into the Phase 1 main dataset

Do not overbuild:

- no concurrency tuning first
- no multi-exchange support
- no daily kline fallback first

**Step 4: Re-run tests**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_fetch_binance_liquidation_snapshot_history.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/fetch_binance_liquidation_snapshot_history.py tests/scripts/test_fetch_binance_liquidation_snapshot_history.py
git commit -m "feat: add Binance snapshot downloader with checksum verification"
```

---

## Task 4: Add Continuity Audit With Sparse Liquidation Semantics

**Files:**
- Create: `scripts/audit_binance_liquidation_snapshot_continuity.py`
- Create: `tests/scripts/test_audit_binance_liquidation_snapshot_continuity.py`

**Step 1: Write the failing tests**

Add tests asserting the continuity audit reports, per symbol and per month:

- `price_coverage_ratio`
- `price_missing_bucket_count`
- `price_max_gap_minutes`
- `price_rows`
- `liquidation_files_found`
- `liquidation_files_expected`
- `liquidation_file_coverage_ratio`
- `liquidation_snapshot_rows`
- `zero_filled_liquidation_minutes`
- `dataset_rows`
- `joined_rows`
- `passes_continuity_gate`

Also add tests asserting:

- price continuity must satisfy `coverage_ratio >= 0.99`
- price continuity must satisfy `max_gap_minutes <= 1`
- a month with zero liquidation snapshots but complete daily files can still pass the liquidation-side continuity gate

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_audit_binance_liquidation_snapshot_continuity.py
```
Expected: FAIL.

**Step 3: Implement the continuity audit**

The script must:

- validate `1m` price continuity on a strict expected minute grid
- validate liquidation side by daily file availability and schema parseability
- not treat sparse liquidation minutes as continuity failure
- zero-fill missing liquidation minutes after joining onto the continuous price grid
- emit:
  - `binance_snapshot_continuity_summary.json`

Reject a symbol-month from Phase 1 if:

- price continuity fails
- liquidation file coverage fails
- join result is unusable

Do not reject just because raw liquidation rows are sparse.

**Step 4: Re-run tests**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_audit_binance_liquidation_snapshot_continuity.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/audit_binance_liquidation_snapshot_continuity.py tests/scripts/test_audit_binance_liquidation_snapshot_continuity.py
git commit -m "feat: add Binance snapshot continuity audit"
```

---

## Task 5: Build Cross-Month Binance Dataset Adapter Into Existing Event-Study Format

**Files:**
- Create: `scripts/build_binance_liquidation_snapshot_event_dataset.py`
- Create: `tests/scripts/test_build_binance_liquidation_snapshot_event_dataset.py`
- Modify: `src/research/liquidation_shock_event_study/event_contract.py` only if a minimal adapter hook is required
- Add regression if needed to: `tests/research/test_liquidation_shock_response_map.py`

**Step 1: Write the failing tests**

Add tests asserting the builder:

- reads Binance CSV inputs
- emits dataset rows in the same format expected by the current event-study pipeline
- preserves `1m shock` semantics
- excludes symbol-months that fail continuity
- concatenates `2024-01 / 2024-02 / 2024-03` into one continuous time series per symbol before shock detection
- does not artificially lose the first 24h of `2024-02-01` or `2024-03-01`
- resets lookback across non-contiguous segments so a failed middle month cannot leak stale history into a later month
- preserves the rule that response excludes the 5m bar containing the shock minute

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_build_binance_liquidation_snapshot_event_dataset.py tests/research/test_liquidation_shock_response_map.py
```
Expected: FAIL.

**Step 3: Implement the dataset builder**

The builder must:

- adapt Binance historical CSVs into the same shape consumed by the current `liquidation_shock_event_study` pipeline
- concatenate all month slices into one continuous time series per symbol before shock detection
- preserve contiguous month stitching only across valid adjacent minute histories
- ensure downstream shock detection is executed per contiguous time segment, not on a symbol-level concatenation that skips failed middle months
- write processed dataset JSONL to:
  - `data/binance_liquidation_snapshot/processed/binance_snapshot_dataset.jsonl`
- write summary JSON to:
  - `reports/liquidation_shock_event_study/binance_snapshot_dataset_summary.json`

Do not change core event-study logic in this task unless the adapter absolutely requires a minimal compatibility hook.

**Step 4: Re-run tests**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_build_binance_liquidation_snapshot_event_dataset.py tests/research/test_liquidation_shock_response_map.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/build_binance_liquidation_snapshot_event_dataset.py tests/scripts/test_build_binance_liquidation_snapshot_event_dataset.py tests/research/test_liquidation_shock_response_map.py src/research/liquidation_shock_event_study/event_contract.py
git commit -m "feat: add Binance snapshot event-study dataset builder"
```

---

## Task 6: Add Event Density Gate And Binance Snapshot Review Output

**Files:**
- Create: `scripts/review_binance_liquidation_snapshot_event_study.py`
- Create: `tests/scripts/test_review_binance_liquidation_snapshot_event_study.py`

**Step 1: Write the failing tests**

Add tests asserting the review can:

- compute total event count
- compute per-month event count
- compute event density by symbol
- compute event density by side
- compute event density by symbol-month and symbol-side
- downgrade when required symbol-month coverage is incomplete
- reject if total events are too low
- reject if any month is too sparse
- emit one of:
  - `binance_snapshot_data_failed`
  - `binance_snapshot_event_density_failed`
  - `binance_snapshot_structure_not_confirmed`
  - `binance_snapshot_structure_confirmed_for_q1_2024_only`

**Step 2: Run tests to verify they fail**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_binance_liquidation_snapshot_event_study.py
```
Expected: FAIL.

**Step 3: Implement review wrapper**

The review should:

- reuse existing shock detection / response map logic
- add:
  - per-month continuity gate summary
  - per-month event density summary
  - by-symbol / by-side event density summary
  - universe integrity summary (`required_symbol_months`, `passed_symbol_months`, `missing_symbol_months`, `universe_integrity_ok`)
  - semantics note
  - window-bias note
  - final decision state
- emit:
  - `2026-05-31_binance_snapshot_event_study_summary.json`
  - `2026-05-31-binance-liquidation-snapshot-event-study-review.md`

The review must explicitly state that any positive result is valid only for `Q1 2024`.
The review must also explicitly state that a reduced or proxy universe cannot be treated as a full-scope replacement validation.

**Step 4: Re-run tests**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_binance_liquidation_snapshot_event_study.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/review_binance_liquidation_snapshot_event_study.py tests/scripts/test_review_binance_liquidation_snapshot_event_study.py
git commit -m "feat: add Binance snapshot event-study review"
```

---

## Task 7: Run End-To-End Phase 1 On 2024-01 / 2024-02 / 2024-03

**Files:**
- Generate: `reports/liquidation_shock_event_study/binance_snapshot_manifest_probe.json`
- Generate: `reports/liquidation_shock_event_study/binance_snapshot_fetch_summary.json`
- Generate: `reports/liquidation_shock_event_study/binance_snapshot_continuity_summary.json`
- Generate: `reports/liquidation_shock_event_study/binance_snapshot_event_density_summary.json`
- Generate: `reports/liquidation_shock_event_study/binance_snapshot_dataset_summary.json`
- Generate: `reports/liquidation_shock_event_study/2026-05-31_binance_snapshot_event_study_summary.json`
- Generate: `docs/reviews/2026-05-31-binance-liquidation-snapshot-event-study-review.md`

**Step 1: Run manifest probe**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/probe_binance_liquidation_snapshot_manifest.py
```
Expected: manifest decision resolves to a real Binance Vision liquidation download mode before download starts.

**Step 2: Download and extract inputs**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/fetch_binance_liquidation_snapshot_history.py
```
Expected: ZIP files downloaded, checksum-checked where available, and extracted for all configured symbols/months.

**Step 3: Run continuity audit**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/audit_binance_liquidation_snapshot_continuity.py
```
Expected: continuity summary JSON created.

**Step 4: Build dataset**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/build_binance_liquidation_snapshot_event_dataset.py
```
Expected: processed dataset JSONL created under `data/`.

**Step 5: Run review**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/review_binance_liquidation_snapshot_event_study.py
```
Expected: markdown review + JSON summary created.

**Step 6: Commit generated Phase 1 evidence**

```bash
git add reports/liquidation_shock_event_study/*.json docs/reviews/2026-05-31-binance-liquidation-snapshot-event-study-review.md
git commit -m "feat: run Binance snapshot event-study phase 1"
```

Do not commit:

- `data/**/*.zip`
- extracted CSVs
- processed dataset JSONL

---

## Task 8: Verification And Documentation Closure

**Files:**
- Verify: `docs/plans/2026-05-31-binance-liquidation-snapshot-event-study-design.md`
- Verify: `docs/plans/2026-05-31-binance-liquidation-snapshot-event-study-implementation-plan.md`

**Step 1: Run focused tests**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q \
  tests/test_binance_liquidation_snapshot_config.py \
  tests/scripts/test_probe_binance_liquidation_snapshot_manifest.py \
  tests/scripts/test_fetch_binance_liquidation_snapshot_history.py \
  tests/scripts/test_audit_binance_liquidation_snapshot_continuity.py \
  tests/scripts/test_build_binance_liquidation_snapshot_event_dataset.py \
  tests/scripts/test_review_binance_liquidation_snapshot_event_study.py \
  tests/research/test_liquidation_shock_detection.py \
  tests/research/test_liquidation_shock_response_map.py \
  tests/research/test_liquidation_shock_event_contract.py
```
Expected: PASS.

**Step 2: Run lint on changed files**

Run:
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
uv run ruff check scripts tests/scripts tests/research configs/base.py
```
Expected: PASS, or only pre-existing unrelated failures are documented explicitly.

**Step 3: Sanity-check review semantics**

Confirm the final review clearly states:

- this was a data-source replacement validation
- not a live strategy promotion decision
- whether continuity, event density, and cross-month structure passed independently
- that the liquidation data is snapshot-proxy semantics, not full liquidation tape
- that any positive result is only valid for `Q1 2024`, not generalized

**Step 4: Commit plan closure adjustments if needed**

```bash
git add docs/plans docs/reviews
git commit -m "docs: close Binance snapshot event-study phase 1"
```

---

## Deferred Enhancements (Do Not Implement In Phase 1)

Only if Task 7 ends with `binance_snapshot_structure_confirmed_for_q1_2024_only`:

1. Expand to more months beyond `2024-01 / 2024-02 / 2024-03`
2. Add regime labels to month windows
3. Compare monthly structure by regime
4. Audit Binance snapshot duplicates / schema anomalies more deeply
5. Compare Binance historical snapshot against self-collected future raw archive
6. Add Binance-specific event-definition sensitivity
7. Add cost / execution delay sensitivity

These enhancements are explicitly:

- `out_of_scope_for_phase1`
- `only_if_phase1_passes`

---

## Final Acceptance For Phase 1

This branch is considered successfully completed only if all of the following are true:

- manifest probe selected a real Binance Vision download mode before downloader execution
- Binance historical files were downloaded and normalized successfully
- checksum verification status is recorded for Phase 1 inputs
- continuity summary exists and applies strict gates on price continuity
- liquidation file availability is audited separately from sparse minute rows
- dataset builder emits Binance-adapted event-study rows from one continuous cross-month time series per symbol
- shock detection does not leak lookback across failed middle months or non-contiguous segments
- event density summary exists and includes month / symbol / side views
- universe integrity summary exists and blocks confirmed decisions when required symbol-month coverage is incomplete
- final review lands on one of the allowed decision states
- no large raw / extracted / processed dataset files are committed
- all focused tests pass
