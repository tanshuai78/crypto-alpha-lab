# Route C Orderbook 每 7 天同步与服务器清理操作手册

> 最后更新：2026-06-05

> 入口文档：`docs/ops/2026-06-05-ops-index_CN.md`

**适用场景：** 不扩容轻量服务器硬盘，服务器只保存短期 orderbook 缓存，本地 Mac 保存长期研究归档。

**服务器：** `root@47.82.4.85`

**服务器数据目录：** `/root/my-bitcoin-project/data/historical_orderbook`

**本地长期归档目录：** `/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook_server_archive`

---

## 1. 当前容量判断

当前服务器状态：

```text
/dev/vda3 30G total, 17G used, 12G free
my-bitcoin-project/data/historical_orderbook: 19M
crypto-alpha-lab/data: 21M
Docker build cache: about 10G
```

旧 orderbook 历史经验数据约：

```text
36G / 74 days ~= 486MB/day
```

如果直接在服务器保存 90 天原始 JSONL：

```text
486MB/day * 90 ~= 44GB
```

因此 30G 轻量服务器不适合保存 90 天原始 orderbook。正确方式是：

- 服务器保留短窗口；
- 每 7 天同步到本地；
- 本地校验成功后删除服务器旧文件；
- 本地归档作为 Route C 长期研究数据源。

---

## 2. Retention 策略

不扩盘模式下，服务器 retention 不建议设为 90 天。

推荐：

```text
COLLECTOR_DATA_RETENTION_DAYS = 14
```

原因：

- 服务器只有约 12G 可用空间；
- 14 天足够覆盖每周同步失败后的缓冲；
- 90 天会让服务器在无人干预时大概率写满磁盘；
- 长期 90 天目标由本地 archive 实现，不由服务器保存。

服务器检查命令：

```bash
cd /root/my-bitcoin-project
grep -n 'COLLECTOR_DATA_RETENTION_DAYS' src/config.py
```

如果不是 14，可改回 14：

```bash
cd /root/my-bitcoin-project
cp src/config.py src/config.py.bak.$(date +%Y%m%d_%H%M%S)
perl -0pi -e 's/COLLECTOR_DATA_RETENTION_DAYS\s*=\s*\d+/COLLECTOR_DATA_RETENTION_DAYS = 14/' src/config.py
grep -n 'COLLECTOR_DATA_RETENTION_DAYS' src/config.py
docker restart my-collector
docker logs --tail 50 my-collector
```

如果想继续使用 `sed`，必须使用扩展正则：

```bash
sed -i -E 's/COLLECTOR_DATA_RETENTION_DAYS = [0-9]+/COLLECTOR_DATA_RETENTION_DAYS = 14/' src/config.py
```

注意：当前 Dockerfile 使用 `COPY . .`，容器内代码来自镜像，不是宿主机代码挂载。修改宿主机 `src/config.py` 后，仅 `docker restart my-collector` 不会让容器读取新配置。需要重新构建镜像并重建容器，见下方命令。

```bash
docker stop my-collector
docker rm my-collector
docker build -t crypto-collector .
docker run -d \
  --name my-collector \
  --restart always \
  -v /root/my-bitcoin-project/data:/app/data \
  crypto-collector
docker exec my-collector grep -n 'COLLECTOR_DATA_RETENTION_DAYS' /app/src/config.py
```

---

## 3. 每周同步总流程

每 7 天执行一次：

1. 服务器压缩非当天旧文件。
2. 服务器生成待同步文件清单。
3. 服务器生成 SHA256 校验文件。
4. 本地拉取文件清单、校验文件和数据文件。
5. 本地校验 SHA256。
6. 校验通过后，服务器删除已同步旧文件。
7. 服务器检查磁盘和 collector 健康。

安全原则：

- 不删除当天正在写入的文件；
- 不删除没有进入清单的文件；
- 不在校验前删除服务器数据；
- 不执行 `rm *.jsonl` 这种宽泛删除命令。

---

## 4. 服务器端：准备同步批次

在服务器执行：

```bash
ssh root@47.82.4.85
```

