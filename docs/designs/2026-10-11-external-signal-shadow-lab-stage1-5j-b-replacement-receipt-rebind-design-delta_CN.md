# Stage 1.5J-B Historical `aggTrades` Launch Anchor And Price Response Exploratory Design: Replacement-Receipt Rebind Delta

**日期:** 2026-10-11  
**状态:** `draft_for_independent_review`  
**父级 Design:** `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md`  
**父级 Design SHA-256:** `ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b`  
**上游治理 Profile Delta:** `docs/designs/2026-10-11-governance-stage1-5j-a-replacement-receipt-profile-v2-design-delta_CN.md`  
**上游治理 Profile Delta SHA-256:** `1d3155c8a38e53f851aaa0f51c8c2ec6ef6aaaf811e4330d8b1c0a491796a86b`  
**目的:** 将 J-B 唯一上游 J-A 输入从旧 receipt 重新绑定到已通过 J-A domain strict loader 与 Rule 17 `stage1_5j_a_receipt_v2` 独立验证的 replacement receipt，并同步全部由该输入决定的数值投影。

---

## 0. Delta Authority And Non-Authorization

本 Delta 仅覆盖父级 Design 的 J-A input identity、J-A governance closure evidence、由 J-A coverage inventory 直接导出的 projection literals、`j_a_input` persistent binding、以及引用这些 literals 的 reducer/evidence packet。除本 Delta 明确覆写处外，父级 Design 保持原样。

本 Delta 不授权 implementation、commit、push、deployment、network、receipt generation、J-B consumption、replay、signal、paper trading、live trading 或 execution action。它不构成 Alpha、统计优势、经济优势、可执行性或交易可行性结论。

**Mutable Set:** 父级 Design §1.1、§2.1 中的上游 J-A identity/projection，§4.2 的 `j_a_input` exact schema 与 J-B state reducer literal，§9 的上游 gap 数，§10 的 external evidence packet 和 routing。  
**No-Touch Set:** J-B 的 observation cohort、独立样本单位、anchor/tie-break、`required_j_b_dates`、5m/1h/4h horizons、Decimal/price arithmetic、gap taxonomy、281/843/393 row cardinalities、J-B receipt lifecycle/tree grammar、output authority flags、发布/网络/trading boundary。

---

## 1. Rebound J-A Receipt Authority

### 1.1 Exact replacement root and four top-level artifacts

父级 Design 中 `20261007T091336Z` root 及其所有 top-level artifact hashes 不再是 J-B 可接受输入。J-B 的唯一可准入 J-A root 是：

```text
J_A_RUN_ID = stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
J_A_ROOT_RELATIVE_PATH = data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
J_A_MANIFEST_SHA256 = b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf
J_A_SUMMARY_SHA256 = 722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b
J_A_REVIEW_SHA256 = 1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152
J_A_REQUEST_JOURNAL_SHA256 = b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa
```

J-A domain source identity is also immutable:

```text
J_A_CORE_PATH = src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py
J_A_CORE_SHA256 = 250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18
J_A_REMEDIATION_PLAN_PATH = docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan-r1_CN.md
J_A_REMEDIATION_PLAN_SHA256 = b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82
```

Any old root, different RUN_ID, artifact hash, source identity, missing file, symlink, additional sealed-tree member, or authority mismatch is a fail-closed `STOP=stage1_5j_b_upstream_authority_mismatch`. No compatibility branch, migration, copy/rewrite of an old root, or fallback root is permitted.

### 1.2 Required Rule 17 v2 governance-closure binding

The replacement root is admissible only together with this exact final, canonical governance closure evidence tuple:

```text
J_A_GOVERNANCE_CLOSURE_EVIDENCE_PATH = .git/plan-execution/governance_artifact_schema/ba362f2480c7872d39eede9254744d6e99216aa73134777658f9f81f05ba7881/evidence/v2_receipt_closure_evidence.json
J_A_GOVERNANCE_CLOSURE_EVIDENCE_SHA256 = c0810b95dc94c740dbc41d55ce01d51d1bd7a09e382b292e156d2522d621e68b
J_A_GOVERNANCE_PROFILE_ID = stage1_5j_a_receipt_v2
J_A_GOVERNANCE_PROFILE_CONTRACT_VERSION = 2
J_A_GOVERNANCE_VERIFIER_PATH = scripts/governance/verify_artifact_schema.py
J_A_GOVERNANCE_VERIFIER_SHA256 = 7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473
J_A_GOVERNANCE_EVIDENCE_STATUS = receipt_closure_audited_positive
J_A_GOVERNANCE_RULE17_V2_POSITIVE = true
```

