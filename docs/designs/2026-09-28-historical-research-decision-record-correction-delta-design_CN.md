# Historical Research Decision Record Correction Delta Design

**日期：** 2026-09-28  
**状态：** `draft_for_review`  
**类型：** 历史研究决策文档纠偏；不重开策略、回测、数据采集或运行时路线。  
**交付范围：** 后续经批准的 docs-only Plan 只能按本 Design 的精确模板修改 `docs/roadmap.md` 与 `docs/project-status/current-document-index_CN.md`。

## 1. Purpose and Final Claim

本 Delta 只纠正 Route C1、Stage 1.4B-Lite 与 Cross-Sectional Factor Lab 在下游治理文档中的过度结论。它不修改原始 review、summary、策略状态、代码、配置、运行时 artifact 或任何权限。

唯一允许的 Final Claim：

> 历史文档必须区分“已停止的具体研究规格”和“该规格可支持的经济结论”。Route C1 的已记录终止原因是基线/对照匹配失败，而非成本后 EV 已证伪；B-Lite crowding-only 分支因稀疏且集中证据而停止，500 次随机基准重采样不是 500 个独立机会；已测试的 pure-price Factor Lab momentum specification 保持停止，但该结果不终止所有可能的非价格截面因子研究。

本 Delta 不声称任何路线存在正期望、可复议、可交易、可执行或可推广的 Alpha。

## 2. Frozen Authority Packet and Serial Dependency

后续 Plan 的 Task 0 必须在任何写入前逐项校验以下 exact bytes。任一 hash 不一致必须 `STOP=historical_decision_correction_authority_mismatch`。

| Authority | 路径或 identity | SHA-256 | 用途 |
| --- | --- | --- | --- |
| 历史方法学审计 | `docs/reviews/2026-09-27-historical-alpha-methodology-audit_CN.md` | `61ba2f7acb88b91db9f23a2f9f085bc493d52160d6ee411978573cb96d9f3ac4` | F-02/F-03/F-05 的纠偏边界与不重开约束 |
| L2 方法论 | `.agent/rules/L2_Alpha_Research_Methodology.md` | `806314e860bbf94d0e4332377d8bf617471f31dfcb51ffab1b646220ba8aed27` | `evidence_insufficient != strategy reopen` 的冻结语义 |
| Route C1 review | `docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md` | `c6f4eef35c87c43348d2cccfd06e2980046806c056565afeac86ef02c30e85eb` | `route_c1_baseline_match_failed` 的原始决策语义 |
| Route C1 summary | `reports/route_c1/route_c1_live_smoke_7d_summary.json` | `3314415f69539bc3370a19cc014a2637d250e9ccbd4e03649d2e627c3779aa55` | 1,536 events、904 matched、0.5885416667 match rate 与无 PnL/win-rate 字段 |
| B-Lite review | `docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md` | `fee493979a97c4f3fe3a182988e9bd36f877197a4eb7f1606d089affe975824e` | `crowding_lite_failed` 与 `stop_crowding_only_branch` |
| B-Lite summary | `reports/external_signal_shadow/stage1_4b_lite_funding_oi_price_crowding_replay_500trials_real_summary.json` | `7872b201559239e77ae7e109f4dc2b00a161494487267ee2396f0c41fb07ca55` | 21 events、6 days、500 baseline trials 与集中度事实 |
| CMOM review | `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` | `720b7f36bd4084883ecbb1dec9c7588e516d8d1f7207e3f0ec0efb2934704cd1` | `stop_price_only_momentum` 的限缩范围 |
| CMOM summary | `reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json` | `b2429af21c9a7fb42ed919efa0c3542498346dcd2a1833ac1d7a8a2d396ca244` | 77 周频调仓、30 bps 情景亏损与回撤事实 |
| Stage 1.6 conclusion closure publication | commit `d2ad662b6b10bc495fc07a23ad8a0aa0fd396f0d` | N/A | 该 commit 已完成旧 Plan 对同一 `roadmap.md` 的发布；本 Delta 只可基于其后字节继续工作 |
| reviewed roadmap baseline | `docs/roadmap.md` | `217bb60180c4300ca03a5efe7335f00b7ae313c249216f3a1235e314a3531f32` | 后续 Plan 的唯一允许输入 baseline |
| reviewed document-index baseline | `docs/project-status/current-document-index_CN.md` | `509589227b2c5518b4e43b08fe8ac12bd620ce448028b8b276e2a75d074c414e` | 后续 Plan 的唯一允许输入 baseline |

