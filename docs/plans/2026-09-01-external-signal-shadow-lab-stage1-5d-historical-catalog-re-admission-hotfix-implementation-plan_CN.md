# Stage 1.5D Historical Catalog Re-admission Hotfix Implementation Plan

> **For agentic workers:** REQUIRED WORKFLOW: use `.agent/workflows/execute-approved-plan.md` only after an external review verdict provides the exact approved Plan SHA-256 and the user explicitly authorizes implementation. Approved Plan bytes are read-only during implementation: do not change these checkboxes; use the workflow task tracker instead.

**状态:** plan_draft  
**Review Mode:** closure_audit  
**Plan authority:** approved Design bytes `6a5fbf17d3acbb8e3f7a977cdd46c1f9e2a3516813c3dc3934e590c59e29155b` at `docs/designs/2026-09-01-external-signal-shadow-lab-stage1-5d-historical-catalog-re-admission-hotfix-design_CN.md`.  
**Prior reviewed Plan lineage SHA-256:** `257c2e1e86ba5d85fb9ddc55ab0da95430fdd8ac336417284366635be3720272` (not execution authority).  
**Approved Plan SHA-256:** pending external approval; Task 0 requires its exact value as `EXPECTED_APPROVED_PLAN_SHA256`.  
**代码实施许可:** false  
**部署许可:** false

**Goal:** Make a fresh Stage 1.5D v3 root durably exclude pre-bootstrap, historical, and invalid-publication catalog articles; preserve real scheduler starvation across restart; and reject malformed or ambiguous resumable roots before any mutation or network request.

**Architecture:** Reuse the existing scheduler-state `articles` mapping as the only terminal lifecycle store and existing formal event plus formal identity-index projection as the only formal-completed authority. Add no registry, database, queue, daemon, lock, parser path, Kline lifecycle, or migration. A strict V3 preflight parses and validates resumable state once; the runner consumes only the detached validated state and never invokes the legacy/defaulting loader on the V3 resume path. It then applies a bootstrap boundary, local terminal reducer, exact scheduler-owned WAL intents, and the existing valid post-bootstrap detail/ExchangeInfo/formal path.

**Tech Stack:** Python 3.11, stdlib (`ast`, `hashlib`, `json`, `os`, `pathlib`, `re`, `stat`), pytest, ruff. No new dependency.

## Global Constraints

- The approved Design SHA above is immutable authority. If its bytes or any Design invariant must change, STOP: `approved_design_change_required`.
- `EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION` changes exactly from `2` to `3`, and the absent Design-required `EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS = 30 * 1000` is added exactly once immediately after it. These are the only `configs/base.py` deltas; no other risk threshold, source URL, retry budget, parser, anchor, ExchangeInfo, formal v2, 1.5F, 1.5G, or 1.5H contract changes.
- `RISK_LIVE_TRADING_ENABLED` remains `False`; execution, alpha, signal, paper-trading, live-trading, and execution-engine authority remain false.
- V3 has no migration, root reuse, diagnostic reconstruction, automatic repair, `setdefault`, coercion, malformed-row dropping, index rebuild, or resume for a legacy/invalid root.
- Before implementation, an external approval verdict must supply the exact `EXPECTED_APPROVED_PLAN_SHA256`; Task 0 rejects any byte mismatch. The approved Plan remains read-only, including its checkboxes, for the whole execution.
- Only scheduler-owned `detail_request`, candidate-validation `exchangeinfo_request`, and `formal_emission` use V3 WAL. Existing post-formal `first_bar_queue`, Kline, and its optional ExchangeInfo cache remain downstream in-memory behavior and are neither deleted nor given a WAL.
- A review finding is verified against frozen contracts and real source topology before adoption. This Plan must not implement a finding that conflicts with them.
- Implementation uses RED-GREEN TDD. Do not add fixture files when an inline synthetic JSON fixture in an existing test is sufficient.
- This Plan creates code and tests only. It does not stop, restart, mutate, deploy, or inspect live VPS roots.
- No automatic commit, push, deployment, or execution is authorized by this Plan.

## Allowed Change Scope

Allowed implementation paths:
- `configs/base.py` - only `EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION = 2` to `= 3`, followed immediately by the one new exact assignment `EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS = 30 * 1000`.
- `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`
- `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

Allowed documentation paths:
- `docs/plans/2026-09-01-external-signal-shadow-lab-stage1-5d-historical-catalog-re-admission-hotfix-implementation-plan_CN.md`

Allowed generated/runtime artifacts:
- none committed. Pytest-only temporary directories and `/tmp/stage1_5d_v3_historical_catalog_re_admission_<BASE_SHA>/` provenance are local, uncommitted artifacts.

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
  - Compatibility evidence: closed-tree test accepts its existing `build_detail_payload_path()` grammar and daily JSONL paths without a naming migration.
- `src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py`
  - Compatibility evidence: V3 formal-projection tests consume its existing formal index format; the production path still appends event then index.
- `src/research/external_signal_shadow/stage1_5d_live_event_source_collector.py`
  - Compatibility evidence: bootstrap tests retain its parser-trusted heartbeat verdict; no parser behavior changes.
- `src/research/external_signal_shadow/stage1_5d_live_event_source_first_bar.py`
  - Compatibility evidence: formal-completed duplicate tests retain an existing queued first-bar item and make no Kline request during catalog admission.
- `tests/research/external_signal_shadow/test_stage1_5d_a827_boundary_regression.py`
  - Compatibility evidence: its direct scheduler-state loader regression remains green without a legacy-loader behavior change.
- `tests/research/external_signal_shadow/test_stage1_5_storage_guard.py`
  - Compatibility evidence: its direct scheduler-state writer/storage-guard regression remains green without a storage-writer change.
- `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
  - Compatibility evidence: runner regression proves only durable `detail_never_attempted_budget_starved` rows produce the existing degraded decision.
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
  - Compatibility evidence: existing 1.5F runtime-gate validator/loader suites remain green; no 1.5F source change is allowed.
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
  - Compatibility evidence: its integrity suite remains green; rejected 1.5D rows produce no new 1.5F/1.5G input.

