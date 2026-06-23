"""Semi-auto collector for Stage 1.5A external catalyst event candidates.

This script produces JSONL rows that can be fed into
run_stage1_5a_historical_event_source_audit.py. It is deliberately conservative:
rows are candidate events and must be manually reviewed before research use.
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import glob
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

CATALYST_EVENT_TYPES = {
    "exchange_delisting_notice",
    "futures_contract_launch",
    "margin_enablement",
    "trading_pair_removal",
    "trading_pair_addition_for_existing_liquid_asset",
    "major_exchange_status_event",
}

EXCLUDED_SYMBOL_WORDS = {
    "ADD",
    "ADDS",
    "AND",
    "BINANCE",
    "BOTS",
    "BSTOCKS",
    "BUY",
    "COIN",
    "CONTRACT",
    "CONTRACTS",
    "CONVERT",
    "CROSS",
    "CRYPTO",
    "DELIVERY",
    "DEVICES",
    "DELIST",
    "DELISTS",
    "EARN",
    "ETF",
    "EXCHANGE",
    "FUTURES",
    "INTEL",
    "ISHARES",
    "KOREA",
    "LAUNCH",
    "LIST",
    "LISTING",
    "LOAN",
    "MARGIN",
    "MARGINED",
    "MICRO",
    "MSCI",
    "MULTIPLE",
    "OKX",
    "ON",
    "PAIR",
    "PAIRS",
    "PERPETUAL",
    "PERP",
    "QUARTERLY",
    "SECURITIES",
    "SERVICES",
    "SOUTH",
    "SPOT",
    "STRATEGY",
    "TOKENIZED",
    "TRADFI",
    "TRADING",
    "TO",
    "USD",
    "USDC",
    "USDT",
    "WILL",
}

FORBIDDEN_OUTPUT_KEYS = {
    "api_key",
    "secret",
    "private_key",
    "wallet_seed",
    "mnemonic",
    "signed_tx",
    "raw_tx",
    "order_request",
    "swap_request",
    "transfer_request",
    "wallet_private_key",
    "tx_payload",
}


class CollectorError(RuntimeError):
    pass


def classify_event_type(title: str) -> str:
    text = title.lower()
    if "delist" in text or "trading pair removal" in text or "remove" in text and "trading" in text:
        return "exchange_delisting_notice"
    if "futures" in text and ("launch" in text or "list" in text) and (
        "perpetual" in text or "perp" in text or "usd-m" in text or "coin-m" in text
    ):
        return "futures_contract_launch"
    if "margin" in text and ("add" in text or "enable" in text or "launch" in text):
        return "margin_enablement"
    if "trading pair" in text and ("add" in text or "open" in text):
        return "trading_pair_addition_for_existing_liquid_asset"
    if "system maintenance" in text or "status" in text:
        return "major_exchange_status_event"
    return "unknown"


def extract_symbols_from_title(title: str) -> list[str]:
    symbols: list[str] = []

    for token in re.findall(r"\b([A-Z0-9]{2,15})(?:USDT|USDC|USD)\b", title.upper()):
        if token not in EXCLUDED_SYMBOL_WORDS and token not in symbols:
            symbols.append(token)
    if symbols:
        return symbols

    for token in re.findall(r"\(([A-Z0-9]{2,12})\)", title.upper()):
        if token not in EXCLUDED_SYMBOL_WORDS and token not in symbols:
            symbols.append(token)
    if symbols:
        return symbols

    for token in re.findall(r"\b[A-Z0-9]{2,12}\b", title.upper()):
        if not token or token in EXCLUDED_SYMBOL_WORDS:
            continue
        if token.isdigit():
            continue
        if token not in symbols:
            symbols.append(token)
    return symbols


def parse_time_to_ms(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        raw = int(value)
        return raw if raw > 10_000_000_000 else raw * 1000
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        raw = int(text)
        return raw if raw > 10_000_000_000 else raw * 1000

    normalized = text.replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "Published on %b %d, %Y",
        "Published on %B %d, %Y",
    ):
        try:
            parsed = dt.datetime.strptime(text, fmt)
            return calendar.timegm(parsed.timetuple()) * 1000
        except ValueError:
            pass
    try:
        parsed = dt.datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return calendar.timegm(parsed.timetuple()) * 1000
    except ValueError:
        return None


def _iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dicts(child)


def _article_url_from_binance_record(record: dict[str, Any]) -> str:
    url = str(record.get("url") or record.get("link") or record.get("articleUrl") or "").strip()
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return urllib.parse.urljoin("https://www.binance.com", url)
    code = str(record.get("code") or record.get("id") or "").strip()
    if code:
        return f"https://www.binance.com/en/support/announcement/{code}"
    return "https://www.binance.com/en/support/announcement"


def _build_row(
    *,
    title: str,
    published_ms: int | None,
    url: str,
    source_url: str,
    source_name: str,
) -> dict[str, Any] | None:
    event_type = classify_event_type(title)
    if event_type not in CATALYST_EVENT_TYPES:
        return None
    symbols = extract_symbols_from_title(title)
    if not symbols:
        return None
    row = {
        "title": title,
        "time": published_ms or 0,
        "symbol": symbols,
        "url": url,
        "source_url": source_url,
        "source_name": source_name,
        "event_type_candidate": event_type,
        "source_capture_method": "semi_auto_collector",
        "manual_review_required": True,
    }
    return {k: v for k, v in row.items() if k not in FORBIDDEN_OUTPUT_KEYS}


def collect_records_from_binance_cms_json(payload: dict[str, Any], source_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in _iter_dicts(payload):
        title = str(record.get("title") or record.get("name") or "").strip()
        if not title:
            continue
        published_ms = parse_time_to_ms(
            record.get("releaseDate")
            or record.get("publishDate")
            or record.get("publishedAt")
            or record.get("createdAt")
            or record.get("time")
        )
        url = _article_url_from_binance_record(record)
        row = _build_row(
            title=html.unescape(title),
            published_ms=published_ms,
            url=url,
            source_url=source_url,
            source_name="binance_official_announcements",
        )
        if row is not None:
            rows.append(row)
    return _dedupe_rows(rows)


def collect_records_from_html(html_text: str, source_url: str, source_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    time_candidates = re.findall(
        r"(?:Published on\s+)?(?:\d{4}-\d{2}-\d{2}|[A-Z][a-z]+\s+\d{1,2},\s+\d{4}|[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})",
        html_text,
    )
    fallback_time = parse_time_to_ms(time_candidates[0]) if time_candidates else None

    for href, label in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.I | re.S):
        title = re.sub(r"<[^>]+>", " ", label)
        title = re.sub(r"\s+", " ", html.unescape(title)).strip()
        if not title:
            continue
        url = urllib.parse.urljoin(source_url, html.unescape(href))
        row = _build_row(
            title=title,
            published_ms=fallback_time,
            url=url,
            source_url=source_url,
            source_name=source_name,
        )
        if row is not None:
            rows.append(row)
    return _dedupe_rows(rows)


def _dedupe_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = (row.get("title"), row.get("time"), tuple(row.get("symbol") or []), row.get("url"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _row_from_manual_item(item: dict[str, Any], source_url: str, source_name: str) -> dict[str, Any] | None:
    if FORBIDDEN_OUTPUT_KEYS.intersection(item.keys()):
        return None
    title = str(item.get("title") or "").strip()
    raw_symbol = item.get("symbol")
    row = _build_row(
        title=title,
        published_ms=parse_time_to_ms(
            item.get("time")
            or item.get("api_time")
            or item.get("published_at")
            or item.get("publishedAt")
        ),
        url=str(item.get("url") or ""),
        source_url=source_url,
        source_name=source_name,
    )
    if row and raw_symbol:
        row["symbol"] = raw_symbol if isinstance(raw_symbol, list) else [str(raw_symbol)]
    return row


def write_jsonl(rows: Iterable[dict[str, Any]], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deduped = _dedupe_rows(rows)
    with output_path.open("w", encoding="utf-8") as f:
        for row in deduped:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(deduped)


def fetch_url(url: str, timeout_sec: float = 15.0) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Stage1.5A semi-auto source audit collector",
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310 - readonly public fetch
        return resp.read()


def default_binance_cms_urls(page_count: int, page_size: int) -> list[str]:
    base_url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
    return [
        f"{base_url}?type=1&pageNo={page_no}&pageSize={page_size}"
        for page_no in range(1, page_count + 1)
    ]


def load_rows_from_source_file(path_pattern: str, source_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for file_name in sorted(glob.glob(path_pattern)):
        text = Path(file_name).read_text(encoding="utf-8")
        stripped = text.lstrip()
        nonempty_lines = [line for line in text.splitlines() if line.strip()]
        if len(nonempty_lines) > 1 and all(line.lstrip().startswith("{") for line in nonempty_lines):
            for line in nonempty_lines:
                item = json.loads(line)
                if isinstance(item, dict):
                    row = _row_from_manual_item(item, source_url=file_name, source_name=source_name)
                    if row:
                        rows.append(row)
        elif stripped.startswith("{"):
            payload = json.loads(text)
            if "title" in payload:
                row = _row_from_manual_item(payload, source_url=file_name, source_name=source_name)
                if row:
                    rows.append(row)
            else:
                rows.extend(collect_records_from_binance_cms_json(payload, source_url=file_name))
        elif stripped.startswith("["):
            for item in json.loads(text):
                if isinstance(item, dict):
                    row = _row_from_manual_item(item, source_url=file_name, source_name=source_name)
                    if row:
                        rows.append(row)
        else:
            rows.extend(collect_records_from_html(text, source_url=file_name, source_name=source_name))
    return _dedupe_rows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect semi-auto Stage 1.5A external catalyst candidate events into JSONL."
    )
    parser.add_argument("--source", choices=["binance_api", "binance_html", "okx_html", "source_file"], required=True)
    parser.add_argument("--source-url", action="append", default=[], help="Source URL to fetch. Can be repeated.")
    parser.add_argument("--source-file", help="Local HTML/JSON file glob to parse.")
    parser.add_argument("--output-jsonl", required=True, help="Output JSONL path for candidate events.")
    parser.add_argument("--raw-cache-dir", default="data/external_signal_shadow/stage1_5a/raw_candidate_sources")
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--sleep-sec", type=float, default=0.5)
    return parser.parse_args()


def _cache_raw(raw: bytes, raw_cache_dir: Path, source: str, source_url: str) -> None:
    raw_cache_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", urllib.parse.urlparse(source_url).netloc + urllib.parse.urlparse(source_url).path)[:120]
    ts = int(time.time() * 1000)
    (raw_cache_dir / f"{source}_{ts}_{safe_name}.raw").write_bytes(raw)


def main() -> None:
    args = parse_args()
    rows: list[dict[str, Any]] = []

    if args.source == "source_file":
        if not args.source_file:
            raise CollectorError("--source-file is required when --source=source_file")
        rows.extend(load_rows_from_source_file(args.source_file, source_name="manual_source_file"))
    else:
        urls = args.source_url
        if args.source == "binance_api" and not urls:
            urls = default_binance_cms_urls(args.max_pages, args.page_size)
        if not urls:
            raise CollectorError("--source-url is required for this source unless --source=binance_api")

        for url in urls:
            raw = fetch_url(url)
            _cache_raw(raw, Path(args.raw_cache_dir), args.source, url)
            text = raw.decode("utf-8", errors="replace")
            if args.source == "binance_api":
                rows.extend(collect_records_from_binance_cms_json(json.loads(text), source_url=url))
            elif args.source == "binance_html":
                rows.extend(collect_records_from_html(text, source_url=url, source_name="binance_official_announcements"))
            elif args.source == "okx_html":
                rows.extend(collect_records_from_html(text, source_url=url, source_name="okx_official_announcements"))
            time.sleep(args.sleep_sec)

    written = write_jsonl(rows, Path(args.output_jsonl))
    print(json.dumps({"output_jsonl": args.output_jsonl, "candidate_event_count": written}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"collector_error: {exc}", file=sys.stderr)
        raise
