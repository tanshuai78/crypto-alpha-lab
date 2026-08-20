# Stage 1.6B Binance Futures Delisting Canonical Official Source Capture And Live-Observation Provenance Design

**日期:** 2026-08-19
**状态:** `design_draft_for_review`
**适用范围:** External Signal Shadow Lab / Stage 1.6B
**安全模式:** `research_shadow_mode`; `RISK_LIVE_TRADING_ENABLED = False`。
**当前授权:** 仅 Design；未经后续 Implementation Plan 审核和用户批准，不新增 collector、不进行部署、不修改 Stage 1.5D/F。

## 1. 结论与使命边界

Stage 1.6B 是 Stage 1.6A 的**官方来源证据 producer**，不是下架策略、行情 collector、replay engine 或风险 veto 执行器。

它解决两个独立但可共享 canonical source profile 的问题：

1. 本地一次性 `historical_backfill`：冻结近 1--2 年 Binance 官方英文公告列表和详情原始载荷，供未来真实 source-schema/sample audit 使用。
2. VPS 持续 `live_observed`：低频观察官方英文公告列表，保存列表收到、候选发现、可信详情验证和原始载荷落盘的来源观察证据，供未来 point-in-time (PIT) 验证使用。

两种模式绝不混写 root，绝不把历史下载时间升级为历史可得时间。Stage 1.6B 不执行语义提取，故不产生 `system_available_at_ms` 或 `fact_available_at_ms`。其完成不等于 `source_audit_passed`、`point_in_time_source_validated`、`market_data_coverage_passed`、`replay_allowed` 或任何交易权限为真。

```text
historical_backfill -> schema / sample / source-text evidence only
live_observed       -> source PIT provenance only

Stage 1.6B
  != market-data collection
  != directional replay
  != alpha interpretation
  != risk-veto enforcement
  != paper/live trading
```

## 2. Confirmed Facts, Assumptions And Decisions

### 2.1 Confirmed Facts

1. Stage 1.6A 已实现 fixture/historical-contract-only reducer。其 runner 只接受 fixture root 与 `historical_backfill`，并将 `source_audit_passed`、PIT、coverage、replay 和 risk-veto authority 硬性保持为 `false`。
2. Stage 1.6A 已冻结 `ListCapture`、`ArticleDiscovery`、canonical `DetailRevision`、`SemanticExtraction`、父公告/child contract、canonical English authority 与历史数据不得伪造 PIT 的契约。
3. 用户报告运行中的 Stage 1.5D/F 位于 VPS，正在采集 `UNITREEUSDT` 的 12 小时 launch-depth observation。该报告不是本 Design 的运行时证明；未来 Plan 的 Task 0 必须重新采集 PID、heartbeat、gate、storage 和 lock 事实。本 Design 不允许在该观察完成前启动 1.6B VPS collector。
4. VPS 是 2 vCPU / 2 GiB RAM / 30 GiB disk 的受限主机。现有 Stage 1.5 storage policy 要求启动时可用空间至少 8 GiB，并在运行中保留 4 GiB protected reserve。
5. 当前 Stage 1.5D 已有 Binance public-web request、HTTPS/domain validation、request manifest 和 content-addressed raw payload 模式；其实现和 config 属于 Stage 1.5D，不是 Stage 1.6B 的运行时依赖。
6. Stage 1.6A 当前 `compute_list_capture_id()` 只表示 `surface|locale|variant|raw_sha256` 的内容身份，且仅由 fixture-only consumer 使用。1.6B 不修改该函数或 Stage 1.6A schema。

### 2.2 Assumptions

1. Binance 官方 announcement index 与 canonical English detail 可能修改 payload schema、URL/variant、locale 语义或可用性；每一次 response 必须以 frozen bytes 而非页面显示结果作为证据。
2. 本 Design 使用的 BAPI public-web transport 承载 Binance 官方内容，但不是此项目已验证的稳定官方开发者 API。artifact 必须记录 `transport_support_status = undocumented_public_web_profile`，不得表述为官方 API 保证。
3. 近 1--2 年的历史页面只能证明当前系统取得了历史官方内容，不能证明当时公告或 schedule fact 对系统可用。
3. 低频顺序 HTTP 请求和小型 append-only manifest 在正常响应大小下应远轻于 Stage 1.5F 的每分钟 depth 采集；这不是部署安全保证，VPS preflight 和运行时 stop condition 仍是硬门禁。

### 2.3 Decisions

