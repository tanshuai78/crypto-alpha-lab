# Stage 1.6A BAPI H2 Versioned Body Grammar Replay Delta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the exact G2 `h2` BAPI body grammar while preserving independent G1 replay for completed Stage 1.6A Adapter v2 audit roots.

**Architecture:** Keep the current sealed-export adapter and its completed-consumer storage loader. Introduce two immutable persisted grammar pairs in the adapter, pass one explicit pair through every reduction, and make the completed consumer select and validate that pair before source-byte reduction. New CLI writes use G2 only; existing G1 roots are read-only and replay under G1.

**Tech Stack:** Python 3.12, standard library (`dataclasses`, `hashlib`, `json`, `typing`), pytest, ruff.

**Approved Design Authority:**

- H2 Delta: `docs/designs/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-design_CN.md` (`SHA-256: f31e9a64f42fcd1eccfab94efa5c9328fbdc154a9ae70880e359bfc701306987`, approved review bytes)
- Parent v2: `docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md` (`SHA-256: 1cb90f89113ceda4d2037cb62d60b8a9f769f7d58c467ad0e515332bc13563fd`)
- Derived artifact schema delta: `docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-adapter-derived-artifact-schema-delta-design_CN.md` (`SHA-256: 2572849bf7df9154170ebc28f9687315728566a7c9498153f346d61308aaeb34`)
- TerminalStatus correction: `docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6b-terminal-status-field-contract-correction-design_CN.md` (`SHA-256: 4bc7bc60a5435f9d71735319eac0dc84bf655bd94bc5f065652545f472596aae`)
- Implementation baseline: `d1f7ee2d9d8eb37389feeed912ff13d34fba8e05`

## Global Constraints

- The adapter artifact profile remains `stage1_6a_sealed_export_source_audit_v2`; no durable artifact key set or schema version changes.
- Only pairs `{stage1_6a_bapi_body_tree_v1, stage1_6a_extractor_v1}` (G1) and `{stage1_6a_bapi_body_tree_v2, stage1_6a_extractor_v2}` (G2) are valid.
- G2 is exactly G1 plus `h2` in allowed and block tags. `h1`, `h5`, unknown tags, malformed nodes, and non-empty `br.child` remain fail-closed.
- No Stage 1.6B, Stage 1.5, `configs/base.py`, threshold, network, VPS, PIT, replay, risk, paper-trading, live-trading, or execution change is authorized.
- Do not mutate existing G1 audit roots. G2 writes use a fresh output root and completion manifest last.
- `persist_adapter_audit()` is the production new-root boundary: it must reject every reduction whose pair is not exactly `G2_GRAMMAR_PAIR`. G1 compatibility is read-only completed-consumer replay only.
- Do not modify `stage1_6a_futures_delisting_audit.py` or `stage1_6a_futures_delisting_models.py`; their independent fixture-audit constants are not this adapter contract.
- Do not commit automatically. A separate completion audit must return `complete` before any later commit decision.

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py`
- `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py`
- `scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py`
- `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py`

Allowed documentation paths:
- `docs/plans/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-implementation-plan_CN.md`
- `docs/reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md`  # only if produced by the completion audit

Allowed generated/runtime artifacts:
- `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/h2_g2_*`  # generated only; never committed

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py`
  - compatibility evidence: `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py`
  - compatibility evidence: Task 0 asserts its exact existing fixture constants and Task 5 proves zero diff; targeted old-audit regression remains GREEN.
- `configs/base.py`
  - compatibility evidence: Task 0 asserts all seven frozen historical thresholds exactly.

Forbidden:
- Any mutation outside the allowed paths.
- Any artifact-profile/schema/key-set/threshold change or compatibility alias.
- Any change to `stage1_6a_futures_delisting_audit.py`, `stage1_6a_futures_delisting_models.py`, Stage 1.6B producer/storage, or existing sealed exports.
- Full-repository formatter/autofix, destructive cleanup, deployment, network collection, or trading/risk permission change.

## Invariant Map

| Design invariant | Task(s) | Mechanical proof |
|---|---|---|
| INV-H2-01, INV-H2-03 | 1 | G1 rejects `h2`; G2 changes no tag except `h2`. |
| INV-H2-02 | 1 | Exact G2 heading LF golden test. |
| INV-H2-04, INV-H2-04a | 3 | Consumer selects pair before reduction and rejects mixed/unknown/absent or row/evidence mismatch. |
| INV-H2-05 | 2 | G1/G2 semantic IDs differ for the same revision. |
| INV-H2-06 | 2, 3 | Existing exact schemas remain unchanged; only existing version values differ by pair. |
| INV-H2-07 | 0, 2, 3, 4 | Frozen G1 root replays read-only; new writer rejects G1 and writes only fresh G2 roots. |
| INV-H2-08, INV-H2-09 | 0, 4 | Frozen REEF bytes/h2 preflight; local G2 output has trusted in-scope REEFUSDT child and settlement timestamp. |
| INV-H2-10 | 4, 5 | G2 output retains exact all-false authority flags; completion audit remains design-only. |

### Task 0: Authority, Workspace, And Frozen-Input Preflight

