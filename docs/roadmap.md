# Crypto Alpha Lab Research Roadmap & Decision Log

**Created:** 2026-05-23
**Latest State Audit:** 2026-07-26 (Evidence Date: 2026-07-26T02:11:01Z)
**Primary State File:** [docs/project-status/current-project-state_CN.md](project-status/current-project-state_CN.md)
**Document Index:** [docs/project-status/current-document-index_CN.md](project-status/current-document-index_CN.md)

---

## 1. Mission and Risk Boundary

`crypto-alpha-lab` is a personal alpha verification laboratory and safe execution base designed for research under a **5,000 – 50,000 USDT** capital scale assumption.

### Hard Safety Invariants

* **Observation First**: All unverified strategy candidates are treated as hypotheses. The system operates strictly in observation and shadow verification mode.
* **Live Trading Disabled**: `RISK_LIVE_TRADING_ENABLED = False` in [configs/base.py](../configs/base.py) and [src/risk/limits.py](../src/risk/limits.py).
* **Zero Trade Signals / Zero Execution Feasibility Claims**: All observation modules enforce `trade_signal_allowed = False`, `paper_trading_allowed = False`, `live_trading_allowed = False`, `execution_engine_allowed = False`, and `execution_feasibility_claim_allowed = False`.
* **Execution Layer Preservation**: The 355-line atomic dual-leg execution engine ([src/execution/order_executor.py](../src/execution/order_executor.py)) is migrated verbatim and frozen. It handles 7 distinct failure recovery paths (maker timeout, net edge check, hedge exception, dust fill rollback, abort on partial fill, duplicate intent rejection, force deleveraging lock).

---

## 2. Current Position

*(Extracted from verified runtime snapshot `_project_context/server_runtime_snapshot_20260726T021054Z.txt` and `docs/project-status/current-project-state_CN.md` as of 2026-07-26)*

* **Active Server Processes**:
  * **Stage 1.5D Live Collector**: PID 88580 running `run_stage1_5d_live_event_source_smoke_collector.py` under root `data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix` (tmux session `stage1_5d_continuous_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`).
  * **Stage 1.5F Live Depth Observer**: PID 88770 running `run_stage1_5f_live_depth_observer.py` under root `data/external_signal_shadow/stage1_5f/live_depth_observer_20260724T070442Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix` (tmux session `stage1_5f_live_depth_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`).
* **Active Verification State**:
  * Stage 1.5D: BAPI detail parser + 202 retry scheduler running continuously; zero detail retry starvation.
  * Stage 1.5F: Watermark Schema V2 active; 2643 heartbeats recorded; 76 pre-bootstrap historical anchors terminal ignored.
* **Current Blockers**:
  * **P1 Blocker**: Stage 1.5G has 1 clean pass event (`SPCXUSD1`), but event-family evidence remains under-sampled. Requires continued continuous observation until current event-family thresholds are met.

---

## 3. Research Track Matrix

> **Status Enumeration Allowed**: `active`, `blocked`, `observation_only`, `completed`, `falsified`, `stopped`, `superseded`, `planned`.

