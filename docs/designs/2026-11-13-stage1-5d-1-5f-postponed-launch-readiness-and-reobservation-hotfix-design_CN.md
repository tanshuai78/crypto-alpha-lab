# Stage 1.5D / 1.5F 延期合约交易状态门禁与新批次重新观察最小修复 Design

日期：2026-11-13（Asia/Shanghai）。状态：`design_candidate / pending_independent_review`。

本次只起草 Design，不是 Implementation Plan 或执行授权。代码、配置、旧数据和 VPS 均未修改；`RISK_LIVE_TRADING_ENABLED=False`，只读影子边界不变。D2 研究继续暂停。本任务修复采集正确性，不研究收益或 Alpha，L2 §15 的策略研究条目不适用。

## 1. 目标与证据

**目标：公告时间到达且 symbol 存在，不再被误认为已经可交易；延期能沿原有修订链传递；对指定两合约在新批次重新核验、等待并观察，而不复活旧失败记录。**

用户已明确要求恢复公告 `2d89a5966b174a2689ab2c2a15db1757` 的 `HYPEUSDC`、`TRXUSDC`，目标是跟随最新官方计划，而不是硬编码 11 月 16 日强行采集。

### 1.1 已确认事实

| 事实 | 证据与限制 |
| --- | --- |
| 本地基线 | HEAD `2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`，起草前工作区干净 |
| VPS 身份 | 用户提供的版本取证为 HEAD `84d6b093dcdb950e190844ca69718fee9f3c21cf`；D/F runner、F loader/client/state、D revision producer 六文件 SHA-256 与本地一致。配置差异仅是后续 1.6F-W2/J-A 追加，不涉及本次 D/F 配置 |
| 故障报告 | 本地 `evidence.txt` 为 49,912 bytes，SHA-256 `b265b63c7feefd70e2a154042999a5a56a1dbde9021806b8f543ea9e5ee0a80c`，捕获时间 `2026-11-13T08:55:49Z`；这是人工取证报告，不是生产准入 artifact |
| 初始正文 | 11 月 11 日 05:01:40.644 UTC 的详情请求成功；报告记录原始正文 82,480 bytes、SHA-256 `97710e4b2be7c852e26baa5a4f451db5f13b40e94dc85b7ae0ed8d52f2c1947d`，解析取得 09:30 / 09:35 UTC 两个计划时间 |
| 发出事件 | 05:12:43.709 UTC 完成 symbol 解析；两 symbol 状态均为 `PENDING_TRADING`。多合约路径允许已确定身份与时间的预告提前 emit，这不等于 F 已可开始采集 |
| 空跑结果 | 两合约分别从 09:30:33.962 / 09:35:34.769 UTC 开始；各 717 次尝试、717 次 HTTP 成功、0 个有效盘口、717 个无效盘口，最终均 `completed`。合计 1,434 次是状态计数对账，未逐条重放原始盘口 |
| 溯源丢失 | 请求和解析记录有上述正文哈希及节点路径，最终事件却为 `detail_fetch_attempted=false`、`detail_payload_hash=null`、`node_path=title_or_exchangeinfo`；identity index 的 payload hash 也为空 |
| 修订实际关闭 | D runtime gate 为 `READY`，但 `schedule_revision_producer_effective_enabled=false`、health 为 `producer_disabled`；F 没有应用 schedule revision。已检查的 11–13 日请求记录没有该公告的后续详情请求 |

报告位于 `/private/tmp/stage15-evidence-full.7IGm6x/evidence.txt`，其来源是 VPS `/tmp/stage15-postponement.WsVDPD/evidence.Gj3QdN`。临时路径不是持久证据根；审查引用上述摘要和报告哈希，部署前另保全精确来源，不扫描或修改旧根。