**Design invariants:** INV-H2-01, INV-H2-07, INV-H2-08, INV-H2-09, INV-H2-10.

**Files:**
- Modify: none.
- Verify: all files in Allowed Change Scope, parent authorities, `configs/base.py`.
- Generated: a local provenance transcript outside the repository or under the fresh runtime root; do not commit it.

**Interfaces:**
- Consumes: the four authority files, frozen reference export `e9ec315753ead7a975c8df87de8fc1670e8b8eb890376a16eca4bb44b2007734`, and its frozen REEF raw bytes.
- Produces: a PASS transcript before any `src/` or test edit; otherwise STOP.

- [ ] **Step 1: Bind execution authority and freeze workspace provenance**

```bash
set -euo pipefail
export BASE_SHA="d1f7ee2d9d8eb37389feeed912ff13d34fba8e05"
export PLAN_PATH="docs/plans/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-implementation-plan_CN.md"
export H2_DESIGN_PATH="docs/designs/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-design_CN.md"
export REF_EXPORT="data/external_signal_shadow/stage1_6b/historical_backfill/hist_delisting_network_retry_20260823T094411Z/sealed_exports/e9ec315753ead7a975c8df87de8fc1670e8b8eb890376a16eca4bb44b2007734"
export FROZEN_G1_ROOT="data/external_signal_shadow/stage1_6a/sealed_export_source_audits/sealed_export_audit_e9ec315753ea_20260823T095847Z"
export PROVENANCE_FILE="${TMPDIR:-/tmp}/stage1_6a_h2_g2_$(date -u +%Y%m%dT%H%M%SZ)_provenance.json"

git merge-base --is-ancestor "$BASE_SHA" HEAD
test -n "${APPROVED_PLAN_SHA:?STOP: set APPROVED_PLAN_SHA from the post-review user approval record}"
test "$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}')" = "$APPROVED_PLAN_SHA"
test "$(shasum -a 256 "$H2_DESIGN_PATH" | awk '{print $1}')" = "f31e9a64f42fcd1eccfab94efa5c9328fbdc154a9ae70880e359bfc701306987"
test "$(shasum -a 256 docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md | awk '{print $1}')" = "1cb90f89113ceda4d2037cb62d60b8a9f769f7d58c467ad0e515332bc13563fd"
test "$(shasum -a 256 docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-adapter-derived-artifact-schema-delta-design_CN.md | awk '{print $1}')" = "2572849bf7df9154170ebc28f9687315728566a7c9498153f346d61308aaeb34"
test "$(shasum -a 256 docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6b-terminal-status-field-contract-correction-design_CN.md | awk '{print $1}')" = "4bc7bc60a5435f9d71735319eac0dc84bf655bd94bc5f065652545f472596aae"

# No pre-existing executable/test/config change may enter this execution.
git diff --quiet "$BASE_SHA" -- configs src scripts tests || {
  echo "STOP: protected tracked tree differs from implementation baseline" >&2
  exit 1
}
test -z "$(git ls-files --others --exclude-standard -- configs src scripts tests)" || {
  echo "STOP: protected tree contains pre-existing untracked files" >&2
  exit 1
}

# Freeze every remaining dirty/untracked path by status and content identity.
python3 - "$PROVENANCE_FILE" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

def git(*args):
    return subprocess.check_output(["git", *args])

def state(path):
    p = Path(path)
    if not p.exists() and not p.is_symlink():
        return {"kind": "missing", "sha256": None}
    if p.is_symlink():
        return {"kind": "symlink", "sha256": hashlib.sha256(os.readlink(p).encode()).hexdigest()}
    if p.is_file():
        return {"kind": "file", "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    raise SystemExit(f"STOP: unsupported provenance path type: {path}")

raw = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
records = {}
for item in raw.split(b"\0"):
    if not item:
        continue
    status = item[:2].decode("ascii")
    if "R" in status or "C" in status:
        raise SystemExit("STOP: rename/copy workspace state requires a separate provenance review")
    if item[2:3] != b" ":
        raise SystemExit(f"STOP: malformed porcelain record: {item!r}")
    path = item[3:].decode("utf-8", "surrogateescape")
    records[path] = {"status": status, **state(path)}

Path(sys.argv[1]).write_text(json.dumps({"records": records}, indent=2, sort_keys=True) + "\n")
print({"provenance_file": sys.argv[1], "preexisting_paths": sorted(records)})
PY
```

Expected: every hash and ancestry check passes; `configs/src/scripts/tests` are clean relative to `BASE_SHA` and contain no untracked file. All other dirty/untracked paths are frozen by status and SHA-256. Any rename/copy state or mismatch is a STOP.

- [ ] **Step 2: Verify frozen thresholds, REEF lineage, and current G1 behavior before code changes**

