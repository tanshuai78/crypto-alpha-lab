import re

from configs import base


def test_stage1_6e_a_config_constants():
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_HTTP_TIMEOUT_SEC == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_RAW_PAYLOAD_BYTES == 2_000_000
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_PROFILES == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_NETWORK_REQUESTS_PER_ROOT == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_MAX_BYTES == 16 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_ORDINARY_RESERVE_BYTES == 1 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_EMERGENCY_RESERVE_BYTES == 256 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_TERMINAL_WRITE_SET_MAX_PEAK_BYTES == 64 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_NONTERMINAL_METADATA_DURABLE_BYTES == 512 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_MANIFEST_DURABLE_BYTES == 128 * 1024

    # Usable root reserve calculation
    usable_normal_root_bytes = (
        base.EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_MAX_BYTES
        - base.EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_ORDINARY_RESERVE_BYTES
        - base.EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_EMERGENCY_RESERVE_BYTES
    )
    max_durable_bytes = (
        base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_PROFILES * base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_RAW_PAYLOAD_BYTES
        + base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_NONTERMINAL_METADATA_DURABLE_BYTES
        + base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_MANIFEST_DURABLE_BYTES
    )
    assert usable_normal_root_bytes > max_durable_bytes
    assert usable_normal_root_bytes == 15_466_496
    assert max_durable_bytes == 8_655_360

    # Host emergency reserve inequality
    host_emergency = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES
    peaks_sum = (
        base.EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        + base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        + base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        + base.EXTERNAL_SIGNAL_STAGE1_6E_A_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
    )
    assert host_emergency >= peaks_sum
    assert peaks_sum == 4_521_984


def test_profile_cores_and_canonical_bytes():
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
        PROFILE_CORES,
        PROFILE_IDS,
        canonical_json,
        compute_profile_attestation_sha256,
        stage1_6e_a_permissions,
    )

    assert PROFILE_IDS == (
        "binance_usdm_rest_depth_v1",
        "binance_usdm_rest_premium_index_v1",
        "binance_usdm_rest_funding_rate_v1",
        "binance_usdm_rest_open_interest_hist_5m_v1",
    )
    assert len(PROFILE_CORES) == 4

    for pid in PROFILE_IDS:
        core = PROFILE_CORES[pid]
        assert core["market_source_profile_id"] == pid
        assert core["profile_schema_version"] == "stage1_6e_a_profile_core_v1"
        assert core["method"] == "GET"
        assert core["scheme"] == "https"
        assert core["host"] == "fapi.binance.com"
        assert core["public_readonly"] is True
        assert core["parser_version"] == "stage1_6e_a_profile_parser_v1"
        assert core["max_raw_response_bytes"] == 2_000_000
        assert core["extra_fields_policy"] == "allowed"

        # Canonical bytes and hash check
        c_bytes = canonical_json(core)
        h = compute_profile_attestation_sha256(core)
        assert len(h) == 64 and re.match(r"^[0-9a-f]{64}$", h)

        # Insertion order invariance
        shuffled = {k: core[k] for k in reversed(list(core.keys()))}
        assert canonical_json(shuffled) == c_bytes
        assert compute_profile_attestation_sha256(shuffled) == h

    perms = stage1_6e_a_permissions()
    assert all(v is False for v in perms.values())
    assert perms["RISK_LIVE_TRADING_ENABLED"] is False


def test_primitive_token_grammar_and_validation():
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
        PROFILE_CORES,
        validate_decimal_string,
        validate_integer,
        validate_ms_timestamp,
        validate_response_schema,
    )

    # validate_decimal_string
    assert validate_decimal_string("0") is True
    assert validate_decimal_string("-0") is True
    assert validate_decimal_string("123.45") is True
    assert validate_decimal_string("-999.001") is True
    assert validate_decimal_string("+123.45") is False
    assert validate_decimal_string("1e5") is False
    assert validate_decimal_string("NaN") is False
    assert validate_decimal_string("Infinity") is False
    assert validate_decimal_string(" 123 ") is False
    assert validate_decimal_string("0123") is False
    assert validate_decimal_string(123) is False
    assert validate_decimal_string(None) is False

    # validate_integer / ms_timestamp
    assert validate_integer(0) is True
    assert validate_integer(12345) is True
    assert validate_integer(True) is False
    assert validate_integer(False) is False
    assert validate_integer(12.34) is False
    assert validate_integer("123") is False

    assert validate_ms_timestamp(0) is True
    assert validate_ms_timestamp(1700000000000) is True
    assert validate_ms_timestamp(-1) is False
    assert validate_ms_timestamp(True) is False

    # Depth response validation
    depth_core = PROFILE_CORES["binance_usdm_rest_depth_v1"]
    valid_depth = {
        "lastUpdateId": 1234567,
        "E": 1700000000100,
        "T": 1700000000000,
        "bids": [["60000.00", "1.500"], ["59990.00", "2.000"]],
        "asks": [["60010.00", "0.500"]],
        "extra_field_allowed": 999,
    }
    ok, err = validate_response_schema(depth_core, valid_depth)
    assert ok is True and err is None

    # Invalid tuple grammar
    invalid_depth_tuple = {
        "lastUpdateId": 1234567,
        "E": 1700000000100,
        "T": 1700000000000,
        "bids": [["60000.00", "1.500", "extra"]],
        "asks": [],
    }
    ok, err = validate_response_schema(depth_core, invalid_depth_tuple)
    assert ok is False

    # Funding rate response validation
    funding_core = PROFILE_CORES["binance_usdm_rest_funding_rate_v1"]
    valid_funding = [
        {
            "symbol": "BTCUSDT",
            "fundingRate": "0.00010000",
            "fundingTime": 1700000000000,
            "markPrice": "60000.00",
            "rateType": "Regular",
        }
    ]
    ok, err = validate_response_schema(funding_core, valid_funding)
    assert ok is True and err is None

    # Funding rate invalid rateType enum
    invalid_funding_enum = [
        {
            "symbol": "BTCUSDT",
            "fundingRate": "0.00010000",
            "fundingTime": 1700000000000,
            "markPrice": "60000.00",
            "rateType": "UnknownEnum",
        }
    ]
    ok, err = validate_response_schema(funding_core, invalid_funding_enum)
    assert ok is False


