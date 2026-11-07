"""Tests for launch price, OI, and basis incremental information analysis.

Conforms to L1 Engineering Process Rules and Rule 15 fixture integrity.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from scripts.external_signal_shadow.run_launch_price_oi_basis_incremental_information import (
    IncrementalAnalysisError,
    build_parent_panel,
    evaluate_comparisons,
    load_snapshot,
    main,
    summarize,
)
from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
    ChildEvaluation,
    aggregate_and_group,
    write_exploratory_outputs,
)


def _compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_canonical_test_csv(tmp_path: Path, children: list[ChildEvaluation]) -> tuple[Path, str]:
    """Generates canonical child_rows.csv via upstream writer and returns (path, sha256)."""
    res = aggregate_and_group(children)
    out_dir = tmp_path / f"canonical_out_{len(children)}"
    child_csv, _ = write_exploratory_outputs(out_dir, children, res, project_root=tmp_path)
    return child_csv, _compute_sha256(child_csv)


def test_snapshot_canonical_contract_and_mutations(tmp_path: Path) -> None:
    """Task 1: Tests load_snapshot against canonical upstream writer and single-point mutations."""
    # 1. Generate canonical children
    c_complete = ChildEvaluation(
        parent_article_id="p1",
        symbol="SYM1",
        listing_regime="standard",
        is_complete=True,
        utc_date="2026-05-01",
        path_status="ok",
        oi_status="ok",
        oi_change=0.15,
        oi_a_status="ok",
        oi_a_change=0.10,
        oi_b_status="ok",
        oi_b_change=0.15,
        oi_c_status="ok",
        oi_c_change=0.20,
        baseline_price_change=0.05,
        terminal_return=0.02,
        long_mae=-0.03,
        long_mfe=0.06,
        basis_status="ok",
        basis=-0.001,
    )
    c_missing = ChildEvaluation(
        parent_article_id="p2",
        symbol="SYM2",
        listing_regime="pre_market",
        is_complete=False,
        missing_reason="missing_jb_anchor_time",
        path_status="missing_jb_anchor_time",
        oi_status="missing_jb_anchor_time",
        oi_a_status="missing_jb_anchor_time",
        oi_b_status="missing_jb_anchor_time",
        oi_c_status="missing_jb_anchor_time",
    )

    csv_path, sha = _make_canonical_test_csv(tmp_path, [c_complete, c_missing])

    # Positive test: canonical CSV loads successfully
    rows = load_snapshot(csv_path, expected_sha256=sha)
    assert len(rows) == 2
    r0 = [r for r in rows if r["symbol"] == "SYM1"][0]
    assert r0["parent_article_id"] == "p1"
    assert r0["listing_regime"] == "standard"
    assert r0["path_status"] == "ok"
    assert r0["baseline_price_change"] == pytest.approx(0.05)
    assert r0["oi_b_change"] == pytest.approx(0.15)
    assert r0["basis"] == pytest.approx(-0.001)

    r1 = [r for r in rows if r["symbol"] == "SYM2"][0]
    assert r1["path_status"] == "missing_jb_anchor_time"
    assert r1["is_complete"] is False

    # Negative 1: Bad expected SHA-256
    with pytest.raises(IncrementalAnalysisError, match="snapshot_sha256_mismatch"):
        load_snapshot(csv_path, expected_sha256="0" * 64)

    # Helper for mutation tests
    raw_lines = csv_path.read_text(encoding="utf-8").splitlines()
    header = raw_lines[0].split(",")

    def _write_mutated(filename: str, mut_header: list[str], mut_rows: list[list[str]]) -> Path:
        p = tmp_path / filename
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(mut_header)
            w.writerows(mut_rows)
        return p

    data_rows = [line.split(",") for line in raw_lines[1:]]

    # Negative 2: Missing required column
    bad_hdr = [col for col in header if col != "baseline_price_change"]
    p_mut = _write_mutated("mut_missing_col.csv", bad_hdr, [r[:-1] for r in data_rows])
    with pytest.raises(IncrementalAnalysisError, match="snapshot_header_mismatch|missing_column"):
        load_snapshot(p_mut, expected_sha256=_compute_sha256(p_mut))

    # Negative 3: Duplicate column in header
    bad_hdr_dup = list(header)
    bad_hdr_dup[1] = bad_hdr_dup[0]
    p_dup = _write_mutated("mut_dup_col.csv", bad_hdr_dup, data_rows)
    with pytest.raises(IncrementalAnalysisError, match="snapshot_header_mismatch|duplicate_column"):
        load_snapshot(p_dup, expected_sha256=_compute_sha256(p_dup))

    # Negative 4: Short row / field count mismatch
    short_rows = [list(data_rows[0][:-2]), list(data_rows[1])]
    p_short = _write_mutated("mut_short_row.csv", header, short_rows)
    with pytest.raises(IncrementalAnalysisError, match="row_field_count_mismatch"):
        load_snapshot(p_short, expected_sha256=_compute_sha256(p_short))

    # Negative 5: Duplicate (parent_article_id, symbol)
    dup_key_rows = [list(data_rows[0]), list(data_rows[0])]
    p_dup_key = _write_mutated("mut_dup_key.csv", header, dup_key_rows)
    with pytest.raises(IncrementalAnalysisError, match="duplicate_parent_symbol_key"):
        load_snapshot(p_dup_key, expected_sha256=_compute_sha256(p_dup_key))

    # Negative 6: Unknown regime
    reg_idx = header.index("listing_regime")
    bad_reg_rows = [list(data_rows[0]), list(data_rows[1])]
    bad_reg_rows[0][reg_idx] = "unsupported_regime"
    p_bad_reg = _write_mutated("mut_bad_reg.csv", header, bad_reg_rows)
    with pytest.raises(IncrementalAnalysisError, match="invalid_listing_regime"):
        load_snapshot(p_bad_reg, expected_sha256=_compute_sha256(p_bad_reg))

    # Negative 7: ok status paired with empty or NaN
    oi_b_idx = header.index("oi_b_change")
    oi_chg_idx = header.index("oi_change")
    bad_nan_rows = [list(data_rows[0]), list(data_rows[1])]
    bad_nan_rows[0][oi_b_idx] = "nan"
    bad_nan_rows[0][oi_chg_idx] = "nan"
    p_nan = _write_mutated("mut_nan.csv", header, bad_nan_rows)
    with pytest.raises(IncrementalAnalysisError, match="non_finite_or_empty_value"):
        load_snapshot(p_nan, expected_sha256=_compute_sha256(p_nan))

    bad_empty_rows = [list(data_rows[0]), list(data_rows[1])]
    bad_empty_rows[0][oi_b_idx] = ""
    bad_empty_rows[0][oi_chg_idx] = ""
    p_empty = _write_mutated("mut_empty.csv", header, bad_empty_rows)
    with pytest.raises(IncrementalAnalysisError, match="non_finite_or_empty_value"):
        load_snapshot(p_empty, expected_sha256=_compute_sha256(p_empty))

    # Negative 8: B alias mismatch (oi_status != oi_b_status or oi_change != oi_b_change)
    oi_st_idx = header.index("oi_status")
    oi_b_st_idx = header.index("oi_b_status")
    bad_alias_rows = [list(data_rows[0]), list(data_rows[1])]
    bad_alias_rows[0][oi_st_idx] = "missing"
    p_alias = _write_mutated("mut_alias.csv", header, bad_alias_rows)
    with pytest.raises(IncrementalAnalysisError, match="alias_status_mismatch"):
        load_snapshot(p_alias, expected_sha256=_compute_sha256(p_alias))

    # Negative 9: Missing anchor row paired with finite results
    term_idx = header.index("terminal_return")
    bad_missing_anchor = [list(data_rows[0]), list(data_rows[1])]
    bad_missing_anchor[1][term_idx] = "0.05"
    p_miss_finite = _write_mutated("mut_miss_finite.csv", header, bad_missing_anchor)
    with pytest.raises(IncrementalAnalysisError, match="missing_anchor_row_has_finite_values"):
        load_snapshot(p_miss_finite, expected_sha256=_compute_sha256(p_miss_finite))

    # Negative 10: Basis empty status on ok path
    basis_st_idx = header.index("basis_status")
    bad_basis_st = [list(data_rows[0]), list(data_rows[1])]
    bad_basis_st[0][basis_st_idx] = ""
    p_basis_empty = _write_mutated("mut_basis_empty.csv", header, bad_basis_st)
    with pytest.raises(IncrementalAnalysisError, match="invalid_basis_status_for_ok_path"):
        load_snapshot(p_basis_empty, expected_sha256=_compute_sha256(p_basis_empty))

    # Negative 11: PIT status upgraded
    pit_idx = header.index("pit_verification_status")
    bad_pit = [list(data_rows[0]), list(data_rows[1])]
    bad_pit[0][pit_idx] = "pit_verified"
    p_pit = _write_mutated("mut_pit.csv", header, bad_pit)
    with pytest.raises(IncrementalAnalysisError, match="unsupported_pit_status"):
        load_snapshot(p_pit, expected_sha256=_compute_sha256(p_pit))

    # Negative 12: Scenario A status set to unknown value
    oi_a_st_idx = header.index("oi_a_status")
    bad_a_st = [list(data_rows[0]), list(data_rows[1])]
    bad_a_st[0][oi_a_st_idx] = "unknown_status"
    p_bad_a_st = _write_mutated("mut_bad_a_st.csv", header, bad_a_st)
    with pytest.raises(IncrementalAnalysisError, match="invalid_scenario_oi_status"):
        load_snapshot(p_bad_a_st, expected_sha256=_compute_sha256(p_bad_a_st))

    # Negative 13: Complete B row paired with is_complete=false
    is_comp_idx = header.index("is_complete")
    bad_is_comp = [list(data_rows[0]), list(data_rows[1])]
    bad_is_comp[0][is_comp_idx] = "false"
    p_bad_is_comp = _write_mutated("mut_bad_is_comp.csv", header, bad_is_comp)
    with pytest.raises(IncrementalAnalysisError, match="complete_b_has_is_complete_false"):
        load_snapshot(p_bad_is_comp, expected_sha256=_compute_sha256(p_bad_is_comp))

    # Negative 14: Invalid UTC date format
    utc_idx = header.index("utc_date")
    bad_date = [list(data_rows[0]), list(data_rows[1])]
    bad_date[0][utc_idx] = "not-a-date"
    p_bad_date = _write_mutated("mut_bad_date.csv", header, bad_date)
    with pytest.raises(IncrementalAnalysisError, match="invalid_utc_date_format"):
        load_snapshot(p_bad_date, expected_sha256=_compute_sha256(p_bad_date))

    # Negative 15: Scenario A status set to unapproved status (missing_predecessor) with empty change
    oi_a_chg_idx = header.index("oi_a_change")
    bad_a_pred = [list(data_rows[0]), list(data_rows[1])]
    bad_a_pred[0][oi_a_st_idx] = "missing_predecessor"
    bad_a_pred[0][oi_a_chg_idx] = ""
    p_a_pred = _write_mutated("mut_a_pred.csv", header, bad_a_pred)
    with pytest.raises(IncrementalAnalysisError, match="invalid_scenario_oi_status"):
        load_snapshot(p_a_pred, expected_sha256=_compute_sha256(p_a_pred))

    # Negative 16: Missing anchor row has unexpected scenario status
    bad_miss_scn = [list(data_rows[0]), list(data_rows[1])]
    bad_miss_scn[1][oi_a_st_idx] = "unexpected_status"
    p_miss_scn = _write_mutated("mut_miss_scn.csv", header, bad_miss_scn)
    with pytest.raises(IncrementalAnalysisError, match="missing_anchor_scenario_status_mismatch"):
        load_snapshot(p_miss_scn, expected_sha256=_compute_sha256(p_miss_scn))

    # Negative 17: Missing anchor row has ok oi_status
    bad_miss_oi_ok = [list(data_rows[0]), list(data_rows[1])]
    bad_miss_oi_ok[1][oi_st_idx] = "ok"
    bad_miss_oi_ok[1][oi_b_st_idx] = "ok"
    p_miss_oi_ok = _write_mutated("mut_miss_oi_ok.csv", header, bad_miss_oi_ok)
    with pytest.raises(IncrementalAnalysisError, match="missing_anchor_oi_status_mismatch"):
        load_snapshot(p_miss_oi_ok, expected_sha256=_compute_sha256(p_miss_oi_ok))

    # Negative 18: Ok path row has non-empty missing_reason
    miss_rsn_idx = header.index("missing_reason")
    bad_ok_rsn = [list(data_rows[0]), list(data_rows[1])]
    bad_ok_rsn[0][miss_rsn_idx] = "missing_jb_anchor_time"
    p_ok_rsn = _write_mutated("mut_ok_rsn.csv", header, bad_ok_rsn)
    with pytest.raises(IncrementalAnalysisError, match="ok_path_has_missing_reason"):
        load_snapshot(p_ok_rsn, expected_sha256=_compute_sha256(p_ok_rsn))

    # Negative 19: Ok path row has missing_jb_anchor_time for oi_status
    bad_ok_anchor_oi = [list(data_rows[0]), list(data_rows[1])]
    bad_ok_anchor_oi[0][oi_st_idx] = "missing_jb_anchor_time"
    bad_ok_anchor_oi[0][oi_b_st_idx] = "missing_jb_anchor_time"
    p_ok_anchor_oi = _write_mutated("mut_ok_anchor_oi.csv", header, bad_ok_anchor_oi)
    with pytest.raises(IncrementalAnalysisError, match="ok_path_has_non_ok_oi_status"):
        load_snapshot(p_ok_anchor_oi, expected_sha256=_compute_sha256(p_ok_anchor_oi))


def test_parent_panel_conservation_and_dates(tmp_path: Path) -> None:
    """Task 1: Tests build_parent_panel medians, conservation, incomplete handling, and date resolution."""
    # 1. Parent p1 with 3 complete children: p=(0.1, 0.3, 1.1), o_B=(0.2, 0.6, 1.9), y=(-0.1, 0.3, 0.9)
    # Expected medians: p=0.3, o_B=0.6, y=0.3
    c1 = ChildEvaluation(
        parent_article_id="p1",
        symbol="S1",
        listing_regime="standard",
        is_complete=True,
        utc_date="2026-05-01",
        path_status="ok",
        oi_status="ok",
        oi_change=0.2,
        oi_b_status="ok",
        oi_b_change=0.2,
        oi_a_status="ok",
        oi_a_change=0.1,
        oi_c_status="ok",
        oi_c_change=0.3,
        baseline_price_change=0.1,
        terminal_return=-0.1,
        long_mae=-0.05,
        long_mfe=0.08,
        basis_status="ok",
        basis=-0.002,
    )
    c2 = ChildEvaluation(
        parent_article_id="p1",
        symbol="S2",
        listing_regime="standard",
        is_complete=True,
        utc_date="2026-05-01",
        path_status="ok",
        oi_status="ok",
        oi_change=0.6,
        oi_b_status="ok",
        oi_b_change=0.6,
        oi_a_status="ok",
        oi_a_change=0.5,
        oi_c_status="ok",
        oi_c_change=0.7,
        baseline_price_change=0.3,
        terminal_return=0.3,
        long_mae=-0.02,
        long_mfe=0.10,
        basis_status="ok",
        basis=-0.001,
    )
    c3 = ChildEvaluation(
        parent_article_id="p1",
        symbol="S3",
        listing_regime="standard",
        is_complete=True,
        utc_date="2026-05-01",
        path_status="ok",
        oi_status="ok",
        oi_change=1.9,
        oi_b_status="ok",
        oi_b_change=1.9,
        oi_a_status="ok",
        oi_a_change=1.8,
        oi_c_status="ok",
        oi_c_change=2.0,
        baseline_price_change=1.1,
        terminal_return=0.9,
        long_mae=-0.01,
        long_mfe=0.20,
        basis_status="ok",
        basis=0.003,
    )

    # 2. Parent p_even with 2 children: p=(0.1, 0.3) -> median 0.2
    c_even1 = ChildEvaluation(
        parent_article_id="p_even",
        symbol="SE1",
        listing_regime="standard",
        is_complete=True,
        utc_date="2026-06-01",
        path_status="ok",
        oi_status="ok",
        oi_change=0.4,
        oi_b_status="ok",
        oi_b_change=0.4,
        oi_a_status="ok",
        oi_a_change=0.3,
        oi_c_status="ok",
        oi_c_change=0.5,
        baseline_price_change=0.1,
        terminal_return=0.05,
        long_mae=-0.02,
        long_mfe=0.08,
        basis_status="ok",
        basis=0.001,
    )
    c_even2 = ChildEvaluation(
        parent_article_id="p_even",
        symbol="SE2",
        listing_regime="standard",
        is_complete=True,
        utc_date="2026-06-01",
        path_status="ok",
        oi_status="ok",
        oi_change=0.8,
        oi_b_status="ok",
        oi_b_change=0.8,
        oi_a_status="ok",
        oi_a_change=0.7,
        oi_c_status="ok",
        oi_c_change=0.9,
        baseline_price_change=0.3,
        terminal_return=0.15,
        long_mae=-0.04,
        long_mfe=0.12,
        basis_status="ok",
        basis=0.002,
    )

    # 3. Parent p_inc with 1 complete and 1 missing anchor child
    c_inc_ok = ChildEvaluation(
        parent_article_id="p_inc",
        symbol="SI1",
        listing_regime="standard",
        is_complete=True,
        utc_date="2026-07-01",
        path_status="ok",
        oi_status="ok",
        oi_change=0.1,
        oi_b_status="ok",
        oi_b_change=0.1,
        oi_a_status="ok",
        oi_a_change=0.1,
        oi_c_status="ok",
        oi_c_change=0.1,
        baseline_price_change=0.05,
        terminal_return=0.01,
        long_mae=-0.01,
        long_mfe=0.02,
        basis_status="ok",
        basis=0.0,
    )
    c_inc_bad = ChildEvaluation(
        parent_article_id="p_inc",
        symbol="SI2",
        listing_regime="standard",
        is_complete=False,
        missing_reason="missing_jb_anchor_time",
        path_status="missing_jb_anchor_time",
        oi_status="missing_jb_anchor_time",
        oi_a_status="missing_jb_anchor_time",
        oi_b_status="missing_jb_anchor_time",
        oi_c_status="missing_jb_anchor_time",
    )

    # 4. Parent p_basis_miss with 2 complete OI children, but 1 unverified basis mapping
    c_bm1 = ChildEvaluation(
        parent_article_id="p_bmiss",
        symbol="SBM1",
        listing_regime="standard",
        is_complete=True,
        utc_date="2026-08-01",
        path_status="ok",
        oi_status="ok",
        oi_change=0.2,
        oi_b_status="ok",
        oi_b_change=0.2,
        oi_a_status="ok",
        oi_a_change=0.2,
        oi_c_status="ok",
        oi_c_change=0.2,
        baseline_price_change=0.1,
        terminal_return=0.02,
        long_mae=-0.02,
        long_mfe=0.05,
        basis_status="ok",
        basis=0.001,
    )
    c_bm2 = ChildEvaluation(
        parent_article_id="p_bmiss",
        symbol="SBM2",
        listing_regime="standard",
        is_complete=True,
        utc_date="2026-08-01",
        path_status="ok",
        oi_status="ok",
        oi_change=0.4,
        oi_b_status="ok",
        oi_b_change=0.4,
        oi_a_status="ok",
        oi_a_change=0.4,
        oi_c_status="ok",
        oi_c_change=0.4,
        baseline_price_change=0.2,
        terminal_return=0.04,
        long_mae=-0.01,
        long_mfe=0.06,
        basis_status="unverified_product_mapping",
    )

    # 5. Parent p_multi_date with children having conflicting dates
    c_md1 = ChildEvaluation(
        parent_article_id="p_mdate",
        symbol="SMD1",
        listing_regime="pre_market",
        is_complete=True,
        utc_date="2026-01-10",
        path_status="ok",
        oi_status="ok",
        oi_change=0.05,
        oi_b_status="ok",
        oi_b_change=0.05,
        oi_a_status="ok",
        oi_a_change=0.05,
        oi_c_status="ok",
        oi_c_change=0.05,
        baseline_price_change=0.02,
        terminal_return=0.01,
        long_mae=-0.01,
        long_mfe=0.02,
        basis_status="unverified_product_mapping",
    )
    c_md2 = ChildEvaluation(
        parent_article_id="p_mdate",
        symbol="SMD2",
        listing_regime="pre_market",
        is_complete=True,
        utc_date="2026-01-11",
        path_status="ok",
        oi_status="ok",
        oi_change=0.15,
        oi_b_status="ok",
        oi_b_change=0.15,
        oi_a_status="ok",
        oi_a_change=0.15,
        oi_c_status="ok",
        oi_c_change=0.15,
        baseline_price_change=0.04,
        terminal_return=0.03,
        long_mae=-0.02,
        long_mfe=0.04,
        basis_status="unverified_product_mapping",
    )

    all_children = [c1, c2, c3, c_even1, c_even2, c_inc_ok, c_inc_bad, c_bm1, c_bm2, c_md1, c_md2]
    csv_path, sha = _make_canonical_test_csv(tmp_path, all_children)
    raw_rows = load_snapshot(csv_path, expected_sha256=sha)

    panel = build_parent_panel(raw_rows)
    assert len(panel) > 0

    # Check p1 medians for Scenario B
    p1_b = [r for r in panel if r["parent_article_id"] == "p1" and r["scenario"] == "B"][0]
    assert p1_b["oi_complete"] is True
    assert p1_b["basis_complete"] is True
    assert p1_b["p"] == pytest.approx(0.3)
    assert p1_b["o"] == pytest.approx(0.6)
    assert p1_b["y"] == pytest.approx(0.3)
    assert p1_b["utc_date"] == "2026-05-01"

    # Check p_even even-number median: p=(0.1, 0.3) -> 0.2
    pe_b = [r for r in panel if r["parent_article_id"] == "p_even" and r["scenario"] == "B"][0]
    assert pe_b["oi_complete"] is True
    assert pe_b["p"] == pytest.approx(0.2)
    assert pe_b["o"] == pytest.approx(0.6)

    # Check p_inc: incomplete parent
    p_inc_b = [r for r in panel if r["parent_article_id"] == "p_inc" and r["scenario"] == "B"][0]
    assert p_inc_b["oi_complete"] is False
    assert p_inc_b["basis_complete"] is False
    assert p_inc_b["p"] is None
    assert p_inc_b["missing_reasons"] == "missing_jb_anchor_time"

    # Check p_bmiss: oi_complete True, basis_complete False
    p_bm_b = [r for r in panel if r["parent_article_id"] == "p_bmiss" and r["scenario"] == "B"][0]
    assert p_bm_b["oi_complete"] is True
    assert p_bm_b["basis_complete"] is False
    assert p_bm_b["p"] == pytest.approx(0.15)
    assert p_bm_b["b"] is None

    # Check p_mdate: multi-date conflict
    p_md_b = [r for r in panel if r["parent_article_id"] == "p_mdate" and r["scenario"] == "B"][0]
    assert p_md_b["utc_date"] == "multi_date_conflict:2026-01-10,2026-01-11"

    # Check conservation: in standard scenario B, total parent records = complete + incomplete
    std_b_records = [r for r in panel if r["listing_regime"] == "standard" and r["scenario"] == "B"]
    complete_count = sum(1 for r in std_b_records if r["oi_complete"])
    incomplete_count = sum(1 for r in std_b_records if not r["oi_complete"])
    assert complete_count + incomplete_count == len(std_b_records)
    # Distinct parents in standard: p1, p_even, p_inc, p_bmiss -> 4 parents
    assert len(std_b_records) == 4
    assert complete_count == 3
    assert incomplete_count == 1


def test_models_independent_affine_vector() -> None:
    """Task 2: Independent affine vectors for M0 and M1 OLS leave-one-out predictions."""
    p_vec = (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0)
    o_vec = (2.0, -1.0, 3.0, 0.0, -2.0, 1.0, 4.0, -3.0)

    # 1. Formula 1: y = 1 + 2*p (pure affine in p)
    # M0 and M1 should both predict y exactly on each holdout fold
    panel_f1: list[dict[str, Any]] = []
    for idx, (p_val, o_val) in enumerate(zip(p_vec, o_vec)):
        y_val = 1.0 + 2.0 * p_val
        panel_f1.append(
            {
                "parent_article_id": f"parent_{idx}",
                "listing_regime": "standard",
                "scenario": "B",
                "utc_date": "2026-05-01",
                "child_symbols": f"SYM_{idx}",
                "required_child_count": 1,
                "scenario_complete_child_count": 1,
                "oi_complete": True,
                "basis_complete": False,
                "missing_reasons": "",
                "p": p_val,
                "o": o_val,
                "b": None,
                "y": y_val,
                "long_mae": -0.02,
                "long_mfe": 0.05,
            }
        )

    folds_f1 = evaluate_comparisons(panel_f1)
    m1_vs_m0_folds = [
        f
        for f in folds_f1
        if f["listing_regime"] == "standard"
        and f["scenario"] == "B"
        and f["cohort"] == "oi_complete"
        and f["comparison"] == "M1_vs_M0"
    ]
    assert len(m1_vs_m0_folds) == 8
    for f in m1_vs_m0_folds:
        assert f["fold_status"] == "ok"
        assert f["pred_base"] == pytest.approx(f["actual_y"], abs=1e-8)
        assert f["pred_extended"] == pytest.approx(f["actual_y"], abs=1e-8)
        assert f["error_base"] == pytest.approx(0.0, abs=1e-8)
        assert f["error_extended"] == pytest.approx(0.0, abs=1e-8)
        assert f["d_i"] == pytest.approx(0.0, abs=1e-8)

    # 2. Formula 2: y = 1 + 2*p + 3*o + 4*p*o (exact M1 interaction formula)
    # M1 should predict y exactly on each holdout fold
    panel_f2: list[dict[str, Any]] = []
    for idx, (p_val, o_val) in enumerate(zip(p_vec, o_vec)):
        y_val = 1.0 + 2.0 * p_val + 3.0 * o_val + 4.0 * p_val * o_val
        panel_f2.append(
            {
                "parent_article_id": f"parent_{idx}",
                "listing_regime": "standard",
                "scenario": "B",
                "utc_date": "2026-05-01",
                "child_symbols": f"SYM_{idx}",
                "required_child_count": 1,
                "scenario_complete_child_count": 1,
                "oi_complete": True,
                "basis_complete": False,
                "missing_reasons": "",
                "p": p_val,
                "o": o_val,
                "b": None,
                "y": y_val,
                "long_mae": -0.02,
                "long_mfe": 0.05,
            }
        )

    folds_f2 = evaluate_comparisons(panel_f2)
    m1_f2_folds = [
        f
        for f in folds_f2
        if f["listing_regime"] == "standard"
        and f["scenario"] == "B"
        and f["cohort"] == "oi_complete"
        and f["comparison"] == "M1_vs_M0"
    ]
    assert len(m1_f2_folds) == 8
    for f in m1_f2_folds:
        assert f["fold_status"] == "ok"
        assert f["pred_extended"] == pytest.approx(f["actual_y"], abs=1e-8)
        assert f["error_extended"] == pytest.approx(0.0, abs=1e-8)


def test_models_independent_basis_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2: Independent basis vector for M2 leave-one-out predictions and M1 comparison."""
    import scripts.external_signal_shadow.run_launch_price_oi_basis_incremental_information as target_mod

    p_vec = (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0)
    o_vec = (2.0, -1.0, 3.0, 0.0, -2.0, 1.0, 4.0, -3.0)
    b_vec = (1.0, -2.0, 0.0, 4.0, -1.0, 2.0, 3.0, -3.0)
    # y = 1 + 2*p + 3*o + 4*p*o + 5*b
    # y = (-18, -8, -4, 21, -16, 26, 82, -63)
    y_known = (-18.0, -8.0, -4.0, 21.0, -16.0, 26.0, 82.0, -63.0)

    panel: list[dict[str, Any]] = []
    for idx, (p_val, o_val, b_val, y_val) in enumerate(zip(p_vec, o_vec, b_vec, y_known)):
        # verify formula
        assert y_val == (1.0 + 2.0 * p_val + 3.0 * o_val + 4.0 * p_val * o_val + 5.0 * b_val)
        panel.append(
            {
                "parent_article_id": f"parent_{idx}",
                "listing_regime": "standard",
                "scenario": "B",
                "utc_date": "2026-05-01",
                "child_symbols": f"SYM_{idx}",
                "required_child_count": 1,
                "scenario_complete_child_count": 1,
                "oi_complete": True,
                "basis_complete": True,
                "missing_reasons": "",
                "p": p_val,
                "o": o_val,
                "b": b_val,
                "y": y_val,
                "long_mae": -0.02,
                "long_mfe": 0.05,
            }
        )

    # Intercept calls to production _fit_and_predict_ols to observe actual design matrices and test vectors
    captured_ols_calls: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    orig_fit = target_mod._fit_and_predict_ols

    def _spy_fit(X_tr: np.ndarray, y_tr: np.ndarray, x_te: np.ndarray) -> Any:
        captured_ols_calls.append((X_tr.copy(), y_tr.copy(), x_te.copy()))
        return orig_fit(X_tr, y_tr, x_te)

    monkeypatch.setattr(target_mod, "_fit_and_predict_ols", _spy_fit)

    folds = evaluate_comparisons(panel)
    m2_folds = [
        f
        for f in folds
        if f["listing_regime"] == "standard"
        and f["scenario"] == "B"
        and f["cohort"] == "basis_complete"
        and f["comparison"] == "M2_vs_M1"
    ]
    assert len(m2_folds) == 8
    for f in m2_folds:
        assert f["fold_status"] == "ok"
        assert f["train_parent_count"] == 7
        assert f["pred_extended"] == pytest.approx(f["actual_y"], abs=1e-7)

    # Fourth fold (parent_3): (p, o, b, y) = (0, 0, 4, 21)
    f3 = [f for f in m2_folds if f["parent_article_id"] == "parent_3"][0]
    expected_m1_pred = -310243.0 / 384032.0
    assert f3["pred_base"] == pytest.approx(expected_m1_pred, abs=1e-5)
    expected_diff_sq = (21.0 - expected_m1_pred) ** 2
    assert f3["d_i"] == pytest.approx(expected_diff_sq, abs=1e-2)

    # Filter captured M2 calls (design matrix has 5 columns: 1, z_p, z_o, z_po, z_b)
    m2_calls = [c for c in captured_ols_calls if c[0].shape[1] == 5]
    assert len(m2_calls) == 8

    # Identify the exact call for fold 3 (parent_3, where holdout y=21.0 is omitted from training y)
    call_3 = [c for c in m2_calls if 21.0 not in c[1]][0]
    X_train_3, y_train_3, x_test_3 = call_3

    assert X_train_3.shape == (7, 5)
    assert x_test_3.shape == (5,)

    # Direct observation of production training standardization on basis column (index 4)
    z_b_train_prod = X_train_3[:, 4]
    assert float(np.mean(z_b_train_prod)) == pytest.approx(0.0, abs=1e-7)
    assert float(np.std(z_b_train_prod, ddof=0)) == pytest.approx(1.0, abs=1e-7)

    # Direct observation of production holdout vector: z_b_test must be 2.0 (strictly using training parameters)
    # (If standardization leaked holdout row b=4 into full sample, std would be 2.291288 and z_b_test would be ~1.5275)
    assert x_test_3[4] == pytest.approx(2.0, abs=1e-7)

    # Production OLS fit coefficients on actual X_train and y_train
    beta_m2_prod, _, _, _ = np.linalg.lstsq(X_train_3, y_train_3, rcond=None)
    assert beta_m2_prod[4] == pytest.approx(10.0, abs=1e-6)

    # Contribution of basis term in production prediction
    basis_term_contrib = beta_m2_prod[4] * x_test_3[4]
    assert basis_term_contrib == pytest.approx(20.0, abs=1e-6)


