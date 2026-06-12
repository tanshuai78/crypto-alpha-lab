import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FORBIDDEN_KEYS = {
    "api_key",
    "private_key",
    "order_id",
    "signed_tx",
    "wallet_seed",
    "swap_payload",
    "mnemonic",
    "seed_phrase",
    "wallet_private_key",
    "tx_payload",
}


def reject_forbidden_keys_recursive(payload: object) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden executable field: {key}")
            reject_forbidden_keys_recursive(value)
    elif isinstance(payload, list | tuple):
        for item in payload:
            reject_forbidden_keys_recursive(item)


def normalize_symbol(symbol: str | None) -> str | None:
    if symbol is None:
        return None
    normalized = symbol.replace("/", "").replace("-", "").replace("_", "").upper()
    return normalized or None


@dataclass(frozen=True)
class ExternalSignalEvent:
    event_id: str
    source: str
    source_skill: str
    event_type: str
    chain: str
    symbol: str | None
    token_address: str | None
    event_time_ms: int
    direction_hint: str
    raw_score: float = 0.0
    notional_usd: float = 0.0
    liquidity_usd: float = 0.0
    risk_flags: tuple[str, ...] = ()
    data_quality: str = "ok"
    shadow_only: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.shadow_only:
            raise ValueError("shadow_only must be True for Stage 0 events")
        if not isinstance(self.event_time_ms, int):
            raise ValueError("event_time_ms must be an integer Unix ms timestamp")
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "chain", self.chain.lower())
        object.__setattr__(self, "direction_hint", self.direction_hint.lower())
        object.__setattr__(self, "data_quality", self.data_quality.lower())
        object.__setattr__(self, "risk_flags", tuple(self.risk_flags))
        reject_forbidden_keys_recursive(
            {
                "metadata": self.metadata,
                "risk_flags": self.risk_flags,
            }
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExternalSignalEvent":
        reject_forbidden_keys_recursive(payload)
        data = dict(payload)
        data["risk_flags"] = tuple(data.get("risk_flags", ()))
        data.setdefault("metadata", {})
        return cls(**data)


@dataclass(frozen=True)
class PriceBar:
    symbol: str
    bar_start_ms: int
    bar_end_ms: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float

    def __post_init__(self) -> None:
        if not isinstance(self.bar_start_ms, int):
            raise ValueError("bar_start_ms must be an integer Unix ms timestamp")
        if not isinstance(self.bar_end_ms, int):
            raise ValueError("bar_end_ms must be an integer Unix ms timestamp")
        if self.bar_end_ms <= self.bar_start_ms:
            raise ValueError("bar_end_ms must be greater than bar_start_ms")
        prices = (self.open_price, self.high_price, self.low_price, self.close_price)
        if any(price <= 0 for price in prices):
            raise ValueError("all OHLC prices must be positive")
        if self.high_price < self.low_price:
            raise ValueError("high_price must be greater than or equal to low_price")
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PriceBar":
        return cls(**payload)


@dataclass(frozen=True)
class RiskDecision:
    event_id: str
    risk_decision: str
    reject_reasons: tuple[str, ...] = ()
    allowed_shadow_direction: str = "none"


@dataclass(frozen=True)
class CusumResult:
    event_id: str
    status: str
    trigger_time_ms: int | None = None
    direction: str | None = None
    threshold_bps: float | None = None
    rolling_vol_bps: float | None = None
    threshold_source: str | None = None


@dataclass(frozen=True)
class ShadowOrder:
    shadow_order_id: str
    event_id: str
    symbol: str | None
    token_address: str | None
    direction: str
    entry_time_ms: int | None
    entry_price: float | None
    take_profit_price: float | None
    stop_loss_price: float | None
    vertical_barrier_time_ms: int | None
    cost_round_trip_bps: float
    status: str
    exit_time_ms: int | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    gross_return_bps: float | None = None
    net_return_bps: float | None = None
    max_adverse_excursion_bps: float | None = None
    max_favorable_excursion_bps: float | None = None


@dataclass(frozen=True)
class ReplayBranchSummary:
    branch_name: str
    shadow_order_count: int
    win_count: int
    loss_count: int
    timeout_count: int


def _load_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_events_jsonl(path: str) -> list[ExternalSignalEvent]:
    return [ExternalSignalEvent.from_dict(row) for row in _load_jsonl(path)]


def load_price_bars_jsonl(path: str) -> list[PriceBar]:
    return [PriceBar.from_dict(row) for row in _load_jsonl(path)]


def price_bars_by_symbol(bars: list[PriceBar]) -> dict[str, list[PriceBar]]:
    grouped: dict[str, list[PriceBar]] = {}
    for bar in bars:
        grouped.setdefault(bar.symbol, []).append(bar)
    return {
        symbol: sorted(symbol_bars, key=lambda item: item.bar_start_ms)
        for symbol, symbol_bars in grouped.items()
    }
