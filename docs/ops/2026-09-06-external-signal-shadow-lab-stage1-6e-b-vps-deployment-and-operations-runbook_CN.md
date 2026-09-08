# Stage 1.6E-B VPS 影子观测部署与运行操作手册 (Deployment & Operations Runbook)

- **日期:** 2026-09-06
- **状态:** `current_runbook_authority`
- **范围:** Stage 1.6E-B Binance USD-M 下架公告实时语义触发与事件级行情观察器的 VPS 实机部署、现场预检、试运行与常驻运维手册
- **代码变更:** `false`（本手册为操作指导文档，不修改任何业务代码）
- **硬安全开关:** `RISK_LIVE_TRADING_ENABLED = false`
- **绑定的已审核部署 Commit:** `854916fd531cbd61a166d81d46107e2cbfc2acb9`
- **权限边界:**
  - `RISK_LIVE_TRADING_ENABLED = false`
  - `execution_feasibility_claim_allowed = false`
  - `net_cost_or_profit_claim_allowed = false`
  - `replay_allowed = false`
  - `paper_trading_allowed = false`
  - `live_trading_allowed = false`
  - `execution_engine_allowed = false`
  - `trade_signal_allowed = false`
  - `arbitrage_claim_allowed = false`
  - `maker_cycle_claim_allowed = false`
  - `alpha_claim_allowed = false`
  - `external_fill_claim_allowed = false`
- **权威设计来源:**
  - 核心设计: [docs/designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md](../designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md)
  - 修复设计: [docs/designs/2026-09-04-external-signal-shadow-lab-stage1-6e-b-completion-remediation-delta-design_CN.md](../designs/2026-09-04-external-signal-shadow-lab-stage1-6e-b-completion-remediation-delta-design_CN.md)
  - 实施计划: [docs/plans/2026-09-06-external-signal-shadow-lab-stage1-6e-b-profilecore-provenance-and-raw-cap-remediation-implementation-plan_CN.md](../plans/2026-09-06-external-signal-shadow-lab-stage1-6e-b-profilecore-provenance-and-raw-cap-remediation-implementation-plan_CN.md)
  - 语法收紧计划: [docs/plans/2026-09-07-external-signal-shadow-lab-stage1-6e-b-source-run-id-grammar-remediation-implementation-plan_CN.md](../plans/2026-09-07-external-signal-shadow-lab-stage1-6e-b-source-run-id-grammar-remediation-implementation-plan_CN.md)
  - 独立审计: 审计裁决 `complete`（无 P0/P1/P2 发现）

---

## 1. 权限与生产安全铁律 (Authority & Invariants)

1. **绝对只读影子观察铁律 (Observation-Only Invariant)**：
   本系统运行严格处于无交易权限的只读影子观察模式。严禁在生产 VPS 环境变量或代码中注入交易所 API Key/Secret。所有向 Binance 派发的网络请求均为公开 REST 行情接口（GET 方法），绝无下单行为。
2. **零容忍硬编码与逃逸后门 (Zero-Bypass Invariant)**：
   严禁使用任何测试逃逸开关（已在代码中彻底删除）。VPS 上的执行环境指纹必须严格由本机的 `/etc/machine-id` 实时生成，与上游 1.6E-A 留存指纹 100% 匹配。
3. **日志与数据存储物理隔离 (Log-Storage Separation)**：
   标准输出/标准错误日志**严禁重定向至 supervisor_root 或 events 目录内**。日志必须写入专用的独立日志目录，防止日志体积膨胀被 StorageGuard 计入事件存储预算。
4. **Fail-Closed 故障自闭原则**：
   若上游公告源中断、磁盘空间不足、E-A 凭证哈希不匹配，观察器必须拒绝派发网络请求并安全退出，绝不允许使用伪造数据或默认配置继续运行。

---

## 2. 基础环境与全局变量规范 (Global Specifications)

每次登录目标 VPS（`root@47.82.4.85`）后，在执行操作前，必须先在终端中声明并导出以下环境变量：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 1. 固化的部署 Commit SHA (不可篡改)
export DEPLOY_COMMIT="854916fd531cbd61a166d81d46107e2cbfc2acb9"

# 2. 上游 1.6E-A 官方审计封签根目录 (已在 2026-09-03 实机验证封存)
export E_A_ROOT="/root/crypto-alpha-lab/data/external_signal_shadow/stage1_6e/capability_audits/stage1_6e_a_capability_20260903T073227Z_c431d5be400aabe216f15c6bf6bee48f"

