# External Signal Shadow Lab Stage 1.5F Live Depth Observer Review

**日期:** 2026-07-01  
**对应设计:** `docs/designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md`  
**对应实现计划:** `docs/plans/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-implementation-plan_CN.md`  
**当前运行重点:** Stage 1.5D detail endpoint degraded retry cadence + fallback hotfix source collector + Stage 1.5F live depth observer

## 1. 当前结论

```text
decision = stage1_5d_detail_endpoint_fallback_hotfix_ready_for_deploy
implementation_status = completed_and_locally_verified
skhyusdt_stage1_5g_status = quarantined_depth_evidence_pass_design_only
target_server_mode = 7d_detail_endpoint_fallback_hotfix
stage1_5h_allowed = design_only
```

当前主线已经从 `Stage 1.5D detail retry scheduler starvation hotfix` 前移到 `Stage 1.5D detail endpoint degraded retry cadence + detail fetch fallback hotfix`。后续部署必须同时更新 1.5D 和 1.5F：

```text
1. Stage 1.5D 使用新的 degraded recent retry cadence，避免 endpoint degraded 后长期不重试近期公告。
2. Stage 1.5D 使用 fallback detail URL，但 fallback 请求必须计入 HTTP request budget。
3. Stage 1.5D 区分 detail_retry_cycle_count 和 detail_http_request_count，避免审计混淆。
4. Stage 1.5D 使用 endpoint_health_by_variant，primary URL degraded 不得污染 fallback URL health。
5. Stage 1.5D 必须启动新的 output root；旧 SKHYUSDT root 只读保存，不改写、不补写。
6. Stage 1.5F 必须消费新的 1.5D root，并 bootstrap 新 watermark。
```

当前可以做：

```text
1. 按第 7 章同步代码、停止旧进程、启动新的 1.5D collector 和 1.5F observer。
2. 按第 8 章检查 1.5D scheduler/fallback state、1.5D events、1.5F summary、depth snapshots 和 request_manifest。
3. 保留旧 SKHYUSDT evidence root 用于 Stage 1.5H design-only 输入，不再继续写入。
4. 基于 2026-07-11 Stage 1.5G quarantined pass 结论编写 1.5H design。
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
P0: 部署 Stage 1.5D detail endpoint degraded retry cadence + fallback hotfix，并用新的 1.5D root 启动 7d collector。
理由: scheduler fairness 已解决“新公告拿不到第一次 detail fetch”的问题，但 2026-07-10 Multiple TradFi 事件证明 Binance detail endpoint 可能长期返回 HTTP 202 + empty，需要 fallback 和 degraded recent retry cadence。

P1: 用新的 1.5D root bootstrap 一个新的 Stage 1.5F root。
理由: watermark 必须从新 root 建立；旧 SKHYUSDT root 已经完成 1.5G 审计，只读保留。

P2: 等待新 root 中出现 post-watermark futures_contract_launch event-symbol。
理由: 只有新 root 中由修复后 1.5D 捕获并解析出的 event-symbol，才有资格进入新一轮 1.5F 12h live depth observation。

P3: 一旦 1.5F 出现 post_watermark_events_accepted > 0，切换到 30-60 分钟巡检频率。
理由: 新事件后的前 12h 是证据窗口，必须确认 active_observation_count、depth_snapshots、request_success_rate 正常增长。

P4: 已完成的 SKHYUSDT 1.5G 结论可作为 1.5H design-only 输入。
理由: 1.5G 结论为 stage1_5g_depth_evidence_quarantined_pass，allowed_next_action=write_stage1_5h_design_only，不允许进入 implementation/paper/live。
```

并行可做：