| ID | Decision | Rationale |
|---|---|---|
| D-01 | 历史 backfill 仅在本地一次性运行；live observer 仅在 VPS 运行。 | 历史操作不需要常驻，避免占用 VPS；PIT 需要持续在线观测。 |
| D-02 | 本地历史 root 与 VPS live root 物理隔离，且两者都不位于 Stage 1.5 root。 | 防止历史数据污染 live provenance，也防止影响 1.5D/F。 |
| D-03 | live observer 是单进程、单线程、顺序网络 I/O；每 300 秒最多一个 index request 和一个 detail request。 | 2 GiB VPS 的最小资源包络；不建立 worker pool 或并发详情抓取。 |
| D-04 | live root hard max 是 256 MiB，ordinary-control-plane reserve 是 4 MiB，terminal emergency reserve 是 1 MiB；normal-data admission ceiling 是 251 MiB（未计入 transient peak），terminal write-set peak 上限 256 KiB。达到容量、host reserve 或 request safety blocker 时 fail closed 并退出。 | 禁止无限增长和与 1.5D/F 争夺 30 GiB 磁盘，同时保证最终 blocker 仍可写入。 |
| D-05 | 历史 backfill 与 live observer 产生 versioned source-capture artifacts；只有 sealed export bundle 可交给未来本地 audit consumer。 | active root 不能被直接当作完成审计输入，避免复制中的 partial state。 |
| D-06 | 本 Design 不修改现有 Stage 1.6A runner 的 fixture-only authority cap。 | 捕获 producer 与真实 audit authority 需要独立 review；避免把新网络输入和 authority unlock 混在一个变更中。 |
| D-07 | Stage 1.6B 不 import Stage 1.5D client、parser、storage guard 或任何 Stage 1.5 runtime module。 | Stage 1.5D client 的 config/profile 和变更周期不同；来源 profile 必须由 1.6B 自己版本化。 |
| D-08 | 只接受经 probe attestation 验证的 Binance official HTTPS index/detail source profile；不得把网页分类路径或非英文页面假设为永久 API 契约。 | 官方 web transport 与页面路径可能变化；先冻结实测 profile 再启动 producer。 |
| D-09 | historical backfill 接受明确的 UTC `[from_ms, to_ms]`，最大跨度 730 天；只有连续分页已覆盖 `from_ms` 且页面无缺口时才可 sealed export。 | 100-page 资源上限不能伪装成近 1--2 年数据完整覆盖。 |
| D-10 | historical backfill 使用两次连续稳定 sweep；只有两次分页顺序和集合相同、都覆盖 `from_ms` 且无页面失败时才可 complete。 | 仅“连续翻到旧日期”无法证明移动中的分页没有漏页、重页或顺序漂移。 |
| D-11 | 详情调度使用 Lane A（从未尝试）优先于 Lane B（退避重试），每 poll 最多一个 detail。 | 防止已多次请求的候选耗尽请求预算，重现 Stage 1.5 的 starvation。 |
| D-12 | 只有 `terminal_status.json` 可表达终态 complete/failure。 | 多个文件不能形成单次原子提交；单一终态 status 才能成为 fail-closed 判定点。 |

## 3. Allowed Change Scope For The Future Plan

本 Design 不改代码；下表是后续 Plan 必须遵守的最大白名单。任何扩大范围都需要 Design delta。

### Allowed implementation paths

```text
configs/base.py
src/research/external_signal_shadow/stage1_6b_canonical_source_models.py
src/research/external_signal_shadow/stage1_6b_canonical_source_client.py
src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py
src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py
scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py
scripts/external_signal_shadow/run_stage1_6b_historical_backfill.py
scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py
```

### Allowed verification paths

```text
tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py
tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py
tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py
tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py
tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py
tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py
tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py
tests/fixtures/external_signal_shadow/stage1_6b/**
```

### Allowed documentation paths

```text
docs/designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md
docs/plans/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-implementation-plan_CN.md
docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md
```

### Allowed generated/runtime artifacts

```text
data/external_signal_shadow/stage1_6b/source_profile_attestations/<profile-sha256>/source_profile_probe_attestation.json
data/external_signal_shadow/stage1_6b/historical_backfill/<run-id>/
data/external_signal_shadow/stage1_6b/live_observation/<run-id>/
```

Runtime artifacts are evidence, are ignored by Git, and must not be committed. `graphify-out/**` remains unchanged unless the user explicitly authorizes a graph update.

### Affected but unchanged

```text
src/research/external_signal_shadow/stage1_6a_*.py
scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py
src/research/external_signal_shadow/stage1_5d_*.py
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
src/research/external_signal_shadow/stage1_5f_*.py
scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
all strategy/, risk/, execution/ modules
```

### Forbidden

```text
any Stage 1.5D/F root, watermark, state or process change
Stage 1.6A authority-cap removal or source-audit verdict enablement
market price / L2 / funding / OI / fee collection
SignalCandidate, TradeIntent, risk-veto enforcement, replay, paper/live trading
authentication, account API, order endpoint or cookie/session use
concurrent worker pools, daemonized historical backfill, root-wide periodic scans
automatic deletion of incomplete roots or evidence cleanup during a run/seal
ruff check --fix ., git clean, rsync --delete, destructive cleanup
```

## 4. Core Issue And Target Architecture

### 4.1 Core Issue

Stage 1.6A can reduce a frozen historical input correctly, but no current producer supplies canonical official raw bytes with a durable distinction between:

```text
historical page downloaded now
vs.
article first discovered and trusted canonical-English detail observed while observer was running
```

Without that distinction, a later historical download could be misrepresented as an announcement-time information set. Without sealed producer exports, a local audit might read a partially copied live root.

### 4.2 Minimal Architecture

```text
Local historical one-shot                 VPS live observer
-------------------------                 -----------------
official index/detail                     official index/detail
  -> historical capture root                -> live capture root
  -> sealed historical export               -> atomic checkpoint
                                                   -> sealed live export
             \                                      /
              \                                    /
               future local real-capture audit consumer
               (separate Design/Plan; not authorized here)
```

