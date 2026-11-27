# Stage 1.3 跨币放量广度与特殊周贡献归因探索 Implementation Plan

## Allowed Change Scope

以下范围仅在本 Plan 独立审核通过、用户批准对应阶段后生效；当前只起草本文件。

| 类别 | 精确范围 |
| --- | --- |
| Allowed implementation paths | 新增 `scripts/external_signal_shadow/run_stage1_3_cross_asset_volume_breadth_attribution.py` |
| Allowed verification paths | 新增 `tests/scripts/external_signal_shadow/test_run_stage1_3_cross_asset_volume_breadth_attribution.py` |
| Allowed documentation paths | 实施期间 `none`；本次编制仅新增本 Plan，不回写 Design、roadmap、旧 Plan 或旧报告 |
| Allowed generated/runtime artifacts | Tasks 1–3 仅新建 `/private/tmp/stage13-volume-breadth-implementation-<RUN_ID>/` 的合成输入、日志、基线及新 `source_binding.json`；Task 4 另获授权后仅新建 `/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution/<RUN_ID>/` 的三个结果文件 |
| Affected but unchanged | 原量价共振 CLI/测试、`src/research/external_signal_shadow/stage1_3_fixed_universe_diagnostic.py`、其领域测试、`stage1_3_models.HistoricalBar`、`configs/base.py`、`src/risk/limits.py`、批准 Design/历史契约、五输入及既有工作区；以调用方回归、摘要和前后范围快照证明兼容，不修改公共接口 |
| Forbidden | 白名单外编辑、解析原始 ZIP/其他研究根、递归跟随输入引用、联网或账户接口、真实 detector/行情重建、扩币/窗口/门槛/退出规则/模型、修改原对照或结论、配置/依赖/profile/独立 Verifier/隔离 worktree/双进程/数据库、全库格式化或 `ruff --fix`、清理原件、自动 add/commit/push、SSH/deploy、生产 D/F 启停、Producer/paper/live |

**批准依据：** 用户批准 [Design](../designs/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution-design_CN.md)，SHA-256 `327641761e2b6c625e873c1c2592418a2b43c640935eed78507b9e36617e30fa`。这是新单，不沿用旧运行批准。**Goal：** 一次只读归因与四级描述，允许可构造性失败，不开发交易策略。**Architecture / Tech Stack：** 主仓 Python 3.11.14、标准库顺序执行，一个新 CLI 和其测试，直接消费固定派生产物。

## 1. 事实、复用与资源门禁

起草时 `HEAD=9712c5580682062416497191250453b267b97040`，有 12 个既存未跟踪文件；正式执行必须重新记录实际基线，不能把空 HEAD diff 当作无变化。`.venv/bin/python` 实测为 3.11.14；本 Plan 不切换历史快照或解释器。只核对既有源码、文档和元数据，不在编制阶段构造真实 G。

| 主要能力 | 在现有 Task 中的实际调用/适配边界 |
| --- | --- |
| 核心模块 `build_default_protocol` / `validate_protocol` / `verify_base_and_safety_config` | Tasks 1–3 取得并核对原 15m/1h/60s/4h 规格、安全配置；L 从原四根 bar 推导，不加新配置阈值 |
| 同模块 `linear_quantile` | Task 2 实际用于分布/MAE/MFE/成本分位；独立手算核对，不复制分位算法 |
| 原量价共振 CLI `_reject_symlink_chain(path, *, stop_code, label)` / `_stream_sha256(path, *, stop_code=...)` | Task 3 直接调用小型祖先链接检查和流式摘要；精确五输入路径、发布前快照由本 CLI 局部适配。旧 helper 在 macOS 只允许系统 `/tmp` 等根别名；五个实际输入仍必须是 Design 的精确路径，不借别名换根 |
| `HistoricalBar` → `build_event_ledger`，原测试的 canonical bar 生成器 | Tasks 1/3 测试内构造真实上游决策并 JSONL 序列化。可导入旧测试的 `_make_168d_canonical_bars` / `_make_plan_section4_dual_rs_with_volume_bars`，不复制生成后的账本/通过标志 |
| 原 CLI `build_cohort` / `summarize_cohort` | 仅在合成测试内作为原成员 artifact 的 canonical 生产路径；真实新运行不调用它们重建原队列/旧 Delta，更不把旧两组统计冒充四级广度 |
| 原 CLI 的 prepare/run/完整身份框架、上游 analyze/detector | 不复用：绑定的固定根、旧 Design/Plan 与统计目标不同。只做本单必要身份与联结，不复制下载、隔离、完整权威元组或通用框架；需要超范围时按 Rule 16 停止 |

