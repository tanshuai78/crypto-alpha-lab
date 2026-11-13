# D2 上新事件与历史业务同行：元数据可行性预审

日期：2026-11-12（Asia/Shanghai）。性质：单份人工决策参考；不是正式 Universe、历史关系数据库、机器输入、准入收据或 Alpha 证据。

## 1. 结论

**D2 有受限的资料可行性，值得继续讨论，但尚不适合直接开始收益研究或搭建工程。主要困难是历史同行关系及其版本证据，不是已定位的行情归档对象。**

| 本轮交付事实 | 实际结果与限制 |
| --- | --- |
| 固定事件 | 先锁定最早 5 个 Parent，包含 7 个 child；没有补样或替换 |
| 公告时间 | 5/5 当前官方详情的发布时间与既有目录毫秒值一致；不是首次传播或历史接收时间证明 |
| 历史业务关系 | 5/7 child 找到合计 10 个候选同行；4/5 Parent 至少一个 child 有候选，3/5 Parent 所有 child 均有候选；证据强弱不同，不能统称历史关系已验证 |
| 关系缺口 | GIGGLE、BEAT 未建立符合限定业务边界的同行；不以其他 meme 或泛 GameFi 代替 |
| 历史产品身份 | 9/10 同行候选找到事件前的 Binance USDT 永续上线依据；Rootstock/RBTC 的对应历史合约身份未知，不用 RIF 替代 |
| 归档对象 | 27 个同行日包对象、30 个 BTC/ETH 对照日包对象：57/57 HEAD 为 HTTP 200；57/57 同名 CHECKSUM 文本 GET 为 HTTP 200，文本格式及文件名检查通过 |
| 尚未证明 | ZIP 实际哈希、分钟完整性、事件时可交易性、真实成本、同行收益、相关性或 Alpha 均未验证 |

这些是资料调查计数，不是独立统计试验数，也不是“达到某个成功比例即可立项”的门槛。没有证据说明同行必然上涨或资金必然被分流；研究状态仍为 `hypothesis_only / evidence_insufficient`。

## 2. 授权、输入与固定样本

依据用户本轮“授权进行 D2 元数据预审”，执行[讨论备忘 §6.1](2026-11-12-launch-event-data-research-directions-discussion_CN.md)。执行开始约为 `2026-11-12T05:57:37Z`；限定联网检查完成于 `06:22:49Z`，其后仅整理与核对报告，未超半天预算。

- 备忘执行版本 SHA-256：`b8d31c5a659e8d5c0fbb6a6c2469d203ba87106ab7bfeb35b6ecca9c14e11c65`。该文件执行前已有未提交修改；本轮不修改它。
- 只读取下列三个既有数据文件的身份、分类或公告时间元数据。不运行旧 loader，不读取 J-A raw 树、J-B 成交、旧研究明细/模型输出，不生成 receipt。
- 对照[J-C 冻结 Design](../designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md)所列身份核对 SHA；本轮权限只覆盖此人工元数据调查，不豁免未来 J-A/J-C 正式消费门禁。

| 本地输入 | SHA-256 |
| --- | --- |
| `data/exports/stage1_5j_token_launch_classification_ledger_v2.csv` | `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b` |
| 下述 J-A 根的 `summary.json` | `722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b` |
| 同根 `manifest.json` | `b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf` |

J-A 根为 `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z`。核对 manifest 内 summary 的路径、字节数与 SHA 绑定；未验证其他 artifacts 或整个 sealed tree。summary 自身标记 `coverage_inventory_evidence_gap`，**不能把本次元数据身份核对写成完整 Rule 17 准入通过**。

### 2.1 排序与锁定先于联网

账本严格 12 列、281 行，不含公告发布时间。按 `crypto / standard / confirmed` 筛出 53 child / 42 Parent；42 个 Parent 均可唯一关联 summary 的 `catalog_denominator_records`，原目录共有 335 条记录。按原始 `release_date_ms`、`source_article_id` 排序后锁定下表，之后才访问当前网络。没有使用计划开盘或当前网页更新时间代替排序依据。

源码定位：[J-A 元数据提取](../../src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py)将官方目录 `releaseDate` 保存为 `release_date_ms`。这是旧目录记录，不是本轮重新抓取后再排序。

