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
  # 引导水印模式：冷启动时基于历史事件时间戳与标识符初始化水印，作为新事件判定的基准基线
2. atomic watermark write。 
  # 原子化水印写入：利用临时文件写入并配合 fsync 与重命名操作，防止系统崩溃导致水印文件损坏
3. corrupted watermark invalid handling。 
  # 损坏水印无效处理：水印文件不存在、JSON解析失败或关键字段缺失/类型不匹配时抛出异常或拦截，防止脏数据干扰
4. same detected_at_ms but unseen event/article 仍可被识别为 post-watermark。 
  # 同时间戳未见事件处理：允许时间戳与最大已处理时间戳相同但ID不同的新事件通过，防止同毫秒的多个并发事件被漏滤
5. event_symbol_id 稳定生成。 
  # 稳定事件标识符生成：基于源名称、文章ID、归一化URL与交易对等元数据生成唯一哈希标识，用于多次运行中去重与状态绑定
6. observer_state startup compaction。 
  # 启动状态压缩：启动时对历史状态按 event_symbol_id 去重只保留最新记录，并原子重写状态文件以防止其无限膨胀
7. restart resume active observation。 
  # 重启恢复活跃观测：支持在进程重启后从状态文件中恢复仍在观察窗口期内的活跃观测任务
8. expired active observation 不会重置 12h window。 
  # 到期活跃观测不重置窗口：重启加载过期活跃观测时直接判定过期，不会重新加上 12 小时观察期，严格遵守时间限制
9. exchangeInfo refresh cache。 
  # 交易信息缓存刷新：定时（如每5分钟）刷新交易对元数据缓存，避免每个轮询周期都请求静态接口以防止 API 请求频率超限
10. request budget precheck。 
  # 请求预算预检：在开启新事件观测前评估每分钟 API 请求速率，超限则拒绝观测，防范并发调用超出币安速率限制
11. public depth endpoint live flag hard gate。 
  # 公共深度接口 Live Flag 硬网关：硬性限制必须显式启用 live_public_readonly 参数才能发起真实网络请求，防范测试期网络调用外溢
12. mock-response-dir fixture mode 禁止真实网络。 
  # 本地 Mock 响应模式：指定本地目录时，客户端直接读取 Mock JSON 文件作为 API 响应，完全禁止发起实际的外部网络连接
13. request_manifest 写 payload hash / payload size。 
  # 请求清单审计记录：每次 API 请求均在清单文件中写入响应状态码、包体大小和 SHA-256 哈希值，用作事后审计和数据连续性检验
14. heartbeat 每轮 poll 写入。 
  # 每轮轮询心跳写入：每次轮询循环结束时向 heartbeat 文件写入心跳行，记录当前活跃/完成计数及最新异常，供监控探针使用
15. summary 区分 bootstrap / running / in_progress / depth_evidence_collected / invalid / failed。 
  # 阶段性决策摘要分类：决策统计摘要中清晰区分引导状态、正常运行无新事件、活跃观察中、深度数据已收集完备、系统无效和失败等六大状态
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

### 4.1 Stage 1.5D validation run

根据当前人工排查记录，服务器上 Stage 1.5D 已经完成一轮干净的 24h validation run：

```text
STAGE1_5D_VALIDATION_SUMMARY = data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json
```

这份 summary 现在作为 Stage 1.5F 的上游安全门使用。它的作用是证明 `stage1_5d_live_event_source_smoke_collector` 这套 source collector/source profile 没有处于 invalid/unsafe 状态。

### 4.2 Stage 1.5D continuous run

当前正在服务器运行、供 Stage 1.5F 实时消费的 1.5D continuous output root 是：

```text
session = stage1_5d_continuous_7d
STAGE1_5D_EVENTS_OUT = data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d
```

该进程当前命令形态：

```text
run_stage1_5d_live_event_source_smoke_collector.py \
  --output-root data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d \
  --output-summary data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d/binance_futures_launch_smoke_summary.json \
  --poll-interval-sec 60 \
  --max-seconds 604800 \
  --live-public-readonly
```

