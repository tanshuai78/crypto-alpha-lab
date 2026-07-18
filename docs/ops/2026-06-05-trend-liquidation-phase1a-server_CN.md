# Trend/Liquidation Phase 1A 服务器部署与运行指南

> 最后更新：2026-06-15

> 入口文档：`docs/ops/2026-06-05-ops-index_CN.md`

## 目的 (Purpose)

以**仅观察模式 (observation-only mode)** 运行 `Trend / Liquidation Regime` 的 Phase 1A 数据链路与监控链路，不接入 `execution`，不触发任何交易执行。

本指南目标是稳定跑通三段链路：

1. `B`：市场行生产器 `build_trend_regime_market_rows.py`（生成 `trend_regime_phase1a_rows.jsonl`）
2. `A`：清算采集器 `collect_trend_regime_force_orders.py`（生成 `trend_regime_liquidation_cache.json`）
3. `watchlist`：`run_trend_regime_watchlist.py`（消费 A+B 并输出观测日志）

---

## 章节目录 (Table of Contents)

1. 目的与术语
1. 运行边界与部署前检查
1. 本地同步与 Docker 部署
1. 快速验证与 24 小时巡检
1. Raw forceOrder 事件采集
1. 多粒度清算聚合与派生
1. 24 小时部署后验收门禁
1. 定期回拉与本地复核
1. 本地历史回放
1. 常见问题与处理
1. 运维命令
1. 建议执行顺序

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
    --raw-output data/trend_regime_force_orders_raw.jsonl \
    --raw-rotate-max-bytes 268435456 \
    --raw-rotate-backup-dir data/backup \
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

除了生成滚动窗口清算缓存（`--output`）外，`collect_trend_regime_force_orders.py` 还支持 `--raw-output` 参数，将每条强平事件逐行追加到 JSONL 文件中。这里的 raw JSONL 是 **primary append-only archive**；`trend_regime_liquidation_cache.json` 只是 **legacy compatibility cache**，仅供现有 watchlist 读取。

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
    --raw-rotate-max-bytes 268435456 \
    --raw-rotate-backup-dir data/backup \
    --flush-interval-sec 5 \
    --max-seconds 0
