# Stage 1.5D / 1.5F 延期合约交易状态门禁与新批次重新观察最小修复 — Implementation Plan

日期：2026-11-13（Asia/Shanghai）。状态：`plan_candidate / pending_independent_review`。

## Allowed Change Scope

以下白名单是未来取得本 Plan 精确版本实施批准后的修改上限，不是本轮执行权限。只修改对应 Task 必需的部分；未列路径不得借“关联修复”顺便改动。

**Allowed implementation paths（均为已有文件）**

| 路径 | 唯一允许目的 |
| --- | --- |
| `configs/base.py` | 只新增 Design §4.2 的两个 recheck 配置，值为 600 秒、每 poll 1 个子预算槽；不改变任何现有阈值或 enablement 值 |
| `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` | 详情溯源、revision-only 重查接线、新 CLI、恢复选择和现有 attestation/consumer proof 接线 |
| `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py` | 两个 nullable watch 字段、对应严格校验/往返和既有队列预算适配 |
| `src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py` | 同页精确 L1 日期延后识别与既有 v2 builder/index/幂等链调用 |
| `src/research/external_signal_shadow/stage1_5d_runtime_gate.py` | 在现有固定字段投影中保留、校验恢复选择；普通 READY 判定不新增 producer-enabled 前提 |
| `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py` | 真实准入/promotion 接线、响应后决策时间、新根 bootstrap/root-contract 绑定和恢复上限传播 |
| `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py` | 统一交易就绪/时间冲突判定、pending reducer、受限 delayed-launch 恢复分支和 D gate 消费校验 |
| `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py` | pending/恢复所需 additive metadata 的显式字段、校验与序列化支持 |
| `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py` | pending reload/promotion 时固定期限、恢复标记、证据上限及 admission/latest hash 一致性 |

**Allowed verification paths（只增补/调整相关测试，不删除既有失败断言）**

