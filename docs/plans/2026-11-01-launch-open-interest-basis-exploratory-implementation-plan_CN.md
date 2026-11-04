# 新合约早期持仓量与基差探索 Implementation Plan

**状态：** `plan_candidate`，待独立审查及用户批准；本文件不授权实现或运行。

**Goal：** 实现获批 Design 的单次历史描述研究，比较 OI 数量变化与后续价格路径，明确基差、时效假设、缺口和 Parent 层限制。

**Design binding：** `docs/designs/2026-11-01-launch-open-interest-basis-exploratory-design_CN.md`，SHA-256 `82dd58310d7f2377c23eac7606a2cf74ec038c9b96b84436dd6a5af2826aa00f`。

## Allowed Change Scope

| 类别 | 范围 |
| --- | --- |
| Allowed implementation paths | 新增 `src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py`；新增 `scripts/external_signal_shadow/run_launch_open_interest_basis_exploratory.py`。 |
| Allowed verification paths | 新增 `tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py`；新增 `tests/scripts/external_signal_shadow/test_run_launch_open_interest_basis_exploratory.py`。 |
| Allowed documentation paths | 无；已批准 Design 和 Plan 保持原字节。 |
| Allowed generated/runtime artifacts | 默认仅测试 `tmp_path` 与临时执行记录；另经用户明确授权后，才在授权的新目录写入探索性 `child_rows.csv` 与 `review_CN.md`。不得覆盖已有输出或写入上游 root。 |
| Affected but unchanged | J-A/J-B/J-C 上游源码、根及契约、分类 ledger、上一研究源码与输出、`configs/base.py`；以基线状态、必要身份校验和相关测试验证。上一研究 `child_rows.csv` 禁止作为本次机器输入，除非另行解决其既有消费边界；本 Plan 不授权改变该边界。 |
| Forbidden | 白名单外修改、批量格式化、删除/清理既有文件、修改配置或上游产物；无单独授权的联网、真实数据消费与研究运行；git add/commit/push、部署、SSH、signal、paper、live、execution。 |

架构保持最小：一个研究模块、一个入口、对应测试；优先复用既有**公开且与本次契约兼容**的 loader/validator，不修改上游或引用私有 reader。上一研究的单次授权仅覆盖旧研究，不得沿用；发现上游冻结契约不兼容则按 Rule 16 停止，而非复制或绕过权限链。探索性输出只供人工阅读，不授予旧 Rule 17 profile、机器消费或交易权限；独立手算与结构检查足够，不新增专用 verifier、Recorder 或状态机。

## Task 0：授权与基线

**依赖：** 本 Plan 独立审查通过及用户明确批准。**不变量：** `INV-01`、`INV-02`。**文件：** 无仓内修改。

1. 对照用户实际批准语句核验 Plan 路径及 SHA-256，并核验上面的 Design 路径与 SHA；不一致或批准缺失立即 `STOP=approved_authority_mismatch`。不得从文件本身推定用户批准。
2. 记录 `BASE_SHA`、已暂存/未暂存 diff、未跟踪路径及其文件哈希或符号链接目标于新建临时目录。核对四个预定新增路径均不存在；存在即停止，不覆盖用户文件。记录已有 Design/Plan 的基线状态，不当作执行期新增文件。
3. 静态核验 J-A/J-B 与 [J-C 上游消费契约](../designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md)及分类 ledger 身份；`RISK_LIVE_TRADING_ENABLED` 必须为 false。读取契约不等于批准消费，禁止调用真实历史 strict loader 或打开 raw ZIP。用户实施批准只允许白名单内开发与测试，不授权网络、真实上游准入或研究归约。

验证并记录实际 RC：

```bash
git rev-parse HEAD
git status --short --untracked-files=all
git diff --binary
git diff --cached --binary
shasum -a 256 docs/designs/2026-11-01-launch-open-interest-basis-exploratory-design_CN.md
shasum -a 256 docs/plans/2026-11-01-launch-open-interest-basis-exploratory-implementation-plan_CN.md
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -c 'from configs import base; assert base.RISK_LIVE_TRADING_ENABLED is False'
```

