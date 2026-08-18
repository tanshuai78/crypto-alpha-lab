# External Signal Shadow Lab Stage 1.5F Live Depth Observer Review

**日期:** 2026-07-01  
**对应设计:** `docs/designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md`  
**对应实现计划:** `docs/plans/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-implementation-plan_CN.md`  
**当前运行重点:** Stage 1.5D/1.5F Storage Lifecycle Resource Guard + local-only Stage 1.5G review

## 1. 当前结论

```text
decision = stage1_5d_1_5f_1_5g_storage_lifecycle_resource_guard_ready_for_commit_and_server_deployment
implementation_status = independently_audited_complete_pending_commit_and_server_deployment
current_server_mode = 7d_storage_lifecycle_resource_guard_hotfix
stage1_5g_next_action = run_after_new_12h_observation
stage1_5h_allowed = design_only_until_more_evidence
```

当前主线已经从 `Title-Symbol Launch-Anchor Validation Gate` hotfix 前移到 `Official Schedule Priority Anchor Contract V2` hotfix。当前 root 的核心目标是修复 GIGADEV 类 official schedule 与 exchangeInfo onboardDate 不一致时的 anchor precedence、root version isolation 和 1.5G lineage 判定：

```text
1. Stage 1.5D 写入 events/*.jsonl 的 launch event 必须满足 formal_event_contract_version = 2。
2. official_schedule_anchor 优先于 exchangeInfo onboardDate；exchangeInfo mismatch 只能作为 diagnostic，不能触发 pending_anchor_conflict。
3. Stage 1.5F 必须写入 observer_root_contract.json，root_mode = v2_production，且默认拒绝 v1/v2 混用。
4. Stage 1.5F 必须使用 --stage1-5d-runtime-gate，并验证 anchor_precedence_policy = official_schedule_priority_v1。
5. Stage 1.5G 必须验证 accepted/state/completed anchor lineage hash；fallback、contamination、malformed、lineage mismatch 一律 invalid。
6. Stage 1.5D/1.5F 必须使用新的 storage_lifecycle_resource_guard_hotfix output root；旧 title-symbol / multi-symbol / SKHYUSDT/SPCX/POPMART evidence root 只读保存，不改写、不补写。
7. schedule_revision transport / consumer ready，但 automatic schedule revision producer classifier 仍是后续 follow-up，不作为本次部署 blocker。
```

当前可以做：

```text
1. 按第 7 章部署 official schedule v2 1.5D/1.5F root。
2. 按第 8.3 至 8.5 检查 v2 anchor contract、root contract/version isolation 和单/multi-symbol 事件链路。
3. 等待新 post-watermark futures launch event，并在 12h observation 完成后运行 Stage 1.5G。
4. 保留旧 title-symbol / SKHYUSDT/SPCX/POPMART evidence root 作为只读历史 evidence，不再继续写入。
```

当前不能做：

```text
1. 不能声明 execution_feasibility_proven。
2. 不能声明 alpha。
3. 不能启动 paper/live trading。
4. 不能把旧事件当前盘口倒推为历史 12h entry 可成交。
5. 不能把 SKHYUSDT quarantined pass 当成 clean pass。
6. 不能基于 quarantined pass 实现 simulator、paper trading 或 live trading；只允许 write_stage1_5h_design_only。
```

## 2. Safety Boundaries

```text
scope = live_depth_observation_only
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
private_endpoint_allowed = false
api_key_allowed = false
order_endpoint_allowed = false
```

Stage 1.5F 只做一件事：消费 Stage 1.5D watermark 之后的新 `futures_contract_launch` event-symbol，并用 Binance USD-M public depth endpoint 连续记录真实盘口证据。

## 3. 后续基本计划

```text
P0: 部署并维持 storage_lifecycle_resource_guard_hotfix 1.5D/1.5F root 健康运行。
理由: 当前核心风险是 official schedule 与 exchangeInfo onboardDate 不一致时，1.5F 使用错误 anchor 或进入 pending_anchor_conflict。

P1: 等待新 root 中出现 post-watermark futures_contract_launch event-symbol。
理由: 只有由当前 formal_event_contract_version = 2 产出的 event-symbol 才有资格进入新一轮 1.5F 12h live depth observation。

P2: 一旦 1.5F 出现 post_watermark_events_accepted > 0，切换到 30-60 分钟巡检频率。
理由: 新事件后的前 12h 是证据窗口，必须确认 active_observation_count、depth_snapshots、request_success_rate 正常增长。

P3: 12h 完成后运行 Stage 1.5G review。
理由: Clean / Quarantined / Invalid 只能由 1.5G 对完整 observation root 判定。

P4: Stage 1.5H 继续保持 design-only。
理由: 单个 clean/quarantine 样本不足以放开 simulator/paper/live，更不能声明 alpha 或 execution feasibility。
```

并行可做：

```text
1. 编写 Stage 1.5H design，必须显式消费 clean/quarantined/invalid 三类 1.5G evidence。
2. 继续运行新的 1.5D/1.5F root，等待下一个 clean 或 quarantined evidence。
3. 编写 Stage 1.5D schedule revision producer rules follow-up design；该 follow-up 不阻塞 v2 root 部署。
4. 定期复核 safety grep，确保没有 private endpoint、api key、order endpoint。
```

暂不推进：

```text
1. paper trading。
2. live trading。
3. execution engine 接入。
4. alpha 结论包装。
5. Stage 1.5H simulator implementation。
```

## 4. 当前服务器路径

### 4.1 最新 hotfix 应使用的路径

每次 SSH 新窗口先设置：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_storage_lifecycle_resource_guard_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_storage_lifecycle_resource_guard_hotfix' | sort | tail -n 1)"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

最新部署后应看到：

```text
STAGE1_5D_EVENTS_OUT = data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_storage_lifecycle_resource_guard_hotfix
STAGE1_5F_OUT = data/external_signal_shadow/stage1_5f/live_depth_observer_<RUN_ID>_7d_storage_lifecycle_resource_guard_hotfix
```

### 4.2 旧路径处理规则

以下路径只用于历史排障、regression 或已完成 evidence 复核，不作为当前新部署写入路径：

```text
data/external_signal_shadow/stage1_5d/live_event_source_continuous_*_7d
data/external_signal_shadow/stage1_5d/live_event_source_continuous_*_7d_empty_detail_retry_hotfix
data/external_signal_shadow/stage1_5d/live_event_source_continuous_*_7d_title_contract_transient_hotfix
data/external_signal_shadow/stage1_5d/live_event_source_continuous_*_7d_detail_retry_scheduler_starvation_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_empty_detail_retry_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_title_contract_transient_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_request_manifest_symbol_key_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix
```

