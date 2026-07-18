# Route C1 每日同步与 7d Overlap 跟踪清单

> 最后更新：2026-07-18

> 入口文档：`docs/ops/2026-06-05-ops-index_CN.md`

**适用场景：** Route C1 已经达到 `route_c1_overlap_ready_for_orderbook_aware`，并且 live overlap 已超过 `7d / 168h`；但 `7d live smoke` 结论仍为 `route_c1_baseline_match_failed`，不允许推广为 live filter。

**当前状态定义：**

```text
input ready, live smoke baseline not ready
```

也就是说：

- liquidation raw 输入已就绪；
- liquidation 1m 输入改为本地从 raw 派生；
- live 1m price 输入已就绪；
- orderbook-aware 输入门槛已就绪；
- 但 `baseline_match_rate` 未达到正式门槛，不能声明 Route C1 可用。
- 服务器端 `run_trend_liq_*` cron 已停用，避免小内存服务器因全量聚合触发 OOM。

---

## 1. 当前目标

这份清单只做一件事：

> 按需把服务器上的最新 raw liquidation / orderbook 同步回本地，在本地派生 1m/5m/hourly 数据，重建 live price 数据，重跑 overlap audit 或 live smoke。

当前阶段**不做**：

- 不调 Route C1 阈值；
- 不改 proxy 结论；
- 不在 `7d live smoke` 未通过时宣布 `30d forward` 结论；
- 不因为输入 ready 就宣布 live filter 可用。

---

## 2. 每日执行顺序

按需复核时按下面顺序执行：

1. 从服务器同步 raw liquidation 文件到 `data/route_c1_live/`
2. 从服务器同步 orderbook 文件到 `my-bitcoin-project/data/historical_orderbook/`
3. 在本地从 raw 派生 `1m/5m/hourly`
4. 基于最新 liquidation 1m 重建 live 1m price 数据集
5. 重跑 overlap audit 或 live smoke
6. 记录关键字段
7. 判断是否仍为 `route_c1_baseline_match_failed`

---

## 3. 目录约定

### 本地 `crypto-alpha-lab`

```text
/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
```

Route C1 live 数据目录：

```text
data/route_c1_live/
```

关键文件：

- `data/route_c1_live/trend_regime_force_orders_raw.jsonl`
- `data/route_c1_live/trend_regime_liquidation_1m.jsonl`
- `data/route_c1_live/trend_regime_liquidation_5m.jsonl`
- `data/route_c1_live/trend_regime_liquidation_hourly.jsonl`
- `data/route_c1_live/route_c1_live_price_1m_dataset.jsonl`
- `reports/route_c1/route_c1_data_overlap_audit_summary.json`

### 本地 `my-bitcoin-project`

```text
/Users/tanshuai/Desktop/AI-test/my-bitcoin-project
```

Orderbook 数据目录：

```text
data/historical_orderbook/
```

---

## 4. 每日同步命令

先在本地 Mac 终端设置服务器变量：

```bash
SERVER=root@47.82.4.85
```

### 4.1 同步 liquidation 数据

服务器端不再定时生成 `trend_regime_liquidation_1m/5m/hourly`。这里只同步 raw archive，派生文件在本地生成。

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
mkdir -p data/route_c1_live reports/route_c1

rsync -avzP $SERVER:/root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl ./data/route_c1_live/
```

### 4.2 同步 orderbook 数据

```bash
cd /Users/tanshuai/Desktop/AI-test/my-bitcoin-project
mkdir -p data/historical_orderbook

rsync -avzP $SERVER:/root/my-bitcoin-project/data/historical_orderbook/ ./data/historical_orderbook/
```

如果同步中断，优先用带断点续传的命令重跑：

```bash
SERVER=root@47.82.4.85

rsync -avzP \
  --partial \
  --append \
  --timeout=120 \
  -e "ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -o TCPKeepAlive=yes" \
  $SERVER:/root/my-bitcoin-project/data/historical_orderbook/ \
  ./data/historical_orderbook/
```

如果担心当天文件还在写入，可以先排除当天文件，单独补拉：

```bash
SERVER=root@47.82.4.85