# 3. Stage 1.6E-B 专用输出目录规划
export E_B_SUPERVISOR_ROOT="/root/crypto-alpha-lab/data/external_signal_shadow/stage1_6e_b/supervisor"
export E_B_EVENTS_ROOT="/root/crypto-alpha-lab/data/external_signal_shadow/stage1_6e_b/events"
export SHARED_STORAGE_LOCK="/root/crypto-alpha-lab/data/external_signal_shadow/.stage1_5_storage_guard.lock"

# 4. 日志目录与 Tmux 会话名
export E_B_LOG_DIR="/root/crypto-alpha-lab/logs/stage1_6e_b"
export E_B_TMUX_SESSION="stage1_6e_b_live_semantic_observer"
```

---

## 3. 三步实施操作流程 (Step-by-Step Runbook)

### 步骤 1：本地与远程代码同步与纯净性验证 (Code Sync & Worktree Cleanliness)

#### 1.1 本地工作站推送检查（在本地开发机执行）
确认本地代码已提交且无残留修改：
```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

# 确认工作区完全干净
git status --short --untracked-files=all

# 确认当前 HEAD SHA
test "$(git rev-parse HEAD)" = "854916fd531cbd61a166d81d46107e2cbfc2acb9" && echo "Local Commit Verified: PASS"

# 推送代码至远程仓库 (根据当前跟踪分支执行 push)
git push
```

#### 1.2 VPS 远端拉取与工作树核验（在 VPS 终端执行）
登录 VPS，拉取最新代码并验证：
```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 1. 拉取代码
git fetch --all
git checkout 854916fd531cbd61a166d81d46107e2cbfc2acb9

# 2. 检查工作树纯净性 (禁止任何 dirty 或 untracked 业务文件)
test -z "$(git status --short --untracked-files=all)" || {
    echo "STOP: VPS worktree is dirty!" >&2
    git status --short
    exit 1
}

# 3. 运行核心模块快速自检
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py

# 4. 检查金融安全开关必须为 False
python3 -c "from configs import base; from src.risk.limits import RiskLimits; assert base.RISK_LIVE_TRADING_ENABLED is False; assert RiskLimits().live_trading_enabled is False"

echo "=== STEP 1 VERIFIED: Codebase clean and tests passing on VPS ==="
BASH
```

---

### 步骤 2：VPS 现场上游依赖与环境预检 (VPS Preflight Inspection)

在 VPS 终端中运行以下一键预检脚本。脚本将自动检查上游 1.6E-A 封签状态、定位当前活跃的 1.6D 公告源、探测 VPS 硬件指纹及磁盘空间配额：

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab
source .venv/bin/activate

echo "=== 2.1 检查上游 1.6E-A 审计凭据 ==="
test -d "$E_A_ROOT" || { echo "STOP: E_A_ROOT not found: $E_A_ROOT" >&2; exit 1; }
test -f "$E_A_ROOT/manifest.json" || { echo "STOP: E_A manifest.json missing" >&2; exit 1; }
test -f "$E_A_ROOT/execution_environment_attestation.json" || { echo "STOP: E_A attestation missing" >&2; exit 1; }
test -f "$E_A_ROOT/terminal_status.json" || { echo "STOP: E_A terminal_status missing" >&2; exit 1; }

# 验证 1.6E-A 终态必须为 complete
E_A_STATUS=$(python3 -c "import json; print(json.load(open('$E_A_ROOT/terminal_status.json'))['status'])")
test "$E_A_STATUS" = "complete" || { echo "STOP: E-A status is not complete ($E_A_STATUS)" >&2; exit 1; }
echo "1.6E-A Audit Root Status: PASS ($E_A_STATUS)"

echo "=== 2.2 自动探测上游 1.6D 活跃公告源目录 ==="
# 1.6D 运行在 stage1_6b namespace 下，寻找最新且未失败的 live_observation run_id
LATEST_1_6D_ROOT=$(find /root/crypto-alpha-lab/data/external_signal_shadow/stage1_6b/live_observation/ \
  -maxdepth 1 -mindepth 1 -type d \( -name "stage1_6d_live_*" -o -name "stage1_6b_live_source_*" \) | sort -r | head -n 1)

test -n "$LATEST_1_6D_ROOT" || { echo "STOP: No active 1.6D live source directory found!" >&2; exit 1; }
test -f "$LATEST_1_6D_ROOT/observer_checkpoint.json" || { echo "STOP: 1.6D observer_checkpoint.json missing" >&2; exit 1; }
test -f "$LATEST_1_6D_ROOT/capture_run_contract.json" || { echo "STOP: 1.6D capture_run_contract.json missing" >&2; exit 1; }
test -f "$LATEST_1_6D_ROOT/source_profile_probe_attestation.json" || { echo "STOP: 1.6D source_profile_probe_attestation.json missing" >&2; exit 1; }

SOURCE_RUN_ID=$(basename "$LATEST_1_6D_ROOT")
echo "Detected 1.6D Source Root: $LATEST_1_6D_ROOT"
echo "Detected 1.6D Source Run ID: $SOURCE_RUN_ID"

# 导出到临时文件以供后续启动阶段继承
echo "export SOURCE_ROOT='$LATEST_1_6D_ROOT'" > /tmp/stage1_6e_b_detected_source.env
echo "export SOURCE_RUN_ID='$SOURCE_RUN_ID'" >> /tmp/stage1_6e_b_detected_source.env

echo "=== 2.3 检查宿主机磁盘与文件系统 ==="
FREE_GB=$(df -BG /root/crypto-alpha-lab | awk 'NR==2 {gsub("G",""); print $4}')
echo "Available Disk Space: ${FREE_GB} GB"
test "$FREE_GB" -ge 8 || { echo "STOP: Insufficient disk space (< 8GB)" >&2; exit 1; }

echo "=== 2.4 检查硬件指纹 (/etc/machine-id) ==="
test -f /etc/machine-id || { echo "STOP: /etc/machine-id not found on VPS!" >&2; exit 1; }
MID_LEN=$(wc -c < /etc/machine-id | tr -d ' ')
test "$MID_LEN" -ge 32 || { echo "STOP: /etc/machine-id invalid length" >&2; exit 1; }
echo "Machine ID: present and valid"

echo "=== 2.5 检查共享锁文件与创建工作目录 ==="
mkdir -p "$E_B_SUPERVISOR_ROOT"
mkdir -p "$E_B_EVENTS_ROOT"
mkdir -p "$E_B_LOG_DIR"
touch "$SHARED_STORAGE_LOCK"

echo "=== STEP 2 PREFLIGHT PASSED: Ready for trial run! ==="
BASH
```

