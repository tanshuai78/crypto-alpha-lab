# Stage 1.5D / 1.5F / 1.5G Storage Lifecycle and Resource Guard Hotfix Design

```text
status = design_revised_after_closure_review
scope = stage1_5d_1_5f_1_5g_storage_lifecycle_resource_guard_hotfix
design_owner = human_research_owner
implementation_allowed = false
implementation_plan_allowed = after_design_review_only
stage1_5g_execution_location = local_only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

## 1. 已确认事实

1. VPS 根磁盘为 `30GB`。清理 DOSUSDT 对应的非活动 root 后，可用空间从约 `4.6G` 增至 `7.3G`；这仍不足以证明一个新 7 天 root 可安全运行。
2. 已归档的 1.5F root `live_depth_observer_20260809T023455Z_7d_schedule_revision_producer_hotfix` 为 `1.62GiB`。其中 `observer_state.jsonl` 为 `1.48GiB`、`323,790` 行；`event_batch_registry.jsonl` 为 `108.5MiB`、`332,672` 行；`depth_snapshots` 仅约 `312KiB`。
3. 该 state stream 仅包含 `66` 个唯一 `event_symbol_id`，即平均每个 id 被持久化约 `4,906` 次。batch registry 仅包含 `23` 个唯一 batch，即平均每个 batch 被持久化约 `14,464` 次。增长来自同一输入 replay 的重复状态转换，不是正常 L2 快照量。
4. 1.5F runner 在启动时调用 `compact_observer_state_jsonl()`；该函数全量读取 JSONL、复制完整 `.bak`，再原子替换。它不在正常运行期间收敛 state 或 batch registry，因此大 root 重启会造成 CPU、内存和额外磁盘峰值。
5. 1.5F runner 每个 poll 都先把既有 launch batch 写成 `batch_started`，随后再次写入 durable/watermark 状态。已完成 batch 会被回退为起始状态再重写，破坏了 append stream 的幂等性。
6. 对已存在的 terminal/active/completed state，当前 replay 路径会更新 duplicate 字段并再次 append；相同 source event 即使没有新的业务状态变化，也会持续增大 `observer_state.jsonl`。
7. 1.5D 的 BAPI detail raw payload 使用 `timestamp.variant.hash` 文件名。相同 article、相同 variant、相同 raw SHA256 在不同 poll 会产生不同文件。DOSUSDT 归档中同一 payload SHA256 至少在 manifest 中出现 `76` 次，且提取到 `215` 个 raw payload 文件。
8. 已有 `EXTERNAL_SIGNAL_STAGE1_5D_MAX_RAW_PAYLOAD_BYTES_PER_DAY` 配置，但当前 `enforce_payload_budget()` 检查的是日 JSONL stream 路径；实际 BAPI raw 文件写入 `raw_payloads/announcement_detail/<article>/`。该 budget 不覆盖实际大文件，属于接线错误。
9. 1.5G `_load_jsonl_file()` 把完整 `observer_state.jsonl` 读入 list，之后才按 `event_symbol_id` 归约 latest state。本地对约 `1.5GiB` state 的 review 峰值内存约 `6.6GB`；VPS 上运行会带来不可接受的失联风险。
10. 1.5G 对 state 的业务使用最终只需要每个 `event_symbol_id` 的 latest row；其现有 reducer 已表达这一语义。1.5F 启动恢复和 batch registry 消费也只读取 latest row。
11. DOSUSDT 现场最小证据包已本地归档为 `16MiB`，含 1.5D event/manifest/raw payload/runtime gate、1.5F accepted/latest state/manifest/snapshots/root contract，以及 1.5G invalid review；`229` 个文件 SHA256 均验证通过。它是本次问题的真实来源证据，但不进入 Git。

## 2. 显式假设

1. 1.5D/1.5F 每次生产部署均使用新的隔离 output root；旧 root 只读，不能被新代码补写或原地迁移。
2. 1.5F `observer_state.jsonl` 和 `event_batch_registry.jsonl` 是 durable latest-checkpoint stream，不是需要无限保存的完整 transition history。accepted/rejected rows、schedule revision registry、diagnostic rows、request manifest 和 depth snapshots 继续承担可审计历史证据角色。
3. 1.5D 对同一 article、同一 detail variant、同一 raw payload 内容的重复请求不增加新的原始事实；保留一次内容寻址文件和每次 request manifest 行足以证明请求重放与响应一致。
4. Stage 1.5G 是离线只读审计工具。其执行位置由 runbook 约束为开发者本地机器，不在 VPS 运行；本次不实现脆弱的主机名/IP 识别或远端自动拒绝逻辑。
5. `30GB` 是本轮已知部署硬件。空间阈值必须显式配置、可在将来硬件变化时复核，但不会在运行时由用户输入覆盖。

## 3. 根因与核心问题

当前实现把两类不同数据混在无限 append-only 生命周期中：

```text
1. immutable evidence:
   raw payload version, request manifest, accepted/rejected decision, depth snapshot

2. mutable checkpoint:
   latest observer state, latest batch lifecycle status
