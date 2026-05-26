# Extreme Funding Candidate Admission Definition Revision Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构 Extreme Funding 的入选定义，把“极端 funding 事件观察”、“研究影子案例”和“未来可交易候选”拆成三层，避免继续用过硬或过乐观的单一门槛误判策略有效性。

**Architecture:** 不接 execution，不改变 live trading 开关。先在 strategy/research 层定义新的 admission taxonomy，再让 historical basis-aware replay 和 parameter sensitivity audit 使用同一套定义输出 anchor event、research shadow case 与 trade candidate 三类结果。Layer A/B 不生成 `SignalCandidate`，只有 Layer C 才允许调用 `build_extreme_funding_candidate(...)`。

**Tech Stack:** Python 3.11, pytest, dataclasses, `configs/base.py` as SSOT, existing `candidate_builder`, existing `extreme_funding_basis_replay`, JSON summary under `reports/extreme_funding`。

---

## 1. 背景与当前问题

当前 `build_extreme_funding_candidate(...)` 是单层硬门：

- `annualized_funding_estimate_pct >= 100`
- `expected_funding_income_bps >= 50`
- `basis_absorption_ratio <= 0.50`
- `net_edge_bps >= 30`
- `slippage_bps <= 10`
- depth proxy 足够

这套逻辑的问题不是“保守”，而是把三类不同问题混成了一类：

- `anchor event`：市场是否出现极端 funding 事件。
- `research shadow case`：是否值得进入历史/影子模拟。
- `trade candidate`：是否接近未来真实交易候选。

上轮审计已经证明：

- DOGE/XRP 的 `conservative_1_interval` 下候选为 0。
- 候选只在 `optimistic_2_intervals` + 放宽参数下出现。
- 主拒绝原因是 `annualized_funding_below_trade_threshold` 与 `expected_funding_income_below_min`。

关键解释：

- `min_expected_funding_income_bps=50` 对单期 funding 来说很高。
- 1 个 8h funding interval 要达到 50 bps，单期 funding rate 约为 `0.50%/8h`，年化约 `547.5%`。
- 当前 DOGE/XRP basis-aware rows 的单期 funding bps 中位数约 10-11 bps，最大约 32-38 bps。
- 因此当前单层硬门天然会把大多数历史极端事件挡掉。

---

## 2. 新策略定义

本轮建议把 Extreme Funding 拆成三层。

### Layer A: Anchor Event

含义：市场确实出现值得研究的 funding 异常。

用途：

- 进入 replay 数据集。
- 不生成 `SignalCandidate`。
- 不进入 execution。

初始条件：

- `annualized_pct >= 100`
- `funding_rate_per_interval > 0`
- `source_type == historical_settled` 或 watchlist level 达到强预警

### Layer B: Research Shadow Case

含义：值得进入 shadow 模拟的研究案例，但还不是可交易候选。

用途：

- 用于 parameter sensitivity / basis-aware replay。
- 输出 `research_case_summary`。
- 不允许 live。
- 不生成 `SignalCandidate`。

初始条件建议：

- anchor event 成立。
- 单期 gross funding income `>= 15 bps`。
- `basis_absorption_ratio <= 0.70`。
- `net_edge_bps` 可以小于 30，但必须记录为 `research_only_net_edge_below_trade_gate`。
- 必须有 basis snapshot。
- shadow 层还必须单独确认 `basis_path_available=true`，至少存在 entry row 之后 1 条同 symbol path row。

### Layer C: Trade Candidate Gate

含义：未来 orderbook-aware replay 之后，才可能接近可交易候选。

用途：

- 仍不直接 live。
- 仅作为进入 pre-live checklist 的前置证据。

条件保持更严格：

- `net_edge_bps >= 30`
- `basis_absorption_ratio <= 0.50`
- real orderbook slippage `<= 10 bps`
- depth capacity `>= planned_notional * 2`
- `expected_holding_intervals=1` 下仍有候选
- `expected_holding_intervals=2` 永远不能直接成为 Layer C。

---

## 3. expected_holding_intervals=2 的使用规则

`expected_holding_intervals=2` 允许存在，但只能作为 optimistic shadow assumption。

硬规则：

- 不得用于 Layer C trade candidate admission。
- 不得作为进入 orderbook-aware replay 的唯一依据。
- 如果 `interval=1` 无候选、`interval=2` 有候选，结论必须写成：
  `strategy_depends_on_funding_persistence`。
- 只有在额外证明 settlement persistence 后，`interval=2` 才能被纳入下一轮策略定义。

---

## 4. 决策门

本轮 review 只能输出三类结论：

- `watchlist_only`
- `funding_persistence_study_required`
- `enter_orderbook_aware_replay`

进入 `orderbook-aware replay` 的最低条件：

