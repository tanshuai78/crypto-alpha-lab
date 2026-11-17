# Stage 1.5D 对 F 消费者证明的新鲜度校验返修 Plan 增补

状态：Draft，待 Model B 定向审查与用户按本增补精确 SHA-256 批准。仅纠正运行证明的实现偏差，不新增 Design，不授予执行权限，不涉及 Alpha 或策略研究。

## Allowed Change Scope

| 类别 | 精确范围 |
| --- | --- |
| Allowed implementation paths | `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`：仅 `verify_stage1_5f_consumer_proof` 的已有心跳过期比较。 |
| Allowed verification paths | `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`：仅新增/调整本增补的新鲜度测试及复用现有证明 fixture 所需的最少代码。 |
| Allowed generated paths | 新建仓外 `/private/tmp/stage15-consumer-freshness.*`；命令、日志、合成 fixture、pytest 临时根及必要的合成 Git 仓都在其内。测试已有临时 Git fixture 只能在该目录内生成提交。 |
| Affected but unchanged | 父 Design/Plan、本增补、`configs/base.py`、F 生产与测试文件、D 启动/轮询调用顺序、Git/受保护树证明规则、锁存逻辑、canonical schema/F watermark/1.5G、同页改期语义与历史运行产物。 |
| Forbidden | 全仓重构、增加配置键/Schema/状态机/验证器、改 F 采集周期或改配置值、修改既有证据/冻结哈希；实际运行、实源读取或回放、联网、SSH、采集启停、仓库暂存/提交/推送、部署、启用 Producer 或交易。 |

**目标：** 使 D 的 F 摘要心跳年龄检查遵守已批准的既有 runtime-gate 新鲜度上限。现行 `configs/base.py` 的 `EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_STALENESS_SEC` 为 180；不修改该值，不改变证明构成或运行权限。

## 1. 权威绑定与缺陷证据

| 角色 | 路径 | SHA-256 |
| --- | --- | --- |
| 进程证明契约（§6.3，现文第 331、338 行；生命周期按既有 ARMED 条款） | `docs/designs/2026-08-10-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-git-ancestry-attestation-design_CN.md` | `28cd9e55540a3eccfd24cca3598acdb7959d02407ff54edf1045765cba5b2f36` |
| 同页 Design（启用边界 `INV-04`） | `docs/designs/2026-11-15-stage1-5d-same-page-revision-scope-design_CN.md` | `08fdc6c4af79a0aaf93033c94b6cc95dd39ae67cdd781dfbeb1049ab6c2b8176` |
| 获批父 Plan（§5 启用证据保持不变） | `docs/plans/2026-11-15-stage1-5d-same-page-revision-scope-implementation-plan_CN.md` | `7932636016fd975d80fb0ed73be7048e4584a826231f50cb4a5fc045602c115d` |

基线部署提交：`0f9e820e2639aa3e07d1aa19e9d6f3ea4272b9e1`。用户提供的 VPS 批次 `20261117T031640Z_0f9e820` 检查输出：同一 F 实例心跳 `1794887394072 → 1794887454101 → 1794887514125`（间隔 60,029 / 60,024 ms），3 个新鲜时点通过，61 次重复抽查返回过期；不是 61 次采集失败，也未观察到 Producer 已启用后锁存。日志仅为报障证据，不是本地测试输入，不作为运行证明继承。

源码：D verifier 硬编码 `now_ms - last_hb > 10_000`，启动和后续启用轮询共用该入口；F 常驻每轮写摘要后休眠 60 秒。已批准 Design 指定沿用既有 runtime-gate 新鲜度上限；现有 F 上游 gate loader 已使用上述配置按秒转毫秒。若在 Producer 已 arm 后读到过期摘要，D 会锁存停用本进程的正式改期发射；当前生产者关闭，不推断已发生此结果。

**Rule 16 路由：** 缺陷性质是实现偏离（`BLOCKED_IMPLEMENTATION_DEFECT`）；修补的是父 Plan §5 的运行证明，不是上次已批准的同页实现任务。虽未增加代码路径，仍按有限任务增补（`BLOCKED_SCOPE_DRIFT`）送 B 审查并取得新授权。只还原已有上限；若要改变冻结的阈值语义、身份约束、锁存、安全或运行生命周期，停止并按 `BLOCKED_SPEC_DRIFT` 返回 Design。

## 2. Task 0：身份、环境与变更基线

依赖：B 推荐批准，用户绑定本增补 SHA-256 和父 Plan SHA-256 的明确本地实施授权。Bash 仓根执行；`APPROVED_SUPPLEMENT_SHA` 必须来自用户批准原文，不得用磁盘摘要反填。以下各段共用同一 shell。任一步身份不符即停止，不切到其他提交、不覆盖本地改动。

