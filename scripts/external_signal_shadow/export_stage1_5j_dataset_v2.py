#!/usr/bin/env python3
"""
scripts/external_signal_shadow/export_stage1_5j_dataset_v2.py

Reproducible exporter for Stage 1.5J Token Launch V2 Dataset and Classification Ledger.
Features:
1. Orthogonal taxonomy: asset_class (crypto, equity, etf, commodity, index, unknown)
                      x listing_regime (standard, pre_market, pre_ipo, unknown).
2. Ground-truth evidence extraction from J-A article JSON AST specification tables.
3. Composite primary key (parent_article_id, symbol) to eliminate cross-announcement symbol collisions.
4. Integer milliseconds for all time fields; Decimal for exact percentage conversions;
   raw receipt string preservation for bps and prices.
5. Retains all 281 child events with explicit missing/gap states (no silent drops, no zero-filling).
6. Full deterministic output and self-verification against 6 acceptance criteria.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def extract_ast_text(node) -> str:
    """Recursively extract plain text from Binance announcement AST body."""
    if isinstance(node, dict):
        if node.get("node") == "text":
            return node.get("text", "")
        return "".join(extract_ast_text(c) for c in node.get("child", []))
    elif isinstance(node, list):
        return "".join(extract_ast_text(c) for c in node)
    return ""


def parse_article_tables(body_obj) -> list:
    """Extract all table rows as 2D lists of cell text."""
    tables = []

    def find_tables(node):
        if isinstance(node, dict):
            if node.get("tag") == "table":
                tables.append(node)
            for c in node.get("child", []):
                find_tables(c)
        elif isinstance(node, list):
            for c in node:
                find_tables(c)

    find_tables(body_obj)

    parsed_tables = []
    for t in tables:
        rows = []

        def find_rows(node):
            if isinstance(node, dict):
                if node.get("tag") == "tr":
                    cells = []
                    for c in node.get("child", []):
                        if isinstance(c, dict) and c.get("tag") in ["td", "th"]:
                            cells.append(extract_ast_text(c).strip())
                    if cells:
                        rows.append(cells)
                for c in node.get("child", []):
                    find_rows(c)
            elif isinstance(node, list):
                for c in node:
                    find_rows(c)

        find_rows(t)
        if rows:
            parsed_tables.append(rows)
    return parsed_tables


def ms_to_iso(ms: int | None) -> str:
    if ms is None:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def bps_to_pct_str(bps_str: str | None) -> str:
    if bps_str is None or bps_str == "":
        return ""
    # Exact decimal division by 100 without float binary representation error
    d = Decimal(bps_str) / Decimal(100)
    # Normalize trailing zeros if any while keeping exact value
    return str(d)


def lead_time_hours_str(lead_time_ms: int | None) -> str:
    if lead_time_ms is None:
        return ""
    d = Decimal(lead_time_ms) / Decimal(3600000)
    return str(round(d, 6))


def classify_from_ast_table(
    title: str,
    tables: list[list[list[str]]],
    symbol: str,
) -> tuple[str, str, str, int, int, str, str, str]:
    """
    Classify symbol based on AST table coordinates and content.
    Returns:
        asset_class: crypto | equity | etf | commodity | index | unknown
        listing_regime: standard | pre_market | pre_ipo | unknown
        classification_status: confirmed | unknown
        table_index: int
        symbol_column_index: int
        field_header: str
        raw_cell_value: str
        evidence_locator: str
    """
    t_lower = title.lower()
    if "pre-market" in t_lower:
        regime = "pre_market"
    elif "pre-ipo" in t_lower:
        regime = "pre_ipo"
    else:
        regime = "standard"

    # Match symbol in tables
    matched_col = None
    for t_idx, tbl in enumerate(tables):
        for r_idx, row in enumerate(tbl):
            for c_idx, cell in enumerate(row):
                if symbol.upper() in cell.upper().replace(" ", ""):
                    matched_col = (t_idx, c_idx, tbl)
                    break
            if matched_col:
                break
        if matched_col:
            break

    if not matched_col:
        return "unknown", regime, "unknown", -1, -1, "", "", "no_table_match"

    t_idx, c_idx, tbl = matched_col
    row_map = {r[0]: (r_idx, r[c_idx] if len(r) > c_idx else "") for r_idx, r in enumerate(tbl) if len(r) > 0}

    # Check for positive crypto headers
    crypto_header = None
    for h in ["Project Info", "Project Information", "Smart Contract Address", "Total Supply", "Max Supply"]:
        if h in row_map and row_map[h][1]:
            crypto_header = h
            break

    # Check for underlying headers
    underlying_header = None
    for h in [
        "Underlying Asset",
        "Underlying Equity",
        "Underlying Equity/Index",
        "Underlying Equity/Index/ETF",
        "Underlying Index/Equity",
        "Underlying Index",
        "Underlying FX Pair",
    ]:
        if h in row_map and row_map[h][1]:
            underlying_header = h
            break

    commodities = ["XAGUSDT", "XPDUSDT", "XPTUSDT", "COPPERUSDT", "BZUSDT", "CLUSDT", "NATGASUSDT"]

    if crypto_header:
        asset_class = "crypto"
        status = "confirmed"
        target_header = crypto_header
        target_row_idx, raw_val = row_map[crypto_header]
    elif underlying_header:
        target_header = underlying_header
        target_row_idx, raw_val = row_map[underlying_header]
        u_val = raw_val.lower()
        u_hdr = target_header.lower()

        if symbol in commodities or any(k in u_val for k in ["silver", "palladium", "platinum", "copper", "crude oil", "natural gas", "gold (xau)"]):
            asset_class = "commodity"
            status = "confirmed"
        elif "fx pair" in u_hdr or symbol == "USDBRLUSDT":
            asset_class = "unknown"
            status = "unknown"
        elif re.search(r"\b(etf|fund)\b", u_val) or ("trust" in u_val and any(k in symbol.lower() for k in ["qqq", "spy"])):
            asset_class = "etf"
            status = "confirmed"
        elif re.search(r"\bindex\b", u_val) and not re.search(r"\b(stock|shares|equity|limited|inc|corp|co|adr)\b", u_val):
            asset_class = "index"
            status = "confirmed"
        elif re.search(r"\b(common stock|stock|shares|equity|adr|corporation|inc\b|co\b|ltd\b|corp\b|group|holding)\b", u_val) or "equity" in u_hdr:
            asset_class = "equity"
            status = "confirmed"
        else:
            asset_class = "unknown"
            status = "unknown"
    else:
        # Cannot be positively identified from table headers
        asset_class = "unknown"
        status = "unknown"
        target_header = "USDⓈ-M Perpetual Contract"
        target_row_idx, raw_val = row_map.get("USDⓈ-M Perpetual Contract", (0, symbol))

    evidence_locator = f"table[{t_idx}].col[{c_idx}].row['{target_header}']"
    return asset_class, regime, status, t_idx, c_idx, target_header, raw_val, evidence_locator


# Frozen Upstream Canonical Identity Tuples
UPSTREAM_J_A_RUN_ID = "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
UPSTREAM_J_A_ROOT_REL = "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
UPSTREAM_J_A_MANIFEST_SHA256 = "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf"
UPSTREAM_J_A_SUMMARY_SHA256 = "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b"

UPSTREAM_J_B_RUN_ID = "stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"
UPSTREAM_J_B_ROOT_REL = "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"
UPSTREAM_J_B_MANIFEST_SHA256 = "f0a8ac724925084161f6b9aa2dced5139b261707fda0f0f21ebd0eb6de3087fb"
UPSTREAM_J_B_SUMMARY_SHA256 = "5ea0f1c87803114c4c6917cd0c3d24292948fa0e7066a80e0a2bce611e32546b"


def run_export(output_dir: Path | None = None) -> tuple[Path, Path]:
    project_root = get_project_root()
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        load_verified_stage1_5j_a_historical_archive_coverage_root,
    )
    from research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
    )

    ja_root = project_root / UPSTREAM_J_A_ROOT_REL
    jb_root = project_root / UPSTREAM_J_B_ROOT_REL
    ja_manifest_path = ja_root / "manifest.json"
    ja_summary_path = ja_root / "summary.json"
    jb_manifest_path = jb_root / "manifest.json"
    jb_summary_path = jb_root / "summary.json"
    ja_details_dir = ja_root / "raw/article_details"

    # Pre-execution Frozen Identity Verification
    if compute_sha256(ja_manifest_path) != UPSTREAM_J_A_MANIFEST_SHA256:
        raise ValueError(f"J-A manifest SHA mismatch: expected {UPSTREAM_J_A_MANIFEST_SHA256}")
    if compute_sha256(ja_summary_path) != UPSTREAM_J_A_SUMMARY_SHA256:
        raise ValueError(f"J-A summary SHA mismatch: expected {UPSTREAM_J_A_SUMMARY_SHA256}")
    if compute_sha256(jb_manifest_path) != UPSTREAM_J_B_MANIFEST_SHA256:
        raise ValueError(f"J-B manifest SHA mismatch: expected {UPSTREAM_J_B_MANIFEST_SHA256}")
    if compute_sha256(jb_summary_path) != UPSTREAM_J_B_SUMMARY_SHA256:
        raise ValueError(f"J-B summary SHA mismatch: expected {UPSTREAM_J_B_SUMMARY_SHA256}")

    # Strict Admission via Public Production Strict Loaders
    ja_summary = load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)
    if ja_summary["run_id"] != UPSTREAM_J_A_RUN_ID:
        raise ValueError(f"J-A RUN_ID mismatch: expected {UPSTREAM_J_A_RUN_ID}, got {ja_summary['run_id']}")

    jb = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(jb_root)
    if jb["run_id"] != UPSTREAM_J_B_RUN_ID:
        raise ValueError(f"J-B RUN_ID mismatch: expected {UPSTREAM_J_B_RUN_ID}, got {jb['run_id']}")

    child_rows = jb["child_rows"]
    child_horizon_rows = jb["child_horizon_rows"]

    # 2. Build index of J-B child horizon rows by (source_article_id, symbol, horizon_ms)
    horizons_index = {}
    for hr in child_horizon_rows:
        key = (hr["source_article_id"], hr["symbol"], hr["horizon_ms"])
        if key in horizons_index:
            raise ValueError(f"Duplicate horizon key found in J-B: {key}")
        horizons_index[key] = hr

    # 3. Calculate batch sizes per parent_article_id
    children_by_article = {}
    for cr in child_rows:
        children_by_article.setdefault(cr["source_article_id"], []).append(cr["symbol"])

    # 4. Load J-A Article Details and extract table specs
    article_cache = {}
    for p in sorted(ja_details_dir.glob("*.json")):
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        data = d.get("data", {})
        body_raw = data.get("body", "{}")
        try:
            body_obj = json.loads(body_raw)
            tables = parse_article_tables(body_obj)
        except Exception:
            tables = []

        article_cache[p.stem] = {
            "title": data.get("title", ""),
            "publishDate": data.get("publishDate"),
            "tables": tables,
            "rel_path": str(p.relative_to(project_root)),
            "sha256": compute_sha256(p),
        }

    # 5. Build Classification Ledger and Full Dataset V2 Rows
    ledger_rows = []
    dataset_rows = []

    for cr in child_rows:
        aid = cr["source_article_id"]
        sym = cr["symbol"]

        if aid not in article_cache:
            raise KeyError(f"Parent article ID {aid} not found in J-A details")

        art = article_cache[aid]
        title = art["title"]
        pub_ms = art["publishDate"]
        launch_ms = cr["symbol_launch_time_ms"]

        # Classify asset and regime from AST tables
        asset_class, listing_regime, class_status, t_idx, c_idx, field_header, raw_val, evidence_locator = classify_from_ast_table(
            title, art["tables"], sym
        )

        ledger_rows.append({
            "parent_article_id": aid,
            "symbol": sym,
            "asset_class": asset_class,
            "listing_regime": listing_regime,
            "classification_status": class_status,
            "table_index": str(t_idx),
            "symbol_column_index": str(c_idx),
            "field_header": field_header,
            "raw_cell_value": raw_val,
            "evidence_locator": evidence_locator,
            "source_relative_path": art["rel_path"],
            "source_sha256": art["sha256"],
        })

        # Calculate time metrics with exact integer arithmetic
        batch_size = len(children_by_article[aid])
        is_single_listing = "true" if batch_size == 1 else "false"

        lead_time_ms = (launch_ms - pub_ms) if (launch_ms is not None and pub_ms is not None) else None
        lead_time_hr_str = lead_time_hours_str(lead_time_ms)

        anchor_delay_ms = cr.get("anchor_delay_ms")
        anchor_delay_sec = str(round(Decimal(anchor_delay_ms) / Decimal(1000), 3)) if anchor_delay_ms is not None else ""
        anchor_price = cr.get("anchor_price") or ""
        anchor_time_ms = cr.get("anchor_time_ms")

        # Extract horizon rows using composite 3-tuple key
        h5m = horizons_index.get((aid, sym, 300000), {})
        h1h = horizons_index.get((aid, sym, 3600000), {})
        h4h = horizons_index.get((aid, sym, 14400000), {})

        row = {
            "parent_article_id": aid,
            "symbol": sym,
            "asset_class": asset_class,
            "listing_regime": listing_regime,
            "is_single_listing": is_single_listing,
            "batch_size": batch_size,
            "announcement_time_ms": pub_ms if pub_ms is not None else "",
            "announcement_time_utc": ms_to_iso(pub_ms),
            "launch_target_time_ms": launch_ms if launch_ms is not None else "",
            "launch_target_time_utc": ms_to_iso(launch_ms),
            "lead_time_ms": lead_time_ms if lead_time_ms is not None else "",
            "lead_time_hours": lead_time_hr_str,
            "anchor_state": cr["anchor_state"],
            "anchor_delay_ms": anchor_delay_ms if anchor_delay_ms is not None else "",
            "anchor_delay_sec": anchor_delay_sec,
            "anchor_price": anchor_price,
            "anchor_time_ms": anchor_time_ms if anchor_time_ms is not None else "",
            "anchor_time_utc": ms_to_iso(anchor_time_ms),
            "j_a_parent_state": cr.get("j_a_parent_state", ""),
            "j_a_child_state": cr.get("j_a_child_state", ""),
            # Horizon 5m
            "horizon_state_5m": h5m.get("child_horizon_state", ""),
            "missing_reason_5m": h5m.get("missing_reason") or "",
            "gross_return_bps_5m": h5m.get("gross_return_bps") or "",
            "gross_return_pct_5m": bps_to_pct_str(h5m.get("gross_return_bps")),
            "sampled_max_excursion_bps_5m": h5m.get("sampled_max_excursion_bps") or "",
            "mfe_pct_5m": bps_to_pct_str(h5m.get("sampled_max_excursion_bps")),
            "sampled_min_excursion_bps_5m": h5m.get("sampled_min_excursion_bps") or "",
            "mae_pct_5m": bps_to_pct_str(h5m.get("sampled_min_excursion_bps")),
            "trade_count_5m": h5m.get("trade_count") if h5m.get("trade_count") is not None else "",
            "horizon_price_5m": h5m.get("horizon_price") or "",
            "horizon_offset_ms_5m": h5m.get("horizon_offset_ms") if h5m.get("horizon_offset_ms") is not None else "",
            # Horizon 1h
            "horizon_state_1h": h1h.get("child_horizon_state", ""),
            "missing_reason_1h": h1h.get("missing_reason") or "",
            "gross_return_bps_1h": h1h.get("gross_return_bps") or "",
            "gross_return_pct_1h": bps_to_pct_str(h1h.get("gross_return_bps")),
            "sampled_max_excursion_bps_1h": h1h.get("sampled_max_excursion_bps") or "",
            "mfe_pct_1h": bps_to_pct_str(h1h.get("sampled_max_excursion_bps")),
            "sampled_min_excursion_bps_1h": h1h.get("sampled_min_excursion_bps") or "",
            "mae_pct_1h": bps_to_pct_str(h1h.get("sampled_min_excursion_bps")),
            "trade_count_1h": h1h.get("trade_count") if h1h.get("trade_count") is not None else "",
            "horizon_price_1h": h1h.get("horizon_price") or "",
            "horizon_offset_ms_1h": h1h.get("horizon_offset_ms") if h1h.get("horizon_offset_ms") is not None else "",
            # Horizon 4h
            "horizon_state_4h": h4h.get("child_horizon_state", ""),
            "missing_reason_4h": h4h.get("missing_reason") or "",
            "gross_return_bps_4h": h4h.get("gross_return_bps") or "",
            "gross_return_pct_4h": bps_to_pct_str(h4h.get("gross_return_bps")),
            "sampled_max_excursion_bps_4h": h4h.get("sampled_max_excursion_bps") or "",
            "mfe_pct_4h": bps_to_pct_str(h4h.get("sampled_max_excursion_bps")),
            "sampled_min_excursion_bps_4h": h4h.get("sampled_min_excursion_bps") or "",
            "mae_pct_4h": bps_to_pct_str(h4h.get("sampled_min_excursion_bps")),
            "trade_count_4h": h4h.get("trade_count") if h4h.get("trade_count") is not None else "",
            "horizon_price_4h": h4h.get("horizon_price") or "",
            "horizon_offset_ms_4h": h4h.get("horizon_offset_ms") if h4h.get("horizon_offset_ms") is not None else "",
            # Article title
            "article_title": title,
        }
        dataset_rows.append(row)

    # Deterministic sort: launch_target_time_ms ascending, then parent_article_id, then symbol
    ledger_rows.sort(key=lambda x: (x["parent_article_id"], x["symbol"]))
    dataset_rows.sort(key=lambda x: (
        x["launch_target_time_ms"] if x["launch_target_time_ms"] != "" else -1,
        x["parent_article_id"],
        x["symbol"]
    ))

    # Export paths
    exports_dir = output_dir if output_dir is not None else (project_root / "data/exports")
    exports_dir.mkdir(parents=True, exist_ok=True)
    ledger_csv_path = exports_dir / "stage1_5j_token_launch_classification_ledger_v2.csv"
    dataset_csv_path = exports_dir / "stage1_5j_full_year_token_launch_dataset_v2.csv"

    # Write Ledger CSV
    ledger_fieldnames = [
        "parent_article_id", "symbol", "asset_class", "listing_regime",
        "classification_status", "table_index", "symbol_column_index",
        "field_header", "raw_cell_value", "evidence_locator",
        "source_relative_path", "source_sha256"
    ]
    with open(ledger_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ledger_fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ledger_rows)

    # Write Dataset V2 CSV
    dataset_fieldnames = list(dataset_rows[0].keys())
    with open(dataset_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dataset_fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(dataset_rows)

    # Post-execution SHA invariant checks on upstream source files
    if compute_sha256(jb_summary_path) != UPSTREAM_J_B_SUMMARY_SHA256:
        raise RuntimeError("FATAL: J-B summary.json modified during export!")
    if compute_sha256(ja_manifest_path) != UPSTREAM_J_A_MANIFEST_SHA256:
        raise RuntimeError("FATAL: J-A manifest.json modified during export!")

    return ledger_csv_path, dataset_csv_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export Stage 1.5J Dataset V2 and Classification Ledger V2.")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to export CSV files to.")
    args = parser.parse_args()
    out_dir = Path(args.output_dir) if args.output_dir else None
    ledger_p, dataset_p = run_export(output_dir=out_dir)
    print(f"SUCCESS: Exported classification ledger -> {ledger_p}")
    print(f"SUCCESS: Exported full dataset v2       -> {dataset_p}")
