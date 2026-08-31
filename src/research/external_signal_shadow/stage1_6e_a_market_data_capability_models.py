import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

PROFILE_IDS: tuple[str, ...] = (
    "binance_usdm_rest_depth_v1",
    "binance_usdm_rest_premium_index_v1",
    "binance_usdm_rest_funding_rate_v1",
    "binance_usdm_rest_open_interest_hist_5m_v1",
)

PROFILE_CORES: dict[str, dict[str, Any]] = {
    "binance_usdm_rest_depth_v1": {
        "profile_schema_version": "stage1_6e_a_profile_core_v1",
        "market_source_profile_id": "binance_usdm_rest_depth_v1",
        "market_data_subtype": "public_rest_visible_orderbook",
        "method": "GET",
        "scheme": "https",
        "host": "fapi.binance.com",
        "path": "/fapi/v1/depth",
        "canonical_query": "limit=100&symbol=BTCUSDT",
        "expected_response_schema": {
            "root_type": "object",
            "root_array": None,
            "required_fields": {
                "E": "ms_timestamp",
                "T": "ms_timestamp",
                "asks": "price_quantity_tuple_array",
                "bids": "price_quantity_tuple_array",
                "lastUpdateId": "integer",
            },
            "tuple_array_fields": {
                "asks": ["price_decimal_string", "quantity_decimal_string"],
                "bids": ["price_decimal_string", "quantity_decimal_string"],
            },
        },
        "payload_time_semantics": {
            "E": "server_output_time_ms",
            "T": "transaction_time_ms",
        },
        "parser_version": "stage1_6e_a_profile_parser_v1",
        "max_raw_response_bytes": 2_000_000,
        "public_readonly": True,
        "documented_request_weight": 5,
        "documented_rate_limit_scope": "endpoint_documented_weight",
        "rate_limit_documentation_observed_at": "2026-08-31",
        "extra_fields_policy": "allowed",
    },
    "binance_usdm_rest_premium_index_v1": {
        "profile_schema_version": "stage1_6e_a_profile_core_v1",
        "market_source_profile_id": "binance_usdm_rest_premium_index_v1",
        "market_data_subtype": "mark_price",
        "method": "GET",
        "scheme": "https",
        "host": "fapi.binance.com",
        "path": "/fapi/v1/premiumIndex",
        "canonical_query": "symbol=BTCUSDT",
        "expected_response_schema": {
            "root_type": "object",
            "root_array": None,
            "required_fields": {
                "estimatedSettlePrice": "decimal_string",
                "indexPrice": "decimal_string",
                "interestRate": "decimal_string",
                "lastFundingRate": "decimal_string",
                "markPrice": "decimal_string",
                "nextFundingTime": "ms_timestamp",
                "symbol": "literal_BTCUSDT",
                "time": "ms_timestamp",
            },
            "tuple_array_fields": {},
        },
        "payload_time_semantics": {
            "nextFundingTime": "next_scheduled_funding_time_ms",
            "time": "payload_observation_time_ms",
        },
        "parser_version": "stage1_6e_a_profile_parser_v1",
        "max_raw_response_bytes": 2_000_000,
        "public_readonly": True,
        "documented_request_weight": 1,
        "documented_rate_limit_scope": "endpoint_documented_weight",
        "rate_limit_documentation_observed_at": "2026-08-31",
        "extra_fields_policy": "allowed",
    },
    "binance_usdm_rest_funding_rate_v1": {
        "profile_schema_version": "stage1_6e_a_profile_core_v1",
        "market_source_profile_id": "binance_usdm_rest_funding_rate_v1",
        "market_data_subtype": "funding_realized_history",
        "method": "GET",
        "scheme": "https",
        "host": "fapi.binance.com",
        "path": "/fapi/v1/fundingRate",
        "canonical_query": "limit=1&symbol=BTCUSDT",
        "expected_response_schema": {
            "root_type": "array",
            "root_array": {"exact_length": 1, "item_type": "object"},
            "required_fields": {
                "fundingRate": "decimal_string",
                "fundingTime": "ms_timestamp",
                "markPrice": "decimal_string",
                "rateType": "enum_Regular_Special",
                "symbol": "literal_BTCUSDT",
            },
            "tuple_array_fields": {},
        },
        "payload_time_semantics": {
            "fundingTime": "realized_funding_event_time_ms",
        },
        "parser_version": "stage1_6e_a_profile_parser_v1",
        "max_raw_response_bytes": 2_000_000,
        "public_readonly": True,
        "documented_request_weight": "not_stated",
        "documented_rate_limit_scope": "shared_500_requests_per_5_minutes_per_IP_with_fundingInfo",
        "rate_limit_documentation_observed_at": "2026-08-31",
        "extra_fields_policy": "allowed",
    },
    "binance_usdm_rest_open_interest_hist_5m_v1": {
        "profile_schema_version": "stage1_6e_a_profile_core_v1",
        "market_source_profile_id": "binance_usdm_rest_open_interest_hist_5m_v1",
        "market_data_subtype": "oi_historical_period_5m",
        "method": "GET",
        "scheme": "https",
        "host": "fapi.binance.com",
        "path": "/futures/data/openInterestHist",
        "canonical_query": "limit=1&period=5m&symbol=BTCUSDT",
        "expected_response_schema": {
            "root_type": "array",
            "root_array": {"exact_length": 1, "item_type": "object"},
            "required_fields": {
                "sumOpenInterest": "decimal_string",
                "sumOpenInterestValue": "decimal_string",
                "symbol": "literal_BTCUSDT",
                "timestamp": "ms_timestamp",
            },
            "tuple_array_fields": {},
        },
        "payload_time_semantics": {
            "timestamp": "period_end_time_5m_ms",
        },
        "parser_version": "stage1_6e_a_profile_parser_v1",
        "max_raw_response_bytes": 2_000_000,
        "public_readonly": True,
        "documented_request_weight": 0,
        "documented_rate_limit_scope": "endpoint_documented_weight",
        "rate_limit_documentation_observed_at": "2026-08-31",
        "extra_fields_policy": "allowed",
    },
}

