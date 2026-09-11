# Stage 1.5D / 1.5F VPS 运维与部署操作手册 (Runbook)

- **日期:** 2026-09-03
- **状态:** `current_runbook_authority`
- **范围:** Stage 1.5D Live Announcement Collector 与 Stage 1.5F Live Depth Observer 的 VPS 实机部署、守护进程启停、日常巡检监控、单币种排障与 Stage 1.5G 离线审阅闭环
- **代码变更:** `false`
- **硬安全开关:** `RISK_LIVE_TRADING_ENABLED = false`
- **权限边界:**
  - `trade_signal_allowed = false`
  - `paper_trading_allowed = false`
  - `live_trading_allowed = false`
  - `execution_engine_allowed = false`
  - `alpha_interpretation_allowed = false`
  - `execution_feasibility_claim_allowed = false`
- **相关权威文档:**
  - 研发总路线图: [docs/roadmap.md](../roadmap.md)
  - 1.5F 核心设计: [docs/designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md](../designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md)
  - 1.5D V3 状态机设计: [docs/designs/2026-09-01-external-signal-shadow-lab-stage1-5d-historical-catalog-re-admission-hotfix-design_CN.md](../designs/2026-09-01-external-signal-shadow-lab-stage1-5d-historical-catalog-re-admission-hotfix-design_CN.md)
  - 历史审查底表: [docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md](../reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md)

---

## 1. 权限与安全铁律

1. **观察优先与只读铁律 (Observation-Only)**：
   本系统运行严格处于无交易、无信号的影子观察模式。严禁在生产 VPS 上配置任何私有 API Key、下单端点或执行引擎插件。
2. **历史证据目录不可篡改铁律 (Immutable Historical Roots)**：
   严禁对历史已生成的 output root 执行覆盖写入、删除、重命名或 `--resume` 复用。任何代码升级、热修复或重启，**必须分配全新的 `RUN_ID` 创建全新根目录**。
3. **单向事件消费契约 (Strict Event-Driven Chain)**：
   `Stage 1.5D` 为官方公告与详情事件的独占生产者（Producer）；`Stage 1.5F` 为独占深度观测消费者（Consumer）。1.5F 启动前必须验证 1.5D 的 `live_safety_gate_summary.json` 处于 `READY` 状态，并且通过 Watermark 严格隔离启动前的历史存量事件。
4. **子进程与环境纯净原则**：
   生产命令均设计在无副作用的子进程块中执行。所有命令块假定工作目录为 `/root/crypto-alpha-lab`，并已激活 `.venv/bin/activate`。

---

## 2. 基础环境与全局变量规范

每次登录 VPS（`root@47.82.4.85`）或开启新的 SSH 窗口时，必须先设置基础环境变量模板：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 1. 统一的版本后缀定义（当前默认升级至 V3 热修复后缀）
export ROOT_SUFFIX="${ROOT_SUFFIX:-7d_historical_catalog_re_admission_hotfix_v3}"

# 2. 统一的 tmux 会话名
export STAGE1_5D_SESSION="stage1_5d_continuous_${ROOT_SUFFIX}"
export STAGE1_5F_SESSION="stage1_5f_live_depth_${ROOT_SUFFIX}"

# 3. 统一的新 Run ID (用于全新启动时)
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"

# 4. 依赖文件与输出目录路径模板
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"
export STAGE1_5D_EVENTS_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_${RUN_ID}_${ROOT_SUFFIX}"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_${RUN_ID}_${ROOT_SUFFIX}"
```

> [!WARNING]
> **历史只读根目录保护**：以下历史 root 仅作历史回溯与只读参考，严禁在任何脚本中将它们重定向为写入目标：
> - `..._7d` / `..._7d_empty_detail_retry_hotfix`
> - `..._7d_title_contract_transient_hotfix`
> - `..._7d_detail_retry_scheduler_starvation_hotfix`
> - `..._7d_storage_lifecycle_resource_guard_hotfix`
> - `..._7d_formal_v2_anchor_source_lineage_projection_hotfix`

---

## 3. 部署前门禁与代码同步

在 VPS 上执行代码更新前，必须验证本地与远端 Git 状态的一致性与工作树纯净性。

### 3.1 本地提交与远端推送检查（在本地工作站）

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

# 1. 检查本地工作树必须干净
git status --short --untracked-files=all

# 2. 运行核心回归测试门禁
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py

# 3. 记录准备部署的目标 Commit SHA
export DEPLOY_COMMIT="$(git rev-parse HEAD)"
echo "DEPLOY_COMMIT=$DEPLOY_COMMIT"
git push origin feature/external-signal-shadow-stage1
```