There is no producer-to-Stage-1.5 transport, no source event consumed by trading code, and no producer-to-market-data connection.

## 5. Source Profile And Trust Boundary

### 5.1 Canonical Source Profile

Stage 1.6B freezes the following independent public-web profile. It is based on the already operating Stage 1.5D transport shape, but is owned and configured by Stage 1.6B rather than imported from it:

```text
source_profile_id = binance_public_web_bapi_en_v1
source_authority = binance_official_content
transport_support_status = undocumented_public_web_profile
base_url = https://www.binance.com
allowed_final_host = www.binance.com

index:
  path = /bapi/composite/v1/public/cms/article/list/query
  query = type=1&pageNo={positive_integer}&pageSize=50
  source_surface = announcement_index
  source_locale = en
  request_variant = bapi_article_list_type_1_page_50_v1

detail:
  path = /bapi/composite/v1/public/cms/article/detail/query
  query = articleCode={32_hex_source_article_id}
  source_surface = announcement_detail
  source_locale = en
  request_variant = bapi_article_detail_query_v1

request_headers_profile_version = stage1_6b_public_web_en_v1
headers = Accept: application/json; Accept-Language: en
Cookie = absent; Authorization = absent
```

The client canonicalizes this complete header profile, including explicit absent `Cookie` and `Authorization` flags, and records `request_headers_profile_sha256` on every manifest row. It may use a fixed non-secret User-Agent, but no runtime-configurable headers, credentials or cookies.

`source_profile_probe_v1` is a separate explicit readonly command. It receives one exact 32-hex `--probe-article-id`, issues one index and one detail request, and writes an atomic attestation at:

```text
data/external_signal_shadow/stage1_6b/source_profile_attestations/<profile-sha256>/source_profile_probe_attestation.json
```

The attestation contains canonical profile/header hashes, final URLs, HTTPS/host/path validation, request class, status, content type, payload size, article-ID extraction location, canonical-English body extraction location and attested-at time. It validates this frozen profile; it never discovers, substitutes or falls back to another endpoint.

Each historical/live run receives one exact `--source-profile-attestation` path. Before any network call it resolves the path under the attestation parent, validates its SHA-256 and requires both profile hashes to equal the currently configured profile/header hashes. It also requires `probe_attested_at_ms <= run_started_at_ms`; operationally the probe is executed immediately before each new run, without an arbitrary TTL. The run atomically writes `capture_run_contract.json` containing `run_id`, `capture_mode`, `run_started_at_ms` and `source_profile_attestation_sha256`, then copies the verified attestation into its root as `source_profile_probe_attestation.json`. Both are authoritative artifacts, the attestation SHA is repeated in every checkpoint and sealed manifest, and a mismatched or temporally impossible attestation blocks startup.

Only a profile-conforming response may be used by either collector. A successful HTTP response with empty, WAF, shell, wrong-locale, malformed, redirected-to-unapproved-host or unparseable payload is not a trusted capture. `source_profile_id` and request variant are part of every capture record. Any profile change requires a Design delta before semantic authority is possible.

### 5.2 Network Rules

```text
network permission: explicit --live-public-readonly only
scheme: HTTPS only
host: exact approved Binance official host allowlist
redirect: final URL must pass the same scheme/host/path checks
auth: none
cookies / session: none
methods: GET only
request concurrency: 1
retry inside one poll: 0

request_class:
  profile_probe_index | profile_probe_detail
  historical_index | historical_detail
  live_index | live_detail

live_observed:
  index requests: <= 1 per 300 seconds
  detail requests: <= 1 per poll

historical backfill:
  sequential index pages only; two sweeps of page range 1..100
  at least 1 second between all requests
  detail requests: <= 1 per request cycle
  required arguments: --from-ms, --to-ms
  max requested span: 730 days
  export allowed only after both stable sweeps cover --from-ms without a page failure
```

For historical index requests, HTTP 429 or any 5xx writes one `page_failure`, sets `HistoricalCoverage.status = incomplete_http_failure`, writes the bounded terminal status, and exits non-zero. It performs no same-run retry; the operator may start a fresh run ID. A historical export is eligible only after both sweeps independently reach `from_ms`, have no page failure, and are stable under Section 7.3.

## 6. Data, State And Temporal Contract

### 6.1 Shared Identities

Stage 1.6B does not redefine Stage 1.6A's existing fixture-only `compute_list_capture_id()`. It calls the equivalent four-field value `list_payload_id`: it identifies **the same list bytes**, not the request that saw them.

```text
list_payload_id = sha256(
  source_surface | source_locale | request_variant | raw_sha256
)

request_observation_id = sha256(
  run_id | request_class | monotonic_request_seq
)

list_capture_id = sha256(
  source_profile_id | canonical_requested_url | page_no |
  list_payload_id | request_observation_id
)

article_discovery_id = sha256(
  source_profile_id | source_article_id | first_list_capture_id
)

detail_revision_id = sha256(
  source_article_id | source_surface | source_locale |
  request_variant | detail_raw_sha256
)

ordered_authoritative_artifacts = canonical_json(
  sorted((relative_path, sha256, byte_count), key=relative_path)
)

export_id = sha256(
  capture_mode | source_profile_id | checkpoint_id | ordered_authoritative_artifacts
)
```

