import json

import pytest


def test_external_signal_stage1_connector_config_constants_exist():
    from configs import base

    assert base.EXTERNAL_SIGNAL_CONNECTOR_EVENT_TIME_BUCKET_MS == 5 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_CONNECTOR_MAX_CEX_LATENCY_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_CONNECTOR_MAX_ONCHAIN_LATENCY_MS == 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_CONNECTOR_MAX_MANUAL_FIXTURE_LATENCY_MS == 24 * 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_CONNECTOR_VERSION == "stage1_v0"
    assert base.EXTERNAL_SIGNAL_CONNECTOR_SCHEMA_VERSION == "external_signal_event_v1"




def test_raw_skill_payload_requires_raw_payload_dict():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    with pytest.raises(ValueError, match="raw_payload"):
        RawSkillPayload.from_dict({"source": "fixture", "data_quality": "fixture", "source_skill": "fixture", "fetched_at_ms": 1000, "raw_payload": []})


def test_raw_skill_payload_defaults_available_at_to_fetched_at():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = RawSkillPayload.from_dict(
        {
            "source": "fixture",
            "source_skill": "fixture",
            "fetched_at_ms": 2000,
            "raw_payload": {"event_time_ms": 1000},
        }
    )

    assert payload.available_at_ms == 2000


def test_raw_skill_payload_has_explicit_data_quality_default():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = RawSkillPayload.from_dict(
        {
            "source": "fixture",
            "source_skill": "fixture",
            "fetched_at_ms": 2000,
            "raw_payload": {"event_time_ms": 1000},
        }
    )

    assert payload.data_quality == "unknown"




def test_file_backed_connector_fixture_accounting(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    assert summary["raw_payload_count"] == 11
    assert summary["summary_accounting_ok"] is True
    assert summary["raw_payload_count"] == (
        summary["emitted_event_count"]
        + summary["deduped_payload_count"]
        + summary["quarantined_payload_count"]
        + summary["rejected_payload_count"]
    )
    assert summary["emitted_event_count"] == 2
    assert summary["deduped_payload_count"] == 1
    assert summary["quarantined_payload_count"] >= 4
    assert summary["rejected_payload_count"] >= 3
    assert output.exists()


def test_connector_summary_includes_required_audit_fields(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    assert summary["source"] == "fixture"
    assert summary["connector_version"] == "stage1_v0"
    assert summary["schema_version"] == "external_signal_event_v1"
    assert summary["input_files"] == ["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"]
    assert summary["run_id"] == "fixture_stage1_v0"
    assert summary["latency_p50_ms"] == 60_000
    assert summary["latency_p95_ms"] == 60_000
    assert summary["event_type_counts"] == {
        "smart_money_inflow": 1,
        "token_audit_pass": 1,
    }
    assert summary["direction_hint_counts"] == {"long": 1, "unknown": 1}
    assert summary["price_mapping_counts"] == {
        "exact": 1,
        "cex_symbol_proxy": 1,
    }


def test_connector_rejects_forbidden_nested_keys(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(tmp_path / "events.jsonl"),
        source="fixture",
    )

    assert summary["reject_reason_counts"]["forbidden_executable_payload"] == 1


def test_connector_dedupes_semantic_duplicate(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(tmp_path / "events.jsonl"),
        source="fixture",
    )

    assert summary["deduped_payload_count"] == 1


def test_connector_quarantines_missing_price_mapping(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(tmp_path / "events.jsonl"),
        source="fixture",
    )

    assert summary["quarantine_reason_counts"]["price_mapping_unavailable"] == 2


def test_connector_quarantines_missing_chain(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(tmp_path / "events.jsonl"),
        source="fixture",
    )

    assert summary["quarantine_reason_counts"]["missing_chain"] == 1
    assert "schema_invalid" not in summary["reject_reason_counts"]


def test_connector_uses_available_at_for_replay_handoff(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    events = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
    assert events
    for event in events:
        assert event["event_time_ms"] == event["metadata"]["available_at_ms"]
        assert event["metadata"]["available_at_ms"] >= event["metadata"]["original_event_time_ms"]
        assert event["metadata"]["source_latency_ms"] >= 0


def test_normalized_events_are_shadow_only_and_non_executable(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    events = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
    assert events
    for event in events:
        assert event["shadow_only"] is True
        assert event.get("notional_usd", 0.0) == 0.0
        assert "order" not in event
        assert "swap" not in event
        assert "wallet" not in event
        assert "raw_payload" not in event.get("metadata", {})


def test_connector_rejects_source_mismatch(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    payload = {
        "source": "binance_web3",
        "source_skill": "smart_money",
        "fetched_at_ms": 1700000060000,
        "raw_payload": {
            "event_type": "smart_money_inflow",
            "chain": "cex",
            "symbol": "BTCUSDT",
            "event_time_ms": 1700000000000,
        },
    }
    input_path = tmp_path / "payloads.jsonl"
    input_path.write_text(json.dumps(payload) + "\n")

    summary = run_file_backed_connector(
        input_files=[str(input_path)],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(tmp_path / "events.jsonl"),
        source="fixture",
    )

    assert summary["reject_reason_counts"]["source_mismatch"] == 1


def test_connector_keeps_external_notional_in_metadata_only(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    payload = {
        "source": "fixture",
        "source_skill": "smart_money",
        "data_quality": "fixture",
        "fetched_at_ms": 1700000060000,
        "available_at_ms": 1700000060000,
        "raw_payload": {
            "event_type": "smart_money_inflow",
            "chain": "cex",
            "symbol": "BTCUSDT",
            "event_time_ms": 1700000000000,
            "notional_usd": 12345.0,
        },
    }
    input_path = tmp_path / "payloads.jsonl"
    output = tmp_path / "events.jsonl"
    input_path.write_text(json.dumps(payload) + "\n")

    run_file_backed_connector(
        input_files=[str(input_path)],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    event = json.loads(output.read_text())
    assert event["notional_usd"] == 0.0
    assert event["metadata"]["external_notional_usd"] == 12345.0
    assert event["metadata"]["external_notional_usd_semantics"] == "informational_only"


def test_event_id_is_stable_across_repeated_runs(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    kwargs = {
        "input_files": ["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        "price_map_path": "tests/fixtures/external_signal_shadow/stage1_price_map.json",
        "source": "fixture",
    }
    run_file_backed_connector(output_path=str(first), **kwargs)
    run_file_backed_connector(output_path=str(second), **kwargs)

    assert first.read_text() == second.read_text()


def test_connector_does_not_write_raw_payload_to_metadata(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    events = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
    assert events
    assert all("raw_payload" not in event["metadata"] for event in events)


def test_normalized_events_are_stage0_compatible(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector
    from src.research.external_signal_shadow.models import load_events_jsonl

    output = tmp_path / "events.jsonl"
    run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    events = load_events_jsonl(str(output))
    assert len(events) == 2