### 3.2 服务器工作树与环境验证（在 VPS 上）

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 检查当前服务器工作树纯净度（禁止存在未提交代码或未追踪临时文件）
git status --short --untracked-files=all

# 校验基础安全开关与核心模块导入
PYTHONPATH=src:. .venv/bin/python -c '
from configs import base
from src.risk.limits import RiskLimits
assert base.RISK_LIVE_TRADING_ENABLED is False
assert RiskLimits.live_trading_enabled is False
print("VPS_ENVIRONMENT_SECURITY_GATE: PASS")
'
BASH
```

### 3.3 Zero-Writer /proc 检查器定义

在签出代码前，必须通过精确的 `/proc/<pid>/cwd` 与 `/proc/<pid>/cmdline` 分析，严格确认目标目录无遗留写入进程。

<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_BEGIN -->
```python
from pathlib import Path
import sys


def inspect_writers(
    proc_root: Path, target_root: Path
) -> list[dict[str, object]]:
  """Inspect proc_root (/proc/<pid>/cwd and /proc/<pid>/cmdline) for running writers in target_root.

  A writer matches only when cwd resolves to target_root and argv contains either
  exact resolved path:
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
  """
  target_resolved = target_root.resolve()
  target_scripts = {
      target_resolved
      / "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py",
      target_resolved
      / "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py",
  }
  matches: list[dict[str, object]] = []

  if not proc_root.is_dir():
    raise RuntimeError(f"proc root not found: {proc_root}")

  for entry in sorted(proc_root.iterdir()):
    if not entry.is_dir() or not entry.name.isdigit():
      continue
    pid = int(entry.name)
    cwd_link = entry / "cwd"
    cmdline_file = entry / "cmdline"

    try:
      cwd = cwd_link.resolve()
      if not cwd_link.exists():
        raise FileNotFoundError(f"cwd link missing or broken: {cwd_link}")
    except Exception as exc:
      raise RuntimeError(f"Failed to inspect /proc/{pid}/cwd: {exc}") from exc

    try:
      raw_cmdline = cmdline_file.read_bytes()
    except Exception as exc:
      raise RuntimeError(
          f"Failed to inspect /proc/{pid}/cmdline: {exc}"
      ) from exc

    if not raw_cmdline:
      continue
    argv = [
        arg.decode("utf-8", errors="replace")
        for arg in raw_cmdline.split(b"\x00")
        if arg
    ]
    if not argv or cwd != target_resolved:
      continue

    matched_script = None
    for arg in argv:
      if not arg:
        continue
      arg_path = Path(arg)
      resolved_script = (
          (cwd / arg_path).resolve()
          if not arg_path.is_absolute()
          else arg_path.resolve()
      )
      if resolved_script in target_scripts:
        matched_script = str(resolved_script)
        break

    if matched_script is not None:
      match_entry: dict[str, object] = {
          "pid": pid,
          "cwd": str(cwd),
          "argv": argv,
          "script": matched_script,
      }
      matches.append(match_entry)
      print(
          f"MATCHING_WRITER: pid={pid} cwd={cwd} script={matched_script}"
          f" argv={argv}",
          file=sys.stderr,
      )

  return matches


if __name__ == "__main__":
  target = (
      Path(sys.argv[1]).resolve()
      if len(sys.argv) > 1
      else Path("/root/crypto-alpha-lab").resolve()
  )
  writers = inspect_writers(Path("/proc"), target)
  if writers:
    print(f"WRITERS_RUNNING={len(writers)}")
    sys.exit(len(writers))
  print("ZERO_WRITERS_RUNNING=0")
  sys.exit(0)
