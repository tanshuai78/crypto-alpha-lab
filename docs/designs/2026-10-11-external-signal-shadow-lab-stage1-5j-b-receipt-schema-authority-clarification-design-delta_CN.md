# Stage 1.5J-B Receipt Schema And Target-Stage Authority Clarification Design Delta

**日期:** 2026-10-11
**状态:** `draft_for_independent_review`
**父级 J-B Design:** `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md`
**父级 J-B Design SHA-256:** `ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b`
**上游 Rebind Delta:** `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md`
**上游 Rebind Delta SHA-256:** `0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c`
**目的:** 仅补全 J-B persistent receipt 的领域 schema 与 target-stage authority identity，使后续 Rule 17 profile 能机械验证已存在的 J-B receipt contract，而不自行创造领域语义。

---

## 1. Confirmed Facts

1. 父级 J-B Design 已冻结 final tree、顶层 summary keys、281/843/393 ledger cardinality、三条 horizon、J-A input/rebind、outcome formula、gap taxonomy、strict-loader semantic replay、atomic publication 和权限边界；它尚未冻结部分 receipt field 的完整 enum/type/nullability/identity relation。
2. Rebind Delta 已将唯一 J-A input 固定为 `20261010T163500Z` replacement receipt、`stage1_5j_a_receipt_v2` closure 及 `120/11/280/1/5` projection，但明确不改变 J-B receipt grammar、measurement 或 lifecycle owner。
3. 当前 J-A replacement summary 的 source parent states 是 `coverage_complete`、`coverage_evidence_gap_archive`、`coverage_evidence_gap_detail`、`coverage_evidence_gap_no_in_scope_usdt_child`；package states 是 `archive_verified_with_post_launch_rows`、`archive_verified_zero_post_launch_rows`、`archive_request_nonpersisted`。这是 J-B source-state projection 的唯一上游词表。
4. 当前不存在 J-B source、CLI、receipt、network authorization 或 final root。本 Delta 定义 future representation，不将 synthetic fixture、J-A root 或任何预期 outcome 视为 J-B positive evidence。

## 2. Assumptions

1. 未来 J-B producer 和 strict loader 均以 parent Design + Rebind Delta 规定的 full public J-A strict-load result为输入；它们不接受 caller-supplied parent/child dictionaries。
2. 未来 J-B target-stage Design authority 将由本 Delta 的 user-approved exact bytes 表示；其未来 implementation Plan、Core、CLI、Config 与 receipt-generation authorization 仍分别绑定，不由本 Delta 预先假设 SHA。
3. 本 Delta 只冻结持久化表示。其字段 literal 不改变 anchor selection、`required_j_b_dates`、physical order、Decimal calculation、gap reason、horizon、reducer、cardinality 或研究 claim。

## 3. Root Cause, Decision, Scope

### 3.1 Root cause

J-B parent receipt schema 已列出 `anchor_state`、`j_a_child_state`、`j_a_parent_state`、`source_parent_state` 及多个 numeric/container field，但没有将它们的完整值域、nullability 和跨 ledger relation 作为 persistence contract 冻结。若先实现 Governance verifier，producer 与 loader 仍可共同接受任意非空状态字符串或重复/遗漏 identity，并获得局部自洽 GREEN。

### 3.2 Decision

1. 本 Delta 成为 J-B receipt 的最新 target-stage domain Design authority。future `authority_packet.approved_j_b_design` 必须绑定本文件的 project-relative path 与 user-approved exact SHA；它不得绑定 Governance Rule 17 profile Design，且 `receipt_generation_authorization.APPROVED_J_B_DESIGN_SHA256` 必须与该 packet SHA 完全相同。
2. 以本 Delta 的 literal schema 约束补全 parent Design §4.2，所有未在本 Delta 覆写的 parent/Rebind clause 保持不变。
3. Governance Rule 17 profile 是独立 external authority：它将在本 Delta approved 后引用此 domain authority，但不替代 receipt-generation 的 J-B research/domain authorization。

### 3.3 Mutable Set

