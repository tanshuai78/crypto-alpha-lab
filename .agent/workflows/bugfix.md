---
description: 系统化缺陷分析与修复 (Bug Analysis & Fix)
---

# /bugfix - 系统化缺陷修复

使用此工作流处理 Bug 报告、系统崩溃或逻辑异常，避免“猜测式修复”。

### 执行步骤：

1. **系统化调试**
   - 调用 `systematic-debugging` Skill 定位根因。
   - 必须通过日志分析或最小复现脚本确认 Bug。

2. **制定方案**
   - 调用 `writing-plans` Skill 描述修复方案。
   - 评估修复是否会影响到 L0 级别的财务安全策略。

3. **回归测试编写**
   - 调用 `test-driven-development` Skill 编写一个能够触发该 Bug 的测试用例。

4. **执行修复**
   - 使用 `executing-plans` 实施代码修复。

5. **最终验证**
   - 调用 `verification-before-completion` 确认测试通过，且没有引入新的回归缺陷。