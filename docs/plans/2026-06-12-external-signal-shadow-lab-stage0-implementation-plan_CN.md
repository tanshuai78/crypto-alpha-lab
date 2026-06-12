# External Signal Shadow Lab Stage 0 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first fixture-only External Signal Shadow Lab pipeline: external event schema, local Risk Guard, optional CUSUM confirmation, triple-barrier shadow orders, replay summary, and review output.

**Architecture:** Implement a new isolated research package under `src/research/external_signal_shadow/`. Stage 0 does not call real external APIs, does not connect wallets, and does not produce executable orders. It only consumes fixture events and fixture price bars, then emits JSON summaries for research review.

**Tech Stack:** Python standard library, dataclasses, pytest, existing `configs/base.py`, existing `scripts/` CLI pattern, existing `reports/` and `docs/reviews/` artifact style.

---

## 0. Non-Negotiable Boundaries

This implementation is research-only.

Do not implement:

- wallet login;
- API key handling;
- external API connector;
- CEX/DEX order placement;
- transaction signing;
- swap;
- copy-trading;
- paper/live trading adapter;
- ML model;
- parameter optimization.

Stage 0 must prove only this:

```text
fixture external events + fixture price bars
-> risk guard
-> no-CUSUM and CUSUM-confirmed replay branches
-> triple-barrier shadow labels
-> summary + review
```

Implementation may mention commit checkpoints in this plan, but in this project do **not** commit automatically unless the user explicitly asks.

---

## 0.1 Review Fixes Incorporated

This revision incorporates the required review fixes before implementation:

- `PriceBar` must include `bar_start_ms` and `bar_end_ms`; trigger-containing bars cannot be used for entry or barrier evaluation.
- CUSUM must use the last completed pre-event close only as a return baseline and must never trigger from pre-event movement.
- CUSUM threshold calculations use log-return units internally; bps are display/config units only.
- Forbidden executable fields must be checked recursively in all event payloads.
- Risk Guard rules must branch between CEX events and on-chain token events.
- no-CUSUM and CUSUM branches must be labeled as baseline/control and confirmation-filtered shadow branches, not strategies.
- Stage 0 pass/fail is infrastructure readiness only and must not depend on positive PnL.
- Fixed TP/SL/holding parameters are sanity-check parameters, not reusable strategy parameters.
- Fixtures must include same-bar TP/SL conservative stop-loss ordering.
- CUSUM must explicitly test fallback to fixed threshold when pre-event bars are insufficient.

Default verification commands use `PYTHONPATH=src uv run pytest ...`. If the local environment already has a working virtualenv, an executor may use `.venv/bin/pytest` equivalently, but must report the exact command used.

---

## 1. Expected Output Artifacts

Create these runtime outputs:

```text
reports/external_signal_shadow/stage0_shadow_replay_summary.json
docs/reviews/2026-06-12-external-signal-shadow-lab-stage0-review_CN.md
```

Create these fixture files:

```text
tests/fixtures/external_signal_shadow/stage0_events.jsonl
tests/fixtures/external_signal_shadow/stage0_price_bars.jsonl
```

Create these source files:

```text
src/research/external_signal_shadow/__init__.py
src/research/external_signal_shadow/models.py
src/research/external_signal_shadow/risk_guard.py
src/research/external_signal_shadow/cusum.py
src/research/external_signal_shadow/triple_barrier.py
src/research/external_signal_shadow/replay.py
src/research/external_signal_shadow/summary.py
```

Create these scripts:

```text
scripts/run_external_signal_shadow_stage0.py
scripts/review_external_signal_shadow_stage0.py
```

Create these tests:

```text
tests/research/test_external_signal_shadow_models.py
tests/research/test_external_signal_shadow_risk_guard.py
tests/research/test_external_signal_shadow_cusum.py
tests/research/test_external_signal_shadow_triple_barrier.py
tests/research/test_external_signal_shadow_replay.py
tests/research/test_external_signal_shadow_summary.py
tests/scripts/test_run_external_signal_shadow_stage0.py
tests/scripts/test_review_external_signal_shadow_stage0.py
```

---

## 2. Configuration Constants

### Task 1: Add Stage 0 Constants

