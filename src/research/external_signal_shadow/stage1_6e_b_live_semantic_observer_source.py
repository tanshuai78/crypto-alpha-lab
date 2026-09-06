"""Stage 1.6D live delisting source consumer and boundary validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from configs import base
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    DETAIL_REQUEST_VARIANT,
    SOURCE_PROFILE_ID,
    compute_live_v3_checkpoint_id,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    sha256_hex,
)


class Stage16EBSourceError(Exception):
    """Base error for source consumer violations."""
    pass


class Stage16EBSourceCheckpointInvalid(Stage16EBSourceError):
    """Raised when checkpoint metadata, stream maps, boundaries, or hashes fail validation."""
    pass


class Stage16EBOrphanOrAmbiguousLiveRevision(Stage16EBSourceError):
    """Raised when candidate observation linkage cardinality is zero or multiple."""
    pass


class Stage16EBRawPathHashOrProfileMismatch(Stage16EBSourceError):
    """Raised when linked raw file is missing, symlink, or hash mismatches."""
    pass


@dataclass(frozen=True)
class SourceSnapshot:
    is_ready: bool
    degraded_reason: str | None
    checkpoint: dict[str, Any]
    checkpoint_id: str
    checkpoint_sha256: str


def derive_daily_observation_stream_key(captured_at_ms: int) -> str:
    date_str = datetime.fromtimestamp(captured_at_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
    return f"detail_observations/{date_str}.jsonl"


class Stage16EBSourceConsumer:
    def __init__(
        self,
        authorized_source_root: Path | str,
        authorized_run_id: str,
        consumer_checkpoint_path: Path | str,
    ):
        self.authorized_source_root = Path(authorized_source_root)
        if not self.authorized_source_root.is_absolute():
            raise Stage16EBSourceError(f"absolute_path_required: {authorized_source_root}")
        if not self.authorized_source_root.is_dir():
            raise Stage16EBSourceError(f"source_root_missing: {authorized_source_root}")

        self.authorized_run_id = str(authorized_run_id)
        self.consumer_checkpoint_path = Path(consumer_checkpoint_path).resolve()
        self.last_consumed_offsets: dict[str, int] = {}
        self.last_consumed_hashes: dict[str, str] = {}

    def validate_source_checkpoint_map(self, chk_data: dict[str, Any]) -> None:
        stream_offsets = chk_data.get("stream_offsets")
        stream_last_hashes = chk_data.get("stream_last_hashes")
        if not isinstance(stream_offsets, dict) or not isinstance(stream_last_hashes, dict):
            raise Stage16EBSourceCheckpointInvalid("stream_maps_must_be_dicts")

        if set(stream_offsets.keys()) != set(stream_last_hashes.keys()):
            raise Stage16EBSourceCheckpointInvalid("stream_maps_keys_inconsistent")

        root_resolved = self.authorized_source_root.resolve()

        for stream_rel, offset in stream_offsets.items():
            if not isinstance(stream_rel, str) or not stream_rel:
                raise Stage16EBSourceCheckpointInvalid(f"invalid_stream_path: {stream_rel}")
            if stream_rel.startswith("/") or ".." in Path(stream_rel).parts:
                raise Stage16EBSourceCheckpointInvalid(f"invalid_stream_path_grammar: {stream_rel}")

            stream_path = (self.authorized_source_root / stream_rel).resolve()
            if not stream_path.is_relative_to(root_resolved):
                raise Stage16EBSourceCheckpointInvalid(f"stream_path_escapes_root: {stream_rel}")

            expected_hash = stream_last_hashes[stream_rel]
            if offset == 0:
                if expected_hash != "":
                    raise Stage16EBSourceCheckpointInvalid(f"zero_offset_must_have_empty_hash: {stream_rel}")
                continue

            if offset < 0:
                raise Stage16EBSourceCheckpointInvalid(f"negative_stream_offset: {stream_rel} {offset}")

            if not stream_path.is_file() or stream_path.is_symlink():
                raise Stage16EBSourceCheckpointInvalid(f"checkpoint_stream_missing: {stream_rel}")

            actual_size = stream_path.stat().st_size
            if actual_size < offset:
                raise Stage16EBSourceCheckpointInvalid(
                    f"checkpoint_stream_size_smaller_than_offset: {stream_rel} {actual_size} < {offset}"
                )

            with open(stream_path, "rb") as f:
                f.seek(offset - 1)
                last_byte = f.read(1)
                if last_byte != b"\n":
                    raise Stage16EBSourceCheckpointInvalid(
                        f"offset_not_line_boundary: {stream_rel} at {offset}"
                    )
                f.seek(0)
                committed_bytes = f.read(offset)

            lines = committed_bytes.rstrip(b"\r\n").splitlines()
            if not lines:
                raise Stage16EBSourceCheckpointInvalid(f"empty_committed_lines: {stream_rel}")
            actual_last_hash = sha256_hex(lines[-1])
            if actual_last_hash != expected_hash:
                raise Stage16EBSourceCheckpointInvalid(
                    f"prefix_hash_mismatch: {stream_rel} expected {expected_hash} got {actual_last_hash}"
                )

    def poll_and_validate_source_snapshot(self, current_time_ms: int) -> SourceSnapshot:
        chk_file = self.authorized_source_root / "observer_checkpoint.json"
        contract_file = self.authorized_source_root / "capture_run_contract.json"
        attest_file = self.authorized_source_root / "source_profile_probe_attestation.json"

        if not chk_file.is_file() or not contract_file.is_file() or not attest_file.is_file():
            raise Stage16EBSourceCheckpointInvalid("source_authority_files_missing")

        contract_data = json.loads(contract_file.read_text(encoding="utf-8"))
        attest_bytes = attest_file.read_bytes()
        attest_sha = sha256_hex(attest_bytes)
        chk_bytes = chk_file.read_bytes()
        chk_sha = sha256_hex(chk_bytes)
        chk_data = json.loads(chk_bytes.decode("utf-8"))

        if contract_data.get("run_id") != self.authorized_run_id:
            raise Stage16EBSourceCheckpointInvalid(f"contract_run_id_mismatch: {contract_data.get('run_id')}")
        if chk_data.get("run_id") != self.authorized_run_id:
            raise Stage16EBSourceCheckpointInvalid(f"checkpoint_run_id_mismatch: {chk_data.get('run_id')}")
        if chk_data.get("capture_mode") != "live_observed":
            raise Stage16EBSourceCheckpointInvalid(f"invalid_capture_mode: {chk_data.get('capture_mode')}")
        if chk_data.get("source_profile_id") != SOURCE_PROFILE_ID:
            raise Stage16EBSourceCheckpointInvalid(f"invalid_source_profile_id: {chk_data.get('source_profile_id')}")

        if attest_sha != contract_data.get("source_profile_attestation_sha256"):
            raise Stage16EBSourceCheckpointInvalid("contract_probe_attestation_sha_mismatch")
        if attest_sha != chk_data.get("source_profile_attestation_sha256"):
            raise Stage16EBSourceCheckpointInvalid("checkpoint_probe_attestation_sha_mismatch")

        expected_chk_id = compute_live_v3_checkpoint_id(chk_data)
        if chk_data.get("checkpoint_id") != expected_chk_id:
            raise Stage16EBSourceCheckpointInvalid("checkpoint_id_recalculation_mismatch")

        # Full checkpoint map and committed boundary validation
        self.validate_source_checkpoint_map(chk_data)

        # Monotonicity check vs last consumed offsets
        curr_offsets = chk_data.get("stream_offsets", {})
        for stream_name, prev_off in self.last_consumed_offsets.items():
            if stream_name in curr_offsets and curr_offsets[stream_name] < prev_off:
                raise Stage16EBSourceCheckpointInvalid(
                    f"stream_offset_rollback_detected: {stream_name} {curr_offsets[stream_name]} < {prev_off}"
                )

        heartbeat_at_ms = chk_data.get("heartbeat_at_ms")
        if heartbeat_at_ms is None or not isinstance(heartbeat_at_ms, int):
            raise Stage16EBSourceCheckpointInvalid("missing_heartbeat_at_ms")

        future_skew_limit = base.EXTERNAL_SIGNAL_STAGE1_6E_B_SOURCE_HEARTBEAT_FUTURE_SKEW_MS
        stale_limit = base.EXTERNAL_SIGNAL_STAGE1_6E_B_SOURCE_STALE_MS

        delta = current_time_ms - heartbeat_at_ms
        if delta < -future_skew_limit:
            return SourceSnapshot(
                is_ready=False,
                degraded_reason="source_heartbeat_future_skew_exceeded",
                checkpoint=chk_data,
                checkpoint_id=expected_chk_id,
                checkpoint_sha256=chk_sha,
            )

        if delta > stale_limit:
            return SourceSnapshot(
                is_ready=False,
                degraded_reason="source_stale",
                checkpoint=chk_data,
                checkpoint_id=expected_chk_id,
                checkpoint_sha256=chk_sha,
            )

        self.last_consumed_offsets = dict(curr_offsets)
        self.last_consumed_hashes = dict(chk_data.get("stream_last_hashes", {}))

        return SourceSnapshot(
            is_ready=True,
            degraded_reason=None,
            checkpoint=chk_data,
            checkpoint_id=expected_chk_id,
            checkpoint_sha256=chk_sha,
        )

    def read_new_detail_revisions(
        self,
        from_offset: int,
        to_offset: int,
    ) -> list[dict[str, Any]]:
        rev_file = self.authorized_source_root / "detail_revisions.jsonl"
        if not rev_file.exists() or from_offset >= to_offset:
            return []

        with rev_file.open("rb") as f:
            f.seek(from_offset)
            chunk = f.read(to_offset - from_offset)

        rows = []
        for line in chunk.decode("utf-8").splitlines():
            line_str = line.strip()
            if line_str:
                rows.append(json.loads(line_str))
        return rows

    def link_and_verify_detail_revision(
        self,
        revision: dict[str, Any],
        current_checkpoint: dict[str, Any],
    ) -> tuple[dict[str, Any], bytes]:
        if revision.get("capture_mode") != "live_observed":
            raise Stage16EBSourceCheckpointInvalid(
                f"invalid_revision_capture_mode: {revision.get('capture_mode')}"
            )
        if revision.get("source_profile_id") != SOURCE_PROFILE_ID:
            raise Stage16EBSourceCheckpointInvalid(
                f"invalid_revision_source_profile_id: {revision.get('source_profile_id')}"
            )
        if revision.get("request_variant") != DETAIL_REQUEST_VARIANT:
            raise Stage16EBSourceCheckpointInvalid(
                f"invalid_revision_request_variant: {revision.get('request_variant')}"
            )

        captured_at_ms = revision.get("captured_at_ms")
        if captured_at_ms is None or not isinstance(captured_at_ms, int):
            raise Stage16EBSourceCheckpointInvalid("revision_missing_captured_at_ms")

        article_id = revision.get("source_article_id")
        if not article_id:
            raise Stage16EBSourceCheckpointInvalid("revision_missing_source_article_id")

        raw_sha = revision.get("detail_raw_sha256")
        if not raw_sha:
            raise Stage16EBSourceCheckpointInvalid("revision_missing_detail_raw_sha256")

        raw_rel = revision.get("raw_payload_relative_path")
        if not raw_rel:
            raise Stage16EBSourceCheckpointInvalid("revision_missing_raw_payload_relative_path")

        daily_stream_key = derive_daily_observation_stream_key(captured_at_ms)
        stream_offsets = current_checkpoint.get("stream_offsets", {})
        if daily_stream_key not in stream_offsets or stream_offsets[daily_stream_key] <= 0:
            raise Stage16EBSourceCheckpointInvalid(
                f"daily_observation_stream_not_committed: {daily_stream_key}"
            )

        daily_offset = stream_offsets[daily_stream_key]
        obs_file = (self.authorized_source_root / daily_stream_key).resolve()
        if not obs_file.is_file() or obs_file.is_symlink():
            raise Stage16EBSourceCheckpointInvalid(f"observation_file_missing: {daily_stream_key}")

        with open(obs_file, "rb") as f:
            obs_bytes = f.read(daily_offset)

        candidates = []
        for line in obs_bytes.decode("utf-8").splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            obs = json.loads(line_str)
            if (
                obs.get("capture_mode") == "live_observed"
                and obs.get("source_profile_id") == SOURCE_PROFILE_ID
                and obs.get("request_variant") == DETAIL_REQUEST_VARIANT
                and obs.get("run_id") == self.authorized_run_id
                and obs.get("trust_validation_status") == "trusted"
                and str(obs.get("source_article_id")) == str(article_id)
                and obs.get("raw_payload_sha256") == raw_sha
                and obs.get("raw_payload_relative_path") == raw_rel
            ):
                candidates.append(obs)

        if len(candidates) != 1:
            raise Stage16EBOrphanOrAmbiguousLiveRevision(
                f"orphan_or_ambiguous_live_revision: found {len(candidates)} candidates for article {article_id}"
            )

        unique_obs = candidates[0]
        if not unique_obs.get("request_observation_id"):
            raise Stage16EBOrphanOrAmbiguousLiveRevision("candidate_missing_request_observation_id")

        if revision.get("t_detail_trusted_ms") is None:
            raise Stage16EBOrphanOrAmbiguousLiveRevision("revision_missing_t_detail_trusted_ms")

        # Physical raw byte validation
        root_resolved = self.authorized_source_root.resolve()
        raw_unresolved = self.authorized_source_root / raw_rel
        if raw_unresolved.is_symlink() or not raw_unresolved.is_file():
            raise Stage16EBRawPathHashOrProfileMismatch(f"raw_missing_or_symlink: {raw_unresolved}")

        raw_file = raw_unresolved.resolve()
        if not raw_file.is_relative_to(root_resolved):
            raise Stage16EBRawPathHashOrProfileMismatch(f"raw_path_escapes_root: {raw_rel}")

        raw_bytes = raw_file.read_bytes()
        actual_raw_sha = sha256_hex(raw_bytes)
        if actual_raw_sha != raw_sha or actual_raw_sha != unique_obs.get("raw_payload_sha256"):
            raise Stage16EBRawPathHashOrProfileMismatch(
                f"raw_payload_hash_mismatch: expected {raw_sha} got {actual_raw_sha}"
            )

        return unique_obs, raw_bytes
