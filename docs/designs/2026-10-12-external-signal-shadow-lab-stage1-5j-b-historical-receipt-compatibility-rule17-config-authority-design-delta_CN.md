# Stage 1.5J-B Historical Receipt Compatibility Domain Design Delta

**日期:** 2026-10-12
**状态:** `draft_for_independent_review`
**J-B 父级 Design:** `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md`
**J-B 父级 Design SHA-256:** `ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b`
**J-B Rebind Delta:** `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md`
**J-B Rebind Delta SHA-256:** `0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c`
**J-B Receipt Schema Authority Delta:** `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md`
**J-B Receipt Schema Authority Delta SHA-256:** `f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25`
**J-B Rule 17 Profile v1 Delta:** `docs/designs/2026-10-11-governance-stage1-5j-b-receipt-rule17-profile-design-delta_CN.md`
**J-B Rule 17 Profile v1 Delta SHA-256:** `a692a888e1a9ae6b66379045fc031c6075eb72ff99fc30d140dd671caaa1153b`
**目的:** 在不修改 J-A 历史 receipt、J-A public strict loader 或 J-A Rule 17 verifier 的前提下，消除 J-B 离线 research/resource constants 与 J-A historical full-file `configs/base.py` SHA admission 的结构冲突，并把新 config authority 纳入 J-B 最新 target-stage domain Design chain。独立 Rule 17 v2 profile 由单独的 Governance Delta 定义。

---

## 0. Delta Authority And Non-Authorization

本 Delta 仅覆写 J-B config ownership、J-B latest target-stage Design identity、J-B `authority_packet.audited_config` 与 receipt-generation authorization 的 config binding。除明确覆写外，所有父级 Design/Delta 保持不变。

本 Delta 不授权 implementation、commit、push、deployment、SSH、network、receipt generation、J-B consumer、replay、signal、paper trading、live trading、execution 或 Alpha claim。它不修改任何风险阈值、仓位、entry/exit、资金配置或 `RISK_LIVE_TRADING_ENABLED`。

**Mutable Set:** J-B config compatibility policy、`configs/base.py` 的 J-B nine-constant block、一个新的 J-B stage-local config module、J-B core/CLI/test domain authority binding、以及与此直接相关的 Plan/Task 0 evidence。
**No-Touch Set:** J-A core、J-A replacement root、J-A authority packet、J-A public strict loader、J-A Rule 17 v1/v2 profiles/verifier/tests/closure evidence、J-B parent Design/Rebind Delta/Receipt Schema Authority Delta bytes、J-B Rule 17 v1 Profile Delta `docs/designs/2026-10-11-governance-stage1-5j-b-receipt-rule17-profile-design-delta_CN.md` (SHA-256 `a692a888e1a9ae6b66379045fc031c6075eb72ff99fc30d140dd671caaa1153b`)、已 blocked R1 Plan bytes、J-B measurement/reducer/Decimal/horizon contract、12 false authority flags、network/receipt/consumer/trading boundaries。

---

## 1. Confirmed Facts And Root Cause

1. The J-A replacement receipt `stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z` records `authority_packet.audited_config.relative_path = configs/base.py` and requires this exact current-workspace file SHA:

```text
J_A_COMPATIBLE_BASE_CONFIG_SHA256 = 473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc
```

2. J-A public strict loader independently resolves the project root, requires `configs/base.py`, and rejects a different on-disk hash before J-B can consume the root:

```text
STOP=stage1_5j_a_authority_packet_invalid:disk_sha_mismatch:audited_config
```

3. The blocked J-B R1 Plan required nine J-B constants to be appended to `configs/base.py`. That alters its complete SHA, mechanically preventing J-A public strict-loader admission. This is a `BLOCKED_SPEC_DRIFT`, not a local test defect or an allowed executor workaround.

4. The current J-B Rule 17 v1 profile validates `audited_config` only as a receipt-internal `{relative_path,sha256}` object. It does not freeze a config path literal. Therefore it cannot independently reject an otherwise structural receipt that binds the wrong config path.

5. The nine J-B values are offline deterministic measurement/resource constants. They do not set risk limits, position size, leverage, entry/exit, trade signal, paper/live permission, or network enablement. `RISK_LIVE_TRADING_ENABLED` remains a shared safety setting in `configs/base.py` and must stay literal `False`.

