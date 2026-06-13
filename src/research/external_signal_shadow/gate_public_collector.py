from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode

PRIVATE_PATH_MARKERS = (
    "/orders",
    "/accounts",
    "/wallet",
    "/withdraw",
    "/withdrawals",
    "/deposit",
    "/deposits",
    "/transfer",
    "/transfers",
    "/positions",
    "/position",
    "/loans",
    "/margin",
    "/sub_accounts",
)


@dataclass(frozen=True)
class GateTickerResult:
    gate_pair: str
    symbol: str
    metadata: dict[str, object]
    response_field_names: tuple[str, ...]
    numeric_parse_failure_count: int


def normalize_gate_pair_to_symbol(value: str) -> str:
    return value.replace("_", "").replace("/", "").upper()


def reject_private_endpoint_path(path: str) -> None:
    lowered = path.lower()
    if any(marker in lowered for marker in PRIVATE_PATH_MARKERS):
        raise ValueError(f"private endpoint path is not allowed: {path}")
    if lowered != "/spot/tickers":
        raise ValueError(f"unsupported public endpoint path: {path}")


def build_gate_ticker_url(base_url: str, path: str, gate_pair: str) -> str:
    reject_private_endpoint_path(path)
    return f"{base_url.rstrip('/')}{path}?{urlencode({'currency_pair': gate_pair})}"


def canonical_response_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_decimal_raw(value: object) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    raw = str(value)
    try:
        Decimal(raw)
    except InvalidOperation:
        return raw, False
    return raw, True


def parse_gate_ticker_payload(payload: object, gate_pair: str) -> GateTickerResult:
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"missing ticker payload for {gate_pair}")
    row = payload[0]
    if not isinstance(row, dict):
        raise ValueError(f"invalid ticker row for {gate_pair}")

    response_pair = str(row.get("currency_pair") or gate_pair)
    if normalize_gate_pair_to_symbol(response_pair) != normalize_gate_pair_to_symbol(gate_pair):
        raise ValueError(f"pair mismatch: requested {gate_pair}, got {response_pair}")
    symbol = normalize_gate_pair_to_symbol(response_pair)
    fields = tuple(sorted(str(key) for key in row.keys()))

    numeric_failures = 0
    metadata: dict[str, object] = {"gate_currency_pair": response_pair}
    field_map = {
        "last_price": "last",
        "base_volume": "base_volume",
        "quote_volume": "quote_volume",
        "change_percentage": "change_percentage",
    }
    for output_name, input_name in field_map.items():
        raw, ok = _parse_decimal_raw(row.get(input_name))
        metadata[f"{output_name}_raw"] = raw
        metadata[f"{output_name}_parse_ok"] = ok
        if not ok:
            numeric_failures += 1

    return GateTickerResult(
        gate_pair=gate_pair,
        symbol=symbol,
        metadata=metadata,
        response_field_names=fields,
        numeric_parse_failure_count=numeric_failures,
    )


