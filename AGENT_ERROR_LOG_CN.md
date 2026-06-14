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

## 通用提醒

- 当前项目默认路径：`/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab`。
- 不要误用旧项目路径：`/Users/tanshuai/Desktop/AI-test/my-bitcoin-project`。
- 不要自动提交，除非用户明确要求。