**Files:**

- Modify: `configs/base.py`
- Test: `tests/research/test_external_signal_shadow_models.py`

**Step 1: Add failing config test**

Add this test near the top of `tests/research/test_external_signal_shadow_models.py`:

```python
def test_external_signal_shadow_stage0_config_constants_exist():
    from configs import base

    assert base.EXTERNAL_SIGNAL_SHADOW_MIN_LIQUIDITY_USD == 500_000.0
    assert base.EXTERNAL_SIGNAL_SHADOW_MAX_SELL_TAX_PCT == 5.0
    assert base.EXTERNAL_SIGNAL_SHADOW_MAX_TOP10_HOLDER_SHARE == 0.35
    assert base.EXTERNAL_SIGNAL_SHADOW_MAX_SMART_MONEY_EXIT_RATE == 0.70
    assert base.EXTERNAL_SIGNAL_SHADOW_CEX_MAX_SPREAD_BPS == 10.0
    assert base.EXTERNAL_SIGNAL_SHADOW_CEX_MIN_DEPTH_10BPS_USD == 100_000.0
    assert base.EXTERNAL_SIGNAL_SHADOW_MIN_ORDERBOOK_COVERAGE == 0.95
    assert base.EXTERNAL_SIGNAL_SHADOW_MIN_PRICE_COVERAGE == 0.99
    assert base.EXTERNAL_SIGNAL_SHADOW_CUSUM_FIXED_THRESHOLD_BPS == 30.0
    assert base.EXTERNAL_SIGNAL_SHADOW_CUSUM_VOL_MULTIPLIER == 1.5
    assert base.EXTERNAL_SIGNAL_SHADOW_CUSUM_CONFIRMATION_WINDOW_MIN == 30
    assert base.EXTERNAL_SIGNAL_SHADOW_TAKE_PROFIT_BPS == 150.0
    assert base.EXTERNAL_SIGNAL_SHADOW_STOP_LOSS_BPS == 100.0
    assert base.EXTERNAL_SIGNAL_SHADOW_MAX_HOLDING_MINUTES == 240
    assert base.EXTERNAL_SIGNAL_SHADOW_ENTRY_DELAY_BARS == 1
    assert base.EXTERNAL_SIGNAL_SHADOW_COST_ROUND_TRIP_BPS == 50.0
```

**Step 2: Run failing test**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_models.py::test_external_signal_shadow_stage0_config_constants_exist -q
```

Expected: fail because constants do not exist.

**Step 3: Implement constants**

Append a new section to `configs/base.py`:

```python
# ─── Research: External Signal Shadow Lab Stage 0 ─────────────────────────────

EXTERNAL_SIGNAL_SHADOW_MIN_LIQUIDITY_USD = 500_000.0
# Minimum token liquidity for accepting an external event into shadow replay.

EXTERNAL_SIGNAL_SHADOW_MAX_SELL_TAX_PCT = 5.0
# Maximum allowed sell tax for token events; higher values are rejected.

EXTERNAL_SIGNAL_SHADOW_MAX_TOP10_HOLDER_SHARE = 0.35
# Maximum top-10 holder concentration. 0.35 = 35%.

EXTERNAL_SIGNAL_SHADOW_MAX_SMART_MONEY_EXIT_RATE = 0.70
# Maximum allowed smart-money exit rate. 0.70 = 70%.

EXTERNAL_SIGNAL_SHADOW_CEX_MAX_SPREAD_BPS = 10.0
# CEX event rejection threshold for current spread.

EXTERNAL_SIGNAL_SHADOW_CEX_MIN_DEPTH_10BPS_USD = 100_000.0
# Minimum CEX depth within 10 bps needed for shadow eligibility.

EXTERNAL_SIGNAL_SHADOW_MIN_ORDERBOOK_COVERAGE = 0.95
# Minimum recent orderbook coverage required for CEX events.

EXTERNAL_SIGNAL_SHADOW_MIN_PRICE_COVERAGE = 0.99
# Minimum price bar coverage required for any shadow replay.

EXTERNAL_SIGNAL_SHADOW_CUSUM_FIXED_THRESHOLD_BPS = 30.0
# Fixed lower bound for CUSUM confirmation threshold.

