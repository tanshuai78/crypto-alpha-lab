# Trend/Liquidation Phase 1A 服务器部署与运行指南

## 目的 (Purpose)

以**仅观察模式 (observation-only mode)** 运行 `Trend / Liquidation Regime` 的 Phase 1A 数据链路与监控链路，不接入 `execution`，不触发任何交易执行。

本指南目标是稳定跑通三段链路：

1. `B`：市场行生产器 `build_trend_regime_market_rows.py`（生成 `trend_regime_phase1a_rows.jsonl`）
2. `A`：清算采集器 `collect_trend_regime_force_orders.py`（生成 `trend_regime_liquidation_cache.json`）
3. `watchlist`：`run_trend_regime_watchlist.py`（消费 A+B 并输出观测日志）

---

## 术语说明 (Terminology)

1. **Observation-only (仅观察模式)**：只产生观测证据，不生成可执行交易。
2. **Watchlist (观察列表)**：策略扫描后输出的监控信号集合。
3. **forceOrder stream (强平流)**：Binance Futures 强平事件 WebSocket 数据流。
4. **Liquidation notional (清算名义金额)**：指定窗口内强平成交额（USDT）。
5. **Raw market rows (原始市场行)**：策略分类器输入行（含 `return_1h_pct`、`oi_change_1h_pct` 等字段）。
6. **Shadow replay (影子回放)**：不下单，仅用历史路径评估成本后方向收益。

---

## 运行边界 (Safety Boundary)

以下行为在本阶段**禁止**：

- 导入 `src/execution/`
- 生成 `TradeIntent`
- 读取私钥/API secret
- 下任何实盘/模拟执行单
- 修改 `RISK_LIVE_TRADING_ENABLED`

本阶段只允许：

- 写入 `data/*.jsonl` 与 `data/*.json` 证据文件
- 写入 `reports/trend_regime/*.json` 回放结果
- 输出 `heartbeat` 与 `reject_counts`

---

## 部署前检查 (Preflight)

在服务器项目目录执行：

```bash
cd /root/crypto-alpha-lab
git pull
docker --version
```

建议确认：

- `scripts/build_trend_regime_market_rows.py` 存在
- `scripts/collect_trend_regime_force_orders.py` 存在
- `scripts/run_trend_regime_watchlist.py` 存在

---

## 本地代码同步到服务器 (Local Sync To Server)

如果你是在本地电脑完成开发，再去服务器部署，必须先同步代码；否则服务器 `docker build` 只会打包旧版本。

### 1) 本地 Mac 执行 `rsync`

```bash
rsync -avzP --exclude='data' --exclude='.git' --exclude='.venv' --exclude='.ruff_cache' --exclude='.pytest_cache' --exclude='__pycache__' \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/ \
  root@47.82.4.85:/root/crypto-alpha-lab/
```

### 2) 服务器端验证同步结果

```bash
cd /root/crypto-alpha-lab
git status --short --branch
ls scripts | grep -E "build_trend_regime_market_rows.py|collect_trend_regime_force_orders.py|run_trend_regime_watchlist.py"
```

---

## 与旧容器关系 (Coexistence With Extreme Funding)

如果你已经在跑 `Extreme Funding` 容器：

- **不需要删除旧容器**。
- 新策略建议使用**新容器名**并行运行。
- 两套容器可以共用同一个 `data` 挂载目录（文件名不同，不冲突）。

---

## Dockerfile 说明 (Do We Need To Rewrite Dockerfile?)

结论：**通常不需要重写 Dockerfile**。

原因：

1. 当前 Dockerfile 提供的是一个通用运行镜像（Python + 项目依赖 + 代码）。
2. 运行哪个链路由 `docker run ... <command>` 覆盖默认 `CMD` 决定。
3. 因此可以用同一个镜像启动多个不同职责的容器。

只有在以下场景才建议改 Dockerfile：

- 你希望把 `websockets` 固化到镜像里，避免 `uv run --with websockets` 动态安装。
- 你需要更严格的生产级约束（非 root 用户、healthcheck、精细化层缓存）。

---

## 镜像/容器关系图示 (Image vs Containers)

本次部署是：**一个镜像，三个容器**（不是一个容器跑三条链路）。

```text
                 +-----------------------------+
                 |   Image: crypto-alpha-lab  |
                 |   (single shared image)    |
                 +-------------+---------------+
                               |
        +----------------------+----------------------+
        |                      |                      |
 +------v-------+      +-------v--------+     +-------v---------+
 | Container A  |      | Container B    |     | Container C     |
 | trend-rows   |      | trend-forceorder|     | trend-watchlist |
 | B: market row|      | A: forceOrder   |     | consume A+B     |
 +--------------+      +-----------------+     +-----------------+
        |                      |                      |
        +---------- write/read shared /app/data -----+
```

