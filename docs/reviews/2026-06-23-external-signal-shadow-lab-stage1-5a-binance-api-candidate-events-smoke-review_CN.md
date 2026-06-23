# External Signal Shadow Lab Stage 1.5A Source Audit Review

## 结论
- **Overall Decision**: `source_audit_sparse_inconclusive`
- **Research Result Valid**: `True`

## Source Integrity
- Total Events Found: `26`
- Source Integrity Pass Rate: `80.77%`
- Schema Quarantine Count: `5`

## Source Resource Safety
- Forbidden Payload Count: `0`
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
- Timestamp Quality High/Medium Ratio: `100.00%`
- Distribution:
  - `high`: `26`

## Event Type / Magnitude / Symbol Mapping
- Trade Pair Mapping Pass Rate: `100.00%`

## Per-source Decisions
### Source: `binance_official_announcements_like_rows_source`
- **Decision**: `source_audit_sparse_inconclusive`
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
- Unique Event Days: `10`
- Symbols with Events: `26`

## Stop Reasons
- 无 (No stop reasons)

## Allowed Next Action
- **Next Action**: `fix_source_audit_or_stop_source`
- 审计未通过或处于稀疏不确定状态，禁止推进到 Replay 阶段。

<!-- references: dydx unlocks calendar -->