# PREDICT 盘前 OI 情景 C 单事件留出检查 Implementation Plan

**日期：** 2026-11-07。**状态：** `plan_candidate / pending_independent_review_and_user_approval`。

## Allowed Change Scope

| 类别 | 精确白名单与边界 |
| --- | --- |
| Allowed implementation paths | 新增 `scripts/external_signal_shadow/run_predict_pre_market_oi_c_holdout.py`，本事件的薄适配、冻结及评分入口。 |
| Allowed verification paths | 新增 `tests/scripts/external_signal_shadow/test_run_predict_pre_market_oi_c_holdout.py`；测试数据只在 `tmp_path` 生成，不另建仓内 fixture。 |
| Allowed documentation paths | 仅本文 `docs/plans/2026-11-07-predict-pre-market-oi-c-single-event-holdout-implementation-plan_CN.md`；批准后保持精确版本，不通过勾选任务改变批准身份。 |
| Allowed generated/runtime artifacts | 实施基线保存在仓外全新 `BASELINE_DIR`；合成测试文件保存在测试临时目录。真实批次须另获授权，只在其全新持久 `batch_root` 写 `model_freeze.json`、`holdout_case.csv`、`review_CN.md` 及 `inputs/` 内获准的官方 ZIP/`.CHECKSUM`。本 Plan 不指定或创建真实输出目录。 |
| Affected but unchanged | 下列已核实的旧 OI core、J-B 纯 helper/配置、增量研究 canonical writer、上游 Design、训练快照及报告。验证复用接口和输入不变性，不修改旧 CLI 的固定 hash、旧收据或其他 consumer 权限。 |
| Forbidden | 白名单外修改；修改 `src/`、`configs/`、依赖、治理规则、旧测试/数据；全库格式化、破坏性清理；自动提交。不得 `git add/commit/push`、部署、SSH、交易客户端或 runtime action。真实训练、下载、评分须另获适用授权，实施批准本身不授予这些权限。 |

> **执行适配：** 使用 `writing-plans` 的任务依赖与 TDD 方法；项目工作流覆盖其默认保存目录、逐任务 commit 和直接启动执行步骤。获独立审查推荐并经用户明确批准本 Plan 后，才进入 `execute-approved-plan.md`；执行者不得自审宣布 `complete`。

**Goal：** 从旧 18 个盘前 C Parent 冻结 M0/M1，再如实记录 PREDICT 一个后续历史事件的预测误差或缺口。

**Architecture：** 一个脚本加一个测试文件；复用现有纯计算、ZIP/物理行保护与 canonical writer，不接入旧完整准入管道。只做一次全训练集拟合和一个事件评分，不做 LOPO、调参或未来事件框架。

**Tech Stack：** 现有 Python >=3.11、NumPy、pytest、Ruff，以及 `csv/json/hashlib/zipfile/urllib.request/datetime/pathlib` 标准库；不新增依赖。

## 1. 批准依据、当前事实与权限

- 用户已批准 [Design](../designs/2026-11-07-predict-pre-market-oi-c-single-event-holdout-design_CN.md)，SHA-256 `b7a8bc2eaeb3bbfe58a34fe026df84d06f0bbbe29c992e9f18970012ae7b131d`。本文逐项落实该版本，不修改模型、样本、时间窗口或结论等级。
- 设计时仓库 HEAD 为 `a528c3a3f15a8153aac00e5edd7c5becf2bf624a`；工作区仅该 Design 为未跟踪文件。执行时重新记录基线，不把此快照冒充实施基线。
- 已读 `AGENTS.md`、L0/L1/L2、`docs/roadmap.md`、`configs/base.py`、实施计划工作流及治理复盘参考。`RISK_LIVE_TRADING_ENABLED=False`；参考文档不产生新规则或授权。
- 当前批准语句未单独确认 Design §2 的受限快照机器消费边界，也未授权真实训练、下载或评分。这不阻止 Plan 起草及将来获批后的合成测试；首次真实批次授权须明确接受 §2，并列明实际允许动作，可一次完成，不增加逐阶段人工审批。
- 本轮未读取训练面板数值、未读取新事件 ZIP、未拟合真实模型。数据内容、计划时间版本适用性和事件资格都是待验证事实，不能写作已通过。

### 1.1 只读输入与复用边界

