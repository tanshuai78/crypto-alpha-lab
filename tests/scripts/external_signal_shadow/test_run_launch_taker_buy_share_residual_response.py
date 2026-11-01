"""Tests for CLI authorization gates, bounded streaming, tamper rejection, and report conservation.

The first six tests use synthetic inputs and fault injection in tmp_path per L1 Rule 15.
The last two tests (test_canonical_upstream_positive and test_canonical_single_mutation_rejected)
require real upstream closure-audited archives and an explicit single-run authorization; they skip
when single-run authorization is absent.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import zipfile
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from research.external_signal_shadow.launch_taker_buy_share_residual_response import (
    AggTradeRecord,
    ChildResidualResponseResult,
    TakerBuyShareResearchError,
    evaluate_child_residual_response,
    stream_and_evaluate_admitted_child,
    verify_v2_ledger_and_select_universe,
    write_exploratory_outputs,
)
from scripts.external_signal_shadow.run_launch_taker_buy_share_residual_response import (
    FIXED_EXPLORATORY_PROTOCOL,
    main,
)

EXPECTED_DESIGN_REL = "docs/designs/2026-10-31-launch-taker-buy-share-residual-response-exploratory-design_CN.md"
EXPECTED_DESIGN_SHA = "5c05cb304da482bf5c29c0f98938795e11949b4130149474b6f8842175684896"
EXPECTED_PLAN_REL = "docs/plans/2026-10-31-launch-taker-buy-share-residual-response-exploratory-implementation-plan_CN.md"
EXPECTED_PLAN_SHA = "e644e9dfa25a063884ccf98cf23539e8fece485c6dca7fd2a03278f243bc240d"
EXPECTED_JA_REL = (
    "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/"
    "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
)
EXPECTED_JB_REL = (
    "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/"
    "stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"
)
EXPECTED_LEDGER_REL = "data/exports/stage1_5j_token_launch_classification_ledger_v2.csv"
EXPECTED_LEDGER_SHA = "36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b"


def _make_valid_auth_dict(output_dir: Path) -> dict[str, Any]:
    return {
        "design_relative_path": EXPECTED_DESIGN_REL,
        "design_sha256": EXPECTED_DESIGN_SHA,
        "plan_relative_path": EXPECTED_PLAN_REL,
        "plan_sha256": EXPECTED_PLAN_SHA,
        "ja_root_relative_path": EXPECTED_JA_REL,
        "jb_root_relative_path": EXPECTED_JB_REL,
        "ledger_relative_path": EXPECTED_LEDGER_REL,
        "ledger_sha256": EXPECTED_LEDGER_SHA,
        "output_dir": str(output_dir),
        "operation": "offline_research_once",
        "network_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_allowed": False,
        "signal_allowed": False,
    }


def _build_synthetic_zip_package(
    ja_root: Path,
    parent_id: str,
    symbol: str,
    utc_date: str,
    csv_lines: list[str],
    zip_req_id: int = 1,
    chk_req_id: int = 2,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Create a synthetic ZIP + CHECKSUM in tmp_path ja_root for unit/fault testing."""
    zip_rel = f"raw/archive/{symbol}/{symbol}-aggTrades-{utc_date}.zip"
    chk_rel = f"{zip_rel}.CHECKSUM"
    zip_path = ja_root / zip_rel
    chk_path = ja_root / chk_rel
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    csv_content = "\n".join(csv_lines) + "\n"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(f"{symbol}-aggTrades-{utc_date}.csv", csv_content.encode("utf-8"))

    zip_bytes = zip_path.read_bytes()
    zip_sha = hashlib.sha256(zip_bytes).hexdigest()
    chk_bytes = f"{zip_sha}  {zip_path.name}\n".encode("utf-8")
    chk_path.write_bytes(chk_bytes)
    chk_sha = hashlib.sha256(chk_bytes).hexdigest()

    pkg_record = {
        "parent_article_id": parent_id,
        "symbol": symbol,
        "utc_date": utc_date,
        "child_state": "archive_verified_with_post_launch_rows",
        "logical_archive_identity": {
            "market": "futures_um",
            "metric": "aggTrades",
            "parent_article_id": parent_id,
            "symbol": symbol,
            "utc_date": utc_date,
        },
        "zip_request_id": zip_req_id,
        "checksum_request_id": chk_req_id,
    }
    req_records = [
        {
            "request_id": zip_req_id,
            "request_kind": "archive",
            "request_state": "response_persisted",
            "response_relative_path": zip_rel,
            "response_sha256": zip_sha,
            "response_bytes": len(zip_bytes),
        },
        {
            "request_id": chk_req_id,
            "request_kind": "checksum",
            "request_state": "response_persisted",
            "response_relative_path": chk_rel,
            "response_sha256": chk_sha,
            "response_bytes": len(chk_bytes),
        },
    ]
    manifest_artifacts = [
        {"relative_path": zip_rel, "sha256": zip_sha, "byte_count": len(zip_bytes)},
        {"relative_path": chk_rel, "sha256": chk_sha, "byte_count": len(chk_bytes)},
    ]
    return pkg_record, req_records, manifest_artifacts


