# Stage 1.4A Derivatives Stress Data Feasibility Audit Review

## 1. Decision Summary
- **Final Outcome:** `stage1_4_data_degraded`
- **Primary Blocker:** `fixture_smoke_only`
- **Research Result Valid:** `INVALID (Fixture or Network Error)`
- **Fixture Smoke Run:** `YES (Smoke Test Only)`

> [!IMPORTANT]
> **本 artifact 是 fixture smoke，不证明真实 derivatives stress data availability。**

## 2. Safety and Scope Boundaries
- **Live Trading Master Switch:** `RISK_LIVE_TRADING_ENABLED` is confirmed `False`.
- **Credentials check:** No private API keys or environment variables were loaded during this execution.
- **Execution scope:** No paper trading, live order placement, or alpha estimation was performed.

## 3. Per-Source Audit Table
| Source | History (Days) | Time Coverage | Field Coverage | Symbol Count | Quality | Proxy Used | Blocker | Usable for 1.4B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Binance Funding Rate (/fapi/v1/fundingRate) | 0.00d | 0.0% | 0.0% | 0 | public_settled_funding_history | No | no_audit_data | No |
| Binance Open Interest (/futures/data/openInterestHist) | 0.00d | 0.0% | 0.0% | 0 | public_history | No | no_audit_data | No |
| Binance Liquidations (Vision Snapshots / Force Orders) | 0.00d | 0.0% | 0.0% | 0 | force_order_archive | No | no_audit_data | No |
| Binance Futures Prices (/fapi/v1/klines) | 0.00d | 0.0% | 0.0% | 0 | futures_klines | No | no_audit_data | No |

## 4. Source Semantics Notes
### 4.1 Funding Rates
- **Status:** Block. Min history of 0.0 days is below the 90d requirement.
- **Notes:** Checked for 8h settlement cadence and publishing lags.

### 4.2 Open Interest
- **Status:** Block. Open Interest blocks full composite replay due to insufficient history or time continuity gaps.
- **Notes:** Continuity checks verify time-series buckets are not missing.

### 4.3 Liquidations
- **Status:** Block. No liquidation audit data was supplied in this run.
- **Notes:** Notional conversion must be verified by sample to unlock full feasibility.
- **Notional Conversion Quality:** `unavailable`

### 4.4 Futures Prices
- **Status:** Block. Price history is below 90d.

## 5. Preview Density Explanation
- **Composite Overlap Windows:** 0
- **Distinct Event Days:** 0
- **Notes:** Preview density represents raw event overlap and is **NOT** a backtest or alpha score.

## 6. Next Action Recommendation
- Continue in **degraded mode** using proxies/archives, or gather longer history before proceeding.
