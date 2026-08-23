"""Test support utilities for Stage 1.6A sealed-export adapter tests."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

SOURCE_PROFILE_ID = "binance_public_web_bapi_en_delisting_catalog_v2"
SELECTED_CATALOG_ID = 161
SELECTED_CATALOG_NAME = "Delisting"
DEFAULT_HEADERS_SHA = "a" * 64
DEFAULT_RUN_ID = "hist_synthetic_run_001"
DEFAULT_EXPORT_ID = "e" * 64


def trusted_article(
    article_id: Optional[str] = None,
    title: str = "Binance Will Delist TokenA (2026-08-20)",
    publish_date: int = 1700000000000,
    body_nodes: Optional[List[Dict[str, Any]]] = None,
    raw_payload_bytes: Optional[bytes] = None,
) -> Dict[str, Any]:
    aid = article_id or ("1" * 32)
    if body_nodes is None:
        body_nodes = [
            {"node": "element", "tag": "p", "child": [{"node": "text", "text": "Fellow Binancians,"}]},
            {"node": "element", "tag": "p", "child": [{"node": "text", "text": "Binance Futures will delist the USDⓈ-M TOKENAUSDT Perpetual Contract at 2026-08-25 09:00 (UTC)."}]},
        ]
    body_str = json.dumps({"node": "root", "child": body_nodes})
    if raw_payload_bytes is None:
        bapi_envelope = {
            "code": "000000",
            "message": None,
            "data": {
                "id": 248842,
                "code": aid,
                "title": title,
                "body": body_str,
                "publishDate": publish_date,
            },
        }
        raw_payload_bytes = json.dumps(bapi_envelope).encode("utf-8")
    return {
        "source_article_id": aid,
        "title": title,
        "publish_date": publish_date,
        "trust_validation_status": "trusted",
        "raw_payload_bytes": raw_payload_bytes,
    }


def nontrusted_article(
    article_id: Optional[str] = None,
    title: str = "Binance Delisting Notice",
    publish_date: int = 1700000000000,
    trust_validation_status: str = "network_error",
) -> Dict[str, Any]:
    aid = article_id or ("2" * 32)
    return {
        "source_article_id": aid,
        "title": title,
        "publish_date": publish_date,
        "trust_validation_status": trust_validation_status,
        "raw_payload_bytes": None,
    }


def build_valid_historical_sealed_export(
    tmp_path: Path,
    *,
    article_specs: Optional[List[Dict[str, Any]]] = None,
    run_id: str = DEFAULT_RUN_ID,
    export_id: str = DEFAULT_EXPORT_ID,
    from_ms: int = 1700000000000,
    to_ms: int = 1710000000000,
    headers_profile_sha: str = DEFAULT_HEADERS_SHA,
) -> tuple[Path, Path]:
    """Build a minimal synthetic valid historical sealed export under project_root."""
    if article_specs is None:
        article_specs = [trusted_article()]

    project_root = tmp_path
    export_parent = project_root / "data" / "external_signal_shadow" / "stage1_6b" / "historical_backfill" / run_id / "sealed_exports"
    export_dir = export_parent / export_id
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "list_captures").mkdir(parents=True, exist_ok=True)
    (export_dir / "raw_payloads" / "indices").mkdir(parents=True, exist_ok=True)
    (export_dir / "raw_payloads" / "details").mkdir(parents=True, exist_ok=True)
    (export_dir / "detail_observations").mkdir(parents=True, exist_ok=True)

    artifacts_meta = []

    def _write_artifact(rel_path: str, content_bytes: bytes):
        p = export_dir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content_bytes)
        artifacts_meta.append({
            "relative_path": rel_path,
            "sha256": hashlib.sha256(content_bytes).hexdigest(),
            "byte_count": len(content_bytes),
        })

    # 1. Raw index payload
    raw_catalog_articles = []
    for idx, spec in enumerate(article_specs, start=1):
        raw_catalog_articles.append({
            "id": 1000 + idx,
            "code": spec["source_article_id"],
            "title": spec["title"],
            "releaseDate": spec["publish_date"],
        })
    raw_index_dict = {
        "code": "000000",
        "data": {
            "catalogs": [{"catalogId": SELECTED_CATALOG_ID, "catalogName": SELECTED_CATALOG_NAME, "total": len(article_specs), "articles": raw_catalog_articles}]
        }
    }
    raw_index_bytes = json.dumps(raw_index_dict).encode("utf-8")
    raw_index_sha = hashlib.sha256(raw_index_bytes).hexdigest()
    raw_index_rel = f"raw_payloads/indices/{raw_index_sha[:2]}/{raw_index_sha}.json"
    _write_artifact(raw_index_rel, raw_index_bytes)

    # 2. List captures
    list_capture_rec = {
        "schema_version": "stage1_6b_list_capture_v2",
        "capture_mode": "historical_backfill",
        "source_profile_id": SOURCE_PROFILE_ID,
        "selected_catalog_id": SELECTED_CATALOG_ID,
        "selected_catalog_name": SELECTED_CATALOG_NAME,
        "selected_catalog_total": len(article_specs),
        "article_count": len(article_specs),
        "raw_sha": raw_index_sha,
        "first_list_capture_id": "lc_sweep_a_p1",
        "page_index": 1,
        "page_size": len(article_specs),
        "sweep_stage": "sweep_a",
        "record_seq": 1,
        "captured_at_ms": 1700000000000,
    }
    _write_artifact("list_captures/sweep_a_0001.jsonl", (json.dumps(list_capture_rec) + "\n").encode("utf-8"))

    # 3. Discoveries
    discoveries_lines = []
    observations_lines = []
    revisions_lines = []

    for idx, spec in enumerate(article_specs, start=1):
        aid = spec["source_article_id"]
        ad_rec = {
            "schema_version": "stage1_6b_article_discovery_v2",
            "capture_mode": "historical_backfill",
            "source_profile_id": SOURCE_PROFILE_ID,
            "source_catalog_id": SELECTED_CATALOG_ID,
            "source_catalog_name": SELECTED_CATALOG_NAME,
            "source_article_id": aid,
            "discovery_title": spec["title"],
            "first_list_capture_id": "lc_sweep_a_p1",
            "discovery_rule_version": "candidate_discovery_rule_v1",
            "notice_lineage_first_detected_at_ms": None,
            "record_seq": idx,
            "captured_at_ms": 1700000000000 + idx,
        }
        discoveries_lines.append(json.dumps(ad_rec))

        obs_id = hashlib.sha256(f"obs_{aid}_{idx}".encode("utf-8")).hexdigest()
        raw_detail_sha = None
        raw_detail_rel = None
        if spec["trust_validation_status"] == "trusted" and spec.get("raw_payload_bytes") is not None:
            raw_bytes = spec["raw_payload_bytes"]
            raw_detail_sha = hashlib.sha256(raw_bytes).hexdigest()
            raw_detail_rel = f"raw_payloads/detail/{aid}/{raw_detail_sha}.bin"
            _write_artifact(raw_detail_rel, raw_bytes)

            rev_id = hashlib.sha256(f"rev_{aid}_{raw_detail_sha}".encode("utf-8")).hexdigest()
            rev_rec = {
                "schema_version": "stage1_6b_detail_revision_v1",
                "capture_mode": "historical_backfill",
                "source_profile_id": SOURCE_PROFILE_ID,
                "source_article_id": aid,
                "detail_revision_id": rev_id,
                "detail_raw_sha256": raw_detail_sha,
                "raw_payload_relative_path": raw_detail_rel,
                "request_variant": "bapi_article_detail_query_v1",
                "source_locale": "en",
                "source_surface": "announcement_detail",
                "t_detail_trusted_ms": 1700000000000 + idx,
                "t_raw_persisted_ms": 1700000000000 + idx,
                "record_seq": idx,
                "captured_at_ms": 1700000000000 + idx,
            }
            revisions_lines.append(json.dumps(rev_rec))

        obs_rec = {
            "schema_version": "stage1_6b_detail_observation_v1",
            "capture_mode": "historical_backfill",
            "source_profile_id": SOURCE_PROFILE_ID,
            "source_article_id": aid,
            "request_observation_id": obs_id,
            "request_variant": "bapi_article_detail_query_v1",
            "requested_url": f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode={aid}",
            "final_url": f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode={aid}",
            "http_status": 200 if spec["trust_validation_status"] == "trusted" else 0,
            "content_type": "application/json",
            "trust_validation_status": spec["trust_validation_status"],
            "raw_payload_sha256": raw_detail_sha,
            "raw_payload_bytes": len(spec["raw_payload_bytes"]) if spec.get("raw_payload_bytes") else 0,
            "raw_payload_relative_path": raw_detail_rel,
            "request_headers_profile_sha256": headers_profile_sha,
            "run_id": run_id,
            "poll_seq": 1,
            "record_seq": idx,
            "captured_at_ms": 1700000000000 + idx,
            "t_detail_receive_ms": 1700000000000 + idx,
        }
        observations_lines.append(json.dumps(obs_rec))

    _write_artifact("article_discoveries.jsonl", ("\n".join(discoveries_lines) + "\n").encode("utf-8"))
    _write_artifact("detail_observations/historical.jsonl", ("\n".join(observations_lines) + "\n").encode("utf-8"))
    _write_artifact("detail_revisions.jsonl", ("\n".join(revisions_lines) + "\n" if revisions_lines else "").encode("utf-8"))

    # 4. Control files
    attestation = {
        "schema_version": "stage1_6b_source_profile_probe_attestation_v2",
        "source_profile_id": SOURCE_PROFILE_ID,
        "selected_catalog_id": SELECTED_CATALOG_ID,
        "selected_catalog_name": SELECTED_CATALOG_NAME,
        "request_headers_profile_sha256": headers_profile_sha,
        "attested_at_ms": 1700000000000,
        "status": "valid",
    }
    att_bytes = json.dumps(attestation).encode("utf-8")
    att_sha = hashlib.sha256(att_bytes).hexdigest()
    _write_artifact("source_profile_probe_attestation.json", att_bytes)

    contract = {
        "schema_version": "stage1_6b_capture_run_contract_v1",
        "run_id": run_id,
        "capture_mode": "historical_backfill",
        "source_profile_id": SOURCE_PROFILE_ID,
        "source_profile_attestation_sha256": att_sha,
        "run_started_at_ms": 1700000000000,
    }
    _write_artifact("capture_run_contract.json", json.dumps(contract).encode("utf-8"))

    checkpoint = {
        "schema_version": "stage1_6b_observer_checkpoint_v2",
        "run_id": run_id,
        "capture_mode": "historical_backfill",
        "source_profile_id": SOURCE_PROFILE_ID,
        "source_profile_attestation_sha256": att_sha,
        "checkpoint_id": "chk_final",
        "prior_checkpoint_id": None,
        "poll_seq": 1,
        "monotonic_request_seq": len(article_specs),
        "record_seq": len(article_specs),
        "accounted_root_bytes": 1000,
        "stream_offsets": {},
        "stream_last_hashes": {},
        "candidate_states": {},
        "heartbeat_at_ms": 1700000000000,
        "last_index_poll_status": "trusted",
        "last_index_poll_coverage": "successful",
    }
    _write_artifact("observer_checkpoint.json", json.dumps(checkpoint).encode("utf-8"))

    coverage = {
        "schema_version": "stage1_6b_historical_coverage_v2",
        "run_id": run_id,
        "capture_mode": "historical_backfill",
        "source_profile_id": SOURCE_PROFILE_ID,
        "status": "complete",
        "selected_catalog_id": SELECTED_CATALOG_ID,
        "selected_catalog_name": SELECTED_CATALOG_NAME,
        "selected_catalog_total_historical_max": len(article_specs),
        "selected_catalog_total_sweep_a_final": len(article_specs),
        "selected_catalog_total_sweep_b_final": len(article_specs),
        "sweep_a_page_count": 1,
        "sweep_b_page_count": 1,
        "sweep_a_transcript": [[1, SELECTED_CATALOG_ID, len(article_specs), raw_index_sha]],
        "sweep_b_transcript": [[1, SELECTED_CATALOG_ID, len(article_specs), raw_index_sha]],
        "sweep_a": {
            "reached_from_ms": True,
            "page_failures": [],
            "transcript_hash": "trans_hash_1",
        },
        "sweep_b": {
            "reached_from_ms": True,
            "page_failures": [],
            "transcript_hash": "trans_hash_1",
        },
        "frozen_candidate_count": len(article_specs),
        "candidate_terminal_count": len(article_specs),
        "pending_candidate_count": 0,
        "unattempted_candidate_count": 0,
        "final_checkpoint_valid": True,
        "from_ms": from_ms,
        "to_ms": to_ms,
    }
    cov_bytes = json.dumps(coverage).encode("utf-8")
    cov_sha = hashlib.sha256(cov_bytes).hexdigest()
    _write_artifact("historical_coverage.json", cov_bytes)

    terminal = {
        "schema_version": "stage1_6b_terminal_status_v1",
        "run_id": run_id,
        "capture_mode": "historical_backfill",
        "source_profile_id": SOURCE_PROFILE_ID,
        "status": "complete",
        "terminal_reason": "historical_backfill_complete",
        "final_checkpoint_id": "chk_final",
        "terminated_at_ms": 1700000001000,
    }
    term_bytes = json.dumps(terminal).encode("utf-8")
    term_sha = hashlib.sha256(term_bytes).hexdigest()
    _write_artifact("terminal_status.json", term_bytes)

    # 5. Manifest
    manifest = {
        "schema_version": "stage1_6b_sealed_export_v1",
        "export_id": export_id,
        "run_id": run_id,
        "capture_mode": "historical_backfill",
        "source_profile_id": SOURCE_PROFILE_ID,
        "status": "complete",
        "terminal_status_sha256": term_sha,
        "historical_coverage_sha256": cov_sha,
        "historical_range_from_ms": from_ms,
        "historical_range_to_ms": to_ms,
        "request_headers_profile_sha256": headers_profile_sha,
        "authoritative_artifacts": sorted(artifacts_meta, key=lambda a: (a["relative_path"], a["sha256"])),
        "sealed_at_ms": 1700000002000,
    }
    (export_dir / "sealed_export_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return project_root, export_dir


def rewrite_authoritative_artifact(export_dir: Path, relative_path: str, data: bytes) -> None:
    """Rewrite a file and update the manifest so that it passes load_sealed_export."""
    p = export_dir / relative_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)

    manifest_p = export_dir / "sealed_export_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    sha = hashlib.sha256(data).hexdigest()
    byte_count = len(data)

    found = False
    for art in manifest.get("authoritative_artifacts", []):
        if art["relative_path"] == relative_path:
            art["sha256"] = sha
            art["byte_count"] = byte_count
            found = True
            break
    if not found:
        manifest["authoritative_artifacts"].append({
            "relative_path": relative_path,
            "sha256": sha,
            "byte_count": byte_count,
        })
    manifest["authoritative_artifacts"] = sorted(manifest["authoritative_artifacts"], key=lambda a: (a["relative_path"], a["sha256"]))

    if relative_path == "terminal_status.json":
        manifest["terminal_status_sha256"] = sha
    elif relative_path == "historical_coverage.json":
        manifest["historical_coverage_sha256"] = sha

    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def make_mutated_export(project_root: Path, export_dir: Path, mutation: str) -> Path:
    """Create a mutated copy of export_dir that fails validation."""
    import shutil
    mutated_dir = export_dir.parent / f"{export_dir.name}_{mutation}"
    if mutated_dir.exists():
        shutil.rmtree(mutated_dir)
    shutil.copytree(export_dir, mutated_dir)

    manifest_p = mutated_dir / "sealed_export_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["export_id"] = mutated_dir.name

    if mutation == "malformed_control_json":
        (mutated_dir / "source_profile_probe_attestation.json").write_bytes(b"not json{")
        # Update manifest to pass load_sealed_export hash check, so adapter fails at control json parsing
        new_bytes = b"not json{"
        for art in manifest["authoritative_artifacts"]:
            if art["relative_path"] == "source_profile_probe_attestation.json":
                art["sha256"] = hashlib.sha256(new_bytes).hexdigest()
                art["byte_count"] = len(new_bytes)
        manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    elif mutation == "missing_request_observation_id":
        obs_p = mutated_dir / "detail_observations/historical.jsonl"
        lines = [json.loads(x) for x in obs_p.read_text(encoding="utf-8").splitlines() if x.strip()]
        for line in lines:
            line.pop("request_observation_id", None)
        new_data = ("\n".join(json.dumps(x) for x in lines) + "\n").encode("utf-8")
        obs_p.write_bytes(new_data)
        for art in manifest["authoritative_artifacts"]:
            if art["relative_path"] == "detail_observations/historical.jsonl":
                art["sha256"] = hashlib.sha256(new_data).hexdigest()
                art["byte_count"] = len(new_data)
        manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    elif mutation == "duplicate_request_observation_id":
        obs_p = mutated_dir / "detail_observations/historical.jsonl"
        lines = [json.loads(x) for x in obs_p.read_text(encoding="utf-8").splitlines() if x.strip()]
        if lines:
            lines.append(dict(lines[0]))  # duplicate
        new_data = ("\n".join(json.dumps(x) for x in lines) + "\n").encode("utf-8")
        obs_p.write_bytes(new_data)
        for art in manifest["authoritative_artifacts"]:
            if art["relative_path"] == "detail_observations/historical.jsonl":
                art["sha256"] = hashlib.sha256(new_data).hexdigest()
                art["byte_count"] = len(new_data)
        manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    elif mutation == "foreign_source_article_id":
        ad_p = mutated_dir / "article_discoveries.jsonl"
        lines = [json.loads(x) for x in ad_p.read_text(encoding="utf-8").splitlines() if x.strip()]
        if lines:
            lines[0]["source_article_id"] = "f" * 32
        new_data = ("\n".join(json.dumps(x) for x in lines) + "\n").encode("utf-8")
        ad_p.write_bytes(new_data)
        for art in manifest["authoritative_artifacts"]:
            if art["relative_path"] == "article_discoveries.jsonl":
                art["sha256"] = hashlib.sha256(new_data).hexdigest()
                art["byte_count"] = len(new_data)
        manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return mutated_dir