rsync -avzP \
  --partial \
  --append \
  --timeout=120 \
  --exclude='*2026-06-05.jsonl' \
  -e "ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -o TCPKeepAlive=yes" \
  $SERVER:/root/my-bitcoin-project/data/historical_orderbook/ \
  ./data/historical_orderbook/
```

---

## 5. 本地派生 liquidation 1m/5m/hourly

每次同步完 raw liquidation 之后，在本地 `crypto-alpha-lab` 执行。不要在小内存服务器上定时全量聚合。

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

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

说明：

- `35d` 覆盖当前 Route C1 复核窗口，避免服务器 OOM，同时保留足够的 live smoke/forward 观察空间。
- 如果只做最近 7 天复核，可以把 `35*24*60*60*1000` 改为 `10*24*60*60*1000`。
- 如果要做更长窗口，优先在本地 Mac 上调大窗口，不要恢复服务器 cron。

---

## 6. 重建 live 1m price 数据集

每次同步完 liquidation 之后，在 `crypto-alpha-lab` 本地执行：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

PYTHONPATH=src uv run python scripts/build_liquidation_shock_event_dataset.py \
  --liquidation-jsonl data/route_c1_live/trend_regime_liquidation_1m.jsonl \
  --output-jsonl data/route_c1_live/route_c1_live_price_1m_dataset.jsonl \
  --events-output-jsonl reports/route_c1/route_c1_live_tmp_events.jsonl \
  --summary-output reports/route_c1/route_c1_live_price_build_summary.json
```

这一步的目的：

- 保证 `price-1m` 与最新 `live liquidation 1m` 时间窗对齐；
- 避免再次误用历史 Q1 2024 proxy 数据做 live overlap。

---

## 7. 重跑 overlap audit

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

PYTHONPATH=src uv run python scripts/audit_route_c1_data_overlap.py \
  --mode live_overlap \
  --liquidation-1m data/route_c1_live/trend_regime_liquidation_1m.jsonl \
  --price-1m data/route_c1_live/route_c1_live_price_1m_dataset.jsonl \
  --orderbook-dir /Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --output reports/route_c1/route_c1_data_overlap_audit_summary.json
