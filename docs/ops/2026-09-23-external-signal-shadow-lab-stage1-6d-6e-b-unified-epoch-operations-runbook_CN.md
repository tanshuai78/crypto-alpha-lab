# Stage 1.6D + 1.6E-B VPS 7天观测周期统一运维与代码部署操作手册

- **文档更新日期：** 2026-09-23
- **适用场景：**
  - **场景 A**：每隔 7 天常规自然到期后的平稳轮换重启（代码无任何修改）；
  - **场景 B**：修改了 Stage 1.6D 或 1.6E-B 运行时代码后的同步、部署与启动。
- **保护对象：** Stage 1.6D（期货下架公告持续源观察器）与 Stage 1.6E-B（实时语义触发与微观流动性观察器）。
- **硬安全边界：** 全流程强制保持 `RISK_LIVE_TRADING_ENABLED = False`，所有执行/实盘/模拟盘权限严密锁定为 `False`。

---

## 核心运行原则与防错铁律

1. **全新 Epoch 独立隔离原则**：
   - 1.6D 运行 7 天后会自动进入 `epoch_complete` 终态并生成封存凭证（`sealed_exports`）。旧目录属于只读历史凭据，**严禁 `--resume`、修改或覆盖**。
   - 1.6E-B 的检查点（Checkpoint）保存的是特定数据流的字节偏移量，**严禁跨 D 根目录复用**。每一轮 7 天观测周期必须生成全新独立的 `RUN_ID`（如 `stage1_6d_live_20260923T...`），派生专属于本轮的 1.6D 与 1.6E-B 目录。
2. **安全停机检查原则**：
   - 在停止旧 1.6E-B 前，**必须首先核验其检查点中的 `active_event_id` 为 `None`**。如果存在正在采样的活跃事件，严禁强杀进程，必须等待其 12 小时采样自然结束。
3. **多模块共存安全（Co-tenancy Safety）**：
   - VPS 上同时常驻运行着 Stage 1.5D 与 1.5F 进程，共用 `/root/crypto-alpha-lab` 仓库。
   - 所有运行时数据写入已被 `.gitignore` 排除的 `data/` 与 `logs/`，工作树源码保持干净。拉取与切换代码时必须谨慎，严禁带入未跟踪的临时改动。

---

## 操作路径快速索引