6. Current blocked-worktree evidence is preserved, not trusted as completion evidence: the pre-J-B `configs/base.py` bytes are available from `HEAD`, while the current modification is the R1 nine-constant append. A future Plan must prove that exact fact before it removes anything; it must not use `git checkout`, `git reset`, or a broad rewrite.

**Graph topology evidence:** `graphify` is unavailable in the current virtual environment (`No module named graphify`). This Delta uses direct source inspection and targeted path/symbol search; future Plan Task 0 must repeat that fact and use `rg` unless a current graph is explicitly authorized.

---

## 2. Decision: Historical Receipt Compatibility Exception

### 2.1 One-off policy carve-out

`configs/base.py` remains the sole SSOT for shared runtime thresholds, risk limits, sizing, execution constraints, entry/exit rules, signal thresholds, and paper/live/runtime enablement.

The sole permitted **Historical Receipt Compatibility Exception** is Stage 1.5J-B's exact module in §2.2. It exists only because the frozen J-A replacement receipt binds the full `configs/base.py` SHA, J-B must call that unchanged public loader, and the nine values are only Design-frozen offline measurement/resource values. This carve-out is not precedent for another stage. Any other stage-local config requires a separately approved project-governance Design and review.

The canonical `.agent/rules/L0_Financial_Safety.md` is not changed because it contains no config-location rule; its risk-invariant protections remain unmodified. Future implementation may change `AGENTS.md` only after Task 0 proves its current SHA is exactly:

```text
AGENTS_PRE_CHANGE_SHA256 = 32c14c73071a6b15d66bad794d652357d4eca90eaa7e2ae3e35310f55abe49cf
AGENTS_POST_CHANGE_SHA256 = 06bb1e5c86a26b2ea3a76296ca11e8749092fff6168a4c6c2d921ed921eef620
```

The exact, and only, allowed substitutions are:

```text
then check `configs/base.py` (all thresholds and limits).
->
then check `configs/base.py` (all shared/risk thresholds and limits) and, only for Stage 1.5J-B historical receipt compatibility, `configs/stage1_5j_b_historical_aggtrades_launch_response.py`.

Risk invariants must not be changed implicitly. `configs/base.py` is the only place to change thresholds.
->
Risk invariants must not be changed implicitly. `configs/base.py` is the only place to change shared, risk, strategy, or execution thresholds. The sole exception is the exact Stage 1.5J-B offline constants in `configs/stage1_5j_b_historical_aggtrades_launch_response.py`, frozen by `docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md`; no other stage-local config module is allowed without a separately approved project-governance Design.

- All thresholds must be in `configs/base.py`. No magic numbers inside `src/`.
->
- All shared, risk, strategy, and execution thresholds must be in `configs/base.py`. The sole exception is the exact nine offline Stage 1.5J-B constants in `configs/stage1_5j_b_historical_aggtrades_launch_response.py`, frozen by `docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md`; no other stage-local config module is allowed without a separately approved project-governance Design. No magic numbers inside `src/`.
```

Any pre/post hash mismatch, additional edit, or policy edit before Task 0 authorization proof is `STOP=stage1_5j_b_config_exception_policy_violation`.

### 2.2 Exact J-B stage-local config authority

The one permitted module is:

```text
J_B_CONFIG_RELATIVE_PATH = configs/stage1_5j_b_historical_aggtrades_launch_response.py
J_B_CONFIG_SOURCE_SHA256 = 771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4
J_B_CONFIG_BYTE_COUNT = 565
```

It consists of exactly these nine ASCII assignments in this order, LF-only, one terminal LF, no BOM, blank lines, comments, imports, `__all__`, helper, dynamic lookup, or other bytes:

```python
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS = 300_000
EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS = (300_000, 3_600_000, 14_400_000)
EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS = 60_000
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES = 268_435_456
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES = 536_870_912
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO = 64
EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES = 65_536
EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES = 67_108_864
EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES = 1_073_741_824
```

