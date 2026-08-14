"""
src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py
Durable append-only registry for Stage 1.5F schedule revisions.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from research.external_signal_shadow.stage1_5_launch_anchor_contract import canonical_json_bytes
from src.research.external_signal_shadow.stage1_5_storage_guard import require_storage_write


def compute_revision_application_id(*, stable_schedule_identity: str, revision_id: str, revision_payload_hash: str) -> str:
    payload = {
        "stable_schedule_identity": stable_schedule_identity,
        "revision_id": revision_id,
        "revision_payload_hash": revision_payload_hash,
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


class ScheduleRevisionRegistry:
    def __init__(self, registry_file: Path):
        self.registry_file = Path(registry_file)
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.applied_ids: set[str] = set()
        self.records: list[dict[str, Any]] = []
        self.latest_status_by_id: dict[str, str] = {}
        self._load()

    def _load(self):
        if not self.registry_file.exists():
            return
        with open(self.registry_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                self.records.append(row)
                row_app_id = row.get("revision_application_id")
                if row_app_id:
                    self.latest_status_by_id[row_app_id] = row.get("status", "")
                if row.get("status") == "revision_applied":
                    if row_app_id:
                        self.applied_ids.add(row_app_id)

    def is_applied(self, revision_application_id: str) -> bool:
        return revision_application_id in self.applied_ids

    def latest_status(self, revision_application_id: str) -> str:
        return self.latest_status_by_id.get(revision_application_id, "")

    def record_revision(
        self,
        *,
        revision_application_id: str,
        status: str,
        stable_schedule_identity: str,
        revision_id: str,
        revision_payload_hash: str,
        storage_guard: Any,
        details: dict[str, Any] | None = None,
    ) -> dict:
        if storage_guard is None:
            raise TypeError("storage_guard_required")

        row = {
            "revision_application_id": revision_application_id,
            "status": status,
            "stable_schedule_identity": stable_schedule_identity,
            "revision_id": revision_id,
            "revision_payload_hash": revision_payload_hash,
            "details": details or {},
        }
        serialized_bytes = (json.dumps(row, ensure_ascii=True) + "\n").encode("utf-8")

        def _write_action():
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_file, "ab") as f:
                f.write(serialized_bytes)
                f.flush()
                os.fsync(f.fileno())

        res = storage_guard.reserve_and_write(
            artifact_class="normal_data",
            transient_peak_bytes=len(serialized_bytes),
            persistent_delta_bytes=len(serialized_bytes),
            write_func=_write_action,
        )

        require_storage_write(storage_guard, res)

        self.records.append(row)
        self.latest_status_by_id[revision_application_id] = status
        if status == "revision_applied":
            self.applied_ids.add(revision_application_id)

        return {"written": True, "storage_blocker": None}
