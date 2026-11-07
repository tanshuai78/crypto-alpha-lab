# 新合约价格状态与 OI／基差增量信息有限探索 Design

**日期：** 2026-11-04。**状态：** `design_candidate / hypothesis_only`，待独立评审和用户明确批准。

**权限：** 本次仅起草 Design；不授权 implementation、真实数据消费、研究运行、联网、下载、commit、push、部署、SSH、signal、shadow 策略、paper、live 或 execution。

## 1. 目标、事实与投入取舍

只回答：**已知观察前价格变化后，OI 是否仍对后续终点收益提供描述性的增量信息？基差能否在实际可用子集中进一步增加信息？** 经济动机是区分价格已经表现出的状态与持仓、相对定价可能带来的额外解释；OI 不标识交易者身份或净多头流入，相关性不证明因果。当前阶段不回答怎样买到所有暴涨币。

上一项 [OI 父 Design](2026-11-01-launch-open-interest-basis-exploratory-design_CN.md)、[时间假设 Delta](2026-11-02-launch-open-interest-scenario-assumptions-design-delta_CN.md) 和 [实施 Plan](../plans/2026-11-02-launch-open-interest-scenario-assumptions-implementation-plan_CN.md) 已形成历史探索输出。已查看的快照有 71 个 child、60 个 Parent；主情景完整 69 个 child、59 个 Parent，两个机制各有不同数量；基差仅部分覆盖。这些是旧快照事实，不保证新运行已获授权或来源真实性已完全认证。历史赢家、收益和若干单因子结果已被反复观察，本文不是独立预注册，不得重新命名旧样本为未见数据。

参照 [治理效果复盘](../reviews/2026-11-04-governance-simplification-follow-up-assessment_CN.md)，比较三种路径：只复述已有边际分组无法回答条件增量；重建原始数据链会重复已有工程；**优先申请对精确结果快照的受限分析消费**，只新增表格计算与独立测试。本轮不下载、不扩 Universe、不增加时间窗口、不重构旧模块。即使没有发现候选关系，也可以完成研究；若实现需要新的数据管道或大规模适配，先报告成本与替代方案，不自动扩建。

## 2. 输入与新增消费边界

旧产物只供人工阅读及复核，不能默认作为新机器输入。**本文申请的唯一新增边界**是：独立评审通过、用户明确接受此边界，且后续 Plan 获批并取得指定单次运行授权后，允许本研究 consumer 只读以下精确快照，用于本文规定的历史统计；不改变旧文件、旧批准或其对其他 consumer 的限制。若用户未接受此受限例外，停止本消费路径，不擅自修改父 Design、不通过改路径绕过，也不自动切换到 raw 全量重放。

| 对象 | 精确身份及用途 |
| --- | --- |
| 输入 CSV | `/private/tmp/launch_open_interest_basis_exploratory_run_20261103/child_rows.csv`，SHA-256 `56afc76bc30dea5b8d0414e320e2d49842ed3b137c4e0bf37c6dca51ce9447c4`；本研究唯一数值输入。`/tmp` 别名须解析到同一物理文件。 |
| 配套旧报告 | 同目录 `review_CN.md`，SHA-256 `af4e277728cdabbb5cb4c8e9abf0da6722b001470a66a6c256034e67cc6104dd`；仅核对协议、状态和身份，不从 Markdown 表格抓取特征或结论。 |
| 旧契约身份 | 父 Design SHA `82dd58310d7f2377c23eac7606a2cf74ec038c9b96b84436dd6a5af2826aa00f`；Delta SHA `7941e641437ad20f4aee96be4b3ff65e7f97503d5d3f8693fdce81c29db55b54`；旧 Plan SHA `256541023e83bbf063b78b0bd84259de73e3dd05268d0b1e924d38eabf2d53d1`。只追溯，不继承旧运行授权。 |

consumer 在建模前验证输入哈希、必需列无重复且每行字段数匹配、联合键 `(parent_article_id,symbol)` 唯一、机制及下表的状态/数值一致性；不能因哈希匹配就跳过语义检查。最小字段契约依据当前旧 [canonical writer 与归约源码](../../src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py) 和上述精确 CSV 核对，不由新 consumer 猜测：