对应关系：

- `trend-rows`：生成 `trend_regime_phase1a_rows.jsonl`
- `trend-forceorder`：生成 `trend_regime_liquidation_cache.json`
- `trend-watchlist`：读取上述两个文件并输出 `trend_regime_watch_events.jsonl`

---

## Docker 构建 (Build)

```bash
cd /root/crypto-alpha-lab
docker build -t crypto-alpha-lab:latest .
```

---

## Docker 运行 (Run)

建议把日志目录与数据目录都挂载出来：

```bash
mkdir -p /root/crypto-alpha-lab/data /root/crypto-alpha-lab/logs
```

### 1) B: 市场行生产器 (Market Rows Producer)

```bash
docker run -d --name trend-rows \
  --restart always \
  --memory="768m" \
  -v /root/crypto-alpha-lab/data:/app/data \
  -v /root/crypto-alpha-lab/logs:/app/logs \
  crypto-alpha-lab:latest \
  python scripts/build_trend_regime_market_rows.py \
    --output data/trend_regime_phase1a_rows.jsonl \
    --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
    --poll-interval-sec 60 \
    --forever
```

### 2) A: 清算采集器 (forceOrder Collector)

> 该容器依赖 `websockets`，使用 `uv run --with websockets` 启动。

```bash
docker run -d --name trend-forceorder \
  --restart always \
  --memory="512m" \
  -v /root/crypto-alpha-lab/data:/app/data \
  -v /root/crypto-alpha-lab/logs:/app/logs \
  crypto-alpha-lab:latest \
  uv run --with websockets python scripts/collect_trend_regime_force_orders.py \
    --output data/trend_regime_liquidation_cache.json \
    --flush-interval-sec 5 \
    --max-seconds 0
```

### 3) Watchlist: 消费 A+B 并输出观察结果

```bash
docker run -d --name trend-watchlist \
  --restart always \
  --memory="512m" \
  -v /root/crypto-alpha-lab/data:/app/data \
  -v /root/crypto-alpha-lab/logs:/app/logs \
  crypto-alpha-lab:latest \
  python scripts/run_trend_regime_watchlist.py \
    --input-jsonl data/trend_regime_phase1a_rows.jsonl \
    --data-root data \
    --forever \
    --row-tail-lines 3000
```

---

## 快速验证 (Smoke Checks)

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}"
```

检查日志：

```bash
docker logs --tail 50 trend-rows
docker logs --tail 50 trend-forceorder
docker logs --tail 50 trend-watchlist
```

检查关键文件：

```bash
ls -lh /root/crypto-alpha-lab/data/trend_regime_phase1a_rows.jsonl
ls -lh /root/crypto-alpha-lab/data/trend_regime_liquidation_cache.json
ls -lh /root/crypto-alpha-lab/data/trend_regime_watch_events.jsonl
```

---

## 24小时观察建议 (24h Observation Checklist)

每 2~4 小时巡检一次：

1. `trend_regime_phase1a_rows.jsonl` 行数是否持续增长
2. `trend_regime_liquidation_cache.json` 是否持续更新时间戳（文件 mtime）
3. `trend_regime_watch_events.jsonl` 是否持续出现 `heartbeat`
4. `reject_counts` 主因分布是否稳定（重点看 `vol_breakout_below_threshold` 占比）
5. `signal_count` 是否持续为 0（若长期为 0，需要做阈值复核或数据源复核）
6. `trend-forceorder` 是否频繁重连（日志中 `force_order_collector_reconnect`）

建议每天汇总一次：

- 总心跳次数
- 总 `signal_count`
- 各 `reject_reason` 占比
- `liquidation_status` 异常占比（如果开启了 REST 回退）

---

## Raw forceOrder 事件采集 (Raw ForceOrder Collection)

除了生成滚动窗口清算缓存（`--output`）外，`collect_trend_regime_force_orders.py` 还支持 `--raw-output` 参数，将每条强平事件逐行追加到 JSONL 文件中，供后续小时级聚合使用。

### 启动命令（附 `--raw-output`）

```bash
uv run --with websockets python scripts/collect_trend_regime_force_orders.py \
  --output data/trend_regime_liquidation_cache.json \
  --raw-output data/trend_regime_force_orders_raw.jsonl \
  --flush-interval-sec 5 \
  --max-seconds 0
