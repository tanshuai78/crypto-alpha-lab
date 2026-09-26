# Stage 1.6F-W2-0：探索性结算前基差机制诊断 Design

**状态：** `draft_for_review`
**日期：** 2026-09-26
**类型：** 只读本地历史证据上的探索性机制诊断；不是策略回测、执行或交易 Design
**本轮交付：** 仅此 Design candidate；不授权 implementation、commit、push、部署、SSH、联网、运行时动作、paper trading 或 live trading。

## 1. 目的、研究等级与 Final Claim

本 Design 的唯一研究问题是：对已冻结 W2 候选根中具备三类完整小时栏的下架合约，永续价格相对指数价格、以及标记价格相对指数价格的**基差绝对值**，在各自已冻结的结算前窗口中是否呈现向窗口末端缩小的探索性现象。

本阶段的 `outcome_inspection_status` 固定为 `outcome_seen`。根级 `research_classification` 是唯一 reducer：任一 metric 有至少一个 finite parent descriptor 时精确为 `exploratory_only`；两个 metric 的 parent descriptor 均为零时精确为 `evidence_insufficient`。每个 metric 另有独立 `metric_evidence_status`：`exploratory_described` 当且仅当其 `n_parent_exploratory_described >= 1`，否则为 `evidence_insufficient`。

若输出分布不显示稳定的向零收敛，只能在根级 `exploratory_only` 下如实描述该反例；它不是新的研究状态，也不构成策略 `falsified` 结论。

它不得形成 `phenomenon_supported`、`alpha_candidate`、`alpha_validated`、统计显著性、收益率、PnL、成本后期望、入场/退出、仓位、执行可行性或交易许可结论。`collection_terminal_with_evidence_gaps` 只表示采集协议完成且保留证据缺口，不表示机制失败。

## 2. 已确认事实

### 2.1 冻结输入与 authority

| 对象 | 路径/身份 | SHA-256 或状态 |
| --- | --- | --- |
| W2 evidence Design | `docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md` | `11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303` |
| W2 implementation Plan | `docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md` | `183689a6b786ccd3dce9f74f5d1fc2e9ccc1741d80f243f5724dd3b7de149229` |
| Network authorization | `configs/authorizations/network_auth_w2_candidate_run_20260925_001.json` | `0189fd4a922c87811e25793b62d12d6ba76ad92e60a95236a3fe54f024fa5dbf` |
| Candidate root | `data/external_signal_shadow/stage1_6f/w2_evidence_candidates/w2_candidate_run_20260925_001` | `run_id=w2_candidate_run_20260925_001` |
| Candidate manifest | 同 root 的 `candidate_manifest.json` | `1bd45df8d27e85b40d30500148575780740c6d089b5700e43c1cbfc22a4a0cea` |
| External Completion Audit review | `/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_completion_audit_review.md` | `1c3051315711b5fb0f80086d7f7dab3639a8ba438a74ab4ec4558ce3180d76f2`，报告 verdict 为 `complete` |
| Historical blind receipt | `/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_preanalysis_blind_receipt.json` | `5f6f1087888e73a0304f91b07d3a8b6ebaf7ca9b7701e4ab4de714dc158e0e25`；签发时为 `not_seen` |

当前 manifest 可由 `load_verified_w2_evidence(...)` 严格重算：`41` 个 denominator identities、`180` logical records、`180` physical objects、`123` 个 metric-window coverages，root state 为 `collection_terminal_with_evidence_gaps`。`87` 个 coverage 为 `observed`，`30` 个为 `temporal_unproven`，`6` 个为 `no_complete_bars`。Index 的有效 complete-bar coverage 中 `zero_index_close_count=0`；`10` 个时间未证实记录为 `null`，不被解释为零价格或零基差。

### 2.2 样本事实与独立单位

