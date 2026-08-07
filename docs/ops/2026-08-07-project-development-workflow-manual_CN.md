# 项目开发 Workflow 操作手册

**创建日期：** 2026-08-07  
**适用范围：** `crypto-alpha-lab` 的非平凡功能、Bug、契约/Schema、持久化、跨模块运行时与部署行为变更。  
**目标：** 用一条可审计的路径完成“事实确认 → Design → Plan → 实施 → 独立完成审计 → 部署”，避免越界修改、遗漏消费者、错误完成声明与不可恢复的服务器操作。

## 1. 先判断该走哪条路径

| 当前工作 | 必经入口 | 产物 / 结束条件 |
|---|---|---|
| 新功能、跨模块 Bug、Contract/Schema/状态/部署行为变更 | [`design-contract.md`](../../.agent/workflows/design-contract.md) | 已审核的 Design；影响实现的 Open Question 为零 |
| 已批准 Design，需要变成可执行任务 | [`implementation-plan.md`](../../.agent/workflows/implementation-plan.md) | 已审核并获得用户批准的 Plan，含 `Allowed Change Scope` |
| 已批准 Plan，需要写代码 | [`execute-approved-plan.md`](../../.agent/workflows/execute-approved-plan.md) | 独立 `audit-plan-completion` verdict 为 `complete` |
| Plan 已实现，需要决定能否提交、部署或宣称完成 | [`audit-plan-completion`](../../.agent/skills/audit-plan-completion/SKILL.md) | `complete`、`incomplete` 或 `blocked` 的证据化结论 |
| 仅修改文档且不改变运行时语义 | 直接最小修改并做 Markdown/链接检查 | 不需要虚构 Design、Plan 或 TDD |

项目安全规则优先于所有 workflow。每次实质性工作开始前先读取 [`AGENTS.md`](../../AGENTS.md)、[`docs/roadmap.md`](../roadmap.md) 与 [`configs/base.py`](../../configs/base.py)。任何情况下不得隐式改变 `RISK_LIVE_TRADING_ENABLED = False`、风险阈值、execution 权限或观察层的只读边界。

## 2. 标准开发主链

```text
确认工作区事实
  -> Design Review
  -> Plan Review + 用户批准
  -> 受控实施
  -> fresh verification + code review
  -> 独立 completion audit
  -> commit
  -> 如涉及运行时，再按版本化 Runbook 部署
```

任一门禁失败都停止向后推进。修复实现方向、契约、风险、Schema 或验证方式的缺口时，回到 Design 或 Plan，而不是在编码过程中临时扩大范围。

## 3. Design 阶段

使用 [`design-contract.md`](../../.agent/workflows/design-contract.md)。它解决“应该做什么、为什么、何时拒绝、谁消费这些数据”四件事，而不是提前写实现代码。

必须完成：

1. 读取当前源码、测试、Fixture、近期提交、`git status` 与项目 SSOT。
2. 区分 Confirmed Facts、Assumptions、Decisions 与 Open Questions。
3. 写出编号不变量，例如 `INV-01`；每个不变量必须可由后续测试、日志或运行产物验证。
4. 对 producer、writer、loader、consumer、reviewer 写清 Contract、持久化、restart、idempotency、兼容性和 Fail-Closed 语义。
5. 涉及运行时变更时写 rollout/rollback；涉及外部数据时声明 provenance 与数据语义。

Design 审查通过前，任何会改变实现路径、风险、Schema、部署或验证方式的 Open Question 都是 blocker。

## 4. Plan 阶段

使用 [`implementation-plan.md`](../../.agent/workflows/implementation-plan.md)。Plan 是执行合同，不是任务愿望清单。

Plan 顶部必须包含完整的 `Allowed Change Scope`：

```markdown
Allowed implementation paths:
- exact source paths

Allowed verification paths:
- exact test paths

Allowed documentation paths:
- exact review/checklist paths

Allowed generated/runtime artifacts:
- exact ignored artifact paths, or none

Affected but unchanged:
- compatible consumer
  - compatibility evidence: exact test

Forbidden:
- full-repository autofix
- unscoped cleanup
- mutations outside the allowed paths
```

每个 Task 必须列出：对应 `INV-*`、精确文件/接口、预期行为、验证命令、预期结果和非目标。行为代码、Bug、Contract 与序列化语义要写 RED-GREEN 测试；文档、fixture metadata 与部署命令只要求最小可执行验证。

Plan 审查必须覆盖：

1. 白名单是否包含所有真实 producer/consumer/serializer/runner 影响。
2. Graphify 发现的候选下游是否已由源码和 `rg` 证实、修改或以回归测试证明兼容。
3. Ponytail 是否已删除单实现 factory、猜测性 registry、无理由配置和无关重构。
4. 是否把 proxy 数据误标为完整数据或 execution-ready 结论。

只有 Review verdict 为 `Approve` 且用户明确批准，才可进入实施。

## 5. 实施阶段

使用 [`execute-approved-plan.md`](../../.agent/workflows/execute-approved-plan.md)。默认在当前工作区原位执行；只有用户明确要求时才使用 worktree 或多 agent 并行。

开始前必须冻结执行输入：已批准 Plan 的路径与 SHA-256、审核 verdict、用户授权、`BASE_SHA` 和 pre-execution dirty/untracked baseline。baseline 写入 Git metadata，不进入提交范围。

