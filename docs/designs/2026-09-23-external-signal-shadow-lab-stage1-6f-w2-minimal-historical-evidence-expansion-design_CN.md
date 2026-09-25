# Stage 1.6F-W2 历史价格证据最小补采 Design

- 日期：2026-09-23
- 状态：`draft_for_review`
- 类型：独立候选证据包；有限公共历史归档补采；不改变 W1 输入契约
- 本轮交付：仅此 Design；`implementation_allowed=false`、`network_collection_allowed=false`、`runtime_action_allowed=false`
- 检查基线：`1b94ab05d72907f700cac8be0709fe975df8f61c`；起草前 tracked/index/untracked 均清洁
- 后续用途：为另行审批的 W2-0 历史终局基差粗筛提供可核验的原始小时价格证据

## 1. 目的与 Final Claim

本 Design 只回答：对冻结 41 标的分母中有结算时间 authority 的标的，能否取得冻结矩阵指定的 W2 小时价格归档，并逐项证明身份、原始字节与时间覆盖，或者留下明确缺口。

成功不等于全部下载成功，也不等于 41 标的均可分析。成功是：41 个分母身份无一丢失；180 个物理对象和对应逻辑记录有已记录的 package 终态；123 个 event/family 覆盖记录可由 strict reader 独立重算；缺结算时间、公告截断、无完整小时栏和采集失败均被保留。远端请求是否实际发生及其 HTTP 观察不由 package bytes 独立证明，必须按 §4.1 的 producer/runtime evidence 与 §12 外部 Completion Audit review artifact 消费。

它不计算 basis、MAE、MFE、资金费收益、统计显著性或研究晋级结论。W2-0 的指标、观察点、样本充分性与去留门槛仍须在读取补采价格结果进行研究之前，另行冻结分析 Design，并满足 §12.1 的 pre-analysis blind boundary。采集完成不自动放行 W2-0，更不放行 W2-1。

## 2. 已确认事实与根因

### 2.1 本地核查事实

2026-09-23 通过生产 `verify_c_input()` 读取保留 C 字节，并使用 `reconstruct_denominator()` 检查 eligibility；用生产 `load_verified_candidate_evidence()` 对 exact `002` root 做只读验证，实际退出码均为 `0`。

| 项目 | 核查结果 |
| --- | --- |
| 冻结 candidate cohort | 41 个 USD-M、USDT 结算永续合约身份；27 个 distinct `parent_article_id`，不声称统计独立 |
| C 中 `settlement_time.fact_parse_status=present` | 31 标的，21 个 distinct parent ID |
| C 中结算时间 `not_stated` | 10 标的，保留分母，不能构造 W2 时间窗口 |
| C 中 `order_restriction`、`last_trading_time` | 41 标的均为 `not_stated`；不等于原公告一定未声明，只表示冻结解析产物没有证明 |
| 矩阵 W2 的三类小时价格记录 | 180 条逻辑记录，180 个不同 URL，覆盖上述 31 标的 |
| 与 `002` 物理 URL 集合相交 | 9 个，生产 loader 已验证全部 `fetched_verified` |
| 不在 `002` 中的 URL | 171 个；当前可下载性未知，历史 HTTP 200 不作当前成功证明 |
| `002` 中复用对象最大 ZIP/CSV | 1,445 / 3,148 bytes；仅是这 9 个对象的实测，不是其他归档大小保证 |

缺结算时间的 10 个标的是 `BDXNUSDT, BOBUSDT, DAMUSDT, KDAUSDT, MILKUSDT, OBOLUSDT, PUFFERUSDT, SLERFUSDT, SXPUSDT, TOKENUSDT`。

9 个相交 URL 分别属于 AIAUSDT、PORT3USDT、UXLINKUSDT，每个标的三类文件。UXLINKUSDT 仅有 2025-09-25，缺 2025-09-26，因此不是 W2 文件齐备。AIAUSDT 和 PORT3USDT 的矩阵实际区间分别为 `[2025-12-11T11:43:46.582Z, 2025-12-11T12:15:00Z)` 与 `[2025-11-23T05:57:34.108Z, 2025-11-23T06:30:00Z)`；均被 Tpub 截短且没有完整小时栏。不能将“有文件”改称“完整 24h 可分析”。

### 2.2 根因及项目定位

2026-09-16 expansion Design §3.2/§5.2 明确只收 W1 与公告前 baseline；现有 `enumerate_candidate_requests()` 只枚举该范围，现有 `002` loader 固定其路径、SHA、705 logical / 664 physical contract。W2 缺口是有意 scope 排除，不是旧 collector 的 bug。

当前 roadmap/current-project-state 中仍有“重新推进 1.6A”的旧叙述，不能覆盖实际 B/C/F 代码、已冻结时间事实与产物。本文不重启 1.6A、不改变线上 1.6D/E-B，也不修改这些状态文档。

Graphify 精准查询尝试：`.venv/bin/python -m graphify query validate_candidate_root_core` 返回 `No module named graphify`。未更新图谱；以下拓扑依据真实源码而非图谱推测。

## 3. 假设、方案与决策

### 3.1 显式假设

- 部分历史 URL 可能仍可取得；任何对象不可得都必须记账，不能自动换源。
- 三类小时价格适合未来粗粒度描述，不保证覆盖最后半小时、真实结算价或盘中风险极值。
- 已解析的历史时间只是 ex-post 时间事实；无 `Tavailable` 证明，不能升级为 PIT。
- 全部分母不是随机样本；本次采集不处理选择偏差和统计独立性。

