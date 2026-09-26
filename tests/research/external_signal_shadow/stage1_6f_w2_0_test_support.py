"""Test support module for Stage 1.6F-W2-0 exploratory terminal basis diagnostic.

Provides canonical mirror fixtures, authority bindings, and single declared mutation helpers.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

# Exact frozen authority paths and SHA-256 digests
W2_0_DESIGN_PATH = "docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-design_CN.md"
W2_0_DESIGN_SHA = "58f4cf8638b05a1c268578ace0ed8d4c6b8b794daa4d94107e2af349d22862c4"

W2_0_PLAN_PATH = "docs/plans/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-implementation-plan_CN.md"
W2_0_PLAN_SHA = "17dc74ee85e66f490460e745e97aa2ec6628baccf9039f69d9e78ed49b0666fe"

W2_DESIGN_PATH = "docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md"
W2_DESIGN_SHA = "11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303"

W2_PLAN_PATH = "docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md"
W2_PLAN_SHA = "183689a6b786ccd3dce9f74f5d1fc2e9ccc1741d80f243f5724dd3b7de149229"

W2_NETWORK_AUTH_PATH = "configs/authorizations/network_auth_w2_candidate_run_20260925_001.json"
W2_NETWORK_AUTH_SHA = "0189fd4a922c87811e25793b62d12d6ba76ad92e60a95236a3fe54f024fa5dbf"

W2_CANDIDATE_ROOT_PATH = "data/external_signal_shadow/stage1_6f/w2_evidence_candidates/w2_candidate_run_20260925_001"
W2_CANDIDATE_MANIFEST_SHA = "1bd45df8d27e85b40d30500148575780740c6d089b5700e43c1cbfc22a4a0cea"

EXTERNAL_AUDIT_PATH = "/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_completion_audit_review.md"
EXTERNAL_AUDIT_SHA = "1c3051315711b5fb0f80086d7f7dab3639a8ba438a74ab4ec4558ce3180d76f2"

HISTORICAL_RECEIPT_PATH = "/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_preanalysis_blind_receipt.json"
HISTORICAL_RECEIPT_SHA = "5f6f1087888e73a0304f91b07d3a8b6ebaf7ca9b7701e4ab4de714dc158e0e25"

FROZEN_20_FALSE_FLAGS: Dict[str, bool] = {
    "RISK_LIVE_TRADING_ENABLED": False,
    "trade_signal_allowed": False,
    "paper_trading_allowed": False,
    "live_trading_allowed": False,
    "execution_engine_allowed": False,
    "private_api_allowed": False,
    "authenticated_api_allowed": False,
    "order_api_allowed": False,
    "alpha_interpretation_allowed": False,
    "execution_feasibility_claim_allowed": False,
    "net_cost_or_profit_claim_allowed": False,
    "replay_allowed": False,
    "point_in_time_directional_replay_allowed": False,
    "alpha_candidate_allowed": False,
    "alpha_validated_allowed": False,
    "network_collection_allowed": False,
    "deployment_allowed": False,
    "ssh_allowed": False,
    "commit_allowed": False,
    "push_allowed": False,
}


def _link_or_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def mutate_mirror_file(target: Path, new_content: bytes | str) -> None:
    if target.exists() or target.is_symlink():
        target.unlink()
    if isinstance(new_content, str):
        target.write_text(new_content, encoding="utf-8")
    else:
        target.write_bytes(new_content)


@dataclass(frozen=True)
class CanonicalW20Mirror:
    project_root: Path
    candidate_root: Path
    w2_0_design_path: Path
    w2_0_design_sha: str
    w2_0_plan_path: Path
    w2_0_plan_sha: str
    w2_design_path: Path
    w2_design_sha: str
    w2_plan_path: Path
    w2_plan_sha: str
    w2_network_auth_path: Path
    w2_network_auth_sha: str
    candidate_manifest_path: Path
    candidate_manifest_sha: str
    external_audit_path: Path
    external_audit_sha: str
    historical_receipt_path: Path
    historical_receipt_sha: str

    def get_admission_kwargs(self) -> Dict[str, Any]:
        return {
            "project_root": self.project_root,
            "candidate_root": self.candidate_root,
            "w2_0_design_path": self.w2_0_design_path,
            "w2_0_design_sha": self.w2_0_design_sha,
            "w2_0_plan_path": self.w2_0_plan_path,
            "w2_0_plan_sha": self.w2_0_plan_sha,
            "w2_design_path": self.w2_design_path,
            "w2_design_sha": self.w2_design_sha,
            "w2_plan_path": self.w2_plan_path,
            "w2_plan_sha": self.w2_plan_sha,
            "w2_network_auth_path": self.w2_network_auth_path,
            "w2_network_auth_sha": self.w2_network_auth_sha,
            "candidate_manifest_sha": self.candidate_manifest_sha,
            "external_audit_path": self.external_audit_path,
            "external_audit_sha": self.external_audit_sha,
            "historical_receipt_path": self.historical_receipt_path,
            "historical_receipt_sha": self.historical_receipt_sha,
        }


def create_canonical_w2_0_mirror(tmp_path: Path, project_root: Path = Path(".")) -> CanonicalW20Mirror:
    """Create a linked/copied mirror of the verified W2 candidate root and exact authority files."""
    mirror_root = tmp_path / "workspace_mirror"
    mirror_root.mkdir(parents=True, exist_ok=True)

    # 1. In-workspace authority files
    w2_0_design = mirror_root / W2_0_DESIGN_PATH
    _link_or_copy(project_root / W2_0_DESIGN_PATH, w2_0_design)
    assert hashlib.sha256(w2_0_design.read_bytes()).hexdigest() == W2_0_DESIGN_SHA

    w2_0_plan = mirror_root / W2_0_PLAN_PATH
    _link_or_copy(project_root / W2_0_PLAN_PATH, w2_0_plan)
    assert hashlib.sha256(w2_0_plan.read_bytes()).hexdigest() == W2_0_PLAN_SHA

    w2_design = mirror_root / W2_DESIGN_PATH
    _link_or_copy(project_root / W2_DESIGN_PATH, w2_design)
    assert hashlib.sha256(w2_design.read_bytes()).hexdigest() == W2_DESIGN_SHA

    w2_plan = mirror_root / W2_PLAN_PATH
    _link_or_copy(project_root / W2_PLAN_PATH, w2_plan)
    assert hashlib.sha256(w2_plan.read_bytes()).hexdigest() == W2_PLAN_SHA

    w2_network_auth = mirror_root / W2_NETWORK_AUTH_PATH
    _link_or_copy(project_root / W2_NETWORK_AUTH_PATH, w2_network_auth)
    assert hashlib.sha256(w2_network_auth.read_bytes()).hexdigest() == W2_NETWORK_AUTH_SHA

    # 2. Upstream authority files needed by load_verified_w2_evidence and verify_c_input
    from tests.research.external_signal_shadow.stage1_6f_w2_test_support import (
        B_SOURCE_EXPORT_RELATIVE,
        C_COMPLETED_ROOT_RELATIVE,
        CANONICAL_002_RELATIVE_PATH,
        FROZEN_AUTHORITY_REGISTRY,
    )
    for rel_path, expected_sha in FROZEN_AUTHORITY_REGISTRY.items():
        src_file = project_root / rel_path
        if src_file.is_file():
            dst_file = mirror_root / rel_path
            _link_or_copy(src_file, dst_file)
            actual_sha = hashlib.sha256(dst_file.read_bytes()).hexdigest()
            assert actual_sha == expected_sha, f"Mirrored SHA mismatch: {rel_path}"

    dir_roots = [
        Path(CANONICAL_002_RELATIVE_PATH),
        Path(C_COMPLETED_ROOT_RELATIVE),
        Path(B_SOURCE_EXPORT_RELATIVE),
    ]
    for dir_rel in dir_roots:
        src_dir = project_root / dir_rel
        if src_dir.is_dir():
            for dirpath, _, filenames in os.walk(src_dir):
                for f in filenames:
                    sp = Path(dirpath) / f
                    rel_to_root = sp.relative_to(project_root)
                    dp = mirror_root / rel_to_root
                    _link_or_copy(sp, dp)

    _link_or_copy(project_root / "configs/base.py", mirror_root / "configs/base.py")

    # 3. Link candidate root files
    src_candidate_root = project_root / W2_CANDIDATE_ROOT_PATH
    dst_candidate_root = mirror_root / W2_CANDIDATE_ROOT_PATH
    dst_candidate_root.mkdir(parents=True, exist_ok=True)

    manifest_src = src_candidate_root / "candidate_manifest.json"
    manifest_dst = dst_candidate_root / "candidate_manifest.json"
    _link_or_copy(manifest_src, manifest_dst)
    assert hashlib.sha256(manifest_dst.read_bytes()).hexdigest() == W2_CANDIDATE_MANIFEST_SHA

    # Link zips and csvs directories
    (dst_candidate_root / "zips").mkdir(parents=True, exist_ok=True)
    for zf in (src_candidate_root / "zips").glob("*.zip"):
        _link_or_copy(zf, dst_candidate_root / "zips" / zf.name)

    (dst_candidate_root / "csvs").mkdir(parents=True, exist_ok=True)
    for cf in (src_candidate_root / "csvs").glob("*.csv"):
        _link_or_copy(cf, dst_candidate_root / "csvs" / cf.name)

    # External audit and receipt are accessed at their immutable external paths
    ext_audit = Path(EXTERNAL_AUDIT_PATH)
    assert ext_audit.is_file()
    assert hashlib.sha256(ext_audit.read_bytes()).hexdigest() == EXTERNAL_AUDIT_SHA

    hist_receipt = Path(HISTORICAL_RECEIPT_PATH)
    assert hist_receipt.is_file()
    assert hashlib.sha256(hist_receipt.read_bytes()).hexdigest() == HISTORICAL_RECEIPT_SHA

    return CanonicalW20Mirror(
        project_root=mirror_root,
        candidate_root=dst_candidate_root,
        w2_0_design_path=w2_0_design,
        w2_0_design_sha=W2_0_DESIGN_SHA,
        w2_0_plan_path=w2_0_plan,
        w2_0_plan_sha=W2_0_PLAN_SHA,
        w2_design_path=w2_design,
        w2_design_sha=W2_DESIGN_SHA,
        w2_plan_path=w2_plan,
        w2_plan_sha=W2_PLAN_SHA,
        w2_network_auth_path=w2_network_auth,
        w2_network_auth_sha=W2_NETWORK_AUTH_SHA,
        candidate_manifest_path=manifest_dst,
        candidate_manifest_sha=W2_CANDIDATE_MANIFEST_SHA,
        external_audit_path=ext_audit,
        external_audit_sha=EXTERNAL_AUDIT_SHA,
        historical_receipt_path=hist_receipt,
        historical_receipt_sha=HISTORICAL_RECEIPT_SHA,
    )