新增全流程上限按 Design 为 **1.00 人时，须在实施批准时确认**，包含本 Design/审阅、本 Plan/审阅、实施/返修、测试、一次真实运行及独立审计，不借上单 2h 余额。每阶段先列实测累计、非零未知/估算区间、剩余最低工作及保守余额；不能因预算未知就记零或自动续费。余额不足就交付 `resource_stop`，不删门禁凑预算。没有正向结果也可完成约定核查。

## 2. 五输入、固定语义与分段授权

记 `R=/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-25-stage1-3-volume-strength-conditional-increment/20261125T124130Z`，`U=/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-24-stage1-3-fixed-universe/20261125T062144Z`。

| 固定真实输入 | SHA-256 |
| --- | --- |
| `R/members.jsonl` | `660bd1fe1d6a7ea608c6cb4accba497e7a66dc58d83a60ae5fac86900b2a2956` |
| `R/summary.json` | `09400e8a7203338291741b0ad20c4c5c16ebeb2605c9cdb0dc16aa65bc38e300` |
| `U/results/ledger.jsonl` | `c26e4da31c2836e4c2119aed8ad2120417e5b5339c75d41bc36bc4ee95df1638` |
| `U/results/summary.json` | `624d26de18a22ed9a4474e78cd1e844bf148b29e33a7c4d47050aa80015edec2` |
| `/private/tmp/stage13-volume-strength-implementation-20261125T124130Z/remediation_r1/source_binding.json` | `201472847ddb45a4575a98f39132830a672d69f7a101f4d032f92b1ad0cd0007` |

Tasks 1–3 的实施批准只允许新代码、合成测试及新绑定准备；真实五输入只可流式核对字节摘要，不解析 JSON/JSONL，不计算真实 G 或收益分组。Task 4 必须在代码独立验收后，再获用户对实际新 binding 路径/SHA、代码与全新 OUT 的单独批准。旧 binding 是一个只读输入，新 binding 是本单来源记录；二者都不是自动授权。

固定 Q=964、J=155、B-only=809；block 9 原 Q=62，其中共振40/仅走强22。唯一新指标为其他三币在 `t-L<u<=t` 内曾触发 A 的数量，L=3600000；右端包含，左端排除，每币四个原 A 决策点，不计目标币/BTC。四级不合并，不选最佳级。原 23 周、Y/MAE/MFE、成本情景、原对照和停止边界全部沿用 Design，不由 Plan/执行者另选。

## 3. 共用执行约定（仅获批实施后）

使用 Bash；先完成预算核对再建立 W，OUT 此时必须不存在。环境/源码身份不符时停止，不降级运行。以下为执行时记录变量，不代表当前获准执行。

`runlog()` 逐字复用[11-24 已审核 Plan](2026-11-24-stage1-3-fixed-universe-mean-return-diagnostic-implementation-plan_CN.md)中的会话函数，来源 SHA-256 为 `bf066b19f0bd43c2378bf6c34553dd10f7c9747ea070815627818c05db8e1e3a`；只复用此函数，不执行旧 Plan，不另建 Shell 框架。

