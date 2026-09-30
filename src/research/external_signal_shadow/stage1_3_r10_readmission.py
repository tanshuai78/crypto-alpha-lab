from __future__ import annotations

import ast
import fcntl
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research.external_signal_shadow.stage1_3_models import (
    STAGE1_3_BAR_INTERVAL_MS,
    HistoricalBar,
    compute_bar_coverage,
    find_duplicate_bar_starts,
)

# ─── APPROVED AUTHORITY CONSTANTS ──────────────────────────────────────────

APPROVED_DESIGN_PATH = "docs/designs/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-design_CN.md"
APPROVED_DESIGN_SHA256 = "1b5088316f4f7dd28424ae37702f7b78d6c5e5b4fb3f873e73282f6137619446"
APPROVED_PLAN_PATH = "docs/plans/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-implementation-plan_CN.md"
APPROVED_PLAN_SHA256 = "7e79731b03fd7db76ae1cc2e75c7de4c1f461d9e057ef8532f6c5f38bf3f5e72"
HISTORICAL_REVIEW_COMMIT = "b122dc0700446990b43cc6fe9f613bf76bc8025c"

FROZEN_AUTHORITIES = (
    ("docs/reviews/2026-09-27-historical-alpha-methodology-audit_CN.md", "61ba2f7acb88b91db9f23a2f9f085bc493d52160d6ee411978573cb96d9f3ac4"),
    ("docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md", "a404b54b141a5a18914c3b34ae5168e4565699d0929a324464cbca27e89546bf"),
    ("reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json", "4c27cd2504e9b9660cf4c418fd80b4f00b91655c6adebce3ade36643178d51d5"),
    ("src/research/external_signal_shadow/stage1_3_summary.py", "6528259eee07e9a82f8bc2a6b3511d5822cf362944f745bd0f296c7977dd3276"),
    ("src/research/external_signal_shadow/stage1_3_candidates.py", "2c59224742a0041f2cbe2930f0b58e142155c9e0a9d134fd69181195219c10b6"),
    ("scripts/run_external_signal_shadow_stage1_3_candidate_discovery.py", "f2ba0454cc8eae23afbb58d2ef7d1e091c4457830f932d9ac60f592405f7f080"),
    (".agent/rules/L2_Alpha_Research_Methodology.md", "806314e860bbf94d0e4332377d8bf617471f31dfcb51ffab1b646220ba8aed27"),
)

STAGE1_3_R10_CANDIDATE_NAMES = ("volume_spike_1h", "relative_strength_vs_btc")
STAGE1_3_R10_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
STAGE1_3_R10_TOTAL_BAR_COUNT = 86400
STAGE1_3_R10_HISTORY_DAYS = 180
STAGE1_3_R10_BARS_PER_SYMBOL = 17280

STAGE1_3_R10_DENY_VECTOR_KEYS = (
    "RISK_LIVE_TRADING_ENABLED",
    "alpha_interpretation_allowed",
    "alpha_candidate_allowed",
    "alpha_validated_allowed",
    "network_collection_allowed",
    "replay_allowed",
    "point_in_time_directional_replay_allowed",
    "private_api_allowed",
    "authenticated_api_allowed",
    "order_api_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_engine_allowed",
    "execution_feasibility_claim_allowed",
    "net_cost_or_profit_claim_allowed",
    "deployment_allowed",
    "ssh_allowed",
    "commit_allowed",
    "push_allowed",
)

FORBIDDEN_IDENTIFIERS = (
    "stage1_3_orchestrator",
    "stage1_3_replay",
    "stage1_3_metrics",
    "stage1_3_baseline",
    "run_stage1_3_candidate_discovery",
    "compute_forward_metrics_from_entry_index",
    "run_random_baseline_trials",
    "urllib.request",
    "requests",
    "aiohttp",
    "httpx",
    "socket",
)


