import pytest

from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_CORES as E_A_PROFILE_CORES,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_IDS as E_A_PROFILE_IDS,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    compute_profile_attestation_sha256,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    DelistingSemanticProjection,
    EnvironmentAuthorityReceipt,
    EventAdmission,
    EventCheckpoint,
    EventContract,
    EventTerminalStatus,
    MarketObservation,
    SlotIntent,
    SourceConsumerCheckpoint,
    SupervisorTerminalStatus,
    canonical_json,
    compute_event_id,
    compute_notice_event_key,
    compute_slot_id,
    derive_event_profile_core,
    sha256_hex,
    stage1_6e_b_permissions,
    validate_event_checkpoint_dict,
    validate_market_observation_dict,
    validate_sha256,
)


def test_permissions_exact_twelve_false():
    perms = stage1_6e_b_permissions()
    assert len(perms) == 12
    expected_keys = {
        "RISK_LIVE_TRADING_ENABLED",
        "execution_feasibility_claim_allowed",
        "net_cost_or_profit_claim_allowed",
        "replay_allowed",
        "alpha_interpretation_allowed",
        "trade_signal_allowed",
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_engine_allowed",
        "private_api_allowed",
        "authenticated_api_allowed",
        "order_api_allowed",
    }
    assert set(perms.keys()) == expected_keys
    for k, v in perms.items():
        assert v is False
        assert type(v) is bool


def test_canonical_json_and_sha256():
    d = {"b": 2, "a": 1}
    assert canonical_json(d) == '{"a":1,"b":2}'
    h = sha256_hex('{"a":1,"b":2}')
    assert len(h) == 64
    assert h == validate_sha256(h)
    with pytest.raises(ValueError, match="sha256_invalid"):
        validate_sha256("NOT_HEX")
    with pytest.raises(ValueError, match="sha256_invalid"):
        validate_sha256(h.upper())  # Reject uppercase


def test_environment_authority_receipt():
    receipt = EnvironmentAuthorityReceipt.create(
        root_kind="supervisor",
        e_a_manifest_id="e918b344b6781bbdb0cd005b3744acf3bb0d370e98ddd5c2973312dc974874b3",
        e_a_manifest_sha256="a" * 64,
        e_a_environment_attestation_sha256="b" * 64,
        e_b_execution_environment_attestation_sha256="c" * 64,
    )
    d = receipt.to_dict()
    assert d["schema_version"] == "stage1_6e_b_environment_authority_receipt_v1"
    assert d["root_kind"] == "supervisor"
    assert len(d["receipt_id"]) == 64

    # Bool as int rejected
    d_bad = dict(d)
    d_bad["root_kind"] = 123
    with pytest.raises(ValueError):
        EnvironmentAuthorityReceipt.from_dict(d_bad)


def test_source_consumer_checkpoint_null_bootstrap_and_active():
    # Bootstrap case: offset == 0 -> last_hash is None, record_seq is None
    chk = SourceConsumerCheckpoint.create(
        supervisor_run_id="stage1_6e_b_semantic_20260904T000000Z_1234567890123456",
        source_root_realpath="/root/crypto-alpha-lab/data/1.6b/live/run_1",
        source_checkpoint_id="1" * 64,
        source_checkpoint_sha256="c" * 64,
        source_stream_offsets={"detail_revisions.jsonl": 0},
        source_stream_last_hashes={},
        detail_revisions_committed_offset=0,
        detail_revisions_last_line_sha256=None,
        last_consumed_detail_revision_record_seq=None,
        active_notice_event_key=None,
        active_event_id=None,
        updated_at_ms=1000,
    )
    d = chk.to_dict()
    assert d["detail_revisions_committed_offset"] == 0
    assert d["detail_revisions_last_line_sha256"] is None
    assert d["last_consumed_detail_revision_record_seq"] is None
    assert len(d["source_consumer_checkpoint_id"]) == 64

    # Invalid bootstrap: offset == 0 but record_seq is provided
    d_invalid = dict(d)
    d_invalid["last_consumed_detail_revision_record_seq"] = 5
    with pytest.raises(ValueError, match="bootstrap_record_seq_must_be_null"):
        SourceConsumerCheckpoint.from_dict(d_invalid)

    # Valid non-zero case
    chk2 = SourceConsumerCheckpoint.create(
        supervisor_run_id="stage1_6e_b_semantic_20260904T000000Z_1234567890123456",
        source_root_realpath="/root/crypto-alpha-lab/data/1.6b/live/run_1",
        source_checkpoint_id="1" * 64,
        source_checkpoint_sha256="c" * 64,
        source_stream_offsets={"detail_revisions.jsonl": 100},
        source_stream_last_hashes={"detail_revisions.jsonl": "a" * 64},
        detail_revisions_committed_offset=100,
        detail_revisions_last_line_sha256="a" * 64,
        last_consumed_detail_revision_record_seq=1,
        active_notice_event_key="2" * 64,
        active_event_id="e" * 64,
        updated_at_ms=2000,
    )
    assert chk2.last_consumed_detail_revision_record_seq == 1


