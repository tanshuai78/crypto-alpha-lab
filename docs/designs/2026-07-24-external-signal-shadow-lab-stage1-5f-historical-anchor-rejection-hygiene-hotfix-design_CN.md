# Stage 1.5F Historical-Anchor Terminal Ignore / Rejection Hygiene Hotfix Design

```text
status = design_draft
scope = stage1_5f_historical_anchor_terminal_ignore_and_rejection_hygiene_hotfix
design_owner = human_research_owner
implementation_allowed = false
implementation_plan_allowed = after_design_review_only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

## 1. 背景

Stage 1.5F launch-time gated observation hotfix 已经修复一个关键风险：不再因为公告捕获时间早于真实上线时间而提前采集 pre-launch empty book。

新 root 部署后，生产检查发现 1.5F 没有错误启动盘口采集，但 `events_rejected` 持续写入大量 historical-anchor rows：

```text
root = live_depth_observer_20260723T160251Z_7d_bapi_detail_and_launch_time_gate_hotfix
active_observation_count = 0
post_watermark_events_accepted = 0
pending_launch_observation_count = 0
pre_watermark_events_ignored = 39455
events_rejected total = 5467
missing_identity_rows = 5467
reason_counts = {"MISSING_REASON": 5467}
```

两分钟内 rejected rows 从 `5431` 增至 `5449`，说明旧事件 admission terminal path 仍在持续重复落盘。

抽样 row：

```json
{
  "symbol": "GLWUSDT",
  "event_id": null,
  "source_article_id": null,
  "rejected_reason": null,
  "status": null,
  "detected_at_ms": null,
  "observation_anchor_ms": 1781170200000,
  "event_age_ms": 3685540115,
  "watermark_max_seen_detected_at_ms": 1784822376255
}
```

这不是 depth evidence 污染；当前没有 active observation，也没有 depth snapshot 写入。但这是审计质量、分类语义和幂等性问题。

## 2. 触发样本

部署后曾出现 `pending_anchor_conflict` 的旧 TradFi symbols：

```text
EBAYUSDT:
  source_article_id = f598c7bb87d74b8c995b9f67bf210be1
  detected_at_ms = 1784822376255
  detected_utc = 2026-07-23T15:59:36.255Z
  symbol_effective_launch_time = 1780995600000
  exchangeinfo_current_onboard_time = 1780996800000
  disagreement = 20min

ASMLUSDT:
  source_article_id = f622c1f2a1a94ba1894d9a9e265fb4b9
  detected_at_ms = 1784822376255
  detected_utc = 2026-07-23T15:59:36.255Z
  symbol_effective_launch_time = 1781169300000
  exchangeinfo_current_onboard_time = 1781170800000
  disagreement = 25min
```

这些 anchor 分别对应 2026-06-09 / 2026-06-11，明显早于当前 root bootstrap watermark。它们从未具备当前 root 的 live depth evidence admission 资格。

正确语义不是 normal rejected candidate，而是：

```text
terminal ignored_historical_anchor_pre_bootstrap
consumable_by_stage1_5g = false
no events_rejected row by default
no pending_anchor_conflict
no depth observation
no watermark promotion
idempotent within current output root
```

## 3. 根因

当前 Stage 1.5F 存在三个独立问题。

### 3.1 Historical Pre-Bootstrap 被混入 Normal Rejected

historical anchor 事件与真正 admission failure 语义不同：

```text
historical/pre-bootstrap anchor:
  当前 root 外的历史事件；应 ignored/out-of-scope。

normal rejected:
  当前 root 的 post-bootstrap candidate；已经进入 admission，但因 age exceeded / unsafe schema / terminal admission failure 被拒绝。
