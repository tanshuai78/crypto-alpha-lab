import calendar
import datetime
import hashlib
import json
import re
from typing import Dict, List, Tuple

from configs import base
from src.research.external_signal_shadow.stage1_5a_source_audit_models import (
    ExternalSignalEventType,
    NormalizedExternalEvent,
    RawSourcePayload,
    SourceProfile,
    TimestampQuality,
)


def extract_from_html_profile(html_str: str, profile: str) -> List[dict]:
    # Extract title from <h1>, <div class="title"> or similar
    title_match = re.search(
        r'(?:class="title"|<h1>)(.*?)(?:</div>|</h1>)', html_str, re.IGNORECASE
    )
    title = title_match.group(1).strip() if title_match else ""

    # Extract time pattern YYYY-MM-DD HH:MM:SS
    time_match = re.search(r"(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})", html_str)
    time_str = time_match.group(1) if time_match else ""

    # Extract href
    url_match = re.search(r'href="(.*?)"', html_str)
    url = url_match.group(1) if url_match else ""

    if not title:
        return []

    published_ms = None
    if time_str:
        try:
            dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            published_ms = int(calendar.timegm(dt.timetuple()) * 1000)
        except Exception:
            pass

    # Extract base asset candidates (uppercase words 2-7 chars)
    symbols = []
    words = re.findall(r"\b[A-Z]{2,7}\b", title)
    for w in words:
        if w not in (
            "BINANCE",
            "OKX",
            "WILL",
            "LIST",
            "DELIST",
            "FUTURES",
            "USD",
            "USDT",
            "AND",
            "ON",
            "TRADING",
            "PAIRS",
        ):
            symbols.append(w)

    if not symbols:
        # Check in HTML body text
        body_words = re.findall(r"\b[A-Z]{2,7}\b", html_str)
        for w in body_words:
            if (
                w
                not in (
                    "BINANCE",
                    "OKX",
                    "WILL",
                    "LIST",
                    "DELIST",
                    "FUTURES",
                    "USD",
                    "USDT",
                    "HTML",
                    "BODY",
                    "DIV",
                    "CLASS",
                    "TIME",
                    "HREF",
                    "AND",
                    "ON",
                )
                and w not in symbols
            ):
                symbols.append(w)

    return [{"title": title, "published_ms": published_ms, "url": url, "symbols": symbols}]


def parse_row_by_profile(payload_str: str, profile: str) -> Tuple[List[dict], int, int]:
    records = []
    disagreement_count = 0
    drift_count = 0

    if profile in (SourceProfile.BINANCE_HTML.value, SourceProfile.OKX_HTML.value):
        extracted = extract_from_html_profile(payload_str, profile)
        if not extracted:
            drift_count += 1
        for rec in extracted:
            # HTML time quality is medium
            rec["source_timestamp_quality"] = TimestampQuality.MEDIUM.value
            rec["disagreement"] = False
            records.append(rec)
    else:
        # JSON or JSONL
        lines = payload_str.strip().split("\n")
        for line in lines:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue

            title = data.get("title", "")
            url = data.get("url", "")

            # Detect disagreement
            disagreement = False
            api_time = data.get("api_time") or data.get("time")
            html_time = data.get("html_time")
            if api_time and html_time and api_time != html_time:
                disagreement = True
                disagreement_count += 1

            published_ms = api_time or html_time
            time_quality = TimestampQuality.HIGH.value if api_time else TimestampQuality.MEDIUM.value
            if not published_ms:
                time_quality = TimestampQuality.LOW.value

            # Extract symbols
            symbol_field = data.get("symbol", "")
            symbols = []
            if isinstance(symbol_field, list):
                symbols = symbol_field
            elif isinstance(symbol_field, str) and symbol_field:
                symbols = [s.strip() for s in re.split(r",", symbol_field)]
            else:
                # Find in title
                words = re.findall(r"\b[A-Z]{2,7}\b", title)
                for w in words:
                    if w not in (
                        "BINANCE",
                        "OKX",
                        "WILL",
                        "LIST",
                        "DELIST",
                        "FUTURES",
                        "USD",
                        "USDT",
                        "NEW",
                        "COIN",
                        "LAUNCH",
                    ):
                        symbols.append(w)

            records.append(
                {
                    "title": title,
                    "published_ms": published_ms,
                    "url": url,
                    "symbols": symbols,
                    "disagreement": disagreement,
                    "source_timestamp_quality": time_quality,
                    "raw_data": data,
                }
            )

    return records, disagreement_count, drift_count


