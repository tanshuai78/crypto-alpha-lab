# Stage 1.5D/1.5F 事件采集链路事故复盘与防止重复返修总结

**日期：** 2026-08-11  
**范围：** Stage 1.5D 官方公告采集、Stage 1.5F 深度观察准入、Stage 1.5G 离线证据复核，以及对应部署操作。  
**风险边界：** 本文仅复盘和提出后续工程门禁；不改变 `RISK_LIVE_TRADING_ENABLED = False`，不产生交易信号，也不启用 schedule revision producer。

## 1. 结论

近期并不是“同一个简单抓取功能反复修坏”，而是一个最初只覆盖普通单币公告的研究链路，逐步承担了以下职责：公告正文解析、多个 Symbol 的完整性、官方上线时间选择、跨进程持久状态、Stage 1.5D 到 Stage 1.5F 的契约传递、离线证据血统和服务器部署。每次真实公告都落在此前未覆盖的一个组合边界上。

已完成的修补大多有效地关闭了对应的历史失效路径；当前 `45c2f20d589b420e80063ab75feb41f2` 事件暴露的是一个新的、可复现的时间状态机缺口：**已知且有效的未来上线锚点，被错误使用了仅适用于“锚点缺失/冲突”的 6 小时解析超时。** 这不是 Git ancestry attestation 或 revision producer 的回归。

因此，后续应停止按单个线上事故“看到什么补什么”的模式，改为每个变更都覆盖一张有限、可执行的时间状态矩阵，并把真实事故冻结成离线 fixture。目标不是增加新的框架，而是在已有 parser、loader 和测试模块中补足状态边界测试。

## 2. 事实边界

本文的“已证实”结论来自版本提交、现有审计文档、当前配置及代码路径。对没有保留原始 BAPI payload 的历史事故，不把推断写成原始事实。

