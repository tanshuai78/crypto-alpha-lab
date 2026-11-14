# Stage 1.5D / 1.5F Hotfix - Task 5 验收边界修订草案

日期：2026-11-14（Asia/Shanghai）。状态：`candidate / pending_B_review_and_user_approval`。

本文只提议调整原 Plan Task 5 的回归验收条款，不改写原批准文件，不修复代码，不自动解除当前 `blocked`。完整回归保留实际非零结果；只有经精确归因的既有问题可以不阻断本次 D/F 编码范围验收，不表示这些问题已修复或下游已兼容。

## Allowed Change Scope

| 类别 | 本次修订边界 |
| --- | --- |
| Allowed implementation paths | `none`；不得再修改 D/F 逻辑或其他生产代码 |
| Allowed verification paths | `none`；不得修改测试、fixture、pytest 配置、断言、skip/xfail 或冻结哈希 |
| Allowed documentation paths | 只新增/修订 `docs/plans/2026-11-14-stage1-5d-1-5f-hotfix-task5-acceptance-boundary-delta_CN.md` |
| Allowed generated/runtime artifacts | 获批后的本地验证只向新建 `/private/tmp/stage15-task5-revalidation.*` 及其中的 pytest 临时根写日志、选择清单和现有格式的合成产物；不新增仓内工具或机器消费产物类型 |
| Affected but unchanged | 原 Design、原 Plan、原 19 文件实施范围、1.5G 冻结契约/历史收据、真实 D/F 根及取证原件；核对身份和范围，不修改 |
| Forbidden | 删除测试、整文件/通配符豁免、改报 RC、自动扩大例外、放宽消费门禁、读取受限真实数据、联网/VPS/启停/提交/推送/部署/交易操作 |

范围分为两层：本文起草只允许新增这份候选文档；未来即使批准本文，也只允许执行下述本地验证与独立审计，不新增代码修改权限。原 Plan 的其他约束及原有独立授权要求继续有效。

## 1. 权威绑定与唯一修改点

| 权威 | 路径/身份 |
| --- | --- |
| 原 Plan | `docs/plans/2026-11-13-stage1-5d-1-5f-postponed-launch-readiness-and-reobservation-hotfix-implementation-plan_CN.md` |
| 原 Plan SHA-256 | `814479e367551d33819562b71d39f426a283d05e30f1d5a7313f2990421b063c` |
| 绑定 Design | `docs/designs/2026-11-13-stage1-5d-1-5f-postponed-launch-readiness-and-reobservation-hotfix-design_CN.md` |
| Design SHA-256 | `f8d5f404e55893f86208c724537077fdcabc391a4d90bebba8bafc94fe619874` |
| 执行前 BASE_SHA | `2f9ba8e04821c3d7a477a65f2b73e34cb6beb442` |
| 执行前基线 | `/private/tmp/stage15-postponement-baseline.H64sqE` |

**唯一拟覆盖条款：**原 Plan Task 5 中“预期所有命令 RC=0”对其完整 pytest 回归命令的适用方式。经 B 审查及用户批准本文精确 SHA 后，改为 §3 的完整诊断加精确例外验收。原静态、安全、范围、来源、权限门禁仍全部有效；Task 0-4、§7 真实来源前提及全部 Design `INV-01` 至 `INV-08` 不变。

这不是普通的新增路径 `BLOCKED_SCOPE_DRIFT`：它改变已批准的验收条件，须明确作为 Rule 16 下的 Plan 验收契约调整审查。本文判断父 Design 不要求修改 1.5G 或取得历史收据重新准入；B 若发现本文影响任何 Design 不变量，必须停止，转相应 Design/Plan 修订，不能只批准豁免。不得用本文追认未经授权的既往操作。

## 2. 问题、事实证据及其限度

### 2.1 待解决的单一阻塞

原八项 finding（`P1-01` 至 `P1-07`、`P2-01`）在上一轮独立审计中已关闭。本次不无依据重开。剩余问题是：原 Plan 要求整套回归 RC=0，但既有测试路径及历史冻结上游身份不匹配，在热修复边界外先行阻断验证。

