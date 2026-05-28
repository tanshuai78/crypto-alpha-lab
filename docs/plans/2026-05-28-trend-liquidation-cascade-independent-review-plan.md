# Trend Liquidation-Cascade Independent Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `liquidation_cascade` 从当前混合的 Trend / Liquidation 策略中拆分出来，独立完成策略定义、数据源路线选择、历史回放验证和去留审查，判断它是否值得继续保留为个人投资者的 Phase 1B 候选主线。

**Architecture:** 不修改 live execution 层，不恢复已退役的 `vol_breakout` 主线，也不预设第三方路线一定可行。先新增 research-only `liquidation_cascade` classifier / replay / review 流程，把数据源路线显式拆成三条：`A=self_collected_forceorder_only`、`B=third_party_historical_only`、`C=hybrid_forceorder_plus_third_party`。本计划的核心不是“尽快跑出信号”，而是用可审计的证据判断：`liquidation_cascade` 本身是否有独立 alpha，哪条数据路线最适合继续投入，以及当前证据是否只够支持“继续升级数据路线”。

**Tech Stack:** Python 3.11, pytest, JSONL, existing `collect_trend_regime_force_orders.py`, existing `aggregate_trend_regime_liquidations.py`, existing `simulate_trend_regime_shadow(...)`, `configs/base.py`, optional third-party REST adapters, reports under `reports/trend_regime/`, review artifact under `docs/reviews/`.

---

## 1. 决策边界

本计划只回答两个问题：

1. `liquidation_cascade` 作为独立子策略，在个人投资者约束下是否值得保留。
2. 如果值得继续，后续应优先采用哪条数据源路线推进 replay 与 shadow 审查。

本计划明确不做：

- 不恢复 `vol_breakout` 主线。
- 不修改 `src/execution/` 或任何 live trading 开关。
- 不把第三方数据源直接接进 live daemon。
- 不把 Binance `forceOrder` lower-bound proxy 误写成“完整 liquidation volume”。
- 不把任何第三方平台字段未经来源标注直接混入本地自采数据。

本计划必须把以下原则写死：

- `liquidation_cascade` 的研究结论必须独立于 `vol_breakout`。
- 数据源质量优先级必须明确，不能让 replay 结果看起来像同质证据。
- 只要主要盈利假设依赖分钟级冲击，而我们只有小时级粗回放，就必须诚实标注证据边界。
- `signal_direction`、`liquidation_side`、`force_order_side` 必须分开命名，禁止语义混淆：
  - `signal_direction`: `long` / `short`
  - `liquidation_side`: `long_liquidation` / `short_liquidation`
  - `force_order_side`: `SELL` / `BUY`
- `continuation` 与 `mean_reversion` 必须作为两个并列假设输出，不能只做 continuation。
- `Route A` 若仍是 `partial lower-bound proxy + 短覆盖窗口`，只能支持 `continue_data_route_upgrade`，不能单独支持 `retire_liquidation_cascade_branch`。

> **Command convention:** 以下所有命令默认在 repo root 执行；如需显式切换目录，统一使用 `cd "$PROJECT_ROOT"`，禁止写绝对路径。

---

## 2. 当前已知前提

基于前几轮 review，当前已知情况如下：

1. `vol_breakout` 已被独立审查并得到 `retire_vol_breakout_branch` 结论，不再作为本计划前置依赖。
2. 当前历史 rows 对 `liquidation_cascade` 的最大问题不是参数，而是 **历史 liquidation 覆盖不足**。
3. 本地已有自采链路：
   - `scripts/collect_trend_regime_force_orders.py`
   - `scripts/aggregate_trend_regime_liquidations.py`
   - `data/trend_regime_force_orders_raw.jsonl`
   - `data/trend_regime_liquidation_hourly.jsonl`
4. Binance `forceOrder` 语义是：
   - partial snapshot
   - lower bound
   - 不是完整每小时全市场 liquidation volume

因此，本计划不能默认“只靠自采 forceOrder 就能完成历史策略判断”；但也不能在未比较数据路线前，直接把第三方数据定为唯一主线。

---

## 3. 数据源路线决策

本计划必须显式比较以下 3 条路线：

### Route A: `self_collected_forceorder_only`

**定义：**
只使用本地 Binance `forceOrder` WebSocket 自采数据，聚合为 `symbol + hour_bucket_ms` 的 `partial_snapshot_lower_bound` proxy。

**优点：**
- 免费
- 来源清晰
- 与现有链路兼容
- 未来 live / observation 一致性最好

**缺点：**
- 无法回填过去几个月 / 几年的历史
- 只适合从部署时点开始积累
- 对 historical replay 推进速度慢
- 只能覆盖 partial lower bound

