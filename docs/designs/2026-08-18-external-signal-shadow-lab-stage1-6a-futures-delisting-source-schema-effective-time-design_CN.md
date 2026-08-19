# Stage 1.6A Binance USD-M Futures Delisting Source / Schema / Effective-Time Audit Design

**日期:** 2026-08-18  
**状态:** `design_draft_for_review`  
**适用范围:** External Signal Shadow Lab / Stage 1.6A  
**安全模式:** `research_shadow_mode`；`RISK_LIVE_TRADING_ENABLED = False`。  
**当前授权:** 仅 Design；`implementation_plan_allowed = false`，直到本 Design 审核通过。

## 1. 结论与使命边界

Stage 1.6A 不是“下架做空策略”，也不产出 `SignalCandidate`、`TradeIntent`、纸盘或实盘指令。它只回答一个前置问题：Binance 官方公告中的 **USD-M 永续合约下架** 是否能以点时、可复现、可区分市场类型的方式被采集和审计，从而值得进入独立的后续 replay 设计。

本阶段的最小可交付物是一个只读 source audit：冻结官方原始载荷及其版本，识别产品范围，拆分公告与合约，抽取带证据的生命周期时间表，并报告价格、资金费、OI 与盘口数据是否足以支持下一阶段诊断。它不证明 alpha，也不允许以“下架必跌”作为默认假设。

```text
source_audit_passed
  != replay_allowed
  != alpha_interpretation_allowed
  != paper_trading_allowed
  != live_trading_allowed

risk_veto_candidate
  != strategy admission block
  != automatic position reduction
```

## 2. 已确认事实、假设与决策

### 2.1 已确认事实

1. 项目路线图将 `futures_delisting_notice` 定为优先事件源，但已拒绝 `announcement_plus_1h_blind_short` 与“下架必然是单边做空机会”的假设。
2. Stage 1.6A 的既定第一动作是 `futures_delisting_source_schema_effective_time_audit`；只有审计通过，才允许另写 `pre_settlement_forced_flow_diagnostic_replay_design`。
3. 当前 Stage 1.5A 已有只读原始载荷、payload hash、`available_at_ms`、source-domain allowlist 与 generic `exchange_delisting_notice` 事件类型模式；它的 title 级 `delist/removal` 分类不能单独证明 USD-M futures scope。
4. 当前 Stage 1.5D/F 正在收集 futures launch 事件。Stage 1.6A 尚无生产模块、持久化 root 或部署任务，且不得改变运行中的 Stage 1.5 root、watermark、事件流或运行进程。
5. `RISK_LIVE_TRADING_ENABLED` 当前为 `False`。本 Design 不授权任何配置值、风险阈值或执行权限变更。

### 2.2 显式假设

1. Binance 公告正文、标题、时间表与产品命名可能发生模板差异、修订或延迟可用；任何未由冻结原始载荷支持的字段都不是事实。
2. 某些公告不会陈述“只减仓/禁止开仓”、结算、最后交易或最终下架时间。缺失是合法审计结果，不允许由标题、当前 exchangeInfo 或经验规则补造。
3. 历史 USD-M K 线、资金费、OI、盘口快照和费率资料的可用性尚未证明。无覆盖的数据指标必须标为 `not_evaluable`。

### 2.3 已作决策

| ID | 决策 | 理由 |
|---|---|---|
| D-01 | 第一版只接受 `margin_family=USD_M`、`contract_type=PERPETUAL`、`underlying_family=crypto_asset` 的 futures delisting。COIN-M、TradFi equity/ETF/leveraged ETF/commodity、现货、杠杆、借贷、Convert、仅交易对移除及 `unknown` 均为 `out_of_scope`。 | USD-M 已不保证同质；不同底层资产的交易时段、价格发现、流动性和强制处理机制不能混样。 |
| D-02 | 以 `ListCapture`、`ArticleDiscovery`、canonical `DetailRevision` 和 versioned `SemanticExtraction` 分离列表变化、正文变化与解析器变化。 | 无关公告改变列表 hash、locale 切换或新 parser 都不能伪造 article revision。 |
| D-03 | 把官方发布时间、首次列表发现、原始正文到达、可信语义提取和系统可用于该语义事实的时间分离。 | 官方页可编辑、详情可延迟、parser 可升级；可交易信息时点不能事后回填。 |
| D-04 | “限制开仓”是可选、证据驱动的 schedule fact，不是每篇公告必有的 `T_reduce`。 | 不同公告可能只给最后交易或结算时间；推断会制造错误锚点。 |
| D-05 | 批量公告作为完整父 declaration；所有 child 必须被分类并核算。只有已完整核实的 in-scope child 才可评估。 | 既不因 mixed notice 丢失已证实的 USD-M crypto child，也不允许未知 child 被静默丢弃。 |
| D-06 | Stage 1.6A 只定义指标、数据前提与缺失语义；不执行方向性 replay。 | 价格方向、MAE、费用后净收益均需要独立的进场、方向、成本和退出契约。 |
| D-07 | `risk_veto_candidate` 只能是非执行诊断字段，真正的策略准入拦截留给独立 1.6R / risk-integration Design。 | 直接影响其他策略开仓属于 L0 风险变更，不能混入 source audit。 |

