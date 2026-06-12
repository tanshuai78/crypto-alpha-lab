# External Signal Shadow Lab Stage 1.1 Manual Payload Dry Run Design

日期：2026-06-12

## 1. 设计结论

Stage 1.1 的目标不是证明外部信号有 alpha，也不是接入自动 API，而是选择一个真实但只读的外部来源，用手动导出的 payload 跑通以下链路：

```text
真实外部来源页面 / skill 输出
-> 手动保存 raw JSONL + provenance
-> Stage 1 file-backed connector normalize
-> available_at_ms / latency / dedup / price mapping
-> source quality gate / handoff readiness check
-> dry run review
```

第一版 source 采用内部 source id，而不是假设 Gate 有一个稳定叫 `marketanalysis` 的官方产品名：

```text
source = gate_marketanalysis_manual_export
source_vendor = gate
source_surface = gate_big_data_dashboard
source_capture_method = manual_export
source_skill = gate_exchange_marketanalysis
```

这里的 `source` 是本项目内部归因 id，用于 summary、review、数据目录和后续统计归因。它不等同于 Gate 官方 API 名称，也不等同于某个稳定网页产品名。

选择 Gate Big Data dashboard / market data surface 的原因不是因为 funding、liquidation、basis、long-short、rankings 等信号已经证明能赚钱。过去研究已经说明这些信号不应再被当作裸进攻 alpha。选择它只是因为：

- 它偏 CEX market tape，资产多为标准交易对，price mapping 成本低；
- 不涉及钱包、签名、DEX swap、MEV、合约税费；
- 可以手动复制/导出，适合验证 connector 对真实 payload 的容错能力；
- 输出可能包含 liquidity、momentum、funding、basis、liquidation、rankings 等字段，能测试 schema 映射、quarantine、reject、metadata 摘要。

Stage 1.1 只回答一个窄问题：

```text
真实只读外部 payload 是否能被安全、可复现、无偷看未来地接入 External Signal Shadow Lab，并且是否达到进入 Stage 0 replay 的最低数据质量？
```

不能回答：

```text
Gate 数据面板是否能赚钱？
外部 skills 是否比本地策略更强？
是否可以 paper/live？
```

## 2. 为什么先做手动 dry run，而不是自动抓 API

现在项目刚完成 Stage 1.0 file-backed connector。最危险的下一步是直接写 HTTP 抓取器，因为这会一次性引入：

- 外部接口不稳定；
- 字段语义不清；
- source latency 难以复现；
- rate limit / anti-bot / HTML 变动；
- 原始 payload 无法审计；
- 后续结果可能混入“抓取时间”和“事件发生时间”的未来函数。

因此 Stage 1.1 必须保持慢一点，但更干净：

```text
人手动采样 20-30 条外部 payload
-> 落盘到 data/external_signal_shadow/raw/gate_marketanalysis_manual_export/<date>.jsonl
-> connector 读取文件
-> 生成 normalized events + summary + review
```

这一步的价值在于发现真实 payload 和 fixture 的差异：字段缺失、symbol 格式混乱、事件时间不可用、来源延迟过大、同一事件重复出现、外部 payload 携带不可接受字段、手动转换语义不稳定等。

如果 Stage 1.1 都跑不稳，后续自动 connector 没有意义。

## 3. 第一版 source 选择与边界

### 3.1 Source identity

Stage 1.1 必须拆分 source identity，避免一个字段同时表示 vendor、页面、skill、采样方式和 schema。

```text
source = gate_marketanalysis_manual_export
source_vendor = gate
source_surface = gate_big_data_dashboard
source_capture_method = manual_export
source_url = captured_source_url_or_manual_reference
source_skill = gate_exchange_marketanalysis
chain = cex
```

summary 和 review 必须输出这些字段。后续如果切到 Binance / OKX，只变更 `source_vendor/source_surface/source_capture_method`，不能复用 Gate source id。

### 3.2 Allowed CEX universe

第一版只接受 CEX majors，资产必须同时满足：

```text
symbol in STAGE1_1_ALLOWED_SYMBOLS
symbol exists in configs/external_signal_shadow_price_map.json
```

第一版白名单必须放在 `configs/base.py`，不能散落在 connector 代码里：

```text
EXTERNAL_SIGNAL_STAGE1_1_ALLOWED_SYMBOLS = (
  "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"
)
```

非白名单 symbol：

```text
quarantine_reason = unsupported_stage1_1_symbol
```

这个限制是故意的。Gate 榜单可能出现大量小币，如果第一版靠 price map 任意放行，就会把 CEX majors dry run 变成小币事件探索，scope 会失控。

### 3.3 不选择 on-chain / DEX source 的原因

