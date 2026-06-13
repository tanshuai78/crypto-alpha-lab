from __future__ import annotations

import json
from pathlib import Path

from research.external_signal_shadow.gate_public_collector import (
    collect_gate_public_snapshots_from_fetcher,
    write_failure_summary,
)


def _payload(pair: str) -> list[dict[str, str]]:
    return [{
        "currency_pair": pair,
        "last": "100.0",
        "base_volume": "10.0",
        "quote_volume": "1000.0",
        "change_percentage": "1.0",
    }]


def test_collect_gate_public_snapshots_writes_five_raw_payloads(tmp_path: Path) -> None:
    calls: list[str] = []

    def fetcher(url: str, timeout_sec: float, user_agent: str) -> tuple[int, object, int]:
        calls.append(url)
        pair = url.split("currency_pair=")[1]
        return 200, _payload(pair), 12

    output = tmp_path / "raw.jsonl"
    summary = collect_gate_public_snapshots_from_fetcher(
        gate_pairs=("BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "DOGE_USDT"),
        output_path=str(output),
        fetcher=fetcher,
        now_ms=lambda: 1781165880000,
    )

    assert len(calls) == 5
    assert output.exists()
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 5
    assert summary["collector_minimal_pass"] is True
    assert summary["http_success_count"] == 5
    assert summary["raw_payload_count"] == 5
    assert summary["api_key_used"] is False
    assert summary["private_endpoint_used"] is False
    assert summary["event_density_alpha_valid"] is False


def test_collector_writes_failure_summary_on_network_error(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    write_failure_summary(
        output_summary_path=str(summary_path),
        failure_type="collector_network_failure",
        http_success_count=0,
        http_failure_count=5,
    )
    summary = json.loads(summary_path.read_text())
    assert summary["decision"] == "external_signal_collector_stage1_2_failed"
    assert summary["failure_type"] == "collector_network_failure"
    assert summary["api_key_used"] is False
    assert summary["private_endpoint_used"] is False
    assert summary["live_safe"] is False


def test_collector_summary_classifies_rate_limit_failure(tmp_path: Path) -> None:
    def fetcher(url: str, timeout_sec: float, user_agent: str) -> tuple[int, object, int]:
        return 429, {"label": "TOO_MANY_REQUESTS"}, 5

    output = tmp_path / "raw.jsonl"
    summary = collect_gate_public_snapshots_from_fetcher(
        gate_pairs=("BTC_USDT", "ETH_USDT"),
        output_path=str(output),
        fetcher=fetcher,
        now_ms=lambda: 1781165880000,
        inter_request_delay_sec=0,
    )

    assert summary["decision"] == "external_signal_collector_stage1_2_failed"
    assert summary["failure_type"] == "rate_limited"
    assert summary["primary_blocker"] == "rate_limited"
    assert summary["rate_limited_count"] == 2
    assert output.exists() is False


def test_collector_summary_classifies_parse_failure(tmp_path: Path) -> None:
    def fetcher(url: str, timeout_sec: float, user_agent: str) -> tuple[int, object, int]:
        pair = url.split("currency_pair=")[1]
        return 200, [{"currency_pair": pair, "last": "bad"}], 5

    output = tmp_path / "raw.jsonl"
    summary = collect_gate_public_snapshots_from_fetcher(
        gate_pairs=("BTC_USDT",),
        output_path=str(output),
        fetcher=fetcher,
        now_ms=lambda: 1781165880000,
        inter_request_delay_sec=0,
    )

    assert summary["decision"] == "external_signal_collector_stage1_2_failed"
    assert summary["failure_type"] == "field_parse_failure"
    assert summary["primary_blocker"] == "field_parse_failure"
    assert summary["field_parse_failure_count"] == 4
