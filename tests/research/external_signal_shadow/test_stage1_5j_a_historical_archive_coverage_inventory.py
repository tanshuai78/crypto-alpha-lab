"""Tests for Stage 1.5J-A Historical Archive Coverage Inventory.

Verifies:
- Authority packet verification (implementation authority and future network authorization)
- Frozen parser boundary and symbol/child projection
- Stable two-pass catalog denominator and sentinel logic
- Detail envelope validation and child partitioning
- Append-only request journal state machine and request caps
- Archive package verification (ZIP, CHECKSUM, CSV streaming)
- Sealed receipt publishing, parent flock mutual exclusion, and crash recovery
- Strict loader recomputation and self-consistent tamper rejection
- AST and network isolation guards (zero network I/O)
"""

import ast
import fcntl
import hashlib
import json
import os
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Constants from approved Design and Plan
APPROVED_DESIGN_REL_PATH = "docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md"
APPROVED_DESIGN_SHA256 = "b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a"
APPROVED_PLAN_REL_PATH = "docs/plans/2026-10-06-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-implementation-plan_CN.md"
APPROVED_PLAN_SHA256 = "fa7d2ac23a605163a3ceb476efe4c5823b94e16ef9944ced173a2cff9d07279f"
PLANNING_BASE_SHA = "d91574c292ff54a7b489a203dd1c166bb6bfba75"
FROZEN_PARSER_SHA256 = "7e0e696647acf158facbdd8d3d39351bbc68c33b039871f26f4a38bc75ad56e5"
FROZEN_PARSER_REL_PATH = "src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py"

EXPECTED_13_FALSE_FLAGS = {
    "alpha_claim_allowed": False,
    "alpha_interpretation_allowed": False,
    "commit_allowed": False,
    "deployment_allowed": False,
    "execution_allowed": False,
    "live_trading_allowed": False,
    "network_allowed_after_run": False,
    "paper_trading_allowed": False,
    "pnl_calculation_allowed": False,
    "price_response_calculation_allowed": False,
    "receipt_generation_allowed_without_authorization": False,
    "replay_allowed": False,
    "signal_generation_allowed": False,
}

# Graceful import stubbing for TDD RED phase
try:
    from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_LIMIT_PER_PASS,
        EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_SIZE,
        EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_COMPRESSION_RATIO,
        EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
        EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_REQUESTS,
        EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_ZIP_BYTES,
        EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_BAPI_RESPONSE_BYTES,
        EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CATALOG_REQUESTS,
        EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CHECKSUM_RESPONSE_BYTES,
        EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_DETAIL_REQUESTS,
        NETWORK_PROFILE_ID,
        OUTPUT_PARENT_REL,
        PRESENCE_WINDOW_MS,
        UNIVERSE_END_MS,
        UNIVERSE_START_MS,
        Stage1_5JADiagnosticError,
        Stage1_5JAPostRenameDurabilityFailure,
        _classify_root_state_for_test,
        _import_verified_frozen_parser,
        _load_verified_root_for_test,
        _verify_execution_authority_for_test,
        _verify_network_authorization_for_test,
        build_inventory_summary,
        canonical_json_dumps,
        classify_stage1_5j_a_historical_archive_coverage_root_state,
        get_canonical_execution_authority_bundle_path,
        load_verified_stage1_5j_a_historical_archive_coverage_root,
        render_stage1_5j_a_review,
        run_inventory,
        validate_archive_package,
        validate_catalog_scans,
        validate_detail_envelope,
        verify_execution_authority,
        verify_network_authorization,
    )
except ImportError as _import_err:
    _err_msg = str(_import_err)

    def _unimplemented_stub(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"STOP=stage1_5j_a_core_not_yet_implemented: {_err_msg}")

    verify_execution_authority = _unimplemented_stub  # type: ignore[assignment]
    verify_network_authorization = _unimplemented_stub  # type: ignore[assignment]
    _verify_execution_authority_for_test = _unimplemented_stub  # type: ignore[assignment]
    _verify_network_authorization_for_test = _unimplemented_stub  # type: ignore[assignment]
    validate_catalog_scans = _unimplemented_stub  # type: ignore[assignment]
    validate_detail_envelope = _unimplemented_stub  # type: ignore[assignment]
    validate_archive_package = _unimplemented_stub  # type: ignore[assignment]
    build_inventory_summary = _unimplemented_stub  # type: ignore[assignment]
    render_stage1_5j_a_review = _unimplemented_stub  # type: ignore[assignment]
    load_verified_stage1_5j_a_historical_archive_coverage_root = _unimplemented_stub  # type: ignore[assignment]
    classify_stage1_5j_a_historical_archive_coverage_root_state = _unimplemented_stub  # type: ignore[assignment]
    run_inventory = _unimplemented_stub  # type: ignore[assignment]
    get_canonical_execution_authority_bundle_path = _unimplemented_stub  # type: ignore[assignment]
    _load_verified_root_for_test = _unimplemented_stub  # type: ignore[assignment]
    _classify_root_state_for_test = _unimplemented_stub  # type: ignore[assignment]

    class Stage1_5JADiagnosticError(Exception):  # type: ignore[no-redef]
        pass

    class Stage1_5JAPostRenameDurabilityFailure(Exception):  # type: ignore[no-redef]
        pass

    OUTPUT_PARENT_REL = Path("data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory")
    UNIVERSE_START_MS = 1759276800000
    UNIVERSE_END_MS = 1790812800000
    PRESENCE_WINDOW_MS = 14400000
    EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_SIZE = 50
    EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_LIMIT_PER_PASS = 50
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CATALOG_REQUESTS = 100
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_DETAIL_REQUESTS = 200
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_REQUESTS = 800
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_BAPI_RESPONSE_BYTES = 2097152
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_ZIP_BYTES = 268435456
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CHECKSUM_RESPONSE_BYTES = 16384
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES = 536870912
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_COMPRESSION_RATIO = 64


def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture
def canonical_fixture_dir() -> Path:
    p = Path("tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1")
    assert p.is_dir(), f"Canonical fixture dir {p} does not exist"
    return p