链上 token / meme / DEX 信号可能更接近进攻型机会，但第一版不适合直接接入：

- price mapping 复杂，CEX 代理价格可能不存在；
- DEX 成交价格受到池子深度、税费、MEV、滑点影响；
- token audit 字段复杂，容易误杀或漏掉风险；
- 很多信号需要钱包语义，违反当前只读边界。

所以 Stage 1.1 只做 CEX source dry run。on-chain source 放到 Stage 1.2 或 Stage 2 以后。

## 4. Raw payload 文件规范与 provenance

Stage 1.1 不直接保存网页 HTML，不保存截图，不保存 API key。只保存手动整理后的 JSONL wrapper，每行一条事件。但手动整理必须有 provenance，否则不可审计。

推荐 wrapper：

```json
{
  "source": "gate_marketanalysis_manual_export",
  "source_vendor": "gate",
  "source_surface": "gate_big_data_dashboard",
  "source_capture_method": "manual_export",
  "source_skill": "gate_exchange_marketanalysis",
  "data_quality": "manual_export",
  "capture_id": "gate_big_data_20260612_001",
  "captured_by": "manual",
  "source_observed_at_ms": 1781165880000,
  "fetched_at_ms": 1781165880000,
  "available_at_ms": 1781165880000,
  "manual_transform_version": "stage1_1_v0",
  "field_confidence": {
    "event_time_ms": "source_provided",
    "symbol": "source_provided",
    "score": "source_native"
  },
  "raw_payload": {
    "event_type": "cex_market_tape_anomaly",
    "chain": "cex",
    "symbol": "SOLUSDT",
    "event_time_ms": 1781165400000,
    "score": 78.0,
    "score_scale": "source_native",
    "score_interpretation_allowed": false,
    "liquidity_usd": 50000000.0,
    "metadata": {
      "source_url": "captured_source_url_or_manual_reference",
      "signal_family": "liquidity_momentum",
      "funding_state": "positive",
      "basis_state": "widening",
      "liquidation_state": "elevated",
      "orderbook_state": "thin"
    }
  }
}
```

硬规则：

- `available_at_ms` 必须是我们实际看到/导出该信号的时间；
- `source_observed_at_ms` 必须记录人工观察来源页面或导出文件的时间；
- `event_time_ms` 只能是来源明确给出的事件时间；
- 如果来源没有事件时间，允许使用 `event_time_ms = available_at_ms`，但必须标记 `event_time_policy = available_at_fallback`；
- `available_at_ms < event_time_ms` 必须 reject；
- `data_quality` 必须是 `manual_export`，不能伪装成 API snapshot；
- `field_confidence` 必须说明关键字段来自 source、人工标准化，还是 fallback；
- 禁止字段仍然递归检查：private key、signed tx、order request、swap request、wallet seed 等。

## 5. Event time 与 latency 规则

`available_at_fallback` 样本不能污染 latency 统计。

```text
event_time_policy = source_provided:
  计入 latency_p50_ms / latency_p95_ms

event_time_policy = available_at_fallback:
  不计入 latency 分位数
  计入 event_time_fallback_count
  降低 source quality
```

Stage 1.1 summary 必须输出：

```json
{
  "event_time_fallback_count": 0,
  "event_time_fallback_ratio": 0.0,
  "latency_sample_count": 0,
  "latency_p50_ms": 0,
  "latency_p95_ms": 0
}
```

Stage 1.1 source quality gate：

```text
event_time_fallback_ratio <= 0.50
```

如果 fallback 超过 50%，不能进入 Stage 0 handoff：

```text
failure_type = source_quality_failure
primary_blocker = event_time_unreliable
```

原因：如果多数样本没有来源事件时间，这个 source 的“延迟可交易性”不可评估。

## 6. 事件类型、方向和 score 语义

### 6.1 事件类型映射

Stage 1.1 不新增复杂策略语义，只把外部字段映射成少量已允许事件类型。

```text
外部 market abnormal / rank surge      -> cex_market_tape_anomaly
外部 liquidity expansion              -> liquidity_expansion
外部 liquidity contraction            -> liquidity_contraction
外部 momentum / top gainer alert       -> market_rank_surge
外部 funding/basis/liquidation warning -> cex_market_tape_anomaly
```

### 6.2 方向规则

```text
market_rank_surge        -> direction_hint = unknown
liquidity_expansion      -> direction_hint = unknown
liquidity_contraction    -> direction_hint = avoid
cex_market_tape_anomaly  -> direction_hint = unknown
```

Stage 0 handling 必须明确：

```text
direction_hint = unknown:
  不生成 directional shadow order；
  只进入 event readiness / CUSUM observation branch。

direction_hint = avoid:
  不生成 long/short shadow order；
  只进入 risk/filter event branch。
```