### Route B: `third_party_historical_only`

**定义：**
接入第三方历史 liquidation 数据源（例如 Coinglass 等），直接构建历史 replay 数据集。

**优点：**
- 立刻获得更长历史覆盖
- 更适合快速验证 `liquidation_cascade` 是否值得继续
- 不需要等待自采几天或几周

**缺点：**
- 字段口径未必与 Binance 原生一致
- 数据质量、时间粒度、交易所覆盖需要额外审计
- 可能涉及速率限制、付费、SLA 不稳定

### Route C: `hybrid_forceorder_plus_third_party`

**定义：**
第三方历史数据用于补过去的 replay，Binance `forceOrder` 自采用于未来 observation / cross-check / drift validation。

**优点：**
- 最现实的工程折中
- 历史验证和未来链路都能兼顾
- 可以比较“第三方历史口径”与“本地自采口径”是否漂移

**缺点：**
- 工程复杂度最高
- 必须严格标注 source 和 quality，避免混淆

**当前推荐边界：**
- 不预设 `Route C` 一定成立。
- 只有在以下条件同时满足时，`Route C` 才能成为主路线：
  1. `Route B` 可获得足够历史覆盖；
  2. `Route B` 字段能映射到统一 schema；
  3. `Route A` 本地 forceOrder 仍在持续采集；
  4. 两者存在可用于 drift validation 的重叠窗口。
- 如果 `Route B` 不可行，则本轮只允许输出 `Route A` 继续采集或 `continue_data_route_upgrade`，不强行宣称 hybrid 主线成立。

---

## 4. 目标输出

本轮执行完成后，必须产出 4 个可审计 artifact：

1. `reports/trend_regime/2026-05-28_liquidation_cascade_data_source_comparison.json`
2. `reports/trend_regime/2026-05-28_liquidation_cascade_viability_summary.json`
3. `reports/trend_regime/2026-05-28_liquidation_cascade_sensitivity.json`
4. `docs/reviews/2026-05-28-trend-liquidation-cascade-independent-review.md`

四个 artifact 必须回答：

- `liquidation_cascade` 的独立触发定义是什么。
- continuation 与 mean-reversion 哪个假设更有证据。
- Route A / B / C 的数据质量、覆盖长度、字段完备度如何。
- 如果只有第三方历史数据能推进，未来是否仍需本地 forceOrder 做交叉校验。
- 成本后结果是否支持继续进入 Phase 1B。
- Route B feasibility 是否真实可执行，而不是停留在“理论上也许可行”。

---

## 5. Files

- Create: `src/research/trend_liquidation_cascade_review.py`
- Create: `scripts/review_trend_liquidation_cascade.py`
- Create: `tests/research/test_trend_liquidation_cascade_review.py`
- Create: `tests/scripts/test_review_trend_liquidation_cascade.py`
- Create: `docs/reviews/2026-05-28-trend-liquidation-cascade-independent-review.md`
- Create: `reports/trend_regime/2026-05-28_liquidation_cascade_data_source_comparison.json`
- Optionally Create: `scripts/fetch_third_party_liquidation_history.py`
- Optionally Create: `tests/scripts/test_fetch_third_party_liquidation_history.py`

**Commit boundary rules:**
- 只提交 `reports/` 下聚合 summary、`docs/reviews/`、代码和小型 fixture。
- 不提交 `data/*.jsonl`、`forceOrder raw`、`third-party raw payload`、大体量 `results` arrays。

---

### Task 1: Define Research-Only Liquidation-Cascade Classifier

**Files:**
- Create: `src/research/trend_liquidation_cascade_review.py`
- Create: `tests/research/test_trend_liquidation_cascade_review.py`

**Step 1: Write failing tests for independent cascade definition**

Create tests for:

```python
def test_short_liquidation_pressure_maps_to_continuation_long_and_mean_reversion_short():
    ...


def test_long_liquidation_pressure_maps_to_continuation_short_and_mean_reversion_long():
    ...


def test_classifier_rejects_negative_return_negative_oi_without_long_liquidation_pressure():
    ...


def test_cascade_classifier_rejects_missing_liquidation_proxy():
    ...


def test_cascade_classifier_rejects_large_move_without_liquidation_confirmation():
    ...


def test_cascade_classifier_supports_explicit_threshold_overrides():
    ...
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_trend_liquidation_cascade_review.py
```

Expected: FAIL because module does not exist.

**Step 3: Implement research-only classifier**

Create:

```python
@dataclass(frozen=True)
class LiquidationCascadeReviewThresholds:
    ...


def classify_liquidation_cascade_for_review(
    row: dict[str, Any],
    *,
    thresholds: LiquidationCascadeReviewThresholds | None = None,
) -> TrendRegimeClassification:
    ...
```

Requirements:

- Must live in `src/research/`, not live scanner.
- Must explicitly separate:
  - `event_type = liquidation_cascade`
  - `liquidation_side = long_liquidation | short_liquidation`
  - `continuation_direction = long | short`
  - `mean_reversion_direction = long | short`
  - `force_order_side = SELL | BUY`
- Must define strategy direction by market pressure, not liquidation naming:
  - `short_liquidation` (BUY force orders, upward pressure) -> `continuation_direction = long`
  - `long_liquidation` (SELL force orders, downward pressure) -> `continuation_direction = short`
- Must use:
  - price direction
  - OI contraction / liquidation-style OI behavior
  - liquidation proxy direction and notional
- Must support source-aware fields:
  - `liquidation_source`
  - `liquidation_source_quality`
  - `liquidation_notional_semantics`
- Must support explicit `thresholds` injection; do not monkeypatch `configs/base.py`.

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_trend_liquidation_cascade_review.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/trend_liquidation_cascade_review.py tests/research/test_trend_liquidation_cascade_review.py
git commit -m "test: add research-only liquidation cascade classifier"
```

---

### Task 2: Add Data Source Comparison Contract

**Files:**
- Create: `scripts/review_trend_liquidation_cascade.py`
- Create: `tests/scripts/test_review_trend_liquidation_cascade.py`

**Step 1: Write failing tests for source comparison summary**

Required tests:

```python
def test_data_source_comparison_reports_forceorder_partial_quality():
    ...


def test_data_source_comparison_reports_missing_third_party_as_upgrade_gap():
    ...


def test_data_source_comparison_keeps_routes_separate():
    ...


def test_route_a_short_partial_coverage_cannot_retire_strategy():
    ...
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_trend_liquidation_cascade.py
```

Expected: FAIL because script does not exist.

**Step 3: Implement source comparison summary**

Create `scripts/review_trend_liquidation_cascade.py` with:

- `build_data_source_comparison(...)`
- `build_cascade_audit_summary(...)`
- `build_cascade_shadow_summary(...)`
- `build_route_decision_snapshot(...)`

Source comparison must include:

```json
{
  "route_a_self_collected_forceorder_only": {
    "available": true,
    "source_quality": "self_collected_partial_history",
    "coverage_hours": 0.0,
    "liquidation_notional_semantics": "partial_snapshot_lower_bound",
    "allowed_decisions_if_only_route_a": ["continue_data_route_upgrade"]
  },
  "route_b_third_party_historical_only": {
    "available": false,
    "source_quality": "not_connected",
    "coverage_hours": 0.0
  },
  "route_c_hybrid_forceorder_plus_third_party": {
    "available": false,
    "reason": "requires_route_b_and_route_a"
  }
}
```

Decision constraints:

- If only `Route A` is available and `coverage_hours < 720`, then:
  - allowed decision = `continue_data_route_upgrade`
  - forbidden decision = `retire_liquidation_cascade_branch`
- `build_route_decision_snapshot(...)` must expose this constraint explicitly.

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_trend_liquidation_cascade.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/review_trend_liquidation_cascade.py tests/scripts/test_review_trend_liquidation_cascade.py
git commit -m "feat: add liquidation cascade data source comparison"
```

---

### Task 3: Third-Party Historical Data Feasibility Audit

**Files:**
- Optionally Create: `scripts/fetch_third_party_liquidation_history.py`
- Optionally Create: `tests/scripts/test_fetch_third_party_liquidation_history.py`

**Step 1: Write failing tests for feasibility audit and adapter safety**

Tests must cover:

```python
def test_vendor_feasibility_summary_uses_fixture_not_real_network():
    ...


def test_missing_api_key_degrades_gracefully():
    ...


def test_third_party_payload_is_normalized_to_forceorder_hourly_schema():
    ...
```

Hard requirements:

- pytest 期间禁止真实网络请求
- 只能用 fixture + mock 验证解析逻辑
- API key 只能从环境变量读取
- 缺 credential 时必须 `warn/skip/exit-safe`，不能把主测试跑崩

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_fetch_third_party_liquidation_history.py
```

Expected: FAIL because adapter / audit script does not exist.

**Step 3: Audit whether third-party API access is feasible**

This step must inspect:

- authentication requirements
- rate limits
- available time granularity
- exchange / symbol coverage
- legal / operational cost
 - historical depth
 - whether fields support replay-safe normalization

Must output feasibility JSON even if no adapter is implemented:

```json
{
  "vendor_candidates": [
    {
      "vendor": "coinglass",
      "api_access": "unknown|available|unavailable",
      "requires_paid_plan": true,
      "granularity": "unknown|1m|1h",
      "exchange_coverage": [],
      "symbol_coverage": [],
      "historical_depth_days": null,
      "can_support_replay": false,
      "blocker": "..."
    }
  ]
}
```

**Step 4: Implement minimal adapter spike only if feasibility is positive**

Do not wire it into live scanner.  
Only output normalized historical rows with explicit source tags and unified schema:

```json
{
  "liquidation_source": "third_party_historical",
  "liquidation_source_quality": "historical_vendor_dataset",
  "vendor_name": "coinglass",
  "vendor_granularity": "1h",
  "long_liquidation_notional_1h_usdt": 0.0,
  "short_liquidation_notional_1h_usdt": 0.0,
  "hour_bucket_ms": 0
}
```

Adapter requirements:

- Use a dedicated normalization layer so Route B matches Route A hourly schema.
- Never hardcode credentials.
- Never send real HTTP from tests.

**Step 5: Run tests**

If adapter was created:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_fetch_third_party_liquidation_history.py
```

Expected: PASS.

**Step 6: Commit**

Only if adapter spike exists:

```bash
git add scripts/fetch_third_party_liquidation_history.py tests/scripts/test_fetch_third_party_liquidation_history.py
git commit -m "spike: add third-party liquidation history adapter"
```

---

### Task 4: Add Independent Cascade Replay And Sensitivity

**Files:**
- Modify: `scripts/review_trend_liquidation_cascade.py`
- Modify: `tests/scripts/test_review_trend_liquidation_cascade.py`

**Step 1: Write failing tests for replay and horizon audit**

Required tests:

```python
def test_cascade_shadow_uses_only_accepted_entries():
    ...


def test_cascade_shadow_path_uses_same_symbol_and_future_only():
    ...


def test_cascade_outputs_dual_cost_and_holding_hours():
    ...


def test_cascade_sensitivity_does_not_mutate_live_config():
    ...


def test_shadow_outputs_continuation_and_mean_reversion_separately():
    ...
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_trend_liquidation_cascade.py
```

Expected: FAIL on missing replay behavior.

**Step 3: Implement cascade replay summary**

Requirements:

- Must support `4h / 8h / 12h / 24h` holding horizons
- Must support `30 bps / 50 bps` dual costs
- Must support threshold sensitivity if needed
- Must output aggregated-only JSON, no `results` array in committed artifacts
- Must output `continuation` and `mean_reversion` hypotheses separately
- Must keep `Route A` / `Route B` / `Route C` evidence boundaries visible in summary
- If only `Route A` with short partial coverage is available, replay may run, but final recommendation cannot be `retire`

Minimum output:

```json
{
  "strategy_slice": "liquidation_cascade_only",
  "time_span_hours": 0.0,
  "entry_event_count": 0,
  "events_per_30d": 0.0,
  "capital_utilization_label": "too_sparse",
  "hypotheses": {
    "continuation": {
      "shadow_by_holding_hours": {
        "4": {"base": {...}, "stress": {...}},
        "8": {"base": {...}, "stress": {...}},
        "12": {"base": {...}, "stress": {...}},
        "24": {"base": {...}, "stress": {...}}
      }
    },
    "mean_reversion": {
      "shadow_by_holding_hours": {
        "4": {"base": {...}, "stress": {...}},
        "8": {"base": {...}, "stress": {...}},
        "12": {"base": {...}, "stress": {...}},
        "24": {"base": {...}, "stress": {...}}
      }
    }
  }
}
```

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_trend_liquidation_cascade.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/review_trend_liquidation_cascade.py tests/scripts/test_review_trend_liquidation_cascade.py
git commit -m "feat: add liquidation cascade replay and sensitivity"
```

---

### Task 5: Generate Independent Review And Route Decision

**Files:**
- Create: `docs/reviews/2026-05-28-trend-liquidation-cascade-independent-review.md`
- Modify: `scripts/review_trend_liquidation_cascade.py`

**Step 1: Run review script**

Run:

```bash
PYTHONPATH=src uv run python scripts/review_trend_liquidation_cascade.py \
  --rows-input data/trend_regime_historical_rows.jsonl \
  --forceorder-hourly-input data/trend_regime_liquidation_hourly.jsonl \
  --route-summary-output reports/trend_regime/2026-05-28_liquidation_cascade_data_source_comparison.json \
  --summary-output reports/trend_regime/2026-05-28_liquidation_cascade_viability_summary.json \
  --sensitivity-output reports/trend_regime/2026-05-28_liquidation_cascade_sensitivity.json
