# PREDICT 盘前 OI 情景 C 单事件留出检查 Design

**日期：** 2026-11-07。**状态：** `design_candidate / hypothesis_only`，待独立审查及用户批准。

**本轮权限：** 仅起草本文。不授权 implementation、真实训练输入消费、拟合、ZIP 下载/解压、新事件数值读取、研究运行、commit、push、部署、SSH、signal、paper、live 或 execution；`RISK_LIVE_TRADING_ENABLED=False` 保持不变。

## 1. 目标、事实与投入取舍

只回答：**用旧 18 个盘前 Parent 冻结的价格基准 M0 与价格/OI 交互模型 M1，在一个较晚事件 PREDICTUSDT 上分别产生什么预测误差？** 不验证总体 Alpha，不要求结果有利，不把 N=1 当作新币总体分布。

- [旧增量研究 Design](2026-11-04-launch-price-oi-basis-incremental-information-exploratory-design_CN.md)，SHA-256 `f38fd9c4609a52cc9d2d6529cceabca35c778e84c374fad4e386029d0493519e`：旧主情景为 B；盘前 C 的内部 LOPO MSE 曾下降约 47.94%。本研究因已观察到该结果而提出，明确承认情景选择属于事后探索，不改写旧主情景。
- [时间假设 Delta](2026-11-02-launch-open-interest-scenario-assumptions-design-delta_CN.md)，SHA-256 `7941e641437ad20f4aee96be4b3ff65e7f97503d5d3f8693fdce81c29db55b54`：C 是信息偏移 10 分钟加发布余量 5 分钟的假设，不是实测时效保证。
- [修订预审](../../data/research_preflights/pre_market_after_20260416_20261106/review_CN.md)，当前 SHA-256 `8fd9ddfde793e974e85e7029202104d42ef143c67fefddd54252f5478ae652cc`：在其检索范围内确认 1 个后续候选；日包和校验文件存在，但内容、实际 T0、所需 OI 两点及历史可得性未验证。
- 事件固定为 `(parent_article_id=5ef55cf8358e4a48b2512a156e89c8e5, symbol=PREDICTUSDT, listing_regime=pre_market)`。[官方公告](https://www.binance.com/en/support/announcement/detail/5ef55cf8358e4a48b2512a156e89c8e5)记载计划开盘 `2026-10-25 08:15 UTC`，不是已经核实的首笔成交时间。

经济动机仅是假设：OI 变化可能在已知价格状态之外增加描述性信息；OI 同时对应多空双方，不识别主力、知情交易或单边流入。是否被研究者或其他会话查看过该事件数值尚不确定，报告默认 `prior_exposure_status=unknown`；有已知观察须如实披露，不能宣称完全盲测。

比较三条路径：继续调旧样本无法产生独立证据；等待更多事件可提高信息量但不必阻止个案检查；本次选择**冻结旧模型、单独评分一个后续事件**。优先复用现有纯计算和读取能力，不建设通用采集平台、调参框架或新版 J-A/J-B。若完成此目标仍需复制旧的大型准入管道，Plan 先说明具体障碍和更小替代，不自动扩建。

## 2. 输入、受限消费与版本边界

旧输出只供人工阅读和复核，不能默认成为新机器输入。本文申请：**用户批准本 Design 并明确接受本节边界、Plan 获批且取得适用真实消费授权后**，仅允许本 consumer 使用以下精确面板进行一次模型冻结及本事件检查。不改变旧文件、旧批准或其他 consumer 权限；不允许通过修改旧 CLI 的固定输入 hash 绕过约束。

| 输入 | 精确身份与用途 |
| --- | --- |
| 训练面板 | `data/research_archives/launch_incremental_run_20261105/parent_panel.csv`，SHA-256 `1396b1f0c34bbb99d936abf13a7a99f44863eb300c9fc35b4fbeefffee6faac2`；唯一训练数值来源。 |
| 配套旧报告 | 同目录 `review_CN.md`，SHA-256 `5f57a97d249c24c06656ee42dff4982fab1cc63742095f4ec16abb701ee3338d`；仅作协议/来源追溯，不从 Markdown 抽取模型输入。 |
| 新原始来源 | 仅 PREDICTUSDT 的官方 UM daily `aggTrades` 和 `metrics` 日包及对应 `.CHECKSUM`，见下表。不是 J-A/J-B 收据，不继承其消费批准，也不得写回旧 root。 |

面板结构以既有 [writer](../../scripts/external_signal_shadow/run_launch_price_oi_basis_incremental_information.py) 的 16 列为准：`parent_article_id,listing_regime,scenario,utc_date,child_symbols,required_child_count,scenario_complete_child_count,oi_complete,basis_complete,missing_reasons,p,o,b,y,long_mae,long_mfe`。验证实际 SHA、表头无重复、每行字段数、联合键 `(parent_article_id,listing_regime,scenario)` 唯一及所选行状态一致；不得仅因 hash 匹配跳过必要语义检查。

只选择 `listing_regime=pre_market AND scenario=C AND oi_complete=true` 的全部行，须恰为 18 个唯一 Parent，日期有效且均不晚于 `2026-04-16`，不含 PREDICT Parent/symbol。所需 child 数与完整 child 数一致且为正、缺失原因为空，`p,o,y,long_mae,long_mfe` 均有限。`b` 不作特征，不要求基差完整。保留排序后的 Parent/child 身份集合，不按收益、OI 大小或拟合效果删训练事件；行数、集合或身份异常时停止，不自动减少样本或重建旧面板。

官方日包路径统一为 `https://data.binance.vision/data/futures/um/daily/{kind}/PREDICTUSDT/{filename}`，校验文本 URL 为该路径加 `.CHECKSUM`：

| kind / filename | 预期 ZIP SHA-256 | 使用条件 |
| --- | --- | --- |
| `aggTrades / PREDICTUSDT-aggTrades-2026-10-25.zip` | `a25d07cd093a9251f69730e0ed9a1371fcb17f6cb94d4f360067ed7ca5d06ba4` | 首次上线日，必需。 |
| `metrics / PREDICTUSDT-metrics-2026-10-25.zip` | `0eff530f194d3b61996b1b5b149639a3550f2684a4f14ed1d9c4a63c29564df3` | 首次上线日，必需。 |
| `aggTrades / PREDICTUSDT-aggTrades-2026-10-26.zip` | `fc640042973f3c5238a14ae0d5d4f42f7e0f5c7d17fca4b798f8bd96adaeec95` | 仅实际必需窗口跨 UTC 日时。 |
| `metrics / PREDICTUSDT-metrics-2026-10-26.zip` | `c2ea538180af560b26021d9888bdbf04d2c9e25327e979adee618d692ab5e6cb` | 仅实际必需窗口跨 UTC 日时。 |

下载时官方校验文本中的文件名/摘要、实际 ZIP 摘要均须匹配上述身份；对象变化则停止，不自动更新 hash、换月包或换数据商。只读流式打开单 CSV，不向旧目录解压；复用既有 ZIP 资源上界及物理行长度保护，CSV 重复列、列数错误、错误 symbol/日期、非有限值、非法成交价格/数量、成交 ID 重复或逆序均拒绝。OI `create_time` 按 UTC 解析，使用 `sum_open_interest` 数量而非 `sum_open_interest_value`；不猜测时间单位、不把未知时间填成已验证事实。[官方公开数据说明](https://github.com/binance/binance-public-data)只提供归档与校验机制，不证明本事件内部时间覆盖或真实可得性。

`aggTrades` 表头/顺序固定为既有七列 `agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker`；ID/毫秒时间须为非负整数，`first_trade_id<=last_trade_id`，时间不得逆序且须落在包的 UTC 日期内，布尔只接受旧读取器的 `true/True/false/False`。`metrics` 必需 `create_time,symbol,sum_open_interest`，按列名读取；允许官方其他未使用列，但列名唯一、行字段数须匹配，时间格式为 UTC `YYYY-MM-DD HH:MM:SS` 且位于五分钟网格和对应 UTC 日。OI 原值须有限且非负；选定两点另须严格为正。格式不兼容则报告，不静默转换为其他来源版本。

## 3. 固定模型与冻结顺序

训练只进行一次，使用上述全部 18 个 Parent 的 C 情景 `p,o,y`，不是复用旧 LOPO 的某一折，也不再做 LOPO、重抽样或混入 standard 行。均值与总体标准差仅由这 18 行计算：`z_p=(p-mu_p)/sigma_p`，`z_o=(o-mu_o)/sigma_o`；`y` 不标准化，交互项不再次标准化。

| 模型 | 固定设计矩阵列 |
| --- | --- |
| M0 | `1,z_p` |
| M1 | `1,z_p,z_o,z_p*z_o` |

用现有 NumPy `linalg.lstsq(rcond=None)` 拟合；各矩阵须满列秩、训练行数大于列数、所需训练标准差大于零且参数有限，否则 `not_estimable`。不加 Ridge、不改特征、不裁剪预测或剔除 KITE 等极端训练事件。

只有两个模型均可估时，模型文件状态为 `frozen` 并允许继续。训练不可估时记录 `freeze_status=not_estimable`、可用的训练元数据和空系数，禁止进入新事件内容消费；仍可按 §4.2 写出一行未评分个案及原因报告，不伪造模型参数。

**顺序门禁：** 先读取获准旧面板，写出新建 `model_freeze.json` 并计算其 SHA-256；成功后才允许下载、读取或解析 PREDICT ZIP 内容。不得用新事件特征、目标、残差或是否有利来选择模型。实现测试须观察真实 I/O 顺序，不以文件时间戳或执行者口述单独证明冻结先后。

`model_freeze.json` 记录本次 Design/Plan 和实际代码身份、训练面板路径/hash、18 个训练身份、时间范围、C 协议、列顺序、均值/总体标准差、M0/M1 系数与矩阵秩、冻结执行时间及既往观察披露。数值以可 round-trip 的有限 JSON 数字保存，不先舍入系数；不含任何 PREDICT 数值，也不自包含自身 hash。后续评分读取该文件的同一已绑定字节，若变化则拒绝；报告中的 hash 仅绑定研究参数，不授予任何运行或交易权限。

## 4. 单事件特征与评分

### 4.1 锚点及时间窗口

- **评分锚点继承训练口径：** 沿用[旧 OI 父 Design §2](2026-11-01-launch-open-interest-basis-exploratory-design_CN.md)和 [J-B `select_launch_anchor_trade`](../../src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py)。本事件计划时间固定为 `S=symbol_launch_time_ms=2026-10-25 08:15:00 UTC`；完整读取并验证首次上线日 aggTrades 后，按 `(transact_time_ms,agg_trade_id)` 选取 `transact_time_ms>=S` 的首笔成交，仅当 `0<=T0-S<=300,000 ms` 时取得合格 T0。上限来自[冻结配置](../../configs/stage1_5j_b_historical_aggtrades_launch_response.py)的 `EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS=300_000`，不修改上游参数。T0 是计划上线后的参考锚点，不是整包最早成交，也不推断 T0 之前绝无成交。
- **提前成交仅作诊断：** 保留首日包最早成交的时间/ID、`transact_time_ms<S` 的成交数量、S 的来源版本及修订说明、合格锚点时间/ID/价格和延迟。早于 S 的同日成交不隐式删除，也不自动当作损坏；但不进入评分用 T0 或 `[T0,D)` 特征窗口。校验和不证明归档从未遗漏记录。
- **计划版本与可比性门禁：** 真实消费前须核实上述 S 的官方时间版本、修订说明及其对此事件的适用性；这不是要求证明历史实时可得性。若计划时间版本不可信、提前成交无法由来源证据合理解释，或存在更早交易日期、不是首次上线日或非盘前启动的已核实反证，保留 Universe=1，以 `anchor_or_regime_conflict` 结束，不评分。适用版本和提前成交已得到解释时，仍只按上述 J-B 规则选择 T0；不得自行换用另一计划时间、整包最早成交或按收益挑锚点。
- **锚点缺口：** 首日包缺失或没有 `transact_time_ms>=S` 的成交，记录 `data_gap` 及对应原因；首笔计划后成交的延迟超过 `300,000 ms` 时，记录 `data_gap / anchor_delay_exceeded`，不继续评分。恰好位于 S 或 `S+300,000 ms` 的首笔计划后成交可取得资格，`S+300,001 ms` 不可；不以次日首笔或提前成交补齐锚点。
- `D=T0+25m`；`p` 为 `[T0,D)` 的末笔价格除首笔价格减一。两个参考价格都按时间和 ID 排序，不用 K 线 close 替换。
- 只计算 C：假定信息截止 `label+10m`、可用时刻 `label+15m`。从 `T0<=label<=D-15m` 中先选最新标签 L1，再要求 `L0=L1-5m>=T0` 且记录存在；两点数量须有限、严格为正、单位一致，`o=OI(L1)/OI(L0)-1`。重复标签或最新点/前驱无效时报告缺口，不先过滤无效值再回退到更早完整对，不用开盘网格替代。
- 参考 entry 为 `[D,D+5s]` 首笔；`E=entry_time+15m`，endpoint 为 `[E-1s,E]` 末笔。`y=P_endpoint/P_entry-1`；MAE/MFE 取 entry 至选定 endpoint 的成交路径，分别与 0 取 min/max。最长需覆盖至 `T0+40m05s`，按实际 T0 计算所需 UTC 日期。
- 沿用旧 writer 的数值精度：由原成交和 OI 计算后，`p,o,y,long_mae,long_mfe` 以 `float(f"{value:.8f}")` 作为建模/评分值；原始参考价格、OI 数量及标签另行保留以便复核。不把显示时舍入后的模型系数用于预测。

上述假设不保证历史真实可得；输出始终 `historical_scenario_only / real_pit_verified=false`。已核实事实与假设冲突则报告，不把假设升级为证据。缺 Index、资金费率或盘口不阻止本次 C 检查，因为它们均不作本次输入；不得因此补造数据或增加指标。

### 4.2 评分、缺口和解释

新事件只套用冻结的标准化参数和系数。记录 `prediction_M0,prediction_M1,error_M0=y-prediction_M0,error_M1=y-prediction_M1`、两绝对/平方误差及 `d=error_M0^2-error_M1^2`。`d>0 / d<0 / d=0` 仅表示本事件平方误差改善/恶化/相等，非统计显著性、交易收益或总体证伪。另报训练 p/o 范围、新事件 z 值、是否超出训练范围及不合理外推（例如预测收益小于 -100%），保留原预测，不裁剪重算。

独立统计单位固定为这 1 个 Parent/child，不因两个模型、多笔成交或重复运行增加 N。唯一候选无论合格与否均保留：报告 Universe=1、scored=0/1、missing=1-scored 和具体原因。缺 OI 两点、参考成交或覆盖则 `data_gap`；模型不可估则 `not_estimable`；不补零、不改窗口、不排除该事件后换样本，也不通过重跑择优。

结果状态限 `scored / data_gap / not_estimable / anchor_or_regime_conflict`，均保持 `hypothesis_only / no_alpha_claim`。输入损坏、身份/权限不符或文件被修改是非零退出；合法数据缺口可交付完整说明，但不能标记已评分。N=1 的总体置信区间、Bootstrap、显著性、总体收益分布和集中度推断为 `N/A`；尾部只报告本事件 MAE/MFE 及外推诊断，贡献全部来自一个事件。不制造 5～10 个样本的充分性门槛。

## 5. 最小实现、产物与验收

建议只新增一个薄脚本及测试，具体路径由 Plan 白名单冻结。优先复用 [旧 OI core](../../src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py) 的 `AggTradeRecord`、`OiMetricRecord`、`stream_aggtrades_csv_lines`、`calculate_oi_change`、`calculate_baseline`、`calculate_path_response` 及既有 `validate_zip_archive_package`；调用前保证本节和 §4 的输入前提，不能因某 helper 默认过滤无效值而改变最新标签规则。训练系数仅需标准 NumPy 运算；旧增量 CLI 的 `_fit_and_predict_ols` 不返回系数，不为复用它修改旧接口。

不调用旧 `execute_exploratory_pipeline`、旧 J-A/J-B loader 或授权函数来冒充本任务权限；不修改旧实现、测试、分类账本、配置、依赖或批准文件。新来源的薄适配只处理本事件的两类官方文件，不复制旧收据系统，不新增独立 Verifier、Recorder、锁、fsync、恢复状态机或通用模型框架。

实际单批次在用户指定的全新持久 `batch_root` 下写 `model_freeze.json`、`holdout_case.csv`、`review_CN.md`；若含下载，仅在其 `inputs/` 保存获准原包及官方校验文本。拒绝已存在 root、覆盖/包含训练输入的输出路径和符号链接绕行；输入保持只读。冻结模型后才建立/消费新输入，CSV 和最终人工报告均绑定模型文件 hash、实际输入 hash 与代码版本。报告最后写，只有全部预期输出完成才标记批次完成；`data_gap` 等状态不能冒称评分成功，失败残留不得覆盖续跑。

模型文件只供本次获批 scorer 消费；评分 CSV/报告只供人工阅读和复核，不授权新的自动下游或未来事件接入。Rule 17 采用结构检查、hash 绑定及独立语义证据，不冒充旧完整 profile；模型研究参数文件不是资金或运行准入凭证。

| 不变量 | 具体验收与最小证据 |
| --- | --- |
| INV-01：权限/身份 | 实际 Design/Plan、训练快照及包身份匹配；未获真实消费许可时仅合成测试；无交易/部署/提交接线。 |
| INV-02：冻结先于新数据 | 真实入口测试捕获模型文件落盘/hash 绑定先于任何新事件内容 I/O；修改留出特征或 y 不改变训练参数，篡改模型文件被拒绝。 |
| INV-03：训练和事件隔离 | 18 个旧 Parent 全部入训，PREDICT 不入训；不混入其他 regime/scenario，不混合 19 个样本重做 LOPO；新事件保留分母。 |
| INV-04：时间/数据规则 | 独立手算覆盖：S 前成交保留但不作 T0（来源解释不足则冲突不评分）；已解释提前成交且 S 处有成交时选择 S；首笔计划后成交在 `S+300,000 ms` 可用、在 `S+300,001 ms` 不可用；首日包/计划后成交缺失、计划版本不可信均不能评分。另保留非网格 T0、C 等号边界、最新点无效/缺前驱不回退、同毫秒 ID 顺序、跨日和 entry/endpoint 缺口测试；PIT 未知标记保持。 |
| INV-05：数学正确 | 观察实际训练矩阵、标准化参数、冻结系数与 scorer 接线；独立已知向量核验 M0/M1 预测、误差及 d，零方差/秩不足不回退。 |
| INV-06：来源和报告 | canonical 上游 writer 产生训练面板正向夹具；公开归档格式的小型合成 ZIP 只证明适配规则，不冒充真实覆盖；授权后用实际包验证 hash/字段/时间。CLI 到三产物须有独立数值断言，单点变异及写出失败须拒绝或准确报告。 |

数学 oracle 可用 8 个纯合成训练点：`p=(-3,-2,-1,0,1,2,3,4)`、`o=(2,-1,3,0,-2,1,4,-3)`、`y=1+2p+3o+4po=(-23,2,-4,1,-11,16,67,-48)`。二者训练均值为 0.5、总体方差为 5.25；新点 `(p,o,y)=(0.5,1,7)` 的 M0 预测应为 0、M1 为 7、d 为 49。内部数学单测可用 8 点，真实入口正向夹具仍须符合训练结构和 18 个 Parent 约束；不得用被测拟合函数产生期望值或新增生产绕过开关。

## 6. 权限、停止条件与后续路由

审批仍为 Design 独立审查及用户批准 → Plan 独立审查及用户实施批准 → 代码/合成测试 → 独立完成审计。Design/Plan 批准均不自动授权真实训练、下载或评分。

用户后续可以**一次明确授权整个受控批次**，列明本任务 Design/Plan 身份、`freeze_model / download_inputs / score_case` 中实际允许的动作、训练来源、上述下载白名单及唯一新 root；内部顺序门禁不要求另建逐阶段批准系统。没有下载许可时仅能使用获准且 hash 匹配的现有包；没有真实训练或评分许可则不得消费相应数据。下载仅限官方 HTTPS 公开来源，无账户/API 密钥或交易客户端；HTTP 不可达不解释为数据不存在，不能自动换源。

本阶段费用、滑点、资金费率、可成交止损、容量、仓位、资本存活、条件交易规则及 live-safe 均为 `N/A`：没有定义交易策略，全部延期。不能凭本事件 d 的正负晋级或否决总体 OI 假说，不能把 M0 是比较基准等同于价格自身已有可交易 Alpha。已知选择偏差、单样本、高尾部风险、来源及时间假设必须同报告披露。

本候选算法、样本及停止分支已给出，不将这些选择留给实施方。数据资格、真实来源和既往观察披露属于未来门禁的待验证事实，不写成已经通过；缺口可诚实完成个案记录。新增事件、改模型/窗口/输入身份或把报告接入机器决策属于新范围，不在结果好坏后自动启动。本文及旧产物保持各自批准边界，本次仅新增此 Design。