然后运行：

```bash
set -euo pipefail

REMOTE_DIR=/root/my-bitcoin-project/data/historical_orderbook
MANIFEST_DIR=/root/orderbook_archive_manifests
RUN_ID=$(date +%Y%m%d_%H%M%S)

mkdir -p "$MANIFEST_DIR"
cd "$REMOTE_DIR"

echo "[1/5] disk before"
df -h /
du -sh "$REMOTE_DIR"

echo "[2/5] compress files older than 1 day"
find . -type f -name '*.jsonl' -mtime +1 -print0 | xargs -0 -r gzip -9

echo "[3/5] build sync file list"
find . -type f \( -name '*.jsonl.gz' -o -name '*.jsonl' \) -mtime +1 | sort \
  > "$MANIFEST_DIR/sync_files_${RUN_ID}.txt"

echo "[4/5] build sha256 manifest"
cd "$REMOTE_DIR"
while IFS= read -r f; do
  sha256sum "$f"
done < "$MANIFEST_DIR/sync_files_${RUN_ID}.txt" \
  > "$MANIFEST_DIR/sha256_${RUN_ID}.txt"

echo "[5/5] summary"
echo "RUN_ID=$RUN_ID"
wc -l "$MANIFEST_DIR/sync_files_${RUN_ID}.txt"
du -ch $(cat "$MANIFEST_DIR/sync_files_${RUN_ID}.txt") 2>/dev/null | tail -1 || true
echo "manifest: $MANIFEST_DIR/sha256_${RUN_ID}.txt"
```

把输出里的 `RUN_ID=...` 复制下来，后续本地命令要用。

示例：

```text
RUN_ID=20260609_080000
```

---

## 5. 本地 Mac：拉取归档文件

在本地 Mac 执行。

先设置变量。把 `RUN_ID` 替换成服务器上一步输出的值：

```bash
SERVER=root@47.82.4.85
RUN_ID=20260609_080000
REMOTE_DIR=/root/my-bitcoin-project/data/historical_orderbook
REMOTE_MANIFEST_DIR=/root/orderbook_archive_manifests
LOCAL_ROOT=/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook_server_archive

mkdir -p "$LOCAL_ROOT/manifests"
```

拉取清单和校验文件：

```bash
scp "$SERVER:$REMOTE_MANIFEST_DIR/sync_files_${RUN_ID}.txt" "$LOCAL_ROOT/manifests/"
scp "$SERVER:$REMOTE_MANIFEST_DIR/sha256_${RUN_ID}.txt" "$LOCAL_ROOT/manifests/"
```

按清单拉取数据文件：

```bash
rsync -avzP \
  --files-from="$LOCAL_ROOT/manifests/sync_files_${RUN_ID}.txt" \
  "$SERVER:$REMOTE_DIR/" \
  "$LOCAL_ROOT/"
```

---

## 6. 本地 Mac：校验归档完整性

在本地 Mac 执行：

```bash
cd /Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook_server_archive

shasum -a 256 -c "manifests/sha256_${RUN_ID}.txt"
```

如果全部通过，会看到大量：

```text
... OK
```

如果出现失败：

```text
FAILED
```

不要删除服务器数据。重新执行 rsync：

```bash
rsync -avzP \
  --files-from="$LOCAL_ROOT/manifests/sync_files_${RUN_ID}.txt" \
  "$SERVER:$REMOTE_DIR/" \
  "$LOCAL_ROOT/"
```

然后再次校验。

---

## 7. 服务器端：校验通过后删除已同步文件

只有在本地 `shasum -a 256 -c` 全部 OK 后，才执行本步骤。

在服务器执行：

```bash
ssh root@47.82.4.85
```

设置同一个 `RUN_ID`：

```bash
set -euo pipefail

RUN_ID=20260609_080000
REMOTE_DIR=/root/my-bitcoin-project/data/historical_orderbook
MANIFEST_DIR=/root/orderbook_archive_manifests

cd "$REMOTE_DIR"

echo "[delete] files listed in $MANIFEST_DIR/sync_files_${RUN_ID}.txt"
while IFS= read -r f; do
  rm -f "$f"
done < "$MANIFEST_DIR/sync_files_${RUN_ID}.txt"

echo "[disk after]"
df -h /
du -sh "$REMOTE_DIR"
```