Forbidden:
- Any mutation outside the allowed paths.
- Any Design, governance, roadmap, review/runbook, raw evidence, VPS root, generated `data/`, or dependency change.
- Any parser/transliteration/manual-symbol mapping change for article `6e9e9784397745f4a49d3f69b1cfebda`.
- Any first-bar/Kline WAL, persistent queue, registry, migration, database, daemon, writer lock, generic framework, feature flag, threshold, or public endpoint change.
- Any `ruff check --fix`, formatter/autofix, `git clean`, `git reset --hard`, `git checkout --`, `rsync --delete`, or destructive cleanup.
- Any live/public request outside existing synthetic pytest fixtures.

## Invariant-To-Task Mapping

| Design invariant | Owner task | Required evidence |
|---|---|---|
| INV-01, INV-02, INV-03, INV-04, INV-14 | 4 | trusted bootstrap, historical and releaseDate boundary RED/GREEN fixtures; zero request/queue/formal assertions |
| INV-05, INV-06 | 4, 5 | durable starvation derivation and terminal/non-reentry restart fixtures |
| INV-07, INV-11, INV-13, INV-16, INV-17 | 2, 3 | exact schema/semantic corruption fixtures; zero-side-effect root fingerprint; provenance/lifecycle matrix |
| INV-08, INV-10 | 3, 5, 6 | formal event/index projection tests; queued first-bar preservation; unchanged consumer suites |
| INV-09, INV-15 | 0, 1, 6 | exact config AST gate; safety assertion; no new lock or authority |
| INV-12 | 5 | detail/BAPI/fallback/ExchangeInfo/formal intent-before-side-effect and crash matrices |

## Task 0: Freeze Authority, Baseline, And Pre-Existing Paths

**Design invariants:** INV-07, INV-09, INV-13, INV-15.  
**Files:**
- Modify: none.
- Create: local `/tmp/stage1_5d_v3_historical_catalog_re_admission_<BASE_SHA>/capture_preexisting_paths.py`.
- Verify: all allowed implementation and verification paths.

**Interfaces:**
- Produces immutable execution inputs: `BASE_SHA`, Design/Plan SHA256, raw worktree provenance snapshots, and `preexisting_path_records.json`.
- Later tasks may edit only a tracked-clean allowed implementation/test path.

**Out of scope:** Do not alter, delete, stage, or attribute existing dirty/untracked paths to this task.

- [ ] **Step 1: Bind exact Design and Plan authority before any code edit.**

```bash
export BASE_SHA="$(git rev-parse HEAD)"
export DESIGN_PATH="docs/designs/2026-09-01-external-signal-shadow-lab-stage1-5d-historical-catalog-re-admission-hotfix-design_CN.md"
export EXPECTED_DESIGN_SHA256="6a5fbf17d3acbb8e3f7a977cdd46c1f9e2a3516813c3dc3934e590c59e29155b"
export ACTUAL_DESIGN_SHA256="$(shasum -a 256 "$DESIGN_PATH" | awk '{print $1}')"
export PLAN_PATH="docs/plans/2026-09-01-external-signal-shadow-lab-stage1-5d-historical-catalog-re-admission-hotfix-implementation-plan_CN.md"
export EXPECTED_APPROVED_PLAN_SHA256="${EXPECTED_APPROVED_PLAN_SHA256:?STOP: external approval verdict must provide exact approved Plan SHA-256}"
export ACTUAL_PLAN_SHA256="$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}')"
export PROVENANCE_DIR="/tmp/stage1_5d_v3_historical_catalog_re_admission_${BASE_SHA}"
[ "$ACTUAL_DESIGN_SHA256" = "$EXPECTED_DESIGN_SHA256" ] || { echo 'STOP: approved Design SHA mismatch'; exit 1; }
[ "$ACTUAL_PLAN_SHA256" = "$EXPECTED_APPROVED_PLAN_SHA256" ] || { echo 'STOP: approved Plan SHA mismatch'; exit 1; }
mkdir -p "$PROVENANCE_DIR"
printf '%s\n' "$BASE_SHA" > "$PROVENANCE_DIR/base_sha"
printf '%s\n' "$ACTUAL_DESIGN_SHA256" > "$PROVENANCE_DIR/design_sha256"
printf '%s\n' "$EXPECTED_APPROVED_PLAN_SHA256" > "$PROVENANCE_DIR/approved_plan_sha256"
printf '%s\n' "$ACTUAL_PLAN_SHA256" > "$PROVENANCE_DIR/actual_plan_sha256"
git status --porcelain=v1 -z --untracked-files=all > "$PROVENANCE_DIR/git_status_before.z"
git diff > "$PROVENANCE_DIR/git_diff_before.patch"
git diff --cached > "$PROVENANCE_DIR/git_diff_cached_before.patch"
```

Expected: `base_sha`, Design SHA, externally supplied approved Plan SHA, equal actual Plan SHA, and raw status/diff snapshots exist. The three raw Git snapshots are provenance only and are not required to equal post-implementation worktree output.

- [ ] **Step 2: Capture exact pre-existing path records.**