_DECIMAL_STRING_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def canonical_json(data: Any) -> bytes:
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_profile_attestation_sha256(profile_core: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(profile_core))


def compute_request_identity(profile_core: dict[str, Any]) -> str:
    req_dict = {
        "canonical_query": profile_core["canonical_query"],
        "host": profile_core["host"],
        "method": profile_core["method"],
        "path": profile_core["path"],
        "scheme": profile_core["scheme"],
    }
    return sha256_hex(canonical_json(req_dict))


def compute_observation_id(
    *,
    capability_run_id: str,
    market_source_profile_id: str,
    profile_attestation_sha256: str,
    probe_request_seq: int,
    request_identity: str,
    outcome_kind: str,
    http_status: int | None,
    raw_payload_persisted: bool,
    raw_sha256: str | None,
    observed_bytes_lower_bound: int,
) -> str:
    obs_dict = {
        "capability_run_id": capability_run_id,
        "http_status": http_status,
        "market_source_profile_id": market_source_profile_id,
        "observed_bytes_lower_bound": observed_bytes_lower_bound,
        "outcome_kind": outcome_kind,
        "probe_request_seq": probe_request_seq,
        "profile_attestation_sha256": profile_attestation_sha256,
        "raw_payload_persisted": raw_payload_persisted,
        "raw_sha256": raw_sha256,
        "request_identity": request_identity,
    }
    return sha256_hex(canonical_json(obs_dict))


def stage1_6e_a_permissions() -> dict[str, bool]:
    return {
        "RISK_LIVE_TRADING_ENABLED": False,
        "execution_feasibility_claim_allowed": False,
        "net_cost_or_profit_claim_allowed": False,
        "replay_allowed": False,
        "alpha_interpretation_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "private_api_allowed": False,
        "authenticated_api_allowed": False,
        "order_api_allowed": False,
    }


def validate_decimal_string(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_DECIMAL_STRING_RE.match(value))