```bash
PYTHONPATH=src:. .venv/bin/python - "$REF_EXPORT" <<'PY'
import hashlib, json, sys
from pathlib import Path
from configs import base
from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter import (
    load_verified_source_snapshot,
    reduce_verified_snapshot,
)
from src.research.external_signal_shadow.stage1_6a_futures_delisting_models import (
    BODY_NORMALIZATION_VERSION as FIXTURE_BODY_NORMALIZATION_VERSION,
    SEMANTIC_EXTRACTOR_VERSION as FIXTURE_SEMANTIC_EXTRACTOR_VERSION,
)

expected_thresholds = {
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS": 30,
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS": 10,
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS": 3,
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO": 0.95,
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO": 0.95,
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO": 0.95,
    "EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT": 0,
}
assert {name: getattr(base, name) for name in expected_thresholds} == expected_thresholds
assert base.RISK_LIVE_TRADING_ENABLED is False
assert FIXTURE_BODY_NORMALIZATION_VERSION == "stage1_6a_norm_v1"
assert FIXTURE_SEMANTIC_EXTRACTOR_VERSION == "stage1_6a_extractor_v1"

export_dir = Path(sys.argv[1])
assert export_dir.name == "e9ec315753ead7a975c8df87de8fc1670e8b8eb890376a16eca4bb44b2007734"
snapshot = load_verified_source_snapshot(Path.cwd(), export_dir)
aid = "572715f2d96e47769ebbb967c2a6e445"
raw_sha = "5f9d2b632423e3d256ab6dd8221ce0809037c5772e8c123c6a66fdd49ea77e27"
raw_rel = f"raw_payloads/detail/{aid}/{raw_sha}.bin"
assert any(row["source_article_id"] == aid for row in snapshot.discoveries)
observation = next(row for row in snapshot.observations if row["source_article_id"] == aid)
revision = next(row for row in snapshot.revisions if row["source_article_id"] == aid)
assert observation["trust_validation_status"] == "trusted"
assert observation["raw_payload_sha256"] == raw_sha
assert observation["raw_payload_relative_path"] == raw_rel
assert revision["detail_raw_sha256"] == raw_sha
assert revision["raw_payload_relative_path"] == raw_rel
raw = export_dir / raw_rel
assert hashlib.sha256(raw.read_bytes()).hexdigest() == "5f9d2b632423e3d256ab6dd8221ce0809037c5772e8c123c6a66fdd49ea77e27"
body = json.loads(json.loads(raw.read_text(encoding="utf-8"))["data"]["body"])
assert body["child"][4]["node"] == "element"
assert body["child"][4]["tag"] == "h2"
current = reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000000000)
reef_outcome = next(row for row in current.parent_outcomes if row["source_article_id"] == aid)
assert reef_outcome["detail_authority_status"] == "body_parse_unresolved"
print({"reference_export": "verified", "reef_h2_index": 4, "reef_g1_status": reef_outcome["detail_authority_status"], "thresholds": expected_thresholds})
PY
```

Expected: the export, ArticleDiscovery, trusted DetailObservation, DetailRevision, raw path/hash, current G1 `body_parse_unresolved`, seven values, fixture constants, and `root.child[4].tag == h2` are exact. Any difference is a STOP; do not substitute a different source export or payload.

- [ ] **Step 3: Establish the read-only G1 compatibility baseline and caller closure**

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py -q
```

Then run:

```bash
PYTHONPATH=src:. .venv/bin/python - "$FROZEN_G1_ROOT" "$REF_EXPORT" <<'PY'
import hashlib, sys
from pathlib import Path
from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter_storage import load_completed_adapter_audit

root, export = map(Path, sys.argv[1:])
summary = root / "stage1_6a_futures_delisting_source_audit_summary.json"
completion = root / "completion_manifest.json"
assert hashlib.sha256(summary.read_bytes()).hexdigest() == "f746860704ed9ffafbb74fd382a41936f3a26e5aecce15acbc15db91d80174bf"
assert hashlib.sha256(completion.read_bytes()).hexdigest() == "cc74c6cc15bdbddd1b11cf4fc7200dc33d8a50b8e01d30f599e74cdaa5cca0a0"
loaded = load_completed_adapter_audit(Path.cwd(), root, export)
assert (loaded["summary"]["body_normalization_version"], loaded["summary"]["semantic_extractor_version"]) == (
    "stage1_6a_bapi_body_tree_v1", "stage1_6a_extractor_v1")
assert loaded["completion_manifest"]["source_audit_passed"] is False
print({"frozen_g1_replay": "PASS", "historical_events": loaded["summary"]["metrics"]["historical_events_found"]})
PY

rg -n 'parse_and_normalize_bapi_body\(|reduce_verified_snapshot\(|ALLOWED_TAGS|BLOCK_TAGS|BODY_NORMALIZATION_VERSION|SEMANTIC_EXTRACTOR_VERSION' src scripts tests
```

Expected: baseline tests are GREEN; the frozen G1 root hashes and independently replays `false`; and the caller inventory is limited to the three planned production locations, the two planned test files, plus the explicitly unchanged fixture-audit/model constants. Any additional production caller, direct global grammar consumer, or test caller outside the two verification files is a STOP and requires Plan revision before implementation.

**Out of scope:** no source, test, config, or artifact mutation.

### Task 1: RED Grammar-Pair Selection And Exact H2 Parsing

**Design invariants:** INV-H2-01, INV-H2-02, INV-H2-03.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py:25-31,77-180`.
- Test: `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py`.

