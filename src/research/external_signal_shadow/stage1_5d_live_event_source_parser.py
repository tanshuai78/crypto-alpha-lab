import hashlib
import html
import json
import re
import unicodedata
from datetime import datetime, timezone

from configs import base


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


SYMBOL_EXTRACTION_VERSION = 3
PARSER_VERSION = "stage1_5d_symbol_extraction_v3"
LAUNCH_SCHEDULE_PARSER_VERSION = "stage1_5d_bapi_launch_schedule_v1"



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
        combined_text = "\n".join(snippets)[:100000]
        symbol_launch_times = extract_symbol_launch_times_ms(combined_text, exact_symbols)
        return {
            "symbols": exact_symbols,
            "symbol_extraction_source": "detail",
            "symbol_derivation_method": "none",
            "quote_derivation_source": None,
            "symbol_validation_status": "validated_by_exact_text",
            "symbol_launch_times_ms": symbol_launch_times,
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


def extract_contract_symbol_candidates_from_title(title: str, max_symbols: int) -> list[str]:
    if classify_event_type(title) != "futures_contract_launch":
        return []

    margin = re.search(r"(?:USDⓈ|USDS|USD)-Margined|(?:USDⓈ|USDS|USD)-M", title, re.IGNORECASE)
    perp = re.search(r"perpetual\s+contracts?", title, re.IGNORECASE)
    launch = re.search(r"will\s+launch|launch", title, re.IGNORECASE)
    if not margin or not perp or not launch:
        return []
    if margin.end() >= perp.start():
        return []

    segment = title[margin.end():perp.start()]
    tokens = re.findall(r"\b[A-Z][A-Z0-9]{1,29}\b", segment)
    out = []
    for token in tokens:
        if token in CONTRACT_SYMBOL_CANDIDATE_STOPWORDS:
            continue
        if token.isdigit():
            continue
        if re.fullmatch(r"\d{4}|\d{2}|\d{8}", token):
            continue
        out.append(token)
        if len(out) >= max_symbols:
            break
    return _dedupe(out)


def extract_symbol_candidates_from_title(title: str, max_symbols: int) -> dict:
    exact_symbols = extract_futures_launch_symbols(title)[:max_symbols]
    if exact_symbols:
        return {
            "symbols": exact_symbols,
            "symbol_extraction_source": "title",
            "symbol_derivation_method": "none",
            "quote_derivation_source": None,
            "symbol_validation_status": "validated_by_exact_text",
            "symbol_launch_times_ms": {},
        }

    raw_candidates = extract_contract_symbol_candidates_from_title(title, max_symbols)
    if raw_candidates:
        return {
            "symbols": raw_candidates,
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_derivation_method": "none",
            "quote_derivation_source": "exchange_info",
            "symbol_validation_status": "requires_exchange_info_validation",
            "symbol_launch_times_ms": {},
        }

    return {
        "symbols": [],
        "symbol_extraction_source": None,
        "symbol_derivation_method": None,
        "quote_derivation_source": None,
        "symbol_validation_status": None,
        "symbol_launch_times_ms": {},
    }


def _normalize_article_text(value: str) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


def _build_bapi_logical_lines(text_nodes: list[dict]) -> list[dict]:
    logical_lines = []
    line_index = 0
    for node_idx, node in enumerate(text_nodes):
        raw_text = node.get("text", "")
        if not raw_text:
            continue
        clean_node_text = re.sub(r"<(?:p|div|tr|br|li|h[1-6]|table|td|th)[^>]*>", "\n", raw_text, flags=re.IGNORECASE)
        clean_node_text = re.sub(r"<[^>]+>", " ", clean_node_text)

        for line in clean_node_text.splitlines():
            norm_line = _normalize_article_text(line)
            if not norm_line:
                continue
            logical_lines.append({
                "text": norm_line,
                "node_path": node.get("path", f"node_{node_idx}"),
                "node_order": node_idx,
                "line_index": line_index,
            })
            line_index += 1
    return logical_lines


def _parse_utc_time_str_to_ms(time_str: str) -> int | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*\([A-Z]+\)", time_str)
    if not match:
        return None
    try:
        dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def _extract_contract_symbols_from_line(text: str) -> list[str]:
    symbols = []
    for sym in re.findall(r"\b([A-Z0-9]{2,30}(?:USDT|USDC|USD1))\b", text):
        if sym in CONTRACT_SYMBOL_CANDIDATE_STOPWORDS or sym in BASE_ASSET_STOPWORDS:
            continue
        symbols.append(sym)
    return symbols


def _extract_launch_time_table_block(logical_lines: list[dict], max_symbols: int) -> dict | None:
    candidates = []
    for launch_idx, launch_line in enumerate(logical_lines):
        if not re.fullmatch(r"Launch\s+Time", launch_line["text"], re.IGNORECASE):
            continue

        header_idx = None
        for prev_idx in range(launch_idx - 1, max(-1, launch_idx - max_symbols - 4), -1):
            prev_text = logical_lines[prev_idx]["text"]
            if re.search(r"Perpetual\s+Contract", prev_text, re.IGNORECASE) and not _extract_contract_symbols_from_line(prev_text):
                header_idx = prev_idx
                break
        if header_idx is None:
            continue

        symbol_rows = []
        for prev in logical_lines[header_idx + 1:launch_idx]:
            for sym in _extract_contract_symbols_from_line(prev["text"]):
                symbol_rows.append((sym, prev))
                if len(symbol_rows) >= max_symbols:
                    break
            if len(symbol_rows) >= max_symbols:
                break

        if not symbol_rows:
            continue

        time_rows = []
        for nxt in logical_lines[launch_idx + 1:launch_idx + 1 + len(symbol_rows) + 3]:
            t_ms = _parse_utc_time_str_to_ms(nxt["text"])
            if t_ms is not None:
                time_rows.append((t_ms, nxt["text"], nxt))
                if len(time_rows) >= len(symbol_rows):
                    break

        if len(symbol_rows) != len(time_rows):
            continue

        symbols = _dedupe([sym for sym, _line in symbol_rows])
        if len(symbols) != len(symbol_rows):
            continue

        symbol_launch_times_ms = {}
        provenance = []
        for (sym, sym_line), (t_ms, t_text, time_line) in zip(symbol_rows, time_rows):
            symbol_launch_times_ms[sym] = t_ms
            provenance.append({
                "symbol": sym,
                "logical_block_id": f"bapi_launch_time_table_{launch_line['line_index']}",
                "symbol_node_path": sym_line["node_path"],
                "time_node_path": time_line["node_path"],
                "common_ancestor_path": launch_line["node_path"].rsplit(".", 1)[0],
                "raw_time_text": t_text,
                "timezone_text": "UTC",
                "pairing_method": "launch_time_table_column_pairing",
                "pairing_confidence": "high",
            })

        candidates.append({
            "symbols": symbols,
            "symbol_launch_times_ms": symbol_launch_times_ms,
            "candidate_provenance": provenance,
            "parser_status": "parsed",
            "consumable_event_allowed": True,
            "launch_time_resolution_status": "table_line_matched",
        })

    if not candidates:
        return None

    first = candidates[0]
    if len(candidates) > 1:
        duplicate_count = sum(
            1
            for candidate in candidates[1:]
            if candidate["symbols"] == first["symbols"]
            and candidate["symbol_launch_times_ms"] == first["symbol_launch_times_ms"]
        )
        if duplicate_count:
            return {
                "symbols": [],
                "symbol_launch_times_ms": {},
                "candidate_provenance": [],
                "parser_status": "launch_schedule_ambiguous",
                "consumable_event_allowed": False,
            }

    return first


def _extract_bapi_schedule_candidates(logical_lines: list[dict], max_symbols: int) -> dict:
    table_block = _extract_launch_time_table_block(logical_lines, max_symbols)
    if table_block is not None:
        return table_block

    symbols_found = []
    times_found = []

    for line in logical_lines:
        text = line["text"]
        if re.search(r"risk warning|disclaimer|footer|related articles", text, re.IGNORECASE):
            continue

        for sym in _extract_contract_symbols_from_line(text):
            symbols_found.append((sym, line))

        time_matches = re.finditer(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*\([A-Z]+\)", text)
        for tm in time_matches:
            dt_str = tm.group(1)
            full_t = tm.group(0)
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                t_ms = int(dt.timestamp() * 1000)
                times_found.append((t_ms, full_t, line))
            except Exception:
                pass



    unique_symbols = list(dict.fromkeys([s[0] for s in symbols_found]))

    # Check for duplicate responsive rendering tables
    if len(symbols_found) > len(unique_symbols):
        if len(symbols_found) % len(unique_symbols) == 0:
            if len(times_found) == len(symbols_found):
                # Duplicate table in HTML -> ambiguous
                return {
                    "symbols": [],
                    "symbol_launch_times_ms": {},
                    "candidate_provenance": [],
                    "parser_status": "launch_schedule_ambiguous",
                    "consumable_event_allowed": False,
                }

    if len(unique_symbols) > 0 and len(times_found) > 0:
        if len(unique_symbols) == len(times_found):
            symbol_launch_times_ms = {}
            candidate_provenance = []
            for idx, sym in enumerate(unique_symbols):
                t_ms, t_text, t_line = times_found[idx]
                s_sym, s_line = next(s for s in symbols_found if s[0] == sym)
                symbol_launch_times_ms[sym] = t_ms
                candidate_provenance.append({
                    "symbol": sym,
                    "logical_block_id": "bapi_schedule_block",
                    "symbol_node_path": s_line["node_path"],
                    "time_node_path": t_line["node_path"],
                    "common_ancestor_path": "table_or_list",
                    "raw_time_text": t_text,
                    "timezone_text": "UTC",
                    "pairing_method": "schedule_index_pairing",
                    "pairing_confidence": "high",
                })
            return {
                "symbols": unique_symbols,
                "symbol_launch_times_ms": symbol_launch_times_ms,
                "candidate_provenance": candidate_provenance,
                "parser_status": "parsed",
                "consumable_event_allowed": True,
            }
        else:
            return {
                "symbols": [],
                "symbol_launch_times_ms": {},
                "candidate_provenance": [],
                "parser_status": "launch_schedule_ambiguous",
                "consumable_event_allowed": False,
            }

    return {
        "symbols": [],
        "symbol_launch_times_ms": {},
        "candidate_provenance": [],
        "parser_status": "no_symbols",
        "consumable_event_allowed": False,
    }





def extract_symbol_candidates_from_bapi_article_payload(
    payload: dict,
    max_symbols: int = 30,
    title: str | None = None,
) -> dict:
    if not isinstance(payload, dict):
        return {
            "symbols": [],
            "symbol_extraction_source": "none",
            "symbol_parse_status": "not_attempted",
            "symbol_parse_failed_reason": "bapi_body_schema_drift",
            "extracted_text": "",
            "symbol_launch_times_ms": {},
            "parser_status": "no_symbols",
            "consumable_event_allowed": False,
            "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
        }

    data = payload.get("data")
    if not isinstance(data, dict):
        return {
            "symbols": [],
            "symbol_extraction_source": "none",
            "symbol_parse_status": "not_attempted",
            "symbol_parse_failed_reason": "bapi_body_schema_drift",
            "extracted_text": "",
            "symbol_launch_times_ms": {},
            "parser_status": "no_symbols",
            "consumable_event_allowed": False,
            "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
        }

    body = data.get("body") or data.get("contentJson")
    if not body:
        return {
            "symbols": [],
            "symbol_extraction_source": "none",
            "symbol_parse_status": "not_attempted",
            "symbol_parse_failed_reason": "bapi_body_missing",
            "extracted_text": "",
            "symbol_launch_times_ms": {},
            "parser_status": "no_symbols",
            "consumable_event_allowed": False,
            "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
        }

    tree = None
    if isinstance(body, dict) or isinstance(body, list):
        tree = body
    elif isinstance(body, str):
        body_str = body.strip()
        if body_str.startswith("{") or body_str.startswith("["):
            try:
                tree = json.loads(body_str)
            except Exception:
                tree = None

    max_json_depth = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_JSON_DEPTH", 32)
    max_node_count = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_NODE_COUNT", 50_000)
    max_extracted_text_chars = getattr(
        base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_EXTRACTED_TEXT_CHARS", 300_000
    )

    if tree is None and isinstance(body, str) and re.search(r"<[a-zA-Z]+[^>]*>", body):
        cleaned_text = re.sub(r"<[^>]+>", " ", body)
        if len(cleaned_text) > max_extracted_text_chars:
            return {
                "symbols": [],
                "symbol_extraction_source": "none",
                "symbol_parse_status": "not_attempted",
                "symbol_parse_failed_reason": "bapi_body_extracted_text_too_large",
                "extracted_text": "",
                "symbol_launch_times_ms": {},
                "parser_status": "no_symbols",
                "consumable_event_allowed": False,
                "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
            }
        text_nodes = [{"path": "body_html", "text": body}]
    elif tree is not None:
        text_nodes = []
        node_count = 0
        extracted_chars = 0
        stack = [(tree, "root", 1)]
        while stack:
            obj, path, depth = stack.pop()
            node_count += 1
            if depth > max_json_depth:
                return {
                    "symbols": [],
                    "symbol_extraction_source": "none",
                    "symbol_parse_status": "not_attempted",
                    "symbol_parse_failed_reason": "bapi_body_json_depth_exceeded",
                    "extracted_text": "",
                    "symbol_launch_times_ms": {},
                    "parser_status": "no_symbols",
                    "consumable_event_allowed": False,
                    "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
                }
            if node_count > max_node_count:
                return {
                    "symbols": [],
                    "symbol_extraction_source": "none",
                    "symbol_parse_status": "not_attempted",
                    "symbol_parse_failed_reason": "bapi_body_json_node_count_exceeded",
                    "extracted_text": "",
                    "symbol_launch_times_ms": {},
                    "parser_status": "no_symbols",
                    "consumable_event_allowed": False,
                    "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
                }
            if isinstance(obj, dict):
                for text_key in ("text", "content"):
                    text_value = obj.get(text_key)
                    if isinstance(text_value, str):
                        extracted_chars += len(text_value)
                        if extracted_chars > max_extracted_text_chars:
                            return {
                                "symbols": [],
                                "symbol_extraction_source": "none",
                                "symbol_parse_status": "not_attempted",
                                "symbol_parse_failed_reason": "bapi_body_extracted_text_too_large",
                                "extracted_text": "",
                                "symbol_launch_times_ms": {},
                                "parser_status": "no_symbols",
                                "consumable_event_allowed": False,
                                "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
                            }
                        text_nodes.append({"path": f"{path}.{text_key}", "text": text_value})
                for k, v in reversed(list(obj.items())):
                    if k not in ("text", "content"):
                        stack.append((v, f"{path}.{k}", depth + 1))
            elif isinstance(obj, list):
                for idx in range(len(obj) - 1, -1, -1):
                    stack.append((obj[idx], f"{path}[{idx}]", depth + 1))
    else:
        return {
            "symbols": [],
            "symbol_extraction_source": "none",
            "symbol_parse_status": "not_attempted",
            "symbol_parse_failed_reason": "bapi_body_schema_drift",
            "extracted_text": "",
            "symbol_launch_times_ms": {},
            "parser_status": "no_symbols",
            "consumable_event_allowed": False,
            "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
        }

    logical_lines = _build_bapi_logical_lines(text_nodes)
    full_extracted_text = "\n".join(line["text"] for line in logical_lines)

    # First try logical schedule parser (table / separated)
    schedule_res = _extract_bapi_schedule_candidates(logical_lines, max_symbols)
    if schedule_res["parser_status"] == "launch_schedule_ambiguous":
        return {
            "symbols": [],
            "symbol_extraction_source": "bapi_article_body",
            "evidence_source": "official_article_body_confirmed",
            "detail_transport": "bapi_article_detail_query",
            "content_provenance": "binance_official_announcement",
            "source_transport": "binance_first_party_public_web_bapi_undocumented",
            "symbol_derivation_method": "none",
            "quote_derivation_source": None,
            "symbol_validation_status": "ambiguous_schedule",
            "extracted_text": full_extracted_text,
            "symbol_launch_times_ms": {},
            "candidate_provenance": [],
            "parser_status": "launch_schedule_ambiguous",
            "consumable_event_allowed": False,
            "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
        }

    if schedule_res["symbols"]:
        return {
            "symbols": schedule_res["symbols"],
            "symbol_extraction_source": "bapi_article_body",
            "evidence_source": "official_article_body_confirmed",
            "detail_transport": "bapi_article_detail_query",
            "content_provenance": "binance_official_announcement",
            "source_transport": "binance_first_party_public_web_bapi_undocumented",
            "symbol_derivation_method": "none",
            "quote_derivation_source": None,
            "symbol_validation_status": "validated_by_exact_text",
            "extracted_text": full_extracted_text,
            "symbol_launch_times_ms": schedule_res["symbol_launch_times_ms"],
            "candidate_provenance": schedule_res["candidate_provenance"],
            "launch_time_resolution_status": schedule_res.get("launch_time_resolution_status", "table_line_matched"),
            "parser_status": "parsed",
            "consumable_event_allowed": True,
            "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
        }


    # Fallback to segment text node parsing (v2 behavior)
    extracted_symbols = []
    candidate_provenance = []
    seen_symbols = set()

    for node in text_nodes:
        if len(extracted_symbols) >= max_symbols:
            break

        node_text = node["text"]
        segments = re.split(r"(?<=[.!?\n])\s+", node_text)

        for segment in segments:
            if len(extracted_symbols) >= max_symbols:
                break

            if re.search(r"risk warning|disclaimer|footer|related articles", segment, re.IGNORECASE):
                continue

            if not re.search(r"launch|will\s+launch|perpetual\s+contracts?|usdⓈ-margined|usd-margined|usds-margined", segment, re.IGNORECASE):
                continue

            matches = re.findall(r"\b([A-Z0-9]{2,30}USDT|[A-Z0-9]{2,30}USDC|[A-Z0-9]{2,30}USD1)\b", segment)
            for m in matches:
                if len(extracted_symbols) >= max_symbols:
                    break
                if m not in seen_symbols:
                    seen_symbols.add(m)
                    extracted_symbols.append(m)
                    candidate_provenance.append({
                        "symbol": m,
                        "body_node_path": node["path"],
                        "event_phrase_match": True,
                        "local_text_span": segment[:200],
                        "segment_start": 0,
                        "segment_end": len(segment),
                        "event_phrase_distance": 0,
                        "parser_context": "bapi_text_node",
                        "section_classification": "launch_announcement_body",
                    })

    if not extracted_symbols:
        return {
            "symbols": [],
            "symbol_extraction_source": "none",
            "symbol_derivation_method": None,
            "quote_derivation_source": None,
            "symbol_validation_status": None,
            "extracted_text": full_extracted_text,
            "symbol_launch_times_ms": {},
            "parser_status": "no_symbols",
            "consumable_event_allowed": False,
            "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
        }

    launch_times = extract_symbol_launch_times_ms(full_extracted_text, extracted_symbols)

    return {
        "symbols": extracted_symbols,
        "symbol_extraction_source": "bapi_article_body",
        "evidence_source": "official_article_body_confirmed",
        "detail_transport": "bapi_article_detail_query",
        "content_provenance": "binance_official_announcement",
        "source_transport": "binance_first_party_public_web_bapi_undocumented",
        "symbol_derivation_method": "none",
        "quote_derivation_source": None,
        "symbol_validation_status": "validated_by_exact_text",
        "extracted_text": full_extracted_text,
        "symbol_launch_times_ms": launch_times,
        "candidate_provenance": candidate_provenance,
        "parser_status": "parsed",
        "consumable_event_allowed": True,
        "launch_schedule_parser_version": LAUNCH_SCHEDULE_PARSER_VERSION,
    }
