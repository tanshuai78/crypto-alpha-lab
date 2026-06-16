"""
tests/research/external_signal_shadow/test_stage1_4a2_vendor_sample_audit.py
"""
import gzip

from research.external_signal_shadow.stage1_4a2_vendor import audit_vendor_sample_file


def test_audit_vendor_sample_jsonl_detects_required_fields(tmp_path) -> None:
    path = tmp_path / "sample.jsonl"
    path.write_text(
        '\n'.join([
            '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"long_liquidation_usd":1000,"short_liquidation_usd":0}',
            '{"symbol":"ETHUSDT","exchange":"binance_usdm","timestamp":1704153600000,"long_liquidation_usd":0,"short_liquidation_usd":2000}',
        ]),
        encoding="utf-8",
    )
    result = audit_vendor_sample_file(path)
    assert result["row_count"] == 2
    assert result["symbol_field_available"] is True
    assert result["timestamp_field_available"] is True
    assert result["notional_usd_available"] is True
    assert result["side_available"] is True
    assert result["symbols_verified"] == ["BTCUSDT", "ETHUSDT"]


def test_audit_vendor_sample_csv_detects_missing_side(tmp_path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text(
        "symbol,exchange,timestamp,notional_usd\nBTCUSDT,binance_usdm,1704067200000,1000\n",
        encoding="utf-8",
    )
    result = audit_vendor_sample_file(path)
    assert result["row_count"] == 1
    assert result["side_available"] is False


def test_audit_vendor_sample_file_computes_history_days(tmp_path) -> None:
    path = tmp_path / "sample.jsonl"
    path.write_text(
        '\n'.join([
            '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"long_liquidation_usd":1000,"short_liquidation_usd":0}',
            '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1712016000000,"long_liquidation_usd":500,"short_liquidation_usd":0}',
        ]),
        encoding="utf-8",
    )
    result = audit_vendor_sample_file(path)
    assert result["history_days"] >= 90.0


def test_audit_vendor_sample_file_rejects_daily_only_for_intraday(tmp_path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text(
        "symbol,exchange,timestamp,long_liquidation_usd,short_liquidation_usd\n"
        "BTCUSDT,binance_usdm,1704067200000,1000,0\n"
        "BTCUSDT,binance_usdm,1704153600000,0,2000\n",
        encoding="utf-8",
    )
    result = audit_vendor_sample_file(path)
    assert result["timestamp_resolution_ms"] >= 86_400_000
    assert result["intraday_usable"] is False


def test_audit_vendor_sample_file_supports_jsonl_gz(tmp_path) -> None:
    path = tmp_path / "sample.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(
            '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"long_liquidation_usd":1000,"short_liquidation_usd":0}\n'
        )
    result = audit_vendor_sample_file(path)
    assert result["row_count"] == 1
