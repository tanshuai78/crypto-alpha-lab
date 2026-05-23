# crypto-alpha-lab（中文说明）

**个人加密货币 Alpha 研究与小仓位实盘执行平台。**（alpha：可验证的收益假设）

这不是套利系统，也不是“躺赚机器”。它是一个“验证 Alpha + 安全执行底座”的实验平台。（execution base：执行底座）

---

## 项目背景（Project Context：项目背景）

本项目创建于 2026 年 5 月，从 `my-bitcoin-project`（一个 carry/MR 套利系统）转向而来：旧系统在工程上可靠，但被市场结构卡死（期限结构趋平、数据链路脆弱）。（carry/MR：资金费 carry / 均值回归 MR）

关键决策：停止围绕“死掉的 Alpha”继续堆工程，重新以更好的 Alpha 假设为起点。（dead alpha：没有可交易边际）

请先阅读 `docs/roadmap.md` 以获取完整设计理由与策略规范。（roadmap：路线图与决策记录）

---

## 架构（Architecture：目录结构与职责）

```
src/
  exchange/        交易所 client + 核心行情/资金费拉取函数（exchange client：交易所客户端）
  execution/       双腿原子化执行引擎（状态机、回滚、库存保护）（atomic dual-leg execution：双腿原子执行）
  risk/            仓位限制、Kill Switch、资金曲线保护（kill switch：紧急停机）
  data/            最小 schema（MarketSnapshot, SignalCandidate）+ SQLite store（schema：字段定义）
  research/        成本模型、replay 框架（replay：回放/重放）
  strategies/      策略实现（每个策略一个子目录）（strategy：策略）
    extreme_funding/     极端资金费事件扫描器（Extreme Funding Event Scanner：极端费率窗口）
    trend_regime/        趋势/清算 Regime 策略（Trend/Liquidation Regime：趋势/清算状态）
    long_horizon_basis/  长周期资金费基差 Desk（Long-Horizon Funding Basis Desk：多日基差管理）
configs/
  base.py          所有配置常量（`src/` 内无魔法数字）（single source of truth：单一事实源）
docs/
  roadmap.md       决策记录与策略规范（decision log：决策日志）
  strategy_specs/  各策略的详细规格（spec：规格说明）
tests/
  execution/       执行层全套测试（已迁移并验证）（test suite：测试套件）
```

---

## 30 天冲刺计划（30-Day Sprint Plan：节奏安排）

| 天数 | 阶段 | 目标 |
|---|---|---|
| 1–10 | Extreme Funding Scanner | 只做数据观测，不做执行；验证真实机会频率。（observation only：仅观测） |
| 11–20 | Trend / Liquidation Regime | 影子模拟；度量扣费后期望值。（shadow simulation：影子模拟） |
| 21–25 | Long-Horizon Basis Desk（数据） | 构建基差历史库与 Funding Flip 检测器；不交易。（Funding Flip：资金费翻转） |
| 26–30 | Long-Horizon Basis Desk（影子） | 仅当 Funding Persistence > 0.6 才做影子持仓模拟。（persistence：持续性） |

**在 `docs/roadmap.md` 的 8 条“实盘前置检查”全部满足前，禁止实盘交易。**（pre-live checks：实盘前检查）

---

## 快速开始（Quick Start：常用命令）

```bash
# 安装依赖
uv sync --all-extras

# 跑全量测试
make test

# 跑 smoke checks
make smoke

# lint + format
make check
```

---

## 关键设计约束（Key Design Constraints：硬边界）

1. **执行层代码按“原样迁移”对待，不允许随意简化。**（verbatim migration：原样迁移）
2. **`risk.limits.live_trading_enabled` 默认是 `False`。** 必须按策略显式开启。（live trading：实盘开关）
3. **每条策略必须把“入场 + 出场 + 止损”当作一个原子单元。** 不允许只有入场逻辑。（atomic unit：原子单元）
4. **任何真钱前都必须先跑影子模式。** 每个策略至少观测 30 天。（shadow mode：影子模式）
5. **单笔最大仓位：500 USDT；最大并发：2。**（position sizing：仓位上限）

---

## 参考归档（Reference Archive：旧项目归档）

旧项目（冻结）：`/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/`（frozen reference：冻结参考）  
对话记录 ID：`1833b66a-1d4e-455c-aedd-1d6b8cb9b9ea`（conversation log：对话日志）

