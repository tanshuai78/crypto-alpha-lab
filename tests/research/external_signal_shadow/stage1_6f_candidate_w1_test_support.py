"""Test support module for Stage 1.6F candidate admission and W1 descriptive diagnostics.

Implements Rule 15 canonical fixture derivation, mirroring, and single declared mutation.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Dict

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    VerifiedCInput,
    verify_c_input,
)

FROZEN_PARENT_F_DESIGN_PATH = "docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md"
FROZEN_PARENT_F_DESIGN_SHA = "87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c"

FROZEN_SCHEMA_DELTA_PATH = "docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md"
FROZEN_SCHEMA_DELTA_SHA = "8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628"

FROZEN_F_PLAN_PATH = "docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md"
FROZEN_F_PLAN_SHA = "6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f"

FROZEN_EXPANSION_DESIGN_PATH = "docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md"
FROZEN_EXPANSION_DESIGN_SHA = "1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4"

FROZEN_EXPANSION_PLAN_PATH = "docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md"
FROZEN_EXPANSION_PLAN_SHA = "fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d"

FROZEN_ADMISSION_DESIGN_PATH = "docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md"
FROZEN_ADMISSION_DESIGN_SHA = "dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097"

CANONICAL_CANDIDATE_RELATIVE_PATH = "data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002"
CANONICAL_CANDIDATE_MANIFEST_SHA = "b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67"

FROZEN_NETWORK_AUTH_PATH = "configs/authorizations/network_auth_expansion_run_20260917_002.json"
FROZEN_NETWORK_AUTH_SHA = "8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6"

C_COMPLETED_ROOT_RELATIVE = "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z"
B_SOURCE_EXPORT_RELATIVE = "data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090"
COVERAGE_MATRIX_RELATIVE = "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json"
REEF_MANIFEST_RELATIVE = "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json"

FROZEN_AUTHORITY_REGISTRY: Dict[str, str] = {
    FROZEN_PARENT_F_DESIGN_PATH: FROZEN_PARENT_F_DESIGN_SHA,
    FROZEN_SCHEMA_DELTA_PATH: FROZEN_SCHEMA_DELTA_SHA,
    FROZEN_F_PLAN_PATH: FROZEN_F_PLAN_SHA,
    FROZEN_EXPANSION_DESIGN_PATH: FROZEN_EXPANSION_DESIGN_SHA,
    FROZEN_EXPANSION_PLAN_PATH: FROZEN_EXPANSION_PLAN_SHA,
    FROZEN_ADMISSION_DESIGN_PATH: FROZEN_ADMISSION_DESIGN_SHA,
    f"{CANONICAL_CANDIDATE_RELATIVE_PATH}/candidate_manifest.json": CANONICAL_CANDIDATE_MANIFEST_SHA,
    FROZEN_NETWORK_AUTH_PATH: FROZEN_NETWORK_AUTH_SHA,
    f"{C_COMPLETED_ROOT_RELATIVE}/completion_manifest.json": "226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0",
    f"{C_COMPLETED_ROOT_RELATIVE}/source_export_receipt.json": "07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e",
    f"{B_SOURCE_EXPORT_RELATIVE}/sealed_export_manifest.json": "1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be",
    COVERAGE_MATRIX_RELATIVE: "b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8",
    REEF_MANIFEST_RELATIVE: "9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f",
    "src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py": "84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3",
    "src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py": "00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f",
}


def _link_or_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def create_canonical_project_mirror(
    tmp_path: Path,
    *,
    project_root: Path | None = None,
) -> Path:
    """Build canonical temporary mirror using hard links or copies of upstream bytes."""
    root = project_root or Path.cwd()
    mirror_root = tmp_path / "mirror_root"
    mirror_root.mkdir(parents=True, exist_ok=True)

    # 1. Mirror individual authority files
    for rel_path, expected_sha in FROZEN_AUTHORITY_REGISTRY.items():
        src_file = root / rel_path
        if not src_file.is_file():
            raise FileNotFoundError(f"Missing canonical source authority file: {src_file}")
        dst_file = mirror_root / rel_path
        _link_or_copy(src_file, dst_file)
        actual_sha = hashlib.sha256(dst_file.read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(f"Mirrored authority SHA mismatch: {rel_path}: {actual_sha} != {expected_sha}")

    # 2. Mirror canonical directories
    dir_roots = [
        Path(CANONICAL_CANDIDATE_RELATIVE_PATH),
        Path(C_COMPLETED_ROOT_RELATIVE),
        Path(B_SOURCE_EXPORT_RELATIVE),
    ]
    for dir_rel in dir_roots:
        src_dir = root / dir_rel
        if not src_dir.is_dir():
            raise FileNotFoundError(f"Missing canonical source directory: {src_dir}")
        for dirpath, _, filenames in os.walk(src_dir):
            for f in filenames:
                sp = Path(dirpath) / f
                rel_to_root = sp.relative_to(root)
                dp = mirror_root / rel_to_root
                _link_or_copy(sp, dp)

    # 3. Mirror configs/base.py
    _link_or_copy(root / "configs/base.py", mirror_root / "configs/base.py")

    return mirror_root


def mutate_mirror_file(file_path: Path, new_content: bytes) -> None:
    """Safely unlink destination first to break hard-link, then write mutated bytes."""
    if file_path.exists() or file_path.is_symlink():
        file_path.unlink()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(new_content)


def load_canonical_verified_c_input(mirror_root: Path) -> VerifiedCInput:
    """Construct canonical VerifiedCInput from canonical mirrored C/B roots."""
    return verify_c_input(
        project_root=mirror_root,
        source_export=mirror_root / B_SOURCE_EXPORT_RELATIVE,
        completed_root=mirror_root / C_COMPLETED_ROOT_RELATIVE,
    )
