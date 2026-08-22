# Stage 1.6B Delisting Catalog Index Schema Authority Delta Implementation Plan

> **执行前提:** 仅在本 Plan 与 Required Scope Amendment 均审核通过并获得用户明确批准后，使用 `.agent/workflows/execute-approved-plan.md` 逐 Task 执行。未经批准不得修改代码、执行 probe、历史回填或 VPS collector。

**Base Design:** `docs/designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md`
**Base Design SHA-256:** `83aaa473a9ddb287ee916eae4da327966daa7b0afd5c465f7cc883a06e4f6bc0`
**Approved Design Delta:** `docs/designs/2026-08-21-external-signal-shadow-lab-stage1-6b-delisting-catalog-index-schema-authority-delta-design_CN.md`
**Delta SHA-256 at planning:** `1cf8c0f7af20c15f6cabcbbe0192a1cdcb036b5f62506fb15ce833e89ad070b4`
**Required Scope Amendment:** `docs/designs/2026-08-21-external-signal-shadow-lab-stage1-6b-catalog-delta-storage-consumer-scope-amendment-design_CN.md`
**Scope Amendment SHA-256 at planning:** `afed99a1a5ba3d08e55a11d103730166f1aef9f6017d9e8087747316aec1d722`
**Planning HEAD:** `72051521aa8dae4e3589d134d5cead43d81f1063`
**Safety mode:** `research_shadow_mode`; `source_audit_passed`, PIT, market-data coverage, replay, risk-veto, paper/live trading and execution remain `false`.

**Goal:** Replace the invalid v1 top-level index parser with the fail-closed v2 `Delisting` catalog source contract, without changing Stage 1.5, Stage 1.6A, storage thresholds or any authority flag.

**Architecture:** One concrete `extract_selected_delisting_catalog(raw_payload)` function owns the exact `catalogId=161` / `catalogName="Delisting"` grammar. The probe, live observer and historical backfill reuse it. V2 profile-bound records add catalog provenance, schema-drift follows a mode-specific terminal lifecycle, and `load_sealed_export()` independently validates the v2 historical provenance rather than trusting producer completion.

**Tech stack:** Python standard library, existing Stage 1.6B `Stage16BStorageGuard`, `pytest`, `ruff`, `ast`, `hashlib`, `json`.

---

## Allowed Change Scope

### Allowed implementation paths

- `src/research/external_signal_shadow/stage1_6b_canonical_source_models.py`
- `src/research/external_signal_shadow/stage1_6b_canonical_source_client.py`
- `src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py`
- `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`
- `scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py`
- `scripts/external_signal_shadow/run_stage1_6b_historical_backfill.py`
- `scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py`

### Allowed verification paths

- `tests/fixtures/external_signal_shadow/stage1_6b/profile_probe_index_fixture.json`
- `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py`
- `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py`
- `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py`
- `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py`

### Allowed documentation paths

- `docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md`

### Allowed generated/runtime artifacts

- execution-local evidence outside repository, e.g. `/tmp/stage1_6b_catalog_delta_<utc-run-id>/`
- pytest temporary directories only

No real `data/external_signal_shadow/stage1_6b/**` capture, probe, backfill, sealed export or VPS artifact is authorized by this Plan.

### Affected but unchanged

- `configs/base.py`
  - Existing Stage 1.6B quotas, request limits and Stage 1.5 host reserves are SSOT and must have zero diff.
