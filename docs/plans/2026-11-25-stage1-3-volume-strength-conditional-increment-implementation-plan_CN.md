# Stage 1.3 量价共振条件增量诊断 Implementation Plan

## Allowed Change Scope

以下白名单仅在本 Plan 经独立审核、用户明确批准对应阶段后生效；当前只起草本文件。

| 类别 | 精确范围 |
| --- | --- |
| Allowed implementation paths | 新建 `scripts/external_signal_shadow/run_stage1_3_volume_strength_conditional_increment.py` |
| Allowed verification paths | 新建 `tests/scripts/external_signal_shadow/test_run_stage1_3_volume_strength_conditional_increment.py` |
| Allowed documentation paths | 执行者 `none`；本 Plan、获批 Design 和旧文档为只读，不更新状态或勾选框 |
| Allowed generated/runtime artifacts | Tasks 1–3 仅新建 `/private/tmp/stage13-volume-strength-implementation-<RUN_ID>/` 的合成输入、日志、缓存、基线和 `source_binding.json`；Task 4 另获批准后仅新建 `/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-25-stage1-3-volume-strength-conditional-increment/<RUN_ID>/` 的结果，不覆盖已有目录 |
| Affected but unchanged | 原 `stage1_3_fixed_universe_diagnostic.py` 领域模块及其 CLI、两份原测试；`stage1_3_models.py`、`stage1_3_candidates.py`、`stage1_3_replay.py`、`stage1_3_metrics.py`、`models.py`；`configs/base.py`、`src/risk/limits.py`。仅只读调用/核对、相关回归及前后摘要检查，不调整共享接口 |
| Forbidden | 白名单外编辑、改动旧研究根或 Design/Plan、解析原始 ZIP、联网/账户接口、重新检测真实信号、扩币/窗口/阈值/退出规则、复用旧 Task 4 授权、改风险配置、添加依赖/配置模块/profile/Verifier/数据库/隔离 worktree/双进程、全库格式化或 `ruff --fix`、清理用户文件、自动 add/commit/push、SSH/deploy/生产采集启停、Producer/paper/live |

日期：2026-11-25（Asia/Shanghai）。状态：`draft_for_independent_review`。

绑定已批准 [Design](../designs/2026-11-25-stage1-3-volume-strength-conditional-increment-design_CN.md)，SHA-256：`a7680d7984c9eba95c12cdda152a989e42d1df25a125bd6d7e2657de20458797`。用户已批准该精确 Design；其文件内保留草稿状态文字，不为改状态重写获批字节。本 Plan 尚未批准实施。

**Goal：** 固定旧 B admitted 队列，以 A 决策点判定放量条件，在同币同周共同支持内计算条件增量，同时报告全共振组收益与依赖性；无支持或负结果也是有效研究交付，不推广 Alpha。

**Architecture / Tech Stack：** 当前主仓同一 Python 3.11.14 环境、标准库，一个顺序研究入口承载小型账本适配与统计；调用现有数学 helper，不重建行情/身份平台。合成测试先验收，实际账本读取与计算另行批准。本稿不执行其中任何 Task。

## 1. 已核对事实、复用及预算

起草时 HEAD：`9712c5580682062416497191250453b267b97040`；新入口与新测试路径均不存在。现有八个未跟踪文件包括两份 Design、两份旧 Plan 和上一单四个 Python 文件，必须原样保留；不能把空 tracked diff 当成工作区干净。执行时重新保存实际基线，不通过提交/清理来制造干净状态。

EG-01 已由 B 关闭。实际源码的字段链已核对：领域模块 440–546 行构造全部决策行、先写参考时间和 trigger_value 后判占用；1137 行原样传递 decision_points；旧 CLI 1233–1250 行逐行序列化，不只写 admitted。A 非接纳行的价格/收益可为 null，本单仅取其条件与参考时间；Y/MAE/MFE 取 B admitted 行。不得从旧 control_keys/d_bps 推导新对照。

