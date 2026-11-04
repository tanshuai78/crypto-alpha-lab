# 新合约 OI 时间假设情景研究 Implementation Plan

**状态：** `plan_candidate`，待独立审查与用户批准；不授权实施、数据消费或运行。

**Goal：** 在既有研究代码上实现已批准的假设情景协议，优先删除可由兼容公开接口替代的重复准入逻辑；结果只供人工探索。

**Design binding：** [Design Delta](../designs/2026-11-02-launch-open-interest-scenario-assumptions-design-delta_CN.md) SHA-256 `7941e641437ad20f4aee96be4b3ff65e7f97503d5d3f8693fdce81c29db55b54`；[父 Design](../designs/2026-11-01-launch-open-interest-basis-exploratory-design_CN.md) SHA-256 `82dd58310d7f2377c23eac7606a2cf74ec038c9b96b84436dd6a5af2826aa00f`，按 Delta §3.1 覆盖。旧 Plan SHA-256 `3209f0a4dde7cb8aa82b27149fbc1fac5aaf684df2ea96cd9bdc8d2d0033eb65` 仅用于追溯；其批准不授权本 Plan，也不将旧实现或测试视为通过。

## Allowed Change Scope

| 类别 | 精确路径或边界 |
| --- | --- |
| Allowed implementation paths | `src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py`；`scripts/external_signal_shadow/run_launch_open_interest_basis_exploratory.py`。 |
| Allowed verification paths | `tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py`；`tests/scripts/external_signal_shadow/test_run_launch_open_interest_basis_exploratory.py`。 |
| Allowed documentation paths | 无；本 Plan、Delta、父 Design 和旧 Plan 的批准字节不得修改。 |
| Allowed generated/runtime artifacts | 实施期仅 `tmp_path` 和工作区外临时基线；实际研究仅另获用户明确单次运行授权后，在该授权指定的全新目录生成 `child_rows.csv`、`review_CN.md`。 |
| Affected but unchanged | J-A/J-B/J-C、上一项 taker-buy 研究源码/契约/产物、ledger、配置及上游数据；检查当前身份与公开接口，按适用授权验证兼容，不修改。上一研究的人类阅读结果不得擅自用于机器消费。 |
| Forbidden | 白名单外修改、全库格式化/清理、覆盖现有文件、修改风险配置或上游；未另行授权的下载、联网、历史数据消费和研究运行；signal、shadow 策略、paper、live、execution、部署、SSH、git add/commit/push。 |

架构：保留一个研究模块及一个 CLI；探索性输出仅供人工阅读，不继承旧 Rule 17 profile，不新增 Recorder、独立 verifier、封树或状态机。Plan 审批只允许白名单内实施和合成测试；真实 upstream 正向测试、来源下载及单次研究归约各须用户明确授权对应操作。

## Task 0：身份、现状与裁剪边界

**依赖：** 本 Plan 经独立审查且用户明确批准。**不变量：** `INV-01`、`INV-02`。**文件：** 无仓内更改。

1. 使用用户实际批准语句核对本 Plan 路径与实时 SHA；核对 Delta 和父 Design 与上述 binding。缺批准或不一致 `STOP=approved_authority_mismatch`，不可反向从磁盘推定授权。
2. 当前四个允许路径已存在、且为未跟踪的实施中工作，不视为可以覆盖的空文件。先在工作区外新建临时基线记录 `BASE_SHA`、HEAD、staged/unstaged diff、全部未跟踪路径及文件类型/内容 SHA、符号链接目标；包含四个目标文件和三个现存设计/旧计划。无法读取或状态在基线建立期间变化即停止，不删除、覆盖或重置用户文件。
3. 对照真实源码：上一研究公开 `build_admitted_ja_context` 和 `open_verified_package_stream` 使用 strict loader 返回的 package 原对象、manifest `relative_path` / `byte_count` 与 request linkage；当前本研究重复实现与其字段不一致。评估复用是否与上游授权及读取上限兼容；不运行历史 loader。若公开接口不可合法复用且正确修复需改白名单外文件，按 Rule 16 `BLOCKED_SCOPE_DRIFT`；若需改冻结语义或上游契约，`BLOCKED_SPEC_DRIFT`。不以 mock 冒充合法准入或擅自扩大白名单。