| 类别 | 当前表现 | BASE 与真实源码证据 | 仍未证明的事项 |
| --- | --- | --- | --- |
| F 旧测试路径 | 3 FAILED，`ValueError: output_root_missing_external_signal_shadow_ancestor` | `test_stage1_5f_historical_anchor_rejection_hygiene.py` 使用 `tmp_path / "out"`；既有 `stage1_5_storage_guard.py:83` 要求 `data/external_signal_shadow` 祖先。两文件在 BASE 和当前均保留此事实 | 这三个场景的后续行为未被本次测试跑到，不能称历史拒绝卫生测试通过 |
| G cross-root | 6 FAILED + 29 ERROR；直接或子进程/fixture 包装后的首要原因是 `STOP=stage1_5g_cross_root_upstream_contract_drift` | `stage1_5g_cross_root_event_family_admission.py:28` 冻结配置文件哈希，`:199` 拒绝漂移；BASE 即不匹配 | 错误发生在真实输入准入前，不证明当前上游可被此历史消费者接纳，也不证明后续断言满足 |
| G N3 | 38 FAILED；直接或包装后的首要原因是 `STOP=stage1_5g_n3_regime_upstream_contract_drift` | `stage1_5g_n3_regime_stratified_admission.py:31` 冻结配置文件哈希，`:317` 拒绝漂移；BASE 即不匹配 | 不证明 N3 当前兼容性、质量判定或真实根准入通过 |

1.5G 冻结的 `configs/base.py` SHA 为 `414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4`；`git show BASE_SHA:configs/base.py` 的实际 SHA 为 `473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc`。不能为通过测试而改写任一身份。

**证据等级：**执行前基线目录没有保存完整回归实跑日志。“既有”归因来自 BASE 源码事实、未变更路径和返修后两轮失败签名一致，不得写成“在 BASE 上完整实跑过”。节点名/失败数量一致仅是辅助证据；每一例外仍须核对实际堆栈、失败阶段及根因。归因不足时保持阻塞，必要的补充复现只能使用隔离临时目录及未改写的 BASE 源码，不得加载受限历史根。

### 2.2 本地参考证据

以下为已存在的上轮审计记录，本文起草未重跑测试。共同根为 `/private/tmp/stage15-closure3-audit.hJ5PDN`；审批前若临时文件丢失或身份不符，须补齐可核验证据，不能凭报告数字批准。Appendix A 自包含精确节点，不要求新增例外数据库或专用验证器。

| 文件 | SHA-256 / 事实 |
| --- | --- |
| `pytest-full.log` | `77f7319f576ce8bac4fb33c33b2fc26f0c882903f619a7ac0ce297d1100c08bd`；RC=1，47 failed、818 passed、7 skipped、29 errors |
| `old-failure-nodes.txt`、`new-failure-nodes.txt` | 二者均为 `cd7b1d4c6afd4840d08b9aba7f38144d7b1a4cf461d5e1da8b0f57bda294eae0`；对应前后两轮审计，不是执行前实跑 |
| `code.before.sha256` | `b02d2691cfd39f8fa7a8a43ded4fb1f9fcb18970918b8fc4ac642eac9b86ee21`；18 个修改 Python 文件的逐文件身份 |
| `worktree.before.patch` | `6bef1774c80dccb856e0548887f43f2b109e81a279ce5c905655b73047e0c823`；原 19 个修改文件的补丁快照 |
| `pytest-targeted.log` | `d240fd12563e8e19f6d34f282066278ec54bc261a955704cf247a8a8be12259b`；RC=0，23 passed、1 skipped、645 deselected |
| `continued-watch-probe.log` | `8e26bcbe33ab3dc3eb73746d3a7ff8a08f0a95f7739a5b10e83776ce02766e37`；修正审计时钟后 RC=0，证明实际冷却截止后第三次改期仍被重查 |