```bash
cat > "$PROVENANCE_DIR/capture_preexisting_paths.py" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

out = Path(sys.argv[1])
only_records_path = Path(sys.argv[2]) if len(sys.argv) == 3 else None


def status_entries():
    raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    )
    items = [part for part in raw.split(b"\0") if part]
    entries = []
    index = 0
    while index < len(items):
        item = items[index]
        status = item[:3].decode("utf-8", "surrogateescape")
        path_text = item[3:].decode("utf-8", "surrogateescape")
        index += 1
        rename_from = None
        if "R" in status[:2] or "C" in status[:2]:
            rename_from = items[index].decode("utf-8", "surrogateescape")
            index += 1
        entries.append((path_text, status, rename_from))
    return entries


def record_for(path_text, status, rename_from):
    path = Path(path_text)
    record = {"path": path_text, "porcelain": status}
    if rename_from is not None:
        record["rename_from"] = rename_from
    try:
        st = path.lstat()
    except FileNotFoundError:
        record.update({"lstat_type": "missing", "lstat_mode": None, "sha256": None})
        return record
    record["lstat_mode"] = st.st_mode
    if path.is_symlink():
        record["lstat_type"] = "symlink"
        record["symlink_target"] = os.readlink(path)
    elif path.is_file():
        record["lstat_type"] = "regular"
        record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    else:
        record["lstat_type"] = "other"
        record["sha256"] = None
    return record


entries = status_entries()
if only_records_path is None:
    records = [record_for(*entry) for entry in entries]
else:
    baseline = json.loads(only_records_path.read_text(encoding="utf-8"))
    current_by_path = {path: (status, rename_from) for path, status, rename_from in entries}
    records = [
        record_for(
            record["path"],
            *(current_by_path.get(record["path"], (None, None))),
        )
        for record in baseline
    ]
records.sort(key=lambda record: record["path"].encode("utf-8", "surrogateescape"))
out.write_text(json.dumps(records, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
PY
python3 "$PROVENANCE_DIR/capture_preexisting_paths.py" \
  "$PROVENANCE_DIR/preexisting_path_records.json"
```

Expected: the JSON record is canonical, deterministic, and contains every Task-0 dirty/untracked path with its original porcelain state and bytes or symlink target.

- [ ] **Step 3: Prove all mutable production/test paths are clean and record the exact config delta authorization.**

```bash
mutable_paths=(
  configs/base.py
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
)
for path in "${mutable_paths[@]}"; do
  git ls-files --error-unmatch -- "$path" >/dev/null || {
    echo "STOP: mutable path is not tracked: $path"
    exit 1
  }
done

git diff --exit-code -- \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py

git diff --cached --exit-code -- \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
```

Expected: exit 0. Otherwise STOP: `mutable_path_not_clean_at_execution_start`.

## Task 1: Make The Two Frozen V3 Config Authorities The Only Config Delta

**Design invariants:** INV-09, INV-13.  
**Files:**
- Modify: `configs/base.py`.
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`.

**Interfaces:**
- `base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION == 3` is the single schema/version authority.
- `base.EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS == 30 * 1000` is the sole releaseDate future-bound authority required by Design Sections 5.3 and 6.3.
- Add the test-only `validate_stage1_5d_v3_config_delta_for_plan(before: str, after: str) -> bool` in `test_stage1_5d_live_event_source_config.py`. It accepts only the same-position metadata assignment `2 -> 3` plus one immediately-following new clock-skew assignment with the exact `30 * 1000` AST; it rejects every other addition, deletion, reorder, name, target, or expression.

**Out of scope:** Do not modify `ALLOWED_CONFIG_DELTA_ASSIGNMENTS` or `validate_configs_base_ast_delta()`: they are the frozen schedule-revision producer Git-attestation policy and accept only its four prior assignments. No config delta beyond the two frozen assignments; no source URL, retry budget, parser, anchor, ExchangeInfo, formal, risk, or static-protection manifest exception.

- [ ] **Step 1: Write RED tests for the exact additive config authority.**

```python
def test_stage1_5d_v3_config_authorities_are_exact():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS == 30 * 1000


def test_validate_stage1_5d_v3_config_delta_for_plan_allows_only_frozen_delta():
    before = """\
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION = 2
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False
"""
    after = """\
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION = 3
EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS = 30 * 1000
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False
"""
    assert validate_stage1_5d_v3_config_delta_for_plan(before, after) is True
    assert validate_stage1_5d_v3_config_delta_for_plan(
        after, after.replace("30 * 1000", "30 * 1001")
    ) is False
```

Also retain assertions that unrelated assignment changes, any other new assignment, duplicate assignments, dynamic expressions, a misplaced clock-skew assignment, and statement reorder reject. Retain the existing schedule-revision production-attestation tests unchanged: its four-name allowlist must reject both V3 config names.

- [ ] **Step 2: Run focused RED tests.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  -k 'metadata_version or clock_skew or validate_stage1_5d_v3_config_delta_for_plan'
```

Expected: fails because metadata is still `2`, the Design-required clock-skew authority is absent, and the test-only comparator does not recognize the exact two-assignment delta.

- [ ] **Step 3: Apply the smallest config/proof change.**

Change only, in this exact order and with no intervening assignment:

```python
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION = 3
EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS = 30 * 1000
```

Add the test-only comparator in the existing config test module. It must accept the one same-position value change plus the directly-following `ast.BinOp(Constant(30), Mult(), Constant(1000))` addition while preserving every pre-existing AST node in order. It must not be imported by production code. Do not use a broad `configs/base.py` allowlist, a line-range exception, or the schedule-revision producer helper.

- [ ] **Step 4: Run GREEN tests and exact AST-delta proof.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  -k 'metadata_version or clock_skew or validate_stage1_5d_v3_config_delta_for_plan'

python3 - "$BASE_SHA" <<'PY'
import ast
import subprocess
import sys
from pathlib import Path

before = subprocess.check_output(["git", "show", f"{sys.argv[1]}:configs/base.py"], text=True)
after = Path("configs/base.py").read_text(encoding="utf-8")
before_nodes = ast.parse(before).body
after_nodes = ast.parse(after).body
assert len(after_nodes) == len(before_nodes) + 1