```

对第 2 类数据每分钟重复写入，不会增加审计价值，却让 root 以 `153-406MiB/day` 的观测速度增长。重启时再全量读写和备份该 stream，会放大 CPU、内存和磁盘压力。

同时，1.5D 的 raw payload 实际写入路径绕过了已声明的 budget，导致相同 BAPI 内容按 timestamp 反复落盘。1.5G 又把已膨胀的 checkpoint stream 完整加载到内存。

这不是单点文件过大问题，而是 writer、checkpoint 生命周期、预算边界和 reviewer 读取方式不一致的问题。

## 4. 范围与显式非目标

### 4.1 范围内

1. 为 1.5D/1.5F 新 root 建立启动和运行时磁盘资源门禁。
2. 将 1.5F state 与 batch registry 收敛为 latest checkpoint，并修复 replay 下的无业务变化重复写入。
3. 将 1.5D detail payload 按 `article + variant + raw_sha256` 内容寻址去重；实际 payload budget 必须覆盖真实 raw payload 目录。
4. 将 1.5G state 输入改为流式 latest-state 归约；1.5G runbook 明确为本地只读操作。
5. 在 summary/runtime gate 中暴露资源门禁状态和 blocker，供部署与日常检查 fail-closed。
6. 使用 DOSUSDT 归档事实构造最小 synthetic regression fixture；不得把它伪称为可提交的完整真实 raw fixture。

### 4.2 显式非目标

1. 不改变 launch parser、formal event contract、anchor contract、schedule revision producer/consumer 的业务语义、watermark 语义或 1.5F admission 判定。
2. 不复活或修改旧 root 的 terminal state，不补写历史 snapshots，不把旧 DOSUSDT evidence 升级为 formal evidence。
3. 不引入数据库、消息队列、对象存储、后台清理服务、第三方依赖、单实现接口或 factory。
4. 不自动删除任何 evidence、历史 root、payload、snapshot 或 manifest；历史归档与删除继续由人工运维流程决定。
5. 不在 VPS 执行 1.5G，也不改变任何 trade/paper/live/execution/alpha authority。
6. 不以调整轮询间隔、降低 depth limit 或扩大磁盘为替代方案掩盖 writer 幂等性问题。

### 4.3 Design 级 Scope Gate

下列是本 Design 已确认的唯一候选实现范围。Implementation Plan 必须逐项确认；需要新增未列路径时，必须回到 Design，不得在执行期扩张。

```text
Allowed implementation paths:
  configs/base.py
  src/research/external_signal_shadow/stage1_5_storage_guard.py              (new, minimal shared guard)
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py    (guard-only scheduler checkpoint persistence)
  src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py
  src/research/external_signal_shadow/stage1_5d_runtime_gate.py
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py (semantic fingerprint/replay classifier only)
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py (guard-only D/F stream persistence)
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py
  src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py (guard-only revision registry persistence)
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
  docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md

Allowed verification paths:
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py        (new)
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
  tests/fixtures/external_signal_shadow/stage1_5d/storage_lifecycle/          (new, synthetic only)
  tests/fixtures/external_signal_shadow/stage1_5f/storage_lifecycle/          (new, synthetic only)

Allowed documentation paths:
  docs/designs/2026-08-13-external-signal-shadow-lab-stage1-5d-1-5f-1-5g-storage-lifecycle-resource-guard-hotfix-design_CN.md
  docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md

Forbidden:
  formal event / schedule revision / anchor contract schema or business semantics
  Stage 1.5F anchor/admission reducer logic outside the named replay classifier
  watermark schema version or watermark identity semantics
  polling interval, depth request limit, authority flags, producer enablement
  any database, queue, object storage, third-party package, factory, or generic backend abstraction
  ruff check --fix . ; git clean ; rsync --delete ; destructive evidence cleanup
  modification of old roots or DOSUSDT archive
```

`stage1_5f_live_depth_observer_loader.py` is deliberately allowed only for the replay classifier because it is the shared root-cause boundary for `active_or_completed_duplicate_revision` and `terminal_revision_seen`. Freezing that function would preserve the unbounded append path; all unrelated Phase A-C anchor logic remains forbidden.

Scope-delta rationale: source inspection after the initial scope freeze confirmed three additional new-root persistent writers: `write_detail_retry_scheduler_state()` in the D scheduler, `append_jsonl()`/`write_json()` in F stream storage, and `ScheduleRevisionRegistry.record_revision()` in F revision registry. They are added solely so each existing write can use the same `stage1_5_storage_guard.py` reservation boundary. This does not authorize changes to retry scheduling, revision linkage/application semantics, event/admission semantics, checkpoint identity, schedule-revision producer enablement, watermark identity, or authority flags.

## 5. 已作决策及理由

### 5.1 30GB VPS 资源安全契约

新 D/F root 必须满足：

```text
host_start_free_bytes >= 8 GiB
host_runtime_protected_reserve_bytes = 4 GiB
host_ordinary_control_plane_reserve_bytes = 52 MiB
host_emergency_blocker_reserve_bytes = 12 MiB
stage1_5d_root_max_bytes = 1 GiB
stage1_5f_root_max_bytes = 2 GiB
stage1_5d_root_ordinary_control_plane_reserve_bytes = 12 MiB
stage1_5d_root_emergency_blocker_reserve_bytes = 4 MiB
stage1_5f_root_ordinary_control_plane_reserve_bytes = 28 MiB
stage1_5f_root_emergency_blocker_reserve_bytes = 4 MiB
stage1_5d_terminal_write_set_max_peak_bytes = 2 MiB
stage1_5f_terminal_write_set_max_peak_bytes = 2 MiB
stage1_5d_raw_payload_root_max_bytes = 768 MiB
root_reconciliation_scan_interval = 5 minutes
stage1_5f_checkpoint_compact_interval = 15 minutes
stage1_5f_checkpoint_compact_threshold = 256 MiB per checkpoint file
stage1_5g_execution_location = local_only
```

理由：启动需要为 Python、系统日志、临时 atomic 文件和其他服务保留余量；运行中 `4GiB` 是不可触碰 reserve。`1GiB + 2GiB` 既给 1.5D 真实 payload version 和 1.5F 多 symbol 12h snapshots 留出宽裕边界，也禁止再次依赖接近写满整盘的人工清理。

资源检查只使用 Python stdlib `fcntl.flock()`、`shutil.disk_usage()`、`Path`/`os.walk()`、`json` 与现有 JSON writer。新增的 `stage1_5_storage_guard.py` 是唯一小型 shared TCB：不引入 backend、factory 或配置对象；只负责跨 D/F host lock、root account、写前 reservation 和写后 reconciliation。生产 D/F root 的共享 lock 固定在其共同父目录 `data/external_signal_shadow/.stage1_5_storage_guard.lock`；lock 文件只用于互斥，不是 durable business artifact。

每个 D/F root 在启动时递归扫描并建立 `accounted_root_bytes`。任何 durable write 均须经同一个 guarded writer boundary：在持有 project-level host lock 的整个“检查 -> temporary/final write -> replace -> 记账”期间，区分：

```text
persistent_delta_bytes = write 完成后 root 的净变化
transient_peak_bytes   = old file 仍存在时，temporary/final 写入额外需要的最大字节

