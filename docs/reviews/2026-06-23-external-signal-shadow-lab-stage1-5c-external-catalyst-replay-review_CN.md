# External Signal Shadow Lab Stage 1.5C External Catalyst Replay Review

## 1. 结论与顶层状态 (Conclusion & Top-Level Decision)
- **Top-Level Decision:** `stage1_5c_replay_completed`
- **Research Result Valid (研究结论有效性):** `True`
- **Baseline Trials Override Used (是否使用了调试次数覆盖):** `False`
- **Promising Cells (有希望的实验组):** ['futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay', 'futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only']
- **Top-Level Blockers (全局阻塞原因):** `None`

---

## 2. 价格与流动性过滤漏斗 (Price and Liquidity Funnel)

### Coverage Attrition Funnel (价格与流动性过滤漏斗)
- **输入 Stage 1.5B 原始事件数 (Symbol-Events):** 63
- **允许的事件类型数 (Allowed Event Type Events):** 63
- **CEX 存在性校验通过数 (Market Pair Existence Verified):** 63
- **价格覆盖校验通过数 (Price History Coverage Pass):** 63
- **流动性代理校验通过数 (Liquidity Proxy Pass):** 0
- **去重与冷却后候选事件数 (Candidate Count After Cooldown):** 124
- **参与 Replay 评估的 Primary 样本行数:** 124
- **拒绝原因统计 (Reject Reason Counts):** {}


---

## 3. Cell-Level Replay Results (各实验组 Replay 明细)
| Cell Key | Decision | Event Count | Median Net Return (4h, 50bps) | Baseline Excess Bps | Blockers |
|---|---|---|---|---|---|
| futures_contract_launch|futures_launch_long_attention_diagnostic|1h|G1_source_event_after_first_hour_delay | stage1_5c_cell_failed | 62 | -269.9262265 | -216.64716210153225 | median_net_return_after_50bps_not_positive, baseline_excess_net_bps_not_positive, price_baseline_excess_net_bps_not_positive, left_tail_drawdown_exceeds_random_baseline, top5_profit_share_exceeds_limit |
| futures_contract_launch|futures_launch_long_attention_diagnostic|1h|G2_price_coverage_only | stage1_5c_cell_failed | 62 | -269.9262265 | -216.64716210153225 | median_net_return_after_50bps_not_positive, baseline_excess_net_bps_not_positive, price_baseline_excess_net_bps_not_positive, left_tail_drawdown_exceeds_random_baseline, top5_profit_share_exceeds_limit |
| futures_contract_launch|futures_launch_short_access_diagnostic|1h|G1_source_event_after_first_hour_delay | stage1_5c_cell_failed | 62 | 169.92622649999998 | 223.20529089846772 | left_tail_drawdown_exceeds_random_baseline |
| futures_contract_launch|futures_launch_short_access_diagnostic|1h|G2_price_coverage_only | stage1_5c_cell_failed | 62 | 169.92622649999998 | 223.20529089846772 | left_tail_drawdown_exceeds_random_baseline |
| futures_contract_launch|futures_launch_long_attention_diagnostic|4h|G1_source_event_after_first_hour_delay | stage1_5c_cell_failed | 62 | -158.3364525 | -105.05738810153227 | median_net_return_after_50bps_not_positive, baseline_excess_net_bps_not_positive, price_baseline_excess_net_bps_not_positive, left_tail_drawdown_exceeds_random_baseline, top5_profit_share_exceeds_limit |
| futures_contract_launch|futures_launch_long_attention_diagnostic|4h|G2_price_coverage_only | stage1_5c_cell_failed | 62 | -158.3364525 | -105.05738810153227 | median_net_return_after_50bps_not_positive, baseline_excess_net_bps_not_positive, price_baseline_excess_net_bps_not_positive, left_tail_drawdown_exceeds_random_baseline, top5_profit_share_exceeds_limit |
| futures_contract_launch|futures_launch_short_access_diagnostic|4h|G1_source_event_after_first_hour_delay | stage1_5c_cell_failed | 62 | 58.3364525 | 111.61551689846773 | left_tail_drawdown_exceeds_random_baseline |
| futures_contract_launch|futures_launch_short_access_diagnostic|4h|G2_price_coverage_only | stage1_5c_cell_failed | 62 | 58.3364525 | 111.61551689846773 | left_tail_drawdown_exceeds_random_baseline |
| futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay | stage1_5c_cell_promising | 62 | 117.34571199999999 | 170.62477639846773 | None |
| futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only | stage1_5c_cell_promising | 62 | 117.34571199999999 | 170.62477639846773 | None |
| futures_contract_launch|futures_launch_short_access_diagnostic|12h|G1_source_event_after_first_hour_delay | stage1_5c_cell_failed | 62 | -217.345712 | -164.06664760153225 | median_net_return_after_50bps_not_positive, baseline_excess_net_bps_not_positive, price_baseline_excess_net_bps_not_positive, top5_profit_share_exceeds_limit |
| futures_contract_launch|futures_launch_short_access_diagnostic|12h|G2_price_coverage_only | stage1_5c_cell_failed | 62 | -217.345712 | -164.06664760153225 | median_net_return_after_50bps_not_positive, baseline_excess_net_bps_not_positive, price_baseline_excess_net_bps_not_positive, top5_profit_share_exceeds_limit |