def test_authorization_denied_before_loader(tmp_path: Path) -> None:
    """Verify CLI rejects missing or invalid single-run authorization BEFORE calling any loader."""
    loader_calls = {"ja": 0, "jb": 0}

    def fake_ja_loader(_p: Path) -> dict[str, Any]:
        loader_calls["ja"] += 1
        return {}

    def fake_jb_loader(_p: Path) -> dict[str, Any]:
        loader_calls["jb"] += 1
        return {}

    out_dir = tmp_path / "out_1"

    # 1. No args / missing auth file
    rc_no_args = main([], ja_loader=fake_ja_loader, jb_loader=fake_jb_loader)
    assert rc_no_args != 0
    assert loader_calls == {"ja": 0, "jb": 0}

    missing_auth = tmp_path / "missing_auth.json"
    rc_missing = main(
        ["--auth-file", str(missing_auth), "--output-dir", str(out_dir)],
        ja_loader=fake_ja_loader,
        jb_loader=fake_jb_loader,
    )
    assert rc_missing != 0
    assert loader_calls == {"ja": 0, "jb": 0}

    # 2. Wrong Plan SHA
    bad_sha_auth = _make_valid_auth_dict(out_dir)
    bad_sha_auth["plan_sha256"] = "0" * 64
    auth_p = tmp_path / "bad_sha.json"
    auth_p.write_text(json.dumps(bad_sha_auth), encoding="utf-8")
    rc_bad_sha = main(
        ["--auth-file", str(auth_p), "--output-dir", str(out_dir)],
        ja_loader=fake_ja_loader,
        jb_loader=fake_jb_loader,
    )
    assert rc_bad_sha != 0
    assert loader_calls == {"ja": 0, "jb": 0}

    # 3. Wrong operation or reused J-C release field
    bad_op_auth = _make_valid_auth_dict(out_dir)
    bad_op_auth["operation"] = "offline_time_path_diagnostic_once"
    auth_p.write_text(json.dumps(bad_op_auth), encoding="utf-8")
    assert main(["--auth-file", str(auth_p), "--output-dir", str(out_dir)], ja_loader=fake_ja_loader, jb_loader=fake_jb_loader) != 0
    assert loader_calls == {"ja": 0, "jb": 0}

    reused_release_auth = _make_valid_auth_dict(out_dir)
    reused_release_auth["release_state"] = "released"
    auth_p.write_text(json.dumps(reused_release_auth), encoding="utf-8")
    assert main(["--auth-file", str(auth_p), "--output-dir", str(out_dir)], ja_loader=fake_ja_loader, jb_loader=fake_jb_loader) != 0
    assert loader_calls == {"ja": 0, "jb": 0}

    # 4. Forbidden permission flag set to True
    for flag in ("network_allowed", "paper_trading_allowed", "live_trading_allowed", "execution_allowed", "signal_allowed"):
        bad_flag_auth = _make_valid_auth_dict(out_dir)
        bad_flag_auth[flag] = True
        auth_p.write_text(json.dumps(bad_flag_auth), encoding="utf-8")
        assert main(["--auth-file", str(auth_p), "--output-dir", str(out_dir)], ja_loader=fake_ja_loader, jb_loader=fake_jb_loader) != 0
        assert loader_calls == {"ja": 0, "jb": 0}
        assert not out_dir.exists()


