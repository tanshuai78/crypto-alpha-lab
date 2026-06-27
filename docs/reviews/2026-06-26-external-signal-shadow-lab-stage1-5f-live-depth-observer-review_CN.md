# External Signal Shadow Lab Stage 1.5F Live Depth Observer Review

**日期:** 2026-06-27  
**对应计划:** `docs/plans/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-implementation-plan_CN.md`  
**对应设计:** `docs/designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md`

## 1. 当前决策

```text
decision = stage1_5f_implementation_ready_pending_live_depth_evidence
implementation_status = completed_and_locally_verified
live_depth_evidence_status = not_collected_yet
stage1_5d_dependency_status = running_24h_source_smoke
stage1_5g_allowed = false_until_completed_12h_depth_observation
```

本轮 Stage 1.5F 代码实现已经完成，并且本地针对 `stage1_5f_live_depth_observer` 的测试已通过。  
但这不等于 Stage 1.5F 的 live depth evidence 已经成功，因为正式 1.5F 需要等 Stage 1.5D 持续 source smoke 产出稳定的 24h evidence，并且在 `watermark` 之后捕捉到新的 `futures_contract_launch` event-symbol，再连续采集约 12h public depth snapshots。

当前结论必须保守理解为：

```text
1. 1.5F 工程实现已经具备运行条件。
2. 1.5F 的真实盘口证据尚未完成。
3. 不能声明 execution_feasibility_proven。
4. 不能声明 alpha。
5. 不能进入 paper/live/execution engine。
```

## 2. Safety Boundaries

Stage 1.5F 的边界保持不变：

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

Stage 1.5F 只做一件事：用 Binance USD-M public depth endpoint 记录真实新事件之后的盘口证据。  
它不是交易模块，不生成 `SignalCandidate`，不生成 `TradeIntent`，不连接私有账户接口。

## 3. 代码完成情况

本轮实现新增了 Stage 1.5F live depth observer 的主要模块：

```text
src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_metrics.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_budget.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py
scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
scripts/external_signal_shadow/review_stage1_5f_live_depth_observer.py
```

已覆盖的关键工程语义：

```text
1. bootstrap watermark mode。
2. atomic watermark write。
3. corrupted watermark invalid handling。
4. same detected_at_ms but unseen event/article 仍可被识别为 post-watermark。
5. event_symbol_id 稳定生成。
6. observer_state startup compaction。
7. restart resume active observation。
8. expired active observation 不会重置 12h window。
9. exchangeInfo refresh cache。
10. request budget precheck。
11. public depth endpoint live flag hard gate。
12. mock-response-dir fixture mode 禁止真实网络。
13. request_manifest 写 payload hash / payload size。
14. heartbeat 每轮 poll 写入。
15. summary 区分 bootstrap / running / in_progress / depth_evidence_collected / invalid / failed。
```

本地验证记录：

```text
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/scripts/external_signal_shadow/test_*stage1_5f* -q

结果: 86 passed
```

```text
ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_*.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  scripts/external_signal_shadow/review_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/scripts/external_signal_shadow/test_*stage1_5f*

结果: All checks passed
```

## 4. 当前服务器状态

根据当前人工排查记录，服务器上 Stage 1.5D 已经重新启动为干净 24h run：

```text
session = stage1_5d_24h_clean
STAGE1_5D_OUT = data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z
```

最近检查显示：

```text
heartbeats 正在增长
raw_payloads 正在增长
events 已有 futures launch rows
poll_success = true
actual_poll_interval_sec 约 60.x 秒
```

这说明当前 Stage 1.5D collector 正在工作。  
但它还没有自然跑完 24h，因此不能把这个 run 当成正式完成的 1.5D 证据。

需要注意：之前存在两个异常 run：

```text
1. stage1_5d_smoke 曾因 max_raw_payload_bytes_per_day_exceeded 停止。
2. 一次启动时 OUT_ROOT 为空，导致 --output-root 为空、summary 写到 /binance_futures_launch_smoke_summary.json。
```

这些异常 run 不能作为正式 24h source smoke 证据使用，只能作为排障记录。

## 5. 部署配置风险

本地 `configs/base.py` 当前仍显示：

```text
EXTERNAL_SIGNAL_STAGE1_5D_MAX_RAW_PAYLOAD_BYTES_PER_DAY = 50_000_000
```

