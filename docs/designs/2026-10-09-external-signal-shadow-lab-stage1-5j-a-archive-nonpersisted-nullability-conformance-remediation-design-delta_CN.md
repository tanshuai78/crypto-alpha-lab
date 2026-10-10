# Stage 1.5J-A Archive Nonpersisted Nullability Conformance Remediation Design Delta

**日期:** 2026-10-09
**状态:** `revision_for_closure_confirmation`
**父级 Design:** `docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md`
**父级 Design SHA-256:** `b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a`
**前序 Remediation Delta:** `docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md`
**前序 Remediation Delta SHA-256:** `6063ed103d31fcf6c60ad8106eb13650f54b74272182c78bf8e81f9ba48a91ac`
**目的:** 只修复 `archive_request_nonpersisted` 的四个 trade fields nullability drift，使 future J-A replacement receipt 恢复父级 v1 contract；不改变 J-A universe、journal、archive date-set、parser、coverage reducer 或网络行为。
**本 Delta 不授权:** implementation、commit、push、network、receipt generation、deployment、SSH、replay、signal、paper trading、live trading、execution、Alpha claim 或 J-B consumption。

---

## 1. Confirmed Facts

1. 父级 Design 规定 `archive_package_records[].child_state="archive_request_nonpersisted"` 时，四个 trade fields `post_launch_row_count`、`first_post_launch_trade_delay_ms`、`first_post_launch_trade_time_ms`、`last_post_launch_trade_time_ms` 必须全为 `null`。
2. 当前 Core 有两个写入 `post_launch_row_count=0` 的 source sites：一是 child 缺失 launch time，二是 checksum 或 ZIP request 未持久化。后者是唯一可达的 `archive_request_nonpersisted` producer path；前者本身违反父级 resolved-detail contract，必须不再构造 archive record。
3. 当前 strict loader 在 archive raw files 缺失时只检查 `child_state == "archive_request_nonpersisted"`，没有独立验证上述四个 fields 的 nullability。因此 producer 和 loader 可共同接受同一非法 record。
4. immutable root `stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z` 含有 `AIAUSDT` 的该非法状态：`post_launch_row_count=0`。它是已知不合规负例，不是可重写、兼容或作为正向 evidence 的 receipt。
5. 父级 Design 要求每个 declared child 均有 positive non-bool integer launch time；缺失/无效时间属于 detail failure，必须保留 target candidate 为 `catalog_detail_unresolved`，不得形成 archive URL。
6. 当前 Core 仍绑定前序 remediation Design/Plan。任何本 Delta 实施都必须更新新 Core 的 approved Design/Plan authority binding；旧 root 因 authority identity 不匹配被 public strict loader 拒绝是预期 fail-closed 行为。

## 2. Assumptions And Decision

### 2.1 Assumptions

1. 父级 Design 的 v1 nullable 与 resolved-detail launch-time contract 是 frozen source of truth；本 Delta 无权把 `0` 合法化，或将缺失 launch time 合法化为 archive nonpersisted state。
2. 本次 defect 是 local implementation conformance defect，修复可限定在现有 J-A Core 与既有 J-A test module，不需要改动上游 parser、配置、CLI、network profile 或治理 verifier。
3. 当前没有与本 Delta authority tuple 匹配的 real positive receipt。因此 pre-network test 不得伪造或重绑定 full receipt 来宣称 cross-boundary positive evidence。

### 2.2 Decision