Therefore identical bytes returned by page 1 and page 2 share `list_payload_id` but have distinct `list_capture_id`. `first_list_capture_id` in a future Stage 1.6B export means the unique request observation, while a future real-capture consumer must explicitly map `list_payload_id` to the existing Stage 1.6A content-identity concept. No Stage 1.6A change is authorized here.

`semantic_extraction_id` remains a future consumer-derived identity under the Stage 1.6A formula. The producer does not declare source audit eligibility, product family, schedule facts, `system_available_at_ms`, `fact_available_at_ms` or any alpha property.

### 6.2 Required Capture Records

Every authoritative record includes `schema_version`, `capture_mode`, `source_profile_id`, `request_headers_profile_sha256`, `poll_seq`, `record_seq`, `captured_at_ms`, `raw_sha256` when bytes exist, and a record hash.

| Physical time | Meaning | Producer assertion |
|---|---|---|
| `T_list_receive` | complete validated index response received | raw source receipt only |
| `T_article_discovered` | candidate article ID/title extracted from the persisted ListCapture | live first-detection anchor only |
| `T_detail_receive` | complete detail response received | raw source receipt only |
| `T_detail_trusted` | canonical-English detail validation succeeded | trusted raw payload observed only |
| `T_raw_persisted` | atomic content-addressed raw rename completed | record may now reference bytes |

| Record | Required facts | Authority |
|---|---|---|
| `ListCapture` | `list_payload_id`, `list_capture_id`, page, requested/final URL, raw hash/path, response status/type/size, `T_list_receive` | raw source observation only |
| `ArticleDiscovery` | `source_article_id`, title as discovery text, first `list_capture_id`, immutable first-detected time | candidate denominator input; no scope proof |
| `DetailObservation` | article ID, request variant, raw hash/path or failure class, `T_detail_receive`, trust-validation status | raw source observation only |
| `DetailRevision` | article ID, canonical-English raw hash, `T_detail_trusted`, `T_raw_persisted` | canonical body version when trusted |
| `ObserverCheckpoint` | `poll_seq`, prior checkpoint hash, stream offsets/last hashes, candidate-state snapshot, last request sequence, attestation SHA | bounded restart authority only |
| `HistoricalCoverage` | requested range, two sweep transcripts, page failures, candidate terminal counts, complete/incomplete state | historical collection completeness only |
| `terminal_status` | `epoch_complete` or concrete failure reason, final checkpoint ID when available | only terminal status authority |
| `SealedExportManifest` | `status`, capture mode, profile/attestation hashes, checkpoint/terminal hashes, historical range/coverage hash when applicable, all authoritative artifact tuples | only valid local-consumer input |

### 6.3 Historical And Live Temporal Semantics

```text
historical_backfill:
  T_* = actual local observation/extraction times only
  notice_lineage_first_detected_at_ms = null
  system_available_at_ms = null
  fact_available_at_ms = null
  capture_time_status = historical_unknown
  point_in_time_replay_eligible = false

live_observed:
  notice_lineage_first_detected_at_ms = T_article_discovered
  raw_detail_fetched_at_ms = T_detail_receive
  trusted_payload_observed_at_ms = T_detail_trusted
  system_available_at_ms = not produced by this producer
  fact_available_at_ms = not produced by this producer
  point_in_time_replay_eligible = false until a future audited semantic consumer
```

The future semantic consumer alone may derive `system_available_at_ms` after consuming a trusted `DetailRevision`. It must not use `T_list_receive`, `T_detail_receive` or `T_detail_trusted` as a substitute semantic-availability claim.

## 7. Persistence, Resource Boundary And Failure Semantics

### 7.1 Root Layout

```text
stage1_6b/
  source_profile_attestations/<profile-sha256>/source_profile_probe_attestation.json
  historical_backfill/<run-id>/
  live_observation/<run-id>/
    capture_run_contract.json
    source_profile_probe_attestation.json
    raw_payloads/index/<raw_sha256>.bin
    raw_payloads/detail/<source_article_id>/<raw_sha256>.bin
    list_captures/YYYY-MM-DD.jsonl
    article_discoveries.jsonl
    detail_observations/YYYY-MM-DD.jsonl
    detail_revisions.jsonl
    request_manifest/YYYY-MM-DD.jsonl
    observer_heartbeats/YYYY-MM-DD.jsonl
    observer_checkpoint.json
    terminal_status.json
    sealed_exports/<export-id>/
```

Raw bytes are content-addressed and atomically written before a record references their path. Duplicate raw bytes are stored once per root. The implementation may not read a whole root into memory to calculate state, quota or export membership.

### 7.2 Live Resource Policy

Stage 1.6B implements its own narrow stdlib storage guard and does not import the Stage 1.5 guard module. Its lock-path helper must reproduce the Stage 1.5 algorithm locally: resolve `output_root`, walk ancestors until `ancestor.name == "external_signal_shadow" and ancestor.parent.name == "data"`, reject if absent, then use:

```text
<derived-external-signal-shadow-ancestor>/.stage1_5_storage_guard.lock
```

For the approved root layout this resolves to `data/external_signal_shadow/.stage1_5_storage_guard.lock`. The path is a host coordination protocol, not a Stage 1.5 runtime/data dependency. It assumes the VPS local filesystem; NFS/SMB deployment is unsupported.