注意：

- 这里只删除清单里的文件；
- 清单只包含 `mtime +1` 的旧文件；
- 当天正在写入的文件不会进入清单。

---

## 8. 每周同步后健康检查

服务器执行：

```bash
cd /root/my-bitcoin-project
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Size}}'
docker logs --tail 50 my-collector
docker exec my-collector python src/data_collector/data_monitor.py --days 1
df -h /
du -sh /root/my-bitcoin-project/data/historical_orderbook
```

Route C 还需要确认 liquidation collector 也在跑：

```bash
cd /root/crypto-alpha-lab
docker ps -a | grep -E 'trend-forceorder|trend-watchlist|trend-rows'
docker logs --tail 30 trend-forceorder
PYTHONPATH=. python3 scripts/check_liquidation_collector_health.py \
  --data-dir data \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT
```

---

## 9. Docker 空间清理

当前服务器 Docker build cache 较大，可以定期安全清理 build cache。

服务器执行：

```bash
docker builder prune -f
docker image prune -f
docker system df
df -h /
```

不要执行：

```bash
docker system prune -a
```

原因：

- `-a` 可能删除后续重启需要的镜像；
- 对当前 5 个容器的运行环境不够保守；
- 研究服务器优先稳定，不追求极限清理。

---

## 10. 每周最短版命令索引

### 服务器准备

```bash
ssh root@47.82.4.85
set -euo pipefail
REMOTE_DIR=/root/my-bitcoin-project/data/historical_orderbook
MANIFEST_DIR=/root/orderbook_archive_manifests
RUN_ID=$(date +%Y%m%d_%H%M%S)
mkdir -p "$MANIFEST_DIR"
cd "$REMOTE_DIR"
find . -type f -name '*.jsonl' -mtime +1 -print0 | xargs -0 -r gzip -9
find . -type f \( -name '*.jsonl.gz' -o -name '*.jsonl' \) -mtime +1 | sort > "$MANIFEST_DIR/sync_files_${RUN_ID}.txt"
while IFS= read -r f; do sha256sum "$f"; done < "$MANIFEST_DIR/sync_files_${RUN_ID}.txt" > "$MANIFEST_DIR/sha256_${RUN_ID}.txt"
echo "RUN_ID=$RUN_ID"
```

### 本地拉取和校验

```bash
SERVER=root@47.82.4.85
RUN_ID=替换成服务器输出
REMOTE_DIR=/root/my-bitcoin-project/data/historical_orderbook
REMOTE_MANIFEST_DIR=/root/orderbook_archive_manifests
LOCAL_ROOT=/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook_server_archive
mkdir -p "$LOCAL_ROOT/manifests"
scp "$SERVER:$REMOTE_MANIFEST_DIR/sync_files_${RUN_ID}.txt" "$LOCAL_ROOT/manifests/"
scp "$SERVER:$REMOTE_MANIFEST_DIR/sha256_${RUN_ID}.txt" "$LOCAL_ROOT/manifests/"
rsync -avzP --files-from="$LOCAL_ROOT/manifests/sync_files_${RUN_ID}.txt" "$SERVER:$REMOTE_DIR/" "$LOCAL_ROOT/"
cd "$LOCAL_ROOT"
shasum -a 256 -c "manifests/sha256_${RUN_ID}.txt"
```

### 服务器删除已同步文件

```bash
ssh root@47.82.4.85
set -euo pipefail
RUN_ID=替换成同一个_RUN_ID
REMOTE_DIR=/root/my-bitcoin-project/data/historical_orderbook
MANIFEST_DIR=/root/orderbook_archive_manifests
cd "$REMOTE_DIR"
while IFS= read -r f; do rm -f "$f"; done < "$MANIFEST_DIR/sync_files_${RUN_ID}.txt"
df -h /
du -sh "$REMOTE_DIR"
```

