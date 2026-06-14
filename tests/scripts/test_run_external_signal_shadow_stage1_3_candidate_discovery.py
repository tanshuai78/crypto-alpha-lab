from __future__ import annotations

import json
from pathlib import Path

from scripts.run_external_signal_shadow_stage1_3_candidate_discovery import main


def test_stage1_3_fixture_run_marked_not_research_valid(tmp_path: Path) -> None:
    bars = tmp_path / "bars.jsonl"
    output = tmp_path / "summary.json"
    interval = 15 * 60 * 1000
    rows = []
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"):
        for i in range(20):
            rows.append({
                "symbol": symbol,
                "bar_start_ms": i * interval,
                "bar_end_ms": (i + 1) * interval,
                "open_price": 100.0,
                "high_price": 101.0,
                "low_price": 99.0,
                "close_price": 100.0,
                "quote_volume": 1_000_000.0,
            })
    bars.write_text("\n".join(json.dumps(row) for row in rows))
    assert main(["--bars", str(bars), "--output", str(output), "--historical-venue", "binance_proxy", "--venue-proxy-used", "--fixture-run"]) == 0
    summary = json.loads(output.read_text())
    assert summary["fixture_run"] is True
    assert summary["research_result_valid"] is False