```

**Step 2: Write review**

Create `docs/reviews/2026-05-28-trend-liquidation-cascade-independent-review.md` with required sections:

1. `范围声明`
2. `策略定义`
3. `数据源路线比较`
4. `当前历史覆盖`
5. `独立 cascade 事件密度`
6. `成本后 shadow 结果`
7. `个人投资者视角评价`
8. `数据源推荐路线`
9. `最终结论`

**Step 3: Enforce final decision gate**

Review 只允许以下三种结论：

1. `retain_for_phase1b_review`
2. `continue_data_route_upgrade`
3. `retire_liquidation_cascade_branch`

推荐 gate：

`retain_for_phase1b_review`：

- 至少一条数据路线已具备可接受覆盖
- `time_span_hours >= 720`
- `entry_event_count >= 10`
- `events_per_30d >= 10`
- `median_net_pnl_bps > 30`
- `stress_cost_50bps.median_net_pnl_bps > 0`
- `worst_trade_net_pnl_bps > -200`
- `stop_loss_exit_rate < 35%`
- `coverage_quality` 不能是 `partial_only_short_window`
- 至少一个 `hypothesis × direction × symbol_tier` 子类单独通过，而不是混合池子偶然好看
- `Route B` 或 `Route C` 可用，或者 `Route A` 覆盖已足够长

`continue_data_route_upgrade`：

- 策略定义看起来合理
- 但 Route A 覆盖不足，Route B/C 尚未接通
- 当前结果还不能回答可行性
- 或第三方 feasibility 尚未通过

`retire_liquidation_cascade_branch`：

- 只有在 Route B/C 或足够长覆盖的 Route A 下，升级数据路线后仍无事件密度或无正期望
- 或对个人投资者而言尾部风险过大、资本利用效率过差
- 禁止在“只有短窗口 partial Route A”条件下直接输出 retire

**Step 4: Placeholder check**

Run:

```bash
rg -n "TODO|TBD|待补|占位|PLAN_NEEDS_VALUE|UNRESOLVED" docs/reviews/2026-05-28-trend-liquidation-cascade-independent-review.md
```

Expected: no output.

**Step 5: Commit**

```bash
git add \
  reports/trend_regime/2026-05-28_liquidation_cascade_data_source_comparison.json \
  reports/trend_regime/2026-05-28_liquidation_cascade_viability_summary.json \
  reports/trend_regime/2026-05-28_liquidation_cascade_sensitivity.json \
  docs/reviews/2026-05-28-trend-liquidation-cascade-independent-review.md
git commit -m "docs: add liquidation cascade independent review"
```

---

## 6. 执行顺序建议

按 3 批执行：

### Batch A：独立策略定义

执行：

- Task 1
- Task 2

通过标准：

- `liquidation_cascade` 定义独立成 research-only classifier
- `signal_direction / liquidation_side / hypothesis` 三者完全分离
- Route A / B / C 的比较框架明确
- 不再与 `vol_breakout` 混在同一个审查口径里

### Batch B：数据路线与 replay

执行：

- Task 3
- Task 4

通过标准：

- 至少明确第三方路线是否可行，并输出 feasibility JSON
- replay summary 能区分不同数据源
- continuation / mean-reversion 两套结果都存在
- dual-cost + holding horizon 输出完整

### Batch C：最终去留决策

执行：

- Task 5

通过标准：

- review 明确给出 `retain / continue_data_route_upgrade / retire`
- 数据源推荐路线由 feasibility 驱动，而不是预设
- 不再让“等 72h 自采”阻塞主线判断

---

## 7. 推荐主线

当前基于已知信息的推荐主线是：

1. 先执行本计划，完成 `liquidation_cascade` 的独立定义和路线审查。
2. 先完成 `Route B feasibility audit`，再决定 `Route C` 是否成立。
3. 如果第三方历史 liquidation 数据可行，再比较 `Route B` 与 `Route C`。
4. 如果第三方路线不可行，再退回 `Route A`，但必须明确它只适合 observation continuity，不适合作为快速推进的主验证路径。

---

## 8. 完成定义

本计划完成后，必须做到：

- `liquidation_cascade` 从混合策略中独立出来；
- 数据路线选择不再摇摆；
- 历史验证与未来 observation 的角色边界清楚；
- 可以明确回答：这个方向是否值得继续投入，而不是继续停留在“数据不够，所以暂时不知道”；
- 即便本轮无法做 alpha 结论，也能明确给出 route decision，而不是继续拖延。