```

如果 historical rows 进入 `events_rejected`，1.5G 的 rejected denominator 和人工根因统计会被历史目录数据主导。

### 3.2 Rejected Row Schema 不完整

runner 的 rejected 分支使用 ad-hoc dict 写入 `events_rejected`，并使用 `rejection_reason` 字段。运营检查与后续审计读取 `rejected_reason/reason` 时会误判为 `MISSING_REASON`。

同时现有 rejected writer 没有直接透传完整 `flat_event` identity，生产输出中 `event_id/source_article_id/detected_at_ms` 为空。implementation plan 必须先做 root-cause preflight，确认是 writer 丢字段、检查脚本投影错误，还是存在多条 writer path。

### 3.3 Terminal Admission State 缺少幂等持久化

Stage 1.5F 对 `event_symbol_id in states` 有幂等保护，但 terminal ignored/rejected 不一定写入 durable `observer_state.jsonl`。因此同一旧 event-symbol 可能在后续 poll 或 restart 后再次 classify 并再次写 audit row。

## 4. 设计目标

本 hotfix 只修 Stage 1.5F terminal ignore / rejected audit hygiene，不改变采集策略。

必须达到：

```text
1. historical/pre-bootstrap anchor 进入 terminal ignored_historical_anchor_pre_bootstrap，而不是 normal events_rejected。
2. historical/pre-bootstrap anchor 不进入 pending_anchor_conflict，不启动 depth observation。
3. terminal ignored/rejected 都写 durable state，后续 poll/restart 幂等跳过。
4. 真正 post-bootstrap normal rejected row 必须具备完整 identity 和 rejected_reason。
5. malformed identity 不进入 events_rejected，只进入 diagnostic stream。
6. diagnostics 不成为新的无限增长源。
7. 1.5G 不需要修改 decision 逻辑；新 diagnostic rows 不被 1.5G 消费。
```

非目标：

```text
不放宽 MAX_ANCHOR_DISAGREEMENT_MS。
不把 20-25min TradFi anchor disagreement 视为正常。
不修改 1.5D BAPI/detail parser。
不修改 1.5G clean/quarantine decision 阈值。
不追溯修改服务器旧 root 中已经写出的 rows。
不允许 paper/live/execution/trade/alpha。
```

## 5. Preflight：先确认真实写入路径

implementation plan 的第一步必须是只读 root-cause preflight，不允许直接重写 schema。

必须完成：

```text
1. 直接读取 10-20 条原始 events_rejected JSONL，不通过投影脚本。
2. 列出所有写 events_rejected 的调用点。
3. 确认 reason 是缺失还是字段 alias 不一致。
4. 确认 identity 是 flatten 前缺失、flatten 后丢失，还是 writer 未透传。
5. 确认是否只有 runner rejected 分支一条写入路径，还是还有 legacy/symbol-level writer。
```

preflight 产出必须写入 implementation plan 的 Task 0 验收结果。不能只修检查脚本，也不能在未确认 writer path 前批量替换逻辑。

## 6. Immutable Bootstrap Watermark

historical classification 必须依赖 root 级不可变 bootstrap watermark，不能使用 moving watermark 或 per-event admission watermark。

root 初始化时必须持久化：

```json
{
  "watermark_schema_version": 2,
  "bootstrap_max_seen_detected_at_ms": 1784822376255,
  "bootstrap_created_at_ms": 1784822584716,
  "bootstrap_source_root": "data/external_signal_shadow/stage1_5d/..."
}
```

规则：

```text
historical_anchor_classification_allowed = true
仅当 bootstrap_max_seen_detected_at_ms 存在且不可变。
```

legacy root 缺失该字段时：

```text
historical_anchor_classification_allowed = false
diagnostic = bootstrap_watermark_missing
safe_action = no normal events_rejected row
```

禁止 fallback：

```text
不得使用 admission_watermark_at_first_seen_ms。
不得使用当前 moving watermark 作为 historical cutoff。
```

如果当前 root 已经运行但缺少 schema v2 bootstrap 字段，implementation plan 必须定义安全迁移：只允许在 bootstrap-watermark-only 阶段或新 root 创建时写入；不得在运行中随 event admission 改写。

## 7. Classification 顺序

新 admission 顺序必须固定：

```text
1. source identity/schema validation
2. anchor candidate normalization
3. immutable bootstrap historical pre-bootstrap terminal check
4. anchor conflict check
5. missing/future/capacity/age admission
6. normal accepted / normal rejected
```

这样 EBAY/ASML 这类 case 会先命中 historical ignored，而不是因为 anchor disagreement 进入 pending conflict。

### 7.1 Source Identity Validation

最低 identity：

```text
stable_event_symbol_key 可构造
source_article_id 非空
event_type 非空
symbol 非空
detected_at_ms 非空
```

如果 identity 不完整：

```text
status = malformed_terminal_diagnostic
normal events_rejected = forbidden
normal ignored state = forbidden
write diagnostic once with consumable_by_stage1_5g=false
```

### 7.2 Anchor Candidate Normalization

“有效 anchor candidate” 必须先规范化：

```text
integer ms timestamp
> 0
reasonable epoch range
source validation passed
not duplicated
```

排除：

```text
None
0
negative
non-integer
明显超出合理 epoch 范围
未通过 source validation 的 onboardDate
```

### 7.3 Historical Pre-Bootstrap Terminal Ignore

新增 terminal status：

```text
ignored_historical_anchor_pre_bootstrap
```

判定：

```text
normalized_anchor_candidates 非空
AND 所有 normalized_anchor_candidates <= bootstrap_max_seen_detected_at_ms
AND delayed launch exception 不成立
=> terminal ignored_historical_anchor_pre_bootstrap
```

这里的 delayed launch exception 也必须基于 immutable bootstrap cutoff，不能内部读取 moving watermark。

如果存在任一 post-bootstrap anchor candidate：

```text
不得 historical ignore；继续进入 conflict/future/age admission。
```

## 8. Terminal Hygiene ID 与幂等

主幂等键使用 stable event-symbol identity，而不是 event_symbol_id：

```text
terminal_hygiene_id = sha256(
  stable_event_symbol_key
  + "|"
  + terminal_status
  + "|"
  + normalized_anchor_class
  + "|"
  + bootstrap_watermark_version_or_value
)
```

推荐 stable key：

```text
stable_event_symbol_key = source_article_id + "|" + event_type + "|" + symbol
```

`event_symbol_id` 仅作为审计字段，不作为主去重因子。原因：它可能依赖 event payload hash、parser version 或 revision，不能保证同一逻辑 event-symbol 跨 revision 稳定。

如果 source identity 不足以构造 stable key：

```text
不得写 normal events_rejected。
不得写 normal ignored state。
只能写 deduped malformed diagnostic。
```

malformed diagnostic 可使用 legacy fallback ID 去重，但不能把 malformed row 升格为正常 terminal state。

## 9. Durable State 与崩溃恢复

terminal ignored/rejected 必须写 durable state，建议扩展 `EventSymbolState`，避免新增并行 registry。

新增/使用字段：

```text
status = ignored_historical_anchor_pre_bootstrap | rejected | malformed_terminal_diagnostic
terminal_hygiene_id
terminal_status
terminal_reason
terminal_at_ms
consumable_by_stage1g
source_event_payload_hash
latest_event_payload_hash
bootstrap_watermark_max_seen_detected_at_ms
```

双写顺序存在崩溃窗口，因此 implementation plan 必须实现 reconciliation：

```text
state exists + audit/diagnostic missing:
  补写 audit/diagnostic row

