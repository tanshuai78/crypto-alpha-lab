# Stage 1.5J-C：新合约上线时间与路径可行性诊断 Design

**日期：** 2026-10-23

**状态：** `revision_candidate_for_closure_audit` / `hypothesis_only`，未批准实施。

**事实核对基线：** `f7118978d6a446fe4bac156979053667ec51b2e7`。本次只读取文档、源码及轻量收据/分类字节；没有解压归约、生成研究收据或核验远程运行态。

## 1. 决策摘要与问题边界

本阶段只回答：**实际首笔成交 60 秒后观察，再假设等待 3 秒，到首笔成交后第 15 分钟为止，还剩多少价格空间？按成交先后顺序，是先触及固定目标线还是固定风险线？**

选择“独立、离线、单场景诊断”，不建设特征库、预测模型、撮合器或交易系统。Pre-Market Crypto 与 Standard Crypto 分开，long/short 两个方向机械并列，不逐事件事后择优。

| 方案 | 结论与理由 |
| --- | --- |
| 直接从 J-B 的 5m/1h/4h 汇总推断 | 不采用：没有 63 秒参考价和 15m 路径顺序，无法回答问题。 |
| 新建逐秒特征库、搜索观察点和阈值 | 不采用：超出最小问题；旧样本反复查看，容易把可行性诊断变成因子择优。 |
| 独立 J-C reader/reducer，小型封闭诊断收据 | 采用：复用认证 raw 入口但不修改上游，新增一个研究场景和一个独立治理 profile。 |

J-C 是历史事实诊断，不证明存在可实时识别的筛选器。它最多为“停止当前场景投入 / 单独申请下一项解释性研究 / 记录证据不足”提供依据；不自动开启所谓 J-D。

**当前授权只覆盖起草本文件。** Design 批准不等于 Plan 批准，Plan 实现批准也不等于生产数据消费或收据生成授权。

## 2. 已确认事实与权威来源

### 2.1 来源优先级

L0/L1/L2 和冻结上游契约优先于讨论稿、预审叙述和本 Design 的假设。本文不修订上游 authority；若下列复用在实现时与冻结契约冲突，按 Rule 12 停止，不就地修改上游。

| 来源 | 路径或唯一身份 | 本次核对结果 / 用途 |
| --- | --- | --- |
| 决策表 | `docs/reviews/2026-10-23-next-research-readiness-decision-table_CN.md` | SHA-256 `6b7e6f1f6391a89fbe6db0367791485542e80a998682bd14d717d1223ae51359`；研究边界与选线依据。 |
| 本地预审 | `docs/reviews/2026-10-23-next-research-readiness-precheck-report_CN.md` | SHA-256 `f79b349906bf6089e88d7e9fc8dcb47d01d29a110a95e4bda5e89035705ede7d`；只支持准备度，不替代 raw 准入。 |
| J-A root，以下简称 `JA` | `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z` | 原始 ZIP、CHECKSUM、公告正文和 manifest 的唯一输入根。 |
| J-B root，以下简称 `JB` | `data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z` | 锚点与 child 集合的唯一输入根，不存放原始 ZIP。 |
| 分类账本，以下简称 `LEDGER` | `data/exports/stage1_5j_token_launch_classification_ledger_v2.csv` | SHA-256 `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b`；只提供固定分类及证据定位，不提供价格。 |
| V2 宽表 | `data/exports/stage1_5j_full_year_token_launch_dataset_v2.csv` | SHA-256 `c7fab484b2fe0968bc2b0c44347f1ec292a86eb687961122c2d2bcdb278ab339`；背景材料，不是 J-C 计算输入。 |
| J-B streaming Delta | `docs/designs/2026-10-13-external-signal-shadow-lab-stage1-5j-b-verified-archive-streaming-reduction-remediation-design-delta_CN.md` | SHA-256 `7e305093027de1d7c9f3d3221aaa237def317c4033e4bed3e837697fe94c0a9d`；现有读取与流式约束。 |

下列 SHA 是读取前必须 exact compare 的冻结值，不允许现场 rebaseline（重算后替换期望值）。

| 文件 | SHA-256 |
| --- | --- |
| `JA/manifest.json` | `b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf` |
| `JA/summary.json` | `722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b` |
| `JB/manifest.json` | `f0a8ac724925084161f6b9aa2dced5139b261707fda0f0f21ebd0eb6de3087fb` |
| `JB/summary.json` | `5ea0f1c87803114c4c6917cd0c3d24292948fa0e7066a80e0a2bce611e32546b` |
| `JB/review_CN.md` | `17e9ffaa973923868621a8ee925dc811c15e12459924ee63897f9c21fcac317e` |
| `configs/base.py` | `473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc` |
| `configs/stage1_5j_b_historical_aggtrades_launch_response.py` | `771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4` |
| `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py` | `250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18` |
| `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py` | `b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f` |
| `scripts/external_signal_shadow/export_stage1_5j_dataset_v2.py` | `b70faa18f4da875d1c3db950b312d97f49551b4887f22c2baf3b96531e6926d8` |
| `scripts/external_signal_shadow/verify_stage1_5j_dataset_v2.py` | `52623af3d766ad52e45b0ca61dd748340cd664644f855b800f5cd7ffc28fb3ee` |
| `scripts/governance/verify_artifact_schema.py` | `7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473` |
| `scripts/governance/verify_stage1_5j_b_receipt_schema.py` | `442c527fb7f49d78eff4e13fd68e5fabfff12ba1e74089cd5e5133977cde90f1` |

J-B 的治理闭环凭据固定为 `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/64e14726202b53727a7627139578369cb6af54f08d5a785d4df006009eb25a2d/evidence/receipt_closure_evidence.json`，SHA-256 为 `8d535303d61b3860eaa69018eff3f76645f91b3e27af1af89e1e956b948f8b6d`。须验证同名 `.json.sha256` sidecar、29 键契约和 `JB` 三件套绑定；不得换用旧执行树。J-A 既有闭环凭据由冻结的 `admit_upstream_j_a_root` 按现有契约检查，不复制或改写。

### 2.2 事实、假设和未证明事项

- J-B child 分母为 281：278 个 `anchor_found`、2 个继承父级 gap、1 个 anchor delay exceeded。其锚点最大延迟为 **300,000ms**，不是 60 秒。
- 当前账本选入 `crypto × standard` 53 行、42 个 Parent；`crypto × pre_market` 18 行、18 个 Parent。前者有 51 个 anchor、2 个 gap；后者 18 个 anchor。J-C 的预期分母是 **71 行，不是只选 69 个成功锚点**，更不是把 281 行称为 281 个独立币种。
- 预审的 278/278 日期包覆盖是元数据初筛，不是本次重验结果。1h gap 不推出 15m gap；完整 1h 也不保证第 63 秒附近存在及时成交。
- 本地 `RISK_LIVE_TRADING_ENABLED=False`；没有核对 VPS 状态。没有历史 L2 深度，AggTrades 不能证明排队、冲击成本、可成交仓位或止损成交。
- 60s/3s、参考价新鲜度、摩擦与价格障碍均是**预设研究场景**，不是测得的 API 延迟、实际滑点或最优策略参数。旧样本全部仍为探索集。
- Graphify 查询因本地缺少模块返回 RC=1；旧图谱早于当前基线。本设计按 `rg`、函数源码和测试核对拓扑，未安装工具或更新图谱。