- `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- `tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py`
- `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- `tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Allowed documentation paths**

- `docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md`：只增补本次门禁、启用前提、新根启动顺序与停止条件。本文在审查/批准前允许修订；批准后不通过打勾、回填进度或改写正文改变批准 SHA。

**Allowed generated/runtime artifacts**

- 编码/合成测试：仅执行基线目录 `/private/tmp/stage15-postponement-baseline.*` 和 pytest `tmp_path`/临时 Git 仓库中的既有格式产物；不得接入真实 API、生产根或受限历史数据。新基线目录必须为空且由 `mktemp` 创建。
- 真实样例：仅在另行取得精确来源读取授权后，在授权的外置临时目录读取原始字节及现有 manifest/version 记录；本 Plan 不预授权下载、复制真实 raw 进仓库或修改 AIA fixture 元数据。
- 线上产物：本 Plan 的实施批准不授权创建。后续操作批准须明确新的 `RUN_ID`、D/F 绝对根、同根 proof 路径和运行期限；只写新根内既有 raw/manifest/version/scheduler/event/index/revision/gate/root-contract/watermark/state/summary 格式。不得写旧根。

**Affected but unchanged**

| 边界 | 保持不变及兼容性验证 |
| --- | --- |
| `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py` | 复用 canonical launch/revision builder、strict validator、latest revision selector 和 hash 函数；Task 1/3/4 及既有契约测试验证 |
| D 的 `stage1_5d_live_event_source_parser.py`、`stage1_5d_live_event_source_storage.py`、`stage1_5d_live_event_source_client.py`（均位于 `src/research/external_signal_shadow/`） | parser 及 raw/manifest/version 首观测、原子写入/预算机制不重写；Task 2/3 使用其真实调用路径和往返测试 |
| `src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py` | 复用当前统一缓存、实际响应 hash/fetched time/available；失败不因缓存仍有 rows 获准，Task 1 加 runner 反例 |
| `src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py` | bootstrap/seen identity/普通 moving watermark 算法不变；例外局限于 loader 的显式恢复分支，Task 4 测试 |
| `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py`、`stage1_5f_live_depth_observer_summary.py`（后者同目录） | 使用既有应用去重及 summary 对 canonical root-contract hash 的绑定，不另建 registry 或重复复制恢复权限字段 |
| 1.5G loader/decision/integrity 与既有 Rule 17 校验工具 | 不改变质量/晋级规则，Task 5 跑现有回归；`completed`/HTTP 200 不等于有效证据 |
| 获批 Design、其 §2 引用的历史 Design、旧 D/F 所有根及 AIA fixture | 不改文件、不迁移/修补旧状态；Task 0 基线与 Task 5 范围核验，真实来源门禁见 §7 |

**Forbidden**

- 白名单外修改、全库格式化、`ruff check --fix .`、`git clean -fdx`、reset/checkout/stash 回退用户改动；不得新建生产模块、通用恢复框架、Recorder、独立 ticket/spec 或新 Verifier。
- 不改变 `RISK_LIVE_TRADING_ENABLED=False`、signal/execution/paper/live 权限；不导入下单/私钥/余额能力，不改变 USDC/USDT 产品范围或 1.5G 业务规则。
- 不开启 revision producer，不把 Part A/真实 fixture/前置 commit 标志提前改为通过；不修改旧根、历史 index、旧 `completed`、bootstrap seen identity 或旧 evidence hash。
- 不执行 `git add`、commit、push、deploy、SSH、API 实测、采集启停或其他 runtime action；后续独立操作批准不能由测试或 CLI 元数据代替。

## 1. 权威、目标与范围说明

**绑定 Design：**[2026-11-13-stage1-5d-1-5f-postponed-launch-readiness-and-reobservation-hotfix-design_CN.md](../designs/2026-11-13-stage1-5d-1-5f-postponed-launch-readiness-and-reobservation-hotfix-design_CN.md)。SHA-256：`f8d5f404e55893f86208c724537077fdcabc391a4d90bebba8bafc94fe619874`。用户已明确仅批准此 Design；本文仍待 B 独立审查及用户精确 SHA 实施批准。

**Goal：**修复“symbol 存在且旧计划到点就启采”的错误，保留可信正文溯源，经既有修订链感知原地延期，并支持指定文章在全新根受限重新核验/观察；不复活旧失败记录。

**Architecture / Tech Stack：**Python 现有 D/F runner、scheduler、v2 transport 与 pending state；pytest/ruff；沿用标准库、现有 storage guard、proof/registry/serializer，不新增依赖。本任务是采集正确性修复而非 Alpha 研究，不生成收益、交易信号或策略规则；L2 §15 策略研究要求为 `N/A`。

起草时核对本地 HEAD 为 `2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`，唯一既有未跟踪项是获批 Design。实施时重新记录实际 `BASE_SHA`，不得假定用户后续提交文档后 HEAD 仍相同。用户线上取证及尚未取得的真实原始字节边界沿用 Design §1；报告摘要不替代真实 fixture。

**按 L1 §2.8 的取舍：**单独加 `TRADING` 只能止住一类空采，不能闭合 D 溯源、同页修订及新根恢复；单独开启 producer 不能制造可信前提。采用已有链的局部适配，不拆分大模块，不把文件数/行数当作最小化证明。新增状态仅服务明确的等待/恢复边界；若需重定义上游 hash、catalog 或 proof 生命周期，按 Rule 16 停止。

## 2. 冻结语义与主要复用边界

### 2.1 不允许实施方另选的时间/权限规则

- `S` 始终来自当前 poll 已通过身份/PIT 的最新正式官方计划；当前成功、新鲜、完整 API 的 `O=onboardDate` 只供一致性检查，不覆盖 `S`。延期冲突为 `O > S + 60,000ms`，包括 `TRADING`。
- 有冲突先处理本轮合法 revision 和可信 API；冲突仅在可信 `S` 与当前有效 `O` 在 60s 内一致时解除。未解 episode 使用固定 6h deadline、清除旧 visibility deadline；重复 poll/hash/reload/仍冲突的 revision 不续期。仍未解且 `now >= deadline`，拒绝 `rejected_anchor_conflict_unresolved_timeout`。
- 冲突已解且新 `S` 在未来，进入 `pending_launch_time_in_future`，保持既有 5m refresh、不受 6h 提前截断；到点且无冲突才使用 `S+15m`。非交易等待为 `pending_exchangeinfo_not_trading`，复用 `symbol_visibility_deadline_ms`；`now > S+15m` 以 `rejected_launch_not_trading_timeout` 拒绝，未知/缺失证据也不能无限等待。
- 普通 `TRADING` 的 clean/recovery 边界分别为 `<=2m`、`<=15m`；晚 1ms 不准入。快照年龄按响应后实际决策时刻计算，区间为 `[-CLOCK_SKEW_TOLERANCE_MS, EXCHANGEINFO_REFRESH_SEC*1000]`，沿用现值 30s/300s；缺 hash、无效时间、`available=false` 不准 active。
- 新恢复只能是指定 article/symbol 的 fresh v2 future-launch，标记 `explicit_future_launch_revalidation_v1`，证据上限 `recovery_validation_only`，不能 clean、不能绕过 15m、不能将晚启采改成新的 12h 窗口。普通事件/旧 active-root recovery 行为不扩大。
- D recheck 是 revision-only：已 emit 的 launch terminal 不重开；600s 冷却、每 poll 至多 1 个既有总预算内槽、原 never-attempted 保底不被挤占；watch 截止为原实际首观测加既有 14d，不顺延。

### 2.2 复用承诺（审计检查真实调用，不以 import 作为证明）

| 能力 | 调用/适配位置与验证 |
| --- | --- |
| `classify_event_symbol_eligibility_with_diagnostics()`、`re_resolve_pending_anchor()` | 在 F loader 内共用最小 readiness 判定，runner 首次和 promotion 均消费实际结论；不新增平行状态机。Task 1 用真实 runner 断言 depth 调用次数 |
| D parser、`apply_formal_launch_event_contract()`、`record_formal_futures_launch_event()`、identity index writer | Task 2 从可信 parser 结果保存元数据，再过 scheduler/Block 2.5/formal writer/index，不另写解析器或人工 provenance |
| `select_detail_retry_attempts()`、既有 `launch_schedule_revision_detail` | Task 3 将 watch 工作纳入现有选择/HTTP 扣账；不额外请求额度、不建后台 worker；真实 runner 排队/请求计数验证 |
| `process_trusted_schedule_revision_detail()`、`link_schedule_revision_candidate()`、`emit_schedule_revision_batch()` | Task 3 仅对已 durable 同页版本提供精确 L1 自关联，不全局放松 revision classifier；仍调用 canonical v2 builder/validator、first-observed registry 和 append 后 dedupe |
| `select_latest_applicable_official_schedule()`、F `process_schedule_revision_event()`/registry | Task 3 验证 durable revision 到 F 单次应用；期望时间手算，不能调用 selector 生成断言 |
| `build_stage1_5d_runtime_gate()`、`verify_stage1_5f_consumer_proof()`、F root-contract writer | Task 4 保留恢复选择，复用原 commit/manifest/canonical hash/PID/sticky 证明链；不把 producer effective 作为普通 D READY/F bootstrap 的前提 |
| `bootstrap_watermark_from_stage1_5d_events()`、`load_watermark()`、state promotion/hash builder | Task 4 使用实际 bootstrap 产物和既有 bootstrap identity/source 字段，同根验证后再请求恢复；只在受限 loader 分支适配 moving watermark，不改全局 watermark 算法 |

## 3. 验证与 Fixture 约定

行为切片均执行公开入口 `RED -> GREEN -> REFACTOR`。先写断言再运行，RED 应为实际行为不符的 `RC=1`，不是导入失败、收集失败或零选中；GREEN 与回归为 `RC=0`。新测试统一在名称中包含 `postponement`，以下 `-k postponement` 命令不得全部 deselect/skip。

Rule 15 分级：纯时间、预算及故障注入可用最小合成输入；跨模块正向必须用真实 canonical builder/serializer/strict loader、实际写出的字节及其 SHA，Git 证明用临时真实 Git 仓库。只替换网络/时钟/进程环境边界，不 monkeypatch `eligible`、proof pass、producer effective、canonical validator 或 revision 选择结果来证明接线通过。negative case 从有效输入做具名最小变异；复合生命周期反例列清所有变化。合成原始正文须标为 synthetic，不称官方样例。

| 独立 Oracle（UTC） | 固定期望 |
| --- | --- |
| `S0=2026-11-11 09:30`（`1794389400000`） | 09:32 clean inclusive；09:45 recovery inclusive；09:45:00.001 不准入 |
| 首次冲突 11-11 09:31 | episode 截止 15:31；09:45:00.001 仍 pending conflict、depth=0；reload 不延长 |
| 10:00 首观测合法 revision 至 `S1=11-16 08:30`（`1794817800000`），当前有效 API 匹配 | clear conflict -> future pending；新 visibility 上限为 11-16 08:45，不再用 11-11 09:45 |
| 到 15:31 无合法解除证据 | 终态 conflict timeout；后到 revision 不复活 |
| snapshot age 边界 | -30,000ms、300,000ms 合规；-30,001ms、300,001ms 不合规；请求前 tick 不参与年龄自证 |
| O 与 S 的差 | +60,000ms 在容差内；+60,001ms 是延期冲突；已有冲突在 API 缺失、过期或仅 status 翻转时仍保留 |
| 原首观测 `t`，watch/recheck | 截止固定 `t+14*24*60*60*1000`；600s 前不 GET；双 symbol 同文章每次只扣一个详情请求 |
| 最晚目标官方 11-16 08:35，观察 12h | 终点 11-16 20:35；晚启动不后移终点，官方再改期才随合法新 anchor 变化 |

Rule 17：不新建 artifact 类型/profile/独立 Verifier，不无条件调用 `scripts/governance/verify_artifact_schema.py`。现有 authority/attestation/profile 校验一律保留，新增 metadata 必须经过现有严格生产/消费校验与 canonical hash；独立语义证据来自上表、次数/期限/调用顺序及真实 consumer 行为。若发现某个已冻结 profile 明确列入实际产物，则运行其原 verifier，不冒称通过不存在的 profile，也不放宽原契约。

## 4. 垂直切片与验证命令

### Task 0：批准身份、基线与执行前事实

**Dependencies：**B 审查通过且用户明确批准本 Plan 精确 SHA；未批准不得进入 Task 1。对应 `INV-01`、`INV-08`。本 Task 只读仓库；基线写仓外。

执行者先读 AGENTS、L0/L1、execute-approved-plan、systematic-debugging/TDD 技能；上游技能的自动 commit、worktree 创建或执行提示不覆盖本 Plan 权限。下列 Bash 中 `APPROVED_PLAN_SHA256` 只能来自用户实际批准原文，禁止先 hash 当前文件再把它自赋为“批准值”。

```bash
set -eu
export GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.
PLAN=docs/plans/2026-11-13-stage1-5d-1-5f-postponed-launch-readiness-and-reobservation-hotfix-implementation-plan_CN.md
DESIGN=docs/designs/2026-11-13-stage1-5d-1-5f-postponed-launch-readiness-and-reobservation-hotfix-design_CN.md
DESIGN_SHA=f8d5f404e55893f86208c724537077fdcabc391a4d90bebba8bafc94fe619874
if [ -z "${APPROVED_PLAN_SHA256:-}" ] ||
   ! printf '%s  %s\n' "$APPROVED_PLAN_SHA256" "$PLAN" | shasum -a 256 -c - ||
   ! printf '%s  %s\n' "$DESIGN_SHA" "$DESIGN" | shasum -a 256 -c -; then
  echo STOP=approved_authority_mismatch; exit 1
