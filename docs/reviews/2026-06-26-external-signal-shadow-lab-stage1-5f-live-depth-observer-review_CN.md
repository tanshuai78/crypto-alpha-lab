# External Signal Shadow Lab Stage 1.5F Live Depth Observer Review

**日期:** 2026-07-01  
**对应设计:** `docs/designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md`  
**对应实现计划:** `docs/plans/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-implementation-plan_CN.md`  
**当前运行重点:** Stage 1.5D/1.5F Official Schedule Priority Anchor Contract V2 + Stage 1.5F root contract/version isolation + Stage 1.5G anchor lineage invalidation

## 1. 当前结论

```text
decision = stage1_5d_1_5f_official_schedule_priority_v2_ready_for_server_deployment
implementation_status = completed_locally_verified_committed_pending_server_deployment
current_server_mode = 7d_official_schedule_anchor_contract_v2_hotfix
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
6. Stage 1.5D/1.5F 必须使用新的 official_schedule_anchor_contract_v2_hotfix output root；旧 title-symbol / multi-symbol / SKHYUSDT/SPCX/POPMART evidence root 只读保存，不改写、不补写。
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
P0: 部署并维持 official_schedule_anchor_contract_v2_hotfix 1.5D/1.5F root 健康运行。
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

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

最新部署后应看到：

```text
STAGE1_5D_EVENTS_OUT = data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_official_schedule_anchor_contract_v2_hotfix
STAGE1_5F_OUT = data/external_signal_shadow/stage1_5f/live_depth_observer_<RUN_ID>_7d_official_schedule_anchor_contract_v2_hotfix
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
4. 新 1.5D/1.5F 部署必须使用 official_schedule_anchor_contract_v2_hotfix 后缀。
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

本章为当前 `official_schedule_anchor_contract_v2_hotfix` 主流程。旧 `title_symbol_launch_anchor_validation_gate_hotfix` root 只保留为历史排障对象，不再作为新部署目标。

```text
current_deployment_scope = stage1_5d_1_5f_official_schedule_priority_anchor_contract_v2_hotfix
root_suffix = 7d_official_schedule_anchor_contract_v2_hotfix
formal_event_contract_version = 2
anchor_precedence_policy = official_schedule_priority_v1
formal_schedule_revision_contract_version = 1
schedule_revision_transport_and_consumer_ready = true
automatic_schedule_revision_producer_ready = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

### 7.1 本地部署前门禁

在本地执行，确认本次提交已存在且工作区没有未提交代码：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

git status --short
git log --oneline -3

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_historical_anchor_rejection_hygiene.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_stage1_5f_deployment_checklist.py -q

git diff --check
```

判定标准：

```text
1. git status --short 为空，或只有明确不提交的本地临时文件。
2. targeted Stage 1.5D/F/G suite 通过。
3. git diff --check 无输出。
4. 最新 commit SHA 已记录，后续服务器 SHA256 对比使用该源码状态。
```

### 7.2 服务器部署前检查

在服务器执行，确认磁盘、旧进程、旧 active observation 状态：

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
  cat "$ACTIVE_5F/live_depth_observer_summary.json" | python3 -m json.tool | grep -E \
  '"decision"|"active_observation_count"|"pending_launch_observation_count"|"total_snapshots_collected"|"last_heartbeat_at_ms"|"blocker"'
fi
```

判定标准：

```text
1. / 可用空间建议 >= 5G；低于 3G 先清理旧 root，不要同步部署。
2. 如果旧 1.5F active_observation_count > 0，应先记录 evidence；除非用户明确接受中断，否则不要直接 kill。
3. 没有 active observation 时，可以进入新 root 部署。
```

### 7.3 本地同步到服务器

本次使用 repo root 安全同步，并排除服务器 `data/`、`.venv/`、`.git/` 和缓存目录，避免破坏运行证据与虚拟环境。

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export SERVER=root@47.82.4.85

rsync -avzP \
  --exclude='data' \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='.ruff_cache' \
  --exclude='.pytest_cache' \
  --exclude='__pycache__' \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/ \
  "$SERVER:/root/crypto-alpha-lab/"
```

