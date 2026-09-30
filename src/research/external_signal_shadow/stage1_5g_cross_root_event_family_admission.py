from __future__ import annotations

import copy
import fcntl
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


# Controlled exception
class Stage1_5GCrossRootAdmissionError(Exception):
    pass


APPROVED_DESIGN_REL_PATH: str = (
    "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md"
)
APPROVED_PLAN_REL_PATH: str = (
    "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md"
)

FROZEN_UPSTREAM_CONTRACT: dict[str, str] = {
    "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py": "596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d",
    "configs/base.py": "414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4",
    "src/research/external_signal_shadow/safety.py": "1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d",
}

EXPECTED_UPSTREAM_FALSE_KEYS: tuple[str, ...] = (
    "trade_signal_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_engine_allowed",
    "alpha_interpretation_allowed",
    "execution_feasibility_claim_allowed",
)

EXPECTED_13_FALSE_FLAGS: dict[str, bool] = {
    "alpha_interpretation_allowed": False,
    "commit_allowed": False,
    "deployment_allowed": False,
    "event_family_conclusion_allowed": False,
    "execution_engine_allowed": False,
    "execution_feasibility_claim_allowed": False,
    "live_trading_allowed": False,
    "network_collection_allowed": False,
    "paper_trading_allowed": False,
    "push_allowed": False,
    "replay_allowed": False,
    "ssh_allowed": False,
    "trade_signal_allowed": False,
}

FROZEN_INPUT_RECORDS: list[dict[str, Any]] = [
    {
        "input_key": "moonshot",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot",
        "source_manifest_sha256": "611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db",
        "expected_parent_article_id": "7379b99aa0f349a49c3b3feca1b4bbd6",
        "expected_parent_event_id": "e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5",
        "expected_symbols": ["MOONSHOTUSDT"],
    },
    {
        "input_key": "batch7",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7",
        "source_manifest_sha256": "0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280",
        "expected_parent_article_id": "0c6ea14ba89b451db6ec9ec364045d22",
        "expected_parent_event_id": "d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0",
        "expected_symbols": ["ACNUSDT", "BWETUSDT", "CRMLUSDT", "MPUSDT", "NKEUSDT", "SECZUSDT", "UNHUSDT"],
    },
]

_RUN_ID_REGEX = re.compile(r"^stage1_5g_cross_root_admission_[0-9]{8}T[0-9]{6}Z$")

# Private cached modules
_CACHED_UPSTREAM_MODULES: dict[str, Any] = {}


def _project_root_from_core_file() -> Path:
    return Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_execution_authority(
    execution_baseline_dir: Path | str,
    supplied_approval_bindings: dict[str, str],
    project_root: Path | None = None,
) -> dict[str, Any]:
    root = (project_root or _project_root_from_core_file()).resolve()
    bundle = Path(execution_baseline_dir).resolve()

    if bundle.is_symlink() or not bundle.is_dir():
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:invalid_baseline_dir")

    auth_json = bundle / "execution_authority.json"
    auth_sha_file = bundle / "execution_authority.sha256"
    ledger_jsonl = bundle / "preexisting_path_ledger.jsonl"
    ledger_sha_file = bundle / "preexisting_path_ledger.sha256"

    for p in (auth_json, auth_sha_file, ledger_jsonl, ledger_sha_file):
        if p.is_symlink() or not p.is_file():
            raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:missing_authority_record")

    if _sha256(auth_json) != auth_sha_file.read_text(encoding="utf-8").strip():
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:auth_sha_mismatch")

    if _sha256(ledger_jsonl) != ledger_sha_file.read_text(encoding="utf-8").strip():
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:ledger_sha_mismatch")

    try:
        authority = json.loads(auth_json.read_text(encoding="utf-8"))
    except Exception as exc:
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:auth_json_unreadable") from exc

    required_keys = {
        "project_root",
        "base_sha",
        "approved_design_path",
        "approved_design_sha256",
        "approved_plan_path",
        "approved_plan_sha256",
        "current_plan_sha256",
    }
    if set(authority.keys()) != required_keys:
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:auth_keys_mismatch")

    # 1. Project root check
    authority_project_root = Path(authority["project_root"]).resolve()
    if authority_project_root != root:
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:project_root_mismatch")

    # 2. Fixed Design/Plan relative paths check
    if authority["approved_design_path"] != APPROVED_DESIGN_REL_PATH:
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:design_path_mismatch")
    if authority["approved_plan_path"] != APPROVED_PLAN_REL_PATH:
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:plan_path_mismatch")

    # 3. current_plan_sha256 == approved_plan_sha256 check
    if authority["current_plan_sha256"] != authority["approved_plan_sha256"]:
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:plan_sha_mismatch")

    # 4. Check supplied approval bindings
    for k in ("approved_design_path", "approved_design_sha256", "approved_plan_path", "approved_plan_sha256"):
        if supplied_approval_bindings.get(k) != authority[k]:
            raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:binding_mismatch")

    # 5. Git HEAD == base_sha check
    base_sha = authority["base_sha"]
    if not isinstance(base_sha, str) or len(base_sha) != 40 or not all(c in "0123456789abcdefABCDEF" for c in base_sha):
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:invalid_base_sha_format")

    res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise Stage1_5GCrossRootAdmissionError(
            f"STOP=approved_authority_mismatch:git_rev_parse_failed:{res.stderr.strip()}"
        )
    current_head = res.stdout.strip()
    if current_head != base_sha:
        raise Stage1_5GCrossRootAdmissionError(
            f"STOP=approved_authority_mismatch:head_sha_mismatch:{current_head}_vs_{base_sha}"
        )

    # 6. Recheck current files on disk
    design_p = root / authority["approved_design_path"]
    plan_p = root / authority["approved_plan_path"]

    if design_p.is_symlink() or not design_p.is_file() or _sha256(design_p) != authority["approved_design_sha256"]:
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:design_drift")

    if plan_p.is_symlink() or not plan_p.is_file() or _sha256(plan_p) != authority["approved_plan_sha256"]:
        raise Stage1_5GCrossRootAdmissionError("STOP=approved_authority_mismatch:plan_drift")

    return authority