预期各命令 `RC=0`，Plan SHA 与用户语句、Design SHA 与 binding 分别一致；另对未跟踪路径逐个记录类型及 SHA。不得将大文件数据目录纳入复制；任何无法确认的基线或上游权限保留未验证状态。

## Task 1：单事件时间、OI 与路径

**依赖：** Task 0。**不变量：** `INV-02`、`INV-03`、`INV-04`、`INV-06`。**文件：** 研究模块、研究测试文件。

以公开纯计算接口先写测试并运行 RED，再实现 GREEN；所有输入均为测试本地合成数据，独立手算期望，不触及真实历史。按 Design §3 实现 `D=T0+15m`，5m 主余量和 1m/3m 敏感性，`L0/L1` 两点均不早于 T0、间隔恰好 5m、正数及同 symbol/单位；独立计算 `floor_5m(T0)` 对照且不加入主分组。对重复、缺包、无对、非正数区分原因，不插值。

时间语义由输入携带可核验的截止时间或可信上界及来源；无法确认其不晚于 D 则对应比较为 `evidence_insufficient`，不得把标签或固定余量当作实际发布证据。无论是否可算，显式记录 `available_time` 未验证、所用假设和标签年龄；不能暗示实时可执行。基差必须同目标合约/可核验指数映射、相同自然分钟和兼容单位；未知映射或无指数时仅基差缺失。

选择顺序必须可测试：先按时界选择最新 `L1`，再检查 `L0=L1-5m` 是否满足下界、存在且有效；不得在前驱缺失时回退搜索更早的完整对。基差先要求两个 bar 同一自然分钟、身份映射正确且 `bar_end <= D-1m`，再取最新合格配对。增加 `test_time_oi_latest_missing_predecessor_no_fallback`：同时提供较早完整对与缺前驱的最新 L1，期望缺失；增加 `test_basis_bar_end_cutoff_selects_older_pair`：提供较新但超时界和较早且合格的同分钟配对，期望选择较早配对。两个测试均通过公开计算接口及独立固定期望验证。

冻结 `[T0,D)` 的价格变化、成交额及主动买入成交额占比；`[D,D+5s]` 第一笔 entry、`entry_delay_ms`，`E=entry_time+15m`、`[E-1s,E]` 最后一笔 endpoint，严格按时间/ID 计算 terminal、含 entry 的 MAE/MFE；非正数、倒序、重复 ID 等不得静默填零。跨 UTC 日缺包须标记缺口，输入声称存在而损坏则拒绝。

独立向量至少包括：`T0=1000ms`、`D=901000ms`、标签 300000/600000ms、OI 100/150，主 OI 变化 `0.5`；标签 0 在主口径排除但可用于网格对照；上界晚于 D 或未知不得产出领先比较。entry 100、终点 110、路径最低 90 最高 120 应得 `0.1/-0.1/0.2`；边界测试覆盖 D、D+5s、D+5s+1ms、E-1s、E 和 E+1ms、同毫秒 ID 顺序。测试还须覆盖错配指数、1m/3m/5m、时间未知、跨日及缺失不影响无关基差/OI 的状态。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py -k 'time_oi or basis or path'
```

记录因功能缺失产生的 RED 和最终 GREEN；预期 GREEN `RC=0`，不得以导入错误冒充行为 RED。

## Task 2：分组、Parent 与敏感性

**依赖：** Task 1。**不变量：** `INV-02`、`INV-04`、`INV-05`、`INV-06`。**文件：** 同 Task 1。

先测试后实现：保留全部 Universe 和缺口，各机制仅以 OI 与路径完整的 child 的事后中位数分组，`>` high、`<=` low；Parent 仅在该 `(parent_article_id, listing_regime)` 的所有选入 child 均完整时，以 child 中位数形成各指标后单独重分组、等权统计。相同 Parent 跨机制仍为一个公告簇，另统计 UTC 日期。输出 terminal/MAE/MFE 的均值、中位数、极值、nearest-rank P25/P75；偶数中位数为两中间值平均。

主场景逐个删除 Parent 并重算中位数和 high-minus-low terminal 均值差，记录被剔除 ID、剩余及两组数量；空组为 `null`。1m/3m 场景各自重新分组并输出 Design 指定的分母及终点差，不按结果选主场景；网格对照仅报告逐事件变化、覆盖及缺失，不混入主分组。用独立向量：三个 Parent OI 为 `1/4,1/2,3/4`，terminal 为 `0.1,0.2,0.4`，原差 `0.25`；删除第三个后差 `0.1`。覆盖平局、空组、多 child 不完整及跨机制 Parent 去重。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py -k 'parent or sensitivity or grouping'
```