**尚未独立证实：**原始 82,480-byte 文件未在本次本地审查中重新取得；新版官方正文、当前完整 `exchangeInfo` 原始字节及 F 在旧开盘时刻使用的完整响应未包含在报告中。用户已核实的新计划为 11 月 16 日 08:30 / 08:35 UTC，`onboardDate` 分别为 `1794817800000` / `1794818100000`；这些是恢复前待新采集核验的输入，不是本次已完成的真实 fixture 验证。

### 1.2 根因与非故障性澄清

- [F 首次准入](../../src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py)的 `classify_event_symbol_eligibility_with_diagnostics()`、pending 重检及 runner promotion 没有共同落实交易状态门禁；v2 anchor 分支虽记录当前 `onboardDate`，也不能据此假定当前冲突已被阻断。
- [D runner](../../scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py)的 BAPI 等待分支漏存详情溯源；已正式发出的文章终态缺少有界改期重查。现有 revision classifier 依赖改期关键词，且丢弃同一文章 ID 的自链接，因此单纯重新 GET 不足以处理原地替换日期。
- 新 D 默认会将启动前公告记录为 bootstrap 存量；旧 `completed` 不会因新版本代码或修订自动重新采集。新批次必须有显式恢复路径。
- `717/720` 使时间覆盖率为 99.58%，不证明盘口健康。`completed` 与当前 `research_result_valid` 不得用于宣称旧数据有效；本次不重定义全项目覆盖率或 1.5G 质量规则，也不宣称下游曾接纳这些数据。

## 2. 范围、最小化与契约覆盖

范围限定为 D/F 的准入、详情元数据、延期重查/生产接线、指定新批次恢复及直接回归测试。复用现有 parser、详情队列与 HTTP 预算、append-only raw/version registry、formal v2 builder/index、revision registry、pending reducer、runtime attestation 和部署手册；不建立新的服务、通用恢复框架或行业/研究管道。

| 较小替代 | 本次取舍 |
| --- | --- |
| 只给 F 加一个 `TRADING` 判断 | 必须做，但不能修复官方时间更新、溯源和旧事件在新根的恢复，不能独自完成目标 |
| 只开启 revision producer 或扩大超时 | 不补同页识别与重查，且不能把未验证的 prerequisite 变为事实；不采用 |
| 复用 D/F 现有链，增加一个明确恢复选择及有界详情重查 | 采用；新增负担集中在状态门禁、同页 L1 关联和真实启动/消费测试，不重构大模块 |

本 Design 获批后仅对下表作前瞻性局部增补，不修改历史 Design 原文件或历史产物：

| 既有边界 | 本次覆盖 | 保留部分 |
| --- | --- | --- |
| [多合约 all-or-none](2026-07-29-external-signal-shadow-lab-stage1-5d-1-5f-multi-symbol-all-or-none-emission-admission-dedupe-hotfix-design_CN.md) | F 进入采集另需当前交易状态 | D 可提前发预告、候选集身份、all-or-none emit 与 per-symbol 去重 |
| [pending deadline](2026-08-11-external-signal-shadow-lab-stage1-5f-pending-anchor-deadline-state-semantics-hotfix-design_CN.md) | 增补“到点仍未可交易”与当前 API 明确冲突的有界处理 | 已有有效 future anchor 不因 6h 超时被提前杀死；官方修订先于 pending promotion |
| [历史 catalog 隔离](2026-09-01-external-signal-shadow-lab-stage1-5d-historical-catalog-re-admission-hotfix-design_CN.md) | 仅显式选择的新根 future-launch 重新核验可绕过普通 catalog 存量过滤 | 默认隔离、旧根 terminal 不复活、不得把旧发布时间改成新发布时间 |
| [revision producer](2026-08-04-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-rules-design_CN.md) | 已 emit 文章的 revision-only 重查及同页精确 L1 日期延后证据 | v2 transport、唯一关联、PIT、durable index、冲突和 registry 幂等 |
| [producer attestation](2026-08-10-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-git-ancestry-attestation-design_CN.md) | 无放宽 | 默认 disabled、Git ancestry/代码树证明、consumer 同根绑定和 sticky failure |

