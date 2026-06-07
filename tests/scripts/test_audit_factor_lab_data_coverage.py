from __future__ import annotations

import json
from pathlib import Path
import pytest
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
