from __future__ import annotations

import json
from pathlib import Path

from scripts.review_external_signal_shadow_stage1_2_collector import main


def test_review_blocks_handoff_when_connector_summary_missing(tmp_path: Path) -> None:
    collector_summary = tmp_path / "collector_summary.json"
    review = tmp_path / "review_CN.md"
    collector_summary.write_text(json.dumps({
        "decision": "external_signal_collector_stage1_2_passed",
        "collector_minimal_pass": True,
    }, ensure_ascii=False))
    result = main([
        "--collector-summary", str(collector_summary),
        "--output", str(review),
    ])
    assert result != 0
    assert "connector_summary_missing" in review.read_text()


def test_stage1_2_review_script_writes_chinese_review(tmp_path: Path) -> None:
    collector_summary = tmp_path / "collector_summary.json"
    connector_summary = tmp_path / "connector_summary.json"
    review = tmp_path / "review_CN.md"
    collector_summary.write_text(json.dumps({
        "decision": "external_signal_collector_stage1_2_passed",
        "collector_minimal_pass": True,
        "connector_minimal_pass": True,
        "stage0_observation_handoff_ready": True,
        "stage0_directional_replay_ready": False,
        "event_density_alpha_valid": False,
        "http_success_count": 5,
        "http_failure_count": 0,
        "raw_payload_count": 5,
        "unique_symbol_count": 5,
        "numeric_parse_failure_count": 0,
        "api_key_used": False,
        "private_endpoint_used": False,
    }, ensure_ascii=False))
    connector_summary.write_text(json.dumps({
        "decision": "external_signal_connector_stage1_passed",
        "connector_minimal_pass": True,
        "emitted_event_count": 5,
        "unique_symbol_count": 5,
        "stage0_handoff_mode": "observation_only",
        "stage0_observation_handoff_ready": True,
        "stage0_directional_replay_ready": False,
        "event_density_alpha_valid": False,
    }, ensure_ascii=False))

    result = main([
        "--collector-summary", str(collector_summary),
        "--connector-summary", str(connector_summary),
        "--output", str(review),
    ])
    assert result == 0
    text = review.read_text()
    assert "Stage 1.2" in text
    assert "公开只读" in text
    assert "不构成 alpha" in text
    assert "directional replay 不允许" in text
