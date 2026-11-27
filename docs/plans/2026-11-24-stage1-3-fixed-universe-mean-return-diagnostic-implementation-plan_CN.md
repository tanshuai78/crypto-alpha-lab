# Stage 1.3 固定成熟现货币池平均收益增量诊断 Implementation Plan

## Allowed Change Scope

以下白名单仅在本 Plan 经独立审核、用户明确批准相应阶段后生效；本次仅起草文档。

| 类别 | 精确范围 |
| --- | --- |
| Allowed implementation paths | 新建 `src/research/external_signal_shadow/stage1_3_fixed_universe_diagnostic.py`；新建 `scripts/external_signal_shadow/run_stage1_3_fixed_universe_diagnostic.py` |
| Allowed verification paths | 新建 `tests/research/external_signal_shadow/test_stage1_3_fixed_universe_diagnostic.py`；新建 `tests/scripts/external_signal_shadow/test_run_stage1_3_fixed_universe_diagnostic.py` |
| Allowed documentation paths | 执行者 `none`；本 Plan 由作者新建，执行时为只读获批契约，不改状态、勾选框或 SHA |
| Allowed generated/runtime artifacts | Tasks 1–3 仅新建 `/private/tmp/stage13-fixed-universe-implementation-<RUN_ID>/` 的合成输入、测试缓存、基线、日志和 `source_manifest.json`；Task 4 另获批准后仅新建 `$HOME/crypto-alpha-lab-evidence/2026-11-24-stage1-3-fixed-universe/<RUN_ID>/`，保存 raw、coverage、账本和结果，不覆盖既有目录 |
| Affected but unchanged | `configs/base.py`、`src/risk/limits.py`、`stage1_3_models.py`、`stage1_3_candidates.py`、`stage1_3_replay.py`、`stage1_3_metrics.py`、它们的现有测试、上游 `external_signal_shadow/models.py`；以只读接口核对、定向回归及前后摘要验证兼容 |
| Forbidden | 白名单外编辑、修改旧 Design/summary/R10 或生产 D/F、增设配置模块/依赖/profile/Verifier/数据库、历史 worktree/双解释器隔离、读取既有受限归档、账户接口、`ruff check --fix .`、`git clean -fdx`、重置用户改动、自动 add/commit/push、SSH/deploy/采集启停、paper/live/Producer 启用 |

日期：2026-11-24（Asia/Shanghai）。状态：`draft_for_independent_review`。

绑定已批准 [Design](../designs/2026-11-23-stage1-3-fixed-universe-mean-return-diagnostic-design_CN.md)：SHA-256 `8622d06b75c17a7bdfd103224cb11b75d147a7b92b1f3a06be6b81cd4417bd23`。用户批准只覆盖该 Design，不是本 Plan 的实施授权。Design 文件保留起草时的状态文字，审批依据为用户批准语句与实际摘要，不为改状态重写获批文件。

**Goal：** 复用旧候选及单事件时间/收益函数，交付一次固定五币、两个候选分别计算的探索诊断；数据不足或负结果都是允许产出，不恢复旧路线资格。

**Architecture / Tech Stack：** 当前主仓同一 Python 3.11+ 环境；一个领域模块承载适配、接线和统计，一个 CLI 顺序执行准备/取数/离线分析，使用标准库及已有项目函数，不训练模型、不引入进程隔离框架。两份新测试分别验证领域结果和 CLI/I/O 边界。

## 1. 冻结事实、接口与实施基线

起草时 HEAD：`9712c5580682062416497191250453b267b97040`；已有未跟踪文件为获批 Design 与 `2026-11-23-stage1-3-spot-universe-constructability-preflight-brief-plan_CN.md`。四个拟新增 Python 路径均不存在。执行前记录实际状态，不要求为了“干净”而提交或删除已有文件；路径已被其他工作占用时先报告，不覆盖。

读取源码确认的主要调用边界（不是本次运行兼容性通过声明）：

| 能力 | 新代码的实际调用/适配承诺 |
| --- | --- |
| `HistoricalBar(symbol, bar_start_ms, bar_end_ms, open_price, high_price, low_price, close_price, quote_volume)` | CSV 适配先检查有限值、精确 symbol/对象时间集，再用 canonical 构造器；其本身的正数比较不能代替 NaN/Infinity 拒绝，`compute_bar_coverage` 的首末范围比例也不能代替固定全区间完整性 |
| `detect_volume_spike_1h(*, symbol, current_1h_quote_volume, same_hour_historical_volumes, event_time_ms, threshold, min_samples)` | 用本轮此前 7d、同 UTC 结束小时历史调用，`threshold=base.EXTERNAL_SIGNAL_STAGE1_3_VOLUME_SPIKE_THRESHOLD`、最少样本读同名 base 常量，不复写检测算法 |
| `detect_relative_strength_vs_btc(*, symbol, alt_1h_return, btc_1h_return, historical_spread_returns, event_time_ms, z_threshold, min_samples)` | 按末时点对齐 BTC，当前 spread 不先入历史；标准差口径保留 `pstdev`，BTC 不作为该候选研究标的 |
| `historical_available_at_ms(bar, *, configured_lag_ms)` / `select_entry_bar(bars, *, event_time_ms, entry_delay_bars)` | 实际调用生成可得时点并选择严格晚于该时点的第一根 bar；15m 连续输入已核验后才定位 entry_index，不在新实现里偷偷改成当前 bar 成交 |
| `compute_forward_metrics_from_entry_index(sorted_bars, *, entry_index, cost_round_trip_bps, signed_direction)` | 明确传 `0.0` 与 `1`；消费 `terminal_return_4h_net_bps` 作为 gross、`entry_open_price`、`exit_close_price`、`mfe_4h_bps`、`mae_4h_bps`；其附带 15m 结果不成为新增研究终点 |
| 旧 orchestrator / baseline / summary / R10 loader | 不导入或调用；不能继承固定 50 bps、中位数门禁、全时期抽样/近小时回退或旧准入文件要求 |
| `research.cost_model` | 不调用默认 maker/taker/slippage；按 Design 将总情景 30/50/80 bps 各扣一次，不制造真实成本 |

