# Crypto Alpha Lab Research Roadmap & Decision Log

**Created:** 2026-05-23
**Latest State Audit:** 2026-09-26 (Evidence Date: 2026-09-26T08:50:00Z)
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

### Alpha Research Methodology v1

Project-wide alpha research follows `.agent/rules/L2_Alpha_Research_Methodology.md`. The methodological change does **not** relax L0 safety or evidence quality. It changes the research question from “does every event win?” to “does a preregistered rule show positive cost-adjusted expectancy across independent opportunities with survivable tail risk?”

Core implications:

* Win rate alone is not an Alpha pass/fail criterion; payoff distribution, MAE/MFE, tail loss, costs and capacity matter.
* Calendar duration is not sample size; strategy conclusions must use the declared independent event/episode unit and clustered splits where needed.
* Losing observations are allowed; unbounded ruin paths, negative cost-adjusted expectancy, hindsight tuning, invalid PIT evidence, or economically negligible capacity are not.
* `phenomenon_supported`, `alpha_candidate`, `alpha_validated`, `evidence_insufficient`, and `falsified` are distinct research states.
* Historical `falsified/stopped/superseded` tracks are not automatically reopened. Reconsideration requires a separate methodology audit showing the old kill materially depended on an invalid/incomplete criterion; routes killed by non-positive cost-adjusted edge or invalid evidence remain closed absent genuinely new evidence.


---

## 2. Current Position

*(Updated as of 2026-09-26 based on Stage 1.6F historical research completion and Stage 1.5 live server observation)*

* **Active Server Processes**:
  * **Stage 1.5D Live Collector**: PID 88580 running `run_stage1_5d_live_event_source_smoke_collector.py` under root `data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix` (tmux session `stage1_5d_continuous_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`).
  * **Stage 1.5F Live Depth Observer**: PID 88770 running `run_stage1_5f_live_depth_observer.py` under root `data/external_signal_shadow/stage1_5f/live_depth_observer_20260724T070442Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix` (tmux session `stage1_5f_live_depth_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`).
* **Active Verification State**:
  * Stage 1.5D: BAPI detail parser + 202 retry scheduler running continuously; zero detail retry starvation.
  * Stage 1.5F: Watermark Schema V2 active; 2643 heartbeats recorded; 76 pre-bootstrap historical anchors terminal ignored.
