# Stage 1.6D VPS Live Source Observation Runbook

- **日期:** 2026-08-25
- **状态:** `current_runbook_draft`
- **范围:** Stage 1.6D Binance USD-M Futures Delisting 的 VPS live source observation only
- **代码变更:** `false`
- **deployment_authorization:** `false`
- **硬安全开关:** `RISK_LIVE_TRADING_ENABLED = false`
- **Design authority:** [1.6D Deployment Authorization Design](../designs/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md)
- **路线 authority:** [Stage 1.6 Futures Delisting Route Map](../project-status/2026-08-24-stage1-6-futures-delisting-route-map_CN.md)
- **历史参考，不是当前 procedure:** [2026-08-19 Stage 1.6B Read-Only Checklist](../reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md)
- **Existing runners:** `scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py` and `scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py`

## 1. Authority Boundary

本 runbook 只编排既有的 public-read-only source probe 和 live observer。它不修改代码、配置、阈值或历史 evidence root。

> [!CAUTION]
> **历史事故根隔离铁律**: 2026-08-26 事故 live 目录 `stage1_6d_live_20260826T031333Z` 属于只读冻结 incident baseline，严禁对其执行 `--resume`、修改或覆盖。任何新启动必须分配全新 `RUN_ID`。

完成全部 preflight 也**不等于**允许启动。只有下列内容在同一 target transcript 中全部 PASS 后，用户才能另行授权一个明确的 `DEPLOY_COMMIT`、host、`RUN_ID` 和 `ATTEST_PATH`：


```text
point_in_time_source_validated = false
market_data_coverage_passed = false
replay_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

所有命令块都在独立 `bash` 子进程运行，避免在交互式 zsh 中使用 `set -u` 触发 `RPROMPT` 问题；每个命令块自行进入 `/root/crypto-alpha-lab`，不依赖前一块的 `cd`。子进程内的变量不会自动回到交互 shell；只有 Section 2 与 Section 5 的显式 handoff 可将已验证的启动事实交给后续命令。任一 `STOP`、assertion failure 或非零退出码均表示不得继续下一节。

## 2. Target Baseline And Environment Gate

先在 VPS 的交互 shell 中记录用户本次授权的 exact commit；不得使用未审查的 descendant。之后再执行下方命令块。

```bash
export DEPLOY_COMMIT='<reviewed-40-character-deployment-commit-sha>'
```

```bash
bash <<'BASH'
set -euo pipefail
: "${DEPLOY_COMMIT:?STOP: export exact reviewed DEPLOY_COMMIT before Section 2}"
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
test "$(git rev-parse HEAD)" = "$DEPLOY_COMMIT" || { echo 'STOP: DEPLOY_COMMIT mismatch' >&2; exit 1; }
test -z "$(git status --short --untracked-files=all)" || { echo 'STOP: target worktree is dirty' >&2; exit 1; }
PYTHONPATH=src:. .venv/bin/python -c \
  "from configs import base; from scripts.external_signal_shadow.run_stage1_6b_live_source_observer import run_live_source_observer; assert base.RISK_LIVE_TRADING_ENABLED is False; print('stage1_6d_target_environment=PASS')"
printf 'DEPLOY_COMMIT=%s\n' "$DEPLOY_COMMIT"
BASH
```

必须输出 `stage1_6d_target_environment=PASS`。解释器或 import 失败不是“稍后再修”的告警，而是 STOP。

运行部署相关的定向回归。不得将无关的 Stage 1.2--1.5 测试 tree 作为本 runbook 的 gate，也不得跳过这六个文件。

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py
BASH
```

Expected: all tests pass. A failure blocks probe and start.

## 3. Dynamic Probe Article And Target-Local V2 Attestation