EXTERNAL_SIGNAL_SHADOW_CUSUM_VOL_MULTIPLIER = 1.5
# Rolling-volatility multiplier used by CUSUM threshold.

EXTERNAL_SIGNAL_SHADOW_CUSUM_CONFIRMATION_WINDOW_MIN = 30
# Maximum minutes after event time to wait for CUSUM confirmation.

EXTERNAL_SIGNAL_SHADOW_TAKE_PROFIT_BPS = 150.0
# Default triple-barrier take-profit distance.

EXTERNAL_SIGNAL_SHADOW_STOP_LOSS_BPS = 100.0
# Default triple-barrier stop-loss distance.

EXTERNAL_SIGNAL_SHADOW_MAX_HOLDING_MINUTES = 240
# Default vertical barrier horizon.

EXTERNAL_SIGNAL_SHADOW_ENTRY_DELAY_BARS = 1
# Number of complete bars after trigger before shadow entry.

EXTERNAL_SIGNAL_SHADOW_COST_ROUND_TRIP_BPS = 50.0
# Default round-trip cost used for shadow net return.
```

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_models.py::test_external_signal_shadow_stage0_config_constants_exist -q
```

Expected: pass.

---

## 3. Models and Validation

### Task 2: Create Event, PriceBar, RiskDecision, CUSUM, and ShadowOrder Models

**Files:**

- Create: `src/research/external_signal_shadow/__init__.py`
- Create: `src/research/external_signal_shadow/models.py`
- Test: `tests/research/test_external_signal_shadow_models.py`

**Step 1: Write model tests**

Add tests for:

```python
def test_external_signal_event_normalizes_symbol_and_requires_shadow_only(): ...
def test_external_signal_event_rejects_executable_payload_fields(): ...
def test_external_signal_event_rejects_forbidden_keys_nested_in_metadata(): ...
def test_external_signal_event_rejects_forbidden_keys_inside_list(): ...
def test_price_bar_rejects_non_positive_prices(): ...
def test_price_bar_requires_high_gte_low(): ...
def test_price_bar_requires_end_after_start(): ...
def test_parse_jsonl_events_and_bars_round_trip(): ...
```

Important expected behavior:

- `BTC/USDT` normalizes to `BTCUSDT`.
- `shadow_only` must be `True`; otherwise raise `ValueError`.
- Any forbidden executable keys must raise `ValueError`, even when nested inside `metadata`, `raw_payload`, lists, or nested dicts.
- Forbidden keys include `api_key`, `private_key`, `order_id`, `signed_tx`, `wallet_seed`, `swap_payload`, `mnemonic`, `seed_phrase`, `wallet_private_key`, and `tx_payload`.
- Implement recursive validation with `reject_forbidden_keys_recursive(payload: object) -> None`.
- `PriceBar` requires `open_price`, `high_price`, `low_price`, `close_price` all positive.
- `high_price >= low_price`.
- `bar_start_ms` and `bar_end_ms` are integer Unix ms timestamps.
- `bar_end_ms > bar_start_ms`.
- Stage 0 assumes complete OHLC bars. A bar that contains the trigger/event time must never be used as an entry or barrier evaluation bar.

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_models.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement `models.py`**

Use `@dataclass(frozen=True)`.

Required classes:

```python
ExternalSignalEvent
PriceBar
RiskDecision
CusumResult
ShadowOrder
ReplayBranchSummary
```

Required helper functions:

```python
reject_forbidden_keys_recursive(payload: object) -> None
normalize_symbol(symbol: str | None) -> str | None
load_events_jsonl(path: str) -> list[ExternalSignalEvent]
load_price_bars_jsonl(path: str) -> list[PriceBar]
price_bars_by_symbol(bars: list[PriceBar]) -> dict[str, list[PriceBar]]
```

