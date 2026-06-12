# External Signal Shadow Lab Stage 1 Connector Design

日期：2026-06-12

## 1. 设计结论

Stage 1 的目标不是接入一个“会交易的外部机器人”，而是建立一条只读、安全、可审计、不会偷看未来的外部信号入口：

```text
外部 skills / 网页 / API 输出
-> raw payload 落盘
-> connector normalize
-> ExternalSignalEvent + available_at_ms
-> price mapping / quarantine
-> Stage 0 Risk Guard / CUSUM / 三重屏障 shadow replay
-> 30 天 shadow evidence
```

本阶段只允许产生研究事件，不允许产生真实订单。

硬边界：

- 不接钱包；
- 不签名；
- 不下单；
- 不 swap；
- 不 copy trade；
- 不读取私钥/API key；
- 不把外部信号直接解释为交易指令；
- 不把 connector 输出直接作为 paper/live 准入；
- 不用 `event_time_ms` 作为回放入场锚点，必须使用 `available_at_ms`。

Stage 1 的核心产物是一组 connector 规范，而不是 alpha 结论。它回答的问题是：

```text
外部来源产生的事件，能否被安全、稳定、去重、可复现、无 look-ahead bias 地接入 shadow lab？
```

不能回答的问题是：

```text
这些外部来源是否真的能赚钱？
```

盈利能力只能由后续 30 天 shadow replay 和 review 决定。

## 2. 为什么 Stage 1 先做 connector，而不是继续写策略

过去几条路线已经给出明确教训：

- funding / basis / liquidation / orderbook 作为裸进攻 alpha 不稳定；
- 纯价格动量、30d momentum、14d CMOM 在当前样本中没有形成可用 alpha；
- C1 更像风控过滤器，不是进攻型收益源；
- 单靠本地价格数据继续调参，容易变成过拟合搜索。

因此下一步不应该立刻再写一个完整策略，而应该先扩大“候选事件来源”。

外部 skills 的价值不在于替我们交易，而在于提供当前数据层缺失的事件雷达：

- smart money inflow / outflow；
- whale / KOL / top trader 行为；
- token audit / honeypot / rug pull 风险；
- meme / new token lifecycle；
- DEX liquidity expansion / contraction；
- CEX market rank / abnormal tape；
- token holder concentration；
- 链上安全与合约风险标签。

Stage 1 要做的是把这些“外部情报”变成结构化事件，然后交给本地 shadow lab 统一验证。

## 3. 本阶段推荐采用的 connector 形态

第一版不直接写多种远程 API connector。推荐使用三层递进：

```text
P0: file-backed skill payload connector
P1: one read-only source-specific connector
P2: multi-source connector registry
```

### 3.1 P0: file-backed skill payload connector

第一优先级是文件型 connector：

```text
data/external_signal_shadow/raw/<source>/<date>/*.jsonl
-> parse
-> normalize
-> ExternalSignalEvent-compatible JSONL
```

含义是：外部 skills、网页抓取、手动导出的 API 响应，先以 JSONL 形式落盘，本项目只读取这些 payload 文件。

优点：

- 不需要在研究代码中保存 API key；
- 不依赖外部插件运行环境；
- 不因为外部接口临时变更导致主流程崩溃；
- 每条原始 payload 都可复现、可审计；
- 出错时能明确区分“外部数据问题”和“本地策略问题”。

这是 Stage 1 最应该先实现的路径。

### 3.2 P1: one read-only source-specific connector

只有 P0 跑通后，才允许选一个真实来源做只读 connector。

推荐优先级：

1. `binance_web3_signal_file_connector`
   适合 market rank、trading signal、token audit、meme rush 等只读 payload。

2. `okx_onchain_signal_file_connector`
   适合 DEX signal、DEX token、DEX trenches、security 等只读 payload。

3. `gate_marketanalysis_file_connector`
   适合 CEX market tape diagnostics，但不再把 funding/basis/liquidation 当作裸 alpha，只作为事件标签或风险状态。

第一版不建议直接做 AI-Trader copytrade connector。原因是复制 AI 操作信号很容易误读成跟单系统，并且其平台成熟度、信号可解释性、可审计性不足。

### 3.3 P2: multi-source connector registry

多来源 registry 放到 Stage 2 之后。Stage 1 不做多源综合打分，也不做“谁收益高就用谁”。