1. 新 Core 使用一个 private pure structural validator 检查 archive record 的既有 `child_state` 与四个 trade fields；不新增 public API、registry、schema framework、配置开关或 request-ID combination rule。
2. 在任何 archive identity、UTC date、archive/checksum request 或 archive record 构造前，缺失、bool、零或负的 child launch time 必须将该 target parent 归约为 `catalog_detail_unresolved` / `detail_parser_unresolved`，无 children archive projection、无 HTTP request、无 archive record。它不是 `archive_request_nonpersisted` 的 sibling state。
3. 唯一合法的 `archive_request_nonpersisted` producer path 为：valid resolved child with positive non-bool launch time -> required UTC date-set -> checksum/archive requests admitted -> either response not persisted -> record with all four trade fields `None`。该 record 在加入 summary 前必须经 validator；strict loader 在 archive replay 中、依赖 raw archive 是否存在之前，对每个 `archive_package_records[]` row 调用同一 validator。
4. 对 `archive_request_nonpersisted`，validator 只要求四个 frozen trade fields 均为 `None`。它不改变或新增对 `checksum_request_id`、`zip_request_id`、`logical_archive_identity`、`utc_date`、date-set、coverage counts 或 parent state 的规则。
5. 当前 root 保持 immutable。新 Core 不增加 fallback、legacy alias、authority rebind 或 compatibility mode；其 public loader 对旧 root 的 authority rejection 不是本 Delta semantic validator 的正向证明。

### 2.3 Authority inheritance

The normative chain is exact and additive:

```text
parent J-A Design (b74c306e...fc15a)
  + prior conformance-remediation Delta (6063ed10...a91ac)
  + this nullability Delta
```

This Delta overrides/adds only the launch-time admission and `archive_request_nonpersisted` nullability edges named here. All non-conflicting parent and prior-Delta invariants, including journal grammar, UTC date-set and finite-positive Decimal validation, remain normative. The future Plan Task 0 must recompute the exact parent and prior-Delta bytes; missing or mismatched authority is `STOP=stage1_5j_a_design_authority_chain_mismatch`. Receipt `authority_packet.approved_design` remains the latest Delta only; its content-addressed authority chain is not a new receipt schema field.

## 3. Scope And Non-Goals

### 3.1 Allowed implementation surface for a future approved Plan

```text
src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py
tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py
```

The future Plan may also create its own `.git/plan-execution/stage1_5j_a/<PLAN_SHA256>/` evidence only as required by the existing J-A authority workflow. It may not whitelist a network authorization or create a receipt during pre-network implementation.

### 3.2 Explicit non-goals

1. No change to `configs/base.py`, frozen parser, J-A CLI, fixture bytes, parent Design, prior Design/Plan bytes, `data/`, J-B, Governance verifier, project-status, roadmap, network profile, universe window, journal grammar, Decimal validation, date-set logic or coverage reduction. The sole catalog/detail exception is the child launch-time admission branch required by §2.2; all other catalog/detail logic is No-Touch.
2. No modification, copy, manifest rehash, authority rebind, deletion or compatibility conversion of any existing root.
3. No network call, receipt generation, replay claim, paper/live trading, execution, Alpha/economic/PIT/price-response claim or J-B admission.
4. No synthetic full receipt, mock network success, fabricated authority packet or handcrafted cross-boundary positive fixture. Existing canonical GRVT component fixture remains unchanged and does not prove this receipt-state repair.

## 4. Data, State And Temporal Contract

For every valid archive record with `child_state="archive_request_nonpersisted"`:

```text
post_launch_row_count               = null
first_post_launch_trade_delay_ms    = null
first_post_launch_trade_time_ms     = null
last_post_launch_trade_time_ms      = null
```

Any non-null value in any one of those fields is invalid. In particular, `post_launch_row_count=0` belongs only to `archive_verified_zero_post_launch_rows`; it is not a substitute for a request-nonpersisted result.

`launch_time_ms is None` is not an archive-record state. A declared child without a positive non-bool launch time causes the target parent to remain `catalog_detail_unresolved` / `detail_parser_unresolved`; no logical archive identity, UTC date, request ID, archive URL or `archive_package_records[]` row may be emitted for it.

This Delta does not change the parent v1 exact key set, array ordering, enum literals, request IDs, logical archive identity, raw archive validation, reducer formulas or `schema_version`. It changes no meaning for the two verified archive states.

The new Core must use this Delta and its later approved Plan as the authority packet identity for future receipt production. The pre-existing roots retain their original bytes and identities; none can become compliant by interpretation under the new Core.

