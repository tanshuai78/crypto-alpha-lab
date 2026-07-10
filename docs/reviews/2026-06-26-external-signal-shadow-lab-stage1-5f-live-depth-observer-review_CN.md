# External Signal Shadow Lab Stage 1.5F Live Depth Observer Review

**日期:** 2026-07-01  
**对应设计:** `docs/designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md`  
**对应实现计划:** `docs/plans/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-implementation-plan_CN.md`  
**当前运行重点:** Stage 1.5D title-contract symbol + transient detail retry hotfix source collector + Stage 1.5F request_manifest symbol-key hotfix live depth observer

## 1. 当前结论

```text
decision = stage1_5d_scheduler_hotfix_ready_for_deploy
implementation_status = completed_and_locally_verified
live_depth_evidence_status = not_collected_yet
target_server_mode = 7d_detail_retry_scheduler_starvation_hotfix
stage1_5g_allowed = plan_only_until_completed_12h_depth_observation
```

当前主线已经从上一轮 `request_manifest symbol-key hotfix` 前移到 `Stage 1.5D detail retry scheduler starvation hotfix`。后续部署必须同时更新 1.5D 和 1.5F：

```text
1. Stage 1.5D 使用新的 detail retry scheduler，避免新公告被旧 202/empty detail 重试队列饿死。
2. Stage 1.5D 必须启动新的 output root，旧 root 不改写、不补写、不作为 formal evidence。
3. Stage 1.5F 继续使用 request_manifest symbol-key 代码，但必须消费新的 1.5D root，并 bootstrap 新 watermark。
4. Stage 1.5G 只能审查新 root 中完成 12h 的 formal event-symbol depth evidence。
```

当前可以做：

```text
1. 按第 7 章重新同步、停止旧进程、启动新的 1.5D collector 和 1.5F observer。
2. 按第 8 章检查 1.5D scheduler state、1.5D events、1.5F summary、depth snapshots 和 request_manifest。
3. 保留旧 root 用于 regression / recovery validation，不混入正式 12h live depth evidence。
```

当前不能做：

```text
1. 不能声明 execution_feasibility_proven。
2. 不能声明 alpha。
3. 不能启动 paper/live trading。
4. 不能把旧事件当前盘口倒推为历史 12h entry 可成交。
5. 不能用旧 root 修复后重新解析出的 missed event 作为 formal live evidence。
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
P0: 部署 Stage 1.5D detail retry scheduler starvation hotfix，并用新的 1.5D root 启动 7d collector。
理由: 2026-07-09 Multiple TradFi 事件已经证明旧 detail retry 队列会被旧 202/empty detail article 占满，导致新公告 detail 从未及时 fetch。

P1: 用新的 1.5D root bootstrap 一个新的 Stage 1.5F root。
理由: watermark 必须从新 root 建立；旧 root 中的 terminal_failed/missed rows 不允许人工修复成 formal evidence。

P2: 等待新 root 中出现 post-watermark futures_contract_launch event-symbol。
理由: 只有新 root 中由修复后 1.5D 捕获并解析出的 event-symbol，才有资格进入 1.5F 12h live depth observation。

P3: 一旦 1.5F 出现 post_watermark_events_accepted > 0，切换到 30-60 分钟巡检频率。
理由: 新事件后的前 12h 是证据窗口，必须确认 active_observation_count、depth_snapshots、request_success_rate 正常增长。

P4: 等至少一个 event-symbol 完成 12h observation，再执行 Stage 1.5G Live Depth Evidence Review。
理由: 1.5G 审查的是完整 depth evidence，不是观察器是否启动；没有足量 snapshots 时不能给执行可行性结论。

P5: 如果 1.5G 判定 depth evidence 足够且盘口质量通过，只允许进入 Stage 1.5H shadow execution simulator 设计/计划。
理由: depth evidence 只能说明“值得模拟执行审查”，不能直接证明 alpha，也不能跳到 paper/live。
```

并行可做：