def build_raw_wrapper_from_ticker(
    result: GateTickerResult,
    *,
    fetched_at_ms: int,
    collector_run_id: str,
    collector_run_started_at_ms: int,
    collector_run_finished_at_ms: int,
    snapshot_sequence_id: int,
    api_status_code: int,
    api_latency_ms: int,
    api_response_hash: str,
    api_endpoint: str,
    api_query: dict[str, str],
    api_url: str,
) -> dict[str, object]:
    metadata = dict(result.metadata)
    metadata["source_url"] = api_url
    return {
        "source": "gate_public_market_snapshot_collector",
        "source_vendor": "gate",
        "source_surface": "gate_api_v4_public_market_data",
        "source_capture_method": "public_rest_snapshot",
        "source_skill": "gate_public_market_snapshot_collector",
        "data_quality": "api_snapshot",
        "capture_id": collector_run_id,
        "captured_by": "script",
        "collector_run_id": collector_run_id,
        "collector_run_started_at_ms": collector_run_started_at_ms,
        "collector_run_finished_at_ms": collector_run_finished_at_ms,
        "snapshot_sequence_id": snapshot_sequence_id,
        "sampling_interval_sec": None,
        "schedule_generated": True,
        "source_observed_at_ms": fetched_at_ms,
        "fetched_at_ms": fetched_at_ms,
        "available_at_ms": fetched_at_ms,
        "api_endpoint": api_endpoint,
        "api_query": api_query,
        "api_status_code": api_status_code,
        "api_latency_ms": api_latency_ms,
        "api_response_hash": api_response_hash,
        "api_response_field_names": list(result.response_field_names),
        "field_confidence": {
            "event_time_ms": "available_at_fallback",
            "symbol": "normalized",
            "score": "missing",
        },
        "raw_payload": {
            "event_type": "cex_market_snapshot",
            "chain": "cex",
            "symbol": result.symbol,
            "event_time_ms": fetched_at_ms,
            "direction_hint": "unknown",
            "score_interpretation_allowed": False,
            "triple_barrier_directional_order_allowed": False,
            "alpha_interpretation_allowed": False,
            "metadata": {**metadata, "event_time_policy": "available_at_fallback"},
        },
    }


def default_fetch_json(url: str, timeout_sec: float, user_agent: str) -> tuple[int, object, int]:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", user_agent)
    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            body = response.read().decode("utf-8")
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            try:
                data = json.loads(body)
                return response.status, data, latency_ms
            except json.JSONDecodeError:
                return response.status, {"error": "JSONDecodeError", "raw_body": body}, latency_ms
    except urllib.error.HTTPError as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        try:
            err_body = e.read().decode("utf-8")
            err_data = json.loads(err_body)
        except Exception:
            err_data = {"error": e.reason}
        return e.code, err_data, latency_ms
    except urllib.error.URLError as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return 0, {"error": "URLError", "reason": str(e.reason)}, latency_ms
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return 0, {"error": "UnknownError", "message": str(e)}, latency_ms