def _sha256_file(path: str | Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_authorities(
    approved_design_path: str = APPROVED_DESIGN_PATH,
    approved_design_sha256: str = APPROVED_DESIGN_SHA256,
    approved_plan_path: str = APPROVED_PLAN_PATH,
    approved_plan_sha256: str = APPROVED_PLAN_SHA256,
    *,
    check_git: bool = True,
    repo_root: Path | None = None,
    git_dir: Path | None = None,
    boundary_commit: str = HISTORICAL_REVIEW_COMMIT,
) -> bool:
    root = repo_root or Path.cwd()
    target_git_dir = git_dir or root

    design_p = root / approved_design_path
    if design_p.is_symlink() or not design_p.is_file():
        raise RuntimeError("STOP=approved_authority_mismatch:design_not_regular_file")
    if _sha256_file(design_p) != approved_design_sha256:
        raise RuntimeError("STOP=stage1_3_r10_readmission_design_approval_mismatch")

    plan_p = root / approved_plan_path
    if plan_p.is_symlink() or not plan_p.is_file():
        raise RuntimeError("STOP=approved_authority_mismatch:plan_not_regular_file")
    if _sha256_file(plan_p) != approved_plan_sha256:
        raise RuntimeError("STOP=approved_authority_mismatch")

    for rel_path, expected_hash in FROZEN_AUTHORITIES:
        target_p = root / rel_path
        if target_p.is_symlink() or not target_p.is_file():
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_authority_mismatch:{rel_path}:not_regular")
        actual_hash = _sha256_file(target_p)
        if actual_hash != expected_hash:
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_authority_mismatch:{rel_path}")

    # Check RISK_LIVE_TRADING_ENABLED
    try:
        import configs.base
        if getattr(configs.base, "RISK_LIVE_TRADING_ENABLED", None) is not False:
            raise RuntimeError("STOP=stage1_3_r10_readmission_authority_mismatch:live_trading_not_disabled")
    except Exception as e:
        if "STOP=" in str(e):
            raise
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_authority_mismatch:config_check_failed:{e}") from e

    if check_git:
        boundary = boundary_commit
        res_cat = subprocess.run(["git", "cat-file", "-e", f"{boundary}^{{commit}}"], cwd=target_git_dir, capture_output=True)
        if res_cat.returncode != 0:
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_authority_mismatch:boundary_commit_missing:{boundary}")

        # Check boundary review blob
        res_rev = subprocess.run(
            ["git", "show", f"{boundary}:docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md"],
            cwd=target_git_dir,
            capture_output=True,
        )
        if res_rev.returncode != 0 or hashlib.sha256(res_rev.stdout).hexdigest() != "a404b54b141a5a18914c3b34ae5168e4565699d0929a324464cbca27e89546bf":
            raise RuntimeError("STOP=stage1_3_r10_readmission_authority_mismatch:boundary_review_blob_mismatch")

        # Check boundary summary blob
        res_sum = subprocess.run(
            ["git", "show", f"{boundary}:reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json"],
            cwd=target_git_dir,
            capture_output=True,
        )
        if res_sum.returncode != 0 or hashlib.sha256(res_sum.stdout).hexdigest() != "4c27cd2504e9b9660cf4c418fd80b4f00b91655c6adebce3ade36643178d51d5":
            raise RuntimeError("STOP=stage1_3_r10_readmission_authority_mismatch:boundary_summary_blob_mismatch")

    return True


# ─── HISTORICAL MANIFEST SNAPSHOT & READER ────────────────────────────────

HISTORICAL_MANIFEST_EXACT_KEYS = (
    "schema_version",
    "historical_run_identity",
    "historical_venue",
    "venue_proxy_used",
    "symbols",
    "interval",
    "history_days",
    "bar_count",
    "bars_sha256",
    "bars_byte_length",
    "event_ledger_sha256",
    "event_ledger_byte_length",
)


@dataclass(frozen=True)
class HistoricalManifestSnapshot:
    manifest_git_commit: str
    manifest_git_path: str
    manifest_blob_sha256: str
    historical_run_identity: str
    bars_sha256: str
    bars_byte_length: int
    event_ledger_sha256: str
    event_ledger_byte_length: int


def read_historical_manifest_from_git(
    commit_oid: str | None,
    manifest_path: str | None,
    *,
    boundary_commit: str = HISTORICAL_REVIEW_COMMIT,
    repo_root: Path | None = None,
) -> HistoricalManifestSnapshot | None:
    if commit_oid is None and manifest_path is None:
        return None
    if (commit_oid is None) != (manifest_path is None):
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:partial_manifest_flags")

    assert commit_oid is not None
    assert manifest_path is not None

    root = repo_root or Path.cwd()

    # Verify boundary commit blobs
    res_rev = subprocess.run(
        ["git", "show", f"{boundary_commit}:docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md"],
        cwd=root,
        capture_output=True,
    )
    if res_rev.returncode != 0 or hashlib.sha256(res_rev.stdout).hexdigest() != "a404b54b141a5a18914c3b34ae5168e4565699d0929a324464cbca27e89546bf":
        raise RuntimeError("STOP=stage1_3_r10_readmission_authority_mismatch:boundary_review_blob_mismatch")

    res_sum = subprocess.run(
        ["git", "show", f"{boundary_commit}:reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json"],
        cwd=root,
        capture_output=True,
    )
    if res_sum.returncode != 0 or hashlib.sha256(res_sum.stdout).hexdigest() != "4c27cd2504e9b9660cf4c418fd80b4f00b91655c6adebce3ade36643178d51d5":
        raise RuntimeError("STOP=stage1_3_r10_readmission_authority_mismatch:boundary_summary_blob_mismatch")

    # Validate commit_oid regex (exact 40 lowercase hex)
    if not re.match(r"^[0-9a-f]{40}$", commit_oid):
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_historical_anchor_invalid:invalid_commit_format:{commit_oid}")

    res_rev_parse = subprocess.run(
        ["git", "rev-parse", "--verify", f"{commit_oid}^{{commit}}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if res_rev_parse.returncode != 0:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_historical_anchor_invalid:commit_rev_parse_failed:{commit_oid}")

    resolved_full_oid = res_rev_parse.stdout.strip()
    if resolved_full_oid != commit_oid:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_historical_anchor_invalid:commit_oid_mismatch:{resolved_full_oid}!={commit_oid}")

    if commit_oid == boundary_commit:
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_commit_equals_boundary")

    res_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit_oid, boundary_commit],
        cwd=root,
        capture_output=True,
    )
    if res_ancestor.returncode != 0:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_historical_anchor_invalid:not_an_ancestor_of_boundary:{commit_oid}")

    # Read git blob
    res_blob = subprocess.run(
        ["git", "show", f"{commit_oid}:{manifest_path}"],
        cwd=root,
        capture_output=True,
    )
    if res_blob.returncode != 0:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_historical_anchor_invalid:git_show_failed:{commit_oid}:{manifest_path}")

    blob_sha256 = hashlib.sha256(res_blob.stdout).hexdigest()
    try:
        data = json.loads(res_blob.stdout.decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_json_decode_failed:{e}") from e

    # Schema validation
    if set(data.keys()) != set(HISTORICAL_MANIFEST_EXACT_KEYS):
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:keys")

    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:schema_version")
    if type(data["historical_run_identity"]) is not str or not data["historical_run_identity"]:
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:historical_run_identity")
    if data["historical_venue"] != "binance_proxy":
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:historical_venue")
    if type(data["venue_proxy_used"]) is not bool or data["venue_proxy_used"] is not True:
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:venue_proxy_used")
    if data["symbols"] != list(STAGE1_3_R10_SYMBOLS):
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:symbols")
    if data["interval"] != "15m":
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:interval")
    if type(data["history_days"]) is not int or data["history_days"] != 180:
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:history_days")
    if type(data["bar_count"]) is not int or data["bar_count"] != 86400:
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:bar_count")
    if not isinstance(data["bars_sha256"], str) or not re.match(r"^[0-9a-f]{64}$", data["bars_sha256"]):
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:bars_sha256")
    if type(data["bars_byte_length"]) is not int or data["bars_byte_length"] <= 0:
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:bars_byte_length")
    if not isinstance(data["event_ledger_sha256"], str) or not re.match(r"^[0-9a-f]{64}$", data["event_ledger_sha256"]):
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:event_ledger_sha256")
    if type(data["event_ledger_byte_length"]) is not int or data["event_ledger_byte_length"] <= 0:
        raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid:event_ledger_byte_length")

    return HistoricalManifestSnapshot(
        manifest_git_commit=commit_oid,
        manifest_git_path=manifest_path,
        manifest_blob_sha256=blob_sha256,
        historical_run_identity=data["historical_run_identity"],
        bars_sha256=data["bars_sha256"],
        bars_byte_length=data["bars_byte_length"],
        event_ledger_sha256=data["event_ledger_sha256"],
        event_ledger_byte_length=data["event_ledger_byte_length"],
    )


# ─── STRUCTURAL BARS PARSER & DATA TYPE ────────────────────────────────────

@dataclass(frozen=True)
class StructuralBarsSnapshot:
    bars_sha256: str
    bars_byte_length: int
    bar_count: int
    symbol_coverage: dict[str, float]
    time_index: tuple[tuple[str, int, int], ...]


def read_structural_bars(bars_path: str | Path) -> StructuralBarsSnapshot:
    p = Path(bars_path)
    if p.is_symlink():
        raise RuntimeError("STOP=stage1_3_r10_readmission_input_invalid:symlink_detected")
    if not p.is_file():
        raise RuntimeError("STOP=stage1_3_r10_readmission_input_invalid:not_regular_file")

    hasher = hashlib.sha256()
    total_bytes = 0
    bars: list[HistoricalBar] = []
    required_symbols_set = set(STAGE1_3_R10_SYMBOLS)

    try:
        with open(p, "rb") as f:
            for line_bytes in f:
                hasher.update(line_bytes)
                total_bytes += len(line_bytes)
                line_str = line_bytes.decode("utf-8").strip()
                if not line_str:
                    continue
                row_dict = json.loads(line_str)
                # HistoricalBar construction validates 15m duration, positive prices, valid high/low, non-negative volume
                bar = HistoricalBar(
                    symbol=row_dict["symbol"],
                    bar_start_ms=int(row_dict["bar_start_ms"]),
                    bar_end_ms=int(row_dict["bar_end_ms"]),
                    open_price=float(row_dict["open_price"]),
                    high_price=float(row_dict["high_price"]),
                    low_price=float(row_dict["low_price"]),
                    close_price=float(row_dict["close_price"]),
                    quote_volume=float(row_dict["quote_volume"]),
                )
                if bar.symbol not in required_symbols_set:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_input_invalid:symbol_universe_mismatch:{bar.symbol}")
                bars.append(bar)
    except Exception as e:
        if "STOP=" in str(e):
            raise
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_input_invalid:bars_parse_failed:{e}") from e

    # Check duplicate bar starts
    duplicates = find_duplicate_bar_starts(bars)
    if duplicates:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_input_invalid:duplicate_bar_start:{list(duplicates.keys())}")

    # Require exact total count
    if len(bars) != STAGE1_3_R10_TOTAL_BAR_COUNT:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_input_invalid:bar_count_mismatch:expected_{STAGE1_3_R10_TOTAL_BAR_COUNT}_got_{len(bars)}")

    # Check coverage
    coverage = compute_bar_coverage(bars, interval_ms=STAGE1_3_BAR_INTERVAL_MS)
    if set(coverage.keys()) != required_symbols_set:
        raise RuntimeError("STOP=stage1_3_r10_readmission_input_invalid:coverage_symbols_mismatch")
    for sym, cov in coverage.items():
        if cov < 0.98:
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_input_invalid:insufficient_coverage:{sym}_{cov}")

    # Verify 180-day span (180 days * 24h * 3600s * 1000ms = 15,552,000,000 ms)
    expected_span_ms = STAGE1_3_R10_HISTORY_DAYS * 24 * 3600 * 1000
    for sym in required_symbols_set:
        sym_bars = [b for b in bars if b.symbol == sym]
        sym_bars_sorted = sorted(sym_bars, key=lambda b: b.bar_start_ms)
        actual_span_ms = sym_bars_sorted[-1].bar_end_ms - sym_bars_sorted[0].bar_start_ms
        if actual_span_ms != expected_span_ms:
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_input_invalid:span_mismatch:{sym}_{actual_span_ms}_expected_{expected_span_ms}")

    # Build time_index without any OHLCV or raw rows
    time_index = tuple((b.symbol, b.bar_start_ms, b.bar_end_ms) for b in bars)

    return StructuralBarsSnapshot(
        bars_sha256=hasher.hexdigest(),
        bars_byte_length=total_bytes,
        bar_count=len(bars),
        symbol_coverage=coverage,
        time_index=time_index,
    )


# ─── AST INTEGRITY GUARD ────────────────────────────────────────────────────

def verify_source_code_integrity(source_code: str) -> bool:
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_outcome_path_detected:syntax_error:{e}") from e

    for node in ast.walk(tree):
        # Check Import
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in FORBIDDEN_IDENTIFIERS:
                    if forbidden in alias.name:
                        raise RuntimeError(f"STOP=stage1_3_r10_readmission_outcome_path_detected:forbidden_reference:{forbidden}")
        # Check ImportFrom
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for forbidden in FORBIDDEN_IDENTIFIERS:
                if forbidden in module_name:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_outcome_path_detected:forbidden_reference:{forbidden}")
            for alias in node.names:
                for forbidden in FORBIDDEN_IDENTIFIERS:
                    if forbidden in alias.name:
                        raise RuntimeError(f"STOP=stage1_3_r10_readmission_outcome_path_detected:forbidden_reference:{forbidden}")
        # Check Name calls or references
        elif isinstance(node, ast.Name):
            for forbidden in FORBIDDEN_IDENTIFIERS:
                if node.id == forbidden:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_outcome_path_detected:forbidden_reference:{forbidden}")
        # Check Attribute access
        elif isinstance(node, ast.Attribute):
            for forbidden in FORBIDDEN_IDENTIFIERS:
                if node.attr == forbidden:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_outcome_path_detected:forbidden_reference:{forbidden}")

    return True


def verify_cli_source_code_integrity(source_code: str) -> bool:
    verify_source_code_integrity(source_code)
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_outcome_path_detected:syntax_error:{e}") from e

    # Verify that args.bars_jsonl (or bars_jsonl) is referenced and passed only to read_structural_bars
    bars_jsonl_refs = 0
    read_bars_calls = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "bars_jsonl":
            bars_jsonl_refs += 1
        elif isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name == "read_structural_bars":
                read_bars_calls += 1

    if read_bars_calls != 1:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_outcome_path_detected:read_structural_bars_must_be_called_once:got_{read_bars_calls}")
    if bars_jsonl_refs != 1:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_outcome_path_detected:bars_jsonl_must_be_referenced_once:got_{bars_jsonl_refs}")

    return True


# ─── EVENT LEDGER SNAPSHOT & PARSER ────────────────────────────────────────

EVENT_LEDGER_EXACT_KEYS = (
    "candidate_name",
    "symbol",
    "source_bar_start_ms",
    "source_bar_end_ms",
    "event_available_at_ms",
)


@dataclass(frozen=True)
class EventLedgerSnapshot:
    ledger_sha256: str
    ledger_byte_length: int
    event_count: int
    events: tuple[tuple[str, str, int, int, int], ...]


def parse_event_ledger(
    event_ledger_path: str | Path | None,
    bars_snapshot: StructuralBarsSnapshot,
) -> EventLedgerSnapshot | None:
    if event_ledger_path is None:
        return None

    p = Path(event_ledger_path)
    if p.is_symlink():
        raise RuntimeError("STOP=stage1_3_r10_readmission_event_ledger_invalid:symlink_detected")
    if not p.is_file():
        raise RuntimeError("STOP=stage1_3_r10_readmission_event_ledger_invalid:not_regular_file")

    hasher = hashlib.sha256()
    total_bytes = 0
    bars_time_index_set = set(bars_snapshot.time_index)
    parsed_events: list[tuple[str, str, int, int, int]] = []
    last_key: tuple[str, str, int] | None = None

    try:
        with open(p, "rb") as f:
            for line_bytes in f:
                hasher.update(line_bytes)
                total_bytes += len(line_bytes)
                line_str = line_bytes.decode("utf-8").strip()
                if not line_str:
                    continue
                row_dict = json.loads(line_str)
                if set(row_dict.keys()) != set(EVENT_LEDGER_EXACT_KEYS):
                    raise RuntimeError("STOP=stage1_3_r10_readmission_event_ledger_invalid:forbidden_or_extra_keys")

                cand = row_dict["candidate_name"]
                if cand not in STAGE1_3_R10_CANDIDATE_NAMES:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_event_ledger_invalid:unknown_candidate_name:{cand}")

                sym = row_dict["symbol"]
                if sym not in STAGE1_3_R10_SYMBOLS:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_event_ledger_invalid:unknown_symbol:{sym}")

                if cand == "relative_strength_vs_btc" and sym == "BTCUSDT":
                    raise RuntimeError("STOP=stage1_3_r10_readmission_event_ledger_invalid:btc_cannot_emit_relative_strength")

                start_ms = row_dict["source_bar_start_ms"]
                end_ms = row_dict["source_bar_end_ms"]
                avail_ms = row_dict["event_available_at_ms"]

                if type(start_ms) is not int or type(end_ms) is not int or type(avail_ms) is not int:
                    raise RuntimeError("STOP=stage1_3_r10_readmission_event_ledger_invalid:timestamp_not_int")

                if end_ms - start_ms != 900000:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_event_ledger_invalid:bar_duration_not_15m:{end_ms - start_ms}")

                if avail_ms != end_ms + 60000:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_event_ledger_invalid:availability_lag_mismatch:{avail_ms}!={end_ms + 60000}")

                bar_identity = (sym, start_ms, end_ms)
                if bar_identity not in bars_time_index_set:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_event_ledger_invalid:no_matching_bar_in_snapshot:{bar_identity}")

                current_key = (cand, sym, avail_ms)
                if last_key is not None and current_key <= last_key:
                    raise RuntimeError(f"STOP=stage1_3_r10_readmission_event_ledger_invalid:not_strictly_ordered_or_duplicate:{current_key} <= {last_key}")
                last_key = current_key

                parsed_events.append((cand, sym, start_ms, end_ms, avail_ms))
    except Exception as e:
        if "STOP=" in str(e):
            raise
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_event_ledger_invalid:ledger_parse_failed:{e}") from e

    return EventLedgerSnapshot(
        ledger_sha256=hasher.hexdigest(),
        ledger_byte_length=total_bytes,
        event_count=len(parsed_events),
        events=tuple(parsed_events),
    )


# ─── REDUCTION RESULT & REDUCER ───────────────────────────────────────────

@dataclass(frozen=True)
class R10ReductionResult:
    readmission_status: str
    evidence_gap_reasons: tuple[str, ...]
    bars_provided: bool
    bars_sha256: str
    bars_byte_length: int
    bars_matches_historical_manifest: bool
    event_ledger_provided: bool
    event_ledger_sha256: str | None
    event_ledger_byte_length: int | None
    event_ledger_matches_historical_manifest: bool
    historical_anchor_status: str
    manifest_git_commit: str | None
    manifest_git_path: str | None
    manifest_blob_sha256: str | None
    historical_run_identity: str | None
    event_identity_status: str
    event_pit_status: str


def reduce_r10_readmission(
    bars_snapshot: StructuralBarsSnapshot,
    manifest_snapshot: HistoricalManifestSnapshot | None,
    ledger_snapshot: EventLedgerSnapshot | None,
) -> R10ReductionResult:
    # 1. Manifest verification
    if manifest_snapshot is not None:
        if (
            bars_snapshot.bars_sha256 != manifest_snapshot.bars_sha256
            or bars_snapshot.bars_byte_length != manifest_snapshot.bars_byte_length
        ):
            raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:bars_manifest_hash_or_length_mismatch")
        bars_matches = True
        historical_anchor_status = "anchored"
        commit = manifest_snapshot.manifest_git_commit
        git_path = manifest_snapshot.manifest_git_path
        blob_sha = manifest_snapshot.manifest_blob_sha256
        run_id = manifest_snapshot.historical_run_identity
    else:
        bars_matches = False
        historical_anchor_status = "absent"
        commit = None
        git_path = None
        blob_sha = None
        run_id = None

    # 2. Ledger verification
    if ledger_snapshot is not None:
        ledger_provided = True
        ledger_sha = ledger_snapshot.ledger_sha256
        ledger_len = ledger_snapshot.ledger_byte_length
        event_identity_status = "valid"
        event_pit_status = "valid"
        if manifest_snapshot is not None:
            if (
                ledger_snapshot.ledger_sha256 != manifest_snapshot.event_ledger_sha256
                or ledger_snapshot.ledger_byte_length != manifest_snapshot.event_ledger_byte_length
            ):
                raise RuntimeError("STOP=stage1_3_r10_readmission_historical_anchor_invalid:event_ledger_manifest_hash_or_length_mismatch")
            ledger_matches = True
        else:
            ledger_matches = False
    else:
        ledger_provided = False
        ledger_sha = None
        ledger_len = None
        ledger_matches = False
        event_identity_status = "not_checked_event_ledger_absent"
        event_pit_status = "not_checked_event_ledger_absent"

    # 3. Gap reasons and final status
    gap_reasons = []
    if manifest_snapshot is None:
        gap_reasons.append("historical_anchor_absent")
    if ledger_snapshot is None:
        gap_reasons.append("event_ledger_absent")
    gap_reasons = sorted(gap_reasons)

    if gap_reasons:
        readmission_status = "evidence_gap"
    else:
        readmission_status = "eligible_for_exploratory_expectancy_design"

    return R10ReductionResult(
        readmission_status=readmission_status,
        evidence_gap_reasons=tuple(gap_reasons),
        bars_provided=True,
        bars_sha256=bars_snapshot.bars_sha256,
        bars_byte_length=bars_snapshot.bars_byte_length,
        bars_matches_historical_manifest=bars_matches,
        event_ledger_provided=ledger_provided,
        event_ledger_sha256=ledger_sha,
        event_ledger_byte_length=ledger_len,
        event_ledger_matches_historical_manifest=ledger_matches,
        historical_anchor_status=historical_anchor_status,
        manifest_git_commit=commit,
        manifest_git_path=git_path,
        manifest_blob_sha256=blob_sha,
        historical_run_identity=run_id,
        event_identity_status=event_identity_status,
        event_pit_status=event_pit_status,
    )


# ─── RECEIPT BUILDER, VALIDATOR & ATOMIC PUBLISHER ─────────────────────────

DEFAULT_PARENT_DIR = Path("data/external_signal_shadow/stage1_3/r10_readmission_preflight")
RUN_ID_REGEX = re.compile(r"^stage1_3_r10_readmission_[0-9]{8}T[0-9]{6}Z$")

RECEIPT_EXACT_TOP_LEVEL_KEYS = (
    "schema_version",
    "run_id",
    "readmission_status",
    "authority_packet",
    "historical_anchor",
    "input_identities",
    "candidate_scope",
    "fixed_rule_identity",
    "pit_checks",
    "independent_unit_status",
    "evidence_gap_reasons",
    "authority_flags",
    "created_at_utc",
)


def build_r10_receipt_dict(
    run_id: str,
    red: R10ReductionResult,
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    if not RUN_ID_REGEX.match(run_id):
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:invalid_run_id:{run_id}")

    created_at = created_at_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    authority_packet = {
        "approved_design_sha256": APPROVED_DESIGN_SHA256,
        "historical_audit_sha256": "61ba2f7acb88b91db9f23a2f9f085bc493d52160d6ee411978573cb96d9f3ac4",
        "stage1_3_review_sha256": "a404b54b141a5a18914c3b34ae5168e4565699d0929a324464cbca27e89546bf",
        "stage1_3_summary_sha256": "4c27cd2504e9b9660cf4c418fd80b4f00b91655c6adebce3ade36643178d51d5",
        "stage1_3_summary_code_sha256": "6528259eee07e9a82f8bc2a6b3511d5822cf362944f745bd0f296c7977dd3276",
        "stage1_3_candidates_code_sha256": "2c59224742a0041f2cbe2930f0b58e142155c9e0a9d134fd69181195219c10b6",
        "stage1_3_runner_sha256": "f2ba0454cc8eae23afbb58d2ef7d1e091c4457830f932d9ac60f592405f7f080",
        "l2_sha256": "806314e860bbf94d0e4332377d8bf617471f31dfcb51ffab1b646220ba8aed27",
        "historical_review_commit": HISTORICAL_REVIEW_COMMIT,
    }

    historical_anchor = {
        "status": red.historical_anchor_status,
        "manifest_git_commit": red.manifest_git_commit,
        "manifest_git_path": red.manifest_git_path,
        "manifest_blob_sha256": red.manifest_blob_sha256,
        "historical_run_identity": red.historical_run_identity,
    }

    input_identities = {
        "bars": {
            "provided": red.bars_provided,
            "sha256": red.bars_sha256,
            "byte_length": red.bars_byte_length,
            "matches_historical_manifest": red.bars_matches_historical_manifest,
        },
        "event_ledger": {
            "provided": red.event_ledger_provided,
            "sha256": red.event_ledger_sha256,
            "byte_length": red.event_ledger_byte_length,
            "matches_historical_manifest": red.event_ledger_matches_historical_manifest,
        },
    }

    fixed_rule_identity = {
        "candidate_names": list(STAGE1_3_R10_CANDIDATE_NAMES),
        "volume_spike_threshold": 3,
        "same_hour_min_samples": 5,
        "relative_strength_z_threshold": 1.5,
        "rolling_days": 7,
        "rolling_std_min_samples": 48,
        "bar_interval_ms": 900000,
        "availability_lag_ms": 60000,
        "entry_delay_bars": 1,
        "forward_horizon_hours": 4,
        "round_trip_cost_bps": 50,
        "random_baseline_trials": 500,
        "symbol_universe": list(STAGE1_3_R10_SYMBOLS),
    }

    pit_checks = {
        "bars_structural_status": "valid",
        "event_identity_status": red.event_identity_status,
        "event_pit_status": red.event_pit_status,
        "post_event_outcome_accessed": False,
    }

    authority_flags = {k: False for k in STAGE1_3_R10_DENY_VECTOR_KEYS}

    return {
        "schema_version": 1,
        "run_id": run_id,
        "readmission_status": red.readmission_status,
        "authority_packet": authority_packet,
        "historical_anchor": historical_anchor,
        "input_identities": input_identities,
        "candidate_scope": list(STAGE1_3_R10_CANDIDATE_NAMES),
        "fixed_rule_identity": fixed_rule_identity,
        "pit_checks": pit_checks,
        "independent_unit_status": "deferred_to_future_exploratory_design",
        "evidence_gap_reasons": list(red.evidence_gap_reasons),
        "authority_flags": authority_flags,
        "created_at_utc": created_at,
    }


def validate_r10_receipt_dict(receipt: dict[str, Any]) -> bool:
    if set(receipt.keys()) != set(RECEIPT_EXACT_TOP_LEVEL_KEYS):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:top_level_keys_mismatch")

    if type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:schema_version_mismatch")

    run_id = receipt["run_id"]
    if type(run_id) is not str or not RUN_ID_REGEX.match(run_id):
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:invalid_run_id:{run_id}")

    status = receipt["readmission_status"]
    if status not in {"eligible_for_exploratory_expectancy_design", "evidence_gap"}:
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:unknown_status:{status}")

    created_at = receipt.get("created_at_utc")
    if type(created_at) is not str or not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", created_at):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:invalid_created_at_utc")

    # Authority flags
    flags = receipt["authority_flags"]
    if not isinstance(flags, dict) or set(flags.keys()) != set(STAGE1_3_R10_DENY_VECTOR_KEYS):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:deny_vector_keys_mismatch")
    for k, v in flags.items():
        if type(v) is not bool or v is not False:
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:deny_vector_flag_must_be_false:{k}={v}")

    # Authority packet (exact keys and frozen values)
    ap = receipt["authority_packet"]
    if not isinstance(ap, dict):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:authority_packet_mismatch")
    expected_ap = {
        "approved_design_sha256": APPROVED_DESIGN_SHA256,
        "historical_audit_sha256": "61ba2f7acb88b91db9f23a2f9f085bc493d52160d6ee411978573cb96d9f3ac4",
        "stage1_3_review_sha256": "a404b54b141a5a18914c3b34ae5168e4565699d0929a324464cbca27e89546bf",
        "stage1_3_summary_sha256": "4c27cd2504e9b9660cf4c418fd80b4f00b91655c6adebce3ade36643178d51d5",
        "stage1_3_summary_code_sha256": "6528259eee07e9a82f8bc2a6b3511d5822cf362944f745bd0f296c7977dd3276",
        "stage1_3_candidates_code_sha256": "2c59224742a0041f2cbe2930f0b58e142155c9e0a9d134fd69181195219c10b6",
        "stage1_3_runner_sha256": "f2ba0454cc8eae23afbb58d2ef7d1e091c4457830f932d9ac60f592405f7f080",
        "l2_sha256": "806314e860bbf94d0e4332377d8bf617471f31dfcb51ffab1b646220ba8aed27",
        "historical_review_commit": HISTORICAL_REVIEW_COMMIT,
    }
    if set(ap.keys()) != set(expected_ap.keys()):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:authority_packet_mismatch")
    for k, expected_v in expected_ap.items():
        if ap.get(k) != expected_v:
            if k == "historical_review_commit":
                raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:boundary_commit_mismatch")
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:authority_packet_mismatch:{k}")

    # Anchor & inputs
    anchor = receipt["historical_anchor"]
    if not isinstance(anchor, dict):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:historical_anchor_mismatch")
    anchor_exact_keys = {
        "status",
        "manifest_git_commit",
        "manifest_git_path",
        "manifest_blob_sha256",
        "historical_run_identity",
    }
    if set(anchor.keys()) != anchor_exact_keys:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:historical_anchor_mismatch")

    anchor_status = anchor.get("status")
    if anchor_status == "anchored":
        commit = anchor.get("manifest_git_commit")
        path = anchor.get("manifest_git_path")
        blob_sha = anchor.get("manifest_blob_sha256")
        run_id_val = anchor.get("historical_run_identity")
        if (
            not isinstance(commit, str)
            or not re.match(r"^[0-9a-f]{40}$", commit)
            or not isinstance(path, str)
            or not path
            or not isinstance(blob_sha, str)
            or not re.match(r"^[0-9a-f]{64}$", blob_sha)
            or not isinstance(run_id_val, str)
            or not run_id_val
        ):
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:historical_anchor_mismatch")
    elif anchor_status == "absent":
        if (
            anchor.get("manifest_git_commit") is not None
            or anchor.get("manifest_git_path") is not None
            or anchor.get("manifest_blob_sha256") is not None
            or anchor.get("historical_run_identity") is not None
        ):
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:historical_anchor_mismatch")
    else:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:unknown_anchor_status")

    inputs = receipt["input_identities"]
    if not isinstance(inputs, dict) or set(inputs.keys()) != {"bars", "event_ledger"}:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:input_identities_mismatch")

    bars_id = inputs["bars"]
    ledger_id = inputs["event_ledger"]
    exact_input_keys = {"provided", "sha256", "byte_length", "matches_historical_manifest"}

    if not isinstance(bars_id, dict) or set(bars_id.keys()) != exact_input_keys:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:input_identities_mismatch")
    if not isinstance(ledger_id, dict) or set(ledger_id.keys()) != exact_input_keys:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:input_identities_mismatch")

    if type(bars_id.get("provided")) is not bool or not bars_id["provided"]:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:bars_must_be_provided")
    if not isinstance(bars_id.get("sha256"), str) or not re.match(r"^[0-9a-f]{64}$", bars_id["sha256"]):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:invalid_bars_sha256")
    if type(bars_id.get("byte_length")) is not int or bars_id["byte_length"] <= 0:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:invalid_bars_length")
    if type(bars_id.get("matches_historical_manifest")) is not bool:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:input_identities_mismatch")

    if type(ledger_id.get("provided")) is not bool:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:input_identities_mismatch")
    if type(ledger_id.get("matches_historical_manifest")) is not bool:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:input_identities_mismatch")

    # Cross-field checks (Design §8.2.1)
    if anchor_status == "anchored":
        if bars_id.get("matches_historical_manifest") is not True:
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch:anchored_bars_must_match")
    else:
        if bars_id.get("matches_historical_manifest") is not False:
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch:unanchored_bars_must_not_match")

    if not ledger_id.get("provided"):
        if ledger_id.get("sha256") is not None or ledger_id.get("byte_length") is not None:
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch:unprovided_ledger_values_must_be_none")
        if ledger_id.get("matches_historical_manifest") is not False:
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch:unprovided_ledger_matches_must_be_false")
    else:
        if not isinstance(ledger_id.get("sha256"), str) or not re.match(r"^[0-9a-f]{64}$", ledger_id["sha256"]):
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:invalid_ledger_sha256")
        if type(ledger_id.get("byte_length")) is not int or ledger_id["byte_length"] <= 0:
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:invalid_ledger_length")
        if anchor_status == "anchored":
            if ledger_id.get("matches_historical_manifest") is not True:
                raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch:anchored_ledger_must_match")
        else:
            if ledger_id.get("matches_historical_manifest") is not False:
                raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch:unanchored_ledger_must_not_match")

    gap_reasons = receipt["evidence_gap_reasons"]
    if status == "eligible_for_exploratory_expectancy_design":
        if gap_reasons != []:
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch:eligible_must_have_no_gaps")
        if anchor_status != "anchored" or not ledger_id.get("provided"):
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch:eligible_requires_anchor_and_ledger")
    else:
        # evidence_gap
        if not gap_reasons:
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch:gap_reasons_must_not_be_empty")
        for r in gap_reasons:
            if r not in {"historical_anchor_absent", "event_ledger_absent"}:
                raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:unknown_gap_reason:{r}")
        if gap_reasons != sorted(list(set(gap_reasons))):
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:gap_reasons_must_be_sorted_and_unique")

    # Candidate scope (Design §8.2)
    candidate_scope = receipt.get("candidate_scope")
    if candidate_scope != list(STAGE1_3_R10_CANDIDATE_NAMES):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:candidate_scope_mismatch")

    # Fixed rule identity (Design §8.2)
    fri = receipt.get("fixed_rule_identity")
    if not isinstance(fri, dict):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    expected_fri_keys = {
        "candidate_names",
        "volume_spike_threshold",
        "same_hour_min_samples",
        "relative_strength_z_threshold",
        "rolling_days",
        "rolling_std_min_samples",
        "bar_interval_ms",
        "availability_lag_ms",
        "entry_delay_bars",
        "forward_horizon_hours",
        "round_trip_cost_bps",
        "random_baseline_trials",
        "symbol_universe",
    }
    if set(fri.keys()) != expected_fri_keys:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")

    if fri.get("candidate_names") != list(STAGE1_3_R10_CANDIDATE_NAMES):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("volume_spike_threshold") != 3 or type(fri.get("volume_spike_threshold")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("same_hour_min_samples") != 5 or type(fri.get("same_hour_min_samples")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("relative_strength_z_threshold") != 1.5 or not isinstance(fri.get("relative_strength_z_threshold"), (int, float)):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("rolling_days") != 7 or type(fri.get("rolling_days")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("rolling_std_min_samples") != 48 or type(fri.get("rolling_std_min_samples")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("bar_interval_ms") != 900000 or type(fri.get("bar_interval_ms")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("availability_lag_ms") != 60000 or type(fri.get("availability_lag_ms")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("entry_delay_bars") != 1 or type(fri.get("entry_delay_bars")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("forward_horizon_hours") != 4 or type(fri.get("forward_horizon_hours")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("round_trip_cost_bps") != 50 or type(fri.get("round_trip_cost_bps")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("random_baseline_trials") != 500 or type(fri.get("random_baseline_trials")) is not int:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")
    if fri.get("symbol_universe") != list(STAGE1_3_R10_SYMBOLS):
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch")

    if receipt.get("independent_unit_status") != "deferred_to_future_exploratory_design":
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:independent_unit_status_must_be_deferred")

    # PIT checks (Design §8.2)
    pit = receipt.get("pit_checks")
    if not isinstance(pit, dict) or set(pit.keys()) != {
        "bars_structural_status",
        "event_identity_status",
        "event_pit_status",
        "post_event_outcome_accessed",
    }:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:pit_checks_mismatch")
    if pit.get("bars_structural_status") != "valid":
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:bars_status_must_be_valid")
    if type(pit.get("post_event_outcome_accessed")) is not bool or pit.get("post_event_outcome_accessed") is not False:
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:outcome_accessed_must_be_false")

    if ledger_id.get("provided"):
        if pit.get("event_identity_status") != "valid" or pit.get("event_pit_status") != "valid":
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:pit_checks_mismatch")
    else:
        if (
            pit.get("event_identity_status") != "not_checked_event_ledger_absent"
            or pit.get("event_pit_status") != "not_checked_event_ledger_absent"
        ):
            raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:pit_checks_mismatch")

    return True


def publish_r10_receipt(
    run_id: str,
    receipt_dict: dict[str, Any],
    *,
    parent_dir: Path | None = None,
    hook_before_rename: Any | None = None,
    hook_after_rename: Any | None = None,
) -> Path:
    if not RUN_ID_REGEX.match(run_id):
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:invalid_run_id:{run_id}")

    validate_r10_receipt_dict(receipt_dict)

    p_dir = parent_dir or DEFAULT_PARENT_DIR
    if p_dir.is_symlink():
        raise RuntimeError("STOP=stage1_3_r10_readmission_receipt_invalid:parent_dir_symlink")

    p_dir.mkdir(parents=True, exist_ok=True)
    p_fd = os.open(str(p_dir), os.O_RDONLY)
    try:
        os.fsync(p_fd)
        try:
            fcntl.flock(p_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:final_root_preexists:{p_dir / run_id}")

        final_root = p_dir / run_id
        if final_root.exists() or final_root.is_symlink():
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:final_root_preexists:{final_root}")

        staging_root = p_dir / f".{run_id}.staging.{os.getpid()}"
        if staging_root.exists() or staging_root.is_symlink():
            raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:staging_root_preexists:{staging_root}")

        staging_root.mkdir(parents=False, exist_ok=False)

        try:
            receipt_path = staging_root / "r10_readmission_receipt.json"
            receipt_bytes = (json.dumps(receipt_dict, indent=2, sort_keys=True) + "\n").encode("utf-8")
            with open(receipt_path, "wb") as f:
                f.write(receipt_bytes)
                f.flush()
                os.fsync(f.fileno())

            receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
            sums_path = staging_root / "SHA256SUMS"
            sums_bytes = f"{receipt_sha256}  r10_readmission_receipt.json\n".encode("utf-8")
            with open(sums_path, "wb") as f:
                f.write(sums_bytes)
                f.flush()
                os.fsync(f.fileno())

            # Fsync staging directory
            fd = os.open(str(staging_root), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

            if hook_before_rename is not None:
                hook_before_rename()

            # Ensure final root does not pre-exist before rename (fail-closed against concurrent/hook collisions)
            if final_root.exists() or final_root.is_symlink():
                raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:final_root_preexists:{final_root}")

            # Atomic rename on same filesystem
            os.replace(staging_root, final_root)

            # Fsync parent dir
            os.fsync(p_fd)

            if hook_after_rename is not None:
                hook_after_rename()

            return final_root
        finally:
            if staging_root.exists():
                try:
                    for child in staging_root.iterdir():
                        child.unlink()
                    staging_root.rmdir()
                except Exception:
                    pass
    finally:
        try:
            fcntl.flock(p_fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(p_fd)


def classify_r10_root(final_root: Path) -> str:
    if final_root.is_symlink():
        return "corrupt_or_unknown"
    if not final_root.exists():
        return "before_start"
    if not final_root.is_dir():
        return "corrupt_or_unknown"

    entries = sorted(p.name for p in final_root.iterdir())
    if entries != ["SHA256SUMS", "r10_readmission_receipt.json"]:
        return "corrupt_or_unknown"

    receipt_p = final_root / "r10_readmission_receipt.json"
    sums_p = final_root / "SHA256SUMS"

    if receipt_p.is_symlink() or sums_p.is_symlink():
        return "corrupt_or_unknown"
    if not receipt_p.is_file() or not sums_p.is_file():
        return "corrupt_or_unknown"

    sums_lines = sums_p.read_text(encoding="utf-8").splitlines()
    if len(sums_lines) != 1:
        return "corrupt_or_unknown"

    expected_sha = hashlib.sha256(receipt_p.read_bytes()).hexdigest()
    if sums_lines[0] != f"{expected_sha}  r10_readmission_receipt.json":
        return "corrupt_or_unknown"

    try:
        data = json.loads(receipt_p.read_bytes().decode("utf-8"))
        validate_r10_receipt_dict(data)
    except Exception:
        return "corrupt_or_unknown"

    return "receipt_published"


def load_local_published_r10_receipt(
    final_root: str | Path,
    *,
    future_consumer_allowed: bool = False,
) -> dict[str, Any]:
    if future_consumer_allowed:
        raise RuntimeError("STOP=stage1_3_r10_readmission_future_consumer_binding_missing")

    p = Path(final_root)
    status = classify_r10_root(p)
    if status != "receipt_published":
        raise RuntimeError(f"STOP=stage1_3_r10_readmission_receipt_invalid:root_status_{status}")

    receipt_p = p / "r10_readmission_receipt.json"
    return json.loads(receipt_p.read_bytes().decode("utf-8"))