SKHYUSDT 已完成 1.5G quarantined review 的 root 必须只读保留：

```text
1.5D: data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260710T090542Z_7d_detail_retry_scheduler_starvation_hotfix
1.5F: data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix
1.5G: data/external_signal_shadow/stage1_5g/reviews/20260711T131211Z
```

规则：

```text
1. 不 rm -rf 旧 SKHYUSDT evidence root。
2. 不在旧 root 上继续启动 1.5F。
3. 不把旧 root 和新 root 的 events/depth_snapshots/request_manifest 混合审计。
4. 新 1.5D/1.5F 部署必须使用 storage_lifecycle_resource_guard_hotfix 后缀。
```

## 5. Stage 1.5F 原理速记

```text
1. Stage 1.5D = 事件源观察器，持续抓 Binance public announcement。
2. Stage 1.5F = 盘口录像机，只对 1.5D 新产出的 event-symbol 采 12h public depth。
3. bootstrap = 划起跑线，把当前已存在的旧事件写入 watermark，防止误当新事件。
4. watermark = 新旧事件边界，包含 max_seen_detected_at_ms 和 seen ids。
5. event-symbol = 一篇公告中的一个 symbol 观察对象；一篇多 symbol 公告会拆成多个观察对象。
6. depth snapshot = 一次 public orderbook 快照，用于计算 spread、top depth、500 USDT slippage proxy。
```

一句话：

```text
1.5F 是录像机，1.5G 是看片审查员。新 root 初始状态通常是在等待 post-watermark 新事件；SKHYUSDT 已完成的片子只读保留，用于 1.5H design-only。
```

## 6. Hotfix 背景

本文件记录过多轮 Stage 1.5D/1.5F hotfix。当前日常执行只以第 7 至第 9 章为准；本章只保留当前 `Official Schedule Priority Anchor Contract V2` 的背景和必须继承的前置语义。

### 6.1 当前事故模式

2026-07-31 `GRVTUSDT` 暴露出一个更高优先级问题：标题中能解析出 symbol，但 1.5D 没有 detail/launch anchor/exchangeInfo validation 就写入 event row，随后 1.5F 在 exchangeInfo 尚未可见或缺 anchor 的阶段把它 hard reject 为 `symbol_not_in_exchangeinfo`。

根因不是单个 parser 正则问题，而是跨阶段 contract 不完整：

```text
1. 1.5D title-symbol 快路径绕过了 formal launch-anchor evidence contract。
2. 1.5F 把 unanchored / legacy row 当成可 terminal reject 的正式 event。
3. symbol_not_in_exchangeinfo 被错误用作 prelaunch/recovery-window 的通用 terminal reason。
```

当前修复目标：

```text
1. 1.5D 只向 events/*.jsonl 写入 formal v2 valid event row。
2. 1.5D title-symbol event 必须进入 detail/BAPI + exchangeInfo validation 路径，并以官方公告 launch schedule 优先于 exchangeInfo onboardDate。
3. 1.5F 对 legacy/unversioned row 进入 pending_source_event_unvalidated 或 pending_launch_anchor_missing。
4. 1.5F 新 root 不再 emit symbol_not_in_exchangeinfo。
5. Stage 1.5G 必须识别 anchor lineage；anchor fallback-only 或 anchor conflicted evidence 不能输出 clean pass。
```

### 6.2 仍需继承的前置修复语义

```text
1. Multiple TradFi 标题没有完整 symbols 时，需要从 detail payload 抽取 XXXUSDT / XXXUSDC。
2. multi-symbol article 必须 all-or-none emit，不能只 emit 首个已可见 symbol。
3. BTCU/ETHU U-settled launch 不能自动拼成 BTCUUSDT / ETHUUSDT。
4. detail_contract_symbol 候选必须通过 Binance USD-M exchangeInfo 验证。
5. Stage 1.5F depth request_manifest 的 depth_snapshot rows 必须带 event_symbol_id / event_id / symbol。
6. delayed launch 事件的 age gate 使用 launch/onboard evidence，但不能绕过 watermark。
7. Stage 1.5G quarantine pass 只能进入 design-only，不能作为 execution feasibility claim。
```

部署纪律：

```text
1. 不复用旧 7d output root。
2. 不覆盖旧 events/*.jsonl。
3. hotfix 部署后启动新的 1.5D output root。
4. 对新的 1.5D root bootstrap 一个匹配的新 1.5F output root。
5. 已错过 12h 窗口的旧事件只能用于 regression / recovery_validation，不得作为 formal 12h live depth evidence。
6. 已完成 1.5G 的 evidence root 只读保留，不继续写入。
```

## 7. 部署 Runbook

本章是已审批 Stage 1.5D/1.5F hotfix 的常规 Git 部署入口；Stage 1.5G 永远不在 VPS 上执行。本次 `detail_retry_cycle_active_root_recovery_hotfix` 同时修复逻辑 retry starvation，并提供受控 active-root recovery 所需代码。

```text
current_deployment_scope = stage1_5d_detail_retry_cycle_active_root_recovery_hotfix
ordinary_new_root_suffix = 7d_detail_retry_cycle_active_root_recovery_hotfix
deployment_transport = git_commit_checkout
formal_event_contract_version = 2
anchor_precedence_policy = official_schedule_priority_v1
schedule_revision_producer_default_enabled = false
RISK_LIVE_TRADING_ENABLED = false
```

**部署边界：** 第 7.2--7.8 节创建一对全新的 D/F root，适用于常规代码部署；它不会恢复旧 root 中已经 pending 的文章。第 7.9 节是同 root active-root recovery 的单次切割规范，仍需独立的部署决策、运行时 preflight 和明确的用户授权，不能与第 7.6/7.7 节混用。

### 7.1 部署原则与数据保护

```text
1. 服务器代码只能通过 Git commit 部署；不再使用 rsync 覆盖 /root/crypto-alpha-lab 源码。
2. 每次部署都新建一个 1.5D root 和一个匹配的 1.5F root；不得复用已有 output root。
3. Git fetch / checkout 只更新受版本控制的源码。data/ 已被 .gitignore 忽略，不会被覆盖或删除。
4. 严禁在服务器执行 git clean、git reset --hard、rsync --delete 或 rm -rf 来完成部署。
5. 停止旧 tmux 只会停止进程；不会删除其 events、snapshots、state 或 1.5G 证据。
6. 新 root 的 watermark 会隔离旧事件；历史 root 只读保留，不会被新 observer 补写。
7. 后续 hotfix 继续复用本章的 Git、隔离 root、bootstrap 和检查流程；只替换经审查的 `ROOT_SUFFIX`、session 名、目标测试与新增验收字段。
```