fi
BASE_SHA=$(git -c core.fsmonitor=false rev-parse HEAD)
BASELINE=$(mktemp -d /private/tmp/stage15-postponement-baseline.XXXXXX)
printf '%s\n' "$BASE_SHA" > "$BASELINE/BASE_SHA.txt"
git -c core.fsmonitor=false status --porcelain=v1 --untracked-files=all > "$BASELINE/status.before.txt"
git -c core.fsmonitor=false diff --binary > "$BASELINE/worktree.before.patch"
git -c core.fsmonitor=false diff --cached --binary > "$BASELINE/index.before.patch"
git -c core.fsmonitor=false ls-files -s > "$BASELINE/index.before.txt"
git -c core.fsmonitor=false ls-files --others --exclude-standard -z > "$BASELINE/untracked.before.nul"
while IFS= read -r -d '' p; do
  mkdir -p "$BASELINE/untracked/$(dirname "$p")"
  cp -p "$p" "$BASELINE/untracked/$p"
  shasum -a 256 "$p" >> "$BASELINE/untracked.before.sha256"
done < "$BASELINE/untracked.before.nul"
cp "$PLAN" "$BASELINE/approved-plan.md"
cp "$DESIGN" "$BASELINE/approved-design.md"
shasum -a 256 "$PLAN" "$DESIGN" configs/base.py > "$BASELINE/authority.before.sha256"
printf 'BASE_SHA=%s\nBASELINE=%s\n' "$BASE_SHA" "$BASELINE"
PYTEST=(.venv/bin/python -m pytest -q -p no:cacheprovider)
D_RUNNER_TEST=tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
F_RUNNER_TEST=tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
"${PYTEST[@]}" "$D_RUNNER_TEST" "$F_RUNNER_TEST" \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py
```

预期：两个 authority 校验为 OK、基线目录/HEAD/status/patch/untracked 字节可复核，既有测试 `RC=0`；既有 skip 原因单列，不称完整真实来源验收。记录九个实现文件的 SHA 及运行清单；有脏改动先对比，不覆盖、不伪造干净基线。若基线测试失败先记录并按 Rule 16 分流，不静默删除测试。Graphify 仅查询 `re_resolve_pending_anchor`、`process_trusted_schedule_revision_detail`、`verify_stage1_5f_consumer_proof`，用 `rg` 核对调用和动态 JSON 字段；不更新图文件。

### Task 1：F 由真实就绪证据决定首次准入和 pending promotion

**Dependencies：**Task 0。对应 `INV-02`、`INV-03`、`INV-01`。**文件：**F loader/models/state/runner；对应 loader/models/state 与 F runner 四个白名单测试文件。

1. RED：对同一个 canonical v2 event 仅改变 API 状态/时间/available/hash，覆盖 USDC、USDT、`PENDING_TRADING`、`PRE_TRADING`、未知/缺字段、过期/未来快照、网络失败但缓存仍有 rows。实际 runner 首次与 pending promotion 均须 depth=0；完整一致的 `TRADING` 正向样例才请求 depth。加入“HTTP 返回晚于 poll tick”的时钟反例。
2. GREEN：在现有 loader 内共用最小 readiness 判定，先合法 revision、再冲突、再 future、再固定 late-start/status，沿 §2.1 落实；runner 不可只凭旧 `pending_ready_for_admission` promotion。复用当前 exchangeInfo 刷新，无逐 symbol 新请求器。
3. RED/GREEN：以上表冲突序列穿过 `re_resolve_pending_anchor()`、state writer/loader 和 promotion；验证原 15m 不杀死 unresolved episode、同 poll 有合法修订先处理、15:31 未解决则终态、终态不复活。新 status/deadline 均经 `EventSymbolState.to_dict()/from_dict()` 保留，拒绝仅存内存。
4. REFACTOR：只消除这三条入口的重复规则，普通 active/completed 收到 revision 后的污染/窗口处理不改。

```bash
"${PYTEST[@]}" tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  "$F_RUNNER_TEST" -k postponement
```

先 RED `RC=1` 且由行为断言失败，后 GREEN `RC=0` 且有实际通过项；输出证明包含各入口 depth 次数、固定 deadline 与独立时间边界，不只 helper 分类结果。

### Task 2：可信正文等待后发出，事件和 index 溯源仍闭合

**Dependencies：**Task 0；可与 Task 1 独立验证，最终组合后再进入 Task 3。对应 `INV-04`、`INV-01`。**文件：**D runner/scheduler；D runner 和 scheduler 两个白名单测试文件。

1. RED：通过真实 D poll/fixture 入口解析双 symbol 正文，第一次 exchangeInfo 不足进入 `pending_pre_trading`，序列化后重载，下一 poll 经 Block 2.5 发出。断言 event/index 的 payload hash 等于实际 raw bytes SHA；fetched time 等于 request manifest；两个 symbol 各自节点路径、`raw_time_text` 来自 parser 的候选证据。
2. GREEN：在可信详情成功后、所有等待/emit 分支前统一设置已有的 attempted/hash/fetched/url/variant/trusted/candidate provenance 字段；检查 strict scheduler 投影、emit builder/index writer 均消费这一来源。不能用毫秒文本、title 或最后一次其他响应 hash 补缺。
3. 增加缺 hash、缺候选溯源及第二 symbol 不完整的 fail-closed/diagnostic 反例，不更改 D 可提前发预告及 all-or-none 规则，不修补旧 index。

```bash
"${PYTEST[@]}" "$D_RUNNER_TEST" \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py -k postponement
```

RED/GREEN 同前；GREEN `RC=0`，实际请求/保存/等待/reload/发出/index 链必须走通，不以直接调用 builder 替代。

### Task 3：已 emit 文章有界重查，同页日期延后经正式链只应用一次

**Dependencies：**Task 1、Task 2。对应 `INV-03`–`INV-06`、`INV-08`。**文件：**base、D runner/scheduler/producer、F runner/loader；D runner/scheduler/producer 与 F runner/loader 五个测试文件。

1. RED：用实际 D runner 的两次可信内容版本及 canonical durable launch/index；旧版本发出后保持 terminal，600s 到时通过现有 `launch_schedule_revision_detail` 选中并重查。新正文只有日期延后、无改期关键词，F 读到 durable v2 revision 后更新 pending anchor，一次应用；重复同目标/同内容、重启后重读均不二次应用。
2. GREEN：仅新增 `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_RECHECK_INTERVAL_SEC=600`、`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_RECHECK_BUDGET_PER_POLL=1`。在原预算选择/扣账内安排同文章一个槽，保留 never-attempted 保底、端点冷却、存储预算。新增且仅新增 nullable `next_schedule_recheck_at_ms`、`schedule_recheck_deadline_ms`；新 article/terminal 构造器与 strict serializer/validator 同步支持。旧兼容读分支如需默认值，仅容许这两个新增字段缺省为 None，不放宽其他缺键/未知键，不改旧根磁盘文件。
3. watch 从当前根 durable index 建立，固定原首观测+14d；最新 official 使用既有合法 revision selector。覆盖 `PENDING_TRADING -> TRADING` 但 O 仍冲突、时间未知/过期、future official、后续合法 revision 更新 S；不能因 status 翻转单独停止。只有全部 symbol 当前证据完整、新鲜、TRADING、到点且 O/S 在 60s 内一致、无未解冲突，才因就绪结束；取消/固定到期/根停仍结束。
4. 同页 L1 扩展局限于“同 article+exact symbol+唯一 durable identity+可核验旧 payload+不同新 hash+严格更晚时间”。先 raw/version，再 durable launch/index，后 link/emit；source first-observed 决定 `revision_available_at_ms`。复用现有 builder/strict transport、semantic ID 算法和 append 成功后登记语义 ID 的顺序。不得全局把普通 launch 当 revision，也不把 API 时间写成官方修订。
5. 负向：仅 HTML 改动、无 index/hash、旧 index 未 durable、L4、身份多匹配、增减 symbol、缺时间、同时间矛盾、无关键词提前/取消不 formal emit。all-symbol 版本保持 all-or-none，原明确 per-symbol 修订路径不变。producer disabled 时仍保存证据/诊断而不 formal emit，普通 launch collection 不受阻。
6. `INV-08` 的正向 attestation 用真实临时 Git 仓库及规范构造的 consumer 产物；既有代码树/commit/Part A/fixture prerequisite 逐项缺失时必须 fail closed。测试环境可提供受控前提，不据此声明生产 prerequisite 通过。

```bash
"${PYTEST[@]}" "$D_RUNNER_TEST" "$F_RUNNER_TEST" \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py -k postponement
```

GREEN `RC=0`；必须有 runner poll -> durable revision -> F registry -> pending anchor 的通过项。独立检查每 poll/文章请求数、固定期限、revision 首观测时间及单次应用，不能手填伪 hash/manifest 或 patch proof 返回值获得正向结论。

### Task 4：新根 bootstrap 之后才显式重新核验，恢复权限不扩散

**Dependencies：**Task 3。对应 `INV-01`、`INV-02`、`INV-03`、`INV-07`、`INV-08`。**文件：**D runner/runtime gate、F runner/loader/models/state；D/F runner、D runtime gate、F runtime gate validator、F loader/models/state 七个白名单测试文件。

1. RED/GREEN CLI：新增唯一参数 `--future-launch-recovery <article_id>:<comma-separated-symbols>`，校验 article、非空去重 symbol，与 `--active-root-recovery-*` 互斥。只接受全新 D/F 根；不搬旧 scheduler/index/state/watermark，不自动扫描旧根。事故 ID/日期不得硬编码进产品逻辑；本次后续操作批准的选择只能是 `2d89a5966b174a2689ab2c2a15db1757:HYPEUSDC,TRXUSDC`。
2. 恢复选择的 wire metadata 使用同一个 `future_launch_recovery` 字段：缺省/None 为禁用，否则 `{source_article_id: <合法ID>, symbols: <排序且无重复列表>}`。D runner -> `build_stage1_5d_runtime_gate()` 固定投影 -> F strict 消费 -> `observer_root_contract.json` 均保留相同规范值，纳入既有 canonical contract hash。初始化后不能跟随任意变化的 gate 自动改写已绑定选择；不匹配即阻断。普通无参数根的兼容性保留。
3. 真正启动顺序的测试必须是：新 D 普通 catalog bootstrap（目标隔离、发布普通 gate）-> 新 F `--bootstrap-watermark` -> F 普通运行产生有效且新鲜 consumer proof -> D 有效 producer+同根 proof/watermark 验证 -> 才允许目标 BAPI GET/emit。producer 未就绪不阻止普通 D READY/F bootstrap，防止互相等待死锁；bootstrap-only summary 不等于有效运行 consumer proof。
4. 复用 F watermark 的 `bootstrap_source_root`、`bootstrap_root_id` 及既有创建时间/seen 字段；在确定的 consumer root 下用 strict loader 校验 watermark 存在且 bootstrap 身份/源与绑定新 D/F 根一致，不以 sleep、文件存在或操作员口头声明替代。需要跨现有 proof 调用传入的新上下文用显式参数，不放入 ambient globals。保留 commit/manifest/hash/进程实例/heartbeat/sticky 校验；受保护源清单如遗漏本次依赖文件，仅在现有 D runner 的 manifest 声明中补齐，不删旧保护项。
5. 目标 GET 重新获得当前可信正文及 API 产品身份；exact 候选集、官方 anchor 在未来且满足既有 14d lead 才写新 formal v2 launch/index。原发布时间不变，新 detected/fetched 取实际重新核验时间。默认历史 catalog 仍隔离，目标不能被普通路径抢先 emit；同页未来恢复不假造一条“已与旧 index 关联”的 revision。
6. 事件使用原有身份/dedupe 算法，marker 精确为 `explicit_future_launch_revalidation_v1`；F 必须同时核对 marker、已绑定选择、article/symbol、新正文与正式 v2 时间。普通 moving watermark 被其他新事件推进后仍可按此限定 future-anchor 分支接纳，但 bootstrap seen、已受理/terminal 身份不豁免；发生提前 seen 时报告启动失败，不清空、不自动换根。
7. state/accepted/summary 消费链中，恢复始终 `evidence_start_class=recovery_start`、`live_depth_evidence_basis=recovery_validation_only`、admission/latest max class=`recovery_validation_only`；source contract/hash 不动，admission/latest hash 按既有 builder 从降级后字段生成。保留 15m late-start、容量/交易状态与最新官方+12h 终点，防旧 recovery helper 早退。无 marker、未知 marker、第三 symbol、旧根、过期 proof、错 D/F 源、缺 bootstrap、producer disabled、错过 15m 均反向验证。

```bash
"${PYTEST[@]}" "$D_RUNNER_TEST" "$F_RUNNER_TEST" \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py -k postponement
```

GREEN `RC=0`；真实 main/poll+临时目录/临时 Git 证明链至少完成一次 bootstrap -> proof -> revalidation -> future pending -> TRADING recovery start，并验证恢复请求在 consumer 未就绪前为 0。旧根临时副本哈希前后一致；不得用直接 helper 调用拼接顺序代替这一入口断言。

### Task 5：操作手册、回归与独立完成审计交接

**Dependencies：**Task 1–4。对应全部 `INV-*`。**修改文件：**仅白名单 runbook；行为测试补强仍限原九个测试文件。

1. 在既有手册加本次操作分支：producer 默认 disabled、代码 proof commit 与后续仅四项 enablement 配置的证明关系、真实 AIA 与本次同页样例分别核验、明确新 RUN_ID/绝对 D/F 根/互指 proof 路径。禁止用 `find ... | tail -1` 隐式选择恢复根。运行命令准备不等于授权执行。
2. 写清 Task 4 启动顺序、旧根保留、7 天 D 截止只是切换/空窗风险而非改全局期限理由；新批次寿命需覆盖最新官方终点+既有 12h。当前条件性目标为 11-16 20:35 UTC，官方改期则重新核验，不硬编码启采。deadline/存储/proof/source 冲突则停止对应恢复，不能强制 active 或补造旧数据。
3. 补一个受授权控制、可实际运行的真实来源测试入口：在 D runner 测试文件中命名 `test_postponement_real_source_contract_when_authorized`。未提供外置来源时明确 skip；经用户明确授权后以 `STAGE15_POSTPONEMENT_REAL_FIXTURE_DIR` 指向原始字节及现有 request manifest/version 记录的只读副本，进入真实 parser/strict writer/consumer 链；元数据不全、hash 不符或语义不支持时应 fail，禁止无条件 skip。此环境变量只是定位，不是授权；不新增授权系统、不联网取数、不修改 AIA 状态。具体真实来源前提见 §7。
4. 按下面命令跑回归/静态门禁。读取实际 diff、cached diff、未跟踪项与 Task 0 快照比较；审核新字段/CLI 的全部消费方，不以 `git diff` 空就称没有修改。保留旧根 hash 证据和 approved Design/Plan 字节不变。

```bash
"${PYTEST[@]}" \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5d_*.py \
  tests/research/external_signal_shadow/test_stage1_5f_*.py \
  tests/research/external_signal_shadow/test_stage1_5g_*.py \
  "$D_RUNNER_TEST" "$F_RUNNER_TEST"