| 类别 | 已证实事实 | 证据 |
| --- | --- | --- |
| 运行安全 | 所有 Stage 1.5 链路仍是 public-read-only，交易、paper trading、执行与 alpha interpretation 均禁止。 | `configs/base.py`、`docs/roadmap.md` |
| 公告形态 | Binance 真实公告存在单 Symbol 提前发布、多 Symbol 交错上线、正文表格、非 `USDT` 结算后缀、详情接口短暂 `202` 和延期/改期公告。 | [announcement shape audit](2026-08-01-binance-futures-announcement-shape-audit_CN.md) |
| 当前事故 | `45c2f20d589b420e80063ab75feb41f2` 已被 1.5D 解析成 4 个 formal v2 Symbol；1.5F 将它们终态写为 `rejected_launch_anchor_unavailable_timeout`，尽管其原 `pending_reason` 是 `pending_launch_time_in_future`。 | 2026-08-10/11 服务器检查输出；当前 1.5F loader 逻辑 |
| 当前阈值 | `EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS = 6h`，而 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS = 14d`。 | `configs/base.py` |
| 当前代码顺序 | `re_resolve_pending_anchor()` 对任意 `pending_*` 状态先检查 `anchor_resolution_deadline_ms`，随后才重新解析并使用锚点。 | `stage1_5f_live_depth_observer_loader.py` |

## 3. 已修补问题清单

下表按失效类别归纳。它不是把所有提交都称为 bug；只记录曾导致真实事件遗漏、错误状态、证据不可靠或部署不可验证的关键问题。

| 时间 | 问题 | 直接影响 | 已采取处理 | 为什么当时会遗漏 |
| --- | --- | --- | --- | --- |
| 6 月下旬 | 初版公告采集仅覆盖有限标题形态。 | 标题或正文中不符合最初正则假设的 Symbol 可能缺失。 | 建立 1.5D collector 和后续 parser 扩展。 | 初期历史样本少，公告被误当成稳定格式。 |
| 7 月上旬 | 详情页短暂 `202` / 空响应会使正文 Symbol、上线时间长期不可得。 | 事件不能在应有的时间进入后续链路。 | 增加 BAPI detail 解析、retry scheduler 和 starvation 诊断。 | 单次请求成功的 smoke test 没有覆盖临时可用性。 |
| 7 月中旬 | 非标准结算资产，如 `SPCXUSD1`，不符合仅 `USDT` 的 Symbol 假设。 | 合法合约被解析器漏掉或误分类。 | 扩展 Symbol 解析和对应 fixture。 | 正则从最常见的 `USDT` 格式归纳，未把结算资产变化列为输入维度。 |
| 7 月下旬 | 上线时间可能晚于公告；1.5F 在开盘前就对 exchangeInfo 缺币种做 terminal reject。GRVT 是已知实例。 | 开盘后仍无法恢复，错过整个观察窗口。 | 引入 launch-time pending、历史锚点 hygiene、标题也抓 detail、anchor validation gate。 | “exchangeInfo 当前不可见”被错误解释为“事件无效”，没有区分时间未到与永久不存在。 |
| 7 月下旬 | 多 Symbol 公告可能分批上线，单个 Symbol 可见不能代表整个候选集合完成。 | partial emit、watermark 提前越过 sibling，或同文多次准入。 | 实现 candidate set all-or-none emission、admission dedupe、每 Symbol 时间推进。 | 测试主要是单 Symbol；完整性和时间推进两个规则分属不同模块。 |
| 8 月初 | 标题中已有 Symbol 时，1.5D 曾走快捷路径，不抓正文/表格的官方上线时间。 | GRVT 之类提前公告没有正式锚点。 | 强制标题 Symbol 仍需 detail 证据，增加 formal contract 与 launch-anchor validation。 | “能提取 Symbol”被误认为“已有足够的观察时点证据”。 |
| 8 月初 | 官方公告时间与 exchangeInfo `onboardDate` 可能不一致，且旧 root 的血统字段不完整。 | 1.5F 可能选错 anchor；1.5G 只能给出 observation-only 或误判。 | 建立 anchor contract v2、官方 schedule priority、跨 root contract 和 1.5G lineage 检查。 | 早期把 exchangeInfo 看作唯一权威，未明确“官方计划”和“交易所可见性”是不同事实。 |
| 8 月初 | 1.5F 启动命令曾使用转义的 `events/\\*.jsonl`。 | 进程在运行，但 glob 实际匹配零个 1.5D 事件文件。 | 更新部署 checklist，并增加进程参数与 glob 命中检查。 | shell 引号/转义属于部署层问题，代码单测不会暴露。 |
| 8 月初 | 长时间根目录和离线 review 的全量读取造成磁盘、CPU 或内存压力。 | VPS 卡顿/重启；读证据本身影响采集可用性。 | 清理旧 root、把 1.5G review 移到本地、改用聚合/流式检查。 | 初期数据量小，测试没有模拟多日 snapshot 根目录。 |
| 8 月上旬 | schedule revision producer 需要证明 producer/consumer 使用同一可验证代码与运行根。 | revision 只能作为未充分证明的控制面，不能安全启用。 | formal revision contract、默认关闭、Git ancestry attestation 和 consumer binding。 | 该能力从单根内部状态扩展到跨根/跨进程后，原契约未覆盖部署身份。 |
| 8 月 10-11 日 | 已知未来锚点的 `pending_launch_time_in_future` 在 6 小时后被 `anchor_resolution_deadline_ms` 终态拒绝。 | `45c2...` 的 4 个 Symbol 在实际开盘前被拒绝，未进入 active/snapshot。 | 尚未修补；应进入下一份窄范围设计/计划。 | 已覆盖“无锚点超时”和“短提前公告等待”，但未覆盖“有效未来锚点 + 公告领先超过 6 小时”的组合。 |

## 4. 当前事故的准确根因

`45c2f20d589b420e80063ab75feb41f2` 是 4 Symbol 的正式 v2 公告。1.5D 成功解析正文并发出 `formal_v2_valid` 事件；问题发生在 1.5F 的 pending 生命周期。

1. 公告发布时间早于首次计划上线约 16 小时 45 分钟，属于允许的未来提前量，且小于 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS = 14d`。
2. 1.5F 最初正确把每个 Symbol 放入 `pending_launch_time_in_future`。
3. 该状态的 `anchor_resolution_deadline_ms` 却按 `first_seen_at_ms + 6h` 设置。
4. 运行器每次到 `next_anchor_resolution_at_ms` 或 `next_admission_check_at_ms` 都调用 `re_resolve_pending_anchor()`。
5. 该函数在确认“已有有效未来锚点”之前，先将超过该 deadline 的任意 pending 状态写为 `rejected_launch_anchor_unavailable_timeout`。

这里的术语和实现不一致：`anchor_resolution_deadline_ms` 应约束“尚未获得可用 anchor”的等待时间，不能约束“已获得 anchor、只是尚未到开盘”的等待时间。

### 不应采用的修复

