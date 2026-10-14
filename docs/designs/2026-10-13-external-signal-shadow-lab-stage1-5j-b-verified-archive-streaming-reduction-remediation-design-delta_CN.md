# Stage 1.5J-B Verified Archive Streaming Reduction Remediation Design Delta

**日期:** 2026-10-13
**状态:** `draft_for_independent_review`
**父级 J-B Design:** `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md`
**父级 J-B Design SHA-256:** `ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b`
**J-B Replacement Receipt Rebind Delta:** `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md`
**Rebind Delta SHA-256:** `0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c`
**J-B Receipt Schema Authority Delta:** `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md`
**Receipt Schema Authority Delta SHA-256:** `f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25`
**最新 J-B Compatibility Domain Delta:** `docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md`
**Compatibility Domain Delta SHA-256:** `66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f`
**当前 Governance Rule 17 v2 Design:** `docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md`
**Governance Rule 17 v2 Design SHA-256:** `8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454`
**已完成但发生语义漂移的 Plan:** `docs/plans/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-domain-implementation-plan_CN.md`
**Plan SHA-256:** `ec5fbc3beeafd47ec42cdf12481751f41424fe3351a6c14845ebc0e5d5a8a319`

**目的:** 修复 J-B 已批准但未进入正式 producer/strict-loader 路径的 verified ZIP/CSV 流式归约。新 J-B receipt 必须从已由 J-A 严格准入的 raw archive bytes 重放 anchor、horizon、Decimal outcome 与 parent reducer；不得把尚未读取原始成交的状态编码为市场数据缺失。

## 0. Delta Authority And Non-Authorization

本 Delta 只处理 J-B raw archive reduction 的 domain semantic gap 及其直接治理身份后果。它不创建 Stage 1.5J-C，不修改 J-A，不重定义 J-B 的 horizon、Decimal、parent-cluster、资源限制或研究边界。

### 0.1 Frozen authority chain and precedence

| Authority | Exact path | SHA-256 | Owns |
| --- | --- | --- | --- |
| Parent J-B Design | `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md` | `ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b` | J-B descriptive problem, horizons, raw archive measurement contract, resource bounds and research boundary. |
| J-B Rebind Delta | `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md` | `0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c` | Exact J-A root, J-A v2 closure tuple, four artifact hashes and `335/131/125/120/11/281/280/1/5` projection. |
| J-B Schema Authority Delta | `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md` | `f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25` | Exact row grammar, reachability/nullability, `281/843/393` identities and parent reducer relations. |
| Compatibility Domain Delta | `docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md` | `66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f` | Stage-local config path/SHA and the exact nine offline constants. |
| Governance Rule 17 v2 Design | `docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md` | `8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454` | Frozen v2 structural profile only; it cannot close this Delta's raw-reduction claim. |
| This Remediation Delta | this file | user-approved exact SHA-256 after independent review | Only raw-reduction semantic remediation and legacy-root admissibility; it does not replace the persistent J-B domain-design identity. |

This Delta does not replace any other authority's owned contract. In particular, Rebind remains authoritative for J-A identity and admission facts; Schema Authority remains authoritative for persisted grammar/reachability; Compatibility remains authoritative for config identity. A conflict is `STOP=stage1_5j_b_remediation_authority_conflict`, never an implementation choice.

本 Delta 不授权 implementation、commit、push、deployment、SSH、network、receipt generation、J-B consumer、strategy/simulator replay、signal、PnL、paper trading、live trading、execution 或 Alpha claim。任何后续实现、单次新 receipt generation 与 closure audit 都需要各自的显式授权。

**Mutable Set for a future approved Plan:**

```text
src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py
tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py
tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py
scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py
.git/plan-execution/stage1_5j_b/<APPROVED_REMEDIATION_PLAN_SHA256>/**
```

Existing Rule 17 v2 verifier/test bytes are No-Touch under this Delta. The approved remediation Plan must use the existing v2 verifier as the independent structural boundary; this Delta does not authorize profile, verifier or v2 evidence-schema changes.

**No-Touch Set:** J-A core/root/raw bytes/authority packet/public strict loader/Rule 17 verifier/tests/closure evidence；所有已提交的 J-B parent/Rebind/Compatibility/v1/v2 Design 和 Plan bytes；`configs/base.py`；J-B stage-local config 的九个精确常量；现有 J-B `20261013T000000Z` 与 `20261013T040000Z` roots；现有 closure evidence；风险、策略、执行、VPS 与网络 collector；全部 12 项 J-B false authority flags；`RISK_LIVE_TRADING_ENABLED=False`。