如果前面的 repo root 同步中断，且只需要补同步本次 design/plan，可单独执行：

```bash
rsync -avzP --relative \
  docs/designs/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-launch-time-priority-anchor-precedence-hotfix-design_CN.md \
  docs/plans/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-schedule-priority-anchor-contract-v2-hotfix-implementation-plan_CN.md \
  "$SERVER:/root/crypto-alpha-lab/"
```

### 7.4 服务器 SHA256 和最小测试

本地生成关键文件 SHA256：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
shasum -a 256 \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py \
  src/research/external_signal_shadow/stage1_5_launch_event_contract.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
```

服务器对比同一批文件：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

sha256sum \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py \
  src/research/external_signal_shadow/stage1_5_launch_event_contract.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_stage1_5f_deployment_checklist.py -q
```

判定标准：

```text
1. 本地和服务器关键文件 SHA256 一致。
2. 服务器最小 Stage 1.5D/F v2 suite 通过。
3. 不通过时不要启动新 root。
```

### 7.5 停止旧 Stage 1.5D / 1.5F 进程

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

tmux ls || true
ps -efww | grep -E 'run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer' | grep -v grep || true

# 停止当前及历史 1.5F observer session。
tmux kill-session -t stage1_5f_live_depth_7d_official_schedule_anchor_contract_v2_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_title_symbol_launch_anchor_validation_gate_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_multisymbol_all_or_none_admission_dedupe_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_bapi_table_runtime_gate_hotfix 2>/dev/null || true

# 停止当前及历史 1.5D collector session。
tmux kill-session -t stage1_5d_continuous_7d_official_schedule_anchor_contract_v2_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5d_continuous_7d_title_symbol_launch_anchor_validation_gate_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5d_continuous_7d_multisymbol_all_or_none_admission_dedupe_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5d_continuous_7d_bapi_table_runtime_gate_hotfix 2>/dev/null || true

# 兜底：按当前 tmux 中真实 session 名停止所有 1.5D/1.5F 会话。
for s in $(tmux ls 2>/dev/null | awk -F: '/stage1_5d|stage1_5f/ {print $1}'); do
  echo "killing $s"
  tmux kill-session -t "$s"
done

ps -efww | grep -E 'run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer' | grep -v grep || true
```

如果 `ps` 仍显示旧 collector/observer，先不要继续启动新进程。

### 7.6 启动 Stage 1.5D official schedule v2 collector

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

if tmux has-session -t stage1_5d_continuous_7d_official_schedule_anchor_contract_v2_hotfix 2>/dev/null; then
  echo "ERROR: Stage 1.5D v2 tmux session already exists; do not create a new empty root." >&2
  ps -efww | grep '.venv/bin/python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py' | grep -v grep || true
  exit 1
fi

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
export STAGE1_5D_EVENTS_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_${RUN_ID}_7d_official_schedule_anchor_contract_v2_hotfix"

if [ -e "$STAGE1_5D_EVENTS_OUT" ]; then
  echo "Refuse to overwrite existing STAGE1_5D_EVENTS_OUT=$STAGE1_5D_EVENTS_OUT" >&2
  exit 1
fi
mkdir -p "$STAGE1_5D_EVENTS_OUT"

tmux new -d -s stage1_5d_continuous_7d_official_schedule_anchor_contract_v2_hotfix "
cd /root/crypto-alpha-lab &&
source .venv/bin/activate &&
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-root '$STAGE1_5D_EVENTS_OUT' \
  --output-summary '$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json' \
  --poll-interval-sec 60 \
  --max-seconds 604800 \
  --live-public-readonly
"

sleep 2
export ACTUAL_STAGE1_5D_EVENTS_OUT="$(
  ps -efww \
    | grep '.venv/bin/python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py' \
    | grep -v grep \
    | tail -n 1 \
    | tr ' ' '\n' \
    | awk 'prev=="--output-root"{print; exit}{prev=$0}'
)"

if [ "$ACTUAL_STAGE1_5D_EVENTS_OUT" != "$STAGE1_5D_EVENTS_OUT" ]; then
  echo "ERROR: Stage 1.5D actual output root mismatch." >&2
  echo "EXPECTED=[$STAGE1_5D_EVENTS_OUT]" >&2
  echo "ACTUAL=[$ACTUAL_STAGE1_5D_EVENTS_OUT]" >&2
  exit 1
fi

echo "STAGE1_5D_EVENTS_OUT=$STAGE1_5D_EVENTS_OUT"
```

