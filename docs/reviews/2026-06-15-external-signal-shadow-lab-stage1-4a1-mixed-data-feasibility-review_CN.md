# Stage 1.4A Derivatives Stress Data Feasibility Audit Review

## 1. Decision Summary
- **Final Outcome:** `stage1_4_data_degraded`
- **Primary Blocker:** `liquidation_history_insufficient`
- **Research Result Valid:** `VALID`
- **Fixture Smoke Run:** `NO (Real Data Run)`

## 2. Safety and Scope Boundaries
- **Live Trading Master Switch:** `RISK_LIVE_TRADING_ENABLED` is confirmed `False`.
- **Credentials check:** No private API keys or environment variables were loaded during this execution.
- **Execution scope:** No paper trading, live order placement, or alpha estimation was performed.

## 3. Per-Source Audit Table
| Source | History (Days) | Time Coverage | Field Coverage | Symbol Count | Quality | Proxy Used | Blocker | Usable for 1.4B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Binance Funding Rate (/fapi/v1/fundingRate) | 179.67d | 100.0% | 100.0% | 5 | public_settled_funding_history | No | None | Yes |
| Binance Open Interest (/futures/data/openInterestHist) | 178.00d | 100.0% | 100.0% | 5 | local_archive | No | None | Yes |
| Binance Liquidations (Vision Snapshots / Force Orders) | 12.31d | 100.0% | 100.0% | 5 | force_order_archive | No | liquidation_history_insufficient | No |
| Binance Futures Prices (/fapi/v1/klines) | 179.99d | 100.0% | 100.0% | 5 | futures_klines | No | None | Yes |

## 4. Per-Symbol Blocker Table
| Symbol | Funding Days | OI Days | Price Days | Liquidation Days | Blockers | Usable |
| --- | --- | --- | --- | --- | --- | --- |
| BTCUSDT | 179.67d | 178.00d | 179.99d | 14.27d | liquidation_insufficient | No |
| DOGEUSDT | 179.67d | 178.00d | 179.99d | 14.25d | liquidation_insufficient | No |
| ETHUSDT | 179.67d | 178.00d | 179.99d | 14.27d | liquidation_insufficient | No |
| SOLUSDT | 179.67d | 178.00d | 179.99d | 12.32d | liquidation_insufficient | No |
| XRPUSDT | 179.67d | 178.00d | 179.99d | 12.31d | liquidation_insufficient | No |

## 5. Source Semantics Notes
### 5.1 Funding Rates
- **Status:** Pass. Min history of 179.7 days satisfies the 90d requirement.
- **Notes:** Checked for 8h settlement cadence and publishing lags.

### 5.2 Open Interest
- **Status:** Pass. Open interest satisfies 90d history and 90% time continuity.
- **Notes:** Continuity checks verify time-series buckets are not missing.

### 5.3 Liquidations
- **Status:** Block. Min liquidation history is 12.3 days, below the 90d requirement.
- **Notes:** Notional conversion must be verified by sample to unlock full feasibility.
- **Notional Conversion Quality:** `verified_by_sample`

### 5.4 Futures Prices
- **Status:** Pass. Min price history is 180.0 days.

## 6. Preview Density Explanation
- **Composite Overlap Windows:** 71643
- **Distinct Event Days:** 14
- **Notes:** Preview density represents raw event overlap and is **NOT** a backtest or alpha score.

## 7. Next Action Recommendation
- Continue in **degraded mode** using proxies/archives, or gather longer history before proceeding.