### 3.2 方案比较与已作决策

| 方案 | 代价/限制 | 决策 |
| --- | --- | --- |
| 仅复用 9 个已存 URL | 无网络，但范围碰巧重叠且两个窗口无完整小时栏，不能作为全样本研究替代 | 不采用 |
| 三类小时价格、固定 180 URL、9 复用 + 171 新请求 | 集合可枚举；Mark 作为价格语义辅助证据；不补微观数据 | 采用 |
| 全市场族、秒级 Index、L2、实时 observer | 超出粗筛前置证据需求，增加下载和运行生命周期 | 不采用 |

采用独立 W2 candidate schema/root，复用可独立调用的旧纯解析函数；禁止把 W2 加进旧 `PERMITTED_WINDOWS_METRICS` 或放宽 exact-002 admission。9 个复用对象复制到新 root 成为独立普通文件，不用 hardlink/symlink，不用外部 CSV 引用替代归档。

## 4. 冻结输入与 Authority

路径均相对项目根。旧 expansion Design 的 §2.1 十项 path/SHA 表及其 source topology 作为传递冻结输入，逐项重算并匹配；它们用于证明历史对象，不赋予此次请求权限。以下是本 Design 额外直接绑定：

| 输入 | 路径 | SHA-256 |
| --- | --- | --- |
| W1 expansion Design | `docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md` | `1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4` |
| W1 expansion Plan | `docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md` | `fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d` |
| W1 admission Design | `docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md` | `dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097` |
| Cardinality Delta | `docs/designs/2026-09-20-external-signal-shadow-lab-stage1-6f-candidate-w1-parent-article-cardinality-correction-delta-design_CN.md` | `02945b5aa9989e48b50381876601ff72f7080878e4e5eb7cc6cdc6eaaf8617f9` |
| `002` manifest | `data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002/candidate_manifest.json` | `b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67` |
| `002` historical network record | `configs/authorizations/network_auth_expansion_run_20260917_002.json` | `8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6` |
| shared source | `src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py` | `81dca38c323a1632e7e1302b8016a40603c970cb16da58ea13108b5a2ae23f3b` |
| existing collector（拓扑证据，不调用 main） | `scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py` | `32c8b06e3167b9d2c5010f5efc95e777748f1a53b552731cdf4f192a8262c4dc` |

覆盖矩阵 path 为 `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json`，SHA 为 `b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8`。C root、B root 使用上述传递表中 manifest 的父目录，由 `verify_c_input()` 校验并仅使用其 retained bytes。

本 Design 新的 approved SHA、未来 Plan 的 approved SHA、一次性网络授权是三个外部输入，不能在未审批草案中伪造。未来 Plan 必须明确引用本 Design 和以上冻结链，不能只绑定最新 HEAD。旧网络记录不能授权 W2。

JSON hash 统一定义 `J(x)=UTF8(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False))`，SHA 为 `sha256(J(x))`。文件 SHA 始终哈希原始 bytes。严格 JSON reader 拒绝重复 key、NaN/Infinity 和额外字段；整数字段拒绝 bool。

### 4.1 Trust Boundary 与 Evidence Class

本 Design 不把不可从本地 bytes 重建的远端事实表述为 independent proof。证据只分为下列三类，任何 consumer 必须保持其类别：

| Evidence class | 可证明内容 | 不可证明内容 / consumer 义务 |
| --- | --- | --- |
| `independently_recomputed` | 分母身份、冻结 URL 集合、文件 hash/长度、复用字节、ZIP/CSV 结构、网格覆盖、manifest 与 root state | strict reader 只能证明本地输入和 bytes 满足本 Design，不能推出网络历史 |
| `producer_attested_runtime_observation` | approved producer 声明的 GET 已发出、HTTP/transport 终态、request/response 时间、171 次 one-attempt discipline、无 redirect/retry | strict reader 不独立证明这些事实，也不能从根内字段排除未记录的额外请求；只能核对字段与本地状态的一致性 |
| `external_authority` | 已批准的 Design、Plan、单次网络授权，以及独立只读 Completion Audit 的 external review artifact | authority 或 review artifact 缺失、SHA 不匹配或被后续 W2-0 Design 拒绝时，不得准入分析 |

`producer_attested_runtime_observation` 的 TCB 是 approved Plan 所绑定的 exact implementation/runtime identity，加上独立只读 Completion Audit 对该 identity、执行证据和最终 manifest 的 external review artifact；它不是 packet capture、第二网络监控器或 remote-server proof。本 Design 不新增这些网络系统，也不把审计结论误称为对 wire-level HTTP 事实的独立重演。

## 5. 分母、时间与请求集合

### 5.1 分母与时间来源

`verify_c_input -> reconstruct_denominator -> eligibility_passed -> matrix in_range symbols -> minus REEFUSDT` 得到 exact-002 的 41 symbols；身份使用 `(parent_article_id, contract_id, canonical_symbol)`，不得只靠 symbol join。必须与 verified-002 的身份集合一致，并验 41 identities / 27 distinct parents。

Tpub 唯一来源为 retained `parent_audit_outcomes.source_published_at_ms`，要求 `publication_time_status=present`，与对应 retained notice 相同；不从日期文件名或当前官网补出时间。Tsettle 只来自同一 contract 的 `settlement_time` fact，须 `fact_parse_status=present`、正整数 `timestamp_ms`，以及 B/C 已验证的 evidence、revision、semantic-extraction lineage。`order_restriction` 和 `last_trading_time` 原样保留其 fact；不得生成 `Tsettle-30m` 默认 cutoff，不把 last-trading/最后一根 Kline 当结算时间。