The future Plan must add and lock these Stage 1.6B SSOT constants:

```text
EXTERNAL_SIGNAL_STAGE1_6B_LIVE_POLL_INTERVAL_SEC = 300
EXTERNAL_SIGNAL_STAGE1_6B_LIVE_ROOT_MAX_BYTES = 256 * 1024 * 1024
EXTERNAL_SIGNAL_STAGE1_6B_LIVE_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES = 4 * 1024 * 1024
EXTERNAL_SIGNAL_STAGE1_6B_LIVE_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES = 1 * 1024 * 1024
EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES = 256 * 1024
EXTERNAL_SIGNAL_STAGE1_6B_MAX_RAW_PAYLOAD_BYTES = 2_000_000
EXTERNAL_SIGNAL_STAGE1_6B_HTTP_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_6B_LIVE_EPOCH_MAX_SECONDS = 7 * 24 * 60 * 60
EXTERNAL_SIGNAL_STAGE1_6B_HISTORICAL_MAX_INDEX_PAGES = 100
EXTERNAL_SIGNAL_STAGE1_6B_HISTORICAL_REQUEST_INTERVAL_SEC = 1.0
EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES = 500
EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_FIRST_ATTEMPT_MAX_POLLS = 2
EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MIN_INTERVAL_SEC = 300
EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MAX_INTERVAL_SEC = 3600
EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MAX_CYCLES = 12
EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MAX_AGE_SEC = 24 * 60 * 60
```

The source-profile probe must reject any response exceeding `2_000_000` bytes or requiring more than `10.0` seconds. Such a probe failure requires a Design delta; the Plan must not relax these limits ad hoc.

Before each live startup and before each poll:

```text
host free bytes >= EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES
normal data:
  root_after_peak <= root_max - ordinary_reserve - emergency_reserve
  host_free_after_peak >= protected_reserve + host_ordinary_reserve + host_emergency_reserve

ordinary control plane:
  root_after_peak <= root_max - emergency_reserve
  host_free_after_peak >= protected_reserve + host_emergency_reserve

terminal control plane:
  root_after_peak <= root_max
  host_free_after_peak >= protected_reserve
  terminal_peak <= 256 KiB
```

`transient_peak_bytes >= max(0, persistent_delta_bytes)` is mandatory. Raw bytes and JSONL capture rows are `normal_data`; routine checkpoint/heartbeat/request-manifest updates are `ordinary_control_plane`; `terminal_status.json` is `terminal_control_plane`.

At startup the Stage 1.6B guard must verify that the existing host emergency reserve can cover the maximum terminal peaks of 1.5D, 1.5F and 1.6B together. It must not alter any existing Stage 1.5 config value.

If a resource check fails, the observer follows the single-authority terminal sequence in Section 7.4, exits non-zero, and never deletes existing evidence to make room. The collector is lower priority than Stage 1.5D/F: failure means no new 1.6B evidence, not relaxed host protection.

### 7.3 Reducer Sequence

`stage1_6a_candidate_discovery_rule_v1` is copied as a frozen semantic rule/version string into the new 1.6B module; it is not imported from Stage 1.6A. Every candidate derived from a persisted ListCapture carries that exact rule version.

Historical pagination is complete only when Sweep A and immediately following Sweep B each fetch pages sequentially from 1, stop only after observing an item with publication time `<= from_ms`, and produce the same ordered transcript:

```text
(page_no, source_article_id, source_published_at_ms)
```

Any duplicate article within a sweep, repeated page payload where page numbers differ, ordering inversion, different A/B transcript, page failure, or failure to reach `from_ms` sets `HistoricalCoverage` incomplete. No sealed export is allowed.

Candidate state is bounded and checkpointed. It contains only unresolved/terminal candidate fields needed to resume: article ID, immutable first discovery fields, lane, attempt/cycle counts, first/last attempt times, next retry time, terminal reason and trusted detail revision ID. Exceeding `MAX_PENDING_DETAIL_CANDIDATES` is a fail-closed capacity failure.

For every live poll and every historical request cycle, select at most one detail candidate:

```text
Lane A: candidate with detail_attempt_count == 0
  order: (first_discovered_poll_seq, source_article_id)
  always selected before Lane B

Lane B: non-terminal candidate with due next_detail_retry_at_ms
  order: (next_detail_retry_at_ms, first_discovered_poll_seq, source_article_id)
  retry interval = min(max_interval, min_interval * 2^(retry_cycle_count - 1))
```

If Lane A cannot be fully attempted within `DETAIL_FIRST_ATTEMPT_MAX_POLLS`, the run records `detail_first_attempt_sla_exceeded` and fails closed rather than silently violating the SLA. A Lane B retry can never consume a request while Lane A is non-empty. After `MAX_CYCLES` or `MAX_AGE_SEC`, the candidate becomes `terminal_detail_failure`; it never becomes a trusted detail or semantic fact. Historical sealed export additionally requires every frozen candidate to be either trusted-detail terminal or terminal-detail-failure; any pending/unattempted candidate makes it incomplete.

For one live poll:

```text
1. Validate startup/checkpoint/profile/resource preconditions.
2. Fetch exactly one index response.
3. Persist raw index bytes atomically, then ListCapture/request-manifest row.
4. Derive new ArticleDiscovery rows; first detection never changes on replay.
5. Select at most one due, unresolved candidate detail.
6. Fetch and validate that detail; persist raw bytes before DetailObservation/DetailRevision.
7. Atomically write ObserverCheckpoint last.
8. Sleep until the next fixed 300-second poll boundary.
```

Network, validation or parse failure writes a bounded request/diagnostic row and leaves the candidate unresolved for a later poll unless the terminal retry limits are reached. It does not mark the candidate in-scope, does not emit a semantic fact, and does not retry in the same poll. A checkpoint with a failed index poll records degraded observation coverage; it does not claim an unobserved time interval was covered.

### 7.4 Crash And Restart Rules

| Crash point | Restart behavior |
|---|---|
| before raw payload rename | ignore owned temporary file; no authoritative record exists |
| raw bytes persisted, record absent | raw orphan is non-authoritative; retain it, then refetch/reconcile by hash without using it as evidence |
| record persisted, checkpoint absent | reconcile bounded uncheckpointed tail; first detection and first trusted observation remain minimum observed time |
| checkpoint persisted | verify committed prefixes and last hashes, then continue from bounded tails; never rewrite previous first-observed values |
| sealed export absent or hash mismatch | local consumer must reject it; active root remains producer-only |

Every append record has monotonic `poll_seq` and `record_seq`. `ObserverCheckpoint` is atomic and stores:

```text
poll_seq
last_request_seq
prior_checkpoint_sha256
per_stream: committed_byte_offset, last_record_hash
candidate_state_snapshot
source_profile_attestation_sha256
```

On restart, the collector verifies each committed prefix boundary and last record hash, then seeks from each recorded byte offset and reads only the bounded tail. With one writer and one checkpoint per poll, it reconciles at most one incomplete poll. It must atomically write a reconciliation checkpoint before admitting any new network request. It never root-scans, rewrites earlier first-observed values, or discards tail evidence silently. A malformed committed prefix, non-monotonic sequence, hash mismatch, or more than one incomplete poll is fail-closed.

For a historical run, evaluate this producer-only predicate after network admission has stopped and the final checkpoint has been atomically written. It must not reference `terminal_status` or a sealed export:

```text
historical_completion_precondition =
  HistoricalCoverage.status == complete
  AND requested_to_ms - requested_from_ms <= 730 days
  AND sweep_a.reached_from_ms == true
  AND sweep_b.reached_from_ms == true
  AND sweep_a.page_failures == []
  AND sweep_b.page_failures == []
  AND sweep_a.transcript_hash == sweep_b.transcript_hash
  AND candidate_terminal_count == frozen_candidate_count
  AND pending_candidate_count == 0
  AND unattempted_candidate_count == 0
  AND final_checkpoint_valid == true
```

Terminal behavior is deliberately single-authority:

1. Stop all network admission and wait for the single in-process write path to finish.
2. Write and validate a final checkpoint if its own reservation admits it; otherwise retain the prior checkpoint and treat completion as failed.
3. For historical mode, evaluate `historical_completion_precondition`. If false, reserve/write `terminal_status.status = failure` with a concrete `historical_*_incomplete` reason and do not seal an export.
4. Only when the mode-specific completion precondition passes, reserve and atomically write `terminal_status.status = complete` last. It is the only artifact permitted to claim completion.
5. Optional diagnostic artifacts are best effort only after independent admission; they are never terminal authority.
6. If `terminal_status.json` cannot reserve/write, write no competing completion claim, exit non-zero, and leave the prior checkpoint as the latest authority.

A normal live epoch ends exactly at `LIVE_EPOCH_MAX_SECONDS`; `terminal_status.reason = epoch_complete`. An operator-requested stop follows the same sequence with `reason = operator_stop`. A historical run may write `terminal_status.reason = historical_backfill_complete` only when `historical_completion_precondition` passes. Only after a valid complete terminal status, no active writer, and no future network work may the process copy bounded artifacts into `sealed_exports/<export-id>/` and write `SealedExportManifest` last. The process exits afterward. Active process sealing is forbidden.

Historical backfill has no same-root resume. A failed local run is retained as incomplete diagnostic evidence; automatic deletion is forbidden. Manual cleanup is outside collection/completion code and requires explicit operator confirmation of exact path and archived/verified hashes. A retry always creates a fresh `<run-id>`.

## 8. Sealed Export And Consumer Boundary

The producer may create a sealed export only after a valid terminal status and no active writer. The export is a new immutable directory containing a bounded capture bundle plus a last-written manifest. It includes the copied probe attestation and `terminal_status.json`, and hashes every authoritative artifact except the manifest itself.

`SealedExportManifest` has this minimum schema:

```text
status
capture_mode
source_profile_id
source_profile_attestation_sha256
checkpoint_id
terminal_status_sha256
requested_from_ms                 # historical only; null for live
requested_to_ms                   # historical only; null for live
historical_coverage_sha256        # historical only; null for live
ordered_authoritative_artifacts
```

```text
generic_sealed_export_acceptance =
  sealed_export_manifest.status == complete
  AND terminal_status.status == complete
  AND checkpoint_id is present
  AND source_profile_id/header hash match all included records
  AND every (relative_path, sha256, byte_count) verifies
  AND capture_mode is homogeneous
```