def test_fold_training_only_and_estimability() -> None:
    """Task 2: Verifies training parameters invariance to holdout row and estimability handling."""
    # 1. Test rank deficiency / zero variance handling
    panel_zero_var: list[dict[str, Any]] = []
    for idx in range(6):
        panel_zero_var.append(
            {
                "parent_article_id": f"p_zv_{idx}",
                "listing_regime": "standard",
                "scenario": "B",
                "utc_date": "2026-05-01",
                "child_symbols": f"S_{idx}",
                "required_child_count": 1,
                "scenario_complete_child_count": 1,
                "oi_complete": True,
                "basis_complete": False,
                "missing_reasons": "",
                "p": 1.0,  # Zero variance in p!
                "o": float(idx),
                "b": None,
                "y": 2.0 * idx,
                "long_mae": -0.01,
                "long_mfe": 0.02,
            }
        )
    folds_zv = evaluate_comparisons(panel_zero_var)
    m1_zv = [f for f in folds_zv if f["comparison"] == "M1_vs_M0"]
    assert len(m1_zv) == 6
    for f in m1_zv:
        assert f["fold_status"] == "not_estimable"
        assert f["pred_base"] is None
        assert f["d_i"] is None

    # 2. Test cross-regime holdout exclusion
    # Parent p_cross appears in both standard and pre_market
    panel_cross: list[dict[str, Any]] = []
    for idx in range(8):
        panel_cross.append(
            {
                "parent_article_id": f"p_std_{idx}",
                "listing_regime": "standard",
                "scenario": "B",
                "utc_date": "2026-05-01",
                "child_symbols": f"S_std_{idx}",
                "required_child_count": 1,
                "scenario_complete_child_count": 1,
                "oi_complete": True,
                "basis_complete": False,
                "missing_reasons": "",
                "p": float(idx),
                "o": float(idx * 2),
                "b": None,
                "y": float(idx * 3),
                "long_mae": -0.01,
                "long_mfe": 0.02,
            }
        )
    # Add p_cross to both regimes
    panel_cross.append(
        {
            "parent_article_id": "p_cross",
            "listing_regime": "standard",
            "scenario": "B",
            "utc_date": "2026-05-01",
            "child_symbols": "S_cross_std",
            "required_child_count": 1,
            "scenario_complete_child_count": 1,
            "oi_complete": True,
            "basis_complete": False,
            "missing_reasons": "",
            "p": 8.0,
            "o": 16.0,
            "b": None,
            "y": 24.0,
            "long_mae": -0.01,
            "long_mfe": 0.02,
        }
    )
    panel_cross.append(
        {
            "parent_article_id": "p_cross",
            "listing_regime": "pre_market",
            "scenario": "B",
            "utc_date": "2026-05-01",
            "child_symbols": "S_cross_pm",
            "required_child_count": 1,
            "scenario_complete_child_count": 1,
            "oi_complete": True,
            "basis_complete": False,
            "missing_reasons": "",
            "p": 5.0,
            "o": 10.0,
            "b": None,
            "y": 15.0,
            "long_mae": -0.01,
            "long_mfe": 0.02,
        }
    )
    folds_cross = evaluate_comparisons(panel_cross)
    f_cross_std = [
        f
        for f in folds_cross
        if f["listing_regime"] == "standard"
        and f["parent_article_id"] == "p_cross"
        and f["comparison"] == "M1_vs_M0"
    ][0]
    # In standard, there are 8 other parents
    assert f_cross_std["train_parent_count"] == 8

    # 3. Changing holdout y must NOT change its prediction
    pred_orig = f_cross_std["pred_base"]

    # Clone panel and mutate p_cross's y to 999.0
    panel_y_test2: list[dict[str, Any]] = []
    for r in panel_cross:
        r_clone = dict(r)
        if r_clone["parent_article_id"] == "p_cross" and r_clone["listing_regime"] == "standard":
            r_clone["y"] = 999.0
        panel_y_test2.append(r_clone)

    folds_mut_y = evaluate_comparisons(panel_y_test2)
    f_mut_std = [
        f
        for f in folds_mut_y
        if f["listing_regime"] == "standard"
        and f["parent_article_id"] == "p_cross"
        and f["comparison"] == "M1_vs_M0"
    ][0]
    assert f_mut_std["pred_base"] == pytest.approx(pred_orig, abs=1e-9)