```bash
set -euo pipefail
REPO=/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
cd "$REPO"
PY="$REPO/.venv/bin/python"
CLI=scripts/external_signal_shadow/run_stage1_3_cross_asset_volume_breadth_attribution.py
TEST=tests/scripts/external_signal_shadow/test_run_stage1_3_cross_asset_volume_breadth_attribution.py
OLDCLI=scripts/external_signal_shadow/run_stage1_3_volume_strength_conditional_increment.py
OLDTEST=tests/scripts/external_signal_shadow/test_run_stage1_3_volume_strength_conditional_increment.py
CORE=src/research/external_signal_shadow/stage1_3_fixed_universe_diagnostic.py
CORETEST=tests/research/external_signal_shadow/test_stage1_3_fixed_universe_diagnostic.py
DESIGN=docs/designs/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution-design_CN.md
PLAN=docs/plans/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution-implementation-plan_CN.md
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
W="/private/tmp/stage13-volume-breadth-implementation-$RUN_ID"
OUT="/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution/$RUN_ID"
test ! -e "$W"; test ! -L "$W"; mkdir "$W"
test ! -e "$OUT"; test ! -L "$OUT"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src:$REPO"
BASE_SHA=$(git -c core.fsmonitor=false rev-parse HEAD)
printf '%s\n' "$BASE_SHA" > "$W/BASE_SHA"
git -c core.fsmonitor=false status --short --untracked-files=all > "$W/before.status"
git -c core.fsmonitor=false diff > "$W/before.worktree.patch"
git -c core.fsmonitor=false diff --cached > "$W/before.index.patch"
git -c core.fsmonitor=false ls-files --others --exclude-standard > "$W/before.untracked"
while IFS= read -r p; do shasum -a 256 "$p"; done < "$W/before.untracked" > "$W/before.untracked.sha256"
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
verify_scope() {
  local tag="$1"
  git -c core.fsmonitor=false status --short --untracked-files=all > "$W/$tag.status" &&
  git -c core.fsmonitor=false diff > "$W/$tag.worktree.patch" &&
  git -c core.fsmonitor=false diff --cached > "$W/$tag.index.patch" &&
  git -c core.fsmonitor=false ls-files --others --exclude-standard > "$W/$tag.untracked" &&
  test "$(git -c core.fsmonitor=false rev-parse HEAD)" = "$BASE_SHA" &&
  cmp "$W/before.worktree.patch" "$W/$tag.worktree.patch" &&
  cmp "$W/before.index.patch" "$W/$tag.index.patch" &&
  shasum -a 256 -c "$W/before.untracked.sha256" &&
  LC_ALL=C sort "$W/before.untracked" > "$W/$tag.before.sorted" &&
  LC_ALL=C sort "$W/$tag.untracked" > "$W/$tag.after.sorted" &&
  LC_ALL=C comm -13 "$W/$tag.before.sorted" "$W/$tag.after.sorted" > "$W/$tag.added" &&
  LC_ALL=C comm -23 "$W/$tag.before.sorted" "$W/$tag.after.sorted" > "$W/$tag.removed" &&
  printf '%s\n' "$CLI" "$TEST" | LC_ALL=C sort > "$W/$tag.allowed" &&
  test ! -s "$W/$tag.removed" &&
  cmp "$W/$tag.allowed" "$W/$tag.added"
}
printf '%s  %s\n' 327641761e2b6c625e873c1c2592418a2b43c640935eed78507b9e36617e30fa "$DESIGN" > "$W/design.sha256"
runlog design shasum -a 256 -c "$W/design.sha256" || exit $?
runlog python "$PY" -B --version || exit $?
```

保存用户实际批准原文；获批 Plan SHA 从批准原文取得，核对磁盘值，不用现场算出的新值替代授权值。另记录 OLDCLI/CORE/config/risk 和全部既有未跟踪文件摘要。新文件原先存在则停止调查，不覆盖。生产校验使用显式异常/非零退出，不用可被 Python 优化模式禁用的 assert；测试中正常使用 pytest 断言。

日志碰撞、命令证据写入、日志打开/关闭或 RC 文件写入失败统一返回74，不能冒充 pytest 的合法RED=1；子命令退出码原样保留。不得依赖函数处于 `if`/`||` 条件下的 `set -e` 自动处理内部错误。重复验证必须同时使用全新日志名、basetemp及范围快照标签，不覆盖已有日志或借用旧RC。

RED 只接受目标测试已成功收集、实际执行且因预期未实现行为失败。缺解释器、缺模块、导入失败、collection error、无关异常或意外全绿均STOP。先写测试；必要时增加仅抛 `NotImplementedError` 的最小接口骨架以完成收集，不先实现算法。执行前在现有日志记明目标nodeid、独立expected和预期失败机制；执行后必须核对本次完整失败节点/traceback均对应预期并留痕，不能只凭RC=1或grep错误词放行GREEN。下列三个RED代码块先比较本次函数实际返回RC，再读取本次新生成的RC文件，两者一致也不替代上述语义核对。