### 2.3 本轮修订的本地拓扑证据

本轮以当前工作区只读核对 `HEAD=f7118978d6a446fe4bac156979053667ec51b2e7`，Git 仅显示本 Design 为未跟踪 candidate；没有核验 VPS 或运行中进程。`configs/base.py`、J-B core、J-B verifier、Rule 17 parent Design 和 J-B 三件套/closure evidence 的实际 SHA 分别与 §2.1 所列身份一致。本证据仅证明本次候选引用的本地字节，不替代未来 Task 0 对当时 workspace 的重算。

J-A 对外提供 `load_verified_stage1_5j_a_historical_archive_coverage_root(root_dir)`，其返回经验证的 `archive_package_records`；J-B 对外提供 `load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(root)` 和 `validate_zip_archive_package(zip_path, ...)`。J-B 的 `_open_verified_package_stream` 与 `_ChunkBoundedReader` 是私有实现，不是 J-C 允许依赖的跨阶段接口。本版据此将 J-C package admission 收敛到自己的 core，见 §4.1；不修改或扩大 J-B API。

## 3. 冻结研究协议：不搜索参数

### 3.1 单一协议输入

后续 Plan 仅物化一个不可调整的研究输入文件 `docs/production_artifacts/stage1_5j_c_time_path_protocol_v1.json`，精确内容如下。JSON 使用 UTF-8、排序键、无空格分隔符、末尾一个 LF。本文对象机械序列化的 SHA-256 为 `4dd353751256191d75fc52388413d97e5a7b177e499bbee28e2dd2ff356e1cbe`，由获批 Plan 绑定；执行者不得选择参数。

```json
{"endpoint_max_age_ms":1000,"entry_max_wait_ms":1000,"friction_bps":[50,80,150],"horizon_ms":900000,"latency_ms":3000,"observation_ms":60000,"protocol_id":"stage1_5j_c_time_path_v1","protocol_version":1,"risk_bps":200,"target_bps":3000}
```

该对象是收据 profile 的版本化**描述性测量输入**，不是配置模块，也不提供共享风险、策略、仓位、入场、退出或执行参数：它不能被 CLI、环境变量、运行配置或调用方覆盖，不能被交易代码读取，也不触发任何交易行为。`risk_bps` 和 `target_bps` 仅命名历史路径的两个观察障碍，分别表示“达到 +3,000bps 前是否先观察到 -200bps”；它们不等同于下单止损、止盈或资金风险限额。

因此 J-B 的阶段本地配置例外不被继承、也不需要为 J-C 新建例外：不创建 `configs/stage1_5j_c*.py`，不修改 `configs/base.py` 或 J-B config，不将这些数值写成 `src/` 中的魔数/可调默认值。producer 只读取获批 Design/Plan 绑定的精确协议字节；独立 verifier 的字面 profile 重复声明该固定对象。若以后要求把任一字段变成可调研究配置、策略规则或执行阈值，必须先提出新的治理 Design；本 Design 不授权这种变更。

选择 200/3000 bps（2%/30%）只为诊断此前“小亏 2%、争取 30%”设想的**价格路径必要条件**，不是推荐下单参数。它不涵盖所有可能策略，也不把低目标触及率直接解释为失败。100% 目标、多组障碍网格、30 秒观察等均不纳入本版。

### 3.2 时间与参考成交

全部时间是 UTC Unix 整数毫秒；不得经 float 秒数往返。每个事件键为 `(parent_article_id, symbol)`，其中 Parent 映射 J-B 的 `source_article_id`。同名 symbol 不得跨 Parent 借数据。

1. `T0` 是上游已准入的实际首笔成交时间；须用 raw 重证时间和价格与 J-B anchor 一致。J-B 原有 launch-time/300s 规则保持不变。
2. `T_obs = T0 + 60000`，`T_decision = T_obs + 3000`，`T_end = T0 + 900000`。终点不是入场后再等 15 分钟；“开盘后前 60 秒”不是开盘之前。
3. 参考成交 `entry` 为物理顺序中首笔 `T_decision <= transact_time <= T_decision + 1000` 的成交。没有则 `entry_unavailable`，不得放宽等待或回填最后成交。
4. 终点成交 `endpoint` 为物理顺序中最后一笔 `T_end - 1000 <= transact_time <= T_end` 的成交。没有则 `endpoint_unavailable`。这不是未来价格、插值或成交保证。
5. 路径包含 `entry` 本身及其之后直到 `T_end` 的全部记录。long 和 short 使用**同一个观察价格基准**，不按主动方筛出不同入场时间。不得称为买一/卖一/中间价；主动方成交价也不能冒充可成交报价。
6. `entry` 同毫秒之前的记录不进入路径；之后的记录按 aggregate trade ID 与物理行序处理。最值重复时取首次达到的记录。1 秒桶不参与任何计算，不新增桶输出。

### 3.3 精确归约与首次触及

以 `Pe` 为 entry 价格，`P` 为随后观察价格，定义初始名义金额归一的方向性价格变化：

```text
long_bps(P)  = 10000 * (P / Pe - 1)
short_bps(P) = 10000 * (1 - P / Pe)
MFE = max(direction_bps(P))，包含 entry，故 >= 0
MAE = min(direction_bps(P))，包含 entry，故 <= 0
terminal_bps = direction_bps(endpoint_price)
cost_adjusted_space_bps(c) = MFE - c，c in {50,80,150}
```

MFE/MAE 分别为有利/不利价格极值，不是收益或回撤承诺；short 公式不是保证金收益，也不是现货可借币证明。`MFE-c` 只是固定成本假设下的完美择时空间代理，**不是严格的可执行净收益上界**，不含 funding、冲击、容量、保证金、强平或订单失败。

首次触及按未舍入值判断：有利变化 `>=3000bps` 为 `target`；不利变化 `<=-200bps` 为 `risk`；到 `T_end` 都未发生为 `neither`。只记录最先发生者及实际触发成交，不假设该线成交，不将触及风险线的价格限制为 -200bps。跳跃直接越过风险线仍记 raw 观察价格；不生成止损后 PnL。第一触及之后继续计算全窗口 MFE/MAE，避免把二者混作可同时实现的收益。

CSV price/quantity 解析为有限正 Decimal；所有价格比、平均数、分位数与判断使用十进制值对应的精确有理数（stdlib `Fraction`），禁止 binary float。机器指标写成约分后的 `numerator/denominator` 字符串，分母为正、分子为整数、0 只能写 `0/1`，例如 `200/1` 表示 200bps。Parent/group 必须从精确值重算，不能从展示小数反推。人类展示如需小数，统一 8 位、`ROUND_HALF_EVEN`，不参与任何判断。raw price 字符串原样保留。

## 4. 原始数据准入与单向依赖

### 4.1 准入顺序