def test_layer_a_reducer_rules():
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
        LayerAInput,
        reduce_layer_a,
    )

    # Socket timeout
    res = reduce_layer_a(LayerAInput(profile_seq=1, is_timeout=True))
    assert res.outcome_kind == "response_not_persisted"
    assert res.raw_payload_persisted is False
    assert res.payload_schema_status == "not_evaluable"
    assert res.payload_time_status == "not_evaluable"
    assert res.provisional_profile_status == "capability_blocked"
    assert res.provisional_terminal_intent == "blocked:profile_timeout"
    assert res.terminal_classification == "terminal_blocked"

    # Transport failure
    res = reduce_layer_a(LayerAInput(profile_seq=1, transport_error=True))
    assert res.outcome_kind == "response_not_persisted"
    assert res.provisional_terminal_intent == "blocked:profile_transport_blocked"

    # Body exceeds cap
    res = reduce_layer_a(LayerAInput(profile_seq=1, body_too_large=True))
    assert res.outcome_kind == "response_not_persisted"
    assert res.provisional_terminal_intent == "blocked:profile_response_too_large"

    # Raw persist failure
    res = reduce_layer_a(LayerAInput(profile_seq=1, raw_persist_failed=True))
    assert res.outcome_kind == "response_not_persisted"
    assert res.provisional_profile_status == "capability_failed"
    assert res.provisional_terminal_intent == "failed:storage_write_blocked"
    assert res.terminal_classification == "terminal_failed"

    # HTTP 429
    res = reduce_layer_a(LayerAInput(profile_seq=1, http_status=429, raw_persisted=True))
    assert res.outcome_kind == "response_persisted"
    assert res.raw_payload_persisted is True
    assert res.provisional_profile_status == "capability_blocked"
    assert res.provisional_terminal_intent == "blocked:profile_http_blocked"

    # Non-identity encoding
    res = reduce_layer_a(LayerAInput(profile_seq=1, http_status=200, raw_persisted=True, non_identity_encoding=True))
    assert res.provisional_terminal_intent == "blocked:profile_response_invalid"

    # Schema drift
    res = reduce_layer_a(LayerAInput(profile_seq=1, http_status=200, raw_persisted=True, schema_invalid=True))
    assert res.payload_schema_status == "invalid"
    assert res.provisional_terminal_intent == "blocked:profile_schema_drift"

    # Time drift
    res = reduce_layer_a(LayerAInput(profile_seq=1, http_status=200, raw_persisted=True, schema_valid=True, time_invalid=True))
    assert res.payload_schema_status == "verified"
    assert res.payload_time_status == "invalid"
    assert res.provisional_terminal_intent == "blocked:profile_time_drift"

    # Valid P1 response (continue)
    res = reduce_layer_a(LayerAInput(profile_seq=1, http_status=200, raw_persisted=True, schema_valid=True, time_valid=True))
    assert res.provisional_profile_status == "capability_pass"
    assert res.provisional_terminal_intent == "continue"
    assert res.terminal_classification == "continue"

    # Valid P4 response (complete:null maps to terminal_classification="continue")
    res = reduce_layer_a(LayerAInput(profile_seq=4, http_status=200, raw_persisted=True, schema_valid=True, time_valid=True))
    assert res.provisional_profile_status == "capability_pass"
    assert res.provisional_terminal_intent == "complete:null"
    assert res.terminal_classification == "continue"
