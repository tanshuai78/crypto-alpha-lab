"""Tests for PREDICT pre-market OI scenario C holdout validation.

Covers Task 1-4 per docs/plans/2026-11-07-predict-pre-market-oi-c-single-event-holdout-implementation-plan_CN.md.
Remediation test suite covering P1-01 through P1-07 and P2-01, P2-02.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import scripts.external_signal_shadow.run_predict_pre_market_oi_c_holdout as holdout_mod
from scripts.external_signal_shadow.run_launch_price_oi_basis_incremental_information import (
    write_parent_panel_csv,
)
from scripts.external_signal_shadow.run_predict_pre_market_oi_c_holdout import (
    HOLDOUT_CASE_HEADER,
    OFFICIAL_ANNOUNCEMENT_URL,
    SCHEDULED_LAUNCH_MS,
    SCHEDULED_LAUNCH_TIME_STR,
    TARGET_SYMBOL,
    build_case_features,
    fit_models,
    load_training_panel,
    main,
    parse_aggtrades_zip,
    parse_metrics_zip,
    score_case,
)
from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
    AggTradeRecord,
    OiMetricRecord,
)

VALID_SCHEDULE_EVIDENCE: dict[str, Any] = {
    "source_url": OFFICIAL_ANNOUNCEMENT_URL,
    "version_verification_status": "verified",
    "version_notes": "Official announcement text matching 2026-10-25 08:15:00 UTC",
    "applicability_conclusion": "applicable",
    "scheduled_launch_utc": SCHEDULED_LAUNCH_TIME_STR,
    "early_trades_explanation": "Pre-launch auction / test fills recorded in official stream",
    "early_trades_source": "official_binance_stream",
}


def _make_dummy_canonical_18_rows(
    p_values: list[float] | None = None,
    o_values: list[float] | None = None,
    y_values: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Create 18 canonical parent rows for pre_market scenario C."""
    if p_values is None:
        p_grid = [-0.2, 0.0, 0.2]
        o_grid = [-0.1, 0.0, 0.1]
        pairs = [(p, o) for p in p_grid for o in o_grid] * 2  # 9 * 2 = 18
        p_values = [pair[0] for pair in pairs]
        o_values = [pair[1] for pair in pairs]
        y_values = [
            float(f"{0.01 + 0.2 * p + 0.3 * o + 0.4 * p * o:.8f}")
            for p, o in zip(p_values, o_values)
        ]

    rows: list[dict[str, Any]] = []
    # Dates deliberately not monotonic with index to test true min/max date logic
    dates = [
        "2026-03-15", "2026-03-01", "2026-03-20", "2026-03-10", "2026-03-25", "2026-03-05",
        "2026-04-01", "2026-03-18", "2026-04-10", "2026-03-12", "2026-04-16", "2026-03-08",
        "2026-03-22", "2026-03-02", "2026-03-28", "2026-03-14", "2026-04-05", "2026-03-30",
    ]
    for i in range(18):
        pid = f"old_parent_{i:02d}_{'a'*20}"
        sym = f"SYM{i:02d}USDT"
        rows.append(
            {
                "parent_article_id": pid,
                "listing_regime": "pre_market",
                "scenario": "C",
                "utc_date": dates[i],
                "child_symbols": sym,
                "required_child_count": 1,
                "scenario_complete_child_count": 1,
                "oi_complete": True,
                "basis_complete": False,
                "missing_reasons": "",
                "p": float(f"{p_values[i]:.8f}"),
                "o": float(f"{o_values[i]:.8f}"),
                "b": None,
                "y": float(f"{y_values[i]:.8f}"),
                "long_mae": -0.01,
                "long_mfe": 0.02,
            }
        )
    return rows


def test_training_canonical_panel_and_mutations(tmp_path: Path) -> None:
    """Test loading canonical panel and verifying schema, date, bounds, and mutations."""
    panel_file = tmp_path / "parent_panel.csv"
    canonical_rows = _make_dummy_canonical_18_rows()
    write_parent_panel_csv(canonical_rows, panel_file)

    with open(panel_file, "rb") as f:
        expected_sha = hashlib.sha256(f.read()).hexdigest()

    # Success path
    loaded = load_training_panel(panel_file, expected_sha)
    assert len(loaded) == 18
    assert all(r["listing_regime"] == "pre_market" and r["scenario"] == "C" for r in loaded)

    # Mutation 1: Hash mismatch
    with pytest.raises(ValueError, match="hash_mismatch"):
        load_training_panel(panel_file, "0" * 64)

    # Mutation 2: Date beyond 2026-04-16
    mut_rows = _make_dummy_canonical_18_rows()
    mut_rows[0]["utc_date"] = "2026-04-17"
    bad_file = tmp_path / "panel_bad_date.csv"
    write_parent_panel_csv(mut_rows, bad_file)
    with open(bad_file, "rb") as f:
        bad_sha = hashlib.sha256(f.read()).hexdigest()
    with pytest.raises(ValueError, match="date_out_of_bounds"):
        load_training_panel(bad_file, bad_sha)

    # Mutation 2b (P2-01): Invalid calendar date like 2026-02-30
    mut_rows_invalid_cal = _make_dummy_canonical_18_rows()
    mut_rows_invalid_cal[0]["utc_date"] = "2026-02-30"
    bad_cal_file = tmp_path / "panel_bad_cal.csv"
    write_parent_panel_csv(mut_rows_invalid_cal, bad_cal_file)
    with open(bad_cal_file, "rb") as f:
        bad_cal_sha = hashlib.sha256(f.read()).hexdigest()
    with pytest.raises(ValueError, match="invalid_utc_date_format"):
        load_training_panel(bad_cal_file, bad_cal_sha)

    # Mutation 3: PREDICT in training panel
    mut_rows = _make_dummy_canonical_18_rows()
    mut_rows[0]["parent_article_id"] = "5ef55cf8358e4a48b2512a156e89c8e5"
    bad_file = tmp_path / "panel_predict.csv"
    write_parent_panel_csv(mut_rows, bad_file)
    with open(bad_file, "rb") as f:
        bad_sha = hashlib.sha256(f.read()).hexdigest()
    with pytest.raises(ValueError, match="predict_in_training"):
        load_training_panel(bad_file, bad_sha)

    # Mutation 4: Row count != 18
    mut_rows = _make_dummy_canonical_18_rows()[:17]
    bad_file = tmp_path / "panel_17.csv"
    write_parent_panel_csv(mut_rows, bad_file)
    with open(bad_file, "rb") as f:
        bad_sha = hashlib.sha256(f.read()).hexdigest()
    with pytest.raises(ValueError, match="row_count_mismatch"):
        load_training_panel(bad_file, bad_sha)


