# Extreme Funding Phase 1B Candidate Builder + Phase 1C Shadow Simulator 框架与 funding-only 边界验证实施计划

> **给 agentic workers:** REQUIRED SUB-SKILL: 使用 `superpowers:executing-plans` 或 `superpowers:subagent-driven-development` 按任务逐项执行。所有步骤使用 checkbox (`- [ ]`) 跟踪。

**目标:** 建立 `extreme_funding` 的 Phase 1B candidate builder contract、Phase 1C shadow simulator skeleton，并用 funding-only historical replay 验证证据边界：当前历史 settled funding 数据不得被误判为可交易 candidate 或完整 PnL 验证。

**架构:** Phase 1A 继续作为 observation-only watchlist 在服务器后台运行。Phase 1B 只在 row 具备 funding、watch/persistence gate、basis、cost、depth 字段时输出 observation-only `SignalCandidate`；funding-only replay 必须安全拒绝为 `missing_basis`。Phase 1C 可以模拟 shadow path，但 funding-only replay 只能输出 `funding_minus_cost` diagnostic，不能输出 `net_pnl_bps` / `win_rate` 这类容易被误读为完整盈利验证的字段。

**Tech Stack:** Python 3.11、pytest、dataclasses、`configs/base.py` 作为 SSOT、`src/strategies/base.py::SignalCandidate`、`data/funding_settled/*.jsonl`、`reports/extreme_funding/`、无 private API、无 execution import。

---

## 1. 本轮范围降级说明

本轮不是完整 Phase 1B / Phase 1C 策略验证。

本轮只完成：

- `ExtremeFundingCandidateDecision` 与 `build_extreme_funding_candidate(...)` contract。
- Phase 1B candidate 的 watch-level、persistence、annualized threshold、basis absorption、cost、depth gate。
- `ExtremeFundingShadowPosition` / `ExtremeFundingShadowResult` 与 `simulate_extreme_funding_shadow(...)` skeleton。
- funding-only historical replay loader。
- funding-only replay 的安全边界验证：不能生成 candidate，不能输出完整 `net_pnl_bps` / `win_rate`。
- review artifact，明确说明完整验证仍依赖 historical/live basis-aware rows。

本轮不完成：

- live trading。
- `TradeIntent` 生成。
- `src/execution/` 导入。
- private exchange endpoint。
- historical basis-aware replay。
- 真实 basis-aware PnL 结论。

---

## 2. 证据边界

当前 `data/funding_settled/*.jsonl` 只包含类似字段：

```json
{"symbol": "DOGE/USDT", "funding_time_ms": 1640995200000, "funding_rate": 0.0012, "mark_price": 0.17, "annualized_pct": 131.4}
```

它缺少：

- `spot_mid_price`
- `perp_mid_price`
- `basis_bps`
- `basis_path`
- `spot_depth_500usdt_bps`
- `perp_depth_500usdt_bps`
- realized slippage

所以本轮必须锁死：

- funding-only replay 可以验证 extreme funding 频率与 funding income 上限。
- funding-only replay 不能验证 `basis_absorption_ratio`。
- funding-only replay 不能验证完整 `net_pnl_bps`。
- funding-only replay 的 shadow 输出只能叫 `funding_minus_cost_bps`。
- 只有 `coverage_quality in {"historical_basis_aware", "live_basis_aware_observation"}` 时，后续版本才允许输出 `net_pnl_bps`、`win_rate`、`max_loss_bps`。

---

## 3. 必守不变量

- 所有 Phase 1B candidate 必须满足 `SignalCandidate.metadata["mode"] == "observation"`。
- 所有 Phase 1B candidate 必须满足 `SignalCandidate.metadata["executable"] is False`。
- Phase 1B 不导入 `src/execution/`、`TradeIntent`、API key、account balance、private config。
- Phase 1B 默认只按 `EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS = 1` 计算入选边际。
- Phase 1C 可以模拟最多 `EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS = 3` 个 funding intervals。
- `estimated_total_cost_bps = fee_bps + slippage_bps + rollback_reserve_bps`。
- `basis_absorption_ratio = max(basis_bps, 0) / expected_funding_income_bps`，仅在 `expected_funding_income_bps > 0` 时有效，否则拒绝。
- `basis_change_bps = current_basis_bps - entry_basis_bps`，正数代表 basis widening loss，负数代表 basis narrowing gain。
- risk halt 用 `basis_loss_bps = max(basis_change_bps, 0)`。
- 完整 PnL 公式只用于 basis-aware path：

```text
net_pnl_bps = funding_income_bps - basis_change_bps - estimated_total_cost_bps
```

---

## Task 1: Baseline And Scope Guard

**Files:**

- Read: `AGENTS.md`
- Read: `docs/roadmap.md`
- Read: `configs/base.py`
- Read: `src/strategies/base.py`
- Read: `src/strategies/extreme_funding/scanner.py`

- [ ] **Step 1: 读取项目规则与接口**

Run:

```bash
sed -n '1,220p' AGENTS.md
sed -n '1,260p' docs/roadmap.md
sed -n '1,260p' configs/base.py
sed -n '1,200p' src/strategies/base.py
sed -n '1,280p' src/strategies/extreme_funding/scanner.py
```

Expected:

- 确认 `SignalCandidate` 当前字段为 `direction`、`confidence`、`entry_exchange`、`hedge_exchange`、`trigger_reason`、`invalidation_reason`、`max_holding_hours`、`stop_loss_pct`、`suggested_notional_usdt`、`metadata`。
- 确认 Phase 1A watchlist scanner 不导入 execution。