def collect_gate_public_snapshots_from_fetcher(
    *,
    gate_pairs: tuple[str, ...],
    output_path: str,
    fetcher: callable,
    now_ms: callable = lambda: int(time.time() * 1000),
    inter_request_delay_sec: float = 0.3,
    base_url: str = "https://api.gateio.ws/api/v4",
    tickers_path: str = "/spot/tickers",
    timeout_sec: float = 10.0,
    user_agent: str = "crypto-alpha-lab-research-readonly/0.1",
    network_mode: str = "mock",
) -> dict[str, object]:
    started_at_ms = now_ms()
    # Format run ID: gate_public_market_snapshot_YYYYMMDD_HHMMSSZ
    # For stability in tests, started_at_ms is converted to UTC string
    time_struct = time.gmtime(started_at_ms / 1000.0)
    time_str = time.strftime("%Y%m%d_%H%M%S", time_struct)
    run_id = f"gate_public_market_snapshot_{time_str}Z"

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    http_success_count = 0
    http_failure_count = 0
    raw_payload_count = 0
    numeric_failures = 0
    rate_limited_count = 0
    parse_error_count = 0
    field_parse_failure_count = 0
    collector_network_failure_count = 0

    rows: list[str] = []

    for idx, pair in enumerate(gate_pairs):
        url = build_gate_ticker_url(base_url, tickers_path, pair)
        status_code, payload, latency = fetcher(url, timeout_sec, user_agent)
        finished_at_ms = now_ms()

        if status_code == 200:
            http_success_count += 1
            try:
                result = parse_gate_ticker_payload(payload, pair)
                if result.numeric_parse_failure_count > 0:
                    http_failure_count += 1
                    field_parse_failure_count += result.numeric_parse_failure_count
                    numeric_failures += result.numeric_parse_failure_count
                    continue
                resp_hash = canonical_response_hash(payload)
                wrapper = build_raw_wrapper_from_ticker(
                    result,
                    fetched_at_ms=finished_at_ms,
                    collector_run_id=run_id,
                    collector_run_started_at_ms=started_at_ms,
                    collector_run_finished_at_ms=finished_at_ms,
                    snapshot_sequence_id=idx + 1,
                    api_status_code=status_code,
                    api_latency_ms=latency,
                    api_response_hash=resp_hash,
                    api_endpoint=tickers_path,
                    api_query={"currency_pair": pair},
                    api_url=url,
                )
                rows.append(json.dumps(wrapper) + "\n")
                raw_payload_count += 1
                numeric_failures += result.numeric_parse_failure_count
            except json.JSONDecodeError:
                http_failure_count += 1
                parse_error_count += 1
            except ValueError:
                http_failure_count += 1
                parse_error_count += 1
        else:
            http_failure_count += 1
            if status_code == 429:
                rate_limited_count += 1
            elif status_code == 0:
                collector_network_failure_count += 1

        if idx < len(gate_pairs) - 1 and inter_request_delay_sec > 0:
            time.sleep(inter_request_delay_sec)

    if rows:
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(rows)

    minimal_pass = (
        http_success_count >= len(gate_pairs)
        and http_failure_count == 0
        and raw_payload_count >= len(gate_pairs)
    )

    numeric_parse_failure_ratio = 0.0
    if raw_payload_count > 0:
        numeric_parse_failure_ratio = float(numeric_failures) / (raw_payload_count * 4.0)

    decision = "external_signal_collector_stage1_2_passed" if minimal_pass else "external_signal_collector_stage1_2_failed"
    failure_type = None
    primary_blocker = None
    if not minimal_pass:
        if rate_limited_count > 0:
            failure_type = "rate_limited"
            primary_blocker = "rate_limited"
        elif collector_network_failure_count > 0:
            failure_type = "collector_network_failure"
            primary_blocker = "collector_network_failure"
        elif parse_error_count > 0:
            failure_type = "parse_error"
            primary_blocker = "parse_error"
        elif field_parse_failure_count > 0:
            failure_type = "field_parse_failure"
            primary_blocker = "field_parse_failure"
        else:
            failure_type = "missing_required_field"
            primary_blocker = "missing_required_field"

    return {
        "decision": decision,
        "collector_version": "stage1_2_v0",
        "source": "gate_public_market_snapshot_collector",
        "network_mode": network_mode,
        "collector_minimal_pass": minimal_pass,
        "failure_type": failure_type,
        "primary_blocker": primary_blocker,
        "http_success_count": http_success_count,
        "http_failure_count": http_failure_count,
        "raw_payload_count": raw_payload_count,
        "numeric_parse_failure_count": numeric_failures,
        "numeric_parse_failure_ratio": numeric_parse_failure_ratio,
        "rate_limited_count": rate_limited_count,
        "parse_error_count": parse_error_count,
        "field_parse_failure_count": field_parse_failure_count,
        "collector_network_failure_count": collector_network_failure_count,
        "api_key_used": False,
        "private_endpoint_used": False,
        "event_density_alpha_valid": False,
        "schedule_generated": True,
        "live_safe": False,
    }


def write_failure_summary(
    output_summary_path: str,
    failure_type: str,
    http_success_count: int,
    http_failure_count: int,
    network_mode: str = "mock",
) -> None:
    summary = {
        "decision": "external_signal_collector_stage1_2_failed",
        "failure_type": failure_type,
        "collector_version": "stage1_2_v0",
        "source": "gate_public_market_snapshot_collector",
        "network_mode": network_mode,
        "collector_minimal_pass": False,
        "http_success_count": http_success_count,
        "http_failure_count": http_failure_count,
        "raw_payload_count": 0,
        "numeric_parse_failure_count": 0,
        "numeric_parse_failure_ratio": 0.0,
        "api_key_used": False,
        "private_endpoint_used": False,
        "event_density_alpha_valid": False,
        "schedule_generated": True,
        "live_safe": False,
    }
    p = Path(output_summary_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