```text
1. 继续完善 Stage 1.5G review 文档和 fixture。
2. 整理 7d artifacts rsync 回本地的命令。
3. 定期复核 safety grep，确保没有 private endpoint、api key、order endpoint。
```

暂不推进：

```text
1. paper trading。
2. live trading。
3. execution engine 接入。
4. alpha 结论包装。
5. 用旧事件当前盘口倒推历史可成交性。
```

## 4. 当前服务器路径

### 4.1 最新 hotfix 应使用的路径

每次 SSH 新窗口先设置：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_scheduler_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix"
export STAGE1_5D_VALIDATION_SUMMARY="data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

最新部署后应看到：

```text
STAGE1_5D_EVENTS_OUT = data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_detail_retry_scheduler_starvation_hotfix
STAGE1_5F_OUT = data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix
```

### 4.2 旧路径处理规则

以下路径只用于历史排障、regression 或 recovery validation，不作为当前 formal evidence 主路径：

```text
data/external_signal_shadow/stage1_5d/live_event_source_continuous_*_7d
data/external_signal_shadow/stage1_5d/live_event_source_continuous_*_7d_empty_detail_retry_hotfix
data/external_signal_shadow/stage1_5d/live_event_source_continuous_*_7d_title_contract_transient_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_empty_detail_retry_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_title_contract_transient_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_request_manifest_symbol_key_hotfix
data/external_signal_shadow/stage1_5d/live_event_source_smoke_interrupted_*
data/external_signal_shadow/stage1_5d/live_event_source_smoke_invalid_*
```