| 能力/身份 | 实际调用或适配边界 |
| --- | --- |
| `research.external_signal_shadow.stage1_3_fixed_universe_diagnostic` | 当前实际摘要 `e233a8af052c92b5746e5456c93cbde3a13056172d5151b4e2fab530146e04ee`。导入位置已确认在当前仓库；不导入历史快照或重新实现其数学函数 |
| `build_default_protocol()` / `verify_base_and_safety_config()` | 复用固定协议及安全/阈值检查。前者已调用后者；新 CLI 检查上游两份 JSON 的 protocol 与之严格一致，不接收改币/窗口/阈值的命令行参数 |
| `linear_quantile(values,p)` / `positive_contribution(values)` | 真实用于组分布、名义区间和全共振组正贡献。仅传本次相应组，Top-10% 的 N 是全共振组，不是 964 或仅正收益数 |
| `reduce_block_sample(block_stats,drawn_blocks)` | 每块 `sum_y,n` 是全共振收益和计数；`sum_d,m` 是共同支持共振事件的 `Y_i-同层B-only均值` 总和和计数。消费其 `mu_gross_bps` / `delta_bps` 并映射到本单字段，不平均各块均值 |
| `HistoricalBar` / `build_event_ledger(bars,protocol=...)` | 仅合成测试调用；产生真实上游决策字段后按旧 writer 的字段方式 JSONL 序列化。原测试中的 canonical bars 生成模式可参考，但不修改原测试或用伪造通过标志替代 producer |
| 旧 `analyze_bars` / CLI fetch/analyze / `classify_result` / 组合检测器 | 不用于本次真实运行：会重建队列、读 ZIP、继承旧对照/分流或重新检测；目标不兼容，保持原代码而非改造成通用框架 |

新增负担仅是消费边界检查、固定队列分组/加权、分块统计适配和报告；一个入口不是最小化的充分证明。若上述复用无法成立，先交付具体不兼容事实，按 Rule 16 分流，不自动多建一个领域层、环境或验证平台。

累计上限为 Design §7.3 的 **2.00 人时**，包含 Design、EG-01 补证/审查、本 Plan/审查、实施/返修、测试、一次正式运行及独立审计；不是从本 Plan 开始重新计时，也不借上一单 8h 余额。执行前在既有日志列明已耗实测、未知/估算区间、保守余额及剩余工作，余额不足完成最低验证即停；未知不能写 0。预算停止不是科学证伪。

## 2. 固定输入与分段权限

定义 `R=/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-24-stage1-3-fixed-universe/20261125T062144Z`，仅以下四份数据/来源文件进入本单；路径与摘要均不得由其中的任意字段覆盖：

| 固定输入 | SHA-256 |
| --- | --- |
| `R/results/ledger.jsonl` | `c26e4da31c2836e4c2119aed8ad2120417e5b5339c75d41bc36bc4ee95df1638` |
| `R/results/summary.json` | `624d26de18a22ed9a4474e78cd1e844bf148b29e33a7c4d47050aa80015edec2` |
| `R/coverage.json` | `98818c6b073fedfcca0946fea90f2e725944ab50082827c2b23a255b1e39ed9f` |
| `/private/tmp/stage13-fixed-universe-implementation-20261124T022723Z/remediation_r4/source_manifest.json` | `c6aca62b38dc1e28604062ab6dbd7f4bb3fc6aa96b5734c4c35aecc415d1f997` |

Tasks 1–3 的实施批准仅覆盖代码、合成测试与绑定准备；真实输入只可做流式字节摘要核对，不解析 ledger、不构造真实分组/收益。Task 4 要求代码与合成验收通过后，用户按实际 binding 路径/SHA、代码身份和全新输出目录单独批准一次正式运行及独立只读核算；不得将本 Design 批准或旧批准当作替代。

## 3. 共用执行约定（获批实施后）

在 Bash、仓库根目录执行；先做累计预算核对，再使用下列变量。仅初始化日志目录，不读取真实行情，不建立目标结果目录。