## 1. Confirmed Facts And Root Cause

1. 父级 J-B Design 已冻结：J-B 必须在 exact J-A strict admission 后，对 J-A manifest 所列的 verified ZIP/`.CHECKSUM` 逐包流式读取 CSV，并以 physical order、`Decimal`、anchor/horizon/tie-break 与 parent median reducer 得出描述性 outcome。
2. 当前 J-A replacement root 的 `archive_package_records` 含 280 个 `archive_verified_with_post_launch_rows` in-scope children；raw archive ZIP 和 `.CHECKSUM` 均保存在 sealed J-A root 中。它们是本 Delta 的唯一 raw input；不得补抓、替换、拼接或重新 inventory。
3. 当前 J-B core 已定义 `validate_zip_archive_package`、CSV header、anchor/horizon selector 与 Decimal outcome helper，但 canonical producer 未调用它们来构造 receipt。
4. 当前 producer 对 J-A `coverage_complete` parent 的 child 固定写 `anchor_state="evidence_gap"`，将所有 child horizon 固定写为 `child_horizon_evidence_gap`，并把每个 horizon 的 `complete` count 固定为 `0`。这不是由原始 ZIP/CSV replay 得出的事实。
5. 当前 `stage1_5j_b_historical_aggtrades_launch_response_20261013T040000Z` 因此只有结构、sealed-tree、authority tuple 与 fail-closed evidence-gapped state 的历史记录价值；它不满足本 Delta 所需的 verified archive reduction positive path，也不得作为后续 consumer、价格结果、Alpha 或执行证据。
6. Rule 17 v2 的独立 verifier 按其批准边界只验证 receipt bytes 的 profile/schema/relation。它不能读取 J-A raw archive 来证明 J-B 已重放成交数据；v2 PASS 不可被误读为 raw-reduction correctness PASS。

**根因分类:** `BLOCKED_IMPLEMENTATION_DEFECT`。父级 Design 已定义需要的 input、算法、resource caps 与 fail-closed states；当前正式 producer/loader 接线漏掉该已批准路径。不得以新 J-C、synthetic CSV、默认 gap 或新网络来源绕过。

## 2. Scope And Explicit Non-Goals

### 2.1 In scope

1. 从 J-A public strict loader 的 exact returned projection 导出每个 logical archive identity，并将 identity 绑定到 J-A persisted `request_records`、`archive_package_records`、manifest-listed ZIP 与 `.CHECKSUM` bytes。
2. 对每个 J-A `coverage_complete` parent 下的 in-scope child，按 §3.2 的 frozen reducer 流式读取 required verified package；计算 anchor、三个 horizon、trade count、min/max excursion、gross return、parent equal-child median、distribution 与 concentration fields。
3. 对 parent gap、valid anchor delay、缺 required date package、无 horizon trade 的唯一可达原因产生 exact gap state；不得把 upstream contradiction、structural corruption 或“未执行 archive replay”编码为任一 evidence gap。
4. J-B strict loader 必须从 J-A raw bytes 独立重演并逐字段比较 persisted child/horizon/parent/reducer/review projection；它不得只验证枚举、nullability 或 J-A summary projection。
5. Preserve the existing `stage1_5j_b_receipt_v2` persistent-contract identity while binding this Delta as an external semantic-remediation provenance authority in the approved remediation Plan, Completion Audit, receipt-generation authorization's approved Plan binding and Receipt Closure Audit report.

### 2.2 Explicit non-goals

- 不新增名为 J-C 的重复 ZIP decompressor/replay stage。该 raw-reduction responsibility 已属于 J-B；J-C 只有在未来拥有不重叠的已批准问题、输入与输出后才可提案。
- 不更改 J-A universe、archive request、availability、package bytes、raw path、checksum、loader 或 J-A Rule 17 profile；不网络补抓。
- 不更改 J-B 5m/1h/4h horizons、60s lookback、300s anchor delay、Decimal quantization、resource caps、parent independent unit 或统计定义。
- 不把 `gross_return_bps` 解释为 PnL，不计算 fee/funding/slippage/borrow/mark price/bid-ask，不生成 signal、entry/exit、sizing、paper/live/execution 或 Alpha conclusion。
- 不修补、删除、覆盖、重新标记或重用两个旧 J-B roots；新 producer 必须只接受新的 authorized `RUN_ID`。