The evidence JSON and its `.sha256` sidecar must be regular contained files, have exactly the frozen canonical evidence hash, and bind the same run ID, root path, four artifact hashes, profile ID/version, verifier path/hash, observed verifier RC `0`, and observed J-A strict-loader RC `0`. A missing, noncanonical, stale, or internally inconsistent tuple is `STOP=stage1_5j_b_upstream_governance_evidence_invalid` before J-B reads a J-A raw package.

J-B producer and strict loader independently validate this evidence tuple, J-A core source identity, four root artifacts, and J-A domain strict-loader result. Rule 17's independent verifier remains a separate audit boundary: J-B source must not import the verifier script or treat its implementation as a producer-side fallback. The J-B Plan and Completion/Receipt Closure Audits must run the exact verifier CLI with `--profile stage1_5j_a_receipt_v2` against the exact root, record its actual RC, and bind its source SHA; a verifier pass alone never grants J-B generation or consumption authority.

---

## 2. Rebound Coverage Projection

### 2.1 Exact projection literals

Before any anchor, archive-date, trade-row, horizon, or J-B reducer work, the strict-loaded J-A `coverage_inventory` projection must exactly equal this table:

| Field | Frozen value |
| --- | ---: |
| `catalog_denominator_count` | 335 |
| `target_parent_count` | 131 |
| `resolved_parent_count` | 125 |
| `parent_coverage_complete_count` | 120 |
| `parent_coverage_gap_count` | 11 |
| `in_scope_usdt_child_count` | 281 |
| `child_coverage_complete_count` | 280 |
| `child_coverage_gap_count` | 1 |
| `out_of_scope_child_count` | 5 |

The J-A `analysis_state` must be `coverage_inventory_evidence_gap`, and `decision` must be `stage1_5j_a_historical_archive_coverage_evidence_gap_published`. The sole child coverage gap is evidence, not a permission to remove a J-A parent/child from J-B's complete 131-parent ledger.

Any mismatch is `STOP=stage1_5j_b_upstream_projection_mismatch`. J-B must not preserve stale literals (`118`, `13`, `278`, `3`), derive an alternate denominator, or silently omit `out_of_scope_child_count` merely because it does not produce a J-B child row.

### 2.2 Directly superseded parent clauses

This Delta supersedes only the following parent statements:

| Parent clause | Replacement rule |
| --- | --- |
| §1.1 old root/hashes/core identity | §1.1 and §1.2 of this Delta are the only admissible upstream authority tuple. |
| §1.1/§2.1 old projection `118` complete / `13` gap | Use §2.1's `120` complete / `11` gap projection. |
| §1.1 old child projection `278` complete / `3` gap | Use §2.1's `280` complete / `1` gap projection. |
| §1.1 omitted `out_of_scope_child_count` | Independently assert §2.1's value `5`. |
| §4.2 `analysis_state` reducer requiring all 118 frozen complete parents | Require all 120 frozen J-A complete parents to have all three `parent_horizon_complete` rows. |
| §9 deferred repair of 13 J-A gaps | The deferred upstream provenance question concerns 11 J-A parent coverage gaps. |
| §10 external packet/routing | Apply §5 of this Delta. |

All other parent clauses, especially the 281 child rows, 843 child-horizon rows, 393 parent-horizon rows, and the research-method contract, are unchanged.

---

## 3. Persistent J-B Input Binding And Reducer

### 3.1 `j_a_input` exact key set

Parent §4.2's `j_a_input` key set is replaced by exactly these 16 keys, with no omission and no extra key:

```text
j_a_core_path,
j_a_core_sha256,
j_a_governance_closure_evidence_relative_path,
j_a_governance_closure_evidence_sha256,
j_a_governance_evidence_status,
j_a_governance_profile_contract_version,
j_a_governance_profile_id,
j_a_governance_rule17_v2_positive,
j_a_governance_verifier_relative_path,
j_a_governance_verifier_sha256,
j_a_journal_sha256,
j_a_manifest_sha256,
j_a_root_relative_path,
j_a_review_sha256,
j_a_run_id,
j_a_summary_sha256
```

Every value is the corresponding literal in §1. A J-B producer persists these values only after §1 and §2 admit the source; a J-B strict loader recomputes and compares them before accepting the receipt. Missing, extra, non-literal, or mismatched fields are `STOP=stage1_5j_b_j_a_input_mismatch`.

The existing `authority_packet` grammar remains unchanged. These input-binding fields belong in `j_a_input`, because they identify the persistent upstream receipt and its independent governance closure rather than J-B's own generation authorization.

### 3.2 Coverage-count and state-reducer changes

`coverage_counts.j_a_parent_coverage_complete_count` is exactly `120`; `coverage_counts.j_a_parent_coverage_gap_count`, `coverage_counts.n_parent_with_j_a_gap` are exactly `11`; and `coverage_counts.j_a_target_parent_count`, `coverage_counts.n_parent_total` are exactly `131`.