**Interfaces:**
- Produces: `GrammarPair`, `G1_GRAMMAR_PAIR`, `G2_GRAMMAR_PAIR`, `grammar_rules_for_pair(grammar_pair)`, and `parse_and_normalize_bapi_body(..., grammar_pair=...)`.
- Consumes: only the exact two persisted string pairs; no models constant or mutable global grammar state.

- [ ] **Step 1: Write the failing parser tests**

Add tests with a synthetic BAPI envelope containing this body fragment:

```python
h2_body = [
    {"node": "element", "tag": "h2", "child": [{"node": "text", "text": "Announcement"}]},
    {"node": "element", "tag": "p", "child": [{"node": "text", "text": "Binance Futures will delist the USDⓈ-M TOKENAUSDT Perpetual Contract at 2026-08-25 09:00 (UTC)."}]},
]

g1_result, g1_error = adapter.parse_and_normalize_bapi_body(
    trusted_article(body_nodes=h2_body)["raw_payload_bytes"],
    article_id="1" * 32,
    grammar_pair=adapter.G1_GRAMMAR_PAIR,
)
assert g1_result is None
assert g1_error == "body_parse_unresolved"

g2_result, g2_error = adapter.parse_and_normalize_bapi_body(
    trusted_article(body_nodes=h2_body)["raw_payload_bytes"],
    article_id="1" * 32,
    grammar_pair=adapter.G2_GRAMMAR_PAIR,
)
assert g2_error is None
assert g2_result["normalized_body"] == "Announcement\nBinance Futures will delist the USDⓈ-M TOKENAUSDT Perpetual Contract at 2026-08-25 09:00 (UTC)."
```

Also add parametrized G2 failures for `h1`, `h5`, an unknown tag, malformed `h2.child`, invalid `h2.attr`, and non-empty `br.child`; each must return `(None, "body_parse_unresolved")`. Add an unsupported pair test expecting `AdapterInputError("unsupported_grammar_pair")`.

- [ ] **Step 2: Run the new tests and confirm RED**

Run:

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  -k 'h2 or grammar_pair' -q
```

Expected: FAIL because `G1_GRAMMAR_PAIR`, `G2_GRAMMAR_PAIR`, and the required `grammar_pair` argument do not exist yet.

- [ ] **Step 3: Implement immutable grammar-pair lookup and parser dispatch**

Replace the single version/tag globals with this local adapter contract; do not add a new module, class hierarchy, CLI flag, alias, or model constant:

```python
GrammarPair = tuple[str, str]

G1_GRAMMAR_PAIR: GrammarPair = (
    "stage1_6a_bapi_body_tree_v1",
    "stage1_6a_extractor_v1",
)
G2_GRAMMAR_PAIR: GrammarPair = (
    "stage1_6a_bapi_body_tree_v2",
    "stage1_6a_extractor_v2",
)
_GRAMMAR_RULES: dict[GrammarPair, tuple[frozenset[str], frozenset[str]]] = {
    G1_GRAMMAR_PAIR: (
        frozenset({"a", "br", "em", "h3", "h4", "li", "p", "span", "strong", "table", "tbody", "td", "tr", "u", "ul"}),
        frozenset({"p", "h3", "h4", "li", "tr", "td"}),
    ),
    G2_GRAMMAR_PAIR: (
        frozenset({"a", "br", "em", "h2", "h3", "h4", "li", "p", "span", "strong", "table", "tbody", "td", "tr", "u", "ul"}),
        frozenset({"h2", "h3", "h4", "li", "p", "tr", "td"}),
    ),
}

def grammar_rules_for_pair(grammar_pair: GrammarPair) -> tuple[frozenset[str], frozenset[str]]:
    try:
        return _GRAMMAR_RULES[grammar_pair]
    except KeyError as exc:
        raise AdapterInputError("unsupported_grammar_pair") from exc
```

Make `grammar_pair` a required keyword-only parameter of `parse_and_normalize_bapi_body`. Resolve `allowed_tags, block_tags = grammar_rules_for_pair(grammar_pair)` once before traversal and use only those local sets in traversal.

- [ ] **Step 4: Run parser tests and targeted lint**

Run:

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  -k 'h2 or grammar_pair' -q
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py
```

Expected: all selected tests PASS and ruff reports no errors.

**Out of scope:** reducer, storage, semantic IDs, CLI, fixtures, models, and existing source exports.

### Task 2: Thread The Explicit Pair Through Reduction And New G2 Writes

