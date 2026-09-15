# Stage 1.6F GAP-02 历史数据能力物理盘点与证据包审计报告 (全量控制组与截断W2实证闭环版)

- **日期**: 2026-09-14
- **审计阶段**: Stage 1.6F (Historical Matched Control Mechanism Diagnostic)
- **对应 Design**: `docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md` (维持 `draft_for_review`，不擅自修改)
- **前置依赖完成根 (GAP-01 Completed Root)**: `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z`
- **物理证据包路径**: `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/`
- **官方原始依据存档**: `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/official_sources/`
- **综合审计裁决**:
  - `evidence_package_integrity`: **PASS** (148/148 ZIP/CSV 文件完整匹配，逐字节与 SHA 校验 0 错误)
  - `anchor_event_source_capability`: **PASS** (REEFUSDT 锚点事件 16 天全部 8 项数据族物理落盘并复验)
  - `control_group_full_universe_enumeration`: **PROVEN_WITH_PER_CANDIDATE_PROVENANCE** (S3 878 个全量 USDT 永续前缀原始 XML 字节固化；包含 5 个非 ASCII Unicode 标的在内全量纳入 2025-01-15 归档探测，确证 380 个活跃在市，498 个未上线或下架；15 项排除链逐项依据与出处固化；365 个候选全量完成 168h 波动率与成交额比率计算并落盘为逐候选 provenance 清单)
  - `control_group_positive_fixture`: **PROVEN_MATCHED_CONTROLS** (严格按 Design Section 6 规则遴选出 Top 3 控制组：`AXLUSDT`, `AKTUSDT`, `REZUSDT`，连续 16 天 1h K 线已全部落盘验证)
  - `sample_rejected_candidates_verified`: **VERIFIED_REJECTED** (`IOSTUSDT` 与 `ONEUSDT` 确证因成交额比率分别为 8.9317 与 2.7312 超出 2.0 上限被否决，代码为 `QUOTE_VOL_RATIO_OUT_OF_BOUNDS`)
  - `full_denominator_archive_coverage`: **ARCHIVE_AVAILABILITY_PROVEN** (1,385 个相交归档探针就绪；合规 42 合约可用率 1,187/1,197，证明归档物理存在)
  - `w2_settlement_window_coverage`: **TRUNCATED_OR_FULL_W2_ARCHIVE_PROVEN** (矩阵内全部 1,197 条在范围记录与 188 条超范围记录均已补入 `nominal_window_start_utc`, `actual_paired_window_start_utc`, `truncation_reason`, `is_truncated_by_tpub`；AIAUSDT 与 PORT3USDT 严格标明为截断 W2 覆盖，实际时长分别为 31.22m 与 32.43m，杜绝完整 24h 误称)
  - `denominator_historical_range_boundary`: **ISOLATED_PARTITION** (严格隔离：42 个在 B export 范围内，6 个超范围合约独立单列待仲裁)
  - `per_event_settlement_rule_mapping`: **PROVEN_OFFLINE_AUTHORITY** (已将官方公告原始 HTML 字节与 SHA-256 紧密绑定入映射契约)
  - `data_semantics_contract`: **PROVEN_OFFLINE_AUTHORITY_WITH_DOWNGRADE** (结算与资金费绑定官方 HTML；Mark FAQ 已绑定；BookDepth 明确降级为观察到的样本结构而非官方公式)
  - **核心门禁状态**: **`GAP-02 = READY_TO_CLOSE`**
  - **设计状态**: **`design_status = DRAFT_PENDING_CLOSURE_CONFIRMATION`**
  - **准入权限**: **`implementation_plan_allowed = false` (等待用户 / Auditor 正式确认)**

---

## 1. 证据工件与封签总清单 (Evidence Artifacts & Checksums)

所有产物均物化于 `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/`：