多源同时接入会带来多重比较风险：总能找到某个来源、某个窗口看起来赚钱，但很可能只是噪声。

## 4. Connector 输入与输出契约

### 4.1 Raw payload 输入

每条 raw payload 必须保留完整原始字段，但禁止包含可执行交易字段。

推荐文件格式：

```json
{
  "source": "binance_web3",
  "source_skill": "trading_signal",
  "fetched_at_ms": 1781165880000,
  "raw_payload": {
    "token": "EXAMPLE",
    "chain": "bsc",
    "token_address": "0xabc...",
    "score": 82.5,
    "signal": "smart_money_inflow",
    "event_time_ms": 1781164800000,
    "liquidity_usd": 1200000.0
  }
}
```

connector 读取 raw payload 后必须做四件事：

1. 计算 canonical `raw_payload_hash`，用于审计和复现；
2. 计算 `available_at_ms`，用于回放锚点；
3. 计算 `source_latency_ms = available_at_ms - event_time_ms`；
4. 输出标准化 `ExternalSignalEvent` 兼容 JSONL。

### 4.2 标准输出

Stage 1 connector 只允许输出 Stage 0 已定义 schema 的兼容事件，并新增 connector metadata：

```json
{
  "event_id": "sha256(semantic_dedup_key)[:24]",
  "source": "binance_web3",
  "source_skill": "trading_signal",
  "event_type": "smart_money_inflow",
  "chain": "bsc",
  "symbol": null,
  "token_address": "0xabc...",
  "event_time_ms": 1781164800000,
  "direction_hint": "long",
  "raw_score": 82.5,
  "notional_usd": 0.0,
  "liquidity_usd": 1200000.0,
  "risk_flags": [],
  "data_quality": "ok",
  "shadow_only": true,
  "metadata": {
    "available_at_ms": 1781165880000,
    "source_latency_ms": 1080000,
    "semantic_dedup_key": "binance_web3|trading_signal|bsc|0xabc...|smart_money_inflow|1781164800000|long",
    "raw_payload_hash": "...",
    "connector_version": "stage1_v0",
    "schema_version": "external_signal_event_v1"
  }
}
```

字段规则：

- `shadow_only` 必须为 `true`；
- `event_id` 必须由 `semantic_dedup_key` 生成，不由 raw payload hash 生成；
- `direction_hint` 只能是 `long|short|avoid|unknown|both`；
- 原始 payload 不能直接塞入 `metadata`，只能保存 hash、必要摘要和可审计字段；
- 所有 payload 必须经过 forbidden key policy；
- 无法映射价格数据的 token 必须进入 quarantine，不得进入 shadow order。

## 5. 时间可用性与 look-ahead 防护

这是 Stage 1 的最高优先级规则。

外部来源经常是延迟信号。例如 smart money inflow 实际发生在 10:00，但网页/skill 在 10:18 才抓到。如果 shadow replay 用 10:00 回放，就是偷看未来。

因此标准事件必须区分：

```json
{
  "event_time_ms": 1781164800000,
  "available_at_ms": 1781165880000,
  "source_latency_ms": 1080000
}
```

规则：

```text
Stage 0 replay entry anchor = available_at_ms
event_time_ms 只用于事件归因和延迟统计
available_at_ms < event_time_ms -> reject
source_latency_ms 超过来源阈值 -> quarantine
```

第一版延迟阈值必须配置在 `configs/base.py`，不能写死在 `src/`：

```text
EXTERNAL_SIGNAL_CONNECTOR_MAX_CEX_LATENCY_MS = 15 * 60 * 1000
EXTERNAL_SIGNAL_CONNECTOR_MAX_ONCHAIN_LATENCY_MS = 60 * 60 * 1000
EXTERNAL_SIGNAL_CONNECTOR_MAX_MANUAL_FIXTURE_LATENCY_MS = 24 * 60 * 60 * 1000
```

语义：

- CEX / market rank：最大 15 分钟；
- on-chain / audit / holder：最大 60 分钟；
- manual fixture：最大 24 小时，但必须标记 `data_quality = fixture_or_manual`，且不得用于 alpha 结论。

## 6. 第一版事件类型白名单

Stage 1 不允许无限接收所有外部字段。第一版只接收以下事件类型：

