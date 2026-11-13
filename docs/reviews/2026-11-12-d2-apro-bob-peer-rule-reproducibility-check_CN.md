# D2 APRO / BOB 历史同行规则复现检查

日期：2026-11-12（Asia/Shanghai）。性质：有限元数据诊断及人工决策参考，不是新 Universe、关系数据库、正式 Design、机器输入或 Alpha 证据。

## 1. 结论

**可以继续低成本讨论 D2，但本轮不直接扩展十个 Parent，也不开始行情研究。APRO 在给定候选及共同证据包内能够复现原三项；BOB 尚不能确认唯一集合。**

| 检查问题 | 本轮结果 |
| --- | --- |
| APRO 的业务分类与截取是否可重复 | 补齐共同来源后，六个给定候选均支持预言机同功能分类；按原优先级和名称排序，得到 BAND、LINK、DIA，与原名单一致 |
| BOB 的原三项是否唯一 | 未证实。B2、Merlin 是原报告已披露但未完成同等级比较的线索；新增证据并不允许覆盖原锁定名单 |
| 是否发现实际业务判定冲突 | 尚未证明独立复核者在相同完整证据下给出互斥名单；最初部分差异来自未找到同一来源，不能冒称规则已被证伪 |
| 是否发现资产可比性问题 | 是。Rootstock 的 RBTC 是 BTC 锚定资产；项目同业务不等于代币具有相同重估逻辑 |
| 是否证明候选发现可重复 | 否。独立复核者收到有限候选池，不是从零盲找全部同行；不能外推行业覆盖率 |
| 是否取得收益或交易证据 | 否。本轮没有行情下载、收益计算、交易成本测量或 Alpha 判定 |

最有用的结果是区分了三个环节：**先找到哪些候选、如何判定业务关系、选中资产代表什么经济风险。**不能只靠最后的字母排序解决前两个环节，也不能因一个 Bitcoin 标签把不同资产等同处理。

## 2. 本轮范围及复核方法

依据用户“按照你的建议开始下一步”，执行此前建议的第一步：只检查 APRO、BOB，保留原五 Parent / 七 child 与原同行名单，不自动扩样。上游依据为[讨论备忘 §6.1](2026-11-12-launch-event-data-research-directions-discussion_CN.md)及[原预审报告](2026-11-12-launch-peer-spillover-metadata-preflight_CN.md)。

- APRO 公告截止：`2025-10-29T09:36:15.831Z`；BOB：`2025-11-21T09:28:51.171Z`。沿用原报告，不重新读取分类账本或 J-A/J-B，不重新排序 Parent。
- 本轮新资料检索前，登记 APRO 六个候选：Band Protocol、Chainlink、DIA、Pyth Network、RedStone、Tellor；BOB 五个候选：B2 Network、Bitlayer、Merlin Chain、Rootstock、Stacks。
- 这十一项来自原报告的已选对象及明确披露的未审线索，不是新增完整行业 Universe。保留原“直接竞品优先、同核心业务其次、原始资料优先、同级名称及资产标识排序、最多三个、不按行情覆盖替换”规则。
- 一个不继承前文的独立助手复核业务分类，未提供旧选择标签、收益或原报告；主审核查资产角色、公开来源和结论边界。随后只针对 DIA、PYTH、Stacks 补充共同来源，复核检索差异是否消失。
- 独立助手不是外部 Model B，也不承担正式批准；本轮是一次条件复核，不是统计意义的多研究者一致性检验。主审知道旧名单，不能将整个过程称为双盲。

## 3. APRO：给定证据包下可以复现，但不是行业前三强

