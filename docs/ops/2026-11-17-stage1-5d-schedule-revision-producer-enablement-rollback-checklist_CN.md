# Stage 1.5D 同页改期 Producer 启用与回退清单

状态：**待审查、待单独授权；当前不执行。** Producer 指 1.5D 的正式同页改期发布功能，不是交易开关。启用后仍是 1.5D 公告采集、1.5F 公开盘口观察；`RISK_LIVE_TRADING_ENABLED=False`，不新增任何交易或执行权限。本清单不替代已批准的 Design/Plan，不是配置变更、Git、SSH 或部署授权。

## 1. 版本与证据

| 项目 | 绑定或状态 |
| --- | --- |
| Proof commit A（及本次已知可用的关闭版） | `de0420bf68a47e1b25bd14e1c5e6daa8b499250a` |
| Config-only enablement commit B | 尚未创建；待审查、授权后方可绑定完整 SHA。B 不等于 A。 |
| 权威规范 | [Git/消费者证明 Design §4、§8、§11](../designs/2026-08-10-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-git-ancestry-attestation-design_CN.md)、[同页范围 Design](../designs/2026-11-15-stage1-5d-same-page-revision-scope-design_CN.md)、[原 Plan §5](../plans/2026-11-15-stage1-5d-same-page-revision-scope-implementation-plan_CN.md)、[新鲜度返修增补](../plans/2026-11-17-stage1-5d-consumer-proof-freshness-plan-supplement_CN.md)、[运维手册 §4、§5、§9.2](2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md)。 |
| A：Part A / 定向回归 | 仓外 `/private/tmp/stage15-part-a-de0420b.7G4Jdq/SHA256SUMS`，SHA-256 `685508a003b759961bcc5cb766e23741488be0f81334830cf2e2d1d54902cec8`；Tasks 1–4 和心跳回归均 RC=0，实源入口 skip 不计为通过。 |
| A：HYPE/TRX 实源离线回放 | 仓外 `/private/tmp/stage15-real-de0420b.Ilvkee/SHA256SUMS`，SHA-256 `a269f81e8b1d65638c5a9dede5157fed976bc5e59e151bcec1cc95afae403e4b`。批准的输入 manifest SHA-256 `c910178580656a65066851d1de6013b11d18cffeda0d04899836a956149cf203`；本地实跑 RC=0，D 发出两条 v2 修订，F 各应用一次，未采盘口。 |
| A：VPS 关闭版证据 | 用户提供的 `DEPLOY_AND_F_PROOF=PASS`；`RUN_ID=20261117T082421Z_de0420b`，日志目录 `/tmp/stage15-de0420b-resume.hWDE2w`（VPS 路径）。D READY、Git 静态证明及 watermark 通过；同一 F 实例在两个不同心跳的年龄 11,839 / 11,848 ms 通过。只证明当次关闭版；启用前重新核对实际线上进程。 |
| 证据限制 | VPS 心跳测试通过时仅在临时目录纠正 mock 文件名大小写，未动仓库；不宣称原样 Linux 测试通过。若后续要改仓库测试，另按变更范围审查并检查新版本证据绑定。本轮未查看 VPS 原始文件，未验 B 的运行证明或真实线上改期。 |

先把上述临时日志、校验清单及实际输出留存在持久仓外证据目录；校验清单须能重新执行校验，VPS 日志经授权只读取得。留存时注明 A、新旧 RUN_ID、捕获时间和出处；不改旧产物、不把历史观测或离线回放当作 B 的运行证明。未取得或不能重验必需证据时停留在关闭版。

## 2. 启用前核验

