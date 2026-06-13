from __future__ import annotations

from research.external_signal_shadow.connector_summary import decide_stage1_connector_summary


def test_stage1_2_summary_sets_directional_replay_ready_false() -> None:
    summary = {
        "raw_payload_count": 5,
        "emitted_event_count": 5,
        "deduped_payload_count": 0,
        "quarantined_payload_count": 0,
        "rejected_payload_count": 0,
        "summary_accounting_ok": True,
        "output_file": "events.jsonl",
        "output_file_sha256": "abc",
        "live_trading_enabled": False,
        "exchange_paper_trading_allowed": False,
        "execution_engine_allowed": False,
        "research_shadow_replay_allowed": True,
        "wallet_required": False,
        "event_type_counts": {"cex_market_snapshot": 5},
        "direction_hint_counts": {"unknown": 5},
        "price_mapping_counts": {"mapped": 5},
        "source": "gate_public_market_snapshot_collector",
    }
    decision = decide_stage1_connector_summary(summary)
    assert decision["decision"] == "external_signal_connector_stage1_passed"
    assert decision["stage0_handoff_mode"] == "observation_only"
    assert decision["stage0_directional_replay_ready"] is False
    assert decision["stage0_observation_handoff_ready"] is True
    assert decision["event_density_alpha_valid"] is False
