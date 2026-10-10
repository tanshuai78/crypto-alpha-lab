# Governance Cross-Boundary Artifact Schema Integrity Implementation Plan

> **For Codex:** 实施时必须逐任务执行；先完成对应 RED 测试与门禁，再写最小生产代码。未经 Plan Review 为 `RECOMMEND_APPROVE` 且用户明确批准本 Plan，不得执行任何任务。

**状态:** `draft_for_independent_review`
**Goal:** 在项目级建立跨信任边界持久化产物的独立只读契约验证器 CLI（`scripts/governance/verify_artifact_schema.py`），内置首个冻结 profile `stage1_5j_a_receipt_v1`，并在 L1 规范、评审审计技能与 Prompt 库中建立 Rule 17 治理闭环。

**Architecture:** 严格遵循只读与 stdlib-only 约束，不构建通用 schema 引擎或动态插件框架。CLI 仅接受 `--profile stage1_5j_a_receipt_v1` 与项目相对路径 `--artifact-root`，独立验证 sealed-tree 成员与哈希、canonical JSON 规范、完整嵌套 summary 结构、journal 状态机与 request_records 全量投影。真实已知的瑕疵收据（20261008T160500Z）作为不可变负例验证，断言其返回 `rc=1`。

**Tech Stack:** Python 3 standard library (`argparse`, `json`, `hashlib`, `os`, `pathlib`, `re`, `sys`), pytest, Ruff, Git.

---

## 1. Approved Design Binding

| Item | Exact value |
| --- | --- |
| Approved Governance Design | `docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md` |
| Approved Governance Design SHA-256 | `73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4` |
| Target J-A Design | `docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md` |
| Target J-A Design SHA-256 | `b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a` |
| Target J-A Delta Design | `docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md` |
| Target J-A Delta Design SHA-256 | `6063ed103d31fcf6c60ad8106eb13650f54b74272182c78bf8e81f9ba48a91ac` |
| Planning BASE_SHA | `c617899132e49661761aa8bdff75816c1dc24d1d` |
| Immutable Negative Reference Root | `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z` |

### 1.1 Frozen J-A Pre-Network Closure Prerequisite

Governance implementation is downstream of the completed J-A R1 pre-network closure. Task 0 must mechanically verify this exact package before it creates any Governance evidence or edits a file. These are authority facts, not inputs that an executor may update from current bytes:

| Item | Exact value |
| --- | --- |
| J-A R1 Plan | `docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan-r1_CN.md` |
| J-A R1 Plan SHA-256 | `b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82` |
| J-A Task 5 receipt | `.git/plan-execution/stage1_5j_a/b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82/evidence/task5_code_review_receipt.md` |
| J-A Task 5 receipt SHA-256 | `009ac8ab8aec87a260746259d0a86f525603f5cfcad6569ab736607eec7e7d85` |
| J-A Completion Audit | `.git/plan-execution/stage1_5j_a/b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82/evidence/completion_audit_report.md` |
| J-A Completion Audit SHA-256 | `d6e79bc6be693fc49507503b4113e630349aaf8c3c1113400816a2847d2a3320` |
| J-A audited Core SHA-256 | `250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18` |
| J-A audited research-test SHA-256 | `16da9fd34af2bd85bc3ef4db248bd4cbe6f6fd1ade47f0f132cf013e899b9f95` |
| J-A audited CLI-test SHA-256 | `9185581c5a13fd4d0af1e235e3420093aa94eeafffcd90ba6a085adc5b9ffe83` |
| Required completion verdict | `COMPLETE_PRE_NETWORK_IMPLEMENTATION` |

Task 0 must verify both receipt/audit sidecars from repository root, recompute every listed source/document SHA-256, and require the exact verdict. Any absence, sidecar failure, SHA mismatch, or verdict mismatch is `STOP=J_A_PRENETWORK_CLOSURE_DRIFT`. It must not substitute later bytes, a report summary, or a new J-A audit.

