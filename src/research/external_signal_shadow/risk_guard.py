from typing import Any

from configs import base
from src.research.external_signal_shadow.models import ExternalSignalEvent, RiskDecision

SUPPORTED_ONCHAIN_CHAINS = {"ethereum", "solana", "bsc", "base", "tron"}


def _num(metadata: dict[str, Any], key: str) -> float | None:
    value = metadata.get(key)
    if value is None:
        return None
    return float(value)


def _direction(direction_hint: str) -> str:
    if direction_hint in {"long", "short"}:
        return direction_hint
    if direction_hint == "both":
        return "both"
    if direction_hint in {"unknown", "avoid"}:
        return "observe_only"
    return "observe_only"


def evaluate_event_risk(event: ExternalSignalEvent) -> RiskDecision:
    reasons: list[str] = []
    metadata = event.metadata

    if event.chain == "cex":
        reasons.extend(_cex_reject_reasons(metadata))
    elif event.chain in SUPPORTED_ONCHAIN_CHAINS:
        reasons.extend(_token_reject_reasons(event, metadata))
    else:
        reasons.append("unsupported_chain")

    if event.data_quality != "ok":
        reasons.append(f"data_quality_{event.data_quality}")

    hard_reasons = [reason for reason in reasons if not reason.startswith("data_quality_")]
    if hard_reasons:
        return RiskDecision(
            event_id=event.event_id,
            risk_decision="reject",
            reject_reasons=tuple(reasons),
            allowed_shadow_direction="none",
        )
    if reasons:
        return RiskDecision(
            event_id=event.event_id,
            risk_decision="quarantine",
            reject_reasons=tuple(reasons),
            allowed_shadow_direction="none",
        )
    return RiskDecision(
        event_id=event.event_id,
        risk_decision="accept_for_shadow",
        reject_reasons=(),
        allowed_shadow_direction=_direction(event.direction_hint),
    )


def _cex_reject_reasons(metadata: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    spread_bps = _num(metadata, "spread_bps")
    depth_10bps_usd = _num(metadata, "depth_10bps_usd")
    orderbook_coverage = _num(metadata, "orderbook_coverage")
    price_coverage = _num(metadata, "price_coverage")

    if spread_bps is None:
        reasons.append("missing_spread_bps")
    elif spread_bps > base.EXTERNAL_SIGNAL_SHADOW_CEX_MAX_SPREAD_BPS:
        reasons.append("wide_spread")

    if depth_10bps_usd is None:
        reasons.append("missing_depth_10bps_usd")
    elif depth_10bps_usd < base.EXTERNAL_SIGNAL_SHADOW_CEX_MIN_DEPTH_10BPS_USD:
        reasons.append("low_depth_10bps")

    if orderbook_coverage is None:
        reasons.append("missing_orderbook_coverage")
    elif orderbook_coverage < base.EXTERNAL_SIGNAL_SHADOW_MIN_ORDERBOOK_COVERAGE:
        reasons.append("low_orderbook_coverage")

    if price_coverage is None:
        reasons.append("missing_price_coverage")
    elif price_coverage < base.EXTERNAL_SIGNAL_SHADOW_MIN_PRICE_COVERAGE:
        reasons.append("low_price_coverage")

    return reasons


def _token_reject_reasons(
    event: ExternalSignalEvent, metadata: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []

    if metadata.get("honeypot_risk") is True:
        reasons.append("honeypot_risk")
    if str(metadata.get("rug_pull_risk", "")).lower() == "high":
        reasons.append("high_rug_pull_risk")

    liquidity_usd = event.liquidity_usd or _num(metadata, "liquidity_usd")
    if liquidity_usd is None or liquidity_usd < base.EXTERNAL_SIGNAL_SHADOW_MIN_LIQUIDITY_USD:
        reasons.append("low_liquidity")

    sell_tax_pct = _num(metadata, "sell_tax_pct")
    if sell_tax_pct is not None and sell_tax_pct > base.EXTERNAL_SIGNAL_SHADOW_MAX_SELL_TAX_PCT:
        reasons.append("high_sell_tax")

    top10_holder_share = _num(metadata, "top10_holder_share")
    if (
        top10_holder_share is not None
        and top10_holder_share > base.EXTERNAL_SIGNAL_SHADOW_MAX_TOP10_HOLDER_SHARE
    ):
        reasons.append("high_top10_holder_share")

    smart_money_exit_rate = _num(metadata, "smart_money_exit_rate")
    if (
        smart_money_exit_rate is not None
        and smart_money_exit_rate > base.EXTERNAL_SIGNAL_SHADOW_MAX_SMART_MONEY_EXIT_RATE
    ):
        reasons.append("high_smart_money_exit_rate")

    return reasons