metadata = "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION"
clock_skew = "EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS"
index = next(
    index
    for index, node in enumerate(before_nodes)
    if isinstance(node, ast.Assign)
    and len(node.targets) == 1
    and isinstance(node.targets[0], ast.Name)
    and node.targets[0].id == metadata
)
assert all(
    ast.dump(before_node, include_attributes=False) == ast.dump(after_node, include_attributes=False)
    for before_node, after_node in zip(before_nodes[:index], after_nodes[:index])
)
before_node, after_node = before_nodes[index], after_nodes[index]
assert isinstance(before_node, ast.Assign) and isinstance(after_node, ast.Assign)
assert len(before_node.targets) == len(after_node.targets) == 1
assert isinstance(before_node.targets[0], ast.Name) and isinstance(after_node.targets[0], ast.Name)
assert before_node.targets[0].id == after_node.targets[0].id == metadata
assert isinstance(before_node.value, ast.Constant) and before_node.value.value == 2
assert isinstance(after_node.value, ast.Constant) and after_node.value.value == 3
inserted = after_nodes[index + 1]
assert isinstance(inserted, ast.Assign) and len(inserted.targets) == 1
assert isinstance(inserted.targets[0], ast.Name) and inserted.targets[0].id == clock_skew
assert ast.dump(inserted.value, include_attributes=False) == ast.dump(
    ast.parse("x = 30 * 1000").body[0].value, include_attributes=False
)
assert all(
    ast.dump(before_node, include_attributes=False) == ast.dump(after_node, include_attributes=False)
    for before_node, after_node in zip(before_nodes[index + 1:], after_nodes[index + 2:])
)
print({"changed_statement_index": index, "metadata": "2->3", "clock_skew": "30*1000"})
PY
```

Expected: focused tests pass; the AST proof confirms exactly one same-position metadata change and exactly one immediately-following clock-skew addition, without evaluating unrelated arithmetic config expressions.

## Task 2: Add The Strict V3 Scheduler-State Contract

**Design invariants:** INV-11, INV-13, INV-14, INV-16, INV-17.  
**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`.
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`.

**Interfaces:**
- Add `validate_stage1_5d_v3_scheduler_state(raw_state: object, *, expected_resume_provenance: dict[str, object]) -> list[str]`.
- Add `serialize_stage1_5d_v3_articles(articles: dict[str, dict]) -> dict[str, dict]`.
- Both operate on JSON values only. `[]` means valid; nonempty stable blocker codes mean invalid. The validator never mutates input.
- The V3 serializer accepts only the 86 Design §6.1 durable keys plus exactly these six runtime-only aliases: `raw`, `symbols`, `payload_sha256`, `last_bapi_payload_sha256`, `symbol_launch_times_utc`, and `symbol_effective_launch_times_utc`. It projects aliases out, rejects every other runtime key, validates the projected 86-key row, and never coerces or silently drops a durable field.

**Out of scope:** Do not alter legacy v1/v2 loader behavior or add migration. A resumable V3 root must never invoke the legacy/defaulting loader after preflight.

- [ ] **Step 1: Write RED unit tests for the frozen V3 grammar and semantic relations.**

Use a single `make_valid_v3_state()` helper in the existing test file. It must build a minimal valid state with:

```python
{
    "metadata_version": 3,
    "catalog_bootstrap_cutoff_ms": 1,
    "resume_provenance": EXPECTED_PROVENANCE,
    "articles": {ARTICLE_ID: VALID_V3_ARTICLE},
    "endpoint_health": VALID_ENDPOINT_HEALTH,
}
```

Add parameterized corruption tests for every required key omission, unknown key, string boolean, bool-as-int, invalid terminal tuple, invalid source article map key, invalid `source_published_at_ms`, missing `inflight_cycle`, malformed intent, and request-identity digest mismatch. Add the three semantic fixtures required by Design §6.1.2:

```python
row["candidate_symbols_ordered"] = ["BTCUSDT", "ETHUSDT"]
row["candidate_symbols_normalized"] = ["ETHUSDT"]
assert validate_stage1_5d_v3_scheduler_state(state, expected_resume_provenance=EXPECTED) == [
    "candidate_symbols_normalized_mismatch"
]

row["detail_fetch_attempt_count"] = row["detail_http_request_count"] + 1
assert "detail_request_counter_alias_mismatch" in validate_stage1_5d_v3_scheduler_state(...)

health["endpoint_health_by_source"]["bapi_article_detail_query"]["detail_endpoint_degraded_until_ms"] = 1
assert "endpoint_health_source_mirror_mismatch" in validate_stage1_5d_v3_scheduler_state(...)
```

Also prove a distinct `detail_retry_cycle_count` is valid, all four candidate identity fields must be null together, and the exact `ensure_ascii=True`, compact UTF-8 candidate hash is accepted. Add the remaining exact negative matrix from Design §6.1.1/§6.1.2: candidate hash mismatch; candidate version mismatch; every missing/unknown endpoint-health top-level and nested key; invalid endpoint result enum; oversized result array; invalid timestamp; invalid rate; invalid source key; invalid variant key; and the source-mirror mismatch. Each case must return its stable blocker before any loader/defaulting call.

Add a mechanical production inventory test. Its AST visitor must inspect the runner and scheduler functions that read, write, mutate, or serialize an article row, then partition every discovered literal article key into exactly one of the frozen 86 durable keys or the six runtime aliases above. The test must fail for an unclassified key, an unobserved durable key, a missing ExchangeInfo pending/retry field, or a runtime row containing an unknown key. Add runtime-projection fixtures proving that all six aliases are excluded from persisted output and that an unknown runtime key raises rather than being filtered.

- [ ] **Step 2: Run the contract RED suite.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  -k 'v3 or scheduler_state or endpoint_health or candidate_symbol'
```

Expected: fails because no strict V3 validator/serializer exists.

- [ ] **Step 3: Implement the contract in the scheduler module.**

Define immutable module constants for the exact 86 durable article keys, the exact six process-local aliases, D-04 terminal reason/type relation, endpoint result enum, allowed source/variant keys, exact nested health keys, and the Design-bounded health result-array limit. Project each runtime row before validation: permit only the 86 durable keys plus the six aliases; remove only those aliases; reject any other runtime key; then validate the projected state in this order:

```text
root exact keys/types/version/provenance
-> article-map id/key equality and exact 86-key set
-> scalar/list/object grammar, no bool-as-int
-> terminal/inflight relation
-> exact inflight operation target and SHA256 identity
-> candidate set identity all-null-or-all-valid relation
-> HTTP counter alias relation
-> endpoint-health exact grammar and source mirrors
```

Use `json.dumps(normalized, ensure_ascii=True, separators=(",", ":")).encode("utf-8")` for candidate identity; do not reuse the separate inflight `canonical_json_bytes()` grammar. `serialize_stage1_5d_v3_articles()` must first project and validate a synthetic state wrapper, then return detached JSON-compatible rows only when valid. The static inventory test is the authority proof that the projection vocabulary covers all current writer/read sites and the existing ExchangeInfo pending contract. Do not call `bool()`, `int()`, `setdefault()`, or mutate incoming rows during V3 serialization/validation.

- [ ] **Step 4: Run GREEN and existing scheduler regressions.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py
```

Expected: all scheduler tests pass, including existing fairness/endpoint-health behavior and every new V3 corruption case.

## Task 3: Add Read-Only Fresh/Resume Preflight Before Any Writer

**Design invariants:** INV-07, INV-08, INV-10, INV-11, INV-12, INV-13, INV-16, INV-17.  
**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`.
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`.
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`.

**Interfaces:**
- Add `build_stage1_5d_v3_resume_provenance(output_root: Path, startup_head_sha: str) -> dict[str, object]`.
- Add `preflight_stage1_5d_v3_root(output_root: Path, output_summary_path: Path, *, expected_resume_provenance: dict[str, object]) -> dict[str, object]`.
- Return shape: `{"kind": "fresh" | "resumable" | "rejected", "reason": str | None, "state": dict | None, "formal_completed_source_article_ids": set[str]}`.
- `main()` exits nonzero with `stage1_5d_v3_resume_preflight_rejected` for `kind == "rejected"`, before StorageGuard, `mkdir`, stream path creation, state/index/payload loading/rebuild, diagnostics, gate/summary writes, or network.
- Only after `kind == "fresh"`, `main()` creates the root once with `output_root.mkdir(parents=True, exist_ok=False)`; `FileExistsError` or a non-directory/symlink result is `stage1_5d_v3_fresh_root_creation_rejected`, with zero writer/network side effect.
- Before fresh/existing classification, `main()` canonicalizes both CLI paths and requires `output_summary_path.resolve(strict=False) == (output_root.resolve(strict=False) / "binance_futures_launch_smoke_summary.json")`; otherwise it stops as `stage1_5d_v3_output_summary_relation_rejected` before `mkdir`, any writer, or network.
- For a resumable V3 root, preflight reads/parses the scheduler-state bytes once, validates them once, deep-detaches the validated JSON state, and returns it. The runner consumes exactly `preflight_result["state"]`; it must not call `load_detail_retry_scheduler_state()` or any other loader/defaulting path for that root.

**Out of scope:** No `rebuild_missing_formal_launch_identity_index()` call or `inflight_cycle` diagnostic/clear recovery for a V3 existing root. No storage module change.

- [ ] **Step 1: Write RED preflight tests with a recursive artifact fingerprint.**

Add a test helper that records every relative path, type, size, and SHA256 below a temp root. Use it before and after each rejected invocation. Cover:

```python
assert preflight(...missing_root...) ["kind"] == "fresh"
assert preflight(...v2_root...) ["kind"] == "rejected"
assert preflight(...bad_resume_provenance...) ["kind"] == "rejected"
assert preflight(...unknown_child...) ["kind"] == "rejected"
assert preflight(...symlink_child...) ["kind"] == "rejected"
assert preflight(...unresolved_detail_intent...) ["kind"] == "rejected"
assert preflight(...active_plus_complete_formal...) ["kind"] == "rejected"
```

For each reject, assert identical fingerprints, zero mocked HTTP calls, no StorageGuard construction, no `build_stream_paths()`, no formal-index rebuild, and no diagnostic/gate/summary artifact. Add a deterministic fresh-root TOCTOU fixture: preflight returns `fresh`, the test creates a sentinel directory at `output_root` immediately before the runner's creation call, and the runner must stop with the sentinel fingerprint unchanged and zero network request.

Add two containment fixtures: a missing/fresh root plus an external `--output-summary`, and an existing valid V3 root plus an external `--output-summary`. Both must fail as `stage1_5d_v3_output_summary_relation_rejected` before root classification; assert zero `mkdir`, writer, StorageGuard, loader, and HTTP calls. Add a valid resumable V3 fixture that monkeypatches `load_detail_retry_scheduler_state()` to raise `AssertionError`; it must resume successfully from the detached preflight state, proving no second read/defaulting window exists.

Add every D-05 adversarial projection case exactly: missing, malformed, duplicate, collisioned, mismatched, provenance-inconsistent, and incomplete per-symbol event/index rows. Test each with and without a scheduler row as required by the Section 6.2.1 matrix. The only accepted crash state remains `formal_emission` plus a complete projection with exact event id and ordered symbols.

Add a closed-tree producer-equality test, not only a synthetic-tree acceptance test. Mechanically inventory every normal 1.5D `output_root` writer callsite, map each emitted relative path to the Section 6.2 grammar, and assert the producer surface equals that grammar, including daily JSONL streams and the exact existing `build_detail_payload_path()` `.bin` name. Any discovered path outside the frozen grammar fails the test; do not extend the allowlist in implementation.

- [ ] **Step 2: Run the preflight RED suite.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'v3_preflight or formal_completed or unresolved_intent or closed_tree or fresh_root_race'
```

Expected: fails because startup currently creates/loads mutable state, rebuilds index, and clears inflight reservations before a V3 preflight exists.

- [ ] **Step 3: Implement fresh/resumable classification and exact closed-tree validation.**

After CLI/static-proof validation and before fresh/existing classification or every output-root writer, canonicalize and compare the summary path:

```text
canonical output_summary_path
== canonical output_root / "binance_futures_launch_smoke_summary.json"
-> otherwise stage1_5d_v3_output_summary_relation_rejected
-> zero mkdir / writer / network
```

Then perform classification:

```text
absent output_root
-> kind=fresh; create once only with output_root.mkdir(parents=True, exist_ok=False)
-> FileExistsError or invalid post-create lstat: fail closed with no writer/network