等待 startup gate 生成，再等 1 到 2 个 poll。`live_safety_gate_summary.json` 在 1.5D 进入主循环前就应先写入 `INITIALIZING`；如果 30 秒内不存在，优先检查 tmux pane 和进程命令行，不要继续启动 1.5F。

```bash
for i in $(seq 1 30); do
  if [ -f "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" ]; then
    break
  fi
  sleep 1
done

if [ ! -f "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" ]; then
  echo "ERROR: Stage 1.5D runtime gate missing: $STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" >&2
  echo "=== tmux ===" >&2
  tmux ls 2>&1 >&2 || true
  echo "=== process ===" >&2
  ps -efww | grep run_stage1_5d_live_event_source_smoke_collector | grep -v grep >&2 || true
  echo "=== output root files ===" >&2
  find "$STAGE1_5D_EVENTS_OUT" -maxdepth 2 -type f 2>/dev/null | sort | head -n 80 >&2 || true
  echo "=== tmux pane tail ===" >&2
  tmux capture-pane -pt stage1_5d_continuous_7d_official_schedule_anchor_contract_v2_hotfix -S -200 2>&1 >&2 || true
  exit 1
fi

sleep 90

cat "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" \
  | python3 -m json.tool | grep -E \
'"decision"|"consumable_by_stage1_5f"|"successful_poll_count"|"failed_poll_count"|"consecutive_failed_polls"|"live_public_readonly"|"formal_event_contract_versions_supported"|"formal_schedule_revision_contract_versions_supported"|"anchor_precedence_policy"|"shared_anchor_validator_enabled"|"trade_signal_allowed"|"paper_trading_allowed"|"live_trading_allowed"|"execution_engine_allowed"|"alpha_interpretation_allowed"|"fatal_blockers"'
```

判定标准：

```text
正常: decision = stage1_5d_runtime_gate_ready。
正常: consumable_by_stage1_5f = true。
正常: formal_event_contract_versions_supported 包含 2。
正常: formal_schedule_revision_contract_versions_supported 包含 1。
正常: anchor_precedence_policy = official_schedule_priority_v1。
正常: shared_anchor_validator_enabled = true。
正常: fatal_blockers = []。
正常: trade_signal_allowed / paper_trading_allowed / live_trading_allowed / execution_engine_allowed / alpha_interpretation_allowed 均为 false。
异常: runtime gate 文件不存在、decision 非 ready、fatal_blockers 非空时，不得启动新 1.5F。
```

### 7.7 Bootstrap 新 Stage 1.5F watermark

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

mkdir -p data/external_signal_shadow/stage1_5e/execution_feasibility

if [ ! -f data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json ]; then
  cp "$(find data/external_signal_shadow/stage1_5e -type f -name execution_feasibility_audit_summary.json | sort | tail -n 1)" \
    data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
fi

export STAGE1_5D_EVENTS_OUT="$(
  ps -efww \
    | grep '.venv/bin/python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py' \
    | grep -v grep \
    | tail -n 1 \
    | tr ' ' '\n' \
    | awk 'prev=="--output-root"{print; exit}{prev=$0}'
)"
if [ -z "$STAGE1_5D_EVENTS_OUT" ]; then
  export STAGE1_5D_EVENTS_OUT="$(
    find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d \
      -name 'live_event_source_continuous_*_7d_official_schedule_anchor_contract_v2_hotfix' \
      -exec sh -c 'test -f "$1/live_safety_gate_summary.json"' sh {} \; -print \
      | sort | tail -n 1
  )"
