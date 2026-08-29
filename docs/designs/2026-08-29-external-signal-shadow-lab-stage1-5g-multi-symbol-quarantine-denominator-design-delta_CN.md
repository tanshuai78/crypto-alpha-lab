# External Signal Shadow Lab Stage 1.5G Multi-Symbol Quarantine Denominator Design Delta

**日期:** 2026-08-29
**状态:** design_approved
**Review Mode:** closure_confirmation
**适用阶段:** Stage 1.5G offline live-depth evidence review；Stage 1.5H 仅作为上游 artifact consumer 执行拒绝性验证
**父级设计:** `docs/designs/2026-07-11-external-signal-shadow-lab-stage1-5g-raw-snapshot-quarantine-design_CN.md`
**实现计划许可:** `true`
**代码实施许可:** `false`
**部署许可:** `false`

---

## 1. 一句话结论

Stage 1.5G 当前把单标的 `coverage_metrics.expected_snapshot_count` 直接作为多标的 quarantine 聚合值的分母，令 `book_availability_ratio` 可以大于 `1`。但修复不能把原有单标的 gate 替换成 aggregate gate。

本 Delta 冻结两层 contract：

```text
Layer A: each formal completed event-symbol
         -> 原有 Stage 1.5G quarantine gates，阈值和语义不变

Layer B: formal completed evidence set aggregate
         -> 使用正确总分母的审计指标；不能掩盖 Layer A failure

overall Stage 1.5G pass
  = global existing gates
  AND every Layer A per-symbol gate passes
  AND Layer B arithmetic / ratio invariants pass
```

当前 Stage 1.5H 是单标的 static proxy。任何 multi-symbol v1/v2 Stage 1.5G bundle 都必须被该 consumer 拒绝；本 Delta 不把多标的审阅结果升级为 1.5H 输入权限。

---

## 2. 已确认事实

1. `compute_coverage_metrics()` 的 `expected_snapshot_count` 是每个 formal completed symbol 的观察窗期望数，而不是聚合总数。当前 12h / 60s 配置下为 `720`。
2. `build_stage1_5g_review_summary()` 当前把该单标的值传给 `compute_raw_snapshot_quarantine_metrics()`；后者对整个 snapshots 集合计算 valid / invalid count，造成分子和分母集合不一致。
3. 父级 Design 已冻结 availability 分母为 `total_expected_snapshots`，并冻结了 `MAX_*`、`MIN_*` quarantine thresholds。其原始证据模型是单标的 12h / 720 snapshot contract。
4. 当前 reducer 虽已按 `event_symbol_id` 分组计算连续 invalid 与 first-valid latency，但 `valid_snapshot_count_after_quarantine`、invalid ratio、availability、warmup / midrun row count 与 minute bucket gate 仍使用 aggregate 值。
5. `20260829T024637Z_local` 的只读本地审阅包含 5 个 formal completed event-symbol、3546 条聚合 snapshot、3543 条 valid snapshot 与 3 条 invalid book；v1 错误输出为：

```text
expected_snapshot_count = 720
book_availability_ratio = 3543 / 720 = 4.9208333333
book_unavailable_ratio = 3 / 720 = 0.0041666667
```

6. 对同一已冻结证据，正确 aggregate 算术为：

```text
N = 5
total_expected_snapshot_count = 5 * 720 = 3600
book_availability_ratio = 3543 / 3600 = 0.9841666667
book_unavailable_ratio = 3 / 3600 = 0.0008333333
invalid_book_ratio = 3 / 3546 = 0.0008460237
```

7. 三条 invalid 的现有 v1 derived diagnostics 分布为：MRKUSDT 1 条 observation-initial invalid；IONQUSDT 1 条 observation-initial invalid 加 1 条 midrun invalid。该分布说明 aggregate 值不足以证明每个 symbol 的原有 gate 都通过。
8. 当前 Stage 1.5H report generator 的治理范围为 `single_event_fixture_bound_report_generator`，其 static proxy 将一组 spread/slippage/depth percentiles 当作单一输入市场，不具备多标的聚合 authority。
9. 已搜索 `data/external_signal_shadow`，没有已生成的 Stage 1.5H report/summary descendant；截至本 Design 写作时：