禁止复用本地 attestation；不得硬编码历史公告 ID。下方单一命令块从 target 的当前 strict selected Delisting catalog 获取一个 current `code`，再以同一个 `PROBE_ARTICLE_ID` 完成 probe 和 attestation validation。它不依赖跨 shell 环境变量。

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
PROBE_ARTICLE_ID="$(PYTHONPATH=src:. .venv/bin/python - <<'PY'
from src.research.external_signal_shadow.stage1_6b_canonical_source_client import (
    Stage16BCanonicalClient, extract_selected_delisting_catalog,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import RequestClass

client = Stage16BCanonicalClient(live_public_readonly=True)
result = client.fetch_index_page(
    page_no=1,
    run_id='stage1_6d_preflight_selector',
    request_class=RequestClass.PROFILE_PROBE_INDEX.value,
    monotonic_request_seq=1,
)
assert result.trust_validation_status == 'trusted', result.trust_validation_status
catalog = extract_selected_delisting_catalog(result.raw_payload)
assert catalog.articles, 'selected Delisting catalog is empty'
article_id = catalog.articles[0].get('code')
assert isinstance(article_id, str) and len(article_id) == 32 and all(c in '0123456789abcdefABCDEF' for c in article_id), article_id
print(article_id.lower())
PY
)"
PYTHONPATH=src:. .venv/bin/python \
  scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py \
  --probe-article-id "$PROBE_ARTICLE_ID" \
  --live-public-readonly \
  --project-root "$PWD"