```text
1. 编写 Stage 1.5H design，必须显式消费 clean/quarantined/invalid 三类 1.5G evidence。
2. 继续运行新的 1.5D/1.5F root，等待下一个 clean 或 quarantined evidence。
3. 定期复核 safety grep，确保没有 private endpoint、api key、order endpoint。
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

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_endpoint_fallback_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_detail_endpoint_fallback_hotfix' | sort | tail -n 1)"
export STAGE1_5D_VALIDATION_SUMMARY="data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

最新部署后应看到：

```text
STAGE1_5D_EVENTS_OUT = data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_detail_endpoint_fallback_hotfix
STAGE1_5F_OUT = data/external_signal_shadow/stage1_5f/live_depth_observer_<RUN_ID>_7d_detail_endpoint_fallback_hotfix
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
4. 新 1.5D/1.5F 部署必须使用 detail_endpoint_fallback_hotfix 后缀。
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

本文件记录过多轮 hotfix。当前部署主线是 2026-07-11 的 `Stage 1.5D detail endpoint degraded retry cadence + fallback hotfix`，前置修复包括 title-contract extraction、transient detail retry、delayed-launch age gate、Stage 1.5F request_manifest symbol-key、Stage 1.5D detail retry scheduler starvation。

### 6.1 已修复的 scheduler starvation 问题

2026-07-09 的 Multiple USDⓈ-Margined TradFi Perpetual Contracts 事件暴露了 scheduler starvation：

```text
1. 1.5D raw payload 能看到新公告。
2. 1.5D events 写出了 terminal_failed，但 symbols=[]。
3. detail_fetch_status=max_age_exceeded，detail_fetch_attempted=false。
4. request_manifest 中大量旧 detail URL 返回 202/empty，占用 detail retry budget。
5. 新公告未及时获得第一次 detail fetch，最终被旧 max-age 分支误记成 parser/symbol empty failure。
```

根因不是公告没有 symbol，而是 collector 的 detail retry 调度不公平：旧 transient article 持续消耗预算，新 no-symbol futures article 不能在有界时间内获得第一次 detail request。该问题由 scheduler fairness、state persistence、backoff、budget_starved taxonomy 解决。

### 6.2 本轮必须修复的 endpoint fallback 问题

2026-07-10 的 Multiple USDⓈ-Margined TradFi 事件证明，scheduler fairness 之后仍可能遇到 detail endpoint degraded：

```text
1. 新公告已经进入 scheduler state。
2. 新公告已经获得 announcement_detail HTTP request。
3. primary detail URL 长期返回 HTTP 202 + empty body。
4. article 进入 endpoint degraded/backoff，但没有可审计 fallback path。
5. 如果不修复，近期公告可能长期无法从 detail payload 解析 symbol。
```

本轮修复重点：

```text
1. degraded recent article retry cadence：近期公告在 endpoint degraded 后仍有有界 retry。
2. detail fallback URL：仅对 HTTP 202 / empty untrusted payload 尝试 fallback。
3. HTTP request budget：primary + fallback 都计入 EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL。
4. cycle/request 拆分：detail_retry_cycle_count 不等于 detail_http_request_count。
5. endpoint_health_by_variant：primary degraded 不污染 fallback variant。
6. fallback provenance：payload_trusted、detail_fetch_variant、detail_fetch_url_used、payload hash 必须可审计。
```

### 6.3 仍需保留的前置修复语义

```text
1. Multiple TradFi 标题没有完整 symbols 时，需要从 detail payload 抽取 XXXUSDT / XXXUSDC。
2. BTCU/ETHU U-settled launch 不能自动拼成 BTCUUSDT / ETHUUSDT。
3. detail_contract_symbol 候选必须通过 Binance USD-M exchangeInfo 验证。
4. Stage 1.5F depth request_manifest 的 depth_snapshot rows 必须带 event_symbol_id / event_id / symbol。
5. delayed launch 事件的 age gate 使用 launch/onboard evidence，但不能绕过 watermark。
6. Stage 1.5G quarantine pass 只能进入 design-only，不能作为 execution feasibility claim。
```

部署纪律：