review 必须输出：

```json
{
  "stage0_replay_eligible_event_count": 0,
  "stage0_observation_only_event_count": 0,
  "directionless_event_count": 0,
  "avoid_event_count": 0
}
```

这能防止 implementation agent 为了让 Stage 0 产生 order，把 `market_rank_surge` 偷偷改成 long。

### 6.3 Score 规则

Gate 页面里的 score、rank、热度、指标输出，不一定是 0-100，也不一定线性。Stage 1.1 禁止把 score 当作 alpha strength。

标准语义：

```json
{
  "raw_score": 78.0,
  "score_scale": "source_native",
  "score_interpretation_allowed": false
}
```

禁止：

- 按 score 排序决定收益强弱；
- 跨 event_type 比较 score；
- 把 score 用作仓位大小；
- 把 score 用作 CUSUM 阈值；
- 用 score 调整三重屏障参数。

第一版 score 只能进入 metadata 摘要，不能进入策略参数。

## 7. Price mapping 与 quarantine 规则

Stage 1.1 必须使用显式 price map，不允许临时猜 symbol。

建议新增或扩展：

```text
configs/external_signal_shadow_price_map.json
```

CEX 交易对映射示例：

```json
{
  "cex:solusdt": {
    "price_series_id": "SOLUSDT",
    "venue": "binance",
    "timeframe": "5m",
    "mapping_type": "direct_cex_symbol",
    "active": true
  }
}
```

规则：

- symbol 能 normalize、属于 allowed symbols、并命中 price map -> emitted candidate；
- symbol 缺失 -> quarantine `missing_asset`；
- symbol 不在 Stage 1.1 白名单 -> quarantine `unsupported_stage1_1_symbol`；
- symbol 存在但无 price map -> quarantine `price_mapping_unavailable`；
- source 给出非 USDT pair，例如 `SOL_USDT`、`SOL/USDT`，connector 可 normalize；
- source 给出纯 token 名，例如 `SOL`，Stage 1.1 不猜测，quarantine `ambiguous_symbol`。

## 8. Summary、质量指标与通过标准

Stage 1.1 dry run 输出：

```text
reports/external_signal_shadow/connectors/stage1_1_gate_marketanalysis_manual_summary.json

docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-1-manual-payload-dry-run-review_CN.md
```

summary 必须包含基础统计、source identity、质量指标和 handoff gate：

```json
{
  "source": "gate_marketanalysis_manual_export",
  "source_vendor": "gate",
  "source_surface": "gate_big_data_dashboard",
  "source_capture_method": "manual_export",
  "source_skill": "gate_exchange_marketanalysis",
  "raw_payload_count": 0,
  "emitted_event_count": 0,
  "deduped_payload_count": 0,
  "quarantined_payload_count": 0,
  "rejected_payload_count": 0,
  "summary_accounting_ok": true,
  "unique_symbol_count": 0,
  "unique_event_time_bucket_count": 0,
  "event_time_fallback_count": 0,
  "event_time_fallback_ratio": 0.0,
  "duplicate_ratio": 0.0,
  "price_mapping_unavailable_ratio": 0.0,
  "rejected_payload_ratio": 0.0,
  "single_symbol_dominance_ratio": 0.0,
  "single_time_bucket_dominance_ratio": 0.0,
  "stage0_replay_eligible_event_count": 0,
  "stage0_observation_only_event_count": 0,
  "directionless_event_count": 0,
  "avoid_event_count": 0,
  "minimal_connector_pass": false,
  "stage0_handoff_ready": false,
  "stage0_handoff_blockers": [],
  "live_safe": false,
  "exchange_paper_trading_allowed": false,
  "execution_engine_allowed": false,
  "research_shadow_replay_allowed": true,
  "alpha_interpretation_allowed": false
}
```

### 8.1 Minimal connector pass

这是“脚本与 connector 基础设施可用”的最低标准：

```text
raw_payload_count >= 10
emitted_event_count >= 1
summary_accounting_ok = true
所有 safety flags 为 false
reject/quarantine reason breakdown 完整
所有 emitted event shadow_only = true
所有 emitted event event_time_ms = available_at_ms
无 raw_payload 泄露到 metadata
无 order/swap/wallet/API key 字段
```

### 8.2 Stage 0 handoff ready

只有同时满足以下条件，才允许进入 Stage 0 replay：

```text
minimal_connector_pass = true
raw_payload_count >= 20
emitted_event_count >= 5
unique_symbol_count >= 3
unique_event_time_bucket_count >= 3
event_time_fallback_ratio <= 0.50
price_mapping_unavailable_ratio <= 0.30
rejected_payload_ratio <= 0.30
single_symbol_dominance_ratio <= 0.70
single_time_bucket_dominance_ratio <= 0.70
no safety failure
```

