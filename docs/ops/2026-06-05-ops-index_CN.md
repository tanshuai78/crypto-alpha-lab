# Ops 入口索引

> 最后更新：2026-06-05

这份索引只保留一条主入口，避免在多份 `ops` 文档之间来回切换。

## 现在该用哪份

### Route C1 每日同步与 7d 跟踪

- 文件：[`2026-06-05-route-c1-daily-sync-and-7d-tracking_CN.md`](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/docs/ops/2026-06-05-route-c1-daily-sync-and-7d-tracking_CN.md)
- 用途：现在服务器在跑几天了，要把最新 liquidation / orderbook 同步回来，重建 live price，并检查 C1 overlap 与 `7d` 门槛时，先看这份。

### Route C Orderbook 周度同步与清理

- 文件：[`2026-06-05-route-c-orderbook-weekly-sync-cleanup_CN.md`](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/docs/ops/2026-06-05-route-c-orderbook-weekly-sync-cleanup_CN.md)
- 用途：服务器磁盘不扩容时，按 7 天周期做 orderbook 回拉、校验、清理。

### Trend / Liquidation Phase 1A

- 文件：[`2026-06-05-trend-liquidation-phase1a-server_CN.md`](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/docs/ops/2026-06-05-trend-liquidation-phase1a-server_CN.md)
- 用途：Trend / Liquidation Phase 1A 的服务器部署、采集、watchlist、验收与回放。

## 选择规则

1. 如果你现在要做 Route C1 的 live 数据同步和 overlap 检查，先打开 `2026-06-05-route-c1-daily-sync-and-7d-tracking_CN.md`。
2. 如果你现在是 orderbook 周度同步、归档和清理，打开 `2026-06-05-route-c-orderbook-weekly-sync-cleanup_CN.md`。
3. 如果你是在维护 Trend/Liquidation Phase 1A 的服务器采集链路，打开 `2026-06-05-trend-liquidation-phase1a-server_CN.md`。