```bash
set -euo pipefail
export GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.
g() { git -c core.fsmonitor=false "$@"; }
H() { shasum -a 256 "$1" | cut -d ' ' -f 1; }
BASE_SHA=0f9e820e2639aa3e07d1aa19e9d6f3ea4272b9e1
SUP=docs/plans/2026-11-17-stage1-5d-consumer-proof-freshness-plan-supplement_CN.md
PLAN=docs/plans/2026-11-15-stage1-5d-same-page-revision-scope-implementation-plan_CN.md
DESIGN=docs/designs/2026-11-15-stage1-5d-same-page-revision-scope-design_CN.md
PROOF_DESIGN=docs/designs/2026-08-10-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-git-ancestry-attestation-design_CN.md
DR=scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
DT=tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
FT=tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
test "$(pwd -P)" = "$(g rev-parse --show-toplevel)"
test "$(g rev-parse HEAD)" = "$BASE_SHA"
test "$(H "$SUP")" = "${APPROVED_SUPPLEMENT_SHA:?STOP=missing_user_approved_sha}"
test "$(H "$PLAN")" = 7932636016fd975d80fb0ed73be7048e4584a826231f50cb4a5fc045602c115d
test "$(H "$DESIGN")" = 08fdc6c4af79a0aaf93033c94b6cc95dd39ae67cdd781dfbeb1049ab6c2b8176
test "$(H "$PROOF_DESIGN")" = 28cd9e55540a3eccfd24cca3598acdb7959d02407ff54edf1045765cba5b2f36
test "$(H configs/base.py)" = ffbc2129a206d3ff7c0a039f10fabc6446a52c9f85c9a869975821b9c0d87079
W=$(mktemp -d /private/tmp/stage15-consumer-freshness.XXXXXX)
printf '%s\n' "$BASE_SHA" > "$W/BASE_SHA.txt"
g status --porcelain --untracked-files=all > "$W/before.status"
printf '?? %s\n' "$SUP" | diff - "$W/before.status"
g diff --binary > "$W/before.worktree.patch"
g diff --cached --binary > "$W/before.index.patch"
g ls-files --others --exclude-standard > "$W/before.untracked"
shasum -a 256 "$SUP" "$PLAN" "$DESIGN" "$PROOF_DESIGN" configs/base.py "$FT" > "$W/bound.sha256"
unset STAGE15_SAME_PAGE_REAL_EVIDENCE_DIR STAGE15_SAME_PAGE_APPROVED_MANIFEST_SHA256
unset STAGE15_POSTPONEMENT_REAL_FIXTURE_DIR
```

期望 RC=0；唯一执行前非 clean 项是尚未提交的增补本身。其他已存在改动或 HEAD 漂移均暂停，不清理工作区也不自动重绑。仓外 `W` 是本地验证目录，不是 VPS `RUN_ID`。

## 3. Task 1：公开校验入口 TDD 与受影响回归

依赖 Task 0。仅改 `DR` / `DT`。复用 `verify_stage1_5f_consumer_proof` 及现有 `_setup_canonical_git_and_consumer_proof`：它在 pytest 临时目录构造隔离 Git fixture，并通过真实 D gate builder/writer 和 F 入口生成证明。冻结 fixture 时钟，把 F 落盘的 `last_heartbeat_at_ms` 作为输入锚点，对 D verifier 传递独立给定的 `now_ms`；不替换被测 verifier、F canonical writer、摘要 SHA 或进程身份检查。mock 只用于外部响应、时钟及临时仓定位，不宣称验证实际 VPS。

- **RED：** 新增 `test_verify_stage1_5f_consumer_proof_uses_runtime_gate_staleness`。固定年龄 `60_029`、`180_000`、`180_001` ms，断言依次通过、通过、`consumer_summary_heartbeat_expired`。期望值是固定测试向量，不从生产配置计算。再通过 `monkeypatch` 仅在进程内把配置值置为 `90`，断言 `90_000` 通过、`90_001` 拒绝，以防实现只是把字面量换成另一字面量。先单跑节点，必须证明至少第一个正向失败确由当前拒绝正常年龄引起，非 fixture 失败。
- **GREEN：** 在现有比较处以 `base.EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_STALENESS_SEC * 1000` 代替 `10_000`，保留现有边界 `>`、拒绝 reason、显式 `stale` 拒绝及两个生产调用点。不得以无时钟调用、写新摘要或删保护条件回避失败。
- **保持行为证据：** 同一 fixture 中以单点变更验证 `stale=True` 在新鲜时仍拒绝（`consumer_summary_stale`）；运行已有 hash/身份/不同 F 实例、D 锁存和 canonical D→F 闭环测试。用源码 diff 核对 post-arm 失败到 sticky latch 的生产接线未变；现有的本地锁存回归与进程身份测试不冒称是 VPS 上启用后的实测。若发现其他有限时间/身份字段缺陷，另记证据，不扩大本增补。
- **最小改动：** 一个现有比较式及定向测试；不新增抽象、fixture 目录、生命周期测试框架，不调整 F 定时、网络调用和 D/F 证明载体。