**不做：**旧根改写/删除/复用、补造 11 日盘口、全历史公告重入、跨根隐式扫描、symbol-only 修订、用 `onboardDate` 覆盖官方计划、增加交易或研究权限、全局质量指标改版。`active/completed` 收到修订后既有污染处理与原窗口语义不在本次重构；本次保证的是不因入场时已知的未交易状态而启采，不承诺消灭所有开盘后市场异常。

## 3. F：进入采集前统一检查当前交易状态

以下规则同时用于首次准入、`re_resolve_pending_anchor()` 和 runner 的 pending promotion，禁止某一路径只检查 symbol 存在或仅凭旧 `pending_ready_for_admission` 放行。以当前 poll 的最新可用正式 revision 确定官方 anchor，再检查 API，不改 source anchor hash 来掩盖冲突。

**时间冲突与执行优先级：**令 `S` 为处理最新合法 revision 后的可信官方 anchor，`O` 为当前成功、未过期且有效的 API `onboardDate`。延期冲突为 `O > S + EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS`，与 `status` 枚举无关；`TRADING` 不能覆盖该冲突。缺失/无效/过期的时间证据既不能证明无冲突，也不能据此推断新的官方计划。

在保留身份、安全、取消和 terminal 不复活等既有门禁的前提下，唯一执行顺序为：

1. 先应用本轮已通过身份、来源与可得时间校验的最新正式 revision，得到 `S`；再结合当前可信 API 时间判定冲突是否解除。已有冲突只有在 `S` 来源仍有效、当前有效 `O` 与 `S` 在既有 60s 容差内一致时才可解除；API 本身不能修改 `S`。仅状态变为 `TRADING`、API 证据消失或重复读到旧 event，不得清除已经记录的 unresolved conflict。
2. 若仍为 `pending_anchor_conflict`，只执行该 episode 的固定 6h resolution deadline，清空旧 `symbol_visibility_deadline_ms`，不执行旧 anchor 的 15m 启动/非交易拒绝条件，且不发 depth 请求。revision 到达但仍有未解冲突时也不得重置期限。
3. 冲突已合法解除后，先判断新 `S` 是否在未来；若是则回到 `pending_launch_time_in_future`。只有无冲突且已到 `S`，才按新 `S` 计算 15m 界限，再判断交易状态及其他准入条件，不能用解除冲突的当前时刻充当新 anchor。

| 条件 | 行为 |
| --- | --- |
| 已确认的 future official anchor 尚未到达、无冲突 | 保留 `pending_launch_time_in_future` 及既有 5 分钟 evidence refresh；清空不适用的 anchor-resolution deadline，不发 depth 请求 |
| `exchangeInfo.available=false`、缺 symbol/状态/有效 `onboardDate`、状态未知或快照失效 | 不得进入 `active`；沿用/细化 pending 诊断，不把旧缓存或缺字段默认成 `TRADING` 或“时间一致”；已有冲突保留其固定 6h episode |
| 任何状态下，API 的有效 `onboardDate` 比当前官方 anchor 晚超过既有 60s 容差，包括 `TRADING + future conflicting onboardDate` | `pending_anchor_conflict`，等待可信修订/证据化解冲突；保留 API hash、抓取时间和两个候选时间，不把 API 时间直接当官方修订 |
| 已到官方 anchor，但仍非 `TRADING`，且没有上述明确的新时间冲突 | `pending_exchangeinfo_not_trading`；等待到既有 recovery start 上限，不发 depth 请求 |
| `TRADING`、当前时间证据完整有效、无未解冲突且已到官方 anchor，其他来源/身份/容量等门禁全部通过 | 才能进入采集；普通事件仍按既有 2m clean / 15m recovery 界限分类，显式恢复另受 §5 降级限制 |