| 对象 | 身份或复用方式 |
| --- | --- |
| 唯一训练数值来源 | `data/research_archives/launch_incremental_run_20261105/parent_panel.csv`；SHA-256 `1396b1f0c34bbb99d936abf13a7a99f44863eb300c9fc35b4fbeefffee6faac2`。 |
| 配套旧报告 | 同目录 `review_CN.md`；SHA-256 `5f57a97d249c24c06656ee42dff4982fab1cc63742095f4ec16abb701ee3338d`；仅来源/协议追溯，不抽取训练数值。 |
| 修订预审 | `data/research_preflights/pre_market_after_20260416_20261106/review_CN.md`；SHA-256 `8fd9ddfde793e974e85e7029202104d42ef143c67fefddd54252f5478ae652cc`；仅元数据与来源线索，不证明 ZIP 内容覆盖。 |
| 旧增量 Design | `docs/designs/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-design_CN.md`；SHA-256 `f38fd9c4609a52cc9d2d6529cceabca35c778e84c374fad4e386029d0493519e`。 |
| OI 时间假设 Delta / 父 Design | `docs/designs/2026-11-02-launch-open-interest-scenario-assumptions-design-delta_CN.md`：`7941e641437ad20f4aee96be4b3ff65e7f97503d5d3f8693fdce81c29db55b54`；`docs/designs/2026-11-01-launch-open-interest-basis-exploratory-design_CN.md`：`82dd58310d7f2377c23eac7606a2cf74ec038c9b96b84436dd6a5af2826aa00f`。 |
| 旧 OI core | `src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py`；复用 `AggTradeRecord`、`OiMetricRecord`、`stream_aggtrades_csv_lines`、`calculate_baseline`、`calculate_path_response`。`calculate_oi_change` 会先过滤非正 OI，须先独立锁定最新 L1 并验证固定前驱，再仅对合格两点调用，不能据其默认行为回退。 |
| J-B 纯 helper / 配置 | `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py` 的 `validate_zip_archive_package`、`validate_aggtrades_csv_header`、`select_launch_anchor_trade`；沿用 `configs/stage1_5j_b_historical_aggtrades_launch_response.py` 的 300,000 ms 锚点上限、ZIP 上限 268,435,456 bytes、CSV 上限 536,870,912 bytes、压缩比 64、物理行 65,536 bytes。只复用纯格式/计算能力，不声称通过旧 profile。 |
| Canonical 训练夹具 writer | `scripts/external_signal_shadow/run_launch_price_oi_basis_incremental_information.py::write_parent_panel_csv(panel, out_path)`，实际 16 列、8 位小数。旧 `_fit_and_predict_ols` 不返回系数，故不改旧接口，新脚本直接用 NumPy 保存拟合结果。 |

已用 `rg` 核实上述定义/消费方；精准 `graphify query "calculate_path_response"` 未找到节点，不能据此推断无调用方。实际旧调用保持不变，无需更新知识图谱。执行时记录实际复用源码 SHA；若接口或语义与本表不符，按 Rule 16 分流，不静默替换。

新事件固定为 `parent_article_id=5ef55cf8358e4a48b2512a156e89c8e5`、`symbol=PREDICTUSDT`、`listing_regime=pre_market`，`S=2026-10-25T08:15:00Z`。官方日包仅以下四个，URL 规则、官方公告地址沿用 Design §1–§2：

| 文件 | 固定 ZIP SHA-256 | 消费条件 |
| --- | --- | --- |
| `PREDICTUSDT-aggTrades-2026-10-25.zip` | `a25d07cd093a9251f69730e0ed9a1371fcb17f6cb94d4f360067ed7ca5d06ba4` | 必需。 |
| `PREDICTUSDT-metrics-2026-10-25.zip` | `0eff530f194d3b61996b1b5b149639a3550f2684a4f14ed1d9c4a63c29564df3` | 必需。 |
| `PREDICTUSDT-aggTrades-2026-10-26.zip` | `fc640042973f3c5238a14ae0d5d4f42f7e0f5c7d17fca4b798f8bd96adaeec95` | 仅所需窗口跨 UTC 日。 |
| `PREDICTUSDT-metrics-2026-10-26.zip` | `c2ea538180af560b26021d9888bdbf04d2c9e25327e979adee618d692ab5e6cb` | 仅所需窗口跨 UTC 日。 |