def test_cohort_keys_and_basis_pairing() -> None:
    """Task 2: Verifies unique fold keys and proper M2/M1 cohort pairing."""
    panel: list[dict[str, Any]] = []
    for idx in range(10):
        b_val = float(idx * 0.001) if idx < 8 else None
        panel.append(
            {
                "parent_article_id": f"parent_{idx}",
                "listing_regime": "standard",
                "scenario": "B",
                "utc_date": "2026-05-01",
                "child_symbols": f"SYM_{idx}",
                "required_child_count": 1,
                "scenario_complete_child_count": 1,
                "oi_complete": True,
                "basis_complete": (idx < 8),
                "missing_reasons": "" if idx < 8 else "unverified_product_mapping",
                "p": float(idx) * 0.1,
                "o": float(idx) * 0.2,
                "b": b_val,
                "y": float(idx) * 0.05,
                "long_mae": -0.01,
                "long_mfe": 0.02,
            }
        )

    folds = evaluate_comparisons(panel)
    assert len(folds) > 0

    # Verify unique 5-tuple keys: (regime, scenario, cohort, comparison, parent_article_id)
    seen_keys: set[tuple[str, str, str, str, str]] = set()
    for f in folds:
        k = (
            f["listing_regime"],
            f["scenario"],
            f["cohort"],
            f["comparison"],
            f["parent_article_id"],
        )
        assert k not in seen_keys, f"Collision on key {k}"
        seen_keys.add(k)

    # In Scenario B standard:
    # oi_complete M1_vs_M0 has 10 folds
    b_oi_folds = [
        f
        for f in folds
        if f["listing_regime"] == "standard"
        and f["scenario"] == "B"
        and f["cohort"] == "oi_complete"
        and f["comparison"] == "M1_vs_M0"
    ]
    assert len(b_oi_folds) == 10

    # basis_complete M1_vs_M0 has 8 folds
    b_basis_m1_folds = [
        f
        for f in folds
        if f["listing_regime"] == "standard"
        and f["scenario"] == "B"
        and f["cohort"] == "basis_complete"
        and f["comparison"] == "M1_vs_M0"
    ]
    assert len(b_basis_m1_folds) == 8

    # basis_complete M2_vs_M1 has 8 folds
    b_basis_m2_folds = [
        f
        for f in folds
        if f["listing_regime"] == "standard"
        and f["scenario"] == "B"
        and f["cohort"] == "basis_complete"
        and f["comparison"] == "M2_vs_M1"
    ]
    assert len(b_basis_m2_folds) == 8

    # Confirm M2 is NOT evaluated on oi_complete cohort
    m2_oi_folds = [f for f in folds if f["cohort"] == "oi_complete" and "M2" in f["comparison"]]
    assert len(m2_oi_folds) == 0