## 3. 范围与显式非目标

### 3.1 In scope

1. Binance 官方公告列表和详情正文的只读 source schema、版本与可用时间审计。
2. USD-M perpetual delisting 的严格产品分类、符号拆分、公告父子关系及完整性规则。
3. `system_available_at_ms`、限制开仓、最后交易、结算、最终下架等时间事实的字段语义、证据和缺失处理。
4. 后续价格、流动性、费用与资金费诊断所需的数据覆盖审计。
5. 仅供人工复核和未来 1.6R 消费的 `risk_veto_candidate` 证据标签定义。

### 3.2 Explicit non-goals

- 编写或部署新的公告 collector、Stage 1.5D parser、Stage 1.5F observer、1.5G reviewer，或修改运行中的 1.5D/F root。
- 制定做空/做多方向、进出场、仓位、止损、杠杆、订单路由、`SignalCandidate` 或 `TradeIntent`。
- 将 `$500` 的盘口估计视为真实成交保证，或以固定“千五费率”宣称净收益。
- 将 `risk_veto_candidate` 接入任何策略、风控准入、自动平仓、通知执行或交易权限。
- 使用现时 exchangeInfo、后来的公告修订或已下架后的市场状态重建历史时点事实。

### 3.3 Future Plan authority boundary

Design 获批后，后续 Plan 可以为专用、只读的 Stage 1.6A source audit 新增最少的 modules、fixtures、tests、runner 和 `EXTERNAL_SIGNAL_STAGE1_6A_*` research-audit constants。Plan 必须给出精确文件白名单，并证明与 Stage 1.5 runtime 隔离。

未经新的 Design，不得将 generic Stage 1.5 launch contract 改作 delisting transport，不得新增 replay/execution/risk-admission consumer，也不得把任何 Stage 1.6A output 接到现有策略。

## 4. 官方来源、产品范围与公告版本契约

### 4.1 Source boundary

```text
accepted source:
  Binance official announcement index + detail payload

accepted product:
  margin_family = USD_M
  contract_type = PERPETUAL
  underlying_family = crypto_asset
  all three facts explicitly supported by the canonical English detail

rejected product:
  COIN-M contract
  TradFi equity / ETF / leveraged ETF / commodity perpetual
  spot delisting
  margin / loan / convert removal
  trading-pair removal without futures settlement/delisting evidence
  unsupported or unknown underlying family
```

每个 child 必须保存 `contract_type`、`settlement_asset`、`quote_asset`、`margin_family` 与 `underlying_family`。title 只能用于候选发现，不得单独产出 `in_scope`。当前或未来的 exchangeInfo 不能作为历史 product family 的权威来源。

第一版不引入资产分类 registry。`underlying_family=crypto_asset` 必须由 canonical English detail 明确支持；无正向证据一律为 `unknown` 并排除。宁可 source audit 因样本不足失败，也不使用当前交易所目录、symbol 名称猜测或事后人工分类把 TradFi 与 crypto 混入。

`candidate_discovery_rule_v1` 固定为：从 canonical English announcement index 的一个 `ListCapture` 中，对每条 list item 的 Unicode-normalized、case-folded title 同时匹配 `binance futures` 与 `delist`。命中的 `source_article_id` 立即形成 `ArticleDiscovery` 和 append-only `audit_candidate_manifest` entry；它在 detail 获取、解析、mapping 或 classification 之前被冻结。该规则故意把最终会被证明为 COIN-M、TradFi、spot 或非下架的 title candidate 放进 audit population，防止 survivorship-by-parser。

### 4.2 Capture, discovery, revision and semantic-extraction identities

下列对象必须分离持久化；它们不是可互相替代的“revision”。

