"""
src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py
Durable append-only registry for Stage 1.5F schedule revisions.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from research.external_signal_shadow.stage1_5_launch_anchor_contract import canonical_json_bytes


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
        details: dict[str, Any] | None = None,
    ):
        row = {
            "revision_application_id": revision_application_id,
            "status": status,
            "stable_schedule_identity": stable_schedule_identity,
            "revision_id": revision_id,
            "revision_payload_hash": revision_payload_hash,
            "details": details or {},
        }
        with open(self.registry_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
        self.records.append(row)
        self.latest_status_by_id[revision_application_id] = status
        if status == "revision_applied":
            self.applied_ids.add(revision_application_id)