* **Stage 1.6F Historical Research State**:
  * **Stage 1.6F-W2 Evidence Expansion**: `w2_candidate_run_20260925_001`; 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined.
  * **Stage 1.6F-W2-0 Terminal Basis Diagnostic**: `w2_0_exploratory_20260926T071500Z`; 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive.
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
| **Cross-Sectional Factor Lab** | `stopped` | `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` (2026-06-10) | Tested 30d/14d pure-price momentum had negative cost-scenario portfolio performance and large drawdowns; this Stage A2 evidence does not evaluate or falsify non-price factors. | Retain tested price-only specification closed; any non-price factor requires a new L2 Design. | Not applicable to untested factors. |
| **Stage 0 – 1.2 (Shadow Setup)** | `completed` | `docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md` (2026-06-12) | Infrastructure and public read-only collectors verified. | Stage 1.3 signal discovery. | Network read failure rate > 5%. |
| **Stage 1.3 – 1.4E (Derivatives Stress)** | `superseded` | `docs/reviews/2026-06-20-external-signal-shadow-lab-stage1-4e-deleveraging-proxy-sensitivity-review_CN.md` (2026-06-20) | Local forceorder snapshots degraded by exchange rate-limiting. Pivot to Stage 1.5 catalyst announcements. | Superseded by Stage 1.5. | Exchange rate-limiting on forceorder stream. |
| **Stage 1.5A – 1.5C1 (Catalyst Replay)** | `completed` | `data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json` (2026-06-24) | Catalyst announcements verified to generate significant historical price response. | Stage 1.5D live collector. | Price coverage < 80%. |
| **Stage 1.5D (Live Event Collector)** | `active` | `_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5d/detail_retry_scheduler_state.json` (2026-07-26) | Server PID 88580 running continuously. BAPI detail parser + 202 retry scheduler active. | Maintain 7d continuous run. | Detail retry starvation > 1800s. |
| **Stage 1.5E (Static Execution Feasibility)** | `completed` | `data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json` (2026-06-25) | Static orderbook audit verified 500 USDT position depth capacity. | Stage 1.5F live observer. | Depth capacity < 500 USDT. |
| **Stage 1.5F (Live Depth Observer)** | `active` | `_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5f/live_depth_observer_summary.json` (2026-07-26) | Server PID 88770 running continuously. Launch gate active; 76 pre-bootstrap anchors terminal ignored. | Capture clean L2 orderbook evidence. | Network error rate > 5% or 0 heartbeats. |
| **Stage 1.5G (Depth Evidence Reviewer)** | `active` | `data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json` (2026-09-23) | Offline reviewer active. SPCXUSD1 and MOONSHOTUSDT passed Clean (MOONSHOTUSDT 99.44% coverage, P50 spread 5.85 bps); SKHYUSDT passed Quarantine; POPMARTUSDT invalid/quarantine candidate. Event-family evidence accumulating (2 Clean, 1 Quarantine). | Accumulate at least 3 unique symbols and 2 source articles under current evidence gates (currently 2 Clean symbols across 2 articles). | No additional clean/quarantine-valid samples after 30d continuous run. |
| **Stage 1.5H (Static Read-Only Report)** | `completed` | `data/external_signal_shadow/stage1_5h/reports/20260712T043755Z/stage1_5h_static_execution_proxy_report_summary.json` (2026-07-12) | Static read-only report generator implemented and verified. Hard safety flags enforced. | Maintain read-only tool role. | Any trade signal or execution feasibility claim. |
| **Stage 1.6A (Futures Delisting Source Schema & Grammar)** | `completed` | `docs/reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md` (2026-08-24) | Verified Binance futures delisting notice source, BAPI H2 versioned grammar, and 3 timestamp anchors. | Stage 1.6B delisting catalog. | Ambiguous delivery/settlement semantics or missing anchors. |
| **Stage 1.6B (Delisting Catalog & Event Burst Queue)** | `completed` | `docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md` (2026-08-22) | Canonical delisting catalog, burst queue failure recovery, and checkpoint contracts verified. | Stage 1.6E capability audit. | Unrecoverable queue drop under burst load. |
| **Stage 1.6E (Market Data Observer & Capability Audit)** | `completed` | `docs/reviews/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-completion-audit_CN.md` (2026-09-04) | Live semantic trigger observer and historical 1s kline / mark / index capability audit completed. | Stage 1.6F matched control. | Kline/mark/index coverage < 80%. |
| **Stage 1.6F (Historical Matched Control & Evidence Expansion)** | `completed` | `w2_candidate_run_20260925_001` | 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined. | conclusion closure only | checksum mismatch. |
| **Stage 1.6F-W2-0 (Exploratory Terminal Basis Diagnostic)** | `completed` | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json` | 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive. | `none_from_current_evidence` | no further gate from current evidence. |
---

## 4. Current Active Chain

### 4.1 Stage 1.5 Live Catalyst Observation Chain

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

### 4.2 Stage 1.6 Delisting Research & Diagnostic Chain

```text
Stage 1.6F W1/W2 evidence
  -> 180 physical source objects
  -> 41 contracts / 27 parents; 31 contracts / 21 parents window-defined
Stage 1.6F-W2-0 exploratory diagnostic
  -> 29 contracts / 19 parents exploratory_described
  -> outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]
  -> 3/19 negative; 16/19 positive
  -> conclusion closure only
