import pytest

from src.research.external_signal_shadow.stage1_5b_event_table_normalizer import (
    build_article_event_rows,
    expand_symbol_event_rows,
    normalize_base_asset_symbol,
)


def test_normalize_base_asset_symbol_to_usdt_pair():
    assert normalize_base_asset_symbol("abc") == ("ABC", "ABCUSDT", "USDT")


def test_normalize_rejects_ambiguous_symbol():
    with pytest.raises(ValueError, match="ambiguous|contains '/'"):
        normalize_base_asset_symbol("PEPE/WBTC/USDT")


def test_normalize_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        normalize_base_asset_symbol("")


def test_normalize_rejects_invalid_regex():
    with pytest.raises(ValueError, match="format|regex"):
        normalize_base_asset_symbol("A")  # too short
    with pytest.raises(ValueError, match="format|regex"):
        normalize_base_asset_symbol("A" * 16)  # too long
    with pytest.raises(ValueError, match="format|regex"):
        normalize_base_asset_symbol("ABC$")  # invalid char


def test_normalize_rejects_forbidden_words():
    with pytest.raises(ValueError, match="forbidden"):
        normalize_base_asset_symbol("USDT")


def test_build_article_and_symbol_rows_expand_multi_symbol_event():
    rows = [{
        "event_type_candidate": "exchange_delisting_notice",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "source_capture_method": "semi_auto_collector",
        "source_line": 35,
        "source_name": "binance_official_announcements",
        "source_url": "https://www.binance.com/bapi/x",
        "symbol": ["COS", "HIGH", "MBOX"],
        "time": 1780642807472,
        "title": "Binance Will Delist COS, D, HIGH, MBOX on 2026-06-19",
        "url": "https://www.binance.com/en/support/announcement/x",
    }]

    article_rows = build_article_event_rows(rows, allowed_event_types={"exchange_delisting_notice"})
    symbol_rows = expand_symbol_event_rows(article_rows, source_audit_decisions={
        "exchange_delisting_notice": "source_audit_passed"
    })

    assert len(article_rows) == 1
    assert article_rows[0].symbol_count == 3
    assert len(symbol_rows) == 3
    assert {r.symbol for r in symbol_rows} == {"COSUSDT", "HIGHUSDT", "MBOXUSDT"}
    assert all(r.replay_allowed is False for r in symbol_rows)
    assert all(r.context_labels_allowed is False for r in symbol_rows)
    assert all(r.directional_hypothesis == "undefined" for r in symbol_rows)
    assert all(r.signed_direction is None for r in symbol_rows)
    assert all(r.effective_time_ms is None for r in symbol_rows)
    assert all(r.effective_time_parse_status == "not_parsed_in_stage1_5b" for r in symbol_rows)
    assert all(r.market_pair_existence_verified is False for r in symbol_rows)
    assert all(r.price_history_coverage_verified is False for r in symbol_rows)
    assert all(r.tradability_verified is False for r in symbol_rows)
    for row in symbol_rows:
        assert not hasattr(row, "local_forceorder_context_present")
        assert not hasattr(row, "funding_context_present")
        assert not hasattr(row, "oi_context_present")
        assert not hasattr(row, "btc_regime_context_present")


def test_build_article_rows_rejects_unsupported_event_type():
    rows = [{
        "event_type_candidate": "margin_enablement",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "source_capture_method": "semi_auto_collector",
        "source_line": 7,
        "source_name": "binance_official_announcements",
        "source_url": "https://www.binance.com/bapi/x",
        "symbol": ["ABC"],
        "time": 1780642807472,
        "title": "Binance Adds ABC to Margin",
        "url": "https://www.binance.com/en/support/announcement/y",
    }]

    with pytest.raises(ValueError, match="unsupported_event_type"):
        build_article_event_rows(rows, allowed_event_types={"futures_contract_launch"})
