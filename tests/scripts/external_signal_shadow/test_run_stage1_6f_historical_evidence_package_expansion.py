"""Tests for Stage 1.6F historical evidence package expansion collector and validator.

Invariant: INV-EP01, INV-EP02, INV-EP03, INV-EP04, INV-EP05, INV-EP10.
"""

import copy
import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Dict, Tuple

import pytest

import scripts.external_signal_shadow.run_stage1_6f_historical_evidence_package_expansion as collector
from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import (
    CANONICAL_CANDIDATE_RUN_ID,
    FROZEN_NETWORK_AUTH_RELATIVE_PATH,
    FROZEN_NETWORK_AUTH_SHA256,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    ALL_PERMISSION_FLAGS_FALSE,
    reconstruct_denominator,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    verify_c_input,
)

FROZEN_DESIGN_PATH = "docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md"
FROZEN_DESIGN_SHA = "1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4"

FROZEN_PLAN_PATH = "docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md"
FROZEN_PLAN_SHA = "fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d"

FROZEN_MATRIX_PATH = "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json"
FROZEN_MATRIX_SHA = "b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8"

REEF_MANIFEST_PATH = "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json"
REEF_MANIFEST_SHA = "9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f"

C_COMPLETED_ROOT = "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z"
B_SOURCE_EXPORT = "data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090"

EXPECTED_COHORT = [
    "1000XUSDT", "AIAUSDT", "AIUSDT", "ALPHAUSDT", "AUDIOUSDT", "BAKEUSDT",
    "BDXNUSDT", "BOBUSDT", "BONDUSDT", "BSWUSDT", "CVXUSDT", "DAMUSDT",
    "DEFIUSDT", "EPTUSDT", "HIFIUSDT", "KDAUSDT", "LEVERUSDT", "LOOMUSDT",
    "MAVIAUSDT", "MBLUSDT", "MDTUSDT", "MILKUSDT", "NEIROETHUSDT", "OBOLUSDT",
    "OMGUSDT", "ORBSUSDT", "PERPUSDT", "PORT3USDT", "PUFFERUSDT", "QUICKUSDT",
    "RADUSDT", "SLERFUSDT", "SLPUSDT", "STPTUSDT", "SXPUSDT", "TANSSIUSDT",
    "TOKENUSDT", "UXLINKUSDT", "VOXELUSDT", "XEMUSDT", "YALAUSDT",
]


def test_section_5_2_canonical_json_test_vectors():
    """Verify Section 5.2 exact JSON vectors."""
    arr = [
        "parent",
        "contract",
        "SYMBOL",
        "w1_shock_12h",
        "2025-01-01T00:00:00+00:00",
        "2025-01-01T00:00:00+00:00",
        "2025-01-01T12:00:00+00:00",
        "metrics_5m",
        "2025-01-01",
        "https://example.test/object.zip",
    ]
    vec1_id = collector.compute_logical_archive_record_id(arr)
    assert vec1_id == "d49cdfa17433748ed194a323eb969632d23a2036d4bc5873bf1b80c25069a295"

    url = "https://example.test/object.zip"
    vec2_id = collector.compute_physical_source_object_id(url)
    assert vec2_id == "3c8db1814c8bfc8be6ef2f19ca9527cb313fece63616de1f6226a2321e8c18b1"

    # Reject whitespace or altered separator
    mutated_bytes = json.dumps(arr, indent=2).encode("utf-8")
    assert hashlib.sha256(mutated_bytes).hexdigest() != vec1_id


def test_authority_flags_mapping():
    """Verify authority flags are exactly the 13 False flags."""
    flags = collector.get_authority_flags()
    assert flags == ALL_PERMISSION_FLAGS_FALSE
    assert len(flags) == 13
    for k, v in flags.items():
        assert v is False
        assert type(v) is bool


def test_cohort_and_enumeration_from_real_authorities(tmp_path):
    """Verify exact 41-symbol cohort and 705/664 logical/physical mapping from frozen C/B/matrix."""
    project_root = Path(".").resolve()
    verified_c = verify_c_input(
        project_root=project_root,
        completed_root=Path(C_COMPLETED_ROOT),
        source_export=Path(B_SOURCE_EXPORT),
    )
    cohort = collector.derive_candidate_cohort(verified_c, Path(FROZEN_MATRIX_PATH))
    assert cohort == EXPECTED_COHORT
    assert len(cohort) == 41

    matrix_sha, logical_records, physical_objects = collector.enumerate_candidate_requests(
        Path(FROZEN_MATRIX_PATH), cohort
    )
    assert matrix_sha == FROZEN_MATRIX_SHA
    assert len(logical_records) == 705
    assert len(physical_objects) == 664


