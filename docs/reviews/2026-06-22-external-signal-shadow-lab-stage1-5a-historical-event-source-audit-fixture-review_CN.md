# External Signal Shadow Lab Stage 1.5A Source Audit Review

## 结论
- **Overall Decision**: `source_audit_failed`
- **Research Result Valid**: `False`

> [!WARNING]
> This is a local fixture run (fixture_run = true). The results are not valid for production research.

## Source Integrity
- Total Events Found: `0`
- Source Integrity Pass Rate: `0.00%`
- Schema Quarantine Count: `0`

## Source Resource Safety
- Forbidden Payload Count: `1`
- Payload Too Large Count: `0`
- JSON Depth Exceeded Count: `0`
- Disallowed Domain Count: `0`
- Schema Parse Error Count: `0`

## Raw Cache / Network Evidence
- Raw Cache Written: `False`
- Raw Cache Path: ``
- network_result_not_deterministic: `False`
- collector_received_at_ms: `None`

## Timestamp / Available-at Quality
- Timestamp Source Disagreement Count: `0`
- Timestamp Quality High/Medium Ratio: `0.00%`
- Distribution:

## Event Type / Magnitude / Symbol Mapping
- Trade Pair Mapping Pass Rate: `0.00%`

## Per-source Decisions
### Source: `generic_json_announcement_rows_source`
- **Decision**: `source_audit_failed`
- Recommended Event Types for Stage 1.5B: `[]`

## Per-event-type Decisions
- `exchange_delisting_notice`: `source_audit_sparse_inconclusive`
- `futures_contract_launch`: `source_audit_sparse_inconclusive`
- `margin_enablement`: `source_audit_sparse_inconclusive`
- `trading_pair_removal`: `source_audit_sparse_inconclusive`
- `trading_pair_addition_for_existing_liquid_asset`: `source_audit_sparse_inconclusive`
- `major_exchange_status_event`: `source_audit_sparse_inconclusive`
- `major_unlock_event`: `observation_only`
- `large_scheduled_token_emission`: `observation_only`
- `new_coin_listing`: `observation_only`
- `whale_deposit`: `observation_only`

## Density / Coverage
- Unique Event Days: `0`
- Symbols with Events: `0`

## Stop Reasons
- **VETO/STOP**: Forbidden payload detected
- **VETO/STOP**: Global safety gates or density gates failed

## Allowed Next Action
- **Next Action**: `fix_source_audit_or_stop_source`
- 审计未通过或处于稀疏不确定状态，禁止推进到 Replay 阶段。

<!-- references: dydx unlocks calendar -->