**一次性前提：** Git Ancestry Attestation 要求服务器目录是带完整提交历史的非 shallow Git 工作树。若 `/root/crypto-alpha-lab/.git` 不存在，或 `git rev-parse --is-shallow-repository` 返回 `true`，不要继续本章；先单独完成服务器 Git 工作树迁移。不要把旧的 `rsync` 树直接当成已验证的 Git 部署树。

### 7.2 本地提交与测试门禁

在本地执行。只有工作区干净、测试通过、提交已推送后，才记录要部署的精确 SHA：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

git status --short
git diff --check

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q

# 工作区干净后，推送当前提交；DEPLOY_COMMIT 必须是本次实际部署的固定值。
git push origin HEAD
export DEPLOY_COMMIT="$(git rev-parse HEAD)"
echo "DEPLOY_COMMIT=$DEPLOY_COMMIT"
git show --no-patch --format='%H%n%s%n%ci' "$DEPLOY_COMMIT"
```

判定：`git status --short` 和 `git diff --check` 均无输出，pytest 通过，且 `git push` 成功。记录 `DEPLOY_COMMIT`，后续服务器必须 checkout 同一个 SHA，不能用不确定的“最新代码”。

### 7.3 服务器 Git 工作树与精确提交检查

在服务器同一个 SSH 窗口执行。下面的命令只读；错误只打印 `STOP`，不会关闭 SSH。

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

SERVER_GIT_READY=1
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "STOP: /root/crypto-alpha-lab is not a Git work tree. Complete the one-time Git migration first." >&2
  SERVER_GIT_READY=0
fi
if [ "$SERVER_GIT_READY" = "1" ] && [ "$(git rev-parse --is-shallow-repository)" != "false" ]; then
  echo "STOP: shallow Git history is not valid for ancestry attestation. Fetch full history before deployment." >&2
  SERVER_GIT_READY=0
fi
if [ "$SERVER_GIT_READY" = "1" ] && ! git check-ignore -q data/external_signal_shadow; then
  echo "STOP: data/ is not ignored by Git; do not checkout until this is corrected." >&2
  SERVER_GIT_READY=0
fi

git remote -v 2>/dev/null || true
git rev-parse --is-shallow-repository 2>/dev/null || true
git status --short 2>/dev/null || true
echo "SERVER_GIT_READY=$SERVER_GIT_READY"
```

若 `SERVER_GIT_READY=0`，停止部署。Git 工作树迁移是一次性基础设施动作，必须保留 `data/`、旧 `.venv/` 和所有旧 root，另行验证后再回到本章。

### 7.4 使用 Git 部署代码，不同步数据

将本地第 7.2 节记录的完整 SHA 粘贴到 `DEPLOY_COMMIT`。`git checkout` 前要求服务器源码工作区干净，避免覆盖服务器上未提交的人工改动。

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 粘贴第 7.2 节输出的精确 40 位 SHA；不得复用文档历史示例 SHA。
export DEPLOY_COMMIT="483fcc98b9741e4458f0bbe970ce587c42aaee75"
DEPLOY_READY=1

if [ "${#DEPLOY_COMMIT}" -ne 40 ]; then
  echo "STOP: DEPLOY_COMMIT must be the exact 40-character commit SHA." >&2
  DEPLOY_READY=0
fi
if [ "$DEPLOY_READY" = "1" ] && [ "$(git rev-parse --is-shallow-repository 2>/dev/null)" != "false" ]; then
  echo "STOP: non-shallow Git history is required." >&2
  DEPLOY_READY=0
fi
if [ "$DEPLOY_READY" = "1" ]; then
  git fetch origin --tags --prune
  if ! git cat-file -e "${DEPLOY_COMMIT}^{commit}" 2>/dev/null; then
    echo "STOP: DEPLOY_COMMIT is absent from this server Git history." >&2
    DEPLOY_READY=0
  fi
fi
if [ "$DEPLOY_READY" = "1" ] && [ -n "$(git status --short)" ]; then
  echo "STOP: server source worktree is dirty; inspect it instead of discarding it." >&2
  git status --short
  DEPLOY_READY=0
fi
if [ "$DEPLOY_READY" = "1" ]; then
  git checkout --detach "$DEPLOY_COMMIT"
  echo "SERVER_HEAD=$(git rev-parse HEAD)"
  git status --short
fi
echo "DEPLOY_READY=$DEPLOY_READY"
```

判定：`DEPLOY_READY=1` 且 `SERVER_HEAD` 等于 `DEPLOY_COMMIT` 才能继续。此步骤不会修改 `data/`；不要执行 `git clean`，也不要再执行旧的 `rsync -avzP ... /root/crypto-alpha-lab/` 代码同步命令。

### 7.5 启动前运行状态检查与停止旧会话

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

date -u
df -hT /
tmux ls || true
ps -efww | grep -E 'run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer' | grep -v grep || true

export ACTIVE_5F="$(ps -efww | grep run_stage1_5f_live_depth_observer | grep -v grep | sed -n 's/.*--output-root \([^ ]*\).*/\1/p' | tail -n 1)"
echo "ACTIVE_5F=[$ACTIVE_5F]"
if [ -n "$ACTIVE_5F" ] && [ -f "$ACTIVE_5F/live_depth_observer_summary.json" ]; then
  python3 - "$ACTIVE_5F/live_depth_observer_summary.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
print({k: s.get(k) for k in (
    "decision", "active_observation_count", "pending_launch_observation_count",
    "total_snapshots_collected", "last_heartbeat_at_ms", "blocker",
)})
PY
fi
```

在停止旧会话前，执行硬性存储预检。此命令只读，不会关闭 SSH：

```bash
HOST_STORAGE_READY=1
python3 - <<'PY' || HOST_STORAGE_READY=0
import shutil

free_bytes = shutil.disk_usage("/").free
minimum_bytes = 8 * 1024 * 1024 * 1024
print({"storage_free_bytes": free_bytes, "required_start_free_bytes": minimum_bytes})
assert free_bytes >= minimum_bytes, "STOP: host free space is below the mandatory 8GiB start threshold"
PY
echo "HOST_STORAGE_READY=$HOST_STORAGE_READY"
```

判定：`HOST_STORAGE_READY=1` 是启动新 root 的硬前提，不是“建议至少 5G”。若旧 observer 的 `active_observation_count > 0`，先保留该 root 并记录摘要；继续部署会中断该 root 的后续采集，但不会删除已采集数据。

确认允许停止旧会话后，**手工填入** `tmux ls` 中的两个真实 session 名；不要使用“匹配到就全部 kill”的循环：

