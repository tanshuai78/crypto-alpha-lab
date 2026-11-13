# D2 历史同行元数据预审：固定顺序第 6–10 个 Parent

日期：2026-11-12（Asia/Shanghai）。性质：人工资料盘点及资源决策参考；不是正式同行 Universe、机器输入、完整历史市场准入、收益研究或 Alpha 证据。

## 1. 决策摘要

**本批找到更多有来源支持的业务关系，但尚未证明可以稳定、无偏地批量构造同行样本。建议保留 D2，暂不启动行情分析程序，也不自动滚动扩查下一批。**

| 本批事实 | 结果及解释边界 |
| --- | --- |
| 固定事件 | 原 42 个 standard Parent 排序的第 6–10 项，共五个 Parent / 五个 child；没有补第 11 项 |
| 公告时间核对 | 5/5 当前官方详情的发布时间与旧目录毫秒值一致；不是首次传播或历史未修改证明 |
| 有业务及资产线索的事件 | IRYS、RLS、NIGHT 三项合计六个资产线索；不等于三个已通过完整同行选样门禁的事件 |
| 事件前明确的目标市场身份 | AR、AVAX、CC 三个 USDT 永续有明确官方历史依据，关联 IRYS、RLS 两个 Parent；没有核验逐分钟可交易性 |
| 市场身份缺口 | FIL 有旧 USDT 期货资料，但本批未精确锁定永续类别；ALEO 的 Binance 历史身份未核实；已识别 AZTEC 合约在 NIGHT 事件后上线 |
| 归档对象检查 | 33 个去重对象：33 次 ZIP HEAD + 33 次 CHECKSUM GET，均 HTTP 200、curl RC=0；校验文本格式及文件名均通过 |
| 未完成的证据 | 部分分支未严格执行预设发现次数或留存完整初池；不能宣称机械同行复现通过。逐 Parent 主动人工耗时也未被独立完整计量 |
| 没有检验 | 价格响应、相关性、成本、公告后可执行空间、净收益和 Alpha 均未计算 |

因此，“对象能找到”仍不是主要瓶颈。较突出的新增限制是：**业务同行未必对应目标市场中的可交易代币；有代币也未必已有对应永续；人工候选发现仍有自由裁量及取证成本。**本批不能用于估计全年合格率、年化独立机会数或策略成败。

## 2. 授权、输入和先锁事件

用户授权“下一步”，随后要求“继续”。执行[上轮复核 §7](2026-11-12-d2-apro-bob-peer-rule-reproducibility-check_CN.md)建议的下一批最多五个 Parent 元数据检查，沿用[原 Brief Plan](2026-11-12-launch-event-data-research-directions-discussion_CN.md)和[首批预审](2026-11-12-launch-peer-spillover-metadata-preflight_CN.md)的权限边界：只读分类/公告元数据、公开资料、归档 HEAD 与校验文本，单份人工报告。不运行旧 loader、研究或交易程序。

读取解析前核对以下字节 SHA-256；三者均匹配。只用账本分类及 J-A 的公告目录元数据，不读取 raw 树、J-B、旧研究明细或行情数值。

| 输入 | SHA-256 |
| --- | --- |
| `data/exports/stage1_5j_token_launch_classification_ledger_v2.csv` | `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b` |
| 原 J-A 根 `summary.json` | `722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b` |
| 同根 `manifest.json` | `b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf` |

J-A 根为 `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z`。核对 manifest 中 summary 的路径、字节数及哈希绑定；**不是整个 sealed tree 或 Rule 17 profile 的重新准入通过**。

账本仍为 12 列 / 281 行；`crypto / standard / confirmed` 为 53 child / 42 Parent。42 个 Parent 均唯一关联原目录。按原 `release_date_ms`、Parent ID 排序，前五项与首批锁定名单一致，随后锁定第 6–10 项，再进行新联网调查。