执行并记录实际 RC（期望各 `RC=0`）：

```bash
git rev-parse HEAD
git status --short --untracked-files=all
git diff --binary
git diff --cached --binary
shasum -a 256 docs/designs/2026-11-02-launch-open-interest-scenario-assumptions-design-delta_CN.md docs/designs/2026-11-01-launch-open-interest-basis-exploratory-design_CN.md docs/plans/2026-11-02-launch-open-interest-scenario-assumptions-implementation-plan_CN.md
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -c 'from configs import base; assert base.RISK_LIVE_TRADING_ENABLED is False'
```

基线快照还必须逐项记录未跟踪文件类型与 hash，命令输出不能取代快照；失败即停。保存用户批准语句与快照位置供独立审计，不生成或模拟历史运行授权。

## Task 1：单事件情景与价格路径

**依赖：** Task 0。**不变量：** 替换后的 `INV-03`、`INV-06`，父 `INV-04`。**文件：** 研究模块及研究测试。

先从公开接口写独立手算 RED，再实现 GREEN。以固定 `D=T0+25m`，情景 A/B/C 的标签可用余量分别 5/10/15 分钟、B 为主；这只是情景假设，既不能写入真实 `information_time` / `available_time`，也不能标记为可信上界或已验证 PIT。最新合格 L1 后只验 L1-5m 的 L0，两点同 symbol、同单位、正数、主口径均不早于 T0；缺前驱不回退。分别计算 `floor_5m(T0)` 网格对照，不并入主样本。来源存在已核实且与假设冲突的事实时停止受影响情景并报告；测试注入该事实，不将用户授权当证据。

独立向量：`T0=16:03`、`D=16:28`，完整自然网格标签下 A 的 `(L0,L1)=(16:15,16:20)`，B 为 `(16:10,16:15)`，C 为 `(16:05,16:10)`；对每情景等号与超界 1ms、缺前驱、重复标签、两点单位、无样本、`T0` 网格前标签和跨日进行测试。另验证原始 OI 字节/值不改变、输出明示各假设和真实可用性未知。

继承父 Design：`[T0,D)` 基线；`[D,D+5s]` 第一笔参考 entry、`E=entry_time+15m`、`[E-1s,E]` endpoint，分别测边界与同毫秒 ID。手算 entry=100、endpoint=110、最低=90、最高=120，依次为 `0.1/-0.1/0.2`。新最大读取终点为 `T0+40m05s`；跨日按该终点覆盖，缺包不改变 D，不从其他 child 借数据。基差必须可核验真实产品/指数映射和兼容单位，否则缺失，不改变 OI 样本资格。

