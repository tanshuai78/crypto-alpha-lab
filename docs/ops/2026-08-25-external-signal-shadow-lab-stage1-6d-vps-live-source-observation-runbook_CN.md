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

所有命令块都在独立 `bash` 子进程运行，避免在交互式 zsh 中使用 `set -u` 触发 `RPROMPT` 问题。任一 `STOP`、assertion failure 或非零退出码均表示不得继续下一节。

## 2. Target Baseline And Environment Gate

在 VPS repository root 执行。将 approved commit 替换为用户本次授权的 commit；不得使用未审查的 descendant。

```bash
bash <<'BASH'
set -euo pipefail
export DEPLOY_COMMIT='c98801bb99e7e0d9d472b9684db97a12f442bdb6'
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

禁止复用本地 attestation；不得硬编码历史公告 ID。先从 target 的当前 strict selected Delisting catalog 获取一个 current `code`；它必须是 32-hex string。这个预选只生成 `PROBE_ARTICLE_ID`，实际 probe 会自行再取 index，并验证它在**probe 同次** selected catalog 中。

```bash
bash <<'BASH'
set -euo pipefail
export PROBE_ARTICLE_ID="$(PYTHONPATH=src:. .venv/bin/python - <<'PY'
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
printf 'PROBE_ARTICLE_ID=%s\n' "$PROBE_ARTICLE_ID"
BASH
```

运行 target-local profile probe：

```bash
bash <<'BASH'
set -euo pipefail
: "${PROBE_ARTICLE_ID:?STOP: run the dynamic selector in Section 3 first}"
PYTHONPATH=src:. .venv/bin/python \
  scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py \
  --probe-article-id "$PROBE_ARTICLE_ID" \
  --live-public-readonly \
  --project-root "$PWD"
BASH
```

从 probe 输出取得 `ATTEST_PATH`，然后验证其 exact contract。`probe_attested_at_ms` 只可早于或等于稍后首启的 `run_started_at_ms`。

```bash
bash <<'BASH'
set -euo pipefail
: "${ATTEST_PATH:?STOP: export exact target probe output path as ATTEST_PATH}"
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
BASH
```

任何 `probe_article_id_not_in_selected_catalog`、transport failure、schema drift 或 hash mismatch 都是 STOP；不得改用历史 ID、其他 endpoint 或其他机器的 attestation。

## 4. Shared Host, Root And Session Gate

设置一个唯一 run ID；首启不得使用已存在的 live root、tmux session 或 `--resume`。Stage 1.5D/F 只在同一 host 上 active 时构成 co-tenancy 健康门禁；UNITREE 和本地 1.5G 不是当前 gate。

```bash
bash <<'BASH'
set -euo pipefail
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

D_ACTIVE="$(pgrep -af 'run_stage1_5d_live_event_source_smoke_collector.py' || true)"
F_ACTIVE="$(pgrep -af 'run_stage1_5f_live_depth_observer.py' || true)"
if [ -n "$D_ACTIVE$F_ACTIVE" ]; then
  printf '%s\n%s\n' "$D_ACTIVE" "$F_ACTIVE"
  echo 'STOP unless each active Stage 1.5D/F writer has a healthy official summary, no blocker, and usable shared storage lock.' >&2
  exit 1
fi

echo "stage1_5_co_tenancy=absent"
# flock tests ownership; a pre-existing lock-file path alone is not an error and must never be deleted.
flock -n "$SHARED_LOCK" -c 'true' || { echo "STOP: shared lock is currently held: $SHARED_LOCK" >&2; exit 1; }
printf 'RUN_ID=%s\nSESSION=%s\nLIVE_ROOT=%s\n' "$RUN_ID" "$SESSION" "$LIVE_ROOT"
BASH
```

如果 1.5D/F active，停止在这里，先在其各自 root 验证 runtime gate/summary、heartbeat、storage 与 `blocker=null`，并确认 shared lock 没有被异常持有；通过后才可重新执行本节。不能通过删除 `.stage1_5_storage_guard.lock` 或任何 1.5 root 来绕过。

## 5. Production Start Contract

本节是**部署后**命令形状，不得在未取得明确用户授权前执行。启动时使用 tmux pane 作为日志载体；不得重定向至 live root，也不得把外部日志文件复制回 root 或 sealed export。

```bash
bash <<'BASH'
set -euo pipefail
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

首个 production epoch 不得传 `--resume`、`--max-polls` 或短于 7 天的 `--max-seconds`。既有 runner 默认以 300 秒单线程顺序轮询，且 epoch 上限为 7 天。tmux pane 可用 `tmux attach -t "$SESSION"` 观察；任何外部持久化日志只能位于 live root family 之外且不是 evidence。

## 6. Running Health Gate

在运行期间只读检查，不重启、不修改 checkpoint：

```bash
bash <<'BASH'
set -euo pipefail
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
assert row['schema_version'] == 'stage1_6b_observer_checkpoint_v2'
assert row['run_id'] == run_id
assert row['capture_mode'] == 'live_observed'
assert row['source_profile_id'] == 'binance_public_web_bapi_en_delisting_catalog_v2'
assert (root / '.stage1_6b_writer.lock').exists()
assert not (root / 'terminal_status.json').exists(), 'STOP: root is terminal; use Section 7'
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
assert terminal['terminal_reason'] == 'epoch_complete'
exports = sorted((root / 'sealed_exports').glob('*/sealed_export_manifest.json'))
assert len(exports) == 1, exports
manifest = load_sealed_export(exports[0].parent)
assert manifest['capture_mode'] == 'live_observed'
print({'terminal_reason': terminal['terminal_reason'], 'sealed_export_id': manifest['export_id']})
PY
BASH
```

Normal completion requires `terminal_reason=epoch_complete` and creates one independent sealed evidence unit. It does not grant any PIT, market-data, replay, alpha or trading conclusion.

### 7.2 Failure terminal

```bash
bash <<'BASH'
set -euo pipefail
: "${LIVE_ROOT:?STOP: export LIVE_ROOT}"
PYTHONPATH=src:. .venv/bin/python - "$LIVE_ROOT" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
terminal = json.loads((root / 'terminal_status.json').read_text(encoding='utf-8'))
assert terminal['status'] == 'failure'
assert not list((root / 'sealed_exports').glob('*/sealed_export_manifest.json'))
print({'failure_terminal_reason': terminal['terminal_reason'], 'action': 'preserve_root_and_stop'})
PY
BASH
```

特别是 `source_profile_schema_drift`：保留 evidence，禁止 endpoint/field alias retry，另行走 source-contract Design。

### 7.3 Interrupted root and controlled resume

人工 cancellation 没有已实现的 graceful terminal handler。禁止手工写 `terminal_status.json`、删除 lock/checkpoint/attestation/raw payload 或重新创建同名 root。

只在另行明确授权后，且 root 无 terminal、无 sealed export、原 attestation SHA 与 capture contract 完全一致时，才可按既有 runner `--resume` 分支恢复。它在 client/network 前必须先写 reconciliation checkpoint：

```bash
bash <<'BASH'
set -euo pipefail
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