[APRO 署期 2025-10-24 的发行方文章](https://medium.com/@APRO_Oracle/at-tokenomics-unveiled-building-a-sustainable-value-ecosystem-for-next-generation-oracle-3eb4ebad85d9)描述将现实数据传递到区块链的预言机服务，并列出 AT 的 BNB Chain 地址，与原报告所识别的 APRO 资产一致。它补充了原先 Nervos 材料之外的项目自身业务及代币线索。

| 给定候选 | 本轮打开的原始资料及署期 | 业务层判断 |
| --- | --- | --- |
| Band Protocol / BAND | [Sonic 预言机集成，2024-10-04](https://blog.bandprotocol.com/bandprotocol-sonic-oracle-integration/) | 为 dApp 提供外部数据馈送，同功能支持 |
| Chainlink / LINK | [白皮书 v1，2017-09-04](https://research.chain.link/whitepaper-v1.pdf) | 连接智能合约与外部数据，同功能支持 |
| DIA / DIA | [DIA 发行方新闻稿，2021-11-09](https://www.globenewswire.com/news-release/2021/11/09/2330743/0/en/dia-association-launches-an-oracle-integration-with-solana.html) | 向应用提供预言机服务，同功能支持；新闻分发平台不改变发行方材料属性 |
| Pyth Network / PYTH | [官方主网与治理文章，2023-11-16](https://www.pyth.network/blog/permissionless-mainnet-token-led-governance-are-live) | 聚合金融数据供链上应用使用，同功能支持 |
| RedStone / RED | [模块化预言机说明，2024-07-27](https://www.redstone.finance/blog/what-is-redstone-modular-oracles-for-defi/) | 向 DeFi 应用提供数据服务，同功能支持 |
| Tellor / TRB | [Layer 主网开放，2025-08-04](https://tellor.io/blog/layer-mainnet-open-to-public/) | 为开发者提供现实数据验证，同功能支持 |

本证据包没有核实哪一项被公告前材料明确识别为 APRO 的直接竞争者，不能凭研究者觉得“更像竞品”提升优先级。将这六项置于相同功能及原始材料层级时，历史英文名称排序为 Band Protocol、Chainlink、DIA、Pyth Network、RedStone、Tellor，前三项与原锁定集合一致。

**这是条件复现，不是唯一最优篮子：**没有证明全行业只有这六个候选、任意研究者独立检索均会发现它们，或字母靠前的三个具有更强经济关联。字母序只是消除并列自由裁量，不代表关系强度、代表性或收益排序。其他三项也不能继续被描述为“没有同等级业务依据”。

所有日期均来自本次可访问材料的署期，而非独立认证的历史页面版本。它们支持有限的历史关系线索，不构成全部来源的严格 PIT 证明。

## 4. BOB：业务交集存在，候选完整性与资产可比性未闭合

[BOB Foundation 白皮书](https://static.gobob.xyz/BOB_Foundation_Token_Whitepaper_ATTR_V1.pdf)正文载明通知日期 `2025-10-28`、发布日期 `2025-11-06`，区分已上线 Ethereum L2 与后续 Bitcoin 安全功能计划。因此，比较“为 Bitcoin 应用提供智能合约执行服务”，不等于比较“相同虚拟机、相同结算层及相同安全实现”。不能把计划能力当成事件时已经上线。

| 给定候选 | 本轮来源及可支持范围 | 剩余问题 |
| --- | --- | --- |
| B2 Network / B2 | [2025-09-24 官方进展](https://blog.bsquared.network/b%C2%B2-network-post-tge-milestone-update-pushing-bitcoin-onto-its-next-growth-curve-891dbd3e34eb)描述 Rollup，并扩展矿业、AI、稳定币产品 | 可支持应用执行功能交集；“相同核心业务”应如何对待多产品项目，尚需统一解释 |
| Bitlayer / BTR | [2024-04-15 主网说明](https://blog.bitlayer.org/introducing-bitlayer-mainnet-v1-unlocking-the-potential-of-bitcoin-56c5fa2159fd/)支持应用构建及 EVM 项目部署 | 同功能支持；不保证与 BOB 安全架构相同 |
| Merlin Chain / MERL | [当前官方文档](https://docs.merlinchain.io/merlin-docs)及[旧活动回顾页](https://docs.merlinchain.io/merlin-docs/user-quick-start/how-to/staking-and-unstaking/staking-merlins-seal-already-concluded)支持 Bitcoin 扩容及 MERL 线索 | 回顾 2024 年活动不证明当前文档当时已公开；本轮未补齐可核实的事件前版本，保留历史证据不足 |
| Rootstock / RBTC | [白皮书修订版，2019-01-29](https://rootstock.io/rsk-white-paper-updated.pdf)支持 Bitcoin 智能合约服务 | 项目功能支持；RBTC 的经济角色与其他项目代币不同，见下一节 |
| Stacks / STX | [官方 Nakamoto 文章，2024-11-21](https://www.stacks.co/blog/optimizing-nakamoto)支持 Bitcoin 智能合约执行及开发者服务 | 同功能支持；Clarity 与 EVM 不同，不能把技术完全一致当作未经约定的条件 |

原集合 **Bitlayer / Rootstock / Stacks 保持不变**。本轮新增查明 B2 的资料不代表已经批准替换它们；也不能因 Merlin 缺证据而认定其业务不合格。若假设五项都通过同层级审查，并将给定的 B2 名称作为排序键，字母序前三将变成 B2 / Bitlayer / Merlin。该演算只是说明候选池会影响截取，**不是本轮确定的新篮子**；真实品牌名 B² 的名称规范化也不能留到看完行情后处理。

本轮没有证明 BOB 无法研究，更没有证明同行币不存在价格溢出。可以确定的只是：原三项尚不能被称为对整个候选池执行完整规则后的唯一结果。

## 5. 代币角色：关系资格不能代替经济机制

| 对象 | 查到的角色线索 | 不能据此声称 |
| --- | --- | --- |
| APRO / AT | 上述 2025-10-24 文章讨论节点质押及治理，并将高级数据服务支付列为后续阶段安排 | 不能把计划支付用途当成已实现现金流，也不能因业务相似断言 AT 与 LINK 等有相同价值捕获 |
| PYTH | 上述 2023-11-16 官方文章说明质押参与治理 | 不等于持有者自动获得预言机收入分红 |
| BOB | 上述白皮书描述网络治理、生态参与及计划中的质押能力 | 不是 BTC 的一比一映射资产；未来能力不能全部视为事件时事实 |
| Bitlayer / BTR | [官方 Tokenomics，2025-08-26](https://blog.bitlayer.org/btr_tokenomics/)描述治理、质押及需投票激活的费用开关 | 不能把条件性的奖励或回购机制当成已启动的分红 |
| Rootstock / RBTC | [Rootstock 官方说明](https://rootstock.io/blog/smart-bitcoin-3-easy-ways-to-get-rbtc/)及[发行方白皮书中的 RBTC/RIF 区分](https://rootstock.io/static/6c63424b1adab118667c0f85b44c6d65/rif-whitepaper-en.pdf)说明 RBTC 用于 gas，按 1:1 锚定 BTC 设计 | 不保证市场无脱锚或桥接风险；不能当成 Rootstock 项目股权，也不能偷换为 RIF |
| Stacks / STX | [项目白皮书当前副本](https://blog.stacks.co/stacks-2-whitepaper)将 STX 共识激励与 sBTC 锚定资产区分 | STX 不是 sBTC；当前文件不是事件时版本的独立证明 |
| B2、MERL | [B2 署期 2025-05-26 的质押/治理说明](https://blog.bsquared.network/b%C2%B2-staking-goes-live-the-journey-of-b2-begins-c25c27650692)；上述 Merlin 回顾页称 MERL 为治理代币 | 角色线索不等于完整经济权利或历史合约准入已验证；Merlin 的版本缺口仍保留 |

RBTC 官方文章虽标注 2023 年，正文包含 2024 年更新，正说明“旧署期”不能自动证明全文从未修改。本轮只把多份原始材料一致支持的锚定设计用作资产异质性诊断，不升级历史版本资格。

**研究含义属于推论：**若未来要检验的是“项目代币的同行重估”，把 BTC 锚定资产与治理/协议资产直接混合，会使篮子的经济解释混杂。可建议事前分层，但不能借本轮诊断直接删除 RBTC、用 RIF 补位或为收益结果增设筛选条件。业务相同仍可能伴随注意力扩散、竞争替代或无响应，方向尚未检验。

本节不是十一种资产的完整 Tokenomics 审计；BAND、LINK、DIA、RED、TRB 的历史价值捕获机制未逐项完成验证。也未新增任何合约存在性或行情覆盖结论。

## 6. 独立复核暴露了什么，未暴露什么

第一次独立检索把 DIA、Stacks 标为历史证据不足，PYTH 的来源仅找到竞争项目介绍。补充 DIA 发行方新闻稿、Stacks 2024 年文章、PYTH 2023 年官方文章后，复核者均修正为有署期原始材料支持，并确认 APRO 在给定证据包内可得原三项。

这三处变化是**取证差异收敛**，不能记作三次业务规则失败。原方案本就规定未知保留、不硬凑三个；本轮不采纳初稿中“是否必须取满三个尚未定义”的批评，不新增无必要的规则。

仍需注意：

1. **候选发现边界。**先知道哪些项目，会影响检索与最终名单；本轮有限候选池不能验证从零发现的重复性。
2. **功能粒度与优先层级。**“能给同类客户解决同类问题”和“技术架构相同”不同；没有成对竞争证据时，不应临时把最熟悉的项目升为直接竞品。
3. **来源取得与资产解释。**限定检索未找到历史材料应记缺口，而不是项目不合格；同业务也不能自动赋予代币相同的风险暴露。

因此，不报告“11/11 规则验证通过”、一致率或 D2 可行率，更不据两个刻意选作清晰/边界案例的项目推断全年研究产能。

## 7. 下一步建议：一次小澄清，再决定是否顺序扩样

建议下一批 Brief Plan 只补充以下简短约定，**本报告提出而未实施，也不修改已锁定方案**：

- 先为目标项目写一句事件前已提供的核心服务及服务对象，再查同行；没有明确成对竞争证据时，按同功能层处理，不按技术营销标签升降级。
- 在相同有限检索范围与时间预算内记录已发现候选及来源，再统一排序；保留超额及未知对象，规范化项目名与稳定资产身份，选定后不因合约或行情缺口换币。无需穷尽全行业，但不能把搜索先后当成排名。
- 代币角色单独标注。若未来正式研究决定仅分析非锚定的协议/治理资产，应事前明确这是新的适用范围，保留不纳入原因，并对所有事件一致执行；本轮不先按这个条件筛币。

不建议把“恢复所有历史网页版本”变成无限前置工作。有限材料可以继续支持清楚标注未知的可行性调查；严格历史可得性与交易主张另行验证，不能用假设填充成事实。

确认上述下一批口径后，可从原固定排序继续最多五个 Parent 的元数据调查，再决定第二批；总投入不超过此前讨论的一工作日，不补容易成功的样本。记录逐 Parent 耗时及主要缺口，仍不计算收益。若相同材料下的核心业务判断仍普遍依赖自由裁量，或必须建立大型行业数据库才能推进，就暂停 D2 工程，而非无限修规则。

本轮尚未扩样，也未冻结正式收益窗口、市场对照、延迟参数或成本模型。APRO 的条件复现支持“可以继续有限调查”，不支持“只留下预言机行业开展收益研究”。

## 8. 范围保护与复核线索

- 执行前 HEAD：`c467e9b043acbd5d1d8b3c8d5d03cb21aeb77760`。执行前备忘已有修改，原预审报告未跟踪；均保留，不回退、不覆写。本轮仓内仅新增本文。
- 原备忘 SHA-256：`b8d31c5a659e8d5c0fbb6a6c2469d203ba87106ab7bfeb35b6ecca9c14e11c65`；原预审 SHA-256：`40c589259a09d1d905b4ecfac67496314812167417c71b8b9390c7c8e308eaa6`。新增前与执行前副本逐字节比较均一致。
- 原 `selection_lock.txt`、`peer_lock_before_instrument_checks.md`、`archive_requests.tsv` 仍存在；本轮重新计算的三个 SHA 与原报告 §7 一致。此核对证明记录字节未变，不证明记录当时所有判断正确，也没有重放行情对象请求。
- 本轮临时目录：`/private/tmp/d2-peer-rule-check-20261112.uoaVUi`；候选范围锁定于 `2026-11-12T06:53:21Z`，`diagnostic_scope_lock.txt` SHA-256 为 `5627c5b790d1eec44d7376352f596f52152e80c1ab12a77a8342c169e504eeed`。公开资料与独立复核收束于约 `07:02Z`；其后仅整理报告。未逐 Parent 计时，不能把这一小批耗时外推全 Universe 人工成本。
- 临时目录不是持久证据根。链接及本报告记录来源、限制和决策；未创建机器 Schema、收据、通用框架或独立 Verifier。
- 未提取或计算行情、收益、相关性、模型预测；公开检索可能附带价格文字或无关同名项目，未据此选样，不作绝对“从未看见任何价格”的声明。
- 没有重新消费冻结账本、J-A/J-B 或真实研究快照；没有市场 ZIP 请求、交易、部署、SSH、commit/push 或运行时操作。未修改代码、配置或批准契约；检查配置仍为 `RISK_LIVE_TRADING_ENABLED=False`。
- 仅做文档范围、引用及差异检查，不虚构 pytest、研究运行或代码扫描成绩。本文不批准正式研究、扩样或任何交易权限。
