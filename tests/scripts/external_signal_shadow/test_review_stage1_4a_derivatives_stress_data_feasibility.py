"""
tests/scripts/external_signal_shadow/test_review_stage1_4a_derivatives_stress_data_feasibility.py
"""

import json

from scripts.external_signal_shadow.review_stage1_4a_derivatives_stress_data_feasibility import main


def test_review_renders_source_audit_table(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"

    # Perfect summary JSON
    summary.write_text(json.dumps({
        "outcome": "stage1_4_data_feasible",
        "primary_blocker": None,
        "research_result_valid": True,
        "fixture_run": False,
        "symbol_audits": {
            "BTCUSDT": {
                "funding": {
                    "funding_history_days": 180.0,
                    "funding_settlement_coverage_ratio": 1.0,
                    "funding_field_coverage_ratio": 1.0,
                    "usable": True
                },
                "oi": {
                    "oi_history_days": 180.0,
                    "oi_time_coverage_ratio": 1.0,
                    "oi_field_coverage_ratio": 1.0,
                    "usable": True
                },
                "liquidation": {
                    "liquidation_history_days": 180.0,
                    "liquidation_time_coverage_ratio": 1.0,
                    "liquidation_field_coverage_ratio": 1.0,
                    "cm_to_um_proxy_used": False,
                    "liquidation_proxy_accepted_for_full_replay": True,
                    "notional_conversion_quality": "verified_by_sample"
                },
                "price": {
                    "price_history_days": 180.0,
                    "time_coverage_ratio": 1.0,
                    "price_bar_coverage_ratio": 1.0
                }
            }
        },
        "preview_metrics": {
            "composite_overlap_window_count": 100,
            "composite_overlap_event_days": 30
        }
    }), encoding="utf-8")

    rc = main(["--summary", str(summary), "--output-review", str(review)])
    assert rc == 0
    assert review.exists()

    text = review.read_text(encoding="utf-8")
    assert "| Source | History (Days) | Time Coverage |" in text
    assert "stage1_4_data_feasible" in text
    assert "verified_by_sample" in text


def test_review_marks_fixture_as_not_research_valid(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"

    summary.write_text(json.dumps({
        "outcome": "stage1_4_data_degraded",
        "primary_blocker": "fixture_smoke_only",
        "research_result_valid": False,
        "fixture_run": True,
        "symbol_audits": {},
        "preview_metrics": {}
    }), encoding="utf-8")

    rc = main(["--summary", str(summary), "--output-review", str(review)])
    assert rc == 0
    assert review.exists()

    text = review.read_text(encoding="utf-8")
    assert "INVALID" in text
    assert "YES (Smoke Test Only)" in text
    assert "本 artifact 是 fixture smoke，不证明真实" in text
    assert "no_audit_data" in text
    assert "| Binance Funding Rate (/fapi/v1/fundingRate) | 0.00d | 0.0% | 0.0% | 0 | public_settled_funding_history | No | no_audit_data | No |" in text


def test_review_mentions_cm_proxy_not_complete_tape(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"

    summary.write_text(json.dumps({
        "outcome": "stage1_4_data_degraded",
        "primary_blocker": "cm_proxy_unaccepted",
        "research_result_valid": True,
        "fixture_run": False,
        "symbol_audits": {
            "BTCUSDT": {
                "liquidation": {
                    "cm_to_um_proxy_used": True,
                    "liquidation_source_quality": "cm_liquidation_snapshot_proxy",
                    "liquidation_proxy_accepted_for_full_replay": False,
                    "notional_conversion_quality": "estimated"
                }
            }
        }
    }), encoding="utf-8")

    rc = main(["--summary", str(summary), "--output-review", str(review)])
    assert rc == 0
    assert review.exists()

    text = review.read_text(encoding="utf-8")
    assert "CM proxy" in text or "cm_liquidation_snapshot_proxy" in text
    assert "does not constitute a complete USD-M tape" in text


def test_review_mentions_oi_blocks_full_composite(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"

    summary.write_text(json.dumps({
        "outcome": "stage1_4_data_degraded",
        "primary_blocker": "oi_history_insufficient",
        "research_result_valid": True,
        "fixture_run": False,
        "symbol_audits": {
            "BTCUSDT": {
                "oi": {
                    "oi_history_days": 45.0,
                    "oi_time_coverage_ratio": 0.85,
                    "oi_field_coverage_ratio": 0.95,
                    "usable": False
                }
            }
        }
    }), encoding="utf-8")

    rc = main(["--summary", str(summary), "--output-review", str(review)])
    assert rc == 0
    assert review.exists()

    text = review.read_text(encoding="utf-8")
    assert "blocks full composite replay" in text


def test_review_renders_symbol_blocker_table(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"

    summary.write_text(json.dumps({
        "outcome": "stage1_4_data_degraded",
        "primary_blocker": "liquidation_history_insufficient",
        "research_result_valid": True,
        "fixture_run": False,
        "symbol_audits": {
            "SOLUSDT": {
                "funding": {
                    "funding_history_days": 180.0,
                    "usable": True
                },
                "oi": {
                    "oi_history_days": 180.0,
                    "oi_blocks_full_composite": False,
                    "usable": True
                },
                "liquidation": {
                    "liquidation_history_days": 12.5,
                    "cm_to_um_proxy_used": False,
                    "liquidation_proxy_accepted_for_full_replay": True,
                    "notional_conversion_quality": "verified_by_sample"
                },
                "price": {
                    "price_history_days": 180.0
                }
            }
        },
        "preview_metrics": {
            "composite_overlap_window_count": 71643,
            "composite_overlap_event_days": 14
        }
    }), encoding="utf-8")

    rc = main(["--summary", str(summary), "--output-review", str(review)])
    assert rc == 0
    assert review.exists()

    text = review.read_text(encoding="utf-8")
    assert "## 4. Per-Symbol Blocker Table" in text
    assert "| Symbol | Funding Days | OI Days | Price Days | Liquidation Days | Blockers | Usable |" in text
    assert "| SOLUSDT | 180.00d | 180.00d | 180.00d | 12.50d | liquidation_insufficient | No |" in text


def test_review_source_table_blocks_short_liquidation_history(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"

    summary.write_text(json.dumps({
        "outcome": "stage1_4_data_degraded",
        "primary_blocker": "liquidation_history_insufficient",
        "research_result_valid": True,
        "fixture_run": False,
        "symbol_audits": {
            "SOLUSDT": {
                "funding": {
                    "funding_history_days": 180.0,
                    "funding_settlement_coverage_ratio": 1.0,
                    "funding_field_coverage_ratio": 1.0,
                    "usable": True,
                },
                "oi": {
                    "oi_history_days": 180.0,
                    "oi_time_coverage_ratio": 1.0,
                    "oi_field_coverage_ratio": 1.0,
                    "oi_blocks_full_composite": False,
                    "usable": True,
                },
                "liquidation": {
                    "liquidation_history_days": 12.5,
                    "liquidation_time_coverage_ratio": 1.0,
                    "liquidation_field_coverage_ratio": 1.0,
                    "cm_to_um_proxy_used": False,
                    "liquidation_proxy_accepted_for_full_replay": True,
                    "notional_conversion_quality": "verified_by_sample",
                },
                "price": {
                    "price_history_days": 180.0,
                    "time_coverage_ratio": 1.0,
                    "price_bar_coverage_ratio": 1.0,
                },
            }
        },
    }), encoding="utf-8")

    rc = main(["--summary", str(summary), "--output-review", str(review)])

    assert rc == 0
    text = review.read_text(encoding="utf-8")
    assert "| Binance Liquidations (Vision Snapshots / Force Orders) | 12.50d | 100.0% | 100.0% | 1 | force_order_archive | No | liquidation_history_insufficient | No |" in text


def test_review_bounds_liquidation_coverage_display_at_one_hundred_percent(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"

    summary.write_text(json.dumps({
        "outcome": "stage1_4_data_degraded",
        "primary_blocker": "liquidation_history_insufficient",
        "research_result_valid": True,
        "fixture_run": False,
        "symbol_audits": {
            "BTCUSDT": {
                "liquidation": {
                    "liquidation_history_days": 12.5,
                    "liquidation_time_coverage_ratio": 348.46,
                    "liquidation_field_coverage_ratio": 1.0,
                    "cm_to_um_proxy_used": False,
                    "liquidation_proxy_accepted_for_full_replay": True,
                    "notional_conversion_quality": "verified_by_sample",
                }
            }
        },
    }), encoding="utf-8")

    rc = main(["--summary", str(summary), "--output-review", str(review)])

    assert rc == 0
    text = review.read_text(encoding="utf-8")
    assert "34846.0%" not in text
    assert "| Binance Liquidations (Vision Snapshots / Force Orders) | 12.50d | 100.0% | 100.0% | 1 | force_order_archive | No | liquidation_history_insufficient | No |" in text
