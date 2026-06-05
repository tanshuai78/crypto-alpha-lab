# Route C1 每日同步与 7d Overlap 跟踪清单

> 最后更新：2026-06-05

> 入口文档：`docs/ops/2026-06-05-ops-index_CN.md`

**适用场景：** Route C1 已经达到 `route_c1_overlap_ready_for_orderbook_aware`，但 live overlap 只有约 `72h`，还没有达到 `7d / 168h` 的 live smoke 启动门槛。

**当前状态定义：**

```text
input ready, time not ready
```

也就是说：

- liquidation 1m 输入已就绪；
- live 1m price 输入已就绪；
- orderbook-aware 输入门槛已就绪；
- 但 overlap 时间长度还不足以做正式 `7d live smoke`。

---

## 1. 当前目标

这份清单只做一件事：

> 每天把服务器上的最新 liquidation / orderbook 同步回本地，重建 live price 数据，重跑 overlap audit，并判断是否已经接近或达到 `168h` 的启动门槛。

当前阶段**不做**：

- 不调 Route C1 阈值；
- 不改 proxy 结论；
- 不提前运行 `30d forward`；
- 不因为输入 ready 就宣布 live filter 可用。

---

## 2. 每日执行顺序

每天按下面顺序执行：

1. 从服务器同步 liquidation 文件到 `data/route_c1_live/`
2. 从服务器同步 orderbook 文件到 `my-bitcoin-project/data/historical_orderbook/`
3. 基于最新 liquidation 1m 重建 live 1m price 数据集
4. 重跑 overlap audit
5. 记录关键字段
6. 判断是否达到 `7d / 168h` 门槛

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

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
mkdir -p data/route_c1_live reports/route_c1

rsync -avzP $SERVER:/root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl ./data/route_c1_live/
rsync -avzP $SERVER:/root/crypto-alpha-lab/data/trend_regime_liquidation_1m.jsonl ./data/route_c1_live/
rsync -avzP $SERVER:/root/crypto-alpha-lab/data/trend_regime_liquidation_5m.jsonl ./data/route_c1_live/
rsync -avzP $SERVER:/root/crypto-alpha-lab/data/trend_regime_liquidation_hourly.jsonl ./data/route_c1_live/
rsync -avzP $SERVER:/root/crypto-alpha-lab/data/trend_regime_liquidation_health.json ./data/route_c1_live/
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

## 5. 重建 live 1m price 数据集

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

## 6. 重跑 overlap audit

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

## 7. 每天要看哪些字段

每天只重点看这几个字段：

### 7.1 输入存在性

必须都为 `true`：

- `liquidation_input_exists`
- `price_input_exists`
- `orderbook_dir_exists`

### 7.2 覆盖质量

理想目标：

- `liquidation_1m_zero_fill_coverage_24h = 1.0`
- `price_1m_coverage_24h >= 0.95`
- `orderbook_snapshot_coverage_24h >= 0.80`

当前目标是尽量接近：

```text
1.0 / 1.0 / 1.0
```

### 7.3 关键状态字段

- `ready_for_price_only`
- `ready_for_orderbook_aware`
- `decision`

当前理想值：

```text
ready_for_price_only = true
ready_for_orderbook_aware = true
decision = route_c1_overlap_ready_for_orderbook_aware
```

### 7.4 核心进度字段

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

## 8. 何时可以进入 7d Live Smoke

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

## 9. 每日记录模板

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

## 10. 异常分支处理

### 情况 A：`liquidation_input_exists = false`

说明本地没有最新 liquidation 1m 文件，或者同步路径错了。

动作：

1. 重新同步 `data/route_c1_live/trend_regime_liquidation_1m.jsonl`
2. 如果服务器没有该文件，就先同步 raw，再重新聚合

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

## 11. 当前阶段禁止事项

当前阶段不要做：

- 不要继续调 `Route C1` 阈值
- 不要提前宣布 live filter 可用
- 不要把 `~72h overlap` 当成 `7d live smoke` 已完成
- 不要跳过 `7d` 直接推进 `30d forward`
- 不要因为某一天数据漂亮就重写结论

---

## 12. 当前阶段的正确口径

当前正确表述应是：

> Route C1 的历史 `price-only proxy` 仍然是 promising；  
> live overlap 已经推进到 `route_c1_overlap_ready_for_orderbook_aware`；  
> 当前输入门槛已经满足；  
> 但时间长度仍不足以做 7d 结论，下一步应继续累计 overlap，直到 `BTC/ETH/SOL` 接近 `168h`。

---

## 13. 一句话操作版

每天只做这四件事：

1. 同步 liquidation
2. 同步 orderbook
3. 重建 live price 1m
4. 重跑 overlap audit，看 `BTC/ETH/SOL` 是否接近 `168h`
