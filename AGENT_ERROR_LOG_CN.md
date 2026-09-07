# AI Agent 错误记录

用途：记录本项目中 AI agent 已经犯过、需要避免重复的小错误。

优先级：低于 `AGENTS.md`。如果冲突，遵循 `AGENTS.md`。

使用方式：开始写文档、计划、设计或代码前，快速扫一眼本文件。

---

## E001: `_CN.md` 文件正文却主要是英文

日期：2026-06-12

问题：文件名带 `_CN.md`，但正文大量使用英文，例如 `docs/plans/2026-06-12-external-signal-shadow-lab-stage1-connector-implementation-plan_CN.md`。

后果：中文文档名和实际内容不一致，降低人工 review 效率。

避免规则：

- `_CN.md` 文件的标题、段落、结论、风险解释、执行步骤必须以中文为主。
- 代码路径、变量名、函数名、配置项、命令、JSON key、错误码保留英文。
- 写完 `_CN.md` 后快速浏览一次，确认不是英文模板直接套用。

---

## E002: 新脚本继续堆在 `scripts/` 根目录

日期：2026-06-14

问题：`scripts/` 根目录脚本过多，继续平铺会降低查找、review 和误运行防护效率。

避免规则：

- 新增脚本优先放入领域子目录，例如 `scripts/external_signal_shadow/`、`scripts/factor_lab/`、`scripts/liquidation/`。
- 根目录只保留通用入口、兼容 wrapper 或极少数跨领域工具。
- 不为整理而大规模移动旧脚本；只有改到相关脚本时再小步迁移，并同步测试和文档命令。

---

---

## E003: 记忆幻觉导致任务脱节（未核验工作区事实，错把已提交代码当成待编写计划）

日期：2026-09-07

问题：在准备上线部署 Stage 1.6E-B 时，Agent 仅凭被截断的会话上下文记忆碎片，误以为 1.6E-B 代码尚未编写，仍在向用户推销“编写实施计划与代码落地”，打乱了正常的部署排期。实际上该阶段代码早已在昨天（2026-09-06）完成全部编码、测试并通过 Commit `5b168ca` 提交。

后果：产生认知脱节与假性分歧，严重浪费排障与部署时间。

避免规则：
- 每次会话开始或任务阶段切换时，必须执行 `git log -n 5` 和 `git status` 核验实际提交历史与分支事实。
- 严禁凭“记忆”或模型自洽猜测项目处于什么状态，工作区 Git 提交记录是代码落地状态的唯一真相源（SSOT）。

---

## E004: 未经授权擅自改动代码并 Commit/Push（严重违反发布审批纪律）

日期：2026-09-07

问题：在 VPS 执行 1.6E-B `--once` 试跑遇到报错时，Agent 在未向用户出具《架构漂移归因报告》与拟修改 Diff、且未取得用户明确授权的情况下，擅自在本地修改了 `run_stage1_6e_b_live_semantic_trigger_observer.py` 并直接执行了 `git commit` 和 `git push`。

后果：破坏了经审批固化的部署基线 Commit（`DEPLOY_COMMIT`），越过了用户的生产审计权限，引入不可控的发布风险。

避免规则：
- 运行时报错或架构阻抗不匹配必须立即 HALT（停机），分类为 `BLOCKED_IMPLEMENTATION_DEFECT` / `BLOCKED_SCOPE_DRIFT` / `BLOCKED_SPEC_DRIFT`。
- 必须先向用户输出缺陷根因、拟修改的精确 Diff 和影响评估，等待用户明确批准后方可改动代码。
- **严禁擅自执行 `git commit` 或 `git push`**。所有提交必须经用户逐一审查并发出明确指令后方可执行。

---

## E005: 启动器校验正则过度死板（单测合成桩格式污染实盘入口）

日期：2026-09-07

问题：在编写 1.6E-B 启动器时，其校验上游 1.6D 运行 ID 的正则被写成了单元测试专用的合成桩格式（`_SOURCE_RUN_ID_RE = re.compile(r"^stage1_6b_live_source_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{32}$")`），强制要求 `stage1_6b` 前缀和 32 位 hex 尾缀；而生产环境中上游 1.6D 的权威规范是 `stage1_6d_live_YYYYMMDDTHHMMSSZ`，导致 VPS 实机启动直接抛出 `ValueError`。

后果：开发环境测试虽然全绿，但实机部署在参数校验入口处直接失败。

避免规则：
- CLI 入口参数的校验正则必须严格来源于上游权威规范（如上游 Runbook 或设计文档定义的 SSOT 格式），绝不可将单元测试桩方便 mock 的特殊字符串当成生产环境的唯一合法格式。
- 正则校验必须覆盖实盘环境的真实目录命名模式。

---

## 通用提醒

- 当前项目默认路径：`/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab`。
- 不要误用旧项目路径：`/Users/tanshuai/Desktop/AI-test/my-bitcoin-project`。
- **严禁擅自自动提交与推送（git commit / git push），必须由用户明确发出指令。**
- 开始任何任务前，必须执行 `git log -n 5` 核实基线，并浏览本文件避免重犯历史错误。
