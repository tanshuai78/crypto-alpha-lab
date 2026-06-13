# External Signal Shadow Lab Stage 1.2 Gate Public Read-Only Collector Design

日期：2026-06-12

## 1. 设计结论

Stage 1.2 的目标是替代 Stage 1.1 中不适合长期执行的“手动写 JSONL”流程，改为由脚本自动采集 Gate 官方公开只读市场数据，并输出 Stage 1 connector 可消费的 raw JSONL。

第一版不再要求用户手动寻找 Gate 页面、手动抄字段、手动拼 payload。流程改为：

```text
Gate public REST market endpoint
-> one-shot collector script
-> raw JSONL with provenance
-> Stage 1 file-backed connector normalize
-> Stage 1 summary / review
-> 可选 Stage 0 observation-only handoff
```

Stage 1.2 只回答一个窄问题：

```text
我们能否稳定、无登录、无 API key、无交易权限地把 Gate 公开市场快照采集成可审计 raw payload？
```

不能回答：

```text
Gate 数据是否有 alpha？
公开市场快照是否能预测涨跌？
是否可以进入 paper/live？
```

最终建议：执行 Stage 1.2，但必须把 `cex_market_snapshot` 明确定义为 observation-only 数据点，而不是外部主动交易事件。它只能用于观察、数据质量验证和后续研究锚点，不能进入三重屏障 directional order。

## 2. 为什么不继续手动 JSONL

手动 JSONL 有三个现实问题：

- 对小白不可操作：不知道市场数据页面在哪里，也不清楚每个字段该怎么翻译成事件。
- 不可复现：不同人手动整理同一页面，可能写出不同字段、不同事件时间、不同 score。
- 容易污染证据：人工可能为了让 pipeline 通过，无意中挑选“看起来更像信号”的样本。

所以 Stage 1.2 不应该让用户继续手写 payload。手动 payload 只保留两个用途：

- 单元测试 fixture；
- 极端异常样本调试。

真实 dry run 必须由脚本生成 raw payload，并且脚本必须写清楚来源、采集时间、字段语义和不可交易边界。

## 3. Source Identity

Stage 1.2 使用新的 source id，和 Stage 1.1 的 manual export 分开，避免混淆。

```text
source = gate_public_market_snapshot_collector
source_vendor = gate
source_surface = gate_api_v4_public_market_data
source_capture_method = public_rest_snapshot
source_skill = gate_public_market_snapshot_collector
chain = cex
```

说明：

- `source` 是项目内部归因 id，不是 Gate 官方产品名。
- `source_surface` 表示数据来自 Gate API v4 public market data，而不是手动页面导出。
- `source_capture_method` 明确是 public REST snapshot，不是 authenticated API、不是网页登录、不是复制交易。

Gate 官方 API v4 文档说明其 REST base URL 是 `https://api.gateio.ws/api/v4`，并提供公开行情接口；Gate SDK 文档中也列出 spot public endpoint，例如 `GET /spot/tickers` 用于获取 ticker 信息。

## 4. 第一版采集范围

Stage 1.2 第一版只采集 CEX majors，不碰 meme、小币、DEX、链上 token。

允许 Gate currency pair：

```text
BTC_USDT
ETH_USDT
SOL_USDT
XRP_USDT
DOGE_USDT
```

对应项目 canonical symbol：

```text
BTCUSDT
ETHUSDT
SOLUSDT
XRPUSDT
DOGEUSDT
```

collector 内部必须做 normalize：

```text
BTC_USDT -> BTCUSDT
BTC/USDT -> BTCUSDT
btcusdt -> BTCUSDT
```

非白名单 symbol 不采集。第一版不做全市场扫描，原因是 Stage 1.2 是数据入口验证，不是找 alpha。

## 5. 采集方式：逐 symbol 公开请求

第一版必须对 5 个白名单逐个请求 ticker endpoint：

```text
GET /spot/tickers?currency_pair=BTC_USDT
GET /spot/tickers?currency_pair=ETH_USDT
GET /spot/tickers?currency_pair=SOL_USDT
GET /spot/tickers?currency_pair=XRP_USDT
GET /spot/tickers?currency_pair=DOGE_USDT
```

不采用：

