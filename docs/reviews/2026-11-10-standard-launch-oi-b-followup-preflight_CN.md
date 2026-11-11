# Standard 后续事件与 OI 情景 B 数据覆盖预审

日期：2026-11-10（Asia/Shanghai）。性质：人工决策参考，不是正式 Universe、准入收据、模型输入或运行授权。

## 1. 结论与本轮边界

**在本次检索范围内，仅确认 1 个后续 standard crypto 候选 Parent / 1 个 child：CTUSDT。两类所需日包及 CHECKSUM 对象均可访问，但 CT 不是项目从未接触过的事件。当前不建议直接启动批量时间外验证工程。**

这不是 OI 无效或 standard B 已被证伪的结论。一个事件仍可做有边界的历史外推检查，但不能承担总体增量复现的证明；是否值得为它开发适配，应另行比较信息收益与成本。

- 用户批准的本轮工作为轻量元数据预审；按现有 Brief Plan 路径执行，不修改研究语义、旧代码、获批文件、分类账本或权限。
- 只读取旧人工报告的训练日期/分母元数据、官方公告、HTTP 响应头和 CHECKSUM 文本。未打开训练 CSV、J-A/J-B 历史数据树或市场 ZIP，未读取本候选的成交价格、OI 数值或后续收益，未拟合/评分。
- 唯一新增仓内文件为本文。公开响应暂存在 `/tmp/standard-oi-b-preflight-20261110.6z6kyK`，仅供本次复核；临时目录可能被清理，不是持久证据根或机器消费产物。
- 本文不授予下载市场 ZIP、研究运行、commit/push、部署、SSH、signal、paper/live 或 execution 权限。

## 2. 时间边界、机制与检索覆盖

### 2.1 从 standard 自身训练边界出发

[归档人工报告](../../data/research_archives/launch_incremental_run_20261105/review_CN.md)记载：standard 情景 B 有 41 个完整 Parent，Universe 为 42 个 Parent；其详细日期列表中的最晚已知日期为 **2026-09-06**。取全部已列日期的最大值，而不是按列表显示顺序取第一项。本文未重新消费训练 CSV 或重验旧研究。

- 归档报告 SHA-256：`5f57a97d249c24c06656ee42dff4982fab1cc63742095f4ec16abb701ee3338d`。
- 本次目标是计划首次上线时间 `S` 位于 **`[2026-09-07T00:00:00Z, 2026-11-10T00:00:00Z)`** 的同机制事件，即包含 9 月 7 日至 11 月 9 日。11 月 10 日排除在外。
- 这不是盘前训练集的 2026-04-16 截止点，也不代表其他研究或人员从未接触过区间内事件。
- 机制沿用既有研究的 `crypto / standard` 方向：加密原生标的的 USDⓈ-M 永续首次上线。排除 TradFi 股票/ETF/外汇/商品、pre-IPO、pre-market、现货上市、交割合约及既有合约维护/阶段转换。
- 本轮是候选分类，不改旧 ledger 的 `confirmed` 标签；未来正式训练/测试身份去重和消费资格仍需对应契约核验。

### 2.2 官方目录与覆盖限度

使用公开 CMS 列表接口 `https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=<id>&pageNo=<n>&pageSize=50`。

| 目录 | 页数 / 条目 | 返回的发布日期范围（UTC，秒级展示） |
| --- | --- | --- |
| 48，New Cryptocurrency Listing | 第 1-4 页，200 条 | 2026-03-04 07:30:01 至 2026-10-29 11:48:52 |
| 49，Latest Binance News | 第 1-3 页，150 条 | 2026-07-10 05:00:02 至 2026-11-10 10:31:19 |

共检查 350 条目录元数据，article code 无重复，页内及页间时间顺序校验通过。350 是检索条目数，**不是研究样本数**。按标题/时间筛查首次合约上线、转换与维护公告；对 CT 和标题未标明 TradFi 的 9 月 18 日多合约公告进一步读取正文。筛查保留公告早于研究区间、但计划开盘落在区间内的情况，例如 9 月 4 日发布、9 月 7 日计划上线的 TradFi 批次。

另以 2026-09/10/11、Futures Will Launch 对官方公告做定向搜索，未增加 crypto standard 候选。搜索结果只作补漏线索，不替代官方正文。

**完整性边界：**本轮没有重建全站所有目录、全部历史正文或修订版本；目录可能存在缓存、漏收或事后变化。不能把“本范围内仅确认一个”写成“全市场绝对只有一个”。检索时可见的 11 月 10 日维护公告不计入目标区间。

## 3. 候选、排除与既往暴露

### 3.1 唯一确认的元数据候选