如果只满足 minimal connector pass，但不满足 handoff ready，只能生成 dry-run review，不能跑 Stage 0 replay。

## 9. Source quality failure 量化规则

Stage 1.1 review 必须按以下阈值触发 `source_quality_failure`：

```text
event_time_fallback_ratio > 0.50
unknown_event_type_ratio > 0.30
duplicate_ratio > 0.50
missing_required_field_ratio > 0.30
single_symbol_dominance_ratio > 0.70
single_time_bucket_dominance_ratio > 0.70
```

原因：手动 payload 最容易出现“全是同一榜单刷新”或“字段靠人工猜测”的假密度。这个必须在 Stage 1.1 卡掉，不能让 10 条人工整理样本假通过。

## 10. 与 Stage 0 replay 的关系

Stage 1.1 只负责生成 normalized events 和 connector summary。是否进入 Stage 0 replay 由 review 决定。

允许 handoff 的条件：

```text
minimal_connector_pass = true
stage0_handoff_ready = true
emitted_event_count >= 5
unique_symbol_count >= 3
unique_event_time_bucket_count >= 3
event_time_fallback_ratio <= 0.50
price_mapping_unavailable_ratio <= 0.30
no safety failure
```

禁止 handoff 的条件：

```text
source latency 大量 stale；
price mapping 大量 unavailable；
emitted event 全部来自单一 symbol / 单一时间点；
payload 字段语义不清；
direction_hint 全部为 unknown/avoid，且没有明确 observation-only replay 设计；
source quality failure 被触发。
```

即使进入 Stage 0 replay，也只允许研究 shadow replay，不允许 paper/live。

## 11. 失败类型与下一步决策

Stage 1.1 review 必须按以下类型归因：

```text
data_failure:
  raw payload 太少、文件不可读、字段缺失严重。

schema_failure:
  payload 能读，但无法稳定映射为 ExternalSignalEvent。

latency_failure:
  available_at_ms 延迟过大，真实可交易性不足。

price_mapping_failure:
  多数事件找不到本地 price series。

source_quality_failure:
  来源字段语义不稳定、重复严重、事件时间不可信、样本过度集中。

connector_completed:
  手动 source dry run 可以作为 Stage 1.2 候选。
```

如果 `connector_completed` 且 `stage0_handoff_ready = true`，下一步二选一：

```text
A. 写 Stage 1.2 same-source 7d manual collection plan
B. 将 emitted events 送入 Stage 0 historical/shadow replay 生成初步结构报告
```

如果 `connector_completed` 但 `stage0_handoff_ready = false`，下一步只能继续扩大手动样本或换 source，不能进入 replay。

如果失败，则暂停该 source，换另一个只读 source。不要调 connector 规则去硬救某个 source。

## 12. 明确禁止事项

Stage 1.1 禁止：

- 自动 HTTP 抓取；
- 浏览器自动登录；
- 使用交易所 API key；
- 接钱包；
- 生成订单；
- 连接 paper trading；
- copy trade；
- 把 funding/basis/liquidation/orderbook thin 解释为直接 long/short；
- 事后修改 event_time_ms 来让回测更好；
- 用 fallback event_time 样本美化 latency；
- 用 score 排序、定仓位、调 CUSUM 或调三重屏障；
- 因为某几条样本 shadow PnL 好就宣布 source 有 alpha。

本阶段唯一合理结论是：

```text
这个真实只读 source 是否值得继续进入 7 天手动收集，或是否满足 Stage 0 replay handoff 门槛。
```

## 13. Implementation Plan 前置检查

写 implementation plan 前必须确认：

- Stage 1 connector 当前测试仍通过；
- `configs/base.py` 增加 Stage 1.1 allowed symbol 白名单；
- `configs/external_signal_shadow_price_map.json` 支持至少 BTC/ETH/SOL/XRP/DOGE；
- raw runtime data 目录已在 `.gitignore`；
- review 文件必须是中文；
- 计划中的 source、source_vendor、source_surface、source_capture_method 不混用 fixture source；
- summary schema 包含 quality metrics 和 handoff gate；
- implementation plan 明确 `available_at_fallback` 不计入 latency 分位数；
- 不自动 commit 文档，等待用户 review。

## 14. 当前决策

```text
decision = proceed_to_stage1_1_manual_payload_dry_run_implementation_plan_with_required_fixes
source = gate_marketanalysis_manual_export
source_vendor = gate
source_surface = gate_big_data_dashboard
source_capture_method = manual_export
scope = manual_export_file_only
live_safe = false
exchange_paper_trading_allowed = false
execution_engine_allowed = false
research_shadow_replay_allowed = true
alpha_interpretation_allowed = false
```