服务器上为了避免 24h source smoke 中途再次触发 raw payload budget，可能已经临时调大到 `200_000_000`。  
如果服务器代码和本地代码不一致，需要在同步前明确：

```text
1. 如果 50MB 足够当前新 run，则不必改。
2. 如果 24h run 仍可能超 50MB，应把预算变更正式写入 configs/base.py 并提交。
3. 不要只在服务器热改后忘记同步，否则下一次 rsync 可能把服务器修复覆盖掉。
```

建议当前每 2-4 小时检查一次：

```bash
STAGE1_5D_OUT=data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z

du -sh "$STAGE1_5D_OUT"/raw_payloads
wc -l "$STAGE1_5D_OUT"/heartbeats/*.jsonl
wc -l "$STAGE1_5D_OUT"/events/*.jsonl
tail -n 3 "$STAGE1_5D_OUT"/heartbeats/*.jsonl
ps -ef | grep run_stage1_5d_live_event_source_smoke_collector | grep -v grep
```

## 6. Stage 1.5F 的原理和目的

大白话：Stage 1.5F 是一个“实时盘口录像机”。

前面 Stage 1.5C replay 发现：某些 Binance futures launch 事件在 12h long direction 上看起来有结构。  
Stage 1.5E 又提醒：历史 Kline 只能说明价格波动大、成交环境可能差，但不能证明当时真实盘口能不能成交。

所以 Stage 1.5F 要做的是：

```text
当 Binance 之后真的又发布新的 futures_contract_launch 公告时，
我们不要只看 close price，
而是在公告被 1.5D 捕捉之后，
对对应 symbol 连续 12h 抓 Binance USD-M public depth，
记录真实 bid/ask spread、top depth、500 USDT buy/sell slippage proxy。
```

它回答的问题是：

```text
1. 新合约上线后，盘口是不是薄到离谱？
2. 500 USDT 这种很小的测试规模，在盘口上会不会已经产生明显滑点？
3. 12h 观察窗口内，盘口质量是稳定、改善，还是持续恶化？
4. close-price replay 是不是可能只是纸面幻觉？
```

它不回答的问题是：

```text
1. 这个事件一定能赚钱吗？不能。
2. 现在可以交易吗？不能。
3. 这个盘口证明可以执行吗？还不能。
4. 可以启动 paper/live 吗？不能。
```

Stage 1.5F 成功以后，下一步才是 Stage 1.5G：对收集到的 live depth evidence 做正式审查。

## 7. 专业术语解释

### 7.1 bootstrap

`bootstrap` 可以理解为“划起跑线”。

当我们第一次启动 1.5F 时，Stage 1.5D 的 events 文件里可能已经有很多旧事件。  
这些旧事件可能是几小时、几天、甚至几个月前的公告。它们已经错过了真实 12h 盘口观察窗口，不能再拿来当“新事件”采盘口。

所以先运行：

```bash
--bootstrap-watermark
```

它只做一件事：读取当前已有 events，把它们记为“已经看过”，然后写入 `watermark.json`。  
它不会采 depth，不会生成交易结论。

一句话：bootstrap 是为了防止 1.5F 把历史旧事件误当成新事件。

### 7.2 watermark

`watermark` 是“水位线”或“事件边界”。

它记录：

```text
max_seen_detected_at_ms
seen_event_ids
seen_source_article_ids
seen_stable_event_keys
watermark_version
watermark_updated_at_ms
```

以后 1.5F 每次读 Stage 1.5D events 时，会问：

```text
这个事件是不是 watermark 之后的新事件？
```

如果不是，就忽略。  
如果是，并且 event age 没超过启动观察窗口，就开始对它采 12h depth。

一句话：watermark 是 1.5F 判断“旧事件”和“新事件”的安全边界。

### 7.3 event-symbol

一篇 Binance futures launch 公告可能包含多个 symbol，例如：

```text
AMDUSDT, QCOMUSDT, USARUSDT
```

1.5F 不按“文章”采盘口，而是按“事件 + symbol”采盘口。  
这就是 `event_symbol_id`。

一句话：一篇公告里有 3 个 symbol，就有 3 个 event-symbol 观察对象。

### 7.4 depth snapshot

`depth snapshot` 是一次盘口快照。  
它来自 Binance USD-M public depth endpoint，包含 bid/ask order book。

1.5F 会从每次快照里计算：