### 4.3 Stage 1.5F live observer

当前 Stage 1.5F live depth observer 已经启动：

```text
session = stage1_5f_live_depth_7d
STAGE1_5F_OUT = data/external_signal_shadow/stage1_5f/live_depth_observer_7d
```

该进程当前读取：

```text
--stage1-5d-events-glob data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d/events/*.jsonl
--stage1-5d-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json
--stage1-5e-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
```

最近一次服务器状态：

```text
decision = stage1_5f_observer_running_no_new_event
post_watermark_events_accepted = 0
active_observation_count = 0
completed_observation_count = 0
total_snapshots_collected = 0
request_success_rate = 1.0
failed_requests_count = 0
heartbeat_count = 153
```

解释：这表示 1.5F 当前运行正常，但 watermark 之后还没有新的 `futures_contract_launch` event-symbol，因此尚未开始任何 12h depth observation。

`pre_watermark_events_ignored` 增长不代表新事件。它表示 1.5F 在每轮扫描时持续看到并忽略 watermark 之前的旧 rows；只要 `post_watermark_events_accepted = 0`，就说明没有新事件进入盘口采集。

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
cd /root/crypto-alpha-lab
STAGE1_5D_OUT=data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z

du -sh "$STAGE1_5D_OUT"/raw_payloads 
# 检查目的：检查已抓取并持久化的原始网页/接口数据包的总磁盘占用空间。
wc -l "$STAGE1_5D_OUT"/heartbeats/*.jsonl
#检查目的：检查心跳记录文件中的总行数（即总轮询次数）。
wc -l "$STAGE1_5D_OUT"/events/*.jsonl
# 检查目的：检查已捕捉并成功解析出的合约上线事件行数。
tail -n 3 "$STAGE1_5D_OUT"/heartbeats/*.jsonl
# 检查目的：查看最新写入的 3 条心跳日志明细，确认最新的运行状态和错误信息。
# 时效性：心跳行中记录的 poll_at_ms（或时间戳）与当前系统时间差值在一两个 poll 周期内（通常不超过 2 分钟）。
# 无故障：心跳记录里的错误字段（如 last_error）值应为 null (或为空)；网络流量预算状态字段应保持为正常状态（如 "ok"）。
ps -ef | grep run_stage1_5d_live_event_source_smoke_collector | grep -v grep
# 检查目的：确认后台收集器进程在操作系统中依然活跃。控制台能够正常输出一条包含当前进程 PID 且匹配上述脚本名称的进程行。
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

### Step 4: 明确 1.5D 与 1.5F 的部署位置和运行时长

推荐部署位置：服务器，不推荐本地笔记本。

原因：

```text
1. 1.5D source collector 需要稳定连续运行，笔记本在公司和家之间移动会断网/休眠。
2. 1.5F live depth observer 要在新事件出现后的前 15 分钟内启动 observation，并连续采集 12h depth。
3. 服务器上用 tmux + venv 可以不依赖本地终端窗口，断开 SSH 后仍继续运行。
```

运行时长分两类：

```text
1. Stage 1.5D 24h validation run:
   目标是证明 source collector 能稳定运行满 24h。
   建议运行 24h 后自然退出，并生成 binance_futures_launch_smoke_summary.json。

2. Stage 1.5D continuous run + Stage 1.5F observer:
   目标是等待 watermark 之后的新 futures_contract_launch。
   建议长期运行，至少覆盖直到捕捉到 1 个新事件，并让 1.5F 完成该 event-symbol 的 12h depth observation。
```

结论：

```text
1. 24h 的 1.5D validation run 是 source collector 可用性证明。
2. 1.5F 真正需要的是一个仍在增长的 1.5D continuous output root。
3. 如果 1.5D run 已经结束，它不会再实时产生事件，只适合做 bootstrap 或审查，不适合作为 live observer 的长期输入。
```

### Step 5: 在服务器上启动新的 Stage 1.5D continuous run

在服务器上执行：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
STAGE1_5D_CONTINUOUS_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_$RUN_ID"

mkdir -p "$STAGE1_5D_CONTINUOUS_OUT"

tmux new -d -s stage1_5d_continuous "
cd /root/crypto-alpha-lab &&
source .venv/bin/activate &&
STAGE1_5D_CONTINUOUS_OUT='$STAGE1_5D_CONTINUOUS_OUT' &&
echo STAGE1_5D_CONTINUOUS_OUT=\"\$STAGE1_5D_CONTINUOUS_OUT\" &&
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-root \"\$STAGE1_5D_CONTINUOUS_OUT\" \
  --output-summary \"\$STAGE1_5D_CONTINUOUS_OUT/binance_futures_launch_smoke_summary.json\" \
  --poll-interval-sec 60 \
  --max-seconds 86400 \
  --live-public-readonly
"

echo "$STAGE1_5D_CONTINUOUS_OUT"
```

检查是否启动成功：

```bash
tmux ls
ps -ef | grep run_stage1_5d_live_event_source_smoke_collector | grep -v grep

tmux capture-pane -t stage1_5d_continuous -p | tail -n 80
wc -l "$STAGE1_5D_CONTINUOUS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_CONTINUOUS_OUT"/events/*.jsonl 2>/dev/null || true
du -sh "$STAGE1_5D_CONTINUOUS_OUT"/raw_payloads 2>/dev/null || true
```

重要：当前 1.5F runner 的正式 observation 会读取 `--stage1-5d-summary` 并校验 1.5D 安全状态。  
如果新 continuous run 还没有自然跑完 24h，它可能还没有 `binance_futures_launch_smoke_summary.json`。这种情况下有两个安全选择：

```text
方案 A: 先等新的 continuous run 跑满 24h，再启动 1.5F。
优点: 完全符合当前 1.5F summary gate。
缺点: 如果 24h 内有新事件，1.5F 可能错过该事件的 12h depth observation。

方案 B: 使用已经完成并通过的 1.5D 24h validation summary 作为 --stage1-5d-summary，
       同时让 --stage1-5d-events-glob 指向新的 continuous run events/*.jsonl。
优点: 可以立即让 1.5F 跟随新的 events 文件等新事件。
缺点: summary 证明的是同一套 collector/source 的历史 24h 稳定性，不是当前 continuous run 自己已经跑满 24h。
```

当前推荐：

```text
如果已经有一个 blockers=[] 且 research_result_valid=true 的 1.5D 24h summary，
可以采用方案 B。
如果没有合格 24h summary，先不要启动正式 1.5F observation。
```

### Step 5.1: 为什么建议新建 output root

每次启动新的 1.5D continuous run，建议使用新的 `output-root`，例如：

```text
data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d
```

而不是复用旧目录。原因：

```text
1. run boundary 清楚：可以明确知道这一批 events、heartbeats、raw_payloads 属于哪次运行。
2. 排障更简单：如果某次 run 失败，不会污染前一次 clean run。
3. watermark 语义更安全：1.5F bootstrap 时可以清楚知道“起跑线”来自哪个 events root。
4. summary 不会互相覆盖：每个 output root 都有自己的 binance_futures_launch_smoke_summary.json。
5. rsync/归档更简单：可以按目录取回某一次 run 的完整证据。
```

复用旧 output root 的主要风险是：旧事件、新事件、异常中断 run 的 heartbeat/raw payload 混在一起，后面 review 很难判断证据边界。

时间戳目录的生成逻辑：

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
STAGE1_5D_LONG_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_${RUN_ID}_7d"
```

这会生成类似：

```text
data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d
```

每次新开一个 7d run，都应该生成新的 `RUN_ID` 和新的 output root。不要手写旧时间戳，也不要复用上一次目录。  
检查时则必须使用服务器上真实查到的目录；如果不确定，用：

```bash
find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name "live_event_source_continuous_*_7d" -print | sort
```

### Step 5.2: 为什么 1.5D 启动需要 Stage 1.5C.1 / 1.5C summary

1.5D 是 live event-source smoke collector。它不是随便去抓 Binance 公告，而是只允许在上游研究链路已经满足条件时运行。

因此启动命令里有：

```bash
--stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json
--stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json
```

这两个文件不是 1.5D 的事件输入。它们是上游证据安全门。

`stage1_5c1_summary` 主要证明：

```text
1. futures price coverage 已扩展完成。
2. decision = stage1_5c1_price_coverage_ready_for_1_5c_rerun。
3. paper/live/alpha 等危险 flag 没有打开。
```

`stage1_5c_summary` 主要证明：

```text
1. Stage 1.5C replay 已经完成。
2. research_result_valid = true。
3. promising_cells 包含 futures_contract_launch + long_attention + 12h。
4. paper/live/execution/alpha 等危险 flag 没有打开。
```

1.5D 真正抓取的实时输入仍然是 Binance announcement public endpoint；1.5C/1.5C.1 summary 只是告诉 1.5D：“为什么允许你观察 futures launch 这个事件源”。

### Step 5.3: 如果 24h 后仍无新事件，切换到 7d continuous run

你现在选择先等当前 24h continuous run 结束是可以的。  
如果 24h 内没有 watermark 之后的新 `futures_contract_launch`，建议切换到 7d continuous run，提高捕捉概率。

7d run 命令：

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
STAGE1_5D_LONG_OUT="data/external_signal_shadow/stage1_5d/live_event_source_continuous_${RUN_ID}_7d"

mkdir -p "$STAGE1_5D_LONG_OUT"

tmux new -d -s stage1_5d_continuous_7d "
cd /root/crypto-alpha-lab &&
source .venv/bin/activate &&
STAGE1_5D_LONG_OUT='$STAGE1_5D_LONG_OUT' &&
echo STAGE1_5D_LONG_OUT=\"\$STAGE1_5D_LONG_OUT\" &&
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-root \"\$STAGE1_5D_LONG_OUT\" \
  --output-summary \"\$STAGE1_5D_LONG_OUT/binance_futures_launch_smoke_summary.json\" \
  --poll-interval-sec 60 \
  --max-seconds 604800 \
  --live-public-readonly
"

echo "$STAGE1_5D_LONG_OUT"
```

检查 7d 1.5D 是否启动：

```bash
tmux ls
ps -ef | grep run_stage1_5d_live_event_source_smoke_collector | grep -v grep
tmux capture-pane -t stage1_5d_continuous_7d -p | tail -n 80
wc -l "$STAGE1_5D_LONG_OUT"/heartbeats/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_LONG_OUT"/events/*.jsonl 2>/dev/null || true
du -sh "$STAGE1_5D_LONG_OUT"/raw_payloads 2>/dev/null || true
```

切到 7d run 后，必须让 1.5F 改读新的 7d events root。操作顺序：

```text
1. 停掉旧的 stage1_5f_live_depth tmux session。
2. 用新的 STAGE1_5D_LONG_OUT/events/*.jsonl 重新 bootstrap watermark。
3. 用新的 STAGE1_5D_LONG_OUT/events/*.jsonl 重启 1.5F observer。
```

示例：

```bash
# 1. 停掉旧 1.5F observer
tmux kill-session -t stage1_5f_live_depth 2>/dev/null || true

# 2. 设置新路径
STAGE1_5D_EVENTS_OUT="$STAGE1_5D_LONG_OUT"
STAGE1_5D_VALIDATION_SUMMARY=data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json
STAGE1_5E_SUMMARY=data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
STAGE1_5F_OUT=data/external_signal_shadow/stage1_5f/live_depth_observer_7d

# 3. bootstrap 新 watermark
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob "$STAGE1_5D_EVENTS_OUT/events/*.jsonl" \
  --stage1-5d-summary "$STAGE1_5D_VALIDATION_SUMMARY" \
  --stage1-5e-summary "$STAGE1_5E_SUMMARY" \
  --output-root "$STAGE1_5F_OUT" \
  --bootstrap-watermark

# 4. 启动 1.5F 7d observer
tmux new -d -s stage1_5f_live_depth_7d "
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

注意：切换到 7d 后，建议使用新的 `STAGE1_5F_OUT`，例如：

```text
data/external_signal_shadow/stage1_5f/live_depth_observer_7d
```

这样旧 24h observer 的 watermark/state 和新 7d observer 不会混在一起。

### Step 5.4: 7d 版 1.5F observer 启动后如何检查

启动后先在服务器当前 shell 设置变量：

```bash
cd /root/crypto-alpha-lab

STAGE1_5D_EVENTS_OUT=data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d
STAGE1_5F_OUT=data/external_signal_shadow/stage1_5f/live_depth_observer_7d
```

如果不确定真实 7d output root，先用：

```bash
find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name "live_event_source_continuous_*_7d" -print | sort
find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name "live_depth_observer_7d" -print | sort
```

#### 启动后 1-3 分钟内检查一次

```bash
tmux ls
ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

tmux capture-pane -t stage1_5d_continuous_7d -p | tail -n 80
tmux capture-pane -t stage1_5f_live_depth_7d -p | tail -n 80

cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null || echo "1.5F summary missing"
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || echo "1.5F heartbeat missing"
```

启动成功的最低条件：

```text
1. tmux ls 有 stage1_5d_continuous_7d 和 stage1_5f_live_depth_7d。
2. ps 能看到 run_stage1_5d_live_event_source_smoke_collector。
3. ps 能看到 run_stage1_5f_live_depth_observer。
4. live_depth_observer_summary.json 存在。
5. heartbeat/*.jsonl 行数开始增长。
6. summary 中 live_depth_observation_allowed = true。
7. summary 中 blocker = null。
```

如果 `cat "$STAGE1_5F_OUT/live_depth_observer_summary.json"` 找不到文件，先检查 `STAGE1_5F_OUT` 是否为空或路径写错：

```bash
echo "STAGE1_5F_OUT=[$STAGE1_5F_OUT]"
find data/external_signal_shadow/stage1_5f -maxdepth 2 -type f -name "live_depth_observer_summary.json" -print
```

#### 正常等待期：每 2-4 小时检查一次

```bash
以后每次新开 SSH，都要先执行：
cd /root/crypto-alpha-lab
export STAGE1_5F_OUT=data/external_signal_shadow/stage1_5f/live_depth_observer_7d
export STAGE1_5D_EVENTS_OUT=data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d

ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

cat "$STAGE1_5F_OUT/live_depth_observer_summary.json"
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || true
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20
find "$STAGE1_5D_EVENTS_OUT/events" -type f -name "*.jsonl" -print -exec wc -l {} \; 2>/dev/null || true

wc -l "$STAGE1_5D_EVENTS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/events/*.jsonl 2>/dev/null || true
du -sh "$STAGE1_5D_EVENTS_OUT"/raw_payloads 2>/dev/null || true
```

正常等待状态应类似：

```text
decision = stage1_5f_observer_running_no_new_event
post_watermark_events_accepted = 0
active_observation_count = 0
total_snapshots_collected = 0
heartbeat_count 持续增长
request_success_rate = 1.0 或接近 1.0
failed_requests_count = 0 或很低
```

这表示 1.5F 正常等待新事件，不代表失败。

#### 如果捕捉到新事件：每 15-30 分钟检查一次

触发信号：

```text
post_watermark_events_accepted > 0
active_observation_count > 0
events_accepted/*.jsonl 行数增加
depth_snapshots/YYYYMMDD/{event_symbol_id}.jsonl 开始出现并增长
```

检查命令：

```bash
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json"
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null -print -exec tail -n 3 {} \;
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null -exec wc -l {} \; | sort -n | tail -n 20
find "$STAGE1_5F_OUT/request_manifest" -type f 2>/dev/null -exec tail -n 5 {} \;
```

重点看：

```text
active_observation_count > 0
request_success_rate >= 0.95
failed_requests_count 不快速增长
max_consecutive_network_errors_seen <= 5
total_snapshots_collected 持续增长
```

#### 12h 观察完成后检查

当某个 event-symbol 完成 12h depth observation，期望看到：

```text
completed_observation_count > 0
decision = stage1_5f_observer_depth_evidence_collected
research_result_valid = true 或至少进入可 review 状态
total_snapshots_collected >= min_snapshot_count_required
```

然后生成 Stage 1.5F review：

```bash
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5f_live_depth_observer.py \
  --summary "$STAGE1_5F_OUT/live_depth_observer_summary.json" \
  --output-review docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

#### 需要立刻处理的异常

```text
1. tmux ls 没有 stage1_5d_continuous_7d:
   1.5D 停了，1.5F 不会再有新事件输入。

2. tmux ls 没有 stage1_5f_live_depth_7d:
   1.5F 停了，不会采 depth。

3. heartbeat_count 不再增长:
   进程可能卡住或已退出。

4. decision = stage1_5f_observer_invalid 或 stage1_5f_observer_failed:
   立即检查 blocker、tmux capture-pane、request_manifest。

5. request_success_rate < 0.95:
   depth 请求质量不足，12h evidence 可能无效。

6. active_observation_count > 0 但 total_snapshots_collected 不增长:
   说明接到事件但 depth 抓取没有推进，需要查 request_manifest/error。
```

### Step 6: 1.5D 与 1.5F 的启动间隔要求

1.5D 和 1.5F 之间没有固定“必须间隔几小时”的要求。真正的要求是：

```text
1. 1.5D events/*.jsonl 路径已经存在或会持续生成。
2. 1.5F 已经 bootstrap 当前已有事件，写入 watermark.json。
3. bootstrap 之后，新事件出现时，1.5F 正在运行。
4. 新事件 detected_at_ms 距离 1.5F 看到它的时间不能超过 event age gate。
```

当前配置：

```text
EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS = 15 * 60 * 1000
```

这意味着：如果 Binance 新 futures launch 被 1.5D 记录后，你过了 12h 才启动 1.5F，正式 live observer 基本已经错过了该事件的有效盘口观察窗口。  
此时再抓当前盘口，只能叫 `current_depth_observation_only`，不能证明“事件后 12h entry window”的真实盘口。

所以正确方式是：

```text
1. 先启动并稳定运行 1.5D continuous collector。
2. 立即对这个 continuous output 做 1.5F bootstrap。
3. bootstrap 完成后，立即启动 1.5F live observer。
4. 让 1.5D 和 1.5F 同时在服务器上运行，等待未来新事件。
```

### Step 7: 1.5D 事件是否会实时传递给 1.5F

不是消息队列式的“推送”，而是文件轮询式的“共享文件流”。

实际链路是：

```text
1. 1.5D 每轮 poll Binance announcement source。
2. 如果发现 futures_contract_launch article，就写入:
   $STAGE1_5D_OUT/events/YYYY-MM-DD.jsonl
3. 1.5F 每轮读取 --stage1-5d-events-glob 匹配到的 events/*.jsonl。
4. 1.5F 用 watermark 判断哪些 event-symbol 是新事件。
5. 新事件通过 event age gate 后，1.5F 开始采 Binance USD-M depth。
```

所以只要两个进程都在服务器上运行，并且 1.5F 的 `--stage1-5d-events-glob` 指向正在增长的 1.5D `events/*.jsonl`，事件就会被近实时消费。  
延迟主要取决于：

```text
1. 1.5D poll interval，当前约 60 秒。
2. 1.5F poll interval，当前默认按 runner loop 执行。
3. 文件写入与读取间隔。
```

### Step 8: bootstrap Stage 1.5F watermark

```bash
STAGE1_5D_EVENTS_OUT=data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d
STAGE1_5D_VALIDATION_SUMMARY=data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json
STAGE1_5E_SUMMARY=data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
STAGE1_5F_OUT=data/external_signal_shadow/stage1_5f/live_depth_observer_7d

PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob "$STAGE1_5D_EVENTS_OUT/events/*.jsonl" \
  --stage1-5d-summary "$STAGE1_5D_VALIDATION_SUMMARY" \
  --stage1-5e-summary "$STAGE1_5E_SUMMARY" \
  --output-root "$STAGE1_5F_OUT" \
  --bootstrap-watermark
```

`watermark` 不是根据 `binance_futures_launch_smoke_summary.json` 划定的。  
准确说：

```text
1. watermark 根据 --stage1-5d-events-glob 读到的 events/*.jsonl 划定。
2. binance_futures_launch_smoke_summary.json 只是 1.5F 的上游安全门，用来证明 1.5D collector/source 没有 invalid 或 unsafe。
```

检查：

```bash
cat "$STAGE1_5F_OUT/watermark.json"
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json"
```

`watermark.json` 主要检查：

```text
watermark_version = 1
max_seen_detected_at_ms > 0
seen_event_ids 非空或 seen_source_article_ids / seen_stable_event_keys 非空
watermark_updated_at_ms 存在
```

如果 `seen_*` 全为空，说明 bootstrap 时没有读到任何 1.5D events。此时要检查 `--stage1-5d-events-glob` 是否写错。

`live_depth_observer_summary.json` 在 bootstrap 后主要检查：

```text
decision = stage1_5f_observer_bootstrap_watermark_only
watermark_present = true
bootstrap_watermark_allowed = true
live_depth_observation_allowed = false
pre_watermark_events_ignored >= 0
post_watermark_events_accepted = 0
research_result_valid = false
```

### Step 9: 启动 Stage 1.5F live observer

```bash
tmux new -d -s stage1_5f_live_depth_7d "
cd /root/crypto-alpha-lab &&
source .venv/bin/activate &&
STAGE1_5D_EVENTS_OUT='data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260629T133308Z_7d' &&
STAGE1_5D_VALIDATION_SUMMARY='data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json' &&
STAGE1_5E_SUMMARY='data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json' &&
STAGE1_5F_OUT='data/external_signal_shadow/stage1_5f/live_depth_observer_7d' &&
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob \"\$STAGE1_5D_EVENTS_OUT/events/*.jsonl\" \
  --stage1-5d-summary \"\$STAGE1_5D_VALIDATION_SUMMARY\" \
  --stage1-5e-summary \"\$STAGE1_5E_SUMMARY\" \
  --output-root \"\$STAGE1_5F_OUT\" \
  --live-public-readonly
"
```

如果使用同一个 1.5F output root 重启 observer，不要随便删除 `watermark.json`。  
删除 watermark 会导致旧事件可能重新进入候选，破坏“只看新事件”的边界。

### Step 10: 监控 Stage 1.5F

```bash
STAGE1_5F_OUT=data/external_signal_shadow/stage1_5f/live_depth_observer_7d

tmux ls
ps -ef | grep run_stage1_5f_live_depth_observer | grep -v grep
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null || true
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || true
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/events_rejected" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
```

重点看 `live_depth_observer_summary.json` 的这些字段：

```text
decision
blocker
watermark_present
pre_watermark_events_ignored
post_watermark_events_accepted
active_observation_count
completed_observation_count
expired_observation_count
failed_observation_count
total_snapshots_collected
request_success_rate
failed_requests_count
max_consecutive_network_errors_seen
research_result_valid
```

判断方式：

```text
stage1_5f_observer_running_no_new_event:
  正常等待状态。说明 watermark 后还没有新 futures launch。

stage1_5f_observer_event_observation_in_progress:
  已接受新 event-symbol，正在采 12h depth。

stage1_5f_observer_depth_evidence_collected:
  至少一个 event-symbol 完成 12h depth observation，且覆盖率/请求质量达标。

stage1_5f_observer_invalid 或 stage1_5f_observer_failed:
  需要立刻检查 blocker、request_manifest、heartbeat 和 tmux 输出。
```

同时看文件层面：

```text
events_accepted/*.jsonl 有新增:
  说明 1.5F 已经接受 watermark 后的新 event-symbol。

depth_snapshots/YYYYMMDD/{event_symbol_id}.jsonl 持续增长:
  说明正在真实采 depth。

heartbeat/*.jsonl 持续增长:
  说明 observer 进程还活着。

request_manifest/*.jsonl 持续增长且 error 为空或很少:
  说明 Binance public depth 请求健康。
```

如果 `events_accepted` 和 `depth_snapshots` 长期为空，但 `heartbeat` 正常增长，通常不是 bug，而是还没有 watermark 之后的新 futures launch event。

### Step 11: 生成正式 Stage 1.5F review

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

## 9.3 已知问题与非阻断修复项

### Issue: `Multiple USDⓈ-Margined TradFi Perpetual Contracts` symbol extraction gap

当前 1.5D parser 对普通单合约 futures launch 标题可以抽出 symbol，例如：

```text
Binance Futures Will Launch USDⓈ-Margined CAPUSDT Perpetual Contract
symbols = ["CAPUSDT"]
```

但对这类多合约 / TradFi 标题：

```text
Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts
symbols = []
```

原因：这类标题本身不包含具体 `XXXUSDT` symbol，具体合约通常在 article detail body/table 里。当前 1.5D live collector 第一版主要解析 announcement list title，没有完整解析 detail page body，因此会出现 `symbols=[]`。

风险判断：

```text
severity = medium
safety_risk = low
impact_type = false_negative
impact = 可能漏采 multi-symbol / TradFi futures launch 的 12h depth observation
blocking_current_1_5f = false
```

为什么不是高危：

```text
1. symbols=[] 不会触发错误 depth 采集。
2. 不会产生交易信号。
3. 不会打开 paper/live/execution。
4. 主要风险是漏掉部分未来事件，而不是错误采集或错误执行。
```

后续修复建议：

```text
stage = Stage 1.5D parser enhancement
next_action = write_small_fix_plan_or_patch_after_current_7d_observer_stable
```

建议测试：

```text
test_parse_multiple_tradfi_launch_extracts_symbols_from_article_body
test_multiple_tradfi_launch_with_no_symbols_is_marked_symbol_parse_failed
test_stage1_5f_rejects_symbol_empty_event_without_crashing
```

修复方向：

```text
1. 当 title 匹配 Multiple USDⓈ-Margined TradFi Perpetual Contracts 时，抓取 source_detail_url。
2. 从 article body/table 中抽取所有 XXXUSDT / XXXUSDC 合约。
3. 若仍无法抽取，明确输出 symbol_parse_failed_count 和 rejection_reason = symbol_missing。
```

该问题可以等待当前 7d observer 稳定运行后再处理，不需要中断当前 1.5D / 1.5F。

## 10. 当前推荐下一步

```text
priority_1 = 保持 Stage 1.5D 7d continuous run 和 Stage 1.5F 7d observer 运行。
priority_2 = 每 2-4 小时检查 heartbeat / events / summary。
priority_3 = 等待 watermark 后的新 futures_contract_launch event-symbol。
priority_4 = 如果 post_watermark_events_accepted > 0，进入 15-30 分钟巡检频率。
priority_5 = 有 completed 12h depth evidence 后，进入 Stage 1.5G Live Depth Evidence Review。
priority_6 = 非阻断并行任务：修复 Multiple TradFi symbol extraction gap。
```

等待新 event 期间可以并行推进：

```text
1. Stage 1.5D parser enhancement:
   修复 Multiple USDⓈ-Margined TradFi Perpetual Contracts 的 symbols=[] 问题。

2. Stage 1.5G Live Depth Evidence Review plan:
   先写 review plan，不执行交易，只定义如何审查 1.5F depth snapshots。

3. Ops hardening:
   把服务器巡检命令整理成 docs/ops 或 shell helper，减少 STAGE1_5F_OUT 为空导致的误查。

4. Artifact sync plan:
   规划如何把 7d raw_payloads / events / depth_snapshots / summary rsync 回本地。

5. No-trade safety review:
   复核 1.5D/1.5F 没有 private endpoint、api key、order endpoint、paper/live/execution flag。
```

不建议并行推进：

```text
1. paper trading
2. live trading
3. execution engine 接入
4. alpha 结论包装
5. 用旧事件当前盘口倒推历史可成交性
```

最重要的纪律：

```text
不要用旧事件的当前盘口证明历史 12h entry 可成交。
不要用少量 depth snapshot 宣称执行可行。
不要把 1.5F 的 observation success 解释成 alpha success。
```
