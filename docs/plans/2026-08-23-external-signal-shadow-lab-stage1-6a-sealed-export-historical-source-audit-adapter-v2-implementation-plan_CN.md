# Stage 1.6A Sealed-Export Historical Source-Audit Adapter v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` (recommended) or `executing-plans` task-by-task. Apply RED -> GREEN -> focused regression for every behavior task. Do not implement until this Plan is reviewed `Approve` and the user explicitly authorizes execution.

**Goal:** Consume one caller-supplied completed Stage 1.6B historical sealed export and produce a separate offline, independently verifiable Stage 1.6A source-audit root without source mutation or any trading-related permission.

**Architecture:** A new adapter snapshot/reducer calls existing Stage 1.6B `load_sealed_export()` exactly once per producer/consumer boundary, retains all validated source bytes in memory, then applies the v2 lineage, BAPI and metric contracts. A separate adapter storage module writes exact artifacts, pre-completion summary and finally the completion manifest; its completed consumer re-reduces the explicit source export and rejects every mismatch. Old fixture-only Stage 1.6A modules and all Stage 1.6B writers stay unchanged.

**Tech Stack:** Python 3.12; stdlib `dataclasses`, `hashlib`, `json`, `pathlib`, `re`, `unicodedata`; existing pytest; existing Stage 1.6B loader.

**Approved Authority:**

```text
v2 Design SHA-256: 1cb90f89113ceda4d2037cb62d60b8a9f769f7d58c467ad0e515332bc13563fd
Schema Delta SHA-256: 2572849bf7df9154170ebc28f9687315728566a7c9498153f346d61308aaeb34
TerminalStatus Correction SHA-256: 4bc7bc60a5435f9d71735319eac0dc84bf655bd94bc5f065652545f472596aae
Implementation baseline: d1656f1c3871e3aec4192140a3753bfaaa22f462
```

The SHA-256 of this Plan is intentionally not self-embedded: writing it into this file would change the hash. Task 0 Phase A binds a reviewer-supplied `REVIEW_CANDIDATE_PLAN_SHA` before approval; the reviewer/user approval record then promotes the same value to `APPROVED_PLAN_SHA`. Task 0 Phase B and Task 6 require that approval value; unset or mismatched authority is a `STOP`.

## Global Constraints