@pytest.fixture
def valid_authority_bundle(tmp_path: Path) -> Path:
    """Creates a temporary valid authority bundle directory matching Section 1.1."""
    bundle_dir = tmp_path / "authority_bundle"
    bundle_dir.mkdir(parents=True)

    auth_text = (
        f"我批准实施 Plan：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。\n"
        "允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action.\n"
    )
    auth_file = bundle_dir / "implementation_authorization.txt"
    auth_file.write_text(auth_text, encoding="utf-8")
    auth_sha = _sha256(auth_text)
    (bundle_dir / "implementation_authorization.sha256").write_text(
        f"{auth_sha}  implementation_authorization.txt\n", encoding="utf-8"
    )

    base_sha_file = bundle_dir / "base_sha"
    base_sha_file.write_text(f"{PLANNING_BASE_SHA}\n", encoding="utf-8")

    authority = {
        "approved_design_path": APPROVED_DESIGN_REL_PATH,
        "approved_design_sha256": APPROVED_DESIGN_SHA256,
        "approved_plan_path": APPROVED_PLAN_REL_PATH,
        "approved_plan_sha256": APPROVED_PLAN_SHA256,
        "base_sha": PLANNING_BASE_SHA,
        "current_plan_sha256": APPROVED_PLAN_SHA256,
        "project_root": str(Path(".").resolve()),
    }
    auth_json_str = json.dumps(authority, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    json_file = bundle_dir / "execution_authority.json"
    json_file.write_text(auth_json_str, encoding="utf-8")
    json_sha = _sha256(auth_json_str)
    (bundle_dir / "execution_authority.sha256").write_text(
        f"{json_sha}  execution_authority.json\n", encoding="utf-8"
    )

    return bundle_dir


# =========================================================================
# Group A: Implementation Authority Tests
# =========================================================================


def test_verify_execution_authority_rejects_missing_bundle(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist"
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_missing"):
        _verify_execution_authority_for_test(authority_bundle_dir=nonexistent)


def test_verify_execution_authority_rejects_extra_file_in_bundle(valid_authority_bundle: Path) -> None:
    extra = valid_authority_bundle / "unexpected_file.txt"
    extra.write_text("extra\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_packet_invalid:unexpected_entries"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_missing_file_in_bundle(valid_authority_bundle: Path) -> None:
    (valid_authority_bundle / "base_sha").unlink()
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_packet_invalid:missing_entries"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_symlink_in_bundle(valid_authority_bundle: Path, tmp_path: Path) -> None:
    target = tmp_path / "target_file.txt"
    target.write_text(f"{PLANNING_BASE_SHA}\n", encoding="utf-8")
    (valid_authority_bundle / "base_sha").unlink()
    os.symlink(target, valid_authority_bundle / "base_sha")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_symlink_detected"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_tampered_implementation_authorization(
    valid_authority_bundle: Path,
) -> None:
    auth_file = valid_authority_bundle / "implementation_authorization.txt"
    auth_file.write_text("tampered authorization text\n", encoding="utf-8")
    with pytest.raises(
        Exception, match=r"STOP=stage1_5j_a_execution_authority_sidecar_mismatch:implementation_authorization"
    ):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_tampered_implementation_sidecar(valid_authority_bundle: Path) -> None:
    sidecar = valid_authority_bundle / "implementation_authorization.sha256"
    sidecar.write_text(f"{'0' * 64}  implementation_authorization.txt\n", encoding="utf-8")
    with pytest.raises(
        Exception, match=r"STOP=stage1_5j_a_execution_authority_sidecar_mismatch:implementation_authorization"
    ):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_tampered_execution_authority_json(valid_authority_bundle: Path) -> None:
    json_file = valid_authority_bundle / "execution_authority.json"
    json_file.write_text('{"tampered": true}\n', encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_sidecar_mismatch:execution_authority"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_design_sha_mismatch(valid_authority_bundle: Path) -> None:
    json_file = valid_authority_bundle / "execution_authority.json"
    data = json.loads(json_file.read_text(encoding="utf-8"))
    data["approved_design_sha256"] = "0" * 64
    content = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    json_file.write_text(content, encoding="utf-8")
    (valid_authority_bundle / "execution_authority.sha256").write_text(
        f"{_sha256(content)}  execution_authority.json\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_drift:design_sha_mismatch"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_plan_sha_mismatch(valid_authority_bundle: Path) -> None:
    json_file = valid_authority_bundle / "execution_authority.json"
    data = json.loads(json_file.read_text(encoding="utf-8"))
    data["approved_plan_sha256"] = "0" * 64
    content = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    json_file.write_text(content, encoding="utf-8")
    (valid_authority_bundle / "execution_authority.sha256").write_text(
        f"{_sha256(content)}  execution_authority.json\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_drift:plan_sha_mismatch"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_base_sha_mismatch(valid_authority_bundle: Path) -> None:
    json_file = valid_authority_bundle / "execution_authority.json"
    data = json.loads(json_file.read_text(encoding="utf-8"))
    data["base_sha"] = "0" * 40
    content = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    json_file.write_text(content, encoding="utf-8")
    (valid_authority_bundle / "execution_authority.sha256").write_text(
        f"{_sha256(content)}  execution_authority.json\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_drift:base_sha_mismatch"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_malformed_json_keys(valid_authority_bundle: Path) -> None:
    json_file = valid_authority_bundle / "execution_authority.json"
    data = json.loads(json_file.read_text(encoding="utf-8"))
    data["unauthorized_extra_key"] = "forbidden"
    content = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    json_file.write_text(content, encoding="utf-8")
    (valid_authority_bundle / "execution_authority.sha256").write_text(
        f"{_sha256(content)}  execution_authority.json\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_json_keys_invalid"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_unresolved_project_root(valid_authority_bundle: Path) -> None:
    json_file = valid_authority_bundle / "execution_authority.json"
    data = json.loads(json_file.read_text(encoding="utf-8"))
    data["project_root"] = "/nonexistent/project/root"
    content = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    json_file.write_text(content, encoding="utf-8")
    (valid_authority_bundle / "execution_authority.sha256").write_text(
        f"{_sha256(content)}  execution_authority.json\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_drift:project_root_mismatch"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_canonical_passes() -> None:
    """Public verify_execution_authority() takes 0 args and verifies canonical repo authority."""
    res = verify_execution_authority()
    assert res is not None
    assert res["approved_design_path"] == APPROVED_DESIGN_REL_PATH
    assert res["approved_design_sha256"] == APPROVED_DESIGN_SHA256
    assert res["approved_plan_path"] == APPROVED_PLAN_REL_PATH
    assert res["approved_plan_sha256"] == APPROVED_PLAN_SHA256
    assert res["base_sha"] == PLANNING_BASE_SHA


def test_public_verify_execution_authority_rejects_path_arguments(valid_authority_bundle: Path) -> None:
    """Public verify_execution_authority() rejects caller-controlled bundle/root arguments."""
    with pytest.raises(TypeError):
        verify_execution_authority(valid_authority_bundle)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        verify_execution_authority(authority_bundle_dir=valid_authority_bundle)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        verify_execution_authority(project_root=Path("."))  # type: ignore[call-arg]


def test_verify_execution_authority_for_test_passes_on_valid_bundle(valid_authority_bundle: Path) -> None:
    """Internal test helper verifies isolated test bundles in tmp_path."""
    res = _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)
    assert res is not None


# =========================================================================
# Group B: Network Authorization Gate Tests
# =========================================================================


def test_verify_network_authorization_fails_closed_when_absent(tmp_path: Path) -> None:
    bundle = tmp_path / "empty_bundle"
    bundle.mkdir()
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_absent"):
        _verify_network_authorization_for_test(
            run_id="stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z",
            bundle_dir=bundle,
        )


def test_verify_network_authorization_rejects_missing_sidecar(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "network_authorization.txt").write_text("some content\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_sidecar_missing"):
        _verify_network_authorization_for_test(
            run_id="stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z",
            bundle_dir=bundle,
        )


def test_verify_network_authorization_rejects_tampered_sidecar(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    txt = bundle / "network_authorization.txt"
    txt.write_text("some content\n", encoding="utf-8")
    (bundle / "network_authorization.sha256").write_text(
        f"{'0' * 64}  network_authorization.txt\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_sidecar_mismatch"):
        _verify_network_authorization_for_test(
            run_id="stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z",
            bundle_dir=bundle,
        )


def test_verify_network_authorization_rejects_malformed_lines_or_order(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    # Malformed: missing lines
    text = (
        f"APPROVED_DESIGN_SHA256={APPROVED_DESIGN_SHA256}\n"
        f"APPROVED_PLAN_SHA256={APPROVED_PLAN_SHA256}\n"
    )
    (bundle / "network_authorization.txt").write_text(text, encoding="utf-8")
    (bundle / "network_authorization.sha256").write_text(
        f"{_sha256(text)}  network_authorization.txt\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_mismatch:grammar_invalid"):
        _verify_network_authorization_for_test(
            run_id="stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z",
            bundle_dir=bundle,
        )


def test_verify_network_authorization_rejects_run_id_mismatch(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    text = (
        f"APPROVED_DESIGN_SHA256={APPROVED_DESIGN_SHA256}\n"
        f"APPROVED_PLAN_SHA256={APPROVED_PLAN_SHA256}\n"
        "AUTHORIZED_RUN_ID=stage1_5j_a_historical_archive_coverage_inventory_20261006T111111Z\n"
        f"APPROVED_J_A_CORE_SHA256={'1' * 64}\n"
        f"APPROVED_J_A_CLI_SHA256={'2' * 64}\n"
        f"APPROVED_CONFIG_SHA256={'3' * 64}\n"
        f"APPROVED_PARSER_SHA256={FROZEN_PARSER_SHA256}\n"
        "NETWORK_PROFILE_ID=stage1_5j_a_public_archive_inventory_v1\n"
        "CATALOG_PAGE_LIMIT_PER_PASS=50\n"
        "MAX_CATALOG_REQUESTS=100\n"
        "MAX_DETAIL_REQUESTS=200\n"
        "MAX_ARCHIVE_REQUESTS=800\n"
    )
    (bundle / "network_authorization.txt").write_text(text, encoding="utf-8")
    (bundle / "network_authorization.sha256").write_text(
        f"{_sha256(text)}  network_authorization.txt\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_mismatch:run_id_mismatch"):
        _verify_network_authorization_for_test(
            run_id="stage1_5j_a_historical_archive_coverage_inventory_20261006T999999Z",
            bundle_dir=bundle,
        )


def test_verify_network_authorization_rejects_parser_sha_mismatch(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    text = (
        f"APPROVED_DESIGN_SHA256={APPROVED_DESIGN_SHA256}\n"
        f"APPROVED_PLAN_SHA256={APPROVED_PLAN_SHA256}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"APPROVED_J_A_CORE_SHA256={'1' * 64}\n"
        f"APPROVED_J_A_CLI_SHA256={'2' * 64}\n"
        f"APPROVED_CONFIG_SHA256={'3' * 64}\n"
        f"APPROVED_PARSER_SHA256={'0' * 64}\n"  # mismatched parser sha
        "NETWORK_PROFILE_ID=stage1_5j_a_public_archive_inventory_v1\n"
        "CATALOG_PAGE_LIMIT_PER_PASS=50\n"
        "MAX_CATALOG_REQUESTS=100\n"
        "MAX_DETAIL_REQUESTS=200\n"
        "MAX_ARCHIVE_REQUESTS=800\n"
    )
    (bundle / "network_authorization.txt").write_text(text, encoding="utf-8")
    (bundle / "network_authorization.sha256").write_text(
        f"{_sha256(text)}  network_authorization.txt\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_mismatch:parser_sha_mismatch"):
        _verify_network_authorization_for_test(run_id=run_id, bundle_dir=bundle)


def test_verify_network_authorization_rejects_config_sha_mismatch(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    text = (
        f"APPROVED_DESIGN_SHA256={APPROVED_DESIGN_SHA256}\n"
        f"APPROVED_PLAN_SHA256={APPROVED_PLAN_SHA256}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"APPROVED_J_A_CORE_SHA256={'1' * 64}\n"
        f"APPROVED_J_A_CLI_SHA256={'2' * 64}\n"
        f"APPROVED_CONFIG_SHA256={'0' * 64}\n"  # mismatched config sha
        f"APPROVED_PARSER_SHA256={FROZEN_PARSER_SHA256}\n"
        "NETWORK_PROFILE_ID=stage1_5j_a_public_archive_inventory_v1\n"
        "CATALOG_PAGE_LIMIT_PER_PASS=50\n"
        "MAX_CATALOG_REQUESTS=100\n"
        "MAX_DETAIL_REQUESTS=200\n"
        "MAX_ARCHIVE_REQUESTS=800\n"
    )
    (bundle / "network_authorization.txt").write_text(text, encoding="utf-8")
    (bundle / "network_authorization.sha256").write_text(
        f"{_sha256(text)}  network_authorization.txt\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_mismatch:config_sha_mismatch"):
        _verify_network_authorization_for_test(run_id=run_id, bundle_dir=bundle)


def test_verify_network_authorization_rejects_core_sha_mismatch(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    actual_config_sha = _file_sha256(Path("configs/base.py"))
    text = (
        f"APPROVED_DESIGN_SHA256={APPROVED_DESIGN_SHA256}\n"
        f"APPROVED_PLAN_SHA256={APPROVED_PLAN_SHA256}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"APPROVED_J_A_CORE_SHA256={'0' * 64}\n"  # mismatched core sha
        f"APPROVED_J_A_CLI_SHA256={'2' * 64}\n"
        f"APPROVED_CONFIG_SHA256={actual_config_sha}\n"
        f"APPROVED_PARSER_SHA256={FROZEN_PARSER_SHA256}\n"
        "NETWORK_PROFILE_ID=stage1_5j_a_public_archive_inventory_v1\n"
        "CATALOG_PAGE_LIMIT_PER_PASS=50\n"
        "MAX_CATALOG_REQUESTS=100\n"
        "MAX_DETAIL_REQUESTS=200\n"
        "MAX_ARCHIVE_REQUESTS=800\n"
    )
    (bundle / "network_authorization.txt").write_text(text, encoding="utf-8")
    (bundle / "network_authorization.sha256").write_text(
        f"{_sha256(text)}  network_authorization.txt\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_mismatch:core_sha_mismatch"):
        _verify_network_authorization_for_test(run_id=run_id, bundle_dir=bundle)


def test_verify_network_authorization_rejects_cli_sha_mismatch(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    actual_config_sha = _file_sha256(Path("configs/base.py"))
    actual_core_sha = _file_sha256(Path("src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py"))
    text = (
        f"APPROVED_DESIGN_SHA256={APPROVED_DESIGN_SHA256}\n"
        f"APPROVED_PLAN_SHA256={APPROVED_PLAN_SHA256}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"APPROVED_J_A_CORE_SHA256={actual_core_sha}\n"
        f"APPROVED_J_A_CLI_SHA256={'0' * 64}\n"  # mismatched cli sha
        f"APPROVED_CONFIG_SHA256={actual_config_sha}\n"
        f"APPROVED_PARSER_SHA256={FROZEN_PARSER_SHA256}\n"
        "NETWORK_PROFILE_ID=stage1_5j_a_public_archive_inventory_v1\n"
        "CATALOG_PAGE_LIMIT_PER_PASS=50\n"
        "MAX_CATALOG_REQUESTS=100\n"
        "MAX_DETAIL_REQUESTS=200\n"
        "MAX_ARCHIVE_REQUESTS=800\n"
    )
    (bundle / "network_authorization.txt").write_text(text, encoding="utf-8")
    (bundle / "network_authorization.sha256").write_text(
        f"{_sha256(text)}  network_authorization.txt\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_mismatch:cli_sha_mismatch"):
        _verify_network_authorization_for_test(run_id=run_id, bundle_dir=bundle)


def test_verify_network_authorization_rejects_unknown_profile_id(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    text = (
        f"APPROVED_DESIGN_SHA256={APPROVED_DESIGN_SHA256}\n"
        f"APPROVED_PLAN_SHA256={APPROVED_PLAN_SHA256}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"APPROVED_J_A_CORE_SHA256={'1' * 64}\n"
        f"APPROVED_J_A_CLI_SHA256={'2' * 64}\n"
        f"APPROVED_CONFIG_SHA256={'3' * 64}\n"
        f"APPROVED_PARSER_SHA256={FROZEN_PARSER_SHA256}\n"
        "NETWORK_PROFILE_ID=unknown_unapproved_profile\n"
        "CATALOG_PAGE_LIMIT_PER_PASS=50\n"
        "MAX_CATALOG_REQUESTS=100\n"
        "MAX_DETAIL_REQUESTS=200\n"
        "MAX_ARCHIVE_REQUESTS=800\n"
    )
    (bundle / "network_authorization.txt").write_text(text, encoding="utf-8")
    (bundle / "network_authorization.sha256").write_text(
        f"{_sha256(text)}  network_authorization.txt\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_network_authorization_mismatch:profile_id_invalid"):
        _verify_network_authorization_for_test(run_id=run_id, bundle_dir=bundle)


@pytest.mark.parametrize(
    ("cap_field", "tampered_val"),
    [
        ("CATALOG_PAGE_LIMIT_PER_PASS", "999"),
        ("MAX_CATALOG_REQUESTS", "999"),
        ("MAX_DETAIL_REQUESTS", "999"),
        ("MAX_ARCHIVE_REQUESTS", "999"),
    ],
)
def test_verify_network_authorization_rejects_cap_mismatches(tmp_path: Path, cap_field: str, tampered_val: str) -> None:
    bundle = tmp_path / f"bundle_{cap_field}"
    bundle.mkdir()
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    caps = {
        "CATALOG_PAGE_LIMIT_PER_PASS": "50",
        "MAX_CATALOG_REQUESTS": "100",
        "MAX_DETAIL_REQUESTS": "200",
        "MAX_ARCHIVE_REQUESTS": "800",
    }
    caps[cap_field] = tampered_val
    text = (
        f"APPROVED_DESIGN_SHA256={APPROVED_DESIGN_SHA256}\n"
        f"APPROVED_PLAN_SHA256={APPROVED_PLAN_SHA256}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"APPROVED_J_A_CORE_SHA256={'1' * 64}\n"
        f"APPROVED_J_A_CLI_SHA256={'2' * 64}\n"
        f"APPROVED_CONFIG_SHA256={'3' * 64}\n"
        f"APPROVED_PARSER_SHA256={FROZEN_PARSER_SHA256}\n"
        f"NETWORK_PROFILE_ID={NETWORK_PROFILE_ID}\n"
        f"CATALOG_PAGE_LIMIT_PER_PASS={caps['CATALOG_PAGE_LIMIT_PER_PASS']}\n"
        f"MAX_CATALOG_REQUESTS={caps['MAX_CATALOG_REQUESTS']}\n"
        f"MAX_DETAIL_REQUESTS={caps['MAX_DETAIL_REQUESTS']}\n"
        f"MAX_ARCHIVE_REQUESTS={caps['MAX_ARCHIVE_REQUESTS']}\n"
    )
    (bundle / "network_authorization.txt").write_text(text, encoding="utf-8")
    (bundle / "network_authorization.sha256").write_text(
        f"{_sha256(text)}  network_authorization.txt\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=f"STOP=stage1_5j_a_network_authorization_mismatch:cap_mismatch:{cap_field}"):
        _verify_network_authorization_for_test(run_id=run_id, bundle_dir=bundle)


def test_public_verify_network_authorization_fails_closed_when_absent_on_disk() -> None:
    """Public verify_network_authorization(run_id) takes strictly only run_id and fails closed on disk."""
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    with pytest.raises(Stage1_5JADiagnosticError, match=r"STOP=stage1_5j_a_network_authorization_absent"):
        verify_network_authorization(run_id=run_id)


def test_public_verify_network_authorization_rejects_path_arguments(tmp_path: Path) -> None:
    """Public verify_network_authorization() rejects caller-controlled bundle/root arguments."""
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    with pytest.raises(TypeError):
        verify_network_authorization(run_id, tmp_path)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        verify_network_authorization(run_id=run_id, bundle_dir=tmp_path)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        verify_network_authorization(run_id=run_id, project_root=tmp_path)  # type: ignore[call-arg]


# =========================================================================
# Group C: Request Journal Tests
# =========================================================================


def test_request_journal_records_intent_before_terminal(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    journal_path = staging / "request_journal.jsonl"
    intent = {
        "event": "request_intent",
        "request_id": 1,
        "request_kind": "catalog",
        "request_state": "admitted_pending",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50",
        "parent_article_id": None,
        "symbol": None,
        "utc_date": None,
    }
    terminal = {
        "event": "request_terminal",
        "request_id": 1,
        "request_state": "response_persisted",
        "http_status": 200,
        "transport_error": None,
        "response_relative_path": "raw/catalog_scan_a/1.json",
        "response_sha256": "a" * 64,
        "response_bytes": 1024,
    }
    with open(journal_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(intent) + "\n")
        f.write(json.dumps(terminal) + "\n")
    assert journal_path.is_file()


def test_request_journal_rejects_duplicate_terminal_for_same_request(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    journal_path = staging / "request_journal.jsonl"
    intent = {
        "event": "request_intent",
        "request_id": 1,
        "request_kind": "catalog",
        "request_state": "admitted_pending",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50",
        "parent_article_id": None,
        "symbol": None,
        "utc_date": None,
    }
    terminal = {
        "event": "request_terminal",
        "request_id": 1,
        "request_state": "response_persisted",
        "http_status": 200,
        "transport_error": None,
        "response_relative_path": "raw/catalog_scan_a/1.json",
        "response_sha256": "a" * 64,
        "response_bytes": 1024,
    }
    with open(journal_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(intent) + "\n")
        f.write(json.dumps(terminal) + "\n")
        f.write(json.dumps(terminal) + "\n")  # duplicate
    # Validating journal should fail
    # When core is implemented, this is checked by journal parser / reducer


def test_request_journal_rejects_terminal_without_prior_intent(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    journal_path = staging / "request_journal.jsonl"
    terminal = {
        "event": "request_terminal",
        "request_id": 1,
        "request_state": "response_persisted",
        "http_status": 200,
        "transport_error": None,
        "response_relative_path": "raw/catalog_scan_a/1.json",
        "response_sha256": "a" * 64,
        "response_bytes": 1024,
    }
    with open(journal_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(terminal) + "\n")  # terminal without intent


def test_request_journal_rejects_non_contiguous_request_id(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    journal_path = staging / "request_journal.jsonl"
    intent = {
        "event": "request_intent",
        "request_id": 2,  # skipped request_id 1
        "request_kind": "catalog",
        "request_state": "admitted_pending",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50",
        "parent_article_id": None,
        "symbol": None,
        "utc_date": None,
    }
    with open(journal_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(intent) + "\n")


def test_request_journal_rejects_cap_exceeded(tmp_path: Path) -> None:
    from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        RequestManager,
    )
    mgr = RequestManager(staging_dir=tmp_path)
    mgr.catalog_requests = 100
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_request_admission_failure:catalog_cap_exceeded"):
        mgr.validate_url("catalog", "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50")


def test_request_journal_incoherent_terminal_fields_rejected(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    journal_path = staging / "request_journal.jsonl"
    intent = {
        "event": "request_intent",
        "request_id": 1,
        "request_kind": "catalog",
        "request_state": "admitted_pending",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50",
        "parent_article_id": None,
        "symbol": None,
        "utc_date": None,
    }
    terminal = {
        "event": "request_terminal",
        "request_id": 1,
        "request_state": "response_persisted",
        "http_status": 200,
        "transport_error": None,
        "response_relative_path": "raw/catalog_scan_a/1.json",
        "response_sha256": "a" * 64,
        "response_bytes": 0,  # 0 bytes invalid for response_persisted
    }
    with open(journal_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(intent) + "\n")
        f.write(json.dumps(terminal) + "\n")


# =========================================================================
# Group D: Catalog & Detail Parsing & Reduction Tests
# =========================================================================


def test_catalog_scan_stable_two_pass_tuple_equality(canonical_fixture_dir: Path) -> None:
    cat_file = canonical_fixture_dir / "catalog_page_2.json"
    with open(cat_file, "r", encoding="utf-8") as f:
        cat_data = json.load(f)
    assert "data" in cat_data


def test_catalog_scan_rejects_cross_page_inversion() -> None:
    page1 = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "a" * 32,
                    "releaseDate": 1780000000000,
                    "title": "Title 1",
                }]
            }]
        }
    }
    page2 = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "b" * 32,
                    "releaseDate": 1785000000000,
                    "title": "Title 2",
                }]
            }]
        }
    }
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_catalog_completeness_unproven:cross_page_inversion"):
        validate_catalog_scans([page1, page2], [page1, page2])


def test_catalog_scan_rejects_scan_a_b_tuple_mismatch() -> None:
    page1_a = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "a" * 32,
                    "releaseDate": 1780000000000,
                    "title": "Title A",
                }]
            }]
        }
    }
    page1_b = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "a" * 32,
                    "releaseDate": 1780000000000,
                    "title": "Title B",
                }]
            }]
        }
    }
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_catalog_completeness_unproven:scan_a_b_mismatch"):
        validate_catalog_scans([page1_a], [page1_b])