**Design invariants:** INV-H2-04a, INV-H2-05, INV-H2-06, INV-H2-07.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py:55-63,484-974,992-1124`.
- Modify: `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py:71-210`.
- Modify: `scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py:9-45`.
- Test: `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py`.
- Test: `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py`.

**Interfaces:**
- Consumes: `grammar_pair: GrammarPair` supplied by the new writer or completed consumer.
- Produces: `AdapterReduction.grammar_pair`, pair-bound IDs, semantic rows, schedule evidence, summary, and manifest values.

- [ ] **Step 1: Write failing reduction and writer tests**

Add a synthetic h2 reducer test that calls `reduce_verified_snapshot(..., grammar_pair=adapter.G2_GRAMMAR_PAIR)` and asserts one semantic extraction, an in-scope eligible `TOKENAUSDT` child, and this exact pair in:

```python
assert reduction.grammar_pair == adapter.G2_GRAMMAR_PAIR
assert reduction.semantic_extractions[0]["body_normalization_version"] == "stage1_6a_bapi_body_tree_v2"
assert reduction.semantic_extractions[0]["semantic_extractor_version"] == "stage1_6a_extractor_v2"
assert reduction.contracts[0]["settlement_time"]["evidence"]["body_normalization_version"] == "stage1_6a_bapi_body_tree_v2"
```

Add a same-source comparison asserting the G1 and G2 reductions have different `semantic_extraction_id` values whenever both produce a semantic extraction. Update legacy reducer-only fixture calls in both adapter test files to pass `grammar_pair=adapter.G1_GRAMMAR_PAIR`. Every test that creates a **new** root through `persist_adapter_audit()` must instead reduce with `adapter.G2_GRAMMAR_PAIR`; the sole intentional G1 writer call is the rejection test below. Completed-consumer G1 compatibility uses the frozen read-only root in Task 4.

Add `test_new_writer_rejects_g1_reduction` in the storage test file. It obtains a synthetic G1 reduction, calls `persist_adapter_audit(...)`, expects `AdapterInputError("new_writer_requires_g2_grammar_pair")`, and asserts the output root was never created. The test must use the production persistence function because that is the boundary every new root crosses.

- [ ] **Step 2: Run both changed test files and confirm RED**

Run:

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py -q
```

Expected: FAIL because the reducer does not yet accept or persist an explicit pair, and the production writer does not yet reject G1 reductions. This command must execute `test_new_writer_rejects_g1_reduction` in RED.

- [ ] **Step 3: Implement one pair value flow**

Make the following minimal interface changes:

```python
@dataclass(frozen=True)
class AdapterReduction:
    grammar_pair: GrammarPair
    candidate_manifest: Dict[str, Any]
    # retain every existing field unchanged

def reduce_verified_snapshot(
    snapshot: VerifiedSourceSnapshot,
    *,
    semantic_extracted_at_ms: int,
    grammar_pair: GrammarPair,
) -> AdapterReduction:
    body_normalization_version, semantic_extractor_version = grammar_pair
    grammar_rules_for_pair(grammar_pair)
    # pass grammar_pair to both selected and comparison parse calls
```

Use the two local version values, never a module-level current-writer constant, for the semantic-ID seed, semantic extraction row, non-null `settlement_time.evidence`, returned reduction, and `build_precompletion_summary`. The summary must take its two version fields from `reduction.grammar_pair`.

At the beginning of `persist_adapter_audit`, after the no-existing-root check and before any directory creation or file write, add the only new-writer admission rule:

```python
if reduction.grammar_pair != G2_GRAMMAR_PAIR:
    raise AdapterInputError("new_writer_requires_g2_grammar_pair")
```

Import `G2_GRAMMAR_PAIR` from the adapter. Keep the existing completion-manifest keys and copy the G2 summary pair unchanged. Do not create a test-only persistence branch, a writer mode field, or a CLI override.

The CLI imports `G2_GRAMMAR_PAIR` and calls:

```python
reduction = reduce_verified_snapshot(
    snapshot,
    semantic_extracted_at_ms=extracted_at_ms,
    grammar_pair=G2_GRAMMAR_PAIR,
)
```

Do not add a CLI grammar argument. New production-shaped writes are always G2 by Design.

- [ ] **Step 4: Run reducer, old-audit compatibility, and lint**

Run:

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py -q
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py \
  scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py
```

Expected: both adapter test files and the old-audit regression PASS; the production writer rejects G1 before it creates any root, and the old-audit regression proves fixture constants were not changed.

**Out of scope:** completed-consumer dispatch and any persistence schema/key changes.

### Task 3: Completed-Consumer Pair Validation Before Source Reduction

**Design invariants:** INV-H2-01, INV-H2-04, INV-H2-04a, INV-H2-06, INV-H2-07.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py:212-405`.
- Test: `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py`.

**Interfaces:**
- Consumes: verified persisted summary, completion manifest, semantic extraction rows, and non-null schedule evidence.
- Produces: `AdapterInputError` before `load_verified_source_snapshot()` for missing, unknown, mixed, or cross-artifact pair mismatch; otherwise calls reducer with the selected pair.

**Ordering precondition:** before it loads or reduces source bytes, the completed consumer validates the persisted pair and all persisted version-bearing projections.

- [ ] **Step 1: Write failing completed-consumer tests**

Use the normal synthetic fixture only to persist a coherent **G2** root; Task 2 makes production persistence reject G1. Coherently rehash altered authoritative artifacts, spy on `load_verified_source_snapshot`, and assert it has zero calls for each independent mutation:

```text
summary G1 / completion G2                         -> persisted_grammar_pair_mismatch
summary unknown pair / completion same              -> unsupported_grammar_pair
summary missing one version member                  -> persisted_grammar_pair_missing
semantic_extractions row pair != G2 root pair       -> persisted_grammar_pair_projection_mismatch
non-null settlement_time.evidence pair != G2 root pair -> persisted_grammar_pair_projection_mismatch
```

Test each exact error separately with `pytest.raises(AdapterInputError, match=<exact taxonomy above>)`; do not use one broad `unsupported_grammar_pair` expectation.

Add a positive G2 test that verifies the existing exact-key validator accepts an otherwise valid G2 summary/completion pair, reaches `_select_persisted_grammar_pair()`, and passes `adapter.G2_GRAMMAR_PAIR` to the reducer. Add direct helper tests that accept the exact G1 and G2 pairs, while G1 completed-root replay remains the frozen read-only integration check in Task 4 rather than a post-delta writer fixture.

- [ ] **Step 2: Run the entire storage test file and confirm RED**

Run:

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py -q
```

Expected: FAIL because consumer currently calls the reducer without pair validation or dispatch, and its existing exact-key validation has no supported-pair admission behavior.

- [ ] **Step 3: Implement one fail-closed selection helper and call order**

After verified artifact bytes are loaded and exact summary/completion schemas are validated, but before `load_verified_source_snapshot`, add a local storage helper with this behavior:

```python
def _select_persisted_grammar_pair(summary: Dict[str, Any], completion: Dict[str, Any]) -> GrammarPair:
    summary_pair = (summary.get("body_normalization_version"), summary.get("semantic_extractor_version"))
    completion_pair = (completion.get("body_normalization_version"), completion.get("semantic_extractor_version"))
    if any(not isinstance(value, str) or not value for value in (*summary_pair, *completion_pair)):
        raise AdapterInputError("persisted_grammar_pair_missing")
    if summary_pair != completion_pair:
        raise AdapterInputError("persisted_grammar_pair_mismatch")
    grammar_rules_for_pair(summary_pair)
    return summary_pair
```

Import `GrammarPair` and `grammar_rules_for_pair` from the adapter. Current storage has no fixed-G1 value validator: preserve its existing exact key-set/schema/profile checks and add this exact supported-pair selector immediately after them. Before the source snapshot is loaded, decode the already verified `semantic_extractions.jsonl`, require each row pair equals the selected pair, and inspect each non-null schedule evidence in `settlement_time`, `order_restriction`, `last_trading_time`, and `delisting_complete_time` in `delisting_contracts.jsonl`; each evidence pair must be two non-empty strings equal to the selected pair. A row/evidence mismatch raises `AdapterInputError("persisted_grammar_pair_projection_mismatch")`. Malformed JSON remains wrapped as `AdapterInputError`; unknown pair uses `unsupported_grammar_pair`; a missing/non-string member uses `persisted_grammar_pair_missing`.

Then call exactly:

```python
grammar_pair = _select_persisted_grammar_pair(summary_data, manifest_data)
_validate_persisted_pair_projections(persisted_bytes, grammar_pair)
snapshot = load_verified_source_snapshot(root, source_export)
rebuilt_reduction = reduce_verified_snapshot(
    snapshot,
    semantic_extracted_at_ms=1700000000000,
    grammar_pair=grammar_pair,
)
```

The helper performs no source search, no compatibility aliasing, no current-default fallback, and no output write.

- [ ] **Step 4: Run storage and all adapter tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py -q
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py
```

Expected: PASS. Every bad persisted pair rejects before source-byte reduction; the unit root replays G2 under G2, and Task 4 separately proves the frozen G1 root replays G1 read-only.

**Out of scope:** source export validation, artifact names, schemas, manifest-last ordering, thresholds, or filesystem discovery behavior.

### Task 4: New Local G2 Audit Of The Frozen Sealed Export

**Design invariants:** INV-H2-02, INV-H2-07, INV-H2-08, INV-H2-09, INV-H2-10.

**Files:**
- Modify: none after Tasks 1-3.
- Verify: `scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py`.
- Generated: one fresh `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/h2_g2_*` root only.

**Interfaces:**
- Consumes: the exact frozen `REF_EXPORT` and the frozen G1 root from Task 0.
- Produces: a read-only G1 completed-consumer replay, then one fresh completed G2 root and its independent completed-consumer result.

- [ ] **Step 1: Recheck the frozen G1 root as read-only historical evidence**

```bash
PYTHONPATH=src:. .venv/bin/python - "$FROZEN_G1_ROOT" "$REF_EXPORT" <<'PY'
import hashlib, sys
from pathlib import Path
from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter_storage import load_completed_adapter_audit

root, export = map(Path, sys.argv[1:])
assert hashlib.sha256((root / "stage1_6a_futures_delisting_source_audit_summary.json").read_bytes()).hexdigest() == "f746860704ed9ffafbb74fd382a41936f3a26e5aecce15acbc15db91d80174bf"
assert hashlib.sha256((root / "completion_manifest.json").read_bytes()).hexdigest() == "cc74c6cc15bdbddd1b11cf4fc7200dc33d8a50b8e01d30f599e74cdaa5cca0a0"
loaded = load_completed_adapter_audit(Path.cwd(), root, export)
assert (loaded["summary"]["body_normalization_version"], loaded["summary"]["semantic_extractor_version"]) == (
    "stage1_6a_bapi_body_tree_v1", "stage1_6a_extractor_v1")
assert loaded["completion_manifest"]["source_audit_passed"] is False
print({"completed_consumer": "PASS", "grammar": "G1", "read_only_root": str(root)})
PY
```