```
<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_END -->

### 3.4 优雅停止旧会话、Zero-Writer 门禁与代码签出 (原子部署块)

本节将停止旧会话、30秒超时零写入者门禁核验与代码拉取签出合并为一个严格原子化的部署门禁脚本块：

<!-- STAGE1_5D_1_5F_ZERO_WRITER_DEPLOYMENT_BEGIN -->
```bash
set -euo pipefail
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 1. Request D/F tmux stop
tmux kill-session -t "$STAGE1_5F_SESSION" 2>/dev/null || true
tmux kill-session -t "$STAGE1_5D_SESSION" 2>/dev/null || true

# 2. Inspect once per second for at most 30 seconds
INSPECT_ATTEMPTS=0
ZERO_WRITER_CONFIRMED=false

while [ "$INSPECT_ATTEMPTS" -lt 30 ]; do
  ACTIVE_COUNT=$(python3 - <<'PY_INSPECT'
from pathlib import Path
runbook = Path("docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md").read_text(encoding="utf-8")
begin = "<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_BEGIN -->"
end = "<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_END -->"
code = runbook[runbook.index(begin) + len(begin):runbook.index(end)].replace("```python", "").replace("```", "")
ns = {}
exec(compile(code, "inspector", "exec"), ns)
writers = ns["inspect_writers"](Path("/proc"), Path("/root/crypto-alpha-lab"))
print(len(writers))
PY_INSPECT
  )
  if [ "$ACTIVE_COUNT" -eq 0 ]; then
    ZERO_WRITER_CONFIRMED=true
    break
  fi
  INSPECT_ATTEMPTS=$((INSPECT_ATTEMPTS + 1))
  sleep 1
done

# 3. Final exact count == 0 check
if [ "$ZERO_WRITER_CONFIRMED" != "true" ]; then
  echo "STOP=stage1_5d_1_5f_writer_still_running" >&2
  exit 1
fi

echo "ZERO_WRITER_CONFIRMED: exact writer count == 0"

# 4. Pull latest code & checkout target commit
git fetch origin feature/external-signal-shadow-stage1
git checkout "$DEPLOY_COMMIT"

# 5. Assert HEAD == DEPLOY_COMMIT, clean protected worktree, new RUN_ID and fresh roots
test "$(git rev-parse HEAD)" = "$DEPLOY_COMMIT"
test -z "$(git status --short --untracked-files=all)"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export STAGE1_5D_EVENTS_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_${RUN_ID}_${ROOT_SUFFIX}"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_${RUN_ID}_${ROOT_SUFFIX}"
test ! -e "$STAGE1_5D_EVENTS_OUT"
test ! -e "$STAGE1_5F_OUT"
echo "DEPLOYMENT_AND_ZERO_WRITER_GATE_PASSED: HEAD=$DEPLOY_COMMIT RUN_ID=$RUN_ID"
```
<!-- STAGE1_5D_1_5F_ZERO_WRITER_DEPLOYMENT_END -->

---

## 4. 标准启动流程 (全新 Root 部署)

全新 Root 部署适用于大版本发布、严重阻断性缺陷修复，或经批准的计划性重置。

在日常 VPS 运维中，系统运行于 producer-disabled 影子模式。若未来经单独授权开启 `configured_enabled=true`，必须严格保留父级规范中的三阶段启动证明链（E0 -> E1 -> E2）：
- **E0 (Bootstrap Waiting for Consumer)**: 1.5D 启动，校验静态证明与 Git Ancestry，因尚未配置 1.5F 报告 `BOOTSTRAP_WAITING_FOR_CONSUMER`；
- **E1 (Consumer Proof Arming)**: 1.5F 在同 output root 和同 HEAD 提交下启动，发布 `observer_root_contract.json` 与 `live_depth_observer_summary.json`；
- **E2 (Restart & Sticky Latch Protection)**: 1.5D 在同 output root 下重启并正式 arm producer，开启 sticky compromised 保护。
严禁将上述流程简化为无验证的单向 D -> F 启动。

### 4.1 确认后台无旧写入者 (Zero-Writer 门禁核验)

在 3.4 节原子部署块中，已通过 `/proc` 检查器与 30 秒超时门禁完成旧会话的优雅停止与零写入者核验。若执行非部署的普通服务重启，可执行以下命令快速核验当前零写入者状态：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 确认所有后台 Python 写入进程已彻底退出 (输出必须为 0)
python3 - <<'PY'
from pathlib import Path
runbook = Path("docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md").read_text(encoding="utf-8")
b = "<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_BEGIN -->"
e = "<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_END -->"
code = runbook[runbook.index(b) + len(b):runbook.index(e)].replace("```python", "").replace("```", "")
ns = {}
exec(compile(code, "inspector", "exec"), ns)
writers = ns["inspect_writers"](Path("/proc"), Path("/root/crypto-alpha-lab"))
assert len(writers) == 0, f"STOP: {len(writers)} writer(s) still active!"
print("ZERO_WRITER_VERIFIED")
PY
```

