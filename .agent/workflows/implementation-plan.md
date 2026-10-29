---
description: 实施计划与白名单规范流程 (Implementation Plan Workflow)
---

# Implementation Plan Workflow (实施计划与白名单流程)

当正式 Design 已完成审查、所有影响实现方向或风险边界的问题均已收敛、且已获得用户明确批准时，使用本 Workflow。

（注：仅影响单模块内部且不触及 `.agent/rules/L1_Engineering_Process.md` §1.2 正式触发条件的局部任务，直接按 `L1` §1.1 在对话中给出简要计划并由用户确认即可，无需生成独立的 `docs/plans/` 文档。）

目标：生成范围受控、按垂直切片组织、带有显式 `Allowed Change Scope` 白名单与可验证命令的实施计划（保存至 `docs/plans/YYYY-MM-DD-<topic>-implementation-plan_CN.md`）。

## 上游技能项目适配规则 (Project Adaptation Before Invoking Upstream Skills)

在调用 `.agent/skills/writing-plans`、`.agent/skills/ponytail`、`.agent/skills/graphify` 或 `.agent/skills/reviewing-implementation-plans` 前，必须遵守以下项目级覆盖规则：

1. **输出路径与提交禁令**：Plan 文档固定写入 `docs/plans/YYYY-MM-DD-<topic>-implementation-plan_CN.md`；未经用户明确要求，严禁自动 `git commit`，也严禁在 Plan Task 中编写逐 Task 自动 `git commit` 步骤。
2. **垂直切片内聚（No External Ticket Files）**：吸收垂直切片（Vertical Slicing）拆分方法，但所有任务切片、前置依赖与验证命令直接写在 Plan 文档内，**不额外生成独立的外部 ticket/spec 工单文件**。
3. **批准前禁止执行**：覆盖 `writing-plans` 默认在写完计划后直接启动执行的提示——在 Plan 经独立审查获得 `Approve` 且用户明确批准实施前，严禁开始修改目标代码。

## 执行步骤

1. **Preflight 与影响边界核查**：
   - 读取已批准 Design（记录精确路径与 SHA-256）、`docs/roadmap.md`、`configs/base.py`、`.agent/rules/L1_Engineering_Process.md`、相关源码/测试及 `git status --short --untracked-files=all`。
   - 若任务受 `.agent/rules/L2_Alpha_Research_Methodology.md` 约束，同时读取 `L2`；Plan 严禁自行发明或调整 Design 未批准的 entry/exit/stop-loss、holding horizon、subgroup filter、cost assumption、benchmark 或 promotion/kill 阈值（若发现必须调整，触发 `L1 Rule 16` 的 `BLOCKED_SPEC_DRIFT` 并退回 Design）。
   - 对计划修改的共享函数、Schema 或契约，按需使用 `rg` 与精准 Graphify 查询核实消费方，区分“需要修改 (`Allowed implementation paths`)”与“保持兼容不修改 (`Affected but unchanged`)”。

2. **嵌入 `Allowed Change Scope` 白名单**：
   - Plan 顶部必须包含 `Allowed Change Scope`，明确列出：
     - `Allowed implementation paths`
     - `Allowed verification paths`
     - `Allowed documentation paths`
     - `Allowed generated/runtime artifacts`
     - `Affected but unchanged`（附兼容性验证方式）
     - `Forbidden`（禁止白名单外修改、禁止全库格式化如 `ruff check --fix .`、禁止未授权 destructive cleanup 如 `git clean -fdx`、禁止未经批准修改 `configs/base.py`）
   - 不适用类别写 `none`。

3. **按垂直切片编写 Task 清单 (Vertical Slicing & Consequence-Driven Checks)**：
   - 调用 `.agent/skills/writing-plans`，将实现拆解为**端到端可独立验证的最小垂直切片（Vertical Slices）**，避免按纯横切层拆成无法单独验证的碎片任务。
   - 每个 Task 必须包含：
     - **目标与对应不变量**（如 `INV-01`）
     - **前置依赖 (Dependencies)**（明确依赖哪些前序 Task）
     - **精确文件路径**（必须落在 `Allowed Change Scope` 内）
     - **实现与测试要点**：
       - 核心逻辑、Bug 修复、契约/状态变更：采用公开接口 `RED → GREEN → REFACTOR` TDD，且测试期望值必须依据规则或公式**独立推算**（`L1` §2 Rule 4）；
       - Fixture 规范遵循 `L1 Rule 15`（单模块内部纯逻辑与故障注入可用本地最小合成数据；跨模块/跨边界正向断言必须来自上游 canonical 构造器/序列化器或 strict loader）；
       - 纯文档、配置说明、静态规则与只读统计输出：采用与之匹配的最小可执行验证（如链接/引用核对、守恒律核对、Schema/哈希核对），不强造伪 TDD。
     - **精确验证命令与预期退出码/输出**。
   - **按后果附加检查**：依据 `.agent/rules/L1_Engineering_Process.md` §3.3（`Rule 17` 分层验证）：
     - 仅当产物**直接授予运行权限、控制交易/资金准入、作为不可逆迁移基础，或任务复用既有冻结 Rule 17 profile** 时，才在 Plan 中安排完整的不可变 profile 权威元组、封树/路径规则与独立 Verifier 脚本（`scripts/governance/verify_artifact_schema.py`）；
     - 对于普通可重算或探索性跨阶段研究产物，Plan 必须声明其实际消费者、结构检查与独立语义证据（独立推算手算向量或不共享待测 bug 的消费端校验），明确说明未覆盖极限且不得冒称通过旧 Rule 17 profile，**不要求生成重复实现的独立 Verifier 脚本**；
     - 纯文档、本地临时输出或单模块内部改动不安排此类仪式任务。

4. **Ponytail 任务剪枝**：
   - 检查所有 Task，裁掉未请求的重构、单实现接口、多余包装层或重复验证步骤，确保用最少文件与最小改动满足全部 `INV-*`。

5. **执行基线与完成审计约定**：
   - Plan 必须声明：执行前记录 `BASE_SHA`、脏工作区/未跟踪文件快照；执行后由独立会话/Subagent 运行 `.agent/skills/audit-plan-completion` 审计，执行者不得自审宣告 `complete`。

6. **Plan 独立审查门禁 (Review Gate)**：
   - 调用 `.agent/skills/reviewing-implementation-plans` 进行审查（状态：`Approve` / `Approve with required fixes` / `Block` / `Defer / request missing inputs`）。
   - 只有取得 `Approve` 且获得用户显式批准后，才可进入 `.agent/workflows/execute-approved-plan.md`。
