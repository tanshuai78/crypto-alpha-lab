import json
import subprocess
import sys


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/run_external_signal_shadow_stage1_1_manual_dry_run.py"] + args,
        capture_output=True,
        text=True,
    )


def test_cli_writes_events_and_summary(tmp_path):
    out_events = tmp_path / "events.jsonl"
    out_summary = tmp_path / "summary.json"

    result = _run_cli([
        "--input", "tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl",
        "--price-map", "tests/fixtures/external_signal_shadow/stage1_price_map.json",
        "--output-events", str(out_events),
        "--output-summary", str(out_summary),
    ])

    assert result.returncode == 0, result.stderr
    assert out_events.exists()
    assert out_summary.exists()

    summary = json.loads(out_summary.read_text())
    assert summary["source"] == "gate_marketanalysis_manual_export"
    assert "stage0_handoff_ready" in summary
    assert "stage0_handoff_mode" in summary
    assert "minimal_connector_pass" in summary


def test_cli_rejects_external_api_flag(tmp_path):
    out_events = tmp_path / "events.jsonl"
    out_summary = tmp_path / "summary.json"

    result = _run_cli([
        "--input", "tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl",
        "--price-map", "tests/fixtures/external_signal_shadow/stage1_price_map.json",
        "--output-events", str(out_events),
        "--output-summary", str(out_summary),
        "--external-api",
    ])

    assert result.returncode == 1
    assert "external-api" in result.stderr.lower() or "not permitted" in result.stderr.lower()


def test_cli_exits_data_failure_when_input_missing(tmp_path):
    out_events = tmp_path / "events.jsonl"
    out_summary = tmp_path / "summary.json"

    result = _run_cli([
        "--input", "data/nonexistent/raw/2099-01-01.jsonl",
        "--price-map", "tests/fixtures/external_signal_shadow/stage1_price_map.json",
        "--output-events", str(out_events),
        "--output-summary", str(out_summary),
    ])

    assert result.returncode == 1
    assert out_summary.exists()
    summary = json.loads(out_summary.read_text())
    assert summary["failure_type"] == "data_failure"
