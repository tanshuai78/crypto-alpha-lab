import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger


def compute_depth_metrics(orderbook: Dict[str, Any], notional_usdt: float = 500.0) -> Dict[str, Any]:
    """
    Compute bid/ask spreads, depths, and estimated slippage from orderbook depth snapshot.
    """
    bids = orderbook.get("bids", [])
    asks = orderbook.get("asks", [])

    if not bids or not asks:
        return {
            "spread_bps": 0.0,
            "best_bid": 0.0,
            "best_ask": 0.0,
            "mid_price": 0.0,
            "top_0_5pct_ask_depth_usdt": 0.0,
            "top_1pct_ask_depth_usdt": 0.0,
            "top_0_5pct_bid_depth_usdt": 0.0,
            "top_1pct_bid_depth_usdt": 0.0,
            "buy_depth_sufficient_for_500usdt": False,
            "sell_depth_sufficient_for_500usdt": False,
            "slippage_estimate_bps_for_500usdt_buy": 0.0,
            "slippage_estimate_bps_for_500usdt_sell": 0.0,
            "depth_status": "empty_orderbook"
        }

    try:
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
    except Exception as e:
        logger.error(f"Failed to parse best bid/ask: {e}")
        return {
            "spread_bps": 0.0,
            "best_bid": 0.0,
            "best_ask": 0.0,
            "mid_price": 0.0,
            "top_0_5pct_ask_depth_usdt": 0.0,
            "top_1pct_ask_depth_usdt": 0.0,
            "top_0_5pct_bid_depth_usdt": 0.0,
            "top_1pct_bid_depth_usdt": 0.0,
            "buy_depth_sufficient_for_500usdt": False,
            "sell_depth_sufficient_for_500usdt": False,
            "slippage_estimate_bps_for_500usdt_buy": 0.0,
            "slippage_estimate_bps_for_500usdt_sell": 0.0,
            "depth_status": "parse_error"
        }

    mid_price = (best_bid + best_ask) / 2.0
    spread_bps = (best_ask - best_bid) / mid_price * 10_000.0

    # Calculate ask depths within 0.5% and 1% of best ask
    top_0_5pct_ask_depth_usdt = 0.0
    top_1pct_ask_depth_usdt = 0.0
    for price_str, qty_str in asks:
        try:
            p = float(price_str)
            q = float(qty_str)
            notional = p * q
            if p <= best_ask * 1.005:
                top_0_5pct_ask_depth_usdt += notional
            if p <= best_ask * 1.01:
                top_1pct_ask_depth_usdt += notional
        except Exception:
            continue

    # Calculate bid depths within 0.5% and 1% of best bid
    top_0_5pct_bid_depth_usdt = 0.0
    top_1pct_bid_depth_usdt = 0.0
    for price_str, qty_str in bids:
        try:
            p = float(price_str)
            q = float(qty_str)
            notional = p * q
            if p >= best_bid * 0.995:
                top_0_5pct_bid_depth_usdt += notional
            if p >= best_bid * 0.99:
                top_1pct_bid_depth_usdt += notional
        except Exception:
            continue

    # Walk asks for buy slippage
    buy_depth_sufficient_for_500usdt = False
    slippage_estimate_bps_for_500usdt_buy = 0.0
    accum_notional = 0.0
    accum_qty = 0.0

    for price_str, qty_str in asks:
        try:
            p = float(price_str)
            q = float(qty_str)
        except Exception:
            continue

        needed = notional_usdt - accum_notional
        notional_avail = p * q
        if notional_avail >= needed:
            # Fill the rest
            filled_qty = needed / p
            accum_qty += filled_qty
            accum_notional = notional_usdt
            buy_depth_sufficient_for_500usdt = True
            break
        else:
            accum_notional += notional_avail
            accum_qty += q

    if buy_depth_sufficient_for_500usdt and accum_qty > 0:
        avg_price = notional_usdt / accum_qty
        slippage_estimate_bps_for_500usdt_buy = (avg_price / best_ask - 1.0) * 10_000.0

    # Walk bids for sell slippage
    sell_depth_sufficient_for_500usdt = False
    slippage_estimate_bps_for_500usdt_sell = 0.0
    accum_notional_sell = 0.0
    accum_qty_sell = 0.0

    for price_str, qty_str in bids:
        try:
            p = float(price_str)
            q = float(qty_str)
        except Exception:
            continue

        needed = notional_usdt - accum_notional_sell
        notional_avail = p * q
        if notional_avail >= needed:
            filled_qty = needed / p
            accum_qty_sell += filled_qty
            accum_notional_sell = notional_usdt
            sell_depth_sufficient_for_500usdt = True
            break
        else:
            accum_notional_sell += notional_avail
            accum_qty_sell += q

    if sell_depth_sufficient_for_500usdt and accum_qty_sell > 0:
        avg_price_sell = notional_usdt / accum_qty_sell
        slippage_estimate_bps_for_500usdt_sell = (1.0 - avg_price_sell / best_bid) * 10_000.0

    depth_status = "depth_computed"
    if not buy_depth_sufficient_for_500usdt:
        depth_status = "insufficient_ask_depth"
    elif not sell_depth_sufficient_for_500usdt:
        depth_status = "insufficient_bid_depth"

    return {
        "spread_bps": spread_bps,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid_price,
        "top_0_5pct_ask_depth_usdt": top_0_5pct_ask_depth_usdt,
        "top_1pct_ask_depth_usdt": top_1pct_ask_depth_usdt,
        "top_0_5pct_bid_depth_usdt": top_0_5pct_bid_depth_usdt,
        "top_1pct_bid_depth_usdt": top_1pct_bid_depth_usdt,
        "buy_depth_sufficient_for_500usdt": buy_depth_sufficient_for_500usdt,
        "sell_depth_sufficient_for_500usdt": sell_depth_sufficient_for_500usdt,
        "slippage_estimate_bps_for_500usdt_buy": slippage_estimate_bps_for_500usdt_buy,
        "slippage_estimate_bps_for_500usdt_sell": slippage_estimate_bps_for_500usdt_sell,
        "depth_status": depth_status
    }


