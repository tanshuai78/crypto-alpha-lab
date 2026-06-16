"""
tests/scripts/external_signal_shadow/test_run_stage1_4a2_vendor_liquidation_data_feasibility.py
"""
import json

from scripts.external_signal_shadow.run_stage1_4a2_vendor_liquidation_data_feasibility import main
from tests.research.external_signal_shadow.stage1_4a2_vendor_fixtures import (
    base_vendor_audit_payload,
)


def test_cli_writes_degraded_summary_for_docs_only_fixture(tmp_path) -> None:
    output = tmp_path / "summary.json"
    rc = main([
        "--vendor-audits",
        "tests/fixtures/external_signal_shadow/stage1_4a2_vendor_audits_docs_only.json",
        "--output-summary",
        str(output),
    ])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "vendor_liquidation_source_degraded"
    assert summary["stage1_4b_candidate_replay_allowed"] is False


def test_cli_does_not_read_vendor_api_key_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TARDIS_API_KEY", "LEAK_CHECK")
    output = tmp_path / "summary.json"
    rc = main([
        "--vendor-audits",
        "tests/fixtures/external_signal_shadow/stage1_4a2_vendor_audits_with_sample.json",
        "--output-summary",
        str(output),
    ])
    assert rc == 0
    text = output.read_text(encoding="utf-8")
    assert "LEAK_CHECK" not in text
    summary = json.loads(text)
    assert summary["purchase_allowed"] is False


def test_feasible_requires_existing_sample_file_when_sample_file_available_true(tmp_path) -> None:
    payload = base_vendor_audit_payload()
    payload["sample_file_path"] = "data/external_signal_shadow/vendor_liquidation_samples/tardis_dev/missing.jsonl"
    payload["sample_file_audited"] = False
    audit_path = tmp_path / "audits.json"
    audit_path.write_text(json.dumps([payload]), encoding="utf-8")
    output = tmp_path / "summary.json"
    rc = main(["--vendor-audits", str(audit_path), "--output-summary", str(output)])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "vendor_liquidation_source_degraded"
    assert summary["primary_blocker"] == "sample_file_not_verified"


def test_sample_file_path_must_be_under_gitignored_vendor_sample_dir(tmp_path) -> None:
    bad_sample = tmp_path / "sample.jsonl"
    bad_sample.write_text(
        '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"long_liquidation_usd":1000,"short_liquidation_usd":0}\n',
        encoding="utf-8",
    )
    payload = base_vendor_audit_payload()
    payload["sample_file_available"] = True
    payload["sample_file_path"] = str(bad_sample)
    payload["sample_file_audited"] = False
    audit_path = tmp_path / "audits.json"
    audit_path.write_text(json.dumps([payload]), encoding="utf-8")
    output = tmp_path / "summary.json"
    rc = main(["--vendor-audits", str(audit_path), "--output-summary", str(output)])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["primary_blocker"] == "sample_file_not_under_runtime_vendor_dir"


def test_sample_audit_conflict_blocks_feasible(tmp_path) -> None:
    runtime_dir = tmp_path / "data" / "external_signal_shadow" / "vendor_liquidation_samples" / "tardis_dev"
    runtime_dir.mkdir(parents=True)
    sample_path = runtime_dir / "sample.jsonl"
    sample_path.write_text(
        '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"notional_usd":1000}\n',
        encoding="utf-8",
    )
    payload = base_vendor_audit_payload()
    payload["sample_file_path"] = str(sample_path)
    payload["side_available"] = True
    payload["sample_file_audited"] = False
    audit_path = tmp_path / "audits.json"
    audit_path.write_text(json.dumps([payload]), encoding="utf-8")
    output = tmp_path / "summary.json"
    rc = main([
        "--vendor-audits",
        str(audit_path),
        "--output-summary",
        str(output),
        "--sample-dir",
        str(tmp_path / "data" / "external_signal_shadow" / "vendor_liquidation_samples"),
    ])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["primary_blocker"] == "sample_audit_conflict"
