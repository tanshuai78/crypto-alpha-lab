import hashlib
import json
import re
from datetime import datetime, timezone



def classify_event_type(title: str) -> str:
    title_lower = title.lower()
    has_usd_m_margin_context = bool(
        re.search(r"(?:USDⓈ|USDS|USD)-Margined|(?:USDⓈ|USDS|USD)-M\b", title, re.IGNORECASE)
    )
    if (
        "futures" in title_lower
        and "launch" in title_lower
        and ("margined" in title_lower or has_usd_m_margin_context)
        and "perpetual" in title_lower
    ):
        return "futures_contract_launch"
    return "ignored_event_type"


def extract_futures_launch_symbols(title: str) -> list[str]:
    # Matches symbols like ABCUSDT or XYZUSDC (uppercase word characters ending with USDT or USDC)
    matches = re.findall(r"\b([A-Z0-9]+USDT|[A-Z0-9]+USDC)\b", title)
    # Deduplicate while preserving order
    return list(dict.fromkeys(matches))


BASE_ASSET_STOPWORDS = {
    "BINANCE", "FUTURES", "WILL", "LAUNCH", "USD", "USDT", "USDC", "USDS",
    "MARGINED", "PERPETUAL", "CONTRACT", "CONTRACTS", "AND", "MULTIPLE",
    "TRADFI", "TIME", "SETTLEMENT", "ASSET", "UNDERLYING", "MARGIN", "TIER",
    "WARNING"
}


CONTRACT_SYMBOL_CANDIDATE_STOPWORDS = BASE_ASSET_STOPWORDS | {
    "LAUNCH", "TIME", "UNDERLYING", "PROJECT", "INFO", "TICK", "SIZE", "MINIMUM",
    "NOTIONAL", "VALUE", "CAPPED", "FUNDING", "RATE", "FEE", "FREQUENCY",
    "EVERY", "EIGHT", "HOURS", "MAXIMUM", "LEVERAGE", "TRADING", "MODE",
    "SUPPORTED", "UNITED", "STABLES", "UTC"
}



def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _has_usds_margined_launch_context(text: str) -> bool:
    margin = re.search(r'(?:USDⓈ|USDS|USD)-Margined|(?:USDⓈ|USDS|USD)-M', text, re.IGNORECASE)
    perp = re.search(r'perpetual\s+contracts?', text, re.IGNORECASE)
    launch = re.search(r'launch|will\s+launch', text, re.IGNORECASE)
    return bool(margin and perp and launch)


def _find_launch_candidate_window(text: str) -> str | None:
    margin_matches = list(re.finditer(r'(?:USDⓈ|USDS|USD)-Margined|(?:USDⓈ|USDS|USD)-M', text, re.IGNORECASE))
    perp_matches = list(re.finditer(r'perpetual\s+contracts?', text, re.IGNORECASE))
    launch_matches = list(re.finditer(r'launch|will\s+launch', text, re.IGNORECASE))
    if not margin_matches or not perp_matches or not launch_matches:
        return None

    for m in margin_matches:
        for p in perp_matches:
            start = min(m.start(), p.start())
            end = max(m.end(), p.end())
            if (end - start) <= 500:
                for lm in launch_matches:
                    window_start = min(m.start(), p.start(), lm.start())
                    window_end = max(m.end(), p.end(), lm.end())
                    if (window_end - window_start) <= 500:
                        return text[window_start:window_end]
    return None


def _extract_between_margin_and_perpetual(text: str) -> str:
    m = re.search(r'(?:USDⓈ|USDS|USD)-Margined|(?:USDⓈ|USDS|USD)-M', text, re.IGNORECASE)
    p = re.search(r'perpetual\s+contracts?', text, re.IGNORECASE)
    if m and p:
        if m.end() < p.start():
            return text[m.end():p.start()]
        elif p.end() < m.start():
            return text[p.end():m.start()]
    return ""


def extract_futures_launch_base_assets(text: str, force_classify: bool = True) -> list[str]:
    if force_classify and classify_event_type(text) != "futures_contract_launch":
        return []
    if extract_futures_launch_symbols(text):
        return []
    window = _find_launch_candidate_window(text)
    if not window:
        return []

    segment = _extract_between_margin_and_perpetual(window)
    tokens = re.findall(r"\b[A-Z][A-Z0-9]{1,19}\b", segment)
    return _dedupe([t for t in tokens if t not in BASE_ASSET_STOPWORDS])


