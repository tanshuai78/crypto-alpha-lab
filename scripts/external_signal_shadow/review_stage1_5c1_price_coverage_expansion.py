import argparse
import json
import os
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1.5C.1: Price Coverage Expansion Review Generator")
    parser.add_argument("--summary", required=True, help="Path to expansion summary JSON")
    parser.add_argument("--output-review", required=True, help="Path to write Chinese Markdown review")

    args = parser.parse_args()

    if not os.path.exists(args.summary):
        print(f"Error: Summary not found at {args.summary}")
        return 1

    with open(args.summary, "r", encoding="utf-8") as f:
        s = json.load(f)

    decision = s.get("decision", "unknown")
    total_events = s.get("stage1_5b_symbol_events", 0)
    pass_events = s.get("futures_coverage_pass_event_count", 0)
    pass_days = s.get("futures_coverage_pass_event_days", 0)
    pass_symbols = s.get("futures_coverage_pass_symbols", 0)
    spot_proxy_count = s.get("spot_proxy_available_event_count", 0)
    not_matured = s.get("not_matured_event_count", 0)
    unique_symbols = s.get("unique_symbol_count", 0)
    blockers = s.get("blockers", [])

    blockers_str = ", ".join(blockers) if blockers else "None"

    markdown = f"""# Stage 1.5C.1 Price Coverage Expansion Audit Review

> **Audit Context:** This report is automatically generated to review price coverage status for Stage 1.5B events.
> **Scope:** Stage 1.5C.1 is a **coverage-only** study. No alpha claims, trading decisions, or model executions are supported.

## 1. Decision & Status
- **Final Decision:** `{decision}`
- **Blockers Active:** `{blockers_str}`

## 2. Futures Coverage Funnel
- **Stage 1.5B Input Events:** `{total_events}` (Unique Symbols: `{unique_symbols}`)
- **Futures Coverage Pass Events:** `{pass_events}` (Calendar Days: `{pass_days}`, Symbols: `{pass_symbols}`)
- **Not Matured Events:** `{not_matured}`
- **Spot Proxy Available Events (Report-Only):** `{spot_proxy_count}`

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

*Report generated at: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}*
"""

    p = Path(args.output_review)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Audit review document written to {args.output_review}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