```text
1. 不复用旧 7d output root。
2. 不覆盖旧 events/*.jsonl。
3. hotfix 部署后启动新的 1.5D output root。
4. 对新的 1.5D root bootstrap 一个匹配的新 1.5F output root。
5. 2026-07-09 missed event 只能用于 regression / recovery_validation，不得作为 formal 12h live depth evidence。
6. SKHYUSDT completed evidence root 只读保留，不继续写入。
```

## 7. 部署 Runbook

### 7.1 本地同步到服务器

本轮部署目标：把已提交的 Stage 1.5D detail endpoint fallback hotfix 和 Stage 1.5F/1.5G 兼容修补同步到服务器。

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
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

如果本地已完成提交且只需要部署服务器，可直接执行 `rsync`，但不要跳过服务器端最小验证。

### 7.2 服务器最小验证

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  -q
```

若服务器缺少 pytest：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

python -m ensurepip --upgrade 2>/dev/null || true
python -m pip install -U pip
python -m pip install -e ".[dev]"
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
tmux kill-session -t stage1_5f_live_depth_7d_detail_retry_overdue_starvation_hotfix 2>/dev/null || true

# 停止旧 1.5D collector。
tmux kill-session -t stage1_5d_continuous_7d_title_contract_transient_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5d_continuous_7d_detail_retry_scheduler_starvation_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5d_continuous_7d_detail_retry_overdue_starvation_hotfix 2>/dev/null || true

ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep || true
```

如果 `ps` 仍显示旧 collector/observer，先不要继续启动新进程，避免多个进程同时采集或写入不同证据 root。

### 7.4 启动 Stage 1.5D detail retry overdue starvation hotfix collector

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
export STAGE1_5D_EVENTS_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_${RUN_ID}_7d_detail_retry_overdue_starvation_hotfix"

if [ -e "$STAGE1_5D_EVENTS_OUT" ]; then
  echo "Refuse to overwrite existing STAGE1_5D_EVENTS_OUT=$STAGE1_5D_EVENTS_OUT" >&2
  exit 1
fi
mkdir -p "$STAGE1_5D_EVENTS_OUT"

tmux new -d -s stage1_5d_continuous_7d_detail_retry_overdue_starvation_hotfix "
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

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"
STAGE1_5F_RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_${STAGE1_5F_RUN_ID}_7d_detail_retry_overdue_starvation_hotfix"
export STAGE1_5D_VALIDATION_SUMMARY="data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

if [ -z "$STAGE1_5D_EVENTS_OUT" ] || [ ! -d "$STAGE1_5D_EVENTS_OUT" ]; then
  echo "Missing STAGE1_5D_EVENTS_OUT" >&2
  exit 1
fi
if [ -e "$STAGE1_5F_OUT" ]; then
  echo "Refuse to overwrite existing STAGE1_5F_OUT=$STAGE1_5F_OUT" >&2
  exit 1
fi

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"

PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob "$STAGE1_5D_EVENTS_OUT/events/*.jsonl" \
  --stage1-5d-summary "$STAGE1_5D_VALIDATION_SUMMARY" \
  --stage1-5e-summary "$STAGE1_5E_SUMMARY" \
  --output-root "$STAGE1_5F_OUT" \
  --bootstrap-watermark

