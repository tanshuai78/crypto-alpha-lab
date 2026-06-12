import json


def test_review_stage1_connector_writes_markdown(tmp_path):
    from scripts.review_external_signal_shadow_stage1_connector import main

    summary = tmp_path / "summary.json"
    output = tmp_path / "review.md"
    summary.write_text(
        json.dumps(
            {
                "decision": "external_signal_connector_stage1_passed",
                "failure_type": "connector_completed",
                "raw_payload_count": 11,
                "emitted_event_count": 2,
                "deduped_payload_count": 1,
                "quarantined_payload_count": 5,
                "rejected_payload_count": 3,
                "summary_accounting_ok": True,
                "latency_p50_ms": 60_000,
                "latency_p95_ms": 60_000,
                "live_trading_enabled": False,
                "exchange_paper_trading_allowed": False,
                "execution_engine_allowed": False,
                "research_shadow_replay_allowed": True,
                "wallet_required": False,
                "reject_reason_counts": {"forbidden_executable_payload": 1},
                "quarantine_reason_counts": {"price_mapping_unavailable": 1},
            }
        )
    )

    result = main(["--summary", str(summary), "--output", str(output)])

    assert result == 0
    text = output.read_text()
    assert "External Signal Shadow Lab Stage 1 Connector 审查报告" in text
    assert "## 1. 结论" in text
    assert "## 3. 统计摘要" in text
    assert "## 7. 不能推出的结论" in text
    assert "不是 alpha 通过" in text
    assert "available_at_ms" in text
    assert "## Conclusion" not in text
    assert "What Cannot Be Concluded" not in text