合格 T0 不晚于当日 08:20，最晚所需时刻为 09:00:05，故本固定事件正常分支只需 10 月 25 日两包；不得为找锚点主动补读次日。跨日能力用合成边界测试验证，不改变 S。

## 2. 最小接口与持久化契约

以下接口均位于唯一新增脚本；内部小函数可就地拆分，不新增类层、服务或文件：

```python
def load_training_panel(path: Path, expected_sha256: str) -> list[dict]: ...
def fit_models(p: np.ndarray, o: np.ndarray, y: np.ndarray) -> dict: ...
def build_case_features(trades: list[AggTradeRecord], oi_records: list[OiMetricRecord],
                        *, scheduled_launch_ms: int, schedule_evidence: dict) -> dict: ...
def score_case(case: dict, frozen_model: dict) -> dict: ...
def main(argv: list[str] | None = None) -> int: ...
```

生产 `main` 只接受 `--auth-file` 和 `--output-dir`；训练路径/hash、事件、S、情景和模型列均固定于批准契约，不提供调参、样本数或跳过校验开关。`fit_models` 的内部数学单测可用 8 点，不因此放宽真实入口的 18 Parent 检查。

**授权载体：** JSON 仅承载用户的适用授权，不是脚本自行签发的权限。核对 Design/Plan 路径和完整 SHA、consumer 路径/实际 SHA、§2 边界明确接受、训练面板及配套报告身份、固定事件/S、获准来源及其摘要、唯一全新 root、`allowed_actions`、既往观察披露及来源版本核验依据。动作只允许 `freeze_model / download_inputs / score_case` 的明确授权子集；实际完整检查须含冻结及评分许可。联网下载另须 `download_inputs` 和 `network_allowed=true`，只接触获准官方 HTTPS URL，不跟随到其他域或换源。无下载许可时只可在冻结后读取授权中列明且实际 hash 匹配的现有包。`signal_allowed / execution_allowed / paper_trading_allowed / live_trading_allowed` 必须均为 false；缺必需字段、身份或权限矛盾均非零退出。

计划时间证据至少记录官方 URL、核验所用版本/内容摘要、修订说明及适用性结论；有提前成交时另记录解释及其来源。可由该批次提供只读来源证据与核验记录，不为此建设公告版本服务，也不要求历史真实 PIT 证明。未知或不足时走冲突状态，不能仅把授权中的一个 true 当作已核实事实。此前是否看过 PREDICT 数值默认 `prior_exposure_status=unknown`，已知观察如实披露。

| 产物 / 消费者 | 必需结构、语义和失败行为 |
| --- | --- |
| `model_freeze.json` / 仅本 scorer | 包含 `freeze_status`、实际 Design/Plan/代码身份、训练路径/hash、排序后 18 Parent/child 身份与日期范围、p/o 训练范围、C 时间协议、两模型列顺序、均值/总体标准差、系数、秩/n、UTC 冻结时间、既往观察披露。JSON 禁止 NaN/Infinity，有限数字 round-trip，不先舍入系数，不含新事件数值或自身 hash。不可估时系数为空、状态明确，不伪造部分成功模型。 |
| `holdout_case.csv` / 人工阅读复核 | 固定一行。列组为身份/状态/原因/假设标签及模型、Plan、脚本 hash；S 来源版本与修订说明；首日最早成交时间/ID、S 前笔数；锚点 ID/T0/价格/延迟；D、基线末笔 ID/时间/价格；L0/L1 及原始 OI；p/o；entry/endpoint 的 ID/时间/原始价格；y/MAE/MFE；z 值、训练范围外标记；两预测、残差、绝对/平方误差、d、预测小于 -1 标记。新脚本定义一个固定列序元组，writer 和测试据此检查，不扩展旧 CSV。缺失值为空，不填 0/NaN；`case_status` 限 Design 的四种值，未评分时原因非空，预测/误差/d 为空。 |
| `review_CN.md` / 人工阅读复核 | 最后写。列出 Universe=1、scored=0/1、missing=1-scored、缺口原因、训练隔离/冻结顺序证据、模型 hash、实际全部输入/代码身份与版本、S 适用性及提前成交诊断、原始参考值、预测/误差/外推诊断、权限与研究限制。`scored` 时说明 d 的单事件含义；其余状态不称评分成功。只在三产物均完成后报告 `batch_status=completed`，不另建成功标记文件。 |

