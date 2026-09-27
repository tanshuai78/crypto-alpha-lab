# Stage 1.6F: 终局基差诊断结论边界与文档冻结 Delta Design

**日期：** 2026-09-26
**状态：** `draft_for_review`
**类型：** 研究结论与下游文档 authority 修正；不是策略、风险模块、Implementation Plan 或运行时 Design。
**本轮交付：** 仅此 Design candidate；不授权 implementation、文档改写、commit、push、deployment、SSH、网络、replay、paper trading 或 live trading。

## 1. 目的与 Final Claim

本 Delta 只冻结 Stage 1.6 现有证据所允许的研究结论，并为未来经批准的文档维护 Plan 定义更正边界。它不产生新数据、重跑诊断、建立策略规则或修改任何现有 artifact。

唯一允许的 W2-0 结论是：在已封存的 `w2_0_exploratory_20260926T071500Z` 输出中，`[-24h, 0h]` 终局窗口的绝对基差没有显示出“通常自然向零收敛”的描述性模式。该结论的研究等级严格为 `exploratory_only`，不是 `falsified`、`phenomenon_supported`、`alpha_candidate`、风险阈值或交易规则。

因此，Stage 1.6 目前没有支持下列任一主张的证据：

- 下架事件存在可交易的方向性 Alpha；
- 反向基差扩张存在 Alpha；
- 任意数值基差阈值，例如 `150 bps`，可作为熔断或平仓阈值；
- 结算前 `24h`、`48h` 或任何固定时点必须平仓；
- W1 的事后描述性价格、资金费率、深度或未平仓量统计可升级为策略、因果或执行结论；
- Stage 1.6R 已有获批准的 runtime consumer、风险模块或实施任务。

## 2. 已确认事实与 Evidence Hierarchy

### 2.1 冻结 authority packet

