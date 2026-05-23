# crypto-alpha-lab

**Personal crypto alpha research and small-position live execution platform.**

Not an arbitrage system. Not a yield machine. An **alpha verification lab** with a safe execution base.

---

## Project Context

This project was created in May 2026, pivoting from `my-bitcoin-project` (a carry/MR arbitrage system
that was technically sound but blocked by market structure — flat term structure and data pipeline fragility).

The decision: stop engineering around dead alpha. Start fresh with better alpha hypotheses.

Read [`docs/roadmap.md`](docs/roadmap.md) for the full design rationale and strategy specifications.

---

## Architecture

```
src/
  exchange/        Exchange client + core market data fetch functions
  execution/       Atomic dual-leg execution engine (state machine, rollback, inventory guard)
  risk/            Position limits, kill switch, equity curve protection
  data/            Minimal schemas (MarketSnapshot, SignalCandidate) + SQLite store
  research/        Cost model, replay framework
  strategies/      Strategy implementations (each in its own subdirectory)
    extreme_funding/     Extreme Funding Event Scanner
    trend_regime/        Trend / Liquidation Regime
    long_horizon_basis/  Long-Horizon Funding Basis Desk
configs/
  base.py          All configuration constants (no magic numbers in src/)
docs/
  roadmap.md       Decision log and strategy specs
  strategy_specs/  Per-strategy detailed specifications
tests/
  execution/       Full execution layer test suite (migrated + verified)
```

---

## 30-Day Sprint Plan

| Days | Phase | Goal |
|---|---|---|
| 1–10 | Extreme Funding Scanner | Data observation only. No execution. Verify real opportunity frequency. |
| 11–20 | Trend / Liquidation Regime | Shadow simulation. Measure expectancy after fees. |
| 21–25 | Long-Horizon Basis Desk (data) | Build Basis history DB and Funding Flip detector. No trading. |
| 26–30 | Long-Horizon Basis Desk (shadow) | Shadow position simulation only if Funding Persistence > 0.6. |

**No live trading until all 8 pre-live checks in `docs/roadmap.md` are satisfied.**

---

## Quick Start

```bash
# Install dependencies
uv sync --all-extras

# Run all tests
make test

# Run smoke checks
make smoke

# Lint + format
make check
```

---

## Key Design Constraints

1. **Execution layer is migrated verbatim from battle-tested code.** Do not simplify it.
2. **`risk.limits.live_trading_enabled` defaults to `False`.** Must be explicitly enabled per strategy.
3. **Every strategy must define entry + exit + stop-loss as an atomic unit.** No entry-only logic.
4. **Shadow mode before any real money.** Minimum 30 days observation per strategy.
5. **Max single position: 500 USDT. Max concurrent positions: 2.**

---

## Reference Archive

Old project (frozen): `/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/`  
Conversation log: ID `1833b66a-1d4e-455c-aedd-1d6b8cb9b9ea`
