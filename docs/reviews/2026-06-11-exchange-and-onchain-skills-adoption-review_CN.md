# 交易所与链上 Skills 采纳评估报告

日期：2026-06-11

## 1. 核心结论

我们应该采纳 skills 体系，但不应该把外部 skills 直接接入交易执行。

正确采纳方式是：

```text
只读数据能力 + 研究工作流模板 + 风控标签体系 + shadow replay
```

禁止采纳方式是：

```text
钱包登录 + 签名 + swap + 下单 + 转账 + 跟单执行
```

经过 Gate、Binance、OKX、BofAI、AI-Trader 等项目调研后，最有价值的不是“让 AI 自动交易”，而是把这些 skills 作为外部情报雷达，补足我们当前项目最缺的非价格信息：

- 链上 token 风险；
- smart money / whale / KOL 行为；
- holder concentration；
- liquidity / slippage / orderbook 风险；
- funding / basis / liquidation 市场结构；
- meme/new token lifecycle；
- token audit / honeypot / rug pull 检测。

当前项目已经证明纯价格动量路线弱，继续只围绕 `close price` 做进攻型 alpha，边际价值不高。下一阶段更值得做的是：

```text
CEX market tape diagnostics + on-chain intelligence layer
```

它们不直接产生交易信号，但可以产生更高质量的候选池、风险过滤器和 shadow-mode 事件标签。

## 2. 当前项目模式的问题

我们当前的研究模式主要是：

```text
本地历史数据 -> 因子定义 -> 回测 -> review
```

这个模式优点是严谨、可复现、不会轻易接 live。但它的问题也明显：

1. 数据维度偏窄。
   主要依赖 CEX kline、funding、liquidation、orderbook。对链上 wallet、holder、token safety、social hype、DEX liquidity 等信息覆盖不足。

2. 价格因子容易滞后。
   Factor Lab Stage A1/A2.2 已经说明，单纯 30d momentum 或 14d CMOM 在当前 Binance spot alt universe 上没有形成可用 alpha。

3. 风控标签不够丰富。
   我们可以判断回测收益、回撤、成本，但缺少“这个 token 是否是貔貅盘、是否 holder 高度集中、是否 smart money 已经退出、是否流动性虚胖”等链上风险标签。

4. 外部情报未结构化。
   如果靠人工看网站、新闻、榜单，很难进入可测试流程。skills 的价值在于把这些情报变成可调用、可落盘、可审计的结构化数据。

## 3. 各项目的采纳价值判断

### 3.1 Gate Skills

代表仓库：`https://github.com/gate/gate-skills`

Gate 的 `gate-exchange-marketanalysis` 是目前最适合我们直接借鉴的模板。

它覆盖的方向与我们项目高度重合：

- liquidity；
- momentum；
- liquidation；
- funding arbitrage；
- basis；
- manipulation risk；
- orderbook / slippage；
- kline breakout；
- weekend liquidity。

判断：

```text
高优先级采纳，但采纳的是研究框架，不是 Gate 专用实现。
```

建议：

不要把项目迁到 Gate，也不要依赖 Gate-only API。应该把它抽象成我们自己的：

```text
CEX Market Tape Diagnostics
```

并优先用 Binance / OKX / Bybit 可获得数据实现。

可转化模块：

- liquidity diagnostics；
- slippage simulation；
- funding/basis diagnostics；
- liquidation anomaly diagnostics；
- manipulation-risk checklist；
- weekend vs weekday liquidity analysis。

### 3.2 Binance Skills Hub

代表仓库：`https://github.com/binance/binance-skills-hub`

值得采纳的 read-only skills：

- `crypto-market-rank`
- `trading-signal`
- `query-token-audit`
- `query-token-info`
- `query-address-info`
- `meme-rush`

不建议采纳的执行类 skills：

- `binance` 主交易 skill；
- wallet；
- payment；
- p2p；
- onchain-pay；
- convert / margin / futures 下单能力。

判断：

```text
适合作为 Web3 情报源，不适合作为交易执行层。
```

最有价值能力：

1. `query-token-audit`
   用于 token safety veto：honeypot、rug pull、异常税、恶意合约。

