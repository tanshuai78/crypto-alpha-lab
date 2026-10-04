# crypto-alpha-lab（中文说明）

**个人加密货币 Alpha 研究与证据验证实验室，具有安全执行底座。**

本项目**不是**套利系统，也**不是**“躺赚机器”。它是一个设计在 5,000 – 50,000 USDT 资金规模假设下的**个人 Alpha 验证实验室**。所有未经验证的候选信号均被严格视为研究假设，而非利润来源。

---

## 1. 当前安全状态与硬性不变量 (L0 Financial Safety)

所有安全控制与风险边界均由 [configs/base.py](configs/base.py)（全系统单一事实源）与 [src/risk/limits.py](src/risk/limits.py) 统一治理：

* **实盘交易已被完全禁用**：`RISK_LIVE_TRADING_ENABLED = False` — 系统启动后严格处于只读影子观测与离线诊断模式。
* **权限否定安全向量**：所有观测与诊断模块均强制执行 Fail-Closed 权限否定向量：
  * `trade_signal_allowed = False` — 禁止自动生成可交易的 `SignalCandidate` 或 `TradeIntent` 信号。
  * `paper_trading_allowed = False` — 禁止模拟盘下单或虚拟撮合。
  * `live_trading_allowed = False` — 实盘下单交易已被完全禁用。
  * `execution_engine_allowed = False` — 禁止连接交易所执行引擎。
  * `alpha_interpretation_allowed = False` — 在没有正式研究关卡支持前，严禁将诊断数据解构为已验证的 Alpha。
  * `execution_feasibility_claim_allowed = False` — 严禁宣称订单簿深度具备交易执行可行性。
* **执行层代码完整性**：底层 355 行原子双腿执行引擎（[src/execution/order_executor.py](src/execution/order_executor.py)）原样冻结迁移，严禁随意简化。其处理 7 种不同的远程与部分成交异常恢复路径（Maker 挂单超时、净边际校验、对冲异常、碎股回滚、部分成交终止、重复意图拦截、强制去杠杆锁定）。

---

## 2. 研究方法论体系 (L2 Alpha Research Methodology)

全项目 Alpha 策略研究严格遵循 [.agent/rules/L2_Alpha_Research_Methodology.md](.agent/rules/L2_Alpha_Research_Methodology.md)：

1. **跨独立机会的真实经济期望**：Alpha 并非由单笔确定性或单一胜率定义。核心衡量标准是预注册规则在扣除全部真实摩擦成本（手续费、滑点、资金费率、借贷成本）后，在**独立机会**上表现出正数学期望，且最大回撤、MAE/MFE、尾部亏损与执行摩擦在 L0 资金安全下完全可承受。
2. **严禁主张越级推论 (Separation of Claims)**：
   $$\text{phenomenon\_supported} \neq \text{alpha\_candidate} \neq \text{executable\_edge} \neq \text{live\_safe}$$
   观测到市场现象并不等同于存在 Alpha 候选，更不等同于可执行或可实盘。
3. **独立机会为统计单元**：统计单位必须是独立的父催化事件（如单篇父公告文章），严禁将同一公告衍生的多个子合约或重叠滑动窗口当作独立样本计算。
4. **输出完整分布而非仅报告胜率**：强制报告胜率、盈亏比、均值、中位数、P10/P25/P50/P75/P90、MAE、MFE 与最大单笔回撤。
5. **严格的事前预注册与抗后视偏差**：所有入场/观测锚点、评估窗口、成本假设、失效与淘汰准则必须在观察结果前冻结，严禁事后参数调优。

---

## 3. 当前研究路线与最新里程碑 (截至 2026 年 10 月)

### 3.1 外部信号影子实验室 (Stage 1.5 — 上线公告与 L2 微观结构诊断)
* **Stage 1.5D 实时公告采集器**：服务器进程 PID 88580 持续运行，Binance 公共目录 + BAPI 详情解析 + 202 重试调度器消除解析饥饿。
* **Stage 1.5F 实时盘口观察器**：服务器进程 PID 88770 持续运行，L2 深度快照采集 + 上线时间闸门 + 水印 Schema V2 + 终端 Ignore 历史锚点清洗。
* **Stage 1.5G N=3 产品机制分层事件族准入**：
  * 准入 3 篇独立公告、3 个父事件与 9 个正式子标的，按 3 种产品机制严格分层隔离：`crypto_standard_perpetual` (`CTUSDT`)、`pre_ipo_equity_perpetual` (`MOONSHOTUSDT`) 与 `tradfi_equity_or_etf_perpetual_batch` (7 个标的：`CRML`、`BWET`、`ACN`、`MP`、`SECZ`、`UNH`、`NKE`)。
  * 达成 Gate 3 事件族样本数量门槛；下游消费强制 Fail-Closed 硬阻断 (`STOP=stage1_5g_n3_future_consumer_not_authorized`)。