```
---

## 5. Historical Completed and Stopped Research

Preserving historical research value and negative findings:

1. **Route C1 Price-Only Proxy 7-Day Live Smoke Test**:
   - Document: `docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md` (2026-07-05).
   - Finding: `stopped_no_promotion`. 904 / 1536 events achieved baseline/control matching (58.85416667% < 70%); the economic edge is not established. This is neither a cost-adjusted EV nor a win-rate falsification.
2. **Stage 1.4B-Lite Crowding-Only Replay**:
   - Document: `docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md` (2026-06-18).
   - Finding: `stopped_crowding_only`. The 21 events across 6 days had candidate counts 13 / 0 / 8; 500 baseline resampling trials are not 500 independent opportunities, and the top five positive events contributed 89.28914131% of gross positive profit. This does not evaluate or falsify a full derivatives-stress composite.
3. **Cross-Sectional Factor Lab Stage A2 (CMOM Factor)**:
   - Document: `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` (2026-06-10).
   - Finding: `retain_closed_for_tested_price_only_specification`. Across 77 weekly rebalances under the 30 bps cost scenario, tested 30d and 14d pure-price momentum had negative portfolio performance and large drawdowns. This does not falsify every cross-sectional factor.

---

## 6. Current Blockers

Organized by category:

* **Data / Verification Blocker (P3 - Stage 1.5G Live Depth)**:
  * **Issue**: Stage 1.5G 虽有 2 个 Clean 通过事件（`SPCXUSD1`, `MOONSHOTUSDT`），但新合约上线事件族样本量仍需持续累积至 $\ge 3$ 个独立标的。
  * **Evidence**: Stage 1.5G 历史评审记录及连续运行心跳。
  * **Required Action**: 保持 VPS 端 1.5D + 1.5F 进程持续运行并监控新上线合约。

---

## 7. Next Gates

### Gate 3: Stage 1.5G Event-Family Evidence Sufficiency
* **Prerequisite**: Stage 1.5D 和 1.5F 持续稳定运行。
* **Required Evidence**: 累积至少 3 个独立上线标的的 `stage1_5g_live_depth_evidence_review_summary.json`。
* **Pass Criteria**: 达到事件族样本量门槛且无致命污染。
* **Fail/Stop Criteria**: 连续 30 天无有效新样本或数据丢失率 $> 10\%$。
* **Safety Boundary**: 观察模式 (`trade_signal_allowed = False`)。

---

## 8. Decision Log

* **2026-05-23**: Pivoted from `my-bitcoin-project` (flat term structure, OKX timeouts) to `crypto-alpha-lab`. Established 5k-50k USDT capital scale assumption and verbatim migration of execution layer.
* **2026-06-10**: Retained the tested 30d/14d pure-price momentum specifications closed after 77 weekly rebalances showed negative 30 bps cost-scenario portfolio performance and large drawdowns; non-price factors are outside this closure's scope and were not reopened.
* **2026-06-18**: Stopped the Stage 1.4B-Lite crowding-only branch: 21 events over 6 days, candidate counts 13 / 0 / 8, and 500 baseline resampling trials rather than independent opportunities. The evidence was sparse and concentrated; no full derivatives-stress conclusion or Alpha claim follows.
* **2026-06-24**: Approved Stage 1.5D Live Announcement Collector design and completed Stage 1.5C price coverage expansion audit.
* **2026-06-26**: Approved Stage 1.5F Live Depth Observer design and deployed real-time L2 orderbook snapshot collection on server.
* **2026-07-05**: Stopped promotion of the Route C1 price-only proxy after 904 / 1536 baseline/control matches (58.85416667% < 70%); its economic edge is not established. This is not a net-EV or win-rate falsification.
* **2026-07-12**: Approved Stage 1.5H Static Execution Proxy Report Generator with strict read-only governance flags.
* **2026-07-19**: Finalized Master Assessment (`2026-07-19-event_source_master_assessment.md`). Approved Stage 1.6A (Futures Delisting) as top priority discovery route and Stage 1.6R (Security Incident) as Risk-Veto side route.
* **2026-07-24**: Implemented and verified Stage 1.5F historical-anchor rejection hygiene hotfix (watermark schema v2, terminal ignored pre-bootstrap state tracking).
* **2026-07-26**: Verified server 1.5D and 1.5F 7-day continuous run state; finalized unified project state (`current-project-state_CN.md`) and document index (`current-document-index_CN.md`).
* **2026-08-10**: Approved Stage 1.5D/1.5F Git Ancestry Attestation design and completed implementation plan. Producer emits version 2 formal schedule revision events; consumer accepts `[1, 2]`; producer configuration remains default disabled (`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False`).
* **2026-09-24**: Adopted project-level L2 Alpha Research Methodology: Alpha is evaluated by preregistered cost-adjusted expectancy across independent opportunities plus robustness, capacity and survivable tail risk; win rate/per-trade certainty is no longer a universal pass/fail criterion. Historical falsifications remain closed unless separately re-audited.
* **2026-09-25**: Stage 1.6F-W2 evidence expansion completed for `w2_candidate_run_20260925_001`: 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined.
* **2026-09-26**: Stage 1.6F-W2-0 exploratory diagnostic completed for `w2_0_exploratory_20260926T071500Z`: 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive.


---

## 9. Superseded Documents

For the complete list of historical, superseded, or falsified design, plan, and review documents, refer to the unified document index:

👉 **[docs/project-status/current-document-index_CN.md](project-status/current-document-index_CN.md)**