existing output_root
-> lstat root
-> validate only Design §6.2 child/path grammar
-> parse raw state bytes
-> compare immutable provenance to expected runtime values
-> call validate_stage1_5d_v3_scheduler_state(...)
-> read formal event/index projection without rebuilding it
-> apply Section 6.2.1 matrix
-> deep-detach the validated state
-> kind=resumable only after every check succeeds
```

Use `lstat`, reject symlinks/devices/FIFOs/sockets, and accept only the Design allowlisted daily JSONL streams and the existing exact raw detail payload grammar. Read-only preflight must not create a missing directory. Do not retain the current `exist_ok=True` root creation. For a valid `formal_emission` crash-after-completion exception, perform no cleanup inside preflight; return its exact row identity for Task 5's guarded post-preflight cleanup. A resumable V3 runner must use only `preflight_result["state"]`; legacy `load_detail_retry_scheduler_state()` remains unchanged for non-V3 compatibility/tests and is forbidden on the V3 resume path.

- [ ] **Step 4: Run GREEN preflight and unchanged storage/formal regressions.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'v3_preflight or formal_completed or unresolved_intent or closed_tree or fresh_root_race'
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py
```

Expected: every V3 reject has zero side effects; valid V3 roots resume; unchanged storage/formal suites pass.

## Task 4: Implement Bootstrap, Admission Tombstones, And Durable Gate Derivation

**Design invariants:** INV-01, INV-02, INV-03, INV-04, INV-05, INV-06, INV-08, INV-14.  
**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`.
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`.

**Interfaces:**
- Add `classify_stage1_5d_catalog_admission(article: dict, *, cutoff_ms: int, detected_at_ms: int, formal_completed_ids: set[str], persisted_row: dict | None) -> str` with only `formal_completed`, `persisted_terminal`, `source_published_at_invalid`, `historical_prebootstrap_catalog_article`, or `active` outcomes.
- Add `build_stage1_5d_terminal_tombstone(existing: dict, *, reason: str, now_ms: int, source_published_at_ms: int | None) -> dict`.
- The terminal helper emits a full valid V3 article row and preserves actual prior request counters; local bootstrap/historical/invalid outcomes have `detail_http_request_count == detail_fetch_attempt_count == 0`.

**Out of scope:** Do not alter parser classification, title/BAPI/support parsing, existing post-bootstrap detail criteria, `first_bar_queue` implementation, runtime-gate threshold, or 1.5F.

- [ ] **Step 1: Write RED runner fixtures for trusted bootstrap and D-03 precedence.**

Use mocked catalog/detail/ExchangeInfo/Kline clients and a fresh temp root. Add these exact cases:

```text
trusted first catalog poll with POPMART/UNITREE-like rows
-> cutoff checkpoint + terminal rows
-> zero detail/ExchangeInfo/Kline/formal/first_bar_queue/F input
-> otherwise READY

first poll source_format_drift or schema_parse_error
-> `cycle_res["heartbeat"]["poll_success"] is not True` or parser-produced catalog article collection is not a list
-> cutoff absent, no `detail_retry_scheduler_state.json` write, zero tombstone/detail/queue

later valid releaseDate < cutoff and title classifier yields ["ABCUSDT"]
-> one historical terminal across repeated poll and restart
-> reducer runs before title-symbol/candidate-validation logic
-> zero detail, candidate-validation ExchangeInfo, formal, first_bar_queue, and F input

missing/bool/string/zero/negative/future-by-one releaseDate
-> source_published_at_invalid with source_published_at_ms=null, zero HTTP

releaseDate == detected_at_ms + skew
-> active existing path

valid active candidate reaches detail_never_attempted_budget_starved
-> durable terminal and restart-derived gate DEGRADED
```

Also prove the trusted-bootstrap predicate exactly: `cycle_res["heartbeat"]["poll_success"] is True` **and** the parser-produced catalog article collection is a `list`. A fresh, unbootstrapped root receiving any untrusted poll writes no scheduler-state checkpoint, so it cannot persist an invalid V3 state without a positive cutoff. Also prove formal-completed and persisted-terminal checks run before timestamp/detail logic, and neither formal-completed duplicate nor terminal duplicate removes a pre-existing in-memory first-bar item.

For each `catalog_bootstrap_preexisting`, `historical_prebootstrap_catalog_article`, or `source_published_at_invalid` transition, the scheduler tombstone checkpoint plus read-back is the sole lifecycle authority. Only after that checkpoint succeeds, use the existing `append_stage1_5d_diagnostic()` path to append one compact non-authoritative audit row to `detail_retry_terminal_diagnostics/`, with `source_article_id`, terminal reason, and terminal timestamp. Do not emit a formal-contract-invalid wrapper. On an uncrashed successful transition, repeated catalog polls and restart observe the durable terminal first and emit no additional row. If the subsequent diagnostic append fails or the process crashes before it completes, do not roll back, reopen, reconstruct, or re-append the lifecycle authority on restart; existing StorageGuard failure behavior remains authoritative. Test the normal path has one matching row, the diagnostic-write-failure path retains the tombstone with zero downstream side effects, and neither path degrades the runtime gate from these local rejections.

In `test_stage1_5f_live_depth_observer_loader.py`, add one tmp-path D-to-F integration test only. It must construct a fresh synthetic D v3 root using the existing event/gate formats; call the existing F `validate_stage1_5d_runtime_gate()` with that exact events glob; and use the existing `verify_stage1_5f_consumer_proof()` contract/summary fixture to prove exact D root-ID binding plus static/runtime attestation. It must prove no bootstrap terminal, later historical terminal, incomplete article, or formal-completed duplicate produces an F observation candidate. The test must make no network request and must not modify 1.5F production code.