```

Docker 容器版本（替换 `trend-forceorder` 的启动命令）：

```bash
docker run -d --name trend-forceorder \
  --restart always \
  --memory="512m" \
  -v /root/crypto-alpha-lab/data:/app/data \
  -v /root/crypto-alpha-lab/logs:/app/logs \
  crypto-alpha-lab:latest \
  uv run --with websockets python scripts/collect_trend_regime_force_orders.py \
    --output data/trend_regime_liquidation_cache.json \
    --raw-output data/trend_regime_force_orders_raw.jsonl \
    --flush-interval-sec 5 \
    --max-seconds 0
```

### 输出格式

每条事件追加一行 JSON，字段如下：

| 字段 | 含义 |
|---|---|
| `symbol` | 交易对，如 `BTC/USDT`（含斜线，与 watchlist 对齐） |
| `side` | 订单方向（`BUY` / `SELL`，即强平单的成交方向） |
| `liquidation_side` | 被清算的仓位方向：`long`（多仓被强平，SELL 成交）或 `short`（空仓被强平，BUY 成交） |
| `notional_usdt` | 本次事件的名义金额（USDT） |
| `timestamp_ms` | 事件时间戳（毫秒） |
| `hour_bucket_utc` | 所属小时桶，格式 `YYYY-MM-DDTHH:00`（无秒数和 Z 后缀） |

**语义说明**：`liquidation_side=long` 表示多仓被强平（产生 SELL 单）；`liquidation_side=short` 表示空仓被强平（产生 BUY 单）。

> [!CAUTION]
> **[局限性 / 无历史回填]** Raw 文件仅从采集器**启动时刻**起累积事件，没有历史回填能力。若采集器在某段市场行情中未运行（容器重启、网络中断等），该时段的强平事件将**永久缺失**，导致对应小时桶的清算代理数据不完整。回放报告中出现 `liquidation_coverage_ratio` 偏低时，首先排查采集器运行时段。

### 检查 Raw 文件

```bash
# 查看行数（每行一条事件）
wc -l /root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl

# 查看最新几条事件
tail -5 /root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl | python3 -m json.tool
```

---

## 小时级清算聚合 (Hourly Liquidation Aggregation)

采集到足够 Raw 事件后（建议至少运行 1 小时），执行聚合脚本将原始事件压缩为小时级代理数据，供历史回放使用。

### 运行命令

```bash
cd /root/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime_force_orders_raw.jsonl \
  --output data/trend_regime_liquidation_hourly.jsonl
```

建议在执行历史回放**之前**先运行一次聚合，确保回放能读取到最新的清算代理数据。

### 输出格式

每行一条记录，按 `(symbol, hour_bucket_utc)` 分组，字段如下：

| 字段 | 含义 |
|---|---|
| `symbol` | 交易对 |
| `hour_bucket_utc` | 小时桶（UTC），格式 `YYYY-MM-DDTHH:00:00Z` |
| `long_liquidation_notional_usdt` | 该小时多仓强平名义金额（USDT） |
| `short_liquidation_notional_usdt` | 该小时空仓强平名义金额（USDT） |
| `total_liquidation_notional_usdt` | 总强平名义金额（USDT） |
| `dominant_side` | 主导方向：`long` / `short` / `neutral` |
| `semantics` | 人类可读说明字符串 |

### 检查聚合输出

```bash
# 查看行数
wc -l /root/crypto-alpha-lab/data/trend_regime_liquidation_hourly.jsonl

# 查看最新几行
tail -5 /root/crypto-alpha-lab/data/trend_regime_liquidation_hourly.jsonl | python3 -m json.tool
```

---

## 定期回拉与本地复核 (Pullback & Local Review)

结论：建议**定期回拉**，但不必高频全量回拉。

推荐节奏：

1. 每 4 小时：服务器先产出摘要，本地回拉摘要文件。
2. 每 24 小时：回拉完整 `trend_regime_watch_events.jsonl`，并按需抽样回拉 `trend_regime_phase1a_rows.jsonl`；同时回拉 `trend_regime_liquidation_hourly.jsonl` 供本地回放。
3. 异常时：立即回拉三份原始文件全量（见下方）。

### 服务器端摘要命令（建议 crontab 每 4 小时执行）

```bash
cd /root/crypto-alpha-lab
python3 - <<'PY'
import json
from pathlib import Path
from collections import Counter

data_dir = Path("data")
rows = data_dir / "trend_regime_phase1a_rows.jsonl"
cache = data_dir / "trend_regime_liquidation_cache.json"
events = data_dir / "trend_regime_watch_events.jsonl"
out = data_dir / "trend_regime_4h_summary.json"