现有 10 个 `not_stated` settlement facts 是已知证据缺口，不是输入损坏；输出 `settlement_time_unproven`。非法 present fact、身份重复、时区/时间单位错误、Tsettle<=Tpub、notice/outcome 冲突是 `STOP=w2_temporal_authority_invalid`，在任何网络请求前终止。

### 5.2 窗口契约

对 31 个有时间事实的标的，`nominal_start=Tsettle-86_400_000`，`actual_start=max(Tpub, nominal_start)`，`end=Tsettle`。要求逐条匹配冻结矩阵的 nominal/start/end、truncation flag/reason 和日期集合。ISO 时间须含 UTC offset 并精确转换为毫秒，不截断精度。

这是当前矩阵批准范围内的 `[actual_start,end)`；不是新增未截断 24h。2 个被公告截断窗口必须显式标记。若未来需要其公告前日期，需新 scope，不从整日文件的附带行扩充本次声明的覆盖范围。整日原始字节保存完整，但窗口外行不构成本 Design 的窗口观测。

### 5.3 枚举与数量守恒

从 frozen `in_range_archive_records` 中按 exact identity、`window=w2_settlement_24h`、`metric in {klines_1h,index_price_1h,mark_price_1h}` 选取。每条 full matrix row 绑定 `sha256(J(row))`，不使用历史 `availability` 字段当新成功状态。复用旧 pure `compute_logical_archive_record_id()` 和 `compute_physical_source_object_id()`：tuple/URL 的 JSON 字符串序列化方法不得改成直接 UTF8(URL)。

Logical tuple 严格为旧 §5.2 的十字段顺序：`parent_article_id, contract_id, canonical_symbol, window, nominal_window_start_utc, window_start_utc, window_end_utc, metric, archive_date_or_month, exact_source_url`。projection 也沿用旧 exact 十字段 mapping。每个 URL 的 family/symbol/date 必须唯一，且路径对应其 matrix family、symbol、`1h`、日期；冲突拒绝。

| 集合 | 定义 | 数量 | `sha256(J(sorted(exact_urls)))` |
| --- | --- | --- | --- |
| ALL | 全部选中 URL | 180 | `3b9ab69a8c1236cab59f161636ae9e4136465ca599d735ef65e37fd2cc574a46` |
| REUSE | ALL 与 verified-002 URL 集合交集 | 9 | `9773f11e316ce480651b0debf6258fefbd39a1ee9bdc2d6bdd838484704ed405` |
| FETCH | ALL 减 REUSE | 171 | `6eac006f8854a17a2d78b4306c03da6f28528aba58ffcfafd6b5f078d4ed7058` |

要求 180 logical / 180 physical、31 有窗口身份 / 21 parent groups；10 无时间身份不得构造请求。每个身份仍输出三类覆盖结果，最终 41×3=123 条。任何集合或计数偏离为 `STOP=w2_request_set_mismatch`，禁止截取前 N 项或用新 URL 补足计数。

## 6. 架构与允许范围

| 角色 | 实际边界 / 未来责任 | 变更 |
| --- | --- | --- |
| B/C producer + strict loader | 来源、分母、时间 facts，retained-byte transaction | 只读复用，禁止修解析器或回填事实 |
| `002` producer/loader | 历史 package 与一次性授权链；`load_verified_candidate_evidence()` | 只读，先完整验证再复用九个对象 |
| 新 W2 本地 CLI | 枚举、授权前检、九对象复制、171 URL 单次下载；唯一网络和 writer owner；产生 Class B runtime observation | 新 script，单次前台运行 |
| 新 W2 evidence module | cohort/time/request derivation、W2 coverage、Class A strict root loader | 新 `src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py`；不 import scripts，无网络 |
| shared pure CSV parser/ID functions | `parse_and_validate_csv()`、两种 ID functions | 直接复用，不修改旧 source |
| W1 / REEF / W2-0 consumers | W1/REEF 继续拒绝 W2 root；W2-0 尚未准入 | 不变 |
| 独立 Completion Auditor | 从 completed root、外部 authority 和执行证据验证 Class A 与 producer identity；只读输出 `complete/incomplete/blocked` review artifact | 后续审计；不写 workspace、candidate root 或 runtime evidence |

未来 Plan 允许新增一个 `run_stage1_6f_w2_historical_evidence_expansion.py`、上述 source module、对应 focused tests，以及 `configs/base.py` 中仅新增 §7 资源常量。script 必须调用 source 的同一 derivation/coverage/strict reader，不复制同 schema 验根器。ZIP 操作使用标准库，reader 独立重读 ZIP member 比较 CSV bytes/CRC，禁止 `src -> scripts`。独立 Completion Audit 依现有审计流程只读生成其 external review artifact；collector 不写 attestation，也不得自证其 runtime identity。

本次只新建 Design 文件。未来 exact 文件白名单由 Plan 冻结；旧 Design/Plan/source/test、现有证据根、线上 collectors、runbooks、roadmap、安全开关和交易模块为 No-Touch。不实现 scheduler、数据库、通用下载框架或 observer。

## 7. 网络授权与资源边界

### 7.1 授权链