.venv/bin/ruff check --no-cache configs/base.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py \
  src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py \
  src/research/external_signal_shadow/stage1_5d_runtime_gate.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  "$D_RUNNER_TEST" "$F_RUNNER_TEST"
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
git -c core.fsmonitor=false diff --check "$BASE_SHA"
git -c core.fsmonitor=false diff --cached --check
git -c core.fsmonitor=false diff --name-status "$BASE_SHA"
git -c core.fsmonitor=false diff --cached --name-status
git -c core.fsmonitor=false status --short --untracked-files=all
shasum -a 256 "$PLAN" "$DESIGN"
.venv/bin/python - <<'PY'
from configs import base
assert base.RISK_LIVE_TRADING_ENABLED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA == ""
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_RECHECK_INTERVAL_SEC == 600
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_RECHECK_BUDGET_PER_POLL == 1
PY
```

预期所有命令 `RC=0`；测试报告应区分实际通过/skip/未授权未执行，不能把真实样例 skip 算作来源已验证。核对 base diff 只新增两常量、runbook 引用/参数/顺序与实现一致，Plan/Design SHA 仍为批准值；scope 比对还须包含未跟踪文件，`diff --check` 不能替代此项。

交付实际增改删路径、各 RED/GREEN/回归命令及 RC、基线目录、source/Plan/Design 身份、复用实际调用位置、未决真实门禁。由独立会话按 `audit-plan-completion` 复核；执行者不得自审宣布 COMPLETE。

## 5. Task / 不变量证据矩阵

命令中的 `PYTEST`、runner test 变量由 Task 0 定义；目标测试均不能零选中。

| Design 不变量 | 实施 Task | 必须交付的证据 / 对应验证命令 |
| --- | --- | --- |
| `INV-01` | 0、1、2、4、5；实际操作另见 §7 | Task 0 双身份/基线命令；Task 4 旧根临时副本前后 hash、terminal 不复活；Task 5 base 断言及范围检查。真实旧根保全不能由合成副本替代 |
| `INV-02` | 1、4 | Task 1 四文件 `-k postponement`；Task 4 入口验证恢复仍检查状态/时间/容量，depth 调用数独立断言 |
| `INV-03` | 1、3、4 | Task 1 冲突六阶段/2m/15m/6h Oracle；Task 3 最新修订；Task 4 15m 不绕过，官方+12h 不后移 |
| `INV-04` | 2 | Task 2 两文件 `-k postponement`：raw -> manifest -> pending reload -> event/index 精确字段对账 |
| `INV-05` | 3 | Task 3 五文件 `-k postponement`：600s/1槽/保底/14d、最新 S、TRADING 但冲突仍 watch、terminal 不再次 launch |
| `INV-06` | 3 | Task 3 真实 runner transport 到 F registry 单次应用、canonical 验证和负向变异；真实官方样例另见 §7 |
| `INV-07` | 4 | Task 4 七文件 `-k postponement`：gate/root-contract/watermark 往返、启动顺序、moving watermark 受限例外、证据字段/hash 降级 |
| `INV-08` | 3、4、5；真实启用另见 §7 | Task 3/4 真实 poll 接线和临时 Git/consumer proof；Task 5 全套回归与 scanner；未授权的真实 proof/观察保持未验收 |

## 6. 偏差分流与停止条件

- `BLOCKED_IMPLEMENTATION_DEFECT`：批准语义明确、可在白名单内修正，留在对应 Task 用 RED/GREEN 修复，不为普通代码缺陷重写 Design。
- `BLOCKED_SCOPE_DRIFT`：只需新增实现/测试/文档路径而未改冻结契约，先停止越界修改；按 L1 §3.2 提交绑定原 Plan SHA 的有限增补，B 与用户批准后重验受影响 source bundle/proof/RUN_ID/证据绑定。不能因为现有文件多就默认白名单可扩张。
- `BLOCKED_SPEC_DRIFT`：若需改变 official/API 优先级、身份/去重算法、terminal/窗口、proof/profile 或恢复权限，列出 Failed Invariant、Upstream SSOT、Contradiction Proof、Proposed Delta，停止受影响工作并返回 Design/Plan 链。
- 真实旧 raw 无法取得、AIA fixture 缺失、consumer proof 不满足、已错过 future/late-start 窗口，均诚实记录门禁未达成；不假造来源、不提高超时、不循环换根制造成功。旧 D 到期不是放宽任何门禁的理由。

## 7. 单独授权后的真实来源、启用与新批次验收（非编码批准权限）

以下不是 Task 0–5 自动执行步骤，也不因本 Plan 获实施批准就取得权限。Task 5 手册需把这些前提列为阻断；后续只有用户明确授权适用的真实读取/提交/部署/运行操作后才可执行。

1. **真实 fixture：**精确取得/只读核验旧正文、新正文和当前 API 原始字节，保留实际 URL/抓取时间/版本首观测/SHA 与 request manifest；旧正文预期身份为 Design 所列 `97710e4b...1947d`，不能从 evidence.txt 重拼。若旧正文缺失，不能称“两版真实来源测试通过”；分别报告已验证新版和缺口。AIA 既有 `aia_postponement_metadata.json` 目前 `data_quality=missing_real_fixture`、PIT 未验证、enablement blocker=true，仍需独立真实核验，不能由本事故样例替代。
2. **可运行验证入口：**获得上述消费授权后，运行 `STAGE15_POSTPONEMENT_REAL_FIXTURE_DIR="<授权的精确目录>" "${PYTEST[@]}" "$D_RUNNER_TEST" -k postponement_real_source_contract_when_authorized`，预期 `RC=0` 且该正向测试实际 passed（skip 不达标）。若输入不满足真实来源/哈希/时间/语义要求则非零；不得自动下载补齐。AIA 原有 prerequisite 另验，不用本测试的 pass 自动设置其 flag。
3. **启用证明：**先独立代码审计，再另获提交/配置/部署授权。沿现有 prerequisite proof commit ancestry、受保护树、四项配置 allowlist、真实 fixture/Part A、匹配 F 进程与新鲜 heartbeat 形成证明；真实源码清单与批准源包对账，不删减 proof。未经这些操作授权及客观证明，不修改任何启用字段。若曾获有限范围增补，先按 L1 §3.2 重验所有受影响身份。
4. **新根顺序：**操作批准明确新 RUN_ID、绝对 D/F 根和 exact recovery 选择；保全旧根精确 manifest/hash。新 D 发布绑定选择且暂不恢复请求，新 F bootstrap 后常规运行，D 核对同根运行 proof/watermark 后才 fresh revalidation。无需跨根 curated snapshot，不迁移旧 `completed`；失败保留诊断，不自动换根。
5. **运行结果：**当前官方计划/API 重新取得，等待真实 TRADING 后才采集；核验两 symbol 各自实际开始时间、有效盘口/无效盘口数、固定窗口终点、revision registry 与所有恢复上限/hash。任一前提不符或 storage/proof/source 失效则阻断，延期则按合法修订更新而非强行在 11-16 开采。旧及新数据仍需原 1.5G 独立准入，覆盖率/HTTP 成功不替代质量。

## 8. 完成与审查边界

本 Plan 预期分别交付三种状态，禁止混为一句“恢复成功”：**代码与合成测试已核验**、**真实来源及启用证明已核验**、**新批次目标观察已核验**。只有前者完成而后两者未执行时，独立审计可以仅就已授权编码范围作结论，必须明确整体观察目标尚未验收。

本文下一步为 B 独立 Plan 审查及用户精确 SHA 实施批准，不自动进入执行。任何 `complete` 只代表满足所声明且已批准的范围，不自动授予 commit、push、deployment、SSH、runtime、paper 或 live 权限；`RISK_LIVE_TRADING_ENABLED=False` 始终保持。
