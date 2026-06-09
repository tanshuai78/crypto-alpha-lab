import json
from pathlib import Path

from scripts.run_factor_lab_stageA2_regime_cash_fallback import main


def test_stageA2_cli_empty_fixture_writes_data_unavailable_summary(tmp_path: Path):
    fixture = tmp_path / "empty.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main(["--offline-sample", str(fixture), "--output", str(output)])

    assert result == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "stageA2_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"
    assert summary["live_usage"] == "not_allowed"


def test_stageA2_cli_fail_on_decision_returns_nonzero_for_unavailable_data(tmp_path: Path):
    fixture = tmp_path / "empty.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main([
        "--offline-sample",
        str(fixture),
        "--output",
        str(output),
        "--fail-on-decision",
    ])

    assert result == 1


def test_stageA2_cli_rejects_unsupported_exchange(tmp_path: Path):
    output = tmp_path / "summary.json"

    result = main(["--exchange", "okx", "--output", str(output)])

    assert result == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "stageA2_data_unavailable"
    assert summary["primary_blocker"] == "unsupported_exchange: okx"
