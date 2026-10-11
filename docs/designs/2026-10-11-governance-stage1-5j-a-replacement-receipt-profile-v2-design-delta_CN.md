# Governance Stage 1.5J-A Replacement Receipt Profile v2 Design Delta

**日期:** 2026-10-11
**状态:** `draft_for_independent_review`
**父级 Governance Design:** `docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md`
**父级 Governance Design SHA-256:** `73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4`
**目的:** 在不修改历史 `stage1_5j_a_receipt_v1` acceptance semantics 的前提下，定义独立的 `stage1_5j_a_receipt_v2` Rule 17 profile，使其可对已封存的 J-A replacement receipt 执行可重现的独立结构验证。

## 1. Confirmed Facts

1. 已提交 Governance verifier 位于 `scripts/governance/verify_artifact_schema.py`，其 SHA-256 为 `0071715439e5fd9f64d9b6e62fe86e027ac8f26f6697873202cd521c52fb8c98`。它只支持 `stage1_5j_a_receipt_v1`，其 contract version 为 `1`。
2. 父级 Governance Design §3.3 冻结 `v1` 的 target identity 为原 J-A Design `b74c306e...` 与首个 J-A conformance remediation Delta `6063ed103...`，并规定任何 acceptance-semantics 变化必须使用新的 profile ID 和版本。
3. 已封存 replacement receipt 的唯一 identity 是：

```text
run_id = stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
root = data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
manifest.json         = b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf
summary.json          = 722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b
review_CN.md          = 1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152
request_journal.jsonl = b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa
```

4. 该 root 的 authority packet 绑定：

```text
parent_j_a_design = docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md
parent_j_a_design_sha256 = b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a
conformance_delta = docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md
conformance_delta_sha256 = 6063ed103d31fcf6c60ad8106eb13650f54b74272182c78bf8e81f9ba48a91ac
nullability_delta = docs/designs/2026-10-09-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-design-delta_CN.md
nullability_delta_sha256 = f427df9435c8b9c8dd2b4b45c24bbbbd595df2c7e8d209f40f6fe2cd13b00f3c
remediation_plan = docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan-r1_CN.md
remediation_plan_sha256 = b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82
```

5. The replacement receipt's persisted `request_journal.jsonl` terminals and `summary.request_records` use receipt-relative values such as `raw/catalog_scan_a/1.json`. They do not prefix these values with `manifest.root_relative_path`.
6. The legacy root `stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z` remains immutable negative evidence. It has `archive_request_nonpersisted.post_launch_row_count=0`, where the parent J-A contract requires `null`.
7. The J-A public strict loader positive-loads the replacement root under its J-A authority packet. This Design does not restate that domain proof as Rule 17 proof.
8. The immutable historical `receipt_closure_audit_report.md` records a Rule 17 `v1` positive invocation using verifier SHA `42e66a08b48f27e20aca31b0d125bbd92459bba6bac148380d17dc881f9398b1`. That SHA differs from the completion-audited `v1` verifier SHA `0071715439e5fd9f64d9b6e62fe86e027ac8f26f6697873202cd521c52fb8c98`.
9. The completion-audited `007171...` `v1` verifier rejects this replacement root before structural success because its `approved_design` is the nullability Delta rather than a frozen `v1` binding. The historical `42e...` result is therefore non-admissible Rule 17 positive evidence, even though the J-A strict-loader result and the four replacement-root hashes remain valid facts.

```text
j_a_domain_receipt_closed = true
governance_rule17_v1_positive = false
governance_rule17_v2_positive = pending
```

## 2. Root Cause And Decision

### 2.1 Root cause

An unapproved local verifier edit attempted to admit the replacement root by extending the historical `v1` approved-design set and accepting both root-prefixed and receipt-relative response paths. That was not a valid repair: it changed profile authority and accepted grammar while retaining `stage1_5j_a_receipt_v1` / version `1`.

### 2.2 Decision