- 父级 J-B Design §4.2/§4.3 中 J-B receipt field grammar、J-B target-stage `approved_j_b_design` identity、以及 future loader/verifier 对这些 representation 的验证责任。

### 3.4 No-Touch Set

- J-A root、J-A v2 verifier/source identity、J-A profile、J-B upstream rebind tuple、`120/11/280/1/5` projection。
- J-B cohort、source independent unit、anchor/date/physical-order/tie-break rules、three horizons、Decimal arithmetic、gap taxonomy、281/843/393 cardinalities、publication/recovery/lifecycle owner、authority flags、network/trading/Alpha boundary。
- `scripts/governance/verify_artifact_schema.py`、其 tests、J-B source/CLI/tests、config、receipt and authorization files。

## 4. Exact Persistent Domain Contract

### 4.1 Shared scalar grammar

```text
SOURCE_ARTICLE_ID = lowercase 32-hex string: ^[0-9a-f]{32}$
SYMBOL = uppercase in-scope USDT symbol: ^[A-Z0-9]+USDT$
UTC_DATE = ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ and a calendar-valid UTC date
HORIZON_MS = one of 300000, 3600000, 14400000
J_B_RECEIPT_SCHEMA_AUTHORITY_PATH = docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md
POSITIVE_MS = non-bool integer > 0
NONNEGATIVE_MS = non-bool integer >= 0
CANONICAL_DECIMAL = a finite Decimal string without exponent, leading plus or redundant trailing zeros; zero is exactly "0"
CANONICAL_POSITIVE_DECIMAL = CANONICAL_DECIMAL whose Decimal value is > 0
CANONICAL_BPS = CANONICAL_DECIMAL quantized to 0.00000001 with ROUND_HALF_EVEN
CANONICAL_RATIO = CANONICAL_DECIMAL quantized to 0.00000001 with ROUND_HALF_EVEN and 0 <= Decimal value <= 1
```

`SOURCE_ARTICLE_ID` and `SYMBOL` are ASCII strings. Every persisted numeric string must parse through Python `Decimal`, be finite, and use the stated canonical serialization; bool is never an integer substitute.

The future target-stage authority bindings are exactly:

```text
authority_packet.approved_j_b_design.relative_path = J_B_RECEIPT_SCHEMA_AUTHORITY_PATH
authority_packet.approved_j_b_design.sha256 = user-approved exact SHA-256 of this Delta
receipt_generation_authorization.APPROVED_J_B_DESIGN_SHA256 = authority_packet.approved_j_b_design.sha256
```

Any path/SHA inequality is `STOP=stage1_5j_b_receipt_authority_mismatch`. This self-SHA is intentionally not written into the mutable candidate: it is frozen only by independent review plus the subsequent user approval of these exact bytes.

### 4.2 J-A source-state projection

`j_a_parent_state` and `source_parent_state` each use exactly this J-A parent enum:

```text
coverage_complete
coverage_evidence_gap_archive
coverage_evidence_gap_detail
coverage_evidence_gap_no_in_scope_usdt_child
```

For every `parent_horizon_rows` row, `source_parent_state` is the exact strict-loaded J-A parent record `parent_state` for its `source_article_id`. For every `child_rows` row, `j_a_parent_state` equals that same parent state.

`j_a_child_state` uses exactly:

```text
j_a_child_coverage_complete
j_a_child_coverage_gap
```

For a `(source_article_id,symbol)` child, it is `j_a_child_coverage_complete` iff its J-A archive-package-state collection is non-empty and every state is `archive_verified_with_post_launch_rows`; otherwise it is `j_a_child_coverage_gap`. A `coverage_complete` parent has only `j_a_child_coverage_complete` children. A `coverage_evidence_gap_archive` parent may have either child state. A `coverage_evidence_gap_detail` or `coverage_evidence_gap_no_in_scope_usdt_child` parent has no `child_rows` or `child_horizon_rows` identity.

### 4.3 `child_rows` exact state and nullability table

`child_rows` remains exactly the parent Design ten-key schema and sort order. Its `anchor_state` enum is exactly:

```text
anchor_found
anchor_unavailable_inherited_j_a_parent_gap
anchor_unavailable_delay_exceeded
```