```bash
set -euo pipefail
REPO=$(pwd -P)
PY="$REPO/.venv/bin/python"
CLI=scripts/external_signal_shadow/run_stage1_3_volume_strength_conditional_increment.py
TEST=tests/scripts/external_signal_shadow/test_run_stage1_3_volume_strength_conditional_increment.py
OLD_CORE=src/research/external_signal_shadow/stage1_3_fixed_universe_diagnostic.py
OLD_UT=tests/research/external_signal_shadow/test_stage1_3_fixed_universe_diagnostic.py
OLD_CT=tests/scripts/external_signal_shadow/test_run_stage1_3_fixed_universe_diagnostic.py
DESIGN=docs/designs/2026-11-25-stage1-3-volume-strength-conditional-increment-design_CN.md
PLAN=docs/plans/2026-11-25-stage1-3-volume-strength-conditional-increment-implementation-plan_CN.md
: "${APPROVED_PLAN_SHA:?missing_actual_user_plan_approval_sha}"
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
W="/private/tmp/stage13-volume-strength-implementation-$RUN_ID"
OUT="/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-25-stage1-3-volume-strength-conditional-increment/$RUN_ID"
test ! -e "$W"; test ! -L "$W"; mkdir "$W"
test ! -e "$OUT"; test ! -L "$OUT"
export PYTHONPATH="$REPO/src:$REPO" PYTHONDONTWRITEBYTECODE=1
BASE_SHA=$(git -c core.fsmonitor=false rev-parse HEAD)
printf '%s\n' "$BASE_SHA" > "$W/BASE_SHA"
git -c core.fsmonitor=false status --porcelain=v1 --untracked-files=all > "$W/before.status"
git -c core.fsmonitor=false diff --binary > "$W/before.worktree.patch"
git -c core.fsmonitor=false diff --cached --binary > "$W/before.index.patch"
git -c core.fsmonitor=false ls-files --others --exclude-standard -z > "$W/before.untracked"
while IFS= read -r -d '' p; do shasum -a 256 "$p"; done \
  < "$W/before.untracked" > "$W/before.untracked.sha256"
printf '%s  %s\n' a7680d7984c9eba95c12cdda152a989e42d1df25a125bd6d7e2657de20458797 \
  "$DESIGN" "$APPROVED_PLAN_SHA" "$PLAN" > "$W/authority.sha256"
shasum -a 256 -c "$W/authority.sha256"
```

记录用户实际批准原文；新代码路径已被他人占用或身份不符即停止，不覆盖。当前 Python 3.11.14 与 helper 导入已在起草时核对；执行时再核对版本、模块 `__file__` 及本仓来源，不安装环境。

下文 `runlog` **原样复用**[11-24 Plan §2](2026-11-24-stage1-3-fixed-universe-mean-return-diagnostic-implementation-plan_CN.md) 已有的会话函数定义，仅复制该函数到当前 Bash 会话，不执行旧 Plan 其他命令、不继承旧权限。其作用仅为命令/stdout/stderr/真实 RC 留痕与拒绝日志覆盖，不新增仓内执行脚本。每个门禁立即检查返回值，失败即停，重复使用新的日志名。

所有 RED 均须 RC=1，且本次已收集目标 nodeid、traceback 正是目标未实现/错误数值；导入/collection 错误、无关异常、旧 rc 文件、日志写入失败都不是 RED 通过证据。各 Task 先只写本切片测试；必要接口骨架允许仅抛 `NotImplementedError`，不先实现算法。确认本次 RED 原因后才运行 GREEN，不把整段流程放进一个忽略失败的条件块。

## 4. Task 1：canonical 决策账本 → 固定队列与共同支持

**Dependencies：** §3 的批准/预算/身份基线通过。**Files：** 新 CLI、TEST。**不变量：** `INV-02/03/04`，兼顾 `INV-01/06`。

**接口：** `build_cohort(rows: list[dict], *, protocol: dict) -> dict`。供同一入口调用，返回固定 B 成员及 A 键/状态/条件、分层计数、共同支持与未匹配身份；函数不读文件、不重检测信号。真实运行边界另核对 B=964，纯逻辑合成测试使用 producer 实际生成的自身计数，不伪造 964 行。

