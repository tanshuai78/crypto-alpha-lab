# External Signal Shadow Lab Stage 1.5G Raw Snapshot Quarantine Design

**日期:** 2026-07-11
**状态:** design_draft_required_fixes_applied
**适用阶段:** Stage 1.5G Live Depth Evidence Review
**上游依赖:** Stage 1.5F live depth observer output root
**触发背景:** SKHYUSDT 12h live depth evidence 出现 `12 / 718 = 1.67%` invalid book rows，当前 1.5G hard gate 直接 invalid。

---

## 1. 一句话结论

本设计不是新增一个 Stage 1.5G，而是升级现有 Stage 1.5G 的 raw snapshot integrity 判定逻辑。

原 1.5G 逻辑：

```text
只要存在任意 invalid_book
=> stage1_5g_depth_evidence_invalid
```

升级后逻辑：

```text
保留 clean evidence hard gate，新增 quarantine-aware research gate。
少量、可解释、可审计的 invalid book 可以 quarantine，
但只能得到 quarantined pass，不能得到 clean pass，不能打开任何交易权限。
```

核心目标：

```text
不要因为 public REST / launch warmup 的少量空盘口浪费整段 live evidence；
也不要把不可成交分钟误当成无害噪声。
```

---

## 2. 为什么需要 quarantine-aware 1.5G

Stage 1.5F 的职责是录制 post-watermark futures launch 后的 12h live depth snapshots。Stage 1.5G 的职责是审计这批 evidence 是否足以支持下一步研究。

SKHYUSDT 样本显示：

```text
1.5D event capture: pass
1.5F live depth collection: pass
1.5G formal evidence recognition: pass
coverage: pass, 718 >= 684
request health: pass, request_success_rate ~= 0.9986
raw snapshot integrity: fail, invalid_book_count = 12
```

12 条 invalid book 的特征是：

```text
best_bid = null
best_ask = null
spread_bps = null
depth_status = invalid
slippage_status = invalid_depth
```

其中前 11 条集中在 launch observation 初期，符合新合约从 exchangeInfo 可见到 orderbook 稳定之间的过渡现象。但是否能归类为 `launch_warmup_empty_book`，必须优先由 `launch_time_ms` 锚定，不能只用 observation 开始时间替代。

如果继续要求 0 invalid book：

```text
clean evidence 标准很严格，但真实 public REST live evidence 很可能长期难以通过。
```

如果直接忽略 invalid book：

```text
会高估真实执行可行性，尤其是 launch 初期不可成交风险。
```

因此需要第三种状态：

```text
quarantined_depth_evidence_pass
```

它承认样本不是 clean，但允许作为下一步 design-only 输入。

---

## 3. Scope / Non-Scope

### 3.1 Scope

本设计只改变 Stage 1.5G 的离线 review 行为：

```text
input:
  - Stage 1.5F output root
  - depth_snapshots/**/*.jsonl
  - observer_state.jsonl
  - request_manifest/**/*.jsonl
  - events_accepted/**/*.jsonl
  - watermark.json

output:
  - stage1_5g_live_depth_evidence_review_summary.json
  - docs/reviews/YYYY-MM-DD-...stage1_5g...md
  - optional derived quarantine diagnostics
```

新增审查内容：

```text
invalid_book classification
invalid_book phase split with launch_time-aware warmup anchor
invalid row and minute bucket metrics
book availability metrics
first valid book latency gate
valid snapshot count after quarantine
clean / quarantined / invalid decision split
```

### 3.2 Non-Scope

本设计不做：

```text
修改 1.5F 原始 depth snapshots
删除 invalid rows
补造 bid/ask
实盘/模拟盘交易
订单模拟器实现
alpha 判定
execution feasibility claim
```

---

## 4. 新 decision taxonomy

现有 1.5G decision 需要扩展为至少三类 depth evidence 结论。