```text
unsafe_stage1_5h_descendant_count = 0
```

10. 已冻结本地 source evidence manifest 的 SHA-256：

```text
46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918
  data/external_signal_shadow/local_evidence/20260829T024637Z_stage1_5f/SHA256SUMS
```

11. Stage 1.5G 与 Stage 1.5H 都是本地、离线、只读流程；任何结果均不允许 execution feasibility、trade signal、paper trading、live trading 或 execution engine。

---

## 3. 显式假设

1. 一个 Stage 1.5G review root 可以包含同一公告的多个 formal completed event-symbol，也可以包含不属于本次 formal evidence set 的 snapshot。
2. `formal_completed_event_symbol_ids` 由既有 formal event integrity path 产生，是本 Delta 唯一的 evidence-set authority；不得从 snapshot 文件名、symbol 文本或 observed row count 推断集合。
3. 1.5H 当前的“single event”治理不能解释为“多个交易标的的混合 orderbook”。每个 futures symbol 是独立微结构市场。
4. 历史 v1 artifact 不重写、不覆盖、不重新贴上 v2 schema；原始 bytes 与既有 hash manifest 必须保持不变。

---

## 4. 根因与风险

### 4.1 根因

当前数据流混淆了两种量：

```text
coverage_metrics.expected_snapshot_count
  = per-symbol expected snapshot count

quarantine valid / invalid row count
  = aggregate rows across all supplied snapshots
```

将它们直接相除时，任何 `N > 1` 的健康多标的 root 都可能有 `book_availability_ratio > 1`。这不是超过 100% 的真实可用率，而是分母错误。

### 4.2 不能只修 aggregate 分母

原有 gates 受单标的 720 个期望样本约束。例如：

```text
4 symbols: 720 valid each
1 symbol: 650 valid
aggregate availability = 3530 / 3600 > 0.98
```

若仅使用 aggregate availability，该坏 symbol 会绕过其 `valid_snapshot_count_after_quarantine >= 684` 与 per-symbol availability contract。因此 aggregate 只能补足 evidence-set 审计，不能替代 per-symbol reducer。

### 4.3 信任链风险

1. 错误的 v1 multi-symbol `quarantined_pass` 若被当前 1.5H 消费，会把不同标的混合为单一 execution proxy。
2. 当前 1.5H loader 接收四个独立路径，仅比较少量字段和行数；相同统计数字的不同 review artifacts 可能被混用。
3. 修复 future loader 而不标记 historical unsafe descendant，会留下看似有效但不可复用的旧结论。

---

## 5. 已作决策

### Decision 1: `S` 是唯一 formal evidence-set authority

```text
S = sorted unique formal_completed_event_symbol_ids
N = len(S)
eligible snapshots(s) = rows where event_symbol_id == s, for s in S
```

非 `S` 的 rows 不进入 Layer A 或 Layer B quarantine numerator/denominator；必须报告为 `ignored_nonformal_snapshot_row_count`。既有全 root raw-integrity check 保持不变，因此非 `S` row 的 structural failure 仍可保守阻断整个 review，但不能污染 quarantine ratios。

### Decision 2: Layer A 保留全部原有 per-symbol gate 语义

对每一个 `s in S`，独立构造 `per_symbol_quarantine_metrics[s]`，并使用现有 `configs/base.py` 阈值、不改数值地判断：