fi
STAGE1_5F_RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_${STAGE1_5F_RUN_ID}_7d_official_schedule_anchor_contract_v2_hotfix"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

BOOTSTRAP_READY=1
if [ -z "$STAGE1_5D_EVENTS_OUT" ] || [ ! -d "$STAGE1_5D_EVENTS_OUT" ]; then
  echo "Missing STAGE1_5D_EVENTS_OUT" >&2
  BOOTSTRAP_READY=0
fi
if [ -e "$STAGE1_5F_OUT" ]; then
  echo "Refuse to overwrite existing STAGE1_5F_OUT=$STAGE1_5F_OUT" >&2
  BOOTSTRAP_READY=0
fi
if [ ! -f "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" ]; then
  echo "Missing Stage 1.5D runtime gate" >&2
  BOOTSTRAP_READY=0
fi

if [ "$BOOTSTRAP_READY" = "1" ]; then
  python3 - <<'PY'
import glob
import os
root = os.environ["STAGE1_5D_EVENTS_OUT"]
hits = sorted(glob.glob(f"{root}/events/*.jsonl"))
print("stage1_5d_events_glob_hit_count", len(hits))
print("stage1_5d_events_glob_tail", hits[-5:])
if not hits:
    raise SystemExit("ERROR: Stage 1.5D events/*.jsonl has no hit; wait for collector first poll")
PY
  if [ $? -ne 0 ]; then
    BOOTSTRAP_READY=0
  fi
fi

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"

if [ "$BOOTSTRAP_READY" != "1" ]; then
  echo "STOP: fix the checks above before bootstrap. This command block did not close SSH." >&2
else
  PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
    --stage1-5d-events-glob "$STAGE1_5D_EVENTS_OUT/events/*.jsonl" \
    --stage1-5d-runtime-gate "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" \
    --stage1-5e-summary "$STAGE1_5E_SUMMARY" \
    --output-root "$STAGE1_5F_OUT" \
    --bootstrap-watermark

  cat "$STAGE1_5F_OUT/observer_root_contract.json" | python3 -m json.tool | grep -E \
  '"root_mode"|"formal_event_contract_versions_allowed"|"formal_schedule_revision_contract_versions_allowed"|"anchor_precedence_policy"|"created_at_ms"'
  cat "$STAGE1_5F_OUT/watermark.json" | python3 -m json.tool
  cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" | python3 -m json.tool | grep -E \
  '"decision"|"stage1_5d_gate_mode"|"stage1_5d_runtime_gate_decision"|"cross_root_upstream_summary_dependency"|"block_new_event_admission"|"max_seen_detected_at_ms"|"blocker"'
fi
```

bootstrap 只建立新 root 的启动边界，不产生正式 live depth evidence。

### 7.8 启动新 Stage 1.5F observer

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

if [ -z "$STAGE1_5D_EVENTS_OUT" ] || [ -z "$STAGE1_5F_OUT" ]; then
  echo "Missing STAGE1_5D_EVENTS_OUT or STAGE1_5F_OUT" >&2
  exit 1
fi

tmux new -d -s stage1_5f_live_depth_7d_official_schedule_anchor_contract_v2_hotfix "
cd /root/crypto-alpha-lab &&
source .venv/bin/activate &&
STAGE1_5D_EVENTS_OUT='$STAGE1_5D_EVENTS_OUT' &&
STAGE1_5E_SUMMARY='$STAGE1_5E_SUMMARY' &&
STAGE1_5F_OUT='$STAGE1_5F_OUT' &&
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob '$STAGE1_5D_EVENTS_OUT/events/*.jsonl' \
  --stage1-5d-runtime-gate '$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json' \
  --stage1-5e-summary '$STAGE1_5E_SUMMARY' \
  --output-root '$STAGE1_5F_OUT' \
  --live-public-readonly
"
```