已有策略参数仅从 `configs/base.py` 只读取得并检查其等于 Design；新增日期、块抽样和资源上限是获批研究协议元数据，显式放入 CLI 生成的来源清单并向核心传递，不新建配置 SSOT，也不提供任意改币/窗口/阈值的 CLI 开关。

### 1.1 资源与阶段权限

累计上限沿用 Design 的 **8.00 人时**，包括此前 Design/返修/B 审核、本 Plan/审核和后续实施、等待、审计。执行前先列明已耗实际值、估算和未知区间，不从零重置；保守剩余预算不足以覆盖实施及最终审核时停止并报告，不能删控制或验证来凑预算。

Tasks 1–3 的新增执行估算约 2.5–4 小时，Task 4 约 0.5–1 小时，独立审计约 0.75–1.25 小时，均为不保证实现的规划区间，不是已获额外预算。真实运行前再次核对累计与余额；未知历史耗时不能填为 0。

默认实施申请应仅包含 **Tasks 1–3：本地代码、合成测试、来源准备**。Task 4 的真实读取/联网/收益计算另按 `source_manifest.json` 实际路径、SHA、代码身份和全新输出目录授权；不得因用户批准一般 Plan 实施就自动执行 Task 4。

## 2. 共用执行约定（仅获实施批准后）

在仓库根目录使用 Bash，记录实际 UTC `RUN_ID`。下列变量贯穿各 Task；`W` 必须原先不存在，所有测试 temp/cache 放在其中，禁止把时间戳示例目录当作实际授权目录。

```bash
set -euo pipefail
REPO=$(pwd -P)
PY="$REPO/.venv/bin/python"
RUFF="$REPO/.venv/bin/ruff"
DESIGN=docs/designs/2026-11-23-stage1-3-fixed-universe-mean-return-diagnostic-design_CN.md
DESIGN_SHA=8622d06b75c17a7bdfd103224cb11b75d147a7b92b1f3a06be6b81cd4417bd23
PLAN=docs/plans/2026-11-24-stage1-3-fixed-universe-mean-return-diagnostic-implementation-plan_CN.md
# APPROVED_PLAN_SHA 必须来自用户实际批准语句，不得以现场计算值代替授权值。
: "${APPROVED_PLAN_SHA:?missing_user_approved_plan_sha}"
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
W="/private/tmp/stage13-fixed-universe-implementation-$RUN_ID"
test ! -e "$W"
mkdir "$W"
export PYTHONPATH="$REPO/src:$REPO" PYTHONDONTWRITEBYTECODE=1
CORE=src/research/external_signal_shadow/stage1_3_fixed_universe_diagnostic.py
CLI=scripts/external_signal_shadow/run_stage1_3_fixed_universe_diagnostic.py
UT=tests/research/external_signal_shadow/test_stage1_3_fixed_universe_diagnostic.py
CT=tests/scripts/external_signal_shadow/test_run_stage1_3_fixed_universe_diagnostic.py
BASE_SHA=$(git -c core.fsmonitor=false rev-parse HEAD)
printf '%s\n' "$BASE_SHA" > "$W/BASE_SHA"
git -c core.fsmonitor=false status --porcelain=v1 --untracked-files=all > "$W/before.status"
git -c core.fsmonitor=false diff --binary > "$W/before.worktree.patch"
git -c core.fsmonitor=false diff --cached --binary > "$W/before.index.patch"
printf '%s  %s\n' "$DESIGN_SHA" "$DESIGN" "$APPROVED_PLAN_SHA" "$PLAN" > "$W/authority.sha256"
shasum -a 256 -c "$W/authority.sha256"
```

保存用户实际批准原文至 W 的既有执行日志/文本，并保存既有未跟踪文件的内容摘要（不能只记录文件名）；执行后验证这些原件未变。只为真实消费绑定读取相关源码和配置，不读取 `data/` 研究归档。

```bash
git -c core.fsmonitor=false ls-files --others --exclude-standard -z > "$W/before.untracked"
while IFS= read -r -d '' p; do shasum -a 256 "$p"; done \
  < "$W/before.untracked" > "$W/before.untracked.sha256"
```

每个门禁保存命令、stdout/stderr、真实退出码，失败即停；不得用 `|| true`、日志中的 PASS 字样或 `tee` 的退出码代替被测命令状态。可在 W 使用下面的会话函数，不为其另建仓内框架：