### 4.2 启动 Stage 1.5D Collector

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 检查宿主机剩余存储空间
df -hT /

# 验证 output-root 不存在，防止意外复用
test ! -e "$STAGE1_5D_EVENTS_OUT" || { echo "STOP: Root already exists: $STAGE1_5D_EVENTS_OUT"; exit 1; }

# 启动 1.5D tmux 会话
tmux new-session -d -s "$STAGE1_5D_SESSION" "
cd /root/crypto-alpha-lab &&
source .venv/bin/activate &&
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \\
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \\
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \\
  --output-root '$STAGE1_5D_EVENTS_OUT' \\
  --output-summary '$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json' \\
  --poll-interval-sec 60 \\
  --max-seconds 604800 \\
  --live-public-readonly
"

echo "STAGE1_5D_STARTED: root=$STAGE1_5D_EVENTS_OUT session=$STAGE1_5D_SESSION"
```

等待 130 秒（至少完成 2 轮 poll）后，验证 1.5D Runtime Gate 达到 `READY` 状态：

```bash
sleep 130
python3 - "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" <<'PY'
import json, sys
from pathlib import Path

p = Path(sys.argv[1])
assert p.is_file(), f"STOP: Missing runtime gate summary: {p}"
g = json.loads(p.read_text())

print({
    "status": g.get("status"),
    "decision": g.get("decision"),
    "consumable_by_stage1_5f": g.get("consumable_by_stage1_5f"),
    "successful_polls": g.get("successful_poll_count"),
    "storage_guard": g.get("storage_guard_status")
})

assert g.get("status") == "READY"
assert g.get("decision") == "stage1_5d_runtime_gate_ready"
assert g.get("consumable_by_stage1_5f") is True
assert g.get("storage_guard_status") == "ready"
assert g.get("storage_blocker") is None
print("STAGE1_5D_GATE: PASS")
PY
```

验证 V3 状态模式（针对 V3 热修复架构）：

```bash
python3 - "$STAGE1_5D_EVENTS_OUT/detail_retry_scheduler_state.json" <<'PY'
import json, sys
from pathlib import Path

p = Path(sys.argv[1])
state = json.loads(p.read_text(encoding="utf-8"))
assert state.get("metadata_version") == 3, f"Expected V3, got: {state.get('metadata_version')}"
cutoff = state.get("catalog_bootstrap_cutoff_ms")
assert isinstance(cutoff, int) and cutoff > 0, f"Invalid cutoff: {cutoff}"
print(f"STAGE1_5D_V3_STATE: PASS (cutoff={cutoff})")
PY
```

### 4.3 Bootstrap 并启动 Stage 1.5F Observer

仅在 1.5D 验证通过后启动 1.5F：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 验证前置依赖文件存在
test -f "$STAGE1_5E_SUMMARY" || { echo "STOP: Missing $STAGE1_5E_SUMMARY"; exit 1; }
test ! -e "$STAGE1_5F_OUT" || { echo "STOP: Root already exists: $STAGE1_5F_OUT"; exit 1; }

# Step 1: 执行无损 Bootstrap (建立新水位线，不抓旧事件，兼容空 events 目录)
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob "$STAGE1_5D_EVENTS_OUT/events/*.jsonl" \
  --stage1-5d-runtime-gate "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" \
  --stage1-5e-summary "$STAGE1_5E_SUMMARY" \
  --output-root "$STAGE1_5F_OUT" \
  --bootstrap-watermark

# 验证水位线建立成功
test -f "$STAGE1_5F_OUT/watermark.json" && echo "STAGE1_5F_BOOTSTRAP_WATERMARK: PASS"

# Step 2: 启动 1.5F tmux 观察会话
# 注意：--stage1-5d-events-glob 必须直接传入未带反斜杠的通配符单引号字符串
tmux new-session -d -s "$STAGE1_5F_SESSION" "
cd /root/crypto-alpha-lab &&
source .venv/bin/activate &&
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \\
  --stage1-5d-events-glob '$STAGE1_5D_EVENTS_OUT/events/*.jsonl' \\
  --stage1-5d-runtime-gate '$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json' \\
  --stage1-5e-summary '$STAGE1_5E_SUMMARY' \\
  --output-root '$STAGE1_5F_OUT' \\
  --live-public-readonly
"

echo "STAGE1_5F_STARTED: root=$STAGE1_5F_OUT session=$STAGE1_5F_SESSION"
```