快照要求：`fetched_at_ms` 为有效时间，以 HTTP 返回后的实际准入决策时刻计算年龄，不拿请求前的 poll tick 误拒新响应；年龄下界为负的既有 `EXTERNAL_SIGNAL_STAGE1_5F_CLOCK_SKEW_TOLERANCE_MS`，上界为 `EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_REFRESH_SEC*1000`，并有实际响应 hash。网络失败即使保留旧 symbol rows 也不能作为可用响应。复用现有统一刷新与预算，不增加逐合约轮询器；若等待刷新导致超过 clean 界限，只能降级或拒绝，不能回写采集开始时间。保留既有 USDC/USDT 等产品范围，不把本事故修成仅支持 USDT。

**无冲突分支的固定 deadline：**到点等待交易就绪复用 `symbol_visibility_deadline_ms = S + EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS`。同一 `S` 下重复 poll、HTTP 成功或进程恢复不得延长它；非 `TRADING` 时 `now > deadline` 拒绝为 `rejected_launch_not_trading_timeout`。API/时间证据仍不完整时不得启动，也不能无限等待超过该界限。此 15m 条件不适用于未解除的冲突 episode；合法 revision 解除冲突后，旧期限废弃，按新 `S` 重新计算。`TRADING` 在恰好 15m 时仍按既有 inclusive recovery 边界处理，晚 1ms 不准入。

当前 API 明确冲突时复用 6h `anchor_resolution_started_at_ms` / `anchor_resolution_deadline_ms` 作为一个固定 unresolved episode，这是对既有 episode 触发条件的局部增补：首次发现该冲突开始计时，重复 hash/heartbeat 不重置；新可信官方修订可关闭此 episode，并按新 anchor 等待。先执行上述 revision/冲突判定，再在仍未解决且 `now >= anchor_resolution_deadline_ms` 时拒绝为既有 `rejected_anchor_conflict_unresolved_timeout`。不能每次重新解析旧事件就清空冲突或延长期限。14d future lead、6h unresolved 与 15m late-start 三种界限不能混用。

**序列验收与能力上限：**以 `S0=11-11 09:30 UTC`、09:31 首次冲突为例，固定 deadline 为 15:31。到 `S0+15m+1ms` 仍应是 pending conflict、无 depth、无 terminal；10:00 收到合法 revision 指向 `S1=11-16 08:30 UTC` 且当前可信 API 时间与之相符时，进入 pending future，清除旧 conflict deadline，后续 15m 界限按 `S1+15m` 而非 `S0+15m` 计算。对照分支无合法更新时，15:31 仍有冲突就终态拒绝；之后到达的 revision 不复活 terminal。普通 pending 链不保证等待超过 6h 才出现的修订，后续只能考虑 §5 已定义且另行授权的新根显式恢复，不能把 bounded failure 宣称为自动恢复成功。

## 4. D：溯源与有界延期重查

### 4.1 在所有成功详情分支共用真实元数据

可信 BAPI 解析成功后，在进入任何等待/emit 分支前保存既有字段：`detail_fetch_attempted=True`、`detail_payload_hash`、`detail_fetched_at_ms`、`detail_fetch_url_used`、variant、可信状态及实际 `candidate_provenance`。hash 对应真正保存的 raw bytes，抓取时间对应 manifest；不得用“最后某个哈希”猜测、写空字符串代替或将发布时间当新内容可得时间。

等待态序列化/反序列化、Block 2.5 emit、formal builder 和 index writer 均消费这些同一来源的字段。per-symbol `raw_time_text` / 节点路径应来自已解析的候选证据，不再将毫秒数字和标题包装成正文原文。此次不修补旧 index 的空 hash。

### 4.2 已 emit 文章只允许 revision-only 重查，不重新发 launch