生产入口必须先完成 §9 的新 consumer 授权，再进行以下步骤；不得因为旧 J-B loader 可调用而视作获准消费。

1. 检查 §2 的精确路径、SHA、source import origin 与闭环凭据；执行 J-A/J-B 公共 strict loaders，保留其原有全部检查。J-B loader 内部的 J-A 重放不能降级成只读 JSON。
2. `LEDGER` 的 12 列精确为 `parent_article_id,symbol,asset_class,listing_regime,classification_status,table_index,symbol_column_index,field_header,raw_cell_value,evidence_locator,source_relative_path,source_sha256`。281 个联合键须唯一且与 J-B child 集合双射，全部对应记录不得缺列或多列。
3. 分类标签仅消费冻结账本，不新训分类器。对选入行，校验 `confirmed`、公告路径必须为 JA manifest 中该 Parent 的正文、SHA、table/column/header/raw-cell 及 symbol 列对应；按冻结 exporter 的 AST 遍历/文本提取语义重解定位，并核对标题 `pre-market`/`pre-ipo`/其余的机制映射。只在新 core 内写必要的独立定位验证，不从 `src/` import `scripts/`，也不重新导出或覆盖 CSV。定位不能唯一重证则 STOP，不用 symbol 名称猜测补齐。
4. 对 anchor 合格的选入 child，计算 `[T0,T_end]` 交集 UTC 日期；日期包须来自已验证 J-A summary 的该 Parent/symbol/date package record，且 logical identity、manifest 成员、请求记录和文件 SHA 对应。不能只组装文件名找到同 symbol 的 ZIP 就读取。
5. J-C core 自己执行 package admission：只接受步骤 1 返回的 J-A `archive_package_records` 中原对象，不接受手工 dict；核对五字段 logical identity、`archive_verified_with_post_launch_rows` 状态、JA manifest/request 关系、受控路径、无 symlink、CHECKSUM 语法和实际 SHA。它调用冻结 J-B 的公开 `validate_zip_archive_package` 做 ZIP/CSV/ratio 资源预检，并以 J-B config 的已绑定 `EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES` 构造 J-C 本地有界 reader。不得 import 或调用 J-B 私有 `_open_verified_package_stream` / `_ChunkBoundedReader`，不得在 J-B 文件增加公开 wrapper。
6. 串行解析所需包到 EOF，完成 CRC、语法与顺序检查后才认可局部结果。不提前在 15m 退出而漏掉 ZIP 完整性验证。共享文件可重复读取但不能重复计事件；不建立持久缓存。

### 4.2 CSV 与缺口语义

精确 7 列 header：`agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker`。拒绝多/缺列、非有限/非正 price/quantity、非非负整数 ID/time、`first_trade_id > last_trade_id`、时间不在包 UTC 日期内、不合法 boolean 文本（只接受 `true/false/True/False`）。不静默跳坏行。每物理行的 UTF-8 字节数（含换行）不得超过继承的 STREAM_CHUNK_BYTES；用有界行读取拒绝超长行，不能先读完整巨大行再检查。

按 UTC 日期顺序打开包，包内保持原始行序。ID 必须严格递增，时间非递减；不排序修复、不合并重复 ID。连续 ID 仅作为本窗口成交序列完整性的诊断条件：从 anchor 到 endpoint 的相邻 aggregate IDs 若不连续，记 `sequence_gap`，**不推断为确认的数据损坏**；若有倒序/重复则契约 STOP。连续性检查覆盖 entry 之前，避免缺掉真正的首笔参考成交。不能从长时间没有成交本身推断缺记录。`max_intertrade_gap_ms` 仅计算 entry 到 endpoint 的相邻成交时间差最大值；单笔为 0，不把末笔到 T_end 的空闲时间混入。

两类失败严格分离：

| 类型 | 行为 |
| --- | --- |
| 身份/来源/哈希/权限/类型/顺序/资源约束违规 | 整次 STOP、非零 RC、无成功收据。不得转为“某币缺数据”后继续。 |
| 已准入源明确的父 gap、anchor unavailable、日期包业务缺口、无及时参考/终点成交、ID 连续性未知 | 保留该 child 分母并生成明确 gap state；不能填 0、借用他行或剔除后声称全覆盖。 |

有 package 已宣称存在但磁盘缺失是身份/完整性 STOP；只有已准入 J-A 状态本来不提供所需日期包才是 `required_package_unavailable`。`endpoint_unavailable`/`sequence_gap` 时，本版不发布局部 MFE 或触及结论，防止不完整路径混入完整统计。

### 4.3 资源与工程影响矩阵

沿用已冻结 J-B 读取器的 ZIP/CSV/ratio/chunk 上限和输出 root/free-space 上限，不新增资源 config：ZIP 256MiB、CSV 512MiB、压缩比 64、底层单次读取 <=65,536 bytes、输出 <=64MiB、可用空间至少 1GiB。导入明确具名常量，不写本地回退值；不得整包解压到磁盘或 `.read()` 全文件。读取块限制不等于进程总内存上限，须测量峰值并记录。

| 角色 | 本版职责 | 不允许的影响 |
| --- | --- | --- |
| J-A writer / J-B writer | 不运行、不改动；历史 raw/receipt 冻结 | 不下载、不重生、不移动、不清理旧 root |
| J-A/J-B public strict loader / ZIP validator | 新 consumer 完成授权后只读复用公共 strict loader 和 `validate_zip_archive_package` | 不绕过、不 monkeypatch 生产准入、不 import J-B 私有 reader、不扩展 J-B horizons |
| J-C package admission / bounded reader | 对 J-A 已验证 record 独立执行文件、CHECKSUM、ZIP 成员、路径和流式行准入 | 不回写 J-A/J-B，不用文件名猜测或手工 record |
| 新 J-C producer / writer | 认证输入、一次场景归约、小型原子输出 | 不发信号、不作执行模拟 |
| 新 J-C domain loader | 校验 seal/schema，再从认证输入独立重放比对全字段 | 不把 manifest 正确等同于计算正确 |
| 新 Rule 17 verifier | 独立字面 profile、结构/状态/封闭树检查 | 不 import producer/loader，不宣称验证了 raw 数值 |
| 审计员 / 后续 reviewer | 两类验证、oracle 与负向探针、报告与数据逐项核对 | 不由作者自签 COMPLETE，不晋级 alpha/交易权限 |

未来实施只允许新增以下组件及其对应测试；具体 Plan 以 exact whitelist 收紧，不能加入其它文件：

- `src/research/external_signal_shadow/stage1_5j_c_launch_time_path_feasibility.py`
- `scripts/external_signal_shadow/run_stage1_5j_c_launch_time_path_feasibility.py`
- `scripts/governance/verify_stage1_5j_c_receipt_schema.py`
- `tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5j_c_launch_time_path_feasibility.py`
- `tests/scripts/governance/test_verify_stage1_5j_c_receipt_schema.py`
- §3 指定的唯一冻结研究协议 JSON。

不修改 `AGENTS.md`、rules、roadmap、任何既有 config、exporter、verifier、J-A/J-B core 或历史 evidence。新 domain/core 使用 stdlib；不设通用适配器、注册表、数据库或新增依赖。