- [ ] 独立审查记录 `proof_commit_sha`、`part_a_suite_run_at_commit`、`fixture_reviewed_against_commit` 均为 A；核对实际日志、退出码、各证据 SHA。A 的线上关闭版证据与当前进程身份应吻合。若 A 不再是候选的经过验证的受保护树，停止重验，不借用其他提交的测试。
- [ ] 用户明确批准启用分支、仅配置提交、推送、VPS 维护窗口和回退动作。不把本清单或上次 Completion Audit 当作执行授权。创建 B 后按完整 SHA 核对候选、来源分支和 A 的祖先关系；若已生成的 B 与批准身份或 diff 不符，不部署。
- [ ] `A → B` 的唯一变化路径为 `configs/base.py`，仅四处模块级赋值的字面量右值变化：`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA=A`；`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED=True`；`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED=True`；`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED=True`。这三项 True 仅在证据和授权齐备后设置，不调整 180 秒、F 就绪标准、重查预算或任何交易开关。使用现有 `verify_git_ancestry_and_static_proof` 核对完整非浅克隆、A 的祖先关系、D/F 受保护树等价、AST 白名单和干净工作树；不要以文件 diff 目测代替。
- [ ] 停机前现场复核当前 HEAD、两个实际 PID/tmux、D/F 根目录、旧 F 新鲜摘要及空活动/待启动队列；用精确 `/proc` 检查区分真实写入者。候选两个输出路径所在文件系统均至少有 `8 GiB` 可用空间，启动 F 前再查。证据不足、有在采/待启动观察或盘空间不足，不开始计划性切换。先确认回退版本 A 可签出且其安全开关为 False。

## 3. 分阶段启用：命令与身份绑定

以下命令是供复审的操作稿，不是运行授权。仅在 §2 通过、B 及执行窗口获批、E2 交接已在隔离环境验证之后使用。在 VPS 的 Bash 里分阶段执行，不要整段粘贴。所有证据写到仓外，不在运行根里加文件。

| 阶段 | 必须成立 |
| --- | --- |
| 切换 A → B | 复核旧 F 无活动/待启动观察。按运维手册停旧 F、旧 D，确认零写入者，再签出精确 B 并检查 Git 静态证明。为 B 分配新 RUN_ID 和 D/F 根。 |
| E0 | 用下方基准参数启动 D，不传 F 证明路径。等 V3 bootstrap 写盘、D READY、`configured_enabled=true` 且 `effective_enabled=false`。只能是等待 F 证明，不能把本地 Git/保护树错误当作正常等待。 |
| E1 | 按同一批 D gate/events 路径 bootstrap F，bootstrap 退出后启动常驻 F。固定 F 的 root、PID 和实例 ID。核验同根 watermark 和 F 运行证明；D 此时仍未有效启用。 |
| E2 | 见 §3.2。保持同一个 B、E0 D 根和 E1 F 实例，仅重启 D，追加两个 F 证明参数。D 启动、D READY、Producer ARMED 分别核验。 |

### 3.1 冻结命令基准

维护人员把获批 B 的完整 SHA 和新 RUN_ID 置入 `APPROVED_B`、`APPROVED_RUN_ID`；证据目录 `W` 为该次操作独有。先在实际 B checkout 执行 D/F 的 `--help`，核对下列参数。当前 A 的 CLI 已核对，B 尚未创建，不把该核对冒充 B 现场核验。