- `src/research/external_signal_shadow/stage1_5_storage_guard.py`
  - Existing shared lock/resource compatibility remains read-only; run its regression unchanged.
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py`
- `scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py`
  - Stage 1.6A stays fixture-only and keeps all authority flags false.
- `src/research/external_signal_shadow/stage1_5d_*.py`
- `src/research/external_signal_shadow/stage1_5f_*.py`
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
  - No Stage 1.5 code, root, process or deployment mutation is permitted.
- The Base Design, both Design Deltas above and this Plan.
  - Immutable execution authorities. Task 0/Task 8 hash equality is mandatory; no Task may edit them.

### Forbidden

- Any mutation outside the paths above.
- Any modification to `configs/base.py`, Stage 1.5, Stage 1.6A, risk, strategy, execution, market-data or account code.
- New endpoint, `catalogId` query parameter, locale fallback, cookie/session/authentication, all-catalog aggregation, positional catalog selection, fuzzy catalog matching or source registry.
- Real network calls in tests, real historical backfill, source-profile probe, VPS deployment/start/restart or cleanup.
- `ruff check --fix .`, `git clean`, `rsync --delete`, whole-repository formatter/refactor, broad dependency changes or destructive cleanup.

## Frozen Mapping And Stop Conditions

| Delta invariant | Production owner | Durable boundary | RED/verification evidence |
|---|---|---|---|
| INV-D01, INV-D02 | client extractor | `malformed_index_schema` | exact catalog, malformed-schema and epoch-ms tests |
| INV-D03, INV-D04 | models, probe, observer, historical runner | v2 profile/records/checkpoint/identity | schema/profile/identity/legacy-rejection tests |
| INV-D05 | historical runner | four-field v2 transcript | A/B, duplicate and global page-order tests |
| INV-D06 | observer/historical storage calls | existing content-addressed raw write | storage regression unchanged |
| INV-D07 | existing storage guard / all writers | shared lock/reservation | guard, static writer and config zero-diff tests |
| INV-D08, INV-D09 | scope gate | no Stage 1.5/1.6A/authority diff | AST/import/scope regressions |
| INV-D10 | observer + live runner | diagnostic -> checkpoint v2 -> terminal failure | schema-drift lifecycle/restart tests |
| INV-D11 | `load_sealed_export()` | independent v2 consumer predicate | forged complete-export rejection tests |

Stop immediately, preserve all evidence and do not widen scope if:

1. Base Design, Catalog Delta or Scope Amendment SHA-256 changes after Task 0.
2. Task 0 finds a v1 artifact that is terminal-complete, sealed or otherwise consumable; report its exact path/hash and do not delete, resume or reinterpret it.
3. A required code path is outside the whitelist, a Stage 1.5/1.6A consumer needs modification, or a real source response requires another endpoint/profile/catalog.
4. The existing `data.catalogs` source cannot supply exactly one `catalogId=161` / `catalogName="Delisting"` catalog under the frozen grammar.
5. Any test requires live network, a changed storage threshold, or a truthy source/PIT/replay/risk/trading authority.

## Task 0: Immutable Authorities, V1 Inventory And Topology

**Invariants:** INV-D03, INV-D07, INV-D08, INV-D09.
**Files:** no repository file change.

1. Create and export one evidence directory, then persist the execution baseline for every later Task:

```bash
export TASK0_EVIDENCE_DIR="/tmp/stage1_6b_catalog_delta_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$TASK0_EVIDENCE_DIR"
export BASE_SHA="$(git rev-parse HEAD)"
export BASE_DESIGN_PATH="docs/designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md"
export DELTA_PATH="docs/designs/2026-08-21-external-signal-shadow-lab-stage1-6b-delisting-catalog-index-schema-authority-delta-design_CN.md"
export SCOPE_AMENDMENT_PATH="docs/designs/2026-08-21-external-signal-shadow-lab-stage1-6b-catalog-delta-storage-consumer-scope-amendment-design_CN.md"
export PLAN_PATH="docs/plans/2026-08-21-external-signal-shadow-lab-stage1-6b-delisting-catalog-index-schema-authority-delta-implementation-plan_CN.md"
export PLANNING_HEAD="72051521aa8dae4e3589d134d5cead43d81f1063"
printf 'export BASE_SHA=%q\nexport TASK0_EVIDENCE_DIR=%q\nexport BASE_DESIGN_PATH=%q\nexport DELTA_PATH=%q\nexport SCOPE_AMENDMENT_PATH=%q\nexport PLAN_PATH=%q\nexport PLANNING_HEAD=%q\n' \
  "$BASE_SHA" "$TASK0_EVIDENCE_DIR" "$BASE_DESIGN_PATH" "$DELTA_PATH" "$SCOPE_AMENDMENT_PATH" "$PLAN_PATH" "$PLANNING_HEAD" > "$TASK0_EVIDENCE_DIR/task0_env.sh"
test "$(shasum -a 256 "$BASE_DESIGN_PATH" | awk '{print $1}')" = \
  "83aaa473a9ddb287ee916eae4da327966daa7b0afd5c465f7cc883a06e4f6bc0"
test "$(shasum -a 256 "$DELTA_PATH" | awk '{print $1}')" = \
  "1cf8c0f7af20c15f6cabcbbe0192a1cdcb036b5f62506fb15ce833e89ad070b4"