Do not use pydantic. Keep dependencies minimal.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_models.py -q
```

Expected: pass.

---

## 4. Risk Guard

### Task 3: Implement Fixture-Only Risk Guard

**Files:**

- Create: `src/research/external_signal_shadow/risk_guard.py`
- Test: `tests/research/test_external_signal_shadow_risk_guard.py`

**Step 1: Write tests**

Required tests:

```python
def test_risk_guard_rejects_honeypot(): ...
def test_risk_guard_rejects_low_liquidity(): ...
def test_risk_guard_rejects_high_sell_tax(): ...
def test_risk_guard_rejects_high_holder_concentration(): ...
def test_risk_guard_rejects_high_smart_money_exit_rate(): ...
def test_risk_guard_rejects_degraded_data_quality(): ...
def test_risk_guard_rejects_cex_wide_spread(): ...
def test_risk_guard_rejects_cex_low_depth(): ...
def test_risk_guard_accepts_clean_long_event(): ...
def test_risk_guard_unknown_direction_becomes_observe_only(): ...
def test_risk_guard_cex_event_does_not_require_token_tax_fields(): ...
def test_risk_guard_token_event_does_not_require_cex_depth_fields(): ...
def test_risk_guard_rejects_unknown_chain_or_missing_market_context(): ...
```

Events may carry metrics through a `metadata: dict[str, object]` field.

Example metadata:

```python
{
    "honeypot_risk": True,
    "sell_tax_pct": 8.0,
    "top10_holder_share": 0.42,
    "smart_money_exit_rate": 0.8,
    "spread_bps": 12.0,
    "depth_10bps_usd": 50_000.0,
    "orderbook_coverage": 0.9,
    "price_coverage": 1.0,
}
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_risk_guard.py -q
```

**Step 3: Implement risk guard**

Create:

```python
def evaluate_event_risk(event: ExternalSignalEvent) -> RiskDecision:
    ...
```

Risk decision values:

```text
accept_for_shadow
reject
quarantine
```

Allowed shadow directions:

```text
long
short
both
observe_only
none
```

Rules:

- hard veto -> `reject`;
- unknown direction but otherwise clean -> `accept_for_shadow` + `observe_only`;
- data quality not `ok` -> `quarantine` unless hard veto is present;
- `chain == "cex"`: apply CEX spread/depth/orderbook/price-coverage rules, and do not require token tax/audit fields;
- `chain != "cex"`: apply token/on-chain liquidity/tax/holder/smart-money-exit rules, and do not require CEX depth/spread fields;
- missing chain or unsupported market context -> `reject` with an explicit reason;
- missing required CEX coverage for CEX events -> `reject`;
- missing required token liquidity for on-chain token events -> `reject`.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_risk_guard.py -q
```

---

## 5. CUSUM Confirmation

### Task 4: Implement CUSUM Confirmation Gate

**Files:**

- Create: `src/research/external_signal_shadow/cusum.py`
- Test: `tests/research/test_external_signal_shadow_cusum.py`

**Step 1: Write tests**

Required tests:

```python
def test_cusum_confirms_positive_move_after_event(): ...
def test_cusum_confirms_negative_move_after_event(): ...
def test_cusum_returns_no_confirm_when_threshold_not_crossed(): ...
def test_cusum_respects_confirmation_window(): ...
def test_cusum_long_hint_rejects_negative_confirmation_as_adverse(): ...
def test_cusum_short_hint_rejects_positive_confirmation_as_adverse(): ...
def test_cusum_unknown_direction_returns_observe_only_no_order(): ...
def test_cusum_uses_max_of_fixed_threshold_and_vol_threshold(): ...
def test_cusum_uses_pre_event_close_only_as_return_baseline(): ...
def test_cusum_does_not_trigger_on_pre_event_move(): ...
def test_cusum_first_post_event_return_is_computed_correctly(): ...
def test_cusum_threshold_units_are_log_return_not_bps(): ...
def test_cusum_reports_threshold_source_fixed_or_vol(): ...
def test_cusum_falls_back_to_fixed_threshold_when_pre_event_bars_insufficient(): ...
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_cusum.py -q
```

**Step 3: Implement `confirm_event_with_cusum`**

Signature:

```python
def confirm_event_with_cusum(
    event: ExternalSignalEvent,
    bars: list[PriceBar],
    *,
    fixed_threshold_bps: float,
    vol_multiplier: float,
    confirmation_window_min: int,
) -> CusumResult:
    ...
```