不要修改旧 `events/*.jsonl`、不要删除旧 root、不要把旧 root 中修复后重放出的 symbol 当作正式 12h live evidence。

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
1.5F 是录像机，1.5G 是看片审查员。当前还没有 post-watermark 新事件，因此还没有片子可审。
```

## 6. Hotfix 背景

本文件记录过多轮 hotfix。当前部署主线是 2026-07-10 的 `Stage 1.5D detail retry scheduler starvation hotfix`，前置修复包括 title-contract extraction、transient detail retry、delayed-launch age gate、Stage 1.5F request_manifest symbol-key。

### 6.1 当前必须修复的问题

2026-07-09 的 Multiple USDⓈ-Margined TradFi Perpetual Contracts 事件暴露了 scheduler starvation：

```text
1. 1.5D raw payload 能看到新公告。
2. 1.5D events 写出了 terminal_failed，但 symbols=[]。
3. detail_fetch_status=max_age_exceeded，detail_fetch_attempted=false。
4. request_manifest 中大量旧 detail URL 返回 202/empty，占用 detail retry budget。
5. 新公告未及时获得第一次 detail fetch，最终被旧 max-age 分支误记成 parser/symbol empty failure。
```

根因不是公告没有 symbol，而是 collector 的 detail retry 调度不公平：旧 transient article 持续消耗预算，新 no-symbol futures article 不能在有界时间内获得第一次 detail request。

### 6.2 新 scheduler 的关键语义

```text
1. never-attempted article 有 first-attempt SLA，不允许被旧 transient article 无限饿死。
2. old HTTP 202/empty/429/5xx/timeout article 进入 backoff，不再每轮抢占预算。
3. scheduler state 持久化到 detail_retry_scheduler_state.json，重启后不丢 pending/backoff/defer 状态。
4. announcement_detail_deferred 是调度诊断，不是 HTTP 请求失败，也不是 parser failure。
5. never-attempted 到 max-age 后是 collection failure：detail_never_attempted_budget_starved，不得计入 symbol_empty/parser_failed。
6. endpoint degraded 时限制旧 transient retry，但保留有界 first-attempt budget。
```

### 6.3 仍需保留的前置修复语义

```text
1. Multiple TradFi 标题没有完整 symbols 时，需要从 detail payload 抽取 XXXUSDT / XXXUSDC。
2. BTCU/ETHU U-settled launch 不能自动拼成 BTCUUSDT / ETHUUSDT。
3. detail_contract_symbol 候选必须通过 Binance USD-M exchangeInfo 验证。
4. Stage 1.5F depth request_manifest 的 depth_snapshot rows 必须带 event_symbol_id / event_id / symbol。
5. delayed launch 事件的 age gate 使用 launch/onboard evidence，但不能绕过 watermark。
```

部署纪律：

```text
1. 不复用旧 7d output root。
2. 不覆盖旧 events/*.jsonl。
3. hotfix 部署后启动新的 1.5D output root。
4. 对新的 1.5D root bootstrap 一个匹配的新 1.5F output root。
5. 2026-07-09 missed event 只能用于 regression / recovery_validation，不得作为 formal 12h live depth evidence。
```

## 7. 部署 Runbook

### 7.1 本地验证并同步到服务器

在本地 Mac 执行：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export SERVER="root@47.82.4.85"

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5f_live_depth_observer.py \
  -q

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_*.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q

git diff --check

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

本次 hotfix 修改了 Stage 1.5D collector。部署后必须重启 1.5D，并用新的 1.5D root 重新 bootstrap 1.5F。

### 7.2 服务器 pytest 依赖修复

如果服务器报：

```text
/root/crypto-alpha-lab/.venv/bin/python: No module named pytest
```

执行：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

python -m ensurepip --upgrade 2>/dev/null || true
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

服务器最小验证：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  -q
```

### 7.3 停止旧 Stage 1.5D / 1.5F 进程

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

tmux ls
ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

# 停止旧 1.5F observer。
tmux kill-session -t stage1_5f_live_depth_7d 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_u_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_empty_detail_retry_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_title_contract_transient_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_delayed_launch_age_gate_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_request_manifest_symbol_key_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_detail_retry_scheduler_starvation_hotfix 2>/dev/null || true

# 本次必须停止旧 1.5D collector，否则仍会使用旧 scheduler。
tmux kill-session -t stage1_5d_continuous_7d_title_contract_transient_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5d_continuous_7d_detail_retry_scheduler_starvation_hotfix 2>/dev/null || true

ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep || true
```

如果 `ps` 仍显示旧 collector/observer，先不要继续启动新进程，避免两个进程同时写不同 root。

### 7.4 启动 Stage 1.5D detail retry scheduler starvation hotfix collector

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
export STAGE1_5D_EVENTS_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_${RUN_ID}_7d_detail_retry_scheduler_starvation_hotfix"

mkdir -p "$STAGE1_5D_EVENTS_OUT"

tmux new -d -s stage1_5d_continuous_7d_detail_retry_scheduler_starvation_hotfix "
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

echo "STAGE1_5D_EVENTS_OUT=$STAGE1_5D_EVENTS_OUT"
```

### 7.5 Bootstrap 新 Stage 1.5F watermark

等待新的 1.5D root 写出至少一轮 heartbeat/raw payload 后执行：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

mkdir -p data/external_signal_shadow/stage1_5e/execution_feasibility

if [ ! -f data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json ]; then
  cp "$(find data/external_signal_shadow/stage1_5e -type f -name execution_feasibility_audit_summary.json | sort | tail -n 1)" \
    data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
fi

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_scheduler_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix"
export STAGE1_5D_VALIDATION_SUMMARY="data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"

rm -rf "$STAGE1_5F_OUT"

PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob "$STAGE1_5D_EVENTS_OUT/events/*.jsonl" \
  --stage1-5d-summary "$STAGE1_5D_VALIDATION_SUMMARY" \
  --stage1-5e-summary "$STAGE1_5E_SUMMARY" \
  --output-root "$STAGE1_5F_OUT" \
  --bootstrap-watermark

cat "$STAGE1_5F_OUT/watermark.json"
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json"
```

bootstrap 只建立新旧边界，不对 bootstrap 前 rows 产生正式 live depth evidence。

### 7.6 启动新 Stage 1.5F observer

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_scheduler_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix"
export STAGE1_5D_VALIDATION_SUMMARY="data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

tmux new -d -s stage1_5f_live_depth_7d_detail_retry_scheduler_starvation_hotfix "
cd /root/crypto-alpha-lab &&
source .venv/bin/activate &&
STAGE1_5D_EVENTS_OUT='$STAGE1_5D_EVENTS_OUT' &&
STAGE1_5D_VALIDATION_SUMMARY='$STAGE1_5D_VALIDATION_SUMMARY' &&
STAGE1_5E_SUMMARY='$STAGE1_5E_SUMMARY' &&
STAGE1_5F_OUT='$STAGE1_5F_OUT' &&
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob \"\$STAGE1_5D_EVENTS_OUT/events/*.jsonl\" \
  --stage1-5d-summary \"\$STAGE1_5D_VALIDATION_SUMMARY\" \
  --stage1-5e-summary \"\$STAGE1_5E_SUMMARY\" \
  --output-root \"\$STAGE1_5F_OUT\" \
  --live-public-readonly
"
```

### 7.7 部署后首次检查

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_scheduler_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix"

date -u
tmux ls
ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" 2>/dev/null || true
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/request_manifest/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || true
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/events_rejected" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
```

## 8. 日常监控

### 8.1 一键设置路径

每次 SSH 新窗口先执行：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_scheduler_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

### 8.2 进程、摘要和 scheduler state 检查

```bash
date -u
tmux ls
ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" 2>/dev/null || true
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null || true

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

### 8.3 Stage 1.5D scheduler 专项检查

```bash
cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" 2>/dev/null | python -m json.tool | grep -E \
"detail_budget_deferred_count|detail_budget_starved_count|detail_never_attempted_expired_count|detail_first_attempt_sla_breach_count|detail_scheduler_pending_count|detail_scheduler_backoff_count|detail_endpoint_degraded" || true

python - <<'PY'
import json
import os
from pathlib import Path
root = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
state_path = root / "detail_retry_scheduler_state.json"
print("scheduler_state_exists", state_path.exists())
if state_path.exists():
    state = json.loads(state_path.read_text())
    articles = state.get("articles", {}) or {}
    print("metadata_version", state.get("metadata_version"))
    print("pending_articles", len(articles))
    print("endpoint_health", state.get("endpoint_health", {}))
    for code, row in list(articles.items())[-5:]:
        print({
            "code": code,
            "attempts": row.get("detail_fetch_attempt_count"),
            "transient_errors": row.get("transient_detail_error_count"),
            "defer_count": row.get("defer_count"),
            "next_retry_at_ms": row.get("next_detail_retry_at_ms"),
            "title": (row.get("title") or "")[:120],
        })
PY
```

判定标准：

```text
正常: scheduler_state_exists=true 或 summary 中 scheduler counters 可读。
正常: 新 no-symbol futures article 有 announcement_detail request row，或仍处于 scheduler pending/backoff/deferred。
异常: detail_fetch_attempted=false 的新 article 被 terminal_failed + symbol_empty/parser_failed。
异常: request_type 全部 unknown，无法区分 announcement_list / announcement_detail / exchange_info。
异常: 同一 source_article_id 每分钟无限写 announcement_detail_deferred 行。
```

### 8.4 Stage 1.5F symbol-key 专项检查

```bash
python - <<'PY'
import glob
import json
import os
root = os.environ["STAGE1_5F_OUT"]
rows = []
missing = []
for p in sorted(glob.glob(f"{root}/request_manifest/**/*.jsonl", recursive=True)):
    with open(p) as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("request_type") == "depth_snapshot":
                rows.append(row)
                if not row.get("event_symbol_id") or not row.get("event_id") or not row.get("symbol"):
                    missing.append(row)