audit/diagnostic exists + state missing:
  补写 terminal state

both exist:
  skip

neither exists:
  首次处理
```

测试必须覆盖：

```text
test_restart_after_terminal_state_write_repairs_missing_audit_row
test_restart_after_audit_write_does_not_duplicate_row
test_terminal_hygiene_id_stable_across_restarts
```

## 10. Normal Events_Rejected Contract

只有以下事件允许进入 normal `events_rejected`：

```text
post-bootstrap candidate
AND 已进入正式 admission
AND 因 anchor age exceeded / unsafe schema / terminal admission failure 被拒绝
```

新增统一 builder：

```text
build_rejected_event_symbol_row(flat_event, symbol, terminal_hygiene_id, rejected_reason, now_ms, watermark, eligibility_diag, basis_diag)
```

新 row 必须包含：

```text
audit_metadata_version = 2
state_schema_version
event_symbol_id
event_id
source_article_id
stable_event_key
stable_event_symbol_key
terminal_hygiene_id
symbol
event_type
title
detected_at_ms
available_at_ms
source_published_at_ms
source_detail_url_normalized
source_event_payload_hash
latest_event_payload_hash
rejected_reason
rejection_reason  # compatibility alias, same value
status = rejected
depth_observation_started = false
rejected_at_ms
observation_anchor_ms
observation_anchor_basis
observation_anchor_confidence
observation_anchor_candidates
observation_anchor_disagreement_max_ms
announcement_capture_age_ms
selected_anchor_age_ms
oldest_anchor_candidate_age_ms
latest_anchor_candidate_age_ms
event_age_ms  # compatibility alias for selected_anchor_age_ms only
bootstrap_watermark_max_seen_detected_at_ms
watermark_max_seen_detected_at_ms
watermark_version
live_depth_evidence_basis
consumable_by_stage1_5g = true
```

不变量：

```text
rejected_reason == rejection_reason
event_symbol_id 非空
stable_event_symbol_key 非空
symbol 非空
rejected_at_ms > 0
source_article_id / event_id 至少一个非空
detected_at_ms 非空
```

若不变量不满足，写 diagnostic stream，不写 `events_rejected`。

## 11. Historical Ignore Diagnostic Contract

historical pre-bootstrap 不写 normal `events_rejected`。只写 terminal ignored state，并最多写一次 diagnostic：

```text
historical_anchor_hygiene_diagnostics/YYYYMMDD.jsonl
```

row contract：

```text
audit_metadata_version = 1
diagnostic_type = historical_anchor_pre_bootstrap_ignored
terminal_hygiene_id
stable_event_symbol_key
event_symbol_id
event_id
source_article_id
symbol
detected_at_ms
normalized_anchor_candidates
bootstrap_watermark_max_seen_detected_at_ms
terminal_at_ms
consumable_by_stage1_5g = false
```

duplicate suppression 默认不逐事件落盘，只做 per-poll counter。允许 diagnostic samples，但必须限流：

```text
EXTERNAL_SIGNAL_STAGE1_5F_MAX_REJECTION_HYGIENE_DIAGNOSTIC_SAMPLES_PER_TYPE = 10
```

禁止把无限 duplicate suppression 写入 diagnostic stream。

## 12. Source Revision 策略

第一版锁定：terminal historical ignored state 不 reopen。

规则：

```text
same stable_event_symbol_key
+ terminal ignored_historical_anchor_pre_bootstrap
-> 当前 root 内永久跳过后续 revision
-> rejected_revision_seen_ignored_count +1
```

只有以下情况作为新候选：

```text
新的 source_article_id
或新的 symbol
或明确 post-bootstrap reschedule event identity
```

不得因为 raw payload hash 改变自动 reopen。Binance 内容修订可能只是正文/格式变化，不能让历史事件反复制造 terminal rows。

## 13. Summary 与 Diagnostics

summary 字段必须区分 gauge、per-poll count、durable total。

从 latest observer_state 重新计算的 gauges：

```text
historical_anchor_ignored_count
rejected_event_symbol_count
malformed_terminal_diagnostic_count
```

当前 poll 指标：

```text
historical_anchor_newly_ignored_this_poll
terminal_state_hits_this_poll
malformed_rows_seen_this_poll
```

durable totals 仅当从 persisted artifact 扫描或 durable counter 得到时使用：

```text
historical_anchor_duplicate_suppressed_total
rejected_event_symbol_duplicate_suppressed_total
rejected_revision_seen_ignored_count
```

禁止把每 poll 累加值命名为普通 `*_count`。扫描 `observer_state.jsonl` 时必须按 stable key / terminal_hygiene_id 取 latest state，不能按原始行数统计。

新增 hygiene 指标：

```text
rejected_missing_identity_count
rejected_missing_reason_count
rejection_hygiene_diagnostic_count
bootstrap_watermark_missing_diagnostic_count
```

`LiveDepthObserverSummary` 是 frozen dataclass，新增字段必须有默认值，旧 summary 反序列化必须兼容。

## 14. 1.5G 兼容边界

本 hotfix 不修改 Stage 1.5G decision 逻辑。

新规则：

```text
normal events_rejected:
  consumable_by_stage1_5g = true
  仅包含 post-bootstrap genuine admission failure

