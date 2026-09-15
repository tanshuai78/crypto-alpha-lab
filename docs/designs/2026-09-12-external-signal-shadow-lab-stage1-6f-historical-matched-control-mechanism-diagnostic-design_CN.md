# Stage 1.6F：历史下架匹配控制组与机制诊断 Design

Status: `draft_for_review`

Date: 2026-09-12

Workspace baseline: `84d6b093dcdb950e190844ca69718fee9f3c21cf`

Authority: 用户允许起草 Design candidate；不是 Design 批准、Plan、implementation、commit、deployment 或 runtime authority。

## 1. 核心问题与结论边界

本阶段回答：**相对于相似的正常合约，下架公告附近是否出现不同的价格、流动性、资金费或基差变化；现有证据是否足够支持继续研究？**

不回答“现在应该做空哪个币”“能赚多少”“哪种策略已验证”。两个窗口是待检验的机制窗口，不预先命名为两个已存在的 Alpha 窗口。历史公告封签解决来源与语义可信度，不自动解决当时可知性、历史行情覆盖或可成交性。

本候选冻结研究问题、证据门槛和最小匹配方法。当前缺少已核实的历史输入与行情接口契约，见 Section 13；在关闭这些阻断项前，不进入 Implementation Plan。不得由 Plan 作者临时猜测数据源或补造 schema。

## 2. 已确认事实、假设与选择

### 2.1 当前工作区事实

- 1.6B/C 的历史路径保留 `capture_mode=historical_backfill`、`capture_time_status=historical_unknown`、`fact_available_at_ms=null`、`system_available_at_ms=null`、`point_in_time_replay_eligible=false`。它们不是实时可用性证据。
- 已直接核对本基线 source bytes：`stage1_6a_sealed_export_adapter.py` SHA-256 为 `44f9fc7ebecd7441076109853b1fd3e2976f1b7b20eb15977ae856e60d98838c`，`stage1_6a_sealed_export_adapter_storage.py` SHA-256 为 `b6964b47750bcb2c6e7fb5039cf77129b883f9e925dd7c2ed38d589d2cdedafd`。`load_completed_adapter_audit(project_root, output_root, source_export)` 会核验完成清单、来源绑定、语法版本并重算语义产物；成功时 `permitted_design_options` 包含 `write_ex_post_diagnostic_design_only`，不包含交易回测权限。它只返回 `completion_manifest`、`summary`、`receipt` 三个顶层对象，不返回 retained event bytes。
- 2026-08-24 C H2 completion audit **记录**了 35 个候选公告、30 个历史事件、30 个事件日、44 个 symbol。此为文档记录，不是本轮重算结果，亦不证明覆盖“所有年份全部下架”。本轮未发现本地 `data/external_signal_shadow/stage1_6b/` 或 `stage1_6a/` 输入目录，不能宣称历史数据已独立验证。
- E-A 验证了 depth、premiumIndex、fundingRate、openInterestHist 四类 REST profile 的能力；这不保证过去每个下架标的的数据仍可获取。
- E-B 的 `event_window_started_at_ms` 等于已持久化语义投影的 `semantic_projected_at_ms`；窗口为该时刻起 12h，而非公告发布起 12h。E-B 未实现临近下架的第二段唤醒。当前代码的每事件最多 3 symbol / 全局一个 active event 限制不在本 Design 修改范围。
- 路线图仍将 E-B 写为 `not_started`，与当前代码及文档不一致；本轮不修改路线图，也不据其旧状态否定代码存在。本轮未 SSH，用户报告的 VPS 状态不是本轮独立运行验证。
- Graphify 当前 Python 环境不可用；已有图谱不能证明对应本基线。使用源码和 `rg` 核对 loader、时间字段及权限，不生成或更新图谱。

### 2.2 研究假设，不是事实

H1：公告后的流动性/资金费变化可能区别于同时间相似合约。H2：临近结算的基差路径可能表现出规则相关的变化。两者均允许“不支持”“数据不足”或“仅相关性”结果。

盘口变薄不能单独证明做市商撤单，OI 下降不能单独证明哪一方被迫平仓，价格上冲不能单独证明 short squeeze。没有订单流、持仓或清算证据时，输出只能称“与机制相容的现象”，不得称因果识别成功。

### 2.3 方案选择

