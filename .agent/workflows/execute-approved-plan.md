---
description: 已批准实施计划的受控执行流程 (Execute Approved Plan Workflow)
---

# Execute Approved Plan Workflow (受控计划执行流程)

当 Implementation Plan 审查结论为 `Approve`、计划顶部包含完整的 `Allowed Change Scope` 白名单、已记录该 Plan 的精确版本、且已获得用户明确授权时，使用本 Workflow。

目标：在当前工作区按白名单严格限定变动范围，以 TDD（测试驱动）控制编码过程，杜绝越界改动与全库命令误伤，高质量完成计划。

---

## 项目执行原则 (Project Execution Rules)

1. **默认原位执行 (In-Place Execution by Default)**：
   - 本项目个人开发默认在当前工作区原位修改代码。
   - 这是对通用 `executing-plans` worktree 默认要求的项目级覆盖；仅在用户已授权当前工作区执行、且 Step 1 已保存脏工作区基线时适用。
   - **默认不新建 git worktree，不自动逐 Task 进行 git commit**（除非用户在 Plan 或指令中明确要求）。
2. **审计职责分离 (Separation of Execution & Audit)**：
   - 执行 Agent（运动员）负责编写代码、TDD 测试和提交自查证据。
   - 最终完成度审计（裁判员）交由**独立 Subagent / 独立 Session / 用户**运行 `.agent/skills/audit-plan-completion` 进行公正判决，避免既当运动员又当裁判员的确认偏误 (Self-confirmation Bias)。

---

## 执行逻辑方案与顺序 (Execution Flow & Sequence)

```text
[Step 1: 冻结 Plan 与记录基线] ──> [Step 2: 确认执行模式] ──> [Step 3: 分批实施与 Scope 校验]
                                                                            │
[Step 5: 最终验证、代码审查与独立审计] <── [Step 4: 按需拓扑复核与图谱更新] <──┘
```

### Step 1: 冻结 Plan、记录 pre-execution 基线快照与范围校验

1. 记录已批准 Plan 的路径与 SHA-256；该 hash、审核 verdict 和用户授权共同构成执行输入。Plan 在执行前被修改时，必须重新审核。
2. 记录基线 `BASE_SHA` 和可供独立审计读取的脏工作区快照。基线写入 Git metadata，不进入工作区或提交范围：
   ```bash
   BASE_SHA=$(git rev-parse HEAD)
   EXECUTION_RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
   EXECUTION_BASELINE_DIR=$(git rev-parse --git-path "plan-execution/$EXECUTION_RUN_ID")
   mkdir -p "$EXECUTION_BASELINE_DIR"
   git status --short --untracked-files=all > "$EXECUTION_BASELINE_DIR/status.txt"
   git diff --binary > "$EXECUTION_BASELINE_DIR/worktree.patch"
   git diff --cached --binary > "$EXECUTION_BASELINE_DIR/index.patch"
   git ls-files --others --exclude-standard > "$EXECUTION_BASELINE_DIR/untracked-paths.txt"
   while IFS= read -r path; do shasum -a 256 "$path"; done \
     < "$EXECUTION_BASELINE_DIR/untracked-paths.txt" \
     > "$EXECUTION_BASELINE_DIR/untracked-sha256.txt"
   ```
3. 预先存在的脏路径/未跟踪路径不得在后续执行中重置、覆盖或误归因。
4. 确认 Plan 顶部的 `Allowed Change Scope` 明确列出了 implementation、verification、documentation、generated/runtime、affected-but-unchanged 和 forbidden 六类；不适用类别必须写 `none`。

---

### Step 2: 确认执行模式 (Execution Mode)

1. **默认模式（主干）**：
   - 使用当前 Agent 在当前工作区原位执行 Plan。
   - 遵循 `executing-plans` 的批次检查点：默认每批 1 至 3 个彼此连续的 Task；遇到共享契约、持久化 Schema、生产 Runner 或部署命令时立即结束当前批次并汇报验证结果。
   - 若 Plan hash、审核结论、用户授权或白名单任一项不匹配，停止执行并返回 Plan 审查。

2. **高级/可选模式（仅在用户明确要求时）**：
   - 若用户显式要求隔离开发：唤醒 `using-git-worktrees` 创建独立工作区。
   - 若用户显式要求多 Agent 并行：唤醒 `subagent-driven-development` 分发独立任务。

---

### Step 3: 分批逐 Task 实施与 Scope 校验 (Per-Task Execution Cycle)

对当前批次的每一个 Task，执行 Agent 严格遵循以下微循环：

1. **测试先行 (RED)**：
   - 行为代码、Bug、契约/序列化语义或行为重构：先在 `Allowed verification paths` 中编写 failing test。
   - 运行测试，确认因预期的原因失败。
   - 文档、Fixture metadata、生成物和部署命令：执行 Plan 声明的最小可执行验证，不制造无意义 TDD 测试。配置修改必须有 Plan 明确授权和相应行为验证。

