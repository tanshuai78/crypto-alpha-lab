---
description: Completion Audit 返修与执行偏差分流闭环 (Completion Audit Remediation Workflow)
---

# Completion Audit Remediation Workflow (审计返修与偏差分流流程)

当独立 `.agent/skills/audit-plan-completion` 的结论为 `incomplete` 或 `blocked`（含具备客观证据的 P0/P1 finding），或执行期间触发范围/实现偏差需要受控修补时，使用本 Workflow。

目标：依据 `.agent/rules/L1_Engineering_Process.md`（特别是 `Rule 16` / alias `Old L1 Rule 12`）与已批准 Design/Plan 边界，先核实根因与影响类型，再按三种路径精准分流修补，并交由独立审计复核。

---

## Step 1: 冻结审计输入与核实 Finding

1. 记录原已批准 Design、Plan（含 SHA-256）、`BASE_SHA`、Pre-execution Baseline 目录及独立 Completion Audit 报告。
2. 检查当前 `git status --short --untracked-files=all`，保护既有脏文件与未跟踪基线不被覆盖或误删。
3. 使用 `.agent/skills/receiving-code-review` 逐条核实 P0/P1 finding：用真实源码、命令输出或最小复现确认问题是否成立，不作表演性附和，也不盲目修改无关代码。

---

## Step 2: 三路径分流规则 (Three-Way Remediation & Drift Routing)

核实后的每个问题必须严格归入以下三类之一处理（与 `.agent/rules/L1_Engineering_Process.md` §3.2 一致）：

| 分流类别 | 判定条件 | 必需动作与门禁 |
|---|---|---|
| **路径 A：白名单内实现或测试缺口 (`BLOCKED_IMPLEMENTATION_DEFECT` / Implementation Gap)** | 原 Design 与 Plan 语义清晰且无需改写；问题仅在于 `Allowed Change Scope` 白名单内漏写逻辑、漏接调用、测试断言错误或文档笔误 | 1. 不重写原 Design/Plan；<br>2. 在原白名单路径内按最小范围修补（行为问题先运行 RED 测试复现，再修到 GREEN）；<br>3. 重新运行受影响验证并交独立审计复核。 |
| **路径 B：有限范围 Plan 增补 (`BLOCKED_SCOPE_DRIFT` / Bounded Scope Supplement)** | 不改变数据结构、跨模块契约、研究语义、权限或风险边界，仅因完成原目标必须新增或触碰原白名单外文件（如新增必要测试或实现路径） | 1. **立即暂停修改白名单外文件**；<br>2. 说明新增文件路径与必要性，完成有限范围 Plan 增补并取得**用户明确批准**；<br>3. **证据与身份绑定核查（Mandatory Identity & Evidence Check）**：增补前必须逐项核查已有运行产物、源包哈希（source bundle hash）、授权绑定（authorization binding）、`RUN_ID` 或验收证据是否依赖原文件集合或原 Plan SHA-256：<br>   - 若**不依赖**：保留既有有效证据，仅对新增/修改文件及受影响边界补充验证；<br>   - 若**依赖**：必须按受影响范围重新生成授权绑定、重跑验证或刷新产物哈希，**严禁沿用已失效的旧哈希或旧收据证明新范围**。 |
| **路径 C：设计或契约变更 (`BLOCKED_SPEC_DRIFT` / Design & Contract Defect)** | 修补需要改变数据结构、跨模块/持久化 Schema、研究假设/统计口径、系统权限或 `L0` 风险边界，或原 Design/Plan 存在结构性矛盾 | 1. **立即停止返修**，保持原 audit verdict（`incomplete` 或 `blocked`）；<br>2. 整理标准 Evidence Packet（失败不变量、上游真实 SSOT 引用、冲突证明、最小调整建议）；<br>3. 退回 `.agent/workflows/design-contract.md` 与 `.agent/workflows/implementation-plan.md`，经独立审查与用户重新批准后再执行。 |

> 若某条 finding 经源码与命令核实无客观依据或无法复现，归类为 `rejected_with_evidence`，记录客观反证提交独立审计复核，不修改代码。

---

## Step 3: 最小批次修补与按需检查 (Minimal Batch Repair)

对归入**路径 A**（或已获用户批准并完成证据绑定核查的**路径 B**）的问题：

1. **按根因分批**：同一根因的问题放在同一最小批次修补，不把无关模块混在同一批次，也不顺手重构未受影响代码（遵循 `.agent/rules/ponytail.md`）。
2. **定向验证**：
   - 行为/逻辑问题：先运行复现测试确认 RED，最小修改后确认 GREEN，且测试期望值必须独立推算（`L1` §2 Rule 4）；
   - 文档/静态规则/配置引用问题：运行对应的链接、引用、哈希或命令检查。
3. **范围与辅助工具检查**：
   - 运行 `git status --short --untracked-files=all`、`git diff --name-only "$BASE_SHA"` 与 `git diff --check "$BASE_SHA"`，确认无越界改动；
   - 若修改了 Python 文件，运行 `python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"`；
   - 若修改了共享符号或契约边界，用 `rg`（及按需 `graphify query/path`）核实调用方兼容性，不在返修期间无条件全量运行 `graphify update .`。

---

## Step 4: 重新交接独立审计 (Re-Verification & Independent Re-Audit)

1. 调用 `.agent/skills/verification-before-completion`，记录每条修补后的实际验证命令、退出码与输出，以及路径 B（若发生）的证据绑定重验记录。
2. 交由**独立 Subagent / 独立会话 / 用户**重新运行 `.agent/skills/audit-plan-completion`；执行返修的 Agent 不得自审宣布 `complete`。
3. 只有独立审计复核给出 `complete` 且用户最终接受后，方可判定闭环。
