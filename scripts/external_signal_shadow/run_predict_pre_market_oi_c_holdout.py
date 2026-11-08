"""PREDICT pre-market OI scenario C single-event holdout runner.

Strictly adheres to:
- docs/designs/2026-11-07-predict-pre-market-oi-c-single-event-holdout-design_CN.md
- docs/plans/2026-11-07-predict-pre-market-oi-c-single-event-holdout-implementation-plan_CN.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np

from configs.stage1_5j_b_historical_aggtrades_launch_response import (
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES,
)
from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
    AggTradeRecord,
    OiMetricRecord,
    stream_aggtrades_csv_lines,
)
from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
    validate_aggtrades_csv_header,
    validate_zip_archive_package,
)

MAX_PHYSICAL_LINE_BYTES = 65_536

# Constant definitions
TARGET_PARENT_ID = "5ef55cf8358e4a48b2512a156e89c8e5"
TARGET_SYMBOL = "PREDICTUSDT"
TARGET_REGIME = "pre_market"
TARGET_SCENARIO = "C"
HISTORICAL_TRAINING_DATE_CUTOFF = "2026-04-16"
SCHEDULED_LAUNCH_TIME_STR = "2026-10-25 08:15:00 UTC"
SCHEDULED_LAUNCH_MS = 1792916100000  # 2026-10-25 08:15:00.000 UTC
OFFICIAL_ANNOUNCEMENT_URL = (
    "https://www.binance.com/en/support/announcement/detail/5ef55cf8358e4a48b2512a156e89c8e5"
)
BINANCE_VISION_BASE_URL = "https://data.binance.vision/data/futures/um/daily"

# Frozen authority identities per Design §2 / Plan §2
FROZEN_DESIGN_PATH = "docs/designs/2026-11-07-predict-pre-market-oi-c-single-event-holdout-design_CN.md"
FROZEN_DESIGN_SHA256 = "b7a8bc2eaeb3bbfe58a34fe026df84d06f0bbbe29c992e9f18970012ae7b131d"
FROZEN_PLAN_PATH = "docs/plans/2026-11-07-predict-pre-market-oi-c-single-event-holdout-implementation-plan_CN.md"
FROZEN_PLAN_SHA256 = "40b62906429ecba11d4d44350338efe3f41abcdc6e7a614c1e6d58f510e26692"
FROZEN_TRAINING_PANEL_PATH = "data/research_archives/launch_incremental_run_20261105/parent_panel.csv"
FROZEN_TRAINING_PANEL_SHA256 = "1396b1f0c34bbb99d936abf13a7a99f44863eb300c9fc35b4fbeefffee6faac2"
FROZEN_REVIEW_PATH = "data/research_archives/launch_incremental_run_20261105/review_CN.md"
FROZEN_REVIEW_SHA256 = "5f57a97d249c24c06656ee42dff4982fab1cc63742095f4ec16abb701ee3338d"
FROZEN_CONSUMER_PATH = "scripts/external_signal_shadow/run_predict_pre_market_oi_c_holdout.py"

FROZEN_ZIP_SHA256: dict[str, str] = {
    "PREDICTUSDT-aggTrades-2026-10-25.zip": "a25d07cd093a9251f69730e0ed9a1371fcb17f6cb94d4f360067ed7ca5d06ba4",
    "PREDICTUSDT-metrics-2026-10-25.zip": "0eff530f194d3b61996b1b5b149639a3550f2684a4f14ed1d9c4a63c29564df3",
    "PREDICTUSDT-aggTrades-2026-10-26.zip": "fc640042973f3c5238a14ae0d5d4f42f7e0f5c7d17fca4b798f8bd96adaeec95",
    "PREDICTUSDT-metrics-2026-10-26.zip": "c2ea538180af560b26021d9888bdbf04d2c9e25327e979adee618d692ab5e6cb",
}

EXPECTED_PANEL_HEADER = (
    "parent_article_id",
    "listing_regime",
    "scenario",
    "utc_date",
    "child_symbols",
    "required_child_count",
    "scenario_complete_child_count",
    "oi_complete",
    "basis_complete",
    "missing_reasons",
    "p",
    "o",
    "b",
    "y",
    "long_mae",
    "long_mfe",
)

HOLDOUT_CASE_HEADER = (
    "parent_article_id",
    "symbol",
    "listing_regime",
    "scenario",
    "scheduled_launch_utc",
    "t0_utc",
    "t0_delay_ms",
    "case_status",
    "missing_reason",
    "model_freeze_sha256",
    "plan_sha256",
    "code_sha256",
    "schedule_source_url",
    "schedule_source_version",
    "schedule_revision_notes",
    "early_trades_explanation",
    "early_trades_count",
    "earliest_trade_id",
    "earliest_trade_utc",
    "t0_trade_id",
    "t0_price",
    "d_utc",
    "baseline_last_trade_id",
    "baseline_last_trade_utc",
    "baseline_last_price",
    "l0_time",
    "l1_time",
    "l0_oi",
    "l1_oi",
    "p",
    "o",
    "entry_trade_id",
    "entry_time_utc",
    "entry_price",
    "endpoint_trade_id",
    "endpoint_time_utc",
    "endpoint_price",
    "y",
    "long_mae",
    "long_mfe",
    "z_p",
    "z_o",
    "prediction_M0",
    "prediction_M1",
    "error_M0",
    "error_M1",
    "abs_error_M0",
    "abs_error_M1",
    "sq_error_M0",
    "sq_error_M1",
    "d",
    "p_out_of_bounds",
    "o_out_of_bounds",
    "extrapolation_warning",
    "historical_scenario_only",
    "real_pit_verified",
    "hypothesis_only",
    "no_alpha_claim",
)


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Enforces HTTPS and strictly blocks cross-domain redirects away from data.binance.vision."""

    def redirect_request(
        self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> urllib.request.Request | None:
        parsed = urlparse(newurl)
        if parsed.scheme != "https" or parsed.netloc != "data.binance.vision":
            raise urllib.error.HTTPError(
                newurl, code, f"STOP=cross_domain_or_insecure_redirect_rejected:{newurl}", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _compute_file_sha256(path: Path) -> str:
    """Stream file SHA-256 calculation with 64KB chunking."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_training_panel(path: Path, expected_sha256: str) -> list[dict[str, Any]]:
    """Load and strictly validate the historical training panel."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"STOP=panel_not_found:{path}")

    actual_sha = _compute_file_sha256(path)
    if actual_sha != expected_sha256:
        raise ValueError(f"STOP=hash_mismatch:expected={expected_sha256}:actual={actual_sha}")

    text = path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("STOP=panel_empty")

    reader = csv.reader(lines)
    header = next(reader)
    if tuple(header) != EXPECTED_PANEL_HEADER:
        raise ValueError(f"STOP=header_mismatch:expected={EXPECTED_PANEL_HEADER}:actual={tuple(header)}")

    rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for row_idx, row in enumerate(reader, start=2):
        if len(row) != len(EXPECTED_PANEL_HEADER):
            raise ValueError(f"STOP=row_field_count_mismatch:line={row_idx}")

        rec = dict(zip(EXPECTED_PANEL_HEADER, row))
        # Filter strictly for pre_market scenario C with oi_complete=true
        if rec["listing_regime"] != TARGET_REGIME or rec["scenario"] != TARGET_SCENARIO:
            continue
        if rec["oi_complete"].strip().lower() != "true":
            continue

        pid = rec["parent_article_id"].strip()
        regime = rec["listing_regime"].strip()
        scen = rec["scenario"].strip()
        utc_date = rec["utc_date"].strip()
        child_symbols = rec["child_symbols"].strip()

        # Check composite key uniqueness
        comp_key = (pid, regime, scen)
        if comp_key in seen_keys:
            raise ValueError(f"STOP=duplicate_composite_key:{comp_key}")
        seen_keys.add(comp_key)

        # Check date validity and cutoff
        try:
            parsed_dt = datetime.strptime(utc_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValueError(f"STOP=invalid_utc_date_format:{utc_date}")

        if parsed_dt > datetime(2026, 4, 16, tzinfo=timezone.utc):
            raise ValueError(f"STOP=date_out_of_bounds:date={utc_date}>cutoff={HISTORICAL_TRAINING_DATE_CUTOFF}")

        # Check PREDICT exclusion
        if pid == TARGET_PARENT_ID or TARGET_SYMBOL in child_symbols:
            raise ValueError(f"STOP=predict_in_training:parent={pid}")

        # Check child denominators
        try:
            req_c = int(rec["required_child_count"])
            comp_c = int(rec["scenario_complete_child_count"])
        except ValueError:
            raise ValueError(f"STOP=invalid_child_count:line={row_idx}")

        if req_c <= 0 or req_c != comp_c:
            raise ValueError(f"STOP=incomplete_children:req={req_c}:comp={comp_c}")

        if rec["missing_reasons"].strip():
            raise ValueError(f"STOP=non_empty_missing_reasons:{rec['missing_reasons']}")

        # Numerical fields
        try:
            p_val = float(rec["p"])
            o_val = float(rec["o"])
            y_val = float(rec["y"])
            mae_val = float(rec["long_mae"])
            mfe_val = float(rec["long_mfe"])
        except ValueError:
            raise ValueError(f"STOP=non_numeric_fields:line={row_idx}")

        for val_name, v in [("p", p_val), ("o", o_val), ("y", y_val), ("mae", mae_val), ("mfe", mfe_val)]:
            if not math.isfinite(v):
                raise ValueError(f"STOP=non_finite_{val_name}:{v}")

        rows.append(
            {
                "parent_article_id": pid,
                "listing_regime": regime,
                "scenario": scen,
                "utc_date": utc_date,
                "child_symbols": child_symbols,
                "p": p_val,
                "o": o_val,
                "y": y_val,
                "long_mae": mae_val,
                "long_mfe": mfe_val,
            }
        )

    if len(rows) != 18:
        raise ValueError(f"STOP=row_count_mismatch:expected=18:actual={len(rows)}")

    # Sort rows by parent_article_id for determinism
    rows.sort(key=lambda r: r["parent_article_id"])
    return rows


def fit_models(
    p_train: np.ndarray,
    o_train: np.ndarray,
    y_train: np.ndarray,
) -> dict[str, Any]:
    """Fit M0 and M1 OLS models and compute standardization statistics."""
    n_samples = len(p_train)
    if n_samples < 8:
        return {
            "freeze_status": "not_estimable",
            "reason": "insufficient_samples",
            "coef_m0": None,
            "coef_m1": None,
            "mu_p": None,
            "sigma_p": None,
            "mu_o": None,
            "sigma_o": None,
            "rank_m0": None,
            "rank_m1": None,
        }

    mu_p = float(np.mean(p_train))
    mu_o = float(np.mean(o_train))

    var_p = float(np.var(p_train, ddof=0))
    var_o = float(np.var(o_train, ddof=0))

    if var_p <= 0.0 or var_o <= 0.0:
        return {
            "freeze_status": "not_estimable",
            "reason": "zero_variance",
            "coef_m0": None,
            "coef_m1": None,
            "mu_p": mu_p,
            "sigma_p": math.sqrt(max(0.0, var_p)),
            "mu_o": mu_o,
            "sigma_o": math.sqrt(max(0.0, var_o)),
            "rank_m0": None,
            "rank_m1": None,
        }

    sigma_p = math.sqrt(var_p)
    sigma_o = math.sqrt(var_o)

    z_p = (p_train - mu_p) / sigma_p
    z_o = (o_train - mu_o) / sigma_o
    z_inter = z_p * z_o

    # Design matrix M0: [1, z_p]
    X_m0 = np.column_stack([np.ones(n_samples), z_p])
    # Design matrix M1: [1, z_p, z_o, z_p*z_o]
    X_m1 = np.column_stack([np.ones(n_samples), z_p, z_o, z_inter])

    rank_m0 = int(np.linalg.matrix_rank(X_m0))
    rank_m1 = int(np.linalg.matrix_rank(X_m1))

    if rank_m0 < 2 or rank_m1 < 4:
        return {
            "freeze_status": "not_estimable",
            "reason": f"rank_deficient:m0={rank_m0}<2:m1={rank_m1}<4",
            "coef_m0": None,
            "coef_m1": None,
            "mu_p": mu_p,
            "sigma_p": sigma_p,
            "mu_o": mu_o,
            "sigma_o": sigma_o,
            "rank_m0": rank_m0,
            "rank_m1": rank_m1,
        }

    coef_m0, _, _, _ = np.linalg.lstsq(X_m0, y_train, rcond=None)
    coef_m1, _, _, _ = np.linalg.lstsq(X_m1, y_train, rcond=None)

    for c in list(coef_m0) + list(coef_m1):
        if not math.isfinite(float(c)):
            return {
                "freeze_status": "not_estimable",
                "reason": "non_finite_coefficients",
                "coef_m0": None,
                "coef_m1": None,
                "mu_p": mu_p,
                "sigma_p": sigma_p,
                "mu_o": mu_o,
                "sigma_o": sigma_o,
                "rank_m0": rank_m0,
                "rank_m1": rank_m1,
            }

    return {
        "freeze_status": "frozen",
        "mu_p": mu_p,
        "sigma_p": sigma_p,
        "mu_o": mu_o,
        "sigma_o": sigma_o,
        "coef_m0": [float(c) for c in coef_m0],
        "coef_m1": [float(c) for c in coef_m1],
        "rank_m0": rank_m0,
        "rank_m1": rank_m1,
    }


def parse_aggtrades_zip(
    zip_path: Path, expected_sha256: str, expected_symbol: str, expected_date: str
) -> list[AggTradeRecord]:
    """Parse aggTrades daily ZIP archive into list of AggTradeRecord."""
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise ValueError(f"STOP=zip_not_found:{zip_path}")

    actual_sha = _compute_file_sha256(zip_path)
    if actual_sha != expected_sha256:
        raise ValueError(f"STOP=hash_mismatch:expected={expected_sha256}:actual={actual_sha}")

    if not validate_zip_archive_package(zip_path):
        raise ValueError(f"STOP=invalid_zip_archive_package:{zip_path}")

    expected_filename = f"{expected_symbol}-aggTrades-{expected_date}.csv"
    with zipfile.ZipFile(zip_path, "r") as zf:
        infolist = zf.infolist()
        if len(infolist) != 1 or infolist[0].filename != expected_filename:
            raise ValueError(f"STOP=invalid_zip_entry:expected={expected_filename}")

        with zf.open(infolist[0]) as raw_f:
            lines = stream_aggtrades_csv_lines(raw_f, max_line_bytes=MAX_PHYSICAL_LINE_BYTES)
            header_line = next(lines, None)
            if header_line is None:
                raise ValueError("STOP=empty_aggtrades_csv")

            header_fields = header_line.split(",")
            if not validate_aggtrades_csv_header(header_fields):
                raise ValueError(f"STOP=invalid_aggtrades_csv_header:{header_fields}")

            trades: list[AggTradeRecord] = []
            prev_trade_id = -1
            prev_transact_time = -1

            for line_str in lines:
                if not line_str.strip():
                    continue

                parts = line_str.split(",")
                if len(parts) != 7:
                    raise ValueError(f"STOP=invalid_trade_fields_count:{len(parts)}")

                try:
                    tid = int(parts[0])
                    price = float(parts[1])
                    qty = float(parts[2])
                    f_id = int(parts[3])
                    l_id = int(parts[4])
                    tt = int(parts[5])
                except ValueError:
                    raise ValueError("STOP=invalid_trade_number_format")

                bm_str = parts[6].strip().lower()
                if bm_str not in ("true", "false"):
                    raise ValueError(f"STOP=invalid_buyer_maker:{parts[6]}")
                is_buyer_maker = bm_str == "true"

                if tid < 0 or f_id < 0 or l_id < 0 or tt < 0:
                    raise ValueError("STOP=negative_id_or_time")
                if f_id > l_id:
                    raise ValueError("STOP=first_trade_id_greater_than_last")
                if price <= 0.0 or not math.isfinite(price) or qty <= 0.0 or not math.isfinite(qty):
                    raise ValueError("STOP=invalid_price_or_qty")

                # Sequence checks: id strictly increasing, time non-decreasing
                if tid <= prev_trade_id:
                    raise ValueError("STOP=trade_id_not_strictly_increasing")
                if tt < prev_transact_time:
                    raise ValueError("STOP=transact_time_not_non_decreasing")

                prev_trade_id = tid
                prev_transact_time = tt

                # Date check
                dt = datetime.fromtimestamp(tt / 1000.0, tz=timezone.utc)
                if dt.strftime("%Y-%m-%d") != expected_date:
                    raise ValueError(f"STOP=trade_date_mismatch:{dt.strftime('%Y-%m-%d')}!={expected_date}")

                trades.append(
                    AggTradeRecord(
                        transact_time_ms=tt,
                        trade_id=tid,
                        price=price,
                        quantity=qty,
                        is_buyer_maker=is_buyer_maker,
                    )
                )

    return trades


def parse_metrics_zip(
    zip_path: Path, expected_sha256: str, expected_symbol: str, expected_date: str
) -> list[OiMetricRecord]:
    """Parse 5m OI metrics daily ZIP archive into list of OiMetricRecord."""
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise ValueError(f"STOP=zip_not_found:{zip_path}")

    actual_sha = _compute_file_sha256(zip_path)
    if actual_sha != expected_sha256:
        raise ValueError(f"STOP=hash_mismatch:expected={expected_sha256}:actual={actual_sha}")

    if not validate_zip_archive_package(zip_path):
        raise ValueError(f"STOP=invalid_zip_archive_package:{zip_path}")

    expected_filename = f"{expected_symbol}-metrics-{expected_date}.csv"
    with zipfile.ZipFile(zip_path, "r") as zf:
        infolist = zf.infolist()
        if len(infolist) != 1 or infolist[0].filename != expected_filename:
            raise ValueError(f"STOP=invalid_zip_entry:expected={expected_filename}")

        with zf.open(infolist[0]) as raw_f:
            lines = stream_aggtrades_csv_lines(raw_f, max_line_bytes=MAX_PHYSICAL_LINE_BYTES)
            header_line = next(lines, None)
            if header_line is None:
                raise ValueError("STOP=empty_metrics_csv")

            cols = [c.strip() for c in header_line.split(",")]
            if len(cols) != len(set(cols)):
                raise ValueError(f"STOP=duplicate_metrics_columns:{header_line}")

            for req_col in ("create_time", "symbol", "sum_open_interest"):
                if req_col not in cols:
                    raise ValueError(f"STOP=missing_metrics_column:{req_col}")

            idx_time = cols.index("create_time")
            idx_sym = cols.index("symbol")
            idx_oi = cols.index("sum_open_interest")

            records: list[OiMetricRecord] = []
            seen_times: set[int] = set()

            for line_str in lines:
                if not line_str.strip():
                    continue

                parts = [p.strip() for p in line_str.split(",")]
                if len(parts) != len(cols):
                    raise ValueError(f"STOP=metrics_field_count_mismatch:{len(parts)}!={len(cols)}")

                sym_val = parts[idx_sym]
                if sym_val != expected_symbol:
                    raise ValueError(f"STOP=metrics_symbol_mismatch:{sym_val}!={expected_symbol}")

                time_str = parts[idx_time]
                try:
                    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                except ValueError:
                    raise ValueError(f"STOP=invalid_metrics_time_format:{time_str}")

                if dt.strftime("%Y-%m-%d") != expected_date:
                    raise ValueError(f"STOP=metrics_date_mismatch:{dt.strftime('%Y-%m-%d')}!={expected_date}")

                # Check 5m grid alignment: minute % 5 == 0, second == 0
                if dt.minute % 5 != 0 or dt.second != 0:
                    raise ValueError(f"STOP=metrics_not_on_5m_grid:{time_str}")

                t_ms = int(dt.timestamp() * 1000)
                if t_ms in seen_times:
                    raise ValueError(f"STOP=duplicate_metrics_timestamp:{time_str}")
                seen_times.add(t_ms)

                try:
                    oi_val = float(parts[idx_oi])
                except ValueError:
                    raise ValueError(f"STOP=invalid_oi_number_format:{parts[idx_oi]}")

                if not math.isfinite(oi_val) or oi_val < 0.0:
                    raise ValueError(f"STOP=invalid_oi_value:{oi_val}")

                records.append(
                    OiMetricRecord(
                        create_time_ms=t_ms,
                        symbol=sym_val,
                        sum_open_interest=oi_val,
                    )
                )

    records.sort(key=lambda r: r.create_time_ms)
    return records


def download_official_inputs(
    approved_inputs: dict[str, str],
    inputs_dir: Path,
    timeout_sec: int = 30,
) -> None:
    """Download official Binance Vision ZIP archives and .CHECKSUM files."""
    inputs_dir.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(SafeRedirectHandler())

    for filename, expected_sha in approved_inputs.items():
        if filename not in FROZEN_ZIP_SHA256:
            raise ValueError(f"STOP=unapproved_input_filename:{filename}")
        if expected_sha != FROZEN_ZIP_SHA256[filename]:
            raise ValueError(f"STOP=input_sha_mismatch:{filename}")

        kind = "aggTrades" if "aggTrades" in filename else "metrics"
        url = f"{BINANCE_VISION_BASE_URL}/{kind}/{TARGET_SYMBOL}/{filename}"
        checksum_url = f"{url}.CHECKSUM"

        # 1. Download official .CHECKSUM
        req_ck = urllib.request.Request(checksum_url, headers={"User-Agent": "AntigravityResearch/1.0"})
        with opener.open(req_ck, timeout=timeout_sec) as resp:
            status_code = getattr(resp, "status", getattr(resp, "code", 200))
            if status_code != 200:
                raise ValueError(f"STOP=checksum_download_http_error:{status_code}")
            ck_bytes = resp.read(MAX_PHYSICAL_LINE_BYTES + 1)
            if len(ck_bytes) > MAX_PHYSICAL_LINE_BYTES:
                raise ValueError("STOP=checksum_size_exceeded")
            ck_text = ck_bytes.decode("utf-8").strip()

        ck_parts = ck_text.split()
        if len(ck_parts) < 2 or ck_parts[0] != expected_sha or ck_parts[1] != filename:
            raise ValueError(f"STOP=checksum_content_mismatch:expected=({expected_sha}, {filename}):actual={ck_parts}")

        (inputs_dir / f"{filename}.CHECKSUM").write_text(ck_text + "\n", encoding="utf-8")

        # 2. Stream download ZIP
        dest_zip = inputs_dir / filename
        h = hashlib.sha256()
        total_downloaded = 0
        req_zip = urllib.request.Request(url, headers={"User-Agent": "AntigravityResearch/1.0"})
        with opener.open(req_zip, timeout=timeout_sec) as resp:
            status_code = getattr(resp, "status", getattr(resp, "code", 200))
            if status_code != 200:
                raise ValueError(f"STOP=zip_download_http_error:{status_code}")
            with open(dest_zip, "wb") as out_f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    total_downloaded += len(chunk)
                    if total_downloaded > EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES:
                        raise ValueError(
                            f"STOP=zip_max_bytes_exceeded:{total_downloaded}>{EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES}"
                        )
                    h.update(chunk)
                    out_f.write(chunk)

        actual_sha = h.hexdigest()
        if actual_sha != expected_sha:
            dest_zip.unlink(missing_ok=True)
            raise ValueError(f"STOP=downloaded_zip_hash_mismatch:expected={expected_sha}:actual={actual_sha}")


def build_case_features(
    trades: list[AggTradeRecord],
    oi_records: list[OiMetricRecord],
    scheduled_launch_ms: int = SCHEDULED_LAUNCH_MS,
    schedule_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract single-event holdout features strictly following Scenario C rules."""
    if schedule_evidence is None:
        schedule_evidence = {}

    base_info: dict[str, Any] = {
        "case_status": None,
        "missing_reason": None,
        "schedule_source_url": schedule_evidence.get("source_url"),
        "schedule_source_version": schedule_evidence.get("version_verification_status"),
        "schedule_revision_notes": schedule_evidence.get("version_notes"),
        "early_trades_explanation": schedule_evidence.get("early_trades_explanation"),
        "early_trades_count": None,
        "earliest_trade_ms": None,
        "earliest_trade_id": None,
        "t0_ms": None,
        "t0_trade_id": None,
        "t0_price": None,
        "t0_delay_ms": None,
        "d_ms": None,
        "baseline_last_trade_id": None,
        "baseline_last_trade_ms": None,
        "baseline_last_price": None,
        "p": None,
        "o": None,
        "y": None,
        "long_mae": None,
        "long_mfe": None,
        "l0_time": None,
        "l1_time": None,
        "l0_oi": None,
        "l1_oi": None,
        "entry_trade_id": None,
        "entry_time_ms": None,
        "entry_price": None,
        "endpoint_trade_id": None,
        "endpoint_time_ms": None,
        "endpoint_price": None,
    }

    # Strict schedule evidence validation per Design §4.1 / Plan §2
    source_url = schedule_evidence.get("source_url")
    ver_status = schedule_evidence.get("version_verification_status")
    ver_notes = schedule_evidence.get("version_notes")
    app_conclusion = schedule_evidence.get("applicability_conclusion")
    sched_utc = schedule_evidence.get("scheduled_launch_utc")

    if (
        source_url != OFFICIAL_ANNOUNCEMENT_URL
        or ver_status != "verified"
        or not ver_notes
        or app_conclusion != "applicable"
        or sched_utc != SCHEDULED_LAUNCH_TIME_STR
    ):
        base_info["case_status"] = "anchor_or_regime_conflict"
        base_info["missing_reason"] = "schedule_evidence_insufficient_or_untrusted"
        return base_info

    if not trades:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = "no_trades_provided"
        return base_info

    early_trades = [t for t in trades if t.transact_time_ms < scheduled_launch_ms]
    base_info["early_trades_count"] = len(early_trades)
    if early_trades:
        base_info["earliest_trade_ms"] = early_trades[0].transact_time_ms
        base_info["earliest_trade_id"] = early_trades[0].trade_id
        early_expl = schedule_evidence.get("early_trades_explanation")
        if not early_expl or not schedule_evidence.get("early_trades_source"):
            base_info["case_status"] = "anchor_or_regime_conflict"
            base_info["missing_reason"] = "early_trades_unexplained"
            return base_info
    else:
        base_info["earliest_trade_ms"] = trades[0].transact_time_ms
        base_info["earliest_trade_id"] = trades[0].trade_id

    # Anchor trade selection
    trades_after_s = [t for t in trades if t.transact_time_ms >= scheduled_launch_ms]
    if not trades_after_s:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = "no_trades_after_scheduled_launch"
        return base_info

    anchor = trades_after_s[0]
    delay_ms = anchor.transact_time_ms - scheduled_launch_ms
    base_info["t0_ms"] = anchor.transact_time_ms
    base_info["t0_trade_id"] = anchor.trade_id
    base_info["t0_price"] = anchor.price
    base_info["t0_delay_ms"] = delay_ms

    if delay_ms > EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = f"anchor_delay_exceeded:delay={delay_ms}>max={EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS}"
        return base_info

    t0_ms = anchor.transact_time_ms
    d_ms = t0_ms + 25 * 60 * 1000  # T0 + 25m
    base_info["d_ms"] = d_ms

    # Baseline price return p over [T0, D)
    base_trades = [t for t in trades if t0_ms <= t.transact_time_ms < d_ms]
    if not base_trades:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = "no_baseline_trades"
        return base_info

    p_start = base_trades[0].price
    last_base_trade = base_trades[-1]
    p_end = last_base_trade.price
    base_info["baseline_last_trade_id"] = last_base_trade.trade_id
    base_info["baseline_last_trade_ms"] = last_base_trade.transact_time_ms
    base_info["baseline_last_price"] = p_end

    p_raw = 0.0 if len(base_trades) == 1 else (p_end / p_start - 1.0)
    base_info["p"] = float(f"{p_raw:.8f}")

    # Scenario C OI selection: cutoff <= D - 15m = T0 + 10m
    oi_cutoff_ms = d_ms - 15 * 60 * 1000
    valid_oi_in_window = [r for r in oi_records if t0_ms <= r.create_time_ms <= oi_cutoff_ms]
    if not valid_oi_in_window:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = "no_oi_records_in_scenario_c_window"
        return base_info

    # L1 is the latest timestamp in the window
    l1_record = valid_oi_in_window[-1]
    l0_ms = l1_record.create_time_ms - 5 * 60 * 1000
    if l0_ms < t0_ms:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = f"scenario_c_predecessor_before_t0:l0={l0_ms}<t0={t0_ms}"
        return base_info

    l0_candidates = [r for r in oi_records if r.create_time_ms == l0_ms]
    if not l0_candidates:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = f"scenario_c_predecessor_missing:l0={l0_ms}"
        return base_info

    l0_record = l0_candidates[0]
    if l0_record.sum_open_interest <= 0.0 or l1_record.sum_open_interest <= 0.0:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = "non_positive_oi_pair"
        return base_info

    o_raw = l1_record.sum_open_interest / l0_record.sum_open_interest - 1.0
    base_info["o"] = float(f"{o_raw:.8f}")
    base_info["l0_time"] = datetime.fromtimestamp(l0_record.create_time_ms / 1000.0, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    base_info["l1_time"] = datetime.fromtimestamp(l1_record.create_time_ms / 1000.0, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    base_info["l0_oi"] = l0_record.sum_open_interest
    base_info["l1_oi"] = l1_record.sum_open_interest

    # Entry selection: first trade in [D, D + 5s]
    d_plus_5s = d_ms + 5 * 1000
    entry_candidates = [t for t in trades if d_ms <= t.transact_time_ms <= d_plus_5s]
    if not entry_candidates:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = "no_entry_trades_in_5s_window"
        return base_info

    entry_trade = entry_candidates[0]
    base_info["entry_trade_id"] = entry_trade.trade_id
    base_info["entry_time_ms"] = entry_trade.transact_time_ms
    base_info["entry_price"] = entry_trade.price

    # Endpoint selection: last trade in [E - 1s, E], where E = entry_time + 15m
    e_ms = entry_trade.transact_time_ms + 15 * 60 * 1000
    e_minus_1s = e_ms - 1000
    endpoint_candidates = [t for t in trades if e_minus_1s <= t.transact_time_ms <= e_ms]
    if not endpoint_candidates:
        base_info["case_status"] = "data_gap"
        base_info["missing_reason"] = "no_endpoint_trades_in_1s_window"
        return base_info

    endpoint_trade = endpoint_candidates[-1]
    base_info["endpoint_trade_id"] = endpoint_trade.trade_id
    base_info["endpoint_time_ms"] = endpoint_trade.transact_time_ms
    base_info["endpoint_price"] = endpoint_trade.price

    # Price return y
    y_raw = endpoint_trade.price / entry_trade.price - 1.0
    base_info["y"] = float(f"{y_raw:.8f}")

    # MAE & MFE along the path [entry, endpoint]
    path_trades = [
        t for t in trades if entry_trade.transact_time_ms <= t.transact_time_ms <= endpoint_trade.transact_time_ms
    ]
    if not path_trades:
        base_info["long_mae"] = 0.0
        base_info["long_mfe"] = 0.0
    else:
        returns = [t.price / entry_trade.price - 1.0 for t in path_trades]
        min_ret = min(returns)
        max_ret = max(returns)
        base_info["long_mae"] = float(f"{min(0.0, min_ret):.8f}")
        base_info["long_mfe"] = float(f"{max(0.0, max_ret):.8f}")

    base_info["case_status"] = "ready_for_scoring"
    return base_info


def score_case(
    case_features: dict[str, Any],
    frozen_model: dict[str, Any],
) -> dict[str, Any]:
    """Score a single event using pre-frozen model parameters."""
    res = dict(case_features)
    if res.get("case_status") != "ready_for_scoring":
        res["z_p"] = None
        res["z_o"] = None
        res["prediction_M0"] = None
        res["prediction_M1"] = None
        res["error_M0"] = None
        res["error_M1"] = None
        res["abs_error_M0"] = None
        res["abs_error_M1"] = None
        res["sq_error_M0"] = None
        res["sq_error_M1"] = None
        res["d"] = None
        res["p_out_of_bounds"] = None
        res["o_out_of_bounds"] = None
        res["extrapolation_warning"] = None
        return res

    mu_p = frozen_model["mu_p"]
    sigma_p = frozen_model["sigma_p"]
    mu_o = frozen_model["mu_o"]
    sigma_o = frozen_model["sigma_o"]
    coef_m0 = frozen_model["coef_m0"]
    coef_m1 = frozen_model["coef_m1"]

    p = res["p"]
    o = res["o"]
    y = res["y"]

    z_p = (p - mu_p) / sigma_p
    z_o = (o - mu_o) / sigma_o
    z_inter = z_p * z_o

    pred_m0 = coef_m0[0] + coef_m0[1] * z_p
    pred_m1 = coef_m1[0] + coef_m1[1] * z_p + coef_m1[2] * z_o + coef_m1[3] * z_inter

    err_m0 = y - pred_m0
    err_m1 = y - pred_m1
    abs_err_m0 = abs(err_m0)
    abs_err_m1 = abs(err_m1)
    sq_err_m0 = err_m0**2
    sq_err_m1 = err_m1**2
    d = sq_err_m0 - sq_err_m1

    res["case_status"] = "scored"
    res["z_p"] = float(z_p)
    res["z_o"] = float(z_o)
    res["prediction_M0"] = float(pred_m0)
    res["prediction_M1"] = float(pred_m1)
    res["error_M0"] = float(err_m0)
    res["error_M1"] = float(err_m1)
    res["abs_error_M0"] = float(abs_err_m0)
    res["abs_error_M1"] = float(abs_err_m1)
    res["sq_error_M0"] = float(sq_err_m0)
    res["sq_error_M1"] = float(sq_err_m1)
    res["d"] = float(d)
    res["extrapolation_warning"] = bool(pred_m0 < -1.0 or pred_m1 < -1.0)
    return res


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for PREDICT holdout execution."""
    parser = argparse.ArgumentParser(description="PREDICT single-event holdout runner")
    parser.add_argument("--auth-file", required=True, help="Path to JSON authorization file")
    parser.add_argument("--output-dir", required=True, help="Path to brand new output directory")
    args = parser.parse_args(argv)

    auth_path = Path(args.auth_file)
    out_dir = Path(args.output_dir)

    if not auth_path.is_file():
        print(f"ERROR: auth file not found: {auth_path}", file=sys.stderr)
        return 1

    try:
        auth = json.loads(auth_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: invalid auth json: {e}", file=sys.stderr)
        return 1

    # Security check: trading permissions must be explicitly present and False
    for p_key in ("signal_allowed", "execution_allowed", "paper_trading_allowed", "live_trading_allowed"):
        if p_key not in auth or auth[p_key] is not False:
            print(f"ERROR: trading permission {p_key} must be explicitly False", file=sys.stderr)
            return 1

    # Section 2 boundaries must be explicitly accepted
    if not auth.get("section_2_boundaries_accepted", False):
        print("ERROR: section_2_boundaries_accepted must be True", file=sys.stderr)
        return 1

    current_code_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    # Consumer identity check
    if "consumer_path" not in auth or "consumer_sha256" not in auth:
        print("ERROR: missing consumer identity in auth", file=sys.stderr)
        return 1
    if auth["consumer_path"] != FROZEN_CONSUMER_PATH:
        print(
            f"ERROR: consumer_path mismatch: expected={FROZEN_CONSUMER_PATH}:actual={auth['consumer_path']}",
            file=sys.stderr,
        )
        return 1
    if auth["consumer_sha256"] != current_code_sha:
        print(
            f"ERROR: consumer_sha256 mismatch: expected={current_code_sha}:actual={auth['consumer_sha256']}",
            file=sys.stderr,
        )
        return 1

    # Validate required auth keys
    for req_key in (
        "plan_path",
        "design_path",
        "plan_sha256",
        "design_sha256",
        "training_panel_path",
        "training_panel_sha256",
        "training_review_path",
        "training_review_sha256",
        "inputs_dir",
        "allowed_actions",
    ):
        if req_key not in auth:
            print(f"ERROR: missing required auth key: {req_key}", file=sys.stderr)
            return 1

    # Verify frozen identity bindings
    if auth["plan_path"] != FROZEN_PLAN_PATH or auth["plan_sha256"] != FROZEN_PLAN_SHA256:
        print("ERROR: plan path or sha256 mismatch vs frozen authority", file=sys.stderr)
        return 1
    if auth["design_path"] != FROZEN_DESIGN_PATH or auth["design_sha256"] != FROZEN_DESIGN_SHA256:
        print("ERROR: design path or sha256 mismatch vs frozen authority", file=sys.stderr)
        return 1
    if auth["training_panel_path"] != FROZEN_TRAINING_PANEL_PATH or auth["training_panel_sha256"] != FROZEN_TRAINING_PANEL_SHA256:
        print("ERROR: training panel path or sha256 mismatch vs frozen authority", file=sys.stderr)
        return 1
    if auth["training_review_path"] != FROZEN_REVIEW_PATH or auth["training_review_sha256"] != FROZEN_REVIEW_SHA256:
        print("ERROR: training review path or sha256 mismatch vs frozen authority", file=sys.stderr)
        return 1

    plan_path = Path(auth["plan_path"])
    design_path = Path(auth["design_path"])
    review_path = Path(auth["training_review_path"])

    if not plan_path.is_file() or not design_path.is_file() or not review_path.is_file():
        print("ERROR: plan, design, or companion review path not found on disk", file=sys.stderr)
        return 1

    if _compute_file_sha256(plan_path) != auth["plan_sha256"]:
        print("ERROR: plan file on disk sha mismatch", file=sys.stderr)
        return 1
    if _compute_file_sha256(design_path) != auth["design_sha256"]:
        print("ERROR: design file on disk sha mismatch", file=sys.stderr)
        return 1
    if _compute_file_sha256(review_path) != auth["training_review_sha256"]:
        print("ERROR: training review file on disk sha mismatch", file=sys.stderr)
        return 1

    # Authorized output root binding check
    auth_root_str = auth.get("batch_root") or auth.get("authorized_output_root")
    if not auth_root_str:
        print("ERROR: missing batch_root/authorized_output_root in auth", file=sys.stderr)
        return 1
    if out_dir.resolve() != Path(auth_root_str).resolve():
        print(f"ERROR: output_dir does not match authorized root: {out_dir} != {auth_root_str}", file=sys.stderr)
        return 1

    # Check output directory does not exist
    if out_dir.exists():
        print(f"ERROR: output_dir already exists: {out_dir}", file=sys.stderr)
        return 1

    # Reject symlinks in output path and all non-system ancestors
    raw_out = Path(args.output_dir).absolute()
    for parent in [raw_out, *raw_out.parents]:
        if str(parent) in ("/", "/var", "/tmp", "/etc", "/private", "/private/var", "/private/tmp"):
            continue
        if parent.is_symlink():
            print(f"ERROR: symlink in output path rejected: {parent}", file=sys.stderr)
            return 1

    allowed_actions = set(auth["allowed_actions"])
    if not allowed_actions.issubset({"freeze_model", "download_inputs", "score_case"}):
        print(f"ERROR: unknown actions: {allowed_actions}", file=sys.stderr)
        return 1

    inputs_dir = Path(auth["inputs_dir"])
    training_panel_path = Path(auth["training_panel_path"])

    resolved_out = out_dir.resolve()
    resolved_inputs = inputs_dir.resolve()
    resolved_training = training_panel_path.parent.resolve()

    # Path check: download_inputs requires inputs_dir to be exactly out_dir / "inputs"
    # When not downloading, inputs_dir is external and must not contain or be contained in out_dir
    if "download_inputs" in allowed_actions:
        expected_download_dir = (out_dir / "inputs").resolve()
        if resolved_inputs != expected_download_dir:
            print(
                f"ERROR: when download_inputs is enabled, inputs_dir must be batch_root/inputs: {resolved_inputs} != {expected_download_dir}",
                file=sys.stderr,
            )
            return 1
    else:
        if resolved_out == resolved_inputs or resolved_out in resolved_inputs.parents or resolved_inputs in resolved_out.parents:
            print(f"ERROR: output_dir contains or is contained in read-only input dir: {resolved_inputs}", file=sys.stderr)
            return 1

    # Training panel directory must always be separate from output directory
    if resolved_out == resolved_training or resolved_out in resolved_training.parents or resolved_training in resolved_out.parents:
        print(f"ERROR: output_dir contains or is contained in training panel dir: {resolved_training}", file=sys.stderr)
        return 1

    # Create output directory
    try:
        out_dir.mkdir(parents=True, exist_ok=False)
    except Exception as e:
        print(f"ERROR: failed to create output directory: {e}", file=sys.stderr)
        return 1

    # STEP 1: Model Freeze
    if "freeze_model" not in allowed_actions:
        print("ERROR: freeze_model action required", file=sys.stderr)
        return 1

    expected_panel_sha = auth["training_panel_sha256"]
    try:
        training_rows = load_training_panel(training_panel_path, expected_panel_sha)
    except Exception as e:
        print(f"ERROR: training panel loading failed: {e}", file=sys.stderr)
        return 1

    p_arr = np.array([r["p"] for r in training_rows], dtype=np.float64)
    o_arr = np.array([r["o"] for r in training_rows], dtype=np.float64)
    y_arr = np.array([r["y"] for r in training_rows], dtype=np.float64)

    fit_dict = fit_models(p_arr, o_arr, y_arr)

    min_p_train = float(min(r["p"] for r in training_rows))
    max_p_train = float(max(r["p"] for r in training_rows))
    min_o_train = float(min(r["o"] for r in training_rows))
    max_o_train = float(max(r["o"] for r in training_rows))

    all_dates = [r["utc_date"] for r in training_rows]
    min_date = min(all_dates)
    max_date = max(all_dates)

    # Write model_freeze.json BEFORE any new content I/O
    freeze_json_path = out_dir / "model_freeze.json"
    freeze_data = {
        "freeze_status": fit_dict["freeze_status"],
        "design_sha256": auth["design_sha256"],
        "plan_sha256": auth["plan_sha256"],
        "code_sha256": current_code_sha,
        "training_panel_path": str(training_panel_path),
        "training_panel_sha256": expected_panel_sha,
        "training_review_path": str(review_path),
        "training_review_sha256": auth["training_review_sha256"],
        "training_parents": [r["parent_article_id"] for r in training_rows],
        "training_child_symbols": [r["child_symbols"] for r in training_rows],
        "training_date_range": {
            "start": min_date,
            "end": max_date,
        },
        "p_train_bounds": {"min": min_p_train, "max": max_p_train},
        "o_train_bounds": {"min": min_o_train, "max": max_o_train},
        "scenario": TARGET_SCENARIO,
        "scenario_timing_protocol": {
            "cutoff_offset_minutes": 10,
            "publication_allowance_minutes": 5,
            "total_offset_minutes": 15,
        },
        "column_order_m0": ["1", "z_p"],
        "column_order_m1": ["1", "z_p", "z_o", "z_p*z_o"],
        "mu_p": fit_dict.get("mu_p"),
        "sigma_p": fit_dict.get("sigma_p"),
        "mu_o": fit_dict.get("mu_o"),
        "sigma_o": fit_dict.get("sigma_o"),
        "coef_m0": fit_dict.get("coef_m0"),
        "coef_m1": fit_dict.get("coef_m1"),
        "rank_m0": fit_dict.get("rank_m0"),
        "rank_m1": fit_dict.get("rank_m1"),
        "n_samples": len(training_rows),
        "utc_frozen_time": datetime.now(timezone.utc).isoformat(),
        "prior_exposure_disclosure": auth.get("prior_exposure_disclosure", "unknown"),
    }
    freeze_bytes = json.dumps(freeze_data, indent=2).encode("utf-8")
    try:
        freeze_json_path.write_bytes(freeze_bytes)
    except Exception as e:
        print(f"ERROR: failed to write model_freeze.json: {e}", file=sys.stderr)
        return 1
    model_freeze_sha = hashlib.sha256(freeze_bytes).hexdigest()

    # If model is not estimable, output un-scored case and exit cleanly
    if fit_dict["freeze_status"] != "frozen":
        unscored_case = {
            "case_status": "not_estimable",
            "missing_reason": fit_dict.get("reason", "model_not_estimable"),
        }
        try:
            _write_holdout_case_csv(out_dir / "holdout_case.csv", unscored_case, model_freeze_sha, auth["plan_sha256"], current_code_sha)
            _write_review_md(out_dir / "review_CN.md", unscored_case, model_freeze_sha, auth, current_code_sha)
        except Exception as e:
            print(f"ERROR: failed to write output files: {e}", file=sys.stderr)
            return 1
        return 0

    # STEP 2: Consume new event content (only after freeze!)
    if "score_case" not in allowed_actions:
        return 0

    # Download branch if requested
    if "download_inputs" in allowed_actions:
        if auth.get("network_allowed") is not True:
            print("ERROR: network_allowed must be True when download_inputs is requested", file=sys.stderr)
            return 1
        approved_inputs = auth.get("approved_inputs", {})
        try:
            download_official_inputs(approved_inputs, inputs_dir)
        except Exception as e:
            print(f"ERROR: download_official_inputs failed: {e}", file=sys.stderr)
            return 1

    approved_inputs = auth.get("approved_inputs", {})
    agg_filename = "PREDICTUSDT-aggTrades-2026-10-25.zip"
    metrics_filename = "PREDICTUSDT-metrics-2026-10-25.zip"

    if agg_filename not in approved_inputs or metrics_filename not in approved_inputs:
        print("ERROR: approved_inputs missing required archive filenames", file=sys.stderr)
        return 1

    if approved_inputs[agg_filename] != FROZEN_ZIP_SHA256[agg_filename]:
        print(f"ERROR: unapproved aggTrades sha256: {approved_inputs[agg_filename]}", file=sys.stderr)
        return 1
    if approved_inputs[metrics_filename] != FROZEN_ZIP_SHA256[metrics_filename]:
        print(f"ERROR: unapproved metrics sha256: {approved_inputs[metrics_filename]}", file=sys.stderr)
        return 1

    agg_path = inputs_dir / agg_filename
    metrics_path = inputs_dir / metrics_filename

    try:
        trades = parse_aggtrades_zip(agg_path, approved_inputs[agg_filename], TARGET_SYMBOL, "2026-10-25")
        metrics = parse_metrics_zip(metrics_path, approved_inputs[metrics_filename], TARGET_SYMBOL, "2026-10-25")
    except Exception as e:
        print(f"ERROR: archive parsing failed: {e}", file=sys.stderr)
        return 1

    schedule_evidence = auth.get("schedule_evidence", {})
    case_features = build_case_features(trades, metrics, scheduled_launch_ms=SCHEDULED_LAUNCH_MS, schedule_evidence=schedule_evidence)

    # Attach verified archive file metadata
    case_features["aggtrades_filename"] = agg_filename
    case_features["aggtrades_sha256"] = approved_inputs[agg_filename]
    case_features["metrics_filename"] = metrics_filename
    case_features["metrics_sha256"] = approved_inputs[metrics_filename]

    # Step 3: Score case strictly using parameters loaded from frozen model file on disk
    freeze_bytes_on_disk = freeze_json_path.read_bytes()
    current_freeze_sha = hashlib.sha256(freeze_bytes_on_disk).hexdigest()
    if current_freeze_sha != model_freeze_sha:
        print("ERROR: model_freeze.json modified after creation", file=sys.stderr)
        return 1

    try:
        frozen_model_loaded = json.loads(freeze_bytes_on_disk.decode("utf-8"))
    except Exception as e:
        print(f"ERROR: failed to parse frozen model json: {e}", file=sys.stderr)
        return 1

    scored_case = score_case(case_features, frozen_model_loaded)
    if scored_case.get("case_status") == "scored":
        p_val = scored_case["p"]
        o_val = scored_case["o"]
        scored_case["p_out_of_bounds"] = bool(p_val < min_p_train or p_val > max_p_train)
        scored_case["o_out_of_bounds"] = bool(o_val < min_o_train or o_val > max_o_train)
    else:
        scored_case["p_out_of_bounds"] = None
        scored_case["o_out_of_bounds"] = None

    # Step 4: Write CSV and Review
    try:
        _write_holdout_case_csv(
            out_dir / "holdout_case.csv",
            scored_case,
            model_freeze_sha,
            auth["plan_sha256"],
            current_code_sha,
        )
        _write_review_md(out_dir / "review_CN.md", scored_case, model_freeze_sha, auth, current_code_sha)
    except Exception as e:
        print(f"ERROR: failed to write output files: {e}", file=sys.stderr)
        return 1

    return 0


def _format_cell(val: Any) -> str:
    """Format single CSV cell without invented fallback values."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val)


def _format_utc(ms: int | None) -> str:
    """Format UTC millisecond timestamp with millisecond precision."""
    if ms is None:
        return ""
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"


def _write_holdout_case_csv(
    csv_path: Path,
    case: dict[str, Any],
    model_freeze_sha: str,
    plan_sha: str,
    code_sha: str,
) -> None:
    """Write exact 1-row holdout_case.csv."""
    case_status = case.get("case_status", "unknown")
    missing_reason = case.get("missing_reason", "")

    row_dict = {
        "parent_article_id": TARGET_PARENT_ID,
        "symbol": TARGET_SYMBOL,
        "listing_regime": TARGET_REGIME,
        "scenario": TARGET_SCENARIO,
        "scheduled_launch_utc": SCHEDULED_LAUNCH_TIME_STR,
        "t0_utc": _format_utc(case.get("t0_ms")),
        "t0_delay_ms": _format_cell(case.get("t0_delay_ms")),
        "case_status": case_status,
        "missing_reason": missing_reason,
        "model_freeze_sha256": model_freeze_sha,
        "plan_sha256": plan_sha,
        "code_sha256": code_sha,
        "schedule_source_url": _format_cell(case.get("schedule_source_url")),
        "schedule_source_version": _format_cell(case.get("schedule_source_version")),
        "schedule_revision_notes": _format_cell(case.get("schedule_revision_notes")),
        "early_trades_explanation": _format_cell(case.get("early_trades_explanation")),
        "early_trades_count": _format_cell(case.get("early_trades_count")),
        "earliest_trade_id": _format_cell(case.get("earliest_trade_id")),
        "earliest_trade_utc": _format_utc(case.get("earliest_trade_ms")),
        "t0_trade_id": _format_cell(case.get("t0_trade_id")),
        "t0_price": _format_cell(case.get("t0_price")),
        "d_utc": _format_utc(case.get("d_ms")),
        "baseline_last_trade_id": _format_cell(case.get("baseline_last_trade_id")),
        "baseline_last_trade_utc": _format_utc(case.get("baseline_last_trade_ms")),
        "baseline_last_price": _format_cell(case.get("baseline_last_price")),
        "l0_time": _format_cell(case.get("l0_time")),
        "l1_time": _format_cell(case.get("l1_time")),
        "l0_oi": _format_cell(case.get("l0_oi")),
        "l1_oi": _format_cell(case.get("l1_oi")),
        "p": _format_cell(case.get("p")),
        "o": _format_cell(case.get("o")),
        "entry_trade_id": _format_cell(case.get("entry_trade_id")),
        "entry_time_utc": _format_utc(case.get("entry_time_ms")),
        "entry_price": _format_cell(case.get("entry_price")),
        "endpoint_trade_id": _format_cell(case.get("endpoint_trade_id")),
        "endpoint_time_utc": _format_utc(case.get("endpoint_time_ms")),
        "endpoint_price": _format_cell(case.get("endpoint_price")),
        "y": _format_cell(case.get("y")),
        "long_mae": _format_cell(case.get("long_mae")),
        "long_mfe": _format_cell(case.get("long_mfe")),
        "z_p": _format_cell(case.get("z_p")),
        "z_o": _format_cell(case.get("z_o")),
        "prediction_M0": _format_cell(case.get("prediction_M0")),
        "prediction_M1": _format_cell(case.get("prediction_M1")),
        "error_M0": _format_cell(case.get("error_M0")),
        "error_M1": _format_cell(case.get("error_M1")),
        "abs_error_M0": _format_cell(case.get("abs_error_M0")),
        "abs_error_M1": _format_cell(case.get("abs_error_M1")),
        "sq_error_M0": _format_cell(case.get("sq_error_M0")),
        "sq_error_M1": _format_cell(case.get("sq_error_M1")),
        "d": _format_cell(case.get("d")),
        "p_out_of_bounds": _format_cell(case.get("p_out_of_bounds")),
        "o_out_of_bounds": _format_cell(case.get("o_out_of_bounds")),
        "extrapolation_warning": _format_cell(case.get("extrapolation_warning")),
        "historical_scenario_only": "true",
        "real_pit_verified": "false",
        "hypothesis_only": "true",
        "no_alpha_claim": "true",
    }

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HOLDOUT_CASE_HEADER)
        writer.writeheader()
        writer.writerow(row_dict)


def _write_review_md(
    md_path: Path,
    case: dict[str, Any],
    model_freeze_sha: str,
    auth: dict[str, Any],
    code_sha: str,
) -> None:
    """Write human-readable review report."""
    case_status = case.get("case_status", "unknown")
    is_scored = case_status == "scored"
    missing_count = 0 if is_scored else 1

    archive_lines: list[str] = []
    approved_inputs = auth.get("approved_inputs")
    if isinstance(approved_inputs, dict):
        for fname in sorted(approved_inputs.keys()):
            label = "aggTrades" if "aggTrades" in fname else ("metrics" if "metrics" in fname else "input")
            archive_sha = approved_inputs[fname]
            archive_lines.append(f"- **Holdout {label} Archive**: `{fname}` (SHA-256: `{archive_sha}`)")

    lines = [
        "# PREDICT 盘前 OI 情景 C 单事件留出检查报告",
        "",
        f"- **Parent ID**: `{TARGET_PARENT_ID}`",
        f"- **Symbol**: `{TARGET_SYMBOL}`",
        f"- **Listing Regime**: `{TARGET_REGIME}`",
        f"- **Scenario**: `{TARGET_SCENARIO}`",
        f"- **Case Status**: `{case_status}`",
        "- **Universe Count**: 1",
        f"- **Scored Count**: {1 if is_scored else 0}",
        f"- **Missing Count**: {missing_count}",
        "",
        "## 1. 身份与绑定信息",
        f"- **Model Freeze Artifact**: `model_freeze.json` (SHA-256: `{model_freeze_sha}`)",
        f"- **Plan SHA-256**: `{auth['plan_sha256']}`",
        f"- **Design SHA-256**: `{auth['design_sha256']}`",
        f"- **Code SHA-256**: `{code_sha}`",
        f"- **Training Panel**: `{auth['training_panel_path']}` (SHA-256: `{auth['training_panel_sha256']}`)",
        f"- **Training Review**: `{auth['training_review_path']}` (SHA-256: `{auth['training_review_sha256']}`)",
        f"- **Consumer Script**: `{auth['consumer_path']}` (SHA-256: `{auth['consumer_sha256']}`)",
        *archive_lines,
        "",
        "## 2. 计划时间与来源核验依据",
        f"- **官方公告 URL**: `{OFFICIAL_ANNOUNCEMENT_URL}`",
        f"- **计划开盘时间 (S)**: `{SCHEDULED_LAUNCH_TIME_STR}`",
        f"- **来源版本核验状态**: `{case.get('schedule_source_version', '')}`",
        f"- **版本/修订说明**: `{case.get('schedule_revision_notes', '')}`",
        f"- **提前成交解释**: `{case.get('early_trades_explanation', '')}`",
        "",
        "## 3. 预测与评估结果",
    ]

    if is_scored:
        lines.extend(
            [
                f"- **实际收益 y**: `{case.get('y')}`",
                f"- **M0 (基准) 预测值**: `{case.get('prediction_M0')}` | **误差**: `{case.get('error_M0')}` | **绝对误差**: `{case.get('abs_error_M0')}`",
                f"- **M1 (扩展) 预测值**: `{case.get('prediction_M1')}` | **误差**: `{case.get('error_M1')}` | **绝对误差**: `{case.get('abs_error_M1')}`",
                f"- **平方误差改善量 d**: `{case.get('d')}`",
                f"- **MAE**: `{case.get('long_mae')}` | **MFE**: `{case.get('long_mfe')}`",
                f"- **外推警告**: `{case.get('extrapolation_warning')}`",
            ]
        )
    else:
        lines.extend(
            [
                f"- **缺失原因**: `{case.get('missing_reason', '')}`",
            ]
        )

    lines.extend(
        [
            "",
            "## 4. 审慎性声明与情景限制",
            "- 本报告仅记录单个后续事件的样本外观测；",
            "- 单事件平方误差改善量 d 不构成统计显著性检验，不代表总体 Alpha 成立；",
            "- `historical_scenario_only`: true；",
            "- `real_pit_verified`: false；",
            "- `hypothesis_only`: true；",
            "- `no_alpha_claim`: true；",
            "- `RISK_LIVE_TRADING_ENABLED` 保持 `False`，无任何交易或执行授权。",
            "- `batch_status=completed`",
            "",
        ]
    )

    md_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