```bash
runlog() (
  local name="$1" rc
  shift
  # 子 shell 限定 FD 与 noclobber；处于 if 条件时仍逐项检查证据写入。
  set -C
  for suffix in command log rc; do
    if test -e "$W/$name.$suffix" || test -L "$W/$name.$suffix"; then
      printf 'STOP=log_name_already_used\n' >&2; exit 74
    fi
  done
  if ! printf '%q ' "$@" > "$W/$name.command"; then
    printf 'STOP=log_command_write_failed\n' >&2; exit 74
  fi
  if ! printf '\n' >> "$W/$name.command"; then
    printf 'STOP=log_command_write_failed\n' >&2; exit 74
  fi
  if ! exec 3> "$W/$name.log"; then
    printf 'STOP=log_open_failed\n' >&2; exit 74
  fi
  if "$@" >&3 2>&1; then rc=0; else rc=$?; fi
  if ! exec 3>&-; then
    printf 'STOP=log_close_failed\n' >&2; exit 74
  fi
  if ! printf '%s\n' "$rc" > "$W/$name.rc"; then
    printf 'STOP=log_rc_write_failed\n' >&2; exit 74
  fi
  exit "$rc"
)
```

RED 只能是目标用例已收集后因未实现行为失败（RC=1）；缺解释器/导入错误、任意无关异常或 collection error 不是有效 RED。测试先写；必要时只增加抛 `NotImplementedError` 的接口骨架以使目标断言可收集，随后最小实现至 GREEN。每次只运行本 Task 已实现的选择集，Task 3 再无过滤运行全部新测试及指定回归。重复验证须使用新的日志名（如 `.r2`），不覆盖之前的真实结果。

三个 RED 调用必须先捕获**本次函数实际返回的 RC**，仅本次 RC=1 才读取并核对该次新生成的 rc 文件；日志碰撞或任何证据写入失败统一 RC=74，collection error 等保留子命令真实 RC，均不得被磁盘旧 RC=1 替代。代码块的 RC 核对仍不是自动接受 RED：执行前在现有执行日志记明本轮目标 nodeid、独立 expected 与预期失败机制，执行后核对本次完整 pytest 失败节点及 traceback 全部对应这些预期，不得以任意异常、缺少结束记录或只 grep 一个错误词通过。确认并留痕前，不得调用紧随其后的 GREEN 命令。

作者/执行者可在仓外用一次性合成命令故障注入核对该会话函数：真实目标失败 RC=1 可进入证据核对；旧 RC=1 碰撞、关键证据写入失败、collection error 和未实现时意外全绿均必须 STOP。不新增仓内 Shell 脚本或执行框架。

## 3. Task 1：canonical 合成 bars → 两候选事件账本

**Dependencies：** 无；先通过 §2 身份/基线检查和预算核算。对应 `INV-01/03/04/05/09`。

**Files：** 新建 CORE、UT；后续 Tasks 可在这两个白名单文件内续建，不改共享 helper。

**接口：** `build_event_ledger(bars: list[HistoricalBar], *, protocol: dict) -> dict`。协议由固定 Design 导出，包含边界/23 块等元数据；结果包含按候选的决策点、可估计性、触发/边界/重叠/接纳状态及事件参考窗。不把 `CandidateEvent` 手写 dict 当作已有检测函数的正式产出。

- [ ] 先核对同一个 `$PY` 的版本、真实模块导入和 `__file__` 来源。只导入 config、models、candidates、replay、metrics，不调用 loader/旧 CLI；Python <3.11、缺依赖、来源不是当前 REPO 或需要另一解释器/历史 worktree 即 STOP，不自动安装环境。
- [ ] 读取 base 后用显式 `if ...: raise ...` 检查五币、3.0/1.5、7d、5/48、15m/4/16 bars、60000ms、entry delay=1、成本 tuple 与 Design 一致；安全检查 `RISK_LIVE_TRADING_ENABLED=False`、`RiskLimits().live_trading_enabled=False`、本地 Producer=False。运行控制不能依赖可被 `-O` 禁用的 Python assert；pytest 断言不受此实现限制。
- [ ] 用 `HistoricalBar` canonical 构造器生成固定 168 天五币合成序列（2026-06-08 至 11-23，15m），不读取任何真实行情。基线 OHLC=100、每 bar quote volume=25；仅 ETH 在 2026-06-16 11:45 的 bar volume=325。其 12:00 结束窗为 400，对历史中位数 100，应正式触发一次并接纳；后三个同一异常窗口的滚动触发应被占用规则抑制，不被改写为三个独立机会。
- [ ] 合成接纳事件最早入场为 12:15，末 bar 为 16:00–16:15；将该末 bar close=101、high=102、low=99，其余 bar OHLC=100。调用真实收益 helper 后应手算得到 gross=100 bps、MFE=200 bps、MAE=-100 bps；不得用被测 helper 自算 expected。
- [ ] 独立相对强弱向量：历史 spread 为 24 个 -0.01、24 个 +0.01，median=0、pstdev=0.01；当前 alt=0.015、BTC=0 时 z=1.5，应触发。当前 0.0149 不触发，BTC 不参与，零方差/不足 48 条均不可估计。边界测试防止当前值先进入自身历史。
- [ ] **另建 RS canonical 正向行情**，不能只沿用上面的量异常行情或单独 detector 向量：仍为完整 168 天五币，所有 open=100、quote volume=25、其余 OHLC=100；仅 ETH 的四根 bar 更改如下：2026-06-14 11:45 close=101，2026-06-15 11:45 close=101.5，2026-06-15 16:00 close=102/high=103/low=99，2026-06-16 11:45 close=100.01。未另指定的 high/low 取 max/min(open,close)，BTC 基线保持 100；全部用 `HistoricalBar` 构造器生成，独立于量异常用例，不手写“已检测”事件。
- [ ] 对该 RS 行情，通过 `build_event_ledger()` 核对指定 2026-06-15 12:00 结束窗口：此前 7d 有 672 个 spread，其中仅 06-14 12:00 为 +0.01，其余 671 个为零，因此 median=0、pstdev=`0.01*sqrt(671)/672`；当前 alt=0.015、BTC=0，z=`0.015/(0.01*sqrt(671)/672)`，严格大于 1.5。事件 available_at=12:01、entry=12:15、exit=16:15，参考价 100→102，gross=200 bps、MFE=300 bps、MAE=-100 bps；必须检查实际历史 spread 的来源时间与 BTC 对齐，不只检查 event_count>0。
- [ ] BTC 对齐反例使用该行情的独立副本：只将 2026-06-15 11:45 的 BTC bar close/high 改为 101.5，open/low 仍 100；目标同窗 BTC 收益变为 0.015、历史不变、spread=0，指定 12:00 事件应消失。只断言该主键不再触发，不错误要求整个 RS 家族为零事件或其他统计不变。
- [ ] 验证 7d 左边界保留、早于边界剔除、UTC 结束小时而非日期或入场小时分组；同币同候选占用独立，两候选不共享资金。周末越界结果、评价区间外和预热事件单列；修改未来 bars 不得改变过去触发与可得时间。

