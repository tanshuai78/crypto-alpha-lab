# 极端资金费监控列表服务器运行指南 (Extreme Funding Watchlist Server Operation)

## 目的 (Purpose)

以**仅观察模式 (observation-only mode)** 运行 Phase 1A.5 监控程序。该守护进程 (daemon) 仅读取币安 (Binance) 公开接口，输出监控事件、心跳日志、拒绝统计以及 JSONL 格式的运行证据。程序**严禁**读取私钥、查询账户余额或读取任何交易执行状态。

---

## 专业术语与专用名称释义 (Terminology Glossary)

为了确保人机协同及后续 AI 代理 (AI agents) 的高精度理解，以下是文档中出现的关键英文术语及其中文释义：

1. **Watchlist (监控列表 / 观察列表)**：策略筛选出的、符合特定高资金费率特征的币种监控列表。
2. **Daemon (守护进程)**：在系统后台持续运行、无人值守的后台程序。
3. **Dry Run (空转测试 / 试运行)**：不涉及真实资金和实际执行的运行测试，用于验证数据流是否畅通。
4. **One-Shot (单次运行)**：程序启动后只执行一次循环（单次数据采集与扫描）便自动退出的运行模式。
5. **Bounded (有界/有限循环)**：程序只执行指定次数的轮询循环便退出的运行模式。
6. **Open Interest, OI (未平仓量 / 持仓量)**：衍生品市场中所有未平仓（未结算或未平仓）合约的总数量，用于评估市场流动性和资金热度。
7. **Lineage (数据血统 / 数据溯源)**：记录数据的来源、定义和计算口径（例如：区分预估费率与已结算费率，标明数据来自哪个特定接口）。
8. **Premium Index (溢价指数)**：反映合约价格相较于现货价格溢价程度的指标，用于计算资金费率。
9. **systemd (系统服务管理器)**：Linux 操作系统中用于管理和控制系统服务（Daemon）的标准工具。
10. **SignalCandidate (信号候选对象)**：策略层生成、包装策略信号的内部数据对象。
11. **TradeIntent (交易意图对象)**：执行层消费、包含下单所需所有风控与参数的执行实体对象。
12. **Warm-up guard / persistence warm-up (预热保护)**：程序启动前 5 分钟的保护门控，用于积累足够的滚动数据，防止启动瞬时因数据不足产生误警报（Alert Flickering）。

---

## 本地单次空转测试 (Local One-Shot Dry Run)

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --once
```

**预期行为：**

- 程序在完成一次轮询采集与扫描后自动退出（Process exits after one polling pass）。
- 无需配置私有 API 密钥（No private API key required）。
- 产生的 JSONL 格式运行证据将被写入 `data/extreme_funding_watch_events.jsonl` 中。
- 代码中没有引入任何执行模块 (`execution`) 的依赖。

---

## 本地有限次数空转测试 (Local Bounded Dry Run)

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --max-iterations 3
```

**预期行为：**

- 程序执行 3 次循环后自动退出。
- 未平仓量 (OI) 数据通过 60 秒缓存器获取，而不是每 10 秒轮询一次，以节约 API 额度。
- 在 5 分钟的预热期（persistence warm-up）内，可能不会生成实际的监控警报事件。

---

## 服务器持续运行指令 (Server Run Command)

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --forever --data-root data
```

---

## Docker 部署与运行 (Docker Deployment & Operations)

对于不支持本地 `uv` 环境或需要运行隔离的服务器环境，推荐使用 Docker 进行部署。

### 1. 同步本地代码至服务器 (本地 Mac 执行)
```bash
rsync -avzP --exclude='data' --exclude='.git' --exclude='.venv' --exclude='.ruff_cache' --exclude='.pytest_cache' --exclude='__pycache__' \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/ \
  root@47.82.4.85:/root/crypto-alpha-lab/
```

### 2. 构建镜像与启动容器 (服务器端执行)
```bash
cd /root/crypto-alpha-lab

# 构建镜像
docker build -t crypto-watchlist .

# 启动容器（限制内存为 512MB，挂载数据目录以持久化日志）
docker run -d --name crypto-watchlist \
  --memory="512m" \
  --restart always \
  -v /root/crypto-alpha-lab/data:/app/data \
  crypto-watchlist
```

### 3. 日常维护常用指令 (服务器端执行)
*   **查看运行日志**：`docker logs -f crypto-watchlist`
*   **停止监控容器**：`docker stop crypto-watchlist`
*   **重启监控容器**：`docker start crypto-watchlist`
*   **删除监控容器**：`docker rm crypto-watchlist`

---

## systemd 服务配置示例 (systemd Example)

```ini
[Unit]
Description=crypto-alpha-lab extreme funding watchlist
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/crypto-alpha-lab
Environment=PYTHONPATH=src
ExecStart=/usr/bin/env uv run python scripts/run_extreme_funding_watchlist.py --forever --data-root data
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 24小时日常巡检清单 (24h Review Checklist)

定期查看日志与 JSONL 证据，检查以下指标：

- **总循环次数 (Total iterations)**
- **API 错误统计**：检查 `watchlist_http_error` (HTTP 请求错误)、`watchlist_url_error` (URL 解析/连接错误)、`watchlist_json_error` (JSON 解析错误)、`watchlist_schema_error` (接口数据结构校验失败) 的发生次数。
- **数据过期计数 (`api_stale`)**：数据因网络延迟超过最大年龄门限的次数。
- **溢价缺失计数 (`missing_premium`)**：获取溢价失败导致数据不完整的次数。
- **预热计数 (`micro_persistence_warmup`)**：因处于启动 5 分钟预热状态而被拦截的次数。
- **事件警报级别统计**：`watch_level_1/2/3` 事件发生次数。
- **触发警报的币种 (Symbols that triggered events)**
- **OI 状态分布**：`oi_status` 处于 `ok` (正常)、`missing` (缺失) 或 `stale` (过期) 的占比分布。
- **文件检查**：JSONL 文件的实际占用空间大小及最新的心跳时间戳 (`latest heartbeat timestamp`)。

---

## 安全边界 (Safety Boundary)

该守护进程**严格禁止**执行以下操作：

- 引入交易执行模块 (`import execution`)。
- 产生策略信号实体 (`Emit SignalCandidate`)。
- 生成交易意图 (`Create TradeIntent`)。
- 读取交易所私钥/API Keys。
- 下达任何实盘或模拟盘订单 (`Place orders`)。