Behavior:

- Use bars for event symbol only.
- Internal threshold units are log-return units, not raw bps.
- `fixed_threshold_log_return = fixed_threshold_bps / 10_000.0`.
- `rolling_vol_log_return = std(pre_event_log_returns)` from up to the preceding 60 completed bars.
- If fewer than 2 pre-event returns are available, fall back to the fixed threshold and report `threshold_source = "fixed"`.
- `threshold_log_return = max(fixed_threshold_log_return, vol_multiplier * rolling_vol_log_return)`.
- Find the last completed bar whose `bar_end_ms <= event.event_time_ms`; use only its close as the first `prev_close` baseline.
- CUSUM confirmation can only occur on bars where `bar_start_ms > event.event_time_ms`.
- The pre-event close is only a return baseline; it can never be the trigger bar.
- Compute the first post-event return as `log(first_post_event_close / pre_event_close)`.
- Return `threshold_bps`, `rolling_vol_bps`, and `threshold_source` in `CusumResult` metadata.
- Return statuses:
  - `confirmed`;
  - `no_confirm`;
  - `adverse_confirm`;
  - `observe_only`;
  - `data_unavailable`.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_cusum.py -q
```

Important: CUSUM must not create shadow orders directly. It only returns confirmation metadata.

---

## 6. Triple Barrier Shadow Orders

### Task 5: Implement Triple Barrier Labeling

**Files:**

- Create: `src/research/external_signal_shadow/triple_barrier.py`
- Test: `tests/research/test_external_signal_shadow_triple_barrier.py`

**Step 1: Write tests**

Required tests:

```python
def test_triple_barrier_long_take_profit_first(): ...
def test_triple_barrier_long_stop_loss_first(): ...
def test_triple_barrier_short_take_profit_first(): ...
def test_triple_barrier_short_stop_loss_first(): ...
def test_triple_barrier_vertical_timeout(): ...
def test_triple_barrier_entry_uses_next_complete_bar_after_trigger(): ...
def test_triple_barrier_applies_round_trip_cost_to_net_return(): ...
def test_triple_barrier_reports_mae_and_mfe(): ...
def test_triple_barrier_returns_data_unavailable_without_entry_bar(): ...
def test_triple_barrier_does_not_use_pre_entry_high_low(): ...
def test_entry_does_not_use_bar_that_contains_trigger_time(): ...
def test_triple_barrier_does_not_use_trigger_bar_high_low(): ...
def test_triple_barrier_same_bar_tp_and_sl_uses_conservative_stop_loss(): ...
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_triple_barrier.py -q
```

**Step 3: Implement `build_shadow_order_with_triple_barrier`**

Signature:

```python
def build_shadow_order_with_triple_barrier(
    event: ExternalSignalEvent,
    trigger_time_ms: int,
    bars: list[PriceBar],
    *,
    direction: str,
    take_profit_bps: float,
    stop_loss_bps: float,
    max_holding_minutes: int,
    entry_delay_bars: int,
    cost_round_trip_bps: float,
) -> ShadowOrder:
    ...
```

Rules:

- Candidate entry/evaluation bars must satisfy `bar_start_ms > trigger_time_ms`.
- A bar with `bar_start_ms <= trigger_time_ms < bar_end_ms` contains the trigger and must not be used for entry, TP, SL, MAE, or MFE.
- Entry is the open price of the `entry_delay_bars`-th candidate bar after `trigger_time_ms`.
- Long take profit: `entry_price * (1 + take_profit_bps / 10000)`.
- Long stop loss: `entry_price * (1 - stop_loss_bps / 10000)`.
- Short take profit: `entry_price * (1 - take_profit_bps / 10000)`.
- Short stop loss: `entry_price * (1 + stop_loss_bps / 10000)`.
- If TP and SL are both touched in the same bar, use conservative ordering: stop loss wins.
- This conservative same-bar ordering must be covered by both unit tests and fixtures.
- Net return = gross return - cost for winning/losing/timeout exits.
- MAE/MFE computed only from bars after entry, not pre-entry bars.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_triple_barrier.py -q
```

---

## 7. Replay Orchestrator

### Task 6: Implement Stage 0 Replay Pipeline