Every J-B producer/loader/CLI use of these nine names must obtain them only through the verified config-authority sequence in §3.3. The future Plan must prove every name is applied to its declared measurement or resource boundary; an unused frozen key, a duplicate literal, or a J-B source fallback to `configs.base` is a fail-closed implementation defect.

`RISK_LIVE_TRADING_ENABLED` remains imported only from `configs.base`, is required to be `False`, and is not part of the stage-local module.

---

## 3. J-A Compatibility And J-B Receipt Authority Contract

### 3.1 J-A compatibility precondition

Before importing or calling the J-A public loader, future J-B execution/testing must require:

```text
SHA256(configs/base.py) = J_A_COMPATIBLE_BASE_CONFIG_SHA256
```

The public `load_verified_stage1_5j_a_historical_archive_coverage_root()` must then actually return success for the frozen J-A replacement root. Any mismatch or nonzero result stops before ZIP access, J-B reduction, staging, receipt publication, or J-B verifier invocation.

The future Plan must first capture the dirty-worktree ledger and prove that the only `configs/base.py` difference from the Task 0 baseline is the exact nine-line R1 block. It may then delete only that block with a narrow patch and recompute the required SHA. It must never assume the equality, overwrite concurrent changes, use a historical checkout, or silently rebaseline.

### 3.2 Latest J-B target-stage domain authority and receipt binding

This Delta becomes the latest J-B target-stage domain Design authority. Its approved SHA is an external post-review binding, never a self-reference:

```text
J_B_COMPATIBILITY_DOMAIN_DELTA_PATH = docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md
J_B_COMPATIBILITY_DOMAIN_DELTA_SHA256 = user-approved exact SHA-256 of this Delta
```

The ordered J-B domain parent chain remains: J-B parent Design -> J-B Rebind Delta -> J-B Receipt Schema Authority Delta -> this Compatibility Domain Delta. `authority_packet` keeps its exact parent key set; it adds no field. For every future J-B receipt:

For every future J-B receipt:

```text
summary.authority_packet.audited_config.relative_path = J_B_CONFIG_RELATIVE_PATH
summary.authority_packet.audited_config.sha256 = J_B_CONFIG_SOURCE_SHA256
summary.authority_packet.approved_j_b_design.relative_path = J_B_COMPATIBILITY_DOMAIN_DELTA_PATH
summary.authority_packet.approved_j_b_design.sha256 = J_B_COMPATIBILITY_DOMAIN_DELTA_SHA256
receipt_generation_authorization.APPROVED_J_B_DESIGN_SHA256 = J_B_COMPATIBILITY_DOMAIN_DELTA_SHA256
receipt_generation_authorization.AUDITED_CONFIG_SHA256 = J_B_CONFIG_SOURCE_SHA256
```

Completion Audit and Receipt Closure require the following three-way equality in addition to the Design/Plan authorization grammar:

```text
SHA256(on-disk J-B stage config)
== summary.authority_packet.audited_config.sha256
== receipt_generation_authorization.AUDITED_CONFIG_SHA256
== J_B_CONFIG_SOURCE_SHA256
```

The J-B producer records this pair only after §3.3 succeeds. The J-B public strict loader independently requires the same exact path and SHA, and rejects the old `configs/base.py` path, an alias, an absent file, a symlink, a changed source byte, or an unapproved key/value with `STOP=stage1_5j_b_config_authority_mismatch`.

This changes only J-B's future authority packet and receipt-generation authorization. It does not alter J-A's historical `audited_config`, J-A loader semantics, or any sealed J-A artifact.

### 3.3 Verified stage-config import sequence

Before producer or strict-loader measurement/replay, one private J-B core helper must return a single verified config-authority result for that operation. It is not a registry, factory, plugin, public selector, or caller-supplied config path. Its exact sequence is:

```text
resolve canonical project-root/J_B_CONFIG_RELATIVE_PATH
-> reject symlink, non-regular file, wrong byte count or pre-import SHA
-> importlib.invalidate_caches() and evict only this exact module name from sys.modules
-> import the exact module
-> require module.__file__ and module.__spec__.origin equal the canonical resolved file
-> require exactly the nine public names, exact non-bool integer/tuple values, and no extra public name
-> recompute post-import byte count/SHA
-> return the verified values plus path/SHA identity
```

