# A/H1 成交压力与价格响应可估计性预审报告

**日期：** 2026-11-19（Asia/Shanghai）  
**执行角色：** Model C — A/H1 可估计性预审执行者  
**性质：** 人工决策参考（`estimability_preflight / read_only_contract_and_source_audit / no_alpha_claim`），**不是 Design、Implementation Plan、正式准入收据、数据消费授权或交易授权**。  
**预算与用时：** 预算上限半个工作日（4 人时）；开始时间 `2026-11-19T15:27:59Z`，结束时间见 §6（未超时、未自动延长、未补数据或扩建）。

---

## 结论：`evidence_insufficient`

**本轮停在冻结上游（Stage 1.5J-A / Stage 1.5J-B / V2 分类账本）的下游消费准入边界：**

1. **已完成的非受限核对**：全部既有规范、冻结上游文件静态身份（SHA-256 与符号链接）、既有主动买入占比与价格/成交额/路径源码、卖压代数关系、固定线性残差共线性、真实函数复用边界以及低维公平实验的统计承载力评估均已核验完毕。
2. **阻断当前给出“值得起草最小实验”或“数据覆盖通过”的最小缺口**：J-A/J-B 冻结上游契约明确规定“收据发布/公开 loader 存在不等于下游消费授权，新 consumer 须另获专门授权”；本轮提示亦明确声明不覆盖冻结上游准入条件。因此本轮**未调用 J-A/J-B strict loader，未解析受限明细，未解压或读取任何 `aggTrades` ZIP 内的成交数值**，无法实测特征窗成交活跃度、成交间隔、`sequence_gap` 与尺度可比的持续净卖压分布。
3. **不越界声明**：本结论为 `evidence_insufficient`，**不代表 H1 已被科学证伪，也不代表本地归档可用于正式实验或存在任何 Alpha 有效证据**。同时，基于源码与既有样本参考规模评估，即使后续获批补做受限只读核验，**`standard crypto` 有限的独立 Parent 样本量与多维度控制（价格路径、波动、活跃度、普通买卖失衡）之间可能存在显著自由度张力**；确切基准变量集、有效秩、估计稳定性与是否暂停，须由后续实测数据与正式 Design 论证，不提前把某一候选维度数写成既定停研门槛，也不得以削弱必要对照来凑出可估计性。

---

## 1. 一页摘要：已确认、未知与下一步取舍

| 维度 | 本轮已确认（有源码/哈希/文档证据） | 本轮仍未知（受限于未获上游消费授权） |
| --- | --- | --- |
| **上游物理文件静态身份** | J-A 4 件套 + closure evidence、J-B 3 件套 + closure evidence/sidecar、V2 分类账本、`configs/stage1_5j_b` 与 J-A/J-B 核心源码均存在、非符号链接，**11 项冻结 SHA-256 全部匹配**。 | 本轮未运行 J-A/J-B strict loader 重放、未逐包核验 280 个 ZIP/`.CHECKSUM` 实际字节与内部 CSV 完整性。 |
| **旧特征与代数关系** | 既有 `launch_taker_buy_share_residual_response.py` 与 `launch_open_interest_basis_exploratory.py` 已解析 `is_buyer_maker` 并计算 `taker_buy_share` 与 `total_notional`；同窗下 `sell_share = 1 - buy_share`、`I = 2*buy_share - 1` 严格仿射等价；固定线性基准残差落入已有线性特征空间，加入线性模型**不扩大特征空间**。 | 跨子窗口持续净卖压（如 $I_{W_1}<0 \land I_{W_2}<0$）在真实 `standard crypto` 样本中的出现频次、相对尺度分布及是否存在极端离群值，**未知**。 |
| **真实复用边界** | `validate_zip_archive_package`、`validate_aggtrades_csv_header`、`select_launch_anchor_trade`、`required_utc_dates_for_window`、`stream_aggtrades_csv_lines`、`build_admitted_ja_context`、`open_verified_package_stream` 可按契约复用；既有 `evaluate_child_residual_response`、`verify_single_run_authorization`、`calculate_baseline`、`load_child_aggtrades_from_ja_root` 均存在协议/授权硬绑定或语义差异，**不可直接借用**。 | 无。 |
| **窗口覆盖与可估计性** | 仅从既有人工文档参考可知，历史研究涉及 `standard crypto` 约 42 个候选 Parent（旧 OI 研究完整 41 个），但不等同于 H1 候选窗口的合格数。 | 逐 Parent/symbol 在 H1 候选观测窗内的时间连续性、成交笔数/成交额衰减、成交间隔、`sequence_gap` 数量、买卖方向分布、可比卖压密度、跨日与同批事件依赖，**全部未知**。 |
| **未来实时可得性与交易** | `configs/base.py:RISK_LIVE_TRADING_ENABLED = False`；历史 `aggTrades` 归档不含挂撤单、最优报价与真实成交滑点，不能推出实时可得或可交易收益。 | 未来如走通探索，仍缺实测点差、深度冲击与独立新样本验证池（11-10 预审在 2026-09-07 至 11-09 仅确认 1 个已知暴露候选 `CTUSDT`）。 |

**下一步是否值得投入：**
- **当前不建议直接起草最小实验 Design/Plan**（缺少最基本的特征窗可比卖压与连续性事实）。
- **可选最小下一步（仅 2~3 人时，零仓内代码改动）**：若用户希望闭环“数据到底能不能测 H1”这一事实问题，须先按 §2.2 明确受限只读预审的真实调用链与上游治理准入形式（含区分“上游冻结收据完整性重验附带计算”与“H1 新结果零收益计算”，并处理 J-B Design L295 / J-A Design L65 对新 consumer 的专门授权要求），再由仓外脚本经严格身份核验后只读检查 `standard crypto` 特征窗的活跃度、序列连续性与可比卖压分布，据实决定“起草最小实验”或“暂停”。
- **另一理性选项（零新增投入）**：鉴于旧 `standard` 样本已反复暴露、后续新事件稀少（2 个月仅 1 个已知暴露事件），且多变量控制与条件卖压子集在小样本下存在较高的自由度与稀疏性风险，用户亦可直接选择**暂缓投入**，将 H1 保留为未证伪的待观察假设。

---

## 2. 来源与准入表

### 2.1 基线与上游静态身份核对结果

核对方法：纯只读静态文件存在性、符号链接检查（`os.path.islink`）与 `hashlib.sha256` 字节摘要比对；**未调用任何 strict loader、未解析受限 JSON/CSV 明细、未解压任何 ZIP**。

| 类别 | 路径 | 预期冻结 SHA-256 | 本轮实测 SHA-256 | 验证状态 | 消费限制（冻结契约） |
| --- | --- | --- | --- | --- | --- |
| 讨论文档 1 | `docs/reviews/2026-11-12-launch-event-data-research-directions-discussion_CN.md` | — | `5f76049319c259356840f8845089322b28fb4498937f24cae4e50038edbfb737` | `RECORDED`（工作区有既有修改，已保留） | 讨论参考，不授予数据消费或运行权限 |
| 讨论文档 2 | `docs/strategy_specs/2026-11-18-crypto_alpha_cross_domain_theories_research_agenda_CN.md` | — | `8b5df15d0ce1803785dbbe6f5067072a870cc09c73dbce242caee3bc94f629e8` | `RECORDED`（既有未跟踪文件，已保留） | 理论地图，不授予数据消费或运行权限 |
| J-A 替换根 manifest | `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/manifest.json` | `b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf` | 一致 | `MATCH`（非软链） | J-A Design §1/INV-15J-A-10 与 Profile v2 Delta §4.2：不授予未专门批准的新下游 consumer 权限；13 项 `authority_flags` 全 `False` |
| J-A 替换根 summary | `.../stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/summary.json` | `722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b` | 一致 | `MATCH`（非软链） | 同上；调用 `load_verified_stage1_5j_a_...` 须先获新 consumer 消费授权 |
| J-A 替换根 journal | `.../stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/request_journal.jsonl` | `b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa` | 一致 | `MATCH`（非软链） | 同上 |
| J-A 替换根 review | `.../stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/review_CN.md` | `1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152` | 一致 | `MATCH`（非软链） | 仅人工可读摘要，不替代 strict loader 或 ZIP 核验 |
| J-A 闭环凭据 | `.git/plan-execution/governance_artifact_schema/ba362f2480c7872d39eede9254744d6e99216aa73134777658f9f81f05ba7881/evidence/v2_receipt_closure_evidence.json` | `c0810b95dc94c740dbc41d55ce01d51d1bd7a09e382b292e156d2522d621e68b` | 一致 | `MATCH`（非软链） | 证明 J-A 替换根通过收据闭环审计，不自动授予下游消费 |
| J-B 生产根 manifest | `data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z/manifest.json` | `f0a8ac724925084161f6b9aa2dced5139b261707fda0f0f21ebd0eb6de3087fb` | 一致 | `MATCH`（非软链） | J-B Design L272/295/INV-JB-10 与兼容 Delta L199：`receipt published != downstream consumer authority`，新 consumer 须另行明确授权 |
| J-B 生产根 summary | `.../stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z/summary.json` | `5ea0f1c87803114c4c6917cd0c3d24292948fa0e7066a80e0a2bce611e32546b` | 一致 | `MATCH`（非软链） | 同上；12 项 `authority_flags` 全 `False` |
| J-B 生产根 review | `.../stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z/review_CN.md` | `17e9ffaa973923868621a8ee925dc811c15e12459924ee63897f9c21fcac317e` | 一致 | `MATCH`（非软链） | 仅人工摘要 |
| J-B 闭环凭据 + sidecar | `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/64e14726202b53727a7627139578369cb6af54f08d5a785d4df006009eb25a2d/evidence/receipt_closure_evidence.json`（及 `.sha256`） | `8d535303...8f8b6d` / `c3856c2e...949c5d9` | 全部一致 | `MATCH`（非软链） | 证明 J-B 闭环审计通过，不授予新 consumer 权限 |
| V2 分类账本 | `data/exports/stage1_5j_token_launch_classification_ledger_v2.csv` | `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b` | 一致 | `MATCH`（非软链） | 位于被 Git 忽略的 `data/exports/`；须经 SHA 校验并与 J-B `child_rows` 281 键双射 + J-A 正文 AST 重证后方可用作分类来源（参考 `launch_taker_buy_share_residual_response.py:1376`） |
| 冻结配置（全局） | `configs/base.py` | — | `ffbc2129a206d3ff7c0a039f10fabc6446a52c9f85c9a869975821b9c0d87079` | `RECORDED`；`RISK_LIVE_TRADING_ENABLED = False` | 唯一共享风控配置源，本轮未修改 |
| 冻结配置（J-B 例外） | `configs/stage1_5j_b_historical_aggtrades_launch_response.py` | `771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4` | 一致 | `MATCH` | 9 项 J-B 离线常量（含 `MAX_ANCHOR_DELAY_MS=300_000`, `STREAM_CHUNK_BYTES=65_536`） |
| 上游核心源码（J-A / J-B） | `src/research/external_signal_shadow/stage1_5j_a_...py` / `stage1_5j_b_...py` | `250fdb9f...2e1e18` / `b2ca8e28...b02fa4f` | 全部一致 | `MATCH` | 只读源码核对，未修改 |
| 既有主动买入占比源码 / CLI | `src/research/external_signal_shadow/launch_taker_buy_share_residual_response.py` / `scripts/.../run_launch_taker_buy_share_residual_response.py` | — | `ef126ceb...9a41df` / `b56d74ef...71dd1` | `RECORDED`（对应 Design `5c05cb30...`、Plan `e644e9df...` 均 `MATCH`） | 含独立单次运行授权门禁，严禁借用其授权运行 H1 |
| 既有 OI/基差源码 / 增量 CLI | `src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py` / `scripts/.../run_launch_price_oi_basis_incremental_information.py` | — | `ed9d6876...5426be` / `daf8c9d5...3651d` | `RECORDED`（对应 OI 父 Design `82dd5831...`、归档人工报告 `5f57a97d...` 均 `MATCH`） | 同上；旧产物仅供人工阅读，不默认作为 H1 机器输入 |

### 2.2 阻断受限读取的最小缺口、真实调用链与所需授权

**为何本轮停在此边界（不伪造、不绕过、不借用其他阶段授权）：**
- 冻结契约明确约束：J-A Design（L65：`No other file, permission, lifecycle owner, downstream consumer or public production entrypoint is authorized by this Design`）、J-B Design（L272：`receipt published != downstream consumer authority`；L295：`future consumer | only separately authorized research Design`；INV-JB-10）、J-B 兼容 Delta（L199）以及既往全部三个合法下游 consumer（`Stage 1.5J-C`、`launch_taker_buy_share_residual_response`、`launch_open_interest_basis_exploratory`）均要求：**调用 J-A/J-B strict loader 与解压 `J-A/raw/archive/*.zip` 必须具备面向当前新 consumer 的明确准入授权，不可跳过 strict loader，也不可仅靠声明“一次预审、非正式下游”就默认满足 J-B Design L295 的“单独授权的研究 Design”条件**。
- 本轮用户提示明确约定：“公开 loader 存在不等于有消费权限。本提示不覆盖冻结上游的准入条件；若仍缺少特定 consumer、身份或单次消费绑定，停在该边界，交付最小缺口与所需授权”。

**下一步受限只读预审的真实调用链、读取范围与附带计算（先厘清机制冲突，再定授权）：**

| 候选只读路径 | 真实调用链（不可跳过 strict loader） | 读取范围 | 附带计算与边界区分 | 治理准入缺口（须用户/治理显式批准） |
| --- | --- | --- | --- | --- |
| **路径 A：双上游接入（J-A + J-B，直接复用 J-B 锚点与 281 键双射）** | `load_verified_stage1_5j_b_historical_aggtrades_launch_response_root` (`stage1_5j_b_...py:1380`) → 内部调用 `admit_upstream_j_a_root` (`L1553`) 与 `load_verified_stage1_5j_a_historical_archive_coverage_root` (`stage1_5j_a_...py:1341`) → **内部调用 `_reduce_verified_aggtrades_launch_response` (`stage1_5j_b_...py:1635`)** → V2 账本 SHA/281 键双射/J-A 正文 AST 核验 → `build_admitted_ja_context` + `open_verified_package_stream` + `stream_aggtrades_csv_lines` 流式读取目标 `standard crypto` 特征窗 | J-A/J-B 冻结收据、J-A catalog/detail/全部 280 个归档包（用于 J-A/J-B 校验）、V2 分类账本、目标 `standard crypto` 特征窗 7 列字段 `(agg_trade_id, price, quantity, first_trade_id, last_trade_id, transact_time, is_buyer_maker)`；对 H1 未来标签窗仅检查时间戳覆盖与记录存在性 | **关键区分**：J-B strict loader **不是只读清单和锚点**，它在 `stage1_5j_b_...py:1635` 会重放原始归档并在 `L1276–1293` 重新计算 J-B 既有冻结的 `5m/1h/4h` `gross_return_bps` 与 `sampled_max/min_excursion_bps` 以校验 `summary.json` 一致性。因此必须严格区分：**（1）上游冻结结果重验**（仅限 J-B strict loader 内部一致性断言，预审脚本禁止消费、输出、排名或汇总其中任何收益/极值字段）与 **（2）H1 新结果计算**（严禁对 H1 窗口计算任何未来收益、MAE/MFE、相关性或拟合） | 1）须明确处理 **J-B Design L295**（`only separately authorized research Design`）要求：要么单独批准一份极简只读预审 Design，要么由用户作为治理负责人显式签发书面治理例外/单次授权说明；<br>2）须**显式批准** J-B strict loader 内部执行既有冻结收据重验重放（`upstream_frozen_receipt_replay_allowed=true`，且禁止消费其收益输出），同时保持 `h1_new_future_return_or_path_calculation_allowed=false` |
| **路径 B：仅接入 J-A 替换根 + V2 账本（不消费 J-B 收据，就地调用 `select_launch_anchor_trade` 确定 $T_0$）** | `load_verified_stage1_5j_a_historical_archive_coverage_root` (`stage1_5j_a_...py:1341`，校验 manifest/summary/journal/catalog/detail 与全部 ZIP/`.CHECKSUM`，**不计算任何收益或路径极值**) → V2 账本 SHA 校验与 J-A `parent_records` 键/正文 AST 核验 → `build_admitted_ja_context` + `open_verified_package_stream` + `stream_aggtrades_csv_lines` + `select_launch_anchor_trade` (`stage1_5j_b_...py:764`，纯函数) | J-A 冻结收据与归档包（用于 J-A strict loader 校验）、V2 账本、目标 `standard crypto` 的 `[launch_ms, T0]` 锚定流与 `S1`/`S2` 特征窗 7 列字段；对未来标签窗仅检查时间覆盖与记录存在性 | **零上游收益重放，零 H1 收益计算**；但不再消费 J-B 收据本身，故不做 J-B `child_rows` 281 键对照（锚点按 J-B 同一纯函数 `select_launch_anchor_trade` 与 `MAX_ANCHOR_DELAY_MS=300_000` 规则独立确定） | 仍受 **J-A Design L65** 与 **Profile v2 Delta §4.2** 约束：须由用户明确批准新 consumer 对 J-A 替换根的单次离线只读预审准入形式（明确采用精简预审 Design 或单次只读预审治理授权），不得默认放行 |

