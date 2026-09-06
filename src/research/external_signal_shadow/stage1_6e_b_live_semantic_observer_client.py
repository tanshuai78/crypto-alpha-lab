"""Stage 1.6E-B slot scheduler and sequential public HTTP client."""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from configs import base
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    validate_decimal_string,
    validate_integer,
    validate_ms_timestamp,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    EventContract,
    EventProfileCore,
    canonical_json,
    compute_slot_id,
    sha256_hex,
)

PROFILE_PRIORITY: dict[str, int] = {
    "binance_usdm_rest_depth_v1": 0,
    "binance_usdm_rest_premium_index_v1": 1,
    "binance_usdm_rest_funding_rate_v1": 2,
    "binance_usdm_rest_open_interest_hist_5m_v1": 3,
}


@dataclass(frozen=True)
class ScheduledSlot:
    slot_id: str
    event_id: str
    base_e_a_profile_id: str
    canonical_symbol: str
    slot_family: str
    slot_index: int
    due_at_ms: int
    request_identity: str


def generate_event_slots(
    event_contract: EventContract,
    event_profile_cores: dict[str, EventProfileCore],
) -> list[ScheduledSlot]:
    """
    Generates all deterministic scheduled slots for an event contract.
    Each symbol has exactly 1,586 slots:
      - depth_60s: 720 slots (indices 0..719, interval 60s)
      - premium_60s: 720 slots (indices 0..719, interval 60s)
      - oi_5m: 144 slots (indices 0..143, interval 300s)
      - funding_start: 1 slot (index 0, due at start)
      - funding_end: 1 slot (index 0, due at start + 12h)
    Slots are sorted by (due_at_ms, profile_priority, canonical_symbol, slot_family, slot_index).
    """
    event_id = event_contract.event_id
    start_ms = event_contract.event_window_started_at_ms
    slots: list[ScheduledSlot] = []

    for sym in event_contract.canonical_symbols_ordered:
        # 1. depth_60s (0..719)
        pid_depth = "binance_usdm_rest_depth_v1"
        core_depth = event_profile_cores[f"{sym}:{pid_depth}"].http_profile_core
        req_id_depth = sha256_hex(
            canonical_json({
                "method": core_depth["method"],
                "scheme": core_depth["scheme"],
                "host": core_depth["host"],
                "path": core_depth["path"],
                "canonical_query": core_depth["canonical_query"],
            })
        )
        for i in range(720):
            due = start_ms + i * base.EXTERNAL_SIGNAL_STAGE1_6E_B_DEPTH_INTERVAL_MS
            s_id = compute_slot_id(
                event_id=event_id,
                base_e_a_profile_id=pid_depth,
                canonical_symbol=sym,
                slot_family="depth_60s",
                slot_index=i,
                due_at_ms=due,
            )
            slots.append(
                ScheduledSlot(
                    slot_id=s_id,
                    event_id=event_id,
                    base_e_a_profile_id=pid_depth,
                    canonical_symbol=sym,
                    slot_family="depth_60s",
                    slot_index=i,
                    due_at_ms=due,
                    request_identity=req_id_depth,
                )
            )

        # 2. premium_60s (0..719)
        pid_premium = "binance_usdm_rest_premium_index_v1"
        core_prem = event_profile_cores[f"{sym}:{pid_premium}"].http_profile_core
        req_id_prem = sha256_hex(
            canonical_json({
                "method": core_prem["method"],
                "scheme": core_prem["scheme"],
                "host": core_prem["host"],
                "path": core_prem["path"],
                "canonical_query": core_prem["canonical_query"],
            })
        )
        for i in range(720):
            due = start_ms + i * base.EXTERNAL_SIGNAL_STAGE1_6E_B_PREMIUM_INTERVAL_MS
            s_id = compute_slot_id(
                event_id=event_id,
                base_e_a_profile_id=pid_premium,
                canonical_symbol=sym,
                slot_family="premium_60s",
                slot_index=i,
                due_at_ms=due,
            )
            slots.append(
                ScheduledSlot(
                    slot_id=s_id,
                    event_id=event_id,
                    base_e_a_profile_id=pid_premium,
                    canonical_symbol=sym,
                    slot_family="premium_60s",
                    slot_index=i,
                    due_at_ms=due,
                    request_identity=req_id_prem,
                )
            )

        # 3. oi_5m (0..143)
        pid_oi = "binance_usdm_rest_open_interest_hist_5m_v1"
        core_oi = event_profile_cores[f"{sym}:{pid_oi}"].http_profile_core
        req_id_oi = sha256_hex(
            canonical_json({
                "method": core_oi["method"],
                "scheme": core_oi["scheme"],
                "host": core_oi["host"],
                "path": core_oi["path"],
                "canonical_query": core_oi["canonical_query"],
            })
        )
        for i in range(144):
            due = start_ms + i * base.EXTERNAL_SIGNAL_STAGE1_6E_B_OPEN_INTEREST_INTERVAL_MS
            s_id = compute_slot_id(
                event_id=event_id,
                base_e_a_profile_id=pid_oi,
                canonical_symbol=sym,
                slot_family="oi_5m",
                slot_index=i,
                due_at_ms=due,
            )
            slots.append(
                ScheduledSlot(
                    slot_id=s_id,
                    event_id=event_id,
                    base_e_a_profile_id=pid_oi,
                    canonical_symbol=sym,
                    slot_family="oi_5m",
                    slot_index=i,
                    due_at_ms=due,
                    request_identity=req_id_oi,
                )
            )

        # 4. funding_start (0)
        pid_funding = "binance_usdm_rest_funding_rate_v1"
        core_funding = event_profile_cores[f"{sym}:{pid_funding}"].http_profile_core
        req_id_funding = sha256_hex(
            canonical_json({
                "method": core_funding["method"],
                "scheme": core_funding["scheme"],
                "host": core_funding["host"],
                "path": core_funding["path"],
                "canonical_query": core_funding["canonical_query"],
            })
        )
        s_id_start = compute_slot_id(
            event_id=event_id,
            base_e_a_profile_id=pid_funding,
            canonical_symbol=sym,
            slot_family="funding_start",
            slot_index=0,
            due_at_ms=start_ms,
        )
        slots.append(
            ScheduledSlot(
                slot_id=s_id_start,
                event_id=event_id,
                base_e_a_profile_id=pid_funding,
                canonical_symbol=sym,
                slot_family="funding_start",
                slot_index=0,
                due_at_ms=start_ms,
                request_identity=req_id_funding,
            )
        )

        # 5. funding_end (0)
        end_ms = start_ms + base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_WINDOW_MS
        s_id_end = compute_slot_id(
            event_id=event_id,
            base_e_a_profile_id=pid_funding,
            canonical_symbol=sym,
            slot_family="funding_end",
            slot_index=0,
            due_at_ms=end_ms,
        )
        slots.append(
            ScheduledSlot(
                slot_id=s_id_end,
                event_id=event_id,
                base_e_a_profile_id=pid_funding,
                canonical_symbol=sym,
                slot_family="funding_end",
                slot_index=0,
                due_at_ms=end_ms,
                request_identity=req_id_funding,
            )
        )

    # Sort slots by:
    # 1. due_at_ms
    # 2. profile priority: depth (0), premium (1), funding (2), open_interest (3)
    # 3. canonical_symbol (lexicographic)
    # 4. slot_family
    # 5. slot_index
    slots.sort(
        key=lambda s: (
            s.due_at_ms,
            PROFILE_PRIORITY.get(s.base_e_a_profile_id, 99),
            s.canonical_symbol,
            s.slot_family,
            s.slot_index,
        )
    )
    return slots