| Parent / child | 公告发布日期（UTC） | 计划上线 S（UTC） | 判断与剩余限制 |
| --- | --- | --- | --- |
| `6bd26adeb6f742fe88eb72faca183566` / `CTUSDT` | 2026-10-01 06:30:01 | 2026-10-01 07:45:00 | [官方公告](https://www.binance.com/en/support/announcement/detail/6bd26adeb6f742fe88eb72faca183566)列明 Underlying Asset 为 Concrete (CT)，USDT 结算永续；支持 crypto standard 候选判断。S 不是实际首笔 T0，首次成交、历史交易连续性和完整研究资格尚未验证。 |

按旧人工报告给出的训练日期边界，CT 晚于旧训练样本；这不是逐行训练 ID 复验，也不是完全未见样本证明。

### 3.2 主要排除项

| 对象 / 官方证据 | 排除原因 |
| --- | --- |
| [2026-09-18 多合约公告](https://www.binance.com/en/support/announcement/detail/3c2b63c9c3e44d40b8cec99961166fe8)：PATH、AMC、CYPH、ANET、HUT、APLD、AGPU | 标题没有 TradFi，但正文 `Underlying Equity/Index` 逐一对应 UiPath、AMC Entertainment、Cypherpunk Technologies、Arista Networks、Hut 8、Applied Digital、Axe Compute 的股票。7 个 child 属于 1 个股权批次 Parent，不能按 ticker 或标题猜成加密样本。 |
| [USDBRLUSDT，2026-09-21](https://www.binance.com/en/support/announcement/detail/533eb2f3998a43e3a34df310998bee48) | 公告明确为 TradFi，非 crypto 原生代币。 |
| [MOONSHOT，2026-09-22](https://www.binance.com/en/support/announcement/detail/7379b99aa0f349a49c3b3feca1b4bbd6)、[OURA，2026-09-23](https://www.binance.com/en/support/announcement/detail/8bd2b3a7684749bba472e71fc3ad8043) | Pre-IPO 股权永续，非目标机制。 |
| 2026-09-07、09-28、09-29、10-06、10-12、10-21、10-26、10-29 的多 TradFi 合约批次 | 目录标题明确为 TradFi，不因同为 USDT 永续而混入 crypto。相关 source code 留在本轮目录响应中。 |
| [PREDICT，2026-10-25](https://www.binance.com/en/support/announcement/detail/5ef55cf8358e4a48b2512a156e89c8e5) | 首次上线为 pre-market；不能因后来现货上市或进入标准阶段再算一个独立 standard 首次上线。 |
| Quarterly 0326 delivery、现货/bStocks 上市及既有合约费用、保证金、tick size、保护期调整 | 分别不是永续首次上线、不是目标标的/市场，或只是维护事件。ONE/TAC/BULLA 的保护期结束也不自动成为新首次上线。 |

### 3.3 CT 的既往暴露不是 unknown_metadata

CT 已在 [2026-10-02 N=3 准入 Design](../designs/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-design_CN.md)及 [2026-10-03 分机制流动性诊断 Design](../designs/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-design_CN.md)中以相同 article code 出现，[roadmap](../roadmap.md)亦记载其流动性诊断结果。

因此应披露为：**项目已知事件，已有准入/流动性研究资料；是否曾查看本次 B 情景的 p/o/y、后续价格路径及是否影响模型选择，未知。** 本轮没有打开这些旧行情根来追查收益。已有资料不证明目标收益已被看过，也不允许反过来声称“完全盲测”。

## 4. 官方归档对象存在性

仅发送 ZIP 的 HTTP HEAD，并 GET 同名 `.CHECKSUM` 文本；未 GET ZIP、解压、计算 ZIP 摘要或解析行情记录。

| 对象 | HEAD / 大小 | 官方 CHECKSUM 文本中的 ZIP SHA-256 |
| --- | --- | --- |
| [CTUSDT-aggTrades-2026-10-01.zip](https://data.binance.vision/data/futures/um/daily/aggTrades/CTUSDT/CTUSDT-aggTrades-2026-10-01.zip) | HTTP 200；8,856,452 bytes | `1718ac7e1750f50a99d65822cc966f71729afdcdd6c84d5bd9752dc228ee8aec` |
| [CTUSDT-metrics-2026-10-01.zip](https://data.binance.vision/data/futures/um/daily/metrics/CTUSDT/CTUSDT-metrics-2026-10-01.zip) | HTTP 200；7,925 bytes | `ee32771b45246ed0715e5969bc25b2503fabd8e9d64ec176f021a4afaf87a913` |

两份 [aggTrades CHECKSUM](https://data.binance.vision/data/futures/um/daily/aggTrades/CTUSDT/CTUSDT-aggTrades-2026-10-01.zip.CHECKSUM)、[metrics CHECKSUM](https://data.binance.vision/data/futures/um/daily/metrics/CTUSDT/CTUSDT-metrics-2026-10-01.zip.CHECKSUM)均 HTTP 200，摘要格式及文件名匹配。它们是官方声明摘要，**不是本轮已下载并独立核对的 ZIP 哈希**。

按现有 T0 后 25 分钟观察、最多 5 秒参考入场延迟和其后 15 分钟路径，且沿用有效锚点延迟上限时，该计划时刻的正常分支不跨 UTC 日；本轮只检查 10 月 1 日两包。不证明实际 T0、OI 最新两点、成交序列、entry/endpoint 完整或真实信息可得时间；这些结论均保留为未验证，不以 HTTP 200 填成通过。

## 5. 是否进入验证：暂缓批量工程，保留有边界的个案选项

1. **本次不支持立即建设多事件 standard 时间外验证工程。** 预期的新样本池没有在已检索范围内形成，且唯一候选已有项目暴露。不是因为 N=1 被禁止，而是它目前无法回答“总体增量是否复现”，不宜用低信息量目标驱动另一套大型管道。
2. **CT 仍可作为单事件历史外推/兼容性检查。** 若用户明确认为这个问题值得投入，先限制研究目标、暴露披露与适配成本；独立使用 standard 自身的旧训练集合和 B 协议，不借用盘前 C 系数，不与 PREDICT 合并成同机制 N=2，也不将新旧样本混合 LOPO 冒充时间外验证。
3. **复用先核实，不直接运行旧 CLI。** 现有 PREDICT 脚本的 `fit_models`、`score_case` 及旧价格/归档 helper 可以优先评估；原 CLI 固定为 18 个盘前 Parent、PREDICT/C 和特定授权，不能只换 symbol 就宣称可用。本文未验证 standard 兼容性，不要求重构已完成任务，也不自动新增框架。
4. **保留线索，不强行晋级或证伪。** 后续可低成本追加同机制公告元数据，或另行比较其他研究问题的价值。若决定计算 CT，仍需相应 Design/Plan、数据消费及运行授权；没有正向研究结果也可以交付，不以追加 A/C、基差、窗口或筛掉异常值来维持本条线。

## 6. 证据定位与实际验证

原始公开响应位于上文临时目录；CMS 文件名为 `catalog48_page1.json` 至 `catalog48_page4.json`、`catalog49_page1.json` 至 `catalog49_page3.json`；正文为 `detail_<article_code>.json`。以下摘要仅用于定位本次响应，不授予任何消费资格：

```text
e6c83bb1b0c40f8b05c5b7ae7d041a82867f317e9c1b329f61c2749749ad6926  catalog48_page1.json
92b59a2abd85e366175f45c791d45d3fb19e7038f15014c99af3305202e70903  catalog48_page2.json
08ada122607aa1b18b0ff9b5ab105f505111c4ddc6dd3ddfb533a113472aae32  catalog48_page3.json
d9a003e825b318eadd5838e9fb906dc1ec3b14fda3d6f72a9880d4c85d6e4d63  catalog48_page4.json
88a888fa4670053df3c58fe16641e61581911650f3a8e05d46326fc906e68f66  catalog49_page1.json
51a0f574d54a5b65dafc7af899774edd0e04a70255743934482b4ef9572e5c1f  catalog49_page2.json
70318686f77ddfa5987b73522cb5d8404c623d7f6ce3149ef144fcc45a2f9c4d  catalog49_page3.json
12300cfcf07f2ecebc2fe9d502131ef6b560772ca6fb0fbe78d51c0ed32ed7a6  detail_6bd26adeb6f742fe88eb72faca183566.json
22a8424ac56180182268e91f053991ab3b8296bbe4c0e6fbc632a99e2ca72199  detail_3c2b63c9c3e44d40b8cec99961166fe8.json
```

- 13 次官方 `curl` 请求：7 次目录 JSON、2 次正文 JSON、2 次 ZIP HEAD、2 次 CHECKSUM GET；均实际返回 HTTP 200，curl RC=0。没有市场 ZIP 下载请求。
- 临时元数据检查：验证 JSON 成功状态、目录 ID、各页 50 条、页内/页间顺序、350 个唯一 article code、CT 公告日期/标的、9 月 18 日股权表头及七标的、两份 CHECKSUM 文件名/摘要格式和 HEAD 大小；RC=0。
- 临时目录没有 `.zip` 文件。未运行研究脚本、pytest、历史收据 loader、独立 Schema verifier 或真实交易接口，不将未运行检查写成通过。
- 本轮结论仅为检索范围内的候选与对象级覆盖，不是 Alpha 结论、完整数据准入或交易建议。