环境前检使用同一 `$PY`，先检查版本再导入真实依赖，不读取行情；预期 RC=0：

```bash
"$PY" -B - "$REPO" <<'PY'
import sys
from pathlib import Path
if sys.version_info < (3, 11):
    raise SystemExit('STOP=python_version_mismatch')
from configs import base
from research.external_signal_shadow import stage1_3_models as models
from research.external_signal_shadow import stage1_3_candidates as candidates
from research.external_signal_shadow import stage1_3_replay as replay
from research.external_signal_shadow import stage1_3_metrics as metrics
from risk import limits as risk_limits
root = Path(sys.argv[1]).resolve()
origins = (
    (base, 'configs/base.py'),
    (models, 'src/research/external_signal_shadow/stage1_3_models.py'),
    (candidates, 'src/research/external_signal_shadow/stage1_3_candidates.py'),
    (replay, 'src/research/external_signal_shadow/stage1_3_replay.py'),
    (metrics, 'src/research/external_signal_shadow/stage1_3_metrics.py'),
    (risk_limits, 'src/risk/limits.py'),
)
for module, relative_path in origins:
    if Path(module.__file__).resolve() != root / relative_path:
        raise SystemExit('STOP=module_origin_mismatch')
if (base.RISK_LIVE_TRADING_ENABLED is not False
        or risk_limits.RiskLimits().live_trading_enabled is not False
        or base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is not False):
    raise SystemExit('STOP=safety_config_mismatch')
print('ENVIRONMENT_AND_SAFETY_OK')
PY
```

将此命令原文/stdout/stderr/RC 保存至 W；本段是实际运行兼容性检查，前文源码核对不能替代。其后执行本 Task 明列的 base 参数等值检查，失败先停止，不修改参数适配。

验证命令与期望：

```bash
# 写用例及最小骨架后：预期 RC=1，且日志指向目标未实现行为。
red_rc=0
if runlog t1.red "$PY" -m pytest -q "$UT" -k 'ledger or signal or timing' \
    --basetemp "$W/t1-red" -p no:cacheprovider; then
  red_rc=0
else
  red_rc=$?
fi
if test "$red_rc" -ne 1; then printf 'STOP=invalid_current_red_rc_%s\n' "$red_rc"; exit 1; fi
if ! recorded_rc=$(cat "$W/t1.red.rc"); then printf 'STOP=red_rc_unreadable\n'; exit 74; fi
if test "$recorded_rc" != "$red_rc"; then printf 'STOP=red_rc_mismatch\n'; exit 74; fi
# 此时仍须按 §2 核对本次完整失败节点/原因并留痕，未确认不能执行下一条 GREEN。
# 实现后：预期 RC=0；不得通过 skip/xfail 绕过这些用例。
runlog t1.green "$PY" -m pytest -q "$UT" -k 'ledger or signal or timing' \
  --basetemp "$W/t1-green" -p no:cacheprovider
```

**交付：** 可独立验证的合成事件账本、手算 oracle 与 RED/GREEN 日志。旧事件数/summary 不是比对目标，本轮不输出任何真实结果。

## 4. Task 2：同一账本 → 确定性对照、统计和准确分流

**Dependencies：** Task 1 GREEN。对应 `INV-05/06/07/08/09`。**Files：** CORE、UT。

**接口：** `analyze_bars(bars: list[HistoricalBar], *, protocol: dict) -> dict` 实际调用 Task 1 账本和真实 helper，返回两个候选的账本/对照映射/summary。仅为易独立验证的数学边界提供 `positive_contribution(values)` 与 `classify_result(metrics)` 等同模块函数，不另造框架或模型类。