作者侧关闭核查仅在仓外用一次性合成命令/最小pytest向量验证：真实目标失败=1可进入证据核对；日志打开或RC写入失败、旧日志碰撞、collection error、意外全绿和GREEN证据写入失败均停止；子命令是否实际执行及旧证据未变需独立确认。不新增仓内Shell文件、研究代码或独立Verifier。

## 4. Task 1：原 A 决策 → 三值 H 与因果广度标注

**Dependencies：** §3 的身份、基线、预算和本地实施批准。**Files：** CLI/TEST。**不变量：** `INV-02`、`INV-03`，兼顾 `INV-01`、`INV-05`。

**接口：** `annotate_breadth(target_keys: list[tuple[str,str,int]], a_rows: list[dict], *, protocol: dict) -> dict`。返回全部目标的 `annotations`、已知/未知计数与逐点缺口；输入的 target_keys 只含 B 唯一键，特征函数不得接收目标 Y。每行输出原键、G/null、其他三币 H、四个预期键/实际状态/触发值/时间及缺口或触发证据。

- [ ] 在 TEST 写 `test_breadth_three_valued_oracle`。目标 ETH 的 t=UTC 2026-06-15 12:01，预期 u 恰为 11:16/11:31/11:46/12:01。纯逻辑向量独立预期如下，不调用被测函数生成 expected。

| 原 A 输入 | 独立预期 |
| --- | --- |
| SOL 在 11:31 admitted=4、11:46 overlap_suppressed=4；XRP 四点未触发；DOGE 有一个缺点但 12:01 admitted=3 | H 为 SOL=1/XRP=0/DOGE=1，G=2；SOL 重复触发只计一币 |
| 将上例 DOGE 12:01 改为 not_triggered/null，其余不变 | DOGE=null、G=null，目标不能消失 |
| 其他三币四点均 not_triggered/null | G=0；全三币各有一个合法触发则 G=3 |
| 只在左端 11:01 或未来 12:16 触发，或只修改 ETH/BTC | 不增加 G；右端 12:01 合法触发必须计入 |
| 已有触发，但同窗口另一点 not_triggered 携带数值、非法状态、NaN、重复键或时间不符 | `STOP=input_invalid`，不得提前返回 H=1 掩盖矛盾 |

- [ ] 写 `test_breadth_causality_and_unknowns`：缺失、feature_not_estimable、block_boundary_censored 不能作为零；合法未知与无效记录分开。修改 t 之后的合法放量事实、任意结果列或周身份不得改变该 t 的 G；输入投影明确只保留 A 所需时间/状态/触发值。先检查四点矛盾再执行存在性判定。
- [ ] 写 `test_breadth_canonical_positive`：复用原 canonical 双 RS 向量，`HistoricalBar`→`build_event_ledger`→JSONL→原 `build_cohort/summarize_cohort` 生成 members；不用 mock 本次 annotate。独立预期 Q 为 ETH 的 12:01/16:16 两键，J 仅 12:01，Y=200 bps；其他三币均无量脉冲时 G=0。再用 `dataclasses.replace` 将 SOL 的 2026-06-15 11:30 bar `quote_volume` 从25改为325，价格保持100；该一小时量为400、历史基准100，产生4倍放量，J 不变而 G=1，SOL admitted 与后续 suppressed 均有真实来源。
- [ ] 写 `test_breadth_canonical_block_censoring`：使用原 168d canonical bar 生成器，ETH 2026-06-20 23:45 close=101 作历史变化，06-21 23:45 close=101.5、06-21 23:30 quote_volume=325；OHLC 保持包络有效，其他三币价格/量维持原基线。在 06-22 00:01 的 ETH 共振，其他币过去四点含真实周尾删失、当时点未触发，预期 H/G 未知。通过上游构造器取得状态，不将真实删失强改为零；fixture 的其他事件保留，J 键应只有该共振。