| 方案 | 取舍 | 决策 |
| --- | --- | --- |
| 只等待 VPS 新公告 | 可增加实时样本，但不能补齐历史控制组、公告前基线或终端窗口 | 不作为 F 的前置等待条件 |
| 先冻结历史证据与匹配诊断协议 | 复用 C 来源验证；数据不足可明确停在诊断层 | 本候选采用 |
| 立即建设历史下载、双窗口采集和交易回测 | 同时引入数据源、调度、执行假设及权限扩张 | 不采用；需要另外提出需求与批准 |

## 3. 父级约束与代码事实绑定

以下 SHA 为本轮计算的文件 bytes；不以文件名、头部状态或本表替代外部审批记录。若后续核验不一致，停止消费，不改父文件适配 F。

| 参考约束 | Repo-relative path | SHA-256 |
| --- | --- | --- |
| B 官方来源/历史与实时分离 | `docs/designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md` | `83aaa473a9ddb287ee916eae4da327966daa7b0afd5c465f7cc883a06e4f6bc0` |
| C sealed-export consumer | `docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md` | `1cb90f89113ceda4d2037cb62d60b8a9f769f7d58c467ad0e515332bc13563fd` |
| C derived-artifact exact schema | `docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-adapter-derived-artifact-schema-delta-design_CN.md` | `2572849bf7df9154170ebc28f9687315728566a7c9498153f346d61308aaeb34` |
| B terminal-status field correction | `docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6b-terminal-status-field-contract-correction-design_CN.md` | `4bc7bc60a5435f9d71735319eac0dc84bf655bd94bc5f065652545f472596aae` |
| C H2 grammar delta | `docs/designs/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-design_CN.md` | `f31e9a64f42fcd1eccfab94efa5c9328fbdc154a9ae70880e359bfc701306987` |
| E-A capability boundary | `docs/designs/2026-08-30-external-signal-shadow-lab-stage1-6e-a-market-data-source-capability-audit-design_CN.md` | `8703e4804fe924b5b43ad1b431d1ffc2239b045510bea2fae94ab1305c1cead3` |
| E-B fixed-window observer | `docs/designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md` | `752aecff8735f22513483e6bf65ae991386f46ff2ae953da44cd1fe9c5898583` |
| E-B remediation delta | `docs/designs/2026-09-04-external-signal-shadow-lab-stage1-6e-b-completion-remediation-delta-design_CN.md` | `145bbb7d84e4d7ae4fc9e901b293b8520b3b825d1377f96d02bff8b8dc67ee44` |

对 F 的 C-side authority precedence 是：C v2 completed-consumer contract + C derived-artifact schema delta + B terminal-status correction + C H2 grammar delta。前者共同定义 completed root、`source_audit_eligible`、`contract_id`、资产/合约字段与其 provenance；terminal-status 只能读取 `terminal_reason`，不得使用 `reason` alias；H2 定义持久化 grammar。F 只接受这组 exact authority 所定义的 schema，不得消费其他历史 copy、旧 fixture grammar 或自行补齐 asset/field compatibility alias。

代码定位：`src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py` 的 `load_verified_source_snapshot`、`reduce_verified_snapshot`、`_make_schedule_fact`；同目录 `stage1_6a_sealed_export_adapter_storage.py` 的 `load_completed_adapter_audit`。这些是本基线事实，不是新增 mutable scope。若准备改变其权限或 schema，停止并另行审查。

## 4. Scope 与契约影响矩阵

包括：历史事件母表、逐事件证据可用性、事件前匹配控制组、W1/W2 分开的描述性机制诊断及结论限制。

不包括：新增下载器/API、修改 B/C/D/E producer、E-B 终端唤醒、策略入场/退出/仓位、净收益/胜率/MAE/MFE 回测、下单/借币、修改 1.5、以新规则升级旧 artifact 权限、增加后台服务或通用研究框架。

