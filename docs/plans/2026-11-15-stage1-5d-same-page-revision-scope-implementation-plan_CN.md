# Stage 1.5D 同页改期范围收窄 Implementation Plan

状态：Draft，待 Model B 审查与用户按本 Plan 精确 SHA-256 批准。L2 不适用：只修只读采集，不涉及 Alpha、交易或研究口径。

## Allowed Change Scope

| 类别 | 精确范围 |
| --- | --- |
| Allowed implementation paths | `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` |
| Allowed verification paths | `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`；`tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py` |
| Allowed documentation paths | `docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md`，仅 §9.2 的行为与启用证据说明 |
| Allowed generated/runtime artifacts | 仅本机新建 `/private/tmp/stage15-same-page.*` 内合成 fixture、pytest 临时根和验收日志；生产 runtime 产物：none |
| Affected but unchanged | 共享 D parser、scheduler、正式身份索引/修订 transport、v2 anchor contract、Git/受保护树证明、F runner/loader/state/registry、1.5G 消费与冻结契约、配置和旧 AIA 证据。Task 1–4 验证调用边界；§5 另验启用证明。 |
| Forbidden | 白名单外修改；修改任何批准文件、旧运行根/日志或冻结哈希；新依赖、队列、Schema、持久化字段、API、News 订阅、独立 Verifier；受限实源读取、联网、真实生产运行、Git 暂存/提交/push、部署、SSH、采集启停、execution/paper/live；禁用 `ruff check --fix .`、`git clean -fdx` 等全库或破坏性命令。 |

**Goal：** 不再主动为独立改期/延期/取消通知抓取详情或发射事件；普通公告、可信同页修订、F 就绪和显式新根补采契约不变。接受只在独立通知公布新时间时漏采；接受原页未变时在既有冷却和固定到期内的有限无效重查。

**方法：** 在 D runner 的行动入口和已有可恢复状态做窄筛选；把已持久化正式事件与现有本根索引对账后，才允许进入已有同页选择及 canonical writer。复用现有 CLI 测试、pytest/Ruff 与 strict consumer，不修改共享 parser 或 F 来满足本轮断言。验收不等同于启用。

## 1. 绑定与执行前冻结（Task 0）

获批 Design：`docs/designs/2026-11-15-stage1-5d-same-page-revision-scope-design_CN.md`，SHA-256 `08fdc6c4af79a0aaf93033c94b6cc95dd39ae67cdd781dfbeb1049ab6c2b8176`。父契约按该 Design §2 的三个 SHA 与原热修复 Plan SHA 核对；V3 恢复另以 `docs/designs/2026-09-01-external-signal-shadow-lab-stage1-5d-historical-catalog-re-admission-hotfix-design_CN.md` §D-05（SHA-256 `6a5fbf17d3acbb8e3f7a977cdd46c1f9e2a3516813c3dc3934e590c59e29155b`）为只读约束。起草时源码 HEAD 为 `ea4b3142364245a5429d8ea10c8ace72c1a9d5dc`；不能代替执行时实际 `BASE_SHA`。

依赖：独立 Plan 审查推荐批准、用户明确批准当前 Plan 与绑定 Design。文件：只读上述契约及配置。以下命令在仓根使用 Bash；把用户实际批准的完整 Plan SHA 通过 `APPROVED_PLAN_SHA` 传入，不得从当前文件反向填值。