本 Plan 不构成 implementation、commit、push、network、receipt-generation、replay、signal、paper trading、live trading、execution 或 J-B upstream consumption 授权。

---

## 2. Allowed Change Scope

```markdown
## Allowed Change Scope

Allowed implementation paths:
- AGENTS.md
- .agent/rules/L1_Engineering_Process.md
- .agent/skills/reviewing-implementation-plans/SKILL.md
- .agent/skills/audit-plan-completion/SKILL.md
- docs/production_artifacts/tri_agent_prompt_library_CN.md
- scripts/governance/verify_artifact_schema.py

Allowed verification paths:
- tests/scripts/governance/test_verify_artifact_schema.py

Allowed documentation paths:
- none  # Plan 自身与已批准 Design 均为不可变只读凭证

Allowed generated/runtime artifacts:
- .git/plan-execution/governance_artifact_schema/<PLAN_SHA>/**

Affected but unchanged:
- src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py
  - compatibility evidence: tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py
- scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py
  - compatibility evidence: tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
- configs/base.py
  - compatibility evidence: python3 -c "from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False"

Forbidden:
- Any mutation outside the allowed paths
- Modifying J-A/J-B source, receipt, fixture, or network authorization files
- Modifying configs/base.py or financial safety thresholds
- Importing target producer/loader/CLI/test modules into scripts/governance/
- Using non-stdlib libraries, subprocess, runpy, importlib, or dynamic execution
- Network requests, receipt creation, or writing any files to artifact directories
```

---

## 3. Design Invariant Mapping

| Invariant ID | Description | Enforcing Task |
| --- | --- | --- |
| `INV-GSI-01` | Verifier acceptance logic derives only from literal profile constants plus validated artifact-root bytes; cannot import/execute target code. | Task 3 (AST tests), Task 4 (stdlib implementation) |
| `INV-GSI-02` | Profile authority tuple immutability and explicit versioning (`stage1_5j_a_receipt_v1`). | Task 3 (Profile tests), Task 4 (Constants lockdown) |
| `INV-GSI-03` | Enforce parent-Design structural summary, journal, and sealed-tree contract independently. | Task 3 (Structural tests), Task 4 (Validation logic) |
| `INV-GSI-04` | Reject noncanonical JSON, symlinks, path traversals, extra/missing files, manifest order/alias errors, and ID mismatches. | Task 3 (Negative mutation tests), Task 4 (Tree validation) |
| `INV-GSI-05` | Markdown validated only by sealed-tree membership, byte count, and SHA-256. | Task 3 (Review file test), Task 4 (Manifest checker) |
| `INV-GSI-06` | Profile pass is additional structural evidence only; cannot override failed stage loader, authority verifier, or receipt closure audit. | Task 1 (Rule 17), Task 2 (Skills & Prompts) |
| `INV-GSI-07` | Plan review, Completion/Closure Audit, and downstream admission require named profile identity, verifier SHA, and real-root evidence. | Task 1 (Rule 17), Task 2 (Skills & Prompts) |
| `INV-GSI-08` | No governance change enables network, receipt generation, replay, signal, paper/live trading, execution, Alpha, or J-B consumption. | Task 0, Task 4 (Strict read-only), Task 5 |

---

## 4. Implementation Tasks

### Task 0: Authority Baseline, Scope Freeze & Plan Hash Verification

**Files:**
- Read-only check: `docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md`
- Runtime evidence creation: `.git/plan-execution/governance_artifact_schema/<PLAN_SHA>/`

- [ ] **Step 1: Verify exact user Plan approval before any baseline or edit.**
  - Parse the user approval sentence for this exact relative Plan path and a 64-lower-hex `APPROVED_PLAN_SHA256`; recompute this Plan's bytes and require equality.
  - Require `git rev-parse HEAD == c617899132e49661761aa8bdff75816c1dc24d1d`. There is no alternative commit, implicit authorization exception, rebaseline, or natural-language override.
  - Require `git diff --cached` to be empty. Require that `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/` does not exist before Task 0 finishes.
  - Any mismatch is `STOP=governance_artifact_schema_execution_authority_mismatch`; do not create an authority/evidence directory or edit a file.