基差时间选择继承父 Design：先只配对同一自然分钟的 Mark/Index，且该对 bar 结束时间 `<= D-1m`，再选最新合格对。独立负向向量固定 `D=16:28:00`，两组合规产品/单位配对分别结束于 `16:27:00` 和 `16:28:00`；断言选择前者，后者超界不得使用。另提供结束时刻看似可用但来自不同自然分钟的 Mark/Index，断言不得互相配对；无合格对时基差缺失，不删除 OI 样本。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q -p no:cacheprovider tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py -k 'scenario or time_oi or basis or path'
```

记录先失败的行为 RED 与 GREEN，GREEN `RC=0` 且选中情景测试；不得仅凭导入失败或零测试冒称 RED/GREEN。

## Task 2：样本、场景与人工报告

**依赖：** Task 1。**不变量：** `INV-02`、`INV-04`、`INV-05`、`INV-06`。**文件：** 同 Task 1。

使用合成输入公开接口测试后实现：两个 `listing_regime` 分别按各情景完整 child 的 OI 事后中位数分组，`>` 为 high。对每个情景、每个 `(parent_article_id, listing_regime)`，只有该组**全部选入 Universe 的 child 在该情景下 OI 与价格路径均 complete**，才以这些 child 的中位数形成完整 Parent 各指标并独立分组；任何一个 child 不完整，该 Parent 组保留缺口且不进入该情景的完整 Parent 统计，不能只聚合完整子集。跨机制 Parent 只计一个公告簇。A/B/C 各自输出 Universe、OI 对、child/Parent 完整数量、缺口、high/low 组数和 `terminal_return` 均值差；空组 `null`。B 按父 Design 输出终点/MAE/MFE 分布及逐 Parent 剔除重算；网格对照单列，各情景输出样本重合与差异，不归因为已证实延迟。

设计手算样例覆盖两机制、跨机制同 Parent、多 child 不完整、ties/空组、三情景各有不同可用记录，以及报告 `historical_scenario_only` 和实际 PIT 未验证。多 child 负向样例明确断言：同 Parent 同机制的 A complete、B `endpoint_unavailable` 时，该 Parent 在对应情景中整体不进入完整 Parent 分组和 LOO，且保留 Parent 缺口及 Universe 分母；不能只断言 B 被排除。独立算出分母与 high-minus-low，不能调用被测聚合函数构造预期；错误来源、缺失 OI/路径、假设与已核实事实冲突均有明确报告/停止行为。没有真实覆盖或可信时间语义不得推断策略收益，也不把 B/C 样本不足当成策略证伪。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q -p no:cacheprovider tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py -k 'scenario or parent or grouping or report'
```

预期 GREEN `RC=0`，记录 RED/GREEN 与选中测试数；不新增独立的 verifier。

## Task 3：受控输入与最小端到端路径

**依赖：** Tasks 1–2。**不变量：** `INV-01`、`INV-02`、`INV-04`、`INV-05`、`INV-06`。**文件：** 四个允许路径。

1. 在实施前置的合成测试验证：无新 Plan/Delta 绑定的单次用户运行授权时，CLI 在真实 loader/输入之前拒绝；实际授权须标明具体操作、当前 Plan/Delta/父 Design、J-A/J-B/ledger 和其他输入身份、全新输出根及所有禁止权限。授权文件只是机器校验输入，不等于用户原始同意；旧 Plan 的 release、授权文件、source bundle 不能直接复用，生产入口也不得用伪造文件证明授权。
   分类 ledger 准入继承 J-C 冻结身份：`data/exports/stage1_5j_token_launch_classification_ledger_v2.csv` 的 SHA-256 必须精确为 `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b`；严格检查 12 列 `parent_article_id,symbol,asset_class,listing_regime,classification_status,table_index,symbol_column_index,field_header,raw_cell_value,evidence_locator,source_relative_path,source_sha256`、分类字段及联合键唯一和适用上游集合一致性。新增只在 `tmp_path` 副本上将一个 `listing_regime` 改写而保持 `(parent_article_id,symbol)` 不变的负向测试，证明冻结 SHA 校验拒绝；不能用仅检查键或重新计算并信任新 SHA 代替。真实 ledger 读取需符合适用消费授权，未授权不计真实准入通过。
2. 优先调用上一研究的公开 `build_admitted_ja_context` / `open_verified_package_stream`，strict loader 返回原 package record，再在本模块以有界流实现必要的新窗口读取；删除本模块重复 J-A admission/manifest 字段解析及只为该重复实现存在的测试，不能修改上一研究或 J-B 私有 reader。沿用其身份、CHECKSUM、CRC、65,536-byte 物理行（含换行）与拒绝损坏规则；处理至 EOF，逐包检查，claimed-present 丢失/损坏是错误，已证实缺包为业务缺口。无合法复用路径时按 Task 0 路由，不通过降低检查继续。
3. OI 不再把 `verified=true`、合成逐行上界或情景标签当成真实时间证据；读取用户明确授权、记录路径/SHA/symbol/单位的原始文件并只使用真实归档中的原始值及标签；缺项保留。假设时点单独计算和报告。保留来源/索引最少字段即可，允许删除复杂认证清单，但不得让未授权目录搜索、未列文件或错误 symbol 静默进入。已核实事实冲突时拒绝对应情景，未核实时仅标记情景假设。基差映射/单位不可信时缺失；禁止凭同名或硬编码单位填值。
4. 报告与明细写到用户授权的全新目录；检查祖先及物理路径、不得位于受保护输入根内或为其祖先，最终目录排他创建，存在即拒绝。输出包含输入身份、Delta/父 Design/本 Plan、假设、样本守恒、三情景及网格、两机制、Parent/日期、缺口和不具交易权限；不可覆盖或伪造成功。
5. 纯计算/故障注入可用本地合成；跨模块正向断言使用上游 canonical 构造器/序列化器或真实 strict loader，不能使用手写 `{bytes, zip_relative_path,...}` 冒充 J-A 成功。若 canonical 路径需要实际历史 root，则待用户另行授权后执行，缺授权明确 `historical_validation_not_authorized` 并 skip；测试应可以在得到指定授权后真正运行，而不是无条件 skip。真实原始 source 验证缺口另记 `evidence_insufficient`。

