# 新合约上线后主动买入占比与剩余价格响应探索 Design

**日期：** 2026-10-31  
**状态：** `design_candidate` / `hypothesis_only`；待独立评审和用户批准。  
**权限：** 本文件仅为设计候选，不授权实现、消费上游数据、历史回放、网络、receipt generation、交易、commit、push、部署或 SSH。

## 1. 目标与决策

研究一个描述性问题：**合约首笔成交后的前 60 秒，主动买入成交额占比不同的历史事件，在假设延迟后的 15 分钟内，价格变化和不利价格路径是否呈现值得进一步研究的差异？**

经济机制假设：集中主动买入可能反映短时需求压力；但它也可能与流动性稀薄、换手或价格透支同时出现，因此方向和持续性均未知。该阶段只研究历史关联，不证明因果、可预测性或可交易收益。

方案取舍：不从 J-B 汇总推算首分钟特征；不构建多指标、多个窗口和阈值的择优搜索；采用单一特征、单一主观察点和单一主评价窗口。Ponytail 原则要求最小实现，但不以 200 行作为删除必要校验与测试的硬上限。

## 2. 既有证据与边界

- [J-C Design §5](2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md) 将自身限定为历史价格空间与首次触及诊断，不输出策略胜率或显著性。其 60 秒观察、3 秒假设延迟、−2% 风险线和 +30% 目标线不是经过验证的交易参数。
- 既有 J-C universe 是 71 个确认分类的 crypto child：18 个 `pre_market`、53 个 `standard`；其中有上游缺口。它们不是 71 个独立 Parent，且不能把 280 个归档包当作 280 个研究样本。具体分母须在准入后重新核对，而非以本段代替检查。
- 本设计提出新的、曾被用户明确要求的条件性信息假设，不重跑或篡改 J-C 冻结场景，也不撤销已有路线停止决定。旧样本与既有结果已被反复查看；本研究不构成独立预注册或样本外验证。
- `AggTrades` 是聚合成交，不包含历史订单簿、撤单、排队、买卖报价和真实成交执行。主动买入占比不是完整的盘口 `order flow imbalance`，也不能识别机构身份。
- 现有根位置、输入身份及 frozen authority 以 [J-C Design §2、§4](2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md) 和 J-A/J-B 上游批准契约为准；当前 Design 草拟时没有重跑上游、验证 ZIP 覆盖或 VPS 状态。`RISK_LIVE_TRADING_ENABLED=False` 是本地配置事实，不代表 VPS 实时状态。

## 3. 研究口径

### 3.1 Universe 与独立单位

沿用 J-C 分类 universe：`asset_class=crypto`、`classification_status=confirmed` 且 `listing_regime` 属于 `pre_market` 或 `standard`。以 `(parent_article_id, symbol)` 唯一识别 child；同 symbol 的其他公告不得借用。两个机制分开报告，不因成交数据可得性或收益表现筛选 universe。

逐 child 输出明细；独立机会以 `parent_article_id` 为基本聚类单位，同 Parent 多 child、两个组或多个指标均不产生额外独立机会。跨 Parent 的同日共同冲击仍可能存在，记录 UTC 日期和集中度，不声称 Parent 间完全独立。

### 3.2 主场景与时间

所有时间使用 UTC Unix 毫秒。`T0` 为 J-B 已准入首笔成交锚点，必须由对应 raw 成交重证，不以计划上线时间替代。

| 定义 | 固定规则 |
| --- | --- |
| 特征窗口 | `[T0, T0 + 60s)`；不含第 60 秒及以后成交，含 T0 本笔。 |
| 观察和延迟 | `T_obs = T0 + 60s`；`T_decision = T_obs + 3s`。3 秒仅是假设，并非实测延迟。 |
| 入场参考 | `T_decision` 至 `T_decision + 1s` 闭区间内按成交时间、ID 顺序的第一笔；无则 `entry_unavailable`。这不是可成交报价。 |
| 主终点 | `T_end = entry.timestamp + 15min`，即实际参考成交后持有 15 分钟；不是 J-C 的 `T0 + 15min`。 |
| 终点参考 | `[T_end - 1s, T_end]` 内最后一笔；无则 `endpoint_unavailable`。不插值、不得用下一笔未来成交。 |
| 路径 | 从 entry 记录起，至 `T_end` 为止按原始顺序的成交；entry 同毫秒但排序在其前的记录不得计入。 |

先冻结口径再运行，不把 30 秒、180 秒、1 小时等作为本次次要参数网格。测量每个窗口实际成交量与时间间隔，稀疏交易不能解释为稳定报价；本阶段没有实测网络或订单执行延迟。

### 3.3 特征和价格响应

对特征窗口内每笔 `price=p_i`、`quantity=q_i` 的有效正数成交，`notional_i = p_i × q_i`。对本研究 USDT 合约，以该成交额作为统一权重：