def test_prefetch_authority_gate_and_mutations(tmp_path):
    """Verify prefetch gate enforces authority checks and one-run authorization file."""
    run_id = "test_run_20260916_001"
    auth_content = {
        "run_id": run_id,
        "approved_design_sha256": FROZEN_DESIGN_SHA,
        "approved_plan_sha256": FROZEN_PLAN_SHA,
    }
    auth_bytes = json.dumps(auth_content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    auth_file = tmp_path / "network_auth.json"
    auth_file.write_bytes(auth_bytes)
    auth_sha = hashlib.sha256(auth_bytes).hexdigest()

    gate_result = collector.validate_prefetch_authority(
        project_root=Path(".").resolve(),
        source_export=Path(B_SOURCE_EXPORT),
        completed_root=Path(C_COMPLETED_ROOT),
        coverage_matrix=Path(FROZEN_MATRIX_PATH),
        approved_design_path=Path(FROZEN_DESIGN_PATH),
        approved_design_sha=FROZEN_DESIGN_SHA,
        approved_plan_path=Path(FROZEN_PLAN_PATH),
        approved_plan_sha=FROZEN_PLAN_SHA,
        network_authorization_file=auth_file,
        network_authorization_sha=auth_sha,
        run_id=run_id,
    )
    assert gate_result["cohort"] == EXPECTED_COHORT
    assert len(gate_result["logical_records"]) == 705
    assert len(gate_result["physical_objects"]) == 664

    # Negative mutations:
    # 1. Wrong design SHA
    with pytest.raises(collector.AuthorityMismatchError, match="STOP=approved_authority_mismatch"):
        collector.validate_prefetch_authority(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha="0" * 64,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_file=auth_file,
            network_authorization_sha=auth_sha,
            run_id=run_id,
        )

    # 2. Wrong plan SHA
    with pytest.raises(collector.AuthorityMismatchError, match="STOP=approved_authority_mismatch"):
        collector.validate_prefetch_authority(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha="0" * 64,
            network_authorization_file=auth_file,
            network_authorization_sha=auth_sha,
            run_id=run_id,
        )

    # 3. Wrong authorization SHA
    with pytest.raises(collector.AuthorityMismatchError, match="STOP=approved_authority_mismatch"):
        collector.validate_prefetch_authority(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_file=auth_file,
            network_authorization_sha="0" * 64,
            run_id=run_id,
        )

    # 4. Extra key in authorization file
    bad_auth = copy.deepcopy(auth_content)
    bad_auth["extra_key"] = "forbidden"
    bad_bytes = json.dumps(bad_auth).encode("utf-8")
    bad_file = tmp_path / "bad_auth.json"
    bad_file.write_bytes(bad_bytes)
    bad_sha = hashlib.sha256(bad_bytes).hexdigest()
    with pytest.raises(collector.AuthorityMismatchError, match="STOP=approved_authority_mismatch"):
        collector.validate_prefetch_authority(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_file=bad_file,
            network_authorization_sha=bad_sha,
            run_id=run_id,
        )


# =====================================================================
# Task 2 Tests: Transport, ZIP safety, CSV parsing, and Family Reducers
# =====================================================================


def _make_zip(filename: str, content: bytes, encrypted: bool = False, external_attr: int = 0) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zinfo = zipfile.ZipInfo(filename)
        if external_attr:
            zinfo.external_attr = external_attr
        zf.writestr(zinfo, content)
    raw = bytearray(buf.getvalue())
    if encrypted:
        raw[6] = 1  # Local file header flag_bits
        cd_idx = raw.find(b"PK\x01\x02")
        if cd_idx != -1:
            raw[cd_idx + 8] = 1  # Central directory flag_bits
    return bytes(raw)


def test_fetch_terminal_outcomes_with_mock_double():
    """Verify single-request transport behavior and terminal outcomes."""
    call_counts: Dict[str, int] = {}

    def mock_fetch(url: str) -> Tuple[int, bytes, str]:
        call_counts[url] = call_counts.get(url, 0) + 1
        if "404" in url:
            return 404, b"", "archive_not_found_404"
        if "302" in url:
            return 302, b"", "redirect_refused"
        if "timeout" in url:
            return 0, b"", "transport_inconclusive"
        if "429" in url:
            return 429, b"", "transport_inconclusive"
        valid_csv = b"open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n1736294400000,1,1,1,1,1,1736297999999,1,1,1,1,0\n"
        return 200, _make_zip("data.csv", valid_csv), "fetched_verified"

    # 1. 404
    res_404 = collector.fetch_and_validate_physical_object(
        "https://example.test/404.zip", "klines_1h", "AAAUSDT", fetch_callable=mock_fetch
    )
    assert res_404["fetch_status"] == "archive_not_found_404"
    assert call_counts["https://example.test/404.zip"] == 1

    # 2. 302 Redirect Refused
    res_302 = collector.fetch_and_validate_physical_object(
        "https://example.test/302.zip", "klines_1h", "AAAUSDT", fetch_callable=mock_fetch
    )
    assert res_302["fetch_status"] == "redirect_refused"
    assert call_counts["https://example.test/302.zip"] == 1

    # 3. Timeout
    res_timeout = collector.fetch_and_validate_physical_object(
        "https://example.test/timeout.zip", "klines_1h", "AAAUSDT", fetch_callable=mock_fetch
    )
    assert res_timeout["fetch_status"] == "transport_inconclusive"
    assert call_counts["https://example.test/timeout.zip"] == 1

    # 4. 429 Rate limit
    res_429 = collector.fetch_and_validate_physical_object(
        "https://example.test/429.zip", "klines_1h", "AAAUSDT", fetch_callable=mock_fetch
    )
    assert res_429["fetch_status"] == "transport_inconclusive"
    assert call_counts["https://example.test/429.zip"] == 1

    # 5. CSV invalid retains ZIP bytes and CSV path without premature unlinking
    bad_csv = b"open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n1736294400000,INVALID,1,1,1,1,1736297999999,1,1,1,1,0\n"
    res_bad_csv = collector.fetch_and_validate_physical_object(
        "https://example.test/bad.zip",
        "klines_1h",
        "AAAUSDT",
        fetch_callable=lambda u: (200, _make_zip("data.csv", bad_csv), "ok"),
    )
    assert res_bad_csv["fetch_status"] == "csv_invalid"
    assert res_bad_csv["zip_bytes"] is not None
    assert res_bad_csv["csv_bytes"] is not None
    assert isinstance(res_bad_csv["csv_bytes"], Path)
    assert res_bad_csv["csv_bytes"].is_file()
    res_bad_csv["csv_bytes"].unlink(missing_ok=True)


def test_zip_member_safety_contract():
    """Verify Section 5.3 strict ZIP member safety rules."""
    valid_csv = b"open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"

    # Corrupt zip bytes
    status, reason, member, csv_bytes = collector.validate_zip_member(b"not_a_zip_corrupt")
    assert status == "archive_invalid"
    assert "corrupt" in reason or "zip" in reason

    # Multiple members
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.csv", valid_csv)
        zf.writestr("b.csv", valid_csv)
    status, reason, member, csv_bytes = collector.validate_zip_member(buf.getvalue())
    assert status == "archive_invalid"
    assert "multiple" in reason

    # Directory member
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zinfo = zipfile.ZipInfo("dir/")
        zf.writestr(zinfo, b"")
    status, reason, member, csv_bytes = collector.validate_zip_member(buf.getvalue())
    assert status == "archive_invalid"

    # Encrypted member
    enc_zip = _make_zip("data.csv", valid_csv, encrypted=True)
    status, reason, member, csv_bytes = collector.validate_zip_member(enc_zip)
    assert status == "archive_invalid"
    assert "encrypted" in reason

    # Path traversal / escape
    bad_name_zip = _make_zip("../escape.csv", valid_csv)
    status, reason, member, csv_bytes = collector.validate_zip_member(bad_name_zip)
    assert status == "archive_invalid"
    assert "path" in reason or "name" in reason

    # Non-csv extension
    txt_zip = _make_zip("data.txt", valid_csv)
    status, reason, member, csv_bytes = collector.validate_zip_member(txt_zip)
    assert status == "archive_invalid"
    assert "csv" in reason

    # Symlink-like member (mode 0o120000)
    symlink_zip = _make_zip("link.csv", b"target.csv", external_attr=(0o120000 << 16))
    status, reason, member, csv_bytes = collector.validate_zip_member(symlink_zip)
    assert status == "archive_invalid"
    assert "symlink" in reason


def test_csv_parser_and_metrics_5m_identity_failure():
    """Verify Section 5.4 strict parsing and metrics_5m symbol mismatch invalidation."""
    # 1. Invalid header
    bad_header_csv = b"col1,col2\n1,2\n"
    status, reason, header, count, first, last, rows = collector.parse_and_validate_csv(
        "klines_1h", bad_header_csv, "AAAUSDT"
    )
    assert status == "csv_invalid"
    assert "header" in reason

    # 2. metrics_5m wrong symbol in one row
    metrics_header = "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio\n"
    mismatched_metrics = (
        metrics_header
        + "2025-01-08 00:00:00,CORRECTUSDT,100,100,1,1,1,1\n"
        + "2025-01-08 00:05:00,WRONGUSDT,100,100,1,1,1,1\n"
    ).encode("utf-8")
    status, reason, header, count, first, last, rows = collector.parse_and_validate_csv(
        "metrics_5m", mismatched_metrics, "CORRECTUSDT"
    )
    assert status == "csv_invalid"
    assert "symbol" in reason
    assert len(rows) == 0  # No row may contribute on symbol mismatch

    # 3. book_depth missing one percentage
    depth_header = "timestamp,percentage,depth,notional\n"
    # Only 9 percentages instead of required 10
    incomplete_depth = (
        depth_header + "".join(f"2025-01-15 00:00:05,{pct},10,10\n" for pct in [-5, -4, -3, -2, -1, 1, 2, 3, 4])
    ).encode("utf-8")
    status, reason, header, count, first, last, rows = collector.parse_and_validate_csv(
        "book_depth", incomplete_depth, "AAAUSDT"
    )
    assert status == "csv_invalid"
    assert "ladder" in reason or "percentage" in reason


def test_canonical_reef_raw_package_parsers():
    """Verify Section 5.4 family reducers using canonical REEF raw ZIP files."""
    manifest_path = Path(REEF_MANIFEST_PATH)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reef_root = manifest_path.parent

    # Test 5 families on real canonical REEF archives
    categories_tested = set()

    for artifact in manifest["artifacts"]:
        cat = artifact.get("rel_category")
        if cat in {"klines_1h", "metrics_5m", "funding_rate", "book_depth", "agg_trades"}:
            if cat in categories_tested:
                continue
            zip_rel = artifact["relative_zip_path"]
            zip_file = reef_root / zip_rel
            assert zip_file.is_file(), f"REEF file missing: {zip_file}"
            zip_bytes = zip_file.read_bytes()
            assert len(zip_bytes) == artifact["zip_size_bytes"]
            assert hashlib.sha256(zip_bytes).hexdigest() == artifact["zip_sha256"]

            # 1. ZIP member safety
            z_status, z_reason, member_name, csv_bytes = collector.validate_zip_member(zip_bytes)
            assert z_status == "fetched_verified", f"ZIP check failed for {cat}: {z_reason}"
            assert len(csv_bytes) == artifact["csv_records"][0]["csv_size_bytes"]
            assert hashlib.sha256(csv_bytes.read_bytes()).hexdigest() == artifact["csv_records"][0]["csv_sha256"]

            # 2. Strict CSV parse
            c_status, c_reason, header, count, first, last, rows = collector.parse_and_validate_csv(
                cat, csv_bytes, "REEFUSDT"
            )
            assert c_status == "fetched_verified", f"CSV parse failed for {cat}: {c_reason}"
            assert header == artifact["csv_records"][0]["csv_header"]
            assert count == artifact["csv_records"][0]["row_count"]
            assert first == artifact["csv_records"][0]["first_row"]
            assert last == artifact["csv_records"][0]["last_row"]

            # 3. Family coverage reducer
            ts_key = collector.TIMESTAMP_KEYS[cat]
            if rows:
                first_ts = rows[0][ts_key]
                last_ts = rows[-1][ts_key]
                step = collector.GRID_STEP_MS[cat] or 3_600_000
                cov = collector.evaluate_coverage(
                    metric=cat,
                    window="w1_shock_12h",
                    window_start_ms=first_ts,
                    window_end_ms=last_ts + step,
                    rows=rows,
                    canonical_symbol="REEFUSDT",
                    fetch_status="fetched_verified",
                    failure_reason="ok",
                )
                if collector.GRID_STEP_MS[cat] is not None:
                    assert cov["coverage_status"] in {"window_observed", "window_incomplete"}
                else:
                    assert cov["coverage_status"] in {"rows_observed_continuity_not_proven", "not_proven"}

            categories_tested.add(cat)

    assert categories_tested == {"klines_1h", "metrics_5m", "funding_rate", "book_depth", "agg_trades"}


# =====================================================================
# Task 3 Tests: Root Writer, Persistence, and Independent Validator
# =====================================================================


def _make_auth_file(tmp_path: Path, run_id: str) -> Tuple[Path, str]:
    """Helper to create network authorization file."""
    auth_content = {
        "run_id": run_id,
        "approved_design_sha256": FROZEN_DESIGN_SHA,
        "approved_plan_sha256": FROZEN_PLAN_SHA,
    }
    auth_bytes = json.dumps(auth_content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    auth_file = tmp_path / f"network_auth_{run_id}.json"
    auth_file.write_bytes(auth_bytes)
    return auth_file, hashlib.sha256(auth_bytes).hexdigest()


def _make_candidate_output_root(tmp_path: Path) -> Path:
    """Helper to create isolated canonical candidate parent directory."""
    p = tmp_path / "data" / "external_signal_shadow" / "stage1_6f" / "evidence_candidates"
    p.mkdir(parents=True, exist_ok=True)
    return p


def test_validator_and_writer_contract(tmp_path):
    """Verify Task 3 root writer, manifest-last persistence, and validator."""
    run_id = "test_run_20260916_root_001"
    output_root = _make_candidate_output_root(tmp_path)

    auth_file, auth_sha = _make_auth_file(tmp_path, run_id)

    # 1. Reused run_id must collide
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True)
    with pytest.raises(collector.CandidateCollectorError, match="STOP=candidate_run_id_collision"):
        collector.execute_collection_run(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            output_root=output_root,
            run_id=run_id,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_file=auth_file,
            network_authorization_sha=auth_sha,
        )

    # 2. Successful collection run with mock fetch double using canonical REEF fixtures
    run_id_success = CANONICAL_CANDIDATE_RUN_ID
    auth_file_s = Path(".").resolve() / FROZEN_NETWORK_AUTH_RELATIVE_PATH
    auth_sha_s = FROZEN_NETWORK_AUTH_SHA256

    reef_manifest = json.loads(Path(REEF_MANIFEST_PATH).read_text(encoding="utf-8"))
    reef_root = Path(REEF_MANIFEST_PATH).parent
    url_to_bytes = {art["url"]: (reef_root / art["relative_zip_path"]).read_bytes() for art in reef_manifest["artifacts"]}

    def mock_fetch(url: str):
        if url in url_to_bytes:
            return 200, url_to_bytes[url], "ok"
        return 404, b"", "HTTP 404 Not Found"

    res = collector.execute_collection_run(
        project_root=Path(".").resolve(),
        source_export=Path(B_SOURCE_EXPORT),
        completed_root=Path(C_COMPLETED_ROOT),
        coverage_matrix=Path(FROZEN_MATRIX_PATH),
        output_root=output_root,
        run_id=run_id_success,
        approved_design_path=Path(FROZEN_DESIGN_PATH),
        approved_design_sha=FROZEN_DESIGN_SHA,
        approved_plan_path=Path(FROZEN_PLAN_PATH),
        approved_plan_sha=FROZEN_PLAN_SHA,
        network_authorization_file=auth_file_s,
        network_authorization_sha=auth_sha_s,
        fetch_callable=mock_fetch,
    )

    completed_root = output_root / run_id_success
    manifest_path = completed_root / "candidate_manifest.json"
    assert manifest_path.is_file()

    # Verify manifest structure
    assert res["schema_version"] == "stage1_6f_historical_evidence_expansion_candidate_manifest_v1"
    assert res["run_id"] == run_id_success
    assert len(res["cohort"]) == 41
    assert len(res["physical_source_objects"]) == 664
    assert len(res["logical_archive_records"]) == 705
    assert len(res["metric_window_coverages"]) == 369
    assert res["candidate_root_state"] == "collection_terminal_with_gaps_or_unproven_data"
    assert res["capture_mode"] == "historical_ex_post_candidate"
    assert res["point_in_time_source_validated"] is False
    assert res["authority_flags"] == collector.EXACT_EXPECTED_13_FALSE_MAPPING

    # 3. Independent validator on completed root passes
    validated = collector.validate_completed_candidate_root(
        completed_root=completed_root,
        approved_design_path=Path(FROZEN_DESIGN_PATH),
        approved_design_sha=FROZEN_DESIGN_SHA,
        approved_plan_path=Path(FROZEN_PLAN_PATH),
        approved_plan_sha=FROZEN_PLAN_SHA,
        network_authorization_sha=auth_sha_s,
        project_root=Path(".").resolve(),
    )
    assert validated["run_id"] == run_id_success


def test_durable_transition_failures_before_manifest_publication(tmp_path, monkeypatch):
    """Verify durable-transition failures before manifest publication leave no manifest."""
    output_root = _make_candidate_output_root(tmp_path)

    reef_manifest = json.loads(Path(REEF_MANIFEST_PATH).read_text(encoding="utf-8"))
    reef_root = Path(REEF_MANIFEST_PATH).parent
    klines_art = next(a for a in reef_manifest["artifacts"] if a["rel_category"] == "klines_1h")
    valid_klines_zip = (reef_root / klines_art["relative_zip_path"]).read_bytes()

    def mock_fetch(url: str):
        if "klines" in url:
            return 200, valid_klines_zip, "ok"
        return 404, b"", "HTTP 404 Not Found"

    # 1. ZIP write failure injection
    run_id_zip_fail = "test_run_zip_fail"
    auth_file, auth_sha = _make_auth_file(tmp_path, run_id_zip_fail)

    orig_atomic_write = collector.atomic_write_bytes
    def failing_zip_write(target_file: Path, content: bytes) -> str:
        if str(target_file).endswith(".zip"):
            raise collector.CandidateCollectorError("candidate_root_invalid:injected_zip_write_failure")
        return orig_atomic_write(target_file, content)

    monkeypatch.setattr(collector, "atomic_write_bytes", failing_zip_write)
    with pytest.raises(collector.CandidateCollectorError, match="injected_zip_write_failure"):
        collector.execute_collection_run(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            output_root=output_root,
            run_id=run_id_zip_fail,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_file=auth_file,
            network_authorization_sha=auth_sha,
            fetch_callable=mock_fetch,
        )
    # Manifest must NOT exist
    assert not (output_root / run_id_zip_fail / "candidate_manifest.json").exists()
    # Reusing this run_id must fail as collision
    with pytest.raises(collector.CandidateCollectorError, match="STOP=candidate_run_id_collision"):
        collector.execute_collection_run(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            output_root=output_root,
            run_id=run_id_zip_fail,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_file=auth_file,
            network_authorization_sha=auth_sha,
            fetch_callable=mock_fetch,
        )

    # 2. Manifest write failure injection
    monkeypatch.undo()
    run_id_manifest_fail = "test_run_manifest_fail"
    auth_file_m, auth_sha_m = _make_auth_file(tmp_path, run_id_manifest_fail)

    def failing_manifest_write(target_file: Path, content: bytes) -> str:
        if target_file.name == "candidate_manifest.json":
            raise collector.CandidateCollectorError("candidate_root_invalid:injected_manifest_write_failure")
        return orig_atomic_write(target_file, content)

    monkeypatch.setattr(collector, "atomic_write_bytes", failing_manifest_write)
    with pytest.raises(collector.CandidateCollectorError, match="injected_manifest_write_failure"):
        collector.execute_collection_run(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            output_root=output_root,
            run_id=run_id_manifest_fail,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_file=auth_file_m,
            network_authorization_sha=auth_sha_m,
            fetch_callable=mock_fetch,
        )
    assert not (output_root / run_id_manifest_fail / "candidate_manifest.json").exists()


def test_validator_rejects_corrupted_manifest_and_tampered_bytes(tmp_path):
    """Verify independent candidate validator detects tampered bytes or missing manifest."""
    output_root = _make_candidate_output_root(tmp_path)
    run_id_valid = CANONICAL_CANDIDATE_RUN_ID
    auth_file = Path(".").resolve() / FROZEN_NETWORK_AUTH_RELATIVE_PATH
    auth_sha = FROZEN_NETWORK_AUTH_SHA256

    reef_manifest = json.loads(Path(REEF_MANIFEST_PATH).read_text(encoding="utf-8"))
    reef_root = Path(REEF_MANIFEST_PATH).parent
    klines_art = next(a for a in reef_manifest["artifacts"] if a["rel_category"] == "klines_1h")
    valid_klines_zip = (reef_root / klines_art["relative_zip_path"]).read_bytes()

    def mock_fetch(url: str):
        if "klines" in url:
            return 200, valid_klines_zip, "ok"
        return 404, b"", "HTTP 404 Not Found"

    collector.execute_collection_run(
        project_root=Path(".").resolve(),
        source_export=Path(B_SOURCE_EXPORT),
        completed_root=Path(C_COMPLETED_ROOT),
        coverage_matrix=Path(FROZEN_MATRIX_PATH),
        output_root=output_root,
        run_id=run_id_valid,
        approved_design_path=Path(FROZEN_DESIGN_PATH),
        approved_design_sha=FROZEN_DESIGN_SHA,
        approved_plan_path=Path(FROZEN_PLAN_PATH),
        approved_plan_sha=FROZEN_PLAN_SHA,
        network_authorization_file=auth_file,
        network_authorization_sha=auth_sha,
        fetch_callable=mock_fetch,
    )
    valid_root = output_root / run_id_valid
    manifest_bytes = (valid_root / "candidate_manifest.json").read_bytes()

    # 1. Missing manifest
    empty_dir = _make_candidate_output_root(tmp_path / "empty") / "run_empty"
    empty_dir.mkdir(parents=True)
    with pytest.raises(collector.CandidateCollectorError, match="missing_manifest"):
        collector.validate_completed_candidate_root(
            completed_root=empty_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 2. Corrupted JSON manifest
    bad_json_dir = _make_candidate_output_root(tmp_path / "bad_json") / "run_bad_json"
    bad_json_dir.mkdir(parents=True)
    (bad_json_dir / "candidate_manifest.json").write_bytes(b"{not json}")
    with pytest.raises(collector.CandidateCollectorError, match="corrupted_manifest"):
        collector.validate_completed_candidate_root(
            completed_root=bad_json_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 3. Run ID mismatch
    wrong_run_id_dir = _make_candidate_output_root(tmp_path / "wrong_id") / "wrong_run_id"
    import shutil
    shutil.copytree(valid_root, wrong_run_id_dir)
    with pytest.raises(collector.CandidateCollectorError, match="run_id_mismatch"):
        collector.validate_completed_candidate_root(
            completed_root=wrong_run_id_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 4. Tampered authority flag (trade_signal_allowed = True)
    import copy
    m_dict = json.loads(manifest_bytes.decode("utf-8"))
    bad_flags_dict = copy.deepcopy(m_dict)
    bad_flags_dict["authority_flags"]["trade_signal_allowed"] = True
    bad_flags_dir = _make_candidate_output_root(tmp_path / "mutations" / "bad_flags") / run_id_valid
    shutil.copytree(valid_root, bad_flags_dir)
    (bad_flags_dir / "candidate_manifest.json").write_text(json.dumps(bad_flags_dict), encoding="utf-8")
    with pytest.raises(collector.CandidateCollectorError, match="authority_flag_not_false:trade_signal_allowed"):
        collector.validate_completed_candidate_root(
            completed_root=bad_flags_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 5. Tampered ZIP byte on disk
    tampered_zip_dir = _make_candidate_output_root(tmp_path / "mutations" / "tampered_zip") / run_id_valid
    shutil.copytree(valid_root, tampered_zip_dir)
    zips = list((tampered_zip_dir / "zips").glob("*.zip"))
    assert len(zips) > 0
    target_zip = zips[0]
    z_content = bytearray(target_zip.read_bytes())
    z_content[0] = (z_content[0] + 1) % 256
    target_zip.write_bytes(z_content)
    with pytest.raises(collector.CandidateCollectorError, match="zip_sha_mismatch"):
        collector.validate_completed_candidate_root(
            completed_root=tampered_zip_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 6. Unexpected file on disk
    unexpected_file_dir = _make_candidate_output_root(tmp_path / "mutations" / "unexpected_file") / run_id_valid
    shutil.copytree(valid_root, unexpected_file_dir)
    (unexpected_file_dir / "extra.txt").write_text("rogue", encoding="utf-8")
    with pytest.raises(collector.CandidateCollectorError, match="unexpected_file:extra.txt"):
        collector.validate_completed_candidate_root(
            completed_root=unexpected_file_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 7. Stale .tmp file on disk
    stale_tmp_dir = _make_candidate_output_root(tmp_path / "mutations" / "stale_tmp") / run_id_valid
    shutil.copytree(valid_root, stale_tmp_dir)
    (stale_tmp_dir / "stale.tmp").write_bytes(b"temp data")
    with pytest.raises(collector.CandidateCollectorError, match="stale_temp_file:stale.tmp"):
        collector.validate_completed_candidate_root(
            completed_root=stale_tmp_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 8. Symlink detected
    symlink_dir = _make_candidate_output_root(tmp_path / "mutations" / "symlink") / run_id_valid
    shutil.copytree(valid_root, symlink_dir)
    (symlink_dir / "symlink.csv").symlink_to(valid_root / "candidate_manifest.json")
    with pytest.raises(collector.CandidateCollectorError, match="symlink_detected"):
        collector.validate_completed_candidate_root(
            completed_root=symlink_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 9. Coverage entry tampered in manifest
    tampered_cov_dir = _make_candidate_output_root(tmp_path / "mutations" / "tampered_cov") / run_id_valid
    shutil.copytree(valid_root, tampered_cov_dir)
    cov_manifest_p = tampered_cov_dir / "candidate_manifest.json"
    cov_data = json.loads(cov_manifest_p.read_text(encoding="utf-8"))
    cov_data["metric_window_coverages"][0]["reason"] = "tampered_reason"
    cov_manifest_p.write_text(json.dumps(cov_data), encoding="utf-8")
    with pytest.raises(collector.CandidateCollectorError, match="coverage_entry_mismatch"):
        collector.validate_completed_candidate_root(
            completed_root=tampered_cov_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 10. Illegal physical fetch_status
    illegal_phys_dir = _make_candidate_output_root(tmp_path / "mutations" / "illegal_phys") / run_id_valid
    shutil.copytree(valid_root, illegal_phys_dir)
    iphys_manifest_p = illegal_phys_dir / "candidate_manifest.json"
    iphys_data = json.loads(iphys_manifest_p.read_text(encoding="utf-8"))
    iphys_data["physical_source_objects"][0]["fetch_status"] = "rogue_status"
    iphys_manifest_p.write_text(json.dumps(iphys_data), encoding="utf-8")
    with pytest.raises(collector.CandidateCollectorError, match="illegal_physical_fetch_status"):
        collector.validate_completed_candidate_root(
            completed_root=illegal_phys_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 11. Logical record_state mismatch with physical
    rec_mismatch_dir = _make_candidate_output_root(tmp_path / "mutations" / "rec_mismatch") / run_id_valid
    shutil.copytree(valid_root, rec_mismatch_dir)
    rm_manifest_p = rec_mismatch_dir / "candidate_manifest.json"
    rm_data = json.loads(rm_manifest_p.read_text(encoding="utf-8"))
    rm_data["logical_archive_records"][0]["record_state"] = "archive_invalid"
    rm_manifest_p.write_text(json.dumps(rm_data), encoding="utf-8")
    with pytest.raises(collector.CandidateCollectorError, match="record_state_mismatch_with_physical"):
        collector.validate_completed_candidate_root(
            completed_root=rec_mismatch_dir,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
        )

    # 12. Missing workspace authority
    with pytest.raises(collector.CandidateCollectorError, match="missing_workspace_authority"):
        collector.validate_completed_candidate_root(
            completed_root=valid_root,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
            project_root=tmp_path / "non_existent_project_root",
        )


def test_existing_f_reader_rejects_candidate_manifest(tmp_path):
    """Verify existing verify_market_evidence strictly rejects candidate manifest."""
    from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
        MarketEvidenceInvalidError,
        verify_market_evidence,
    )

    candidate_root = tmp_path / "candidate_root"
    candidate_root.mkdir()
    (candidate_root / "gap02_evidence_manifest.json").write_text(
        json.dumps({"schema_version": "stage1_6f_historical_evidence_expansion_candidate_manifest_v1"}), encoding="utf-8"
    )

    with pytest.raises(MarketEvidenceInvalidError):
        verify_market_evidence(candidate_root)


# =====================================================================
# Task 4 Tests: Full Frozen-Authority Integration and Regressions
# =====================================================================


def test_canonical_positive_integration_and_routing(tmp_path):
    """Verify Task 4 positive integration, single-call routing, and invariant preservation."""
    # Recheck authority hashes first
    assert hashlib.sha256(Path(REEF_MANIFEST_PATH).read_bytes()).hexdigest() == REEF_MANIFEST_SHA
    assert hashlib.sha256(Path(FROZEN_MATRIX_PATH).read_bytes()).hexdigest() == FROZEN_MATRIX_SHA
    f_denom_path = Path("src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py")
    f_source_path = Path("src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py")
    assert hashlib.sha256(f_denom_path.read_bytes()).hexdigest() == collector.EXACT_AUTHORITY_FILES["f_denominator_module"]
    assert hashlib.sha256(f_source_path.read_bytes()).hexdigest() == collector.EXACT_AUTHORITY_FILES["f_source_module"]

    # Verify canonical C + reconstruct_denominator yields exactly 41 symbols
    verified_c = verify_c_input(
        project_root=Path(".").resolve(),
        completed_root=Path(C_COMPLETED_ROOT),
        source_export=Path(B_SOURCE_EXPORT),
    )
    c_root = Path(C_COMPLETED_ROOT)
    contracts = [json.loads(line) for line in (c_root / "delisting_contracts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(contracts) == 63
    assert sum(1 for c in contracts if c.get("source_audit_eligible")) == 48

    denom_rows = reconstruct_denominator(verified_c)
    eligible_symbols = {r.symbol for r in denom_rows if r.eligibility_passed}
    assert len(eligible_symbols) == 47

    cohort = collector.derive_candidate_cohort(verified_c, Path(FROZEN_MATRIX_PATH))
    assert len(cohort) == 41

    # Verify 705 logical records and 664 physical objects with 41 shared URLs
    matrix_sha, logical_recs, physical_objs = collector.enumerate_candidate_requests(
        coverage_matrix_path=Path(FROZEN_MATRIX_PATH),
        cohort=cohort,
    )
    assert len(logical_recs) == 705
    assert len(physical_objs) == 664
    from collections import Counter
    url_counts = Counter(r["exact_source_url"] for r in logical_recs)
    shared_urls = [u for u, c in url_counts.items() if c > 1]
    assert len(shared_urls) == 41

    # Transport double with single-call counter
    call_counts: Dict[str, int] = {}
    reef_manifest = json.loads(Path(REEF_MANIFEST_PATH).read_text(encoding="utf-8"))
    reef_root = Path(REEF_MANIFEST_PATH).parent
    klines_art = next(a for a in reef_manifest["artifacts"] if a["rel_category"] == "klines_1h")
    valid_klines_zip = (reef_root / klines_art["relative_zip_path"]).read_bytes()

    def counting_fetch(url: str) -> Tuple[int, bytes, str]:
        call_counts[url] = call_counts.get(url, 0) + 1
        if "klines" in url:
            return 200, valid_klines_zip, "ok"
        return 404, b"", "HTTP 404 Not Found"

    run_id = CANONICAL_CANDIDATE_RUN_ID
    output_root = _make_candidate_output_root(tmp_path)
    auth_file = Path(".").resolve() / FROZEN_NETWORK_AUTH_RELATIVE_PATH
    auth_sha = FROZEN_NETWORK_AUTH_SHA256

    res = collector.execute_collection_run(
        project_root=Path(".").resolve(),
        source_export=Path(B_SOURCE_EXPORT),
        completed_root=Path(C_COMPLETED_ROOT),
        coverage_matrix=Path(FROZEN_MATRIX_PATH),
        output_root=output_root,
        run_id=run_id,
        approved_design_path=Path(FROZEN_DESIGN_PATH),
        approved_design_sha=FROZEN_DESIGN_SHA,
        approved_plan_path=Path(FROZEN_PLAN_PATH),
        approved_plan_sha=FROZEN_PLAN_SHA,
        network_authorization_file=auth_file,
        network_authorization_sha=auth_sha,
        fetch_callable=counting_fetch,
    )
    assert res["run_id"] == run_id

    # Every physical URL must be requested EXACTLY once
    assert len(call_counts) == 664
    assert all(cnt == 1 for cnt in call_counts.values())

    completed_root = output_root / run_id
    # Validator passes
    validated = collector.validate_completed_candidate_root(
        completed_root=completed_root,
        approved_design_path=Path(FROZEN_DESIGN_PATH),
        approved_design_sha=FROZEN_DESIGN_SHA,
        approved_plan_path=Path(FROZEN_PLAN_PATH),
        approved_plan_sha=FROZEN_PLAN_SHA,
        network_authorization_sha=auth_sha,
        project_root=Path(".").resolve(),
    )
    assert validated["run_id"] == run_id

    # Existing F reader strictly rejects this completed root
    from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
        MarketEvidenceInvalidError,
        verify_market_evidence,
    )
    with pytest.raises(MarketEvidenceInvalidError):
        verify_market_evidence(completed_root)

    # Invariant check: REEF package manifest and both F modules remain completely unchanged
    assert hashlib.sha256(Path(REEF_MANIFEST_PATH).read_bytes()).hexdigest() == REEF_MANIFEST_SHA
    assert hashlib.sha256(f_denom_path.read_bytes()).hexdigest() == collector.EXACT_AUTHORITY_FILES["f_denominator_module"]
    assert hashlib.sha256(f_source_path.read_bytes()).hexdigest() == collector.EXACT_AUTHORITY_FILES["f_source_module"]


def test_ast_and_forbidden_patterns():
    """Verify Task 4 Step 2 AST and no-scope / no-permission assertions."""
    import ast

    collector_script_path = Path("scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py")
    tree = ast.parse(collector_script_path.read_text(encoding="utf-8"))

    # 1. Assert no forbidden imports
    forbidden_modules = {
        "requests",
        "boto3",
        "ccxt",
        "binance",
        "paramiko",
        "fabric",
        "subprocess",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import: {alias.name}"
                assert "execution" not in alias.name, f"Forbidden execution import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import from: {node.module}"
                assert "execution" not in node.module, f"Forbidden execution import from: {node.module}"
                if "stage1_6f_historical_diagnostic" in node.module:
                    for alias in node.names:
                        assert alias.name in {
                            "reconstruct_denominator",
                            "ALL_PERMISSION_FLAGS_FALSE",
                            "verify_c_input",
                            "VerifiedCInput",
                        }, f"Forbidden import from F module: {alias.name}"

        # 2. Assert no calls to ZipFile.extract or extractall
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"extract", "extractall"}, f"Forbidden ZipFile extraction method called: {node.func.attr}"


def test_coverage_reducer_grid_gaps_and_duplicates():
    """Verify coverage reducer correctly detects grid gaps, duplicates, and non-grid conflicts."""
    # 1. klines_1h grid coverage
    base_ts = 1736294400000
    step_ms = 3_600_000
    normal_rows = [{"open_time": base_ts + i * step_ms} for i in range(24)]

    cov_normal = collector.evaluate_coverage(
        metric="klines_1h",
        window="w1_shock_12h",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 24 * step_ms,
        rows=normal_rows,
        canonical_symbol="TESTUSDT",
        fetch_status="fetched_verified",
        failure_reason="ok",
    )
    assert cov_normal["coverage_status"] == "window_observed"
    assert cov_normal["gap_count"] == 0
    assert cov_normal["conflict_count"] == 0

    # Gap: remove one hourly bar
    gap_rows = normal_rows[:10] + normal_rows[11:]
    cov_gap = collector.evaluate_coverage(
        metric="klines_1h",
        window="w1_shock_12h",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 24 * step_ms,
        rows=gap_rows,
        canonical_symbol="TESTUSDT",
        fetch_status="fetched_verified",
        failure_reason="ok",
    )
    assert cov_gap["coverage_status"] == "window_incomplete"
    assert cov_gap["gap_count"] == 1

    # Conflict / duplicate: duplicate one hourly bar
    dup_rows = normal_rows + [normal_rows[5]]
    cov_dup = collector.evaluate_coverage(
        metric="klines_1h",
        window="w1_shock_12h",
        window_start_ms=base_ts,
        window_end_ms=base_ts + 24 * step_ms,
        rows=dup_rows,
        canonical_symbol="TESTUSDT",
        fetch_status="fetched_verified",
        failure_reason="ok",
    )
    assert cov_dup["coverage_status"] == "window_incomplete"
    assert cov_dup["conflict_count"] == 1

    # 2. Non-grid funding_rate: duplicate calc_time yields not_proven
    fr_rows = [
        {"calc_time": 1736294400000, "last_funding_rate": 0.0001},
        {"calc_time": 1736323200000, "last_funding_rate": 0.0001},
    ]
    cov_fr = collector.evaluate_coverage(
        metric="funding_rate",
        window="w1_shock_12h",
        window_start_ms=1736294400000,
        window_end_ms=1736380800000,
        rows=fr_rows,
        canonical_symbol="TESTUSDT",
        fetch_status="fetched_verified",
        failure_reason="ok",
    )
    assert cov_fr["coverage_status"] == "rows_observed_continuity_not_proven"
    assert cov_fr["conflict_count"] == 0

    fr_dup_rows = fr_rows + [{"calc_time": 1736294400000, "last_funding_rate": 0.0002}]
    cov_fr_dup = collector.evaluate_coverage(
        metric="funding_rate",
        window="w1_shock_12h",
        window_start_ms=1736294400000,
        window_end_ms=1736380800000,
        rows=fr_dup_rows,
        canonical_symbol="TESTUSDT",
        fetch_status="fetched_verified",
        failure_reason="ok",
    )
    assert cov_fr_dup["coverage_status"] == "not_proven"
    assert cov_fr_dup["conflict_count"] == 1


def test_atomic_write_statvfs_capacity_and_readback_failure(tmp_path, monkeypatch):
    """Verify atomic_write_bytes fail-closed behavior on disk capacity or readback failure."""
    target_file = tmp_path / "atomic_test.dat"
    content = b"sample_data"

    # 1. Capacity check failure (avail space < 2 * len(content))
    class MockStatVfsZero:
        f_bavail = 0
        f_frsize = 4096

    import os
    monkeypatch.setattr(os, "statvfs", lambda p: MockStatVfsZero())
    with pytest.raises(collector.CandidateCollectorError, match="insufficient_disk_space"):
        collector.atomic_write_bytes(target_file, content)

    # 2. Normal write succeeds
    monkeypatch.undo()
    sha = collector.atomic_write_bytes(target_file, content)
    assert hashlib.sha256(content).hexdigest() == sha
    assert target_file.read_bytes() == content

    # 3. Readback length mismatch
    target_file_len_corrupt = tmp_path / "atomic_len_corrupt.dat"
    orig_replace = os.replace

    def mock_replace_len(src, dst):
        orig_replace(src, dst)
        Path(dst).write_bytes(b"longer_corrupted_data")

    monkeypatch.setattr(os, "replace", mock_replace_len)
    with pytest.raises(collector.CandidateCollectorError, match="readback_length_mismatch"):
        collector.atomic_write_bytes(target_file_len_corrupt, content)

    # 4. Readback SHA mismatch with same length
    target_file_sha_corrupt = tmp_path / "atomic_sha_corrupt.dat"

    def mock_replace_sha(src, dst):
        orig_replace(src, dst)
        Path(dst).write_bytes(b"sample_daza")  # exactly 11 bytes

    monkeypatch.setattr(os, "replace", mock_replace_sha)
    with pytest.raises(collector.CandidateCollectorError, match="readback_sha_mismatch"):
        collector.atomic_write_bytes(target_file_sha_corrupt, content)


def test_main_cli_entrypoint(tmp_path, monkeypatch):
    """Verify CLI main entrypoint argument parsing and dispatch."""
    run_id = "test_run_main_001"
    auth_file, auth_sha = _make_auth_file(tmp_path, run_id)
    output_root = _make_candidate_output_root(tmp_path)

    # Mock execute_collection_run and validate_completed_candidate_root to avoid real network
    called = {}

    def mock_execute(*args, **kwargs):
        called["execute"] = True
        return {"run_id": run_id}

    def mock_validate(*args, **kwargs):
        called["validate"] = True
        return {"candidate_root_state": "collection_terminal_with_full_grid_coverage"}

    monkeypatch.setattr(collector, "execute_collection_run", mock_execute)
    monkeypatch.setattr(collector, "validate_completed_candidate_root", mock_validate)

    argv = [
        "--project-root", str(Path(".").resolve()),
        "--source-export", str(Path(B_SOURCE_EXPORT)),
        "--completed-root", str(Path(C_COMPLETED_ROOT)),
        "--coverage-matrix", str(Path(FROZEN_MATRIX_PATH)),
        "--output-root", str(output_root),
        "--run-id", run_id,
        "--approved-design-path", str(Path(FROZEN_DESIGN_PATH)),
        "--approved-design-sha256", FROZEN_DESIGN_SHA,
        "--approved-plan-path", str(Path(FROZEN_PLAN_PATH)),
        "--approved-plan-sha256", FROZEN_PLAN_SHA,
        "--network-authorization-file", str(auth_file),
        "--network-authorization-sha256", auth_sha,
    ]

    rc = collector.main(argv)
    assert rc == 0
    assert called.get("execute") is True
    assert called.get("validate") is True


def test_audit_p0_1_strict_csv_validation_no_coercion():
    """Verify P0-1: CSV fields must be strictly parsed without coercion, rejecting non-numeric/NaN/Inf."""
    # 1. K-line with non-numeric price
    kline_header = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"
    kline_bad_price = (
        kline_header
        + "1736899200000,INVALID_PRICE,0.001011,0.000999,0.000999,261442091,1736902799999,262587.694323,2079,130971365,131596.492114,0\n"
    ).encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("klines_1h", kline_bad_price, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    # 2. K-line with NaN / Inf
    kline_nan = (
        kline_header
        + "1736899200000,NaN,0.001011,0.000999,0.000999,261442091,1736902799999,262587.694323,2079,130971365,131596.492114,0\n"
    ).encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("klines_1h", kline_nan, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    kline_inf = (
        kline_header
        + "1736899200000,0.001005,Inf,0.000999,0.000999,261442091,1736902799999,262587.694323,2079,130971365,131596.492114,0\n"
    ).encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("klines_1h", kline_inf, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    # 2b. K-line with non-numeric ignore column
    kline_bad_ignore = (
        kline_header
        + "1736899200000,0.001005,0.001011,0.000999,0.000999,261442091,1736902799999,262587.694323,2079,130971365,131596.492114,NOT_A_DECLARED_VALUE\n"
    ).encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("klines_1h", kline_bad_ignore, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    # 3. Book depth with float percentage "1.9" (must not be truncated to 1)
    depth_header = "timestamp,percentage,depth,notional\n"
    depth_coerced = (depth_header + "2025-01-15 00:00:05,1.9,100.0,100.0\n").encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("book_depth", depth_coerced, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason or "unapproved_percentage" in reason

    # 4. Book depth with non-numeric / negative depth or notional
    depth_bad_depth = (depth_header + "2025-01-15 00:00:05,1,INVALID_DEPTH,100.0\n").encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("book_depth", depth_bad_depth, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    depth_neg_depth = (depth_header + "2025-01-15 00:00:05,1,-50.0,100.0\n").encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("book_depth", depth_neg_depth, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    depth_nan_notional = (depth_header + "2025-01-15 00:00:05,1,100.0,nan\n").encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("book_depth", depth_nan_notional, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    # 5. Funding rate with NaN rate
    funding_header = "calc_time,funding_interval_hours,last_funding_rate\n"
    funding_nan = (funding_header + "1735689600015,4,nan\n").encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("funding_rate", funding_nan, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    funding_bad_interval = (funding_header + "1735689600015,0,0.0001\n").encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("funding_rate", funding_bad_interval, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    # 6. Metrics 5m with NaN ratio
    metrics_header = "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio\n"
    metrics_nan = (
        metrics_header
        + "2025-01-15 00:00:00,TESTUSDT,nan,4931083.46,4.28,1.34,4.84,1.20\n"
    ).encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("metrics_5m", metrics_nan, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    # 7. Agg trades with invalid boolean or NaN price
    agg_header = "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
    agg_bad_bool = (
        agg_header
        + "128498853,0.001005,94245.0,309344255,309344255,1736899205340,not_a_bool\n"
    ).encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("agg_trades", agg_bad_bool, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason

    agg_nan_price = (
        agg_header
        + "128498853,nan,94245.0,309344255,309344255,1736899205340,true\n"
    ).encode("utf-8")
    status, reason, _, _, _, _, _ = collector.parse_and_validate_csv("agg_trades", agg_nan_price, "TESTUSDT")
    assert status == "csv_invalid"
    assert "row_parse_error" in reason


def test_audit_p0_2_validator_rejects_forged_url_and_undeclared_keys(tmp_path):
    """Verify P0-2: Validator rejects forged exact_source_url and undeclared keys in physical/logical records."""
    import shutil
    run_id = CANONICAL_CANDIDATE_RUN_ID
    auth_file = Path(".").resolve() / FROZEN_NETWORK_AUTH_RELATIVE_PATH
    auth_sha = FROZEN_NETWORK_AUTH_SHA256
    output_root = _make_candidate_output_root(tmp_path)

    collector.execute_collection_run(
        project_root=Path(".").resolve(),
        source_export=Path(B_SOURCE_EXPORT),
        completed_root=Path(C_COMPLETED_ROOT),
        coverage_matrix=Path(FROZEN_MATRIX_PATH),
        output_root=output_root,
        run_id=run_id,
        approved_design_path=Path(FROZEN_DESIGN_PATH),
        approved_design_sha=FROZEN_DESIGN_SHA,
        approved_plan_path=Path(FROZEN_PLAN_PATH),
        approved_plan_sha=FROZEN_PLAN_SHA,
        network_authorization_file=auth_file,
        network_authorization_sha=auth_sha,
        fetch_callable=lambda url: (404, b"", "HTTP 404 Not Found"),
    )
    valid_root = output_root / run_id

    # Base validation passes
    collector.validate_completed_candidate_root(
        completed_root=valid_root,
        approved_design_path=Path(FROZEN_DESIGN_PATH),
        approved_design_sha=FROZEN_DESIGN_SHA,
        approved_plan_path=Path(FROZEN_PLAN_PATH),
        approved_plan_sha=FROZEN_PLAN_SHA,
        network_authorization_sha=auth_sha,
        project_root=Path(".").resolve(),
    )

    # 1. Forged exact_source_url in physical object
    mut_url_root = _make_candidate_output_root(tmp_path / "mut_url") / run_id
    shutil.copytree(valid_root, mut_url_root)
    m_path = mut_url_root / "candidate_manifest.json"
    m_data = json.loads(m_path.read_text(encoding="utf-8"))
    m_data["physical_source_objects"][0]["exact_source_url"] = "https://forged.binance.vision/data/futures/um/daily/klines/fake.zip"
    m_path.write_text(json.dumps(m_data), encoding="utf-8")
    with pytest.raises(collector.CandidateCollectorError, match="exact_source_url_mismatch"):
        collector.validate_completed_candidate_root(
            completed_root=mut_url_root,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
            project_root=Path(".").resolve(),
        )

    # 2. Undeclared key in physical object
    mut_key_phys_root = _make_candidate_output_root(tmp_path / "mut_key_phys") / run_id
    shutil.copytree(valid_root, mut_key_phys_root)
    m_path = mut_key_phys_root / "candidate_manifest.json"
    m_data = json.loads(m_path.read_text(encoding="utf-8"))
    m_data["physical_source_objects"][0]["forged_field"] = "malicious_injection"
    m_path.write_text(json.dumps(m_data), encoding="utf-8")
    with pytest.raises(collector.CandidateCollectorError, match="physical_object_keys_mismatch"):
        collector.validate_completed_candidate_root(
            completed_root=mut_key_phys_root,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
            project_root=Path(".").resolve(),
        )

    # 3. Undeclared key in logical record
    mut_key_log_root = _make_candidate_output_root(tmp_path / "mut_key_log") / run_id
    shutil.copytree(valid_root, mut_key_log_root)
    m_path = mut_key_log_root / "candidate_manifest.json"
    m_data = json.loads(m_path.read_text(encoding="utf-8"))
    m_data["logical_archive_records"][0]["forged_field"] = "malicious_injection"
    m_path.write_text(json.dumps(m_data), encoding="utf-8")
    with pytest.raises(collector.CandidateCollectorError, match="logical_record_keys_mismatch"):
        collector.validate_completed_candidate_root(
            completed_root=mut_key_log_root,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
            project_root=Path(".").resolve(),
        )


def test_audit_p1_1_bounded_chunk_zip_read_and_crc(monkeypatch):
    """Verify P1-1: validate_zip_member uses bounded chunk streaming and checks CRC without whole testzip."""
    # 1. Prohibit testzip: if testzip() is called, monkeypatch raises AssertionError
    def forbidden_testzip(self):
        raise AssertionError("testzip() is strictly prohibited by Section 5.3")

    monkeypatch.setattr(zipfile.ZipFile, "testzip", forbidden_testzip)

    # Valid zip extraction should work without calling testzip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.csv", b"col1,col2\n1,2\n")
    valid_zip_bytes = buf.getvalue()

    status, reason, member_name, csv_bytes = collector.validate_zip_member(valid_zip_bytes)
    assert status == "fetched_verified", f"Failed with {reason}"
    assert member_name == "test.csv"
    assert isinstance(csv_bytes, Path)
    assert csv_bytes.is_file()
    assert csv_bytes == b"col1,col2\n1,2\n"

    # 2. Corrupt CRC in zip payload
    corrupt_buf = io.BytesIO()
    with zipfile.ZipFile(corrupt_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("corrupt.csv", b"col1,col2\n1,2\n")
    raw_zip = bytearray(corrupt_buf.getvalue())
    # Corrupt compressed data in the middle without breaking header
    raw_zip[len(raw_zip) // 2] ^= 0xFF
    status, reason, _, _ = collector.validate_zip_member(bytes(raw_zip))
    assert status == "archive_invalid"
    assert "crc" in reason or "corrupt" in reason or "read_error" in reason

    # 3. Tampered uncompressed size in zip header
    import struct
    tampered_buf = io.BytesIO()
    with zipfile.ZipFile(tampered_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tampered.csv", b"col1,col2\n" + b"1,2\n" * 50)
    tampered_data = bytearray(tampered_buf.getvalue())
    struct.pack_into("<I", tampered_data, 22, 10)
    cd_offset = tampered_data.find(b"\x50\x4b\x01\x02")
    struct.pack_into("<I", tampered_data, cd_offset + 24, 10)
    status, reason, _, _ = collector.validate_zip_member(bytes(tampered_data))
    assert status == "archive_invalid"
    assert "crc" in reason or "read_error" in reason or "size" in reason

    # 4. Oversized member (stream exceeding member.file_size halts early)
    class OversizedStream:
        def __init__(self):
            self.called = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            self.called += 1
            if self.called == 1:
                return b"X" * 100
            return b""

    monkeypatch.setattr(zipfile.ZipFile, "open", lambda self, m: OversizedStream())
    # valid_zip_bytes has test.csv with length 14 bytes; OversizedStream returns 100 bytes (> 14)
    status, reason, _, _ = collector.validate_zip_member(valid_zip_bytes)
    assert status == "archive_invalid"
    assert "member_size_exceeded" in reason


def test_collector_rejects_non_canonical_output_root(tmp_path):
    """Verify collector fail-closed rejection of non-canonical output_root."""
    run_id = "test_run_non_canonical_001"
    auth_file, auth_sha = _make_auth_file(tmp_path, run_id)

    # 1. Non-canonical directory outside project (missing 4-level canonical tail)
    wrong_output_root = tmp_path / "some_random_dir"
    with pytest.raises(collector.CandidateCollectorError, match="STOP=invalid_canonical_candidate_root_path"):
        collector.execute_collection_run(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            output_root=wrong_output_root,
            run_id=run_id,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_file=auth_file,
            network_authorization_sha=auth_sha,
        )

    # 2. Non-canonical directory inside project (candidate_evidence_packages instead of evidence_candidates)
    wrong_project_subroot = Path(".").resolve() / "data" / "external_signal_shadow" / "stage1_6f" / "candidate_evidence_packages"
    with pytest.raises(collector.CandidateCollectorError, match="STOP=invalid_canonical_candidate_root_path"):
        collector.execute_collection_run(
            project_root=Path(".").resolve(),
            source_export=Path(B_SOURCE_EXPORT),
            completed_root=Path(C_COMPLETED_ROOT),
            coverage_matrix=Path(FROZEN_MATRIX_PATH),
            output_root=wrong_project_subroot,
            run_id=run_id,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_file=auth_file,
            network_authorization_sha=auth_sha,
        )


def test_validator_rejects_non_canonical_completed_root_parent(tmp_path):
    """Verify validator fail-closed rejection of non-canonical completed_root parent."""
    wrong_parent_root = tmp_path / "wrong_candidates" / "run_001"
    wrong_parent_root.mkdir(parents=True)
    with pytest.raises(collector.CandidateCollectorError, match="candidate_root_invalid:non_canonical_parent_path"):
        collector.validate_completed_candidate_root(
            completed_root=wrong_parent_root,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha="dummy",
            project_root=Path(".").resolve(),
        )


def test_validator_rejects_legacy_candidate_evidence_packages_run_001():
    """Verify validator strictly rejects previous run located in non-canonical candidate_evidence_packages."""
    legacy_path = Path("data/external_signal_shadow/stage1_6f/candidate_evidence_packages/expansion_candidate_run_20260917_001").resolve()
    if legacy_path.is_dir():
        with pytest.raises(collector.CandidateCollectorError, match="candidate_root_invalid:non_canonical_parent_path"):
            collector.validate_completed_candidate_root(
                completed_root=legacy_path,
                approved_design_path=Path(FROZEN_DESIGN_PATH),
                approved_design_sha=FROZEN_DESIGN_SHA,
                approved_plan_path=Path(FROZEN_PLAN_PATH),
                approved_plan_sha=FROZEN_PLAN_SHA,
                network_authorization_sha="dummy",
                project_root=Path(".").resolve(),
            )


def test_collector_adapter_delegates_to_shared_source_core():
    """Verify that collector.validate_completed_candidate_root adapts shared source core."""
    with pytest.raises(collector.CandidateCollectorError, match="missing_manifest|candidate_root_invalid"):
        collector.validate_completed_candidate_root(
            completed_root=Path("/nonexistent/root"),
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha="dummy",
            project_root=Path(".").resolve(),
        )


def test_collector_adapter_rejects_non_002_alias_network_auth(tmp_path):
    """Verify that collector adapter does not search or select alias network auth for non-002 roots."""
    non_002_run_id = "test_run_non_002_probe_001"
    output_root = _make_candidate_output_root(tmp_path)
    completed_root = output_root / non_002_run_id
    completed_root.mkdir(parents=True)

    # Place alias file in evidence_candidates (parent of completed_root)
    alias_parent_auth = output_root / f"network_auth_{non_002_run_id}.json"
    auth_data = {
        "run_id": non_002_run_id,
        "approved_design_sha256": FROZEN_DESIGN_SHA,
        "approved_plan_sha256": FROZEN_PLAN_SHA,
    }
    auth_bytes = json.dumps(auth_data).encode("utf-8")
    alias_parent_auth.write_bytes(auth_bytes)
    auth_sha = hashlib.sha256(auth_bytes).hexdigest()

    auth_pkt = {
        key: {
            "path": rel_p,
            "sha256": collector.EXACT_AUTHORITY_FILES[key],
        }
        for rel_p, key in collector.FIXED_AUTHORITY_KEY_MAP.items()
    }
    auth_pkt["approved_historical_evidence_expansion_design"] = {
        "path": FROZEN_DESIGN_PATH,
        "sha256": FROZEN_DESIGN_SHA,
    }
    auth_pkt["approved_expansion_implementation_plan"] = {
        "path": FROZEN_PLAN_PATH,
        "sha256": FROZEN_PLAN_SHA,
    }
    auth_pkt["network_collection_authorization"] = {
        "run_id": non_002_run_id,
        "approved_design_sha256": FROZEN_DESIGN_SHA,
        "approved_plan_sha256": FROZEN_PLAN_SHA,
        "authorization_record_sha256": auth_sha,
    }

    # Place manifest in completed_root with all 13 false flags, valid keys
    manifest_data = {
        "schema_version": collector.SCHEMA_VERSION,
        "run_id": non_002_run_id,
        "authority_packet": auth_pkt,
        "cohort": EXPECTED_COHORT,
        "physical_source_objects": [],
        "logical_archive_records": [],
        "metric_window_coverages": [],
        "candidate_root_state": "collection_terminal_with_gaps_or_unproven_data",
        "capture_mode": "historical_ex_post_candidate",
        "point_in_time_source_validated": False,
        "authority_flags": collector.EXACT_EXPECTED_13_FALSE_MAPPING,
    }
    (completed_root / "candidate_manifest.json").write_bytes(
        json.dumps(manifest_data).encode("utf-8")
    )

    # Call validate_completed_candidate_root
    # It must NOT select alias_parent_auth. It must fail closed because configs/authorizations/ does not have this mapping.
    with pytest.raises(collector.CandidateCollectorError) as exc_info:
        collector.validate_completed_candidate_root(
            completed_root=completed_root,
            approved_design_path=Path(FROZEN_DESIGN_PATH),
            approved_design_sha=FROZEN_DESIGN_SHA,
            approved_plan_path=Path(FROZEN_PLAN_PATH),
            approved_plan_sha=FROZEN_PLAN_SHA,
            network_authorization_sha=auth_sha,
            project_root=Path(".").resolve(),
        )

    err_msg = str(exc_info.value)
    assert "missing_workspace_authority" in err_msg
    assert f"network_auth_{non_002_run_id}.json" in err_msg
    assert str(alias_parent_auth) not in err_msg
