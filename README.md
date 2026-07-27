# crypto-alpha-lab

**Personal crypto alpha research and evidence verification lab with a safe execution base.**

This project is **not** an arbitrage system and **not** a yield machine. It is an **alpha verification lab** designed for personal research under a 5,000 – 50,000 USDT capital scale assumption. All unverified candidates are treated strictly as hypotheses, not profit sources.

---

## Current Safety Status

All safety controls and risk boundaries are governed by [configs/base.py](configs/base.py) and [src/risk/limits.py](src/risk/limits.py):

* `RISK_LIVE_TRADING_ENABLED = False` — The system boots strictly in observation mode.
* `trade_signal_allowed = False` — No automated trade signals may be produced.
* `paper_trading_allowed = False` — No paper trading or simulated order execution permitted.
* `live_trading_allowed = False` — Live trading execution is disabled.
* `execution_engine_allowed = False` — Execution engine connections are disabled.
* `alpha_interpretation_allowed = False` — Observation artifacts must not be interpreted as validated alpha without formal evidence review.
* `execution_feasibility_claim_allowed = False` — No claim of orderbook execution feasibility is permitted.

---

## Current Research Focus

The current primary research focus is **External Signal Shadow Lab (Stage 1.5)** — observing live exchange catalyst announcements, collecting real-time L2 orderbook depth snapshots, and auditing data quality under strict evidence gates.

For detailed runtime state, research specs, and document indexes, refer to:
* [Current Project State (docs/project-status/current-project-state_CN.md)](docs/project-status/current-project-state_CN.md)
* [Research Roadmap & Decision Log (docs/roadmap.md)](docs/roadmap.md)
* [Current Document Index (docs/project-status/current-document-index_CN.md)](docs/project-status/current-document-index_CN.md)

---

## Architecture

```text
crypto-alpha-lab/
├── configs/
│   └── base.py                        # Single source of truth for all thresholds and flags
├── src/
│   ├── execution/                     # Atomic dual-leg execution engine (verbatim migrated, 355 lines)
│   │   └── order_executor.py          # 7 failure recovery paths (maker timeout, rollback, inventory guard)
│   ├── strategies/                    # Base strategy interfaces
│   │   └── base.py                    # SignalCandidate dataclass and BaseStrategy contract
│   ├── risk/                          # Position limits and risk gates
│   │   └── limits.py                  # RiskLimits snapshot and live trading guard
│   └── research/external_signal_shadow/ # External catalyst shadow observation pipeline (Stage 1.5)
│       ├── stage1_5d_live_event_source_* # Stage 1.5D: Announcement collector + BAPI detail parser + 202 retry scheduler
│       ├── stage1_5f_live_depth_*       # Stage 1.5F: L2 orderbook observer + launch gate + watermark v2 + terminal hygiene
│       ├── stage1_5g_live_depth_*       # Stage 1.5G: Offline depth snapshot auditor (Clean / Quarantine / Invalid)
│       └── stage1_5h_static_execution_* # Stage 1.5H: Static read-only execution proxy reporter (Strict read-only)
└── scripts/external_signal_shadow/     # Operational runners and offline review tools (Stage 1.3 - 1.5H)
```

---

## Source-of-Truth Order

When evaluating system state, thresholds, or implementation decisions, adhere strictly to this priority order:

1. `configs/base.py` — Configuration constants and safety flags.
2. `docs/project-status/current-project-state_CN.md` — Verified local and server runtime snapshot.
3. `docs/project-status/current-document-index_CN.md` — Valid document index and authority entrypoints.
4. `src/`, `scripts/`, `tests/` — Verified source code and unit/integration test suite.
5. Runtime Artifacts — Output summaries, watermarks, and observer state files.
6. `docs/roadmap.md` — Research roadmap and decision log.

---

## Quick Start

### Installation & Dependency Management

```bash
# Install dependencies using uv
uv sync --all-extras
```

### Verification & Testing

```bash
# Run pytest test suite
make test

# Run verbose pytest
make test-verbose

# Run ruff code linter
make lint

# Run compileall and safety gate smoke check
make smoke

# Run full check (lint + test)
make check
```

---

## Safety Invariants

1. **Capital Preservation First**: Capital preservation overrides all optimization or profit-seeking logic.
2. **Shadow-First Requirement**: Any entry, exit, or sizing logic change must be validated in shadow mode for at least one full strategy cycle before live consideration.
3. **No Private Credentials Required**: Public data collection and observation pipelines require no API keys, private credentials, or wallet signatures.
4. **No Output-Root Rewrite**: Operational scripts write append-only JSON/JSONL artifacts into explicit timestamped output roots without overwriting existing data.
5. **Execution Layer Integrity**: `src/execution/order_executor.py` (355 lines) must not be simplified. It handles 7 distinct remote and partial-fill recovery paths.

---

## Repository Map

```text
crypto-alpha-lab/
├── Makefile                           # Development targets (install, test, lint, smoke, check)
├── pyproject.toml                     # Python project metadata and dependencies
├── configs/                           # System configuration constants
│   ├── base.py
│   └── external_signal_shadow_price_map.json
├── src/                               # Core Python library
│   ├── execution/                     # Atomic execution engine
│   ├── risk/                          # Risk limits and risk gates
│   ├── strategies/                    # Strategy contracts (SignalCandidate)
│   └── research/                      # Research modules (cost model, external signal shadow)
├── scripts/                           # Operational runners and review scripts
│   └── external_signal_shadow/        # Stage 1.3 - 1.5H runner scripts
├── tests/                             # Pytest test suite
│   ├── execution/
│   ├── research/
│   └── scripts/
└── docs/                              # Project documentation
    ├── designs/                       # Component design specifications
    ├── plans/                         # Implementation plans
    ├── reviews/                       # Formal review reports
    ├── project-status/                # Project state and document index
    ├── strategy_specs/                # Research specs and roadmaps
    ├── ops/                           # Operations guides and sync logs
    └── roadmap.md                     # Research roadmap and decision log
```