normal data write:
  accounted_root_bytes + transient_peak_bytes
    <= root_max_bytes - root_ordinary_control_plane_reserve_bytes
       - root_emergency_blocker_reserve_bytes
  disk_free_bytes - transient_peak_bytes
    >= host_runtime_protected_reserve_bytes
       + host_ordinary_control_plane_reserve_bytes
       + host_emergency_blocker_reserve_bytes

ordinary control-plane write (READY gate refresh, root contract, normal summary,
watermark commit):
  accounted_root_bytes + transient_peak_bytes <= root_max_bytes
       - root_emergency_blocker_reserve_bytes
  disk_free_bytes - transient_peak_bytes
    >= host_runtime_protected_reserve_bytes + host_emergency_blocker_reserve_bytes

terminal control-plane write (FAILED gate, final blocker summary/diagnostic,
failed-payload terminal manifest):
  accounted_root_bytes + transient_peak_bytes <= root_max_bytes
  disk_free_bytes - transient_peak_bytes >= host_runtime_protected_reserve_bytes
```

因此 `4GiB` protected reserve 不被任何写入触碰。ordinary control plane 可使用 ordinary reserve，但必须保留 emergency blocker reserve；terminal control plane 只在 storage failure 生命周期内使用 emergency reserve，随后进程退出。root emergency reserve 为 D/F 各自 `4MiB`；host emergency reserve `12MiB` 大于 D+F 两个 `2MiB` terminal write set peak 之和，保留 `8MiB` 余量。terminal write set 必须是固定、大小上限可验证的少量 artifact，不能把 state、manifest history 或任意 exception dump 嵌入 final summary。

terminal reserve 不是拍脑袋常量。对按顺序写入的 terminal artifact 集合 `i=1..n`，其 required peak 必须计算为：

```text
terminal_write_set_peak_bytes = max_k(
  sum(persistent_delta_bytes_i for i < k) + transient_peak_bytes_k
)
```

集合仅可包含 failed runtime gate、final summary、final storage diagnostic 与最多一条 failed-payload terminal manifest。每种 row 使用 bounded scalar fields；blocker list、string field 和 diagnostic sample 均有固定最大长度。启动时必须以这些最大字段构造 terminal rows，并验证：每个 terminal artifact 与完整 terminal write set peak 均不超过对应 `*_terminal_write_set_max_peak_bytes`；同时 `host_emergency_blocker_reserve_bytes >= D_terminal_peak + F_terminal_peak`。配置不足时启动拒绝。D/F 使用同一 `flock` 路径，避免两个进程同时以同一个 free-space 读数批准写入。写入成功后记录实际 persistent delta；启动和固定 `5` 分钟 scan cadence 在同一 lock 下重新扫描并纠正 account。scan 仅用于 reconciliation，不能替代写前 reservation。

Reservation helper invariant：

```text
transient_peak_bytes >= max(0, persistent_delta_bytes)

direct JSONL append:
  transient_peak_bytes = serialized append bytes
  persistent_delta_bytes = successful file growth

atomic replacement:
  transient_peak_bytes = candidate temporary bytes
  persistent_delta_bytes = candidate bytes - old target bytes

checkpoint compaction:
  transient_peak_bytes = exact compact candidate bytes
  persistent_delta_bytes = candidate bytes - old checkpoint bytes
```

checkpoint compaction 的 temporary file 也属于 transient peak。compaction 采用两阶段算法：第一 pass 流式建立 latest map；第二 pass 以 canonical JSONL 精确计算 compact candidate bytes；仅当 candidate 的 peak reservation 可通过时写 temp、`fsync`、`os.replace()` 并 `fsync` parent directory。不得以旧 append file 的大小作为 temp reserve，也不得复制 `.bak`。该算法允许“旧文件很大、latest map 很小”的 root 被收敛；若 candidate 本身无法预留，则 fail-closed 而非写满磁盘。

`256MiB` threshold 是 trigger，不是 compaction 的 peak reservation。liveness 条件为：只要 physical-last latest candidate 加 ordinary 与 emergency reserve 仍低于 root limit，运行中 compaction 必须允许发生，即使旧 append stream 已超过 root budget 的一半。上述所有数值以命名常量写入 `configs/base.py`；Implementation Plan 不得改为 CLI flag、环境变量或隐含 fallback。

### 5.2 低空间 fail-closed，而不是自动删除

```text
before start:
  free < 8GiB or root >= own budget
  -> do not start; explicit storage_start_* blocker