```text
GET /spot/tickers
然后本地过滤全市场
```

原因：

- 避免全市场响应过大；
- 避免无意采入非白名单；
- 每个 symbol 可以独立记录 HTTP status、latency、parse error；
- 单个 symbol 失败不影响其他 symbol；
- summary 能准确统计 per-symbol failure。

第一版只做 public REST API，不做网页爬虫。

禁止：

- 登录 Gate；
- 使用 API key；
- 使用 Gate SDK；
- 使用 ccxt；
- 读取 `.env`、环境变量、secrets 文件；
- 调用 private endpoint；
- 读取账户、余额、订单、仓位；
- 提交 order / cancel / transfer / swap；
- 存储 cookie、token、secret。

第一版 REST client 建议只使用 Python 标准库：

```text
urllib.request
json
time
datetime
hashlib
```

这样做不是因为 SDK 不好，而是为了降低误用 private endpoint / auth profile 的风险。

## 6. 配置入口

所有 REST 参数和白名单必须进入 `configs/base.py`，不能散落在脚本或 `src/` 里。implementation plan 必须新增并注释以下常量：

```python
EXTERNAL_SIGNAL_STAGE1_2_GATE_REST_BASE_URL = "https://api.gateio.ws/api/v4"
EXTERNAL_SIGNAL_STAGE1_2_GATE_TICKERS_PATH = "/spot/tickers"
EXTERNAL_SIGNAL_STAGE1_2_ALLOWED_GATE_PAIRS = (
    "BTC_USDT",
    "ETH_USDT",
    "SOL_USDT",
    "XRP_USDT",
    "DOGE_USDT",
)
EXTERNAL_SIGNAL_STAGE1_2_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_2_MAX_RETRIES = 1
EXTERNAL_SIGNAL_STAGE1_2_RETRY_BACKOFF_SEC = 2.0
EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT = "crypto-alpha-lab-research-readonly/0.1"
```

每个常量都要有中文或英文注释说明用途、安全范围和为什么不可用于交易。

## 7. Collector 输出 raw JSONL 规范

Stage 1.2 collector 输出路径：

```text
data/external_signal_shadow/raw/gate_public_market_snapshot_collector/YYYY-MM-DD.jsonl
```

该路径必须在 `.gitignore` 中，不能提交真实 raw 数据。

每行 wrapper 示例：

```json
{
  "source": "gate_public_market_snapshot_collector",
  "source_vendor": "gate",
  "source_surface": "gate_api_v4_public_market_data",
  "source_capture_method": "public_rest_snapshot",
  "source_skill": "gate_public_market_snapshot_collector",
  "data_quality": "api_snapshot",
  "capture_id": "gate_public_market_snapshot_20260612_001",
  "captured_by": "script",
  "collector_run_id": "gate_public_market_snapshot_20260612T120000Z",
  "collector_run_started_at_ms": 1781165880000,
  "collector_run_finished_at_ms": 1781165880123,
  "snapshot_sequence_id": 1,
  "sampling_interval_sec": null,
  "schedule_generated": true,
  "source_observed_at_ms": 1781165880123,
  "fetched_at_ms": 1781165880123,
  "available_at_ms": 1781165880123,
  "api_endpoint": "/spot/tickers",
  "api_query": {"currency_pair": "BTC_USDT"},
  "api_status_code": 200,
  "api_latency_ms": 123,
  "api_response_hash": "sha256_hex",
  "api_response_field_names": ["currency_pair", "last", "base_volume", "quote_volume", "change_percentage"],
  "field_confidence": {
    "event_time_ms": "available_at_fallback",
    "symbol": "normalized",
    "score": "missing"
  },
  "raw_payload": {
    "event_type": "cex_market_snapshot",
    "chain": "cex",
    "symbol": "BTCUSDT",
    "event_time_ms": 1781165880123,
    "event_time_policy": "available_at_fallback",
    "direction_hint": "unknown",
    "score_interpretation_allowed": false,
    "triple_barrier_directional_order_allowed": false,
    "alpha_interpretation_allowed": false,
    "metadata": {
      "gate_currency_pair": "BTC_USDT",
      "source_url": "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT",
      "last_price_raw": "65000.1",
      "last_price_parse_ok": true,
      "base_volume_raw": "123.45",
      "base_volume_parse_ok": true,
      "quote_volume_raw": "8000000",
      "quote_volume_parse_ok": true,
      "change_percentage_raw": "1.23",
      "change_percentage_parse_ok": true
    }
  }
}
```