## 5. 分母、统计与结论限制

### 5.1 样本守恒与 Parent 口径

`universe_rows` 保留全部 281 键和分类，选入条件固定为 `asset_class=crypto` 且 `listing_regime in {standard,pre_market}` 且 `classification_status=confirmed`。不以收益、锚点成功或路径状态筛选 universe；分类与冻结集合不符即 STOP，不自动改分母。

`child_rows` 为选入 71 键 × 两方向，共 142 行；两方向共享准入/价格引用，不是 142 个独立机会。`parent_rows` 按 `(parent_article_id,listing_regime,direction)` 分组；同 Parent 不因方向、child、极值或成本情景增加独立样本数。

Parent 仅在本组**所有选入 child** 均 `complete` 时为 `complete`，否则为 `gap`，仍保留成员键和缺失数。此口径不是宣称整个公告的非 crypto 标的均完整。完整 Parent 的 terminal/MFE/MAE 各取 child 中位数；不是等权可交易组合的 PnL。触及类型按 child 的计数及 Parent 内比例报告，不能强行给 Parent 编造一条成交路径。

跨 Parent 仍可能同日受共同冲击。记录实际 T0 所在 UTC 日期；一个 Parent 跨日时列全部日期，不把 Parent 拆为多个独立样本。只报告数量与分布，不输出显著性、置信区间、预测准确率或 OOS 通过结论。

### 5.2 固定输出统计

按两个 regime × 两方向的 4 个组，分别输出完整 child 与严格完整 Parent 两个层次的 terminal/MFE/MAE 分布：`n,mean,median,min,max,p10,p25,p75,p90`。空集合 `n=0`，其它全部 `null`；均值为算术平均，偶数中位数取中央两项均值，分位数采用 nearest-rank（排序后第 `ceil(p*n)` 项），不混淆 P50 与偶数中位数。

固定报告完整/缺失分母、三种首次触及计数；Parent 层的触及指标为每 Parent 内比例的等权平均，不命名为策略胜率。三档成本分别报告 `MFE-c` 的 child/Parent 分布与正值数量；所有档位全部展示，不择优。

集中度诊断只做一项：完整 Parent 按 MFE 降序、Parent ID 升序破同值，固定列 top 1/top 3 ID 及其占总 MFE 的比例；总 MFE 为 0 时比例为 `null`。不删样本重选规则，不将“去极值后好看”作为晋级依据。终点负收益尾部、最小 MAE、实际 risk 触发越界幅度均保留，不以 2% 截断。

### 5.3 结论 reducer

逐组逐成本 `space_status` 的固定顺序：有任何选入 child 不完整，或组为空，先判 `evidence_insufficient`；否则若有 child 的未舍入 `MFE > cost`，判 `observed_space`；否则判 `no_observed_space`。严格完整子集的分布仍可描述，但不能覆盖整组缺口。

这些是有限历史集合的诊断标签，不是 L2 的 `alpha_candidate` 或总体显著性。`observed_space` 仅说明存在一段事后可见运动；`no_observed_space` 仅说明本组历史事件在该参考价/窗口/成本假设下没有正空间，不能证伪全部新币策略。均值或中位数不佳不排除未研究的可事前识别子集。

首次触及结果只报告，不再创造“目标先触及比例 > X”之类的晋级/死刑门槛。人类资源决定另写 review：可以停止该固定场景投入，也可申请一项新的信息假设；不得自动缩短观察时间、改分类、删除尾部或加入特征来挽救结果。

| Claim 层 | 本阶段许可 |
| --- | --- |
| `phenomenon_claim` | 只描述已准入路径、覆盖率、空间与触及顺序，限定历史样本和场景 |
| `statistical_edge_claim` / `economic_edge_claim` | 不支持；没有未窥探样本或可执行净收益 |
| `execution_feasibility_claim` / `capital_survival_claim` | 不支持；缺历史盘口、成交/保证金模型与延迟测量 |
| `live_permission_claim` | 永远为 false；研究收据无授权能力 |

## 6. Rule 17：小型收据的精确契约

### 6.1 Profile 与封闭树

新增且唯一 profile：`stage1_5j_c_time_path_v1`，`profile_contract_version=1`，权威为**本 Design 经用户批准的最终 path/SHA**及固定协议对象。最终 Design SHA 不自嵌入本文，批准后由 Plan、profile literal 与运行授权三方绑定；有差异 STOP，不接受“最新文件”。不改变 J-A/J-B 任何 schema/version。

独立 verifier 为 `scripts/governance/verify_stage1_5j_c_receipt_schema.py --artifact-root <root> --profile stage1_5j_c_time_path_v1`。现有 `verify_artifact_schema.py` 被 J-A 绑定，**不得添加 J-C dispatch 或修改字节**；后续审计仍用它检查 J-A profile v2，再分别用 J-B/J-C 独立 verifier 检查对应产物。

正式 J-C root 固定在 `data/external_signal_shadow/stage1_5j_c/launch_time_path_feasibility/<run_id>`；run_id grammar 为 `stage1_5j_c_launch_time_path_feasibility_YYYYMMDDTHHMMSSZ`，日期须真实 UTC。完成度审计前的全链验证另有 §9 的 `validation_only` 授权，其 root 为该授权绑定的临时绝对路径，不能发布到正式 data 目录。两类 root 的 `artifact_kind` 必须明确区分，不能把临时正向测试产物冒充生产收据。

两类 root 都仅有三个普通文件：`manifest.json,summary.json,review_CN.md`，不得有额外目录、symlink、未知文件或 `.sha256` 混入封闭根。

所有 JSON 禁重复键、额外键、NaN/Infinity；int 排除 bool；SHA 为 64 小写 hex；路径为项目相对 POSIX、禁止绝对路径/`..`/symlink；价格字符串是原始有限正数十进制文本。JSON canonical 为 `sort_keys=True,separators=(",",":"),ensure_ascii=False` 加一个 LF；数组按下述键排序。机器指标与比例字符串均采用 §3 的唯一约分有理数格式，禁正号、前导零、负零及可约分形式。

### 6.2 Exact key sets

下面对象逐项列出的 keys 均为 exact set；`null` 只在显式允许处出现，不使用缺键代表未知。