记录行为 RED 和 GREEN，预期 GREEN `RC=0`；输出不得声称预测、净 PnL 或统计显著性。

## Task 3：准入、归约和人工报告

**依赖：** Tasks 1–2。**不变量：** `INV-01` 至 `INV-06`。**文件：** 四个白名单路径。

1. 入口默认拒绝历史消费；未核对单次用户授权时，必须在真实 loader/raw 调用之前停止。单次授权须明确 Plan/Design 身份、只读输入根和身份、允许的操作、独立新输出目录及权限；授权文件本身不证明用户身份。已获批准的旧研究授权不可复用。用户实施批准不等于历史运行批准。
2. 实现受控只读适配，使用已批准的 J-A/J-B 公共 strict loader 和 ZIP validator、已验证的 ledger 唯一键/锚点及对应日期包；先完成适用的上游 admission，按真实 source topology 验证，不能假设旧 CLI 的单次授权可供新 consumer 使用。分类 ledger 严格核验 J-C 冻结 SHA-256 `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b` 和其 §4.1 定义的 12 列精确结构、联合键及分类字段；不得仅依赖联合键。raw 逐包有界读取并检查来源、身份、跨日、CRC、顺序；拒绝损坏数据，业务缺包保留分母。读取权限或上游契约不兼容时停止并按 Rule 16 路由。
   AggTrades 底层读取和含换行的物理 CSV 行均遵守已冻结的 `EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES`（65,536 bytes），导入具名常量而非新增配置；在完整超长行进入内存前检测并拒绝，ZIP 元数据预检不能替代该检查。不得导入 J-B 私有 reader 或为此修改上游。
3. OI metrics、mark/index 文件须记录来源、哈希、symbol、单位、标签和覆盖；信息时间依据及其可信上界需可追溯到具体来源/版本/适用范围。仅有文件标签或来源不明的固定延迟不足以证明上界。无法核实上界时不得进行相应 OI 领先比较，标注 `evidence_insufficient`；不得通过用户授权绕过时间语义。产品映射不明时基差缺失。数据下载或扩展覆盖不在实施授权内，须另行明确授权。
4. 人工报告与逐 child 明细记录输入身份、协议、缺口/分母、延迟假设、全部场景、Parent 聚类及 LOO、日期集中、不可交易结论。输出目录在授权路径上排他创建，检查祖先与输入根，拒绝碰撞或覆盖；异常时不得报告成功或污染上游。无默认持久数据目录、机器消费契约或新增 verifier。

输出隔离在创建前检查祖先符号链接和解析后的物理路径，禁止输出等于受保护输入 root、位于其内部或为其祖先；最终目录排他创建，存在即拒绝。禁止通过符号链接祖先绕过检查；测试中允许 `tmp_path` 下独立模拟受保护根。