cat "$STAGE1_5F_OUT/watermark.json"
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json"
```

bootstrap 只建立启动时的新旧边界，不对 bootstrap 前 rows 产生正式 live depth evidence。1.5F 运行后，watermark 会随 accepted events 继续前推；对 delayed launch contract-symbol，后续 eligibility 必须同时审计 launch/onboard time evidence。

### 7.6 启动新 Stage 1.5F observer

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5D_VALIDATION_SUMMARY="data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

if [ -z "$STAGE1_5D_EVENTS_OUT" ] || [ -z "$STAGE1_5F_OUT" ]; then
  echo "Missing STAGE1_5D_EVENTS_OUT or STAGE1_5F_OUT" >&2
  exit 1
fi

tmux new -d -s stage1_5f_live_depth_7d_detail_retry_overdue_starvation_hotfix "
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

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"

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

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

### 8.2 进程、摘要和 request 计数检查

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

### 8.3 Stage 1.5D scheduler/overdue retry 专项检查

```bash
cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" 2>/dev/null | python -m json.tool | grep -E \
"detail_budget_deferred_count|detail_budget_starved_count|detail_never_attempted_expired_count|detail_first_attempt_sla_breach_count|detail_scheduler_pending_count|detail_scheduler_backoff_count|detail_endpoint_degraded|detail_degraded_recent_retry_count|detail_fetch_fallback_attempt_count|detail_fetch_fallback_success_count|detail_fetch_attempt_manifest_mismatch_count|detail_retry_overdue_pending_count|detail_retry_overdue_attempted_count|detail_retry_due_timestamp_missing_count|detail_attempt_manifest_mismatch_count|detail_retry_oldest_overdue_ms|detail_retry_overdue_warn_active|detail_retry_overdue_hard_warn_active|detail_retry_overdue_selected_total|detail_retry_overdue_deferred_total|detail_retry_overdue_retry_cycle_total" || true

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
    print("endpoint_health_by_variant", state.get("endpoint_health_by_variant") or state.get("endpoint_health", {}).get("by_variant", {}))
    for code, row in list(articles.items())[-5:]:
        print({
            "code": code,
            "detail_retry_cycle_count": row.get("detail_retry_cycle_count"),
            "detail_http_request_count": row.get("detail_http_request_count"),
            "detail_fetch_attempt_count": row.get("detail_fetch_attempt_count"),
            "transient_errors": row.get("transient_detail_error_count"),
            "defer_count": row.get("defer_count"),
            "next_retry_at_ms": row.get("next_detail_retry_at_ms"),
            "terminal_failure_type": row.get("terminal_failure_type"),
            "title": (row.get("title") or "")[:120],
        })
PY

