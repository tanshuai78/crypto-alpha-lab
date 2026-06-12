import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_jsonl(path: str):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


BASE_TIME = 1781165880000  # 2026-06-12 UTC approx


def _manual_payload(**overrides):
    payload = {
        "source": "gate_marketanalysis_manual_export",
        "source_vendor": "gate",
        "source_surface": "gate_big_data_dashboard",
        "source_capture_method": "manual_export",
        "source_skill": "gate_exchange_marketanalysis",
        "data_quality": "manual_export",
        "capture_id": "gate_big_data_20260612_001",
        "captured_by": "manual",
        "source_observed_at_ms": BASE_TIME,
        "fetched_at_ms": BASE_TIME,
        "available_at_ms": BASE_TIME,
        "manual_transform_version": "stage1_1_v0",
        "field_confidence": {
            "event_time_ms": "source_provided",
            "symbol": "source_provided",
            "score": "source_native",
        },
        "raw_payload": {
            "event_type": "cex_market_tape_anomaly",
            "chain": "cex",
            "symbol": "SOLUSDT",
            "event_time_ms": BASE_TIME - 480_000,
            "score": 78.0,
            "score_scale": "source_native",
            "score_interpretation_allowed": False,
            "metadata": {"event_time_policy": "source_provided"},
        },
    }
    payload.update(overrides)
    return payload