def test_model_hand_calculated_oracles() -> None:
    """Test OLS model fitting against independent hand-calculated oracle vectors."""
    # Oracle 1: 8 synthetic points
    p = np.array([-3, -2, -1, 0, 1, 2, 3, 4], dtype=np.float64)
    o = np.array([2, -1, 3, 0, -2, 1, 4, -3], dtype=np.float64)
    y = np.array([-23, 2, -4, 1, -11, 16, 67, -48], dtype=np.float64)

    fit_res = fit_models(p, o, y)
    assert fit_res["freeze_status"] == "frozen"
    assert fit_res["mu_p"] == pytest.approx(0.5)
    assert fit_res["mu_o"] == pytest.approx(0.5)
    assert fit_res["sigma_p"] == pytest.approx(math.sqrt(5.25))
    assert fit_res["sigma_o"] == pytest.approx(math.sqrt(5.25))

    # M0 standardized coefficients: [0, 33*sqrt(21)/28]
    expected_m0_beta1 = 33.0 * math.sqrt(21.0) / 28.0
    assert fit_res["coef_m0"][0] == pytest.approx(0.0)
    assert fit_res["coef_m0"][1] == pytest.approx(expected_m0_beta1)

    # M1 standardized coefficients: [4.5, 2*sqrt(21), 2.5*sqrt(21), 21]
    assert fit_res["coef_m1"][0] == pytest.approx(4.5)
    assert fit_res["coef_m1"][1] == pytest.approx(2.0 * math.sqrt(21.0))
    assert fit_res["coef_m1"][2] == pytest.approx(2.5 * math.sqrt(21.0))
    assert fit_res["coef_m1"][3] == pytest.approx(21.0)

    # Test point (p, o, y) = (0.5, 1, 7)
    std = math.sqrt(5.25)
    zp = (0.5 - 0.5) / std
    zo = (1.0 - 0.5) / std
    pred_m0 = fit_res["coef_m0"][0] + fit_res["coef_m0"][1] * zp
    pred_m1 = (
        fit_res["coef_m1"][0]
        + fit_res["coef_m1"][1] * zp
        + fit_res["coef_m1"][2] * zo
        + fit_res["coef_m1"][3] * zp * zo
    )
    assert pred_m0 == pytest.approx(0.0)
    assert pred_m1 == pytest.approx(7.0)
    d = (7.0 - pred_m0) ** 2 - (7.0 - pred_m1) ** 2
    assert d == pytest.approx(49.0)


def test_model_not_estimable() -> None:
    """Test rank deficiency, zero variance, and non-finite values produce not_estimable."""
    # Zero variance in p
    p_flat = np.zeros(18, dtype=np.float64)
    o = np.arange(18, dtype=np.float64)
    y = np.ones(18, dtype=np.float64)
    res = fit_models(p_flat, o, y)
    assert res["freeze_status"] == "not_estimable"
    assert res["coef_m0"] is None
    assert res["coef_m1"] is None

    # Linearly dependent p and o
    p = np.arange(18, dtype=np.float64)
    o = p * 2.0
    res = fit_models(p, o, y)
    assert res["freeze_status"] == "not_estimable"

    # Non-finite value in y
    y_inf = y.copy()
    y_inf[0] = np.nan
    res = fit_models(p, p * 3.0 + 1.0, y_inf)
    assert res["freeze_status"] == "not_estimable"