- [ ] 写 `test_cohort_canonical_and_a_overlap`：以 `HistoricalBar` 构造下述固定五币完整合成 bars，调用 `build_default_protocol()` 与 `build_event_ledger()`，序列化全部 decision_points 再读回；必须在同一 `ETHUSDT,block_id=0` 层同时产生共振与 B-only 接纳事件，不能仅验证 A 状态或无支持输出。不读取真实 bars。
- [ ] 对照 canonical 无放量版本，证实 B 队列身份不因 A 改变；验证 A admitted / overlap_suppressed 均可入 A=1，not_triggered/null 为 A=0。包含相对走强但自身收益为负的合成边界，不隐加绝对上涨条件。
- [ ] 写 `test_cohort_rejects_missing_duplicate_unknown_and_time`：单点删除 A 行、重复键、不可估计/边界/未知状态、状态与 trigger_value 矛盾、NaN/Infinity、错 feature 窗/available_at/块/entry/exit 必须精确拒绝；不填 A=0。手算 12:00→12:01→12:15→16:15；A 非接纳的价格/收益 null 不得误拒或补算。
- [ ] 最小实现校验与连接：键为 `(candidate,symbol,available_at_ms)`；B 仅 admitted、四个非 BTC 标的；A>=3.0 的语义按 Design §3.2。先按 A 和计数确定同币同周支持，后续 Y 不参与组/支持筛选。删除未放量 B 后不补入此前 B overlap_suppressed；未匹配保留在全组分母。

**Canonical 正向 fixture：** 沿用原领域测试 `_make_rs_canonical_bars()` 的双 RS 向量，仅新增一处成交量脉冲。五币 UTC `[2026-06-08,2026-11-23)` 全部连续 15m bars 默认 `O=H=L=C=100,quote_volume=25`；仅 ETH 覆盖下表，其他输入不改：

| bar_start（UTC） | O / H / L / C / quote_volume |
| --- | --- |
| 2026-06-14 11:45 | 100 / 101 / 100 / 101 / 25 |
| 2026-06-15 11:30 | 100 / 100 / 100 / 100 / 325 |
| 2026-06-15 11:45 | 100 / 101.5 / 100 / 101.5 / 25 |
| 2026-06-15 16:00 | 100 / 103 / 99 / 102 / 25 |
| 2026-06-16 11:45 | 100 / 100.01 / 100 / 100.01 / 25 |

独立预期如下；事件唯一键仍是 `(candidate,symbol,available_at_ms)`，表中 UTC 时点转换为毫秒，不用被测代码生成 expected：

| B 事件 | available_at（UTC） | 参考入场 -> 终点（UTC） | 原 B gross Y | 同时点 A |
| --- | --- | --- | --- | --- |
| k1 | 2026-06-15 12:01 | 12:15 -> 16:15 | `10000*(102/100-1)=200 bps` | `overlap_suppressed`，trigger_value=4.0 |
| k2 | 2026-06-15 16:16 | 16:30 -> 20:30 | `10000*(100/100-1)=0 bps` | `not_triggered`，trigger_value=null |

两事件均为 `relative_strength_vs_btc,ETHUSDT,admitted`。11:30 放量脉冲仅改变 quote_volume，不改变原双 RS 向量的价格/B 条件；12:00 的 A 窗成交额为 `325+3*25=400`，历史中位数 100，倍数 4，且处于其 11:46 已接纳观察的占用期。k2 的 A 窗成交额恢复 100，不触发。

必须断言全 B 接纳键集合恰为 `{k1,k2}`，而非只查目标键存在；Q=2、共振=1、B-only=1、支持共振=1、未匹配共振=0。手算 `mu_joint_all=mu_joint_supported=200`、`mu_control_reweighted=0`、`Delta=200 bps`。这是一项待实施时由真实 producer 核验的合成规格，不是本轮已运行结果；若产生额外事件或不符，先查清源码事实，不能删行/篡改产物凑预期。

```bash
if runlog t1.red "$PY" -B -m pytest "$TEST" -k 'cohort_' \
  --basetemp "$W/t1-red" -p no:cacheprovider -ra; then red_rc=0; else red_rc=$?; fi
test "$red_rc" -eq 1
# 核对本次目标失败原因并留痕后才允许实现及 GREEN。
runlog t1.green "$PY" -B -m pytest "$TEST" -k 'cohort_' \
  --basetemp "$W/t1-green" -p no:cacheprovider -ra
```

**交付验收：** GREEN RC=0，无 skip/xfail；canonical 生产字段穿过本入口，Q、两组、支持/未匹配守恒。负向确认 `STOP=cohort_contract_mismatch` 或 `STOP=cohort_time_mismatch`，不只断言任意异常。

## 5. Task 2：固定分组 → 条件增量、依赖诊断与分流

**Dependencies：** Task 1 GREEN。**Files：** 同 CLI、TEST。**不变量：** `INV-04/05/06`。