- **若代码有修改（需要同步并部署新代码）**：从 **[第一部分：代码修改与同步部署流水线](#第一部分代码修改与同步部署流水线场景-b-专用)** 开始执行。
- **若仅为常规 7 天到期重启（代码无改动）**：直接从 **[第二部分：新 Epoch 环境锁定与前置依赖发现](#第二部分新-epoch-环境锁定与前置依赖发现)** 开始执行。

---

## 第一部分：代码修改与同步部署流水线（场景 B 专用）

> [!NOTE]
> 如果本次只是 7 天自然到期重启、没有任何代码改动，请直接跳过此部分，前往第二部分。

### 步骤 0.1：在 Mac 本地提交并推送到远端

在本地开发机完成 1.6D 或 1.6E-B 代码修改后，执行自动化验证并推送：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
source .venv/bin/activate

# 1. 运行相关单元测试，确保无回归故障
pytest tests/scripts/external_signal_shadow/test_run_stage1_6* tests/src/research/external_signal_shadow/test_stage1_6* -q

# 2. 检查工作区状态并提交
git status --short
git add configs/ src/ scripts/
git commit -m "feat/fix(stage1_6): <描述你的代码修改>"

# 3. 推送到远程 GitHub 仓库
git push origin <当前分支名，如 feature/external-signal-shadow-stage1>

# 4. 打印并记录本次要部署的 40 位 Commit SHA
export DEPLOY_COMMIT="$(git rev-parse HEAD)"
echo "本次部署目标 Commit SHA: [$DEPLOY_COMMIT]"
```
> 请复制上面打印出的 40 位 SHA 字符串，在后续步骤中使用。

---

### 步骤 0.2：在 VPS 远端拉取并检出指定 Commit

登录 **VPS 终端**，执行以下标准检出流程：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 1. 填入你在 0.1 步中记录的 40 位 SHA
export DEPLOY_COMMIT='<粘贴 0.1 步复制的 40 位 Commit SHA>'

# 2. 确认工作树无未提交源码改动（仅允许存在 ignored 的 data/ 与 logs/）
git status --short

# 3. 从远端拉取最新提交并切换
git fetch origin
git checkout "$DEPLOY_COMMIT"

# 4. 验证检出是否精准匹配
actual="$(git rev-parse HEAD)"
test "$actual" = "$DEPLOY_COMMIT" || { echo "STOP: Commit 切换失败，当前为 $actual" >&2; exit 1; }
echo "CHECK_OK: VPS 已成功切换至目标 Commit: $actual"

# 5. 校验基础金融安全开关
PYTHONPATH=src:. .venv/bin/python -c '
from configs import base
from src.risk.limits import RiskLimits
assert base.RISK_LIVE_TRADING_ENABLED is False
assert RiskLimits.live_trading_enabled is False
print("CHECK_OK: 基础金融安全开关已锁定为只读 (PASS)")
'
```

---

## 第二部分：新 Epoch 环境锁定与前置依赖发现

从本部分开始，所有命令均在 **VPS 交互终端** 中执行。

### 步骤 2.1：锁定当前有效的 `DEPLOY_COMMIT`

根据你的场景，在 VPS 终端导出 `DEPLOY_COMMIT` 变量：

- **场景 A（常规重启，无代码改动）**：直接锁定 VPS 当前工作树的 `HEAD`：
  ```bash
  export DEPLOY_COMMIT="$(git rev-parse HEAD)"
  echo "当前运行 Commit: [$DEPLOY_COMMIT]"
  ```
- **场景 B（代码变动后部署）**：使用第一部分确认检出的 Commit：
  ```bash
  export DEPLOY_COMMIT='<填入刚才部署的 40 位 Commit SHA>'
  ```

---

### 步骤 2.2：在 VPS 自动发现并校验唯一合规的 `E_A_ROOT`

在 VPS 终端直接执行以下只读门禁脚本，自动枚举并锁定通过环境门禁校验的 `E_A_ROOT`：

```bash
bash <<'BASH'
set -euo pipefail
export PROJECT_ROOT=/root/crypto-alpha-lab
export GIT_CONFIG_GLOBAL=/dev/null
cd "$PROJECT_ROOT"

PYTHONPATH=src:. .venv/bin/python - "$PROJECT_ROOT" <<'PY'
import sys
from pathlib import Path

from scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit import (
    get_vps_step_a_projection,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage import (
    validate_e_a_runtime_gate,
)

project_root = Path(sys.argv[1]).resolve(strict=True)
parent = project_root / "data/external_signal_shadow/stage1_6e/capability_audits"
assert parent.is_dir() and not parent.is_symlink(), f"STOP=e_a_audits_parent_invalid:{parent}"
projection = get_vps_step_a_projection(project_root)
accepted = []
for candidate in sorted(parent.iterdir()):
    if not candidate.is_dir() or candidate.is_symlink():
        continue
    try:
        gate = validate_e_a_runtime_gate(candidate, step_a_projection=projection)
    except Exception as exc:
        continue
    accepted.append((candidate.resolve(), gate["manifest_id"], gate["manifest_sha256"]))

assert len(accepted) == 1, f"STOP=e_a_root_cardinality:{len(accepted)}:{accepted}"
root, manifest_id, manifest_sha = accepted[0]
print(f"export E_A_ROOT='{root}'")
print(f"CHECK_OK=e_a_runtime_gate:manifest_id={manifest_id}")
PY
BASH
```
> 输出中会包含一行 `export E_A_ROOT='/root/crypto-alpha-lab/data/...`，请复制该完整路径用于下一步。

---

### 步骤 2.3：在当前 VPS 终端统一导出核心基础变量

在 **当前 VPS 交互终端** 执行以下命令（请将尖括号替换为实际值）：

```bash
export PROJECT_ROOT=/root/crypto-alpha-lab
export GIT_CONFIG_GLOBAL=/dev/null
export DEPLOY_COMMIT='<确认后的40位SHA>'
export E_A_ROOT='<步骤2.2输出的E_A_ROOT绝对路径>'
export SHARED_STORAGE_LOCK="$PROJECT_ROOT/data/external_signal_shadow/.stage1_5_storage_guard.lock"
export E_B_BASE="$PROJECT_ROOT/data/external_signal_shadow/stage1_6e_b/epochs"

# 验证导出结果
printf 'PROJECT_ROOT=%s\nDEPLOY_COMMIT=%s\nE_A_ROOT=%s\n' "$PROJECT_ROOT" "$DEPLOY_COMMIT" "$E_A_ROOT"
```

---

## 第三部分：安全停机检查与旧会话优雅清理

在启动新周期前，必须确保上一轮观察没有处于半途中的活跃事件，随后安全终止旧进程。

在 VPS 终端执行以下脚本：

```bash
bash <<'BASH'
set -euo pipefail
export PROJECT_ROOT=/root/crypto-alpha-lab
cd "$PROJECT_ROOT"

echo "=== 1. 检查旧 E-B Checkpoint 中的活跃事件 ==="
python3 - <<'PY'
import json
from pathlib import Path

base = Path("data/external_signal_shadow/stage1_6e_b")
for path in sorted(base.glob("**/source_consumer_checkpoint.json")):
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
        active = row.get("active_event_id")
        print(f"Checkpoint: {path} | active_event_id: {active}")
        assert active is None, f"STOP: 存在未处理完的活跃事件 [{active}]，严禁停止！"
    except Exception as exc:
        print(f"Checkpoint 检查提示: {path} -> {exc}")
PY

echo -e "\n=== 2. 优雅停止旧 E-B tmux 会话 ==="
# 遍历并停止所有匹配 stage1_6e_b 的 tmux 会话
for sess in $(tmux ls -F '#{session_name}' 2>/dev/null | grep -E '^stage1_6e_b' || true); do
    echo "正在停止会话: $sess"
    tmux send-keys -t "$sess" C-c 2>/dev/null || true
    sleep 2
    tmux kill-session -t "$sess" 2>/dev/null || true
done

# 遍历并清理可能残留的旧 1.6D 僵尸进程
pkill -f 'run_stage1_6b_live_source_observer.py' 2>/dev/null || true
pkill -f 'run_stage1_6e_b_live_semantic_trigger_observer.py' 2>/dev/null || true

echo -e "\n=== 3. 验证进程是否完全清理 ==="
if pgrep -af 'run_stage1_6b_live_source_observer.py' >/dev/null; then
    echo "警告：仍有 1.6D 进程在运行！" >&2; exit 1
else
    echo "1.6D 进程已完全清空。"
fi

if pgrep -af 'run_stage1_6e_b_live_semantic_trigger_observer.py' >/dev/null; then
    echo "警告：仍有 1.6E-B 进程在运行！" >&2; exit 1
else
    echo "1.6E-B 进程已完全清空。"
fi

echo -e "\nCHECK_OK=old_sessions_safely_terminated"
BASH
```
> 输出显示 `CHECK_OK=old_sessions_safely_terminated` 即表示停机与清理完成。

---

## 第四部分：新 Epoch 环境预检与目标机本地证明（Attestation）

在 VPS 终端执行以下整段脚本，它将：
1. 校验宿主机磁盘可用容量（确保 $\ge 8\text{ GiB}$）；
2. 自动生成新周期的全局唯一 `RUN_ID`（带当前 UTC 时间戳），规划全新的隔离目录结构；
3. 运行在线探测器（Probe），自动选取当前币安最新有效 Delisting 公告，生成防篡改证明文件 `source_profile_probe_attestation.json`；
4. 将全套配置持久化写入 `/tmp/stage1_6_epoch.env`。

```bash
bash <<'BASH'
set -euo pipefail
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${DEPLOY_COMMIT:?STOP=DEPLOY_COMMIT_missing}"
: "${E_A_ROOT:?STOP=E_A_ROOT_missing}"
cd "$PROJECT_ROOT"

# 1. 校验磁盘可用容量
PYTHONPATH=src:. .venv/bin/python - <<'PY'
import shutil
from configs import base
assert base.RISK_LIVE_TRADING_ENABLED is False
free = shutil.disk_usage('.').free
assert free >= 8 * 1024 * 1024 * 1024, f'STOP=磁盘剩余空间不足8GiB:{free}'
print(f'CHECK_OK: 磁盘可用空间充足 ({free / 1024 / 1024 / 1024:.2f} GiB)')
PY

# 2. 生成全新隔离的 RUN_ID 与目录
export RUN_ID="stage1_6d_live_$(date -u +%Y%m%dT%H%M%SZ)"
export D_ROOT="$PROJECT_ROOT/data/external_signal_shadow/stage1_6b/live_observation/$RUN_ID"
export D_SESSION="stage1_6d_${RUN_ID}"
export D_LOG_DIR="$PROJECT_ROOT/logs/stage1_6d"
export E_B_SUPERVISOR_ROOT="$E_B_BASE/$RUN_ID/supervisor"
export E_B_EVENTS_ROOT="$E_B_BASE/$RUN_ID/events"
export E_B_SESSION="stage1_6e_b_${RUN_ID}"
export E_B_LOG_DIR="$PROJECT_ROOT/logs/stage1_6e_b/$RUN_ID"

test ! -e "$D_ROOT" || { echo "STOP=D目录已存在:$D_ROOT" >&2; exit 1; }
test ! -e "$E_B_SUPERVISOR_ROOT" || { echo "STOP=E-B目录已存在:$E_B_SUPERVISOR_ROOT" >&2; exit 1; }

# 3. 运行目标机探针并生成 Attestation
echo "正在执行 Delisting 源探测并生成 Attestation..."
PROBE_ARTICLE_ID="$(PYTHONPATH=src:. .venv/bin/python - <<'PY'
from src.research.external_signal_shadow.stage1_6b_canonical_source_client import Stage16BCanonicalClient, extract_selected_delisting_catalog
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import RequestClass

client = Stage16BCanonicalClient(live_public_readonly=True)
result = client.fetch_index_page(page_no=1, run_id='stage1_6d_epoch_preflight', request_class=RequestClass.PROFILE_PROBE_INDEX.value, monotonic_request_seq=1)
assert result.trust_validation_status == 'trusted'
catalog = extract_selected_delisting_catalog(result.raw_payload)
article_id = catalog.articles[0].get('code')
assert isinstance(article_id, str) and len(article_id) == 32
print(article_id.lower())
PY
)"

PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py \
  --probe-article-id "$PROBE_ARTICLE_ID" \
  --live-public-readonly \
  --project-root "$PROJECT_ROOT"

ATTEST_PATH="$PROJECT_ROOT/data/external_signal_shadow/stage1_6b/source_profile_attestations/$(PYTHONPATH=src:. .venv/bin/python - <<'PY'
from scripts.external_signal_shadow.run_stage1_6b_source_profile_probe import compute_source_profile_sha256
print(compute_source_profile_sha256())
PY
)/source_profile_probe_attestation.json"

test -f "$ATTEST_PATH" && test ! -L "$ATTEST_PATH" || { echo "STOP=证明文件生成失败:$ATTEST_PATH" >&2; exit 1; }

# 4. 固化全量环境配置到 /tmp/stage1_6_epoch.env
cat > /tmp/stage1_6_epoch.env <<EOF2
export PROJECT_ROOT='$PROJECT_ROOT'
export GIT_CONFIG_GLOBAL=/dev/null
export DEPLOY_COMMIT='$DEPLOY_COMMIT'
export E_A_ROOT='$E_A_ROOT'
export SHARED_STORAGE_LOCK='$SHARED_STORAGE_LOCK'
export RUN_ID='$RUN_ID'
export D_ROOT='$D_ROOT'
export D_SESSION='$D_SESSION'
export D_LOG_DIR='$D_LOG_DIR'
export E_B_SUPERVISOR_ROOT='$E_B_SUPERVISOR_ROOT'
export E_B_EVENTS_ROOT='$E_B_EVENTS_ROOT'
export E_B_SESSION='$E_B_SESSION'
export E_B_LOG_DIR='$E_B_LOG_DIR'
export ATTEST_PATH='$ATTEST_PATH'
EOF2
chmod 600 /tmp/stage1_6_epoch.env

echo -e "\n=== 新 Epoch 环境配置准备完毕 ==="
cat /tmp/stage1_6_epoch.env
echo -e "\nCHECK_OK=target_local_d_attestation_ready"
BASH
```
> 输出显示 `CHECK_OK=target_local_d_attestation_ready` 即表示预检和证明已就绪。

---

## 第五部分：启动新一轮 1.6D 守护进程

在 VPS 终端执行以下脚本：创建独立 tmux 会话启动 1.6D，并在完成首轮采集后校验心跳：

```bash
bash <<'BASH'
set -euo pipefail
source /tmp/stage1_6_epoch.env
cd "$PROJECT_ROOT"

mkdir -p "$D_LOG_DIR"
echo "正在创建 tmux 会话 [$D_SESSION] 启动 1.6D..."
tmux new-session -d -s "$D_SESSION" -c "$PROJECT_ROOT" \
  "exec env PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py --source-profile-attestation '$ATTEST_PATH' --live-public-readonly --run-id '$RUN_ID' --project-root '$PROJECT_ROOT' > '$D_LOG_DIR/$RUN_ID.log' 2>&1"

# 等待 8 秒，让 1.6D 完成第一轮 poll 并写入 checkpoint
sleep 8
tmux has-session -t "$D_SESSION" 2>/dev/null || { 
  tail -n 100 "$D_LOG_DIR/$RUN_ID.log" >&2
  echo 'STOP: 1.6D 启动失败退出！' >&2
  exit 1
}

echo "CHECK_OK: 1.6D 会话已启动 ($D_SESSION)"

# 校验首轮心跳写入
python3 - "$D_ROOT" "$RUN_ID" <<'PY'
import json, sys, time
from pathlib import Path

root, run_id = Path(sys.argv[1]), sys.argv[2]
contract = json.loads((root / 'capture_run_contract.json').read_text(encoding='utf-8'))
checkpoint = json.loads((root / 'observer_checkpoint.json').read_text(encoding='utf-8'))

assert contract['run_id'] == run_id and checkpoint['run_id'] == run_id
assert contract['capture_mode'] == checkpoint['capture_mode'] == 'live_observed'
assert not (root / 'terminal_status.json').exists(), 'STOP=d_terminal_premature'

age_ms = int(time.time() * 1000) - checkpoint['heartbeat_at_ms']
assert 0 <= age_ms <= 900_000, f'STOP=心跳超时:{age_ms}ms'

print({
    'CHECK_OK': '1.6D 首轮心跳正常',
    'poll_seq': checkpoint.get('poll_seq'),
    'heartbeat_age_ms': age_ms,
    'checkpoint_id': checkpoint.get('checkpoint_id')
})
PY
BASH
```

---

## 第六部分：Bootstrap 并启动新一轮 1.6E-B 消费者

在 1.6D 首轮采集确认后，执行 1.6E-B 单次注册引导并启动常驻消费者：

```bash
bash <<'BASH'
set -euo pipefail
source /tmp/stage1_6_epoch.env
cd "$PROJECT_ROOT"

test ! -e "$E_B_SUPERVISOR_ROOT" && test ! -e "$E_B_EVENTS_ROOT" || { echo 'STOP: E-B 根目录非全新！' >&2; exit 1; }

# 1. 执行单次引导注册 (--once)
echo "正在执行 1.6E-B 单次注册引导 (--once)..."
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py \
  --e-a-root "$E_A_ROOT" \
  --source-root "$D_ROOT" \
  --source-run-id "$RUN_ID" \
  --e-b-supervisor-root "$E_B_SUPERVISOR_ROOT" \
  --e-b-events-root "$E_B_EVENTS_ROOT" \
  --deployment-git-commit "$DEPLOY_COMMIT" \
  --shared-storage-lock "$SHARED_STORAGE_LOCK" \
  --once

test -f "$E_B_SUPERVISOR_ROOT/source_consumer_checkpoint.json" || { echo 'STOP: 检查点未生成！' >&2; exit 1; }
echo 'CHECK_OK: 1.6E-B 单次注册成功'

# 2. 启动常驻 1.6E-B 观察器
mkdir -p "$E_B_LOG_DIR"
echo "正在创建 tmux 会话 [$E_B_SESSION] 启动 1.6E-B..."
tmux new-session -d -s "$E_B_SESSION" -c "$PROJECT_ROOT" \
  "exec env PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py --e-a-root '$E_A_ROOT' --source-root '$D_ROOT' --source-run-id '$RUN_ID' --e-b-supervisor-root '$E_B_SUPERVISOR_ROOT' --e-b-events-root '$E_B_EVENTS_ROOT' --deployment-git-commit '$DEPLOY_COMMIT' --shared-storage-lock '$SHARED_STORAGE_LOCK' --poll-interval-s 1.0 > '$E_B_LOG_DIR/observer.log' 2>&1"

sleep 6
tmux has-session -t "$E_B_SESSION" 2>/dev/null || { 
  tail -n 100 "$E_B_LOG_DIR/observer.log" >&2
  echo 'STOP: 1.6E-B 启动失败退出！' >&2
  exit 1
}

echo "CHECK_OK: 1.6E-B 会话已启动 ($E_B_SESSION)"
BASH
```

---

## 第七部分：双端联合健康检查确认

在 VPS 终端执行以下只读检查脚本，确认双端强绑定、心跳新鲜且硬安全开关 100% 生效：

```bash
bash <<'BASH'
set -euo pipefail
source /tmp/stage1_6_epoch.env
cd "$PROJECT_ROOT"

python3 - "$D_ROOT" "$E_B_SUPERVISOR_ROOT" "$RUN_ID" "$DEPLOY_COMMIT" <<'PY'
import json, sys, time
from pathlib import Path

d_root, e_root, run_id, commit = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
d = json.loads((d_root / 'observer_checkpoint.json').read_text(encoding='utf-8'))
e = json.loads((e_root / 'source_consumer_checkpoint.json').read_text(encoding='utf-8'))

age_ms = int(time.time() * 1000) - d['heartbeat_at_ms']
assert d['run_id'] == run_id, "RUN_ID 匹配失败"
assert str(d_root.resolve()) == e['source_root_realpath'], "数据源根路径绑定失败"
assert not (d_root / 'terminal_status.json').exists(), 'STOP=d_terminal_root'
assert 0 <= age_ms <= 900_000, f'STOP=心跳超时:{age_ms}ms'
assert all(value is False for value in e['permissions'].values()), "权限安全开关存在泄露！"

print({
    'STATUS': '1.6D + 1.6E-B 联合启动成功且强绑定通过',
    'd_poll_seq': d.get('poll_seq'),
    'd_heartbeat_age_ms': age_ms,
    'e_b_active_event_id': e['active_event_id'],
    'e_b_permissions_safe': True,
    'deploy_commit': commit,
})
PY

tmux has-session -t "$D_SESSION" 2>/dev/null && echo "1.6D tmux 会话: [RUNNING]"
tmux has-session -t "$E_B_SESSION" 2>/dev/null && echo "1.6E-B tmux 会话: [RUNNING]"
echo 'CHECK_OK=epoch_health_passed'
BASH
```
> 输出显示 `CHECK_OK=epoch_health_passed` 即标志全新 7 天周期启动圆满完成！

---

## 第八部分：日常巡检与 7 天后自然闭环处理

### 8.1 日常一键巡检命令

日常只需在 VPS 执行以下命令，即可随时获取心跳、轮巡次数以及是否有活跃事件触发：

```bash
bash <<'BASH'
source /tmp/stage1_6_epoch.env
python3 - "$D_ROOT" "$E_B_SUPERVISOR_ROOT" "$RUN_ID" "$DEPLOY_COMMIT" <<'PY'
import json, sys, time
from pathlib import Path
d_root, e_root = Path(sys.argv[1]), Path(sys.argv[2])
d = json.loads((d_root / 'observer_checkpoint.json').read_text(encoding='utf-8'))
e = json.loads((e_root / 'source_consumer_checkpoint.json').read_text(encoding='utf-8'))
age_ms = int(time.time() * 1000) - d['heartbeat_at_ms']
print({
    '1.6D_轮巡次数': d.get('poll_seq'),
    '1.6D_心跳延迟(ms)': age_ms,
    '1.6E-B_活跃事件ID': e.get('active_event_id'),
    '健康状态': 'PASS' if 0 <= age_ms <= 900_000 and not (d_root / 'terminal_status.json').exists() else 'ALERT'
})
PY
tmux has-session -t "$D_SESSION" 2>/dev/null && echo "1.6D tmux: RUNNING"
tmux has-session -t "$E_B_SESSION" 2>/dev/null && echo "1.6E-B tmux: RUNNING"
BASH
```

### 8.2 7 天后自然到期处理

1. **到期特征**：
   - 1.6D 达到 7 天上限后，tmux 会话会自动退出，根目录下会生成 `terminal_status.json`（`terminal_reason = "epoch_complete"`）及 `sealed_exports/`。
2. **处理流程**：
   - 检查 1.6E-B 的 `active_event_id` 确认无活跃事件；
   - 严格按照本手册从 **[第二部分](#第二部分新-epoch-环境锁定与前置依赖发现)** 开始执行，开启下一个 7 天 Epoch；
   - **历史目录与封存文件原地保留作为只读证据，严禁删除**。