```bash
set -euo pipefail
umask 077
cd /root/crypto-alpha-lab
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. GIT_OPTIONAL_LOCKS=0
A=de0420bf68a47e1b25bd14e1c5e6daa8b499250a
B=${APPROVED_B:?missing approved B SHA}
RUN_ID=${APPROVED_RUN_ID:?missing approved new RUN_ID}
[[ "$B" =~ ^[0-9a-f]{40}$ && "$B" != "$A" ]]
[[ "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z(_[a-zA-Z0-9_-]+)?$ ]]
g() { git -c core.fsmonitor=false "$@"; }
test "$(g rev-parse HEAD)" = "$B"
test -z "$(g status --porcelain --untracked-files=all)"
B_CFG=$(sha256sum configs/base.py | cut -d' ' -f1)
W=$(mktemp -d /tmp/stage15-enable.XXXXXX)
PY="$PWD/.venv/bin/python"
DR="$PWD/scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py"
FR="$PWD/scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py"
DATA="$PWD/data/external_signal_shadow"
C1="$DATA/stage1_5c1/price_coverage/price_coverage_expansion_summary.json"
C="$DATA/stage1_5c/external_catalyst_replay_summary.json"
E="$DATA/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"
bind_roots() {
  D="$DATA/stage1_5d/live_event_source_continuous_$RUN_ID"
  F="$DATA/stage1_5f/live_depth_observer_$RUN_ID"
  DS="stage1_5d_continuous_$RUN_ID"
  FS="stage1_5f_live_depth_$RUN_ID"
  SUM="$D/binance_futures_launch_smoke_summary.json"
  GATE="$D/live_safety_gate_summary.json"
  EVENTS="$D/events/*.jsonl"
  D_ARGS=(--stage1-5c1-summary "$C1" --stage1-5c-summary "$C"
          --output-root "$D" --output-summary "$SUM"
          --poll-interval-sec 60 --max-seconds 604800 --live-public-readonly)
  F_ARGS=(--stage1-5d-events-glob "$EVENTS" --stage1-5d-runtime-gate "$GATE"
          --stage1-5e-summary "$E" --output-root "$F")
}
start() {
  local session=$1 log=$2 command payload
  shift 2
  printf -v command '%q ' env PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 "$@"
  printf -v payload 'exec %s >>%q 2>&1' "$command" "$log"
  tmux new-session -d -s "$session" -c "$PWD" "bash -c $(printf '%q' "$payload")"
}
writers() {
  "$PY" - <<'PY'
from pathlib import Path
p = Path("docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md")
lines = p.read_text().splitlines()
a = "<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_BEGIN -->"
b = "<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_END -->"
assert lines.count(a) == lines.count(b) == 1
i, j = lines.index(a), lines.index(b)
assert lines[i + 1] == "```python" and lines[j - 1] == "```"
ns = {"__name__": "inspector"}
exec(compile("\n".join(lines[i + 2:j - 1]), str(p), "exec"), ns)
for row in sorted(ns["inspect_writers"](Path("/proc"), Path.cwd()), key=lambda r: r["pid"]):
    print(row["pid"])
PY
}
bind_roots
"$PY" "$DR" --help > "$W/D.help"
"$PY" "$FR" --help > "$W/F.help"
printf '%s\n' "B=$B" "B_CFG=$B_CFG" "RUN_ID=$RUN_ID" "D=$D" "F=$F" > "$W/identity"
# 这些是分段命令：E0 前检查两个根不存在、空间及证明均满足 §2。
start "$DS" "$W/E0.log" "$PY" "$DR" "${D_ARGS[@]}"
# E0 READY 并证明未启用后才执行 E1 两条命令：
"$PY" "$FR" "${F_ARGS[@]}" --bootstrap-watermark > "$W/E1.bootstrap.log" 2>&1
start "$FS" "$W/E1.log" "$PY" "$FR" "${F_ARGS[@]}" --live-public-readonly
```

### 3.2 E1 → E2：同根恢复与有界交接

**STOP 条件先于命令。** 当前 D 每次启动会写 `INITIALIZING` gate，直到成功完成轮询；F 每轮用严格 loader 重验 D gate，遇到 `INITIALIZING` 也会阻断新事件。这不是 180 秒新鲜度能解决的问题。两个 180 秒分别限制 **F 摘要对 D** 和 **D gate 对 F** 的年龄，均不保证可停 180 秒。

- 交接只在 E0 D gate 为 READY 且 `generated_at_ms` 年龄不超过 **15 秒**、E1 F 刚完成一次有效轮询时开始。用 F 摘要的 `stage1_5d_runtime_gate_last_validated_at_ms`，要求当时年龄 **0–5 秒**、`stage1_5d_runtime_gate_invalid_count` 有明确基线、未阻断新准入。记录 F PID、实例 ID、三项 D 绑定、合约摘要、watermark 摘要、心跳、gate 生成时刻、E0 D PID 与实际 argv。F 线上非 mock 轮末休眠 60 秒；以此安排短窗口，不以会话存活或摘要时间代替证明。
- 从发出 E0 停机动作起，给整段 **45 秒单次预算**，每 **2 秒**读状态；其中确认 E0 退出最多 **10 秒**。预算含零写入者核对、V3 恢复前检及 E2 首轮发布 READY/ARMED，不是只等启动。45 秒是操作上限，不修改运行时阈值。时钟跳变、E0 PID 未退出、D 原 gate 已生变或失效、F 身份变化或任何轮询出现 `block_new_event_admission`、上游 gate 失效计数增加，立即 STOP；不重试 E2、不重启 F。
- 停 D 前及停 D 后、发 E2 前均调用现成校验：D 上游用 `validate_stage1_5d_runtime_gate(GATE, EVENTS, now_ms)`；F 证明用 `verify_stage1_5f_consumer_proof`，传入现有 F contract/summary、`canonical_root_id(D)`、B、`canonical_manifest_sha256("1.5F_v1", CONSUMER_RUNTIME_MANIFEST)` 和当前时间。另核验与 E1 的 PID、实例 ID、合约和水位线绑定仍一致。F 心跳更新是正常的，不强制摘要整文件不变。
- 下列命令仅用于该窗口内；每条失败均 STOP。V3 前检使用原生 `preflight_stage1_5d_v3_root`，结果须为 `resumable` 且无须修补或清理异常 intent。前检和启动都不修改身份字段。实际运行脚本仍会再次前检。