| Object | Identity / required facts | 语义 |
|---|---|---|
| `ListCapture` | `list_capture_id`、`source_surface=announcement_index`、locale、request variant、`list_raw_sha256`、`fetched_at_ms` | 一次公告列表取得。新增无关 article 造成 list hash 改变，只产生新的 `ListCapture`。 |
| `ArticleDiscovery` | `source_article_id`、不可变 `notice_lineage_first_detected_at_ms`、首次 `list_capture_id` | 一篇 article 首次被列表发现。重复出现只增加 discovery telemetry，不重置首次时间。 |
| `DetailRevision` | `detail_revision_id = sha256(source_article_id | source_surface | source_locale | request_variant | detail_raw_sha256)`、不可变 `revision_first_observed_at_ms` | canonical English detail 的内容版本。相同 hash 的再次取得属于 observation telemetry；不同 hash 才是新的正文 revision candidate。 |
| `SemanticExtraction` | `semantic_extraction_id = sha256(detail_revision_id | semantic_extractor_version | body_normalization_version | canonical_fact_fingerprint)`、`semantic_extracted_at_ms` | 对一个 detail revision 的一次版本化语义解释。时间不参与 identity；同 identity 的重复成功 observation 保留最早 `system_available_at_ms`。新 parser 只在实际运行后产生新的 extraction，不回填历史可得时间。 |

所有原始 bytes、HTTP/解析结果与 source URL 都必须附着到相应 capture/observation。列表 bytes 永远不能产生或修改 `DetailRevision`。

### 4.3 Canonical semantic authority and evidence pointers

```text
semantic_authority_locale = en
semantic_authority_variant = canonical_binance_english_detail
```

市场范围、symbol、限制、结算与下架 schedule 只从 canonical English detail 提取。其它 locale/region/translation 可以保存为非权威 raw evidence，但 `semantic_authority = false`，不得与英文内容 hash 比较来生成 revision。若 canonical English source 无法取得或无法验证 variant，`source_audit_eligible = false`。

每个 `present` schedule fact 的 evidence pointer 至少包含：

```text
detail_revision_id
detail_raw_sha256
semantic_extraction_id
semantic_extractor_version
body_normalization_version
location_kind = json_pointer | dom_path | normalized_text_span
location_value
normalized_body_utf8_byte_start
normalized_body_utf8_byte_end
excerpt
```

字节 offset 只针对由 `body_normalization_version` 生成的 UTF-8 normalized body；`detail_raw_sha256` 将其锚定回不可变原始 bytes。没有可复现 pointer 的事实不是 `present`。

每条 notice 还必须标明 `capture_mode`：

```text
live_observed
  = 运行中的 collector 在公告列表/详情首次可见时留下的本地接收证据。

historical_backfill
  = 后来下载的历史官方页面或 fixture；可用于 schema、scope、
    schedule 文本和市场存在性审计，但不能证明当时市场何时得到该信息。
```

`historical_backfill` 永远不能被标为 point-in-time replay eligible，也不得把本次下载时间写成历史 `notice_lineage_first_detected_at_ms` 或 `system_available_at_ms`。

```text
source_published_at_ms
  = 官方载荷所声明的发布时间；仅作来源事实。

raw_detail_fetched_at_ms
  = 本系统首次取得该 DetailRevision 原始 bytes 的时间；不等于可使用的语义事实时间。

trusted_payload_observed_at_ms
  = canonical detail payload 首次通过 transport/trust validation 的时间；
    不等于 parser 已成功提取当前 schedule facts 的时间。

system_available_at_ms
  = 当前 SemanticExtraction 首次成功产生其 canonical fact fingerprint 的时间；
    是 point-in-time research 的唯一 authoritative availability time。

notice_lineage_first_detected_at_ms
  = 本系统首次在官方列表发现该 article 的时间；
    永不被后续 detail、revision 或 replay 时间覆盖。
```

`system_available_at_ms` 不能早于 `semantic_extracted_at_ms`。若旧 raw detail 在 T0 已存储但 extractor v1 失败、extractor v2 在 T2 成功，则该 SemanticExtraction 的 `system_available_at_ms = T2`；不得回填为 T0。

时间事实使用 `fact_parse_status`：`present`、`not_stated`、`unparseable`、`conflicting` 或 `out_of_scope`；capture 时间使用 `capture_time_status`：`present`、`historical_unknown` 或 `not_observed`。两者不得共用一个 status enum。只有 `fact_parse_status=present` 且对应 SemanticExtraction 有 `system_available_at_ms` 才允许进入后续计算。