**Files:**

- Create: `src/research/external_signal_shadow/replay.py`
- Test: `tests/research/test_external_signal_shadow_replay.py`

**Step 1: Write tests**

Required tests:

```python
def test_replay_outputs_no_cusum_and_cusum_branches(): ...
def test_replay_rejected_events_do_not_create_shadow_orders(): ...
def test_replay_observe_only_events_do_not_create_directional_orders(): ...
def test_replay_no_cusum_branch_enters_after_event_time(): ...
def test_replay_cusum_branch_enters_after_cusum_trigger(): ...
def test_replay_records_cusum_no_confirm_count(): ...
def test_replay_records_win_loss_timeout_counts(): ...
def test_replay_summary_is_deterministic_for_fixture_inputs(): ...
def test_summary_labels_no_cusum_branch_as_baseline_control(): ...
def test_summary_labels_cusum_branch_as_confirmation_filtered_shadow(): ...
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_replay.py -q
```

**Step 3: Implement `run_stage0_shadow_replay`**

Signature:

```python
def run_stage0_shadow_replay(
    events: list[ExternalSignalEvent],
    bars: list[PriceBar],
) -> dict:
    ...
```

Required branches:

```text
no_cusum_all_accepted_events
cusum_confirmed_events
```

Branch behavior:

- `no_cusum_all_accepted_events`: accepted long/short events generate shadow orders using event time as trigger time.
- `cusum_confirmed_events`: accepted events generate shadow orders only if CUSUM confirms in allowed direction.
- unknown/observe-only events are counted but do not create orders.

Output summary must include:

```json
{
  "mode": "fixture_only_stage0",
  "live_trading_enabled": false,
  "external_api_enabled": false,
  "wallet_required": false,
  "events_total": 0,
  "events_accepted": 0,
  "events_rejected": 0,
  "events_quarantined": 0,
  "branches": {
    "no_cusum_all_accepted_events": {},
    "cusum_confirmed_events": {}
  },
  "branch_semantics": {
    "no_cusum_all_accepted_events": "baseline_control_not_strategy",
    "cusum_confirmed_events": "confirmation_filtered_shadow_not_strategy"
  },
  "parameter_policy": "fixed_stage0_sanity_check_not_optimized",
  "alpha_interpretation_allowed": false,
  "decision": "external_signal_shadow_stage0_passed|external_signal_shadow_stage0_failed",
  "primary_blocker": null
}
```

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_replay.py -q
```

---

## 8. Summary Decision

### Task 7: Implement Decision and Failure Taxonomy

**Files:**

- Create: `src/research/external_signal_shadow/summary.py`
- Test: `tests/research/test_external_signal_shadow_summary.py`

**Step 1: Write tests**

Required tests:

```python
def test_stage0_summary_passes_when_pipeline_runs_and_orders_exist(): ...
def test_stage0_summary_fails_when_no_accepted_events(): ...
def test_stage0_summary_fails_when_no_price_bars(): ...
def test_stage0_summary_classifies_data_failure(): ...
def test_stage0_summary_classifies_structure_failure_when_no_shadow_orders(): ...
def test_stage0_summary_never_marks_live_safe(): ...
def test_stage0_summary_reports_cusum_vs_no_cusum_comparison(): ...
def test_stage0_summary_passes_even_when_net_return_negative_if_pipeline_valid(): ...
def test_stage0_summary_does_not_use_pnl_as_alpha_decision(): ...
def test_stage0_summary_requires_branch_semantics(): ...
def test_stage0_summary_requires_parameter_policy_and_no_alpha_interpretation(): ...
```

Failure taxonomy:

```text
data_failure
risk_guard_density_failure
cusum_confirmation_failure
shadow_order_structure_failure
stage0_completed
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_summary.py -q
```

**Step 3: Implement summary helpers**

Functions:

```python
def decide_stage0_shadow_replay(summary: dict) -> dict:
    ...

def summarize_branch_orders(orders: list[ShadowOrder]) -> dict:
    ...
