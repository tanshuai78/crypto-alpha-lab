# Historical Alpha Methodology Audit：历史路线关闭理由审计

**日期**：2026-09-27（核查跨越 2026-09-26 / 27）
**项目**：`crypto-alpha-lab`
**工作区 HEAD**：`bd5d7f3b34b7e42e883e9bbb8410fdf688982793`
**性质**：一次性、只读历史决策审计；本文件是新增审计记录，不是 Design、Implementation Plan 或路线重启授权。
**政策依据**：[L2 Alpha Research Methodology](../../.agent/rules/L2_Alpha_Research_Methodology.md)，特别是 §6、§8、§9、§12、§13；L0 / L1 保持优先。

## 1. 结论先行

本次没有找到可以直接宣布“过去误杀、现在应当重启”的完整证据链。也不能据此说历史方法论没有问题。

发现最值得保留的一项方法学待查事项：**Stage 1.3 的 `volume_spike_1h` 与 `relative_strength_vs_btc` 两个候选，最终仅被成本后中位收益不为正这一关挡住。原始 summary 没有提供成本后均值，原文却把负中位数解释成没有正收益结构。这个推理不成立。**

但上述发现尚未满足 L2 §13 的第二项要求：本次没有完成其原始输入、独立机会、时点可得性与无后视污染的再准入验证。因此不把它们直接标成已具备复议资格，更不声称存在正期望。

| 审计结果 | 本次认定 |
|---|---|
| 已确认仅凭字面上的“胜率低 / 存在亏损”关闭，且原证据再准入也已验证的路线 | **0 条** |
| 与胜率式判定相近、值得复核的中位数门禁问题 | **1 条路线中的 2 个候选**，见 F-01 |
| 已完成全部资格验证的 `reconsider_under_expectancy_framework` | **0 项**；两候选为 `methodology_review_candidate / EVIDENCE_GAP` |
| 成本后结果已有明显负证据、无需因 L2 而重开的分支 | 纯价格截面动量、Liquidation-only 5m、当前版 Vol Breakout、当前版 Route B Liquidation Cascade |
| 不能等同于成本后 EV 非正的关闭/降级 | 数据连续性失败、baseline 匹配失败、事件过少、未完成实现、投入优先级降低 |
| 路线状态变更 / 重新回测 / 参数修改 | **均未执行** |

**总体判断：不应全面重开旧研究。应保留既有停止决定，纠正关闭理由的误记，并把极少数真正受不完整判定口径影响的候选放进待查清单。**

## 2. 审计问题、范围与证据等级

### 2.1 唯一核心问题

> 如果移除“必须高胜率、不能出现亏损、每段结果都必须好看”的要求，原来的关闭理由是否仍然成立？

这不是重新寻找 Alpha，也不是事后筛选赢家。尤其不做以下替换：

- 不把负中位数改写成负均值。
- 不把低胜率改写成负期望，也不把高胜率改写成正期望。
- 不把缺失数据、零交易的占位 `0.0` 当作 EV = 0。
- 不把稀少事件、少数大赢家自动视为没有价值；也不因此豁免尾部生存、样本有效性和容量问题。
- 不把静态成本下的历史样本收益当作已知的未来总体期望。
- 不把现象诊断的反向比例当作交易胜率。

### 2.2 范围

以 roadmap、project state 和历史 review 为索引，追溯 2026-05 至 2026-09 的主要研究决策：Extreme Funding、Trend/Liquidation、Route C1、Factor Lab、External Signal Stage 1.3 / 1.4 / 1.5、旧事件源优先级裁剪，以及当前 W1 / W2-0 的结论边界。

表中条目是决策单元，不是相互独立的策略数量。同一条路线的不同数据源、时间粒度、假设或阶段分别记录，避免把局部分支失败推广到整个主题。

不审计另一个仓库 `my-bitcoin-project` 的完整历史；涉及迁移前 Carry / MR 的记录仅按本仓库证据处理。本次也不继续暂停中的 Stage 1.6 conclusion Delta 审核。