find "$STAGE1_5D_EVENTS_OUT/detail_retry_scheduler_diagnostics" -type f 2>/dev/null | sort | tail -n 5 | xargs tail -n 20 2>/dev/null || true
find "$STAGE1_5D_EVENTS_OUT/detail_retry_terminal_diagnostics" -type f 2>/dev/null | sort | tail -n 5 | xargs tail -n 20 2>/dev/null || true
```

判定标准：

```text
正常: scheduler_state_exists=true 或 summary 中 scheduler counters 可读。
正常: summary 可读 detail_fetch_fallback_attempt_count / detail_fetch_fallback_success_count。
正常: endpoint_health_by_variant 可区分 primary 和 fallback URL variant。
正常: 新 no-symbol futures article 有 announcement_detail request row，或仍处于 scheduler pending/backoff/deferred。
正常: overdue selected/deferred totals 可读；若有 deferred，diagnostics 中必须出现原因。
正常: detail_unavailable_timeout 只出现在 detail_retry_terminal_diagnostics，且 consumable_by_stage1_5f=false。
异常: detail_fetch_attempt_manifest_mismatch_count > 0。
异常: fallback 请求数量突破 EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL。
异常: 429/5xx/timeout/url_validation_failed 后立即 fallback。
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
depth_manifest_rows > 0 后，missing_symbol_key_rows 必须为 0。
exchangeInfo rows 不对应单个 event-symbol，不要求 event_symbol_id。
announcement_detail_deferred rows 是 1.5D scheduler diagnostic，不应被 1.5F/1.5G depth request health 当成 depth_snapshot。
```

### 8.5 Stage 1.5F delayed-launch watermark 专项检查

用于确认 delayed launch 事件不会因为 `detected_at_ms` 早于运行中的 watermark 而被误判为 `pre_watermark`。以 SPCXUSD1 为例：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export ARTICLE_ID="6cbb1b11a9c843949624cf2eacaac8b4"
export SYMBOL="SPCXUSD1"
export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"

python - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

article_id = os.environ["ARTICLE_ID"]
symbol = os.environ["SYMBOL"]
d_root = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
f_root = Path(os.environ["STAGE1_5F_OUT"])

def utc(ms):
    if ms is None:
        return None
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()

print("STAGE1_5D_EVENTS_OUT", d_root)
print("STAGE1_5F_OUT", f_root)

w_path = f_root / "watermark.json"
if w_path.exists():
    w = json.loads(w_path.read_text())
    print("\n=== 1.5F watermark ===")
    print("max_seen_detected_at_ms", w.get("max_seen_detected_at_ms"))
    print("max_seen_detected_utc", utc(w.get("max_seen_detected_at_ms")))
    print("seen_source_article_contains_symbol_article", article_id in (w.get("seen_source_article_ids") or []))

s_path = d_root / "detail_retry_scheduler_state.json"
print("\n=== 1.5D scheduler ===")
print("scheduler_exists", s_path.exists())
if s_path.exists():
    s = json.loads(s_path.read_text())
    row = (s.get("articles") or {}).get(article_id)
    print("article_in_scheduler", row is not None)
    if row:
        print(json.dumps({
            "title": row.get("title"),
            "event_type": row.get("event_type"),
            "candidate_symbols": row.get("candidate_symbols"),
            "symbol_validation_status": row.get("symbol_validation_status"),
            "terminal_failure_type": row.get("terminal_failure_type"),
            "first_detected_at_ms": row.get("first_detected_at_ms"),
            "first_detected_utc": utc(row.get("first_detected_at_ms")),
            "symbol_effective_launch_times_ms": row.get("symbol_effective_launch_times_ms"),
            "symbol_effective_launch_times_utc": {
                k: utc(v) for k, v in (row.get("symbol_effective_launch_times_ms") or {}).items()
            },
            "symbol_onboard_times_ms": row.get("symbol_onboard_times_ms"),
            "symbol_onboard_times_utc": {
                k: utc(v) for k, v in (row.get("symbol_onboard_times_ms") or {}).items()
            },
        }, indent=2, ensure_ascii=False))

print("\n=== 1.5D event rows ===")
events_found = 0
for p in sorted((d_root / "events").glob("*.jsonl")):
    for line_no, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
        if article_id in line or symbol in line:
            events_found += 1
            print(p, line_no, line[:1500])
print("events_found", events_found)
PY
```

判定标准：

```text
上线前正常 pending:
  article_in_scheduler = true
  candidate_symbols contains SYMBOL
  symbol_validation_status = pending_pre_trading
  terminal_failure_type = null
  symbol_effective_launch_times_ms[SYMBOL] 晚于 watermark
  events_found = 0

上线后正常 handoff:
  1.5D events 中出现 symbols=[SYMBOL] + symbol_parse_status=parsed
  1.5F events_accepted 中出现 SYMBOL
  observation_age_basis = symbol_effective_launch_time 或 symbol_onboard_time
  announcement_time_capture_evidence_allowed = false 可接受
  launch_time_depth_evidence_allowed = true
  live_depth_evidence_basis = launch_time_only

异常:
  terminal_failure_type = candidate_validation_rejected
  symbol_parse_failed_reason = exchange_info_disallowed_contract_type
  events_rejected 中 reason = pre_watermark 且 symbol_effective_launch_times_ms[SYMBOL] 晚于 watermark
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
validation=rejected + symbol_parse_status=terminal_failed = exchangeInfo 明确拒绝，例如非允许 contractType 或资产不在 allowlist。
```

## 10. 首次输出判读模板

新一轮 detail endpoint fallback hotfix 部署后，首次输出应类似：

```text
STAGE1_5D_EVENTS_OUT = data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_detail_endpoint_fallback_hotfix
STAGE1_5F_OUT = data/external_signal_shadow/stage1_5f/live_depth_observer_<RUN_ID>_7d_detail_endpoint_fallback_hotfix

1.5D:
  heartbeat rows > 0
  request_manifest rows > 0
  detail_retry_scheduler_state.json exists or summary scheduler counters readable
  detail_fetch_fallback_attempt_count readable
  detail_fetch_attempt_manifest_mismatch_count = 0

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
status = normal_initial_detail_endpoint_fallback_hotfix_run
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
6. HTTP 202 + empty body 可以存在，但应进入 transient/backoff/degraded recent retry/fallback 语义，不能被误判为 parser 证据。
```

