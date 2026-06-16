"""
tests/research/external_signal_shadow/test_stage1_4a2_vendor_config.py
"""

from configs import base


def test_stage1_4a2_vendor_config_constants_exist() -> None:
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_VENDOR_ORDER == (
        "tardis_dev",
        "coinglass",
        "laevitas",
        "coinalyze",
        "coin_metrics_pro",
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MIN_HISTORY_DAYS == 90.0
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MIN_SYMBOLS_WITH_USABLE_DATA == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MAX_TIMESTAMP_RESOLUTION_MS == 60_000
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MIN_VENDOR_DATA_LAG_MS == 60_000
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_LOW_COST_MAX_USD_PER_MONTH == 50.0
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MEDIUM_COST_MAX_USD_PER_MONTH == 200.0


def test_stage1_4a2_runtime_paths_are_gitignored() -> None:
    # Use subprocess rather than importing git internals.
    import subprocess

    sample_path = "data/external_signal_shadow/vendor_liquidation_samples/tardis_dev/sample.jsonl"
    result = subprocess.run(
        ["git", "check-ignore", sample_path],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    template_path = "docs/context/stage1_4a2_vendor_audit_template.json"
    assert template_path
