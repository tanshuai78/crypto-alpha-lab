"""Tests for CLI authorization gates, safe output directory isolation, tamper rejection, and stream limits.

Conforms to L1 Engineering Process Rules and Rule 15 fixture integrity.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.external_signal_shadow.run_launch_open_interest_basis_exploratory import (
    main,
)
from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
    APPROVED_DESIGN_DELTA_PATH,
    APPROVED_DESIGN_DELTA_SHA256,
    APPROVED_DESIGN_PATH,
    APPROVED_DESIGN_SHA256,
    APPROVED_PLAN_PATH,
    APPROVED_PLAN_SHA256,
    J_A_ROOT_RELATIVE_PATH,
    J_B_ROOT_RELATIVE_PATH,
    LEDGER_RELATIVE_PATH,
    LEDGER_SHA256,
    OBSERVATION_OFFSET_MS,
    LaunchOiResearchError,
    verify_single_run_authorization,
    verify_v2_ledger_and_select_universe,
)


def _make_valid_auth_dict(output_dir: Path) -> dict[str, Any]:
    return {
        "design_relative_path": APPROVED_DESIGN_PATH,
        "design_sha256": APPROVED_DESIGN_SHA256,
        "design_delta_relative_path": APPROVED_DESIGN_DELTA_PATH,
        "design_delta_sha256": APPROVED_DESIGN_DELTA_SHA256,
        "plan_relative_path": APPROVED_PLAN_PATH,
        "plan_sha256": APPROVED_PLAN_SHA256,
        "ja_root_relative_path": J_A_ROOT_RELATIVE_PATH,
        "jb_root_relative_path": J_B_ROOT_RELATIVE_PATH,
        "ledger_relative_path": LEDGER_RELATIVE_PATH,
        "ledger_sha256": LEDGER_SHA256,
        "output_dir": str(output_dir),
        "operation": "offline_research_once",
        "network_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_allowed": False,
        "signal_allowed": False,
    }


def test_old_plan_sha_rejected(tmp_path: Path):
    """Task 3 (Plan L79): Old plan SHA (3209f0a4dde7cb8aa82b27149fbc1fac5aaf684df2ea96cd9bdc8d2d0033eb65) is rejected."""
    out_dir = tmp_path / "out"
    auth_data = _make_valid_auth_dict(out_dir)
    auth_data["plan_sha256"] = "3209f0a4dde7cb8aa82b27149fbc1fac5aaf684df2ea96cd9bdc8d2d0033eb65"
    auth_file = tmp_path / "old_plan_auth.json"
    auth_file.write_text(json.dumps(auth_data), encoding="utf-8")

    with pytest.raises(LaunchOiResearchError, match="auth_plan_sha_mismatch"):
        verify_single_run_authorization(auth_file, expected_output_dir=out_dir)


def test_design_delta_sha_mismatch_rejected(tmp_path: Path):
    """Task 3 (Plan L79): Missing or mismatched design delta SHA is rejected."""
    out_dir = tmp_path / "out"
    auth_data = _make_valid_auth_dict(out_dir)
    auth_data["design_delta_sha256"] = "bad" * 16
    auth_file = tmp_path / "bad_delta_auth.json"
    auth_file.write_text(json.dumps(auth_data), encoding="utf-8")

    with pytest.raises(LaunchOiResearchError, match="auth_design_delta_sha_mismatch"):
        verify_single_run_authorization(auth_file, expected_output_dir=out_dir)


def test_cli_stops_without_authorization(tmp_path: Path):
    """Plan line 90: CLI stops before calling loader if authorization is absent or invalid."""
    out_dir = tmp_path / "new_output"
    # Call main with non-existent auth file
    rc = main(
        ["--auth-file", str(tmp_path / "non_existent_auth.json"), "--output-dir", str(out_dir)],
        project_root=tmp_path,
    )
    assert rc != 0
    assert not out_dir.exists()


def test_output_dir_collision_rejected(tmp_path: Path):
    """Plan line 90: Output directory collision must be rejected, no overwrite."""
    out_dir = tmp_path / "existing_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    canary = out_dir / "canary.txt"
    canary.write_text("protected", encoding="utf-8")

    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(out_dir)), encoding="utf-8")

    rc = main(["--auth-file", str(auth_file), "--output-dir", str(out_dir)], project_root=tmp_path)
    assert rc != 0
    # Canary must be untouched
    assert canary.read_text(encoding="utf-8") == "protected"


def test_output_dir_symlink_ancestor_to_protected_root_rejected(tmp_path: Path):
    """Plan line 90: Output ancestor symlink pointing to temporary protected root is rejected, and protected root has no writes."""
    protected_root = tmp_path / "protected_ja_root"
    protected_root.mkdir(parents=True, exist_ok=True)
    canary = protected_root / "canary.json"
    canary.write_text('{"untouched": true}', encoding="utf-8")

    symlink_dir = tmp_path / "symlink_parent"
    symlink_dir.symlink_to(protected_root)

    # An output directory located inside the symlinked ancestor
    bad_output_dir = symlink_dir / "nested_out"

    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(bad_output_dir)), encoding="utf-8")

    rc = main(
        ["--auth-file", str(auth_file), "--output-dir", str(bad_output_dir)],
        project_root=tmp_path,
        extra_protected_paths=[protected_root],
    )
    assert rc != 0
    assert not (protected_root / "nested_out").exists()
    assert canary.read_text(encoding="utf-8") == '{"untouched": true}'


def test_ledger_frozen_sha_mismatch_rejected(tmp_path: Path):
    """Plan line 90: Keeping (parent, symbol) same while modifying listing_regime causes frozen SHA mismatch rejection."""
    real_ledger = Path("data/exports/stage1_5j_token_launch_classification_ledger_v2.csv")
    if not real_ledger.exists():
        pytest.skip("Local real ledger not found for mutation test.")

    content = real_ledger.read_text(encoding="utf-8")
    lines = content.splitlines()
    lines[0]
    first_row = lines[1].split(",")
    # Mutate listing_regime (index 3)
    original_regime = first_row[3]
    first_row[3] = "mutated_regime" if original_regime != "mutated_regime" else "other_regime"
    lines[1] = ",".join(first_row)
    mutated_content = "\n".join(lines) + "\n"

    fake_ledger_path = tmp_path / "mutated_ledger.csv"
    fake_ledger_path.write_text(mutated_content, encoding="utf-8")

    # verify_v2_ledger_and_select_universe must raise LaunchOiResearchError on SHA mismatch
    with pytest.raises(LaunchOiResearchError) as exc_info:
        verify_v2_ledger_and_select_universe(fake_ledger_path)
    assert "ledger_sha256_mismatch" in str(exc_info.value)


def test_overlong_physical_line_rejected(tmp_path: Path):
    """P1-04 remediation: CSV physical line > 65,536 bytes without newline is rejected before buffering entire line."""
    import io

    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        stream_aggtrades_csv_lines,
    )

    class TrackingBytesIO(io.BytesIO):
        def __init__(self, initial_bytes: bytes) -> None:
            super().__init__(initial_bytes)
            self.bytes_read = 0

        def read(self, size: int = -1) -> bytes:
            data = super().read(size)
            self.bytes_read += len(data)
            return data

    overlong_line = ("a" * 70_000).encode("utf-8")
    stream = TrackingBytesIO(overlong_line)

    with pytest.raises(LaunchOiResearchError) as exc_info:
        list(stream_aggtrades_csv_lines(stream, chunk_size=65_536, max_line_bytes=65_536))
    assert "physical_line_length_exceeded" in str(exc_info.value)
    # Verify bounded line budget: Rejected at 65,537 bytes before full 70,000 bytes entered memory
    assert stream.bytes_read <= 65_537
    assert stream.bytes_read < 70_000


def test_physical_line_exact_boundary():
    """P1-04 remediation: Physical line including newline of exactly 65,536 bytes passes; 65,537 bytes fails."""
    import io

    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
        stream_aggtrades_csv_lines,
    )

    # 1. Exactly 65,536 bytes (65,535 chars + '\n')
    valid_exact_line = b"x" * (EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES - 1) + b"\n"
    stream_valid = io.BytesIO(valid_exact_line)
    lines = list(stream_aggtrades_csv_lines(stream_valid, chunk_size=65_536, max_line_bytes=65_536))
    assert len(lines) == 1
    assert len(lines[0]) == 65_535

    # 2. Exactly 65,537 bytes (65,536 chars + '\n') -> 1 byte over limit
    over_limit_line = b"x" * EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES + b"\n"
    stream_over = io.BytesIO(over_limit_line)
    with pytest.raises(LaunchOiResearchError) as exc_info:
        list(stream_aggtrades_csv_lines(stream_over, chunk_size=65_536, max_line_bytes=65_536))
    assert "physical_line_length_exceeded" in str(exc_info.value)


def test_cli_stops_when_ledger_missing(tmp_path: Path):
    """P1-01 remediation: CLI must exit non-zero if classification ledger is missing."""
    out_dir = tmp_path / "output_ledger_missing"
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(out_dir)), encoding="utf-8")

    # project_root has no ledger
    rc = main(
        ["--auth-file", str(auth_file), "--output-dir", str(out_dir)],
        project_root=tmp_path,
    )
    assert rc != 0
    assert not out_dir.exists()


def test_cli_end_to_end_synthetic_run(tmp_path: Path):
    """P1-01 remediation: CLI executes reduction pipeline, writes child_rows.csv & review_CN.md, and exits 0."""
    proj = Path.cwd().resolve()
    real_ledger = proj / LEDGER_RELATIVE_PATH
    if not real_ledger.is_file():
        pytest.skip("Real ledger not present for end-to-end CLI synthetic test.")

    out_dir = tmp_path / "research_run_01"
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(_make_valid_auth_dict(out_dir)), encoding="utf-8")

    # Select first child from real ledger to test genuine wiring against ledger universe
    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        AggTradeRecord,
        OiMetricRecord,
        verify_v2_ledger_and_select_universe,
    )

    selected = verify_v2_ledger_and_select_universe(real_ledger)
    assert len(selected) > 0
    first_child = selected[0]
    target_pid = first_child["parent_article_id"]
    target_sym = first_child["symbol"]

    # Mock JA and JB loaders returning minimal valid structures for fast test execution
    def mock_ja_loader(root: Path):
        return {"artifacts": [], "run_id": "mock_ja"}

    def mock_jb_loader(root: Path):
        return {
            "child_rows": [
                {
                    "source_article_id": target_pid,
                    "symbol": target_sym,
                    "anchor_time_ms": 1_000_000,
                }
            ]
        }

    mock_metrics = {
        target_sym: [
            OiMetricRecord(
                create_time_ms=1_000_000,
                symbol=target_sym,
                sum_open_interest=100.0,
                information_time_ms=1_000_000,
            ),
            OiMetricRecord(
                create_time_ms=1_300_000,
                symbol=target_sym,
                sum_open_interest=150.0,
                information_time_ms=1_300_000,
            ),
            OiMetricRecord(
                create_time_ms=1_600_000,
                symbol=target_sym,
                sum_open_interest=200.0,
                information_time_ms=1_600_000,
            ),
        ]
    }
    mock_trades = {
        target_sym: [
            AggTradeRecord(
                transact_time_ms=2_500_000,
                trade_id=1,
                price=10.0,
                quantity=1.0,
                is_buyer_maker=False,
            ),
            AggTradeRecord(
                transact_time_ms=3_400_000,
                trade_id=2,
                price=11.0,
                quantity=1.0,
                is_buyer_maker=False,
            ),
        ]
    }

    rc = main(
        ["--auth-file", str(auth_file), "--output-dir", str(out_dir)],
        project_root=proj,
        ja_loader=mock_ja_loader,
        jb_loader=mock_jb_loader,
        metrics_by_symbol=mock_metrics,
        aggtrades_by_symbol=mock_trades,
    )
    assert rc == 0
    child_csv = out_dir / "child_rows.csv"
    review_md = out_dir / "review_CN.md"
    assert child_csv.is_file()
    assert review_md.is_file()

    # Check child_rows.csv contents
    csv_text = child_csv.read_text(encoding="utf-8")
    assert "parent_article_id,symbol,listing_regime" in csv_text

    # Check review_CN.md contents
    md_text = review_md.read_text(encoding="utf-8")
    assert APPROVED_DESIGN_SHA256 in md_text
    assert APPROVED_DESIGN_DELTA_SHA256 in md_text
    assert APPROVED_PLAN_SHA256 in md_text
    assert LEDGER_SHA256 in md_text
    assert "Child Universe 候选总数" in md_text
    assert "## 7. 实际消费输入文件清单与身份（Input Provenance Manifest）" in md_text
    assert "无实际磁盘输入文件消费记录" in md_text

    # Check output directory contains strictly the two approved files
    assert not (out_dir / "consumed_inputs.json").exists()
    assert sorted([p.name for p in out_dir.iterdir()]) == ["child_rows.csv", "review_CN.md"]


@pytest.fixture
def single_run_auth_file() -> Path:
    """Return path to explicit user single-run authorization file if provided, else skip."""
    import os

    env_path = os.environ.get("LAUNCH_OI_SINGLE_RUN_AUTH_FILE")
    if not env_path or not env_path.strip():
        pytest.skip("historical_validation_not_authorized: LAUNCH_OI_SINGLE_RUN_AUTH_FILE not set")
    p = Path(env_path.strip())
    if not p.is_file():
        pytest.skip(f"historical_validation_not_authorized: auth file not found at {p}")
    return p


def test_canonical_upstream_positive(single_run_auth_file: Path) -> None:
    """P1-05 remediation: Verify positive admission, ledger selection, J-A package verification, and consumer pipeline execution from canonical closure-audited roots when authorized."""
    import csv

    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        build_admitted_ja_context,
        calculate_path_response,
        compute_required_utc_dates,
        load_child_aggtrades_from_ja_root,
        verify_single_run_authorization,
        verify_v2_ledger_and_select_universe,
    )
    from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        load_verified_stage1_5j_a_historical_archive_coverage_root,
    )
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
    )

    proj = Path.cwd().resolve()
    # Validate the unmodified user-provided single-run authorization file directly
    auth_data = verify_single_run_authorization(
        auth_file=single_run_auth_file,
        expected_output_dir=None,
        project_root=proj,
    )
    authorized_out_dir = Path(str(auth_data["output_dir"]))

    ja_root = proj / J_A_ROOT_RELATIVE_PATH
    jb_root = proj / J_B_ROOT_RELATIVE_PATH
    ledger_path = proj / LEDGER_RELATIVE_PATH

    ja_summary = load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)
    jb_summary = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(jb_root)
    selected = verify_v2_ledger_and_select_universe(ledger_path)
    ja_ctx = build_admitted_ja_context(ja_root, ja_summary)

    jb_by_key = {
        (str(r["source_article_id"]), str(r["symbol"])): r for r in jb_summary["child_rows"]
    }

    # Verify canonical J-A package admission + streaming + path calculation on a real admitted child
    verified_agg_children = 0
    for s_row in selected:
        pid = str(s_row["parent_article_id"])
        sym = str(s_row["symbol"])
        jb_entry = jb_by_key.get((pid, sym))
        if jb_entry is None or jb_entry.get("anchor_time_ms") is None:
            continue
        t0_ms = int(jb_entry["anchor_time_ms"])
        req_dates = compute_required_utc_dates(t0_ms)
        if all(
            (pid, sym, d) in ja_ctx.package_by_key
            and ja_ctx.package_by_key[(pid, sym, d)].get("child_state")
            == "archive_verified_with_post_launch_rows"
            for d in req_dates
        ):
            st, trades = load_child_aggtrades_from_ja_root(
                ja_root=ja_root,
                ja_summary=ja_summary,
                parent_article_id=pid,
                symbol=sym,
                t0_ms=t0_ms,
                ja_ctx=ja_ctx,
            )
            assert st == "ok"
            assert len(trades) > 0
            path_res = calculate_path_response(trades=trades, d_ms=t0_ms + OBSERVATION_OFFSET_MS)
            if path_res.status == "ok":
                assert path_res.entry_price is not None and path_res.entry_price > 0
                assert path_res.endpoint_price is not None and path_res.endpoint_price > 0
                verified_agg_children += 1
                break

    assert verified_agg_children >= 1

    # Check whether verified OI information-time upper-bound evidence is available before running full CLI
    oi_prov_path = proj / "data/external_signal_shadow/oi_metrics/oi_provenance_manifest.json"
    if not oi_prov_path.is_file():
        pytest.skip(
            "evidence_insufficient: oi_provenance_manifest.json with verified information_time upper bound not present"
        )

    rc = main(
        ["--auth-file", str(single_run_auth_file), "--output-dir", str(authorized_out_dir)],
        project_root=proj,
    )
    assert rc == 0

    child_csv = authorized_out_dir / "child_rows.csv"
    review_md = authorized_out_dir / "review_CN.md"
    assert child_csv.is_file()
    assert review_md.is_file()

    with open(child_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) > 0
    complete_rows = [r for r in rows if (r.get("is_complete") or "").lower() == "true"]
    assert len(complete_rows) >= 1
    c0 = complete_rows[0]
    assert c0["symbol"]
    assert c0["parent_article_id"]
    assert float(c0["terminal_return"]) is not None
    assert float(c0["oi_change"]) is not None
    assert float(c0["entry_price"]) > 0
    assert float(c0["endpoint_price"]) > 0


def test_canonical_single_mutation_rejected(single_run_auth_file: Path, tmp_path: Path) -> None:
    """P1-05 remediation: Verify single mutation on temporary copy of admitted upstream J-A package and J-B summary is rejected fail-closed."""
    import shutil

    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        build_admitted_ja_context,
        compute_required_utc_dates,
        execute_exploratory_pipeline,
        load_child_aggtrades_from_ja_root,
        verify_single_run_authorization,
        verify_v2_ledger_and_select_universe,
    )
    from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        load_verified_stage1_5j_a_historical_archive_coverage_root,
    )

    proj = Path.cwd().resolve()
    # Verify authorization without rewriting single_run_auth_file
    verify_single_run_authorization(
        auth_file=single_run_auth_file,
        expected_output_dir=None,
        project_root=proj,
    )

    ja_root = proj / J_A_ROOT_RELATIVE_PATH
    real_jb_root = proj / J_B_ROOT_RELATIVE_PATH
    ledger_path = proj / LEDGER_RELATIVE_PATH
    selected = verify_v2_ledger_and_select_universe(ledger_path)

    # 1. Single-byte mutation in a temporary copy of an admitted J-A package's .CHECKSUM file
    ja_summary = load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)
    build_admitted_ja_context(ja_root, ja_summary)
    verified_pkg = next(
        p
        for p in ja_summary["archive_package_records"]
        if p.get("child_state") == "archive_verified_with_post_launch_rows"
    )
    pid = str(verified_pkg["parent_article_id"])
    sym = str(verified_pkg["symbol"])
    req_d = str(verified_pkg["utc_date"])
    zip_rel = str(verified_pkg["zip_relative_path"])
    chk_rel = str(verified_pkg["checksum_relative_path"])

    mutated_ja_root = tmp_path / "mutated_ja_root"
    (mutated_ja_root / Path(zip_rel).parent).mkdir(parents=True, exist_ok=True)
    shutil.copy2(ja_root / zip_rel, mutated_ja_root / zip_rel)
    shutil.copy2(ja_root / chk_rel, mutated_ja_root / chk_rel)
    shutil.copy2(ja_root / "manifest.json", mutated_ja_root / "manifest.json")

    # Flip 1 character in the copied .CHECKSUM file
    chk_copy = mutated_ja_root / chk_rel
    chk_bytes = bytearray(chk_copy.read_bytes())
    chk_bytes[0] = ord("f") if chk_bytes[0] != ord("f") else ord("0")
    chk_copy.write_bytes(bytes(chk_bytes))

    # Choose t0_ms at the start of req_d with a 60s span so only req_d is required
    from datetime import datetime, timezone

    t0_ms = int(
        datetime.strptime(req_d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000
    )
    assert compute_required_utc_dates(t0_ms, span_ms=60_000) == [req_d]

    with pytest.raises(LaunchOiResearchError, match="corrupted_archive_data:checksum_file_sha256_mismatch"):
        load_child_aggtrades_from_ja_root(
            ja_root=mutated_ja_root,
            ja_summary=ja_summary,
            parent_article_id=pid,
            symbol=sym,
            t0_ms=t0_ms,
            horizon_span_ms=60_000,
        )

    # 2. Single-point mutation in a temporary copy of J-B summary.json
    mutated_jb_root = tmp_path / "mutated_jb_root"
    shutil.copytree(real_jb_root, mutated_jb_root)
    summary_file = mutated_jb_root / "summary.json"
    summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
    summary_data["schema_version"] = "corrupted_version_mutation"
    summary_file.write_text(json.dumps(summary_data), encoding="utf-8")

    out_dir = tmp_path / "mutated_out"
    with pytest.raises(Exception):
        execute_exploratory_pipeline(
            selected_children=selected[:1],
            ja_root=ja_root,
            jb_root=mutated_jb_root,
            output_dir=out_dir,
            project_root=proj,
        )
    assert not out_dir.exists()


def test_auth_source_path_validation(tmp_path: Path):
    """P1-03 remediation: verify_single_run_authorization rejects relative paths that escape project root or contain symlinks."""
    out_dir = tmp_path / "out"
    auth_data = _make_valid_auth_dict(out_dir)

    # 1. Escaping path via ..
    auth_data["oi_source_relative_path"] = "../../escape_root"
    auth_file = tmp_path / "auth_escape.json"
    auth_file.write_text(json.dumps(auth_data), encoding="utf-8")

    with pytest.raises(LaunchOiResearchError, match="auth_source_path_escapes_project_root"):
        verify_single_run_authorization(auth_file, expected_output_dir=out_dir, project_root=tmp_path)

    # 2. Symlink in source directory path
    real_src = tmp_path / "real_oi_data"
    real_src.mkdir(parents=True, exist_ok=True)
    symlink_src = tmp_path / "symlink_oi_data"
    symlink_src.symlink_to(real_src)

    auth_data["oi_source_relative_path"] = "symlink_oi_data"
    auth_file_symlink = tmp_path / "auth_symlink.json"
    auth_file_symlink.write_text(json.dumps(auth_data), encoding="utf-8")

    with pytest.raises(LaunchOiResearchError, match="auth_source_path_symlink_forbidden"):
        verify_single_run_authorization(auth_file_symlink, expected_output_dir=out_dir, project_root=tmp_path)

    # 3. Valid non-escaping, non-symlink path passes when bound to manifest sha or authorized_input_files
    auth_data["oi_source_relative_path"] = "real_oi_data"
    manifest_file = real_src / "oi_provenance_manifest.json"
    manifest_file.write_text('{"symbols": {}}', encoding="utf-8")
    import hashlib
    manifest_sha = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
    auth_data["oi_source_manifest_sha256"] = manifest_sha

    auth_file_ok = tmp_path / "auth_ok.json"
    auth_file_ok.write_text(json.dumps(auth_data), encoding="utf-8")

    verified = verify_single_run_authorization(auth_file_ok, expected_output_dir=out_dir, project_root=tmp_path)
    assert verified["oi_source_relative_path"] == "real_oi_data"


def test_auth_missing_oi_identity_binding_rejected(tmp_path: Path):
    """P1-03 remediation: Specifying oi_source_relative_path without oi_source_manifest_sha256 or authorized_input_files is rejected."""
    out_dir = tmp_path / "out"
    auth_data = _make_valid_auth_dict(out_dir)
    auth_data["oi_source_relative_path"] = "some_oi_dir"
    auth_file = tmp_path / "auth_no_identity.json"
    auth_file.write_text(json.dumps(auth_data), encoding="utf-8")

    with pytest.raises(LaunchOiResearchError, match="auth_missing_oi_source_identity_binding"):
        verify_single_run_authorization(auth_file, expected_output_dir=out_dir, project_root=tmp_path)


def test_auth_oi_manifest_sha_mismatch_rejected(tmp_path: Path):
    """P1-03 remediation: Mismatched oi_source_manifest_sha256 is rejected fail-closed."""
    out_dir = tmp_path / "out"
    auth_data = _make_valid_auth_dict(out_dir)
    oi_dir = tmp_path / "oi_dir"
    oi_dir.mkdir(parents=True, exist_ok=True)
    manifest = oi_dir / "oi_provenance_manifest.json"
    manifest.write_text('{"symbols": {}}', encoding="utf-8")

    auth_data["oi_source_relative_path"] = "oi_dir"
    auth_data["oi_source_manifest_sha256"] = "bad" * 16
    auth_file = tmp_path / "auth_bad_manifest.json"
    auth_file.write_text(json.dumps(auth_data), encoding="utf-8")

    with pytest.raises(LaunchOiResearchError, match="auth_oi_manifest_sha_mismatch"):
        verify_single_run_authorization(auth_file, expected_output_dir=out_dir, project_root=tmp_path)


def test_auth_input_file_unauthorized_or_tampered_rejected(tmp_path: Path):
    """P1-03 remediation: Consuming an input file not listed in authorized_input_files or with tampered SHA is rejected."""
    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        execute_exploratory_pipeline,
    )

    oi_dir = tmp_path / "oi_data"
    oi_dir.mkdir(parents=True, exist_ok=True)
    csv_file = oi_dir / "TEST-metrics-2026-05-01.csv"
    csv_file.write_text("create_time,open_interest\n1000000,100.0\n", encoding="utf-8")
    import hashlib
    real_sha = hashlib.sha256(csv_file.read_bytes()).hexdigest()

    manifest = oi_dir / "oi_provenance_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "symbols": {
                    "TEST": {
                        "source_name": "binance",
                        "source_version": "v1",
                        "applicable_scope": "all",
                        "unit": "USDT",
                        "files": {csv_file.name: {"sha256": real_sha}},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    selected = [{"parent_article_id": "art_1", "symbol": "TEST", "listing_regime": "standard", "utc_date": "2026-05-01"}]
    jb_summary = {
        "schema_version": "stage1_5j_b_historical_aggtrades_launch_response.v1",
        "child_rows": [{"source_article_id": "art_1", "symbol": "TEST", "anchor_time_ms": 1_000_000}],
    }

    # 1. authorized_input_files does not list csv_file
    with pytest.raises(LaunchOiResearchError, match="unauthorized_source_file_rejected"):
        execute_exploratory_pipeline(
            selected_children=selected,
            ja_root=tmp_path,
            jb_root=tmp_path,
            output_dir=out_dir / "1",
            project_root=tmp_path,
            ja_loader=lambda r: {"archive_package_records": []},
            jb_loader=lambda r: jb_summary,
            sources_dirs=[oi_dir],
            authorized_input_files={"other_file.csv": "abc"},
        )

    # 2. authorized_input_files lists csv_file but with wrong SHA
    with pytest.raises(LaunchOiResearchError, match="auth_source_file_sha_mismatch"):
        execute_exploratory_pipeline(
            selected_children=selected,
            ja_root=tmp_path,
            jb_root=tmp_path,
            output_dir=out_dir / "2",
            project_root=tmp_path,
            ja_loader=lambda r: {"archive_package_records": []},
            jb_loader=lambda r: jb_summary,
            sources_dirs=[oi_dir],
            authorized_input_files={csv_file.name: "0" * 64},
        )


def test_cli_records_consumed_input_files(tmp_path: Path):
    """P1-03 remediation: CLI execution records consumed files and SHAs in review_CN.md and only outputs approved files."""
    proj = Path.cwd().resolve()
    real_ledger = proj / LEDGER_RELATIVE_PATH
    if not real_ledger.is_file():
        pytest.skip("Real ledger not present for end-to-end CLI synthetic test.")

    proj_dir = tmp_path.parent / f"proj_{tmp_path.name}"
    proj_dir.mkdir(parents=True, exist_ok=True)
    out_dir = tmp_path / "research_run_consumed"
    oi_dir = proj_dir / "oi_sources"
    oi_dir.mkdir(parents=True, exist_ok=True)

    # Set up ledger in proj_dir with authentic bytes
    target_ledger = proj_dir / LEDGER_RELATIVE_PATH
    target_ledger.parent.mkdir(parents=True, exist_ok=True)
    target_ledger.write_bytes(real_ledger.read_bytes())

    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        AggTradeRecord,
        verify_v2_ledger_and_select_universe,
    )

    selected = verify_v2_ledger_and_select_universe(target_ledger)
    first_child = selected[0]
    target_pid = first_child["parent_article_id"]
    target_sym = first_child["symbol"]

    from datetime import datetime, timezone

    dt_0 = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    t0_ms = int(dt_0.timestamp() * 1000)
    d_ms = t0_ms + 1_500_000

    csv_file = oi_dir / f"{target_sym}-metrics-2026-05-01.csv"
    csv_file.write_text(
        "create_time,sum_open_interest\n"
        "2026-05-01 00:10:00,100.0\n"
        "2026-05-01 00:15:00,150.0\n",
        encoding="utf-8",
    )
    import hashlib
    csv_sha = hashlib.sha256(csv_file.read_bytes()).hexdigest()

    manifest_file = oi_dir / "oi_provenance_manifest.json"
    manifest_data = {
        "symbols": {
            target_sym: {
                "source_name": "binance",
                "source_version": "v1",
                "applicable_scope": "all",
                "unit": "USDT",
                "files": {
                    csv_file.name: {"sha256": csv_sha}
                },
            }
        }
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
    manifest_sha = hashlib.sha256(manifest_file.read_bytes()).hexdigest()

    # Build auth dict specifying oi_source_relative_path inside project_root
    auth_data = _make_valid_auth_dict(out_dir)
    auth_data["oi_source_relative_path"] = "oi_sources"
    auth_data["oi_source_manifest_sha256"] = manifest_sha
    auth_file = tmp_path / "auth_consumed.json"
    auth_file.write_text(json.dumps(auth_data), encoding="utf-8")

    mock_trades = {
        target_sym: [
            AggTradeRecord(transact_time_ms=d_ms, trade_id=1, price=10.0, quantity=1.0, is_buyer_maker=False),
            AggTradeRecord(transact_time_ms=d_ms + 900_000, trade_id=2, price=11.0, quantity=1.0, is_buyer_maker=False),
        ]
    }

    rc = main(
        ["--auth-file", str(auth_file), "--output-dir", str(out_dir)],
        project_root=proj_dir,
        ja_loader=lambda r: {"artifacts": [], "run_id": "mock_ja"},
        jb_loader=lambda r: {
            "child_rows": [{"source_article_id": target_pid, "symbol": target_sym, "anchor_time_ms": t0_ms}]
        },
        metrics_by_symbol=None,
        aggtrades_by_symbol=mock_trades,
    )
    assert rc == 0
    assert not (out_dir / "consumed_inputs.json").exists()
    assert sorted([p.name for p in out_dir.iterdir()]) == ["child_rows.csv", "review_CN.md"]

    review_md = out_dir / "review_CN.md"
    assert review_md.is_file()
    md_text = review_md.read_text(encoding="utf-8")
    assert "## 7. 实际消费输入文件清单与身份（Input Provenance Manifest）" in md_text
    assert csv_sha in md_text
    assert manifest_sha in md_text
    assert "- **Parent Universe UTC 日期分布**:" in md_text
    assert "- **完整 Parent 样本 UTC 日期分布**:" in md_text
    assert '"2026-05-01"' in md_text

    import csv
    with open(out_dir / "child_rows.csv", "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    target_row = next(r for r in rows if r["symbol"] == target_sym)
    assert target_row["utc_date"] == "2026-05-01"