```

### 输出格式

每条事件追加一行 JSON。当前 research raw schema 至少包含以下字段：

| 字段 | 含义 |
|---|---|
| `schema_version` | raw schema 版本号 |
| `source` | 数据源标识，当前为 `binance_forceorder_ws` |
| `event_id` | 原始事件稳定去重键 |
| `symbol` | 规范化交易对，如 `BTC/USDT` |
| `exchange_symbol` | 交易所原始交易对，如 `BTCUSDT` |
| `event_time_ms` | WebSocket 事件时间戳（毫秒） |
| `trade_time_ms` | 强平成交时间戳（毫秒） |
| `side` | 强平单方向（`BUY` / `SELL`） |
| `liquidated_position_side` | 被清算仓位方向：`long` 或 `short` |
| `liquidation_side` | 研究语义方向：`long_liquidation` 或 `short_liquidation` |
| `price` | 成交价格 |
| `quantity` | 成交数量 |
| `notional_usdt` | 本次事件的名义金额（USDT） |
| `raw_payload` | 原始 WebSocket payload |

**语义说明**：`liquidated_position_side=long` / `liquidation_side=long_liquidation` 表示多仓被强平（产生 `SELL` 单）；`liquidated_position_side=short` / `liquidation_side=short_liquidation` 表示空仓被强平（产生 `BUY` 单）。

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

## 多粒度清算聚合与派生机制 (Multi-Granularity Liquidation Derivation & Aggregation)

在升级后的采集架构中：
1. **Raw Event Archive 是唯一真实数据源 (Primary Fact Source)**：`trend_regime_force_orders_raw.jsonl` 中持久化了所有原始强平事件。
2. **Cache 仅用于遗留兼容性 (Legacy Compatibility Only)**：`trend_regime_liquidation_cache.json` 仅用于为内存 Watchlist 快速提供 1h 滚动总清算额。
3. **派生数据 (Derived Outputs)**：所有研究和回放用的清算指标都应从原始归档按 canonical timestamp 派生为以下三个文件：
   - `trend_regime_liquidation_1m.jsonl`：1分钟级别清算聚合（含 zero-fill）。
   - `trend_regime_liquidation_5m.jsonl`：5分钟级别清算聚合（含 zero-fill）。
   - `trend_regime_liquidation_hourly.jsonl`：1小时级别清算聚合（保持遗留的 `hour_bucket_ms` 字段结构）。

### 定期派生 Crontab 配置 (Cron-based Derivation Schedule)

> [!CAUTION]
> **2026-07-18 当前状态：服务器端 `run_trend_liq_*` 定时派生已停用。**
>
> Jul 16 的 OOM 日志确认，`run_trend_liq_hourly.sh` 中的 `aggregate_trend_regime_liquidations.py --bucket 1h` 曾被 kernel OOM killer 杀掉。该脚本会全量读取 `trend_regime_force_orders_raw.jsonl`，不适合在约 `1.6GB` 内存的小服务器上长期定时运行。
>
> 当前推荐：服务器只保留 `trend-forceorder` raw 采集；`1m/5m/hourly` 派生在本地 Mac 同步 raw 后按需执行。除非 `aggregate_trend_regime_liquidations.py` 已改为增量/窗口化，否则不要恢复下面的 cron 派生任务。

在服务器上配置 crontab 定期执行派生脚本。
> [!WARNING]
> 对于 `1m` 和 `5m` 颗粒度，由于使用了 `--fill-empty-buckets` 填充所有无交易时段的空桶，高频写入会占用一定的存储空间与 IOPS。更关键的是，`scripts/aggregate_trend_regime_liquidations.py` 当前会全量读取 `trend_regime_force_orders_raw.jsonl` 后再聚合；随着 raw archive 增长，调度频率过高会导致 CPU / 内存压力显著上升。

历史 crontab 调度配置（当前不再推荐直接启用）：
```cron
# 每 5 分钟串行执行 1m + 5m 聚合。
# 使用 flock 防止跨分钟重叠；使用 nice 降低对 sshd 和采集进程的资源争抢。
*/5 * * * * flock -n /tmp/trend_liq_derive.lock bash -lc '
  cd /root/crypto-alpha-lab || exit 1
  now_ms=$(($(date +\%s)*1000))
  start_ms=$((now_ms - 86400000))
  PYTHONPATH=. nice -n 10 python3 scripts/aggregate_trend_regime_liquidations.py \
    --bucket 1m \
    --fill-empty-buckets \
    --start-ms "$start_ms" \
    --end-ms "$now_ms" \
    --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
    --output data/trend_regime_liquidation_1m.jsonl &&
  PYTHONPATH=. nice -n 10 python3 scripts/aggregate_trend_regime_liquidations.py \
    --bucket 5m \
    --fill-empty-buckets \
    --start-ms "$start_ms" \
    --end-ms "$now_ms" \
    --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
    --output data/trend_regime_liquidation_5m.jsonl
' >> /root/crypto-alpha-lab/logs/trend_liq_derive.log 2>&1

# 每小时第 5 分钟执行一次 1h 聚合。
# 复用同一把锁，避免整点附近与 1m/5m 聚合并发读取同一个 raw archive。
5 * * * * flock -n /tmp/trend_liq_derive.lock bash -lc '
  cd /root/crypto-alpha-lab || exit 1
  PYTHONPATH=. nice -n 10 python3 scripts/aggregate_trend_regime_liquidations.py \
    --bucket 1h \
    --output data/trend_regime_liquidation_hourly.jsonl
' >> /root/crypto-alpha-lab/logs/trend_liq_hourly.log 2>&1

# 健康检查降频到每 30 分钟一次。
# 当前脚本会全量扫描 raw + aggregate 文件，不适合与高频聚合绑定在同一周期。
*/30 * * * * flock -n /tmp/trend_liq_derive.lock bash -lc '
  cd /root/crypto-alpha-lab || exit 1
  PYTHONPATH=. nice -n 10 python3 scripts/check_liquidation_collector_health.py \
    --data-dir data
