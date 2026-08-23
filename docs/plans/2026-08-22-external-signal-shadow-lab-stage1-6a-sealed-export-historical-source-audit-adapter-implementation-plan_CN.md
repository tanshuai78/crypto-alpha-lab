# Stage 1.6A Sealed Export Historical Source-Audit Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** `draft_for_review` - this document authorizes no implementation, local real-data run, VPS operation, replay, risk veto, paper trading, or live trading.

**Design authority under closure confirmation:** [2026-08-22 Stage 1.6A Sealed Export Historical Source-Audit Adapter Design](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/docs/designs/2026-08-22-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design_CN.md)

**Design SHA-256:** `9979a3b772c56e277d9ed81a0259049321fa2129d4e070b71c91406a61858263`

**Implementation approval SHA control:** The reviewer/user approval record must supply the exact approved Plan hash as `APPROVED_PLAN_SHA256` at execution time. Task 0 rejects a current Plan whose hash differs; it must not treat an execution-time self-hash as approval.

**Planning baseline:** `d1656f1c3871e3aec4192140a3753bfaaa22f462`

**Goal:** Build a local, offline Stage 1.6A adapter that converts exactly one verified Stage 1.6B historical sealed export into a deterministic, independently verifiable source-audit root, without granting PIT, market-data, risk-veto, alpha, paper-trading, or execution authority.

**Architecture:** The new adapter calls the existing Stage 1.6B `load_sealed_export()` validator exactly once, captures every consumed authoritative artifact into a single-read in-memory snapshot, and derives all 1.6A records only from that snapshot. A separate 1.6A persistence profile writes derived records, a pre-completion summary, and a last-written completion manifest; its completed consumer reconstructs the source snapshot and exact-compares a fresh deterministic reduction before accepting the root.

**Tech Stack:** Python 3.12, stdlib `json`/`hashlib`/`pathlib`/`unicodedata`, existing Stage 1.6A model/audit/storage/summary helpers, existing Stage 1.6B sealed-export consumer, `pytest`, `ruff`.

## Global Constraints

- `RISK_LIVE_TRADING_ENABLED = false`; this work creates no network, strategy, risk, market-data, replay, paper-trading, or execution path.
- The input is exactly one local `historical_backfill/.../sealed_exports/<export_id>/` directory. No glob, `latest` shortcut, raw 1.6B run root, capture bundle, VPS path, or symlink escape is accepted.
- The adapter calls `stage1_6b_canonical_source_storage.load_sealed_export(export_dir)` exactly once before creating an output root. It must not duplicate 1.6B manifest, hash, terminal, catalog, or historical-coverage validation.
- Every consumed 1.6B artifact is read once after validation, size/hash checked against the verified manifest tuple, parsed from those same bytes, and never reopened for semantic reduction.
- The adapter never copies or mutates Stage 1.6B raw evidence. It writes only a receipt that pins the input export ID, manifest hash, and sorted consumed-artifact tuples.
- BAPI article identity is `data.code == source_article_id`; numeric `data.id` is diagnostic-only.
- Supported exact versions are `stage1_6a_bapi_body_tree_v1`, `stage1_6a_extractor_v1`, and `stage1_6a_audit_metric_v1`. Unknown/mismatched versions reject; no fallback dispatch exists.
- A parent aggregates every `DetailObservation` with its `source_article_id`: any trusted observation establishes transport-level detail authority and terminal non-trusted retries are diagnostics only; no trusted observation plus only terminal non-trusted observations yields denominator-visible `detail_unavailable`; pending/unresolved observations without a trusted observation reject the export. Missing/duplicate `request_observation_id`, trusted observation/revision/raw linkage failures, or orphan revisions reject before semantic reduction.
- Record/hash-linked malformed BAPI envelope, `body_parse_unresolved`, and publication conflict remain in the frozen candidate denominator and fail `source_integrity_parent_pass`. Missing required streams, contradictory immutable provenance, and a present wrong string `data.code` reject the entire input export before semantic reduction.
- Existing `EXTERNAL_SIGNAL_STAGE1_6A_*` values in `configs/base.py` are the only threshold authority. Add no config, alias, threshold, environment override, or hidden default.
- The original `run_stage1_6a_futures_delisting_source_audit.py --fixture-run` behavior remains byte-for-byte compatible at its contract boundary. Do not add real-input support to that CLI.
- No real adapter source-audit run occurs during implementation. Task 0's read-only `load_sealed_export()` preflight against the explicitly frozen export is required; all RED/GREEN tests use deterministic synthetic fixtures and temporary roots only.
- A partial output root is non-consumable. Only `completion_manifest.json`, written last, may state final completion, final `source_audit_passed`, or final `allowed_next_action` / `permitted_design_options`.

---

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_6a_sealed_export_historical_adapter.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_summary.py`
- `scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py`
- `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py`
- `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py`
- `tests/fixtures/external_signal_shadow/stage1_6a_sealed_export_adapter/`

Allowed documentation paths:
- `docs/plans/2026-08-22-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-implementation-plan_CN.md`

Allowed generated/runtime artifacts:
- `${TMPDIR:-/tmp}/stage1_6a_sealed_export_adapter_execution_<timestamp>/` - execution-local provenance only; never committed.
- `pytest` temporary directories only. A later separately approved local operation may create `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/<run-id>/`; it is generated data and must not be committed.

Affected but unchanged:
- `configs/base.py`
  - compatibility evidence: exact AST/value guard in Task 6 and existing Stage 1.6A summary tests.
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py`
  - compatibility evidence: `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py` stays zero-diff and passes.
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py`
  - compatibility evidence: `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py` stays zero-diff and passes.
- `scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py`
  - compatibility evidence: `tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py` stays zero-diff and passes.
- `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`
  - compatibility evidence: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py` stays zero-diff and passes.
- `src/research/external_signal_shadow/stage1_6b_canonical_source_{client,models,observer}.py`
  - compatibility evidence: their existing test modules stay zero-diff and pass.
- `src/research/external_signal_shadow/stage1_5*.py`, `scripts/external_signal_shadow/run_stage1_5*.py`, and all `tests/**/test_stage1_5*.py`
  - compatibility evidence: Task 6 enforces zero diff and runs the listed Stage 1.5 regression subset.

Forbidden:
- Any mutation outside the allowed paths.
- Any change to the approved Design, this Plan during execution, `configs/base.py`, Stage 1.5, or any Stage 1.6B producer/client/observer/storage path.
- Any network request, subprocess-based transport, VPS command, tmux session, deployment command, real sealed-export run, or writing below an existing Stage 1.6B root.
- Any raw-evidence copy, whole-repository formatter/autofix, unscoped cleanup, `git clean`, or destructive git operation.
- Any metric denominator exclusion for a valid imported parent based on parse, mapping, classification, detail, or publication outcome. Structural evidence-chain corruption rejects the input before metrics exist; it is not a denominator exclusion.

## Invariant-to-Task Map

| Design invariant | Production boundary | Task and evidence |
| --- | --- | --- |
| INV-01, INV-08 | verified sealed-export path and in-memory snapshot | Tasks 0-1: one `load_sealed_export` call, path/symlink rejection, one-read/hash-checked receipt tests |
| INV-02, INV-06 | candidate/outcome reducer | Tasks 2-3: every discovery remains denominator; multi-observation aggregation is trusted-preferred; malformed/detail-failed parents emit no child |
| INV-03, INV-04 | BAPI envelope/body reducer | Task 2: `data.code`, raw hash, revision linkage, no title semantics tests |
| INV-05, INV-07 | historical records and authority caps | Tasks 2-3, 5: null PIT fields and every non-source authority false |
| INV-09, INV-12, INV-14 | persistence and completed consumer | Task 4: durable-artifact metric rebuild, pre-completion cap, manifest-last crash, hash/receipt/replay exact-comparison tests |
| INV-10 | runner/module import surface | Tasks 5 and 6: no-network CLI and AST/import isolation checks |
| INV-11 | summary threshold snapshot | Tasks 3 and 6: exact current config snapshot and zero config diff |
| INV-13 | publication reducer | Task 2: valid-int grammar, `publishDate` authority, `first_list_capture_id`-bound `releaseDate` and event-day tests |

## Task 0: Freeze Execution Authority and Prove Existing Compatibility

**Design invariants:** INV-01, INV-10, INV-11, INV-12, INV-14.

**Files:**
- Create: none.
- Modify: none.
- Verify: all paths listed in `Affected but unchanged`.

**Interfaces:**
- Consumes: `load_sealed_export(export_dir: Path) -> Dict[str, Any]` from `stage1_6b_canonical_source_storage.py`.
- Produces: an external execution log containing baseline, Design/Plan hashes, local sealed-export preflight, static consumer inventory, and explicit STOP/continue decision. It is not a repository artifact.

