from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
    select_detail_retry_attempts,
    compute_detail_transient_backoff_ms,
    serialize_retry_articles,
    classify_never_attempted_defer_state,
    load_detail_retry_scheduler_state,
    write_detail_retry_scheduler_state,
    update_detail_endpoint_health,
)
from pathlib import Path



def test_never_attempted_article_is_selected_before_old_transient_backlog():
    now_ms = 1_000_000
    state = {
        "old1": {
            "source_article_id": "old1",
            "first_detected_at_ms": now_ms - 60_000,
            "detail_fetch_attempt_count": 7,
            "transient_detail_error_count": 7,
            "next_detail_retry_at_ms": now_ms,
            "last_retry_at_ms": now_ms - 60_000,
        },
        "old2": {
            "source_article_id": "old2",
            "first_detected_at_ms": now_ms - 60_000,
            "detail_fetch_attempt_count": 7,
            "transient_detail_error_count": 7,
            "next_detail_retry_at_ms": now_ms,
            "last_retry_at_ms": now_ms - 60_000,
        },
        "new": {
            "source_article_id": "new",
            "first_detected_at_ms": now_ms - 1_000,
            "detail_fetch_attempt_count": 0,
            "transient_detail_error_count": 0,
            "next_detail_retry_at_ms": 0,
            "defer_count": 0,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    )

    assert selected == ["new"]


def test_older_never_attempted_article_cannot_be_starved_by_continuous_new_articles():
    now_ms = 1_000_000
    state = {
        "older": {
            "source_article_id": "older",
            "first_detected_at_ms": now_ms - 9 * 60 * 1000,
            "detail_fetch_attempt_count": 0,
            "defer_count": 8,
            "next_detail_retry_at_ms": 0,
            "last_retry_at_ms": 0,
        },
        "newer": {
            "source_article_id": "newer",
            "first_detected_at_ms": now_ms - 10_000,
            "detail_fetch_attempt_count": 0,
            "defer_count": 0,
            "next_detail_retry_at_ms": 0,
            "last_retry_at_ms": 0,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    )

    assert selected == ["older"]


def test_first_attempt_sla_breached_article_is_selected_before_non_breached_article():
    now_ms = 20 * 60 * 1000
    state = {
        "high_defer_not_breached": {
            "source_article_id": "high_defer_not_breached",
            "first_detected_at_ms": now_ms - 60_000,
            "detail_fetch_attempt_count": 0,
            "defer_count": 2,
            "next_detail_retry_at_ms": 0,
            "last_retry_at_ms": 0,
        },
        "time_breached": {
            "source_article_id": "time_breached",
            "first_detected_at_ms": now_ms - 11 * 60 * 1000,
            "detail_fetch_attempt_count": 0,
            "defer_count": 0,
            "next_detail_retry_at_ms": 0,
            "last_retry_at_ms": 0,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
        max_first_attempt_delay_polls=3,
        max_first_attempt_delay_ms=10 * 60 * 1000,
    )

    assert selected == ["time_breached"]


def test_attempted_transient_article_not_selected_before_next_retry_time():
    now_ms = 1_000_000
    state = {
        "old": {
            "source_article_id": "old",
            "first_detected_at_ms": now_ms - 60_000,
            "detail_fetch_attempt_count": 2,
            "transient_detail_error_count": 2,
            "next_detail_retry_at_ms": now_ms + 30_000,
            "last_retry_at_ms": now_ms - 30_000,
        }
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    )

    assert selected == []


def test_serialize_retry_articles_fills_required_schema_defaults():
    raw_state = {
        "old": {
            "source_article_id": "old",
            "title": "Binance Futures Will Launch XUSDT Perpetual Contract",
            "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/old",
            "source_published_at_ms": 1000,
            "detected_at_ms": 2000,
            "event_type": "futures_contract_launch",
            "detail_fetch_attempt_count": 3,
        }
    }

    serialized = serialize_retry_articles(raw_state)

    article = serialized["old"]
    assert article["source_article_id"] == "old"
    assert article["defer_count"] == 0
    assert article["transient_detail_error_count"] == 0
    assert article["next_detail_retry_at_ms"] == 0
    assert article["title"]
    assert article["source_detail_url_normalized"]
    assert article["event_type"] == "futures_contract_launch"


def test_never_attempted_defer_sla_breach_counter_increments_before_max_age():
    result = classify_never_attempted_defer_state(
        detail_fetch_attempt_count=0,
        first_detected_at_ms=0,
        now_ms=11 * 60 * 1000,
        never_attempted_max_defer_sec=10 * 60,
        detail_fetch_max_age_sec=3600,
    )

    assert result["classification"] == "detail_first_attempt_sla_breach"
    assert result["terminal_failure_type"] is None


def test_never_attempted_max_age_becomes_budget_starved_not_parser_failure():
    result = classify_never_attempted_defer_state(
        detail_fetch_attempt_count=0,
        first_detected_at_ms=0,
        now_ms=3601 * 1000,
        never_attempted_max_defer_sec=10 * 60,
        detail_fetch_max_age_sec=3600,
    )

    assert result["classification"] == "detail_never_attempted_budget_starved"
    assert result["terminal_failure_type"] == "detail_never_attempted_budget_starved"
    assert result["detail_fetch_status"] == "budget_starved"


def test_detail_retry_scheduler_state_round_trips(tmp_path):
    state = {
        "articles": {
            "old": {
                "source_article_id": "old",
                "title": "Binance Futures Will Launch XUSDT Perpetual Contract",
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/old",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": 900,
                "detected_at_ms": 1000,
                "event_type": "futures_contract_launch",
                "symbol_extraction_source": "none",
                "pending_reason": "title_symbol_missing",
                "first_detected_at_ms": 1000,
                "detail_fetch_attempt_count": 2,
                "transient_detail_error_count": 2,
                "last_retry_at_ms": 2000,
                "next_detail_retry_at_ms": 62000,
                "defer_count": 0,
            }
        },
        "endpoint_health": {
            "detail_endpoint_degraded_until_ms": 62000,
            "recent_detail_attempt_results": ["http_202_empty"],
        },
    }

    write_detail_retry_scheduler_state(tmp_path, state, metadata_version=1)
    loaded = load_detail_retry_scheduler_state(tmp_path)

    assert loaded["metadata_version"] == 1
    assert loaded["articles"]["old"]["next_detail_retry_at_ms"] == 62000
    assert loaded["endpoint_health"]["detail_endpoint_degraded_until_ms"] == 62000


def test_old_202_backoff_survives_restart_and_new_article_gets_attempt(tmp_path):
    write_detail_retry_scheduler_state(
        tmp_path,
        {
            "articles": {
                "old": {
                    "source_article_id": "old",
                    "title": "Old article",
                    "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/old",
                    "source_parent_url": "https://www.binance.com/en/support/announcement",
                    "source_published_at_ms": 900,
                    "detected_at_ms": 1000,
                    "event_type": "futures_contract_launch",
                    "first_detected_at_ms": 1000,
                    "detail_fetch_attempt_count": 5,
                    "transient_detail_error_count": 5,
                    "next_detail_retry_at_ms": 999999,
                    "last_retry_at_ms": 5000,
                },
                "new": {
                    "source_article_id": "new",
                    "title": "New article",
                    "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/new",
                    "source_parent_url": "https://www.binance.com/en/support/announcement",
                    "source_published_at_ms": 7900,
                    "detected_at_ms": 8000,
                    "event_type": "futures_contract_launch",
                    "first_detected_at_ms": 8000,
                    "detail_fetch_attempt_count": 0,
                    "transient_detail_error_count": 0,
                    "next_detail_retry_at_ms": 0,
                    "defer_count": 0,
                },
            },
            "endpoint_health": {},
        },
        metadata_version=1,
    )

    loaded = load_detail_retry_scheduler_state(tmp_path)
    selected = select_detail_retry_attempts(
        detail_retry_state=loaded["articles"],
        now_ms=10_000,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    )

    assert selected == ["new"]


def test_pending_detail_article_survives_restart_after_it_disappears_from_catalog_list(tmp_path):
    write_detail_retry_scheduler_state(
        tmp_path,
        {
            "articles": {
                "missing_from_catalog": {
                    "source_article_id": "missing_from_catalog",
                    "title": "Binance Futures Will Launch XUSDT Perpetual Contract",
                    "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/missing_from_catalog",
                    "source_parent_url": "https://www.binance.com/en/support/announcement",
                    "source_published_at_ms": 1000,
                    "detected_at_ms": 1100,
                    "event_type": "futures_contract_launch",
                    "symbol_extraction_source": "none",
                    "pending_reason": "title_symbol_missing",
                    "first_detected_at_ms": 1100,
                    "detail_fetch_attempt_count": 0,
                    "transient_detail_error_count": 0,
                    "next_detail_retry_at_ms": 0,
                    "defer_count": 0,
                }
            },
            "endpoint_health": {},
        },
        metadata_version=1,
    )

    loaded = load_detail_retry_scheduler_state(tmp_path)
    article = loaded["articles"]["missing_from_catalog"]

    assert article["source_detail_url_normalized"].endswith("/missing_from_catalog")
    assert article["title"]
    assert article["event_type"] == "futures_contract_launch"
    assert select_detail_retry_attempts(
        detail_retry_state=loaded["articles"],
        now_ms=1200,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    ) == ["missing_from_catalog"]


def test_endpoint_degraded_after_recent_202_empty_rate_crosses_threshold():
    health = {"recent_detail_attempt_results": []}
    now_ms = 100_000
    for idx in range(5):
        health = update_detail_endpoint_health(
            health,
            now_ms=now_ms + idx,
            result_code="http_202_empty",
            degraded_rate_threshold=0.80,
            degraded_min_sample=5,
            degraded_backoff_sec=15 * 60,
        )

    assert health["detail_endpoint_degraded_until_ms"] == now_ms + 4 + 15 * 60 * 1000
    assert health["detail_endpoint_transient_error_rate"] == 1.0


def test_endpoint_degraded_skips_old_transient_but_preserves_never_attempted_first_attempt():
    now_ms = 100_000
    state = {
        "old": {
            "source_article_id": "old",
            "detail_fetch_attempt_count": 4,
            "transient_detail_error_count": 4,
            "next_detail_retry_at_ms": now_ms,
            "last_retry_at_ms": now_ms - 60_000,
            "first_detected_at_ms": now_ms - 600_000,
        },
        "new": {
            "source_article_id": "new",
            "detail_fetch_attempt_count": 0,
            "transient_detail_error_count": 0,
            "next_detail_retry_at_ms": 0,
            "first_detected_at_ms": now_ms - 1_000,
            "defer_count": 0,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=now_ms + 60_000,
    )

    assert selected == ["new"]


def test_endpoint_degraded_preserves_budget_cap_for_many_never_attempted_articles():
    now_ms = 100_000
    state = {
        f"new{i}": {
            "source_article_id": f"new{i}",
            "detail_fetch_attempt_count": 0,
            "transient_detail_error_count": 0,
            "next_detail_retry_at_ms": 0,
            "first_detected_at_ms": now_ms - i * 1000,
            "defer_count": 0,
        }
        for i in range(20)
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms + 60_000,
    )

    assert len(selected) == 3
    assert all(state[code]["detail_fetch_attempt_count"] == 0 for code in selected)


def test_endpoint_degraded_allows_recent_transient_retry_with_protected_budget():
    now_ms = 4 * 60 * 60 * 1000
    state = {
        "recent": {
            "source_article_id": "recent",
            "first_detected_at_ms": now_ms - 30 * 60 * 1000,
            "detail_http_request_count": 2,
            "detail_retry_cycle_count": 2,
            "transient_detail_error_count": 2,
            "next_detail_retry_at_ms": now_ms - 1,
            "last_retry_at_ms": now_ms - 11 * 60 * 1000,
        },
        "old": {
            "source_article_id": "old",
            "first_detected_at_ms": now_ms - 12 * 60 * 60 * 1000,
            "detail_http_request_count": 8,
            "detail_retry_cycle_count": 8,
            "transient_detail_error_count": 8,
            "next_detail_retry_at_ms": now_ms - 1,
            "last_retry_at_ms": now_ms - 11 * 60 * 1000,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms + 60_000,
        degraded_recent_article_window_ms=3 * 60 * 60 * 1000,
        degraded_recent_retry_interval_ms=10 * 60 * 1000,
        degraded_recent_retry_budget_per_poll=1,
        degraded_recent_retry_max_cycles=6,
    )

    assert selected == ["recent"]


def test_endpoint_degraded_recent_retry_respects_interval_and_attempt_cap():
    now_ms = 4 * 60 * 60 * 1000
    state = {
        "too_soon": {
            "source_article_id": "too_soon",
            "first_detected_at_ms": now_ms - 30 * 60 * 1000,
            "detail_http_request_count": 2,
            "detail_retry_cycle_count": 2,
            "transient_detail_error_count": 2,
            "next_detail_retry_at_ms": now_ms - 1,
            "last_retry_at_ms": now_ms - 2 * 60 * 1000,
        },
        "too_many": {
            "source_article_id": "too_many",
            "first_detected_at_ms": now_ms - 30 * 60 * 1000,
            "detail_http_request_count": 6,
            "detail_retry_cycle_count": 6,
            "transient_detail_error_count": 6,
            "next_detail_retry_at_ms": now_ms - 1,
            "last_retry_at_ms": now_ms - 11 * 60 * 1000,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms + 60_000,
        degraded_recent_article_window_ms=3 * 60 * 60 * 1000,
        degraded_recent_retry_interval_ms=10 * 60 * 1000,
        degraded_recent_retry_budget_per_poll=1,
        degraded_recent_retry_max_cycles=6,
    )

    assert selected == []


def test_serialize_retry_articles_fills_http_request_and_retry_cycle_counts():
    serialized = serialize_retry_articles({"a": {"source_article_id": "a"}})
    assert serialized["a"]["detail_http_request_count"] == 0
    assert serialized["a"]["detail_retry_cycle_count"] == 0