```bash
export OLD_5D_SESSION="stage1_5d_continuous_7d_storage_lifecycle_resource_guard_hotfix"
export OLD_5F_SESSION="stage1_5f_live_depth_7d_storage_lifecycle_resource_guard_hotfix"

tmux kill-session -t "$OLD_5F_SESSION"
tmux kill-session -t "$OLD_5D_SESSION"

ps -efww | grep -E 'run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer' | grep -v grep || true
```

`ps` 仍显示旧 collector 或 observer 时，不得启动新进程。停止会话不执行任何数据删除。

### 7.6 启动新的 Stage 1.5D collector

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 本次常规新 root 部署使用该 suffix；active-root recovery 不创建新 root。
export ROOT_SUFFIX="7d_detail_retry_cycle_active_root_recovery_hotfix"
export STAGE1_5D_SESSION="stage1_5d_continuous_${ROOT_SUFFIX}"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export STAGE1_5D_EVENTS_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_${RUN_ID}_${ROOT_SUFFIX}"

D_START_READY="$HOST_STORAGE_READY"
if [ "$D_START_READY" != "1" ]; then
  echo "STOP: host storage preflight failed; do not create a new Stage 1.5D root." >&2
fi
if tmux has-session -t "$STAGE1_5D_SESSION" 2>/dev/null; then
  echo "STOP: target Stage 1.5D tmux session already exists." >&2
  D_START_READY=0
fi
if [ -e "$STAGE1_5D_EVENTS_OUT" ]; then
  echo "STOP: refuse to reuse existing Stage 1.5D root: $STAGE1_5D_EVENTS_OUT" >&2
  D_START_READY=0
fi

if [ "$D_START_READY" = "1" ]; then
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
fi

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "D_START_READY=$D_START_READY"
```

等待至少两个 poll 后检查 runtime gate。失败只会停止后续操作，不会关闭 SSH：

```bash
D_GATE_READY=1
sleep 130
python3 - "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.is_file():
    raise SystemExit(f"STOP: missing runtime gate: {p}")
else:
    g = json.loads(p.read_text())
    view = {k: g.get(k) for k in (
        "status", "decision", "consumable_by_stage1_5f", "successful_poll_count",
        "failed_poll_count", "consecutive_failed_polls",
        "formal_event_contract_versions_supported",
        "formal_schedule_revision_contract_versions_supported",
        "anchor_precedence_policy", "schedule_revision_producer_configured_enabled",
        "schedule_revision_producer_effective_enabled", "fatal_blockers",
        "storage_guard_status", "storage_free_bytes", "storage_root_bytes",
        "storage_root_scanned_at_ms", "storage_root_max_bytes", "storage_blocker",
        "storage_terminal_write_set_peak_bytes", "storage_emergency_blocker_reserve_bytes",
    )}
    print(view)
    assert g.get("status") == "READY"
    assert g.get("decision") == "stage1_5d_runtime_gate_ready"
    assert g.get("consumable_by_stage1_5f") is True
    assert g.get("fatal_blockers") in (None, [])
    assert g.get("storage_guard_status") == "ready"
    assert g.get("storage_blocker") is None
    assert int(g.get("storage_root_bytes") or -1) >= 0
    assert int(g.get("storage_root_max_bytes") or 0) > int(g.get("storage_root_bytes") or 0)
PY
if [ $? -ne 0 ]; then
  D_GATE_READY=0
fi
echo "D_GATE_READY=$D_GATE_READY"
```

仅当 `D_GATE_READY=1` 时，才继续启动 1.5F。`schedule_revision_producer_configured_enabled` 和 `schedule_revision_producer_effective_enabled` 必须保持 `false`；producer 关闭不阻断普通 launch event 采集。

### 7.7 Bootstrap 并启动新的 Stage 1.5F observer

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

# 本次常规新 root 部署使用该 suffix；active-root recovery 不创建新 root。
export ROOT_SUFFIX="7d_detail_retry_cycle_active_root_recovery_hotfix"
export STAGE1_5F_SESSION="stage1_5f_live_depth_${ROOT_SUFFIX}"
export STAGE1_5F_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_${STAGE1_5F_RUN_ID}_${ROOT_SUFFIX}"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

F_START_READY=1
if [ ! -f "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" ]; then
  echo "STOP: Stage 1.5D runtime gate is missing." >&2
  F_START_READY=0
fi
if [ "$F_START_READY" = "1" ]; then
  python3 - "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" <<'PY'
import json, sys
g = json.load(open(sys.argv[1]))
assert g.get("status") == "READY"
assert g.get("decision") == "stage1_5d_runtime_gate_ready"
assert g.get("consumable_by_stage1_5f") is True
assert g.get("fatal_blockers") in (None, [])
assert g.get("storage_guard_status") == "ready"
assert g.get("storage_blocker") is None
PY
  if [ $? -ne 0 ]; then
    echo "STOP: Stage 1.5D runtime gate is not admissible for Stage 1.5F." >&2
    F_START_READY=0
  fi
fi
if [ -e "$STAGE1_5F_OUT" ]; then
  echo "STOP: refuse to reuse existing Stage 1.5F root: $STAGE1_5F_OUT" >&2
  F_START_READY=0
fi
if tmux has-session -t "$STAGE1_5F_SESSION" 2>/dev/null; then
  echo "STOP: target Stage 1.5F tmux session already exists." >&2
  F_START_READY=0
fi
if [ ! -f "$STAGE1_5E_SUMMARY" ]; then
  echo "STOP: required Stage 1.5E summary is missing: $STAGE1_5E_SUMMARY" >&2
  F_START_READY=0
fi

if [ "$F_START_READY" = "1" ]; then
  python3 - "$STAGE1_5D_EVENTS_OUT" <<'PY'
import glob, sys
hits = sorted(glob.glob(f"{sys.argv[1]}/events/*.jsonl"))
print({"stage1_5d_events_glob_hit_count": len(hits), "tail": hits[-3:]})
assert hits, "STOP: wait for Stage 1.5D to create events/*.jsonl"
PY
  if [ $? -ne 0 ]; then
    F_START_READY=0
  fi
fi

echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
echo "F_START_READY=$F_START_READY"
```

仅当 `F_START_READY=1` 且 Python 检查通过时，建立新 watermark。bootstrap 不会采集旧事件，也不会改写旧 root：

```bash
if [ "$F_START_READY" != "1" ]; then
  echo "STOP: Stage 1.5F was not started; fix the checks above. SSH remains open." >&2
else
  if ! PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
    --stage1-5d-events-glob "$STAGE1_5D_EVENTS_OUT/events/*.jsonl" \
    --stage1-5d-runtime-gate "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" \
    --stage1-5e-summary "$STAGE1_5E_SUMMARY" \
    --output-root "$STAGE1_5F_OUT" \
    --bootstrap-watermark; then
    echo "STOP: Stage 1.5F bootstrap failed; observer tmux session was not started. SSH remains open." >&2
    F_START_READY=0
  else
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
  fi
fi

echo "F_START_READY=$F_START_READY"
```

