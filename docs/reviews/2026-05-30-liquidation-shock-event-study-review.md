# Liquidation Shock 1m Event Study Review

**Review Date:** 2026-05-30  
**Primary Decision:** `INSUFFICIENT_1M_DATA_DEPTH`  
**Phase 2 Status:** `DO NOT PROCEED`  
**Primary Reason:** Real Coinalyze `1m` liquidation coverage is too sparse and discontinuous to support the required `24h` trailing anomaly window plus a post-lookback evaluation window.

---

## 1. Executive Summary

- **Feasibility outcome:** failed
- **Qualified symbols:** `0 / 5`
- **Route to Phase 2:** blocked
- **Action:** stop this `1m shock -> fixed 5/10/15 minute response` line under the current data source

This review supersedes the earlier intermediate `continue_to_context_bucketing` interpretation. That earlier result came from a response-map pass on an already-built dataset. After rerunning the feasibility probe with a real `COINALYZE_API_KEY`, the governing result is that the `1m` source itself does **not** satisfy the research plan’s data-depth and continuity requirements.

---

## 2. Feasibility Gate Result

Source:
- [2026-05-30_liquidation_shock_event_study_feasibility.json](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_feasibility.json)

Key fields:
- `decision = insufficient_1m_data_depth`
- `supports_24h_lookback = false`
- `qualified_symbols = []`
- `coverage_ratio = 0.1736`
- `usable_eval_hours_after_lookback = 0.0`

Per symbol:
- `BTC/USDT`: `859 / 3596` observed vs expected `1m` bars, `coverage_ratio = 0.2389`
- `ETH/USDT`: `933 / 3591`, `0.2598`
- `SOL/USDT`: `511 / 3544`, `0.1442`
- `XRP/USDT`: `499 / 3565`, `0.1400`
- `DOGE/USDT`: `301 / 3541`, `0.0850`

Interpretation:
- none of the five symbols can support the plan’s required `24h` trailing reference with a usable evaluation window after lookback
- the current free Coinalyze `1m` data is not merely “thin”; it is structurally insufficient for this study design

---

## 3. Structural Signal Note

Source:
- [2026-05-30_liquidation_shock_event_study_summary.json](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_summary.json)

The response-map pass still contains a useful observation:
- the built dataset shows a **mean-reversion-leaning** directional structure

Examples from the current summary:
- `directional_bias_by_horizon`
  - `5m = 58.7%`
  - `10m = 62.4%`
  - `15m = 60.2%`
- `median_response_bps_by_horizon`
  - `5m = -3.84`
  - `10m = -6.98`
  - `15m = -8.26`

But this signal note is **not actionable** for Phase 2, because the feasibility gate failed. In other words:
- there may be a reversion-shaped response in the current constructed sample
- but the underlying `1m` liquidation dataset is not reliable enough to justify further context bucketing or directional-alpha development

---

## 4. Final Decision

**`INSUFFICIENT_1M_DATA_DEPTH`**

This line does **not** advance to Phase 2 context bucketing.

Why this is the correct governing state:
- the plan explicitly required `1m` data depth and continuity to pass before Phase 2
- the real feasibility rerun with live API access failed that gate
- therefore the study must stop on data sufficiency, even if the provisional response map appears structurally interesting

---

## 5. Next Action

`stop_liquidation_shock_line_under_current_vendor_constraints`

That means:
- do not continue context slicing on this `1m` Coinalyze-based line
- do not treat the current response-map result as a valid strategy promotion signal
- if liquidation research continues later, it must begin with a different data source or a materially different research design that does not require continuous `1m` liquidation history