def validate_event_response_schema(
    schema: dict[str, Any],
    payload: Any,
) -> tuple[bool, str | None]:
    root_type = schema.get("root_type")
    target_obj: dict[str, Any]

    if root_type == "object":
        if not isinstance(payload, dict):
            return False, "root_is_not_object"
        target_obj = payload
    elif root_type == "array":
        if not isinstance(payload, list):
            return False, "root_is_not_array"
        root_arr_cfg = schema.get("root_array") or {}
        exact_len = root_arr_cfg.get("exact_length", 1)
        if len(payload) != exact_len:
            return False, f"array_length_mismatch_expected_{exact_len}"
        if not isinstance(payload[0], dict):
            return False, "array_item_is_not_object"
        target_obj = payload[0]
    else:
        return False, f"unknown_root_type_{root_type}"

    req_fields: dict[str, str] = schema.get("required_fields", {})
    for f_name, f_type in req_fields.items():
        if f_name not in target_obj:
            return False, f"missing_required_field_{f_name}"
        val = target_obj[f_name]

        if f_type == "ms_timestamp":
            if not validate_ms_timestamp(val):
                return False, f"invalid_ms_timestamp_for_{f_name}"
        elif f_type == "integer":
            if not validate_integer(val):
                return False, f"invalid_integer_for_{f_name}"
        elif f_type == "decimal_string":
            if not validate_decimal_string(val):
                return False, f"invalid_decimal_string_for_{f_name}"
        elif f_type.startswith("literal_"):
            expected = f_type[len("literal_") :]
            if val != expected:
                return False, f"invalid_{f_type}_for_{f_name}"
        elif f_type == "enum_Regular_Special":
            if val not in ("Regular", "Special"):
                return False, f"invalid_enum_Regular_Special_for_{f_name}"
        elif f_type == "price_quantity_tuple_array":
            if not isinstance(val, list):
                return False, f"field_{f_name}_is_not_array"
            for item in val:
                if not isinstance(item, list) or len(item) != 2:
                    return False, f"invalid_tuple_length_in_{f_name}"
                if not validate_decimal_string(item[0]) or not validate_decimal_string(item[1]):
                    return False, f"invalid_tuple_decimal_string_in_{f_name}"
        else:
            return False, f"unknown_type_rule_{f_type}"

    return True, None