冻结 W2 universe 有 `41` 个 contract identities、`27` 个 distinct `parent_article_id`；其中 `31` 个 contracts、`21` 个 parents 为 `window_defined`，其余 `10` 个 contracts、`6` 个 parents 为 `settlement_time_unproven`。完整三指标记录为 `29` 个 contract rows，对应 `19` 个 parents；其余 `2` 个 window-defined contracts、`2` 个 parents 为 `no_complete_bars`。29 个完整合约的父公告簇大小为：14 个簇各有 1 个合约、1 个簇有 2 个、3 个簇各有 3 个、1 个簇有 4 个。故：

- `41` 是完整分母，不是可分析行数；
- `29` 是 contract-level 探索性描述行数，不能当作独立统计样本；
- `27` 是完整 parent denominator，`21` 是 parent window-defined count，`19` 是当前 parent-level 可描述上限；
- `10` 个 contract rows / `6` 个 parents 的 `temporal_unproven` 与 `2` 个 contract rows / `2` 个 parents 的 `no_complete_bars` 必须保留在完整 contract 与 parent ledger，绝不补时、删行或静默并入观察样本。

### 2.3 盲态事实与根因

W2 Design §12.2 允许采集和 strict reader 无输出解析原始行，但禁止在 Analysis Design 获批准前向研究接口显示 OHLC 或 price-derived output。后续元数据核验过程错误序列化了 manifest 内的 `first_row` / `last_row` 嵌套原始行；当前 `stage1_6f_w2_historical_price_candidate_manifest_v1` 确实保存这些行，strict reader 也要求其与 CSV 重算一致。

该 exposure 不改变 candidate root、network collection、Completion Audit 或其签发时 historical receipt 的真实性；但其后发生的研究治理状态必须 fail closed 为 `outcome_seen`。因此本 Design 明确排除确认性 W2-0，不尝试覆盖、修订或伪造原 receipt，也不将同一 root 重新下载后冒充未见样本。

## 3. 假设、决策与范围

### 3.1 探索性机制假设

`H-W2E-01`：在已冻结结算前窗口内，部分下架合约的永续/指数或标记/指数基差绝对值可能在窗口末端低于窗口初端。

这只是市场现象假设。它不说明该变化由下架规则造成，不说明可提前获知、可成交、可跨市场对冲、可承受路径风险，也不说明存在收益或 Alpha。

### 3.2 已作决策

| 决策 | 理由 |
| --- | --- |
| 只分析终局基差，不分析价格方向 | 直接回答 W2 采集的原始目的，避免引入另一条方向性假设。 |
| 使用每个 identity 已冻结的 `[window_start_ms, window_end_ms)` | 不新增或事后挑选固定小时长度。 |
| primary 为绝对基差端点变化 | “收敛”定义为向零靠近，而非 signed basis 恰好为正/负。 |
| parent-level 为解释单位 | 同一公告下的合约儿童相关；27-parent denominator 不得被 19 个可描述 parents 替代。 |
| 仅探索性、不设显著性/晋级阈值 | 当前 root 已 `outcome_seen`，且仅有 19 个父公告。 |
| 复用现有 W2 strict reader | 维持唯一 W2 evidence trust boundary；不复制 ZIP/CSV 验根器。 |

### 3.3 Scope

包括：离线读取已验证 W2 root、三族同 timestamp complete-bar 对齐、两种基差端点描述、contract-to-parent 聚类描述、完整 denominator/缺口 ledger、不可变 bundle 与严格 read-back。

不包括：新网络请求、重新采集、修改 W2 manifest/schema、修改 W2 collector 或 strict reader、补齐 settlement time、公告语义再解析、价格方向、收益/PnL、费用/滑点/深度/容量、MAE/MFE、显著性、控制组、策略、shadow/paper/live execution、VPS、数据库、常驻 observer、W2-1 或 holdout。

## 4. 数据、时间与指标契约

### 4.1 准入顺序

future W2-0 runner 必须在读取任何 raw CSV 前依次：