- [ ] **Step 1: Record baseline and protect pre-existing work**

  Run from the repository root before changing any allowed implementation file:

  ```bash
  export BASE_SHA="$(git rev-parse HEAD)"
  export PLANNING_BASE_SHA="d1656f1c3871e3aec4192140a3753bfaaa22f462"
  export DESIGN_PATH="docs/designs/2026-08-22-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design_CN.md"
  export PLAN_PATH="docs/plans/2026-08-22-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-implementation-plan_CN.md"
  : "${APPROVED_PLAN_SHA256:?STOP: set the exact Plan SHA-256 recorded by the approving reviewer/user}"
  export DESIGN_SHA256="$(shasum -a 256 "$DESIGN_PATH" | awk '{print $1}')"
  export PLAN_SHA256="$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}')"
  export EXECUTION_PROVENANCE_DIR="${TMPDIR:-/tmp}/stage1_6a_sealed_export_adapter_execution_$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$EXECUTION_PROVENANCE_DIR"
  export PREEXISTING_STATE_JSON="$EXECUTION_PROVENANCE_DIR/preexisting_state.json"
  export EXPECTED_EXPORT_ID="3fbe8e92d83af929913ca16276df3cddf81b26b7327e476b19712870a7792247"
  export EXPECTED_INPUT_MANIFEST_SHA256="2d0d992a6dc4d8086f2d07b8c29143e4d74b140ce370848564d032d51503a254"
  printf 'BASE_SHA=%s\nPLANNING_BASE_SHA=%s\nDESIGN_SHA256=%s\nPLAN_SHA256=%s\nEXECUTION_PROVENANCE_DIR=%s\n' \
    "$BASE_SHA" "$PLANNING_BASE_SHA" "$DESIGN_SHA256" "$PLAN_SHA256" "$EXECUTION_PROVENANCE_DIR"
  test "$PLAN_SHA256" = "$APPROVED_PLAN_SHA256" || { echo "STOP: Plan differs from approved review artifact" >&2; exit 1; }
  test "$DESIGN_SHA256" = "9979a3b772c56e277d9ed81a0259049321fa2129d4e070b71c91406a61858263" || { echo "STOP: Design differs from reviewed authority" >&2; exit 1; }
  git merge-base --is-ancestor "$PLANNING_BASE_SHA" "$BASE_SHA"
  if ! git diff --quiet "$PLANNING_BASE_SHA".."$BASE_SHA" -- \
    configs/base.py src/research/external_signal_shadow/stage1_6a_* \
    src/research/external_signal_shadow/stage1_6b_* scripts/external_signal_shadow/run_stage1_6a_* \
    scripts/external_signal_shadow/run_stage1_6b_* tests/research/external_signal_shadow/test_stage1_6a_* \
    tests/research/external_signal_shadow/test_stage1_6b_* tests/scripts/external_signal_shadow/test_run_stage1_6a_* \
    tests/scripts/external_signal_shadow/test_run_stage1_6b_*; then
    echo "STOP: implementation baseline drifted from the reviewed planning baseline" >&2
    exit 1
  fi
  PYTHONPATH=src:. .venv/bin/python - "$PREEXISTING_STATE_JSON" <<'PY'
  import hashlib, json, os, subprocess, sys
  from pathlib import Path

  def digest(path: Path) -> str:
      if path.is_symlink():
          return "symlink:" + hashlib.sha256(os.readlink(path).encode()).hexdigest()
      if path.is_file():
          return hashlib.sha256(path.read_bytes()).hexdigest()
      return "non_regular"

  raw = subprocess.check_output(
      ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], text=False
  )
  entries = []
  for item in raw.split(b"\0"):
      if not item:
          continue
      status, raw_path = item[:2].decode(), item[3:].decode()
      if "R" in status or "C" in status:
          raise SystemExit(f"STOP: rename/copy pre-existing state requires a separate provenance parser: {status} {raw_path}")
      path = Path(raw_path)
      entries.append({"path": raw_path, "status": status, "sha256": digest(path) if path.exists() or path.is_symlink() else "missing"})
  Path(sys.argv[1]).write_text(json.dumps(entries, sort_keys=True, indent=2) + "\n", encoding="utf-8")
  print({"preexisting_entry_count": len(entries), "provenance": sys.argv[1]})
  PY
  ```

  Expected: the Design hash matches exactly; the reviewed planning baseline is an ancestor of the execution baseline; and no relevant 1.6A/1.6B/config/test path drifted between them. The provenance file records every pre-existing dirty/untracked path, status, and content hash. Never overwrite, stage, revert, or claim any recorded entry as this task's work. STOP if Design/Plan hashes change after this step, an entry's recorded hash changes, or baseline drift is detected.

- [ ] **Step 2: Confirm the exact Design P0 contract before using it as implementation authority**

  Run:

  ```bash
  rg -n -A 14 'Completed-consumer source binding|source_integrity_parent_pass|body_parse_unresolved|request_observation_id|structural evidence-chain|must not use a glob' "$DESIGN_PATH"
  ```

  Expected: the exact Design hash above distinguishes input-export structural rejection from denominator-visible parent failures, states that `body_parse_unresolved` remains in the frozen denominator while failing the source-integrity numerator, and defines the Section 3.1.1 caller-supplied sealed-export binding with no glob/latest/search. This is a closure confirmation of existing Design content, not permission to edit the Design. If the Design still has status `design_draft_for_review`, the Plan remains `draft_for_review`; obtain the Design review/approval decision before implementation.

- [ ] **Step 3: Perform the Design-required read-only real-export preflight**

  This step reads no artifact twice through new code and writes nothing. It does not run the new adapter.

  ```bash
  export SEALED_EXPORT='data/external_signal_shadow/stage1_6b/historical_backfill/hist_delisting_retry_20260822T041106Z/sealed_exports/3fbe8e92d83af929913ca16276df3cddf81b26b7327e476b19712870a7792247'
  PYTHONPATH=src:. .venv/bin/python - "$SEALED_EXPORT" "$EXPECTED_EXPORT_ID" "$EXPECTED_INPUT_MANIFEST_SHA256" <<'PY'
  import json
  import sys
  from collections import Counter
  from pathlib import Path
  from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import load_sealed_export

  root = Path(sys.argv[1])
  expected_export_id = sys.argv[2]
  expected_manifest_sha256 = sys.argv[3]
  returned = load_sealed_export(root)
  raw = json.loads((root / "sealed_export_manifest.json").read_text(encoding="utf-8"))
  assert returned == raw, "STOP: loader return is not the raw sealed-export manifest dictionary"
  def read_jsonl(relative_path):
      return [json.loads(line) for line in (root / relative_path).read_text().splitlines() if line]

  discoveries = read_jsonl("article_discoveries.jsonl")
  observations = read_jsonl("detail_observations/historical.jsonl")
  revisions = read_jsonl("detail_revisions.jsonl")
  expected_observation_keys = {
      "schema_version", "capture_mode", "source_profile_id", "request_headers_profile_sha256",
      "run_id", "poll_seq", "record_seq", "request_observation_id", "source_article_id",
      "request_variant", "requested_url", "final_url", "http_status", "content_type",
      "raw_payload_sha256", "raw_payload_bytes", "raw_payload_relative_path",
      "trust_validation_status", "t_detail_receive_ms", "captured_at_ms",
  }
  assert all(set(row) == expected_observation_keys for row in observations), "STOP: DetailObservation schema changed"
  assert all(row["schema_version"] == "stage1_6b_detail_observation_v1" for row in observations), "STOP: DetailObservation schema version changed"
  assert all(isinstance(row.get("request_observation_id"), str) and row["request_observation_id"] for row in observations), "STOP: DetailObservation lacks a stable request_observation_id"
  assert len({row["request_observation_id"] for row in observations}) == len(observations), "STOP: duplicate DetailObservation.request_observation_id"
  expected_revision_keys = {
      "schema_version", "capture_mode", "source_profile_id", "source_article_id",
      "source_surface", "source_locale", "request_variant", "detail_revision_id",
      "detail_raw_sha256", "raw_payload_relative_path", "t_detail_trusted_ms",
      "t_raw_persisted_ms", "captured_at_ms", "record_seq",
  }
  assert all(set(row) == expected_revision_keys for row in revisions), "STOP: DetailRevision schema changed"
  assert all(row["schema_version"] == "stage1_6b_detail_revision_v1" for row in revisions)
  assert all(type(row["t_detail_trusted_ms"]) is int and 10**12 <= row["t_detail_trusted_ms"] < 10**13 for row in revisions), "STOP: exact trusted timestamp field invalid"
  assert "revision_first_observed_at_ms" not in expected_revision_keys
  assert len({row["detail_revision_id"] for row in revisions}) == len(revisions), "STOP: duplicate detail revision identity"
  tuple_paths = [row["relative_path"] for row in raw["authoritative_artifacts"]]
  required_topology = {
      "article_discoveries.jsonl", "detail_observations/historical.jsonl",
      "detail_revisions.jsonl", "historical_coverage.json", "request_manifest/historical.jsonl",
      "capture_run_contract.json", "observer_checkpoint.json", "terminal_status.json",
      "source_profile_probe_attestation.json", "list_captures/sweep_a.jsonl", "list_captures/sweep_b.jsonl",
  }
  assert required_topology <= set(tuple_paths), "STOP: real manifest artifact topology is not mappable"
  assert any(p.startswith("raw_payloads/index/") for p in tuple_paths), "STOP: index raw payload tuple missing"
  assert any(p.startswith("raw_payloads/detail/") for p in tuple_paths), "STOP: detail raw payload tuple missing"
  discovery_ids = {row["source_article_id"] for row in discoveries}
  observations_per_article = Counter(row["source_article_id"] for row in observations)
  assert set(observations_per_article) == discovery_ids, "STOP: DetailObservation/article discovery membership mismatch"
  assert all(count == 1 for count in observations_per_article.values()), "STOP: the frozen real export no longer has exactly one observation per candidate"
  observation_by_article = {row["source_article_id"]: row for row in observations}
  failures = {
      article_id: row["trust_validation_status"]
      for article_id, row in observation_by_article.items()
      if row["trust_validation_status"] != "trusted"
  }
  assert raw["export_id"] == root.name == expected_export_id
  assert __import__("hashlib").sha256((root / "sealed_export_manifest.json").read_bytes()).hexdigest() == expected_manifest_sha256
  assert len(discoveries) == 35
  assert len({row["source_article_id"] for row in discoveries}) == 35
  expected_discovery_keys = {
      "schema_version", "capture_mode", "source_profile_id", "source_article_id", "discovery_title",
      "discovery_rule_version", "first_list_capture_id", "captured_at_ms", "record_seq",
      "source_catalog_id", "source_catalog_name", "notice_lineage_first_detected_at_ms",
  }
  assert all(set(row) == expected_discovery_keys for row in discoveries)
  assert all(row["notice_lineage_first_detected_at_ms"] is None for row in discoveries)
  assert set(observation_by_article) == discovery_ids
  assert len(observations) == 35
  assert sum(row["trust_validation_status"] == "trusted" for row in observations) == 33
  assert len(revisions) == 33
  assert failures == {
      "572715f2d96e47769ebbb967c2a6e445": "network_error",
      "5150d4f0ee1546d7ae6382ba7cda3ffe": "network_error",
  }
  assert all(row["trust_validation_status"] != "pending" for row in observations)
  assert {row["source_article_id"] for row in revisions} == {
      row["source_article_id"] for row in observations if row["trust_validation_status"] == "trusted"
  }
  print({"export_id": raw["export_id"], "manifest_equal": returned == raw, "discoveries": len(discoveries), "detail_observations": len(observations), "detail_observation_schema": "stage1_6b_detail_observation_v1", "unique_request_observation_ids": len({row["request_observation_id"] for row in observations}), "one_observation_per_current_parent": True, "trusted_detail_observations": 33, "detail_revisions": len(revisions), "detail_revision_timestamp_field": "t_detail_trusted_ms", "artifact_tuple_paths": tuple_paths, "terminal_failures": failures})
  PY
  ```

  Expected: manifest equality and the frozen manifest hash; 35 unique candidate parents; exactly 35 `stage1_6b_detail_observation_v1` rows with non-empty globally unique `request_observation_id` values; and, as a fact of this one frozen export only, exactly one observation per candidate. It must also show 33 trusted observations, two terminal failures, 33 matching `stage1_6b_detail_revision_v1` parents using exact `t_detail_trusted_ms`, and no pending observation. The output records the complete manifest tuple topology and its mapping to candidate/discovery, detail, list-capture, and raw-payload classes. STOP on any difference, unmappable artifact class, missing/duplicate observation identity, missing raw index/detail tuple, or timestamp-schema drift. The one-observation-per-parent assertion is a real-export preflight fact, not a reducer rule: the generic reducer must still aggregate any number of observations per parent under Design Section 6.5.