def test_summary_independent_error_contributions() -> None:
    """Task 2: Independent error vectors for summarize diagnostics and fixed-fold sensitivity."""
    # Synthetic folds: error_M0 = (1, 2, 3), error_M1 = (0, 1, 2)
    # d_i = (1^2 - 0^2, 2^2 - 1^2, 3^2 - 2^2) = (1, 3, 5)
    # mean(d_i) = 3.0
    # excluding 0: mean(3, 5) = 4.0
    # excluding 1: mean(1, 5) = 3.0
    # excluding 2: mean(1, 3) = 2.0
    # sensitivity range: [2.0, 4.0]
    dummy_panel: list[dict[str, Any]] = [
        {
            "parent_article_id": f"p_{i}",
            "listing_regime": "standard",
            "scenario": "B",
            "utc_date": "2026-05-01",
            "child_symbols": f"S_{i}",
            "required_child_count": 1,
            "scenario_complete_child_count": 1,
            "oi_complete": True,
            "basis_complete": False,
            "missing_reasons": "",
            "p": float(i),
            "o": float(i),
            "b": None,
            "y": float(i),
            "long_mae": -0.01 * (i + 1),
            "long_mfe": 0.02 * (i + 1),
        }
        for i in range(3)
    ]

    dummy_folds: list[dict[str, Any]] = [
        {
            "listing_regime": "standard",
            "scenario": "B",
            "cohort": "oi_complete",
            "comparison": "M1_vs_M0",
            "parent_article_id": "p_0",
            "fold_status": "ok",
            "train_parent_count": 2,
            "actual_y": 0.0,
            "pred_base": 1.0,
            "pred_extended": 0.0,
            "error_base": 1.0,
            "error_extended": 0.0,
            "d_i": 1.0,
        },
        {
            "listing_regime": "standard",
            "scenario": "B",
            "cohort": "oi_complete",
            "comparison": "M1_vs_M0",
            "parent_article_id": "p_1",
            "fold_status": "ok",
            "train_parent_count": 2,
            "actual_y": 1.0,
            "pred_base": 3.0,
            "pred_extended": 2.0,
            "error_base": 2.0,
            "error_extended": 1.0,
            "d_i": 3.0,
        },
        {
            "listing_regime": "standard",
            "scenario": "B",
            "cohort": "oi_complete",
            "comparison": "M1_vs_M0",
            "parent_article_id": "p_2",
            "fold_status": "ok",
            "train_parent_count": 2,
            "actual_y": 2.0,
            "pred_base": 5.0,
            "pred_extended": 4.0,
            "error_base": 3.0,
            "error_extended": 2.0,
            "d_i": 5.0,
        },
    ]

    summary = summarize(dummy_panel, dummy_folds)
    key = ("standard", "B", "oi_complete", "M1_vs_M0")
    assert key in summary["comparisons"]
    comp = summary["comparisons"][key]

    assert comp["all_estimable"] is True
    assert comp["mean_d_i"] == pytest.approx(3.0)
    assert comp["mse_base"] == pytest.approx((1.0 + 4.0 + 9.0) / 3.0)
    assert comp["mse_extended"] == pytest.approx((0.0 + 1.0 + 4.0) / 3.0)
    assert comp["median_abs_error_base"] == pytest.approx(2.0)
    assert comp["median_abs_error_extended"] == pytest.approx(1.0)

    # Sensitivity range [2.0, 4.0]
    sens_range = comp["sensitivity_mean_d_i_range"]
    assert sens_range[0] == pytest.approx(2.0)
    assert sens_range[1] == pytest.approx(4.0)

    # Top positive contributions: p_2 (5.0), p_1 (3.0), p_0 (1.0)
    top_contrib = comp["top_positive_contributions"]
    assert len(top_contrib) == 3
    assert top_contrib[0]["parent_article_id"] == "p_2"
    assert top_contrib[0]["d_i"] == pytest.approx(5.0)
    assert top_contrib[1]["parent_article_id"] == "p_1"
    assert top_contrib[1]["d_i"] == pytest.approx(3.0)

    # M2_vs_M1 synthetic folds: error_M1 = (0, 1, 2), error_M2 = (0, 0, 1) -> d_i = (0, 1, 3), mean = 4/3
    dummy_folds_m2: list[dict[str, Any]] = [
        {
            "listing_regime": "standard",
            "scenario": "B",
            "cohort": "basis_complete",
            "comparison": "M2_vs_M1",
            "parent_article_id": "p_0",
            "fold_status": "ok",
            "train_parent_count": 2,
            "actual_y": 0.0,
            "pred_base": 0.0,
            "pred_extended": 0.0,
            "error_base": 0.0,
            "error_extended": 0.0,
            "d_i": 0.0,
        },
        {
            "listing_regime": "standard",
            "scenario": "B",
            "cohort": "basis_complete",
            "comparison": "M2_vs_M1",
            "parent_article_id": "p_1",
            "fold_status": "ok",
            "train_parent_count": 2,
            "actual_y": 1.0,
            "pred_base": 2.0,
            "pred_extended": 1.0,
            "error_base": 1.0,
            "error_extended": 0.0,
            "d_i": 1.0,
        },
        {
            "listing_regime": "standard",
            "scenario": "B",
            "cohort": "basis_complete",
            "comparison": "M2_vs_M1",
            "parent_article_id": "p_2",
            "fold_status": "ok",
            "train_parent_count": 2,
            "actual_y": 2.0,
            "pred_base": 4.0,
            "pred_extended": 3.0,
            "error_base": 2.0,
            "error_extended": 1.0,
            "d_i": 3.0,
        },
    ]
    summary_m2 = summarize(dummy_panel, dummy_folds_m2)
    key_m2 = ("standard", "B", "basis_complete", "M2_vs_M1")
    assert key_m2 in summary_m2["comparisons"]
    comp_m2 = summary_m2["comparisons"][key_m2]
    assert comp_m2["mean_d_i"] == pytest.approx(4.0 / 3.0)

    # When one fold is not_estimable:
    dummy_folds_not_est = list(dummy_folds)
    dummy_folds_not_est[0] = dict(dummy_folds_not_est[0])
    dummy_folds_not_est[0]["fold_status"] = "not_estimable"
    dummy_folds_not_est[0]["d_i"] = None

    summary_ne = summarize(dummy_panel, dummy_folds_not_est)
    comp_ne = summary_ne["comparisons"][key]
    assert comp_ne["all_estimable"] is False
    assert comp_ne["mean_d_i"] is None


