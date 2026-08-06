---
description: 实施计划与白名单规范流程 (Implementation Plan Workflow)
---

# Implementation Plan Workflow (实施计划与白名单流程)

当 Design 已完成审核、所有 required fixes 已解决、且没有任何影响实现方向的 Open Question 时，使用本 Workflow。

目标：生成无过度设计、且带有硬性文件白名单的 Markdown 实施计划（保存至 `docs/plans/YYYY-MM-DD-<topic>-implementation-plan_CN.md`）。

## 执行步骤

1. **Preflight 与影响清单**：
   - 重新读取已批准 Design、`docs/roadmap.md`、`configs/base.py`、当前源码、测试、Fixture、近期提交及 `git status --short --untracked-files=all`。
   - 将每个 `INV-*` 映射到预期 production entry point、持久化/序列化路径、消费者和验证证据。
   - 对计划修改的共享 SSOT、Helper、契约、Schema、CLI 或 transport boundary 运行精准 Graphify 查询，并以源码和 `rg` 验证。
   - 将影响分为：需要修改、兼容但不修改、仅 advisory、兼容性尚未证明。最后一类在证明兼容或纳入任务前属于 P0。

2. **编写实施计划 (Superpowers)**：
   - 调用 `.agent/skills/writing-plans` 将 Design 拆解为可被 TDD 逐步推进的 Task 清单。
   - 本项目覆盖 `writing-plans` 的默认文档位置与提交行为：Plan 写入 `docs/plans/`；未经用户明确要求不得自动 commit。
   - 未经用户明确要求，Plan 不得生成或执行逐 Task `git commit` 步骤。
   - 在 Review verdict 为 `Approve` 且用户明确批准前，不得提供或启动 `writing-plans` 的执行选项。
   - 每个 Task 必须写明：对应 Design Invariant、精确文件、接口、验证命令、预期结果与不在本 Task 范围内的内容。
   - 行为代码和 bugfix 使用 RED-GREEN TDD；文档、Fixture metadata 和部署命令使用最小可执行验证，不得制造无意义测试。

3. **嵌入 `Allowed Change Scope` 强制白名单**：
   - Plan 顶部必须包含以下 Markdown 白名单规范块：

```markdown
## Allowed Change Scope

Allowed implementation paths:
- src/.../contract.py
- scripts/.../runner.py
- configs/base.py  # 仅当 Design 明确批准阈值/配置修改时

Allowed verification paths:
- tests/.../test_contract.py

Allowed documentation paths:
- docs/reviews/<exact-review-or-checklist>.md  # 仅当 Task 明确要求该交付物时

Allowed generated/runtime artifacts:
- data/<exact-run-root>/**  # generated only; not committed
- graphify-out/<exact-generated-file>  # 仅当项目 hook/update 实际产生该文件时

Affected but unchanged:
- src/.../compatible_consumer.py
  - compatibility evidence: tests/.../test_compatible_consumer.py

Forbidden:
- Any mutation outside the allowed paths
- Unrelated formatter or refactor changes
- Full-repository autofix or formatting (e.g. ruff check --fix .)
- Unscoped destructive cleanup (e.g. git clean -fdx)
- Threshold changes outside configs/base.py or without explicit Design approval
```

   - 所有类别都必须出现；不适用时写 `none`。使用精确路径，只有边界明确的文件族才允许 bounded glob。
   - `Allowed Change Scope` 约束的是后续执行，不自动授权修改已批准的 Design 或 Plan；若实现迫使 Design 改变，必须停止并重新走 Design Review。
   - 全库非修改型检查可以作为 verification，但不得据此修复白名单外问题。

4. **任务剪枝 (Ponytail)**：
   - 审查 Plan 中的 Task：是否有非必要的抽象、胶水层或试图重构无关代码的 Task？
   - 优先复用现有 Helper、stdlib 和原生能力；裁掉 speculative registry、单产品 factory、无批准边界理由的单实现 interface。
   - 不得以最小化为由删除 trust-boundary validation、Fail-Closed、restart recovery、idempotency、兼容性或 SSOT。

5. **计划严格审查 (Review Gate)**：
   - 调用 `.agent/skills/reviewing-implementation-plans` 进行静态风险审查：
     - **白名单校验**：是否包含显式的 `Allowed Change Scope`？
     - **Ponytail 校验**：是否遵循 YAGNI 阶梯？
     - **Graphify 碰撞**：使用 `graphify query/path/affected` 找出候选消费者，以源码和 `rg` 验证后分类：需要修改者进入 `Allowed implementation paths`；兼容且无需修改者进入 `Affected but unchanged` 并附回归证据。
   - Review verdict 状态机：
     - `Approve`：可进入用户批准门禁。
     - `Approve with required fixes`：修订后重新审核，禁止执行。
     - `Block`：禁止执行。
     - `Defer / request missing inputs`：补齐输入后重新审核。

6. **执行基线与完成审计契约**：
   - Plan 必须要求执行开始前记录 `BASE_SHA` 和 `git status --short --untracked-files=all`。
   - 对执行可能重叠的既有 dirty/untracked 路径，要求保存 patch 或 SHA-256 provenance；不得自动 revert、overwrite 或归因给本次任务。
   - Plan 必须规定：执行后、宣称完成或提交/部署前调用 `.agent/skills/audit-plan-completion`，并取得 `complete` verdict。

7. **硬性门禁 (Hard Gate)**：
   - 每个 Design Invariant 必须 100% 映射到至少一个 Task。
   - 禁止在 Plan 中包含 `ruff check --fix .` 等全库未限定目录的自动修复指令。
   - 只有计划审查最终 verdict 为 `Approve` 且获得用户显式批准，才允许使用 `subagent-driven-development` 或 `executing-plans` 开始编码。
   - 输出仅为一篇 Plan 文档；未经用户明确要求不提交。