## 5. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| INV-15J-A-N-00 | Producer and strict loader independently enforce positive non-bool integer `launch_time_ms` admission for every declared child. An invalid value is `catalog_detail_unresolved` / `detail_parser_unresolved`, with `children=[]`, `parent_state=coverage_evidence_gap_detail` and zero archive identity/request/record output. |
| INV-15J-A-N-01 | Every future producer-created valid `archive_request_nonpersisted` record has all four frozen trade fields null. |
| INV-15J-A-N-02 | The strict loader independently applies the same private structural nullability validator to every archive record before raw-file replay branch selection. |
| INV-15J-A-N-03 | A single semantic mutation `post_launch_row_count: null -> 0` for `archive_request_nonpersisted` reaches the validator and fail-closes with `STOP=stage1_5j_a_archive_package_record_invalid:archive_request_nonpersisted_trade_fields_must_be_null`. |
| INV-15J-A-N-04 | The old `20261008T160500Z` root remains immutable and is never made loader-compatible through fallback, rebind or schema relaxation. |
| INV-15J-A-N-05 | Pre-network completion is implementation-only evidence. It creates no receipt and does not grant network, Governance verifier, J-B, Alpha, replay, paper/live or execution authority. |

## 6. Producer, Loader And Consumer Matrix

| Actor | Required change or behavior | Forbidden behavior | Proof |
| --- | --- | --- | --- |
| producer `run_inventory` | invalid launch time routes to `catalog_detail_unresolved` / `detail_parser_unresolved` before archive work; the sole valid nonpersisted branch constructs four null trade fields and passes the shared validator before adding the row | emitting `0`; converting missing launch time into nonpersisted; bypassing validator; network test seam | no-request/no-record launch-time proof plus valid-branch wiring inspection |
| strict loader | independently replays every parsed declared child's positive non-bool integer launch-time admission before accepting `validated_target_detail`; an invalid value requires `catalog_detail_unresolved`, `detail_parser_unresolved`, `children=[]`, `parent_state=coverage_evidence_gap_detail` and zero archive projection. For valid archive rows it invokes the nullability validator before persisted/nonpersisted replay-path selection | treating parser `parsed` or state enum alone as sufficient; accepting invalid launch time as validated detail; accepting a mutated `0` | invalid-launch replay acceptance/rejection proof plus direct validator mutation and loader-call proof |
| existing root | stays byte-identical and fail-closed under future authority binding | copying, editing, resealing or authority rebinding | path/hash baseline and public loader rejection |
| future replacement receipt | may be produced only after a later, separately authorized network run | using legacy root as positive evidence | future Receipt Closure Audit |
| J-B/Governance verifier | remains blocked from consuming any root in this Delta | implicit rebind or consumer admission | no consumer code/path in Plan scope |

## 7. Failure Semantics, Persistence And Recovery

The private validator must raise exactly:

```text
STOP=stage1_5j_a_archive_package_record_invalid:archive_request_nonpersisted_trade_fields_must_be_null
```

when an `archive_request_nonpersisted` row has any non-null frozen trade field. The producer must fail before the affected record enters the summary; the loader must fail before it accepts a nonpersisted raw-file branch. Missing/invalid launch time follows the parent reducer in §4 rather than this row validator. No coercion from `0` to `null`, inference from `child_state`, fallback, warning or partial acceptance is permitted.

This repair does not alter J-A staging, parent `flock`, double `fsync`, atomic rename, four-state lifecycle or crash/recovery protocol. If a process fails before publication, existing no-resume behavior remains; if a final root exists, collision handling remains unchanged. There is no migration: legacy final roots are immutable and rejected rather than transformed.

## 8. Verification Strategy And Evidence Provenance

### 8.1 Pre-network implementation gates

The future Plan must require all of the following:

1. A pure local record test accepts `archive_request_nonpersisted` only when all four trade fields are `None`; it is internal logic coverage, not a receipt claim.
2. Four single-field negative tests each mutate exactly one of the four fields from `None` to a non-null value. The required named probe changes only `post_launch_row_count` from `None` to `0` and asserts the exact STOP in INV-15J-A-N-03.
3. A valid target detail whose declared child has `launch_time_ms` equal to `None`, `True`, `0`, `-1`, `1.5` or `"123"` must be reduced to `catalog_detail_unresolved` / `detail_parser_unresolved`; the test asserts `children=[]`, `parent_state=coverage_evidence_gap_detail`, no archive identity, no archive package record and zero HTTP request. This is parent-contract proof, not a new archive-record state.
4. A loader replay proof supplies each invalid launch-time parser projection and requires acceptance only of that unresolved representation; it must reject a forged `validated_target_detail` representation for the same projection. This proof exercises the actual loader replay path, not a parallel test-only reducer.
5. A production-wiring proof demonstrates the sole valid `run_inventory` nonpersisted construction branch and `load_verified_stage1_5j_a_historical_archive_coverage_root` call the same private validator. This proof must inspect/call actual production symbols; it may not use a parallel test-only validator.
6. The public loader is invoked on immutable `20261008T160500Z` without mutation and fails closed under the new authority identity. This is legacy incompatibility proof only, not a semantic-nullability probe.
7. Existing canonical GRVT fixture Proof B, target J-A tests, Ruff, `git diff --check`, `RISK_LIVE_TRADING_ENABLED is False`, index/scope proof and `.agent/tools/anti_shortcut_scan.py` with its actual process return code all pass. The scanner command is read from the approved future Plan; a summarized scanner claim is insufficient.

### 8.2 Deferred post-network receipt closure

Only after a separate user-approved single-use network authorization creates a new root bound to this Delta and its approved Plan may a Receipt Closure Audit conduct a real-root positive load.

If the future root contains one or more genuine `archive_request_nonpersisted` rows, that audit must use an isolated temporary copy and one declared semantic mutation: change only one row's `post_launch_row_count` from `null` to `0`. Derived witness preparation must then: canonical-regenerate `summary.json`; regenerate `review_CN.md` from the mutated summary; update the manifest byte-count/SHA for both `summary.json` and `review_CN.md`; and canonical-regenerate `manifest.json`. The loader must reject with exactly the STOP in INV-15J-A-N-03, not an earlier manifest, review-projection or hash failure. Derived-file regeneration is required witness preparation, not a second semantic mutation.

If the future root has no genuine `archive_request_nonpersisted` row, set `real_root_nullability_mutation=not_applicable_no_nonpersisted_row`. Do not manufacture that state by changing `child_state`, deleting raw packages or fabricating a request failure. The pre-network production-path negative tests remain the nullability proof; any then-approved Governance verifier provides separate structural evidence.

## 9. Safety And Research Boundary

This is deterministic schema conformance work, not an Alpha research stage. The following are `N/A`: phenomenon claim, statistical/economic edge, independent sample, outcome metric, cost/friction, MAE/tail analysis, promotion/kill rule and execution feasibility. The only permitted conclusion is whether the specified v1 nullability contract is enforced.

`RISK_LIVE_TRADING_ENABLED` remains `False`. All existing J-A authority flags remain `false`; no flag is added, removed or changed by this Delta.

## 10. Authority And Routing

1. The first independent review of this Design is a `closure_audit`. Because that audit found blockers and this revision keeps its proof graph, trust boundary and scope frozen, the next review is `closure_confirmation`; only then may the user issue explicit Design approval for a remediation Implementation Plan.
2. A later approved Plan Task 0 must verify the authority chain in §2.3 before baseline capture. A missing/mismatched parent or prior Delta is `STOP=stage1_5j_a_design_authority_chain_mismatch`.
3. A later approved Plan plus explicit user implementation authorization may perform only the pre-network source/test changes in §3.1. It cannot authorize commit, push, deployment, SSH, network, receipt generation, J-B consumption or trading action.
4. Successful pre-network Completion Audit closes only implementation readiness. It routes next to the separate Governance verifier Implementation Plan, where the old root is a required real negative case.
5. A future J-A network run requires a new user authorization bound to this Delta, its approved remediation Plan and newly audited Core/CLI/Config bytes. It must use a new RUN_ID and cannot reuse legacy authorization or root.
6. Only after the future root passes both J-A strict-loader closure and the independently approved Governance verifier may a separate J-B Design Delta bind it as upstream positive evidence.

## 11. Open Questions

None that affect the pre-network implementation path. The future network timing and archive availability are intentionally deferred to the later single-use authorization; they cannot alter this nullability repair.