注意：`--stage1-5d-events-glob` 必须让 Python 收到未转义的 `events/*.jsonl`。不要写成带反斜杠的 glob；带反斜杠会被 Python `glob.glob()` 当成字面量，匹配不到任何 `events/YYYY-MM-DD.jsonl`。

### 7.9 部署后首次检查

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"

date -u
tmux ls
ps -efww | grep -E 'run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer' | grep -v grep

python3 - <<'PY'
import glob
import os
import subprocess

root = os.environ["STAGE1_5D_EVENTS_OUT"]
pattern = f"{root}/events/*.jsonl"
hits = sorted(glob.glob(pattern))
print("stage1_5d_events_glob_pattern", pattern)
print("stage1_5d_events_glob_hit_count", len(hits))
print("stage1_5d_events_glob_tail", hits[-5:])
if not hits:
    raise SystemExit("ERROR: Stage 1.5F events glob matches zero files")

ps = subprocess.check_output(
    "ps -efww | grep run_stage1_5f_live_depth_observer | grep -v grep",
    shell=True,
    text=True,
)
if "\\*.jsonl" in ps:
    raise SystemExit("ERROR: Stage 1.5F process uses escaped events glob; restart with events/*.jsonl")
print("stage1_5f_events_glob_process_check", "ok")
PY

cat "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" 2>/dev/null | python3 -m json.tool | grep -E \
'"decision"|"consumable_by_stage1_5f"|"successful_poll_count"|"failed_poll_count"|"consecutive_failed_polls"|"formal_event_contract_versions_supported"|"formal_schedule_revision_contract_versions_supported"|"anchor_precedence_policy"|"shared_anchor_validator_enabled"|"fatal_blockers"' || true

cat "$STAGE1_5F_OUT/observer_root_contract.json" 2>/dev/null | python3 -m json.tool | grep -E \
'"root_mode"|"formal_event_contract_versions_allowed"|"formal_schedule_revision_contract_versions_allowed"|"anchor_precedence_policy"' || true

cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null | python3 -m json.tool | grep -E \
'"decision"|"stage1_5d_gate_mode"|"stage1_5d_runtime_gate_decision"|"stage1_5d_runtime_gate_stale"|"stage1_5d_runtime_gate_invalid_count"|"cross_root_upstream_summary_dependency"|"block_new_event_admission"|"active_observation_count"|"pending_launch_observation_count"|"post_watermark_events_accepted"|"schedule_revision_registry_orphan_count"|"schedule_revision_registry_ambiguous_count"|"last_heartbeat_at_ms"|"blocker"' || true

wc -l "$STAGE1_5D_EVENTS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/events/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/request_manifest/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || true
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/events_rejected" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/request_manifest" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
```

正常首检：

```text
1. tmux 中只有新的 official_schedule_anchor_contract_v2_hotfix 1.5D/1.5F session。
2. 1.5D live_safety_gate_summary decision = stage1_5d_runtime_gate_ready。
3. 1.5D formal_event_contract_versions_supported 包含 2。
4. 1.5D formal_schedule_revision_contract_versions_supported 包含 1。
5. 1.5D anchor_precedence_policy = official_schedule_priority_v1。
6. 1.5F observer_root_contract.root_mode = v2_production。
7. 1.5F stage1_5d_runtime_gate_decision = stage1_5d_runtime_gate_ready。
8. 1.5F cross_root_upstream_summary_dependency = false。
9. 1.5F block_new_event_admission = false。
10. stage1_5d_events_glob_hit_count > 0，且 stage1_5f_events_glob_process_check = ok。
11. 没有新事件时 active_observation_count = 0、pending_launch_observation_count = 0 属于正常。
```

## 8. 日常监控

### 8.1 一键设置路径

每次 SSH 新窗口先执行：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

### 8.2 进程、摘要和 request 计数检查

```bash
date -u
tmux ls
ps -efww | grep -E 'run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer' | grep -v grep