def test_cli_denies_before_snapshot_read(tmp_path: Path) -> None:
    """Task 3: Verifies CLI denies bad/missing auth, bad paths, or invalid flags before reading snapshot."""
    # 1. Missing args
    assert main([]) != 0
    assert main(["--auth-file", "nonexistent.json"]) != 0
    assert main(["--auth-file", "foo.json", "--output-dir", "bar", "--extra"]) != 0

    # 2. Non-existent auth file
    out_dir = tmp_path / "out_1"
    assert main(["--auth-file", str(tmp_path / "missing_auth.json"), "--output-dir", str(out_dir)]) != 0
    assert not out_dir.exists()

    # 3. Invalid JSON in auth file
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("not json", encoding="utf-8")
    assert main(["--auth-file", str(bad_json), "--output-dir", str(out_dir)]) != 0
    assert not out_dir.exists()

    # Base valid auth template
    valid_auth = {
        "operation": "offline_research_once",
        "design_relative_path": "docs/designs/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-design_CN.md",
        "design_sha256": "f38fd9c4609a52cc9d2d6529cceabca35c778e84c374fad4e386029d0493519e",
        "plan_relative_path": "docs/plans/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-implementation-plan_CN.md",
        "plan_sha256": "fe8dc877323f91725773502eaf606822350f47ed703fc484c5d199e5265fda6f",
        "input_csv_path": "/private/tmp/launch_open_interest_basis_exploratory_run_20261103/child_rows.csv",
        "input_csv_sha256": "56afc76bc30dea5b8d0414e320e2d49842ed3b137c4e0bf37c6dca51ce9447c4",
        "input_review_path": "/private/tmp/launch_open_interest_basis_exploratory_run_20261103/review_CN.md",
        "input_review_sha256": "af4e277728cdabbb5cb4c8e9abf0da6722b001470a66a6c256034e67cc6104dd",
        "output_dir": str(out_dir.resolve()),
        "allowed_actions": ["snapshot_validation", "research_run"],
        "network_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_allowed": False,
        "signal_allowed": False,
    }

    # Helper to test invalid auth dict
    def assert_auth_rejected(auth_data: dict[str, Any], tag: str) -> None:
        p = tmp_path / f"auth_{tag}.json"
        p.write_text(json.dumps(auth_data), encoding="utf-8")
        target_out = tmp_path / f"out_{tag}"
        rc = main(["--auth-file", str(p), "--output-dir", str(target_out)])
        assert rc != 0, f"Expected rejection for {tag}, got {rc}"
        assert not target_out.exists(), f"Output dir {target_out} created on rejection for {tag}"

    # 4. Missing required fields
    for field in list(valid_auth.keys()):
        bad_auth = dict(valid_auth)
        del bad_auth[field]
        assert_auth_rejected(bad_auth, f"missing_{field}")

    # 5. Invalid operation
    bad_op = dict(valid_auth, operation="live_trading")
    assert_auth_rejected(bad_op, "bad_op")

    # 6. Mismatched design SHA / plan SHA
    bad_d_sha = dict(valid_auth, design_sha256="0" * 64)
    assert_auth_rejected(bad_d_sha, "bad_design_sha")
    bad_p_sha = dict(valid_auth, plan_sha256="0" * 64)
    assert_auth_rejected(bad_p_sha, "bad_plan_sha")

    # 7. Non-boolean or True forbidden permissions
    for flag in [
        "network_allowed",
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_allowed",
        "signal_allowed",
    ]:
        assert_auth_rejected(dict(valid_auth, **{flag: True}), f"{flag}_true")
        assert_auth_rejected(dict(valid_auth, **{flag: "false"}), f"{flag}_str")
        assert_auth_rejected(dict(valid_auth, **{flag: 0}), f"{flag}_int")

    # 8. allowed_actions checks
    assert_auth_rejected(dict(valid_auth, allowed_actions=[]), "empty_actions")
    assert_auth_rejected(dict(valid_auth, allowed_actions=["snapshot_validation"]), "no_research_run")
    assert_auth_rejected(dict(valid_auth, allowed_actions=["unknown_action"]), "unknown_action")
    assert_auth_rejected(dict(valid_auth, allowed_actions=["research_run", "research_run"]), "duplicate_action")

    # 9. Actual Design/Plan file on disk tampered / mismatched
    fake_design = tmp_path / "fake_design.md"
    fake_design.write_text("tampered content", encoding="utf-8")
    assert_auth_rejected(
        dict(valid_auth, design_relative_path=str(fake_design)),
        "tampered_design_file",
    )


