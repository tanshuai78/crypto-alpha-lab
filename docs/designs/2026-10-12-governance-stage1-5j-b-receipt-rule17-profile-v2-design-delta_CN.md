# Governance Stage 1.5J-B Receipt Rule 17 Profile v2 Design Delta

**日期:** 2026-10-12
**状态:** `draft_for_independent_review`
**父级 Governance Design:** `docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md`
**父级 Governance Design SHA-256:** `73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4`
**J-B Rule 17 Profile v1 Delta:** `docs/designs/2026-10-11-governance-stage1-5j-b-receipt-rule17-profile-design-delta_CN.md`
**J-B Rule 17 Profile v1 Delta SHA-256:** `a692a888e1a9ae6b66379045fc031c6075eb72ff99fc30d140dd671caaa1153b`
**J-B Compatibility Domain Delta:** `docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md`
**J-B Compatibility Domain Delta SHA-256:** `66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f`
**目的:** 定义独立的 `stage1_5j_b_receipt_v2` Rule 17 profile，使 J-B receipt 的 persisted config authority 与最新 J-B Compatibility Domain Delta 精确绑定；保留 v1 immutable bytes/behavior，并将 v1-on-v2 的任何 pass 判定为非权威 closure evidence。

---

## 0. Delta Authority And Non-Authorization

本 Delta 仅定义新的 J-B independent verifier profile authority、profile selection 和 closure-evidence identity。它不改变 J-B domain measurement/reducer/renderer/lifecycle owner，不修改 J-A 任何 source/artifact/verifier，也不修改 J-B v1 profile bytes。

本 Delta 不授权 implementation、commit、push、deployment、SSH、network、receipt generation、consumer、replay、signal、paper trading、live trading、execution 或 Alpha claim。

**Mutable Set:** 一个新的 J-B Rule 17 v2 profile definition、future verifier v2 branch、其 direct tests、以及 future profile closure evidence。
**No-Touch Set:** Governance parent Design bytes、J-B Rule 17 v1 Delta and profile/verifier behavior、J-B parent/Rebind/Receipt Schema Authority Delta bytes、J-B Compatibility Domain Delta SHA `66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f`、J-A core/root/loader/verifier/closure evidence、J-B domain core/CLI/measurement/reducer/renderer/lifecycle, all authority flags and all runtime/trading permissions.

---

## 1. Confirmed Facts And Scope

1. Rule 17 requires an immutable profile authority tuple: approved Governance Design, target-stage authority, profile ID/version, verifier source identity, receipt identity, and actual validator results. A profile name alone is not authority.
2. `stage1_5j_b_receipt_v1` accepts an `audited_config` object grammar but does not freeze its path/SHA. It cannot independently prove the J-B Compatibility Domain Delta's new config authority edge.
3. The Compatibility Domain Delta establishes the latest J-B target-stage Design authority, the sole permitted stage-local config path, exact 565-byte config source, and exact SHA `771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4`.
4. There is no generated J-B receipt or receipt-generation authorization. Synthetic verifier fixtures prove only structural mechanics and are not domain-positive or closure evidence.

**In scope:** a successor independent profile and its future verifier/test/evidence contract.
**Out of scope:** changes to v1, J-A, domain producer/loader semantics, config policy, config source, any receipt generation, any root publication, or any permission.

---

## 2. Immutable v2 Profile Authority Tuple

The future verifier contains literal constants only. It must not read these documents, `.git`, J-B source/CLI/loader/tests, environment variables, sockets, subprocesses, or network APIs at runtime.

```text
PROFILE_ID = stage1_5j_b_receipt_v2
PROFILE_CONTRACT_VERSION = 2

GOVERNANCE_PARENT_DESIGN_PATH = docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md
GOVERNANCE_PARENT_DESIGN_SHA256 = 73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4

PROFILE_V2_DESIGN_PATH = docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md
PROFILE_V2_DESIGN_SHA256 = user-approved exact SHA-256 of this Delta

LATEST_J_B_DOMAIN_DESIGN_PATH = docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md
LATEST_J_B_DOMAIN_DESIGN_SHA256 = 66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f

J_B_PARENT_DESIGN_PATH = docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md
J_B_PARENT_DESIGN_SHA256 = ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b
J_B_REBIND_DELTA_PATH = docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md
J_B_REBIND_DELTA_SHA256 = 0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c
J_B_RECEIPT_SCHEMA_AUTHORITY_PATH = docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md
J_B_RECEIPT_SCHEMA_AUTHORITY_SHA256 = f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25

PROFILE_AUDITED_CONFIG_RELATIVE_PATH = configs/stage1_5j_b_historical_aggtrades_launch_response.py
PROFILE_AUDITED_CONFIG_SHA256 = 771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4

VERIFIER_RELATIVE_PATH = scripts/governance/verify_stage1_5j_b_receipt_schema.py
VERIFIER_SOURCE_SHA256 = completion-audited exact SHA-256 of the v2 verifier source
```

