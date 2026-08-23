"""Stage 1.6A sealed-export historical source-audit adapter."""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import src.research.external_signal_shadow.stage1_6b_canonical_source_storage as storage

SOURCE_PROFILE_ID = "binance_public_web_bapi_en_delisting_catalog_v2"
SELECTED_CATALOG_ID = 161
SELECTED_CATALOG_NAME = "Delisting"

SCHEMA_VERSION_CANDIDATE_MANIFEST = "stage1_6a_adapter_candidate_manifest_v1"
SCHEMA_VERSION_SEMANTIC_EXTRACTION = "stage1_6a_adapter_semantic_extraction_v1"
SCHEMA_VERSION_DELISTING_NOTICE = "stage1_6a_adapter_delisting_notice_v1"
SCHEMA_VERSION_DELISTING_CONTRACT = "stage1_6a_adapter_delisting_contract_v1"
SCHEMA_VERSION_PARENT_OUTCOME = "stage1_6a_parent_audit_outcome_v1"
ARTIFACT_PROFILE_VERSION = "stage1_6a_sealed_export_source_audit_v2"

BODY_NORMALIZATION_VERSION = "stage1_6a_bapi_body_tree_v1"
SEMANTIC_EXTRACTOR_VERSION = "stage1_6a_extractor_v1"
CANDIDATE_DISCOVERY_RULE_VERSION = "candidate_discovery_rule_v1"
AUDIT_METRIC_DEFINITION_VERSION = "stage1_6a_audit_metric_v1"

ALLOWED_TAGS = {"a", "br", "em", "h3", "h4", "li", "p", "span", "strong", "table", "tbody", "td", "tr", "u", "ul"}
BLOCK_TAGS = {"p", "h3", "h4", "li", "tr", "td"}
UTC_DT_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")


class AdapterInputError(ValueError):
    """Raised when an input export violates structural, integrity, or linkage invariants."""
    pass


@dataclass(frozen=True)
class VerifiedSourceSnapshot:
    project_root: Path
    export_id: str
    manifest: Dict[str, Any]
    manifest_bytes: bytes
    artifact_bytes: Dict[str, bytes]
    control_records: Dict[str, Dict[str, Any]]
    list_captures: Tuple[Dict[str, Any], ...]
    discoveries: Tuple[Dict[str, Any], ...]
    observations: Tuple[Dict[str, Any], ...]
    revisions: Tuple[Dict[str, Any], ...]
    raw_payload_bytes: Dict[str, bytes]


@dataclass(frozen=True)
class AdapterReduction:
    candidate_manifest: Dict[str, Any]
    parent_outcomes: Tuple[Dict[str, Any], ...]
    detail_revision_projection: Tuple[Dict[str, Any], ...]
    semantic_extractions: Tuple[Dict[str, Any], ...]
    notices: Tuple[Dict[str, Any], ...]
    contracts: Tuple[Dict[str, Any], ...]
    diagnostics: Tuple[Dict[str, Any], ...]