```text
expected_snapshot_count_s = coverage_metrics.expected_snapshot_count
observed_snapshot_count_s
valid_snapshot_count_after_quarantine_s
invalid_book_row_count_s
invalid_book_ratio_s = invalid_s / observed_s
book_availability_ratio_s = valid_s / expected_s
book_unavailable_ratio_s = invalid_s / expected_s
launch_warmup invalid row/minute count_s
midrun invalid row/minute count_s
midrun_invalid_book_ratio_s = midrun_invalid_s / observed_s
max_consecutive_invalid_after_warmup_s
first_valid_book_latency_ms_s
crossed_or_negative_book_count_s
schema_invalid_count_s
quarantined_depth_quality_s
blockers_s
```

每个 symbol 都必须独立满足既有 valid-count、availability、invalid ratio、warmup、midrun、consecutive invalid、latency、crossed/schema、coverage、per-symbol request-success 以及 quarantined depth-quality gates。`compute_depth_quality_metrics()` 必须对每个 symbol 的 valid rows 独立运行；不得以混合 markets 的 p50/p95、top-depth 或 healthy-window ratio 代替任一 symbol 的 gate。

现有 global request-success 和全 root raw-integrity checks 保持为额外的保守全局 gate；它们可以阻断 overall review，但不能证明任一 symbol 通过。任一 `blockers_s` 非空，overall Stage 1.5G 不得输出 clean 或 quarantined pass。

### Decision 3: Layer B 只提供正确 aggregate evidence metrics

```text
per_symbol_expected_snapshot_count
  = coverage_metrics.expected_snapshot_count

total_expected_snapshot_count
  = N * per_symbol_expected_snapshot_count

aggregate_observed = sum(observed_s)
aggregate_valid = sum(valid_s)
aggregate_invalid = sum(invalid_s)

aggregate_book_availability_ratio = aggregate_valid / total_expected_snapshot_count
aggregate_book_unavailable_ratio = aggregate_invalid / total_expected_snapshot_count
aggregate_invalid_book_ratio = aggregate_invalid / aggregate_observed
```

Layer B 不得单独允许 pass。Layer A 对每个 symbol 已应用父级 `MIN_BOOK_AVAILABILITY_RATIO`、`MIN_VALID_SNAPSHOTS_AFTER_QUARANTINE` 和所有 invalid gates；在同一 per-symbol expected contract 下，Layer B availability 是透明 aggregate audit，不是放宽 gate。

`N <= 0`、per-symbol expected count 缺失或非正数、total expected 非正数、任何 ratio 非有限数或不在 `[0.0, 1.0]`，均 fail closed。禁止 `min(max(ratio, 0.0), 1.0)` 或其他 clamp。

### Decision 4: Stage 1.5G schema 升级为 v2

新的 Stage 1.5G summary 与 standalone quarantine summary 采用 `schema_version = 2`。v2 必须保留 `coverage_metrics.expected_snapshot_count` 的 per-symbol 语义，并在 `quarantine` 中显式输出：

```json
{
  "formal_completed_symbol_count": 5,
  "eligible_event_symbol_ids": ["..."],
  "ignored_nonformal_snapshot_row_count": 0,
  "per_symbol_expected_snapshot_count": 720,
  "total_expected_snapshot_count": 3600,
  "aggregate_observed_snapshot_count": 3546,
  "aggregate_valid_snapshot_count_after_quarantine": 3543,
  "aggregate_invalid_book_row_count": 3,
  "aggregate_book_availability_ratio": 0.9841666667,
  "aggregate_book_unavailable_ratio": 0.0008333333,
  "aggregate_invalid_book_ratio": 0.0008460237,
  "per_symbol_quarantine_metrics": {
    "event_symbol_id": {
      "quarantined_depth_quality": {"blockers": []},
      "blockers": []
    }
  }
}
```

v2 不得输出含混的 `quarantine.expected_snapshot_count`、`quarantine.observed_snapshot_count`、`quarantine.valid_snapshot_count_after_quarantine`、`quarantine.invalid_book_row_count` 或无前缀的 aggregate ratio key。单标的值只位于 `per_symbol_quarantine_metrics`；集合值必须带 `aggregate_` 前缀。