```bash
set -euo pipefail
ROOT=$(pwd -P)
DESIGN=docs/designs/2026-11-15-stage1-5d-same-page-revision-scope-design_CN.md
PLAN=docs/plans/2026-11-15-stage1-5d-same-page-revision-scope-implementation-plan_CN.md
DR=scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
DT=tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
FT=tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
OPS=docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md
T=tests/research/external_signal_shadow
H() { shasum -a 256 "$1" | cut -d ' ' -f 1; }
[ -n "${APPROVED_PLAN_SHA:-}" ] &&
  [ "$(H "$PLAN")" = "$APPROVED_PLAN_SHA" ] &&
  [ "$(H "$DESIGN")" = 08fdc6c4af79a0aaf93033c94b6cc95dd39ae67cdd781dfbeb1049ab6c2b8176 ] ||
  { echo STOP=approved_authority_mismatch >&2; exit 1; }
W=$(mktemp -d /private/tmp/stage15-same-page.XXXXXX)
g() { git -c core.fsmonitor=false "$@"; }
BASE_SHA=$(g rev-parse HEAD)
printf '%s\n' "$BASE_SHA" > "$W/BASE_SHA"
shasum -a 256 "$DESIGN" "$PLAN" configs/base.py > "$W/bound-files.sha256"
snapshot() {
  local phase=$1
  g status --porcelain=v1 --untracked-files=all -z > "$W/$phase.status"
  g diff --cached --binary --no-ext-diff > "$W/$phase.index.patch"
  g diff --binary --no-ext-diff > "$W/$phase.worktree.patch"
  g ls-files --others --exclude-standard -z > "$W/$phase.untracked"
  while IFS= read -r -d '' p; do shasum -a 256 "$p"; done \
    < "$W/$phase.untracked" > "$W/$phase.untracked.sha256"
}
snapshot before
unset STAGE15_POSTPONEMENT_REAL_FIXTURE_DIR STAGE15_SAME_PAGE_REAL_EVIDENCE_DIR
export PYTHONPATH="$ROOT/src:$ROOT" PYTHONDONTWRITEBYTECODE=1 PYTEST_DEBUG_TEMPROOT="$W"
pt() { .venv/bin/python -m pytest -q -p no:cacheprovider "$@"; }
```

将父 Design/Plan（按 §2 逐个比较）的实际哈希、配置安全值及四个白名单路径的初始状态保存到 `$W`；身份错误立即停止，白名单若已有不属于本任务的变更先报告，不覆盖。先在 BASE 运行 Task 3 的 F 入口基线与 Task 4 的相关既有回归，留存命令、节点、实际 RC、失败原因；新增节点此时不属于基线。已知旧断言与新要求冲突，仅按 Task 1/2 定向更换，不视为可任意排除的失败。

## 2. Task 1：阻断独立通知，保留普通上新（INV-01）

依赖：Task 0。文件：`$DR`、`$DT`。

- **RED：**在实际 D runner poll 用原始列表及可追踪请求的现有测试 stub 驱动三类明确主句（`Will Postpone/Reschedule/Cancel the Launch of …`）及 `USDⓈ-Margined`；改期正文 fixture 带明确新时间。对照 `Will Launch …` 附旧延期背景。断言独立项零详情调用、零普通事件、零正式修订，普通对照仍走正常上新，原始列表请求、响应及 manifest 计数不被重写。
- **GREEN：**用 D 入口窄守卫拦截明确独立主句，覆盖普通候选、first-bar/pending/详情及正式 emit 通路；保留原始列表行。移除独立标题主动入队及生产可信正文分支对 `process_trusted_schedule_revision_detail` 的调用；不删仍用于 transport/历史兼容测试的 helper。不把当前标题作为已合法创建的同页重查的准入条件。原 `test_runner_emits_revision_only_after_durable_launch_in_same_poll` 被新合同替代的生产期望改为负向，保留正式普通上新成功断言及其余 helper/consumer 测试。
- **保留的边界：**普通首次详情、已有人工恢复授权、列表解析与 raw 证据格式不变。保护范围是 D runner 的行动入口，不把标题是延期的任意字样当作全局禁入。

```bash
pt "$DT" -k 'same_page_scope_d_independent_titles or same_page_scope_d_no_cross_article_emit'
```

预期新增两个测试族在修正前因目标行为而失败，修正后 `RC=0` 且均执行；不是靠 skip 或不收集。遗留和预算场景由 Task 2 共同封口。

## 3. Task 2：本根身份、恢复公平及 canonical D→F 修订（INV-01、INV-03）

依赖：Task 1。文件：`$DR`、`$DT`，必要时在 `$FT` 补共享消费断言，不改 F 源码。