---

## 11. Route C 数据口径提醒

这个流程只解决 orderbook 长期归档。

Route C C1 仍然需要同时保留：

- `/root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl`
- `/root/crypto-alpha-lab/data/trend_regime_liquidation_1m.jsonl`
- `/root/crypto-alpha-lab/data/trend_regime_liquidation_5m.jsonl`
- `/root/my-bitcoin-project/data/historical_orderbook/*.jsonl` 或 `.jsonl.gz`

第一版 Route C 不急着增加更多数据源。

优先保证：

- liquidation collector 连续；
- orderbook collector 连续；
- 两者有至少 7 天时间重叠；
- 本地 archive 可校验、可复现。

---

## 12. Route C1 Price-Only Precheck 决策路径

### 12.1 阶段定义

| 阶段 | 触发条件 | 执行脚本 | 决策标签 |
|---|---|---|---|
| **Proxy Snapshot（已完成）** | Binance Vision 历史快照下载后 | `review_route_c1_price_only.py --run-mode proxy_snapshot` | `proxy_promising_wait_for_live_overlap` |
| **Live Smoke 7d** | live liquidation 连续采集满 7 天后 | `review_route_c1_price_only.py --run-mode live_smoke_7d` | `live_smoke_promising_continue_to_30d` |
| **Forward 30d** | live liquidation 连续采集满 30 天后 | `review_route_c1_price_only.py --run-mode forward_30d` | `forward_provisional_pass` 或 `forward_failed_stop_route_c` |

当前状态：**Proxy Snapshot 已通过**（`proxy_promising_wait_for_live_overlap`），等待 7 天 live overlap。

### 12.2 Live Smoke 7d 触发条件检查

在 7 天 live liquidation 数据积累后，先运行 overlap 审计确认数据可用：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/audit_route_c1_data_overlap.py \
  --liquidation-dir data \
  --kline-dir data/binance_liquidation_snapshot/extracted/klines \
  --symbols BTCUSDT ETHUSDT SOLUSDT \
  --output reports/route_c1/route_c1_data_overlap_audit_live_smoke.json
cat reports/route_c1/route_c1_data_overlap_audit_live_smoke.json | python3 -m json.tool | grep -E 'decision|overlap_hours|primary_blocker'
```

决策规则：
- `overlap_hours >= 168` → 可进行 live smoke 审计
- `overlap_hours < 168` 或 `primary_blocker: missing_*` → 继续等待，不运行 live smoke

### 12.3 Live Smoke 7d 运行命令

overlap 审计确认可用后执行：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
mkdir -p reports/route_c1

# live smoke 直接读取已合并好的 1m price/liquidation 数据集
PYTHONPATH=src uv run python scripts/review_route_c1_price_only.py \
  --run-mode live_smoke_7d \
  --dataset data/route_c1_live/route_c1_live_price_1m_dataset.jsonl \
  --symbols BTCUSDT ETHUSDT SOLUSDT \
  --output reports/route_c1/route_c1_live_smoke_7d_summary.json \
  --review-output docs/reviews/$(date +%Y-%m-%d)-route-c1-live-smoke-7d-review.md
```

### 12.4 Live Smoke 7d 决策门槛

读取 JSON 结果：

```bash
python3 -c "
import json
with open('reports/route_c1/route_c1_live_smoke_7d_summary.json') as f:
    s = json.load(f)
print('decision:', s['decision'])
print('proxy_kill_switch_weak:', s['proxy_kill_switch_weak'])
print('vol_ratio:', s['post_event_vol_ratio_median'])
print('range_ratio:', s['post_event_range_ratio_median'])
print('excursion_p90_ratio:', s['post_event_abs_excursion_p90_ratio'])
print('matched_events:', s['matched_event_count'])
print('baseline_match_rate:', s['baseline_match_rate'])
"
```