def verify_frozen_upstream_contract(project_root: Path | None = None) -> None:
    root = (project_root or _project_root_from_core_file()).resolve()
    for rel_path, expected_sha in FROZEN_UPSTREAM_CONTRACT.items():
        p = root / rel_path
        if p.is_symlink() or not p.is_file():
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_upstream_contract_drift")
        if _sha256(p) != expected_sha:
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_upstream_contract_drift")


def _import_verified_upstream(project_root: Path | None = None) -> dict[str, Any]:
    global _CACHED_UPSTREAM_MODULES
    root = (project_root or _project_root_from_core_file()).resolve()

    target_modules = {
        "src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review": "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py",
        "configs.base": "configs/base.py",
        "src.research.external_signal_shadow.safety": "src/research/external_signal_shadow/safety.py",
    }

    # If first call, verify no preloaded foreign/shadow modules exist
    if not _CACHED_UPSTREAM_MODULES:
        for mod_name, rel_path in target_modules.items():
            if mod_name in sys.modules:
                mod = sys.modules[mod_name]
                expected_origin = str((root / rel_path).resolve())
                mod_file = getattr(mod, "__file__", None)
                spec_origin = getattr(getattr(mod, "__spec__", None), "origin", None)
                if (mod_file and str(Path(mod_file).resolve()) != expected_origin) or (
                    spec_origin and str(Path(spec_origin).resolve()) != expected_origin
                ):
                    raise Stage1_5GCrossRootAdmissionError(
                        "STOP=stage1_5g_cross_root_upstream_module_origin_mismatch"
                    )

        # Verify frozen contracts on disk
        verify_frozen_upstream_contract(project_root=root)

        # Lazy import and verify origin
        loaded = {}
        for mod_name, rel_path in target_modules.items():
            mod = importlib.import_module(mod_name)
            expected_origin = str((root / rel_path).resolve())
            mod_file = getattr(mod, "__file__", None)
            spec_origin = getattr(getattr(mod, "__spec__", None), "origin", None)
            if not mod_file or str(Path(mod_file).resolve()) != expected_origin:
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_upstream_module_origin_mismatch")
            if not spec_origin or str(Path(spec_origin).resolve()) != expected_origin:
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_upstream_module_origin_mismatch")
            # Rehash actual file
            if _sha256(Path(mod_file)) != FROZEN_UPSTREAM_CONTRACT[rel_path]:
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_upstream_contract_drift")
            loaded[mod_name] = mod

        # Check callables / constants exist
        rev_mod = loaded["src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review"]
        cfg_mod = loaded["configs.base"]
        safety_mod = loaded["src.research.external_signal_shadow.safety"]

        if not hasattr(rev_mod, "load_stage1_5g_inputs") or not hasattr(rev_mod, "build_stage1_5g_review_summary"):
            raise Stage1_5GCrossRootAdmissionError("STOP=BLOCKED_SPEC_DRIFT")
        if not hasattr(cfg_mod, "EXTERNAL_SIGNAL_STAGE1_5G_MIN_EVENT_FAMILY_SAMPLE_REQUIRED") or not hasattr(
            cfg_mod, "EXTERNAL_SIGNAL_STAGE1_5G_MIN_SOURCE_ARTICLES_REQUIRED"
        ):
            raise Stage1_5GCrossRootAdmissionError("STOP=BLOCKED_SPEC_DRIFT")
        if not hasattr(safety_mod, "canonical_json_dumps"):
            raise Stage1_5GCrossRootAdmissionError("STOP=BLOCKED_SPEC_DRIFT")

        _CACHED_UPSTREAM_MODULES = loaded
    else:
        # Validate that sys.modules has not been monkeypatched/shadowed
        for mod_name, cached_mod in _CACHED_UPSTREAM_MODULES.items():
            if sys.modules.get(mod_name) is not cached_mod:
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_upstream_module_origin_mismatch")
            rel_path = target_modules[mod_name]
            expected_origin = str((root / rel_path).resolve())
            mod_file = getattr(cached_mod, "__file__", None)
            spec_origin = getattr(getattr(cached_mod, "__spec__", None), "origin", None)
            if not mod_file or str(Path(mod_file).resolve()) != expected_origin:
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_upstream_module_origin_mismatch")
            if not spec_origin or str(Path(spec_origin).resolve()) != expected_origin:
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_upstream_module_origin_mismatch")
            if _sha256(Path(mod_file)) != FROZEN_UPSTREAM_CONTRACT[rel_path]:
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_upstream_contract_drift")

    return _CACHED_UPSTREAM_MODULES


