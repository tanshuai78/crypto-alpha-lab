# Stage 1.6F Candidate Evidence Admission 与多标的 W1 描述性诊断审查报告

> **审查日期**：2026-09-20  
> **审查对象**：Stage 1.6F 候选证据准入与 W1 描述性诊断产物（Run ID: `candidate_w1_run_20260920_001`）  
> **对应设计**：  
> - 父级设计：[`docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md`](../designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md) (SHA-256: `dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097`)  
> - 修正设计：[`docs/designs/2026-09-20-external-signal-shadow-lab-stage1-6f-candidate-w1-parent-article-cardinality-correction-delta-design_CN.md`](../designs/2026-09-20-external-signal-shadow-lab-stage1-6f-candidate-w1-parent-article-cardinality-correction-delta-design_CN.md) (SHA-256: `02945b5aa9989e48b50381876601ff72f7080878e4e5eb7cc6cdc6eaaf8617f9`)  
> **对应计划**：[`docs/plans/2026-09-18-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-implementation-plan_CN.md`](../plans/2026-09-18-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-implementation-plan_CN.md)  
> **审计状态**：`Verdict: COMPLETE` (所有 Finding 全部 CLOSED；P0-3 权威规范冲突已由批准的 Cardinality Correction Delta Design 闭环，双重 Effective Authority 确立)  
> **安全边界**：`RISK_LIVE_TRADING_ENABLED = False`，所有 13 项权限标志严格为 `False`；纯离线只读分析，严禁交易信号、实盘/模拟盘执行、控制组匹配或因果/Alpha 结论。

---

## 1. 核心审查结论与事实总览 (Executive Summary & Key Facts)

本阶段成功在隔离的只读体系下，将经采集扩充的候选证据包 `expansion_candidate_run_20260917_002` 准入并完成首批 41 标的、19 项指标-视界元组的 W1（Tpub 至 Tpub+12h）原始描述性诊断运算。

```yaml
review_verdict: stage1_6f_candidate_w1_descriptive_diagnostic_passed
design_compliance_status: fully_fulfilled_effective_authority_bound
effective_design_authority:
  parent_design_sha256: dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097
  cardinality_delta_design_sha256: 02945b5aa9989e48b50381876601ff72f7080878e4e5eb7cc6cdc6eaaf8617f9
bundle_run_id: candidate_w1_run_20260920_001
bundle_state_at_write: sealed_valid_at_write
canonical_candidate_run_id: expansion_candidate_run_20260917_002
candidate_manifest_sha256: b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67
output_root: data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/candidate_w1_run_20260920_001

# 核心数量守恒
n_denominator_events: 41
n_unique_parent_article_ids: 27      # 真实严格派生 27 个 distinct parent_article_id（非独立统计样本，符合 Effective Design Authority）
n_metric_records_total: 779         # 严格守恒 41 标的 x 19 元组
n_descriptive_only: 704            # 90.37% 成功提取有效描述性指标
n_diagnostic_incomplete: 75        # 9.63% 因原始数据覆盖/网格缺失如实标记

# 安全开关
live_trading_enabled: false
trade_signal_allowed: false
execution_feasibility_claim_allowed: false
point_in_time_directional_replay_allowed: false
```

### 1.1 事实、假设与决策边界 (Facts, Assumptions & Decisions)

1. **已确认事实 (Facts)**：
   - 41 个候选标的分母全部来自上游经审计的 Stage 1.6A/1.6B 真实公告，对应 27 个 distinct `parent_article_id`（非独立统计样本；符合 Effective Design Authority，见 1.2 节说明）。
   - `Tpub` 时间戳唯一且严格锁定在验证通过的 `parent_audit_outcomes.source_published_at_ms`（即官方选定的可信 BAPI `publishDate`），与保留通知中的数值完全一致。
   - 候选证据包数据为事后收集（`capture_mode: historical_ex_post_candidate`），其 `point_in_time_source_validated = False`。