## 5. 生命周期时间锚点契约

### 5.1 Anchor taxonomy

| Anchor | 字段 | 语义 | 是否必需 | 禁止推断 |
|---|---|---|---|---|
| T0a | `source_published_at_ms` | 公告自述发布时间 | 否 | 不等同系统可得时间 |
| T0b | `notice_lineage_first_detected_at_ms` | 首次发现公告列表 | 对 `live_observed` 必需 | 不得被后续时间改写 |
| T0c | `system_available_at_ms` | 当前 semantic fact 首次被运行中系统成功提取的时间 | 对 point-in-time 研究必需 | 不得用 payload 到达、发布时间或旧 revision 时间代替 |
| T-restrict | `order_restriction_start_ms` | 公告明确规定的新开仓/下单限制生效时间 | 否 | 不得默认为 reduce-only |
| T-last | `last_trading_time_ms` | 公告明确的最后正常交易时间 | 否 | 不得由 settlement 倒推 |
| T-settle | `settlement_time_ms` | 公告明确的结算/清算时间 | 否 | 不得由 last trading 推断 |
| T-delisted | `delisting_complete_time_ms` | 公告明确的合约完成下架时间 | 否 | 不得等同 settlement |
| T-final-hour-window | `final_hour_start_ms` | 仅在 `settlement_time_ms` 为 `present` 时由其减一小时得到的派生诊断窗口 | 否 | 不是公告原始事实 |
| T-final-hour-policy | `final_hour_policy_status` / evidence | 官方是否明确了 final-hour 特殊政策 | 否 | 不得由 `settlement_time_ms` 推断 |

`order_restriction_type` 只允许：`reduce_only_only`、`no_new_positions`、`no_new_orders`、`unknown`。当公告未明确限制类型时，时间和类型均为 `not_stated`，不得写入 `reduce_only_only`。

### 5.2 Point-in-time anti-hindsight rule

```text
eligible research information time = fact_available_at_ms
  = the source SemanticExtraction.system_available_at_ms

any replay row timestamp < fact_available_at_ms
  => forbidden

later DetailRevision or later SemanticExtraction
  => a later fact version, never a rewrite of the former information set
```

每个 schedule fact 必须绑定 `source_detail_revision_id`、`source_semantic_extraction_id` 与 `fact_available_at_ms`。例如 R1 于 10:00 可用且给出 `settlement_time_ms=18:00`，R2 于 12:00 可用且改为 20:00，则 11:00 的 information set 只能看见 18:00，13:00 才可看见 20:00。

`T-final-hour-window` 是由可信 `T-settle` 推导的报告窗口，不是允许在公告发布前使用的先知锚点，也不证明交易所存在 final-hour 特殊机制。若 `T-settle <= fact_available_at_ms`，该 notice 可记录为事后/无可行动窗口，但不得被删除。

对于 `historical_backfill`，`notice_lineage_first_detected_at_ms` 和 `system_available_at_ms` 的 `capture_time_status` 必须为 `historical_unknown`；即使 `T-restrict`、`T-last` 或 `T-settle` 能从正文解析，也只能用于 timetable/source-schema 审计，不能构造公告后收益、entry delay 或任何点时 replay 窗口。

## 6. Symbol 映射与多合约隔离

### 6.1 Parent/child model

一个 `DelistingNotice` 是不可拆分的公告证据单位；一个 `DelistingContract` 是其下单一 USD-M perpetual contract 的子记录。子记录的 stable identity 为：

```text
sha256(source_article_id | detail_revision_id | canonical_symbol | margin_family | contract_type | underlying_family)
```

该 identity 仅用于 source-audit 记录。它不是交易身份，也不得复用 Stage 1.5 launch event identity。

### 6.2 Batch integrity reducer

```text
trusted detail
-> classify product family
-> extract the complete declared contract set
-> classify and account for every child market family
-> validate every in-scope child anchor status/evidence
-> emit one complete parent plus eligible in-scope child records

any symbol omitted from the declared set, or any child with unresolved scope
-> emit one notice-level diagnostic
-> mark all affected child candidates source_audit_eligible = false
-> no eligible child from an incomplete parent
```

已完整解析的 mixed-market parent 不会因存在明确 `out_of_scope` child 而整体丢弃：已确认的 USD-M crypto child 可单独进入 source audit，COIN-M/TradFi 等 child 保留为已核算的 `out_of_scope`。输出必须包括 `mixed_notice_count`、`out_of_scope_child_count` 和 `usd_m_crypto_children_excluded_due_to_incomplete_parent_count`，防止 packaging bias 被隐藏。

