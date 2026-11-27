# Stage 1.3 固定五币量价系列研究复盘与收口（2026-11-23 至 2026-11-26）

日期：2026-11-27（Asia/Shanghai）。性质：`retrospective / branch_stopped / no_alpha_claim`。

本文基于已提交归档的三轮研究代码/文档（Commit `9df7507`）及三轮独立审计通过的仓外只读结果整理，用于封存当前固定五币现货量价探索分支。本文不修改任何已批准的历史 Design、Implementation Plan、规则文件或原始产物，也不授予任何联网、重跑、`commit`/`push`、部署、paper 或 live 权限（`RISK_LIVE_TRADING_ENABLED = False`）。

---

## 1. 三轮探索总览与核心事实

研究窗口固定为 UTC `[2026-06-15, 2026-11-23)`（23 个 7d 市场块，前 7d 预热），固定五币 `BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT / DOGEUSDT`（`BTCUSDT` 为相对走强参考），15m 现货 K 线网格、`60s` 假定延迟、`4h` 参考终点，往返成本仅做 `30 / 50 / 80 bps` 情景披露（`cost_context_only`）。

| 轮次与主题 | 固定样本与核心指标（均为已审实测值） | 独立审计结论与路由 |
| --- | --- | --- |
| **第 1 轮（11-23/24）**<br>固定五币双单指标均值诊断 | `volume_spike_1h`（`n = 787`）：`mu_gross_bps = 16.14`，`median = 6.07`，`delta_bps = 22.42`，23 块 bootstrap 95% CI：`mu = [-6.92, 43.05]`，`delta = [0.98, 40.74]`；<br>`relative_strength_vs_btc`（`n = 964`）：`mu_gross_bps = 4.08`，`median = -3.30`，`delta_bps = 1.80`，CI：`mu = [-8.10, 18.51]`，`delta = [-7.05, 10.70]` | `complete`；双候选均为 `inconclusive_or_concentrated / pause_for_new_evidence / evidence_insufficient` |
| **第 2 轮（11-25）**<br>固定走强队列 `Q` 的放量条件增量 | 固定 `Q = 964`（共振 `J = 155`、仅走强 `b_only = 809`，共同支持覆盖 `155 / 155`，涉及 `64 / 92` 层）：<br>`mu_joint_all_bps = 43.05`，`mu_control_reweighted_bps = -12.45`，`delta_bps = 55.50`；CI 均跨零（`mu = [-14.39, 88.27]`，`delta = [-20.29, 117.14]`）；<br>前后半段断层：Blocks 0–10（`n = 82`）`mu = 79.93 / delta = 106.41`，Blocks 11–22（`n = 73`）`mu = 1.62 / delta = -1.70`；<br>剔除 `block_id = 9`（`n = 115`）：`mu = 11.97`，`delta = 10.71` | `complete`；`inconclusive_or_concentrated / pause_for_new_evidence / evidence_insufficient` |
| **第 3 轮（11-26）**<br>跨币放量广度 `G` 与 `block_id = 9` 归因 | 固定 `J = 155` 核对 1,860 个回看槽位：`151` 笔 `G` 已知（`G=0: 32`、`G=1: 24`、`G=2: 17`、`G=3: 78`），**`4` 笔 `G` 未知**（`missing_row = 18`，`block_boundary_censored = 12`）；按可构造性门禁保留全部 155 行、`outcome_joined = false`，四级收益表全置 `null`；<br>`block_id = 9`（`2026-08-17..2026-08-24`，`Q = 62`：`40 joint / 22 b_only`）时间线完整透传：8/17–18 仅 `b_only`（11 笔），8/19–21 单边普涨（30 笔共振多在 `G=2/3`，日均 `+400.6 / +120.6 / +165.6 bps`），8/22–23 见顶回撤（10 笔共振转负 `-31.5 / -228.4 bps`，多笔 `G=3` 出现深回撤）；DOGE 仅有的 2 笔 `b_only` 对照全落在 8/23 暴跌日（`-473.71 / -86.23 bps`） | `complete`；`breadth_not_estimable / stop_due_to_evidence / evidence_insufficient` |

---