在当前根 durable formal index 可关联的文章中，监测仍处于 `PENDING_TRADING` / `PRE_TRADING`，或存在 §3 延期冲突、已有未解冲突、尚未到官方时间等未确认交易就绪情况的 symbol。比较当前成功 API 响应与最新已确认官方计划；后者由 durable launch 加已通过身份/时序校验的修订按现有 selection 规则确定，不能始终取原 index 时间，也不能取 JSONL 最后一行。延期冲突使用 §3 同一时间条件，不依赖状态枚举；`TRADING + future conflicting onboardDate` 仍需保留同文章 watch。`onboardDate` 晚于计划是重查线索，不是修订事实。即使 API 尚未更新，也按冷却间隔有限重读，以覆盖原公告原地改期。

复用 `launch_schedule_revision_detail` 队列、详情端点、raw 保存和版本登记。已 emit article 的 launch terminal 状态保持不变，只准 revision 工作更新元数据；其他 bootstrap/historical/rejected terminal 不因此重入。工作归还后仍是 emitted terminal，不能再次写普通 launch。

新增且仅新增两项实际需要的节流配置，均位于 `configs/base.py`：`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_RECHECK_INTERVAL_SEC=600`、`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_RECHECK_BUDGET_PER_POLL=1`。后者是既有详情/HTTP 总预算的子集，不是附加额度；保留 never-attempted 的现有保底槽，预算不足时延后。多 symbol 同文章一次请求，不按 symbol 重复 GET。

用现有 scheduler article metadata 加入 nullable 的 `next_schedule_recheck_at_ms`、`schedule_recheck_deadline_ms`，不新建 watch 数据库。截止时间固定为原事件实际首次观测时间加既有 14d lookback，重复请求及重启不得顺延。只有当前成功、未过期且完整的证据确认所有 symbol 已 `TRADING`、各自官方时间已到且 API 时间与最新可信官方 anchor 在既有 60s 容差内一致、无未解延期冲突时，才可因“交易就绪”结束 watch；单独状态变为 `TRADING`，或时间缺失/无效/过期，不满足该结束条件。取消、超过原固定期限或根停止仍结束 watch，不能借冲突无限续期；后续终态市场不作为新上新重开。

### 4.3 同一文章原地延后作为受限 L1 证据

只有同时满足以下条件，才可走不依赖标题关键词的同页路径：

1. 详情确实属于该 `source_article_id`；旧 launch/index 已在当前根 durable，旧 payload hash 与来源可核验；新 raw hash 不同。
2. 新可信正文能精确解析相同候选 symbol 和各自时间；新时间严格晚于最新已确认官方时间。单纯 HTML/价格/杠杆修饰变化不构成修订。
3. 以“同一 article ID + 精确 symbol + 既有唯一 index identity”作 L1 关联；令 `supersedes_source_article_id` 等于该文章 ID。此自关联只用于版本延后，不扩张为 L4 symbol-only，也不因当前 index 看似唯一就猜测别的公告。
4. `revision_available_at_ms` 来自新 raw version 首次观测登记，不使用原 `releaseDate`、页面更新时间或重启时间回填。沿用 `revision_id == revision_semantic_id == revision_application_id`、semantic dedupe、append-only registry 和 per-symbol lineage。
5. exact-all-symbols 更新保持既有 all-or-none 规则；明确 per-symbol 更新遵循原 transport。symbol 变化、缺时间、同时间矛盾或无法唯一关联均 diagnostic-only。无关键词的提前/取消不由此新路径推断；既有明确修订/取消路径不变。

**durable 先于比较：**复用现有 raw/version 保存，先完成 launch + index 持久化，后 link/emit revision。producer 未有效启用时只能保存证据和诊断，不能 formal emit；不能把诊断写成“延期已传到 F”。同页语义已发而再次观测相同目标/内容时不产生第二次应用。

## 5. 指定两合约在新根重新核验

### 5.1 一个显式入口，不建设跨根迁移