def _find_contract_symbol_candidate_windows(text: str) -> list[str]:
    keywords = [
        r"(?:USDⓈ|USDS|USD)-Margined",
        r"(?:USDⓈ|USDS|USD)-M",
        r"Perpetual\s+Contracts?",
        r"Settlement\s+Asset",
    ]
    pattern = "|".join(keywords)
    windows = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        start = max(0, m.start() - 200)
        end = min(len(text), m.end() + 200)
        windows.append(text[start:end])
    return windows



def extract_contract_symbol_candidates_from_detail_text(text: str, max_symbols: int) -> list[str]:
    # 1. Locate the launch context window first
    window = _find_launch_candidate_window(text)
    if not window:
        return []
    
    # 2. Filter out lines containing "warning" or "risk" from the window
    clean_lines = []
    for line in window.splitlines():
        if "warning" in line.lower() or "risk" in line.lower():
            continue
        clean_lines.append(line)
    clean_window = "\n".join(clean_lines)

    windows = _find_contract_symbol_candidate_windows(clean_window)
    out = []
    seen = set()
    for w in windows:
        for token in re.findall(r"\b[A-Z][A-Z0-9]{1,29}\b", w):
            if token in CONTRACT_SYMBOL_CANDIDATE_STOPWORDS:
                continue
            if token.isdigit():
                continue
            if token not in seen:
                seen.add(token)
                out.append(token)
            if len(out) >= max_symbols:
                return out
    return out