### 2.1 Publication order is already resolved

Stage 1.6 conclusion-closure Plan 已实施、完成独立 Completion Audit 并由上述 commit 发布。因此，本 Delta 绝不与该旧 Plan 并行、重排或合并执行。后续 docs-only Plan 必须以本节列出的 post-publication target bytes 为 baseline；任一目标文件不匹配时停止，不能自行 rebase、合并或选择旧 baseline。

后续 Plan 还必须接收用户批准语句中的 `APPROVED_DELTA_DESIGN_SHA256`，在任何生成、备份或写入前验证它等于本 Design 的当时 exact bytes。该值将写入 §5.2 的索引元数据模板；缺失或不匹配必须 `STOP=historical_decision_correction_design_approval_mismatch`。

### 2.2 Required Git attestation

后续 Plan 的 Task 0 必须机械验证该 publication dependency，而不是仅相信表格文字：

```bash
git cat-file -e d2ad662b6b10bc495fc07a23ad8a0aa0fd396f0d^{commit} || exit 1
git merge-base --is-ancestor d2ad662b6b10bc495fc07a23ad8a0aa0fd396f0d HEAD || exit 1
test "$(git show d2ad662b6b10bc495fc07a23ad8a0aa0fd396f0d:docs/roadmap.md | shasum -a 256 | awk '{print $1}')" = \
  217bb60180c4300ca03a5efe7335f00b7ae313c249216f3a1235e314a3531f32 || exit 1
```

任一步失败必须 `STOP=historical_decision_correction_stage1_6_publication_dependency_mismatch`。这只证明本 Delta 接续已经发布的 Stage 1.6 文档基线，不授予 commit、push 或任何 runtime authority。

## 3. Confirmed Facts

### 3.1 Route C1 price-only proxy

- 原始 summary 的顶层 decision 为 `route_c1_baseline_match_failed`。
- `event_count=1536`，`matched_event_count=904`，`baseline_match_rate=0.5885416667`，低于冻结门槛 `0.70`。
- 原始 summary 不包含净 PnL 或交易胜率字段。
- 可记录的事实仅为：已测 price-only proxy 因对照匹配不足而停止推广；经济 edge 未建立。不得记录为“成本后 net edge <= 0 已被证明”、“胜率不达标导致终止”或“Route C1 已证伪”。

### 3.2 Stage 1.4B-Lite crowding-only replay

- 原始顶层 decision 为 `crowding_lite_failed`，next action 为 `stop_crowding_only_branch`。
- 三类候选事件数为 13、0、8；总计 21 events、6 days、5 symbols。
- `random_baseline_trials=500` 是随机基准重采样次数，不是独立机会计数。
- 全局 `top_5_positive_events_gross_profit_share=0.8928914131`；证据存在稀疏与集中问题。
- B-Lite 没有 liquidation leg，且原 artifact 禁止将 crowding-only 结果推广为完整 derivatives-stress composite 结论。
- 可记录的事实仅为：crowding-only 分支已停止/降优先，证据不足以建立独立 Alpha；不得记录为“500 个独立试验已确认 no Alpha”或“全 derivatives-stress 路线被证伪”。

### 3.3 Cross-Sectional Factor Lab