cat "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" 2>/dev/null || true
cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" 2>/dev/null || true
cat "$STAGE1_5F_OUT/observer_root_contract.json" 2>/dev/null || true
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null || true

cat "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" 2>/dev/null | python3 -m json.tool | grep -E \
'"decision"|"consumable_by_stage1_5f"|"successful_poll_count"|"failed_poll_count"|"consecutive_failed_polls"|"request_success_rate"|"formal_event_contract_versions_supported"|"formal_schedule_revision_contract_versions_supported"|"anchor_precedence_policy"|"shared_anchor_validator_enabled"|"fatal_blockers"' || true

cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null | python3 -m json.tool | grep -E \
'"decision"|"stage1_5d_gate_mode"|"stage1_5d_runtime_gate_decision"|"stage1_5d_runtime_gate_stale"|"stage1_5d_runtime_gate_invalid_count"|"cross_root_upstream_summary_dependency"|"block_new_event_admission"|"active_observation_count"|"pending_launch_observation_count"|"pending_launch_time_in_future_count"|"pending_launch_anchor_missing_count"|"pending_anchor_conflict_count"|"pending_observation_capacity_count"|"post_watermark_events_accepted"|"schedule_revision_registry_orphan_count"|"schedule_revision_registry_ambiguous_count"|"last_heartbeat_at_ms"|"blocker"' || true

wc -l "$STAGE1_5D_EVENTS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/events/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/request_manifest/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || true
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/events_rejected" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20
find "$STAGE1_5F_OUT/request_manifest" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true