print("depth_manifest_rows", len(rows))
print("missing_symbol_key_rows", len(missing))
for row in rows[-5:]:
    print({
        "symbol": row.get("symbol"),
        "event_symbol_id": row.get("event_symbol_id"),
        "event_id": row.get("event_id"),
        "http_status": row.get("http_status"),
        "audit_metadata_version": row.get("audit_metadata_version"),
    })
PY
```

判定标准：

```text
missing_symbol_key_rows 必须等于 0。
depth_manifest_rows 为 0 且 post_watermark_events_accepted=0，表示仍在等待新事件。
depth_manifest_rows > 0 时，所有 depth_snapshot rows 必须带 event_symbol_id / event_id / symbol。
```

## 9. Raw Payload 与 Events 检查

### 9.1 查看 1.5F watermark 时间

```bash
python - <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path
import os

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

### 9.2 快速 grep raw payload

```bash
grep -RniE "Futures Will Launch|Will Launch.*Perpetual|USDⓈ-Margined|USDS-Margined|USD-M.*Perpetual" \
  "$STAGE1_5D_EVENTS_OUT"/raw_payloads \
  | tail -n 80
```

`grep` 只适合粗筛，会命中旧标题或非 launch 文本。是否真是新事件，要继续看 `releaseDate`、`detected_at_ms` 和 `events/*.jsonl`。