```

Stage 0 can pass even if strategy results are negative, as long as the pipeline works. It is an infrastructure readiness decision, not an alpha decision.

Pipeline pass requirements:

- `events_total > 0`;
- `price_bars_total > 0`;
- Risk Guard produced accepted/rejected/quarantined counts;
- no-CUSUM branch exists;
- CUSUM-confirmed branch exists;
- at least one branch generated at least one shadow order;
- fixture run produced TP, SL, and timeout examples across branches;
- `live_trading_enabled = false`;
- `external_api_enabled = false`;
- `wallet_required = false`;
- `alpha_interpretation_allowed = false`.

Do not use net PnL, win rate, or positive return as Stage 0 pass gates. Those are diagnostic metrics only.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_summary.py -q
```

---

## 9. Fixtures

### Task 8: Add Deterministic Fixture Events and Price Bars

**Files:**

- Create: `tests/fixtures/external_signal_shadow/stage0_events.jsonl`
- Create: `tests/fixtures/external_signal_shadow/stage0_price_bars.jsonl`
- Test: `tests/research/test_external_signal_shadow_replay.py`

**Fixture requirements:**

Events must include:

1. Clean long CEX event that hits TP.
2. Clean long CEX event that hits SL.
3. Clean short CEX event that times out.
4. Honeypot token event that Risk Guard rejects.
5. Low-liquidity token event that Risk Guard rejects.
6. Unknown-direction event that becomes observe-only.
7. Event that does not CUSUM-confirm.
8. Event that CUSUM-confirms in adverse direction.
9. Clean long CEX event where the same evaluation bar touches both TP and SL; expected exit reason is stop_loss.

Price bars must include enough minute bars for each accepted symbol to test:

- entry delay;
- TP first;
- SL first;
- vertical timeout;
- CUSUM confirmation;
- no confirmation;
- trigger-time bar exclusion;
- same-bar TP/SL conservative stop-loss ordering.

Keep fixture small and human-readable. Do not include real wallet addresses.

Add fixture validation test:

```python
def test_fixture_contains_same_bar_tp_sl_conservative_case(): ...
```

**Verification:**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_replay.py -q
```

---

## 10. CLI Script

### Task 9: Add Stage 0 Runner CLI

**Files:**

- Create: `scripts/run_external_signal_shadow_stage0.py`
- Test: `tests/scripts/test_run_external_signal_shadow_stage0.py`

**Step 1: Write tests**

Required tests:

```python
def test_run_external_signal_shadow_stage0_writes_summary(tmp_path): ...
def test_run_external_signal_shadow_stage0_empty_events_writes_data_failure(tmp_path): ...
def test_run_external_signal_shadow_stage0_rejects_external_api_flag(): ...
def test_run_external_signal_shadow_stage0_output_has_live_trading_false(): ...
```

**Step 2: Implement CLI**

CLI args:

```text
--events tests/fixtures/external_signal_shadow/stage0_events.jsonl
--price-bars tests/fixtures/external_signal_shadow/stage0_price_bars.jsonl
--output reports/external_signal_shadow/stage0_shadow_replay_summary.json
```

No external API flags are allowed in Stage 0.

`main(argv: list[str] | None = None) -> int` should return:

- `0` if summary is written;
- `1` only for malformed input path / unreadable input / invalid JSONL.

A data-unavailable research result is not a Python process failure if it writes a summary.

**Step 3: Verify**

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_external_signal_shadow_stage0.py -q
```

Manual run:

```bash
PYTHONPATH=src uv run python scripts/run_external_signal_shadow_stage0.py \
  --events tests/fixtures/external_signal_shadow/stage0_events.jsonl \
  --price-bars tests/fixtures/external_signal_shadow/stage0_price_bars.jsonl \
  --output reports/external_signal_shadow/stage0_shadow_replay_summary.json
```

Expected output file exists and contains `"live_trading_enabled": false`.

---

## 11. Review Generator

### Task 10: Add Chinese Review Generator

**Files:**

- Create: `scripts/review_external_signal_shadow_stage0.py`
- Test: `tests/scripts/test_review_external_signal_shadow_stage0.py`
- Output: `docs/reviews/2026-06-12-external-signal-shadow-lab-stage0-review_CN.md`

**Step 1: Write tests**

Required tests:

