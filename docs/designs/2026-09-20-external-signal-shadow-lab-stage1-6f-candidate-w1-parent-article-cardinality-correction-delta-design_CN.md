# Stage 1.6F Candidate W1 `parent_article_id` 基数修正 Delta Design

**日期：** 2026-09-20  
**状态：** `draft_for_review`  
**类型：** 最小 authority-correction Delta；不是 Implementation Plan、代码变更、数据重采集、重跑或运行时授权。

## 1. 根因、范围与非目标

父级 Design `docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md` Section 6.5 第 332 行将 canonical `expansion_candidate_run_20260917_002` 的 `n_unique_parent_article_ids` 写为 `38`。该数值混淆了上游 C 全集的 38 个 parent IDs 与 canonical candidate cohort 的派生基数。

本 Delta 仅在满足 Section 3 的 **pre-W1 independent derivation** 后，窄范围替代父级第 332 行中的该错误基数语义。它不依据 W1 implementation、denominator JSONL、summary 或 loader 的自洽结果来修正父级 authority。

**非目标：**

- 不改变 `n_denominator=41`、指标、H1/H4/H12 窗口、准入规则、输出 schema、writer、loader、consumer 或 sealed bundle bytes；
- 不修改父级 Design 或既有 Plan bytes，不重跑数据，不修复或重写任何实施产物；
- 不把 27 个 distinct IDs 解释为 27 个独立统计样本，亦不产生胜率、显著性、Alpha、收益、PnL、成本或执行可行性结论；
- 不授权 Plan、实现、网络访问、SSH、runtime、deployment、commit、push、paper trading 或 live trading。

## 2. Evidence Hierarchy 与冻结 authority packet

### 2.1 Primary correction evidence: pre-W1 frozen bytes

以下 bytes 是 W1 consumer 执行前已冻结的 candidate admission 输入。它们是 `38 -> 27` 的唯一 primary authority；验证器必须仅用 Python 标准库 `hashlib`、`json` 和 `pathlib` 读取它们，禁止 import W1 producer、writer、loader 或读取 W1 bundle。

| 输入 | 路径 | SHA-256 |
|---|---|---|
| C completion manifest | `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json` | `226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0` |
| C source-export receipt | `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/source_export_receipt.json` | `07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e` |
| Archive coverage matrix | `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json` | `b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8` |
| Canonical candidate manifest | `data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002/candidate_manifest.json` | `b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67` |
| Candidate-collection Design | `docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md` | `1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4` |
| Candidate-collection Plan | `docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md` | `fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d` |

`candidate_manifest.json` authority packet must itself declare the exact C completion, C receipt and matrix SHA-256 values above. The receipt's `raw_payloads/detail/<parent_article_id>/...` inventory is the C-parent membership source; all candidate parent IDs must be a subset of it.

### 2.2 Secondary consistency confirmation: post-W1 artifacts

下列 artifacts 只能确认 implementation output 与 primary derivation 一致，**不得**作为修正 38 的来源、替代 primary bytes，或在 primary derivation 未通过时将 Design 变更为 27。

| 输出 | SHA-256 |
|---|---|
| `stage1_6f_candidate_w1_bundle_manifest.json` | `aa6d66eaa9fa2405b3a6aa8ce5468d5a64a748706f7f5781b8cc7431978a5298` |
| `stage1_6f_candidate_w1_denominator.jsonl` | `f9468681a58fa1569b8e10bbc47d8499db321acbc38d2b44f8b29adc4f24b16d` |
| `stage1_6f_candidate_w1_summary.json` | `fbb39dd9aeb602938ead6326f3577dbb7470bf64d7c0198087194dd101d37200` |

现有 W1 Plan `docs/plans/2026-09-18-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-implementation-plan_CN.md`（SHA-256 `1d0c714d4fc8525acd9c0940a9705cb8849d44217fbe0d5d391b3b2f4381f0f3`）是 historical execution record，不是本 Delta 的 correction evidence。

## 3. Pre-W1 Independent Derivation

定义：