| 边界 | Producer / writer | Loader / consumer / reviewer | F 处理 |
| --- | --- | --- | --- |
| 官方公告与历史封签 | 现有 B | C canonical loader | 全部只读；不拼接多个 root 成假封签 |
| C 完成语义与 denominator | 现有 C | `load_completed_adapter_audit`，后续 F | 按 4.1 的 retained-byte transaction 消费；禁止 summary-only 或验证后 reopen-path 解析 |
| 历史行情/合约 universe/规则版本 | 尚未完成本轮输入核验 | source-specific verifier 尚待 Section 13 冻结 | 缺失明确记账；不得默认为 E-A 已覆盖 |
| E-B 实时原始观测 | 现有 E-B | 其既有契约；本版 F 不直接接入 | 仅作覆盖能力参考，未来接入另定消费契约 |
| F 诊断产物 | 未来只读离线程序，尚未授权实施 | 独立 reviewer | 保留来源/排除原因，不能写回上游 |

F 对 C 的新增消费只解释 `write_ex_post_diagnostic_design_only` 允许设计的内容，不将 C 的 `replay_allowed=false` 改写为 true。市场数据输入/输出的 exact schema 在数据源核验后补入候选并再审，不能留给实施者自行定义。

### 4.1 C → F retained-byte transaction

F 对一个候选 completed root 只允许如下顺序：

1. 调用 `load_completed_adapter_audit(project_root, completed_root, source_export)`；任何异常或返回对象中 `completion_manifest.source_audit_passed is not True` 都是 `source_invalid`。
2. 只使用该调用已返回、已验证的 in-memory `completion_manifest` 解析 artifact metadata；不重新打开或重新解析 `completion_manifest.json`。其 `authoritative_artifacts` 必须恰好列出下列九个 relative path，且每项有唯一 `relative_path`、nonnegative `byte_length` 与 SHA-256：`source_export_receipt.json`、`audit_candidate_manifest.json`、`parent_audit_outcomes.jsonl`、`detail_revisions.jsonl`、`semantic_extractions.jsonl`、`delisting_notices.jsonl`、`delisting_contracts.jsonl`、`audit_diagnostics.jsonl`、`stage1_6a_futures_delisting_source_audit_summary.json`。缺失、重复、额外条目或路径逃逸均为 `source_invalid`。
3. 对这九个 manifest-listed path 各读取一次，立即在内存中检查 exact byte length 与 SHA-256；所有 checks 通过后形成一次性 `verified_artifact_bytes`。F 只从这份 buffer 解析 event master、parent outcome、revision、semantic、notice、contract 和 diagnostic rows；不得在 semantic consumption 时 reopen path。
4. 任一 artifact 的 path/hash/length/JSONL 解析/schema 失败，或 F 的一次读取所得 bytes 与 returned manifest metadata 不一致，都使整份 C 输入 `source_invalid`，且 market reducer、matching reducer、F writer 均为零调用。retained bytes 已经通过后发生的同路径外部改动不得影响 F；F 不接受 partial C root、备用路径、旧 fixture 或 summary fallback。

这条 transaction 不修改 C producer/loader；它只冻结 F 在 C loader 不返回 retained bytes 时的 downstream read-after-verify 行为。市场数据仅在这条 transaction 完成后才可进入本 Design 的独立 provenance gate。

## 5. 事件母表与时间契约

### 5.1 母表不能只包含“有行情的成功样本”

先从经过完整验证的 C `audit_candidate_manifest.json` 和 parent outcomes 重建全部候选公告 denominator，再关联其 detail revision、semantic extraction、notice、contract。保留不在范围、解析失败、时间缺失、revision conflict、行情缺失及无控制组的条目与原始原因。C 失败的 root 不能贡献通过样本。

通过 root 也不能覆盖逐行 eligibility：匹配必须要求同一 verified parent 的 `source_integrity_parent_pass is True`、`detail_authority_status=trusted`、`parent_declaration_status=complete`、`mapping_status=pass`、`classification_status=in_scope`，以及所关联 child 的 `source_audit_eligible is True`。不完整/冲突 parent 全组仅保留 denominator，不因某个子合约行情或元数据齐全而恢复资格；不得新增一个并不存在的 parent eligibility 字段代替上述检查。

研究子行沿用 C `contract_id`，同时保留 export ID、completion manifest SHA、parent article ID、detail revision ID、semantic extraction ID、symbol、quote/settlement asset、margin family、contract type、underlying family。不同 revision 不作为独立事件增加样本数；出现同一 symbol 多次通知/重上架而无法确认生命周期时，该组保留但不进入匹配统计，禁止自行按时间“猜最新”。

