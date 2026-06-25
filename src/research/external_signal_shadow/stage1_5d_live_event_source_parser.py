import hashlib
import json
import re


def classify_event_type(title: str) -> str:
    title_lower = title.lower()
    if (
        "futures" in title_lower
        and "launch" in title_lower
        and "margined" in title_lower
        and "perpetual" in title_lower
    ):
        return "futures_contract_launch"
    return "ignored_event_type"


def extract_futures_launch_symbols(title: str) -> list[str]:
    # Matches symbols like ABCUSDT or XYZUSDC (uppercase word characters ending with USDT or USDC)
    matches = re.findall(r"\b([A-Z0-9]+USDT|[A-Z0-9]+USDC)\b", title)
    # Deduplicate while preserving order
    return list(dict.fromkeys(matches))


def extract_base_asset(symbol: str) -> str:
    for quote in ("USDT", "USDC"):
        if symbol.endswith(quote):
            return symbol[: -len(quote)]
    return symbol


def build_stable_event_key(source_article_id: str, symbol: str) -> str:
    return f"binance_{source_article_id}_{symbol}"


def build_event_revision_hash(row: dict) -> str:
    serialized = json.dumps(row, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def dedupe_events(rows: list[dict]) -> list[dict]:
    seen_ids = set()
    seen_urls = set()
    unique_rows = []
    for row in rows:
        art_id = row.get("source_article_id")
        url = row.get("source_detail_url_normalized")

        is_dup = False
        if art_id and art_id in seen_ids:
            is_dup = True
        if url and url in seen_urls:
            is_dup = True

        if not is_dup:
            if art_id:
                seen_ids.add(art_id)
            if url:
                seen_urls.add(url)
            unique_rows.append(row)
    return unique_rows


def normalize_live_event(
    raw: dict,
    source_parent_url: str,
    detected_at_ms: int,
    source_published_at_ms: int,
    source_published_at_ms_confidence: str,
) -> dict:
    code = raw.get("code") or ""
    title = raw.get("title") or ""

    event_type = classify_event_type(title)
    symbols = tuple(extract_futures_launch_symbols(title))
    base_assets = tuple(extract_base_asset(s) for s in symbols)

    source_detail_url_normalized = f"{source_parent_url.rstrip('/')}/{code}"

    symbol_part = symbols[0] if symbols else "UNKNOWN"
    stable_key = build_stable_event_key(code, symbol_part)

    event_id = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()

    return {
        "event_id": event_id,
        "event_type": event_type,
        "source_name": "binance_official_announcements",
        "source_profile": "binance_official_announcements_like_rows",
        "title": title,
        "symbols": symbols,
        "base_assets": base_assets,
        "detected_at_ms": detected_at_ms,
        "available_at_ms": detected_at_ms,
        "source_article_id": code,
        "source_detail_url_normalized": source_detail_url_normalized,
        "source_published_at_ms": source_published_at_ms,
        "source_published_at_ms_confidence": source_published_at_ms_confidence,
        "historical_delay_comparison_allowed": source_published_at_ms_confidence != "low",
        "stable_event_key": stable_key,
        "stage1_5c_research_context_label": "futures_launch_long_attention_12h_close_price_replay_only",
        "trade_signal_allowed": False,
        "replay_context_label_only": True,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }


def parse_binance_announcement_payload(payload: dict) -> dict:
    source_format_drift = False
    source_format_drift_count = 0
    schema_parse_error = False

    if not isinstance(payload, dict) or "data" not in payload:
        source_format_drift = True
        source_format_drift_count = 1
        return {
            "events": [],
            "source_format_drift": source_format_drift,
            "source_format_drift_count": source_format_drift_count,
            "schema_parse_error": schema_parse_error,
        }

    data = payload["data"]
    if not isinstance(data, dict) or "catalogs" not in data:
        source_format_drift = True
        source_format_drift_count = 1
        return {
            "events": [],
            "source_format_drift": source_format_drift,
            "source_format_drift_count": source_format_drift_count,
            "schema_parse_error": schema_parse_error,
        }

    catalogs = data["catalogs"]
    if not isinstance(catalogs, list):
        schema_parse_error = True
        return {
            "events": [],
            "source_format_drift": source_format_drift,
            "source_format_drift_count": source_format_drift_count,
            "schema_parse_error": schema_parse_error,
        }

    if len(catalogs) == 0:
        source_format_drift = True
        source_format_drift_count = 1
        return {
            "events": [],
            "source_format_drift": source_format_drift,
            "source_format_drift_count": source_format_drift_count,
            "schema_parse_error": schema_parse_error,
        }

    catalog = catalogs[0]
    if not isinstance(catalog, dict) or "articles" not in catalog:
        source_format_drift = True
        source_format_drift_count = 1
        return {
            "events": [],
            "source_format_drift": source_format_drift,
            "source_format_drift_count": source_format_drift_count,
            "schema_parse_error": schema_parse_error,
        }

    articles = catalog["articles"]
    if not isinstance(articles, list):
        schema_parse_error = True
        return {
            "events": [],
            "source_format_drift": source_format_drift,
            "source_format_drift_count": source_format_drift_count,
            "schema_parse_error": schema_parse_error,
        }

    return {
        "events": articles,
        "source_format_drift": False,
        "source_format_drift_count": 0,
        "schema_parse_error": False,
    }
