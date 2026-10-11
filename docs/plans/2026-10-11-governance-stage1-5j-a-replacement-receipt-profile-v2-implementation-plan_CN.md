# Governance Stage 1.5J-A Replacement Receipt Profile v2 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this Plan task-by-task.

**Goal:** 在不改变 `stage1_5j_a_receipt_v1` 已冻结接受语义、J-A 代码或任何 receipt bytes 的前提下，为独立 Rule 17 verifier 增加唯一的 `stage1_5j_a_receipt_v2` profile，并对唯一 replacement receipt 建立可复核的结构验证与外部 identity evidence。

**Architecture:** 保留 v1 的显式入口和 literal constants；先用冻结的 v1 脚本与测试源生成行为 oracle，再增加一个显式 v2 分支。v2 仅改变已批准的 authority chain 与 persisted response-path grammar，其他 J-A 结构检查复用本地纯校验路径。receipt root 永远只读；真实 root identity 由 Plan evidence 中的外部 canonical JSON 和 sidecar 绑定，不由 verifier 自我声明。

**Tech Stack:** Python 3 standard library, `argparse`, `hashlib`, `json`, `pathlib`, `pytest`, Ruff, existing Rule 17 verifier, J-A public strict loader.

---

## 1. Approved Authority And Frozen Contract

**User-approved Design:**

```text
docs/designs/2026-10-11-governance-stage1-5j-a-replacement-receipt-profile-v2-design-delta_CN.md
SHA-256: 1d3155c8a38e53f851aaa0f51c8c2ec6ef6aaaf811e4330d8b1c0a491796a86b
```

This Plan is a deterministic governance change, not an alpha, network, collection, replay, price-response, execution, paper-trading, or live-trading change. L2 research semantics are `N/A`; L0 and L1 remain mandatory.

### 1.1 Frozen inputs that Task 0 must verify

```text
Planning BASE_SHA
  bfe3e97fd39adfa40aab8d64c5fb01c3b093aa9a

Parent Governance Design
  docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md
  73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4

J-A parent Design
  docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md
  b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a

J-A conformance Delta
  docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md
  6063ed103d31fcf6c60ad8106eb13650f54b74272182c78bf8e81f9ba48a91ac

J-A nullability Delta
  docs/designs/2026-10-09-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-design-delta_CN.md
  f427df9435c8b9c8dd2b4b45c24bbbbd595df2c7e8d209f40f6fe2cd13b00f3c

J-A nullability R1 Plan
  docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan-r1_CN.md
  b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82

Pre-v2 verifier source
  scripts/governance/verify_artifact_schema.py
  0071715439e5fd9f64d9b6e62fe86e027ac8f26f6697873202cd521c52fb8c98

Pre-v2 verifier test source
  tests/scripts/governance/test_verify_artifact_schema.py
  369627b1f34423f439e4ed977e060de22bd9107b29feb5c3721aa349301a99c3
```

**Frozen positive receipt identity, read-only:**

```text
profile_id = stage1_5j_a_receipt_v2
profile_contract_version = 2
run_id = stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
root = data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
manifest.json         = b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf
summary.json          = 722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b
review_CN.md          = 1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152
request_journal.jsonl = b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa
```

**Frozen negative receipt identity, read-only:**

```text
data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z
```

The pre-v2 correction evidence is immutable input:

```text
.git/plan-execution/stage1_5j_a/b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82/evidence/receipt_closure_governance_rule17_correction_supplement.md
SHA-256: 0868fab441b410cc2d4b68371791955a041ff440451e3a6cb8ac5457546f58ea
```

Its `.md.sha256` sidecar and the original immutable receipt closure report SHA `6037344c5852f7ac8b91db8d45d050d7e192518513a2d31c9edccf64298c6453` must validate in Task 0. The supplement establishes that historical verifier `42e66...` is non-admissible Rule 17 positive evidence; this Plan must not repair, replace, or reinterpret it.

## 2. Allowed Change Scope

Allowed implementation paths:
- `scripts/governance/verify_artifact_schema.py`

Allowed verification paths:
- `tests/scripts/governance/test_verify_artifact_schema.py`

Allowed documentation paths:
- none. The approved Design and this Plan are read-only authority documents during execution.