- [ ] TDD 冻结 Design §5 的 C_i：同币、同块、同 available_at UTC 小时、同自身/BTC r1h 负/零/正、当点不触发 k 且没有已有占用；匹配键不得偷换成 volume 状态或当前价格。对照可以在事件之后，但不能按未来信号排除。使用全部合格对照，重复引用保留，无小时/块/符号回退。
- [ ] 构造逐个仅改变一项条件的拒绝例、共享对照的权重例和后续出现新信号仍可作为当前参考点的例；手算 `y=[100,-20]`、对照均值分别 `[20,0]`，得到 mu=40、delta=30，而不是按对照数量加权事件。常数成本下 delta 不变、mu 各减 30/50/80 一次。
- [ ] 对 Task 1 **两套**完整 canonical bars 分别走 `build_event_ledger()` 和 `analyze_bars()` 的真实检测→接纳→收益→对照→summary；量异常用例的指定事件 gross/delta 均为 100 bps。RS 用例的指定 06-15 12:00 事件，其 C_i 只能是 06-16 12:01 的 ETH 点：自身 r1h=0.0001、BTC=0、当点不触发且未被占用，对照参考价 100→100，故指定事件 d_i=200 bps。
- [ ] RS 行情还应在 06-15 16:15 因终点价格脉冲产生第二个接纳事件（available_at=16:16，在首事件退出后；entry=16:30、exit=20:30、gross=0），其同小时同正向状态无对照。因此该家族应为接纳 2、匹配 1、未匹配 1，mu_gross=100 bps、匹配子集 delta=200 bps，分流为 `inconclusive_or_concentrated / pause_for_new_evidence`，而非把合成覆盖当 Alpha 支持。保存两个事件及指定 C_i 的精确主键，并验证 BTC 对齐反例使指定首事件消失。内部纯统计小向量仍允许直接构造，但不能代替两个候选的完整 canonical 正向接线或声称实源覆盖。
- [ ] 保存事件和对照主键 `(candidate, symbol, available_at)`、时间/参考价及派生值；按 Design 的先特征、再边界、后触发/占用顺序互斥分类。在各候选适用币种内，评价决策点总数=特征不可估计+边界剔除+未触发+重叠抑制+接纳；仅在特征可估计且边界合格的点上，触发数=重叠抑制+接纳，接纳=匹配+未匹配。相对强弱的 BTC 不混进适用币种分母，不通过填零制造守恒。
- [ ] 所有点估计与区间从原始分子/分母重算；空样本/零分母为 null。线性插值分位数用已知向量 `[0,10,20,30]`，P25=7.5、P50=15、P75=22.5；Top-K 用 Design 单正收益十事件例得到三项均 100%，并验证全负/全零/空集均 null。
- [ ] Bootstrap 同时重采样所有币、两候选共同的 23 个完整块，10000 次、seed=20261123；不在每个候选内部另取不同随机序列。可以缓存每块 sum/count 加速，但必须与账本权重严格相同；无事件块不删除，空分母复制计数、不补抽、不填零，阻断完整正向区间。
- [ ] 独立检查块归约：块 A 的 `(sum_y,n,sum_d,m)=(200,2,100,2)`，块 B 为 `(-100,1,-50,1)`；抽 A,A 得 mu=100、delta=50，A,B 得 mu=100/3、delta=50/3，B,B 得 mu=-100、delta=-50。该纯归约 oracle 不是将真实运行改为两块或三次复制。
- [ ] 按 Design §8 自上而下首个命中分流。必须覆盖 `(-20,+50)` 为 `relative_increment_without_positive_gross`、`(+20,-50)`/`(-20,-50)` 为 `no_increment_observed`、`(-20,null)` 为 `not_estimable`；再覆盖部分匹配优先、均值/delta=0、区间下界=0、空复制及有效双正向。不得把子集 delta 贴成全候选的正/负结论。
- [ ] 固定前 11/后 12 块、逐币/块及最佳事件剔除均只重计原账本，不重新补入被抑制事件；全候选、每币、每块和全部成本情景均可追溯。连续亏损按币/候选排序，不拼跨币序列；不得报告资金组合 PnL 或 MAE/MFE 的可成交收益。

```bash
# RED 模式同 Task 1：要求目标断言失败 RC=1，不能是导入/收集错误。
red_rc=0
if runlog t2.red "$PY" -m pytest -q "$UT" -k 'control or summary or bootstrap or routing' \
    --basetemp "$W/t2-red" -p no:cacheprovider; then
  red_rc=0
else
  red_rc=$?
fi
if test "$red_rc" -ne 1; then printf 'STOP=invalid_current_red_rc_%s\n' "$red_rc"; exit 1; fi
if ! recorded_rc=$(cat "$W/t2.red.rc"); then printf 'STOP=red_rc_unreadable\n'; exit 74; fi
if test "$recorded_rc" != "$red_rc"; then printf 'STOP=red_rc_mismatch\n'; exit 74; fi
# 按 §2 核对本次完整失败节点/原因并留痕后，才允许 GREEN。
runlog t2.green "$PY" -m pytest -q "$UT" --basetemp "$W/t2-green" -p no:cacheprovider
```

**交付：** 无网络的完整合成分析链和逐项 oracle；不把合成交易对、SHA 或 outcome 当成实源证据。

## 5. Task 3：模拟传输 → CLI 门禁、来源准备及本地验收交接

**Dependencies：** Task 2 GREEN。对应 `INV-01/02/03/07/08/09`。**Files：** CORE、CLI、CT（必要时在 UT 补接口回归）。

### 5.1 同一 CLI 的三个明确动作

`main(argv) -> int` 提供下列固定入口，不提供研究规则优化参数。`prepare` 不访问网络、归档或真实收益；只有未来明确调用 `fetch` 才允许公开请求；`analyze` 无网络能力调用。普通预期错误输出稳定 `STOP=<reason>` 且非零，关键 GO/STOP 不用 Python assert。