def compare_admitted_projection(stored_proj: dict[str, Any], recomputed_proj: dict[str, Any]) -> None:
    """Pure comparator verifying stored and recomputed projections match exactly."""
    required_keys = {
        "schema_version",
        "decision",
        "clean_depth_evidence_pass",
        "source_evidence_manifest_sha256",
        "formal_completed_event_symbol_ids_sha256",
        "formal_children",
    }
    if set(stored_proj.keys()) != required_keys or set(recomputed_proj.keys()) != required_keys:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")

    for k in (
        "schema_version",
        "decision",
        "clean_depth_evidence_pass",
        "source_evidence_manifest_sha256",
        "formal_completed_event_symbol_ids_sha256",
    ):
        if stored_proj[k] != recomputed_proj[k] or type(stored_proj[k]) is not type(recomputed_proj[k]):
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")

    # Compare formal_children array
    s_children = stored_proj["formal_children"]
    r_children = recomputed_proj["formal_children"]
    if not isinstance(s_children, list) or not isinstance(r_children, list):
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")
    if len(s_children) != len(r_children) or len(s_children) == 0:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")

    child_keys = {
        "event_symbol_id",
        "event_id",
        "symbol",
        "source_article_id",
        "evidence_label",
        "state_status",
        "formal_completed",
    }
    for sc, rc in zip(s_children, r_children):
        if set(sc.keys()) != child_keys or set(rc.keys()) != child_keys:
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")
        for ck in child_keys:
            if sc[ck] != rc[ck] or type(sc[ck]) is not type(rc[ck]):
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")