| 精确列名 | writer/归约来源与本 consumer 的含义 |
| --- | --- |
| `parent_article_id`, `symbol`, `listing_regime` | writer 的 `ChildEvaluation` 同名字段；前两项非空，机制只能为 `pre_market` 或 `standard`，它们定义 Universe 身份，不用 symbol 单独去重。 |
| `utc_date` | writer 写 `c.utc_date or ""`；正常归约由 J-B `anchor_time_ms` 派生 UTC `YYYY-MM-DD`，缺锚点时为空。Parent 日期再按 §3.1 归并，不拿空值推算日期。 |
| `oi_a_status`, `oi_a_change` | 情景 A 的 `OiResult.status` / `oi_change` 经 `ChildEvaluation.oi_a_status` / `oi_a_change` 写出；只有状态精确为 `ok` 且 change 为有限数才取得 A 的 OI 资格。 |
| `oi_b_status`, `oi_b_change` | 情景 B 对应字段；只有 `ok` 加有限 change 才取得 B 的 OI 资格。writer 可能从通用 B 别名回填，但 consumer 只读这两个显式 B 列，不自行 fallback。 |
| `oi_c_status`, `oi_c_change` | 情景 C 对应字段；只有 `ok` 加有限 change 才取得 C 的 OI 资格。不得用 B 的资格代替 A/C。 |
| `baseline_price_change` | `calculate_baseline` 的 `price_change`，即 `[T0,D)` 内按时间和 ID 排序的末笔价格除首笔价格减一；不是 4h 收益，也不是后续 `terminal_return`。没有另设 baseline 状态列，路径 `ok` 时此值必须为有限数。 |
| `path_status`, `terminal_return`, `long_mae`, `long_mfe` | `calculate_path_response` 的对应结果；路径 `ok` 时三个数都必须有限，分别为后续终点收益及相对 entry 的 MAE/MFE。只有 `terminal_return` 作目标，MAE/MFE 不作特征。 |
| `basis_status`, `basis` | 原归约的基差结果状态/值；只有 `ok` 加有限 basis 才取得基差资格。`unverified_product_mapping` 表示未取得可用产品映射，basis 必须为空，不解释为 0 或已验证的 HTTP 404。 |
| `is_complete`, `missing_reason` | writer 输出小写 `true` / `false` 和缺失原因；它们是旧 B 主情景摘要，不是所有情景的统一资格。核对 `is_complete` 与 B 的 OI/路径资格一致；不得据此过滤 A/C。 |
| `oi_status`, `oi_change` | 旧 B 通用别名；必须分别与 `oi_b_status`, `oi_b_change` 一致，数值按解析后值比较；不参与额外拟合或作为缺列 fallback。 |
| `pit_verification_status`, `interpretation_status` | writer 的同名字段；本快照必须分别为 `unverified_scenario_assumption` 和 `historical_scenario_only`，不得改成已验证 PIT。 |

本次作者核对：writer 定义的 99 列表头与快照的列名/顺序一致；`path_status` 和三个显式 OI 状态列均只有 `ok`（69 行）及 `missing_jb_anchor_time`（2 行）。后两行的上述 OI change、价格/路径数值、`utc_date`、`basis` 与 `basis_status` 均为空，`is_complete=false` 且 `missing_reason=missing_jb_anchor_time`；其余行 `is_complete=true` 且 `missing_reason` 为空。基差列有 `ok`（51 行）、`unverified_product_mapping`（18 行）和缺锚点时未执行基差计算的空状态（2 行）。这些是**指定快照的受限状态集合**，不是旧 producer 的全部枚举；不接纳其他来源版本或自动扩展状态集合。测试样例可改变行数，但须保持上述状态/数值关系；不得将这些观察数量当作测试夹具必须凑齐的门槛。

供离线复核的最小源码摘录如下，各行均来自上述 `write_exploratory_outputs`；省略号表示省略无关写出列，不是新 consumer 的 fallback。核对时源码 SHA-256 为 `ed9d68767d56f884f13b02cb5d323a602b8595518dc4c108577ee9092f5426be`，仅记录出处版本，不新增运行前读取整个源码的门禁。

```python
b_status = c.oi_b_status if c.oi_b_status is not None else c.oi_status
b_chg = c.oi_b_change if c.oi_b_change is not None else c.oi_change
# writer.writerow 中的情景状态/值片段：
c.oi_a_status or "",
f"{c.oi_a_change:.8f}" if c.oi_a_change is not None else "",
...
b_status or "",
f"{b_chg:.8f}" if b_chg is not None else "",
...
c.oi_c_status or "",
f"{c.oi_c_change:.8f}" if c.oi_c_change is not None else "",
```