- 30d price-only momentum 与 14d CMOM 都经过 77 次周频调仓评估。
- 30 bps 成本情景下，30d momentum total return 为 `-84.0536526261%`、max drawdown 为 `84.4405601471%`；14d CMOM total return 为 `-75.3217357415%`、max drawdown 为 `75.3217357415%`。
- 原 review 的 next action 是 `stop_price_only_momentum`，明确不终止整个 Factor Lab；非价格因子若要研究，必须是新假设与独立 Design。
- 可记录的事实仅为：已测试 pure-price cross-sectional momentum specification 保持停止，因其在已测成本情景中组合表现为负且回撤很大；不得记录为“所有 cross-sectional factors 已证伪”或“整个 Factor Lab 永久终结”。

## 4. Two-Layer Decision Semantics

本次不建立全项目 schema，也不修改原始 historical artifacts。未来目标文档只可使用下列冻结语义：

| Route | Research evidence state | Portfolio action |
| --- | --- | --- |
| Route C1 price-only proxy | `evidence_insufficient_control_matching`; economic edge `not_established` | `stopped_no_promotion` |
| Stage 1.4B-Lite crowding-only | `evidence_insufficient_sparse_concentrated`; full composite `not_evaluated` | `stopped_crowding_only` |
| Tested pure-price Factor Lab momentum | `negative_cost_scenario_performance_and_large_drawdown_for_tested_price_only_specification` | `retain_closed_for_tested_price_only_specification` |

这些 labels 只约束本 Delta 的文档语义，不能新增为 config、JSON schema、API 字段、策略状态机或 runtime authority。`evidence_insufficient` 不是重新研究授权。

## 5. Exact Mutable Set and Canonical Transformations

### 5.1 Mutable Set

唯一允许的未来写入是以下 12 个完整 range。Plan 必须从 §2 baseline 派生两份完整 expected documents，并验证实际文件与 expected document byte-for-byte 相等；不允许“等价中文”、自由改写、局部 token 判断或任何额外 prose。

| ID | 文件 | mutable range | 唯一允许 replacement |
| --- | --- | --- | --- |
| R1 | `docs/roadmap.md` | Research Track Matrix 的 Cross-Sectional Factor Lab 行 | §5.2 `ROADMAP_FACTOR_MATRIX_ROW` |
| R2 | `docs/roadmap.md` | `## 5. Completed and Falsified Work` heading | §5.2 `ROADMAP_HISTORICAL_SECTION_HEADING` |
| R3 | `docs/roadmap.md` | §5 Route C1 条目 | §5.2 `ROADMAP_C1_ENTRY` |
| R4 | `docs/roadmap.md` | §5 B-Lite 条目 | §5.2 `ROADMAP_BLITE_ENTRY` |
| R5 | `docs/roadmap.md` | §5 Factor Lab 条目 | §5.2 `ROADMAP_FACTOR_ENTRY` |
| R6 | `docs/roadmap.md` | 2026-06-10 Decision Log 行 | §5.2 `ROADMAP_FACTOR_LOG` |
| R7 | `docs/roadmap.md` | 2026-06-18 Decision Log 行 | §5.2 `ROADMAP_BLITE_LOG` |
| R8 | `docs/roadmap.md` | 2026-07-05 Decision Log 行 | §5.2 `ROADMAP_C1_LOG` |
| R9 | `current-document-index_CN.md` | 现有“使用说明”引用行之后、首个 `---` 之前的 header/metadata 局部治理纠偏记录 | §5.2 `INDEX_CORRECTION_METADATA` |
| R10 | `current-document-index_CN.md` | Stage 1.4B table row | §5.2 `INDEX_BLITE_ROW` |
| R11 | `current-document-index_CN.md` | 完整 §4.3 subsection | §5.2 `INDEX_ROUTE_C1_SECTION` |
| R12 | `current-document-index_CN.md` | 完整 §4.4 subsection | §5.2 `INDEX_FACTOR_SECTION` |

### 5.2 Exact canonical text

`<APPROVED_DELTA_DESIGN_SHA256>` 只能被 Task 0 已验证、且与用户批准语句相同的 64 位 SHA-256 替换一次。其余字符、换行、Markdown 标记和中英文均为 exact bytes。

`ROADMAP_FACTOR_MATRIX_ROW`

