# Liquidation Shock 1m Event Study Review

**Review Date:** 2026-05-30  
**Data Range:** 4.04 Days  
**Decision:** `RETIRE_LIQUIDATION_SHOCK_EVENT_STUDY`  
**Details:** Failed checks: no adjacent horizons passed criteria (passed: [], bias: {5: 0.4131054131054131, 10: 0.3757062146892655, 15: 0.3983050847457627}, mm_bias: {5: 0.4, 10: 0.3943089430894309, 15: 0.37209302325581395}, median_bps: {5: -3.84, 10: -6.98, 15: -8.26})

---

## 1. Executive Summary

- **Total Deduplicated Shock Events:** 358
- **Event Frequency (per 24h):** 88.62
- **Success Criteria Checks:** Failed

### Symbol Distribution:
- **BTC/USDT:** 87 events (24.3%)
- **DOGE/USDT:** 41 events (11.5%)
- **ETH/USDT:** 83 events (23.2%)
- **SOL/USDT:** 73 events (20.4%)
- **XRP/USDT:** 74 events (20.7%)

---

## 2. Response Analysis by Horizon

| Horizon | Raw Up Count | Raw Down Count | Raw Flat Count | Directional Bias | Min-Move Up | Min-Move Down | Min-Move Flat | Min-Move Bias | Median Dir Return (bps) |
|---|---|---|---|---|---|---|---|---|---|
| 5m | 145 | 206 | 7 | 41.3% | 84 | 126 | 148 | 40.0% | -3.84 bps |
| 10m | 133 | 221 | 4 | 37.6% | 97 | 149 | 112 | 39.4% | -6.98 bps |
| 15m | 141 | 213 | 4 | 39.8% | 96 | 162 | 100 | 37.2% | -8.26 bps |

---

## 3. Return Distribution Stats

| Horizon | Min Return (bps) | Max Return (bps) | Mean Return (bps) | Median Return (bps) |
|---|---|---|---|---|
| 5m | -64.94 bps | +85.69 bps | +3.21 bps | +0.77 bps |
| 10m | -84.55 bps | +97.41 bps | +1.85 bps | +4.52 bps |
| 15m | -87.37 bps | +142.08 bps | +1.77 bps | +3.03 bps |

---

## 4. Failed Checks Details

- [x] **FAIL**: no adjacent horizons passed criteria (passed: [], bias: {5: 0.4131054131054131, 10: 0.3757062146892655, 15: 0.3983050847457627}, mm_bias: {5: 0.4, 10: 0.3943089430894309, 15: 0.37209302325581395}, median_bps: {5: -3.84, 10: -6.98, 15: -8.26})

---

## 5. Conclusion & Action Item

Based on the quantitative criteria, the event study has determined that:

**RETIRE (No Tradeable Edge)**: The directional signal structure failed due to: Failed checks: no adjacent horizons passed criteria (passed: [], bias: {5: 0.4131054131054131, 10: 0.3757062146892655, 15: 0.3983050847457627}, mm_bias: {5: 0.4, 10: 0.3943089430894309, 15: 0.37209302325581395}, median_bps: {5: -3.84, 10: -6.98, 15: -8.26}). We should retire liquidation directional alpha research as planned.