```bash
# 同一 Bash 会话连续执行此块，不在启动与监控之间插入人工步骤。
(
set -euo pipefail
command -v timeout >/dev/null
FC="$F/observer_root_contract.json"
FSUM="$F/live_depth_observer_summary.json"
E2_ARGS=("${D_ARGS[@]}" --stage1-5f-consumer-root-contract "$FC"
         --stage1-5f-consumer-summary "$FSUM")
E0_D_PID=$(tmux list-panes -t "=$DS" -F '#{pane_pid}')
E1_F_PID=$(tmux list-panes -t "=$FS" -F '#{pane_pid}')
[[ "$E0_D_PID" =~ ^[0-9]+$ && "$E1_F_PID" =~ ^[0-9]+$ ]]
cat "/proc/$E0_D_PID/cmdline" > "$W/E0.argv"
cat "/proc/$E1_F_PID/cmdline" > "$W/E1.argv"
printf '%s\0' "$PY" "$DR" "${D_ARGS[@]}" | cmp - "$W/E0.argv"
printf '%s\0' "$PY" "$FR" "${F_ARGS[@]}" --live-public-readonly | cmp - "$W/E1.argv"
printf '%s\0' "$PY" "$DR" "${E2_ARGS[@]}" > "$W/E2.expected.argv"
cp "$GATE" "$W/E0.gate.json"
cp "$FSUM" "$W/E1.summary.json"
sha256sum "$FC" "$F/watermark.json" > "$W/E1.bound.sha256"

remaining() {
  local left=$((45 - (SECONDS - E2_STARTED)))
  (( left > 0 )) || return 124
  printf '%s\n' "$left"
}
probe() {
  local cap=$1 phase=$2 started_ms=${3:-0}
  timeout -s KILL "${cap}s" "$PY" - "$phase" "$started_ms" "$W" "$D" "$F" "$B" "$EVENTS" <<'PY'
import sys

if sys.flags.optimize != 0:
    sys.exit("STOP=e2_probe_python_optimization_enabled")

import json
import time
from pathlib import Path
from configs import base
from scripts.external_signal_shadow import run_stage1_5d_live_event_source_smoke_collector as d
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import validate_stage1_5d_runtime_gate


def require(condition, reason):
    if not condition:
        sys.exit(f"STOP=e2_probe_{reason}")


phase, started, work, d_root, f_root, head, events = sys.argv[1:]
w, f = Path(work), Path(f_root)
gate_path = Path(d_root) / "live_safety_gate_summary.json"
summary_path = f / "live_depth_observer_summary.json"
contract = f / "observer_root_contract.json"
now = time.time_ns() // 1_000_000
s = json.loads(summary_path.read_bytes())
ref = json.loads((w / "E1.summary.json").read_bytes())
old_gate = json.loads((w / "E0.gate.json").read_bytes())
hb = s["last_heartbeat_at_ms"]
require(base.RISK_LIVE_TRADING_ENABLED is False, "live_trading_not_disabled")
require(0 <= now - hb <= 1000 * base.EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_STALENESS_SEC,
        "f_heartbeat_not_fresh")
instance = ref["consumer_process_instance_id"]
require(bool(instance) and s["consumer_process_instance_id"] == instance, "f_instance_mismatch")
n = s["stage1_5d_runtime_gate_invalid_count"]
require(type(n) is int and n >= 0 and n == ref["stage1_5d_runtime_gate_invalid_count"],
        "f_upstream_gate_invalid_count_changed")
require(s["block_new_event_admission"] is False and s["stage1_5d_runtime_gate_stale"] is False,
        "f_admission_blocked_or_gate_stale")
require(s["storage_guard_status"] == "ready" and s.get("storage_blocker") is None, "f_storage_not_ready")
require(s["stage1_5d_gate_mode"] == "runtime_gate", "f_wrong_gate_mode")
require(Path(s["stage1_5d_runtime_gate_path"]).resolve() == gate_path.resolve(), "f_gate_path_mismatch")
p = d.verify_stage1_5f_consumer_proof(
    consumer_root_contract_path=contract, consumer_summary_path=summary_path,
    expected_d_output_root_id=d.canonical_root_id(d_root), expected_d_startup_head_sha=head,
    expected_consumer_manifest_sha256=d.canonical_manifest_sha256("1.5F_v1", d.CONSUMER_RUNTIME_MANIFEST),
    now_ms=now,
)
require(p["valid"] and p["consumer_process_instance_id"] == instance, f"f_proof_invalid:{p.get('reason')}")
g = validate_stage1_5d_runtime_gate(gate_path, events, now)
s2 = json.loads(summary_path.read_bytes())
require(s2["consumer_process_instance_id"] == instance, "f_instance_changed_during_probe")
require(s2["stage1_5d_runtime_gate_invalid_count"] == n and s2["block_new_event_admission"] is False,
        "f_admission_changed_during_probe")
gate = g.get("gate_summary") or {}
if phase in {"before", "after_stop"}:
    require(g["valid"] and gate["status"] == "READY" and gate == old_gate, "e0_gate_not_ready_or_changed")
    require(gate["schedule_revision_producer_effective_enabled"] is False, "e0_producer_unexpectedly_enabled")
    if phase == "before":
        require(0 <= now - gate["generated_at_ms"] <= 15_000, "e0_gate_outside_handoff_window")
        require(0 <= now - s["stage1_5d_runtime_gate_last_validated_at_ms"] <= 5_000,
                "f_gate_check_outside_handoff_window")
else:
    require(phase == "monitor", "unknown_phase")
    if gate == old_gate:
        sys.exit(75)  # 不是新 E2 gate，继续在剩余预算内等待
    require(int(started) <= gate["generated_at_ms"] <= now, "e2_gate_timestamp_mismatch")
    require(d.canonical_root_id(gate["source_root"]) == d.canonical_root_id(d_root), "e2_d_root_mismatch")
    if (gate["status"], gate["decision"]) == ("INITIALIZING", "stage1_5d_runtime_gate_initializing"):
        sys.exit(75)  # 允许短暂初始化，但上面的 F 证明必须继续有效
    require(g["valid"] and gate["status"] == "READY", f"e2_gate_not_ready:{g.get('reason')}")
    require(gate["first_poll_started_at_ms"] >= int(started), "e2_poll_not_from_new_process")
    require(gate["successful_poll_count"] >= 1, "e2_no_successful_poll")
    require(gate["storage_guard_status"] == "ready" and gate.get("storage_blocker") is None,
            "e2_storage_not_ready")
    for key in ("configured_enabled", "consumer_prerequisites_verified", "effective_enabled"):
        require(gate[f"schedule_revision_producer_{key}"] is True, f"e2_producer_{key}_not_true")
    require(gate["schedule_revision_producer_health"] == "ready", "e2_producer_health_not_ready")
print(json.dumps({"phase": phase, "D_gate_ms": gate["generated_at_ms"],
                  "F_heartbeat_ms": hb, "F_instance": p["consumer_process_instance_id"]}))
PY
}

# E0 停机前，除双侧证明外，核验当前实际 F 的 watermark 已按 E1 验过。
probe 2 before > "$W/E2.precheck.log"
E2_STARTED=$SECONDS
launch_attempted=0
verified=0
E2_D_PID=
cleanup_e2() {
  local rc=$? current stopped_pid= stop_at
  trap - EXIT HUP INT TERM
  [ "$verified" -eq 0 ] || return 0
  printf 'STOP=e2_handoff_failed rc=%s elapsed=%ss\n' "$rc" "$((SECONDS - E2_STARTED))" >&2
  if [ "$launch_attempted" -eq 1 ]; then
    # DS 在 start 前以 list-sessions 确认不存在，且维护窗口独占；
    # 只处置本次尝试创建的 DS，不把 E1 或不明会话当作 E2。
    if ! current=$(timeout -s KILL 3s tmux list-sessions -F '#{session_name}'); then
      echo STOP=e2_stop_not_confirmed >&2
      exit 1
    fi
    if grep -Fxq "$DS" <<< "$current"; then
      if ! current=$(timeout -s KILL 3s tmux list-panes -t "=$DS" -F '#{pane_pid}') ||
         ! [[ "$current" =~ ^[0-9]+$ && "$current" != "$E0_D_PID" && "$current" != "$E1_F_PID" && "$DS" != "$FS" ]] ||
         ! { [ -z "$E2_D_PID" ] || [ "$current" = "$E2_D_PID" ]; } ||
         ! timeout -s KILL 3s tmux kill-session -t "=$DS"; then
        echo STOP=e2_stop_not_confirmed >&2
        exit 1
      fi
      stopped_pid=$current
      stop_at=$SECONDS
      while [ -e "/proc/$stopped_pid" ]; do
        if (( SECONDS - stop_at >= 10 )); then echo STOP=e2_stop_not_confirmed >&2; exit 1; fi
        sleep 2
      done
    fi
    # 确认只剩 E1 F；无法确认时不签出、不重启，按 §4 上报。
    if ! current=$(writers) || [ "$current" != "$E1_F_PID" ]; then
      echo STOP=e2_stop_not_confirmed >&2
    else
      echo E2_STOP_CONFIRMED >&2
    fi
  fi
  exit 1
}
trap cleanup_e2 EXIT
trap 'exit 1' HUP INT TERM
timeout -s KILL 2s tmux kill-session -t "=$DS"
while [ -e "/proc/$E0_D_PID" ]; do
  (( SECONDS - E2_STARTED < 10 )) || exit 1
  sleep 2
done
(( SECONDS - E2_STARTED < 10 ))
actual=$(writers)
test "$actual" = "$E1_F_PID"
test "$(g rev-parse HEAD)" = "$B"
test "$(sha256sum configs/base.py | cut -d' ' -f1)" = "$B_CFG"
left=$(remaining)
timeout -s KILL "${left}s" "$PY" - "$D" "$SUM" "$B" <<'PY'
from pathlib import Path
import sys
from scripts.external_signal_shadow import run_stage1_5d_live_event_source_smoke_collector as d
root, summary, head = sys.argv[1:]
root = Path(root)
r = d.preflight_stage1_5d_v3_root(
    root, Path(summary), expected_resume_provenance=d.build_stage1_5d_v3_resume_provenance(root, head))
print("V3_RESUME_PREFLIGHT", r["kind"], r["reason"])
if r["kind"] != "resumable" or r.get("crash_cleanup_row"):
    sys.exit("STOP=v3_same_root_resume_rejected_or_requires_cleanup")
if any(a.get("inflight_cycle") for a in (r.get("state") or {}).get("articles", {}).values()):
    sys.exit("STOP=v3_unresolved_inflight")
PY
check_e1() {
  test "$(tmux list-panes -t "=$FS" -F '#{pane_pid}')" = "$E1_F_PID" &&
    cmp "$W/E1.argv" "/proc/$E1_F_PID/cmdline" &&
    sha256sum -c --status "$W/E1.bound.sha256"
}
# 将 tmux 客户端调用（含 start）一并限制在本次剩余时间内；清理不用此期限。
tmux() {
  local cap
  cap=$(remaining) || return 124
  command timeout -s KILL "${cap}s" tmux "$@"
}
check_e1
left=$(remaining)
probe "$left" after_stop > "$W/E2.after_stop.log"
sessions=$(tmux list-sessions -F '#{session_name}')
if grep -Fxq "$DS" <<< "$sessions"; then exit 1; fi
E2_WALL_MS=$(date +%s%3N)
launch_attempted=1
start "$DS" "$W/E2.log" "$PY" "$DR" "${E2_ARGS[@]}"
E2_D_PID=$(tmux list-panes -t "=$DS" -F '#{pane_pid}')
[[ "$E2_D_PID" =~ ^[0-9]+$ && "$E2_D_PID" != "$E0_D_PID" && "$E2_D_PID" != "$E1_F_PID" ]]

while left=$(remaining); do
  test "$(tmux list-panes -t "=$DS" -F '#{pane_pid}')" = "$E2_D_PID"
  cmp "$W/E2.expected.argv" "/proc/$E2_D_PID/cmdline"
  check_e1
  test "$(g rev-parse HEAD)" = "$B"
  test "$(sha256sum configs/base.py | cut -d' ' -f1)" = "$B_CFG"
  left=$(remaining)
  if probe "$left" monitor "$E2_WALL_MS" >> "$W/E2.monitor.log" 2>&1; then
    # 在接受证据之前重新核对身份和同一计时器，超时不发成功标记。
    test "$(tmux list-panes -t "=$DS" -F '#{pane_pid}')" = "$E2_D_PID"
    check_e1
    remaining >/dev/null
    verified=1
    printf 'E2_ARMED_VERIFIED D_PID=%s F_PID=%s elapsed=%ss\n' "$E2_D_PID" "$E1_F_PID" "$((SECONDS - E2_STARTED))"
    exit 0
  else
    rc=$?
    [ "$rc" -eq 75 ] || exit "$rc"
  fi
  left=$(remaining)
  if (( left >= 2 )); then sleep 2; else sleep "$left"; fi
done
exit 124
)
```

