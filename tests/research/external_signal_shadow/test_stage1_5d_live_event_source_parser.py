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
    extract_symbol_candidates_from_bapi_article_payload,
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
    assert row["parser_version"] == "stage1_5d_symbol_extraction_v3"
    assert row["symbol_extraction_version"] == 3



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


def test_title_extracts_raw_contract_symbol_candidate_ethusd1():
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        extract_symbol_candidates_from_title,
    )
    title = "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)"
    result = extract_symbol_candidates_from_title(title, max_symbols=30)
    assert result["symbols"] == ["ETHUSD1"]
    assert result["symbol_extraction_source"] == "title_contract_symbol"
    assert result["symbol_derivation_method"] == "none"
    assert result["symbol_validation_status"] == "requires_exchange_info_validation"


def test_title_prefers_exact_usdt_usdc_symbols_as_parsed_title_symbols():
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        extract_symbol_candidates_from_title,
    )
    title = "Binance Futures Will Launch USDⓈ-Margined CAPUSDT Perpetual Contract (2026-06-27)"
    result = extract_symbol_candidates_from_title(title, max_symbols=30)
    assert result["symbols"] == ["CAPUSDT"]
    assert result["symbol_extraction_source"] == "title"
    assert result["symbol_validation_status"] == "validated_by_exact_text"


def test_title_contract_candidate_does_not_collect_generic_words():
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        extract_symbol_candidates_from_title,
    )
    title = "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)"
    result = extract_symbol_candidates_from_title(title, max_symbols=30)
    assert result["symbols"] == []


def test_title_candidate_extraction_only_scans_margin_to_perpetual_segment():
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        extract_contract_symbol_candidates_from_title,
    )
    title = "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract; Risk Warning ABCDEF"
    result = extract_contract_symbol_candidates_from_title(title, max_symbols=30)
    assert result == ["ETHUSD1"]


def test_title_candidate_rejects_usds_margined_generic_title_without_symbol():
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        extract_contract_symbol_candidates_from_title,
    )
    title = "Binance Futures Will Launch Multiple USDS-Margined TradFi Perpetual Contracts (2026-07-02)"
    assert extract_contract_symbol_candidates_from_title(title, max_symbols=30) == []


def test_title_candidate_rejects_date_and_generic_words():
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        extract_contract_symbol_candidates_from_title,
    )
    title = "Binance Futures Will Launch USDⓈ-Margined Perpetual Contract (2026-07-03)"
    assert extract_contract_symbol_candidates_from_title(title, max_symbols=30) == []


def test_bapi_body_json_tree_text_extraction_records_context():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": '{"node":"root","child":[{"node":"text","text":"Binance Futures will launch SHAZUSDT and SOFIUSDT USDⓈ-Margined Perpetual Contracts."}]}',
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SHAZUSDT", "SOFIUSDT"]
    assert result["symbol_extraction_source"] == "bapi_article_body"
    assert result["evidence_source"] == "official_article_body_confirmed"
    assert result["detail_transport"] == "bapi_article_detail_query"
    assert result["content_provenance"] == "binance_official_announcement"
    assert result["source_transport"] == "binance_first_party_public_web_bapi_undocumented"
    assert result["candidate_provenance"][0]["body_node_path"]
    assert result["candidate_provenance"][0]["event_phrase_match"] is True
    assert "extracted_text" in result


def test_raw_unparsed_bapi_body_string_is_not_parsed():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": "SHAZUSDT SOFIUSDT appears but this is not recognized JSON tree",
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == []
    assert result["symbol_parse_status"] == "not_attempted"
    assert result["symbol_parse_failed_reason"] == "bapi_body_schema_drift"


def test_unrelated_valid_symbol_in_bapi_disclaimer_is_ignored():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": '{"node":"root","child":[{"node":"text","text":"Risk warning: BTCUSDT may be volatile."}]}',
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == []


def test_bapi_body_reuses_existing_launch_time_parser():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": '{"node":"root","child":[{"node":"text","text":"Binance Futures will launch SHAZUSDT USDⓈ-Margined Perpetual Contract at 2026-07-21 13:30 (UTC)."}]}',
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SHAZUSDT"]
    assert result["symbol_launch_times_ms"]["SHAZUSDT"] == 1784640600000


def test_single_large_node_does_not_capture_disclaimer_symbol():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": '{"node":"root","child":[{"node":"text","text":"Binance Futures will launch SHAZUSDT USDⓈ-Margined Perpetual Contract at 2026-07-21 13:30 (UTC). Risk warning: BTCUSDT may be volatile."}]}',
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SHAZUSDT"]


def test_bapi_json_depth_limit_is_enforced(monkeypatch):
    nested = {"text": "Binance Futures will launch ABCUSDT Perpetual Contract."}
    for _ in range(5):
        nested = {"child": nested}
    payload = {"code": "000000", "data": {"body": nested}}

    monkeypatch.setattr(
        "configs.base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_JSON_DEPTH", 3
    )
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)

    assert result["symbols"] == []
    assert result["symbol_parse_failed_reason"] == "bapi_body_json_depth_exceeded"


