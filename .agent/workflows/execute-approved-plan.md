---
description: 已批准实施计划的受控执行流程 (Execute Approved Plan Workflow)
---

# Execute Approved Plan Workflow (受控计划执行流程)

当正式 Implementation Plan 经审查通过、包含完整的 `Allowed Change Scope` 白名单、已绑定精确的 Design/Plan SHA-256、且已获得用户明确授权实施时，使用本 Workflow。

（注：仅影响单模块内部的简要计划任务，在用户确认简要计划后直接遵循 `.agent/rules/L1_Engineering_Process.md` §1.1、§2（TDD 与期望值独立推算、步骤门禁与范围控制）与 §4（完成标准）执行 TDD、范围检查与验证命令，无需建立多角色盲审交接包。）

目标：在受控范围内按计划切片完成实现与验证，严格遵守 `.agent/rules/L1_Engineering_Process.md`（唯一工程流程权威）与 `Allowed Change Scope`，由独立审计闭环验收。

---

## 上游技能项目适配规则 (Project Adaptation Before Invoking Upstream Skills)

在调用 `.agent/skills/executing-plans`、`.agent/skills/test-driven-development`、`.agent/skills/systematic-debugging`、`.agent/skills/verification-before-completion`、`.agent/skills/requesting-code-review`、`.agent/skills/ponytail` 或 `.agent/skills/graphify` 前，必须遵守以下项目级覆盖规则：

1. **默认原位执行，禁止自动提交**：默认在当前工作区原位修改，不新建 `git worktree`（除非用户显式要求调用 `using-git-worktrees`）；未经用户明确指令，**严禁执行 `git add`、`git commit`、`git push`、`git reset`、`git checkout` 或 `git clean`**。
2. **审计职责分离**：执行者只负责完成实现、运行验证并提交客观事实记录；完成度审计必须交由独立会话/Subagent 或用户运行 `.agent/skills/audit-plan-completion`，执行者严禁自审给出 `complete`。
3. **规则单一权威**：工程与测试纪律以 `.agent/rules/L1_Engineering_Process.md` 为准；外部技能中的绝对化口号（如 `no-fixtures` 或强制每步提交）均服从 `L1`。

---

## 执行步骤

### Step 1: 冻结输入与记录 Pre-Execution 基线

1. 核对已批准 Design 与 Plan 的路径及 SHA-256；若与用户批准绑定值不符，立即停止（`STOP`）。
2. 在 `.git/plan-execution/` 下记录当前 `BASE_SHA`（`git rev-parse HEAD`）、`git status --short --untracked-files=all`、工作区与暂存区补丁（`git diff --binary`、`git diff --cached --binary`）以及既有未跟踪文件列表与 SHA-256。
3. 既有脏路径或未跟踪路径在执行期间严禁回退、覆盖或误归因给当前任务。

---

### Step 2: 逐切片实施与验证 (Per-Task Vertical Slice Loop)

按 Plan 的 Task 依赖顺序分批推进，每个 Task 遵循以下准则：

1. **前置契约核实与偏差分流 (`L1 Rule 16` / alias `Old L1 Rule 12`)**：
   - 若 Task 消费上游跨模块契约、Schema 或持久化产物，先核实上游真实定义（model/dataclass、serializer、strict loader）。
   - 严禁在下游用 `.get(k, default)`、伪造 hash 或复制外部 attestation 掩盖上游契约不匹配。
   - 发现计划与工作区现实冲突时，立即按 `.agent/rules/L1_Engineering_Process.md` §3.2 三分法处置：
     - `BLOCKED_IMPLEMENTATION_DEFECT`：执行者对现有 API/设计理解偏差且可在当前白名单与设计内修正 → 记录后原地修正；
     - `BLOCKED_SCOPE_DRIFT`：不改变契约/研究语义/风险边界，但需新增或触碰白名单外文件 → 暂停并走有限范围 Plan 增补（见 `.agent/workflows/remediate-completion-audit.md` 与 `L1` §3.2 的证据绑定检查）；
     - `BLOCKED_SPEC_DRIFT`：需改变数据结构、契约、研究语义、权限或风险边界 → 立即停止并携 Evidence Packet 退回 Design/Plan 流程。