The pre/post bytes must both equal §2.2. Cache eviction makes the checked module object derive from the checked source bytes; any import, origin, value, public-name, or post-import mismatch is `STOP=stage1_5j_b_config_authority_mismatch`. `RISK_LIVE_TRADING_ENABLED` is separately read from `configs.base` and must be literal `False`.

---

## 4. Separate Rule 17 v2 Governance Authority

The existing `stage1_5j_b_receipt_v1` profile does not contain an `audited_config.relative_path` literal. It and its Design Delta remain immutable and non-authoritative for a receipt governed by this Delta, regardless of whether a v1 invocation returns `0`.

The required separate candidate is:

```text
J_B_RULE17_V2_PROFILE_DELTA_PATH = docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md
PROFILE_ID = stage1_5j_b_receipt_v2
PROFILE_CONTRACT_VERSION = 2
```

That Governance Delta must bind this Delta's exact approved path/SHA, the exact v2 profile tuple, verifier path/source identity, and closure-evidence identity. It alone defines independent verifier acceptance. For a receipt using §3.2, any v1 verifier result, even `RC=0`, is non-authoritative and is `STOP=governance_j_b_wrong_profile_evidence` when offered as Completion or Receipt Closure evidence.

J-B domain loader success and the separate v2 Rule 17 verifier success are both required. Neither grants receipt-generation, consumer, network, Alpha, replay, signal, paper/live, execution, deployment, commit, or push authority.

---

## 5. Acceptance Invariants And Fail-Closed Sequence

| ID | Invariant | Required failure |
| --- | --- | --- |
| `INV-JB-HRC-01` | `configs/base.py` equals `473dd4...` before public J-A admission. | `STOP=stage1_5j_b_j_a_compatibility_base_config_mismatch` |
| `INV-JB-HRC-02` | Public J-A strict loading of the exact replacement root succeeds before any J-B raw package access. | Preserve the public J-A `STOP`; no J-B fallback. |
| `INV-JB-HRC-03` | The single stage-local config file has exactly the §2.2 bytes and SHA. | `STOP=stage1_5j_b_config_authority_mismatch` |
| `INV-JB-HRC-04` | J-B producer and strict loader bind `audited_config` exactly to §3.2. | `STOP=stage1_5j_b_config_authority_mismatch` |
| `INV-JB-HRC-05` | A separately approved Rule 17 v2 profile independently requires the exact persisted config path/SHA; v1 evidence is non-authoritative. | `STOP=governance_j_b_wrong_profile_evidence` |
| `INV-JB-HRC-06` | The compatibility exception cannot carry risk, execution, signal, paper/live, network, or dynamic configuration. | `STOP=stage1_5j_b_config_exception_policy_violation` |
| `INV-JB-HRC-07` | Each of the nine constants is consumed only from the stage-local module at its frozen boundary. | `STOP=stage1_5j_b_config_authority_mismatch` |
| `INV-JB-HRC-08` | J-A implementation, receipt, verifier, profile, and closure evidence are unchanged. | `STOP=stage1_5j_b_j_a_no_touch_violation` |

Reducer order is fixed:

```text
Task 0 dirty-worktree/config-diff proof
-> exact base config SHA
-> public J-A strict loader
-> J-B stage config pre/import/origin/value/post-import identity
-> J-B authority packet and receipt-generation authorization equality
-> J-B domain replay
-> separately approved independent Rule 17 v2 verifier
```

Any earlier failure stops the sequence. No temporary clean worktree, caller-selected project root, subprocess adapter, copied J-A receipt, synthetic positive J-A fixture, config fallback, or compatibility alias is permitted.

---

## 6. Persistence, Lifecycle, Compatibility, And Fixture Provenance

This Delta creates no receipt and changes no current persisted artifact. There is no config migration, receipt rewrite, root replacement, or compatibility acceptance for J-A historical artifacts.

Future J-B receipts use the unchanged three-file sealed-tree lifecycle from the parent J-B Design. The receipt serializer writes the exact stage-local `audited_config` pair and latest domain Design identity; staging/final crash states remain owned by the J-B domain lifecycle. A crash before final publication leaves no J-B receipt authority, and a final root whose config authority fails either J-B strict loader or separately approved Rule 17 v2 is not consumable.

