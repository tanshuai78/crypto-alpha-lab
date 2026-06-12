import json


def test_run_stage1_connector_writes_summary_and_events(tmp_path):
    from scripts.run_external_signal_shadow_stage1_connector import main

    output_events = tmp_path / "events.jsonl"
    output_summary = tmp_path / "summary.json"

    result = main(
        [
            "--input",
            "tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl",
            "--price-map",
            "tests/fixtures/external_signal_shadow/stage1_price_map.json",
            "--output-events",
            str(output_events),
            "--output-summary",
            str(output_summary),
            "--source",
            "fixture",
        ]
    )

    assert result == 0
    assert output_events.exists()
    assert output_summary.exists()
    summary = json.loads(output_summary.read_text())
    assert summary["decision"] == "external_signal_connector_stage1_passed"


def test_run_stage1_connector_rejects_external_api_flag(tmp_path):
    from scripts.run_external_signal_shadow_stage1_connector import main

    result = main(
        [
            "--input",
            "tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl",
            "--price-map",
            "tests/fixtures/external_signal_shadow/stage1_price_map.json",
            "--output-events",
            str(tmp_path / "events.jsonl"),
            "--output-summary",
            str(tmp_path / "summary.json"),
            "--source",
            "fixture",
            "--external-api",
        ]
    )

    assert result == 1


def test_run_stage1_connector_outputs_are_stage0_compatible(tmp_path):
    from scripts.run_external_signal_shadow_stage1_connector import main
    from src.research.external_signal_shadow.models import load_events_jsonl

    output_events = tmp_path / "events.jsonl"
    output_summary = tmp_path / "summary.json"
    result = main(
        [
            "--input",
            "tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl",
            "--price-map",
            "tests/fixtures/external_signal_shadow/stage1_price_map.json",
            "--output-events",
            str(output_events),
            "--output-summary",
            str(output_summary),
            "--source",
            "fixture",
        ]
    )

    assert result == 0
    assert load_events_jsonl(str(output_events))