1. 核对本 Design、其未来 approved Plan、W2 collection Design/Plan、network authorization、candidate manifest 的 exact path 与 SHA；
2. 核对 external Completion Audit artifact 的 path、SHA、`complete` verdict 和 required W2 collection bindings；
3. 核对 historical receipt 的 path/SHA，记录其签发时 `not_seen`，同时强制本次 `outcome_inspection_status=outcome_seen`；根级 `research_classification` 只能在本节 reducer 完成后按 §1 写入；
4. 调用唯一的 `load_verified_w2_evidence(...)`；任何拒绝均在 output-root 创建前 `STOP=w2_0_admission_invalid`；
5. 仅在 1--4 全部通过后读取 strict reader 已验证的 parsed rows，进行本节指定的 deterministic calculation。

historical receipt 是签发时状态证据，不能覆盖后续 exposure；本 Design 的 `outcome_seen` 是对当前研究消费的 fail-closed admission classification，不是新的 receipt writer、publisher 或 runtime root。

### 4.2 合约行资格与时间对齐

一个 `(parent_article_id, contract_id, canonical_symbol)` 只有同时满足下列条件才是 `exploratory_described`：

- 精确拥有 `klines_1h`、`index_price_1h`、`mark_price_1h` 三族；
- 三条 `complete_bar_status` 均为 `observed`；
- 从该 identity 共享的 `[window_start_ms, window_end_ms)` 用上游 `compute_w2_grid_points(...)` 重算同一个 non-empty complete-bar grid `C`；
- `t_first` 精确为 `C[0]`、`t_last` 精确为 `C[-1]`，且 `t_first < t_last`；
- 三族均精确包含 `t_first` 与 `t_last`；完整 `C` 覆盖仍由三个 `complete_bar_status=observed` 和 strict reader 重算证明；
- `index_close(t_first) > 0` 且 `index_close(t_last) > 0`，所有参与值 finite。

不得 forward-fill、back-fill、最近值替代、跨 family 补齐、按日历时间重采样、将 raw-open point 当作 complete-bar，或以 `t_settle_ms` 本身代替最后完整小时栏。`temporal_unproven` 必为 `diagnostic_incomplete:temporal_unproven`；`no_complete_bars` 必为 `diagnostic_incomplete:no_complete_bars`；缺少 `C[0]` 或 `C[-1]` 必为 `diagnostic_incomplete:endpoint_coverage_gap`；其余对齐/非有限/非正 index 错误必为该 contract 的 `diagnostic_incomplete:<exact_reason>`，不得使整个 run 成功地省略该身份。

### 4.3 固定计算

对合格 contract row，在 `t_first` 与 `t_last` 分别计算：

```text
perp_index_basis_bps(t) = 10_000 * (perp_close(t) - index_close(t)) / index_close(t)
mark_index_basis_bps(t) = 10_000 * (mark_close(t) - index_close(t)) / index_close(t)
delta_abs_basis_bps = abs(basis_bps(t_last)) - abs(basis_bps(t_first))
```

`delta_abs_basis_bps < 0` 仅描述“该 contract 在该已冻结窗口两端更接近零”；它不是胜率、交易信号、收益或 Alpha。输出不得包含 OHLC 值、raw CSV 行、收益率、价格方向、资金费、费用或 PnL。

每个 parent 的每种 metric 使用其合格 child contracts 的 `delta_abs_basis_bps` 的确定性中位数，作为一个 parent-level descriptor。每个 parent 必须在 27-row parent ledger 中恰好一次：有任一双 metric 合格 child 时为 `exploratory_described`；否则全 child `temporal_unproven` 时为 `diagnostic_incomplete:temporal_unproven`；否则无 complete bars 时为 `diagnostic_incomplete:no_complete_bars`；其余失败为 `diagnostic_incomplete:<exact_reason>`。parent row 必须同时列出每个 metric 的 `metric_evidence_status`，因此一个 parent 不会因另一个 metric 的失败而消失。

### 4.4 汇总

对两个 metric（`perp_index_basis_bps`、`mark_index_basis_bps`）分别报告：

