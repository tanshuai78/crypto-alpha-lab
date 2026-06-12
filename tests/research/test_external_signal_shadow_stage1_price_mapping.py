

def test_canonical_asset_id_formats_correctly():
    from src.research.external_signal_shadow.price_mapping import canonical_asset_id

    assert canonical_asset_id("cex", "BTC/USDT", None) == "cex:BTCUSDT"
    assert canonical_asset_id("cex", "eth-usdt", None) == "cex:ETHUSDT"
    assert canonical_asset_id("bsc", None, "0xABC123") == "bsc:0xabc123"
    assert canonical_asset_id("cex", None, None) is None


def test_resolve_price_mapping_finds_active_mapping(tmp_path):
    from src.research.external_signal_shadow.price_mapping import (
        load_price_map,
        resolve_price_mapping,
    )

    map_path = tmp_path / "map.json"
    map_path.write_text(
        '{"cex:btcusdt": {"price_series_id": "binance_spot_btc_usdt", "venue": "binance", "timeframe": "5m", "mapping_type": "exact", "active": true}}'
    )
    price_map = load_price_map(str(map_path))

    mapping = resolve_price_mapping(price_map, chain="cex", symbol="btc-usdt", token_address=None)
    assert mapping is not None
    assert mapping.price_series_id == "binance_spot_btc_usdt"


def test_resolve_price_mapping_returns_none_if_inactive_or_missing(tmp_path):
    from src.research.external_signal_shadow.price_mapping import (
        load_price_map,
        resolve_price_mapping,
    )

    map_path = tmp_path / "map.json"
    map_path.write_text(
        '{"cex:btcusdt": {"price_series_id": "binance_spot_btc_usdt", "venue": "binance", "timeframe": "5m", "mapping_type": "exact", "active": false}}'
    )
    price_map = load_price_map(str(map_path))

    assert resolve_price_mapping(price_map, chain="cex", symbol="btc-usdt", token_address=None) is None
    assert resolve_price_mapping(price_map, chain="cex", symbol="eth-usdt", token_address=None) is None