| 证据工件文件名 | 物理相对路径 | 最新 SHA-256 | 解决的审计阻断项 | 核心改进与指标 |
|:---|:---|:---:|:---:|:---|
| **全量底层标的普查与排除快照** | `historical_universe_snapshot_20250115.json` | `63449f932636893a0b24466d04e79b2456553ad8d9502f677f8d6b66d197d5e8` | P0-1 (全量 878 Universe) | 固化 S3 878 全量 USDT 前缀（含 5 个 Unicode 标的）、380 活跃探针、498 非活跃探针、15 排除链出处、365 候选名单 |
| **365 候选逐项基线 Provenance** | `historical_control_candidates_baseline_provenance_reef_20250115.json` | `e34da67918daa8be84a7dbc647918decc40bdd6a9fd4bf8a521ae9ce1f2b68ad` | P0-2 (打分可复验性) | 记录 365 候选全部 8 天归档 URL、SHA、字节数、168 bar 计数、vol、med_qvol、比率、合格/拒绝、距离与排名 |
| **控制组合格/否决汇总名单** | `historical_control_universe_reef_20250115.json` | `b3042945036fe4825b7fc1e40150be438805a706b8dd1e5b80ac849a3808cdb0` | P0 控制组聚合 | 120 个合格控制组全量排序、245 个否决候选明细、Top 3 控制组、硬哈希绑定上述两项工件 |
| **证据清单 Manifest** | `gap02_evidence_manifest.json` | `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f` | 证据完整性 | 148 个物理 ZIP/CSV 工件全覆盖，辅件 SHA-256 完整注册，0 校验错误 |
| **逐归档全相交矩阵** | `denominator_archive_coverage_matrix_all_intersecting.json` | `b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8` | P1 (W2 字段补齐) | 1,385 归档探针；42 合约 1,187/1,197 可用；逐条补入 nominal 与 paired window 字段及截断原因 |
| **逐事件结算映射** | `settlement_rule_mapping_37contracts.json` | `40b338651644d9d141f075f1dc78b8f219b435d52a8e9246eebbe33b3b4b7601` | P1-1 (结算映射) | 37 个交割合约硬绑定本地官方公告 HTML 与 SHA-256 |
| **数据语义规范契约** | `data_semantics_contract.json` | `5a096c50b194521ccc1402884ee15364783b1201a2c5fb0d289d64548cd38fd2` | P1-2 (语义契约) | 绑定结算公告、资金费 FAQ、标记价格 FAQ；BookDepth 降级为观察结构 |
| **S3 永续前缀原始 XML** | `official_sources/s3_binance_vision_futures_um_klines_symbols_list.xml` | `885835e03ebeb93d92b957804fafe55565606ddc9492930519aed91941e03072` | 权威 bytes | 官方 Data Vision S3 两页包含的全部 1,032 唯一前缀，其中以 USDT 结尾的全部 878 个前缀无过滤留存 (91,956 字节) |
| **官方结算规则 HTML** | `official_sources/binance_announcement_settlement_4bcabddf0e81423ebca242e185bf157d.html` | `2ba30d566e99928c4df332dbda6a62aaf1a4e9d39a0048f3c40d0266e5b6dd36` | 权威 bytes | 官方 2024-11-04 公告：交割结算价由 1h 调整为 30m 均值 |
| **官方资金费规则 HTML** | `official_sources/binance_faq_funding_rate_360033525031.html` | `9266dac6d2dd6c3bd873a0fd4da7bc0780026fe79dcfb241c2e0f0db9cd953ca` | 权威 bytes | 资金费率公式、8h/4h 周期、结算前 1 分钟延迟与 Premium Index 预估说明 |
| **官方标记价格 HTML** | `official_sources/binance_faq_mark_price_360033525011.html` | `3604bf98774f37a7b67078c7c8b28454ad5e9bc1f9f3b1eac9f71d24c139a64a` | 权威 bytes | 支持中心标记价格与指数价格原则说明快照 |

---