关键规则：

- `available_at_ms = fetched_at_ms`。
- 如果 API 返回结果没有可靠事件时间，则 `event_time_ms = available_at_ms`，并标记 `event_time_policy = available_at_fallback`。
- `available_at_fallback` 样本不能用于 latency alpha 判断。
- `direction_hint = unknown`，不允许生成 directional triple-barrier order。
- `triple_barrier_directional_order_allowed = false`。
- `alpha_interpretation_allowed = false`。
- `score_interpretation_allowed = false`，不能把 API 字段直接当强弱评分。
- `metadata` 只存白名单字段和解析状态，不存完整 raw response。
- raw wrapper 层必须保存 `api_response_hash`、endpoint、query、status、latency、field names，保证可审计。

## 8. 数值字段规则

Gate ticker 返回的价格、成交量、涨跌幅等字段可能是字符串形式数字。第一版必须保留原始字符串，并单独记录 parse 状态。

示例：

```json
{
  "last_price_raw": "65000.1",
  "last_price_parse_ok": true,
  "base_volume_raw": "123.45",
  "base_volume_parse_ok": true,
  "quote_volume_raw": "8000000",
  "quote_volume_parse_ok": true,
  "change_percentage_raw": "1.23",
  "change_percentage_parse_ok": true
}
```

解析失败不能猜测、不能填 0。必须记录：

```text
field_parse_failure
numeric_parse_failure_count
numeric_parse_failure_ratio
```

如果必需字段解析失败，该 symbol 的 payload 进入 quarantine 或 collector failure breakdown。

## 9. Event Type 语义

第一版新增一个保守事件类型：

```text
cex_market_snapshot
```

它表示“采集到一条公开市场快照”，不是买入信号，也不是卖出信号。

Stage 1 connector 的 event type whitelist 必须新增：

```text
cex_market_snapshot
```

映射规则：

```text
cex_market_snapshot:
  direction_hint = unknown
  score_interpretation_allowed = false
  observation_only = true
  triple_barrier_directional_order_allowed = false
  alpha_interpretation_allowed = false
```

禁止把 `cex_market_snapshot` 映射成：

```text
market_rank_surge
momentum_signal
liquidity_expansion
long
short
```

因为它是定时快照，不是外部系统主动发出的异常事件。

## 10. Stage 0 handoff 语义

Stage 1.2 产生的数据只能用于 observation-only handoff。

```text
stage0_handoff_mode = observation_only
stage0_directional_replay_ready = false
stage0_observation_handoff_ready = true
```

必须明确：

```text
cex_market_snapshot never creates directional shadow order
```

原因是定时快照的事件密度来自采样频率，不是市场真实 signal 频率。如果每 5 分钟跑一次 collector，就会机械地产生 5 条新 event。这个 event count 只能证明采集成功，不能证明外部信号频率，也不能证明 alpha。

summary 必须输出：

```json
{
  "schedule_generated": true,
  "event_density_alpha_valid": false,
  "stage0_handoff_mode": "observation_only",
  "stage0_directional_replay_ready": false,
  "triple_barrier_directional_order_allowed": false
}
```

## 11. 与 Stage 1.1 的关系

Stage 1.1 已经证明：file-backed connector 可以处理一批结构化 Gate-like payload，并输出 observation-only handoff。

但 Stage 1.1 的真实 manual raw 文件实际仍接近 fixture 镜像，不能证明真实用户可长期操作。

Stage 1.2 的价值是补上这一环：

```text
不是人工写样本，而是脚本采集公开快照。
```

Stage 1.2 完成后，如果 public collector 稳定，再考虑 Stage 1.3：

```text
Gate MarketAnalysis skill / MCP readonly adapter
或 Gate / Binance / OKX 多来源 public collector 对比
```

而不是马上做 alpha。

## 12. 安全边界

Stage 1.2 必须继承 Stage 0 / Stage 1 的安全边界：