' > /root/crypto-alpha-lab/data/trend_regime_liquidation_health.json 2>> /root/crypto-alpha-lab/logs/trend_liq_health.log
```

说明：

1. `&&` 只能保证同一条 cron 内部按顺序执行，不能阻止下一轮 cron 到点后再次启动；真正防重叠的是 `flock -n /tmp/trend_liq_derive.lock`。
2. `1m` 聚合已从“每分钟一次”降为“每 5 分钟一次”。这是因为 `1m` 文件主要用于本地研究回放，不需要在服务器上每分钟全量重算。
3. `health check` 不再与 `1m/5m` 聚合绑定为同周期串行任务，而是单独降频。原因是 `scripts/check_liquidation_collector_health.py` 同样会全量扫描 raw archive 和聚合文件，高频运行会额外放大 CPU 压力。
4. 如果某一轮聚合尚未结束，下一轮会因为 `flock -n` 直接跳过。这比堆积多个 Python 进程更安全。

### 推荐安装方式：脚本包装 + `crontab <file>` (Recommended Install Method)

不要优先使用 `crontab -e` 手工编辑超长命令。

原因：

1. SSH 不稳定时，交互式编辑器容易中途断开，导致保存失败或误写。
2. `crontab` 的每条任务本质上必须是单行；把多行 `bash -lc '...'` 直接粘进去，容易触发 `bad minute`。
3. 将复杂逻辑放进独立脚本后，cron 本身只保留短命令，便于审计、替换与回滚。

推荐 sequence：

1. 先写 shell 脚本：
   - `scripts/run_trend_liq_derive.sh`
   - `scripts/run_trend_liq_hourly.sh`
   - `scripts/run_trend_liq_health.sh`
2. 再写 cron 文件，例如：`/root/crypto-alpha-lab/trend_liq_safe.cron`
3. 使用非交互方式安装：
   ```bash
   crontab -l > /root/crontab.backup.$(date +%Y%m%d-%H%M%S)
   crontab /root/crypto-alpha-lab/trend_liq_safe.cron
   crontab -l
   ```

### 实际部署文件（2026-06-15 历史落地版本） (Actual Deployed Files)

2026-06-15 曾经落地的安全版调度，不再直接把复杂命令写进 `crontab`，而是通过以下 3 个脚本承载：

1. `/root/crypto-alpha-lab/scripts/run_trend_liq_derive.sh`
   - 串行执行 `1m` 与 `5m` 聚合。
   - 自动计算最近 24h 的 `start_ms` / `end_ms`。
2. `/root/crypto-alpha-lab/scripts/run_trend_liq_hourly.sh`
   - 执行 `1h` 聚合。
3. `/root/crypto-alpha-lab/scripts/run_trend_liq_health.sh`
   - 运行 `scripts/check_liquidation_collector_health.py` 并输出健康摘要。

对应的历史 `crontab` 入口是：

```cron
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

*/5 * * * * flock -n /tmp/trend_liq_derive.lock /root/crypto-alpha-lab/scripts/run_trend_liq_derive.sh >> /root/crypto-alpha-lab/logs/trend_liq_derive.log 2>&1
5 * * * * flock -n /tmp/trend_liq_derive.lock /root/crypto-alpha-lab/scripts/run_trend_liq_hourly.sh >> /root/crypto-alpha-lab/logs/trend_liq_hourly.log 2>&1
*/30 * * * * flock -n /tmp/trend_liq_derive.lock /root/crypto-alpha-lab/scripts/run_trend_liq_health.sh > /root/crypto-alpha-lab/data/trend_regime_liquidation_health.json 2>> /root/crypto-alpha-lab/logs/trend_liq_health.log
```

历史验收命令：

```bash
crontab -l
crontab -l | grep -E 'flock|run_trend_liq'
```

只有当输出中能看到 `flock` 和三个 `run_trend_liq_*` 脚本时，才说明旧版 `*/1` / `*/15` 任务已被成功替换。

### 实际部署状态（2026-07-18 当前） (Current Deployed State)

当前服务器上已移除 `run_trend_liq_*` cron，避免全量聚合任务再次触发 OOM。

当前推荐的 `crontab` 输出应只保留环境行：

```cron
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

停用命令：

```bash
crontab -l > /root/crontab.backup.$(date +%Y%m%d-%H%M%S)
crontab -l | grep -v 'run_trend_liq_' | crontab -
crontab -l | nl -ba
```

服务器端仍应保留：

1. `trend-forceorder`：持续采集 `data/trend_regime_force_orders_raw.jsonl`。
2. `trend-rows` / `trend-watchlist`：如仍需要实时观察，可继续运行。
3. `my-collector`：在 `my-bitcoin-project` 中持续采集 orderbook。

本地按需派生命令：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl \
  data/route_c1_live/

END_MS=$(python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
)
START_MS=$((END_MS - 35*24*60*60*1000))

PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/route_c1_live/trend_regime_force_orders_raw.jsonl \
  --bucket 1m \
  --fill-empty-buckets \
  --start-ms "$START_MS" \
  --end-ms "$END_MS" \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --output data/route_c1_live/trend_regime_liquidation_1m.jsonl

PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/route_c1_live/trend_regime_force_orders_raw.jsonl \
  --bucket 5m \
  --fill-empty-buckets \
  --start-ms "$START_MS" \
  --end-ms "$END_MS" \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --output data/route_c1_live/trend_regime_liquidation_5m.jsonl

PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/route_c1_live/trend_regime_force_orders_raw.jsonl \
  --bucket 1h \
  --output data/route_c1_live/trend_regime_liquidation_hourly.jsonl
```

验收命令：

```bash
crontab -l | grep -E 'run_trend_liq|aggregate_trend_regime_liquidations|check_liquidation' || echo "trend_liq_cron_disabled"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
wc -l /root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl
```

预期：

1. `trend_liq_cron_disabled` 出现。
2. `trend-forceorder` 仍在运行。
3. raw 文件行数继续增长。

### 2026-07-18 事故记录：cron hourly 聚合触发 OOM (Incident Note)

现象：

1. 服务器曾因内存 OOM 卡死并导致数据采集中断。
2. Docker 容器检查显示 `trend-forceorder`、`trend-rows`、`trend-watchlist`、`crypto-watchlist` 均为 `OOMKilled=false`。
3. kernel 日志显示被杀目标为 `cron.service` 下的 `python3`。

关键证据：

```text
oom-kill: ... task_memcg=/system.slice/cron.service,task=python3
Out of memory: Killed process ... (python3) ... anon-rss:879760kB
run_trend_liq_hourly.sh: line 8: ... Killed PYTHONPATH=. nice -n 10 python3 scripts/aggregate_trend_regime_liquidations.py --input data/trend_regime_force_orders_raw.jsonl --bucket 1h --output data/trend_regime_liquidation_hourly.jsonl
```

结论：

1. 直接 OOM 目标是 `run_trend_liq_hourly.sh` 的全量 `1h` 聚合。
2. 根因不是 Docker 容器 OOM，也不是磁盘满。
3. `flock` 能防止并发堆积，但不能降低单次全量聚合的内存峰值。
4. 只要 raw archive 继续增长，服务器端 `1m/5m/hourly/health` 全量扫描都有长期复发风险。

本次处理：

1. 备份 crontab。
2. 移除所有 `run_trend_liq_*` cron。
3. 将后续派生职责迁移到本地 Mac。

### 2026-06-15 事故记录：CPU 99% / SSH 断开 (Incident Note)

现象：

1. 服务器 CPU 长时间接近 `99%`。
2. SSH 连接经常在认证前后直接被关闭：`Connection closed by 47.82.4.85 port 22`。
3. 根分区并未打满：`df -h` 显示 `/` 仍有约 `13G` 可用空间，使用率约 `56%`。

直接原因：

1. `scripts/aggregate_trend_regime_liquidations.py` 当前实现会先全量读取 `trend_regime_force_orders_raw.jsonl`，再做聚合；raw archive 越大，单次执行越慢。
2. 原始 crontab 中 `1m` 聚合为 `*/1`，当单次运行超过 60 秒后，下一分钟 cron 会启动新的 Python 进程，导致多个聚合任务重叠。
3. `5m` 聚合与健康检查同时读取同一个大文件，进一步放大 CPU、内存与 I/O 争抢。
4. 当系统资源被抢空时，`sshd` 可能无法及时分配资源或受到 OOM / 调度抖动影响，从而表现为 SSH 连接被直接关闭。

已排除项：

1. 这次问题的主因不是根分区磁盘已满；磁盘空间不是当前首要瓶颈。
2. 清理 `/root/my-bitcoin-project/...` 的旧 orderbook 数据，不会直接解决 `/root/crypto-alpha-lab` 当前这套 liquidation 派生链路的 CPU 问题。

本次缓解方案：

1. 将 `1m` 聚合从“每分钟一次”降为“每 5 分钟一次”。
2. 为派生任务增加 `flock` 锁，禁止跨分钟重叠执行。
3. 为聚合和健康检查增加 `nice -n 10`，降低它们与 sshd / 采集器争抢 CPU 的优先级。
4. 将健康检查降频到每 30 分钟一次，避免它与高频派生同时全量扫描 raw archive。

后续长期修复方向：

1. 将 `trend_regime_force_orders_raw.jsonl` 改为更积极的日切或周切归档，避免 active raw 文件无限增长。
2. 将 `aggregate_trend_regime_liquidations.py` 改为增量聚合，只处理“上次聚合后新增的 raw 事件”，不要每次全量读取整个 archive。

### 历史脚本式 cron 切换后 10 分钟巡检 (Historical 10-Minute Post-Switch Checklist)

> [!NOTE]
> 本节用于复盘 2026-06-15 的脚本式 cron 切换流程。2026-07-18 之后，当前推荐状态是停用 `run_trend_liq_*` cron；不要用本节作为恢复服务器端定时派生的操作清单。

切换完成后的前 10 分钟，不要只看 `crontab -l`。必须同时检查“旧进程是否退干净、CPU 是否回落、派生文件是否继续更新”。

第 0 分钟：确认新 cron 仍在

```bash
crontab -l
crontab -l | grep -E 'flock|run_trend_liq'
```

预期：

1. 只看到 3 条新任务。
2. 不再出现旧的 `*/1` 和 `*/15` 条目。

第 0 到 1 分钟：确认没有旧残留进程堆积

```bash
pgrep -af 'aggregate_trend_regime_liquidations.py|check_liquidation_collector_health.py|run_trend_liq'
```

预期：

1. 最多只看到当前这一轮对应的少量进程。
2. 不应该出现多组历史遗留的聚合进程同时常驻。

第 1 到 3 分钟：看 CPU / load 是否开始回落

```bash
uptime
ps -eo pid,etime,%cpu,%mem,cmd --sort=-%cpu | head -20
```

预期：

1. 不再有多个 `aggregate_trend_regime_liquidations.py` 同时高 CPU 占用。
2. `sshd` 不应继续被批处理任务压制。

第 3 到 5 分钟：检查派生日志

```bash
tail -n 50 /root/crypto-alpha-lab/logs/trend_liq_derive.log
tail -n 50 /root/crypto-alpha-lab/logs/trend_liq_hourly.log
tail -n 50 /root/crypto-alpha-lab/logs/trend_liq_health.log
```

预期：

1. 没有持续 traceback。
2. 没有权限错误、路径错误或 `file not found`。

第 5 到 7 分钟：确认 `1m/5m` 派生文件继续更新

```bash
ls -lh /root/crypto-alpha-lab/data/trend_regime_liquidation_1m.jsonl
ls -lh /root/crypto-alpha-lab/data/trend_regime_liquidation_5m.jsonl
stat /root/crypto-alpha-lab/data/trend_regime_liquidation_1m.jsonl
stat /root/crypto-alpha-lab/data/trend_regime_liquidation_5m.jsonl
```

预期：

1. 文件存在。
2. 修改时间刷新到最近几分钟。

第 7 到 10 分钟：确认 health 摘要继续产出

```bash
ls -lh /root/crypto-alpha-lab/data/trend_regime_liquidation_health.json
tail -n 50 /root/crypto-alpha-lab/logs/trend_liq_health.log
```

预期：

1. health JSON 存在。
2. 没有连续报错。

额外检查：排查 OOM

```bash
dmesg -T | grep -i -E 'killed process|out of memory|oom'
```

预期：

切换后不应继续新增由聚合脚本引发的 OOM 记录。

### 历史失败回滚方法 (Historical Rollback Procedure)

> [!CAUTION]
> 当前不要回滚到包含 `run_trend_liq_hourly.sh` 的旧 cron。Jul 16 已确认该 hourly 全量聚合会触发 OOM。本节只用于理解历史切换流程，不作为当前恢复方案。

如果新 cron 安装失败、脚本路径写错，或者切换后 10 分钟内系统状态更差，按以下顺序回滚：

1. 查看最近一次备份：
   ```bash
   ls -lt /root/crontab.backup.*
   ```
2. 恢复旧版 cron：
   ```bash
   crontab /root/crontab.backup.<timestamp>
   crontab -l
   ```
3. 如有必要，临时停用新脚本日志写入：
   ```bash
   mv /root/crypto-alpha-lab/scripts/run_trend_liq_derive.sh /root/crypto-alpha-lab/scripts/run_trend_liq_derive.sh.disabled
   mv /root/crypto-alpha-lab/scripts/run_trend_liq_hourly.sh /root/crypto-alpha-lab/scripts/run_trend_liq_hourly.sh.disabled
   mv /root/crypto-alpha-lab/scripts/run_trend_liq_health.sh /root/crypto-alpha-lab/scripts/run_trend_liq_health.sh.disabled
   ```
4. 回滚后立即再次执行：
   ```bash
   crontab -l
   pgrep -af 'aggregate_trend_regime_liquidations.py|check_liquidation_collector_health.py|run_trend_liq'
   ```

注意：

回滚只解决“调度层配置错误”。如果根因是 raw archive 已经过大，旧 cron 恢复后仍可能重新触发 CPU 过高问题，因此回滚后应优先继续推进 raw 轮转或增量聚合修复。

### 归档备份与 Checksum 轮转策略 (Archive Backup & Checksum Rotation)

为防止原始归档文件（`trend_regime_force_orders_raw.jsonl`）体积无限增长，采集脚本现已支持自动轮转：

```bash
python scripts/collect_trend_regime_force_orders.py \
  --raw-output data/trend_regime_force_orders_raw.jsonl \
  --raw-rotate-max-bytes 536870912 \
  --raw-rotate-backup-dir data/backup
