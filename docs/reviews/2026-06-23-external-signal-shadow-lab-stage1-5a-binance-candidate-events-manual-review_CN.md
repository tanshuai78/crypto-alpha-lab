# Stage 1.5A Binance Candidate Events Manual Review

## 结论
- Raw candidate rows: `236`
- Reviewed high-confidence rows: `94`
- Rejected rows: `142`
- High-confidence output: `data/external_signal_shadow/stage1_5a/manual_sources/binance_candidate_events_reviewed_high_confidence.jsonl`
- Rejected output: `data/external_signal_shadow/stage1_5a/manual_sources/binance_candidate_events_review_rejected.jsonl`

本次整理采用保守规则：优先保留 primary spot delisting 与明确 USDⓈ/USDT/USDC crypto perpetual launch；排除 bStocks/TradFi/Pre-IPO、Loan/VIP/Collateral、fiat pair、generic new pairs、symbol extraction 不可信的行。

## Raw Event Type Counts
- `futures_contract_launch`: `79`
- `exchange_delisting_notice`: `64`
- `margin_enablement`: `58`
- `trading_pair_addition_for_existing_liquid_asset`: `33`
- `major_exchange_status_event`: `2`

## Kept Event Type Counts
- `futures_contract_launch`: `71`
- `exchange_delisting_notice`: `23`

## Top Reject Reasons
- `margin_event_not_clean_single_asset_enablement`: `57`
- `low_confidence_symbol_extraction`: `54`
- `delisting_title_not_primary_spot_notice`: `34`
- `spot_pair_addition_branch_excluded_first_pass`: `33`
- `fiat_pair_or_fiat_promo`: `29`
- `loan_or_collateral_only`: `23`
- `not_spot_exchange_delisting`: `17`
- `generic_new_pairs`: `14`
- `websocket_or_infra`: `9`
- `non_crypto_or_generic_futures_launch`: `8`
- `bstocks_or_tradfi_or_preipo`: `7`
- `multiple_or_quarterly_generic_contract`: `2`
- `unsupported_first_pass_event_type`: `2`
- `futures_launch_without_usd_stable_pair`: `1`

## Kept Coverage
- Unique event days: `81`
- Date range UTC: `2023-11-27` to `2026-06-23`

## Next Action
- Run Stage 1.5A source audit with `--source-file-mode real` on the high-confidence JSONL.
- If source audit remains sparse, increase Binance API pages or manually add older primary delisting/futures-launch notices.
