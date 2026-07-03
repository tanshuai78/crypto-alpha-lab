# External Signal Shadow Lab Stage 1.5F Live Depth Observer Review

**日期:** 2026-07-01  
**对应设计:** `docs/designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md`  
**对应实现计划:** `docs/plans/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-implementation-plan_CN.md`  
**当前运行重点:** Stage 1.5D title-contract symbol + transient detail retry hotfix source collector + Stage 1.5F delayed-launch age gate hotfix live depth observer

## 1. 当前结论

```text
decision = stage1_5f_running_waiting_for_post_watermark_event
implementation_status = completed_and_locally_verified
live_depth_evidence_status = not_collected_yet
current_server_mode = 7d_delayed_launch_age_gate_hotfix_observation
stage1_5g_allowed = plan_only_until_completed_12h_depth_observation
```

当前可以做：

```text
1. 保持 Stage 1.5D title-contract/transient-detail hotfix 版 7d collector 运行。
2. 重新 bootstrap 并启动 Stage 1.5F delayed-launch age gate hotfix 版 live depth observer。
3. 定期检查 raw payload、1.5D events、1.5F summary。
4. 先写 Stage 1.5G Live Depth Evidence Review plan。
```

当前不能做：

```text
1. 不能声明 execution_feasibility_proven。
2. 不能声明 alpha。
3. 不能启动 paper/live trading。
4. 不能把旧事件当前盘口倒推为历史 12h entry 可成交。
5. 不能用少量 depth snapshot 宣称执行可行。
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
P0: 维持 title-contract/transient-detail hotfix 版 1.5D collector + delayed-launch age gate hotfix 版 1.5F observer，并每 2-4 小时巡检。
理由: 当前没有 post-watermark 新事件，主要风险是进程静默退出、路径变量误查、或 raw payload 中出现新事件但 events 未写入。

P1: 等待 Stage 1.5D 写入 watermark 之后的新 futures_contract_launch event-symbol。
理由: 只有 post-watermark 新事件才有资格进入 1.5F live depth observation；旧事件不能补完整 12h 盘口证据。

P2: 一旦 1.5F 出现 post_watermark_events_accepted > 0，切换到 30-60 分钟巡检频率。
理由: 新事件后的前 12h 是证据窗口，必须确认 active_observation_count、depth_snapshots、request_success_rate 正常增长。

P3: 等至少一个 event-symbol 完成 12h observation，再执行 Stage 1.5G Live Depth Evidence Review。
理由: 1.5G 审查的是完整 depth evidence，不是观察器是否启动；没有足量 snapshots 时不能给执行可行性结论。

P4: 如果 1.5G 判定 depth evidence 不足或盘口质量差，保留 no-trade 结论并回到事件源等待。
理由: 小币 futures launch 的 Kline replay 可能是纸面幻觉，真实 depth 证据不足时必须维持安全 no-op。

P5: 如果 1.5G 判定 depth evidence 足够且盘口质量通过，只允许进入 Stage 1.5H shadow execution simulator 设计/计划。
理由: depth evidence 只能说明“值得模拟执行审查”，不能直接证明 alpha，也不能跳到 paper/live。
```

并行可做：