```text
smart_money_inflow
smart_money_outflow
whale_accumulation
whale_distribution
token_audit_pass
token_audit_warning
liquidity_expansion
liquidity_contraction
market_rank_surge
meme_lifecycle_event
cex_market_tape_anomaly
```

映射规则：

- `smart_money_inflow` -> `direction_hint = long`
- `whale_accumulation` -> `direction_hint = long`
- `market_rank_surge` -> `direction_hint = long|unknown`，取决于来源是否有明确方向
- `liquidity_expansion` -> `direction_hint = unknown`，只表示可交易性改善
- `token_audit_pass` -> `direction_hint = unknown`，只表示风险标签改善
- `smart_money_outflow` -> `direction_hint = avoid|short`
- `whale_distribution` -> `direction_hint = avoid|short`
- `token_audit_warning` -> `direction_hint = avoid`
- `liquidity_contraction` -> `direction_hint = avoid`
- `cex_market_tape_anomaly` -> `direction_hint = unknown`

重要边界：

```text
token audit 不是买入信号；
liquidity expansion 不是买入信号；
market rank surge 不是买入信号；
smart money inflow 也不是买入信号，只是候选事件。
```

所有事件都必须经过本地 Risk Guard 和 shadow replay。

## 7. 文件存放位置与目录规范

Stage 1 是研究数据入口，不是策略、执行或风控核心模块。

建议源码目录：

```text
src/research/external_signal_shadow/
  schemas.py
  connector_base.py
  file_backed_connector.py
  price_mapping.py
  safety.py
  connector_summary.py
```

建议脚本：

```text
scripts/run_external_signal_shadow_stage1_connector.py
scripts/review_external_signal_shadow_stage1_connector.py
```

建议 fixture：

```text
tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl
tests/fixtures/external_signal_shadow/stage1_price_map.json
```

建议测试：

```text
tests/research/test_external_signal_shadow_stage1_connector.py
tests/research/test_external_signal_shadow_stage1_price_mapping.py
tests/scripts/test_run_external_signal_shadow_stage1_connector.py
```

建议运行数据目录：

```text
data/external_signal_shadow/raw/
data/external_signal_shadow/normalized/
reports/external_signal_shadow/connectors/
```

不要触碰：

```text
src/strategies/
src/execution/
src/risk/
```

除非后续已有明确 implementation plan 且通过 shadow evidence 证明需要接入。Stage 1 不产生策略，不产生订单，不进入 execution。

`.gitignore` 应确保：

```text
data/external_signal_shadow/raw/
data/external_signal_shadow/normalized/
```

不进入版本库。

允许提交的是：

```text
tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl
tests/fixtures/external_signal_shadow/stage1_price_map.json
reports/external_signal_shadow/connectors/stage1_connector_fixture_summary.json
```

真实外部原始数据不应提交。

## 8. 去重、幂等与 hash 规则

每个 connector run 必须幂等。

必须拆分两个概念：

```text
semantic_dedup_key: 判断是否是同一个语义事件
raw_payload_hash: 审计和复现，不用于语义去重
```

### 8.1 semantic_dedup_key

第一版定义：

```text
source
+ source_skill
+ chain
+ canonical_asset_id
+ event_type
+ event_time_bucket
+ direction_hint
```

其中：

```text
canonical_asset_id = cex:<SYMBOL> 或 <chain>:<token_address>
event_time_bucket = floor(event_time_ms / 5min)
```

`event_id` 由 semantic key 生成：

```text
event_id = sha256(semantic_dedup_key)[:24]
```

不允许把 `raw_payload_hash` 放进 semantic key。原因是外部网页字段经常变化，比如新增 rank、url、label、description；如果 hash 参与去重，同一事件会被重复计数。

### 8.2 raw_payload_hash

canonical hash 规则必须固定：

```python
json.dumps(
    raw_payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
)
```

然后 `sha256`。

注意：hash 对象是 `raw_payload` 本身，不包含 `fetched_at_ms`，否则同一 payload 每次抓取都会变成新 hash。

## 9. Forbidden key policy

Stage 1 必须防止任何可执行交易 payload 混入研究数据，但不能粗暴禁止所有包含 `tx`、`swap`、`order` 的字段，否则会误杀合法分析字段。

### 9.1 Hard reject exact keys

以下 exact keys 必须 hard reject：