- `n_denominator_contracts=41`；
- `n_contract_exploratory_described`、各 exact `diagnostic_incomplete` count；
- `n_parent_denominator=27`、`n_parent_window_defined=21`、`n_parent_exploratory_described`，以及完整 27-row parent ledger 的 exact status counts；
- parent-level `minimum`、`median`、`maximum`、P25、P75 和负 `delta_abs_basis_bps` parent count；
- contract-level 同类描述仅标为 correlated diagnostic rows；
- `non_independence_notice`、`outcome_inspection_status=outcome_seen`、按 §1 唯一 reducer 产生的 `research_classification` 与 per-metric `metric_evidence_status`。

有限值排序后计算分位数：P25/P75 使用 nearest-rank，rank=`ceil(p*n)`，索引为 `max(1, rank)-1`；中位数沿用排序中央值或两个中央值的算术均值。`n_parent_exploratory_described=0` 时所有分布标量必须为 `null`，不能写零。

## 5. Producer / Consumer / Artifact 契约

| 边界 | Writer / producer | Consumer / validator | W2-0 处理 |
| --- | --- | --- | --- |
| W2 candidate root | 已批准 W2 collector | `load_verified_w2_evidence(...)` | 只读、精确路径和 SHA；不迁移、不修复、不写回。 |
| External Completion Audit | 独立只读 audit 会话/平台外部 artifact | W2-0 admission | 只消费 exact path+SHA+`complete`；不创建 audit writer/publisher。 |
| Historical blind receipt | 外部历史 receipt | W2-0 admission | 绑定其 bytes 作为签发时证据；本次消费强制 `outcome_seen`。 |
| W2-0 exploratory bundle | 新 W2-0 local offline runner | 新 W2-0 strict bundle loader / later review | create-exclusive、manifest-last；只含本节许可的派生 basis descriptors。 |
| W1/REEF/W2 collector | 既有 owner | 既有 consumers | 不改变、不导入 W2-0、继续拒绝不兼容 root。 |

未来 implementation 的最小代码范围预期为一个 W2-0 analysis source/storage module、一个 offline CLI、focused tests；是否拆分 storage 仅由 Plan 基于 W1 现有 create-exclusive bundle 模式决定。不得复用 W1 的 schema 或修改 W1 文件来承载 W2-0。

## 6. 输出、持久化与恢复

每个获批准执行必须写入新的 create-exclusive root：

```text
data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/<run_id>/
  stage1_6f_w2_0_denominator.jsonl
  stage1_6f_w2_0_contract_metrics.jsonl
  stage1_6f_w2_0_parent_metrics.jsonl
  stage1_6f_w2_0_summary.json
  stage1_6f_w2_0_bundle_manifest.json
```

`stage1_6f_w2_0_bundle_manifest.json` 是唯一 seal event，最后原子写入。它精确绑定本 Design/未来 Plan、W2 collection Design/Plan、network authorization、candidate manifest、external Completion Audit artifact、historical receipt 的 path+SHA，以及 `outcome_seen`、按 §1 唯一 reducer 产生的 root/metric classifications、§11 定义的 exact 20-field `authority_flags` 全 false vector、所有 artifact 的 path/length/SHA 与 `41 contracts / 27 parents / 31 window-defined contracts / 21 window-defined parents / 29 complete contracts / 19 complete parents` 的冻结上界。strict bundle loader 必须拒绝缺失、额外、非 bool 或非 `False` 的任一 `authority_flags` entry；不得以 `.get(..., False)` 或默认值修补。

写入采用同目录 temporary file、flush、fsync、read-back hash/length verification、atomic rename；任何写入、serialization、read-back、manifest 或 strict output-loader 验证失败为 `STOP=w2_0_bundle_invalid`，不发布 manifest、不修复、不重用 run ID。已 seal bundle 后的 strict-loader 拒绝使其成为只读 forensic root；不得 overwrite、append、删除或再封存。

## 7. Failure Semantics