```bash
# Tasks 1–3 内唯一允许调用的非测试 CLI 动作：只生成元数据。
TARGET_RUN="$HOME/crypto-alpha-lab-evidence/2026-11-24-stage1-3-fixed-universe/$RUN_ID"
MANIFEST="$W/source_manifest.json"
test ! -e "$TARGET_RUN"
runlog t3.prepare "$PY" -B "$CLI" prepare --repo-root "$REPO" \
  --run-root "$TARGET_RUN" --output "$MANIFEST" \
  --design-sha256 "$DESIGN_SHA" --plan-sha256 "$APPROVED_PLAN_SHA"
shasum -a 256 "$MANIFEST"
```

来源清单只承担可复算来源/对象绑定，不是新的权限 JSON 或自动授权器。最少记录：Design/Plan 路径与摘要、实际 HEAD、两个新实现及实际复用源码/配置摘要、固定研究协议、135 组对象的 symbol/月份或日期/ZIP 和 CHECKSUM 精确 URL/CSV 名称及预期日期集、五币身份核查来源、唯一目标输出目录和 Design 资源上限。不得包含账户信息或把未知的未来 ZIP 摘要先编造为固定值。

结构为 JSON object：版本为整数 1，身份/协议/资源/输出位置为具名对象，源码绑定及归档对象为列表；所有必需路径/URL/SHA 字段为非空字符串，对象唯一键及日历集合必须与固定 135 组完全一致。prepare 和两个消费者共同校验必需字段类型、协议值与身份，不能默默忽略缺字段或接受额外币种/URL/研究开关；SHA 匹配不能代替这些结构/语义检查。完整字段名由实现者在上述结构内保持一致，清单冻结后任何字节变化均使原批准摘要失效，不因此建立新的长期上游 Schema。

五币身份依据须在真实运行前列明可复核出处：旧 Git 中的精确名单及 Binance Spot 来源接线、所需官方身份资料、目标区间需要核查的证据与限度；不能只写“主流币所以通过”。若资料不足，保留资格未证实并停止 Task 4 授权申请，不偷偷加入全市场公告爬取。需要新增必要官方资料 URL 时先在未批准的清单中明确列出，再交实际清单 SHA 批准，不在真实读取中自由扩展请求范围。

### 5.2 适配/I/O 的 RED → GREEN

- [ ] 在 CT 用测试临时目录与模拟 HTTP 返回验证 prepare/fetch/analyze；所有真实 socket 请求由测试禁止。测试包从 canonical `HistoricalBar` 字段按官方 12 列结构序列化成微秒 CSV，再 ZIP，摘要用这些实际合成字节计算；它只证明适配接线，不声称官方已发布或历史覆盖。
- [ ] 内容入口先核对 CHECKSUM 目标文件名及摘要，再核对单 CSV 成员名称、字段/有限值、微秒 open/close 规则、对象日期范围、完整预定 bar 集合及 OHLC，最后构造 `HistoricalBar`。禁止 `extractall`；不把零成交额当停牌或补零，也不因有效归档包外没有行就自动判零成交。
- [ ] 对所有五币、全部预热与评价起点进行严格检查，通过后才生成 `coverage.json` 的合格结果；模拟缺包、重复、缺行、错误 symbol/字段/单位、NaN/Infinity 和错误 checksum 均必须非零并给出目标 STOP，结果目录不能出现有效成功标记。
- [ ] 传输累计计数含失败、元数据及重试；先检查第 321 次请求不发生，单次接收读取受剩余字节预算限制，不能整包下载后再检查 256 MiB。串行 >=1s、timeout<=20s；仅 TLS/timeout 同对象额外一次且全程最多 20 次，失败尝试分开保留，不覆盖原件。访问拒绝/摘要冲突立即停止，不关闭 TLS 验证、不自动切 URL、跟随不受控重定向或改包。
- [ ] 模拟 `prepare` 的零网络/零数据读取、analyze 的零网络、原始输入只读及异常中断。fetch 必须拒绝已经存在的 TARGET_RUN；analyze 仅接受由同一绑定 fetch 生成并校验通过的 RUN，且 `RUN/results/` 原先不存在。来源清单/coverage 不符或 results 已存在均拒绝，不覆盖。失败目录保留，重跑需要新目录/适用批准，不续写旧证据冒充新一轮；不建立重启恢复状态机。
- [ ] analyze 消费前重新核对来源清单、批准摘要、实现/复用源码身份、实际 ZIP 与 coverage 来源关系及内容合同，不能仅信任写过的 `coverage=true`。只读取清单列明文件，无任意路径/样本拼接入口；输入期间或结束摘要改变即报失败，不发布成功。
- [ ] 最终 JSON 使用有限数/null（`allow_nan=False`），完成所有账本和 summary 后最后写 `EXECUTION_FINISHED` 文本标记，含义仅“该命令执行完待独立审计”，不是审计 complete 或任何运行准入。部分结果/缺标记不可作为成功消费。

稳定错误至少区分 `source_manifest_mismatch`、`source_identity_mismatch`、`existing_output_root`、`checksum_mismatch`、`coverage_incomplete`、`nonfinite_value`、`request_limit`、`download_byte_limit`、`access_restricted`；负向测试须证明相应 STOP，而非只证明 RC 非零。其余错误保留原始上下文，不能宽泛捕获后回退零收益。