def test_output_collision_and_no_false_success(tmp_path: Path) -> None:
    """Verify existing output dir, protected root collision, or mid-run failure exits non-zero without false success."""
    loader_calls = {"ja": 0, "jb": 0}

    def fake_ja_loader(_p: Path) -> dict[str, Any]:
        loader_calls["ja"] += 1
        raise TakerBuyShareResearchError("STOP=synthetic_mid_run_loader_failure")

    def fake_jb_loader(_p: Path) -> dict[str, Any]:
        loader_calls["jb"] += 1
        return {}

    # 1. Output directory already exists -> rejected before loader
    existing_out = tmp_path / "already_exists"
    existing_out.mkdir()
    marker = existing_out / "keep.txt"
    marker.write_text("preserve", encoding="utf-8")

    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(existing_out)), encoding="utf-8")
    rc_exists = main(
        ["--auth-file", str(auth_file), "--output-dir", str(existing_out)],
        ja_loader=fake_ja_loader,
        jb_loader=fake_jb_loader,
    )
    assert rc_exists != 0
    assert loader_calls == {"ja": 0, "jb": 0}
    assert marker.read_text(encoding="utf-8") == "preserve"
    assert not (existing_out / "child_rows.csv").exists()
    assert not (existing_out / "review_CN.md").exists()

    # 2. Output directory inside or ancestor of a protected root -> rejected before loader
    protected_root = tmp_path / "protected" / "ja_root"
    protected_root.mkdir(parents=True)
    inside_prot = protected_root / "new_sub"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(inside_prot)), encoding="utf-8")
    rc_inside = main(
        ["--auth-file", str(auth_file), "--output-dir", str(inside_prot)],
        ja_loader=fake_ja_loader,
        jb_loader=fake_jb_loader,
        extra_protected_paths=[protected_root],
    )
    assert rc_inside != 0
    assert loader_calls == {"ja": 0, "jb": 0}

    # Even if ancestor didn't exist yet:
    non_existent_anc = tmp_path / "anc_parent"
    prot_child = non_existent_anc / "sub" / "input_root"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(non_existent_anc)), encoding="utf-8")
    rc_anc = main(
        ["--auth-file", str(auth_file), "--output-dir", str(non_existent_anc)],
        ja_loader=fake_ja_loader,
        jb_loader=fake_jb_loader,
        extra_protected_paths=[prot_child],
    )
    assert rc_anc != 0
    assert loader_calls == {"ja": 0, "jb": 0}

    # 3. Mid-run failure does not create output directory or leave partial files
    clean_out = tmp_path / "clean_out"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(clean_out)), encoding="utf-8")
    rc_fail = main(
        ["--auth-file", str(auth_file), "--output-dir", str(clean_out)],
        ja_loader=fake_ja_loader,
        jb_loader=fake_jb_loader,
    )
    assert rc_fail != 0
    assert not clean_out.exists()


def test_output_symlink_ancestor_rejected(tmp_path: Path) -> None:
    """Verify output path with a symlink ancestor pointing to a protected root is rejected without writing."""
    protected_root = tmp_path / "protected_input_root"
    protected_root.mkdir()
    sentinel = protected_root / "do_not_touch.txt"
    sentinel.write_text("untouched", encoding="utf-8")

    symlink_anc = tmp_path / "symlink_to_protected"
    symlink_anc.symlink_to(protected_root, target_is_directory=True)
    target_out = symlink_anc / "new_report_dir"

    loader_calls = {"count": 0}

    def fake_loader(_p: Path) -> dict[str, Any]:
        loader_calls["count"] += 1
        return {}

    auth_file = tmp_path / "auth_sym.json"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(target_out)), encoding="utf-8")

    rc = main(
        ["--auth-file", str(auth_file), "--output-dir", str(target_out)],
        ja_loader=fake_loader,
        jb_loader=fake_loader,
        extra_protected_paths=[protected_root],
    )
    assert rc != 0
    assert loader_calls["count"] == 0
    assert list(protected_root.iterdir()) == [sentinel]


def test_ledger_classification_tamper_rejected(tmp_path: Path) -> None:
    """Verify tampering only listing_regime in a copy of V2 ledger (preserving composite keys) is rejected by SHA check."""
    real_ledger = Path(EXPECTED_LEDGER_REL)
    tampered_ledger = tmp_path / "tampered_ledger.csv"

    with real_ledger.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    regime_idx = header.index("listing_regime")
    mutated = False
    for r in rows[1:]:
        if r[regime_idx] == "standard":
            r[regime_idx] = "pre_market"
            mutated = True
            break
    assert mutated

    with tampered_ledger.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(rows)

    with pytest.raises(TakerBuyShareResearchError, match="STOP=.*ledger_sha_mismatch"):
        verify_v2_ledger_and_select_universe(
            ledger_path=tampered_ledger,
            jb_child_rows=[],
            ja_root=tmp_path,
            project_root=tmp_path,
            expected_ledger_sha256=EXPECTED_LEDGER_SHA,
        )