三个产物始终标记 `historical_scenario_only / real_pit_verified=false / hypothesis_only / no_alpha_claim`。模型文件的 hash 绑定研究参数，不是运行准入凭证；CSV/报告无机器下游准入资格。Rule 17 用结构、hash 和下述独立语义测试，不新增 Schema verifier、Recorder、锁、fsync 或恢复状态机。未覆盖真实发布时间、全交易史无遗漏、前瞻盲测或可执行净收益。

## 3. 垂直切片与验证

所有 Task 的代码/测试修改仅限顶部两个白名单文件；Task 0、4、5 不新增实现文件。行为切片均先写公开接口失败测试，保存 RED 命令及实际失败原因，再最小实现至 GREEN，最后在相同断言下整理。预期值来自下列公式/向量，不调用待测算法生成期望值。

### Task 0：基线与身份，后续切片的共同前置

**Dependencies：** Plan 独立审查推荐及用户明确实施批准。**覆盖：** INV-01、INV-03。

- [ ] 重新核对本 Plan 的用户批准 SHA、Design SHA 和上游文档；无有限增补时保持两文件白名单。`APPROVED_PLAN_SHA256` 仅从用户对本 Plan 的明确实施批准原文读取，不得用当前文件的计算结果自行充当批准值，也不得沿用修订前的审查 SHA。未收到批准或无法核验原文时立即 `STOP=approved_authority_mismatch`，不得运行后续命令或进入 Task 1。不得以 Design 获批推断实施或消费已获批。
- [ ] 在仓外记录 HEAD、暂存/未暂存补丁、全部未跟踪路径及现有文件 hash；保护已有 Design/Plan 和其他用户改动。命令由执行者运行并保留变量，不在本次起草中执行：

```bash
set -euo pipefail
stop_authority_mismatch() { printf '%s\n' 'STOP=approved_authority_mismatch' >&2; exit 1; }
PLAN_PATH=docs/plans/2026-11-07-predict-pre-market-oi-c-single-event-holdout-implementation-plan_CN.md
DESIGN_PATH=docs/designs/2026-11-07-predict-pre-market-oi-c-single-event-holdout-design_CN.md
EXPECTED_DESIGN_SHA256=b7a8bc2eaeb3bbfe58a34fe026df84d06f0bbbe29c992e9f18970012ae7b131d
[ -n "${APPROVED_PLAN_SHA256:-}" ] || stop_authority_mismatch
ACTUAL_PLAN_SHA256=$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}') || stop_authority_mismatch
ACTUAL_DESIGN_SHA256=$(shasum -a 256 "$DESIGN_PATH" | awk '{print $1}') || stop_authority_mismatch
[ "$ACTUAL_PLAN_SHA256" = "$APPROVED_PLAN_SHA256" ] || stop_authority_mismatch
[ "$ACTUAL_DESIGN_SHA256" = "$EXPECTED_DESIGN_SHA256" ] || stop_authority_mismatch
printf 'APPROVED_AUTHORITY_MATCH=OK\nPlan SHA-256: %s\nDesign SHA-256: %s\n' \
  "$ACTUAL_PLAN_SHA256" "$ACTUAL_DESIGN_SHA256"

BASE_SHA=$(git rev-parse HEAD)
BASELINE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/predict-holdout-baseline.XXXXXXXX")
printf '%s\n' "$BASE_SHA" > "$BASELINE_DIR/BASE_SHA.txt"
git status --short --untracked-files=all > "$BASELINE_DIR/status.before.txt"
git diff --binary > "$BASELINE_DIR/unstaged.before.patch"
git diff --cached --binary > "$BASELINE_DIR/staged.before.patch"
git ls-files --others --exclude-standard -z > "$BASELINE_DIR/untracked.before.zlist"
while IFS= read -r -d '' path; do shasum -a 256 "$path"; done \
  < "$BASELINE_DIR/untracked.before.zlist" > "$BASELINE_DIR/untracked.before.sha256"
```

**预期：** 仅当 Plan SHA 与用户实际批准语句一致、Design SHA 与上述获批值一致时，打印 `APPROVED_AUTHORITY_MATCH=OK` 及两个实际摘要，再记录基线；整体 RC=0，基线文件实际存在，未消费真实数值。批准值缺失、文件不可读或任一摘要不一致均打印 `STOP=approved_authority_mismatch`、RC=1，不创建实施基线、不继续 Task 1。当前 HEAD 与起草快照不同不自动失败，但不得覆盖新出现的用户改动；若影响契约，按 Rule 16 分流。