| decision | 含义 | allowed_next_action | 禁止事项 |
|---|---|---|---|
| `stage1_5g_depth_evidence_clean_pass` | 0 invalid book，coverage/request/depth quality 全过 | `write_stage1_5h_design_or_shadow_simulator_design` | 不允许 paper/live/trade signal；不直接允许 implementation |
| `stage1_5g_depth_evidence_quarantined_pass` | 存在少量可解释 invalid book，quarantine 后有效样本仍过线 | `write_stage1_5h_design_only` | 不允许 1.5H implementation，不允许 execution feasibility claim，不允许 paper/live/trade signal |
| `stage1_5g_depth_evidence_invalid` | invalid ratio 高、midrun 异常超阈值、first valid latency 超阈值、crossed/negative book、或 quarantine 后样本不足 | `continue_observation` | 不允许进入 1.5H implementation |

兼容现有 not-ready 状态：

```text
stage1_5g_not_ready_no_completed_observation
stage1_5g_depth_evidence_observation_only
```

注意：

```text
clean_pass 也不是交易许可。
quarantined_pass 更不是 execution feasibility 证明。
```

所有输出必须保持：

```text
stage1_5h_implementation_allowed = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

---

## 5. Invalid book 分类

Stage 1.5G 需要把 invalid book 分成不同类型。不同类型风险权重不同。

### 5.1 Warmup anchor 选择

Warmup phase 不得默认锚定 `observation_start_ms`。

优先级必须是：

```text
if launch_time_ms is available:
    warmup_window = [launch_time_ms, launch_time_ms + warmup_window_ms)
    warmup_phase_label = launch_warmup
else:
    warmup_window = [observation_start_ms, observation_start_ms + warmup_window_ms)
    warmup_phase_label = observation_initial
    warning = launch_time_missing_warmup_anchor_degraded