* **Stage 1.5H N=3 产品机制分层流动性摩擦诊断**：
  * 对 9 个子标的与 3 个父事件完成双边 P95 滑点摩擦与点差评估。
  * **实证核心结论**：微观结构流动性摩擦在不同产品机制间呈现**极端分化**：
    * `crypto_standard_perpetual`：边际 P95 滑点总和 17.99 bps（P50 点差 5.66 bps，可用度 99.58%）。
    * `pre_ipo_equity_perpetual`：边际 P95 滑点总和 31.58 bps（P50 点差 5.85 bps，深度比 22.40x）。
    * `tradfi_equity_or_etf_perpetual_batch`：边际 P95 滑点总和中位数 80.02 bps（P50 点差 29.71 bps，最高达 87.43 bps）。
  * 严禁跨机制池化，严禁使用单一统一定价地板；研究结论严格保持 `evidence_insufficient`。

### 3.2 期货下架公告研究 (Stage 1.6 — Futures Delisting 催化剂路线)
* **Stage 1.6A–1.6C**：下架公告源语法契约、突发队列故障恢复与密封导出适配器已完成。
* **Stage 1.6D 实盘 VPS 观测部署**：已完成 Runbook 治理规范（[docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md](docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md)），等待预检记录与用户显式部署授权。
* **Stage 1.6E–1.6F**：秒级 Kline/Mark/Index 数据能力与匹配控制完成；Stage 1.6F-W2-0 探索性终端基差诊断完成（结论收敛封板）。

### 3.3 历史信号准入前置校验 (Stage 1.3 R10)
* 离线结构化 Bar 校验 + Git 锚定 Manifest + 点对点因果解析门禁已通过 69 项测试验证，下游消费强制 Fail-Closed 阻断 (`STOP=stage1_3_r10_readmission_future_consumer_binding_missing`)。

### 3.4 历史基线与终止研究路线
* **Carry / MR 期限结构平坦**：OKX 现货超时且利差平坦 ($\le 0.000$)，逻辑冻结作为历史基线。
* **Route C1 纯价格代理**：7 天实盘影子测试因对照匹配率 $58.85\% < 70\%$ 终止推广。
* **Stage 1.4B-Lite 衍生品拥挤度**：因样本高度集中（6 天 21 事件中前 5 个正向事件贡献了 $89.29\%$ 利润）而停止。
* **Cross-Sectional Factor Lab (Stage A2 CMOM)**：测试的 30d/14d 纯价格动量在 30 bps 成本情景下表现为净亏损，价格动量规格保持关闭。

---

## 4. 系统架构与代码全景 (Architecture)

