from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
    classify_event_type,
    dedupe_events,
    derive_symbol_candidates_from_base_assets_in_launch_context,
    extract_futures_launch_base_assets,
    extract_futures_launch_symbols,
    extract_symbols_from_detail_payload,
    normalize_live_event,
    parse_binance_announcement_payload,
    extract_symbol_candidates_from_detail_payload,
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


def test_normalize_event_adds_symbol_extraction_diagnostics_for_title_symbols():
    row = normalize_live_event(
        raw={"title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract", "code": "abc"},
        source_parent_url="https://www.binance.com/en/support/announcement",
        detected_at_ms=10_000,
        source_published_at_ms=1_000,
        source_published_at_ms_confidence="medium",
    )

    assert row["symbols"] == ("ABCUSDT",)
    assert row["symbol_extraction_source"] == "title"
    assert row["detail_fetch_attempted"] is False
    assert row["detail_fetch_status"] == "not_needed"
    assert row["symbol_parse_failed_reason"] is None
    assert row["symbol_parse_status"] == "parsed"
    assert row["parser_version"] == "stage1_5d_symbol_extraction_v2"
    assert row["symbol_extraction_version"] == 2


def test_normalize_event_adds_terminal_failed_diagnostics_when_no_symbols_without_detail():
    row = normalize_live_event(
        raw={"title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts", "code": "tradfi"},
        source_parent_url="https://www.binance.com/en/support/announcement",
        detected_at_ms=10_000,
        source_published_at_ms=1_000,
        source_published_at_ms_confidence="medium",
    )

    assert row["symbols"] == ()
    assert row["symbol_extraction_source"] == "none"
    assert row["detail_fetch_attempted"] is False
    assert row["detail_fetch_status"] == "not_needed"
    assert row["symbol_parse_failed_reason"] == "symbol_missing_no_detail_attempted"
    assert row["symbol_parse_status"] == "terminal_failed"


def test_extract_symbols_from_multiple_tradfi_detail_text():
    detail = "Contracts: AAPLUSDT, MSFTUSDT and NVDAUSDT USDⓈ-Margined Perpetual Contracts"
    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["AAPLUSDT", "MSFTUSDT", "NVDAUSDT"]


def test_extract_symbols_from_nested_detail_payload():
    detail = {
        "data": {
            "body": [
                {"type": "table", "rows": [["AMDUSDT"], ["QCOMUSDT"], ["USARUSDT"]]},
                {"text": "Ignore BTC, include only futures pairs"},
            ]
        }
    }
    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["AMDUSDT", "QCOMUSDT", "USARUSDT"]


def test_detail_extraction_preserves_order_dedupes_and_caps():
    detail = "AAAUSDT BBBUSDT AAAUSDT CCCUSDT DDDUSDT"
    assert extract_symbols_from_detail_payload(detail, max_symbols=3) == ["AAAUSDT", "BBBUSDT", "CCCUSDT"]


def test_detail_extraction_does_not_match_standalone_usdt():
    detail = "The contract is margined and settled in USDT. No concrete symbol appears here."
    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == []


def test_normalize_event_uses_detail_symbols_override():
    row = normalize_live_event(
        raw={"title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts", "code": "tradfi"},
        source_parent_url="https://www.binance.com/en/support/announcement",
        detected_at_ms=10_000,
        source_published_at_ms=1_000,
        source_published_at_ms_confidence="medium",
        symbols_override=["AMDUSDT", "QCOMUSDT"],
        extraction_metadata={
            "symbol_extraction_source": "detail",
            "detail_fetch_attempted": True,
            "detail_fetch_status": "success",
            "symbol_parse_failed_reason": None,
            "symbol_parse_status": "parsed",
        },
    )

    assert row["symbols"] == ("AMDUSDT", "QCOMUSDT")
    assert row["base_assets"] == ("AMD", "QCOM")
    assert row["symbol_extraction_source"] == "detail"
    assert row["symbol_parse_status"] == "parsed"
    assert row["stable_event_key"] == "binance_tradfi_MULTI"
    assert len(row["event_id"]) == 64