注意：`--stage1-5d-events-glob` 必须传入未带反斜杠的 `events/*.jsonl`。传入 `events/\*.jsonl` 会使 Python 按字面量查找，1.5F 看不到任何事件文件。

### 7.8 首次部署检查

等待约 90 秒后执行。该检查同时验证 Git commit、D/F root 绑定、attestation 与基础运行状态：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

sleep 90
python3 - "$STAGE1_5D_EVENTS_OUT" "$STAGE1_5F_OUT" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root_d = Path(sys.argv[1]).resolve()
root_f = Path(sys.argv[2]).resolve()
gate = json.loads((root_d / "live_safety_gate_summary.json").read_text())
contract = json.loads((root_f / "observer_root_contract.json").read_text())
summary = json.loads((root_f / "live_depth_observer_summary.json").read_text())
root_id = hashlib.sha256(str(root_d).encode()).hexdigest()

print({
    "stage1_5d": {k: gate.get(k) for k in (
        "status", "decision", "consumable_by_stage1_5f", "successful_poll_count",
        "schedule_revision_producer_configured_enabled",
        "schedule_revision_producer_effective_enabled",
    )},
    "stage1_5f_contract": {k: contract.get(k) for k in (
        "root_mode", "source_stage1_5d_output_root_id",
        "source_stage1_5d_events_root_id", "source_stage1_5d_runtime_gate_root_id",
        "consumer_static_attestation_verified",
    )},
    "stage1_5f_summary": {k: summary.get(k) for k in (
        "decision", "stage1_5d_runtime_gate_decision",
        "consumer_runtime_attestation_verified",
        "consumer_runtime_attestation_compromised", "block_new_event_admission",
        "active_observation_count", "pending_launch_observation_count", "blocker",
        "storage_guard_status", "storage_free_bytes", "storage_root_bytes",
        "storage_root_scanned_at_ms", "storage_root_max_bytes", "storage_blocker",
        "storage_terminal_write_set_peak_bytes", "storage_emergency_blocker_reserve_bytes",
    )},
})

assert gate.get("status") == "READY"
assert gate.get("decision") == "stage1_5d_runtime_gate_ready"
assert all(contract.get(k) == root_id for k in (
    "source_stage1_5d_output_root_id",
    "source_stage1_5d_events_root_id",
    "source_stage1_5d_runtime_gate_root_id",
))
assert contract.get("consumer_static_attestation_verified") is True
assert summary.get("consumer_runtime_attestation_verified") is True
assert summary.get("consumer_runtime_attestation_compromised") is False
assert summary.get("block_new_event_admission") is False
assert summary.get("storage_guard_status") == "ready"
assert summary.get("storage_blocker") is None
assert int(summary.get("storage_root_bytes") or -1) >= 0
assert int(summary.get("storage_root_max_bytes") or 0) > int(summary.get("storage_root_bytes") or 0)
PY

ps -efww | grep run_stage1_5f_live_depth_observer | grep -v grep || true
```

正常首检：1.5D 为 `READY` / `stage1_5d_runtime_gate_ready`；三个 `source_stage1_5d_*_root_id` 全部相同且绑定新 D root；1.5F runtime attestation 为 true、`block_new_event_admission=false`。若任一断言失败，停止新会话、保留所有新旧 root，定位后再重新部署。

### 7.9 Active-Root Recovery Cutover Runbook (Non-Executable by Default)

> [!IMPORTANT]
> **Non-Executable by Default**: 本小节仅作为未来 active-root 恢复切割的操作规范文档与审计依据。实施计划与本代码库默认**不授权**自动执行切换；必须在所有代码实现、静态检查与回归验证完全闭环并经独立部署决策后，方可由操作人员手动执行。

```text
Task 0 / current-B premise evidence, before code edits:
  freeze B commit, current roots, current scheduler/event/manifest facts,
  current watermark/root contract and health only.

Deployment preflight, after implementation/completion:
  freeze exact approved C commit and fresh target/root facts again:
  article is one 32-hex value, pending/retryable/nonterminal/not emitted/in max age;
  prove no systemd/supervisord/cron/container restart policy will recreate B or generic C D/F
    (record tmux ls, ps -ef, and verify no auto-supervisor/cron recreates processes);
  D/F gates and host storage are ready; no concurrent writer; F active_observation_count=0;
  current watermark/state/root contract and B lock path are readable; C lock equals B lock.

Cutover:
  1. stop B D and B F; prove both exited; do not checkout or restart B.
  2. start D(C) exactly once, against original absolute D root, with both exact flags:
       --active-root-recovery-source-article-id=<article>
       --active-root-recovery-provenance=active_root_retry_cycle_recovery_v1
  3. record PID, started_at, full command line, C commit, article and enum in the local ledger;
     prove the running command contains both flags before accepting D READY.
  4. verify D READY, same B lock, and target continuity.
  5. start F(C) once against original absolute F root, without --bootstrap-watermark;
     verify same watermark/root/state, C process/commit, healthy attestation and unchanged D-root bindings.
  6. only then allow recovery to continue; verify any emitted target row carries the marker and F evidence is recovery-only.

If D(C) exits before the target becomes terminal or formal:
  stop; no automatic generic restart is a valid continuation; fresh deployment preflight is required;
  any new recovery invocation must repeat the exact authority pair.

Partial-cutover failure matrix:
  C D fails before root write -> stop C processes; preserve roots/ledger; do not restart B; new decision.
  C D writes scheduler state then fails -> stop C processes; preserve roots/ledger; fresh preflight.
  C D emits marked event and C F fails -> stop C D; preserve event/roots; never start old B F.
  C F starts with unhealthy attestation/binding -> stop both C processes; preserve roots/ledger; new decision.
  C pair healthy -> recovery may continue.

Always forbidden:
  bootstrap/new root, automatic B resume, marker stripping, manual state/watermark/event edits,
  manual/offline compaction before recovery, or VPS 1.5G review.
  Existing guarded automatic F startup compaction remains allowed lifecycle behavior.