每批执行 1 至 3 个连续 Task；遇到共享 Contract、持久化 Schema、生产 Runner 或部署命令时立即结束本批。每个行为变更遵循：

```text
RED: 先写会按预期失败的测试
GREEN: 仅实现让测试通过的最小代码
REFACTOR: 保持绿色的前提下删除重复和不必要复杂度
SCOPE: 检查 tracked、staged 与 untracked 实际变动
```

发现白名单外修改、全库 autofix 或来源不明的变动时：停止、保存 diff 和 baseline 比对，不得自动 `git checkout`、`git reset`、`git clean` 或删除文件。由用户决定保留、拆分或回退。

## 6. 三个工具的固定分工

| 工具 | 只负责什么 | 不负责什么 |
|---|---|---|
| Superpowers | 需求澄清、Plan 执行、TDD、fresh verification、代码审查与 completion audit 的生命周期门禁 | 不替代源码证据，也不自动授权扩大范围 |
| Ponytail | 在已批准需求内选择最小实现：复用现有代码、stdlib 优先、拒绝猜测性抽象 | 不删除 Fail-Closed、idempotency、restart recovery、兼容性或 SSOT |
| Graphify | 对共享函数、Contract、Schema、CLI、transport boundary 发现候选消费者和拓扑影响 | 不证明正确性；`INFERRED`/`AMBIGUOUS` edge 不能单独构成结论 |

Graphify 的正确使用方式是精准而非泛问：

```bash
.venv/bin/python -m graphify affected "<exact_symbol>"
.venv/bin/python -m graphify path "<producer>" "<consumer>"
rg -n '"<changed_json_key>"|<cli_flag>|<event_type>' src scripts tests
```

仅在实际修改共享边界时运行。所有代码 Task 完成后运行一次 `graphify update .`；更新产生的 `graphify-out/` 文件必须在 Plan 的 generated artifact 白名单中声明，且默认保持 ignored。

## 7. 完成审计、提交与部署

实现者不能只凭“测试通过”宣布完成。先运行 Plan 指定的 targeted/integration/deployment/safety checks、`git diff --check`，对重大改动执行代码审查；然后由独立 subagent、独立 session 或用户运行 [`audit-plan-completion`](../../.agent/skills/audit-plan-completion/SKILL.md)。

审计只接受三个结论：

- `complete`：才可提交、部署或宣称完成。
- `incomplete`：缺实现、接线、序列化、测试、文档或兼容性证据；回到相应 Task。
- `blocked`：存在 P0、验证失败或 provenance 无法核实；停止并由用户决定下一步。

提交时只包含审计允许的范围。运行时 `data/**/*.jsonl`、大 payload 和 server root 默认不提交；小而确定的测试 Fixture、review/checklist 和决策文档按 Plan 明确规则提交。

## 8. Stage 1.5D / 1.5F 部署规则

本手册不复制具体 `tmux`、root suffix、`rsync`、CLI 参数或服务器清理命令。它们随 Contract 版本变化，唯一可执行来源是当前版本化 Runbook：

- [`2026-06-26 Stage 1.5F Live Depth Observer Review，第 7-9 章`](../reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md)
- 对应 hotfix 的 deployment checklist（如有）

每次部署只按以下稳定顺序执行：

1. 完成本地验证与 `audit-plan-completion = complete`。
2. 检查服务器磁盘、当前 tmux/进程、active observation；有 active observation 时不得随意重启 1.5F。
3. 同步代码时排除服务器 `data/`、`.venv/`、`.git/` 与缓存，保护运行证据。
4. 先启动 Stage 1.5D；以实际进程参数和 `live_safety_gate_summary.json` 确认真实 output root 与 gate。
5. 再 bootstrap 并启动 Stage 1.5F；确认其 `--stage1-5d-events-glob` 为 `events/*.jsonl`，不是 `events/\*.jsonl`。
6. 做首次健康检查：runtime gate ready、root contract/version、heartbeat、blocker、accepted/pending/active 状态、glob 命中与 request error。
7. 异常时停止后续启动步骤，保存 tmux pane、进程参数和 summary；不改写旧 root，也不把历史 observation 补写进新 root。

`shadow-deployment` 不单独建立为 workflow，除非同类部署事故重复出现，或 Stage 1.6 及后续多个 source 复用同一部署生命周期。当前做法是让稳定门禁留在本手册，让版本敏感命令留在 Runbook。

## 9. 每次开发的最短检查卡

```text
1. 这是文档修改，还是会改变运行时/Contract/Schema？
2. 若会改变：先走 Design；不要直接改代码。
3. Design 无 blocker 后写 Plan，包含完整 Allowed Change Scope。
4. Plan 审核 Approve 且用户批准后，冻结 Plan hash 和 baseline。
5. 按批次实施；行为代码先 RED，再 GREEN。
6. 每批检查 scope；共享边界才做 Graphify + rg。
7. fresh verification + code review + 独立 completion audit。
8. 只有 complete 才提交；涉及服务器时再按当前 Runbook 部署。
```

这张检查卡不能替代项目规则、已批准 Design/Plan 或当前版本 Runbook；三者冲突时，优先遵守安全规则和当前已批准的具体契约。
