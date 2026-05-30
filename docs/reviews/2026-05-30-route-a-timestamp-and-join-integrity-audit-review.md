# Route A Timestamp and Join Integrity Audit Review

本审计报告针对 Route A (Binance WebSocket forceOrder 采集路径) 的时间戳对齐与 Replay Join 完整性进行审查。

> [!NOTE]
> 本次历史回放与完整性审计仅用于解决 Route A 历史推进能力（Historical-Advancement Capability）与底层数据格式阻塞诊断。它并不意味着 Route A 的数据或策略已达到实盘就绪（Live-Ready）或执行就绪（Execution-Ready）的状态。

---

## 1. Forensic Checklist (取证清单与排查结论)

在审计启动前，我们对存量的 `2024` 年脏数据残余进行了排查：

- **问题 1：存量 hourly 文件是当前代码生成的，还是历史残留的 Stale Artifact？**
  - **结论**：属于 Stale Artifact。当前 WebSocket 收集器代码（`scripts/collect_trend_regime_force_orders.py`）使用 `datetime.strftime("%Y-%m-%dT%H:00")` 生成整点字符串，不可能直接输出 `:20:00` 这样的分钟级不整点桶。
- **问题 2：存量 raw 文件是否已经包含非整点 bucket 毫秒值？**
  - **结论**：本地未发现 `trend_regime_force_orders_raw.jsonl`，而存量的 `trend_regime_liquidation_hourly.jsonl` 仅包含 1 行，且其时间戳为 `1716852000000` (即 2024-05-27 23:20:00 UTC)，这说明该文件是由早期调试或未对齐的代码生成并残留于服务器中的。
- **问题 3：provided_hour_bucket_ms 是否与 canonical event timestamp 一致？**
  - **结论**：不一致。存量数据的 `hour_bucket_ms` 对应为分钟级对齐（23:20:00），而非 UTC 小时对齐（23:00:00）。
- **问题 4：是否属于前期部署残留文件？**
  - **结论**：是的。该记录属于 2024 年的数据残余，与当前 2026 年的回放和采集窗口完全脱节。

---

## 2. Baseline Integrity Snapshot (基线完整性度量)

### Input Coverage & Alignment
- **Raw File Path**: `data/trend_regime_force_orders_raw.jsonl` (本地不存在 / 存量为空)
- **Hourly File Path**: `data/trend_regime_liquidation_hourly.jsonl`
- **Hourly Row Count**: 1
- **Non-Hour Aligned Hourly Buckets**: 1 (对应 `1716852000000`)
- **Min/Max Hourly Bucket (Legacy)**: 2024-05-27 23:20:00 UTC

### Replay Join Status (存量回放关联状态)
- **Liquidation Rows Joined Count**: 0 (因小时桶对齐不匹配，Join 无法关联)
- **Invalid Hourly Bucket Count**: 0
- **Liquidation Coverage Ratio**: 0.0%

---

## 3. Hardening & Verification Logic (代码加固与验证逻辑)

为彻底阻断由于格式或历史残留导致的脏数据风险，我们已实施如下加固：

1. **多源时间戳解析器**：优先解析 `event_time_ms`, `trade_time_ms`, `E`, `T`, `timestamp_ms`，仅在完全缺失时使用 `hour_bucket_ms` 作为 Fallback，对于无任何时间戳的无效数据直接丢弃并记录 `missing_timestamp_count`。
2. **小时桶强制取整**：在聚合器与 Replay Join 侧同时实施防御性整除取整（`// 3600000 * 3600000`），保证入库与 Join 键值必须是 UTC 小时整点。
3. **包装兼容设计**：保留 `aggregate_raw_to_hourly` 原有签名，新增 `aggregate_raw_to_hourly_with_audit` 支持输出 audit 诊断信息，不破坏已有 CLI 主入口及单元测试。

---

## 4. Fresh Regeneration & Server Reset Procedure (服务器复位验证程序)

为进一步在干净环境下验证 Route A 链路，定义以下复位步骤：

### 容器与备份指令
```bash
# 1. 停止策略与采集容器
docker stop trend-watchlist trend-forceorder

# 2. 确认容器已完全停止
docker ps --format '{{.Names}}' | rg 'trend-forceorder|trend-watchlist' && exit 1 || true

# 3. 进入工作目录并备份残留数据
cd /root/crypto-alpha-lab
ts=$(date +%Y%m%d_%H%M%S)
mkdir -p data/route_a_backups/$ts
cp -a data/trend_regime_liquidation_cache.json data/route_a_backups/$ts/ 2>/dev/null || true
cp -a data/trend_regime_force_orders_raw.jsonl data/route_a_backups/$ts/ 2>/dev/null || true
cp -a data/trend_regime_liquidation_hourly.jsonl data/route_a_backups/$ts/ 2>/dev/null || true
sha256sum data/route_a_backups/$ts/* > data/route_a_backups/$ts/SHA256SUMS 2>/dev/null || true

# 4. 禁用/移走旧残留文件，以防污染后续采集
[ -f data/trend_regime_liquidation_cache.json ] && mv data/trend_regime_liquidation_cache.json data/trend_regime_liquidation_cache.json.$ts.disabled
[ -f data/trend_regime_force_orders_raw.jsonl ] && mv data/trend_regime_force_orders_raw.jsonl data/trend_regime_force_orders_raw.jsonl.$ts.disabled
[ -f data/trend_regime_liquidation_hourly.jsonl ] && mv data/trend_regime_liquidation_hourly.jsonl data/trend_regime_liquidation_hourly.jsonl.$ts.disabled

# 5. 启动容器重新监听
docker start trend-forceorder trend-watchlist
```

### 实时抓取验证指令
当重新接收到实时强平数据时，运行如下命令检查生成格式：
```bash
# 检查新 raw 数据行数
wc -l /root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl

# 观察前 5 行格式与时间戳对齐情况
sed -n '1,5p' /root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl

# 运行加固后的聚合脚本生成 hourly 文件
PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime_force_orders_raw.jsonl \
  --output data/trend_regime_liquidation_hourly.jsonl

# 验证 hourly 输出是否完全整点对齐
tail -n 5 /root/crypto-alpha-lab/data/trend_regime_liquidation_hourly.jsonl
```

---

## 5. Decision & Next Steps (审计结论与后续决策)

- **Current State**: `route_a_old_artifact_only`
  - 当前 Route A 的 2024 残余数据已被确认为 Stale Artifact。代码层面已完成对时间戳的整点对齐加固与 Replay Join 防御。
- **Action Plan**:
  1. 将当前加固后的代码部署至测试环境。
  2. 执行上述 **Server Reset** 复位流程清除历史残留。
  3. 待新数据流入后，观察并确认没有 `2024` 残留及分钟级非整点对齐现象。