`probe()` 拒绝任何 Python 优化模式（包括 `PYTHONOPTIMIZE=1`）；关键判定不依赖 `assert`。隔离演练须确认优化模式非零退出、不会输出 `E2_ARMED_VERIFIED`。

`75` 只表示仍看到 E0 gate 或同根 E2 的 `INITIALIZING`，不是通过；其他错误、超时、一般 HUP/INT/TERM 均进入清理。启动阶段不允许无人值守，维护会话和 tmux 只允许本次操作者使用。若控制 shell 被强杀、主机掉线或出现 `e2_stop_not_confirmed`，不得假定已停；按 §4 先核对并隔离本次 E2 D，未经确认不签出 A 或重启 F。这个监控限制**未验收进程继续运行**，不宣称程序在两次采样之间绝无短暂 ARMED；任何已落盘修订及观察都必须保留。
**尚待独立验证：** 用隔离的候选 B 演练上述有界切换，并观察 F 采到短暂 `INITIALIZING` 时的 STOP 路径。本稿未在 B 或 VPS 运行 E2；如果不能证实交接窗口足够且保持同一 F，实际启用维持 STOP，按 Rule 16 路由。不得添加 `--resume`、`--future-launch-recovery`、`--active-root-recovery-*`，或调整 180 秒、伪造 gate / heartbeat 来绕过。