Expected: the same exact G1 bytes replay to their independently rebuilt historical false verdict. This step creates no root and writes no file.

- [ ] **Step 2: Create one fresh local G2 root with the existing CLI**

```bash
set -euo pipefail
export REF_EXPORT="data/external_signal_shadow/stage1_6b/historical_backfill/hist_delisting_network_retry_20260823T094411Z/sealed_exports/e9ec315753ead7a975c8df87de8fc1670e8b8eb890376a16eca4bb44b2007734"
export AUDIT_RUN_ID="h2_g2_$(date -u +%Y%m%dT%H%M%SZ)"
export AUDIT_ROOT="data/external_signal_shadow/stage1_6a/sealed_export_source_audits/$AUDIT_RUN_ID"
test ! -e "$AUDIT_ROOT"

PYTHONPATH=src:. .venv/bin/python \
  scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py \
  --project-root "$PWD" \
  --source-export "$REF_EXPORT" \
  --audit-run-id "$AUDIT_RUN_ID" \
  --output-root "$AUDIT_ROOT"
```

Expected: one new local root only, with `completion_manifest.json` written last. Any failure leaves no completed claim and must not be retried into the same root.

- [ ] **Step 3: Assert the exact G2 result and all-false authority boundary**

```bash
PYTHONPATH=src:. .venv/bin/python - "$AUDIT_ROOT" <<'PY'
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
summary = json.loads((root / "stage1_6a_futures_delisting_source_audit_summary.json").read_text())
completion = json.loads((root / "completion_manifest.json").read_text())
reef = next(json.loads(line) for line in (root / "delisting_contracts.jsonl").read_text().splitlines()
            if json.loads(line)["parent_article_id"] == "572715f2d96e47769ebbb967c2a6e445")
assert (summary["body_normalization_version"], summary["semantic_extractor_version"]) == (
    "stage1_6a_bapi_body_tree_v2", "stage1_6a_extractor_v2")
assert (completion["body_normalization_version"], completion["semantic_extractor_version"]) == (
    "stage1_6a_bapi_body_tree_v2", "stage1_6a_extractor_v2")
assert reef["canonical_symbol"] == "REEFUSDT"
assert reef["source_audit_eligible"] is True
assert reef["settlement_time"]["timestamp_ms"] == 1737536400000
assert summary["metrics"]["trusted_parents_count"] == 35
assert summary["metrics"]["historical_events_found"] == 30
assert summary["metrics"]["event_days"] == 30
assert summary["metrics"]["symbols_with_events"] == 44
assert summary["source_audit_evidence_candidate_passed"] is True
assert completion["source_audit_passed"] is True
assert all(value is False for value in completion["authority_flags"].values())
print({"g2_root": str(root), "source_audit_passed": True, "authority_flags": "all_false"})
PY
```

Expected: exact values above. `source_audit_passed=true` remains a design-only source-audit result; it does not permit PIT, replay, paper, live, execution, or trading.

- [ ] **Step 4: Independently consume the exact fresh G2 root**

```bash
PYTHONPATH=src:. .venv/bin/python - "$AUDIT_ROOT" "$REF_EXPORT" <<'PY'
import sys
from pathlib import Path
from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter_storage import load_completed_adapter_audit

loaded = load_completed_adapter_audit(Path.cwd(), Path(sys.argv[1]), Path(sys.argv[2]))
assert loaded["completion_manifest"]["source_audit_passed"] is True
assert loaded["summary"]["body_normalization_version"] == "stage1_6a_bapi_body_tree_v2"
print({"completed_consumer": "PASS", "grammar": "G2"})
PY
```

Expected: PASS against the explicit source-export path with no network call or path discovery.

**Out of scope:** VPS deployment, Stage 1.6B recollection, root resume, old-root mutation, market-data validation, replay, risk, or execution.

### Task 5: Completion Scope Gate And Independent Audit

**Design invariants:** all INV-H2-01 through INV-H2-10.

**Files:**
- Modify: none unless a Task 1-3 test demonstrates an in-scope defect.
- Verify: all Allowed Change Scope paths and fresh G2 runtime root.
- Create: `docs/reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md` only if the audit workflow generates it.

**Interfaces:**
- Consumes: the approved Plan bytes, final source/tests, and fresh G2 root.
- Produces: completion-audit verdict; no deployment authority.

- [ ] **Step 1: Run the complete permitted regression suite and lint**

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py -q
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py \
  scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py