## 2. P0 阻断项解决实证：全量 878 Universe 普查与 365 候选逐项 Provenance

### 2.1 2025-01-15 当期 878 全量 Universe 普查与排除链固化 (`historical_universe_snapshot_20250115.json`)
- **底层资产池普查**:
  - 权威源：`official_sources/s3_binance_vision_futures_um_klines_symbols_list.xml`，严禁使用 ASCII 正则过滤，完整解析出全部 **878 个以 USDT 结尾的永续合约前缀**。
  - **包含的 5 个非 ASCII Unicode 标的独立探测结果**:
    1. `哈基米USDT`: HEAD 探测 URL `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data/futures/um/daily/klines/%E5%93%88%E5%9F%BA%E7%B1%B3USDT/1h/%E5%93%88%E5%9F%BA%E7%B1%B3USDT-1h-2025-01-15.zip` $ightarrow$ **HTTP 404**
    2. `币安人生USDT`: HEAD 探测 URL `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data/futures/um/daily/klines/%E5%B8%81%E5%AE%89%E4%BA%BA%E7%94%9FUSDT/1h/%E5%B8%81%E5%AE%89%E4%BA%BA%E7%94%9FUSDT-1h-2025-01-15.zip` $ightarrow$ **HTTP 404**
    3. `我踏马来了USDT`: HEAD 探测 URL `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data/futures/um/daily/klines/%E6%88%91%E8%B8%8F%E9%A9%AC%E6%9D%A5%E4%BA%86USDT/1h/%E6%88%91%E8%B8%8F%E9%A9%AC%E6%9D%A5%E4%BA%86USDT-1h-2025-01-15.zip` $ightarrow$ **HTTP 404**
    4. `牛来USDT`: HEAD 探测 URL `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data/futures/um/daily/klines/%E7%89%9B%E6%9D%A5USDT/1h/%E7%89%9B%E6%9D%A5USDT-1h-2025-01-15.zip` $ightarrow$ **HTTP 404**
    5. `龙虾USDT`: HEAD 探测 URL `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data/futures/um/daily/klines/%E9%BE%99%E8%99%BEUSDT/1h/%E9%BE%99%E8%99%BEUSDT-1h-2025-01-15.zip` $ightarrow$ **HTTP 404**
  - 全量 878 标的在 `2025-01-15` 的探测结果完全守恒：
    - **380 个** 合约返回 HTTP 200，证明当日在市活跃；
    - **498 个** 合约返回 HTTP 404（含上述 5 个 Unicode 标的），属于当日尚未上线或已下架标的。
    - 守恒关系：$878 = 380 + 498$。
- **排除链执行 (Exclusions Chain，共 15 个，逐项记录出处与原因)**:
  1. **同 Underlying 排除 (1个)**: `REEFUSDT`（锚点事件标的自身，依据 Design Section 6 Item 1）。
  2. **生命周期不足 7 天排除 (2个)**: `DUSDT`、`PROMUSDT`（在 `2025-01-08` 探针返回 404，上市时间不足 7 天，依据 Design Section 6 Item 2）。
  3. **前期下架公告排除 (12个)**: 在 C 根中于 `2025-01-15 08:00:06 UTC` 前已发布下架公告且在 380 列表中仍有归档的合约：`BONDUSDT`, `CTKUSDT`, `CVXUSDT`, `LOOMUSDT`, `MAVIAUSDT`, `MDTUSDT`, `OMGUSDT`, `ORBSUSDT`, `RADUSDT`, `SLPUSDT`, `STPTUSDT`, `XEMUSDT`（逐条绑定 C 根公告 Article ID、发布时间戳与交割时间戳）。
- **合格候选标的池**: $380 - 15 = \mathbf{365}$ **个合约**。