- Layer C `trade_candidate_count > 0` under `expected_holding_intervals=1`。
- 或者 Layer B `research_shadow_admitted_count > 0` under `expected_holding_intervals=1`，且：
  - `median_shadow_net_pnl_bps > 20`
  - `win_rate > 55%`
  - 主要 blocker 不是 `annualized_funding_below_trade_threshold` / `expected_funding_income_below_min`
  - `basis_absorbed` 不是主导拒绝原因
  - review 明确 `depth_aware=false`，只允许进入 orderbook-aware replay，不允许 live

如果只有 `expected_holding_intervals=2` 下 Layer B 才有样本：

- 不进入 `orderbook-aware replay`
- 输出 `funding_persistence_study_required`

---

## Task 1: Add Admission Definition Config

**Files:**
- Modify: `configs/base.py`
- Test: `tests/test_extreme_funding_config.py`

**Step 1: Write failing test**

Add:

```python
def test_extreme_funding_admission_definition_config_defined():
    assert base.EXTREME_FUNDING_ANCHOR_ANNUALIZED_THRESHOLD_PCT == 100.0
    assert base.EXTREME_FUNDING_RESEARCH_MIN_GROSS_FUNDING_BPS == 15.0
    assert base.EXTREME_FUNDING_RESEARCH_BASIS_ABSORPTION_MAX_RATIO == 0.70
    assert base.EXTREME_FUNDING_TRADE_EXPECTED_HOLDING_INTERVALS == 1
```

**Step 2: Verify failing test**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py::test_extreme_funding_admission_definition_config_defined -q
```

Expected: FAIL with missing config attributes.

**Step 3: Add config constants**

Add constants to `configs/base.py` with explicit comments:

```python
EXTREME_FUNDING_ANCHOR_ANNUALIZED_THRESHOLD_PCT = 100.0
# Minimum annualized funding rate (%) to qualify as an anchor event (Layer A).
# 100% annualized is still an observation/research threshold, not a live trigger.

EXTREME_FUNDING_RESEARCH_MIN_GROSS_FUNDING_BPS = 15.0
# Minimum single-interval gross funding income in bps for Layer B research shadow cases.
# This is deliberately lower than the trade gate so historical tail events are not hidden.

EXTREME_FUNDING_RESEARCH_BASIS_ABSORPTION_MAX_RATIO = 0.70
# Maximum basis absorption ratio for Layer B research cases.
# Layer C keeps the stricter 0.50 trade gate.

EXTREME_FUNDING_TRADE_EXPECTED_HOLDING_INTERVALS = 1
# Layer C trade candidate admission must be valid under one funding interval.
```

**Step 4: Verify**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add configs/base.py tests/test_extreme_funding_config.py
git commit -m "test+feat: add extreme funding admission definition config"
```

---

## Task 2: Add Admission Layer Classifier

**Files:**
- Create: `src/strategies/extreme_funding/admission.py`
- Test: `tests/strategies/test_extreme_funding_admission.py`

**Step 1: Write failing tests**

Add tests:

```python
def test_classifies_anchor_event_without_trade_candidate():
    ...

def test_research_shadow_admission_allows_lower_gross_funding_than_trade_gate():
    ...

def test_trade_candidate_requires_one_interval_and_net_edge_gate():
    ...

def test_two_interval_assumption_is_marked_optimistic_only():
    ...

def test_research_shadow_admission_does_not_emit_signal_candidate():
    ...

def test_trade_candidate_requires_conservative_one_interval():
    ...

def test_research_admitted_records_trade_blocker():
    ...

def test_missing_funding_or_basis_is_classified_safely():
    ...
```

**Step 2: Verify failing tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_admission.py -q
```

Expected: FAIL because module does not exist.

**Step 3: Implement minimal classifier**

Create:

```python
@dataclass(frozen=True)
class ExtremeFundingAdmissionResult:
    anchor_event: bool
    research_shadow_admitted: bool
    trade_candidate_admitted: bool
    admission_layer: str
    reject_reason: str | None
    metrics: dict[str, Any]
```

Implement:

```python
classify_extreme_funding_admission(row: dict[str, Any]) -> ExtremeFundingAdmissionResult
```

Layer names:

- `no_anchor`
- `anchor_only`
- `research_shadow`
- `trade_candidate`

Required metrics:

- `gross_funding_bps`
- `basis_absorption_ratio`
- `net_edge_bps`
- `assumption_level`
- `basis_snapshot_available`
- `basis_path_available`
- `basis_path_intervals`
- `trade_blockers`

Required safety rules:

- Missing `funding_rate_per_interval` returns `missing_funding_rate`.
- Missing `basis_bps` returns `missing_basis`.
- Layer B does not create `SignalCandidate`.
- Layer C requires `expected_holding_intervals == EXTREME_FUNDING_TRADE_EXPECTED_HOLDING_INTERVALS`.
- If Layer B passes but Layer C fails, record bridge reasons in `trade_blockers`.

**Step 4: Verify**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_admission.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/strategies/extreme_funding/admission.py tests/strategies/test_extreme_funding_admission.py
git commit -m "test+feat: add layered extreme funding admission classifier"
```

---

## Task 3: Add Anchor-Only And Research Case Replay Summary

