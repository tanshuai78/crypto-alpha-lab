from __future__ import annotations

from typing import Any

from configs.base import (
    LIQUIDATION_SHOCK_DIRECTION_MIN_MOVE_BPS,
    LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES,
)
from src.research.liquidation_shock_event_study.event_contract import (
    LiquidationShockEvent,
)


def build_response_map(
    event: LiquidationShockEvent,
    price_map: dict[int, dict[str, Any]],
    min_move_bps: float | None = None,
) -> dict[str, Any] | None:
    if min_move_bps is None:
        min_move_bps = LIQUIDATION_SHOCK_DIRECTION_MIN_MOVE_BPS

    shock_ms = event.shock_bar_start_ms
    entry_ms = shock_ms + 60_000

    # Get entry price (open price of minute M+1)
    entry_row = price_map.get(entry_ms)
    if not entry_row:
        return None

    entry_price = float(entry_row.get("open_price") or 0.0)
    if entry_price <= 0.0:
        return None

    # Calculate exits
    exit_prices: dict[int, float] = {}
    exit_timestamps_ms: dict[int, int] = {}

    for horizon in LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES:
        exit_ms = shock_ms + horizon * 60_000
        exit_row = price_map.get(exit_ms)
        if not exit_row:
            return None

        exit_price = float(exit_row.get("close_price") or 0.0)
        if exit_price <= 0.0:
            return None

        exit_prices[horizon] = exit_price
        exit_timestamps_ms[horizon] = exit_ms

    bps_changes: dict[int, float] = {}
    directional_bps: dict[int, float] = {}
    sign_directions: dict[int, int] = {}
    min_move_directions: dict[int, int] = {}

    direction = event.expected_price_direction

    for horizon in LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES:
        exit_price = exit_prices[horizon]
        # Raw bps change: (exit - entry) / entry * 10000
        raw_change_bps = ((exit_price - entry_price) / entry_price) * 10000.0
        bps_changes[horizon] = raw_change_bps

        # Directional bps change: positive means price moved in expected direction
        if direction == "up":
            dir_change_bps = raw_change_bps
        else:
            dir_change_bps = -raw_change_bps
        directional_bps[horizon] = dir_change_bps

        # Sign-only direction label
        if dir_change_bps > 0.0:
            sign_dir = 1
        elif dir_change_bps < 0.0:
            sign_dir = -1
        else:
            sign_dir = 0
        sign_directions[horizon] = sign_dir

        # Min-move filtered direction label
        if dir_change_bps >= min_move_bps:
            min_move_dir = 1
        elif dir_change_bps <= -min_move_bps:
            min_move_dir = -1
        else:
            min_move_dir = 0
        min_move_directions[horizon] = min_move_dir

    return {
        "symbol": event.symbol,
        "shock_bar_start_ms": shock_ms,
        "expected_price_direction": direction,
        "entry_timestamp_ms": entry_ms,
        "entry_price": entry_price,
        "exit_timestamps_ms": exit_timestamps_ms,
        "exit_prices": exit_prices,
        "bps_changes": bps_changes,
        "directional_bps": directional_bps,
        "sign_directions": sign_directions,
        "min_move_directions": min_move_directions,
    }
