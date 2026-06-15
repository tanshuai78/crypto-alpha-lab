"""
src/research/external_signal_shadow/stage1_4a_liquidation.py
"""

from configs.base import (
    EXTERNAL_SIGNAL_STAGE1_4_CM_TO_UM_SYMBOL_MAP,
)
from research.external_signal_shadow.stage1_4a_coverage import compute_time_coverage


def map_force_order_side_to_liquidation_side(side: str) -> str:
    """
    Maps force order side to liquidation side:
    - SELL -> long_liquidation
    - BUY -> short_liquidation
    """
    if not side:
        return "unknown"
    normalized = str(side).upper()
    if normalized == "SELL":
        return "long_liquidation"
    elif normalized == "BUY":
        return "short_liquidation"
    return "unknown"


def audit_cm_to_um_symbol_mapping(cm_symbols: list[str]) -> dict:
    """
    Audits the symbol mapping from CM to UM.
    """
    mapped_count = 0
    for sym in cm_symbols:
        if sym in EXTERNAL_SIGNAL_STAGE1_4_CM_TO_UM_SYMBOL_MAP:
            mapped_count += 1

    quality = "proxy" if mapped_count > 0 else "missing"
    return {
        "cm_to_um_proxy_used": True,
        "liquidation_symbol_mapping_quality": quality,
        "mapped_count": mapped_count,
        "total_count": len(cm_symbols),
    }


def audit_liquidation_notional_conversion(metadata: dict | None) -> dict:
    """
    Audits the notional conversion quality.
    """
    if not metadata:
        return {
            "notional_conversion_required": True,
            "notional_conversion_quality": "unavailable",
        }

    req = metadata.get("notional_conversion_required", True)
    qual = metadata.get("notional_conversion_quality", "unavailable")
    return {
        "notional_conversion_required": req,
        "notional_conversion_quality": qual,
    }


def _audit_generic_liquidation_rows(
    rows: list[dict],
    expected_symbols: tuple[str, ...],
    source_name: str,
    source_quality: str,
    mapping_quality: str,
    cm_to_um_proxy_used: bool,
    notional_conversion_required: bool,
    notional_conversion_quality: str,
    liquidation_proxy_accepted_for_full_replay: bool = False,
) -> dict:
    """
    Internal helper to perform generic liquidation audit on a list of rows.
    """
    # Filter rows matching expected symbols (after mapping if CM proxy used)
    symbol_rows = []
    for r in rows:
        sym = r.get("symbol")
        if not sym:
            continue
        # If CM proxy is used, map CM symbol to UM symbol
        if cm_to_um_proxy_used:
            sym = EXTERNAL_SIGNAL_STAGE1_4_CM_TO_UM_SYMBOL_MAP.get(sym, sym)

        if sym in expected_symbols:
            symbol_rows.append(r)

    record_count = len(symbol_rows)

    if record_count == 0:
        return {
            "liquidation_source": source_name,
            "liquidation_source_quality": source_quality,
            "liquidation_history_days": 0.0,
            "liquidation_field_coverage_ratio": 0.0,
            "liquidation_time_coverage_ratio": 0.0,
            "liquidation_nonzero_window_count": 0,
            "liquidation_symbol_mapping_quality": mapping_quality,
            "cm_to_um_proxy_used": cm_to_um_proxy_used,
            "liquidation_proxy_accepted_for_full_replay": liquidation_proxy_accepted_for_full_replay,
            "notional_conversion_required": notional_conversion_required,
            "notional_conversion_quality": notional_conversion_quality,
        }

    valid_field_count = 0
    timestamps = []

    for r in symbol_rows:
        side = r.get("side")
        price = r.get("price")

        qty = None
        for k in ("qty", "origQty", "amount", "last_filled_qty"):
            if r.get(k) is not None:
                qty = r[k]
                break

        time_val = None
        for k in ("time", "timestamp", "event_time"):
            if r.get(k) is not None:
                time_val = r[k]
                break

        if side is not None and price is not None and qty is not None and time_val is not None:
            valid_field_count += 1
            timestamps.append(int(time_val))

    field_coverage_ratio = float(valid_field_count / record_count)

    # Use 24h expected interval (86,400,000 ms) for daily continuity of liquidation events
    interval_ms = 24 * 60 * 60 * 1000
    coverage = compute_time_coverage(timestamps, interval_ms)

    # Count of unique hourly windows with at least one liquidation event
    nonzero_window_count = coverage["actual_unique_bucket_count"]

    return {
        "liquidation_source": source_name,
        "liquidation_source_quality": source_quality,
        "liquidation_history_days": coverage["history_days"],
        "liquidation_field_coverage_ratio": field_coverage_ratio,
        "liquidation_time_coverage_ratio": min(1.0, coverage["time_coverage_ratio"]),
        "liquidation_nonzero_window_count": nonzero_window_count,
        "liquidation_symbol_mapping_quality": mapping_quality,
        "cm_to_um_proxy_used": cm_to_um_proxy_used,
        "liquidation_proxy_accepted_for_full_replay": liquidation_proxy_accepted_for_full_replay,
        "notional_conversion_required": notional_conversion_required,
        "notional_conversion_quality": notional_conversion_quality,
    }


