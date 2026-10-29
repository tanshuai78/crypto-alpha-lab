# `.agent/skills` 技能来源、归属与项目适配说明 (`skills-sources.md`)

本文件记录 `.agent/skills/` 下各技能包的来源分类、版本可核查状态、是否作过仓内定制，以及外部方法在本项目治理体系中的吸收位置。

> **治理优先级约束**：所有外部技能包均服从 `AGENTS.md` 规定的优先级顺序：
> `L0 资金安全 (.agent/rules/L0_Financial_Safety.md)` > `L1 工程流程 (.agent/rules/L1_Engineering_Process.md)` > `L2 Alpha 研究方法论 (.agent/rules/L2_Alpha_Research_Methodology.md)` > `项目工作流 (.agent/workflows/*.md)` > `第三方技能默认行为`。

---

## 一、项目自有技能（Project-Owned Skills，共 3 个）

以下 3 个技能为本项目针对量化研发治理自行编写并维护的技能，可随项目治理计划直接演进：

| 技能目录 | 核心职责 | 权威规则绑定与维护说明 |
|---|---|---|
| `.agent/skills/reviewing-implementation-plans/` | 实施计划静态审查（`Allowed Change Scope` 白名单、垂直切片与依赖、Ponytail 最小化、拓扑碰撞、按后果触发验证） | 绑定 `.agent/rules/L1_Engineering_Process.md` 与 `L2_Alpha_Research_Methodology.md`；仓内直接维护 |
| `.agent/skills/audit-plan-completion/` | 实施完成后的独立只读审计（规范要求 vs 事实证据、全量工作区/暂存区/未跟踪文件核对、`Rule 15/16/17` 按后果核验、权限隔离） | 绑定 `.agent/rules/L1_Engineering_Process.md`；`complete` 绝不自动授予 commit/deploy/runtime/trading 权限 |
| `.agent/skills/closure-revision/` | Design / Plan 审查发现问题后的作者侧受控闭环修订（Blocker Ledger、`Mutable/No-Touch Set`、关联影响锥、诚实标注 `CLOSED / PARTIALLY_CLOSED / OPEN`） | 绑定 `.agent/rules/L1_Engineering_Process.md` §2（闭环修订纪律 Closure Revision Discipline）；直接在仓内维护，禁止外部整包覆盖 |

---

## 二、外部引入技能族（External Skill Families，共 25 个目录）

以下技能目录来自外部开源技能族，安装于 `.agent/skills/`。由于当初引入时未在仓内保留独立的 `.git` 子模块或锁定清单，其精确上游 commit SHA 标为 `unverified`；本次治理**不直接改写这些第三方技能源码**，而是通过项目规则与工作流前置适配层进行约束。