| 对象 | 精确字段与类型 |
| --- | --- |
| `manifest` | `profile_id:str,profile_contract_version:int,artifact_kind:str,run_id:str,files:list[FileSeal]`；files 恰为 review 和 summary，按 path 排序，不自哈希 manifest |
| `FileSeal` | `relative_path:str,size_bytes:int,sha256:str` |
| `summary` | `profile_id:str,profile_contract_version:int,artifact_kind:str,run_id:str,authority:Authority,protocol:object,permissions:Permissions,analysis_state:str,universe_rows:list[Universe],child_rows:list[Child],parent_rows:list[Parent],group_rows:list[Group]` |
| `Authority` | `design:FileSeal,plan:FileSeal,user_receipt_generation_approval:FileSeal,authorization_release:FileSeal,run_authorization:FileSeal,source_files:list[FileSeal],input_files:list[FileSeal]`；seal 路径项目相对；三项授权路径含 `.git/` |
| `Permissions` | `network_allowed,receipt_regeneration_allowed,signal_allowed,consumer_promotion_allowed,alpha_claim_allowed,paper_trading_allowed,live_trading_allowed,execution_allowed`，8 个 bool 全部 false；当前授权的单次 producer 操作不由这些输出字段授予 |
| `Universe` | `parent_article_id:str,symbol:str,asset_class:str,listing_regime:str,classification_status:str,in_scope:bool`；按 parent/symbol 排序，原标签逐字来自 LEDGER |
| `TradeRef` | `utc_date:str,physical_row:int,agg_trade_id:int,time_ms:int,price:str`；row 从 header 后首条数据算 1；输入 file 身份由 parent/symbol/date 关系绑定 |
| `Child` | `parent_article_id:str,symbol:str,listing_regime:str,direction:str,state:str,t0:TradeRef|null,entry:TradeRef|null,endpoint:TradeRef|null,mfe_trade:TradeRef|null,mae_trade:TradeRef|null,terminal_bps:str|null,mfe_bps:str|null,mae_bps:str|null,first_touch:str,touch_trade:TradeRef|null,max_intertrade_gap_ms:int|null` |
| `Parent` | `parent_article_id:str,listing_regime:str,direction:str,state:str,symbols:list[str],utc_dates:list[str],n_complete:int,n_gap:int,terminal_bps:str|null,mfe_bps:str|null,mae_bps:str|null,touch_counts:TouchCounts|null` |
| `TouchCounts` | `target:int,risk:int,neither:int`，非负；总和为本层完整 child 数；Parent gap 时整个对象 null |
| `Distribution` | `n:int,mean:str|null,median:str|null,min:str|null,max:str|null,p10:str|null,p25:str|null,p75:str|null,p90:str|null`；值单位 bps |
| `LevelStats` | `n_total:int,n_complete:int,n_gap:int,terminal:Distribution,mfe:Distribution,mae:Distribution` |
| `CostStats` | `cost_bps:int,space_status:str,child:Distribution,parent:Distribution,child_positive:int,parent_positive:int` |
| `Concentration` | `top1_parent_ids:list[str],top3_parent_ids:list[str],top1_share:str|null,top3_share:str|null`；share 为 0..1 的精确比例 |
| `Group` | `listing_regime:str,direction:str,child:LevelStats,parent:LevelStats,touch_counts:TouchCounts,parent_touch_fraction_mean:object,costs:list[CostStats],concentration:Concentration`；fraction object 恰 `target,risk,neither`，各为精确比例或全 null |

`artifact_kind` 仅 `validation_only/production_diagnostic`，manifest、summary、授权 operation、物理 root 必须一致；domain loader 必须显式接收预期 kind，无默认升级。正式消费路径拒绝 validation_only。`protocol` 精确等于 §3 对象。`direction` 仅 `long/short`；选入行 `listing_regime` 仅 `standard/pre_market`。Universe asset_class 只允许现有账本的 `crypto,equity,etf,commodity,index,unknown`，regime `standard,pre_market,pre_ipo,unknown`，classification `confirmed/unknown`；当前精确字节身份同时约束实际组合。

`analysis_state` 仅 `time_path_described`（全部 142 Child complete）或 `time_path_evidence_gap`（否则）。`Parent.state` 仅 `complete/gap`。`Child.state` 按下列优先级取唯一值：

```text
inherited_j_a_parent_gap
anchor_unavailable
required_package_unavailable
entry_unavailable
endpoint_unavailable
sequence_gap
complete
```

这是 J-C 本地枚举，不改 J-B 原值。前两项无 t0；其余有 t0。required_package_unavailable 的其它 TradeRef 全 null；entry_unavailable 同；endpoint_unavailable 可保留 entry，其余除 t0 外 null；sequence_gap 保留 entry/endpoint，极值/touch/指标/maxgap 全 null。所有非 complete 的 `first_touch=unavailable`，其余指标均 null。complete 所有价格引用和三个 bps、maxgap 非 null；first_touch 仅 target/risk/neither，neither 时 touch_trade null，target/risk 时非 null。触发记录必须在路径内，类型/价格/时间符合 §3，不能与另一方向的触发引用串值。

Parent symbols 与 universe 选入子集完全一致；日期列表来自非空 t0 的 UTC 日期、去重升序。完整 Parent 指标须由成员重算，gap 的指标/touch_counts 全 null。Group 从 child/parent 重算；没有完整 Parent 时 fraction 三项均 null。costs 按 50/80/150 排序；groups/parents/children 分别按各自身份字段字典序排序。`n_total=n_complete+n_gap`，所有集合、计数、null 组合和 projection 都是 verifier 的结构验收项，不只核对总行数。

`source_files` 恰为本表 §2 列出的 8 个 config/source/script 文件，加新 J-C core/CLI/verifier 三个文件，共 11 个；`input_files` 恰包含 JA manifest/summary、JB 三件套、LEDGER、固定协议 JSON、J-B closure JSON 及其 sidecar，共 9 个。每项排序、唯一；JA raw 全成员由其 manifest 和 domain admission 绑定，不在 J-C 复制 280 份原始清单。source/input 自身 SHA 在 domain loader 和审计时重算；独立 verifier 只对冻结字面来源 tuple、合法 keyset 和新源码身份字段语法负责，不把执行者自报 source hash 当作代码审计。

`review_CN.md` 必须为 summary 的确定性渲染。字节模板为下列首段，继而按 group_rows 顺序追加四个组段，最后追加尾段；每行 LF、文件末尾一个 LF、段落之间不另加空行。花括号为字段替换，不输出花括号；整数十进制，无补零。costs 按数组顺序逐行渲染，共三行。独立 verifier 另行实现同模板，不 import renderer。

```text
# Stage 1.5J-C 时间与路径诊断
run_id: {run_id}
profile_id: stage1_5j_c_time_path_v1
artifact_kind: {artifact_kind}
analysis_state: {analysis_state}
universe_children: 281
selected_children: 71
```

每组段：

```text
## {listing_regime} / {direction}
children: {child.n_total}; complete: {child.n_complete}; gap: {child.n_gap}
parents: {parent.n_total}; complete: {parent.n_complete}; gap: {parent.n_gap}
first_touch: target={touch_counts.target}; risk={touch_counts.risk}; neither={touch_counts.neither}
cost_bps={cost_bps}; space_status={space_status}
```

尾段固定一行：`Exploratory price-path diagnosis only; no alpha, execution, paper or live trading authority.`。完整指标保存在 summary；不能自由增加盈利/可执行结论，不能以文字覆盖数据。模板变更须修订 profile 契约。

## 7. Reducer、持久化与异常恢复

流程为 `authorization -> frozen identity -> upstream strict admission -> ledger scope -> package admission -> stream reduce -> child projection -> parent/group projection -> full schema check -> seal/publish`。任何权限/契约错误都在正式输出可见前阻断。schema 合法但有真实业务缺口可以发布 gap 收据，不能伪装无缺口 PASS。