### 9.3 解析 raw payload 并按 releaseDate 列出最新 launch 标题

公告官网：https://www.binance.com/en/support/announcement/list/48

```bash
python - <<'PY'
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import os

root = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
raw_dir = root / "raw_payloads"
rows = {}
pattern = re.compile(r"futures.*will\s+launch.*perpetual|will\s+launch.*perpetual", re.I)

for path in sorted(raw_dir.glob("*.jsonl")):
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            envelope = json.loads(line)
        except Exception:
            continue
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            continue
        catalogs = payload.get("data", {}).get("catalogs", [])
        for catalog in catalogs:
            for article in catalog.get("articles", []) or []:
                title = article.get("title") or ""
                if not pattern.search(title):
                    continue
                code = article.get("code") or article.get("id") or ""
                release_ms = article.get("releaseDate") or 0
                rows[code] = {"release_ms": release_ms, "code": code, "title": title}

items = sorted(rows.values(), key=lambda r: r["release_ms"], reverse=True)
print("launch_titles", len(items))
for row in items[:20]:
    ts = datetime.fromtimestamp(row["release_ms"] / 1000, tz=timezone.utc).isoformat() if row["release_ms"] else "unknown"
    print(ts, row["code"], row["title"])
PY
```

### 9.4 检查 1.5D events 是否写入 futures launch event

```bash
python - <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path
import os

root = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
rows = []

for path in sorted((root / "events").glob("*.jsonl")):
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("event_type") == "futures_contract_launch":
            rows.append(row)

rows.sort(key=lambda r: r.get("detected_at_ms") or 0, reverse=True)
print("event_rows", len(rows))
for row in rows[:30]:
    detected_ms = row.get("detected_at_ms") or 0
    published_ms = row.get("source_published_at_ms") or 0
    print("---")
    print("detected_utc", datetime.fromtimestamp(detected_ms / 1000, tz=timezone.utc).isoformat() if detected_ms else None)
    print("published_utc", datetime.fromtimestamp(published_ms / 1000, tz=timezone.utc).isoformat() if published_ms else None)
    print("source_article_id", row.get("source_article_id"))
    print("symbols", row.get("symbols"))
    print("symbol_parse_status", row.get("symbol_parse_status"))
    print("symbol_extraction_source", row.get("symbol_extraction_source"))
    print("symbol_validation_status", row.get("symbol_validation_status"))
    print("detail_fetch_status", row.get("detail_fetch_status"))
    print("terminal_failure_type", row.get("terminal_failure_type"))
    print("title", row.get("title"))
PY
```

判读：

```text
raw payload 有新 launch，但 events 没写入 = parser/normalizer 或 scheduler 覆盖问题。
events 中 symbols 非空 + parsed = 1.5D 成功产出 event-symbol。
events 中 detected_utc 晚于 1.5F watermark utc_time = 1.5F 理论上应接受为 post-watermark。
detail_fetch_status=budget_starved 或 terminal_failure_type=detail_never_attempted_budget_starved = collection/scheduler failure，不是公告无 symbol 证据。
detail_fetch_status=max_age_exceeded + detail_fetch_attempted=false 不应在新 root 中再次出现。
validation=pending_exchangeinfo_missing = 候选 symbol 还未出现在 exchangeInfo，不能写入 parsed event。
validation=rejected + symbol_parse_status=terminal_failed = exchangeInfo 明确拒绝，例如非 PERPETUAL 或资产不在 allowlist。
```