818 是完整命令所有通过节点的总数，包含其中通过的 G 测试，不是 D/F 专属计数。23 项定向通过也不能代替其余相关回归。真实来源测试的 skip 不等于真实来源验证通过。

## 3. 拟替换的验收条款

1. **完整诊断始终保留。** 原 Task 5 的全部测试路径仍运行；允许增加报告参数，不得过滤文件。完整命令的实际 RC、PASSED/FAILED/ERROR/SKIPPED/XFAIL、收集数量和原因全部记录，非零不得改报零。
2. **例外按三元组适用。** 只有 Appendix A 中精确 `nodeid + FAILED/ERROR + §2.1 对应根因/阶段` 一致的当前失败才可进入待处理集合。76 个条目是上限，不是必须凑满的配额；同节点换成其他失败、ERROR/FAILED 类型变化、收集/导入/环境失败、其他冻结文件漂移或新增失败，均不在例外内。
3. **保留全部其他测试。** 完整日志逐项归因后，可生成 pytest 原生 `--deselect=<nodeid>` 参数，但 pytest 按前缀匹配，传入完整 nodeid 不等于精确排除。必须先收集不带 deselect 的完整集合 F 和带参数的实际剩余集合 R，确认 `F - R` 与本轮已归因例外集合 E 完全相等，且 `R - F` 为空，才可运行必过集并要求 RC=0。额外缺失、应排而未排或集合漂移立即停止，不允许 `complete`，不得放宽例外来容纳前缀误排。不得用整文件排除、宽泛 `-k`、新增 skip/xfail 或更改断言来获得零退出码。已恢复 PASS 的旧节点继续留在必过集合；独立确认不是绕过门禁导致的假恢复。
4. **防止选择集漂移。** 完整运行的每个节点必须归入实际 PASS、经原契约/授权解释的 skip 或精确已归因例外之一。完整与必过运行保留 `-vv` 的逐 nodeid 结果；各次实际运行节点集合还须分别与对应收集集合完全一致，重复完整收集也须一致。必过集不得出现未解释的新 skip/xfail、额外 deselect、零收集或丢失既有测试。核对节点身份与原因，不只比较 47/29 或 7 等总数。例外已故障的下游行为仍明确未覆盖。
5. **其他门禁不变。** 原 Task 5 的 Ruff、scanner（warning 逐项解释）、diff/cached diff、未跟踪范围、所有 `INV-*` 接线/独立期望和安全配置仍须满足原要求。不因本文增加独立 Rule 17 Verifier，也不绕过已有 validator/profile。
6. **结论限于编码范围。** 独立审计只有在上述条款及全部其他原要求满足时，才可就“原 Plan + 获批本文限定的 D/F 代码与合成测试范围”给出 `complete`。报告必须同时列出完整回归的真实非零结果、精确例外及未覆盖范围，不得称全库全绿、1.5G 兼容通过、真实来源已验收或线上恢复成功。
7. **停止条件。** 身份/证据缺失、例外归因不成立、新异常、非例外测试失败或选择集不诚实时保持 `blocked`。本文不授权任何进一步代码修复；须按实际影响另行 Rule 16 分流，不自动扩大例外或修复范围。

## 4. 获批后的最小验证步骤

### 4.1 身份与证据绑定

Dependencies：B 审查通过，用户明确批准本文精确 SHA 及上述验收变化。只收到“同意继续”或旧 Plan 实施批准不足以执行新验收。

```bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. GIT_OPTIONAL_LOCKS=0
unset PYTEST_ADDOPTS STAGE15_POSTPONEMENT_REAL_FIXTURE_DIR
PLAN=docs/plans/2026-11-13-stage1-5d-1-5f-postponed-launch-readiness-and-reobservation-hotfix-implementation-plan_CN.md
DESIGN=docs/designs/2026-11-13-stage1-5d-1-5f-postponed-launch-readiness-and-reobservation-hotfix-design_CN.md
DELTA=docs/plans/2026-11-14-stage1-5d-1-5f-hotfix-task5-acceptance-boundary-delta_CN.md
: "${APPROVED_TASK5_DELTA_SHA256:?must come from explicit user approval}"
test "$(shasum -a 256 "$PLAN" | awk '{print $1}')" = 814479e367551d33819562b71d39f426a283d05e30f1d5a7313f2990421b063c
test "$(shasum -a 256 "$DESIGN" | awk '{print $1}')" = f8d5f404e55893f86208c724537077fdcabc391a4d90bebba8bafc94fe619874
test "$(shasum -a 256 "$DELTA" | awk '{print $1}')" = "$APPROVED_TASK5_DELTA_SHA256"
RUN=$(mktemp -d /private/tmp/stage15-task5-revalidation.XXXXXX)
mkdir "$RUN/tmp"
export TMPDIR="$RUN/tmp"
git -c core.fsmonitor=false rev-parse HEAD > "$RUN/HEAD.txt"
git -c core.fsmonitor=false status --short --untracked-files=all > "$RUN/status.before.txt"
git -c core.fsmonitor=false diff > "$RUN/worktree.before.patch"
git -c core.fsmonitor=false diff --cached > "$RUN/index.before.patch"
shasum -a 256 "$PLAN" "$DESIGN" "$DELTA" > "$RUN/authority.sha256"
shasum -a 256 -c /private/tmp/stage15-closure3-audit.hJ5PDN/code.before.sha256
```

身份错误立即 `STOP=approved_authority_mismatch`；参考代码身份变化则先核对变更及证据依赖，不沿用旧关闭证据。复用的是 pytest 原生选择、原有测试/validator、Git 基线和 SHA 检查；不新建 Recorder、插件或通用门禁框架。

**Mandatory identity & evidence check：**原 Plan/Design SHA 不变；新增本文 SHA 与两者组成新的验收授权绑定。未变更的源码证据可保留，但不能用上轮日志代替本次必过集实跑。本文不改变源包文件集，不生成或刷新任何生产 source bundle、收据、旧运行授权或 `RUN_ID`；任何已有证明若依赖原验收结论/权限，仍不得自动继承。真实 fixture、proof commit、部署和采集新批次继续按原 Plan §7 另行授权及重验。

### 4.2 完整回归、精确归因和其余节点必过

Dependencies：§4.1。下列为同一 Bash 会话；`-vv -ra --color=no` 保留逐 nodeid 结果及 skip 原因，不改变测试选择。收集使用单独的 `--collect-only -q`，不叠加运行命令的 verbosity 参数。完整命令先实跑，不能只运行剔除集；收集失败、结果提取为空或任何集合比较失败均立即停止。

```bash
PYTEST=(.venv/bin/python -m pytest -vv -p no:cacheprovider -ra --color=no)
COLLECT=(.venv/bin/python -m pytest --collect-only -q -p no:cacheprovider --color=no)
TESTS=(
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py
  tests/research/external_signal_shadow/test_stage1_5d_*.py
  tests/research/external_signal_shadow/test_stage1_5f_*.py
  tests/research/external_signal_shadow/test_stage1_5g_*.py
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
)
"${COLLECT[@]}" "${TESTS[@]}" > "$RUN/collection.full.log" 2>&1
awk '/^tests\/.*::/ {print}' "$RUN/collection.full.log" | LC_ALL=C sort > "$RUN/collection.full.nodes"
test -s "$RUN/collection.full.nodes"
if "${PYTEST[@]}" "${TESTS[@]}" > "$RUN/full.log" 2>&1; then
  FULL_RC=0
else
  FULL_RC=$?
fi
printf '%s\n' "$FULL_RC" > "$RUN/full.rc"
case "$FULL_RC" in 0|1) ;; *) echo 'STOP=unexpected_pytest_execution_failure'; exit 1;; esac
sed -nE 's/^(tests\/.*::.*) (PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)([[:space:]].*)?$/\1/p' "$RUN/full.log" | LC_ALL=C sort > "$RUN/full.executed.nodes"
cmp "$RUN/collection.full.nodes" "$RUN/full.executed.nodes"
awk '/^<!-- task5-known-failures:start -->$/ {p=1; next}
     /^<!-- task5-known-failures:end -->$/ {p=0}
     p && /^(FAILED|ERROR) tests\// {print}' "$DELTA" | LC_ALL=C sort > "$RUN/approved-exceptions.txt"
test "$(wc -l < "$RUN/approved-exceptions.txt" | tr -d ' ')" = 76
awk '/^(FAILED|ERROR) tests\// {print $1 " " $2}' "$RUN/full.log" | LC_ALL=C sort > "$RUN/actual-failures.txt"
LC_ALL=C comm -23 "$RUN/actual-failures.txt" "$RUN/approved-exceptions.txt" > "$RUN/unexpected-failures.txt"
test ! -s "$RUN/unexpected-failures.txt"
```