def extract_symbol_launch_times_ms(text: str, symbols: list[str]) -> dict[str, int]:
    out = {}
    matches = list(re.finditer(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", text))
    for symbol in symbols:
        symbol_matches = list(re.finditer(rf"\b{re.escape(symbol)}\b", text))
        best_dt_ms = None
        min_dist = 999999
        for sm in symbol_matches:
            for dm in matches:
                dist = abs(dm.start() - sm.start())
                if dist < min_dist and dist < 150:
                    dt_str = f"{dm.group(1)}T{dm.group(2)}:00"
                    try:
                        dt = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
                        best_dt_ms = int(dt.timestamp() * 1000)
                        min_dist = dist
                    except ValueError:
                        continue
        if best_dt_ms is not None:
            out[symbol] = best_dt_ms
    return out

def derive_symbol_candidates_from_base_assets_in_launch_context(text: str, max_symbols: int) -> dict:
    bases = extract_futures_launch_base_assets(text)
    symbols = [f"{base}USDT" for base in bases[:max_symbols]]
    return {
        "symbols": symbols,
        "symbol_extraction_source": "title_base_asset_derived" if symbols else None,
        "symbol_derivation_method": "base_asset_plus_quote" if symbols else None,
        "quote_derivation_source": "explicit_usdt_context" if symbols else None,
        "symbol_validation_status": "unverified" if symbols else None,
    }


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


SYMBOL_EXTRACTION_VERSION = 2
PARSER_VERSION = "stage1_5d_symbol_extraction_v2"


def normalize_live_event(
    raw: dict,
    source_parent_url: str,
    detected_at_ms: int,
    source_published_at_ms: int,
    source_published_at_ms_confidence: str,
    symbols_override: list[str] | tuple[str, ...] | None = None,
    extraction_metadata: dict | None = None,
) -> dict:
    code = raw.get("code") or ""
    title = raw.get("title") or ""

    event_type = classify_event_type(title)

    if symbols_override is not None:
        symbols = tuple(symbols_override)
    else:
        symbols = tuple(extract_futures_launch_symbols(title))

    base_assets = tuple(extract_base_asset(s) for s in symbols)

    source_detail_url_normalized = f"{source_parent_url.rstrip('/')}/{code}"

    if len(symbols) == 0:
        stable_key = f"binance_{code}_UNKNOWN"
        event_id = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
    elif len(symbols) == 1:
        stable_key = f"binance_{code}_{symbols[0]}"
        event_id = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
    else:
        stable_key = f"binance_{code}_MULTI"
        event_id = hashlib.sha256(f"{stable_key}|{','.join(sorted(symbols))}".encode("utf-8")).hexdigest()

    # Default metadata
    meta = {
        "symbol_extraction_source": "title" if symbols else "none",
        "detail_fetch_attempted": False,
        "detail_fetch_status": "not_needed",
        "symbol_parse_failed_reason": None if symbols else "symbol_missing_no_detail_attempted",
        "symbol_parse_status": "parsed" if symbols else "terminal_failed",
        "parser_version": PARSER_VERSION,
        "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
    }
    if extraction_metadata:
        # Merge, but preserve version fields
        meta.update(extraction_metadata)
        meta["parser_version"] = PARSER_VERSION
        meta["symbol_extraction_version"] = SYMBOL_EXTRACTION_VERSION

    result = {
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
    result.update(meta)
    return result


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


def extract_symbol_candidates_from_detail_payload(payload: object, max_symbols: int, title: str | None = None) -> dict:
    snippets = []

    def _walk(obj: object) -> None:
        if isinstance(obj, str):
            snippets.append(obj)
        elif isinstance(obj, dict):
            for val in obj.values():
                _walk(val)
        elif isinstance(obj, (list, tuple, set)):
            for val in obj:
                _walk(val)

    _walk(payload)

    if title:
        snippets.insert(0, title)

    # 1. Exact matches of USDT/USDC symbols (preferred)
    exact_symbols = []
    seen = set()
    for s in snippets:
        if len(exact_symbols) >= max_symbols:
            break
        bounded_s = s[:100000]
        matches = re.findall(r"\b([A-Z0-9]{2,30}USDT|[A-Z0-9]{2,30}USDC)\b", bounded_s)
        for m in matches:
            if len(exact_symbols) >= max_symbols:
                break
            if m not in seen:
                seen.add(m)
                exact_symbols.append(m)

    if exact_symbols:
        return {
            "symbols": exact_symbols,
            "symbol_extraction_source": "detail",
            "symbol_derivation_method": "none",
            "quote_derivation_source": None,
            "symbol_validation_status": "validated_by_exact_text",
        }

    # 1.5 Contract-symbol candidates (e.g. BTCU, ETHU)
    combined_text = "\n".join(snippets)[:100000]
    contract_candidates = extract_contract_symbol_candidates_from_detail_text(combined_text, max_symbols)
    if contract_candidates:
        symbol_launch_times = extract_symbol_launch_times_ms(combined_text, contract_candidates)
        return {
            "symbols": contract_candidates,
            "symbol_extraction_source": "detail_contract_symbol",
            "symbol_derivation_method": "none",
            "quote_derivation_source": None,
            "symbol_validation_status": "requires_exchange_info_validation",
            "symbol_launch_times_ms": symbol_launch_times,
        }


    # 2. Base asset derivation fallback
    derived_symbols = []
    seen_derived = set()
    for s in snippets:
        if len(derived_symbols) >= max_symbols:
            break
        window = _find_launch_candidate_window(s[:100000])
        if window:
            bases = extract_futures_launch_base_assets(window, force_classify=False)
            for b in bases:
                sym = f"{b}USDT"
                if len(derived_symbols) >= max_symbols:
                    break
                if sym not in seen_derived:
                    seen_derived.add(sym)
                    derived_symbols.append(sym)

    if derived_symbols:
        return {
            "symbols": derived_symbols,
            "symbol_extraction_source": "detail_base_asset_derived",
            "symbol_derivation_method": "base_asset_plus_quote",
            "quote_derivation_source": "explicit_usdt_context",
            "symbol_validation_status": "unverified",
        }

    return {
        "symbols": [],
        "symbol_extraction_source": "none",
        "symbol_derivation_method": None,
        "quote_derivation_source": None,
        "symbol_validation_status": None,
    }


def extract_symbols_from_detail_payload(payload: object, max_symbols: int) -> list[str]:
    """Extract futures contract symbols from nested Binance detail payload or raw text."""
    res = extract_symbol_candidates_from_detail_payload(payload, max_symbols)
    return res["symbols"]