def test_delisting_semantic_projection_and_admission():
    proj = DelistingSemanticProjection.create(
        supervisor_run_id="stage1_6e_b_semantic_20260904T000000Z_1234567890123456",
        source_root_realpath="/root/crypto-alpha-lab/data/1.6b/live/run_1",
        source_checkpoint_id="c" * 64,
        source_checkpoint_sha256="1" * 64,
        source_article_id="123456",
        source_request_observation_id="req_1",
        source_detail_revision_id="rev_1",
        source_detail_raw_sha256="2" * 64,
        source_detail_raw_relative_path="raw/123456.bin",
        copied_source_raw_relative_path=f"source_detail_raw/{'2'*64}.bin",
        g2_body_normalization_version="stage1_6a_bapi_body_tree_v2",
        g2_semantic_extractor_version="stage1_6a_extractor_v2",
        normalized_body_sha256="3" * 64,
        source_first_detected_at_ms=1000,
        source_detail_trusted_at_ms=2000,
        eligible_symbols_ordered=["REEFUSDT"],
        effective_delist_time_ms=5000000,
        eligibility_status="eligible",
        blocker=None,
        semantic_projected_at_ms=3000,
    )
    d = proj.to_dict()
    assert d["eligible_symbols_normalized"] == ["REEFUSDT"]
    assert d["eligible_symbol_set_sha256"] is not None
    assert len(d["semantic_projection_id"]) == 64

    # Notice event key and event ID derivations
    notice_key = compute_notice_event_key("123456")
    event_id = compute_event_id(d["semantic_projection_id"])
    assert len(notice_key) == 64
    assert len(event_id) == 64

    # Event admission
    adm = EventAdmission.create(
        semantic_projection_id=d["semantic_projection_id"],
        notice_event_key=notice_key,
        event_id=event_id,
        decision="admitted",
        blocker=None,
        active_event_id_at_decision=None,
        decided_at_ms=3500,
    )
    d_adm = adm.to_dict()
    assert d_adm["decision"] == "admitted"
    assert len(d_adm["admission_id"]) == 64


def test_derived_profile_cores_exact_transforms():
    base_manifest_id = "e918b344b6781bbdb0cd005b3744acf3bb0d370e98ddd5c2973312dc974874b3"
    symbol = "REEFUSDT"
    for base_pid in E_A_PROFILE_IDS:
        base_core = E_A_PROFILE_CORES[base_pid]
        canonical_attest = compute_profile_attestation_sha256(base_core)
        derived = derive_event_profile_core(
            event_id="e" * 64,
            source_article_id="123456",
            source_detail_revision_id="rev_1",
            canonical_symbol=symbol,
            base_e_a_manifest_id=base_manifest_id,
            base_e_a_profile_id=base_pid,
            base_e_a_profile_attestation_sha256=canonical_attest,
            base_e_a_profile_core=base_core,
        )
        d = derived.to_dict()
        assert d["schema_version"] == "stage1_6e_b_event_profile_core_v1"
        assert d["canonical_symbol"] == symbol
        assert len(d["profile_attestation_sha256"]) == 64
        assert d["base_e_a_profile_attestation_sha256"] == canonical_attest

        http_core = d["http_profile_core"]
        # Inner raw cap equals outer raw cap
        assert http_core["max_raw_response_bytes"] == d["event_max_raw_response_bytes"]

        # Exact transform checks
        if base_pid == "binance_usdm_rest_depth_v1":
            assert http_core["canonical_query"] == f"limit=100&symbol={symbol}"
            assert d["event_max_raw_response_bytes"] == 262144
            assert http_core["max_raw_response_bytes"] == 262144
        elif base_pid == "binance_usdm_rest_premium_index_v1":
            assert http_core["canonical_query"] == f"symbol={symbol}"
            assert http_core["expected_response_schema"]["required_fields"]["symbol"] == f"literal_{symbol}"
            assert d["event_max_raw_response_bytes"] == 32768
            assert http_core["max_raw_response_bytes"] == 32768
        elif base_pid == "binance_usdm_rest_funding_rate_v1":
            assert http_core["canonical_query"] == f"limit=1&symbol={symbol}"
            assert http_core["expected_response_schema"]["required_fields"]["symbol"] == f"literal_{symbol}"
            assert d["event_max_raw_response_bytes"] == 32768
            assert http_core["max_raw_response_bytes"] == 32768
        elif base_pid == "binance_usdm_rest_open_interest_hist_5m_v1":
            assert http_core["canonical_query"] == f"limit=1&period=5m&symbol={symbol}"
            assert http_core["expected_response_schema"]["required_fields"]["symbol"] == f"literal_{symbol}"
            assert d["event_max_raw_response_bytes"] == 32768
            assert http_core["max_raw_response_bytes"] == 32768

        # Unchanged keys retain original values
        for k in ("scheme", "host", "path", "method", "timeout_sec"):
            if k in base_core:
                assert http_core[k] == base_core[k]

    # Invalid attestation rejects with ValueError("sha256_invalid")
    with pytest.raises(ValueError, match="sha256_invalid"):
        derive_event_profile_core(
            event_id="e" * 64,
            source_article_id="123456",
            source_detail_revision_id="rev_1",
            canonical_symbol=symbol,
            base_e_a_manifest_id=base_manifest_id,
            base_e_a_profile_id="binance_usdm_rest_depth_v1",
            base_e_a_profile_attestation_sha256="not_a_valid_sha256",
            base_e_a_profile_core=E_A_PROFILE_CORES["binance_usdm_rest_depth_v1"],
        )