未来 collector 同时需要 externally approved 本 Design、approved implementation Plan、独立一次性网络授权。授权记录 exact fields：`schema_version, run_id, design_sha256, plan_sha256, all_urls_sha256, reuse_urls_sha256, fetch_urls_sha256, max_requests, public_archive_get_allowed, permission_flags`。

`schema_version=stage1_6f_w2_network_authorization_v1`、`max_requests=171`、三个集合 hash 为 §5.3 值；`public_archive_get_allowed=true` 仅在用户确实批准这次公共 GET 后成立。`permission_flags` 是 §12 的 exact false mapping。记录路径/SHA 和用户批准语句由 collector 外部提供，reader 与外部值核对，不接受包内自我授权。run_id 必须等于新 root basename。Design/Plan 审批不自动授予网络权限。

网络授权只允许最多 171 次 public GET；它不证明任何 GET 实际发生。完成采集后，对 Class B 远端观察的唯一可消费证明是 §12 所定义的外部 Completion Audit review artifact，而不是 manifest 内的 HTTP/timestamp 字段。

### 7.2 请求与预算

只请求 FETCH 中的 exact matrix HTTPS URL，按 URL 字典序单线程 GET；不发 HEAD、不跟随任何 3xx、不重试、不镜像、不猜 URL、不换 host、不自动更新矩阵、不带认证或账户信息。拒绝 userinfo/query/fragment/非 443 endpoint；对当前固定 URL 集合的 path/family 检查必须通过。禁止从环境代理、cookie 或 netrc 注入认证；标准 TLS 证书校验不得关闭。

使用已有 `EXCHANGE_TIMEOUT_MS=10_000` 和 `EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT`。以下是候选的运行资源上限，供 Design 审核；未来仅在 `configs/base.py` 新增，不在 source 藏阈值：

| Constant | 值 | 用途 |
| --- | --- | --- |
| `EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES` | `1_048_576` | 每个响应体，包括错误体 |
| `EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES` | `4_194_304` | 每个解压 CSV |
| `EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES` | `65_536` | 下载、复制、解压流式块 |
| `EXTERNAL_SIGNAL_STAGE1_6F_W2_MIN_FREE_BYTES` | `4_294_967_296` | 创建 root、每次下载/解压前的输出文件系统余量 |
| `EXTERNAL_SIGNAL_STAGE1_6F_W2_REQUEST_INTERVAL_SECONDS` | `1` | 相邻 GET 开始时间最小间隔 |

171 是冻结 request-set 上界而非可调容量。成功保留的 FETCH 响应体最多 171 MiB；180 份 ZIP+CSV 最多 900 MiB，不含小型 metadata 与至多一个对象的临时文件。超过任何 byte/free-space 边界为 run-fatal `STOP=w2_resource_budget_exceeded`，无 final manifest；不得放宽上限继续。socket timeout 是 I/O 超时，不声称整个 run 有严格 wall-clock 上限。每次 read 长度不超过剩余额度与 chunk 上限的较小值，到上限只允许再读一个字节确认 EOF；有额外字节立即停止且不持久化越界数据。未知长度、伪造 Content-Length 同样受流式上限约束。collector 与 reader 均检查这些资源常量为本表冻结值，不允许通过修改 config 绕过预算。

## 8. 物理字节、CSV 与覆盖契约

### 8.1 复用、下载与物理终态

REUSE 必须在 canonical-002 loader 成功后逐对象确认 `fetched_verified`、URL/ID、普通文件、SHA/长度和 CSV/ZIP 一致。复制到新的 `zips/{physical_id}.zip`、`csvs/{physical_id}.csv` 后回读，再验源文件 hash 未变；不使用 hardlink/symlink。复用损坏是输入 authority 错误，不能改走网络下载。REUSE 的本轮 attempt=0，request/response timestamps=null；其旧请求元数据只通过 source manifest identity 追溯，不冒充本轮请求。

FETCH 的每个对象本轮 attempt=1。HTTP 200 完整响应落盘为 ZIP 后才解析。HTTP 404=`archive_not_found_404`；任意 3xx=`redirect_refused`；其他 HTTP、TLS、超时、429 或断流=`transport_inconclusive`。非完整 200 响应不写最终 ZIP/CSV，清理本对象临时文件；清理失败为 local run-fatal。只表示一次请求结果，不声称远端永远不存在。

完整 200 的 ZIP 损坏=`archive_invalid`，保留 ZIP；ZIP 合法而 CSV 不合法=`csv_invalid`，保留 ZIP 和完整提取的 CSV。二者均禁止给 coverage 提供任何行。合法物理对象=`fetched_verified`，这个状态只证明文件验证成功，不保证窗口完整。

### 8.2 ZIP 与 CSV

继承旧 expansion §5.3：exactly one regular CSV member；禁止目录、加密、symlink、绝对路径、`..`、路径分隔符和额外 member。验证 member basename 必须等于所选 URL 的 `.zip` basename 改为 `.csv`，防 family/symbol/date 文件身份混淆。禁止 `extract/extractall/testzip/整文件 zf.read`；`ZipFile.open()` 定长块读取，校验 CRC、声明长度、byte cap，写 collector-generated path。

三种 family 均复用冻结 shared parser 的 exact 12 列 header 和类型/finite 检查，包括第 12 列 `ignore`；不修原始数据。W2 再要求每行 `open_time % 3_600_000 == 0`、`close_time == open_time+3_600_000-1`、open_time 落在 URL 的 UTC 日期、每 timestamp 唯一且递增。任一失败使整个 CSV `csv_invalid`。OHLC/数量的旧有限、非负谓词保持；Index close 为零不导致除法，因为本采集不计算比率，并在覆盖记录保留 `zero_index_close_count`。