For `capture_mode == historical_backfill`, the full consumer predicate is `historical_export_acceptance`: it requires `generic_sealed_export_acceptance`, then independently loads and verifies the hashed `HistoricalCoverage` artifact. It repeats only data clauses from the producer precondition; it does not use the producer's prior boolean decision.

```text
historical_export_acceptance =
  generic_sealed_export_acceptance
  AND terminal_status.status == complete
  AND terminal_status.reason == historical_backfill_complete
  AND HistoricalCoverage.status == complete
  AND HistoricalCoverage.requested_from_ms == sealed_export_manifest.requested_from_ms
  AND HistoricalCoverage.requested_to_ms == sealed_export_manifest.requested_to_ms
  AND requested_to_ms - requested_from_ms <= 730 days
  AND sweep_a.reached_from_ms == true
  AND sweep_b.reached_from_ms == true
  AND sweep_a.page_failures == []
  AND sweep_b.page_failures == []
  AND sweep_a.transcript_hash == sweep_b.transcript_hash
  AND candidate_terminal_count == frozen_candidate_count
  AND pending_candidate_count == 0
  AND unattempted_candidate_count == 0
```

Failure of any historical clause rejects the export even when all files, hashes, `terminal_status` and `SealedExportManifest` say `complete`. For `capture_mode == live_observed`, `requested_from_ms`, `requested_to_ms` and `historical_coverage_sha256` must all be null; the historical predicate is inapplicable and `generic_sealed_export_acceptance` remains the complete consumer boundary.

No local audit consumer may read `live_observation/<run-id>/` directly. The future real-capture audit design must decide how separate historical and live sealed exports are combined. This Design deliberately does not remove the current Stage 1.6A fixture-only cap or declare a real source audit pass.

## 9. Acceptance Invariants

| ID | Invariant |
|---|---|
| INV-01 | Stage 1.5D/F source, state, roots, processes, watermark and deployment remain unchanged. |
| INV-02 | Historical and live roots are physically disjoint and every record has exactly one capture mode. |
| INV-03 | Historical downloads never populate `notice_lineage_first_detected_at_ms`, `system_available_at_ms`, `fact_available_at_ms` or PIT eligibility. |
| INV-04 | A live first discovery is anchored to persisted `T_article_discovered`; detail arrival never rewrites it. |
| INV-05 | Only canonical English detail from the attested profile may form a trusted `DetailRevision`; list payloads never form revisions or semantic availability. |
| INV-06 | `list_payload_id` is content identity and `list_capture_id` is request-observation identity; identical bytes on distinct pages cannot collapse into one capture. |
| INV-07 | All raw bytes referenced by an authoritative record exist under the same root and match the recorded SHA-256. |
| INV-08 | An active root is never a local audit input or seal source; only a verified sealed export is consumable. |
| INV-09 | Live observer performs at most one index and one detail request per 300-second poll, with no intra-poll retry or concurrency. |
| INV-10 | Lane A first attempts have precedence; Lane B cannot starve them, and missed first-attempt SLA is terminal rather than silent. |
| INV-11 | Every 1.6B persistent write passes its own guard while holding a locally derived shared lock path; normal and ordinary writes preserve the frozen terminal reserve. |
| INV-12 | Insufficient host/root reserve causes durable fail-closed collector exit; it never deletes evidence or weakens Stage 1.5 reserves. |
| INV-13 | Restart/replay verifies checkpoint prefixes, reads bounded tails only, writes a reconciliation checkpoint before network admission, and preserves content identities and earliest verified observation times. |
| INV-14 | Profile drift, domain/redirect/locale/variant failure, WAF/shell/empty body or malformed response is non-authoritative and cannot create scope/schedule facts. |
| INV-15 | Historical coverage is non-consumable unless the consumer verifies complete range, matching stable sweeps, no page failure and all frozen candidates terminal; producer status alone is insufficient. |
| INV-16 | `terminal_status.json` is the sole terminal completion/failure authority; a missing status cannot be inferred from checkpoint, summary or diagnostic. |
| INV-17 | `source_audit_passed`, PIT validation, market coverage, replay, risk veto, alpha, paper trading, live trading and execution permissions remain false. |
| INV-18 | No code path reads market prices, L2, funding, OI, fees, account endpoints or authenticated Binance resources. |
| INV-19 | A source-profile attestation must predate its run, match static profile/header hashes, be SHA-bound in run contract/checkpoints, copied into the root and included in its export. |
| INV-20 | VPS deployment requires a fresh general Stage 1.5 health predicate, not only a named-event condition. |

## 10. Contract Impact Matrix

| Component | Role | Change | Compatibility requirement |
|---|---|---|---|
| Stage 1.6B models/client/storage/observer | new producer | allowed in future Plan | stdlib-only, isolated from Stage 1.5 runtime |
| `configs/base.py` | Stage 1.6B resource/network SSOT | additive only | no existing config AST change |
| Stage 1.6A fixtures/reducer/runner | future consumer | unchanged in this Design | retain fixture-only cap and historical semantics |
| Stage 1.5D/F/G | unrelated live launch pipeline | unchanged | no imports, roots, deployment or process changes |
| market-data/replay/risk/strategy/execution | downstream research/control | unchanged | no transport, input or authority grant |