### Decision 5: v2 derived artifacts 使用同次 review manifest 绑定

对于写出的 v2 quarantine bundle，新增：

```text
stage1_5g_review_manifest.json
```

`stage1_5g_review_id` 是以下 canonical JSON projection 的 SHA-256：

```text
{
  "schema_version": 2,
  "source_evidence_manifest_sha256": "...",
  "formal_completed_event_symbol_ids": sorted(S)
}
```

main summary 与 standalone quarantine summary 必须共同写入：

```text
stage1_5g_review_id
source_evidence_manifest_sha256
formal_completed_event_symbol_ids_sha256
```

manifest 必须写入相同 fields，及以下 derived artifact 的相对路径和 SHA-256：

```text
stage1_5g_live_depth_evidence_review_summary.json
stage1_5g_quarantine_summary.json
depth_quality_input_rows.jsonl
quarantined_invalid_book_rows.jsonl
```

JSONL row schema 不增加 metadata；它们由 manifest 的 path + SHA-256 绑定。Stage 1.5H v2 loader 必须从 main summary 所在 root 读取 manifest，验证 supplied paths、review id、source identity、formal-id hash、v2 projection equality 与四个 artifact hash。任一不一致：`stage1_5g_quarantine_v2_artifact_mismatch`。

### Decision 6: 当前 Stage 1.5H 拒绝所有 multi-symbol bundle

Stage 1.5H compatibility matrix：

```text
v1 + N == 1
  + existing supported quarantined-pass artifact set
  -> preserve existing historical single-symbol path

v1 + N > 1
  -> reject: stage1_5g_v1_multi_symbol_denominator_unsafe

v2 + N == 1
  + stage1_5g_depth_evidence_quarantined_pass
  -> require complete v2 closed bundle and manifest/provenance validation
  -> then enter existing single-symbol path

v2 + N == 1
  + stage1_5g_depth_evidence_clean_pass
  -> not authorized by this Delta
  -> preserve current Stage 1.5H boundary; no clean-input loader/report path

v2 + N > 1
  -> reject: stage1_5h_multi_symbol_input_not_authorized

unknown schema version
  -> reject: unsupported_stage1_5g_schema_version
```

1.5H never recalculates, migrates or writes back to Stage 1.5G artifacts. Multi-symbol 1.5H must wait for an independently approved per-symbol report plus event-level reducer Design.

### Decision 7: historical unsafe descendant handling

Any historical Stage 1.5H output whose upstream is `schema_version=1` and `N>1` is:

```text
classification = preserved_defect_evidence
non_authoritative = true
reusable_as_stage1_5h_evidence = false
```

It must not be deleted, patched in place or upgraded. Plan preflight must enumerate its path and hash; current expected count is `0`.

### Decision 8: artifact write matrix

| Stage 1.5G state | Main summary | Quarantine summary / JSONL / manifest | Stage 1.5H eligibility |
| --- | --- | --- | --- |
| pre-quarantine structural or denominator failure | required, invalid | not written | no |
| clean pass | required | not written, preserving existing clean behavior | not authorized by this Delta; current 1.5H has no clean-input path |
| quarantine analysis completed, overall quarantined pass | required | required closed v2 bundle | only quarantined v2 `N==1` |
| quarantine analysis completed, overall invalid | required | required diagnostic closed v2 bundle if invalid rows exist | no |

Diagnostic invalid bundles remain immutable but never consumer-eligible.

---

## 6. Scope / Non-Goals

### 6.1 Scope

1. Stage 1.5G per-symbol quarantine reducer, aggregate audit metrics and v2 derived artifact schema.
2. Stage 1.5G review manifest, source identity binding and summary/JSONL hash verification contract.
3. Stage 1.5H version/provenance validation and fail-closed rejection of all multi-symbol input.
4. Tests for per-symbol gate preservation, aggregate arithmetic, provenance, artifact matrix and historical descendant detection.
5. A fresh local v2 re-review of the hash-frozen `20260829T024637Z_stage1_5f` evidence into `data/external_signal_shadow/stage1_5g/reviews/20260829T024637Z_local_v2`.