## 10. 首次输出判读模板

新一轮 detail retry scheduler starvation hotfix 部署后，首次输出应类似：

```text
STAGE1_5D_EVENTS_OUT = data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_detail_retry_scheduler_starvation_hotfix
STAGE1_5F_OUT = data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix

1.5D:
  heartbeat rows > 0
  request_manifest rows > 0
  detail_retry_scheduler_state.json exists or summary scheduler counters readable

1.5F:
  decision = stage1_5f_observer_running_no_new_event
  stage1_5e_context_missing = false
  watermark_present = true
  post_watermark_events_accepted = 0
  active_observation_count = 0
  total_snapshots_collected = 0
  request_success_rate = 1.0
  failed_requests_count = 0
  heartbeat_count >= 1
```

判读：

```text
status = normal_initial_detail_retry_scheduler_starvation_hotfix_run
path_status = current_1_5d_and_1_5f_roots_match
1.5D_status = running_and_writing_heartbeats_request_manifest_scheduler_state
1.5F_status = running_and_waiting_for_post_watermark_event
depth_collection_status = not_started_because_no_new_post_watermark_event_symbol
```

说明：

```text
1. post_watermark_events_accepted = 0 表示 1.5F 尚未接受 watermark 之后的新 event-symbol。
2. active_observation_count = 0 和 total_snapshots_collected = 0 在无新事件时正常。
3. heartbeat_count 应持续增长；如果不增长，优先检查 tmux / ps / stderr。
4. 1.5D request_manifest 中 request_type 不应全部为 unknown。
5. 新 no-symbol futures article 不应直接变成 detail_fetch_attempted=false + terminal_failed + symbol_empty/parser_failed。
```

## 11. Stage 1.5G 衔接

可以现在写 `Stage 1.5G Live Depth Evidence Review plan`，但不能执行正式 evidence review 结论，直到 1.5F 至少完成一个 event-symbol 的 12h observation。

1.5G 将审查：

```text
1. 是否覆盖完整 12h observation window。
2. snapshot 数量是否达到 min_snapshot_count_required。
3. snapshot 时间分布是否均匀，是否存在大 gap。
4. spread、top depth、500 USDT buy/sell slippage proxy 是否可接受。
5. request_manifest / heartbeat / timestamp quality 是否支持审计。
6. close-price replay 是否被真实盘口证据支持，还是仍可能是幻觉。
```

1.5G 不允许：

```text
1. 不证明 alpha。
2. 不启动 paper/live。
3. 不把盘口证据等同于真实成交收益。
4. 不把旧事件当前盘口当历史证据。
```

## 12. 历史问题索引

### 12.1 旧 1.5D smoke 中断

历史上曾出现：

```text
max_raw_payload_bytes_per_day_exceeded
OUT_ROOT 为空导致 summary 写到 /binance_futures_launch_smoke_summary.json
```

这些 run 不能作为正式 24h source smoke evidence，只保留作排障记录。

### 12.2 Multiple TradFi symbols=[]

已在本地修复：detail fallback 会持久化 detail payload，并从 detail payload 中抽取完整 `XXXUSDT/XXXUSDC`。

### 12.3 BTCU/ETHU U-settled symbols=[]

已在本地修复：BTCU/ETHU 是 Binance USD-M exchangeInfo 中的 raw contract symbols，不能自动改写为 BTCUUSDT/ETHUUSDT。

修复后的规则：