```text
private_key
seed
mnemonic
signature
signed_tx
raw_tx
api_key
secret
password
passphrase
order_request
swap_request
transfer_request
wallet_seed
wallet_private_key
tx_payload
```

### 9.2 Hard reject path patterns

以下路径模式必须 hard reject：

```text
wallet.private_key
wallet.seed
transaction.signed_payload
transaction.raw_tx
order.intent
order.request
swap.calldata
swap.request
transfer.request
```

### 9.3 Allowed analytics keys

以下 analytics 字段允许存在：

```text
tx_count
tx_hash
swap_count_24h
orderbook_imbalance
orderbook_depth_usd
```

边界：

```text
允许描述历史链上交易或盘口统计；
禁止携带可执行交易请求、签名、calldata、订单意图。
```

## 10. Price mapping 策略

CEX symbol 事件：

```text
BTC/USDT -> BTCUSDT
ETH-USDT -> ETHUSDT
```

链上 token 事件：

```text
token_address + chain -> price_series_id
```

第一版不直接接 DEX 实时价格。建议采用显式 mapping artifact：

```text
configs/external_signal_shadow_price_map.json
```

格式：

```json
{
  "bsc:0xabc...": {
    "price_series_id": "EXAMPLEUSDT",
    "venue": "binance",
    "timeframe": "5m",
    "mapping_type": "cex_symbol_proxy",
    "active": true
  },
  "cex:BTCUSDT": {
    "price_series_id": "BTCUSDT",
    "venue": "binance",
    "timeframe": "5m",
    "mapping_type": "direct_cex_symbol",
    "active": true
  }
}
```

没有 mapping：

```text
quarantine_reason = price_mapping_unavailable
不得进入 Stage 0 replay
```

这样做会漏掉很多早期 meme 机会，但能避免 Stage 1 因 DEX 价格、池子切换、税费、滑点和 MEV 复杂性而失控。

Stage 1 的目标是安全接入，不是抢跑链上新币。

## 11. Quarantine 与 Reject 规则

以下情况必须进入 quarantine 或 reject，不能进入 shadow replay：

- 缺少 `event_time_ms`；
- 缺少 `available_at_ms`；
- `available_at_ms < event_time_ms`；
- `source_latency_ms` 超过对应来源阈值；
- 缺少 `chain`；
- 既没有 `symbol` 也没有 `token_address`；
- `direction_hint` 无法映射；
- `event_type` 不在白名单；
- 缺少价格映射；
- payload 中出现 hard reject exact keys；
- payload 中出现 hard reject path patterns；
- 数据质量无法判断。

分类规则：

```text
reject = 安全不允许或语义非法，例如 forbidden key、available_at_ms < event_time_ms。
quarantine = 数据不完整、价格映射缺失、延迟过大、需要人工检查。
```

这两个概念不能混淆。

## 12. Summary 统计守恒关系

summary 必须可审计，不能双重计数。

守恒关系：

```text
raw_payload_count
= emitted_event_count
+ deduped_payload_count
+ quarantined_payload_count
+ rejected_payload_count
```

`unsupported_event_type_count`、`forbidden_payload_count` 等只能作为 reason breakdown，不应作为独立总数参与守恒。

summary 必须输出：

```json
{
  "run_id": "20260612T000000Z_binance_web3_stage1_v0",
  "source": "binance_web3",
  "connector_version": "stage1_v0",
  "schema_version": "external_signal_event_v1",
  "input_files": [],
  "output_file": "data/external_signal_shadow/normalized/stage1_events.jsonl",
  "output_file_sha256": "...",
  "raw_payload_count": 0,
  "emitted_event_count": 0,
  "deduped_payload_count": 0,
  "quarantined_payload_count": 0,
  "rejected_payload_count": 0,
  "reject_reason_counts": {},
  "quarantine_reason_counts": {},
  "event_type_counts": {},
  "direction_hint_counts": {},
  "price_mapping_counts": {},
  "latency_p50_ms": 0,
  "latency_p95_ms": 0,
  "summary_accounting_ok": true,
  "live_trading_enabled": false,
  "exchange_paper_trading_allowed": false,
  "execution_engine_allowed": false,
  "research_shadow_replay_allowed": true,
  "wallet_required": false
}
```

## 13. 与 Stage 0 的衔接