### 4.4 首次部署绑定核验

等待 90 秒后执行双端握手核验：

```bash
sleep 90
python3 - "$STAGE1_5D_EVENTS_OUT" "$STAGE1_5F_OUT" <<'PY'
import hashlib, json, sys
from pathlib import Path

root_d = Path(sys.argv[1]).resolve()
root_f = Path(sys.argv[2]).resolve()
gate = json.loads((root_d / "live_safety_gate_summary.json").read_text())
contract = json.loads((root_f / "observer_root_contract.json").read_text())
summary = json.loads((root_f / "live_depth_observer_summary.json").read_text())
expected_d_id = hashlib.sha256(str(root_d).encode()).hexdigest()

assert gate.get("status") == "READY", "1.5D gate is not READY"
assert contract.get("source_stage1_5d_output_root_id") == expected_d_id, "Root binding mismatch!"
assert contract.get("consumer_static_attestation_verified") is True, "Static attestation failed"
assert summary.get("consumer_runtime_attestation_verified") is True, "Runtime attestation failed"
assert summary.get("consumer_runtime_attestation_compromised") is False, "Attestation compromised!"
assert summary.get("block_new_event_admission") is False, "New event admission blocked"
assert summary.get("storage_guard_status") == "ready", "Storage guard not ready"
print("STAGE1_5D_5F_INITIAL_HANDSHAKE: FULLY_VERIFIED_PASS")
PY
```

---

## 5. 日常监控与巡检

### 5.1 快速定位当前活跃 Root 路径

在日常巡检登录时，优先从运行中的系统进程自动探测当前活跃根目录：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(ps -eo comm=,args= | awk '$1 ~ /^python/ && /run_stage1_5d_live_event_source_smoke_collector.py/ {for (i = 1; i <= NF; i++) if ($i == "--output-root") print $(i + 1)}' | tail -n 1)"
export STAGE1_5F_OUT="$(ps -eo comm=,args= | awk '$1 ~ /^python/ && /run_stage1_5f_live_depth_observer.py/ {for (i = 1; i <= NF; i++) if ($i == "--output-root") print $(i + 1)}' | tail -n 1)"

# 如果无正在运行的进程，则回退查找同后缀最新目录
if [ -z "$STAGE1_5D_EVENTS_OUT" ]; then
  export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name "live_event_source_continuous_*_${ROOT_SUFFIX}" | sort | tail -n 1)"
fi
if [ -z "$STAGE1_5F_OUT" ]; then
  export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name "live_depth_observer_*_${ROOT_SUFFIX}" | sort | tail -n 1)"
fi

echo "ACTIVE_1.5D_ROOT=[$STAGE1_5D_EVENTS_OUT]"
echo "ACTIVE_1.5F_ROOT=[$STAGE1_5F_OUT]"
```

### 5.2 “一条命令看健康状态” (One-Command Health Dashboard)

无需分别查找各 JSON，直接运行整合脚本获取核心状态快照：

```bash
python3 - "$STAGE1_5D_EVENTS_OUT" "$STAGE1_5F_OUT" <<'PY'
import json, sys
from pathlib import Path

def load(root, name):
    p = Path(root) / name if root else Path("missing")
    return json.loads(p.read_text()) if p.is_file() else {"missing": str(p)}

g = load(sys.argv[1], "live_safety_gate_summary.json")
s = load(sys.argv[2], "live_depth_observer_summary.json")