Positive J-A admission evidence must derive only from the actual J-A replacement root through the public J-A strict loader. Independent verifier mechanics may use a clearly labeled synthetic J-B sealed tree, but that tree is never a domain-positive receipt, never substitutes J-A admission, and never proves semantic replay or closure.

---

## 7. Safety, Research, And Authority Boundaries

**L2 applicability:** This stage remains `exploratory_descriptive_only`. The config move changes no hypothesis, independent sampling unit, point-in-time boundary, fixed horizons, outcome calculation, costs, capacity conclusion, Alpha status, PnL claim, or promotion/kill rule. All Alpha/economic/execution/liveness claims remain `not_evaluated` or `evidence_insufficient` as frozen by the parent Design.

All twelve J-B authority flags remain literal `false`. `RISK_LIVE_TRADING_ENABLED` stays `False`. The stage-local module contains no permission flag, risk threshold, trade parameter, secret, host, URL, credential, network setting, or executable behavior.

---

## 8. Future Plan And Verification Obligations

A future Plan may begin only after independent Design review and explicit user approval. Its Task 0 must bind this Delta SHA and:

1. Record blocked R1 Plan SHA `ce82883e3e7e17fb8b97c73116ee7f7d7b6a3fee01813013afe74ef252ebde42`, the current dirty-worktree path/SHA ledger, and the prior `14 passed, 3 failed` core-test evidence as non-completion evidence.
2. Prove the current `configs/base.py` diff equals only the exact nine R1 additions; otherwise stop `BLOCKED_SCOPE_DRIFT` without mutation.
3. Restore only the proven block through a narrow patch; require `SHA256(configs/base.py) = 473dd4...`; then invoke the public J-A loader on the actual replacement root and record actual success.
4. Apply only the §2.1 three-substitution `AGENTS.md` patch and require its post-change SHA before source/test changes; this policy patch grants no runtime or receipt authority.
5. Create the single §2.2 file and require its byte count/SHA/pre-import/import-origin/exact-value/post-import sequence before changing J-B behavior.
6. Move all nine J-B uses from `configs.base` to the verified result in §3.3, retain the base-only `RISK_LIVE_TRADING_ENABLED` read, and demonstrate each value's actual boundary use.
7. Update J-B producer/loader and receipt-generation parser/tests for the exact §3.2 pair and all equality checks. Test one-fact mutations of base SHA, stage config path, stage config source SHA, one config value, preloaded stale module, old `configs/base.py` receipt pair, and stale design SHA.
8. Only after the separate Governance v2 Delta has independently passed review and approval, implement/test its v2 verifier. Completion and Receipt Closure must reject v1-as-v2 evidence with `STOP=governance_j_b_wrong_profile_evidence`.
9. Run canonical positive J-A admission, negative one-fact probes, J-B domain loader, independent Rule 17 v2 verifier, Ruff, `anti_shortcut_scan.py` with actual process RC, and scope/index proofs. No J-B receipt-generation authorization or final J-B root may exist.

The allowed future implementation scope is intentionally limited to `AGENTS.md`, `configs/base.py`, the single new config module, the existing J-B core/CLI/verifier and their direct tests, plus the new Plan's `.git/plan-execution` evidence. Any J-A file, J-A receipt, J-A verifier, network path, new consumer, registry, factory, plugin, environment override, or generic config framework is `BLOCKED_SCOPE_DRIFT`.

---

## 9. Rollback And Open Questions

**Rollback:** Before receipt-generation authorization, rollback means removing only the unapproved J-B compatibility-remediation changes using a reviewed narrow diff while retaining the blocker evidence and historical documents. It never changes J-A artifacts or attempts to restore J-A compatibility through loader relaxation.

**Non-blocking deferred governance debt:** J-A's current public loader treats a generation-time full-file `configs/base.py` hash as a future-workspace admission dependency. A general solution based on immutable generation-environment provenance is a separate governance/receipt-compatibility project. It is explicitly out of scope here.

**Blocking open questions:** None. This Delta fixes the known J-B contradiction without changing J-A or any financial safety boundary.