## 2. 分维度归因与收口决策

按 `AGENTS.md` 文档规范区分以下五类结论，不混淆“证据/资源停止”与“广义科学证伪”：

- **`data failure`（数据与边界可构造性缺口）**：
  - 第 3 轮的 4 个未知 `G` 并非原始市场缺失，而是消费既有派生账本 `U/results/ledger.jsonl` 的客观边界所致：`2026-06-15T00:01`（SOL、XRP）往前 1h 落入 `eval_start_utc` 之前的预热区（账本无 eval 决策行）；`2026-07-13T00:16` 与 `2026-09-21T00:16`（ETH）往前 1h 跨越周日块尾，上游在调用 detector 前将跨块 4h 窗口标为 `block_boundary_censored`，未输出客观放量状态。
- **`density failure`（独立机会密度与对照稀疏）**：
  - 23 个 7d 市场块仅为近似依赖单位且相邻块可能相关，真实独立行情机会数远小于 155 笔事件行数；全队列正收益高度集中于单一市场周（`block_id = 9` 占共振事件约 26% 且贡献大部分均值）；同时局部 `(symbol, block_id)` 对照稀疏（如 `block_id = 9` 中 `DOGEUSDT` 仅有 2 笔 `b_only` 对照）。
- **`structure failure`（结构与机制局限）**：
  - 前后半段表现严重断裂（前半段 `+79.93 bps`，后半段 `+1.62 bps`），且名义 bootstrap 区间显著跨零；
  - `block_id = 9` 完整时间线显示：跨币高放量广度 `G = 3` 既出现在 8/19–21 主升加速段，也同样出现在 8/22–23 见顶暴力砸盘段；纯无方向放量广度无法区分“趋势启动”与“高潮反转”；
  - 原同币同周对照存在显著**周内阶段错配**（把 8/19–21 普涨期共振与 8/23 暴跌期 `b_only` 对照相减，放大了表面条件差异）；此外共振组入场前本身具有更高的 `self_r1h` 与 `b_trigger_value`，尚未剥离纯动量混杂。
- **`execution/cost failure`（成本空间与尾部路径风险）**：
  - 第 1 轮单指标毛均值（`16.14 / 4.08 bps`）及第 2 轮去特殊周后的共振毛均值（`11.97 bps`）均低于常见 `30 / 50 / 80 bps` 现货往返摩擦情景；即便全样本共振毛均值 `43.05 bps` 留给手续费、点差与冲击成本的空间也极薄；
  - 特殊周回撤段可见极端 4h 路径尾部损失（如 `2026-08-22T06:31 XRPUSDT` `G=3`：`y_gross_bps = -502.09`、`mae_4h_bps = -1005.44`；`2026-08-22T02:46 DOGEUSDT` `G=3`：`y_gross_bps = -114.12`、`mae_4h_bps = -1147.61`），4h 包络且无法推导可执行止损。