在 D 增加一个默认不提供的 CLI 选择：`--future-launch-recovery <article_id>:<comma-separated-symbols>`。本次运行授权只能填写 `2d89a5966b174a2689ab2c2a15db1757:HYPEUSDC,TRXUSDC`；不在源码中硬编码事故日期或自动恢复所有旧事件。参数校验 article ID、非空去重 symbol 集，不能与 `--active-root-recovery-*` 混用。

它只适用于**全新 D/F 根**，不读取或改写旧 scheduler、state、watermark、index；无需构建新 curated snapshot 或修补事故旧 index。既有跨根 snapshot loader/linking 契约保持原样。D runtime gate 记录该恢复选择，F 在现有同根 attestation/root-contract metadata 中保留并核对它；这是对象边界，不授予运行权限。

D 仍先执行普通 catalog bootstrap。指定文章只进入独立的 revision/revalidation 工作入口，不能被普通 launch 分支抢先发出；默认历史隔离不变。**恢复详情请求与 launch emit 必须晚于 producer 有效启用、匹配新 F 的有效 consumer proof 和已完成 bootstrap 的 watermark 核验。**复用现有 consumer root-contract/summary 绑定，并核对该新根 watermark 的 source/root 身份；不以 sleep 或操作员“应该已经启动”代替。尚未就绪时 pending/diagnostic-only，不创建提前可消费的恢复事件；普通 launch collection 不因此停用。

### 5.2 重新取得当前事实，不搬运旧事实

通过既有 BAPI 和 parser 重新取得同文章正文，候选集必须与显式请求完全一致；当前 API 必须确认这两个目标产品身份。只有精确官方 anchor 在当前时刻之后、且满足既有 future lead 和来源规则时，才可创建新根的 formal v2 launch 及 index；否则 diagnostic-only，不重置老根。

保留原 `source_published_at_ms`；新根的 `detected_at_ms` / `detail_fetched_at_ms` 是本次真实重新核验时刻，不伪装成新公告，也不回填旧 hash。事件使用既有 article/symbol 身份和 dedupe 算法，不为避开去重随机造 ID；相同业务 ID 在不同根的发生由根身份区分。

恢复事件以既有字段携带新精确枚举 `detail_recovery_provenance=explicit_future_launch_revalidation_v1`，不得冒用 `active_root_retry_cycle_recovery_v1`。F 仅在标记与已绑定 D 恢复选择、article/symbol、正式 v2 来源及新正文时间全部一致时接受它。

F 对这类行的 delayed-launch 判断可使用经核验的 future official anchor，以兼容普通新事件先推进了 moving watermark 的情况；只覆盖这条显式恢复分支，不能把所有 BAPI/历史行加到豁免中。bootstrap seen identity、现根已受理/terminal 身份仍不得绕过；若恢复行意外提前进入 bootstrap，则 fail closed 并报告启动失败，不擦除 watermark，也不自动换根重试。

证据上限固定为 `recovery_validation_only`：`evidence_start_class=recovery_start`、`live_depth_evidence_basis=recovery_validation_only`、禁止 clean 晋级。F 的 admission/latest 证据字段及 accepted/state 接线一致下调上限，按既有规则生成 admission/latest hash；原始 source contract/hash 保持真实且不被改写，不能只写一个说明字段。新恢复分支仍必须通过 §3 的交易状态、未来/冲突、容量及 **15m late-start 上限**，不得借旧 recovery helper 的早退路径绕过。实际观察窗口仍锚定最新官方时间，不把晚启动改成新的 12h 窗口。

普通修订只更新同根 pending；旧根 `completed` 和当前根 terminal 不自动复活。若再次失败或错过窗口，明确报告失败，不能为凑成功循环新建根。

## 6. 持久化、兼容与验证机制

不新增机器消费 artifact 类型、通用 profile、Recorder 或独立 Verifier。继续使用既有 raw、request manifest、payload-version registry、scheduler、formal event/index、revision registry、runtime gate、F root contract/state。新字段是上述现有结构中的有界 additive metadata；缺省恢复选择表示禁用，新 recovery 枚举只有新代码和匹配根可消费。现有 v1/v2 事件与普通 active-root recovery 不能被误标为本次恢复。