每个情景的 child 完整资格固定为：该情景显式 OI 状态为 `ok`、`path_status=ok`，且该情景 change、`baseline_price_change`、`terminal_return`、`long_mae`、`long_mfe` 均有限、日期有效。缺锚点行保留 Universe 与原因而不纳入模型；基差空状态只允许出现在该缺锚点分支，不能冒充映射失败或成功。完整状态的必要值为空/非有限、缺失状态带有相矛盾数值、未知状态、别名不一致、身份冲突、哈希不匹配或 writer 与此字段映射无法对应时，均须在建模前非零退出；不得改上游 writer、补默认值或推断 `complete` 以继续。所有原始候选行留在分母中。快照中 OI 为数量相对变化，基差为价格比值，均不解释为 USDT 资金流入；只对快照已保存的数值精度负责，不声称恢复原始高精度。

这是派生快照研究，不重新认证官方 `.CHECKSUM`、历史 404、原始授权链、历史产品映射或 OI 实际发布时间；沿用并披露旧来源的不确定性，不将当前快照身份核对包装成完整旧 Rule 17 profile 验收。若发现已核实事实否定某输入语义，停止受影响比较并报告，不忽略事实继续。输入消失或身份变化时请求精确缺失 bytes，不自动下载或重新生成。

## 3. 冻结研究口径

### 3.1 时间、样本及 Parent

保持旧 Delta 的 `D=T0+25m`、A/B/C 总假定可用余量 5/10/15m、各自最新 L1 与固定 `L0=L1-5m`；本 consumer 不重选标签。价格特征仅用 `[T0,D)` 的 `baseline_price_change`；entry 为 `[D,D+5s]` 首笔参考成交，终点为 entry 后 15m，沿用旧 `terminal_return`、`long_mae`、`long_mfe`。不改变窗口、不用后续最大涨幅构造特征或筛选样本；特征时间约束是情景假设，真实 PIT 仍未验证。

两个 `listing_regime` 分开。对每个情景、每个 `(parent_article_id,listing_regime)`，只有全部选入 child 的该情景 OI、价格特征和后续路径均完整时才进入对应主分析。各数值取全部这些 child 的中位数；中位数以排序后中间值或两中间值均值定义。缺一个 child 不聚合剩余子集；保留 Universe、缺失数量与原因。Parent 是聚类单位，不把 child 当独立机会；跨机制相同 Parent 只算一个公告簇，同日期事件仍可能相关。

基差完整子集还要求该 Parent 的全部选入 child 都有有效 `basis_status=ok` 和有限基差值；取其中位数。缺基差不删除 OI 主分析，不按有利结果选择子集。每个机制/情景输出实际集合及交集，不预设必然保持旧 69/59 个完整样本。Parent 日期检查全部 child 的已知日期集合：唯一日期用该日期，无日期记 `unknown`，多个日期列明冲突及全部日期；Universe 与完整 Parent 日期统计分开，不取首个 child 替代。

### 3.2 有限比较：三个固定模型，不搜索参数

记 Parent 价格特征为 `p`、该情景 OI 变化为 `o`、基差为 `b`、终点收益为 `y`。仅使用带截距的普通最小二乘，不调超参数、不删极值、不变换为暴涨二分类。模型固定如下：

| 模型 | 设计矩阵列 | 要回答的问题 |
| --- | --- | --- |
| M0 | `1, z_p` | 价格自身提供的基准解释。 |
| M1 | `1, z_p, z_o, z_p*z_o` | OI 及唯一预设的价格交互项是否增加信息；允许不同价格状态下 OI 关联不同，不预先指定正负。 |
| M2 | `1, z_p, z_o, z_p*z_o, z_b` | 已知价格与 OI 后，基差是否进一步增加信息；不再增加基差交互项。 |

样本集合标识 `cohort` 固定为：`oi_complete` 是 §3.1 在各机制、各情景下形成的 OI/价格/路径完整 Parent 集合；`basis_complete` 仅用于 B，是对应 `oi_complete` 内基差也完整的子集。比较仅有下表三类，`comparison` 按“扩展模型 vs 基准模型”命名：

| scenario / cohort | comparison | 基准 → 扩展 | 用途 |
| --- | --- | --- | --- |
| A/B/C / `oi_complete` | `M1_vs_M0` | M0 → M1 | OI 增量；B 为主，A/C 仅作假设敏感性，不挑选胜出情景。 |
| B / `basis_complete` | `M1_vs_M0` | M0 → M1 | 重新在基差子集上评估 OI 增量，不能借用完整 OI 集合的拟合。 |
| B / `basis_complete` | `M2_vs_M1` | M1 → M2 | 基差在价格与 OI 之外的增量，直接基准必须为同一子集的 M1。 |