### 2.3 证据优先级

1. 原始研究 review 的明确决策、适用范围与原因。
2. 原始 JSON summary 中实际保存的计数、均值、中位数、blocker。
3. 当前生产判定函数及其 Git 历史，用于交叉核对决策规则；不能替代原始输入真实性证明。
4. roadmap / current-project-state 仅为索引及二手摘要。与前三项冲突时，记录冲突，不替它补造证据。

本次独立解析了关键 summary，并对 Stage 1.3 存量 summary 调用现有纯判定函数复核；**未重新计算原始行情收益、未重新跑历史策略、未执行采集、未验证所有历史 raw bytes 的完整性**。报告里的历史收益数字均是既有产物的记录值，不是本次新回测结果。

### 2.4 处置标签

| 标签 | 含义 |
|---|---|
| `retain_closed` | 保持原分支停止；L2 更新不提供重开理由 |
| `retain_blocked` | 数据、对照、执行等阻塞仍在，不冒充经济性证伪 |
| `retain_observation_only` | 原本就未关闭，不存在“重新打开” |
| `retain_portfolio_deprioritized` | 保留投入优先级裁剪，不冒充实测 EV <= 0 |
| `methodology_review_candidate` | 已发现判定口径问题，但复议资格证据尚未闭合 |
| `reconsider_under_expectancy_framework` | 仅在不完整门禁影响与原证据可再评估性均有依据后使用；也只允许提出复议，不授权执行 |
| `closure_reason_conflict / EVIDENCE_GAP` | 原因矛盾或原证据缺失，保留现状，不推断 Alpha 正负 |

## 3. 重点发现

### F-01：Stage 1.3 将负中位数作为最终收益门禁，未证明均值非正

