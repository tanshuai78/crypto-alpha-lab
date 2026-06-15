# External Signal Shadow Lab Stage 1.4A.1 Real Data Audit Plan Review

## 1. 决策判定
- **最终结论：** **通过 (Approved)**
- **允许的下一步决策（Next Allowed Decision）：** 
  - 若清算数据不足或缺失：`continue_data_collection` (继续收集 CEX 实盘清算数据)
  - 若四项数据均过检合格：`eligible_for_phase1b_review` (合格进入下一阶段)

---

## 2. 总体判定与亮点设计
本轮二审针对修订后的 `2026-06-15-external-signal-shadow-lab-stage1-4a1-real-data-audit-completion-plan_CN.md` 进行。该计划完美地吸收并修入了上一轮一审提出的防假审计约束，包含 UTC 时区安全解析、动态推断 Open Interest 频率、清算 Manifest 独立统计指标、Ruff 规避单字母变量及 `rsync` 限制手动运维等。

计划边界清晰，不涉及任何 forward return / PnL 计算，严守 Phase 1 纯数据审计定位，安全等级高，判定为 **通过**，建议立即开始执行。

---

## 3. 做得对的地方 (Strengths)
1. **时区与时序计算的严密性**：OI 数据的 `create_time` 显式强制使用 `timezone.utc` 解析，避免了在非 UTC 容器/物理机上运行时 `datetime.timestamp()` 发生的系统时区偏移。
2. **频率的非硬编码推断**：针对 Binance Vision Metrics ZIP 文件，不再盲目假设固定 5m 或每小时频率，而是采用数据点 sorted timestamps 差值的 median 值动态推断。这可有效抵抗数据缺失、漂移和重复的噪声干扰。
3. **真实清算 Manifest 审计**：清算 manifest HEAD 成功只作为可用性审计指标（coverage ratio），明确禁止伪造 synthetic liquidation events 行，保证了可行性审计结果的完全真实性。
4. **安全与降级防御**：REST 分页网络拉取增加了 stall 防止死循环检测；Vision 下载采用优雅降级（单日 ZIP 404 记录到 summary 而不崩溃）；规避了单字母变量 `l`。
5. **硬编码隔离**：所有控制参数与路径模板全部抽离至 `configs/base.py`，保持了 configuration SSOT。

---

## 4. 必须修正的问题 (Required Fixes)
- 无（上一轮所有 mandatory fixes 均已完全合并并体现在本计划中）。

---

## 5. 参数 / 阈值 / 证据边界审核
- **数据深度**：`EXTERNAL_SIGNAL_STAGE1_4_REAL_AUDIT_HISTORY_DAYS` 设置为 180 天，完全覆盖并高于 90 天的最短可行性审计线（`EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN`），统计厚度足够。
- **频控友好**：网络请求间带有 polite delay `EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC = 0.2` (200ms)，符合 Binance 频控安全红线。
- **分页限制**：REST 分页单页 `limit=1000` 处于合理与安全的 API 返回上限。

---

## 6. 建议执行顺序
1. **Task 1 & 1.5**：添加 configs 配置常量，配置并验证 `.gitignore` 规则（确保 `data/external_signal_shadow/derivatives_stress/` 被忽略）。
2. **Task 2**：实现 Binance Vision metrics OI 的下载与转换脚本 `build_stage1_4a_binance_vision_oi_metrics_archive.py`，编写并验证单元测试（包括 create_time UTC 解析、ZIP 读写和 interval 推断）。
3. **Task 3, 4, 5, 6, 7**：修改 `run_stage1_4a_derivatives_stress_data_feasibility.py` 及相关 test 模块，完成 REST 分页、符号标准化、nested forceOrder 解析以及 manifest coverage 审计升级。
4. **Task 8, 9, 10**：实际运行测试、收集数据（含 live-public 和 mixed audit）、生成 review 脚本及最终的可行性 review 报告（确认 per-symbol blocker table 渲染正常）。

---

## 7. 数据证据语义风险
- **Vision Metrics 延迟性**：Daily metrics ZIP 是历史日包，不是实盘实时的 OI。本次审计主要验证*历史 replay 阶段数据源的可行性*，并不代表实时策略运行时能拿到同等质量的数据。
- **Liquidation Manifest 占位**：Manifest HEAD 成功仅代表日包 ZIP 文件的存在性，不代表该文件已下载解压或事件级可用。若 liquidation 数据源最终仅有 manifest，它不能参与 full composite replay。

---

## 8. 本轮能证明什么 / 不能证明什么
- **能证明**：
  - 过去 90d/180d 期间，Binance settled funding、futures klines、Open Interest 及清算数据的历史可用性与时间连续性。
  - 数据接口是否能在有限的限频策略下，平滑地获取并拼接成时序对齐的 composite 序列。
- **不能证明**：
  - 无法证明任何 derivatives stress 策略的预期收益或 Alpha edge（因为禁止计算 forward return 和 PnL）。
  - 无法证明实时交易状态下 exchange API 的响应延迟或滑点。

---

## 9. 禁止从本轮结果推出什么结论
- **严禁推出**：“数据可行性通过后即可直接上线实盘或进行 shadow 交易”。
- **严禁推出**：“衍生品挤压/爆仓反转等事件有盈利空间”。