### Task 1：canonical 面板到可独立核验的模型冻结

**Dependencies：** Task 0。**文件：** 新脚本、新测试。**覆盖：** INV-01、INV-02、INV-03、INV-05、INV-06。

- [ ] RED：`test_training_canonical_panel_and_mutations` 使用旧 `write_parent_panel_csv` 写 18 个合法 pre_market/C Parent；读实际字节算 fixture hash。检查真实 16 列表头、重复列/联合键、行字段数、日期 <=2026-04-16、PREDICT 排除、正且一致的 child 分母、空 missing_reasons、p/o/y/MAE/MFE 有限，basis 缺失仍可入训。单点变异包括 hash、列/键、数量、日期、身份、NaN 和状态；不默默减为 17 行。
- [ ] RED：`test_model_hand_calculated_oracles` 检查实际标准化矩阵、系数、秩和序列化后的预测，不只断言输出存在。`test_model_not_estimable` 覆盖零方差、常量/线性相关特征造成 M1 不满秩、非有限参数；无 Ridge/删点回退。
- [ ] GREEN：实现 `load_training_panel`、`fit_models` 及冻结 JSON 写出/加载；main 的真实路径始终传固定训练身份，测试只在隔离模块内替换真实路径/hash 为 canonical fixture 的实际身份，不新增生产绕过开关或假上游收据。

**独立 oracle 1：** 使用 p=`(-3,-2,-1,0,1,2,3,4)`、o=`(2,-1,3,0,-2,1,4,-3)`、y=`(-23,2,-4,1,-11,16,67,-48)`。p/o 均值均为 1/2、总体方差均为 21/4，y 均值为 0。M0 原始坐标截距/斜率为 `-33/28,33/14`；标准化系数为 `[0,33*sqrt(21)/28]`。M1 标准化系数为 `[4.5,2*sqrt(21),2.5*sqrt(21),21]`。新点 `(0.5,1,7)` 预测应为 `0,7`，d=49；数值容差仅用于浮点比较，不作研究门槛。

**独立 oracle 2，供真实入口合成正向测试：** 取 p∈{-0.2,0,0.2}、o∈{-0.1,0,0.1} 的 9 个笛卡尔点各两行，使用 18 个不同旧 Parent/child 身份；令 `y=0.01+0.2*p+0.3*o+0.4*p*o`。两均值为 0、总体方差分别为 `2/75,1/150`；M0 原始系数为 `(0.01,0.2)`，M1 为 `(0.01,0.2,0.3,0.4)`。测试点 `(p,o,y)=(0,0.1,0.04)` 应得两预测 `0.01,0.04`、d=`0.0009`。重复特征是数学夹具，不代表真实事件独立性证据。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest \
  -q -p no:cacheprovider tests/scripts/external_signal_shadow/test_run_predict_pre_market_oi_c_holdout.py \
  -k 'test_training or test_model'