只允许单进程串行运行，不设置服务/调度器。每个 child 保留常量大小的 anchor、entry、endpoint、两方向极值及首次触及累加器；禁止存储全部成交列表。上游 loader 可能额外重演归档，**单 pass 仅描述 J-C 自身每包归约，不承诺全流程只读一次 ZIP**。

输出 run root 必须事先不存在；用固定同级 `.<run_id>.lock` 独占创建锁和 `.<run_id>.staging` staging。拒绝已存在 lock/staging/root，不自动清理。写三文件后分别 fsync，再 fsync staging directory，原子 rename 为正式 root，再 fsync parent directory，全部成功才 RC=0。发布前重算输入身份，发现漂移则 STOP。普通退出移除自身 lock 并 fsync parent；失败/中断的残留由独立授权清理，不自动重试覆盖。

file fsync、staging fsync、rename 失败均不能产生成功状态；rename 后 parent fsync 失败必须非零，已可见 root 标记为待人工只读审计，不能自行当作成功或删除。原子 rename 仅在独占单 writer 模型下使用，外部并发写入属 STOP；不得用 replace 覆盖已有正式根。

core 仅可在 parent-directory fsync 成功后返回 `PublishResult`；CLI 仅在取得该返回值后，才在 §9 的同一 RUN_ID evidence 目录写入 `producer_lifecycle_evidence.json` 与同名 sidecar。该 JSON canonical key set 为 `evidence_schema_version:int,run_id:str,artifact_kind:str,operation:str,design:FileSeal,plan:FileSeal,user_receipt_generation_approval:FileSeal,authorization_release:FileSeal,run_authorization:FileSeal,final_root:str,manifest_sha256:str,summary_sha256:str,review_sha256:str,publish_terminal:str,producer_returned_success:bool`；其中 version 只能 1，`publish_terminal` 只能 `parent_directory_fsynced`，最后一项只能 true，三件套 SHA 必须重算匹配。core 异常或 CLI 非零时不得产生该 evidence；其写入/sidecar 失败也使 CLI 非零。这个文件不在封闭 receipt root 中，不是 domain loader 的替代输入。

重复相同 RUN_ID：不重生、不覆盖，返回 `STOP=stage1_5j_c_output_exists`。崩溃恢复只允许新授权/新 RUN_ID 或独立只读验证已有根；不能续写一个半成品。同一 Plan 的每次授权/审计按 RUN_ID 分目录保留，见 §9，不覆盖旧授权来重跑。当前历史 JB 三个旧 run（20261013T000000Z、20261013T040000Z、20261014T033000Z）全部不准入，永久保留原样，不把清理混入研究。

CLI 契约/数据错误 RC=1，参数用法错误 RC=2；审计记录 actual process RC，不用终端字符串替代。若上游错误，保留原 STOP 原因并附 J-C stage，不吞异常。

## 8. 不变量与机械验证

| ID | 必须成立的不变量 | 机械证明 / 失败出口 |
| --- | --- | --- |
| INV-01 | exact upstream/root/source/protocol identity，无 rebaseline | 任意 path/hash/profile/import-origin 变异均 `STOP=stage1_5j_c_authority_mismatch` |
| INV-02 | 生产消费需要用户提供的单次批准及其派生授权；输出不授权下游 | 缺失/错误用户 approval、错 RUN_ID、错 core SHA、权限 true 或派生字段不一致，均在任何上游 loader 前拒绝 |
| INV-03 | 281 universe、71×2 child，联合键无串值 | 重复键、AIA 跨 Parent 借值、删 gap、额外 symbol 负向测试 |
| INV-04 | persisted package 先准入，再读 ZIP | 无记录裸 ZIP、跨 Parent/date、CHECKSUM/manifest 改写、symlink/逃逸全部拒绝 |
| INV-05 | 边界与同毫秒顺序精确，无未来成交 | 63s/64s/899s/900s 边界及一毫秒外、重复时间不同 ID、跨 UTC 日期、无成交测试 |
| INV-06 | first passage 不由极值倒推、不假定线价成交 | 相同 min/max 但相反先后顺序、跳过风险线、neither、阈值等号及舍入伪触及测试 |
| INV-07 | 缺失保持 null，不产生 false zero/no-space | 各 gap state 条件、整体优先 insufficient、空组、Parent 混合完整性测试 |
| INV-08 | 只有固定单场景、无方向/成本择优 | AST/接口检查无参数搜索/网络入口；全部 4 组×3 成本存在；参数变异拒绝 |
| INV-09 | 流式资源限制可测，不靠注释 | 实际底层 readinto 观测、ZIP/CSV/ratio/root/free-space 边界、超长行拒绝；记录峰值 RSS |
| INV-10 | raw -> child -> parent/group -> prose 全链对账 | 固定 gap oracle + 确定性选择的完整真实路径 oracle + 独立 verifier；伪造合法 extrema/计数也须被 domain replay 拒绝 |
| INV-11 | crash 不假成功、不覆盖历史 | 四 fsync/rename fault injections、重复 RUN_ID、stale lock/staging、final root collision；可信闭环须同时满足 §9 的 process RC、lifecycle evidence、replay、verifier 和 oracle 联合门禁 |
| INV-12 | no-touch、无权限扩张 | 基线 tracked/staged/untracked union、HEAD、白名单、输入前后 SHA；L0 bool identity 断言 |

Fixture 分级：

1. **Canonical positive**：真实冻结 JA/JB root 经公共 strict loader 准入，固定 LEDGER 与全部选入分母，同一 CLI 在 §9 定义的 `validation_only` 单次授权下向绑定的临时输出根走完整链。测试 fixture 的用户原文/release 只能证明 grammar、字段绑定和拒绝行为；它不是生产用户批准或 custodian 放行的替代物。实际运行前必须存在用户逐字提供的批准原文及非 executor 写入的 release。不得伪造包记录、哈希、闭环凭据或替换 loader 得到 GREEN。
2. **Independent oracle**：固定 `PRLUSDT`、Parent `0116dd83010043bd95c37626e2277bbe` 是**固定 gap oracle**：独立流式解析并按本协议逐字段对比；该实现不调用生产 parser/reducer/统计 helpers。AST dependency scan 与 production semantic helper raising-sentinel 同时证明独立性。若 PRL 不满足 entry/endpoint 条件，必须报告同一 gap，绝不替换成一个能 PASS 的样本。

   同时必须有一个**确定性正向语义 oracle**。在 J-C 自己完成 package admission 后，按 `(parent_article_id,symbol)` 字典序扫描认证 raw 输入，选取第一个独立计算为 `complete` 的 child；选择发生在任何 return、direction、first-touch、MFE/MAE 或输出值比较之前，不得按结果挑样本。对该 key 以独立标准库流式 parser/reducer 重算 entry、endpoint、long/short 两方向 MFE/MAE、terminal、first touch 及 child 到 Parent/Group projection，并与 receipt 逐字段比较。若不存在任何 complete child，则固定输出 `positive_semantic_evidence_unavailable`；不得给出 `receipt_closure_audited`，只能报告 `receipt_closure_incomplete` 或相应 evidence gap。
