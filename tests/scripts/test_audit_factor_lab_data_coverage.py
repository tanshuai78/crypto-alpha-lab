from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_factor_lab_data_coverage import main


def test_audit_factor_lab_data_coverage_writes_summary_json(tmp_path) -> None:
    output_file = tmp_path / "summary.json"
    fixture_path = Path("tests/fixtures/factor_lab/stage0_sample_payload.json")

    # Run CLI main with args
    args = [
        "--offline-sample", str(fixture_path),
        "--output", str(output_file),
        "--history-days", "540"
    ]
    ret = main(args)
    assert ret == 0
    assert output_file.exists()

    with open(output_file, encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["run_mode"] == "stage0_data_coverage_audit"
    assert summary["data_source"] == "binance"
    assert "spot" in summary["market_types"]
    assert "usdt_perp" in summary["market_types"]


def test_cli_supports_offline_sample_payload(tmp_path) -> None:
    output_file = tmp_path / "summary.json"
    fixture_path = Path("tests/fixtures/factor_lab/stage0_sample_payload.json")

    args = [
        "--offline-sample", str(fixture_path),
        "--output", str(output_file)
    ]
    assert main(args) == 0


def test_cli_summary_contains_bias_contract(tmp_path) -> None:
    output_file = tmp_path / "summary.json"
    fixture_path = Path("tests/fixtures/factor_lab/stage0_sample_payload.json")

    args = [
        "--offline-sample", str(fixture_path),
        "--output", str(output_file)
    ]
    main(args)

    with open(output_file, encoding="utf-8") as f:
        summary = json.load(f)

    assert "bias_contract" in summary
    bias = summary["bias_contract"]
    assert bias["survivorship_bias_control"] == "not_controlled"
    assert bias["universe_scope"] == "current_tradable_universe_only"


def test_cli_decision_is_deterministic_for_sample_payload(tmp_path) -> None:
    output_file = tmp_path / "summary.json"
    fixture_path = Path("tests/fixtures/factor_lab/stage0_sample_payload.json")

    args = [
        "--offline-sample", str(fixture_path),
        "--output", str(output_file)
    ]
    main(args)

    with open(output_file, encoding="utf-8") as f:
        summary = json.load(f)

    # In our fixture, we have 3 swap symbols and 2 spot symbols passing liquidity,
    # and their history coverage is >= 95%, so symbols_passing_liquidity >= 30 fails,
    # meaning decision should be factor_lab_data_unavailable.
    # Wait, the threshold for passing liquidity is 30. Let's make sure it is tested correctly.
    assert summary["decision"] == "factor_lab_data_unavailable"


def test_cli_summary_contains_primary_blocker_and_allowed_modes(tmp_path) -> None:
    output_file = tmp_path / "summary.json"
    fixture_path = Path("tests/fixtures/factor_lab/stage0_sample_payload.json")

    args = [
        "--offline-sample", str(fixture_path),
        "--output", str(output_file)
    ]
    main(args)

    with open(output_file, encoding="utf-8") as f:
        summary = json.load(f)

    assert "primary_blocker" in summary
    assert "allowed_next_stage" in summary
    assert "stage_a_allowed_modes" in summary


def test_cli_summary_contains_generated_at_and_network_mode(tmp_path) -> None:
    output_file = tmp_path / "summary.json"
    fixture_path = Path("tests/fixtures/factor_lab/stage0_sample_payload.json")

    args = [
        "--offline-sample", str(fixture_path),
        "--output", str(output_file)
    ]
    main(args)

    with open(output_file, encoding="utf-8") as f:
        summary = json.load(f)

    assert "generated_at_utc" in summary
    assert summary["network_mode"] == "offline_sample"


def test_cli_summary_uses_plan_liquidity_usage_string(tmp_path) -> None:
    output_file = tmp_path / "summary.json"
    fixture_path = Path("tests/fixtures/factor_lab/stage0_sample_payload.json")

    main(["--offline-sample", str(fixture_path), "--output", str(output_file)])

    with open(output_file, encoding="utf-8") as f:
        summary = json.load(f)

    assert (
        summary["current_liquidity_gate"]["usage"]
        == "stage0_screening_only_not_historical_tradability"
    )


def test_cli_summary_contains_allowed_modes_by_market(tmp_path) -> None:
    output_file = tmp_path / "summary.json"
    fixture_path = Path("tests/fixtures/factor_lab/stage0_sample_payload.json")

    main(["--offline-sample", str(fixture_path), "--output", str(output_file)])

    with open(output_file, encoding="utf-8") as f:
        summary = json.load(f)

    assert "stage_a_allowed_modes_by_market" in summary
    assert "spot" in summary["stage_a_allowed_modes_by_market"]
    assert "usdt_perp" in summary["stage_a_allowed_modes_by_market"]


def test_cli_summary_market_readiness_does_not_hide_perp_failure(tmp_path) -> None:
    output_file = tmp_path / "summary.json"
    fixture_path = tmp_path / "perp_failed_payload.json"
    fixture = json.loads(Path("tests/fixtures/factor_lab/stage0_sample_payload.json").read_text())
    fixture["markets"] = [m for m in fixture["markets"] if m["type"] != "spot"]
    for idx in range(30):
        symbol = f"ALT{idx:02d}/USDT"
        normalized = f"ALT{idx:02d}USDT"
        fixture["markets"].append(
            {
                "symbol": symbol,
                "id": normalized,
                "active": True,
                "type": "spot",
                "quote": "USDT",
                "base": f"ALT{idx:02d}",
            }
        )
        fixture["klines"][f"{normalized}_spot"] = {
            "history_length": 540,
            "coverage_ratio": 1.0,
            "median_volume_30d": 25000000.0,
        }
    for key in list(fixture["klines"].keys()):
        if key.endswith("_swap"):
            fixture["klines"][key]["coverage_ratio"] = 0.0
            fixture["klines"][key]["history_length"] = 0
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    main(["--offline-sample", str(fixture_path), "--output", str(output_file), "--history-days", "540"])

    with open(output_file, encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["markets"]["usdt_perp"]["decision"] == "factor_lab_data_unavailable"
    assert summary["stage_a_allowed_modes_by_market"]["usdt_perp"]["price_volume_fast_track"] is False
    assert summary["stage_a_allowed_modes_by_market"]["spot"]["price_volume_fast_track"] is True
