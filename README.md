# crypto-alpha-lab

**Personal crypto alpha research and evidence verification lab with a safe execution base.**

This project is **not** an arbitrage system and **not** a yield machine. It is an **alpha verification lab** designed for personal quantitative research under a 5,000 – 50,000 USDT capital scale assumption. All unverified candidates are treated strictly as hypotheses, not profit sources.

---

## 1. Safety Status & Invariants (L0 Financial Safety)

All safety controls and risk boundaries are governed exclusively by [configs/base.py](configs/base.py) (single source of truth) and [src/risk/limits.py](src/risk/limits.py):

* **Live Trading Disabled**: `RISK_LIVE_TRADING_ENABLED = False` — The system operates strictly in observation and shadow verification mode.
* **Authority Denial Vectors**: All observation and diagnostic modules enforce strict fail-closed authority vectors:
  * `trade_signal_allowed = False` — No automated trading signals (`SignalCandidate` / `TradeIntent`) may be produced.
  * `paper_trading_allowed = False` — No paper trading or simulated order execution permitted.
  * `live_trading_allowed = False` — Live order placement is completely disabled.
  * `execution_engine_allowed = False` — Connections to exchange execution engines are prohibited.
  * `alpha_interpretation_allowed = False` — Diagnostic evidence must not be interpreted as validated alpha without formal research gates.
  * `execution_feasibility_claim_allowed = False` — No orderbook execution feasibility claims are permitted.
* **Execution Layer Preservation**: The 355-line atomic dual-leg execution engine ([src/execution/order_executor.py](src/execution/order_executor.py)) is verbatim migrated and frozen. It handles 7 distinct failure recovery paths (maker timeout, net edge check, hedge exception, dust fill rollback, abort on partial fill, duplicate intent rejection, force deleveraging lock).

---

## 2. Research Methodology (L2 Alpha Research Methodology)

Project-wide alpha research follows [.agent/rules/L2_Alpha_Research_Methodology.md](.agent/rules/L2_Alpha_Research_Methodology.md):

1. **Expectancy Across Independent Opportunities**: Alpha is evaluated by preregistered, cost-adjusted expected value across independent opportunities with survivable tail risk (drawdown, MAE/MFE, capacity, execution friction), rather than win rate or per-trade certainty alone.
2. **Separation of Claims**:
   $$\text{phenomenon\_supported} \neq \text{alpha\_candidate} \neq \text{executable\_edge} \neq \text{live\_safe}$$
   Evidence of an observed market pattern does not imply positive post-cost expectancy, let alone execution feasibility or trading permission.
3. **Independent Sampling Unit**: The statistical unit is the independent parent catalyst (e.g. parent announcement article), not correlated child symbols or overlapping time slices.
4. **Outcome Distribution**: Studies report full outcome distributions (win rate, payoff ratio, mean, median, P10/P25/P50/P75/P90, MAE, MFE, maximum loss), not simplistic averages.
5. **Strict Anti-Hindsight**: All rules, horizons, friction models, and kill criteria are preregistered before outcome inspection.

---

## 3. Active Research Tracks & Current Milestones (as of October 2026)

### 3.1 External Signal Shadow Lab (Stage 1.5 — Catalyst Announcements & L2 Microstructure)
* **Stage 1.5D (Live Event Collector)**: PID 88580 running continuously on server; Binance public catalog + BAPI article detail parser + 202 retry scheduler active.
* **Stage 1.5F (Live Depth Observer)**: PID 88770 running continuously on server; real-time L2 orderbook snapshot collection + launch-time age gate + Watermark Schema V2 + terminal hygiene ignore classifier active.
* **Stage 1.5G N=3 (Regime-Stratified Event-Family Admission)**:
  * Admitted 3 independent parent articles/events and 9 formal child symbols stratified into 3 distinct product regimes: `crypto_standard_perpetual` (`CTUSDT`), `pre_ipo_equity_perpetual` (`MOONSHOTUSDT`), and `tradfi_equity_or_etf_perpetual_batch` (7 symbols: `CRML`, `BWET`, `ACN`, `MP`, `SECZ`, `UNH`, `NKE`).
  * Passed Gate 3 sample quantity threshold; downstream consumers strictly fail-closed (`STOP=stage1_5g_n3_future_consumer_not_authorized`).
* **Stage 1.5H N=3 (Product-Regime Stratified Liquidity Friction Diagnostic)**:
  * Evaluated double-sided P95 slippage and spread friction across 9 child symbols / 3 parent events.
  * **Empirical Finding**: Microstructure friction exhibits extreme regime stratification:
    * `crypto_standard_perpetual`: 17.99 bps marginal P95 slippage sum (p50 spread 5.66 bps, availability 99.58%).
    * `pre_ipo_equity_perpetual`: 31.58 bps marginal P95 slippage sum (p50 spread 5.85 bps, depth ratio 22.40x).
    * `tradfi_equity_or_etf_perpetual_batch`: 80.02 bps median marginal P95 slippage sum (p50 spread 29.71 bps, up to 87.43 bps).
  * Cross-regime pooling and uniform friction floors are strictly prohibited; research classification strictly `evidence_insufficient`.

### 3.2 Futures Delisting Observation (Stage 1.6 — Contract Delisting Catalysts)
* **Stage 1.6A–1.6C**: Notice source grammar, burst queue failure recovery, and sealed export adapters completed.
* **Stage 1.6D (Live VPS Observation)**: Runbook governance completed ([docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md](docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md)); awaiting target preflight transcript and explicit user deployment authorization.
* **Stage 1.6E–1.6F**: Kline/mark/index capability completed; Stage 1.6F-W2-0 exploratory terminal basis diagnostic completed (descriptive conclusion closure only).