ATTEST_PATH="$PWD/data/external_signal_shadow/stage1_6b/source_profile_attestations/$(PYTHONPATH=src:. .venv/bin/python - <<'PY'
from scripts.external_signal_shadow.run_stage1_6b_source_profile_probe import compute_source_profile_sha256
print(compute_source_profile_sha256())
PY
)/source_profile_probe_attestation.json"
test -f "$ATTEST_PATH" || { echo "STOP: expected attestation is missing: $ATTEST_PATH" >&2; exit 1; }
PYTHONPATH=src:. .venv/bin/python - "$ATTEST_PATH" <<'PY'
import hashlib, json, re, sys
from pathlib import Path
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    SOURCE_PROFILE_ID, compute_request_headers_profile_sha256,
)
p = Path(sys.argv[1]).resolve()
allowed = (Path.cwd() / 'data/external_signal_shadow/stage1_6b/source_profile_attestations').resolve()
assert p.is_relative_to(allowed) and p.name == 'source_profile_probe_attestation.json'
row = json.loads(p.read_text(encoding='utf-8'))
assert row['schema_version'] == 'stage1_6b_source_profile_probe_attestation_v2'
assert row['source_profile_id'] == SOURCE_PROFILE_ID == 'binance_public_web_bapi_en_delisting_catalog_v2'
assert row['selected_catalog_id'] == 161 and row['selected_catalog_name'] == 'Delisting'
assert re.fullmatch(r'[0-9a-f]{64}', row['source_profile_sha256'])
assert row['request_headers_profile_sha256'] == compute_request_headers_profile_sha256()
assert isinstance(row['probe_attested_at_ms'], int) and not isinstance(row['probe_attested_at_ms'], bool)
print({'ATTEST_PATH': str(p), 'attestation_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'probe_attested_at_ms': row['probe_attested_at_ms']})
PY
printf 'PROBE_ARTICLE_ID=%s\n' "$PROBE_ARTICLE_ID"
printf 'ATTEST_PATH=%s\n' "$ATTEST_PATH"
BASH
```

`probe_attested_at_ms` 只可早于或等于稍后首启的 `run_started_at_ms`。保存本节打印的 `ATTEST_PATH`，供 Section 5 的显式 handoff 使用。任何 `probe_article_id_not_in_selected_catalog`、transport failure、schema drift 或 hash mismatch 都是 STOP；不得改用历史 ID、其他 endpoint 或其他机器的 attestation。

## 4. Shared Host, Root And Session Gate

设置一个唯一 run ID；首启不得使用已存在的 live root、tmux session 或 `--resume`。Stage 1.5D/F 只在同一 host 上 active 时构成 co-tenancy 健康门禁；UNITREE 和本地 1.5G 不是当前 gate。

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
export RUN_ID="stage1_6d_live_$(date -u +%Y%m%dT%H%M%SZ)"
export SESSION="stage1_6d_live_${RUN_ID}"
export LIVE_ROOT="data/external_signal_shadow/stage1_6b/live_observation/${RUN_ID}"
export SHARED_LOCK="data/external_signal_shadow/.stage1_5_storage_guard.lock"

python3 - <<'PY'
import shutil
required = 8 * 1024 * 1024 * 1024
free = shutil.disk_usage('.').free
print({'storage_free_bytes': free, 'required_start_free_bytes': required})
assert free >= required, 'STOP: host free space is below 8 GiB'
PY

test ! -e "$LIVE_ROOT" || { echo "STOP: fresh live root already exists: $LIVE_ROOT" >&2; exit 1; }
tmux has-session -t "$SESSION" 2>/dev/null && { echo "STOP: target tmux session already exists: $SESSION" >&2; exit 1; } || true
if pgrep -af 'run_stage1_6b_live_source_observer.py' >/dev/null; then
  echo 'STOP: an existing Stage 1.6D writer is running' >&2
  pgrep -af 'run_stage1_6b_live_source_observer.py' >&2
  exit 1
fi

python3 - <<'PY'
import json
import time
from pathlib import Path

PROCESS_SPECS = {
    "stage1_5d": {
        "script": "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py",
        "summary": "live_safety_gate_summary.json",
    },
    "stage1_5f": {
        "script": "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py",
        "summary": "live_depth_observer_summary.json",
    },
}


def active_roots(script: str) -> list[str]:
    roots = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            argv = [part.decode("utf-8") for part in (proc / "cmdline").read_bytes().split(b"\0") if part]
        except OSError:
            continue
        # tmux retains its first new-session command in argv after that pane exits.
        # Only an interpreter process is an active Stage 1.5 writer.
        if not argv or not Path(argv[0]).name.startswith("python"):
            continue
        if script not in argv:
            continue
        try:
            roots.append(argv[argv.index("--output-root") + 1])
        except (ValueError, IndexError) as exc:
            raise SystemExit(f"STOP: active writer has no --output-root: pid={proc.name}") from exc
    if len(roots) != len(set(roots)):
        raise SystemExit(f"STOP: duplicate active writer root for {script}: {roots}")
    return roots


def load(root: str, summary_name: str) -> dict:
    path = Path(root) / summary_name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"STOP: unreadable active-writer summary: {path}: {exc}") from exc


def verify(stage: str, root: str) -> int:
    summary = load(root, PROCESS_SPECS[stage]["summary"])
    if stage == "stage1_5d":
        assert summary.get("status") == "READY", summary
        assert summary.get("decision") == "stage1_5d_runtime_gate_ready", summary
        assert summary.get("consumable_by_stage1_5f") is True, summary
        assert summary.get("fatal_blockers") in (None, []), summary
    else:
        assert summary.get("consumer_runtime_attestation_verified") is True, summary
        assert summary.get("consumer_runtime_attestation_compromised") is False, summary
        assert summary.get("block_new_event_admission") is False, summary
        assert summary.get("blocker") is None, summary
    assert summary.get("storage_guard_status") == "ready", summary
    assert summary.get("storage_blocker") is None, summary
    heartbeat = summary.get("last_heartbeat_at_ms")
    assert isinstance(heartbeat, int) and heartbeat > 0, summary
    return heartbeat


active = {
    stage: active_roots(spec["script"])
    for stage, spec in PROCESS_SPECS.items()
}
if not any(active.values()):
    print("stage1_5_co_tenancy=absent")
    raise SystemExit(0)

first = {
    (stage, root): verify(stage, root)
    for stage, roots in active.items()
    for root in roots
}
print({"stage1_5_co_tenancy": "observing", "roots": active, "heartbeats": first})
time.sleep(70)
second = {
    (stage, root): verify(stage, root)
    for stage, roots in active.items()
    for root in roots
}
for key, first_heartbeat in first.items():
    assert second[key] > first_heartbeat, {
        "STOP": "active Stage 1.5 heartbeat did not advance in 70 seconds",
        "writer": key,
        "first": first_heartbeat,
        "second": second[key],
    }
print({"stage1_5_co_tenancy": "healthy", "roots": active, "heartbeats": second})
PY

# flock tests ownership; a pre-existing lock-file path alone is not an error and must never be deleted.
flock -n "$SHARED_LOCK" -c 'true' || { echo "STOP: shared lock is currently held: $SHARED_LOCK" >&2; exit 1; }
printf 'RUN_ID=%s\nSESSION=%s\nLIVE_ROOT=%s\n' "$RUN_ID" "$SESSION" "$LIVE_ROOT"
BASH
```

若 1.5D/F active，本节只接受实际 Python interpreter process，并从其 `/proc/*/cmdline` 精确读取 `--output-root`；tmux server 保留的历史 `new-session` 参数不构成 active writer。在 70 秒窗口内两次验证 official summary、heartbeat、storage、attestation 与 blocker 状态。仅当每个 active writer 的 heartbeat 前进且共享锁当前可用时，输出 `stage1_5_co_tenancy=healthy` 并继续；任何解析、summary、heartbeat 或 lock failure 都是 STOP。不能通过删除 `.stage1_5_storage_guard.lock` 或任何 1.5 root 来绕过。

本 runbook 不停止或重启 Stage 1.5。若实际 active 的 1.5 writer 不健康，必须保留其 root，并按该 stage 自己的结束或恢复授权处理；不得用 `kill -9`、删除 tmux server 或修改其 durable state 来把 co-tenancy 伪造为 absent。

## 5. Production Start Contract

本节是**部署后**命令形状，不得在未取得明确用户授权前执行。启动时使用 tmux pane 作为日志载体；不得重定向至 live root，也不得把外部日志文件复制回 root 或 sealed export。

只有 Section 2--4 均 PASS 且用户已明确授权 exact `DEPLOY_COMMIT`、host、`RUN_ID` 与 `ATTEST_PATH` 后，才可在**同一个 VPS 交互 shell**中填入 Section 3/4 的打印值，并验证启动 handoff。新开终端时只可重输这些已验证值，禁止重新生成 `RUN_ID` 或 `ATTEST_PATH`。

```bash
export ATTEST_PATH='<exact-ATTEST_PATH-printed-by-Section-3>'
export RUN_ID='<exact-RUN_ID-printed-by-Section-4>'
export SESSION='<exact-SESSION-printed-by-Section-4>'
export LIVE_ROOT='<exact-LIVE_ROOT-printed-by-Section-4>'

bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
: "${ATTEST_PATH:?STOP: target-local v2 attestation path is required}"
: "${RUN_ID:?STOP: fresh RUN_ID is required}"
: "${SESSION:?STOP: fresh SESSION is required}"
: "${LIVE_ROOT:?STOP: fresh LIVE_ROOT is required}"
test -f "$ATTEST_PATH" || { echo "STOP: attestation missing: $ATTEST_PATH" >&2; exit 1; }
test "$SESSION" = "stage1_6d_live_${RUN_ID}" || { echo 'STOP: SESSION does not bind RUN_ID' >&2; exit 1; }
test "$LIVE_ROOT" = "data/external_signal_shadow/stage1_6b/live_observation/${RUN_ID}" || { echo 'STOP: LIVE_ROOT does not bind RUN_ID' >&2; exit 1; }
printf 'START_CONTEXT=PASS RUN_ID=%s SESSION=%s LIVE_ROOT=%s ATTEST_PATH=%s\n' "$RUN_ID" "$SESSION" "$LIVE_ROOT" "$ATTEST_PATH"
BASH
```

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
: "${ATTEST_PATH:?STOP: target-local v2 attestation path is required}"
: "${RUN_ID:?STOP: fresh RUN_ID is required}"
: "${SESSION:?STOP: fresh SESSION is required}"
: "${LIVE_ROOT:?STOP: fresh LIVE_ROOT is required}"
test ! -e "$LIVE_ROOT" || { echo "STOP: root already exists" >&2; exit 1; }
tmux has-session -t "$SESSION" 2>/dev/null && { echo "STOP: session already exists" >&2; exit 1; }

tmux new-session -d -s "$SESSION" \
  "cd '$PWD' && exec env PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py --source-profile-attestation '$ATTEST_PATH' --live-public-readonly --run-id '$RUN_ID' --project-root '$PWD'"
printf 'STARTED_SESSION=%s\nSTARTED_ROOT=%s\n' "$SESSION" "$LIVE_ROOT"
BASH
```

首个 production epoch 不得传 `--resume`、`--max-polls` 或短于 7 天的 `--max-seconds`。既有 runner 默认以 300 秒单线程顺序轮询，每次 poll 最多顺序抓取 4 个 detail（`EXTERNAL_SIGNAL_STAGE1_6B_LIVE_MAX_DETAIL_REQUESTS_PER_POLL = 4`，FIFO 突发队列调度），且 epoch 上限为 7 天。tmux pane 可用 `tmux attach -t "$SESSION"` 观察；任何外部持久化日志只能位于 live root family 之外且不是 evidence。

## 6. Running Health Gate

在运行期间只读检查，不重启、不修改 checkpoint：

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
: "${LIVE_ROOT:?STOP: export LIVE_ROOT}"
: "${RUN_ID:?STOP: export RUN_ID}"
: "${SESSION:?STOP: export SESSION}"
tmux has-session -t "$SESSION"
pgrep -af "run_stage1_6b_live_source_observer.py.*--run-id ${RUN_ID}"
PYTHONPATH=src:. .venv/bin/python - "$LIVE_ROOT" "$RUN_ID" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
run_id = sys.argv[2]
checkpoint = root / 'observer_checkpoint.json'
assert checkpoint.is_file(), f'STOP: missing checkpoint: {checkpoint}'
row = json.loads(checkpoint.read_text(encoding='utf-8'))
assert row['schema_version'] == 'stage1_6b_observer_checkpoint_v3'
assert row['run_id'] == run_id
assert row['capture_mode'] == 'live_observed'
assert row['source_profile_id'] == 'binance_public_web_bapi_en_delisting_catalog_v2'
assert (root / '.stage1_6b_writer.lock').exists()
assert not (root / 'terminal_status.json').exists(), 'STOP: root is terminal; use Section 7'
assert row.get('pending_terminal_failure_reason') is None, 'STOP: root has pending terminal failure intent'
print({'live_checkpoint_id': row['checkpoint_id'], 'poll_seq': row['poll_seq'], 'accounted_root_bytes': row['accounted_root_bytes']})
PY
BASH
```

若 checkpoint 未随至少一个 polling cycle 出现、writer/session 不匹配、storage blocker 出现或 root terminal，STOP 并进入 Section 7；不得启动第二 writer。

## 7. Terminal, Seal, Interruption And Resume

### 7.1 Normal completion

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
: "${LIVE_ROOT:?STOP: export LIVE_ROOT}"
PYTHONPATH=src:. .venv/bin/python - "$LIVE_ROOT" <<'PY'
import json, sys
from pathlib import Path
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import load_sealed_export
root = Path(sys.argv[1])
terminal = json.loads((root / 'terminal_status.json').read_text(encoding='utf-8'))
assert terminal['schema_version'] == 'stage1_6b_terminal_status_v1'
assert terminal['capture_mode'] == 'live_observed'
assert terminal['status'] == 'complete'
assert terminal['terminal_reason'] in ('epoch_complete', 'test_bound')
exports = sorted((root / 'sealed_exports').glob('*/sealed_export_manifest.json'))
assert len(exports) == 1, exports
manifest = load_sealed_export(exports[0].parent)
assert manifest['capture_mode'] == 'live_observed'
print({'terminal_reason': terminal['terminal_reason'], 'sealed_export_id': manifest['export_id']})
PY
BASH
```

Normal completion requires `terminal_reason=epoch_complete` (或测试环境 `test_bound`) and creates one independent sealed evidence unit. It does not grant any PIT, market-data, replay, alpha or trading conclusion.

### 7.2 Failure terminal

受控终态包含以下 4 种 failure 模式和 1 种 operator stop：
1. `detail_first_attempt_deadline_missed`: Lane A 候选 detail 首次抓取超过准入时分配的 SLA 截止 poll_seq（排队延迟或抓取饿死）。
2. `pending_detail_candidate_capacity_exceeded`: 待抓取候选队列超过容量上限（`EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES = 500`）。
3. `source_profile_schema_drift`: Binance API 响应 schema 结构或 catalog 漂移，记录 `malformed_index_schema` 降级检查点。
4. `storage_exhausted`: 写入触发磁盘存储保护阻断。`root_budget_exceeded` 与 `host_reserve_exceeded` 仅可作为 guard diagnostic，不能写入 terminal reason。
5. `operator_stop`: 操作员发送 SIGINT/SIGTERM/Ctrl+C 触发的主动优雅终止（`status="complete"`, `terminal_reason="operator_stop"`，不封存）。

所有 failure 终态均**严禁封存** (`sealed_exports/` 不存在)，保留未封存 live evidence root 供事后审计：

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
: "${LIVE_ROOT:?STOP: export LIVE_ROOT}"
PYTHONPATH=src:. .venv/bin/python - "$LIVE_ROOT" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
terminal = json.loads((root / 'terminal_status.json').read_text(encoding='utf-8'))
assert terminal['status'] in ('failure', 'complete')
assert not list((root / 'sealed_exports').glob('*/sealed_export_manifest.json'))
print({'terminal_reason': terminal['terminal_reason'], 'status': terminal['status'], 'action': 'preserve_root_and_stop'})
PY
BASH
```

特别是 `source_profile_schema_drift` 或 SLA/Capacity failure：保留 evidence，禁止手工篡改，另行走 source-contract Design。

### 7.3 Interrupted root and controlled resume

只在另行明确授权后，且 root 无 terminal、无 sealed export、原 attestation SHA 与 capture contract 完全一致，且检查点 schema 为 `stage1_6b_observer_checkpoint_v3` 且 `pending_terminal_failure_reason` 为 null 时，才可按既有 runner `--resume` 分支恢复。它在 client/network 前必须先写 reconciliation checkpoint：

```bash
bash <<'BASH'
set -euo pipefail
cd /root/crypto-alpha-lab || { echo 'STOP: repository root unavailable' >&2; exit 1; }
test -d .git || { echo 'STOP: not a Git repository' >&2; exit 1; }
: "${ATTEST_PATH:?STOP: original attestation path is required}"
: "${RUN_ID:?STOP: original RUN_ID is required}"
: "${LIVE_ROOT:?STOP: original LIVE_ROOT is required}"
test -d "$LIVE_ROOT"
test ! -e "$LIVE_ROOT/terminal_status.json" || { echo 'STOP: terminal root cannot resume' >&2; exit 1; }
test -z "$(find "$LIVE_ROOT/sealed_exports" -mindepth 1 -maxdepth 1 -type d -print -quit 2>/dev/null)" || { echo 'STOP: sealed root cannot resume' >&2; exit 1; }
# This is a post-authorization command shape; do not run it as a substitute for preflight.
PYTHONPATH=src:. .venv/bin/python \
  scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py \
  --source-profile-attestation "$ATTEST_PATH" \
  --live-public-readonly \
  --run-id "$RUN_ID" \
  --resume \
  --project-root "$PWD"
BASH
```


## 8. No-Start / Rollback Rule

```text
preflight failure or missing authorization -> do not start
source-profile/schema drift -> preserve failure root; no seal; stop
operator cancellation -> preserve interrupted root; no fabricated terminal
terminal or sealed root -> no resume; next epoch requires new root and fresh target attestation
```

任何 1.6D root 只能记录 public source observation。它不能将下列值改为 true：`point_in_time_source_validated`、`market_data_coverage_passed`、`replay_allowed`、`trade_signal_allowed`、`paper_trading_allowed`、`live_trading_allowed`、`execution_engine_allowed`、`alpha_interpretation_allowed`。