```bash
red_rc=0
if runlog t1.red "$PY" -B -m pytest "$TEST" -k 'test_breadth_' --basetemp "$W/t1-red" -p no:cacheprovider -ra; then red_rc=0; else red_rc=$?; fi
if test "$red_rc" -ne 1; then printf 'STOP=invalid_current_red_rc_%s\n' "$red_rc"; exit 1; fi
if ! recorded_rc=$(cat "$W/t1.red.rc"); then printf 'STOP=red_rc_unreadable\n'; exit 74; fi
if test "$recorded_rc" != "$red_rc"; then printf 'STOP=red_rc_mismatch\n'; exit 74; fi
# 按§3核对并留存本次全部目标失败证据后再实现最小算法；缺模块/导入失败不是RED。
runlog t1.green "$PY" -B -m pytest "$TEST" -k 'test_breadth_' --basetemp "$W/t1-green" -p no:cacheprovider -ra || exit $?
```

**验收：** GREEN RC=0，canonical 非零广度及真实删失各自通过；测试没有读取五份真实输入。未知结果仍保留目标键/来源，不因为不能估计就重建行情。

## 5. Task 2：锁定标注 → 时间线、四级描述与合法缺口

**Dependencies：** Task 1 GREEN。**Files：** CLI/TEST。**不变量：** `INV-02`、`INV-04`、`INV-05`。

**接口：** `describe_attribution(members: list[dict], breadth: dict, *, protocol: dict) -> dict`。先验证标注键恰为原 J，后在全部 G 已知时联结 Y/MAE/MFE。机器结果含 `counts`、`coverage`、`focus_week`、`full_sample`、`without_block_9`、`per_symbol`、`per_block`、`governance`、`routing`；空单元仍存在。

- [ ] 写 `test_attribution_hand_oracle`：纯内部数学向量 G0=[100,0]、G1=[-20]、G2=[]、G3=[300] bps，分别分配到原 block0/block1/空/block9。预期四组数量2/1/0/1，G0 sum=100、mean=50、win_rate=0.5、P05=5/P10=10/P25=25/P50=50/P75=75/P90=90、平均赢100/平均亏null/盈亏比null、最差0；G1 胜率0，G2 所有不可定义统计null。G0 的30/50/80成本均值为20/0/-30，P10=-20/-40/-70、最差=-30/-50/-80。移除block9仅使G3变空，其他成员的 G 不变；四币×四级、23块×四级保留零单元且各自回加4。
- [ ] 同向量为 G0 的两事件分别设 MAE=-50/-100、MFE=200/100，独立预期 MAE mean=-75/P10=-95/P50=-75/min=-100，MFE mean=150/P50=150/P90=190/max=200；原 Y=0 留在胜率分母，无亏损或无盈利时盈亏比null。分位实际调用 CORE.linear_quantile，不能缓存 expected 自证。
- [ ] 写 `test_attribution_unknown_blocks_all_group_statistics`：将一个目标 G 置未知，保留全部目标行、缺口和特殊周原事件时间线；`full_sample/without_block_9/per_symbol/per_block` 收益表均为null，输出 `breadth_not_estimable / stop_due_to_evidence`。不得只分析已知行，不得调用四级收益汇总。所有 G 已知才输出 `descriptive_attribution_only / pause_for_new_evidence`。
- [ ] 写 `test_attribution_focus_week_passthrough`：真实运行仅使用原 block9 的62个 Q 成员，保留40/22分组和原 conditional_control_keys/conditional_d_bps；按 `(available_at_ms,symbol)` 排序，UTC 日/币汇总原共振 count/sum/mean，单列 DOGE 原两个对照。内部最小向量可测试原值透传和排序；不得重新求匹配、移动对照或生成新的 Delta。report 明确原对照稀疏及周内阶段混杂，既有可比性限制保留。
- [ ] 所有路径保留 `alpha_research_status=evidence_insufficient`、`minimum_economically_meaningful_gain=null`、原成本情景和全部执行权限False。无模型、bootstrap、p值、最优G级/合并门槛、收益排序筛选或净交易/因果声明。