### 6.2 Explicit Non-Goals

This Delta does not:

1. modify Stage 1.5D or Stage 1.5F code, scheduling, output roots, raw snapshot rows or VPS processes;
2. change coverage, availability, invalid-book, warmup, latency, gap, request-health or depth-quality threshold values;
3. change the clean/quarantined/invalid decision taxonomy or allowed next actions;
4. create a Stage 1.5H multi-symbol report, event-level reducer, implementation permission, execution feasibility claim, alpha conclusion, paper trading or live trading permission;
5. modify historical v1 artifacts, their SHA256 manifests, or previous review reports;
6. migrate or overwrite `20260829T024637Z_local`.

---

## 7. Acceptance Invariants

1. **INV-01 Evidence-set authority:** `S` is exactly the deduplicated formal completed event-symbol set from the existing integrity result. No other source may define `S`.
2. **INV-02 Per-symbol authority:** every parent quarantine gate applies independently to every `s in S` with unchanged `configs/base.py` thresholds.
3. **INV-03 Overall reducer:** aggregate metrics cannot turn any nonempty `blockers_s` into clean or quarantined pass.
4. **INV-04 Same-set arithmetic:** Layer B counts only rows in `S`, and `total_expected_snapshot_count = len(S) * per_symbol_expected_snapshot_count`; no observed-row fallback exists.
5. **INV-05 Ratio bounds:** every per-symbol and aggregate ratio is finite and within `[0.0, 1.0]`; breach is `quarantine_ratio_out_of_range`, not clamping.
6. **INV-06 Single-symbol preservation:** for `N=1`, v2 arithmetic equals existing v1 arithmetic, except for explicit v2 fields, manifest and schema version.
7. **INV-07 Artifact closure:** every v2 quarantine bundle is bound by one review id, one source manifest hash, one formal-id hash and manifest SHA-256 entries for all four artifacts.
8. **INV-08 Consumer safety:** Stage 1.5H accepts only authorized single-symbol quarantined v1/v2 bundles; clean v2 is out of scope, all multi-symbol v1/v2 bundles are rejected, and source evidence is never mutated.
9. **INV-09 Evidence immutability:** v1 `20260829T024637Z_local`, its 1.5F source root and source `SHA256SUMS` remain unchanged. The re-review root is fresh and named `20260829T024637Z_local_v2`.
10. **INV-10 Permission preservation:** every output state retains `execution_feasibility_claim_allowed`, `trade_signal_allowed`, `paper_trading_allowed`, `live_trading_allowed`, `execution_engine_allowed` and `alpha_interpretation_allowed` as `false`.

---

## 8. Data, State and Temporal Contract

### 8.1 Producer / writer / loader / consumer impact matrix

| Component | Change | Authority / limit |
| --- | --- | --- |
| Stage 1.5D producer | none | existing live event evidence immutable |
| Stage 1.5F producer | none | existing raw snapshots immutable |
| Stage 1.5G loader | source manifest digest required for v2 bundle | source root remains read-only |
| Stage 1.5G reviewer | Layer A + Layer B reducer | only derived local artifacts change |
| Stage 1.5G writer | v2 summary, diagnostics and manifest | fresh output root only; no overwrite |
| Stage 1.5H loader | version, cardinality and manifest validation | reject unsafe/mixed artifact bundle |
| Stage 1.5H report generator | no proxy-model change | only accepted single-symbol quarantined bundle reaches existing logic |

### 8.2 V2 quarantine projection

For a v2 quarantine analysis, both embedded and standalone summary must contain:

```text
schema_version = 2
stage1_5g_review_id
source_evidence_manifest_sha256
formal_completed_event_symbol_ids_sha256
formal_completed_symbol_count
eligible_event_symbol_ids
ignored_nonformal_snapshot_row_count
per_symbol_expected_snapshot_count
total_expected_snapshot_count
aggregate_observed_snapshot_count
aggregate_valid_snapshot_count_after_quarantine
aggregate_invalid_book_row_count
aggregate_book_availability_ratio
aggregate_book_unavailable_ratio
aggregate_invalid_book_ratio
per_symbol_quarantine_metrics
```

For each per-symbol metric, at minimum write the Section 5 Decision 2 fields and exact blockers. The summary and standalone quarantine projection must be byte-equivalent after canonical JSON serialization; the manifest hashes bind their stored bytes and both JSONL artifacts.

`per_symbol_quarantine_metrics[event_symbol_id].quarantined_depth_quality` is the authoritative depth-quality result for that market. Any retained aggregate depth-quality output is diagnostic only and cannot replace a per-symbol blocker check.

### 8.3 Golden arithmetic and decision rule

For the preserved 20260829 evidence:

```text
N = 5
per symbol expected = 720
total expected = 3600
aggregate observed = 3546
aggregate valid = 3543
aggregate invalid = 3

aggregate availability = 3543 / 3600
aggregate unavailable = 3 / 3600
aggregate invalid observed = 3 / 3546
```

This fixes only aggregate arithmetic. The overall decision is not inferred from `3543 / 3600`; it is reduced after every symbol's unchanged gate result is known.

### 8.4 Failure semantics

The following produce `stage1_5g_depth_evidence_invalid` with `allowed_next_action=continue_observation`:

```text
formal_completed_symbol_count_missing_or_zero
authoritative_per_symbol_expected_snapshot_count_missing
total_expected_snapshot_count_invalid
per_symbol_quarantine_gate_failed
quarantine_ratio_out_of_range
source_evidence_manifest_missing_or_unreadable
```

Stage 1.5H maps incompatible cardinality, malformed v2, manifest/identity/hash mismatch and unknown schema version to `stage1_5h_input_rejected` using the exact blockers in Decision 6 and `stage1_5g_quarantine_v2_artifact_mismatch`.

### 8.5 Persistence, restart and idempotency

1. This is an offline pure review; it has no network request, live process, checkpoint or resume state.
2. A fresh v2 review of byte-identical source evidence must have identical arithmetic, decision, deterministic review id and artifact hashes, excluding fields that intentionally encode its new output-root path.
3. A target v2 output root must be fresh. Existing v1 and prior v2 roots are immutable; no in-place upgrade or overwrite is allowed.

---

## 9. Compatibility and Migration

1. `EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION` becomes `2` for newly written review artifacts.
2. Historical v1 single-symbol quarantined artifacts retain their historical arithmetic and remain readable only through the explicit legacy single-symbol branch.
3. Historical v1 multi-symbol artifacts are preserved but unsafe Stage 1.5H input. They are rejected without recalculation or mutation.
4. Historical unsafe Stage 1.5H descendants, if found during preflight, are registered as `preserved_defect_evidence`; current count is zero.
5. New v2 artifacts require no source-evidence migration because Stage 1.5F data is unchanged.
6. The known v1 `20260829T024637Z_local` output is defect evidence only and must not be used for Stage 1.5H. Re-review uses the unchanged source manifest and a new `20260829T024637Z_local_v2` output root.

---

## 10. Verification Strategy

### 10.1 Unit and golden tests

