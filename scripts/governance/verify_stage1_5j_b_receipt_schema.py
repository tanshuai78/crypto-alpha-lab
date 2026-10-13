#!/usr/bin/env python3
"""Governance Independent Rule 17 Verifier for Stage 1.5J-B Receipt Schema.

Pure standard library CLI tool to verify structural schema integrity of
Stage 1.5J-B historical aggTrades launch-response receipts.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

PROFILE_ID = "stage1_5j_b_receipt_v1"
PROFILE_CONTRACT_VERSION = 1

PROFILE_ID_V2 = "stage1_5j_b_receipt_v2"
PROFILE_CONTRACT_VERSION_V2 = 2

OUTPUT_PARENT = "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response"
RUN_ID_REGEX = r"^stage1_5j_b_historical_aggtrades_launch_response_[0-9]{8}T[0-9]{6}Z$"
SCHEMA_VERSION = "stage1_5j_b_historical_aggtrades_launch_response_v1"

GOVERNANCE_PARENT_DESIGN_PATH = "docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md"
GOVERNANCE_PARENT_DESIGN_SHA256 = "73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4"

PROFILE_V2_DESIGN_PATH = "docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md"
PROFILE_V2_DESIGN_SHA256 = "8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454"

LATEST_J_B_DOMAIN_DESIGN_PATH = "docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md"
LATEST_J_B_DOMAIN_DESIGN_SHA256 = "66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f"

J_B_PARENT_DESIGN_PATH = "docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md"
J_B_PARENT_DESIGN_SHA256 = "ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b"

J_B_REBIND_DELTA_PATH = "docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md"
J_B_REBIND_DELTA_SHA256 = "0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c"

J_B_RECEIPT_SCHEMA_AUTHORITY_PATH = "docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md"
J_B_RECEIPT_SCHEMA_AUTHORITY_SHA256 = "f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25"

J_B_PROFILE_DESIGN_DELTA_PATH = "docs/designs/2026-10-11-governance-stage1-5j-b-receipt-rule17-profile-design-delta_CN.md"

PROFILE_AUDITED_CONFIG_RELATIVE_PATH = "configs/stage1_5j_b_historical_aggtrades_launch_response.py"
PROFILE_AUDITED_CONFIG_SHA256 = "771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4"

FROZEN_AUTHORITY_FLAGS = {
    "alpha_claim_allowed": False,
    "broker_routing_allowed": False,
    "capital_commitment_allowed": False,
    "discretionary_override_allowed": False,
    "execution_engine_allowed": False,
    "execution_feasibility_claim_allowed": False,
    "live_trading_allowed": False,
    "network_access_allowed": False,
    "paper_trading_allowed": False,
    "position_sizing_allowed": False,
    "realtime_telemetry_allowed": False,
    "trade_intent_allowed": False,
}

FROZEN_RESEARCH_STATUS = {
    "alpha_evidence_status": "evidence_insufficient",
    "capital_survival_claim": "not_evaluated",
    "economic_edge_claim": "not_evaluated",
    "execution_feasibility_claim": "not_evaluated",
    "live_permission_claim": False,
    "phenomenon_claim": "not_evaluated",
    "research_mode": "exploratory_descriptive_only",
    "statistical_edge_claim": "not_evaluated",
}

FROZEN_J_A_PROJECTIONS = {
    "catalog_denominator_count": 335,
    "child_coverage_complete_count": 280,
    "child_coverage_gap_count": 1,
    "in_scope_usdt_child_count": 281,
    "out_of_scope_child_count": 5,
    "parent_coverage_complete_count": 120,
    "parent_coverage_gap_count": 11,
    "resolved_parent_count": 125,
    "target_parent_count": 131,
}

FROZEN_J_A_ROOT_INFO = {
    "j_a_core_path": "src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py",
    "j_a_core_sha256": "250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18",
    "j_a_manifest_sha256": "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf",
    "j_a_request_journal_sha256": "b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa",
    "j_a_review_sha256": "1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152",
    "j_a_root_relative_path": "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z",
    "j_a_run_id": "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z",
    "j_a_summary_sha256": "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b",
}

CHILD_ROW_REQUIRED_KEYS = {
    "anchor_delay_ms",
    "anchor_price",
    "anchor_state",
    "anchor_time_ms",
    "j_a_child_state",
    "j_a_parent_state",
    "required_archive_dates_by_horizon",
    "source_article_id",
    "symbol",
    "symbol_launch_time_ms",
}

LEGAL_ANCHOR_STATES = {
    "evidence_gap",
    "anchor_found",
    "anchor_unavailable_inherited_j_a_parent_gap",
    "anchor_unavailable_delay_exceeded",
}

CHILD_HORIZON_ROW_REQUIRED_KEYS = {
    "child_horizon_state",
    "gross_return_bps",
    "horizon_ms",
    "horizon_offset_ms",
    "horizon_price",
    "horizon_selected_time_ms",
    "horizon_target_time_ms",
    "missing_reason",
    "sampled_max_excursion_bps",
    "sampled_min_excursion_bps",
    "source_article_id",
    "symbol",
    "trade_count",
}

LEGAL_CHILD_HORIZON_STATES = {
    "child_horizon_complete",
    "child_horizon_evidence_gap",
}

LEGAL_MISSING_REASONS = {
    "inherited_j_a_parent_gap",
    "evidence_gap_missing_launch_time",
    "evidence_gap_anchor_delay",
    "evidence_gap_missing_required_archive_package",
    "evidence_gap_missing_horizon_trade",
}

PARENT_HORIZON_ROW_REQUIRED_KEYS = {
    "failed_child_reasons",
    "horizon_ms",
    "parent_gross_return_bps",
    "parent_horizon_state",
    "parent_sampled_max_excursion_bps",
    "parent_sampled_min_excursion_bps",
    "source_article_id",
    "source_parent_state",
}

LEGAL_PARENT_HORIZON_STATES = {
    "parent_horizon_complete",
    "parent_horizon_evidence_gap",
}

SUMMARY_REQUIRED_KEYS = {
    "analysis_state",
    "authority_flags",
    "authority_packet",
    "child_horizon_rows",
    "child_rows",
    "coverage_counts",
    "decision",
    "j_a_input",
    "parent_horizon_rows",
    "research_status",
    "run_id",
    "schema_version",
}

COVERAGE_COUNTS_REQUIRED_KEYS = {
    "j_a_parent_coverage_complete_count",
    "j_a_parent_coverage_gap_count",
    "j_a_target_parent_count",
    "n_child_horizon_complete_by_horizon",
    "n_child_horizon_gap_by_horizon",
    "n_parent_horizon_complete_by_horizon",
    "n_parent_horizon_gap_by_horizon",
    "n_parent_total",
    "n_parent_with_j_a_gap",
    "parent_distribution_by_horizon",
}

PARENT_DIST_REQUIRED_KEYS = {
    "max",
    "mean",
    "median",
    "min",
    "n_complete_parent",
    "p10",
    "p25",
    "p50",
    "p75",
    "p90",
    "top_1_abs_return_contribution",
    "top_1_parent_ids",
    "top_3_abs_return_contribution",
    "top_3_parent_ids",
}

LEGAL_J_A_PARENT_STATES = {
    "coverage_complete",
    "coverage_evidence_gap_archive",
    "coverage_evidence_gap_detail",
    "coverage_evidence_gap_no_in_scope_usdt_child",
}

LEGAL_J_A_CHILD_STATES = {
    "j_a_child_coverage_complete",
    "j_a_child_coverage_gap",
}


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _verify_canonical_json(raw: bytes) -> tuple[bool, object]:
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        return False, None
    canonical_repr = (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    return (raw == canonical_repr), obj


def verify_receipt(root_path: Path, profile_id: str = PROFILE_ID) -> tuple[bool, str]:
    """Verify structural integrity of the Stage 1.5J-B receipt tree."""
    if not root_path.is_dir():
        return False, f"Artifact root directory does not exist: {root_path}"

    # Check that root directory contains only regular files and exactly the three expected files
    members = sorted(root_path.iterdir())
    member_names = {m.name for m in members}
    expected_names = {"manifest.json", "summary.json", "review_CN.md"}

    if member_names != expected_names:
        return False, f"Sealed tree members mismatch: observed {member_names}, expected {expected_names}"

    for m in members:
        if not m.is_file() or m.is_symlink():
            return False, f"Tree member must be regular non-symlink file: {m.name}"

    manifest_bytes = (root_path / "manifest.json").read_bytes()
    summary_bytes = (root_path / "summary.json").read_bytes()
    review_bytes = (root_path / "review_CN.md").read_bytes()

    # Verify review_CN.md byte safety
    if b"\x00" in review_bytes:
        return False, "review_CN.md contains null byte"
    try:
        review_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False, "review_CN.md is not valid UTF-8"

    # Verify manifest canonical JSON
    ok_m, manifest_obj = _verify_canonical_json(manifest_bytes)
    if not ok_m:
        return False, "manifest.json is not canonical JSON"

    if manifest_obj.get("schema_version") != SCHEMA_VERSION:
        return False, f"manifest schema_version mismatch: {manifest_obj.get('schema_version')}"

    manifest_artifacts = {a["path"]: a for a in manifest_obj.get("artifacts", [])}
    if set(manifest_artifacts.keys()) != {"summary.json", "review_CN.md"}:
        return False, "manifest.json artifacts list mismatch"

    # Verify manifest hashes
    if manifest_artifacts["summary.json"]["sha256"] != _sha256_bytes(summary_bytes):
        return False, "manifest summary.json sha256 mismatch"
    if manifest_artifacts["summary.json"]["byte_count"] != len(summary_bytes):
        return False, "manifest summary.json byte_count mismatch"

    if manifest_artifacts["review_CN.md"]["sha256"] != _sha256_bytes(review_bytes):
        return False, "manifest review_CN.md sha256 mismatch"
    if manifest_artifacts["review_CN.md"]["byte_count"] != len(review_bytes):
        return False, "manifest review_CN.md byte_count mismatch"

    # Verify summary canonical JSON
    ok_s, summary_obj = _verify_canonical_json(summary_bytes)
    if not ok_s:
        return False, "summary.json is not canonical JSON"

    # Verify schema version and run ID
    if summary_obj.get("schema_version") != SCHEMA_VERSION:
        return False, f"summary schema_version mismatch: {summary_obj.get('schema_version')}"

    run_id = summary_obj.get("run_id")
    if not isinstance(run_id, str) or not re.match(RUN_ID_REGEX, run_id):
        return False, f"summary run_id invalid: {run_id}"

    # Verify authority flags
    flags = summary_obj.get("authority_flags", {})
    if flags != FROZEN_AUTHORITY_FLAGS:
        return False, f"authority_flags mismatch: {flags}"

    # Verify research status
    research_status = summary_obj.get("research_status", {})
    if research_status != FROZEN_RESEARCH_STATUS:
        return False, f"research_status mismatch: {research_status}"

    # Verify authority packet approved_j_b_design and audited_config
    auth_packet = summary_obj.get("authority_packet", {})
    if not isinstance(auth_packet, dict):
        return False, "authority_packet must be a dictionary"

    app_des = auth_packet.get("approved_j_b_design", {})
    if not isinstance(app_des, dict):
        return False, "authority_packet approved_j_b_design must be a dictionary"

    if profile_id == PROFILE_ID:
        if app_des.get("relative_path") != J_B_RECEIPT_SCHEMA_AUTHORITY_PATH:
            return False, f"authority_packet approved_j_b_design path mismatch: {app_des.get('relative_path')}"
        if app_des.get("sha256") != J_B_RECEIPT_SCHEMA_AUTHORITY_SHA256:
            return False, f"authority_packet approved_j_b_design sha mismatch: {app_des.get('sha256')}"
    elif profile_id == PROFILE_ID_V2:
        if app_des.get("relative_path") != LATEST_J_B_DOMAIN_DESIGN_PATH:
            return False, f"authority_packet approved_j_b_design path mismatch: {app_des.get('relative_path')}"
        if app_des.get("sha256") != LATEST_J_B_DOMAIN_DESIGN_SHA256:
            return False, f"authority_packet approved_j_b_design sha mismatch: {app_des.get('sha256')}"

        audited_cfg = auth_packet.get("audited_config")
        if not isinstance(audited_cfg, dict):
            return False, "authority_packet audited_config missing or not a dictionary"
        if audited_cfg.get("relative_path") != PROFILE_AUDITED_CONFIG_RELATIVE_PATH:
            return False, f"authority_packet audited_config relative_path mismatch: {audited_cfg.get('relative_path')}"
        if audited_cfg.get("sha256") != PROFILE_AUDITED_CONFIG_SHA256:
            return False, f"authority_packet audited_config sha256 mismatch: {audited_cfg.get('sha256')}"
    else:
        return False, f"Unsupported profile: {profile_id}"

    # Verify j_a_input
    j_a_input = summary_obj.get("j_a_input", {})
    for k, v in FROZEN_J_A_ROOT_INFO.items():
        if j_a_input.get(k) != v:
            return False, f"j_a_input {k} mismatch: {j_a_input.get(k)} != {v}"

    for k, v in FROZEN_J_A_PROJECTIONS.items():
        if j_a_input.get(k) != v:
            return False, f"j_a_input projection {k} mismatch: {j_a_input.get(k)} != {v}"

    # For v2, perform structural row and coverage count checks
    if profile_id == PROFILE_ID_V2:
        if set(summary_obj.keys()) != SUMMARY_REQUIRED_KEYS:
            return False, f"summary.json keys mismatch: {set(summary_obj.keys()) ^ SUMMARY_REQUIRED_KEYS}"

        decision = summary_obj.get("decision")
        if decision not in (
            "stage1_5j_b_historical_aggtrades_launch_response_described_published",
            "stage1_5j_b_historical_aggtrades_launch_response_evidence_gap_published",
        ):
            return False, f"summary decision invalid: {decision}"

        analysis_state = summary_obj.get("analysis_state")
        if analysis_state not in (
            "exploratory_response_described",
            "exploratory_response_evidence_gap",
            "launch_response_evidence_gap",
        ):
            return False, f"summary analysis_state invalid: {analysis_state}"

        # Verify parent_horizon_rows and extract parent_state_by_article
        parent_horizon_rows = summary_obj.get("parent_horizon_rows")
        if not isinstance(parent_horizon_rows, list) or len(parent_horizon_rows) != 393:
            return False, f"parent_horizon_rows must be list of 393 rows, observed {len(parent_horizon_rows) if isinstance(parent_horizon_rows, list) else type(parent_horizon_rows)}"

        parent_state_by_article = {}
        parent_horizon_counts = {}
        for idx, phr in enumerate(parent_horizon_rows):
            if not isinstance(phr, dict) or set(phr.keys()) != PARENT_HORIZON_ROW_REQUIRED_KEYS:
                return False, f"parent_horizon_rows[{idx}] keys mismatch"
            if phr["parent_horizon_state"] not in LEGAL_PARENT_HORIZON_STATES:
                return False, f"parent_horizon_rows[{idx}] parent_horizon_state invalid: {phr['parent_horizon_state']}"
            if phr["horizon_ms"] not in (300000, 3600000, 14400000):
                return False, f"parent_horizon_rows[{idx}] horizon_ms invalid: {phr['horizon_ms']}"
            if phr["source_parent_state"] not in LEGAL_J_A_PARENT_STATES:
                return False, f"parent_horizon_rows[{idx}] source_parent_state invalid: {phr['source_parent_state']}"
            if not isinstance(phr["failed_child_reasons"], list):
                return False, f"parent_horizon_rows[{idx}] failed_child_reasons must be list"

            p_id = phr["source_article_id"]
            if p_id not in parent_state_by_article:
                parent_state_by_article[p_id] = phr["source_parent_state"]
                parent_horizon_counts[p_id] = set()
            else:
                if phr["source_parent_state"] != parent_state_by_article[p_id]:
                    return False, f"parent_horizon_rows[{idx}] inconsistent source_parent_state for {p_id}"
            parent_horizon_counts[p_id].add(phr["horizon_ms"])

            if phr["source_parent_state"] != "coverage_complete":
                if phr["parent_horizon_state"] != "parent_horizon_evidence_gap":
                    return False, f"parent_horizon_rows[{idx}] gap parent must have parent_horizon_evidence_gap"
                if not phr["failed_child_reasons"]:
                    return False, f"parent_horizon_rows[{idx}] gap parent failed_child_reasons cannot be empty"
                for r_item in phr["failed_child_reasons"]:
                    if not isinstance(r_item, dict) or r_item.get("missing_reason") != "inherited_j_a_parent_gap":
                        return False, f"parent_horizon_rows[{idx}] gap parent reason must be inherited_j_a_parent_gap"

        if len(parent_state_by_article) != 131:
            return False, f"parent_horizon_rows distinct parents must be 131, observed {len(parent_state_by_article)}"
        for p_id, h_set in parent_horizon_counts.items():
            if h_set != {300000, 3600000, 14400000}:
                return False, f"parent_horizon_rows parent {p_id} missing required horizons: {h_set}"

        n_comp_parents = sum(1 for st in parent_state_by_article.values() if st == "coverage_complete")
        n_gap_parents = sum(1 for st in parent_state_by_article.values() if st != "coverage_complete")
        if n_comp_parents != 120 or n_gap_parents != 11:
            return False, f"parent_horizon_rows parent state counts mismatch: {n_comp_parents} complete, {n_gap_parents} gap"

        # Verify child_rows and cross-table consistency with parent_horizon_rows
        child_rows = summary_obj.get("child_rows")
        if not isinstance(child_rows, list) or len(child_rows) != 281:
            return False, f"child_rows must be list of 281 rows, observed {len(child_rows) if isinstance(child_rows, list) else type(child_rows)}"

        for idx, cr in enumerate(child_rows):
            if not isinstance(cr, dict) or set(cr.keys()) != CHILD_ROW_REQUIRED_KEYS:
                return False, f"child_rows[{idx}] keys mismatch"
            if cr["anchor_state"] not in LEGAL_ANCHOR_STATES:
                return False, f"child_rows[{idx}] anchor_state invalid: {cr['anchor_state']}"
            if cr["j_a_parent_state"] not in LEGAL_J_A_PARENT_STATES:
                return False, f"child_rows[{idx}] j_a_parent_state invalid: {cr['j_a_parent_state']}"
            if cr["j_a_child_state"] not in LEGAL_J_A_CHILD_STATES:
                return False, f"child_rows[{idx}] j_a_child_state invalid: {cr['j_a_child_state']}"
            if cr["anchor_state"] in ("evidence_gap", "anchor_unavailable_inherited_j_a_parent_gap"):
                if cr["anchor_delay_ms"] is not None or cr["anchor_price"] is not None or cr["anchor_time_ms"] is not None:
                    return False, f"child_rows[{idx}] gap anchor fields must be null"
            dates_map = cr.get("required_archive_dates_by_horizon")
            if not isinstance(dates_map, dict) or set(dates_map.keys()) != {"300000", "3600000", "14400000"}:
                return False, f"child_rows[{idx}] required_archive_dates_by_horizon keys invalid"

            p_id = cr["source_article_id"]
            if p_id not in parent_state_by_article:
                return False, f"child_rows[{idx}] source_article_id '{p_id}' not found in parent_horizon_rows"
            expected_p_state = parent_state_by_article[p_id]
            if cr["j_a_parent_state"] != expected_p_state:
                return False, f"child_rows[{idx}] j_a_parent_state '{cr['j_a_parent_state']}' mismatch with parent_horizon_rows '{expected_p_state}'"
            if expected_p_state != "coverage_complete":
                if cr["anchor_state"] != "anchor_unavailable_inherited_j_a_parent_gap":
                    return False, f"child_rows[{idx}] anchor_state must be anchor_unavailable_inherited_j_a_parent_gap for gap parent"
            else:
                if cr["anchor_state"] == "anchor_unavailable_inherited_j_a_parent_gap":
                    return False, f"child_rows[{idx}] anchor_state cannot be anchor_unavailable_inherited_j_a_parent_gap for complete parent"

        # Verify child_horizon_rows and cross-table consistency with parent_horizon_rows
        child_horizon_rows = summary_obj.get("child_horizon_rows")
        if not isinstance(child_horizon_rows, list) or len(child_horizon_rows) != 843:
            return False, f"child_horizon_rows must be list of 843 rows, observed {len(child_horizon_rows) if isinstance(child_horizon_rows, list) else type(child_horizon_rows)}"

        for idx, chr_ in enumerate(child_horizon_rows):
            if not isinstance(chr_, dict) or set(chr_.keys()) != CHILD_HORIZON_ROW_REQUIRED_KEYS:
                return False, f"child_horizon_rows[{idx}] keys mismatch"
            if chr_["child_horizon_state"] not in LEGAL_CHILD_HORIZON_STATES:
                return False, f"child_horizon_rows[{idx}] child_horizon_state invalid: {chr_['child_horizon_state']}"
            if chr_["horizon_ms"] not in (300000, 3600000, 14400000):
                return False, f"child_horizon_rows[{idx}] horizon_ms invalid: {chr_['horizon_ms']}"
            if chr_["missing_reason"] is not None and chr_["missing_reason"] not in LEGAL_MISSING_REASONS:
                return False, f"child_horizon_rows[{idx}] missing_reason invalid: {chr_['missing_reason']}"
            if chr_["child_horizon_state"] == "child_horizon_evidence_gap":
                if (
                    chr_["gross_return_bps"] is not None
                    or chr_["horizon_offset_ms"] is not None
                    or chr_["horizon_price"] is not None
                    or chr_["horizon_selected_time_ms"] is not None
                    or chr_["sampled_max_excursion_bps"] is not None
                    or chr_["sampled_min_excursion_bps"] is not None
                    or chr_["trade_count"] is not None
                ):
                    return False, f"child_horizon_rows[{idx}] gap outcome fields must be null"

            p_id = chr_["source_article_id"]
            if p_id not in parent_state_by_article:
                return False, f"child_horizon_rows[{idx}] source_article_id '{p_id}' not found in parent_horizon_rows"
            expected_p_state = parent_state_by_article[p_id]
            if expected_p_state != "coverage_complete":
                if chr_["child_horizon_state"] != "child_horizon_evidence_gap":
                    return False, f"child_horizon_rows[{idx}] child_horizon_state must be child_horizon_evidence_gap for gap parent"
                if chr_["missing_reason"] != "inherited_j_a_parent_gap":
                    return False, f"child_horizon_rows[{idx}] missing_reason must be inherited_j_a_parent_gap for gap parent"

        cov_counts = summary_obj.get("coverage_counts")
        if not isinstance(cov_counts, dict) or set(cov_counts.keys()) != COVERAGE_COUNTS_REQUIRED_KEYS:
            return False, "coverage_counts keys mismatch"
        if cov_counts["j_a_parent_coverage_complete_count"] != 120:
            return False, "coverage_counts j_a_parent_coverage_complete_count mismatch"
        if cov_counts["j_a_parent_coverage_gap_count"] != 11:
            return False, "coverage_counts j_a_parent_coverage_gap_count mismatch"
        if cov_counts["j_a_target_parent_count"] != 131:
            return False, "coverage_counts j_a_target_parent_count mismatch"
        if cov_counts["n_parent_total"] != 131:
            return False, "coverage_counts n_parent_total mismatch"
        if cov_counts["n_parent_with_j_a_gap"] != 11:
            return False, "coverage_counts n_parent_with_j_a_gap mismatch"

        for h_str in ("300000", "3600000", "14400000"):
            c_comp = cov_counts["n_child_horizon_complete_by_horizon"].get(h_str)
            c_gap = cov_counts["n_child_horizon_gap_by_horizon"].get(h_str)
            if c_comp is None or c_gap is None or c_comp + c_gap != 281:
                return False, f"coverage_counts child horizon sum mismatch for {h_str}"

            p_comp = cov_counts["n_parent_horizon_complete_by_horizon"].get(h_str)
            p_gap = cov_counts["n_parent_horizon_gap_by_horizon"].get(h_str)
            if p_comp is None or p_gap is None or p_comp + p_gap != 131:
                return False, f"coverage_counts parent horizon sum mismatch for {h_str}"

        p_dist = cov_counts["parent_distribution_by_horizon"]
        if not isinstance(p_dist, dict) or set(p_dist.keys()) != {"300000", "3600000", "14400000"}:
            return False, "parent_distribution_by_horizon keys mismatch"
        for h_str, dist in p_dist.items():
            if not isinstance(dist, dict) or set(dist.keys()) != PARENT_DIST_REQUIRED_KEYS:
                return False, f"parent_distribution_by_horizon[{h_str}] keys mismatch"

    return True, ""


def main(argv: list[str] | None = None) -> int:
    """Entry point for governance verification CLI."""
    parser = argparse.ArgumentParser(description="Governance Stage 1.5J-B Receipt Schema Verifier")
    parser.add_argument("--profile", required=True, help="Profile ID")
    parser.add_argument("--artifact-root", required=True, help="Artifact root relative to project root")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    if args.profile not in (PROFILE_ID, PROFILE_ID_V2):
        sys.stderr.write(f"Unsupported profile: {args.profile}\n")
        return 2

    # Path safety & traversal checks
    raw_path_str = args.artifact_root
    if os.path.isabs(raw_path_str) or ".." in Path(raw_path_str).parts:
        sys.stderr.write("Artifact root must be a relative path without traversal\n")
        return 2

    normalized_path = Path(raw_path_str)
    # Check that artifact root is directly below OUTPUT_PARENT
    expected_parent = Path(OUTPUT_PARENT)
    if normalized_path.parent != expected_parent:
        sys.stderr.write(f"Artifact root must be directly inside {OUTPUT_PARENT}\n")
        return 2

    if not re.match(RUN_ID_REGEX, normalized_path.name):
        sys.stderr.write(f"Artifact root basename must match {RUN_ID_REGEX}\n")
        return 2

    if not normalized_path.is_dir():
        sys.stderr.write(f"Artifact root directory does not exist: {normalized_path}\n")
        return 2

    # Check symlinks in path
    cur = normalized_path
    while cur != Path(".") and cur != cur.parent:
        if cur.is_symlink():
            sys.stderr.write(f"Symlink detected in path: {cur}\n")
            return 2
        cur = cur.parent

    # Execute verification
    ok, err_msg = verify_receipt(normalized_path, profile_id=args.profile)
    if not ok:
        sys.stderr.write(f"Contract violation [{args.profile}]: {err_msg}\n")
        return 1

    sys.stdout.write(f"SUCCESS: Artifact root '{normalized_path}' is conformant with '{args.profile}'\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