```bash
# 首轮只增加 CT 用例及接口骨架；目标未实现行为应 RED=1。
red_rc=0
if runlog t3.red "$PY" -m pytest -q "$CT" \
    --basetemp "$W/t3-red" -p no:cacheprovider; then
  red_rc=0
else
  red_rc=$?
fi
if test "$red_rc" -ne 1; then printf 'STOP=invalid_current_red_rc_%s\n' "$red_rc"; exit 1; fi
if ! recorded_rc=$(cat "$W/t3.red.rc"); then printf 'STOP=red_rc_unreadable\n'; exit 74; fi
if test "$recorded_rc" != "$red_rc"; then printf 'STOP=red_rc_mismatch\n'; exit 74; fi
# 按 §2 核对本次完整失败节点/原因并留痕后，才允许 GREEN。
# 补实现后运行以下全部 GREEN 门禁，任一非零停止。
runlog t3.cli "$PY" -m pytest -q "$CT" --basetemp "$W/t3-cli" -p no:cacheprovider
runlog t3.regression "$PY" -m pytest -q "$UT" "$CT" \
  tests/research/external_signal_shadow/test_stage1_3_models.py \
  tests/research/external_signal_shadow/test_stage1_3_candidates.py \
  tests/research/external_signal_shadow/test_stage1_3_replay.py \
  tests/research/external_signal_shadow/test_stage1_3_metrics.py \
  tests/research/external_signal_shadow/test_stage1_3_config.py \
  --basetemp "$W/t3-regression" -p no:cacheprovider -ra
runlog t3.ruff "$RUFF" check --no-cache "$CORE" "$CLI" "$UT" "$CT"
runlog t3.scanner "$PY" .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA" \
  "$CORE" "$CLI"
runlog t3.diff git diff --check
runlog t3.index-diff git diff --cached --check
shasum -a 256 -c "$W/authority.sha256"
```

该七文件回归集合必须全量实跑，不能用 `-k`、deselect、skip/xfail 或删除失败用例变绿；纯合成新测试不应有实源 skip。scanner 的路径参数以当前源码定义的 positional `files` 接口传入；若工具行为与记录不符，保留真实 RC 并按 Rule 16 分流，不修改工具以求通过。

执行后保存 `after.status`、worktree/index patch、既有未跟踪文件摘要、四个新增文件摘要和日志。核对 HEAD/index 不变、执行前所有非本单变更原样保留，差集仅四个白名单 Python 文件；`git diff HEAD` 看不到未跟踪文件，不能只靠它验范围。白名单新文件的空白格式由 scoped Ruff 的 W 类规则覆盖，不把空的 tracked diff 当作其格式已验证。

**Task 3 终点：** 交付 source_manifest 实际路径/SHA、实现摘要、合成/回归/静态门禁、复用调用证据、输入准备缺口、累计预算与余额；交独立只读代码/合成验收。未取得 Task 4 新批准前在此停止，不计算真实收益，不宣布整个 Plan complete。

## 6. Task 4：另获批准后，一次限定真实读取与结果交付

**Dependencies：** Tasks 1–3 门禁及独立验收通过、身份资料可支持继续、预算有余额；用户批准 source_manifest 实际路径/SHA、源代码身份、精确 TARGET_RUN 及本 Task 的联网/读取/分析范围。对应全部 `INV-*`。**Files：** 仓内只读，写入仅白名单目标 RUN 与 W 日志。

### 6.1 前检、取数与 coverage 门禁

重新核对用户批准而非新算自填的 manifest SHA、Design/Plan/代码绑定、HEAD/工作区快照、全新目标目录和预算。若 Tasks 1–3 代码有返修，原来源清单/批准绑定不得继续使用，先重验并取得适用新批准。

```bash
# 本段仅在另获 Task 4 批准后运行；两个 SHA 必须来自实际批准记录。
: "${APPROVED_MANIFEST_SHA:?missing_task4_approved_manifest_sha}"
printf '%s  %s\n' "$APPROVED_MANIFEST_SHA" "$MANIFEST" > "$W/task4.manifest.sha256"
shasum -a 256 -c "$W/task4.manifest.sha256"
shasum -a 256 -c "$W/authority.sha256"
test ! -e "$TARGET_RUN"
runlog t4.fetch "$PY" -B "$CLI" fetch --manifest "$MANIFEST" \
  --manifest-sha256 "$APPROVED_MANIFEST_SHA"
```

fetch 先按清单核对五币普通现货身份及目标期间证据，再按固定对象表保存原始字节、请求时间/URL/状态、失败及累计请求/ZIP 字节；完成完整性和 coverage 核验才允许分析。产品身份、归档存在、历史资格、实时可用性不能混为一个布尔结论；只有当前 exchangeInfo 或目录存在仍不能证明历史资格，不能凭无报错自动通过。

取得资料仍不能支撑 Design §3 的资格时，或任何包失败、内容冲突、覆盖不完整、资源触限时，fetch 非零并交付缺口，**不得继续 analyze**。这属于可接受的停止交付，不是一次有效 Alpha 负结果；不换币、时间、供应商或降到 0.98 覆盖要求。

### 6.2 一次离线分析与人工报告

仅当 fetch=0 且 coverage 内容合同实际满足时：

```bash
runlog t4.analyze "$PY" -B "$CLI" analyze --manifest "$MANIFEST" \
  --manifest-sha256 "$APPROVED_MANIFEST_SHA"
shasum -a 256 -c "$W/task4.manifest.sha256"
shasum -a 256 -c "$W/authority.sha256"
```

fetch 输出 `RUN/coverage.json`，原始包及必要身份资料保存到 RUN/raw。analyze 重新验证原件后只读消费，不发网络请求；在全新 `RUN/results/` 输出 `ledger.jsonl`（含每决策点资格/事件/对照关系）、`summary.json` 和最后的 `EXECUTION_FINISHED`。来源清单/日志保存精确对应关系；字段至少覆盖 Design §7.2。CLI/消费者在本轮核对结构、来源、时间和数学语义，不能靠 JSON 可解析或共享错误算法证明正确。