schema/serializer、root-contract hash、生产/消费校验及持久化恢复测试必须同步支持这些增补；不得悄悄忽略新字段后仍称恢复已绑定。需要补充现有受保护 runtime manifest 的文件应在后续 Plan 白名单与 attestation 证明中明确，不绕过原证明链。既有 Rule 17 profile 和校验义务不变；CLI 参数与 metadata 不替代用户的操作授权。

复用现有 append/durable 顺序和幂等恢复：重复读取同版本保留 first-observed；事件已落盘而 index 未完成时不能先 link；同 revision 已应用则不重复移动 anchor；pending deadline 在重载后保持。保持已有 storage guard、网络失败和日志隔离，不为本次构建新的 WAL/崩溃状态机。

## 7. 验收不变量与独立测试

以下是后续 Plan 必须映射到具体任务/命令的验收边界，不是本次已运行或已通过的测试：

| 不变量 | 必须验证的公开行为与独立期望 |
| --- | --- |
| `INV-01` 安全与旧根不可变 | 交易开关及 signal/paper/live/execution 权限维持 false；运行禁令独立于 Design/Plan 批准；旧根内容/哈希不因恢复改变 |
| `INV-02` F 状态门禁 | 相同合法事件仅改变 API 状态：`PENDING_TRADING`、`PRE_TRADING`、缺失/未知、不可用/过期均无 depth 调用；只有满足全部门禁的 `TRADING` 可 active。增加 `TRADING + future conflicting onboardDate` 无 depth 的反例；缺失/无效/过期时间不能当作一致。覆盖 USDC/USDT、快照年龄/时钟边界、首次、pending 重检和实际 runner promotion |
| `INV-03` 时间/冲突与固定期限 | 无冲突时以 09:30 anchor 手算：09:32 为普通 clean 边界，09:45 为 recovery 边界，09:45:00.001 不准入；pending 不重置 deadline。冲突序列必须覆盖 `S0 -> 09:31 conflict -> S0+15m+1ms 仍 pending -> 10:00 合法 revision(S1) -> pending future(S1)`，证明旧 15m 不杀死 6h 内的有效更新，新界限为 `S1+15m`。负向分支无更新时 15:31 固定 6h 到期拒绝，后到 revision 不复活 terminal；原先的 future 5d、API 不替代官方时间规则不变 |
| `INV-04` 溯源闭合 | 一次可信详情先等待 symbol、再 emit：事件/索引 hash 与真实 raw/manifest 相等，fetched time、正文节点和原时间文字保留；经 serializer 重载后仍一致，缺元数据不伪装正文确认 |
| `INV-05` 有界重查 | 同文章双 symbol 最多一次请求；600s 前不重查，每 poll 最多一个预算内槽，never-attempted 保底不被占用；同版本及重启不延长 watch 的固定 14d 期限；launch terminal 不重新 emit。增加 `PENDING_TRADING -> TRADING` 但延期冲突未解时仍保留 watch 的序列；可信 revision 后重新按最新 anchor 判断，全部状态/时间证据一致且已到点才可因就绪结束。时间未知不提前结束，取消/固定期限/根停止仍有界终止 |
| `INV-06` 同页延期 transport | 两个可信版本、同 article/symbol 唯一 index：仅日期延后且无关键词也能形成 v2 revision，F 实际只应用一次；可得时间等于新版本首观测。仅 HTML 变化、缺 index/hash、L4、多匹配、缺 symbol 时间和同时间冲突均不 formal emit |
| `INV-07` 新根显式恢复 | 无参数时旧公告仍被隔离；参数错配、旧根、consumer 未就绪、bootstrap 身份已 seen、未知恢复标记均不绕过。新 consumer 就绪后目标 fresh revalidation 可进入 pending；moving watermark 后到仍按限定 future 例外处理；不扩大到第三个 symbol，不能 clean 或绕过 late-start |
| `INV-08` 真实接线与激活诚实 | 默认 producer disabled 时修订/显式恢复只有诊断，普通 launch collection 不变；已有 Part A、真实 fixture、Git/consumer prerequisite 任一缺失即不能有效启用。实际 D poll → durable revision → F registry → pending anchor 的公开入口测试通过，不能以孤立 helper/静态导入代替 |