2. **最小实现 (GREEN - Ponytail)**：
   - 仅在 `Allowed implementation paths` 中编写满足该 Task 所需的最少代码。
   - 应用 Ponytail 决策阶梯：复用既有 Helper、优先 stdlib、不添加未要求的抽象层/工厂模式。
   - 针对有已知上限的有意简化，添加 `ponytail:` 注释说明升级路径。

3. **重构与精简 (REFACTOR)**：
   - 保持测试通过的同时精简代码。

4. **Task 级 Scope 校验 (硬性拦截)**：
   - 每次 Task 完成后检查当前的实际变动路径：
     ```bash
     git diff --name-only "$BASE_SHA"
     git diff --cached --name-only "$BASE_SHA"
     git status --short --untracked-files=all
     git ls-files --others --exclude-standard
     ```
   - **硬门禁**：所有变动路径必须严格落在 `Allowed Change Scope` 白名单内！
   - 若发现越界、全库格式化或无关文件被触碰（例如误跑 `ruff --fix .`），立即停止；保存当前 diff 和基线比对结果，不得自动 `git checkout`、`git reset` 或删除文件。由用户决定保留、拆分或回退。

5. **批次检查点**：
   - 汇报完成的 Task、精确验证命令和结果、实际变动路径及未解决问题。
   - 不得在前一批的验证或 Scope gate 失败时继续下一批。

---

### Step 4: 拓扑按需查询与单次图谱增量更新 (Disciplined Graphify Usage)

1. **小 Task 执行期间**：
   - 不在每个 Task 完成后都全量更新图谱。
   - 仅当实际修改共享 SSOT、公共 Helper、Contract、Schema、CLI 或 transport boundary 时，使用精准查询：
     ```bash
     .venv/bin/python -m graphify affected "<exact_symbol>"
     .venv/bin/python -m graphify path "<producer>" "<consumer>"
     ```
   - 对 JSON/JSONL 字段、CLI flag、事件类型和路径，再用 `rg` 检查真实消费者。Graphify 只发现候选影响；必须以源码验证，并运行 Plan 声明的兼容性回归。
2. **全部 Task 代码修改与测试通过后**：
   - 代码变更后运行一次 AST-only 图谱增量更新；仅文档变更时跳过：
     ```bash
     .venv/bin/python -m graphify update .
     ```
   - 更新前确认实际会变动的 `graphify-out/` 文件已列入 Plan 的 `Allowed generated/runtime artifacts`，且保持 ignored 或按 Plan 的明确规则处理。

---

### Step 5: 最终验证、代码审查与交接独立 Completion Audit (Separation of Roles)

所有 Task 执行完毕且单项测试通过后：

1. **执行 Agent 自查**：
   - 调用 `verification-before-completion`，运行 Plan 要求的完整 targeted/integration/deployment/safety verification，并运行 `git diff --check "$BASE_SHA"` 与 `git diff --cached --check "$BASE_SHA"`。
   - 对重大代码修改调用 `requesting-code-review`；修复其必须问题后重新运行受影响验证。
   - 输出不落库的《Task Execution Report》：Plan hash、`BASE_SHA`、baseline 目录、每个 Task 的文件/符号、验证命令与结果、实际变动路径和未解决问题。
2. **交接独立 Completion Audit（裁判员视角）**：
   - 由**独立 Subagent / 独立 Session / 用户**运行 [`.agent/skills/audit-plan-completion`](../skills/audit-plan-completion/SKILL.md)。
   - 独立审计视角审查：白名单合规性、生产 Runner 是否真正接入新逻辑、部署 Glob 转义正确性。
   - 只有当 Completion Audit 给出 **`complete`** 结论时，整体开发才正式判定为完成。

---

## 3 个工具在本 Workflow 中的应用细节

### 1. Superpowers 的应用
- **`executing-plans`**：作为原位执行的主干流程，驱动 Agent 按 Task 逐步推进。
- **`test-driven-development`**：驱动行为代码、Bug 和语义重构的 RED-GREEN-REFACTOR 循环。
- **`verification-before-completion` / `requesting-code-review`**：提供最终的 fresh evidence 与重大变更的独立代码审查。
- **`subagent-driven-development` / `using-git-worktrees`**（高级可选）：仅在用户明确要求时唤醒。

### 2. Ponytail 的应用
- **决策阶梯 (Rung 1~7)**：贯穿每个 Task 的编码阶段，强制寻求最小 Diff、最少行数。
- **`ponytail:` 注释机制**：对有 Known Ceiling 的临时简化显式打标。
- **边界**：Ponytail 不删除 trust-boundary validation、Fail-Closed、restart recovery、idempotency、兼容性或 SSOT；范围防护由 Git baseline 和 `Allowed Change Scope` 负责。

### 3. Graphify 的应用
- **精准点查**：仅在修改共享边界时用 `affected` / `path` 发现候选 Caller，再以源码和 `rg` 验证真实影响。
- **单次增量更新**：全部代码修改和验证通过后仅执行一次 `graphify update .`，避免频繁写盘；更新产生的 ignored 生成物必须在 Plan 中声明。