- [ ] **Step 2: 运行当前基线测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py tests/scripts/test_run_extreme_funding_watchlist.py tests/test_extreme_funding_config.py -q
PYTHONPATH=src uv run pytest tests -q
```

Expected:

```text
PASS
```

- [ ] **Step 3: Safety grep**

Run:

```bash
rg -n "src\.execution|TradeIntent|apiKey|secret|private|balance" src/strategies src/research scripts tests || true
```

Expected:

- 不应在 `src/strategies/extreme_funding/` 发现 execution/private 依赖。

---

## Task 2: Add Phase 1B / 1C Config Constants

**Files:**

- Modify: `configs/base.py`
- Test: `tests/test_extreme_funding_config.py`

- [ ] **Step 1: 写 failing config tests**

Append to `tests/test_extreme_funding_config.py`:

```python
def test_extreme_funding_phase1b_candidate_config_values_are_defined() -> None:
    import configs.base as config

    assert config.EXTREME_FUNDING_MIN_NET_EDGE_BPS == 30.0
    assert config.EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO == 0.50
    assert config.EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS == 1
    assert config.EXTREME_FUNDING_MIN_EXPECTED_FUNDING_INCOME_BPS == 50.0
    assert config.EXTREME_FUNDING_FEE_BPS == 8.0
    assert config.EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS == 8.0
    assert config.EXTREME_FUNDING_ROLLBACK_RESERVE_BPS == 10.0
    assert config.EXTREME_FUNDING_MAX_SLIPPAGE_BPS == 10.0


def test_extreme_funding_phase1c_shadow_config_values_are_defined() -> None:
    import configs.base as config

    assert config.EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS == 3
    assert config.EXTREME_FUNDING_SHADOW_EXIT_ANNUALIZED_BELOW_PCT == 15.0
    assert config.EXTREME_FUNDING_SHADOW_BASIS_LOSS_HALT_RATIO == 0.50
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py::test_extreme_funding_phase1b_candidate_config_values_are_defined tests/test_extreme_funding_config.py::test_extreme_funding_phase1c_shadow_config_values_are_defined -q
```

Expected:

```text
FAIL AttributeError
```

- [ ] **Step 3: 在 `configs/base.py` 新增常量**

Add near existing `EXTREME_FUNDING_*` constants:

```python
# Extreme Funding Phase 1B candidate builder. Observation-only thresholds.
EXTREME_FUNDING_MIN_NET_EDGE_BPS = 30.0
EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO = 0.50
EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS = 1
EXTREME_FUNDING_MIN_EXPECTED_FUNDING_INCOME_BPS = 50.0
EXTREME_FUNDING_FEE_BPS = 8.0
EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS = 8.0
EXTREME_FUNDING_ROLLBACK_RESERVE_BPS = 10.0
EXTREME_FUNDING_MAX_SLIPPAGE_BPS = 10.0

# Extreme Funding Phase 1C shadow simulator. No live execution.
EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS = 3
EXTREME_FUNDING_SHADOW_EXIT_ANNUALIZED_BELOW_PCT = 15.0
EXTREME_FUNDING_SHADOW_BASIS_LOSS_HALT_RATIO = 0.50
```

- [ ] **Step 4: 运行 config tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py -q
```

Expected:

```text
PASS
```

---

## Task 3: Add Phase 1B Candidate Builder Contract

**Files:**

- Create: `src/strategies/extreme_funding/candidate_builder.py`
- Test: `tests/strategies/test_extreme_funding_candidate_builder.py`

- [ ] **Step 1: 写 accepted candidate failing test**

Create `tests/strategies/test_extreme_funding_candidate_builder.py`:

```python
from src.strategies.base import SignalCandidate
from src.strategies.extreme_funding.candidate_builder import build_extreme_funding_candidate


def _complete_row(**overrides):
    row = {
        "timestamp_ms": 1710000000000,
        "source_type": "live_watch_event",
        "symbol": "DOGE/USDT",
        "exchange": "binance",
        "direction": "neutral",
        "annualized_funding_estimate_pct": 650.0,
        "funding_rate_per_interval": 0.008,
        "expected_holding_intervals": 1,
        "basis_bps": 10.0,
        "basis_source": "spot_perp_mid",
        "fee_bps": 8.0,
        "slippage_bps": 8.0,
        "rollback_reserve_bps": 10.0,
        "depth_capacity_usdt": 2000.0,
        "planned_notional_usdt": 500.0,
        "micro_persistence": 0.80,
        "settlement_persistence": 0.50,
        "watch_level": "watch_level_3",
        "coverage_quality": "live_basis_aware_observation",
    }
    row.update(overrides)
    return row


def test_build_candidate_accepts_complete_basis_aware_row() -> None:
    decision = build_extreme_funding_candidate(_complete_row())

    assert decision.accepted is True
    assert decision.reject_reason is None
    assert isinstance(decision.candidate, SignalCandidate)
    assert decision.candidate.strategy_type == "extreme_funding"
    assert decision.candidate.symbol == "DOGE/USDT"
    assert decision.candidate.direction == "neutral"
    assert decision.candidate.expected_edge_bps == 44.0
    assert decision.candidate.metadata["mode"] == "observation"
    assert decision.candidate.metadata["executable"] is False
    assert decision.candidate.metadata["estimated_total_cost_bps"] == 26.0
    assert decision.candidate.metadata["basis_absorption_ratio"] == 0.125
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_candidate_builder.py::test_build_candidate_accepts_complete_basis_aware_row -q
```

Expected:

```text
FAIL ModuleNotFoundError
```

- [ ] **Step 3: 实现 candidate builder**