def _base_stage1_1_summary(**overrides):
    payload = {
        "source": "gate_marketanalysis_manual_export",
        "raw_payload_count": 20,
        "emitted_event_count": 5,
        "deduped_payload_count": 0,
        "quarantined_payload_count": 15,
        "rejected_payload_count": 0,
        "summary_accounting_ok": True,
        "output_file": "events.jsonl",
        "output_file_sha256": "abc",
        "live_trading_enabled": False,
        "exchange_paper_trading_allowed": False,
        "execution_engine_allowed": False,
        "research_shadow_replay_allowed": True,
        "wallet_required": False,
        "unique_symbol_count": 3,
        "unique_event_time_bucket_count": 3,
        "event_time_fallback_ratio": 0.0,
        "duplicate_ratio": 0.0,
        "price_mapping_unavailable_ratio": 0.0,
        "rejected_payload_ratio": 0.0,
        "unknown_event_type_ratio": 0.0,
        "missing_required_field_ratio": 0.0,
        "single_symbol_dominance_ratio": 0.50,
        "single_time_bucket_dominance_ratio": 0.50,
        "stage0_replay_eligible_event_count": 0,
        "stage0_observation_only_event_count": 5,
        "directionless_event_count": 5,
        "avoid_event_count": 0,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Task 2: Source profile
# ---------------------------------------------------------------------------

def test_gate_manual_source_profile_uses_internal_source_id():
    from src.research.external_signal_shadow.source_profiles import get_source_profile

    profile = get_source_profile("gate_marketanalysis_manual_export")

    assert profile.source == "gate_marketanalysis_manual_export"
    assert profile.source_vendor == "gate"
    assert profile.source_surface == "gate_big_data_dashboard"
    assert profile.source_capture_method == "manual_export"
    assert profile.source_skill == "gate_exchange_marketanalysis"
    assert "BTCUSDT" in profile.allowed_symbols


def test_raw_skill_payload_accepts_complete_manual_provenance_fields():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = RawSkillPayload.from_dict(_manual_payload())

    assert payload.source_vendor == "gate"
    assert payload.source_surface == "gate_big_data_dashboard"
    assert payload.source_capture_method == "manual_export"
    assert payload.capture_id == "gate_big_data_20260612_001"
    assert payload.field_confidence["event_time_ms"] == "source_provided"


def test_manual_export_rejects_missing_capture_id():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = _manual_payload()
    payload.pop("capture_id")

    with pytest.raises(ValueError, match="capture_id"):
        RawSkillPayload.from_dict(payload)


def test_manual_export_source_profile_mismatch_rejected():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    with pytest.raises(ValueError, match="source profile"):
        RawSkillPayload.from_dict(_manual_payload(source_vendor="binance"))


def test_field_confidence_value_must_be_allowed():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = _manual_payload()
    payload["field_confidence"]["event_time_ms"] = "manual_guess"

    with pytest.raises(ValueError, match="field_confidence"):
        RawSkillPayload.from_dict(payload)


def test_available_at_fallback_requires_event_time_equals_available_at():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = _manual_payload()
    payload["field_confidence"]["event_time_ms"] = "available_at_fallback"
    payload["raw_payload"]["metadata"]["event_time_policy"] = "available_at_fallback"
    payload["raw_payload"]["event_time_ms"] = payload["available_at_ms"] - 60_000

    with pytest.raises(ValueError, match="available_at_fallback"):
        RawSkillPayload.from_dict(payload)


def test_score_interpretation_allowed_must_be_false_for_manual_source():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = _manual_payload()
    payload["raw_payload"]["score_interpretation_allowed"] = True

    with pytest.raises(ValueError, match="score_interpretation_allowed"):
        RawSkillPayload.from_dict(payload)


# ---------------------------------------------------------------------------
# Task 3: Fixture shape
# ---------------------------------------------------------------------------

def test_stage1_1_fixture_has_minimum_manual_payload_shape():
    rows = _load_jsonl("tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl")

    assert len(rows) >= 20
    assert {row["source"] for row in rows} == {"gate_marketanalysis_manual_export"}
    assert all(row["source_vendor"] == "gate" for row in rows)
    assert all(row["source_surface"] == "gate_big_data_dashboard" for row in rows)
    assert all(row["source_capture_method"] == "manual_export" for row in rows)
    assert all(row["data_quality"] == "manual_export" for row in rows)
    assert all("capture_id" in row for row in rows)
    assert all("field_confidence" in row for row in rows)


def test_stage1_1_fixture_contains_quality_edge_cases():
    rows = _load_jsonl("tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl")
    symbols = {row["raw_payload"].get("symbol") for row in rows}
    policies = {row["raw_payload"].get("metadata", {}).get("event_time_policy") for row in rows}

    assert {"BTCUSDT", "ETHUSDT", "SOLUSDT"}.issubset(symbols)
    assert "available_at_fallback" in policies
    assert any(row["raw_payload"].get("symbol") == "PEPEUSDT" for row in rows)


# ---------------------------------------------------------------------------
# Task 4: Whitelist & event-time policy
# ---------------------------------------------------------------------------

def test_stage1_1_quarantines_symbol_outside_allowed_universe(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="gate_marketanalysis_manual_export",
    )

    assert summary["quarantine_reason_counts"]["unsupported_stage1_1_symbol"] >= 1


def test_stage1_1_available_at_fallback_not_counted_in_latency_percentiles(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="gate_marketanalysis_manual_export",
    )

    assert summary["event_time_fallback_count"] >= 1
    assert summary["event_time_fallback_ratio"] > 0.0
    assert summary["latency_sample_count"] < summary["emitted_event_count"]


# ---------------------------------------------------------------------------
# Task 5: Quality metrics
# ---------------------------------------------------------------------------

def test_stage1_1_summary_reports_quality_and_handoff_metrics(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="gate_marketanalysis_manual_export",
    )

    assert summary["source_vendor"] == "gate"
    assert summary["source_surface"] == "gate_big_data_dashboard"
    assert summary["source_capture_method"] == "manual_export"
    assert summary["unique_symbol_count"] >= 3
    assert summary["unique_event_time_bucket_count"] >= 3
    assert 0.0 <= summary["duplicate_ratio"] <= 1.0
    assert 0.0 <= summary["price_mapping_unavailable_ratio"] <= 1.0
    assert 0.0 <= summary["rejected_payload_ratio"] <= 1.0
    assert 0.0 <= summary["unknown_event_type_ratio"] <= 1.0
    assert 0.0 <= summary["missing_required_field_ratio"] <= 1.0
    assert 0.0 <= summary["single_symbol_dominance_ratio"] <= 1.0
    assert 0.0 <= summary["single_time_bucket_dominance_ratio"] <= 1.0
    assert "minimal_connector_pass" in summary
    assert "stage0_handoff_ready" in summary
    assert "stage0_handoff_blockers" in summary


def test_stage1_1_quality_ratios_handle_zero_denominators():
    from src.research.external_signal_shadow.connector_summary import _safe_ratio

    assert _safe_ratio(1, 0) == 0.0
    assert _safe_ratio(0, 0) == 0.0
    assert _safe_ratio(1, 4) == 0.25


def test_stage1_1_summary_reports_unknown_and_missing_required_field_ratios(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="gate_marketanalysis_manual_export",
    )

    assert "unknown_event_type_ratio" in summary
    assert "missing_required_field_ratio" in summary
    assert summary["unknown_event_type_ratio"] > 0.0


# ---------------------------------------------------------------------------
# Task 6: Handoff gate & mode & failure classification
# ---------------------------------------------------------------------------

def test_stage1_1_handoff_ready_requires_density_not_just_one_event():
    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    summary = _base_stage1_1_summary(
        raw_payload_count=10,
        emitted_event_count=1,
        unique_symbol_count=1,
        unique_event_time_bucket_count=1,
        single_symbol_dominance_ratio=1.0,
        single_time_bucket_dominance_ratio=1.0,
    )

    result = decide_stage1_connector_summary(summary)

    assert result["minimal_connector_pass"] is True
    assert result["stage0_handoff_ready"] is False
    assert "insufficient_emitted_events" in result["stage0_handoff_blockers"]


def test_price_mapping_failure_when_unavailable_ratio_high():
    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    result = decide_stage1_connector_summary(
        _base_stage1_1_summary(price_mapping_unavailable_ratio=0.60)
    )

    assert result["decision"] == "external_signal_connector_stage1_failed"
    assert result["failure_type"] == "price_mapping_failure"
    assert result["primary_blocker"] == "price_mapping_unavailable_high"


def test_stage1_1_source_quality_failure_when_event_time_unreliable():
    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    result = decide_stage1_connector_summary(
        _base_stage1_1_summary(event_time_fallback_ratio=0.80)
    )

    assert result["decision"] == "external_signal_connector_stage1_failed"
    assert result["failure_type"] == "source_quality_failure"
    assert result["primary_blocker"] == "event_time_unreliable"


def test_stage0_handoff_mode_is_observation_only_for_unknown_events():
    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    result = decide_stage1_connector_summary(
        _base_stage1_1_summary(
            stage0_replay_eligible_event_count=0,
            stage0_observation_only_event_count=5,
            directionless_event_count=5,
            avoid_event_count=0,
        )
    )

    assert result["stage0_handoff_mode"] == "observation_only"
    assert result["stage0_directional_replay_ready"] is False
    assert result["stage0_observation_handoff_ready"] is True