**最小所需授权绑定清单（无论选择路径 A 或路径 B，均须显式列明；不要求新建正式 Stage、收据生成器或完整 Rule 17 Verifier）：**
1. **明确 consumer 身份与治理准入形式**：写明 `operation = "h1_estimability_preflight_read_only_once"`、选定路径（路径 A 或路径 B），以及针对 J-A Design L65 /（如选路径 A）J-B Design L295 的明确治理批准形式（独立极简 Design 或用户显式书面单次只读预审例外）。
2. **精确绑定上游只读身份**（沿用 §2.1 已验证的精确路径与 SHA-256）：
   - `ja_root_relative_path`（`20261010T163500Z`，manifest `b6654906...`、summary `722c3be6...`、closure `c0810b95...`）；
   - 如选路径 A：`jb_root_relative_path`（`20261014T044500Z`，manifest `f0a8ac72...`、summary `5ea0f1c8...`、closure `8d535303...`）；
   - `ledger_relative_path`（`stage1_5j_token_launch_classification_ledger_v2.csv`，SHA `36e56f45...`）。
3. **显式区分“上游重验”与“H1 新计算”权限开关**：
   - 仅当选路径 A 时：`jb_strict_loader_frozen_receipt_replay_verification_allowed=true`（且明确禁止预审脚本消费、记录或汇总 J-B `child_horizon_rows` / `parent_horizon_rows` 中的任何收益与极值字段）；
   - 两条路径均强制 `False`：`h1_future_return_or_path_calculation_allowed=false`、`model_fitting_allowed=false`、`network_allowed=false`、`signal_allowed=false`、`paper_trading_allowed=false`、`live_trading_allowed=false`、`execution_allowed=false`。
4. **明确仓外预审脚本与输出位置**：固定一次性只读脚本路径（保存于仓外临时目录并记录 SHA-256）及唯一允许更新/新增的人工报告路径。

---

## 3. Parent / symbol 覆盖与可估计性表（分母守恒与事前候选窗口）

### 3.1 读取成交数值前预先声明的探索性候选窗口（未执行读取）