2. `crypto-market-rank`
   用于外部热度和 smart money inflow 排名。

3. `trading-signal`
   用于 smart money event label，但只能 shadow，不允许 copy trade。

4. `meme-rush`
   用于 meme/new launch lifecycle 观察，不建议直接做抢跑策略。

### 3.3 OKX OnchainOS Skills

代表仓库：`https://github.com/okx/onchainos-skills`

值得采纳的 read-only skills：

- `okx-dex-market`
- `okx-dex-token`
- `okx-dex-signal`
- `okx-dex-trenches`
- `okx-security`
- `okx-dex-ws` 的只读数据思想

不建议采纳的执行类 skills：

- `okx-dex-swap`
- `okx-dex-strategy`
- `okx-agentic-wallet`
- `okx-onchain-gateway`
- `okx-defi-invest`
- `okx-x402-payment`

判断：

```text
非常适合做链上 intelligence layer，但必须剥离执行能力。
```

最有价值能力：

1. `okx-dex-token`
   token price、liquidity、holder、top trader、cluster analysis。

2. `okx-dex-signal`
   smart money / whale / KOL 行为追踪。

3. `okx-dex-trenches`
   meme launchpad、dev reputation、bundle/sniper detection、同车钱包。

4. `okx-security`
   token / DApp / transaction / approval 风险检查。

这些能力如果结构化落地，能补足我们当前没有的“链上真实性”和“风险状态”数据。

### 3.4 BofAI Skills

代表仓库：`https://github.com/BofAI/skills`

值得参考的方向：

- `tronscan-skill`
- `trc20-toolkit-skill`
- `multisig-permissions`
- `sunswap`
- `sunperp-skill`
- `usdd-skill`

判断：

```text
不作为主线 alpha，但适合作为 TRON 生态链研究和权限安全设计参考。
```

最值得借鉴的是 `multisig-permissions` 的思想：

```text
提案 -> 审查 -> 明确授权 -> 执行
```

这对我们未来如果引入任何半自动交易或风控动作，都很重要。

### 3.5 AI-Trader

代表仓库：`https://github.com/HKUDS/AI-Trader`

判断：

```text
暂不采纳。
```

原因：

- 平台成熟度和接口稳定性不足；
- signals/operations 语义不够稳定；
- leaderboard 容易有幸存者偏差；
- 不适合直接接 copytrade；
- 更适合作为外部观察样本，而不是系统依赖。

如果未来重新评估，只能以 `read-only shadow source` 形式接入。

## 4. 应该采纳哪些 Skills 能力

### 第一优先级：CEX Market Tape Diagnostics

来源参考：

- Gate `gate-exchange-marketanalysis`
- Binance CEX public market data
- OKX / Bybit public market data

目标：

不是直接找信号，而是判断市场结构是否适合交易。

应包含指标：

- spread；
- depth；
- slippage；
- quote volume；
- orderbook imbalance；
- funding rate；
- basis；
- liquidation anomaly；
- weekend liquidity；
- manipulation-risk flags。

适合当前项目的原因：

我们之前失败的策略，多次暴露出同一个问题：信号本身可能没有错，但执行环境、beta regime、流动性和拥挤状态没有被识别。CEX market tape diagnostics 正好补这个洞。

### 第二优先级：Token Safety / Risk Guard

来源参考：

- Binance `query-token-audit`
- OKX `okx-security`
- OKX `okx-dex-token`

目标：

在研究链上 token 或 meme 前，先把明显不能碰的标的排除。

应包含 veto：

- honeypot；
- rug pull risk；
- abnormal buy/sell tax；
- holder concentration；
- dev wallet concentration；
- suspicious bundler/sniper cluster；
- liquidity too thin；
- fake volume；
- contract mutable / ownership risk。

适合当前项目的原因：

进攻型 alpha 如果进入链上/meme，最大风险不是“信号弱”，而是买到不能卖、流动性消失、dev rug、假池子。这层必须先做。

### 第三优先级：Smart Money / Whale / KOL Shadow Signals

来源参考：

- Binance `trading-signal`
- Binance `crypto-market-rank`
- OKX `okx-dex-signal`
- OKX `okx-dex-token` top trader / holder cluster

目标：