不要仅把 6 小时改成 24 小时或更大。这样会掩盖真正缺少 anchor 的事件，使无效 pending 状态占用更多时间和容量，且仍不能证明所有公告提前量都小于新阈值。

### 正确的最小语义

| pending 状态 | 可以使用的终态 deadline | 不变量 |
| --- | --- | --- |
| `pending_launch_anchor_missing` | `first_seen_at_ms + anchor_resolution_window` | 到期仍没有有效 anchor 才可终态拒绝。 |
| `pending_anchor_conflict` | 明确的 conflict-resolution deadline | 冲突未消除才可终态拒绝。 |
| `pending_launch_time_in_future` 且 anchor 已有效 | 不使用 anchor-resolution deadline；等待 `observation_anchor_ms`。 | 不得仅因公告提前时间长而终态拒绝。 |
| 已到 anchor 但 exchangeInfo 尚不可见 | `anchor + guard + recovery_window`。 | 超过交易所可见性恢复窗口后才可终态拒绝。 |

## 5. 为什么会持续遗漏

### 5.1 测试按事故样本增长，没有按状态组合增长

每轮修补通常都有一个正确的事故回归测试，但测试多为“某个文章 + 某个时点”。实际运行条件是笛卡尔组合：

```text
公告形态
  x Symbol 数量
  x 官方时间证据状态
  x exchangeInfo 可见性
  x 公告领先时间
  x 重启/轮询时刻
  x terminal / pending 状态
  x 事件文件日期轮换与部署 glob
```

GRVT 测试证明了“开盘前不得 hard reject”；它没有证明“开盘前等待超过 6 小时时仍不得 hard reject”。这不是测试写错，而是测试矩阵缺失了时间跨度维度。

### 5.2 语义被复用，状态却已经改变

`anchor_resolution_deadline_ms` 最初适合无 anchor 的重试保护。后来它被放在通用 `pending_*` 入口前，语义悄然扩大为所有 pending 的总寿命。共享入口减少代码不等于共享 deadline 合理；deadline 必须由状态语义决定。

### 5.3 系统边界在扩张，契约晚于数据流形成

链路由“抓取一条公告”扩展到“用可追溯证据驱动 12 小时盘口观察”。上游事件、运行根、consumer identity、revision 与离线 review 都成为契约输入。若新增字段或状态只在一个阶段验证，另一个阶段会用旧假设解释它。

### 5.4 生产部署和资源读取没有被当成一等测试对象

转义 glob、root 选择、`tmux` 重启和大 JSONL 读取不属于 parser 单测，因此出现了“代码正确但进程没有消费事件”以及“review 占满 VPS”两类运行问题。它们需要小型部署合约检查，而不是更多业务逻辑。

### 5.5 真实原始证据没有总能及时冻结

部分早期事故只保留了提取行或运行日志，没有原始 BAPI payload。合成 fixture 能覆盖状态机，但不能覆盖公告正文形态的全部变体。缺失的原始输入让复现从“字节级”退化为“行为级”。

## 6. 防止无休止返修的最小机制

不建议新建一个通用事件平台、状态机框架或大规模模拟器。已有 parser、loader、state 和 test 文件足以承载以下约束。

### 6.1 每个 1.5D/1.5F bugfix 必须先补一张有限矩阵

Design/Plan 中必须列出与本次变更相关的最小输入矩阵和预期终态，不能只列事故本身。对 anchor 生命周期，基线矩阵固定为：

| anchor | 领先时间 | exchangeInfo | 预期 |
| --- | --- | --- | --- |
| 缺失 | 任意 | 任意 | 保持 `pending_launch_anchor_missing` 至解析 deadline。 |
| 有效未来 | `< 6h` | 未可见 | `pending_launch_time_in_future`。 |
| 有效未来 | `> 6h` | 未可见 | 仍为 `pending_launch_time_in_future`，不得使用解析 deadline。 |
| 有效未来 | `16h` | 未可见 | 仍为 pending，覆盖本次事故。 |
| 已到 anchor | recovery window 内 | 未可见 | pending/recovery，不得提前 terminal。 |
| 已过 recovery window | 未可见 | terminal reject。 |
| 已到 anchor | 可见 | 可用 | 晋升 active 并开始采集。 |

对于多 Symbol 事件，上表至少要验证每个 Symbol 独立推进，以及全批次 durable/watermark 规则不被提前提交。

### 6.2 每个真实事故冻结一个最小 fixture 包

