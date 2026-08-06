---
description: 设计契约与架构选型流程 (Design Contract Workflow)
---

# Design Contract Workflow (设计契约流程)

当出现新功能设计、数据/状态契约修改、重大重构或跨模块线上问题修复时，使用本 Workflow。

目标：在动任何代码和 Plan 前，形成一份证据可追溯、Fail-Closed 闭环、且不存在影响实现路径的未决问题的 Markdown 设计文稿（保存至 `docs/designs/YYYY-MM-DD-<topic>-design_CN.md`）。

## 执行步骤

1. **同步事实与需求澄清 (Superpowers)**：
   - 在任何项目检查或提问前，先调用 `.agent/skills/using-superpowers`，再调用 `.agent/skills/brainstorming`。
   - 在 `brainstorming` 的项目探索步骤中读取 `docs/roadmap.md`、`configs/base.py`、相关源码、测试、Fixture、近期提交和当前 `git status --short --untracked-files=all`，再澄清用户真实意图、边界、不变量和成功标准。
   - 本项目覆盖 `brainstorming` 的默认文档位置与提交行为：Design 写入 `docs/designs/`；未经用户明确要求不得自动 commit。
   - 本项目覆盖 `brainstorming` 的默认终态：Design Review 和用户批准前不得直接调用 `writing-plans`。

2. **精准架构拓扑与依赖检索 (Graphify)**：
   - **严禁宽泛泛问**。对设计涉及的核心函数/类使用精准拓扑查询：
     ```bash
     .venv/bin/python -m graphify query "<exact_function_name>"
     .venv/bin/python -m graphify path "<Source_Module>" "<Target_Module>"
     .venv/bin/python -m graphify affected "<exact_function_name>" --depth 2
     ```
   - 先确认 `graphify-out/graph.json` 对应当前源码基线；若图谱过期，本 Workflow 默认将结果降级为 advisory，并使用源码与 `rg` 补足，不自动运行会修改 `graphify-out/` 的更新命令。
   - 如确需更新图谱，必须先取得用户明确授权，并单独记录生成文件；不得自动提交这些文件。
   - Graphify 只负责发现候选依赖。必须回到真实源码行验证；对 JSON key、Schema、JSONL、CLI flag、event type 和文件路径使用 `rg` 补充搜索。

3. **收敛设计范围与 Anti-Overengineering (Ponytail)**：
   - 按以下顺序应用 Ponytail 决策阶梯：
     1. 当前需求是否真的需要该概念或功能？
     2. 库内是否已有可复用的数据结构、Helper、契约或模式？
     3. Python stdlib 或原生平台能力是否已经覆盖？
     4. 是否正在创建无批准边界理由的单实现接口或单产品工厂？
     5. 是否已收敛为满足不变量的最小 Diff 和最少文件？
   - **禁止**在 Design 中添加猜测性框架、未来扩展点、单实现的接口或非请求的工厂模式。
   - 优先级必须保持：L0 safety / data-loss prevention → 已批准不变量 → 兼容性与 SSOT → Ponytail minimality。

4. **撰写 Design Doc 核心要素**：
   设计文稿必须包含以下章节；不适用项写 `N/A` 并说明原因，不得为满足模板而制造抽象：
   - 已确认事实 (Confirmed Facts)
   - 显式假设 (Assumptions)
   - 已作决策及理由 (Decisions)
   - 根因或待解决问题 (Root Cause / Core Issue)
   - 范围与显式非目标 (Scope / Non-Goals)
   - 编号验收不变量 (Acceptance Invariants，例如 `INV-01`)
   - Producer / writer / loader / consumer / reviewer 契约影响矩阵
   - 数据/状态/时间契约 (Data / State / Temporal Contract，包括 status、Schema version、point-in-time 语义)
   - 异常处理与 Fail-Closed 语义 (Failure Semantics / Reducer Sequence)
   - 持久化、Crash 恢复与幂等性 (Persistence / Restart / Crash Window / Idempotency)
   - 兼容性、迁移和旧 artifact/root 处理规则
   - 证据与 Fixture provenance（真实冻结 payload 或明确标记的 synthetic fixture）
   - Safety / authority boundary（包括 live、paper、execution、alpha permission）
   - 验证策略（happy path、failure path、boundary、restart、production wiring）
   - Rollout / rollback（仅运行时或部署行为变化时适用）
   - 未解决问题 (Open Questions)，注明是否阻断、owner 和延后理由

5. **Design Review Gate**：
   - 完成 `brainstorming` 的 placeholder、矛盾、范围和歧义自审。
   - 对跨模块、契约、Schema、运行时或资金安全设计，使用 `.agent/skills/brainstorming/spec-document-reviewer-prompt.md` 做独立文档审查。
   - 审查发现影响实现的缺口时，修订 Design 并重新审查。

6. **硬性门禁 (Hard Gate)**：
   - **若存在任何会改变实现路径、风险、Schema、部署或验证方式的 Open Question，严禁进入 Plan 编写阶段**。
   - 非阻断 Open Question 可以保留，但必须证明其不影响本次实现并明确延后处理方式。
   - Graphify 只用于提供关系线索，最终结论必须回到真实源码、日志或 Fixture。
   - 输出仅为一篇 Design 文档，不修改任何代码；未经用户明确要求不提交。
   - 只有 Design 审查通过且获得用户明确批准，才允许调用 `implementation-plan.md`。