- [ ] **Step 2: Run the reducer RED suite.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'bootstrap or historical or release_date or publication or starvation or terminal_non_reentry'
```

Expected: fails because current startup has no cutoff/tombstones and current admission re-adds prior terminal articles.

- [ ] **Step 3: Implement only the D-02/D-03/D-04 reducers.**

On the first parser-trusted poll of a fresh root, where `cycle_res["heartbeat"]["poll_success"] is True` and the parser-produced catalog article collection is a `list`, construct all bootstrap terminal rows, serialize/write/read-back the V3 scheduler checkpoint with cutoff/provenance/health, discard that poll's events and `first_bar_queue`, then start normal admission only on later trusted polls. Before that condition is first true, retain existing poll-failure behavior but do not write `detail_retry_scheduler_state.json`; no V3 state may exist without a positive cutoff. For later classified rows, apply the exact non-reordered reducer before every title-derived-symbol or candidate-validation branch:

```text
formal completed -> skip catalog admission only
persisted terminal -> skip catalog admission only
invalid releaseDate -> guarded terminal checkpoint
releaseDate < cutoff -> guarded terminal checkpoint
otherwise -> existing active path
```

Derive `scheduler_starved_expired_count` each loop from durable terminal rows whose `terminal_failure_type == "detail_never_attempted_budget_starved"`; do not retain a process-only resettable counter. On every local terminal checkpoint failure, stop before detail/ExchangeInfo/formal/queue side effects. A later diagnostic failure never rolls back or reopens the already durable terminal. Keep every tombstone until the root is retired.

- [ ] **Step 4: Run GREEN reducer suite plus 1.5F gate compatibility.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'bootstrap or historical or release_date or publication or starvation or terminal_non_reentry'
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -k 'stage1_5d_v3 or bootstrap or historical or formal'
```

Expected: local rejections leave D otherwise READY; real starvation remains DEGRADED; the existing F consumer blocks non-READY input; and the D-to-F synthetic root binding admits no rejected/pre-bootstrap/formal-completed article.

## Task 5: Enforce Exact Scheduler-Owned WAL And Formal Completion Ordering

**Design invariants:** INV-06, INV-08, INV-10, INV-12, INV-16.  
**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`.
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`.

**Interfaces:**
- Add `build_stage1_5d_inflight_cycle(*, source_article_id: str, operation: str, cycle: int, request_ordinal: int, reserved_at_ms: int, request_target: dict) -> dict`.
- Add `checkpoint_stage1_5d_v3_scheduler_state(...) -> None`, which writes and read-backs a fully valid V3 state and leaves an intent intact when a post-side-effect finalization fails.
- `record_formal_futures_launch_event()` retains event-then-index order; Task 5 calls it only after a durable `formal_emission` intent.

**Out of scope:** Do not add Kline intent, writer lock, queue persistence, index rebuild, or a generic transaction framework.

- [ ] **Step 1: Write RED tests for every scheduler-owned side effect and crash point.**

Add deterministic mocks that record side-effect order. Test:

```text
detail BAPI request: durable matching detail_request intent -> one HTTP -> raw/manifest/outcome checkpoint -> intent null
support primary and support fallback: distinct requested_url/variant/ordinal/digest intents before each URL
candidate-validation ExchangeInfo cache miss: durable sorted-symbol exchangeinfo_request intent -> one request -> manifest/outcome -> intent null
formal: durable formal_emission intent -> event -> complete index -> active-row removal
```

For each operation, force failure after intent and before side effect, and after side effect before final checkpoint. Assert unresolved intent remains, restart rejects with zero network/mutation, and no diagnostic-clear/retry path exists. Test the sole exception: a `formal_emission` intent plus exactly matching full projection receives only a guarded active-row removal; event-id/symbol mismatch rejects and cleanup failure writes no second side effect.

Add an exhaustive AST inventory over every production destructive mutation of `detail_retry_state`, not just `.pop(...)`: `.pop(...)`, `del detail_retry_state[...]`, `.clear()`, dictionary-comprehension/filter replacement, and whole-map replacement that can remove an active row. Each discovered removal must map to either a D-04 terminal row or a complete formal event/index authority; an unclassified removal fails. Add a detail failure regression where `detail_fetch_attempt_count` remains exactly equal to `detail_http_request_count`; do not increment it a second time after a request has already incremented the HTTP count.

- [ ] **Step 2: Run the WAL RED suite.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'inflight or reservation or formal_completion or fallback_identity or crash or terminal_transition or counter_alias'
```

Expected: fails because current startup clears inflight cycles, allows formal-index rebuild, and several removals are not durable V3 successors.

- [ ] **Step 3: Implement the exact three-operation WAL only.**

Replace the current `{cycle, reserved_at_ms}` reservation with the Design §6.1 exact seven-key intent and SHA256. Persist/read back before each actual BAPI/support URL, candidate-validation ExchangeInfo request, and formal event. Bind support intent to the exact requested pre-redirect URL and variant. Preserve the intent on any post-intent failure.

Replace every direct or equivalent scheduler-row removal with one explicit successor:

```text
local/retry/failure terminal -> checkpoint full D-04 tombstone -> remove only in-memory active selection
formal success -> intent -> event -> full index -> checkpoint removal
```

Do not remove existing first-bar queue work. Remove the V3-incompatible startup behavior that appends a diagnostic, clears inflight state, and continues. Remove only the redundant post-request `detail_fetch_attempt_count += 1` mutation that would violate the frozen HTTP-counter alias; retain logical `detail_retry_cycle_count` as independent scheduler state.

- [ ] **Step 4: Run GREEN WAL/formal regressions.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'inflight or reservation or formal_completion or fallback_identity or crash or terminal_transition or counter_alias'
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py
```

Expected: every scheduler-owned operation is intent-before-side-effect; incomplete paths fail closed; formal/index/storage behavior remains compatible.

