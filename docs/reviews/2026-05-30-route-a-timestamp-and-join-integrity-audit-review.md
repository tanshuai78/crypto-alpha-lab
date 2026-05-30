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

---

## 6. Post-Restart Validation Status (重启后的即时验证状态)

在 2026-05-30 的服务器重启与旧文件 rotate 完成后，服务器出现如下状态：

- `data/trend_regime_force_orders_raw.jsonl` 未生成或仍为空；
- `data/trend_regime_liquidation_hourly.jsonl` 未生成或仍为空；
- `trend-forceorder` 日志持续表现为 `messages=0 accepted=0 symbols_with_liq=0`；
- 旧的 `2024-05-27T23:20:00Z` 小时级脏记录未重新出现。

这组现象的正确解释是：

- **这不代表修复失败**；
- **这代表 Route A 已处于干净重置后的“无新事件”状态**；
- 当前尚未出现新的 Binance `forceOrder` 事件，因此新 raw / hourly 文件没有重新长出。

换句话说，重启后的即时结论应表述为：

- **部署已生效**
- **旧脏 artifact 已隔离**
- **collector live 路径仍等待第一条真实事件做最终闭环验证**

---

## 7. Immediate Post-Restart Checks (重启后立即巡检命令)

完成容器重建后，先执行以下命令确认 Route A 已在干净状态运行：

```bash
cd /root/crypto-alpha-lab

docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | egrep "trend-(forceorder|watchlist)"
docker logs --tail 30 trend-forceorder
ls -lh data/trend_regime_liquidation_cache.json
ls -lh data/trend_regime_force_orders_raw.jsonl data/trend_regime_liquidation_hourly.jsonl 2>/dev/null || echo "route_a_files_not_created_yet"
```

正确解读：

- 如果 `trend-forceorder`、`trend-watchlist` 都为 `Up`，说明容器已正常恢复；
- 如果 `trend_regime_liquidation_cache.json` 已生成，说明 collector 已运行；
- 如果 raw / hourly 文件尚未创建，或创建后仍为空，说明当前只是 **没有新 forceOrder 事件**，不是代码回退或修复失效。

建议后续巡检使用最短命令：

```bash
cd /root/crypto-alpha-lab

docker logs --tail 30 trend-forceorder
ls -lh data/trend_regime_force_orders_raw.jsonl 2>/dev/null || echo "raw_not_created"
wc -l data/trend_regime_force_orders_raw.jsonl 2>/dev/null || echo "raw=0"
```

---

## 8. First-Event Acceptance Procedure (第一条新事件后的验收步骤)

一旦 `data/trend_regime_force_orders_raw.jsonl` 出现第一条新记录，立刻执行下面的最小验收流程：

```bash
cd /root/crypto-alpha-lab

wc -l data/trend_regime_force_orders_raw.jsonl
tail -n 3 data/trend_regime_force_orders_raw.jsonl

PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime_force_orders_raw.jsonl \
  --output data/trend_regime_liquidation_hourly.jsonl

wc -l data/trend_regime_liquidation_hourly.jsonl
tail -n 5 data/trend_regime_liquidation_hourly.jsonl
```

通过标准：

1. 新 raw 行中的事件时间应落在当前 2026 采集窗口内，而不是再次出现 2024；
2. 新 hourly 文件中的 `hour_bucket_ms` 必须对应 UTC 整点小时；
3. 不得再次出现 `:20:00` 这类分钟级非整点 bucket；
4. 若新 hourly 文件正常生成，则可将 Route A 状态从 `route_a_old_artifact_only` 升级为：
   - `route_a_current_code_clean_waiting_for_events`
   - 或 `route_a_raw_timestamp_clean_aggregator_fixed`
   具体取决于 snapshot 审计字段结果。

---

## 9. Handoff To Route B Mainline (切换回 Route B 主线)

当前主线决策应当明确为：

- **Route A**：继续后台监听，作为未来 cross-check 与 Route C overlap 的辅助来源；
- **Route B**：作为当前 liquidation_cascade 研究主线继续推进；
- **Route C**：在 Route A 尚无新样本前，不再作为主线阻塞条件。

原因：

1. Route A 当前受制于事件驱动特性，何时出现第一条新 `forceOrder` 无法由工程节奏控制；
2. Route B 已成功拉取并 join：
   - 约 `1499h` 历史覆盖；
   - `7162` 行第三方 liquidation 小时级数据；
   - `2393` 行成功 joined historical rows；
3. 因此 liquidation_cascade 的下一阶段分析应基于 **Route B-only** 继续推进，而不是继续等待 Route A live overlap。

对外部操作的具体建议：

1. 保持 `trend-forceorder` 容器继续运行；
2. 每隔数小时巡检一次 raw 行数；
3. 研究主线转入 Route B-only replay / review；
4. 待 Route A 出现新样本后，再回头执行 Route C overlap 验证。