- **RED：**用普通 D 路径的 canonical 正式 event 及逐 symbol index 构造正常根，验证同版本恢复非零个已完成身份；冻结同一 poll 含独立旧项（未尝试、已尝试待重试及误分普通）、合法到期同页工作和新的普通首次详情。故障注入逐个改变 root、event、稳定身份、每 symbol hash/旧锚点/正文 hash、遗漏或重复 index、晚于决策的时钟或只剩 snapshot。断言无资格者在候选排序前拒绝、零详情请求/正式发射，单轮同页与首次详情的既有保底都成立。
- **启动证据：**`preflight_stage1_5d_v3_root` 的索引读取目前按 `symbols` 聚合字段取投影；`record_formal_futures_launch_event` 通过 `build_formal_launch_identity_index_rows` 实际写逐行 `symbol`。按 V3 D-05 修正本地读侧，用严格正式 launch event 与完整逐 symbol 投影对账，再进入原 exclusivity/inflight 条件判定。不可把同页额外资格（可核验的旧正文 hash 等）误作所有普通事件的 V3 恢复条件。复用同一启动/事件读取证据供该判定和首轮身份使用；不写转换文件、不补造索引、不把启动后的 `rebuild_missing_formal_launch_identity_index` 当成前置证明或允许 V3 修复残缺提交。
- **轮内证据：**复用已有 `events/*.jsonl` 同页选择读取，在该遍历中只对本轮候选提取可信 `futures_contract_launch` 行；以 `validate_launch_anchor_contract(..., compatibility_mode=False)`、canonical index 构造器与 `load_valid_formal_launch_identity_index` 提供的本地行/冲突证据完成局部对账，不另加每篇或每轮全树扫描。对每个文章要求恰一正式事件、完整且每 symbol 唯一的 durable index，匹配本根 ID、生产提交、event ID、稳定身份、官方锚点、anchor contract hash、原正文 hash，且首观测/持久化时间可信、不晚于本轮。索引行的根绑定用既有 writer 口径；没有字段不得补默认值。外置 snapshot 不用于证明本根身份，也不能替换或修补缺损的本根行；保持原 CLI 和历史其他消费边界。
- **恢复与预算：**沿用根/provenance、scheduler 兼容和旧状态加载，先排除遗留独立项及没有本轮资格的旧修订可请求项，再去重、候选排序及调用 `select_detail_retry_attempts`；从已对账的同页 watch 重新派发，不延长期限、不重置冷却、不让旧重试绕过门禁。断言原事件首观测起 14 天、600 秒冷却、每 poll 上限 1、共享详情/HTTP 上限、首次详情保底；到期、历史取消、冲突或交易状态与当前有效计划达到既有停止条件时不再调度。验证实际请求计数（含未发出与失败请求的语义），而非把“选中”当请求；失败不能绕过已有重试/冷却约束。
- **正式发射：**保留 `record_payload_version_first_observed`、`select_latest_applicable_official_schedule`、`detect_and_emit_same_page_schedule_revision`、`append_formal_schedule_revision` 与已有语义 ID 恢复。只有本轮合法 recheck context、可信正文、完全相同 symbol 集及官方时间严格延后才发射，旧首版 payload 绑定 durable event，后续版本依已有合法修订/版本证据；不从 exchangeInfo 或未证实 watch 伪造。用现有 F 入口实读 D 输出，校验两个 symbol 各自新旧毫秒值、available-at、应用次数与 identity。覆盖 disabled/前提未满足、正文/锚点不满足、重复回放/重启、旧锚点拒绝和原显式新根补采边界。固定事件、时钟、期望锚点和调用次数由用例独立给出，不由待测逻辑反算。
- **最小性与停机：**保留原有恢复拒绝矩阵；原来以测试字典同时手写 `symbol` 和 `symbols`、但不写实际 event 的案例不得再作为跨边界正证。读侧适配不改任何 persisted schema，不加二级索引或全历史重扫；若已有读取路径不足以有界核实，或严格 F 消费/恢复要求改变上游契约，先按 Rule 16 停止。测试不替换被检验的资格判定、writer 或 F loader。

```bash
pt "$DT" "$FT" -k 'same_page_scope_d_resume or same_page_scope_d_retry_budget or same_page_scope_df_revision or preflight_stage1_5d_v3_root or future_launch_recovery'
```

预期新增三测试族先以目标原因 RED，再与原阳性/阴性一起 `RC=0`，有独立的 F 持久化应用证据。另在 `$FT` 的同一 D→F 验证接线上加 §5 的显式外置实源入口；本轮验证其未授权不读取（仅该可选实源节点明确 skip），不制造新的 archive harness 或复制生产校验。

## 4. Task 3–4：F 不变回归、范围与验收

### Task 3：不同文章的 F 证据归属（INV-02、INV-03）