```text
cohort = set(candidate_manifest.cohort)
C = {(parent_article_id, contract_id, canonical_symbol)
     for logical_archive_record in candidate_manifest.logical_archive_records
     if canonical_symbol in cohort}
M = {(parent_article_id, contract_id, symbol)
     for matrix_record in archive_coverage_matrix.in_range_archive_records
     if symbol in cohort}
P = {parent_article_id for (parent_article_id, _, _) in C}
```

唯一有效的 correction proof 必须同时满足：

```text
SHA-256 of every Section 2.1 input matches exactly
candidate_manifest authority packet binds C completion, C receipt and matrix hashes
len(cohort) = 41
REEFUSDT not in cohort
C = M
len(C) = 41
P is a subset of C receipt raw-detail parent IDs
len(P) = 27
```

所以 canonical cohort 的修正事实为：

```text
n_denominator = len(C) = 41
n_unique_parent_article_ids = len(P) = 27
```

这条推导只使用 collection-stage frozen bytes，且不依赖 W1 reducer、W1 denominator JSONL、W1 summary、W1 sealed manifest、现有 `load_candidate_w1_bundle(...)` 或任何实施后 source identity。`27` 不是 config，也不是允许硬编码的 fallback。

若 primary derivation 不能证明上述每一项，必须 `STOP=pre_w1_authority_derivation_unproven`。此时不得批准本 Delta；问题必须重新分类为 `implementation_or_evidence_discrepancy`，不得通过修改 Design 追认实施输出。

## 4. 决策与 Effective Design Authority

仅当 Section 3 通过、独立审查通过并由用户批准该 exact Delta bytes 后，父级 Design Section 6.5 第 332 行的 summary 句子被下列文字窄范围替代：

```text
The summary has n_denominator=41, n_unique_parent_article_ids equal to the
cardinality of the distinct parent_article_id values across the admitted
denominator rows (27 for canonical expansion_candidate_run_20260917_002), and
non_independence_notice=historical_ex_post_descriptive_rows_may_share_parent_articles_and_are_not_independent_samples.
It must not calculate, serialize or imply a win rate, significance test, alpha,
return, PnL, control adjustment or economic interpretation.
```

批准后的 effective authority 必须是：

```text
Effective Stage 1.6F Candidate W1 Design Authority =
  Parent Design SHA-256 dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097
  + approved SHA-256 of this exact Cardinality Correction Delta
```

该组合 authority 的规则如下：

- `candidate_w1_run_20260920_001` 的 completion/review interpretation 必须同时绑定 parent SHA 和 approved Delta SHA；
- W1 Plan `1d0c714d...` 保留为历史执行记录，**不得**在未显式绑定 approved Delta SHA 的情况下被重新授权或重新执行；
- 任何新的 implementation、rerun、repair 或 consumer 变更必须先有新的或修订后的 Plan，并显式冻结 parent SHA 与 Delta SHA；
- 未来 cohort 仍须从自身 admitted rows 派生基数；不得继承 27，也不得继承上游 C 全集的 38。

## 5. 契约影响矩阵

| 角色 | 变更 | 不变量 |
|---|---|---|
| Pre-W1 verifier | 新的 review proof obligation | 仅验证 Section 2.1 bytes 和 Section 3 集合关系；不得读取 W1 output。 |
| Producer / writer / loader / consumer | N/A | 不修改现有实现、schema、artifact 或路径。 |
| Existing W1 Plan | authority lifecycle rule | 只作历史记录；禁止在未绑定 Delta 的情况下复用。 |
| Completion auditor / reviewer | authority binding | 必须同时验证 parent SHA 和 approved Delta SHA，再解释 existing W1 bundle。 |
| Post-W1 strict loader | secondary confirmation only | 只检查 output 与 primary `41 / 27` 相符，不能生成 correction authority。 |

## 6. Acceptance Invariants