---

### 步骤 3：试运行验证与 Tmux 常驻启动 (Trial Run & Daemon Start)

#### 3.1 阶段一：单步试探验证（--once 模式）
通过 `--once` 参数运行一个完整的轮询探测周期，确保配置完全正确且无任何报错：

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab
source .venv/bin/activate
source /tmp/stage1_6e_b_detected_source.env

echo "Starting trial run (--once)..."
PYTHONPATH=src:. .venv/bin/python \
  scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py \
  --e-a-root "$E_A_ROOT" \
  --source-root "$SOURCE_ROOT" \
  --source-run-id "$SOURCE_RUN_ID" \
  --e-b-supervisor-root "$E_B_SUPERVISOR_ROOT" \
  --e-b-events-root "$E_B_EVENTS_ROOT" \
  --deployment-git-commit "$DEPLOY_COMMIT" \
  --shared-storage-lock "$SHARED_STORAGE_LOCK" \
  --once

echo "=== 3.1 TRIAL RUN SUCCESS: Exit code 0 ==="
BASH
```
> **检查标准**：终端输出退出码为 `0`，`supervisor` 根目录下正常生成 `supervisor_checkpoint.json`，未抛出任何 `KeyError`、`ValueError` 或 `Stage16EB*` 异常。

---

#### 3.2 阶段二：创建 Tmux 会话并拉起常驻守护进程
确认试运行无误后，在独立的后台 tmux 会话中拉起持续观察进程，并将日志写入独立日志文件：

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab
source .venv/bin/activate
source /tmp/stage1_6e_b_detected_source.env

# 检查是否已有运行中的同名会话，避免重复拉起
if tmux has-session -t "$E_B_TMUX_SESSION" 2>/dev/null; then
    echo "WARNING: Tmux session $E_B_TMUX_SESSION already exists!"
    echo "Use 'tmux attach -t $E_B_TMUX_SESSION' to view."
    exit 1
fi

LOG_FILE="$E_B_LOG_DIR/observer_$(date -u +%Y%m%dT%H%M%SZ).log"

# 创建新的后台 tmux 会话并启动常驻轮询（轮询间隔 1.0 秒）
tmux new-session -d -s "$E_B_TMUX_SESSION" -c /root/crypto-alpha-lab \
  "PYTHONPATH=src:. .venv/bin/python \
  scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py \
  --e-a-root '$E_A_ROOT' \
  --source-root '$SOURCE_ROOT' \
  --source-run-id '$SOURCE_RUN_ID' \
  --e-b-supervisor-root '$E_B_SUPERVISOR_ROOT' \
  --e-b-events-root '$E_B_EVENTS_ROOT' \
  --deployment-git-commit '$DEPLOY_COMMIT' \
  --shared-storage-lock '$SHARED_STORAGE_LOCK' \
  --poll-interval-s 1.0 2>&1 | tee -a '$LOG_FILE'"

echo "=== 3.2 DAEMON STARTED SUCCESSFULLY ==="
echo "Tmux Session: $E_B_TMUX_SESSION"
echo "Log File: $LOG_FILE"
BASH
```