during run:
  normal-data reservation fails or a reconciliation scan finds breach
  -> use reserved emergency budget for final summary/gate blocker atomically
  -> stop normal polling and exit non-zero
  -> no new raw payload, event admission, snapshot, or append-only checkpoint write
```

1.5D storage breach 的唯一正式传播方式是既有 runtime gate：storage blocker 必须加入 `fatal_blockers`，并令 `decision = stage1_5d_runtime_gate_failed`、`consumable_by_stage1_5f = false`。不得仅添加 F 不认识的 storage 字段而继续 `ready`。1.5F 继续通过既有 non-ready runtime gate fail-closed；其自身 breach 写出 terminal blocker 后退出，而不是继续采样到 `ENOSPC`。任何连 terminal blocker 都无法写出的 `ENOSPC` 也必须导致进程失败退出。不得通过删除旧 evidence 恢复运行。

### 5.3 latest checkpoint 的流式原子收敛

`observer_state.jsonl` 与 `event_batch_registry.jsonl` 的 durable contract 改为：文件保留每个 identity 的 latest row；历史 transition 不在这两个文件内无限累积。

```text
observer state identity = event_symbol_id
batch registry identity = event_batch_id
```

compaction 必须逐行读取、仅在内存中保留每个 identity 的 latest row、写入同目录 temporary file、`fsync` 后 `os.replace()`，并 `fsync` parent directory。不得复制完整 `.bak`。

任何 checkpoint 中的非空 malformed JSON row 都是 checkpoint integrity failure：compaction 不得 replace authoritative file、不得跳过后继续生成“干净” checkpoint；必须保留原文件并写出 bounded checkpoint-integrity diagnostic。新 production root 的启动恢复因此 fail-closed 退出，不继续以可能损坏或被截断的 latest state 运行。1.5G 继续将相同 parse failure 作为 evidence blocker，避免 compaction 擦除 invalid evidence。

Crash 语义：

```text
crash before os.replace:
  original checkpoint remains authoritative; discard temp on next startup

crash after os.replace:
  compacted latest checkpoint is authoritative

no full-file backup:
  valid because prior full transition history is not required by startup or 1.5G;
  immutable evidence streams remain untouched