### 3.3 启用后验收

- ARMED 后再检查连续 3 次 D 成功轮询与同一 F 的 2 次独立心跳；包括年龄大于 10 秒且不超过 180 秒的有效 F 证明。D/F 公开只读、实盘关闭、F 无准入阻断，保留命令、RC、完整 SHA、根、PID、F 实例和 gate/summary。
- 首次真实同页改期另验：同一 article 的可信新版正文和可得时刻、D 正式 v2 记录、payload hash、每标的新旧锚点及 F 同一 `revision_application_id` 恰好应用一次。无真实事件只标「已启用、待首例」，不注入生产测试事件。盘口能否采到仍依赖新锚点、交易所就绪和既有时窗；不接管独立延期/取消，不补采 HYPE/TRX 已过窗口。

## 4. 分阶段回退

| 阶段或信号 | 停止边界及必须保留证据 |
| --- | --- |
| 尚未停 A，任一前检失败 | 不切换、不停 A，保持 Producer 关闭。 |
| E0/E1，尚未 ARMED | 先记 B 的 SHA、RUN_ID、PID、gate/summary 及失败阶段。按授权停止已启动的候选进程并确认零写入者；没有启动的一侧不假报完成，也不杀不明 PID。冻结失败根，再用新 A 根恢复。 |
| 已 ARMED，核实尚无正式 v2 改期且无活动/待启动观察 | 完成证据采集后，先停 D（切断发射），确认退出后再停 F；如果观察已开始或状态不明，不执行计划性中断。 |
| 已发正式修订、出现 compromised，或存在活动/待启动观察 | 先冻结已发 v2 行、F registry 和应用 ID、当前及持久观察进度、watermark、gate/summary、PID/实例、SHA 和时间。保留锁存及 B 两根，不撤销、重写或重放历史。只有维护许可覆盖该次观察中断或获明确应急停止授权时才停；否则停止计划性切换并报告。紧急隔离如不能安全先采全证据，先按已授权边界停 D，记录中断，进程退出后补采根目录原件，不回填时间。 |