**人工/独立审计暂停点：**上面只能证明节点及结果类型属于候选集合，不能证明根因。逐条阅读 `full.log` 的异常链/fixture 或子进程堆栈，完成 §3 的根因、skip 和选择集核对，直接在交付报告说明；不另建强制台账。任一不符即停止，禁止执行下面的 deselect。不得将“来自某个 G 文件”或某个错误字符串出现在日志任意位置作为整组归因。

确认后先核对实际排除集合，再运行必过集；不能只看参数名称或 deselected 数量。若前缀参数误排了其他节点，本命令必须阻断，不能以 RC=0 继续验收：

```bash
DESELECT=()
while read -r outcome nodeid; do
  test -n "$nodeid"
  DESELECT+=("--deselect=$nodeid")
done < "$RUN/actual-failures.txt"
"${COLLECT[@]}" "${TESTS[@]}" > "$RUN/collection.full.recheck.log" 2>&1
awk '/^tests\/.*::/ {print}' "$RUN/collection.full.recheck.log" | LC_ALL=C sort > "$RUN/collection.full.recheck.nodes"
cmp "$RUN/collection.full.nodes" "$RUN/collection.full.recheck.nodes"
"${COLLECT[@]}" "${TESTS[@]}" "${DESELECT[@]}" > "$RUN/collection.required.log" 2>&1
awk '/^tests\/.*::/ {print}' "$RUN/collection.required.log" | LC_ALL=C sort > "$RUN/collection.required.nodes"
test -s "$RUN/collection.required.nodes"
LC_ALL=C comm -13 "$RUN/collection.full.nodes" "$RUN/collection.required.nodes" > "$RUN/collection.unexpected.nodes"
test ! -s "$RUN/collection.unexpected.nodes"
LC_ALL=C comm -23 "$RUN/collection.full.nodes" "$RUN/collection.required.nodes" > "$RUN/collection.removed.nodes"
cut -d ' ' -f 2- "$RUN/actual-failures.txt" | LC_ALL=C sort > "$RUN/exception.nodes"
cmp "$RUN/exception.nodes" "$RUN/collection.removed.nodes"
if "${PYTEST[@]}" "${TESTS[@]}" "${DESELECT[@]}" > "$RUN/required.log" 2>&1; then
  REQUIRED_RC=0
else
  REQUIRED_RC=$?
fi
printf '%s\n' "$REQUIRED_RC" > "$RUN/required.rc"
test "$REQUIRED_RC" = 0
sed -nE 's/^(tests\/.*::.*) (PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)([[:space:]].*)?$/\1/p' "$RUN/required.log" | LC_ALL=C sort > "$RUN/required.executed.nodes"
cmp "$RUN/collection.required.nodes" "$RUN/required.executed.nodes"
```

预期所有收集/集合核对命令 RC=0，必过集 RC=0、有实际 passed、仅精确例外被 deselect；不预报通过数。若当前代码仍保持参考快照，完整运行可能仍为 47 failed/818 passed/7 skipped/29 errors；只有实际排除集合核对通过后，必过集才可能为 818 passed/7 skipped/76 deselected。以上都不是本文已执行证据，也未断言现有 76 项已发生前缀误排。skip 必须结合详细日志逐 nodeid 核对授权/契约，不能仅以数量相等认可；实际输出格式无法逐节点对账时保持阻塞，不改用汇总数量自证。