- [ ] **Step 2: Verify approved Governance Design and the frozen J-A closure prerequisite.**
  - Recompute the approved Governance Design SHA-256 and require `73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4`.
  - Verify every §1.1 J-A path exists; run `shasum -a 256 -c` for each J-A receipt/audit sidecar from repository root; recompute the R1 Plan, Core, research-test, and CLI-test bytes; and require the exact completion verdict `COMPLETE_PRE_NETWORK_IMPLEMENTATION` in the frozen completion audit bytes.
  - Any J-A prerequisite mismatch is exactly `STOP=J_A_PRENETWORK_CLOSURE_DRIFT`; no Governance implementation may proceed.

- [ ] **Step 3: Create once the Governance authority/evidence packet and freeze pre-existing worktree ownership.**
  - Only after Steps 1-2 pass, create `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/` with `implementation_authorization.txt`, its SHA-256 sidecar, `base_sha`, and canonical `execution_authority.json` plus sidecar. The authority JSON binds the approved Governance Design path/SHA, exact Plan path/SHA, `c617899132e49661761aa8bdff75816c1dc24d1d`, and the §1.1 J-A closure tuple.
  - Create canonical `evidence/pre_execution_worktree_ledger.json` plus sidecar. For every pre-existing modified tracked or untracked path, record exactly `path`, `path_type`, `byte_count`, and `sha256`; record the staged-name-only result separately. Do not merely record a pathname. The clean J-A Core and tests are bound by §1.1; if any of those paths are dirty or untracked at Task 0, they must additionally appear in this ledger with exact bytes.
  - At Task 5 and Completion Audit, compare the final worktree against this ledger: task-induced paths must be whitelisted; ledger paths must retain exact bytes; any foreign or drifted path is `STOP=governance_artifact_schema_scope_or_baseline_drift`.

---

### Task 1: Rule 17 Specification in Engineering Process Rules and Project AGENTS.md