| 对象 | 路径 | SHA-256 / 身份 |
| --- | --- | --- |
| W2 evidence Design | `docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md` | `11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303` |
| W2 evidence Plan | `docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md` | `183689a6b786ccd3dce9f74f5d1fc2e9ccc1741d80f243f5724dd3b7de149229` |
| W2 network authorization | `configs/authorizations/network_auth_w2_candidate_run_20260925_001.json` | `0189fd4a922c87811e25793b62d12d6ba76ad92e60a95236a3fe54f024fa5dbf` |
| W2 candidate manifest | `data/external_signal_shadow/stage1_6f/w2_evidence_candidates/w2_candidate_run_20260925_001/candidate_manifest.json` | `1bd45df8d27e85b40d30500148575780740c6d089b5700e43c1cbfc22a4a0cea` |
| W2-0 Design | `docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-design_CN.md` | `58f4cf8638b05a1c268578ace0ed8d4c6b8b794daa4d94107e2af349d22862c4` |
| W2-0 Plan | `docs/plans/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-implementation-plan_CN.md` | `17dc74ee85e66f490460e745e97aa2ec6628baccf9039f69d9e78ed49b0666fe` |
| W2-0 external Completion Audit | `/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_0_exploratory_diagnostic_completion_audit_review.md` | `1c034753b3d2ec41b53122967e2282d5ed0f1ded8d4100b1935064a3ad73271e`; exact `Final Verdict: COMPLETE`，P0/P1/P2 均为 0 |
| W2-0 sealed manifest | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json` | `74ce94ac0f21125b97590228664f11ed836a0ed7836e2b75ed1ac35d555a317f` |
| W2-0 summary | 同一 root 的 `stage1_6f_w2_0_summary.json` | `4af9aa1bad656d096f0eaffe5bd17d3e98bbc553329949dd6319507420da26b3` |

上述 sealed manifest 是本 Delta 的 W2-0 事实来源。`docs/roadmap.md` 与 `docs/project-status/current-project-state_CN.md` 是待未来 Plan 更正的下游叙述文件，不是本结论的 authority。

### 2.2 事实与非事实

| 分类 | 冻结内容 |
| --- | --- |
| W1 facts | 41 个候选 contract、27 个 distinct `parent_article_id`；输入是 `historical_ex_post_candidate`，且 `point_in_time_source_validated=False`。W1 仅有描述性统计，禁止推导方向、成本、执行或 Alpha。 |
| W2 collection facts | 41 contract / 27 parent 完整分母；W2-0 admission 保留 `31` window-defined contract、`21` window-defined parent、`29` complete contract、`19` complete parent。缺口仍在分母中，未被删除或填补。 |
| W2-0 facts | `outcome_inspection_status=outcome_seen`、`research_classification=exploratory_only`、两类 metric 均为 `exploratory_described`。独立描述单位是 `parent_article_id`，contract 行不是独立样本。 |
| W2-0 implementation-completion fact | 外部独立只读 Completion Audit 对 exact W2-0 Design、Plan、sealed manifest、production strict reader、artifact hash/length、scope、scanner、测试和权限边界给出 `COMPLETE`。该事实只证明实施与封存 bundle 的完整性；不提高 W2-0 结果的研究等级，也不证明 Alpha、执行、风险规则或因果机制。 |
| 非事实 | 该输出没有收益、PnL、手续费、滑点、盘口可执行深度、仓位、资金占用、清算距离、点在时可用性或交易执行证据。 |

## 3. 当前终局窗口的描述性结果

定义固定为 W2-0 的 `delta_abs_basis_bps = abs(basis_last) - abs(basis_first)`。负值表示朝零收敛，正值表示绝对基差拉大。下表由 sealed `stage1_6f_w2_0_parent_metrics.jsonl` 的 19 个 `exploratory_described` parent 行独立重算；其目的仅是冻结描述性分布，不能用于拟合阈值。

| 指标 | P25 | P50 | P75 | 负值 parent | 正值 parent |
| --- | ---: | ---: | ---: | ---: | ---: |
| `median_delta_abs_perp_basis_bps` | +12.407940689016186 | +102.55655569154337 | +446.66861842102907 | 3 / 19 | 16 / 19 |
| `median_delta_abs_mark_basis_bps` | +4.015736373189862 | +41.71871219723057 | +283.01068213762466 | 3 / 19 | 16 / 19 |

**允许的事实表述：** 在该历史、事后、已见 outcome 的 19 个 complete parent 子集中，两类终局绝对基差的中位数均为正，且各有 16/19 个 parent 的绝对基差拉大。故“终局窗口通常自然收敛”未获该描述性样本支持。

**口径：** P25/P50/P75 与 sealed `stage1_6f_w2_0_summary.json` 完全一致，均为 W2-0 已冻结的 nearest-rank（最近秩）分位数；本 Delta 不定义或使用另一套插值估计器。

**禁止的升级表述：** 该结果不证明“反向操作可盈利”、不证明任何事件因果机制、不能确定拐点和进入时机，也不能把 P25/P50/P75 或任一极端事件转成 hard stop、risk veto、强平边界或 Stage 1.5 的持仓/退出规则。

## 4. 核心问题、决策与研究状态

### 4.1 核心问题

下游项目文档目前混合了三个不同等级的陈述：已封存的 W2-0 描述性事实、未经证据支持的数值风险规则，以及尚未定义或验证的下架策略与 consumer。该混合会把 `outcome_seen` 的探索性观察错误提升为执行约束。

### 4.2 决策

1. `[-24h, 0h]` 的自然终局收敛假设状态固定为 `not_supported_in_current_exploratory_sample`，而不是 L2 定义的 `falsified`。
2. 下架事件的方向性策略、收敛策略、反向扩张策略和任何执行机制均不得写为 Alpha；其唯一状态映射见 §4.3。
3. `Stage 1.6R` 是尚未立项的 Security Incident Risk-Veto（安全事故风险否决）路线，不是下架事件 consumer。本 Delta 不为其创建 consumer、模块或实施任务。
4. 当前研究分支的合理动作是停止把现有 W1/W2/W2-0 样本用于阈值或策略参数形成。除非低成本获得未用于现有规则形成的独立历史 parent cohort，否则不开展确认性 W2-1。
5. 在本 Delta 获批准且另一个文档维护 Plan 获批准前，不修改任何下游叙述或项目状态文件。

### 4.3 唯一研究状态 reducer

1. `not_supported_in_current_exploratory_sample` 仅是描述性发现标签，不是新增 L2 research state。
2. 尚未形成具体、预注册、可检验规则的下架方向性策略、终局收敛策略与反向扩张策略，唯一状态为 `hypothesis_only`。
3. 已被明确提出、但现有 admissible evidence 缺少可执行价格、费用、滑点、容量、持仓路径或订单状态而无法评估或支持的执行可行性/成本主张，唯一状态为 `evidence_insufficient`；它不构成策略规则。
4. 任何未来 claim 必须先按上述 reducer 归类；不得把 `outcome_seen`、`exploratory_only` 或描述性标签改写为 `falsified`、`phenomenon_supported`、`alpha_candidate` 或 `alpha_validated`。

## 5. Scope、影响锥与非目标

本 Delta 的直接产物仅是本文件。获批准后，未来独立的文档维护 Plan 可在严格核验 Section 2 authority 后，且仅可修改：

- `docs/roadmap.md`；
- `docs/project-status/current-project-state_CN.md`。

未来 Plan 必须将上述文件中与本 Delta 冲突的 run root、对象数、研究状态、`falsified`、数值熔断、固定提前退出、W1 方向性/Carry 解释和未经测量的因果叙述，降级或移除为符合 Sections 3-4 的事实边界。历史 review 是其发布时的审查记录，除非另有 authority，不得回写。

**Non-Goals：**

- 不改 `configs/base.py`、交易权限、风控阈值、订单逻辑、collector、strict reader、W1/W2/W2-0 source、测试或 sealed artifact；
- 不创建 Stage 1.6R Security Incident Risk-Veto 模块，也不创建任何未来下架持仓、退出或风险 consumer 的模块、CLI、schema、runtime root、VPS 作业或新 collector；
- 不重采、删除、移动或重新解释已封存数据；
- 不设计入场、退出、止损、仓位、成本模型、回放、回测、paper trading 或 live trading；
- 不将 19 complete parent 当作新的完整独立样本分母，也不使用同一数据集形成未来验证规则。

## 6. Acceptance Invariants

| ID | 不变量 | Fail-Closed 语义 |
| --- | --- | --- |
| INV-S16C-01 | 所有结论必须绑定 Section 2 的 exact path、SHA 与 `w2_0_exploratory_20260926T071500Z`；W2-0 implementation-completion 事实还必须绑定外部 Completion Audit 的 exact path、SHA 与 `Final Verdict: COMPLETE`。在消费 `parent_metrics` 前，production `load_verified_w2_0_bundle(...)` 必须 PASS，且只能使用其返回的 manifest-bound `parent_records`。 | 任一 authority path、SHA、run ID、manifest state、artifact length/schema、20-field authority vector 或 external audit verdict 不匹配，`STOP=stage1_6_conclusion_authority_mismatch`。 |
| INV-S16C-02 | 统计独立单位只能是 `parent_article_id`；19 仅是可描述子集，不替代 27 parent 分母。 | 任何将 29 contract 或 19 complete parent 表述为完整独立结论分母的文案必须拒绝。 |
| INV-S16C-03 | W2-0 只允许 `exploratory_only` 描述结论；`outcome_seen` 不可恢复为盲态。 | 任何 `falsified`、`phenomenon_supported`、Alpha、PnL 或执行表述必须拒绝。 |
| INV-S16C-04 | 不得从本样本派生数值阈值、固定提前退出或任何下架持仓、退出或风险 consumer 规则。 | 任何将 bps 分位数、`24h` 或 `48h` 写作 must/mandatory/hard rule 的变更必须 `STOP=stage1_6_hindsight_rule_promotion`。 |
| INV-S16C-05 | W1 事后描述性数据不构成方向、Carry、成本、因果或执行证据。 | 未绑定独立、点在时、成本和执行证据的升级请求必须 `STOP=stage1_6_w1_claim_upgrade_unproven`。 |
| INV-S16C-06 | 本 Delta 不改变任何 producer、writer、loader、consumer、schema、root 或 runtime lifecycle。 | 任何需要 source/config/runtime 改动的请求必须分流至新的 Design。 |
| INV-S16C-07 | 全部 authority flags 保持 false；本 Design 不授予任何运行时权限。 | 网络、replay、private/authenticated/order API、execution、paper/live trading、deployment、SSH、commit、push 仍全部禁止。 |
| INV-S16C-08 | 任何未来文档维护 Plan 必须接收外部用户批准绑定 `APPROVED_DELTA_DESIGN_PATH` 与 `APPROVED_DELTA_DESIGN_SHA256`，并在读取或改写下游文档前验证本 Delta 的 exact bytes。 | 路径不是本 Delta、SHA 不匹配或缺失批准绑定，`STOP=stage1_6_conclusion_authority_mismatch`。 |

## 7. Producer、Consumer、状态与持久化契约

| 边界 | 现有 owner | 本 Delta 的处理 |
| --- | --- | --- |
| W1/W2 collectors 与 candidate roots | 已有 collector / strict reader lifecycle | No change；不重跑、不迁移、不写回。 |
| W2-0 diagnostic root | W2-0 offline writer / strict bundle loader | No change；sealed root 只读。 |
| W2 collection external audit 与 historical receipt | 独立只读 audit artifact | No change；仅作为 W2-0 authority packet 的既有绑定。 |
| W2-0 external Completion Audit | 独立只读 Completion Audit artifact | 本 Delta 与未来文档维护 preflight 只消费 exact path + SHA + `COMPLETE` verdict；不创建 audit writer、publisher 或 runtime producer。 |
| 下游文档 | 未来经批准的 document-maintenance Plan | 只能消费本 Delta 已冻结的事实；不能产生 runtime artifact 或规则。 |

没有新 schema、持久化 writer、crash window、restart path 或幂等性语义。原因是本 Delta 不执行、不写入运行时状态；唯一未来 writer 是受 Plan 限制的 Markdown 文档维护者。`graphify` 为 N/A，因为不存在 source-module producer/consumer topology 改动。

## 8. L2 研究边界

| L2 项 | 本 Delta 的冻结结论 |
| --- | --- |
| 允许的 claim level | `exploratory_only` 的终局基差分布事实。 |
| independent unit | `parent_article_id`；同一公告下的 contract 为相关诊断行。 |
| anti-hindsight | outcome 已见，故不得从本样本选择阈值、退出时点、子组或反向规则，再宣称确认性。 |
| cost / capacity / execution | `evidence_insufficient`；没有可执行价格、费用、滑点、容量、持仓路径或订单状态证据。该状态仅适用于该明确的可行性/成本主张，具体策略仍按 §4.3 为 `hypothesis_only`。 |
| loss / MAE / tail risk | 只能把尾部分布描述为研究风险信息，不能变为可执行风险边界。 |
| promotion / kill | 当前没有自动 promotion。未满足确认性或经济性证据不等于交易策略 `falsified`；当前只能停止此样本上的规则形成。 |

## 9. 验证与未来 Plan 路由

在任何下游文档维护 Plan 前，Task 0 必须：

1. 接收 `APPROVED_DELTA_DESIGN_PATH` 与 `APPROVED_DELTA_DESIGN_SHA256`，以 `shasum -a 256` 验证本 Delta 的 exact bytes；
2. 用 `shasum -a 256` 验证 Section 2 所列 authority bytes；
3. 验证 W2-0 external Completion Audit 的 exact path/SHA、`Final Verdict: COMPLETE` token，以及其对 exact W2-0 Design、Plan 和 sealed manifest 的绑定；此检查只能确认 implementation-completion 事实，不得升级 Section 3 的研究结论；
4. 调用 production `load_verified_w2_0_bundle(output_root=..., project_root=...)`。只有该 strict loader PASS 后，才可使用其返回的 manifest-bound `parent_records` 重算并核对 Section 3 的 nearest-rank P25/P50/P75 和 `3/19`、`16/19` 计数；不得直接打开 `parent_metrics.jsonl`；
5. 对拟改的两个下游 Markdown 文件做 scoped diff，证明未留下错误 run root、错误 physical-object count、策略 `falsified`、数值 risk veto、固定提前退出、W1 方向性/Carry 提升或未经测量的因果叙述；
6. 验证 `RISK_LIVE_TRADING_ENABLED=False`，并运行 `.agent/tools/anti_shortcut_scan.py` 读取 actual process exit code；
7. 证明仅文档白名单变化，未写入 `data/`、`configs/`、`src/`、`scripts/`、测试或 Git index 外的 runtime artifact。

若任一步失败，未来 Plan 必须停止，不得以人工摘要、默认值、替代 root 或重新解释指标补救。

## 10. Open Questions

| 问题 | 状态 | 路由 |
| --- | --- | --- |
| 是否存在低成本、未用于当前规则形成的独立历史 parent cohort | Non-blocking for this closure; blocking for confirmation | 仅在证据存在后，另起 W2-1 Design。 |
| 是否存在具体、经批准的下架相关持仓、退出或风险 consumer | Non-blocking | 先起独立 consumer Design 与单独的 stage identity；不得关联或创建 Stage 1.6R。 |
| 现有 1.6D/1.6E-B 观察运行是否值得长期保留 | Non-blocking | 作为运营与数据保留决策单独评估，不影响本结论。 |

## 11. Self-Review

- 结论从 sealed W2-0 artifact 与 exact hashes 派生，不以当前 `roadmap` 或项目状态文件为 authority。
- W2-0 implementation-completion 仅以 Section 2 的 external Completion Audit exact path/SHA/`COMPLETE` verdict 证明；它不改变 `outcome_seen/exploratory_only`、分母、缺口或任何研究/交易权限。
- 任何未来消费者先通过 production strict loader 取得 manifest-bound parsed records，再重算统计；不得绕过 sealed-bundle admission 直接读取 artifact 文件。
- 未来文档维护 Plan 还必须以外部用户批准的本 Delta path/SHA 绑定 exact Design bytes；Section 2 的上游 authority 不能替代该批准绑定。
- 保留 41 contract / 27 parent 分母、31/21 window-defined 与 29/19 complete 的缺口语义，没有静默删样本。
- 将终局反例限定为 `outcome_seen/exploratory_only`，没有把它升级为 Alpha、交易或强制风控规则。
- Stage 1.6R 仅指 Security Incident Risk-Veto；下架 consumer 必须使用未来独立 Design 与独立 stage identity。
- 没有新增生产者、消费者、artifact writer、schema、阈值、代码、网络或运行时操作。
- 此文件需独立 closure review 和用户批准；在此之前不得编写文档维护 Plan 或修改下游文档。