`underlying_family=unknown` 仅在 child 的 contract/margin/settlement/quote 事实完整、但不满足 crypto positive-evidence rule 时视为已核算的 `out_of_scope`。若 child 的市场类型、合约类型或符号集合本身无法确定，则 parent 不完整，任何 child 都不得 eligible。

对 `live_observed` in-scope child，“required anchor”是 `notice_lineage_first_detected_at_ms`、该 child facts 的 `system_available_at_ms`、产品范围与完整合约集合；限制开仓、最后交易和结算可以合法缺失，但必须显式记录缺失状态。对 `historical_backfill`，T0 缺失是预期状态，结果只可用于 source/schema audit，不得升级为 point-in-time evidence。

## 7. 数据覆盖与微观结构指标契约

### 7.1 先审计数据，再计算指标

| 指标类别 | 后续候选指标 | 需要的点时数据 | 1.6A 的输出 |
|---|---|---|---|
| 价格反应 | T0+1h / 4h / 12h / 临近结算的 log return、实现波动率 | 具有明确 bar close time 和 coverage 的历史 USD-M 价格 | `coverage_pass` 或 `not_evaluable` |
| 尾部路径 | MAE、MFE、wick risk、最大跳空 | 方向、entry/exit rule、连续高低价或 trades | 仅定义前提；不计算方向性结论 |
| 流动性 | spread、book availability、深度衰减、$500 假设性 sweep cost | 同时刻的 L2 snapshots、快照延迟与有效档位 | 区分 historical unavailable 与 live-observable |
| 成本 | 手续费、funding crossing、mark-index divergence | 费率来源/账户假设、funding timestamps、mark/index 数据 | 每个输入单独覆盖状态 |

`$500` 仅是未来可预注册的最小容量探针，不是仓位建议。盘口估计必须写明：快照时点、买卖方向、所用档位、未成交量处理和 snapshot-to-action 延迟。没有真实 L2 数据时，不能把价格 bar 或当前盘口替代为历史滑点。

方向性 MAE/MFE 与净收益必须在后续独立 Design 中冻结 `side`、entry delay、exit、最大持有时间、taker/maker 假设、实际 fee schedule、funding crossing 与无成交处理。1.6A 只输出方向无关的覆盖和结构诊断。

### 7.2 Endogeneity and controls

下架标的可能在公告前已处于流动性衰退、趋势下跌、资金费失衡或项目风险暴露状态。任何后续方向性研究必须预先定义匹配控制变量，至少包括公告前价格动量、成交量/深度衰减、funding、OI 与市场 regime；不得只以 BTC 或随机日期作为充分反事实。

### 7.3 Source-audit verdict decomposition and threshold authority

`source_audit_passed` 不是模糊总开关。它仅表示 source schema 与历史样本密度通过，且不授权 point-in-time replay：

```text
source_schema_integrity_passed =
  canonical English authority available for every eligible sample
  AND source_integrity_pass_rate >= EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO
  AND symbol_mapping_pass_rate >= EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO
  AND event_type_classification_pass_rate >= EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO
  AND available_at_policy_defined = true
  AND forbidden_payload_count <= EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT

sample_sufficiency_passed =
  historical_events_found >= EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS
  AND event_days >= EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS
  AND symbols_with_events >= EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS

source_audit_passed =
  source_schema_integrity_passed
  AND sample_sufficiency_passed

point_in_time_source_validated =
  live_observed_eligible_notice_count >= EXTERNAL_SIGNAL_STAGE1_6A_MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES
  AND no accepted live fact has missing/conflicting capture-time provenance

market_data_coverage_passed =
  a separately reported coverage verdict; it is not part of source_audit_passed
```

### 7.4 Audit Metric Definition

所有以下统计仅针对一个 immutable `audit_candidate_manifest`。该 manifest 在 `candidate_discovery_rule_v1` 命中时写入，且必须在 detail 获取、semantic extraction、symbol mapping 与 event-type classification 前冻结。summary 必须写入 `audit_metric_definition_version=stage1_6a_audit_metric_v1`、candidate rule version 和 manifest hash。

