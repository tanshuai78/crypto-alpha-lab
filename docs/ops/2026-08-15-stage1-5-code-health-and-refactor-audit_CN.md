# Stage 1.5 核心模块瘦身与复杂度体检报告

**生成时间：** 2026-08-15  
**文档目的：** 为后续阶段性验证完成后、启动模块重构（Refactoring）提供清晰的技术债务图谱、膨胀根因及拆分建议。  
**范围界定：** 重点针对 Stage 1.5D（事件源采集）、Stage 1.5F（深度盘口观测）和 Stage 1.5G（离线证据复核）的超大模块。  
**当前状态：** 仅做体检与备忘留档，**现阶段暂不实施重构**，维持现有 1,202 个通过测试的稳定运行状态。

---

## 1. 超大文件规模总览

| 文件路径 | 模块归属 | 当前行数 (LOC) | 复杂度等级 | 核心职责概述 |
| :--- | :--- | :--- | :--- | :--- |
| `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` | 1.5D 运行器 | **4,184 行** | 🔴 极高 (God File) | 轮询公告列表、并发抓取详情、重试调度、多币种集合发射、状态持久化与门禁上报。 |
| `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py` | 1.5F 运行器 | **2,016 行** | 🔴 极高 (God File) | 轮询事件流、Pending 锚点生命周期、深度多线程请求、Watermark 事务提交、Compaction 与健康摘要。 |
| `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py` | 1.5G 审查器 | **2,018 行** | 🔴 极高 | 加载多日深度快照、时间单调性/交叉盘口检查、隔离（Quarantine）分类、中英文 Markdown 生成。 |
| `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py` | 1.5F 加载与分类 | **1,295 行** | 🟡 偏高 | 事件加载、时间锚点优先级决议、语义重放指纹比对、准入状态机规约。 |
| `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py` | 1.5D 解析器 | **1,046 行** | 🟡 偏高 | 币安公告标题正则匹配、正文 HTML/表格提取、结算资产识别与时区转换。 |
| `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py` | 1.5F 状态与压缩 | **883 行** | 🟢 中等 | Physical-last 状态字典化简、Two-pass 流式压缩、Batch Registry 状态迁移。 |
| `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py` | 1.5D 重试调度 | **733 行** | 🟢 中等 | 202 降级退避、详情请求预算管理、饿死超时诊断。 |

---

## 2. 深度剖析：三大主要模块的膨胀根因

### 2.1 Stage 1.5D 运行器 (`run_stage1_5d...py` - 4,184 行)
* **膨胀根因**：
  1. **职责过载（God Script）**：该文件不仅包含 CLI 参数和轮询主循环，还内嵌了：
     - `fetch_announcement_detail_with_budget`（HTTP 重试与网络交互）
     - `process_multi_symbol_candidate_sets`（多币种状态集合归约）
     - `reconcile_storage_and_gate`（StorageGuard 边界检查）
     - `build_stage1_5d_smoke_summary`（极其庞大的字典拼装）
  2. **状态机历史补丁堆叠**：为了解决“GRVT 提前开盘”、“BAPI 202 详情延迟”、“正文提取多币种独立时间”等问题，每次都在同一个大函数里插入额外的 `if-elif-else` 分支。
* **重构拆解建议**：
  - `stage1_5d_runner_pipeline.py`：精简后的纯主循环（控制在 300 行内）。
  - `stage1_5d_detail_orchestrator.py`：负责详情抓取、重试回退与预算消耗。
  - `stage1_5d_multi_symbol_manager.py`：独立管理多币种全量/部分发射逻辑。

---

### 2.2 Stage 1.5F 运行器 (`run_stage1_5f...py` - 2,016 行)
* **膨胀根因**：
  1. **复杂的六阶段时间状态机**：包含 `pending_launch_anchor_missing`、`pending_launch_time_in_future`、`active`、`completed`、`rejected`、`expired` 等状态跃迁，全部在单次 poll 的循环体内串行判断。
  2. **混合了高频网络 IO 与原子存储逻辑**：深度快照的并发请求、Watermark 的原子提交、Checkpoint 的定期 Compaction 全都穿插在运行器中。
* **重构拆解建议**：
  - `stage1_5f_lifecycle_manager.py`：纯粹的内存状态流转器（输入事件与当前时间，输出下一个状态）。
  - `stage1_5f_depth_sampler.py`：纯粹的深度采样与并发轮询器。
  - `run_stage1_5f_live_depth_observer.py`：仅保留装配和驱动逻辑（~400 行）。

---

### 2.3 Stage 1.5G 复核器 (`stage1_5g...py` - 2,018 行)
* **膨胀根因**：
  1. **分析逻辑与长文本渲染混杂**：文件中有近 1,000 行纯粹是用于构造大型 Markdown 报告的格式化字符串（表格、统计指标、原因分类等）。
  2. **海量审计规则的平铺**：包含了对交叉盘口、价差过大、时间戳回退、快照缺失等 20+ 项细则的硬编码逐行检查。
* **重构拆解建议**：
  - `stage1_5g_integrity_rules.py`：仅包含纯数据规则断言。
  - `stage1_5g_markdown_renderer.py`：将所有 Markdown 生成模版剥离独立。
  - `stage1_5g_evidence_review.py`：仅保留核心流程编排。

---

## 3. 重构路线图与实施原则（供后续参考）

未来进行重构时，建议遵循以下**五大安全守则**：

1. **测试先行保真（Zero Semantic Regression）**：
   - 依赖现有的 **1,202 个单元与集成测试**。重构必须在测试全绿的前提下一步步移动代码，不改变任何一个业务字段与外部 JSONL Schema。
2. **拒绝过度抽象（Apply Ponytail）**：
   - 拆解的目标是“**拆分大文件为专职小模块**”，而不是引入抽象基类（ABC）、工厂模式（Factory）或通用框架。坚持使用 Python 原生类型与纯函数。
3. **保持 StorageGuard 不变量（L0 Financial Safety）**：
   - 所有的存储写入点依然必须强制要求 `storage_guard` 关键字参数，保留跨进程 `fcntl.flock` 锁定与预算约束。
4. **单阶段独立重构**：
   - 按照 `1.5G 报告渲染器 -> 1.5D 详情编排器 -> 1.5F 状态机` 的顺序，每次只动一个 Stage，独立验证。
