
# Stage 1.5G Live Depth Evidence Review Report

**审计结论 (Decision):** `stage1_5g_depth_evidence_quarantined_pass`
**允许的下一步行动 (Allowed Next Action):** `write_stage1_5h_design_only`
**证据范围 (Evidence Scope):** `single_event`
**是否允许推导家族级结论 (Event-Family Conclusion Allowed):** `False`

## 1. 安全边界审计 (Safety Boundaries)

| 安全控制项 (Safety Item) | 状态 (Status) |
| --- | --- |
| 实盘下单 (trade_signal_allowed) | `False` |
| 模拟盘下单 (paper_trading_allowed) | `False` |
| 实盘交易 (live_trading_allowed) | `False` |
| 执行引擎介入 (execution_engine_allowed) | `False` |
| Alpha判定解释 (alpha_interpretation_allowed) | `False` |
| 执行可行性确认 (execution_feasibility_claim_allowed) | `False` |

## 2. 阻断器与警告 (Blockers & Warnings)

- :white_check_mark: 无阻断项 (No blockers)


## 3. 水印审计与证据分类 (Watermark & Evidence Labels)

- **正式证据数量 (Formal announcement_and_launch_time count):** `1`
- **各证据标签统计 (Evidence label counts):**
  - `launch_time_only`: 0
  - `recovery_validation_only`: 0
  - `announcement_and_launch_time`: 1

## 4. 覆盖率与请求健康度审计 (Coverage & Request Health)

- **预估快照总数 (Expected snapshot count):** `720`
- **要求的最低快照数 (Min snapshot count required):** `684`
- **快照采样间隔 (Snapshot interval ms):** `60000 ms`
- **最大快照间隔时间 (Computed max gap allowed):** `600000 ms`
- **全局请求成功率 (Global request success rate):** `1.0`
- **单币最低请求成功率 (Per-symbol min request success rate):** `1.0`

## 5. 裸快照完整性审计 (Raw Snapshot Integrity)

- **JSONL 解析错误行数 (JSONL parse error count):** `0`
- **JSONL 解析错误率 (JSONL parse error ratio):** `0.0`
- **交叉盘/非法订单簿数 (Invalid book count):** `12`
- **非单调递增时间戳数 (Non-monotonic timestamp count):** `0`
- **最大重复快照占比 (Max duplicate snapshot ratio):** `0.0`
- **最大空值率 (Max null ratio):** `0.008356545961002786`

## 6. Quarantine 审计

- **隔离的无效订单簿行数 (invalid_book_row_count):** `12`
- **隔离的无效订单簿分钟数 (invalid_book_minute_bucket_count):** `12`
- **订单簿可用率 (book_availability_ratio):** `0.9805555555555555`
- **订单簿不可用率 (book_unavailable_ratio):** `0.016666666666666666`
- **首个有效订单簿延迟时间 (first_valid_book_latency_ms):** `660000 ms`
- **最大连续无效行数 (max_consecutive_invalid):** `11`
- **Warmup后最大连续无效行数 (max_consecutive_invalid_after_warmup):** `1`
- **执行可用性声明 (execution_availability_claim):** `None`
- **隔离无效行路径 (quarantined_rows_path):** `/private/var/folders/kl/8l2btt7x06z9qwsnfmblw6yw0000gn/T/pytest-of-tanshuai/pytest-468/test_cli_writes_quarantine_art0/review_out/quarantined_invalid_book_rows.jsonl`
- **深度质量输入行路径 (depth_quality_input_rows_path):** `/private/var/folders/kl/8l2btt7x06z9qwsnfmblw6yw0000gn/T/pytest-of-tanshuai/pytest-468/test_cli_writes_quarantine_art0/review_out/depth_quality_input_rows.jsonl`

> [!WARNING]
> quarantined pass 只能支持 1.5H design，不允许 execution feasibility claim / paper / live。

## 7. 深度与滑点审计 (Depth & Slippage Quality)

- **P50 价差 (Spread bps P50):** `None bps`
- **P95 价差 (Spread bps P95):** `None bps`
- **P50 买滑点 (Buy slippage bps P50):** `None bps`
- **P95 买滑点 (Buy slippage bps P95):** `None bps`
- **P50 卖滑点 (Sell slippage bps P50):** `None bps`
- **P95 卖滑点 (Sell slippage bps P95):** `None bps`
- **P05 买盘深度 (Top bid depth P05):** `None USDT`
- **P50 买盘深度 (Top bid depth P50):** `None USDT`
- **P05 卖盘深度 (Top ask depth P05):** `None USDT`
- **P50 卖盘深度 (Top ask depth P50):** `None USDT`
- **健康时间占比 (Healthy window ratio):** `None`
- **深度与持仓上限容量比 (Depth capacity ratio to risk cap P50):** `None`

## 8. 风险与局限性声明 (Risks & Limitations)

> [!IMPORTANT]
> 本审计所用到的 1-minute 静态深度/滑点，仅仅代表 Polling 采样时刻的静态订单簿数据截面（static lower-bound proxy），不能代表实盘高频爆拉或砸盘撮合下的真实 execution 可行性与深度。
> 本阶段依然严禁进行任何形式的实盘/模拟盘交易，或下达任何执行信号。