### 3.3 Historical Signal Readmission Preflight (Stage 1.3 R10)
* Offline structural bars reader + Git-anchored manifest + point-in-time event causality gate verified; downstream consumers hard-blocked fail-closed (`STOP=stage1_3_r10_readmission_future_consumer_binding_missing`).

### 3.4 Historical Reference & Stopped Routes
* **Carry / Flat Term Structure**: OKX spot timeouts and flat carry slope ($\le 0.000$); logic frozen as baseline.
* **Route C1 (Price-Only Proxy)**: 7-day smoke test stopped due to baseline/control matching rate $58.85\% < 70\%$; no promotion.
* **Stage 1.4B-Lite (Crowding-Only)**: Stopped due to event concentration (top 5 positive events contributed $89.29\%$ of gross profit across 21 events / 6 days).
* **Cross-Sectional Factor Lab (Stage A2 CMOM)**: Tested pure-price 30d/14d momentum closed after negative portfolio performance under 30 bps cost scenario.

---

## 4. Architecture & Repository Map

```text
crypto-alpha-lab/
├── configs/
│   ├── base.py                        # Single source of truth for all constants, thresholds, and limits
│   └── external_signal_shadow_price_map.json
├── src/
│   ├── execution/                     # Atomic dual-leg execution engine (verbatim migrated, 355 lines)
│   │   └── order_executor.py          # 7 failure recovery paths (maker timeout, rollback, inventory guard)
│   ├── strategies/                    # Strategy interfaces and strong types
│   │   └── base.py                    # SignalCandidate dataclass and BaseStrategy contract
│   ├── risk/                          # Position limits and risk gates
│   │   └── limits.py                  # RiskLimits snapshot and live trading guard
│   └── research/                      # Quantitative research and shadow observation pipelines
│       ├── cost_model.py              # Exchange fee, slippage, and borrow cost calculations
│       └── external_signal_shadow/    # Catalyst shadow observation modules (Stage 1.3 - 1.6)
│           ├── stage1_3_r10_readmission.py # Stage 1.3 R10: Offline readmission preflight gate
│           ├── stage1_5d_live_event_source_* # Stage 1.5D: Live announcement collector & BAPI detail parser
│           ├── stage1_5f_live_depth_*       # Stage 1.5F: L2 depth observer, watermark v2, terminal hygiene
│           ├── stage1_5g_n3_regime_stratified_admission.py # Stage 1.5G N=3: Regime-stratified admission
│           ├── stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py # Stage 1.5H N=3: Friction diagnostic
│           ├── stage1_6a_futures_delisting_* # Stage 1.6A: Delisting source grammar and sealed adapter
│           ├── stage1_6b_canonical_source_* # Stage 1.6B: Delisting event burst queue and checkpointing
│           ├── stage1_6e_*                  # Stage 1.6E: Semantic observer and capability audit
│           └── stage1_6f_*                  # Stage 1.6F: Matched control and basis diagnostic
├── scripts/external_signal_shadow/     # Operational runners and CLI review tools (Stage 1.3 - 1.6)
├── tests/                             # Comprehensive test suites (unit, integration, mutation, AST guards)
├── docs/                              # Project documentation and decision logs
│   ├── designs/                       # Formal design specifications
│   ├── plans/                         # Executable implementation plans
│   ├── reviews/                       # Formal audit and code review reports
│   ├── project-status/                # Primary project state and document index
│   │   ├── current-project-state_CN.md
│   │   └── current-document-index_CN.md
│   ├── ops/                           # Operational runbooks and checklists
│   └── roadmap.md                     # Research roadmap and decision log
└── Makefile                           # Standard development targets
```

---

## 5. Source-of-Truth Hierarchy

When evaluating system state, thresholds, or technical decisions, adhere strictly to this priority order:

1. `configs/base.py` — Configuration constants and safety thresholds (no magic numbers inside `src/`).
2. `docs/project-status/current-project-state_CN.md` — Verified local and server runtime snapshot.
3. `docs/project-status/current-document-index_CN.md` — Document index and current authority entrypoints.
4. `src/`, `scripts/`, `tests/` — Verified source code, production call paths, and test suites.
5. Runtime Artifacts (`data/external_signal_shadow/...`) — Sealed production receipts, summaries, and manifests.
6. `docs/roadmap.md` — Research roadmap and decision log.

---

## 6. Quick Start

### Installation & Dependency Management

```bash
# Install and synchronize dependencies using uv
uv sync --all-extras
```

### Verification & Testing

```bash
# Run pytest test suite
make test

# Run verbose pytest test suite
make test-verbose

# Run ruff linter
make lint

# Run compileall and safety gate smoke check
make smoke

# Run full check (lint + test)
make check

# Run anti-shortcut scanner (AST & contract integrity)
python3 .agent/tools/anti_shortcut_scan.py
```

---

## 7. Operational Guidelines for AI Agents

All AI agents operating in this repository must comply with persistent rules defined in `AGENTS.md`:

1. **Priority Hierarchy**: L0 Financial Safety > L1 Engineering Process > L2 Alpha Research Methodology > Project Workflows.
2. **Mandatory Planning**: Always follow `.agent/skills/writing-plans` and receive explicit user confirmation before modifying code in `src/`.
3. **No Phantom Files**: Do NOT reference `src/main.py` or `src/config.py` — they do not exist in this project.
4. **TDD for Logic**: Core logic changes require test-driven development (write failing tests before implementation).
5. **No Speculative Abstractions**: Implement the smallest, most boring solution that satisfies verified goals.
6. **Documentation Policy**: Human review documents are written in Chinese while code identifiers, file paths, configurations, and class names must retain exact English spellings.