首版匹配对象限已核实的 Binance USD-M crypto perpetual，同 quote asset、settlement asset 和合约类型；不混入 COIN-M、现货移除、杠杆借贷下架、TradFi 或仅凭标题归类的记录。C 语义标签不是独立的历史合约元数据替代物；两者冲突为证据不足，不修改 C 标签。

### 5.2 各时间有独立含义

| F 概念 | 来源/含义 | 禁止替代 |
| --- | --- | --- |
| `Tpub` | C 已验证的官方 publication timestamp；缺失则 W1 不可评估 | 不取下载、mtime 或本次审查时间 |
| `Tavailable` | 事实当时确已可用的独立证据；历史 C 输入保持 null / historical_unknown | 不赋值为 Tpub |
| `Tsettlement` | C `settlement_time.timestamp_ms`，要求 `fact_parse_status=present` 且关联证据有效 | 不取 last trading / order restriction / delisting complete |
| `Tcapture` | 实时采集实际开始时间，若引用覆盖说明则单列 | 不回填为 Tpub 或补造之前快照 |
| 行情时间 | 原始数据定义的 exchange/event time；bar open/close、观察时间和抓取时间分列 | 不把抓取时刻当历史有效时刻 |

所有时间 UTC epoch milliseconds，exact integer，bool/string 不作为时间；按来源规定转换单位且留记录，不能凭数值长度猜测。时间冲突保留原因，不静默取 min/max。C 中其他 schedule facts 为 not_stated 时保持未知。

W1 = `[Tpub, Tpub + 12h)`；W2 = `[Tsettlement - 24h, Tsettlement)`。两窗口重叠要标注，不能当成独立证据计数。若 Tpub 晚于 W2 起点，W2 公告前区间仅是事后诊断，绝非当时可以提前交易。Tsettlement <= Tpub 为异常样本，不做正常双窗口比较。

为避免匹配特征与被比较结果重叠，W2 的公告前部分只作未匹配原始描述；W2 配对诊断限定为 `[max(Tpub, Tsettlement - 24h), Tsettlement)`。若发生截断，必须显示原窗口、实际配对区间及截断原因，不得称完整 24h 配对结果或窗口覆盖完成，亦不得换控制组来补齐。

如停止交易早于窗口末尾，仅报告真实可观察子区间及缺口，禁止延长最后报价、插值穿越停牌或将缺口记为零摩擦。E-B 的实际窗口与 W1 不同，覆盖交集不能标称覆盖整个 W1。

## 6. 最小匹配控制组协议

以下数值为本候选的研究设计选择，不是已经验证的经验规律。批准前可修改；批准后不得按结果调参。

1. 每个公告使用当时历史 universe，不使用今天仍存活的 exchangeInfo 列表。控制合约在 Tpub 时属于同市场/quote/settlement/type，已存在至少 7 个完整日且尚未停止交易；排除本公告所有标的、同 underlying 以及 Tpub 前已公开宣布下架的合约。无法核实 universe 和排除信息的样本为 `control_universe_unverified`，不以“没找到公告”当作“未宣布”。
2. 特征截止 `E = floor(Tpub / 3600000) * 3600000`，仅用 `[E - 7d, E)` 的 168 个连续完整 1h bar。不得使用 Tpub 所在未完成 bar 或事件后数据。每 bar 正价格、有限值、非负 quote volume；缺失、重复冲突、零波动或零中位成交额导致该合约不进入匹配，不填补。
3. 只用两个可核验特征：168 个 `ln(close/open)` 的 population standard deviation，以及 168 个 hourly quote volume 的中位数。市值不作为首版必选维度，因为当前没有冻结历史市值来源；不以当前市值代替历史值，也不把成交额叫市值。
4. 对每个候选，波动率和中位成交额与事件合约的比率均须在 `[0.5, 2.0]`。距离为两项比率的 `abs(ln(ratio))` 之和；按距离、canonical symbol 字典序排序，选择前 3 个，数量为 1–3，等权；0 个则 unmatched，不放宽门槛“凑数”。本数值 3 是离线匹配选择，不是 E-B capacity 限制。
5. 匹配集合在公告锚点冻结，W1/W2 共用，不能为终端窗口重新选择事后最合适对照。后续控制合约遭公告、停牌、产品规则变化或数据缺口时，受影响指标只保留此前共同可观察区间并记录 censor；禁止临时替换、重新分配权重或以未来存活状态预筛。
6. 匹配是事后可重复的统计对照，不消除未观测混杂，也不制造 PIT 权限。相同行情来源与采样规则必须同时用于事件与控制组；不同 granularity 不直接合并。

