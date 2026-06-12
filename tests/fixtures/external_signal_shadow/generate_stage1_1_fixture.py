import json
from pathlib import Path

path = Path(
    "/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/.worktrees/external-signal-shadow-stage1/tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl"
)

rows = []
base_time = 1781165400000

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]

# Create 15 normal valid rows
for i in range(15):
    rows.append(
        {
            "source": "gate_marketanalysis_manual_export",
            "source_vendor": "gate",
            "source_surface": "gate_big_data_dashboard",
            "source_capture_method": "manual_export",
            "source_skill": "gate_exchange_marketanalysis",
            "data_quality": "manual_export",
            "capture_id": f"gate_big_data_20260612_{i:03d}",
            "captured_by": "manual",
            "source_observed_at_ms": base_time + i * 300000,
            "fetched_at_ms": base_time + i * 300000 + 1000,
            "available_at_ms": base_time + i * 300000 + 1000,
            "manual_transform_version": "stage1_1_v0",
            "field_confidence": {
                "event_time_ms": "source_provided",
                "symbol": "source_provided",
                "score": "source_native",
            },
            "raw_payload": {
                "event_type": "cex_market_tape_anomaly",
                "chain": "cex",
                "symbol": symbols[i % len(symbols)],
                "event_time_ms": base_time + i * 300000,
                "metadata": {"event_time_policy": "source_provided"},
            },
        }
    )

# Add 1 available_at_fallback row
rows.append(
    {
        "source": "gate_marketanalysis_manual_export",
        "source_vendor": "gate",
        "source_surface": "gate_big_data_dashboard",
        "source_capture_method": "manual_export",
        "source_skill": "gate_exchange_marketanalysis",
        "data_quality": "manual_export",
        "capture_id": "gate_big_data_20260612_015",
        "captured_by": "manual",
        "source_observed_at_ms": base_time - 1000000,
        "fetched_at_ms": base_time - 1000000,
        "available_at_ms": base_time - 1000000,
        "manual_transform_version": "stage1_1_v0",
        "field_confidence": {
            "event_time_ms": "available_at_fallback",
            "symbol": "source_provided",
        },
        "raw_payload": {
            "event_type": "cex_market_tape_anomaly",
            "chain": "cex",
            "symbol": "BTCUSDT",
            "event_time_ms": base_time - 1000000,
            "metadata": {"event_time_policy": "available_at_fallback"},
        },
    }
)

# Add 1 unsupported symbol PEPEUSDT
rows.append(
    {
        "source": "gate_marketanalysis_manual_export",
        "source_vendor": "gate",
        "source_surface": "gate_big_data_dashboard",
        "source_capture_method": "manual_export",
        "source_skill": "gate_exchange_marketanalysis",
        "data_quality": "manual_export",
        "capture_id": "gate_big_data_20260612_016",
        "captured_by": "manual",
        "source_observed_at_ms": base_time,
        "fetched_at_ms": base_time,
        "available_at_ms": base_time,
        "manual_transform_version": "stage1_1_v0",
        "field_confidence": {
            "event_time_ms": "source_provided",
            "symbol": "source_provided",
        },
        "raw_payload": {
            "event_type": "cex_market_tape_anomaly",
            "chain": "cex",
            "symbol": "PEPEUSDT",
            "event_time_ms": base_time,
        },
    }
)

# Add 1 missing symbol
rows.append(
    {
        "source": "gate_marketanalysis_manual_export",
        "source_vendor": "gate",
        "source_surface": "gate_big_data_dashboard",
        "source_capture_method": "manual_export",
        "source_skill": "gate_exchange_marketanalysis",
        "data_quality": "manual_export",
        "capture_id": "gate_big_data_20260612_017",
        "captured_by": "manual",
        "source_observed_at_ms": base_time,
        "fetched_at_ms": base_time,
        "available_at_ms": base_time,
        "manual_transform_version": "stage1_1_v0",
        "field_confidence": {
            "event_time_ms": "source_provided",
        },
        "raw_payload": {
            "event_type": "cex_market_tape_anomaly",
            "chain": "cex",
            "event_time_ms": base_time,
        },
    }
)

# Add 1 duplicate of row 0
rows.append(rows[0])

# Add 1 unsupported event type
rows.append(
    {
        "source": "gate_marketanalysis_manual_export",
        "source_vendor": "gate",
        "source_surface": "gate_big_data_dashboard",
        "source_capture_method": "manual_export",
        "source_skill": "gate_exchange_marketanalysis",
        "data_quality": "manual_export",
        "capture_id": "gate_big_data_20260612_018",
        "captured_by": "manual",
        "source_observed_at_ms": base_time,
        "fetched_at_ms": base_time,
        "available_at_ms": base_time,
        "manual_transform_version": "stage1_1_v0",
        "field_confidence": {
            "event_time_ms": "source_provided",
            "symbol": "source_provided",
        },
        "raw_payload": {
            "event_type": "unsupported_event_type",
            "chain": "cex",
            "symbol": "BTCUSDT",
            "event_time_ms": base_time,
        },
    }
)

# Add 1 score_interpretation_allowed = false
rows.append(
    {
        "source": "gate_marketanalysis_manual_export",
        "source_vendor": "gate",
        "source_surface": "gate_big_data_dashboard",
        "source_capture_method": "manual_export",
        "source_skill": "gate_exchange_marketanalysis",
        "data_quality": "manual_export",
        "capture_id": "gate_big_data_20260612_019",
        "captured_by": "manual",
        "source_observed_at_ms": base_time,
        "fetched_at_ms": base_time,
        "available_at_ms": base_time,
        "manual_transform_version": "stage1_1_v0",
        "field_confidence": {
            "event_time_ms": "source_provided",
            "symbol": "source_provided",
        },
        "raw_payload": {
            "event_type": "cex_market_tape_anomaly",
            "chain": "cex",
            "symbol": "BTCUSDT",
            "event_time_ms": base_time,
            "score": 0.99,
            "metadata": {"score_interpretation_allowed": False},
        },
    }
)

with open(path, "w") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")