遵照 [讨论备忘 §4.1](2026-11-12-launch-event-data-research-directions-discussion_CN.md#41-参数依据与实验固定不是一回事2026-11-19)，**不把原议程的 `60m/15m` 或三段等长 15m 窗口当作默认参数**。在未来获批读取任何成交数值前，预先定义以下两组 **`exploratory_preflight_candidate`（探索性预审观察尺度）**，选择理由仅基于机制结构与数据粒度，**完全不依赖未来收益**：

| 预审候选尺度 | 早期噪声缓冲 | 特征前段 $W_1$ | 特征后段 $W_2$ | 未来标签窗（**仅查时间/记录覆盖，不查价格**） | 设定理由与待核验问题 |
| --- | --- | --- | --- | --- | --- |
| **S1（短尺度，探索候选）** | $[T_0, T_0+5\text{m})$ | $[T_0+5\text{m}, T_0+15\text{m})$ | $[T_0+15\text{m}, T_0+25\text{m})$ | $[T_0+25\text{m}, T_0+40\text{m}]$ | 1）只需 2 段子窗即可定义“持续卖压”与“响应减弱”，避免 3 段切窗进一步抬升基准维度；2）避开首 5 分钟开盘极端价差跳变；3）总特征跨度与既有 OI/基差研究决策点 $D=T_0+25\text{m}$ 对齐，便于后续理解数据活跃度衰减。 |
| **S2（中尺度，探索候选）** | $[T_0, T_0+15\text{m})$ | $[T_0+15\text{m}, T_0+35\text{m})$ | $[T_0+35\text{m}, T_0+55\text{m})$ | $[T_0+55\text{m}, T_0+70\text{m}]$ | 检验开盘后 15~55 分钟是否仍保持足够成交密度与可比卖压，还是成交额已相对首 15 分钟剧烈冷却、导致卖压不可比或断档。 |

**尺度可比的卖压观测口径（绝不将不同币种绝对 USDT 成交额直接视为相同压力）：**
- 未来获批读取后，应对每个子窗 $W_k \in \{W_1, W_2\}$ 同时记录：
  1. 无量纲归一化净卖压 $-I_{W_k} = (S_{W_k} - B_{W_k}) / V_{W_k} \in [-1, 1]$（跨币种量纲一致）；
  2. 相对同币种缓冲窗成交额的净卖压强度 $-Q_{W_k} / V_{\text{buf}}$（消除币种市值/绝对流动性差异；若 $V_{\text{buf}}$ 异常偏低则标记不可估计）；
  3. 持续净卖压指示条件：$Q_{W_1} < 0 \land Q_{W_2} < 0$（即两段均为净卖出），并统计跨币种的 $V_{W_2} / V_{W_1}$ 活跃度衰减比与 $|Q_{W_2}| / |Q_{W_1}|$ 卖压保持比。

### 3.2 Parent / symbol 分母守恒与当前核验状态表

> **严格区分四个不同证据层级（绝不互相替代）：**
> 1. **元数据/文件可定位**：上游根目录、manifest、summary、账本文件在本地存在且静态 SHA-256 匹配（**本轮已确认**）。
> 2. **物理校验通过**：通过 strict loader、`.CHECKSUM`、ZIP 资源上界与全流式 CSV 校验至 EOF/CRC（**本轮未执行，待消费授权**）。
> 3. **窗口可用与可估计**：目标 `standard crypto` 集合内各子窗无 `sequence_gap`、活跃度达标、存在可比持续净卖压、未来标签窗时间覆盖完整（**本轮未执行，待消费授权**）。
> 4. **未来可实时取得（PIT）**：真实上线时刻通过交易所实时流以可接受延迟取得完整逐笔方向与价格（**离线历史归档永远无法单独证明**）。

| 统计层 / 核验项 | 既往文档参考口径（仅作背景追溯，非本轮实测） | 本轮实际核验状态 | 缺失 / 无法确认的具体原因 |
| --- | --- | --- | --- |
| J-A / J-B 顶层全量分母 | J-A 365 天窗口：131 目标 Parent（120 完整、11 缺口），281 范围内 USDT child（280 归档完整、1 缺口 `AIAUSDT`）；J-B 281 child（278 `anchor_found`、2 继承 gap、1 延迟超 300s）。来源：J-C Design §2.2。 | 文件存在且静态 SHA-256 全部匹配；**未调用 strict loader 重放** | `blocked_pending_upstream_consumer_authorization`（缺少 H1 预审单次只读消费授权） |
| `standard crypto` 候选集合（V2 账本） | 参考规模：53 child / 42 Parent（其中 J-B 参考 51 child 有锚点、2 child 继承 J-A gap，对应旧 OI 研究 41 完整 Parent、1 缺锚点 Parent）。来源：J-C Design §2.2、11-06 总结。 | 账本 SHA-256 匹配 `36e56f45...`；**未在本次消费读取逐行明细或重证 J-A 正文 AST** | 同上；旧 41 Parent 仅作参考，不作为本次固定名单或合格数 |
| 逐 Parent/symbol 分类、官方上线时间与 `T0` anchor | 未按 H1 独立核验 | `unknown / not_executed` | 同上 |
| 逐 symbol ZIP/`.CHECKSUM` 实际核验与所需日期覆盖 | J-C 预审曾初筛 15m 窗口不跨午夜，但**不得外推至 S1（40m）或 S2（70m）窗口有效** | `unknown / not_executed` | 同上；需按真实 `T0` 与目标窗口动态检查 `required_utc_dates_for_window` |
| 字段、时间精度、排序、重复 ID 与 `sequence_gap` | 源码契约确认 schema 为 7 列且整数毫秒，但逐包内部质量未针对 H1 窗口实测 | `unknown / not_executed` | 同上 |
| 特征窗成交数量、成交额、成交间隔、买卖方向与卖压分布 | 既有文档无分窗（$W_1, W_2$）净卖压与活跃度衰减统计 | `unknown / not_executed` | 同上 |
| 尺度可比的持续净卖压有效 Parent 数 | 无历史记录 | `unknown / not_executed` | 同上；此项为决定 H1 能否做低维比较的最关键未知项 |
| Parent/child 多标的、跨 UTC 日与同日同批事件依赖 | 已知 53 child / 42 Parent 存在同公告多 child 簇；同日跨 Parent 宏观共振风险存在 | `partially_known_from_docs / unverified_for_h1` | 需获批读取后按 `parent_article_id` 与 `utc_date` 重新汇总实际有效集 |
| 未来标签区间时间/记录覆盖（仅查覆盖，不查价格） | 未核验 | `unknown / not_executed` | 同上 |
| 后续时间外 `standard` 候选池（2026-09-07 至 11-09） | [11-10 预审](2026-11-10-standard-launch-oi-b-followup-preflight_CN.md) 仅确认 1 个候选 `CTUSDT`（且已有 1.5G/1.5H 项目暴露） | 已核对 11-10 报告结论（非本轮重检索） | 说明即便旧样本探索有线索，短期内仍无充足独立时间外验证集 |

---

## 4. 旧特征重复性与真实复用接口说明

### 4.1 既有主动买入占比、价格、成交额与路径计算核对

逐行核查仓库源码，确认项目**已有两个完整模块直接解析 `is_buyer_maker` 并计算主动买入占比与成交额**，不存在“首次使用成交方向”的说法：

| 源码模块 | 窗口定义 | 精度与排序 | 已计算的特征与路径指标 | 与 H1 的区别 |
| --- | --- | --- | --- | --- |
| [`launch_taker_buy_share_residual_response.py`](../../src/research/external_signal_shadow/launch_taker_buy_share_residual_response.py) (L311–694) | 特征窗 `[T0, T0+60s)`；延迟 `3s`；入场 `[T0+63s, T0+64s]` 首笔；终点 `entry+15m`（`[E-1s, E]` 末笔） | `Decimal -> Fraction` 精确有理数；严格校验 `(ts, aggregate_id)` 递增及 `tid == prev_id + 1`（检出 `sequence_gap`）；$O(1)$ 流式内存 | `feature_trade_count`、`feature_max_intertrade_gap_ms`、`total_notional`、`taker_buy_share = buy_notional / total_notional`（`is_buyer_maker is False`）、`vwap`、`vwap_deviation`；路径 `terminal_return`、`long_mae`、`long_mfe` | 仅首 60 秒单窗汇总，按样本中位数二分 `high/low`；无分窗时间演化、无卖压—下行响应交互。注：仓内未检索到该模块已归档的历史运行报告。 |
| [`launch_open_interest_basis_exploratory.py`](../../src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py) (L580–703) | 基准窗 `[T0, D)`（默认 `D = T0+25m`）；入场 `[D, D+5s]` 首笔；终点 `entry+15m` | `float`；按 `(transact_time_ms, trade_id)` 排序；列表全量载入内存 | `calculate_baseline` 计算 `trade_count`、`price_change = last/first - 1`、`total_notional`、`taker_buy_share`；`calculate_path_response` 计算 `terminal_return`、`long_mae`、`long_mfe` | 单窗汇总；后续 [`run_launch_price_oi_basis_incremental_information.py`](../../scripts/external_signal_shadow/run_launch_price_oi_basis_incremental_information.py) (L630–692) 仅取了 `baseline_price_change`（`p`），**并未将 `baseline_taker_buy_share` 或 `baseline_total_notional` 放入 OLS**。 |
| [`stage1_5j_b_historical_aggtrades_launch_response.py`](../../src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py) | `5m / 1h / 4h` 固定终点 | `Decimal` | `gross_return_bps`、`sampled_max_excursion_bps`、`sampled_min_excursion_bps`、`trade_count` | 未使用 `is_buyer_maker`，未计算成交额。 |

### 4.2 卖方占比、买方占比与归一化失衡的精确代数关系

对任意成交额 $V_W = B_W + S_W > 0$ 的窗口 $W$，记买方占比 $b_W = B_W / V_W$：

$$s_W = \frac{S_W}{V_W} = 1 - b_W, \qquad I_W = \frac{Q_W}{V_W} = \frac{B_W - S_W}{V_W} = 2 b_W - 1 = 1 - 2 s_W$$

- **结论 1（严格线性冗余）**：同窗同成交额口径下，`taker_buy_share`（$b_W$）、主动卖出占比（$s_W$）与归一化净买卖失衡（$I_W$）互为精确仿射变换，**仅含 1 个独立自由度**；改名或取负号不是新特征。
- **结论 2（绝对额跨币种不可比）**：绝对净卖额 $-Q_W = -V_W I_W$ 受币种流动性规模主导（不同新币开盘首小时成交额可差一到两个数量级），不能把不同币种的绝对 USDT 净卖出额直接视为相同卖压。

### 4.3 固定线性基准残差的共线性核对

若在训练期估计固定线性同期响应模型 $\hat{r}_W = \hat{\alpha} + \hat{\lambda} Q_W + \hat{\beta}^\top X_W$ 并构造残差 $e_W = r_W - \hat{r}_W$：
1. 当后续预测模型的基准特征集 $Z_{\text{base}}$ 已包含 $(1, r_W, Q_W, X_W)$（或其张成子空间）时，$e_W \in \operatorname{span}(Z_{\text{base}})$。将其再加入线性预测模型会导致设计矩阵**严格列秩亏**，列空间维度增加为 **0**，OLS 预测值恒等不变（在满列秩约束下甚至直接触发 `not_estimable`）。
2. 同理，对两个子窗口 $W_1, W_2$ 使用跨事件固定的常系数 $(\hat{\lambda}, \hat{\beta})$ 构造残差差值 $\Delta e = e_{W_2} - e_{W_1}$，只要基准已包含两窗各自的价格变化与压力/控制量，$\Delta e$ **依然是基准特征的精确线性组合**，线性模型下完全冗余。
3. 因此，H1 若采用线性/广义线性模型检验，**严禁把固定线性基准残差或残差一阶差作为“新增特征”塞入扩展模型**；扩展项必须具备真实的非线性/条件交互结构（见 §5.2）。

### 4.4 真实复用接口清单（不以“文件存在/可导入”冒充复用）

| 能力类别 | 具体符号与位置 | 真实复用分类 | 调用边界与不复用理由 |
| --- | --- | --- | --- |
| ZIP 资源上界校验 | `validate_zip_archive_package` (`stage1_5j_b_...py:569`) | **可直接调用** | 纯文件/ZIP 元数据校验（256MB zip / 512MB csv / 64x ratio / 单 CSV），无阶段授权耦合。 |
| CSV 表头校验 | `validate_aggtrades_csv_header` (`stage1_5j_b_...py:602`) | **可直接调用** | 精确比对 7 列头。 |
| Anchor 选择 | `select_launch_anchor_trade` (`stage1_5j_b_...py:764`) | **可直接调用** | 纯函数，`transact_time >= launch_ms` 且延迟 $\le 300{,}000\text{ ms}$。 |
| 所需 UTC 日期计算 | `required_utc_dates_for_window` (`launch_taker_buy_share_...py:250`) | **可直接调用** | 整数毫秒算术，无 float 舍入误差，优于 `timestamp()` 除法版本。 |
| 有界 CSV 行流 | `stream_aggtrades_csv_lines` (`launch_open_interest_basis_...py:1618`) | **可直接调用** | 强制 65,536 字节物理行上限与严格 UTF-8 解码。 |
| J-A 包流式准入与读取 | `build_admitted_ja_context` / `open_verified_package_stream` (`launch_taker_buy_share_...py:1558,1635`) | **经授权后可调用** | 无硬编码阶段 Design SHA，完整验证 `logical_archive_identity`、request linkage、manifest SHA、`.CHECKSUM`、ZIP caps 与 `_BoundedStreamReader`；但调用前提是已获上游消费授权并经 J-A strict loader 拿到 `ja_summary`。 |
| J-A / J-B 严格加载器 | `load_verified_stage1_5j_a_...` (`stage1_5j_a_...py:1341`) / `load_verified_stage1_5j_b_...` (`stage1_5j_b_...py:1380`) | **受限公开接口（待授权，须区分附带重放）** | 公开存在不等于有消费权限；其中 J-A strict loader 重放 journal/catalog/detail 与全部 ZIP/`.CHECKSUM` 校验（不计算收益），而 J-B strict loader **不是只读清单和锚点**，会在 `stage1_5j_b_...py:1635` 重放原始归档并在 `L1276–1293` 重算既有冻结 `5m/1h/4h` 历史收益与极值以核验一致性（调用前须按 §2.2 明确治理准入与重验边界）。 |
| J-B 私有流读取器 | `_open_verified_package_stream` / `_ChunkBoundedReader` (`stage1_5j_b_...py:607,639`) | **禁止调用（私有）** | 前导下划线私有实现，J-C 与 TakerBuyShare 契约已明文禁止下游依赖。 |
| 既有单 child 评估与归约 | `evaluate_child_residual_response` / `stream_and_evaluate_admitted_child` (`launch_taker_buy_share_...py:311,1893`) | **仅可参考（不可直调）** | 内部硬锁 60s/3s/15m 协议 SHA (`17cb308b...`) 且会计算未来收益/MAE/MFE。 |
| 既有基准与路径计算 | `calculate_baseline` / `calculate_path_response` (`launch_open_interest_basis_...py:580,614`) | **仅可参考（不可直调）** | 单窗汇总、无波动/间隔统计、采用 `float` 而非 `Fraction`；且 `calculate_path_response` 计算未来收益。 |
| 既有 aggTrades 内存加载 | `load_child_aggtrades_from_ja_root` (`launch_open_interest_basis_...py:2545`) | **仅可参考（不建议直调）** | 将窗口内全部成交装入内存列表且转 `float`，且未检测 `tid != prev_tid + 1` 的 `sequence_gap`。 |
| 既有授权与账本函数 | `verify_single_run_authorization`（两模块均有）、`verify_v2_ledger_and_select_universe` (`launch_taker_buy_share_...py:1376`) | **禁止借用（仅参考结构）** | 授权函数硬绑定旧 Design/Plan SHA；账本选择函数硬锁 `expected_selected_count=71`（合并了 `pre_market`），H1 仅看 `standard` 须单独筛选并保持分母透明。 |

---

## 5. 低维公平比较的可行性、主要限制与后续投入估计

> 本节仅作方法与可行性评估，**不运行实验、不拟合模型、不硬编码固定样本门槛或固定成本门槛**。

### 5.1 候选低维基准设计及其控制假设（非冻结下限）

要在两段特征子窗（$W_1, W_2$）结构下把 H1 与“普通价格路径、波动状态、成交活跃度变化、普通买卖失衡”区分开来，下面给出**一组探索性候选低维控制设想**（示意 5~7 个特征，含截距约 6~8 个参数）。**需明确：这是待后续数据与正式 Design 检验论证的候选控制假设，而不是已证明的“强制变量清单”或不可修改的参数下限**（实际控制项的选取、共线性精简与函数形式须以实测特征矩阵诊断和后续 Design 论证为准）：

1. **累计价格变化**（候选如 $r_{\text{tot}} = r_{W_1} + r_{W_2}$）：用于控制特征期整体涨跌方向与幅度；
2. **价格路径变化/减速**（候选如 $r_{\text{decel}} = r_{W_2} - r_{W_1}$）：用于防范普通下跌放缓（例如从 $-2\%$ 变为 $-0.1\%$）直接冒充“卖压响应减弱”；
3. **特征窗实现波动**（候选如子分钟对数收益标准差或对数高低幅 $\sigma_{\text{feat}}$）：用于控制波动率状态；
4. **成交活跃度及变化**（候选如对数活跃度变化 $\Delta \log V = \log(V_{W_2} / V_{W_1})$，视实测相关性决定是否同时纳入总活跃度 $\log(V_{W_1} + V_{W_2})$）：用于控制开盘后自然冷却；
5. **普通买卖失衡**（候选如总失衡 $I_{\text{tot}}$ 或后段失衡 $I_{W_2}$，等价于 `taker_buy_share`；是否再纳入两段失衡差 $\Delta I = I_{W_2} - I_{W_1}$ 需视实测冗余度与自由度权衡）。

### 5.2 候选非线性交互设想与反冗余边界（非唯一表达、不保证有效秩）

- **已证伪/应排除的冗余表达**：同窗 `sell_share`/`I_W`（严格仿射等价，见 §4.2）、固定常系数线性残差 $e_W$ 或 $\Delta e$（落入已有线性张成空间，见 §4.3）。
- **候选非冗余表达设想（探索方向，非唯一形式，本轮不冻结公式或阈值）**：
  - 一种可能思路是构造**单一条件非线性交互项**，只在“两段均为持续净卖压（例如 $I_{W_1} < 0 \land I_{W_2} < 0$）”时激活，用于尝试刻画“在持续净卖压背景下，后段相对前段的下行价格响应减弱”，示意结构如：
    $$h_{\text{H1}} = \mathbb{I}(I_{W_1} < 0 \land I_{W_2} < 0) \cdot P_{\text{sustained}}(I_{W_1}, I_{W_2}, V) \cdot \Delta_{\text{resp}}(r_{W_1}, r_{W_2}, I_{W_1}, I_{W_2})$$
  - 其中 $P_{\text{sustained}}$ 尝试刻画两段持续净卖压强度（示意如 $\min(-I_{W_1}, -I_{W_2})$），$\Delta_{\text{resp}}$ 尝试刻画相对卖压的下行响应变化。
  - **严格限定其局限性（避免过度宣称）**：
    1. 在基准中纳入价格变化/减速、活跃度变化与普通失衡是合理的反混杂方向，但**不构成“加入该组合即自动保证交互具备独立增量”的唯一保证**；
    2. 非线性/条件交互形式只避免代数恒等共线，**并不保证在真实有限样本中提高设计矩阵的有效秩或估计稳定性**（若持续卖压子集过稀或与基准变量高度近似共线，仍可能出现高方差或病态）；
    3. 确切特征公式、控制集精简、实测条件数/有效秩、估计稳定性与可检测精度，须留待后续受限实测数据与正式 Design 论证。

### 5.3 样本、压力可比性与噪声的承载力风险评估

即使尚未读取原始逐笔记录，仅从数学结构与既有项目记录即可预见以下四个主要风险（**其中维度与样本张力作为后续实测核验的重点风险项，不将 6~8 维预设为当前既定停研门槛**）：

1. **小样本与条件稀疏风险（需实测数据与 Design 论证）**：
   - 既有文档中 `standard crypto` 参考规模约 41 个完整 Parent（按时间切分或留一法时训练集仅 24~40 个 Parent）。
   - 在上述候选低维控制设想下（约 6~8 个基准参数，叠加 1 个候选交互项约 7~9 个参数），参数规模相对有限独立 Parent 已较紧凑；即使后续 Design 论证出更精简的控制组合，小样本自由度约束依然存在。
   - 更关键的是**条件稀疏效应**：条件交互项仅在满足“持续净卖压”的 Parent 子集上非零。若实测读数显示符合条件的有效独立 Parent 数量非常少，有效信息将高度集中于极少数事件，估计方差与单事件敏感度风险会显著上升（类似历史 `pre_market` A 情景中单折 `KITEUSDT` 失稳的前车之鉴）。
   - **方法边界**：后续是否具备足够的可检测精度与估计稳定性，须基于受限只读预审的实测分布及后续 Design 论证决定；同时坚持**不得通过删减必要的价格、波动或活跃度对照来人为制造表面可估计性**。
2. **微观噪声混杂（无同步报价）**：
   - `aggTrades` 仅有成交价，无最优买卖报价（midquote）。在薄盘口新币上，主买与主卖交替成交引入的 bid-ask bounce 噪声与瞬时价格冲击混杂，会直接降低子窗价格响应的信噪比。
3. **跨币种压力可比性未验证**：
   - 新币首小时总成交额与流动性分化极大，归一化失衡 $I_W$ 掩盖绝对规模，绝对成交额 $Q_W$ 无法跨币种比较，相对缓冲窗成交额又依赖缓冲窗本身无异常。必须先在受限只读预审中实测各口径分布，才能判断是否可比。
4. **开发集暴露与后续验证瓶颈**：
   - 旧 `standard` 样本已在多轮研究中反复观测，即使做出正向探索结果也仅能标为 `exploratory`，不能充当样本外确认；而 [11-10 预审](2026-11-10-standard-launch-oi-b-followup-preflight_CN.md) 表明 2026-09-07 至 11-09 仅新增 1 个已知暴露候选 `CTUSDT`，短期内缺乏足量独立新事件检验。

### 5.4 后续新增投入估计（端到端，不含沉没成本）

| 阶段 | 范围与交付物 | 预计新增投入 | 前置条件与停止边界 |
| --- | --- | --- | --- |
| **阶段 A：补完本预审受限数据只读核验** | 仓外一次性流式校验脚本（按 §2.2 选定路径 A 或路径 B 接入 strict loader 与 `open_verified_package_stream` + `stream_aggtrades_csv_lines`）+ 补齐本报告 §3.2 实测分母与压力分布表；**零 H1 未来收益计算、零仓内代码改动**。 | **2 ~ 3 人时**（外部支出 `$0`，无联网） | 须先按 §2.2 明确路径并完成对应治理准入批准（含处理 J-A Design L65 / 如选路径 A 则含 J-B Design L295 及显式区分上游冻结收据重验重放与 H1 零收益计算）。若实测持续净卖压样本过稀或 `sequence_gap`/活跃度坍塌严重，**直接暂停，总投入止步于此**。 |
| **阶段 B：H1 最小探索实验（仅当阶段 A 确认可估计时）** | 1 份精简 Design（含 L2 §15 项与经论证的精确基准/交互公式、有效秩与可检测精度分析）+ 独立 B 评审 + 1 份精简 Plan + 独立评审 + 最小脚本与独立手算/上游正向测试 + 完成度审计 + 1 次获批离线运行与结果复核（不建完整 Rule 17 收据体系、不建独立 Verifier 或新 Stage）。 | **16 ~ 26 人时**（约 2 ~ 3.5 人日；外部支出 `$0`） | 仅能产出旧开发集上的 `exploratory` 增量判断，**仍不授予交易权限**；且若进入阶段 B 后实测基准自由度超载、近似共线失稳或单事件主导，按 Design 停止条件终止，不改窗重跑。 |

---

## 6. 实际运行命令、退出码、仓外证据目录与工作区核对

- **开始时间（UTC）：** `2026-11-19T15:27:59Z`
- **初版定稿时间（UTC）：** `2026-11-19T15:38:47Z`（耗时约 11 分钟）
- **局部修订时间（UTC）：** `2026-11-20T02:12Z`（按独立审查意见仅修订 P1-01、P1-02 及交付日志单位 P2-01，耗时约 5 分钟；累计远低于半工作日 4 人时预算上限，未读取新数据、未改代码）
- **仓外证据目录：** `/tmp/h1-estimability-preflight-20261119.fCQaTg`
  - 包含：`head_before.txt`、`status_before.txt`、`staged_before.patch`、`unstaged_before.patch`、`identity_check.json`、`commands_log.txt`、`status_after.txt`、`report_sha256.txt`
  - 该目录仅用于本次复核留痕，非持久证据根或机器消费产物。

### 6.1 已执行命令与退出码

| 序号 | 命令概要 | 退出码 | 核对结果 |
| --- | --- | ---: | --- |
| 1 | `date -u`、`git rev-parse HEAD`、`git status --short --untracked-files=all`、检查目标报告不存在 | `0` | `HEAD=7bdb29bfc89155d6b155df6bed61479a496d3da9`；既有 `M 2026-11-12-...` 与 `?? 2026-11-18-...` 完整保留；目标报告不存在 |
| 2 | `shasum -a 256` 计算两份必读讨论文档摘要 | `0` | 已记录至 §2.1 |
| 3 | `mktemp -d /tmp/h1-estimability-preflight-20261119.XXXXXX` 与 `git diff --cached/--name-status` | `0` | 创建 `/tmp/h1-estimability-preflight-20261119.fCQaTg`；暂存区为空 |
| 4 | 源码静态检索（`grep` + 只读查看 J-A/J-B/TakerBuyShare/OI/Incremental 源码与 Design/Plan 消费条款） | `0` | 确认 J-A/J-B 冻结下游消费门禁及既有 `is_buyer_maker` 计算与复用边界（注：首个 `grep consumer_admission_allowed` 无匹配返回 `1`，随后按 `authority_flags` 与 Design 文本查清全部条款返回 `0`） |
| 5 | Python 静态文件存在性、非符号链接与 SHA-256 核对（19 + 6 = 25 项上游文件与源码，结果落盘 `identity_check.json`） | `0` | 全部 11 项冻结预期 SHA-256 `MATCH`，其余关键源码/配置摘要已记录 |
| 6 | AST 静态检查 `configs/base.py:RISK_LIVE_TRADING_ENABLED` 及定位仓内 `taker` 相关文档 | `0` | `RISK_LIVE_TRADING_ENABLED = False`；仓内无已归档的 taker_buy_share 运行报告 |
| 7 | 保存执行前基线快照至 `/tmp/h1-estimability-preflight-20261119.fCQaTg/` | `0` | `head_before.txt`、`status_before.txt`、`staged_before.patch`、`unstaged_before.patch` 已保存 |
| 8 | 落盘初版报告后核对工作区前后差异、两份必读文档摘要未变及报告 SHA-256 | `0` | 初版仅新增本报告，既有修改与未跟踪文件原封不动，零源码/配置/上游改动 |
| 9 | 局部修订（P1-01 真实调用链与重验边界、P1-02 候选低维设想口径、P2-01 摘要窗口与日志字节/字符单位修正）后复核 `git diff --check`、工作区前后差异与最新报告 SHA-256（留痕于 `commands_log.txt`、`status_after.txt`、`report_sha256.txt`） | `0`（见回复与留痕文件） | 仅更新本报告与仓外日志，未读取新数据、未改代码 |

### 6.2 明确未执行的禁止项确认

- 未修改任何源码、测试、配置、现有文档、上游收据或归档；
- 未联网、未下载、未补样、未执行 SSH/VPS 操作、未影响现有采集；
- 未执行 `git add`、`git commit`、`git push` 或部署；
- 未调用 J-A/J-B strict loader，未读取受限原始 ZIP 成交记录；
- 未计算任何未来收益、MAE/MFE、收益排名、相关性显著性或预测效果；
- 未训练模型、未拟合冲击系数、未参数寻优或置乱实验；
- 未创建正式 Stage、机器消费链、扫描器、收据生成器或完整 Rule 17 框架；
- `RISK_LIVE_TRADING_ENABLED` 保持 `False`，所有 `signal/paper/live/execution` 权限不变。

---

## 7. 路径 B 执行方案与待授权清单（仅准备，未执行真实读取）

> **本节状态：** 路径 B 单次只读预审执行包准备完毕，**本轮未调用任何真实数据 strict loader、未解析真实分类账本明细、未打开任何真实市场 ZIP**。交付后即停止，等待独立复核与用户精确授权。

### 7.1 完整冻结身份清单（执行前强制静态逐项精确比对）

| 类别 | 路径 / 标识 | 实测字节数 | 冻结 SHA-256 / 值 | 状态 |
| --- | --- | ---: | --- | --- |
| 仓库基线 `HEAD` | `git rev-parse HEAD` | — | `7bdb29bfc89155d6b155df6bed61479a496d3da9` | 已核对 |
| J-A 替换根 | `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z` | 目录 | `run_id = stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z` | 存在、非软链 |
| J-A `manifest.json` | `<J_A_ROOT>/manifest.json` | `122,878` | `b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf` | `MATCH`（非软链） |
| J-A `summary.json` | `<J_A_ROOT>/summary.json` | `602,901` | `722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b` | `MATCH`（非软链） |
| J-A `request_journal.jsonl` | `<J_A_ROOT>/request_journal.jsonl` | `448,205` | `b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa` | `MATCH`（非软链） |
| J-A `review_CN.md` | `<J_A_ROOT>/review_CN.md` | `40,462` | `1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152` | `MATCH`（非软链） |
| J-A Rule 17 v2 闭环证据 | `.git/plan-execution/governance_artifact_schema/ba362f2480c7872d39eede9254744d6e99216aa73134777658f9f81f05ba7881/evidence/v2_receipt_closure_evidence.json` | `3,010` | `c0810b95dc94c740dbc41d55ce01d51d1bd7a09e382b292e156d2522d621e68b` | `MATCH`（非软链） |
| J-A 闭环证据 sidecar | `.../v2_receipt_closure_evidence.json.sha256` | `99` | `70948a929538ac32928e8032de5a7c9ac1e35b5af462486ea9b7ca3f2f120649` | `MATCH`（非软链） |
| V2 分类账本 | `data/exports/stage1_5j_token_launch_classification_ledger_v2.csv` | `133,000` | `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b` | `MATCH`（非软链） |
| 共享风控配置 | `configs/base.py` | `91,045` | `ffbc2129a206d3ff7c0a039f10fabc6446a52c9f85c9a869975821b9c0d87079`（`RISK_LIVE_TRADING_ENABLED=False`） | `MATCH`（非软链） |
| J-B 离线常量配置（锚点上限来源） | `configs/stage1_5j_b_historical_aggtrades_launch_response.py` | `565` | `771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4` | `MATCH`（非软链） |
| J-A 核心模块 | `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py` | `105,207` | `250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18` | `MATCH`（非软链） |
| J-B 核心模块（仅复用纯函数） | `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py` | `93,090` | `b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f` | `MATCH`（非软链） |
| 主动买入占比模块（仅复用流式准入） | `src/research/external_signal_shadow/launch_taker_buy_share_residual_response.py` | `98,734` | `ef126ceb83f978f231271a39b091b670ae2e7e7054021230ac3edad29b9a41df` | `MATCH`（非软链） |
| OI/基差模块（仅复用有界行流） | `src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py` | `161,584` | `ed9d68767d56f884f13b02cb5d323a602b8595518dc4c108577ee9092f5426be` | `MATCH`（非软链） |
| 适用上游契约文档 | `docs/designs/2026-10-05-...stage1-5j-a-...design_CN.md` / `2026-10-11-governance-stage1-5j-a-...v2-design-delta_CN.md` | `33,401` / `22,928` | `b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a` / `1d3155c8a38e53f851aaa0f51c8c2ec6ef6aaaf811e4330d8b1c0a491796a86b` | `MATCH` |

### 7.2 实际调用链、附带读取范围与两阶段职责边界

**严格分离“阶段 I：J-A 全根完整性校验”与“阶段 II：`standard crypto` 特征窗统计”，且全程零 J-B 收据消费：**

1. **前置门禁（零受限数据读取）**：
   - `verify_path_b_authorization_packet`：校验用户签发的单次授权 JSON（22 个精确键、`operation == "h1_path_b_estimability_preflight_read_only_once"`、脚本磁盘字节 SHA-256、全部 8 项禁止权限必须为 `false`、`RISK_LIVE_TRADING_ENABLED is False`）；调用 `verify_actual_git_head` 读取仓库**实际 `git rev-parse HEAD`** 并强制比对 `7bdb29bf...`（且执行结束写盘前后再次核对实际 `HEAD`）；调用 `verify_fresh_out_of_repo_output_dir` 强制要求输出目录**尚不存在、非符号链接、父目录存在且解析后严格位于仓库外**。
   - `verify_static_path_b_identities`：校验上表全部 13 项冻结文件存在、无符号链接、SHA-256 精确匹配，并核验 J-A `v2_receipt_closure_evidence.json.sha256` sidecar 与 `profile_id == "stage1_5j_a_receipt_v2"` / `profile_contract_version == 2` / `governance_rule17_v2_positive is True`。
2. **阶段 I — J-A 全根完整性校验（附带全根读取，零收益重放）**：
   - 调用 `load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)`（`stage1_5j_a_...py:1341`，仅在门禁通过后延迟导入）。
   - **明确披露附带读取范围**：为满足“不得跳过 strict loader”的上游完整性契约，J-A strict loader 会读取并重放 J-A 全根（`manifest.json`、`summary.json`、`request_journal.jsonl`、`review_CN.md`、`raw/catalog_scan_a/*.json`、`raw/catalog_scan_b/*.json`、`raw/article_details/*.json` 以及 `raw/archive/` 下全部 280 个 ZIP/`.CHECKSUM` 包的校验和、ZIP 上界与 post-launch 行计数）。
   - **边界清晰**：此阶段仅用于证明 J-A 上游收据树与归档包完整未篡改，**不计算任何价格收益、路径极值或 H1 统计量**；且**不导入、不调用** `load_verified_stage1_5j_b_historical_aggtrades_launch_response_root`，**不读取** `data/external_signal_shadow/stage1_5j_b/**`。
3. **阶段 II-A — 不依赖 J-B 的 V2 账本对账与 `standard crypto` 筛选**：
   - 调用 `reconcile_v2_ledger_against_ja_summary`：
     - **零 J-B 对账**：直接从 `ja_summary["parent_records"]` 提取全部 `child_scope == "in_scope_usdt"` 的 `(source_article_id, symbol)` 键集合及对应的 `symbol_launch_time_ms`、`parent_state`、`detail_status`，与 V2 账本 12 列 CSV 做全集精确双射（缺失或多余任意 1 键即 `STOP=ledger_ja_bijection_mismatch`）。
     - **独立 `standard crypto` 筛选**：按 `asset_class == "crypto" and listing_regime == "standard" and classification_status == "confirmed"` 筛选（遇 `asset_class == "crypto"` 但 `classification_status != "confirmed"` 则 fail-closed `STOP=ledger_unconfirmed_crypto`；**不硬编码 `71`、`53` 或 `41`**）。
     - **公告正文 AST 重证**：对每条入选 `standard crypto` 记录，核验 `raw/article_details/{pid}.json` 路径无软链、SHA 与 J-A `manifest.json` 及账本 `source_sha256` 三方一致、标题不含 `pre-market` / `pre-ipo`（确认 `standard`），并在正文 AST 表格中精确核对 `table_index`、`symbol_column_index`、`field_header`、`raw_cell_value` 与 `evidence_locator`。
4. **阶段 II-B — 仅 `standard crypto` 的流式特征窗统计与未来标签覆盖计数**：
   - 仅对筛选出的 `standard crypto` child，通过 `build_admitted_ja_context` + `open_verified_package_stream`（内置 `validate_zip_archive_package` 与 `65_536` 字节流块上限）+ `stream_aggtrades_csv_lines` + `validate_aggtrades_csv_header` 按所需 UTC 日期（`required_utc_dates_for_window`）以 $O(1)$ 内存流式读取。
   - **纯锚点函数复用、规则来源与接口适配**：
     - 复用函数：`stage1_5j_b_historical_aggtrades_launch_response.py:764` 的纯函数 `select_launch_anchor_trade`（导入该模块仅触发 `_verify_stage_config()` 核验 `configs/stage1_5j_b_...py` 565 字节 SHA 与 `RISK_LIVE_TRADING_ENABLED is False`，**不读取任何 J-B 收据或归档**）。
     - 锚点规则来源：物理顺序中首笔满足 `transact_time >= symbol_launch_time_ms` 且 `transact_time - symbol_launch_time_ms <= EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS`（`300_000` ms），源自 J-B Design §3.2 与冻结配置 `configs/stage1_5j_b_historical_aggtrades_launch_response.py`（SHA `771e6e44...`）。
     - 接口适配说明：原生 `select_launch_anchor_trade` 形参标注为 `trades: list[dict[str, Any]]`，内部仅执行单遍 `for t in trades:` 并在首笔 `ts >= symbol_launch_time_ms` 处立即返回；本脚本用 `select_anchor_via_canonical_helper` 将 $O(1)$ 内存流式生成器适配传入，配合 `saw_post_launch` 标志精确区分 `anchor_delay_exceeded` 与 `anchor_no_post_launch_trade`，并将命中的首笔锚点成交重新送入 `buf` 累积器（避免全量加载或漏计首笔）。
   - **窗口定义（与 §3.1 严格一致，零收益择优搜索）**：
     - **`S1`**：缓冲 `[T0, T0+5m)`、`W1 = [T0+5m, T0+15m)`、`W2 = [T0+15m, T0+25m)`、未来标签窗 `[T0+25m, T0+40m]`；
     - **`S2`**：缓冲 `[T0, T0+15m)`、`W1 = [T0+15m, T0+35m)`、`W2 = [T0+35m, T0+55m)`、未来标签窗 `[T0+55m, T0+70m]`。
   - **严格限定的统计内容**：
     - `buf`、`W1`、`W2` 内以精确 `Fraction` 仅统计：活跃度（`trade_count`、`total_notional`、`buy_notional`、`sell_notional`、`net_flow`）、连续性与边界空档（`first_ts`、`last_ts`、`leading_gap_ms`、`trailing_gap_ms`、`max_intertrade_gap_ms`、`sequence_gap_count`、`sparse_trade_flag`）、成交方向（`taker_buy_share`、`taker_sell_share`、`normalized_imbalance`、`normalized_net_sell_pressure`）及跨窗卖压可比性（`is_sustained_net_sell`、`activity_decay_ratio = V_w2/V_w1`、`rel_net_sell_w1 = -Q_w1/V_buf`、`rel_net_sell_w2 = -Q_w2/V_buf`、`sell_pressure_retention_ratio = (-Q_w2)/(-Q_w1)`）。
     - 未来标签窗 `[T0+w2_end, T0+label_end]` 由 `LabelCoverageAccumulator.add_timestamp_only(ts)` 处理，**代码级不读取、不传递、不存储 `price` 与 `quantity`**，仅输出 `label_has_records`（**仅声明窗口内存在记录，不等同于端点覆盖完成**）、`label_trade_count`、`label_sparse_trade_flag`、`label_first_ts`、`label_last_ts`、`label_leading_gap_ms`、`label_trailing_gap_ms`、`label_max_intertrade_gap_ms` 及 `label_endpoint_rule_status = "undefined_in_preflight"`。
     - **独占输出与零覆盖**：写盘通过 `write_exclusive_out_of_repo_json` 要求全新目录 `os.mkdir(..., 0o700)` 并以 `os.open(..., O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0o600)` 独占创建输出 JSON，遇已有目录/文件或任何符号链接立即 `STOP`，杜绝写穿符号链接覆盖输入或仓内文件。
     - **全程零收益计算**：不计算任何未来收益、MAE/MFE、收益排名、相关性显著性或拟合任何模型。

### 7.3 缺口分类、Parent 分母守恒与异常/边界处理规则

1. **互斥 child 状态（零隐式剔除，全量入表；严禁把“存在记录”提升为“已确认可估计”）**：
   - `j_a_parent_or_detail_gap`（`j_a_parent_state != "coverage_complete"` 或缺 `symbol_launch_time_ms`）
   - `j_a_archive_package_missing_or_unverified`（锚点搜索日或 `[T0, T0+label_end]` 所需 UTC 日期包在 J-A 中缺失或非 `archive_verified_with_post_launch_rows`）
   - `anchor_no_post_launch_trade` / `anchor_delay_exceeded`
   - `sequence_gap`（`[T0, T0+label_end]` 内存在任意 `agg_trade_id != prev_agg_trade_id + 1`，保留分母并记录 `sequence_gap_count`）
   - `feature_window_empty_or_zero_notional`（`buf`、`W1` 或 `W2` 任一为空或 `total_notional == 0`）
   - `future_label_no_records`（未来标签窗内 `label_trade_count == 0`）
   - `records_present_estimability_unconfirmed`（**仅表示各特征子窗与未来标签窗均至少存在记录且无 `sequence_gap`，绝不宣称端点规则满足、窗口覆盖完整或已确认可估计**；同步输出 `estimability_status = "unknown_pending_design_criteria"`、`any_feature_or_label_sparse` 及各子窗与标签窗的 `leading_gap_ms`/`trailing_gap_ms`，且**不擅自增设成交量、笔数或间隔阈值**）
2. **Parent 分母守恒（独立统计单元 `parent_article_id`）**：
   - `summarize_window_denominator_conservation` 强制校验两项恒等式（违背即 fail-closed `STOP`）：
     - `n_children_total == sum(child_status_counts.values())`
     - `n_parents_total == n_parents_all_children_records_present + n_parents_partial_gap + n_parents_all_gap`
   - 同步输出：`n_parents_confirmed_estimable = null`（`estimability_confirmation_status = "unknown_pending_endpoint_and_design_criteria"`，端点规则与可估计条件未定义前绝不计入已确认可估计数）、`n_parents_all_records_present_with_any_sparse_window`、多 child Parent 计数（`n_parents_multi_child`）、同 UTC 日多 Parent 聚类（`same_utc_date_multi_parent_clusters`）及全 child 存在记录且含持续净卖压的 Parent 数。
3. **零分母、稀疏成交、序列缺口与身份错误处理**：
   - **零分母**：`total_notional == 0` 时所有占比/失衡/衰减比/相对卖压均输出 `null` 并置显式 `zero_denominator_flags`，绝不除零或代填 `0`；非持续净卖压（`Q_w1 >= 0` 或 `Q_w2 >= 0`）时 `sell_pressure_retention_ratio = null`。
   - **稀疏成交**：显式记录 `trade_count`、`sparse_trade_flag = (trade_count < 2)`、`leading_gap_ms`/`trailing_gap_ms`；`trade_count < 2` 时 `max_intertrade_gap_ms = null`，不隐式丢弃事件，也不设主观筛选门槛。
   - **序列缺口与顺序错乱**：ID 跳跃记入 `sequence_gap`；时间戳倒退（`ts < prev_ts`）或 ID 重复/倒退（`tid <= prev_id`）直接 fail-closed `STOP=trade_sequence_order_violation`。
   - **身份/授权/输出/格式错误**：任何实际 `git HEAD` 失配（执行前及执行后）、文件缺失/软链/SHA 失配、授权键/标志错误、已有输出目录或符号链接输出目标、账本双射失配或 CSV 列/类型错误，均立即抛出 `PathBPreflightError("STOP=...")`、非零退出且不覆盖任何既有文件。

### 7.4 仓外执行包产物、手算合成验证结果、拟执行命令与停止条件

- **仓外脚本与验证文件（均位于仓库外部，仓库零缓存/零代码改动）**：
  - 一次性执行脚本：`/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/run_h1_path_b_estimability_preflight.py`
    - SHA-256：`085ab4c224965f8f1c541c3f0756a0d48f9c1552da2bcf6c8424726cf1d263fe`
  - 合成手算验证脚本：`/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/test_h1_path_b_synthetic.py`
    - SHA-256：`8ca6bc5348aa628a8f1fb0bb6c4035fdb774f17e0e9563b7d19ba4c4b2823e08`
  - 待用户签发的授权 JSON 拟放路径：`/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/path_b_authorization.json`（**当前不存在；未获批不得创建或运行**）
  - 获批后仓外输出目录：`/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_run_output`（要求为全新非符号链接目录，产出独占创建的 `path_b_estimability_summary.json`）
- **手算合成逻辑验证结果（仅使用独立手算合成样本，零真实数据读取，`PYTHONDONTWRITEBYTECODE=1 python3 -B`，8/8 全部 `PASS`，`RC=0`）**：
  1. `test_01_hand_calculated_direction_s1_boundaries_and_label_price_isolation`：手算核对 `is_buyer_maker` 方向、`S1` 精确半开/闭区间边界与边界空档、`Fraction` 占比/失衡/衰减比/相对卖压/卖压保持比，并将未来标签窗 `price`/`quantity` 置 `None` 证明代码级不读取未来价格。
  2. `test_02_s2_boundaries_and_anchor_delay_edges`：核对 `S2` 精确边界、单笔稀疏成交 `sparse_trade_flag=True` & `max_intertrade_gap_ms=None`、净买压下 `is_sustained_net_sell=False` & `sell_retention=None`、锚点 `300_000ms` 通过 / `300_001ms` 判 `anchor_delay_exceeded` / 无上市后成交判 `anchor_no_post_launch_trade`。
  3. `test_03_zero_denominator_empty_subwindow_and_label_no_records`：核对空 `W1`、零名义额 `buf`（`price=0`）与空未来标签窗（`future_label_no_records`）均无除零异常且正确置 `zero_denominator_flags`。
  4. `test_04_sequence_gap_and_ordering_violations`：核对 `agg_trade_id` 跳号判 `sequence_gap`（保留分母），重复 ID 与时间倒退均触发 `STOP=trade_sequence_order_violation`。
  5. `test_05_ja_only_ledger_reconciliation_and_parent_conservation`：以纯合成 J-A `parent_records`/manifest/detail/V2 CSV 验证零 J-B 双射对账、`standard crypto` 筛选、SHA/双射/regime 失配 fail-closed `STOP`，以及多 child Parent 与同日聚类的分母守恒与 `n_parents_confirmed_estimable is None`。
  6. `test_06_pb_p1_01_actual_git_head_and_auth_gate_fail_closed`（**PB-P1-01 回归**）：在 `/tmp` 创建独立提交不同的临时 git 仓库验证触发 `STOP=git_head_mismatch`，非 git 目录触发 `STOP=git_head_check_failed`，任意禁止标志为 `true` 均 fail-closed `STOP`。
  7. `test_07_pb_p1_02_fresh_dir_and_exclusive_non_symlink_output`（**PB-P1-02 回归**）：验证已有目录、符号链接目录、指向仓内的父级符号链接及指向目标文件的符号链接输出均触发 `STOP` 且目标文件零改动，全新仓外目录独占写入成功。
  8. `test_08_pb_p1_03_auditor_sparse_counterexample_not_marked_estimable`（**PB-P1-03 回归**）：精确复现审查反例（`buf`/`W1`/`W2` 各 1 笔、未来标签窗仅第 25 分钟 1 笔距第 40 分钟差 15 分钟），验证输出 `records_present_estimability_unconfirmed`、`label_trailing_gap_ms == 900_000`、`label_endpoint_rule_status == "undefined_in_preflight"`、`n_parents_confirmed_estimable is None`、`n_parents_all_records_present_with_any_sparse_window == 1`。
- **获批后拟执行命令（本轮未运行）**：
  ```bash
  PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/run_h1_path_b_estimability_preflight.py \
    --auth-file /tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/path_b_authorization.json \
    --output-dir /tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_run_output \
    --project-root /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
  ```
- **执行期停止条件**：
  1. 任意实际 `HEAD`、冻结身份、授权字段、输出目录/文件防覆盖、J-A strict loader、V2 账本双射/AST 或成交顺序校验返回 `STOP=...` → 立即终止、报告精确根因，不绕过或降级；
  2. 累计投入达到原 **4.00 人时**上限 → 立即交付现状与已取得事实，不自动延期、不补抓数据；
  3. 若实测 `S1`/`S2` 满足可比持续净卖压的有效独立 `standard` Parent 过稀、或 `sequence_gap`/活跃度坍塌/边界空档严重 → 如实交付数据事实并建议暂停，不换窗搜索收益、不削弱对照。

### 7.5 预算核算（计入已发生投入，区分墙钟记录与估算，不自动追加半个工作日）

沿用 [讨论备忘 §6.4](2026-11-12-launch-event-data-research-directions-discussion_CN.md#64-vcp-与跨领域讨论后的取舍及下一步2026-11-19) 的**总预算上限 4.00 人时（半个工作日）**，严格区分墙钟记录与估算口径，**不未经依据扣减等待时间并自称实测，也不重新起算或自动追加半个工作日**：

| 环节 | 时间记录（UTC） | 计量口径 | 消耗（人时） | 说明 |
| --- | --- | --- | ---: | --- |
| 1. 初版非受限预审、源码/身份核对与报告撰写 | 2026-11-19 `15:27:59Z → 15:39:31Z`（11.5 分钟） | 墙钟记录 | `0.19` | 已发生 |
| 2. 独立审查后局部修订（P1-01/P1-02/P2-01） | 2026-11-20 `02:07:48Z → 02:12:36Z`（4.8 分钟） | 墙钟记录 | `0.08` | 已发生 |
| 3. 路径 B 执行包准备、手算合成验证与报告追加 | 2026-11-20 `02:25:14Z → 03:27:50Z`（62.6 分钟） | 墙钟记录（含工具/生成等待，全额计入） | `1.04` | 已发生（PB-P2-01 修正：原表 `0.35` 未提供扣减依据，现按完整 62.6 分钟墙钟全额计入） |
| 4. 本轮定向返修（PB-P1-01/02/03 & PB-P2-01） | 2026-11-20 `03:41Z` 启动遇流中断，`06:41Z → 06:48Z` 恢复完成 | **估算**（不含 3 小时流中断空白，不冒称实测） | `0.25` | 已发生估算（实际编辑与 8 项回归约 15 分钟） |
| **已发生执行投入小计（不含外部审查员与用户耗时）** | 墙钟 `1.31` + 估算 `0.25` | 墙钟 + 估算合计 | **`1.56`** | 若叠加前两轮独立审查/用户阅读协作**估算**（约 `0.44` 人时），保守累计估算约 **`2.00` 人时** |
| **原 4.00 人时上限内剩余预算** | `4.00 - 1.56`（保守含协作：`4.00 - 2.00`） | 按上限扣减 | **`2.00 ~ 2.44`** | **不自动追加预算** |
| 5. 获批后单次路径 B 只读运行、回填 §3.2 实测表与定向复核 | 预计 | **估算** | **`1.50 ~ 2.00`** | 外部支出 `$0`；可落在剩余 `2.00 ~ 2.44` 人时内。若选择走需完整独立评审的“方案 2：独立极简准入 Design”，须在总上限 `4.00` 人时内一并计入并从严控时，到点即交付现状 |

### 7.6 新 Consumer 治理准入形式与精确契约依据（待用户裁决，本轮不自行豁免）

**适用契约条款（路径 B 不消费 J-B 收据，故不触发 J-B Design L295；但仍严格受以下 J-A 与 V2 账本条款约束）：**
1. **J-A Design（`b74c306e...`）§2 L65**：`No other file, permission, lifecycle owner, downstream consumer or public production entrypoint is authorized by this Design.`
2. **J-A Design §6 `INV-15J-A-10`（L287）**：`J-A makes no PIT, price, cost, PnL, Alpha, execution, paper/live or downstream-consumer claim.`
3. **J-A Design §9（L359, L367）**：`Later research needs a separately approved Design for hypothesis, parent-level sample treatment, PIT semantics, price/trade construction, cost evidence, hold/risk rules and independent validation.`；且仅完成闭环审计的收据字节可被后续 consumer 视作已验证。
4. **J-A Profile v2 Delta（`1d3155c8...`）§4.2（L123）、§5.4（L166）、`INV-GSI-V2-07`（L178）、§10（L228）**：Consumer Matrix 未授权除待定 J-B 外的任何新下游 consumer，`v2` 闭环不授予新 consumer 或 replay 权限。
5. **V2 分类账本（`36e56f45...`）与 [讨论备忘 §6.1 L192 & §6.4 L247](2026-11-12-launch-event-data-research-directions-discussion_CN.md#L192)**：账本位于被 Git 忽略的 `data/exports/`，消费前须核验精确 SHA 与 J-A 正文 AST，且不得以“仓外只读脚本”为由跳过上游消费授权。

**两种待用户明确裁决的准入形式（本轮既不自行豁免，也不扩建流程）：**

| 准入方案 | 适用前提与治理地位 | 最小所需动作与内容（不扩建 Rule 17 / 新 Stage） |
| --- | --- | --- |
| **方案 1：用户显式签发“单次书面治理例外”** | **仅作为待用户明确批准的候选方案，绝非默认生效。** 适用于用户认定“本轮仅做一次性离线只读可估计性预审、零收益计算、零仓内代码/持久机器产物、不触发 J-A §9 的策略/收益研究条款”的情形。 | 独立复核通过本执行包后，由用户在回复或仓外 `path_b_authorization.json` 中显式写明：`governance_admission_mode = "user_explicit_written_governance_exception"`，逐项绑定 §7.1 的 `HEAD`、J-A 根/manifest/summary/closure SHA、V2 账本 SHA、脚本路径与 SHA `085ab4c2...`、全新仓外输出目录及全部 8 项 `false` 禁止标志，明确对 J-A Design L65 / Profile v2 Delta §4.2 授予**单次离线只读预审例外**。 |
| **方案 2：独立极简准入 Design** | 若独立复核或用户裁定必须按 J-A Design L65 / §9 及 Profile v2 Delta §4.2 字面要求以正式 Design 登记新 consumer，则走此路径。 | 仅需 1 份精简 Design（约 1 页，**不扩建为策略研究 Design、不建正式 Stage、不建新收据 schema 或 Rule 17 Verifier**），最小内容仅含 5 项：<br>1）目标与非目标（仅离线只读核验 `standard crypto` 在 `S1`/`S2` 特征窗的活跃度、连续性、方向与卖压可比性，零收益/零模型/零交易）；<br>2）§7.1 全部冻结输入与源码 SHA 绑定；<br>3）§7.2 真实调用链（J-A 全根校验 + 零 J-B 收据消费 + 纯锚点函数适配 + 未来窗仅查记录存在与边界空档）；<br>4）§7.3 无 J-B 账本对账、分母守恒与全部 `false` 禁止权限；<br>5）仓外脚本 SHA（`085ab4c2...`）、全新仓外输出目录与人工报告更新边界。经独立 B 审与用户批准后签发 `path_b_authorization.json`（`governance_admission_mode = "approved_minimal_design"`）执行。 |

---

*路径 B 执行包准备完毕，本轮到此停止，不执行真实数据读取，等待独立复核与用户精确授权。*


---

## 8. 获批单次执行结果与 Fail-Closed 停止报告（`H1_PATH_B_READONLY_20261120_01`）

> **执行状态：`STOPPED_FAIL_CLOSED`（`RC=1`）｜结论维持：`evidence_insufficient`**  
> 在调用上游 J-A strict loader 核验冻结收据 `authority_packet` 时触发 fail-closed 停止（`STOP=stage1_5j_a_authority_packet_invalid:disk_sha_mismatch:audited_config`）。按批准书 §四 停止条件，**已立即停止并如实报告；未修改任何代码或配置、未绕过 strict loader、未换目录重跑、未扩大例外**。

### 8.1 批准身份、执行命令、退出码与完整日志

- **批准标识：** `H1_PATH_B_READONLY_20261120_01`（方案 1：`user_explicit_written_governance_exception`）
- **批准前报告版本 SHA-256（保留不变前缀内容）：** `724ddc1a63307ad036402e258f0c3a42b0bd0bc01484589255ef6f206d1e96e7`（追加本节后的最终 SHA-256 见交付回复及 `/tmp/h1-estimability-preflight-20261119.fCQaTg/report_sha256.txt`）
- **实际仓库 `HEAD`（执行前及执行后均核对一致）：** `7bdb29bfc89155d6b155df6bed61479a496d3da9`
- **仓外授权 JSON：** `/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/path_b_authorization.json`
  - SHA-256：`dba30329f163fd58c5f93535fb13f405d452487e388ce9fb8496c5c430c62b80`
- **唯一获准执行脚本：** `/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/run_h1_path_b_estimability_preflight.py`
  - SHA-256：`085ab4c224965f8f1c541c3f0756a0d48f9c1552da2bcf6c8424726cf1d263fe`
- **执行时间（UTC）：** `2026-11-20T07:47:18Z → 2026-11-20T07:47:53Z`
- **实际执行命令：**
  ```bash
  PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/run_h1_path_b_estimability_preflight.py \
    --auth-file /tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/path_b_authorization.json \
    --output-dir /tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_run_output \
    --project-root /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
  ```
- **退出码：** `RC=1`
- **完整执行日志（留痕于 `/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_run_stdout_stderr.log`）：**
  ```text
  Traceback (most recent call last):
    File "/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/run_h1_path_b_estimability_preflight.py", line 1467, in <module>
      raise SystemExit(main())
    File "/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/run_h1_path_b_estimability_preflight.py", line 1457, in main
      out_file = run_authorized_path_b_preflight(
    File "/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_package/run_h1_path_b_estimability_preflight.py", line 1265, in run_authorized_path_b_preflight
      ja_summary = load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)
    File "/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py", line 1345, in load_verified_stage1_5j_a_historical_archive_coverage_root
      return _load_verified_stage1_5j_a_historical_archive_coverage_root_internal(
    File "/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py", line 1447, in _load_verified_stage1_5j_a_historical_archive_coverage_root_internal
      _validate_authority_packet(summary_data, root)
    File "/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py", line 1308, in _validate_authority_packet
      raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_authority_packet_invalid:disk_sha_mismatch:{comp}")
  research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory.Stage1_5JADiagnosticError: STOP=stage1_5j_a_authority_packet_invalid:disk_sha_mismatch:audited_config
  ```

### 8.2 精确根因（经只读源码与 `git log` / `git show` 核证）

1. **前置门禁全部通过**：`verify_path_b_authorization_packet`（含实际 `git HEAD`、全部 22 键与 8 项 `false` 禁止标志、脚本 SHA、全新仓外输出目录检查）与 `verify_static_path_b_identities`（全部 13 项冻结文件 SHA-256、J-A closure sidecar 与 `governance_rule17_v2_positive is True`）均通过。
2. **上游 J-A strict loader 实盘配置校验阻断**：
   - `stage1_5j_a_historical_archive_coverage_inventory.py:1286, 1303–1308` 的 `_validate_authority_packet` 强制要求当前工作区 `configs/base.py` 的磁盘 SHA-256 逐字节等于 J-A `summary.json` 中历史记录的 `authority_packet.audited_config.sha256`；
   - 经只读 `git show 00bac0b:configs/base.py | shasum -a 256` 核实，J-A 生产收据生成时（提交 `00bac0b`）的 `configs/base.py` SHA-256 为 **`473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc`**；
   - 经只读 `git log -n 5 --oneline -- configs/base.py` 与 `git show --stat ea4b314 -- configs/base.py` 核实，2026-11-14 提交 `ea4b314`（`fix(stage1_5): add postponed launch readiness gate, bounded revision recheck, and future-launch recovery`）向 `configs/base.py` 新增 6 行，使当前 `HEAD`（`7bdb29b`）下的 `configs/base.py` SHA-256 变为 **`ffbc2129a206d3ff7c0a039f10fabc6446a52c9f85c9a869975821b9c0d87079`**；
   - 因此，在当前 `HEAD`（`7bdb29b`）上直接调用未修改的 J-A 冻结 strict loader（以及任何内部依赖 J-A strict loader 的 J-B strict loader）必然在 `_validate_authority_packet` 处确定性返回 `STOP=stage1_5j_a_authority_packet_invalid:disk_sha_mismatch:audited_config`。
3. **Rule 16 分类**：此阻断属于 **`BLOCKED_SPEC_DRIFT`（冻结历史收据加载器对实盘 `configs/base.py` 全文件哈希绑定与后续 `Stage 1.5D` 配置演进之间的上游历史收据兼容边界冲突）**，不是脚本编码缺陷，也不得通过绕过 strict loader 或临时回退 `configs/base.py` 解决。

### 8.3 实际读取范围、分母状态与限制（2026-11-20 依据源码执行顺序定向修正）

> **修正说明：** 初版 §8.3 曾称“未打开任何市场 ZIP”，该表述不准确。经只读核对 [stage1_5j_a_historical_archive_coverage_inventory.py:1380-1455](../../src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py) 的真实执行顺序与原失败栈（停在 `L1447 -> L1308`），现准确区分**已发生读取**与**未发生步骤**如下（本修正未重跑 loader，未修改原失败日志与授权原件）：

- **已发生的原始字节/哈希读取**：
  1. 路径 B 前置门禁：读取 `path_b_authorization.json`、13 项冻结文件原始字节并计算 SHA-256，读取 J-A `v2_receipt_closure_evidence.json` 及 `.sha256` sidecar；
  2. J-A strict loader 在调用 `_validate_authority_packet`（`L1447`）**之前**已完成：`manifest.json` 规范性校验（`L1390–1403`）、**遍历 `manifest.json` 全部 708 个登记产物并对每个文件读取原始字节核对 `stat().st_size` 与 `_file_sha256(p)`（`L1406–1417`，其中包含 `raw/archive/` 下的 280 个市场 `.zip` 文件、280 个 `.CHECKSUM`、131 个 `article_details`、14 个 `catalog_scans` 与 3 个顶层收据文件）**、目录树 `rglob("*")` 额外文件检查（`L1420–1422`），以及 `summary.json` 规范字节、键集、`run_id` 与 13 项 `authority_flags` 校验（`L1425–1445`）；随后于 `L1447 -> L1308` 因 `audited_config`（`configs/base.py`）磁盘 SHA 失配立即 fail-closed 停止。
- **尚未发生的上游语义重放**：
  - 未执行 `render_stage1_5j_a_review` 重渲染比对（`L1450`）；
  - 未执行 `request_journal.jsonl` 语义重放（`L1456–1463`）；
  - 未执行 `catalog_scan_a`/`catalog_scan_b` 目录双扫语义重放（`L1466–1525`）；
  - 未执行 `raw/article_details/*.json` 公告正文与冻结 parser 语义重放（`L1528–1549`）。
- **尚未发生的解压、逐笔解析与 H1 统计**：
  - 未执行 `validate_archive_package`（`L1604`），即**未解压任何市场 ZIP、未读取任何 CSV 成交记录或解析任何逐笔交易**；
  - 未解析任何 V2 分类账本（`stage1_5j_token_launch_classification_ledger_v2.csv`）逐行明细；
  - 未执行任何 H1 `S1`/`S2` 窗口统计、未消费 J-B 收据、未计算任何收益或 MAE/MFE。
- **仓外输出目录**：`/tmp/h1-estimability-preflight-20261119.fCQaTg/path_b_run_output` **未创建**（`No such file or directory`），零结果 JSON 写出。
- **Parent / child 分母、缺口、稀疏与边界空档**：全部保持 **`not_executed / unknown`（受阻于上游 J-A strict loader `audited_config` 历史兼容门禁）**；绝不据此宣布 H1 成立或被证伪。
- **`RISK_LIVE_TRADING_ENABLED`**：保持 `False`。

### 8.4 本次预算更新（沿用原 4.00 人时总上限，不追加）

| 环节 | 时间记录（UTC） | 计量口径 | 消耗（人时） |
| --- | --- | --- | ---: |
| 前期累计（环节 1–4，见 §7.5） | — | 墙钟 `1.31` + 估算 `0.25` | `1.56`（含外部审查/协作保守估算约 `2.00`） |
| 5. 本次获批单次执行、根因取证与停机报告追加 | 2026-11-20 `07:47:18Z → 07:50:xxZ`（约 3 分钟） | 墙钟记录 | `0.05` |
| **最新累计执行投入** | — | 墙钟 + 估算合计 | **`1.61`**（含协作保守估算约 **`2.05`**） |
| **原 4.00 人时总上限内剩余预算** | `4.00 - (1.61 ~ 2.05)` | 按上限扣减 | **`1.95 ~ 2.39`**（不自动追加） |

### 8.5 供独立审核与用户决策的下一步路由（本轮不自行推进）

1. **选项 A（低成本暂缓 — 推荐先评估投入产出比）**：在当前 `HEAD` 上解开 J-A 历史收据 strict loader 对 `configs/base.py` 演进的兼容阻断，本身就需要额外的上游治理兼容裁决（类似历史 J-B 兼容 Delta）；叠加旧 `standard` 开发集已反复暴露、后续独立新样本稀少，用户可直接选择**暂缓 H1**，避免仅为探索预审额外投入治理工程。
2. **选项 B（若仍坚持读取旧 `standard` 实测分母）**：按 L1 Rule 16 `BLOCKED_SPEC_DRIFT` 路由，由用户与独立审核先专门裁决合法的上游历史收据兼容路径（例如：起草针对 J-A 历史收据 `audited_config` 只读兼容的最小治理 Design Delta，或在独立治理批准下界定历史提交只读核验方式），再签发新的单次授权；**严禁绕过 strict loader、严禁私改 `configs/base.py` 或 J-A 核心源码**。


---

## 9. 隔离历史环境限定方案（待批准，本轮仅调查准备、未创建环境或执行读取）

> **本节结论：`可提交限定执行审批`（附紧预算预警，不代表真实 loader 已通过，也不代表 H1 成立）。**  
> 经只读核对历史候选提交 `2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`（`2026-11-13 15:25:15 +0800`，早于 `ea4b314` 对 `configs/base.py` 的改动）及本地未跟踪原件，J-A `authority_packet` 全 7 项组件、闭环证据、V2 分类账本及 4 个路径 B 复用模块/配置**全部齐备且 SHA-256 精确匹配（零缺失项）**，且无须修改任何冻结 strict loader、上游收据或主工作区配置。但须明确两点限制：1）原脚本因硬编码主仓 `sys.path` 及主仓 `configs/base.py` 哈希，不能直接复用，须新建仓外隔离适配脚本并另签全新授权；2）原 `4.00` 人时总预算剩余余量较窄，执行与复核须严格一次性收口，触及上限即暂停。

### 9.1 历史身份齐备性核对（候选提交 `2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`）

核对方法：对 Git 跟踪组件使用 `git show 2f9ba8e04821c3d7a477a65f2b73e34cb6beb442:<path>` 只读计算字节 SHA-256，与 J-A `summary.json` 的 `authority_packet` 期望值比对；对 Git 未包含的历史授权与闭环证据原件仅核对本地磁盘存在性、非符号链接与 SHA-256（**未运行 loader、未解压市场 ZIP、未解析 V2 账本明细**）。

| 组件类别与名称 | 相对路径 | 期望 SHA-256（J-A `authority_packet` / 冻结契约） | 来源类型 | 在 `2f9ba8e0` / 磁盘核对结果 |
| --- | --- | --- | --- | --- |
| J-A `approved_design` | `docs/designs/2026-10-09-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-design-delta_CN.md` | `f427df9435c8b9c8dd2b4b45c24bbbbd595df2c7e8d209f40f6fe2cd13b00f3c` | Git 可恢复 | `in_git=True` / `MATCH`（18,391 B） |
| J-A `approved_plan` | `docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan-r1_CN.md` | `b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82` | Git 可恢复 | `in_git=True` / `MATCH`（36,474 B） |
| J-A `audited_cli` | `scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py` | `ed4d1d9f8d4efe916186a4e64c0cb94188115e67d8251679811d2a02c133c417` | Git 可恢复 | `in_git=True` / `MATCH`（3,292 B） |
| J-A `audited_config` | `configs/base.py` | `473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc` | Git 可恢复 | **`in_git=True` / `MATCH`**；AST 核对 `RISK_LIVE_TRADING_ENABLED=False`（当前工作区为 `ffbc2129...`，不匹配） |
| J-A `audited_core` | `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py` | `250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18` | Git 可恢复 | `in_git=True` / `MATCH`（105,207 B） |
| J-A `frozen_parser` | `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py` | `7e0e696647acf158facbdd8d3d39351bbc68c33b039871f26f4a38bc75ad56e5` | Git 可恢复 | `in_git=True` / `MATCH`（40,042 B） |
| J-A `network_authorization` 原件 | `.git/plan-execution/stage1_5j_a/b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82/network_authorization.txt` | `3a4c31cb12e6a16e9b9a8afc0a8169761d276f6bd17568481bbad20577a298fe` | **Git 不包含（本地原件）** | `on_disk=True` / 非软链 / `MATCH`（778 B）；**仅作历史来源证据，不构成本次联网权限** |
| J-A `network_authorization` sidecar | `.../stage1_5j_a/b578ab6b.../network_authorization.sha256` | 正文首段 `3a4c31cb...  network_authorization.txt\n` | **Git 不包含（本地原件）** | `on_disk=True` / 非软链 / 摘要 `35fae050...`（92 B），文本精确匹配原件 SHA |
| J-A Rule 17 v2 闭环证据 + sidecar | `.git/plan-execution/governance_artifact_schema/ba362f24.../evidence/v2_receipt_closure_evidence.json`（及 `.sha256`） | `c0810b95dc94c740dbc41d55ce01d51d1bd7a09e382b292e156d2522d621e68b` / `70948a92...` | **Git 不包含（本地原件）** | `on_disk=True` / 非软链 / 双双 `MATCH`（3,010 B / 99 B） |
| V2 分类账本 | `data/exports/stage1_5j_token_launch_classification_ledger_v2.csv` | `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b` | **Git 不包含（本地原件）** | `on_disk=True` / 非软链 / `MATCH`（133,000 B） |
| 路径 B 复用常量与模块（4 项） | `configs/stage1_5j_b_...py`、`stage1_5j_b_...py`、`launch_taker_buy_share_...py`、`launch_open_interest_basis_...py` | `771e6e44...` / `b2ca8e28...` / `ef126ceb...` / `ed9d6876...` | Git 可恢复 | 4 项在 `2f9ba8e0` **全部 `in_git=True` / `MATCH`**，与当前 `HEAD` 逐字节一致 |
| Python 包初始化文件 | `src/__init__.py`、`src/research/__init__.py`、`src/research/external_signal_shadow/__init__.py`、`configs/__init__.py` | — | Git 可恢复 | 4 项在 `2f9ba8e0` 全部存在 |

- **缺失项清单：** **无（0 项缺失）**。不制造替代证明，不重新绑定旧网络授权。

### 9.2 真正隔离方案、目录布局、只读保护与磁盘估算

1. **为什么禁止使用 `git worktree add`**：
   - J-A strict loader 的 `_validate_authority_packet`（`stage1_5j_a_...py:1325`）硬编码路径 `<project_root>/.git/plan-execution/stage1_5j_a/b578ab6b.../network_authorization.txt`。
   - 在 `git worktree` 中，`<worktree>/.git` 是普通文本指针文件而非目录，根本无法在 `<worktree>/.git/plan-execution/...` 下存放文件。
   - 因此，隔离历史快照**必须使用独立克隆目录**（`git clone --local --no-checkout --no-hardlinks /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab <ISOLATED_REPO>` + `git -C <ISOLATED_REPO> checkout --detach 2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`），使 `<ISOLATED_REPO>/.git/` 成为独立真实目录、不与主仓共享对象硬链或 `.git` 指针，并原生支持 `git rev-parse HEAD == 2f9ba8e0...`。
2. **拟定隔离目录布局（消除 macOS `/tmp` 软链歧义，本轮未创建）**：
   - 使用物理无软链根路径 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/`：
     - `repo_2f9ba8e0/`：独立历史快照仓（`HEAD = 2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`）；
     - `repo_2f9ba8e0/data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/`：从主仓只读深拷贝（普通文件逐字节复制，**禁用软链与硬链**）J-A 替换根 709 个文件；
     - `repo_2f9ba8e0/data/exports/stage1_5j_token_launch_classification_ledger_v2.csv`：普通文件深拷贝；
     - `repo_2f9ba8e0/.git/plan-execution/stage1_5j_a/b578ab6b.../network_authorization.txt` 及 `.sha256`：普通文件深拷贝（仅作历史来源证据，不授予联网权限）；
     - `repo_2f9ba8e0/.git/plan-execution/governance_artifact_schema/ba362f24.../evidence/v2_receipt_closure_evidence.json` 及 `.sha256`：普通文件深拷贝；
     - `runner_pkg/`：全新仓外适配脚本与新授权 JSON；
     - `run_output/`：全新仓外输出目录（执行前不存在，独占非符号链接写入）。
3. **只读输入保护与隔离声明**：
   - 拷贝后先核对副本与原件 SHA-256 逐一匹配，再对 `repo_2f9ba8e0/{configs,src,scripts,docs,data,.git/plan-execution}` 执行 `chmod -R a-w` 只读锁护；
   - 不回退当前主工作区、不改生产配置、不使用任何软链接绕过检查、绝不将隔离副本宣称为新生产收据。
4. **磁盘与复制成本估算（仅据 J-A `manifest.json` 元数据计算，本轮未复制）**：
   - J-A `manifest.json` 登记产物共 **708 个文件 / `778,366,520` 字节（`742.31 MiB`）**，加 `manifest.json`（`122,878` B）合计 **`778,489,398` 字节（`742.43 MiB`）**：
     - `raw_archive_zip`：280 个 / `763,017,036` B（`727.67 MiB`）；
     - `raw_archive_checksum`：280 个 / `28,016` B（`0.03 MiB`）；
     - `raw_article_details`：131 个 / `13,515,668` B（`12.89 MiB`）；
     - `raw_catalog_scans`：14 个 / `714,232` B（`0.68 MiB`）；
     - 顶层收据（`summary.json` / `request_journal.jsonl` / `review_CN.md`）：3 个 / `1,091,568` B（`1.04 MiB`）。
   - 叠加独立克隆仓与 5 个未跟踪原件（约 137 KiB），整个隔离副本总磁盘占用预计 `< 1.0 GiB`；实测 `/private/tmp` 剩余可用空间 **`219.04 GiB`**（`235,197,394,944` 字节），本地 SSD 复制预计耗时 `< 10 秒`。

### 9.3 模块导入、公开入口接线与必要仓外适配差异

**为什么不能简单说“设置 `PYTHONPATH` 即可”——现有脚本与上游源码存在 5 处具体接线约束：**

1. **现有 runner 的 `sys.path.insert(0, ...)` 会强行覆盖 `PYTHONPATH`**：
   - 现有 `/tmp/.../run_h1_path_b_estimability_preflight.py`（L43–47）硬编码 `DEFAULT_PROJECT_ROOT = Path("/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab")` 并在模块顶层将其及 `.../src` 插入 `sys.path` 索引 `0`。即使外部设置了 `PYTHONPATH=<ISOLATED_REPO>:<ISOLATED_REPO>/src` 并传入 `--project-root <ISOLATED_REPO>`，所有模块仍会被劫持回主工作区！
2. **J-A `_resolve_project_root()` 完全绑定模块物理文件位置**：
   - `stage1_5j_a_...py:537–543` 的 `_resolve_project_root()` 按 `Path(__file__).resolve().parent.parent.parent.parent` 反推根目录，且公开入口 `load_verified_stage1_5j_a_historical_archive_coverage_root(root_dir)`（L1341）**不接受 `project_root` 参数**。只有当 `stage1_5j_a_...` 真实从 `<ISOLATED_REPO>/src/...` 导入时，`_resolve_project_root()` 才会锚定到 `<ISOLATED_REPO>`，使 `root_dir` 通过 `not_under_output_parent` 校验（L1373）并解析隔离根下的 `configs/base.py` 与 `.git/plan-execution/...`。
3. **双命名空间导入要求（带 `src.` 与不带 `src.`）**：
   - J-A 内部 `_import_verified_frozen_parser()`（`stage1_5j_a_...py:843`）动态导入 **`src.research.external_signal_shadow.stage1_5d_live_event_source_parser`**（带 `src.` 前缀）并严格校验其 `__file__` 与 `__spec__.origin` 等于 `<ISOLATED_REPO>/src/...`；
   - 而 J-A/J-B/Taker/OI 模块内部又导入 `configs.*` 与 `research.external_signal_shadow.*`（不带 `src.` 前缀）；
   - 同时 `stage1_5j_b_...py:308,380` 在模块导入时即运行 `_verify_stage_config()`，要求 `configs.stage1_5j_b_...` 的 `__file__` 严格等于 `<ISOLATED_REPO>/configs/stage1_5j_b_...py`。
4. **必须的仓外适配差异（本轮不实现，待批后新建独立脚本，保留旧脚本 `085ab4c2...` 不动）**：
   - **差异 1（先解析参数再导包）**：移除硬编码 `DEFAULT_PROJECT_ROOT` 及模块顶层业务 `import`；先解析 `--isolated-repo-root`、`--main-repo-root`、`--auth-file`、`--output-dir`，清理 `sys.path` 中所有指向主仓库的路径（且要求进程 `cwd` 位于 `/private/tmp/...` 而非主仓），再将 `[str(isolated_root), str(isolated_root / "src")]` 置于 `sys.path` 最前，随后才导入 `configs.*`、`research.*` 与 J-A 公开 strict loader。
   - **差异 2（导入起源硬断言）**：在调用公开 `load_verified_stage1_5j_a_historical_archive_coverage_root` 前后，对已导入的 `configs.base`、`configs.stage1_5j_b_...`、`stage1_5j_a_...`、`stage1_5j_b_...`、`launch_taker_buy_share_...`、`launch_open_interest_basis_...`（及加载后的 `src.research.external_signal_shadow.stage1_5d_live_event_source_parser`）逐一断言 `Path(mod.__file__).resolve()` 与 `Path(mod.__spec__.origin).resolve()` 均严格位于 `<ISOLATED_REPO>` 之下且与主仓无交集。
   - **差异 3（冻结配置 SHA 与双 `HEAD` 核对）**：将 `configs/base.py` 期望 SHA 绑定为隔离历史快照值 `473dd4e9...`，同时分别调用 `verify_actual_git_head` 核对**主工作区 `HEAD == 7bdb29bf...`** 与**隔离快照 `HEAD == 2f9ba8e0...`**（执行前及执行后各一次）。
5. **严格遵守的公开入口禁令**：仅调用未修改的公开 `load_verified_stage1_5j_a_historical_archive_coverage_root`；**严禁 monkeypatch、严禁调用 `_load_verified_..._for_test`、严禁跳过校验或删除历史哈希检查**。

### 9.4 新执行身份重新绑定（严格区分主仓与隔离环境）

- **既有授权已作废**：`H1_PATH_B_READONLY_20261120_01` 已于 `2026-11-20T07:47:53Z` 执行并 fail-closed 停止，**不可复用于重跑**；原脚本 `085ab4c2...`、原授权 `dba30329...` 与原日志 `2a1ddb24...` 全部原封保留。
- **未来新授权 JSON 必须分别绑定以下独立身份（禁止将两处 `HEAD` 混为一谈）**：
  1. `governance_authorization_reference`：全新批准标识（如 `H1_PATH_B_ISOLATED_2F9_20261120_02`），`governance_admission_mode` 由用户明确指定，`operation = "h1_path_b_isolated_snapshot_preflight_read_only_once"`；
  2. `main_workspace_root`（`/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab`）与 `main_workspace_expected_head_sha = 7bdb29bfc89155d6b155df6bed61479a496d3da9`；
  3. `isolated_snapshot_root`（`/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0`）与 `isolated_snapshot_expected_head_sha = 2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`；
  4. 冻结输入身份：`isolated_base_config_sha256 = 473dd4e9...`、J-A 4 件套 SHA、J-A 闭环证据 + sidecar SHA、J-A 历史 `network_authorization.txt` SHA（仅作来源证据，`network_allowed=false`）、V2 分类账本 SHA；
  5. 新仓外适配脚本的精确路径与合成测试通过后的实测 SHA-256；
  6. 全新仓外输出目录（如 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/run_output`，尚不存在、独占非软链写盘）及全部 8 项 `false` 禁止标志。

### 9.5 最小执行步骤、验证方法、停止条件与本轮最新预算

**未来获批后的最小执行步骤（本轮均未执行）：**
1. **步骤 1（仅脚本与合成验证）**：在 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/` 编写新仓外适配脚本及合成测试（新增“主仓路径污染拒载”、“模块 `__file__` 必须落在隔离根”、“双 HEAD 失配拒载” 3 项回归），用 `PYTHONDONTWRITEBYTECODE=1 python3 -B` 跑通全部合成测试（预期 `RC=0`，零真实数据读取）并锁定新脚本 SHA。
2. **步骤 2（仅待用户签发新批准后创建隔离副本）**：执行 `git clone --local --no-checkout --no-hardlinks` + `checkout --detach 2f9ba8e0...`，逐字节深拷贝 J-A 根（709 文件）及 5 个未跟踪原件，复核全部 SHA 后施加 `chmod -R a-w`。
3. **步骤 3（单次路径 B 隔离执行）**：切换 `cwd=/private/tmp/h1-isolated-hist-2f9ba8e0-20261120`，运行 `PYTHONDONTWRITEBYTECODE=1 python3 -B .../run_h1_path_b_isolated_snapshot.py --main-repo-root ... --isolated-repo-root ... --auth-file ... --output-dir ...`；预期 `RC=0`，产出 `run_output/path_b_estimability_summary.json`（零 J-B 收据消费，零未来收益/MAE/MFE/拟合，S1/S2 与未来标签窗仅查记录存在与边界空档规则完全不变）。
4. **步骤 4（主仓不变性与结果回填）**：核对主仓 `HEAD` / staged / unstaged patch 逐字节不变、零 `__pycache__`、隔离仓 `HEAD == 2f9ba8e0...`、模块起源日志无主仓路径；仅向本报告追加实测分母、缺口、稀疏、边界空档与卖压可比性分布表，交付独立审核。

**硬停止条件：**
- 任何模块 `__file__` / `__spec__.origin` 落入主工作区、任一双 `HEAD` 或冻结 SHA 失配、J-A strict loader 触发任何 `STOP`、账本双射或成交顺序报错 → 立即停止并报告，不绕过；
- **若运行中发现必须修改冻结 loader、收据或信任规则才能通过 → 立即停止并报告具体冲突，绝不自行扩大为兼容工程**；
- 累计投入达到原 `4.00` 人时总上限 → 立即交付现状并停止，不自动追加。

**最新预算核算（计入本轮实际消耗，沿用原 `4.00` 人时总上限，不重新起算）：**

| 环节 | 时间记录（UTC） | 计量口径 | 消耗（人时） |
| --- | --- | --- | ---: |
| 前期累计（环节 1–5，见 §7.5 & §8.4） | — | 墙钟 `1.36` + 估算 `0.25` | `1.61`（含外部审查/协作保守估算约 `2.05`） |
| 6. 本轮 §8.3 源码修正、历史组件核对与 §9 隔离方案准备 | 2026-11-20 `09:20:54Z → 09:25:xxZ`（约 5 分钟） | **实测墙钟** | `0.08` |
| **最新累计执行投入** | — | 墙钟 `1.44` + 估算 `0.25` | **`1.69`**（含前期协作保守估算约 **`2.13`**） |
| **原 `4.00` 人时总上限内剩余预算** | `4.00 - (1.69 ~ 2.13)` | 按上限扣减 | **`1.87 ~ 2.31`**（不自动追加） |
| 7. 获批后完成隔离脚本/合成测试 + 建隔离副本 + 单次运行 + 回填与独立复核（预计） | — | **估算** | **`1.25 ~ 1.90`**（外部支出 `$0`；**可紧贴落入剩余 `1.87 ~ 2.31` 人时内，但已无多余返修空间**，若审核再次打回或触及 `4.00` 上限须直接暂停） |


---

## 10. 隔离环境单次执行结果（`H1_PATH_B_ISOLATED_2F9_20261120_02`）

> **执行状态：`STOPPED_FAIL_CLOSED`（`RC=1`）｜结论维持：`evidence_insufficient`**  
> 隔离历史快照创建、714 文件深拷贝与完整性校验、双 `HEAD`、16 项冻结身份、6 个隔离模块起源校验及 J-A strict loader 的 `manifest`/`summary`/`_validate_authority_packet`/`review`/`journal`/`catalog_scan_a/b` 重放**全部通过**；在 J-A strict loader `L1486` 动态导入冻结解析器 `stage1_5d_live_event_source_parser.py` 时，因命令中 `python3` 解析为 macOS 系统 **`Python 3.9.6`**（不支持 PEP 604 `str | None` 运行期联合类型语法）触发 `TypeError` 停止。按批准书停止条件，**已立即停止、保留现场并报告；未私自切换解释器重跑、未修改任何代码/脚本/配置/旧授权**。

### 10.1 批准与执行身份、实际命令、退出码与完整日志

- **批准标识：** `H1_PATH_B_ISOLATED_2F9_20261120_02`（已执行并停机，后续不得复用）
- **报告执行前保留前缀 SHA-256（§§1–9 逐字节不变）：** `a0f1e35bddb8c0ac71eaf9343dda67ac959a8dbded29312eac2c3354a0f4a95e`（备份原件留存于 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/stage2_evidence/report_before_stage2.md`）
- **主仓实际 `HEAD`（执行前及执行后一致）：** `7bdb29bfc89155d6b155df6bed61479a496d3da9`
- **隔离历史仓及实际 `HEAD`：** `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0` — `2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`（隔离 `configs/base.py` SHA-256：`473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc`）
- **获准运行脚本：** `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/run_h1_path_b_isolated_snapshot.py`
  - SHA-256：`6b78a3f1c32d771cd767e599c34175b125a1248e226f84fbc1d8304cab879959`（未修改）
- **本次授权 JSON：** `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/path_b_isolated_authorization.json`
  - SHA-256：`c77f87ebf82461c563b9b20d113e03f337c391a991641a04b0c8d07c67e3f047`
- **隔离副本完整性证据（`/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/stage2_evidence/step2_copy_integrity.json`）：**
  - 深拷贝普通文件 `714` 个（J-A 根 `709` 文件 + V2 账本 + 4 个原件/sidecar），合计 `778,626,377` 字节（`742.56 MiB`）；`symlinks_detected = 0`、`hardlinks_detected = 0`；全部 `708` 项 J-A manifest 产物与 `16` 项冻结文件 SHA-256 精确匹配；仅在隔离仓内对 `1,689` 个条目施加只读 `chmod`（主仓零改动）。
- **步骤 4 实际执行命令（`cwd=/private/tmp/h1-isolated-hist-2f9ba8e0-20261120`）：**
  ```bash
  env -u PYTHONPATH -u GIT_DIR -u GIT_WORK_TREE \
    PYTHONDONTWRITEBYTECODE=1 python3 -B \
    /private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/run_h1_path_b_isolated_snapshot.py \
    --main-repo-root /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab \
    --isolated-repo-root /private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0 \
    --auth-file /private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/path_b_isolated_authorization.json \
    --output-dir /private/tmp/h1-isolated-hist-2f9ba8e0-20261120/run_output
  ```
- **执行时间（UTC）：** `2026-11-20T10:22:12Z → 2026-11-20T10:22:16Z`｜**真实退出码：** `RC=1`
- **完整 stdout/stderr 日志（留存于 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/stage2_evidence/run_stdout_stderr.log`）：**
  ```text
  Traceback (most recent call last):
    File "/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/run_h1_path_b_isolated_snapshot.py", line 1762, in <module>
      raise SystemExit(main())
    File "/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/run_h1_path_b_isolated_snapshot.py", line 1751, in main
      out_file = run_authorized_isolated_path_b_preflight(
    File "/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/run_h1_path_b_isolated_snapshot.py", line 1542, in run_authorized_isolated_path_b_preflight
      ja_summary = ja_loader(ja_root)
    File "/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0/src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py", line 1345, in load_verified_stage1_5j_a_historical_archive_coverage_root
      return _load_verified_stage1_5j_a_historical_archive_coverage_root_internal(
    File "/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0/src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py", line 1486, in _load_verified_stage1_5j_a_historical_archive_coverage_root_internal
      parser_mod = _import_verified_frozen_parser()
    File "/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0/src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py", line 847, in _import_verified_frozen_parser
      mod = importlib.import_module(mod_name)
    File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/importlib/__init__.py", line 127, in import_module
      return _bootstrap._gcd_import(name[level:], package, level)
    File "<frozen importlib._bootstrap>", line 1030, in _gcd_import
    File "<frozen importlib._bootstrap>", line 1007, in _find_and_load
    File "<frozen importlib._bootstrap>", line 986, in _find_and_load_unlocked
    File "<frozen importlib._bootstrap>", line 680, in _load_unlocked
    File "<frozen importlib._bootstrap_external>", line 850, in exec_module
    File "<frozen importlib._bootstrap_external>", line 228, in _call_with_frames_removed
    File "/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0/src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py", line 61, in <module>
      def _find_launch_candidate_window(text: str) -> str | None:
  TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
  ```

### 10.2 实际推进边界、根因与隔离验证证据

1. **隔离接线与上游 `authority_packet` 实测通过**：
   - 从失败栈可见，调用链中的 `stage1_5j_a_...py`（`L1345 -> L1486 -> L847`）及被导入的 `stage1_5d_live_event_source_parser.py`（`L61`）均来自 **`/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0/src/...`**，无任何主仓路径泄漏；
   - J-A strict loader 已顺利通过了此前在主仓失败的 `_validate_authority_packet`（`L1447`，`configs/base.py = 473dd4e9...` 校验通过）、`render_stage1_5j_a_review`（`L1450`）、`request_journal.jsonl` 重放（`L1460`）以及 `catalog_scan_a`/`catalog_scan_b` 双扫重放（`L1484`）。
2. **精确失败根因（解释器版本，非代码/隔离缺陷）**：
   - 命令中 `python3` 在系统 `PATH` 中解析为 `/usr/bin/python3`（`Python 3.9.6`）；而冻结解析器 `stage1_5d_live_event_source_parser.py` 未使用 `from __future__ import annotations`，其第 61 行 `-> str | None`（PEP 604）需要 **Python 3.10+**。
   - 只读核查确认：项目 `.venv/bin/python` 软链指向独立的 **`/Users/tanshuai/.local/share/uv/python/cpython-3.11.14-macos-aarch64-none/bin/python3.11`（`Python 3.11.14`）**；且经静态核对，该独立 `python3.11` 解释器的 `sys.path` 完全不含主仓路径，J-A/J-B/Taker/OI/Parser 全部 5 个模块仅依赖 Python 标准库（零第三方包依赖）。**注意：不可直接调用 `<主仓>/.venv/bin/python`**，因为其 `site-packages` 位于主仓目录内，会触发防污染门禁 `STOP=main_repo_path_pollution_detected`。
3. **尚未发生的步骤与分母状态**：
   - 未执行 `raw/article_details/*.json` 语义重放（`L1544`）、未执行 `validate_archive_package` ZIP 解压与逐笔解析（`L1604`）、未解析 V2 分类账本逐行明细、未执行 H1 `S1`/`S2` 窗口统计、未创建 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/run_output`；
   - Parent/child 实测分母、缺口、稀疏状态、首末时间、边界空档与卖压可比性全部维持 **`not_executed / unknown`**，`RISK_LIVE_TRADING_ENABLED` 保持 `False`。

### 10.3 本次预算更新（继续累计原 `4.00` 人时总上限，不重新起算）

| 环节 | 时间记录（UTC） | 计量口径 | 消耗（人时） |
| --- | --- | --- | ---: |
| 前期累计（环节 1–6，见 §9.5） | — | 墙钟 `1.44` + 估算 `0.25` | `1.69`（含外部审查/协作保守估算约 `2.13`） |
| 7. 第 1 阶段仓外隔离脚本与 10 项合成测试（`-B` & `-O -B`） | 2026-11-20 `09:41:15Z → 09:48:34Z`（7.3 分钟） | **实测墙钟** | `0.12` |
| 8. 第 2 阶段克隆/深拷贝/校验、单次执行（Python 3.9 停机）与 §10 报告追加 | 2026-11-20 `10:20:51Z → 10:25:xxZ`（约 4 分钟） | **实测墙钟** | `0.07` |
| **最新累计执行投入** | — | 墙钟 `1.63` + 估算 `0.25` | **`1.88`**（含前期独立审查/协作保守估算约 **`2.45`**，已粗估纳入第 1 阶段审核约 `0.13` 人时） |
| **原 `4.00` 人时总上限内剩余预算** | `4.00 - (1.88 ~ 2.45)` | 按上限扣减 | **`1.55 ~ 2.12`**（不自动追加；仅需切换为独立 `python3.11` 解释器即可复跑，无需改脚本或重新复制，预计耗时 `0.40 ~ 0.80` 人时含复核） |

### 10.4 供独立审核与用户决策的最小解除阻断动作（本轮不自行执行）

- **零代码改动、零重拷贝**：隔离只读快照 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0` 与脚本 `6b78a3f1...` 均已就绪且保持完整；
- 若用户批准继续，仅需签发新批准标识（如 `H1_PATH_B_ISOLATED_2F9_20261120_03`，作废 `_02`），明确允许：
  1. 复用已核验的只读隔离快照 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0` 与脚本 `6b78a3f1...`；
  2. 新建对应的新授权 JSON（仅更新 `governance_authorization_reference` 与新证据目录）；
  3. 将步骤 4 命令中的解释器由系统 `python3`（3.9.6）明确指定为仓外独立解释器 `/Users/tanshuai/.local/share/uv/python/cpython-3.11.14-macos-aarch64-none/bin/python3.11 -B` 执行单次只读预审。


---

### 10.5 获批复跑结果（`H1_PATH_B_ISOLATED_2F9_20261120_03`，独立 `Python 3.11.14`，`RC=0`）

> **执行状态：`COMPLETED_RC_0`｜严格边界：`records_present != confirmed_estimable`、`no_alpha_claim`**  
> 按用户批准使用独立仓外解释器 `/Users/tanshuai/.local/share/uv/python/cpython-3.11.14-macos-aarch64-none/bin/python3.11 -B`、复用只读快照 `repo_2f9ba8e0` 与未修改脚本 `6b78a3f1...`，在通过前置解释器与 7/7 隔离模块（含 `stage1_5d_live_event_source_parser`）导入核验后，完成单次路径 B 隔离只读预审（`RC=0`）。**全程未消费 J-B 收据，未计算任何未来收益、MAE/MFE、收益排名、相关性或拟合模型**；`§§1–10.4` 历史内容逐字节保留。

#### 10.5.1 执行身份、命令、退出码与模块起源证据

- **批准标识：** `H1_PATH_B_ISOLATED_2F9_20261120_03`（新授权，未复用 `_01` 或 `_02`）
- **固定解释器：** `/Users/tanshuai/.local/share/uv/python/cpython-3.11.14-macos-aarch64-none/bin/python3.11`（`Python 3.11.14`，仓外独立路径，非裸 `python3`、非主仓 `.venv/bin/python`）
- **报告追加前保留前缀 SHA-256（§§1–10.4 逐字节不变）：** `ff0d8559bf48299cc4efe9c240ebfc68dbd1949e24fb8b1a1f4c985224b14a34`（备份于 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/stage2_evidence_03/report_before_run03.md`）
- **双 `HEAD`（执行前、写盘前、写盘后三次核对一致）：**
  - 主仓 `HEAD`：`7bdb29bfc89155d6b155df6bed61479a496d3da9`
  - 隔离历史仓 `HEAD`：`2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`（`configs/base.py` = `473dd4e9...`，`RISK_LIVE_TRADING_ENABLED = False`）
- **未修改脚本 SHA-256：** `6b78a3f1c32d771cd767e599c34175b125a1248e226f84fbc1d8304cab879959`
- **新授权 JSON：** `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/path_b_isolated_authorization_03.json`
  - SHA-256：`446333a58274f65695a4449f686b7a8007afb115a16fd8a5d826020a4c279378`（保持原 27 键精确 schema，全部 8 项禁止标志 `false`）
- **前置导入验证（未调用 loader，`/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/stage2_evidence_03/step1_py311_import_check.json`）：** 7/7 必需模块（含 `src.research.external_signal_shadow.stage1_5d_live_event_source_parser`）均严格自 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0/...` 导入，零主仓路径泄漏。
- **实际执行命令（`cwd=/private/tmp/h1-isolated-hist-2f9ba8e0-20261120`）：**
  ```bash
  env -u PYTHONPATH -u GIT_DIR -u GIT_WORK_TREE \
    PYTHONDONTWRITEBYTECODE=1 \
    /Users/tanshuai/.local/share/uv/python/cpython-3.11.14-macos-aarch64-none/bin/python3.11 -B \
    /private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/run_h1_path_b_isolated_snapshot.py \
    --main-repo-root /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab \
    --isolated-repo-root /private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0 \
    --auth-file /private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/path_b_isolated_authorization_03.json \
    --output-dir /private/tmp/h1-isolated-hist-2f9ba8e0-20261120/run_output_03
  ```
- **执行时间（UTC）：** `2026-11-20T10:39:38Z → 2026-11-20T10:41:20Z`（约 102 秒）｜**真实退出码：** `RC=0`
- **唯一结果产物：** `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/run_output_03/path_b_estimability_summary.json`
  - 体积：`523,390` 字节｜SHA-256：`bf1fdb3e93c57de008c1612bacafec51ef57f735e654f2688fd9082366fed6cd`
  - 全部 7/7 实跑模块 `__file__`/`__spec__.origin` 均记录于结果 JSON `verified_isolated_module_origins` 且全部落在 `/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0/` 下；`consume_jb_receipt = false`、`future_return_or_path_computed = false`、`risk_live_trading_enabled = false`。

#### 10.5.2 实测 Parent / child 分母守恒、全量缺口与时间跨度（零 J-B 依赖）

1. **无 J-B 账本对账通过（`bijection_verified_without_jb = true`）**：
   - J-A `in_scope_usdt` child 总数 = V2 分类账本行数 = **`281`**；
   - 全集结构：`crypto|standard|confirmed = 53`、`crypto|pre_market|confirmed = 18`、`equity|standard|confirmed = 165`、`etf|standard|confirmed = 31`、`commodity|standard|confirmed = 7`、`equity|pre_ipo|confirmed = 6`、`unknown|standard|unknown = 1`；
   - 全部 53 条入选 `standard crypto` 记录均通过了 J-A `raw/article_details/*.json` manifest SHA、标题 regime 与正文 AST 表格证据重证，对应 **`42` 个独立 Parent**（其中 `10` 个为多 child Parent）。
2. **`S1` 与 `S2` 实测分母与缺口（两窗口分母与缺口完全一致，`denominator_conservation_verified = true`）**：

| 分母 / 状态项 | `S1` 实测 | `S2` 实测 | 说明 |
| --- | ---: | ---: | --- |
| `n_children_total`（入选 `standard crypto` child） | `53` | `53` | 全量守恒 |
| `records_present_estimability_unconfirmed`（child） | `51` | `51` | 仅表示各子窗与未来窗均存在记录且无 `sequence_gap` |
| `j_a_parent_or_detail_gap`（child） | `2` | `2` | 同一 Parent `31ec31401a...` 下 `AIAUSDT`、`SPORTFUNUSDT`（继承 J-A 上游缺口） |
| 其余 6 类缺口（`sequence_gap` / `anchor_*` / 空窗 / 空标签 / 缺日期包） | 均为 `0` | 均为 `0` | 全部 51 个 child 零 `sequence_gap`、零空窗、零空标签 |
| `n_parents_total`（独立 Parent） | `42` | `42` | `41 + 0 + 1 = 42` 守恒 |
| `n_parents_all_children_records_present` | `41` | `41` | 全 child 均存在记录的独立 Parent |
| `n_parents_partial_gap` / `n_parents_all_gap` | `0` / `1` | `0` / `1` | 缺口集中在 1 个 Parent |
| `n_parents_all_records_present_with_any_sparse_window` | `0` | `0` | 51 个 child 中无任何子窗或标签窗出现 `< 2` 笔成交 |
| **`n_parents_confirmed_estimable`** | **`null`** | **`null`** | **`unknown_pending_endpoint_and_design_criteria`（端点与可估计条件未定义，绝不强行判通过）** |
| 同 UTC 日多 Parent 聚类 | `2` 日（`4` Parent） | `2` 日（`4` Parent） | `2025-12-10`（2 个 Parent）、`2026-01-22`（2 个 Parent） |

3. **时间跨度与锚点延迟（51 个存在记录的 child）**：
   - 首末锚点时间 $T_0$：**`2025-10-09T09:45:02.386Z`** 至 **`2026-09-06T06:45:01.348Z`**；
   - 锚点延迟 `anchor_delay_ms`：`min = 380 ms`、`P50 = 1,341 ms`、`P90 = 3,343 ms`、`max = 297,911 ms`（全部 $\le 300{,}000\text{ ms}$，但最大一笔接近 5 分钟上限）。

#### 10.5.3 实测成交活跃度、连续性与边界空档（51 个 child，零稀疏窗）

| 窗口与子段 | 成交笔数 `min / P50 / max` | 成交额 USDT `min / P50 / max` | 最大成交间隔 `P50 / P90 / max` (ms) | 首端空档 `P50 / max` (ms) | 末端空档 `P50 / P90 / max` (ms) |
| --- | --- | --- | --- | --- | --- |
| **`S1` `buf` `[0, 5m)`** | `1,662 / 14,737 / 60,318` | `240.6k / 3.38M / 10.90M` | `644 / 2,394 / 5,807` | `0 / 0` | `61 / 298 / 2,531` |
| **`S1` `W1` `[5m, 15m)`** | `1,157 / 18,147 / 170,185` | `199.6k / 3.41M / 21.49M` | `1,147 / 3,552 / 8,738` | `53 / 1,900` | `67 / 377 / 2,016` |
| **`S1` `W2` `[15m, 25m)`** | `878 / 14,745 / 110,970` | `169.6k / 3.00M / 19.01M` | `1,203 / 3,610 / 10,437` | `105 / 2,874` | `64 / 208 / 2,848` |
| **`S1` `label` `[25m, 40m]`（仅计数/时间）** | `1,581 / 24,822 / 123,721` | *不读取* | `1,283 / 4,272 / 14,877` | `69 / 883` | `81 / 320 / 594` |
| **`S2` `buf` `[0, 15m)`** | `2,819 / 35,610 / 215,622` | `440.2k / 6.89M / 28.32M` | `1,152 / 3,552 / 8,738` | `0 / 0` | `67 / 377 / 2,016` |
| **`S2` `W1` `[15m, 35m)`** | `1,956 / 32,898 / 187,388` | `430.0k / 5.84M / 30.50M` | `1,478 / 4,156 / 12,417` | `105 / 2,874` | `84 / 275 / 512` |
| **`S2` `W2` `[35m, 55m)`** | `2,020 / 27,616 / 131,040` | `354.9k / 4.60M / 21.50M` | `1,556 / 5,812 / 17,688` | `55 / 547` | `67 / 354 / 857` |
| **`S2` `label` `[55m, 70m]`（仅计数/时间）** | `1,583 / 17,443 / 146,624` | *不读取* | `1,643 / 5,922 / 12,121` | `84 / 418` | `120 / 485 / 3,318` |

- **事实解读**：在 51 个存在记录的 `standard crypto` child 上，未出现成交稀疏断档（最低单子窗也有 `878` 笔成交，未来标签窗末端空档中位数仅 `81 ms` / `120 ms`、最大 `594 ms` / `3,318 ms`）。

#### 10.5.4 实测成交方向与卖压可比性分布（揭示 3 项关键数据限制）

| 指标（51 child；持续净卖压子集单独标注） | `S1` 实测分位数 / 计数 | `S2` 实测分位数 / 计数 | 事实含义与限制 |
| --- | --- | --- | --- |
| 持续净卖压（$Q_{W_1}<0 \land Q_{W_2}<0$）child 数 | **`32 / 51`**（`W1` 净卖 `43`，`W2` 净卖 `39`） | **`29 / 51`**（`W1` 净卖 `43`，`W2` 净卖 `35`） | `standard` 新币上线在开盘首小时整体偏主动净卖出 |
| 持续净卖压独立 Parent 数（任一 child / 全 child） | **`28 / 41`**（全 child：`23 / 41`） | **`23 / 41`**（全 child：`20 / 41`） | 仅按 $>0$ 口径看子集占过半 Parent |
| 描述性强度分布（非筛选阈值）：$-I_{W_1}, -I_{W_2} > 0.02$ / $> 0.05$ | 任一 child Parent：`21 / 41`｜**`7 / 41`** | 任一 child Parent：`16 / 41`｜**`7 / 41`** | **限制 1（卖压幅度偏温和）**：多数持续净卖压仅微弱偏卖（全样本 $-I$ 中位数仅 `+3% ~ +4%`），两段均超 `5%` 的独立 Parent 仅 **7 个** |
| 全样本归一化净卖压 $-I_{W_1}$ / $-I_{W_2}$ | `P10=-0.007, P50=+0.037, P90=+0.119` / `P10=-0.035, P50=+0.039, P90=+0.096` | `P10=-0.006, P50=+0.032, P90=+0.087` / `P10=-0.032, P50=+0.029, P90=+0.080` | — |
| 活跃度衰减比 $V_{W_2}/V_{W_1}$ | `P10=0.525, P50=0.836, P90=1.474`（`min=0.369, max=2.274`） | `P10=0.510, P50=0.773, P90=1.167`（`min=0.357, max=4.636`） | 活跃度温和回落（中位保留约 77%–84%），未普遍坍塌 |
| 相对缓冲窗卖压 $-Q_{W_1}/V_{\text{buf}}$ / $-Q_{W_2}/V_{\text{buf}}$ | `P50=+0.046` / `P50=+0.038` | `P50=+0.030` / `P50=+0.017` | 跨币种绝对成交额相差 **71×–108×**（**限制 2**：绝对 USDT 净卖额完全不可跨币种直接比较） |
| 持续子集卖压保持比 $(-Q_{W_2})/(-Q_{W_1})$ | `P25=0.509, P50=1.105, P90=4.663, max=20.817` | `P25=0.312, P50=0.900, P90=9.677, max=34.118` | **限制 3（比值奇异）**：因部分事件 $W_1$ 净卖压接近 0（如 `-I = +0.0008`），原始比值飙升至 `20.8× / 34.1×`，后续若建模**严禁直接使用原始净流比值** |

- **综合事实定位（不宣布 H1 成立，不自动进入收益实验）**：
  1. **原始成交覆盖层面**：51/53 个 `standard crypto` child（41/42 个独立 Parent）在 `S1`/`S2` 窗内成交密集、零 `sequence_gap`、零空窗，排除了“数据大面积稀疏断档或活跃度彻底坍塌”的担忧；
  2. **研究可估计性与价值约束层面**：仍存在四项硬制约——（a）两段均具较强净卖压的独立 Parent 偏少（两段 $-I > 5\%$ 仅 `7/41` Parent），多数仅微弱偏卖（`+3% ~ +4%`）；（b）原始净流比值存在近零分母爆炸（最高 `34.1×`），跨币种绝对成交额相差约 100 倍；（c）端点匹配规则、基准变量有效秩与可检测精度尚未经正式 Design 论证（`n_parents_confirmed_estimable = null`），且缺少实时盘口/报价/撤单数据；（d）全部 41 个 Parent 仍是反复观测过的旧开发集，短期外样本稀少（11-10 预审 2 个月仅 1 个已知暴露候选 `CTUSDT`）。

#### 10.5.5 最终预算核算（累计在原 `4.00` 人时总上限内，未超支）

| 环节 | 时间记录（UTC） | 计量口径 | 消耗（人时） |
| --- | --- | --- | ---: |
| 前期累计（环节 1–8，见 §10.3） | — | 墙钟 `1.63` + 估算 `0.25` | `1.88`（含外部审查/协作保守估算约 `2.45`） |
| 9. 本次 `H1_PATH_B_ISOLATED_2F9_20261120_03` 解释器/导入前置核验、单次执行（`RC=0`）、结果汇总与 §10.5 追加 | 2026-11-20 `10:39:06Z → 10:45:xxZ`（约 6 分钟） | **实测墙钟** | `0.10` |
| **预审全流程最终累计投入** | — | 墙钟 `1.73` + 估算 `0.25` | **`1.98`**（含全程独立审查/协作保守估算约 **`2.65`**） |
| **原 `4.00` 人时上限内结余** | `4.00 - (1.98 ~ 2.65)` | 按上限扣减 | **`1.35 ~ 2.02`**（未超时、未追加预算；本轮预审圆满闭环，交付独立审核） |