print("=== STAGE 1.5D STATUS ===")
print(f"Status: {g.get('status')} | Decision: {g.get('decision')} | 5F-Consumable: {g.get('consumable_by_stage1_5f')}")
print(f"Polls: Success={g.get('successful_poll_count')} / Failed={g.get('failed_poll_count')} (Consecutive Fail={g.get('consecutive_failed_polls')})")
print(f"Storage: Guard={g.get('storage_guard_status')} | Used={g.get('storage_root_bytes')}B | Max={g.get('storage_root_max_bytes')}B")

print("\n=== STAGE 1.5F STATUS ===")
print(f"Decision: {s.get('decision')} | Admission Blocked: {s.get('block_new_event_admission')}")
print(f"Events: Accepted={s.get('post_watermark_events_accepted')} | Active Obs={s.get('active_observation_count')} | Completed={s.get('completed_observation_count')}")
print(f"Pending: Launch-Time={s.get('pending_launch_observation_count')} | Capacity={s.get('pending_observation_capacity_count')}")
print(f"Storage: Guard={s.get('storage_guard_status')} | Used={s.get('storage_root_bytes')}B | Max={s.get('storage_root_max_bytes')}B")

d_ok = (g.get("status") == "READY" and g.get("consecutive_failed_polls", 0) == 0 and g.get("storage_guard_status") == "ready")
f_ok = (s.get("block_new_event_admission") is False and s.get("storage_guard_status") == "ready" and s.get("blocker") is None)

print(f"\nOVERALL HEALTH CHECK: {'[PASS]' if (d_ok and f_ok) else '[ALERT_ACTION_REQUIRED]'}")
PY
```

### 5.3 校验事件流与 Root 绑定完整性

确认 1.5D 产生的文件被 1.5F 正确感知：

```bash
python3 - "$STAGE1_5D_EVENTS_OUT" "$STAGE1_5F_OUT" <<'PY'
import glob, hashlib, json, sys
from pathlib import Path

root_d = Path(sys.argv[1]).resolve()
root_f = Path(sys.argv[2]).resolve()
events = sorted(glob.glob(str(root_d / "events" / "*.jsonl")))
contract = json.loads((root_f / "observer_root_contract.json").read_text())
root_id = hashlib.sha256(str(root_d).encode()).hexdigest()

keys = ("source_stage1_5d_output_root_id", "source_stage1_5d_events_root_id", "source_stage1_5d_runtime_gate_root_id")
binding_ok = all(contract.get(k) == root_id for k in keys)

print({
    "1.5D_events_file_count": len(events),
    "1.5D_events_tail": [Path(e).name for e in events[-3:]],
    "1.5F_binding_ok": binding_ok,
})
assert binding_ok, "CRITICAL: 1.5F is bound to an incorrect 1.5D root!"
PY
```

### 5.4 优雅停止当前会话

当需要进行系统维护、代码重启或滚动切割时执行：

```bash
# 1. 检查是否有正在采集中 (Active Observation) 的事件
python3 - "$STAGE1_5F_OUT/live_depth_observer_summary.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
active = s.get("active_observation_count", 0)
if active > 0:
    print(f"WARNING: There are {active} active observations in progress! Stopping now will interrupt 12h sampling.")
else:
    print("Zero active observations. Safe to stop.")
PY

# 2. 杀掉 tmux 会话
tmux kill-session -t "$STAGE1_5F_SESSION" 2>/dev/null || true
tmux kill-session -t "$STAGE1_5D_SESSION" 2>/dev/null || true

# 3. 确认进程退出
ps -eo pid=,ppid=,comm=,args= | awk '$3 ~ /^python/ && (/run_stage1_5d_live_event_source_smoke_collector.py/ || /run_stage1_5f_live_depth_observer.py/)' || true
```

---

## 6. 常见排障与链路追踪

### 6.1 查看 1.5F 当前有效 Watermark 时间

```bash
python3 - "$STAGE1_5F_OUT/watermark.json" <<'PY'
import json, sys
from datetime import datetime, timezone

w = json.load(open(sys.argv[1]))
max_seen = w.get("max_seen_detected_at_ms", 0)
dt = datetime.fromtimestamp(max_seen / 1000, tz=timezone.utc).isoformat() if max_seen else "None"
print({
    "watermark_schema_version": w.get("watermark_schema_version"),
    "bootstrap_root_id": w.get("bootstrap_root_id"),
    "max_seen_detected_at_ms": max_seen,
    "max_seen_detected_at_utc": dt,
})
PY
```

### 6.2 按交易对 Symbol 或 Article ID 追踪端到端链路

当发现某个特定新币公告没有进入深度观测时，通过以下脚本一键排查其在 1.5D 和 1.5F 中的流转归宿：

```bash
export QUERY_KEY="POPMART"  # 支持输入 symbol (如 POPMARTUSDT) 或 article_id