def test_oversized_csv_line_rejected(tmp_path: Path) -> None:
    """Verify bounded CSV reader rejects physical lines > 65,536 bytes without producing a report."""
    from research.external_signal_shadow.launch_taker_buy_share_residual_response import (
        build_admitted_ja_context,
    )

    ja_root = tmp_path / "ja_root"
    ja_root.mkdir()
    parent_id = "a" * 32
    symbol = "OVERUSDT"
    utc_date = "2026-01-01"
    t0_ms = 1_767_225_600_000  # 2026-01-01 00:00:00 UTC

    oversized_price = "1" + ("0" * 66_000)
    csv_lines = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"1,{oversized_price},1,1,1,{t0_ms},false",
    ]
    pkg_rec, req_recs, man_arts = _build_synthetic_zip_package(
        ja_root, parent_id, symbol, utc_date, csv_lines
    )
    manifest_obj = {"artifacts": man_arts, "run_id": "synthetic_ja"}
    (ja_root / "manifest.json").write_text(
        json.dumps(manifest_obj, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    ja_summary = {
        "request_records": req_recs,
        "archive_package_records": [pkg_rec],
    }
    ctx = build_admitted_ja_context(ja_root, ja_summary)
    jb_row = {
        "source_article_id": parent_id,
        "symbol": symbol,
        "j_a_parent_state": "coverage_complete",
        "j_a_child_state": "j_a_child_coverage_complete",
        "anchor_state": "anchor_found",
        "symbol_launch_time_ms": t0_ms,
        "anchor_time_ms": t0_ms,
        "anchor_price": "100",
    }

    with pytest.raises(TakerBuyShareResearchError, match="STOP=.*csv_line_length_exceeded"):
        stream_and_evaluate_admitted_child(
            admitted_ja_context=ctx,
            parent_article_id=parent_id,
            symbol=symbol,
            listing_regime="standard",
            jb_child_row=jb_row,
            protocol=FIXED_EXPLORATORY_PROTOCOL,
        )

    # Verify streaming reads to EOF even after max_possible_end_ms (corrupt row after window is still caught)
    sym_eof = "EOFCHECKUSDT"
    eof_lines = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"1,100,1,1,1,{t0_ms},false",
        f"2,100,1,2,2,{t0_ms + 63_000},false",
        f"3,110,1,3,3,{t0_ms + 963_000},false",
        f"4,0,1,4,4,{t0_ms + 2_000_000},false",  # after 15m window, non-positive price at EOF
    ]
    pkg_eof, req_eof, man_eof = _build_synthetic_zip_package(
        ja_root, parent_id, sym_eof, utc_date, eof_lines, zip_req_id=10, chk_req_id=11
    )
    (ja_root / "manifest.json").write_text(
        json.dumps({"artifacts": man_arts + man_eof, "run_id": "synthetic_ja"}, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    ctx_eof = build_admitted_ja_context(
        ja_root, {"request_records": req_eof, "archive_package_records": [pkg_eof]}
    )
    jb_row_eof = dict(jb_row, symbol=sym_eof)
    with pytest.raises(TakerBuyShareResearchError, match="STOP=non_positive_price"):
        stream_and_evaluate_admitted_child(
            admitted_ja_context=ctx_eof,
            parent_article_id=parent_id,
            symbol=sym_eof,
            listing_regime="standard",
            jb_child_row=jb_row_eof,
            protocol=FIXED_EXPLORATORY_PROTOCOL,
        )

    # Also verify via CLI main that an oversized CSV line exits non-zero and writes no report
    out_dir = tmp_path / "no_report_out"
    auth_file = tmp_path / "auth_over.json"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(out_dir)), encoding="utf-8")
    rc = main(
        ["--auth-file", str(auth_file), "--output-dir", str(out_dir)],
        ja_loader=lambda _p: (_ for _ in ()).throw(
            TakerBuyShareResearchError("STOP=csv_line_length_exceeded:OVERUSDT:2026-01-01:1")
        ),
        jb_loader=lambda _p: {},
    )
    assert rc != 0
    assert not out_dir.exists()


def test_summary_structure_and_conservation(tmp_path: Path) -> None:
    """Verify child_rows.csv and review_CN.md structure, conservation, cross-day streaming, corrupt/missing package, and duplicate keys."""
    from research.external_signal_shadow.launch_taker_buy_share_residual_response import (
        build_admitted_ja_context,
    )

    # 1. Cross-day streaming positive + missing next-day package + corrupt checksum + duplicate key checks
    ja_root = tmp_path / "ja_multi"
    ja_root.mkdir()
    parent_id = "b" * 32
    symbol = "CROSSUSDT"
    # 2026-01-01 23:50:00 UTC = 1767311400000 ms
    t0_ms = 1_767_311_400_000
    t_entry_ms = t0_ms + 63_000  # 23:51:03 UTC (still 2026-01-01)
    t_end_ms = t_entry_ms + 900_000  # 00:06:03 UTC on 2026-01-02

    day1_lines = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"100,100,3,100,100,{t0_ms},false",
        f"101,100,1,101,101,{t0_ms + 10_000},true",
        f"102,100,1,102,102,{t_entry_ms},false",
    ]
    day2_lines = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"103,90,1,103,103,{t_end_ms - 100_000},true",
        f"104,130,1,104,104,{t_end_ms - 50_000},false",
        f"105,120,1,105,105,{t_end_ms},false",
    ]
    pkg1, req1, man1 = _build_synthetic_zip_package(
        ja_root, parent_id, symbol, "2026-01-01", day1_lines, zip_req_id=1, chk_req_id=2
    )
    pkg2, req2, man2 = _build_synthetic_zip_package(
        ja_root, parent_id, symbol, "2026-01-02", day2_lines, zip_req_id=3, chk_req_id=4
    )
    (ja_root / "manifest.json").write_text(
        json.dumps({"artifacts": man1 + man2, "run_id": "syn"}, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    # Missing day2 package -> required_package_unavailable
    ctx_missing_day2 = build_admitted_ja_context(
        ja_root, {"request_records": req1, "archive_package_records": [pkg1]}
    )
    jb_row = {
        "source_article_id": parent_id,
        "symbol": symbol,
        "j_a_parent_state": "coverage_complete",
        "j_a_child_state": "j_a_child_coverage_complete",
        "anchor_state": "anchor_found",
        "symbol_launch_time_ms": t0_ms,
        "anchor_time_ms": t0_ms,
        "anchor_price": "100",
    }
    res_missing_pkg = stream_and_evaluate_admitted_child(
        admitted_ja_context=ctx_missing_day2,
        parent_article_id=parent_id,
        symbol=symbol,
        listing_regime="standard",
        jb_child_row=jb_row,
        protocol=FIXED_EXPLORATORY_PROTOCOL,
    )
    assert res_missing_pkg.status == "required_package_unavailable"
    assert res_missing_pkg.taker_buy_share == Fraction(3, 4)
    assert res_missing_pkg.terminal_return is None

    # Both day1 and day2 packages present -> complete cross-day evaluation
    ctx_both = build_admitted_ja_context(
        ja_root, {"request_records": req1 + req2, "archive_package_records": [pkg1, pkg2]}
    )
    res_cross = stream_and_evaluate_admitted_child(
        admitted_ja_context=ctx_both,
        parent_article_id=parent_id,
        symbol=symbol,
        listing_regime="standard",
        jb_child_row=jb_row,
        protocol=FIXED_EXPLORATORY_PROTOCOL,
    )
    assert res_cross.status == "complete"
    assert res_cross.feature_max_intertrade_gap_ms == 10_000
    assert res_cross.taker_buy_share == Fraction(3, 4)
    assert res_cross.terminal_return == Fraction(1, 5)  # 120 / 100 - 1 = 0.2
    assert res_cross.long_mae == Fraction(-1, 10)  # 90 / 100 - 1 = -0.1
    assert res_cross.long_mfe == Fraction(3, 10)  # 130 / 100 - 1 = 0.3

    # P1-01 in stream_and_evaluate_admitted_child: entry window crosses midnight (T0 = 23:58:58 UTC)
    # 1) When 2026-01-02 package is missing -> must return required_package_unavailable (NOT entry_unavailable)
    t0_cross_entry = 1_767_311_938_000  # 2026-01-01 23:58:58 UTC
    sym_ce = "CROSSENTRYUSDT"
    ce_day1_lines = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"200,100,2,200,200,{t0_cross_entry},false",
        f"201,100,2,201,201,{t0_cross_entry + 15_000},true",
    ]
    ce_day2_no_entry_lines = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"202,100,1,202,202,{t0_cross_entry + 70_000},false",
    ]
    pkg_ce1, req_ce1, man_ce1 = _build_synthetic_zip_package(
        ja_root, parent_id, sym_ce, "2026-01-01", ce_day1_lines, zip_req_id=5, chk_req_id=6
    )
    pkg_ce2, req_ce2, man_ce2 = _build_synthetic_zip_package(
        ja_root, parent_id, sym_ce, "2026-01-02", ce_day2_no_entry_lines, zip_req_id=7, chk_req_id=8
    )
    (ja_root / "manifest.json").write_text(
        json.dumps(
            {"artifacts": man1 + man2 + man_ce1 + man_ce2, "run_id": "syn"},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    jb_row_ce = {
        "source_article_id": parent_id,
        "symbol": sym_ce,
        "j_a_parent_state": "coverage_complete",
        "j_a_child_state": "j_a_child_coverage_complete",
        "anchor_state": "anchor_found",
        "symbol_launch_time_ms": t0_cross_entry,
        "anchor_time_ms": t0_cross_entry,
        "anchor_price": "100",
    }
    ctx_ce_missing_day2 = build_admitted_ja_context(
        ja_root, {"request_records": req_ce1, "archive_package_records": [pkg_ce1]}
    )
    res_ce_missing = stream_and_evaluate_admitted_child(
        admitted_ja_context=ctx_ce_missing_day2,
        parent_article_id=parent_id,
        symbol=sym_ce,
        listing_regime="standard",
        jb_child_row=jb_row_ce,
        protocol=FIXED_EXPLORATORY_PROTOCOL,
    )
    assert res_ce_missing.status == "required_package_unavailable"
    assert res_ce_missing.taker_buy_share == Fraction(1, 2)
    assert res_ce_missing.terminal_return is None

    # 2) When 2026-01-02 package IS present and has no trade in [T0+63s, T0+64s] -> entry_unavailable
    ctx_ce_both = build_admitted_ja_context(
        ja_root, {"request_records": req_ce1 + req_ce2, "archive_package_records": [pkg_ce1, pkg_ce2]}
    )
    res_ce_no_entry = stream_and_evaluate_admitted_child(
        admitted_ja_context=ctx_ce_both,
        parent_article_id=parent_id,
        symbol=sym_ce,
        listing_regime="standard",
        jb_child_row=jb_row_ce,
        protocol=FIXED_EXPLORATORY_PROTOCOL,
    )
    assert res_ce_no_entry.status == "entry_unavailable"
    assert res_ce_no_entry.taker_buy_share == Fraction(1, 2)
    assert res_ce_no_entry.terminal_return is None

    # Duplicate package record key rejected
    with pytest.raises(TakerBuyShareResearchError, match="STOP=duplicate_package_record"):
        build_admitted_ja_context(
            ja_root, {"request_records": req1, "archive_package_records": [pkg1, dict(pkg1)]}
        )

    # Corrupt checksum file rejected
    chk_file = ja_root / f"raw/archive/{symbol}/{symbol}-aggTrades-2026-01-01.zip.CHECKSUM"
    orig_chk = chk_file.read_bytes()
    chk_file.write_bytes(b"corrupt_checksum_content\n")
    with pytest.raises(TakerBuyShareResearchError, match="STOP=checksum_invalid"):
        stream_and_evaluate_admitted_child(
            admitted_ja_context=ctx_both,
            parent_article_id=parent_id,
            symbol=symbol,
            listing_regime="standard",
            jb_child_row=jb_row,
            protocol=FIXED_EXPLORATORY_PROTOCOL,
        )
    chk_file.write_bytes(orig_chk)
    # Construct 4 synthetic children across pre_market (1 complete, 1 gap) and standard (2 complete)
    # Standard:
    #   P1/S1USDT: share = 1/4, term = 1/10, mae = -1/20, mfe = 2/10
    #   P2/S2USDT: share = 3/4, term = 3/10, mae = -1/10, mfe = 4/10
    #   -> Standard median share = 1/2; low={P1/S1} (term=1/10), high={P2/S2} (term=3/10), diff = 2/10 = 1/5
    # Pre-market:
    #   P3/PM1USDT: share = 2/5, term = -1/10, mae = -2/10, mfe = 1/20
    #   P4/PM2USDT: status = entry_unavailable (share = 3/5, term = None)
    #   -> Pre-market complete = 1 -> median = 2/5 -> low={P3/PM1}, high=empty -> diff = None (evidence_insufficient)
    c1 = evaluate_child_residual_response(
        parent_article_id="p" + "1" * 31,
        symbol="S1USDT",
        listing_regime="standard",
        protocol=FIXED_EXPLORATORY_PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(1, Decimal("100"), Decimal("1"), 0, False),
            AggTradeRecord(2, Decimal("100"), Decimal("3"), 10_000, True),
            AggTradeRecord(3, Decimal("100"), Decimal("1"), 63_000, False),
            AggTradeRecord(4, Decimal("95"), Decimal("1"), 100_000, True),
            AggTradeRecord(5, Decimal("120"), Decimal("1"), 200_000, False),
            AggTradeRecord(6, Decimal("110"), Decimal("1"), 963_000, False),
        ],
    )
    c2 = evaluate_child_residual_response(
        parent_article_id="p" + "2" * 31,
        symbol="S2USDT",
        listing_regime="standard",
        protocol=FIXED_EXPLORATORY_PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(1, Decimal("100"), Decimal("3"), 0, False),
            AggTradeRecord(2, Decimal("100"), Decimal("1"), 10_000, True),
            AggTradeRecord(3, Decimal("100"), Decimal("1"), 63_000, False),
            AggTradeRecord(4, Decimal("90"), Decimal("1"), 100_000, True),
            AggTradeRecord(5, Decimal("140"), Decimal("1"), 200_000, False),
            AggTradeRecord(6, Decimal("130"), Decimal("1"), 963_000, False),
        ],
    )
    c3 = evaluate_child_residual_response(
        parent_article_id="p" + "3" * 31,
        symbol="PM1USDT",
        listing_regime="pre_market",
        protocol=FIXED_EXPLORATORY_PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(1, Decimal("100"), Decimal("2"), 0, False),
            AggTradeRecord(2, Decimal("100"), Decimal("3"), 10_000, True),
            AggTradeRecord(3, Decimal("100"), Decimal("1"), 63_000, False),
            AggTradeRecord(4, Decimal("80"), Decimal("1"), 100_000, True),
            AggTradeRecord(5, Decimal("105"), Decimal("1"), 200_000, False),
            AggTradeRecord(6, Decimal("90"), Decimal("1"), 963_000, False),
        ],
    )
    c4 = evaluate_child_residual_response(
        parent_article_id="p" + "4" * 31,
        symbol="PM2USDT",
        listing_regime="pre_market",
        protocol=FIXED_EXPLORATORY_PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(1, Decimal("100"), Decimal("3"), 0, False),
            AggTradeRecord(2, Decimal("100"), Decimal("2"), 10_000, True),
        ],
    )

    out_dir = tmp_path / "report_out"
    csv_path, md_path = write_exploratory_outputs(
        output_dir=out_dir,
        protected_paths=[tmp_path / "protected"],
        protocol=FIXED_EXPLORATORY_PROTOCOL,
        child_results=[c1, c2, c3, c4],
        design_sha256=EXPECTED_DESIGN_SHA,
        plan_sha256=EXPECTED_PLAN_SHA,
        ja_run_id="stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z",
        jb_run_id="stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z",
        ledger_sha256=EXPECTED_LEDGER_SHA,
    )

    assert Path(csv_path).is_file()
    assert Path(md_path).is_file()
    assert {p.name for p in out_dir.iterdir()} == {"child_rows.csv", "review_CN.md"}

    with Path(csv_path).open("r", encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))

    # Conservation: all 4 universe children present in CSV
    assert len(csv_rows) == 4
    by_sym = {r["symbol"]: r for r in csv_rows}
    assert by_sym["S1USDT"]["status"] == "complete"
    assert by_sym["S1USDT"]["feature_max_intertrade_gap_ms"] == "10000"
    assert by_sym["S1USDT"]["taker_buy_share_exact"] == "1/4"
    assert by_sym["S1USDT"]["terminal_return_exact"] == "1/10"
    assert by_sym["S1USDT"]["child_group"] == "low"
    assert by_sym["S2USDT"]["status"] == "complete"
    assert by_sym["S2USDT"]["feature_max_intertrade_gap_ms"] == "10000"
    assert by_sym["S2USDT"]["taker_buy_share_exact"] == "3/4"
    assert by_sym["S2USDT"]["terminal_return_exact"] == "3/10"
    assert by_sym["S2USDT"]["child_group"] == "high"
    assert by_sym["PM1USDT"]["status"] == "complete"
    assert by_sym["PM1USDT"]["feature_max_intertrade_gap_ms"] == "10000"
    assert by_sym["PM1USDT"]["taker_buy_share_exact"] == "2/5"
    assert by_sym["PM2USDT"]["status"] == "entry_unavailable"
    assert by_sym["PM2USDT"]["feature_max_intertrade_gap_ms"] == "10000"
    assert by_sym["PM2USDT"]["terminal_return_exact"] == ""

    md_text = Path(md_path).read_text(encoding="utf-8")
    assert EXPECTED_DESIGN_SHA in md_text
    assert EXPECTED_PLAN_SHA in md_text
    assert EXPECTED_LEDGER_SHA in md_text
    assert "exploratory" in md_text
    assert "evidence_insufficient" in md_text
    assert "1/5" in md_text  # standard high_minus_low_terminal_mean = 3/10 - 1/10 = 1/5
    assert "feature_max_intertrade_gap_ms" in md_text
    # P1-02 negative assertions: review_CN.md must NOT contain unapproved MAE/MFE leave-one-out or Child leave-one-out
    assert "high - low MAE Mean" not in md_text
    assert "high - low MFE Mean" not in md_text
    assert "Child 视角逐一剔除每个完整 Parent" not in md_text


