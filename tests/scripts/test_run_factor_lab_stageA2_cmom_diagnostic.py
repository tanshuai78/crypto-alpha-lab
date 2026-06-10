from __future__ import annotations

import json
from pathlib import Path

from scripts.run_factor_lab_stageA2_cmom_diagnostic import main


def test_stageA2_cmom_cli_empty_fixture_writes_data_unavailable(tmp_path: Path) -> None:
    fixture = tmp_path / "empty.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main(["--offline-sample", str(fixture), "--output", str(output)])

    assert result == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "stageA2_cmom_data_unavailable"
    assert summary["live_usage"] == "not_allowed"
    assert summary["paper_shadow_allowed"] is False


def test_stageA2_cmom_cli_fail_on_decision_returns_nonzero_for_data_unavailable(tmp_path: Path) -> None:
    fixture = tmp_path / "empty.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main([
        "--offline-sample", str(fixture),
        "--output", str(output),
        "--fail-on-stop",
    ])

    assert result == 1