def test_multi_symbol_detail_event_id_is_stable_across_symbol_order():
    raw = {"title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts", "code": "tradfi"}
    kwargs = {
        "raw": raw,
        "source_parent_url": "https://www.binance.com/en/support/announcement",
        "detected_at_ms": 10_000,
        "source_published_at_ms": 1_000,
        "source_published_at_ms_confidence": "medium",
        "extraction_metadata": {
            "symbol_extraction_source": "detail",
            "detail_fetch_attempted": True,
            "detail_fetch_status": "success",
            "symbol_parse_failed_reason": None,
            "symbol_parse_status": "parsed",
        },
    }
    normalize_live_event(symbols_override=["AMDUSDT", "QCOMUSDT", "USARUSDT"], **kwargs)
    normalize_live_event(symbols_override=["USARUSDT", "AMDUSDT", "QCOMUSDT"], **kwargs)




def test_extract_base_assets_from_usds_margined_launch_title():
    title = "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)"

    assert extract_futures_launch_base_assets(title) == ["BTCU", "ETHU"]


def test_base_asset_fallback_builds_unvalidated_usdt_candidates_in_usds_margined_launch_context():
    title = "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)"

    result = derive_symbol_candidates_from_base_assets_in_launch_context(title, max_symbols=30)

    assert result["symbols"] == ["BTCUUSDT", "ETHUUSDT"]
    assert result["symbol_extraction_source"] == "title_base_asset_derived"
    assert result["symbol_derivation_method"] == "base_asset_plus_quote"
    assert result["quote_derivation_source"] == "explicit_usdt_context"
    assert result["symbol_validation_status"] == "unverified"


def test_base_asset_fallback_does_not_derive_from_non_launch_or_risk_text():
    title = "Update on the Collateral Ratio Under Portfolio Margin and the Leverage & Margin Tiers of USDⓈ-M Perpetual Contracts"

    assert derive_symbol_candidates_from_base_assets_in_launch_context(title, max_symbols=30)["symbols"] == []


def test_base_asset_fallback_accepts_usds_margined_ascii_variant():
    title = "Binance Futures Will Launch USDS-Margined BTCU and ETHU Perpetual Contracts"

    assert derive_symbol_candidates_from_base_assets_in_launch_context(title, max_symbols=30)["symbols"] == ["BTCUUSDT", "ETHUUSDT"]


def test_base_asset_fallback_accepts_short_usd_m_variants_in_title_context():
    titles = [
        "Binance Futures Will Launch USD-M BTCU and ETHU Perpetual Contracts",
        "Binance Futures Will Launch USDS-M BTCU and ETHU Perpetual Contracts",
        "Binance Futures Will Launch USDⓈ-M BTCU and ETHU Perpetual Contracts",
    ]

    for title in titles:
        assert derive_symbol_candidates_from_base_assets_in_launch_context(title, max_symbols=30)["symbols"] == [
            "BTCUUSDT",
            "ETHUUSDT",
        ]


def test_base_asset_fallback_is_case_insensitive_for_launch_context():
    title = "Binance futures will launch usds-margined BTCU and ETHU perpetual contracts"

    assert derive_symbol_candidates_from_base_assets_in_launch_context(title, max_symbols=30)["symbols"] == ["BTCUUSDT", "ETHUUSDT"]


def test_detail_base_asset_fallback_derives_symbols_when_detail_has_base_assets_only():
    detail = {
        "data": {
            "body": "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts."
        }
    }

    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["BTCU", "ETHU"]


def test_detail_prefers_full_symbols_over_base_asset_fallback():
    detail = "Binance Futures will launch USDⓈ-Margined BTCUUSDT and ETHUUSDT Perpetual Contracts."

    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["BTCUUSDT", "ETHUUSDT"]