```bash
red_rc=0
if runlog t2.red "$PY" -B -m pytest "$TEST" -k 'test_attribution_' --basetemp "$W/t2-red" -p no:cacheprovider -ra; then red_rc=0; else red_rc=$?; fi
if test "$red_rc" -ne 1; then printf 'STOP=invalid_current_red_rc_%s\n' "$red_rc"; exit 1; fi
if ! recorded_rc=$(cat "$W/t2.red.rc"); then printf 'STOP=red_rc_unreadable\n'; exit 74; fi
if test "$recorded_rc" != "$red_rc"; then printf 'STOP=red_rc_mismatch\n'; exit 74; fi
# 确认目标 RED 后实现固定描述，不增添研究判据。
runlog t2.green "$PY" -B -m pytest "$TEST" -k 'test_attribution_' --basetemp "$W/t2-green" -p no:cacheprovider -ra || exit $?
```

## 6. Task 3：五输入 CLI → canonical 端到端、静态门禁与新绑定

**Dependencies：** Tasks 1–2 GREEN。**Files：** CLI/TEST、W。**不变量：** 全部 `INV-01`–`INV-05`；此阶段不解析真实输入。

**CLI：** `main(argv: list[str] | None=None) -> int`，仅 `prepare --approved-plan-sha --binding-output --output-root` 与 `run --binding --binding-sha`。无输入替换、窗口/门槛/成本/币池选项，无 count bypass。真实计数由固定契约校验，不靠用户传数字。

- [ ] prepare 调用原安全/协议/链接/摘要 helper，只做五文件的流式字节核对；不 JSON-load 真实 summary/binding，不解析 ledger/members。新 binding 保存批准 Design/Plan 路径及 SHA、HEAD、Python 身份、五输入精确路径/SHA、新 CLI/TEST、OLDCLI/CORE/config/risk 六份代码摘要和 OUT；记录 `provenance_record_only_not_execution_authorization`。绑定文件必须新建，旧 binding 不覆盖。
- [ ] run 开始及写出前共用同一局部身份检查：精确五输入路径、所有相关祖先无非法符号链接、resolve 后仍为预期对象、普通文件、摘要及 `(st_dev,st_ino)` 不变；新 binding 自身同样检查。核验实际 helper 的模块路径及代码摘要、Design/Plan/HEAD/安全配置；拒绝同字节换根、`..`、目录移动后链接回原路径、运行中替换/修改。只读五输入，不沿旧 binding/summary 内的路径继续打开任何文件。外层统一 `STOP=input_invalid`，保留可断言的 cause：`path_mismatch/hash_mismatch/reference_mismatch/protocol_mismatch/cohort_mismatch/time_or_price_mismatch/nonfinite_value/duplicate_key/input_changed_during_run/output_not_new/code_or_authority_mismatch`；负向测试须命中对应具体 cause，不能由更早的无关错误代替。
- [ ] 严格 JSON/JSONL 拒绝非有限常量。协议一致；R summary 引用的 source_binding SHA 对应第五输入，其 fixed_inputs 与旧 binding 一致；U summary 的 manifest 引用与旧 binding 中记录的 manifest SHA 一致，但不读取 manifest。核对完整账本 B admitted 键集合与 members 完全相同、无重复，Q/J/两组/焦点周计数正确；各成员与原 B/A 行的时间、状态、触发值、参考价格、Y/MAE/MFE一致，Y公式/原延迟/4h/块边界正确。继承的是上轮已审计对照，不重复拟合或重算全套旧统计。
- [ ] 先提取 J 键与所需 A 字段并固定 breadth，再把原成员交 describe；原其他币后续收益和对照值不进入特征函数。合法缺口 RC=0 可交付，必须标缺口且全部新收益分组为null；输入无效 RC=2，打印 `STOP=input_invalid` 和具体 cause，不写有效完成结果。预算/范围停止在 W 记录 `resource_stop`，不发起真实 run。
- [ ] OUT 仅允许固定新证据父目录下一个全新直接子目录，前后检查不存在、非链接；先在内存完成校验/序列化且拒绝 NaN，再新建 OUT。结果仅 `breadth_members.jsonl`、`summary.json`、`report_CN.md`，不加封树或权限收据。摘要最后写，明确 `execution_completed_pending_independent_audit`；只有三个文件齐全、结构有效且实际RC=0才是有效执行交付，部分写出/异常不是完成证明，不能覆盖失败目录续跑。
- [ ] `test_cli_canonical_prepare_and_run`：使用 Task1 的 G=1 canonical 全链（bar→原ledger→原members→新CLI→三个文件），独立断言目标键、12个来源槽位、SOL真实触发证据、G=1、Y均值200及成本均值170/150/120，其余三级为空且null、表分母守恒。测试内用 pytest monkeypatch 将固定路径/摘要和期望计数替换为该 canonical 小样本的 Q=2/J=1/焦点周=0，不添加生产 CLI 放宽参数，不将合成输入伪称真实资格。原 cohort/summarize 只用于测试内生产原 artifact；不 mock 新 annotate/describe/main。
- [ ] `test_cli_canonical_gap_delivery`：使用 Task1 周一删失 canonical 向量，原producer如实生成其Q/J；独立断言 J 唯一键为06-22 00:01、G未知、成员不消失、三个结果文件如实交付且新收益表全null。可估计性缺口不是测试 skip，不为使测试通过篡改上游删失状态。
- [ ] `test_cli_identity_scope_and_mutation`：在 canonical 合成副本上，分别注入来源摘要/引用/协议不符、成员重复/漏项、时间/价格矛盾、NaN、输入路径跨根/祖先链接、绑定替换、发布前输入内容或 inode 改变；每例断言具体 `STOP=input_invalid` 与对应 cause、RC=2、无有效完成状态。覆盖相同字节的目录迁移后链接反例，不能仅断言“非零”。对 socket 连接设失败钩子，证明合成链零联网。所有故障仅在 W 的合成副本，不修改真实五输入。