def _create_zip_file(path: Path, filename: str, content: bytes) -> str:
    """Create a zip file with single member and return its SHA-256."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, content)
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def test_archive_format_and_bounds(tmp_path: Path) -> None:
    """Test ZIP format, headers, duplicate columns, and resource validation (P1-03)."""
    csv_content = (
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
        "1,100.0,1.0,1,1,1792916101000,true\n"
    ).encode("utf-8")
    zip_path = tmp_path / "PREDICTUSDT-aggTrades-2026-10-25.zip"
    sha = _create_zip_file(zip_path, "PREDICTUSDT-aggTrades-2026-10-25.csv", csv_content)

    # Valid parse
    trades = parse_aggtrades_zip(zip_path, sha, expected_symbol="PREDICTUSDT", expected_date="2026-10-25")
    assert len(trades) == 1
    assert trades[0].trade_id == 1
    assert trades[0].price == 100.0

    # Wrong sha
    with pytest.raises(ValueError, match="hash_mismatch"):
        parse_aggtrades_zip(zip_path, "0" * 64, expected_symbol="PREDICTUSDT", expected_date="2026-10-25")

    # Invalid aggTrades CSV header rejected
    bad_header_csv = (
        "trade_id,price,qty,f_id,l_id,t_time,is_maker\n"
        "1,100.0,1.0,1,1,1792916101000,true\n"
    ).encode("utf-8")
    bad_hdr_zip = tmp_path / "bad_hdr.zip"
    bad_hdr_sha = _create_zip_file(bad_hdr_zip, "PREDICTUSDT-aggTrades-2026-10-25.csv", bad_header_csv)
    with pytest.raises(ValueError, match="invalid_aggtrades_csv_header"):
        parse_aggtrades_zip(bad_hdr_zip, bad_hdr_sha, expected_symbol="PREDICTUSDT", expected_date="2026-10-25")

    # Metrics parse
    metrics_csv = (
        "create_time,symbol,sum_open_interest\n"
        "2026-10-25 08:20:00,PREDICTUSDT,100.0\n"
        "2026-10-25 08:25:00,PREDICTUSDT,110.0\n"
    ).encode("utf-8")
    m_zip_path = tmp_path / "PREDICTUSDT-metrics-2026-10-25.zip"
    m_sha = _create_zip_file(m_zip_path, "PREDICTUSDT-metrics-2026-10-25.csv", metrics_csv)
    records = parse_metrics_zip(m_zip_path, m_sha, expected_symbol="PREDICTUSDT", expected_date="2026-10-25")
    assert len(records) == 2
    assert records[0].sum_open_interest == 100.0
    assert records[1].sum_open_interest == 110.0

    # Metrics duplicate column rejected
    dup_cols_csv = (
        "create_time,symbol,sum_open_interest,sum_open_interest\n"
        "2026-10-25 08:20:00,PREDICTUSDT,100.0,100.0\n"
    ).encode("utf-8")
    dup_zip = tmp_path / "dup_metrics.zip"
    dup_sha = _create_zip_file(dup_zip, "PREDICTUSDT-metrics-2026-10-25.csv", dup_cols_csv)
    with pytest.raises(ValueError, match="duplicate_metrics_columns"):
        parse_metrics_zip(dup_zip, dup_sha, expected_symbol="PREDICTUSDT", expected_date="2026-10-25")


def test_time_anchor_contract() -> None:
    """Test anchor trade selection, early trade diagnosis, and anchor delay cutoff."""
    S = SCHEDULED_LAUNCH_MS  # 2026-10-25 08:15:00 UTC

    # Case 1: Trade exactly at S
    t_exact = [AggTradeRecord(transact_time_ms=S, trade_id=1, price=100.0, quantity=1.0, is_buyer_maker=False)]
    case = build_case_features(t_exact, [], scheduled_launch_ms=S, schedule_evidence=VALID_SCHEDULE_EVIDENCE)
    assert case["t0_ms"] == S
    assert case["t0_delay_ms"] == 0

    # Case 2: Trade at S + 300,000 ms (valid anchor bound)
    t_bound = [AggTradeRecord(transact_time_ms=S + 300_000, trade_id=1, price=100.0, quantity=1.0, is_buyer_maker=False)]
    case = build_case_features(t_bound, [], scheduled_launch_ms=S, schedule_evidence=VALID_SCHEDULE_EVIDENCE)
    assert case["t0_ms"] == S + 300_000
    assert case["t0_delay_ms"] == 300_000

    # Case 3: Trade at S + 300,001 ms (exceeded anchor bound -> data_gap)
    t_exceeded = [AggTradeRecord(transact_time_ms=S + 300_001, trade_id=1, price=100.0, quantity=1.0, is_buyer_maker=False)]
    case = build_case_features(t_exceeded, [], scheduled_launch_ms=S, schedule_evidence=VALID_SCHEDULE_EVIDENCE)
    assert case["case_status"] == "data_gap"
    assert "anchor_delay_exceeded" in case["missing_reason"]

    # Case 4: Early trade before S
    t_early = [
        AggTradeRecord(transact_time_ms=S - 10_000, trade_id=1, price=99.0, quantity=1.0, is_buyer_maker=False),
        AggTradeRecord(transact_time_ms=S + 1000, trade_id=2, price=100.0, quantity=1.0, is_buyer_maker=False),
    ]
    case = build_case_features(t_early, [], scheduled_launch_ms=S, schedule_evidence=VALID_SCHEDULE_EVIDENCE)
    assert case["early_trades_count"] == 1
    assert case["t0_ms"] == S + 1000


def test_time_oi_and_price_boundaries() -> None:
    """Test Scenario C OI selection, price return p, response return y, and single baseline trade (P2-02)."""
    S = SCHEDULED_LAUNCH_MS
    t0 = S + 1000  # 08:15:01
    D = t0 + 25 * 60 * 1000  # 08:40:01
    E = D + 15 * 60 * 1000  # 08:55:01

    trades = [
        AggTradeRecord(transact_time_ms=t0, trade_id=1, price=100.0, quantity=1.0, is_buyer_maker=False),
        AggTradeRecord(transact_time_ms=t0 + 10 * 60 * 1000, trade_id=2, price=102.0, quantity=1.0, is_buyer_maker=False),
        AggTradeRecord(transact_time_ms=D - 1000, trade_id=3, price=100.0, quantity=1.0, is_buyer_maker=False),
        AggTradeRecord(transact_time_ms=D, trade_id=4, price=100.0, quantity=1.0, is_buyer_maker=False),
        AggTradeRecord(transact_time_ms=D + 5 * 60 * 1000, trade_id=5, price=98.0, quantity=1.0, is_buyer_maker=False),
        AggTradeRecord(transact_time_ms=D + 10 * 60 * 1000, trade_id=6, price=106.0, quantity=1.0, is_buyer_maker=False),
        AggTradeRecord(transact_time_ms=E, trade_id=7, price=104.0, quantity=1.0, is_buyer_maker=False),
    ]

    oi_records = [
        OiMetricRecord(1792916400000, TARGET_SYMBOL, 100.0),
        OiMetricRecord(1792916700000, TARGET_SYMBOL, 110.0),
    ]

    case = build_case_features(trades, oi_records, scheduled_launch_ms=S, schedule_evidence=VALID_SCHEDULE_EVIDENCE)
    assert case["case_status"] == "ready_for_scoring"
    assert case["p"] == pytest.approx(0.0)
    assert case["o"] == pytest.approx(0.1)
    assert case["y"] == pytest.approx(0.04)
    assert case["long_mae"] == pytest.approx(-0.02)
    assert case["long_mfe"] == pytest.approx(0.06)

    # P2-02 Check: Single baseline trade in [T0, D) gives p = 0.0 (not data_gap)
    single_base_trades = [
        AggTradeRecord(transact_time_ms=t0, trade_id=1, price=100.0, quantity=1.0, is_buyer_maker=False),
        AggTradeRecord(transact_time_ms=D, trade_id=4, price=100.0, quantity=1.0, is_buyer_maker=False),
        AggTradeRecord(transact_time_ms=E, trade_id=7, price=104.0, quantity=1.0, is_buyer_maker=False),
    ]
    case_single = build_case_features(single_base_trades, oi_records, scheduled_launch_ms=S, schedule_evidence=VALID_SCHEDULE_EVIDENCE)
    assert case_single["case_status"] == "ready_for_scoring"
    assert case_single["p"] == pytest.approx(0.0)


def test_score_hand_calculated_and_extrapolation() -> None:
    """Test end-to-end scoring against the independent numerical walkthrough in the Plan."""
    canonical_rows = _make_dummy_canonical_18_rows()
    p_train = np.array([r["p"] for r in canonical_rows], dtype=np.float64)
    o_train = np.array([r["o"] for r in canonical_rows], dtype=np.float64)
    y_train = np.array([r["y"] for r in canonical_rows], dtype=np.float64)
    frozen_model = fit_models(p_train, o_train, y_train)

    case = {
        "case_status": "ready_for_scoring",
        "missing_reason": "",
        "p": 0.0,
        "o": 0.1,
        "y": 0.04,
        "long_mae": -0.02,
        "long_mfe": 0.06,
        "t0_ms": SCHEDULED_LAUNCH_MS + 1000,
        "entry_price": 100.0,
        "endpoint_price": 104.0,
    }

    scored = score_case(case, frozen_model)
    assert scored["case_status"] == "scored"
    assert scored["prediction_M0"] == pytest.approx(0.01)
    assert scored["prediction_M1"] == pytest.approx(0.04)
    assert scored["abs_error_M0"] == pytest.approx(0.03)
    assert scored["abs_error_M1"] == pytest.approx(0.0)
    assert scored["d"] == pytest.approx(0.0009)
    assert scored["long_mae"] == pytest.approx(-0.02)
    assert scored["long_mfe"] == pytest.approx(0.06)


def _prepare_cli_fixtures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, out_dir: Path | None = None) -> dict[str, Any]:
    """Prepare canonical training panel, test inputs ZIPs, and valid auth dict with monkeypatched frozen identities."""
    if out_dir is None:
        out_dir = tmp_path / "batch_out"

    training_dir = tmp_path / "training_data"
    training_dir.mkdir(parents=True, exist_ok=True)
    panel_file = training_dir / "fixture_parent_panel.csv"
    canonical_rows = _make_dummy_canonical_18_rows()
    write_parent_panel_csv(canonical_rows, panel_file)
    panel_sha = hashlib.sha256(panel_file.read_bytes()).hexdigest()

    review_file = training_dir / "fixture_review_CN.md"
    review_file.write_text("# Training Review Fixture\n", encoding="utf-8")
    review_sha = hashlib.sha256(review_file.read_bytes()).hexdigest()

    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    S = SCHEDULED_LAUNCH_MS
    t0 = S + 1000
    D = t0 + 25 * 60 * 1000
    E = D + 15 * 60 * 1000

    trades_csv = (
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
        f"1,100.0,1.0,1,1,{t0},true\n"
        f"2,102.0,1.0,2,2,{t0 + 10 * 60 * 1000},true\n"
        f"3,100.0,1.0,3,3,{D - 1000},true\n"
        f"4,100.0,1.0,4,4,{D},true\n"
        f"5,98.0,1.0,5,5,{D + 5 * 60 * 1000},true\n"
        f"6,106.0,1.0,6,6,{D + 10 * 60 * 1000},true\n"
        f"7,104.0,1.0,7,7,{E},true\n"
    ).encode("utf-8")
    agg_zip = inputs_dir / "PREDICTUSDT-aggTrades-2026-10-25.zip"
    agg_sha = _create_zip_file(agg_zip, "PREDICTUSDT-aggTrades-2026-10-25.csv", trades_csv)

    metrics_csv = (
        "create_time,symbol,sum_open_interest\n"
        "2026-10-25 08:20:00,PREDICTUSDT,100.0\n"
        "2026-10-25 08:25:00,PREDICTUSDT,110.0\n"
    ).encode("utf-8")
    metrics_zip = inputs_dir / "PREDICTUSDT-metrics-2026-10-25.zip"
    metrics_sha = _create_zip_file(metrics_zip, "PREDICTUSDT-metrics-2026-10-25.csv", metrics_csv)

    # Monkeypatch frozen constants to match synthetic fixtures in this isolated test module
    monkeypatch.setattr(holdout_mod, "FROZEN_TRAINING_PANEL_PATH", str(panel_file))
    monkeypatch.setattr(holdout_mod, "FROZEN_TRAINING_PANEL_SHA256", panel_sha)
    monkeypatch.setattr(holdout_mod, "FROZEN_REVIEW_PATH", str(review_file))
    monkeypatch.setattr(holdout_mod, "FROZEN_REVIEW_SHA256", review_sha)
    monkeypatch.setattr(
        holdout_mod,
        "FROZEN_ZIP_SHA256",
        {
            "PREDICTUSDT-aggTrades-2026-10-25.zip": agg_sha,
            "PREDICTUSDT-metrics-2026-10-25.zip": metrics_sha,
        },
    )

    plan_path = holdout_mod.FROZEN_PLAN_PATH
    plan_sha = holdout_mod.FROZEN_PLAN_SHA256
    design_path = holdout_mod.FROZEN_DESIGN_PATH
    design_sha = holdout_mod.FROZEN_DESIGN_SHA256
    code_sha = hashlib.sha256(Path(holdout_mod.__file__).read_bytes()).hexdigest()

    auth_dict = {
        "consumer_path": holdout_mod.FROZEN_CONSUMER_PATH,
        "consumer_sha256": code_sha,
        "plan_path": plan_path,
        "plan_sha256": plan_sha,
        "design_path": design_path,
        "design_sha256": design_sha,
        "section_2_boundaries_accepted": True,
        "training_panel_path": str(panel_file),
        "training_panel_sha256": panel_sha,
        "training_review_path": str(review_file),
        "training_review_sha256": review_sha,
        "batch_root": str(out_dir),
        "allowed_actions": ["freeze_model", "score_case"],
        "network_allowed": False,
        "signal_allowed": False,
        "execution_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "inputs_dir": str(inputs_dir),
        "approved_inputs": {
            "PREDICTUSDT-aggTrades-2026-10-25.zip": agg_sha,
            "PREDICTUSDT-metrics-2026-10-25.zip": metrics_sha,
        },
        "schedule_evidence": VALID_SCHEDULE_EVIDENCE,
        "prior_exposure_disclosure": "fixture_testing_only",
    }
    return {
        "panel_file": panel_file,
        "review_file": review_file,
        "inputs_dir": inputs_dir,
        "out_dir": out_dir,
        "auth_dict": auth_dict,
        "agg_sha": agg_sha,
        "metrics_sha": metrics_sha,
        "code_sha": code_sha,
    }


def test_cli_canonical_to_three_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CLI runs end-to-end and produces all three output files with accurate hand-calculated numbers."""
    out_dir = tmp_path / "test_output_batch"
    fixtures = _prepare_cli_fixtures(tmp_path, monkeypatch, out_dir=out_dir)
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(fixtures["auth_dict"]), encoding="utf-8")

    rc = main(["--auth-file", str(auth_file), "--output-dir", str(out_dir)])
    assert rc == 0

    # 1. model_freeze.json
    freeze_json = out_dir / "model_freeze.json"
    assert freeze_json.is_file()
    freeze_data = json.loads(freeze_json.read_text(encoding="utf-8"))
    assert freeze_data["freeze_status"] == "frozen"
    assert len(freeze_data["training_parents"]) == 18
    assert "p_train_bounds" in freeze_data
    assert "o_train_bounds" in freeze_data
    assert "scenario_timing_protocol" in freeze_data
    # P1-07 Check: True min and max dates
    assert freeze_data["training_date_range"]["start"] == "2026-03-01"
    assert freeze_data["training_date_range"]["end"] == "2026-04-16"

    # 2. holdout_case.csv
    csv_file = out_dir / "holdout_case.csv"
    assert csv_file.is_file()
    lines = csv_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2  # header + 1 row
    reader = csv.DictReader(lines)
    assert tuple(reader.fieldnames) == HOLDOUT_CASE_HEADER
    row = next(reader)
    assert row["case_status"] == "scored"
    assert float(row["prediction_M0"]) == pytest.approx(0.01)
    assert float(row["prediction_M1"]) == pytest.approx(0.04)
    assert float(row["abs_error_M0"]) == pytest.approx(0.03)
    assert float(row["abs_error_M1"]) == pytest.approx(0.0)
    assert float(row["d"]) == pytest.approx(0.0009)
    assert float(row["long_mae"]) == pytest.approx(-0.02)
    assert float(row["long_mfe"]) == pytest.approx(0.06)
    # Check millisecond timestamps
    assert ".000 UTC" in row["t0_utc"] or " UTC" in row["t0_utc"]

    # 3. review_CN.md
    md_file = out_dir / "review_CN.md"
    assert md_file.is_file()
    md_content = md_file.read_text(encoding="utf-8")
    assert "PREDICTUSDT" in md_content
    assert "model_freeze.json" in md_content
    assert "batch_status=completed" in md_content
    # P1-07 Check: Report includes actual holdout archive digests
    assert "Holdout aggTrades Archive" in md_content
    assert fixtures["agg_sha"] in md_content
    assert "Holdout metrics Archive" in md_content
    assert fixtures["metrics_sha"] in md_content