统计展示保留公告级、symbol 级和 unmatched denominator；多 symbol 公告不是多个独立冲击。第一版只给逐公告配对差与分布，不做显著性、因果或收益结论。C 的 30-event source sufficiency 门槛不作为 F 的统计功效标准。

## 7. 两窗口的证据门槛与研究对象

| 对象 | 必要证据 | 可支持结论 | 不足时 |
| --- | --- | --- | --- |
| 公告后价格相对变化 | 同步历史价格、事件前基线、合格控制组 | 标注 ex-post 的相对价格路径 | 无对照只可原始描述；不可称超额收益 |
| spread / visible depth / 静态冲击 | 当时 L2 原始 bytes、正确 bid/ask、时序/单位/有效性、同频控制数据 | 瞬时可见流动性差异；静态 proxy | 只有 OHLCV 则该项 unavailable；不能推算真实滑点 |
| 资金费压力 | 逐次实际 funding timestamp/rate、规则与 symbol 历史关联 | 资金费方向、频次、费率序列 | premium/lastFundingRate 不能代替完整实际结算序列 |
| OI 联合变化 | 当时 OI、计量单位、价格/时间对齐 | OI 与价格/基差联合变化 | 不推断被迫平仓方向或清算规模 |
| W2 基差路径 | 同期 perp price、mark、index 的独立定义与序列 | 分开看 `10000*(perp/index-1)` 与 `10000*(mark/index-1)` | 不能把 mark 当可成交价格；无 index 就不算基差 |
| 终端结算机制 | 每事件适用规则、规则生效时间及来源、正式结算值或足够分辨率的规则输入 | 规则相关结算差异的事后诊断 | 仅有最后价不能声称验证结算收敛 |

不得把上述缺项累计成一个虚假的“全部行情覆盖通过”。每个 event / symbol / window / metric 单独给分母、期望/实际区间、缺口与结论级别。具体 sampler、最大时间偏差、覆盖阈值和输出公式须随真实行情 profile 在 Section 13 关闭前冻结；本候选没有授权实施一个猜测参数的 reducer。