核对并保留 B 两根后，使用**已验证关闭版模板**的参数构造新 A 启动，不从 B 的 E2 argv 复制 F 证明参数。以下是分段回退命令，须已取得回退授权并按上表核对状态；`W` 仍指仓外证据目录。

```bash
# 分段执行。按上表授权并冻结证据后，核对当前 B 和实际进程。
test "$(g rev-parse HEAD)" = "$B"
R_D_PID=
R_F_PID=
if tmux has-session -t "=$DS" 2>/dev/null; then
  R_D_PID=$(tmux list-panes -t "=$DS" -F '#{pane_pid}')
  [[ "$R_D_PID" =~ ^[0-9]+$ ]]
  RB_D_ARGS=("${D_ARGS[@]}")
  case "${ROLLBACK_D_PHASE:?set observed E0 or E2}" in
    E0) ;;
    E2) RB_D_ARGS+=(--stage1-5f-consumer-root-contract "$F/observer_root_contract.json"
                    --stage1-5f-consumer-summary "$F/live_depth_observer_summary.json");;
    *) exit 1;;
  esac
  printf '%s\0' "$PY" "$DR" "${RB_D_ARGS[@]}" | cmp - "/proc/$R_D_PID/cmdline"
fi
if tmux has-session -t "=$FS" 2>/dev/null; then
  R_F_PID=$(tmux list-panes -t "=$FS" -F '#{pane_pid}')
  [[ "$R_F_PID" =~ ^[0-9]+$ ]]
  printf '%s\0' "$PY" "$FR" "${F_ARGS[@]}" --live-public-readonly | cmp - "/proc/$R_F_PID/cmdline"
fi
actual=$(writers)
expected=$(printf '%s\n' "$R_D_PID" "$R_F_PID" | sed '/^$/d' | sort -n)
test "$actual" = "$expected"
if [ -n "$R_D_PID" ]; then
  tmux kill-session -t "=$DS"
  STOP_D_AT=$SECONDS
  while [ -e "/proc/$R_D_PID" ]; do
    (( SECONDS - STOP_D_AT < 30 )) || { echo STOP=rollback_d_has_not_exited; exit 1; }
    sleep 2
  done
fi
actual=$(writers)
test "$actual" = "$R_F_PID"
if [ -n "$R_F_PID" ]; then
  test "$(tmux list-panes -t "=$FS" -F '#{pane_pid}')" = "$R_F_PID"
  tmux kill-session -t "=$FS"
fi
# 从停 F 起最多等待 30 秒（每 2 秒检查）；无法确认即 STOP。
for ((i=0; i<15; i++)); do
  actual=$(writers) || exit 1
  [ -z "$actual" ] && break
  sleep 2
done
test -z "$actual"
test -z "$(g status --porcelain --untracked-files=all)"
g checkout --detach "$A"
test "$(g rev-parse HEAD)" = "$A"
test -z "$(g status --porcelain --untracked-files=all)"
"$PY" -c 'from configs import base; from src.risk.limits import RiskLimits; assert base.RISK_LIVE_TRADING_ENABLED is RiskLimits.live_trading_enabled is False; assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is False'
# 使用新审批的回退 RUN_ID，检查两个新根不存在与 8 GiB 门槛。
RUN_ID=${APPROVED_ROLLBACK_RUN_ID:?missing approved rollback RUN_ID}
[[ "$RUN_ID" =~ ^[0-9]{8}T[0-9]{6}Z(_[a-zA-Z0-9_-]+)?$ ]]
bind_roots
test ! -e "$D" && test ! -L "$D" && test ! -e "$F" && test ! -L "$F"
start "$DS" "$W/A.rollback.D.log" "$PY" "$DR" "${D_ARGS[@]}"
# 等 A 的新 D READY，核验 producer_disabled 及剩余空间后才执行 F 两条。
"$PY" "$FR" "${F_ARGS[@]}" --bootstrap-watermark > "$W/A.rollback.bootstrap.log" 2>&1
start "$FS" "$W/A.rollback.F.log" "$PY" "$FR" "${F_ARGS[@]}" --live-public-readonly
```

回退完成标准：B 根和证据仍在，A 的新 D READY，`configured_enabled=false`、`effective_enabled=false`、`health=producer_disabled`；新 F 的进程/启动 SHA=A、同根 watermark 和运行证明有效，且实盘=False。记录中断时段，不自动补历史。如果 A 签出、零写入者、空间、D/F 启动或证明任何一项失败，停止并报告，不叠加进程或复用失败根。

**当前下一步：** 由 Model B 定向复核三项 P1 及相邻逻辑；在交接演练和单独授权之前，保持现有 A 的只读 D/F 和 Producer=False。