Create `src/strategies/extreme_funding/candidate_builder.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from configs.base import (
    EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO,
    EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS,
    EXTREME_FUNDING_FEE_BPS,
    EXTREME_FUNDING_MAX_HOLDING_HOURS,
    EXTREME_FUNDING_MAX_SLIPPAGE_BPS,
    EXTREME_FUNDING_MIN_EXPECTED_FUNDING_INCOME_BPS,
    EXTREME_FUNDING_MIN_NET_EDGE_BPS,
    EXTREME_FUNDING_MICRO_PERSISTENCE_MIN,
    EXTREME_FUNDING_ROLLBACK_RESERVE_BPS,
    EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS,
    EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
    RISK_MAX_SINGLE_POSITION_USDT,
)
from src.strategies.base import SignalCandidate

_ALLOWED_WATCH_LEVELS = {"watch_level_2", "watch_level_3", "historical_settled_extreme"}


@dataclass(frozen=True)
class ExtremeFundingCandidateDecision:
    accepted: bool
    candidate: SignalCandidate | None
    reject_reason: str | None
    metrics: dict[str, Any]


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:
        return None
    return result


def _reject(reason: str, metrics: dict[str, Any]) -> ExtremeFundingCandidateDecision:
    return ExtremeFundingCandidateDecision(False, None, reason, metrics)


def _costs(row: dict[str, Any]) -> tuple[float, float, float, float]:
    fee_bps = _number_or_none(row.get("fee_bps"))
    slippage_bps = _number_or_none(row.get("slippage_bps"))
    rollback_reserve_bps = _number_or_none(row.get("rollback_reserve_bps"))
    fee_bps = EXTREME_FUNDING_FEE_BPS if fee_bps is None else fee_bps
    slippage_bps = EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS if slippage_bps is None else slippage_bps
    rollback_reserve_bps = (
        EXTREME_FUNDING_ROLLBACK_RESERVE_BPS
        if rollback_reserve_bps is None
        else rollback_reserve_bps
    )
    return fee_bps, slippage_bps, rollback_reserve_bps, fee_bps + slippage_bps + rollback_reserve_bps


def build_extreme_funding_candidate(row: dict[str, Any]) -> ExtremeFundingCandidateDecision:
    symbol = str(row.get("symbol") or "UNKNOWN")
    exchange = str(row.get("exchange") or "unknown")
    source_type = str(row.get("source_type") or "live_watch_event")
    watch_level = str(row.get("watch_level") or "")
    annualized_pct = _number_or_none(row.get("annualized_funding_estimate_pct"))
    micro_persistence = _number_or_none(row.get("micro_persistence"))
    settlement_persistence = _number_or_none(row.get("settlement_persistence"))
    funding_rate_per_interval = _number_or_none(row.get("funding_rate_per_interval"))
    basis_bps = _number_or_none(row.get("basis_bps"))
    depth_capacity_usdt = _number_or_none(row.get("depth_capacity_usdt"))
    planned_notional_usdt = _number_or_none(row.get("planned_notional_usdt")) or RISK_MAX_SINGLE_POSITION_USDT
    expected_intervals = int(_number_or_none(row.get("expected_holding_intervals")) or EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS)
    fee_bps, slippage_bps, rollback_reserve_bps, estimated_total_cost_bps = _costs(row)

    metrics: dict[str, Any] = {
        "symbol": symbol,
        "exchange": exchange,
        "source_type": source_type,
        "watch_level": watch_level,
        "annualized_funding_estimate_pct": annualized_pct,
        "micro_persistence": micro_persistence,
        "settlement_persistence": settlement_persistence,
        "expected_holding_intervals": expected_intervals,
        "fee_bps": fee_bps,
        "slippage_bps": slippage_bps,
        "rollback_reserve_bps": rollback_reserve_bps,
        "estimated_total_cost_bps": estimated_total_cost_bps,
    }

    if watch_level not in _ALLOWED_WATCH_LEVELS:
        return _reject("watch_level_too_weak", metrics)
    if annualized_pct is None or annualized_pct < EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT:
        return _reject("annualized_funding_below_trade_threshold", metrics)
    if source_type == "historical_settled":
        if settlement_persistence is None or settlement_persistence < 0.50:
            return _reject("settlement_persistence_below_min", metrics)
    elif micro_persistence is None or micro_persistence < EXTREME_FUNDING_MICRO_PERSISTENCE_MIN:
        return _reject("micro_persistence_below_min", metrics)
    if funding_rate_per_interval is None:
        return _reject("missing_funding_rate", metrics)
    if basis_bps is None:
        return _reject("missing_basis", metrics)

    expected_funding_income_bps = funding_rate_per_interval * expected_intervals * 10_000.0
    basis_cost_bps = max(basis_bps, 0.0)
    basis_absorption_ratio = (
        basis_cost_bps / expected_funding_income_bps
        if expected_funding_income_bps > 0.0
        else float("inf")
    )
    net_edge_bps = expected_funding_income_bps - basis_cost_bps - estimated_total_cost_bps
    metrics.update(
        {
            "funding_rate_per_interval": funding_rate_per_interval,
            "basis_bps": basis_bps,
            "basis_cost_bps": basis_cost_bps,
            "basis_absorption_ratio": basis_absorption_ratio,
            "expected_funding_income_bps": expected_funding_income_bps,
            "net_edge_bps": net_edge_bps,
            "depth_capacity_usdt": depth_capacity_usdt,
            "planned_notional_usdt": planned_notional_usdt,
        }
    )

    if expected_funding_income_bps < EXTREME_FUNDING_MIN_EXPECTED_FUNDING_INCOME_BPS:
        return _reject("expected_funding_income_below_min", metrics)
    if basis_absorption_ratio > EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO:
        return _reject("basis_absorbed", metrics)
    if net_edge_bps < EXTREME_FUNDING_MIN_NET_EDGE_BPS:
        return _reject("net_edge_below_min", metrics)
    if slippage_bps > EXTREME_FUNDING_MAX_SLIPPAGE_BPS:
        return _reject("slippage_above_max", metrics)
    if depth_capacity_usdt is None:
        return _reject("missing_depth_capacity", metrics)
    if depth_capacity_usdt < planned_notional_usdt * 2.0:
        return _reject("depth_capacity_insufficient", metrics)

    candidate = SignalCandidate(
        strategy_type="extreme_funding",
        symbol=symbol,
        direction=str(row.get("direction") or "neutral"),
        confidence=0.60,
        expected_edge_bps=round(net_edge_bps, 10),
        entry_exchange=exchange,
        hedge_exchange=exchange,
        trigger_reason="extreme_funding_basis_aware_candidate",
        invalidation_reason="funding_decay_or_basis_loss_halt",
        max_holding_hours=float(EXTREME_FUNDING_MAX_HOLDING_HOURS),
        stop_loss_pct=0.0,
        suggested_notional_usdt=min(planned_notional_usdt, RISK_MAX_SINGLE_POSITION_USDT),
        metadata={
            "mode": "observation",
            "executable": False,
            "coverage_quality": row.get("coverage_quality", "live_basis_aware_observation"),
            "source_type": source_type,
            "watch_level": watch_level,
            "basis_source": row.get("basis_source"),
            "basis_bps": basis_bps,
            "basis_absorption_ratio": round(basis_absorption_ratio, 10),
            "expected_funding_income_bps": round(expected_funding_income_bps, 10),
            "fee_bps": fee_bps,
            "slippage_bps": slippage_bps,
            "rollback_reserve_bps": rollback_reserve_bps,
            "estimated_total_cost_bps": estimated_total_cost_bps,
            "expected_holding_intervals": expected_intervals,
        },
    )
    return ExtremeFundingCandidateDecision(True, candidate, None, metrics)
```