3. **Pure internal synthetic**：只在纯函数内构造价格路径，验证首次触及/舍入/跨日/稀疏边界，不声称是上游正向收据。模块边界正向验证不能用它替代 canonical。
4. **Negative mutations**：在 `/tmp` 物理隔离 copy 内逐项变异，禁止 hardlink/symlink/bind-mount 写穿。每一例必须断言预期 owner、精确 STOP/失败类别和 actual process RC，不能仅断言非零：

   | 变异边界 | 唯一必须拒绝的 owner | 不可替代的证明 |
   | --- | --- | --- |
   | J-A/J-B root、package record、ZIP 路径/identity、CHECKSUM、manifest/source SHA 或 raw ZIP 字节 | 上游公共 strict loader，或 J-C domain loader 的 package admission/replay | Rule 17 即使结构通过也不构成通过；记录 upstream/J-C STOP |
   | J-C root keyset、enum、sealed file、manifest hash、profile、权限或闭合目录 | 独立 J-C Rule 17 verifier | verifier 必须以自己的 schema/renderer 拒绝，不 import producer/loader |
   | receipt 内部仍自洽、但 raw path、极值、first-touch、child/Parent/Group projection 被伪造 | J-C domain replay | Rule 17 可通过；domain replay 必须以 raw 重算拒绝 |
   | 用户批准原文/release 缺失、release 与原文/派生授权 tuple 不同、原文或 sidecar 非法 | CLI authorization preflight | 在任一 upstream loader 调用前停止；本地原文、sidecar、派生 JSON 全部自洽但 release 缺失的 probe 仍须 STOP，测试以 loader sentinel 证明未读输入 |
   | parent-directory fsync fault after rename | producer/CLI lifecycle contract，随后 closure predicate | CLI 非零且不得有 lifecycle evidence；可见 root 不能取得 closure verdict |

必须实际运行 anti-shortcut scanner 并记录 source SHA/RC，非零不得写 clean；warning 每项处置落盘。Ruff 仅检查新白名单组件，不隐瞒仓库其它历史问题；既有 J-A/J-B 回归证明 no-touch，Git staged 内容不得被隐式加入。上述均是未来 Plan 的验收要求，本次文档工作未执行。

## 9. 权限、审计与升级路由

用户批准原文是运行授权的根，不是 `run_authorization.json`。本 Design 将**用户或其明确指定的 Authorization Custodian**列为唯一的人工 TCB owner：Custodian 在 executor 之外取得用户的真实批准消息，逐字核对后才 materialize approval/release。CLI、producer、测试工具和审计器均不是 Custodian，均不得创建、改写、删除或自行放行这两份授权凭据。

每次运行先在 `.git/plan-execution/stage1_5j_c/<approved_implementation_plan_sha256>/<run_id>/user_receipt_generation_approval.txt` 保存用户**逐字提供**的单次批准文本，并以唯一同名 `.txt.sha256` sidecar 固定；sidecar 精确为 `<64 lowercase hex><two ASCII spaces>user_receipt_generation_approval.txt<LF>`。其 ASCII、LF 结尾、无空白/空行、无重复 key、固定顺序的 11 行 grammar 为：

```text
APPROVED_J_C_PLAN_RELATIVE_PATH=<approved plan relative path>
APPROVED_J_C_PLAN_SHA256=<64 lowercase hex>
AUTHORIZED_SOURCE_BUNDLE_SHA256=<64 lowercase hex>
AUTHORIZED_OPERATION=<operation>
AUTHORIZED_RUN_ID=<run_id>
AUTHORIZED_OUTPUT_ROOT=<exact output root>
NETWORK_ALLOWED=false
SIGNAL_ALLOWED=false
PAPER_TRADING_ALLOWED=false
LIVE_TRADING_ALLOWED=false
EXECUTION_ALLOWED=false
```

`AUTHORIZED_SOURCE_BUNDLE_SHA256` 是 `source_files` 的身份封条：对 §6 要求的恰好 11 个、按 `relative_path` 升序的 `FileSeal` 对象数组，以本 Design 的 canonical JSON 规则序列化并 SHA-256；不含用户批准、派生授权或任何 input file。CLI 必须从物理源码重算每个 seal 和 bundle，再与用户原文及派生授权比对；少一个、多一个、顺序不同或任一 SHA 不同均 fail-closed。

批准原文旁必须存在 Custodian 独立写入的 `authorization_release.json` 及唯一同名 `.json.sha256` sidecar，sidecar 精确为 `<64 lowercase hex><two ASCII spaces>authorization_release.json<LF>`。release 是 canonical JSON，exact key set 为 `release_schema_version:int,release_state:str,user_receipt_generation_approval:FileSeal,design:FileSeal,plan:FileSeal,authorized_source_bundle_sha256:str,operation:str,run_id:str,output_root:str,network_allowed:bool,signal_allowed:bool,paper_trading_allowed:bool,live_trading_allowed:bool,execution_allowed:bool`；version 只能 `1`，`release_state` 只能 `user_message_verified_and_released`，五项权限均为 false。其每项 seal、bundle、tuple 和权限必须与用户原文及物理 Design/Plan/source bytes 完全一致。Custodian 只可在直接核对用户消息原文后写入该 release；它不运行 J-C CLI、不读取 J-A/J-B 输入、不生成或修改 `run_authorization.json` 或 receipt。

这是一项显式、有限的人工作业 TCB，而非对聊天身份的伪造密码学证明：可信来源是用户消息原文加上 Custodian 的人工 release，不是 executor 生成的任一 filesystem 字节。CLI 只允许 `lstat`/只读打开既存 approval/release 并拒绝 symlink；producer/CLI 不得含有创建、覆盖、rename、unlink 或修复 approval/release 的代码路径。Plan 必须以静态 no-writer scan 与运行时 write-sentinel 同时证明这个职责边界，并以“本地原文、sidecar、派生 JSON 全部自洽但 release 缺失”负向 fixture 证明 preflight 在 loader 前停止。若没有由 Custodian 独立 materialize 的 release，则 STOP=`stage1_5j_c_independent_approval_release_unavailable`，不得以本地自洽文本替代。独立 closure audit 仍必须取得用户消息原文，逐字比较 approval text，并复核 release 的 custodian boundary。

`authorization_release.json` 不在 sealed receipt root，也不是 Rule 17 receipt profile 的成员；它是 Custodian -> CLI 的外部 authority contract。CLI parser 与独立 closure auditor 的 release parser 必须分别以本段 literal key set 实现，auditor 不得 import CLI/producer parser。审计记录必须保存两者各自的 source SHA、actual parse RC 和 user-message comparison 结论。

仅在 Task 0 已验证用户原文、两个 sidecar、Custodian release、approved Plan 实际 SHA、物理 source bundle 和上述 tuple 后，才可由 CLI 派生独立 `run_authorization.json`，固定置于同目录。每个 RUN_ID 只准生成一个新 root；旧授权、sidecar 和审计目录不可覆盖。CLI preflight 的顺序固定为：approval/release 文件、sidecar 与 custodian-release boundary -> grammar/release tuple -> Plan/Design/source/input identity -> 派生授权 -> 上游 strict loaders。任一前项失败必须在调用任何 upstream loader 前停止。