**接口：** `summarize_cohort(cohort: dict, *, protocol: dict) -> dict`；`classify_observation(metrics: dict) -> dict`。前者实际调用已有三项统计 helper，并调用后者；后者只执行 Design §6 首个命中分流，不复用旧 classify_result。

- [ ] 写 `test_statistics_hand_oracle_support_weights`，直接使用纯数学向量：层一共振 `[100,0]`、B-only `[20,40]`；层二共振 `[-20]`、B-only `[0,0,0]` bps。独立预期 `mu_joint_supported=80/3`、重加权对照 `20`、`Delta=20/3`；新增无对照层共振 `1000` 时 `mu_joint_all=270`、Delta 不变，未匹配不能消失。这类向量仅证明数学，不冒充上游 artifact。
- [ ] 在现有 TEST 增加 `test_statistics_no_common_support_preserves_marginals`：ETH/块0 仅共振 `+100`、SOL/块0 仅 B-only `+20`，其他块为空。独立预期 Q=2、全共振=1、支持共振=0、未匹配共振=1；`mu_joint_all=100`，B-only 均值=20，支持共振均值/重加权对照/Delta 均为 null，全共振三成本情景均值为 70/50/20；仍为 `not_estimable / stop_due_to_evidence`。另测无共振但 B-only 非空，保留 B-only 分布，不把其均值一同置 null。
- [ ] 写 `test_statistics_block_diagnostics_and_null`：上述两层置于两个市场块，原始块统计分别为 `(sum_y,n,sum_d,m)=(100,2,40,2)`、`(-20,1,-20,1)`；抽 `[0,0]` 应为 `(mu,Delta)=(50,20)`，`[0,1]` 为 `(80/3,20/3)`，`[1,1]` 为 `(-20,-20)`。23 块含零块，跨币同行情一起抽；纯合成 oracle 可直接指定抽样索引，真实运行固定 10000 次/seed 20261123，不暴露寻优选项。
- [ ] 固定原支持和对照；前 11/后 12 块、逐币/逐块剔除均只减原贡献。上述无 1000 版本去掉最佳事件 100 后应有 `mu=-10,Delta=-25`；有 1000 版本删除该未匹配最佳事件时 Delta 不变。bootstrap 及固定诊断对各估计量分别处理分母：无共同支持时仍重计可估计的全组均值；例如无支持向量抽中块0时 mu=100、Delta=null，抽中全空块时两者才都为 null。各自披露空复制/分母，不补抽、不标不完整区间为完整；Delta 不可估计不能使全组结果一起消失。
- [ ] 写 `test_statistics_distribution_cost_and_routing`：调用 linear_quantile 和 positive_contribution，核对全共振/全部B-only/支持共振三个独立分布，旧协议 P05/P10/P25/P50/P75/P90、平均赢亏/盈亏比、最差值、MAE/MFE；正贡献 K 按全共振 N，零正贡献为 null。Y=100 时三成本情景为 70/50/20，Delta 不因双方同扣成本改变；不从包络推导可成交止损。
- [ ] 完整实现 Design §4–§6：按共振事件权重加权各同层全部 B-only，禁止全局组均值直接相减；保留两估计对象与未控制变量限制。两半/所有固定剔除、区间与成本资源判断都实际进入分流，不仅打印出来。

纯逻辑分流测试至少覆盖以下独立预期；“稳定”指两区间完整且下界>0、全部固定诊断两指标均>0：

| 输入场景 | 必须输出 |
| --- | --- |
| 无支持、Delta=null | `not_estimable / stop_due_to_evidence` |
| mu=50、Delta=-1 | `no_increment_observed / stop_fixed_spec_this_round` |
| mu=-20、Delta=10 | `relative_increment_without_positive_gross / stop_fixed_spec_this_round` |
| mu=50、Delta=10，但区间跨零、空复制、两半冲突或某剔除 null | `inconclusive_or_concentrated / pause_for_new_evidence` |
| mu=50、Delta=10，稳定 | `bounded_positive_pattern / consider_independent_validation_only` |
| mu=20、Delta=10，稳定但三个成本情景均值非正 | `bounded_positive_pattern / stop_strategy_development_this_round` |