test "$(shasum -a 256 "$SCOPE_AMENDMENT_PATH" | awk '{print $1}')" = \
  "afed99a1a5ba3d08e55a11d103730166f1aef9f6017d9e8087747316aec1d722"
git cat-file -e "${PLANNING_HEAD}^{commit}"
git merge-base --is-ancestor "$PLANNING_HEAD" "$BASE_SHA"
test -z "$(git diff --name-only "$PLANNING_HEAD" "$BASE_SHA" -- \
  src/research/external_signal_shadow/stage1_6b_canonical_source_*.py \
  scripts/external_signal_shadow/run_stage1_6b_*.py \
  tests/research/external_signal_shadow/test_stage1_6b_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_*.py)" \
  || { echo 'STOP: Stage 1.6B-relevant paths changed after Planning HEAD; re-review required.' >&2; exit 1; }
shasum -a 256 "$BASE_DESIGN_PATH" "$DELTA_PATH" "$SCOPE_AMENDMENT_PATH" "$PLAN_PATH" \
  > "$TASK0_EVIDENCE_DIR/authorities.sha256"
git status --short --untracked-files=all | tee "$TASK0_EVIDENCE_DIR/git-status.txt"
```

Record every dirty/untracked path's path, porcelain status and SHA-256 in `$TASK0_EVIDENCE_DIR/preexisting-paths.jsonl`; fail closed on a rename/copy status rather than guessing its identity:

```bash
python3 - "$TASK0_EVIDENCE_DIR/preexisting-paths.jsonl" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

