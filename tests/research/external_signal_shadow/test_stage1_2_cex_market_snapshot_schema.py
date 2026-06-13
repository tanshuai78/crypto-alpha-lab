from __future__ import annotations

import json
from pathlib import Path

from research.external_signal_shadow.file_backed_connector import run_file_backed_connector


def _wrapper(now_ms: int = 1781165880123) -> dict:
    return {
        "source": "gate_public_market_snapshot_collector",
        "source_vendor": "gate",
        "source_surface": "gate_api_v4_public_market_data",
        "source_capture_method": "public_rest_snapshot",
        "source_skill": "gate_public_market_snapshot_collector",
        "data_quality": "api_snapshot",
        "capture_id": "gate_public_market_snapshot_20260612_001",
        "captured_by": "script",
        "source_observed_at_ms": now_ms,
        "fetched_at_ms": now_ms,
        "available_at_ms": now_ms,
        "field_confidence": {
            "event_time_ms": "available_at_fallback",
            "symbol": "normalized",
            "score": "missing",
        },
        "raw_payload": {
            "event_type": "cex_market_snapshot",
            "chain": "cex",
            "symbol": "BTCUSDT",
            "event_time_ms": now_ms,
            "direction_hint": "unknown",
            "score_interpretation_allowed": False,
            "triple_barrier_directional_order_allowed": False,
            "alpha_interpretation_allowed": False,
            "metadata": {
                "gate_currency_pair": "BTC_USDT",
                "event_time_policy": "available_at_fallback",
                "triple_barrier_directional_order_allowed": False,
                "alpha_interpretation_allowed": False,
            },
        },
    }


def test_stage1_connector_allows_cex_market_snapshot_as_observation_only(tmp_path: Path) -> None:
    input_path = tmp_path / "raw.jsonl"
    price_map = tmp_path / "price_map.json"
    output_path = tmp_path / "events.jsonl"
    input_path.write_text(json.dumps(_wrapper()) + "\n")
    price_map.write_text(json.dumps({
        "cex:BTCUSDT": {
            "price_series_id": "BTCUSDT",
            "venue": "binance",
            "timeframe": "5m",
            "mapping_type": "direct_cex_symbol",
            "active": True,
        }
    }))

    summary = run_file_backed_connector(
        input_files=[str(input_path)],
        price_map_path=str(price_map),
        output_path=str(output_path),
        source="gate_public_market_snapshot_collector",
    )

    assert summary["emitted_event_count"] == 1
    event = json.loads(output_path.read_text().splitlines()[0])
    assert event["event_type"] == "cex_market_snapshot"
    assert event["direction_hint"] == "unknown"
    assert event["shadow_only"] is True
    assert event.get("notional_usd", 0.0) == 0.0
    assert event["metadata"]["event_time_policy"] == "available_at_fallback"
    assert event["metadata"]["triple_barrier_directional_order_allowed"] is False
    assert event["metadata"]["alpha_interpretation_allowed"] is False


def test_connector_rejects_top_level_forbidden_keys_before_schema_filtering(tmp_path: Path) -> None:
    input_path = tmp_path / "raw.jsonl"
    price_map = tmp_path / "price_map.json"
    output_path = tmp_path / "events.jsonl"
    payload = _wrapper()
    payload["api_key"] = "SHOULD_NOT_BE_ACCEPTED"

    input_path.write_text(json.dumps(payload) + "\n")
    price_map.write_text(json.dumps({
        "cex:BTCUSDT": {
            "price_series_id": "BTCUSDT",
            "venue": "binance",
            "timeframe": "5m",
            "mapping_type": "direct_cex_symbol",
            "active": True,
        }
    }))

    summary = run_file_backed_connector(
        input_files=[str(input_path)],
        price_map_path=str(price_map),
        output_path=str(output_path),
        source="gate_public_market_snapshot_collector",
    )

    assert summary["emitted_event_count"] == 0
    assert summary["rejected_payload_count"] == 1
    assert "forbidden_executable_payload" in summary["reject_reason_counts"]