空 CSV 或仅有 header、没有数据行的 CSV 同样为 `csv_invalid`，保留完整提取字节且不提供覆盖行。此非空门禁属于 W2 wrapper，不修改旧 shared parser 的行为。

### 8.3 两种网格必须分开

H=3,600,000；a=actual_start；b=end。原始小时 open 网格 `G={t: t为UTC整点, a<=t<b}`。完整小时网格 `C={t in G: t+H<=b}`。CSV 全日验证先于任何切片。

- `raw_open_grid_status=observed` 当且仅当 G 非空且 G 中每个点恰有一个有效行；缺点=`incomplete`；G 为空=`no_expected_points`。
- `complete_bar_status=observed` 当且仅当 C 非空且 C 中每个点恰有一个有效完整栏；缺点=`incomplete`；C 为空=`no_complete_bars`。
- 任何 referenced physical failure，两个状态均 `not_proven`，不拿同窗口其他合法文件凑完整覆盖。
- 结算时间未证明的 10 标的：两个状态均 `temporal_unproven`，start/end/counts=null，logical IDs=[]，不得报空网格通过。
- 缺点不能插值、补零、forward-fill 或 dedup。跨日期 join 后再次检查重复/冲突。窗口外行不得用于 G/C 计数。

AIA/PORT3 即使原始 open 网格齐备，`complete_bar_status=no_complete_bars`；因此不得报告其粗路径完成。任何“最后可见完整栏”都不等于 settlement price，也不等于 -30m anchor。`close_time` 是栏末时间，不是历史系统获取时间。

## 9. Manifest 与 Strict Reader

新 root：`data/external_signal_shadow/stage1_6f/w2_evidence_candidates/<run_id>/`，run_id 匹配 `[A-Za-z0-9][A-Za-z0-9_-]{0,95}`。只含 `zips/`、`csvs/` 和最后写入的 `candidate_manifest.json`；不得接受临时文件、其他文件、目录 symlink 或路径 alias。所有 JSON record 为 exact key sets，不能用“至少包含”解释本节。

顶层 exact keys：

```text
schema_version, run_id, authority_packet, denominator_records,
logical_archive_records, physical_source_objects, metric_window_coverages,
request_set, candidate_root_state, capture_mode,
point_in_time_source_validated, authority_flags
```

固定 `schema_version=stage1_6f_w2_historical_price_candidate_manifest_v1`，`capture_mode=historical_ex_post_candidate`，`point_in_time_source_validated=false`。

`authority_packet` exact keys：`frozen_inputs, approved_design, approved_plan, network_authorization`。前三类文件绑定使用 `{path,sha256}`；`frozen_inputs` 是 §4 直接表、十项传递表和矩阵合并后的去重 path 列表，按 path 排序，每项 exact `{path,sha256}`；approved_design/plan 是外部批准值。network_authorization exact `{path,sha256,run_id}`，其 bytes 必须满足 §7.1。相同路径不同 hash、丢失、多余输入都拒绝。未来执行 source/config 的实际版本另由 approved Plan Task 0/执行证据绑定，不能由 manifest 自选语义。

`denominator_records` 共 41，按 identity 排序。exact keys：`parent_article_id,contract_id,canonical_symbol,t_pub_ms,settlement_time_fact,order_restriction_fact,last_trading_time_fact,nominal_window_start_ms,window_start_ms,window_end_ms,is_truncated_by_tpub,temporal_status`。三个 fact 是冻结 C 原对象 exact 深拷贝，包含其 evidence，类型/keys 必须与 canonical C schema 一致。temporal_status 仅 `window_defined` / `settlement_time_unproven`；后者窗口字段与截断标志均 null。前者字段独立按 §5 重算。

`logical_archive_records` 共 180，exact keys：`logical_archive_record_id,matrix_record_sha256,matrix_record_projection_v1,physical_source_object_id,record_state`。projection exact 十字段由 §5.3 定义；record_state 与引用物理 `fetch_status` 相同。排序按 logical ID；logical/physical 关系由 reader 重新枚举，禁止只检查 record hash 自洽。

`physical_source_objects` 共 180，沿用旧 expansion §5.2 physical 的 exact 18 字段：`physical_source_object_id,exact_source_url,fetch_status,http_status_or_transport_error,zip_relative_path,zip_byte_length,zip_sha256,csv_relative_path,csv_byte_length,csv_sha256,zip_member_name,csv_header,csv_row_count,first_row,last_row,request_started_at_ms,response_observed_at_ms,reason`，再新增 `acquisition_method,source_manifest_sha256,source_physical_source_object_id,network_attempt_count`。acquisition_method 仅 `copied_verified_002` / `network_get`。前者两个 source 字段绑定 exact-002 和相同 ID，HTTP/time=null、attempt=0；后者两个 source 字段=null、attempt=1、request 时间为正整数毫秒，response 时间无响应时 null，否则不小于 request。物理状态六枚举沿用旧 expansion，reason 为非空解释字符串，不作为 validator 放行依据。