`analysis_state=exploratory_response_described` iff all **120** frozen J-A complete parents have `parent_horizon_complete` at each of the three unchanged horizons. Otherwise it is `exploratory_response_evidence_gap`. The paired decision remains the parent Design's same two enumerated literals. This is only an upstream projection rebind: it does not convert any response, price return, distribution, concentration statistic, or gap to Alpha evidence.

---

## 4. Invariants And Fail-Closed Admission Order

| ID | Acceptance invariant |
| --- | --- |
| `INV-JB-RB-01` | Only the replacement root and four top-level artifact hashes in §1.1 are admissible. |
| `INV-JB-RB-02` | J-B admission requires the exact positive Rule 17 v2 closure tuple in §1.2; historical v1 evidence and profile-name-only claims are insufficient. |
| `INV-JB-RB-03` | The strict-loaded J-A projection equals all nine values in §2.1, including `120/11/280/1/5`. |
| `INV-JB-RB-04` | A generated J-B receipt persists the complete exact `j_a_input` key set in §3.1, and its loader independently verifies it. |
| `INV-JB-RB-05` | J-B's existing 131-parent ledger, 281 child rows, 843 child horizons, 393 parent horizons, three horizons, and explicit evidence gaps stay unchanged. |
| `INV-JB-RB-06` | Neither J-A domain-loader pass nor Rule 17 verifier pass alone grants J-B receipt-generation, downstream-consumption, Alpha, or trading authority. |

Admission order is fixed: containment/no-symlink/regular-file checks; closure-evidence sidecar and canonical hash; §1.2 closure tuple; exact J-A core source identity; public J-A strict-loader success; four top-level artifact hashes; §2.1 projection; only then J-A raw package access and J-B computation. A failure never produces a partial J-B root, alternate projection, or fallback to the old receipt.

---

## 5. Required Future Verification And Review Packet

### 5.1 Positive and negative proof obligations

A future J-B Plan must derive its sole positive fixture from the full §1.1 root only after public J-A strict loading and §1.2/§2.1 verification. It must not use a hand-written root, copied authority packet, cropped tree, or old v1 governance claim as a positive fixture.

Required negative probes each mutate one declared boundary fact and must reach the named gate:

| Mutation | Required result |
| --- | --- |
| old `20261007T091336Z` root or any different RUN_ID | `STOP=stage1_5j_b_upstream_authority_mismatch` |
| one of four §1.1 artifact hashes | `STOP=stage1_5j_b_upstream_authority_mismatch` |
| closure evidence/profile/version/verifier SHA/status/positive flag/sidecar | `STOP=stage1_5j_b_upstream_governance_evidence_invalid` |
| `parent_coverage_complete_count: 120 -> 118` | `STOP=stage1_5j_b_upstream_projection_mismatch` |
| `parent_coverage_gap_count: 11 -> 13` | `STOP=stage1_5j_b_upstream_projection_mismatch` |
| `child_coverage_complete_count: 280 -> 278` | `STOP=stage1_5j_b_upstream_projection_mismatch` |
| `child_coverage_gap_count: 1 -> 3` | `STOP=stage1_5j_b_upstream_projection_mismatch` |
| `out_of_scope_child_count: 5 -> 0` | `STOP=stage1_5j_b_upstream_projection_mismatch` |
| one persisted §3.1 `j_a_input` key/value | `STOP=stage1_5j_b_j_a_input_mismatch` |

Completion and receipt-closure audits must separately run the independent verifier exactly as specified in §1.2, record its profile ID/version, verifier source SHA, root identity, four top-level artifact hashes, and actual RC. That audit may not substitute the target J-B producer or loader for the independent verifier.

### 5.2 Minimal external review packet

An independent reviewer must receive exact bytes of: this Delta and parent J-B Design; the v2 governance Profile Delta; v2 closure evidence JSON and sidecar; the four §1.1 root artifacts; J-A core; the exact verifier source; and the final J-A domain receipt-closure audit plus its correction supplement. Missing any listed byte is `EVIDENCE_GAP`, not a positive upstream admission claim.

---

## 6. Research Boundary And Routing

The new `120/11/280/1/5` values are deterministic data-coverage projections. They do not alter J-B's descriptive `aggTrades` anchor/response method, constitute no effect-size observation, and provide no Alpha, statistical, economic, execution, liquidity, slippage, fee, funding, paper, or live-trading evidence.

This Design requires a new Implementation Plan and independent review before any J-B source, test, receipt, or runtime action. That Plan must retain the parent Design's no-network input boundary and must not authorize J-A re-capture, J-B raw-data download, J-B receipt generation, or downstream J-B consumption merely by implementing this rebind.