| Track | Status | Latest Evidence | Decision | Next Gate | Kill Criteria |
|---|---|---|---|---|---|
| **Original Carry / MR** | `stopped` | `docs/roadmap.md` (2026-05-23) | Term structure slope = 0.000 (flat carry); OKX spot timeouts broke 60-cycle history. | None (Historical baseline only) | Flat term structure persistence > 30 days. |
| **Extreme Funding Scanner** | `observation_only` | `docs/roadmap.md#historical-verification--backtest-results` (2026-05-23) | 5-year settled funding verified DOGE/XRP win rate > 64%; 74d local orderbook showed 0 signals due to exchange 10.95% API capping. | Shadow scanner daemon in 1.5 env. | Zero signals > 100% annualized funding over 30d. |
| **Trend / Liquidation Scanner** | `observation_only` | [configs/base.py:L124](../configs/base.py#L124) | Vol breakout (2.5x 30d baseline) + OI cascade directional candidate. Hard stop 1.5%, max 12h hold. | Shadow simulation in 1.5 env. | Net edge $\le$ 20 bps round-trip cost over 20 signals. |
| **Tactical Carry** | `stopped` | `docs/roadmap.md` (2026-05-23) | Replaced by Extreme Funding Scanner and Basis Desk due to flat term structure. | None | Flat term structure persistence. |
| **Long-Horizon Basis Desk** | `observation_only` | [configs/base.py:L145](../configs/base.py#L145) | Multi-day carry (10-25% funding, 3-7d hold). Basis drawdown halt >50% cumulative funding income required every 8h. | Basis DB & 8h Funding Flip detector. | Cumulative basis loss > 50% funding income or maker fill rate < 70%. |
| **Cross-Sectional Factor Lab** | `falsified` | `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` (2026-06-10) | Stage A2 CMOM factor excess return failed to outperform Cash Fallback after transaction costs. | Closed / Historical Reference. | Factor Sharpe uplift over cash fallback $\le 0$. |
| **Stage 0 – 1.2 (Shadow Setup)** | `completed` | `docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md` (2026-06-12) | Infrastructure and public read-only collectors verified. | Stage 1.3 signal discovery. | Network read failure rate > 5%. |
| **Stage 1.3 – 1.4E (Derivatives Stress)** | `superseded` | `docs/reviews/2026-06-20-external-signal-shadow-lab-stage1-4e-deleveraging-proxy-sensitivity-review_CN.md` (2026-06-20) | Local forceorder snapshots degraded by exchange rate-limiting. Pivot to Stage 1.5 catalyst announcements. | Superseded by Stage 1.5. | Exchange rate-limiting on forceorder stream. |
| **Stage 1.5A – 1.5C1 (Catalyst Replay)** | `completed` | `data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json` (2026-06-24) | Catalyst announcements verified to generate significant historical price response. | Stage 1.5D live collector. | Price coverage < 80%. |
| **Stage 1.5D (Live Event Collector)** | `active` | `_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5d/detail_retry_scheduler_state.json` (2026-07-26) | Server PID 88580 running continuously. BAPI detail parser + 202 retry scheduler active. | Maintain 7d continuous run. | Detail retry starvation > 1800s. |
| **Stage 1.5E (Static Execution Feasibility)** | `completed` | `data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json` (2026-06-25) | Static orderbook audit verified 500 USDT position depth capacity. | Stage 1.5F live observer. | Depth capacity < 500 USDT. |
| **Stage 1.5F (Live Depth Observer)** | `active` | `_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5f/live_depth_observer_summary.json` (2026-07-26) | Server PID 88770 running continuously. Launch gate active; 76 pre-bootstrap anchors terminal ignored. | Capture clean L2 orderbook evidence. | Network error rate > 5% or 0 heartbeats. |
| **Stage 1.5G (Depth Evidence Reviewer)** | `active` | `data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json` (2026-07-22) | Offline reviewer active. SPCXUSD1 passed Clean; SKHYUSDT passed Quarantine; POPMARTUSDT invalid/quarantine candidate. Event-family conclusion remains blocked by sample size. | Accumulate at least 3 unique symbols and 2 source articles under current evidence gates. | No additional clean/quarantine-valid samples after 30d continuous run. |
| **Stage 1.5H (Static Read-Only Report)** | `completed` | `data/external_signal_shadow/stage1_5h/reports/20260712T043755Z/stage1_5h_static_execution_proxy_report_summary.json` (2026-07-12) | Static read-only report generator implemented and verified. Hard safety flags enforced. | Maintain read-only tool role. | Any trade signal or execution feasibility claim. |
| **Stage 1.6 Roadmap (Futures Delisting 1.6A & Risk-Veto 1.6R)** | `planned` | `docs/strategy_specs/2026-07-19-event_source_master_assessment.md` (2026-07-19) | Master Assessment approved Stage 1.6A (Futures Delisting) and Stage 1.6R (Security Risk-Veto) as top priority design docs. | Write Stage 1.6A design doc. | Lack of auditable point-in-time timestamps. |

---

## 4. Current Active Chain

The active development and operational chain for the current observation phase is:

```text
Stage 1.5D Live Announcement Collector (PID 88580)
  ├── Binance Public Catalog API + BAPI Article Detail Parser
  └── 202 Accepted Retry Scheduler (State: detail_retry_scheduler_state.json)
        │
        ▼ (Outputs events/*.jsonl)
Stage 1.5F Live Depth Observer (PID 88770)
  ├── Launch-Time Age Gate (holds pending events until onboard time)
  ├── Watermark Schema V2 (bootstrap_max_seen_detected_at_ms)
  └── Terminal Hygiene Classifier (pre-bootstrap historical anchors -> terminal ignored, non-rejected)
        │
        ▼ (Outputs L2 depth snapshots & observer_state.jsonl)
Stage 1.5G Live Depth Evidence Reviewer (Offline Tool)
  ├── Audit L2 snapshot completeness, polarity, and initial warmup gaps
  └── Classify events: Clean Evidence Pass vs. Quarantine Pass vs. Invalid Failure
        │
        ▼
Stage 1.5H Static Execution Proxy Report Generator (Offline Tool)
  └── Strictly Read-Only Report Generation (trade_signal_allowed = False)
```

---

## 5. Completed and Falsified Work

Preserving historical research value and negative findings:

1. **Route C1 Price-Only Proxy 7-Day Live Smoke Test**:
   - Document: `docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md` (2026-07-05).
   - Finding: `falsified`. 7-day live smoke test showed high sample overlap, insufficient win rate, and net edge after fees $\le 0$. Route C1 price-only proxy branch terminated.
2. **Stage 1.4B-Lite Crowding-Only Replay**:
   - Document: `docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md` (2026-06-18).
   - Finding: `falsified`. 500 trials of crowding-only metrics showed zero statistically significant independent alpha. Decision made in Stage 1.4C to pivot to external catalyst announcements.
3. **Cross-Sectional Factor Lab Stage A2 (CMOM Factor)**:
   - Document: `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` (2026-06-10).
   - Finding: `falsified`. Cross-sectional momentum (CMOM) factor excess returns failed to clear transaction costs over Cash Fallback. Factor Lab closed.

---

## 6. Current Blockers

Organized by category:

* **Data / Verification Blocker (P1)**:
  * **Issue**: Stage 1.5G has 1 clean pass event, but event-family sample size is still insufficient.
  * **Evidence**: `data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json` (`decision = stage1_5g_depth_evidence_clean_pass`, `clean_depth_evidence_pass = true`).
  * **Risk**: A single clean event supports continued read-only Stage 1.5H design work, but cannot justify a family-level conclusion about catalyst launch depth quality.
  * **Required Action**: Maintain server 1.5D + 1.5F continuous run and continue reviewing new contract launch observations until current event-family thresholds are met.
* **Engineering / Design Blocker (P2)**:
  * **Issue**: Stage 1.6A (Futures Delisting Notice) design specification document not yet drafted.
  * **Evidence**: Roadmap Total Spec `docs/strategy_specs/2026-07-13-整理的后续事件源研究路线图-external-catalyst-event-sources-unified-research-roadmap_CN.md:L305`.
  * **Risk**: Delay in expanding into next-generation forced-flow event discovery.
  * **Required Action**: Draft `docs/designs/2026-07-26-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md`.

---

## 7. Next Gates

### Gate 1: Stage 1.5G Event-Family Evidence Sufficiency
* **Prerequisite**: Stage 1.5D and 1.5F continuous server observation running cleanly.
* **Required Evidence**: `stage1_5g_live_depth_evidence_review_summary.json` generated for each new contract launch event.
* **Current Evidence**: `SPCXUSD1` has already passed Clean (`clean_depth_evidence_pass = true`, `book_availability_ratio = 99.86%`).
* **Pass Criteria**: Event-family threshold is met with at least 3 unique symbols and 2 source articles, without any trade signal or execution feasibility permission being enabled.
* **Fail/Stop Criteria**: `invalid_book_ratio > 0.05` or missing snapshots $> 10\%$.
* **Safety Boundary**: Observation mode only (`trade_signal_allowed = False`).

### Gate 2: Stage 1.6A Futures Delisting Design Review
* **Prerequisite**: Stage 1.6 Unified Roadmap & Master Assessment approved.
* **Required Evidence**: Drafted `docs/designs/2026-07-26-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md`.
* **Pass Criteria**: Design review approved with clear definition of Binance futures delisting source, scope isolation, and 3 timestamp anchors (`available_at_ms`, `non_reduce_only_start_time_ms`, `settlement_time_ms`).
* **Fail/Stop Criteria**: Missing timestamp anchors or inability to separate futures delisting from spot/margin delisting.
* **Safety Boundary**: Read-only source audit design (`implementation_plan_allowed = False` until design approved).

---

## 8. Decision Log

* **2026-05-23**: Pivoted from `my-bitcoin-project` (flat term structure, OKX timeouts) to `crypto-alpha-lab`. Established 5k-50k USDT capital scale assumption and verbatim migration of execution layer.
* **2026-06-10**: Closed Cross-Sectional Factor Lab after Stage A2 CMOM factor failed to clear cash fallback.
* **2026-06-18**: Terminated Stage 1.4B derivatives stress crowding replay after 500 trials proved zero net edge. Pivoted in Stage 1.4C to Stage 1.5 External Catalyst Announcements.
* **2026-06-24**: Approved Stage 1.5D Live Announcement Collector design and completed Stage 1.5C price coverage expansion audit.
* **2026-06-26**: Approved Stage 1.5F Live Depth Observer design and deployed real-time L2 orderbook snapshot collection on server.
* **2026-07-05**: Terminated Route C1 price-only proxy after 7-day live smoke test failed win rate and net edge criteria.
* **2026-07-12**: Approved Stage 1.5H Static Execution Proxy Report Generator with strict read-only governance flags.
* **2026-07-19**: Finalized Master Assessment (`2026-07-19-event_source_master_assessment.md`). Approved Stage 1.6A (Futures Delisting) as top priority discovery route and Stage 1.6R (Security Incident) as Risk-Veto side route.
* **2026-07-24**: Implemented and verified Stage 1.5F historical-anchor rejection hygiene hotfix (watermark schema v2, terminal ignored pre-bootstrap state tracking).
* **2026-07-26**: Verified server 1.5D and 1.5F 7-day continuous run state; finalized unified project state (`current-project-state_CN.md`) and document index (`current-document-index_CN.md`).

---

## 9. Superseded Documents

For the complete list of historical, superseded, or falsified design, plan, and review documents, refer to the unified document index:

👉 **[docs/project-status/current-document-index_CN.md](project-status/current-document-index_CN.md)**