The four anchor fields are `symbol_launch_time_ms`, `anchor_time_ms`, `anchor_delay_ms`, `anchor_price`. Their exact combinations are:

| `anchor_state` | `j_a_parent_state` | `symbol_launch_time_ms` | `anchor_time_ms` / `anchor_delay_ms` / `anchor_price` |
| --- | --- | --- | --- |
| `anchor_found` | `coverage_complete` | `POSITIVE_MS` | `POSITIVE_MS`, `NONNEGATIVE_MS <= EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS`, `CANONICAL_POSITIVE_DECIMAL` |
| `anchor_unavailable_inherited_j_a_parent_gap` | not `coverage_complete` | `POSITIVE_MS` or `null` | all `null` |
| `anchor_unavailable_delay_exceeded` | `coverage_complete` | `POSITIVE_MS` | `POSITIVE_MS`, `NONNEGATIVE_MS > EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS`, `CANONICAL_POSITIVE_DECIMAL` |

For `anchor_found` and `anchor_unavailable_delay_exceeded`, `anchor_time_ms >= symbol_launch_time_ms` and `anchor_delay_ms == anchor_time_ms - symbol_launch_time_ms`. For every non-null anchor time, price and delay, the selected row is the parent Design §3.3 first global physical row; no new selector is introduced. Under this exact Rebind/J-A admission, `coverage_complete + symbol_launch_time_ms=null` and `coverage_complete + no post-launch trade` are unreachable and illegal persistent representations: an upstream parent failure takes precedence and is represented only as `anchor_unavailable_inherited_j_a_parent_gap`.

`required_archive_dates_by_horizon` has exactly decimal-string keys `"300000"`, `"3600000"`, `"14400000"`. Each value is an ascending, duplicate-free array of `UTC_DATE`. It is all empty arrays iff `anchor_state` is not `anchor_found`; otherwise each array is non-empty and equals the parent Design §3.3 required-date calculation for that horizon.

### 4.4 `child_horizon_rows` exact state and nullability

Every row has exactly the parent Design thirteen keys. `(source_article_id,symbol)` must occur exactly once in `child_rows`; each such identity has exactly one row at each `HORIZON_MS`, ordered `(source_article_id,symbol,horizon_ms)`.

```text
child_horizon_state = child_horizon_complete | child_horizon_evidence_gap
missing_reason = null |
  inherited_j_a_parent_gap |
  evidence_gap_missing_launch_time |
  evidence_gap_anchor_delay |
  evidence_gap_missing_required_archive_package |
  evidence_gap_missing_horizon_trade
```

For `child_horizon_complete`, `missing_reason=null`; `horizon_price` is `CANONICAL_POSITIVE_DECIMAL`; `horizon_selected_time_ms` and `horizon_target_time_ms` are `POSITIVE_MS`; `horizon_offset_ms` is a non-bool integer in `[-EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS, 0]`; `gross_return_bps`, `sampled_min_excursion_bps` and `sampled_max_excursion_bps` are `CANONICAL_BPS`; `trade_count` is `POSITIVE_MS`. `horizon_ms`, `source_article_id`, `symbol` are always non-null identities.

For `child_horizon_evidence_gap`, `missing_reason` is one of the five listed non-null literals and all non-identity outcome fields are `null`: `horizon_offset_ms`, `horizon_price`, `horizon_selected_time_ms`, `horizon_target_time_ms`, `gross_return_bps`, `sampled_max_excursion_bps`, `sampled_min_excursion_bps`, `trade_count`. The required mapping from `anchor_state` to reason is fixed:

```text
anchor_unavailable_inherited_j_a_parent_gap -> inherited_j_a_parent_gap
anchor_unavailable_delay_exceeded             -> evidence_gap_anchor_delay
```

When `anchor_state=anchor_found`, only the parent Design §3.3 required-package check may produce `evidence_gap_missing_required_archive_package`; only the subsequent selected-horizon search may produce `evidence_gap_missing_horizon_trade`. `evidence_gap_missing_launch_time` remains a frozen parent gap-taxonomy literal, but is illegal under this exact admitted J-A input because the parent-state failure precedence resolves it before J-B child-row production.

