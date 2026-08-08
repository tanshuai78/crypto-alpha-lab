from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
    select_detail_retry_attempts,
    compute_detail_transient_backoff_ms,
    serialize_retry_articles,
    classify_never_attempted_defer_state,
    load_detail_retry_scheduler_state,
    write_detail_retry_scheduler_state,
    update_detail_endpoint_health,
    update_detail_endpoint_health_by_source,
    is_detail_source_degraded,
    classify_detail_source_failure,
    summarize_detail_retry_overdue_state,
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


def test_serialize_retry_articles_preserves_revision_detail_work_type():
    serialized = serialize_retry_articles({
        "revision": {"source_article_id": "revision", "detail_work_type": "launch_schedule_revision_detail"}
    })
    assert serialized["revision"]["detail_work_type"] == "launch_schedule_revision_detail"


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


def test_overdue_attempted_transient_selected_after_endpoint_degraded_expires():
    now_ms = 10_000_000
    article = {
        "first_detected_at_ms": now_ms - 90 * 60 * 1000,
        "detail_http_request_count": 2,
        "detail_fetch_attempt_count": 2,
        "detail_retry_cycle_count": 1,
        "transient_detail_error_count": 1,
        "last_detail_failure_class": "http_202_empty",
        "detail_retryable": True,
        "last_retry_at_ms": now_ms - 80 * 60 * 1000,
        "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
        "defer_count": 1,
        "pending_reason": "title_symbol_missing",
    }

    selected = select_detail_retry_attempts(
        detail_retry_state={"f434": article},
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == ["f434"]


def test_overdue_attempted_transient_gets_bounded_slot_even_with_never_attempted_backlog():
    now_ms = 10_000_000
    state = {
        "fresh1": {
            "first_detected_at_ms": now_ms - 3 * 60 * 1000,
            "detail_http_request_count": 0,
            "detail_fetch_attempt_count": 0,
            "next_detail_retry_at_ms": 0,
        },
        "fresh2": {
            "first_detected_at_ms": now_ms - 4 * 60 * 1000,
            "detail_http_request_count": 0,
            "detail_fetch_attempt_count": 0,
            "next_detail_retry_at_ms": 0,
        },
        "fresh3": {
            "first_detected_at_ms": now_ms - 5 * 60 * 1000,
            "detail_http_request_count": 0,
            "detail_fetch_attempt_count": 0,
            "next_detail_retry_at_ms": 0,
        },
        "f434": {
            "first_detected_at_ms": now_ms - 90 * 60 * 1000,
            "detail_http_request_count": 2,
            "detail_fetch_attempt_count": 2,
            "detail_retry_cycle_count": 1,
            "transient_detail_error_count": 1,
            "last_detail_failure_class": "http_202_empty",
            "detail_retryable": True,
            "last_retry_at_ms": now_ms - 80 * 60 * 1000,
            "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            "defer_count": 1,
            "pending_reason": "title_symbol_missing",
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert "f434" in selected
    assert len(selected) <= 3
    assert len(selected) == len(set(selected))


def test_overdue_slot_is_within_total_budget_not_additive():
    now_ms = 10_000_000
    state = {
        f"fresh{i}": {
            "first_detected_at_ms": now_ms - i * 60_000,
            "detail_http_request_count": 0,
            "detail_fetch_attempt_count": 0,
            "next_detail_retry_at_ms": 0,
        }
        for i in range(1, 5)
    }
    state["f434"] = {
        "first_detected_at_ms": now_ms - 90 * 60 * 1000,
        "detail_http_request_count": 2,
        "detail_fetch_attempt_count": 2,
        "detail_retry_cycle_count": 1,
        "transient_detail_error_count": 1,
        "last_detail_failure_class": "http_202_empty",
        "detail_retryable": True,
        "last_retry_at_ms": now_ms - 80 * 60 * 1000,
        "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert len(selected) <= 3


def test_overdue_reserved_slot_never_consumes_last_first_attempt_slot():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "fresh": {
                "first_detected_at_ms": now_ms - 60_000,
                "detail_http_request_count": 0,
                "detail_fetch_attempt_count": 0,
                "next_detail_retry_at_ms": 0,
            },
            "f434": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            },
        },
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == ["fresh"]


def test_overdue_attempted_respects_minimum_retry_interval():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "f434": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 5 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms + 10 * 60 * 1000,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == []


def test_attempted_state_with_missing_next_retry_is_diagnosed_not_selected():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "bad": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": 0,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == []


def test_title_symbol_missing_alone_does_not_make_hard_failure_retryable():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "hard": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "pending_reason": "title_symbol_missing",
                "last_detail_failure_class": "http_404",
                "detail_retryable": False,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == []


def test_missing_failure_class_does_not_make_title_symbol_missing_retryable():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "ambiguous": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "pending_reason": "title_symbol_missing",
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == []


def test_http_500_transient_row_does_not_consume_overdue_reserved_slot_with_first_attempt_backlog():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "fresh": {
                "first_detected_at_ms": now_ms - 5 * 60 * 1000,
                "detail_http_request_count": 0,
            },
            "server_error": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_500",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == ["fresh"]


def test_http_202_empty_attempted_row_is_retryable():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "f434": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == ["f434"]


def test_overdue_attempted_transient_not_selected_when_degraded_active_and_not_recent_allowed():
    now_ms = 10_000_000
    article = {
        "first_detected_at_ms": now_ms - 10 * 60 * 60 * 1000,
        "detail_http_request_count": 2,
        "detail_fetch_attempt_count": 2,
        "detail_retry_cycle_count": 10,
        "transient_detail_error_count": 8,
        "last_detail_failure_class": "http_202_empty",
        "detail_retryable": True,
        "last_retry_at_ms": now_ms - 4 * 60 * 60 * 1000,
        "next_detail_retry_at_ms": now_ms - 3 * 60 * 60 * 1000,
    }

    selected = select_detail_retry_attempts(
        detail_retry_state={"old": article},
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms + 10 * 60 * 1000,
        degraded_recent_article_window_ms=3 * 60 * 60 * 1000,
        degraded_recent_retry_interval_ms=10 * 60 * 1000,
        degraded_recent_retry_budget_per_poll=1,
        degraded_recent_retry_max_cycles=6,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == []


def test_summarize_detail_retry_overdue_state_reports_attempted_overdue_rows():
    now_ms = 10_000_000
    result = summarize_detail_retry_overdue_state(
        {
            "f434": {
                "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "transient_detail_error_count": 1,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "terminal_state": False,
            },
            "future": {
                "detail_http_request_count": 1,
                "next_detail_retry_at_ms": now_ms + 10_000,
                "terminal_state": False,
            },
        },
        now_ms=now_ms,
        warn_ms=30 * 60 * 1000,
        hard_warn_ms=2 * 60 * 60 * 1000,
    )

    assert result["detail_retry_overdue_pending_count"] == 1
    assert result["detail_retry_overdue_attempted_count"] == 1
    assert result["detail_retry_oldest_overdue_ms"] == 70 * 60 * 1000
    assert result["detail_retry_overdue_warn_active"] is True
    assert result["detail_retry_overdue_hard_warn_active"] is False
    assert result["detail_retry_overdue_articles"][0]["source_article_id"] == "f434"


def test_summarize_overdue_skips_attempted_row_with_zero_next_retry():
    now_ms = 10_000_000
    result = summarize_detail_retry_overdue_state(
        {
            "attempted_missing_next": {
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "next_detail_retry_at_ms": 0,
                "terminal_state": False,
            }
        },
        now_ms=now_ms,
        warn_ms=30 * 60 * 1000,
        hard_warn_ms=2 * 60 * 60 * 1000,
    )

    assert result["detail_retry_overdue_attempted_count"] == 0
    assert result["detail_retry_due_timestamp_missing_count"] == 1


def test_overdue_diagnostics_do_not_hide_http_attempt_counter_mismatch():
    now_ms = 10_000_000
    result = summarize_detail_retry_overdue_state(
        {
            "legacy_mismatch": {
                "detail_http_request_count": 0,
                "detail_fetch_attempt_count": 2,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
                "terminal_state": False,
            }
        },
        now_ms=now_ms,
        warn_ms=30 * 60 * 1000,
        hard_warn_ms=2 * 60 * 60 * 1000,
    )

    assert result["detail_retry_overdue_attempted_count"] == 0
    assert result["detail_retry_overdue_attempted_count"] == 0
    assert result["detail_attempt_manifest_mismatch_count"] == 1
    assert result["legacy_attempt_count_fallback_used"] is False


def test_overdue_attempted_queue_has_bounded_round_robin_service():
    now_ms = 10_000_000
    state = {
        f"article_{i}": {
            "source_article_id": f"article_{i}",
            "first_detected_at_ms": now_ms - (100 + i) * 60_000,
            "detail_http_request_count": 2,
            "transient_detail_error_count": 1,
            "last_detail_failure_class": "http_202_empty",
            "detail_retryable": True,
            "last_retry_at_ms": now_ms - (80 + i) * 60_000,
            "next_detail_retry_at_ms": now_ms - (70 + i) * 60_000,
        }
        for i in range(3)
    }

    selected_set = set()
    for poll in range(3):
        current_now = now_ms + poll * 15 * 60_000
        selected = select_detail_retry_attempts(
            detail_retry_state=state,
            now_ms=current_now,
            detail_budget_per_poll=1,
            endpoint_degraded_until_ms=0,
            overdue_attempted_retry_budget_per_poll=1,
            overdue_attempted_min_interval_ms=10 * 60_000,
            min_never_attempted_slots_per_poll=0,
        )
        for code in selected:
            selected_set.add(code)
            state[code]["last_retry_at_ms"] = current_now
            state[code]["next_detail_retry_at_ms"] = current_now + 60 * 60_000

    assert selected_set == {"article_0", "article_1", "article_2"}


def test_support_202_degraded_state_does_not_suppress_bapi_detail():
    now = 100_000
    health = update_detail_endpoint_health_by_source(
        {},
        now_ms=now,
        source="support_article_detail",
        result_code="http_202_empty",
        degraded_rate_threshold=0.8,
        degraded_min_sample=1,
        degraded_backoff_sec=900,
    )
    assert is_detail_source_degraded(health, "support_article_detail", now + 1) is True
    assert is_detail_source_degraded(health, "bapi_article_detail_query", now + 1) is False


def test_bapi_degraded_state_does_not_disable_support_fallback():
    now = 100_000
    health = update_detail_endpoint_health_by_source(
        {},
        now_ms=now,
        source="bapi_article_detail_query",
        result_code="http_503",
        degraded_rate_threshold=0.8,
        degraded_min_sample=1,
        degraded_backoff_sec=900,
    )
    assert is_detail_source_degraded(health, "bapi_article_detail_query", now + 1) is True
    assert is_detail_source_degraded(health, "support_article_detail", now + 1) is False


def test_legacy_global_degraded_state_is_support_only_not_bapi():
    now = 100_000
    legacy_health = {"detail_endpoint_degraded_until_ms": now + 60_000}

    assert is_detail_source_degraded(legacy_health, "bapi_article_detail_query", now) is False
    assert is_detail_source_degraded(legacy_health, "support_article_detail", now) is True


def test_bapi_illegal_parameter_is_article_specific_terminal_not_support_terminal():
    state = classify_detail_source_failure(
        source="bapi_article_detail_query",
        http_status=400,
        error="bapi_api_code_non_000000",
    )
    assert state["retryable"] is False
    assert state["terminal_reason"]
    assert state["support_fallback_allowed"] is True


def test_bapi_429_is_transient_and_updates_bapi_breaker_only():
    state = classify_detail_source_failure(
        source="bapi_article_detail_query",
        http_status=429,
        error="bapi_http_non_200",
    )
    assert state["retryable"] is True
    assert state["breaker_source"] == "bapi_article_detail_query"


def test_bapi_identity_mismatch_is_integrity_failure_with_support_fallback():
    state = classify_detail_source_failure(
        source="bapi_article_detail_query",
        http_status=200,
        error="bapi_article_identity_mismatch",
    )
    assert state["retryable"] is False
    assert state["integrity_alert"] is True
    assert state["support_fallback_allowed"] is True


def test_bapi_parser_diagnostics_round_trip():
    raw_state = {
        "art1": {
            "source_article_id": "art1",
            "last_bapi_detail_status": "success",
            "last_bapi_payload_hash": "hash123",
            "last_bapi_parser_version": "stage1_5d_symbol_extraction_v3",
            "last_bapi_parser_status": "no_symbols",
            "last_bapi_parse_attempt_at_ms": 1000,
            "launch_anchor_policy": "bapi_multi_contract_strict",
            "required_launch_anchor_source": "detail_per_symbol_time_or_exchangeinfo_onboard",
        }
    }
    serialized = serialize_retry_articles(raw_state)
    assert serialized["art1"]["last_bapi_detail_status"] == "success"
    assert serialized["art1"]["last_bapi_payload_hash"] == "hash123"
    assert serialized["art1"]["last_bapi_parser_version"] == "stage1_5d_symbol_extraction_v3"
    assert serialized["art1"]["last_bapi_parser_status"] == "no_symbols"
    assert serialized["art1"]["last_bapi_parse_attempt_at_ms"] == 1000
    assert serialized["art1"]["launch_anchor_policy"] == "bapi_multi_contract_strict"
    assert serialized["art1"]["required_launch_anchor_source"] == "detail_per_symbol_time_or_exchangeinfo_onboard"


def test_v1_scheduler_state_loads_with_safe_defaults(tmp_path):
    import json
    v1_json = {
        "metadata_version": 1,
        "articles": {
            "art1": {"source_article_id": "art1", "title": "Test Title"}
        },
        "endpoint_health": {}
    }
    file_path = tmp_path / "detail_retry_scheduler_state.json"
    file_path.write_text(json.dumps(v1_json))
    loaded = load_detail_retry_scheduler_state(tmp_path)
    art = loaded["articles"]["art1"]
    assert art["last_bapi_detail_status"] is None
    assert art["last_bapi_parser_status"] is None
    assert art["launch_anchor_policy"] is None

