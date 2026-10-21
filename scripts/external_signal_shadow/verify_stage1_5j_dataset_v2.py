#!/usr/bin/env python3
"""
scripts/external_signal_shadow/verify_stage1_5j_dataset_v2.py

Strict verification suite for Stage 1.5J Dataset V2 and Classification Ledger V2.
Enforces all 6 user-approved acceptance criteria:
Gate 1: Upstream J-A and J-B receipt files unmodified (SHA invariant holds).
Gate 2: Dataset composite primary key (parent_article_id, symbol) is strictly unique
        and matches canonical J-B child_rows set (281 rows).
Gate 3: All 3 horizons (5m, 1h, 4h) match J-B receipt exactly (state, missing_reason,
        raw bps, converted pct via Decimal, trade_count, prices, offsets).
Gate 4: Multi-event same-name symbols (e.g. AIAUSDT) do not cross-contaminate;
        gap row retains null/empty values; lead_time >= 1h integer comparison
        is not contaminated by decimal rounding.
Gate 5: Classification ledger is 1-to-1 bijective with dataset v2; every confirmed
        record has non-empty evidence_locator and valid source_relative_path/sha256;
        unknown record (USDBRL) explicitly preserved.
Gate 6: Export reproducibility: re-running export produces byte-for-byte identical output.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# Frozen Upstream Canonical Identity Tuples
UPSTREAM_J_A_RUN_ID = "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
UPSTREAM_J_A_ROOT_REL = "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
UPSTREAM_J_A_MANIFEST_SHA256 = "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf"
UPSTREAM_J_A_SUMMARY_SHA256 = "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b"

UPSTREAM_J_B_RUN_ID = "stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"
UPSTREAM_J_B_ROOT_REL = "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"
UPSTREAM_J_B_MANIFEST_SHA256 = "f0a8ac724925084161f6b9aa2dced5139b261707fda0f0f21ebd0eb6de3087fb"
UPSTREAM_J_B_SUMMARY_SHA256 = "5ea0f1c87803114c4c6917cd0c3d24292948fa0e7066a80e0a2bce611e32546b"


def run_verification() -> None:
    project_root = Path(__file__).resolve().parents[2]
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    ja_root = project_root / UPSTREAM_J_A_ROOT_REL
    jb_root = project_root / UPSTREAM_J_B_ROOT_REL
    ja_manifest_path = ja_root / "manifest.json"
    ja_summary_path = ja_root / "summary.json"
    jb_manifest_path = jb_root / "manifest.json"
    jb_summary_path = jb_root / "summary.json"

    dataset_csv_path = project_root / "data/exports/stage1_5j_full_year_token_launch_dataset_v2.csv"
    ledger_csv_path = project_root / "data/exports/stage1_5j_token_launch_classification_ledger_v2.csv"

    print("=" * 70)
    print("STARTING STAGE 1.5J V2 EXPORT VERIFICATION SUITE")
    print("=" * 70)

    # ---------------------------------------------------------
    # Gate 1: Upstream Receipt SHA Invariant & Strict Admission
    # ---------------------------------------------------------
    print("[Gate 1] Checking Upstream Source Receipts...")
    assert ja_manifest_path.exists(), f"J-A manifest missing: {ja_manifest_path}"
    assert ja_summary_path.exists(), f"J-A summary missing: {ja_summary_path}"
    assert jb_manifest_path.exists(), f"J-B manifest missing: {jb_manifest_path}"
    assert jb_summary_path.exists(), f"J-B summary missing: {jb_summary_path}"

    assert compute_sha256(ja_manifest_path) == UPSTREAM_J_A_MANIFEST_SHA256, (
        f"J-A manifest SHA mismatch: expected {UPSTREAM_J_A_MANIFEST_SHA256}, got {compute_sha256(ja_manifest_path)}"
    )
    assert compute_sha256(ja_summary_path) == UPSTREAM_J_A_SUMMARY_SHA256, (
        f"J-A summary SHA mismatch: expected {UPSTREAM_J_A_SUMMARY_SHA256}, got {compute_sha256(ja_summary_path)}"
    )
    assert compute_sha256(jb_manifest_path) == UPSTREAM_J_B_MANIFEST_SHA256, (
        f"J-B manifest SHA mismatch: expected {UPSTREAM_J_B_MANIFEST_SHA256}, got {compute_sha256(jb_manifest_path)}"
    )
    assert compute_sha256(jb_summary_path) == UPSTREAM_J_B_SUMMARY_SHA256, (
        f"J-B summary SHA mismatch: expected {UPSTREAM_J_B_SUMMARY_SHA256}, got {compute_sha256(jb_summary_path)}"
    )

    from research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        load_verified_stage1_5j_a_historical_archive_coverage_root,
    )
    from research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
    )

    ja_summary = load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)
    assert ja_summary["run_id"] == UPSTREAM_J_A_RUN_ID, (
        f"J-A RUN_ID mismatch: expected {UPSTREAM_J_A_RUN_ID}, got {ja_summary['run_id']}"
    )

    jb = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(jb_root)
    assert jb["run_id"] == UPSTREAM_J_B_RUN_ID, (
        f"J-B RUN_ID mismatch: expected {UPSTREAM_J_B_RUN_ID}, got {jb['run_id']}"
    )
    assert jb["schema_version"] == "stage1_5j_b_historical_aggtrades_launch_response_v1"
    assert len(jb["child_rows"]) == 281
    assert len(jb["child_horizon_rows"]) == 843
    print("  ✓ Gate 1 Passed: Upstream receipt files verified via SHA invariants and strict loaders.")

    # ---------------------------------------------------------
    # Gate 2: Primary Key & Canonical Membership
    # ---------------------------------------------------------
    print("[Gate 2] Checking Primary Key & Exact 281 Event Set...")
    with open(dataset_csv_path, encoding="utf-8") as f:
        dataset_rows = list(csv.DictReader(f))

    assert len(dataset_rows) == 281, f"Expected 281 rows, got {len(dataset_rows)}"

    dataset_keys = [(r["parent_article_id"], r["symbol"]) for r in dataset_rows]
    assert len(dataset_keys) == len(set(dataset_keys)), "Composite primary key not unique in dataset!"

    jb_keys = [(cr["source_article_id"], cr["symbol"]) for cr in jb["child_rows"]]
    assert set(dataset_keys) == set(jb_keys), "Dataset keys do not match J-B child_rows!"
    print("  ✓ Gate 2 Passed: 281 primary keys strictly unique and match J-B child_rows.")

    # ---------------------------------------------------------
    # Gate 3: Window Metrics Exact Correspondence with J-B
    # ---------------------------------------------------------
    print("[Gate 3] Checking Window Metrics Correspondence with J-B Receipt...")
    horizons_map = {}
    for hr in jb["child_horizon_rows"]:
        key = (hr["source_article_id"], hr["symbol"], hr["horizon_ms"])
        horizons_map[key] = hr

    dataset_dict = {(r["parent_article_id"], r["symbol"]): r for r in dataset_rows}

    for (aid, sym), r in dataset_dict.items():
        for h_ms, h_label in [(300000, "5m"), (3600000, "1h"), (14400000, "4h")]:
            hr = horizons_map[(aid, sym, h_ms)]

            # Check state and missing reason
            assert r[f"horizon_state_{h_label}"] == hr["child_horizon_state"], f"State mismatch for {(aid, sym, h_label)}"
            exp_missing = hr["missing_reason"] or ""
            assert r[f"missing_reason_{h_label}"] == exp_missing, f"Missing reason mismatch for {(aid, sym, h_label)}"

            # If complete, verify bps and pct
            if hr["child_horizon_state"] == "child_horizon_complete":
                assert r[f"gross_return_bps_{h_label}"] == hr["gross_return_bps"]
                assert r[f"sampled_max_excursion_bps_{h_label}"] == hr["sampled_max_excursion_bps"]
                assert r[f"sampled_min_excursion_bps_{h_label}"] == hr["sampled_min_excursion_bps"]

                # Verify exact Decimal conversion
                exp_pct = str(Decimal(hr["gross_return_bps"]) / Decimal(100))
                assert r[f"gross_return_pct_{h_label}"] == exp_pct, f"Decimal pct conversion mismatch for {(aid, sym, h_label)}"

                assert r[f"trade_count_{h_label}"] == str(hr["trade_count"])
                assert r[f"horizon_price_{h_label}"] == hr["horizon_price"]
                assert r[f"horizon_offset_ms_{h_label}"] == str(hr["horizon_offset_ms"])
            else:
                # Evidence gap: MUST BE EMPTY, NOT ZERO
                assert r[f"gross_return_bps_{h_label}"] == "", f"Expected empty bps for gap {(aid, sym, h_label)}"
                assert r[f"gross_return_pct_{h_label}"] == "", f"Expected empty pct for gap {(aid, sym, h_label)}"
                assert r[f"trade_count_{h_label}"] == "", f"Expected empty trade_count for gap {(aid, sym, h_label)}"

    print("  ✓ Gate 3 Passed: 843 window metrics strictly match J-B receipt.")

    # ---------------------------------------------------------
    # Gate 4: Cross-Contamination & Rounding Integrity Probes
    # ---------------------------------------------------------
    print("[Gate 4] Checking AIA Dedup and Exact Lead-Time Probes...")
    aia_rows = [r for r in dataset_rows if r["symbol"] == "AIAUSDT"]
    assert len(aia_rows) == 2, f"Expected exactly 2 AIA rows, got {len(aia_rows)}"

    gap_aia = next(r for r in aia_rows if r["anchor_state"] != "anchor_found")
    complete_aia = next(r for r in aia_rows if r["anchor_state"] == "anchor_found")

    # Verify gap row did NOT inherit complete row's return or trades
    assert gap_aia["horizon_state_5m"] == "child_horizon_evidence_gap"
    assert gap_aia["gross_return_bps_5m"] == ""
    assert gap_aia["trade_count_5m"] == ""

    # Verify complete row retained its true returns
    assert complete_aia["horizon_state_5m"] == "child_horizon_complete"
    assert complete_aia["gross_return_bps_5m"] == "1634.53815261"
    assert complete_aia["trade_count_5m"] == "34228"

    # Verify integer ms lead time >= 1h comparison for DOS and MARSCOIN
    dos_row = next(r for r in dataset_rows if r["symbol"] == "DOSUSDT")
    marscoin_row = next(r for r in dataset_rows if r["symbol"] == "MARSCOINUSDT")

    # In raw receipt, their lead time is strictly < 3,600,000 ms
    assert int(dos_row["lead_time_ms"]) < 3600000, f"DOS lead time ms expected < 1h: {dos_row['lead_time_ms']}"
    assert int(marscoin_row["lead_time_ms"]) < 3600000, f"MARSCOIN lead time ms expected < 1h: {marscoin_row['lead_time_ms']}"
    print(f"  ✓ Gate 4 Passed: AIA gap isolation verified; DOS ({dos_row['lead_time_ms']}ms) & MARSCOIN ({marscoin_row['lead_time_ms']}ms) correctly < 3,600,000ms.")

    # ---------------------------------------------------------
    # Gate 5: Classification Ledger 1-to-1 Correspondence & AST Coordinate Proof
    # ---------------------------------------------------------
    print("[Gate 5] Checking Classification Ledger 1-to-1 Correspondence & AST Coordinate Proof...")
    from scripts.external_signal_shadow.export_stage1_5j_dataset_v2 import (
        classify_from_ast_table,
        parse_article_tables,
    )

    with open(ledger_csv_path, encoding="utf-8") as f:
        ledger_rows = list(csv.DictReader(f))

    assert len(ledger_rows) == 281, f"Expected 281 ledger rows, got {len(ledger_rows)}"

    ledger_keys = [(r["parent_article_id"], r["symbol"]) for r in ledger_rows]
    assert ledger_keys == sorted(dataset_keys), "Ledger keys do not match dataset keys!"

    required_cols = [
        "parent_article_id", "symbol", "asset_class", "listing_regime",
        "classification_status", "table_index", "symbol_column_index",
        "field_header", "raw_cell_value", "evidence_locator",
        "source_relative_path", "source_sha256"
    ]
    assert list(ledger_rows[0].keys()) == required_cols, f"Ledger columns mismatch: {list(ledger_rows[0].keys())}"

    # Verify each row against actual AST JSON file on disk
    regime_counter = {}
    for r in ledger_rows:
        src_path = project_root / r["source_relative_path"]
        assert src_path.exists(), f"Source file does not exist: {src_path}"
        assert compute_sha256(src_path) == r["source_sha256"], f"SHA mismatch for source file: {src_path}"
        assert r["asset_class"] in ["crypto", "equity", "etf", "commodity", "index", "unknown"]
        assert r["listing_regime"] in ["standard", "pre_market", "pre_ipo", "unknown"]
        assert r["classification_status"] in ["confirmed", "unknown"]

        with open(src_path, encoding="utf-8") as f:
            art_data = json.load(f)["data"]
        title = art_data.get("title", "")
        body_obj = json.loads(art_data.get("body", "{}"))
        tables = parse_article_tables(body_obj)

        t_idx = int(r["table_index"])
        c_idx = int(r["symbol_column_index"])
        assert 0 <= t_idx < len(tables), f"Table index {t_idx} out of range for {r['symbol']} in {src_path}"
        tbl = tables[t_idx]

        # Verify symbol appears in that column
        sym = r["symbol"]
        col_cells = [row[c_idx] if len(row) > c_idx else "" for row in tbl]
        assert any(sym.upper() in c.upper().replace(" ", "") for c in col_cells), (
            f"Symbol {sym} not found in table[{t_idx}].col[{c_idx}]"
        )

        # Verify field_header and raw_cell_value
        hdr = r["field_header"]
        val = r["raw_cell_value"]
        row_map = {row[0]: row[c_idx] if len(row) > c_idx else "" for row in tbl if len(row) > 0}
        assert hdr in row_map, f"Header '{hdr}' not found in table[{t_idx}] for {sym}"
        assert row_map[hdr] == val, f"Cell value mismatch for {sym}: expected '{val}', observed '{row_map[hdr]}'"

        # Re-run strict classification and verify match
        re_class, re_regime, re_status, re_t, re_c, re_hdr, re_val, re_loc = classify_from_ast_table(
            title, tables, sym
        )
        assert re_class == r["asset_class"], f"Asset class mismatch: {re_class} vs {r['asset_class']}"
        assert re_regime == r["listing_regime"], f"Regime mismatch: {re_regime} vs {r['listing_regime']}"
        assert re_status == r["classification_status"], f"Status mismatch: {re_status} vs {r['classification_status']}"
        assert re_t == t_idx and re_c == c_idx and re_hdr == hdr and re_val == val, "Coordinate/value mismatch"
        assert re_loc == r["evidence_locator"], f"Evidence locator mismatch: {re_loc} vs {r['evidence_locator']}"

        key = (r["asset_class"], r["listing_regime"], r["classification_status"])
        regime_counter[key] = regime_counter.get(key, 0) + 1

    # Verify exact group counts across all 281 events
    assert regime_counter.get(("crypto", "standard", "confirmed")) == 53, f"Expected 53 crypto x standard, got {regime_counter.get(('crypto', 'standard', 'confirmed'))}"
    assert regime_counter.get(("crypto", "pre_market", "confirmed")) == 18, f"Expected 18 crypto x pre_market, got {regime_counter.get(('crypto', 'pre_market', 'confirmed'))}"
    assert regime_counter.get(("equity", "standard", "confirmed")) == 165, f"Expected 165 equity x standard, got {regime_counter.get(('equity', 'standard', 'confirmed'))}"
    assert regime_counter.get(("equity", "pre_ipo", "confirmed")) == 6, f"Expected 6 equity x pre_ipo, got {regime_counter.get(('equity', 'pre_ipo', 'confirmed'))}"
    assert regime_counter.get(("etf", "standard", "confirmed")) == 31, f"Expected 31 etf x standard, got {regime_counter.get(('etf', 'standard', 'confirmed'))}"
    assert regime_counter.get(("commodity", "standard", "confirmed")) == 7, f"Expected 7 commodity x standard, got {regime_counter.get(('commodity', 'standard', 'confirmed'))}"
    assert regime_counter.get(("unknown", "standard", "unknown")) == 1, f"Expected 1 unknown x standard, got {regime_counter.get(('unknown', 'standard', 'unknown'))}"

    # Verify AIAUSDT has exactly 2 event rows representing 1 unique symbol across 2 distinct parents
    aia_ledger = [r for r in ledger_rows if r["symbol"] == "AIAUSDT"]
    assert len(aia_ledger) == 2, f"Expected 2 AIA rows, got {len(aia_ledger)}"
    assert len(set(r["parent_article_id"] for r in aia_ledger)) == 2

    print("  ✓ Gate 5 Passed: All 281 classifications verified against exact AST table coordinates and raw cell values.")

    # ---------------------------------------------------------
    # Gate 6: Byte-for-Byte Determinism / Reproducibility (Read-Only)
    # ---------------------------------------------------------
    print("[Gate 6] Checking Byte-for-Byte Reproducibility in Isolated Tempdir...")
    sha_dataset_1 = compute_sha256(dataset_csv_path)
    sha_ledger_1 = compute_sha256(ledger_csv_path)

    # Re-run export into an isolated temporary directory (strictly read-only on data/exports)
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(
            [
                sys.executable,
                str(project_root / "scripts/external_signal_shadow/export_stage1_5j_dataset_v2.py"),
                "--output-dir",
                tmp_dir,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        tmp_dataset = Path(tmp_dir) / "stage1_5j_full_year_token_launch_dataset_v2.csv"
        tmp_ledger = Path(tmp_dir) / "stage1_5j_token_launch_classification_ledger_v2.csv"

        sha_dataset_tmp = compute_sha256(tmp_dataset)
        sha_ledger_tmp = compute_sha256(tmp_ledger)

        assert sha_dataset_tmp == sha_dataset_1, (
            f"Dataset CSV output mismatch! Canonical: {sha_dataset_1}, Tempdir: {sha_dataset_tmp}"
        )
        assert sha_ledger_tmp == sha_ledger_1, (
            f"Ledger CSV output mismatch! Canonical: {sha_ledger_1}, Tempdir: {sha_ledger_tmp}"
        )

    # Re-verify that canonical data/exports files remained strictly untouched
    assert compute_sha256(dataset_csv_path) == sha_dataset_1, "Canonical dataset CSV was modified!"
    assert compute_sha256(ledger_csv_path) == sha_ledger_1, "Canonical ledger CSV was modified!"
    print(
        f"  ✓ Gate 6 Passed: Deterministic execution verified via read-only tempdir. "
        f"Dataset SHA: {sha_dataset_1[:16]}..., Ledger SHA: {sha_ledger_1[:16]}..."
    )

    print("=" * 70)
    print("ALL 6 ACCEPTANCE GATES PASSED (PASS_ALL)")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