先以 RED→GREEN 测无授权前不调用 loader、真实字段格式兼容/不可伪造正向、超长行拒绝、完整与跨日缺包、来源未列或身份错误、两机制三情景报告、输出碰撞/符号链接及独立数值。canonical 正向 + 临时副本单点变异仅在单次授权包含对应动作和输出位置时执行；不能自行改写授权文件的目录或复用前次输出。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q -p no:cacheprovider tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py tests/scripts/external_signal_shadow/test_run_launch_open_interest_basis_exploratory.py
```

预期合成和拒绝测试 `RC=0`；逐项记录 pass/skip 及原因。若测试包含真实 ledger 或历史 raw，未授权时须跳过该项，不能把退出码 0 当作真实准入成功。不得默认请求单次真实研究授权以完成代码修复。

## Task 4：收尾与独立复核

**依赖：** Tasks 0–3。**不变量：** `INV-01` 至 `INV-06`。**文件：** 无额外仓内文件。

记录各门禁实际结果、被删重复逻辑及复用边界；比对执行前快照、HEAD、staged/unstaged/untracked 与白名单。单次研究未授权、真实来源尚缺或上游正向未验证时如实报告，不把合成测试通过说成研究完成。独立会话进行 completion audit；若确有授权才核对真实运行和输出，不把该 Plan 当作运行许可。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q -p no:cacheprovider tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py tests/scripts/external_signal_shadow/test_run_launch_open_interest_basis_exploratory.py
.venv/bin/ruff check --no-cache src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py scripts/external_signal_shadow/run_launch_open_interest_basis_exploratory.py tests/research/external_signal_shadow/test_launch_open_interest_basis_exploratory.py tests/scripts/external_signal_shadow/test_run_launch_open_interest_basis_exploratory.py
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
git diff --check "$BASE_SHA"
git diff --cached --name-status "$BASE_SHA"
git status --short --untracked-files=all
```

记录实际进程 RC，pytest、Ruff、scanner 和 diff-check 预期 `RC=0`；明确测试 skip，不能用 clean scanner 代替语义验证。独立审计的 `complete` 仅针对批准范围，不授予下载、runtime、commit、部署、paper/live 或交易权限。

## 不变量与任务映射

| 不变量 | 任务和证明 |
| --- | --- |
| `INV-01` | 0、3、4：身份、上游契约、单次授权前拒绝及输出隔离。 |
| `INV-02` | 0、2、3：Universe/Parent 守恒、各机制和缺失报告。 |
| `INV-03`（Delta 替换） | 1、2、3：A/B/C 假定时点、D 与边界、PIT 未验证和冲突停止。 |
| `INV-04` | 1、3：OI/基差单位、价格、跨日、真实来源身份及手算。 |
| `INV-05` | 2、3：B 分布与 Parent LOO、A/C 对比、样本重合和情景声明。 |
| `INV-06`（Delta 替换） | 1–3：独立手算、情景标签、Rule 15 上游正向与授权边界。 |

Rule 16：白名单内实现缺陷就地修复；仅扩路径需先获有限 Plan 增补批准；改变研究语义、上游契约或权限则停止并退回 Design。Plan 候选必须独立审查并获用户明确批准后才可实施。