def test_derived_profile_core_dependency_mutation():
    base_manifest_id = "e918b344b6781bbdb0cd005b3744acf3bb0d370e98ddd5c2973312dc974874b3"
    symbol = "REEFUSDT"
    base_pid = "binance_usdm_rest_depth_v1"
    base_core = E_A_PROFILE_CORES[base_pid]

    sentinel_a = "1" * 64
    sentinel_b = "2" * 64
    assert sentinel_a != compute_profile_attestation_sha256(base_core)
    assert sentinel_b != compute_profile_attestation_sha256(base_core)

    derived_a = derive_event_profile_core(
        event_id="e" * 64,
        source_article_id="123456",
        source_detail_revision_id="rev_1",
        canonical_symbol=symbol,
        base_e_a_manifest_id=base_manifest_id,
        base_e_a_profile_id=base_pid,
        base_e_a_profile_attestation_sha256=sentinel_a,
        base_e_a_profile_core=base_core,
    )
    derived_b = derive_event_profile_core(
        event_id="e" * 64,
        source_article_id="123456",
        source_detail_revision_id="rev_1",
        canonical_symbol=symbol,
        base_e_a_manifest_id=base_manifest_id,
        base_e_a_profile_id=base_pid,
        base_e_a_profile_attestation_sha256=sentinel_b,
        base_e_a_profile_core=base_core,
    )

    assert derived_a.base_e_a_profile_attestation_sha256 == sentinel_a
    assert derived_b.base_e_a_profile_attestation_sha256 == sentinel_b
    assert derived_a.profile_attestation_sha256 != derived_b.profile_attestation_sha256
    assert derived_a.to_dict() != derived_b.to_dict()



def test_slot_intent_and_market_observation_grammar():
    slot_id = compute_slot_id(
        event_id="e" * 64,
        base_e_a_profile_id="binance_usdm_rest_depth_v1",
        canonical_symbol="REEFUSDT",
        slot_family="depth_60s",
        slot_index=0,
        due_at_ms=100000,
    )
    assert len(slot_id) == 64

    # Slot intent
    intent = SlotIntent.create(
        slot_id=slot_id,
        request_identity="1" * 64,
        request_sequence=1,
        base_e_a_profile_id="binance_usdm_rest_depth_v1",
        canonical_symbol="REEFUSDT",
        due_at_ms=100000,
        reserved_at_ms=100010,
        stage="prepared",
    )
    assert intent.to_dict()["stage"] == "prepared"

    # Valid observation: verified_response
    obs_verified = MarketObservation.create_verified(
        event_id="e" * 64,
        slot_id=slot_id,
        slot_family="depth_60s",
        slot_index=0,
        due_at_ms=100000,
        dispatch_started_at_ms=100010,
        completed_at_ms=100050,
        canonical_symbol="REEFUSDT",
        base_e_a_profile_id="binance_usdm_rest_depth_v1",
        profile_attestation_sha256="4" * 64,
        request_identity="req_id_1",
        request_sequence=1,
        http_status=200,
        response_headers_subset={"content-type": "application/json"},
        raw_sha256="5" * 64,
        raw_relative_path="raw/body_1.body",
        raw_byte_count=1234,
    )
    assert validate_market_observation_dict(obs_verified.to_dict()) is True

    # Valid observation: slot_missed_deadline
    obs_missed = MarketObservation.create_missed_deadline(
        event_id="e" * 64,
        slot_id=slot_id,
        slot_family="depth_60s",
        slot_index=0,
        due_at_ms=100000,
        completed_at_ms=160001,
        canonical_symbol="REEFUSDT",
        base_e_a_profile_id="binance_usdm_rest_depth_v1",
        profile_attestation_sha256="4" * 64,
        request_identity="req_id_1",
    )
    assert validate_market_observation_dict(obs_missed.to_dict()) is True

    # Valid observation: request_outcome_unknown_after_restart
    obs_unknown = MarketObservation.create_unknown_after_restart(
        event_id="e" * 64,
        slot_id=slot_id,
        slot_family="depth_60s",
        slot_index=0,
        due_at_ms=100000,
        completed_at_ms=105000,
        canonical_symbol="REEFUSDT",
        base_e_a_profile_id="binance_usdm_rest_depth_v1",
        profile_attestation_sha256="4" * 64,
        request_identity="req_id_1",
        request_sequence=1,
    )
    assert validate_market_observation_dict(obs_unknown.to_dict()) is True