```text
1. detail_contract_symbol 候选必须精确匹配 exchangeInfo symbol。
2. exchangeInfo 只有 BTCUUSDT 时，候选 BTCU 不得被伪验证为 BTCUUSDT，应保持 pending_exchangeinfo_missing。
3. exchangeInfo 中 BTCU/ETHU 为 PERPETUAL + TRADING + quoteAsset=U + marginAsset=U 时，emit symbols=["BTCU","ETHU"]。
4. rejected candidate 必须写 terminal diagnostic event，不能静默留在 retry state。
5. 1.5F depth request 必须使用 raw symbol=BTCU/ETHU。
```

### 12.4 旧事件不能补完整 12h live depth

已经错过 12h entry window 的事件，即使现在 parser 修复，也不能补成完整 live depth evidence。只能等待 watermark 之后的新事件。

### 12.5 2026-07-02 empty detail payload 事件

2026-07-02 曾出现 Binance announcement detail 返回 `HTTP 202 + 0-byte body` 的情况。

旧行为：

```text
1. 把 202 + 空 body 当成 detail fetch success。
2. 持久化 0-byte payload。
3. 产出 symbols=[] 的 terminal_failed event。
```

修复后行为：

```text
1. 202 + 空 body 被视为 transient detail unavailable。
2. request_manifest 写入失败诊断，但不把空 body 作为可信 payload。
3. 保持 pending_retry，不写 terminal event。
4. 后续 poll 或进程重启后仍可重新尝试 detail fetch。
```

发布边界：

```text
正式观察:
  使用新的 Stage 1.5D output root。
  使用新的 Stage 1.5F output root。
  从新的 Stage 1.5D root bootstrap 新的 Stage 1.5F watermark。
  只有新 watermark 之后的事件才能计入正式 12h live depth evidence。

恢复性验证:
  使用单独 output root，命名中包含 recovery_validation。
  已经见过的文章，例如 d2acaa91c14e4cc598aaee1017efc1ac，只能用于验证 parser/retry 行为。
  recovery validation 不能标记为有效 12h live depth evidence，因为初始 live window 可能已经错过。
  recovery validation artifacts 不能混入正式 Stage 1.5F evidence root。
```

监控命令：
```bash
python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
for path in sorted((root / "request_manifest").glob("*.jsonl")):
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("source_type") == "announcement_detail" and row.get("payload_size_bytes") == 0:
            print(json.dumps(row, ensure_ascii=False))
PY
```

### 12.6 2026-07-02 ETHUSD1 与 transient detail retry hotfix (M3)

2026-07-02 live 事件暴露出两类问题：
- `ETHUSD1` 这类标题中直接出现 raw contract symbol 的事件，原 parser 没有完整覆盖。
- Multiple TradFi 和 ETHUSD1 事件都遇到 Binance detail `HTTP 202 + empty body`，旧逻辑会错误持久化空 payload。

修复边界：
- 修复目标是未来事件。
- 已经被 watermark 跨过或已经 terminal 的旧 row，只能作为 recovery validation。
- 重新解析出的 `23c9b8e88309409cbcd8509af0b78d10` 或 `d2acaa91c14e4cc598aaee1017efc1ac`，不能作为正式 12h live depth evidence。

修复后验证命令：
```bash
python - <<'PY'
import glob, json, os
rows = []
for p in glob.glob(os.path.join(os.environ["STAGE1_5D_EVENTS_OUT"], "events", "*.jsonl")):
    for line in open(p):
        if line.strip():
            r = json.loads(line)
            if r.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10":
                rows.append(r)
print(rows[-3:])
PY
```

### 12.7 2026-07-03 Delayed Launch Age Gate 与证据标签规则 (M3)

本次 hotfix 当时的部署目标：

```text
Stage 1.5D root: live_event_source_continuous_*_7d_title_contract_transient_hotfix
Stage 1.5F root: live_depth_observer_7d_delayed_launch_age_gate_hotfix
Stage 1.5F tmux: stage1_5f_live_depth_7d_delayed_launch_age_gate_hotfix
```

