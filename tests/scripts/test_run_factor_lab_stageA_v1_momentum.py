from __future__ import annotations

import json

from scripts.run_factor_lab_stageA_v1_momentum import main


def test_cli_empty_fixture_writes_data_unavailable_summary(tmp_path) -> None:
    fixture = tmp_path / "fixture.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main(["--offline-sample", str(fixture), "--output", str(output)])

    assert result == 0
    assert output.exists()
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "stageA_v1_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"


def test_cli_summary_marks_not_live_safe(tmp_path) -> None:
    fixture = tmp_path / "fixture.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    main(["--offline-sample", str(fixture), "--output", str(output)])

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["live_usage"] == "not_allowed"


def test_cli_fail_on_decision_returns_nonzero_for_data_unavailable(tmp_path) -> None:
    fixture = tmp_path / "fixture.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main(["--offline-sample", str(fixture), "--output", str(output), "--fail-on-decision"])

    assert result == 1
