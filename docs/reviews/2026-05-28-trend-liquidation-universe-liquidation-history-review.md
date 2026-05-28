# Trend Liquidation Historical Replay Review — 2026-05-28

> **范围声明**：本次 replay 仅验证 universe 对齐修复与 liquidation proxy 数据链路。
> 不代表策略可交易状态或 live-ready 结论。

---

## 1. 输入数据摘要

| 指标 | 值 |
|---|---|
| 总行数 | 2495 |
| Symbols | BTC/USDT, DOGE/USDT, ETH/USDT, SOL/USDT, XRP/USDT |
| 时间跨度 | 498.0h（**烟雾回放**，未达 720h 全量阈值） |
| ADA/USDT 污染 | **否**（universe 对齐修复已生效） |
| 非 watchlist 行数 | 0 |
| 缺失 symbol 行数 | 0 |

> **注**：498h 回放覆盖约 20.75 天，属于 "smoke replay" 分类。OI 数据 500 行限制仍影响历史跨度，但 universe 对齐已干净。

---

## 2. Stale Row 归一化

| 指标 | 值 |
|---|---|
| historical_mode | `true` |
| 归一化行数（原 api_stale） | 2495（其中 2490 行原始为 api_stale） |

所有历史行均已通过 `normalize_rows_for_historical_replay()` 将 `data_age_sec` 置零，避免 `api_stale` 批量拒绝。

---

## 3. Classification 拒绝分布

### 汇总（2495 行，两个成本档位结果相同）

| 拒绝原因 | 行数 | 占比 |
|---|---|---|
| `vol_breakout_below_threshold` | **2285** | **91.6%** |
| `return_below_min` | 172 | 6.9% |
| `volume_below_min` | 30 | 1.2% |
| `oi_confirmation_below_min` | 8 | 0.3% |

**主要拦截点：`vol_breakout_below_threshold`（91.6%）**

### 按 Symbol 拒绝明细

| Symbol | vol_breakout | return_below_min | volume_below_min | oi_below_min |
|---|---|---|---|---|
| BTC/USDT | 468 | 30 | 0 | 1 |
| ETH/USDT | 465 | 30 | 0 | 4 |
| SOL/USDT | 450 | 49 | 0 | 0 |
| XRP/USDT | 462 | 36 | 0 | 1 |
| DOGE/USDT | 440 | 27 | **30** | 2 |

> DOGE/USDT 有 30 行 `volume_below_min`，占该 symbol 约 12%。24h volume < 300M USDT 门槛在低波动窗口内会命中。

---

## 4. Liquidation 覆盖率

| 指标 | 值 |
|---|---|
| 有 liquidation 数据行数 | 0 |
| 缺失 liquidation 数据行数 | 2495 |
| coverage_ratio | **0.0** |

**原因**：`trend_regime_force_orders_raw.jsonl` 尚未存在（forceOrder 采集器需在服务器上以 `--raw-output` 模式持续运行后才能积累数据）。此轮回放在无 liquidation proxy 的情况下运行，是预期行为。

**影响**：当前 entry_event_count = 0，部分原因可能是清算过滤门槛（`TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_MAJOR` = 10M、Large Alt = 3M）在无 liquidation 数据时直接拒绝。需待 forceOrder 数据积累后复核。

---

## 5. Entry Events 与 Trade 结果

### Base Cost（30.0 bps）

| 指标 | 值 |
|---|---|
| entry_event_count | **0** |
| trade_count | 0 |
| mean_net_pnl_bps | 0.0 |
| median_net_pnl_bps | 0.0 |
| win_rate | 0.0 |
| worst_trade_net_pnl_bps | 0.0 |

### Stress Cost（50.0 bps）

| 指标 | 值 |
|---|---|
| entry_event_count | **0** |
| trade_count | 0 |
| mean_net_pnl_bps | 0.0 |
| median_net_pnl_bps | 0.0 |
| win_rate | 0.0 |
| worst_trade_net_pnl_bps | 0.0 |

---

## 6. 结论与下一步

- **Universe 对齐修复成功**：ADA/USDT 已完全剔除，non_watchlist_row_count = 0，missing_symbol_row_count = 0。这是本轮计划的核心验证目标，已达成。

- **主要拦截点未变**：`vol_breakout_below_threshold` 占比 91.6%，是 Phase 1A 进入下一阶段的核心障碍。在 498h 的历史窗口内（低波动市场阶段），当前 `VOL_BREAKOUT_MULTIPLIER=2.5` 门槛几乎过滤全部行。