```

在启动时执行一次收敛；运行中仅当同时满足“达到最小间隔”和“文件超过 compact threshold”时收敛。`threshold` 与 `interval` 是部署硬件的 calibration knobs，必须写入 `configs/base.py`，而不是隐含常量。

### 5.4 replay 不得产生 durable checkpoint 写入

source semantic replay 的**业务 state**不变时：

```text
same semantic input + same current durable state
-> in-memory no-op
-> no observer_state append
```

但 business-state no-op 不等于 transaction-recovery no-op。batch lifecycle 使用现有准确状态，且只能单调推进：

```text
unknown -> batch_started
batch_started -> siblings_partially_durable | siblings_all_durable | batch_blocked
siblings_partially_durable -> siblings_all_durable | batch_blocked
siblings_all_durable -> watermark_committed
watermark_committed and batch_blocked are final
```

`update_batch_registry_status()` 是单调性唯一边界：对既有 `watermark_committed` 请求 `batch_started`、`siblings_partially_durable` 或 `siblings_all_durable` 必须拒绝且不 append；相同 status/相同 durable keys/相同 reason 也不得 append。runner 在写 `batch_started` 前必须先检查 registry map，已 final batch 不得重新开始。

每次 launch replay 必须执行下面的 recovery reducer，而不是按“same replay 不写 watermark”短路：

```text
1. 根据 latest state map 判断所有 expected siblings 是否 durable。
2. 有未 durable sibling：仅在 registry edge 实际变化时推进/保留 siblings_partially_durable。
3. 全部 durable 且 registry < siblings_all_durable：写 siblings_all_durable 一次。
4. registry = siblings_all_durable 且 watermark 尚未包含 event identity：原子写 watermark 一次。
5. watermark 已包含 identity 且 registry = siblings_all_durable：写 watermark_committed 一次。
6. registry = watermark_committed 但 watermark 缺少 identity：视为 durable corruption，fail-closed；不得猜测性修复。
```

这覆盖 crash-after-first-sibling、crash-after-last-sibling、crash-before-all-durable、crash-after-all-durable-before-watermark、crash-after-watermark-before-final-registry-row 与 watermark-committed replay。`watermark_committed` 后的正常 replay 不得产生 registry 或 watermark write。

`active_or_completed_duplicate_revision` 和 `terminal_revision_seen` 的 `duplicate_suppressed_count`/last-seen 只属于进程内 poll telemetry；两者不得调用 `append_jsonl(state_file, ...)`。它们只能在本次 batch 的 durable recovery reducer 中被视为“该 sibling 已 durable”，不能制造新的 state transition。下一次 compaction 只写已经存在的 durable latest state，不把瞬时 counter 变成新的 checkpoint 事实。

replay 判定使用版本化 `source_semantic_fingerprint_v1`，并以 `EventSymbolState.latest_source_semantic_fingerprint: str = ""` 持久化最后已处理值。该字段是 additive observer-state compatibility field：old row 缺失时 `from_dict()` 得到空字符串；new row round-trip 必须保留值；`observer_state_schema_version` 保持现有 `3`，formal event contract 与 watermark schema/version 均不改变。每个 symbol 的 canonical projection 必须恰好包含：

```text
event_id, source_article_id, stable_event_key, stable_event_symbol_key, symbol,
detected_at_ms, source_published_at_ms, source_detail_url_normalized,
formal_event_contract_version, formal_event_consumable_by_stage1_5f,
source_contract_status, symbol_identity_validation_status,
symbol_official_schedule_anchor_ms[symbol],
symbol_exchangeinfo_onboard_date_ms[symbol],
symbol_effective_observation_anchor_ms[symbol],
symbol_effective_launch_times_ms[symbol], symbol_effective_launch_time_sources[symbol],
symbol_source_anchor_contract_hashes[symbol], symbol_anchor_evidence_levels[symbol],
symbol_max_evidence_classes[symbol], symbol_anchor_comparison_statuses[symbol],
launch_anchor_validation_status, anchor_precedence_policy, anchor_contract_decision_at_ms
```

Maps are projected by the uppercase symbol key; keys are sorted; serialization is canonical JSON (`sort_keys=True`, compact separators, UTF-8) then SHA256. It explicitly excludes `now_ms`、request id、manifest timestamp/path、local filename、HTTP fetch time and raw payload path. An included-field change creates at most one durable state update for that new fingerprint; excluded-field changes create none; restart plus the same fingerprint creates none. The existing `latest_event_payload_hash` remains raw-payload provenance and is not repurposed as this semantic fingerprint.

### 5.5 raw payload 内容寻址与实际预算

对 BAPI detail payload：

```text
identity = source_article_id + detail_fetch_variant + raw_payload_sha256
path = raw_payloads/announcement_detail/<article>/<detail_fetch_variant>.<raw_payload_sha256>.bin
```

同一 identity 重试：保留原文件，返回同一 `payload_path` 与 hash；每次请求仍写入 request manifest。相同内容属于不同 article 时不得跨 article 共用路径，因为 article provenance 是证据的一部分。内容 hash 或 variant 改变时，保留新 version。

`MAX_RAW_PAYLOAD_BYTES_PER_DAY` 不能被偷换成无日目录的 root cumulative budget。新 root 使用单独的 `EXTERNAL_SIGNAL_STAGE1_5D_RAW_PAYLOAD_ROOT_MAX_BYTES`，递归统计实际 `raw_payloads/announcement_detail/`；原 per-day 常量保留旧语义，不能作为新 root gate。`.bin` 仅由 identity 决定，content type 留在 manifest，避免同 bytes 因 response header 变化得到不同 path。

HTTP request 已发生但 data payload 无法取得 normal-data reservation 时，使用 emergency reserve 写一条最终 manifest：`raw_payload_persisted=false`、`payload_path=null`、可用时记录 `raw_payload_sha256` 和 `storage_blocker`；不得引用不存在的 temp/final file。随后立即 fail-closed。若该 manifest 也无法写出，summary/gate 必须标记 `request_manifest_persistence_unknown=true` 后退出。

### 5.6 1.5G 本地流式 latest-state 读取

checkpoint 的唯一 latest authority 是**每个 identity 最后一个成功解析的物理 JSONL 行**。这是现有 1.5F restart 和 batch registry loader 的真实语义；timestamp 只作审计字段，不参与 latest 选择。compaction、1.5F restart、batch registry 与 1.5G 必须使用同一个 physical-last comparator。

因此 1.5G 必须以一次流式 pass 将 `observer_state.jsonl` 归约为 `event_symbol_id -> physical_last_valid_row`，之后只把该 latest map 交给既有 evidence integrity reducer。不得先构造完整 `list[dict]`。state JSON parse error 仍是 blocker；out-of-order/missing/equal timestamps 不得改变 physical-last 选择；所有其它 stream 的现有读取不在本次重构范围内。

VPS deployment checklist 禁止 1.5G 命令；完成 1.5F observation 后，按最小必要 root 或完整 root 同步到本地，并在那里运行 1.5G。

## 6. 验收不变量

| ID | 不变量 |
| --- | --- |
| `INV-01` | 在 30GB VPS 上，1.5D/1.5F 启动前 free space 小于 `8GiB` 时，任何 collector/observer 都不得启动写入。 |
| `INV-02` | normal-data reservation 不能保留 protected/ordinary/emergency reserve、ordinary control-plane write 不能保留 emergency reserve、或 reconciliation 发现 root breach 时，D/F 必须以 emergency reserve 写出 bounded terminal blocker evidence 后 fail-closed 退出；不得自动删除 evidence。 |
| `INV-03` | 新 1.5D root 不得超过 `1GiB`，新 1.5F root 不得超过 `2GiB`；每次 durable write 之前必须在跨 D/F host lock 内预留 persistent delta 和 transient peak。normal/ordinary/terminal 三类写入必须遵守 5.1 的 reserve hierarchy。 |
| `INV-04` | `observer_state.jsonl` 和 `event_batch_registry.jsonl` 只保留 latest checkpoint；启动和运行中 compaction 不得生成完整 `.bak` 副本。 |
| `INV-05` | checkpoint compaction 在任何 crash window 中均保留原文件或完整 physical-last latest checkpoint，不得留下半写 authoritative file；大旧 append stream 不得仅因原文件大而无法 compact。 |
| `INV-06` | 同一 event semantic replay 不得写入新的 business state；只允许恰好一次完成缺失的 batch/watermark transaction edge。`watermark_committed`/`batch_blocked` batch 不得回退。 |
| `INV-07` | 同一 article、variant、raw SHA256 的 BAPI detail retry 必须复用同一 payload path；manifest 仍逐请求保留。 |
| `INV-08` | 1.5D raw payload budget 必须统计实际 detail payload 目录；日 JSONL 大小不得被误当作 raw byte budget。 |
| `INV-09` | raw payload hash/variant 变化必须保留独立 version；不得因 dedupe 丢失 article provenance 或 manifest-to-payload 可追溯性。 |
| `INV-10` | 1.5F restart、checkpoint compaction、batch registry 和 1.5G 对 state 的 latest result 必须一致：每个 identity 的 physical-last valid row；1.5G 不得构造完整 state rows list。 |
| `INV-11` | 任何 malformed non-empty checkpoint row 都不得被 compaction 删除或绕过；1.5F restart 必须 fail-closed，1.5G 必须保留 parse-error evidence blocker。 |
| `INV-12` | 生产 runbook 不得在 VPS 执行 1.5G；1.5G 只读本地副本，绝不回写 D/F root。 |
| `INV-13` | 本次不得改变 launch/revision/admission 的业务结果、formal contract version、watermark schema、poll interval、depth request limit 或任何安全授权 flag。 |
| `INV-14` | `RISK_LIVE_TRADING_ENABLED = False`，且 trade/paper/live/execution/alpha permissions 均保持 false。 |

## 7. 契约影响矩阵

| 组件 | 角色 | 本次变化 | 不变项 |
| --- | --- | --- | --- |
| `stage1_5_storage_guard.py` | shared storage TCB | host lock、reservation、account/reconciliation、guarded write primitive | stdlib only；无 backend/factory；不含业务状态 |
| `stage1_5d_live_event_source_storage.py` | raw payload writer | 内容寻址、实际目录 root budget、guarded raw/manifest write | payload hash、manifest provenance、article isolation |
| `stage1_5d_runtime_gate.py` | D->F safety contract | storage blocker -> existing failed gate mapping | gate schema version、F existing non-ready handling |
| `run_stage1_5d_live_event_source_smoke_collector.py` | 1.5D runner / runtime gate writer | start/runtime storage guard、complete D write-surface routing、gate blocker | parser、event emission、revision producer default disabled |
| `stage1_5f_live_depth_observer_state.py` | state/batch checkpoint persistence | physical-last compaction、no full backup、monotonic batch transition | state/batch identities、terminal evidence semantics |
| `stage1_5f_live_depth_observer_loader.py` | replay classifier | source semantic fingerprint/replay classification only | all other anchor/admission reducer behavior |
| `stage1_5f_live_depth_observer_watermark.py` | batch transaction commit | guarded atomic write only；identity semantics unchanged | watermark schema/version/identity semantics |
| `run_stage1_5f_live_depth_observer.py` | 1.5F runner | complete F write-surface routing、recovery reducer、scheduled compaction、storage fail-close/summary | admission reducer、snapshot cadence、runtime gate validation |
| `stage1_5g_live_depth_evidence_review.py` | local reviewer loader | physical-last state stream reduction | formal lineage/evidence pass-fail policy |
| deployment runbook | operator consumer | local-only 1.5G、storage guard acceptance fields | Git deploy, new-root isolation, no destructive deployment commands |

## 8. 数据、状态与时间契约

### 8.1 新的 storage guard summary fields

1.5D runtime gate 和 1.5F summary 必须包含：

```text
storage_guard_status: ready | blocked_start_free_space | blocked_start_root_budget | blocked_runtime_reserve | blocked_root_budget | blocked_checkpoint_integrity | blocked_control_plane_write_failed
storage_guard_checked_at_ms: integer
storage_free_bytes: integer
storage_root_bytes: integer  # current accounted estimate, including successful writes since last scan
storage_root_scanned_at_ms: integer
storage_root_max_bytes: integer
storage_blocker: string | null
request_manifest_persistence_unknown: boolean
storage_terminal_write_set_peak_bytes: integer
storage_emergency_blocker_reserve_bytes: integer
```

`storage_guard_status != ready` 是 fail-closed runtime condition。1.5D 必须将 blocker 写入既有 `fatal_blockers` 并产生 `stage1_5d_runtime_gate_failed`；1.5F 必须令 `block_new_event_admission = true` 并退出。terminal control-plane write set 只包含 failed gate、final summary/diagnostic 和可选 failed-payload terminal manifest；其全部 serialized/transient peak 必须受已配置上限约束。

### 8.2 Checkpoint compaction timing

```text
startup:
  compact both checkpoint files before loading latest state

