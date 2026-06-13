from __future__ import annotations

import json
from pathlib import Path

from scripts.collect_gate_public_market_snapshot_stage1_2 import main


def test_cli_rejects_mock_and_live_flag_together(tmp_path: Path) -> None:
    output = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    result = main([
        "--mock-response",
        "tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json",
        "--live-public-readonly",
        "--output",
        str(output),
        "--output-summary",
        str(summary),
    ])
    assert result != 0
    payload = json.loads(summary.read_text())
    assert payload["failure_type"] == "conflicting_mock_and_live_public_readonly"


def test_collector_does_not_read_api_key_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GATE_API_KEY", "SHOULD_NOT_BE_USED")
    monkeypatch.setenv("GATE_SECRET", "SHOULD_NOT_BE_USED")
    output = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    result = main([
        "--mock-response",
        "tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json",
        "--output",
        str(output),
        "--output-summary",
        str(summary),
    ])
    assert result == 0
    combined = output.read_text() + summary.read_text()
    assert "SHOULD_NOT_BE_USED" not in combined
    assert json.loads(summary.read_text())["api_key_used"] is False


def test_cli_requires_live_flag_or_mock_response(tmp_path: Path) -> None:
    output = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    result = main(["--output", str(output), "--output-summary", str(summary)])
    assert result != 0
    assert summary.exists()
    payload = json.loads(summary.read_text())
    assert payload["decision"] == "external_signal_collector_stage1_2_failed"
    assert payload["failure_type"] == "missing_mock_or_live_public_readonly_flag"


def test_cli_mock_response_writes_raw_jsonl(tmp_path: Path) -> None:
    output = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    result = main([
        "--mock-response",
        "tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json",
        "--output",
        str(output),
        "--output-summary",
        str(summary),
    ])
    assert result == 0
    assert output.exists()
    assert len(output.read_text().splitlines()) == 5
    summary_payload = json.loads(summary.read_text())
    assert summary_payload["collector_minimal_pass"] is True
    assert summary_payload["network_mode"] == "mock"
    assert summary_payload["event_density_alpha_valid"] is False