| 技能族 | 包含的目录（`.agent/skills/<name>`） | 仓内可核查的来源线索 | 上游版本 / Commit 状态 | 是否在本次治理中改写源码 | 本项目适配与覆盖位置 |
|---|---|---|---|---|---|
| **Superpowers 开发工作流技能族**（14 个） | `using-superpowers`、`brainstorming`、`writing-plans`、`executing-plans`、`test-driven-development`、`systematic-debugging`、`verification-before-completion`、`requesting-code-review`、`receiving-code-review`、`subagent-driven-development`、`dispatching-parallel-agents`、`using-git-worktrees`、`finishing-a-development-branch`、`writing-skills` | `SKILL.md` 含 `<SUBAGENT-STOP>`、`<EXTREMELY-IMPORTANT>`、流程图及 `superpowers:` 技能调用约定 | `unverified`（仓内未记录精确上游 tag/commit） | **否**（保持原样） | 在 `.agent/rules/L1_Engineering_Process.md` 及 `.agent/workflows/{design-contract,implementation-plan,execute-approved-plan,remediate-completion-audit}.md` 顶部通过“上游技能项目适配规则”覆盖其默认路径（统一写入 `docs/designs/` 与 `docs/plans/`）、禁止自动 `git commit`、默认当前工作区原位执行（不默认新建 worktree）、且必须经独立审查与用户批准后方可执行 |
| **Ponytail 极简主义技能族**（6 个） | `ponytail`、`ponytail-audit`、`ponytail-debt`、`ponytail-gain`、`ponytail-help`、`ponytail-review` | `SKILL.md` 含 7 级极简决策阶梯（Rung 1–7）、`ponytail:` 注释规范及 `ponytail-*` 斜杠命令说明 | `unverified`（仓内未记录精确上游 tag/commit） | **否**（保持原样） | 在 `.agent/rules/ponytail.md` (`D03`) 与 `.agent/rules/L1_Engineering_Process.md` (`Rule 15`) 中完成项目级适配：保留 Rung 1–7 最小化阶梯，但明确 `L0/L1/L2` 安全与契约不变量优先，并修正其绝对化 `no-fixtures` 表述（单模块纯逻辑/故障注入可用最小合成输入，跨边界正向测试必须使用上游 canonical 来源） |
| **Context / Memory 上下文管理技能族**（4 个） | `context-compression`、`context-optimization`、`filesystem-context`、`memory-systems` | `SKILL.md` 与 `references/` 围绕长会话上下文压缩、KV-cache 预算、文件系统上下文卸载与记忆架构展开 | `unverified`（仓内未记录精确上游 tag/commit） | **否**（保持原样） | 仅在用户明确请求优化上下文或整理长会话记录时按需参考；不得覆盖项目审计基线或持久化契约规则 |
| **Graphify 知识图谱技能**（1 个） | `graphify` | `SKILL.md` 定义 `/graphify` 触发器、`graphify-out/` 输出目录（`graph.json`、`GRAPH_REPORT.md`、`wiki/index.md`）与 AST/语义图谱命令 | `unverified`（仓内未记录精确上游 tag/commit） | **否**（保持原样） | 在 `AGENTS.md`（`graphify` 节）、`.agent/rules/L1_Engineering_Process.md` §4.3 与 `.agent/workflows/*.md` 中适配：图谱查询仅作跨模块依赖发现线索（必须回到真实源码与 `rg` 核实）；取消“每次改代码后无条件运行 `graphify update .`”，改为仅在跨模块共享边界实际变化且 Plan 白名单允许时更新 |

---

## 三、方法吸收但未安装技能包的外部参考（Matt Pocock Skills）

针对 `mattpocock/skills` 中的优秀工程实践，本项目采用**方法论内化吸收**方式，**未在 `.agent/skills/` 下安装新的外部技能包**，以避免与既有 Superpowers / 项目工作流产生重复采访或双轨文书冲突：

| 吸收的核心方法 | 为什么不直接安装原版技能包 | 在本项目中的落地位置 |
|---|---|---|
| **选择性澄清（Selective Clarification，源自 `grilling` / `grill-with-docs`）** | 原版 `grilling` 倾向于遍历决策树持续追问并维护独立文档，若在 `brainstorming` 后再跑一遍会造成双倍采访与文书门禁 | 写入 `.agent/rules/L1_Engineering_Process.md` §1.3、`.agent/workflows/design-contract.md` Step 1 与 `docs/production_artifacts/tri_agent_prompt_library_CN.md` (`A-Intake-and-Design`)：源码可查事实不问用户；只问会改变范围、研究语义、权限、风险或验收的未知项；关键术语直接写在 Design 内，不强制新建独立 `GLOSSARY.md` |
| **垂直切片任务拆分（Vertical Slicing，源自 `to-tickets` / `to-spec`）** | 本项目已有正式 `Design` 与 `Implementation Plan`，若额外生成独立 `spec` 或外部 `ticket` 文件会导致多份规格并存与同步漂移 | 写入 `.agent/workflows/implementation-plan.md` Step 3、`.agent/rules/L1_Engineering_Process.md` §2（步骤门禁与范围控制）与 `.agent/skills/reviewing-implementation-plans/SKILL.md`：在 Plan 内部将任务拆分为端到端可独立验证的垂直切片并写明前置依赖，不生成外部 ticket 文件 |
| **公开接口 TDD 与独立推算期望值（源自 `tdd`）** | 本项目已安装 `.agent/skills/test-driven-development/`，只需补齐“期望值独立推算”与“测试公开接口而非死锁私有实现细节”的约束 | 写入 `.agent/rules/L1_Engineering_Process.md` §2 Rule 4、`.agent/workflows/execute-approved-plan.md` Step 2.2 与 `.agent/skills/audit-plan-completion/SKILL.md` §4.1 |
| **按痛点触发的边界整理（源自 `improve-codebase-architecture`）** | 定期强制跑全库重构容易触发越界修改与不必要的代码震荡 | 由 `.agent/rules/L1_Engineering_Process.md` 与 `AGENTS.md` 约束：仅当实际开发痛点（如单次逻辑改动反复散落多处）且经用户明确立项批准时，才作为独立重构任务按工作流执行 |