Stage 1 的 normalized events 应该能直接被 Stage 0 runner 使用，但回放锚点必须是 `available_at_ms`。

第一版实现可以有两种方式：

1. 在 Stage 1 输出给 Stage 0 的事件中，将 `event_time_ms_for_replay = available_at_ms`；
2. 或者在 Stage 0 runner 中显式支持 `metadata.available_at_ms` 作为 replay anchor。

推荐第一版采用更少侵入的方式：

```text
connector 输出 normalized event 时：
- 原始事件时间保留在 metadata.original_event_time_ms；
- Stage 0 兼容字段 event_time_ms 设置为 available_at_ms；
- metadata.available_at_ms 同步保留；
- metadata.source_latency_ms 保留。
```

这样可以不改 Stage 0 现有模型，同时避免回放偷看未来。

示例：

```bash
PYTHONPATH=src uv run python scripts/run_external_signal_shadow_stage0.py \
  --events data/external_signal_shadow/normalized/stage1_events.jsonl \
  --price-bars data/external_signal_shadow/price_bars/stage1_price_bars.jsonl \
  --output reports/external_signal_shadow/stage1_shadow_replay_summary.json
```

Stage 1 不负责证明 alpha。它只负责保证：

```text
external raw payload -> normalized event -> Stage 0 replay
```

这条链路可跑通、可审计、可复现，且不发生 look-ahead bias。

## 14. 风控与安全边界

Stage 1 connector 必须继承 Stage 0 的 L0 安全规则。

字段命名必须避免和研究 shadow replay 混淆：

```text
live_trading_enabled = false
exchange_paper_trading_allowed = false
execution_engine_allowed = false
research_shadow_replay_allowed = true
wallet_required = false
external_api_enabled = connector_specific，但只读
```

语义：

- 允许：本地 research shadow order record；
- 禁止：交易所 paper account；
- 禁止：模拟撮合实盘账户；
- 禁止：execution engine intent；
- 禁止：真实订单。

如果未来实现 direct HTTP connector，必须额外满足：

- 只读接口；
- 不接受交易 API key；
- 不读取环境变量中的交易密钥；
- 不支持 POST / order / swap / transfer；
- 超时失败时安全退出；
- rate limit 不重试到阻塞主流程；
- raw payload 全部落盘；
- 连接失败输出 `connector_data_unavailable`，不输出空成功。

## 15. Fixture 必须覆盖的失败路径

Stage 1.0 不访问互联网，只跑 fixture。fixture 不应只有 happy path，必须覆盖：

1. 正常 `smart_money_inflow` -> emitted；
2. 正常 `token_audit_pass` -> emitted，`direction_hint = unknown`；
3. 语义重复 payload -> deduped；
4. unsupported `event_type` -> rejected；
5. nested `private_key` -> forbidden rejected；
6. missing `chain` -> quarantine；
7. missing `symbol/token_address` -> quarantine；
8. price mapping unavailable -> quarantine；
9. stale `available_at_ms/event_time_ms` latency -> quarantine；
10. `available_at_ms < event_time_ms` -> rejected；
11. raw payload 被错误塞入 metadata -> rejected or schema failure。

最低测试断言：

```text
test_connector_rejects_forbidden_nested_keys
test_connector_dedupes_semantic_duplicate
test_connector_quarantines_missing_price_mapping
test_connector_uses_available_at_for_replay_handoff
test_summary_accounting_is_conservative
test_normalized_events_are_stage0_compatible
```

## 16. Stage 1 通过标准

Stage 1 通过不是收益为正，而是基础设施可用。

通过条件：

```text
raw_payload_count > 0
emitted_event_count > 0
summary_accounting_ok = true
forbidden payload 被 hard reject
quarantine/reject 规则可解释
事件可直接进入 Stage 0 replay
replay handoff 使用 available_at_ms，不使用原始 event_time_ms 偷看未来
summary 包含 source、connector_version、run_id、payload hash、dedup stats、latency stats
live_trading_enabled = false
exchange_paper_trading_allowed = false
execution_engine_allowed = false
research_shadow_replay_allowed = true
wallet_required = false
```

失败类型：

```text
data_failure: 没有 raw payload 或 payload 无法读取
schema_failure: payload 无法映射成 ExternalSignalEvent
safety_failure: 可执行字段没有被拒绝
latency_failure: available_at_ms 语义缺失或延迟口径错误
mapping_failure: symbol/token 无法映射且未 quarantine
summary_accounting_failure: 守恒关系不成立
replay_handoff_failure: normalized events 无法进入 Stage 0
connector_completed: connector 基础设施通过
```