```

原因：

```text
如果 1.5F 因 age gate、delayed launch、collector delay 等原因在 launch 后一段时间才开始 observation，
“observation 前 15 分钟”不一定是“launch warmup”。
```

### 5.2 `launch_warmup_empty_book`

定义：

```text
launch_time_ms 存在
launch_time_ms <= fetched_at_ms < launch_time_ms + warmup_window_ms
且 best_bid/best_ask/spread_bps 缺失
且 depth_status = invalid 或 slippage_status = invalid_depth
```

解释：

```text
新合约刚上线时，exchangeInfo 和 orderbook 稳定可能不同步。
该类异常可 quarantine，但不能 clean pass。
```

### 5.3 `observation_initial_empty_book`

定义：

```text
launch_time_ms 缺失
observation_start_ms <= fetched_at_ms < observation_start_ms + warmup_window_ms
且 best_bid/best_ask/spread_bps 缺失
```

解释：

```text
这是 degraded fallback 分类，不能强称 launch_warmup。
summary 必须输出 launch_time_missing_warmup_anchor_degraded warning。
```

### 5.4 `midrun_empty_book`

定义：

```text
fetched_at_ms 不在 warmup_window 内
且 best_bid/best_ask/spread_bps 缺失
```

解释：

```text
稳定后仍出现空盘口，更接近真实流动性中断或 endpoint 异常。
第一版只允许极少量 quarantine。
```

### 5.5 `crossed_or_negative_book`

定义：

```text
best_bid <= 0
best_ask <= 0
best_bid >= best_ask
spread_bps < 0
```

解释：

```text
该类表示盘口逻辑自相矛盾，不应在第一版 quarantine pass 中放行。
默认 hard fail。
```

### 5.6 `schema_invalid`

定义：

```text
关键字段缺失、类型不可转换、event_symbol_id/symbol/fetched_at_ms 缺失。
```

解释：

```text
这属于采集/序列化/loader schema 问题，不应作为市场微结构噪声处理。
默认 hard fail，除非先修 schema compatibility。
```

### 5.7 `request_failed`

定义：

```text
HTTP/network/request manifest 层面失败。
```

解释：

```text
这不属于 raw book content invalid，应走 request health gate。
```

---

## 6. Row count、minute bucket 与 availability 指标

1.5F 产物是 snapshot rows，不能默认 `1 row = 1 minute`。

未来可能出现：

```text
同一分钟多条 snapshot
某些分钟缺 snapshot
poll interval 改变
retry 导致时间不均匀
```

因此 summary 必须同时输出 row count 与 minute bucket count：

```json
{
  "invalid_book_row_count": 12,
  "invalid_book_minute_bucket_count": 12,
  "launch_warmup_invalid_row_count": 11,
  "launch_warmup_invalid_minute_bucket_count": 11,
  "midrun_invalid_book_row_count": 1,
  "midrun_invalid_minute_bucket_count": 1
}
```

Minute bucket 建议按 UTC minute floor：

```text
minute_bucket_ms = fetched_at_ms // 60000 * 60000
```

但 gate 不得只依赖 minute bucket。第一版同时检查 row count 与 minute bucket count。

Book availability 必须独立计算：

```text
book_availability_ratio = valid_book_count / total_expected_snapshots
book_unavailable_ratio = invalid_book_count / total_expected_snapshots
invalid_book_ratio = invalid_book_row_count / observed_snapshot_count
```

SKHYUSDT 候选值：

```text
valid = 706
total_observed = 718
total_expected = 720
invalid_book_ratio = 12 / 718 = 0.0167
book_availability_ratio = 706 / 720 = 0.9806
book_unavailable_ratio = 12 / 720 = 0.0167
```

注意：

```text
invalid rows 不参与 spread/slippage/top-depth 分位数；
invalid rows 必须参与 availability/stability 指标。
```

---

## 7. Quarantine 判定规则

### 7.1 Clean pass

必须满足：

```text
invalid_book_count = 0
coverage pass
request health pass
raw snapshot schema pass
depth quality pass
formal_announcement_and_launch_count >= 1
```

输出：

```text
stage1_5g_depth_evidence_clean_pass
allowed_next_action = write_stage1_5h_design_or_shadow_simulator_design
```

### 7.2 Quarantined pass

必须同时满足：

```text
formal_announcement_and_launch_count >= 1
formal_completed_event_symbol_ids 非空
invalid_book_count > 0
invalid_book_ratio <= MAX_INVALID_BOOK_RATIO
book_availability_ratio >= MIN_BOOK_AVAILABILITY_RATIO
first_valid_book_latency_ms <= MAX_FIRST_VALID_BOOK_LATENCY_MS
launch_warmup_invalid_row_count <= MAX_LAUNCH_WARMUP_INVALID_ROW_COUNT
launch_warmup_invalid_minute_bucket_count <= MAX_LAUNCH_WARMUP_INVALID_MINUTE_BUCKET_COUNT
midrun_invalid_book_ratio <= MAX_MIDRUN_INVALID_BOOK_RATIO
midrun_invalid_book_count <= MAX_MIDRUN_INVALID_BOOK_COUNT
max_consecutive_invalid_after_warmup <= MAX_CONSECUTIVE_INVALID_AFTER_WARMUP
valid_snapshot_count_after_quarantine >= MIN_VALID_SNAPSHOTS_AFTER_QUARANTINE
crossed_or_negative_book_count = 0
schema_invalid_count = 0
coverage pass before and after quarantine
request health pass
quarantined depth quality pass
```

Quarantine 不得提升 observation-only 证据：

```text
launch_time_only / recovery_validation_only / observation_only 可以输出 quarantine diagnostics，
但不能输出 stage1_5g_depth_evidence_quarantined_pass。
```

`expected_snapshot_count` 必须来自 coverage result：

```text
expected_snapshot_count = coverage_metrics.expected_snapshot_count
不得用 len(snapshots) 兜底。
如果 expected_snapshot_count 缺失或 <= 0，输出 expected_snapshot_count_missing，并禁止 quarantined pass。
```

输出：

```text
stage1_5g_depth_evidence_quarantined_pass
allowed_next_action = write_stage1_5h_design_only
```

权限仍然必须是：

```text
stage1_5h_implementation_allowed = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

### 7.3 Invalid

任一条件触发 invalid：