def admit_frozen_cross_root_inputs(
    project_root: Path | None = None,
    input_records_override: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    root = (project_root or _project_root_from_core_file()).resolve()
    modules = _import_verified_upstream(project_root=root)
    rev_mod = modules["src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review"]
    load_stage1_5g_inputs = rev_mod.load_stage1_5g_inputs
    build_stage1_5g_review_summary = rev_mod.build_stage1_5g_review_summary

    records_to_process = input_records_override if input_records_override is not None else FROZEN_INPUT_RECORDS
    if len(records_to_process) != 2:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")

    admitted_results: list[dict[str, Any]] = []

    for record in records_to_process:
        # 1. Stored summary checks
        if "stored_summary_path" not in record or "stored_summary_sha256" not in record:
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")
        summary_rel = record["stored_summary_path"]
        stored_p = root / summary_rel
        if stored_p.is_symlink() or not stored_p.is_file():
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")
        summary_bytes = stored_p.read_bytes()
        if _sha256(stored_p) != record["stored_summary_sha256"]:
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")

        try:
            stored_summary = json.loads(summary_bytes.decode("utf-8"))
        except Exception as exc:
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch") from exc

        # 2. Source root checks
        if "source_root_path" not in record or "source_manifest_sha256" not in record:
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")
        source_rel = record["source_root_path"]
        source_p = root / source_rel
        if source_p.is_symlink() or not source_p.is_dir():
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")

        manifest_p = source_p / "SHA256SUMS"
        if manifest_p.is_symlink() or not manifest_p.is_file():
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")
        if _sha256(manifest_p) != record["source_manifest_sha256"]:
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")

        # 3. Production loader
        bundle = load_stage1_5g_inputs(source_p)
        if getattr(bundle, "loader_blockers", None):
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_root_not_clean")

        # 4. Production reducer
        recomputed = build_stage1_5g_review_summary(
            summary=bundle.summary,
            watermark=bundle.watermark,
            states=bundle.states,
            accepted_events=bundle.accepted_events,
            snapshots=bundle.snapshots,
            request_manifest_rows=bundle.request_manifest_rows,
            output_root=source_p,
            loader_blockers=bundle.loader_blockers,
        )

        # 5. Check clean pass & invariants
        if (
            recomputed.get("schema_version") != 2
            or recomputed.get("decision") != "stage1_5g_depth_evidence_clean_pass"
            or recomputed.get("clean_depth_evidence_pass") is not True
            or len(recomputed.get("blockers", [])) > 0
            or recomputed.get("source_evidence_manifest_sha256") != record.get("source_manifest_sha256")
        ):
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_root_not_clean")

        for fk in EXPECTED_UPSTREAM_FALSE_KEYS:
            if recomputed.get(fk) is not False or type(recomputed.get(fk)) is not bool:
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_root_not_clean")

        # 6. Extract formal projection from both stored and recomputed summaries
        def _extract_projection(s: dict[str, Any]) -> dict[str, Any]:
            elds = s.get("event_level_decisions", [])
            children = []
            for eld in elds:
                if (
                    eld.get("evidence_label") == "announcement_and_launch_time"
                    and eld.get("state_status") == "completed"
                    and eld.get("formal_completed") is True
                ):
                    children.append({
                        "event_symbol_id": str(eld.get("event_symbol_id")),
                        "event_id": str(eld.get("event_id")),
                        "symbol": str(eld.get("symbol")),
                        "source_article_id": str(eld.get("source_article_id")),
                        "evidence_label": "announcement_and_launch_time",
                        "state_status": "completed",
                        "formal_completed": True,
                    })
            return {
                "schema_version": s.get("schema_version"),
                "decision": s.get("decision"),
                "clean_depth_evidence_pass": s.get("clean_depth_evidence_pass"),
                "source_evidence_manifest_sha256": s.get("source_evidence_manifest_sha256"),
                "formal_completed_event_symbol_ids_sha256": s.get("formal_completed_event_symbol_ids_sha256"),
                "formal_children": children,
            }

        stored_proj = _extract_projection(stored_summary)
        recomputed_proj = _extract_projection(recomputed)

        # Compare projections
        compare_admitted_projection(stored_proj, recomputed_proj)

        # Check children match expected ledger
        expected_symbols = record.get("expected_symbols", [])
        recomputed_symbols = [c["symbol"] for c in recomputed_proj["formal_children"]]
        if set(recomputed_symbols) != set(expected_symbols) or len(recomputed_symbols) != len(expected_symbols):
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_child_identity_collision")

        if record.get("expected_parent_article_id"):
            for c in recomputed_proj["formal_children"]:
                if c["source_article_id"] != record["expected_parent_article_id"]:
                    raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_parent_independence_mismatch")
        if record.get("expected_parent_event_id"):
            for c in recomputed_proj["formal_children"]:
                if c["event_id"] != record["expected_parent_event_id"]:
                    raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_parent_independence_mismatch")

        admitted_record = {
            "input_key": record["input_key"],
            "stored_summary_path": record["stored_summary_path"],
            "stored_summary_sha256": record["stored_summary_sha256"],
            "source_root_path": record["source_root_path"],
            "source_manifest_sha256": record["source_manifest_sha256"],
            "recomputed_formal_projection": recomputed_proj,
        }
        admitted_results.append(admitted_record)

    return admitted_results


def build_cross_root_summary(
    admitted_records: list[dict[str, Any]],
    run_id: str,
    config_thresholds_override: dict[str, int] | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(run_id, str) or not _RUN_ID_REGEX.match(run_id):
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_publication_integrity_failure:invalid_run_id")

    if len(admitted_records) != 2:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")

    # Check input order
    if [r["input_key"] for r in admitted_records] != ["moonshot", "batch7"]:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_input_authority_mismatch")

    # Parent independence
    parent_articles = []
    parent_events = []
    all_child_symbols: list[str] = []
    all_child_es_ids: list[str] = []
    parent_ledger: list[dict[str, Any]] = []

    for r in admitted_records:
        proj = r.get("recomputed_formal_projection", {})
        children = proj.get("formal_children", [])
        if not children:
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_child_identity_collision")

        p_article = children[0]["source_article_id"]
        p_event = children[0]["event_id"]
        # Verify all children in this record share the same parent article and event
        for c in children:
            if c["source_article_id"] != p_article or c["event_id"] != p_event:
                raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_parent_independence_mismatch")

        parent_articles.append(p_article)
        parent_events.append(p_event)

        child_es_ids = [c["event_symbol_id"] for c in children]
        child_syms = [c["symbol"] for c in children]

        all_child_symbols.extend(child_syms)
        all_child_es_ids.extend(child_es_ids)

        parent_ledger.append({
            "parent_article_id": p_article,
            "parent_event_id": p_event,
            "child_event_symbol_ids": child_es_ids,
            "child_symbols": child_syms,
        })

    # Require exactly 2 distinct parent articles and 2 distinct parent events
    if len(set(parent_articles)) != 2 or len(set(parent_events)) != 2:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_parent_independence_mismatch")

    # Require no duplicate child symbol or event_symbol_id
    if len(set(all_child_symbols)) != len(all_child_symbols) or len(set(all_child_es_ids)) != len(all_child_es_ids):
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_child_identity_collision")

    # Require exact 8 symbols
    expected_8_symbols = {
        "MOONSHOTUSDT",
        "ACNUSDT",
        "BWETUSDT",
        "CRMLUSDT",
        "MPUSDT",
        "NKEUSDT",
        "SECZUSDT",
        "UNHUSDT",
    }
    if set(all_child_symbols) != expected_8_symbols or len(all_child_symbols) != 8:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_child_identity_collision")

    # Config threshold check
    root = (project_root or _project_root_from_core_file()).resolve()
    modules = _import_verified_upstream(project_root=root)
    cfg_mod = modules["configs.base"]

    if config_thresholds_override is not None:
        if "min_symbols" not in config_thresholds_override or "min_articles" not in config_thresholds_override:
            raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_threshold_not_met")
        min_symbols = config_thresholds_override["min_symbols"]
        min_articles = config_thresholds_override["min_articles"]
    else:
        min_symbols = getattr(cfg_mod, "EXTERNAL_SIGNAL_STAGE1_5G_MIN_EVENT_FAMILY_SAMPLE_REQUIRED", None)
        min_articles = getattr(cfg_mod, "EXTERNAL_SIGNAL_STAGE1_5G_MIN_SOURCE_ARTICLES_REQUIRED", None)

    if min_symbols != 3 or min_articles != 2:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_threshold_not_met")

    formal_symbol_count = len(all_child_symbols)
    distinct_source_article_count = len(set(parent_articles))
    independent_parent_event_count = len(set(parent_events))

    if formal_symbol_count < min_symbols or distinct_source_article_count < min_articles:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_threshold_not_met")

    summary_payload = {
        "authority_flags": copy.deepcopy(EXPECTED_13_FALSE_FLAGS),
        "cross_root_evidence_count_status": "sufficient",
        "decision": "stage1_5g_cross_root_event_family_admission_pass",
        "distinct_source_article_count": distinct_source_article_count,
        "formal_symbol_count": formal_symbol_count,
        "independent_parent_event_count": independent_parent_event_count,
        "input_records": copy.deepcopy(admitted_records),
        "parent_ledger": parent_ledger,
        "run_id": run_id,
        "schema_version": 1,
        "stage1_5g_gate3_complete": False,
    }

    return summary_payload


DEFAULT_EVENT_FAMILY_ADMISSIONS_PARENT = "data/external_signal_shadow/stage1_5g/event_family_admissions"
_FAILPOINT_HOOK: Any = None


def render_review(summary: dict[str, Any]) -> str:
    """Render authoritative Markdown projection strictly byte-for-byte matching §5.3 template."""
    lines = [
        "# Stage 1.5G Cross-Root Admission Receipt",
        "",
        f"- `run_id`: `{summary['run_id']}`",
        "- `decision`: `stage1_5g_cross_root_event_family_admission_pass`",
        "- `cross_root_evidence_count_status`: `sufficient`",
        "- `stage1_5g_gate3_complete`: `false`",
        "- `formal_symbol_count`: `8`",
        "- `distinct_source_article_count`: `2`",
        "- `independent_parent_event_count`: `2`",
        "",
        "## Parent Ledger",
        "",
        "| parent_article_id | parent_event_id | child_event_symbol_ids | child_symbols |",
        "| --- | --- | --- | --- |",
    ]
    for p in summary["parent_ledger"]:
        child_ids = ",".join(p["child_event_symbol_ids"])
        child_syms = ",".join(p["child_symbols"])
        lines.append(f"| {p['parent_article_id']} | {p['parent_event_id']} | {child_ids} | {child_syms} |")

    lines.extend([
        "",
        "## Frozen Inputs",
        "",
        "| input_key | stored_summary_path | stored_summary_sha256 | source_root_path | source_manifest_sha256 |",
        "| --- | --- | --- | --- | --- |",
    ])
    for inp in summary["input_records"]:
        lines.append(
            f"| {inp['input_key']} | {inp['stored_summary_path']} | {inp['stored_summary_sha256']} | {inp['source_root_path']} | {inp['source_manifest_sha256']} |"
        )

    lines.extend([
        "",
        "## Authority Flags",
        "",
        "| flag | value |",
        "| --- | --- |",
    ])
    for flag in sorted(summary["authority_flags"].keys()):
        lines.append(f"| {flag} | false |")

    lines.append("")
    return "\n".join(lines)


def load_verified_cross_root_receipt(
    root: Path | str,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Strict reader validating manifest, byte lengths, hashes, summary schema, false vector, and Markdown projection."""
    final_root = Path(root).resolve()
    if final_root.is_symlink() or not final_root.is_dir():
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_publication_integrity_failure:invalid_root")

    items = list(final_root.iterdir())
    item_names = {item.name for item in items}
    expected_files = {
        "stage1_5g_cross_root_admission_summary.json",
        "stage1_5g_cross_root_admission_review_CN.md",
        "stage1_5g_cross_root_admission_manifest.json",
    }
    if item_names != expected_files:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_publication_integrity_failure:unlisted_files")

    for item in items:
        if item.is_symlink() or not item.is_file():
            raise Stage1_5GCrossRootAdmissionError(
                "STOP=stage1_5g_cross_root_publication_integrity_failure:symlink_or_not_file"
            )

    modules = _import_verified_upstream()
    canonical_json_dumps = modules["src.research.external_signal_shadow.safety"].canonical_json_dumps

    # 1. Manifest
    man_p = final_root / "stage1_5g_cross_root_admission_manifest.json"
    man_bytes = man_p.read_bytes()
    try:
        manifest = json.loads(man_bytes.decode("utf-8"))
    except Exception as exc:
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:manifest_unreadable"
        ) from exc

    if canonical_json_dumps(manifest).encode("utf-8") != man_bytes:
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:manifest_not_canonical"
        )

    if set(manifest.keys()) != {"artifacts", "frozen_input_records", "run_id", "schema_version"}:
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:manifest_keys"
        )

    if (
        manifest.get("schema_version") != 1
        or not isinstance(manifest.get("run_id"), str)
        or not _RUN_ID_REGEX.match(manifest["run_id"])
    ):
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:manifest_schema"
        )

    if not isinstance(manifest.get("artifacts"), dict) or set(manifest["artifacts"].keys()) != {"review", "summary"}:
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:manifest_artifacts"
        )

    for art_name, exp_rel in (
        ("review", "stage1_5g_cross_root_admission_review_CN.md"),
        ("summary", "stage1_5g_cross_root_admission_summary.json"),
    ):
        art_meta = manifest["artifacts"][art_name]
        if not isinstance(art_meta, dict) or set(art_meta.keys()) != {"byte_count", "relative_path", "sha256"}:
            raise Stage1_5GCrossRootAdmissionError(
                "STOP=stage1_5g_cross_root_publication_integrity_failure:art_meta_keys"
            )
        if (
            art_meta["relative_path"] != exp_rel
            or not isinstance(art_meta["byte_count"], int)
            or art_meta["byte_count"] <= 0
            or not isinstance(art_meta["sha256"], str)
            or not re.match(r"^[0-9a-f]{64}$", art_meta["sha256"])
        ):
            raise Stage1_5GCrossRootAdmissionError(
                "STOP=stage1_5g_cross_root_publication_integrity_failure:art_meta_fields"
            )

        file_bytes = (final_root / exp_rel).read_bytes()
        if len(file_bytes) != art_meta["byte_count"] or hashlib.sha256(file_bytes).hexdigest() != art_meta["sha256"]:
            raise Stage1_5GCrossRootAdmissionError(
                f"STOP=stage1_5g_cross_root_publication_integrity_failure:{art_name}_mismatch"
            )

    # 2. Summary
    sum_p = final_root / "stage1_5g_cross_root_admission_summary.json"
    sum_bytes = sum_p.read_bytes()
    try:
        summary = json.loads(sum_bytes.decode("utf-8"))
    except Exception as exc:
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:summary_unreadable"
        ) from exc

    if canonical_json_dumps(summary).encode("utf-8") != sum_bytes:
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:summary_not_canonical"
        )

    expected_summary_keys = {
        "authority_flags",
        "cross_root_evidence_count_status",
        "decision",
        "distinct_source_article_count",
        "formal_symbol_count",
        "independent_parent_event_count",
        "input_records",
        "parent_ledger",
        "run_id",
        "schema_version",
        "stage1_5g_gate3_complete",
    }
    if set(summary.keys()) != expected_summary_keys:
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:summary_keys"
        )

    if (
        summary.get("schema_version") != 1
        or summary.get("decision") != "stage1_5g_cross_root_event_family_admission_pass"
        or summary.get("cross_root_evidence_count_status") != "sufficient"
        or summary.get("stage1_5g_gate3_complete") is not False
        or type(summary.get("stage1_5g_gate3_complete")) is not bool
        or summary.get("formal_symbol_count") != 8
        or summary.get("distinct_source_article_count") != 2
        or summary.get("independent_parent_event_count") != 2
    ):
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:summary_invariants"
        )

    if summary.get("run_id") != manifest.get("run_id"):
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:run_id_mismatch"
        )

    if canonical_json_dumps(summary["input_records"]) != canonical_json_dumps(manifest["frozen_input_records"]):
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:manifest_input_records_mismatch"
        )

    if set(summary["authority_flags"].keys()) != set(EXPECTED_13_FALSE_FLAGS.keys()):
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:authority_flags_keys"
        )

    for k, v in summary["authority_flags"].items():
        if v is not False or type(v) is not bool:
            raise Stage1_5GCrossRootAdmissionError(
                "STOP=stage1_5g_cross_root_publication_integrity_failure:authority_flags_values"
            )

    # 3. Review
    expected_md = render_review(summary)
    actual_md = (final_root / "stage1_5g_cross_root_admission_review_CN.md").read_text(encoding="utf-8")
    if actual_md != expected_md:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_review_projection_mismatch")

    # 4. Independently re-admit both frozen roots and require exact canonical equality
    proj_root = (project_root or _project_root_from_core_file()).resolve()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=proj_root)

    if canonical_json_dumps(summary["input_records"]) != canonical_json_dumps(admitted_inputs):
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:input_records_mismatch"
        )

    # Derive expected parent ledger from real admitted inputs
    expected_parent_ledger = []
    for inp in admitted_inputs:
        proj = inp["recomputed_formal_projection"]
        child_ids = [c["event_symbol_id"] for c in proj["formal_children"]]
        child_syms = [c["symbol"] for c in proj["formal_children"]]
        parent_article_id = proj["formal_children"][0]["source_article_id"]
        parent_event_id = proj["formal_children"][0]["event_id"]
        expected_parent_ledger.append({
            "child_event_symbol_ids": child_ids,
            "child_symbols": child_syms,
            "parent_article_id": parent_article_id,
            "parent_event_id": parent_event_id,
        })

    # 5. Parent ledger validation against expected parent ledger derived from real projections
    if summary["parent_ledger"] != expected_parent_ledger:
        raise Stage1_5GCrossRootAdmissionError(
            "STOP=stage1_5g_cross_root_publication_integrity_failure:parent_ledger_mismatch"
        )

    return {"summary": summary, "manifest": manifest, "review": actual_md}


def classify_receipt_state(
    parent: Path | str,
    run_id: str,
    project_root: Path | None = None,
) -> str:
    """Byte-authoritative state classifier."""
    p = Path(parent).resolve()
    if not isinstance(run_id, str) or not _RUN_ID_REGEX.match(run_id):
        return "corrupt_or_unknown"

    final_root = p / run_id
    staging_pattern = re.compile(rf"^\.{re.escape(run_id)}\.staging\.[1-9][0-9]*$")
    staging_found = False
    if p.is_dir():
        for child in p.iterdir():
            if staging_pattern.match(child.name):
                staging_found = True
                break

    if not final_root.exists() and not final_root.is_symlink():
        if staging_found:
            return "staging_only"
        return "unpublished"

    if final_root.is_symlink() or not final_root.is_dir():
        return "corrupt_or_unknown"

    try:
        load_verified_cross_root_receipt(final_root, project_root=project_root)
        return "receipt_published"
    except Exception:
        return "corrupt_or_unknown"


def publish_cross_root_receipt(
    summary: dict[str, Any],
    run_id: str,
    parent_dir_override: Path | None = None,
    project_root: Path | None = None,
) -> Path:
    """Atomic publication of cross-root admission receipt."""
    if not isinstance(run_id, str) or not _RUN_ID_REGEX.match(run_id) or summary.get("run_id") != run_id:
        raise Stage1_5GCrossRootAdmissionError("STOP=stage1_5g_cross_root_publication_integrity_failure:invalid_run_id")

    parent_dir = (parent_dir_override or (_project_root_from_core_file() / DEFAULT_EVENT_FAMILY_ADMISSIONS_PARENT)).resolve()
    parent_dir.mkdir(parents=True, exist_ok=True)

    final_root = parent_dir / run_id
    if final_root.exists() or final_root.is_symlink():
        raise Stage1_5GCrossRootAdmissionError(
            f"STOP=stage1_5g_cross_root_publication_integrity_failure:final_root_preexists:{final_root}"
        )

    pid = os.getpid()
    staging_dir = parent_dir / f".{run_id}.staging.{pid}"
    if staging_dir.exists() or staging_dir.is_symlink():
        raise Stage1_5GCrossRootAdmissionError(
            f"STOP=stage1_5g_cross_root_publication_integrity_failure:staging_preexists:{staging_dir}"
        )

    staging_dir.mkdir(parents=True, exist_ok=False)

    def _trigger_failpoint(position: str) -> None:
        if _FAILPOINT_HOOK is not None:
            _FAILPOINT_HOOK(position)

    modules = _import_verified_upstream()
    canonical_json_dumps = modules["src.research.external_signal_shadow.safety"].canonical_json_dumps

    # 1. Summary
    summary_bytes = canonical_json_dumps(summary).encode("utf-8")
    tmp_sum = staging_dir / f".tmp_summary_{pid}"
    fd = os.open(str(tmp_sum), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.write(fd, summary_bytes)
    os.fsync(fd)
    os.close(fd)
    _trigger_failpoint("after_summary_write")
    os.replace(tmp_sum, staging_dir / "stage1_5g_cross_root_admission_summary.json")
    _trigger_failpoint("after_summary_fsync")

    # 2. Review
    review_text = render_review(summary)
    review_bytes = review_text.encode("utf-8")
    tmp_rev = staging_dir / f".tmp_review_{pid}"
    fd = os.open(str(tmp_rev), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.write(fd, review_bytes)
    os.fsync(fd)
    os.close(fd)
    _trigger_failpoint("after_review_write")
    os.replace(tmp_rev, staging_dir / "stage1_5g_cross_root_admission_review_CN.md")
    _trigger_failpoint("after_review_fsync")

    # 3. Manifest
    manifest_payload = {
        "artifacts": {
            "review": {
                "byte_count": len(review_bytes),
                "relative_path": "stage1_5g_cross_root_admission_review_CN.md",
                "sha256": hashlib.sha256(review_bytes).hexdigest(),
            },
            "summary": {
                "byte_count": len(summary_bytes),
                "relative_path": "stage1_5g_cross_root_admission_summary.json",
                "sha256": hashlib.sha256(summary_bytes).hexdigest(),
            },
        },
        "frozen_input_records": summary["input_records"],
        "run_id": run_id,
        "schema_version": 1,
    }
    manifest_bytes = canonical_json_dumps(manifest_payload).encode("utf-8")
    tmp_man = staging_dir / f".tmp_manifest_{pid}"
    fd = os.open(str(tmp_man), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.write(fd, manifest_bytes)
    os.fsync(fd)
    os.close(fd)
    _trigger_failpoint("after_manifest_write")
    os.replace(tmp_man, staging_dir / "stage1_5g_cross_root_admission_manifest.json")
    _trigger_failpoint("after_manifest_fsync")

    # Verify staging contents strictly before rename
    load_verified_cross_root_receipt(staging_dir, project_root=project_root)

    st_fd = os.open(str(staging_dir), os.O_RDONLY)
    os.fsync(st_fd)
    os.close(st_fd)
    _trigger_failpoint("after_staging_fsync")

    # Lock parent directory, re-check collision, atomic rename, fsync parent
    p_fd = os.open(str(parent_dir), os.O_RDONLY)
    fcntl.flock(p_fd, fcntl.LOCK_EX)
    renamed = False
    try:
        _trigger_failpoint("before_rename")
        if final_root.exists() or final_root.is_symlink():
            raise Stage1_5GCrossRootAdmissionError(
                f"STOP=stage1_5g_cross_root_publication_integrity_failure:collision:{run_id}"
            )
        os.replace(staging_dir, final_root)
        renamed = True
        _trigger_failpoint("after_rename")
        os.fsync(p_fd)
        _trigger_failpoint("after_parent_fsync")
    except Exception as exc:
        if renamed:
            raise Stage1_5GCrossRootAdmissionError("STOP=POST_RENAME_DURABILITY_FAILURE") from exc
        raise
    finally:
        fcntl.flock(p_fd, fcntl.LOCK_UN)
        os.close(p_fd)

    return final_root