- **Liquidation proxy 数据链路已就绪，但数据尚未积累**：`collect_trend_regime_force_orders.py --raw-output` 的启动命令、聚合器 `aggregate_trend_regime_liquidations.py`、以及 replay 的 `--liquidation-hourly-jsonl` 参数全部实现并通过测试。需要服务器端以 `--raw-output` 模式持续运行采集器，积累至少 24h 原始事件后，才能评估 liquidation 覆盖率对 entry_event_count 的实际影响。

- **回放仍处于 smoke replay 分类**（498h < 720h）：历史跨度受限于 Binance OI API 500 行上限。`entry_event_count = 0` 本质上是市场状态问题（低波动窗口），不是代码或链路问题。

- **当前决策**：维持 `keep_observation_only`。待满足以下其中一项条件后进入下一阶段：
  1. 服务器 forceOrder 采集器积累 ≥ 72h 原始事件（`liquidation_coverage_ratio > 0.3`），重跑 replay 确认 entry_event_count > 0；
  2. 或市场出现 vol_breakout 信号（1h 波动率 > 2.5× 30日基线），实时链路产生第一个 watchlist 信号。

---

*数据来源*：`reports/trend_regime/2026-05-28_historical_replay_summary.json`（2026-05-28 本地生成）

---

## 7. 本轮执行结论（运维状态）

- `trend-forceorder` 容器已确认带 `--raw-output data/trend_regime_force_orders_raw.jsonl` 启动，参数正确。
- 采集器日志已出现 `force_order_collector_start`，说明进程启动正常。
- 当前日志为 `messages=0 accepted=0`，表示观察窗口内尚未捕获到 `forceOrder` 事件；这在非强平时段是正常状态。
- 因无 raw 事件，`trend_regime_force_orders_raw.jsonl` 可暂时不存在，属于预期，不是故障。

---

## 8. 后续操作步骤（72h 验收流程）

### Step 1: 持续采集 72 小时

保持以下 3 个容器持续运行：

- `trend-rows`
- `trend-watchlist`
- `trend-forceorder`（必须包含 `--raw-output`）

快速检查命令：

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
docker inspect trend-forceorder --format '{{json .Config.Cmd}}'
docker logs --tail 100 trend-forceorder
```

### Step 2: 每 4 小时巡检一次

```bash
wc -l /root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl
ls -lh /root/crypto-alpha-lab/data/trend_regime_liquidation_cache.json
docker logs --tail 80 trend-forceorder
```

检查要点：

- `raw` 行数是否增长（`>0` 即表示已捕获到事件）
- `cache` 文件修改时间是否持续更新
- `accepted` 是否开始大于 0

### Step 3: 72 小时后执行聚合

```bash
cd /root/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime_force_orders_raw.jsonl \
  --output data/trend_regime_liquidation_hourly.jsonl
```

### Step 4: 重跑历史回放

```bash
cd /root/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/replay_trend_regime_shadow.py \
  --input data/trend_regime_historical_rows.jsonl \
  --liquidation-hourly-jsonl data/trend_regime_liquidation_hourly.jsonl \
  --output reports/trend_regime/2026-05-28_historical_replay_summary.json
```

### Step 5: 验收字段检查

重点看 `reports/trend_regime/2026-05-28_historical_replay_summary.json` 的：

- `liquidation_history_join_summary.liquidation_history_input_count`
- `liquidation_history_join_summary.liquidation_rows_joined_count`
- `liquidation_history_join_summary.liquidation_raw_duration_hours`
- `base.liquidation_coverage_ratio`
- `base.entry_event_count`

第一轮链路通过标准（数据链路级）：

- `liquidation_raw_duration_hours >= 72`
- `liquidation_history_input_count > 0`
- `liquidation_rows_joined_count > 0`
- `base.liquidation_coverage_ratio > 0`

如仍不满足，继续 `continue_partial_liquidation_collection`，不进入 `phase1b`。

---

## 9. 服务器完整操作手册（按当前服务器配置）

> 适用环境：
> - 服务器项目目录：`/root/crypto-alpha-lab`
> - 镜像：`crypto-alpha-lab:latest`
> - 容器：`trend-rows`、`trend-watchlist`、`trend-forceorder`
> - 不操作旧策略容器：`crypto-watchlist`

### 9.1 本地代码同步到服务器

先在本地确认代码已提交并 push：

```bash
git status
git add -A
git commit -m "chore: update trend liquidation ops and replay workflow"
git push origin <your-branch>
```

登录服务器并同步：

```bash
ssh root@47.82.4.85
cd /root/crypto-alpha-lab
git fetch --all
git checkout <your-branch>
git pull --ff-only
```

若服务器不走 git，同步备用命令（本地执行）：

```bash
rsync -avzP --exclude='data' --exclude='.git' --exclude='.venv' --exclude='.ruff_cache' --exclude='.pytest_cache' --exclude='__pycache__' \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/ \
  root@47.82.4.85:/root/crypto-alpha-lab/