## 3. Verified Archive Reduction Contract

### 3.1 Admission and package provenance

Producer 与 strict loader 必须各自按下列顺序完成 raw-open gate；任何失败保留上游 named `STOP`，在 `ZipFile.open()` 前终止，且不得产生 partial J-B root：

```text
exact J-A root containment / regular-file / no-symlink
-> J-A v2 closure-evidence JSON + unique .sha256 sidecar
-> exact Rebind J-A v2 tuple (profile/version/evidence status/positive flag/verifier path+SHA)
-> actual `verify_artifact_schema.py --profile stage1_5j_a_receipt_v2` RC=0
-> exact J-A Core identity
-> exact J-A public strict-loader PASS
-> four Rebind top-level artifact hashes
-> exact Rebind projection 335/131/125/120/11/281/280/1/5
-> persisted logical package identity
-> only then ZipFile.open()
```

Plan, Completion Audit and Receipt Closure Audit must independently run that exact J-A verifier CLI against the exact J-A root, record its actual process RC and bind verifier source SHA. The producer/loader must validate the evidence tuple but must not import the verifier script as a runtime fallback.

对每个 J-B child/horizon，唯一允许的 package source 为 J-A returned records 中完全匹配：

```text
(parent_article_id, symbol, utc_date, "aggTrades", "futures_um")
```

的 logical identity。ZIP 与 `.CHECKSUM` path 必须由该 identity 的 persisted J-A request/manifest relation 解析并在 sealed J-A root 下验证；不得根据 symbol/date 自行构造未被 J-A persisted bytes 证明的替代 input。path escape、symlink、缺成员、extra member、size/hash/checksum mismatch、ZIP member count/header/encoding/CSV grammar/numeric violation 都是 structural `STOP`，不是 evidence gap。

### 3.2 Streaming calculation

每次只允许打开一个 verified ZIP member，并使用 `ZipFile.open()`、受 `EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES` 限制的 text/CSV iterator。禁止 `ZipFile.read()`、`extract()`、whole-file read、保留 raw trades、并发处理多个 package，或把 raw row 写入 J-B final root。

The following are inherited from the parent J-B Design's measurement clauses; the explicit same-timestamp statements are this Delta's clarification of the parent contract, not new measurement freedom.

1. Package order is ascending required `utc_date`; within each package, physical order is the header-following 1-based CSV row order. `transact_time` must be nondecreasing in that physical order. `agg_trade_id` must not reorder a stream.
2. `price` and `quantity` are parsed only from UTF-8 tokens as finite positive `Decimal`; every persisted decimal is quantized and serialized exactly to the parent's `0.00000001` round-half-even canonical form.
3. The anchor-search universe is the verified global physical stream over exactly the J-A persisted logical identities needed from launch through the largest horizon. The anchor is the earliest physical row with `transact_time >= launch_time`; equal timestamps choose the earliest physical row. It is usable only when `anchor_time_ms - launch_time_ms <= 300000`.
4. For each horizon, required UTC dates are the parent Design's UTC-date calculation over the actual anchor target interval. The persisted date list is ascending and duplicate-free. A missing required logical package has the exact required-package gap and ends that horizon's search.
5. The target is `anchor_time_ms + horizon_ms`. Search the closed interval `[target_time_ms - 60000, target_time_ms]`; choose the latest physical row in that interval, so equal timestamps choose the latest physical row. No selected row has the exact missing-horizon-trade gap.
6. A complete horizon computes trade count, price extrema and gross return from the closed physical-row interval from the selected anchor through the selected horizon row, inclusive. Min/max include both endpoints.
7. `parent_horizon_complete` iff the source parent is `coverage_complete` and **every** matching in-scope child is `child_horizon_complete` at that horizon. Only then is every parent outcome the equal-child simple median over all child outcomes. If any child is gap, every parent outcome field is null; taking a median over remaining complete children is forbidden.

### 3.3 State reachability matrix