### 4.3 原门禁及独立结论

Dependencies：§4.2。运行原 Plan Task 5 中原样的 Ruff、scanner、安全配置断言、范围及 authority 检查；均要求 RC=0，scanner warning 保留技术处置。测试/日志只写 `$RUN`，不能因只读审核而写仓内缓存。

```bash
git -c core.fsmonitor=false diff --check 2f9ba8e04821c3d7a477a65f2b73e34cb6beb442
git -c core.fsmonitor=false diff --cached --check
git -c core.fsmonitor=false diff > "$RUN/worktree.after.patch"
git -c core.fsmonitor=false diff --cached > "$RUN/index.after.patch"
git -c core.fsmonitor=false status --short --untracked-files=all > "$RUN/status.after.txt"
cmp "$RUN/worktree.before.patch" "$RUN/worktree.after.patch"
cmp "$RUN/index.before.patch" "$RUN/index.after.patch"
cmp "$RUN/status.before.txt" "$RUN/status.after.txt"
shasum -a 256 -c "$RUN/authority.sha256"
shasum -a 256 -c /private/tmp/stage15-closure3-audit.hJ5PDN/code.before.sha256
```

报告必须同时列出原 Plan SHA、Design SHA、本文批准 SHA、当前源码身份、原基线及本次验证目录；分别给出完整回归 RC、精确例外/归因、必过集 RC、skip 和未覆盖范围。独立审计者不使用 C 的自评替代这些证据；原八项关闭结果只有在相关代码/事实无新反证时保留。

## 5. 不变量与未验收边界

| 不变量 | 验收证据与不变边界 |
| --- | --- |
| `INV-01` | 原安全断言、旧根不写、authority/范围前后检查；本文不授权真实根读取或任何运行操作 |
| `INV-02`、`INV-03` | 原 F loader/models/state/runner 的状态、时间、冲突/固定期限测试继续纳入必过集，不作例外 |
| `INV-04` | 原 D 溯源及 serializer/strict consumer 测试继续必过；真实官方 raw 另行授权，skip 不作通过 |
| `INV-05`、`INV-06` | 原重查预算/期限、canonical transport 与 D poll 到 F registry 入口证据继续核验，不用导入或计数替代 |
| `INV-07`、`INV-08` | 原新根恢复、bootstrap/consumer/Git proof 负向与正向测试继续必过；生产 prerequisites 不由合成测试置 true |
| G 及旧 F 例外 | 不声明其后续行为已验证，不晋级任何数据、不改 1.5G 规则；修旧 F 路径须另获测试白名单批准，改变冻结 G 契约须单独走 Rule 16 |

**审批与收尾：**B 只审本文的验收变化、基线归因、精确例外及权限边界，不无依据重审已关闭实现。用户批准本文前，当前结论维持 `blocked`；批准后也须实际重验和独立审计，不能凭批准直接改成 `complete`。本文未授予 implementation、commit、push、deployment、SSH、runtime、paper 或 live 权限，`RISK_LIVE_TRADING_ENABLED=False` 不变。

## Appendix A. 精确候选例外节点

以下逐行列出原 pytest 结果类型与完整 nodeid；每行还须满足 §2.1 对应根因/阶段。此清单只能经审查和用户批准修改，不得由新日志自动扩充。总计 47 FAILED + 29 ERROR = 76，分布为 F 3、G cross-root 35、G N3 38。