- The sole source is one explicit caller path under `data/external_signal_shadow/stage1_6b/historical_backfill/<run-id>/sealed_exports/<export-id>/`; no glob, scan, latest, ID search, HTTP, websocket, browser, retry, repair, resume, reseal or raw copy.
- Call `stage1_6b_canonical_source_storage.load_sealed_export(export_dir)` exactly once at each source snapshot boundary. Do not duplicate the Stage 1.6B validator.
- `configs/base.py` is read-only SSOT. Snapshot exactly the seven historical `EXTERNAL_SIGNAL_STAGE1_6A_*` thresholds; do not add fallbacks or alter config.
- Trusted raw BAPI JSON/envelope/body failure is denominator-visible. Control JSON/JSONL/schema/hash/path/linkage failure is structural and occurs before output-root creation.
- Public input/consumer boundaries raise only `AdapterInputError`, wrapping `OSError`, `JSONDecodeError`, `KeyError`, `TypeError` and `ValueError`.
- The only output family is `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/<audit-run-id>/`; root basename equals `audit_run_id`; no overwrite, repair or resume.
- Historical/PIT fields and every authority flag remain exact `null`, `historical_unknown` or `false` as required by v2 Sections 8.3 and 12.6.
- Do not import or call Stage 1.5, strategies, risk, execution, HTTP clients, old `process_capture_bundle()` or old fixture storage.
- Before Plan approval, prove candidate authority hashes, protected code baseline, candidate Plan SHA, complete tracked/untracked workspace provenance and the real-export preflight. After approval but before any `src/`/`scripts/`/`tests/` mutation, bind the same Plan bytes as `APPROVED_PLAN_SHA` and capture execution workspace provenance. Existing untracked designs and old Plan are pre-existing evidence, not implementation changes and their file types/SHA-256 values must remain unchanged.

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py`
- `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py`
- `scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py`
- `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py`
- `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py`

Allowed documentation paths:
- `docs/plans/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-v2-implementation-plan_CN.md`
- `docs/reviews/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-v2-completion-audit_CN.md` only when produced by completion audit.

Allowed generated/runtime artifacts:
- `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/<audit-run-id>/**` generated only; never commit.
- `data/external_signal_shadow/stage1_6b/historical_backfill/**/sealed_exports/**` read-only only; never mutate.
- `graphify-out/graph.json` read-only advisory input; never regenerate without a separate authorization.

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`
  - Evidence: monkeypatch/count-assert one `load_sealed_export()` call; existing Stage 1.6B storage tests stay green.
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_summary.py`
- `scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py`
  - Evidence: existing fixture-only regression suite remains green; AST test prohibits adapter imports/calls.
- `configs/base.py`
  - Evidence: exact threshold snapshot test and no-diff check.

Forbidden:
- Mutation outside allowed paths; Stage 1.6B/Stage 1.5/config/strategy/risk/execution changes; edits to old fixture modules or superseded 2026-08-22 Plan.
- Network/source repair/compatibility alias/current exchangeInfo/current webpage lookup.
- Full-repo formatting/autofix, `ruff check --fix .`, destructive cleanup or unscoped refactor.

## Invariant Map

| Invariants | Task | Proof |
|---|---|---|
| INV-01 | 0, 1, 6 | explicit confined source path and no scan/glob/latest |
| INV-02 | 0, 1, 6 | one loader call and retained-byte hash/path validation |
| INV-03 | 1, 2 | ArticleDiscovery-only frozen candidate population |
| INV-04 | 0, 1, 2 | nonempty, in-set, globally unique observation membership |
| INV-05 | 1, 2 | completed-export certificate for detail_unavailable |
| INV-06 | 1, 2 | bidirectional observation/revision/raw/header-profile linkage |
| INV-07 | 2 | selected canonical-English BAPI-only semantic authority |
| INV-08 | 2 | wrong-code structural versus malformed-envelope outcome split |
| INV-09 | 2 | exact first-list chain and publication corroboration |
| INV-10 | 2, 3 | denominator-visible source failures and metric numerator failure |
| INV-11 | 2, 3 | publication/schedule explicit unparseable or not_stated states |
| INV-12 | 2, 3 | deterministic revision selection and conflict handling |
| INV-13 | 2, 3 | all-child accounting before eligible child output |
| INV-14 | 3, 5 | historical null/unknown fields and exact false authority flags |
| INV-15 | 3, 4 | one outcome per candidate and durable metric rebuild |
| INV-16 | 4, 5 | pre-completion cap and completion-manifest-last authority |
| INV-17 | 4, 6 | independent exact-source completed consumer replay |
| INV-18 | 4, 6 | reject mutated internally-consistent final verdict/action |
| INV-19 | 0, 3, 4 | seven-key config SSOT snapshot and drift rejection |
| INV-20 | 0, 1, 4, 6 | read-only source bytes and input mutation rejection |
| INV-21 | 3, 4 | deterministic projections excluding only run metadata |
| Delta INV-D01..D06 | 3, 4 | four projection schemas, asset provenance/null, consumer replay |

---

### Task 0: Freeze Baseline And Re-Verify Real Input Authority

**Design coverage:** PG-01, PG-02, PG-04, PG-10; INV-01, INV-02, INV-04, INV-05, INV-19, INV-20.

**Files:** Create none. Modify no source, test or Design file.

**Produces:** pre-approval review transcript with candidate authority/baseline/workspace provenance, explicit source export, loader result, exact input schemas/counts and seven-key config snapshot; then a post-approval execution-authority transcript. Any discrepancy is `STOP` and requires Design review.

- [ ] **Phase A / Step 1: Before approval, prove candidate authority, protected baseline and review workspace provenance.**

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export PLANNING_BASE_SHA="d1656f1c3871e3aec4192140a3753bfaaa22f462"
export EXPECTED_V2_DESIGN_SHA="1cb90f89113ceda4d2037cb62d60b8a9f769f7d58c467ad0e515332bc13563fd"
export EXPECTED_SCHEMA_DELTA_SHA="2572849bf7df9154170ebc28f9687315728566a7c9498153f346d61308aaeb34"
export EXPECTED_TERMINAL_CORRECTION_SHA="4bc7bc60a5435f9d71735319eac0dc84bf655bd94bc5f065652545f472596aae"
export PLAN_PATH="docs/plans/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-v2-implementation-plan_CN.md"
export REVIEW_CANDIDATE_PLAN_SHA="<SHA-256 of the candidate Plan supplied to this review>"
export REVIEW_WORKSPACE_PROVENANCE_JSON="$(mktemp -t stage1_6a_adapter_review_workspace.XXXXXX.json)"
PYTHONPATH=src:. .venv/bin/python - "$PLANNING_BASE_SHA" "$EXPECTED_V2_DESIGN_SHA" "$EXPECTED_SCHEMA_DELTA_SHA" "$EXPECTED_TERMINAL_CORRECTION_SHA" "$PLAN_PATH" "$REVIEW_CANDIDATE_PLAN_SHA" "$REVIEW_WORKSPACE_PROVENANCE_JSON" <<'PY'
import hashlib, json, os, subprocess, sys
from pathlib import Path
base, v2_sha, delta_sha, terminal_sha, plan_path, candidate_plan_sha, out = sys.argv[1:]
assert candidate_plan_sha and not candidate_plan_sha.startswith('<'), 'STOP: review must provide REVIEW_CANDIDATE_PLAN_SHA'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha('docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md') == v2_sha
assert sha('docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-adapter-derived-artifact-schema-delta-design_CN.md') == delta_sha
assert sha('docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6b-terminal-status-field-contract-correction-design_CN.md') == terminal_sha
assert sha(plan_path) == candidate_plan_sha, 'STOP: review candidate Plan SHA mismatch'
subprocess.run(['git', 'merge-base', '--is-ancestor', base, 'HEAD'], check=True)
protected = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', base, '--', 'configs', 'src', 'scripts', 'tests'], text=True).splitlines()
assert not protected, {'STOP': 'protected implementation surface diverged before execution', 'paths': protected}
tracked = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', base], text=True).splitlines()
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z']).decode().split('\0')
paths = sorted(set(p for p in tracked + untracked if p))
untracked_code = sorted(p for p in untracked if p and p.startswith(('src/', 'scripts/', 'tests/', 'configs/')))
assert not untracked_code, {'STOP': 'preexisting_untracked_code_can_shadow_imports', 'paths': untracked_code}
def fingerprint(rel):
    p = Path(rel)
    if p.is_symlink(): return {'type': 'symlink', 'target': os.readlink(p)}
    if p.is_file(): return {'type': 'file', 'sha256': sha(p)}
    return {'type': 'other'}
provenance = {p: fingerprint(p) for p in paths}
Path(out).write_text(json.dumps(provenance, sort_keys=True), encoding='utf-8')
print({'planning_base_sha': base, 'review_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'preexisting_paths': provenance, 'review_workspace_provenance_json': out})
PY
```

Expected: every Design authority hash and the reviewer-supplied candidate Plan hash matches; `PLANNING_BASE_SHA` is an ancestor and no protected implementation path diverged before review; every pre-existing tracked/untracked path has a captured file type/SHA-256. This is read-only and must PASS before the reviewer can approve the Plan. Do not reset, clean, checkout or overwrite them.

- [ ] **Step 2: Preflight one user-supplied export, with no source selection logic.**

```bash
export PROJECT_ROOT="$PWD"
export SOURCE_EXPORT="$PROJECT_ROOT/data/external_signal_shadow/stage1_6b/historical_backfill/hist_delisting_retry_20260822T041106Z/sealed_exports/3fbe8e92d83af929913ca16276df3cddf81b26b7327e476b19712870a7792247"
PYTHONPATH=src:. .venv/bin/python - "$PROJECT_ROOT" "$SOURCE_EXPORT" <<'PY'
import hashlib, json, sys
from collections import Counter, defaultdict
from pathlib import Path
import configs.base as base
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import historical_coverage_is_complete, load_sealed_export
root, export = map(Path, sys.argv[1:])
export = export.resolve(strict=True)
allowed = (root / 'data/external_signal_shadow/stage1_6b/historical_backfill').resolve(strict=True)
assert export.is_relative_to(allowed), 'STOP: export path outside historical_backfill'
manifest = load_sealed_export(export)  # exactly one call
assert manifest['export_id'] == export.name
assert export.name == '3fbe8e92d83af929913ca16276df3cddf81b26b7327e476b19712870a7792247'
assert hashlib.sha256((export / 'sealed_export_manifest.json').read_bytes()).hexdigest() == '2d0d992a6dc4d8086f2d07b8c29143e4d74b140ce370848564d032d51503a254'
assert manifest['capture_mode'] == 'historical_backfill'
assert manifest['source_profile_id'] == 'binance_public_web_bapi_en_delisting_catalog_v2'
def rows(p): return [json.loads(x) for x in (export / p).read_text().splitlines() if x.strip()]
discoveries, observations, revisions = map(rows, ('article_discoveries.jsonl', 'detail_observations/historical.jsonl', 'detail_revisions.jsonl'))
assert discoveries and observations and revisions
expected_discovery_keys = {'capture_mode', 'captured_at_ms', 'discovery_rule_version', 'discovery_title', 'first_list_capture_id', 'notice_lineage_first_detected_at_ms', 'record_seq', 'schema_version', 'source_article_id', 'source_catalog_id', 'source_catalog_name', 'source_profile_id'}
expected_observation_keys = {'capture_mode', 'captured_at_ms', 'content_type', 'final_url', 'http_status', 'poll_seq', 'raw_payload_bytes', 'raw_payload_relative_path', 'raw_payload_sha256', 'record_seq', 'request_headers_profile_sha256', 'request_observation_id', 'request_variant', 'requested_url', 'run_id', 'schema_version', 'source_article_id', 'source_profile_id', 't_detail_receive_ms', 'trust_validation_status'}
expected_revision_keys = {'capture_mode', 'captured_at_ms', 'detail_raw_sha256', 'detail_revision_id', 'raw_payload_relative_path', 'record_seq', 'request_variant', 'schema_version', 'source_article_id', 'source_locale', 'source_profile_id', 'source_surface', 't_detail_trusted_ms', 't_raw_persisted_ms'}
assert all(set(x) == expected_discovery_keys and x.get('schema_version') == 'stage1_6b_article_discovery_v2' for x in discoveries)
assert {(x['source_catalog_id'], x['source_catalog_name']) for x in discoveries} == {(161, 'Delisting')}
assert all(x.get('schema_version') == 'stage1_6b_detail_observation_v1' for x in observations)
assert all(set(x) == expected_observation_keys for x in observations)
assert all(isinstance(x.get('request_observation_id'), str) and x['request_observation_id'] for x in observations)
assert len({x['request_observation_id'] for x in observations}) == len(observations)
assert all(set(x) == expected_revision_keys and x.get('schema_version') == 'stage1_6b_detail_revision_v1' for x in revisions)
discovery_ids = {x['source_article_id'] for x in discoveries}
assert {x['source_article_id'] for x in observations} == discovery_ids
assert all(sum(x['source_article_id'] == article_id for x in observations) == 1 for article_id in discovery_ids)
for rel, schema in {
    'capture_run_contract.json': 'stage1_6b_capture_run_contract_v1',
    'source_profile_probe_attestation.json': 'stage1_6b_source_profile_probe_attestation_v2',
    'observer_checkpoint.json': 'stage1_6b_observer_checkpoint_v2',
    'historical_coverage.json': 'stage1_6b_historical_coverage_v2',
    'terminal_status.json': 'stage1_6b_terminal_status_v1',
}.items():
    assert json.loads((export / rel).read_text()).get('schema_version') == schema
terminal = json.loads((export / 'terminal_status.json').read_text())
assert set(terminal) == {'schema_version', 'capture_mode', 'run_id', 'source_profile_id', 'status', 'terminal_reason', 'final_checkpoint_id', 'terminated_at_ms'}
assert terminal.get('status') == 'complete'
assert terminal.get('terminal_reason') == 'historical_backfill_complete'
assert 'reason' not in terminal
coverage = json.loads((export / 'historical_coverage.json').read_text())
assert historical_coverage_is_complete(coverage)
assert {k: coverage[k] for k in ('selected_catalog_id', 'selected_catalog_name', 'frozen_candidate_count', 'candidate_terminal_count', 'pending_candidate_count', 'unattempted_candidate_count', 'final_checkpoint_valid')} == {
    'selected_catalog_id': 161, 'selected_catalog_name': 'Delisting', 'frozen_candidate_count': 35,
    'candidate_terminal_count': 35, 'pending_candidate_count': 0, 'unattempted_candidate_count': 0,
    'final_checkpoint_valid': True,
}
assert len(discoveries) == len(observations) == 35 and len(revisions) == 33
assert Counter(row['trust_validation_status'] for row in observations) == {'trusted': 33, 'network_error': 2}
by_article = defaultdict(list)
for observation in observations:
    by_article[observation['source_article_id']].append(observation)
nontrusted_articles = sorted(article for article, values in by_article.items() if not any(value['trust_validation_status'] == 'trusted' for value in values))
assert nontrusted_articles == ['5150d4f0ee1546d7ae6382ba7cda3ffe', '572715f2d96e47769ebbb967c2a6e445']
assert sorted(value['request_observation_id'] for article in nontrusted_articles for value in by_article[article]) == [
    '11d10ec7c43dc30c0ef1c5b9d19ecc90f6525117decc01b3cb1ee15f8121ec21',
    '30116ee1f4c61723f7110dd0038d12de719487c588ef5a717d2c8fe7ce0963f6',
]
identity_view = [(row['source_article_id'], row['request_observation_id'], row['trust_validation_status']) for row in sorted(observations, key=lambda row: row['request_observation_id'])]
assert hashlib.sha256(json.dumps(identity_view, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest() == '1e97145d45a38a4f76e0efd5d8f4cda7b225336b8f9a9590edbc15270b773b21'
attestation = json.loads((export / 'source_profile_probe_attestation.json').read_text())
contract = json.loads((export / 'capture_run_contract.json').read_text())
assert (attestation['selected_catalog_id'], attestation['selected_catalog_name']) == (161, 'Delisting')
assert attestation['source_profile_id'] == contract['source_profile_id'] == terminal['source_profile_id'] == coverage['source_profile_id'] == manifest['source_profile_id']
assert attestation['request_headers_profile_sha256'] == manifest['request_headers_profile_sha256']
assert all(row['request_headers_profile_sha256'] == attestation['request_headers_profile_sha256'] for row in observations)
assert contract['run_id'] == terminal['run_id'] == coverage['run_id']
keys = ('EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS', 'EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS', 'EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS', 'EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO', 'EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO', 'EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO', 'EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT')
expected_thresholds = {
    'EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS': 30,
    'EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS': 10,
    'EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS': 3,
    'EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO': 0.95,
    'EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO': 0.95,
    'EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO': 0.95,
    'EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT': 0,
}
actual_thresholds = {k: getattr(base, k) for k in keys}
assert actual_thresholds == expected_thresholds, {'STOP': 'historical_threshold_snapshot_mismatch', 'actual': actual_thresholds}
print({'export_id': manifest['export_id'], 'manifest_sha256': hashlib.sha256((export / 'sealed_export_manifest.json').read_bytes()).hexdigest(), 'discoveries': len(discoveries), 'observations': len(observations), 'revisions': len(revisions), 'nontrusted_article_ids': nontrusted_articles, 'observation_keys': sorted(observations[0]), 'revision_keys': sorted(revisions[0]), 'thresholds': actual_thresholds})
PY
```

Expected: loader passes, the exact named sealed export and manifest bytes match, `terminal_reason` is the only terminal field, coverage terminal accounting is complete, the current reference population is exactly 35 candidates / 33 trusted revisions / 2 known network-error parents, all seven runtime threshold values exactly match the frozen 30/10/3/0.95/0.95/0.95/0 contract, and printed schemas agree with v2. The one-observation-per-candidate assertion is a fact about this frozen reference export only, not a generic reducer rule. Any mismatch, absent file or failed assertion stops implementation; no alias or upstream mutation is allowed.

- [ ] **Step 3: Re-run the upstream historical completion regression that proves `terminal_reason` acceptance.**

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py \
  -k 'sweep_parity_and_completion' -q
```

Expected: PASS. It confirms the existing Stage 1.6B loader accepts a completed historical export only through `terminal_reason='historical_backfill_complete'` plus historical coverage completion; no `reason` alias is introduced.

- [ ] **Step 4: Record why old Stage 1.6A cannot be reused.**

```bash
rg -n 'def process_capture_bundle|details_by_id\[aid\]|def persist_audit_artifacts|def load_completed_audit' \
  src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py \
  src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py
```

Expected: transcript demonstrates fixture one-detail/conditional-storage behavior. Treat it as unchanged compatibility evidence only.

- [ ] **Phase B / Step 5: After Phase A PASS, formal Plan approval and explicit user execution authorization, bind execution authority before Task 1.**

```bash
export PLANNING_BASE_SHA="d1656f1c3871e3aec4192140a3753bfaaa22f462"
export EXPECTED_V2_DESIGN_SHA="1cb90f89113ceda4d2037cb62d60b8a9f769f7d58c467ad0e515332bc13563fd"
export EXPECTED_SCHEMA_DELTA_SHA="2572849bf7df9154170ebc28f9687315728566a7c9498153f346d61308aaeb34"
export EXPECTED_TERMINAL_CORRECTION_SHA="4bc7bc60a5435f9d71735319eac0dc84bf655bd94bc5f065652545f472596aae"
export PLAN_PATH="docs/plans/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-v2-implementation-plan_CN.md"
export REVIEW_CANDIDATE_PLAN_SHA="<Phase A transcript candidate Plan SHA-256>"
export APPROVED_PLAN_SHA="<same SHA-256 recorded in the user/reviewer approval record>"
export WORKSPACE_PROVENANCE_JSON="$(mktemp -t stage1_6a_adapter_execution_workspace.XXXXXX.json)"
PYTHONPATH=src:. .venv/bin/python - "$PLANNING_BASE_SHA" "$EXPECTED_V2_DESIGN_SHA" "$EXPECTED_SCHEMA_DELTA_SHA" "$EXPECTED_TERMINAL_CORRECTION_SHA" "$PLAN_PATH" "$REVIEW_CANDIDATE_PLAN_SHA" "$APPROVED_PLAN_SHA" "$WORKSPACE_PROVENANCE_JSON" <<'PY'
import hashlib, json, os, subprocess, sys
from pathlib import Path
base, v2_sha, delta_sha, terminal_sha, plan_path, candidate_plan_sha, approved_plan_sha, out = sys.argv[1:]
assert candidate_plan_sha == approved_plan_sha and not approved_plan_sha.startswith('<'), 'STOP: approval did not bind the reviewed candidate bytes'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha('docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md') == v2_sha
assert sha('docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-adapter-derived-artifact-schema-delta-design_CN.md') == delta_sha
assert sha('docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6b-terminal-status-field-contract-correction-design_CN.md') == terminal_sha
assert sha(plan_path) == approved_plan_sha, 'STOP: approved Plan changed after Phase A'
subprocess.run(['git', 'merge-base', '--is-ancestor', base, 'HEAD'], check=True)
protected = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', base, '--', 'configs', 'src', 'scripts', 'tests'], text=True).splitlines()
assert not protected, {'STOP': 'protected implementation surface diverged before Task 1', 'paths': protected}
tracked = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', base], text=True).splitlines()
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z']).decode().split('\0')
paths = sorted(set(p for p in tracked + untracked if p))
untracked_code = sorted(p for p in untracked if p and p.startswith(('src/', 'scripts/', 'tests/', 'configs/')))
assert not untracked_code, {'STOP': 'preexisting_untracked_code_can_shadow_imports', 'paths': untracked_code}
def fingerprint(rel):
    p = Path(rel)
    if p.is_symlink(): return {'type': 'symlink', 'target': os.readlink(p)}
    if p.is_file(): return {'type': 'file', 'sha256': sha(p)}
    return {'type': 'other'}
Path(out).write_text(json.dumps({p: fingerprint(p) for p in paths}, sort_keys=True), encoding='utf-8')
print({'execution_authority_rebind': 'PASS', 'workspace_provenance_json': out})
PY
export BASE_SHA="$(git rev-parse HEAD)"
```

Expected: this is the first command that requires `APPROVED_PLAN_SHA`; it must bind exactly the Phase A reviewed bytes after approval and before any production/test mutation. If it passes, Task 1 may begin. If it fails, no implementation work is allowed.

---

### Task 1: Add Snapshot Loader And Synthetic Sealed-Export Test Builder

**Design coverage:** PG-01..PG-05; INV-01..INV-06, INV-20.

**Files:**
- Create `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py`
- Create `tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py`
- Create `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py`

**Interfaces:**

```python
class AdapterInputError(ValueError): pass

@dataclass(frozen=True)
class VerifiedSourceSnapshot:
    export_id: str
    manifest: dict[str, object]
    artifact_bytes: dict[str, bytes]
    control_records: dict[str, dict[str, object]]
    list_captures: tuple[dict[str, object], ...]
    discoveries: tuple[dict[str, object], ...]
    observations: tuple[dict[str, object], ...]
    revisions: tuple[dict[str, object], ...]
    raw_payload_bytes: dict[str, bytes]

def load_verified_source_snapshot(project_root: Path, export_dir: Path) -> VerifiedSourceSnapshot: ...
```

Test support exports only `build_valid_historical_sealed_export(tmp_path, *, article_specs)`, `rewrite_authoritative_artifact(export_dir, relative_path, data)` and `make_mutated_export(project_root, export_dir, mutation)`. It builds a tiny synthetic hash-valid Stage 1.6B historical export accepted by the existing loader and must label test rows synthetic; it is never official evidence.

- [ ] **Step 1: Add failing snapshot tests.**

```python
def test_snapshot_accepts_explicit_historical_export_and_calls_loader_once(monkeypatch, tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    calls, real = 0, storage.load_sealed_export
    def counted(path):
        nonlocal calls
        calls += 1
        return real(path)
    monkeypatch.setattr(adapter.storage, 'load_sealed_export', counted)
    assert adapter.load_verified_source_snapshot(root, export).export_id == export.name
    assert calls == 1

def test_snapshot_rejects_escape_control_json_identity_and_foreign_membership(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    with pytest.raises(adapter.AdapterInputError): adapter.load_verified_source_snapshot(root, root / 'outside')
    for mutation in ('malformed_control_json', 'missing_request_observation_id', 'duplicate_request_observation_id', 'foreign_source_article_id'):
        with pytest.raises(adapter.AdapterInputError):
            adapter.load_verified_source_snapshot(root, make_mutated_export(root, export, mutation))

def test_snapshot_rejects_post_loader_source_byte_mutation(monkeypatch, tmp_path): ...
def test_snapshot_rejects_attestation_run_contract_manifest_or_header_profile_mismatch(tmp_path): ...
```

- [ ] **Step 2: Prove RED.**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py -q`

Expected: FAIL because new symbols do not exist.

- [ ] **Step 3: Implement retained-byte snapshot validation.**

```python
def load_verified_source_snapshot(project_root: Path, export_dir: Path) -> VerifiedSourceSnapshot:
    try:
        root, source = project_root.resolve(strict=True), export_dir.resolve(strict=True)
        allowed = (root / 'data/external_signal_shadow/stage1_6b/historical_backfill').resolve(strict=True)
        if not source.is_relative_to(allowed): raise AdapterInputError('source_export_path_outside_historical_backfill')
        manifest = storage.load_sealed_export(source)  # the one permitted call
        return _build_snapshot_from_retained_bytes(source, manifest)
    except AdapterInputError: raise
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise AdapterInputError(f'source_snapshot_invalid:{exc}') from exc
```

`_build_snapshot_from_retained_bytes` verifies v2 schemas/profile/catalog, manifest tuples, confined paths, bytes/hash/size, run/attestation/header bindings, candidate membership and nonempty globally unique observation identities. It reads each reducer input once into memory, does not parse BAPI JSON/body, re-open retained paths or use a fallback field.

- [ ] **Step 4: Verify GREEN and unaffected upstream loader.**

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py -q
```

Expected: PASS.

---

### Task 2: Implement Observation/Revision Aggregation And Canonical BAPI Reduction

**Design coverage:** PG-03..PG-08; INV-03..INV-13.

**Files:**
- Modify `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py`
- Modify `tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class AdapterReduction:
    candidate_manifest: dict[str, object]
    parent_outcomes: tuple[dict[str, object], ...]
    detail_revision_projection: tuple[dict[str, object], ...]
    semantic_extractions: tuple[dict[str, object], ...]
    notices: tuple[dict[str, object], ...]
    contracts: tuple[dict[str, object], ...]
    diagnostics: tuple[dict[str, object], ...]

def reduce_verified_snapshot(snapshot: VerifiedSourceSnapshot, *, semantic_extracted_at_ms: int) -> AdapterReduction: ...
def parse_and_normalize_bapi_body(raw_payload: bytes, *, article_id: str) -> tuple[dict[str, object] | None, str | None]: ...
```

`parse_and_normalize_bapi_body` returns `(None, 'malformed_bapi_envelope')` or `(None, 'body_parse_unresolved')` for payload quality. It raises `AdapterInputError` only for a present string `data.code` that names a different article or another structural lineage contradiction.

- [ ] **Step 1: Add observation/revision RED matrix.**

Implement tests named:

```python
test_network_error_then_trusted_observation_produces_trusted_parent
test_trusted_then_network_error_does_not_downgrade_parent
test_two_trusted_observations_same_raw_hash_share_one_logical_revision
test_two_trusted_observations_distinct_raw_hashes_select_max_trusted_time_then_hash
test_trusted_observation_without_revision_rejects_export
test_orphan_revision_without_trusted_observation_rejects_export
test_revision_profile_variant_header_or_surface_locale_mismatch_rejects_export
test_zero_or_foreign_observation_rejects_export
test_nontrusted_only_parent_requires_completed_terminal_accounting_certificate
```

For accepted nontrusted input assert `detail_authority_status == 'detail_unavailable'`, `source_integrity_parent_pass is False`, one notice exists, and semantic/contract rows are empty.

- [ ] **Step 2: Add BAPI/first-list/publication RED matrix.**

Implement tests named:

```python
test_invalid_trusted_raw_json_is_malformed_envelope_not_structural_reject
test_missing_or_nonstring_data_code_is_malformed_envelope
test_present_wrong_data_code_rejects_entire_export
test_body_unknown_tag_and_nonempty_br_child_are_body_parse_unresolved
test_canonical_body_normalization_golden_vectors
test_first_list_capture_missing_duplicate_wrong_article_or_invalid_release_date_rejects
test_publish_date_conflict_fails_source_integrity_and_event_day
test_publish_date_unparseable_alone_remains_denominator_visible
test_incompatible_trusted_revisions_produce_revision_conflicting_without_eligible_child
test_unresolved_batch_child_prevents_any_eligible_child_subset
test_all_frozen_candidates_require_valid_first_list_capture_chain
```

`test_canonical_body_normalization_golden_vectors` is a small parametrized RED set, added before reducer implementation. It asserts root/element/text exact key shapes, allowed tags and transparent recursion; `br -> LF`; the required pre/post LF behavior for `p`, `h3`, `h4`, `li`, `tr`, `td`; CRLF/CR normalization; NFKC; horizontal whitespace collapse; space trimming around LF; repeated-LF collapse; edge trim; stable `normalized_body_sha256` and canonical fact fingerprint; and multibyte UTF-8 byte start/end plus excerpt agreement against normalized bytes. Use v2 JSON body-tree fixtures, not legacy HTML. Assert all title/symbol/product/schedule/publication facts come from selected raw BAPI `data`; `data.id` is diagnostic only; list title supplies no semantic field.

- [ ] **Step 3: Prove RED.**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py -q`

Expected: FAIL because aggregation/parser behavior is absent.

- [ ] **Step 4: Implement reducer in fixed order.**

```text
freeze sorted ArticleDiscovery candidates
-> validate every first_list_capture chain
-> group all DetailObservations by article
-> reject zero/foreign/duplicate observation identity
-> validate bidirectional trusted observation <-> revision <-> raw linkage
-> establish trusted aggregate or certificate-backed detail_unavailable
-> select max(t_detail_trusted_ms, detail_raw_sha256)
-> parse selected BAPI envelope/body
-> reduce selected declaration and every child
-> emit one outcome and one notice per candidate
```

Implement the exact v2 tree grammar/normalization and UTF-8 evidence offsets. Emit child `settlement_asset` and `quote_asset` only as direct selected-body uppercase evidence or `None`; never infer them from symbol/exchangeInfo/title/current web. `None` makes declaration incomplete and prevents all eligible children. Missing schedule facts are exact nested `not_stated` objects, never omitted.

- [ ] **Step 5: Verify GREEN.**

Run the Step 3 command. Expected: PASS; structural contradictions reject before persistence while raw payload quality failures stay in frozen denominator.

---

### Task 3: Build Exact Projections, Metrics And Pre-Completion Summary

**Design coverage:** PG-08..PG-10; INV-10..INV-15, INV-19, INV-21; Delta INV-D01..D04.

**Files:**
- Modify `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py`

**Interfaces:**

```python
def build_precompletion_summary(reduction: AdapterReduction, *, audit_run_id: str,
    source_export_receipt_sha256: str, candidate_manifest_sha256: str) -> dict[str, object]: ...
def deterministic_projection_view(value: object) -> object: ...
```

`deterministic_projection_view` recursively removes only `semantic_extracted_at_ms`; it preserves all other keys/values and row order.

- [ ] **Step 1: Add exact-schema/order RED tests.**

```python
def test_candidate_manifest_is_exact_sorted_and_contains_all_candidates(): ...
def test_every_candidate_has_one_exact_notice_including_detail_unavailable(): ...
def test_parent_outcome_revision_and_diagnostic_jsonl_orders_are_deterministic(): ...
def test_semantic_and_contract_rows_exist_only_for_selected_trusted_authority(): ...
def test_contract_assets_are_source_proved_or_null_never_symbol_inferred(): ...
def test_schedule_facts_are_exact_objects_and_not_stated_is_explicit(): ...
def test_projection_jsonl_order_and_duplicate_logical_row_reject(): ...
def test_historical_fields_and_authority_flags_are_exact_false_or_unknown(): ...
```

Asset test covers evidence `USDT` versus `None`/incomplete/no eligible child and monkeypatches any exchangeInfo/current-web attempt to fail.

- [ ] **Step 2: Add metric/summary RED tests.**

```python
def test_metrics_use_all_parent_outcomes_not_success_rows():
    reduction = reduce_fixture_with(trusted_count=33, terminal_nontrusted_count=2)
    summary = build_precompletion_summary(reduction, audit_run_id='a', source_export_receipt_sha256='0'*64, candidate_manifest_sha256='1'*64)
    assert summary['metrics']['candidate_total_denominator'] == 35
    assert summary['metrics']['trusted_parents_count'] == 33
    assert summary['metrics']['source_integrity_pass_rate'] == pytest.approx(33 / 35)
    assert summary['source_audit_passed'] is False
    assert summary['allowed_next_action'] == 'pending_completion'

def test_summary_binds_candidate_rule_and_exact_manifest_bytes_hash(): ...
def test_parent_outcome_and_summary_exact_schema_reject_missing_extra_or_unknown_values(): ...
def test_forbidden_authority_diagnostics_use_request_observation_identity_and_distinct_count(): ...
def test_summary_rejects_extra_threshold_or_nonfalse_authority_value(): ...
```

- [ ] **Step 3: Prove RED.**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py -q`

Expected: FAIL.

- [ ] **Step 4: Implement exact projection/metric construction.**

Use v2 Sections 12.3-12.6 and the delta verbatim. The diagnostic count is `count(distinct DetailObservation.request_observation_id)` and no network/malformed/publication/revision outcome creates a forbidden-authority diagnostic. Sort rows strictly:

```python
semantic_rows.sort(key=lambda r: (r['source_article_id'], r['detail_revision_id'], r['semantic_extraction_id']))
notice_rows.sort(key=lambda r: r['source_article_id'])
contract_rows.sort(key=lambda r: (r['parent_article_id'], r['canonical_symbol'], r['contract_id']))
parent_outcome_rows.sort(key=lambda r: r['source_article_id'])
detail_revision_rows.sort(key=lambda r: (r['source_article_id'], r['detail_revision_id']))
diagnostic_rows.sort(key=lambda r: r['observation_identity'])
```

Reject tied sort keys/duplicate logical rows. Build metrics only from complete parent outcomes. `audit_candidate_manifest_sha256` is SHA-256 of exact persisted `audit_candidate_manifest.json` bytes, not `manifest_id`; summary also has `candidate_discovery_rule_version='candidate_discovery_rule_v1'`. Pre-completion summary always has `source_audit_passed=false`, `allowed_next_action='pending_completion'`, `permitted_design_options=[]`.

- [ ] **Step 5: Verify GREEN plus old reducer compatibility.**

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py -q
```

Expected: PASS.

---

### Task 4: Add Adapter Persistence And Independent Completed Consumer

**Design coverage:** PG-11, PG-12; INV-14..INV-21; Delta INV-D01..D06.

**Files:**
- Create `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py`
- Create `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py`
- Modify `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py`
- Modify `tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py`

**Interfaces:**

```python
ADAPTER_OUTPUT_PARENT = Path('data/external_signal_shadow/stage1_6a/sealed_export_source_audits')
def persist_adapter_audit(output_root: Path, *, audit_run_id: str, snapshot: VerifiedSourceSnapshot,
    reduction: AdapterReduction, semantic_extracted_at_ms: int) -> Path: ...
def load_completed_adapter_audit(project_root: Path, output_root: Path, source_export: Path) -> dict[str, object]: ...
```

- [ ] **Step 1: Add RED storage/consumer tests.**

```python
def test_persistence_writes_exact_artifacts_precompletion_then_manifest_last(tmp_path): ...
def test_precompletion_summary_has_only_fixed_nonfinal_pass_and_pending_action(tmp_path): ...
def test_partial_root_without_completion_manifest_is_nonconsumable(tmp_path): ...
def test_completed_consumer_rejects_hash_shape_and_projection_tamper(tmp_path): ...
def test_completed_consumer_rejects_coherent_source_derived_artifact_tamper(tmp_path): ...
def test_completed_consumer_rejects_boolean_and_action_tampered_together(tmp_path): ...
def test_completed_consumer_ignores_only_semantic_extracted_at_ms_in_rebuild(tmp_path): ...
def test_completed_consumer_rejects_candidate_summary_binding_threshold_and_flag_mismatch(tmp_path): ...
def test_completed_consumer_rejects_missing_extra_or_unknown_projection_schema_values(tmp_path): ...
def test_completed_consumer_rejects_missing_or_mutated_explicit_source_export(tmp_path): ...
def test_threshold_drift_is_consumer_rejection_not_new_pass(tmp_path): ...
```

Tamper cases must include one `settlement_asset`, one JSONL order, one nested evidence ID, and one candidate-manifest byte. The coherent tamper test modifies each of `source_export_receipt.json`, `parent_audit_outcomes.jsonl`, `detail_revisions.jsonl`, `audit_diagnostics.jsonl` and summary authority projection in turn, recomputes that artifact tuple in `completion_manifest.json`, and still requires completed-consumer rejection. This proves source-byte reconstruction rather than only manifest SHA verification.

- [ ] **Step 2: Prove RED.**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py -q`

Expected: FAIL because adapter storage does not exist.

- [ ] **Step 3: Implement fresh-root manifest-last persistence.**

Use same-directory temp files and `Path.replace()`. Exact writer sequence:

```text
validate new confined root and basename/run-id
-> write receipt plus all Section 12.2 derived artifacts
-> write exact pre-completion summary
-> reread/hash/schema-check persisted artifacts
-> rebuild metrics/predicate from durable parent outcomes
-> re-reduce retained source bytes and exact-compare every source-derived authority projection
-> atomically write completion_manifest.json LAST
```

The writer and completed consumer must rebuild and compare `source_export_receipt.json`, `audit_candidate_manifest.json`, `parent_audit_outcomes.jsonl`, `detail_revisions.jsonl`, `semantic_extractions.jsonl`, `delisting_notices.jsonl`, `delisting_contracts.jsonl`, `audit_diagnostics.jsonl`, and the summary authority projection. The only comparison exclusions are Design-approved local run metadata: `semantic_extracted_at_ms`, `audit_run_id` where the same persisted root supplies it, and write/completion timestamps. No other field may be ignored. Manifest lists every prior artifact sorted `(relative_path, sha256)`. Only manifest persists final pass/action/options. The completed consumer verifies all stored hashes/bytes/schema/receipt/threshold/false flags, calls `load_verified_source_snapshot` once, re-reduces the identical explicit source, and rejects any rebuilt projection/metric/predicate/action mismatch via `AdapterInputError`.

- [ ] **Step 4: Verify GREEN.**

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py -q
```

Expected: PASS; input export bytes are never written.

---

### Task 5: Add Thin Offline CLI And Integration Boundary Tests

**Design coverage:** PG-01, PG-11..PG-13; INV-01, INV-14, INV-16..INV-21.

**Files:**
- Create `scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py`
- Create `tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py`

**CLI:**

```bash
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py \
  --project-root "$PWD" --source-export "$SOURCE_EXPORT" \
  --audit-run-id "$AUDIT_RUN_ID" \
  --output-root "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/$AUDIT_RUN_ID"
```

No URL, network permission, fixture, resume, threshold override, action or trading flag is accepted.

- [ ] **Step 1: Add CLI RED tests.**

```python
def test_cli_runs_synthetic_completed_export_to_separate_fresh_root(tmp_path): ...
def test_cli_rejects_existing_or_mismatched_run_id_output_root_before_write(tmp_path): ...
def test_cli_rejects_invalid_source_before_creating_output_root(tmp_path): ...
def test_cli_has_no_network_stage15_or_legacy_fixture_import_boundary(): ...
def test_legacy_fixture_cli_remains_fixture_only_and_unmodified(): ...
```

The static test parses adapter modules/script with `ast`, rejecting imports/references to `requests`, `urllib.request`, `http`, `websocket`, `selenium`, `stage1_5`, `strategies`, `risk`, `execution`, `process_capture_bundle`, and `persist_audit_artifacts`.

- [ ] **Step 2: Prove RED.**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py -q`

Expected: FAIL because CLI is absent.

- [ ] **Step 3: Implement orchestration only.**

```python
snapshot = load_verified_source_snapshot(args.project_root, args.source_export)
extracted_at_ms = now_ms()
reduction = reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=extracted_at_ms)
completion_path = persist_adapter_audit(args.output_root, audit_run_id=args.audit_run_id,
    snapshot=snapshot, reduction=reduction, semantic_extracted_at_ms=extracted_at_ms)
```

Validate output basename before source read/output creation. Catch `AdapterInputError`, print concise stderr failure and exit 1. On success print completion path and exit 0. Do not add fallback selection or any other side effect.

- [ ] **Step 4: Verify bounded full suite.**

```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py -q
```

Expected: PASS.

---

### Task 6: Run Real Export, Independent Consumer And Completion Audit

**Design coverage:** all PG-01..PG-13, all INV-01..INV-21, all Delta INV-D01..D06.

**Files:** Create the allowed completion-audit review only if `audit-plan-completion` produces it. Modify nothing else. Requires the `WORKSPACE_PROVENANCE_JSON` captured by Task 0.

- [ ] **Step 1: Run explicit real export after all tests pass.**

```bash
export AUDIT_RUN_ID="sealed_export_adapter_$(date -u +%Y%m%dT%H%M%SZ)"
export ADAPTER_OUT="data/external_signal_shadow/stage1_6a/sealed_export_source_audits/$AUDIT_RUN_ID"
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py \
  --project-root "$PWD" --source-export "$SOURCE_EXPORT" \
  --audit-run-id "$AUDIT_RUN_ID" --output-root "$ADAPTER_OUT"
```

Expected: new completed root or exit 1 before root creation for structural source failure. A completed `source_audit_passed=false` is a valid result; recorded 33/35 source integrity is below 0.95 and must not be laundered.

- [ ] **Step 2: Invoke the independent consumer against the identical explicit source.**

```bash
PYTHONPATH=src:. .venv/bin/python - "$PWD" "$ADAPTER_OUT" "$SOURCE_EXPORT" <<'PY'
from pathlib import Path
import sys
from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter_storage import load_completed_adapter_audit
m = load_completed_adapter_audit(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))['completion_manifest']
print({'status': m['status'], 'source_audit_passed': m['source_audit_passed'], 'allowed_next_action': m['allowed_next_action'], 'authority_flags': m['authority_flags']})
PY
```

Expected: `status='complete'`; all flags false. False maps to `source_audit_failed_or_inconclusive` with empty options. True can only map to Design-only options, never replay/risk/trading/deployment.

- [ ] **Step 3: Rebind approved authority immediately before completion audit.**

```bash
export EXPECTED_V2_DESIGN_SHA="1cb90f89113ceda4d2037cb62d60b8a9f769f7d58c467ad0e515332bc13563fd"
export EXPECTED_SCHEMA_DELTA_SHA="2572849bf7df9154170ebc28f9687315728566a7c9498153f346d61308aaeb34"
export EXPECTED_TERMINAL_CORRECTION_SHA="4bc7bc60a5435f9d71735319eac0dc84bf655bd94bc5f065652545f472596aae"
export PLAN_PATH="docs/plans/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-v2-implementation-plan_CN.md"
: "${APPROVED_PLAN_SHA:?STOP: set the SHA-256 from the user/reviewer approval record}"
PYTHONPATH=src:. .venv/bin/python - "$EXPECTED_V2_DESIGN_SHA" "$EXPECTED_SCHEMA_DELTA_SHA" "$EXPECTED_TERMINAL_CORRECTION_SHA" "$PLAN_PATH" "$APPROVED_PLAN_SHA" <<'PY'
import hashlib, sys
from pathlib import Path
v2_sha, delta_sha, terminal_sha, plan_path, approved_plan_sha = sys.argv[1:]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha('docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md') == v2_sha, 'STOP: v2 Design authority changed'
assert sha('docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-adapter-derived-artifact-schema-delta-design_CN.md') == delta_sha, 'STOP: Schema Delta authority changed'
assert sha('docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6b-terminal-status-field-contract-correction-design_CN.md') == terminal_sha, 'STOP: TerminalStatus correction authority changed'
assert sha(plan_path) == approved_plan_sha, 'STOP: approved Plan changed after Task 0'
print({'completion_authority_rebind': 'PASS'})
PY
```

Expected: all three Design authority bytes and the exact reviewer-approved Plan bytes still match Task 0. Any mismatch is a `STOP`, even though the Plan path is otherwise an allowed documentation path.

- [ ] **Step 4: Enforce whitelist and completion gate.**

```bash
PYTHONPATH=src:. .venv/bin/python - "$BASE_SHA" "$WORKSPACE_PROVENANCE_JSON" <<'PY'
import hashlib, json, os, subprocess, sys
from pathlib import Path
base, provenance_path = sys.argv[1:]
baseline = json.loads(Path(provenance_path).read_text())
def fingerprint(rel):
    p = Path(rel)
    if p.is_symlink(): return {'type': 'symlink', 'target': os.readlink(p)}
    if p.is_file(): return {'type': 'file', 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    return {'type': 'other'}
for rel, expected in baseline.items():
    assert Path(rel).exists() or Path(rel).is_symlink(), {'STOP': 'preexisting_path_missing', 'path': rel}
    assert fingerprint(rel) == expected, {'STOP': 'preexisting_path_changed', 'path': rel}
tracked = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', base], text=True).splitlines()
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z']).decode().split('\0')
current_changed = set(tracked) | {path for path in untracked if path}
implementation_changed = current_changed - set(baseline)
allowed = {
    'src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py',
    'src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py',
    'scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py',
    'tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py',
    'tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py',
    'tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py',
    'tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py',
    'docs/plans/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-v2-implementation-plan_CN.md',
    'docs/reviews/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-v2-completion-audit_CN.md',
}
assert implementation_changed <= allowed, {'STOP': 'out_of_scope_changed_paths', 'paths': sorted(implementation_changed - allowed)}
print({'tracked_changed': sorted(tracked), 'untracked': sorted(path for path in untracked if path), 'implementation_changed': sorted(implementation_changed)})
PY
git diff --check "$BASE_SHA" -- \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py \
  scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py \
  tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py
```

Expected: all pre-existing dirty/untracked paths are byte-identical; tracked and untracked changed-path union contains only the exact allowlist. Invoke `.agent/skills/audit-plan-completion`; completion claim requires its `complete` verdict. Otherwise stop and use `remediate-completion-audit`.

## Plan Self-Review

- Every v2 invariant and Delta invariant maps to Tasks 0-6.
- Stage 1.6B loader is reused, not copied; old fixture Stage 1.6A and config are regression-tested but unchanged.
- Minimal production surface: two adapter modules and one thin CLI. No registry, factory, network client, migration, resume/checkpoint machine or config change.
- This is a Plan only. Review with `reviewing-implementation-plans`; implementation and deployment remain forbidden until the review verdict is `Approve` and the user separately approves execution.