`PROFILE_V2_DESIGN_SHA256` and `VERIFIER_SOURCE_SHA256` are external bindings, never self-references. Future Plan Task 0 binds the approved v2 Design SHA before source edits; Completion and Receipt Closure bind the final verifier source SHA after implementation.

The canonical future closure evidence path is:

```text
.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/<APPROVED_PROFILE_PLAN_SHA256>/evidence/receipt_closure_evidence.json
```

Only the independent Receipt Closure Auditor may create a canonical positive artifact at this path. Producer, domain loader, CLI, verifier, test, implementation executor, and Completion Audit may emit diagnostic facts but must not create, overwrite, or promote this positive closure artifact.

The evidence JSON has exactly this flat top-level key set; no nested object, omitted key, extra key, alias, or `null` is allowed:

```text
audited_config_relative_path
audited_config_sha256
domain_loader_expected_rc
domain_loader_observed_rc
evidence_status
governance_parent_design_relative_path
governance_parent_design_sha256
governance_rule17_j_b_v2_positive
j_b_compatibility_domain_delta_relative_path
j_b_compatibility_domain_delta_sha256
j_b_parent_design_relative_path
j_b_parent_design_sha256
j_b_rebind_delta_relative_path
j_b_rebind_delta_sha256
j_b_receipt_schema_authority_relative_path
j_b_receipt_schema_authority_sha256
j_b_profile_v2_design_relative_path
j_b_profile_v2_design_sha256
manifest_sha256
profile_contract_version
profile_id
receipt_root_relative_path
receipt_run_id
review_sha256
summary_sha256
verifier_expected_rc
verifier_observed_rc
verifier_relative_path
verifier_source_sha256
```

Every `*_relative_path` is a non-empty ASCII string and must equal its §2 literal or the actual sealed receipt root as applicable. Every `*_sha256`, `manifest_sha256`, `summary_sha256`, and `review_sha256` is a lowercase 64-hex ASCII string matching the named bytes. `profile_id` equals `stage1_5j_b_receipt_v2`; `profile_contract_version` is the non-bool integer `2`; both expected/observed RC pairs are non-bool integer `0`; `evidence_status` equals `receipt_closure_audited_positive`; and `governance_rule17_j_b_v2_positive` is boolean `true`. `receipt_run_id` is a non-empty ASCII string and must be the final component of `receipt_root_relative_path`.

Canonical evidence bytes are exactly `json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\\n"`. The sidecar bytes are exactly `<evidence_sha256><two ASCII spaces>receipt_closure_evidence.json\\n`, where `evidence_sha256` is the lowercase SHA-256 of those canonical JSON bytes. A missing, malformed, noncanonical, stale, non-auditor-produced, or tuple-mismatched evidence artifact is `STOP=governance_j_b_wrong_profile_evidence` and is not closure evidence.

---

## 3. v2 Structural Authority Contract

All v1 structural key-set, enum, sealed-tree, canonical JSON, row-relation, projection, and byte rules are copied as literal v2 verifier constants and checks. This is semantic inheritance from the immutable v1 Design, not runtime import or delegation. The only changed v2 authority rules are:

```text
summary.authority_packet.approved_j_b_design.relative_path
  = LATEST_J_B_DOMAIN_DESIGN_PATH

summary.authority_packet.approved_j_b_design.sha256
  = LATEST_J_B_DOMAIN_DESIGN_SHA256

summary.authority_packet.audited_config.relative_path
  = PROFILE_AUDITED_CONFIG_RELATIVE_PATH

summary.authority_packet.audited_config.sha256
  = PROFILE_AUDITED_CONFIG_SHA256
```