def validate_integer(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return True


def validate_ms_timestamp(value: Any) -> bool:
    if not validate_integer(value):
        return False
    return value >= 0


def validate_response_schema(profile_core: dict[str, Any], payload: Any) -> tuple[bool, str | None]:
    schema = profile_core["expected_response_schema"]
    root_type = schema["root_type"]

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
        elif f_type == "literal_BTCUSDT":
            if val != "BTCUSDT":
                return False, f"invalid_literal_BTCUSDT_for_{f_name}"
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


@dataclass(frozen=True)
class LayerAInput:
    profile_seq: int
    is_timeout: bool = False
    transport_error: bool = False
    body_too_large: bool = False
    raw_persist_failed: bool = False
    http_status: int | None = None
    raw_persisted: bool = False
    is_redirect: bool = False
    non_identity_encoding: bool = False
    json_parse_invalid: bool = False
    schema_invalid: bool = False
    time_invalid: bool = False
    schema_valid: bool = False
    time_valid: bool = False


@dataclass(frozen=True)
class LayerAOutcome:
    outcome_kind: str  # response_persisted | response_not_persisted
    raw_payload_persisted: bool
    payload_schema_status: str  # verified | invalid | not_evaluable
    payload_time_status: str  # verified | invalid | not_evaluable
    provisional_profile_status: str  # capability_pass | capability_blocked | capability_failed
    provisional_terminal_intent: str
    terminal_classification: str  # continue | terminal_blocked | terminal_failed


def reduce_layer_a(inp: LayerAInput) -> LayerAOutcome:
    """
    Evaluates Layer A conditions in exact Design Section 5.2 order.
    Only the first matching condition applies.
    """
    if inp.is_timeout:
        return LayerAOutcome(
            outcome_kind="response_not_persisted",
            raw_payload_persisted=False,
            payload_schema_status="not_evaluable",
            payload_time_status="not_evaluable",
            provisional_profile_status="capability_blocked",
            provisional_terminal_intent="blocked:profile_timeout",
            terminal_classification="terminal_blocked",
        )

    if inp.transport_error:
        return LayerAOutcome(
            outcome_kind="response_not_persisted",
            raw_payload_persisted=False,
            payload_schema_status="not_evaluable",
            payload_time_status="not_evaluable",
            provisional_profile_status="capability_blocked",
            provisional_terminal_intent="blocked:profile_transport_blocked",
            terminal_classification="terminal_blocked",
        )

    if inp.body_too_large:
        return LayerAOutcome(
            outcome_kind="response_not_persisted",
            raw_payload_persisted=False,
            payload_schema_status="not_evaluable",
            payload_time_status="not_evaluable",
            provisional_profile_status="capability_blocked",
            provisional_terminal_intent="blocked:profile_response_too_large",
            terminal_classification="terminal_blocked",
        )

    if inp.raw_persist_failed:
        return LayerAOutcome(
            outcome_kind="response_not_persisted",
            raw_payload_persisted=False,
            payload_schema_status="not_evaluable",
            payload_time_status="not_evaluable",
            provisional_profile_status="capability_failed",
            provisional_terminal_intent="failed:storage_write_blocked",
            terminal_classification="terminal_failed",
        )

    if inp.is_redirect:
        return LayerAOutcome(
            outcome_kind="response_persisted",
            raw_payload_persisted=True,
            payload_schema_status="not_evaluable",
            payload_time_status="not_evaluable",
            provisional_profile_status="capability_blocked",
            provisional_terminal_intent="blocked:profile_redirect_blocked",
            terminal_classification="terminal_blocked",
        )

    if inp.http_status is not None and not (200 <= inp.http_status < 300):
        return LayerAOutcome(
            outcome_kind="response_persisted",
            raw_payload_persisted=True,
            payload_schema_status="not_evaluable",
            payload_time_status="not_evaluable",
            provisional_profile_status="capability_blocked",
            provisional_terminal_intent="blocked:profile_http_blocked",
            terminal_classification="terminal_blocked",
        )

    if inp.non_identity_encoding:
        return LayerAOutcome(
            outcome_kind="response_persisted",
            raw_payload_persisted=True,
            payload_schema_status="not_evaluable",
            payload_time_status="not_evaluable",
            provisional_profile_status="capability_blocked",
            provisional_terminal_intent="blocked:profile_response_invalid",
            terminal_classification="terminal_blocked",
        )

    if inp.json_parse_invalid:
        return LayerAOutcome(
            outcome_kind="response_persisted",
            raw_payload_persisted=True,
            payload_schema_status="invalid",
            payload_time_status="not_evaluable",
            provisional_profile_status="capability_blocked",
            provisional_terminal_intent="blocked:profile_response_invalid",
            terminal_classification="terminal_blocked",
        )

    if inp.schema_invalid:
        return LayerAOutcome(
            outcome_kind="response_persisted",
            raw_payload_persisted=True,
            payload_schema_status="invalid",
            payload_time_status="not_evaluable",
            provisional_profile_status="capability_blocked",
            provisional_terminal_intent="blocked:profile_schema_drift",
            terminal_classification="terminal_blocked",
        )

    if inp.time_invalid:
        return LayerAOutcome(
            outcome_kind="response_persisted",
            raw_payload_persisted=True,
            payload_schema_status="verified",
            payload_time_status="invalid",
            provisional_profile_status="capability_blocked",
            provisional_terminal_intent="blocked:profile_time_drift",
            terminal_classification="terminal_blocked",
        )

    # Valid response
    if inp.profile_seq == 4:
        return LayerAOutcome(
            outcome_kind="response_persisted",
            raw_payload_persisted=True,
            payload_schema_status="verified",
            payload_time_status="verified",
            provisional_profile_status="capability_pass",
            provisional_terminal_intent="complete:null",
            terminal_classification="continue",
        )

    return LayerAOutcome(
        outcome_kind="response_persisted",
        raw_payload_persisted=True,
        payload_schema_status="verified",
        payload_time_status="verified",
        provisional_profile_status="capability_pass",
        provisional_terminal_intent="continue",
        terminal_classification="continue",
    )
