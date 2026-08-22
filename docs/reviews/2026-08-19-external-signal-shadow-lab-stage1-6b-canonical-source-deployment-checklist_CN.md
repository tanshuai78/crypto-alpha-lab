# Stage 1.6B Canonical Official Source Capture Deployment Checklist (Read-Only)

**日期:** 2026-08-19  
**状态:** `read_only_preflight_checklist`  
**适用范围:** External Signal Shadow Lab / Stage 1.6B  
**安全声明:** 本文档仅作为部署前的只读检查清单，**不构成任何 VPS 部署或实盘执行授权**。本文档不包含任何直接启动命令、tmux/systemd 守护进程指令、可执行脚本调用或权限开启指令。

---

## 1. 部署前置条件硬性门禁 (Preflight Gates)

在考虑未来 Stage 1.6B VPS 部署前，必须按顺序逐一核对并满足以下全部前置条件：

### 1.1 Stage 1.5D/F 主机健康与观测状态门禁
- [ ] **UNITREE 观测已完成**: Stage 1.5F 对 `UNITREEUSDT` 的 12 小时深度观测已完全结束。
- [ ] **Stage 1.5G 复核完毕**: 本地 Stage 1.5G 质量复核已完成，且不再占用 VPS 任何 CPU/内存/磁盘资源。
- [ ] **Stage 1.5D/F 进程与锁健康**:
  - Stage 1.5D runtime gate 处于 `ready` 状态。
  - Stage 1.5F blocker 为 `null`。
  - Stage 1.5D 和 1.5F 的 PID、心跳 (heartbeat) 和存储遥测 (storage telemetry) 均处于健康状态。
  - 主机共享锁路径严格指向 `data/external_signal_shadow/.stage1_5_storage_guard.lock`，无死锁或残留未释放锁。

### 1.2 VPS 磁盘与资源配额门禁
- [ ] **主机可用空间预检**: 目标主机可用磁盘空间 >= `EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES` (8 GiB)。
- [ ] **配额数学验证**:
  - `EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES` (12 MiB) >= `EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES` (2 MiB) + `EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES` (2 MiB) + `EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES` (256 KiB)。
- [ ] **根目录物理隔离**:
  - Stage 1.6B 运行根目录位于 `data/external_signal_shadow/stage1_6b/` 下，严禁与 Stage 1.5D/F 共享任何子目录。

### 1.3 来源配置探针凭证门禁 (Attestation Gate)
- [ ] **探针先行完成**: 在目标采集启动前，已针对固定的 32-hex 公告 ID 运行过探针，并生成原子凭证文件。
- [ ] **V2 profile 绑定**: 凭证的 `source_profile_id` 必须为 `binance_public_web_bapi_en_delisting_catalog_v2`，且 `schema_version` 必须为 `stage1_6b_source_profile_probe_attestation_v2`。
- [ ] **同次目录-详情链路**: `probe_article_id` 必须来自同一次 index 响应中精确选择的 `catalogId=161`、`catalogName=Delisting` 的 `articles` 列表；随后仅对该 ID 进行 detail GET。
- [ ] **凭证哈希强绑定**:
  - 探针凭证严格存放于 `data/external_signal_shadow/stage1_6b/source_profile_attestations/<profile-sha256>/source_profile_probe_attestation.json`。
  - 凭证中的 `source_profile_sha256` 与 `request_headers_profile_sha256` 与静态 SSOT 完全一致。
  - 凭证时间戳 `probe_attested_at_ms` 早于或等于运行启动时间 `run_started_at_ms`。
  - `capture_run_contract.json` 中记录的 `source_profile_attestation_sha256` 与该凭证物理文件的 SHA-256 完全匹配。

---

## 2. 运行时与终止不变量检查 (Runtime Invariants)

- [ ] **单进程排他锁**: 每个 live 观测 root 必须持有 `.stage1_6b_writer.lock` 生命周期锁，严禁同一 root 双进程运行。
- [ ] **低频顺序请求**: 单线程顺序 I/O，每 300 秒最多 1 次 index 请求和最多 1 次 detail 请求，零并发，零轮内重试。
- [ ] **候选人 SLA 监控**: 新候选人在 2 个轮次窗口内必须完成首次详情尝试，否则触发终端 SLA 阻断。
- [ ] **容量上限守卫**: 未完成详情候选人数量严禁超过 `EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES` (500)。
- [ ] **Fail-Closed 终止行为**: 发生资源不足或网络不可恢复错误时，原子写入 `terminal_status.json` 并退出，严禁删除已有证据。

---

## 3. 权限与安全边界声明 (Zero Authority Invariant)

- 所有交易、回测与策略权限必须保持禁用：
  - `RISK_LIVE_TRADING_ENABLED` 为 False。
  - `source_audit_passed` 为 False。
  - `point_in_time_source_validated` 为 False。
  - `market_data_coverage_passed` 为 False。
  - `replay_allowed` 为 False。
  - `risk_veto_candidate` 为 False。
  - `trade_signal_allowed` 为 False。
  - `paper_trading_allowed` 为 False。
  - `live_trading_allowed` 为 False。
  - `execution_engine_allowed` 为 False。
  - `alpha_interpretation_allowed` 为 False。

---

## 4. 结论与授权边界

本清单仅供部署审计核对。任何部署动作需另行发起经过审查的操作工单，本阶段代码实现与测试通过不代表已获得部署许可。