<!-- task5-known-failures:start -->
```text
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_classify_receipt_state
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_compare_admitted_projection_mismatch
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_final_root_collision_rejected
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_post_rename_durability_failure
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_pre_rename_failpoints[after_manifest_fsync]
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_pre_rename_failpoints[after_manifest_write]
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_pre_rename_failpoints[after_review_fsync]
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_pre_rename_failpoints[after_review_write]
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_pre_rename_failpoints[after_staging_fsync]
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_pre_rename_failpoints[after_summary_fsync]
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_pre_rename_failpoints[after_summary_write]
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_lifecycle_pre_rename_failpoints[before_rename]
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_loader_rejects_forged_child_event_symbol_id
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_loader_rejects_forged_parent_identity
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_publish_and_load_verified_cross_root_receipt
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_reducer_config_threshold_not_met
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_reducer_duplicate_event_id
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_reducer_duplicate_event_symbol_id
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_reducer_duplicate_source_article
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_reducer_duplicate_symbol
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_reducer_missing_child
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_render_review_matches_literal_template
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_single_mutation_injected_markdown
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_single_mutation_manifest_hash_mismatch
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_single_mutation_manifest_missing_artifact
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_single_mutation_summary_extra_key
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_single_mutation_summary_wrong_authority_flag
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_single_mutation_symlink_artifact
ERROR tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_single_mutation_unlisted_file
FAILED tests/research/external_signal_shadow/test_stage1_5f_historical_anchor_rejection_hygiene.py::test_end_to_end_genuine_rejection_retains_identity
FAILED tests/research/external_signal_shadow/test_stage1_5f_historical_anchor_rejection_hygiene.py::test_end_to_end_historical_anchor_rejection_hygiene_flow
FAILED tests/research/external_signal_shadow/test_stage1_5f_historical_anchor_rejection_hygiene.py::test_end_to_end_rejection_hygiene_malformed_rows
FAILED tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_isolated_subprocess_origin_and_chdir_independence
FAILED tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_negative_missing_source_root
FAILED tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_negative_source_sha256sums_digest_corruption
FAILED tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_negative_stored_summary_byte_corruption
FAILED tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_production_loader_called_once_per_root_via_profile
FAILED tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py::test_real_root_cross_root_admission_positive_contract
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_admit_frozen_n3_inputs_rejects_missing_record
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_admit_frozen_n3_inputs_rejects_tampered_source_manifest_hash
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_admit_frozen_n3_inputs_rejects_tampered_stored_summary_hash
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_build_n3_summary_rejects_duplicate_parent_article
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_build_n3_summary_rejects_regime_field_mutation
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_build_n3_summary_rejects_wrong_url_in_declaration
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_ct_projection_rejects_changed_batch7_duplicate_child
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_ct_projection_rejects_missing_ct_child
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_ct_projection_rejects_ninth_child
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_final_root_collision_rejected
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_future_consumer_attempt_raises_fatal_stop
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_after_rename_raises_post_rename_durability_failure
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_post_rename_durability_failure
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_pre_rename_failpoints[after_manifest_write]
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_pre_rename_failpoints[after_review_write]
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_pre_rename_failpoints[after_summary_write]
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_pre_rename_failpoints[before_manifest_write]
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_pre_rename_failpoints[before_rename]
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_pre_rename_failpoints[before_review_write]
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_pre_rename_failpoints[before_summary_write]
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_lifecycle_pre_rename_foreign_sibling_fails_closed
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_loader_rejects_forged_manifest_relative_path
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_loader_rejects_forged_product_regime_ledger
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_loader_rejects_markdown_projection_mismatch
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_loader_rejects_noncanonical_manifest
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_loader_rejects_symlink_final_root
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_loader_rejects_tampered_manifest
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_production_loader_called_once_per_root_via_profile
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_public_writer_rejects_symlink_root
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_publish_and_load_verified_n3_receipt
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_real_root_n3_admission_positive_contract
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_render_review_content
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_summary_authority_flag_true_rejected
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_summary_extra_key_rejected
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_unlisted_file_in_final_root_rejected
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_verify_execution_authority_happy_path
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_verify_frozen_upstream_contract_happy_path
FAILED tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py::test_writer_rejects_ancestor_symlink_output_parent

```
<!-- task5-known-failures:end -->