---

## 4. 历史基准对比 (Baseline Comparison)
- **Random Baseline Trials (随机基准模拟次数):** 500
- **Random Baseline Median Net Return (4h, 50bps):** -53.27906439846773 bps
- **Price Move Baseline Median Net Return (4h, 50bps):** -87.220844 bps
- **Random Baseline Left Tail (5th percentile):** -1393.63523 bps

---

## 5. 安全红线与合规披露 (Safety Boundaries & Disclosures)
> [!IMPORTANT]
> **Stage 1.5C research-only constraints:**
> 1. **Stage 1.5C promising does not permit paper/live.** 即使有实验组被判定为 promising，也不允许直接上线实盘 (live) 或模拟盘 (paper)。
> 2. **Stage 1.5C failed does not invalidate external catalyst source audit.** 单个实验组回测失败不代表上游数据源审计结论失效，仅代表当前的被动执行参数在该子组下无法获得正期望。
> 3. **Signed short replay is diagnostic only.** 做空方向的 Replay 纯属诊断性质，不代表实际上有借币、保证金或执行通路。
> 4. **No execution feasibility was proven without orderbook/depth.** 没有配套的订单簿/深度归档数据，任何基于 Close 价格的 Replay 都不算通过执行可行性论证。
> 5. **Delisting replay uses notice_time_available_at; effective_time replay is not implemented.** 退市公告回测仅基于 notice_time_available_at 锚定，尚未实现 effective_time 退市生效日期的回测。
> 6. **A promising cell only allows live event-source smoke collector design, not execution/shadow readiness.** 一个 promising cell 仅允许我们进入 Stage 1.5D 活体事件源收集器设计，不代表任何执行系统已经就绪。

- **paper_trading_allowed:** `False`
- **live_trading_allowed:** `False`
- **alpha_interpretation_allowed:** `False`
- **execution_engine_allowed:** `False`

---

## 6. 后续行动指南 (Allowed Next Action)
- **Replay Invalid:** 修复数据覆盖、Symbol 映射或价格归档。
- **Replay Completed (No Promising Cells):** 增加更多高可信事件源，或扩大回测价格覆盖面。若全部 cell 回测失败，应考虑停止当前分支或在重试前引入 OKX 数据源。
- **Replay Completed (With Promising Cells):** 允许编写 Stage 1.5D 活体事件源收集器设计方案 (write_stage1_5d_live_event_source_smoke_collector_design)。如果考虑部署 Shadow 观察模式，必须首先编写执行可行性数据审计方案 (write_execution_feasibility_data_audit_plan)。
