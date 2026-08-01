# Stage 1.5D / 1.5F 标题/锚点校验门控 Hotfix 部署评审报告

**日期**: 2026-08-01  
**评审对象**: Stage 1.5D 标题符号提取门控与 Stage 1.5F 线上 Launch Anchor SSOT 校验门控 Hotfix  
**安全级别**: L0 级资金安全与防错重构  
**执行状态**: 已完成代码重构与全套单元/集成测试验证（PASS 100%）

---

## 1. 核心变更摘要 (Executive Summary)

针对 Stage 1.5D 中单币种标题提取事件跳过 BAPI 详情抓取直接发出的缺陷，以及 Stage 1.5F 中旧版/未挂载 SSOT launch anchor 事件可能进入观察队列的风险，本 Hotfix 实现了以下硬化隔离：

1. **Stage 1.5D 移除标题直接发出 Bypass (Direct Emission Bypass Removal)**:
   - 包含单币种/多币种标题提取候选词的公告事件，一律入队 `detail_retry_state`，要求必须经由 BAPI Detail Body 抓取或 `exchangeInfo` 交易对校验。
   - 必须通过 `validate_formal_launch_event` 校验并挂载 `formal_event_contract_version = 1`, `formal_event_consumable_by_stage1_5f = True`, `source_contract_status = "formal_v1_valid"` 后方可写入 `events/*.jsonl`。

2. **Stage 1.5F 极简源契约与 Launch Anchor SSOT 校验 (SSOT Launch Anchor Gate)**:
   - 新增 `classify_stage1_5d_source_contract` 模块，明确划分 `formal_v1_valid`, `formal_v1_missing`, `formal_v1_invalid`。
   - 在 Stage 1.5F 准入防线中，优先评估源契约与 anchor 状态。对于未包含合规 launch anchor 的事件，赋予 `pending_source_event_unvalidated` 或 `rejected_source_contract_invalid`，切断其进入 `events_accepted` 观察队列的路径。

3. **GRVT 真实事故回归冻结 (GRVT Incident Protection)**:
   - 成功抓取并冻结 GRVT (`20536b05b2a34b87a3bae99c45d0dc91`) 的官方 post-incident BAPI payload 及其对应 1.5F 回归测试用例，确保后续任何无有效 launch anchor 的事件均被 100% 拦截。

---

## 2. 变更文件与代码位置 (File Map)

1. [src/research/external_signal_shadow/stage1_5_launch_event_contract.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5_launch_event_contract.py)
   - 导出 `classify_anchor_evidence`, `validate_formal_launch_event`, `build_formal_launch_event` 三大 SSOT 契约函数。
2. [src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py)
   - `EventSymbolState` 升级为 Schema Version 3，新增 `formal_event_contract_version`, `source_contract_status`, `symbol_identity_validation_status`, `launch_anchor_validation_status` 等字段。
3. [src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py)
   - 引入 `classify_stage1_5d_source_contract`；重构 `classify_event_symbol_eligibility_with_diagnostics` 与 `classify_event_symbol_revision_admission`。
4. [src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py)
   - 更新 `create_pending_observation_state` 填充 Schema v3 默认状态。
5. [src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py)
   - 修复 `from configs import base` 导入，新增 `detail_fetch_status == "not_needed"` 过滤机制。
6. [scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py)
   - 移除标题提取直接发出 bypass，增加 `validate_formal_launch_event` 发出前严格校验。
7. [tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_grvt_real_frozen_fixture.json](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_grvt_real_frozen_fixture.json)
   - 冻结的 GRVT 事故真实 API 响应。

---

## 3. 测试验证结果 (Verification Results)

### 3.1 单元测试与集成测试汇总

- **Launch Contract 测试**: `tests/research/external_signal_shadow/test_stage1_5_launch_event_contract.py` (6/6 PASS)
- **1.5D 调度器测试**: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py` (39/39 PASS)
- **1.5D 收集器与烟雾测试**: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py` (106/106 PASS)
- **1.5F 观察者测试**: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py` (33/33 PASS)
- **全套策略与脚本回归测试**: `tests/research/external_signal_shadow/` 与 `tests/scripts/external_signal_shadow/` (1054/1054 PASS)

### 3.2 资金安全 invariant 验证

- `configs/base.py` 中 `RISK_LIVE_TRADING_ENABLED = False` 维持 `False` 状态。
- 系统维持纯 Shadow Observation 模式，没有任何实盘交易风险暴露。

---

## 4. 结论 (Conclusion)

Hotfix 计划中全部 18 项 Task 均已按照规范高标准完成并通过硬核测试验证。系统已具备防范 GRVT 式标题无锚点上线事件冲击的能力。