The v2 verifier returns RC `1` for any valid invocation whose receipt violates those literals, including an old `configs/base.py` config pair, a receipt that retains `approved_j_b_design = f108...`, a stale/missing config SHA, alias, or extra authority key. It does not open the workspace config module, does not parse receipt-generation authorization, and does not replace the J-B domain loader's current-disk/import/replay proof.

The J-B domain loader and v2 verifier remain complementary: the former validates actual stage-config disk/import authority and semantic replay; the latter validates the persisted authority pair and structural receipt grammar from literal independent constants.

---

## 4. v1/v2 Sibling Profile Evidence Semantics

`stage1_5j_b_receipt_v1` remains immutable. Its result on a future v2-governed receipt is non-authoritative regardless of RC.

Only this exact conjunction can be positive J-B governance closure evidence:

```text
profile_id = stage1_5j_b_receipt_v2
profile_contract_version = 2
approved profile-v2 Design path/SHA match §2
verifier path/source SHA match §2
domain loader actual RC = 0
v2 verifier actual RC = 0
closure evidence and sidecar match §2
```

Any profile-name mismatch, v1 result offered as v2 evidence, missing profile-v2 Design binding, or mismatched verifier/closure identity is:

```text
STOP=governance_j_b_wrong_profile_evidence
```

The v2 verifier itself returns RC `2` for unsupported/malformed profile invocation before receipt validation. It returns RC `1` only for a valid v2 invocation with a contract violation. A profile pass never grants receipt-generation, consumer, Alpha, network, replay, signal, paper/live, execution, deployment, commit, or push authority.

---

## 5. Acceptance Invariants And Failure Sequence

| ID | Invariant | Mechanical evidence |
| --- | --- | --- |
| `INV-GSI-JB-V2-01` | Only the §2 profile tuple identifies v2. | Task 0 approved-Design SHA binding plus closure evidence path/SHA. |
| `INV-GSI-JB-V2-02` | v2 verifier acceptance derives only from literal constants and artifact bytes. | AST/import-isolation test and synthetic sealed-tree mutations. |
| `INV-GSI-JB-V2-03` | `approved_j_b_design` is the Compatibility Domain Delta, not the prior Schema Authority Delta. | One-field receipt mutation returns RC `1`. |
| `INV-GSI-JB-V2-04` | `audited_config` is exactly the stage-local path/SHA. | Path or SHA mutation returns RC `1`. |
| `INV-GSI-JB-V2-05` | v1 evidence cannot close a v2 receipt. | Closure-audit wrong-profile probe returns `STOP=governance_j_b_wrong_profile_evidence`. |
| `INV-GSI-JB-V2-06` | v2 pass and J-B domain-loader pass are both required, without authority promotion. | Closure evidence binds both RCs and all flags remain false. |

Failure sequence is fixed:

```text
valid CLI/profile selection
-> literal v2 authority tuple
-> receipt envelope/sealed-tree/schema/relation checks
-> persisted latest-domain/config authority checks
-> verifier RC
-> closure evidence identity plus independent J-B domain-loader RC
```

No v1 fallback, profile auto-detection, profile alias, source import, or dynamic Design lookup is permitted.

---

## 6. Persistence, Fixture, Safety, And Future Verification

This Delta creates no artifact, does not change a receipt lifecycle, and requires no network or runtime action. The v2 verifier remains read-only. Synthetic J-B trees prove only verifier mechanics; the sole cross-boundary domain-positive fixture remains a receipt derived through public strict loading of the actual J-A replacement root and canonical J-B producer serialization.

Any future Plan may modify only the existing J-B verifier and its direct tests plus its dedicated `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/<APPROVED_PROFILE_PLAN_SHA256>/**` evidence tree. It must not modify v1, J-A, J-B domain producer/loader, data roots, or permissions under this Governance authority. Domain changes are owned by the separately approved Compatibility Domain Delta and its Plan.

Required v2 tests include exact profile literal assertions, v2 config path/SHA mutation, latest-domain Design path/SHA mutation, v1 invocation treated as non-authoritative closure evidence, unsupported profile RC `2`, verifier isolation, sealed-tree/schema mutations, and a proof that v2 verifier never opens workspace config bytes.

**L2 applicability:** N/A beyond preserving the parent's `exploratory_descriptive_only` state. This profile changes no hypothesis, sampling unit, outcome, cost, Alpha claim, or trading boundary.

**Blocking open questions:** None. This Delta establishes only independent governance authority required by the already-defined J-B config compatibility domain contract.