```text
best_bid
best_ask
mid_price
spread_bps
top_bid_depth_usdt
top_ask_depth_usdt
buy_slippage_bps_for_500usdt
sell_slippage_bps_for_500usdt
```

一句话：depth snapshot 是用来判断真实盘口厚不厚、滑点大不大的原始证据。

### 7.5 observation window

Stage 1.5F 预注册的观察窗口是 12h：

```text
EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS = 12h
EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC = 60
EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COVERAGE_RATIO = 0.80
```

如果 60 秒采一次，12h 理论上约 720 次快照。  
80% 覆盖率意味着至少需要约 576 次有效快照。

一句话：不是随便抓几次盘口就算完成，必须覆盖完整 12h 窗口的大部分时间。

### 7.6 request_manifest

`request_manifest` 是请求审计账本。  
它记录每次 public request 的请求时间、HTTP 状态、payload 大小、payload hash、错误信息等。

一句话：以后 review 能知道“到底有没有真实请求过 Binance，返回了什么规模的数据”。

### 7.7 heartbeat

`heartbeat` 是进程心跳。  
每轮 poll 写一行，表示 collector/observer 还活着，并记录 active count、error、budget 等状态。

一句话：heartbeat 用来判断服务器程序是不是还在正常跑，而不是静默死掉。

## 8. 正确操作流程

### Step 1: 先让 Stage 1.5D 干净 run 跑满 24h

当前应继续观察：

```bash
STAGE1_5D_OUT=data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z

ps -ef | grep run_stage1_5d_live_event_source_smoke_collector | grep -v grep
wc -l "$STAGE1_5D_OUT"/heartbeats/*.jsonl
du -sh "$STAGE1_5D_OUT"/raw_payloads
tail -n 3 "$STAGE1_5D_OUT"/heartbeats/*.jsonl
```

24h 正常结束后检查：

```bash
cat "$STAGE1_5D_OUT/binance_futures_launch_smoke_summary.json"
```

期望至少看到：

```text
decision = stage1_5d_event_detection_passed 或 operational_pass_event_detection_unvalidated
blockers = []
research_result_valid = true
poll_count 接近 1440
observation_hours >= 24
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

如果 `binance_futures_launch_smoke_summary.json` 不存在，说明 1.5D 还没自然结束或异常退出。

### Step 2: 拉回 1.5D artifacts 到本地

在本地执行：

```bash
rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/ \
  data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/
```

### Step 3: 生成或更新 Stage 1.5D review

如果已有 1.5D review，则根据最终 summary 更新：

```text
docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md
```

### Step 4: 为 Stage 1.5F 选择正式 input

1.5F 最好消费一个仍会继续增长的 Stage 1.5D output root。  
如果 24h run 已经结束，它只能用于 bootstrap 或历史审查，不能继续产生新事件。

推荐操作是：

```text
1. 用已完成 24h run 证明 Stage 1.5D source collector 可用。
2. 启动一个新的长期 Stage 1.5D continuous run。
3. 对这个新的 continuous run 做 Stage 1.5F bootstrap。
4. 让 1.5F 跟着这个 continuous run 等新事件。
```

### Step 5: bootstrap Stage 1.5F watermark

```bash
STAGE1_5D_OUT=data/external_signal_shadow/stage1_5d/live_event_source_smoke_YYYYMMDDTHHMMSSZ
STAGE1_5F_OUT=data/external_signal_shadow/stage1_5f/live_depth_observer

PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob "$STAGE1_5D_OUT/events/*.jsonl" \
  --stage1-5d-summary "$STAGE1_5D_OUT/binance_futures_launch_smoke_summary.json" \
  --stage1-5e-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json \
  --output-root "$STAGE1_5F_OUT" \
  --bootstrap-watermark
```

检查：

```bash
cat "$STAGE1_5F_OUT/watermark.json"
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json"
```

bootstrap 的 summary 应显示：

```text
decision = stage1_5f_observer_bootstrap_watermark_only
live_depth_observation_allowed = false
```

### Step 6: 启动 Stage 1.5F live observer

```bash
tmux new -d -s stage1_5f_live_depth "
cd /root/crypto-alpha-lab &&
source .venv/bin/activate &&
STAGE1_5D_OUT='data/external_signal_shadow/stage1_5d/live_event_source_smoke_YYYYMMDDTHHMMSSZ' &&
STAGE1_5F_OUT='data/external_signal_shadow/stage1_5f/live_depth_observer' &&
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob \"\$STAGE1_5D_OUT/events/*.jsonl\" \
  --stage1-5d-summary \"\$STAGE1_5D_OUT/binance_futures_launch_smoke_summary.json\" \
  --stage1-5e-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json \
  --output-root \"\$STAGE1_5F_OUT\" \
  --live-public-readonly
