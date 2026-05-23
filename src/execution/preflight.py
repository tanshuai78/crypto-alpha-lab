from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import TradeIntent

PREFLIGHT_BLOCKER_PREFIXES = {
    "input_invalid",
    "missing_dependency",
    "venue_capability",
}


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    reason: str = ""
    blocker_code: str = ""
    diagnostics: dict[str, Any] | None = None


def _result(
    ok: bool,
    reason: str,
    *,
    blocker_code: str = "",
    diagnostics: dict[str, Any] | None = None,
) -> PreflightResult:
    return PreflightResult(
        ok=ok,
        reason=reason,
        blocker_code=blocker_code,
        diagnostics=diagnostics or {},
    )


def preflight_check(intent: TradeIntent, exchanges: dict) -> PreflightResult:
    if intent.target_base_qty <= 0:
        return _result(
            False,
            "target_base_qty must be positive",
            blocker_code="input_invalid/target_qty",
            diagnostics={"field": "target_base_qty", "value": intent.target_base_qty},
        )

    for leg in (intent.leg_a, intent.leg_b):
        exchange = exchanges.get(leg.exchange)
        if exchange is None:
            return _result(
                False,
                f"missing exchange client for {leg.exchange}",
                blocker_code="missing_dependency/exchange_client",
                diagnostics={"exchange": leg.exchange, "client_order_id": leg.client_order_id},
            )

        if leg.post_only and not getattr(exchange, "supports_post_only", True):
            return _result(
                False,
                f"post-only is not supported by {leg.exchange}",
                blocker_code="venue_capability/post_only_unsupported",
                diagnostics={"exchange": leg.exchange, "client_order_id": leg.client_order_id},
            )

        if leg.reduce_only and not getattr(exchange, "supports_reduce_only", True):
            return _result(
                False,
                f"reduce-only is not supported by {leg.exchange}",
                blocker_code="venue_capability/reduce_only_unsupported",
                diagnostics={"exchange": leg.exchange, "client_order_id": leg.client_order_id},
            )

        if leg.type == "limit" and (leg.price is None or leg.price <= 0):
            return _result(
                False,
                f"limit leg missing valid price: {leg.client_order_id}",
                blocker_code="input_invalid/limit_price",
                diagnostics={"client_order_id": leg.client_order_id, "price": leg.price},
            )

    return _result(True, "ok")
