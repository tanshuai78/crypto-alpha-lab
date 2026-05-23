---
description: 安全代码重构流程 (Refactoring)
---

# /refactor - 安全代码重构

使用此工作流对现有代码进行重构、优化或清理，在不改变外部行为的前提下提升质量。

### 执行步骤：

1. **重构范围评估**
   - 调用 `brainstorming` Skill 评估重构的必要性、范围及可能带来的风险。

2. **制定重构计划**
   - 调用 `writing-plans` Skill，列出分阶段重构的步骤。
   - 确保每个阶段都是可逆且可验证的。

3. **测试保障**
   - 对于重构区域，调用 `test-driven-development`（如果现有测试不足）。
   - 确保重构前后的测试表现一致。

4. **执行重构任务**
   - 使用 `executing-plans` 分步实施重构。

5. **代码审查**
   - 调用 `requesting-code-review` 重点检查重构是否意外改变了核心逻辑或导致了性能下降。

6. **验证关闭**
   - 调用 `verification-before-completion` 进行最终的完整性检查。