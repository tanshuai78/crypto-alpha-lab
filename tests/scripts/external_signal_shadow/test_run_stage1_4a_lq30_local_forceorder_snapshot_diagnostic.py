import json

from scripts.external_signal_shadow.run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic import (
    main,
)


def test_lq30_runner_without_alignment_inputs_marks_alignment_unavailable(tmp_path):
    archive = tmp_path / "force_orders.jsonl"
    archive.write_text(
        json.dumps({
            "symbol": "BTCUSDT",
            "side": "SELL",
            "price": "65000",
            "origQty": "0.1",
            "time": 1710000000000,
        }) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "summary.json"
    rc = main([
        "--local-force-order-archive", str(archive),
        "--output-summary", str(output),
    ])
    assert rc == 0
    assert output.exists()
    summary = json.loads(output.read_text(encoding="utf-8"))

    assert summary["decision"] == "liquidation_diagnostic_unusable"
    assert summary["overlap_report"]["alignment_overlap_available"] is False
    assert summary["complete_liquidation_tape_claim_allowed"] is False
    assert summary["paper_trading_allowed"] is False


def test_lq30_runner_with_alignment_inputs_computes_overlap(tmp_path):
    archive = tmp_path / "force_orders.jsonl"
    archive.write_text(
        json.dumps({
            "symbol": "BTCUSDT",
            "side": "SELL",
            "price": "65000",
            "origQty": "0.1",
            "time": 1710000000000,
        }) + "\n",
        encoding="utf-8",
    )

    funding = tmp_path / "funding.jsonl"
    funding.write_text(
        json.dumps({
            "symbol": "BTCUSDT",
            "fundingTime": 1710000000000,
            "fundingRate": "0.0005",
        }) + "\n",
        encoding="utf-8",
    )

    oi = tmp_path / "oi.jsonl"
    oi.write_text(
        json.dumps({
            "symbol": "BTCUSDT",
            "timestamp": 1710000000000,
            "sumOpenInterest": "100",
        }) + "\n",
        encoding="utf-8",
    )

    price = tmp_path / "price.jsonl"
    price.write_text(
        json.dumps({
            "symbol": "BTCUSDT",
            "open_time": 1709999100000,  # 15m bucket: 1709999100000 to 1710000000000
            "open_price": 65000,
            "close_price": 65100,
        }) + "\n",
        encoding="utf-8",
    )

    output = tmp_path / "summary.json"
    rc = main([
        "--local-force-order-archive", str(archive),
        "--funding-archive", str(funding),
        "--oi-archive", str(oi),
        "--price-archive", str(price),
        "--output-summary", str(output),
    ])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["overlap_report"]["alignment_overlap_available"] is True
    # Since we have only one row, and timestamp matches 1710000000000 (which is bucket_start_ms or bucket_end_ms depending on the 15m bucket:
    # 1710000000000 // 900000 * 900000 = 1710000000000
    # So bucket_start_ms = 1710000000000, bucket_end_ms = 1710000900000
    # funding: fundingTime = 1710000000000 <= 1710000900000 - 300000 (1710000600000). Yes, 1710000000000 <= 1710000600000. So aligned!
    # oi: timestamp = 1710000000000 <= 1710000900000, staleness = 900000 <= 3600000. Yes, aligned!
    # price: open_time is 1709999100000, bucket_start_ms = 1710000000000. Difference is 900000 (15m). Yes, within 15m covering. Aligned!
    # Let's see if our implementation finds overlap.