```python
def test_review_external_signal_shadow_stage0_writes_markdown(tmp_path): ...
def test_review_mentions_no_live_trading_and_no_external_api(tmp_path): ...
def test_review_explains_cusum_is_confirmation_not_alpha(tmp_path): ...
def test_review_explains_triple_barrier_is_shadow_evaluation(tmp_path): ...
def test_review_includes_failure_taxonomy(tmp_path): ...
```

**Step 2: Implement review script**

CLI args:

```text
--summary reports/external_signal_shadow/stage0_shadow_replay_summary.json
--output docs/reviews/2026-06-12-external-signal-shadow-lab-stage0-review_CN.md
```

Review must include sections:

```text
1. 结论
2. Stage 0 范围
3. 数据与事件覆盖
4. Risk Guard 结果
5. CUSUM 对照结果
6. 三重屏障 shadow order 结果
7. 分支语义与参数边界
7. 失效类型与归因
8. 不能推出的结论
9. 下一步建议
```

Must explicitly state:

```text
本轮不是 alpha 通过；不是 paper/live 准入；不允许下单；不允许接钱包。
no-CUSUM branch 是 baseline control，不是策略。
CUSUM branch 是 confirmation-filtered shadow，不是策略。
固定 TP/SL/holding 参数只用于 Stage 0 基础设施 sanity check，不可迁移为真实策略参数。
Stage 1 才允许在预注册参数组下比较事件类型，但不得事后优化。
```

**Step 3: Verify**

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_review_external_signal_shadow_stage0.py -q
```

Manual run:

```bash
PYTHONPATH=src uv run python scripts/review_external_signal_shadow_stage0.py \
  --summary reports/external_signal_shadow/stage0_shadow_replay_summary.json \
  --output docs/reviews/2026-06-12-external-signal-shadow-lab-stage0-review_CN.md
```

---

## 12. Full Verification

### Task 11: Run Focused and Full Checks

Run focused checks:

```bash
PYTHONPATH=src uv run pytest \
  tests/research/test_external_signal_shadow_models.py \
  tests/research/test_external_signal_shadow_risk_guard.py \
  tests/research/test_external_signal_shadow_cusum.py \
  tests/research/test_external_signal_shadow_triple_barrier.py \
  tests/research/test_external_signal_shadow_replay.py \
  tests/research/test_external_signal_shadow_summary.py \
  tests/scripts/test_run_external_signal_shadow_stage0.py \
  tests/scripts/test_review_external_signal_shadow_stage0.py -q
```

Run lint:

```bash
uv run ruff check src/research/external_signal_shadow scripts/run_external_signal_shadow_stage0.py scripts/review_external_signal_shadow_stage0.py tests/research/test_external_signal_shadow_*.py tests/scripts/test_run_external_signal_shadow_stage0.py tests/scripts/test_review_external_signal_shadow_stage0.py
```

Run full suite before declaring completion:

```bash
PYTHONPATH=src uv run pytest -q
```

Expected:

```text
all tests pass
ruff check pass
```

If full suite fails outside External Signal Shadow Lab, document the failure and do not claim full completion.

---

## 13. Completion Criteria

Stage 0 implementation is complete only if all are true:

- config constants exist in `configs/base.py`;
- fixture-only replay can run end-to-end;
- no-CUSUM and CUSUM-confirmed branches both appear in summary;
- Risk Guard rejects fixture bad events;
- triple barrier produces TP / SL / timeout examples;
- triple barrier fixture covers same-bar TP/SL conservative stop-loss ordering;
- generated summary has `live_trading_enabled = false`;
- generated summary has `external_api_enabled = false`;
- Chinese review is generated;
- focused tests pass;
- ruff passes;
- full pytest passes or unrelated failures are explicitly documented.

---

## 14. Handoff Notes for Future Stage 1

Do not implement these in Stage 0.

Stage 1 may add one connector at a time:

```text
Binance token audit connector
OKX token hot list connector
OKX smart money signal connector
Gate marketanalysis-derived internal event connector
```

Each connector must have its own design and implementation plan.

Stage 1 must still be read-only and shadow-only.

Forward shadow replay must run for at least 30 days before any external event type can be considered a strategy candidate.