## Task 6: Run Scope, Regression, And Completion Gates

**Design invariants:** INV-01 through INV-17.  
**Files:**
- Modify: none beyond prior tasks.
- Verify: all allowed verification paths and read-only affected suites.

**Interfaces:**
- Produces test/ruff/diff evidence only.
- Does not grant implementation completion, commit, deployment, or runtime authority until `audit-plan-completion` returns `complete`.

**Out of scope:** Do not run against a VPS or create a live D/F root.

- [ ] **Step 1: Run focused tests in dependency order.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
```

Expected: pass with all new V3 contract, preflight, bootstrap, reducer, WAL, formal-completion, and no-side-effect tests.

- [ ] **Step 2: Run affected-consumer and D-to-F integration regression suites.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_a827_boundary_regression.py \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py
```

Expected: pass. Any required source change outside the Allowed Change Scope is STOP: `design_or_plan_delta_required`.

- [ ] **Step 3: Run static, scope, and safety gates.**

```bash
.venv/bin/ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py

git diff --check
python3 - <<'PY'
from configs import base
from src.risk.limits import RiskLimits
assert base.RISK_LIVE_TRADING_ENABLED is False
assert RiskLimits.live_trading_enabled is False
print('RISK_LIVE_TRADING_ENABLED=False')
PY

```

Expected: ruff and diff checks pass; both safety assertions are false. Step 4 performs the separate pre-existing-path and implementation-scope proofs.

- [ ] **Step 4: Prove pre-existing-path integrity and implementation scope independently.**

```bash
python3 "$PROVENANCE_DIR/capture_preexisting_paths.py" \
  "$PROVENANCE_DIR/preexisting_path_records_after.json" \
  "$PROVENANCE_DIR/preexisting_path_records.json"
cmp -s "$PROVENANCE_DIR/preexisting_path_records.json" \
  "$PROVENANCE_DIR/preexisting_path_records_after.json"

python3 - "$BASE_SHA" "$PROVENANCE_DIR/preexisting_path_records.json" <<'PY'
import json
import subprocess
import sys

base_sha, records_path = sys.argv[1:]
records = json.load(open(records_path, encoding="utf-8"))
preexisting = {
    name
    for record in records
    for name in (record["path"], record.get("rename_from"))
    if name is not None
}
raw = subprocess.check_output(
    ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"]
)
items = [part for part in raw.split(b"\0") if part]
current = []
index = 0
while index < len(items):
    item = items[index]
    status = item[:3].decode("utf-8", "surrogateescape")
    path = item[3:].decode("utf-8", "surrogateescape")
    index += 1
    rename_from = None
    if "R" in status[:2] or "C" in status[:2]:
        rename_from = items[index].decode("utf-8", "surrogateescape")
        index += 1
    current.append((path, status, rename_from))

allowed = {
    "configs/base.py",
    "src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py",
    "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py",
    "tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py",
    "tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py",
}
remaining = [
    (path, status, rename_from)
    for path, status, rename_from in current
    if path not in preexisting and rename_from not in preexisting
]
unexpected_status_paths = sorted({path for path, _, _ in remaining} - allowed)
new_untracked = sorted(path for path, status, _ in remaining if status == "?? ")
assert not unexpected_status_paths, {"unexpected_status_paths": unexpected_status_paths, "remaining": remaining}
assert not new_untracked, {"new_untracked_paths": new_untracked}

changed = set(
    subprocess.check_output(["git", "diff", "--name-only", base_sha, "--"], text=True).splitlines()
)
new_tracked = sorted(changed - preexisting)
unexpected_tracked = sorted(set(new_tracked) - allowed)
assert not unexpected_tracked, {"unexpected_new_tracked_paths": unexpected_tracked, "new_tracked": new_tracked}
print({"new_status_paths": sorted(path for path, _, _ in remaining), "new_tracked_paths": new_tracked})
PY
```

Expected: `cmp` proves only Task-0 pre-existing paths retain their original porcelain state and bytes/symlink/missing state. The final status then proves every remaining path is an allowed tracked implementation/test path, rejects every newly created untracked path, and the `BASE_SHA` tracked diff independently remains within the same allowlist.

- [ ] **Step 5: Run the mandatory independent completion audit.**

Provide the approved Design bytes, externally supplied `EXPECTED_APPROVED_PLAN_SHA256`, matching Task-0 actual Plan SHA, `BASE_SHA`, Task-0 provenance directory, final status/diff scope output, all commands/results above, and the exact config AST proof to `.agent/skills/audit-plan-completion`.

Expected: `complete`. If verdict is `incomplete` or `blocked`, use `.agent/workflows/remediate-completion-audit.md`; do not claim completion, commit, deploy, or start a VPS root.

## Plan Review Checklist

- [ ] Every INV-01 through INV-17 maps to a Task and mechanical evidence.
- [ ] `configs/base.py` is protected by the exact metadata `2 -> 3` change plus the immediately-following exact `30 * 1000` clock-skew addition, and no other AST delta.
- [ ] V3 validation parses once before any output-root mutation/network request; resumable execution consumes only its detached preflight state and never invokes loader/defaulting.
- [ ] First-bar/Kline ownership remains unchanged and is explicitly tested against accidental suppression.
- [ ] Every scheduler-owned side effect has a pre-intent, durable outcome, and crash path; no Kline WAL is introduced.
- [ ] Existing v2 roots reject rather than migrate or rebuild.
- [ ] No task grants runtime, deployment, execution, alpha, paper-trading, or live-trading authority.
- [ ] No placeholder, broad allowlist, global autofix, or unbounded cleanup command remains.

## Review Gate

This Plan is `plan_draft`. It must be reviewed with `.agent/skills/reviewing-implementation-plans` and receive `Approve`, then receive explicit user approval, before any code modification or execution workflow. The only post-implementation operational claim permitted by the Design remains a fresh-root lifecycle correctness claim; it does not establish complete source coverage, alpha, tradability, execution feasibility, or profit.