### 2.2 365 个候选标的逐项基线 Provenance 与比率打分 (`historical_control_candidates_baseline_provenance_reef_20250115.json`)
严格按照 Design Section 6 第 2~4 条规则，对全部 365 个候选逐一拉取 `2025-01-08` 至 `2025-01-15` 共 8 天归档（共 $365 	imes 8 = 2,920$ 个日归档文件）：
- **基线时间区间**: $[E - 168	ext{h}, E) = [	ext{2025-01-08 08:00:00 UTC}, 	ext{2025-01-15 08:00:00 UTC})$。
- **锚点标的 REEF 基线**:
  - 168 根 1h K 线对数收益率总体标准差：`vol = 0.010977`
  - 168 根 1h K 线中位小时 Quote Volume：`med_qvol = 243,443.61` USDT
- **全量 365 个候选评价结果**:
  - **合格控制组合约数 (两个比率均在 [0.5, 2.0] 内)**: **120 个**
  - **被否决合约数**: **245 个**，拒绝原因分类完全透明且可复查：
    - `QUOTE_VOL_RATIO_OUT_OF_BOUNDS`: **207 个**（成交额比率超出 [0.5, 2.0] 边界）
    - `BOTH_RATIOS_OUT_OF_BOUNDS`: **16 个**（波动率与成交额比率均超出边界）
    - `ZERO_VOLATILITY_OR_ZERO_MEDIAN_QUOTE_VOLUME`: **19 个**（因流动性停滞导致波动率为 0 或中位成交额为 0，依 Design Section 6 Item 2 fail-closed 否决）
    - `INCOMPLETE_BASELINE_BARS`: **1 个**（区间内有效 K 线不足 168 根）
    - `VOLATILITY_RATIO_OUT_OF_BOUNDS`: **2 个**（仅波动率比率超出边界）
  - **被审计样本确证**:
    - `IOSTUSDT`: decision=`rejected`, `quote_volume_ratio` = 8.9317, rejection_code=`QUOTE_VOL_RATIO_OUT_OF_BOUNDS`
    - `ONEUSDT`: decision=`rejected`, `quote_volume_ratio` = 2.7312, rejection_code=`QUOTE_VOL_RATIO_OUT_OF_BOUNDS`
- **依据匹配距离优选 Top 3 控制组**:
  $$	ext{dist} = |\ln(	ext{vol\_ratio})| + |\ln(	ext{qvol\_ratio})|$$

| 排名 | 优选控制组合约 | 匹配距离 (Distance) | 波动率比率 (Vol Ratio) | 成交额比率 (Quote Vol Ratio) | 判定结果 |
|:---:|:---|:---:|:---:|:---:|:---:|
| **1** | **`AXLUSDT`** | **`0.0096`** | **`1.0092`** | **`1.0005`** | **合格 (Top 1)** |
| **2** | **`AKTUSDT`** | **`0.0377`** | **`0.9684`** | **`0.9945`** | **合格 (Top 2)** |
| **3** | **`REZUSDT`** | **`0.0710`** | **`1.0424`** | **`0.9710`** | **合格 (Top 3)** |

### 2.3 控制组 16 天全区间行情物理落盘
已为 Top 3 控制组（`AXLUSDT`, `AKTUSDT`, `REZUSDT`）下载连续 16 天（2025-01-08 至 2025-01-23）的 1h K 线归档（共 48 个 ZIP 及解压 CSV，全部校验通过），完整注入 `matched_controls/` 并写入 Manifest，与 REEF 形成同频对照。

---

## 3. P1 阻断项解决实证：W2 逐条记录字段补齐与截断窗口规范