```text
crypto-alpha-lab/
├── configs/
│   ├── base.py                        # 全局配置常量、阈值与安全硬开关的单一事实源
│   └── external_signal_shadow_price_map.json
├── src/
│   ├── execution/                     # 底层执行引擎（原样迁移冻结，355 行）
│   │   └── order_executor.py          # 7 种异常恢复路径（Maker 超时、对冲异常、碎股回滚等）
│   ├── strategies/                    # 策略基础契约与强类型接口
│   │   └── base.py                    # SignalCandidate 数据类与 BaseStrategy 接口
│   ├── risk/                          # 风险控制模块与持仓边界
│   │   └── limits.py                  # RiskLimits 快照与实盘隔离保护
│   └── research/                      # 量化研究与影子观察管线
│       ├── cost_model.py              # 手续费、滑点与资金借贷成本模型
│       └── external_signal_shadow/    # 催化剂影子观察与诊断模块 (Stage 1.3 - 1.6)
│           ├── stage1_3_r10_readmission.py # 1.3 R10: 离线只读准入前置门禁
│           ├── stage1_5d_live_event_source_* # 1.5D: 实时公告采集与 BAPI 详情调度
│           ├── stage1_5f_live_depth_*       # 1.5F: L2 盘口观察器、水印 v2、终端 Ignore
│           ├── stage1_5g_n3_regime_stratified_admission.py # 1.5G N=3: 产品机制分层准入门禁
│           ├── stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py # 1.5H N=3: 机制分层摩擦诊断
│           ├── stage1_6a_futures_delisting_* # 1.6A: 下架公告语法与密封适配器
│           ├── stage1_6b_canonical_source_* # 1.6B: 下架事件突发队列与检查点
│           ├── stage1_6e_*                  # 1.6E: 语义观察器与数据能力审计
│           └── stage1_6f_*                  # 1.6F: 匹配对照与终端基差诊断
├── scripts/external_signal_shadow/     # 运行脚本与 CLI 审查工具集 (Stage 1.3 - 1.6)
├── tests/                             # 自动化测试套件（单元、集成、变异注入与 AST 防护）
├── docs/                              # 项目文档与决策日志
│   ├── designs/                       # 正式设计规范文档 (Design)
│   ├── plans/                         # 实施计划文档 (Implementation Plan)
│   ├── reviews/                       # 正式审查与审计报告 (Review / Audit)
│   ├── project-status/                # 项目状态基线与文档索引
│   │   ├── current-project-state_CN.md
│   │   └── current-document-index_CN.md
│   ├── ops/                           # 运维手册与上线 Checklist
│   └── roadmap.md                     # 研究路线图与决策全景日志
└── Makefile                           # 标准工程构建目标
```

---

## 5. 事实来源优先级 (Source-of-Truth Hierarchy)

在评估系统状态、配置阈值或架构实现时，必须严格遵守以下优先级顺序：

1. `configs/base.py` — 配置常量与全局安全控制开关（`src/` 内严禁出现魔法数字）。
2. `docs/project-status/current-project-state_CN.md` — 经严格核实的工作区与服务器真实快照。
3. `docs/project-status/current-document-index_CN.md` — 统一事实文档索引与当前权威规范入口。
4. `src/`、`scripts/`、`tests/` — 经测试覆盖的生产代码、生产调用链路与自动化测试套件。
5. 运行归档回执 (`data/external_signal_shadow/...`) — 生产密封发布的 Manifest、Summary 与诊断收敛回执。
6. `docs/roadmap.md` — 研究路线图与重大决策全景日志。

---

## 6. 快速开始 (Quick Start)

### 安装与依赖同步

```bash
# 使用 uv 安装和同步所有依赖
uv sync --all-extras
```

### 自动化验证与质量检查

```bash
# 运行静默测试
make test

# 运行详细测试
make test-verbose

# 运行 ruff 代码静态检查
make lint

# 运行代码格式化
make fmt

# 运行字节码编译与资金安全开关 Smoke 检查
make smoke

# 运行全量质检 (Lint + Test)
make check

# 运行 AST 静态代码反绕过扫描器
python3 .agent/tools/anti_shortcut_scan.py
```

---

## 7. AI 代理工作规范 (Guidelines for AI Agents)

所有在本仓库中工作的 AI 代理必须严格遵守 `AGENTS.md` 中的持久规则：

1. **优先级序列**：L0 资金安全 > L1 工程过程纪律 > L2 Alpha 研究方法论 > 项目业务流程。
2. **强制计划确认**：在修改 `src/` 下任何代码前，必须编写实现计划（Implementation Plan）并获得用户显式确认。
3. **禁止虚构文件**：严禁引用 `src/main.py` 或 `src/config.py` — 本项目中不存在这两个文件。
4. **测试驱动开发 (TDD)**：核心逻辑改动必须先写失败测试，再实现逻辑代码，最后验证通过。
5. **反过度设计**：实现满足验证目标的最小、最稳定方案，禁止为单次需求添加多余抽象或预留拓展。
6. **文档规范**：所有面向人类审查的说明文档可采用中文撰写，但代码级标识符（变量名、类名、配置项、错误码、文件路径）必须保留精确的英文原名。

---

## 8. 参考归档 (Reference Archive)

* 旧项目路径（已冻结）：`/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/`（Tag: `frozen/2026-05-23-before-migration`）
* 初始重构决策对话 ID：`1833b66a-1d4e-455c-aedd-1d6b8cb9b9ea`