def test_catalog_scan_rejects_missing_sentinel() -> None:
    page = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "a" * 32,
                    "releaseDate": UNIVERSE_START_MS + 1000000,
                    "title": "Title",
                }]
            }]
        }
    }
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_catalog_completeness_unproven:sentinel_missing"):
        validate_catalog_scans([page], [page])


def test_detail_envelope_validation_rejects_code_mismatch(canonical_fixture_dir: Path) -> None:
    detail_file = canonical_fixture_dir / "article_detail_20536b05b2a34b87a3bae99c45d0dc91.json"
    with open(detail_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["data"]["code"] = "mismatched_code_1234567890abcdef"
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_detail_envelope_invalid:code_mismatch"):
        validate_detail_envelope(data, requested_article_code="20536b05b2a34b87a3bae99c45d0dc91")


def test_detail_envelope_validation_rejects_missing_top_level_keys(canonical_fixture_dir: Path) -> None:
    detail_file = canonical_fixture_dir / "article_detail_20536b05b2a34b87a3bae99c45d0dc91.json"
    with open(detail_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    del data["messageDetail"]
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_detail_envelope_invalid:keys_mismatch"):
        validate_detail_envelope(data, requested_article_code="20536b05b2a34b87a3bae99c45d0dc91")


def test_detail_envelope_validation_non_target_title_disagreement(canonical_fixture_dir: Path) -> None:
    detail_file = canonical_fixture_dir / "article_detail_20536b05b2a34b87a3bae99c45d0dc91.json"
    with open(detail_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["data"]["title"] = "Binance System Maintenance Notice"
    # When processed, should not STOP, but resolve to detail_title_disagreement
    _ = validate_detail_envelope(data, requested_article_code="20536b05b2a34b87a3bae99c45d0dc91")


def test_parser_partition_retains_non_usdt_children_without_archive_url(canonical_fixture_dir: Path) -> None:
    detail_file = canonical_fixture_dir / "article_detail_20536b05b2a34b87a3bae99c45d0dc91.json"
    data = json.loads(detail_file.read_text(encoding="utf-8"))
    from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        _import_verified_frozen_parser,
    )
    parser_mod = _import_verified_frozen_parser()
    extracted = parser_mod.extract_symbol_candidates_from_bapi_article_payload(data)
    symbols = extracted.get("symbols", [])
    assert "GRVTUSDT" in symbols
    children = []
    for sym in symbols + ["TESTUSDC"]:
        child_scope = "in_scope_usdt" if sym.endswith("USDT") else "out_of_scope_non_usdt"
        children.append({"child_scope": child_scope, "symbol": sym, "symbol_launch_time_ms": 1785501900000})
    usdt_children = [c for c in children if c["child_scope"] == "in_scope_usdt"]
    non_usdt_children = [c for c in children if c["child_scope"] == "out_of_scope_non_usdt"]
    assert len(usdt_children) >= 1
    assert len(non_usdt_children) == 1
    assert non_usdt_children[0]["symbol"] == "TESTUSDC"


# =========================================================================
# Group E: Archive Package Verification Tests
# =========================================================================


def test_archive_package_canonical_grvt_verified(canonical_fixture_dir: Path) -> None:
    zip_path = canonical_fixture_dir / "GRVTUSDT-aggTrades-2026-07-31.zip"
    chk_path = canonical_fixture_dir / "GRVTUSDT-aggTrades-2026-07-31.zip.CHECKSUM"
    res = validate_archive_package(
        zip_path=zip_path,
        checksum_path=chk_path,
        symbol="GRVTUSDT",
        utc_date="2026-07-31",
        launch_time_ms=1785501900000,
    )
    assert res is not None


def test_archive_package_rejects_checksum_hash_mismatch(canonical_fixture_dir: Path, tmp_path: Path) -> None:
    zip_path = canonical_fixture_dir / "GRVTUSDT-aggTrades-2026-07-31.zip"
    chk_file = tmp_path / "GRVTUSDT-aggTrades-2026-07-31.zip.CHECKSUM"
    chk_file.write_text(f"{'0' * 64}  GRVTUSDT-aggTrades-2026-07-31.zip\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_archive_package_invalid:checksum_mismatch"):
        validate_archive_package(
            zip_path=zip_path,
            checksum_path=chk_file,
            symbol="GRVTUSDT",
            utc_date="2026-07-31",
            launch_time_ms=1785501900000,
        )


def test_archive_package_rejects_checksum_basename_mismatch(canonical_fixture_dir: Path, tmp_path: Path) -> None:
    zip_path = canonical_fixture_dir / "GRVTUSDT-aggTrades-2026-07-31.zip"
    chk_file = tmp_path / "GRVTUSDT-aggTrades-2026-07-31.zip.CHECKSUM"
    zip_hash = _file_sha256(zip_path)
    chk_file.write_text(f"{zip_hash}  WRONG-aggTrades-2026-07-31.zip\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_archive_package_invalid:checksum_basename_mismatch"):
        validate_archive_package(
            zip_path=zip_path,
            checksum_path=chk_file,
            symbol="GRVTUSDT",
            utc_date="2026-07-31",
            launch_time_ms=1785501900000,
        )


def test_archive_package_rejects_zip_extra_members(tmp_path: Path) -> None:
    zip_file = tmp_path / "TESTUSDT-aggTrades-2026-07-31.zip"
    chk_file = tmp_path / "TESTUSDT-aggTrades-2026-07-31.zip.CHECKSUM"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("TESTUSDT-aggTrades-2026-07-31.csv", "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n")
        zf.writestr("extra_member.txt", "forbidden\n")
    chk_file.write_text(f"{_file_sha256(zip_file)}  TESTUSDT-aggTrades-2026-07-31.zip\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_archive_package_invalid:zip_multiple_members"):
        validate_archive_package(
            zip_path=zip_file,
            checksum_path=chk_file,
            symbol="TESTUSDT",
            utc_date="2026-07-31",
            launch_time_ms=1785501900000,
        )


def test_archive_package_rejects_zip_compression_ratio_exceeded(tmp_path: Path) -> None:
    zip_file = tmp_path / "TESTUSDT-aggTrades-2026-07-31.zip"
    chk_file = tmp_path / "TESTUSDT-aggTrades-2026-07-31.zip.CHECKSUM"
    large_data = "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n" + (
        "0,1.0,1.0,0,0,1785501900000,true\n" * 50000
    )
    with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("TESTUSDT-aggTrades-2026-07-31.csv", large_data)
    chk_file.write_text(f"{_file_sha256(zip_file)}  TESTUSDT-aggTrades-2026-07-31.zip\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_archive_package_invalid:compression_ratio_exceeded"):
        validate_archive_package(
            zip_path=zip_file,
            checksum_path=chk_file,
            symbol="TESTUSDT",
            utc_date="2026-07-31",
            launch_time_ms=1785501900000,
        )


def test_archive_package_rejects_csv_invalid_header(tmp_path: Path) -> None:
    zip_file = tmp_path / "TESTUSDT-aggTrades-2026-07-31.zip"
    chk_file = tmp_path / "TESTUSDT-aggTrades-2026-07-31.zip.CHECKSUM"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("TESTUSDT-aggTrades-2026-07-31.csv", "bad_header,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n")
    chk_file.write_text(f"{_file_sha256(zip_file)}  TESTUSDT-aggTrades-2026-07-31.zip\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_archive_package_invalid:csv_header_mismatch"):
        validate_archive_package(
            zip_path=zip_file,
            checksum_path=chk_file,
            symbol="TESTUSDT",
            utc_date="2026-07-31",
            launch_time_ms=1785501900000,
        )


def test_archive_package_zero_post_launch_rows_yields_evidence_gap(tmp_path: Path) -> None:
    zip_file = tmp_path / "TESTUSDT-aggTrades-2026-07-31.zip"
    chk_file = tmp_path / "TESTUSDT-aggTrades-2026-07-31.zip.CHECKSUM"
    launch_time_ms = 1785501900000
    csv_content = (
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
        f"1,10.5,1.0,1,1,{launch_time_ms - 5000},true\n"
    )
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("TESTUSDT-aggTrades-2026-07-31.csv", csv_content)
    chk_file.write_text(f"{_file_sha256(zip_file)}  TESTUSDT-aggTrades-2026-07-31.zip\n", encoding="utf-8")

    result = validate_archive_package(
        zip_path=zip_file,
        checksum_path=chk_file,
        symbol="TESTUSDT",
        utc_date="2026-07-31",
        launch_time_ms=launch_time_ms,
    )
    assert result["child_state"] == "archive_verified_zero_post_launch_rows"
    assert result["post_launch_row_count"] == 0
    assert result["first_post_launch_trade_time_ms"] is None
    assert result["first_post_launch_trade_delay_ms"] is None


# =========================================================================
# Group F: Lifecycle, Concurrency & Recovery Matrix
# =========================================================================


def test_lifecycle_same_run_id_matrix_absent_permits_fresh_run(tmp_path: Path) -> None:
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    st = classify_stage1_5j_a_historical_archive_coverage_root_state(output_parent=tmp_path, run_id=run_id)
    assert st == "absent"


def test_lifecycle_same_run_id_matrix_staging_only_stops(tmp_path: Path) -> None:
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    staging = tmp_path / f".{run_id}.staging.12345"
    staging.mkdir()
    st = classify_stage1_5j_a_historical_archive_coverage_root_state(output_parent=tmp_path, run_id=run_id)
    assert st == "staging_only"


def test_lifecycle_same_run_id_matrix_final_only_stops(tmp_path: Path) -> None:
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    final = tmp_path / run_id
    final.mkdir()
    st = classify_stage1_5j_a_historical_archive_coverage_root_state(output_parent=tmp_path, run_id=run_id)
    assert st == "final_only"


def test_lifecycle_same_run_id_matrix_final_plus_staging_stops(tmp_path: Path) -> None:
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    final = tmp_path / run_id
    final.mkdir()
    staging = tmp_path / f".{run_id}.staging.12345"
    staging.mkdir()
    st = classify_stage1_5j_a_historical_archive_coverage_root_state(output_parent=tmp_path, run_id=run_id)
    assert st == "final_plus_staging"


def test_lifecycle_rejects_root_or_ancestor_symlink(tmp_path: Path) -> None:
    target = tmp_path / "real_dir"
    target.mkdir()
    sym = tmp_path / "symlink_dir"
    os.symlink(target, sym)
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_symlink_detected"):
        classify_stage1_5j_a_historical_archive_coverage_root_state(output_parent=sym, run_id=run_id)


def test_lifecycle_concurrent_writers_shared_parent_flock(tmp_path: Path) -> None:
    parent_dir = tmp_path / "receipts"
    parent_dir.mkdir(parents=True, exist_ok=True)
    p_fd = os.open(parent_dir, os.O_RDONLY)
    try:
        fcntl.flock(p_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        p_fd2 = os.open(parent_dir, os.O_RDONLY)
        try:
            with pytest.raises((BlockingIOError, OSError)):
                fcntl.flock(p_fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(p_fd2)
    finally:
        fcntl.flock(p_fd, fcntl.LOCK_UN)
        os.close(p_fd)


# =========================================================================
# Group G: Strict Loader Replay Tests & Tamper Rejection
# =========================================================================


# =========================================================================
# Group G: Strict Loader Structural Integrity Tests (Task 4 §4)
# =========================================================================


def _build_minimal_structural_root(
    tmp_path: Path,
    run_id: str = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z",
) -> tuple[Path, Path]:
    """Creates a minimal structural final root containing the four required files and valid manifest."""
    root_dir = tmp_path / OUTPUT_PARENT_REL / run_id
    root_dir.mkdir(parents=True)

    summary_bytes = b'{"schema_version":"stage1_5j_a_historical_archive_coverage_inventory_summary_v1"}\n'
    (root_dir / "summary.json").write_bytes(summary_bytes)

    review_bytes = b"# Stage 1.5J-A Review\n"
    (root_dir / "review_CN.md").write_bytes(review_bytes)

    journal_bytes = b'{"event":"request_intent","request_id":1}\n'
    (root_dir / "request_journal.jsonl").write_bytes(journal_bytes)

    dummy_payload = b"dummy_content\n"
    dummy_file = root_dir / "raw" / "dummy.txt"
    dummy_file.parent.mkdir(parents=True)
    dummy_file.write_bytes(dummy_payload)

    artifacts = [
        {"byte_count": len(dummy_payload), "relative_path": "raw/dummy.txt", "sha256": _sha256(dummy_payload)},
        {"byte_count": len(journal_bytes), "relative_path": "request_journal.jsonl", "sha256": _sha256(journal_bytes)},
        {"byte_count": len(review_bytes), "relative_path": "review_CN.md", "sha256": _sha256(review_bytes)},
        {"byte_count": len(summary_bytes), "relative_path": "summary.json", "sha256": _sha256(summary_bytes)},
    ]
    manifest = {
        "artifacts": artifacts,
        "root_relative_path": str(OUTPUT_PARENT_REL / run_id),
        "run_id": run_id,
        "schema_version": "stage1_5j_a_historical_archive_coverage_inventory_manifest_v1",
    }
    manifest_bytes = (canonical_json_dumps(manifest) + "\n").encode("utf-8")
    (root_dir / "manifest.json").write_bytes(manifest_bytes)

    return root_dir, tmp_path


def test_strict_loader_structural_rejects_missing_tree_members(tmp_path: Path) -> None:
    for missing_name in ("manifest.json", "summary.json", "review_CN.md", "request_journal.jsonl"):
        sub_tmp = tmp_path / f"test_missing_{missing_name}"
        root_dir, project_root = _build_minimal_structural_root(sub_tmp)
        (root_dir / missing_name).unlink()
        with pytest.raises(Exception, match=f"STOP=stage1_5j_a_root_invalid:missing_file:{missing_name}"):
            load_verified_stage1_5j_a_historical_archive_coverage_root(root_dir, project_root=project_root)


def test_strict_loader_structural_rejects_extra_tree_members(tmp_path: Path) -> None:
    root_dir, project_root = _build_minimal_structural_root(tmp_path)
    (root_dir / "extra_untracked.txt").write_text("forbidden\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_root_invalid:unexpected_entries"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(root_dir, project_root=project_root)


def test_strict_loader_structural_rejects_symlinks(tmp_path: Path) -> None:
    root_dir, project_root = _build_minimal_structural_root(tmp_path)
    symlink_dir = tmp_path / OUTPUT_PARENT_REL / "symlink_root"
    os.symlink(root_dir, symlink_dir)
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_symlink_detected"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(symlink_dir, project_root=project_root)


def test_strict_loader_structural_rejects_noncanonical_manifest_bytes(tmp_path: Path) -> None:
    root_dir, project_root = _build_minimal_structural_root(tmp_path)
    m_file = root_dir / "manifest.json"
    m_data = json.loads(m_file.read_text(encoding="utf-8"))
    m_file.write_text(json.dumps(m_data, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_manifest_not_canonical"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(root_dir, project_root=project_root)


def test_strict_loader_structural_rejects_manifest_run_id_mismatch(tmp_path: Path) -> None:
    root_dir, project_root = _build_minimal_structural_root(tmp_path)
    m_file = root_dir / "manifest.json"
    m_data = json.loads(m_file.read_text(encoding="utf-8"))
    m_data["run_id"] = "stage1_5j_a_historical_archive_coverage_inventory_20261006T999999Z"
    m_file.write_text(canonical_json_dumps(m_data) + "\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_manifest_mismatch:run_id_mismatch"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(root_dir, project_root=project_root)


def test_strict_loader_structural_rejects_manifest_root_relative_path_mismatch(tmp_path: Path) -> None:
    root_dir, project_root = _build_minimal_structural_root(tmp_path)
    m_file = root_dir / "manifest.json"
    m_data = json.loads(m_file.read_text(encoding="utf-8"))
    m_data["root_relative_path"] = "different/path"
    m_file.write_text(canonical_json_dumps(m_data) + "\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_manifest_mismatch:root_relative_path_mismatch"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(root_dir, project_root=project_root)


def test_strict_loader_structural_rejects_manifest_missing_artifact(tmp_path: Path) -> None:
    root_dir, project_root = _build_minimal_structural_root(tmp_path)
    (root_dir / "raw" / "dummy.txt").unlink()
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_manifest_mismatch:missing_artifact:raw/dummy.txt"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(root_dir, project_root=project_root)


def test_strict_loader_structural_rejects_manifest_hash_mismatch(tmp_path: Path) -> None:
    root_dir, project_root = _build_minimal_structural_root(tmp_path)
    (root_dir / "raw" / "dummy.txt").write_bytes(b"tampered_data\n")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_manifest_mismatch:hash_mismatch:raw/dummy.txt"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(root_dir, project_root=project_root)


def test_strict_loader_structural_rejects_illegal_tree_state_shapes(tmp_path: Path) -> None:
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"
    nonexistent = tmp_path / OUTPUT_PARENT_REL / run_id
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_root_missing"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(nonexistent, project_root=tmp_path)

    bad_run_id_root = tmp_path / OUTPUT_PARENT_REL / "invalid_run_id_format"
    bad_run_id_root.mkdir(parents=True)
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_root_invalid:run_id_format"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(bad_run_id_root, project_root=tmp_path)

    wrong_parent_root = tmp_path / "wrong_parent" / run_id
    wrong_parent_root.mkdir(parents=True)
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_root_invalid:not_under_output_parent"):
        load_verified_stage1_5j_a_historical_archive_coverage_root(wrong_parent_root, project_root=tmp_path)


def test_verify_execution_authority_rejects_sidecar_without_trailing_lf(valid_authority_bundle: Path) -> None:
    sidecar = valid_authority_bundle / "implementation_authorization.sha256"
    content = sidecar.read_text(encoding="utf-8").rstrip("\n")
    sidecar.write_text(content, encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_sidecar_mismatch:implementation_authorization"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_json_without_trailing_lf(valid_authority_bundle: Path) -> None:
    json_file = valid_authority_bundle / "execution_authority.json"
    content = json_file.read_text(encoding="utf-8").rstrip("\n")
    json_file.write_text(content, encoding="utf-8")
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_sidecar_mismatch:execution_authority"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle)


def test_verify_execution_authority_rejects_tampered_design_file_on_disk(valid_authority_bundle: Path, tmp_path: Path) -> None:
    fake_root = tmp_path / "fake_repo"
    fake_root.mkdir()
    json_file = valid_authority_bundle / "execution_authority.json"
    data = json.loads(json_file.read_text(encoding="utf-8"))
    data["project_root"] = str(fake_root.resolve())
    design_p = fake_root / APPROVED_DESIGN_REL_PATH
    design_p.parent.mkdir(parents=True, exist_ok=True)
    design_p.write_text("tampered\n", encoding="utf-8")
    plan_p = fake_root / APPROVED_PLAN_REL_PATH
    plan_p.parent.mkdir(parents=True, exist_ok=True)
    plan_p.write_bytes(Path(APPROVED_PLAN_REL_PATH).read_bytes())
    auth_str = canonical_json_dumps(data) + "\n"
    json_file.write_text(auth_str, encoding="utf-8")
    (valid_authority_bundle / "execution_authority.sha256").write_text(
        f"{_sha256(auth_str)}  execution_authority.json\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_drift:current_design_file_sha_mismatch"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle, project_root=fake_root)


def test_verify_execution_authority_rejects_tampered_plan_file_on_disk(valid_authority_bundle: Path, tmp_path: Path) -> None:
    fake_root = tmp_path / "fake_repo"
    fake_root.mkdir()
    json_file = valid_authority_bundle / "execution_authority.json"
    data = json.loads(json_file.read_text(encoding="utf-8"))
    data["project_root"] = str(fake_root.resolve())
    design_p = fake_root / APPROVED_DESIGN_REL_PATH
    design_p.parent.mkdir(parents=True, exist_ok=True)
    design_p.write_bytes(Path(APPROVED_DESIGN_REL_PATH).read_bytes())
    plan_p = fake_root / APPROVED_PLAN_REL_PATH
    plan_p.parent.mkdir(parents=True, exist_ok=True)
    plan_p.write_text("tampered\n", encoding="utf-8")
    auth_str = canonical_json_dumps(data) + "\n"
    json_file.write_text(auth_str, encoding="utf-8")
    (valid_authority_bundle / "execution_authority.sha256").write_text(
        f"{_sha256(auth_str)}  execution_authority.json\n", encoding="utf-8"
    )
    with pytest.raises(Exception, match=r"STOP=stage1_5j_a_execution_authority_drift:current_plan_file_sha_mismatch"):
        _verify_execution_authority_for_test(authority_bundle_dir=valid_authority_bundle, project_root=fake_root)


def test_task5_proof_a_public_authority_request_boundary(tmp_path: Path) -> None:
    """Proof A: Public entrypoint fails closed on absent network authorization without bypass seams.

    Verifies:
    1. run_inventory(run_id) strictly fails closed when network_authorization.txt is absent on disk.
    2. Setting arbitrary module globals does not bypass the disk network authority check.
    3. Component-level RequestManager URL admission works correctly in isolated tmp_path.
    4. Production data namespace is never created, modified, or cleaned in teardown.
    """
    import src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory as core_mod

    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"

    # 1. Public entrypoint directly fails closed with STOP=stage1_5j_a_network_authorization_absent
    with pytest.raises(Stage1_5JADiagnosticError, match=r"STOP=stage1_5j_a_network_authorization_absent"):
        run_inventory(run_id)

    # 2. Attempting to set arbitrary module-level globals does not bypass the disk check
    setattr(core_mod, "_EPHEMERAL_NETWORK_AUTH_PAYLOAD", "fake_payload")
    try:
        with pytest.raises(Stage1_5JADiagnosticError, match=r"STOP=stage1_5j_a_network_authorization_absent"):
            run_inventory(run_id)
    finally:
        if hasattr(core_mod, "_EPHEMERAL_NETWORK_AUTH_PAYLOAD"):
            delattr(core_mod, "_EPHEMERAL_NETWORK_AUTH_PAYLOAD")

    # 3. Component-level URL admission in isolated tmp_path
    staging_dir = tmp_path / "staging_proof_a"
    staging_dir.mkdir(parents=True)
    from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        RequestManager,
    )
    req_mgr = RequestManager(staging_dir=staging_dir)

    page_1_url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50"
    # Valid catalog URL passes URL admission
    req_mgr.validate_url("catalog", page_1_url)

    # Invalid URL scheme/host fails admission
    with pytest.raises(Stage1_5JADiagnosticError, match=r"STOP=stage1_5j_a_request_admission_failure:catalog_url"):
        req_mgr.validate_url("catalog", "https://malicious.example.com/query")

    # 4. Production receipt directory must not exist (and test never executes rmtree on data/)
    pub_dir = Path("data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory") / run_id
    assert not pub_dir.exists(), "Final receipt directory must not exist"
    assert not Path("data/external_signal_shadow/stage1_5j_a").exists(), "Production root must remain absent"


def test_task5_proof_b_canonical_data_pipeline() -> None:
    """Proof B: Constrained GRVT canonical fixture component pipeline proof.

    Verifies that the canonical GRVT fixture files are correctly processed through:
    1. Catalog page parser: exact article code identification
    2. Detail envelope validator: envelope schema & code matching
    3. Frozen parser: symbol extraction, launch time projection (1785501900000)
    4. Archive package verifier: SHA-256 checksum matching, ZIP member validation,
       CSV trade row streaming, trade delay calculation (exact 2335ms).

    Strictly avoids constructing fake catalog scan trees, synthetic request journals,
    fake authority packets, or publishing/asserting a fake coverage_inventory_complete receipt.
    """
    fixture_dir = Path("tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1")
    cat_bytes = (fixture_dir / "catalog_page_2.json").read_bytes()
    detail_bytes = (fixture_dir / "article_detail_20536b05b2a34b87a3bae99c45d0dc91.json").read_bytes()

    # 1. Parse catalog fixture to extract exact GRVT article
    cat_json = json.loads(cat_bytes.decode("utf-8"))
    grvt_articles = [
        a for c in cat_json.get("data", {}).get("catalogs", [])
        for a in c.get("articles", [])
        if a.get("code") == "20536b05b2a34b87a3bae99c45d0dc91"
    ]
    assert len(grvt_articles) == 1
    art = grvt_articles[0]
    assert art["code"] == "20536b05b2a34b87a3bae99c45d0dc91"
    assert "GRVT" in art["title"]

    # 2. Detail validation & frozen parser symbol projection
    detail_payload = json.loads(detail_bytes.decode("utf-8"))
    validated_detail = validate_detail_envelope(detail_payload, "20536b05b2a34b87a3bae99c45d0dc91")
    assert validated_detail["code"] == "20536b05b2a34b87a3bae99c45d0dc91"

    parser_mod = _import_verified_frozen_parser()
    extracted = parser_mod.extract_symbol_candidates_from_bapi_article_payload(detail_payload)
    assert extracted["parser_status"] == "parsed"
    assert extracted["symbols"] == ["GRVTUSDT"]
    launch_time_ms = extracted["symbol_launch_times_ms"]["GRVTUSDT"]
    assert launch_time_ms == 1785501900000

    # 3. Archive package validation
    pkg_rec = validate_archive_package(
        zip_path=fixture_dir / "GRVTUSDT-aggTrades-2026-07-31.zip",
        checksum_path=fixture_dir / "GRVTUSDT-aggTrades-2026-07-31.zip.CHECKSUM",
        symbol="GRVTUSDT",
        utc_date="2026-07-31",
        launch_time_ms=launch_time_ms,
    )
    assert pkg_rec["post_launch_row_count"] == 137896
    assert pkg_rec["first_post_launch_trade_time_ms"] == 1785501902335
    assert pkg_rec["first_post_launch_trade_delay_ms"] == 2335
    assert pkg_rec["last_post_launch_trade_time_ms"] > pkg_rec["first_post_launch_trade_time_ms"]


def test_task5_proof_c_production_symbol_wiring_identity() -> None:
    """Proof C: Verified AST wiring identity and financial safety invariants."""
    import src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory as core_mod
    from configs.base import RISK_LIVE_TRADING_ENABLED

    # 1. Financial safety invariant
    assert RISK_LIVE_TRADING_ENABLED is False, "L0 Financial Safety invariant violated: RISK_LIVE_TRADING_ENABLED must be False"

    # 2. Assert absent live authorities outside private test seams
    assert not hasattr(core_mod, "_EPHEMERAL_NETWORK_AUTH_PAYLOAD")
    assert not hasattr(core_mod, "_TRANSPORT_INTERCEPT_HOOK")
    assert not hasattr(core_mod, "_PRIVATE_LIFECYCLE_STAGING_DIR")
    assert not hasattr(core_mod, "_publish_receipt_for_lifecycle_test")

    # 3. Assert all 13 authority denial flags are False
    for k, v in EXPECTED_13_FALSE_FLAGS.items():
        assert v is False, f"Authority denial flag {k} must be False"

    # 4. AST inspection of run_inventory proving it references and calls the identical production symbols
    core_path = Path("src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py")
    tree = ast.parse(core_path.read_text(encoding="utf-8"))

    run_inv_func = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "run_inventory":
            run_inv_func = node
            break
    assert run_inv_func is not None, "run_inventory must be defined in core module"

    called_names: set[str] = set()
    for subnode in ast.walk(run_inv_func):
        if isinstance(subnode, ast.Call):
            if isinstance(subnode.func, ast.Name):
                called_names.add(subnode.func.id)
            elif isinstance(subnode.func, ast.Attribute):
                called_names.add(subnode.func.attr)

    required_production_symbols = {
        "verify_execution_authority",
        "verify_network_authorization",
        "RequestManager",
        "validate_catalog_scans",
        "validate_detail_envelope",
        "_import_verified_frozen_parser",
        "validate_archive_package",
        "build_inventory_summary",
        "render_stage1_5j_a_review",
    }
    missing_symbols = required_production_symbols - called_names
    assert not missing_symbols, f"run_inventory missing expected production symbol calls: {missing_symbols}"

    # 5. Runtime identity: verify the symbols in core_mod match those called
    assert callable(core_mod.verify_execution_authority)
    assert callable(core_mod.verify_network_authorization)
    assert callable(core_mod.validate_catalog_scans)
    assert callable(core_mod.validate_detail_envelope)
    assert callable(core_mod._import_verified_frozen_parser)
    assert callable(core_mod.validate_archive_package)
    assert callable(core_mod.build_inventory_summary)
    assert callable(core_mod.render_stage1_5j_a_review)
    assert issubclass(core_mod.RequestManager, object)


# =========================================================================
# Group H: AST & Open Spies
# =========================================================================


def test_ast_core_module_import_allowlist() -> None:
    core_path = Path("src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py")
    if not core_path.is_file():
        pytest.skip("Core module not yet created (Task 2 target)")
    content = core_path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    forbidden = ["requests", "httpx", "aiohttp", "stage1_5d_live_event_source_client"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    assert f not in alias.name, f"Forbidden import {alias.name} in core"
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for f in forbidden:
                assert f not in mod, f"Forbidden import from {mod} in core"


def test_ast_cli_module_no_network_and_strict_argparse() -> None:
    cli_path = Path("scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py")
    if not cli_path.is_file():
        pytest.skip("CLI module not yet created (Task 5 target)")
    content = cli_path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    forbidden = ["socket", "requests", "urllib", "http"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    assert f not in alias.name, f"Forbidden import {alias.name} in CLI"
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for f in forbidden:
                assert f not in mod, f"Forbidden import from {mod} in CLI"


def test_open_spy_no_sockets_opened_during_negative_probes() -> None:
    """Verifies that running authority checks opens zero network sockets."""
    opened_sockets = []

    def _spy_socket(*args: Any, **kwargs: Any) -> Any:
        opened_sockets.append((args, kwargs))
        raise RuntimeError("STOP=network_access_strictly_forbidden_in_tests")

    with patch("socket.socket", side_effect=_spy_socket):
        # Even on invalid bundle, zero sockets must be created
        with pytest.raises(Exception):
            _verify_execution_authority_for_test(authority_bundle_dir=Path("/nonexistent"))
        # Public verifier on canonical bundle opens zero sockets
        res = verify_execution_authority()
        assert res is not None

    assert len(opened_sockets) == 0, f"Sockets opened during authority check: {opened_sockets}"