```

默认阈值为 `512 MiB`。如果你需要在维护窗口里手动做一次确定性的归档，下面的周度轮转 sequence 仍然有效：

1. **停止采集服务**。
2. **计算原始文件校验和**：
   ```bash
   sha256sum data/trend_regime_force_orders_raw.jsonl > data/trend_regime_force_orders_raw.jsonl.sha256
   ```
3. **备份并重命名**：
   ```bash
   mv data/trend_regime_force_orders_raw.jsonl data/backup/trend_regime_force_orders_raw_$(date +\%Y\%m\%d).jsonl
   mv data/trend_regime_force_orders_raw.jsonl.sha256 data/backup/
   ```
4. **重建空的 Raw 归档文件**：
   ```bash
   touch data/trend_regime_force_orders_raw.jsonl
   ```
5. **重启采集服务**。

---

## 24小时部署后验收门禁 (24h Post-Deploy Acceptance Gate)

新采集链路部署并运行 24 小时后，运行 `scripts/check_liquidation_collector_health.py` 对链路进行验收。
验收标准的健康检查输出必须满足以下条件，否则判定为部署不合格，严禁启动后续 `liquidation_shock_event_study` 的回放与研究：
- `raw_exists` 为 `true`
- `raw_time_span_hours` 必须 `>= 24.0`
- `raw_invalid_json_line_count` 必须为 `0`
- `raw_duplicate_event_count` 必须为 `0` (或极低水平)
- `aggregate_1m_exists` 为 `true`
- `aggregate_1m_coverage_ratio_24h` 必须 `>= 0.99`
- `aggregate_1m_max_gap_minutes_24h` 必须 `<= 1`
- `aggregate_5m_exists` 为 `true`
- `aggregate_1h_exists` 为 `true`
- `research_ready_1m_24h` 必须为 `true`

---

---

## 定期回拉与本地复核 (Pullback & Local Review)

结论：建议**定期回拉**，但不必高频全量回拉。

推荐节奏：

1. 每 4 小时：服务器先产出摘要，本地回拉摘要文件。
2. 每 24 小时：回拉完整 `trend_regime_watch_events.jsonl`，并按需抽样回拉 `trend_regime_phase1a_rows.jsonl`；同时回拉 `trend_regime_force_orders_raw.jsonl`，在本地派生 `trend_regime_liquidation_hourly.jsonl` 供回放。
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

# 3) 原始强平归档（本地派生小时级清算代理）
rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/
```

本地派生小时级清算代理：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime/trend_regime_force_orders_raw.jsonl \
  --bucket 1h \
  --output data/trend_regime/trend_regime_liquidation_hourly.jsonl
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
PYTHONPATH=. python3 scripts/replay_trend_regime_shadow.py \
  --input data/trend_regime_historical_rows.jsonl \
  --output reports/trend_regime/replay_summary.json \
  --liquidation-hourly-jsonl data/trend_regime/trend_regime_liquidation_hourly.jsonl
```

### 不带清算数据的冒烟回放（仅验证流程）

```bash
PYTHONPATH=. python3 scripts/replay_trend_regime_shadow.py \
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
4. 采集至少 1 小时后，先回拉 raw，再在本地运行 `aggregate_trend_regime_liquidations.py` 生成小时级清算代理文件。
5. 回拉数据后，执行本地 `replay_trend_regime_shadow.py`（附 `--liquidation-hourly-jsonl`），确认 `liquidation_coverage_ratio` 不全为 0。
6. 连续观察 24h 后，再进入下一轮 review 与参数决策。