```markdown
| **Cross-Sectional Factor Lab** | `stopped` | `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` (2026-06-10) | Tested 30d/14d pure-price momentum had negative cost-scenario portfolio performance and large drawdowns; this Stage A2 evidence does not evaluate or falsify non-price factors. | Retain tested price-only specification closed; any non-price factor requires a new L2 Design. | Not applicable to untested factors. |
```

`ROADMAP_HISTORICAL_SECTION_HEADING`

```markdown
## 5. Historical Completed and Stopped Research
```

`ROADMAP_C1_ENTRY`

```markdown
1. **Route C1 Price-Only Proxy 7-Day Live Smoke Test**:
   - Document: `docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md` (2026-07-05).
   - Finding: `stopped_no_promotion`. 904 / 1536 events achieved baseline/control matching (58.85416667% < 70%); the economic edge is not established. This is neither a cost-adjusted EV nor a win-rate falsification.
```

`ROADMAP_BLITE_ENTRY`

```markdown
2. **Stage 1.4B-Lite Crowding-Only Replay**:
   - Document: `docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md` (2026-06-18).
   - Finding: `stopped_crowding_only`. The 21 events across 6 days had candidate counts 13 / 0 / 8; 500 baseline resampling trials are not 500 independent opportunities, and the top five positive events contributed 89.28914131% of gross positive profit. This does not evaluate or falsify a full derivatives-stress composite.
```

`ROADMAP_FACTOR_ENTRY`

```markdown
3. **Cross-Sectional Factor Lab Stage A2 (CMOM Factor)**:
   - Document: `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` (2026-06-10).
   - Finding: `retain_closed_for_tested_price_only_specification`. Across 77 weekly rebalances under the 30 bps cost scenario, tested 30d and 14d pure-price momentum had negative portfolio performance and large drawdowns. This does not falsify every cross-sectional factor.
```

`ROADMAP_FACTOR_LOG`

```markdown
* **2026-06-10**: Retained the tested 30d/14d pure-price momentum specifications closed after 77 weekly rebalances showed negative 30 bps cost-scenario portfolio performance and large drawdowns; non-price factors are outside this closure's scope and were not reopened.
```

`ROADMAP_BLITE_LOG`

```markdown
* **2026-06-18**: Stopped the Stage 1.4B-Lite crowding-only branch: 21 events over 6 days, candidate counts 13 / 0 / 8, and 500 baseline resampling trials rather than independent opportunities. The evidence was sparse and concentrated; no full derivatives-stress conclusion or Alpha claim follows.
```

`ROADMAP_C1_LOG`

```markdown
* **2026-07-05**: Stopped promotion of the Route C1 price-only proxy after 904 / 1536 baseline/control matches (58.85416667% < 70%); its economic edge is not established. This is not a net-EV or win-rate falsification.
```

`INDEX_CORRECTION_METADATA`

```markdown
> **局部治理纠偏 Design 日期：** 2026-09-28；仅修正 C1、B-Lite 与 Factor Lab 的历史决策措辞，未执行全仓库重新扫描。
> **纠偏 Design SHA-256：** `<APPROVED_DELTA_DESIGN_SHA256>`。
```

`INDEX_BLITE_ROW`

```markdown
| **Stage 1.4B** | Review | [docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md](../reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md) | `historical_reference` | `stopped_crowding_only` | Yes | Completed | None | Stage 1.4C | 21 events / 6 days; 500 baseline resampling trials are not independent opportunities; evidence sparse/concentrated, not a full derivatives-stress or no-Alpha conclusion |
```

`INDEX_ROUTE_C1_SECTION`