### 3.1 矩阵内逐条记录字段全面对齐 (`denominator_archive_coverage_matrix_all_intersecting.json`)
针对审计提出的 W2 记录字段不完整问题，已对全部 1,197 条在范围记录（含 476 条 W2 记录）与 188 条超范围记录（含 78 条 W2 记录）进行统一补齐，每一条记录均显式包含以下四个字段：
- `nominal_window_start_utc`: 名义观察窗口起点。对于 W2，为名义 24h 起点 $T_{	ext{settle}} - 24	ext{h}$；对于未排期交割为 `null`。
- `actual_paired_window_start_utc`: 实际配对观察窗口起点。对于受 $T_{	ext{pub}}$ 截断的合约，为 $\max(T_{	ext{pub}}, T_{	ext{settle}} - 24	ext{h})$；对于无截断合约，与名义起点一致。
- `truncation_reason`: 截断原因说明。当被 $T_{	ext{pub}}$ 截断时，显式记录 `"T_pub occurs after (T_settle - 24h); window truncated to [T_pub, T_settle) per Design Section 5.2"`；未截断时为 `null`；无交割排期时记录 `"NO_SCHEDULED_SETTLEMENT_TIME"`。
- `is_truncated_by_tpub`: 布尔标志位，显式标明是否发生公告时间截断。
- `coverage_scope_type`: 覆盖类型，显式区分为 `FULL_24H_W2_ARCHIVE_COVERAGE`、`TRUNCATED_W2_ARCHIVE_COVERAGE` 或 `NO_SETTLEMENT_WINDOW`。

### 3.2 截断事件个案核实
在 42 个合规在范围合约中，严格核实仅有 2 个合约存在截断：
1. **`AIAUSDT`**:
   - $T_{	ext{pub}}$: `2025-12-11 11:43:46.582 UTC`
   - $T_{	ext{settle}}$: `2025-12-11 12:15:00 UTC`
   - 名义 W2: `[2025-12-10 12:15:00 UTC, 2025-12-11 12:15:00 UTC)` (24h)
   - 实际配对区间: `[2025-12-11 11:43:46.582 UTC, 2025-12-11 12:15:00 UTC)`
   - 实际配对时长: **31.22 分钟**
   - 覆盖分类: `TRUNCATED_W2_ARCHIVE_COVERAGE`
2. **`PORT3USDT`**:
   - $T_{	ext{pub}}$: `2025-11-23 05:57:34.108 UTC`
   - $T_{	ext{settle}}$: `2025-11-23 06:30:00 UTC`
   - 名义 W2: `[2025-11-22 06:30:00 UTC, 2025-11-23 06:30:00 UTC)` (24h)
   - 实际配对区间: `[2025-11-23 05:57:34.108 UTC, 2025-11-23 06:30:00 UTC)`
   - 实际配对时长: **32.43 分钟**
   - 覆盖分类: `TRUNCATED_W2_ARCHIVE_COVERAGE`

其余 30 个有交割排期的合约 W2 均为完整 24h 覆盖；10 个合约无交割排期（`NO_SCHEDULED_SETTLEMENT_TIME`）。
**本报告与矩阵全量严正规范：W2 覆盖定义为“截断与完整 W2 覆盖 (Truncated or Full W2 Archive Coverage)”，严禁将 AIAUSDT 与 PORT3USDT 表述为完整 24h 覆盖。**

---

## 4. 门禁汇总与当前边界

| 门禁项 | 当前状态 | 裁决依据 |
|:---|:---:|:---|
| **EVIDENCE_GAP-01** | **CLOSED** | 经 C 根权威 9 元组物理封签与 Section 4.1 校验通过 |
| **EVIDENCE_GAP-02** | **READY_TO_CLOSE** | P0 (878/380/15/365 全量 S3 前缀普查、5 个非 ASCII 标的实测与逐候选 Provenance) 及 P1 (W2 逐条记录字段与截断规范) 全部实证闭环并落盘 |
| **Design Status** | **DRAFT_PENDING_CLOSURE_CONFIRMATION** | 维持草稿状态，严禁在审核通过前擅自修改 Design 文档 |
| **Implementation Plan** | **BLOCKED** | 严格禁止编写 Plan，禁止修改 `src/` 或 `configs/`，等待用户 / Auditor 正式验收通过并下达指令 |\n