**Files:**
- Modify: `.agent/rules/L1_Engineering_Process.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Produces: Project-wide Rule 17 definition governing cross-boundary persistent artifact schema integrity.

- [ ] **Step 1: Add Rule 17 to `.agent/rules/L1_Engineering_Process.md`**
  Append verbatim as specified in Design §3.2:
  ```markdown
  17. **Cross-Boundary Artifact Schema Integrity**: For every newly created or revised persistent artifact that crosses a producer/consumer, process, lifecycle, or downstream-stage trust boundary, its approved Design/Plan MUST name an immutable profile authority tuple, exact key sets, legal enum literals, conditional field combinations, sealed-tree/path rules, and deterministic byte/projection obligations. A producer and its domain loader MUST each enforce their contract. Completion and receipt-closure audits MUST additionally run an independently implemented artifact verifier whose acceptance logic derives only from its literal approved profile constants and artifact bytes, not from the target producer or loader. The audit record MUST bind the exact approved Design SHA, verifier source SHA, profile ID/version and receipt identity. Internal pure-logic unit tests remain exempt when they prove no cross-boundary artifact claim.
  ```

- [ ] **Step 2: Synchronize Rule 17 in `AGENTS.md`**
  Add Rule 17 under Section `L1 Engineering Process Rules` maintaining numbering alignment with `L1_Engineering_Process.md`.

- [ ] **Step 3: Verify Rule 17 Text Alignment**
  - Command: `git diff --check .agent/rules/L1_Engineering_Process.md AGENTS.md`
  - Expected: Clean exit (rc=0), whitespace valid.

---

### Task 2: Updating Review Skill, Audit Skill, and Prompt Library

**Files:**
- Modify: `.agent/skills/reviewing-implementation-plans/SKILL.md`
- Modify: `.agent/skills/audit-plan-completion/SKILL.md`
- Modify: `docs/production_artifacts/tri_agent_prompt_library_CN.md`

**Interfaces:**
- Produces: Enhanced review checklist, Tier 3 artifact verifier audit step, and prompt instructions requiring explicit profile authority tuples.

- [ ] **Step 1: Update `.agent/skills/reviewing-implementation-plans/SKILL.md`**
  Under Section `Core Review Flow`, add subsection for `Cross-Boundary Artifact Schema Integrity Gate`:
  - When an implementation plan creates or mutates a persistent artifact crossing trust boundaries:
    - Must declare an immutable external profile authority tuple: `(profile_id, profile_contract_version, governance_design_relative_path, governance_design_sha256, target_stage_design_relative_path, target_stage_design_sha256, target_stage_delta_relative_path, target_stage_delta_sha256, verifier_relative_path, verifier_source_sha256, receipt_root_relative_path, manifest_sha256, summary_sha256, review_sha256, request_journal_sha256)`.
    - Must specify exact key sets, enums, nullability rules, and sealed manifest bindings.
    - Must require independent verifier execution in Task checklist.

- [ ] **Step 2: Update `.agent/skills/audit-plan-completion/SKILL.md`**
  Under Section `Evidence Authority Hierarchy` and Section `Audit Flow`:
  - In Tier 3 / Cross-boundary verification: require executing `scripts/governance/verify_artifact_schema.py --profile <profile_id> --artifact-root <relative_root>` against sealed production root.
  - Explicitly mandate recording `profile_id`, `verifier_source_sha256`, and target receipt hashes in completion audit report.
  - Affirm that verifier pass alone is structural evidence and does not replace the stage domain strict loader or receipt closure audit.

- [ ] **Step 3: Update `docs/production_artifacts/tri_agent_prompt_library_CN.md`**
  - In `A-Completion-Audit` and `A-Completion-Closure`: add requirement to run `verify_artifact_schema.py` whenever auditing an artifact crossing stage boundaries.
  - In `B-Design-First` and `B-Design-Closure`: add verification of Rule 17 profile authority tuple and schema boundaries.

- [ ] **Step 4: Verify Formatting and Diff**
  - Command: `git diff --check .agent/skills/ docs/production_artifacts/`
  - Expected: Clean exit (rc=0).

---

### Task 3: TDD RED Phase — Governance Artifact Verifier Test Suite

**Files:**
- Create: `tests/scripts/governance/test_verify_artifact_schema.py`

**Interfaces:**
- Consumes: `scripts/governance/verify_artifact_schema.py` (CLI entry point and core validation functions)
- Produces: Test coverage for CLI invocation, AST import restrictions, profile contract enforcement, and negative probes.

- [ ] **Step 1: Write Failing Tests in `tests/scripts/governance/test_verify_artifact_schema.py`**
  Do not create `tests/scripts/governance/__init__.py` or any package scaffolding. The verifier is a standalone CLI; tests invoke its exact file entry point without adding a package framework.

  Include tests covering:
  1. `test_cli_argument_validation`:
     - Missing arguments -> rc=2
     - Unsupported profile (e.g. `--profile invalid_profile`) -> rc=2
     - Absolute path (e.g. `--artifact-root /tmp/...`) -> rc=2
     - Parent directory traversal (e.g. `--artifact-root ../foo`) -> rc=2
     - Non-existent path -> rc=2
  2. `test_ast_strict_stdlib_isolation`:
     - Parse `scripts/governance/verify_artifact_schema.py` with `ast`.
     - Assert all imported modules are in Python stdlib (`sys`, `os`, `json`, `pathlib`, `re`, `argparse`, `hashlib`).
     - Assert no imports of `src.*`, `configs.*`, `tests.*`.
     - Assert no calls to `subprocess`, `os.system`, `importlib`, `runpy`, `exec`, `eval`, `compile`, dynamic `__import__`.
  3. `test_stage1_5j_a_receipt_v1_minimal_valid_fixture`:
     - Construct a minimal conformant sealed receipt in `tmp_path` satisfying all Section 5.1-5.4 contracts.
     - Execute verifier -> rc=0.
  4. `test_stage1_5j_a_receipt_v1_single_mutation_negatives`:
     - Start every probe from the declared minimal valid local tree. Apply exactly one semantic mutation per case. When a mutation changes a sealed artifact, regenerate only the derived manifest entry/canonical manifest needed to reach the intended semantic gate; this regeneration is witness preparation, not a second semantic mutation.
     - Each row below is mandatory and must assert `rc=1` plus the named contract-class diagnostic. A compressed parametrized test is permitted only when its case table names every row and preserves one mutation per invocation.

       | Contract class | Required one-mutation negatives |
       | --- | --- |
       | CLI/profile/read-only | unknown profile; wrong profile version; absolute, empty-component, `.` and `..` root argument; nonexistent root; input-tree before/after byte inventory unchanged; verifier source has no `.git` inspection/access. |
       | Canonical JSON | `manifest.json` and `summary.json` each: UTF-8 BOM, missing terminal newline, non-sorted keys, and noncanonical separators. |
       | Manifest identity and entries | manifest schema/run/root mismatch; artifact-entry unknown/missing key; bool/negative `byte_count`; invalid SHA grammar; duplicate entry; unsorted entry; safe-looking alias or unapproved relative grammar; missing listed member; extra regular file; unexpected directory; hash mismatch; byte-count mismatch. |
       | Tree traversal | root symlink, ancestor symlink, descendant directory symlink, and descendant file symlink, each rejected without following it. |
       | Summary envelope | top-level missing key, top-level unknown key, schema-version mismatch, run-ID mismatch, every authority flag independently `True`, and exact `universe_window`, `catalog_scan`, and `authority_packet` field/key/type failures. |
       | Denominator and parent rows | denominator ordering fault; each candidate-status/detail-request conditional mismatch; parent ordering fault; each parent `detail_status` conditional combination; child unknown/missing key and invalid primitive grammar; nonvalidated parent with nonempty children or non-gap-detail state. |
       | Archive rows | archive ordering fault; each of the three `child_state` conditional field combinations; each of four nonpersisted trade fields independently `null -> non-null`; logical-identity unknown/missing key, literal, grammar, and containing-record equality mismatch. |
       | Coverage and decision | each `coverage_inventory` field independently set to bool, negative, or non-integer; each invalid `analysis_state`/`decision` pair. |
       | Journal state machine | intent unknown key and legacy `created_at_utc`; invalid context for all four request kinds; duplicate request ID; non-contiguous/nonpositive ID; terminal before intent; duplicate terminal; dangling intent; and each required terminal sibling state/HTTP-response combination. |
       | Completed projection | independently mutate each projection field (`request_id`, `request_kind`, `url`, `request_state`, `http_status_or_transport_error`, `response_bytes`, `response_relative_path`, `response_sha256`) while preserving a valid journal; each must reject. |

     - The minimal local tree is only a verifier-mechanics fixture. It must never be labeled a J-A receipt, real-root evidence, semantic closure, or downstream admission evidence.
  5. `test_immutable_section_1_negative_reference_root`:
     - Invoke verifier against actual immutable real root: `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z`
     - Assert returns `rc=1`
     - Assert stderr/stdout identifies `post_launch_row_count` expected null, observed 0.

- [ ] **Step 2: Run Pytest to Verify RED Failure**
  - Command: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/scripts/governance/test_verify_artifact_schema.py`
  - Expected output: FAIL (ModuleNotFoundError or FileNotFoundError for `scripts/governance/verify_artifact_schema.py`).