| Upstream/J-B condition | Required result |
| --- | --- |
| Parent is not `coverage_complete` | `inherited_j_a_parent_gap`; do not open child raw package. |
| `coverage_complete` with missing launch time | `STOP=stage1_5j_b_upstream_projection_schema_contradiction`; the Schema Authority makes this representation unreachable. |
| `coverage_complete` with no post-launch trade where Schema Authority makes it unreachable | `STOP=stage1_5j_b_upstream_projection_schema_contradiction`; do not create a J-B gap. |
| Valid anchor candidate exists but delay exceeds `300000` ms | `anchor_unavailable_delay_exceeded` and `evidence_gap_anchor_delay`. |
| A required logical date has no J-A verified package | `evidence_gap_missing_required_archive_package`. |
| Required verified packages exist, but the closed horizon window has no trade | `evidence_gap_missing_horizon_trade`. |
| ZIP/hash/checksum/member/header/encoding/timestamp/numeric/CSV parser corruption | Structural named `STOP`; never evidence gap. |
| Required raw stream was never executed | `STOP=stage1_5j_b_raw_reduction_not_executed`; implementation defect, never evidence gap. |

### 3.4 Outcome, shared TCB and loader replay

`child_horizon_complete` 仅可在实际 raw replay 成功后出现，且所有 outcome fields non-null、`missing_reason=null`。`child_horizon_evidence_gap` 的 outcome fields 必须全为 null，且 reason 必须是 §3.2 唯一可达原因。完整 parent 和 distribution fields 只能从 complete child outcomes 得出；不得以 `0`、空数组或 null 替代一次本应执行的 reducer。

The shared production trusted-computing base is exactly `raw-stream parser + deterministic reduction kernel`. The producer flows `admitted raw bytes -> shared TCB -> persisted receipt`. The strict loader independently reopens the admitted raw bytes, runs that same TCB, and compares every persisted child/horizon/parent row, coverage count, distribution and rendered review projection. It cannot call the Rule 17 verifier, trust persisted outcomes, or use producer precomputed output as its replay oracle. Any difference is named J-B `STOP`.

The required independent semantic test oracle must not import or call the production reduction kernel. It independently calculates anchor/horizon selection, inclusive counts/extrema, Decimal serialization, parent median and distribution from the canonical raw fixture. Its PASS, canonical fixture identity and oracle source SHA are mandatory closure evidence; producer-loader dual PASS alone is insufficient.

## 4. Legacy Root And Governance Identity

### 4.1 Legacy-root handling

下列历史 roots immutable、不得删除或覆盖：

```text
stage1_5j_b_historical_aggtrades_launch_response_20261013T000000Z
stage1_5j_b_historical_aggtrades_launch_response_20261013T040000Z
```

它们在本 Delta 后均标记为 `legacy_not_admissible_for_verified_archive_reduction`：可保留诊断、结构审计和缺陷溯源价值，但不能作为 J-B raw-reduction positive input、future consumer input 或本 Delta 的 closure baseline。新 producer 必须拒绝任何旧 `RUN_ID`、final-only overwrite、staging reuse 或 legacy authorization。

### 4.2 Existing Rule 17 v2 profile remains authoritative

This remediation changes whether J-B producer/loader actually conform to the already frozen raw-reduction semantics; it does **not** change the persistent receipt contract. The following remain exactly unchanged: the `281/843/393` identity cardinalities, key sets, enum literals, conditional nullability, canonical JSON, sealed-tree rules, `authority_packet` grammar, authority flags, structural relations, and independent verifier trust boundary.

Therefore new remediation receipts remain `profile_id=stage1_5j_b_receipt_v2` and must retain the v2 literal persistent authority pair:

```text
summary.authority_packet.approved_j_b_design
  = Compatibility Domain Delta path/SHA
summary.authority_packet.audited_config
  = Compatibility-frozen stage-local config path/SHA
```

This Delta's exact SHA is bound outside the persisted v2 receipt grammar:

1. The remediation Implementation Plan binds this Delta's exact path/SHA and the current v2 Design/verifier identity.
2. The fixed eight-key receipt-generation authorization continues to bind `APPROVED_J_B_PLAN_SHA256`; that approved Plan is the transitive exact authorization for this Delta. No authorization key is added, removed or aliased.
3. Completion Audit and the Receipt Closure Audit report bind this Delta, the approved Plan, Core SHA, CLI SHA, exact inherited stage-config path/SHA, independent semantic-oracle evidence, and the v2 closure-evidence tuple. The canonical v2 `receipt_closure_evidence.json` retains its existing exact key set and receives no remediation alias or extra field.