def test_base_asset_fallback_ignores_tokens_outside_launch_sentence_window():
    detail = """
    Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts.
    Risk Warning: PORTFOLIO MARGIN TIER SETTLEMENT ASSET LEVERAGE COLLATERAL RATIO.
    """

    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["BTCU", "ETHU"]



def test_base_asset_fallback_ignores_table_labels_launch_time_settlement_asset():
    detail = """
    Launch Time: 2026-07-01
    Underlying Asset: BTCU and ETHU
    Settlement Asset: USDT
    Margin Tier: Portfolio Margin update
    """

    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == []


def test_detail_extracts_u_settled_contract_symbols_from_table_text():
    detail = """
    Binance Futures will launch the following perpetual contract(s) as below:
    2026-07-01 09:00 (UTC): BTCU Perpetual Contract with up to 100x leverage
    2026-07-01 10:00 (UTC): ETHU Perpetual Contract with up to 100x leverage
    USDⓈ-M Perpetual Contract
    BTCU
    ETHU
    Settlement Asset
    U (United Stables)
    U (United Stables)
    """

    result = extract_symbol_candidates_from_detail_payload(detail, max_symbols=30, title="Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)")

    assert result["symbols"] == ["BTCU", "ETHU"]
    assert result["symbol_extraction_source"] == "detail_contract_symbol"
    assert result["symbol_derivation_method"] == "none"
    assert result["symbol_validation_status"] == "requires_exchange_info_validation"
    assert result["symbol_launch_times_ms"]["BTCU"] == 1782896400000
    assert result["symbol_launch_times_ms"]["ETHU"] == 1782900000000


def test_detail_contract_symbol_path_prefers_btcu_over_btcuusdt_derivation():
    detail = "USDⓈ-M Perpetual Contract BTCU ETHU Settlement Asset U U"
    title = "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)"

    result = extract_symbol_candidates_from_detail_payload(detail, max_symbols=30, title=title)

    assert result["symbols"] == ["BTCU", "ETHU"]
    assert "BTCUUSDT" not in result["symbols"]
    assert "ETHUUSDT" not in result["symbols"]


def test_detail_contract_symbol_candidate_does_not_collect_table_labels():
    detail = """
    USDⓈ-M Perpetual Contract
    BTCU
    ETHU
    Launch Time
    Underlying Asset
    Settlement Asset
    Minimum Notional Value
    Capped Funding Rate
    """

    result = extract_symbol_candidates_from_detail_payload(detail, max_symbols=30, title="Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts")

    assert result["symbols"] == ["BTCU", "ETHU"]


def test_detail_extracts_july_2_tradfi_usdt_symbols_from_body_text():
    detail_text = """
    Binance Futures will launch the following perpetual contract(s) as below:
    2026-07-02 09:15 (UTC): STRCUSDT Perpetual Contract
    2026-07-02 09:20 (UTC): CATUSDT Perpetual Contract
    2026-07-02 09:25 (UTC): TXNUSDT Perpetual Contract
    2026-07-02 09:30 (UTC): FLEXUSDT Perpetual Contract
    2026-07-02 09:35 (UTC): TERUSDT Perpetual Contract
    2026-07-02 09:40 (UTC): TTWOUSDT Perpetual Contract
    2026-07-02 09:45 (UTC): KSTRUSDT Perpetual Contract
    2026-07-02 09:50 (UTC): BSPUSDT Perpetual Contract
    """
    result = extract_symbol_candidates_from_detail_payload(
        detail_text,
        max_symbols=30,
        title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
    )

    assert result["symbol_extraction_source"] == "detail"
    assert result["symbol_validation_status"] == "validated_by_exact_text"
    assert result["symbols"] == [
        "STRCUSDT",
        "CATUSDT",
        "TXNUSDT",
        "FLEXUSDT",
        "TERUSDT",
        "TTWOUSDT",
        "KSTRUSDT",
        "BSPUSDT",
    ]