```text
total_notional = sum(notional_i)
taker_buy_share = sum(notional_i where is_buyer_maker == false) / total_notional
vwap = sum(p_i * q_i) / sum(q_i)
vwap_deviation = last_feature_window_trade_price / vwap - 1
```

`false` 表示买方不是 maker，即该笔为主动买方；不得反转方向。窗口为空、总数量或总成交额非正时特征不可用，不填零。`total_notional` 与 `vwap_deviation` 仅描述，不参与分组、筛选或组合信号。VWAP 偏离不称为“已站稳”。

以 `Pe` 为 entry 参考价格、`P_end` 为终点参考价格，对完整路径计算：

```text
terminal_return = P_end / Pe - 1
long_mae = min(P / Pe - 1)     # 路径含 entry，值 <= 0
long_mfe = max(P / Pe - 1)     # 路径含 entry，值 >= 0
```

以上是未扣成本的价格响应，不是策略收益、可成交利润或止损成交。主分析只使用多头价格方向作统一描述，不做事后多空择优；负收益不等于已验证的做空收益。成交金额与比值使用明确的十进制或等价精度，分组和比较使用未展示舍入值。

### 3.4 分组与汇总

分别在每个 `listing_regime` 中，对**本组特征与路径均完整**的 child，取其 `taker_buy_share` 的样本中位数作为描述性分界：严格大于中位数为 `high`，小于或等于中位数为 `low`；相同数值不拆分，某组为空则如实报告。中位数使用完整历史样本，是事后描述边界，**不是历史当时可用的交易阈值或 80% 信号**。报告筛选前后数量和样本全体特征分布。

逐 child 分别报告两组的样本量和 `terminal_return`、`long_mae`、`long_mfe` 的均值、中位数、最小值、最大值、P25/P75；分位数采用 nearest-rank，偶数中位数取中央两项均值。附上 Parent 数量及每个 Parent 的 child 构成，避免 child 数混作独立样本。

补充 Parent 层：以 `(parent_article_id, listing_regime)` 为一组，仅当该组所有选入 universe child 均完整时，以该组 child 的 `taker_buy_share` 中位数和三项结果的 child 中位数作为描述值；对完整 Parent 组的特征按本机制的 Parent 中位数划分 `high/low`，严格大于中位数为 `high`，小于或等于中位数为 `low`，等权汇总。该聚合是描述而非可交易组合，同一 Parent 跨两个机制或 UTC 日仍只有一个公告簇。若某分组为空或独立 Parent 少到无法有意义描述，标注 `evidence_insufficient`，不补样或改阈值。

报告单个 Parent 对均值差异的影响：分别在每个机制下，以 Parent 层 `terminal_return` 的 `high` 组均值减 `low` 组均值为原始差异。按 Parent ID 逐一做 leave-one-parent-out：每次删除该 Parent 在本机制中的完整 Parent 组，使用剩余组重新计算本机制 Parent 特征中位数、按上述相同规则重新分组，再计算差异；不按效果选择剔除对象。逐次记录被剔除的 Parent ID、剩余完整 Parent 总数、两组数量和差异；无剩余 Parent 或任一组为空时差异记 `null`。报告原始差异、全部逐次结果及非 null 差异的最小值和最大值；若无非 null 差异，范围为 `null`。这是重新分组后的敏感性描述，并非固定原分界的贡献分解，也不对 `long_mae`、`long_mfe` 计算此差异。涉及多个机制、多个汇总视角均需完整报告，不作显著性或胜率结论。

## 4. 输入、输出与数据缺口

### 4.1 上游与消费权限

- 输入为经准入的 J-A replacement root 原始归档、J-B verified root 的 child/anchor 及 V2 分类 ledger；不用 J-C `validation_only` 临时 root 作为正式输入，不重生成或修改任何上游产物。
- J-A/J-B 的既有冻结契约对下游 consumer 和历史消费有独立授权边界；公开 loader 可调用不等于已有消费权限。独立 Design/Plan 的批准不自动授权历史运行或 receipt generation。实施 Plan 必须明确该新 consumer 的只读准入方式、适用上游条款和所需的单次运行授权；无法证明兼容时停止并报告，不擅自复制或绕过 J-C 的授权链。
- 正向输入身份和验证使用上游公开 strict loader 与 `validate_zip_archive_package` 等已获准接口，并核对上游 manifest、校验和、ledger 联合键和 anchor；不得导入 J-B 私有 reader 作为公共契约，也不得以合成 fixture 冒充真实上游兼容证据。
- 逐包流式读取；按上游记录确认 Parent/symbol/UTC 日期及完整性。`entry.timestamp` 在 `[T0+63s, T0+64s]`，所以 `T_end` 在 `[T0+16m03s, T0+16m04s]`，比 J-C 旧终点 `T0+15min` 晚，但早于 `T0+1h`，仍可能跨 UTC 日。若同一事件 `[T0,T0+1h]` 的日期包覆盖已通过可信验证，可作为本研究所需日期包覆盖的初筛依据；不得据此省略物理 ZIP、身份与完整性、时间序列、入场参考和终点参考成交的独立核验。不得假设所有事件 ZIP 均已覆盖，也不下载或借用其他事件的包。

