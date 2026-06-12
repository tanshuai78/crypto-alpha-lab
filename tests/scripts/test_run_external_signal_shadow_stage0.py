import json


def test_run_external_signal_shadow_stage0_writes_summary(tmp_path):
    from scripts.run_external_signal_shadow_stage0 import main

    output = tmp_path / "summary.json"
    result = main(
        [
            "--events",
            "tests/fixtures/external_signal_shadow/stage0_events.jsonl",
            "--price-bars",
            "tests/fixtures/external_signal_shadow/stage0_price_bars.jsonl",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert output.exists()
    summary = json.loads(output.read_text())
    assert summary["mode"] == "fixture_only_stage0"


def test_run_external_signal_shadow_stage0_empty_events_writes_data_failure(tmp_path):
    from scripts.run_external_signal_shadow_stage0 import main

    events = tmp_path / "events.jsonl"
    bars = tmp_path / "bars.jsonl"
    output = tmp_path / "summary.json"
    events.write_text("")
    bars.write_text(
        json.dumps(
            {
                "symbol": "BTCUSDT",
                "bar_start_ms": 0,
                "bar_end_ms": 60_000,
                "open_price": 100.0,
                "high_price": 101.0,
                "low_price": 99.0,
                "close_price": 100.0,
            }
        )
        + "\n"
    )

    result = main(["--events", str(events), "--price-bars", str(bars), "--output", str(output)])

    assert result == 0
    summary = json.loads(output.read_text())
    assert summary["decision"] == "external_signal_shadow_stage0_failed"
    assert summary["failure_type"] == "data_failure"


def test_run_external_signal_shadow_stage0_rejects_external_api_flag(tmp_path):
    from scripts.run_external_signal_shadow_stage0 import main

    output = tmp_path / "summary.json"
    result = main(
        [
            "--events",
            "tests/fixtures/external_signal_shadow/stage0_events.jsonl",
            "--price-bars",
            "tests/fixtures/external_signal_shadow/stage0_price_bars.jsonl",
            "--output",
            str(output),
            "--external-api",
        ]
    )

    assert result == 1


def test_run_external_signal_shadow_stage0_output_has_live_trading_false(tmp_path):
    from scripts.run_external_signal_shadow_stage0 import main

    output = tmp_path / "summary.json"
    main(
        [
            "--events",
            "tests/fixtures/external_signal_shadow/stage0_events.jsonl",
            "--price-bars",
            "tests/fixtures/external_signal_shadow/stage0_price_bars.jsonl",
            "--output",
            str(output),
        ]
    )

    summary = json.loads(output.read_text())
    assert summary["live_trading_enabled"] is False
    assert summary["external_api_enabled"] is False
    assert summary["wallet_required"] is False