```

Expected: all tests PASS and ruff reports no errors.

- [ ] **Step 2: Enforce final scope and authority checks**

```bash
set -euo pipefail
export BASE_SHA="d1f7ee2d9d8eb37389feeed912ff13d34fba8e05"
export PLAN_PATH="docs/plans/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-implementation-plan_CN.md"
export H2_DESIGN_PATH="docs/designs/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-design_CN.md"
test -n "${PROVENANCE_FILE:?STOP: reuse the Task 0 provenance file}"
test -n "${APPROVED_PLAN_SHA:?STOP: reuse the post-review approval SHA}"
git diff --check
test "$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}')" = "$APPROVED_PLAN_SHA"
test "$(shasum -a 256 "$H2_DESIGN_PATH" | awk '{print $1}')" = "f31e9a64f42fcd1eccfab94efa5c9328fbdc154a9ae70880e359bfc701306987"
test "$(shasum -a 256 docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md | awk '{print $1}')" = "1cb90f89113ceda4d2037cb62d60b8a9f769f7d58c467ad0e515332bc13563fd"
test "$(shasum -a 256 docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-adapter-derived-artifact-schema-delta-design_CN.md | awk '{print $1}')" = "2572849bf7df9154170ebc28f9687315728566a7c9498153f346d61308aaeb34"
test "$(shasum -a 256 docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6b-terminal-status-field-contract-correction-design_CN.md | awk '{print $1}')" = "4bc7bc60a5435f9d71735319eac0dc84bf655bd94bc5f065652545f472596aae"
git diff --quiet "$BASE_SHA" -- \
  configs/base.py \
  src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py \
  src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py || {
  echo "STOP: affected-but-unchanged path differs from baseline" >&2
  exit 1
}

PYTHONPATH=src:. .venv/bin/python - "$BASE_SHA" "$PROVENANCE_FILE" <<'PY'
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from configs import base

BASE_SHA, provenance_path = sys.argv[1:]

def git(*args):
    return subprocess.check_output(["git", *args])

def state(path):
    p = Path(path)
    if not p.exists() and not p.is_symlink():
        return {"kind": "missing", "sha256": None}
    if p.is_symlink():
        return {"kind": "symlink", "sha256": hashlib.sha256(os.readlink(p).encode()).hexdigest()}
    if p.is_file():
        return {"kind": "file", "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    raise SystemExit(f"STOP: unsupported scope path type: {path}")

raw = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
status_by_path = {}
for item in raw.split(b"\0"):
    if not item:
        continue
    status = item[:2].decode("ascii")
    if "R" in status or "C" in status:
        raise SystemExit("STOP: rename/copy workspace state requires a separate scope review")
    if item[2:3] != b" ":
        raise SystemExit(f"STOP: malformed porcelain record: {item!r}")
    status_by_path[item[3:].decode("utf-8", "surrogateescape")] = status

preexisting = json.loads(Path(provenance_path).read_text())["records"]
tracked = set(git("diff", "--name-only", BASE_SHA).decode().splitlines())
untracked = set(git("ls-files", "--others", "--exclude-standard").decode().splitlines())
current = tracked | untracked

# Frozen pre-existing paths must survive unchanged, including paths no longer
# visible in the current tracked/untracked sets after deletion or restoration.
for path, expected in sorted(preexisting.items()):
    actual = {"status": status_by_path.get(path), **state(path)}
    if actual != expected:
        raise SystemExit(f"STOP: pre-existing workspace path changed: {path}")

implementation_changed = current - set(preexisting)
allowed_exact = {
    "src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py",
    "src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py",
    "scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py",
    "tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py",
    "tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py",
    "docs/plans/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-implementation-plan_CN.md",
    "docs/reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md",
}
for path in sorted(implementation_changed):
    if path in allowed_exact or fnmatch.fnmatch(path, "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/h2_g2_*"):
        continue
    raise SystemExit(f"STOP: out-of-scope changed/untracked path: {path}")

assert base.RISK_LIVE_TRADING_ENABLED is False
print({"scope_gate": "PASS", "implementation_changed_paths": sorted(implementation_changed)})
PY
```

Expected: all four Design hashes and the approved Plan hash still match; every pre-existing path retains its exact status/type/SHA-256 even if deleted or restored during execution; every new implementation path belongs to the exact allowlist; all three affected-but-unchanged files have zero diff; and `configs.base.RISK_LIVE_TRADING_ENABLED is False`. Any other result is a STOP.

- [ ] **Step 3: Run `audit-plan-completion` before claiming completion**

Invoke `.agent/skills/audit-plan-completion` against this Plan, the four Design authority hashes, the exact source diff, test output, and fresh G2 root. The audit must verify both G1 replay and G2 replay, the fail-before-source dispatch tests, the REEF real-root result, scope provenance, and all-false authority flags.

Expected: `Verdict: complete`. Any other verdict blocks completion, commit, deployment, and additional operational claims.

**Out of scope:** commits, deployment, VPS collection, risk/trading enablement, or changing a failed verdict by altering thresholds.

## Plan Outcome

```text
implementation_plan_status = draft_pending_review
implementation_allowed = false
deployment_allowed = false
RISK_LIVE_TRADING_ENABLED = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

This Plan is not implementation approval. Code execution requires a Plan review verdict of `Approve` and the user's explicit approval of the reviewed Plan bytes.
