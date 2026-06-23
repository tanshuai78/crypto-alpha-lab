import pytest

from src.research.external_signal_shadow.stage1_5b_event_table_models import (
    ArticleEventRow,
    EventTableDecision,
    SymbolEventRow,
)
from src.research.external_signal_shadow.stage1_5b_event_table_summary import (
    build_event_table_summary,
)


@pytest.fixture
def sample_article_rows():
    rows = []
    base_ts = 1710000000000
    for i in range(30):
        ts = base_ts + i * 86_400_000
        rows.append(ArticleEventRow(
            article_event_id=f"article-{i}",
            stage1_5a_source_line=i + 1,
            source_name="binance_official_announcements",
            source_profile="binance_official_announcements_like_rows",
            source_capture_method="semi_auto_collector",
            source_url="https://www.binance.com/bapi/x",
            source_detail_url=f"https://www.binance.com/en/support/announcement/{i}",
            source_domain="binance.com",
            title=f"Binance Futures Will Launch TOK{i:02d}USDT Perpetual Contract",
            event_type="futures_contract_launch" if i < 20 else "exchange_delisting_notice",
            source_published_at_ms=ts,
            event_time_ms=ts,
            notice_time_ms=ts,
            effective_time_ms=None,
            effective_time_parse_status="not_parsed_in_stage1_5b",
            available_at_ms=ts + 900_000,
            available_at_policy="source_published_at_ms_plus_stage1_5a_primary_announcement_delay_ms",
            symbols=[f"TOK{i:02d}"],
            symbol_count=1,
            manual_review_status="reviewed_high_confidence",
            input_payload_hash=f"input-{i}",
            article_payload_hash=f"article-hash-{i}",
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
        ))
    return rows


@pytest.fixture
def sample_symbol_rows(sample_article_rows):
    rows = []
    for article in sample_article_rows:
        base_asset = article.symbols[0]
        rows.append(SymbolEventRow(
            symbol_event_id=f"symbol-{article.article_event_id}",
            article_event_id=article.article_event_id,
            event_type=article.event_type,
            symbol=f"{base_asset}USDT",
            base_asset=base_asset,
            quote_asset="USDT",
            venue="binance",
            source_name=article.source_name,
            source_profile=article.source_profile,
            source_detail_url=article.source_detail_url,
            source_parent_url=article.source_url,
            title=article.title,
            source_published_at_ms=article.source_published_at_ms,
            event_time_ms=article.event_time_ms,
            notice_time_ms=article.notice_time_ms,
            effective_time_ms=None,
            effective_time_parse_status="not_parsed_in_stage1_5b",
            available_at_ms=article.available_at_ms,
            available_at_policy=article.available_at_policy,
            event_payload_hash=f"event-{article.article_event_id}",
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
        ))
    return rows


def test_summary_ready_when_article_and_symbol_density_pass(sample_article_rows, sample_symbol_rows):
    summary = build_event_table_summary(sample_article_rows, sample_symbol_rows, source_audit_passed=True)
    assert summary["decision"] == EventTableDecision.READY.value
    assert summary["article_level_row_count"] >= 30
    assert summary["replay_allowed"] is False
    assert summary["paper_trading_allowed"] is False
    assert summary["stage1_5c_candidate_allowance_not_determined_by_stage1_5b"] is True
    assert summary["next_action"] == "write_stage1_5c_external_catalyst_replay_implementation_plan"


def test_summary_reports_event_type_counts_article_and_symbol_level(sample_article_rows, sample_symbol_rows):
    summary = build_event_table_summary(sample_article_rows, sample_symbol_rows, source_audit_passed=True)
    assert summary["event_type_counts_article_level"] == {
        "futures_contract_launch": 20,
        "exchange_delisting_notice": 10,
    }
    assert summary["event_type_counts_symbol_level"] == {
        "futures_contract_launch": 20,
        "exchange_delisting_notice": 10,
    }


def test_summary_failed_when_source_audit_not_passed(sample_article_rows, sample_symbol_rows):
    summary = build_event_table_summary(sample_article_rows, sample_symbol_rows, source_audit_passed=False)
    assert summary["decision"] == EventTableDecision.FAILED.value
    assert "source_audit_not_passed" in summary["blockers"]