def test_cli_output_isolation_and_partial_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 3: Output isolation, path safety, and fail-closed handling."""
    input_dir = tmp_path / "mock_inputs"
    input_dir.mkdir()
    fake_csv = input_dir / "child_rows.csv"
    fake_csv.write_text("dummy", encoding="utf-8")
    fake_csv_sha = hashlib.sha256(fake_csv.read_bytes()).hexdigest()

    fake_review = input_dir / "review_CN.md"
    fake_review.write_text("# Review", encoding="utf-8")
    fake_review_sha = hashlib.sha256(fake_review.read_bytes()).hexdigest()

    output_root = tmp_path / "mock_outputs"
    output_root.mkdir()
    exist_dir = output_root / "exist_dir"
    exist_dir.mkdir()

    import scripts.external_signal_shadow.run_launch_price_oi_basis_incremental_information as target_mod

    monkeypatch.setattr(target_mod, "FIXED_INPUT_CSV_PATH", fake_csv)
    monkeypatch.setattr(target_mod, "FIXED_INPUT_CSV_SHA256", fake_csv_sha)
    monkeypatch.setattr(target_mod, "FIXED_INPUT_REVIEW_PATH", fake_review)
    monkeypatch.setattr(target_mod, "FIXED_INPUT_REVIEW_SHA256", fake_review_sha)

    # Output dir already exists
    auth_exist = tmp_path / "auth_exist.json"
    auth_exist.write_text(
        json.dumps({
            "operation": "offline_research_once",
            "design_relative_path": "docs/designs/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-design_CN.md",
            "design_sha256": "f38fd9c4609a52cc9d2d6529cceabca35c778e84c374fad4e386029d0493519e",
            "plan_relative_path": "docs/plans/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-implementation-plan_CN.md",
            "plan_sha256": "fe8dc877323f91725773502eaf606822350f47ed703fc484c5d199e5265fda6f",
            "input_csv_path": str(fake_csv.resolve()),
            "input_csv_sha256": fake_csv_sha,
            "input_review_path": str(fake_review.resolve()),
            "input_review_sha256": fake_review_sha,
            "output_dir": str(exist_dir.resolve()),
            "allowed_actions": ["research_run"],
            "network_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_allowed": False,
            "signal_allowed": False,
        }),
        encoding="utf-8",
    )
    assert target_mod.main(["--auth-file", str(auth_exist), "--output-dir", str(exist_dir)]) != 0

    # 2. Output collision with input directory
    auth_col = tmp_path / "auth_col.json"
    auth_col.write_text(
        json.dumps({
            **json.loads(auth_exist.read_text(encoding="utf-8")),
            "output_dir": str(input_dir.resolve()),
        }),
        encoding="utf-8",
    )
    assert target_mod.main(["--auth-file", str(auth_col), "--output-dir", str(input_dir)]) != 0

    # 3. CSV hash mismatch rejection before modeling
    bad_csv_out = output_root / "out_bad_csv"
    auth_bad_csv = tmp_path / "auth_bad_csv.json"
    auth_bad_csv.write_text(
        json.dumps({
            **json.loads(auth_exist.read_text(encoding="utf-8")),
            "input_csv_sha256": "0" * 64,
            "output_dir": str(bad_csv_out.resolve()),
        }),
        encoding="utf-8",
    )
    assert target_mod.main(["--auth-file", str(auth_bad_csv), "--output-dir", str(bad_csv_out)]) != 0
    assert not bad_csv_out.exists()

    # 4. Review hash mismatch rejection
    bad_rev_out = output_root / "out_bad_rev"
    auth_bad_rev = tmp_path / "auth_bad_rev.json"
    auth_bad_rev.write_text(
        json.dumps({
            **json.loads(auth_exist.read_text(encoding="utf-8")),
            "input_review_sha256": "0" * 64,
            "output_dir": str(bad_rev_out.resolve()),
        }),
        encoding="utf-8",
    )
    assert target_mod.main(["--auth-file", str(auth_bad_rev), "--output-dir", str(bad_rev_out)]) != 0
    assert not bad_rev_out.exists()


def test_cli_canonical_csv_to_all_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 3: End-to-end execution from canonical writer to all three artifacts via main()."""
    p_vec = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, -1.5, 2.5]
    o_vec = [2.0, -1.0, 3.0, 0.0, -2.0, 1.0, 4.0, -3.0, 1.5, -2.5]
    b_vec = [1.0, -2.0, 0.0, 4.0, -1.0, 2.0, 3.0, -3.0, None, None]
    y_known = [
        1.0 + 2.0 * p + 3.0 * o + 4.0 * p * o + (5.0 * b if b is not None else 0.0)
        for p, o, b in zip(p_vec, o_vec, b_vec)
    ]
    dates = [
        "2026-05-01",
        "2026-05-01",
        "2026-05-01",
        "2026-05-01",
        "2026-05-01",
        "2026-05-02",
        "2026-05-02",
        "2026-05-03",
        "2026-05-03",
        "2026-05-04",
    ]

    children: list[ChildEvaluation] = []
    for idx in range(10):
        b_val = b_vec[idx]
        b_st = "ok" if b_val is not None else "unverified_product_mapping"
        children.append(
            ChildEvaluation(
                parent_article_id=f"parent_{idx}",
                symbol=f"SYM_{idx}",
                listing_regime="standard",
                is_complete=True,
                utc_date=dates[idx],
                path_status="ok",
                oi_status="ok",
                oi_change=o_vec[idx],
                oi_b_status="ok",
                oi_b_change=o_vec[idx],
                oi_a_status="ok",
                oi_a_change=o_vec[idx],
                oi_c_status="ok",
                oi_c_change=o_vec[idx],
                baseline_price_change=p_vec[idx],
                terminal_return=y_known[idx],
                long_mae=-0.01 * (idx + 1),
                long_mfe=0.04 * (idx + 1),
                basis=b_val,
                basis_status=b_st,
            )
        )
    children.append(
        ChildEvaluation(
            parent_article_id="parent_inc",
            symbol="SYM_INC",
            listing_regime="standard",
            is_complete=False,
            utc_date=None,
            missing_reason="missing_jb_anchor_time",
            path_status="missing_jb_anchor_time",
            oi_status="missing_jb_anchor_time",
            oi_change=None,
            oi_b_status="missing_jb_anchor_time",
            oi_b_change=None,
            oi_a_status="missing_jb_anchor_time",
            oi_a_change=None,
            oi_c_status="missing_jb_anchor_time",
            oi_c_change=None,
            baseline_price_change=None,
            terminal_return=None,
            long_mae=None,
            long_mfe=None,
            basis=None,
            basis_status="",
        )
    )

    input_container = tmp_path / "test_inputs"
    input_container.mkdir()
    csv_path, csv_sha = _make_canonical_test_csv(input_container, children)
    review_path = input_container / "input_review.md"
    review_path.write_text("# Input Review Placeholder\n", encoding="utf-8")
    review_sha = hashlib.sha256(review_path.read_bytes()).hexdigest()

    import scripts.external_signal_shadow.run_launch_price_oi_basis_incremental_information as target_mod

    monkeypatch.setattr(target_mod, "FIXED_INPUT_CSV_PATH", csv_path)
    monkeypatch.setattr(target_mod, "FIXED_INPUT_CSV_SHA256", csv_sha)
    monkeypatch.setattr(target_mod, "FIXED_INPUT_REVIEW_PATH", review_path)
    monkeypatch.setattr(target_mod, "FIXED_INPUT_REVIEW_SHA256", review_sha)

    output_container = tmp_path / "test_outputs"
    output_container.mkdir()
    out_dir = output_container / "actual_out"
    auth_file = tmp_path / "auth_valid.json"
    auth_data = {
        "operation": "offline_research_once",
        "design_relative_path": "docs/designs/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-design_CN.md",
        "design_sha256": "f38fd9c4609a52cc9d2d6529cceabca35c778e84c374fad4e386029d0493519e",
        "plan_relative_path": "docs/plans/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-implementation-plan_CN.md",
        "plan_sha256": "fe8dc877323f91725773502eaf606822350f47ed703fc484c5d199e5265fda6f",
        "input_csv_path": str(csv_path.resolve()),
        "input_csv_sha256": csv_sha,
        "input_review_path": str(review_path.resolve()),
        "input_review_sha256": review_sha,
        "output_dir": str(out_dir.resolve()),
        "allowed_actions": ["snapshot_validation", "research_run"],
        "network_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_allowed": False,
        "signal_allowed": False,
    }
    auth_file.write_text(json.dumps(auth_data), encoding="utf-8")

    rc = target_mod.main(["--auth-file", str(auth_file), "--output-dir", str(out_dir)])
    assert rc == 0

    panel_file = out_dir / "parent_panel.csv"
    diag_file = out_dir / "fold_diagnostics.csv"
    report_file = out_dir / "review_CN.md"
    assert panel_file.is_file()
    assert diag_file.is_file()
    assert report_file.is_file()

    panel_text = panel_file.read_text(encoding="utf-8")
    assert "parent_article_id,listing_regime,scenario,utc_date" in panel_text
    assert "parent_inc" in panel_text

    diag_text = diag_file.read_text(encoding="utf-8")
    assert "listing_regime,scenario,cohort,comparison,parent_article_id" in diag_text
    assert "M1_vs_M0" in diag_text

    # Verify actual non-collinear numeric wiring in fold_diagnostics.csv
    with open(diag_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        diag_rows = list(reader)

    ok_folds = [r for r in diag_rows if r["fold_status"] == "ok"]
    assert len(ok_folds) > 0

    # Specifically check parent_3 in M2_vs_M1 on basis_complete cohort
    f3_m2 = [
        r
        for r in ok_folds
        if r["parent_article_id"] == "parent_3"
        and r["comparison"] == "M2_vs_M1"
        and r["cohort"] == "basis_complete"
    ]
    assert len(f3_m2) == 1
    assert float(f3_m2[0]["actual_y"]) == pytest.approx(21.0)
    assert float(f3_m2[0]["pred_extended"]) == pytest.approx(21.0, abs=1e-5)
    expected_m1_base = -310243.0 / 384032.0
    assert float(f3_m2[0]["pred_base"]) == pytest.approx(expected_m1_base, abs=1e-5)
    expected_diff_sq = (21.0 - expected_m1_base) ** 2
    assert float(f3_m2[0]["d_i"]) == pytest.approx(expected_diff_sq, abs=1e-2)

    report_text = report_file.read_text(encoding="utf-8")
    assert "exploratory / historical_scenario_only / no_alpha_claim" in report_text
    assert "分析代码 SHA-256：" in report_text
    assert "### 跨情景样本交集统计" in report_text
    assert "### UTC 日期分布与集中度诊断" in report_text
    assert "EXECUTION_SUCCESSFUL" in report_text
    assert report_text.strip().endswith("EXECUTION_SUCCESSFUL")


def test_authorized_exact_snapshot_contract() -> None:
    """Task 3: Verifies authorized exact snapshot contract against Design §2 without running research."""
    auth_env = os.environ.get("PRICE_OI_BASIS_SNAPSHOT_VALIDATION_AUTH_FILE")
    if not auth_env:
        pytest.skip("snapshot_validation_not_authorized")

    auth_path = Path(auth_env)
    assert auth_path.is_file(), f"Auth file does not exist: {auth_path}"
    auth_data = json.loads(auth_path.read_text(encoding="utf-8"))

    import scripts.external_signal_shadow.run_launch_price_oi_basis_incremental_information as target_mod

    # Strictly validate authorization for snapshot_validation action
    target_mod.validate_authorization(auth_data, required_action="snapshot_validation")

    # Verify input CSV contract
    csv_path = Path(auth_data["input_csv_path"])
    expected_csv_sha = auth_data["input_csv_sha256"]
    rows = load_snapshot(csv_path, expected_sha256=expected_csv_sha)
    assert len(rows) == 71
    complete_count = sum(1 for r in rows if r["path_status"] == "ok")
    missing_count = sum(1 for r in rows if r["path_status"] == "missing_jb_anchor_time")
    assert complete_count == 69
    assert missing_count == 2

    # Verify input review contract
    rev_path = Path(auth_data["input_review_path"])
    assert rev_path.is_file(), f"Input review file not found: {rev_path}"
    assert _compute_sha256(rev_path) == auth_data["input_review_sha256"]


def test_authorized_exact_snapshot_contract_fails_on_bad_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 3: Verifies authorized exact snapshot contract fails (not skip) when auth is invalid."""
    bad_auth = tmp_path / "bad_auth.json"
    bad_auth.write_text(json.dumps({"operation": "bad"}), encoding="utf-8")
    monkeypatch.setenv("PRICE_OI_BASIS_SNAPSHOT_VALIDATION_AUTH_FILE", str(bad_auth))

    with pytest.raises(IncrementalAnalysisError):
        test_authorized_exact_snapshot_contract()