依赖：Task 0 可先表征；Task 2 完成后与 D 一起重验。文件仅 `$FT`。

从 canonical D writer/fixture 生成不同 article ID、同 symbol 的两个正常 launch，走实际 F 入口。独立给定 `S0=10:00`、`10:07` 发现并持久化新公告、`S1=10:10`。S0 未 TRADING 时零深度；S1 提供新鲜 `TRADING + onboardDate=S1`，超过 60 秒但仍在旧 15 分钟内，旧 waiting/pending 保持冲突无新 depth，只有合格新事件以 S1 接纳并写新事件盘口。旧 active 继续原窗口/证据，不修改旧状态或冒名；分别测试有余容量和全局容量不足（按既有容量逻辑延后或拒绝，不绕过），终态不假去重、不复活。检查请求对应的事件上下文及 accepted/latest/depth/completed 行身份，不把交易所相同 symbol 的请求次数当归属证明。缺乏可区分的新鲜时间证据时，没有“最新公告优先”保证，不给排他性断言。可做保持行为的 GREEN 表征，不强造 RED；如果限定反例无法通过，不改 F，按 Rule 16 报告。

```bash
pt "$FT" -k 'same_page_scope_f_article_isolation or same_poll_schedule_revision_prevents_stale_launch_admission or future_launch_recovery'
```

预期 `RC=0`，新矩阵全执行，覆盖各旧状态和容量分支及 §3.1 的明确时间冲突。如基线旧行为便不满足，停，不通过修改测试期望承接。

### Task 4：最小文档、回归及独立审计交接（INV-01 至 INV-04）

依赖：Task 1–3。文档文件仅 `$OPS` §9.2。写明收窄版本仅同页、何时允许漏采和 14 天有界残余请求；旧 AIA 证明及门槛不追溯改写；§5 未验证仍不得启用，保留 §9.1/§9.3 操作和补采权限边界。轻量核对本地链接、实际选项名称和文档 diff，不强设伪 TDD。

```bash
pt "$DT" "$FT" \
  "$T"/test_stage1_5_launch_anchor_contract.py \
  "$T"/test_stage1_5d_live_event_source_parser.py \
  "$T"/test_stage1_5d_live_event_source_collector.py \
  "$T"/test_stage1_5d_live_event_source_storage.py \
  "$T"/test_stage1_5d_detail_retry_scheduler.py \
  "$T"/test_stage1_5d_schedule_revision_producer.py \
  "$T"/test_stage1_5f_live_depth_observer_loader.py \
  "$T"/test_stage1_5f_live_depth_observer_state.py \
  "$T"/test_stage1_5f_schedule_revision_registry.py \
  "$T"/test_stage1_5f_live_depth_observer_watermark.py
.venv/bin/ruff check --no-cache "$DR" "$DT" "$FT"
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
g diff --check
g diff --cached --check
test "$(g rev-parse HEAD)" = "$BASE_SHA"
shasum -a 256 -c "$W/bound-files.sha256"
snapshot after
cmp "$W/before.index.patch" "$W/after.index.patch"
.venv/bin/python - <<'PY'
from configs import base
assert base.RISK_LIVE_TRADING_ENABLED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA == ""
PY
```

命令期望 `RC=0`，分别保存实际退出码和日志；pytest 中任何 skip/xfail 必列节点与原因，已有和新增明确 opt-in 实源节点的未授权 skip 不算真实验证，新增合成节点不得 skip/xfail。按前后快照核对 staged、unstaged、untracked 差异均在四路径内，其他文件未动；交付实际调用/适配位置、RED/GREEN、各不变量证据与运行目录。只验明确列出的调用面，不拿上轮 R1 例外清单豁免失败，也不宣称全仓或 1.5G 运行已通过。

| Design 不变量 | 机械验证和交付证据 |
| --- | --- |
| `INV-01` | Task 1 poll gate + Task 2 恢复/预算节点，Task 4 回归；比较详情 URL 计数、候选输入、durable 事件及 raw/manifest 对照 |
| `INV-02` | Task 3 F 矩阵，Task 4 回归；按事件身份、官方锚点与现有窗口核对输出 |
| `INV-03` | Task 2 D→F 实接线、Task 3/4 旧锚点和显式新根补采回归；比对 v2 严格消费、重复应用数与负向阻断 |
| `INV-04` | Task 0/4 合同身份、配置断言、范围差异及 §9.2 文档；后续适用 Part A、实源、Git 与 F 运行证明由 §5 再验，不能在本次宣告已满足 |