### 4.5 `parent_horizon_rows` exact relation

Every row has exactly the parent Design eight keys. `parent_horizon_state` is exactly `parent_horizon_complete` or `parent_horizon_evidence_gap`. `(source_article_id,horizon_ms)` is unique; the complete identity set is the 131 strict-loaded J-A target parent identities cross the three `HORIZON_MS` values, hence 393 rows ordered `(source_article_id,horizon_ms)`.

`parent_horizon_complete` iff `source_parent_state=coverage_complete` and every matching child identity has `child_horizon_state=child_horizon_complete` at the same horizon. It then has non-null `parent_gross_return_bps`, `parent_sampled_min_excursion_bps`, `parent_sampled_max_excursion_bps` as `CANONICAL_BPS`, and `failed_child_reasons=[]`.

`parent_horizon_evidence_gap` has all three parent outcome fields `null`. If matching child rows exist, `failed_child_reasons` is the non-empty, duplicate-free, ASCII ordered list of exactly their `(symbol,missing_reason)` pairs whose child state is gap; every element has exactly `symbol` and `missing_reason`, with `SYMBOL` and a non-null §4.4 gap reason. If matching child rows do not exist because `source_parent_state` is `coverage_evidence_gap_detail` or `coverage_evidence_gap_no_in_scope_usdt_child`, the list is exactly one parent-gap sentinel:

```json
{"missing_reason":"inherited_j_a_parent_gap","symbol":null}
```

The `null` sentinel is only legal in that no-child condition and sorts before all string symbols. It does not create a child, symbol, new gap reason or new observation; it preserves the parent Design requirement that every parent gap be explicit and non-empty.

### 4.6 Coverage and distribution exact grammar

All four count maps in `coverage_counts` have exactly the three decimal-string horizon keys and non-bool non-negative integer values. `n_child_horizon_complete_by_horizon + n_child_horizon_gap_by_horizon = 281` for each horizon; `n_parent_horizon_complete_by_horizon + n_parent_horizon_gap_by_horizon = 131`; `n_parent_with_j_a_gap=11`, `j_a_parent_coverage_complete_count=120`, `j_a_parent_coverage_gap_count=11`, `j_a_target_parent_count=n_parent_total=131` as frozen by Rebind Delta.

`parent_distribution_by_horizon` has exactly the three horizon keys. Each value has exactly the fourteen parent Design keys. `n_complete_parent` is a non-bool integer in `[0,131]` and equals the corresponding complete-parent count. When it is zero, all nine percentile/statistic scalar fields are `null`, both contribution fields are canonical `"0"`, and both ID arrays are empty. Otherwise all nine statistic scalar fields are `CANONICAL_BPS`; `top_1_abs_return_contribution` and `top_3_abs_return_contribution` are `CANONICAL_RATIO`, with `0 <= top_1_abs_return_contribution <= top_3_abs_return_contribution <= 1`; `top_1_parent_ids` has `min(1,n_complete_parent)` unique `SOURCE_ARTICLE_ID`s and `top_3_parent_ids` has `min(3,n_complete_parent)` unique IDs, both in the parent Design §3.5 ranking order and drawn only from complete parent identities at that horizon.

## 5. Producer, Loader And Future Verifier Matrix

| Role | Required responsibility | Forbidden shortcut |
| --- | --- | --- |
| J-B producer | derive every row from full admitted J-A root; emit only §§4.1-4.6 grammar | free-form state string, omission/duplication, inferred fallback |
| J-B strict loader | independently strict-load J-A, reconstruct identity sets/reducer/render and reject any mismatch | trust producer summary or Governance verifier result |
| future Rule 17 J-B verifier | independently validate literal approved profile against sealed J-B artifact bytes | import J-B source/loader or define new domain enums |
| Receipt Closure Auditor | bind target-stage Design/Plan/Core/CLI/Config authority and run both validators | treat a synthetic fixture or one validator as closure |

## 6. Failure, Persistence, Compatibility And Recovery