python3 - "$STAGE1_5D_EVENTS_OUT" "$STAGE1_5F_OUT" "$QUERY_KEY" <<'PY'
import glob, json, os, sys
from pathlib import Path

root_d = Path(sys.argv[1])
root_f = Path(sys.argv[2])
query = sys.argv[3].upper()

print(f"=== SEARCHING FOR QUERY: [{query}] ===")

# 1. 检查 1.5D events/*.jsonl
found_events = []
for f in glob.glob(str(root_d / "events" / "*.jsonl")):
    for line in open(f):
        if query in line:
            found_events.append(json.loads(line))
print(f"1.5D Formally Emitted Events: {len(found_events)}")
for e in found_events:
    print(f"  -> event_id={e.get('event_id')} symbols={e.get('symbols')} detected_at_ms={e.get('detected_at_ms')}")

# 2. 检查 1.5D events_rejected/*.jsonl
rejected_d = []
for f in glob.glob(str(root_d / "events_rejected" / "*.jsonl")):
    for line in open(f):
        if query in line:
            rejected_d.append(json.loads(line))
print(f"1.5D Rejected Events: {len(rejected_d)}")
for r in rejected_d:
    print(f"  -> reason={r.get('rejected_reason')} article_id={r.get('source_article_id')}")

# 3. 检查 1.5F observer_state.jsonl
f_states = []
p_state = root_f / "observer_state.jsonl"
if p_state.is_file():
    for line in open(p_state):
        if query in line:
            f_states.append(json.loads(line))
print(f"1.5F Observer State Rows: {len(f_states)}")
for s in f_states[-3:]:  # 打印最新的 3 条状态变更
    print(f"  -> symbol={s.get('symbol')} status={s.get('status')} pending_reason={s.get('pending_reason')} rejected_reason={s.get('rejected_reason')}")

# 4. 检查 1.5F 盘口快照文件
snapshots = glob.glob(str(root_f / "depth_snapshots" / f"*{query}*"))
print(f"1.5F L2 Depth Snapshot Directories: {len(snapshots)}")
for snap in snapshots:
    print(f"  -> {Path(snap).name}")