在事故发生后一个工作日内，将以下最小材料提交到 `tests/fixtures/external_signal_shadow/`：

1. 原始 BAPI payload 或明确标注为合成的 canonical 输入。
2. 归一化的期望 1.5D event 行，仅保留与事故相关字段。
3. 一组确定的时钟点和 exchangeInfo 可见性输入。
4. 期望的 1.5F 状态序列，例如 `pending -> active -> completed`，或合法 terminal。

本次 `45c2...` 应成为第一个“formal v2 多 Symbol + 有效未来 anchor + 领先超过 6 小时”的 fixture。它不能被只复制标题的测试替代。

### 6.3 新 patch 的合并门槛

每次修复必须同时满足：

1. 原事故 RED test 先失败，再变绿。
2. 邻近矩阵边界至少两项变绿；对时间规则，其中一项必须跨越原阈值。
3. 复用的共享 helper 的所有直接调用者均已检查。
4. 1.5D -> 1.5F 的正式事件行和 state 持久化均断言关键字段，不只断言最终 summary。
5. deployment checklist 包含进程实际参数与 glob 的非变更检查。

这五项应由现有 `design-contract.md`、`implementation-plan.md`、`audit-plan-completion` 和 `remediate-completion-audit.md` 工作流执行；不要为此新增第二套平行工作流。

### 6.4 部署与资源操作的固定边界

1. 服务器只做持续采集、短 summary 和小范围状态检查。
2. 1.5G 大型 review 在本地运行；同步时校验文件清单和大小，读取 JSONL 使用流式迭代，不使用整棵运行根的 `read_text()`。
3. 启动 1.5F 后，必须验证：events glob 至少命中一个文件，且 `ps -efww` 中不含 `\\*.jsonl`。
4. 运行根保留采用明确的磁盘预算和日期清理清单；清理前先确认不属于活动进程 root。

这些是操作约束，不需要改写采集逻辑。

## 7. 本轮后续行动与停止边界

### 必须做

1. 为“状态专属 pending deadline”写一份窄范围 design 和 implementation plan。
2. 实现前先添加 `45c2...` 的离线 fixture 和跨 6 小时阈值的 failing test。
3. 修补只应触及 1.5F pending anchor 生命周期、其已有测试和必要的部署检查说明；不应改动 1.5D parser、revision producer 或 Git ancestry attestation。
4. 修补后，必须在新的真实事件中观察到 `pending_launch_time_in_future -> active -> depth_snapshots`，才可宣称生产路径已验证。

### 不应做

1. 不应为了本次事故扩大 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS`。
2. 不应启用 `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED`；它与本次常规 launch 生命周期无关，仍保持默认关闭。
3. 不应基于一次或两次盘口观察宣称存在 alpha、可交易窗口或执行可行性。
4. 不应在没有 fixture 和时间矩阵的情况下直接热修服务器。

## 8. 可验证的成功标准

本次机制改进是否有效，不以“未来不再有任何 bug”衡量，而以以下可观察条件衡量：

| 标准 | 通过证据 |
| --- | --- |
| 事件解析 | 真实或冻结的 multi-Symbol formal v2 事件完整保留每 Symbol 官方 schedule。 |
| 长领先时间 | 有效未来 anchor 在 6h、16h 和更长测试时钟点均不会因 anchor-resolution deadline 终态拒绝。 |
| 开盘推进 | 到达 anchor 且 exchangeInfo 可见后，状态进入 active 并写入 depth snapshots。 |
| 缺锚点保护 | 真正缺失/冲突 anchor 仍会在各自 deadline 后安全终态，不会无限 pending。 |
| 部署消费 | 1.5F 进程 glob 命中当前 1.5D `events/*.jsonl`，且 process argument 没有转义 glob。 |
| 资源安全 | 本地 1.5G review 对已同步 evidence 运行，不使 VPS 的持续采集进程失去响应。 |

## 9. 最终判断

反复返修的成本真实存在，但根因不是“工程师不仔细”，也不是再增加一层抽象就能解决。根因是外部公告与交易所可见性具有不稳定时间语义，而系统此前没有把这些语义完整建模为有限状态和矩阵测试。

后续每次真实事件仍可能揭示此前未知的外部形态；但只要将每次事故沉淀为最小原始证据、状态转换和跨阈值测试，新增问题会从“等几天才在生产发现”逐步转变为“离线 fixture 立即失败”。这才是缩短等待周期、提高可靠性且不扩大系统复杂度的可行路径。
