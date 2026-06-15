import json
import zipfile

from scripts.external_signal_shadow.build_stage1_4a_binance_vision_oi_metrics_archive import (
    build_metrics_zip_url,
    convert_metrics_csv_line,
    convert_metrics_zip_to_jsonl,
    infer_interval_ms,
    parse_metrics_create_time_ms,
)


def test_build_metrics_url_uses_daily_metrics_path():
    url = build_metrics_zip_url(
        base_url="https://data.binance.vision",
        symbol="BTCUSDT",
        date_str="2024-01-01",
    )
    assert "/data/futures/um/daily/metrics/BTCUSDT/" in url
    assert "BTCUSDT-metrics-2024-01-01.zip" in url
    assert "openInterest" not in url


def test_convert_metrics_csv_rows_to_stage1_4_oi_rows():
    header = "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio".split(",")
    line = "2024-01-01 00:00:00,BTCUSDT,74006.26600000,3131493738.89740000,1.36,1.25,1.50,1.31".split(",")

    row = convert_metrics_csv_line(header, line, source_file="BTCUSDT-metrics-2024-01-01.zip")

    assert row["symbol"] == "BTCUSDT"
    assert row["sumOpenInterest"] == "74006.26600000"
    assert row["sumOpenInterestValue"] == "3131493738.89740000"
    assert row["timestamp"] == 1704067200000
    assert row["source"] == "binance_vision_um_daily_metrics"
    assert row["source_file"] == "BTCUSDT-metrics-2024-01-01.zip"


def test_metrics_create_time_parsed_as_utc_ms():
    assert parse_metrics_create_time_ms("2024-01-01 00:00:00") == 1704067200000


def test_metrics_interval_inferred_from_rows():
    rows = [
        {"timestamp": 1704067200000},
        {"timestamp": 1704067500000},
        {"timestamp": 1704067800000},
    ]
    assert infer_interval_ms(rows) == 300_000


def test_metrics_interval_inferred_from_rows_with_duplicates_and_gaps():
    rows = [
        {"timestamp": 1704067200000},
        {"timestamp": 1704067200000},  # duplicate
        {"timestamp": 1704067500000},  # +300s
        {"timestamp": 1704068100000},  # gap (+600s)
        {"timestamp": 1704068400000},  # +300s
    ]
    # Median of positive deltas (300k, 600k, 300k) is 300k
    assert infer_interval_ms(rows) == 300_000


def test_convert_metrics_zip_to_jsonl(tmp_path):
    # Prepare mock zip content
    zip_path = tmp_path / "BTCUSDT-metrics-2024-01-01.zip"
    csv_filename = "BTCUSDT-metrics-2024-01-01.csv"
    csv_content = (
        "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio\n"
        "2024-01-01 00:00:00,BTCUSDT,74006.26600000,3131493738.89740000,1.36,1.25,1.50,1.31\n"
        "2024-01-01 00:05:00,BTCUSDT,74100.00000000,3132000000.00000000,1.36,1.25,1.50,1.31\n"
    )

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(csv_filename, csv_content)

    rows, malformed, duplicates = convert_metrics_zip_to_jsonl(str(zip_path), "BTCUSDT")

    assert len(rows) == 2
    assert malformed == 0
    assert duplicates == 0
    assert rows[0]["timestamp"] == 1704067200000
    assert rows[1]["timestamp"] == 1704067500000
    assert rows[0]["sumOpenInterest"] == "74006.26600000"
    assert rows[1]["sumOpenInterest"] == "74100.00000000"


def test_build_stage1_4a_downloader_cli(tmp_path):
    from scripts.external_signal_shadow.build_stage1_4a_binance_vision_oi_metrics_archive import (
        main as downloader_main,
    )

    # Create mock zip file in a mock zip directory
    mock_zip_dir = tmp_path / "mock_zips"
    mock_zip_dir.mkdir()

    zip_path = mock_zip_dir / "BTCUSDT-metrics-2024-01-01.zip"
    csv_filename = "BTCUSDT-metrics-2024-01-01.csv"
    csv_content = (
        "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio\n"
        "2024-01-01 00:00:00,BTCUSDT,74006.26600000,3131493738.89740000,1.36,1.25,1.50,1.31\n"
    )
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(csv_filename, csv_content)

    output_file = tmp_path / "output.jsonl"
    summary_file = tmp_path / "summary.json"

    rc = downloader_main([
        "--symbols", "BTCUSDT",
        "--days", "1",
        "--end-date", "2024-01-01",
        "--output", str(output_file),
        "--output-summary", str(summary_file),
        "--mock-zip-dir", str(mock_zip_dir)
    ])

    assert rc == 0
    assert output_file.exists()
    assert summary_file.exists()

    # Verify output contents
    with open(output_file, "r") as f:
        rows = [json.loads(line) for line in f]
    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTCUSDT"

    # Verify summary contents
    with open(summary_file, "r") as f:
        summary = json.load(f)
    assert summary["row_count"] == 1
    assert summary["requested_days"] == 1
    assert summary["download_success_count"] == 1
    assert summary["download_failure_count"] == 0
    assert summary["history_days_by_symbol"]["BTCUSDT"] == 0.0