```bash
if runlog t2.red "$PY" -B -m pytest "$TEST" -k 'statistics_' \
  --basetemp "$W/t2-red" -p no:cacheprovider -ra; then red_rc=0; else red_rc=$?; fi
test "$red_rc" -eq 1
# 核对目标 RED；再作最小实现。
runlog t2.green "$PY" -B -m pytest "$TEST" -k 'statistics_' \
  --basetemp "$W/t2-green" -p no:cacheprovider -ra
```

**交付验收：** GREEN RC=0；每项手算、空集和分流边界通过；保留 `alpha_research_status=evidence_insufficient`、`minimum_economically_meaningful_gain=null`，全部执行/交易与 OOS 推广标志为 False。

## 6. Task 3：受控 CLI → 合成端到端、静态门禁与来源准备

**Dependencies：** Tasks 1–2 GREEN。**Files：** 同 CLI、TEST；W 内绑定和日志。**不变量：** 全部 `INV-01`–`INV-06`，本 Task 不运行真实分组。

**CLI 接口：** `main(argv: list[str] | None = None) -> int`；只提供 `prepare --approved-plan-sha --binding-output --output-root` 与 `run --binding --binding-sha`。没有输入替换、改参数、cost、bootstrap seed 或扩大币池的用户选项。

- [ ] 写 `test_cli_prepare_and_canonical_run`：必须使用 Task 1 固定双 RS/放量向量，通过 `HistoricalBar`→`build_event_ledger()`→全决策 JSONL→本次 CLI 读取/分组/统计→实际输出的完整链路，不 mock 本次 build_cohort/summarize_cohort。独立断言 B 成员键集合 `{k1,k2}`、两组与支持计数、k1 的 `conditional_control_keys` 恰为 `[k2]`、对照均值=0/conditional_d_bps=200，最终四估计量为 200/200/0/200 bps。不得拿纯数学测试或 not_estimable 的 CLI 用例替代此非空支持正向接线；此单周小样本仍因稳健性不足标 `inconclusive_or_concentrated / pause_for_new_evidence`，不要求正向晋级。测试可注入临时合成来源及自身生成的摘要/计数来验证消费边界；仅限 pytest 内存 monkeypatch，不增加真实 CLI 放宽参数、不把合成输入伪称实际 964 事件或真实输入身份已通过。
- [ ] 写 `test_cli_input_identity_path_output_and_mutation`：精确路径/摘要/协议/来源引用、代码变化、输入缺失/解析后越界/相同字节不同根/符号链接、非有限值、重复行、错误时间或原件运行中变化均须拒绝，验证具体 STOP。拦截 socket 连接证明合成测试零网络。CLI 的合法输入读取只限四份固定文件，不沿 coverage/manifest 内的路径递归读取 ZIP、身份原件或任意源码。
- [ ] prepare 仅检查当前 Design/Plan SHA、基线、实际依赖与四输入字节摘要，拒绝既有 binding 文件与既有目标目录；不解析真实 ledger。把新 CLI/TEST、旧 helper、configs/base.py、src/risk/limits.py 的实际路径/SHA、当前解释器真实路径/版本、四输入和全新输出根写进单份 `source_binding.json`；它是来源记录，不是授权凭证，不引入权限 schema/profile。
- [ ] run 先核对用户批准的 binding SHA、固定路径/摘要、代码/环境、输出根及本地安全配置，再解析四输入。核对 summary/coverage 的 manifest_sha256、固定旧 authority 路径/SHA、原 manifest 的 run_root 和协议；不执行原 manifest 中任何取数/loader 指令。实际 B=964、A/B全决策计数与旧 summary 一致，必需字段存在、有限、键唯一、时间/块/价格收益相符，才构造支持及统计。原 summary 的 passed 标签不是语义验证。
- [ ] 输出根只允许 §Allowed Change Scope 指定父目录下一个新子目录，非符号链接、解析后仍在该父目录；存在即拒绝，不续跑。输入与绑定前后摘要一致、结构/分母/数值检查通过后才写 `EXECUTION_FINISHED`，文义仅“执行完毕待独立审计”。身份/时间等错误非零，保留失败日志但无有效成功标记；有效输入的可估计性按下表逐对象处理，不能因 Delta 不可估计提前跳过全部收益/bootstrap。合法证据缺口可 RC=0 交付，不能称研究通过。

