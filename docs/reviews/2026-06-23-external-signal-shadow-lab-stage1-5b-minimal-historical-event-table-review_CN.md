# External Signal Shadow Lab Stage 1.5B Minimal Historical Event Table Review

## 1. 结论
当前 Stage 1.5B minimal historical event table 的状态为：`stage1_5b_event_table_ready`。

## 2. Input / Output Evidence
- **上游审计状态 (source_audit_passed)**: True
- **Article 级别公告事件数 (article_level_row_count)**: 94
- **Symbol 扩展后的事件数 (normalized_symbol_event_count)**: 194
- **唯一事件天数 (unique_event_days)**: 81
- **包含事件的 Symbol 数 (symbols_with_events)**: 191

## 3. Article-level Coverage
- 包含公告级别记录 94 条，达到了首期目标的范围要求（门槛值为不少于 30 条）。

## 4. Symbol-expanded Coverage
- 扩展后的事件共有 194 条，覆盖了 191 个交易对，具有合理的时间分布密度（共有 81 个 UTC 日包含事件，门槛值为 20 天）。

## 5. Event Type Counts
- **Article 级别事件类型计数**：
  - `futures_contract_launch`: 71
  - `exchange_delisting_notice`: 23
- **Symbol 级别事件类型计数**：
  - `futures_contract_launch`: 94
  - `exchange_delisting_notice`: 100

## 6. Safety Boundaries (安全边界约束)
> [!IMPORTANT]
> - **Stage 1.5B 准备就绪不代表 alpha 存在，不设定 replay_allowed 为 true**。
> - **Stage 1.5B 准备就绪不允许进行 paper_trading_allowed 或 live_trading_allowed**。
> - **Stage 1.5B 准备就绪不决定任何事件是否符合 Stage 1.5C stage1_5c_replay_candidate_allowed 准入条件**。
> - **Stage 1.5B 仅允许编写 Stage 1.5C replay 实施计划**。
> - 所有归一化生成的 `BASEUSDT` 交易对均为**研究假设**，实际交易所的 `market pair` 是否存在、价格历史覆盖范围 (`price_history_coverage_verified`)、可交易性 (`tradability_verified`)、深度和流动性均**未在 Stage 1.5B 中验证**，必须由 Stage 1.5C 执行检查。
> - 方向性假设 (`directional_hypothesis`) 统一为 `"undefined"`，方向标志 `signed_direction` 为 `null`，禁止任何 long/short 交易意图。
> - 在本阶段中**不输出** funding/OI/liquidation/BTC regime 等 context labels (即 context_label_join_allowed 为 false)。

## 7. Blockers (阻碍因素)
无

## 8. Allowed Next Action (允许的下一步行动)
允许的下一步行动为：`write_stage1_5c_external_catalyst_replay_implementation_plan`。
如果为 `write_stage1_5c_external_catalyst_replay_implementation_plan`，则可进入 Stage 1.5C 的设计与规划阶段。