```

**预期：** RED 命中对应缺失/错误行为；GREEN RC=0，无真实数据 skip 伪装为正向兼容。8 点 oracle 仅检验内部数学，canonical 入口仍要求完整 18 Parent。

### Task 2：官方格式小 ZIP 到单事件特征和评分

**Dependencies：** Task 1。**文件：** 同两个白名单文件。**覆盖：** INV-03、INV-04、INV-05、INV-06。

- [ ] RED：`test_archive_format_and_bounds` 在 `tmp_path` 生成公开格式的单 CSV ZIP 和对应实际校验文本；覆盖 ZIP 单成员/期望文件名/资源上界、重复列/错误字段数、UTF-8、物理行含换行恰为 65,536 bytes 可读及多 1 byte 拒绝。只声称适配规则正确，不声称真实 archive 覆盖；需要比较旧 helper 时用其 strict 格式校验作为正向证据。
- [ ] GREEN：复用 ZIP helper 和 `stream_aggtrades_csv_lines`，不抽取到文件系统；流式消费完整包并校验结尾/CRC。aggTrades 严格七列表头、非负整数 ID/毫秒时间、first<=last、ID 严增/时间不降、正确 UTC 日、有限正价格/数量及既有布尔集合。metrics 按列名取必需三列、允许额外唯一列、字段数一致、UTC 五分钟网格/日期/symbol 正确、OI 有限且非负；不猜时间单位或用名义价值。重复 OI 标签保留为明确 `data_gap`，不字典覆盖；最新所选 OI 为 0 同样缺口，不回退。
- [ ] RED：`test_time_anchor_contract` 覆盖有解释的提前成交且 S 处有成交时取 S、S+300,000 可用/S+300,001 不可用、同毫秒按 ID、无首日包/无计划后成交、版本未知/提前成交解释不足/已知更早交易日期或机制冲突。诊断保留提前成交，不放入特征；不以次日首笔补 T0。
- [ ] RED：`test_time_oi_and_price_boundaries` 覆盖非网格 T0、C 可用时刻恰等于 D、最新点为 0/缺前驱均不回退、无关未来记录不改变所选两点、entry 的 D/D+5s 和 endpoint 的 E-1s/E、D+5s+1ms 无 entry、endpoint 缺口、跨日日期集合、8 位精度和 MAE/MFE 路径端点。
- [ ] RED：`test_score_hand_calculated_and_extrapolation` 使用下面贯通样例核两预测、残差/误差/d，并覆盖 d 的正/负/零、超训练范围和预测小于 -1 时保留原值及诊断；未评分状态不得产生伪数值。
- [ ] GREEN：实现 `build_case_features` 和 `score_case`。先定资格再计算：T0 为 sorted trades 经 J-B helper 选出的计划后参考成交；D=T0+25m；先从标签选最新 L1<=D-15m，再查 L0=L1-5m>=T0 且两点正值；p 来自 `[T0,D)`，entry/endpoint/MAE/MFE 沿用 Design 和旧公开纯函数。所有已核实时间反证如实报告，不把假设填入 verified 字段。保留原始参考值，p/o/y/MAE/MFE 量化到 `float(f"{value:.8f}")` 后评分；系数不舍入、不裁剪。

**数值贯通样例：** S=08:15:00Z，T0=S+1s，D=08:40:01Z；T0 和 D 前末笔均为 100，故 p=0。metrics 的 L0=08:20、L1=08:25，OI 为 100、110，故 o=0.1；entry 位于 D，价格 100；路径含 98、106，endpoint 位于 E=08:55:01，价格 104。故 y=0.04、MAE=-0.02、MFE=0.06。与 Task 1 的 18 点模型相连后，须满足：

```python
assert result["prediction_M0"] == pytest.approx(0.01)
assert result["prediction_M1"] == pytest.approx(0.04)
assert result["d"] == pytest.approx(0.0009)
assert result["long_mae"] == pytest.approx(-0.02)
assert result["long_mfe"] == pytest.approx(0.06)
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest \
  -q -p no:cacheprovider tests/scripts/external_signal_shadow/test_run_predict_pre_market_oi_c_holdout.py \
  -k 'test_archive or test_time or test_score'