基差子集内重新评估 M0、M1、M2，禁止以 M2 对 M0 的混合增量冒充基差的独立增量，也不能拿完整样本 M1 与基差子集 M2 直接相减。即使两个集合恰好相同也保留不同 `cohort` 身份；无可用基差子集则该项 `evidence_insufficient`，不得填零。

`z` 在每次训练中用训练样本均值与总体标准差标准化，测试行只套用训练参数；交互项为 `z_p*z_o`，不再独立标准化。`y` 不标准化；不使用价格之外的成交额、主动买入占比、网格 OI、技术指标、其他持有期或机制内新子组。它们是明确延期项，不在本轮结果不好时自动加入。

### 3.3 增量与影响检查

采用 leave-one-Parent-out：每折留出一个 Parent，训练集合在全部机制中移除该 Parent；模型仍分别在各 `(regime,scenario,cohort)` 内拟合。所有标准化与估计只使用该集合的训练行，不跨 cohort 借用预测或标准化参数，不以留出收益选模型。使用现有 NumPy `linalg.lstsq(rcond=None)`；训练矩阵须满列秩且训练行数大于列数。必要特征训练标准差为零、矩阵不满秩或不可有限计算时标记该模型折 `not_estimable`，不加正则、不换模型补救。

对上表每个同集合模型对，保存每个留出 Parent 的实际收益、预测、误差与 `d_i=error_base_i^2-error_extended_i^2`；基准/扩展按上表取值，因此 `M2_vs_M1` 固定计算 `error_M1_i^2-error_M2_i^2`。`mean(d_i)>0` 只表示该内部检查的均方误差减小。两模型的均方误差、绝对误差中位数、有效/不可估数量及贡献诊断均按 `(regime,scenario,cohort,comparison)` 独立汇总。若任一应有折不可估，该模型对完整集合的增量汇总为 `null / not_estimable`，不得各自删折得到不同比较分母。无需 p-value、显著性筛选或净收益计算。

所有有效折贡献按 Parent 完整展示；列出最大三个正向贡献及去掉每一个已计算 `d_i` 后的均值范围。后者仅是**固定折贡献敏感性**，不重新训练，不称为重新拟合的 Jackknife。另报 Parent/日期集中度及 `y`、MAE、MFE 的 count、均值、中位数、min/max，保留极端值。不对 MAE/MFE 再拟合一套模型，也不将极端 MFE 作为可捕获利润。

这里的留出法只是同一已观察历史上的内部模型检查：其他折可含较晚日期，且研究者已看过历史；不是 walk-forward、未见样本或实际可用时点的交易预测。不同日期和机制的共同市场因素也没有被因果识别。

## 4. 结论、停止与延期

本轮成功标准是完成可复核的固定比较，而不是得到正结果。M1 无误差改善、改善集中于极少数 Parent、A/B/C 表现不稳定、基差子集不足或不可估时，如实报告并停止本轮扩因子；这些结果仅说明**本次具体方法没有提供稳健增量证据**，不能证伪所有非线性关系、OI 或新币研究。

若 B 有改善，报告改善幅度、A/C 结果、绝对误差和贡献集中度，而不是只宣布胜出。正改善、系数正负或情景方向一致均不自动晋级；最多提出两条与实际结果对应的后续机制假设，供未来独立事件预先定义验证。不得反过来围绕已知赢家扫描阈值、删异常、挑时间或更换主情景。

统一使用 `exploratory / historical_scenario_only / no_alpha_claim`；计算与覆盖不足用 `evidence_insufficient`，不可估单独列明。符合数据的历史现象可称 `phenomenon_supported`，但不可据此称为 `alpha_candidate`、因果、已验证 PIT 或可交易收益。L2 §15 的独立单位、时间与反事后选择、分布、尾部及集中度按上文执行；费用、滑点、资金费率、可成交止损、容量、仓位、资本存活和 live-safe 为 `N/A`，因为本轮不定义策略或净 PnL，全部留待另行批准的后续阶段。

## 5. 最小实现、产物和验收

候选架构是一个新分析脚本及其测试，复用 Python 标准库 CSV/哈希/路径检查和已安装 NumPy，不新增依赖；Plan 再给出精确文件白名单。旧 OI 模块、CLI 和已批准文档保持不变，不调用会重放 raw 并写旧报告的 `execute_exploratory_pipeline`，不将旧硬编码授权检查当成本任务许可。只复用契约兼容的公开能力，不新增通用模型框架、认证清单、Recorder、独立 Verifier、锁或恢复状态机。