```text
authority / external audit / historical receipt mismatch
  -> STOP=w2_0_admission_invalid; zero output
W2 strict reader rejection
  -> STOP=w2_0_candidate_root_invalid; zero output
per-contract temporal / complete-bar / endpoint coverage / index validity failure
  -> exact diagnostic_incomplete row; retain denominator identity
one metric has zero parent descriptors
  -> its metric_evidence_status=evidence_insufficient and null distribution
both metrics have zero parent descriptors
  -> research_classification=evidence_insufficient
either metric has at least one parent descriptor
  -> research_classification=exploratory_only
local serialization / atomic publication / strict bundle read-back failure
  -> STOP=w2_0_bundle_invalid; no consumable bundle
```

No exception may be converted to empty success, zero basis, zero change, synthetic timestamp, alternate root, alternate URL, retry collection or fallback metric.

## 8. L2 Research Methodology Boundary

| L2 requirement | W2-0 decision |
| --- | --- |
| Claim level | Only exploratory mechanism description; no phenomenon confirmation, statistical/economic edge or live claim. |
| Independent unit | 27 `parent_article_id` are the full denominator; contract rows under the same parent are correlated diagnostics, and 19 current complete parents are not a replacement denominator. |
| Point-in-time / hindsight | Historical ex-post input, `outcome_seen`; no confirmatory interpretation. Windows and formulas are fixed here before future execution, but this does not restore blinding. |
| Outcome distribution | Parent-level basis-change distribution only; no win rate, return, expectancy or significance. |
| Cost/friction/capacity | N/A: no trade, executable price, size, fee or holding claim is permitted. |
| Loss/MAE/tail risk | N/A: no entry, exit, PnL or survival claim is evaluated. |
| Outliers/concentration | Report parent-level min/P25/median/P75/max and parent-cluster counts; no promotion based on any outlier. |
| Conditional Alpha | N/A: no conditional strategy subgroup is permitted. |
| Promote / kill | No automatic promotion to W2-1. A future separate Design may use an independent unseen holdout only if W2-0 is judged worth following. Absence, inconsistency or insufficient evidence can stop further W2 work, but does not `falsify` a trading strategy. |

## 9. Acceptance Invariants

| ID | Invariant | Required future proof |
| --- | --- | --- |
| INV-W20-01 | Exact W2 authority binding precedes raw-row access. | Correct root/artifact positive; one SHA/path/run/verdict mutation stops before output creation. |
| INV-W20-02 | `outcome_inspection_status` 不可逆地为 `outcome_seen`；根级 `research_classification` 只能由 §1 reducer 产生，且只允许 `exploratory_only` 或 `evidence_insufficient`。 | Output and loader reject `not_seen`、`phenomenon_supported`、`alpha_candidate`、`alpha_validated`、任何确认性状态，以及不符合 §1 reducer 的分类组合。 |
| INV-W20-03 | 41 contract and 27 parent denominators persist; 31/21 window-defined and 29/19 complete counts remain explicit. | Canonical root produces complete contract and 27-row parent ledgers; temporal/no-bar mutations retain identities/parents as incomplete. |
| INV-W20-04 | Three-family expected complete-bar endpoints are exact. | Missing/duplicate/non-finite/zero-index or absent `C[0]/C[-1]` mutations become exact incomplete reason, never filled. |
| INV-W20-05 | Basis definition is deterministic and limited. | Known pure arithmetic fixture; mutations prove no price direction, return, PnL, funding or cost field can be emitted. |
| INV-W20-06 | Parent articles, not contracts, are independent descriptive units and remain conserved. | Multi-child and all-incomplete-parent fixtures prove one parent summary, 27-parent denominator conservation and no 29-as-independent statistic. |
| INV-W20-07 | Output is immutable and auditable. | Create-exclusive collision, short write, crash-before-manifest, symlink, hash mutation and post-seal rejection tests fail closed. |
| INV-W20-08 | W2-0 不得改变 W2/W1/REEF collection，且 bundle `authority_flags` 必须是上游 13-field deny vector 的 strict 20-field false superset。 | Existing W2 strict-reader tests and flags remain green；positive bundle 含 exact 20-field false vector；缺失、额外、非 bool 或任一 true flag mutation 均被 strict loader 拒绝；static scan rejects network, collector import, execution/PnL/permission code. |