records = []
for line in subprocess.check_output(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"], text=True
).splitlines():
    status, path = line[:2], line[3:]
    if "R" in status or "C" in status:
        raise SystemExit(f"STOP: Task 0 cannot baseline rename/copy status: {line}")
    candidate = Path(path)
    if not candidate.is_file():
        raise SystemExit(f"STOP: Task 0 dirty/untracked path is not a regular file: {path}")
    records.append({
        "path": path,
        "status": status,
        "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    })
Path(sys.argv[1]).write_text(
    "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
    encoding="utf-8",
)
PY
```

Treat pre-existing untracked Design documents as user-owned until explicitly included in this work. Require the Base Design, Catalog Delta and Scope Amendment hashes to equal header values. `$TASK0_EVIDENCE_DIR/authorities.sha256` is the immutable four-file Task 0 record; Task 8 must compare against it rather than a self-embedded final hash.
3. Inventory only local `data/external_signal_shadow/stage1_6b/` paths, if present: v1 profile-attestation directories, `historical_backfill/*`, `live_observation/*`, `observer_checkpoint.json`, `terminal_status.json` and `sealed_exports/*`. Record path, SHA-256 and detected `source_profile_id`/schema/status. Do not write, delete or open a network connection. Expected local state is no consumable v1 artifact; a contrary result is a stop condition.
4. Run focused topology evidence with `rg` and advisory Graphify for `fetch_index_page`, `run_source_profile_probe`, `Stage16BObserver` and `load_sealed_export`. Record every current direct `data.articles`, `catalogs[0]`, `fetch_index_page` and sealed-export consumer call site. Also inventory every `request_manifest` producer, the exact `request_observation_id` construction, `record_seq` owner, success/failure row path and checkpoint `stream_offsets`/`stream_last_hashes` owner. Current source inspection is expected to find no `request_manifest` producer; that absence must be recorded before Task 4 establishes one single writer boundary. If any existing producer is found, STOP unless Task 4 explicitly reuses that exact producer, ID construction and `record_seq` authority; never create a second producer. Expected modification set: v2 modules/runners/tests only.
5. Run the existing 1.6B suite before edits and record its result as baseline. Existing tests may pass despite the live failure because the fixture has synthetic top-level `data.articles`; this is expected baseline evidence, not validation of the real profile.

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py -q
```

Expected: baseline recorded; no repository mutation.

## Task 1: V2 Models, Profile Identity And RED Schema Tests

**Invariants:** INV-D01--INV-D04, INV-D10.
**Files:**

- Modify: `src/research/external_signal_shadow/stage1_6b_canonical_source_models.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py`

1. Write RED tests for exact constants:

```python
assert SOURCE_PROFILE_ID == "binance_public_web_bapi_en_delisting_catalog_v2"
assert INDEX_REQUEST_VARIANT == "bapi_article_list_type_1_delisting_catalog_161_page_50_v2"
assert SELECTED_CATALOG_ID == 161
assert SELECTED_CATALOG_NAME == "Delisting"
```

2. Write RED serialization tests requiring:

```python
SourceProfileProbeAttestation.schema_version == "stage1_6b_source_profile_probe_attestation_v2"
ListCaptureRecord.schema_version == "stage1_6b_list_capture_v2"
ArticleDiscoveryRecord.schema_version == "stage1_6b_article_discovery_v2"
HistoricalCoverageRecord.schema_version == "stage1_6b_historical_coverage_v2"
ObserverCheckpointRecord.schema_version == "stage1_6b_observer_checkpoint_v2"
CaptureRunContract.schema_version == "stage1_6b_capture_run_contract_v1"
```

Require v2 `ListCaptureRecord` to serialize `selected_catalog_id`, `selected_catalog_name`, `selected_catalog_total` and only the selected-catalog `article_count`. Require `ArticleDiscoveryRecord` to serialize source catalog provenance. Require `ObserverCheckpointRecord` to serialize `last_index_poll_status` and `last_index_poll_coverage`.

Require `HistoricalCoverageRecord` to serialize only four-field v2 transcripts `(page_no, selected_catalog_id, source_article_id, source_published_at_ms)`. Its existing `sweep_a` / `sweep_b` dictionaries must each persist the P1 diagnostic shape below without a new model class:

```python
{
    "per_page_selected_catalog_total": [
        {"page_no": 1, "selected_catalog_total": 426},
    ],
    "first_selected_catalog_total": 426,
    "last_selected_catalog_total": 426,
}
```

`page_no` is positive, `selected_catalog_total` is a non-negative integer, and `first`/`last` are `None` only when the per-page list is empty. These fields are diagnostics only and are not completion inputs.

3. Write RED tests for allowed checkpoint pairs: `trusted/successful` and each enumerated non-trusted status with `degraded_not_successful`; reject an unknown status, unknown coverage and `trusted/degraded_not_successful`.
4. Write exact v2 identity-algebra RED tests using identical raw bytes and the frozen helpers:

```python
v2_payload_page_1 = compute_list_payload_id(
    "announcement_index", "en",
    "bapi_article_list_type_1_delisting_catalog_161_page_50_v2", raw_sha,
)
v2_payload_page_2 = compute_list_payload_id(
    "announcement_index", "en",
    "bapi_article_list_type_1_delisting_catalog_161_page_50_v2", raw_sha,
)
assert v2_payload_page_1 == v2_payload_page_2
assert v2_payload_page_1 != compute_list_payload_id(
    "announcement_index", "en", "bapi_article_list_type_1_page_50_v1", raw_sha,
)
assert compute_list_capture_id(v2_profile, page_1_url, 1, v2_payload_page_1, request_1) != \
       compute_list_capture_id(v2_profile, page_2_url, 2, v2_payload_page_1, request_1)
assert compute_list_capture_id(v2_profile, page_1_url, 1, v2_payload_page_1, request_1) != \
       compute_list_capture_id(v2_profile, page_1_url, 1, v2_payload_page_1, request_2)
assert compute_article_discovery_id(v2_profile, article_id, first_capture_1) == \
       compute_article_discovery_id(v2_profile, article_id, first_capture_1)
assert compute_article_discovery_id(v2_profile, article_id, first_capture_1) != \
       compute_article_discovery_id(v2_profile, article_id, first_capture_2)
```

Add an explicit no-migration assertion: a serialized v1 record/profile is rejected as v2 input and is never recomputed or relabeled with v2 constants.
5. Implement the minimum additive v2 models/constants and source-profile hashing inputs. Keep `CaptureRunContract`, terminal status and sealed export schemas at v1; do not edit any config value or Stage 1.6A identity function.
6. Run the targeted model suite. Expected: all v2 serialization, identity, profile isolation and checkpoint-pair tests pass.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py -q
```

## Task 2: One Strict Selected-Catalog Extractor And Structural Fixture

**Invariants:** INV-D01, INV-D02, INV-D06.
**Files:**

- Modify: `src/research/external_signal_shadow/stage1_6b_canonical_source_client.py`
- Modify: `tests/fixtures/external_signal_shadow/stage1_6b/profile_probe_index_fixture.json`
- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py`

1. Replace the old fixture's synthetic top-level `data.articles` shape with a minimal synthetic structural mirror of the 2026-08-21 read-only diagnostic: seven catalogs, `Delisting` at zero-based position `3`, and a nonmatching valid first catalog. Include fixture metadata/comment-equivalent test name documenting that it is synthetic parser input, not source-audit evidence.
2. Write RED client tests for `extract_selected_delisting_catalog(raw_payload)`:

```python
result = extract_selected_delisting_catalog(payload)
assert result.catalog_id == 161
assert result.catalog_name == "Delisting"
assert result.catalog_total >= len(result.articles)
assert result.articles[0]["code"] == expected_delisting_article_id
```

3. Add a parameterized RED matrix: top-level `data.articles` only; missing/duplicate selected catalog; ID/name mismatch; non-list `articles`; total invalid or below list length; invalid code/title; seconds, float, string, bool, zero, negative and out-of-range `releaseDate`. Each must yield only `malformed_index_schema`.
4. Add RED tests that a valid empty selected catalog is accepted, and that `fetch_index_page()` returns `trusted` only after this exact extractor succeeds.
5. Implement one frozen `SelectedDelistingCatalogResult` and one strict extractor in the client module (it may import the v2 catalog constants/model). `fetch_index_page()` calls it solely for semantic validation; it keeps the full raw response bytes unchanged. Do not create a registry, generic parser, fallback or a second parser in any caller.
6. Run client tests. Expected: the old fixture shape fails before implementation and the synthetic seven-catalog fixture passes afterward.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py -q
```

## Task 3: V2 Probe Attestation, Detail Binding And Pre-Network Rejection

**Invariants:** INV-D01--INV-D04, INV-D07.
**Files:**

- Modify: `scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py`

1. Write RED probe tests with injected opener proving the supplied `probe_article_id` must be present in the **same** `SelectedDelistingCatalogResult.articles` from the probe index response before the detail opener is called. A syntactically valid article ID outside the selected catalog must fail before the detail request and leave no attestation file.
2. Write RED success assertions for `source_profile_probe_v2`, v2 profile hash, v2 `index_article_id_path`, selected catalog ID/name/selected count and guarded attestation write.
3. Keep existing tests for absent `--live-public-readonly`, path confinement and guarded persistence. Add a no-write assertion for `malformed_index_schema` and a no-detail-opener assertion for a nonmember probe ID.
4. Write RED runner tests supplying a syntactically valid v1 probe attestation to each v2 historical/live runner. Each must reject on profile/schema validation before client construction or opener use, create no output root, and write no artifact.
5. Implement the minimal sequence:

```text
one index request
-> strict selected-catalog extractor
-> require exact --probe-article-id membership in selected articles
-> one detail request for that same ID
-> guarded v2 attestation write
```

The historical/live startup checks may reuse their existing `source_profile_id` and header authority boundary; no second attestation validator is authorized.

6. Run probe and pre-network startup tests. Expected: exactly one index plus one related detail request only on probe success; all probe failure paths write no attestation, and v1 attestation inputs make zero opener calls.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py -q
```

## Task 4: Live Reducer Schema-Drift Lifecycle And V2 Checkpoint

**Invariants:** INV-D01--INV-D04, INV-D07, INV-D10.
**Files:**

- Modify: `src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`
- Modify: `scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py`

1. Write RED observer tests proving every successful list/reducer path calls the shared extractor and emits only v2 `ListCapture`/`ArticleDiscovery` catalog fields. A source response with catalog 161 at nonzero position must derive candidates from that catalog, never `catalogs[0]` or top-level `data.articles`.
2. Write RED live schema-drift test with malformed selected catalog. Assert exactly:

```text
no ListCapture row
no ArticleDiscovery row
no candidate state progress
one guarded bounded index request/diagnostic row
one ObserverCheckpoint v2:
  last_index_poll_status = malformed_index_schema
  last_index_poll_coverage = degraded_not_successful
```

3. Write RED request-observation identity tests for both trusted and malformed index results. For one HTTP index attempt assert `request_manifest` rows added is exactly `1`, the row's `request_observation_id` is unique and equals the request's frozen ID, `monotonic_request_seq` advances exactly once, and the checkpoint's manifest stream offset/last hash includes that one row. The malformed row must set `validation_status=malformed_index_schema`; it is neither `ListCapture` nor successful coverage.
4. Write RED runner test: the observer raises a dedicated schema-drift failure after the degraded checkpoint; the runner writes terminal `failure/source_profile_schema_drift`, creates no sealed export, returns non-zero through CLI, and a subsequent `--resume` is rejected before any opener call. Add a terminal-reservation-failure variant: the degraded checkpoint remains the latest authority, no terminal complete/failure substitute is written, no sealed export exists, and the CLI exits non-zero.
5. Under the Scope Amendment's bounded restart-read authorization only, write RED resume tests on these exact profile-authority axes:

```text
valid v2 CaptureRunContract:
  schema_version = stage1_6b_capture_run_contract_v1
  source_profile_id = binance_public_web_bapi_en_delisting_catalog_v2
  source-profile, attestation and header hashes match v2 authority
  => does not reject solely because CaptureRunContract.schema_version is v1

legacy-profile CaptureRunContract:
  schema_version = stage1_6b_capture_run_contract_v1
  source_profile_id = binance_public_web_bapi_en_v1
  OR v2 profile/attestation/header authority does not match
  => reject before reconciliation write and client/opener construction
```

Also separately prove that a v1 `ObserverCheckpoint`, `[v1 ListCapture, v2 ListCapture]` bounded committed-prefix batch, and `[v1 ArticleDiscovery, v2 ArticleDiscovery]` bounded committed-prefix batch each reject during the existing pre-reconciliation read. For every rejection assert zero opener calls and zero root mutation. The mixed-record fixtures must place both parsed rows within the existing bounded prefix read; do not introduce a root scan, migration, second scan or new reconciliation algorithm.
6. Establish the single live request-manifest authority at the existing `Stage16BObserver._append_record()` boundary. Every attempted live index request writes exactly one guarded `request_manifest/YYYY-MM-DD.jsonl` observation row before its result branch, with `request_observation_id`, request class/sequence, page, requested/final URL, HTTP status/content type, byte count, validation status and error. Do not add a second schema-drift diagnostic writer, a second request ID, or a separate `record_seq` owner.
7. Implement v2 checkpoint fields on every poll. For `malformed_index_schema`, reuse that single manifest row, checkpoint while holding ordinary guard admission, then raise the dedicated terminal exception. The runner catches only that exception to write terminal failure through existing terminal guard logic and skips sealing. Other existing transport statuses retain their Base Design lifecycle.
8. Run observer/live runner tests. Expected: schema drift preserves restart bounds and leaves a durable failure root, not a complete export.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py -q
```

## Task 5: Historical V2 Sweep, Completeness Failure And Total Diagnostics

**Invariants:** INV-D01--INV-D05, INV-D07, INV-D10.
**Files:**

- Modify: `scripts/external_signal_shadow/run_stage1_6b_historical_backfill.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py`

1. Update existing historical fixtures/tests from fake small timestamps to valid 13-digit epoch-ms values. Write RED assertions that both sweeps use only the shared selected-catalog extractor and transcript tuples are exactly `(page_no, 161, source_article_id, releaseDate_ms)`.
2. Write RED tests for global selected-catalog ordering. `page1.last_releaseDate < page2.first_releaseDate` must be `incomplete_ordering_inversion`, even if each page is internally sorted.
3. Write a direct RED empty-selected-catalog historical test: a structurally valid `articles=[]` receipt produces no transcript entry, cannot set `reached_from_ms`, yields incomplete coverage, terminal failure and no sealed export. It must never be reclassified as `malformed_index_schema`.
4. Write RED schema-drift test asserting:

```text
page_failure.validation == malformed_index_schema
HistoricalCoverage.schema_version == stage1_6b_historical_coverage_v2
HistoricalCoverage.status == incomplete_schema_failure
terminal_status.status == failure
terminal_reason == historical_index_schema_failure
sealed_exports absent
```

The test must prove the final checkpoint is written before terminal status when reservation succeeds.
5. Extend the same existing guarded append authority for historical index attempts: one request creates exactly one request-manifest row with the frozen request ID/sequence and result metadata. Add a RED test proving a malformed historical index response creates one `page_failure` and one matching manifest row, not a second schema-drift record; its committed stream boundary is included by the final checkpoint.
6. Add the Task 1 P1 diagnostic fields under each sweep only: ordered `per_page_selected_catalog_total` rows of exact `{"page_no": positive_int, "selected_catalog_total": nonnegative_int}` shape, plus matching `first_selected_catalog_total` and `last_selected_catalog_total`. Persist them in `HistoricalCoverage v2`; test that they exactly reflect the trusted ListCapture totals and that `first`/`last` match the first/last page row. They are explanatory diagnostics only: a total change cannot by itself complete/fail coverage or replace transcript A/B parity.
7. Implement selected-catalog-only historical pagination, the same single request-manifest row per attempted index request, four-field transcripts, global ordering check, schema-drift page-failure terminal sequence and the diagnostic totals. Preserve existing two-sweep, one-detail-cycle, range, retry and no-seal requirements.
8. Run historical tests. Expected: only a stable, globally ordered, complete v2 selected-catalog sweep can reach the existing producer completion predicate.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py -q
```

## Task 6: V2 Sealed Export Consumer Verification

**Invariants:** INV-D03, INV-D04, INV-D05, INV-D07, INV-D11.
**Files:**

- Modify: `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py`

1. Write RED sealed-export tests that construct otherwise hash-valid v2 bundles and assert `load_sealed_export()` rejects:

```text
v1 source_profile_id or HistoricalCoverage schema
three-field transcript or tuple catalog_id != 161
seconds/float/string/bool timestamp
ListCapture wrong/missing selected catalog provenance
ArticleDiscovery wrong/missing source catalog provenance
unknown or invalid v2 checkpoint status/coverage pair
```

2. Write a positive RED fixture/bundle with v2 profile, four-field transcripts, v2 list/discovery/checkpoint records and complete Base historical predicates. It must pass without reparsing every raw index payload.
3. Under the Scope Amendment's narrow authorization only, implement one `v2_historical_export_acceptance` branch inside the existing read-only `load_sealed_export()` after generic hash/terminal/range validation. Reuse model validators for timestamp/tuple/checkpoint-pair checks. Do not change `seal_export()` quota/copy semantics, storage guard/reserve, root accounting or accept v1 as v2.
4. Keep live export historical-null behavior unchanged. Add test coverage that a live export never enters the historical v2 predicate.
5. Run storage tests. Expected: consumer acceptance is independent of producer-written `status=complete` and rejects forged v2 provenance.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py -q
```

## Task 7: Static Closure, Runbook Constraint And Compatibility Tests

**Invariants:** INV-D07--INV-D09.
**Files:**

- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py`
- Modify: `docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md`

1. Add a static source/AST test covering `stage1_6b_canonical_source_client.py`, observer, probe runner and both collection runners. It must fail if a runtime caller directly reads `data.articles`, selects `catalogs[0]`, iterates all catalogs, or JSON-parses index payload outside `extract_selected_delisting_catalog()`.
2. Extend the existing persistent-writer closure test to include `request_manifest` diagnostics and prove all writes still route through Stage 1.6B guarded storage and the shared host lock.
3. Update the deployment checklist as a read-only preflight contract only: require profile v2, a fresh v2 attestation, and a probe article ID that is visible in the current selected `Delisting` catalog. Preserve its explicit prohibition on VPS start/deployment commands and all Stage 1.5 health gates.
4. Run focused suites plus read-only compatibility tests. Expected: no direct index parser bypass, no unguarded new writer, no Stage 1.5/1.6A change.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py -q
```

## Task 8: Full Verification, Scope Gate And Completion Audit

**Invariants:** INV-D01--INV-D11.
**Files:** no production/doc changes.

1. In the same terminal that retained Task 0 environment, or after explicitly sourcing its persisted record, recompute Base Design, Catalog Delta, Scope Amendment and Plan SHA-256. Require equality to Task 0 execution-log values; a changed authority is a stop condition.

```bash
source "$TASK0_EVIDENCE_DIR/task0_env.sh"
test -n "$BASE_SHA"
test -f "$TASK0_EVIDENCE_DIR/authorities.sha256"
shasum -a 256 "$BASE_DESIGN_PATH" "$DELTA_PATH" "$SCOPE_AMENDMENT_PATH" "$PLAN_PATH" \
  > "$TASK0_EVIDENCE_DIR/authorities.final.sha256"
diff -u "$TASK0_EVIDENCE_DIR/authorities.sha256" \
  "$TASK0_EVIDENCE_DIR/authorities.final.sha256"
```
2. Run the full changed Stage 1.6B suite and read-only Stage 1.5/1.6A regressions:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py -q
```

3. Run `ruff check` only on the allowed implementation/test scripts. Run `git diff --check "$BASE_SHA"`.

```bash
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_6b_canonical_source_models.py \
  src/research/external_signal_shadow/stage1_6b_canonical_source_client.py \
  src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py \
  src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py \
  scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py \
  scripts/external_signal_shadow/run_stage1_6b_historical_backfill.py \
  scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py
git diff --check "$BASE_SHA"
```

4. Run this repository-local scope gate against `BASE_SHA`. It fails if:

```text
any changed path is outside Allowed Change Scope
configs/base.py has a diff
Stage 1.5/Stage 1.6A affected-but-unchanged paths have a diff
any authority value other than literal False assigns source_audit_passed, point_in_time_source_validated,
market_data_coverage_passed, replay_allowed, risk_veto_candidate,
trade_signal_allowed, paper_trading_allowed, live_trading_allowed,
execution_engine_allowed or RISK_LIVE_TRADING_ENABLED
```

The Task 7 static closure tests, executed in Step 2, are the mechanical authority for direct-parser and persistent-writer closure; do not duplicate a weaker text scan here.

```bash
python3 - "$BASE_SHA" "$TASK0_EVIDENCE_DIR" <<'PY'
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

base = sys.argv[1]
task0_evidence_dir = Path(sys.argv[2])
allowed = {
    "src/research/external_signal_shadow/stage1_6b_canonical_source_models.py",
    "src/research/external_signal_shadow/stage1_6b_canonical_source_client.py",
    "src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py",
    "src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py",
    "scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py",
    "scripts/external_signal_shadow/run_stage1_6b_historical_backfill.py",
    "scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py",
    "tests/fixtures/external_signal_shadow/stage1_6b/profile_probe_index_fixture.json",
    "tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py",
    "tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py",
    "tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py",
    "tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py",
    "docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md",
}
changed = set(
    filter(
        None,
        subprocess.check_output(
            ["git", "diff", "--name-only", base], text=True
        ).splitlines(),
    )
)
preexisting = {
    json.loads(line)["path"]
    for line in (task0_evidence_dir / "preexisting-paths.jsonl").read_text(encoding="utf-8").splitlines()
}
current_untracked = set(
    filter(
        None,
        subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"], text=True
        ).splitlines(),
    )
)
implementation_changed = (changed | current_untracked) - preexisting
assert implementation_changed <= allowed, sorted(implementation_changed - allowed)
if "configs/base.py" not in preexisting:
    assert not subprocess.call(["git", "diff", "--quiet", base, "--", "configs/base.py"])
for pattern in (
    "src/research/external_signal_shadow/stage1_5",
    "src/research/external_signal_shadow/stage1_6a",
    "scripts/external_signal_shadow/run_stage1_5",
    "scripts/external_signal_shadow/run_stage1_6a",
):
    assert not any(path.startswith(pattern) for path in implementation_changed), pattern

for line in (task0_evidence_dir / "preexisting-paths.jsonl").read_text(encoding="utf-8").splitlines():
    record = json.loads(line)
    path = Path(record["path"])
    assert path.is_file(), ("preexisting_path_missing", record["path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], record["path"]

false_required = {
    "source_audit_passed",
    "point_in_time_source_validated",
    "market_data_coverage_passed",
    "replay_allowed",
    "risk_veto_candidate",
    "trade_signal_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_engine_allowed",
    "RISK_LIVE_TRADING_ENABLED",
}

def is_literal_false(node):
    return isinstance(node, ast.Constant) and node.value is False

for path in implementation_changed:
    if not path.endswith(".py"):
        continue
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        names = {target.id for target in targets if isinstance(target, ast.Name)}
        for name in names & false_required:
            assert is_literal_false(value), (path, name, "authority_must_be_literal_false")
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value in false_required
                ):
                    assert is_literal_false(value), (path, key.value, "authority_dict_must_be_literal_false")
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if (
                    keyword.arg in false_required
                ):
                    assert is_literal_false(keyword.value), (path, keyword.arg, "authority_keyword_must_be_literal_false")
PY
```

5. Run `.agent/skills/audit-plan-completion` against `BASE_SHA`, the Base Design, both immutable Design Deltas, this Plan and final diff. Required verdict: `complete` before commit, any deployment decision or real source command.
6. Confirm no source-profile probe, historical backfill, live observer start, VPS deployment or authority change occurred during execution.

## Completion Boundary

This Plan completes only the v2 selected-`Delisting` catalog code/test/checklist contract. It does not authorize a real source-profile probe, local historical backfill, VPS live observer, Stage 1.6A real-source consumption, source-audit pass, PIT validation, market-data collection, replay, risk veto, paper trading, live trading or execution.