runtime:
  at configured cadence and size threshold only
  compact state and batch registry independently
  candidate bytes, not old append-file bytes, determine temporary reservation

after compaction:
  reload/update in-memory latest map only when needed
  no change to accepted/rejected/snapshot/manifest/diagnostic streams
```

Compaction must never run concurrently with a second observer process on the same root; existing one-root/one-process runbook invariant remains required.

### 8.3 Guarded write-surface closure

新 root 中，下表列出的所有 persistent write 必须经过 `stage1_5_storage_guard.py` 的唯一 guarded writer boundary。任何 runner 直接调用未 guard 的 `append_jsonl`、`open(..., "w")`、`Path.write_text` 或 atomic replacement 都是 Scope/Invariant violation；本次不允许只保护 raw/state/snapshot 三个大文件而留下旁路。

| Stage | Normal-data artifacts | Control-plane artifacts |
| --- | --- | --- |
| 1.5D | events, raw-payload JSONL, request manifest, heartbeat, detail retry scheduler state/diagnostics, parse results, formal launch identity index, revision payload versions, raw detail payload | runtime gate, final smoke summary, final storage diagnostic, failed-payload manifest row |
| 1.5F | observer state, batch registry, revision registry, accepted/rejected/pending/diagnostic rows, request manifest, depth snapshots, heartbeat | observer root contract at startup, final summary, final storage diagnostic, watermark transaction commit only when recovery reducer authorizes it |

The writer boundary receives the intended artifact class and exact serialized bytes or temp peak bytes. It never changes row content, state reducer, event identity, watermark identity, or admission decision. Directory creation is part of the same reservation; `ENOSPC` at any point invalidates the reservation, reports the designated blocker if possible, and exits.

### 8.4 Raw payload and manifest relation

```text
manifest request row:
  always emitted for an attempted request
  payload_path may repeat for same content retry; null only when storage blocked
  raw_payload_sha256 identifies content
  raw_payload_persisted records whether bytes reached final path