| 输入状态 | 必须保留/计算的结果 | 退出与分流 |
| --- | --- | --- |
| 无共振事件 | 共振均值与支持指标/Delta 为 null；保留 B-only 等其他可估计组别描述及完整计数 | RC=0；`not_estimable / stop_due_to_evidence` |
| 有共振但无共同支持 | 全共振均值、分布、成本、MAE/MFE、正贡献和可估计的 bootstrap/固定诊断继续计算；支持相关指标及 Delta 为 null；B-only 非空时保留其描述 | RC=0；`not_estimable / stop_due_to_evidence`，不进入正向资源分流 |
| 部分或全部共同支持 | 正常计算全组与支持内估计对象；披露未匹配范围，区间与剔除按各自分母处理 | RC=0；沿用 Design §6 首个命中规则 |
| 身份、来源、时点或必需字段契约无效 | 只保留失败留痕，不发布有效研究结果或成功标记 | 非零及具体 STOP，不当成有效 not_estimable 研究交付 |

Task 3 的 CLI 合成测试同步覆盖 Task 2 的无共同支持向量，核对实际落盘 `mu_joint_all_bps=100,delta_bps=null`、成本 70/50/20 与 not_estimable 标签；不能只在纯数学函数中验证保留规则。

输出仅三份机器/人工产物加执行结束标记：`members.jsonl` 保留 Q 每个 B 身份、A 来源键/状态/倍数、组/层/支持、原 B 时间/价格/特征/Y/MAE/MFE及新的 `conditional_control_keys/conditional_control_mean_bps/conditional_d_bps`；`summary.json` 使用 `mu_joint_all_bps`、`mu_joint_supported_bps`、`mu_control_reweighted_bps`、`delta_bps` 对应 Design 四个估计量，并保存来源绑定摘要、完整计数/分子分母、23 块、区间空复制数、分布、固定诊断、可比性与分流；`report_CN.md` 人工说明限制。不能覆盖或混用旧 control_keys/d_bps。结构/有限性检查与独立 oracle 足够，不新增 Rule 17 Verifier 或封树工具。

```bash
if runlog t3.red "$PY" -B -m pytest "$TEST" -k 'cli_' \
  --basetemp "$W/t3-red" -p no:cacheprovider -ra; then red_rc=0; else red_rc=$?; fi
test "$red_rc" -eq 1
# 核对目标 RED 后实现 CLI，再执行全部门禁；每个 runlog 非零即停止。
runlog t3.regression "$PY" -B -m pytest "$TEST" "$OLD_UT" "$OLD_CT" \
  --basetemp "$W/t3-regression" -p no:cacheprovider -ra
runlog t3.ruff "$REPO/.venv/bin/ruff" check --no-cache "$CLI" "$TEST"
runlog t3.scanner "$PY" -B .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA" "$CLI"
runlog t3.diff git -c core.fsmonitor=false diff --check
runlog t3.cached git -c core.fsmonitor=false diff --cached --check
runlog t3.authority shasum -a 256 -c "$W/authority.sha256"
runlog t3.prior-files shasum -a 256 -c "$W/before.untracked.sha256"
runlog t3.prepare "$PY" -B "$CLI" prepare --approved-plan-sha "$APPROVED_PLAN_SHA" \
  --binding-output "$W/source_binding.json" --output-root "$OUT"
shasum -a 256 "$W/source_binding.json"
```

**交付验收：** 各 GREEN/静态/准备 RC=0，scanner clean，三文件完整回归无 skip/xfail；不预写测试通过数量。新旧源码/配置与输入的摘要及实际调用证据、基线前后 status/worktree/index patch 交付，独立审计确认只新增 CLI/TEST、原八个未跟踪文件不变。OUT 仍不存在。交付 binding 精确路径/SHA、累计预算及余额，停在 Tasks 1–3 验收，不自行发起 Task 4。

## 7. Task 4：另获授权的一次账本离线诊断

**Dependencies：** Tasks 1–3 独立验收通过；预算余额可覆盖一次运行及最终审核；用户已明确批准实际 binding SHA、代码与输出目录。**Files：** 仓内 none；仅获批全新 OUT 及 W 新日志。**不变量：** 全部。

批准原文存 W 新文件。以下变量必须逐字来自实际用户批准和 Task 3 交付，不用现场重新计算值代替批准值；每条命令失败即停止。