```text
1. 编写 Stage 1.5G review design / implementation plan。
2. 整理 7d artifacts rsync 回本地的命令。
3. 把当前监控命令沉淀为 docs/ops 或 shell helper。
4. 定期复核 safety grep，确保没有 private endpoint、api key、order endpoint。
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

### 4.1 当前应使用的 delayed-launch age gate hotfix 路径

```bash
export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_title_contract_transient_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix"
export STAGE1_5D_VALIDATION_SUMMARY="data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"
```

delayed-launch age gate hotfix 部署后应记录的实际路径：

```text
STAGE1_5D_EVENTS_OUT = data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_title_contract_transient_hotfix
STAGE1_5F_OUT = data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix
```

### 4.2 不再作为当前监控目标的旧路径

以下路径是历史 run 或旧 7d run，不应作为当前 hotfix 监控主路径：

```text
data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d
data/external_signal_shadow/stage1_5f/live_depth_observer_7d
data/external_signal_shadow/stage1_5d/live_event_source_continuous_*_7d_empty_detail_retry_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_empty_detail_retry_hotfix
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_title_contract_transient_hotfix
data/external_signal_shadow/stage1_5d/live_event_source_smoke_interrupted_*
data/external_signal_shadow/stage1_5d/live_event_source_smoke_invalid_*
```

保留它们用于历史排障，不要混入当前 hotfix 证据链。

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

本次 hotfix 修复三类 Stage 1.5D 漏采/误解析问题：

```text
1. Multiple USDⓈ-Margined TradFi Perpetual Contracts：标题没有完整 symbols，需要从 detail payload 抽取 XXXUSDT / XXXUSDC。
2. BTCU/ETHU U-settled launch：标题/detail 只有 BTCU、ETHU，这些是 raw contract symbols，不允许自动拼成 BTCUUSDT / ETHUUSDT。
3. exchangeInfo validation：detail_contract_symbol 候选必须用 Binance USD-M exchangeInfo 结构化验证 contractType/status/quoteAsset/marginAsset/onboardDate；未验证候选不得写入 parsed event。
```

关键语义：

```text
1. BTCU/ETHU 在 exchangeInfo 中存在且 quoteAsset=U、marginAsset=U、contractType=PERPETUAL、status=TRADING 时，Stage 1.5D emit symbols=["BTCU", "ETHU"]。
2. 如果 exchangeInfo 只有 BTCUUSDT，但候选是 BTCU，不得把 BTCU 改写成 BTCUUSDT；应保持 pending_exchangeinfo_missing。
3. 如果 exchangeInfo 明确 rejected，例如 contractType 非 PERPETUAL，应写 terminal diagnostic event，不能静默留在 retry state。
4. Stage 1.5F depth request 必须使用 raw symbol=BTCU，不得拼成 BTCUUSDT。
```

部署纪律：

```text
1. 不复用旧 7d output root。
2. 不覆盖旧 events/*.jsonl。
3. hotfix 部署后启动新的 1.5D output root。
4. 对新的 1.5D root bootstrap 一个匹配的新 1.5F output root。
```

## 7. 部署 Runbook

### 7.1 本地验证并同步到服务器

在本地 Mac 执行：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export SERVER="root@47.82.4.85"

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q

# 本地当前完整验证结果：1428 passed
# 如需提交前全仓复核：
# PYTHONPATH=src:. .venv/bin/python -m pytest -q

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

本次 hotfix 只要求重启 Stage 1.5F。Stage 1.5D title-contract/transient-detail collector 可以继续运行，因为事件源 parser/collector 本次未改。

### 7.2 服务器 pytest 依赖修复

如果服务器报：

```text
/root/crypto-alpha-lab/.venv/bin/python: No module named pytest
```

执行：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

which python
python -V
python -m pip --version

python -m pip install -U pip
python -m pip install -e ".[dev]"
```

如果 `pip` 不可用：

```bash
python -m ensurepip --upgrade
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

服务器最小验证：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

预期：

```text
44 passed 左右
```

### 7.3 停止旧 Stage 1.5F observer

本次不默认停止 Stage 1.5D collector。只停止旧 1.5F observer，避免两个 observer 同时消费不同 output root：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

tmux ls
ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

tmux kill-session -t stage1_5f_live_depth_7d 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_u_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_empty_detail_retry_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_title_contract_transient_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_7d_delayed_launch_age_gate_hotfix 2>/dev/null || true
```

如果 Stage 1.5D collector 不在运行，再使用 7.4 启动；否则跳过 7.4。

### 7.4 可选：启动 Stage 1.5D title-contract/transient-detail 7d collector

仅当 `ps` 没有看到 `run_stage1_5d_live_event_source_smoke_collector.py` 时执行：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
export STAGE1_5D_EVENTS_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_${RUN_ID}_7d_title_contract_transient_hotfix"

tmux new -d -s stage1_5d_continuous_7d_title_contract_transient_hotfix "
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

### 7.5 Bootstrap delayed-launch age gate hotfix 版 Stage 1.5F watermark

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

mkdir -p data/external_signal_shadow/stage1_5e/execution_feasibility

if [ ! -f data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json ]; then
  cp "$(find data/external_signal_shadow/stage1_5e -type f -name execution_feasibility_audit_summary.json | sort | tail -n 1)" \
    data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
fi

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_title_contract_transient_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix"
export STAGE1_5D_VALIDATION_SUMMARY="data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"

# 新 root，只用于 delayed-launch age gate hotfix；bootstrap rows 不产生正式 live evidence。
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

### 7.6 启动 delayed-launch age gate hotfix 版 Stage 1.5F observer

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_title_contract_transient_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix"
export STAGE1_5D_VALIDATION_SUMMARY="data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json"
export STAGE1_5E_SUMMARY="data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json"

tmux new -d -s stage1_5f_live_depth_7d_delayed_launch_age_gate_hotfix "
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

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_title_contract_transient_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix"

date -u
tmux ls
ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null || true
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || true
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/events_rejected" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20
```

## 8. 日常监控

### 8.1 一键设置路径

每次 SSH 新窗口先执行：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_title_contract_transient_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix"

echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

### 8.2 进程和摘要检查

```bash
date -u
tmux ls
ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null || true
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || true
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/events_rejected" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20

if [ -f "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" ]; then
  cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json"
else
  echo "1.5D summary not written yet; active 7d run should be monitored via heartbeats/events/request_manifest."
fi
wc -l "$STAGE1_5D_EVENTS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/events/*.jsonl 2>/dev/null || true
tail -n 3 "$STAGE1_5D_EVENTS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
tail -n 3 "$STAGE1_5D_EVENTS_OUT"/events/*.jsonl 2>/dev/null || true
du -sh "$STAGE1_5D_EVENTS_OUT"/raw_payloads 2>/dev/null || true
```

判读：

```text
1.5D heartbeats 行数增长 = source collector 活着。
1.5D events 行数增长 = 发现 futures launch event row；不等于 1.5F 已接受。
1.5F heartbeat_count 增长 = depth observer 活着。
post_watermark_events_accepted = 0 = 还没有 watermark 之后的新 event-symbol 被接受。
active_observation_count > 0 = 正在对新事件采 12h depth。
total_snapshots_collected 增长 = 已开始写入盘口快照。
detail_pending_retry_count 增长 = detail 页面暂不可用且已发生 detail fetch retry；不包含 title candidate 的 exchangeInfo pre-trading/pending。
detail_empty_payload_count 增长 = detail response 为空，例如 HTTP 202 + 0 byte；这是本次 hotfix 重点监控项。
detail_terminal_failed_count 增长 = detail 已进入明确终态失败，需要检查对应 request_manifest 和 events row。
pre_launch_validation_deferred_count 增长 = title/exchangeInfo 候选已经识别，但 symbol 还不是 TRADING，不应进入 1.5F depth。
```

监控频率：

```text
前 30 分钟：每 5 分钟检查一次。
之后：每 2-4 小时检查一次。
如果 post_watermark_events_accepted > 0：每 30-60 分钟检查 depth_snapshots。
如果 active_observation_count > 0：保持 12h 观察窗口内的定期巡检。
```

## 9. Raw Payload 与 Events 检查

### 9.1 查看 1.5F watermark 时间

```bash
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix"

python - <<'PY'
import json
from datetime import datetime, timezone
from pathlib import Path
import os

p = Path(os.environ["STAGE1_5F_OUT"]) / "watermark.json"
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

`grep` 只适合粗筛，会命中旧标题或非 launch 文本。是否真是新事件，要继续看 `releaseDate` 和 events。

### 9.3 解析 raw payload 并按 releaseDate 列出最新 launch 标题

公告官网：https://www.binance.com/en/support/announcement/list/48
每次 SSH 新窗口先执行：
```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate
export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_title_contract_transient_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix"
echo "STAGE1_5D_EVENTS_OUT=[$STAGE1_5D_EVENTS_OUT]"
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
```

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
    print("title", row.get("title"))
PY
```

判读：

```text
raw payload 有新 launch，但 events 没写入或 symbols=[] = parser/normalizer 覆盖问题。
events 中 symbols 非空 + parsed = 1.5D 成功产出 event-symbol。
events 中 detected_utc 晚于 watermark utc_time = 1.5F 理论上应接受为 post-watermark。
source=title_contract_symbol + validation=validated = 标题中 ETHUSD1 这类 raw contract symbol 直抽并通过 exchangeInfo 验证。
source=detail_contract_symbol + validation=validated + symbols=["BTCU","ETHU"] = U-settled raw contract symbol hotfix 路径生效。
source=detail_base_asset_derived + validation=validated = base-asset-plus-quote fallback 路径生效，但不能用于 BTCU/ETHU 这类 raw U-settled symbol。
source=detail + validation=validated_by_exact_text = detail 原文完整 XXXUSDT/XXXUSDC symbol 路径生效。
validation=pending_exchangeinfo_missing = 候选 symbol 还未出现在 exchangeInfo，不能写入 parsed event。
validation=rejected + symbol_parse_status=terminal_failed = exchangeInfo 明确拒绝，例如非 PERPETUAL 或资产不在 allowlist。
```

## 10. delayed-launch age gate hotfix 首次输出判读模板

delayed-launch age gate hotfix 重新部署后，首次输出应类似：

```text
STAGE1_5F_OUT = data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix
STAGE1_5D_EVENTS_OUT = data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_title_contract_transient_hotfix

decision = stage1_5f_observer_running_no_new_event
stage1_5e_context_missing = false
watermark_present = true
post_watermark_events_accepted = 0
active_observation_count = 0
total_snapshots_collected = 0
request_success_rate = 1.0
failed_requests_count = 0
heartbeat_count = 1

1.5F heartbeat rows = 1
1.5F events_accepted rows = 0
1.5D heartbeat rows = 5
1.5D events rows = 26
```

判读：

```text
status = normal_initial_delayed_launch_age_gate_hotfix_run
path_status = correct_delayed_launch_age_gate_hotfix_paths
1.5D_status = running_and_writing_heartbeats
1.5F_status = running_and_waiting_for_post_watermark_event
depth_collection_status = not_started_because_no_new_post_watermark_event_symbol
```

说明：

```text
1. `1.5D events = 26` 是当前 root 中已有 event rows，不代表 1.5F 已接受；实际数字按新 root 启动时点变化。
2. `post_watermark_events_accepted = 0` 表示 1.5F 尚未接受 watermark 之后的新 event-symbol。
3. `active_observation_count = 0` 和 `total_snapshots_collected = 0` 在无新事件时正常。
4. `heartbeat_count = 1` 表示 1.5F 刚启动；后续应持续增长。
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

### 12.5 2026-07-02 empty detail payload incident

2026-07-02 incident: Binance announcement detail returned HTTP 202 + 0-byte body.
Old behavior: treated as success, persisted empty payload, emitted symbols=[] terminal_failed.
Fixed behavior: treats as transient detail unavailable, writes manifest failure, keeps pending_retry, no terminal event.

Rollout policy:

```text
Formal observation:
  Use a new Stage 1.5D output root.
  Use a new Stage 1.5F output root.
  Bootstrap the new Stage 1.5F root from the new Stage 1.5D root.
  Only events after this new watermark can count as formal 12h live depth evidence.

Recovery validation:
  Use a separate output root containing recovery_validation in the name.
  Already-seen articles such as d2acaa91c14e4cc598aaee1017efc1ac can validate parser/retry behavior.
  Recovery validation must not be labeled valid 12h live depth evidence because the initial live window may already be missed.
  Do not mix recovery_validation artifacts into the formal Stage 1.5F evidence root.
```

Monitoring command:
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

### 12.6 2026-07-02 ETHUSD1 and transient detail retry hotfix (M3)

2026-07-02 live incident:
- ETHUSD1 title event exposed title raw contract symbol gap.
- Multiple TradFi and ETHUSD1 exposed Binance detail HTTP 202 + empty persistence.
- Fix target is future events only; already-watermarked/terminal rows are recovery validation only.
- It is forbidden to use reparsed 23c9b8e88309409cbcd8509af0b78d10 or d2acaa91c14e4cc598aaee1017efc1ac rows as official 12h live depth evidence.

Post-hotfix verification command:
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

### 12.7 2026-07-03 Delayed Launch Age Gate and Evidence Labeling Rules (M3)

Deployment target after this hotfix:

```text
Stage 1.5D root: live_event_source_continuous_*_7d_title_contract_transient_hotfix
Stage 1.5F root: live_depth_observer_7d_delayed_launch_age_gate_hotfix
Stage 1.5F tmux: stage1_5f_live_depth_7d_delayed_launch_age_gate_hotfix
```

Delayed contract launch (e.g., onboarded hours before launch) incidents exposed limitation in using detected_at_ms for the 15-minute observation age gate, leading to premature rejections.

Implementation checks:
- `symbol_effective_launch_times_ms[symbol]` / `symbol_onboard_times_ms[symbol]` can be used as `observation_age_base_ms`.
- `symbol_resolved_at_ms` is allowed only with delayed-launch evidence; ordinary late parser retry rows fall back to `detected_at_ms`.
- `pending, launch_time_in_future` must not write `events_rejected/*.jsonl` and must not advance watermark.
- accepted/rejected rows must include `observation_age_base_ms`, `observation_age_basis`, `event_age_ms`, `max_event_age_ms`, `watermark_max_seen_detected_at_ms`, and `watermark_version`.

Evidence labeling guardrails:
1. `announcement_and_launch_time`:
   - Both announcement capture (detected_at_ms) and launch/onboard time (symbol_effective_launch_times_ms / symbol_onboard_times_ms) are strictly after the watermark.
   - This represents fully valid, zero-lag announcement edge evidence.
2. `launch_time_only`:
   - Announcement capture was before/equal to watermark, but launch/onboard time is after the watermark.
   - Live depth observer can still capture the launch orderbook, but this evidence does not prove announcement edge.
3. `recovery_validation_only`:
   - Both announcement capture and launch/onboard time are before/equal to the watermark.
   - Used for debugging parser, retry, and loader behaviors only. Strictly forbidden from being merged into formal evidence.