Only a future change to a persisted receipt key set, enum, nullability, cardinality, canonical serialization, sealed-tree rule, `authority_packet` grammar, structural relation, or verifier trust boundary may require a new Rule 17 profile version. No v3 Design, verifier, evidence tree or mutable Governance scope is authorized by this Delta.

## 5. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| INV-JB-RR-01 | 只有 exact admitted J-A root 的 persisted logical package identity、manifest-listed ZIP 和 `.CHECKSUM` 可作为 J-B raw input；无 fallback、重建 path 或网络。 |
| INV-JB-RR-02 | J-A `coverage_complete` child 不得因 producer 未读取 package 而被写成 `evidence_gap`；每个 gap 必须有 §3.2 机械可重演的唯一原因。 |
| INV-JB-RR-03 | package parser、physical order、anchor、required dates、horizon selector、tie-break、Decimal math 与 serialization 严格遵从 §3.2 inherited/clarified reducer。 |
| INV-JB-RR-04 | resource cap、single-package streaming、no raw retention 与 no partial output 保持 fail-closed。 |
| INV-JB-RR-05 | Producer 与 strict loader 都从 J-A raw bytes replay；两者共享的 production TCB 仅为 raw-stream parser + deterministic reduction kernel，loader 的 persisted-result comparison 覆盖 rows、reducers、counts 与 rendered projection；独立 oracle 不得调用该 kernel。 |
| INV-JB-RR-06 | 当前两个 J-B roots immutable，且不可作为 verified archive reduction 或 downstream consumer positive evidence。 |
| INV-JB-RR-07 | successor receipt 只能以 fresh authorized `RUN_ID`、fresh Core/CLI SHA、Compatibility Delta 冻结的 exact inherited stage-config path/SHA，以及本 Delta/approved Plan identity 原子发布。 |
| INV-JB-RR-08 | Closure requires existing independent v2 structural-verifier PASS, J-B strict-loader raw-replay PASS and independent semantic-oracle PASS; no one result alone is sufficient. Remediation provenance is bound externally per §4.2 without changing v2 artifact grammar. |
| INV-JB-RR-09 | J-B remains `exploratory_descriptive_only`; all twelve authority flags and `RISK_LIVE_TRADING_ENABLED` remain literal `False`. |
| INV-JB-RR-10 | 本 Delta 不创建 J-C、consumer、replay/Alpha/trading authority。 |

## 6. Verification And Fixture Provenance

未来 Plan 的 Task 0 必须首先记录以下 **non-completion defect baseline**，逐项 exact match；任何漂移在 mutation 前为 `BLOCKED_SCOPE_DRIFT` 或 `BLOCKED_SPEC_DRIFT`，不得 rebaseline 或将其解释为 completion evidence：

```text
current committed HEAD
approved Parent/Rebind/Schema/Compatibility/Remediation/v2-Governance Design and remediation Plan bytes
current J-B core SHA256 = 245ae39793d4f4ccfa972b5898aa9b0f53c34353facf21568fa7ebc9e020c2f4
Compatibility-frozen stage config path/SHA
J-A closure tuple and existing evidence tuple
legacy 20261013T000000Z:
  manifest = 36df19595b503a5e4f385a8fc6a834dc0b0c41c5c85e6b4641dea96606dad96a
  summary = a61e75f55ca7bfaba930ca14e8002e8c46298cd35636f0d742685681f8196373
  review = 9a926c51c72f9b797cf006cc5c6d3a645e4f64b96c220de50b52946682311393
legacy 20261013T040000Z:
  manifest = cdcf5dd23ea139e2d6fc7274c065d2c20c3f7df9e277cbf215460d06045b2974
  summary = eaf4130057f50af50aa9e40a958baab9e465f5ae646a605f8393a78b33aecca9
  review = 45720b24591446183f10949e58d2399722461de1db9eb297028348e2ee4df5bb
for both legacy roots and each of 300000/3600000/14400000:
  child complete/gap = 0/281; parent complete/gap = 0/131
source evidence: core lines 1165-1313 show the canonical producer does not call
the raw-reduction helpers and hardcodes evidence-gap states/counts.
```

Fixture classes are disjoint:

