# Governance Stage 1.5J-B Receipt Rule 17 Profile Design Delta

**日期:** 2026-10-11
**状态:** `draft_for_independent_review`
**父级 Governance Design:** `docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md`
**父级 Governance Design SHA-256:** `73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4`
**J-B 父级 Design:** `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md`
**J-B 父级 Design SHA-256:** `ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b`
**J-B Rebind Delta:** `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md`
**J-B Rebind Delta SHA-256:** `0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c`
**J-B Receipt Schema Authority Delta:** `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md`
**J-B Receipt Schema Authority Delta SHA-256:** `f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25`
**目的:** 定义独立的 `stage1_5j_b_receipt_v1` Rule 17 structural verifier profile。该 profile 只验证 J-B receipt 的封存树、持久化 schema、authority 和内部 relation；J-B strict loader 仍是唯一的领域语义 replay/renderer owner。

## 1. Confirmed Facts

1. J-B receipt schema/target-stage authority 已由上述 Receipt Schema Authority Delta 冻结。未来 `authority_packet.approved_j_b_design` 必须绑定该领域 Delta，而不是本 Governance profile。
2. J-B Rebind Delta 已冻结唯一 J-A upstream identity、`stage1_5j_a_receipt_v2` governance closure 和 `120/11/280/1/5` projection；它不定义 J-B target receipt 的独立 Rule 17 verifier。
3. `scripts/governance/verify_artifact_schema.py` 和 `tests/scripts/governance/test_verify_artifact_schema.py` 是已封存的 J-A v1/v2 verifier surface；当前 SHA-256 分别为 `7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473` 和 `b0865f2eaeca091e45bee3724840c349c63a12778dc2a64e855dab2c36c81ff6`。J-B 不得修改、调用、重解释或以行为回归替代其 bytes identity。
4. 当前不存在 J-B producer、CLI、final receipt 或 receipt-generation authorization。任何 synthetic fixture 只能证明独立 verifier mechanics，不能构成 J-B production-positive、semantic replay、closure 或 downstream admission 证据。

## 2. Assumptions

1. 未来 J-B producer/strict loader 仅以 parent Design、Rebind Delta 和全量 strict-loaded J-A replacement root 为输入；它们不接受 caller-supplied J-A/J-B row dictionaries 作为 positive boundary fixture。
2. 本 Design 在独立 review 和用户 approval 后的 exact SHA-256 是 future Plan 与 future closure evidence 的外部 immutable audit binding。它不写入 J-B receipt 的 `approved_j_b_design`，因为该字段属于 target-stage domain authority，已在 Receipt Schema Authority Delta 中冻结。
3. J-B strict loader 将独立 re-render `review_CN.md` 的 exact bytes；本 profile 不创建第二个 Markdown semantic authority。

## 3. Decision, Scope, And No-Touch Boundary

### 3.1 Decision

1. 新增独立 stdlib-only verifier surface：

```text
scripts/governance/verify_stage1_5j_b_receipt_schema.py
tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py
```

   它不 import `src/`、J-B CLI、J-B loader、J-B tests 或 J-A verifier；不得读取 `.git`、网络、环境权限或动态 Design/Plan 内容。
2. verifier 内置下文完整 immutable profile constants，并对传入 root 的 artifact bytes 进行只读验证。它不自证 source SHA；future Completion/Receipt Closure Audit 必须在外部记录此 Design approved SHA、verifier source SHA、profile ID/version、root/run、manifest/summary/review SHA 和两个 validator 的 actual RC。
3. `summary.authority_packet.approved_j_b_design` 必须等于已批准 J-B Receipt Schema Authority Delta 的 path/SHA。`receipt_generation_authorization.APPROVED_J_B_DESIGN_SHA256` 的跨文件 authority proof 仍由 J-B strict loader 和 Receipt Closure Auditor 负责；profile verifier 仅验证 receipt-internal object 与其 frozen domain tuple。
4. `review_CN.md` 只验证 sealed-tree regular membership、manifest byte count 和 SHA-256，以及 parent Governance Design 允许的 UTF-8/LF/NUL byte safety。它禁止解析标题、表格、投影、数值或任何 Markdown semantic content。

### 3.2 Mutable Set

