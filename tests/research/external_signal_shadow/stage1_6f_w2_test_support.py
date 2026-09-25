"""Test support module for Stage 1.6F-W2 historical price evidence expansion.

Implements Rule 15 canonical fixture derivation, mirroring, and single declared mutation.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import pytest

W2_DESIGN_PATH = "docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md"
W2_DESIGN_SHA = "11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303"

W2_PLAN_PATH = "docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md"
W2_PLAN_SHA = "183689a6b786ccd3dce9f74f5d1fc2e9ccc1741d80f243f5724dd3b7de149229"

EXPANSION_DESIGN_PATH = "docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md"
EXPANSION_DESIGN_SHA = "1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4"

EXPANSION_PLAN_PATH = "docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md"
EXPANSION_PLAN_SHA = "fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d"

ADMISSION_DESIGN_PATH = "docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md"
ADMISSION_DESIGN_SHA = "dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097"

CARDINALITY_DELTA_DESIGN_PATH = "docs/designs/2026-09-20-external-signal-shadow-lab-stage1-6f-candidate-w1-parent-article-cardinality-correction-delta-design_CN.md"
CARDINALITY_DELTA_DESIGN_SHA = "02945b5aa9989e48b50381876601ff72f7080878e4e5eb7cc6cdc6eaaf8617f9"

CANONICAL_002_RELATIVE_PATH = "data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002"
CANONICAL_002_MANIFEST_SHA = "b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67"

CANONICAL_002_NETWORK_AUTH_PATH = "configs/authorizations/network_auth_expansion_run_20260917_002.json"
CANONICAL_002_NETWORK_AUTH_SHA = "8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6"

COVERAGE_MATRIX_RELATIVE = "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json"
COVERAGE_MATRIX_SHA = "b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8"

C_COMPLETED_ROOT_RELATIVE = "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z"
B_SOURCE_EXPORT_RELATIVE = "data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090"

PARENT_F_DESIGN_PATH = "docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md"
PARENT_F_DESIGN_SHA = "87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c"

SCHEMA_DELTA_PATH = "docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md"
SCHEMA_DELTA_SHA = "8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628"

F_PLAN_PATH = "docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md"
F_PLAN_SHA = "6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f"

REEF_MANIFEST_RELATIVE = "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json"
REEF_MANIFEST_SHA = "9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f"

FROZEN_AUTHORITY_REGISTRY: Dict[str, str] = {
    W2_DESIGN_PATH: W2_DESIGN_SHA,
    EXPANSION_DESIGN_PATH: EXPANSION_DESIGN_SHA,
    EXPANSION_PLAN_PATH: EXPANSION_PLAN_SHA,
    ADMISSION_DESIGN_PATH: ADMISSION_DESIGN_SHA,
    CARDINALITY_DELTA_DESIGN_PATH: CARDINALITY_DELTA_DESIGN_SHA,
    f"{CANONICAL_002_RELATIVE_PATH}/candidate_manifest.json": CANONICAL_002_MANIFEST_SHA,
    CANONICAL_002_NETWORK_AUTH_PATH: CANONICAL_002_NETWORK_AUTH_SHA,
    COVERAGE_MATRIX_RELATIVE: COVERAGE_MATRIX_SHA,
    "src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py": "81dca38c323a1632e7e1302b8016a40603c970cb16da58ea13108b5a2ae23f3b",
    "scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py": "32c8b06e3167b9d2c5010f5efc95e777748f1a53b552731cdf4f192a8262c4dc",
    PARENT_F_DESIGN_PATH: PARENT_F_DESIGN_SHA,
    SCHEMA_DELTA_PATH: SCHEMA_DELTA_SHA,
    F_PLAN_PATH: F_PLAN_SHA,
    REEF_MANIFEST_RELATIVE: REEF_MANIFEST_SHA,
    f"{C_COMPLETED_ROOT_RELATIVE}/completion_manifest.json": "226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0",
    f"{C_COMPLETED_ROOT_RELATIVE}/source_export_receipt.json": "07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e",
    f"{B_SOURCE_EXPORT_RELATIVE}/sealed_export_manifest.json": "1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be",
    "src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py": "84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3",
    "src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py": "00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f",
}

FROZEN_13_FALSE_FLAGS: Dict[str, bool] = {
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
}

ALL_URLS_SHA256 = "3b9ab69a8c1236cab59f161636ae9e4136465ca599d735ef65e37fd2cc574a46"
REUSE_URLS_SHA256 = "9773f11e316ce480651b0debf6258fefbd39a1ee9bdc2d6bdd838484704ed405"
FETCH_URLS_SHA256 = "6eac006f8854a17a2d78b4306c03da6f28528aba58ffcfafd6b5f078d4ed7058"


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

    # 2. Mirror Plan file
    plan_src = root / W2_PLAN_PATH
    if plan_src.is_file():
        dst_plan = mirror_root / W2_PLAN_PATH
        _link_or_copy(plan_src, dst_plan)

    # 3. Mirror canonical directories
    dir_roots = [
        Path(CANONICAL_002_RELATIVE_PATH),
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

    # 4. Mirror configs/base.py
    _link_or_copy(root / "configs/base.py", mirror_root / "configs/base.py")

    return mirror_root


def mutate_mirror_file(file_path: Path, new_content: bytes) -> None:
    """Safely unlink destination first to break hard-link, then write mutated bytes."""
    if file_path.exists() or file_path.is_symlink():
        file_path.unlink()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(new_content)


def create_test_network_authorization(
    destination_path: Path,
    *,
    run_id: str,
    design_sha256: str = W2_DESIGN_SHA,
    plan_sha256: str = W2_PLAN_SHA,
    all_urls_sha256: str = ALL_URLS_SHA256,
    reuse_urls_sha256: str = REUSE_URLS_SHA256,
    fetch_urls_sha256: str = FETCH_URLS_SHA256,
    max_requests: int = 171,
    public_archive_get_allowed: bool = True,
    permission_flags: Dict[str, bool] | None = None,
) -> tuple[Path, str]:
    """Create valid test-only one-time network authorization artifact."""
    payload = {
        "schema_version": "stage1_6f_w2_network_authorization_v1",
        "run_id": run_id,
        "design_sha256": design_sha256,
        "plan_sha256": plan_sha256,
        "all_urls_sha256": all_urls_sha256,
        "reuse_urls_sha256": reuse_urls_sha256,
        "fetch_urls_sha256": fetch_urls_sha256,
        "max_requests": max_requests,
        "public_archive_get_allowed": public_archive_get_allowed,
        "permission_flags": permission_flags or dict(FROZEN_13_FALSE_FLAGS),
    }
    raw_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
    mutate_mirror_file(destination_path, raw_bytes)
    sha = hashlib.sha256(raw_bytes).hexdigest()
    return destination_path, sha


class FakeResponse:
    """Deterministic fake HTTP response for stream/transport testing."""

    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None):
        self.status = status
        self.code = status
        self.body = body
        self.headers = headers or {}
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self.body):
            return b""
        if size < 0 or self._offset + size > len(self.body):
            chunk = self.body[self._offset:]
            self._offset = len(self.body)
            return chunk
        chunk = self.body[self._offset : self._offset + size]
        self._offset += size
        return chunk

    def close(self) -> None:
        pass

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


def expected_status_or_stop(status: str) -> Any:
    if status.startswith("STOP="):
        return pytest.raises(Exception, match=status)
    return contextlib.nullcontext()


def make_transport(event: Any) -> Any:
    def _transport(url: str) -> FakeResponse:
        if isinstance(event, Exception):
            raise event
        if event == "timeout":
            raise TimeoutError("Simulated socket timeout")
        if isinstance(event, tuple) and len(event) == 2:
            return FakeResponse(status=event[0], body=event[1])
        if isinstance(event, int):
            return FakeResponse(status=event, body=b"")
        if isinstance(event, FakeResponse):
            return event
        if callable(event):
            return event(url)
        raise ValueError(f"Unknown transport event: {event}")

    return _transport


@dataclass(frozen=True)
class CanonicalW2Root:
    candidate_root: Path
    authority_kwargs: Dict[str, Any]
    manifest: Dict[str, Any]

    def single_point_mutation(self, mutation: str) -> "CanonicalW2Root":
        mut_parent = self.candidate_root.parent / f"mut_{mutation}"
        if mut_parent.exists():
            shutil.rmtree(mut_parent)
        mut_parent.mkdir(parents=True, exist_ok=True)
        mut_dir = mut_parent / self.candidate_root.name
        shutil.copytree(self.candidate_root, mut_dir)

        manifest_path = mut_dir / "candidate_manifest.json"
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

        if mutation == "extra_manifest_key":
            manifest_data["bogus_extra_key"] = "forbidden"
            manifest_path.unlink()
            manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        elif mutation == "forged_url":
            manifest_data["physical_source_objects"][0]["exact_source_url"] = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/forged.zip"
            manifest_path.unlink()
            manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        elif mutation == "http_bool":
            manifest_data["physical_source_objects"][0]["http_status_or_transport_error"] = True
            manifest_path.unlink()
            manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        elif mutation == "wrong_member":
            zips = sorted(list((mut_dir / "zips").glob("*.zip")))
            assert len(zips) > 0
            target_zip = zips[0]
            target_zip.unlink()
            with zipfile.ZipFile(target_zip, "w") as zf:
                zf.writestr("wrong_member_name.csv", b"open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n")

        elif mutation == "header_only_csv":
            csvs = sorted(list((mut_dir / "csvs").glob("*.csv")))
            assert len(csvs) > 0
            target_csv = csvs[0]
            header = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"
            target_csv.unlink()
            target_csv.write_text(header, encoding="utf-8")
            target_zip = mut_dir / "zips" / f"{target_csv.stem}.zip"
            with zipfile.ZipFile(target_zip, "r") as zf_in:
                member_name = zf_in.namelist()[0]
            target_zip.unlink()
            with zipfile.ZipFile(target_zip, "w") as zf:
                zf.writestr(member_name, header.encode("utf-8"))

        elif mutation == "duplicate_open_time":
            csvs = sorted(list((mut_dir / "csvs").glob("*.csv")))
            assert len(csvs) > 0
            target_csv = csvs[0]
            lines = target_csv.read_text(encoding="utf-8").splitlines()
            assert len(lines) >= 2
            new_lines = [lines[0], lines[1], lines[1]] + lines[2:]
            new_content = "\n".join(new_lines) + "\n"
            target_csv.unlink()
            target_csv.write_text(new_content, encoding="utf-8")
            target_zip = mut_dir / "zips" / f"{target_csv.stem}.zip"
            with zipfile.ZipFile(target_zip, "r") as zf_in:
                member_name = zf_in.namelist()[0]
            target_zip.unlink()
            with zipfile.ZipFile(target_zip, "w") as zf:
                zf.writestr(member_name, new_content.encode("utf-8"))

        elif mutation == "root_state_all_complete":
            manifest_data["candidate_root_state"] = "collection_terminal_all_complete_bars"
            manifest_path.unlink()
            manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        else:
            raise ValueError(f"Unknown mutation: {mutation}")

        new_kwargs = dict(self.authority_kwargs)
        new_kwargs["candidate_root"] = mut_dir
        return CanonicalW2Root(
            candidate_root=mut_dir,
            authority_kwargs=new_kwargs,
            manifest=manifest_data,
        )


def build_canonical_w2_root_fixture(
    base_dir: Path,
    canonical_w2_inputs: Dict[str, Any],
    run_id: str | None = None,
) -> CanonicalW2Root:
    """Build canonical W2 gaps root fixture with 9 copied 002 objects and 171 inconclusive objects."""
    import src.research.external_signal_shadow.stage1_6f_w2_evidence_source as w2_source

    if run_id is None:
        auth_bytes = canonical_w2_inputs["network_authorization_path"].read_bytes()
        auth_data = json.loads(auth_bytes.decode("utf-8"))
        run_id = auth_data["run_id"]

    authority = w2_source.derive_w2_authority_inputs(**canonical_w2_inputs)
    request_set = w2_source.derive_w2_request_set(authority)

    candidate_root = base_dir / "data/external_signal_shadow/stage1_6f/w2_evidence_candidates" / run_id
    zips_dir = candidate_root / "zips"
    csvs_dir = candidate_root / "csvs"
    zips_dir.mkdir(parents=True, exist_ok=True)
    csvs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy 9 canonical 002 physical objects
    verified_002_objs = {
        obj["physical_source_object_id"]: obj
        for obj in authority.verified_002.manifest["physical_source_objects"]
    }

    physical_records: list[dict[str, Any]] = []
    loaded_csv_rows: dict[str, list[dict[str, Any]]] = {}

    for phys in request_set.physical_records:
        pid = phys["physical_source_object_id"]
        if pid in request_set.reuse_ids:
            old_obj = verified_002_objs[pid]
            src_zip = authority.verified_002.completed_root / old_obj["zip_relative_path"]
            src_csv = authority.verified_002.completed_root / old_obj["csv_relative_path"]
            dst_zip = candidate_root / old_obj["zip_relative_path"]
            dst_csv = candidate_root / old_obj["csv_relative_path"]

            shutil.copy2(src_zip, dst_zip)
            shutil.copy2(src_csv, dst_csv)

            obj = dict(old_obj)
            obj["acquisition_method"] = "copied_verified_002"
            obj["source_manifest_sha256"] = CANONICAL_002_MANIFEST_SHA
            obj["source_physical_source_object_id"] = pid
            obj["network_attempt_count"] = 0
            obj["http_status_or_transport_error"] = None
            obj["request_started_at_ms"] = None
            obj["response_observed_at_ms"] = None
            obj["reason"] = "canonical_002_reused"
            physical_records.append(obj)

            # Pre-parse CSV rows for coverage calculation
            valid, reason, rows, _, _, _ = w2_source.validate_w2_csv_content(
                dst_csv.read_bytes(),
                obj["exact_source_url"],
            )
            assert valid, f"Canonical 002 CSV invalid: {reason}"
            loaded_csv_rows[pid] = rows
        else:
            obj = {
                "physical_source_object_id": pid,
                "exact_source_url": phys["exact_source_url"],
                "fetch_status": "transport_inconclusive",
                "http_status_or_transport_error": "Connection timed out",
                "zip_relative_path": None,
                "zip_byte_length": None,
                "zip_sha256": None,
                "csv_relative_path": None,
                "csv_byte_length": None,
                "csv_sha256": None,
                "zip_member_name": None,
                "csv_header": None,
                "csv_row_count": 0,
                "first_row": None,
                "last_row": None,
                "request_started_at_ms": 1726560000000,
                "response_observed_at_ms": None,
                "reason": "transport_inconclusive:test_mock",
                "acquisition_method": "network_get",
                "source_manifest_sha256": None,
                "source_physical_source_object_id": None,
                "network_attempt_count": 1,
            }
            physical_records.append(obj)

    # 2. Build logical archive records
    phys_map = {obj["physical_source_object_id"]: obj for obj in physical_records}
    logical_records: list[dict[str, Any]] = []
    for log_rec in request_set.logical_records:
        pid = log_rec["physical_source_object_id"]
        rec = dict(log_rec)
        rec["record_state"] = phys_map[pid]["fetch_status"]
        logical_records.append(rec)

    # 3. Compute metric window coverages
    metric_coverages = w2_source.compute_w2_metric_coverages(
        authority.denominator_records,
        logical_records,
        phys_map,
        loaded_csv_rows,
    )

    # 4. Authority packet
    frozen_inputs = [
        {"path": rel_p, "sha256": exp_sha}
        for rel_p, exp_sha in sorted(FROZEN_AUTHORITY_REGISTRY.items())
    ]

    auth_path = canonical_w2_inputs["network_authorization_path"]
    proj_root = canonical_w2_inputs["project_root"]
    try:
        rel_auth_p = str(auth_path.relative_to(proj_root))
    except ValueError:
        rel_auth_p = str(auth_path)

    manifest_data = {
        "schema_version": "stage1_6f_w2_historical_price_candidate_manifest_v1",
        "run_id": run_id,
        "authority_packet": {
            "frozen_inputs": frozen_inputs,
            "approved_design": {
                "path": W2_DESIGN_PATH,
                "sha256": W2_DESIGN_SHA,
            },
            "approved_plan": {
                "path": W2_PLAN_PATH,
                "sha256": W2_PLAN_SHA,
            },
            "network_authorization": {
                "path": rel_auth_p,
                "sha256": canonical_w2_inputs["network_authorization_sha"],
                "run_id": run_id,
            },
        },
        "denominator_records": list(authority.denominator_records),
        "logical_archive_records": logical_records,
        "physical_source_objects": physical_records,
        "metric_window_coverages": list(metric_coverages),
        "request_set": {
            "all_urls_sha256": request_set.all_urls_sha256,
            "reuse_urls_sha256": request_set.reuse_urls_sha256,
            "fetch_urls_sha256": request_set.fetch_urls_sha256,
            "n_logical": len(request_set.logical_records),
            "n_physical": len(request_set.physical_records),
            "n_reused": len(request_set.reuse_ids),
            "n_network_attempts": len(request_set.fetch_ids),
        },
        "candidate_root_state": "collection_terminal_with_evidence_gaps",
        "capture_mode": "historical_ex_post_candidate",
        "point_in_time_source_validated": False,
        "authority_flags": dict(FROZEN_13_FALSE_FLAGS),
    }

    manifest_file = candidate_root / "candidate_manifest.json"
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    authority_kwargs = {
        "project_root": canonical_w2_inputs["project_root"],
        "candidate_root": candidate_root,
        "approved_design_path": canonical_w2_inputs["approved_design_path"],
        "approved_design_sha": canonical_w2_inputs["approved_design_sha"],
        "approved_plan_path": canonical_w2_inputs["approved_plan_path"],
        "approved_plan_sha": canonical_w2_inputs["approved_plan_sha"],
        "network_authorization_path": canonical_w2_inputs["network_authorization_path"],
        "network_authorization_sha": canonical_w2_inputs["network_authorization_sha"],
    }

    return CanonicalW2Root(
        candidate_root=candidate_root,
        authority_kwargs=authority_kwargs,
        manifest=manifest_data,
    )