严格 nullability：fetched_verified 的 ZIP/CSV path/hash/length/header/member/first/last 非 null、row_count>0；archive_invalid 仅 ZIP 的 path/hash/length 非 null，CSV/解析元数据 null、row_count=0；csv_invalid 有 ZIP/CSV path/hash/length/member，其 header 可为原始字符串或 null，first/last=null、row_count=0。404/redirect/transport 的 ZIP/CSV 和解析元数据全 null、row_count=0。完整失败字节仍按 §8 保存，不能删掉 csv_invalid 的 CSV。

HTTP 字段类型与终态必须同时成立：`copied_verified_002` 的 `http_status_or_transport_error=null`；`network_get` 收到响应时该字段为 exact int HTTP code（100..599，禁止 bool），response 时间为正整数；未收到响应时为非空 transport error 字符串，response 时间=null。network 的 `fetched_verified/archive_invalid/csv_invalid` 只能对应完整 HTTP 200；`archive_not_found_404` 只能对应 404；`redirect_refused` 只能对应 300..399；其他响应码或无响应只能为 `transport_inconclusive`。收到 200 后断流也是 `transport_inconclusive`，保留响应时间但不保留最终 ZIP/CSV。reader 必须检查上述对应关系；远端结果无法仅凭本地字节重现，reader 不把此元数据校验声称为独立证明当时 HTTP 响应。

`metric_window_coverages` 共 123，排序 identity + metric，exact keys：`parent_article_id,contract_id,canonical_symbol,metric,window_start_ms,window_end_ms,logical_archive_record_ids,expected_open_count,observed_open_count,missing_open_count,raw_open_grid_status,expected_complete_bar_count,observed_complete_bar_count,missing_complete_bar_count,complete_bar_status,zero_index_close_count`。logical IDs 排序且精确等于该 identity/family 请求集。时间已证明而 physical failure 时 expected counts 仍派生，observed/missing/zero counts=null；temporal_unproven 时所有 counts=null；其余 counts 是非负 exact int，非 Index family 的 zero_index_close_count=null。Index 的 zero count 只在有效完整栏 C 内计算。

`request_set` exact keys：`all_urls_sha256,reuse_urls_sha256,fetch_urls_sha256,n_logical,n_physical,n_reused,n_network_attempts`；hash/count 必须精确匹配 §5.3。它是 Class B producer-attested count；root 内字段的 schema 一致性不能独立证明 GET 或无隐藏请求。少于 171 个已记录尝试不能发布完整 package；W2-0 还必须有 §12 对 171 次的 external Completion Audit review artifact。

`candidate_root_state` 仅 `collection_terminal_all_complete_bars` / `collection_terminal_with_evidence_gaps`；前者要求全部 41 时间已证明、全部 physical verified、123 个 complete_bar_status=observed。对本冻结输入，前者不可达，必须为后者；它表示采集协议完成且证据有缺口，不表示交易机制失败。

新 strict reader 接收 root、project_root 和外部三项 authority，不接收 collector 中间对象或 Completion Audit artifact。依次独立重验 Class A 的旧 authority/C/002、时间/请求集合、schema keys/types、路径/完整文件集合、所有 SHA/长度、ZIP 与 CSV 同字节性、全日解析、窗口和 root state；它只检查 Class B 字段的类型、终态对应关系与计数自洽。任何 false flag 被改为 true、未知 schema/key、伪 URL、替换 family、source link、额外文件、缺表、非终态，都拒绝 root。读完只返回 `independently_recomputed` local evidence，不输出信号、分析结论或“GET 已发生”的断言。

## 10. 顺序、持久化与失败恢复

固定顺序：外部批准 + 冻结文件验证 → canonical C/002 loader → 分母/时间/矩阵集合比对 → 校验网络许可/资源 → 原子独占创建新 root → 复制九个对象并回读 → 按排序单次 GET 171 个对象并分别落盘/验证 → 汇总 41/180/180/123 → 回读全部文件并重算 → 清理工作临时文件 → manifest-last 原子发布 → strict reader 重算 Class A → 独立只读 Completion Audit 验证 runtime identity 与最终 artifact，并输出 §12.1 external review artifact。

每个文件通过同文件系统独占 `.part` 写入、flush/fsync、rename 与目录 fsync；root 用独占 mkdir，禁止覆盖。最终 root 文件必须 inode 独立于旧包；相对路径只能为 ID 派生的上述两个目录路径。完整 manifest 不包含自 hash；最终 raw manifest SHA 由外部审计记录。manifest 是提交标志，不能先写 `complete` 再补文件。

任意本地 I/O、读回/hash、rename/fsync、清理、资源失败为 run-fatal，优先于 remote status；不发布 final manifest，保留受损 root 供取证。strict reader 拒绝已发布 manifest 时退出非零，该 root 仍不得准入，不重写成通过状态。崩溃发生在 manifest 发布后但审查前时，只有再次严格只读验根才能判断其 Class A 有效性。Class A root 通过而 Completion Audit 未完成、失败或缺少 §12.1 合格 external review artifact 时，root 只能保留取证，绝不准入 W2-0。

不恢复、不补写、不原地修复。重复 run_id 必拒绝；重采只能新 run_id、新网络授权。九个复用来源只读；中断或完成 root 均不自动删除。collector/reader 不把任意异常 catch 成空数据或成功摘要。

## 11. 验收不变量与验证策略