def test_bapi_json_node_count_limit_is_enforced(monkeypatch):
    payload = {
        "code": "000000",
        "data": {
            "body": [
                {"text": f"Binance Futures will launch A{i}USDT Perpetual Contract."}
                for i in range(5)
            ]
        },
    }

    monkeypatch.setattr(
        "configs.base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_NODE_COUNT", 3
    )
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)

    assert result["symbols"] == []
    assert result["symbol_parse_failed_reason"] == "bapi_body_json_node_count_exceeded"


def test_bapi_extracted_text_limit_is_enforced(monkeypatch):
    payload = {
        "code": "000000",
        "data": {
            "body": {
                "text": "Binance Futures will launch ABCUSDT Perpetual Contract at 2026-07-21 13:30 (UTC)."
            }
        },
    }

    monkeypatch.setattr(
        "configs.base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_EXTRACTED_TEXT_CHARS",
        20,
    )
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)

    assert result["symbols"] == []
    assert result["symbol_parse_failed_reason"] == "bapi_body_extracted_text_too_large"


def test_bapi_f434_fixture_extracts_expected_symbols():
    import json
    from pathlib import Path
    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_f434_fixture.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SHAZUSDT", "SOFIUSDT", "PANWUSDT", "PENGUSDT"]
    assert set(result["symbol_launch_times_ms"]) == {"SHAZUSDT", "SOFIUSDT", "PANWUSDT", "PENGUSDT"}


def test_bapi_d0833_fixture_extracts_expected_symbols():
    import json
    from pathlib import Path
    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_d0833_fixture.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["GEVUSDT", "VRTUSDT", "SNOWUSDT", "APPUSDT"]


def test_bapi_6cbb_fixture_extracts_spcxusd1():
    import json
    from pathlib import Path
    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_6cbb_fixture.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SPCXUSD1"]


def test_minimized_schedule_fixture_preserves_expected_schedule_structure():
    import json
    from pathlib import Path
    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_f434_real_frozen_fixture.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"]
    assert result["extracted_text"]
    assert "UTC" in result["extracted_text"]


def test_a827_real_frozen_fixture_hash_matches_expected():
    import hashlib, json
    from pathlib import Path

    fixture = Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json")
    meta = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture_metadata.json").read_text())
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == meta["fixture_sha256"]
    payload = json.loads(fixture.read_text())
    assert payload.get("data", {}).get("code") == meta["articleCode"]


def test_a827_bapi_fixture_extracts_symbols_and_launch_times():
    import json
    from pathlib import Path
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        extract_symbol_candidates_from_bapi_article_payload,
    )

    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json").read_text())
    meta = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture_metadata.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, title=meta["title"])
    assert result["symbols"] == meta["expected_symbols"]
    assert result["symbol_launch_times_ms"] == meta["expected_symbol_launch_times_ms"]


def test_stage1_5d_parser_versions_are_v3():
    from src.research.external_signal_shadow import stage1_5d_live_event_source_parser as p
    assert p.PARSER_VERSION == "stage1_5d_symbol_extraction_v3"
    assert p.SYMBOL_EXTRACTION_VERSION == 3
    assert p.LAUNCH_SCHEDULE_PARSER_VERSION == "stage1_5d_bapi_launch_schedule_v1"


def test_bapi_table_launch_schedule_symbol_time_count_mismatch_is_diagnostic():
    payload = {
        "code": "000000",
        "data": {
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
            "body": "<table><tr><th>USDⓈ-M Perpetual Contract</th><th>AAAUSDT</th><th>BBBUSDT</th></tr><tr><th>Launch Time</th><th>2026-07-27 13:30 (UTC)</th></tr></table>"
        }
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts")
    assert result["symbols"] == []
    assert result["symbol_launch_times_ms"] == {}
    assert result["parser_status"] == "launch_schedule_ambiguous"
    assert result["consumable_event_allowed"] is False


def test_bapi_table_parser_does_not_capture_disclaimer_symbols():
    payload = {
        "code": "000000",
        "data": {
            "title": "Binance Futures Will Launch TMFUSDT Perpetual Contract",
            "body": "<p>Binance Futures will launch TMFUSDT Perpetual Contract at 2026-07-27 13:30 (UTC).</p><p>Disclaimer: BTCUSDT is a benchmark asset.</p>"
        }
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, title="Binance Futures Will Launch TMFUSDT Perpetual Contract")
    assert result["symbols"] == ["TMFUSDT"]
    assert "BTCUSDT" not in result["symbols"]


def test_bapi_table_parser_duplicate_mobile_desktop_table_is_ambiguous():
    payload = {
        "code": "000000",
        "data": {
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
            "body": "<div><table><tr><th>USDⓈ-M Perpetual Contract</th><th>TMFUSDT</th></tr><tr><th>Launch Time</th><th>2026-07-27 13:30 (UTC)</th></tr></table><table><tr><th>USDⓈ-M Perpetual Contract</th><th>TMFUSDT</th></tr><tr><th>Launch Time</th><th>2026-07-27 13:30 (UTC)</th></tr></table></div>"
        }
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts")
    assert result["parser_status"] == "launch_schedule_ambiguous"
    assert result["consumable_event_allowed"] is False



