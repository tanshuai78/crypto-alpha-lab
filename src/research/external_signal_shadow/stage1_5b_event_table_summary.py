import datetime
from collections import Counter
from typing import Any, Dict, List

from configs import base
from src.research.external_signal_shadow.stage1_5b_event_table_models import (
    ArticleEventRow,
    EventTableDecision,
    SymbolEventRow,
)
from src.research.external_signal_shadow.stage1_5b_event_table_normalizer import (
    normalize_base_asset_symbol,
)


def build_event_table_summary(
    article_rows: List[ArticleEventRow],
    symbol_rows: List[SymbolEventRow],
    source_audit_passed: bool,
) -> Dict[str, Any]:
    article_level_row_count = len(article_rows)
    normalized_symbol_event_count = len(symbol_rows)

    # Calculate unique event days
    unique_days_set = set()
    for row in article_rows:
        dt = datetime.datetime.fromtimestamp(row.event_time_ms / 1000, tz=datetime.timezone.utc)
        unique_days_set.add(dt.date())
    unique_event_days = len(unique_days_set)

    # Unique symbols
    symbols_with_events = len({row.symbol for row in symbol_rows})

    # Event type counts
    event_type_counts_article_level = dict(Counter(row.event_type for row in article_rows))
    event_type_counts_symbol_level = dict(Counter(row.event_type for row in symbol_rows))

    # Multi-symbol articles
    multi_symbol_article_count = sum(1 for row in article_rows if len(row.symbols) > 1)

    # Rates
    source_detail_url_present_rate = (
        sum(1 for row in article_rows if row.source_detail_url) / article_level_row_count
        if article_level_row_count > 0
        else 1.0
    )
    source_published_at_present_rate = (
        sum(1 for row in article_rows if row.source_published_at_ms > 0) / article_level_row_count
        if article_level_row_count > 0
        else 1.0
    )
    manual_review_status_pass_rate = (
        sum(1 for row in article_rows if row.manual_review_status == "reviewed_high_confidence")
        / article_level_row_count
        if article_level_row_count > 0
        else 1.0
    )

    # Duplicate IDs
    article_ids = [row.article_event_id for row in article_rows]
    article_event_id_duplicate_count = len(article_ids) - len(set(article_ids))

    symbol_ids = [row.symbol_event_id for row in symbol_rows]
    symbol_event_id_duplicate_count = len(symbol_ids) - len(set(symbol_ids))

    # Quarantine count
    symbol_normalization_quarantine_count = 0
    for row in article_rows:
        for sym in row.symbols:
            try:
                normalize_base_asset_symbol(sym)
            except ValueError:
                symbol_normalization_quarantine_count += 1

    # Check allowed event types only
    allowed_types = set(base.EXTERNAL_SIGNAL_STAGE1_5B_ALLOWED_EVENT_TYPES)
    unsupported_type_present = any(
        row.event_type not in allowed_types for row in article_rows
    )

    # Identify blockers
    blockers = []
    if not source_audit_passed:
        blockers.append("source_audit_not_passed")

    # Hard safety blockers
    if unsupported_type_present:
        blockers.append("unsupported_event_type_present")
    if manual_review_status_pass_rate < 1.0:
        blockers.append("manual_review_status_failed")
    if source_detail_url_present_rate < 1.0:
        blockers.append("missing_source_detail_url")
    if source_published_at_present_rate < 1.0:
        blockers.append("missing_source_timestamp")
    if symbol_normalization_quarantine_count > 0:
        blockers.append("symbol_normalization_quarantine_failed")
    if article_event_id_duplicate_count > 0:
        blockers.append("duplicate_article_event_ids")
    if symbol_event_id_duplicate_count > 0:
        blockers.append("duplicate_symbol_event_ids")

    # Density blockers (for sparse)
    density_blockers = []
    if article_level_row_count < base.EXTERNAL_SIGNAL_STAGE1_5B_MIN_ARTICLE_EVENTS:
        density_blockers.append("article_level_row_count_below_30")
    if unique_event_days < base.EXTERNAL_SIGNAL_STAGE1_5B_MIN_UNIQUE_EVENT_DAYS:
        density_blockers.append("unique_event_days_below_20")
    if symbols_with_events < base.EXTERNAL_SIGNAL_STAGE1_5B_MIN_SYMBOLS_WITH_EVENTS:
        density_blockers.append("symbols_with_events_below_3")

    # Determine Decision
    if blockers:
        decision = EventTableDecision.FAILED.value
        all_blockers = blockers + density_blockers
    elif density_blockers:
        decision = EventTableDecision.SPARSE.value
        all_blockers = density_blockers
    else:
        decision = EventTableDecision.READY.value
        all_blockers = []

    # Next Action
    if decision == EventTableDecision.READY.value:
        next_action = "write_stage1_5c_external_catalyst_replay_implementation_plan"
    elif decision == EventTableDecision.SPARSE.value:
        next_action = "collect_more_high_confidence_events_or_add_okx_source_audit"
    else:
        next_action = "fix_event_table_inputs_before_replay"

    return {
        "stage": "external_signal_shadow_lab_stage1_5b",
        "scope": "minimal_historical_event_table_only",
        "decision": decision,
        "source_audit_required": True,
        "source_audit_passed_required": True,
        "source_audit_passed": source_audit_passed,
        "article_level_row_count": article_level_row_count,
        "normalized_symbol_event_count": normalized_symbol_event_count,
        "unique_event_days": unique_event_days,
        "symbols_with_events": symbols_with_events,
        "event_type_counts_article_level": event_type_counts_article_level,
        "event_type_counts_symbol_level": event_type_counts_symbol_level,
        "multi_symbol_article_count": multi_symbol_article_count,
        "source_detail_url_present_rate": source_detail_url_present_rate,
        "source_published_at_present_rate": source_published_at_present_rate,
        "manual_review_status_pass_rate": manual_review_status_pass_rate,
        "article_event_id_duplicate_count": article_event_id_duplicate_count,
        "symbol_event_id_duplicate_count": symbol_event_id_duplicate_count,
        "symbol_normalization_quarantine_count": symbol_normalization_quarantine_count,
        "stage1_5c_candidate_allowance_not_determined_by_stage1_5b": True,
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "context_label_join_allowed": False,
        "blockers": all_blockers,
        "next_action": next_action,
        "price_join_allowed": False,
        "forward_return_allowed": False,
        "replay_allowed": False,
        "alpha_interpretation_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
    }
