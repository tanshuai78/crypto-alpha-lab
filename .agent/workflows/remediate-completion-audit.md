---
description: Completion Audit 返修闭环 (Completion Audit Remediation)
---

# Completion Audit Remediation Workflow

仅当独立 `audit-plan-completion` 的 verdict 为 `incomplete` 或 `blocked`，且报告给出了具备证据的 P0/P1 finding 时使用。

目标：逐条验证 finding、以最小范围修补已批准 Plan 的实现缺口、由独立审计重新判定；不得把返修扩展为新需求或无关重构。

## 不适用范围

- 新功能、用户新增需求或可选 P2 改进。
- 没有路径、行为、证据或验证缺口的猜测性意见。
- 已确认原 Design/Plan 规则错误、缺少安全不变量或需要改变契约的情形；这些必须走 delta Design/Plan。

## Step 1: Freeze Audit Inputs

1. 记录原 approved Design、Plan、Plan SHA-256、`BASE_SHA`、pre-execution baseline 和 Completion Audit 报告。
2. 记录当前 `git status --short --untracked-files=all`；不得覆盖、归因或回退 pre-existing dirty/untracked paths。
3. 从审计报告提取每条 P0/P1 finding，建立不落库的 repair ledger：

   ```text
   Finding ID | Severity | Evidence | Disposition | Root cause | Allowed paths | Planned verification | Status
   ```

4. `Planned verification` 记录计划执行的 RED/GREEN/集成验证及预期结果；Step 6 的 `verification-before-completion` 记录实际命令、时间、退出码和结果。
5. Finding 只能标为 `accepted`、`rejected_with_evidence` 或 `deferred_with_user_approval`。未采纳 finding 不得触发代码修改。
6. 延后 P0/P1 finding 时，必须记录用户批准、原因、恢复条件和具体 follow-up Design/Plan 路径。延后不改变原 audit verdict；没有 follow-up 路径时 finding 保持 open，禁止宣称完成。

## Step 2: Verify and Classify Each Accepted Finding

对每条 finding 使用 `receiving-code-review`：以源码、日志、最小复现或原 Plan 不变量验证其是否成立，不能盲从审计结论。

分类规则：

| 类别 | 判定 | 后续动作 |
|---|---|---|
| A: implementation gap | 原 Design/Plan 已明确要求，代码漏接入、漏序列化、漏测试或实现错误 | 进入 Step 3；原 Design/Plan 不改写 |
| B: interpretation gap | 原 Design 目标明确，Plan 或实现细节存在唯一、可证实的解释 | 记录短 repair note，进入 Step 3 |
| C: design/plan defect | 原规则不可满足、缺少安全不变量、改变 contract/schema/persistence 或新增行为 | 停止返修；新建 delta Design 和 delta Plan，重新审核并取得用户批准 |
| D: evidence insufficient | finding 无法复现或证据不足 | 停止该 finding；补证据或以 `rejected_with_evidence` 关闭 |

不得为了处理 A/B 类 finding 重写原 approved Design/Plan。原件保留为历史记录；只有 C 类才创建明确引用原文件的 delta 文档。

C 类不会改写原 Completion Audit verdict：原 verdict 为 `incomplete` 或 `blocked` 就保持原状。delta Design/Plan 获批并执行后，才开始新的 audit cycle。

## Step 3: Form a Minimal Repair Batch

1. 一个 batch 只允许包含同一根因、同一 Allowed Change Scope 和同一组定向验证的 finding。
2. 不同 root cause 必须拆分；不得将 deployment 文档、持久化 schema 和业务逻辑的独立问题混入同一 batch。
3. 写出 repair card（不落库）：

   ```text
   Accepted finding IDs:
   Original BASE_SHA:
   Original Plan path:
   Original Plan SHA-256:
   Completion Audit report path/SHA-256:
   Original Plan task/invariant:
   Confirmed root cause:
   Exact allowed implementation/test/doc paths:
   Forbidden paths:
   Planned RED command and expected failure:
   Planned GREEN command and expected pass:
   Required re-audit boundary:
   ```

4. 若 repair card 的路径超出原 Plan 白名单，停止并按 Step 2 C 类处理；不得静默扩大范围。

## Step 4: Repair One Root Cause

1. 行为、契约、序列化或生产路径问题：使用 `systematic-debugging` 确认根因，并按 `test-driven-development` 先运行 RED。
2. 仅修改 repair card 列出的路径，使用 Ponytail：修共享根因，不在多个 caller 复制补丁；禁止新增未被 finding 要求的抽象、依赖、配置或重构。
3. 文档或部署命令问题：使用最小可执行验证；不得在交互式 SSH 文档中保留会关闭会话的顶层 `exit`。
4. 每条 finding 修复后立即运行 GREEN；失败时停在当前 finding，不进入下一条。

## Step 5: Targeted Topology and Scope Check

仅当修补触及 shared helper、SSOT、contract/schema、runner、CLI 或 transport boundary 时：

```bash
graphify query "<exact_symbol>"
graphify path "<producer>" "<consumer>"
rg -n '"<changed_json_field>"|<exact_symbol>' src tests scripts
```

- Graphify 结果仅用于发现候选影响面，必须以源码验证。
- 不运行全量 `graphify update`、LLM extraction 或 community labeling；返修不应产生无关 `graphify-out/` 写入。
- 每个 batch 后检查：

```bash
git diff --name-only "$BASE_SHA"
git diff --cached --name-only "$BASE_SHA"
git status --short --untracked-files=all
git diff --check "$BASE_SHA"
git diff --cached --check "$BASE_SHA"
```

发现未授权路径、全库 autofix 或所有权不清的变更时，停止并向用户报告；不得自动 `checkout`、`reset`、`clean` 或删除文件。

## Step 6: Verify and Re-Audit

1. 运行原 finding 的复现/失败测试、修补测试、受影响的 integration/deployment/safety checks，以及原 Plan 要求的相关命令。
2. 对所有返修，使用 `verification-before-completion` 记录实际命令、时间、退出码和结果，并与 Step 1 的 planned verification 对照。
3. 由独立 Subagent、独立 Session 或用户重新运行 `audit-plan-completion`；执行返修的 agent 不得为自己的返修给出 `complete` verdict。审计必须重新检查完整 Allowed Change Scope 与原 Plan 不变量；验证命令可聚焦于 accepted finding 和确认的受影响边界，不以无关全量测试替代定向证据。
4. 只有独立审计 verdict 为 `complete`，才可宣称原 Plan 已完成、提交、合并或部署。

## Stop Conditions

立即停止当前 batch，并要求用户决定后续动作：

- finding 需要新行为、contract/schema/persistence 或风险语义变化；
- 复现表明根因与 finding 不同；
- 需要修改原 Plan 白名单之外的文件；
- 当前 batch 引入原本通过的、非 finding 范围模块测试失败；
- 需要启用交易、paper trading、execution engine 或改变 `RISK_LIVE_TRADING_ENABLED = False`。