---

#### 3.3 阶段三：首轮状态核查与运行监控
启动 5~10 秒后，执行状态核查：

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab

# 1. 检查 tmux 会话存活状态
tmux list-sessions | grep "$E_B_TMUX_SESSION"

# 2. 检查 Python 进程状态
ps aux | grep "run_stage1_6e_b_live_semantic_trigger_observer" | grep -v grep

# 3. 查看最近日志输出
LATEST_LOG=$(ls -t "$E_B_LOG_DIR"/observer_*.log | head -n 1)
echo "--- Last 20 lines of $LATEST_LOG ---"
tail -n 20 "$LATEST_LOG"

echo "=== 3.3 INITIAL HEALTH CHECK: PASS ==="
BASH
```

---

## 4. 日常巡检与运维排障指南 (Operations & Troubleshooting)

### 4.1 常用巡检指令

* **连接控制台实时观察**：
  ```bash
  tmux attach -t stage1_6e_b_live_semantic_observer
  # 退出控制台保持后台运行：按 Ctrl+B，然后按 D
  ```

* **跟踪实时日志**：
  ```bash
  tail -f /root/crypto-alpha-lab/logs/stage1_6e_b/$(ls -t /root/crypto-alpha-lab/logs/stage1_6e_b/ | head -n 1)
  ```

* **查看 Supervisor 消费检查点状态**：
  ```bash
  python3 -m json.tool /root/crypto-alpha-lab/data/external_signal_shadow/stage1_6e_b/supervisor/source_consumer_checkpoint.json
  ```

* **查看是否有新捕获的下架事件目录**：
  ```bash
  ls -lh /root/crypto-alpha-lab/data/external_signal_shadow/stage1_6e_b/events/
  ```

---

### 4.2 紧急停止与优雅关机规范 (Emergency Stop)

如果遇到突发异常（如币安 API 结构巨变或网络中断），需停止常驻进程：

```bash
# 优雅向 tmux 发送中断信号
tmux send-keys -t stage1_6e_b_live_semantic_observer C-c
sleep 3

# 检查进程是否已退出，如仍存在则关闭会话
if tmux has-session -t stage1_6e_b_live_semantic_observer 2>/dev/null; then
    tmux kill-session -t stage1_6e_b_live_semantic_observer
fi
echo "Observer gracefully stopped."
```

> [!CAUTION]
> **锁文件处理警告**：严禁手动删除 `.stage1_6e_b_supervisor.lock` 或 `.stage1_6_shared.lock`。进程在正常退出或崩溃自愈时会自动释放排他锁；手动删除锁文件极易引发双进程脑裂并发写坏数据。

---

### 4.3 常见报错排障速查表 (Troubleshooting Reference)

| 报错现象 / 异常码 | 根因分析 | 处理方案 |
|---|---|---|
| `environment_attestation_failed` | VPS 硬件指纹或文件系统设备号与 E-A 阶段记录不一致 | 检查是否在与 E-A 相同的 VPS 原机上运行；严禁跨机器搬迁目录。 |
| `missing_e_a_profile_core` | E-A 根目录中缺少 4 个标准 Profile 之一 | 重新指定合法的 E-A 权威审计路径。 |
| `insufficient_startup_free_space` | VPS 磁盘剩余空间低于 StorageGuard 预留门槛（8 GiB） | 清理 `/root/crypto-alpha-lab/logs/` 中的过期历史日志或拓展磁盘。 |
| `profile_core_raw_response_bound_invalid` | 行情接口单次响应大小超出协议硬顶（深度 256KB/指标 32KB） | 正常 Fail-Closed 触发，查看具体是哪个标的返回超大报文并记录事件。 |
| `invalid_source_run_id_format` | 传入的 `--source-run-id` 不符合正则命名规范 | 重新运行预检脚本自动探测正确的 1.6D Run ID。 |