```

## 8. 日常监控

### 8.1 当前 root 快速定位

每次新的 SSH 窗口先执行。优先从运行进程提取 root；没有进程时才回退到最新同后缀目录：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export ROOT_SUFFIX="7d_detail_retry_cycle_active_root_recovery_hotfix"
export STAGE1_5D_EVENTS_OUT="$(ps -efww | grep run_stage1_5d_live_event_source_smoke_collector | grep -v grep | sed -n 's/.*--output-root \([^ ]*\).*/\1/p' | tail -n 1)"
export STAGE1_5F_OUT="$(ps -efww | grep run_stage1_5f_live_depth_observer | grep -v grep | sed -n 's/.*--output-root \([^ ]*\).*/\1/p' | tail -n 1)"

if [ -z "$STAGE1_5D_EVENTS_OUT" ]; then
  export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name "live_event_source_continuous_*_${ROOT_SUFFIX}" | sort | tail -n 1)"
fi
if [ -z "$STAGE1_5F_OUT" ]; then
  export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name "live_depth_observer_*_${ROOT_SUFFIX}" | sort | tail -n 1)"
fi

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

### 8.2 一条命令看健康状态

```bash
python3 - "$STAGE1_5D_EVENTS_OUT" "$STAGE1_5F_OUT" <<'PY'
import json, sys
from pathlib import Path

def load(root, name):
    p = Path(root) / name
    return json.loads(p.read_text()) if p.is_file() else {"missing": str(p)}

g = load(sys.argv[1], "live_safety_gate_summary.json")
s = load(sys.argv[2], "live_depth_observer_summary.json")
print({
    "stage1_5d": {k: g.get(k) for k in (
        "status", "decision", "successful_poll_count", "failed_poll_count",
        "consecutive_failed_polls", "consumable_by_stage1_5f", "fatal_blockers",
        "storage_guard_status", "storage_free_bytes", "storage_root_bytes",
        "storage_root_max_bytes", "storage_root_scanned_at_ms", "storage_blocker",
        "storage_terminal_write_set_peak_bytes", "storage_emergency_blocker_reserve_bytes",
    )},
    "stage1_5f": {k: s.get(k) for k in (
        "decision", "post_watermark_events_accepted", "active_observation_count",
        "pending_launch_observation_count", "pending_launch_time_in_future_count",
        "pending_launch_anchor_missing_count", "pending_anchor_conflict_count",
        "pending_observation_capacity_count", "block_new_event_admission", "blocker",
        "storage_guard_status", "storage_free_bytes", "storage_root_bytes",
        "storage_root_max_bytes", "storage_root_scanned_at_ms", "storage_blocker",
        "storage_terminal_write_set_peak_bytes", "storage_emergency_blocker_reserve_bytes",
    )},
})
PY
```

正常：1.5D `decision=stage1_5d_runtime_gate_ready`、`storage_guard_status=ready`、连续失败为 `0`；1.5F `storage_guard_status=ready`、`block_new_event_admission=false`、`storage_blocker=null`、`blocker=null`。任一 guard 状态非 `ready`、root bytes 达到 root max、或出现 storage blocker 时，停止对应会话、保留 root 与 `storage_failure_diagnostic.json`，不得原地重启或删除数据。没有新事件时，accepted、active、pending 均为 `0` 是正常结果。

### 8.3 事件流和 root 绑定快速检查

```bash
python3 - "$STAGE1_5D_EVENTS_OUT" "$STAGE1_5F_OUT" <<'PY'
import glob
import hashlib
import json
import sys
from pathlib import Path

root_d = Path(sys.argv[1]).resolve()
root_f = Path(sys.argv[2]).resolve()
events = sorted(glob.glob(str(root_d / "events" / "*.jsonl")))
contract = json.loads((root_f / "observer_root_contract.json").read_text())
root_id = hashlib.sha256(str(root_d).encode()).hexdigest()
keys = (
    "source_stage1_5d_output_root_id",
    "source_stage1_5d_events_root_id",
    "source_stage1_5d_runtime_gate_root_id",
)
print({
    "events_glob_hit_count": len(events),
    "events_glob_tail": events[-3:],
    "root_binding_ok": all(contract.get(k) == root_id for k in keys),
    "root_binding_values": {k: contract.get(k) for k in keys},
})
PY

ps -efww | grep run_stage1_5f_live_depth_observer | grep -v grep || true
```

必须看到 `events_glob_hit_count > 0` 和 `root_binding_ok=true`。进程命令行中不得出现字面量 `events/\*.jsonl`。

### 8.4 新公告的状态语义检查

设置公告内的一个或多个 symbol；逗号、空格和分号均可分隔。命令只显示每个 symbol 的最后一条 durable state，避免刷屏：

```bash
export SYMBOLS="替换为目标，例如 AAAUSDT BBBUSDT"

python3 - "$STAGE1_5F_OUT" <<'PY'
import json
import os
import sys
from pathlib import Path

symbols = {s for raw in os.environ.get("SYMBOLS", "").replace(";", ",").split(",") for s in raw.split() if s}
latest = {}
p = Path(sys.argv[1]) / "observer_state.jsonl"
for line in p.read_text().splitlines() if p.is_file() else []:
    row = json.loads(line)
    if row.get("symbol") in symbols:
        latest[row["symbol"]] = row
for symbol in sorted(symbols):
    row = latest.get(symbol, {})
    print(symbol, {k: row.get(k) for k in (
        "status", "pending_reason", "pending_terminal_reason", "rejected_reason",
        "observation_anchor_ms", "anchor_resolution_deadline_ms",
        "next_anchor_resolution_at_ms", "next_admission_check_at_ms",
    )})
PY
```

本 hotfix 的重点判读：

```text
有效 future anchor：
status = pending_launch_time_in_future
anchor_resolution_deadline_ms = null
next_anchor_resolution_at_ms 非 null
next_admission_check_at_ms = observation_anchor_ms + guard

官方取消 revision：
status = pending_cancelled
pending_reason = official_schedule_cancelled
pending_terminal_reason = ""
observation_anchor_ms / next_anchor_resolution_at_ms / next_admission_check_at_ms 均为 null
且该 symbol 不计入 pending_launch_observation_count。

缺失或冲突 anchor：仍按既有 fail-closed 规则在 6h deadline 后进入相应 terminal rejection。
```

### 8.5 停止当前新 root

停止仅停止进程，所有 output root 和历史数据均保留：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export ROOT_SUFFIX="7d_detail_retry_cycle_active_root_recovery_hotfix"
tmux kill-session -t "stage1_5f_live_depth_${ROOT_SUFFIX}" 2>/dev/null || true
tmux kill-session -t "stage1_5d_continuous_${ROOT_SUFFIX}" 2>/dev/null || true

ps -efww | grep -E 'run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer' | grep -v grep || true
```

停止前若 `active_observation_count > 0`，先保存第 8.2 节输出；之后需要新的代码部署时，重复第 7 章并创建新的 root，不删除本 root。

## 9. 新事件定位与排障

本章只保留当前 `storage_lifecycle_resource_guard_hotfix` root 的必要排障命令。旧 BAPI table / endpoint fallback / starvation 专项命令不再放在日常 runbook 主体中，历史语义见第 12 章索引。