### 4.2 缺口与失败

保留全部 universe 分母，逐 child 记录至少 `upstream_gap`、`anchor_unavailable`、`feature_unavailable`、`entry_unavailable`、`required_package_unavailable`、`endpoint_unavailable`、`sequence_gap`、`complete` 及对应原因。分类是质量状态，不是收益。相邻 aggregate ID 间断记 `sequence_gap`，不推断成确定的交易所故障；缺少的路径不进入完整结果，特征可得时可单独描述，不填零。

上游身份不一致、哈希/内容校验失败、记录顺序倒退、非法 CSV 或异常资源消耗等属于完整性/安全错误：停止当前运行，不将其伪装为普通缺样或生成成功结论。上游已明确不存在的日期包是业务缺口；宣称存在却不可验证的包是错误。结果应明确各状态、child/Parent 的数量及潜在选择偏差。

### 4.3 输出与生命周期

未来运行仅产生独立的探索性逐 child 明细与人类可读汇总；必须记录输入身份、协议、分母、缺口和计算版本。输出不授予下游消费或任何运行权限，不覆盖上游、J-C 或既有证据；若未来拟供其他程序或阶段消费，须先定义并验证相应产物契约。作为单次可重算研究输出，按现行 Rule 17 做结构检查和独立手算语义验证，不默认新增独立 verifier、封闭树、专用 Recorder 或恢复状态机；不得以此覆盖上游冻结义务。

## 5. 结论等级、停止与安全

| 项目 | 本阶段约束 |
| --- | --- |
| Claim | 仅描述 `exploratory` 的历史关联或 `evidence_insufficient`；不声称统计因果、方向预测力、`alpha_candidate` 或 `alpha_validated`。 |
| 成本、流动性与容量 | 无历史盘口与真实成交，不计算伪精确净 PnL；手续费、点差、滑点、市场冲击、资金费率、容量与拒单属于后续可执行性研究。 |
| 损失与集中度 | 保留完整终点分布、MAE/MFE、逐 Parent 敏感性；不把 MAE 当成止损成交或资金最大损失。 |
| 条件策略 | 不声明可实时使用样本中位数、不设置买入阈值、止盈止损、仓位或方向信号。 |
| 晋级 | 正向历史差异仅能提出下一项独立、事前冻结的假设，并以未来未参与选择的新事件评估；不自动晋级策略、实盘或影子执行。 |
| 停止 | 证据明显不足、观察差异对单一 Parent 高度敏感、或新增资源不值得投入时，可停止此研究工作包；不把探索性不佳自动写成对所有策略的 `falsified`。 |
| 交易与运维 | `signal/paper/live/execution/network` 均不获本 Design 授权；不修改风险配置，不进行 VPS 操作。 |

## 6. 验收、不变量与后续批准

未来实施须满足：

1. `INV-01`：原 J-A/J-B/J-C 数据、协议及权限不变；未经适用的消费和运行授权不得读取归约历史 raw。
2. `INV-02`：预定 universe 守恒，缺口原因不丢失；Parent 不因 child 数、方向或分组膨胀。
3. `INV-03`：特征仅用 `[T0,T0+60s)`，entry 在延迟后，终点为实际参考 entry 后 15 分钟；不借用未来价格或跨事件数据。
4. `INV-04`：买卖方向、成交额、VWAP、同毫秒顺序、组边界、缺失和终点采用可复核规则；正向上游契约用真实合规字节验证，纯计算测试可用手算合成样例。
5. `INV-05`：报告两机制全部组别、child/Parent 数及缺口，保留全部样本；不把 hindsight 中位数当 PIT 交易信号，不作策略收益或显著性声明。
6. `INV-06`：验证覆盖手算的买卖方向、加权金额/VWAP、时间边界、entry/endpoint、跨日缺包、分组相等值及 Parent 聚合；对 Parent 敏感性验证逐次重算分界、空组为 `null` 和分母记录；包含至少一条具备上游来源的正向准入证据和独立语义核对。

后续依次进行独立 Design Review、用户明确批准 Design、Implementation Plan 及其独立 Review、用户明确批准 Plan，然后才可实施。实际消费或运行还须满足上游契约及对应用户授权；批准本 Design 或 Plan 不自动授予这些权限。

**开放核验项：** 本次只拟定研究协议；实施 Plan 必须在消费前逐项解析现行 J-A/J-B 冻结契约和 consumer 授权路径、所需日期包与 root 身份。若上游契约不允许本文所述新 consumer，或 15 分钟窗口不能得到可验证覆盖，应先停止并反馈，不以实现便利改变事实或扩大权限。
