import json
import subprocess
import sys
from pathlib import Path


def _run_review(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/review_external_signal_shadow_stage1_1_manual_dry_run.py"] + args,
        capture_output=True,
        text=True,
    )


def _make_summary(tmp_path, **overrides) -> Path:
    summary = {
        "source": "gate_marketanalysis_manual_export",
        "source_vendor": "gate",
        "source_surface": "gate_big_data_dashboard",
        "source_capture_method": "manual_export",
        "connector_version": "stage1_v0",
        "schema_version": "external_signal_event_v1",
        "decision": "external_signal_connector_stage1_passed",
        "failure_type": "connector_completed",
        "primary_blocker": None,
        "minimal_connector_pass": True,
        "stage0_handoff_ready": True,
        "stage0_handoff_mode": "observation_only",
        "stage0_handoff_blockers": [],
        "stage0_directional_replay_ready": False,
        "stage0_observation_handoff_ready": True,
        "raw_payload_count": 21,
        "emitted_event_count": 5,
        "deduped_payload_count": 2,
        "quarantined_payload_count": 12,
        "rejected_payload_count": 2,
        "summary_accounting_ok": True,
        "output_file": "/tmp/events.jsonl",
        "output_file_sha256": "abc123",
        "event_time_fallback_ratio": 0.1,
        "duplicate_ratio": 0.095,
        "price_mapping_unavailable_ratio": 0.0,
        "rejected_payload_ratio": 0.095,
        "unknown_event_type_ratio": 0.048,
        "missing_required_field_ratio": 0.0,
        "single_symbol_dominance_ratio": 0.25,
        "single_time_bucket_dominance_ratio": 0.06,
        "unique_symbol_count": 5,
        "unique_event_time_bucket_count": 5,
        "latency_p50_ms": 480000,
        "latency_p95_ms": 480000,
        "latency_sample_count": 4,
        "reject_reason_counts": {"unsupported_event_type": 1},
        "quarantine_reason_counts": {"unsupported_stage1_1_symbol": 1, "stale_latency": 2},
    }
    summary.update(overrides)
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False))
    return path


def test_review_writes_chinese_markdown(tmp_path):
    summary_path = _make_summary(tmp_path)
    out_path = tmp_path / "review.md"

    result = _run_review([
        "--summary", str(summary_path),
        "--output", str(out_path),
    ])

    assert result.returncode == 0, result.stderr
    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")

    assert "stage0_handoff_ready" in text
    assert "stage0_handoff_mode" in text
    assert "不是 alpha 通过" in text or "禁止" in text or "不构成任何 alpha" in text


def test_review_observation_only_conclusion_does_not_allow_directional_replay(tmp_path):
    summary_path = _make_summary(
        tmp_path,
        stage0_handoff_ready=True,
        stage0_handoff_mode="observation_only",
        stage0_directional_replay_ready=False,
        stage0_observation_handoff_ready=True,
    )
    out_path = tmp_path / "review.md"

    result = _run_review(["--summary", str(summary_path), "--output", str(out_path)])

    assert result.returncode == 0, result.stderr
    text = out_path.read_text(encoding="utf-8")
    assert "Stage 0 observation-only 交接就绪" in text
    assert "directional replay 不就绪" in text
    assert "observation 或 directional replay 可进行" not in text


def test_review_does_not_contain_english_headings(tmp_path):
    summary_path = _make_summary(tmp_path)
    out_path = tmp_path / "review.md"

    _run_review(["--summary", str(summary_path), "--output", str(out_path)])

    text = out_path.read_text(encoding="utf-8")
    for forbidden in ("## Conclusion", "## Summary", "## Result"):
        assert forbidden not in text, f"English heading found: {forbidden}"


def test_review_exits_error_when_summary_missing(tmp_path):
    out_path = tmp_path / "review.md"

    result = _run_review([
        "--summary", str(tmp_path / "nonexistent.json"),
        "--output", str(out_path),
    ])

    assert result.returncode == 1