def parse_utc_timestamp_ms(dt_str: str) -> Optional[int]:
    cleaned = dt_str.strip()
    for fmt in UTC_DT_FORMATS:
        try:
            dt = datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def parse_and_normalize_bapi_body(
    raw_payload: bytes,
    *,
    article_id: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parses a trusted BAPI raw payload, validates BAPI envelope grammar, and normalizes body tree.
    Returns (result_dict, None) on success, or (None, error_status) on payload quality failure.
    Raises AdapterInputError on present string data.code mismatch.
    """
    try:
        envelope = json.loads(raw_payload.decode("utf-8"))
    except Exception:
        return None, "malformed_bapi_envelope"

    if not isinstance(envelope, dict):
        return None, "malformed_bapi_envelope"

    data = envelope.get("data")
    if not isinstance(data, dict):
        return None, "malformed_bapi_envelope"

    data_code = data.get("code")
    if not isinstance(data_code, str):
        return None, "malformed_bapi_envelope"

    if data_code != article_id:
        raise AdapterInputError(f"data_code_article_id_mismatch: {data_code} != {article_id}")

    data_title = data.get("title")
    if not isinstance(data_title, str) or not data_title.strip():
        return None, "malformed_bapi_envelope"

    data_body_str = data.get("body")
    if not isinstance(data_body_str, str):
        return None, "malformed_bapi_envelope"

    # Numeric id is diagnostic only
    raw_numeric_id = data.get("id")
    bapi_numeric_id = raw_numeric_id if (type(raw_numeric_id) is int and not isinstance(raw_numeric_id, bool)) else None

    # Parse publishDate
    raw_pub_date = data.get("publishDate")
    publish_date_valid = (
        type(raw_pub_date) is int
        and not isinstance(raw_pub_date, bool)
        and 1_000_000_000_000 <= raw_pub_date < 10_000_000_000_000
    )
    publish_date = raw_pub_date if publish_date_valid else None

    # Parse body tree
    try:
        body_tree = json.loads(data_body_str)
    except Exception:
        return None, "body_parse_unresolved"

    if not isinstance(body_tree, dict):
        return None, "body_parse_unresolved"

    tokens: List[str] = []

    def _traverse(node: Any) -> bool:
        if not isinstance(node, dict):
            return False
        node_kind = node.get("node")
        if node_kind == "root":
            if set(node.keys()) != {"node", "child"} or not isinstance(node.get("child"), list):
                return False
            for c in node["child"]:
                if not _traverse(c):
                    return False
            return True
        elif node_kind == "element":
            keys = set(node.keys())
            if not keys.issubset({"node", "tag", "attr", "child"}):
                return False
            tag = node.get("tag")
            if tag not in ALLOWED_TAGS:
                return False
            attr = node.get("attr")
            if attr is not None and not isinstance(attr, dict):
                return False
            child = node.get("child")
            if child is not None and not isinstance(child, list):
                return False

            if tag == "br":
                if child:
                    return False
                tokens.append("\n")
                return True

            is_block = tag in BLOCK_TAGS
            if is_block:
                tokens.append("\n")
            if child:
                for c in child:
                    if not _traverse(c):
                        return False
            if is_block:
                tokens.append("\n")
            return True
        elif node_kind == "text":
            if set(node.keys()) != {"node", "text"} or not isinstance(node.get("text"), str):
                return False
            tokens.append(node["text"])
            return True
        else:
            return False

    if not _traverse(body_tree):
        return None, "body_parse_unresolved"

    raw_text = "".join(tokens)
    # Normalization steps
    t = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[ \t\f\v]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n+", "\n", t)
    normalized_body = t.strip(" \n")

    return ({
        "source_article_id": article_id,
        "bapi_numeric_id": bapi_numeric_id,
        "title": data_title,
        "normalized_body": normalized_body,
        "normalized_body_sha256": hashlib.sha256(normalized_body.encode("utf-8")).hexdigest(),
        "publish_date": publish_date,
        "publish_date_valid": publish_date_valid,
    }, None)


def _build_snapshot_from_retained_bytes(
    project_root: Path,
    export_dir: Path,
    manifest: Dict[str, Any],
    manifest_bytes: bytes,
) -> VerifiedSourceSnapshot:
    export_id = manifest.get("export_id", "")
    if not export_id or export_dir.name != export_id:
        raise AdapterInputError(f"export_id_mismatch: {export_dir.name} != {export_id}")

    if manifest.get("status") != "complete":
        raise AdapterInputError("export_status_not_complete")

    if manifest.get("capture_mode") != "historical_backfill":
        raise AdapterInputError("capture_mode_not_historical_backfill")

    if manifest.get("source_profile_id") != SOURCE_PROFILE_ID:
        raise AdapterInputError(f"export_profile_mismatch: {manifest.get('source_profile_id')} != {SOURCE_PROFILE_ID}")

    artifacts = manifest.get("authoritative_artifacts", [])
    if not artifacts:
        raise AdapterInputError("export_has_zero_artifacts")

    artifact_bytes: Dict[str, bytes] = {}

    for art in artifacts:
        rel_p = art.get("relative_path", "")
        expected_sha = art.get("sha256", "")
        expected_size = art.get("byte_count", 0)

        file_p = export_dir / rel_p
        if not file_p.is_file():
            raise AdapterInputError(f"missing_authoritative_artifact: {rel_p}")

        data = file_p.read_bytes()
        if len(data) != expected_size:
            raise AdapterInputError(f"artifact_size_mismatch: {rel_p}")

        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != expected_sha:
            raise AdapterInputError(f"artifact_hash_mismatch: {rel_p}")

        artifact_bytes[rel_p] = data

    control_records: Dict[str, Dict[str, Any]] = {}
    required_controls = {
        "capture_run_contract.json": "stage1_6b_capture_run_contract_v1",
        "source_profile_probe_attestation.json": "stage1_6b_source_profile_probe_attestation_v2",
        "observer_checkpoint.json": "stage1_6b_observer_checkpoint_v2",
        "historical_coverage.json": "stage1_6b_historical_coverage_v2",
        "terminal_status.json": "stage1_6b_terminal_status_v1",
    }

    for rel_p, expected_schema in required_controls.items():
        if rel_p not in artifact_bytes:
            raise AdapterInputError(f"missing_required_control_artifact: {rel_p}")
        try:
            parsed = json.loads(artifact_bytes[rel_p].decode("utf-8"))
        except Exception as exc:
            raise AdapterInputError(f"malformed_control_json:{rel_p}:{exc}") from exc

        if not isinstance(parsed, dict) or parsed.get("schema_version") != expected_schema:
            raise AdapterInputError(f"invalid_control_schema:{rel_p}")
        if parsed.get("source_profile_id") != SOURCE_PROFILE_ID:
            raise AdapterInputError(f"control_profile_mismatch:{rel_p}")
        control_records[rel_p] = parsed

    contract = control_records["capture_run_contract.json"]
    attestation = control_records["source_profile_probe_attestation.json"]
    terminal = control_records["terminal_status.json"]
    coverage = control_records["historical_coverage.json"]

    if attestation.get("selected_catalog_id") != SELECTED_CATALOG_ID or attestation.get("selected_catalog_name") != SELECTED_CATALOG_NAME:
        raise AdapterInputError("attestation_catalog_mismatch")

    expected_headers_sha = manifest.get("request_headers_profile_sha256")
    if attestation.get("request_headers_profile_sha256") != expected_headers_sha:
        raise AdapterInputError("attestation_headers_profile_mismatch")

    contract_run_id = contract.get("run_id")
    if not contract_run_id or terminal.get("run_id") != contract_run_id or coverage.get("run_id") != contract_run_id:
        raise AdapterInputError("control_run_id_mismatch")

    if terminal.get("status") != "complete" or terminal.get("terminal_reason") != "historical_backfill_complete":
        raise AdapterInputError("terminal_status_not_historical_complete")

    if "reason" in terminal:
        raise AdapterInputError("terminal_status_contains_legacy_reason_field")

    list_captures: List[Dict[str, Any]] = []
    for rel_p, raw_data in artifact_bytes.items():
        if rel_p.startswith("list_captures/") and rel_p.endswith(".jsonl"):
            for line in raw_data.decode("utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("schema_version") != "stage1_6b_list_capture_v2":
                    raise AdapterInputError("list_capture_schema_invalid")
                if row.get("source_profile_id") != SOURCE_PROFILE_ID:
                    raise AdapterInputError("list_capture_profile_mismatch")
                if row.get("selected_catalog_id") != SELECTED_CATALOG_ID or row.get("selected_catalog_name") != SELECTED_CATALOG_NAME:
                    raise AdapterInputError("list_capture_catalog_mismatch")
                list_captures.append(row)

    if "article_discoveries.jsonl" not in artifact_bytes:
        raise AdapterInputError("missing_article_discoveries")

    discoveries: List[Dict[str, Any]] = []
    for line in artifact_bytes["article_discoveries.jsonl"].decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema_version") != "stage1_6b_article_discovery_v2":
            raise AdapterInputError("article_discovery_schema_invalid")
        if row.get("source_profile_id") != SOURCE_PROFILE_ID:
            raise AdapterInputError("article_discovery_profile_mismatch")
        if row.get("source_catalog_id") != SELECTED_CATALOG_ID or row.get("source_catalog_name") != SELECTED_CATALOG_NAME:
            raise AdapterInputError("article_discovery_catalog_mismatch")
        discoveries.append(row)

    if not discoveries:
        raise AdapterInputError("article_discoveries_empty")

    discovery_article_ids: Set[str] = {r.get("source_article_id", "") for r in discoveries}
    if "" in discovery_article_ids:
        raise AdapterInputError("empty_source_article_id_in_discovery")

    if "detail_observations/historical.jsonl" not in artifact_bytes:
        raise AdapterInputError("missing_detail_observations")

    observations: List[Dict[str, Any]] = []
    seen_obs_ids: Set[str] = set()
    for line in artifact_bytes["detail_observations/historical.jsonl"].decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema_version") != "stage1_6b_detail_observation_v1":
            raise AdapterInputError("detail_observation_schema_invalid")
        if row.get("source_profile_id") != SOURCE_PROFILE_ID:
            raise AdapterInputError("detail_observation_profile_mismatch")

        obs_id = row.get("request_observation_id")
        if not isinstance(obs_id, str) or not obs_id:
            raise AdapterInputError("missing_or_invalid_request_observation_id")
        if obs_id in seen_obs_ids:
            raise AdapterInputError(f"duplicate_request_observation_id: {obs_id}")
        seen_obs_ids.add(obs_id)

        if row.get("request_headers_profile_sha256") != expected_headers_sha:
            raise AdapterInputError("observation_headers_profile_mismatch")

        aid = row.get("source_article_id")
        if not aid or aid not in discovery_article_ids:
            raise AdapterInputError(f"foreign_source_article_id_in_observation: {aid}")

        observations.append(row)

    revisions: List[Dict[str, Any]] = []
    if "detail_revisions.jsonl" in artifact_bytes:
        for line in artifact_bytes["detail_revisions.jsonl"].decode("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("schema_version") != "stage1_6b_detail_revision_v1":
                raise AdapterInputError("detail_revision_schema_invalid")
            if row.get("source_profile_id") != SOURCE_PROFILE_ID:
                raise AdapterInputError("detail_revision_profile_mismatch")
            if row.get("source_locale") != "en" or row.get("source_surface") != "announcement_detail" or row.get("request_variant") != "bapi_article_detail_query_v1":
                raise AdapterInputError("detail_revision_provenance_invalid")
            aid = row.get("source_article_id")
            if not aid or aid not in discovery_article_ids:
                raise AdapterInputError(f"foreign_source_article_id_in_revision: {aid}")
            revisions.append(row)

    raw_payload_bytes: Dict[str, bytes] = {}
    for rel_p, data in artifact_bytes.items():
        if rel_p.startswith("raw_payloads/detail/") or rel_p.startswith("raw_payloads/details/"):
            raw_payload_bytes[rel_p] = data

    return VerifiedSourceSnapshot(
        project_root=project_root,
        export_id=export_id,
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        artifact_bytes=artifact_bytes,
        control_records=control_records,
        list_captures=tuple(list_captures),
        discoveries=tuple(discoveries),
        observations=tuple(observations),
        revisions=tuple(revisions),
        raw_payload_bytes=raw_payload_bytes,
    )


def load_verified_source_snapshot(project_root: Path, export_dir: Path) -> VerifiedSourceSnapshot:
    """Load and verify a Stage 1.6B sealed export into an immutable in-memory snapshot."""
    try:
        root = project_root.resolve(strict=True)
        source = export_dir.resolve(strict=True)
        allowed = (root / "data" / "external_signal_shadow" / "stage1_6b" / "historical_backfill").resolve(strict=True)
        if not source.is_relative_to(allowed):
            raise AdapterInputError("source_export_path_outside_historical_backfill")

        manifest = storage.load_sealed_export(source)
        manifest_bytes = (source / "sealed_export_manifest.json").read_bytes()
        if json.loads(manifest_bytes.decode("utf-8")) != manifest:
            raise AdapterInputError("sealed_export_manifest_changed_during_snapshot")
        return _build_snapshot_from_retained_bytes(root, source, manifest, manifest_bytes)
    except AdapterInputError:
        raise
    except Exception as exc:
        raise AdapterInputError(f"source_snapshot_invalid:{exc}") from exc


def _make_schedule_fact(
    status: str,
    ts_ms: Optional[int] = None,
    order_restriction_type: Optional[str] = None,
    revision_id: Optional[str] = None,
    extraction_id: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "fact_parse_status": status,
        "capture_time_status": "historical_unknown",
        "timestamp_ms": ts_ms,
        "order_restriction_type": order_restriction_type,
        "source_detail_revision_id": revision_id,
        "source_semantic_extraction_id": extraction_id,
        "fact_available_at_ms": None,
        "evidence": evidence,
    }


def _parent_outcome(
    *,
    source_article_id: str,
    detail_authority_status: str,
    selected_detail_revision_id: Optional[str],
    source_integrity_parent_pass: bool,
    source_published_at_ms: Optional[int],
    publication_time_status: str,
    parent_declaration_status: str,
    mapping_status: str,
    classification_status: str,
    eligible_child_count: int,
    semantic_extracted_at_ms: Optional[int],
    diagnostic_codes: List[str],
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION_PARENT_OUTCOME,
        "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
        "source_article_id": source_article_id,
        "capture_mode": "historical_backfill",
        "semantic_extracted_at_ms": semantic_extracted_at_ms,
        "notice_lineage_first_detected_at_ms": None,
        "system_available_at_ms": None,
        "fact_available_at_ms": None,
        "capture_time_status": "historical_unknown",
        "point_in_time_replay_eligible": False,
        "risk_veto_candidate": False,
        "detail_authority_status": detail_authority_status,
        "selected_detail_revision_id": selected_detail_revision_id,
        "source_integrity_parent_pass": source_integrity_parent_pass,
        "source_published_at_ms": source_published_at_ms,
        "publication_time_status": publication_time_status,
        "parent_declaration_status": parent_declaration_status,
        "mapping_status": mapping_status,
        "classification_status": classification_status,
        "eligible_child_count": eligible_child_count,
        "diagnostic_codes": sorted(set(diagnostic_codes)),
    }


def reduce_verified_snapshot(
    snapshot: VerifiedSourceSnapshot,
    *,
    semantic_extracted_at_ms: int,
) -> AdapterReduction:
    """Core reducer that projects verified sealed export into exact Stage 1.6A adapter artifacts."""
    sorted_discoveries = sorted(snapshot.discoveries, key=lambda r: r["source_article_id"])

    # 1. Candidate manifest
    manifest_id = hashlib.sha256(
        f"{snapshot.export_id}|{CANDIDATE_DISCOVERY_RULE_VERSION}|{len(sorted_discoveries)}".encode("utf-8")
    ).hexdigest()

    manifest_candidates = []
    for d in sorted_discoveries:
        manifest_candidates.append({
            "source_article_id": d["source_article_id"],
            "discovery_title": d["discovery_title"],
            "first_list_capture_id": d["first_list_capture_id"],
            "source_catalog_id": SELECTED_CATALOG_ID,
            "source_catalog_name": SELECTED_CATALOG_NAME,
            "notice_lineage_first_detected_at_ms": None,
        })

    candidate_manifest_dict = {
        "schema_version": SCHEMA_VERSION_CANDIDATE_MANIFEST,
        "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
        "capture_mode": "historical_backfill",
        "input_export_id": snapshot.export_id,
        "input_manifest_sha256": hashlib.sha256(snapshot.manifest_bytes).hexdigest(),
        "candidate_discovery_rule_version": CANDIDATE_DISCOVERY_RULE_VERSION,
        "manifest_id": manifest_id,
        "candidates": manifest_candidates,
    }

    # 2. Build list capture & raw index release date mapping
    lc_by_id: Dict[str, Dict[str, Any]] = {}
    for lc in snapshot.list_captures:
        cid = lc.get("list_capture_id") or lc.get("first_list_capture_id")
        if cid:
            lc_by_id[cid] = lc
    catalog_release_dates: Dict[str, int] = {}

    for d in sorted_discoveries:
        aid = d["source_article_id"]
        lc_id = d.get("first_list_capture_id")
        if not lc_id or lc_id not in lc_by_id:
            raise AdapterInputError(f"candidate_first_list_capture_missing: {aid}")

        lc = lc_by_id[lc_id]
        raw_rel = lc.get("raw_payload_relative_path")
        if not raw_rel or raw_rel not in snapshot.artifact_bytes:
            raw_sha = lc.get("raw_sha") or lc.get("raw_payload_sha256", "")
            raw_rel = f"raw_payloads/index/{raw_sha}.bin"
            if raw_rel not in snapshot.artifact_bytes:
                raw_rel = f"raw_payloads/indices/{raw_sha[:2]}/{raw_sha}.json"
        if raw_rel not in snapshot.artifact_bytes:
            raise AdapterInputError(f"missing_raw_index_payload: {raw_rel}")

        try:
            raw_index = json.loads(snapshot.artifact_bytes[raw_rel].decode("utf-8"))
            catalogs = raw_index.get("data", {}).get("catalogs", [])
            delist_catalog = next((c for c in catalogs if c.get("catalogId") == SELECTED_CATALOG_ID or c.get("catalogName") == SELECTED_CATALOG_NAME), None)
            if delist_catalog:
                articles = delist_catalog.get("articles", [])
            else:
                articles = []
                for c in catalogs:
                    articles.extend(c.get("articles", []))
            article_entry = next((a for a in articles if a.get("code") == aid), None)
            if not article_entry:
                raise AdapterInputError(f"candidate_missing_in_raw_catalog: {aid}")
            rel_date = article_entry.get("releaseDate")
            if not (type(rel_date) is int and not isinstance(rel_date, bool) and 1_000_000_000_000 <= rel_date < 10_000_000_000_000):
                raise AdapterInputError(f"invalid_catalog_release_date: {aid}")
            catalog_release_dates[aid] = rel_date
        except Exception as exc:
            if isinstance(exc, AdapterInputError):
                raise
            raise AdapterInputError(f"raw_index_parse_error:{aid}:{exc}") from exc

    # 3. Index observations and revisions by article
    obs_by_article: Dict[str, List[Dict[str, Any]]] = {}
    for obs in snapshot.observations:
        obs_by_article.setdefault(obs["source_article_id"], []).append(obs)

    rev_by_article: Dict[str, List[Dict[str, Any]]] = {}
    for rev in snapshot.revisions:
        rev_by_article.setdefault(rev["source_article_id"], []).append(rev)

    # Validate bidirectional linkage between trusted observations and revisions
    for aid, obs_list in obs_by_article.items():
        trusted_obs = [o for o in obs_list if o.get("trust_validation_status") == "trusted"]
        rev_list = rev_by_article.get(aid, [])
        if trusted_obs and not rev_list:
            raise AdapterInputError(f"trusted_observation_missing_revisions: {aid}")

        for o in trusted_obs:
            raw_sha = o.get("raw_payload_sha256")
            if not raw_sha:
                raise AdapterInputError(f"trusted_observation_missing_raw_sha: {aid}")
            matching_rev = next((r for r in rev_list if r.get("detail_raw_sha256") == raw_sha), None)
            if not matching_rev:
                raise AdapterInputError(f"trusted_observation_unmatched_revision: {aid}:{raw_sha}")
            raw_rel = matching_rev.get("raw_payload_relative_path", "")
            if raw_rel not in snapshot.raw_payload_bytes:
                raise AdapterInputError(f"missing_raw_detail_payload: {raw_rel}")

    for aid, rev_list in rev_by_article.items():
        obs_list = obs_by_article.get(aid, [])
        for r in rev_list:
            raw_sha = r.get("detail_raw_sha256")
            matching_obs = next((o for o in obs_list if o.get("trust_validation_status") == "trusted" and o.get("raw_payload_sha256") == raw_sha), None)
            if not matching_obs:
                raise AdapterInputError(f"orphan_revision_without_trusted_observation: {aid}:{raw_sha}")

    parent_outcomes = []
    detail_revision_projections = []
    semantic_extractions = []
    notices = []
    contracts = []
    diagnostics = []

    for d in sorted_discoveries:
        aid = d["source_article_id"]
        obs_list = obs_by_article.get(aid, [])
        if not obs_list:
            raise AdapterInputError(f"zero_observations_for_candidate: {aid}")

        trusted_obs = [o for o in obs_list if o.get("trust_validation_status") == "trusted"]
        rev_list = rev_by_article.get(aid, [])

        if not trusted_obs or not rev_list:
            # Denominator-visible detail unavailable
            parent_outcomes.append(_parent_outcome(
                source_article_id=aid, detail_authority_status="detail_unavailable",
                selected_detail_revision_id=None, source_integrity_parent_pass=False,
                source_published_at_ms=None, publication_time_status="not_evaluable",
                parent_declaration_status="not_evaluable", mapping_status="not_evaluable",
                classification_status="not_evaluable", eligible_child_count=0,
                semantic_extracted_at_ms=None, diagnostic_codes=["detail_unavailable"],
            ))
            notices.append({
                "schema_version": SCHEMA_VERSION_DELISTING_NOTICE,
                "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
                "source_article_id": aid,
                "detail_revision_id": None,
                "semantic_extraction_id": None,
                "source_detail_title": None,
                "source_published_at_ms": None,
                "publication_time_status": "unparseable",
                "parent_declaration_status": "incomplete",
                "source_audit_eligible": False,
                "declared_child_count": 0,
                "eligible_child_count": 0,
                "capture_mode": "historical_backfill",
                "semantic_extracted_at_ms": None,
                "notice_lineage_first_detected_at_ms": None,
                "system_available_at_ms": None,
                "fact_available_at_ms": None,
                "capture_time_status": "historical_unknown",
                "point_in_time_replay_eligible": False,
                "risk_veto_candidate": False,
            })
            continue

        # Select deterministic revision by max(t_detail_trusted_ms, detail_raw_sha256)
        selected_rev = max(rev_list, key=lambda r: (r.get("t_detail_trusted_ms", 0), r.get("detail_raw_sha256", "")))
        selected_rev_id = selected_rev["detail_revision_id"]
        for r in sorted(rev_list, key=lambda x: (x["source_article_id"], x["detail_revision_id"])):
            raw_data = snapshot.raw_payload_bytes[r["raw_payload_relative_path"]]
            try:
                bapi_numeric_id = json.loads(raw_data.decode("utf-8")).get("data", {}).get("id")
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                bapi_numeric_id = None
            detail_revision_projections.append({
                "schema_version": "stage1_6a_detail_revision_projection_v1",
                "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
                "source_article_id": aid,
                "detail_revision_id": r["detail_revision_id"],
                "detail_raw_sha256": r["detail_raw_sha256"],
                "raw_payload_relative_path": r["raw_payload_relative_path"],
                "t_detail_trusted_ms": r["t_detail_trusted_ms"],
                "source_surface": r["source_surface"],
                "source_locale": r["source_locale"],
                "request_variant": r["request_variant"],
                "bapi_numeric_id": bapi_numeric_id,
                "detail_authority_status": "trusted",
                "selected_for_parent": r["detail_revision_id"] == selected_rev_id,
            })
        raw_rel = selected_rev["raw_payload_relative_path"]
        raw_bytes = snapshot.raw_payload_bytes[raw_rel]

        parsed_bapi, parse_err = parse_and_normalize_bapi_body(raw_bytes, article_id=aid)

        if parse_err:
            parent_outcomes.append(_parent_outcome(
                source_article_id=aid, detail_authority_status=parse_err,
                selected_detail_revision_id=selected_rev_id, source_integrity_parent_pass=False,
                source_published_at_ms=None, publication_time_status="not_evaluable",
                parent_declaration_status="not_evaluable", mapping_status="not_evaluable",
                classification_status="not_evaluable", eligible_child_count=0,
                semantic_extracted_at_ms=None, diagnostic_codes=[parse_err],
            ))
            notices.append({
                "schema_version": SCHEMA_VERSION_DELISTING_NOTICE,
                "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
                "source_article_id": aid,
                "detail_revision_id": None,
                "semantic_extraction_id": None,
                "source_detail_title": None,
                "source_published_at_ms": None,
                "publication_time_status": "unparseable",
                "parent_declaration_status": "incomplete",
                "source_audit_eligible": False,
                "declared_child_count": 0,
                "eligible_child_count": 0,
                "capture_mode": "historical_backfill",
                "semantic_extracted_at_ms": None,
                "notice_lineage_first_detected_at_ms": None,
                "system_available_at_ms": None,
                "fact_available_at_ms": None,
                "capture_time_status": "historical_unknown",
                "point_in_time_replay_eligible": False,
                "risk_veto_candidate": False,
            })
            continue

        # Check publication time against catalog
        cat_rel_date = catalog_release_dates.get(aid)
        bapi_pub_date = parsed_bapi["publish_date"]
        if not parsed_bapi["publish_date_valid"]:
            pub_status = "unparseable"
            pub_pass = False
        elif bapi_pub_date != cat_rel_date:
            pub_status = "conflicting"
            pub_pass = False
        else:
            pub_status = "present"
            pub_pass = True

        norm_body = parsed_bapi["normalized_body"]
        norm_body_sha = parsed_bapi["normalized_body_sha256"]

        # Parse schedule facts from body
        settle_match = re.search(r"(?:conduct automatic settlement|automatic settlement|close all positions and delist|will delist)[^\n\.\;]*?at\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*\(UTC\)", norm_body, re.IGNORECASE)
        settle_ts = parse_utc_timestamp_ms(settle_match.group(1)) if settle_match else None

        # Check multi-revision semantic conflict
        is_revision_conflicting = False
        if len(rev_list) > 1:
            for other_rev in rev_list:
                if other_rev["detail_revision_id"] == selected_rev_id:
                    continue
                other_rel = other_rev["raw_payload_relative_path"]
                other_parsed, other_err = parse_and_normalize_bapi_body(snapshot.raw_payload_bytes[other_rel], article_id=aid)
                if other_parsed:
                    other_match = re.search(r"(?:conduct automatic settlement|automatic settlement|close all positions and delist|will delist)[^\n\.\;]*?at\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*\(UTC\)", other_parsed["normalized_body"], re.IGNORECASE)
                    other_settle_ts = parse_utc_timestamp_ms(other_match.group(1)) if other_match else None
                    if settle_ts != other_settle_ts:
                        is_revision_conflicting = True

        # Semantic extraction ID
        fact_fingerprint_seed = f"{selected_rev_id}|{settle_ts}|{bapi_pub_date}"
        fact_fingerprint = hashlib.sha256(fact_fingerprint_seed.encode("utf-8")).hexdigest()
        semantic_extraction_id = hashlib.sha256(
            f"{selected_rev_id}|{SEMANTIC_EXTRACTOR_VERSION}|{BODY_NORMALIZATION_VERSION}|{fact_fingerprint}".encode("utf-8")
        ).hexdigest()

        # Semantic extraction row
        semantic_extractions.append({
            "schema_version": SCHEMA_VERSION_SEMANTIC_EXTRACTION,
            "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
            "source_article_id": aid,
            "detail_revision_id": selected_rev_id,
            "semantic_extraction_id": semantic_extraction_id,
            "semantic_extractor_version": SEMANTIC_EXTRACTOR_VERSION,
            "body_normalization_version": BODY_NORMALIZATION_VERSION,
            "canonical_fact_fingerprint": fact_fingerprint,
            "normalized_body_sha256": norm_body_sha,
            "semantic_extracted_at_ms": semantic_extracted_at_ms,
            "capture_mode": "historical_backfill",
            "system_available_at_ms": None,
            "fact_available_at_ms": None,
            "capture_time_status": "historical_unknown",
            "point_in_time_replay_eligible": False,
            "risk_veto_candidate": False,
        })

        # Extract symbols and contracts
        # Look for perpetual contract declarations
        symbol_candidates = re.findall(r"(?:USDⓈ-M|USDT-M|USDC-M|COIN-M)?\s*([A-Z0-9_]+)\s*(?:Perpetual|Delivery|Contract)", norm_body)
        if not symbol_candidates:
            # Check standalone symbols in title or body
            direct_syms = re.findall(r"\b([A-Z0-9]{2,10}(?:USDT|USDC|USD))\b", norm_body + " " + parsed_bapi["title"])
            symbol_candidates = direct_syms

        # Deduplicate symbols preserving order
        seen_syms = set()
        declared_symbols = []
        for s in symbol_candidates:
            s_clean = s.strip().upper()
            if s_clean not in seen_syms and len(s_clean) >= 3 and s_clean not in {"THE", "ALL", "AND", "PERPETUAL", "FUTURES", "CONTRACT"}:
                seen_syms.add(s_clean)
                declared_symbols.append(s_clean)

        # Check for unknown batch tokens or malformed child declarations
        has_unresolved_batch = "UNKNOWN_BATCH_TOKEN" in norm_body or not declared_symbols

        child_contracts = []
        all_children_valid = not has_unresolved_batch

        for sym in declared_symbols:
            margin_family = "unknown"
            contract_type = "unknown"
            underlying_family = "unknown"
            settlement_asset = None
            quote_asset = None
            is_in_scope = False

            if sym.endswith("USDT") or sym.endswith("USDC"):
                margin_family = "USD_M"
                contract_type = "PERPETUAL"
                underlying_family = "crypto_asset"
                # Proof of asset in body
                if "USDT" in norm_body and sym.endswith("USDT"):
                    settlement_asset = "USDT"
                    quote_asset = "USDT"
                elif "USDC" in norm_body and sym.endswith("USDC"):
                    settlement_asset = "USDC"
                    quote_asset = "USDC"
                is_in_scope = True
            elif "USD" in sym:
                margin_family = "COIN_M"
                contract_type = "PERPETUAL"
                underlying_family = "crypto_asset"
                is_in_scope = False

            contract_id = hashlib.sha256(
                f"{aid}|{selected_rev_id}|{sym}|{margin_family}|{contract_type}|{underlying_family}".encode("utf-8")
            ).hexdigest()

            # Schedule fact evidence
            settle_ev = None
            if settle_match:
                settle_ev = {
                    "detail_revision_id": selected_rev_id,
                    "detail_raw_sha256": selected_rev["detail_raw_sha256"],
                    "semantic_extraction_id": semantic_extraction_id,
                    "semantic_extractor_version": SEMANTIC_EXTRACTOR_VERSION,
                    "body_normalization_version": BODY_NORMALIZATION_VERSION,
                    "location_kind": "normalized_text_span",
                    "location_value": settle_match.group(0),
                    "normalized_body_utf8_byte_start": len(norm_body[:settle_match.start()].encode("utf-8")),
                    "normalized_body_utf8_byte_end": len(norm_body[:settle_match.end()].encode("utf-8")),
                    "excerpt": settle_match.group(0),
                }

            settle_fact = _make_schedule_fact(
                status="present" if settle_ts else "not_stated",
                ts_ms=settle_ts,
                revision_id=selected_rev_id if settle_ts else None,
                extraction_id=semantic_extraction_id if settle_ts else None,
                evidence=settle_ev,
            )
            order_restr_fact = _make_schedule_fact(status="not_stated")
            last_trading_fact = _make_schedule_fact(status="not_stated")
            delist_complete_fact = _make_schedule_fact(status="not_stated")

            child_eligible = (
                is_in_scope
                and settlement_asset is not None
                and not has_unresolved_batch
                and not is_revision_conflicting
            )

            contract_rec = {
                "schema_version": SCHEMA_VERSION_DELISTING_CONTRACT,
                "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
                "contract_id": contract_id,
                "parent_article_id": aid,
                "detail_revision_id": selected_rev_id,
                "semantic_extraction_id": semantic_extraction_id,
                "canonical_symbol": sym,
                "settlement_asset": settlement_asset,
                "quote_asset": quote_asset,
                "margin_family": margin_family,
                "contract_type": contract_type,
                "underlying_family": underlying_family,
                "is_in_scope": is_in_scope,
                "source_audit_eligible": child_eligible,
                "settlement_time": settle_fact,
                "order_restriction": order_restr_fact,
                "last_trading_time": last_trading_fact,
                "delisting_complete_time": delist_complete_fact,
                "capture_mode": "historical_backfill",
                "semantic_extracted_at_ms": semantic_extracted_at_ms,
                "notice_lineage_first_detected_at_ms": None,
                "system_available_at_ms": None,
                "fact_available_at_ms": None,
                "capture_time_status": "historical_unknown",
                "point_in_time_replay_eligible": False,
                "risk_veto_candidate": False,
            }
            child_contracts.append(contract_rec)

        if not all_children_valid or is_revision_conflicting:
            for c in child_contracts:
                c["source_audit_eligible"] = False

        contracts.extend(child_contracts)

        eligible_children = [c for c in child_contracts if c["source_audit_eligible"]]
        declared_child_count = len(child_contracts)
        eligible_child_count = len(eligible_children)

        if is_revision_conflicting:
            parent_decl_status = "revision_conflicting"
            mapping_status = "fail"
            class_status = "fail"
        elif not all_children_valid or has_unresolved_batch:
            parent_decl_status = "incomplete"
            mapping_status = "fail"
            class_status = "fail"
        else:
            parent_decl_status = "complete"
            mapping_status = "pass"
            class_status = "in_scope" if eligible_child_count > 0 else "out_of_scope"

        source_integrity_pass = pub_pass and (parse_err is None)
        parent_eligible = (parent_decl_status == "complete" and mapping_status == "pass" and eligible_child_count > 0)

        diag_codes = []
        if not pub_pass:
            diag_codes.append(f"publication_time_{pub_status}")
        if is_revision_conflicting:
            diag_codes.append("revision_conflicting")
        if not all_children_valid:
            diag_codes.append("incomplete_child_declaration")

        parent_outcomes.append(_parent_outcome(
            source_article_id=aid, detail_authority_status="trusted",
            selected_detail_revision_id=selected_rev_id,
            source_integrity_parent_pass=source_integrity_pass,
            source_published_at_ms=bapi_pub_date if pub_pass else None,
            publication_time_status=pub_status, parent_declaration_status=parent_decl_status,
            mapping_status=mapping_status, classification_status=class_status,
            eligible_child_count=eligible_child_count,
            semantic_extracted_at_ms=semantic_extracted_at_ms, diagnostic_codes=diag_codes,
        ))

        notices.append({
            "schema_version": SCHEMA_VERSION_DELISTING_NOTICE,
            "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
            "source_article_id": aid,
            "detail_revision_id": selected_rev_id,
            "semantic_extraction_id": semantic_extraction_id,
            "source_detail_title": parsed_bapi["title"],
            "source_published_at_ms": bapi_pub_date if pub_pass else None,
            "publication_time_status": pub_status,
            "parent_declaration_status": parent_decl_status,
            "source_audit_eligible": parent_eligible,
            "declared_child_count": declared_child_count,
            "eligible_child_count": eligible_child_count,
            "capture_mode": "historical_backfill",
            "semantic_extracted_at_ms": semantic_extracted_at_ms,
            "notice_lineage_first_detected_at_ms": None,
            "system_available_at_ms": None,
            "fact_available_at_ms": None,
            "capture_time_status": "historical_unknown",
            "point_in_time_replay_eligible": False,
            "risk_veto_candidate": False,
        })

    # Sort all derived collections strictly
    parent_outcomes.sort(key=lambda r: r["source_article_id"])
    detail_revision_projections.sort(key=lambda r: (r["source_article_id"], r["detail_revision_id"]))
    semantic_extractions.sort(key=lambda r: (r["source_article_id"], r["detail_revision_id"], r["semantic_extraction_id"]))
    notices.sort(key=lambda r: r["source_article_id"])
    contracts.sort(key=lambda r: (r["parent_article_id"], r["canonical_symbol"], r["contract_id"]))
    diagnostics.sort(key=lambda r: r.get("observation_identity", ""))

    return AdapterReduction(
        candidate_manifest=candidate_manifest_dict,
        parent_outcomes=tuple(parent_outcomes),
        detail_revision_projection=tuple(detail_revision_projections),
        semantic_extractions=tuple(semantic_extractions),
        notices=tuple(notices),
        contracts=tuple(contracts),
        diagnostics=tuple(diagnostics),
    )


def deterministic_projection_view(value: Any) -> Any:
    """Recursively removes only semantic_extracted_at_ms, preserving all other keys, types, and ordering."""
    if isinstance(value, dict):
        return {
            k: deterministic_projection_view(v)
            for k, v in value.items()
            if k != "semantic_extracted_at_ms"
        }
    elif isinstance(value, list):
        return [deterministic_projection_view(x) for x in value]
    elif isinstance(value, tuple):
        return tuple(deterministic_projection_view(x) for x in value)
    return value


def build_precompletion_summary(
    reduction: AdapterReduction,
    *,
    audit_run_id: str,
    source_export_receipt_sha256: str,
    candidate_manifest_sha256: str,
) -> Dict[str, Any]:
    """Builds pre-completion summary containing frozen metrics, threshold snapshot, and false authority flags."""
    import configs.base as base

    total_candidates = len(reduction.parent_outcomes)
    trusted_parents = sum(1 for o in reduction.parent_outcomes if o["detail_authority_status"] == "trusted")
    source_integrity_passed = sum(1 for o in reduction.parent_outcomes if o["source_integrity_parent_pass"])
    source_integrity_rate = (source_integrity_passed / total_candidates) if total_candidates > 0 else 0.0

    delisting_parents = [o for o in reduction.parent_outcomes if o["detail_authority_status"] == "trusted"]
    delisting_count = len(delisting_parents)
    symbol_mapping_passed = sum(1 for o in delisting_parents if o["mapping_status"] == "pass")
    symbol_mapping_rate = (symbol_mapping_passed / delisting_count) if delisting_count > 0 else 0.0

    classification_count = delisting_count
    classification_passed = sum(
        1 for o in delisting_parents if o["classification_status"] in ("in_scope", "out_of_scope")
    )
    classification_rate = (classification_passed / classification_count) if classification_count > 0 else 0.0

    eligible_outcomes = [
        o for o in reduction.parent_outcomes
        if o["parent_declaration_status"] == "complete"
        and o["mapping_status"] == "pass"
        and o["classification_status"] == "in_scope"
        and o["eligible_child_count"] > 0
    ]
    historical_events_found = len(eligible_outcomes)

    # Event days: distinct UTC calendar dates of present source_published_at_ms among eligible parents
    eligible_aids = {o["source_article_id"] for o in eligible_outcomes}
    event_dates: Set[str] = set()
    for n in reduction.notices:
        if n["source_article_id"] in eligible_aids:
            pub_ms = n.get("source_published_at_ms")
            if pub_ms is not None:
                dt_str = datetime.fromtimestamp(pub_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                event_dates.add(dt_str)
    event_days = len(event_dates)

    # Distinct eligible child symbols
    eligible_symbols: Set[str] = set()
    for c in reduction.contracts:
        if c.get("source_audit_eligible"):
            eligible_symbols.add(c["canonical_symbol"])
    symbols_with_events = len(eligible_symbols)

    forbidden_payload_count = len({d["observation_identity"] for d in reduction.diagnostics})

    threshold_snapshot = {
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS": base.EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS,
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS": base.EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS,
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS": base.EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS,
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO": base.EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO,
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO": base.EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO,
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO": base.EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO,
        "EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT": base.EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT,
    }

    available_at_policy_defined = True
    source_schema_integrity_passed = bool(
        source_integrity_rate >= threshold_snapshot["EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO"]
        and symbol_mapping_rate >= threshold_snapshot["EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO"]
        and classification_rate >= threshold_snapshot["EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO"]
        and available_at_policy_defined
        and forbidden_payload_count <= threshold_snapshot["EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT"]
    )

    sample_sufficiency_passed = bool(
        historical_events_found >= threshold_snapshot["EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS"]
        and event_days >= threshold_snapshot["EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS"]
        and symbols_with_events >= threshold_snapshot["EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS"]
    )

    source_audit_evidence_candidate_passed = bool(source_schema_integrity_passed and sample_sufficiency_passed)

    authority_flags = {
        "RISK_LIVE_TRADING_ENABLED": False,
        "point_in_time_source_validated": False,
        "market_data_coverage_passed": False,
        "replay_allowed": False,
        "point_in_time_directional_replay_allowed": False,
        "risk_veto_candidate": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "execution_feasibility_claim_allowed": False,
    }

    return {
        "schema_version": "stage1_6a_source_audit_summary_v1",
        "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
        "audit_run_id": audit_run_id,
        "audit_summary_state": "pre_completion",
        "source_export_receipt_sha256": source_export_receipt_sha256,
        "input_export_id": reduction.candidate_manifest["input_export_id"],
        "input_manifest_sha256": reduction.candidate_manifest["input_manifest_sha256"],
        "audit_candidate_manifest_sha256": candidate_manifest_sha256,
        "candidate_discovery_rule_version": CANDIDATE_DISCOVERY_RULE_VERSION,
        "audit_metric_definition_version": AUDIT_METRIC_DEFINITION_VERSION,
        "body_normalization_version": BODY_NORMALIZATION_VERSION,
        "semantic_extractor_version": SEMANTIC_EXTRACTOR_VERSION,
        "metrics": {
            "candidate_total_denominator": total_candidates,
            "trusted_parents_count": trusted_parents,
            "symbols_mapped_count": symbol_mapping_passed,
            "classified_parents_count": classification_passed,
            "source_integrity_pass_rate": source_integrity_rate,
            "symbol_mapping_pass_rate": symbol_mapping_rate,
            "event_type_classification_pass_rate": classification_rate,
            "historical_events_found": historical_events_found,
            "event_days": event_days,
            "symbols_with_events": symbols_with_events,
            "forbidden_payload_count": forbidden_payload_count,
        },
        "available_at_policy_defined": available_at_policy_defined,
        "source_schema_integrity_passed": source_schema_integrity_passed,
        "sample_sufficiency_passed": sample_sufficiency_passed,
        "source_audit_evidence_candidate_passed": source_audit_evidence_candidate_passed,
        "threshold_snapshot": threshold_snapshot,
        "source_audit_passed": False,
        "allowed_next_action": "pending_completion",
        "permitted_design_options": [],
        "authority_flags": authority_flags,
    }