| 原顺序 / Parent 官方链接 | child / 项目 | 原发布时间 UTC / Unix ms | 当前正文计划上线 S，UTC |
| --- | --- | --- | --- |
| 6 / [302095391f0f43c0a6d206b3a10c4e78](https://www.binance.com/en/support/announcement/detail/302095391f0f43c0a6d206b3a10c4e78) | IRYSUSDT / Irys | 2025-11-26 14:43:56.086 / `1764168236086` | 2025-11-26 16:00 |
| 7 / [76379c0d6b7f4fc4861a734db668803a](https://www.binance.com/en/support/announcement/detail/76379c0d6b7f4fc4861a734db668803a) | RLSUSDT / Rayls | 2025-12-02 08:43:20.303 / `1764665000303` | 2025-12-02 10:00 |
| 8 / [97c003f1e70f497e98f606ae8b3f1822](https://www.binance.com/en/support/announcement/detail/97c003f1e70f497e98f606ae8b3f1822) | POWERUSDT / Power Protocol | 2025-12-06 07:40:14.266 / `1765006814266` | 2025-12-06 09:00 |
| 9 / [070db7effe984b69bd4bf2240cee4487](https://www.binance.com/en/support/announcement/detail/070db7effe984b69bd4bf2240cee4487) | WETUSDT / HumidiFi | 2025-12-10 05:45:14.302 / `1765345514302` | 2025-12-10 07:00 |
| 10 / [675d519f99d34af29b4225a70a7995fa](https://www.binance.com/en/support/announcement/detail/675d519f99d34af29b4225a70a7995fa) | NIGHTUSDT / Midnight | 2025-12-10 09:44:29.769 / `1765359869769` | 2025-12-10 11:00 |

五次官方详情 JSON 请求在 `2026-11-12T07:16:28Z–07:16:34Z` 发出，均 HTTP 200、curl RC=0、API `code=000000`；`publishDate` 均匹配原值。S 不是实际首笔成交 T0。

**具体版本风险：**五份响应的 `lastUpdateTime` 均为 0，但 WET 正文明确说明曾于 2025-12-10 将最高杠杆由 20x 改为 50x。这是“字段为零不能证明正文从未修改”的实际例子。没有据此断言发布时间也被修改；本轮没有验证原始推送、历史接收延迟及更早披露。

## 3. 核心服务、同行线索和代币角色

先以目标的事件前材料写清服务/客户，再找具名关系；不把同链、泛 RWA、GameFi 或隐私标签本身当同行证据。架构不同不自动排除；代币角色单列，不暗增“只收治理币”规则。最多三个，未知不硬凑，不因行情缺口换币。

### 3.1 IRYS：两项较清晰的成对业务比较

核心服务：为数据型链上应用提供可验证数据存储并结合执行。Irys [2025-01-28 发行方新闻稿](https://chainwire.org/2025/01/28/irys-launches-the-first-programmable-datachain-purpose-built-for-ai/)直接将 Filecoin、Arweave 作为比较对象。只取其比较关系，不采信性能、成本等营销数字；当时为测试网材料，不证明所有规划功能在事件时已成熟。

- 固定核验线索：**Arweave / AR；Filecoin / FIL**。两者的[Arweave 论文，署期 2023-12-26](https://www.arweave.org/files/arweave-lightpaper.pdf)、[Filecoin 论文，署期 2017-07-19](https://filecoin.io/filecoin.pdf)支持存储服务定位；代币与网络存储支付/激励相关，不是自动分红凭证。
- 另实际检查 4EVERLAND、aleph.im / Aleph Cloud、DeNet、Filebase，共六个项目槽位。[4EVERLAND 2024-06-18 周报](https://medium.com/4everland/the-4everland-bi-weekly-report-jun-3-2024-jun-16-2024-768e42f58380)支持存储/托管服务交集，但仍需处理上下游与同行边界；其 [LAND 是资源计价单位](https://docs.4everland.org/get-started/billing-and-pricing/what-is-land)，不能未经映射当成交易所资产。不是断言该项目没有其他代币。
- [aleph.im 2019 白皮书副本](https://resources.cryptocompare.com/asset-management/567/1675701639148.pdf)有应用存储与计算交集，但未完成旧发行资产到事件时身份的映射；DeNet 的旧文章直接打开未取得完整正文，当前文档涉及 2026 年版本；[Filebase SDK](https://filebase.github.io/filebase-sdk/)支持服务描述，但没有完成事件前版本与可投资资产确认。均保留缺口，不视为永久不合格。
- 其他已遇线索包括 Walrus、Sia、Storj、Swarm、Stratos、Peergos、Pinata、NFT.Storage、Functionland、Inrupt；未逐项完成历史资格比较，不补第三项，不宣称 AR/FIL 是完整行业“前两名”。

### 3.2 RLS：机构服务交集成立，不能直接推导代币需求

核心服务：面向金融机构的隐私、合规链部署与互操作，连接机构结算及 DeFi。[Rayls 2024-06-20 发行方发布](https://www.prweb.com/releases/rayls-blockchain-launches-today-aiming-to-combine-the-traditional-and-decentralised-finance-ecosystems-302178254.html)及[2025-09-17 Tokenomics](https://www.rayls.com/blog/rayls-tokenomics-a-united-tradfi-defi-economy)支持此定位；后者包含拟议治理与费用安排，不是使用量、收入或价值捕获已实现证明。

- 固定核验线索：**Avalanche / AVAX；Canton / Canton Coin（CC）**，按这两个项目的英文名称排序。属于同服务/客户推断，没有查明事件前明确点名的成对竞争优先级。
- [Avalanche Evergreen 官方文章，页面署期 2023-04-09](https://www.avalanche.com/about/blog/avalanche-launches-evergreen-for-institutional-blockchain-deployments/)描述机构许可链、定制部署与互操作。原 avax.network 路径访问失败后定位到此正式站路径。平台服务重合不证明每条机构链都以 AVAX 付费，更不证明 RLS 上新将增加 AVAX 需求。
- [Canton 2024-07-01 官方发布](https://www.canton.network/canton-network-press-releases/the-canton-networks-global-synchronizer-and-canton-coin-go-live?hs_amp=true)支持受监管资产隐私交换与互操作，Canton Coin 支付同步流量等效用；CC 标识另由 Binance 的具名资产公告核对，不用同缩写的股票或其他代币替代。
- 该分支实际检查 Aleo、Avalanche、Aztec、Base Ledgers、Canton、Cardano 六项；其他业务/版本资格未知。Corda、Kaleido、Hyperledger Besu/Fabric、Quorum、Midnight、Oasis、Secret、Partior 等只是后续未核线索，不因缺少独立代币便称没有业务竞争。
- 分支不能证明这六项就是初池排序前六，故这两个核验线索**不是已经证明可机械复现的完整研究篮子**，详见 §6。

### 3.3 POWER：目标定位可追溯，本预算内未建立具体同行资产

核心服务：为游戏及合作产品提供共享经济、奖励/结算及运营工具。[Pixion Games 2025-09-25 合作公告](https://pixiongames.com/pixion-games-power-protocol-partnership-ecosystem-token-power-2/)描述 POWER 在 Fableborne 及未来产品中的角色；后续能力不能全部当成事件时事实。

本批两次通用发现主要返回目标自身、合作方和 Ronin、Solana、Ethereum L2 等宽泛宿主平台，**没有据此确认同核心服务的同行代币**。Fableborne 是应用/合作关系，不因名称关联变成竞争者。没有为凑三个追加熟悉的游戏币。

[2025-12-23 的发行方扩展公告](https://chainwire.org/2025/12/23/power-protocol-announces-expansion-of-its-web3-distribution-layer/)晚于本事件，不能证明 12 月 6 日已有该扩展规模。这里的缺口是限定检索未定位足够关系，不是证明没有同行，更不是证明游戏生态不能研究。

### 3.4 WET：业务同行与可投资代币之间出现断层

核心服务：以主动做市及链上结算，为路由/聚合器流量提供现货交易执行。[Syndica 原始研究，2025-11-26](https://blog.syndica.io/deep-dive-solana-defi-october-2025/)提供事件前 HumidiFi、SolFi、Tessera 同类业务线索；只使用业务存在/类别，不按交易量、市场份额、价差或表现选币。当前取得的 [HumidiFi Litepaper 副本](https://resources.cryptocompare.com/asset-management/21309/1766139895705.pdf)支持主动流动性模式，但副本不能独立证明事件前公开版本。

实际检查的六项为 Aquifer、BisonFi、GoonFi、Obric、SolFi、Tessera；未完成它们的事件前可投资代币身份绑定。**本批没有确定同行代币，不等于查明它们当时均没有代币。**ZeroFi 保留为未核线索；没有猜测 GOON 等相似 ticker。

Raydium/Orca 的普通 AMM、Jupiter/Titan/DFlow 的路由角色需要分别论证，不能因为有可交易代币就自动替换上述缺口；同时也不宣判它们永远不能作为更宽交易执行研究中的同行或对照。业务粒度问题尚未冻结，本轮不据此追加新的关系类别。

### 3.5 NIGHT：隐私可编程应用不同于仅匿名转账

核心服务：为开发者及企业提供可编程隐私、公私状态及选择性披露。[Midnight 2025-06-06 官方文章](https://midnight.network/blog/midnight-at-consensus-2025-building-the-future-of-rational-privacy)描述 NIGHT 与 DUST 的不同角色，并含主网上线前计划；未据该旧文章推断事件时所有能力均已上线。

- 固定核验线索：**Aleo / ALEO；Aztec / AZTEC**，同服务推断，不是已证实成对竞争。[Aleo 2024-09-17 官方主网 FAQ](https://aleo.org/post/aleo-mainnet-faq/)支持隐私 dApp/开发者平台及费用、质押资产线索；[Aztec 2025-10-08 官方文章](https://aztec.network/blog/aztec-the-private-world-computer)支持公私混合智能合约应用。
- [Aztec 2025-12-06 官方安排](https://aztec.network/blog/aztec-tge-next-steps)说明当时 Token Vault 中资产不可转让，仍可参与质押/治理，最早计划于 2026 年 2 月投票开启 TGE。**现货不可转让并不自动证明没有永续/盘前衍生品**；目标交易所身份另查。
- 实际检查 Aleo、Aztec、Canton、Chainlink、Duality Technologies、Fhenix 六项；Canton 对本项精确隐私应用平台关系仍未知。Oasis、Secret、Mina、Partisia 等未核线索不作反向排除。只做匿名支付或单一隐私组件，也不能仅因“隐私”标签自动成为同功能平台。
- 原分支的发现步骤不合规；上述资料只是主审复核过的事实线索，不能包装为该发现算法的成功结果，详见 §6。

以上所有旧署期的当前网页/PDF都不是独立认证的历史快照；有时原始材料本身也含规划、营销或修订。本阶段允许保留明确标注的线索与未知，但不能升级为已验证 PIT。

## 4. 历史目标市场：在锁定线索后检查，不以归档存在代替身份

`2026-11-12T15:18:17Z` 固定上述六个资产核验线索及各项未知后，才开始本轮 Binance 同行合约查询。没有因查到合约或缺数据改变线索。核验范围仍为 Binance USDⓈ-M / USDT 永续，不混用其他交易所、现货、USDC、BUSD、币本位或交割合约。

| 资产线索 | 官方历史依据 / 本批判断 | 是否请求事件三天归档 |
| --- | --- | --- |
| AR | [2021-09-24 公告](https://www.binance.com/en/support/announcement/detail/6863561ed5814891bb99374da33a17ce)明确 ARUSDT 于 2021-09-28 03:30 UTC 上线，为 USDT 保证金永续 | 是 |
| FIL | [2020-11-03 官方竞赛](https://www.binance.com/en/support/announcement/detail/3e5cd93fe9a745f28e4445e677579438)支持 FIL 的 USDT-Margined Futures 已存在；本批未独立精确锁定永续 symbol/类别的历史依据。不能将这点取证缺口称为当时不存在，也不能用 FILUSD 币本位或 FILBUSD 代替 | 否，历史类别证据仍部分不足 |
| AVAX | [2020-09-22 公告](https://www.binance.com/en/support/announcement/detail/14040912781f429da8863a97ba1e4e3a)明确 AVAX/USDT 永续于 2020-09-23 07:00 UTC 上线并以 USDT 抵押 | 是 |
| CC | [2025-10-31 盘前上线](https://www.binance.com/en/support/announcement/detail/75b473baa0db499ca39cb1a40dba1b7b)明确底层 Canton Network/CC 及 USDT 永续；[2025-11-10 转标准公告](https://www.binance.com/en/support/announcement/detail/1c849dd19ba64e15af8ba7ac91c3fbdb)计划 11:30 UTC 起过渡，均早于 RLS 事件；未取得实际过渡完成日志 | 是 |
| ALEO | 本批未定位足够的 Binance 历史产品身份。其他交易所 ALEOUSDT 及包含 Bybit 转发的 COINRF 页面不构成 Binance 证据 | 否，身份未知；不是认定无此合约 |
| AZTEC | [Binance 官方公告](https://www.binance.com/en/support/announcement/detail/2bf6526552a8464da4420fd0d5a412a9)明确所识别 AZTECUSDT 盘前永续于 2026-02-11 04:30 UTC 上线，晚于 NIGHT 事件 | 否，对该已识别产品为事件后上线；不补其他币 |

六份直接关联身份的官方详情 JSON 请求发出于 `15:22:33Z–15:22:41Z`，均 HTTP 200、curl RC=0、API `code=000000`。另查询一份 2025 年保证金更新公告，未包含所需标的，不将其计作身份支持。搜索失败或无命中也不等于市场不存在。

BTCUSDT/ETHUSDT 沿用首批报告列出的官方 USDT 永续历史资料。这些历史身份依据与本轮对象检查都不证明事件分钟无停牌、维护、流动性枯竭或异常交易。

## 5. 实际归档检查：33 个物理对象，不是 33 个独立事件

只对三个已明确身份的同行，以及五个事件的 BTC/ETH 对照，检查公告日前一天、当天、后一天的 1m 日包。统一路径：`https://data.binance.vision/data/futures/um/daily/klines/{SYMBOL}/1m/{SYMBOL}-1m-{YYYY-MM-DD}.zip`，仅 HEAD；同 URL 加 `.CHECKSUM` 仅 GET，限制文本体积 8,192 bytes。**没有 GET 市场 ZIP。**

| Parent | 同行对象及 UTC 三天 | BTC/ETH 对照及去重 |
| --- | --- | --- |
| 6 / IRYS | ARUSDT：2025-11-25、26、27，3 对象 | 同三天各 BTCUSDT、ETHUSDT，6 对象 |
| 7 / RLS | AVAXUSDT、CCUSDT：2025-12-01、02、03，6 对象 | 同三天各 BTCUSDT、ETHUSDT，6 对象 |
| 8 / POWER | 没有确定同行资产，不猜测对象 | 2025-12-05、06、07，各 BTCUSDT、ETHUSDT，6 对象 |
| 9 / WET | 没有确定同行资产，不猜测对象 | 2025-12-09、10、11，各 BTCUSDT、ETHUSDT，6 对象 |
| 10 / NIGHT | ALEO 未核身份、AZTEC 事件后上线，均未请求 | 同 Parent 9，保留六项逻辑引用，不重复请求 |

共 39 个 Parent-对象逻辑引用，去重为 **33 个对象 = 9 个同行对象 + 24 个市场对照对象**。物理请求为 66 次，发出于 `2026-11-12T15:24:26Z–15:26:05Z`：33 HEAD + 33 CHECKSUM GET，逐项 HTTP 200 / curl RC=0，无重试。所有 HEAD 的正文下载字节数为 0；33 份校验文本均含合法 64 位十六进制摘要，且文件名精确对应请求 ZIP。

这 33 个对象分别支持 `archive_object_found`、`checksum_available`，不支持 `price_coverage_verified=true`。本轮没有实际 ZIP 摘要比对、解压、分钟连续性、时点对齐或价格数值核验。未请求的 FIL/ALEO 等不是归档失败分母，也不能由未请求推出 404。

WET 与 NIGHT 同一 UTC 日，对照对象重合。未来事件研究不能把重复下载或多个同行计为额外独立新闻冲击；窗口重叠、同日其他消息及同行自身公告仍须处理。

## 6. 执行偏差及不能伪造的“复现通过”

本批在联网前另设了低成本检索约束：每项目两次通用发现，最多检查六个项目槽位，再按关系/来源等级及稳定名称排序。**这只是本次有限调查的操作约束，不是获批的正式研究协议；实际没有被所有分支严格执行，因此不能称其验证成功。**

- RLS 分支实际检查六项，但不能可靠还原最初两次通用查询的完整候选池及名称规范化。已撤回“这六项是机械排序前六”的自评。
- NIGHT 分支实际进行了六次通用发现，比预设多四次；初始两次未找出后来所报六项，不能将后续追加倒灌为原池。已撤回其“规则内同行选择已完成”的自评。
- IRYS 的首个发现查询包含已知 Arweave/Filecoin 名称，不属于完全盲发现。后续来源确实支持比较关系，但不能据此声称无研究者先验影响。
- 主审核查来源并在合约/归档查询前重新记录六个**资料核验线索**，没有把分支建议包装成合格研究 Universe。RLS/NIGHT 的新增业务来源可以作为事实线索保留，不能消除上述过程限制。
- 4EVERLAND、aleph.im、未检查的行业线索等保留缺口；POWER 的少量通用查询不充分也不得解释为客观没有同行。没有从“搜不到”推导业务不合格。

不为这项人工预审新增 Recorder、自动分类器、行业标签数据库或审批系统。后续若正式立项，应先冻结一个确实能执行、允许未知且有明确候选边界的方法；本批过程不应冒充该方法的验证证据。

## 7. 人工成本及继续/暂停判断

分两段执行：首段已有 `07:13:34Z` 事件锁定、`07:16Z` 公告请求及 `07:20Z` 资料检查点；用户随后要求“继续”，后段有 `15:18Z` 线索锁定及 `15:22–15:26Z` 身份/对象请求记录。**不能把两个时段的跨度当作持续劳动时长，亦未取得完整主动人时计量。**

| Parent | 已有投入记录 / 最明显新增成本 |
| --- | --- |
| IRYS | 主审交错处理，未单独计主动分钟；主要成本是去中心化存储、托管层及旧资产映射边界，而非归档 HEAD |
| RLS | 分支自报初查 `07:15:34–07:20:30Z`，不是独立计时证明，亦不含主审复核；机构链与基础代币经济连接仍需解释 |
| POWER | 主审交错处理，未单独计主动分钟；限定查询未定位具名同服务资产，扩查是否划算尚不确定 |
| WET | 主审交错处理，未单独计主动分钟；同服务项目可定位，但资产身份/业务粒度存在缺口 |
| NIGHT | 分支自报初查 `07:15:33–07:20:11Z`，不是独立计时证明，亦不含更正/主审复核；发现约束偏离、历史资产/市场可得性均影响成本 |

**逐 Parent 精确成本是本次交付缺口。**不能据上述自报数字计算“每个合格 Parent 只要几分钟”，也不能声称半天预算已被精确独立验收。实际没有因凑齐有效事件补样；本批到此停止，不扩到第 11–15 项。

对研究的指导分开判断：

1. **资料层面部分可行。**IRYS 的成对比较、RLS 的机构客户功能、NIGHT 的隐私应用定位均有可查历史材料；未观察收益也能提出具体关系，不必仅凭叙事猜测。
2. **产能尚未证明。**五个新 Parent 中只有 IRYS/RLS 的部分线索取得明确事件前目标永续身份；未核历史身份不等于真实缺失。候选发现不完整，本批与首批方法也不完全一致，不能简单合并成全年成功率。
3. **经济机制尚未闭合。**项目业务扩张不自动增加同行代币需求；AVAX 与机构部署的关联、WET 同行业务是否有对应资产等，应区别于“档案能下载”。没有证据证明注意力溢出为正，也没有证伪它。
4. **暂不滚动堆工程或样本。**先讨论如何以更简单且统一的来源/关系方法保留完整适用 Parent 和缺口，再决定是否正式 Design。不能只留下本批较清晰的两个事件算收益，或临时改成只做存储/机构链以获取好结果。
5. **未来最关键的实验仍是可执行延迟后的响应。**若进入正式研究，再明确接收/决策时间、一个主要窗口、市场对照、聚类及成本边界。本轮没有冻结 5–15 分钟等参数，也没有授权下载或运行。

结论仍为 `hypothesis_only / evidence_insufficient`。本批不是 D2 Alpha 成功或失败的证据；它支持把下一次讨论聚焦在**可重复的关系构造及可交易资产映射**，而非立即建设新闻监控或回测系统。

## 8. 范围、检查与临时复核线索

执行基线 HEAD：`c467e9b043acbd5d1d8b3c8d5d03cb21aeb77760`。基线已有备忘修改、首批预审与 APRO/BOB 复核未跟踪文件，全部保留；本轮仓内只新增本文，不改旧名单、规则、批准契约、代码或配置。

临时目录 `/private/tmp/d2-next5-preflight-20261112.Ndo9je` 可能被系统清理，不是持久证据根或新机器消费链。表格及来源链接是人工交付；以下摘要用于定位本次操作记录：

| 临时记录 | SHA-256 |
| --- | --- |
| `selection_lock.txt`，新联网前第 6–10 项锁定 | `b41a9df9b4c89e8f376bcb0e9219690bf4cabe23f0eb18dfe7f349af290ed4b8` |
| `peer_lock_before_market_checks.md`，市场查询前线索与偏差锁定 | `c19e89d428b485e33e81e11243fec8e3d33f7a63d51e55aeab27ff646a9fec94` |
| `identity_decision_before_archive.txt`，对象检查前身份处置 | `2125d99b53ed2222ea4bf2ee72dc00edf1df124a280c6c746779321cb35bfcd9` |
| `archive_objects_locked.tsv`，33 个去重对象 | `0af2891c08dbddc5524a785ba5851e3427421d41986b4cb13551e9262ce0d4dd` |
| `archive_requests.tsv`，66 次方法/URL/HTTP/RC/UTC/正文下载字节 | `0222fd6f4f88b3c01e61e9723d7c0c7ae6b42f6fc79108e37b8951b58351672b` |

- 用独立于联网循环的文本检查重算请求数、HEAD 零正文及校验文本文件名/摘要格式，RC=0；不冒称验证了实际 ZIP 哈希。确认两项同日 Parent 的逻辑引用没有丢失。
- 公告首次沙箱内请求曾 DNS 失败（curl RC=6、HTTP 000），在获准联网环境重试成功；部分公开来源访问失败、仅有搜索文本或日期不明，均未伪装为取得历史原件。66 次归档请求自身没有失败。
- 检索返回过 2026 年比较页、价格/市场字段及同名项目；仅作资料线索或舍弃，不提取行情、不依据表现选样，不宣称完全未受既往结果暴露。IRYS、POWER 等此前已出现在本项目研究，不是全新未见留出样本。
- 最后核对三份本地输入哈希、既有三份文档逐字节一致、Git 基线/范围、本文空白及引用目标。纯元数据/文档任务不运行或伪造 pytest、代码扫描、研究计算或 Rule 17 verifier 成绩。
- 未下载行情 ZIP、读取 J-A raw/J-B 或研究快照、计算收益/相关性/成本、拟合、下单、SSH、部署、commit/push 或运行时操作。`RISK_LIVE_TRADING_ENABLED=False` 保持不变；本文不批准正式研究、后续扩样或任何交易权限。