## 17. Stage 1 不允许推出的结论

即使 connector 跑通，也不能推出：

- 外部 skills 有 alpha；
- smart money 信号有效；
- token audit pass 可以买入；
- CUSUM confirmation 可以交易；
- 三重屏障结果可以上线；
- 可以开启 exchange paper/live；
- 可以做 copy trade。

Stage 1 的唯一结论是：

```text
这个外部来源是否能安全、稳定、可审计、无 look-ahead bias 地成为 shadow lab 的事件输入。
```

## 18. 推荐实施顺序

### Stage 1.0: connector fixture implementation

实现文件型 fixture connector：

```text
tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl
tests/fixtures/external_signal_shadow/stage1_price_map.json
-> scripts/run_external_signal_shadow_stage1_connector.py
-> data/external_signal_shadow/normalized/stage1_events.jsonl
-> reports/external_signal_shadow/connectors/stage1_connector_summary.json
```

这一步只用 fixture，不访问互联网。

### Stage 1.1: first real source dry-run

从一个外部来源手动导出 payload，放入 raw 目录，用同一个 connector parser 跑。

推荐优先选择：

```text
Binance / OKX / Gate 中最容易拿到、最稳定、字段最清楚的只读 payload。
```

不是选“看起来最赚钱”的来源，而是选“最容易审计”的来源。

### Stage 1.2: 30 天 shadow collection

每天固定时间运行 connector，生成 normalized events，进入 Stage 0 replay。

30 天后只看 shadow evidence：

- 事件数量是否足够；
- source latency 是否可接受；
- Risk Guard reject 是否合理；
- CUSUM 是否减少噪声；
- 三重屏障结果是否有结构；
- 是否依赖单一 token、单一天、单一热点；
- 成本后是否仍有空间。

## 19. 后续决策树

```text
Stage 1 connector fixture 失败
-> 修 schema / safety / mapping / latency，不进入外部数据。

Stage 1 connector fixture 通过，但真实 source payload 不稳定
-> 保留 fixture 能力，暂停该来源。

真实 source 30 天 shadow 无结构
-> 停止该来源，不调参硬救。

真实 source 30 天 shadow 有结构，但样本少
-> 延长 shadow，不进入策略。

真实 source 30 天 shadow 有结构，且通过风险/成本/集中度检查
-> 写 Stage 2 source-specific shadow evaluation design。
```

## 20. Required Fixes Before Implementation

实施前必须确认 implementation plan 覆盖以下事项：

1. 增加 `available_at_ms` 与 `source_latency_ms`；Stage 0 replay 必须锚定 `available_at_ms`。
2. 将 `paper_shadow_allowed` 拆成 `exchange_paper_trading_allowed`、`execution_engine_allowed`、`research_shadow_replay_allowed`，避免和研究 shadow order 混淆。
3. 拆分 `semantic_dedup_key` 与 `raw_payload_hash`。
4. 固定 canonical JSON hash 规则。
5. 定义 forbidden exact keys、forbidden path patterns 与 analytics allowlist。
6. 新增显式 price mapping artifact：`configs/external_signal_shadow_price_map.json`。
7. 定义 summary 统计守恒关系与 reason breakdown。
8. fixture 覆盖 reject / quarantine / dedup / staleness / available_at 失败路径。
9. 代码放在 `src/research/external_signal_shadow/`，不要放入 `src/strategies/`、`src/execution/`、`src/risk/`。

## 21. 当前推荐决策

```text
decision = proceed_to_stage1_connector_implementation_plan_with_required_fixes
first_connector = file_backed_skill_payload_connector
direct_http_connector = explicitly_out_of_scope_for_stage1_0
real_source_priority = choose_after_fixture_connector_passes
live_safe = false
exchange_paper_trading_allowed = false
execution_engine_allowed = false
research_shadow_replay_allowed = true
wallet_required = false
```

一句话：Stage 1 先做“外部信号入口的安全适配器”，不是做“外部信号交易策略”。补齐 `available_at_ms`、稳定去重、price mapping、summary 守恒和失败 fixture 后，再进入 implementation plan。
