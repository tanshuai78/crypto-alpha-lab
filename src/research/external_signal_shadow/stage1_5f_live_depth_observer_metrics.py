from configs import base
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import DepthSnapshot


def _parse_levels(levels_raw: list) -> list[tuple[float, float]]:
    parsed = []
    if not levels_raw:
        return parsed
    for item in levels_raw:
        try:
            p = float(item[0])
            q = float(item[1])
            if p > 0 and q > 0:
                parsed.append((p, q))
        except Exception:
            pass
    return parsed


def compute_mid_price(best_bid: float, best_ask: float) -> float:
    return (best_bid + best_ask) / 2.0


def compute_spread_bps(best_bid: float, best_ask: float) -> float:
    if best_bid <= 0:
        return 0.0
    return (best_ask / best_bid - 1.0) * 10000.0


def compute_top_notional(levels: list[tuple[float, float]], n: int) -> float:
    return sum(p * q for p, q in levels[:n])


def walk_book_for_quote_notional(levels: list[tuple[float, float]], notional_usdt: float) -> float | None:
    total_qty = 0.0
    remaining = notional_usdt
    for price, qty in levels:
        level_notional = price * qty
        if remaining <= level_notional:
            needed_qty = remaining / price
            total_qty += needed_qty
            remaining = 0.0
            break
        else:
            total_qty += qty
            remaining -= level_notional

    if remaining > 1e-6:
        return None
    if total_qty <= 0:
        return None
    return notional_usdt / total_qty


def parse_depth_payload(symbol: str, payload: dict, fetched_at_ms: int, event_symbol_id: str = "") -> DepthSnapshot:
    bids_raw = payload.get("bids", [])
    asks_raw = payload.get("asks", [])
    exchange_time_ms = payload.get("T")

    bids = _parse_levels(bids_raw)
    asks = _parse_levels(asks_raw)

    if not bids or not asks:
        return DepthSnapshot(
            event_symbol_id=event_symbol_id,
            symbol=symbol,
            fetched_at_ms=fetched_at_ms,
            exchange_time_ms=exchange_time_ms,
            best_bid=None,
            best_ask=None,
            spread_bps=None,
            top_bid_depth_usdt=0.0,
            top_ask_depth_usdt=0.0,
            buy_slippage_bps=None,
            sell_slippage_bps=None,
            slippage_status="invalid_depth",
            depth_status="invalid",
        )

    best_bid = bids[0][0]
    best_ask = asks[0][0]

    if best_bid >= best_ask or best_bid <= 0 or best_ask <= 0:
        return DepthSnapshot(
            event_symbol_id=event_symbol_id,
            symbol=symbol,
            fetched_at_ms=fetched_at_ms,
            exchange_time_ms=exchange_time_ms,
            best_bid=best_bid,
            best_ask=best_ask,
            spread_bps=None,
            top_bid_depth_usdt=0.0,
            top_ask_depth_usdt=0.0,
            buy_slippage_bps=None,
            sell_slippage_bps=None,
            slippage_status="invalid_depth",
            depth_status="invalid",
        )

    mid_price = compute_mid_price(best_bid, best_ask)
    spread_bps = compute_spread_bps(best_bid, best_ask)

    top_bid_depth_usdt = compute_top_notional(bids, 20)
    top_ask_depth_usdt = compute_top_notional(asks, 20)

    notional_usdt = base.EXTERNAL_SIGNAL_STAGE1_5F_SLIPPAGE_NOTIONAL_USDT

    buy_vwap = walk_book_for_quote_notional(asks, notional_usdt)
    sell_vwap = walk_book_for_quote_notional(bids, notional_usdt)

    buy_slippage_bps = None
    sell_slippage_bps = None
    slippage_status = "ok"

    if buy_vwap is None or sell_vwap is None:
        slippage_status = "insufficient_depth"
    else:
        buy_slippage_bps = (buy_vwap / mid_price - 1.0) * 10000.0
        sell_slippage_bps = (1.0 - sell_vwap / mid_price) * 10000.0

    return DepthSnapshot(
        event_symbol_id=event_symbol_id,
        symbol=symbol,
        fetched_at_ms=fetched_at_ms,
        exchange_time_ms=exchange_time_ms,
        best_bid=best_bid,
        best_ask=best_ask,
        spread_bps=spread_bps,
        top_bid_depth_usdt=top_bid_depth_usdt,
        top_ask_depth_usdt=top_ask_depth_usdt,
        buy_slippage_bps=buy_slippage_bps,
        sell_slippage_bps=sell_slippage_bps,
        slippage_status=slippage_status,
        depth_status="healthy",
    )