## 11. Verification Strategy

Future Plan must use RED tests first and prove at least:

1. `list_payload_id` equality but distinct `list_capture_id` for same bytes from different pages/request sequences; all identity/hash stability;
2. profile/header-attestation hash binding, wrong-domain/redirect/locale/variant rejection, WAF/empty/malformed payload rejection and no Cookie/Auth use;
3. historical timestamp nullability and prevention of PIT promotion; live `T_list_receive` -> `T_article_discovered` -> `T_detail_receive` -> `T_detail_trusted` ordering;
4. list payload change does not create a DetailRevision; canonical detail hash change creates exactly one new revision;
5. two-sweep stable pagination plus inserted item, repeated page, duplicate, order inversion and HTTP 429/5xx failure fixtures;
6. Lane A/Lane B ordering, first-attempt SLA failure, exponential backoff, max cycle/age terminal state, and historical all-candidates-terminal gate;
7. raw-before-record ordering, checkpoint prefix/tail recovery, one-incomplete-poll reconciliation, malformed-prefix failure and first-time immutability;
8. active-seal rejection, normal 7-day terminal state, terminal status as only authority, missing-terminal-status rejection, export full-hash verification and self-hash exclusion;
9. producer writes failure/no export when `historical_completion_precondition` fails; historical consumer rejection for complete terminal/manifest with incomplete coverage, A/B transcript mismatch or one pending detail; complete historical acceptance and live export with null historical manifest fields;
10. root traversal/symlink escape rejection, no Stage 1.5 root input/output, no external network target outside attested profile;
11. normal/ordinary/terminal quota boundaries, shared-lock serialization with simulated 1.5D/F writes, host terminal-reserve sufficiency, terminal-status persistence and no-delete behavior;
12. static imports/AST test rejecting strategy/risk/execution/market-data/account clients and Stage 1.5D/F imports;
13. read-only compatibility tests proving no diff in Stage 1.5D/F and Stage 1.6A production files.

VPS rollout requires a fresh preflight immediately before starting 1.6B. It must prove:

```text
Stage 1.5D runtime gate = ready and heartbeat age <= 2 configured polls + 30 sec
Stage 1.5D storage guard = ready and storage blocker = null
Stage 1.5F active observation count = 0, blocker = null, storage guard = ready
Stage 1.5F heartbeat age <= 2 configured polls + 30 sec
no scheduled Stage 1.5D/F recovery, root migration, restart or cutover
host disk satisfies the existing 8 GiB start threshold
the 1.6B-derived lock path equals the shared host lock path
all authority/trading flags remain false
```

The current `UNITREEUSDT` observation completion and its local-only Stage 1.5G review are a one-time prerequisite for this rollout, not a permanent deployment invariant. After the general predicate passes, the observer must demonstrate two advancing checkpoints, request counts within cap, and unchanged healthy Stage 1.5D/F PID/heartbeat/storage telemetry.

## 12. Rollout And Rollback

1. Implement and test locally first; no network calls in unit tests.
2. Run source-profile probe explicitly and review its attestation before each new historical/live run.
3. Run local historical backfill only after a valid probe; it writes a new local root. Incomplete roots are preserved automatically and never deleted by collection or sealing code.
4. Do not deploy live observer until the current `UNITREEUSDT` Stage 1.5F observation completes, its Stage 1.5G review is performed locally, and the general VPS predicate above passes.
5. VPS deployment starts a new Stage 1.6B live root and does not restart or alter Stage 1.5D/F.
6. On any collector failure, stop only the Stage 1.6B process and preserve its root. Rollback is the absence of the 1.6B process; no Stage 1.5 rollback is involved.

## 13. Explicit Non-Goals And Deferred Work

| Deferred item | Why it is deferred | Owner / prerequisite |
|---|---|---|
| Real Stage 1.6A source-audit authority | Current reducer is fixture-only and real audit consumer must be separately reviewed. | Future real-capture audit Design after verified exports exist. |
| Market-data coverage audit | Requires independent price/L2/funding/OI/fee source and PIT contracts. | Future Stage 1.6C Design. |
| Directional forced-flow replay | Requires pre-registered side, delay, exit, cost and control-group design. | Only after source, PIT and coverage gates pass. |
| Risk-veto enforcement | Changes other strategies' admission behavior. | Future Stage 1.6R integration Design. |
| Continuous unbounded history retention | Violates 30 GiB VPS constraint. | Explicit retention Design only if evidence need justifies it. |

## 14. Open Questions

No implementation-path open question remains.

`source_profile_probe_v1` is a fixed-profile conformity gate. If its response fails the frozen host/path/locale/variant/payload constraints, it blocks the run and yields no fallback guessed endpoint. It does not alter the implementation boundary or authorize a profile substitution.

## 15. Approval Boundary

This Design authorizes neither code nor deployment. It may proceed to an Implementation Plan only after Design review approves:

1. the scope whitelist and Stage 1.5 isolation;
2. content identity versus request-observation identity, stable historical sweeps and bounded detail scheduler;
3. the checkpoint/terminal/sealed-export authority boundary;
4. the 2 GiB VPS resource cap and general fail-closed deployment predicate;
5. the fact that 1.6B produces source provenance only, not a source-audit pass, market-data coverage, replay or trading authority.
