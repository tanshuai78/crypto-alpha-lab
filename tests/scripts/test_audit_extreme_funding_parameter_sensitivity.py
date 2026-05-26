import json

from scripts.audit_extreme_funding_parameter_sensitivity import run_parameter_sensitivity_audit
from src.research.extreme_funding_basis_replay import build_historical_basis_row


def _write_basis_rows(path):
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=110.0,
            spot_mid_price=100.0,
            perp_mid_price=100.10,
        ),
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=2000,
            funding_rate=0.007,
            annualized_pct=120.0,
            spot_mid_price=100.0,
            perp_mid_price=100.05,
        ),
    ]
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.__dict__, sort_keys=True) + "\n")


def test_audit_cli_writes_candidate_and_shadow_json(tmp_path) -> None:
    input_path = tmp_path / "basis_rows.jsonl"
    output_dir = tmp_path / "reports"
    _write_basis_rows(input_path)

    result = run_parameter_sensitivity_audit(
        input_path=input_path,
        output_dir=output_dir,
        tag="test_doge",
    )

    assert result["candidate_output"].exists()
    assert result["shadow_output"].exists()

    candidate_summary = json.loads(result["candidate_output"].read_text(encoding="utf-8"))
    shadow_summary = json.loads(result["shadow_output"].read_text(encoding="utf-8"))
    assert candidate_summary["status"] == "ok"
    assert shadow_summary["status"] == "ok"


def test_audit_cli_handles_empty_input_with_status_flag(tmp_path) -> None:
    input_path = tmp_path / "empty.jsonl"
    output_dir = tmp_path / "reports"
    input_path.write_text("", encoding="utf-8")

    result = run_parameter_sensitivity_audit(
        input_path=input_path,
        output_dir=output_dir,
        tag="empty",
    )

    candidate_summary = json.loads(result["candidate_output"].read_text(encoding="utf-8"))
    shadow_summary = json.loads(result["shadow_output"].read_text(encoding="utf-8"))

    assert candidate_summary["status"] == "insufficient_basis_data"
    assert shadow_summary["status"] == "insufficient_basis_data"


def test_audit_cli_includes_decision_gate_fields(tmp_path) -> None:
    input_path = tmp_path / "basis_rows.jsonl"
    output_dir = tmp_path / "reports"
    _write_basis_rows(input_path)

    result = run_parameter_sensitivity_audit(
        input_path=input_path,
        output_dir=output_dir,
        tag="gate_fields",
    )
    candidate_summary = json.loads(result["candidate_output"].read_text(encoding="utf-8"))

    assert candidate_summary["candidate_summaries"]
    first = candidate_summary["candidate_summaries"][0]
    assert "param_set" in first
    assert "assumption_level" in first["param_set"]
    assert "candidate_count" in first
    assert "top_reject_reason" in first


def test_audit_output_contains_admission_layer_counts(tmp_path) -> None:
    input_path = tmp_path / "basis_rows.jsonl"
    output_dir = tmp_path / "reports"
    _write_basis_rows(input_path)

    result = run_parameter_sensitivity_audit(
        input_path=input_path,
        output_dir=output_dir,
        tag="admission_counts",
    )
    candidate_summary = json.loads(result["candidate_output"].read_text(encoding="utf-8"))
    first = candidate_summary["candidate_summaries"][0]
    assert "admission_layer_counts" in first
    assert "research_to_trade_blocker_counts" in first
    assert "strategy_depends_on_funding_persistence" in candidate_summary["decision_gate_snapshot"]
