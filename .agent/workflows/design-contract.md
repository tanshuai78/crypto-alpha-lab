---
description: 设计契约与架构选型流程 (Design Contract Workflow)
---

# Design Contract Workflow (设计契约流程)

当任务触及 `.agent/rules/L1_Engineering_Process.md` §1.2 所列的任一正式触发条件（新建或修改持久化产物/跨模块/跨进程/下游阶段消费契约、修改 `configs/base.py` 风险/策略/执行阈值或权限、修改执行/风控/资金安全逻辑、立项或否决 Alpha 研究假设、修改多模块共享边界且兼容尚不明确、或用户明确要求先审 Design）时，使用本 Workflow。

仅影响单模块内部逻辑且不触及上述触发条件的局部任务，按 `.agent/rules/L1_Engineering_Process.md` §1.1 使用简要计划（Brief Plan）即可，无需进入本 Workflow。

目标：在编写 Implementation Plan 和修改代码前，形成一份事实可追溯、边界清晰、且不存在影响实现路径或风险边界的未决问题的设计文档（保存至 `docs/designs/YYYY-MM-DD-<topic>-design_CN.md`）。

## 上游技能项目适配规则 (Project Adaptation Before Invoking Upstream Skills)

在调用 `.agent/skills/using-superpowers`、`.agent/skills/brainstorming`、`.agent/skills/ponytail` 或 `.agent/skills/graphify` 前，必须遵循以下项目级覆盖规则（优先级：`L0 > L1 > L2 > 本 Workflow > 第三方技能默认行为`）：

1. **输出路径与提交禁令**：Design 文档固定写入 `docs/designs/YYYY-MM-DD-<topic>-design_CN.md`；未经用户明确指令，严禁自动执行 `git add`、`git commit` 或 `git push`。
2. **批准门禁覆盖**：覆盖 `brainstorming` 默认直接转入 `writing-plans` 的终态——在独立 Design Review 通过且用户明确批准前，不得编写或执行 Implementation Plan。
3. **术语与标识符保持**：遵循 `AGENTS.md` 文档政策，正文可使用中文，但所有代码级标识符、配置项、类名、函数名、文件路径和状态枚举保持精确英文原名。

## 执行步骤

1. **同步事实与选择性澄清 (Fact Sync & Selective Clarification)**：
   - 调用 `.agent/skills/using-superpowers` 与 `.agent/skills/brainstorming`，先从工作区读取 `docs/roadmap.md`、`configs/base.py`、`.agent/rules/L1_Engineering_Process.md`、相关源码/测试/Fixture 及 `git status --short --untracked-files=all`。
   - 若任务涉及 alpha discovery、策略假设、事件研究、factor、replay/backtest、策略晋级/证伪、expectancy、PnL 或 economic-edge claim，必须同时读取 `.agent/rules/L2_Alpha_Research_Methodology.md`（L2 仅约束研究方法，不授予任何交易或执行权限）。
   - 执行 `.agent/rules/L1_Engineering_Process.md` §1.3 的**选择性澄清（Selective Clarification）**：
     - 凡能通过源码、配置、测试或现有文档查明的事实，直接查证，不向用户重复提问；
     - 仅当未知项会改变**实现范围、研究语义、权限边界、风险暴露或验收标准**时，向用户提出收敛、具体的问题；
     - 不在澄清完成后重复运行第二轮采访流程，也不强制创建独立的 `GLOSSARY`、`ADR` 或外部 `spec` 文件（关键术语直接在 Design 内定义即可）。

2. **按需拓扑与依赖核查 (Targeted Topology & Source Verification)**：
   - 仅当设计触及跨模块共享边界、公共 Helper、Schema 或持久化产物时，使用精准 Graphify 查询辅助定位候选调用方（例如 `.venv/bin/python -m graphify query "<exact_symbol>"` 或 `path` / `affected`），并用 `rg` 与真实源码行核实。
   - 若 `graphify-out/graph.json` 过期，将查询结果视为候选线索并以 `rg` 和源码为准；未经用户明确授权，不在 Design 阶段自动运行会改写 `graphify-out/` 的更新命令。

3. **范围收敛与最小化 (Ponytail Minimality)**：
   - 遵循 `.agent/rules/ponytail.md` 与 `.agent/skills/ponytail/SKILL.md`：优先复用库内既有结构与 Python 标准库，禁止在 Design 中引入无真实多实现需求的抽象接口、插件注册表、通用工厂或未请求的配置开关。
   - 最小化不得削弱 `L0` 资金安全、`L1` 跨边界不变量或 `L2` 研究诚实性。

4. **撰写 Design 文档（核心结构 + 按后果增补）**：
   - **必选核心部分**（所有正式 Design 均需包含，内容应精炼直接，不为凑字数堆砌模板）：
     1. **目标与背景 (Goal & Problem Statement)**
     2. **已确认事实与显式假设 (Confirmed Facts & Assumptions)**（含关键术语或口径定义）
     3. **范围与非目标 (Scope & Non-Goals)**
     4. **关键决策与理由 (Key Decisions & Rationale)**
     5. **验收标准与不变量 (Acceptance Criteria & Invariants，如 `INV-01`)**
     6. **安全与权限边界 (Safety & Authority Boundary，明确 live/paper/execution/commit 权限)**
     7. **适用批准链与未决问题 (Approval Chain & Open Questions)**
   - **按后果增补部分（Consequence-Driven Additions）**：
     - 依据 `.agent/rules/L1_Engineering_Process.md` §3 的触发条件按需增补，**不适用时省略或简写 `N/A + 一句话理由`，严禁为填满固定 16 节模板而虚构状态机、崩溃窗口或独立验证器**：
       - 跨边界持久化产物：按 `L1 Rule 17` 声明其消费契约、数据语义与验证方式。仅当产物直接授予运行权限、控制交易/资金准入、作为不可逆迁移基础或复用既有 profile 时，才定义完整 profile 权威元组、封树/路径规则与独立 Verifier；普通可重算跨阶段研究输出定义结构校验与独立语义证据，不默认要求独立 Verifier 脚本；人类阅读报告或单次探索输出按 `L1 Rule 17` 声明免除独立 Verifier 与封树证明。
       - 涉及多阶段写入、进程重启恢复或外部 I/O 副作用：补充异常处理、Fail-Closed 与幂等/恢复语义。
       - 涉及跨模块正向契约消费：按 `L1 Rule 15` 说明权威上游构造器/加载器来源。
   - **Alpha Research 专项要求（仅当任务受 `L2` 约束时适用）**：
     - 按 `.agent/rules/L2_Alpha_Research_Methodology.md` §15 逐项定义或标明 `N/A + 理由`（包括独立样本单元、PIT 边界、预先冻结规则、结果分布指标、成本/容量边界、MAE/尾部风险、集中度依赖、晋级/证伪/证据不足语义及延后声明）。描述性阶段保持 `phenomenon_supported` 或 `evidence_insufficient` 即可，不得凭空捏造策略交易阈值。

5. **Design 审查与硬门禁 (Review & Hard Gate)**：
   - 完成自检：确认无未决的阻断性 Open Question，所有引用标识符与源码一致。
   - 按项目三角色流程交由独立审查（或使用 `.agent/skills/brainstorming/spec-document-reviewer-prompt.md`）；若审查需补材料，只补受影响源码或规则原文，不要求提交技能使用证明。
   - 只有独立审查通过且获得用户明确批准后，才允许进入 `.agent/workflows/implementation-plan.md`。