- **`confirmed next action`（确认的下一步动作）**：
  1. **正式停止本轮固定五币现货 15m 量价系列（单指标、量价共振、跨币放量广度）的进一步开发与数据返工**，将分支状态标记为 `stopped`（研究定性维持已审 `evidence_insufficient`，不冒称已科学证伪广义量价理论）。
  2. **不为补齐 4 个边界槽位去重读原始 ZIP、修改上游 `stage1_3_fixed_universe_diagnostic.py` 或删掉未知事件重跑**：23 周区间已被多次暴露不再是独立 OOS，且特殊周反例已足够说明继续投入的性价比极低。
  3. 后续转向任何新研究方向前，先按 [L2 §14.1](../../.agent/rules/L2_Alpha_Research_Methodology.md#141-lightweight-research-direction-screening) 四问（买单机制、独立机会/容量、可验证性与成本边界、最小预算与停手条件）完成轻量初筛，再决定是否立项。

---

## 3. 对后续研究的可复用经验

1. **特征计算与未来收益标签必须解耦**：上游若因“未来 4h 持仓跨块”而将整行决策标记为 `block_boundary_censored` 并跳过特征计算，会阻断下游任何跨边界的因果回看（如本次周一 `00:16` 无法获知周日 `23:31/23:46` 是否放量）。未来设计研究账本时，**只依赖过去信息的客观特征状态**应始终完整落盘，**未来收益窗口是否删失**单独列字段标记。
2. **周内行情切换会击穿稀疏的“同币同周”对照**：加密市场一周内可完整走完“横盘 → 主升 → 砸盘”。设计条件对照实验时，必须同步检查对照组在单元内的数量密度与时间分布，警惕对照集中于单日极端波动造成的阶段错配。
3. **坚持“先可构造性门禁 + 低成本体检，再决定是否扩建”**：三轮探索均严格控制边界与预算，既挡住了“删缺口凑收益表”的隐性偏差，也在未投入重型回测/实盘工程前就看清了高广度尾损与样本集中度风险。

---

## 4. 仓内归档与仓外证据定位

- **仓内代码、测试与已审 Design/Plan 归档提交**：Commit `9df7507`（原样封存，不回写修改）：
  - 第 1 轮：[Design](../designs/2026-11-23-stage1-3-fixed-universe-mean-return-diagnostic-design_CN.md)（SHA-256 `8622d06b75c17a7bdfd103224cb11b75d147a7b92b1f3a06be6b81cd4417bd23`）、[Preflight Brief Plan](../plans/2026-11-23-stage1-3-spot-universe-constructability-preflight-brief-plan_CN.md)、[Implementation Plan](../plans/2026-11-24-stage1-3-fixed-universe-mean-return-diagnostic-implementation-plan_CN.md)（SHA-256 `bf066b19f0bd43c2378bf6c34553dd10f7c9747ea070815627818c05db8e1e3a`）；代码 [stage1_3_fixed_universe_diagnostic.py](../../src/research/external_signal_shadow/stage1_3_fixed_universe_diagnostic.py) 与 [run_stage1_3_fixed_universe_diagnostic.py](../../scripts/external_signal_shadow/run_stage1_3_fixed_universe_diagnostic.py)。
  - 第 2 轮：[Design](../designs/2026-11-25-stage1-3-volume-strength-conditional-increment-design_CN.md)（SHA-256 `a7680d7984c9eba95c12cdda152a989e42d1df25a125bd6d7e2657de20458797`）、[Implementation Plan](../plans/2026-11-25-stage1-3-volume-strength-conditional-increment-implementation-plan_CN.md)（SHA-256 `751dcc7b4ec9b9de4b788ffe648f8166253568fb59e2f450ffe8c06e3fc28a5d`）；代码 [run_stage1_3_volume_strength_conditional_increment.py](../../scripts/external_signal_shadow/run_stage1_3_volume_strength_conditional_increment.py)。
  - 第 3 轮：[Design](../designs/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution-design_CN.md)（SHA-256 `327641761e2b6c625e873c1c2592418a2b43c640935eed78507b9e36617e30fa`）、[Implementation Plan](../plans/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution-implementation-plan_CN.md)（SHA-256 `2aa3f67bec40f4344518ad322800818619aa5d6502ac4ce136ef03e4c654b584`）；代码 [run_stage1_3_cross_asset_volume_breadth_attribution.py](../../scripts/external_signal_shadow/run_stage1_3_cross_asset_volume_breadth_attribution.py)。
- **仓外只读运行产物（不提交进 Git，下表仅供来源定位，不授予重新运行或下游自动消费权限）**：

| 轮次 | 仓外证据根目录 | 核心 `summary.json` SHA-256 |
| --- | --- | --- |
| 第 1 轮（固定五币均值） | `/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-24-stage1-3-fixed-universe/20261125T062144Z` | `624d26de18a22ed9a4474e78cd1e844bf148b29e33a7c4d47050aa80015edec2` |
| 第 2 轮（放量条件增量） | `/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-25-stage1-3-volume-strength-conditional-increment/20261125T124130Z` | `09400e8a7203338291741b0ad20c4c5c16ebeb2605c9cdb0dc16aa65bc38e300` |
| 第 3 轮（跨币放量广度） | `/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution/20261126T082841Z` | `f21e026c4c3079167b11aecc5203b7ae625926a25980498541c42a6fd62f1391` |