- [ ] **Step 4: 运行 accepted test**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_candidate_builder.py::test_build_candidate_accepts_complete_basis_aware_row -q
```

Expected:

```text
PASS
```

---

## Task 4: Add Phase 1B Reject Reason Tests

**Files:**

- Modify: `tests/strategies/test_extreme_funding_candidate_builder.py`

- [ ] **Step 1: 增加 gate / reject tests**

Append:

```python

def test_candidate_rejects_weak_watch_level() -> None:
    decision = build_extreme_funding_candidate(_complete_row(watch_level="watch_level_1"))
    assert decision.accepted is False
    assert decision.reject_reason == "watch_level_too_weak"


def test_candidate_rejects_low_micro_persistence_for_live_row() -> None:
    decision = build_extreme_funding_candidate(_complete_row(micro_persistence=0.50))
    assert decision.accepted is False
    assert decision.reject_reason == "micro_persistence_below_min"


def test_candidate_rejects_low_settlement_persistence_for_historical_row() -> None:
    decision = build_extreme_funding_candidate(
        _complete_row(
            source_type="historical_settled",
            watch_level="historical_settled_extreme",
            micro_persistence=None,
            settlement_persistence=0.20,
        )
    )
    assert decision.accepted is False
    assert decision.reject_reason == "settlement_persistence_below_min"


def test_candidate_rejects_annualized_below_trade_threshold() -> None:
    decision = build_extreme_funding_candidate(_complete_row(annualized_funding_estimate_pct=80.0))
    assert decision.accepted is False
    assert decision.reject_reason == "annualized_funding_below_trade_threshold"


def test_candidate_rejects_missing_basis() -> None:
    row = _complete_row()
    row.pop("basis_bps")
    decision = build_extreme_funding_candidate(row)
    assert decision.accepted is False
    assert decision.reject_reason == "missing_basis"


def test_candidate_rejects_basis_absorbed() -> None:
    decision = build_extreme_funding_candidate(_complete_row(basis_bps=50.0))
    assert decision.accepted is False
    assert decision.reject_reason == "basis_absorbed"


def test_candidate_rejects_net_edge_below_min() -> None:
    decision = build_extreme_funding_candidate(_complete_row(funding_rate_per_interval=0.006, basis_bps=10.0))
    assert decision.accepted is False
    assert decision.reject_reason == "net_edge_below_min"


def test_candidate_rejects_expected_funding_income_below_min() -> None:
    decision = build_extreme_funding_candidate(
        _complete_row(
            annualized_funding_estimate_pct=120.0,
            funding_rate_per_interval=0.0049,
            basis_bps=0.0,
        )
    )
    assert decision.accepted is False
    assert decision.reject_reason == "expected_funding_income_below_min"


def test_candidate_rejects_slippage_above_max() -> None:
    decision = build_extreme_funding_candidate(_complete_row(slippage_bps=12.0))
    assert decision.accepted is False
    assert decision.reject_reason == "slippage_above_max"


def test_candidate_rejects_missing_depth_capacity() -> None:
    row = _complete_row()
    row.pop("depth_capacity_usdt")
    decision = build_extreme_funding_candidate(row)
    assert decision.accepted is False
    assert decision.reject_reason == "missing_depth_capacity"


def test_candidate_rejects_depth_capacity_insufficient() -> None:
    decision = build_extreme_funding_candidate(_complete_row(depth_capacity_usdt=600.0, planned_notional_usdt=500.0))
    assert decision.accepted is False
    assert decision.reject_reason == "depth_capacity_insufficient"
```

- [ ] **Step 2: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_candidate_builder.py -q
```

Expected:

```text
PASS
```

---

## Task 5: Add Historical Funding Replay Loader

**Files:**

- Create: `src/research/extreme_funding_replay.py`
- Test: `tests/research/test_extreme_funding_replay.py`

- [ ] **Step 1: 写 replay loader tests**

Create `tests/research/test_extreme_funding_replay.py`:

```python
import json

from src.research.extreme_funding_replay import detect_extreme_funding_segments, load_settled_funding_rows


def test_load_settled_funding_rows_from_jsonl(tmp_path) -> None:
    path = tmp_path / "funding.jsonl"
    path.write_text(
        json.dumps({"symbol": "DOGE/USDT", "funding_time_ms": 1000, "funding_rate": 0.001, "mark_price": 0.2, "annualized_pct": 109.5}) + "\n",
        encoding="utf-8",
    )
    rows = load_settled_funding_rows(path)
    assert len(rows) == 1
    assert rows[0].symbol == "DOGE/USDT"
    assert rows[0].coverage_quality == "funding_only_insufficient_for_basis"


def test_detect_extreme_funding_segments_groups_consecutive_rows() -> None:
    rows = [
        {"symbol": "DOGE/USDT", "funding_time_ms": 1, "funding_rate": 0.001, "annualized_pct": 109.5},
        {"symbol": "DOGE/USDT", "funding_time_ms": 2, "funding_rate": 0.0011, "annualized_pct": 120.4},
        {"symbol": "DOGE/USDT", "funding_time_ms": 3, "funding_rate": 0.0001, "annualized_pct": 10.9},
        {"symbol": "DOGE/USDT", "funding_time_ms": 4, "funding_rate": 0.0012, "annualized_pct": 131.4},
    ]
    segments = detect_extreme_funding_segments(rows, threshold_pct=100.0)
    assert len(segments) == 2
    assert segments[0]["row_count"] == 2
    assert segments[0]["coverage_quality"] == "funding_only_insufficient_for_basis"
```