def normalize_payload(
    raw_payload: RawSourcePayload,
) -> Tuple[List[NormalizedExternalEvent], Dict]:
    metrics = {
        "timestamp_source_disagreement_count": 0,
        "source_format_drift_count": 0,
        "schema_quarantine_count": 0,
    }

    try:
        payload_str = raw_payload.raw_payload_bytes.decode("utf-8", errors="replace")
    except Exception:
        metrics["source_format_drift_count"] += 1
        return [], metrics

    records, disagreement_count, drift_count = parse_row_by_profile(
        payload_str, raw_payload.source_profile
    )
    metrics["timestamp_source_disagreement_count"] += disagreement_count
    metrics["source_format_drift_count"] += drift_count

    events = []
    raw_hash = hashlib.sha256(raw_payload.raw_payload_bytes).hexdigest()

    for rec in records:
        title = rec["title"]
        symbols = rec["symbols"] or [""]

        # 1. Map event type
        title_lower = title.lower()
        event_type = "unknown"
        if "delist" in title_lower or "removal" in title_lower:
            event_type = ExternalSignalEventType.DELISTING.value
        elif (
            "futures" in title_lower
            or "launch" in title_lower
            and ("permanent" in title_lower or "perp" in title_lower)
        ):
            event_type = ExternalSignalEventType.FUTURES_LAUNCH.value
        elif "margin" in title_lower:
            event_type = ExternalSignalEventType.MARGIN_ENABLE.value
        elif "unlock" in title_lower:
            event_type = ExternalSignalEventType.MAJOR_UNLOCK.value
        elif "list new coin" in title_lower or "new listing" in title_lower:
            event_type = ExternalSignalEventType.NEW_COIN.value
        elif "whale" in title_lower:
            event_type = ExternalSignalEventType.WHALE_DEPOSIT.value

        # For each symbol, normalize
        for raw_sym in symbols:
            # Handle ambiguous symbol mapping
            quarantine_reasons = []
            trade_pair_mapping_status = "pass"
            base_asset_mapping_status = "pass"

            if "/" in raw_sym and "WBTC" in raw_sym:
                quarantine_reasons.append("ambiguous_symbol")
                trade_pair_mapping_status = "failed"

            if event_type == "unknown":
                quarantine_reasons.append("unsupported_event_type")

            # Parse base asset
            base_asset = raw_sym
            if "/" in raw_sym:
                base_asset = raw_sym.split("/")[0]
            elif "-" in raw_sym:
                base_asset = raw_sym.split("-")[0]

            # Construct trade pair
            if raw_sym == "":
                trade_pair = ""
                base_asset_mapping_status = "failed"
                trade_pair_mapping_status = "failed"
            elif raw_sym.endswith("USDT"):
                trade_pair = raw_sym
            else:
                trade_pair = f"{base_asset}USDT"

            # Check if domain was ok
            domain = "unknown"
            if raw_payload.source_url.startswith("http"):
                from src.research.external_signal_shadow.stage1_5a_source_audit_safety import (
                    normalize_source_domain,
                )

                domain = normalize_source_domain(raw_payload.source_url)

            # Available_at rule
            published_ms = rec["published_ms"]
            time_quality = rec["source_timestamp_quality"]

            hindsight_risk = False
            observation_only = False

            if raw_payload.source_profile == SourceProfile.UNLOCK_ROWS.value:
                # unlock calendar defaults
                observation_only = True
                hindsight_risk = True
                available_at_ms = raw_payload.collector_received_at_ms
            else:
                if published_ms:
                    available_at_ms = (
                        published_ms + base.EXTERNAL_SIGNAL_STAGE1_5A_PRIMARY_ANNOUNCEMENT_DELAY_MS
                    )
                else:
                    time_quality = TimestampQuality.LOW.value
                    available_at_ms = raw_payload.collector_received_at_ms
                    observation_only = True

            if time_quality == TimestampQuality.LOW.value:
                observation_only = True
            if event_type == "unknown":
                observation_only = True

            # Event type restriction
            if event_type in [
                ExternalSignalEventType.NEW_COIN.value,
                ExternalSignalEventType.WHALE_DEPOSIT.value,
                ExternalSignalEventType.MAJOR_UNLOCK.value,
                ExternalSignalEventType.TOKEN_EMISSION.value,
            ]:
                observation_only = True

            replay_allowed = not observation_only and not quarantine_reasons

            # Event Gid
            event_key = f"{title}_{trade_pair}_{published_ms}"
            event_id = hashlib.sha256(event_key.encode("utf-8")).hexdigest()
            event_hash = hashlib.sha256(
                f"{event_id}_{available_at_ms}".encode("utf-8")
            ).hexdigest()

            event = NormalizedExternalEvent(
                event_id=event_id,
                event_type=event_type,
                symbol=trade_pair,
                base_asset=base_asset,
                quote_asset="USDT" if trade_pair else "",
                venue=raw_payload.source_name.split("_")[0],
                source_name=raw_payload.source_name,
                source_domain=domain,
                source_url=rec["url"] or raw_payload.source_url,
                source_parent_url=raw_payload.source_parent_url,
                source_published_at_ms=published_ms or 0,
                event_time_ms=published_ms or 0,
                available_at_ms=available_at_ms,
                collector_received_at_ms=raw_payload.collector_received_at_ms,
                raw_payload_hash=raw_hash,
                event_payload_hash=event_hash,
                raw_payload_size_bytes=len(raw_payload.raw_payload_bytes),
                detail_url_available=bool(rec["url"]),
                source_integrity_level="full_detail" if rec["url"] else "index_only",
                schema_version=base.EXTERNAL_SIGNAL_CONNECTOR_SCHEMA_VERSION,
                source_timestamp_quality=time_quality,
                historical_available_at_confidence="high"
                if time_quality in ("high", "medium")
                else "low",
                edited_page_risk=False,
                hindsight_risk=hindsight_risk,
                magnitude=1.0,
                base_asset_mapping_status=base_asset_mapping_status,
                trade_pair_mapping_status=trade_pair_mapping_status,
                quarantine_reasons=quarantine_reasons,
                replay_allowed=replay_allowed,
                observation_only=observation_only,
            )

            if quarantine_reasons:
                metrics["schema_quarantine_count"] += 1

            events.append(event)

    return events, metrics