Rule 15：仅内部逻辑和故障注入可用手写最小输入；跨模块正向以 canonical constructor/writer/strict loader 建立，外部请求与钟在边界可注入。Rule 17：本 Plan 不生产权限产物、不改 schema，不新增或复用其他冻结 profile；现有 v2 结构检查加独立语义期望及 F 消费，保留现有 Git/消费者证明，不另造 Verifier。Rule 16：白名单内实际实现偏差用 `BLOCKED_IMPLEMENTATION_DEFECT` 定向修并重验；仅增加文件/任务则 `BLOCKED_SCOPE_DRIFT`，先审定并获准有限增补，重验受影响身份/源码包/运行证据；变更冻结语义、F 契约或持久化生命周期为 `BLOCKED_SPEC_DRIFT`，返回 Design。不得靠放松门禁、刷新哈希或隐藏失败过关。

执行者交独立 Completion Audit（`.agent/skills/audit-plan-completion/SKILL.md`），不得自审 `complete`。完成仅指授权的代码、合成测试及文档；不授权提交、实源回放、生产启用、部署或交易。

## 5. 后续启用证据（不在本 Plan 的执行授权内）

1. **版本和 Part A：**独立代码验收后，另行授权 proof commit，冻结实际受保护树和 Part A 日志身份。按 `docs/plans/2026-08-07-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-and-1-5f-lineage-closure-implementation-plan_CN.md` 的 Part A Tasks 1–4 原命令在该候选版本逐项复核（含其 1.5G integrity 节点）；保留真实 RC，不因本次不改 1.5G 就宣告既有 Part A 已通过。不得套用旧验收记录，不修改既有 profile 或冻结哈希。
2. **HYPE/TRX 实源：**另获明确的外置证据读取及本地离线执行授权后，按批准身份绑定归档 manifest、旧/新 BAPI 正文、新版同批 exchangeInfo、来源 URL、抓取时间和完整摘要。复核公告 `2d89a5966b174a2689ab2c2a15db1757` 的两个 symbol 和旧 UTC `11-11 09:30/09:35`、新 UTC `11-16 08:30/08:35`。有源证据约束的回放时钟，用捕获依据标记版本可得时间；不把新版回填到旧时点，不用新版 API 冒充旧版同批数据或验证真正 TRADING。其实际输入证明不足即失败。F 验的是正式修订应用，不宣称取得盘口或 11 月 16 日补采成功。
3. **实源入口约定：**Task 2 的 `test_same_page_scope_real_revision_when_authorized` 使用相同生产 D/F 调用链和 canonical 收发。将应授权的归档目录由执行者传给 `STAGE15_SAME_PAGE_REAL_EVIDENCE_DIR`，并运行下方显式命令；正向必须实际 `1 passed, RC=0`，单版本 parser pass 不算。获准后不可将路径、hash、来源、PIT 缺失或消费者无输出变成 skip。此环境变量只是定位，不是授权；不联网、不补缺失生产证据。合成注入的运行外部依赖单列，不冒充真实启动或通过真实消费者运行证明。
4. **启用及运行：**仅本 Delta 批准且独立验收版本不再以 AIA 为启用先决条件；旧元数据不改、不宣称 AIA 通过。以现有 Git ancestry/受保护树 proof、独立实源、Part A、新鲜 F 根契约/summary/同根 watermark 与实际代码/进程绑定为前提，另行审批配置提交、部署及启动。任何前提未满足继续关闭；不复活旧终态，不改变现有 `recovery_validation_only` 或为这两个合约补开已过期窗口。

```bash
# 仅在单独精确授权之后，从候选 proof commit 的工作树运行：
: "${APPROVED_REAL_EVIDENCE_DIR:?requires separately approved evidence directory}"
STAGE15_SAME_PAGE_REAL_EVIDENCE_DIR="$APPROVED_REAL_EVIDENCE_DIR" \
  pt "${FT}::test_same_page_scope_real_revision_when_authorized"
```

下一步：Model B 审查本 Plan；用户核对并批准精确 Plan SHA 后，Model C 才能执行 Task 0–4。