**Files:**
- Modify: `src/research/extreme_funding_parameter_sensitivity.py`
- Modify: `scripts/audit_extreme_funding_parameter_sensitivity.py`
- Test: `tests/research/test_extreme_funding_parameter_sensitivity.py`
- Test: `tests/scripts/test_audit_extreme_funding_parameter_sensitivity.py`

**Step 1: Write failing tests**

Add tests:

```python
def test_anchor_only_summary_counts_anchor_rows_separately_from_path_rows():
    ...

def test_research_shadow_count_can_exceed_trade_candidate_count():
    ...

def test_audit_output_contains_admission_layer_counts():
    ...

def test_research_to_trade_blocker_counts_are_reported():
    ...

def test_strategy_depends_on_funding_persistence_is_detected_automatically():
    ...
```

**Step 2: Verify failing tests**

Run:

```bash
PYTHONPATH=src uv run pytest \
  tests/research/test_extreme_funding_parameter_sensitivity.py \
  tests/scripts/test_audit_extreme_funding_parameter_sensitivity.py \
  -q
```

Expected: FAIL.

**Step 3: Implement summary fields**

Add to sensitivity outputs:

- `anchor_event_count`
- `research_shadow_admitted_count`
- `trade_candidate_count`
- `admission_layer_counts`
- `research_to_trade_blocker_counts`
- `strategy_depends_on_funding_persistence`
- `any_trade_candidate`
- `conservative_has_trade_candidate`

**Step 4: Verify**

Run:

```bash
PYTHONPATH=src uv run pytest \
  tests/research/test_extreme_funding_parameter_sensitivity.py \
  tests/scripts/test_audit_extreme_funding_parameter_sensitivity.py \
  -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/extreme_funding_parameter_sensitivity.py \
        scripts/audit_extreme_funding_parameter_sensitivity.py \
        tests/research/test_extreme_funding_parameter_sensitivity.py \
        tests/scripts/test_audit_extreme_funding_parameter_sensitivity.py
git commit -m "test+feat: add anchor-only admission summary for extreme funding"
```

---

## Task 4: Rerun Sensitivity Audit With New Definition

**Files:**
- Generate: `reports/extreme_funding/2026-05-26_doge_admission_definition_candidate_summary.json`
- Generate: `reports/extreme_funding/2026-05-26_xrp_admission_definition_candidate_summary.json`
- Create: `docs/reviews/2026-05-26-extreme-funding-admission-definition-revision-review.md`

**Step 1: Run DOGE**

```bash
PYTHONPATH=src uv run python scripts/audit_extreme_funding_parameter_sensitivity.py \
  --input reports/extreme_funding/2026-05-25_basis_rows_DOGEUSDT.jsonl \
  --output-dir reports/extreme_funding \
  --tag 2026-05-26_doge_admission_definition
```

**Step 2: Run XRP**

```bash
PYTHONPATH=src uv run python scripts/audit_extreme_funding_parameter_sensitivity.py \
  --input reports/extreme_funding/2026-05-25_basis_rows_XRPUSDT.jsonl \
  --output-dir reports/extreme_funding \
  --tag 2026-05-26_xrp_admission_definition
```

**Step 3: Write review**

Review must answer:

- How many anchor events exist?
- How many research-shadow admissions exist?
- Does trade candidate remain zero?
- Is `expected_holding_intervals=2` still required?
- Should strategy proceed to orderbook-aware replay?
- Which of the three decisions applies: `watchlist_only`, `funding_persistence_study_required`, or `enter_orderbook_aware_replay`?

**Step 4: Verify review has no placeholders**

```bash
rg -n "TODO|TBD|粘贴|占位|PLAN_NEEDS_VALUE|UNRESOLVED" docs/reviews/2026-05-26-extreme-funding-admission-definition-revision-review.md
```

Expected: no output.

**Step 5: Commit**

```bash
git add reports/extreme_funding/2026-05-26_*_admission_definition_* \
        docs/reviews/2026-05-26-extreme-funding-admission-definition-revision-review.md
git commit -m "docs+report: review revised extreme funding admission definition"
```

---

## Done Definition

This plan is complete when:

- Extreme Funding has explicit three-layer admission terminology.
- `expected_holding_intervals=2` is restricted to optimistic shadow analysis.
- Research shadow admission no longer pretends to be trade admission.
- Trade candidate gate still requires conservative 1 interval proof.
- New replay summary separates anchor events, research shadow cases, and trade candidates.
- Summary includes `research_to_trade_blocker_counts`.
- Review ends with exactly one decision: `watchlist_only`, `funding_persistence_study_required`, or `enter_orderbook_aware_replay`.
- Review clearly states whether revised entry logic is enough to continue or whether the strategy remains watchlist-only.

## Risk Controls

- No execution integration.
- No live trading.
- No private API.
- No weakening of `RISK_MAX_SINGLE_POSITION_USDT`.
- Any candidate from Layer B must be tagged research-only.
- Layer C remains blocked until orderbook-aware replay proves real depth and slippage.