```bash
: "${APPROVED_BINDING_PATH:?missing_actual_binding_path}"
: "${APPROVED_BINDING_SHA:?missing_actual_binding_sha}"
runlog t4.authority shasum -a 256 -c "$W/authority.sha256"
printf '%s  %s\n' "$APPROVED_BINDING_SHA" "$APPROVED_BINDING_PATH" > "$W/task4.binding.sha256"
runlog t4.binding shasum -a 256 -c "$W/task4.binding.sha256"
test ! -e "$OUT"; test ! -L "$OUT"
runlog t4.run "$PY" -B "$CLI" run \
  --binding "$APPROVED_BINDING_PATH" --binding-sha "$APPROVED_BINDING_SHA"
```

run 内先验证全部消费边界，固定 964 个 B 的 A 分类和共同支持计数再计算 Y 分布/Delta；不调用 detector、旧 analyze_bars 或原始行情。先保留未匹配，再按 Design 固定两半/剔除与联合块抽样，不能看到结果后增加子组。RC=0 只代表一次执行完成或如实交付可估计性缺口；不论标签正负都交独立审计，不自动二跑或更换 binding。

前后重新保存 HEAD、status、worktree/index patch、原未跟踪摘要、四输入/源码/绑定摘要；验证允许范围外无变化。输出文件摘要、完整命令和 RC、真实起止时间、累计预算与剩余缺口一并交付。缺口/错误不得用旧日志或估算冒充通过。

### 7.1 独立只读 Completion Audit

审计按当前批准范围声明结论：仅 Tasks 1–3 验收通过不代表本 Plan 全单 complete；Task 4 合法交付及该阶段验收完成后，才可讨论全单工程完成。工程 complete 与 Alpha 成立永久分离。

独立审计不执行 CLI 再开一轮实验；在用户准许的同四输入和本次结果内只读核算：Q=964 与 A 分类/时间联结、完整支持与对照键集合、全组/支持分子分母、Delta、成本扣减、一个固定块复制、固定剔除和标签，核对两种均值未混淆及旧控制列未误用；包括 Delta 不可估计时仍保留其他可估计指标。纯数学复核不得调用本次 summarize_cohort 自证；可用独立短式算术/手算，不新建审计 Recorder、独立 Verifier 或读取 ZIP。

## 8. Design 不变量覆盖与停止路由

| 不变量 | 切片及验证命令/证据 |
| --- | --- |
| `INV-01` | §3 基线、Task 3 prepare/原件摘要/完整回归、Task 4 前后不变性；读真实数据须独立批准，安全函数显式检查 False，不用可被 Python -O 禁用的运行 assert |
| `INV-02` | Task 1 cohort_ 时点反例；Task 3 cli_ 来源/路径/变更反例、prepare 与真实 run 前后摘要；不递归沿上游任意路径读入 |
| `INV-03` | Task 1 canonical 正反例与 Task 4 的 Q=964 实际守恒；A 抑制仍为真条件，不重排 B、不另加自身上涨条件 |
| `INV-04` | Task 1 双 RS canonical 同币同周非空支持及未匹配；Task 2 手算加权、无对照 1000 与零支持保留反例；Task 3 实际成员/对照主键与最终 Delta 接线；Task 4 成员表供独立重计 |
| `INV-05` | Task 2 分块复制、各指标独立空分母、成本/分布/剔除/标签测试；Task 3 落盘的有支持正向及无支持保留结果、完整回归；Task 4 结果只标已暴露探索，不输出可执行收益 |
| `INV-06` | §1 真实复用接口与 Tasks 1–3 实际调用检查，阶段预算记录，Task 2 Design §6 首个命中分流，Task 4 无二次试跑/扩展 |

既定范围内实现错误按 `BLOCKED_IMPLEMENTATION_DEFECT` 局部修；仅需增加路径/工作但语义不变按 `BLOCKED_SCOPE_DRIFT` 先停止并申请有限 Plan 增补；需要改变固定队列、对照/窗口/阈值、读取权限或上游冻结语义按 `BLOCKED_SPEC_DRIFT` 停止，不借实现便利放宽 Design。

本 Plan 先交 B 独立审核，再由用户按实际 SHA 批准相应阶段。当前仅文档起草，不开启 implementation、真实分组运行、commit、push、deployment、SSH、生产 runtime、Producer、paper 或 live 权限。
