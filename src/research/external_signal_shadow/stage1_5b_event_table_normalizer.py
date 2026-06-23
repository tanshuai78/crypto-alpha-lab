import hashlib
import json
import re
from dataclasses import asdict
from typing import Any, Dict, List, Set, Tuple

from configs import base
from src.research.external_signal_shadow.stage1_5b_event_table_models import (
    ArticleEventRow,
    SymbolEventRow,
)

FORBIDDEN_BASE_ASSETS = {"USDT", "USDC", "BUSD", "USD", "EUR", "TRY", "GBP"}


def canonical_json_hash(obj: Dict[str, Any]) -> str:
    serialized = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def normalize_base_asset_symbol(raw_symbol: str) -> Tuple[str, str, str]:
    if not isinstance(raw_symbol, str):
        raise ValueError("Symbol must be a string")
    trimmed = raw_symbol.strip()
    if not trimmed:
        raise ValueError("Symbol is empty")

    if "/" in trimmed:
        raise ValueError(f"Symbol contains '/': {trimmed} (ambiguous)")

    uppercased = trimmed.upper()
    if not re.match(r"^[A-Z0-9]{2,15}$", uppercased):
        raise ValueError(
            f"Symbol {trimmed!r} does not match required format ^[A-Z0-9]{'{{'}2,15{'}}'}$"
        )

    if uppercased in FORBIDDEN_BASE_ASSETS:
        raise ValueError(f"Symbol {trimmed!r} is a forbidden base asset word")

    base_asset = uppercased
    symbol = f"{base_asset}USDT"
    quote_asset = "USDT"
    return base_asset, symbol, quote_asset


def dataclass_to_json_dict(row: Any) -> Dict[str, Any]:
    return asdict(row)


def build_article_event_rows(
    rows: List[Dict[str, Any]], allowed_event_types: Set[str]
) -> List[ArticleEventRow]:
    article_rows = []
    for row in rows:
        event_type = row.get("event_type_candidate")
        if not event_type:
            raise ValueError("unsupported_event_type_present: missing event_type_candidate")
        if event_type not in allowed_event_types:
            raise ValueError(
                f"unsupported_event_type_present: {event_type!r} is not allowed for Stage 1.5B"
            )

        title = row.get("title", "")
        time_ms = row.get("time", 0)
        url = row.get("url", "")

        # article_event_id = sha256(title|time|url)
        id_str = f"{title}|{time_ms}|{url}"
        article_event_id = hashlib.sha256(id_str.encode("utf-8")).hexdigest()

        # Build initial row without hash
        article_row = ArticleEventRow(
            article_event_id=article_event_id,
            stage1_5a_source_line=row.get("source_line", 0),
            source_name=row.get("source_name", ""),
            source_profile=base.EXTERNAL_SIGNAL_STAGE1_5B_SOURCE_PROFILE,
            source_capture_method=row.get("source_capture_method", ""),
            source_url=row.get("source_url", ""),
            source_detail_url=url,
            source_domain="binance.com",
            title=title,
            event_type=event_type,
            source_published_at_ms=time_ms,
            event_time_ms=time_ms,
            available_at_ms=time_ms + base.EXTERNAL_SIGNAL_STAGE1_5B_PRIMARY_ANNOUNCEMENT_DELAY_MS,
            available_at_policy="source_published_at_ms_plus_stage1_5a_primary_announcement_delay_ms",
            symbols=row.get("symbol", []),
            symbol_count=len(row.get("symbol", [])),
            manual_review_status=row.get("manual_review_status", ""),
            input_payload_hash=canonical_json_hash(row),
            article_payload_hash="",  # placeholder
            notice_time_ms=time_ms,
            effective_time_ms=None,
            effective_time_parse_status="not_parsed_in_stage1_5b",
        )

        # Compute payload hash excluding article_payload_hash itself
        row_dict = dataclass_to_json_dict(article_row)
        del row_dict["article_payload_hash"]
        article_row.article_payload_hash = canonical_json_hash(row_dict)

        article_rows.append(article_row)

    return article_rows


def expand_symbol_event_rows(
    article_rows: List[ArticleEventRow], source_audit_decisions: Dict[str, str]
) -> List[SymbolEventRow]:
    symbol_rows = []
    for article_row in article_rows:
        for raw_symbol in article_row.symbols:
            base_asset, symbol, quote_asset = normalize_base_asset_symbol(raw_symbol)

            # symbol_event_id = sha256(article_event_id|symbol)
            id_str = f"{article_row.article_event_id}|{symbol}"
            symbol_event_id = hashlib.sha256(id_str.encode("utf-8")).hexdigest()

            symbol_row = SymbolEventRow(
                symbol_event_id=symbol_event_id,
                article_event_id=article_row.article_event_id,
                event_type=article_row.event_type,
                symbol=symbol,
                base_asset=base_asset,
                quote_asset=quote_asset,
                venue="binance",
                source_name=article_row.source_name,
                source_profile=article_row.source_profile,
                source_detail_url=article_row.source_detail_url,
                source_parent_url=article_row.source_url,
                title=article_row.title,
                source_published_at_ms=article_row.source_published_at_ms,
                event_time_ms=article_row.event_time_ms,
                notice_time_ms=article_row.notice_time_ms,
                effective_time_ms=None,
                effective_time_parse_status="not_parsed_in_stage1_5b",
                available_at_ms=article_row.available_at_ms,
                available_at_policy=article_row.available_at_policy,
                event_payload_hash="",  # placeholder
                source_quality="stage1_5a_passed_manual_reviewed_high_confidence",
                source_audit_decision="source_audit_passed",
                event_type_audit_decision=source_audit_decisions.get(
                    article_row.event_type, "source_audit_passed"
                ),
                stage1_5a_source_key="binance_official_announcements_like_rows_source",
                stage1_5a_review_path="docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-reviewed-high-confidence-source-audit-review_CN.md",
                stage1_5a_summary_path="data/external_signal_shadow/stage1_5a/binance_reviewed_high_confidence_source_audit_summary.json",
                manual_review_status=article_row.manual_review_status,
                symbol_normalization_method="base_asset_plus_usdt_assumption",
            )

            # Compute payload hash excluding event_payload_hash itself
            row_dict = dataclass_to_json_dict(symbol_row)
            del row_dict["event_payload_hash"]
            symbol_row.event_payload_hash = canonical_json_hash(row_dict)

            symbol_rows.append(symbol_row)

    return symbol_rows