Model C 依据实际结果另写同 RUN 的 `report_CN.md`：两个候选完整分母、点估计与可估计性、全部成本情景、MAE/MFE/尾损、23 块贡献/名义区间和不确定性限制、固定切分/剔除/Top-K、准确观察与资源标签、未验证成本/容量/执行和已暴露区间说明。报告不得升级为独立样本外、全市场 Alpha、旧 R10 再准入或实盘资格。

保留命令及真实 RC、源码/输入/仓库前后不变性、所有结果摘要与预算结余。非正结果不改窗/删币/改对照重跑；需要重跑须说明原因、新目录及适用新授权。本 Task 到 `delivered_for_independent_audit` 为止，不由执行者宣告 complete。

## 7. 不变量到任务与验证命令映射

| Design 不变量 | 任务与验收命令/证据 |
| --- | --- |
| `INV-01` 权限与历史隔离 | T1 的 §2 身份/基线与显式安全检查；T3 `t3.regression`/范围差集；T4 前后批准及输入摘要核对，无账户/执行调用 |
| `INV-02` 固定币池与原件 | T3 `t3.cli` 的有限值/单位/缺包/摘要/全区间 oracle；T4 `t4.fetch` 的 135 组来源、资格和 coverage；失败不进入分析 |
| `INV-03` 因果时间 | T1 `t1.green` 的两候选 canonical 正向、RS 的 672 个历史 spread/同窗 BTC 对齐及 BTC 单点变异、12:00→12:01→12:15→16:15；T3 原始微秒适配；T4 账本时间独立复算 |
| `INV-04` 固定候选 | T1 `t1.green` 调用真实检测的手算边界和两候选公共入口正向；T2 `t2.green` 两套 canonical bars 至最终统计；T3 指定旧 config/candidates 回归与来源绑定 |
| `INV-05` 分母与相关性 | T1 占用/边界；T2 `t2.green` 的决策状态守恒、零样本/空块、共同块 bootstrap；T4 原始账本与 summary 对账 |
| `INV-06` 简单对照 | T2 `t2.green` 两候选完整正向（含 RS 精确 C_i、d_i=200 和子集 delta）、单条件变异、复用权重、无匹配/回退；T4 抽查 C_i 全部条件与重复权重 |
| `INV-07` 均值/成本/路径 | T1 gross/MFE/MAE oracle；T2 均值/分位数/Top-K/块归约/扣成本 oracle；T4 独立复算与结果摘要 |
| `INV-08` 限定声明 | T2 §8 四组及零值/null/部分匹配分流测试；T3 `t3.cli` 输出结构；T4 report/summary 对照 Design 的声明边界 |
| `INV-09` 最小化与预算 | T1 导入与预算；§2 及 T1/T2/T3 的本次 RED RC/新证据/目标失败原因核对，碰撞与写入失败必须停止；T3 实际调用及 scoped Ruff/scanner、四文件差集；T4 资源记录，无新框架/Verifier |

## 8. Rule 15–17、独立审计与完成定义

**Fixture 分级：** 数值归约、分流、适配/故障注入可用最小合成向量；跨模块正向须由真实 canonical `HistoricalBar`/检测函数/收益函数形成接线，不手写上游“已通过”记录；官方覆盖只能由获准读取的实际 ZIP/CHECKSUM 与内容合同证明。mock 请求和合成 SHA 永不当作官方来源证据。

**Rule 16：** 在白名单内偏离已批准行为的缺陷可局部 TDD 修复；新增实现路径需先停并申请有限 Plan 增补；需要改变候选、币池、时间、成本、匹配、结果标签或历史冻结契约则 STOP=`BLOCKED_SPEC_DRIFT`。失败旧测试不得自行改断言、deselect 或当作“基线例外”处理。未触发的崩溃/封树/跨进程矩阵不强加。

**Rule 17：** 产物为单次可重算探索输出，实际消费者为本轮 analyze 与人工审计，没有任何运行/资金准入权。不创建独立 Schema Verifier，不运行旧 J-A/J-B/J-C profile 校验，也不建立不可逆迁移或多阶段 fsync 协议。结构校验及独立数学/时间/样本语义证据仍必须完成。

**独立审计（只读）：** 核对用户阶段批准与 Design/Plan/来源清单实际 SHA，直接读取 committed/cached/unstaged/untracked 变更并对照执行前基线；核验实际调用而非仅导入名或 C 自评。重跑指定合成回归与静态门禁到审计外置目录；不因审计自动重新读取/运行实源。现有结果至少独立复算一组正/负收益、控制均值/增量、分位数/Top-K、分母和一个分块复制例，并核对原件摘要、请求与预算记录。

全部要求满足才可对本限定 Plan 给出 `complete`。因资格/覆盖失败已按合同停止时，可明确报告相应准备任务完成和整体研究未进入/`blocked`，不能把未运行的真实实验记通过。若只完成 Tasks 1–3，整体必然仍待 Task 4 及最终审计。

`complete` 仅代表本 Plan 当前获批范围的工程/证据交付满足，不授予 commit、push、merge、SSH、deployment、生产 runtime、Producer、paper、live 或执行权限。所有交易/执行权限继续 False；本 Plan 不修改规则、roadmap 或历史研究状态。