- **INV-PC01 Authority narrowness：** 本 Delta 只替代父级 Design Section 6.5 第 332 行中 `n_unique_parent_article_ids=38` 的错误基数语义；其余父级条款保持不变。
- **INV-PC02 Anti-hindsight derivation：** `27` 必须仅由 Section 3 的 pre-W1 frozen bytes 导出；实施后 output 不得作为 primary correction evidence。
- **INV-PC03 Cohort separation：** 上游 C 全集的 `38` 不能作为 canonical candidate W1 summary 的输入、默认值或 fallback。
- **INV-PC04 Mechanical cardinality：** canonical `expansion_candidate_run_20260917_002` 必须满足 `len(C) == 41`、`len(P) == 27`；secondary bundle 的 summary 仅可确认其等于 primary `len(P)`。
- **INV-PC05 Non-independence：** `non_independence_notice` 的精确值保持 `historical_ex_post_descriptive_rows_may_share_parent_articles_and_are_not_independent_samples`；27 不得被标记或解释为独立统计样本。
- **INV-PC06 Effective authority chain：** 获批后，解释既有 W1 bundle 必须绑定 parent SHA 与 Delta SHA；新的执行必须使用显式绑定二者的新/修订 Plan。
- **INV-PC07 No implementation drift：** 不修改 schema、writer、loader、consumer、artifact bytes、运行时状态或任何权限标志。
- **INV-PC08 Safety boundary：** `RISK_LIVE_TRADING_ENABLED` 与所有 Stage 1.6F 权限标志保持严格 `False`；本 Delta 不授予任何运行、交易或部署权限。

## 7. Failure Semantics、持久化与兼容性

这是 authority-only 文档修正，不新增 writer、持久化状态、Crash Window、恢复操作或幂等操作，均为 N/A。

primary SHA、C-parent membership、matrix equality、41-identity count 或 27-parent count任一失败时，终态唯一为 `STOP=pre_w1_authority_derivation_unproven`。primary 通过而 secondary bundle 不一致时，终态唯一为 `STOP=implementation_or_evidence_discrepancy`。两种终态均禁止修改父级 Design、Delta、bundle、denominator rows 或 summary 来消除差异。

旧 REEF-only evidence package、任何非 `expansion_candidate_run_20260917_002` candidate root 及未来采集根不获得本 Delta 的基数声明。

## 8. 验证策略

1. 独立执行 Section 3 的 stdlib-only verifier，核对六个 primary bytes（其中四个为 JSON）、candidate authority packet、`cohort`、`C`、`M` 和 C receipt parent inventory；期望唯一输出 `41 / 27`。
2. 对 2026-09-20 W1 bundle 重新计算 Section 2.2 SHA-256，并以 strict loader 确认 `denominator_count=41`、summary `n_unique_parent_article_ids=27`；这只能作为 secondary consistency confirmation。
3. 负向审查：删除/替换任一 primary SHA、令 `C != M`、加入 `REEFUSDT`、把 candidate parent 移出 receipt inventory，或使 `len(P) != 27`，均必须触发 `STOP=pre_w1_authority_derivation_unproven`。
4. authority-chain 审查：任何只绑定 parent SHA、或尝试复用旧 Plan 而未绑定 approved Delta SHA 的 rerun/repair，必须被拒绝为 `STOP=stale_plan_authority`。
5. scope/permission 审查：只允许本 Delta 变更；确认 `RISK_LIVE_TRADING_ENABLED = False`，且不执行网络、SSH、runtime、部署、commit 或 push。

## 9. Revision Ledger 与未决问题

| Finding | 状态 | Closure mechanism |
|---|---|---|
| P0-01 hindsight evidence upgrade | CLOSED in candidate | Section 2.1 and Section 3 establish an output-independent primary derivation; bundle is secondary only. |
| P0-02 effective authority chain | CLOSED in candidate | Section 4 binds parent + approved Delta and prohibits stale Plan reuse. |
| P1-01 loader identity not frozen | CLOSED in candidate | Strict loader has no authority role in the correction proof; it is secondary consistency evidence only. |

`earlier_closure_audit_miss = true`：此前未对 `C 47 / 38 parents -> candidate 41 -> distinct candidate parents` 做机械重算。`closure_escape_count = 1`。这不是本 Delta 产生的新基数或新权限。

**未决问题：** 无阻断本 Delta 审查的未决问题。未来 cohort、任何 implementation repair 或重新执行均明确在本 Delta 范围外。

## 10. Gate 与权限

本文件在独立 Design Review 和用户逐字批准前保持 `draft_for_review`。批准仅使本 Delta 成为 effective Design Authority 的第二个 bound byte；不自动授权 Plan、实现、重跑、网络、SSH、runtime、deployment、commit、push、paper trading 或 live trading。