**证据**：[2026-06-13 Review §4.4–§5](2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md)、[原始 summary](../../reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json)、[生产判定函数](../../src/research/external_signal_shadow/stage1_3_summary.py#L12)。

| 候选 | 事件数 / 天数 / 币种数 | 50 bps 成本后中位数 | 相对随机基准的中位数差 | 实际最终 blocker |
|---|---|---:|---:|---|
| `volume_spike_1h` | 5,690 / 155 / 5 | -48.957880 bps | +4.227561 bps | `median_net_return_not_positive` |
| `relative_strength_vs_btc` | 4,004 / 173 / 4 | -52.286318 bps | +1.012357 bps | `median_net_return_not_positive` |

机械核对结果：

1. 两项都通过当时函数中位于此前的事件数、币种数、天数、单币/单日集中度、Top5 盈利集中度及正 baseline excess 条件。
2. 最后 `median_net_return_after_50bps <= 0` 将它们降为 `candidate_diagnostic_promising`，禁止 live smoke；顶层只接受 `candidate_promising_for_live_smoke`，因此输出 `stop_gate_ticker_direction`。
3. 当前函数重算出的五个候选记录与存量 summary 完全一致。Git 记录显示该文件最近一次提交为 `b122dc0`（2026-06-14），并非为本次审计新改的规则。
4. summary 没有均值、平均盈利/亏损或独立机会层的净期望。正 baseline excess 在这里也是**中位数之差**，不是平均超额收益。

**方法学问题**：成本后中位数不为正，说明分布中心不佳，但不能推出均值不为正。负中位数门禁不是字面上的 `win_rate > 50%`，不能将两者完全等同；它确实同样可能排除低胜率、高赔率分布。

**仍不能忽略的反证/缺口**：两项左尾相对随机基准分别恶化约 106.68 / 58.68 bps；历史来源是 Binance proxy，而目标 collector 是 Gate；事件可能相关。原 review 的 `research_result_valid=True` 不是本次对 raw 输入、机会独立性和 PIT 的重新认证。

**处置**：`methodology_review_candidate / EVIDENCE_GAP`，拟议复议标签为 `reconsider_under_expectancy_framework`，**本次尚不激活该标签**。如用户另行决定继续，先定位原始输入及事件记录，核验可再评估性；然后才考虑在原固定规则、原成本和原分母下补充 expectancy 诊断。不能放宽成本、换窗口或新增子组来“救活”它。

### F-02：Route C1 的“成本后 edge <= 0”关闭叙述缺少所引证据支持

**证据**：[2026-07-05 Review](2026-07-05-route-c1-live-smoke-7d-review.md#L64)、[原始 summary](../../reports/route_c1/route_c1_live_smoke_7d_summary.json)、[生产判定函数](../../scripts/review_route_c1_price_only.py#L788)。

- 原始决策是 `route_c1_baseline_match_failed`。
- 1,536 个事件中 904 个匹配成功，匹配率 `0.5885416667 < 0.70`。
- 三项价格风险强度比为 1.550707、1.692838、3.805591；弱信号 kill switch 为 `false`。
- summary 没有净 PnL 或交易胜率字段；它不是成本后收益回测。
- Review 的“成本后为正”位于未来验收表，而非已完成的测试结果。`run_mode=live_smoke_7d` 也不能替代真实 `sample_days=23`。

但 **HEAD 版本**及工作区 roadmap §5 都把它概括为“净 edge <= 0，因此 terminated”。这不是本次工作区未提交改动才出现的问题。原 review 自身还存在“Ratios below gate thresholds”与数值表不一致、提前称 candidate alpha 的措辞问题。

**不变量**：对照失败不能改写成净期望失败；未来验收项不能改写成已完成证据。

**处置**：`closure_reason_conflict / EVIDENCE_GAP`。保持不推广、不重启；建议以后将索引中的关闭理由改为原始匹配/证据阻塞，或者补上真正支持经济性关闭的另一份原始报告。本次没有发现“仅因胜率关闭”的证据，故不打复议标签。

### F-03：Factor Lab 的负结果支持保持停止，但停止范围被摘要扩大

**证据**：[CMOM Review](2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md)、[CMOM summary](../../reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json)、[Regime/Cash Review](2026-06-10-cross-sectional-factor-lab-stageA2-regime-cash-fallback-review_CN.md)。

- 77 次周频调仓，30 bps 静态成本下：30d momentum 总收益 -84.05%，14d CMOM -75.32%；对应最大回撤约 84.44% / 75.32%。
- 加 cash filter 后两项结果仍为 -61.08% / -53.54%，并存在跑输 BTC、集中度或 mostly-cash 问题。
- 原始 next action 是 `stop_price_only_momentum`。Review §5 明说停止纯价格动量，**不是直接终止整个 Factor Lab**。

**处置**：已失败的纯价格分支 `retain_closed`。用户提出“这种不应因胜率思想而重开”的原则适用，但准确理由是被测组合在指定成本下的亏损、基准劣势和回撤，不是单独一次胜率不足；也不能把组合累计收益直接当成每次机会的 EV 估计。

另记录两项解释限制：10 个百分点改善门槛不是统计显著性检验；30/50/80 bps 是静态成本情景，不是所有真实滑点的已验证上限。纠正这两种说法不构成重开亏损分支的理由。非价格因子是否值得做，是新的研究问题，本审计没有授权。

### F-04：Liquidation-only 5m 有过胜率门禁，但并非因此值得翻案

**证据**：[Review](2026-05-30-liquidation-only-5m-baseline-review.md)、[原始 summary](../../reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_baseline_summary.json)、[决策代码](../../scripts/review_liquidation_only_5m.py#L54)。

代码要求至少两个视界同时满足正中位数、成本后胜率 >= 48%、最差结果 >= -1,000 bps。这个胜率硬门槛不是通用 Alpha 定义，但检查隐藏在 Markdown 表格之外的 JSON **均值**后，得到：

| 视界 | 顺势成本后均值 | 反转成本后均值 |
|---|---:|---:|
| 5m | -18.751362 bps | -13.248638 bps |
| 10m | -15.728606 bps | -16.271394 bps |
| 15m | -15.732351 bps | -16.267649 bps |

六组均为 54 个事件，使用既有 16 bps 成本口径。移除胜率门槛并不能消除这些负经济性记录。

**处置**：`retain_closed`。这是“旧门禁含方法学问题，但不意味着旧路线应重开”的明确案例。结论仅限原版本、原样本、原成本，不是证明未来一切清算策略的总体 EV 都非正。

### F-05：B-Lite 被停止的主要理由是密度/集中度，不能写成已测出全部负 EV

**证据**：[500-trials Review](2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md)、[Stage 1.4C 联合决策](2026-06-18-external-signal-shadow-lab-stage1-4c-joint-decision-review_CN.md)、[判定函数](../../src/research/external_signal_shadow/stage1_4b_lite_summary.py#L64)。

- 三类事件分别 13 / 0 / 8 个，primary blocker 均为 `candidate_event_count_below_min`。
- 第三类成本后中位数为 **+56.07 bps**，不支持“全部结果负收益”的概括。
- 总计 21 个事件、6 天；Top5 正盈利贡献 89.29%。这是稀疏和集中度问题，不是证明每个独立机会的均值 <= 0。
- 500 trials 是随机基准重采样次数，不是 500 个独立事件。
- 1.4C 明确停止 crowding-only 主线，同时保留 liquidation-assisted 方向；不等于 derivatives stress 全线失败。

**处置**：保持原主线停止，不按本次“仅胜率”标准重开。将已证明的事项限定为当时研究投入门槛不通过，不使用“已独立证明没有任何 Alpha”替代它。少数大赢家并非自动无效，但当前证据不足以越过原停止决定。

### F-06：W1 / W2-0 不是已有净期望为负的策略关闭证据

**证据**：[W1 Review](2026-09-20-stage1-6f-candidate-w1-descriptive-diagnostic-review_CN.md)、[W2-0 Design §1](../designs/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-design_CN.md#L12)。

W1 限定原始描述性指标，禁止收益/PnL/Alpha 推论；W2-0 明确“分布不显示稳定向零收敛，不构成策略 falsified”，也禁止成本后期望、入场/退出和执行可行性结论。

因此，“多数基差反向扩大”“方向不稳定”“出现极端亏损形状”既不能证明 delisting 全路线没有 Alpha，也不能证明反向操作有 Alpha。现有工作区 roadmap 的策略证伪和强制退出规则超出了所引 W2-0 Design 的结论权限。

**处置**：仅登记结论层级边界，不恢复本次已暂停的 closure Delta 审核，不重算 W2-0、不改 sealed bundle、不据此启动 W2-1 / 1.6R。是否减少该方向投入属于资源决策，不需要伪装成完整的经济性证伪。

## 4. 历史路线处置台账

下面 22 行是审计索引，不表示 22 个统计独立策略。`保留`表示不因本次审计改变原运行/研究状态。

| ID | 路线 / 决策单元 | 原始理由与出处 | 去掉胜率式要求后 | 本次处置 |
|---|---|---|---|---|
| R01 | Extreme Funding | [05-26 admission revision](2026-05-26-extreme-funding-admission-definition-revision-review.md)：Layer C 为零、强度/净边际门禁、保守 shadow 中位数未过门；原结论 `watchlist_only` | 不会自动变成可执行候选，且原本没彻底关闭 | `retain_observation_only`；记下旧胜率/中位数门禁，不重开 |
| R02 | Vol Breakout 当前版 | [05-28 Review](2026-05-28-trend-vol-breakout-viability-review.md)：仅 498h；moderate 3 笔，胜率 66.7% 但均值 -123.95 bps、最差 -393.03 bps；aggressive 仍负 | 负结果、稀疏与尾部问题仍在 | `retain_closed`，不推广成全主题永久无效 |
| R03 | Liquidation Cascade Route B 当前版 | [05-29 Review](2026-05-29-trend-liquidation-route-b-coinalyze-review.md)引用 05-30 B-only 产物：baseline 零事件；放宽后 1 / 5 笔、均值 -80.90 / -71.71 bps | 仍无正经济性证据；零样本不是零 EV | `retain_closed`；Route A 数据问题与其分开 |
| R04 | Liquidation-only 5m 顺势/反转 | F-04：六个视界/方向组合成本后均值全部负 | 胜率门槛移除也不能抹去负经济性 | `retain_closed` |
| R05 | Coinalyze 1m shock -> 5/10/15m | [05-30 Review](2026-05-30-liquidation-shock-event-study-review.md)：覆盖率 0.1736，0/5 合格，24h lookback 后可用评估小时为 0 | 数据障碍完全保留 | `retain_blocked`，不是 Alpha 证伪 |
| R06 | Binance liquidationSnapshot 替代研究 | [05-31 Review](2026-05-31-binance-liquidation-snapshot-event-study-review.md)：15 symbol-month 仅 8 合格、非完整 tape、Q1 样本偏差 | 无法靠取消方向比例门槛恢复全集覆盖 | `retain_blocked` |
| R07 | Route C1 price-risk proxy | F-02：58.85% baseline match < 70%；不是 PnL 结果 | 匹配障碍仍在 | `closure_reason_conflict / EVIDENCE_GAP`；不重启 |
| R08 | Factor Lab 30d/14d price-only momentum | F-03：成本情景下大幅亏损、基准劣势、回撤 | 经济与生存问题仍在 | `retain_closed`，仅限已测纯价格分支 |
| R09 | Factor Lab regime/cash filters | [A2 Round 1](2026-06-10-cross-sectional-factor-lab-stageA2-regime-cash-fallback-review_CN.md)：减亏但仍 -61.08% / -53.54%，基准/集中度等不过关 | 不是要求每次都赚钱才失败 | `retain_closed`，不新增调参 |
| R10 | Stage 1.3 volume spike / relative strength | F-01：其他已编码门禁通过，仅负中位数阻断；没有均值 | 关闭推理需复核，但原证据准入未重验 | `methodology_review_candidate / EVIDENCE_GAP`，两个候选 |
| R11 | Stage 1.3 其余候选 | [06-13 Review §5](2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md)：volume-confirmed 与 price-only baseline 的中位数 excess 非正；rotation 是 stub/零事件 | 不能把中位数差或 stub 当 EV；也不是仅胜率关闭 | 保留不推进；不得套用 R10 的通过记录 |
| R12 | Stage 1.4B-Lite crowding-only | F-05：13/0/8 事件、6 天总覆盖、集中度，1.4C 停主线 | 样本与证据障碍仍在 | 保留停止；不宣称所有子类净均值非正 |
| R13 | Stage 1.4E deleveraging proxy | [Review](2026-06-20-external-signal-shadow-lab-stage1-4e-deleveraging-proxy-sensitivity-review_CN.md)、[summary](../../reports/external_signal_shadow/stage1_4e_deleveraging_proxy_sensitivity_review_500trials_real_summary.json)：15m 11 事件/9天，左尾 -525.84 vs -282.11 bps；1h 仅1事件且4h中位结果差于 price baseline | 15m 实际失败边为左尾，1h 为基准表现；稀疏另需保留，不只是负中位数 | `retain_closed`（当前代理/过滤器版本） |
| R14 | Stage 1.4A 源可行性 / LQ30 | [真实源审计](2026-06-15-external-signal-shadow-lab-stage1-4a1-real-data-audit-review_CN.md)：清算历史/名义量换算不足；[vendor审计](2026-06-15-external-signal-shadow-lab-stage1-4a2-vendor-liquidation-data-feasibility-review_CN.md)：无样本；[LQ30真实诊断](2026-06-17-external-signal-shadow-lab-stage1-4a-lq30-local-forceorder-snapshot-diagnostic-real-review_CN.md)反而为 promising | 源限制不因统计哲学变化消失；LQ30 未被当时报告整体关闭 | 保留数据阻塞/观察；不能统一归类“负 EV” |
| R15 | Stage 1.5C futures launch cells | [06-23 Review](2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-review_CN.md)：12h long 两 cell promising；1h/4h short 正中位数但左尾不过关；其他 cell 多重 blocker | 左尾风险不等于“只要有亏损就否决”；不是整条路线关闭 | 保留 cell 级结论与执行限制，不重开失败 cell |
| R16 | 旧事件源路线 Spot Pair Addition After-First-Hour | [07-19 assessment 第四层](../strategy_specs/2026-07-19-event_source_master_assessment.md)、[07-29 联合评审](2026-07-29-external-signal-shadow-lab-stage1-6-roadmap-and-codex-proposal-joint-review_CN.md)：竞争/样本/间接性/与1.5重叠；状态页另称低胜率 | 没有定位到冻结净收益实验；不是可确认的纯胜率误杀 | `retain_portfolio_deprioritized / EVIDENCE_GAP` |
| R17 | Complex Social Volume | 同上联合评审、[状态页 §11](../project-status/current-project-state_CN.md#L243)：操纵/噪声/API成本/投入优先级 | 仍属数据与资源判断，非已测净EV | `retain_portfolio_deprioritized` |
| R18 | 旧 Scheduled Token Unlock | 同上：缺 PIT，`unlocked != sold`，冻结 replay | 历史可得性问题保留 | `retain_blocked` |
| R19 | Prediction Market / Governance Quant | 同上：回测/语义解析成本，降级定性阅读 | 取消胜率门槛不降低这些成本 | `retain_portfolio_deprioritized` |
| R20 | 迁移前 Carry / MR | [状态页 §11](../project-status/current-project-state_CN.md#L243)仅记录 Carry期限斜率0、MR API超时不能凑齐60周期 | 属当时市场/运行问题，非胜率门禁；未定位本仓库内一手关闭实验 | 保留原状态；`EVIDENCE_GAP`，不把单次flat证明成永久无carry |
| R21 | Long-Horizon Basis Desk | [状态矩阵](../project-status/current-project-state_CN.md#L88)：`planned_only`；[07-29 Review](2026-07-29-external-signal-shadow-lab-stage1-6-roadmap-and-codex-proposal-joint-review_CN.md)要求 observation-only 标注 | 未找到因胜率被关闭的原决策 | `retain_observation_only`，不是待重启路线 |
| R22 | Stage 1.6F W1 / W2-0 delisting | F-06：已做描述性诊断，无许可作成本后策略结论 | 不能仅凭反例/方向分歧关掉全部Alpha可能，也不能反向升级 | 保留研究边界；暂停的结论Delta仍暂停 |

**编号消歧**：R16–R19 的旧事件源编号属于 2026-07 路线图。旧 `1.6D Token Unlock` 不是后来部署的 `1.6D delisting live source`；旧 `1.6E/1.6F` 也不能与后来 delisting 子阶段按字母直接对应。

## 5. 如何理解“胜率有问题，但不重开”

Extreme Funding 提供了现成反例：[XRP shadow summary](../../reports/extreme_funding/2026-05-25_basis_aware_shadow_XRPUSDT_summary.json)记录胜率约 **47.81%**、中位数 **-1.111263 bps**，而均值为 **+0.472432 bps**。它说明低胜率/负中位数不必然等于负均值，但这点微弱样本均值也不证明可执行 Alpha。

随后 [05-26 sensitivity review](2026-05-26-extreme-funding-parameter-sensitivity-audit-review.md#L110)确有 `win_rate > 55%` 的硬门槛；[admission revision](2026-05-26-extreme-funding-admission-definition-revision-review.md#L129)却同时记录 Layer C 为零、强度/净边际不足，且原结论是保留 watchlist。不能把它包装成“胜率导致已关闭路线被误杀”。

相反，Vol Breakout 的 moderate 样本胜率约 66.7%，均值仍负；Liquidation-only 5m 即便不用胜率门槛，六组均值仍负。这些反例共同说明：

> 本次要纠正的是判定依据，不是把“低胜率不好”替换成“低胜率可能好，所以全部重来”。

“不够稳定”也必须拆开：要求每笔、每天都盈利并不合理；独立样本无法重复、结果完全依赖单一时期、尾部损失突破资本约束，则是仍需保留的证据/生存问题。前者可以被审计质疑，后者不能被一句“接受亏损”取消。

## 6. 建议的最小后续行动

1. **本次审计到此归档，不重开一批路线。** 已有经济负结果或证据/安全阻塞继续保留，不加采集器、不新增长期维护链路。
2. **若只做一个后续核查，优先定位 R10 的历史原始输入。** 这是本次最直接的方法学问题；先判断材料是否完整、可按原规则再评估。若材料缺失或污染不可解决，保留 `EVIDENCE_GAP`，不要为一次翻案重新大规模采集。
3. **记录性修正优先于研究重启。** F-02 的 C1 原因、F-03 的 Factor Lab 范围、F-05 的 B-Lite 密度理由值得在获得文档修改授权后同步到 roadmap；本报告不直接修改这些已有文件。
4. **不借本审计恢复 Stage 1.6 Delta 审核。** W1/W2-0 结论冻结工作仍按用户暂停要求处理。本报告只指出它们不是成本后收益证伪材料。

如果以后 R10 获得复议资格，`reconsider_under_expectancy_framework` 的含义也只能是“值得按期望收益口径核对一次”，而不是 `alpha_candidate`，更不是实施/回测/网络/交易授权。任何新结果必须说明它是历史探索性复核，不能把已经看过的样本洗回盲态确认性样本。

## 7. 核验方法、结果与限制

### 7.1 本次已运行的检查

- `git status --short`、`git rev-parse HEAD`、`git show HEAD:docs/roadmap.md`：区分已提交历史摘要和本次工作区未提交改动。
- `rg`、`sed`、`nl`、`git log -- <path>`：检索关闭理由并读取相关 source / review。
- `.venv/bin/python -B` 的只读断言：用已存 summary 核对 Stage 1.3 现有判定函数的五项输出；两项负中位数候选的前置门禁逐条检查；检查 5m 六个均值均负、C1 匹配率及决策、live flag 为 `False`。**actual exit code = 0**。
- `shasum -a 256`：记录本报告所依赖的关键文件当前 bytes。

这些检查验证的是历史判定记录及口径，不是再次宣告每个历史实验通过 Completion Audit。未运行完整 pytest、anti-shortcut scanner 或策略生产 CLI；本次没有行为代码变更，也不作代码完成审计结论。

### 7.2 可复制的只读核心核对

在项目根目录运行。只读取既有 JSON 与配置，不下载数据、不重算行情收益、不写诊断产物。

```bash
.venv/bin/python -B - <<'PY'
import json
from pathlib import Path
from configs import base
from src.research.external_signal_shadow.stage1_3_summary import decide_stage1_3_summary

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

s = load("reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json")
checked = decide_stage1_3_summary(s)
assert checked["candidate_results"] == s["candidate_results"]
assert checked["next_action"] == s["next_action"] == "stop_gate_ticker_direction"
names = {r["candidate_name"] for r in s["candidate_results"]
         if r["primary_blocker"] == "median_net_return_not_positive"}
assert names == {"volume_spike_1h", "relative_strength_vs_btc"}
print("CHECK_OK=stage1_3_decision_records")

liq = load("reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_baseline_summary.json")
assert set(liq["aggregates"]) == {"1", "2", "3"}
for horizon, records in liq["aggregates"].items():
    assert set(records) == {"continuation", "mean_reversion"}
    for name, row in records.items():
        assert row["event_count"] == 54 and row["mean_cost_adjusted_bps"] < 0
        print(horizon, name, row["mean_cost_adjusted_bps"])
print("CHECK_OK=liquidation_5m_six_negative_recorded_means")

c1 = load("reports/route_c1/route_c1_live_smoke_7d_summary.json")
assert c1["decision"] == "route_c1_baseline_match_failed"
assert c1["baseline_match_rate"] == c1["matched_event_count"] / c1["event_count"]
assert c1["baseline_match_rate"] < c1["route_c1_params"]["ROUTE_C1_BASELINE_MATCH_RATE_MIN"]
assert base.RISK_LIVE_TRADING_ENABLED is False
print("CHECK_OK=c1_matching_blocker_and_live_disabled")
PY
```

### 7.3 审计限制

- 这是按现有索引与历史报告覆盖主要路线的一次审计，不声称发现了所有未记录、口头或外部 agent 的决策。
- 旧 summary 的读取和 hash 固定不等于原行情真实性、幸存者偏差、独立样本和 PIT 验证全部完成。
- R10 原始输入再准入、R20 迁移前一手日志、R16–R19 的净收益实验均未取得充分证据；不能用主观合理性补齐。
- 没有运行服务器检查。历史文档中的 PID、运行状态和 API 可用性不代表当前事实。
- 本次不改变任何已批准 Design、Plan、权限、阈值或 sealed bundle。旧状态不自动升级，旧证据不足也不被改写为已证明负 EV。

## 8. 关键证据快照

以下 SHA 是本次读取时计算，方便以后辨别“同名文件已被重生成”。它们是审计记录，不是新运行权限。

| 文件 | SHA-256 |
|---|---|
| [L2](../../.agent/rules/L2_Alpha_Research_Methodology.md) | `806314e860bbf94d0e4332377d8bf617471f31dfcb51ffab1b646220ba8aed27` |
| [Stage1.3 summary](../../reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json) | `4c27cd2504e9b9660cf4c418fd80b4f00b91655c6adebce3ade36643178d51d5` |
| [Stage1.3 reducer](../../src/research/external_signal_shadow/stage1_3_summary.py) | `6528259eee07e9a82f8bc2a6b3511d5822cf362944f745bd0f296c7977dd3276` |
| [C1 summary](../../reports/route_c1/route_c1_live_smoke_7d_summary.json) | `3314415f69539bc3370a19cc014a2637d250e9ccbd4e03649d2e627c3779aa55` |
| [Liquidation-only 5m summary](../../reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_baseline_summary.json) | `07e24d095aaa96ee69d0a73132ef71801e738056ce0debb16d4234148825191c` |
| [CMOM summary](../../reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json) | `b2429af21c9a7fb42ed919efa0c3542498346dcd2a1833ac1d7a8a2d396ca244` |
| [B-Lite 500-trials summary](../../reports/external_signal_shadow/stage1_4b_lite_funding_oi_price_crowding_replay_500trials_real_summary.json) | `7872b201559239e77ae7e109f4dc2b00a161494487267ee2396f0c41fb07ca55` |
| [Cascade B-only sensitivity](../../reports/trend_regime/2026-05-30_liquidation_cascade_route_b_only_sensitivity.json) | `dfdda30322cb57219fdecdde51cfc19734ceea9a8cc404d09954ba2af519e668` |
| [XRP historical shadow summary](../../reports/extreme_funding/2026-05-25_basis_aware_shadow_XRPUSDT_summary.json) | `1475c76c293fe508ecde8a8e94beeb50da0ff6c0a987e92efd29d556d7b33cbe` |

### 8.1 预存工作区改动保护

本次开始时已有两个改动项，本审计不编辑：

| 文件 | 开始核对时 SHA-256 | 原状态 |
|---|---|---|
| [roadmap](../roadmap.md) | `e12c623878de2304e82c3ebd1aef96ed4f56e226fa0d7dc9748283e96b56dfe6` | tracked modified |
| [暂停中的 conclusion Delta](../designs/2026-09-26-external-signal-shadow-lab-stage1-6f-terminal-basis-conclusion-closure-delta-design_CN.md) | `1037c06b70f5162eb4202067637bb3c7dd03e0807ee28f5ca4d63e1742f5df06` | untracked |

本次唯一新增交付文件为本报告。没有实施、网络请求、SSH、部署、commit、push、paper trading 或 live trading。