### 9.1 查看 1.5F watermark 时间

```bash
python3 - <<'PY'
import json, os
from datetime import datetime, timezone
from pathlib import Path

p = Path(os.environ["STAGE1_5F_OUT"]) / "watermark.json"
if not p.exists():
    print("watermark_missing", p)
    raise SystemExit(0)
w = json.loads(p.read_text())
ms = w.get("max_seen_detected_at_ms", 0)
print("watermark_path", p)
print("max_seen_detected_at_ms", ms)
print("utc_time", datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat() if ms else "0 / not initialized")
print("seen_event_ids", len(w.get("seen_event_ids", [])))
print("seen_source_article_ids", len(w.get("seen_source_article_ids", [])))
print("seen_stable_event_keys", len(w.get("seen_stable_event_keys", [])))
PY
```

### 9.2 按文章或 symbol 定位完整链路

发现官网新公告时，优先用这条单命令检查 1.5D scheduler、1.5D formal event、1.5F accepted/rejected/state 三层，不要先贴大量 `grep -R` 输出。

```bash
export ARTICLE_ID="替换为公告 article id"
export SYMBOLS=""  # 可选；single-symbol 填 GRVTUSDT，multi-symbol 填 PYPLUSDT,GSUSDT,SMHUSDT；空值只按 ARTICLE_ID 匹配

python3 - <<'PY'
import json, os
from pathlib import Path

article = os.environ.get("ARTICLE_ID", "").strip()
symbols = [
    s.strip()
    for raw in os.environ.get("SYMBOLS", "").replace(";", ",").split(",")
    for s in raw.split()
    if s.strip()
]
root_d = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
root_f = Path(os.environ["STAGE1_5F_OUT"])

def match(line: str) -> bool:
    return bool((article and article in line) or any(s in line for s in symbols))

out = {"article": article, "symbols": symbols}

scheduler = root_d / "detail_retry_scheduler_state.json"
st = {}
if scheduler.exists():
    data = json.loads(scheduler.read_text())
    st = data.get("articles", {}).get(article) or data.get(article) or {}
out["stage1_5d_scheduler_present"] = bool(st)
out["stage1_5d_scheduler_status"] = {k: st.get(k) for k in [
    "candidate_symbols", "symbol_validation_status", "pending_reason",
    "detail_fetch_status", "detail_fetch_attempt_count", "last_bapi_detail_status",
    "last_bapi_parser_status", "symbol_launch_times_ms", "symbol_effective_launch_times_ms",
    "symbol_onboard_times_ms", "terminal_failure_type",
]}

hits = []
for p in sorted((root_d / "events").glob("*.jsonl")):
    for line in p.read_text().splitlines():
        if match(line):
            hits.append(json.loads(line))
out["stage1_5d_event_hits"] = len(hits)
out["stage1_5d_last_event"] = hits[-1] if hits else None

for name, subdir in [("accepted", "events_accepted"), ("rejected", "events_rejected")]:
    rows = []
    for p in sorted((root_f / subdir).glob("*.jsonl")):
        for line in p.read_text().splitlines():
            if match(line):
                rows.append(json.loads(line))
    out[f"stage1_5f_{name}_hits"] = len(rows)
    out[f"stage1_5f_last_{name}"] = rows[-1] if rows else None

state_rows = []
state_path = root_f / "observer_state.jsonl"
if state_path.exists():
    for line in state_path.read_text().splitlines():
        if match(line):
            state_rows.append(json.loads(line))
out["stage1_5f_state_hits"] = len(state_rows)
out["stage1_5f_last_state"] = state_rows[-1] if state_rows else None

print(json.dumps(out, ensure_ascii=False, indent=2))
PY
```

### 9.3 当前 root 判读标准

```text
正常等待:
  1.5D scheduler_present = true，状态为 pending_*，events 尚无 formal row。
  说明 detail / exchangeInfo / launch anchor 尚未满足 formal contract，继续等待。

正常 emit:
  1.5D event row 存在，formal_event_contract_version = 2，source_contract_status = formal_v2_valid。
  anchor_precedence_policy = official_schedule_priority_v1。
  launch_anchor_evidence_level 优先为 official_schedule 或 official_schedule_confirmed_by_exchangeinfo。
  说明 1.5D 已产出当前 v2 1.5F root 可消费 row。

正常 1.5F pending:
  1.5F state 为 pending_launch_time_in_future / pending_observation_capacity / pending_exchangeinfo_*。
  说明 1.5F 没有误杀，继续按 anchor/window 等待。

异常:
  1.5D event row 缺 formal_event_contract_version。
  1.5D event row source_contract_status != formal_v2_valid。
  1.5D event row 缺 anchor_precedence_policy = official_schedule_priority_v1。
  1.5D 对有官方 launch time 的公告只写 exchangeInfo onboardDate 为 effective anchor。
  1.5F events_rejected 出现 symbol_not_in_exchangeinfo。
  1.5F --stage1-5d-events-glob 被展开成 events/YYYY-MM-DD.jsonl。
```


## 10. Stage 1.5G / Stage 1.5H 衔接

SKHYUSDT 已完成一轮 12h Stage 1.5F observation，并通过 Stage 1.5G quarantine-aware review：

```text
decision = stage1_5g_depth_evidence_quarantined_pass
allowed_next_action = write_stage1_5h_design_only
clean_depth_evidence_pass = false
quarantined_depth_evidence_pass = true
quarantine_candidate = true
execution_feasibility_claim_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

这意味着：

```text
1. 可以写 Stage 1.5H design。
2. 1.5H design 必须明确区分 clean / quarantined / invalid depth evidence。
3. 1.5H design 必须把 invalid book quarantine 后的 book_availability_ratio 作为 execution availability discount。
4. 不能直接实现 Stage 1.5H simulator。
5. 不能声明 execution feasibility，更不能进入 paper/live。
```

### 10.1 SPCXUSD1 Stage 1.5G clean evidence 主结论（2026-07-22）

SPCXUSD1 已完成一轮 12h Stage 1.5F observation，并在 2026-07-22 Stage 1.5G review 中得到 clean pass：

```text
stage1_5g_review_summary = data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json
stage1_5g_review_markdown = docs/reviews/2026-07-22-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md

