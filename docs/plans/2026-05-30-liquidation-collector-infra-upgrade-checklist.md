# Liquidation Collector Infra Upgrade Checklist

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this checklist task-by-task.

**Goal:** 在部署到服务器之前，把 liquidation 采集链路升级成“原始事件归档优先、研究可用、可恢复”的长期研究基础设施，确保后续可以稳定沉淀 raw event，并可靠派生 `1m / 5m / 1h` 聚合数据。

**Architecture:** 保留现有 `trend-forceorder` WebSocket 采集器，但重新明确数据分层：`raw event JSONL` 是主事实源，滚动 `cache.json` 仅用于旧 watchlist 兼容；新增 schema contract、dedup、zero-fill、健康检查与定期派生能力，形成可长期运行、可复核、可重放的数据基础设施。

**Tech Stack:** Python 3.11, pytest, JSONL, Docker, Binance forceOrder WebSocket, standalone scripts, cron-based aggregation.

---

## Boundary

这份清单只处理 **采集基础设施升级**，不处理：

- 新策略研究
- `liquidation_shock_event_study` Phase 2
- Route B vendor 替换
- execution / cost simulation

目标是先把服务器端数据链路建成一个长期可用、足够支撑 future event study 的事实源。

---

## Must-Have Outcomes

完成部署前，代码必须满足这 8 个最小结果：

1. `trend_regime_force_orders_raw.jsonl` 被明确为主事实源，且 raw schema 固化
2. raw event 具有稳定 `event_id`，聚合层可去重
3. 原始事件可稳定派生成 `1m / 5m / 1h` 聚合文件
4. `1m / 5m` 聚合支持 zero-fill，避免研究分布失真
5. 旧 `trend_regime_liquidation_cache.json` 继续保留，避免打断现有 watchlist
6. 健康检查能输出 archive integrity + `research_ready_1m_24h`
7. 运维文档写清楚 cron 派生、rotate、checksum、24h acceptance
8. 服务器部署后不是“容器在跑”，而是数据质量达标

---

## Checklist

### 1. 固化 raw event contract

**必须完成**
- 在 `scripts/collect_trend_regime_force_orders.py` 中明确 raw event schema
- 至少包含：
  - `schema_version`
  - `source`
  - `event_id`
  - `symbol`
  - `exchange_symbol`
  - `event_time_ms`
  - `trade_time_ms`
  - `side`
  - `liquidated_position_side`
  - `liquidation_side`
  - `price`
  - `quantity`
  - `notional_usdt`
  - `raw_payload`
- 明确：`--raw-output` 是主事实源，`--output` 只是旧链路兼容 cache

**验收标准**
- 新成员只看脚本和测试，就知道 raw 每一行的研究语义

---

### 2. raw writer 可恢复、可持久

**必须完成**
- raw 写入必须 append-only
- 每条事件一行 JSON
- 写入后 `flush()`
- 支持 `--fsync-raw`
- 支持 `--raw-schema-version`

**验收标准**
- 容器重启后不会因为 writer 语义模糊破坏 archive 连续性

---

### 3. 扩展聚合脚本支持多粒度 + dedup

**必须完成**
- 扩展 `aggregate_trend_regime_liquidations.py`
- 至少支持：
  - `1m`
  - `5m`
  - `1h`
- `bucket` 参数必须防御性校验，不允许非法粒度静默通过
- 聚合器必须：
  - 以 canonical event timestamp 重算 bucket
  - fallback legacy bucket 时计数
  - 按 `event_id` 去重
- 输出 schema 明确区分：
  - `1m/5m` 用 `bar_start_ms`
  - `1h` 保留 legacy `hour_bucket_ms`

**验收标准**
- 同一份 raw 能稳定生成：
  - `data/trend_regime_liquidation_1m.jsonl`
  - `data/trend_regime_liquidation_5m.jsonl`
  - `data/trend_regime_liquidation_hourly.jsonl`
- 旧 `1h` 产物不回归

---

### 4. 研究用聚合支持 zero-fill

**必须完成**
- `1m / 5m` 聚合支持：
  - `--fill-empty-buckets`
  - `--start-ms`
  - `--end-ms`
  - `--symbols`
- 空桶应明确输出为 0，而不是缺失

**验收标准**
- 后续 24h anomaly distribution 可以基于真实的 zero-filled 1m 序列计算

---

### 5. 保持旧 watchlist 兼容，不破坏现有主线

**必须完成**
- 不修改 `trend-watchlist` 对 `trend_regime_liquidation_cache.json` 的读取契约
- 不让这次升级影响：
  - `run_trend_regime_watchlist.py`
  - 当前 Route B-only 主线

**验收标准**
- watchlist 继续可运行
- cache 文件继续按旧格式落盘

---

### 6. 增加健康检查脚本

**必须完成**
- 新增 / 扩展健康检查脚本，至少输出：
  - raw 行数
  - raw 最新事件时间
  - raw invalid JSON line count
  - raw duplicate event count
  - raw 最近 1h / 24h 事件数
  - `1m / 5m / 1h` 文件存在性、行数、最新 bucket
  - `aggregate_1m_coverage_ratio_24h`
  - `aggregate_1m_max_gap_minutes_24h`
  - `research_ready_1m_24h`

**验收标准**
- 一条命令能回答：当前 collector 是否足够支撑 future 1m shock event study

---

### 7. 明确定期派生机制

**必须完成**
- 运维文档中明确实际运行方式：
  - cron 派生 `1m / 5m / 1h`
- 明确 active raw file、backup dir、checksum 和 rotate 规则
- 补充 1m 文件体积 / IOPS 风险提示

**验收标准**
- 多粒度聚合不是“手工脚本能力”，而是有实际运行方式的基础设施

---

### 8. 24h 部署后验收标准

**必须完成**
- 文档里写清楚 24h acceptance gate
- 至少检查：
  - `raw_invalid_json_line_count == 0`
  - `raw_duplicate_event_count` 在可接受范围内
  - `aggregate_1m_exists == true`
  - `aggregate_1m_coverage_ratio_24h >= 0.99`
  - `aggregate_1m_max_gap_minutes_24h <= 1`
  - `watchlist_cache_updated == true`
  - `research_ready_1m_24h == true`

**验收标准**
- 不再以“容器 Up”作为成功定义

---

## Deployment Sequence After Code Is Ready

代码改造完成后，服务器部署顺序必须是：

1. 同步代码到服务器
2. 重建 `crypto-alpha-lab:latest` 镜像
3. 停止 `trend-forceorder` / `trend-watchlist`
4. 备份并 rotate 旧 raw / cache / aggregate 文件，同时生成 checksum
5. 删除旧容器
6. 启动新容器
7. 安装 cron 聚合任务
8. 运行健康检查脚本
9. 确认 raw 开始在干净状态下积累
10. 等待 24h acceptance gate

---

## Done Definition

只有在下面条件全部满足后，才允许进入服务器部署：

- raw schema 固化
- raw writer append-only / flush / optional fsync 到位
- `event_id` 存在且聚合可去重
- 聚合支持 `1m / 5m / 1h`
- `1m / 5m` 支持 zero-fill
- watchlist 兼容不破坏
- 健康检查可输出 `research_ready_1m_24h`
- cron / rotate / checksum 文档已更新
- 关键测试通过

如果这些条件未满足，就不要先去 rotate 文件和重启容器。