```markdown
### 4.3 Trend Regime / Liquidation Cascade (Priority 2 Strategy & Route A/B/C/C1)
- **状态**：`implemented` (核心策略在 `configs/base.py`) / `stopped_no_promotion` (Route C1 price-only proxy)
- **核心文档**：
  - [docs/plans/2026-05-26-trend-liquidation-phase1a-implementation-plan.md](../plans/2026-05-26-trend-liquidation-phase1a-implementation-plan.md) (`implemented`)
  - [docs/plans/2026-06-02-route-c1-price-only-implementation-plan_CN.md](../plans/2026-06-02-route-c1-price-only-implementation-plan_CN.md) (`implemented`)
  - [docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md](../reviews/2026-07-05-route-c1-live-smoke-7d-review.md) (`stopped_no_promotion`: 904 / 1536 baseline/control matches; 58.85416667% < 70%; economic edge not established)
- **结论**：Route A/B 受到 API 限频与数据完整性拦截，Route C1 纯价格代理因 baseline/control matching failed 而停止推广，不构成成本后 EV 或胜率证伪；现仅保留 1h 波动率突破 (2.5x) + OI 动量方向性框架。
```

`INDEX_FACTOR_SECTION`

```markdown
### 4.4 Cross-Sectional Factor Lab (截面因子实验室)
- **状态**：`historical_reference` / `retain_closed_for_tested_price_only_specification`
- **核心文档**：
  - [docs/strategy_specs/cross_sectional_factor_lab_implementation_guide_CN_v3.md](../strategy_specs/cross_sectional_factor_lab_implementation_guide_CN_v3.md) (`historical_reference`)
  - [docs/reviews/2026-06-09-cross-sectional-factor-lab-stageA1-closure-review_CN.md](../reviews/2026-06-09-cross-sectional-factor-lab-stageA1-closure-review_CN.md) (`review_approved`)
  - [docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md](../reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md) (`retain_closed_for_tested_price_only_specification`: tested 30d/14d pure-price momentum had negative 30 bps cost-scenario portfolio performance and large drawdowns)
- **结论**：已测试 pure-price 截面动量规格保持关闭；该结果不评估、也不证伪所有 cross-sectional factors。任何非价格因子研究必须另起 L2 Design。
```

### 5.3 No-Touch Set

- `docs/project-status/current-project-state_CN.md`：没有本 Delta 需要纠正的 C1、B-Lite 或 Factor Lab 断言。
- 除 R1-R12 外的全部字节；R11 必须保留 Route A/B 的既有文本与链接，不能借完整 subsection replacement 扩面。
- 全部原始 reviews、summaries、reports、source code、configs、tests、runtime roots、VPS runbooks 与 external audit artifacts。
- Stage 1.3 R10 的状态、阈值、样本、`reconsider_under_expectancy_framework` 或任何 re-admission 结论。
- Route A/B、Liquidation-only 5m、Extreme Funding、Stage 1.5、Stage 1.6 与所有其他路线。

若正确纠偏需要 No-Touch Set 中任一文件或任何不在 R1-R12 的字节变化，必须 `STOP=historical_decision_correction_scope_drift` 并另起 Design。

## 6. Acceptance Invariants

| ID | Invariant | Required mechanical evidence |
| --- | --- | --- |
| INV-HDRC-01 | 所有下游修正绑定 §2 exact authority 与经用户批准的 Delta bytes | Task 0 重算全部 SHA-256，并验证 `APPROVED_DELTA_DESIGN_SHA256` |
| INV-HDRC-02 | 两份输出只由 exact baseline 加 R1-R12 生成 | 对每份完整实际文件做 byte-for-byte equality against independently derived expected document |
| INV-HDRC-03 | C1 只表达 control/baseline matching failed 与 economic edge not established | R3、R8、R11 exact template equality；不得在 owned ranges 另加 C1 断言 |
| INV-HDRC-04 | B-Lite 不把 500 baseline trials 表述为独立机会或 no-Alpha 证明 | R4、R7、R10 exact template equality；不得在 owned ranges 另加 B-Lite 断言 |
| INV-HDRC-05 | Factor Lab 结论只覆盖 tested pure-price momentum specification | R1、R2、R5、R6、R12 exact template equality；不得在 owned ranges 另加 Factor Lab 断言 |
| INV-HDRC-06 | 文档纠偏不授予研究、策略或运行时权限 | promotion/negative semantic gate 仅检查 R1-R12；whole-document equality 证明 outside-owned bytes 未变 |
| INV-HDRC-07 | 不破坏用户已有工作区与 Git index 状态 | 记录并逐项比较 pre-existing path ledger：path、XY、worktree state/SHA/mode、index blob/mode/stage；不要求整个 worktree clean |
| INV-HDRC-08 | 两文档只可通过单文件 atomic publish 进入可识别、单调安全的发布与恢复状态 | §7 State x Artifact、Transition x Failure、same-filesystem `os.replace()`、candidate/parent `fsync()` 与每次 publish 后 exact-byte recheck |