```

**预期：** GREEN RC=0；合法数据缺口保持 Universe=1、不产生预测；损坏格式/错误身份非零异常不冒充合格输入。分支测试不得读取本地真实 ZIP。

### Task 3：受控 CLI 到三产物，验证真实 I/O 顺序

**Dependencies：** Task 1–2。**文件：** 同两个白名单文件。**覆盖：** INV-01 至 INV-06。

- [ ] RED：`test_cli_canonical_to_three_outputs` 通过 `main(argv)`，使用 canonical writer 的 18 Parent、Task 2 小 ZIP、实际 fixture 摘要及仅测试有效的来源/授权对象，得到真实落盘三产物；CSV 中两预测、d、MAE/MFE 必须为上述手算值。测试不 mock 拟合、特征、scorer 或结果 writer；网络边界用内存公开格式内容替代，不触网。
- [ ] RED：`test_cli_freeze_precedes_new_content` 在实际 `urlopen`、新包读取及模型文件写出/hash 边界捕获调用顺序：冻结落盘并完成 hash 绑定在任何新 ZIP 内容读取/下载之前。改留出价格或 y 后训练均值/标准差/系数保持不变；冻结执行时间等元数据不要求字节恒同。模型文件随后篡改必须拒绝，不能重新拟合覆盖。
- [ ] RED：`test_cli_fail_closed_and_honest_gaps` 分别验证无授权、Plan/Design/输入/代码身份错误、未接受 §2、禁网却请求下载、未获评分许可、旧 root/祖先符号链接/输出包含或位于输入目录、包摘要错误、校验文本错误文件名、写模型/CSV/报告失败。不可估时不发生新内容 I/O；数据缺口/锚点冲突仍输出一行未评分记录，不标 `scored`。输入或写出损坏 RC!=0，不显示批次完成，保留残留、不覆盖续跑。
- [ ] GREEN：main 依序核授权及安全路径 → 只读验证训练来源/拟合 → 全新 root 写冻结 JSON 并绑定 SHA → 仅合格模型建立 inputs 并获取获准包 → 校验/完整解析/计算 → 重验冻结及实际输入身份 → 写一行 CSV → 最后写报告。评分只从同一已绑定模型字节加载参数，不再训练。首次 root 用排他新建；无自动删除/重跑机制。
- [ ] GREEN：下载只用官方 HTTPS URL；有限超时、分块读取并在超过既有 ZIP 大小上限前中止，校验文本也有物理行上界；核对官方文件名/摘要和批准摘要。HTTP 不可达非零退出，不当作不存在，不自动换源/更新身份。首次日缺包等可确认缺口按 Design 状态记录。未获网络权限时连请求都不得发出。
- [ ] REFACTOR：只保留本事件需要的分支与来源适配；整个日包流式验证，内存仅保留诊断和相关价格路径/OI 记录，不复制旧 J-A/J-B loader、授权系统或归约流程。测试只在隔离模块中注入临时输入身份，不把测试替身/合成 hash 宣称为官方正向证据。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest \
  -q -p no:cacheprovider tests/scripts/external_signal_shadow/test_run_predict_pre_market_oi_c_holdout.py \
  -k test_cli
```

**预期：** GREEN RC=0；只有三份结果文件及获准 inputs，无额外 audit recorder/成功标记。完成状态与是否 scored 分开，残留不伪装完成。`--help` 不消费任何真实输入。

### Task 4：合成实现验收与独立 Completion Audit

**Dependencies：** Task 0–3。**覆盖：** INV-01 至 INV-06。**文件：** 只读核验两个白名单文件及基线，不新增文档。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest \
  -q -p no:cacheprovider tests/scripts/external_signal_shadow/test_run_predict_pre_market_oi_c_holdout.py
.venv/bin/ruff check --no-cache \
  scripts/external_signal_shadow/run_predict_pre_market_oi_c_holdout.py \
  tests/scripts/external_signal_shadow/test_run_predict_pre_market_oi_c_holdout.py
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
git diff --check "$BASE_SHA"
git diff --cached --check
git status --short --untracked-files=all
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -c \
  'from configs import base; assert base.RISK_LIVE_TRADING_ENABLED is False'
```

**预期：** 检查 RC=0；必需合成测试不跳过，不读真实训练数值/ZIP；范围与基线一致，两个新未跟踪文件的内容必须直接审阅，不能只看 tracked diff。实施方提交实际 RED/GREEN/门禁 RC、基线目录、文件 hash 与未决项，不把本 Plan 的预期输出抄成执行证据。

独立审计按 `audit-plan-completion` 核源码、接线、oracle 独立性、fixture 来源、全部工作区状态及不变量。代码实现可验收与真实数据兼容、实际研究完成分开表述；Task 5 未授权/未运行时应明确列为待执行，不以合成测试冒称整个真实研究已完成。审计 `complete` 只对应明确声明的已批准实现范围，不赋予后续操作权限。

### Task 5：授权后的一次真实批次及结果复核

**Dependencies：** Task 4 的独立代码审计通过，用户明确接受 Design §2，并给出适用真实操作授权。**覆盖：** 全部 INV，特别是 INV-02、INV-04、INV-06。**写入范围：** 仅该授权指定的新持久 batch_root。

- [ ] 一个授权可以覆盖 `freeze_model / download_inputs / score_case`，绑定实际 Plan/Design/代码、只读训练快照、官方来源/摘要及 root；无需再逐阶段等待用户确认。若只授予部分动作，不补齐其他权限。
- [ ] 先验证旧快照身份与 18 行训练语义；来源版本核验记录要能解释 S 的适用性，不要求不存在的真实发布时间证据。有提前成交时据实际来源作解释，不能因希望评分就放行。
- [ ] 按 main 顺序仅运行一个批次；实际 hash 与官方 .CHECKSUM/固定摘要不符、来源版本不合或运行失败即停止受影响操作，不换样本、窗口或 root 反复择优。合法缺口交付未评分原因。

```bash
# AUTH_FILE 与 BATCH_ROOT 仅取自该次用户明确授权，不由执行者自行扩权。
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python \
  scripts/external_signal_shadow/run_predict_pre_market_oi_c_holdout.py \
  --auth-file "$AUTH_FILE" --output-dir "$BATCH_ROOT"