| Metric | Counting unit / numerator | Denominator / population | Exclusions and time rule |
|---|---|---|---|
| `historical_events_found` | distinct `source_article_id` parent notices with canonical English `DetailRevision`, complete parent declaration, and at least one in-scope `USD_M + PERPETUAL + crypto_asset` child | N/A; it is a parent-notice count | One batch notice counts once, never once per child. Only `capture_mode=historical_backfill` parents count. |
| `event_days` | distinct UTC calendar dates of `source_published_at_ms` among `historical_events_found` parents | N/A; it is a parent-notice date count | Count only `source_published_at_ms.fact_parse_status=present`; never use `settlement_time_ms` date. |
| `symbols_with_events` | distinct `canonical_symbol` among eligible in-scope children of `historical_events_found` parents | N/A; it is a child-symbol diversity count | A symbol repeating across notices counts once. Out-of-scope children never count. |
| `source_integrity_pass_rate` | manifest parents for which canonical source bytes are persisted, trusted canonical English detail is obtained, and immutable capture/provenance fields are complete | every distinct parent `source_article_id` in `audit_candidate_manifest` | Detail unavailable, WAF, parse failure or missing provenance remain in denominator and fail numerator. |
| `symbol_mapping_pass_rate` | trusted-detail candidate parents whose complete declared contract set is deterministically extracted and every child is accounted as in-scope or out-of-scope | all trusted canonical-English-detail parents in the manifest that declare a candidate futures delisting | Notice-level metric. A declared batch with one unaccounted child fails the numerator. |
| `event_type_classification_pass_rate` | trusted-detail candidate parents deterministically classified as `in_scope` or fully accounted `out_of_scope` | all trusted canonical-English-detail parents in the manifest | ambiguous, conflicting or unresolved parents stay in denominator and fail numerator. |
| `forbidden_payload_count` | payload observations used, or attempted to be used, as semantic authority despite violating the source/domain/locale/variant boundary | N/A; absolute count | Correctly rejected WAF, untrusted or non-English payloads do not count. Non-English translation or non-Binance payload used to populate a schedule fact does count. |

The denominator membership of every rate is immutable once its manifest entry exists. A later successful parse can change only that entry's numerator outcome; it can never remove the entry from a denominator. Any implementation that filters its denominator by trusted detail, successful mapping or successful classification before measuring the corresponding failure rate is invalid.

未来 Plan 必须在 `configs/base.py` 新增并由 config tests 锁定以下唯一 threshold authority；roadmap 只提供政策来源，不能成为运行时 threshold authority：

```text
EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS = 30
EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS = 10
EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS = 3
EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO = 0.95
EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO = 0.95
EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO = 0.95
EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT = 0
EXTERNAL_SIGNAL_STAGE1_6A_MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES = 1
```

这些是 research-audit gates，不是交易阈值；本 Design 不授权其它 config 变更。

| Verdict combination | Allowed next action |
|---|---|
| `source_audit_passed = false` | `source_audit_failed_or_inconclusive`; 不写 replay Design。 |
| source audit pass，但 `point_in_time_source_validated = false` | `write_live_source_observation_design_only` 或 `write_ex_post_diagnostic_design_only`; `point_in_time_directional_replay_allowed = false`。 |
| source audit 与 point-in-time source 均 pass，但 market data coverage fail | 仅写 market-data coverage remediation/design；不得声明 execution feasibility。 |
| 三者均 pass | 仅允许另行评审 `pre_settlement_forced_flow_diagnostic_replay_design`；本 Design 仍不授权实现 replay。 |

## 8. 与 Stage 1.5 的隔离式复用

| 组件 | 1.6A 使用方式 | 本阶段是否修改 |
|---|---|---|
| Stage 1.5A `RawSourcePayload`、payload hash、domain safety | 作为可复用模式候选；Plan 必须先验证 schema 是否足够 | 否 |
| Stage 1.5A generic `DELISTING` title 分类 | 仅作为候选发现；不能作为 futures scope 证明 | 否 |
| Stage 1.5C price coverage/replay helpers | 仅作为历史价格覆盖审计的候选依赖 | 否 |
| Stage 1.5D/F/G live launch pipeline | 物理、事件 schema、root 和部署均隔离 | 否 |
| Stage 1.5E depth/cost methodology | 可借鉴指标定义；不能把 launch 证据直接当下架证据 | 否 |

若未来 audit implementation 发现现有 Stage 1.5A 模型无法承载 `DelistingNotice` 的 parent/child、revision 或 schedule evidence，必须停止并提交 Design delta；不得将下架字段临时塞入 launch contract。

## 9. Risk-Veto 的严格边界

本 Design 允许一个只读、不可执行字段：