派生授权 exact keys：`design:FileSeal,plan:FileSeal,user_receipt_generation_approval:FileSeal,authorization_release:FileSeal,authorized_source_bundle_sha256:str,run_id:str,output_root:str,source_files:list[FileSeal],input_files:list[FileSeal],operation:str,network_allowed:bool,signal_allowed:bool,paper_trading_allowed:bool,live_trading_allowed:bool,execution_allowed:bool`。`user_receipt_generation_approval` 与 `authorization_release` 必须精确 seal 上述物理文件；`authorized_source_bundle_sha256` 必须与其 11 个 `source_files` 的重算结果、用户原文及 release 一致；五项权限 false；source/input 列表与 §6 一致，授权不把自身放进 source/input，避免哈希循环。文件 canonical JSON + 唯一同名 `.json.sha256` sidecar，sidecar 精确为 `<64 lowercase hex><two ASCII spaces>run_authorization.json<LF>`；无自动改写。Plan SHA 来自批准的物理字节，不要求尚不存在的源码在本 Design 中预填 hash。

两种 operation 的条件契约：

| operation | source 身份与前置授权 | output_root 与 artifact_kind |
| --- | --- | --- |
| `offline_time_path_validation_once` | Custodian 已核对用户原文并写入 release；固定 11 行 grammar 单独绑定测试范围、待审源码 bundle、RUN_ID 与精确临时根；允许先完成 canonical integration 再做完成度审计，绝不豁免上游准入 | output_root 是本机临时目录下一个不存在的绝对路径；逐祖先无 symlink、不得落在仓库或正式 data 根内；`artifact_kind=validation_only` |
| `offline_time_path_diagnostic_once` | 已完成实现审计后，Custodian 核对用户原文并另行 release 正式单次生产消费，绑定审计过的源码 bundle、RUN_ID 与正式 root | output_root 是 §6 的项目相对正式路径；`artifact_kind=production_diagnostic` |

output_root 是唯一定义允许临时绝对路径的字段，不放宽 FileSeal 的相对路径约束。CLI 不提供参数或环境变量覆盖此根，也不提供跳过准入开关。待审源码发生改变须新验证授权/新 RUN_ID，旧验证结果不能绑定新字节。两种授权都覆盖同一 root 发布后的只读 domain replay/审计，但不允许再次生产；另一个 root 的消费仍需新授权。纯内部 synthetic 测试不消费生产 raw，不需要这种运行授权。

独立审计报告输出到上述 RUN_ID 子树的 `evidence/receipt_closure_audit_report.md` 及唯一同名 `.md.sha256`，不能落到 J-A/J-B governance 树。报告至少绑定 user approval 原文/sidecar、Custodian release/sidecar 和 custodian-release boundary 检查、approved Design/Plan、协议、source/verifier SHA、profile id/version、artifact_kind、RUN_ID、三件套 SHA、每项命令 actual RC、oracle/负向探针和 scope/index/no-touch 结果。

只有以下**联合谓词**全部成立，独立审计员才可写 `receipt_closure_audited`：生产 CLI actual process `RC=0`；用户消息、approval text、Custodian release 三者逐字/逐字段匹配，且 custodian-release boundary 有效；有效 `producer_lifecycle_evidence.json` 与 sidecar 存在且其 `publish_terminal=parent_directory_fsynced`、`producer_returned_success=true`、RUN_ID/root/三件套 SHA 与物理字节一致；J-C domain replay `RC=0`；J-C Rule 17 verifier `RC=0`；固定 PRL gap oracle 按真实状态通过；确定性正向 semantic oracle 为 `passed`；全部要求的负向探针、scope/index/no-touch 检查通过。任一条件缺失、非零或 `positive_semantic_evidence_unavailable`，结论只能是 `receipt_closure_incomplete`，即使 rename 后 root 看起来合法也不得例外。专门的 parent-directory fsync 注入测试必须证明：root 可见但 producer 非零且 lifecycle evidence 缺失时，此谓词为 false。

validation_only 通过不等于正式收据生成完成，作者/producer 不自签该状态。Rule 17 独立验真、domain replay 与 oracle 分别证明结构、raw 语义和独立计算，任何一条都不替代其余两条。

既有上游 verifier 使用冻结代码；新 J-C verifier standalone 避免修改被绑定的通用 verifier。审计不得把“J-C 结构通过”写成“JA/JB/J-C 原始事实全部重证”。严格区分结构完整性、raw 语义重放与独立计算 oracle 三条证明链。

Rule 12：实现缺陷仅在白名单内修；需动上游/config/verifier/ledger 即 `BLOCKED_SCOPE_DRIFT`；本 Design 与冻结 source 契约矛盾即 `BLOCKED_SPEC_DRIFT` 并提交 invariant/source/contradiction packet。不得以补丁、mock、兼容 fallback 或非正式数据替代继续。

## 10. 交付、成本与未决项

本 Design 批准后的最小交付为：一个固定协议、一个含独立 package admission 的流式诊断实现及测试、一个独立 profile verifier、Custodian release 到派生授权的 preflight、发布 lifecycle evidence、一次另行获准的研究收据与独立审计。没有运行采集器、网络 API、VPS 部署、订单、仓位或交易阈值改变；**rollout/rollback=N/A**，因为没有生产交易运行变更，失败只保留隔离研究输出。

预审的 8~12 人时是估计，不是交付承诺。Plan 必须重新估算完整成本，包含上游重复准入、独立 oracle、profile 测试、审计和重跑；若不再满足低成本假设，先向用户报告缺口和新增预算，不自动扩大工程。资源停止与策略证伪保持分离。

| 事项 | 是否阻断本 Design 路径 | Owner / 处理 |
| --- | --- | --- |
| 2%/30%、1s freshness、60s+3s 是假设而非实测 | 无实现歧义，但必须由用户随 Design 明确批准 | 用户/独立 Design reviewer；不同场景先改 Design，不能留给 executor 挑选 |
| raw 内是否存在完整新窗口、真实运行时间与峰值内存 | 不阻断设计；不能在本次静态读取中假称已知 | 未来获准实验/测试；不足如实 gap 或资源 STOP，不换样本 |
| 实际成交、盘口、延迟、funding/容量/保证金 | 不在本版范围 | 将来独立研究；本版权限和 claim 始终不升级 |
| 固定协议的边界 | 不阻断：其仅为只读、不可覆盖的收据测量输入，不是配置模块或执行阈值 | Plan 必须证明没有 CLI/env/config override，且不能被交易路径 import；若未来需要可调或执行性含义，先另起治理 Design |
| 下一阶段假设、真实样本外、B/A 路线 | 不阻断 | 本版不命名/不授权下一阶段；按结果重新决定是否投入 |

**下一步仅为独立 Design Review 和用户批准。未批准前不写 Implementation Plan，不实施、不运行历史路径实验、不生成 receipt，也不 commit/push/deploy/SSH。**
