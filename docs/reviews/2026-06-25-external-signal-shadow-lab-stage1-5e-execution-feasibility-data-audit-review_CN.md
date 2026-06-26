# External Signal Shadow Lab Stage 1.5E Execution Feasibility Data Audit Review

## 1. Decision (决策)
- **Top-Level Decision:** `stage1_5e_execution_feasibility_proxy_failed`
- **execution_feasibility_proven:** `False`
- **Allowed Next Action:** `none_reassess`

## 2. Upstream Evidence (上游证据)
- **总唯一事件数量 (top_level_unique_symbol_event_count):** 62
- **候选事件天数 (candidate_event_days):** 47
- **包含事件的标的数量 (symbols_with_events):** 61
- **Blockers (阻碍项):**
- `p95_entry_15m_range_exceeds_multiplier_threshold`
- `entry_1h_range_too_wide`
- `entry_4h_range_too_wide`
- `historical_orderbook_depth_no_matched_snapshots`
- `historical_orderbook_no_candidate_symbol_overlap`

## 3. Cell-Level Historical Proxy Audit (单元格级历史代理审计)

### Cell: `futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay`
- **Cell Status:** `proxy_failed`
- **事件数量 (cell_event_count):** 62
- **Entry 15m Bar Range (BPS):** Median 293.32258254254566, P95 1010.2241125050888
- **Entry 1h Range (BPS):** Median 763.4580133085278
- **Entry 4h Range (BPS):** Median 1493.9796405210327
- **Pre-Entry 24h Volume (USDT):** Median 97943475.75404999, P05 19151759.117771003
- **Quote Volume Pass Rate:** 0.8064516129032258
- **Live Spread (BPS):** Median N/A
- **Live Slippage (BPS for 500 USDT buy):** Median N/A

### Cell: `futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only`
- **Cell Status:** `proxy_failed`
- **事件数量 (cell_event_count):** 62
- **Entry 15m Bar Range (BPS):** Median 293.32258254254566, P95 1010.2241125050888
- **Entry 1h Range (BPS):** Median 763.4580133085278
- **Entry 4h Range (BPS):** Median 1493.9796405210327
- **Pre-Entry 24h Volume (USDT):** Median 97943475.75404999, P05 19151759.117771003
- **Quote Volume Pass Rate:** 0.8064516129032258
- **Live Spread (BPS):** Median N/A
- **Live Slippage (BPS for 500 USDT buy):** Median N/A


## 4. Historical Orderbook / Depth Evidence (历史订单簿/深度证据)
- **historical_orderbook_depth_available:** `False`
- **historical_depth_file_count:** `1164`
- **candidate_symbol_overlap_count:** `0`
- **matched_snapshot_count:** `0`
- **matched_candidate_event_count:** `0`
- **coverage_reject_reason:** `historical_orderbook_no_candidate_symbol_overlap`
- **审计结论:** 历史订单簿深度归档不可用，无法进行历史回测层面的盘口真实成交价核验。

## 5. Live Depth Snapshot Evidence (实时深度快照证据)
- **live_depth_snapshot_available:** `False`
- **Source Smoke Dependency Status:** `pending`
- **审计结论:** 未采集到任何实时盘口快照数据。

## 5.1 Mark / Index Proxy Evidence
- **mark_index_proxy_available:** `False`
- **mark_index_divergence_status:** `not_audited`
- **审计结论:** 当前版本未接入历史 `markPriceKlines` / `indexPriceKlines` / `premiumIndexKlines`，不得声称已完成 mark/index divergence 审计。

## 6. Why close-price replay is still not execution proof (为什么收盘价回放仍然不能证明可执行性)
即使历史 Kline 代理指标与交易量通过审计，收盘价 (close price) 仍然不能作为真实市场成交价的证明。这是因为：
1. **盘口变薄与瞬间重定价风险:** 新币上线或极端事件触发时，盘口买卖价差 (bid/ask spread) 可能极度变宽，单笔 500 USDT 的市价订单就可能产生超过 100 bps 的滑点。
2. **缺乏限价单撮合时间证据:** 真实执行多为 Maker-first，收盘价回放假定可以在 Close Price 瞬间以 100% 填充率成交，忽略了单腿敞口时间和撤单退回逻辑。

## 7. Safety Boundaries (安全边界约束)
- **paper_trading_allowed:** `False`
- **live_trading_allowed:** `False`
- **execution_engine_allowed:** `False`
- **alpha_interpretation_allowed:** `False`

## 8. Allowed Next Action (允许的下一步行动)
- **当前决策:** `stage1_5e_execution_feasibility_proxy_failed`
- **允许行动:** `none_reassess`
- **说明:** 当前尚未满足进入 Stage 1.5F 的条件。请检查并修复相关 Blockers。
