"""
src/research/external_signal_shadow/stage1_4a_orchestrator.py
"""

from configs.base import EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_OI_INTERVAL_MS
from research.external_signal_shadow.stage1_4a_funding import audit_funding_history_rows
from research.external_signal_shadow.stage1_4a_liquidation import (
    audit_force_order_archive_rows,
    audit_liquidation_manifest_only,
    audit_liquidation_snapshot_rows,
)
from research.external_signal_shadow.stage1_4a_oi import audit_open_interest_history_rows
from research.external_signal_shadow.stage1_4a_price import audit_price_source_rows
from research.external_signal_shadow.stage1_4a_summary import evaluate_feasibility_summary


def run_stage1_4a_feasibility_audit(
    symbol_funding_rows: dict[str, list[dict]],
    symbol_oi_rows: dict[str, list[dict]],
    symbol_liquidation_rows: dict[str, list[dict]],
    symbol_price_rows: dict[str, list[dict]],
    preview_counts: dict,
    global_metadata: dict,
    liquidation_proxy_accepted_for_full_replay: bool = False,
) -> dict:
    """
    Orchestrates the feasibility audit by running source-specific audits for each symbol,
    aggregating results, and calling the decision engine.
    """
    symbol_audits = {}

    # Identify all symbols that have any data input
    all_symbols = set(symbol_funding_rows.keys()) | set(symbol_oi_rows.keys()) | \
                  set(symbol_liquidation_rows.keys()) | set(symbol_price_rows.keys())

    for sym in all_symbols:
        funding_rows = symbol_funding_rows.get(sym, [])
        oi_rows = symbol_oi_rows.get(sym, [])
        liq_rows = symbol_liquidation_rows.get(sym, [])
        price_rows = symbol_price_rows.get(sym, [])

        # Funding audit
        funding_audit = audit_funding_history_rows(funding_rows, sym)

        # OI audit
        oi_audit = audit_open_interest_history_rows(
            oi_rows, sym, EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_OI_INTERVAL_MS
        )

        # Liquidation audit: check if exact force order archive should be used
        use_force_order_archive = (
            global_metadata.get("liquidation_source_type") == "force_order_archive"
            or global_metadata.get("local_force_order_archive_found", False)
        )
        if use_force_order_archive:
            liq_audit = audit_force_order_archive_rows(liq_rows, (sym,))
        else:
            is_manifest_only = (
                global_metadata.get("network_mode") == "live_public_readonly"
                and not use_force_order_archive
            )
            if is_manifest_only:
                avail_days_map = global_metadata.get("liquidation_manifest_available_days_by_symbol", {})
                avail_count = avail_days_map.get(sym, 0)
                liq_audit = audit_liquidation_manifest_only(avail_count)
            else:
                liq_audit = audit_liquidation_snapshot_rows(
                    liq_rows, (sym,), liquidation_proxy_accepted_for_full_replay
                )


        # Price audit
        price_source_kind = global_metadata.get("price_source_kind", "futures_klines")
        price_audit = audit_price_source_rows(price_rows, sym, price_source_kind)

        symbol_audits[sym] = {
            "funding": funding_audit,
            "oi": oi_audit,
            "liquidation": liq_audit,
            "price": price_audit,
        }

    # Run decision summary engine
    summary_result = evaluate_feasibility_summary(
        symbol_audits, preview_counts, global_metadata
    )

    # Attach individual audits for downstream review script
    summary_result["symbol_audits"] = symbol_audits

    return summary_result