## 7. Two-Document Publication and Recovery Contract

不存在受消费者验证的 manifest；不得再使用 `manifest-last` 术语或创建新 manifest subsystem。后续 Plan 必须在 `/tmp` 创建唯一 `EXECUTION_PROVENANCE_DIR`，其中保存同一次发布尝试的 attempt identity、authority hashes、两份 baseline copies、两份 expected document copies、target index-entry snapshot 与完整 pre-existing provenance ledger。验证两份 candidate、实际 authority 和 provenance 后，按 `current-document-index_CN.md -> roadmap.md` 顺序发布。索引是更高优先级事实入口，因此崩溃时先保证高权威消费者不继续读取旧过度结论。

### 7.1 Atomic publication primitive

每次 target publish 必须使用以下唯一原语：`durable verified candidate -> os.replace(candidate, target) -> fsync(target parent) -> exact-byte recheck`。candidate 必须是 regular non-symlink file，且 `os.stat(candidate).st_dev == os.stat(target.parent).st_dev`；不相等必须 `STOP=historical_decision_correction_cross_filesystem_publish`。Plan 必须在 `os.replace()` 前对 candidate file descriptor 执行 `flush()` 和 `os.fsync()`，成功 replace 后以 read-only directory descriptor 对 target parent 执行 `os.fsync()`，随后重新读取 target 并验证它精确等于 provenance bundle 中的 expected copy。

禁止 `target.write_text(...)`、`open(target, "w")`、`cp candidate target`、truncate/rewrite、跨 filesystem move 及任何非 `os.replace()` 的 target 写入。该 primitive 保证进程崩溃时 target 只会是旧的 exact bytes 或新的 exact bytes，不会是 partial/torn bytes；任一步错误或 recheck 不一致必须停止，不得继续第二个 publish。

### 7.2 State x Artifact matrix

| State | index bytes | roadmap bytes | provenance bundle | candidates / expected copies | index snapshot + non-target ledger | consumer safety / next action |
| --- | --- | --- | --- | --- | --- | --- |
| `before` | exact §2 baseline | exact §2 baseline | absent or a fresh-start bundle with no durable candidates; neither is resume authority | absent | absent or fresh snapshot/ledger | fresh-start preflight may create a new attempt; no target write |
| `staged` | exact §2 baseline | exact §2 baseline | valid same-attempt bundle | both candidates durable and expected copies hash-verified | durable and hash-verified | only atomic index publish is allowed |
| `index_published` | exact expected index | exact §2 roadmap baseline | valid original bundle required | index candidate consumed; both expected copies remain; roadmap candidate durable | exact original snapshot/ledger required | index is corrected; resume may only atomic-publish roadmap |
| `both_published` | exact expected index | exact expected roadmap | valid original bundle required | candidates consumed; both expected copies remain | exact original snapshot/ledger required | both consumers see corrected bytes; only full validation/review/audit remains |
| any other state | unknown, mixed, partial or non-regular bytes | unknown, mixed, partial or non-regular bytes | any | any | any | `STOP=historical_decision_correction_publication_state_corrupt`; no guess, search/replace, reset or overwrite |

### 7.3 Transition x Failure matrix

