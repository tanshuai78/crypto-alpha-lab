"""Source profile probe runner for Stage 1.6B."""

import argparse
import hashlib
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

from src.research.external_signal_shadow.stage1_6b_canonical_source_client import (
    Stage16BCanonicalClient,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    ALLOWED_FINAL_HOST,
    BASE_URL,
    DETAIL_PATH,
    INDEX_PATH,
    PROBE_COMMAND_VERSION,
    SOURCE_AUTHORITY,
    SOURCE_PROFILE_ID,
    TRANSPORT_SUPPORT_STATUS,
    RequestClass,
    SourceProfileProbeAttestation,
    canonical_json,
    compute_request_headers_profile_sha256,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import (
    Stage16BStorageGuard,
    validate_probe_attestation_path,
    write_atomic_json,
)


def compute_source_profile_sha256() -> str:
    profile_dict = {
        "source_profile_id": SOURCE_PROFILE_ID,
        "source_authority": SOURCE_AUTHORITY,
        "transport_support_status": TRANSPORT_SUPPORT_STATUS,
        "base_url": BASE_URL,
        "allowed_final_host": ALLOWED_FINAL_HOST,
        "index_path": INDEX_PATH,
        "detail_path": DETAIL_PATH,
    }
    return hashlib.sha256(canonical_json(profile_dict).encode("utf-8")).hexdigest()


def run_source_profile_probe(
    probe_article_id: str,
    live_public_readonly: bool,
    project_root: Optional[Path] = None,
    opener: Optional[Callable[..., Any]] = None,
) -> Path:
    """Execute source profile probe and persist signed attestation JSON."""
    if not live_public_readonly:
        raise ValueError("live_public_readonly_required: must explicitly supply --live-public-readonly")

    # Validate 32 hex char article ID
    if len(probe_article_id) != 32 or not all(c in "0123456789abcdefABCDEF" for c in probe_article_id):
        raise ValueError(f"invalid_probe_article_id: article ID must be 32 hex chars, got {probe_article_id}")

    p_root = (project_root or Path.cwd()).resolve()
    client = Stage16BCanonicalClient(live_public_readonly=True, opener=opener)

    # 1. Probe Index Query
    res_index = client.fetch_index_page(
        page_no=1,
        run_id="probe_run",
        request_class=RequestClass.PROFILE_PROBE_INDEX.value,
        monotonic_request_seq=1,
    )
    if res_index.trust_validation_status != "trusted":
        raise RuntimeError(f"Probe index fetch failed: {res_index.trust_validation_status} - {res_index.error_message}")

    # 2. Probe Detail Query
    res_detail = client.fetch_article_detail(
        article_code=probe_article_id,
        run_id="probe_run",
        request_class=RequestClass.PROFILE_PROBE_DETAIL.value,
        monotonic_request_seq=2,
    )
    if res_detail.trust_validation_status != "trusted":
        raise RuntimeError(f"Probe detail fetch failed: {res_detail.trust_validation_status} - {res_detail.error_message}")

    profile_sha = compute_source_profile_sha256()
    headers_sha = compute_request_headers_profile_sha256()
    now_ms = int(time.time() * 1000)

    attestation = SourceProfileProbeAttestation(
        schema_version="stage1_6b_source_profile_probe_attestation_v1",
        probe_command_version=PROBE_COMMAND_VERSION,
        source_profile_id=SOURCE_PROFILE_ID,
        source_authority=SOURCE_AUTHORITY,
        transport_support_status=TRANSPORT_SUPPORT_STATUS,
        source_profile_sha256=profile_sha,
        request_headers_profile_sha256=headers_sha,
        probe_article_id=probe_article_id,
        index_requested_url=res_index.requested_url,
        index_final_url=res_index.final_url,
        index_http_status=res_index.http_status,
        index_content_type=res_index.content_type,
        index_payload_bytes=res_index.raw_payload_bytes,
        index_article_id_path="data.articles[].code",
        detail_requested_url=res_detail.requested_url,
        detail_final_url=res_detail.final_url,
        detail_http_status=res_detail.http_status,
        detail_content_type=res_detail.content_type,
        detail_payload_bytes=res_detail.raw_payload_bytes,
        detail_body_path="data.body",
        probe_attested_at_ms=now_ms,
    )

    target_dir = p_root / "data" / "external_signal_shadow" / "stage1_6b" / "source_profile_attestations" / profile_sha
    target_path = target_dir / "source_profile_probe_attestation.json"

    # Strict path check before writing
    validated_path = validate_probe_attestation_path(target_path, project_root=p_root)

    guard = Stage16BStorageGuard(output_root=target_dir)
    guard.validate_startup_free_space()
    current_size = validated_path.stat().st_size if validated_path.is_file() else 0
    write_atomic_json(
        run_root=target_dir,
        relative_path="source_profile_probe_attestation.json",
        data_dict=attestation.to_dict(),
        write_class="ordinary_control_plane",
        guard=guard,
        current_root_bytes=current_size,
    )

    return validated_path


def main():
    parser = argparse.ArgumentParser(description="Stage 1.6B Source Profile Probe Runner")
    parser.add_argument("--probe-article-id", required=True, help="32-hex pinned Binance announcement article code")
    parser.add_argument("--live-public-readonly", action="store_true", default=False, help="Explicit readonly network permission")
    parser.add_argument("--project-root", type=Path, default=None, help="Root path of the project")

    args = parser.parse_args()

    try:
        att_path = run_source_profile_probe(
            probe_article_id=args.probe_article_id,
            live_public_readonly=args.live_public_readonly,
            project_root=args.project_root,
        )
        print(f"SUCCESS: Source profile probe attested at {att_path}")
        sys.exit(0)
    except Exception as exc:
        print(f"FAILED: Source profile probe failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