问题背景：
部分合约会先发公告，真正进入 `TRADING` 状态或到达 `onboardDate` 可能在几小时后。如果 Stage 1.5F 只用 `detected_at_ms` 做 15 分钟 age gate，会把这种 delayed launch 事件提前判为 `age_exceeded`，导致盘口观察还没开始就被拒绝。

实现检查点：
- `symbol_effective_launch_times_ms[symbol]` / `symbol_onboard_times_ms[symbol]` 可作为 `observation_age_base_ms`。
- `symbol_resolved_at_ms` 只能在存在 delayed-launch 证据链时作为 age base；普通 late parser retry 必须回退到 `detected_at_ms`。
- `pending, launch_time_in_future` 不能写入 `events_rejected/*.jsonl`，也不能推进 watermark。
- accepted/rejected rows 必须包含 `observation_age_base_ms`、`observation_age_basis`、`event_age_ms`、`max_event_age_ms`、`watermark_max_seen_detected_at_ms`、`watermark_version`。

证据标签边界：
1. `announcement_and_launch_time`:
   - announcement capture time，即 `detected_at_ms`，和 launch/onboard time，即 `symbol_effective_launch_times_ms` / `symbol_onboard_times_ms`，都严格晚于 watermark。
   - 这是完整的公告捕获 + 上线盘口证据，可以进入正式 1.5G 审查。
2. `launch_time_only`:
   - 公告捕获时间早于或等于 watermark，但 launch/onboard time 晚于 watermark。
   - Stage 1.5F 可以观察上线盘口，但不能证明公告捕获链路有效。
3. `recovery_validation_only`:
   - 公告捕获时间和 launch/onboard time 都早于或等于 watermark。
   - 只能用于调试 parser、retry、loader，不得混入正式 evidence。


### 12.8 2026-07-06 Stage 1.5F request_manifest symbol-key hotfix

修复原因：
Stage 1.5G 需要按 `event_symbol_id` / `symbol` 计算每个 event-symbol 的 request success rate，才能判断盘口采集是否可靠。旧版 Stage 1.5F 写入 `request_manifest/*.jsonl` 的 depth rows 只有全局请求信息，无法归因到具体 event-symbol，因此 1.5G 会被 `request_manifest_symbol_key_missing` 阻断。

修复后 depth request manifest rows 必须包含：

```text
request_type = depth_snapshot
audit_metadata_version = 1
event_symbol_id = <event_symbol_id_hash>
event_id = <event_id>
symbol = <actual_depth_symbol>
```

注意：`exchangeInfo` 是交易所级别元数据请求，不对应单个 event-symbol，不要求加 symbol key。当前部署和检查命令以第 7/8 章为准，本节只保留历史语义。

判定标准：

```text
1. depth_snapshot rows 一旦出现，missing_symbol_key_rows 必须等于 0。
2. depth_manifest_rows=0 且 post_watermark_events_accepted=0 是正常等待状态。
3. 旧 output root 即使代码已升级，也不能补成 formal-auditable root。
```

### 12.9 2026-07-10 Stage 1.5D detail retry scheduler starvation hotfix

修复原因：
2026-07-09 Multiple TradFi 事件证明旧 1.5D detail retry 队列存在 starvation：旧 HTTP 202/empty detail article 长期占用 budget，新公告虽然进入 raw payload，却没有及时获得第一次 detail fetch，最后被误写成 `terminal_failed` + `symbols=[]`。

修复后语义：

```text
1. never-attempted futures article 必须在有界 SLA 内获得第一次 detail attempt。
2. old transient detail article 进入 backoff，不得无限抢占 budget。
3. scheduler state 持久化，进程重启后 pending/backoff/defer 状态可恢复。
4. budget_starved 是 collection failure，不是 parser failure。
5. announcement_detail_deferred 是 scheduler diagnostic，不是 HTTP request failure。
6. 2026-07-09 missed event 只能用于 regression / recovery_validation，不得进入 formal 12h live evidence。
```

当前部署和检查命令以第 7/8 章为准，本节只保留历史问题和判读标准，避免重复维护多套命令。