decision = stage1_5g_depth_evidence_clean_pass
allowed_next_action = write_stage1_5h_design_or_shadow_simulator_design
clean_depth_evidence_pass = true
quarantined_depth_evidence_pass = false
quarantine_candidate = false
formal_announcement_and_launch_count = 1
invalid_book_row_count = 0
book_availability_ratio = 0.9986111111111111
depth_quality_clean_mode_available = true
depth_quality_quarantined_mode_available = false
blockers = []
```

本结论取代前期关于 SPCXUSD1 只能作为 recovery/probe/regression candidate 的临时判断。当前应把 SPCXUSD1 作为 Stage 1.5G clean evidence 主样本只读保留。

这证明：

```text
1. Stage 1.5D delayed-launch / pending_pre_trading handoff 路径可工作。
2. Stage 1.5F 能在合约上线后完成 12h live public depth observation。
3. Stage 1.5G quarantine-aware reviewer 对该样本给出 clean pass，不需要 quarantine。
4. 1.5D -> 1.5F -> 1.5G 的 formal announcement_and_launch_time depth evidence 链路跑通。
```

这仍不证明：

```text
alpha；
execution feasibility；
maker-first fill rate；
entry/exit rule；
paper/live trading readiness。
```

允许的下一步是编写 Stage 1.5H clean-input design / shadow simulator design plan；不允许直接接入 paper/live 或声明执行可行性。

后续新 root 完成 12h observation 后，**只在本地工作站**运行 Stage 1.5G。VPS 只允许读取和传输完整的 1.5F evidence；不得在 VPS 上执行 `review_stage1_5g_live_depth_evidence.py`。

在本地工作站执行。先填写服务器上已完成的 1.5F root 绝对路径；这不会修改 VPS 或原始 root：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
source .venv/bin/activate

export SERVER="root@47.82.4.85"
export REMOTE_STAGE1_5F_OUT="/root/crypto-alpha-lab/替换为已完成的 live_depth_observer root"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export LOCAL_EVIDENCE_ROOT="$PWD/data/external_signal_shadow/local_evidence/${RUN_ID}_stage1_5f"
export STAGE1_5G_OUT="$PWD/data/external_signal_shadow/stage1_5g/reviews/${RUN_ID}_local"

mkdir -p "$LOCAL_EVIDENCE_ROOT"
# A complete F root is bounded to 2GiB and avoids missing optional-directory errors.
rsync -aP --partial "$SERVER:$REMOTE_STAGE1_5F_OUT/" "$LOCAL_EVIDENCE_ROOT/"

find "$LOCAL_EVIDENCE_ROOT" -type f -exec shasum -a 256 {} \; | sort > "$LOCAL_EVIDENCE_ROOT/SHA256SUMS"
wc -l "$LOCAL_EVIDENCE_ROOT/observer_state.jsonl"
```

同步完成后仍在本地执行 review。`STAGE1_5G_OUT` 是本地生成物，不提交、不回传 VPS：

```bash
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  --stage1-5f-output-root "$LOCAL_EVIDENCE_ROOT" \
  --output-root "$STAGE1_5G_OUT" \
  --output-summary "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review_summary.json" \
  --output-review "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review.md"
```

判定：

```text
stage1_5g_depth_evidence_clean_pass -> 可写 1.5H design / shadow simulator design plan，但仍不能 paper/live。
stage1_5g_depth_evidence_quarantined_pass -> 只允许 write_stage1_5h_design_only。
stage1_5g_depth_evidence_invalid -> continue_observation。
```

## 11. 历史问题索引

以下历史问题已不再作为当前日常 runbook 的执行章节。保留本索引是为了定位旧 root、旧 review 和旧 design 的上下文；当前部署、监控、停止、1.5G review 一律以第 7 至第 9 章为准。

| 日期 | 问题 | 当前状态 | 是否保留日常命令 |
| --- | --- | --- | --- |
| 2026-07-02 | Binance detail `HTTP 202 + empty body` 被误当成功 payload | 已由 transient/backoff/fallback 语义修复 | 否 |
| 2026-07-02 | ETHUSD1 / raw contract symbol 解析覆盖不足 | 已由 title-contract transient hotfix 修复 | 否 |
| 2026-07-03 | delayed launch 被 `detected_at_ms` age gate 误拒 | 已由 launch/onboard anchor gate 修复 | 否 |
| 2026-07-06 | Stage 1.5F request_manifest 缺 symbol key | 已修复，当前只保留 symbol-key 不变量 | 否 |
| 2026-07-10 | Stage 1.5D detail retry scheduler starvation | 已修复，当前只保留 retry/scheduler 状态摘要 | 否 |
| 2026-07-11 | detail endpoint degraded retry cadence + fallback | 已修复，当前由 runtime gate + manifest 摘要覆盖 | 否 |
| 2026-07-18 | TRADIFI_PERPETUAL false negative | 已修复，当前由 exchangeInfo identity validation 覆盖 | 否 |
| 2026-07-18 | delayed-launch watermark / evidence label | 已修复，当前由 formal contract + 1.5F pending state 覆盖 | 否 |
| 2026-07-21 | f434 Multiple TradFi missed-event / overdue starvation | 已修复，当前由 all-or-none + formal event contract 覆盖 | 否 |
| 2026-07-29 | multi-symbol partial emit / admission dedupe | 已修复，但 stable identity collision 检查仍保留在 8.6 | 是，压缩保留 |
| 2026-07-31 | GRVT title-only unanchored emit + 1.5F premature reject | 当前主线修复目标，检查保留在 8.3 至 8.5 | 是 |

历史 root 处理规则：

```text
1. 旧 root 默认只读，不继续写入。
2. 已同步或已确认无审计价值的旧 root 可以从服务器删除以释放磁盘。
3. 旧 root 不能补成新的 clean 12h live depth evidence。
4. 历史问题复盘需要时，从 Git 历史、docs/designs、docs/plans、docs/reviews 对应日期文件中查找，不再在本 runbook 维护重复命令。
```

当前必须长期保留的安全不变量：

```text
1. 1.5D 写入 events/*.jsonl 的 launch row 必须通过 formal v2 contract。
2. 1.5F 必须使用 --stage1-5d-runtime-gate。
3. 1.5F 不得从旧 --stage1-5d-summary 跨 root 放行新 admission。
4. 1.5F 不得在新 root emit symbol_not_in_exchangeinfo。
5. stable_event_symbol_key collision 必须阻断 admission。
6. active observation 运行中不得随意重启 1.5F。
7. Stage 1.5G clean/quarantine/invalid 只评价 evidence，不放开 paper/live/execution/alpha。
8. 1.5D/1.5F 必须使用 StorageGuard TCB fail-closed 资源保护，严格遵守 30GB VPS 容量上限与 8GiB/4GiB 宿主机/根目录空闲保留。
9. 1.5F 状态与批次注册表必须使用 2-pass streaming physical-last 压缩与 PID 作用域原子写入，禁止产生 .bak 文件。
10. 所有持久化落盘操作必须显式使用 Python 标准库 fcntl.flock 进程锁，拒绝第三方数据库与未受保护的直接写盘。


```