先用 `tmp_path` 写并验证公开入口负向行为：无授权不调用 loader、目录碰撞不覆盖、无时间上界不产生领先比较、错误映射基差缺失但不删除 OI、缺包与损坏区分及样本守恒。新增保持 `(parent_article_id, symbol)` 不变而仅修改 `listing_regime` 的 ledger 副本测试，证明冻结 SHA 不符时拒绝；新增超长物理行测试，证明在完整读取前非零拒绝且无成功结果；新增输出祖先符号链接指向临时受保护输入根的测试，证明拒绝且根内无写入。

正向跨边界兼容不得以手写结构伪装上游：J-A/J-B 使用真实权威上游构造器/strict loader；OI、Mark/Index 外部来源须在另行授权后，使用实际来源文件验证真实字段、单位和时间标签并记录来源身份，文件哈希本身不证明字段语义或信息截止时间。无法取得真实来源时标记 `historical_validation_not_authorized` 或 `evidence_insufficient`，不得声称实际来源兼容已通过；访问受限冻结根的测试缺少单独授权须显式 skip 并记录，不计作正向通过。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/scripts/external_signal_shadow/test_run_launch_open_interest_basis_exploratory.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py
```

预期合成/拒绝路径 `RC=0`；记录实际 pass/skip。需真实上游的正向断言未获授权时只能报告 `historical_validation_not_authorized`，不得宣称真实端到端已验证。

## Task 4：独立运行门禁与收尾

**依赖：** Tasks 0–3 的实现和离线测试；实际数据准入/研究还需独立授权。**不变量：** `INV-01` 至 `INV-06`。**文件：** 无额外仓内修改。

实施方整理实际文件及测试 RC、输入/输出边界、数据语义证据和缺口；若时间上界证据缺失，明确停在 `evidence_insufficient`，不以实施完成掩盖研究未能执行。若用户另行明确授权网络、真实准入或单次运行，执行者须先匹配实际授权内容、根和输出；正向通过及单点变异仅修改临时副本。全部归约仅在授权包含该操作时执行；只批准准入测试不等于批准全量研究。数据来源不满足冻结设计则停止，禁止自行改变窗口或结论等级。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py tests/scripts/external_signal_shadow/test_run_launch_open_interest_basis_exploratory.py
.venv/bin/ruff check src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py scripts/external_signal_shadow/run_launch_open_interest_basis_exploratory.py tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py tests/scripts/external_signal_shadow/test_run_launch_open_interest_basis_exploratory.py
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
git diff --check "$BASE_SHA"
git diff --cached --name-status "$BASE_SHA"
git status --short --untracked-files=all
```

记录各进程实际 RC，前四项预期 `RC=0`；逐项比对 Task 0 快照、已提交/暂存/未暂存/未跟踪变更和白名单，不把预存未跟踪文件误认成本次变更。独立会话执行 completion audit；`implementation_ready`、测试通过不等于真实数据门禁或研究已完成，`complete` 也不授予 commit、部署、网络、paper/live 或 execution。

## 不变量映射与审查

| Design 不变量 | 任务 / 最小证据 |
| --- | --- |
| `INV-01` | Task 0、3、4：批准身份、禁止越权、授权前拒绝与受控输出。 |
| `INV-02` | Task 0–3：Universe 守恒、child/Parent 与缺口测试。 |
| `INV-03` | Task 1、3：独立时间边界向量、信息截止上界及未知时停止。 |
| `INV-04` | Task 1–3：手算 OI、路径、产品映射、单位、跨日与缺失。 |
| `INV-05` | Task 2–4：分布、三个余量、Parent LOO 和探索性声明。 |
| `INV-06` | Task 1–3：公开接口独立期望、Rule 15 分级、实际上游正向证据另行授权。 |

Rule 16：白名单内缺陷就地修；仅路径扩大先申请有限 Plan 增补；修改研究语义、上游契约或权限即停止并回到 Design。Plan 候选需独立审查与用户明确批准，未经批准不得实施；本 Plan 不授权未来真实数据消费、下载或研究运行。