```text
invalid_book_ratio > MAX_INVALID_BOOK_RATIO
book_availability_ratio < MIN_BOOK_AVAILABILITY_RATIO
first_valid_book_latency_ms > MAX_FIRST_VALID_BOOK_LATENCY_MS
midrun invalid 超阈值
warmup invalid row/minute bucket 超阈值
quarantine 后有效样本不足
存在 crossed_or_negative_book
存在 schema_invalid
request health 不过
coverage 不过
raw JSONL parse error 不过
quarantined depth quality 不过
```

输出：

```text
stage1_5g_depth_evidence_invalid
allowed_next_action = continue_observation
```

---

## 8. 建议配置项

所有阈值必须进入 `configs/base.py`。不得在 `src/` 中硬编码。

建议第一版固定使用：

```python
EXTERNAL_SIGNAL_STAGE1_5G_MAX_INVALID_BOOK_RATIO = 0.02

EXTERNAL_SIGNAL_STAGE1_5G_LAUNCH_WARMUP_WINDOW_MS = 15 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5G_MAX_LAUNCH_WARMUP_INVALID_ROW_COUNT = 15
EXTERNAL_SIGNAL_STAGE1_5G_MAX_LAUNCH_WARMUP_INVALID_MINUTE_BUCKET_COUNT = 12

EXTERNAL_SIGNAL_STAGE1_5G_MAX_MIDRUN_INVALID_BOOK_RATIO = 0.002
EXTERNAL_SIGNAL_STAGE1_5G_MAX_MIDRUN_INVALID_BOOK_COUNT = 1
EXTERNAL_SIGNAL_STAGE1_5G_MAX_CONSECUTIVE_INVALID_AFTER_WARMUP = 1

EXTERNAL_SIGNAL_STAGE1_5G_MIN_VALID_SNAPSHOTS_AFTER_QUARANTINE = 684
EXTERNAL_SIGNAL_STAGE1_5G_MIN_BOOK_AVAILABILITY_RATIO = 0.98
EXTERNAL_SIGNAL_STAGE1_5G_MAX_FIRST_VALID_BOOK_LATENCY_MS = 15 * 60 * 1000

EXTERNAL_SIGNAL_STAGE1_5G_CROSSED_OR_NEGATIVE_BOOK_ALLOWED = False
```

设计理由：

- `2%` 总 invalid 上限允许 public REST 少量噪声，但不会放任大面积无效盘口。
- `15min` warmup 只覆盖新合约上线初期盘口同步窗口。
- warmup invalid minute bucket 上限为 12，不允许整个 15 分钟 warmup 窗口 15/15 分钟完全无效。
- midrun invalid 第一版只允许 1 条，因为稳定后空盘口更危险。
- `MIN_BOOK_AVAILABILITY_RATIO = 0.98` 防止删除坏行后忽略不可成交分钟。
- `MIN_VALID_SNAPSHOTS_AFTER_QUARANTINE` 与 `MIN_BOOK_AVAILABILITY_RATIO` 是 AND gate；684/720 只代表 coverage 通过，不代表 availability 通过。
- `MAX_FIRST_VALID_BOOK_LATENCY_MS = 15min` 防止“前 30 分钟无盘口，后面很好”的样本被放行。
- crossed/negative book 第一版不允许 quarantine。
- quarantine 后有效样本仍需达到当前 1.5G 95% coverage 要求。

---

## 9. 输出 schema 扩展

1.5G summary 应新增：