- 本未批准 Governance Delta 的 profile authority、independent verifier ownership、J-B persistent structural contract、future test/CLI/closure obligations。

### 3.3 No-Touch Set

- J-A v1/v2 profile ID、acceptance semantics、verifier/test source bytes和上述 SHA。
- 已批准 J-B parent Design、Rebind Delta、Receipt Schema Authority Delta 的 bytes、J-A replacement root、`120/11/280/1/5` projection、J-B domain schema/reducer/renderer/lifecycle owner。
- J-B source、CLI、tests、config、receipt、receipt-generation authorization、network、consumer、Alpha/replay/signal/paper/live/execution、commit/push/deployment/SSH action。

## 4. Immutable Profile Authority Tuple

The future verifier uses literal constants for this tuple. It must not discover them by reading documents at runtime.

```text
profile_id = stage1_5j_b_receipt_v1
profile_contract_version = 1

governance_parent_design_relative_path = docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md
governance_parent_design_sha256 = 73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4

j_b_parent_design_relative_path = docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md
j_b_parent_design_sha256 = ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b
j_b_rebind_delta_relative_path = docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md
j_b_rebind_delta_sha256 = 0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c
j_b_receipt_schema_authority_relative_path = docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md
j_b_receipt_schema_authority_sha256 = f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25

j_b_profile_design_delta_relative_path = docs/designs/2026-10-11-governance-stage1-5j-b-receipt-rule17-profile-design-delta_CN.md
j_b_verifier_relative_path = scripts/governance/verify_stage1_5j_b_receipt_schema.py
```

`j_b_profile_design_delta_sha256` is deliberately an external post-approval binding, not a mutable self-reference inside this candidate. Before any implementation, the approved Plan Task 0 must hard-bind its approved value and reject any mismatch. Future closure evidence must repeat that path/SHA plus the exact verifier source SHA. A receipt field may not substitute this audit binding.

The receipt-internal authority rule is exact:

```text
summary.authority_packet.approved_j_b_design.relative_path = j_b_receipt_schema_authority_relative_path
summary.authority_packet.approved_j_b_design.sha256 = j_b_receipt_schema_authority_sha256
```

No alias, predecessor Design, Rebind Delta alone, Governance profile path, dynamic SHA lookup, fallback or compatibility acceptance is legal.

## 5. `stage1_5j_b_receipt_v1` Structural Contract

### 5.1 Root, manifest, and byte rules

```text
OUTPUT_PARENT = data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response
RUN_ID_REGEX = ^stage1_5j_b_historical_aggtrades_launch_response_[0-9]{8}T[0-9]{6}Z$
SCHEMA_VERSION = stage1_5j_b_historical_aggtrades_launch_response_v1
```

Verifier input is a project-relative, contained, non-symlink final root directly below `OUTPUT_PARENT`, whose basename matches `RUN_ID_REGEX`. Every ancestor from project root through root is non-symlink. The final root has exactly three regular members and no descendants:

```text
manifest.json
summary.json
review_CN.md
```

`manifest.json` and `summary.json` are UTF-8 without BOM and are byte-for-byte `json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n'`. `review_CN.md` is UTF-8 without BOM, LF-only, has one terminal LF and no NUL. Manifest has exactly `artifacts`, `root_relative_path`, `run_id`, `schema_version`; it lists only `review_CN.md` and `summary.json`, in lexical relative-path order. Each artifact has exactly `byte_count`, `relative_path`, `sha256`; byte count is a non-bool non-negative integer and the lower-case 64-hex SHA must match disk bytes. Manifest never self-lists.

### 5.2 Summary envelope, flags, research status, and domain authority

`summary.json` has exactly:

```text
analysis_state, authority_flags, authority_packet, child_horizon_rows,
child_rows, coverage_counts, decision, j_a_input, parent_horizon_rows,
research_status, run_id, schema_version
```

`analysis_state` is exactly `exploratory_response_described` or `exploratory_response_evidence_gap`; `decision` is exactly the paired `stage1_5j_b_historical_aggtrades_launch_response_described_published` or `stage1_5j_b_historical_aggtrades_launch_response_evidence_gap_published` value from §5.6.

`authority_flags` has exactly twelve keys, each literal `false`:

```text
alpha_claim_allowed, alpha_interpretation_allowed, commit_allowed,
deployment_allowed, execution_allowed, live_trading_allowed, network_allowed,
paper_trading_allowed, pnl_calculation_allowed,
receipt_generation_allowed_without_authorization, replay_allowed,
signal_generation_allowed
```

`research_status` has exactly `alpha_evidence_status`, `capital_survival_claim`, `economic_edge_claim`, `execution_feasibility_claim`, `live_permission_claim`, `phenomenon_claim`, `research_mode`, `statistical_edge_claim`; its values are exactly `evidence_insufficient`, five `not_evaluated` claim literals, `false` for `live_permission_claim`, and `exploratory_descriptive_only` for `research_mode`.

`authority_packet` has exactly `approved_j_b_design`, `approved_j_b_plan`, `audited_cli`, `audited_config`, `audited_core`, `j_a_manifest_sha256`, `receipt_generation_authorization`. The first five have exactly `relative_path` and `sha256`; `receipt_generation_authorization` has exactly `authorized_run_id`, `relative_path`, `sha256`. All SHA values are lower-case 64-hex, `j_a_manifest_sha256` equals `b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf`, and `approved_j_b_design` satisfies §4 exactly. The verifier validates only this receipt-internal grammar and frozen target Design tuple; it does not read the external authorization file or sidecar.

### 5.3 Rebound J-A tuple and projection

`j_a_input` has exactly these sixteen keys:

```text
j_a_core_path, j_a_core_sha256,
j_a_governance_closure_evidence_relative_path,
j_a_governance_closure_evidence_sha256,
j_a_governance_evidence_status,
j_a_governance_profile_contract_version,
j_a_governance_profile_id,
j_a_governance_rule17_v2_positive,
j_a_governance_verifier_relative_path,
j_a_governance_verifier_sha256,
j_a_journal_sha256, j_a_manifest_sha256, j_a_root_relative_path,
j_a_review_sha256, j_a_run_id, j_a_summary_sha256
```

Every value equals the literal Rebind Delta tuple for `stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z`, including `stage1_5j_a_receipt_v2`, version `2`, `receipt_closure_audited_positive`, `true`, the J-A v2 verifier path/SHA and all four top-level J-A artifact hashes. `coverage_counts` has exactly `j_a_parent_coverage_complete_count`, `j_a_parent_coverage_gap_count`, `j_a_target_parent_count`, `n_child_horizon_complete_by_horizon`, `n_child_horizon_gap_by_horizon`, `n_parent_horizon_complete_by_horizon`, `n_parent_horizon_gap_by_horizon`, `n_parent_total`, `n_parent_with_j_a_gap`, `parent_distribution_by_horizon`.

The frozen scalar projection is:

```text
j_a_parent_coverage_complete_count = 120
j_a_parent_coverage_gap_count = 11
j_a_target_parent_count = 131
n_parent_total = 131
n_parent_with_j_a_gap = 11
```

Each count/distribution map has exactly the decimal-string keys `"300000"`, `"3600000"`, `"14400000"`; integer counts are non-bool and non-negative. Each `parent_distribution_by_horizon` value has exactly `max`, `mean`, `median`, `min`, `n_complete_parent`, `p10`, `p25`, `p50`, `p75`, `p90`, `top_1_abs_return_contribution`, `top_1_parent_ids`, `top_3_abs_return_contribution`, `top_3_parent_ids` and obeys the literal scalar/ID-array grammar in the approved J-B Receipt Schema Authority Delta.

### 5.4 Exact row schemas, enums, and conditional combinations

The verifier must copy the following literal profile constants from the approved J-B Receipt Schema Authority Delta; it must not weaken them to arbitrary nonempty strings:

```text
SOURCE_ARTICLE_ID = ^[0-9a-f]{32}$
SYMBOL = ^[A-Z0-9]+USDT$
HORIZON_MS = 300000 | 3600000 | 14400000
J_A_PARENT_STATE = coverage_complete |
  coverage_evidence_gap_archive |
  coverage_evidence_gap_detail |
  coverage_evidence_gap_no_in_scope_usdt_child
J_A_CHILD_STATE = j_a_child_coverage_complete | j_a_child_coverage_gap
ANCHOR_STATE = anchor_found |
  anchor_unavailable_inherited_j_a_parent_gap |
  anchor_unavailable_delay_exceeded
CHILD_HORIZON_STATE = child_horizon_complete | child_horizon_evidence_gap
PARENT_HORIZON_STATE = parent_horizon_complete | parent_horizon_evidence_gap
MISSING_REASON = inherited_j_a_parent_gap |
  evidence_gap_missing_launch_time |
  evidence_gap_anchor_delay |
  evidence_gap_missing_required_archive_package |
  evidence_gap_missing_horizon_trade
```

`child_rows` is ordered by `(source_article_id,symbol)`, has exactly 281 rows, and every row has exactly `anchor_delay_ms`, `anchor_price`, `anchor_state`, `anchor_time_ms`, `j_a_child_state`, `j_a_parent_state`, `required_archive_dates_by_horizon`, `source_article_id`, `symbol`, `symbol_launch_time_ms`. Its anchor nullability, positive/non-bool integer rules, canonical Decimal grammar and required-date map are exactly §4.3 of the approved Schema Authority Delta.

`child_horizon_rows` is ordered by `(source_article_id,symbol,horizon_ms)`, has exactly 843 rows, and every row has exactly `child_horizon_state`, `gross_return_bps`, `horizon_ms`, `horizon_offset_ms`, `horizon_price`, `horizon_selected_time_ms`, `horizon_target_time_ms`, `missing_reason`, `sampled_max_excursion_bps`, `sampled_min_excursion_bps`, `source_article_id`, `symbol`, `trade_count`. Complete rows require `missing_reason=null` and all outcome fields non-null/type-valid. Gap rows require one non-null `MISSING_REASON` and every outcome field null. Anchor-to-gap-reason combinations are exactly §4.4 of that Delta.

`parent_horizon_rows` is ordered by `(source_article_id,horizon_ms)`, has exactly 393 rows, and every row has exactly `failed_child_reasons`, `horizon_ms`, `parent_gross_return_bps`, `parent_horizon_state`, `parent_sampled_max_excursion_bps`, `parent_sampled_min_excursion_bps`, `source_article_id`, `source_parent_state`. Complete rows require canonical non-null BPS outcomes and `failed_child_reasons=[]`; gap rows require null outcomes and the precise non-empty failed-child/sentinel form in §4.5 of the Schema Authority Delta.

All persisted Decimal/BPS/ratio values must satisfy the exact finite canonical grammar and bounds in Schema Authority Delta §4.1. The independent verifier does not recompute trade arithmetic, anchor selection, required dates, physical ordering or reducer inputs; J-B strict loader does that domain proof.

### 5.5 Cartesian identity and cross-row relations

The following relations are structural and mandatory:

1. `child_rows` has 281 unique identities `(source_article_id,symbol)`.
2. `child_horizon_rows` has exactly the set `child_identities x {300000,3600000,14400000}`: 843 unique identities, no extra/missing/duplicate row, and its `source_article_id`/`symbol` values equal its parent child row.
3. `parent_horizon_rows` has exactly the 131 J-A target-parent identity set x the same three horizons: 393 unique identities. For each source/horizon, `source_parent_state` equals every matching child row's `j_a_parent_state`; source parents without child identities use only the approved Schema Authority Delta parent-gap sentinel representation.
4. Each child row's `required_archive_dates_by_horizon` uses exactly the three horizon keys, each date list is sorted/unique/calendar-valid, and non-anchor rows have three empty arrays. No verifier fallback computes or normalizes dates.
5. Coverage counts equal the actual complete/gap rows at each horizon, their sums are respectively 281 and 131, and distribution `n_complete_parent`, ID arrays and contribution ratios obey the exact approved Schema Authority Delta relations.

### 5.6 Reducer pair and `review_CN.md` boundary

```text
analysis_state = exploratory_response_described
iff every J-A coverage-complete parent has parent_horizon_complete at all three horizons

decision = stage1_5j_b_historical_aggtrades_launch_response_described_published
iff analysis_state = exploratory_response_described
```

Otherwise the evidence-gap state and paired evidence-gap decision are required. Return sign, distribution values, concentration or any Markdown content never changes this reducer.