Any enum/type/nullability/identity/relation mismatch is `STOP=stage1_5j_b_receipt_schema_mismatch` before a strict loader accepts the root. Existing parent failure precedence, flock, staging, fsync, rename, collision and no-resume behavior are unchanged. No migration or compatibility alias exists: a future receipt with a pre-Delta ambiguous representation is rejected, not normalized.

This Delta is documentation-only. It writes no root and creates no crash/recovery state. Future implementation must use the parent Design's four-state lifecycle and prove no final/staging state is accepted after a schema failure.

## 7. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| `INV-JB-SC-01` | `approved_j_b_design` names the latest approved J-B target-stage domain authority, never a Governance profile authority. |
| `INV-JB-SC-02` | All source/anchor/child-horizon/parent-horizon enums and conditional fields are exactly §§4.1-4.5. |
| `INV-JB-SC-03` | The 281 child, 843 child-horizon and 393 parent-horizon ledgers have complete unique Cartesian identity sets and cross-table source/symbol consistency. |
| `INV-JB-SC-04` | Every J-A source-state projection uses the strict-loaded J-A enum/relation in §4.2; no arbitrary pass-through state is accepted. |
| `INV-JB-SC-05` | Coverage/distribution count, scalar and ID-array forms are exactly §4.6 and preserve the Rebind projection. |
| `INV-JB-SC-06` | This schema clarification grants no implementation, receipt-generation, consumer, network, Alpha, replay, signal, paper/live trading, execution, deployment, commit or push authority. |

## 8. Evidence And Verification Strategy

The future Plan has two non-interchangeable fixture classes:

1. **Target J-B producer/strict-loader fixture:** derive only from the full public strict-loaded J-A replacement root through the canonical J-B producer/serializer. It is the only positive cross-boundary fixture and the only baseline for target producer/loader negatives. It must not be a hand-written J-A root, child/parent row, source state, authority packet or CSV.
2. **Governance verifier mechanics fixture:** an explicitly labeled synthetic sealed J-B structural tree. It may prove only independent verifier mechanics and must never prove J-B semantic replay, target-stage authority, cross-boundary positivity or receipt closure.

Target producer/loader negative probes mutate exactly one declared fact from the first fixture: every legal enum literal branch; every conditional nullability branch; a zero archive-package-state collection; duplicate/missing child identity; duplicate/missing child-horizon identity; duplicate/missing parent-horizon identity; child/parent source mismatch; an invalid source ID/symbol/date/Decimal; one map key; one distribution scalar/ID-array relation; and `approved_j_b_design` rebound to a Governance profile path. Each must reach the target producer/loader schema gate, not an earlier manifest/hash gate.

The future independent Rule 17 verifier profile must reproduce these literal schema checks without importing J-B source. Its mechanics-fixture mutations remain confined to that verifier boundary. Completion and receipt closure must record actual test, Ruff, scanner and validator process RCs.

## 9. Safety, Research Boundary And Rollout

This is deterministic receipt-schema work, not an Alpha study. The following are `N/A`: phenomenon support, statistical/economic edge, outcome distribution conclusion, cost/friction, capacity, MAE/tail claim, strategy promotion/kill and execution feasibility. `RISK_LIVE_TRADING_ENABLED` remains `False`; all J-B authority flags remain false.

Rollout/rollback is `N/A`: no code, deployment, root, profile implementation or runtime action is authorized. If a future implementation cannot meet this exact schema, it must stop rather than publish or reinterpret an ambiguous receipt.

## 10. Open Questions And Routing

Open Questions: none affecting implementation after this Delta is reviewed and explicitly approved. Future receipt-specific run ID/hashes, implementation Plan SHA, verifier source SHA and receipt-generation authorization remain intentionally unknown until their separate authorized lifecycle stages; they are not schema ambiguities and cannot be guessed here.

Next route: independent review of this narrow target-stage Delta. Only after user approval may the Governance J-B Rule 17 Profile Delta be revised to reference this approved domain authority, use a separate new J-B verifier, preserve J-A v2 verifier bytes, and limit its Markdown check to byte/tree integrity.