```json
{
  "decision": "stage1_5g_depth_evidence_quarantined_pass",
  "allowed_next_action": "write_stage1_5h_design_only",
  "clean_depth_evidence_pass": false,
  "quarantined_depth_evidence_pass": true,
  "quarantine_candidate": true,
  "stage1_5h_implementation_allowed": false,
  "execution_feasibility_claim_allowed": false,
  "invalid_book_row_count": 12,
  "invalid_book_minute_bucket_count": 12,
  "invalid_book_ratio": 0.0167,
  "invalid_book_ratio_observed": 0.0167,
  "observed_snapshot_count": 718,
  "expected_snapshot_count": 720,
  "valid_snapshot_count_after_quarantine": 706,
  "book_availability_ratio": 0.9806,
  "book_unavailable_ratio": 0.0167,
  "execution_availability_claim": "partial_not_clean",
  "warmup_anchor": "launch_time_ms",
  "launch_time_missing_warmup_anchor_degraded": false,
  "invalid_book_by_phase": {
    "launch_warmup": 11,
    "observation_initial": 0,
    "midrun": 1
  },
  "invalid_book_by_reason": {
    "launch_warmup_empty_book": 11,
    "observation_initial_empty_book": 0,
    "midrun_empty_book": 1,
    "crossed_or_negative_book": 0,
    "schema_invalid": 0
  },
  "launch_warmup_invalid_row_count": 11,
  "launch_warmup_invalid_minute_bucket_count": 11,
  "midrun_invalid_book_count": 1,
  "midrun_invalid_minute_bucket_count": 1,
  "max_consecutive_invalid": 11,
  "max_consecutive_invalid_after_warmup": 1,
  "first_valid_book_latency_ms": 660000,
  "quarantined_rows_path": ".../quarantined_invalid_book_rows.jsonl",
  "depth_quality_input_row_count": 706,
  "quarantine_blockers": [],
  "quarantine_warnings": [
    "not_clean_depth_evidence",
    "launch_warmup_empty_book_present",
    "midrun_empty_book_present"
  ]
}
```

命名要求：

- `clean_depth_evidence_pass` 和 `quarantined_depth_evidence_pass` 必须互斥。
- `quarantined_depth_evidence_pass=true` 时，`clean_depth_evidence_pass=false`。
- `execution_feasibility_claim_allowed` 必须仍为 false。
- `execution_availability_claim` 必须为 `partial_not_clean`，不能输出 `fully_available`。

---

## 10. 派生文件

Quarantine 不得修改原始 `depth_snapshots/**/*.jsonl`。

可以新增派生文件：

```text
stage1_5g/reviews/<run_id>/quarantined_invalid_book_rows.jsonl
stage1_5g/reviews/<run_id>/depth_quality_input_rows.jsonl
stage1_5g/reviews/<run_id>/stage1_5g_quarantine_summary.json
```

用途：

| 文件 | 用途 |
|---|---|
| `quarantined_invalid_book_rows.jsonl` | 记录被隔离的无效盘口行及 reason/phase |
| `depth_quality_input_rows.jsonl` | 记录参与 depth quality 的有效快照行 |
| `stage1_5g_quarantine_summary.json` | 单独记录 quarantine 判定和统计 |

注意：

```text
这些是 derived artifacts，不是 1.5F 原始证据。
只有 invalid_book_row_count > 0 时才写 quarantine artifacts。
clean_pass 不应写空 quarantine 文件，避免误导审计。
```

---

## 11. Depth quality 与 availability quality

原逻辑：

```text
raw_integrity 有任何 invalid_book => 不计算 depth_quality
```

新逻辑：

```text
raw_integrity clean => 用全部 snapshots 计算 clean depth_quality
raw_integrity quarantine_candidate => 用 depth_quality_input_rows 计算 quarantined depth_quality
raw_integrity hard fail => 不计算 depth_quality
```

但必须拆成两组指标：

```text
invalid rows 不参与 spread/slippage/top-depth 分位数。
invalid rows 必须参与 book availability / stability 指标。
```

Summary 示例：

```json
{
  "depth_quality_clean_mode_available": false,
  "depth_quality_quarantined_mode_available": true,
  "quarantined_depth_quality": {
    "input_valid_rows": 706,
    "excluded_invalid_rows": 12,
    "spread_p50_bps": "...",
    "slippage_500usdt_p95_bps": "..."
  },
  "book_availability_quality": {
    "availability_ratio": 0.9806,
    "unavailable_ratio": 0.0167,
    "max_consecutive_invalid": 11,
    "max_consecutive_invalid_after_warmup": 1,
    "first_valid_book_latency_ms": 660000
  },
  "depth_quality_input_mode": "quarantined_valid_rows",
  "depth_quality_input_row_count": 706,
  "excluded_invalid_book_row_count": 12
}
```