- [ ] **Step 4: Inventory every existing consumer before introducing a new persistence profile**

  Run and record all matches:

  ```bash
  rg -n 'load_sealed_export|persist_audit_artifacts|load_completed_audit|build_stage1_6a_source_audit_summary|REQUIRED_ARTIFACT_FILENAMES|SUMMARY_FILENAME' \
    src/research/external_signal_shadow scripts/external_signal_shadow tests
  rg -n 'EXTERNAL_SIGNAL_STAGE1_6A_' configs/base.py
  rg -n 'urllib\.request|requests|httpx|aiohttp|socket|subprocess|stage1_5' \
    src/research/external_signal_shadow/stage1_6a_* scripts/external_signal_shadow/run_stage1_6a_* || true
  ```

  Expected: all 1.6B producer/client/observer/storage modules stay read-only; no existing request-manifest writer is reused or duplicated; the new work needs a separate named 1.6A artifact profile rather than changing the fixture profile. STOP if an unlisted 1.6A/1.6B consumer requires a behavior/schema change outside this Plan's allowed paths.

- [ ] **Step 5: Confirm the red baseline**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
    tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
    tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py
  ```

  Expected: PASS before implementation. A failing baseline is a STOP; diagnose it under a separate bug workflow rather than absorbing it into this adapter.

## Task 1: Build the Verified Sealed-Export Snapshot Boundary

**Design invariants:** INV-01, INV-04, INV-08, INV-10, INV-12, INV-14.

**Files:**
- Create: `src/research/external_signal_shadow/stage1_6a_sealed_export_historical_adapter.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py`
- Create: `tests/fixtures/external_signal_shadow/stage1_6a_sealed_export_adapter/valid_bapi_detail_v1.json`
- Create: `tests/fixtures/external_signal_shadow/stage1_6a_sealed_export_adapter/unknown_body_node_v1.json`
- Modify: none.

**Interfaces:**

```python
@dataclass(frozen=True)
class VerifiedArtifact:
    relative_path: str
    artifact_class: str
    sha256: str
    byte_length: int
    raw_bytes: bytes

@dataclass(frozen=True)
class VerifiedSealedExportSnapshot:
    export_dir: Path
    manifest: dict[str, Any]
    manifest_sha256: str
    artifacts: dict[str, VerifiedArtifact]
    receipt: dict[str, Any]

class AdapterInputError(ValueError):
    """The sealed export cannot enter the adapter reducer."""

def load_verified_historical_sealed_export(
    export_dir: Path, *, project_root: Path
) -> VerifiedSealedExportSnapshot: ...
```

`artifact_class` is one of `article_discoveries`, `detail_observations`, `detail_revisions`, `selected_catalog_list_captures`, `selected_catalog_raw_indexes`, `trusted_raw_bapi_details`, or `historical_coverage`. The snapshot contains only Design Section 3.4 authoritative artifacts. No later reducer API accepts a `Path` to source evidence. All input path, JSON/JSONL, tuple, schema, hash, linkage, and profile failures are wrapped as `AdapterInputError`; tests must not depend on raw `FileNotFoundError`, `JSONDecodeError`, or filesystem exception types.

- [ ] **Step 1: Write failing snapshot-boundary tests**

  In the new test module, create a test-local `build_valid_v2_export(tmp_path, fixture_dir)` that writes a minimum synthetic historical v2 export, a valid 1.6B sealed manifest with correct hashes, and the exact artifact classes above. The helper must use fixture BAPI bytes for the detail record; it must not use the user's real export or a network mock.

  Add these tests before production code:

  ```python
  def test_snapshot_calls_stage1_6b_loader_once_and_pins_same_bytes(monkeypatch, tmp_path, fixture_dir):
      export_dir = build_valid_v2_export(tmp_path, fixture_dir)
      calls = []
      real_loader = storage_6b.load_sealed_export
      monkeypatch.setattr(adapter.storage_6b, "load_sealed_export", lambda path: calls.append(path) or real_loader(path))
      snapshot = adapter.load_verified_historical_sealed_export(export_dir, project_root=tmp_path)
      assert calls == [export_dir.resolve()]
      assert snapshot.manifest["export_id"] == export_dir.name
      assert "detail_observations/historical.jsonl" in snapshot.artifacts
      assert snapshot.receipt["consumed_artifacts"] == sorted(
          snapshot.receipt["consumed_artifacts"],
          key=lambda row: (row["artifact_class"], row["relative_path"], row["sha256"]),
      )

  @pytest.mark.parametrize("candidate", [
      lambda root: root.parent / "elsewhere",
      lambda root: root.parent,
  ])
  def test_snapshot_rejects_non_export_or_escape_before_loader(monkeypatch, tmp_path, fixture_dir, candidate):
      export_dir = build_valid_v2_export(tmp_path, fixture_dir)
      opener = Mock(side_effect=AssertionError("loader must not run"))
      monkeypatch.setattr(adapter.storage_6b, "load_sealed_export", opener)
      with pytest.raises(adapter.AdapterInputError):
          adapter.load_verified_historical_sealed_export(candidate(export_dir), project_root=tmp_path)
      opener.assert_not_called()

  def test_snapshot_rejects_artifact_changed_after_1_6b_validation(monkeypatch, tmp_path, fixture_dir):
      export_dir = build_valid_v2_export(tmp_path, fixture_dir)
      real_loader = storage_6b.load_sealed_export
      def validate_then_tamper(path):
          manifest = real_loader(path)
          (path / "detail_observations/historical.jsonl").write_text(
              '{"tampered":true}\n'
          )
          return manifest
      monkeypatch.setattr(adapter.storage_6b, "load_sealed_export", validate_then_tamper)
      with pytest.raises(adapter.AdapterInputError, match="hash|size"):
          adapter.load_verified_historical_sealed_export(export_dir, project_root=tmp_path)
  ```

  Also test a symlink below the allowed historical sealed-export parent resolving to an outside file/directory, and assert rejection before the loader call.

- [ ] **Step 2: Run the snapshot tests and confirm RED**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py -k snapshot
  ```

  Expected: FAIL because `stage1_6a_sealed_export_historical_adapter` and `load_verified_historical_sealed_export` do not yet exist.

- [ ] **Step 3: Implement the smallest snapshot loader**

  Implement only the declared dataclasses and `load_verified_historical_sealed_export` in the new adapter module:

  ```python
  def load_verified_historical_sealed_export(export_dir: Path, *, project_root: Path) -> VerifiedSealedExportSnapshot:
      try:
          allowed_parent = (project_root / "data/external_signal_shadow/stage1_6b/historical_backfill").resolve()
          resolved = export_dir.resolve(strict=True)
          if (
              not resolved.is_relative_to(allowed_parent)
              or resolved.parent.name != "sealed_exports"
              or resolved.parent.parent.parent != allowed_parent
          ):
              raise AdapterInputError("sealed export must resolve under historical_backfill/<run-id>/sealed_exports")
          manifest = storage_6b.load_sealed_export(resolved)  # exactly one call
          manifest_bytes = (resolved / "sealed_export_manifest.json").read_bytes()
          if json.loads(manifest_bytes) != manifest or resolved.name != manifest.get("export_id"):
              raise AdapterInputError("sealed-export manifest authority mismatch")
          # For each declared, consumed tuple: read once, verify length/hash, parse from that byte string only.
      except AdapterInputError:
          raise
      except (OSError, ValueError) as exc:
          raise AdapterInputError("sealed-export input validation failed") from exc
  ```

  Derive the consumption list solely from the Task 0 manifest-tuple inventory. Require exactly one `detail_observations/historical.jsonl`, one historical `HistoricalCoverage` artifact, the two sweep ListCapture streams, every referenced raw index payload, and every trusted raw BAPI detail payload; reject duplicates, missing classes, paths outside the export root, invalid JSON/JSONL, or an artifact class not declared by the manifest. Catch every low-level path, JSON/JSONL, schema, hash, profile, and linkage exception at this boundary and raise `AdapterInputError` with the original exception chained; no `FileNotFoundError`, `JSONDecodeError`, `OSError`, or bare `ValueError` may escape. The snapshot must retain parsed `DetailObservation` rows from the exact hash-checked bytes so no reducer can infer detail outcome from `ArticleDiscovery` or a missing revision. Build the receipt without `raw_bytes`, and sort it exactly by `(artifact_class, relative_path, sha256)`. Do not add a second 1.6B validator or read source paths after this method returns.

  In temporary-root tests, monkeypatch only `stage1_6a_futures_delisting_storage.STAGE1_6A_OUTPUT_PARENT` where an existing 1.6A writer validates a temporary output. The production adapter must derive its input/output confinement from the explicit `project_root`; it must not depend on the process working directory.

- [ ] **Step 4: Make the snapshot tests green**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py -k snapshot \
    tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py
  ```

  Expected: PASS. `git diff -- src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py` is empty.

## Task 2: Add the Strict BAPI Detail and Parent/Child Reducer

**Design invariants:** INV-02, INV-03, INV-04, INV-05, INV-06, INV-07, INV-12, INV-13.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6a_sealed_export_historical_adapter.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py`
- Modify: `tests/fixtures/external_signal_shadow/stage1_6a_sealed_export_adapter/valid_bapi_detail_v1.json`
- Modify: `tests/fixtures/external_signal_shadow/stage1_6a_sealed_export_adapter/unknown_body_node_v1.json`

**Interfaces:**