```bash
red_rc=0
if runlog t3.red "$PY" -B -m pytest "$TEST" -k 'test_cli_' --basetemp "$W/t3-red" -p no:cacheprovider -ra; then red_rc=0; else red_rc=$?; fi
if test "$red_rc" -ne 1; then printf 'STOP=invalid_current_red_rc_%s\n' "$red_rc"; exit 1; fi
if ! recorded_rc=$(cat "$W/t3.red.rc"); then printf 'STOP=red_rc_unreadable\n'; exit 74; fi
if test "$recorded_rc" != "$red_rc"; then printf 'STOP=red_rc_mismatch\n'; exit 74; fi
# 核对目标 RED 后实现最小 CLI；以下任一非零均停止。
runlog t3.regression "$PY" -B -m pytest "$TEST" "$OLDTEST" "$CORETEST" --basetemp "$W/regression" -p no:cacheprovider -ra || exit $?
runlog t3.ruff "$REPO/.venv/bin/ruff" check --no-cache "$CLI" "$TEST" || exit $?
runlog t3.scanner "$PY" -B .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA" "$CLI" || exit $?
runlog t3.diff git -c core.fsmonitor=false diff --check || exit $?
runlog t3.cached git -c core.fsmonitor=false diff --cached --check || exit $?
runlog t3.prior-files shasum -a 256 -c "$W/before.untracked.sha256" || exit $?
runlog t3.scope verify_scope after || exit $?
: "${APPROVED_PLAN_SHA:?actual_user_plan_sha_required}"
runlog t3.prepare "$PY" -B "$CLI" prepare --approved-plan-sha "$APPROVED_PLAN_SHA" --binding-output "$W/source_binding.json" --output-root "$OUT" || exit $?
shasum -a 256 "$W/source_binding.json" > "$W/source_binding.sha256"
test ! -e "$OUT"; test ! -L "$OUT"
```

**交付验收：** 三文件完整回归RC=0、无skip/xfail；Ruff/scanner/diff及新绑定准备通过，不预写测试数量。另保存 after.status/worktree.patch/index.patch/untracked、全部源文件摘要，核对 HEAD未变、原暂存/未暂存patch逐字节相同、原既存文件摘要一致，新增文件恰为CLI/TEST，无越界改动。实际私有 helper 调用与分位调用有源码位置及测试覆盖。交付 RED/GREEN 命令/真实RC、binding路径/SHA、累计预算/余额；停在 Tasks1–3 独立验收，不自行运行 Task4 或宣布全单 complete。

## 7. Task 4：单独授权的一次真实读取与独立审计