## 10. Verification Strategy

Future Plan must require:

1. Task 0 baseline: exact Design and all authority SHA checks; current workspace/index/untracked scope proof; `RISK_LIVE_TRADING_ENABLED=False` AST proof.
2. Canonical positive fixture: link-or-copy only the existing verified W2 authority bytes and derive expected rows through `load_verified_w2_evidence(...)`, never handcraft cross-boundary positives.
3. Negative mutations: one declared mutation for wrong authority, receipt/status, missing family, missing `C[0]`/`C[-1]`, duplicate bar, zero index, nonfinite value, incomplete status, all-incomplete parent, parent-cluster counting, missing/extra/non-bool/true `authority_flags` entry, and post-seal bundle file/hash.
4. Crash/recovery: writer fails before manifest publication and leaves no consumable bundle; duplicate run ID stops; sealed root strict read-back is required.
5. Production wiring: CLI imports the W2-0 source only; source imports W2 strict reader but never `scripts`; no socket/network API; scanner actual RC `0` and any warning has a disposition ledger.
6. Scope proof: only Plan whitelist changes; existing W2 collector/root/manifest/auth/receipt and W1/REEF code bytes remain unchanged; ignored runtime outputs are not committed.

## 11. Safety and Authority

`authority_flags` 的 key set 必须精确等于下列 20 个字段，且每个值均为 bool `False`；缺失不等于 `False`，不得使用默认值补齐。前 13 个为 network authorization/strict reader 已冻结 deny vector，后 7 个仅为 W2-0 新增 deny fields：

```text
RISK_LIVE_TRADING_ENABLED
trade_signal_allowed
paper_trading_allowed
live_trading_allowed
execution_engine_allowed
private_api_allowed
authenticated_api_allowed
order_api_allowed
alpha_interpretation_allowed
execution_feasibility_claim_allowed
net_cost_or_profit_claim_allowed
replay_allowed
point_in_time_directional_replay_allowed
alpha_candidate_allowed
alpha_validated_allowed
network_collection_allowed
deployment_allowed
ssh_allowed
commit_allowed
push_allowed
```

This Design grants no implementation or runtime permission. It is local/offline by intent, but any future implementation still requires an approved Plan. No output from W2-0 changes `configs/base.py`, position limits, order logic or VPS state.

## 12. Open Questions

| Question | Status | Owner / handling |
| --- | --- | --- |
| 是否存在未接触的独立历史或未来 holdout 以开展确认性 W2-1 | Non-blocking for W2-0; blocking for any confirmation claim | Future research owner; no holdout discovery/collection in this scope. |
| 应否为未来候选根去除 manifest 中 raw `first_row` / `last_row` OHLC | Non-blocking for current W2-0; separate schema Design required | Future evidence-package owner; current root immutable. |
| 10 个 settlement_time_unproven 身份是否可从独立公告证据补证 | Non-blocking; blocking only for将其纳入 W2-0 | Separate semantic-evidence task; no inference or backfill here. |

## 13. Self-Review

- 范围只增加一个离线探索性 consumer/bundle，不重写 collector、root 或 schema。
- W2 collection 的 Class A/B authority 与 external Completion Audit 边界保持不变；不新增 audit writer/publisher。
- `outcome_seen` 明确禁止确认性与 Alpha 升级；探索性输出不伪装为策略结论。
- W2-0 bundle authority vector 严格继承上游 13 个 deny flags，并以 7 个 W2-0 deny flags 扩展为 exact 20-field 全 false contract；缺失字段不会被视为 false。
- 41-contract/27-parent denominator、31/21 window-defined、29/19 complete 与 10/6/2/2 缺口语义均有保留路径；无缺失替代或静默删样本。
- 无 implementation、网络、部署、交易、commit 或 push authority。