```python
SUPPORTED_BODY_NORMALIZATION_VERSION = "stage1_6a_bapi_body_tree_v1"
SUPPORTED_SEMANTIC_EXTRACTOR_VERSION = "stage1_6a_extractor_v1"

@dataclass(frozen=True)
class SealedExportAuditResult:
    receipt: dict[str, Any]
    candidate_manifest: dict[str, Any]
    parent_outcomes: list[dict[str, Any]]
    detail_revisions: list[dict[str, Any]]
    semantic_extractions: list[dict[str, Any]]
    notices: list[dict[str, Any]]
    contracts: list[dict[str, Any]]
    diagnostics: list[dict[str, Any]]
    metrics_raw: dict[str, Any]

def reduce_verified_sealed_export(
    snapshot: VerifiedSealedExportSnapshot
) -> SealedExportAuditResult: ...

def _freeze_unique_candidates(discoveries: list[dict[str, Any]]) -> list[dict[str, Any]]: ...

def _group_parent_observations(
    observations: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]: ...

def _select_parent_revisions(
    *, trusted_observations: list[dict[str, Any]], revisions: list[dict[str, Any]], raw_details: dict[str, VerifiedArtifact]
) -> dict[str, dict[str, Any]]: ...
```

- [ ] **Step 1: Write RED tests for the BAPI authority boundary**

  Add fixtures and direct reducer tests that require all of the following:

  ```python
  def test_detail_identity_requires_data_code_not_numeric_data_id(snapshot):
      result = adapter.reduce_verified_sealed_export(snapshot)
      revision = result.detail_revisions[0]
      assert revision["source_article_id"] == "a" * 32
      assert revision["bapi_numeric_id"] == 248842

  @pytest.mark.parametrize("mutation", [
      {"node": "unknown", "child": []},
      {"node": "element", "tag": "script", "child": []},
      {"node": "root", "child": "not-an-array"},
      {"node": "text", "text": 3},
  ])
  def test_unrecognized_body_shape_is_denominator_visible_source_integrity_failure(snapshot, mutation):
      result = reduce_with_body_mutation(snapshot, mutation)
      outcome = result.parent_outcomes[0]
      assert outcome["detail_authority_status"] == "body_parse_unresolved"
      assert outcome["source_integrity_parent_pass"] is False
      assert result.metrics_raw["source_integrity_numerator"] == 0
      assert result.metrics_raw["candidate_total_denominator"] == 1
      assert result.contracts == []

  def test_terminal_network_error_is_denominator_visible(snapshot):
      unavailable = adapter.reduce_verified_sealed_export(with_terminal_network_error(snapshot))
      assert unavailable.parent_outcomes[0]["detail_authority_status"] == "detail_unavailable"
      assert unavailable.parent_outcomes[0]["source_integrity_parent_pass"] is False

  def test_network_error_then_trusted_observation_produces_trusted_parent(snapshot):
      result = adapter.reduce_verified_sealed_export(
          with_parent_observations(snapshot, ["network_error", "trusted"])
      )
      assert result.parent_outcomes[0]["detail_authority_status"] == "trusted"
      assert result.parent_outcomes[0]["source_integrity_parent_pass"] is True

  def test_trusted_then_network_error_does_not_downgrade_parent(snapshot):
      result = adapter.reduce_verified_sealed_export(
          with_parent_observations(snapshot, ["trusted", "network_error"])
      )
      assert result.parent_outcomes[0]["detail_authority_status"] == "trusted"
      assert result.parent_outcomes[0]["source_integrity_parent_pass"] is True

  def test_two_trusted_observations_same_raw_hash_share_one_revision(snapshot):
      result = adapter.reduce_verified_sealed_export(
          with_two_trusted_observations_same_raw_hash(snapshot)
      )
      assert len(result.detail_revisions) == 1

  def test_two_trusted_observations_distinct_raw_hashes_feed_multi_revision_selection(snapshot):
      result = adapter.reduce_verified_sealed_export(
          with_two_trusted_observations_distinct_raw_hashes(snapshot)
      )
      assert len(result.detail_revisions) == 2
      assert selected_revision_id(result) == EXPECTED_MAX_TUPLE_REVISION_ID

  def test_trusted_observation_without_revision_rejects_export(snapshot):
      with pytest.raises(adapter.AdapterInputError, match="trusted.*revision|linkage"):
          adapter.reduce_verified_sealed_export(with_missing_trusted_revision(snapshot))

  def test_revision_without_trusted_observation_rejects_export(snapshot):
      with pytest.raises(adapter.AdapterInputError, match="orphan.*revision|linkage"):
          adapter.reduce_verified_sealed_export(with_orphan_detail_revision(snapshot))

  def test_duplicate_request_observation_id_rejects_export(snapshot):
      with pytest.raises(adapter.AdapterInputError, match="request_observation_id|duplicate"):
          adapter.reduce_verified_sealed_export(with_duplicate_request_observation_id(snapshot))

  def test_unresolved_observation_without_trusted_detail_rejects_export(snapshot):
      with pytest.raises(adapter.AdapterInputError, match="pending|unresolved|observation"):
          adapter.reduce_verified_sealed_export(with_unresolved_nontrusted_observation(snapshot))

  def test_linked_malformed_envelope_is_denominator_visible_but_wrong_present_data_code_rejects_export(snapshot):
      malformed = adapter.reduce_verified_sealed_export(with_missing_data_object(snapshot))
      assert malformed.parent_outcomes[0]["detail_authority_status"] == "malformed_bapi_envelope"
      assert malformed.parent_outcomes[0]["source_integrity_parent_pass"] is False
      with pytest.raises(adapter.AdapterInputError, match="data\.code|identity"):
          adapter.reduce_verified_sealed_export(with_wrong_present_data_code(snapshot))

  @pytest.mark.parametrize("bad_release_date", [None, True, 0, -1, 1_758_098_727, 1.0, "1758098727976", 10**13])
  def test_missing_or_invalid_selected_catalog_release_date_rejects_export(snapshot, bad_release_date):
      with pytest.raises(adapter.AdapterInputError, match="selected catalog.*article|releaseDate"):
          adapter.reduce_verified_sealed_export(with_catalog_release_date(snapshot, bad_release_date))

  def test_candidate_missing_from_selected_catalog_raw_index_rejects_export(snapshot):
      with pytest.raises(adapter.AdapterInputError, match="selected catalog.*article|discovery.*linkage"):
          adapter.reduce_verified_sealed_export(without_catalog_article(snapshot))

  def test_publication_corroboration_uses_only_article_discovery_first_list_capture(snapshot):
      result = adapter.reduce_verified_sealed_export(
          with_first_and_later_capture_dates(snapshot, first=1_758_098_727_976, later=1_758_098_727_977)
      )
      assert result.parent_outcomes[0]["publication_time_status"] == "present"
      assert result.notices[0]["source_published_at_ms"] == 1_758_098_727_976

  @pytest.mark.parametrize("mutation", ["missing_first_list_capture", "duplicate_first_list_capture", "missing_first_index_raw", "first_capture_article_missing"])
  def test_first_list_capture_release_date_chain_is_structural_and_fail_closed(snapshot, mutation):
      with pytest.raises(adapter.AdapterInputError, match="first_list_capture_id|releaseDate|linkage"):
          adapter.reduce_verified_sealed_export(mutate_first_capture_chain(snapshot, mutation))

  def test_publication_time_uses_detail_publish_date_and_catalog_is_only_corroboration(snapshot):
      result = adapter.reduce_verified_sealed_export(snapshot)
      assert result.notices[0]["source_published_at_ms"] == 1_758_098_727_976
      assert result.notices[0]["source_published_at_source"] == "detail_data_publishDate"

  def test_publication_conflict_fails_source_integrity_and_never_enters_event_days(snapshot):
      result = reduce_with_release_date(snapshot, 1_758_098_727_977)
      assert result.parent_outcomes[0]["publication_time_status"] == "conflicting"
      assert result.parent_outcomes[0]["source_integrity_parent_pass"] is False
      assert result.notices[0]["source_published_at_ms"] is None

  @pytest.mark.parametrize("publish_date", [None, True, 0, -1, 1_758_098_727, 1.0, "1758098727976", 10**13])
  def test_unparseable_publish_date_is_not_envelope_rejection_or_source_integrity_failure(snapshot, publish_date):
      result = adapter.reduce_verified_sealed_export(with_publish_date(snapshot, publish_date))
      outcome = result.parent_outcomes[0]
      assert outcome["publication_time_status"] == "unparseable"
      assert outcome["source_integrity_parent_pass"] is True
      assert result.notices[0]["source_published_at_ms"] is None
      assert result.metrics_raw["event_days"] == 0

  def test_historical_output_never_claims_pit_or_replay_authority(snapshot):
      result = adapter.reduce_verified_sealed_export(snapshot)
      assert result.semantic_extractions[0]["system_available_at_ms"] is None
      assert result.semantic_extractions[0]["fact_available_at_ms"] is None
      assert result.semantic_extractions[0]["capture_time_status"] == "historical_unknown"
      assert result.semantic_extractions[0]["point_in_time_replay_eligible"] is False

  def test_equivalent_duplicate_discoveries_collapse_before_any_detail_outcome(snapshot):
      result = adapter.reduce_verified_sealed_export(with_equivalent_duplicate_discovery(snapshot))
      assert result.metrics_raw["candidate_total_denominator"] == 1
      assert len(result.candidate_manifest["items"]) == 1

  def test_conflicting_duplicate_discoveries_reject_before_semantic_reduction(snapshot):
      with pytest.raises(adapter.AdapterInputError, match="duplicate.*discovery"):
          adapter.reduce_verified_sealed_export(with_conflicting_duplicate_discovery(snapshot))

  def test_parent_revision_selection_is_maximum_trusted_time_then_raw_sha_and_input_order_independent(snapshot):
      forward = adapter.reduce_verified_sealed_export(with_two_trusted_revisions(snapshot, reverse=False))
      reverse = adapter.reduce_verified_sealed_export(with_two_trusted_revisions(snapshot, reverse=True))
      assert selected_revision_id(forward) == selected_revision_id(reverse) == EXPECTED_MAX_TUPLE_REVISION_ID
      assert {row["detail_revision_id"] for row in forward.detail_revisions} == {REVISION_A, REVISION_B}

  def test_semantically_equivalent_trusted_revisions_do_not_create_conflict(snapshot):
      result = adapter.reduce_verified_sealed_export(with_equivalent_two_trusted_revisions(snapshot))
      assert result.parent_outcomes[0]["parent_declaration_status"] == "complete"
      assert result.parent_outcomes[0]["mapping_status"] == "pass"

  @pytest.mark.parametrize("conflict", ["symbol_set", "product_family", "same_present_schedule_fact"])
  def test_cross_revision_conflict_fails_mapping_and_classification_without_cherry_pick(snapshot, conflict):
      result = adapter.reduce_verified_sealed_export(with_revision_conflict(snapshot, conflict))
      outcome = result.parent_outcomes[0]
      assert outcome["parent_declaration_status"] == "revision_conflicting"
      assert outcome["mapping_status"] == "fail"
      assert outcome["event_type_classification_status"] == "unresolved"
      assert result.contracts == []
      assert len(result.detail_revisions) == 2
  ```

  Include valid-tree coverage for root/text/allowed elements, `br` line breaks, block boundaries, CR-to-LF, NFKC, whitespace collapse, empty text omission, JSON-pointer and normalized text-span evidence. Assert all traversal is ascending array order. Add denominator-visible malformed-envelope cases for missing `data`, absent/non-string `data.code`, non-string `body`, and missing/empty `title`; each uses `publication_time_status="not_evaluable"`. Add structural input-export rejection cases for a present mismatched `data.code`, missing raw hash linkage, wrong detail revision linkage, trusted observation without a revision, revision without trusted observation, duplicate `request_observation_id`, and every broken `ArticleDiscovery.first_list_capture_id -> ListCapture -> index raw -> article -> releaseDate` link. The later-capture mutation must prove that it cannot alter first-capture corroboration. Separately cover missing, null, bool, zero, negative, seconds, float, string, and out-of-range **detail** `publishDate` as a valid linked parent with `fact_parse_status=unparseable`, no `event_days` contribution, and no automatic source-integrity failure. Every path/JSON/schema/hash/linkage rejection in this task must assert `AdapterInputError`, not its `ValueError` base class. The Task 5 runner RED must pass one structural-linkage-invalid fixture and assert that neither `parent_audit_outcomes.jsonl` nor an output root is produced.