**Dependencies：** Tasks1–3 独立验收通过，原1h累计预算仍可覆盖最低运行/审计，用户实际批准新 binding 路径/SHA及代码/OUT。**Files：** 仓内none，只有获批新 OUT 和 W 新日志。**不变量：** 全部。

```bash
: "${APPROVED_BINDING_PATH:?actual_user_binding_path_required}"
: "${APPROVED_BINDING_SHA:?actual_user_binding_sha_required}"
printf '%s  %s\n' "$APPROVED_BINDING_SHA" "$APPROVED_BINDING_PATH" > "$W/task4.binding.sha256"
runlog t4.binding shasum -a 256 -c "$W/task4.binding.sha256" || exit $?
runlog t4.before-scope verify_scope t4-before || exit $?
test ! -e "$OUT"; test ! -L "$OUT"
runlog t4.run "$PY" -B "$CLI" run --binding "$APPROVED_BINDING_PATH" --binding-sha "$APPROVED_BINDING_SHA" || exit $?
runlog t4.after-scope verify_scope t4-after || exit $?
```

保存实际批准原文、起止UTC、完整命令/RC和前后 HEAD/status/worktree/index/原未跟踪文件/代码及五输入摘要。只有一次run；未知、负面或异常均不自动换目录重跑。源码变更使旧 binding 失效时保留旧记录，重新验收并另获授权，不能自刷摘要继续。

独立 Completion Audit 仅在同五输入及新结果内只读核验，不重跑 CLI/上游：确认 Q/J和完整目标键、全部G/来源/未知分母；独立手算左右端点/重复触发/未知存在性，核对焦点周62行原值透传，以及全部分组/币周分子分母、固定剔除和成本。不得调用被审 annotate/describe 自证，不强加独立 Rule17 Verifier。全部可构造时做完整描述核算；存在未知时核验155行仍保留及新收益表全null，不把“未算收益”当作遗漏。先验声明和权限限制必须在机器/人工报告一致。

本单供人工消费的机器产物采用结构与独立语义证据验证，不授予其他阶段自动准入。合法缺口的如实交付可满足本次工程范围，但研究状态仍是 evidence_insufficient；输入错误/未满足必要交付则 incomplete 或 blocked。执行者不自审宣布 complete。

## 8. 不变量映射与路由

| 不变量 | Task及具体验证 |
| --- | --- |
| `INV-01` | §3基线，Task3身份/路径/变更反例、prepare和前后摘要，Task4同五输入复核；对应 t3.regression/ruff/scanner/diff/prior-files/prepare 与 t4.binding/run |
| `INV-02` | Task1 canonical目标、Task2表守恒、Task3完整键/原成员对账、Task4真实 Q=964/J=155与焦点62行核对；对应 test_breadth_canonical_positive、test_attribution_hand_oracle、test_cli_canonical_prepare_and_run |
| `INV-03` | Task1全部独立因果/三值向量及真实删失；Task3实际CLI接线；对应 t1.green、test_cli_canonical_gap_delivery及独立逐点核算 |
| `INV-04` | Task2独立分布/成本/空组/固定剔除，Task3未知禁止分组及三产物接线，Task4独立分母/算术核验；对应 t2.green/t3.regression |
| `INV-05` | 各阶段累计预算、真实调用/适配证据、分段批准、静态范围与最终原分流/权限核对；§3复用日志函数、Tasks1–3本次实际RED RC/新RC文件/目标失败traceback核对，日志碰撞或证据写入失败74即STOP，GREEN同样受约束；任何研究语义变动不得由执行者决定 |

白名单内实现/测试缺口按 `BLOCKED_IMPLEMENTATION_DEFECT` 局部RED/GREEN；必须增加文件但不改契约则 `BLOCKED_SCOPE_DRIFT`，先获有限Plan增补并核对 binding/代码/证据是否需重验；改变窗口、分母、三值、输入权限或研究声明则 `BLOCKED_SPEC_DRIFT`，停止并退回Design，不静默修补。原件不改，旧日志不覆盖。

本 Plan 当前只进入独立 B 审查。审核推荐不等于用户批准；用户批准本地实施仍不等于真实读取批准。`complete` 仅代表已批准范围交付，不自动授予 commit、push、deployment、SSH、生产 runtime、Producer、paper 或 live 权限。
