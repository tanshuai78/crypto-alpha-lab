import hashlib
import json
from collections import Counter
from pathlib import Path

from configs import base
from src.research.external_signal_shadow.price_mapping import (
    _normalize_symbol,
    canonical_asset_id,
    load_price_map,
    resolve_price_mapping,
)
from src.research.external_signal_shadow.safety import (
    canonical_json_hash,
    validate_no_executable_payload,
)
from src.research.external_signal_shadow.schemas import ConnectorRecord, RawSkillPayload

EVENT_TYPE_DIRECTION = {
    "smart_money_inflow": "long",
    "whale_accumulation": "long",
    "market_rank_surge": "unknown",
    "liquidity_expansion": "unknown",
    "token_audit_pass": "unknown",
    "smart_money_outflow": "avoid",
    "whale_distribution": "avoid",
    "token_audit_warning": "avoid",
    "liquidity_contraction": "avoid",
    "meme_lifecycle_event": "unknown",
    "cex_market_tape_anomaly": "unknown",
    "cex_market_snapshot": "unknown",
}


def run_file_backed_connector(
    *,
    input_files: list[str],
    price_map_path: str,
    output_path: str,
    source: str,
) -> dict:
    price_map = load_price_map(price_map_path)
    records: list[ConnectorRecord] = []
    seen_semantic_keys: set[str] = set()

    for input_file in input_files:
        lines = Path(input_file).read_text().splitlines()
        for line in lines:
            if not line.strip():
                continue
            payload_dict = json.loads(line)
            try:
                validate_no_executable_payload(payload_dict)
            except ValueError:
                records.append(
                    ConnectorRecord(
                        status="rejected",
                        reject_reasons=("forbidden_executable_payload",),
                    )
                )
                continue
            try:
                wrapper = RawSkillPayload.from_dict(payload_dict)
                records.append(_process_payload(wrapper, source, price_map, seen_semantic_keys))
            except Exception as e:
                records.append(
                    ConnectorRecord(
                        status="rejected",
                        reject_reasons=("parse_error", str(e)),
                    )
                )

    emitted_events = []
    event_type_counts: Counter[str] = Counter()
    direction_hint_counts: Counter[str] = Counter()
    price_mapping_counts: Counter[str] = Counter()
    emitted_symbol_counts: Counter[str] = Counter()
    emitted_time_bucket_counts: Counter[int] = Counter()
    unique_symbols = set()
    unique_time_buckets = set()
    source_latencies_ms: list[int] = []
    # Stage 1.1 event classification counters
    stage0_replay_eligible_event_count = 0
    stage0_observation_only_event_count = 0
    directionless_event_count = 0
    avoid_event_count = 0

    summary = {
        "source": source,
        "connector_version": base.EXTERNAL_SIGNAL_CONNECTOR_VERSION,
        "schema_version": base.EXTERNAL_SIGNAL_CONNECTOR_SCHEMA_VERSION,
        "run_id": f"{source}_{base.EXTERNAL_SIGNAL_CONNECTOR_VERSION}",
        "input_files": input_files,
        "raw_payload_count": len(records),
        "emitted_event_count": 0,
        "deduped_payload_count": 0,
        "quarantined_payload_count": 0,
        "rejected_payload_count": 0,
        "event_time_fallback_count": 0,
        "reject_reason_counts": {},
        "quarantine_reason_counts": {},
        "event_type_counts": {},
        "direction_hint_counts": {},
        "price_mapping_counts": {},
        "latency_p50_ms": None,
        "latency_p95_ms": None,
    }

    for record in records:
        if record.status == "emitted":
            summary["emitted_event_count"] += 1
            if record.event:
                emitted_events.append(record.event)
                event_type_counts[record.event["event_type"]] += 1
                direction_hint = record.event["direction_hint"]
                direction_hint_counts[direction_hint] += 1
                metadata = record.event.get("metadata", {})
                price_mapping_counts[metadata.get("price_mapping_type", "unknown")] += 1

                symbol = record.event["symbol"]
                bucket = (
                    record.event["event_time_ms"]
                    // base.EXTERNAL_SIGNAL_CONNECTOR_EVENT_TIME_BUCKET_MS
                )
                unique_symbols.add(symbol)
                unique_time_buckets.add(bucket)
                emitted_symbol_counts[symbol] += 1
                emitted_time_bucket_counts[bucket] += 1

                # Stage 1.1 event classification
                if direction_hint == "long":
                    stage0_replay_eligible_event_count += 1
                elif direction_hint == "unknown":
                    stage0_observation_only_event_count += 1
                    directionless_event_count += 1
                elif direction_hint == "avoid":
                    avoid_event_count += 1

                event_time_policy = metadata.get("event_time_policy", "source_provided")
                if event_time_policy == "available_at_fallback":
                    summary["event_time_fallback_count"] += 1
                else:
                    latency_ms = metadata.get("source_latency_ms")
                    if isinstance(latency_ms, int):
                        source_latencies_ms.append(latency_ms)
        elif record.status == "deduped":
            summary["deduped_payload_count"] += 1
        elif record.status == "quarantined":
            summary["quarantined_payload_count"] += 1
            for reason in record.quarantine_reasons:
                summary["quarantine_reason_counts"][reason] = (
                    summary["quarantine_reason_counts"].get(reason, 0) + 1
                )
        elif record.status == "rejected":
            summary["rejected_payload_count"] += 1
            for reason in record.reject_reasons:
                summary["reject_reason_counts"][reason] = (
                    summary["reject_reason_counts"].get(reason, 0) + 1
                )

    summary["summary_accounting_ok"] = summary["raw_payload_count"] == (
        summary["emitted_event_count"]
        + summary["deduped_payload_count"]
        + summary["quarantined_payload_count"]
        + summary["rejected_payload_count"]
    )
    summary["event_type_counts"] = dict(sorted(event_type_counts.items()))
    summary["direction_hint_counts"] = dict(sorted(direction_hint_counts.items()))
    summary["price_mapping_counts"] = dict(sorted(price_mapping_counts.items()))
    summary["latency_p50_ms"] = _percentile_nearest_rank(source_latencies_ms, 50)
    summary["latency_p95_ms"] = _percentile_nearest_rank(source_latencies_ms, 95)

    # Stage 1.1 Metrics
    summary["unique_symbol_count"] = len(unique_symbols)
    summary["unique_event_time_bucket_count"] = len(unique_time_buckets)
    summary["latency_sample_count"] = len(source_latencies_ms)

    from src.research.external_signal_shadow.connector_summary import _safe_ratio

    missing_required_field_count = (
        summary["reject_reason_counts"].get("schema_invalid", 0)
        + summary["quarantine_reason_counts"].get("missing_chain", 0)
        + summary["quarantine_reason_counts"].get("missing_asset", 0)
    )

    summary["event_time_fallback_ratio"] = _safe_ratio(
        summary["event_time_fallback_count"], summary["emitted_event_count"]
    )
    summary["duplicate_ratio"] = _safe_ratio(
        summary["deduped_payload_count"], summary["raw_payload_count"]
    )
    summary["price_mapping_unavailable_ratio"] = _safe_ratio(
        summary["quarantine_reason_counts"].get("price_mapping_unavailable", 0),
        summary["raw_payload_count"],
    )
    summary["rejected_payload_ratio"] = _safe_ratio(
        summary["rejected_payload_count"], summary["raw_payload_count"]
    )
    summary["unknown_event_type_ratio"] = _safe_ratio(
        summary["reject_reason_counts"].get("unsupported_event_type", 0),
        summary["raw_payload_count"],
    )
    summary["missing_required_field_ratio"] = _safe_ratio(
        missing_required_field_count, summary["raw_payload_count"]
    )

    summary["single_symbol_dominance_ratio"] = _safe_ratio(
        max(emitted_symbol_counts.values()) if emitted_symbol_counts else 0,
        summary["emitted_event_count"],
    )
    summary["single_time_bucket_dominance_ratio"] = _safe_ratio(
        max(emitted_time_bucket_counts.values()) if emitted_time_bucket_counts else 0,
        summary["emitted_event_count"],
    )

    # Stage 1.1: add source provenance fields and event classification counts.
    if source == base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE:
        summary["source_vendor"] = base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_VENDOR
        summary["source_surface"] = base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SURFACE
        summary["source_capture_method"] = base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_CAPTURE_METHOD
        summary["stage0_replay_eligible_event_count"] = stage0_replay_eligible_event_count
        summary["stage0_observation_only_event_count"] = stage0_observation_only_event_count
        summary["directionless_event_count"] = directionless_event_count
        summary["avoid_event_count"] = avoid_event_count

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for event in emitted_events:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")

    summary["output_file"] = output_path

    if out_path.exists():
        h = hashlib.sha256()
        h.update(out_path.read_bytes())
        summary["output_file_sha256"] = h.hexdigest()
    else:
        summary["output_file_sha256"] = ""

    summary.update(
        {
            "live_trading_enabled": False,
            "exchange_paper_trading_allowed": False,
            "execution_engine_allowed": False,
            "research_shadow_replay_allowed": True,
            "wallet_required": False,
        }
    )

    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    return decide_stage1_connector_summary(summary)