def normalize_orderbook_symbol(symbol: str) -> str:
    """Normalize local CEX orderbook symbols to compact Binance-style symbols."""
    if not symbol:
        return ""
    normalized = str(symbol).upper().strip()
    if ":" in normalized:
        normalized = normalized.split(":", 1)[0]
    normalized = normalized.replace("/", "")
    return normalized


def _historical_depth_files(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(
        file_path
        for file_path in path.glob("*.jsonl")
        if "_funding_" not in file_path.name
    )


def _symbol_from_depth_filename(file_path: Path) -> str:
    parts = file_path.name.split("_")
    if len(parts) < 3:
        return ""
    return normalize_orderbook_symbol(parts[1])


def _candidate_key(candidate: Dict[str, Any]) -> tuple:
    return (
        candidate.get("symbol_event_id"),
        candidate.get("signed_mode"),
        candidate.get("entry_delay_hours"),
        candidate.get("filter_group"),
    )


def load_historical_depth_snapshots(
    historical_depth_path: Any,
    candidate_rows: List[Dict[str, Any]],
    match_window_ms: int,
    notional_usdt: float = 500.0,
) -> Dict[str, Any]:
    """
    Load local historical orderbook JSONL rows and match snapshots to candidates.

    A depth archive is considered available only when at least one snapshot matches
    a candidate by normalized symbol and timestamp window.
    """
    path = Path(historical_depth_path)
    files = _historical_depth_files(path)
    candidates_by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    candidate_symbols = set()
    for candidate in candidate_rows:
        symbol = normalize_orderbook_symbol(candidate.get("symbol", ""))
        if not symbol:
            continue
        candidate_symbols.add(symbol)
        candidates_by_symbol.setdefault(symbol, []).append(candidate)

    orderbook_symbols = set()
    filename_symbols = {_symbol_from_depth_filename(file_path) for file_path in files}
    filename_symbols.discard("")
    orderbook_symbols.update(filename_symbols)
    candidate_symbol_overlap_count = len(candidate_symbols & orderbook_symbols)
    if files and candidate_symbols and filename_symbols and candidate_symbol_overlap_count == 0:
        return {
            "depth_rows": [],
            "coverage": {
                "historical_depth_input_path": str(path),
                "historical_depth_file_count": len(files),
                "historical_depth_parsed_row_count": 0,
                "historical_depth_malformed_row_count": 0,
                "candidate_symbol_count": len(candidate_symbols),
                "orderbook_symbol_count": len(orderbook_symbols),
                "candidate_symbol_overlap_count": 0,
                "matched_snapshot_count": 0,
                "matched_candidate_event_count": 0,
                "matched_symbol_count": 0,
                "historical_orderbook_depth_available": False,
                "coverage_reject_reason": "historical_orderbook_no_candidate_symbol_overlap",
            },
        }

    parsed_row_count = 0
    malformed_row_count = 0
    best_match_by_candidate: Dict[tuple, tuple[int, Dict[str, Any], Dict[str, Any]]] = {}

    for file_path in files:
        try:
            handle = file_path.open("r", encoding="utf-8")
        except OSError:
            continue
        with handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    snapshot_ts = int(row["timestamp"])
                except Exception:
                    malformed_row_count += 1
                    continue

                parsed_row_count += 1
                symbol = normalize_orderbook_symbol(row.get("symbol", ""))
                if not symbol:
                    continue
                orderbook_symbols.add(symbol)

                for candidate in candidates_by_symbol.get(symbol, []):
                    entry_time_ms = candidate.get("entry_time_ms")
                    if entry_time_ms is None:
                        continue
                    delta_ms = abs(snapshot_ts - int(entry_time_ms))
                    if delta_ms > match_window_ms:
                        continue
                    key = _candidate_key(candidate)
                    previous = best_match_by_candidate.get(key)
                    if previous is None or delta_ms < previous[0]:
                        best_match_by_candidate[key] = (delta_ms, row, candidate)

    depth_rows = []
    matched_symbol_event_ids = set()
    matched_symbols = set()
    for delta_ms, snapshot, candidate in best_match_by_candidate.values():
        metrics = compute_depth_metrics(snapshot, notional_usdt=notional_usdt)
        symbol = normalize_orderbook_symbol(snapshot.get("symbol", candidate.get("symbol", "")))
        matched_symbol_event_ids.add(candidate.get("symbol_event_id"))
        matched_symbols.add(symbol)
        depth_rows.append({
            "symbol": symbol,
            "symbol_event_id": candidate.get("symbol_event_id"),
            "event_type": candidate.get("event_type"),
            "signed_mode": candidate.get("signed_mode"),
            "entry_delay_hours": candidate.get("entry_delay_hours"),
            "filter_group": candidate.get("filter_group"),
            "entry_time_ms": candidate.get("entry_time_ms"),
            "historical_depth_timestamp_ms": int(snapshot["timestamp"]),
            "historical_depth_delta_ms": delta_ms,
            "historical_depth_exchange": snapshot.get("exchange"),
            "depth_fetched_at_ms": None,
            "exchange_event_time_ms": int(snapshot["timestamp"]),
            "exchange_transaction_time_ms": None,
            "depth_snapshot_age_ms": delta_ms,
            "depth_timestamp_quality": "historical_snapshot_time",
            **metrics,
        })

    candidate_symbol_overlap_count = len(candidate_symbols & orderbook_symbols)
    matched_snapshot_count = len(depth_rows)
    coverage = {
        "historical_depth_input_path": str(path),
        "historical_depth_file_count": len(files),
        "historical_depth_parsed_row_count": parsed_row_count,
        "historical_depth_malformed_row_count": malformed_row_count,
        "candidate_symbol_count": len(candidate_symbols),
        "orderbook_symbol_count": len(orderbook_symbols),
        "candidate_symbol_overlap_count": candidate_symbol_overlap_count,
        "matched_snapshot_count": matched_snapshot_count,
        "matched_candidate_event_count": len([x for x in matched_symbol_event_ids if x]),
        "matched_symbol_count": len(matched_symbols),
        "historical_orderbook_depth_available": matched_snapshot_count > 0,
    }
    if candidate_symbol_overlap_count == 0:
        coverage["coverage_reject_reason"] = "historical_orderbook_no_candidate_symbol_overlap"
    elif matched_snapshot_count == 0:
        coverage["coverage_reject_reason"] = "historical_orderbook_no_entry_time_match"

    return {
        "depth_rows": depth_rows,
        "coverage": coverage,
    }


def normalize_depth_timestamp_fields(orderbook: Dict[str, Any], fetched_at_ms: int) -> Dict[str, Any]:
    """
    Extract event/transaction time from orderbook and compute snapshot age.
    """
    # "E" and "T" are typical event/transaction timestamps in Binance WebSockets stream depth responses.
    # Binance REST /fapi/v1/depth does not usually contain them.
    e_time = orderbook.get("E")
    t_time = orderbook.get("T")

    exchange_event_time_ms = int(e_time) if e_time is not None else None
    exchange_transaction_time_ms = int(t_time) if t_time is not None else None

    depth_snapshot_age_ms = None
    if exchange_transaction_time_ms is not None:
        depth_snapshot_age_ms = fetched_at_ms - exchange_transaction_time_ms
        depth_timestamp_quality = "exchange_time"
    else:
        depth_timestamp_quality = "local_fetch_time_only"

    return {
        "depth_fetched_at_ms": fetched_at_ms,
        "exchange_event_time_ms": exchange_event_time_ms,
        "exchange_transaction_time_ms": exchange_transaction_time_ms,
        "depth_snapshot_age_ms": depth_snapshot_age_ms,
        "depth_timestamp_quality": depth_timestamp_quality
    }
