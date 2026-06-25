from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
    classify_event_type,
    dedupe_events,
    extract_futures_launch_symbols,
    normalize_live_event,
    parse_binance_announcement_payload,
)


def test_extract_symbols_from_binance_futures_launch_title():
    title = "Binance Futures Will Launch USDⓈ-Margined ZESTUSDT and BTWUSDT Perpetual Contracts"
    assert extract_futures_launch_symbols(title) == ["ZESTUSDT", "BTWUSDT"]


def test_classify_futures_launch_only():
    assert classify_event_type("Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract") == "futures_contract_launch"
    assert classify_event_type("Binance Will Delist ABC") == "ignored_event_type"


def test_normalize_event_available_at_uses_detected_when_source_time_low_confidence():
    row = normalize_live_event(
        raw={"title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract", "code": "abc"},
        source_parent_url="https://www.binance.com/en/support/announcement",
        detected_at_ms=10_000,
        source_published_at_ms=1_000,
        source_published_at_ms_confidence="low",
    )
    assert row["available_at_ms"] == 10_000
    assert row["historical_delay_comparison_allowed"] is False


def test_dedupe_uses_article_id_or_url_not_timestamp_only():
    a = {"source_article_id": "abc", "source_detail_url_normalized": "u1", "source_published_at_ms": 1, "stable_event_key": "k1"}
    b = {"source_article_id": "abc", "source_detail_url_normalized": "u1", "source_published_at_ms": 2, "stable_event_key": "k2"}
    rows = dedupe_events([a, b])
    assert len(rows) == 1


def test_parser_empty_articles_is_valid_zero_events():
    result = parse_binance_announcement_payload({"data": {"catalogs": [{"articles": []}]}})
    assert result["events"] == []
    assert result["source_format_drift"] is False
    assert result["schema_parse_error"] is False


def test_parser_marks_source_format_drift_when_catalogs_missing():
    result = parse_binance_announcement_payload({"data": {"items": []}})
    assert result["events"] == []
    assert result["source_format_drift"] is True
    assert result["source_format_drift_count"] == 1


def test_parser_marks_schema_parse_error_when_articles_not_list():
    result = parse_binance_announcement_payload({"data": {"catalogs": [{"articles": {"bad": "shape"}}]}})
    assert result["events"] == []
    assert result["schema_parse_error"] is True
