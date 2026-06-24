# Stage 1.5C.1 Price Coverage Expansion Audit Review

> **Audit Context:** This report is automatically generated to review price coverage status for Stage 1.5B events.
> **Scope:** Stage 1.5C.1 is a **coverage-only** study. No alpha claims, trading decisions, or model executions are supported.

## 1. Decision & Status
- **Final Decision:** `stage1_5c1_price_coverage_ready_for_1_5c_rerun`
- **Blockers Active:** `None`

## 2. Futures Coverage Funnel
- **Stage 1.5B Input Events:** `194` (Unique Symbols: `191`)
- **Futures Coverage Pass Events:** `63` (Calendar Days: `46`, Symbols: `61`)
- **Not Matured Events:** `1`
- **Spot Proxy Available Events (Report-Only):** `0`

## 3. Safety Boundaries
- **api_key_used:** `False`
- **private_endpoint_used:** `False`
- **paper_trading_allowed:** `False`
- **live_trading_allowed:** `False`
- **alpha_interpretation_allowed:** `False`

## 4. Execution Guidance & Next Actions
1. **If Decision is `stage1_5c1_price_coverage_ready_for_1_5c_rerun`**:
   - The expanded price history archive is complete and dense enough.
   - You are permitted to rerun Stage 1.5C using the generated `external_catalyst_events_futures_coverage_pass.jsonl` table.
2. **If Decision is `stage1_5c1_price_coverage_sparse_inconclusive` or `stage1_5c1_price_coverage_failed`**:
   - Do NOT run Stage 1.5C replay. Stop and investigate event source gaps.
3. **Spot Proxy Disclaimer**:
   - The spot proxy archive is report-only. Spot price proxy must not be used as futures execution price.

*Report generated at: 2026-06-24 08:11:23 UTC*