```text
risk_veto_candidate = true
  only when a trusted in-scope USD-M delisting notice has a complete symbol set
  and every candidate fact has system_available_at_ms present.
```

该字段只能出现在审计报告中，用于人工查看和未来 1.6R schema 对齐。它不得写入现有策略黑名单、不得阻断开仓、不得触发减仓或通知动作。后续若要将其变成策略准入输入，必须另行设计：资产映射、false-positive policy、有效期、解除条件、人工确认、故障降级和每个消费者的回归验证。

## 10. Failure Semantics, Persistence and Idempotency

1. 原始 payload 写入成功前，不得产生 `source_audit_passed` 或可评估子记录。
2. detail 不可信、WAF/login shell、HTTP 202 empty、正文不可解析、产品范围冲突或符号不完整时，只产生诊断；不得发出来自不完整 parent 的 eligible child。
3. 相同 article 的 list hash 变化只产生新的 `ListCapture`。相同 `source_article_id + source_locale + request_variant + detail_raw_sha256` 重复取得时保持同一个 `detail_revision_id` 与不可变的最早 `revision_first_observed_at_ms`。
4. canonical detail hash 改变才产生新的 `DetailRevision`。新 parser 对旧 detail 成功时产生新的 `SemanticExtraction`，其 `system_available_at_ms` 必须是实际 extraction 时间，不得回填 raw fetch 时间。
5. restart/replay 同一 immutable capture/revision/extractor 输入必须得到相同 parent/child identity、fact parse status 和 scope decision。
6. 任何原始 payload、时间证据、符号集合或数据覆盖证明缺失，都只能降低为 `not_evaluable` / `source_audit_failed`，不能被默认值补齐。

## 11. 验收不变量

- **INV-01 Scope isolation:** 只有被可信正文明确识别的 `USD_M + PERPETUAL + crypto_asset` delisting child 可成为 in-scope audit record。
- **INV-02 Point-in-time truth:** `notice_lineage_first_detected_at_ms` 与每个 fact 的 `system_available_at_ms` 不被后续 detail、revision 或 replay 回填。
- **INV-03 Anchor evidence:** 每个 `present` 时间锚点都携带原始载荷来源和定位证据；未陈述即 `not_stated`。
- **INV-04 No inferred reduce-only:** 未出现明确限制文字时，`order_restriction_start_ms` 与 `order_restriction_type` 不得被推断。
- **INV-05 Batch completeness:** 批量公告无法完整解析时，不得发射部分 eligible contracts。
- **INV-06 Revision durability:** 只有 canonical English detail 的新 payload hash 追加为 DetailRevision，永不覆写过去可得信息。
- **INV-07 Data honesty:** 无历史 USD-M price/L2/funding/OI 覆盖的指标为 `not_evaluable`，不得用当前数据替代。
- **INV-08 No directional claim:** 1.6A 不产出做多/做空、MAE、净收益或 alpha 结论。
- **INV-09 No execution authority:** 所有 trade/paper/execution/alpha 权限保持 false；不触碰 `RISK_LIVE_TRADING_ENABLED`。
- **INV-10 Risk-veto isolation:** `risk_veto_candidate` 不得成为任何现有策略的自动准入/平仓输入。
- **INV-11 Restart determinism:** 相同 immutable payload/revision 输入在重跑后产生相同 audit verdict 与 identities。
- **INV-12 Stage 1.5 protection:** 1.6A 不读取、写入、重启或依赖正在运行的 Stage 1.5D/F live roots。
- **INV-13 Historical honesty:** `historical_backfill` 不得伪造 `notice_lineage_first_detected_at_ms` 或 `system_available_at_ms`，也不得进入 point-in-time replay。
- **INV-14 Capture/revision separation:** list capture 变化、locale/variant 差异与重复取得均不得伪造 `DetailRevision`。
- **INV-15 Revision-time authority:** 每个 schedule fact 绑定其 DetailRevision、SemanticExtraction 与 `fact_available_at_ms`；后续 revision 不能在先前 information set 中出现。
- **INV-16 Parser-time authority:** 新 extractor 只能从其实际运行时刻起提供新 semantic facts，不能让旧 raw payload 事后变为早已可用。
- **INV-17 Underlying-family isolation:** 只有 `USD_M + PERPETUAL + crypto_asset` child 可以进入本事件族；其它已知 family 必须被完整核算后隔离。
- **INV-18 Verdict determinism:** `source_audit_passed`、point-in-time readiness 与下一步动作由 config-SSOT thresholds 和显式 predicate 决定。