## 11. Stage 1.5G / Stage 1.5H 衔接

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

### 11.1 SPCXUSD1 Stage 1.5G clean evidence 主结论（2026-07-22）

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

export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_detail_endpoint_fallback_hotfix' | sort | tail -n 1)"
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
3. exchangeInfo 中 BTCU/ETHU 为允许 contractType，例如 PERPETUAL/TRADIFI_PERPETUAL，且 TRADING + quoteAsset=U + marginAsset=U 时，emit symbols=["BTCU","ETHU"]。
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

### 12.10 2026-07-11 Stage 1.5D detail endpoint degraded retry cadence + fallback hotfix

修复原因：
2026-07-10 Multiple TradFi 事件证明，scheduler starvation 修复后仍可能遇到另一个独立问题：Binance announcement detail endpoint 对某些文章长期返回 `HTTP 202` + empty body。此时 collector 已经公平地给新公告 detail fetch 机会，但 primary detail URL 仍拿不到可信 payload，导致 symbol 无法解析。

修复后语义：

```text
1. detail_retry_cycle_count 表示 scheduler 选中 article 的 logical retry cycle。
2. detail_http_request_count 表示真实 announcement_detail / fallback HTTP request 数量。
3. fallback request 必须计入 EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL。
4. fallback 只允许用于 HTTP 202 / empty untrusted payload；429/5xx/timeout/url_validation_failed 不允许同 poll fallback。
5. endpoint_health_by_variant 按 URL variant 分桶，primary degraded 不得污染 fallback URL。
6. fallback 成功必须保留 payload_trusted、detail_fetch_variant、detail_fetch_url_used 和 payload hash provenance。
7. 新部署必须使用 detail_endpoint_fallback_hotfix root，不得继续写旧 SKHYUSDT evidence root。
```

Stage 1.5G 衔接：

```text
SKHYUSDT old root 已完成 stage1_5g_depth_evidence_quarantined_pass。
allowed_next_action = write_stage1_5h_design_only。
clean_depth_evidence_pass = false。
execution_feasibility_claim_allowed = false。
```

### 12.11 2026-07-12 Stage 1.5D -> 1.5F fallback success probe

验证目的：
用受控 probe 验证“detail payload 成功解析后，1.5D 能写出 futures launch event，1.5F 能在 15min age gate 内接收该 event 并开始 depth observation”。该 probe 用于降低已知代码路径漏抓风险，不等价于真实 Binance detail endpoint 已完全恢复。

Probe root：

```text
stage1_5d_probe_root = data/external_signal_shadow/stage1_5d_probe/fallback_success_20260712T085203Z
stage1_5f_probe_root = data/external_signal_shadow/stage1_5f_probe/fallback_success_20260712T085203Z
```

关键结果：

```text
stage1_5d_event_emitted = true
source_article_id = probe-detail-fallback-success
symbol = SKHYUSDT
detail_fetch_status = success
symbol_parse_status = parsed
detail_payload_trusted = true
detail_fetch_variant = primary

event_age_ms_at_1_5f_accept = 688
max_event_age_ms = 900000
stage1_5f_decision = stage1_5f_observer_event_observation_in_progress
post_watermark_events_accepted = 1
active_observation_count = 1
total_snapshots_collected = 2
request_success_rate = 1.0
total_requests_made = 3
rejected_event_count = 0
```

1.5F safety flags remained false：