1. Preserve `stage1_5j_a_receipt_v1` acceptance behavior exactly. The verifier source file will necessarily receive an additional profile, so source bytes cannot remain identical; the pre-v2 `v1` source SHA and a frozen behavioral corpus are the required regression oracle.
2. Define one additional literal profile, `stage1_5j_a_receipt_v2`, with `profile_contract_version=2`. No `v1` fallback, alias, dynamic Design lookup, or runtime-configured profile is permitted.
3. `v2` binds this Design Delta, the parent Governance Design, the R1 remediation Plan, and both named J-A remediation Deltas as an ordered authority chain. It does not treat an arbitrary Design or Plan with a valid SHA as admissible.
4. `v2` defines one response-path grammar: a persisted response path is the exact receipt-relative manifest member path, beginning with `raw/`. A `manifest.root_relative_path` prefix is invalid for this profile.
5. The replacement root remains immutable. The later verifier implementation may read it but must not create, rename, delete, repair, rewrite, or re-publish any file beneath it.

## 3. Scope And Non-Goals

### 3.1 In scope

- A new immutable Governance verifier profile definition for the one replacement J-A receipt lineage.
- Independent structural validation of that profile's authority chain, sealed-tree identity, receipt-relative response paths, and inherited J-A v1 structural contract.
- Exact positive and negative evidence requirements for a later Governance implementation Plan and Receipt Closure Audit addendum.

### 3.2 Explicit non-goals

- Changing `stage1_5j_a_receipt_v1`, its version, its constants, its tests, or its historical acceptance/rejection behavior.
- Changing J-A producer, strict loader, CLI, parser, config, network authorization, request journal, coverage reducer, output root, manifest, summary, review, or raw files.
- Re-running network collection, generating a new receipt, replaying data, or adding a compatibility parser.
- Authorizing J-B consumption, alpha interpretation, price-response measurement, paper trading, live trading, execution, commit, push, deployment, or SSH.
- Turning a Governance verifier pass into a substitute for J-A strict-loader positive load or J-A Receipt Closure Audit.

## 4. Trust Boundary And Profile Authority

### 4.1 v2 profile authority and external receipt-evidence tuple

The later Plan and audit evidence must bind this exact tuple. The verifier uses literal constants only for profile-level authority identities and must not read a Design file to discover them. Receipt identity and artifact hashes are recorded by the independent Completion/Closure Audit, not hardcoded as verifier acceptance constants: otherwise a one-field semantic mutation whose isolated manifest is canonically rebuilt could never reach its intended semantic gate.

```text
profile_id = stage1_5j_a_receipt_v2
profile_contract_version = 2

governance_profile_design_delta_relative_path = docs/designs/2026-10-11-governance-stage1-5j-a-replacement-receipt-profile-v2-design-delta_CN.md
governance_profile_design_delta_sha256 = exact SHA-256 of the user-approved immutable Design Delta bytes
governance_parent_design_relative_path = docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md
governance_parent_design_sha256 = 73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4

target_parent_design_relative_path = docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md
target_parent_design_sha256 = b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a
target_conformance_delta_relative_path = docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md
target_conformance_delta_sha256 = 6063ed103d31fcf6c60ad8106eb13650f54b74272182c78bf8e81f9ba48a91ac
target_nullability_delta_relative_path = docs/designs/2026-10-09-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-design-delta_CN.md
target_nullability_delta_sha256 = f427df9435c8b9c8dd2b4b45c24bbbbd595df2c7e8d209f40f6fe2cd13b00f3c
target_remediation_plan_relative_path = docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan-r1_CN.md
target_remediation_plan_sha256 = b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82

receipt_root_relative_path = data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
receipt_run_id = stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
manifest_sha256 = b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf
summary_sha256 = 722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b
review_sha256 = 1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152
request_journal_sha256 = b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa
```

The receipt lines above are mandatory external Closure Audit evidence for this one positive root. The `v2` verifier instead validates that its argument exactly equals the root's manifest `root_relative_path` and validates the manifest's own sealed-tree hashes. `verifier_relative_path` and `verifier_source_sha256` are also recorded only after the future implementation's exact bytes are independently reviewed. The verifier must never attest its own source SHA from mutable in-file data.