单次运行仅在另获授权的新输出目录写 `parent_panel.csv`、`fold_diagnostics.csv` 和 `review_CN.md`。前者覆盖各情景/机制的 Parent Universe、所需/完整 child 数、OI/基差资格与缺失、日期及聚合值；后者以 `(regime,scenario,cohort,comparison,parent_article_id)` 为唯一键记录全部预期折和状态，同一 Parent 的 B 主集合折与基差子集折不得覆盖或混用；报告按相同 cohort/模型对区分主结果及补充结果，并列输入/代码/Design/Plan 身份、范围守恒、假设与局限。它们只供人工阅读和复核，不提供新的机器下游、运行或交易授权。按 Rule 17 使用基本结构检查及独立数值证据，不声称通过旧完整 profile。

运行前核对显式用户授权、本任务批准版本、精确快照身份和唯一输出目录；输出不能等于、包含或覆盖输入，拒绝既有目录和危险物理路径；只读输入、单写者、无并发 consumer。失败非零退出，缺口不是假成功；报告成功标记最后生成，中途中断的文件不能被当作完成。输出可重算，不要求断电持久化或多状态恢复。

| 不变量 | 验收证据 |
| --- | --- |
| INV-01：受限消费与零交易权限 | 未获本次消费/运行授权前拒绝；错误快照 SHA、旧任务授权或输出碰撞均拒绝，原输入前后不变。 |
| INV-02：Parent 与分母守恒 | 按 §2 的精确列名及状态计算各情景资格，不用 B 摘要代替 A/C；多 child 中一项缺失则对应 Parent 不入完整集合；缺基差不删主分析；跨机制同 Parent 无训练泄漏；日期缺失/冲突明示。 |
| INV-03：固定时间及假设等级 | 原窗口与 A/B/C 字段不改，后续收益不作特征；训练标准化不读留出行；报告不冒称 PIT 或前瞻验证。 |
| INV-04：比较方法唯一且同样本 | 独立代数样例验证 OLS、标准化、交互、平方误差增量与中位数；基差增量必须是同一 `basis_complete` 的 M2 对 M1；价格足以解释的样例不凭训练拟合改善冒称 OI 增量；零方差/秩不足折保留不可估状态。 |
| INV-05：完整输出与不挑结果 | 同一 B Parent 同时进入两种 cohort 时，独立核对各自训练集合、折唯一键及输出不碰撞；基差子集重算各模型，不借用主集合预测；保留所有预期折、极值和贡献；A/C 不替代 B；空集、缺口、不可估及非正改善都能正常报告。 |
| INV-06：正常入口可核对且实现受控 | canonical writer 字段/状态与 §2 契约对应，合成 CSV 经真实入口到三份输出，手算核对 Parent 值、cohort/模型对、折状态、误差和标签；重复键、必要列缺失、未知状态、状态与空值矛盾、B 别名不一致及单点损坏被拒绝。真实快照正向消费按本次授权单独验证，不以合成测试宣称来源真实性。 |

Rule 15 分层：本 consumer 内部合成表可证明计算与本入口接线，但不能自称旧 producer 兼容；跨边界正向样例须由旧 `write_exploratory_outputs` canonical writer 生成，或使用明确授权的精确快照 bytes，负向基于该来源作单点变异。Plan 应核实 canonical 路径可用性，不能手写来源签名绕过；合成测试、获授权快照兼容验证和实际研究完成分别报告，不为完成代码审计强求提前运行真实研究。

## 6. 审批与未决边界

本文所有算法选择均为候选，不是已运行结果。当前没有需要实施方自由决定的特征、主窗口、模型或成功阈值；来源真实性及真实发布时间仍属已披露的证据上限，不通过再建验证系统伪装解决。

下一步仅提交独立 Design Review，重点审查受限 consumer 例外是否可接受、比较是否足以回答该问题及方法能否独立复核。用户批准时须明确接受 §2 的精确快照受限消费边界；这仅确定拟实施契约，不授权实际消费。其后才能起草 Implementation Plan，经独立审核和用户实施批准后编码；真实快照消费与一次运行还须显式指定本任务 Design/Plan、输入路径与 SHA、全新输出根及禁止权限。旧运行语句不自动复用。

未经上述批准，不新增代码、不运行历史比较，不改风险配置；`RISK_LIVE_TRADING_ENABLED=False`。本文不改变治理规则，不重开 J-C 已关闭策略，不授予网络、signal、paper/live 或 execution 权限。
