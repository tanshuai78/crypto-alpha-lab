# crypto-alpha-lab（中文说明）

**个人加密货币 Alpha 研究与证据验证实验室，具有安全执行底座。**

本项目**不是**套利系统，也**不是**“躺赚机器”。它是一个设计在 5,000 – 50,000 USDT 资金规模假设下的**个人 Alpha 验证实验室**。所有未经验证的候选信号均被严格视为研究假设，而非利润来源。

---

## 当前安全状态 (Current Safety Status)

所有安全控制和风险边界均由 [configs/base.py](configs/base.py) 与 [src/risk/limits.py](src/risk/limits.py) 统一治理：

* `RISK_LIVE_TRADING_ENABLED = False` — 系统启动后严格处于影子观测模式。
* `trade_signal_allowed = False` — 禁止自动生成可交易的 `SignalCandidate` 信号。
* `paper_trading_allowed = False` — 禁止模拟盘下单或虚拟交易撮合。
* `live_trading_allowed = False` — 实盘下单交易已被完全禁用。
* `execution_engine_allowed = False` — 禁止连接实盘执行引擎。
* `alpha_interpretation_allowed = False` — 在没有正式证据审查前，禁止将观测数据解构为已验证的 Alpha。
* `execution_feasibility_claim_allowed = False` — 严禁宣称订单簿深度具备交易执行可行性。

---

## 当前研究聚焦 (Current Research Focus)

当前的核心研究方向是 **External Signal Shadow Lab (Stage 1.5)** — 实时观测交易所催化剂公告事件、收集实时 L2 深度盘口快照、并在严格的证据闸门下离线审计数据质量。

获取详细运行状态、研究规范与文档索引入口，请参阅：
* [项目当前状态 (docs/project-status/current-project-state_CN.md)](docs/project-status/current-project-state_CN.md)
* [研究路线图与决策记录 (docs/roadmap.md)](docs/roadmap.md)
* [当前文档索引入口 (docs/project-status/current-document-index_CN.md)](docs/project-status/current-document-index_CN.md)

---

## 架构职责 (Architecture)

```text
crypto-alpha-lab/
├── configs/
│   └── base.py                        # 配置常量与安全开关的单一事实源 (Single Source of Truth)
├── src/
│   ├── execution/                     # 底层执行层代码（原样迁移，共 355 行）
│   │   └── order_executor.py          # 7 种异常恢复路径（限价委托超时、净边际回滚、库存保护锁等）
│   ├── strategies/                    # 策略基础契约层
│   │   └── base.py                    # SignalCandidate 强类型定义与 BaseStrategy 接口
│   ├── risk/                          # 风险控制模块
│   │   └── limits.py                  # RiskLimits 配置快照与实盘隔离开关
│   └── research/external_signal_shadow/ # 外部催化剂影子观察管线 (Stage 1.5)
│       ├── stage1_5d_live_event_source_* # Stage 1.5D: 公告采集 + BAPI 详情解析 + 202 Retry 调度器
│       ├── stage1_5f_live_depth_*       # Stage 1.5F: L2 盘口观察 + 上线时间闸门 + 水印 v2 + 终端 Ignore Hygiene
│       ├── stage1_5g_live_depth_*       # Stage 1.5G: 离线深度快照质量审查器 (Clean / Quarantine / Invalid)
│       └── stage1_5h_static_execution_* # Stage 1.5H: 静态只读执行代理报告生成器 (Strict Read-Only)
└── scripts/external_signal_shadow/     # 影子运行器与离线评审工具集 (Stage 1.3 - 1.5H)
```

---

## 事实来源优先级 (Source-of-Truth Order)

在评估系统运行状态、阈值参数或技术实现决策时，请严格遵守以下优先级顺序：

1. `configs/base.py` — 配置常量与全局安全控制开关。
2. `docs/project-status/current-project-state_CN.md` — 经核实的本地与服务器运行快照。
3. `docs/current-document-index_CN.md` — 有效文档索引与当前权威规范入口。
4. `src/`、`scripts/`、`tests/` — 经测试覆盖的系统源程序与单元/集成测试套件。
5. 运行归档证据 — 包括 Summary 指标汇总、Watermark 水印和任务状态文件。
6. `docs/roadmap.md` — 研究路线图与决策记录。

---

## 快速开始 (Quick Start)

### 安装与依赖同步

```bash
# 使用 uv 安装和同步所有依赖
uv sync --all-extras
```

### 测试与代码校验

```bash
# 跑静默单元/集成测试
make test

# 跑详细单元/集成测试
make test-verbose

# 跑 ruff 代码静态扫描
make lint

# 跑字节码编译与安全限频 Smoke 测试
make smoke

# 跑一键全量校验 (Lint + Test)
make check
```

---

## 安全不变量 (Safety Invariants)

1. **本金保全第一 (Capital Preservation First)**：本金保全优先级高于任何优化或盈利率目标。
2. **影子验证前置 (Shadow-First)**：任何入场、出场或仓位计算逻辑的变更，必须在影子观察模式下通过至少一个完整策略周期后，方可评估实盘可行性。
3. **免私钥/免凭证 (No Private Credentials)**：公共数据收集与观察管线在设计上仅依赖交易所公开只读接口，不使用 API Key、私钥或钱包签名。
4. **禁止 Output Root 历史改写 (No Output-Root Rewrite)**：运行脚本仅采用追加写入方式输出带时间戳的 JSON/JSONL 文件，严禁覆盖历史运行数据。
5. **保持执行层代码完整 (Execution Layer Integrity)**：`src/execution/order_executor.py` (共 355 行) 已通过生产环境异常考验，严禁随意简化或修改。

---

## 参考归档 (Reference Archive)

* 旧项目路径（已冻结）：`/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/`
* 本次重构决策对话 ID：`1833b66a-1d4e-455c-aedd-1d6b8cb9b9ea`