raw payload file:
  one file per article + variant + content hash
  atomically created if absent
  never overwritten or pruned automatically
```

### 8.5 Temporary-file ownership and cleanup

All guard-created atomic temporary files use only these root-local schemas:

```text
.<target-name>.atomic.<process-instance-id>.tmp
.<target-name>.compact.<process-instance-id>.tmp
```

At startup, a runner may remove only orphan files under its own output root matching the exact target basename and one of these schemas. It must not glob-delete arbitrary `*.tmp`, recurse outside its root, or remove payload evidence. A temp file is never referenced by a manifest; a final payload path is recorded only after replace succeeds.

### 8.6 1.5G state reduction contract

```text
input order = file line order
latest ordering = last successfully parsed physical line for the identity
parse failure = existing jsonl_parse_error blocker
output = map[event_symbol_id]latest_state
```

The reviewer may receive an already compacted state stream or an old append stream; both must produce the same physical-last latest-state result.

## 9. Failure、Crash、Restart 与幂等性

| 情形 | 必须行为 |
| --- | --- |
| start free space below threshold | no stream directory creation beyond best-effort summary; process exits non-zero |
| runtime reserve/root budget breached | no new admission/payload/snapshot writes after blocker; process exits non-zero |
| ordinary control-plane write would consume emergency reserve | do not perform ordinary write; emit terminal storage blocker using emergency reserve and exit non-zero |
| checkpoint contains malformed non-empty row | do not compact or replace; preserve original, emit bounded integrity diagnostic, fail-closed on 1.5F restart |
| `ENOSPC` during write | no retry loop; surface storage blocker if possible, exit non-zero |
| crash before checkpoint replace | original checkpoint remains authoritative; only owned stale temp may be removed on startup |
| crash after checkpoint replace | compacted checkpoint is authoritative; no reconstruction from deleted `.bak` is required |
| crash during deduped raw write | final content-addressed file appears only after atomic replace; manifest references only completed write result |
| same event replay | no business-state mutation; recovery reducer may complete exactly one missing registry/watermark edge |
| same raw response retry | same payload path/hash; new manifest row only |
| old root restart | not supported as migration path; old root remains immutable evidence |

## 10. 兼容性、迁移与历史 artifact 处理

1. 本 hotfix 仅对新 output root 生效。旧 root 不做在线 compaction、dedupe migration 或 manifest rewrite。
2. 旧 `observer_state.jsonl` 与 registry 仍可被新 1.5G 的流式 reader 读取，并按既有 1.5F physical-last checkpoint authority 得到兼容结果。旧 1.5G timestamp-order 结果若与该 authority 不同，属于本 hotfix 明确统一的旧 reviewer inconsistency；必须由 out-of-order regression fixture 证明新结果与 restart authority 一致。
3. 旧 raw payload timestamp paths 仍可被 manifest 读取；新 writer 只影响新 root。
4. DOSUSDT 的 `16MiB` 本地 evidence archive 是只读 incident evidence，不提交 Git，不作为正式 1.5G evidence，不替代新 live collection。
5. 现有 deployment Git ancestry attestation、formal contract v2、producer default-disabled 和 consumer proof 不改变。

## 11. 验证策略与 fixture provenance

### 11.1 单元与性质测试

1. 1.5F：相同 terminal/active/completed launch replay 多次后，state/registry/watermark 文件行数不增长；`active_or_completed_duplicate_revision` 和 `terminal_revision_seen` 只更新内存 telemetry；任一 included semantic fingerprint field 改变只产生一次合法 state update，excluded audit field 改变不产生 durable update。
2. 1.5F：`watermark_committed`/`batch_blocked` batch 重放不得回退；同一 status/keys/reason 不得 append；partial batch 只在真实 pending -> durable transition 时推进。
3. 1.5F：完整 crash matrix 覆盖 first sibling、last sibling、all-durable、watermark、final registry row 五个 crash window；replay 只能完成缺失 edge 一次，`watermark_committed` 与 watermark identity 不一致必须 fail-closed。
4. 1.5F：state 和 registry compaction 前后 physical-last latest maps、restart result 与 1.5G decision 完全一致；覆盖 out-of-order/equal/missing timestamp；任一 malformed middle row 必须保留原文件、阻止 compaction 且使 restart/review fail-closed；不存在 `.bak`；模拟 crash-before-replace 保留原文件。
5. 1.5F：old append file 很大、latest map 很小时，two-pass candidate reservation 仍允许 compaction；candidate 本身无空间时不创建 temp 并 fail-closed。
6. 1.5D：相同 article/variant/raw bytes（包括不同 content type）写入多次，只生成一个 `.bin` payload file；内容或 variant 改变时生成独立文件；manifest-to-file SHA relation 有效。
7. 1.5D：实际 `announcement_detail` 目录超过 root payload budget 时阻断，日 JSONL 为空/很小时也不能绕过；HTTP 已完成但 raw persistence 被拒绝时，最终 manifest 不得指向不存在 payload。
8. D/F：模拟 `disk_usage` 的 start/runtime/root-budget 三个失败路径、atomic overwrite old+temp、raw temp+final、checkpoint candidate temp、D/F simultaneous near-reserve writes。normal data 必须保留 ordinary+emergency reserve；ordinary control-plane write 不得消耗 emergency reserve；D/F sequential terminal failures 必须都能写 final blockers；terminal write set 超过 configured cap 必须在 startup validation 拒绝。断言 blocker、无新 admission/append、non-zero exit 和 protected reserve 不被突破。
9. State compatibility：old row 缺失 `latest_source_semantic_fingerprint` 必须加载为 `""`，new row round-trip 保留该值，且 `observer_state_schema_version == 3`、formal event/watermark schema version 不变。
10. 1.5G：对 synthetic append-only state stream，流式 physical-last reducer 与 1.5F loader/compaction 的 latest map 等价；测试禁止全量 state list loader 被调用；accepted/snapshot/manifest loader 回归保持不变。

### 11.2 Fixture provenance

```text
DOSUSDT incident archive:
  local_only_incident_evidence
  not committed