The external Closure Audit must write canonical `v2_receipt_closure_evidence.json` plus a SHA-256 sidecar beneath the future Plan evidence directory. It binds every line of this tuple, the observed `v2` result, and the independent J-A strict-loader result. It is the mechanical identity gate for the four receipt hashes; that gate is separate from the verifier's structural gates.

### 4.2 Producer, verifier, consumer matrix

| Role | Required behavior | Prohibited behavior |
| --- | --- | --- |
| J-A producer | Already published the sealed replacement root under its own one-time authority. | Re-run, repair, mutate, or write the root for Governance. |
| J-A strict loader | Remains the sole domain semantic loader and must positive-load independently. | Being imported, invoked, or inspected by the Governance verifier. |
| Governance v2 verifier | Reads only literal `v2` constants and files below a validated project-relative root. | Importing target code, reading `.git`, network, subprocesses, writes, fallback to `v1`, or dynamic profile discovery. |
| Receipt Closure Auditor | Runs the strict loader and independent `v2` verifier against the immutable root. | Treating either result alone as full closure. |
| J-B consumer | Remains blocked pending its own identity/projection/cardinality Design Delta. | Reading this root or inferring research/execution authority. |

## 5. `stage1_5j_a_receipt_v2` Structural Contract

### 5.1 Inherited structural contract

Except for the explicit identity and response-path rules below, `v2` must independently enforce every exact structural rule of the parent Governance Design §5 for the J-A v1 receipt family: project-relative root validation, no symlinks, sealed manifest tree, exact JSON/JSONL keys, enums, conditional nullability, deterministic journal projection, authority packet shape, archive-package record states, coverage counts, and authority flags.

For `review_CN.md`, the Governance verifier checks only sealed-tree membership, byte count, and SHA-256. Markdown renderer/projection semantics remain exclusively with the J-A strict loader and Receipt Closure Audit.

This inheritance is a constraint, not a call into `v1` code. The future implementation may share local pure validation helpers only when the helper's behavior is identical for both profiles; it must dispatch from explicit literal profile IDs and must leave `v1` literals and acceptance results unchanged.

### 5.2 Exact authority-chain rule

For the replacement root, `summary.authority_packet.approved_design` must equal exactly:

```json
{
  "relative_path": "docs/designs/2026-10-09-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-design-delta_CN.md",
  "sha256": "f427df9435c8b9c8dd2b4b45c24bbbbd595df2c7e8d209f40f6fe2cd13b00f3c"
}
```

`summary.authority_packet.approved_plan` must equal exactly the R1 path/SHA in §1. The verifier must validate its argument against `manifest.root_relative_path`, manifest hashes against disk bytes, and every profile-authority literal above. The external Closure Audit, rather than verifier self-attestation, compares the observed root, run ID, and four top-level hashes to §4.1. Any authority, manifest, or external-evidence mismatch is fail-closed; no fallback or alias is accepted.

### 5.3 Exact receipt-relative response-path rule

For every `request_terminal` and completed `summary.request_records` entry with `request_state="response_persisted"`:

```text
response_relative_path is a safe POSIX relative path
response_relative_path starts with "raw/"
response_relative_path equals exactly one manifest.artifacts[].relative_path
response_sha256 equals that member's SHA-256
```

`response_relative_path` must not begin with `manifest.root_relative_path + "/"`, `/`, `./`, `../`, or contain an empty, `.` or `..` component. Non-persisted terminals retain the parent J-A fixed `null` response-field combination. The terminal projection and `summary.request_records` must be exact value-for-value equals; a prefix-normalization fallback is forbidden.

### 5.4 State, authority, and safety rules