"
```

### Step 7: 监控 Stage 1.5F

```bash
STAGE1_5F_OUT=data/external_signal_shadow/stage1_5f/live_depth_observer

tmux ls
ps -ef | grep run_stage1_5f_live_depth_observer | grep -v grep
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null || true
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || true
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/events_rejected" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
```

如果长时间没有新事件，正常状态可能是：

```text
stage1_5f_observer_running_no_new_event
```

这不是失败，只代表 watermark 后还没有新的 Binance futures launch event-symbol。

如果出现新事件且开始采 depth，状态应进入：

```text
stage1_5f_observer_event_observation_in_progress
```

如果至少一个 event-symbol 完成 12h 观察且覆盖率达标，才可能进入：

```text
stage1_5f_observer_depth_evidence_collected
```

### Step 8: 生成正式 Stage 1.5F review

当 `live_depth_observer_summary.json` 存在且有 completed observation 后：

```bash
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5f_live_depth_observer.py \
  --summary data/external_signal_shadow/stage1_5f/live_depth_observer/live_depth_observer_summary.json \
  --output-review docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

如果目前没有 completed observation，不要把 review 写成成功，只能保留为 `pending_live_depth_evidence`。

## 9. 后续试验是否可能成功

需要拆成两个层面看。

### 9.1 工程上是否可能成功

有可能，而且概率相对较高。  
原因：

```text
1. 1.5D 已经能稳定 poll Binance announcement source。
2. 1.5F 已经实现 watermark、event-symbol tracking、public depth fetch、request manifest、heartbeat、state resume。
3. mock / fixture 测试已经验证基本状态机能工作。
4. 服务器已经具备 tmux + venv 长时间运行环境。
```

工程上主要风险：

```text
1. 1.5D raw_payload budget 再次触顶。
2. 服务器进程中断或 OUT_ROOT 配错。
3. Binance announcement schema drift。
4. Binance public endpoint 临时失败。
5. 新事件太少，等待周期较长。
```

### 9.2 研究上是否可能成功

不确定，且难度明显高于工程成功。  
原因：

```text
1. Stage 1.5E 已经显示 execution_feasibility_proxy_failed。
2. futures launch 小币在 launch 后价格和盘口可能剧烈重定价。
3. 12h long replay 看起来有结构，但可能是 close-price replay 幻觉。
4. 真正决定能不能做的是 live bid/ask spread、depth、slippage、gap 和稳定性。
```

Stage 1.5F 成功的最低条件：

```text
1. watermark 后出现新的 Binance futures_contract_launch event-symbol。
2. 事件被 1.5D 及时捕捉。
3. 该 symbol 在 Binance USD-M exchangeInfo 中存在。
4. 1.5F 在 event age gate 内启动 observation。
5. 12h 内 public depth requests success rate >= 0.95。
6. snapshot coverage ratio >= 0.80。
7. max snapshot gap 不超过配置阈值。
```

即使满足这些条件，也只能说明：

```text
可以进入 Stage 1.5G Live Depth Evidence Review。
```

不能直接说明：

```text
可以交易
可以 paper
可以 live
alpha 已验证
execution feasibility 已证明
```

## 10. 当前推荐下一步

```text
priority_1 = 让当前 Stage 1.5D clean 24h run 跑完，并确认 summary 正常。
priority_2 = 拉回 1.5D artifacts，更新 1.5D review。
priority_3 = 如果需要长期等待新事件，启动新的 continuous 1.5D source collector。
priority_4 = 对 continuous 1.5D output 做 Stage 1.5F bootstrap watermark。
priority_5 = 启动 Stage 1.5F live_depth_observer，等待 watermark 后的新 event-symbol。
priority_6 = 有 completed 12h depth evidence 后，进入 Stage 1.5G Live Depth Evidence Review。
```

最重要的纪律：

```text
不要用旧事件的当前盘口证明历史 12h entry 可成交。
不要用少量 depth snapshot 宣称执行可行。
不要把 1.5F 的 observation success 解释成 alpha success。
```