资金费与借币利息分开：USD-M perpetual 的 funding 不是现货杠杆借币利息；不加入不存在的借币腿。负 funding 表示空头向多头支付，周期不能写死为 8h；本阶段只描述费率与结算时间，不计算假想持仓净 PnL。[Binance funding rules](https://www.binance.com/en-AE/support/faq/detail/360033525031)

终端收敛是待检验假设，而非结算制度保证可成交套利。例如官方 2024-11-04 公告规定自 2024-11-11 08:00 UTC 起相关结算从此前一小时逐秒指数均值改为半小时均值，且适用于下架合约。因此不能用统一的“最后一刻现货指数”解释所有历史事件。该网页仅支持设计理由；实际输入仍须冻结每事件适用规则与原始证据，不从本次联网阅读获得历史 authority。[Settlement price calculation update](https://www.binance.com/en-AE/support/announcement/detail/4bcabddf0e81423ebca242e185bf157d)

## 8. Fail-Closed 与结果顺序

先 source integrity，再语义/时间与 denominator，再 market provenance/coverage，再匹配，再各项描述性诊断；不得先计算漂亮指标再补来源检查。

| 条件 | 结果与后续 |
| --- | --- |
| 必须的 B/C bytes 缺失、C verifier 失败、4.1 的 artifact path/hash/length/schema transaction 失败，或 verified completion manifest 的 `source_audit_passed` 非 exact true | `source_invalid`；不运行匹配或市场 reducer，不产生通过报告 |
| 来源合法但某事件时间/类型/生命周期证据不足 | 保留事件和原因；阻断该项消费，不修改其他合法事件 |
| 市场数据未提供/不可取得或对照不足 | `diagnostic_incomplete`；允许缺口清单，不允许成功覆盖声明 |
| 已提供的数据 hash/schema/身份冲突 | `market_evidence_invalid`；对应输入所有依赖指标停止，不降级成普通缺失继续算 |
| 某 window/metric 所需证据和对照齐全 | `descriptive_only`；仅该项可计算，不提升全 root 或其他指标 |
| 所有预先声明的 window/metric 证据齐全且没有截断，均有合法评价结果 | 可报告“诊断协议执行完成”；不等于机制成立、Alpha 或执行可行 |

不得以删掉不可评估指标缩小预先声明的集合后声称完成；空事件集、全 unmatched、全 unavailable 均不能成为正面研究结果。不支持假设的合法结果必须保留，不因方向不符合期待而排除。

## 9. 持久化、兼容性与 Fixture

本轮交付只有本 Design，尚无 F writer/schema 或运行产物；因此本轮 crash/restart、迁移和部署为 N/A。未来实现必须离线读取固定快照并使用新的独立输出目录，不能就地更新 B/C/E 原始 root 或历史报告。

实施前需冻结 F exact input/output schema、闭合 manifest 与实际 reader。F 的 C input identity 是 4.1 returned completion-manifest 的 in-memory fields（含 source export ID / manifest hash）、source-export receipt SHA、九个 artifact metadata 与 retained bytes SHA，而不是 completed-root pathname。completion-manifest 文件 bytes 的 SHA 可作为离线 Reality Snapshot 证据记录，但 F 不为取得它而 reopen 该文件。要求每项输出可追溯到这些输入、时间锚点、匹配参数和排除原因；完成标记最后发布，中断/缺文件/输入变化不能被 consumer 当成完成。相同输入与参数的语义结果可重算，不通过增加数据库、队列或后台 daemon 解决纯批处理问题。

真实 fixtures 必须来自重新验证的 B/C export 和有明确来源的行情 raw，记录 hash 与提取规则；合成数据必须标为 synthetic，只证明逻辑，不证明历史覆盖、市场统计或 Alpha。不能用作者手写的成功 summary 代替 producer → persisted bytes → consumer 的测试。

历史非 PIT artifact 保持原权限与原 bytes，不迁移成实时证据。若未来要接入 E-B 或建设 terminal observer，另行冻结接口与审批，不把本 Design 当隐含扩展授权。

## 10. Acceptance Invariants 与最小验证

以下为后续 Plan 的 mandatory matrix；本轮未运行它们，不能把设计中的 fixture 要求写成已通过测试。

| ID | 不变量 | 最小 positive / negative / boundary proof |
| --- | --- | --- |
| INV-F01 | validated C bytes == F parsed bytes == F consumed bytes | 真 export + C completion 正例；在 loader return 后替换/截断任一九个 artifact 或仅交 summary，4.1 hash/length gate 必须在任何 market/matching/F writer 调用前失败；parser 只能接收 retained buffer，不能 reopen path |
| INV-F02 | Historical 不升级成 PIT | 正例 null availability 原样保留；试图用 Tpub/下载时间替换或打开 replay 权限必须拒绝 |
| INV-F03 | 母表与排除原因不丢失，逐行 eligibility 不被 root PASS 覆盖 | 同一 fixture 含通过、失败、无行情和 unmatched；逐父公告重算总数；通过 root 含不完整批量公告时所有对应子行仍不可匹配；删失败行不得通过 |
| INV-F04 | W1/W2 与 E-B 实际窗口分开 | exact 左闭右开边界、窗口重叠、Tsettlement<=Tpub、采集迟到、停牌缺口；Tsettlement=Tpub+12h 时 W2 公告前 12h 只能原始描述，配对结果为截断窗口，不能声称完整 W2 |
| INV-F05 | 匹配只用事件前且非幸存者 universe | 改 Tpub 后价格不能改变原匹配；使用当前 universe/未来存活筛选必须失败 |
| INV-F06 | 匹配规则确定且不凑数 | 0/1/3/4 候选、比率边界、排序并列、缺一根 baseline bar；后续控制污染不得替换或重新加权 |
| INV-F07 | 不以便宜数据冒充昂贵证据 | OHLCV 不能启用 L2 指标；mark 不能启用可成交价结论；费率预估不能冒充实际资金费 |
| INV-F08 | 结算规则按历史事件关联 | 跨规则生效边界正例；缺规则/错误规则/缺逐秒输入不得“用最后价补齐” |
| INV-F09 | 多币公告不增加独立冲击数量 | 单公告三币与三公告单币区分；revision 重复不翻倍；展示 matched/unmatched 分母 |
| INV-F10 | 失败不能被输出包装掩盖 | hash 损坏、零事件、全部缺数据、缺完成标记、写入中断均不能形成有效完成 bundle |
| INV-F11 | 生产路径不是 fixture-only | 真实 C loader → returned manifest → retained manifest-listed bytes → F；冻结输入改动与 extra/unlisted artifact 都被检出；重复离线读取语义一致 |
| INV-F12 | 零权限与无上游副作用 | source tree hashes 不变；禁止 network/order/execution 调用；输出 flags 非 exact false 即拒绝 |

Window/metric 计算与 writer 的完整 mechanical matrix 要在 Section 13 关闭时一并加入；目前不宣称该候选已满足实施级接口完整性。

## 11. Safety 与 Authority

`RISK_LIVE_TRADING_ENABLED`、`trade_signal_allowed`、`paper_trading_allowed`、`live_trading_allowed`、`execution_engine_allowed`、`private_api_allowed`、`authenticated_api_allowed`、`order_api_allowed`、`alpha_interpretation_allowed`、`execution_feasibility_claim_allowed`、`net_cost_or_profit_claim_allowed`、`replay_allowed`、`point_in_time_directional_replay_allowed` 均保持 false。这里只声明限制，不向旧 artifact 新增字段。

本轮不改变任何 config、风险阈值、已有 parser/loader，也不执行网络采集、SSH、VPS 停启或运行 observer。公开规则网页查阅仅作 Design 参考，不代表采集授权。任何后续实施需要独立批准的 Plan；部署与 runtime 另行授权。

## 12. 成功标准与停止投入条件

F 的成功是能够解释“哪些事件、哪些窗口、哪些机制有合法可用证据，匹配后观察到什么，以及哪些仍不知道”，不是必须得到正 Alpha。只要来源或核心行情缺口未闭合，就停在 `diagnostic_incomplete`，不能以继续修 collector 作为默认解决办法。

投入顺序：先找到并重验 B/C 原始封签，再对真实样本核实历史行情与 universe 可用性，最后决定是否值得实施配对诊断。若核心历史数据不可恢复，记录该机制不可识别并交给 1.6G 决定停止或保持诊断；不为追求阶段 PASS 重建无授权采集平台。若描述结果值得继续，仍须单独提出 PIT/策略/成本模型 Design。

## 13. Open Questions 与下一步门禁

| 未决项 | Owner | 是否阻断 Plan | 最小关闭证据 |
| --- | --- | --- | --- |
| B export + C H2 completed root 当前物理位置及可重新验证性 | 用户提供存放位置；A 在本地只读核验 | 是 | `SOURCE_EXPORT` 与 `C_H2_COMPLETED_ROOT` exact path；`load_completed_adapter_audit(project_root, C_H2_COMPLETED_ROOT, SOURCE_EXPORT)` 成功结果；returned completion manifest 与 source-export receipt SHA；九个 authoritative-artifact relative path/SHA/byte_length；随后按 4.1 重读的 retained-byte checks 及 denominator。不是再次贴历史结论 |
| 历史 universe、价格/指数、funding、OI、L2、结算规则中哪些有可验证来源 | A 做能力盘点；若需外部新采集由用户另行批准 | 是 | source-specific schema/时间/单位/raw provenance、真实样例、覆盖缺口；明确不可取得的数据，不承诺全量 |
| 基于上述实际输入的 F exact schema、对齐/coverage/reducer/output 契约 | A 修订候选，B 审核，用户批准 | 是 | 消除接口未知并补全 Section 7/9/10 的机械预期；不能交由 Plan 重新设计 |
| 历史 PIT 市值是否可获得 | 后续研究 owner | 否 | 首版匹配不依赖市值；增加该特征须独立修订，不静默 fallback |
| 是否需要第二段实时 terminal 采集或交易策略 | 用户未来需求 | 否 | 当前明确不实施，不影响本版协议 |

当前：`design_review_allowed=true`；`trust_boundary_frozen=false`；`implementation_plan_allowed=false`；`implementation_allowed=false`；`deployment_allowed=false`；`runtime_action_allowed=false`。本候选可供讨论与审查，不能仅凭“允许写 Design”推导输入已通过或下一阶段已获授权。