- [ ] **Step 2: Run the reducer tests and confirm RED**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py
  ```

  Expected: FAIL because `reduce_verified_sealed_export`, frozen candidate de-duplication, deterministic revision selection, and the strict parser do not yet exist. This whole-module RED command must run every newly added BAPI, duplicate, revision, conflict, and historical-authority test before implementation.

- [ ] **Step 3: Implement the strict reducer in the new adapter module**

  Add private helpers in the same module, not a new parser framework:

  ```python
  def _parse_bapi_detail(raw: bytes, expected_article_id: str) -> tuple[dict[str, Any] | None, str | None]: ...
  def _normalize_bapi_body_tree(body_json: str) -> tuple[str, list[dict[str, Any]]]: ...
  def _reduce_parent(... ) -> tuple[dict[str, Any], list[dict[str, Any]], ...]: ...
  ```

  First validate trusted observation/revision/raw identity, SHA/path, request variant, profile, and canonical `en` provenance. Any contradiction raises `AdapterInputError` before parent reduction. `_parse_bapi_detail` then returns `(payload, None)` for a well-formed semantic envelope or `(None, "malformed_bapi_envelope")` for malformed bytes after that trusted chain is established; it must not reclassify malformed payload quality as an evidence-link failure. A present string `data.code` unequal to `expected_article_id` raises `AdapterInputError`. An absent/non-string `data.code`, missing/non-object `data`, missing/empty `data.title`, or non-string `data.body` returns the malformed-envelope status and `publication_time_status="not_evaluable"`. Preserve `data.id` only as `bapi_numeric_id` if `type(data.id) is int`. Preserve raw `data.publishDate` without range/type validation here; the dedicated publication reducer alone applies `type(value) is int and not bool and 10**12 <= value < 10**13`, otherwise records `fact_parse_status="unparseable"`, no timestamp, and no `event_days` contribution.

  `_normalize_bapi_body_tree` accepts exactly the Design Section 6.3 grammar: root keys exactly `{node, child}`, element keys limited to `{node, tag, attr, child}`, allowed tags only `a, br, em, h3, h4, li, p, span, strong, table, tbody, td, tr, u, ul`, text keys exactly `{node, text}`, and opaque dict-only `attr`. Reject unknown keys/node/tag, non-list child, or non-string text. Traverse child arrays in input order. Normalize with CR-to-LF, `unicodedata.normalize("NFKC", ...)`, horizontal whitespace collapse, trimming around newlines, collapsing repeated newlines, and final strip.

  Before reading any `DetailObservation`, call `_freeze_unique_candidates` on the imported `ArticleDiscovery` rows. Group by `source_article_id`, then compare this immutable membership projection exactly:

  ```python
  (
      row["schema_version"], row["source_article_id"], row["discovery_title"], row["first_list_capture_id"],
      row["discovery_rule_version"], row["source_catalog_id"], row["source_catalog_name"],
      row["capture_mode"], row["source_profile_id"],
  )
  ```

  Task 0 must first confirm this exact source-row key set against the selected export. One row is accepted. Equivalent duplicates collapse to one lexicographically sorted candidate. Any conflicting projection rejects the input export before detail linkage, body parsing, output creation, or metric computation. `record_seq`, `captured_at_ms`, and the observed-null `notice_lineage_first_detected_at_ms` are transport/adapter metadata and are not membership fields. After de-duplication, retain `notice_lineage_first_detected_at_ms=None` and derive `source_export_id=snapshot.manifest["export_id"]`; neither participates in source-row equivalence.

  Before every publication reduction, resolve `ArticleDiscovery.first_list_capture_id` to exactly one ListCapture and its exact verified raw index tuple, then find the matching selected-catalog article and validate `releaseDate`. No later capture is an authority. Any failure in this chain raises `AdapterInputError` before parent reduction. Reduce **every frozen unique candidate** into one parent outcome. First group every parsed `DetailObservation` by `source_article_id`; never construct `observation_by_article` with last-write-wins semantics. Reject globally missing/duplicate `request_observation_id` before grouping. For each parent, form its trusted subset. If it is non-empty, establish transport-level detail authority as trusted; retain every non-trusted observation only as diagnostic, and validate every trusted observation's same-article `DetailRevision` and verified raw BAPI artifact. If it is empty and all observations have an explicitly recognized terminal non-trusted status, emit denominator-visible `detail_unavailable` with `publication_time_status="not_evaluable"`. An unknown, pending, or unresolved non-trusted status without a trusted observation raises `AdapterInputError`; never silently classify it as terminal. Validate the relation in both directions: every trusted observation must have exactly one logical matching revision/raw tuple, and every DetailRevision must have at least one matching trusted observation. Link each raw detail, detail observation, detail revision, and BAPI envelope by the same article ID, raw SHA/path, request variant, profile, and canonical `en` authority. A missing required stream, missing trusted revision, orphan revision, raw hash/path mismatch, contradictory provenance, or wrong present string `data.code` raises `AdapterInputError` before semantic reduction and produces no artifacts/metrics. Only no-trusted terminal observations, record/hash-linked malformed envelope, `body_parse_unresolved`, and publication conflict retain the frozen parent, set `source_integrity_parent_pass=false`, emit no eligible child, and record a diagnostic. An unparseable `publishDate` remains explicit but does not itself rewrite `source_integrity_parent_pass`.

  Only after observation aggregation and bidirectional linkage validation may `_select_parent_revisions` retain every linked trusted revision in `detail_revisions.jsonl`, reduce each revision with the same strict body/published-time semantics, and select the parent-level revision by `max(t_detail_trusted_ms, detail_raw_sha256)`, never observation/file order or parse convenience. Multiple trusted observations with the same raw SHA share one logical revision; distinct trusted raw SHA values require distinct revision rows and enter this selection/conflict reducer. Compare all trusted revisions before deciding parent completeness. A difference in declared symbol set, product-family classification, or any same present schedule fact yields `parent_declaration_status="revision_conflicting"`, `mapping_status="fail"`, and `event_type_classification_status="unresolved"`; no revision is cherry-picked to emit a child. A semantically equivalent multi-revision parent selects the max tuple without conflict. The source-integrity numerator may remain true only when its separate Section 8 predicate is satisfied.

  Before reducing any detail publication fact, locate the same `article.code == source_article_id` in the exact verified selected-catalog raw-index/list-capture pair. Its `releaseDate` must satisfy `type(value) is int and not bool and 10**12 <= value < 10**13`; a missing article or invalid catalog `releaseDate` raises an input-export validation error before any parent outcome/metric/output exists. Only after that discovery-linkage gate, reuse the existing Stage 1.6A schedule and product-family reducers through their public functions; do not edit `stage1_6a_futures_delisting_audit.py`. Construct publication facts from detail `data.publishDate` and use the validated catalog `releaseDate` only as exact-int corroboration. Preserve every required parent/child completeness rule: a mixed, incomplete, unresolved, or mapping-failed parent emits no eligible subset. Optional schedule-fact unparseability remains explicit and does not by itself rewrite `source_integrity_parent_pass`.

  Construct semantic identities deterministically from linked revision identity, supported extractor/normalization versions, and canonical facts. Never include extraction time. Set all historical PIT/fact availability timestamps to `None`, `capture_time_status="historical_unknown"`, and replay eligibility to `False`.

- [ ] **Step 4: Make reducer and original fixture regressions green**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py
  ```

  Expected: PASS. The original model/audit source and test files have zero diff.

## Task 3: Compute Frozen Metrics and a Real-Adapter Summary Without Authority Leakage

**Design invariants:** INV-02, INV-05, INV-06, INV-07, INV-11, INV-12, INV-13, INV-14.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6a_sealed_export_historical_adapter.py`
- Modify: `src/research/external_signal_shadow/stage1_6a_futures_delisting_summary.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py`

**Interfaces:**

```python
def build_sealed_export_source_audit_summary(
    audit_result: SealedExportAuditResult, *, run_id: str
) -> dict[str, Any]: ...