---

### Task 4: TDD GREEN Phase — Implement Governance Artifact Verifier CLI

**Files:**
- Create: `scripts/governance/verify_artifact_schema.py`

**Interfaces:**
- Produces: `verify_artifact_schema.py` executable CLI script.
- Entrypoint: `main(argv=None) -> int` returning 0 on success, 1 on contract violation, 2 on usage error.

- [ ] **Step 1: Implement Core Structure in `scripts/governance/verify_artifact_schema.py`**
  1. CLI Arguments & Path Sanitization:
     - Derive project root from `Path(__file__).resolve().parents[2]`.
     - Reject absolute paths, empty components, and `.` or `..` traversals.
     - Check symlinks using `os.path.islink()` on every lexical path ancestor.
     - Validate `--profile` against supported set `{"stage1_5j_a_receipt_v1"}`.
  2. Profile Constants Definition (§5.1 - §5.3):
     - `SUMMARY_SCHEMA_VERSION`, `MANIFEST_SCHEMA_VERSION`, `RUN_ID_REGEX`, `SHA256_REGEX`.
     - `MANIFEST_EXACT_KEYS`, `MANIFEST_ARTIFACT_EXACT_KEYS`.
     - `SUMMARY_EXACT_KEYS`, `AUTHORITY_FLAG_EXACT_KEYS`.
     - `INTENT_EXACT_KEYS`, `TERMINAL_EXACT_KEYS`, `REQUEST_KINDS`, `TERMINAL_STATES`.
     - Authority metadata strings for Design and Delta bindings.
  3. Manifest & Sealed Tree Verifier:
     - Validate canonical byte encoding of `manifest.json`.
     - Verify exact keys and values.
     - Verify `manifest.artifacts` ordering and completeness (every file on disk accounted for, no extra files or directories, symlinks forbidden).
     - Verify file byte counts and SHA-256 hashes.
  4. Summary Verifier:
     - Validate canonical byte encoding of `summary.json`.
     - Verify exact keys, all 13 authority flags `False`, exact `universe_window`, `catalog_scan`, and `authority_packet`.
     - Verify `catalog_denominator_records` sorting, enum literals, and nullability.
     - Verify `parent_records` sorting, detail statuses, parent states, and child structures.
     - Verify `archive_package_records` sorting, states, and conditional trade field nullability (`archive_request_nonpersisted` requires all four trade fields `None`).
     - Verify `coverage_inventory` counts.
  5. Request Journal & Completed Projection Verifier:
     - Read `request_journal.jsonl` line by line.
     - Verify exact intent and terminal keys and conditional context combinations.
     - Track state machine: 1 intent + 1 terminal per request ID in ascending order.
     - Build completed projection and assert bit-for-bit equality against `summary.request_records`.
  6. Return Code and Diagnostic Output:
     - On any contract failure: print formatted diagnostic with expected constraint vs observed value to `sys.stderr` and exit with `rc=1`.
     - On CLI / argument failure: print error and exit with `rc=2`.
     - On full pass: print success summary and exit with `rc=0`.