2. **按任务性质执行测试与验证 (`L1` §2 Rule 4 & `L1 Rule 15` / alias `Old L1 Rule 11`)**：
   - **核心逻辑、状态/契约变更与 Bug 修复**：
     - Bug 修复先按 `.agent/skills/systematic-debugging` 用测试或日志确认根因；重构先用测试锁定现有公开行为；
     - 针对公开接口执行 `RED → GREEN → REFACTOR` TDD，不在测试中死锁未来极易变动的私有内部实现细节；
     - 测试期望值必须依据业务规则或数学公式**独立推算**，严禁把被测函数当场的错误或凑巧输出直接抄进 `assert`；
     - **Fixture 分级 (`L1 Rule 15`)**：单模块内部纯逻辑与异常/故障分支允许使用最小合成输入或故障注入；跨模块/跨边界正向验证必须使用上游 canonical 构造器/序列化器或经上游 strict loader 校验的产物。
   - **纯文档、配置说明、静态规则与只读统计脚本**：
     - 执行 Plan 声明的最小可执行验证（如存在性、引用/链接完整性、样本守恒律、哈希核对），不强行制造伪单元测试。

3. **最小化实现 (Ponytail)**：
   - 仅在 `Allowed implementation paths` 内编写满足当前 Task 所需的最少代码（遵循 `.agent/rules/ponytail.md`）。

4. **范围检查与按需扫描 (Scope Check & Conditional Tooling)**：
   - 每个 Task 或批次完成后，检查实际改动范围是否严格落在 `Allowed Change Scope` 内：
     ```bash
     git status --short --untracked-files=all
     git diff --name-only "$BASE_SHA"
     ```
   - **按修改类型触发辅助工具（`.agent/rules/L1_Engineering_Process.md` §4.3 条件化工具）**：
     - **AST 防投机扫描 (`anti_shortcut_scan.py`)**：仅当本次修改包含 Python 源码/脚本/测试（或进入最终执行收尾检查）时运行 `python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"`；纯 Markdown/文档子任务无需每步重复运行。若产生 `WARNING`，在执行记录中写明技术原因，确认未弱化契约校验。
     - **Graphify 图谱 (`graphify`)**：仅在修改共享函数、跨模块契约或公共边界时按需点查；仅当跨模块代码边界实际发生变化且 Plan 的 `Allowed generated/runtime artifacts` 明确允许更新 `graphify-out/` 时，在全部代码修改完成后运行一次 `.venv/bin/python -m graphify update .`。纯文档、规则或单文件内部微调不运行图谱更新。

---

### Step 3: 最终验证与独立审计交接 (Final Verification & Blind-First Handoff)

1. **执行者收尾自检**：
   - 调用 `.agent/skills/verification-before-completion`，完整运行 Plan 要求的最终验证命令集，并检查 `git diff --check "$BASE_SHA"` 与 `git diff --cached --check "$BASE_SHA"`。
   - 对重大代码变更按需调用 `.agent/skills/requesting-code-review`（基于精确 SHA 范围）。
2. **盲审交接给独立 Completion Audit**：
   - 向独立审计会话/Subagent 或用户移交客观事实输入（Approved Design/Plan 路径与 SHA-256、`BASE_SHA`、Pre-execution Baseline 目录、`Allowed Change Scope`、实际运行的命令与退出码、候选文件哈希及已知未决问题）。
   - 不向审计员注入“已完美完成”等主观自评；只有独立运行 `.agent/skills/audit-plan-completion` 给出 `complete` 且用户最终接受后，任务才告完成。