避免误把 quarantined depth quality 当作 clean depth quality。

---

## 12. SKHYUSDT 回归预期

当前 hard gate 下：

```text
SKHYUSDT decision = stage1_5g_depth_evidence_invalid
blocker = invalid_book
invalid_book_count = 12
```

按本设计固定第一版阈值后，预期：

```text
clean_depth_evidence_pass = false
quarantine_candidate = true
invalid_book_count = 12
invalid_book_ratio ~= 0.0167
launch_warmup_empty_book_count = 11
midrun_empty_book_count = 1
valid_snapshot_count_after_quarantine = 706
book_availability_ratio ~= 0.9806
first_valid_book_latency_ms = 660000
max_consecutive_invalid = 11
max_consecutive_invalid_after_warmup = 1
```

在第一版阈值下，SKHYUSDT 应固定得到：

```text
stage1_5g_depth_evidence_quarantined_pass
allowed_next_action = write_stage1_5h_design_only
clean_depth_evidence_pass = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

必须新增反例 fixture：

```text
same as SKHYUSDT but midrun_invalid_book_count = 2
=> stage1_5g_depth_evidence_invalid
=> blocker = midrun_invalid_book_count_exceeded
```

---

## 13. 测试要求

必须使用 TDD。至少覆盖：

1. `0 invalid_book` 输出 clean pass。
2. warmup phase 优先使用 `launch_time_ms`，不是 `observation_start_ms`。
3. 缺失 `launch_time_ms` 时使用 `observation_initial_empty_book`，并输出 `launch_time_missing_warmup_anchor_degraded` warning。
4. launch warmup 少量 empty book，row/minute bucket/availability/latency 均过线，输出 quarantined pass。
5. invalid row count 与 invalid minute bucket count 分开计算。
6. `book_availability_ratio < 0.98` 输出 invalid。
7. `first_valid_book_latency_ms > 15min` 输出 invalid，blocker 为 `first_valid_book_latency_too_high`。
8. midrun invalid count = 1 时 SKHYUSDT fixture 输出 quarantined pass。
9. midrun invalid count = 2 时输出 invalid。
10. midrun invalid ratio 超阈值时输出 invalid。
11. crossed book 出现，输出 invalid。
12. schema invalid 出现，输出 invalid。
13. quarantine 后有效样本少于 684，输出 invalid。
14. quarantine 后 depth quality 不过，输出 invalid，不能 pass。
15. `quarantined_depth_evidence_pass` 不允许任何 paper/live/execution flag。
16. depth quality 同时输出 `quarantined_depth_quality` 与 `book_availability_quality`。

---

## 14. 风险边界

Quarantine 是研究便利，不是执行可行性证明。

必须明确：

```text
invalid book = 当分钟不可成交或不可验证成交。
```

因此：

- 不得把 invalid book 删除后宣称 12h 完全可成交。
- 不得把 quarantined pass 用作交易信号。
- 不得用 quarantined pass 推导 event-family alpha。
- 不得把 launch warmup 缺盘口解释成无害噪声。
- 不得把 `depth_quality_input_rows` 当作完整原始市场证据。

Quarantine 只回答：

```text
在严格记录无效盘口和盘口可用性缺口的前提下，剩余有效盘口是否足以支持下一步 simulator design？
```

---

## 15. 推荐下一步

1. 请其他 agent 评审本 design，重点看 `MAX_MIDRUN_INVALID_BOOK_COUNT = 1` 和 `MIN_BOOK_AVAILABILITY_RATIO = 0.98` 是否足够保守。
2. 如果采纳，基于本 design 写 implementation plan。
3. implementation plan 中必须先补 `configs/base.py` 常量和测试。
4. 先用 SKHYUSDT 作为 regression fixture。
5. 实现后重新运行 1.5G，但不得改写原始 1.5F artifacts。

本设计未授权任何 paper/live/execution 行为。