@pytest.fixture
def single_run_auth_file() -> Path:
    """Return path to explicit user single-run authorization file if provided, else skip."""
    env_path = os.environ.get("TAKER_BUY_SHARE_SINGLE_RUN_AUTH_FILE", "").strip()
    if not env_path:
        pytest.skip("historical_validation_not_authorized: TAKER_BUY_SHARE_SINGLE_RUN_AUTH_FILE not set")
    p = Path(env_path)
    if not p.is_file():
        pytest.skip(f"historical_validation_not_authorized: auth file not found at {p}")
    return p


def test_canonical_upstream_positive(single_run_auth_file: Path) -> None:
    """Verify positive admission and reduction of at least one real complete child from closure-audited J-A/J-B roots."""
    from research.external_signal_shadow.launch_taker_buy_share_residual_response import (
        build_admitted_ja_context,
        verify_single_run_authorization,
    )
    from research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        load_verified_stage1_5j_a_historical_archive_coverage_root,
    )
    from research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
    )

    proj = Path.cwd().resolve()
    verify_single_run_authorization(auth_file=single_run_auth_file, expected_output_dir=None, project_root=proj)

    ja_root = proj / EXPECTED_JA_REL
    jb_root = proj / EXPECTED_JB_REL
    ledger_path = proj / EXPECTED_LEDGER_REL

    ja_summary = load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)
    jb_summary = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(jb_root)
    _u_rows, selected_rows = verify_v2_ledger_and_select_universe(
        ledger_path=ledger_path,
        jb_child_rows=jb_summary["child_rows"],
        ja_root=ja_root,
        project_root=proj,
    )
    ctx = build_admitted_ja_context(ja_root, ja_summary)
    jb_by_key = {(str(r["source_article_id"]), str(r["symbol"])): r for r in jb_summary["child_rows"]}

    complete_res: ChildResidualResponseResult | None = None
    for s_row in selected_rows:
        pid = str(s_row["parent_article_id"])
        sym = str(s_row["symbol"])
        reg = str(s_row["listing_regime"])
        jb_r = jb_by_key[(pid, sym)]
        if jb_r["j_a_parent_state"] == "coverage_complete" and jb_r["anchor_state"] == "anchor_found":
            res = stream_and_evaluate_admitted_child(
                admitted_ja_context=ctx,
                parent_article_id=pid,
                symbol=sym,
                listing_regime=reg,
                jb_child_row=jb_r,
                protocol=FIXED_EXPLORATORY_PROTOCOL,
            )
            if res.status == "complete":
                complete_res = res
                break

    assert complete_res is not None
    assert complete_res.taker_buy_share is not None
    assert Fraction(0, 1) <= complete_res.taker_buy_share <= Fraction(1, 1)
    assert complete_res.terminal_return is not None