- `archive_request_nonpersisted` retains `post_launch_row_count`, `first_post_launch_trade_delay_ms`, `first_post_launch_trade_time_ms`, and `last_post_launch_trade_time_ms` as exact `null` values.
- All 13 `authority_flags` values are exact booleans equal to `false`.
- `RISK_LIVE_TRADING_ENABLED` remains `False`; no profile result changes this setting or grants runtime authority.
- A verifier pass is additional structural evidence only. It does not establish semantic completeness, alpha evidence, price response, replay permission, paper/live trading, execution feasibility, or J-B admission.

## 6. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| INV-GSI-V2-01 | The frozen pre-v2 verifier and post-v2 verifier produce exactly equal `(rc, diagnostic_class)` outcomes for the §8.2 v1 behavioral corpus; `v2` is a distinct literal ID/version with no fallback or alias. |
| INV-GSI-V2-02 | `v2` accepts only the ordered self-Delta, parent-Governance-Design, parent-J-A-Design, two-J-A-Delta, and R1-Plan authority chain in §4.1 and the root authority packet in §5.2. |
| INV-GSI-V2-03 | The independent Closure Audit binds `v2` positive evidence to exactly one sealed root, run ID, approved v2 Delta SHA, verifier SHA, and four top-level hashes in §4.1; verifier success alone is not that identity proof. |
| INV-GSI-V2-04 | Persisted response paths are exact receipt-relative `raw/...` manifest members; root-prefixed and normalized alternatives fail closed. |
| INV-GSI-V2-05 | `v2` independently enforces the inherited exact J-A v1 structural contract without importing or trusting producer/loader acceptance. |
| INV-GSI-V2-06 | The replacement root and legacy roots remain immutable; all audit mutations occur only in isolated disposable copies. |
| INV-GSI-V2-07 | A valid `v2` pass creates no network, receipt, J-B, alpha, replay, signal, paper, live, or execution authority. |

## 7. Failure, Persistence, And Compatibility Semantics

1. This is a read-only verifier profile. It creates no staging directory, lock, marker, cache, receipt, or recovery state. Crash/restart handling is therefore `fail closed`: any exception, malformed input, unreadable file, symlink, or hash mismatch returns nonzero and leaves the project unchanged.
2. `v1` remains the historical profile for its original authority tuple. It must reject the replacement root by its `approved_design` authority mismatch and reject the legacy root by its existing nonpersisted nullability diagnostic.
3. `v2` rejects the legacy `20261008T160500Z` root at its authority-chain/profile gate because that root does not carry the required nullability-Delta/R1 identity. The `v2` nullability gate is proved only by a `null -> 0` mutation of an otherwise valid isolated replacement-root copy; no root is migrated or repaired.
4. The `v2` CLI can structurally validate only roots carrying the literal `v2` authority chain, but a positive downstream admission additionally requires the external §4.1 receipt-evidence tuple. A later rerun with different bytes cannot inherit this positive evidence and requires a new Design Delta and Closure Audit record rather than an expanded allowlist.

## 8. Evidence And Verification Strategy

The later Implementation Plan must require all of the following before any `v2` success claim:

1. Verify the parent Governance Design, all three J-A Design/Delta files, the exact root, and the four top-level hashes in §4.1 before editing code.
2. Before editing the verifier, freeze the v1 behavioral oracle:
   - baseline verifier SHA `0071715439e5fd9f64d9b6e62fe86e027ac8f26f6697873202cd521c52fb8c98`;
   - baseline test source `tests/scripts/governance/test_verify_artifact_schema.py` SHA `369627b1f34423f439e4ed977e060de22bd9107b29feb5c3721aa349301a99c3`;
   - the exact registered minimal-valid v1 fixture, every named `MUTATION_CASES` one-mutation case in that frozen test source, and the immutable legacy-negative root.
   Record each baseline result as `(case_id, rc, diagnostic_class)` in Plan evidence before source edits. The post-v2 verifier must reproduce the complete v1 corpus exactly. No existing v1 case may be removed, weakened, skipped, or relabeled.