def evaluate_source_audit_candidate(summary: dict[str, Any]) -> bool: ...
```

The fixture-only `build_stage1_6a_source_audit_summary()` remains unchanged in behavior and continues to cap `source_audit_passed=false`.

- [ ] **Step 1: Write RED metric and summary tests**

  Add direct tests for the exact metric populations:

  ```python
  def test_body_parse_unresolved_stays_in_source_integrity_denominator_and_fails_numerator(snapshot):
      summary = summary_mod.build_sealed_export_source_audit_summary(
          adapter.reduce_verified_sealed_export(malformed_body_snapshot(snapshot)), run_id="run"
      )
      assert summary["metrics"]["source_integrity_denominator"] == 1
      assert summary["metrics"]["source_integrity_numerator"] == 0
      assert summary["metrics"]["source_integrity_pass_rate"] == 0.0

  def test_batch_with_one_unmapped_declared_contract_fails_notice_level_mapping(snapshot):
      summary = build_summary_for_incomplete_batch(snapshot)
      assert summary["metrics"]["symbol_mapping_denominator"] == 1
      assert summary["metrics"]["symbol_mapping_numerator"] == 0
      assert summary["metrics"]["historical_events_found"] == 0

  def test_summary_preserves_historical_denominators_and_has_no_pit_or_trade_authority(snapshot):
      summary = build_valid_summary(snapshot)
      assert summary["source_audit_passed"] is False
      assert summary["source_audit_evidence_candidate_passed"] in {True, False}
      assert summary["point_in_time_source_validated"] is False
      assert summary["market_data_coverage_passed"] is False
      assert summary["risk_veto_candidate"] is False
      assert summary["replay_allowed"] is False
      assert summary["trade_signal_allowed"] is False
      assert summary["paper_trading_allowed"] is False
      assert summary["live_trading_allowed"] is False
      assert summary["execution_engine_allowed"] is False

  def test_summary_rejects_reinterpretation_if_config_snapshot_changes(monkeypatch, snapshot):
      summary = build_valid_summary(snapshot)
      monkeypatch.setattr(base_config, "EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS", 31)
      assert summary_mod.evaluate_source_audit_candidate(summary) is False

  def test_failed_candidate_emits_no_next_stage_design_action(snapshot):
      summary = build_failing_summary(snapshot)
      assert summary["source_audit_evidence_candidate_passed"] is False
      assert summary["source_audit_passed"] is False
      assert summary["allowed_next_action"] == "pending_completion"
      assert summary["permitted_design_options"] == []

  def test_exact_threshold_sample_is_candidate_pass_but_summary_has_no_final_action(tmp_path):
      result = build_complete_result(parent_count=30, utc_event_days=10, symbols={"AAAUSDT", "BBBUSDT", "CCCUSDT"})
      summary = summary_mod.build_sealed_export_source_audit_summary(result, run_id="threshold")
      assert summary["source_audit_evidence_candidate_passed"] is True
      assert summary["source_audit_passed"] is False
      assert summary["allowed_next_action"] == "pending_completion"
      assert summary["permitted_design_options"] == []
      completion = storage.persist_sealed_export_audit_artifacts(tmp_path / "audit", result, summary, run_id="threshold")
      assert json.loads(completion.read_text())["source_audit_passed"] is True
      assert json.loads(completion.read_text())["allowed_next_action"] == "write_live_source_observation_design_only"
      assert json.loads(completion.read_text())["permitted_design_options"] == ["write_live_source_observation_design_only", "write_ex_post_diagnostic_design_only"]

  def test_forbidden_payload_count_is_rebuilt_from_distinct_observation_diagnostics(snapshot):
      result = reduce_with_forbidden_attempts(snapshot, observation_ids=["obs-a", "obs-a", "obs-b"])
      summary = summary_mod.build_sealed_export_source_audit_summary(result, run_id="forbidden")
      assert summary["metrics"]["forbidden_payload_count"] == 2
      assert all(row["diagnostic_type"] == "forbidden_semantic_authority_attempt" for row in result.diagnostics)
  ```

  Include independent tests that: one batch notice is one `historical_events_found`; `event_days` uses valid, non-conflicting `data.publishDate` UTC dates; symbols count only eligible complete-parent child contracts; forbidden payloads stay zero unless prohibited semantic authority was attempted; `forbidden_payload_count` is exactly the distinct `request_observation_id` count from durable forbidden-attempt diagnostics rather than a parent boolean; source/mapping/classification denominators are decided before the corresponding outcome; and one less than each frozen sample threshold cannot produce a candidate pass.

- [ ] **Step 2: Run the summary tests and confirm RED**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py -k 'metric or summary or denominator'
  ```

  Expected: FAIL because the real-adapter summary API does not exist and the fixture summary cannot satisfy its distinct semantic contract.

- [ ] **Step 3: Add the smallest separate real-adapter summary builder**

  In `stage1_6a_futures_delisting_summary.py`, add `build_sealed_export_source_audit_summary` and `evaluate_source_audit_candidate`; do not change the fixture builder's field meanings. The new builder must calculate:

  ```python
  source_integrity_pass_rate = source_integrity_numerator / source_integrity_denominator
  symbol_mapping_pass_rate = symbol_mapping_numerator / symbol_mapping_denominator
  event_type_classification_pass_rate = classification_numerator / classification_denominator
  ```

  `source_integrity_numerator` counts only parents satisfying the full Design Section 8 `source_integrity_parent_pass` predicate. In particular, `body_parse_unresolved` is excluded from this numerator even when raw bytes/hash/provenance are valid. Source integrity denominator is every candidate parent. Mapping/classification use the Design's trusted-detail parent populations, but neither drops unresolved parents from the frozen manifest. The source-schema integrity predicate must additionally require `available_at_policy_defined=true`; its meaning is historical-only and does not populate any PIT timestamp.

  Store exactly these seven consumed `EXTERNAL_SIGNAL_STAGE1_6A_*` values and `audit_metric_definition_version="stage1_6a_audit_metric_v1"` in `threshold_snapshot`: `MIN_HISTORICAL_EVENTS`, `MIN_EVENT_DAYS`, `MIN_SYMBOLS_WITH_EVENTS`, `MIN_SOURCE_INTEGRITY_RATIO`, `MIN_SYMBOL_MAPPING_RATIO`, `MIN_EVENT_TYPE_CLASSIFICATION_RATIO`, and `MAX_FORBIDDEN_PAYLOAD_COUNT`. Do not store `MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES`. `evaluate_source_audit_candidate` returns false unless the currently imported config exactly matches that key/value set, supported versions match, source-schema integrity/mapping/classification predicates pass, sample sufficiency passes, and forbidden count is within the existing threshold. Do not add an input-validity term to this metric predicate: verified sealed input is the producer precondition.

  The summary must contain `artifact_profile_version="stage1_6a_sealed_export_source_audit_v1"`, `implementation_scope="sealed_export_historical_source_audit_adapter"`, `fixture_run=false`, `audit_summary_state="pre_completion"`, `source_audit_evidence_candidate_passed`, and **always** `source_audit_passed=false`, `allowed_next_action="pending_completion"`, and `permitted_design_options=[]`. It must never serialize a final next-stage action. All non-source authorities remain present and exact false/not-evaluable exactly as the Design requires.

- [ ] **Step 4: Make summary tests green**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py -k 'metric or summary or denominator' \
    tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py
  ```

  Expected: PASS. The original fixture runner test remains zero-diff and continues to prove its permanent false cap.

## Task 4: Persist the Adapter Profile and Add an Independent Completed Consumer

**Design invariants:** INV-01, INV-08, INV-09, INV-11, INV-12, INV-14.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py`
- Modify: `src/research/external_signal_shadow/stage1_6a_sealed_export_historical_adapter.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py`

**Interfaces:**

```python
SEALED_EXPORT_AUDIT_REQUIRED_ARTIFACT_FILENAMES = (
    "source_export_receipt.json", "audit_candidate_manifest.json",
    "parent_audit_outcomes.jsonl", "detail_revisions.jsonl",
    "semantic_extractions.jsonl", "delisting_notices.jsonl",
    "delisting_contracts.jsonl", "audit_diagnostics.jsonl",
    "stage1_6a_futures_delisting_source_audit_summary.json",
)

def persist_sealed_export_audit_artifacts(
    output_root: Path, audit_result: SealedExportAuditResult,
    summary_dict: dict[str, Any], *, run_id: str
) -> Path: ...

def load_completed_sealed_export_audit_artifacts(output_root: Path) -> dict[str, Any]: ...

def load_completed_sealed_export_source_audit(
    output_root: Path, *, sealed_export: Path, project_root: Path
) -> dict[str, Any]: ...

def authority_projection(artifact_name: str, value: Any) -> Any: ...

def rebuild_metrics_from_derived_artifacts(
    *, candidate_manifest: dict[str, Any], parent_outcomes: list[dict[str, Any]],
    notices: list[dict[str, Any]], contracts: list[dict[str, Any]], diagnostics: list[dict[str, Any]],
    threshold_snapshot: dict[str, Any]
) -> dict[str, Any]: ...
```

`load_completed_sealed_export_audit_artifacts` validates only local completion/hashes/pre-completion summary shape. `load_completed_sealed_export_source_audit` is in the adapter module and adds receipt source snapshot reconstruction, deterministic reduction, metrics/predicate exact comparison, and authority checks without creating an output root.

`authority_projection` removes only these non-authoritative run-metadata fields before deterministic replay comparison:

```text
semantic_extractions.jsonl row: semantic_extracted_at_ms, audit_run_id
summary: run_id
completion_manifest.json: run_id, completed_at
```

No other timestamp, identity, source/revision/raw hash, fact/evidence pointer, parent/child status, metric, predicate, or safety-authority field may be removed. A local output path is never serialized as authority and is not a comparison field.