PY
```

### 6.3 常见故障判读与处置手册

| 异常现象 | 核心根因 | 处置 SOP |
|:---|:---|:---|
| 1.5D `consecutive_failed_polls > 3` | 币安公告网络接口受阻或解析异常 | 检查 VPS 网络出口；查看 `1.5D/live_event_source_smoke_collector.log`，不得强行删除数据。 |
| 1.5F `block_new_event_admission = true` | 1.5D Gate 变为 `DEGRADED` 或存储超标 | 执行 5.2 节检查 `storage_guard`；确认磁盘是否有意外膨胀，检查 1.5D 是否因调度器饥饿被挂起。 |
| 1.5F 报 `pending_anchor_conflict` | 官方计划时间与 ExchangeInfo 上线时间冲突 | V2 契约下应优先采信 Official Schedule；若发生阻断需核对是否使用了正确的 V2 镜像。 |
| 新公告显示 `ignored_historical_anchor_pre_bootstrap` | 该公告发布于 Watermark 建立之前 | **正常现象**。系统设计严格拒绝采集历史存量公告，仅记录 Tombstone 且不进入 1.5F 盘口收集。 |

---

## 7. 事件后审计：Stage 1.5G 触发式离线审阅 SOP

### 7.1 触发时机与运行原则

- **触发条件**：日常巡检（5.2节）发现 1.5F 的 `completed_observation_count > 0`，且某个标的的 12 小时 L2 深度盘口采集已自然闭环结束。
- **架构原则（VPS 只读采集，本地离线计算）**：
  **严禁直接在生产 VPS 上运行 Stage 1.5G 审阅脚本**。VPS 仅用于盘口数据产生与网络传输；所有 1.5G 证据审计与合规判定必须在**本地研究工作站**离线执行。

### 7.2 本地执行 SOP

在本地开发机执行以下同步与审阅命令：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
source .venv/bin/activate

# 1. 目标服务器与路径设置
export SERVER="root@47.82.4.85"
export REMOTE_STAGE1_5F_OUT="/root/crypto-alpha-lab/替换为VPS上已完成的live_depth_observer目录"

# 2. 本地工作站归档路径定义
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export LOCAL_EVIDENCE_ROOT="$PWD/data/external_signal_shadow/local_evidence/${RUN_ID}_stage1_5f"
export STAGE1_5G_OUT="$PWD/data/external_signal_shadow/stage1_5g/reviews/${RUN_ID}_local_v2"

# 3. 将完整的 1.5F 产物安全传输至本地 (受 2GiB 存储守卫保护，安全可传输)
mkdir -p "$LOCAL_EVIDENCE_ROOT"
rsync -aP --partial "$SERVER:$REMOTE_STAGE1_5F_OUT/" "$LOCAL_EVIDENCE_ROOT/"

# 4. 生成本地防篡改 SHA256 校验清单
find "$LOCAL_EVIDENCE_ROOT" -type f -exec shasum -a 256 {} \; | sort > "$LOCAL_EVIDENCE_ROOT/SHA256SUMS"
test ! -e "$STAGE1_5G_OUT" || { echo "STOP: review output root already exists: $STAGE1_5G_OUT" >&2; exit 1; }

# 5. 执行 Stage 1.5G 离线深度证据审计
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  --stage1-5f-output-root "$LOCAL_EVIDENCE_ROOT" \
  --output-root "$STAGE1_5G_OUT" \
  --output-summary "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review_summary.json" \
  --output-review "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review.md"

echo "STAGE1_5G_REVIEW_COMPLETED: $STAGE1_5G_OUT"
```

### 7.3 审阅判定解读

审查生成的 `stage1_5g_live_depth_evidence_review_summary.json` 中的 `decision`：

```text
1. stage1_5g_depth_evidence_clean_pass (Clean Pass):
   -> 盘口完全连续、深度健康、极性正确，无任何无效订单簿行。
   -> 允许进入 Stage 1.5H 报告生成与 Shadow 仿真器设计。
   
2. stage1_5g_depth_evidence_quarantined_pass (Quarantine Pass):
   -> 存在轻微非致命跳变或孤立坏行，但整体可用率满足阈值。
   -> 仅允许用于 Stage 1.5H 静态评估，严禁直接声称执行可行性。

3. stage1_5g_depth_evidence_invalid (Invalid Failure):
   -> 盘口严重缺失、时间倒挂或数据污染。样本作废，继续保持观察。
```

---

## 8. 下游数据流向与 Stage 1.5H 研报边界

1. **本地证据库沉淀**：
   通过 1.5G 验证的样本（如历史样本 `SPCXUSD1`、`SKHYUSDT`）将永久保留在 `data/external_signal_shadow/stage1_5g/reviews/` 目录下，作为多标的横截面样本集。
2. **Stage 1.5H 静态研报角色**：
   Stage 1.5H（`run_stage1_5h_static_execution_proxy_report.py`）专用于对通过 1.5G 审计的样本生成多标的隔离点差与滑点摩擦评估报告。
3. **严禁越权操作**：
   无论是 1.5G 还是 1.5H，均**绝对禁止**推出实盘成交可行性、Alpha 收益预测或自动化下单交易的结论。具体研报操作请参阅治理规范：
   [docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md](../reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md)。

---

## 附录：V3 历史目录重入切断特权操作 (V3 Cutover Quick Reference)

当从历史 V2 调度器状态（`metadata_version=2`）升级至 V3 模式时，需特别注意：
1. **彻底拒绝历史复用**：V3 引入了 86 字段状态校验与强闭树检查，旧 root 不支持原地 upgrade，必须启全新 output root。
2. **Cutoff 冻结确认**：启动 1.5D 后必须看到 `catalog_bootstrap_cutoff_ms` 成功落盘（见 4.2 节验证代码）。
3. **存量历史事件隔离**：历史公告（如 POPMART、UNITREE 等）会被自动转为不可恢复的 Tombstone 墓碑，杜绝后台重试队列饥饿。