summary = {}
summary["rows_line_count"] = sum(1 for _ in rows.open("r", encoding="utf-8")) if rows.exists() else 0
summary["rows_mtime"] = rows.stat().st_mtime if rows.exists() else None
summary["cache_mtime"] = cache.stat().st_mtime if cache.exists() else None

if events.exists():
    lines = [ln for ln in events.read_text(encoding="utf-8").splitlines() if ln.strip()]
    summary["event_line_count"] = len(lines)
    summary["last_event"] = json.loads(lines[-1]) if lines else None
    reject_counter = Counter()
    for ln in lines[-500:]:
        obj = json.loads(ln)
        reject_counter.update(obj.get("reject_counts", {}))
    summary["reject_counts_recent_500"] = dict(reject_counter)
else:
    summary["event_line_count"] = 0
    summary["last_event"] = None
    summary["reject_counts_recent_500"] = {}

out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
print(out)
PY
```

### 本地回拉命令（每 4 小时）

```bash
# 本地先建策略子目录
mkdir -p /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_4h_summary.json \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/
```

### 本地回拉命令（每 24 小时）

```bash
# 本地先建策略子目录
mkdir -p /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime

# 1) 核心观测证据（建议全量）
rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_watch_events.jsonl \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/

# 2) 清算缓存（体积小，建议全量）
rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_liquidation_cache.json \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/

# 3) 小时级清算代理（供本地回放使用）
rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_liquidation_hourly.jsonl \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/
```

### 异常时回拉（立即执行）

触发条件示例：

- `rows` 行数停止增长
- `cache` 长时间不更新
- `signal_count`/`reject_counts` 异常跳变
- `trend-forceorder` 重连频繁

异常时建议直接全量回拉：

```bash
mkdir -p /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_phase1a_rows.jsonl \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_liquidation_cache.json \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_watch_events.jsonl \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/
```

---

## 本地历史回放 (Local Shadow Replay)

回拉数据后，可在本地执行影子回放，验证信号条件分布与清算覆盖率。

### 带清算数据的完整回放（推荐）

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/replay_trend_regime_shadow.py \
  --input data/trend_regime_historical_rows.jsonl \
  --output reports/trend_regime/replay_summary.json \
  --liquidation-hourly-jsonl data/trend_regime/trend_regime_liquidation_hourly.jsonl
```

### 不带清算数据的冒烟回放（仅验证流程）

```bash
PYTHONPATH=src uv run python scripts/replay_trend_regime_shadow.py \
  --input data/trend_regime_historical_rows.jsonl \
  --output reports/trend_regime/replay_summary.json
```

> [!NOTE]
> 不传 `--liquidation-hourly-jsonl` 时，回放报告中所有行的 `liquidation_coverage_ratio=0.0`（清算数据全部缺失），这是预期行为，不影响其他字段的验证。

---

## 常见问题与处理 (Troubleshooting)

### 1) `trend-forceorder` 启动失败：缺少 `websockets`

使用如下命令启动（已包含依赖注入）：

```bash
uv run --with websockets python scripts/collect_trend_regime_force_orders.py ...
```

### 2) `signal_count` 长期为 0

优先排查：

1. `trend_regime_phase1a_rows.jsonl` 是否在更新
2. `data_age_sec` 是否过大导致 `api_stale`
3. `oi_change_1h_pct` 是否持续低于阈值
4. `liquidation_notional_1h_usdt` 是否长期为 0

### 3) 容器频繁重启

检查：

- 内存是否不足（建议至少 512MB）
- 网络波动导致 API 超时
- 服务器时间是否异常

---

## 运维命令 (Ops Commands)

```bash
# 查看状态
docker ps

# 实时日志
docker logs -f trend-rows
docker logs -f trend-forceorder
docker logs -f trend-watchlist

# 重启单个服务
docker restart trend-rows
docker restart trend-forceorder
docker restart trend-watchlist

# 停止并删除
docker stop trend-rows trend-forceorder trend-watchlist
docker rm trend-rows trend-forceorder trend-watchlist
```

---

## 建议执行顺序 (Recommended Rollout)

1. 先启动 `trend-rows`，确认 rows 文件正常增长。
2. 再启动 `trend-forceorder`（附 `--raw-output`），确认 cache 与 raw JSONL 文件正常落盘。
3. 最后启动 `trend-watchlist`，确认 heartbeat 与 reject 统计持续输出。
4. 采集至少 1 小时后，运行 `aggregate_trend_regime_liquidations.py` 生成小时级清算代理文件。
5. 回拉数据后，执行本地 `replay_trend_regime_shadow.py`（附 `--liquidation-hourly-jsonl`），确认 `liquidation_coverage_ratio` 不全为 0。
6. 连续观察 24h 后，再进入下一轮 review 与参数决策。
