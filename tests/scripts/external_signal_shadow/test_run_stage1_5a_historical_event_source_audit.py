import json
import os
import tempfile
from unittest.mock import patch

import pytest

from scripts.external_signal_shadow.run_stage1_5a_historical_event_source_audit import (
    main,
)


def test_runner_writes_summary_from_fixture_jsonl():
    # GIVEN a local JSONL fixture file
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        f.write(
            b'{"title": "Binance Will Delist MOB", "time": 1710921600000, "symbol": "MOB"}\n'
        )
        f_name = f.name

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as out_f:
        out_name = out_f.name

    try:
        # WHEN running with --fixture-run
        args = [
            "run_stage1_5a_historical_event_source_audit.py",
            "--source-profile",
            "binance_official_announcements_like_rows",
            "--source-file",
            f_name,
            "--output-summary",
            out_name,
            "--fixture-run",
        ]

        with patch("sys.argv", args):
            main()

        # THEN the output summary should exist and contain expected top level values
        assert os.path.exists(out_name)
        with open(out_name, "r") as r:
            summary = json.load(r)

        assert summary["stage"] == "external_signal_shadow_lab_stage1_5a"
        assert summary["research_result_valid"] is False
        assert summary["metrics"]["historical_events_found"] == 1
        assert summary["metrics"]["raw_cache_written"] is False
        assert summary["metrics"]["network_result_not_deterministic"] is False

    finally:
        os.unlink(f_name)
        os.unlink(out_name)


def test_runner_real_source_file_mode_marks_research_result_valid():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        f.write(
            b'{"title": "Binance Will Delist MOB", "time": 1710921600000, "symbol": "MOB"}\n'
        )
        f_name = f.name

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as out_f:
        out_name = out_f.name

    try:
        args = [
            "run_stage1_5a_historical_event_source_audit.py",
            "--source-profile",
            "binance_official_announcements_like_rows",
            "--source-file",
            f_name,
            "--source-file-mode",
            "real",
            "--output-summary",
            out_name,
        ]

        with patch("sys.argv", args):
            main()

        with open(out_name, "r") as r:
            summary = json.load(r)

        assert summary["research_result_valid"] is True
        assert summary["metrics"]["historical_events_found"] == 1
        assert summary["metrics"]["raw_cache_written"] is False
    finally:
        os.unlink(f_name)
        os.unlink(out_name)


def test_runner_propagates_network_raw_cache_metadata():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as out_f:
        out_name = out_f.name

    try:
        args = [
            "run_stage1_5a_historical_event_source_audit.py",
            "--source-profile",
            "generic_json_announcement_rows",
            "--source-url",
            "https://binance.com/announcement",
            "--output-summary",
            out_name,
        ]

        with patch(
            "scripts.external_signal_shadow.run_stage1_5a_historical_event_source_audit.load_or_fetch_payloads"
        ) as mock_load:
            mock_load.return_value = (
                [],
                False,
                {
                    "raw_cache_written": True,
                    "raw_cache_path": "data/external_signal_shadow/stage1_5a/raw/20260622/binance",
                    "network_result_not_deterministic": True,
                    "collector_received_at_ms": 1710921605000,
                },
            )
            with patch("sys.argv", args):
                main()

        with open(out_name, "r") as r:
            summary = json.load(r)

        assert summary["metrics"]["raw_cache_written"] is True
        assert summary["metrics"]["raw_cache_path"].endswith("/binance")
        assert summary["metrics"]["network_result_not_deterministic"] is True
        assert summary["metrics"]["collector_received_at_ms"] == 1710921605000
    finally:
        os.unlink(out_name)


def test_runner_rejects_disallowed_domain_before_fetch():
    # GIVEN a disallowed domain URL
    args = [
        "run_stage1_5a_historical_event_source_audit.py",
        "--source-profile",
        "generic_json_announcement_rows",
        "--source-url",
        "https://evil-domain.com/data",
        "--output-summary",
        "dummy.json",
    ]

    with patch("sys.argv", args):
        with pytest.raises(ValueError, match="is not in allowlist"):
            main()


def test_runner_supports_source_profile_argument():
    # GIVEN missing args (should raise SystemExit due to argparse)
    args = [
        "run_stage1_5a_historical_event_source_audit.py",
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit):
            main()