def validate_event_response_time(
    time_semantics: dict[str, str],
    payload: Any,
) -> tuple[bool, str | None]:
    target_obj: dict[str, Any]
    if isinstance(payload, dict):
        target_obj = payload
    elif isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], dict):
        target_obj = payload[0]
    else:
        return False, "payload_not_object_or_array_of_objects"

    for f_name, _ in time_semantics.items():
        if f_name not in target_obj:
            return False, f"missing_time_semantic_field_{f_name}"
        val = target_obj[f_name]
        if not validate_ms_timestamp(val):
            return False, f"invalid_time_semantic_timestamp_for_{f_name}"

    return True, None


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, hdrs: Any, newurl: str) -> None:
        return None


def _build_default_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        _NoRedirectHandler(),
        urllib.request.ProxyHandler({}),
    )


@dataclass(frozen=True)
class ClientFetchResult:
    outcome_kind: str
    http_status: int | None
    headers_subset: dict[str, str]
    raw_body: bytes | None
    failure_reason: str | None


class Stage16EBPublicClient:
    def __init__(
        self,
        opener: urllib.request.OpenerDirector | Any | None = None,
        timeout_sec: float | None = None,
    ):
        self._opener = opener if opener is not None else _build_default_opener()
        self._timeout_sec = (
            timeout_sec
            if timeout_sec is not None
            else base.EXTERNAL_SIGNAL_STAGE1_6E_B_HTTP_TIMEOUT_SEC
        )

    def _extract_headers_subset(self, hdrs: Any) -> tuple[dict[str, str], bool]:
        """
        Extracts only lowercase 'content-type', 'content-encoding', and 'date' keys
        that were actually present in the response.
        """
        subset: dict[str, str] = {}
        if hdrs is None:
            return subset, False

        allowed_keys = ("content-type", "content-encoding", "date")
        for k in allowed_keys:
            val = hdrs.get(k)
            if val is None:
                val = hdrs.get(k.title()) or hdrs.get(k.upper())
            if val is not None:
                subset[k] = str(val).strip()

        # Enforce max canonical JSON bytes <= 8192
        canonical_b = canonical_json(subset)
        if len(canonical_b) > 8192:
            subset = {}

        ce = subset.get("content-encoding")
        non_identity = False
        if ce is not None and ce.lower() != "identity":
            non_identity = True

        return subset, non_identity

    def fetch(self, http_profile_core: dict[str, Any]) -> ClientFetchResult:
        scheme = http_profile_core["scheme"]
        host = http_profile_core["host"]
        path = http_profile_core["path"]
        query = http_profile_core["canonical_query"]
        url = f"{scheme}://{host}{path}?{query}"
        try:
            max_raw_bytes = http_profile_core["max_raw_response_bytes"]
        except KeyError as exc:
            raise ValueError("profile_core_raw_response_bound_invalid") from exc

        if type(max_raw_bytes) is not int or max_raw_bytes <= 0:
            raise ValueError("profile_core_raw_response_bound_invalid")

        req = urllib.request.Request(
            url=url,
            headers={"Accept-Encoding": "identity"},
            method="GET",
        )

        try:
            resp = self._opener.open(req, timeout=self._timeout_sec)
            status_code = getattr(resp, "status", getattr(resp, "code", 200))
            hdrs = getattr(resp, "headers", None)
            headers_subset, non_identity = self._extract_headers_subset(hdrs)

            if 300 <= status_code < 400:
                return ClientFetchResult(
                    outcome_kind="redirect_rejected",
                    http_status=status_code,
                    headers_subset=headers_subset,
                    raw_body=None,
                    failure_reason="redirect_rejected",
                )

            if non_identity:
                return ClientFetchResult(
                    outcome_kind="content_encoding_invalid",
                    http_status=status_code,
                    headers_subset=headers_subset,
                    raw_body=None,
                    failure_reason="content_encoding_invalid",
                )

            read_limit = max_raw_bytes + 1
            raw_chunk = resp.read(read_limit)
            if hasattr(resp, "close"):
                resp.close()

            if len(raw_chunk) > max_raw_bytes:
                return ClientFetchResult(
                    outcome_kind="raw_size_exceeded",
                    http_status=status_code,
                    headers_subset=headers_subset,
                    raw_body=None,
                    failure_reason="raw_size_exceeded",
                )

            if status_code != 200:
                return ClientFetchResult(
                    outcome_kind="http_response_invalid",
                    http_status=status_code,
                    headers_subset=headers_subset,
                    raw_body=None,
                    failure_reason="http_response_invalid",
                )

            return ClientFetchResult(
                outcome_kind="response_verified",
                http_status=status_code,
                headers_subset=headers_subset,
                raw_body=raw_chunk,
                failure_reason=None,
            )

        except urllib.error.HTTPError as exc:
            headers_subset, non_identity = self._extract_headers_subset(exc.headers)
            if 300 <= exc.code < 400:
                return ClientFetchResult(
                    outcome_kind="redirect_rejected",
                    http_status=exc.code,
                    headers_subset=headers_subset,
                    raw_body=None,
                    failure_reason="redirect_rejected",
                )

            body_bytes = b""
            if exc.fp is not None:
                body_bytes = exc.fp.read(max_raw_bytes + 1)

            if len(body_bytes) > max_raw_bytes:
                return ClientFetchResult(
                    outcome_kind="raw_size_exceeded",
                    http_status=exc.code,
                    headers_subset=headers_subset,
                    raw_body=None,
                    failure_reason="raw_size_exceeded",
                )

            if non_identity:
                return ClientFetchResult(
                    outcome_kind="content_encoding_invalid",
                    http_status=exc.code,
                    headers_subset=headers_subset,
                    raw_body=None,
                    failure_reason="content_encoding_invalid",
                )

            return ClientFetchResult(
                outcome_kind="http_response_invalid",
                http_status=exc.code,
                headers_subset=headers_subset,
                raw_body=None,
                failure_reason="http_response_invalid",
            )

        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)) or "timed out" in str(exc.reason):
                return ClientFetchResult(
                    outcome_kind="request_timeout",
                    http_status=None,
                    headers_subset={},
                    raw_body=None,
                    failure_reason="request_timeout",
                )
            return ClientFetchResult(
                outcome_kind="transport_error",
                http_status=None,
                headers_subset={},
                raw_body=None,
                failure_reason="transport_error",
            )
        except (socket.timeout, TimeoutError):
            return ClientFetchResult(
                outcome_kind="request_timeout",
                http_status=None,
                headers_subset={},
                raw_body=None,
                failure_reason="request_timeout",
            )
        except Exception:
            return ClientFetchResult(
                outcome_kind="transport_error",
                http_status=None,
                headers_subset={},
                raw_body=None,
                failure_reason="transport_error",
            )