The profile's `review_CN.md` check ends at §5.1 sealed-tree/hash/byte-safety. It must not parse headings, tables, strings, counts, flags, input identity or non-claim prose. J-B strict loader alone independently re-renders and verifies its semantic projection byte-for-byte.

## 6. Producer, Verifier, Loader, Consumer, And Audit Matrix

| Role | Required behavior | Forbidden behavior |
| --- | --- | --- |
| J-B producer | Future authorized writer derives rows from full admitted J-A root and emits only the domain contract. | Network, raw retention, J-A mutation, verifier substitution, consumer authorization. |
| J-B strict loader | Independently strict-loads J-A and J-B, recomputes domain semantics/reducer, validates authorization and exact Markdown render. | Trusting producer summary or profile pass as semantic proof. |
| J-B Rule 17 verifier | Uses literal profile constants plus root bytes only and validates §§4-5 structurally. | Importing J-B/J-A target code, `.git` access, dynamic profile discovery, writes, subprocesses, sockets or network. |
| Verifier tests | Use only a labeled synthetic sealed tree to prove verifier mechanics and isolated mutations. | Claiming that fixture is a J-B receipt, semantic replay or closure evidence. |
| Receipt Closure Auditor | Runs public J-B strict loader and exact independent verifier against an immutable authorized J-B root. | Treating either pass, a test fixture, or one external SHA as closure. |
| Future consumer | Requires separately approved consumer Design and explicit authority. | Reading J-B receipt because this profile passes. |

## 7. Failure, CLI, Persistence, And Compatibility

The future verifier is read-only. It neither repairs, normalizes, rewrites, stages, renames, locks nor deletes. Failure precedence is containment/symlink -> CLI/root argument -> canonical bytes -> sealed tree/manifest -> summary envelope/authority -> rebind tuple/projection -> row schema/cartesian relation/conditional fields -> reducer pair -> review byte safety.

Its CLI exits are fixed:

```text
0 = root is conformant with the selected supported literal profile
1 = valid invocation reached profile validation and found a contract violation
2 = invalid CLI arguments, unsupported profile, non-project-relative/traversal root,
    unavailable root, or unreadable root before profile validation
```

No existing profile changes. `stage1_5j_a_receipt_v1` and `stage1_5j_a_receipt_v2` retain their exact source identities and acceptance/rejection behavior because the new J-B verifier is a different executable. `stage1_5j_b_receipt_v1` accepts no J-A profile, legacy J-B root, partial root, staging root, final-plus-staging root or compatibility alias.

## 8. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| `INV-GSI-JB-01` | Only literal `stage1_5j_b_receipt_v1`/version `1` and §4 tuple identify this profile; its future approval SHA is externally bound before implementation and again at closure. |
| `INV-GSI-JB-02` | The independent verifier derives acceptance only from literal profile constants and J-B artifact bytes, never J-B producer/loader/test imports or their acceptance. |
| `INV-GSI-JB-03` | `approved_j_b_design` is exactly the approved J-B Receipt Schema Authority Delta, while the Governance profile Design SHA remains an external audit binding. |
| `INV-GSI-JB-04` | The verifier enforces exact summary, authority, rebind, projection, rows, enums, conditional combinations, manifest and Cartesian relations in §§5.1-5.5 without inventing domain semantics. |
| `INV-GSI-JB-05` | `review_CN.md` validation is only byte/tree/hash safety; exact semantic render is solely J-B strict-loader responsibility. |
| `INV-GSI-JB-06` | Profile pass and strict-loader pass are independently required for a future closure; neither grants consumer, Alpha, trading, runtime or execution authority. |
| `INV-GSI-JB-07` | Closure evidence binds exact approved profile Design SHA, verifier source SHA, profile ID/version, root/run, manifest/summary/review hashes and both actual RC values. |
| `INV-GSI-JB-08` | CLI return codes are exactly §7; an invalid invocation must never be reported as a contract-conformant root or a profile violation. |

## 9. Future Verification And Evidence Strategy

### 9.1 Allowed implementation surface and fixture classes

Only a later independently reviewed and user-approved Plan may modify:

```text
scripts/governance/verify_stage1_5j_b_receipt_schema.py
tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py
.git/plan-execution/governance_stage1_5j_b_receipt_profile/<APPROVED_PROFILE_PLAN_SHA256>/**
```

Plan Task 0 must prove the two J-A files in §1 remain exact bytes/SHA and must hard-bind this Design's approved SHA before any edit. It must not add J-B support to the J-A verifier.

Fixture classes are non-interchangeable:

1. Target J-B producer/strict-loader positive fixture derives only from the full public strict-loaded J-A replacement root through canonical J-B production serialization. It is the sole positive cross-boundary fixture.
2. A labeled synthetic sealed J-B tree proves only the independent profile verifier's structural mechanics. It cannot prove J-B semantic replay, authority admission or receipt closure.

### 9.2 Exact mutation and process obligations

The new verifier test suite must use one declared mutation per case and rebuild only the affected canonical bytes/manifest where required to reach the intended gate. It must cover, at minimum:

```text
every profile/version and immutable tuple literal;
every top-level and nested exact key-set family;
each of the 12 false authority flags;
every persisted j_a_input literal and 120/11/131 projection literal;
every enum literal branch listed in §5.4;
every conditional nullability combination for anchor, child horizon and parent horizon;
each child/child-horizon/parent-horizon duplicate, omission, order and cross-row identity mismatch;
each required-date map key/date ordering rule and coverage/distribution relation;
canonical JSON/LF/BOM/NUL violations;
manifest byte/SHA mismatch, missing/extra tree member and symlink;
review byte-safety/manifest mismatch; and CLI 0/1/2 classification.
```

The target J-B producer/loader suite must independently derive its positive fixture from the J-A replacement root and demonstrate that the loader, not the verifier, detects semantic/re-render defects. A synthetic mechanics fixture cannot substitute for this proof.

### 9.3 Future closure evidence

Only an independent Receipt Closure Auditor may write canonical closure evidence and its SHA-256 sidecar beneath:

```text
.git/plan-execution/governance_stage1_5j_b_receipt_profile/<APPROVED_PROFILE_PLAN_SHA256>/evidence/
```

The evidence record has exact fields:

```text
evidence_status,
governance_parent_design_relative_path, governance_parent_design_sha256,
j_b_parent_design_relative_path, j_b_parent_design_sha256,
j_b_rebind_delta_relative_path, j_b_rebind_delta_sha256,
j_b_receipt_schema_authority_relative_path, j_b_receipt_schema_authority_sha256,
j_b_profile_design_delta_relative_path, j_b_profile_design_delta_sha256,
profile_id, profile_contract_version,
verifier_relative_path, verifier_source_sha256,
receipt_root_relative_path, receipt_run_id,
manifest_sha256, summary_sha256, review_sha256,
strict_loader_expected_rc, strict_loader_observed_rc,
verifier_expected_rc, verifier_observed_rc,
governance_rule17_j_b_v1_positive
```

All four expected/observed RC values are integer `0`, `evidence_status=receipt_closure_audited_positive`, and `governance_rule17_j_b_v1_positive=true`. The auditor derives path/hash/run values from approved bytes and immutable root, reruns both validators, and rejects every mismatch with `STOP=governance_j_b_v1_receipt_identity_evidence_mismatch`.

## 10. Safety, Rollout, Open Questions, And Routing

This is deterministic governance work. It changes no J-B study, phenomenon/statistical/economic edge claim, PnL, cost, liquidity, capacity, replay, signal, paper/live trading or execution authority. `RISK_LIVE_TRADING_ENABLED` remains `False`; every persisted J-B authority flag remains `false`.

Rollout/rollback: N/A. This Design authorizes no code, deployment or root. If future implementation cannot satisfy this profile, it must stop without publishing a J-B receipt or reinterpreting legacy bytes.

Open questions: none that alter the future implementation path. Future Plan SHA, verifier source SHA, J-B run ID/root hashes and receipt-generation authorization are intentionally unavailable lifecycle outputs; they must be freshly bound in their separate approved stages and must not be guessed here.

Next route: independent Design review. Only a reviewed and user-approved Governance profile Design may unblock a replacement J-B Implementation Plan; that Plan remains responsible for the separate J-B domain implementation and receipt-generation authority chain.
