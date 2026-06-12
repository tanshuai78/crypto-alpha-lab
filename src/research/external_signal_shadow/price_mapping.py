import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PriceMapping:
    price_series_id: str
    venue: str
    timeframe: str
    mapping_type: str
    active: bool


def load_price_map(path: str) -> dict[str, PriceMapping]:
    payload = json.loads(Path(path).read_text())
    return {key.lower(): PriceMapping(**value) for key, value in payload.items()}


def _normalize_symbol(symbol: str | None) -> str | None:
    if symbol is None:
        return None
    normalized = symbol.replace("/", "").replace("-", "").replace("_", "").upper()
    return normalized or None


def canonical_asset_id(chain: str, symbol: str | None, token_address: str | None) -> str | None:
    normalized_chain = chain.lower()
    if normalized_chain == "cex":
        normalized_symbol = _normalize_symbol(symbol)
        return f"cex:{normalized_symbol}" if normalized_symbol else None
    if token_address:
        return f"{normalized_chain}:{token_address.lower()}"
    return None


def resolve_price_mapping(
    price_map: dict[str, PriceMapping],
    *,
    chain: str,
    symbol: str | None,
    token_address: str | None,
) -> PriceMapping | None:
    key = canonical_asset_id(chain, symbol, token_address)
    if key is None:
        return None
    mapping = price_map.get(key.lower())
    if mapping is None or not mapping.active:
        return None
    return mapping