```json
{
  "live_trading_enabled": false,
  "exchange_paper_trading_allowed": false,
  "execution_engine_allowed": false,
  "research_shadow_replay_allowed": true,
  "alpha_interpretation_allowed": false,
  "wallet_required": false,
  "api_key_required": false,
  "private_endpoint_used": false
}
```

任何响应、payload、metadata 中出现以下字段，必须 reject：

```text
api_key
secret
private_key
signed_tx
raw_tx
wallet_seed
mnemonic
order_request
swap_request
transfer_request
```

即使来自 public API，也必须递归检查 forbidden keys。

## 13. 质量门禁

Stage 1.2 的通过不是收益通过，而是 collector 基础设施通过。必须拆成三层。

### 13.1 Collector minimal pass

```text
http_success_count >= 5
http_failure_count = 0
raw_payload_count >= 5
api_key_used = false
private_endpoint_used = false
forbidden_payload_count = 0
```

### 13.2 Connector minimal pass

```text
emitted_event_count >= 5
unique_symbol_count >= 5
price_mapping_unavailable_ratio = 0.0
summary_accounting_ok = true
all emitted events shadow_only = true
all emitted events notional_usd = 0.0
```

### 13.3 Stage 0 observation handoff ready

```text
collector_minimal_pass = true
connector_minimal_pass = true
stage0_handoff_mode = observation_only
stage0_observation_handoff_ready = true
stage0_directional_replay_ready = false
event_density_alpha_valid = false
```

如果只采集到 1-2 个 symbol，或者 price mapping 不完整，只能输出 collector dry-run review，不能进入 Stage 0 observation handoff。

## 14. 错误处理与失败 summary

collector 必须安全失败，并且即使失败也写 summary。不能只退出非零。

summary 路径：

```text
reports/external_signal_shadow/connectors/stage1_2_gate_public_collector_summary.json
```

失败 summary 至少包含：

```json
{
  "decision": "external_signal_collector_stage1_2_failed",
  "failure_type": "collector_network_failure|rate_limited|parse_error|missing_required_field|field_parse_failure|price_mapping_failure",
  "http_success_count": 0,
  "http_failure_count": 5,
  "api_key_used": false,
  "private_endpoint_used": false,
  "live_safe": false
}
```

错误处理规则：

- HTTP timeout：记录 `collector_network_failure`。
- 429 / rate limit：记录 `rate_limited`，不刷接口。
- 非 JSON 响应：记录 `parse_error`。
- 某个 symbol 缺失：该 symbol 记 quarantine，不影响其他 symbol。
- 全部 symbol 缺失：top-level decision = `external_signal_collector_stage1_2_failed`。
- API 字段缺失：写入 `missing_required_field`，不能猜。
- 数值字段解析失败：写入 `field_parse_failure`。

## 15. 网络调用开关

真实 Gate 请求必须显式开启：

```text
python scripts/collect_gate_public_market_snapshot_stage1_2.py --live-public-readonly
```

没有 `--live-public-readonly` 时，只允许：

```text
--mock-response tests/fixtures/...
```

pytest 默认不能联网。CI 默认不能联网。这样可以避免 coding agent 或自动化测试误触外部网络。

## 16. .gitignore 前置检查

implementation plan 的第一个任务必须检查 runtime raw / normalized 路径是否被忽略：

```bash
git check-ignore data/external_signal_shadow/raw/gate_public_market_snapshot_collector/2026-06-12.jsonl
git check-ignore data/external_signal_shadow/normalized/stage1_2_gate_public_events.jsonl
```

如果不通过，先修 `.gitignore`，再采集真实数据。

## 17. 文件与目录

新增代码建议：

```text
src/research/external_signal_shadow/gate_public_collector.py
scripts/collect_gate_public_market_snapshot_stage1_2.py
scripts/review_external_signal_shadow_stage1_2_collector.py
tests/research/external_signal_shadow/test_gate_public_collector.py
```

输出文件：

```text
data/external_signal_shadow/raw/gate_public_market_snapshot_collector/YYYY-MM-DD.jsonl
data/external_signal_shadow/normalized/stage1_2_gate_public_events.jsonl
reports/external_signal_shadow/connectors/stage1_2_gate_public_collector_summary.json
docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md
```

不应放入：