- [ ] **Step 1: Write RED persistence and consumer tests**

  Add tests for the new profile only; retain all old storage tests unchanged:

  ```python
  def test_adapter_summary_cannot_claim_final_pass_before_completion(tmp_path, result, summary):
      completion = storage.persist_sealed_export_audit_artifacts(tmp_path / "audit", result, summary, run_id="r")
      persisted_summary = json.loads((completion.parent / storage.SUMMARY_FILENAME).read_text())
      manifest = json.loads(completion.read_text())
      assert persisted_summary["source_audit_passed"] is False
      assert persisted_summary["allowed_next_action"] == "pending_completion"
      assert persisted_summary["permitted_design_options"] == []
      assert manifest["source_audit_passed"] in {True, False}

  def test_crash_after_summary_before_completion_is_not_consumable(monkeypatch, tmp_path, result, summary, sealed_export):
      monkeypatch.setattr(storage, "write_atomic_json", fail_only_when_writing_completion_manifest)
      with pytest.raises(OSError):
          storage.persist_sealed_export_audit_artifacts(tmp_path / "audit", result, summary, run_id="r")
      assert (tmp_path / "audit" / storage.SUMMARY_FILENAME).exists()
      assert json.loads((tmp_path / "audit" / storage.SUMMARY_FILENAME).read_text())["source_audit_passed"] is False
      with pytest.raises(ValueError):
          adapter.load_completed_sealed_export_source_audit(
              tmp_path / "audit", sealed_export=sealed_export, project_root=tmp_path
          )

  @pytest.mark.parametrize("tamper", ["source_export_receipt.json", "parent_audit_outcomes.jsonl", "detail_revisions.jsonl"])
  def test_completed_consumer_rejects_local_hash_tampering(tmp_path, completed_adapter_root, sealed_export, tamper):
      (completed_adapter_root / tamper).write_text("tampered")
      with pytest.raises(ValueError, match="Hash mismatch"):
          adapter.load_completed_sealed_export_source_audit(completed_adapter_root, sealed_export=sealed_export, project_root=tmp_path)

  def test_completed_consumer_replays_source_bytes_and_rejects_persisted_metric_lie(tmp_path, completed_adapter_root, sealed_export):
      mutate_json(completed_adapter_root / storage.SUMMARY_FILENAME, "source_integrity_numerator", 999)
      repair_local_hash_in_completion_manifest(completed_adapter_root)
      with pytest.raises(ValueError, match="replay|metric"):
          adapter.load_completed_sealed_export_source_audit(completed_adapter_root, sealed_export=sealed_export, project_root=tmp_path)

  def test_completed_consumer_rejects_precompletion_action_or_final_manifest_action_mismatch(tmp_path, completed_failing_adapter_root, sealed_export):
      mutate_json(completed_failing_adapter_root / storage.SUMMARY_FILENAME, "allowed_next_action", "source_audit_failed_or_inconclusive")
      mutate_json(completed_failing_adapter_root / storage.SUMMARY_FILENAME, "permitted_design_options", ["live_source_observation"])
      repair_local_hash_in_completion_manifest(completed_failing_adapter_root)
      with pytest.raises(ValueError, match="allowed_next_action|completion action"):
          adapter.load_completed_sealed_export_source_audit(
              completed_failing_adapter_root, sealed_export=sealed_export, project_root=tmp_path
          )

  def test_persistence_rebuild_rejects_metric_summary_that_disagrees_with_durable_parent_rows(tmp_path, result, summary):
      summary["metrics"]["source_integrity_numerator"] = 35
      summary["metrics"]["source_integrity_pass_rate"] = 1.0
      with pytest.raises(ValueError, match="durable.*metric|rebuild"):
          storage.persist_sealed_export_audit_artifacts(tmp_path / "audit", result, summary, run_id="r")
      assert not (tmp_path / "audit" / "completion_manifest.json").exists()

  def test_completed_consumer_rejects_unknown_semantic_version(tmp_path, completed_adapter_root, sealed_export):
      mutate_json(completed_adapter_root / storage.SUMMARY_FILENAME, "body_normalization_version", "v99")
      repair_local_hash_in_completion_manifest(completed_adapter_root)
      with pytest.raises(ValueError, match="version"):
          adapter.load_completed_sealed_export_source_audit(completed_adapter_root, sealed_export=sealed_export, project_root=tmp_path)

  def test_completed_consumer_accepts_later_replay_when_only_allowed_run_metadata_differs(tmp_path, completed_adapter_root, sealed_export, monkeypatch):
      monkeypatch.setattr(adapter, "utc_now_ms", lambda: ORIGINAL_EXTRACTION_MS + 60_000)
      accepted = adapter.load_completed_sealed_export_source_audit(completed_adapter_root, sealed_export=sealed_export, project_root=tmp_path)
      assert accepted["completion_manifest"]["status"] == "complete"

  def test_completed_consumer_rejects_authority_field_even_if_only_metadata_is_ignored(tmp_path, completed_adapter_root, sealed_export):
      mutate_jsonl_row(completed_adapter_root / "semantic_extractions.jsonl", 0, "detail_raw_sha256", "0" * 64)
      repair_local_hash_in_completion_manifest(completed_adapter_root)
      with pytest.raises(ValueError, match="replay|authority"):
          adapter.load_completed_sealed_export_source_audit(completed_adapter_root, sealed_export=sealed_export, project_root=tmp_path)

  def test_completed_consumer_requires_the_exact_receipted_sealed_export(tmp_path, completed_adapter_root, sealed_export, fixture_dir):
      wrong_export = build_valid_v2_export(tmp_path / "wrong", fixture_dir)
      with pytest.raises(ValueError, match="export_id|manifest|receipt"):
          adapter.load_completed_sealed_export_source_audit(
              completed_adapter_root, sealed_export=wrong_export, project_root=tmp_path
          )

  def test_completed_consumer_constructs_one_verified_snapshot(monkeypatch, tmp_path, completed_adapter_root, sealed_export):
      calls = 0
      real_loader = adapter.storage_6b.load_sealed_export
      def counted_loader(path):
          nonlocal calls
          calls += 1
          return real_loader(path)
      monkeypatch.setattr(adapter.storage_6b, "load_sealed_export", counted_loader)
      adapter.load_completed_sealed_export_source_audit(
          completed_adapter_root, sealed_export=sealed_export, project_root=tmp_path
      )
      assert calls == 1
  ```

  Include source-binding tests for: caller path outside the historical sealed-export family, wrong caller export ID, matching export ID with mismatched manifest hash, and receipt consumed-tuple mismatch. Assert no glob, `latest`, export-ID search, parent-root scan, or hardcoded source path occurs. Include receipt mutation tests for export ID, manifest hash, and consumed tuple sort/order/hash/length. Include an input export mutation after adapter completion: repair neither 1.6B manifest nor receipt, then require completed consumer rejection when it rebuilds its verified snapshot. Add a deterministic same-input/two-output test that exact-compares authority records and metric populations while allowing only run metadata/path timestamps to differ.

- [ ] **Step 2: Run persistence tests and confirm RED**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py -k 'completion or consumer or receipt or replay'
  ```

  Expected: FAIL because no separate sealed-export persistence profile/consumer exists.

- [ ] **Step 3: Implement a separate artifact profile using existing atomic helpers**

  Keep `REQUIRED_ARTIFACT_FILENAMES`, `persist_audit_artifacts`, and `load_completed_audit` behavior intact. In the same storage module, add the explicitly named `SEALED_EXPORT_AUDIT_REQUIRED_ARTIFACT_FILENAMES`, `persist_sealed_export_audit_artifacts`, and `load_completed_sealed_export_audit_artifacts`; they must reuse `validate_output_root_path`, `write_atomic_json`, `write_append_jsonl`, and `compute_file_sha256` rather than add a second writer implementation.

  Write exactly the nine pre-completion artifacts listed by the interface. The receipt is JSON; derived collections are canonical JSONL in deterministic order. Copy the supplied summary, force `artifact_profile_version="stage1_6a_sealed_export_source_audit_v1"`, `audit_summary_state="pre_completion"`, `source_audit_passed=false`, `allowed_next_action="pending_completion"`, and `permitted_design_options=[]`, then hash every authoritative artifact. Before writing a completion manifest, reread the durable candidate manifest, parent outcomes, derived revisions, extractions, notices, contracts, diagnostics, and summary bytes; call one pure `rebuild_metrics_from_derived_artifacts(...)`; and require exact equality for candidate membership/count/hash, every metric numerator/denominator/rate, `historical_events_found`, `event_days`, `symbols_with_events`, distinct forbidden-observation count, component predicates, and `source_audit_evidence_candidate_passed`. Any mismatch raises before the manifest write. The completion manifest contains only hashes of pre-completion artifacts (never itself), input receipt/manifest identity, count fields, `artifact_profile_version`, `status="complete"`, final `source_audit_passed=evaluate_source_audit_candidate(rebuilt_summary)`, and final action derived only from the Parent Stage 1.6A table: pass with PIT false is `write_live_source_observation_design_only` plus `["write_live_source_observation_design_only", "write_ex_post_diagnostic_design_only"]`; failure is `source_audit_failed_or_inconclusive` plus `[]`. Any failure before this final atomic write leaves the root non-consumable.

  `load_completed_sealed_export_audit_artifacts` must require the exact artifact set, verify each hash, require summary pre-completion state and `source_audit_passed=false`, and return parsed local artifacts. It must not accept the fixture profile. In the adapter module, implement `load_completed_sealed_export_source_audit` to:

  1. validate local profile/hashes;
  2. reject unsupported exact versions and a changed threshold snapshot;
  3. construct exactly one `snapshot = load_verified_historical_sealed_export(sealed_export, project_root=project_root)`; that one construction performs Section 3.1 confinement and the sole `load_sealed_export()` call. Exact-bind `snapshot` basename, manifest hash/identity/profile/range/coverage fields, and consumed tuple set to the receipt. Do not pre-call `load_sealed_export()` or reopen a second snapshot;
  4. rerun `reduce_verified_sealed_export` and `build_sealed_export_source_audit_summary`;
  5. require summary action fields to remain exactly `pending_completion` / `[]`; derive the expected **final** action from `completion_manifest.source_audit_passed`, require it to equal the completion manifest action fields, then exact-compare `authority_projection(...)` of candidate manifest, parent outcomes, revisions, extractions, notices, contracts, diagnostics, all metric populations/rates/predicates, receipt, and final completion fields;
  6. reject any non-false PIT/market/risk/replay/trading authority or a summary that claims final truth or final-stage permission.

  It returns parsed validated artifacts only after all six checks pass. It performs no writes and no network I/O.

- [ ] **Step 4: Make completion tests green**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py -k 'completion or consumer or receipt or replay' \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py
  ```

  Expected: PASS. Fixture-profile persistence tests still pass without changed assertions.

## Task 5: Expose the Offline-Only Adapter Runner