committed regression fixture:
  synthetic_offline_fixture_derived_from_verified_DOSUSDT_observations
  contains only minimum identities, repeated state/batch rows, and hashes
  no claim of real_frozen_bapi_payload unless original bytes are explicitly committed with provenance
```

Implementation Plan 的 Task 0 必须在不修改文件的前提下复核当前 workspace 与本地 DOSUSDT archive：archive manifest/SHA256、`du`、`wc -l`、unique state/batch identity counts、raw payload path pattern、以及 1.5G local profiling provenance。若与本 Design 的历史观测数字不一致，以当前可验证 artifact 为准；不得伪造或补造原始 payload。

### 11.3 Production wiring acceptance

1. 新 root 启动时 gate/summary 同时显示 `storage_guard_status = ready`、`storage_free_bytes >= 8GiB`。
2. D/F root summary 显示 own root budget、accounted root bytes、最近 scan 时间、storage blocker 和 control-plane persistence state；正常运行中 root bytes 可观测且不超过上限。
3. 7 天结束后，检查 checkpoint 文件大小、row count 和 compaction diagnostics；它们必须与 unique state/batch 数量和真实 active snapshot 数量成比例，而不是与 poll count 成比例。root 不得发生 storage exit；若发生，则视为容量验收失败而不是正常完成。
4. 1.5G 只在本地 root 副本上运行；VPS 运行日志不得出现 1.5G reviewer process。
5. 所有 safety flags 仍为 false；本 hotfix 不产生 alpha 或 execution conclusion。

## 12. Rollout、Rollback 与运维边界

1. 部署前必须有至少 `8GiB` 可用空间；不足时不启动新 7 天 root。此阈值是 host start guard，不是对普通运行时正常写入的授权。
2. 部署使用 Git exact commit checkout 与新 D/F root，保持现有 Git migration 和 root isolation 规则；不得使用 `rsync --delete`、`git clean`、`git reset --hard` 或 `rm -rf` 作为部署步骤。
3. 新 root 仅在 storage guard、runtime gate 和 root binding 均验证通过后启动 1.5F。
4. rollback 是停止新 tmux session、保留新旧 root 与 storage blocker；不得重用旧 root 或原地回写。
5. 1.5G runbook 只描述本地同步与本地 review；服务器不再提供执行 1.5G 的命令。这是 operator governance/TCB 前提：非恶意操作员遵守该 runbook；本次不以 hostname/IP 检测伪造代码强制。

## 13. 开放问题

| 问题 | 是否阻断 | Owner | 处理 |
| --- | --- | --- | --- |
| 在 `1GiB/2GiB` root budget 下，连续 7 天、多 event/30 active-symbol 压力的真实容量余量是否充足？ | 否 | implementation verification | 先用 deterministic synthetic worst-case test 验证；若超出，后续只调整已配置 calibration knobs，不扩大 scope。初始配置必须显式写入：5-minute scan cadence、compaction interval 和 threshold；不得留给运行时默认值。 |
| 1.5G 的 accepted/snapshot/manifest streams 是否也需完全流式化？ | 否 | future performance design | 本次已证实的 6.6GB 放大来自 state 全量加载；先修 state stream。若本地 profiling 显示其他 stream 成为主导，再单独设计。 |
| 历史 root 的长期归档介质和保留天数 | 否 | human research owner | 保持人工最小证据包归档流程；本次禁止自动删除。 |

## 14. Design Review Checklist

```text
[ ] All existing replay, formal contract, watermark, admission, and authority tests remain required.
[ ] No storage guard bypass can continue normal writes below reserve.
[ ] No checkpoint compaction creates a full-size backup or requires full state list in memory.
[ ] Raw dedupe preserves article/variant/content provenance and does not silently delete evidence.
[ ] 1.5G local-only runbook has no VPS execution path.
[ ] Plan declares narrow Allowed Change Scope and verifies direct graph consumers of writer, checkpoint, gate, and reviewer helpers.
[ ] No unresolved question changes the implementation path or safety boundary.
```