```

查看结果：

```bash
cat /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/reports/route_c1/route_c1_data_overlap_audit_summary.json
```

---

## 8. 每次要看哪些字段

每次复核只重点看这几个字段：

### 8.1 输入存在性

必须都为 `true`：

- `liquidation_input_exists`
- `price_input_exists`
- `orderbook_dir_exists`

### 8.2 覆盖质量

理想目标：

- `liquidation_1m_zero_fill_coverage_24h = 1.0`
- `price_1m_coverage_24h >= 0.95`
- `orderbook_snapshot_coverage_24h >= 0.80`

当前目标是尽量接近：

```text
1.0 / 1.0 / 1.0
```

### 8.3 关键状态字段

- `ready_for_price_only`
- `ready_for_orderbook_aware`
- `decision`

当前理想值：

```text
ready_for_price_only = true
ready_for_orderbook_aware = true
decision = route_c1_overlap_ready_for_orderbook_aware
```

### 8.4 核心进度字段

最重要的是：

```text
overlap_hours_by_symbol
```

重点盯：

- `BTCUSDT`
- `ETHUSDT`
- `SOLUSDT`

因为 `7d live smoke` 的主要判断应基于主集，不应只依赖 `DOGE/XRP`。

---

## 9. 何时可以进入 7d Live Smoke

> [!NOTE]
> 这一节保留为历史门槛说明。当前本地 overlap 已超过 `168h`，并且已经运行过 `7d live smoke`；最新短板不是 overlap 时长，而是 `baseline_match_rate < 0.70`。

### 启动条件

当 `BTCUSDT`、`ETHUSDT`、`SOLUSDT` 的 overlap 都接近或达到：

```text
168h
```

才可以说：

```text
7d overlap ready
```

更保守的执行标准：

- `BTCUSDT >= 168h`
- `ETHUSDT >= 168h`
- `SOLUSDT >= 168h`
- `decision = route_c1_overlap_ready_for_orderbook_aware`

只有满足这些，才启动正式 `7d live smoke`。

### 还不能做什么

如果 overlap 只有：

```text
~72h
```

那只能说明：

- 输入链已打通；
- 研究可以继续；
- 但**不能**把它当成 7 天结论。

---

## 10. 记录模板

建议每天手动记录一次，保持最小观察表。

格式示例：

```text
Date: 2026-06-04
decision: route_c1_overlap_ready_for_orderbook_aware
liq_coverage_24h: 1.0
price_coverage_24h: 1.0
orderbook_coverage_24h: 1.0
BTC_overlap_h: 96.4
ETH_overlap_h: 96.3
SOL_overlap_h: 95.8
XRP_overlap_h: 95.9
DOGE_overlap_h: 96.0
next_action: continue_collect
```

今日参考记录：

```text
Date: 2026-06-05
decision: route_c1_overlap_ready_for_orderbook_aware
liq_coverage_24h: 1.0
price_coverage_24h: 1.0
orderbook_coverage_24h: 1.0
BTC_overlap_h: 117.1
ETH_overlap_h: 117.08
SOL_overlap_h: 116.55
XRP_overlap_h: 116.65
DOGE_overlap_h: 116.63
next_action: continue_collect
```

如果要更快查看，也可以直接用 `jq`：

```bash
jq '{
  decision,
  liquidation_1m_zero_fill_coverage_24h,
  price_1m_coverage_24h,
  orderbook_snapshot_coverage_24h,
  overlap_hours_by_symbol
}' /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/reports/route_c1/route_c1_data_overlap_audit_summary.json
```

---

## 11. 异常分支处理

### 情况 A：`liquidation_input_exists = false`

说明本地没有最新 liquidation 1m 文件，或者同步路径错了。

动作：

1. 重新同步 `data/route_c1_live/trend_regime_force_orders_raw.jsonl`
2. 在本地重跑第 5 节的 `aggregate_trend_regime_liquidations.py`
3. 不要恢复服务器端 `run_trend_liq_*` cron

### 情况 B：`price_input_exists = false`

说明 live 1m price 数据集没生成成功。

动作：

1. 重跑 `build_liquidation_shock_event_dataset.py`
2. 检查 `route_c1_live_price_build_summary.json`

### 情况 C：`orderbook_snapshot_coverage_24h < 0.80`

说明 orderbook 数据当日有明显缺口。

动作：

1. 检查服务器端 orderbook collector 日志
2. 检查本地同步是否完整
3. 检查最近一天文件是否存在且有持续增长

### 情况 D：某些币种 overlap 掉回 `0.0h`

优先判断：

1. 该 symbol 的本地 orderbook 新日期文件是否缺失
2. 该 symbol 的 live price 数据是否覆盖到最新 liquidation 时间窗
3. 是否误用了历史 proxy 价格集

---

## 12. 当前阶段禁止事项

当前阶段不要做：

- 不要继续调 `Route C1` 阈值
- 不要提前宣布 live filter 可用
- 不要把 `overlap ready` 当成 `7d live smoke` 已通过
- 不要在 `baseline_match_rate < 0.70` 时推进正式 `30d forward` 结论
- 不要因为某一天数据漂亮就重写结论
- 不要在服务器上恢复 `run_trend_liq_hourly.sh` 定时任务

---

## 13. 当前阶段的正确口径

当前正确表述应是：

> Route C1 的历史 `price-only proxy` 仍然是 promising；  
> live overlap 已经推进到 `route_c1_overlap_ready_for_orderbook_aware`；  
> 当前输入门槛已经满足；  
> 但 `7d live smoke` 仍为 `route_c1_baseline_match_failed`，不能推广为 live filter；
> 后续如需复核，应同步 raw 到本地后重新派生，不在服务器上定时全量聚合。

---

## 14. 一句话操作版

后续复核只做这五件事：

1. 同步 raw liquidation
2. 同步 orderbook
3. 本地派生 liquidation 1m/5m/hourly
4. 重建 live price 1m
5. 重跑 overlap audit 或 live smoke