| 顺序 / Parent 官方链接 | child | 原目录发布时间，UTC / 毫秒 | 正文计划上线 S，UTC |
| --- | --- | --- | --- |
| 1 / [8272526b66b042dfbfbd7b717f3d4490](https://www.binance.com/en/support/announcement/detail/8272526b66b042dfbfbd7b717f3d4490) | GIGGLEUSDT | 2025-10-09 08:23:03.522 / `1759998183522` | 2025-10-09 09:45 |
| 2 / [b7c479f8dfa64156a34e8bcefc241732](https://www.binance.com/en/support/announcement/detail/b7c479f8dfa64156a34e8bcefc241732) | LABUSDT、RIVERUSDT | 2025-10-17 12:58:48.360 / `1760705928360` | LAB 14:30；RIVER 14:45，同日 |
| 3 / [eedd30f534f94583b64db6ba7f375ac0](https://www.binance.com/en/support/announcement/detail/eedd30f534f94583b64db6ba7f375ac0) | ATUSDT（APRO） | 2025-10-29 09:36:15.831 / `1761730575831` | 2025-10-29 11:30 |
| 4 / [15f01e2861ac46e2b698212cb220f4d7](https://www.binance.com/en/support/announcement/detail/15f01e2861ac46e2b698212cb220f4d7) | BEATUSDT（Audiera）、CLANKERUSDT（tokenbot） | 2025-11-12 10:15:39.520 / `1762942539520` | CLANKER 12:00；BEAT 12:15，同日 |
| 5 / [36c4f838c82b4f81920d5adc958d9a53](https://www.binance.com/en/support/announcement/detail/36c4f838c82b4f81920d5adc958d9a53) | BOBUSDT（Build on Bitcoin） | 2025-11-21 09:28:51.171 / `1763717331171` | 2025-11-21 10:45 |

### 2.2 当前核验结果及不能据此推断的内容

逐一 GET 官方公开详情接口 `https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=<Parent ID>`，检查时间为 `2026-11-12T06:01:23Z` 至 `06:01:26Z`：五项均 HTTP 200、curl RC=0、API `code=000000`，`publishDate` 与上表完全一致；本次返回的 `lastUpdateTime` 均为 0。

正文支持这七个 child 为加密原生标的、USDT 结算永续的首次上线公告候选，没有因当前核验排除或替换 Parent。Parent 4 的普通网页入口发生目录页重定向，但官方详情 JSON 可读取，未将其误判为公告不存在。

**限制：**当前 API 可以修订内容，`lastUpdateTime=0` 不能保证从未修改；本轮没有完成全互联网更早预告、历史推送日志和公告历史版本的穷尽核验。因此上表只能称“原目录与当前官方发布时间一致”，不能直接当成真实首次信息冲击的 PIT 锚点。S 也不是实际首笔成交 T0。项目 TGE、现货或 Alpha 上线与首次永续公告必须区分。

## 3. 先锁同行，再核历史合约和归档

`2026-11-12T06:14:21Z`，在本轮首次同行合约身份查询和任何归档对象请求之前，固定下表十项候选。不依据事件收益、市值表现或归档是否齐全选币；每个 child 不超过三个。

| 新币 | 固定同行候选 / 资产 | 关系依据与本轮判定 |
| --- | --- | --- |
| GIGGLE | 无 | 官方定位为 meme；未建立直接业务同行。其他 BNB meme 不因同链、叙事相似而入选；不是证明没有同行 |
| LAB | Banana Gun / BANANA | 链上交易终端、执行/狙击工具的核心功能相近；由两方历史业务描述推定，不是项目双方明确声明的直接竞品；LAB 历史材料为第三方来源 |
| RIVER | Lista DAO / LISTA；Liquity / LQTY | 抵押稳定币及相关借贷/稳定模块的业务交集；River 旧身份和当前服务范围的历史衔接仍需补证。不能由此认定跨链架构、抵押结构或代币价值捕获相同 |
| APRO / AT | Band Protocol / BAND；Chainlink / LINK；DIA / DIA | 预言机/链外数据服务，具有较清晰的同核心业务候选依据；不是按同分钟价格相关性选取 |
| BEAT | 无 | 音乐/舞蹈游戏。未找到本次能核实的直接同类业务代币；不以泛游戏、音乐流媒体代币填充 |
| CLANKER | Pump.fun / PUMP | 有第三方原始研究直接比较二者的代币创建/发行功能；报告历史公开时间的独立证明较弱，暂作候选 |
| BOB | Bitlayer / BTR；Rootstock / RBTC；Stacks / STX | Bitcoin 智能合约/DeFi 基础设施的同业务候选；三者安全模型、资产角色不同。RBTC 是 Rootstock 的对应原生资产候选，不是 RIF |

**候选不等于历史关系准入。**这里优先使用公告前成文的项目材料，其次使用同期第三方材料；多数关系属于“同核心业务”的研究者归类，不是成对竞争关系的独立事实证明。当前读取的旧日期文章或 PDF 不是经过独立时间戳认证的历史页面快照，不能标成全部 PIT 已验证。

**顺序记录的小偏差：**锁定笔记中 RIVER 的展示顺序为 Lista、Liquity；若证据同级，严格英文字典序应为 Liquity、Lista。本轮保留原锁定记录并披露，未在查行情后改选。只有两项、未触及三项上限，故未改变候选集合；未来如把排序用于截取集合，须在截取及行情核验前机械执行并列规则，不能沿用手写顺序。

### 3.1 历史关系的可追溯来源与质量限制

| 对象 | 公告前成文的来源 | 本轮能支持什么 / 剩余限制 |
| --- | --- | --- |
| LAB / BANANA | [LAB，2025-10-03，Crowdfund Insider](https://www.crowdfundinsider.com/2025/10/253789-lab-closes-1-5m-community-round-lab-token-en-route/)；[Banana Gun，2024-07-19，KuCoin 项目介绍](https://www.kucoin.com/announcement/en-banana-gun-banana-gets-listed-on-kucoin) | 支持链上交易工具的功能交集；LAB 正文由网页检索工具解析，但直接 curl 为 403；KuCoin 为 HTTP 200。KuCoin 现货介绍仅用于业务/资产身份，不充当 Binance 永续证明 |
| River | [发行方 satUSD 更名文章，2024-09-11](https://blog.river.inc/sat-stablecoin-is-renaming-to-satusd-2/) | 可定位到旧稳定币业务的缓存/索引文本；直接 curl DNS 失败（HTTP 000、RC=6），网页打开亦失败。不能把缓存条目当作已验证的原始历史版本或完整代币迁移映射 |
| LISTA / LQTY | [Lista，2024-11-27](https://blog.lista.org/product-update-lisusd-peg-stability-module-psm-update)；[Liquity，2024-09-04](https://www.liquity.org/blog/liquity-v2-improving-defi-with-bold-innovation) | 两份发行方业务文章直接访问均 HTTP 200，支持稳定币业务候选；本轮未独立验证历史网页版本。同行资产为 LISTA/LQTY，不是 lisUSD/LUSD |
| APRO | [Nervos 2024 年度报告](https://www.nervos.org/assets/pdfs/2024_Nervos_Foundation_Year-end_Report.pdf)；[Nervos 托管社区周报，2024-08](https://talk.nervos.org/t/ckb-weekly/7306/56) | 报告/周报描述 APRO 的预言机业务。网页工具可解析；PDF 直接 curl 因本轮 8MB 上限中止（HTTP 200、RC=56），没有声称成功保存完整 PDF |
| BAND / LINK / DIA | [Band 2019 年回顾，2019-12-31](https://medium.com/bandprotocol/band-protocol-2019-recap-c608e3297958)；[Chainlink OCR 技术论文，2021-02-24](https://research.chain.link/ocr.pdf)；[DIA 发行方新闻稿，2021-11-09](https://www.globenewswire.com/news-release/2021/11/09/2330743/0/en/dia-association-launches-an-oracle-integration-with-solana.html) | 支持预言机服务身份。LINK PDF 直接 HTTP 200；BAND、DIA 为可检索/解析的历史文本，但直接 curl 均 HTTP 403，未记作完整原始正文下载成功 |
| CLANKER / PUMP | [K33 原始研究《Pump Up The Base》](https://assets.ctfassets.net/i0qyt2j9snzb/10CVg1ZbSkfJSsGKRtKnib/fed849d1549e3308ad69ed7bb647aaf5/Pump_Up_The_Base.pdf)，PDF 元数据日期 2024-12-04 | HTTP 200；正文直接比较业务功能，但 PDF CreationDate/ModDate 不能独立证明当日已公开。Pump.fun 服务当时存在不等于 PUMP 代币已交易，产品身份另查 |
| BOB / BTR | [BOB 论文，封面 October 2024](https://docs.gobob.xyz/whitepaper.pdf)；[Bitlayer 论文，2025-07-09](https://static.bitlayer.org/Bitlayer-Technical-Whitepaper.pdf) | 均 HTTP 200，支持 Bitcoin 智能合约/DeFi 业务交集。BOB 当前 PDF 元数据为 2025-07-23，不能当成已取得 2024 原版；两个日期均早于 BOB 事件，但公开历史版本仍待验证 |
| RBTC / STX | [Rootstock 2024/25 路线图副本](https://resources.cryptocompare.com/asset-management/308/1719992086574.pdf)；[Stacks 发行方文章，2024-11-21](https://www.stacks.co/blog/optimizing-nakamoto) | 均 HTTP 200。前者为第三方保存的发行方资料，PDF 元数据 2024-07-03；副本来源/公开时间证明弱于独立历史存档。Stacks 文本支持 Bitcoin 智能合约业务，不代表各协议技术等同 |

**最常见缺口不是行业名字，而是“事件前已公开的确切业务版本 + 当时资产身份 + 可重复的同行选择依据”这一组合。**本轮未额外建设历史行业库。

人工检索不保证穷尽。另发现但未认定为同等级合格并集的线索包括：LAB 的 BullX/GMGN/Photon（历史可投资资产身份未核）；River 的 Maker/Sky（历史代币迁移映射未核）；APRO 的 Pyth/RedStone/Tellor、BOB 的 Merlin/B2（未完成同等级历史证据比较）；CLANKER 的 Zora（业务边界未定）。没有声称这些项目不存在或应永久排除，也不能把本表宣称为行业“前三名”。本轮不在查完归档后追加同行。

## 4. 历史市场身份，不以当前 exchangeInfo 或 ZIP 存在替代

以下官方资料支持对应合约曾在事件前上线；本轮未完整复核其后所有维护/下架/重上记录，故不等于逐分钟可交易性已核实。九个同行均按 Binance USDⓈ-M USDT 永续定位，不混入现货、USDC、币本位或交割合约。

| 候选资产 / 合约 | 历史官方依据（UTC） | 本轮结论 |
| --- | --- | --- |
| Banana Gun / BANANAUSDT | [上线 2024-08-15 02:00](https://www.binance.com/en/support/announcement/detail/78925b1330584febb9baca0b45ac8e40) | 公告列明 Banana Gun、USDT 结算永续，早于 LAB 事件 |
| Lista / LISTAUSDT | [上线 2024-06-20 12:30](https://www.binance.com/en/support/announcement/detail/6f7bdac5744c4a109b1042496764df91) | 早于 RIVER 事件 |
| Liquity / LQTYUSDT | [上线 2023-03-10 12:00](https://www.binance.com/en/support/announcement/detail/dc1fa8e36e8c4cbdb6f200bd3aac916e) | 早于 RIVER 事件；并非检索中出现的未经核实“3 月 8 日”说法 |
| Band / BANDUSDT | [上线 2020-07-29 07:00](https://www.binance.com/en/support/announcement/detail/ea85b877da3f4bebaf17922f32f58dbc)；[2025-06-13 USDⓈ-M 维护公告](https://www.binance.com/en/support/announcement/detail/b1219385d93740d1a8af9fc8de80f1cb) | 历史 BAND/USDT 永续，后者另确认 USDⓈ-M 类别 |
| Chainlink / LINKUSDT | [上线 2020-01-17 08:00](https://www.binance.com/en/support/announcement/detail/360038885371) | LINK/USDT 永续，非 LINKUSD 季度交割 |
| DIA / DIAUSDT | [上线 2024-10-02 12:30](https://www.binance.com/en/support/announcement/detail/b2552cf226ed409990663ea2a8fc089f) | 早于 APRO 事件 |
| Pump.fun / PUMPUSDT | [盘前上线 2025-07-10 07:30](https://www.binance.com/en/support/announcement/detail/4bc8b483d10d4619babb2015066b2d89)；[计划 2025-07-14 17:20 起转标准永续](https://www.binance.com/en/support/announcement/detail/e220b78bdf4848e3a61eb9fce99e2580) | 两条来源均早于 CLANKER 事件；不与其他名为 PUMP 的项目或 PUMPBTC 混淆。转换公告说明可耗时最多一小时，不冒称已取得实际完成日志 |
| Bitlayer / BTRUSDT | [上线 2025-08-27 10:30](https://www.binance.com/en/support/announcement/detail/2fc4d9f952ee4db4b36f1a350c211163) | 明确底层为 Bitlayer，早于 BOB 事件 |
| Stacks / STXUSDT | [上线 2023-02-21 14:30](https://www.binance.com/en/support/announcement/detail/e0aa73262d384ed3a616a4a66f59c9b5) | 早于 BOB 事件 |
| Rootstock / RBTC | 未取得 Binance 对应 USDT 永续的可信历史身份依据 | 历史身份未知，未猜测 RBTCUSDT 对象或换成 RIF；没有足够证据写 `instrument_unavailable_at_event` |
| BTCUSDT / ETHUSDT | [Binance 2020-01-16 官方回顾](https://www.binance.com/en/blog/all/421499824684900356)；[ETH 永续已上线公告，2019-11-29](https://www.binance.com/en/support/announcement/detail/360036964392) | 官方历史资料明确 USDT 永续类别，早于全部五个事件；不是当前交易对列表倒推 |

上述 12 次官方详情 JSON 请求发生于 `06:20:23Z` 至 `06:21:15Z` 之间，逐项 HTTP 200、curl RC=0、API `code=000000`。当前副本只用于历史产品元数据线索，不证明该副本当年各字段完全相同。

## 5. 日度归档对象检查

公告 UTC 日前一天、当天、后一天三天；未因同行或日期的行情覆盖重新选择对象。没有检查新币自身的价格，因为本阶段问题是既有同行及 BTC/ETH 数据能否定位。

每个对象使用官方 URL：`https://data.binance.vision/data/futures/um/daily/klines/{SYMBOL}/1m/{SYMBOL}-1m-{YYYY-MM-DD}.zip`，仅执行 **HEAD**；对同 URL 后加 `.CHECKSUM` 执行 **GET**。例如 [BANDUSDT 2025-10-29 的校验文本](https://data.binance.vision/data/futures/um/daily/klines/BANDUSDT/1m/BANDUSDT-1m-2025-10-29.zip.CHECKSUM)。下表的币和日期完整确定了 57 个实际请求对象，不是计划清单。

| Parent | 对象 SYMBOL | 三个实际检查 UTC 日 | ZIP HEAD / CHECKSUM GET | 检查结果 |
| --- | --- | --- | --- | --- |
| 1 | BTCUSDT、ETHUSDT | 2025-10-08、09、10 | 各 6 次 HTTP 200 / RC=0 | 6 对象可定位，6 文本可取得 |
| 2 | BANANAUSDT、LISTAUSDT、LQTYUSDT | 2025-10-16、17、18 | 各 9 次 HTTP 200 / RC=0 | 9 同行对象可定位，9 文本可取得 |
| 2 | BTCUSDT、ETHUSDT | 同上 | 各 6 次 HTTP 200 / RC=0 | 6 对照对象可定位，6 文本可取得 |
| 3 | BANDUSDT、LINKUSDT、DIAUSDT | 2025-10-28、29、30 | 各 9 次 HTTP 200 / RC=0 | 9 同行对象可定位，9 文本可取得 |
| 3 | BTCUSDT、ETHUSDT | 同上 | 各 6 次 HTTP 200 / RC=0 | 6 对照对象可定位，6 文本可取得 |
| 4 | PUMPUSDT | 2025-11-11、12、13 | 各 3 次 HTTP 200 / RC=0 | 3 同行对象可定位，3 文本可取得 |
| 4 | BTCUSDT、ETHUSDT | 同上 | 各 6 次 HTTP 200 / RC=0 | 6 对照对象可定位，6 文本可取得 |
| 5 | BTRUSDT、STXUSDT | 2025-11-20、21、22 | 各 6 次 HTTP 200 / RC=0 | 6 同行对象可定位，6 文本可取得 |
| 5 | BTCUSDT、ETHUSDT | 同上 | 各 6 次 HTTP 200 / RC=0 | 6 对照对象可定位，6 文本可取得 |

实际检查区间为 `2026-11-12T06:22:04Z` 至 `06:22:49Z`，共 114 次请求，57 HEAD + 57 CHECKSUM GET；无请求重试，无 HTTP/传输失败。57 份文本各含合法的 64 位十六进制摘要，文件名与所请求 ZIP 完全一致。

- 对已查 57 个对象分别标记 `archive_object_found`、`checksum_available`；本轮没有可据此标记的 `archive_not_found`。
- RBTC 的历史身份未知，未发出三天对象请求，归档可用性为 `availability_unknown`；不能把它算入已检查 57 个对象的成功或失败分母。
- **没有下载 ZIP，所以没有核对任何实际 ZIP 哈希。**对象存在及校验文本可取得，均不证明每分钟有记录、无空档、公告时交易正常或交易成本可测。

## 6. 资源判断与下一步讨论建议

**不因 GIGGLE/BEAT 的关系缺口立即否定 D2，也不因 57 个对象均能定位就宣布值得全面开工。**本次显示：部分有明确业务的项目可以建立可追溯候选；对 meme 或泛娱乐项目，“行业”标签过宽，容易变成研究者任意分组。

最值得继续讨论的具体问题是：**在公告前已经确定、且当时可交易的同业务资产，是否在新永续上线公告后出现相对于市场对照的正向异常响应？**这是待检验假说，不是本轮发现。若反向或无效，不能事后改称“资金分流”就算同一假说成功。

进入正式 Design 前需要解决的最小问题：

1. **历史关系可复现性。**复核目标项目与同行的事件前公开材料、资产身份和并列选择；保留原五个 Parent 的缺口，不只留下资料齐全事件。若扩展候选范围，须事前明确总体纳排规则，不能用本次调查结果反向定义成功行业。
2. **事件锚点与混杂。**明确观察公告还是计划开盘；补查更早公开合约预告、同日多 child、同行自身公告等。公告时间不是实际获知时间；一个 Parent 的多个同行不能当作多次独立事件。
3. **限定所需数据。**未来获准下载后才验证实际 ZIP、分钟连续性与窗口对齐。BTC/ETH 对象可定位不代表两个对照一定足以消除板块/全市场冲击，控制规则留待 Design 冻结。
4. **经济问题与预算。**注意力/替代买盘或交易性流动性需求只是可能机制，尚不能写出已被证明的付款方。年化独立机会、实际费用/价差、可成交窗口仍未知；沿用初筛四问明确投入上限和停止条件，不能凭五个 Parent 外推产能。

最大的新增成本预计是**人工历史关系和公告版本核验，以及后续定义无偏对照/事件聚类**，不是继续下载更多 K 线。先讨论关系证据能否低成本稳定复现；如果必须补建庞大历史行业标签库才能推进，应暂停这条工程支线，而非为凑齐样本扩大项目。

## 7. 复核线索、范围保护与未做事项

本轮临时公开资料和人工调查记录位于 `/private/tmp/d2-metadata-preflight-20261112.QV0vhk`，可能被系统清理；不是持久证据根或未来机器消费接口。上述表格、链接和限制才是本次交付。关键记录身份：

| 临时人工复核线索 | SHA-256 |
| --- | --- |
| `selection_lock.txt`，联网前五 Parent 锁定及输入校验 | `06579bfa1d2a3d214d837d64f01506d31746e7f96a8feb28fe0129f44778313c` |
| `peer_lock_before_instrument_checks.md`，合约/归档查询前的同行锁定 | `7a760abd9d6170c1b5d2b1f0fc5ffee37f69f437c3a1ecfac7decac4ebf81297` |
| `archive_requests.tsv`，逐对象 URL、方法、HTTP、RC、UTC 时间、下载字节数 | `46274c841d96c9dc8cb7f80eca790a24713858993602cd6f6d0441e3e2dbaee0` |

- 公开业务资料存在 DNS 失败、403 和下载大小中止，已在 §3 单独列明；curl RC=0 不等于 HTTP 请求成功，未把这些失败伪装成来源完整。
- 沿用的全年事件此前已进入本项目研究，不能声称这五个 Parent 是完全未见留出样本。检索摘要、公开研究图表或公告示例可能偶然展示价格，本轮未提取、计算或据此选择事件/同行；不作绝对“从未看见任何价格文字”的声明。
- 执行基线 HEAD：`c467e9b043acbd5d1d8b3c8d5d03cb21aeb77760`。仅新增本文；原有备忘修改保留，冻结输入、代码、配置和已批准契约不修改。整理后再次核对输入及备忘哈希、Git 范围、请求计数和 CHECKSUM 文本格式。
- 未请求市场 ZIP 正文、解压或解析行情；未计算收益/相关性、拟合、评分、运行研究或生成新机器产物；未新增代码、依赖、采集平台、Design/Plan 或 Rule 17 独立 Verifier。纯资料/文档任务不虚构 pytest 或代码扫描验证。
- 未执行 commit/push、部署、SSH、运行时或任何交易操作；配置文件的 `RISK_LIVE_TRADING_ENABLED` 保持 `False`。本文不授予上述权限，也不自动授予正式研究运行权限。