| ID | 验收不变量 | 必须具有的机械证明 / 单点负向测试 |
| --- | --- | --- |
| INV-W2E01 | 本 Design/Plan/新网络许可三层独立，旧授权无效 | 缺一种、错 SHA、错 run、许可 false、FETCH hash 被改时 GET 计数=0 |
| INV-W2E02 | 41/27 分母、31/21 有时间、10 缺时间不可静默缩减 | canonical C loader 正例；删一个无时间身份或伪造时间拒绝 |
| INV-W2E03 | URL 180/9/171 与三个集合 hash 冻结 | 错日期/多URL/删URL/换host、重复 physical ID 拒绝 |
| INV-W2E04 | 复用完整校验与独立复制，不回退请求 | nine-real-object 正例；损坏 source、hash、symlink 拒绝且不发替代 GET；改新测试副本不影响旧 inode |
| INV-W2E05 | exact-URL 一次请求，流式有上限 | 3xx/404/429/timeout/read断流、伪 Content-Length、超 byte cap；producer execution evidence 证明无 retry/跳转/HEAD；该运行事实归 Class B，不由 root bytes 独立证明 |
| INV-W2E06 | ZIP/CSV/身份先于覆盖 | 多 member、CRC、路径逃逸、wrong member symbol/date/family、空/header-only CSV、第12列非数值/NaN、非整点、错误 close_time、重复 timestamp 必失败 |
| INV-W2E07 | 开栏覆盖与完整栏分开，缺时间不等于零样本 | AIA/PORT3 exact 窗口、跨 UTC 日、t=a/t=b、缺一个小时、零 Index close；不插值、不接受空 C 为 observed |
| INV-W2E08 | csv_invalid 字节保留，local failure 高于 remote terminal | invalid CSV 仍保存；atomic-write、disk-full、fsync、readback、manifest 发布前后 crash injection |
| INV-W2E09 | strict reader 只独立重算 Class A，不升级 Class B | completed candidate with gaps 正例；额外 field/file、fake URL、wrong source、HTTP 404 配 fetched_verified、HTTP 字段 bool、伪 coverage/count/root-state mutation 拒绝；reader result 不含“GET 已发生”结论 |
| INV-W2E10 | schema、旧包与权限隔离 | old REEF/002/W1 reader 对新 schema/root 拒绝；旧 source/artifact SHA 前后不变；13 flags 精确 false |
| INV-W2E11 | production wiring 唯一 | CLI 真实调用新 source/loader；无 src→scripts、无网络 reader、无另一个同 schema validator |
| INV-W2E12 | producer/runtime identity 与 remote observation 有外部链路 | valid Class A root + valid §12.1 independent read-only audit review artifact 正例；错 Plan/Design/network SHA、错 manifest/run、source/config hash、argv、scanner RC、worktree/index evidence、attempt count、非 `complete` verdict 或 executor/collector 自写 review 都拒绝 W2-0 admission |
| INV-W2E13 | W2-0 outcome-blind 先于价格研究 | metadata-only 正例；缺 `preanalysis_blind_receipt` 或 `outcome_seen` 时 W2-0 只能 `exploratory_only`，不得产生 `alpha_candidate` / `alpha_validated`；任何 raw price-derived output 在 receipt 前为 admission failure |

正向边界 fixture 必须由真实 verified C、verified-002 和 canonical 新构造器派生。九份真实 ZIP/CSV 为 parser/复制正例，不能拿随便制造的字典或 foreign hash 绕过 loader。171 个未知远端对象在离线 collection 测试中可使用明确标记的 HTTP failure transport fixture，产出合法的 gaps-root 正例；不得把 synthetic transport transcript 当生产下载证据。pure grid 单元测试允许 synthetic 行且必须明确不跨 upstream 信任边界。未来单次授权采集后，strict reader 只审计 Class A；独立 Completion Audit 另行核验 exact producer/runtime identity 并返回 Class B external review artifact，二者都不能以联网测试替代。

未来 Plan 必须逐 INV 映射 Task、RED/GREEN、实际 RC、anti-shortcut scanner 的 source+script+tests 扫描和 warning disposition、Task 0 baseline/index/scope proof，以及独立只读 Completion Audit 的 §12.1 review artifact 交付。镜像 fixture 修改前必须断开硬链接或直接独立复制，不能污染真实 authority。扫描/测试通过不代替 Class A reader、Class B external review artifact、authority 或网络授权。

## 12. 权限、兼容性与 Rollout

所有 artifact 的 `authority_flags` exact keys 全为 singleton `false`：

```text
RISK_LIVE_TRADING_ENABLED, trade_signal_allowed, paper_trading_allowed,
live_trading_allowed, execution_engine_allowed, private_api_allowed,
authenticated_api_allowed, order_api_allowed, alpha_interpretation_allowed,
execution_feasibility_claim_allowed, net_cost_or_profit_claim_allowed,
replay_allowed, point_in_time_directional_replay_allowed
```

Design 当前 `implementation_allowed=false, network_collection_allowed=false, commit_allowed=false, push_allowed=false, deployment_allowed=false, SSH_allowed=false, runtime_action_allowed=false`。未来唯一可独立批准的是本地一次性 public archive GET，不变更任何交易权限。

旧 W1/REEF/root 不迁移、不重封存、不更新 SHA。W2 新 schema 对旧 reader 不兼容是有意的。未来 W2-0 admission 必须同时冻结本 Design SHA、approved implementation Plan SHA、network authorization SHA、真实 final manifest SHA、§12.1 independent Completion Audit review artifact 的 path+SHA、§12.2 `preanalysis_blind_receipt`，以及后续分析 Design SHA；不能把 171 个请求完成、root schema 通过或 Class A reader 通过当分析准入。