| Transition | Failure before / during | Required resulting interpretation | Restart action |
| --- | --- | --- | --- |
| `before -> staged` | candidate creation, flush, fsync or candidate hash validation fails | both targets remain §2 baseline; incomplete bundle is not authority | fresh start only after both targets re-pass fresh-start preflight; never reuse an incomplete bundle |
| `staged -> index_published` | pre-replace failure leaves index baseline; crash during/after `os.replace()` yields only baseline or expected index bytes | baseline is `staged`; expected index plus baseline roadmap is `index_published`; any other bytes are corrupt | baseline state may fresh-start; `index_published` may resume only with original valid bundle |
| `index_published -> both_published` | pre-replace failure leaves `index_published`; crash during/after `os.replace()` yields only baseline or expected roadmap bytes | expected index plus baseline roadmap remains `index_published`; both expected bytes is `both_published`; any other bytes are corrupt | resume only with original valid bundle; never rewrite index |
| `both_published -> validation` | validation, review or audit fails | both expected bytes remain published but no completion authority exists | retain bytes, stop, and route findings through the approved remediation workflow; do not silently rollback or rebaseline |

每个 transition 前都必须重新检查：目标为 regular non-symlink file、其当前 bytes 是该状态允许的 exact bytes、target Git index entry 未被改动、§2 authorities 未漂移。publish index 成功而 roadmap 未开始或失败时，restart 必须识别 `index_published` 并只完成 roadmap；不可回滚或修改任何用户自有路径。任何恢复完成后必须从头重跑所有 gates。

Task 0 必须分为互斥的两种 preflight：

1. `fresh_start_preflight`：两份 target 都必须是 exact §2 baseline、regular non-symlink、未 staged，且 Git index entries 等于 snapshot；随后创建新的 `EXECUTION_PROVENANCE_DIR` 并记录完整 provenance。target 已 dirty、staged、symlink 或 baseline 不匹配时必须停止，不能清理它们。
2. `resume_preflight`：只接受 `index_published` 或 `both_published`，且必须由调用方显式提供同一次发布尝试的原 `EXECUTION_PROVENANCE_DIR`。target worktree 相对 Git baseline 为 dirty 在这两个状态中是预期行为；它们必须分别精确等于本次 attempt 的 expected copies，target Git index entries 必须仍等于 original snapshot，所有 non-target pre-existing paths 必须仍匹配 original ledger。resume 不得重新采集 provenance 或将现状当作新 baseline。

原 attempt provenance bundle 缺失、损坏、attempt identity 不匹配，或其中 baseline/expected/ledger bytes 无法通过 hash 验证时，必须 `STOP=historical_decision_correction_resume_provenance_unavailable`。主机重启导致 `/tmp` 丢失时安全动作也是 STOP，不是猜测恢复。目标以外的 pre-existing dirty、staged 或 untracked bytes 不是错误，但必须按 INV-HDRC-07 原样保留；严禁为追求 clean worktree 使用 `reset`、`checkout`、`restore` 或 unscoped cleanup。

## 8. Future Plan Requirements

本 Delta 经独立 review 与用户批准后，后续 Implementation Plan 必须是 docs-only，并至少包含：

1. Task 0：用户 implementation approval 必须同时绑定 `APPROVED_DELTA_DESIGN_PATH`、`APPROVED_DELTA_DESIGN_SHA256`、`APPROVED_PLAN_PATH`、`APPROVED_PLAN_SHA256`；在任何写入前验证四者 exact bytes、§2 authority packet 与 §2.2 Git attestation。`fresh_start_preflight` 必须验证当前两份 target 等于 §2 baselines；`resume_preflight` 必须验证原 provenance bundle 中的两份 baseline copies 等于 §2 baselines，且当前 targets 只匹配 §7.2 的合法 resume state，绝不要求它们再次等于 §2 baselines。
2. 按 §7 区分 `fresh_start_preflight` 与 `resume_preflight`；只有 fresh start 可创建 `EXECUTION_PROVENANCE_DIR`，resume 必须校验同次 attempt 的原 bundle。
3. 从 exact baseline 应用 R1-R12 生成两份完整 `/tmp` expected documents；使用 `APPROVED_DELTA_DESIGN_SHA256` 替换 R9 的唯一 placeholder，随后验证 each candidate whole-document equality。
4. 每个 exact range replacement 的 positive proof、一个针对 R1-R12 任意单字符变异的 negative mutation proof，以及 outside-owned byte preservation proof。
5. 严格实现 §7 的 `before -> staged -> index_published -> both_published` transition/recovery table；不得创建 manifest 或假设双文件 rename 原子性。
6. `git diff --check`、`anti_shortcut_scan.py` actual RC、scope/index/provenance proof、`requesting-code-review` 与 fresh independent Completion Audit 路由。
7. 所有权限保持 false；Plan 不得包含网络、SSH、VPS、数据采集、回测重跑、paper/live trading、commit、push 或 deployment。