把外部 smart money 行为变成事件标签，做 30 天 shadow replay。

不要直接使用为交易信号。

应输出：

```json
{
  "source": "binance_web3|okx_onchainos",
  "event_type": "smart_money_buy|smart_money_sell|whale_inflow|kol_signal",
  "chain": "solana|bsc|base|ethereum",
  "token_address": "...",
  "event_time": "...",
  "event_notional_usd": 0.0,
  "wallet_count": 0,
  "current_exit_rate": 0.0,
  "risk_flags": [],
  "shadow_only": true
}
```

验证问题：

- 信号出现后 5m/30m/4h/24h 价格是否继续；
- smart money 是否已经退出；
- 信号是否只是追高；
- 是否集中在低流动性 token；
- 是否经常触发安全 veto。

### 第四优先级：Meme / New Token Discovery

来源参考：

- Binance `meme-rush`
- OKX `okx-dex-trenches`

目标：

只做观测与风险研究，不做自动买入。

适合问题：

- 新 token 迁移到 DEX 后是否有可重复结构；
- dev reputation 是否能过滤 rug；
- bundle/sniper concentration 是否能预测失败；
- social hype + liquidity growth 是否能形成候选池。

当前不建议做交易策略，因为执行难度和诈骗风险都高。

## 5. 不应该采纳哪些 Skills 能力

现阶段禁止接入：

- wallet login；
- private key / signing；
- transaction broadcast；
- swap；
- CEX order placement；
- DEX strategy order；
- payment；
- earn / staking / lending 自动操作；
- copytrade；
- auto-rebalance。

原因：

1. 我们还没有经过 shadow-mode 证明这些外部信号有边际收益。
2. 链上 token 风险远高于 CEX 大币。
3. 外部 CLI 输出属于不可信输入，存在 prompt injection 和数据污染风险。
4. 一旦接入钱包或 API key，工程错误会变成资金损失。

## 6. 采用 Skills 后相比当前模式的好处

### 6.1 从单一价格因子扩展到多维情报

当前模式：

```text
price / volume / funding / liquidation / orderbook
```

引入只读 skills 后：

```text
price + liquidity + funding + liquidation + holder + wallet flow + token safety + social hype + smart money + DEX pool
```

这能帮助我们跳出“价格涨了所以买”的弱因子框架。

### 6.2 形成候选池，而不是盲目全市场扫描

skills 可以帮助先筛出：

- 热度上升 token；
- smart money 聚集 token；
- liquidity 扩张 token；
- safety audit 通过 token；
- holder concentration 不极端 token。

再进入本地回测/事件研究。

这比直接从 Binance 当前可交易 universe 做横截面排序更接近实盘信息流。

### 6.3 更容易建立 Risk Guard

Token safety、holder concentration、slippage、liquidity pool、dev reputation 这些标签，可以直接变成风控 veto。

示例：

```text
if honeypot_risk == true:
    reject
if sell_tax > 5%:
    reject
if top10_holder_share > 35%:
    reject
if liquidity_usd < 500_000:
    reject
if smart_money_exit_rate > 70%:
    reject
```

这类规则不一定赚钱，但能显著减少“死法”。

### 6.4 更适合 shadow-mode 验证

外部 skills 天然是事件流：

- 某钱包买入；
- 某 token 进入榜单；
- 某 token 通过/未通过安全审计；
- 某 meme 从 bonding curve 迁移；
- 某 token smart money inflow 异常。

这些都可以落盘后做事件研究：

```text
event time -> post 5m/30m/4h/24h return/risk/liquidity
```

比直接把它们当交易信号安全得多。

## 7. 推荐的后续行动路线

### Step 0：冻结原则

先写入项目规则：

```text
External skills are read-only research inputs by default.
No wallet, no signing, no order, no swap, no transfer.
All external signals must pass local Risk Guard and 30d shadow replay before any live consideration.
```

### Step 1：写一份 CEX Market Tape Diagnostics Design

优先级最高。

目标：

参考 Gate `gate-exchange-marketanalysis`，用 Binance/OKX/Bybit 数据做我们自己的市场结构诊断。

第一版只做：