def audit_force_order_archive_rows(
    rows: list[dict], expected_symbols: tuple[str, ...]
) -> dict:
    """
    Audits local force order archive rows.
    """
    return _audit_generic_liquidation_rows(
        rows=rows,
        expected_symbols=expected_symbols,
        source_name="local_force_order_archive",
        source_quality="force_order_archive",
        mapping_quality="exact",
        cm_to_um_proxy_used=False,
        notional_conversion_required=False,
        notional_conversion_quality="verified_by_sample",
        liquidation_proxy_accepted_for_full_replay=True,  # Exact local archive is accepted
    )


def audit_liquidation_snapshot_rows(
    rows: list[dict],
    expected_symbols: tuple[str, ...],
    liquidation_proxy_accepted_for_full_replay: bool = False,
) -> dict:
    """
    Audits Binance Vision CM liquidation snapshot rows (acting as a proxy).
    """
    # For CM proxy: symbol mapping quality is 'proxy', notional conversion is required,
    # and default quality is estimated/metadata_present_unverified unless specified.
    return _audit_generic_liquidation_rows(
        rows=rows,
        expected_symbols=expected_symbols,
        source_name="binance_vision_cm_liquidation_snapshot",
        source_quality="cm_liquidation_snapshot_proxy",
        mapping_quality="proxy",
        cm_to_um_proxy_used=True,
        notional_conversion_required=True,
        notional_conversion_quality="estimated",
        liquidation_proxy_accepted_for_full_replay=liquidation_proxy_accepted_for_full_replay,
    )


def audit_binance_vision_manifest_entries(
    entries: list[dict],
    expected_symbols: tuple[str, ...],
    liquidation_proxy_accepted_for_full_replay: bool = False,
) -> dict:
    """
    Audits manifest entries for Binance Vision liquidation snapshots.
    """
    available_count = 0
    for entry in entries:
        symbol = entry.get("symbol")
        mapped_symbol = EXTERNAL_SIGNAL_STAGE1_4_CM_TO_UM_SYMBOL_MAP.get(symbol, symbol)
        if mapped_symbol in expected_symbols and entry.get("manifest_available", True):
            available_count += 1

    return audit_liquidation_manifest_only(available_count=available_count)


def audit_liquidation_manifest_only(available_count: int) -> dict:
    """
    Audits manifest-only availability for Binance Vision Coin-M liquidation snapshots.
    No event rows are created; reports date-range manifest availability only.
    """
    return {
        "liquidation_source": "binance_vision_cm_liquidation_snapshot_manifest",
        "liquidation_source_quality": "cm_liquidation_snapshot_manifest_only",
        "liquidation_manifest_available_count": available_count,
        "liquidation_history_days": 0.0,
        "liquidation_field_coverage_ratio": 0.0,
        "liquidation_time_coverage_ratio": 0.0,
        "liquidation_nonzero_window_count": 0,
        "cm_to_um_proxy_used": True,
        "liquidation_proxy_accepted_for_full_replay": False,
        "notional_conversion_required": True,
        "notional_conversion_quality": "unavailable",
        "usable": False,
    }