def _process_payload(
    wrapper: RawSkillPayload,
    source: str,
    price_map: dict,
    seen_semantic_keys: set[str],
) -> ConnectorRecord:
    if wrapper.source != source:
        return ConnectorRecord(status="rejected", reject_reasons=("source_mismatch",))

    try:
        validate_no_executable_payload(wrapper.raw_payload)
    except ValueError:
        return ConnectorRecord(status="rejected", reject_reasons=("forbidden_executable_payload",))

    raw_payload_hash = canonical_json_hash(wrapper.raw_payload)
    raw = wrapper.raw_payload

    event_type = raw.get("event_type")
    chain = raw.get("chain")
    symbol = raw.get("symbol")
    token_address = raw.get("token_address")
    event_time_ms = raw.get("event_time_ms")
    available_at_ms = wrapper.available_at_ms

    if not isinstance(event_time_ms, int) or not isinstance(event_type, str):
        return ConnectorRecord(status="rejected", reject_reasons=("schema_invalid",))

    if not isinstance(chain, str):
        return ConnectorRecord(status="quarantined", quarantine_reasons=("missing_chain",))

    if available_at_ms < event_time_ms:
        return ConnectorRecord(status="rejected", reject_reasons=("available_before_event",))

    if event_type not in EVENT_TYPE_DIRECTION:
        return ConnectorRecord(status="rejected", reject_reasons=("unsupported_event_type",))

    latency_ms = available_at_ms - event_time_ms
    if wrapper.data_quality == "fixture":
        max_latency = base.EXTERNAL_SIGNAL_CONNECTOR_MAX_MANUAL_FIXTURE_LATENCY_MS
    elif chain.lower() == "cex":
        max_latency = base.EXTERNAL_SIGNAL_CONNECTOR_MAX_CEX_LATENCY_MS
    else:
        max_latency = base.EXTERNAL_SIGNAL_CONNECTOR_MAX_ONCHAIN_LATENCY_MS

    if latency_ms > max_latency:
        return ConnectorRecord(status="quarantined", quarantine_reasons=("stale_latency",))

    if source == base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE and chain and chain.lower() == "cex":
        normalized_symbol = _normalize_symbol(symbol)
        if (
            normalized_symbol
            and normalized_symbol not in base.EXTERNAL_SIGNAL_STAGE1_1_ALLOWED_SYMBOLS
        ):
            return ConnectorRecord(
                status="quarantined", quarantine_reasons=("unsupported_stage1_1_symbol",)
            )

    asset_key = canonical_asset_id(chain, symbol, token_address)
    if not asset_key:
        return ConnectorRecord(status="quarantined", quarantine_reasons=("missing_asset",))

    mapping = resolve_price_mapping(
        price_map, chain=chain, symbol=symbol, token_address=token_address
    )
    if not mapping:
        return ConnectorRecord(
            status="quarantined", quarantine_reasons=("price_mapping_unavailable",)
        )

    direction_hint = EVENT_TYPE_DIRECTION[event_type]
    bucket = event_time_ms // base.EXTERNAL_SIGNAL_CONNECTOR_EVENT_TIME_BUCKET_MS
    semantic_dedup_key = f"{wrapper.source}|{wrapper.source_skill}|{chain}|{asset_key}|{event_type}|{bucket}|{direction_hint}"

    if semantic_dedup_key in seen_semantic_keys:
        return ConnectorRecord(status="deduped")

    seen_semantic_keys.add(semantic_dedup_key)

    event_id = hashlib.sha256(semantic_dedup_key.encode("utf-8")).hexdigest()[:24]

    event_metadata = {
        **raw.get("metadata", {}),
        "event_time_policy": raw.get("metadata", {}).get("event_time_policy", "source_provided"),
        "original_event_time_ms": event_time_ms,
        "available_at_ms": available_at_ms,
        "source_latency_ms": latency_ms,
        "semantic_dedup_key": semantic_dedup_key,
        "raw_payload_hash": raw_payload_hash,
        "connector_version": base.EXTERNAL_SIGNAL_CONNECTOR_VERSION,
        "schema_version": base.EXTERNAL_SIGNAL_CONNECTOR_SCHEMA_VERSION,
        "price_series_id": mapping.price_series_id,
        "price_mapping_type": mapping.mapping_type,
    }

    # explicit rejection of raw_payload from metadata
    event_metadata.pop("raw_payload", None)

    if "notional_usd" in raw:
        event_metadata["external_notional_usd"] = float(raw["notional_usd"])
        event_metadata["external_notional_usd_semantics"] = "informational_only"

    event = {
        "event_id": event_id,
        "event_type": event_type,
        "event_time_ms": available_at_ms,  # Shift event time
        "chain": chain,
        "symbol": symbol,
        "token_address": token_address,
        "source": wrapper.source,
        "source_skill": wrapper.source_skill,
        "direction_hint": direction_hint,
        "raw_score": float(raw.get("score", 0.0)),
        "liquidity_usd": float(raw.get("liquidity_usd", 0.0)),
        "notional_usd": 0.0,
        "shadow_only": True,
        "metadata": event_metadata,
    }

    return ConnectorRecord(status="emitted", event=event)


def _percentile_nearest_rank(values: list[int], percentile: int) -> int | None:
    if not values:
        return None
    sorted_values = sorted(values)
    # Nearest-rank percentile keeps the reported latency deterministic and simple.
    rank = max(1, (percentile * len(sorted_values) + 99) // 100)
    return sorted_values[min(rank, len(sorted_values)) - 1]