def test_canonical_single_mutation_rejected(single_run_auth_file: Path, tmp_path: Path) -> None:
    """Copy a real admitted package to tmp_path, mutate 1 byte of CHECKSUM, and verify fail-closed rejection."""
    from research.external_signal_shadow.launch_taker_buy_share_residual_response import (
        AdmittedJAContext,
        build_admitted_ja_context,
        verify_single_run_authorization,
    )
    from research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        load_verified_stage1_5j_a_historical_archive_coverage_root,
    )
    from research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
    )

    proj = Path.cwd().resolve()
    verify_single_run_authorization(auth_file=single_run_auth_file, expected_output_dir=None, project_root=proj)

    ja_root = proj / EXPECTED_JA_REL
    jb_root = proj / EXPECTED_JB_REL
    ja_summary = load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)
    jb_summary = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(jb_root)
    ctx = build_admitted_ja_context(ja_root, ja_summary)

    target_jb: dict[str, Any] | None = None
    target_pkg: dict[str, Any] | None = None
    for cr in jb_summary["child_rows"]:
        if cr["j_a_parent_state"] == "coverage_complete" and cr["anchor_state"] == "anchor_found":
            pid = str(cr["source_article_id"])
            sym = str(cr["symbol"])
            for (k_pid, k_sym, _k_date), pkg in ctx.package_by_key.items():
                if k_pid == pid and k_sym == sym and pkg["child_state"] == "archive_verified_with_post_launch_rows":
                    target_jb = cr
                    target_pkg = pkg
                    break
        if target_pkg is not None:
            break

    assert target_jb is not None and target_pkg is not None
    sym = str(target_pkg["symbol"])
    utc_date = str(target_pkg["utc_date"])
    zip_rel = f"raw/archive/{sym}/{sym}-aggTrades-{utc_date}.zip"
    chk_rel = f"{zip_rel}.CHECKSUM"

    tmp_ja = tmp_path / "ja_copy"
    (tmp_ja / zip_rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ja_root / zip_rel, tmp_ja / zip_rel)
    shutil.copy2(ja_root / chk_rel, tmp_ja / chk_rel)

    # Mutate 1 hex digit in the copied CHECKSUM file
    chk_bytes = bytearray((tmp_ja / chk_rel).read_bytes())
    chk_bytes[0] = ord("f") if chk_bytes[0] != ord("f") else ord("0")
    (tmp_ja / chk_rel).write_bytes(bytes(chk_bytes))

    mut_ctx = AdmittedJAContext(
        ja_root=tmp_ja,
        manifest_by_path=ctx.manifest_by_path,
        request_by_id=ctx.request_by_id,
        package_by_key=ctx.package_by_key,
        admitted_object_ids=ctx.admitted_object_ids,
    )

    with pytest.raises(TakerBuyShareResearchError, match="STOP=.*checksum_invalid"):
        stream_and_evaluate_admitted_child(
            admitted_ja_context=mut_ctx,
            parent_article_id=str(target_jb["source_article_id"]),
            symbol=sym,
            listing_regime="standard",
            jb_child_row=target_jb,
            protocol=FIXED_EXPLORATORY_PROTOCOL,
        )
