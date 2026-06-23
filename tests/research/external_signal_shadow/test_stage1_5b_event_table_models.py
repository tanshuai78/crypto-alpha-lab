from src.research.external_signal_shadow.stage1_5b_event_table_models import (
    ArticleEventRow,
    EventTableDecision,
    SymbolEventRow,
)


def test_stage1_5b_models_have_required_safety_flags():
    article = ArticleEventRow(
        article_event_id="a1",
        stage1_5a_source_line=1,
        source_name="binance_official_announcements",
        source_profile="binance_official_announcements_like_rows",
        source_capture_method="semi_auto_collector",
        source_url="https://www.binance.com/bapi/x",
        source_detail_url="https://www.binance.com/en/support/announcement/x",
        source_domain="binance.com",
        title="Binance Will Delist ABC",
        event_type="exchange_delisting_notice",
        source_published_at_ms=1710921600000,
        event_time_ms=1710921600000,
        available_at_ms=1710922500000,
        available_at_policy="source_published_at_ms_plus_stage1_5a_primary_announcement_delay_ms",
        symbols=["ABC"],
        symbol_count=1,
        manual_review_status="reviewed_high_confidence",
        input_payload_hash="h1",
        article_payload_hash="h2",
        notice_time_ms=1710921600000,
        effective_time_ms=None,
        effective_time_parse_status="not_parsed_in_stage1_5b",
        directional_hypothesis="undefined",
        signed_direction=None,
        long_allowed=False,
        short_allowed=False,
        replay_allowed=False,
        stage1_5c_review_pending=True,
        stage1_5c_input_allowed=True,
        stage1_5c_replay_candidate_allowed=False,
        stage1_5c_requires_price_coverage_check=True,
        stage1_5c_requires_filter_group_assignment=True,
        stage1_5c_requires_baseline_evaluation=True,
    )
    assert article.replay_allowed is False
    assert article.stage1_5c_review_pending is True
    assert article.stage1_5c_replay_candidate_allowed is False
    assert article.directional_hypothesis == "undefined"
    assert article.signed_direction is None


def test_symbol_event_row_disallows_trading_execution():
    row = SymbolEventRow(
        symbol_event_id="s1",
        article_event_id="a1",
        event_type="futures_contract_launch",
        symbol="ABCUSDT",
        base_asset="ABC",
        quote_asset="USDT",
        venue="binance",
        source_name="binance_official_announcements",
        source_profile="binance_official_announcements_like_rows",
        source_detail_url="https://www.binance.com/en/support/announcement/x",
        source_parent_url="https://www.binance.com/bapi/x",
        title="Binance Futures Will Launch ABCUSDT",
        source_published_at_ms=1710921600000,
        event_time_ms=1710921600000,
        available_at_ms=1710922500000,
        available_at_policy="source_published_at_ms_plus_stage1_5a_primary_announcement_delay_ms",
        notice_time_ms=1710921600000,
        effective_time_ms=None,
        effective_time_parse_status="not_parsed_in_stage1_5b",
        event_payload_hash="h",
        source_quality="stage1_5a_passed_manual_reviewed_high_confidence",
        source_audit_decision="source_audit_passed",
        event_type_audit_decision="source_audit_passed",
        stage1_5a_source_key="binance_official_announcements_like_rows_source",
        stage1_5a_review_path="docs/reviews/stage1_5a_review.md",
        stage1_5a_summary_path="data/external_signal_shadow/stage1_5a/summary.json",
        manual_review_status="reviewed_high_confidence",
        symbol_normalization_method="base_asset_plus_usdt_assumption",
        market_pair_existence_verified=False,
        price_history_coverage_verified=False,
        tradability_verified=False,
        directional_hypothesis="undefined",
        signed_direction=None,
        long_allowed=False,
        short_allowed=False,
        context_labels_allowed=False,
        replay_allowed=False,
        stage1_5c_review_pending=True,
        stage1_5c_input_allowed=True,
        stage1_5c_replay_candidate_allowed=False,
        paper_trading_allowed=False,
        live_trading_allowed=False,
    )
    assert row.paper_trading_allowed is False
    assert row.live_trading_allowed is False
    assert row.market_pair_existence_verified is False
    assert row.price_history_coverage_verified is False
    assert row.tradability_verified is False
    assert row.directional_hypothesis == "undefined"
    assert row.signed_direction is None
    assert row.stage1_5c_replay_candidate_allowed is False


def test_event_table_decision_enum_values():
    assert EventTableDecision.READY.value == "stage1_5b_event_table_ready"
    assert EventTableDecision.SPARSE.value == "stage1_5b_event_table_sparse_inconclusive"
    assert EventTableDecision.FAILED.value == "stage1_5b_event_table_failed"