- [ ] **Step 2: Run Pytest to Verify GREEN**
  - Command: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/scripts/governance/test_verify_artifact_schema.py`
  - Expected output: PASS (all tests green).

---

### Task 5: Static Quality Gates And Immutable Negative-Reference Evidence

**Files:**
- Read-only verification across all modified/created files.

- [ ] **Step 1: Run Ruff Linter**
  - Command: `.venv/bin/ruff check scripts/governance/verify_artifact_schema.py tests/scripts/governance/test_verify_artifact_schema.py`
  - Expected output: `All checks passed!` (rc=0).

- [ ] **Step 2: Run Git Diff Whitespace Check**
  - Command: `git diff --check`
  - Expected output: Clean exit (rc=0).

- [ ] **Step 3: Run Anti-Shortcut Scanner**
  - Command: `python3 .agent/tools/anti_shortcut_scan.py --base-sha c617899132e49661761aa8bdff75816c1dc24d1d`
  - Capture the actual process exit code in Task 5 evidence; expected `scanner_rc=0`. A narrative scanner summary is not evidence.

- [ ] **Step 4: Verify L0 Financial Safety Invariant**
  - Command: `python3 -c "from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False"`
  - Expected output: Clean exit (rc=0).

- [ ] **Step 5: Verify Negative Reference Root Direct Invocation**
  - Run under `set +e`; record `negative_reference_rc=$?`; restore `set -e`; require `negative_reference_rc == 1`. `rc=0`, `rc=2`, signal termination, or any other code is failure.
  - Require the diagnostic to identify `archive_request_nonpersisted.post_launch_row_count`, expected `null`, observed `0`.
  - Recompute and require these immutable root hashes before invocation: manifest `afce37097f9d7ab0732afe0164cbc918f2d263788fd4b41be674536ba1cee21c`; summary `2cf233c476b4ad43ea8105a274af38cc1fd595e1b22012966ceb656aa68aa7a7`; review `38917ed3014b4e6b758cc3900f67925c4cb942cc73b879c0fa90da0135b219b5`; journal `139453f07072d3f31ad3d398434a12bc7786cda30003bdd0cf7e8f3d23ed5582`.

- [ ] **Step 6: Create external negative-reference verifier evidence.**
  - Create canonical JSON plus a SHA-256 sidecar at `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/negative_reference_verifier_evidence.json`.
  - The record is created by the executor shell after the verifier exits, not by the verifier. It must contain: `profile_id`, `profile_contract_version`, Governance Design path/SHA, target parent Design path/SHA, target J-A Delta path/SHA, `verifier_relative_path`, externally computed `verifier_source_sha256`, negative root relative path, the four frozen root hashes, `observed_rc`, `expected_rc`, exact diagnostic, approved Plan path/SHA, Planning BASE_SHA, and `positive_real_root_evidence="not_applicable_pre_network"`.
  - Record `observed_rc=1` and `expected_rc=1` only after Step 5's exact check passes. The evidence must not label the negative root as positive or substitute the local minimal fixture for real-root evidence.
  - Completion Audit must independently recompute every recorded source/root hash, sidecar, return code, and diagnostic rather than trusting this record.

---

### Task 6: Independent Code Review

- [ ] **Step 1: Prepare review input after all Task 5 gates pass.**
  - Bind the review request to `c617899132e49661761aa8bdff75816c1dc24d1d..HEAD`, the exact approved Plan SHA, Governance Design SHA, Task 0 authority packet, Task 5 negative-reference evidence SHA, actual scanner RC, and the allowed-path diff.
  - The reviewer must independently verify stdlib isolation, no target-code import/source inspection, the complete Task 3 mutation matrix, `rc=1` negative-root semantics, no-write behavior, authority-evidence record, and L0 flags.

- [ ] **Step 2: Require a closed review receipt.**
  - Store `task6_code_review_receipt.md` and its sidecar under `.git/plan-execution/governance_artifact_schema/<APPROVED_PLAN_SHA256>/evidence/`.
  - Any OPEN P0/P1 is `STOP=governance_artifact_schema_code_review_open_findings`; do not route to Completion Audit.

---

## 5. Completion Audit Handoff

Upon completing all tasks:
1. Re-run full test suite and verify 0 regressions across existing test suites (`test_stage1_5j_a_historical_archive_coverage_inventory.py`, `test_run_stage1_5j_a_historical_archive_coverage_inventory.py`).
2. Verify `git status --porcelain` against the Task 0 byte ledger: only whitelist paths may be task-induced; every pre-existing path must retain its exact bytes.
3. Verify `git diff --cached` is empty (no unauthorized staging or commit).
4. Run an independent Completion Audit via `.agent/skills/audit-plan-completion/SKILL.md` only after Task 6 receipt is closed. The auditor must verify Task 0 authority/J-A closure bindings, every Task 3 matrix row, Task 5 actual RCs, external verifier/root evidence, source/receipt hashes, scope/index ledger, and `RISK_LIVE_TRADING_ENABLED is False`.
5. A Completion Audit pass establishes Governance verifier pre-network implementation readiness only. It does not authorize network, receipt generation, replacement-root positive evidence, J-B consumption, paper/live trading, execution, commit, push, deployment, or SSH.