## 9. Non-Goals and Routing

- 不判定 Route C1、B-Lite、Factor Lab 或 R10 是否具有 Alpha。
- 不重算均值、收益、PIT、独立机会、成本、滑点、容量、MAE、尾部或置信区间。
- 不将任何 historical outcome 样本重新标记为 blind 或 confirmatory。
- 不改写原始 review 的历史事实，只纠正下游摘要对其结论范围的描述。
- 不创建双状态数据库、枚举、配置、运行时字段或发布 manifest。

| Question | Current disposition | Required future route |
| --- | --- | --- |
| R10 原始 event ledger/PIT/独立机会是否可再准入？ | 本 Delta 不回答 | 独立 Stage 1.3 evidence re-admission Design |
| C1 能否通过新的对照设计建立经济 edge？ | 未建立，且不在 scope | 独立 Route C1 counterfactual/economic Design |
| 非价格 Factor Lab 是否有可测机制？ | 本 Delta 不主张 | 独立 Factor hypothesis Design |
| B-Lite full derivatives-stress composite 是否可研究？ | B-Lite 未评估 full composite | 独立 data/provenance-first Design |

## 10. Revision Ledger and Self-Review

| Review finding | Disposition in this revision |
| --- | --- |
| P0: 与 Stage 1.6 roadmap Plan 的无序冲突 | §2.1 固定为 post-`d2ad662` baseline；禁止 parallel/rebase |
| P0: 自由语义与 token validator | §5 R1-R12 exact templates + whole-document equality |
| P0: 双文档部分发布、atomicity 与 resume | §7 same-filesystem durable candidate + `os.replace()` + parent `fsync()`；fresh-start/resume split + same-attempt provenance bundle |
| P1: semantic gate 误扫全文件 | §6 限制 gates 至 owned ranges；outside-owned bytes 由 equality 证明 |
| P1: clean worktree 与用户改动冲突 | INV-HDRC-07/§7 使用 provenance ledger，禁止 reset/cleanup |
| P1: L2 authority 缺失 | §2 加入 exact L2 hash |
| P1: Factor survival 表述过度 | §3.3/§4 使用 tested cost-scenario performance + large drawdown |
| P1: index metadata 不透明 | R9 精确记录 Design 日期、approved Design SHA 与非全仓扫描 |
| P1: Plan/commit identity 未机械绑定 | §2.2 与 §8 绑定 Stage 1.6 Git attestation、approved Plan bytes 与 explicit implementation approval |
| P0: Factor Lab non-price historical全称断言过宽 | §5.2 改为当前 Stage A2 evidence/本 closure scope 的限缩语义 |
| P1: State/transition matrix 与 resume baseline 表述不完整 | §7.2/§7.3 增加完整矩阵；§8.1 区分 fresh/resume baseline 验证 |
| Evidence gap: C1 `data_semantics` raw field | 删除该非 Final Claim 必要断言；不需要额外 evidence |

- [x] 只含 docs authority 纠偏，没有代码、运行时、网络或交易工作。
- [x] 每条纠正结论均绑定原始 review、summary、L2 与历史方法学审计。
- [x] 明确区分 evidence state、portfolio action 与 Alpha authority。
- [x] R10、C1 新设计、B-Lite full composite、非价格 Factor 全部留给独立 future Design。
- [x] `current-project-state_CN.md` 已核查并排除出 scope。
- [x] 本候选需要 Model B Closure Review；作者不得自我批准或开启任何权限。