tail -n 3 "$STAGE1_5D_EVENTS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
tail -n 3 "$STAGE1_5D_EVENTS_OUT"/events/*.jsonl 2>/dev/null || true
```

### 8.3 Stage 1.5D v2 event contract 批量检查

```bash
PYTHONPATH=src:. python3 - <<'PY'
import json
import os
from pathlib import Path
from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
    validate_launch_anchor_contract,
    validate_schedule_revision_contract,
)

root = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
launch_checked = 0
revision_checked = 0
bad = []
for p in sorted((root / "events").glob("*.jsonl")):
    for lineno, line in enumerate(p.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("event_type") == "futures_contract_launch_schedule_revision":
            revision_checked += 1
            res = validate_schedule_revision_contract(row)
            if not res.get("valid"):
                bad.append({"path": str(p), "lineno": lineno, "event_type": row.get("event_type"), "blockers": res.get("blockers")})
            continue
        launch_checked += 1
        for sym in row.get("symbols") or [None]:
            res = validate_launch_anchor_contract(row, sym, compatibility_mode=False)
            if not res.get("valid"):
                bad.append({"path": str(p), "lineno": lineno, "symbol": sym, "blockers": res.get("blockers")})
print("launch_checked", launch_checked)
print("revision_checked", revision_checked)
print("anchor_contract_bad_count", len(bad))
for item in bad[:20]:
    print(json.dumps(item, ensure_ascii=False))
PY
```

正常判读：

```text
anchor_contract_bad_count = 0。
launch rows 必须为 formal_event_contract_version = 2。
schedule revision rows 如出现，必须通过 formal_schedule_revision_contract_version = 1 validator。
若 launch_checked = 0，表示当前新 root 尚无 post-bootstrap consumable event，等待新公告即可。
```

### 8.4 Stage 1.5F root contract / version isolation 检查

```bash
python3 - <<'PY'
import json
import os
from pathlib import Path
root = Path(os.environ["STAGE1_5F_OUT"])
contract_path = root / "observer_root_contract.json"
summary_path = root / "live_depth_observer_summary.json"
print("observer_root_contract_exists", contract_path.exists())
if contract_path.exists():
    c = json.loads(contract_path.read_text())
    print(json.dumps({
        "root_mode": c.get("root_mode"),
        "formal_event_contract_versions_allowed": c.get("formal_event_contract_versions_allowed"),
        "formal_schedule_revision_contract_versions_allowed": c.get("formal_schedule_revision_contract_versions_allowed"),
        "anchor_precedence_policy": c.get("anchor_precedence_policy"),
    }, indent=2, ensure_ascii=False))
if summary_path.exists():
    s = json.loads(summary_path.read_text())
    print(json.dumps({
        "decision": s.get("decision"),
        "block_new_event_admission": s.get("block_new_event_admission"),
        "blocker": s.get("blocker"),
        "runtime_gate_diagnostic_count": s.get("runtime_gate_diagnostic_count"),
    }, indent=2, ensure_ascii=False))
PY
```

正常判读：

```text
root_mode = v2_production。
formal_event_contract_versions_allowed = [2]。
formal_schedule_revision_contract_versions_allowed = [1]。
anchor_precedence_policy = official_schedule_priority_v1。
block_new_event_admission = false。
```

### 8.5 新事件定位：单 symbol 或 multi-symbol

单 symbol：

```bash
export ARTICLE_ID="替换为 source_article_id"
export SYMBOLS="GRVTUSDT"
```

multi-symbol：

```bash
export ARTICLE_ID="替换为 source_article_id"
export SYMBOLS="PYPLUSDT GSUSDT SMHUSDT"
```

定位命令：

```bash
python3 - <<'PY'
import json
import os
from pathlib import Path
article = os.environ.get("ARTICLE_ID", "")
symbols = [
    s.strip()
    for raw in os.environ.get("SYMBOLS", "").replace(";", ",").split(",")
    for s in raw.split()
    if s.strip()
]
root_d = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
root_f = Path(os.environ["STAGE1_5F_OUT"])
needles = [article] + symbols

def row_hits(paths):
    hits = []
    for p in paths:
        if not p.exists():
            continue
        for lineno, line in enumerate(p.read_text().splitlines(), 1):
            if any(n and n in line for n in needles):
                try:
                    row = json.loads(line)
                except Exception:
                    row = {"raw": line[:500]}
                hits.append((str(p), lineno, row))
    return hits

stage1_5d_events = row_hits(sorted((root_d / "events").glob("*.jsonl")))
stage1_5f_accepted = row_hits(sorted((root_f / "events_accepted").glob("*.jsonl")))
stage1_5f_rejected = row_hits(sorted((root_f / "events_rejected").glob("*.jsonl")))
stage1_5f_state = row_hits([root_f / "observer_state.jsonl"])

print(json.dumps({
    "article": article,
    "symbols": symbols,
    "stage1_5d_event_hits": len(stage1_5d_events),
    "stage1_5f_accepted_hits": len(stage1_5f_accepted),
    "stage1_5f_rejected_hits": len(stage1_5f_rejected),
    "stage1_5f_state_hits": len(stage1_5f_state),
}, indent=2, ensure_ascii=False))

for label, hits in [
    ("stage1_5d_last_event", stage1_5d_events[-3:]),
    ("stage1_5f_last_accepted", stage1_5f_accepted[-3:]),
    ("stage1_5f_last_rejected", stage1_5f_rejected[-3:]),
    ("stage1_5f_last_state", stage1_5f_state[-5:]),
]:
    print("===", label, "===")
    for p, lineno, row in hits:
        print(json.dumps({
            "path": p,
            "lineno": lineno,
            "event_type": row.get("event_type"),
            "source_article_id": row.get("source_article_id"),
            "symbols": row.get("symbols"),
            "symbol": row.get("symbol"),
            "status": row.get("status"),
            "pending_reason": row.get("pending_reason"),
            "rejected_reason": row.get("rejected_reason") or row.get("rejection_reason"),
            "formal_event_contract_version": row.get("formal_event_contract_version"),
            "source_contract_status": row.get("source_contract_status"),
            "anchor_precedence_policy": row.get("anchor_precedence_policy"),
            "observation_anchor_ms": row.get("observation_anchor_ms"),
            "effective_observation_anchor_ms": row.get("effective_observation_anchor_ms"),
            "latest_anchor_contract_hash": row.get("latest_anchor_contract_hash"),
        }, ensure_ascii=False))
PY
```

### 8.6 新事件 active observation 检查

当 `post_watermark_events_accepted > 0` 或 `active_observation_count > 0` 后执行：

```bash
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null | python3 -m json.tool | grep -E \
'"decision"|"active_observation_count"|"completed_observation_count"|"total_snapshots_collected"|"request_success_rate"|"failed_requests_count"|"active_expected_snapshot_count"|"active_unique_snapshot_bucket_count"|"active_missing_snapshot_bucket_count"|"active_out_of_window_snapshot_row_count"|"active_anchor_revision_contaminated_count"|"completed_anchor_revision_contaminated_count"|"first_depth_request_at_ms"|"first_healthy_snapshot_at_ms"|"first_valid_book_latency_ms"' || true

find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null -exec tail -n 20 {} \;
find "$STAGE1_5F_OUT/observer_state.jsonl" -type f 2>/dev/null -exec tail -n 20 {} \;
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20
find "$STAGE1_5F_OUT/request_manifest" -type f 2>/dev/null -exec tail -n 20 {} \;
```

### 8.7 12h 完成后 Stage 1.5G review

不要把本地 pytest 临时生成的 1.5G review 提交到 `docs/reviews/`。生产 review 优先写入本次 `STAGE1_5G_OUT` 目录，确认后再决定是否复制到 `docs/reviews/`。

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)_official_schedule_anchor_contract_v2_hotfix"
export STAGE1_5G_OUT="data/external_signal_shadow/stage1_5g/reviews/${RUN_ID}"

PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  --stage1-5f-output-root "$STAGE1_5F_OUT" \
  --output-root "$STAGE1_5G_OUT" \
  --output-summary "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review_summary.json" \
  --output-review "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review.md"

cat "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review_summary.json" \
  | python3 -m json.tool | grep -E \
'"decision"|"allowed_next_action"|"clean_depth_evidence_pass"|"quarantined_depth_evidence_pass"|"quarantine_candidate"|"formal_announcement_and_launch_count"|"book_availability_ratio"|"invalid_book_row_count"|"anchor_contract_lineage_mismatch"|"anchor_revision_contaminated"|"malformed_anchor_contract"|"blockers"'
```

### 8.8 停止新 root

正常结束或需要重新部署时：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

date -u
tmux ls
ps -efww | grep -E 'run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer' | grep -v grep

tmux kill-session -t stage1_5f_live_depth_7d_official_schedule_anchor_contract_v2_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5d_continuous_7d_official_schedule_anchor_contract_v2_hotfix 2>/dev/null || true

ps -efww | grep -E 'run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer' | grep -v grep || true
```

停止前若 `active_observation_count > 0`，先记录：

```bash
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null | python3 -m json.tool | grep -E \
'"active_observation_count"|"total_snapshots_collected"|"active_expected_snapshot_count"|"active_unique_snapshot_bucket_count"|"last_heartbeat_at_ms"'
```



## 9. 新事件定位与排障

本章只保留当前 `official_schedule_anchor_contract_v2_hotfix` root 的必要排障命令。旧 BAPI table / endpoint fallback / starvation 专项命令不再放在日常 runbook 主体中，历史语义见第 12 章索引。

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

后续新 root 完成 12h observation 后，再运行 Stage 1.5G：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_official_schedule_anchor_contract_v2_hotfix' | sort | tail -n 1)"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export STAGE1_5G_OUT="data/external_signal_shadow/stage1_5g/reviews/${RUN_ID}"

PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  --stage1-5f-output-root "$STAGE1_5F_OUT" \
  --output-root "$STAGE1_5G_OUT" \
  --output-summary "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review_summary.json" \
  --output-review "docs/reviews/$(date -u +%Y-%m-%d)-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md"
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
```