**Design invariants:** INV-01, INV-07, INV-08, INV-09, INV-10, INV-11.

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py`
- Create: `tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py`
- Modify: none.

**Interfaces:**

```python
def run_sealed_export_source_audit(
    *, sealed_export: Path, output_root: Path, project_root: Path
) -> Path: ...
```

CLI arguments are exactly `--sealed-export`, `--output-root`, `--project-root`; no network, fixture-run, capture-bundle, resume, endpoint, or live flag exists.

- [ ] **Step 1: Write failing runner tests**

  Add tests using only the Task 1 temporary export builder:

  ```python
  def test_runner_writes_fresh_adapter_root_only_after_verified_input(tmp_path, fixture_dir):
      export_dir = build_valid_v2_export(tmp_path, fixture_dir)
      output_root = tmp_path / "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/run"
      completion = runner.run_sealed_export_source_audit(
          sealed_export=export_dir, output_root=output_root, project_root=tmp_path
      )
      assert completion == output_root / "completion_manifest.json"
      assert json.loads(completion.read_text())["status"] == "complete"

  def test_runner_rejects_bad_input_before_creating_output(monkeypatch, tmp_path):
      output_root = tmp_path / "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/run"
      with pytest.raises(ValueError):
          runner.run_sealed_export_source_audit(
              sealed_export=tmp_path / "not-an-export", output_root=output_root, project_root=tmp_path
          )
      assert not output_root.exists()

  def test_runner_has_no_network_or_fixture_escape_surface():
      source = Path(runner.__file__).read_text()
      assert "--capture-bundle" not in source
      assert "--fixture-run" not in source
      assert not {"urllib.request", "requests", "httpx", "aiohttp", "socket"} & imported_modules(source)

  def test_runner_rejects_structural_input_before_output_root_admission(monkeypatch, tmp_path, fixture_dir):
      export_dir = with_missing_trusted_revision(build_valid_v2_export(tmp_path, fixture_dir))
      output_root = tmp_path / "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/run"
      monkeypatch.setattr(runner, "validate_sealed_export_audit_output_root", Mock(side_effect=AssertionError("must not admit output")))
      with pytest.raises(adapter.AdapterInputError):
          runner.run_sealed_export_source_audit(sealed_export=export_dir, output_root=output_root, project_root=tmp_path)
      assert not output_root.exists()
  ```

  Add CLI subprocess tests for success and nonzero failure. Assert a pre-existing output root, an output root outside `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/`, and a symlink escape all fail without output mutation.

- [ ] **Step 2: Run runner tests and confirm RED**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py
  ```

  Expected: FAIL because the new runner module does not exist.

- [ ] **Step 3: Implement the minimal offline runner**

  Implement only argument parsing and the one orchestration sequence:

  ```python
  def run_sealed_export_source_audit(*, sealed_export: Path, output_root: Path, project_root: Path) -> Path:
      snapshot = load_verified_historical_sealed_export(sealed_export, project_root=project_root)
      result = reduce_verified_sealed_export(snapshot)
      effective_run_id = output_root.name
      summary = build_sealed_export_source_audit_summary(result, run_id=effective_run_id)
      validate_sealed_export_audit_output_root(output_root, project_root=project_root)
      return persist_sealed_export_audit_artifacts(output_root, result, summary, run_id=effective_run_id)
  ```

  The output-root basename is the sole `effective_run_id`; no caller-supplied second run ID exists. `validate_sealed_export_audit_output_root` may be a small adapter-local wrapper around the existing Stage 1.6A root validator that additionally requires the `sealed_export_source_audits/<run-id>` family. The exact required order is snapshot load, pure structural/semantic reduction, summary construction, output-root admission, then persistence. No output validator, directory creation, or writer call may occur before the reducer succeeds. The main function prints only the completion-manifest path on success and reports a concise `AdapterInputError` message to stderr on failure.

- [ ] **Step 4: Make runner tests green**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py \
    tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py
  ```

  Expected: PASS. The original fixture-only CLI remains isolated and unchanged.

## Task 6: Enforce Static Isolation, Scope, and Completion Evidence

**Design invariants:** INV-01 through INV-14.

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py`
- Modify: none outside the allowed scope.

**Interfaces:**
- Consumes: all APIs produced in Tasks 1-5.
- Produces: final reproducible test evidence only. It does not create a production output root.

- [ ] **Step 1: Add RED static safety tests**

  Add an AST/import test covering exactly the new adapter module and new runner:

  ```python
  FORBIDDEN_IMPORT_PREFIXES = (
      "urllib.request", "requests", "httpx", "aiohttp", "socket",
      "src.strategies", "src.execution", "src.risk", "stage1_5",
  )

  def test_adapter_and_runner_are_offline_stage_isolated_and_do_not_modify_configs():
      for path in NEW_PRODUCTION_PATHS:
          assert not forbidden_imports(path, FORBIDDEN_IMPORT_PREFIXES)
      assert no_call_to_network_or_process_transport(NEW_PRODUCTION_PATHS)
      assert "EXTERNAL_SIGNAL_STAGE1_6A_" not in Path(ADAPTER_PATH).read_text()
  ```

  Add a threshold snapshot test that compares the exact seven historical/source-audit keys named in Task 3 with current `configs/base.py` literals, and rejects absent/extra keys; it must assert the live-only `EXTERNAL_SIGNAL_STAGE1_6A_MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES` is absent. Add a test that completed roots with `source_audit_passed=true` still contain, and set to exact `False`, every one of: `point_in_time_source_validated`, `point_in_time_directional_replay_allowed`, `market_data_coverage_passed`, `risk_veto_candidate`, `replay_allowed`, `alpha_interpretation_allowed`, `trade_signal_allowed`, `paper_trading_allowed`, `live_trading_allowed`, `execution_engine_allowed`, and `RISK_LIVE_TRADING_ENABLED`. Do not use `dict.get(key, False)`; a missing key fails.

- [ ] **Step 2: Run static tests and confirm RED**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py -k 'static or threshold or authority' \
    tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py -k static
  ```

  Expected: FAIL until static checks and threshold snapshot behavior are present.

- [ ] **Step 3: Implement only fixes required by the tests**

  Keep imports stdlib plus the existing Stage 1.6A/1.6B sealed-export loader only. Put no network client or process call in adapter/runner code. Ensure the summary contains the exact seven-key threshold snapshot and keeps all required authorities present and false. Do not add tests or code that run the real adapter, contact Binance, start a VPS process, or mutate Stage 1.6B.

- [ ] **Step 4: Run the bounded full verification suite**

  Run:

  ```bash
  PYTHONPATH=src:. .venv/bin/pytest -q \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py \
    tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
    tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py \
    tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py
  PYTHONPATH=src:. .venv/bin/ruff check \
    src/research/external_signal_shadow/stage1_6a_sealed_export_historical_adapter.py \
    src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py \
    src/research/external_signal_shadow/stage1_6a_futures_delisting_summary.py \
    scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py \
    tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
    tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
    tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py
  ```

  Expected: all tests and bounded lint pass.

- [ ] **Step 5: Enforce final scope and authority checks**

  Run:

  ```bash
  test "$(shasum -a 256 "$DESIGN_PATH" | awk '{print $1}')" = "$DESIGN_SHA256"
  test "$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}')" = "$PLAN_SHA256"
  PYTHONPATH=src:. .venv/bin/python - "$BASE_SHA" "$PREEXISTING_STATE_JSON" <<'PY'
  import hashlib, json, os, subprocess, sys
  from pathlib import Path

  base_sha, preexisting_path = sys.argv[1:]
  exact_allowed = {
      "src/research/external_signal_shadow/stage1_6a_sealed_export_historical_adapter.py",
      "src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py",
      "src/research/external_signal_shadow/stage1_6a_futures_delisting_summary.py",
      "scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py",
      "tests/research/external_signal_shadow/test_stage1_6a_sealed_export_historical_adapter.py",
      "tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py",
      "tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py",
      "tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py",
  }
  allowed_fixture_prefix = "tests/fixtures/external_signal_shadow/stage1_6a_sealed_export_adapter/"

  def digest(path: Path) -> str:
      if path.is_symlink():
          return "symlink:" + hashlib.sha256(os.readlink(path).encode()).hexdigest()
      if path.is_file():
          return hashlib.sha256(path.read_bytes()).hexdigest()
      return "missing" if not path.exists() else "non_regular"

  preexisting = {row["path"]: row for row in json.loads(Path(preexisting_path).read_text(encoding="utf-8"))}
  for path_text, row in preexisting.items():
      actual = digest(Path(path_text))
      if actual != row["sha256"]:
          raise SystemExit(f"STOP: pre-existing path changed: {path_text}")

  tracked = set(subprocess.check_output(["git", "diff", "--name-only", base_sha], text=True).splitlines())
  untracked = set(subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], text=True).splitlines())
  current_changed = tracked | untracked
  implementation_changed = current_changed - set(preexisting)
  disallowed = sorted(
      path for path in implementation_changed
      if path not in exact_allowed and not path.startswith(allowed_fixture_prefix)
  )
  if disallowed:
      raise SystemExit(f"STOP: changed paths outside exact allowlist: {disallowed}")
  print({"implementation_changed": sorted(implementation_changed), "allowlist": "passed"})
  PY
  git diff --check "$BASE_SHA" --
  git status --short --untracked-files=all
  ```

  Expected: every pre-existing dirty/untracked artifact has its recorded hash unchanged, and every tracked/untracked path created or changed by implementation is inside the exact allowlist (or the one bounded fixture prefix). No whitespace errors. STOP on any mismatch; do not repair an out-of-scope change as part of this plan.

- [ ] **Step 6: Run the mandatory independent completion audit**

  After code review and before any claim of completion, invoke [audit-plan-completion](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/.agent/skills/audit-plan-completion/SKILL.md) against this Plan, the approved Design hash, allowed scope, tests, and diff. Proceed only on its `complete` verdict. A later user-approved local operation is a separate step and must start from a fresh output root.

## Plan Self-Review

**Spec coverage:** INV-01 through INV-14 map to Tasks 0-6. `body_parse_unresolved` remains denominator-visible and fails `source_integrity_parent_pass` in Tasks 2-3. Task 0 verifies the actual `load_sealed_export()` return dictionary, manifest hash, ArticleDiscovery schema, DetailObservation outcomes, and DetailRevision linkage. Task 4 requires a caller-supplied sealed-export path, receipt binding, supported-version rejection, and metadata-limited authority replay comparison.

**Ponytail check:** The plan introduces one adapter module, one runner, one test module, and two static JSON fixtures. It reuses the existing 1.6B validator and 1.6A atomic writers; it does not add a transport layer, config, registry, storage engine, raw-evidence copy, or new 1.6B schema.

**Type consistency:** Tasks 1-5 use only `VerifiedSealedExportSnapshot`, `SealedExportAuditResult`, `load_verified_historical_sealed_export`, `reduce_verified_sealed_export`, `build_sealed_export_source_audit_summary`, `persist_sealed_export_audit_artifacts`, and `load_completed_sealed_export_source_audit(output_root, sealed_export=..., project_root=...)` as declared above.

**Placeholder scan:** No deferred implementation placeholders are permitted. Any mismatch in existing 1.6B loader behavior, unknown authoritative artifact class, unlisted consumer, or needed Design change is a STOP and requires a new approved Design/Plan revision.

## Review Gate

This document is a planning artifact only. It must pass `reviewing-implementation-plans` with verdict `Approve`, then receive the user's explicit approval before implementation begins. No execution option, commit, local real-data audit, or VPS deployment is authorized by this draft.