2. **明确假设 (Assumptions)**：
   - 候选归档仅用于揭示事后物理现象与分布特征，不假定历史实盘具备点在时实时可用性。
   - `is_buyer_maker` 仅代表撮合引擎挂单方角色，未假定其为绝对的主动买/卖气压。
3. **关键决策 (Decisions)**：
   - **分母绝对守恒**：即使标的数据存在缺失（如 14 个 `csv_invalid` 物理对象），该标的也绝对保留在分母中，并产生 `diagnostic_incomplete` 记录，严禁丢弃、填充或平滑。
   - **零因果与零 Alpha 声称**：本诊断仅计算纯原始统计量（如 `bar_close_change_bps`, `delta_oi_value`, `median_notional`），严禁计算超额收益、胜率、信息比率或 PnL。

### 1.2 P0-3 权威规范冲突闭环说明 (Authority Specification Drift Closed Ledger)

- **冲突原委**：
  - 父级 Design [`docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md:332`](../designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md#L332) 原文本规定：  
    `The summary has n_denominator=41, n_unique_parent_article_ids=38...`
  - 但由上游已审计 C 输入（47 个合格标的，对应 38 个父级 ID）经 Matrix 范围交集（42 标的）并排除 REEFUSDT 严格派生出的 41 标的候选分母，其映射的唯一 `parent_article_id` 集合经数学与程序校验严格为 **27 个 distinct parent_article_id**（非独立统计样本，因单篇下架公告常包含多个同批下架合约）。
- **根因分析**：
  - 父级 Design 第 332 行在起草时混淆了上游 C 输入全集的 38 个父文章 ID 与经条件筛选后 41 标的队列的 27 个 distinct `parent_article_id`，属于 Design 阶段的定义笔误（Specification Drift）。
- **闭环方案与处置结论 (CLOSED)**：
  - **已获批准的修正 Design**：用户已核准并冻结最小修正 Delta Design [`docs/designs/2026-09-20-external-signal-shadow-lab-stage1-6f-candidate-w1-parent-article-cardinality-correction-delta-design_CN.md`](../designs/2026-09-20-external-signal-shadow-lab-stage1-6f-candidate-w1-parent-article-cardinality-correction-delta-design_CN.md)（SHA-256: `02945b5aa9989e48b50381876601ff72f7080878e4e5eb7cc6cdc6eaaf8617f9`）。
  - **权威文本窄范围替代**：该 Delta Design 窄范围替代了父级 Design 第 332 行中 `n_unique_parent_article_ids=38` 的语义，明确规定基数严格等于从 admitted denominator rows 派生的 27 个 distinct `parent_article_id`。
  - **Pre-W1 独立推导证据**：Delta Design Section 3 的 stdlib-only 独立推导验证已通过（6 个 pre-W1 冻结文件哈希完全匹配，C==M，27 篇父文章严格为 C receipt 38 篇父文章的真子集）。
  - **履约结论**：本报告正式绑定双重 Effective Design Authority，**P0-3 权威规范冲突正式关闭 (CLOSED)**。设计目标完全达成。

---

## 2. 四维失效审计分类 (Four-Dimensional Failure Audit)

依据 `AGENTS.md` 投研审计规范，必须严格分离并审查以下四类潜在失效模式：

### 2.1 数据失效 (Data Failure)
- **现象审计**：
  - 候选根中包含 14 个 `csv_invalid` 物理归档对象（12 个由于 Binance 早期深度文件格式非 10 档梯阶导致 Schema 漂移，2 个由于 `metrics_5m` 早期文件缺少必须的表头字段）。
  - 在 W1 诊断生成时，对应时段的指标提取全部严格触发了 `candidate_coverage_not_admissible`。
- **隔离状态**：
  - **隔离成功**。未发生任何数据强行截断或格式强制转换（例如 `float("nan")` 逃逸）；失效被如实记录在 `stage1_6f_candidate_w1_metrics.jsonl` 中，保留完整的失败原因链（如 `conflict_duplicates`, `missing_columns`）。

### 2.2 密度与样本失效 (Density Failure)
- **现象审计**：
  - **资金费率 (Funding Observations)**：在 H1（1 小时）视界内，仅 12 个标的观测到结算点（`n_descriptive = 12`），多达 29 个标的标记为 `diagnostic_incomplete`。
  - **根因分析**：加密货币资金费率通常以 4 小时或 8 小时为一个结算周期。在公告发生后的 1 小时窗口内，绝大多数标的尚未经历结算点。
- **投研含义**：
  - 短窗口（H1）内的资金费率观察样本极度稀疏，**严禁使用 H1 视界进行短期资金费率套利或冲击分析**；在 H4（35/41 有效）与 H12（40/41 有效）下样本密度才具备描述意义。

### 2.3 结构与分布特征 (Structure & Distribution Observations)
- **现象审计**：
  - **可见深度代理低值分布 (Visible Depth Proxy Low Values)**：
    - 在 $+1\%$ 卖盘深度代理上，观测到样本最低值：`minimum = 5.9958 USDT`（中位数为 `39,784.28 USDT`）。
    - 需特别指明：本诊断未采集公告发布前（pre-announcement）的深度基准，上述数值仅为 W1 观测窗口内的静态绝对描述值，不构成"盘口塌陷"或"断崖式下跌"等时序变化断言。
  - **价格路径极端偏斜 (Price Path Skew)**：
    - H4 视界内，收盘价变化中位数为 `-34.06 bps`，但极大值达到 `+15,737.93 bps`（+157.38%），极小值为 `-1,373.58 bps`（-13.74%）。
    - H12 视界内，收盘价变化中位数为 `-244.42 bps`（-2.44%），极大值为 `+4,887.89 bps`，极小值为 `-3,809.66 bps`。
- **分布特征分析**：
  - 期货下架候选标的在 H12 视界收盘价变化呈现负向中位数漂移（-244.42 bps），但分布同时伴随极端右偏与厚尾离散特征（H4 极大值达 +15,737.93 bps）。
  - 该分布特征表明原始价格路径具有高度离散性，在未经点在时验证与独立控制组对齐前，严禁仅凭中位数负向漂移推导任何单边策略假设。

### 2.4 执行与成本边界隔离 (Execution & Cost Boundary Enforcement)
- **现象审计**：
  - **基差离散分布 (Basis Dispersion)**：
    - `perp_index_basis`（永续对指数溢价）在 H12 视界中，中位数为 `+10.69 bps`，但极大值达到 `+2,382.73 bps`（+23.83%）。
  - **未平仓量变化 (Open Interest Delta)**：
    - H1 视界未平仓量变化中位数为 `-$85,423.31 USDT`；H4 视界中位数为 `-$262,486.80 USDT`；H12 视界中位数为 `-$324,031.37 USDT`。
- **严格边界声明 (Strict Boundary Disclaimers)**：
  - 依据冻结 Design Section 3.2（第 68 行）与 Section 4.2（第 98 行）强制约束，**本诊断严格禁止推导交易成本、滑点摩擦、流动性冲击、可交易性（tradability）或执行可行性（execution feasibility）结论**。
  - 观测到的基差极端值（+2,382.73 bps）与可见深度代理低值（5.9958 USDT）仅属于事后非 PIT、非独立样本的原始分布统计，不包含撮合引擎执行模拟、实盘订单簿回放或流动性消耗模型，绝不支持任何双腿对冲可行性、基差套利收益或实盘冲击成本推论。

---

## 3. 产物与指标详细数据清单 (Detailed Metrics Breakdown)

以下数据来源于官方密封产物 [`stage1_6f_candidate_w1_summary.json`](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/candidate_w1_run_20260920_001/stage1_6f_candidate_w1_summary.json)：

### 3.1 聚合交易与市场规模 (Agg Trades)
| 视界 | 描述指标 | 有效标的数 (分母=41) | 最小值 (USDT) | 中位数 (USDT) | 最大值 (USDT) |
|---|---|---|---|---|---|
| **H1** | `total_notional` | 41 | 567,046.20 | 4,372,893.42 | 88,422,239.78 |
| **H4** | `total_notional` | 41 | 1,191,365.69 | 6,037,221.23 | 349,657,487.12 |
| **H12** | `total_notional` | 41 | 2,309,426.49 | 9,632,438.65 | 685,368,255.90 |

### 3.2 价格变化路径与基差表现 (Price & Basis)
| 指标名称 | 描述指标 | 视界 | 有效标的数 | 最小值 (bps) | 中位数 (bps) | 最大值 (bps) |
|---|---|---|---|---|---|---|
| **price_path** | `bar_close_change_bps` | **H4** | 41 | -1,373.58 | **-34.06** | **+15,737.93** |
| **price_path** | `bar_close_change_bps` | **H12** | 41 | -3,809.66 | **-244.42** | **+4,887.89** |
| **perp_index_basis** | `median_basis_bps` | **H4** | 41 | -172.37 | +6.14 | +1,849.64 |
| **perp_index_basis** | `median_basis_bps` | **H12** | 41 | -155.66 | +10.69 | **+2,382.73** |
| **mark_index_basis** | `median_mark_basis_bps` | **H4** | 41 | -152.37 | +3.69 | +202.14 |
| **mark_index_basis** | `median_mark_basis_bps` | **H12** | 41 | -150.89 | +8.26 | +38.99 |

### 3.3 未平仓量变化 (Open Interest Value Delta)
| 视界 | 描述指标 | 有效标的数 | 诊断不完整标的数 | 最小值 (USDT) | 中位数 (USDT) | 最大值 (USDT) |
|---|---|---|---|---|---|---|
| **H1** | `delta_oi_value` | 36 | 5 | -1,799,645.35 | **-85,423.31** | +2,865,486.50 |
| **H4** | `delta_oi_value` | 36 | 5 | -2,829,298.12 | **-262,486.80** | +10,887,131.08 |
| **H12** | `delta_oi_value` | 36 | 5 | -2,936,186.31 | **-324,031.37** | +5,449,901.93 |

### 3.4 盘口深度阶梯分布 (Visible Depth Proxy - H1 视界)
| 深度档位 | 描述指标 | 有效标的数 | 最小值 (USDT) | 中位数 (USDT) | 最大值 (USDT) |
|---|---|---|---|---|---|
| **-5% (买五)** | `median_notional` | 33 | 4,316.49 | 227,406.83 | 1,088,468.06 |
| **-1% (买一)** | `median_notional` | 33 | 358.65 | 38,626.90 | 1,040,956.74 |
| **+1% (卖一)** | `median_notional` | 33 | **5.9958** | 39,784.28 | 151,799.38 |
| **+5% (卖五)** | `median_notional` | 33 | **5.9958** | 150,982.60 | 435,175.19 |

---

## 4. 治理合规与安全隔离核查

```text
[CHECK-01] 静态文件 Hash 与不可变性：通过 (候选根目录 1,329 个文件 [664 个 ZIP、664 个 CSV、1 个 Manifest] 及 15 项冻结权威文件哈希与字节长度校验完全通过)
[CHECK-02] 权限与安全开关联动：通过 (13 项权限在 Denominator / Metrics / Summary / Manifest 中递归校验全部为 False)
[CHECK-03] 逆向读取反验 (Load Verification)：通过 (load_candidate_w1_bundle 反读生成的 Bundle 结构、哈希与字段完全通过校验)
[CHECK-04] 代码架构层级隔离：通过 (src/ 不引入 scripts/，无循环引用，无网络客户端或外部 API 调用)
[CHECK-05] 运行期权限：通过 (无部署操作、无 SSH 访问、无 Git commit/push、无实盘下单逻辑)
[CHECK-06] 权威文档履约状态：通过 (P0-3 规范冲突已由批准的 Cardinality Correction Delta Design [SHA: 02945b5aa9989e48b50381876601ff72f7080878e4e5eb7cc6cdc6eaaf8617f9] 正式修正并闭环，双重 Effective Authority 确立)
```

### 4.1 Commit 1 Anti-Shortcut Scanner Disposition Ledger

对共享 candidate evidence validation core 与 collector thin adapter 的 scoped scanner 实际退出码为 `0`，共 4 条 warning，无 error。下列 warning 均为内存聚合或受冻结输入约束的字段选择；不修改 authority、provenance、hash 或权限字段。

| Source line | Rule | Disposition |
|---|---|---|
| `stage1_6f_candidate_evidence_source.py:708` | `RULE-AST-02-DICT-GET-FALLBACK` | `TIMESTAMP_KEYS.get(metric, "open_time")` 仅在 `validate_candidate_root_core(...)` 已将 logical records 与冻结 matrix exact projection 对齐后调用；该调用链中的 metric 属于冻结 family 集合。未知 metric 不构成可接受输入。 |
| `stage1_6f_candidate_evidence_source.py:751` | `RULE-AST-02-DICT-GET-FALLBACK` | `observed_counts.get(ts, 0) + 1` 是窗口时间戳频数初始化与累加；`0` 仅表示此前未观察到该 timestamp。 |
| `stage1_6f_candidate_evidence_source.py:776` | `RULE-AST-02-DICT-GET-FALLBACK` | `counts.get(t, 0) + 1` 是 funding `calc_time` 重复观测计数；不构造或补全 funding 数据。 |
| `stage1_6f_candidate_evidence_source.py:783` | `RULE-AST-02-DICT-GET-FALLBACK` | `trade_ids.get(tid, 0) + 1` 是 agg-trade ID 重复观测计数；不构造或补全交易记录。 |

该处置仅解释 scanner warning，不放宽 candidate root strict validation，也不授权任何网络、execution、paper-trading 或 live-trading 行为。

---

## 5. 明确的后续行动计划 (Confirmed Next Actions)

依据本审查揭示的事实与 Roadmap 既定目标，确认后续研发推进路线：

1. **Design line 332 规范修正流程 (P0 任务：已完成 CLOSED)**：
   - Cardinality Correction Delta Design 已获核准并冻结（SHA: `02945b5aa9989e48b50381876601ff72f7080878e4e5eb7cc6cdc6eaaf8617f9`），Pre-W1 独立推导验证全部通过，Stage 1.6F 权威闭环已达成。
2. **推进 Stage 1.6A 生产端期货下架事件源采集与生效时间设计 (当前最高优先级)**：
   - 当前 1.6F 完成了 41 标的事后原始描述性统计（如 H12 收盘价变化中位数 -244.42 bps、基差极大值 +2,382.73 bps），但此类事后描述性数据严格禁止用于实盘策略、Alpha 评估或因果推论，亦不具备点在时实时可用性；
   - 后续如需探索该类事件的交易价值与风控拦截，必须开启 Stage 1.6A，设计线上期货下架公告采集器，捕获 `available_at_ms`（公告到达时间）与 `settlement_time_ms`（清算生效时间），为系统建立 Risk-Veto 机制。
3. **保持 1.6F-2（因果控制组与 W2 收敛）处于隔离待决状态**：
   - 当前 41 标的分母因事件相关性（对应 27 个 distinct `parent_article_id`，存在同文章批量下架）属于明确的非独立统计样本，且 1 秒级指数和严格点在时控制组目前缺乏足够物理证据；
   - 严禁在缺乏完整点在时微观数据前轻率构建合成控制组或进行因果回归。
4. **状态更新**：
   - 将本审查结论同步更新至 `docs/project-status/current-project-state_CN.md`。