按顺序单独执行以下三个阶段：写测试后执行 RED，确认失败原因后才修改生产代码，然后执行 GREEN 和回归。不要一次粘贴三条测试命令。以下函数将每个命令、合并输出和实际 RC 记录在仓外 W；期望 RED RC=1，其余 RC=0。

```bash
run_logged() {
  local label=$1 expected=$2 rc=0
  shift 2
  printf '%q ' "$@" > "$W/$label.command"
  printf '\n' >> "$W/$label.command"
  "$@" > "$W/$label.log" 2>&1 || rc=$?
  printf '%s\n' "$rc" > "$W/$label.rc"
  test "$rc" -eq "$expected"
}
run_logged red 1 .venv/bin/python -m pytest -q -rA -p no:cacheprovider --basetemp "$W/red" \
  "$DT::test_verify_stage1_5f_consumer_proof_uses_runtime_gate_staleness"
run_logged green 0 .venv/bin/python -m pytest -q -rA -p no:cacheprovider --basetemp "$W/green" \
  "$DT::test_verify_stage1_5f_consumer_proof_uses_runtime_gate_staleness"
run_logged regression 0 .venv/bin/python -m pytest -q -rsxX -p no:cacheprovider --basetemp "$W/regression" \
  "$DT" "$FT" tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
```

须阅读实际日志，不能用 RED 的 RC=1 代替失败归因。回归所有 skips / xfails 列节点、原因；既有未授权实源 skip 不算通过，新增合成测试不得 skip/xfail。没有旧失败例外自动豁免。

## 4. Task 2：交付核验与后续权限

依赖 Task 1：

```bash
.venv/bin/ruff check --no-cache "$DR" "$DT"
.venv/bin/python .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
g diff --check
g diff --cached --check
test "$(g rev-parse HEAD)" = "$BASE_SHA"
g diff --cached --binary > "$W/after.index.patch"
cmp "$W/before.index.patch" "$W/after.index.patch"
g ls-files --others --exclude-standard > "$W/after.untracked"
cmp "$W/before.untracked" "$W/after.untracked"
printf '%s\n' "$DR" "$DT" | LC_ALL=C sort > "$W/allowed.changed"
g diff --name-only "$BASE_SHA" | LC_ALL=C sort > "$W/actual.changed"
cmp "$W/allowed.changed" "$W/actual.changed"
g status --porcelain --untracked-files=all > "$W/after.status"
g diff --binary > "$W/after.worktree.patch"
shasum -a 256 -c "$W/bound.sha256"
.venv/bin/python - <<'PY'
from configs import base
from src.risk.limits import RiskLimits
assert base.RISK_LIVE_TRADING_ENABLED is RiskLimits.live_trading_enabled is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA == ""
PY
```

| 冻结约束 | 验收证据 |
| --- | --- |
| 既有 Git/消费者证明 Design 的 `INV-A8`，及 §6 的绑定与失效保护 | Task 1 的 canonical 摘要 + 独立时间向量；原证明、F 身份和锁存回归；生产两处调用、锁存与写入路径 diff 未改。 |
| 同页 Design `INV-03` / `INV-04` 的受影响边界 | Task 1 既有同页 D→F 闭环回归；Task 0/2 范围、配置与版本证据。未触碰 `INV-01` / `INV-02` 的对应实现场景，不作重新验收或扩展承诺。 |

保存 `W`、前后范围快照、RED/GREEN/回归命令与退出码，交独立 Completion Audit。Rule 15 采用现有 canonical 接线，Rule 17 本增补不新产出或改写授权载体、Schema 或冻结 profile，不加独立 Verifier。执行者不得自审宣告 `complete`。

**不属于本增补的执行权限：** 新 proof commit、父 Plan §5 的适用 Part A、真实 HYPE/TRX 离线验证，以及候选版本的 Git/消费者运行、同根 watermark 复核，均按原流程分别授权并绑定新版本；不得把 `0f9e820` 的结果直接继承给修复版。线上现有 D/F 保持只读，Producer 继续关闭。本增补批准或 Completion Audit 通过均不授权提交、推送、部署、重启、实源访问、paper 或 live。