- [ ] **Step 2: Run tests to confirm fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/test_extreme_funding_replay.py -q
```

Expected:

```text
FAIL ModuleNotFoundError
```

- [ ] **Step 3: Implement replay loader**

Create `src/research/extreme_funding_replay.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class SettledFundingRow:
    symbol: str
    funding_time_ms: int
    funding_rate: float
    annualized_pct: float
    mark_price: float | None = None
    coverage_quality: str = "funding_only_insufficient_for_basis"


def load_settled_funding_rows(path: str | Path) -> list[SettledFundingRow]:
    rows: list[SettledFundingRow] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            rows.append(
                SettledFundingRow(
                    symbol=str(raw["symbol"]),
                    funding_time_ms=int(raw["funding_time_ms"]),
                    funding_rate=float(raw["funding_rate"]),
                    annualized_pct=float(raw["annualized_pct"]),
                    mark_price=float(raw["mark_price"]) if raw.get("mark_price") is not None else None,
                )
            )
    return rows


def _as_dict(row: SettledFundingRow | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, SettledFundingRow):
        return {
            "symbol": row.symbol,
            "funding_time_ms": row.funding_time_ms,
            "funding_rate": row.funding_rate,
            "annualized_pct": row.annualized_pct,
            "mark_price": row.mark_price,
            "coverage_quality": row.coverage_quality,
        }
    return row