```

**预期：** 合格或诚实缺口交付 RC=0，三产物结构完整、case_status 准确；损坏/身份/权限/写出失败 RC!=0。实际文件逐个算 SHA，训练面板、配套旧报告及只读来源前后不变。独立复核者用冻结系数、原始参考价格/OI 和公式重算 p/o/y/MAE/MFE、两预测/误差/d，核对一行分母及未被篡改的冻结先后证据。未取得授权时本任务保持未执行，不虚构通过记录。

## 4. 不变量到任务及命令的闭环

| Design 不变量 | 实现任务 | 最小可执行验证与证据 |
| --- | --- | --- |
| INV-01 权限/身份 | 0、1、3、4、5 | `-k 'test_training or test_cli_fail_closed'`；Task 4 范围/安全命令；Task 5 真实授权及字节身份，实施批准不代替操作批准。 |
| INV-02 冻结先于新数据 | 1、3、5 | `-k 'test_model or test_cli_freeze'`；实际 I/O 顺序、模型篡改拒绝、真实冻结文件 SHA 和只读训练身份。 |
| INV-03 训练/事件隔离 | 1、2、3、5 | `-k 'test_training or test_cli_canonical or test_cli_fail_closed'`；18 旧 Parent、PREDICT 排除、Universe=1/missing 守恒。 |
| INV-04 时间/数据 | 2、3、5 | `-k 'test_archive or test_time or test_cli_fail_closed'`；S 版本与锚点边界、最新标签不回退、C/价格窗口、实际包内容核验。 |
| INV-05 数学正确 | 1、2、3、5 | `-k 'test_model or test_score or test_cli_canonical'`；独立矩阵/系数/预测 oracle、冻结 round-trip、实际单事件手算。 |
| INV-06 来源/报告 | 1、2、3、4、5 | canonical writer 正向 + 单点变异 + `-k test_cli`；三产物数值贯通/写出失败及授权后的真实字节核验，不以合成 ZIP 证明实际覆盖。 |

上表 `-k` 均接 Task 4 的同一 pytest 命令/文件，预期 RC=0；不强加无消费者的固定测试数量或全仓历史数据测试。若新增代码改变共享接口才重新做受影响消费方调查；当前白名单不允许改旧接口。

## 5. 停止条件、投入剪枝与解释上限

- 实现偏离本契约但可在两文件内修复：`BLOCKED_IMPLEMENTATION_DEFECT`，最小修补并回归，不重写 Design。确需白名单外改动且不变语义：`BLOCKED_SCOPE_DRIFT`，先停越界部分，提交有限 Plan 增补并核查受影响身份/授权/证据绑定。需改训练集合、模型、窗口、来源身份、权限或持久化契约：`BLOCKED_SPEC_DRIFT`，退回 Design/Plan，不发明 fallback。
- 精简落实为复用公开 helper、只新增两文件、无共享改动、一次授权批次、正常入口有独立数值断言；不以任意行数强删必要校验。不新增通用 downloader/model registry、任务工单、调参、重采样、完整旧 profile、Recorder 或独立 Verifier；没有新增配置/依赖的必要依据。
- C 是观察旧样本后选择的探索情景，不改写旧 B 主情景。即便个案 d>0，也只说明本事件平方误差下降；d<0 同样不能证伪总体 OI。真实 PIT、完全盲测、总体 CI/Bootstrap/显著性/收益分布均不宣称，重复本事件不增加 N。
- 仅报告本事件 MAE/MFE 与外推诊断；不识别主力/因果或方向资金流。费用、滑点、容量、仓位、净 PnL、资金存活、shadow/live-safe 均为 N/A，不把预测误差改进解释为可交易 Alpha；`RISK_LIVE_TRADING_ENABLED=False` 和全部交易/执行权限保持不变。
- 本文交付后送 Model B 独立审查，再由用户决定是否批准精确 SHA 版本；不自动开始实现、真实消费或研究运行。