3. Add `v2` as a second explicit profile only after the baseline evidence exists. Shared pure helpers are allowed only if the recorded v1 corpus remains exactly equal.
4. Invoke the new CLI against the immutable replacement root with `--profile stage1_5j_a_receipt_v2`; expected `rc=0`.
5. Invoke `v1` against the legacy root; expected `rc=1` with the nonpersisted nullability diagnostic. Invoke `v2` against that same legacy root; expected `rc=1` with authority-chain/profile mismatch. Do not use legacy-root behavior as a `v2` nullability probe.
6. Use an isolated writable copy of the replacement root for one-field negative probes. Any file that is mutated must be copied, not hard-linked; read-only raw files may be hard-linked only if their bytes remain untouched.
7. Require at least these single-claim structural-verifier probes to reach the intended `v2` gate:
   - replacement `approved_design` path or SHA mutation;
   - persisted `response_relative_path` changed from `raw/...` to root-prefixed form;
   - persisted `response_relative_path` changed to a non-manifest `raw/...` member;
   - `archive_request_nonpersisted.post_launch_row_count` changed from `null` to `0`;
   - extra file and manifest-listed but grammar-disallowed path;
   - ancestor and descendant symlink;
   - one authority flag changed from `false` to `true`.
8. Independently mutate a manifest member without rebuilding its manifest entry; `v2` must return `rc=1` for sealed-tree hash/byte mismatch. For mutations whose target semantic check follows manifest verification, rebuild only the isolated copy's manifest with canonical byte counts and SHA-256 values. The test must assert the specific semantic diagnostic, not a preceding manifest mismatch.
9. Separately prove the external receipt-identity gate: mutate `review_CN.md` in an isolated copy, rebuild its manifest canonically, then compare observed root/run/four hashes with §4.1 using the external `v2_receipt_closure_evidence.json` procedure. The structural verifier may pass this Markdown-content-only copy; the external evidence comparator must reject it for `review_sha256` mismatch.
10. Re-run J-A public strict loader on the untouched real root independently of `v2`, record both results, and state that neither replaces the other.
11. Run target pytest, Ruff, `git diff --check`, actual `anti_shortcut_scan.py` return code, and direct `RISK_LIVE_TRADING_ENABLED is False` verification.

## 9. Allowed Future Implementation Surface

Only a separately approved Plan may modify:

```text
scripts/governance/verify_artifact_schema.py
tests/scripts/governance/test_verify_artifact_schema.py
.git/plan-execution/governance_artifact_schema/<future-plan-sha>/**
```

The approved v2 Design Delta and approved Plan are read-only authority documents, not implementation paths. No J-A source, J-A test, J-A CLI, parser, configuration, network authorization, `data/` root, J-B file, risk/execution module, or existing `v1` artifact is an implementation path. If `v2` cannot be implemented without changing one of those paths, stop as `BLOCKED_SCOPE_DRIFT` or `BLOCKED_SPEC_DRIFT` as applicable.

## 10. Authority And Routing

1. This Design Delta is documentation only. It does not authorize implementation, commit, push, network, receipt generation, deployment, SSH, replay, signal, paper/live trading, execution, alpha claim, or J-B consumption.
2. Independent Design review and explicit user Design approval are required before an Implementation Plan may be drafted.
3. An approved `v2` Implementation Plan and separate implementation authorization may create only the independent verifier/test/evidence changes in §9. It cannot recreate or change the receipt.
4. A fresh Completion Audit and a fresh Receipt Closure Audit must record the exact approved v2 Delta path/SHA, `v2` verifier SHA, profile ID/version, root identity, four top-level hashes, v1 behavioral-oracle equality results, and the `v2_receipt_closure_evidence.json` sidecar result.
5. Only after both the J-A strict loader and independently approved `v2` verifier pass on the immutable root may a separate J-B Design Delta consider downstream identity, projection, and cardinality rebind. That later Delta remains a distinct authority decision.

## 11. Open Questions

None that affect this Design's implementation path. Whether to pursue J-B after future `v2` closure is explicitly deferred and does not change this Delta.