Allowed generated/runtime artifacts:
- `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/base_sha`
- `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/implementation_authorization.txt`
- `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/implementation_authorization.sha256`
- `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/allowed_change_scope.json`
- `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/allowed_change_scope.sha256`
- `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/execution_authority.json`
- `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/execution_authority.sha256`
- SHA-256 sidecars for the preceding generated authority files
- `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/**`
- isolated disposable directories beneath `/tmp/stage1_5j_a_receipt_v2_*` only; remove after every probe.

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`
  - compatibility evidence: direct public strict-loader positive load of frozen replacement root; verifier never imports it.
- `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/**`
  - evidence: before/after four top-level SHA-256 values and byte inventory equal; never mutate this root.
- `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z/**`
  - evidence: v1 returns nullability diagnostic and v2 returns authority/profile diagnostic; never mutate this root.
- `configs/base.py`
  - compatibility evidence: direct `RISK_LIVE_TRADING_ENABLED is False` assertion.
- `docs/designs/2026-10-11-governance-stage1-5j-a-replacement-receipt-profile-v2-design-delta_CN.md`
  - authority evidence: exact SHA-256 matches the user approval.
- `.agent/skills/audit-plan-completion/SKILL.md`, `.agent/skills/reviewing-implementation-plans/SKILL.md`, and `docs/production_artifacts/tri_agent_prompt_library_CN.md`
  - consumer classification: affected but unchanged; they invoke or require the CLI generically and must not assume a closed profile allowlist.

Forbidden:
- Any change to J-A source, J-A tests, J-A CLI, parser, config, receipt, raw data, manifest, summary, review, request journal, or network authorization.
- Any change to `stage1_5j_a_receipt_v1` literal values, existing v1 test cases, expected v1 results, profile version, or v1 acceptance semantics.
- Dynamic profile registry, dynamic Design/Plan lookup, alias, fallback, configuration option, compatibility parser, target-module import/source inspection, `.git` access by verifier, subprocess/network/write from verifier, or dependency addition.
- Any mutation outside allowed paths, repository-wide formatter/autofix, destructive cleanup, commit, push, deployment, SSH, runtime collection, replay, J-B consumption, paper/live trading, execution, or risk-threshold change.

## 3. Invariant-to-Task Matrix

| Design invariant | Production enforcement | Mechanical proof | Fail-closed result |
| --- | --- | --- | --- |
| `INV-GSI-V2-01` | Explicit two-branch CLI dispatch; v1 wrapper retains historical behavior. | Pre/post v1 corpus from frozen `BASE_SHA` fixture/test source. | Any row mismatch: `STOP=governance_v2_v1_behavioral_oracle_mismatch`. |
| `INV-GSI-V2-02` | v2 literal constants validate ordered authority chain and exact root packet. | v2 fixture plus real-root authority mutations. | `rc=1` authority-chain diagnostic; no alias/fallback. |
| `INV-GSI-V2-03` | Verifier validates structure only; executor produces non-authoritative candidate/transcript evidence, while the independent Receipt Closure Auditor alone writes final identity evidence. | Auditor-owned canonical `v2_receipt_closure_evidence.json` with the candidate's exact key set, two audited state changes, canonical bytes, sidecar, four-hash comparator, and strict-loader result. | `STOP=governance_v2_receipt_identity_evidence_mismatch`. |
| `INV-GSI-V2-04` | v2 persisted responses are exact receipt-relative `raw/...` members. | Root-prefixed and non-manifest path mutations. | `rc=1` response-path diagnostic. |
| `INV-GSI-V2-05` | Inherited exact J-A structure is local literal validation, no target import. | Frozen v1 `MUTATION_CASES` replayed through v2 canonical overlay without exclusions, v1 corpus, AST isolation, sealed-tree probes. | `rc=1` structural diagnostic. |
| `INV-GSI-V2-06` | Verifier creates no persistent state. | before/after real-root inventory; mutations only in `/tmp`. | `STOP=governance_v2_real_root_mutation_detected`. |
| `INV-GSI-V2-07` | No authority flag/config/runtime/J-B path changes. | L0 assertion, static absence, scope/index proof. | Forbidden path/flag blocks audit. |

## 4. Execution Rules

1. Execute in order. A separate implementation authorization is mandatory in addition to Plan approval. Task 0 must persist and validate its exact text, scope digest, and authority record before source/test edits. If a Task 0 authorization, baseline, ownership, topology, or scope gate fails, stop before code/test edits and classify under L1 Rule 16.
2. Use RED -> GREEN for verifier/test edits. Never alter frozen v1 cases to make the oracle green.
3. The verifier remains stdlib-only and read-only. It must never import `src`, `configs`, test source, J-A code, or invoke process/network APIs.
4. Evidence is audit output, not verifier input or acceptance authority. The verifier never reads `.git`.
5. No task has a commit step. User retains version-control authority.

---

### Task 0: Freeze Authority, Scope, Real Roots, And v1 Behavioral Oracle

**Invariants:** `INV-GSI-V2-01`, `INV-GSI-V2-02`, `INV-GSI-V2-03`, `INV-GSI-V2-06`, `INV-GSI-V2-07`.

**Files:**
- Read: all §1.1 authorities, verifier/test bytes, both real roots, correction supplement and sidecar.
- Create: `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/base_sha`
- Create: `implementation_authorization.txt`, `allowed_change_scope.json`, and `execution_authority.json` in the same Plan-evidence root, with SHA-256 sidecars.
- Create: `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/pre_execution_worktree_ledger.json`
- Create: `evidence/pre_execution_tracked_worktree.diff`, `evidence/pre_execution_index.diff`, and `evidence/topology_impact_assessment.json`, each with SHA-256 sidecars.
- Create: `evidence/v1_behavioral_oracle_harness.py`, `evidence/v1_behavioral_oracle_pre.json`, and `evidence/v2_inherited_mutation_contract.json`, each with SHA-256 sidecars.
- Do not modify: repository source/test, Design, Plan, receipt roots, or J-A evidence.

**Step 1: Freeze the separate implementation-authorization packet before any edit.**

Plan approval alone is insufficient. Before creating any execution evidence or changing source/test, the executor must receive the following user-supplied text verbatim and copy it unchanged to `implementation_authorization.txt`:

```text
我授权执行 Implementation：docs/plans/<APPROVED_PLAN_PATH>（SHA-256: <APPROVED_PLAN_SHA256>）。
绑定 Design：docs/designs/2026-10-11-governance-stage1-5j-a-replacement-receipt-profile-v2-design-delta_CN.md（SHA-256: 1d3155c8a38e53f851aaa0f51c8c2ec6ef6aaaf811e4330d8b1c0a491796a86b）。
允许仅修改：scripts/governance/verify_artifact_schema.py；tests/scripts/governance/test_verify_artifact_schema.py；.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/**。
不允许 commit、push、deployment、SSH、network、receipt generation、J-B consumption、alpha、replay、signal、paper trading、live trading 或 execution action。
```

`<APPROVED_PLAN_PATH>` and `<APPROVED_PLAN_SHA256>` must be replaced exactly by the independently reviewed Plan path and SHA. No executor may generate, normalize, paraphrase, or infer this text. Create canonical `allowed_change_scope.json` with exact keys `implementation_paths`, `verification_paths`, `generated_paths`, and `forbidden_capabilities`, then create `execution_authority.json` with exact keys:

```text
approved_plan_relative_path
approved_plan_sha256
approved_design_relative_path
approved_design_sha256
implementation_authorization_relative_path
implementation_authorization_sha256
implementation_authorization_text_sha256
planning_base_sha
allowed_change_scope_relative_path
allowed_change_scope_sha256
```

The record must bind the exact copied authorization text, this Plan, the approved v2 Design, the fixed `bfe3e97...` baseline, and the canonical scope file. Write sidecars and validate every field and digest before proceeding. Missing, extra, or mismatched authorization/scope fields, text, or digest is `STOP=implementation_authorization_missing` or `STOP=implementation_authorization_mismatch`.

**Step 2: Verify approved bytes and baseline before any edit.**

Run from repository root with `set -euo pipefail`:

```bash
test "$(git rev-parse HEAD)" = "bfe3e97fd39adfa40aab8d64c5fb01c3b093aa9a"
git diff --cached --quiet
shasum -a 256 \
  docs/designs/2026-10-11-governance-stage1-5j-a-replacement-receipt-profile-v2-design-delta_CN.md \
  docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md \
  docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md \
  docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md \
  docs/designs/2026-10-09-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-design-delta_CN.md \
  docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan-r1_CN.md \
  scripts/governance/verify_artifact_schema.py \
  tests/scripts/governance/test_verify_artifact_schema.py
```

Recompute this Plan SHA-256 and require equality with both the Plan approval and `execution_authority.json`. Write verified `HEAD` to `base_sha` and hash it. Expected: every digest equals §1.1, Plan/Design/implementation-authorization bindings match, and index is empty. Any mismatch is `STOP=approved_authority_mismatch` or `STOP=governance_v2_baseline_mismatch`.

**Step 3: Create the pre-execution ownership ledger.**

Record canonical JSON with `planning_base_sha`, Design/Plan SHA-256, full `git status --short --untracked-files=all`, task-induced whitelist, `foreign_untracked_files`, and `preexisting_untracked_files`. For every pre-existing tracked-dirty and untracked path, record `relative_path`, `git_state`, `file_type`, `exists`, `byte_count`, and `sha256`; for a directory, record a sorted recursive member inventory and its SHA-256. Persist the exact outputs of `git diff --binary` and `git diff --cached --binary` as named files above, recording each byte count and SHA-256 in the ledger. Pre-existing J-B draft and this approved v2 Design/Plan must remain separately attributed. If source/test differs from §1.1, or an allowed source/test path is already dirty, stop as `BLOCKED_SCOPE_DRIFT`; never rebaseline it.

**Step 4: Perform mandatory shared-CLI topology and consumer preflight.**

Run and persist exact command/output/RC evidence:

```bash
graphify query "verify_artifact_schema" --budget 5000
rg -n "verify_artifact_schema|stage1_5j_a_receipt_v1|stage1_5j_a_receipt_v2" \
  --glob '!data/**' --glob '!*.pyc' .
```

Classify every result in `topology_impact_assessment.json` as exactly one of `requires_modification`, `affected_but_unchanged`, or `irrelevant_advisory`. The governance test is `requires_modification`; the audit/review skills and prompt library are `affected_but_unchanged` with compatibility evidence that they call the profile CLI generically; historical documents are `irrelevant_advisory`. A no-node Graphify response is advisory only, not absence proof; the `rg` source inspection is controlling. Any actual runtime consumer outside the whitelist that requires a semantic or CLI-contract change is `STOP=BLOCKED_SCOPE_DRIFT` before RED.

**Step 5: Recompute real-root and correction-evidence facts.**

Require the four replacement-root hashes and run ID in §1.1, plus a byte inventory before work. Validate:

```bash
shasum -a 256 -c \
  .git/plan-execution/stage1_5j_a/b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82/evidence/receipt_closure_governance_rule17_correction_supplement.md.sha256
```

Require the referenced original closure report to retain SHA `6037344c5852f7ac8b91db8d45d050d7e192518513a2d31c9edccf64298c6453`. Expected: `OK`; roots remain read-only. Sidecar/root/hash mismatch is `BLOCKED_SPEC_DRIFT`.

**Step 6: Materialize the create-once v1 oracle and inherited-v2 matrix before source edits.**

Use exact `git show bfe3e97:<path>` bytes for frozen verifier and frozen test module. Create `v1_behavioral_oracle_harness.py` once before the baseline run; it may call only frozen registered `_build_minimal_valid_receipt` and `_apply_mutation` helpers in a disposable mock project. Record its SHA-256 in `v1_behavioral_oracle_pre.json` before execution and never modify or replace it. The harness records canonical rows for `minimal_valid_v1`, every frozen `MUTATION_CASES` ID without deletion/relabeling, and `legacy_negative_v1`.

Each row includes `case_id`, `rc`, `diagnostic_class`, and SHA-256 of captured diagnostic text. `diagnostic_class` is the frozen case's `expected_diag_keyword`, proven present in the actual diagnostic; use `success` for minimal valid and `post_launch_row_count_nullability` for legacy. Record frozen verifier/test SHA-256, ordered case IDs, harness SHA-256, oracle JSON SHA-256, and legacy four top-level hashes. Expected: minimal `rc=0`; every mutation and legacy row `rc=1`.

Create `v2_inherited_mutation_contract.json` from the same frozen case list. It must contain the ordered frozen case IDs, `frozen_case_count`, `v2_replayed_case_count`, and an exact `exclusion_replacement_table`. This Plan requires `exclusion_replacement_table=[]`: the v2 canonical overlay changes only valid fixture authority/path values, then replays every inherited one-mutation fault through v2. If any frozen mutation cannot be replayed without an exclusion or replacement, stop as `BLOCKED_SPEC_DRIFT`; do not silently omit, relabel, or weaken it.

Missing/extra case, unexpected RC, or source hash mismatch is `STOP=governance_v2_v1_oracle_capture_failed`.

**Step 7: Record historical v1 results.**

Run v1 against legacy root and replacement root. Expected: legacy `rc=1` identifies `post_launch_row_count` nullability; replacement `rc=1` identifies v1 `approved_design` mismatch. These are facts, not v2 success evidence.

---

### Task 1: RED - Add Explicit v2 Contract Tests Without Weakening v1

**Invariants:** all `INV-GSI-V2-*`.

**Files:**
- Modify: `tests/scripts/governance/test_verify_artifact_schema.py`
- Do not modify: verifier until all designated v2 RED cases fail for unsupported profile.

**Step 1: Preserve frozen v1 fixture and replay every inherited mutation through the v2 overlay.**

Add v2 fixture preparation that starts from registered `_build_minimal_valid_receipt`, applies only a declared v2 authority/path overlay, then canonically rebuilds only affected fixture manifest entries. It is verifier-mechanics only, never real-root, semantic closure, or downstream evidence. The overlay uses every literal in approved Design §4.1 and §5.2, nullability Delta as `approved_design`, R1 Plan as `approved_plan`, and receipt-relative `raw/...` values in terminal/projection rows. It never reads a Design at runtime.

Load the ordered frozen case IDs and expected diagnostic classes from Task 0's immutable `v2_inherited_mutation_contract.json` and `v1_behavioral_oracle_pre.json`, not from a mutable post-edit table. For each frozen `MUTATION_CASES` mutation, apply the v2 overlay to the registered fixture and replay the single inherited mutation. The expected v2 result is `rc=1` at the corresponding inherited structural gate. The frozen contract requires zero exclusions and zero replacements; a missing, extra, relabeled, multi-mutation, or unexpectedly passing row fails the test.

**Step 2: Add RED tests.**

1. `test_v2_profile_authority_literals_exact`: parse source constants and assert the exact v2 Design Delta, parent Governance Design, parent J-A Design, conformance Delta, nullability Delta, R1 Plan, profile ID, profile version, and literal two-profile supported set from Design §4.1. It must reject extra authority aliases or allowlists.
2. `test_v2_profile_is_explicit_and_v1_has_no_alias_or_fallback`: only literal v1/v2 IDs are accepted; version-like aliases return `rc=2`.
3. `test_stage1_5j_a_receipt_v2_minimal_mechanics_fixture`: derived v2 fixture returns `rc=0`.
4. `test_stage1_5j_a_receipt_v2_inherited_mutation_matrix`: replay every frozen inherited case through the v2 canonical overlay and require the Task 0 ordered IDs/cardinality with no exclusion/replacement entry.
5. `test_stage1_5j_a_receipt_v2_authority_chain_rejects_single_field_mutations`: independently change v2 approved-design path/SHA and approved-plan path/SHA; rebuild fixture manifest; each returns `rc=1` at authority gate.
6. `test_stage1_5j_a_receipt_v2_response_path_is_receipt_relative`: valid `raw/...` passes; root-prefixed and safe non-manifest `raw/...` paths each return `rc=1` after matching terminal/projection mutation and manifest rebuild.
7. `test_stage1_5j_a_receipt_v2_nonpersisted_nullability_and_sealed_tree`: `post_launch_row_count: null -> 0`, one authority flag true, one extra file, grammar-disallowed manifest member, root/ancestor/descendant symlink, and unrebuilt manifest-member mutation each fail at intended gate.
8. `test_v2_external_identity_comparator_rejects_review_hash_drift`: mutate fixture `review_CN.md`, rebuild manifest entry, and prove a test-local external tuple comparator rejects observed review SHA. Structural verifier may pass this content-only copy.
9. `test_real_roots_have_profile_specific_read_only_results`: v1 legacy nullability failure and v2 legacy authority/profile failure without root mutation.
10. `test_real_replacement_root_v2_passes_without_writes`: records before/after inventory, runs v2, expects `rc=0` and no root change.

Keep and extend AST isolation only to assert both profile paths retain no target import/source loading, `.git` access, write API, subprocess, dynamic import, or network API. Do not relax v1 restrictions.

**Step 3: Run RED.**

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/scripts/governance/test_verify_artifact_schema.py -k 'v2 or real_roots'
```

Expected before implementation: v2 success fails because profile is unsupported; v1 remains unchanged. Any v2 case passing before intended code exists is `BLOCKED_IMPLEMENTATION_DEFECT`.

---

### Task 2: GREEN - Add the Bounded v2 Profile Branch

**Invariants:** `INV-GSI-V2-01`, `INV-GSI-V2-02`, `INV-GSI-V2-04`, `INV-GSI-V2-05`, `INV-GSI-V2-07`.

**Files:**
- Modify: `scripts/governance/verify_artifact_schema.py`

**Step 1: Add literal v2 constants only.**

Add `PROFILE_ID_V1`, `PROFILE_ID_V2`, versions `1`/`2`, and `SUPPORTED_PROFILES = frozenset({PROFILE_ID_V1, PROFILE_ID_V2})`. Add v2 literal constants for approved Design Delta, parent Governance Design, parent J-A Design, first remediation Delta, nullability Delta, and R1 Plan exactly as Design §4.1. The authority constants must be direct literals, not aliases, collections with spare entries, runtime document reads, or a generic profile registry/configuration.

**Step 2: Preserve v1 flow and isolate only differences.**

Retain explicit `verify_stage1_5j_a_receipt_v1(...)` wrapper with historical literals/diagnostics. Add explicit `verify_stage1_5j_a_receipt_v2(...)` wrapper. Shared local pure helpers are allowed only for identical inherited checks.

Parameterize only:
- authority: v1 keeps existing historical approved-design membership; v2 requires exact nullability-Delta `approved_design` and exact R1 `approved_plan` path/SHA;
- persisted response path: v1 keeps `manifest.root_relative_path + "/"` prefix; v2 requires safe receipt-relative `raw/...`, exact manifest member, and matching member SHA.

All other manifest/schema/enum/nullability/journal/projection/flag/path/symlink/sealed-tree checks remain literal validation. v2 requires all four `archive_request_nonpersisted` trade fields `None`; it rejects legacy at authority/profile before nullability evaluation.

**Step 3: Use explicit CLI dispatch.**

```python
if args.profile == PROFILE_ID_V1:
    diag = verify_stage1_5j_a_receipt_v1(project_root, artifact_root_arg)
elif args.profile == PROFILE_ID_V2:
    diag = verify_stage1_5j_a_receipt_v2(project_root, artifact_root_arg)
else:
    # existing rc=2 unsupported-profile path
```

No root-prefix normalization for v2 and no v2-to-v1 retry. Return codes remain `0` success, `1` contract violation, `2` unsafe CLI use.

**Step 4: Run GREEN.**

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/scripts/governance/test_verify_artifact_schema.py
```

Expected: v1 and v2 tests pass. Any v1 regression is `STOP=governance_v2_v1_regression`.

---

### Task 3: Prove Exact v1 Behavioral Compatibility After v2 Edit

**Invariants:** `INV-GSI-V2-01`, `INV-GSI-V2-05`.

**Files:**
- Read: frozen `bfe3e97` v1 verifier/test bytes and Task 0 oracle.
- Create: `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/v1_behavioral_oracle_post.json`
- Create: `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/v1_behavioral_oracle_comparison.json`
- Create: SHA-256 sidecars.

**Step 1: Re-run frozen corpus with post-v2 verifier.**

Use the exact create-once Task 0 harness bytes and SHA-256, its frozen test fixture/mutation source from `git show bfe3e97:tests/scripts/governance/test_verify_artifact_schema.py`, and modified verifier bytes. Do not use mutable current `MUTATION_CASES` as corpus source. A harness SHA mismatch is `STOP=governance_v2_v1_oracle_harness_mismatch`.

**Step 2: Compare mechanically.**

Require identical ordered case list and identical `(case_id, rc, diagnostic_class)` for every row. `minimal_valid_v1` remains `rc=0`; all mutation/legacy rows remain `rc=1`; post diagnostic contains frozen class and matches recorded diagnostic-text SHA where fixture path is deterministic. Write comparison JSON with baseline/post source SHAs, the exact harness SHA, pre-oracle SHA, post-oracle SHA, `equal=true`, and per-case rows. Any mismatch is `STOP=governance_v2_v1_behavioral_oracle_mismatch`.

---

### Task 4: Real-Root v2 Evidence And Isolated Mutation Probes

**Invariants:** `INV-GSI-V2-02`, `INV-GSI-V2-03`, `INV-GSI-V2-04`, `INV-GSI-V2-05`, `INV-GSI-V2-06`, `INV-GSI-V2-07`.

**Files:**
- Read-only: both real roots and J-A public strict-loader module.
- Create: `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/v2_receipt_closure_candidate.json`
- Create: `v2_structural_verifier_transcript.json`, `strict_loader_transcript.json`, `v2_real_root_mutation_matrix.json`, and sidecars in the same evidence directory.
- Do not create: `v2_receipt_closure_evidence.json` or its sidecar. Those canonical artifacts belong only to the independent Receipt Closure Auditor in Task 8.

**Step 1: Positive independent v2 structural validation.**

```bash
.venv/bin/python scripts/governance/verify_artifact_schema.py \
  --profile stage1_5j_a_receipt_v2 \
  --artifact-root data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
```

Expected `rc=0`. Record stdout/RC, verifier SHA, profile/version, root/run, four hashes, and before/after recursive byte/path inventory equality.

**Step 2: Independently invoke J-A public strict loader.**

```bash
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from pathlib import Path
from research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
    load_verified_stage1_5j_a_historical_archive_coverage_root,
)
root = Path(
    "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/"
    "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
)
summary = load_verified_stage1_5j_a_historical_archive_coverage_root(root)
assert summary["run_id"] == root.name
print(summary["analysis_state"])
PY
```

Expected `rc=0`. Record command, module path, result digest, and RC separately. State that domain loader and v2 verifier are both required; neither substitutes for the other.

**Step 3: Produce non-authoritative closure candidate evidence.**

Write `v2_receipt_closure_candidate.json` plus sidecar with exact keys:

```text
profile_id
profile_contract_version
governance_profile_design_delta_relative_path
governance_profile_design_delta_sha256
governance_parent_design_relative_path
governance_parent_design_sha256
target_parent_design_relative_path
target_parent_design_sha256
target_conformance_delta_relative_path
target_conformance_delta_sha256
target_nullability_delta_relative_path
target_nullability_delta_sha256
target_remediation_plan_relative_path
target_remediation_plan_sha256
verifier_relative_path
verifier_source_sha256
receipt_root_relative_path
receipt_run_id
manifest_sha256
summary_sha256
review_sha256
request_journal_sha256
verifier_observed_rc
verifier_expected_rc
strict_loader_observed_rc
strict_loader_expected_rc
v1_behavioral_oracle_comparison_sha256
correction_supplement_relative_path
correction_supplement_sha256
evidence_status
governance_rule17_v2_positive
```

Every value equals Design or independently captured output. `evidence_status` is exactly `candidate_pre_receipt_closure_audit`; `governance_rule17_v2_positive` is exactly `false`. The executor writes this only after Steps 1-2 pass; the verifier never consumes/writes it. A stdlib comparator recomputes all candidate fields. A disposable `review_CN.md` mutation with canonical manifest rebuild must be rejected by this comparator on `review_sha256`, even if structural verifier passes the content-only copy. Candidate evidence must never be named, interpreted, or routed as final closure evidence.

**Step 4: Execute isolated real-root-derived mutation matrix.**

For each probe use `/tmp/stage1_5j_a_receipt_v2_*`. The source root is never writable. Copy/reflink every mutated file before changing it; untouched raw files may be hard-linked only after recording their hashes and must remain unmodified. Rebuild only manifest entries necessary to expose semantic gate. Remove copy after recording result.

| Case ID | One mutation | Expected result |
| --- | --- | --- |
| `v2_approved_design_path` | Change only `approved_design.relative_path`; rebuild summary entry. | `rc=1`, authority-chain diagnostic. |
| `v2_approved_design_sha` | Change only `approved_design.sha256`; rebuild summary entry. | `rc=1`, authority-chain diagnostic. |
| `v2_root_prefixed_response_path` | Change one terminal/projection `raw/...` to `<manifest.root_relative_path>/raw/...`; rebuild entries. | `rc=1`, receipt-relative path diagnostic. |
| `v2_nonmanifest_response_path` | Change terminal/projection to safe but unlisted `raw/...`; rebuild entries. | `rc=1`, manifest-member diagnostic. |
| `v2_nonpersisted_nullability` | Change only `post_launch_row_count: null -> 0`; rebuild summary entry. | `rc=1`, nullability diagnostic. |
| `v2_extra_file` | Add one unlisted regular file. | `rc=1`, sealed-tree diagnostic. |
| `v2_disallowed_manifest_path` | Change one member to grammar-disallowed path and add matching isolated file. | `rc=1`, manifest-path diagnostic. |
| `v2_ancestor_symlink` | Create ancestor symlink in disposable tree only. | `rc=1`, symlink diagnostic. |
| `v2_descendant_symlink` | Replace listed descendant file/directory with symlink. | `rc=1`, symlink diagnostic. |
| `v2_authority_flag_true` | Change one authority flag false to true; rebuild summary entry. | `rc=1`, flag diagnostic. |
| `v2_manifest_hash_mismatch` | Mutate listed member without manifest rebuild. | `rc=1`, hash/byte diagnostic. |
| `v2_external_review_identity` | Change `review_CN.md`, rebuild manifest entry, run external comparator. | comparator rejects review SHA mismatch. |

Matrix records case ID, copy strategy, mutated paths, manifest rebuild flag, verifier/comparator RC, expected class, observed diagnostic SHA, cleanup result, and revalidated source-root hashes. The bounded real-root matrix supplements rather than substitutes for the Task 1 full inherited mutation matrix. Mismatch: `STOP=governance_v2_real_root_probe_failed`.

**Step 5: Prove failure/restart is no-op.**

After malformed disposable copy returns nonzero, rerun v2 on untouched real root. Expected `rc=0`, same root inventory. Verifier owns no lock, staging, cache, marker, or publication state; any real-root write is P0.

---

### Task 5: Static Gates, Scope Proof, And Safety Boundary

**Invariants:** `INV-GSI-V2-05`, `INV-GSI-V2-06`, `INV-GSI-V2-07`.

**Files:** read-only verification of allowed changed paths and evidence.

**Step 1: Tests and Ruff.**

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  tests/scripts/governance/test_verify_artifact_schema.py
.venv/bin/ruff check \
  scripts/governance/verify_artifact_schema.py \
  tests/scripts/governance/test_verify_artifact_schema.py
```

Expected both `rc=0`.

**Step 2: Safety and forbidden behavior.**

```bash
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from configs import base
assert base.RISK_LIVE_TRADING_ENABLED is False
PY
if rg -n '(^|[^[:alnum:]_])(subprocess|os\.system|importlib|runpy|exec|eval|compile|__import__)([^[:alnum:]_]|$)' \
  scripts/governance/verify_artifact_schema.py; then
  exit 1
else
  test "$?" -eq 1
fi
```

Expected L0 assertion `rc=0`; the absence check must return `rg_rc=1` and be converted to command success only by the explicit branch above. Use the AST test as the authoritative absence proof. Confirm verifier contains no import/reference to `src`, `configs`, J-A module paths, test source, `.git`, or network client.

**Step 3: Formatting and scanner.**

```bash
git diff --check bfe3e97fd39adfa40aab8d64c5fb01c3b093aa9a
git diff --cached --check bfe3e97fd39adfa40aab8d64c5fb01c3b093aa9a
git diff --check
python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha bfe3e97fd39adfa40aab8d64c5fb01c3b093aa9a
scanner_rc=$?
printf 'scanner_rc=%s\n' "$scanner_rc"
test "$scanner_rc" -eq 0
```

Record actual `scanner_rc`. Expected all `rc=0`; scanner warning needs explicit evidence disposition, nonzero is blocker.

**Step 4: Authority, ownership, scope, and index proof.**

Recompute and validate every `execution_authority.json` field, the copied implementation-authorization text/SHA, and the canonical scope-file SHA before any review handoff. Compare `git status --short --untracked-files=all` to the Task 0 ledger. For every pre-existing tracked-dirty and untracked path, recompute `file_type`, `byte_count`, and `sha256` (or recursive inventory hash) and require exact equality with the ledger. Require the saved pre-execution binary diff artifacts and their sidecars to retain their recorded bytes; they preserve the original diff, while allowed source/test edits may legitimately change the live diff. Only two source/test paths and evidence directory may be task-induced. Pre-existing J-B/v2 Design/Plan bytes must match ledger. Require `git diff --cached --quiet` returns `0`. Extra task-induced file, authority mismatch, or pre-existing-byte mismatch is `STOP=governance_v2_scope_violation`.

---

### Task 6: Independent Code Review

**Invariants:** all `INV-GSI-V2-*`.

**Files:**
- Create: `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/task6_review_input_snapshot.json`
- Create: `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/task6_code_review_receipt.md`
- Create: SHA-256 sidecars.

**Step 1: Bind review input.**

Snapshot must include approved v2 Design/Plan SHA, execution-authority/scope/authorization hashes, Task 0 ownership/topology facts, allowed-path diff, pre/post oracle/comparison hashes, frozen inherited-case cardinality and empty exclusion table, scanner RC, verifier SHA, v2 candidate/transcript hashes, strict-loader transcript SHA, mutation matrices SHA, and four real-root hashes.

Reviewer independently validates the implementation authorization packet; re-hashes all pre-existing ownership-ledger paths and diff artifacts; reruns the create-once harness at its recorded SHA; verifies v1 corpus equality; verifies frozen inherited-case IDs/cardinality and `exclusion_replacement_table=[]`; inspects exact v2 authority literals against Design §4.1; verifies explicit dispatch; exact v2 authority/path/legacy behavior; no target import/`.git`/subprocess/network/write in verifier; immutable root/no-write proof; single-mutation isolation; candidate comparator including rebuilt-manifest review mutation; L0/scope/index/scanner evidence. OPEN P0/P1: `STOP=governance_v2_code_review_open_findings`.

### Task 7: Independent Completion Audit

Only after a closed Task 6 receipt invoke `.agent/skills/audit-plan-completion/SKILL.md`. Auditor independently recomputes Plan/Design/source/root/evidence hashes; revalidates the separate implementation authorization, scope artifact, and execution-authority record; re-hashes pre-existing ledger paths and binary diff evidence; reruns the frozen harness at its recorded SHA; mechanically checks inherited-case cardinality and `exclusion_replacement_table=[]`; independently compares every exact v2 authority source literal to Design §4.1; runs v1/v2 real-root paths; verifies oracle comparison and sidecars; checks topology/scope/index; runs scanner with actual RC; and invokes public J-A strict loader separately.

Strongest permitted result: `COMPLETE_PRE_NETWORK_GOVERNANCE_V2_IMPLEMENTATION`. Candidate evidence remains non-authoritative and `governance_rule17_v2_positive=false`. This result does not authorize commit, push, deployment, SSH, network, receipt generation, J-B consumption, alpha/replay/signal/paper/live/execution use, or receipt mutation.

### Task 8: Independent Receipt Closure Audit

**Invariants:** `INV-GSI-V2-02`, `INV-GSI-V2-03`, `INV-GSI-V2-05`, `INV-GSI-V2-06`, `INV-GSI-V2-07`.

**Owner and files:** An independent Receipt Closure Auditor, not the executor or Completion Auditor, may create `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/v2_receipt_closure_evidence.json` and its SHA-256 sidecar.

After Task 7 reports `COMPLETE_PRE_NETWORK_GOVERNANCE_V2_IMPLEMENTATION`, the independent auditor must reread immutable replacement-root bytes, rerun the J-A public strict loader and exact reviewed v2 verifier, validate the separate implementation-authorization packet, recompute exact v2 authority literals, revalidate the candidate/transcript/matrix hashes, and compare the root/run/four top-level hashes to approved Design §4.1. Candidate evidence is comparison input only: every final field is projected from the auditor's own recomputation and must not become authoritative by copying candidate values.

The final `v2_receipt_closure_evidence.json` must contain exactly these keys, with no missing or extra key:

```text
profile_id
profile_contract_version
governance_profile_design_delta_relative_path
governance_profile_design_delta_sha256
governance_parent_design_relative_path
governance_parent_design_sha256
target_parent_design_relative_path
target_parent_design_sha256
target_conformance_delta_relative_path
target_conformance_delta_sha256
target_nullability_delta_relative_path
target_nullability_delta_sha256
target_remediation_plan_relative_path
target_remediation_plan_sha256
verifier_relative_path
verifier_source_sha256
receipt_root_relative_path
receipt_run_id
manifest_sha256
summary_sha256
review_sha256
request_journal_sha256
verifier_observed_rc
verifier_expected_rc
strict_loader_observed_rc
strict_loader_expected_rc
v1_behavioral_oracle_comparison_sha256
correction_supplement_relative_path
correction_supplement_sha256
evidence_status
governance_rule17_v2_positive
```

It is the same exact key set as `v2_receipt_closure_candidate.json`. The final record differs only by the two independently audited state values: `evidence_status="receipt_closure_audited_positive"` and `governance_rule17_v2_positive=true`; every other field must equal the auditor's own approved-Design, verified-source, or observed-root projection. The projection is mechanical: `profile_id` is the exact v2 literal; `profile_contract_version` is integer `2`; every `*_relative_path` is the exact approved relative-path string; every `*_sha256` is a lowercase 64-hex string independently rehashed from its named source; `receipt_run_id` equals the verified root basename; all four receipt hashes are rehashed from the root; all four RC fields are integer `0`; and the two state fields have only the exact values above. Its bytes must be exactly UTF-8 without BOM, `json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)` followed by exactly one `\n`. Its sidecar must be exactly `<64-lowercase-hex><two ASCII spaces>v2_receipt_closure_evidence.json\n`.

Before publication, the auditor must parse and re-encode the planned bytes, recompute SHA-256, and construct the exact sidecar. After writing, it must reread the final JSON and sidecar, repeat the canonical-byte comparison and SHA-256 calculation, and validate the sidecar grammar/name/hash. Only if every independent check and this self-verification pass may it retain the final-positive artifact. Any missing/extra field, wrong type/value/enum, noncanonical byte, sidecar mismatch, or hash mismatch is `STOP=governance_v2_receipt_identity_evidence_mismatch`: do not retain a final-positive artifact and keep `governance_rule17_v2_positive=false` in all pre-existing candidate evidence. This audit neither modifies the root nor grants downstream, network, alpha, replay, paper/live, or execution authority.

## 5. Completion Criteria

Ready for independent Completion Audit only when:

1. Task 0 validates the separate implementation authorization, canonical allowed scope, execution-authority record, worktree ownership, topology classification, v1 source/test bytes, correction evidence, root hashes, create-once harness, frozen inherited mutation contract, and v1 oracle before edits.
2. v2 explicit profile/version passes frozen replacement root with receipt-relative `raw/...` paths.
3. Full v1 corpus is mechanically equal before/after v2 source edit using the same Task 0 harness bytes, and the full frozen inherited matrix replays under v2 with exact ordered IDs/cardinality and `exclusion_replacement_table=[]`.
4. v1 legacy remains nullability failure; v2 legacy remains authority/profile failure.
5. Every Task 4 mutation fails at intended gate in disposable copies; no real root changed.
6. Candidate evidence/transcripts bind Design chain, verifier SHA, profile/version, root/run, four hashes, v2/strict-loader results, v1 comparison, and correction supplement, while retaining `governance_rule17_v2_positive=false`.
7. Target pytest, Ruff, whitespace, scanner actual RC, L0, authority/ownership/topology/scope/index gates all pass.
8. Independent code review has no OPEN P0/P1 and independent Completion Audit is not skipped.

Final Rule 17 v2-positive closure is not an executor completion criterion. It exists only after Task 8 independently writes canonical `v2_receipt_closure_evidence.json` and sidecar with `governance_rule17_v2_positive=true`.

## 6. Stop And Escalation Routing

| Condition | Required route |
| --- | --- |
| Authority/root/supplement/Plan/Design byte mismatch | `BLOCKED_SPEC_DRIFT`; return to Design/authority review. |
| Separate implementation authorization/scope/authority-record missing, malformed, or mismatched | `BLOCKED_SPEC_DRIFT`; do not create execution evidence or edit source/test. |
| Existing verifier/test differs before Task 1, or frozen v1 behavior cannot reproduce | `BLOCKED_SCOPE_DRIFT`; do not rebaseline. |
| Topology preflight finds an incompatible runtime consumer outside the whitelist | `BLOCKED_SCOPE_DRIFT`; do not expand scope ad hoc. |
| Pre-existing tracked-dirty/untracked path, binary diff, or ownership-ledger bytes change | `BLOCKED_SCOPE_DRIFT`; preserve evidence and do not overwrite user bytes. |
| Frozen inherited mutation IDs/cardinality differ, an exclusion/replacement is required, or the create-once harness SHA changes | `BLOCKED_SPEC_DRIFT`; do not weaken the matrix or replace the oracle. |
| v2 requires modifying J-A, receipt, config, Design/Plan, or another unlisted path | `BLOCKED_SCOPE_DRIFT` or `BLOCKED_SPEC_DRIFT` under L1 Rule 16. |
| v2 violates approved contract inside allowed code/test scope | `BLOCKED_IMPLEMENTATION_DEFECT`; repair only after RED evidence. |
| Executor or Completion Auditor writes final `v2_receipt_closure_evidence.json` | `BLOCKED_SCOPE_DRIFT`; preserve candidate evidence and route only to independent Receipt Closure Audit. |
| Real-root write, network access, runtime receipt production, J-B invocation, or risk authority change | stop immediately; preserve evidence and classify scope/safety violation. |

## 7. Explicit Non-Authorization

This Plan is a document only until independently reviewed and explicitly approved by the user. A future implementation approval permits only bounded governance verifier/test/evidence work above. It never authorizes commit, push, deployment, SSH, network, data collection, receipt generation, J-B rebind/consumption, alpha conclusion, signal, replay, paper/live trading, or execution.