| 决策标签 | 含义 | 下一步 |
|---|---|---|
| `live_smoke_promising_continue_to_30d` | live smoke 通过 | 继续采集至 30 天，再运行 forward_30d |
| `price_risk_not_confirmed` | 任一 ratio gate 未过 | 停止等待，分析具体弱项 |
| `baseline_match_failed` | match_rate < 0.70 | 检查 live liq 数据质量 |
| `data_unavailable` | 事件数为 0 | 检查 liquidation collector 是否正常 |

补充说明：

- `Price Risk Ratios` 才是这条路线的核心信号强度指标，`baseline_match_rate` 是对照覆盖质量指标，不是信号强弱本身。
- 这次 `baseline_match_rate = 0.589` 说明有一部分事件没有找到足够像的对照窗口，但不代表价格风险信号弱；相反，这次三个 ratio 都已经过了各自门槛。
- 最低成本的提升方式不是先放宽正式门槛，而是继续积累更长、更分散的 live 数据，让样本在 `month/day` 维度更均衡。
- 这里的 baseline 不是“另一个 liquidation 事件”，而是“相似但未被 liquidation 污染的正常对照窗口”，用于估计事件发生前后的反事实波动水平。

### 12.4.1 Candidate Alpha 最短验收表

| 阶段 | 必须满足 | 通过标准 | 不通过时怎么做 |
|---|---|---|---|
| 1. 研究成立 | `Price Risk Ratios` 过线，`baseline_match_rate >= 0.70`，样本不过度集中 | 事件后强度和对照覆盖都稳定 | 继续采集 live 数据，不改正式门槛 |
| 2. 独立复核 | 换一段独立 live 窗口或不同 regime 再跑一次 | 方向不反转，强度不明显退化 | 暂停推广，先查样本结构 |
| 3. 成本后为正 | 显式扣掉手续费、滑点、盘口深度和延迟 | 预期净收益仍为正 | 先别谈 alpha，继续优化执行或放弃 |
| 4. 执行可落地 | shadow / paper 跑完整周期，不能频繁卡腿或拒单 | 下单、撤单、重试路径稳定 | 修执行，不进实盘 |
| 5. 风控闭环 | 仓位上限、单腿暴露时间、熔断条件都明确 | 先有风控，再谈收益 | 不进实盘 |
| 6. 小资金试运行 | 上面都过，再做小资金试跑 | 运行稳定、无静默失败 | 回退到 shadow / paper |

结论：这条 liquidation 线已经进入 candidate alpha 观察区，但还没到“可考虑实盘”的阶段。当前最短板仍然是对照覆盖率，而不是价格风险强度。

**如果 proxy_kill_switch_weak = True 且 7d live smoke 也弱** → 停止 Route C1，不进入 30 天阶段。

### 12.5 Forward 30d 运行命令

live smoke 7d 通过后，等待满 30 天运行：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/review_route_c1_price_only.py \
  --run-mode forward_30d \
  --dataset data/trend_regime_liquidation_1m.jsonl \
  --symbols BTCUSDT ETHUSDT SOLUSDT \
  --output reports/route_c1/route_c1_forward_30d_summary.json \
  --review-output docs/reviews/$(date +%Y-%m-%d)-route-c1-forward-30d-review.md
```

| 决策标签 | 含义 |
|---|---|
| `forward_provisional_pass` | 所有 30d 门槛通过，进入执行设计阶段 |
| `forward_failed_stop_route_c` | 任一 30d 门槛未过，停止 Route C |

### 12.6 快速状态检查

任何时候检查 live liquidation collector 状态：

```bash
# 服务器端
ssh root@iZt4nd2xclaurycevfhphnZ
docker ps -a | grep forceorder
docker logs --tail 30 trend-forceorder
wc -l /root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl 2>/dev/null || echo "raw=0"
wc -l /root/crypto-alpha-lab/data/trend_regime_liquidation_1m.jsonl 2>/dev/null || echo "1m=0"
```

本地查看最新 proxy 审计结果：

```bash
cat /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/reports/route_c1/route_c1_price_only_proxy_summary.json \
  | python3 -m json.tool \
  | grep -E 'decision|vol_ratio|range_ratio|excursion|event_count|match_rate'
```