def test_cli_freeze_precedes_new_content_and_disk_scoring(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify I/O order, disk-based model consumption, and file tampering rejection (P1-04)."""
    out_dir = tmp_path / "batch_freeze_seq"
    fixtures = _prepare_cli_fixtures(tmp_path, monkeypatch, out_dir=out_dir)

    io_events: list[str] = []
    original_freeze_write = Path.write_bytes
    original_parse_agg = holdout_mod.parse_aggtrades_zip
    original_parse_metrics = holdout_mod.parse_metrics_zip
    original_score_case = holdout_mod.score_case

    def spy_freeze_write(path_obj: Path, data: bytes) -> int:
        if path_obj.name == "model_freeze.json":
            io_events.append("WRITE:model_freeze.json")
        return original_freeze_write(path_obj, data)

    def spy_parse_agg(*args: Any, **kwargs: Any) -> Any:
        io_events.append("READ:aggtrades_zip")
        return original_parse_agg(*args, **kwargs)

    def spy_parse_metrics(*args: Any, **kwargs: Any) -> Any:
        io_events.append("READ:metrics_zip")
        return original_parse_metrics(*args, **kwargs)

    def spy_score_case(*args: Any, **kwargs: Any) -> Any:
        io_events.append("CALL:score_case")
        return original_score_case(*args, **kwargs)

    monkeypatch.setattr(Path, "write_bytes", spy_freeze_write)
    monkeypatch.setattr(holdout_mod, "parse_aggtrades_zip", spy_parse_agg)
    monkeypatch.setattr(holdout_mod, "parse_metrics_zip", spy_parse_metrics)
    monkeypatch.setattr(holdout_mod, "score_case", spy_score_case)

    auth_file = tmp_path / "auth_seq.json"
    auth_file.write_text(json.dumps(fixtures["auth_dict"]), encoding="utf-8")

    rc = main(["--auth-file", str(auth_file), "--output-dir", str(out_dir)])
    assert rc == 0

    # P1-04 Check: I/O events sequence assertion
    assert "WRITE:model_freeze.json" in io_events
    assert "READ:aggtrades_zip" in io_events
    assert "READ:metrics_zip" in io_events
    assert "CALL:score_case" in io_events

    idx_freeze = io_events.index("WRITE:model_freeze.json")
    idx_agg = io_events.index("READ:aggtrades_zip")
    idx_metrics = io_events.index("READ:metrics_zip")
    idx_score = io_events.index("CALL:score_case")

    assert idx_freeze < idx_agg
    assert idx_freeze < idx_metrics
    assert idx_agg < idx_score

    # File tampering test
    out_dir2 = tmp_path / "batch_tamper"
    fixtures2 = _prepare_cli_fixtures(tmp_path, monkeypatch, out_dir=out_dir2)
    auth_file2 = tmp_path / "auth_tamper.json"
    auth_file2.write_text(json.dumps(fixtures2["auth_dict"]), encoding="utf-8")

    original_build_case_features = holdout_mod.build_case_features

    def tamper_hook(*args: Any, **kwargs: Any) -> Any:
        (out_dir2 / "model_freeze.json").write_text('{"tampered": true}', encoding="utf-8")
        return original_build_case_features(*args, **kwargs)

    monkeypatch.setattr(holdout_mod, "build_case_features", tamper_hook)
    rc_tamper = main(["--auth-file", str(auth_file2), "--output-dir", str(out_dir2)])
    assert rc_tamper != 0


def test_cli_p1_01_and_p1_02_protections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify consumer identity, companion review, explicit false permissions, output root, symlinks, and containment (P1-01, P1-02)."""
    out_dir = tmp_path / "out_p1"
    fixtures = _prepare_cli_fixtures(tmp_path, monkeypatch, out_dir=out_dir)

    # P1-01: Invalid consumer path rejected
    bad_consumer_path = dict(fixtures["auth_dict"])
    bad_consumer_path["consumer_path"] = "scripts/wrong_script.py"
    f_cpath = tmp_path / "auth_bad_cpath.json"
    f_cpath.write_text(json.dumps(bad_consumer_path), encoding="utf-8")
    assert main(["--auth-file", str(f_cpath), "--output-dir", str(out_dir)]) != 0

    # P1-01: Invalid consumer SHA rejected
    bad_consumer = dict(fixtures["auth_dict"])
    bad_consumer["consumer_sha256"] = "bad" * 21 + "b"
    f_consumer = tmp_path / "auth_bad_consumer.json"
    f_consumer.write_text(json.dumps(bad_consumer), encoding="utf-8")
    assert main(["--auth-file", str(f_consumer), "--output-dir", str(out_dir)]) != 0

    # P1-01: Invalid training review SHA rejected
    bad_review = dict(fixtures["auth_dict"])
    bad_review["training_review_sha256"] = "0" * 64
    f_review = tmp_path / "auth_bad_review.json"
    f_review.write_text(json.dumps(bad_review), encoding="utf-8")
    assert main(["--auth-file", str(f_review), "--output-dir", str(out_dir)]) != 0

    # P1-01: Missing trading permission rejected
    bad_perm = dict(fixtures["auth_dict"])
    del bad_perm["live_trading_allowed"]
    f_perm = tmp_path / "auth_bad_perm.json"
    f_perm.write_text(json.dumps(bad_perm), encoding="utf-8")
    assert main(["--auth-file", str(f_perm), "--output-dir", str(out_dir)]) != 0

    # P1-02: Output root mismatch rejected
    f_root = tmp_path / "auth_bad_root.json"
    bad_root_auth = dict(fixtures["auth_dict"])
    bad_root_auth["batch_root"] = str(tmp_path / "different_root")
    f_root.write_text(json.dumps(bad_root_auth), encoding="utf-8")
    assert main(["--auth-file", str(f_root), "--output-dir", str(out_dir)]) != 0

    # P1-02: Symlink ancestor in output path rejected
    symlink_dir = tmp_path / "symlink_dir"
    target_real_dir = tmp_path / "target_real_dir"
    target_real_dir.mkdir(parents=True, exist_ok=True)
    symlink_dir.symlink_to(target_real_dir)
    symlink_out = symlink_dir / "out"

    bad_sym_auth = dict(fixtures["auth_dict"])
    bad_sym_auth["batch_root"] = str(symlink_out)
    f_sym = tmp_path / "auth_symlink.json"
    f_sym.write_text(json.dumps(bad_sym_auth), encoding="utf-8")
    assert main(["--auth-file", str(f_sym), "--output-dir", str(symlink_out)]) != 0

    # P1-02: Output inside external inputs dir rejected (containment when not downloading)
    out_inside_inputs = fixtures["inputs_dir"] / "nested_out"
    bad_cont_auth = dict(fixtures["auth_dict"])
    bad_cont_auth["batch_root"] = str(out_inside_inputs)
    f_cont = tmp_path / "auth_cont.json"
    f_cont.write_text(json.dumps(bad_cont_auth), encoding="utf-8")
    assert main(["--auth-file", str(f_cont), "--output-dir", str(out_inside_inputs)]) != 0


def test_cli_p1_05_download_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify download branch, batch_root/inputs location, and cross-domain redirect rejection (P1-02, P1-05)."""
    out_dir = tmp_path / "out_download"
    download_inputs_dir = out_dir / "inputs"

    fixtures = _prepare_cli_fixtures(tmp_path, monkeypatch, out_dir=out_dir)
    fixtures["auth_dict"]["inputs_dir"] = str(download_inputs_dir)
    fixtures["auth_dict"]["allowed_actions"] = ["freeze_model", "download_inputs", "score_case"]
    fixtures["auth_dict"]["network_allowed"] = True

    trades_csv = (
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
        f"1,100.0,1.0,1,1,{SCHEDULED_LAUNCH_MS + 1000},true\n"
    ).encode("utf-8")
    raw_zip_buf = io.BytesIO()
    with zipfile.ZipFile(raw_zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("PREDICTUSDT-aggTrades-2026-10-25.csv", trades_csv)
    zip_bytes = raw_zip_buf.getvalue()
    zip_sha = hashlib.sha256(zip_bytes).hexdigest()

    metrics_csv = (
        "create_time,symbol,sum_open_interest\n"
        "2026-10-25 08:20:00,PREDICTUSDT,100.0\n"
    ).encode("utf-8")
    raw_m_buf = io.BytesIO()
    with zipfile.ZipFile(raw_m_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("PREDICTUSDT-metrics-2026-10-25.csv", metrics_csv)
    m_zip_bytes = raw_m_buf.getvalue()
    m_zip_sha = hashlib.sha256(m_zip_bytes).hexdigest()

    monkeypatch.setattr(
        holdout_mod,
        "FROZEN_ZIP_SHA256",
        {
            "PREDICTUSDT-aggTrades-2026-10-25.zip": zip_sha,
            "PREDICTUSDT-metrics-2026-10-25.zip": m_zip_sha,
        },
    )
    fixtures["auth_dict"]["approved_inputs"] = {
        "PREDICTUSDT-aggTrades-2026-10-25.zip": zip_sha,
        "PREDICTUSDT-metrics-2026-10-25.zip": m_zip_sha,
    }

    class MockResponse:
        def __init__(self, data: bytes):
            self._io = io.BytesIO(data)
            self.status = 200

        def read(self, size: int = -1) -> bytes:
            return self._io.read(size)

        def __enter__(self) -> MockResponse:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    class MockOpener:
        def open(self, req: Any, timeout: int = 30) -> MockResponse:
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if url.endswith("PREDICTUSDT-aggTrades-2026-10-25.zip.CHECKSUM"):
                return MockResponse(f"{zip_sha}  PREDICTUSDT-aggTrades-2026-10-25.zip\n".encode("utf-8"))
            elif url.endswith("PREDICTUSDT-aggTrades-2026-10-25.zip"):
                return MockResponse(zip_bytes)
            elif url.endswith("PREDICTUSDT-metrics-2026-10-25.zip.CHECKSUM"):
                return MockResponse(f"{m_zip_sha}  PREDICTUSDT-metrics-2026-10-25.zip\n".encode("utf-8"))
            elif url.endswith("PREDICTUSDT-metrics-2026-10-25.zip"):
                return MockResponse(m_zip_bytes)
            raise ValueError(f"Unexpected url in mock: {url}")

    monkeypatch.setattr(holdout_mod.urllib.request, "build_opener", lambda *args: MockOpener())

    auth_file = tmp_path / "auth_dl.json"
    auth_file.write_text(json.dumps(fixtures["auth_dict"]), encoding="utf-8")

    # 1. Successful download to batch_root/inputs
    rc = main(["--auth-file", str(auth_file), "--output-dir", str(out_dir)])
    assert rc == 0
    assert (download_inputs_dir / "PREDICTUSDT-aggTrades-2026-10-25.zip").is_file()
    assert (download_inputs_dir / "PREDICTUSDT-aggTrades-2026-10-25.zip.CHECKSUM").is_file()

    # 2. Download inputs dir NOT inside batch_root/inputs rejected
    out_dir_ext = tmp_path / "out_ext_dl"
    fixtures["auth_dict"]["batch_root"] = str(out_dir_ext)
    fixtures["auth_dict"]["inputs_dir"] = str(tmp_path / "external_inputs")
    auth_file_ext = tmp_path / "auth_ext_dl.json"
    auth_file_ext.write_text(json.dumps(fixtures["auth_dict"]), encoding="utf-8")
    assert main(["--auth-file", str(auth_file_ext), "--output-dir", str(out_dir_ext)]) != 0

    # 3. SafeRedirectHandler blocks cross-domain redirects
    handler = holdout_mod.SafeRedirectHandler()
    req = urllib.request.Request("https://data.binance.vision/test")
    with pytest.raises(urllib.error.HTTPError, match="cross_domain_or_insecure_redirect_rejected"):
        handler.redirect_request(req, None, 302, "Found", {}, "https://evil.com/fake.CHECKSUM")


def test_cli_p1_06_schedule_evidence_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify schedule evidence validation and honest conflict reporting (P1-06)."""
    out_dir = tmp_path / "out_sched_conflict"
    fixtures = _prepare_cli_fixtures(tmp_path, monkeypatch, out_dir=out_dir)

    # Case 1: unverified schedule status -> anchor_or_regime_conflict
    bad_evidence = dict(VALID_SCHEDULE_EVIDENCE)
    bad_evidence["version_verification_status"] = "unverified"
    fixtures["auth_dict"]["schedule_evidence"] = bad_evidence

    auth_file = tmp_path / "auth_unverified_sched.json"
    auth_file.write_text(json.dumps(fixtures["auth_dict"]), encoding="utf-8")

    rc = main(["--auth-file", str(auth_file), "--output-dir", str(out_dir)])
    assert rc == 0

    csv_file = out_dir / "holdout_case.csv"
    assert csv_file.is_file()
    reader = csv.DictReader(csv_file.read_text(encoding="utf-8").strip().splitlines())
    row = next(reader)
    assert row["case_status"] == "anchor_or_regime_conflict"
    assert row["missing_reason"] == "schedule_evidence_insufficient_or_untrusted"

    md_file = out_dir / "review_CN.md"
    assert md_file.is_file()
    md_content = md_file.read_text(encoding="utf-8")
    assert "anchor_or_regime_conflict" in md_content
    assert "schedule_evidence_insufficient_or_untrusted" in md_content


def test_cli_p1_07_not_estimable_and_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify model not_estimable produces consistent CSV/review, and write failure causes RC!=0 (P1-07)."""
    out_dir = tmp_path / "out_not_estimable"
    fixtures = _prepare_cli_fixtures(tmp_path, monkeypatch, out_dir=out_dir)

    # Force fit_models to return not_estimable
    monkeypatch.setattr(
        holdout_mod,
        "fit_models",
        lambda *args, **kwargs: {"freeze_status": "not_estimable", "reason": "test_zero_variance"},
    )

    auth_file = tmp_path / "auth_not_est.json"
    auth_file.write_text(json.dumps(fixtures["auth_dict"]), encoding="utf-8")

    rc = main(["--auth-file", str(auth_file), "--output-dir", str(out_dir)])
    assert rc == 0

    csv_file = out_dir / "holdout_case.csv"
    assert csv_file.is_file()
    reader = csv.DictReader(csv_file.read_text(encoding="utf-8").strip().splitlines())
    row = next(reader)
    assert row["case_status"] == "not_estimable"
    assert row["missing_reason"] == "test_zero_variance"

    md_file = out_dir / "review_CN.md"
    assert md_file.is_file()
    md_content = md_file.read_text(encoding="utf-8")
    assert "not_estimable" in md_content
    assert "test_zero_variance" in md_content
    assert "Scored Count**: 0" in md_content
    assert "Missing Count**: 1" in md_content

    # Write failure causes RC!=0
    out_dir_fail = tmp_path / "out_write_fail"
    fixtures2 = _prepare_cli_fixtures(tmp_path, monkeypatch, out_dir=out_dir_fail)
    auth_file_fail = tmp_path / "auth_fail.json"
    auth_file_fail.write_text(json.dumps(fixtures2["auth_dict"]), encoding="utf-8")

    def bad_writer(*args: Any, **kwargs: Any) -> None:
        raise OSError("Permission denied / disk full simulation")

    monkeypatch.setattr(holdout_mod, "_write_holdout_case_csv", bad_writer)
    assert main(["--auth-file", str(auth_file_fail), "--output-dir", str(out_dir_fail)]) != 0