```text
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

判定：

```text
stage1_5d_to_1_5f_probe_status = passed
known_code_path_miss_risk = reduced
formal_12h_live_evidence_created = false
live_fallback_url_success_validated = false
```

边界说明：

```text
1. 本次 probe 验证的是 controlled detailPayload 成功路径和 1.5F age-gate/acceptance/depth snapshot 链路。
2. d0833e4ae9b542be90dbf3fe1c960c53 的 primary/detail fallback live URL 仍返回 HTTP 202 + empty body，不能用该 URL 证明 live fallback detail fetch 已恢复。
3. 本次 probe 不构成 Stage 1.5G formal 12h live depth evidence，也不允许 paper/live/execution/alpha 解释。
4. 下一次真实 futures_contract_launch 仍需观察 1.5D detail_fetch_status、symbol_parse_status、1.5F events_accepted、depth_snapshots 和 request_manifest depth rows。
```

### 12.12 2026-07-18 Stage 1.5D TRADIFI_PERPETUAL false negative hotfix

触发事件：

```text
source_article_id = 6cbb1b11a9c843949624cf2eacaac8b4
title = Binance Futures Will Launch USDⓈ-Margined SPCXUSD1 Perpetual Contract (2026-07-20)
source_published_at_ms = 1784277011242
stage1_5d_detected_at_ms = 1784301104843
launch_time_utc = 2026-07-20 09:00:00 UTC
```

现场现象：

```text
stage1_5d_list_payload_contains_article = true
stage1_5d_event_type = futures_contract_launch
stage1_5d_title_candidate_symbol = SPCXUSD1
stage1_5d_written_event_symbols = []
symbol_parse_status = terminal_failed
symbol_parse_failed_reason = exchange_info_disallowed_contract_type
terminal_failure_type = candidate_validation_rejected
stage1_5f_events_accepted = 0
```

根因：

```text
exchangeInfo 返回：
  symbol = SPCXUSD1
  status = PENDING_TRADING
  contractType = TRADIFI_PERPETUAL
  quoteAsset = USD1
  marginAsset = USD1
  onboardDate = 1784538000000

旧配置：
  EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES = ("PERPETUAL",)

结果：
  TRADIFI_PERPETUAL 被错误视为 disallowed contract type。
  1.5D 把有效 Binance Futures launch prelaunch row 误写成 terminal_failed。
```

修复内容：

```text
EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES = ("PERPETUAL", "TRADIFI_PERPETUAL")
```

回归测试覆盖：

```text
1. TRADIFI_PERPETUAL + USD1 + TRADING + title_contract_symbol
   => emit parsed SPCXUSD1 event-symbol, no detail fetch required.

2. TRADIFI_PERPETUAL + USD1 + PENDING_TRADING + title_contract_symbol
   => keep pending_pre_trading, no terminal_failed, no detail fetch required.
```

边界说明：

```text
1. 本次问题是 1.5D exchangeInfo validation false negative，不是 Binance list coverage 问题，也不是 1.5F depth observer 问题。
2. 修复只扩展 Binance futures perpetual contractType 白名单；仍要求公告标题被识别为 futures_contract_launch，且 quoteAsset/marginAsset 属于允许集合。
3. SPCXUSD1 公告发布时间早于当前重启后 watermark，不能手工改写为 clean formal post-watermark evidence。
4. SPCXUSD1 可作为 recovery/probe/regression candidate；正式 1.5F evidence 仍需等待 watermark 之后的新 futures launch event。
5. paper/live/execution/alpha flags 继续保持 false。
```

### 12.13 2026-07-18 Stage 1.5F delayed-launch watermark hotfix

触发原因：

```text
SPCXUSD1 在 1.5D hotfix 后进入 pending_pre_trading：
  source_article_id = 6cbb1b11a9c843949624cf2eacaac8b4
  first_detected_at_ms = 1784370927741
  first_detected_utc = 2026-07-18T10:35:27.741Z
  symbol_effective_launch_times_ms[SPCXUSD1] = 1784538000000
  symbol_effective_launch_time_utc = 2026-07-20T09:00:00Z

当前 1.5F watermark：
  max_seen_detected_at_ms = 1784370927741
  seen_source_article_contains_spcx = false