def test_event_checkpoint_validation():
    chk = EventCheckpoint.create(
        event_id="e" * 64,
        event_contract_sha256="c" * 64,
        profile_attestation_sha256_by_symbol_and_profile={"REEFUSDT:depth": "a" * 64},
        completed_slot_ids_ordered=["s1", "s2"],
        last_observation_sha256="0" * 64,
        accounted_root_bytes=1000,
        inflight_slot_intent=None,
        updated_at_ms=5000,
    )
    d = chk.to_dict()
    assert validate_event_checkpoint_dict(d) is True

    # Unordered completed slots rejected
    d_bad = dict(d)
    d_bad["completed_slot_ids_ordered"] = ["s2", "s1"]
    with pytest.raises(ValueError, match="completed_slot_ids_not_lexicographic"):
        validate_event_checkpoint_dict(d_bad)


def test_event_contract_and_terminal_statuses():
    contract = EventContract(
        schema_version="stage1_6e_b_event_contract_v1",
        event_id="e" * 64,
        supervisor_run_id="run_1",
        semantic_projection_id="p" * 64,
        semantic_projection_row_sha256="1" * 64,
        admission_id="a" * 64,
        admission_row_sha256="2" * 64,
        source_article_id="12345",
        source_detail_revision_id="rev_1",
        source_detail_raw_sha256="3" * 64,
        source_checkpoint_id="4" * 64,
        source_checkpoint_sha256="5" * 64,
        effective_delist_time_ms=5000000,
        event_window_started_at_ms=1000000,
        event_window_ends_at_ms=44200000,
        window_duration_ms=43200000,
        canonical_symbols_ordered=["REEFUSDT"],
        canonical_symbols_normalized=["REEFUSDT"],
        symbol_set_sha256="6" * 64,
        expected_slot_count=1586,
        e_a_manifest_id="7" * 64,
        e_a_manifest_sha256="8" * 64,
        e_a_profile_attestation_sha256_by_id={},
        execution_environment_attestation_sha256="9" * 64,
        storage_contract={},
        permissions=stage1_6e_b_permissions(),
    )
    assert contract.to_dict()["schema_version"] == "stage1_6e_b_event_contract_v1"

    event_term = EventTerminalStatus(
        schema_version="stage1_6e_b_terminal_status_v1",
        event_id="e" * 64,
        status="complete",
        coverage_status="complete",
        terminal_reason=None,
        event_window_started_at_ms=1000000,
        event_window_ends_at_ms=44200000,
        terminal_at_ms=44260000,
        expected_slot_count=1586,
        durable_slot_count=1586,
        successful_slot_count=1586,
        failed_slot_count=0,
        missed_slot_count=0,
        per_symbol_slot_counts=[{
            "canonical_symbol": "REEFUSDT",
            "expected_slot_count": 1586,
            "successful_slot_count": 1586,
            "failed_slot_count": 0,
            "missed_slot_count": 0,
        }],
        accounted_root_bytes=500000,
        permissions=stage1_6e_b_permissions(),
    )
    assert event_term.to_dict()["status"] == "complete"

    sup_term = SupervisorTerminalStatus(
        schema_version="stage1_6e_b_supervisor_terminal_status_v1",
        supervisor_run_id="run_1",
        status="failed",
        terminal_reason="source_degraded_unrecoverable",
        terminal_at_ms=2000000,
        accounted_root_bytes=10000,
        permissions=stage1_6e_b_permissions(),
    )
    assert sup_term.to_dict()["status"] == "failed"