def detect_extreme_funding_segments(
    rows: Iterable[SettledFundingRow | dict[str, Any]],
    *,
    threshold_pct: float,
) -> list[dict[str, Any]]:
    sorted_rows = sorted((_as_dict(row) for row in rows), key=lambda item: (str(item["symbol"]), int(item["funding_time_ms"])))
    segments: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_symbol: str | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            return
        annualized_values = [float(item["annualized_pct"]) for item in current]
        funding_income_bps = sum(float(item["funding_rate"]) * 10_000.0 for item in current)
        segments.append(
            {
                "symbol": str(current[0]["symbol"]),
                "start_ms": int(current[0]["funding_time_ms"]),
                "end_ms": int(current[-1]["funding_time_ms"]),
                "row_count": len(current),
                "max_annualized_pct": max(annualized_values),
                "median_annualized_pct": sorted(annualized_values)[len(annualized_values) // 2],
                "funding_income_bps": funding_income_bps,
                "settlement_persistence": 1.0,
                "coverage_quality": "funding_only_insufficient_for_basis",
            }
        )
        current = []

    for row in sorted_rows:
        symbol = str(row["symbol"])
        if symbol != current_symbol:
            flush()
            current_symbol = symbol
        if float(row["annualized_pct"]) >= threshold_pct:
            current.append(row)
        else:
            flush()
    flush()
    return segments
```

- [ ] **Step 4: Run replay tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/test_extreme_funding_replay.py -q
```

Expected:

```text
PASS
```

---

## Task 6: Add Phase 1C Shadow Simulator Skeleton

**Files:**

- Create: `src/strategies/extreme_funding/shadow_simulator.py`
- Test: `tests/strategies/test_extreme_funding_shadow_simulator.py`

- [ ] **Step 1: 写 shadow simulator tests**

Create `tests/strategies/test_extreme_funding_shadow_simulator.py`:

```python
from src.strategies.extreme_funding.shadow_simulator import ExtremeFundingShadowPosition, simulate_extreme_funding_shadow


def _position(**overrides):
    position = {
        "symbol": "DOGE/USDT",
        "side": "long_spot_short_perp",
        "entry_time_ms": 1000,
        "entry_basis_bps": 10.0,
        "estimated_total_cost_bps": 26.0,
        "notional_usdt": 500.0,
        "max_holding_intervals": 3,
        "coverage_quality": "historical_basis_aware",
    }
    position.update(overrides)
    return ExtremeFundingShadowPosition(**position)


def test_shadow_simulator_counts_basis_narrowing_as_gain() -> None:
    result = simulate_extreme_funding_shadow(
        _position(),
        [{"funding_time_ms": 2000, "funding_rate": 0.008, "basis_bps": 5.0, "annualized_pct": 650.0}],
    )
    assert result.exit_reason == "path_exhausted"
    assert result.basis_change_bps == -5.0
    assert result.basis_loss_bps == 0.0
    assert result.net_pnl_bps == 59.0


def test_shadow_simulator_stops_on_basis_loss_halt() -> None:
    result = simulate_extreme_funding_shadow(
        _position(),
        [{"funding_time_ms": 2000, "funding_rate": 0.008, "basis_bps": 60.0, "annualized_pct": 650.0}],
    )
    assert result.exit_reason == "basis_loss_halt"
    assert result.basis_change_bps == 50.0
    assert result.basis_loss_bps == 50.0


def test_shadow_simulator_stops_on_funding_flip() -> None:
    result = simulate_extreme_funding_shadow(
        _position(),
        [{"funding_time_ms": 2000, "funding_rate": -0.0001, "basis_bps": 10.0, "annualized_pct": -10.0}],
    )
    assert result.exit_reason == "funding_flip"


def test_shadow_simulator_stops_on_funding_decay_after_counting_interval() -> None:
    result = simulate_extreme_funding_shadow(
        _position(),
        [{"funding_time_ms": 2000, "funding_rate": 0.0001, "basis_bps": 10.0, "annualized_pct": 10.0}],
    )
    assert result.exit_reason == "funding_decay"
    assert result.funding_income_bps == 1.0


def test_shadow_simulator_marks_funding_only_coverage_as_insufficient() -> None:
    result = simulate_extreme_funding_shadow(
        _position(entry_basis_bps=0.0, max_holding_intervals=1, coverage_quality="funding_only_insufficient_for_basis"),
        [{"funding_time_ms": 2000, "funding_rate": 0.008, "annualized_pct": 650.0}],
    )
    assert result.coverage_quality == "funding_only_insufficient_for_basis"
    assert result.notes == ["basis_path_missing"]
```

- [ ] **Step 2: Run tests to confirm fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_shadow_simulator.py -q
```

Expected:

```text
FAIL ModuleNotFoundError
```

- [ ] **Step 3: Implement shadow simulator**

Create `src/strategies/extreme_funding/shadow_simulator.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from configs.base import (
    EXTREME_FUNDING_SHADOW_BASIS_LOSS_HALT_RATIO,
    EXTREME_FUNDING_SHADOW_EXIT_ANNUALIZED_BELOW_PCT,
)


@dataclass(frozen=True)
class ExtremeFundingShadowPosition:
    symbol: str
    side: str
    entry_time_ms: int
    entry_basis_bps: float
    estimated_total_cost_bps: float
    notional_usdt: float
    max_holding_intervals: int
    coverage_quality: str


@dataclass(frozen=True)
class ExtremeFundingShadowResult:
    symbol: str
    side: str
    closed: bool
    exit_reason: str
    intervals_held: int
    funding_income_bps: float
    basis_change_bps: float
    basis_loss_bps: float
    estimated_total_cost_bps: float
    net_pnl_bps: float
    coverage_quality: str
    notes: list[str]


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:
        return None
    return result


def simulate_extreme_funding_shadow(position: ExtremeFundingShadowPosition, path: list[dict[str, Any]]) -> ExtremeFundingShadowResult:
    funding_income_bps = 0.0
    basis_change_bps = 0.0
    notes: list[str] = []
    exit_reason = "path_exhausted"
    intervals_held = 0

    for row in path:
        if intervals_held >= position.max_holding_intervals:
            exit_reason = "max_holding_intervals_reached"
            break

        funding_rate = _number_or_none(row.get("funding_rate")) or 0.0
        funding_income_bps += funding_rate * 10_000.0
        intervals_held += 1

        basis_bps = _number_or_none(row.get("basis_bps"))
        if basis_bps is None:
            if "basis_path_missing" not in notes:
                notes.append("basis_path_missing")
            basis_bps = position.entry_basis_bps

        basis_change_bps = basis_bps - position.entry_basis_bps
        basis_loss_bps = max(basis_change_bps, 0.0)

        if funding_rate < 0.0:
            exit_reason = "funding_flip"
            break

        annualized_pct = _number_or_none(row.get("annualized_pct"))
        if annualized_pct is not None and annualized_pct < EXTREME_FUNDING_SHADOW_EXIT_ANNUALIZED_BELOW_PCT:
            exit_reason = "funding_decay"
            break

        if funding_income_bps > 0.0 and basis_loss_bps > funding_income_bps * EXTREME_FUNDING_SHADOW_BASIS_LOSS_HALT_RATIO:
            exit_reason = "basis_loss_halt"
            break

    if intervals_held >= position.max_holding_intervals and exit_reason == "path_exhausted":
        exit_reason = "max_holding_intervals_reached"

    net_pnl_bps = funding_income_bps - basis_change_bps - position.estimated_total_cost_bps
    return ExtremeFundingShadowResult(
        symbol=position.symbol,
        side=position.side,
        closed=True,
        exit_reason=exit_reason,
        intervals_held=intervals_held,
        funding_income_bps=round(funding_income_bps, 10),
        basis_change_bps=round(basis_change_bps, 10),
        basis_loss_bps=round(max(basis_change_bps, 0.0), 10),
        estimated_total_cost_bps=position.estimated_total_cost_bps,
        net_pnl_bps=round(net_pnl_bps, 10),
        coverage_quality=position.coverage_quality,
        notes=notes,
    )
```

- [ ] **Step 4: Run shadow tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_shadow_simulator.py -q
```

Expected:

```text
PASS
```

---

## Task 7: Add Funding-only Candidate Replay Script

**Files:**

- Create: `scripts/replay_extreme_funding_candidates.py`
- Test: `tests/scripts/test_replay_extreme_funding_candidates.py`
- Output: `reports/extreme_funding/2026-05-25_candidate_replay_summary.json`

- [ ] **Step 1: 写 script test**

Create `tests/scripts/test_replay_extreme_funding_candidates.py`:

```python
import json

from scripts.replay_extreme_funding_candidates import build_candidate_replay_summary


def test_candidate_replay_summary_marks_funding_only_rows_as_missing_basis(tmp_path) -> None:
    path = tmp_path / "binance_doge_settled.jsonl"
    path.write_text(json.dumps({"symbol": "DOGE/USDT", "funding_time_ms": 1000, "funding_rate": 0.008, "mark_price": 0.2, "annualized_pct": 650.0}) + "\n", encoding="utf-8")
    summary = build_candidate_replay_summary([path], threshold_pct=100.0)
    assert summary["input_file_count"] == 1
    assert summary["segments_seen"] == 1
    assert summary["has_threshold_segments"] is True
    assert summary["status"] == "ok"
    assert summary["candidate_count"] == 0
    assert summary["reject_reason_counts"] == {"missing_basis": 1}
    assert summary["coverage_quality"] == "funding_only_insufficient_for_basis"


def test_candidate_replay_summary_marks_empty_input() -> None:
    summary = build_candidate_replay_summary([], threshold_pct=100.0)
    assert summary["input_file_count"] == 0
    assert summary["segments_seen"] == 0
    assert summary["candidate_count"] == 0
    assert summary["has_threshold_segments"] is False
    assert summary["status"] == "no_threshold_segments_or_no_input"
```

- [ ] **Step 2: Implement script**

Create `scripts/replay_extreme_funding_candidates.py`:

```python
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.research.extreme_funding_replay import detect_extreme_funding_segments, load_settled_funding_rows
from src.strategies.extreme_funding.candidate_builder import build_extreme_funding_candidate


def _segment_to_candidate_row(segment: dict[str, Any]) -> dict[str, Any]:
    intervals = int(segment["row_count"])
    funding_income_bps = float(segment["funding_income_bps"])
    return {
        "timestamp_ms": int(segment["start_ms"]),
        "source_type": "historical_settled",
        "symbol": str(segment["symbol"]),
        "exchange": "binance",
        "direction": "neutral",
        "watch_level": "historical_settled_extreme",
        "annualized_funding_estimate_pct": float(segment["max_annualized_pct"]),
        "funding_rate_per_interval": funding_income_bps / intervals / 10_000.0 if intervals else 0.0,
        "expected_holding_intervals": 1,
        "settlement_persistence": float(segment.get("settlement_persistence", 1.0)),
        "coverage_quality": "funding_only_insufficient_for_basis",
    }


def build_candidate_replay_summary(paths: list[str | Path], *, threshold_pct: float) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    for path in paths:
        segments.extend(detect_extreme_funding_segments(load_settled_funding_rows(path), threshold_pct=threshold_pct))

    reject_counts: Counter[str] = Counter()
    candidate_count = 0
    for segment in segments:
        decision = build_extreme_funding_candidate(_segment_to_candidate_row(segment))
        if decision.accepted:
            candidate_count += 1
        else:
            reject_counts[decision.reject_reason or "unknown_reject"] += 1

    has_threshold_segments = len(segments) > 0
    return {
        "threshold_pct": threshold_pct,
        "input_file_count": len(paths),
        "segments_seen": len(segments),
        "has_threshold_segments": has_threshold_segments,
        "status": "ok" if has_threshold_segments else "no_threshold_segments_or_no_input",
        "candidate_count": candidate_count,
        "reject_reason_counts": dict(sorted(reject_counts.items())),
        "coverage_quality": "funding_only_insufficient_for_basis",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay extreme funding Phase 1B funding-only candidates.")
    parser.add_argument("--input-glob", default="data/funding_settled/binance_*_settled.jsonl")
    parser.add_argument("--threshold-pct", type=float, default=100.0)
    parser.add_argument("--output", default="reports/extreme_funding/2026-05-25_candidate_replay_summary.json")
    args = parser.parse_args()
    summary = build_candidate_replay_summary(sorted(Path().glob(args.input_glob)), threshold_pct=args.threshold_pct)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run tests and replay**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_replay_extreme_funding_candidates.py -q
PYTHONPATH=src uv run python scripts/replay_extreme_funding_candidates.py --input-glob 'data/funding_settled/binance_*_settled.jsonl' --threshold-pct 100 --output reports/extreme_funding/2026-05-25_candidate_replay_summary.json
```

Expected:

- test PASS。
- summary 中包含 `input_file_count`、`has_threshold_segments`、`status`。
- 如果 `has_threshold_segments is True`，summary 中 `candidate_count == 0` 且 `reject_reason_counts["missing_basis"] > 0`。
- 如果没有输入文件或没有 threshold segment，`status == "no_threshold_segments_or_no_input"`，不能把空结果误读为策略验证成功。

---

## Task 8: Add Funding-only Shadow Diagnostic Script

**Files:**

- Create: `scripts/simulate_extreme_funding_shadow.py`
- Test: `tests/scripts/test_simulate_extreme_funding_shadow.py`
- Output: `reports/extreme_funding/2026-05-25_shadow_replay_summary.json`

- [ ] **Step 1: 写 funding-only diagnostic test**

Create `tests/scripts/test_simulate_extreme_funding_shadow.py`:

```python
from scripts.simulate_extreme_funding_shadow import build_shadow_replay_summary


def test_shadow_replay_summary_uses_funding_minus_cost_names_for_funding_only() -> None:
    segments = [{"symbol": "DOGE/USDT", "start_ms": 1000, "row_count": 1, "funding_income_bps": 80.0, "coverage_quality": "funding_only_insufficient_for_basis"}]
    summary = build_shadow_replay_summary(segments)
    assert summary["shadow_trade_count"] == 1
    assert summary["median_funding_minus_cost_bps"] == 54.0
    assert summary["positive_funding_minus_cost_rate"] == 1.0
    assert "median_net_pnl_bps" not in summary
    assert "win_rate" not in summary
    assert summary["coverage_quality"] == "funding_only_insufficient_for_basis"
```

- [ ] **Step 2: Implement funding-only diagnostic script**

Create `scripts/simulate_extreme_funding_shadow.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any

from configs.base import EXTREME_FUNDING_FEE_BPS, EXTREME_FUNDING_ROLLBACK_RESERVE_BPS, EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS, EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS
from src.research.extreme_funding_replay import detect_extreme_funding_segments, load_settled_funding_rows


def build_shadow_replay_summary(segments: list[dict[str, Any]]) -> dict[str, Any]:
    total_cost_bps = EXTREME_FUNDING_FEE_BPS + EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS + EXTREME_FUNDING_ROLLBACK_RESERVE_BPS
    funding_minus_cost_values: list[float] = []
    for segment in segments:
        capped_income = float(segment["funding_income_bps"])
        if int(segment["row_count"]) > EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS:
            capped_income = capped_income * EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS / int(segment["row_count"])
        funding_minus_cost_values.append(capped_income - total_cost_bps)

    return {
        "shadow_trade_count": len(funding_minus_cost_values),
        "median_funding_minus_cost_bps": median(funding_minus_cost_values) if funding_minus_cost_values else 0.0,
        "mean_funding_minus_cost_bps": sum(funding_minus_cost_values) / len(funding_minus_cost_values) if funding_minus_cost_values else 0.0,
        "positive_funding_minus_cost_rate": sum(1 for value in funding_minus_cost_values if value > 0.0) / len(funding_minus_cost_values) if funding_minus_cost_values else 0.0,
        "coverage_quality": "funding_only_insufficient_for_basis",
        "notes": ["funding_only_replay_does_not_validate_basis_absorption", "funding_only_replay_does_not_validate_net_pnl"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate extreme funding Phase 1C funding-only diagnostics.")
    parser.add_argument("--input-glob", default="data/funding_settled/binance_*_settled.jsonl")
    parser.add_argument("--threshold-pct", type=float, default=100.0)
    parser.add_argument("--output", default="reports/extreme_funding/2026-05-25_shadow_replay_summary.json")
    args = parser.parse_args()
    segments: list[dict[str, Any]] = []
    for path in sorted(Path().glob(args.input_glob)):
        segments.extend(detect_extreme_funding_segments(load_settled_funding_rows(path), threshold_pct=args.threshold_pct))
    summary = build_shadow_replay_summary(segments)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run tests and diagnostic replay**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_simulate_extreme_funding_shadow.py -q
PYTHONPATH=src uv run python scripts/simulate_extreme_funding_shadow.py --input-glob 'data/funding_settled/binance_*_settled.jsonl' --threshold-pct 100 --output reports/extreme_funding/2026-05-25_shadow_replay_summary.json
```

Expected:

- test PASS。
- output 中没有 `median_net_pnl_bps` 和 `win_rate`。
- output 中有 `median_funding_minus_cost_bps`。

---

## Task 9: Add Review Artifact

**Files:**

- Create: `docs/reviews/2026-05-25-extreme-funding-phase1b-1c-funding-only-boundary-review.md`
- Read: `reports/extreme_funding/2026-05-25_candidate_replay_summary.json`
- Read: `reports/extreme_funding/2026-05-25_shadow_replay_summary.json`

- [ ] **Step 1: 生成 review 文档**

Create `docs/reviews/2026-05-25-extreme-funding-phase1b-1c-funding-only-boundary-review.md` with actual summary numbers from generated JSON files.

Required text:

```markdown
# Extreme Funding Phase 1B / 1C funding-only 边界验证结论

## 1. 结论

本轮没有证明 `Extreme Funding` 已具备可交易盈利能力。

本轮只证明：

- Phase 1B candidate builder contract 可运行。
- Phase 1C shadow simulator skeleton 可运行。
- funding-only historical replay 不会被误判成 basis-aware candidate。
- funding-only shadow 只能输出 `funding_minus_cost` diagnostic，不能输出完整 `net_pnl_bps` / `win_rate`。

## 2. Candidate Replay Summary

在该小节内嵌入 `reports/extreme_funding/2026-05-25_candidate_replay_summary.json` 的完整 JSON 输出。

## 3. Shadow Diagnostic Summary

在该小节内嵌入 `reports/extreme_funding/2026-05-25_shadow_replay_summary.json` 的完整 JSON 输出。

## 4. 下一步

下一份计划应是 `Historical Basis-Aware Replay Plan`，至少补齐：

- historical `spot_mid_price`
- historical `perp_mid_price`
- `basis_bps`
- funding time alignment
- entry / holding period basis path
- depth / slippage proxy
- `historical_basis_aware` observation row
- basis-aware candidate replay
- basis-aware shadow PnL summary
```

最终 review 文件必须包含两个 summary 的实际 JSON block，不保留人工待替换文本。

- [ ] **Step 2: 检查 review 没有未替换文本**

Run:

```bash
rg -n "__REPLACE_ME__|UNRESOLVED_TOKEN" docs/reviews/2026-05-25-extreme-funding-phase1b-1c-funding-only-boundary-review.md
```

Expected:

```text
(no output)
```

---

## Task 10: Full Verification

- [ ] **Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=src uv run pytest \
  tests/test_extreme_funding_config.py \
  tests/strategies/test_extreme_funding_candidate_builder.py \
  tests/research/test_extreme_funding_replay.py \
  tests/strategies/test_extreme_funding_shadow_simulator.py \
  tests/scripts/test_replay_extreme_funding_candidates.py \
  tests/scripts/test_simulate_extreme_funding_shadow.py \
  -q
```

Expected:

```text
PASS
```

- [ ] **Step 2: Run full tests and smoke**

Run:

```bash
make test
make smoke
```

Expected:

```text
PASS
configs OK
risk gate OK
```

- [ ] **Step 3: Safety grep**

Run:

```bash
rg -n "src\.execution|TradeIntent|apiKey|secret|private|balance" src/strategies/extreme_funding src/research scripts/replay_extreme_funding_candidates.py scripts/simulate_extreme_funding_shadow.py || true
```

Expected:

- 不应出现新增 execution/private 依赖。

- [ ] **Step 4: 输出产物检查**

Run:

```bash
ls -lh reports/extreme_funding/2026-05-25_candidate_replay_summary.json reports/extreme_funding/2026-05-25_shadow_replay_summary.json
cat reports/extreme_funding/2026-05-25_candidate_replay_summary.json
cat reports/extreme_funding/2026-05-25_shadow_replay_summary.json
```

Expected:

- 两个 summary 文件存在。
- candidate summary 使用 `candidate_count` / `reject_reason_counts`。
- shadow summary 使用 `median_funding_minus_cost_bps` / `positive_funding_minus_cost_rate`。
- shadow summary 不包含 `median_net_pnl_bps` / `win_rate`。

---

## Done Definition

本计划完成后的准确表述：

- `candidate_builder.py` 已实现，但 funding-only replay 不应产生 candidate。
- `shadow_simulator.py` 已实现 skeleton，但 funding-only replay 只能输出 `funding_minus_cost` diagnostic。
- `reports/extreme_funding/` 下生成审计态 summary，不提交到 `data/` 作为运行态数据。
- review 文档明确说明本轮没有证明策略可交易盈利。
- 完整 Phase 1B / 1C 策略验证仍依赖下一步 `Historical Basis-Aware Replay Plan` 或未来 `live_basis_aware_observation` rows。
- 所有测试通过。
- 没有 execution/private API 依赖。

---

## Execution Handoff

计划完成并保存到：

`docs/plans/2026-05-25-extreme-funding-phase1b-candidate-builder-phase1c-shadow-simulator-implementation-plan.md`

执行选项：

1. **Subagent-Driven（推荐）**：每个 task 一个 fresh subagent，task 完成后人工 review。
2. **Inline Execution**：在当前会话使用 `superpowers:executing-plans` 逐 task 执行，关键节点停下来复核。