historical_anchor_hygiene_diagnostics:
  consumable_by_stage1_5g = false
  1.5G 不读取

malformed_terminal_diagnostics:
  consumable_by_stage1_5g = false
  1.5G 不读取
```

1.5G 若读取旧 root 中 malformed rejected rows，应保持兼容，不崩溃；但新 root 不应再出现 `missing_identity_ratio = 1.0` 或 `reason_counts = {"MISSING_REASON": ...}`。

## 15. 测试要求

Implementation plan 必须采用 TDD。

### 15.1 Preflight / Writer Tests

```text
test_preflight_lists_all_events_rejected_writer_paths
test_rejected_row_contains_rejected_reason_and_rejection_reason_alias
test_build_rejected_event_symbol_row_requires_identity
test_malformed_identity_goes_to_diagnostic_not_events_rejected
```

### 15.2 Historical Ignore Tests

```text
test_all_valid_anchors_pre_bootstrap_short_circuits_conflict
test_historical_anchor_pre_bootstrap_writes_terminal_ignored_state_not_events_rejected
test_historical_anchor_pre_bootstrap_is_idempotent_across_polls
test_historical_anchor_pre_bootstrap_survives_restart_and_suppresses_duplicate
test_one_post_bootstrap_anchor_prevents_historical_ignore
test_invalid_zero_anchor_is_not_counted_as_historical_candidate
test_delayed_launch_check_uses_root_bootstrap_watermark
```

### 15.3 Crash Recovery Tests

```text
test_restart_after_terminal_state_write_repairs_missing_audit_row
test_restart_after_audit_write_does_not_duplicate_row
test_terminal_hygiene_id_stable_across_restarts
```

### 15.4 Summary Tests

```text
test_summary_counts_historical_ignored_latest_states_as_gauge
test_summary_does_not_count_observer_state_append_history_as_gauge
test_summary_exposes_rejected_missing_identity_and_reason_counts
test_summary_new_fields_have_defaults_for_legacy_compatibility
```

### 15.5 Regression Tests

```text
test_future_launch_pending_still_does_not_write_rejected_row
test_anchor_conflict_for_post_bootstrap_future_event_still_pending
test_launch_anchor_age_exceeded_writes_one_rejected_row_with_identity
test_pre_watermark_ignored_does_not_write_events_rejected_row
test_clean_post_watermark_event_acceptance_unaffected
test_historical_ignored_diagnostic_sample_is_capped_per_type
```

## 16. 生产验收

部署新 root 后检查：

```bash
wc -l "$STAGE1_5F_OUT"/events_rejected/*.jsonl 2>/dev/null || true
sleep 120
wc -l "$STAGE1_5F_OUT"/events_rejected/*.jsonl 2>/dev/null || true
```

验收标准：

```text
没有新 post-bootstrap admission failure 时，events_rejected 行数不应每轮持续增长。
historical-anchor old events 不写 normal events_rejected。
historical_anchor_ignored_count 可上升，但 duplicate suppressed 后不产生无限 diagnostic rows。
rejected_missing_identity_count = 0
rejected_missing_reason_count = 0
malformed_terminal_diagnostic_count = 0 或有明确 diagnostic row
pending_launch_observation_count 不因旧 historical anchors 长期 > 0
active_observation_count = 0 时 total_snapshots_collected = 0
```

抽样检查：

```bash
python3 - <<'PY'
import glob, json, os
root = os.environ["STAGE1_5F_OUT"]
total = 0
missing_identity = 0
missing_reason = 0
for p in glob.glob(f"{root}/events_rejected/*.jsonl"):
    with open(p) as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            row = json.loads(line)
            if not row.get("event_symbol_id") or (not row.get("event_id") and not row.get("source_article_id")) or not row.get("detected_at_ms"):
                missing_identity += 1
            if not (row.get("rejected_reason") or row.get("rejection_reason")):
                missing_reason += 1
print({
    "total": total,
    "missing_identity": missing_identity,
    "missing_reason": missing_reason,
})
PY
```

新增 diagnostic 限流检查：

```bash
find "$STAGE1_5F_OUT" -maxdepth 2 -type f \( -path '*/historical_anchor_hygiene_diagnostics/*' -o -path '*/rejection_hygiene_diagnostics/*' \) -print -exec wc -l {} \; 2>/dev/null || true
```

## 17. 风险与回滚

主要风险：

```text
1. historical ignore 判定过宽，把合法 delayed launch 误忽略。
2. terminal ignored 幂等过强，导致真实 reschedule revision 不再重新评估。
3. 双写 reconciliation 复杂，可能遗漏 state/audit 修复。
4. observer_state schema 扩展破坏旧 state 读取。
```

缓解：

```text
1. 只在所有 normalized anchors 都早于 immutable bootstrap watermark 时 historical ignore。
2. 任一 post-bootstrap anchor candidate 存在时，不走 historical ignore。
3. delayed launch exception 必须使用 immutable bootstrap cutoff。
4. 第一版不因 payload hash 自动 reopen，只允许新 source_article_id / 新 symbol / 明确 reschedule identity。
5. EventSymbolState 新字段必须有默认值，旧 state 可读。
6. diagnostic stream 不被 1.5G 消费。
7. 不修改 accepted/depth snapshot 路径。
```

回滚方式：

```text
停止新 1.5F tmux session；
保留 output root 作为审计；
恢复上一版 root suffix 启动命令；
不删除旧 root，不改历史 evidence。
```

## 18. 最终判定

本 hotfix 值得做，但语义必须从“historical anchor rejection”修正为“historical anchor terminal ignored”。

原因：

```text
当前问题不污染盘口 evidence，但会持续产生不可审计 rows；
historical pre-bootstrap event 不应进入 1.5G normal rejected 分母；
缺 identity/reason 会削弱 1.5G 和人工复盘可信度；
重复写入会让 7d root 文件膨胀；
修补范围可以限制在 1.5F terminal ignore / rejection hygiene，不需要改 1.5D、1.5G 或交易相关逻辑。
```

实施前必须先写 implementation plan，并在 plan 中明确 TDD 顺序、schema migration、root-cause preflight、reconciliation 和生产验收命令。