行为修改使用 `RED -> GREEN -> REFACTOR`。按 Rule 15，纯时间/边界/预算测试可使用最小合成数据；跨模块正向输入由现有 formal builder、serializer、strict validator 和真实临时 Git 仓库构造，期望日期、次数及字段由手算规格独立确定。不能手填伪 manifest/哈希来绕过 attestation，也不能调用被测 selector 自证期望值。

真实官方正文需按精确路径/URL与授权取得原始字节、保留抓取时间和 hash；从取证文本摘出的 JSON 不能冒充 `real_frozen_bapi_payload`。旧 AIA 真实 fixture/prerequisite 与本次同页真实样例分别验证，不能互相替代或先把 `REAL_FIXTURE_VERIFIED` 置 true。只有代码/合成测试完成时，报告应明确真实样例和线上观察尚未验收。

直接影响的实现位置预计为 D runner/scheduler/producer、F loader/models/runner 及其现有单元/入口测试、`configs/base.py` 和部署手册；正式文件白名单及执行命令只在获批 Design 后的 Plan 中冻结。不得借此拆分或重写数千行模块、修改 1.5G 业务规则或扩展研究脚本。

## 8. 部署、停止与批准边界

1. 本文经独立 B review 和用户精确版本批准后，才编写 Implementation Plan；Plan 的实施批准不自动允许 commit/push、SSH、部署、API 实测或采集重启。
2. 编码阶段保持 producer 默认 disabled。代码/回归及独立 completion audit 完成后，另行取得代码提交、真实 fixture 核验和部署/运行授权。已有 proof commit ancestry、受保护代码树、四项 enablement 配置白名单和匹配新 F 的 attestation 不得被删减；未满足时明确未启用，不能只手改开关伪造通过。
3. 获授权后，在新 `RUN_ID`/D/F 根部署同一受审代码，D 指向新 F consumer 证明路径、F 指向新 D 源与 gate；F 完成 bootstrap 后才允许目标恢复请求。旧根只读保留，既有 raw 保留期限规则不因本次故障改变。
4. 通过新获取的官方正文/API 核验目标身份、当前计划及 `TRADING` 转换。当前目标时间仍是条件而非保证：按 08:30 / 08:35 UTC 和既有 12h 窗口，至少运行到 11 月 16 日 20:35 UTC；再改期则重新计算。原 D 七天期限约在 14 日到达，仅是切换排期/空窗风险，不作为修改全局时限或跳过批准的理由。
5. 门禁冲突、source/consumer binding 失效、真实正文不支持目标、超过固定期限或存储安全不足时，保留诊断并停止该恢复/正式修订，不放宽门禁。未来窗口已经错过时报告未达成，不通过重置时间或再次试跑制造完成证据。
6. 分别交付“代码实现与测试”“真实来源及启用证明”“新批次目标观察”的事实；后两项未执行时不得宣布恢复成功。旧数据和新数据均需按原 1.5G 准入独立审核，不能因 `completed`、HTTP 200 或时间覆盖通过就晋级。

没有需要用户再次确认的目标问题。保留的是真实样例/最新时间、部署身份和未来观察结果等后续可执行门禁，不将它们冒写成已完成，也不以它们为由继续无限元数据取证。若实施必须改变未列明的上游契约，按 L1 Rule 16 停止并分流，不能静默扩展。