```text
src/strategies/
src/execution/
src/risk/
```

因为 Stage 1.2 是研究数据入口，不是策略，不是风控，不是执行引擎。

## 18. 测试要求

必须先写测试，再写实现。

最小测试：

```text
test_gate_symbol_normalization
test_collector_builds_public_url_only
test_collector_rejects_private_endpoint_path
test_collector_does_not_read_api_key_env
test_collector_builds_readonly_raw_wrappers
test_collector_requires_no_api_key
test_collector_rejects_private_or_executable_fields
test_collector_outputs_unknown_direction_only
test_collector_sets_available_at_as_replay_anchor
test_collector_marks_event_time_available_at_fallback
test_collector_preserves_numeric_raw_strings_and_parse_status
test_collector_tracks_numeric_parse_failures
test_collector_handles_missing_symbol_without_crashing
test_collector_writes_failure_summary_on_network_error
test_collector_summary_splits_collector_and_connector_pass
test_cex_market_snapshot_never_creates_directional_shadow_order
test_stage1_2_summary_sets_directional_replay_ready_false
test_stage1_connector_allows_cex_market_snapshot_as_observation_only
test_collector_summary_passes_with_five_supported_symbols
test_collector_summary_blocks_handoff_when_price_mapping_missing
test_collector_does_not_write_to_execution_or_strategy_modules
test_live_public_readonly_flag_required_for_network_call
```

网络测试默认不进入 pytest。pytest 使用 fixture/mock HTTP response。真实 Gate 请求只能通过脚本手动运行，并在 review 中记录：

```text
network_mode = live_public_readonly
api_key_used = false
private_endpoint_used = false
```

## 19. 完成条件

Stage 1.2 完成后必须有：

- collector 代码；
- fixture/mock 测试；
- real public readonly dry run summary；
- 中文 review；
- `.gitignore` 覆盖 raw runtime data；
- 明确说明结果不可用于 alpha、paper、live；
- 明确说明 `cex_market_snapshot` 是 schedule-generated observation，不是 market signal。

完成后的唯一允许结论：

```text
Gate public read-only collector 是否能稳定生成 Stage 1 raw payload。
```

禁止结论：

```text
Gate 快照有 alpha。
Gate snapshot event count 表示真实信号频率。
Gate signal 可以交易。
可以接 paper/live。
可以生成 directional triple-barrier shadow order。
```

## 20. 推荐下一步

```text
decision = proceed_to_stage1_2_gate_public_read_only_collector_implementation_plan_with_required_fixes
scope = public_rest_snapshot_collector_only
first_source = gate_api_v4_spot_tickers
live_safe = false
exchange_paper_trading_allowed = false
execution_engine_allowed = false
research_shadow_replay_allowed = true
alpha_interpretation_allowed = false
```

Required fixes before implementation plan：

1. Treat `cex_market_snapshot` as observation-only, never directional order.
2. Add `cex_market_snapshot` to Stage 1 connector allowed event types.
3. Use per-symbol `GET /spot/tickers?currency_pair=...` requests, not full-market scan.
4. Use stdlib public REST client only; no SDK, no ccxt, no env/secrets reads.
5. Move REST timeout/retry/user-agent/base-url/pairs into `configs/base.py` with comments.
6. Add `api_response_hash`, endpoint/query/status/latency, and response field names.
7. Preserve numeric raw strings and track parse status/failures.
8. Split `collector_minimal_pass`, `connector_minimal_pass`, and `stage0_observation_handoff_ready`.
9. Mark `schedule_generated=true` and `event_density_alpha_valid=false`.
10. Always write failure summary on network/rate-limit/parse failures.
11. Verify `.gitignore` before writing raw runtime files.
12. Require explicit `--live-public-readonly` flag for real network calls.

Stage 1.2 不继续推进手动 JSONL，也不需要用户找到 Gate 页面。用户只需要运行一个脚本，脚本自己采集公开只读快照。

## 21. 参考来源

- Gate API v4 官方文档：`https://www.gate.com/docs/developers/apiv4/en/`
- Gate API spot public endpoint 文档：`GET /spot/tickers`，见 Gate API SDK 文档：`https://github.com/gateio/gateapi-js/blob/master/docs/SpotApi.md`