- spread；
- depth；
- slippage；
- funding；
- basis；
- liquidation anomaly；
- volume shock；
- weekend liquidity。

输出不是交易信号，而是市场状态标签：

```text
tradable
risky_liquidity
funding_crowded
basis_dislocated
liquidation_stress
manipulation_risk
```

### Step 2：写一份 Onchain Skills Read-Only Evaluation Design

目标：

评估 Binance/OKX/BofAI 的只读链上能力是否能稳定返回数据，字段是否可复现，成本/限额是否可接受。

第一版只测：

- token search；
- token dynamic / liquidity；
- token audit；
- smart money signal；
- holder concentration；
- hot token list。

不测 swap，不测 wallet。

### Step 3：统一外部信号 schema

所有外部 skills 输出都要变成统一格式：

```json
{
  "source": "gate|binance_web3|okx_onchainos|bofai",
  "source_skill": "...",
  "event_type": "...",
  "chain": "...",
  "symbol": "...",
  "token_address": "...",
  "event_time_utc": "...",
  "raw_score": 0.0,
  "notional_usd": 0.0,
  "liquidity_usd": 0.0,
  "risk_flags": [],
  "data_quality": "ok|degraded|unavailable",
  "shadow_only": true
}
```

### Step 4：做 30 天 shadow replay

每个外部事件都评估：

- post 5m return；
- post 30m return；
- post 4h return；
- post 24h return；
- max adverse excursion；
- liquidity change；
- spread/slippage proxy；
- 是否触发 token safety veto；
- 是否晚于行情。

通过标准不能只看收益，必须看：

- 样本数；
- 不同日期稳定性；
- 不同链稳定性；
- 不同 token 类型稳定性；
- 失败样本的死法。

### Step 5：再决定是否进入策略化

只有满足以下条件，才允许从“情报雷达”升级为“策略候选”：

- 样本数足够；
- 30 天 shadow 有正向结构；
- 风控 veto 能明显减少尾部亏损；
- 成本/滑点后仍有空间；
- 不依赖单一 token、单一天、单一热点；
- 不需要钱包/抢跑/超低延迟执行。

## 8. 建议优先级排序

| 优先级 | 方向 | 采用对象 | 当前动作 |
|---|---|---|---|
| P0 | CEX Market Tape Diagnostics | Gate marketanalysis 思路 | 立即写 design |
| P1 | Token Safety Risk Guard | Binance audit / OKX security | 写 read-only evaluation |
| P1 | Smart Money Shadow Signals | Binance trading-signal / OKX dex-signal | 只做 shadow |
| P2 | On-chain Token Intelligence | OKX dex-token / Binance token-info | 做数据可用性审计 |
| P2 | Meme/New Token Discovery | Binance meme-rush / OKX trenches | 只做观察，不交易 |
| P3 | TRON Ecosystem Research | BofAI tronscan / sunswap / sunperp | 可选小实验 |
| 禁止 | Wallet / Swap / Orders | Binance/OKX/Gate 执行类 skills | 不接入 |

## 9. 最终建议

采纳 skills，但只采纳“研究与风控能力”。

下一步不要再继续纯价格动量路线，也不要急着做链上交易机器人。最稳的推进路径是：

```text
P0: CEX Market Tape Diagnostics
P1: Onchain Token Safety + Smart Money Shadow Signals
P2: 30d Shadow Replay
P3: 决定是否形成新的进攻型 alpha 研究线
```

一句话总结：

```text
skills 不是我们的交易员，而是我们的雷达、审计员和风控观察员。
先让它们帮我们看见更多信息，再决定有没有值得交易的结构。
```

## 10. 参考来源

- Gate Skills: https://github.com/gate/gate-skills
- Binance Skills Hub: https://github.com/binance/binance-skills-hub
- Binance Academy: How to Use Binance Skills MCP Server: https://academy.binance.com/en/articles/how-to-use-binance-skills-mcp-server
- OKX OnchainOS Skills: https://github.com/okx/onchainos-skills
- OKX OnchainOS Docs: https://web3.okx.com/build/docs/waas/ai-agent-skill
- BofAI Skills: https://github.com/BofAI/skills
- AI-Trader: https://github.com/HKUDS/AI-Trader