1. **A - Canonical cross-boundary positive:** complete sealed J-A replacement root -> real public J-A admission -> real J-B producer(temp root) -> real J-B strict loader. It is outcome-blind: lexicographically first J-A complete parent/child whose real required packages yield an anchor and three selected horizons. J-A raw bytes must not be modified.
2. **B - Upstream-authority negative:** a single `/tmp` mutation of J-A root/hash/checksum/raw bytes must reach the earlier J-A/upstream admission `STOP`; it is not required to reach a J-B parser.
3. **C - Isolated J-B parser/reducer negative:** synthetic `/tmp` ZIP/CSV is allowed only at a private pure-function test seam for header, timestamp, price, quantity, tie, Decimal and parser checks. It cannot be called cross-boundary positive evidence or create authority/root state.
4. **D - Persisted J-B artifact negative:** single mutation of J-B row/summary/review/manifest bytes must be rejected by the J-B loader and/or existing v2 structural verifier at its named gate.

For class A, the independent oracle above calculates expected fields from real ZIP bytes without importing/calling the production kernel. If its canonical fixture does not exist, stop `BLOCKED_SPEC_DRIFT`; never handwrite CSV, hash or authority packet as a positive substitute.

至少需要以下 mechanical proof：

1. `F-JA -> J-B producer(temp root) -> J-B strict loader -> existing v2 verifier` class-A positive chain，且至少一个 derived complete child/horizon 与一个 parent reduction 是 non-null；
2. 独立 oracle 比较 exact anchor/horizon row、trade count、Decimal bps、min/max、parent median、distribution/concentration，并记录 oracle PASS、fixture identity 与 oracle source SHA；
3. Class-B root/hash/checksum/raw mutation stops at upstream admission; Class-C header/price/timestamp/tie/Decimal mutation stops at its private pure seam; Class-D persisted outcome/manifest/review mutation stops at loader/existing v2 verifier. No mutation may bypass sealed J-A admission to claim cross-boundary positivity;
4. producer/loader 不读取 raw input 的 regression proof：对 canonical complete child 把 raw stream access forced to fail，producer/loader 必须 STOP，绝不可输出 synthetic `missing_horizon_trade` gap；
5. lifecycle proof：absent/staging-only/final-only/final-plus-staging、same-RUN dual process、fsync/rename/collision；
6. actual pytest, Ruff, `anti_shortcut_scan.py` actual RC, `git diff --check`, index/scope proof, `RISK_LIVE_TRADING_ENABLED is False`；
7. independent code review、Completion Audit、fresh single-run authorization、fresh root Receipt Closure Audit。The external remediation provenance report must record this Delta/Plan/Core/CLI/config identities, oracle PASS/source SHA, Domain loader/v2 verifier actual RC, v2 verifier SHA, v2 closure-evidence tuple, new root identity and three artifact hashes.

## 7. Research Methodology Boundary

本 Delta 是 deterministic data-provenance and measurement-conformance remediation，不是 alpha evaluation。L2 required items 的状态如下：

| L2 item | Status |
| --- | --- |
| mechanism / claim / promotion / kill | `N/A`; 不提出或评价任何交易机制。 |
| independent unit | 保持 `source_article_id` parent cluster；child 不是独立机会。 |
| PIT / preregistration | 不构造 PIT decision 或策略规则；只描述 J-A persisted historical trade prints。 |
| outcome distribution / MAE / tail / concentration | 仅作为 frozen descriptive fields；不作 PnL、expectancy、survival 或 capacity claim。 |
| fee / friction / liquidity | `N/A`; 不把 trade-print price 当作 executable price。 |
| evidence-gap semantics | Only §3.3's reachable delay/package/horizon absence may persist as evidence gap; unreadable/corrupt input and an unexecuted raw stream are structural/implementation `STOP`, not market evidence. No gap is interpreted as negative alpha. |

## 8. Routing

1. 本 Delta 先接受 independent Design review；`RECOMMEND_APPROVE` 不是 implementation authority。
2. 用户批准本 Delta 后，起草一个同时绑定本 Delta 与 existing v2 authority tuple 的 remediation Implementation Plan；Plan 必须先完成 Task 0 drift/legacy proof，之后才允许 RED -> implementation -> GREEN。
3. Plan approval 仅可授权 code/test/evidence-tree changes；它不得授权 network 或 receipt generation。
4. Completion Audit 通过后，新的单次 receipt-generation authorization 才可被单独考虑；其成功 root 仍须经过 independent J-B domain strict-load、independent semantic oracle、existing v2 verifier 和 Receipt Closure Audit。

在上述步骤完成前，正确动作是 no-op。当前 J-B 研究结论仍为 `evidence_insufficient`，不存在 consumer、replay、signal、paper/live、execution 或 Alpha authority。