1. Existing single-symbol quarantined fixture: v2 reports `N=1`; per-symbol and aggregate arithmetic equal existing v1 values; the complete bundle and manifest validate.
2. Five-symbol golden fixture: `5 * 720 = 3600`, `3543` valid and `3` invalid; assert exact aggregate ratios and no ratio exceeds `1`.
3. `test_multi_symbol_aggregate_pass_but_one_symbol_fails`: four symbols have 720 valid rows and one has 650; aggregate availability exceeds 0.98, but overall result is invalid because that symbol violates the unchanged `684` requirement.
4. `test_same_aggregate_counts_different_symbol_distribution`: preserve aggregate counts while concentrating midrun invalid rows in one symbol; assert the decision follows that symbol's gate rather than aggregate camouflage.
5. `test_one_symbol_depth_quality_fails_while_aggregate_looks_healthy`: four markets pass all depth-quality thresholds while one fails a p95/depth/healthy-window threshold; overall result is invalid.
6. A nonformal snapshot row increments `ignored_nonformal_snapshot_row_count` and affects neither Layer A nor Layer B ratios; a structural raw-integrity issue still blocks globally.
7. `N=0`, missing per-symbol expected count, nonpositive total, NaN/infinite/out-of-range ratio and any clamp attempt fail closed with exact blockers.
8. Assert the v2 embedded/standalone quarantine projection canonical bytes are identical, then verify all manifest artifact hashes. Mix paths from two reviews and assert `stage1_5g_quarantine_v2_artifact_mismatch`.
9. Verify artifact write matrix for clean, quarantined pass, quarantine invalid and pre-quarantine structural/denominator failure.
10. Stage 1.5H fixtures: v1 `N=1` quarantined bundle is accepted through the legacy path; v1 `N>1` is rejected; v2 `N=1` quarantined bundle with valid manifest is accepted; v2 clean input retains current rejection/no-path behavior; v2 `N>1` is rejected with `stage1_5h_multi_symbol_input_not_authorized`.
11. Descendant preflight fixture: discovered unsafe v1 multi-symbol Stage 1.5H output is retained and reported but cannot be consumed.

### 10.2 Local evidence regression

After implementation, use a fresh local output root only:

```text
data/external_signal_shadow/stage1_5g/reviews/20260829T024637Z_local_v2
```

Required sequence:

```text
verify source SHA256SUMS
assert unsafe_stage1_5h_descendant_count == 0
run Stage 1.5G locally only
assert schema_version == 2
assert total_expected_snapshot_count == 3600
assert aggregate availability == 3543 / 3600
assert aggregate unavailable == 3 / 3600
assert aggregate invalid observed == 3 / 3546
assert each symbol has a complete gate result
assert every safety permission remains false
```

The result may establish only corrected Stage 1.5G evidence validity. It cannot authorize current Stage 1.5H, any implementation, deployment or trading activity.

---

## 11. Rollout and Rollback

1. Implement and test locally before any VPS sync; this change has no required VPS runtime deployment.
2. Preserve the existing v1 local output, source evidence archive and hash manifest.
3. Generate only the fresh v2 local review root and inspect its per-symbol gates, aggregate arithmetic and manifest.
4. If v2 fails any invariant, stop with all existing evidence unchanged. Rollback is code revert only; no artifact deletion or source recapture is needed.

---

## 12. Safety and Authority Boundary

This Delta does not widen authority. For every state in this Delta:

```text
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

The only permitted conclusion is whether the offline Stage 1.5G evidence review is internally valid under corrected per-symbol and aggregate contracts. A multi-symbol Stage 1.5G result is not current Stage 1.5H evidence.

---

## 13. Open Questions

None. The per-symbol authority, aggregate semantics, artifact bundle identity, legacy handling, current 1.5H boundary and fresh re-review root are fully specified.

---

## 14. Approval Gate

Before an Implementation Plan may be written, review must confirm:

1. every parent quarantine gate remains per-symbol and aggregate metrics cannot mask failure;
2. current Stage 1.5H rejects all multi-symbol v1/v2 bundles;
3. v2 review manifest closes cross-file path/hash provenance;
4. historical unsafe descendant enumeration is fail-closed and currently reports zero;
5. no Stage 1.5D/F, VPS collector, threshold, execution or trading-permission scope was added;
6. the v1 20260829 review remains preserved defect evidence and re-review targets only `20260829T024637Z_local_v2`.

Until approval:

```text
implementation_plan_allowed = false
implementation_allowed = false
deployment_allowed = false
```