```

风险：

```text
bootstrap watermark 是启动边界，不是冻结边界。
1.5F accepted 新 event 后会继续前推 watermark。
如果 SPCXUSD1 在 launch 前仍 pending，而另一个 event 先被 1.5F accepted，watermark 可能前推到晚于 SPCXUSD1 first_detected_at_ms。
旧 1.5F 逻辑只看 detected_at_ms，会在 SPCXUSD1 launch 后将其误判为 pre_watermark。
```

修复内容：

```text
1. 普通事件仍使用 event_is_post_watermark(row, watermark)。
2. delayed launch contract-symbol 新增 launch-time-only 通道：
   - event_type = futures_contract_launch
   - source_article_id/event_id/stable_key 未被 watermark seen
   - symbol_extraction_source in {title_contract_symbol, detail_contract_symbol}
   - symbol_validation_status = validated
   - symbol_effective_launch_times_ms 或 symbol_onboard_times_ms 中存在该 symbol
   - launch/onboard time > watermark.max_seen_detected_at_ms
3. 满足上述条件时，即使 detected_at_ms < running watermark，也允许进入 1.5F eligibility。
4. accepted 后 watermark 不回退 max_seen_detected_at_ms；重复处理由 observer_state.jsonl 的 event-symbol state 防止。
```

证据边界：

```text
announcement_time_capture_evidence_allowed = false
launch_time_depth_evidence_allowed = true
live_depth_evidence_basis = launch_time_only
```

回归测试覆盖：

```text
1. delayed launch event: detected_at_ms < running watermark, launch_time > watermark, identity unseen
   => eligible / pending-by-future-launch / accepted-after-launch。

2. delayed launch event identity already seen by watermark
   => rejected pre_watermark。

3. detected_at_ms < watermark 且无 per-symbol launch/onboard metadata
   => rejected pre_watermark。

4. accepted older delayed-launch event 不得回退 max_seen_detected_at_ms；event-symbol 去重必须依赖 observer_state.jsonl。
```

边界说明：

```text
1. 本次是 1.5F eligibility/watermark 小修，不改变 1.5D parser 或 scheduler。
2. 该修复不把 delayed launch recovery 样本升级为 clean announcement-capture evidence。
3. 该修复只降低 delayed launch 盘口采集被 running watermark 挤掉的风险。
4. paper/live/execution/alpha flags 继续保持 false。
5. 部署后建议新建 1.5D/1.5F root，避免旧 root 混用旧 eligibility 口径。
```

---

## 16. 2026-07-21 f434 Multiple TradFi Missed-Event Diagnostic & Stage 1.5D Overdue Starvation Hotfix

### 16.1 事件诊断纪录

```text
2026-07-21 f434 Multiple TradFi missed-event diagnostic:
  article list capture succeeded
  detail endpoint returned repeated 202 empty
  candidate_symbols remained null
  next_detail_retry overdue ~= 19.7h
  endpoint degraded window expired ~= 10.8h
  1.5D event not emitted
  1.5F accepted/rejected absent
  result = missed formal 1.5F evidence
  required action = Stage 1.5D detail retry overdue starvation hotfix
```

### 16.2 证据边界

```text
This missed event must not be manually backfilled into formal Stage 1.5F evidence.
It may only be used as regression/recovery validation for the overdue starvation hotfix.
```

### 16.3 部署后检查点

```text
1. New 1.5D root heartbeat grows (suffix = _7d_detail_retry_overdue_starvation_hotfix).
2. New 1.5F root heartbeat grows (suffix = _7d_detail_retry_overdue_starvation_hotfix).
3. Root suffix matches overdue hotfix.
4. detail_retry_overdue_pending_count is present in summary.
5. pending articles with next_detail_retry_at_ms <= now appear in manifest retries or explicit overdue diagnostics.
6. 1.5F continues using the new root and accepts only emitted event rows.
7. old root remains read-only.
```