### 12.1 External Completion Audit Binding

Completion Auditor 依 `.agent/skills/audit-plan-completion/SKILL.md` 严格只读：不得创建、修改或补写项目文件、fixture、文档、candidate root、runtime evidence 或本 Design 的任何 artifact。它只返回 `complete`、`incomplete` 或 `blocked` 的 external review artifact；该 artifact 由审计会话/平台外部保存，不能由 collector、executor 或 auditor 写入 workspace 后再被当作审计输入。

只有 `complete` artifact 可被 W2-0 引用。未来 W2-0 Design 必须把其外部 `path` 与原始 bytes SHA-256 一同冻结，并要求 artifact 精确记录：auditor identity/session；approved Design/Plan/network-authorization 的 path+SHA；run ID、candidate root relative path、final manifest SHA；实际 entry point 与 command argv；approved Plan runtime allowlist 的 source path+SHA、实际 `configs/base.py` SHA、Git HEAD；anti-shortcut scanner command 与 actual exit code `0`；runtime path、index 和 untracked runtime path 的 clean evidence；以及 producer-attested `network_attempt_count=171`、distinct FETCH URL count `171`、no-retry/no-redirect assertion，和“未记录请求不能由本地 bytes 独立排除”的声明。

W2-0 admission 对这个 external artifact 执行 byte-SHA 与内容核对，但它不是新的 machine-readable runtime root，不要求或允许任何 post-audit publisher。artifact 的 Class B 结论仍不是 wire-level HTTP 重演；它仅将 independent read-only audit 所核验的 producer/runtime identity 与 manifest 绑定。缺 artifact、非 `complete` verdict、缺任何上述 binding、路径/SHA 不匹配，或 artifact 显示 scope/runtime drift 时，W2-0 fail closed。

### 12.2 Pre-Analysis Blind Boundary

在 W2-0 analysis Design 的 approved SHA 与对应 `preanalysis_blind_receipt` 冻结前，只允许检查 root/Completion Audit artifact 的 metadata：文件存在性、路径、hash、schema、`fetch_status`、coverage status、缺失计数和 `temporal_status`。不得向人类或研究接口显示、导出或计算 OHLC 值、basis、return、MAE/MFE、方向结果或任何 price-derived statistic。为完成 §8 的类型、CRC、hash 与网格验证，collector/strict reader 对原始行进行的无输出解析不属于 outcome inspection，且不得生成任何价格派生报告。

未来 W2-0 Design 必须把 root 外 receipt 作为入参，至少冻结：`schema_version=stage1_6f_w2_preanalysis_blind_receipt_v1`、analysis Design SHA、final manifest SHA、Completion Audit review artifact SHA、`outcome_inspection_status` 和签发时间。`outcome_inspection_status=not_seen` 才可开始 preregistered W2-0；如果 raw CSV 或任何 price-derived outcome 已被人查看，必须为 `outcome_seen`，该数据上的 W2-0 只能标记 `exploratory_only`，不得产生 `alpha_candidate`、`alpha_validated` 或确认性经济结论，后续必须另有 holdout/independent sample。

原始 CSV 在 candidate root 中可读，系统不能从本地 bytes 证明某个人从未查看过它；receipt 是 fail-closed 的研究治理声明，而非对人类观察行为的密码学证明。缺 receipt、状态不精确或无法证明 `not_seen` 时，默认 `outcome_seen`。

VPS rollout/rollback：N/A，范围内没有部署、常驻进程或线上状态变更。本地不合格 package 的回退是停止消费并保留取证，没有“用旧成功摘要代替”路径。

## 13. Open Questions 与交付门禁

| 问题 | 处理与 owner | 是否阻断本采集 Design 的 Plan |
| --- | --- | --- |
| 171 URL 今天是否可取得 | 未来获授权 collector 输出逐对象终态，不预先保证 | 否，失败分支已冻结 |
| 10 个 settlement facts / 41 个 restriction facts 是否可从公告进一步解析 | 独立语义证据任务；本文保持 not_stated、不补 current FAQ 默认值 | 否；但会限制未来 W2-0 claim |
| Class B runtime observation 是否可被 wire-level 独立证明 | 本 Design 不引入 packet capture；§12.1 将 producer/runtime identity 绑定到 independent read-only audit artifact | 否；无合格 review artifact 则该 root 不能进入 W2-0 |
| W2-0 前是否发生 price outcome inspection | 按 §12.2 提供 external blind receipt；无法证明 not_seen 时 fail closed 为 `outcome_seen/exploratory_only` | 否；但阻断确认性 W2-0 claim |
| W2-0 是否必须补分钟/秒级、怎样判研究去留 | 后续分析 Design owner 决定；本文无晋级/终止经济判断 | 否，不进入本次 implementation |
| Graphify 当前环境不可用 | 拓扑已回到源码验证；未来 Plan 的工具 gate 按当时 canonical workflow 处理 | 否，本 Design 不安装工具 |
| 草案是否足以审批 | 独立 B review 与用户审批 | 是，在完成前不得编写实施 Plan 或采集 |

作者自审需检查 schema 守恒、时间截断、复用/no-fallback、Class A/B/C 信任边界、read-only Completion Audit 外部绑定、outcome-blind 边界、reader/crash 路径和所有 source binding。作者不能自我批准。交付仅此 candidate Design；下一步为独立 Design closure review，不是实施、下载或分析。