## 12. Verification Strategy and Design Completion Gate

后续 Implementation Plan 必须从只读、冻结的官方样本和明确标记的 synthetic failure fixtures开始，至少机械验证：

1. `USD_M + PERPETUAL + crypto_asset` accepted；COIN-M、TradFi、spot、margin、loan、Convert、pair-only 和 `unknown` rejected or isolated as `out_of_scope`。
2. 单合约、同市场批量公告与 mixed-market 批量公告均保持完整 parent declaration；不完整 parent 不会发出 eligible subset，而完整 parent 的 in-scope child 不会因已核实的 out-of-scope sibling 被静默丢失。
3. 新增无关 article 改变 announcement list hash，不会为既有 article 产生 DetailRevision；相同 canonical detail hash 重复取得保持同一 `detail_revision_id` 和最早 observation time；canonical detail hash 改变才产生新 revision。
4. English 与非 English/不同 request variant 的 bytes 不会互相生成 revision。canonical English source 缺失时 source audit 不 eligible。
5. R1 于 10:00 给出 settle=18:00，R2 于 12:00 给出 settle=20:00：11:00 information set 只见 18:00，13:00 才见 20:00。
6. raw detail 在 T0 被捕获、extractor v1 失败、extractor v2 于 T2 成功时，新 facts 的 `system_available_at_ms=T2`，不回填 T0。
7. `historical_backfill` 可有 `settlement_time_ms.fact_parse_status=present`，但 capture-time status 为 `historical_unknown`，且 `point_in_time_replay_eligible=false`。
8. `order_restriction_start_ms`、`settlement_time_ms`、`last_trading_time_ms` 的 `present/not_stated/unparseable/conflicting` 路径，以及 `final_hour_start_ms` 与 `final_hour_policy_status` 的独立性。
9. 缺少 L2、fee、funding 或 OI 时对应指标为 `not_evaluable`，不输出估计净收益。
10. config tests 锁定全部 `EXTERNAL_SIGNAL_STAGE1_6A_*` thresholds；summary verdict 只能由这些 constants 和明确 predicate 导出。
11. `risk_veto_candidate` 的静态 consumer-isolation test 证明 Stage 1.6A 不会 import/call `strategies/*`、risk admission 或 `execution/*`，且它只能写入 audit artifact。
12. 历史回填 payload 即使能解析完整 schedule，也保持 `historical_backfill` 和 `point_in_time_replay_eligible = false`。
13. 40 个冻结 candidate parent 中，30 个 trusted/complete、10 个 detail unavailable 时，`source_integrity_pass_rate = 30 / 40`，不得变为 `30 / 30`；批量公告在 `historical_events_found` 中只计一个 parent，但其 eligible children 分别计入 `symbols_with_events`。
14. 同一 immutable `audit_candidate_manifest` 在 restart/replay 后产生相同 metric population、分子、分母、`semantic_extraction_id`、summary verdict 与 `allowed_next_action`。

Design 审核通过的标准是：上述 invariants 无冲突，官方 source 的原始证据边界和字段缺失规则可被测试，且未来 Plan 的范围仍限定为 read-only source audit。通过后可写 audit implementation plan；任何价格方向、执行可行性或 risk-veto enforcement 都需新的 Design。

## 13. Rollout, Rollback and Open Questions

本阶段没有 runtime rollout、VPS 部署、配置变更或 rollback 操作。未来 audit implementation 的默认输出根必须独立于 Stage 1.5D/F，且 1.5G 永远不在 VPS 上运行的既定边界不变。

没有会改变本 Design 实现路径的开放问题。以下为 audit 将验证的外部事实，而不是待决定的设计分支：canonical English 公告模板是否稳定、哪些 schedule facts实际出现、实时 point-in-time capture 是否建立，以及历史数据覆盖是否足够。它们的失败结果按本 Design 输出 `source_audit_failed`、`source_audit_inconclusive` 或 `not_evaluable`，不会扩张范围或降低不变量。

## 14. 下一步

1. 对本 Design 做独立审查，重点检查 anchor 语义、USD-M scope、batch completeness、revision point-in-time 边界和风险权限隔离。
2. 仅在 Design 获批后，使用 `implementation-plan.md` 编写一个窄范围、只读的 source/schema/effective-time audit Plan。
3. 该 Plan 不得包含 replay、交易、risk-veto enforcement 或 Stage 1.5D/F production wiring。