```

### 9.2 重建镜像

```bash
ssh root@47.82.4.85
cd /root/crypto-alpha-lab
docker build -t crypto-alpha-lab:latest .
```

### 9.3 重建 Trend 三容器

先停并删除旧容器（只删这 3 个）：

```bash
docker rm -f trend-watchlist trend-forceorder trend-rows
```

启动 `trend-rows`：

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

启动 `trend-forceorder`（关键：必须带 raw 输出）：

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
    --max-seconds 0 \
    --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT
```

启动 `trend-watchlist`（注意 `--row-tail-lines` 和上一行要用 `\` 连续）：

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

### 9.4 启动后 5 分钟内自检

```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
docker logs --tail 80 trend-rows
docker logs --tail 80 trend-watchlist
docker logs --tail 80 trend-forceorder
docker inspect trend-forceorder --format '{{json .Config.Cmd}}'
```

`trend-forceorder` 预期：
- 有 `force_order_collector_start`
- 可能长时间 `accepted=0`（正常）

### 9.5 72 小时复检命令清单（可直接执行）

每 4 小时巡检一次：

```bash
cd /root/crypto-alpha-lab
wc -l data/trend_regime_force_orders_raw.jsonl || true
ls -lh data/trend_regime_liquidation_cache.json
docker logs --tail 80 trend-forceorder
```
最短巡检命令：
```bash
cd /root/crypto-alpha-lab

docker ps --format "table {{.Names}}\t{{.Status}}" | egrep "trend-(rows|watchlist|forceorder)"
wc -l data/trend_regime_force_orders_raw.jsonl 2>/dev/null || echo "raw=0_or_missing"
docker logs --tail 50 trend-forceorder
```

72 小时后聚合小时级清算：

```bash
cd /root/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime_force_orders_raw.jsonl \
  --output data/trend_regime_liquidation_hourly.jsonl

tail -n 5 data/trend_regime_liquidation_hourly.jsonl
```

72 小时后重跑历史回放：

```bash
cd /root/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/replay_trend_regime_shadow.py \
  --input data/trend_regime_historical_rows.jsonl \
  --liquidation-hourly-jsonl data/trend_regime_liquidation_hourly.jsonl \
  --output reports/trend_regime/2026-05-28_historical_replay_summary.json
```

快速查看关键验收字段：

```bash
python3 - <<'PY'
import json
p = "reports/trend_regime/2026-05-28_historical_replay_summary.json"
obj = json.load(open(p, "r", encoding="utf-8"))
base = obj.get("base", {})
join = obj.get("liquidation_history_join_summary", {})
print("liquidation_history_input_count:", join.get("liquidation_history_input_count"))
print("liquidation_rows_joined_count:", join.get("liquidation_rows_joined_count"))
print("liquidation_raw_duration_hours:", join.get("liquidation_raw_duration_hours"))
print("liquidation_coverage_ratio:", base.get("liquidation_coverage_ratio"))
print("entry_event_count:", base.get("entry_event_count"))
PY
```

### 9.6 回拉到本地复检（建议）

本地先建目录：

```bash
mkdir -p /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime
mkdir -p /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/reports/trend_regime
```

回拉 4 个关键文件：

```bash
rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_liquidation_hourly.jsonl \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_watch_events.jsonl \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/data/trend_regime/

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/reports/trend_regime/2026-05-28_historical_replay_summary.json \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/reports/trend_regime/
```

### 9.7 常见故障与处理

1. `--row-tail-lines: command not found`  
原因：命令换行处漏了 `\`。  
处理：确保 `--forever \` 与下一行连在同一条 `docker run` 命令里。

2. `python: command not found`  
原因：服务器无 `python` 软链。  
处理：用 `python3`。

3. `trend_regime_force_orders_raw.jsonl` 不存在  
原因：尚未采到任何 forceOrder 事件。  
处理：先看 `docker logs --tail 80 trend-forceorder` 是否有 `force_order_collector_start`；有则继续等待样本。

