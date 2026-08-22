# Stage 1.6B Delisting Catalog Index Schema Authority Delta Design

**日期:** 2026-08-21
**状态:** `design_draft_for_review`
**类型:** 窄范围 Design delta；补充并优先于下列 Base Design 的冲突条款。
**Base Design:** `docs/designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md`
**Base Design SHA-256:** `83aaa473a9ddb287ee916eae4da327966daa7b0afd5c465f7cc883a06e4f6bc0`
**安全模式:** `research_shadow_mode`; 所有 source-audit、PIT、market-data、replay、risk-veto、paper/live trading 与 execution authority 均保持 `false`。

## 1. Delta 结论与边界

Stage 1.6B v1 的真实 `source_profile_probe_v1` 已在运行前 fail-closed。对以下 Binance 官方 HTTPS 请求的只读诊断显示：

```text
GET https://www.binance.com/bapi/composite/v1/public/cms/article/list/query
  ?type=1&pageNo=1&pageSize=50

HTTP 200
Content-Type: application/json;charset=UTF-8
JSON path present: data.catalogs[].articles
JSON path absent:  data.articles
```

page 1 与 page 2 都包含 `catalog_id = 161`、`catalog_name = Delisting`。该 catalog 的 `total = 426`，且两页的 `releaseDate` 在各自 article list 内递减。响应还有六个无关 catalog，例如 `New Cryptocurrency Listing`、`Latest Binance News`、`Latest Activities` 和 `Maintenance Updates`。

**本 Delta 冻结的唯一修复方向：** Stage 1.6B 只从同一已批准 index 请求响应内、唯一匹配的 `catalog_id = 161` 与 `catalog_name = "Delisting"` catalog 读取 `articles`。不得扫描、合并、排序或补偿其它 catalog；不得新增 endpoint、query 参数、fallback profile 或网络权限。

这是一项 source-profile、capture schema 与 historical completeness 语义变更，不能直接修补为宽松 parser。它不修改 Stage 1.5D/F/G、Stage 1.6A、市场数据、风险 veto 或任何交易代码。

## 2. 已确认事实、假设与决策

### 2.1 已确认事实

1. 当前 v1 client 在 `fetch_index_page()` 中要求 `data.articles` 是 list；真实响应因该路径缺失而返回 `malformed_index_schema`。
2. v1 的 live observer 和 historical backfill 也直接读取 `data.articles`。仅放宽 probe 会导致后续 run 的 `article_count = 0`、候选分母为空，不能解决问题。
3. v1 fixture 同时有合成的 `data.articles` 与空的 `data.catalogs`，因此未覆盖真实 response shape。
4. `catalog_id = 161` 的实时元数据为 `catalog_name = Delisting`。该值及名称必须同时匹配，不能按数组 position 选择。
5. 当前 v1 probe 在 index validation 前退出，未写入 probe attestation；因此没有有效的 v1 source capture root 或 consumable sealed export 需要迁移。

### 2.2 显式假设

1. Binance 可能将未来公告归入其它 catalog。该风险不能通过猜测式聚合解决；本 Delta 的受控语义是 Binance 当前显式 `Delisting` catalog，而非“所有可能含下架词的公告”。
2. `catalog_id = 161` 或名称改变、缺失、重复或 schema 漂移是 profile drift，必须 fail-closed，不能自动选择近似 catalog。
3. 历史 `Delisting` catalog 的分页在每个 page 内按 `releaseDate` 非递增。该假设必须由两次 sweep 的实际 transcript 验证，不能由当前 page 1/2 样本代替。

### 2.3 决策与理由

| ID | 决策 | 理由 |
|---|---|---|
| D-01 | 采用唯一 `catalog_id=161` + `catalog_name="Delisting"` source slice。 | 任务是 futures delisting；明确 catalog 比所有 catalog 合并拥有更小、更可审计的候选分母。 |
| D-02 | source profile 升级为 `binance_public_web_bapi_en_delisting_catalog_v2`。 | profile 不只是 URL/headers；已批准的解析位置和 catalog authority 也改变。v1 不能被新 binary 重新解释。 |
| D-03 | index request URL、headers、HTTPS host、300 秒 live cadence 与所有 storage limits 保持不变。 | 只修 response schema authority，不扩展网络或 VPS 资源风险。 |
| D-04 | `ListCapture` 与 `ArticleDiscovery` 使用 v2 schema 并持久化 selected catalog provenance。 | future consumer 必须能证明候选来自哪个官方 catalog，不能从 raw bytes 外推。 |
| D-05 | historical transcript 在每一项中包含 catalog identity。 | sweep completeness 绑定到唯一 source slice，不能把跨 catalog 文章误当成同一个有序列表。 |
| D-06 | v1 probe attestation、active root、checkpoint 和 sealed export 一律不可由 v2 resume 或消费。 | 避免不同 source profile 下混合 candidate denominator 或 identity。 |

## 3. Allowed Change Scope 与非目标

后续 Implementation Plan 只能触及以下实现/验证类别，最终精确路径由 Plan 的 Task 0 inventory 冻结：

```text
configs/base.py                              unchanged
stage1_6b_canonical_source_models.py         profile/record schema only
stage1_6b_canonical_source_client.py         strict catalog schema validator only
stage1_6b_canonical_source_observer.py       selected-catalog reducer only
run_stage1_6b_source_profile_probe.py        v2 attestation only
run_stage1_6b_historical_backfill.py         v2 transcript/reducer only
run_stage1_6b_live_source_observer.py        profile/root preflight only if required
tests/fixtures/external_signal_shadow/stage1_6b/
tests/research/external_signal_shadow/test_stage1_6b_*.py
tests/scripts/external_signal_shadow/test_run_stage1_6b_*.py
docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md
```

Explicit non-goals:

```text
all-catalog scanning or cross-catalog candidate aggregation
catalogId query parameter, a new endpoint, locale fallback, cookie/session or authentication
automatic catalog ID/name discovery, fuzzy matching or positional catalog selection
Stage 1.5D/F/G or Stage 1.6A code/data/schema modification
VPS deployment, live collector start, historical run, source-audit pass, PIT/replay/risk/trading authority
quota/lock/reserve/config changes
```

If any required implementation lies outside this scope, or if a real response does not satisfy the v2 grammar, implementation stops and a new Design delta is required.

## 4. V2 Source Profile And Index Grammar

The v2 profile keeps the exact existing request transport:

```text
source_profile_id = binance_public_web_bapi_en_delisting_catalog_v2
source_authority = binance_official_content
transport_support_status = undocumented_public_web_profile

index URL = https://www.binance.com/bapi/composite/v1/public/cms/article/list/query
index query = type=1&pageNo={positive_integer}&pageSize=50
index request_variant = bapi_article_list_type_1_delisting_catalog_161_page_50_v2
index source locale = en

selected_catalog_id = 161
selected_catalog_name = Delisting
selected_article_path = data.catalogs[?catalogId==161 && catalogName=="Delisting"].articles[]
```

The index response is trusted for candidate discovery only if all conditions hold:

```text
payload is JSON object
payload.data is object
payload.data.catalogs is list
exactly one catalog is object with:
  catalogId is integer 161
  catalogName is exact ASCII string "Delisting"
  articles is list
  total is a non-negative integer and total >= len(articles)
every selected article is object with:
  code is exactly 32 lowercase/uppercase hexadecimal characters
  title is non-empty string
  releaseDate is an integer but not bool
  1_000_000_000_000 <= releaseDate < 10_000_000_000_000
```

The `releaseDate` interval is the frozen 13-digit Unix-epoch-milliseconds predicate. A 10-digit seconds value, float, string, bool, zero, negative value or out-of-range integer is `malformed_index_schema`; it must never make `reached_from_ms` true.

`data.articles`, a matching ID with a different name, a matching name with a different ID, zero/multiple matching catalogs, an invalid selected article, invalid total, or any malformed container is `malformed_index_schema`. No fallback, skip-invalid-row, flattening, `catalogs[0]`, fuzzy name match or response-order selection is permitted.

Schema drift has one mode-specific durable lifecycle:

```text
probe:
  malformed_index_schema
  -> no attestation write
  -> non-zero exit

historical_backfill:
  malformed_index_schema
  -> durable page_failure(validation=malformed_index_schema)
  -> final valid checkpoint when its reservation admits it
  -> HistoricalCoverage.status = incomplete_schema_failure
  -> terminal_status.status = failure
  -> terminal_reason = historical_index_schema_failure
  -> no sealed export; non-zero exit

live_observed:
  malformed_index_schema
  -> no ListCapture / ArticleDiscovery / candidate-state progress
  -> durable bounded index request/diagnostic row
  -> durable ObserverCheckpoint v2 with last_index_poll_status=malformed_index_schema
     and last_index_poll_coverage=degraded_not_successful
  -> terminal_status.status = failure
  -> terminal_reason = source_profile_schema_drift
  -> no sealed export; non-zero exit
```

The live checkpoint records that a request failed; it must not claim successful source coverage, candidate discovery or a complete observation interval. This checkpoint/terminal sequence remains subject to the existing ordinary/terminal StorageGuard reservation rules. If its terminal write cannot be admitted, the last durable checkpoint/diagnostic remains the authority and the process exits non-zero.

Every `ObserverCheckpoint v2` includes these exact fields:

```text
last_index_poll_status:
  trusted
  | disallowed_redirect
  | empty_payload
  | payload_size_exceeded
  | waf_rejected
  | malformed_json
  | malformed_index_schema
  | http_error
  | network_error

last_index_poll_coverage:
  successful                 # only when status == trusted
  | degraded_not_successful  # for every other listed status
```

Any other status, any other coverage value, or an invalid status/coverage pair is a v2 checkpoint integrity failure. `malformed_index_schema` is the only listed status whose v2 lifecycle is changed by this Delta: it is terminal `source_profile_schema_drift` after the degraded checkpoint. Other existing transport/validation statuses retain the Base Design's failure/retry lifecycle while using the same explicit checkpoint grammar.

An empty but otherwise valid selected `articles` list is valid source receipt. In live mode it yields a `ListCapture` with `article_count = 0`; in historical mode it cannot satisfy `reached_from_ms` and hence cannot make coverage complete by itself.

## 5. Durable Records, Identity And Temporal Rules

### 5.1 Profile and attestation

`source_profile_probe_v2` replaces the v1 command identity. It still performs exactly one index and one exact-ID detail GET under `--live-public-readonly`, writes through the existing Stage 1.6B StorageGuard/shared lock, and records:

```text
source_profile_id = ..._v2
source_profile_sha256 includes:
  existing v1 profile fields
  selected_catalog_id = 161
  selected_catalog_name = Delisting
  selected_article_path

index_article_id_path = data.catalogs[?catalogId==161 && catalogName=="Delisting"].articles[].code
selected_catalog_id = 161
selected_catalog_name = Delisting
selected_catalog_article_count
```

The probe attestation remains valid only for a run with the identical v2 profile/header hash. A v1 attestation fails startup; v2 never writes into the v1 attestation directory because the source profile SHA changes.

The exact authoritative schema-version values are frozen as follows:

```text
SourceProfileProbeAttestation.schema_version = stage1_6b_source_profile_probe_attestation_v2
ListCapture.schema_version                  = stage1_6b_list_capture_v2
ArticleDiscovery.schema_version             = stage1_6b_article_discovery_v2
HistoricalCoverage.schema_version           = stage1_6b_historical_coverage_v2
ObserverCheckpoint.schema_version           = stage1_6b_observer_checkpoint_v2
CaptureRunContract.schema_version           = stage1_6b_capture_run_contract_v1
TerminalStatus.schema_version               = stage1_6b_terminal_status_v1
SealedExportManifest.schema_version         = stage1_6b_sealed_export_v1
```

`ObserverCheckpoint` is v2 because it adds the durable failed/degraded index-poll fields required above. `CaptureRunContract`, terminal status and sealed manifest retain their v1 field schemas; their required `source_profile_id = ..._v2` keeps them profile-isolated. A loader must reject a v1 `HistoricalCoverage` or `ObserverCheckpoint` where a v2 record is required; it must not reinterpret a three-field transcript as v2.

### 5.2 ListCapture and ArticleDiscovery v2

Every v2 `ListCapture` stores, in addition to prior fields:

```text
schema_version = stage1_6b_list_capture_v2
selected_catalog_id = 161
selected_catalog_name = Delisting
selected_catalog_total
article_count = exact len(selected Delisting catalog.articles)
```

`article_count` retains its existing field name but has one v2-only meaning: the exact number of articles in the selected `Delisting` catalog. It is never an aggregate across `data.catalogs`; no second selected-catalog count field is permitted.

Every v2 `ArticleDiscovery` stores:

```text
schema_version = stage1_6b_article_discovery_v2
source_catalog_id = 161
source_catalog_name = Delisting
```

`source_article_id`, `first_list_capture_id`, live first-detection time and candidate rule remain unchanged in meaning. The v2 request variant changes `list_payload_id`; the v2 profile ID then changes `list_capture_id` and `article_discovery_id`. No v1 identity must be preserved across a profile authority change. Detail revision identity remains based on the discovered article ID and the existing detail source identity; it does not gain an unrelated catalog field.

`historical_backfill` still writes null PIT fields only. `live_observed` still anchors first discovery to the selected-catalog `ArticleDiscovery` record. This Delta grants no semantic extraction or fact-availability time.

## 6. Reducer, Sweep, Failure And Restart Contract

The client must expose one small strict selected-catalog extraction result to both the live observer and historical runner. The result is derived from the already validated raw response and is not a second parser or a caller-specific fallback.

The future Plan must implement this as one concrete immutable result, not independent caller parsing:

```text
SelectedDelistingCatalogResult:
  catalog_id: int             # always 161
  catalog_name: str           # always Delisting
  catalog_total: int
  articles: tuple[dict, ...]

extract_selected_delisting_catalog(raw_payload: bytes)
  -> SelectedDelistingCatalogResult
  | raises/returns malformed_index_schema
```

No generic registry, source interface or fallback parser is authorized.

```text
validated index raw bytes
  -> strict unique Delisting catalog selection
  -> selected article list + catalog provenance
  -> persist raw bytes
  -> ListCapture v2
  -> ArticleDiscovery v2 only for frozen title rule matches
```

For each historical sweep the transcript is exactly:

```text
(page_no, selected_catalog_id, source_article_id, source_published_at_ms)
```

`selected_catalog_id` must be `161` in every tuple. Across the concatenated selected-catalog sequence `page1.article1 ... page1.last, page2.first ...`, `releaseDate` must be globally non-increasing. A duplicate `source_article_id` within the selected catalog in one sweep, repeated raw page payload at different page numbers, any within-page or cross-page release-date ordering inversion, missing catalog provenance, A/B transcript mismatch, page failure, or failure to reach `from_ms` makes `HistoricalCoverage` incomplete. It cannot write `terminal_status.status = complete` or a sealed export.

The historical pagination stop condition is evaluated only over the selected catalog's `releaseDate`. Other catalog timestamps and items are semantically invisible to v2, even though they remain inside the content-addressed raw index bytes.

Restart/reconciliation must restore selected-catalog candidate state only from valid v2 checkpoint/record prefixes. A v1 root, checkpoint, record schema, source profile ID, source-profile attestation or sealed export is rejected before reconciliation and before network admission. No migration, replay conversion or data rewrite is authorized.

## 7. V2 Sealed-Export Consumer Acceptance

The Base Design's `historical_export_acceptance` remains necessary but is insufficient for v2. A local consumer must independently parse the hashed authoritative artifacts and require:

```text
v2_historical_export_acceptance =
  base historical_export_acceptance
  AND SealedExportManifest.source_profile_id
      == binance_public_web_bapi_en_delisting_catalog_v2
  AND HistoricalCoverage.schema_version
      == stage1_6b_historical_coverage_v2
  AND every historical transcript item is exactly:
      (positive page_no, 161, 32-hex source_article_id, 13-digit epoch-ms)
  AND all v2 ListCapture records have:
      schema_version == stage1_6b_list_capture_v2
      selected_catalog_id == 161
      selected_catalog_name == "Delisting"
      article_count >= 0
      selected_catalog_total >= article_count
  AND all v2 ArticleDiscovery records have:
      schema_version == stage1_6b_article_discovery_v2
      source_catalog_id == 161
      source_catalog_name == "Delisting"
  AND every v2 ObserverCheckpoint has a recognized
      last_index_poll_status / last_index_poll_coverage pair
```

The consumer must reject malformed tuple shape, an ID other than `161`, invalid millisecond timestamp, missing/wrong catalog provenance, an incompatible record schema, a v1 source profile, or an unrecognized checkpoint poll status. It need not reparse every raw index payload to reimplement the producer parser; it independently verifies the persisted v2 provenance and Base Design hashes/predicates. A historical export with any schema-drift page failure already fails the Base completion predicate and is rejected again here.

## 8. Acceptance Invariants

| ID | Invariant |
|---|---|
| INV-D01 | Only the unique `(catalogId=161, catalogName="Delisting")` object is a v2 candidate source; array position and all other catalogs are non-authoritative. |
| INV-D02 | The exact v2 grammar failure modes are fail-closed. A malformed selected catalog or article cannot be skipped or downgraded to an empty candidate set. |
| INV-D03 | Every v2 probe, run contract, checkpoint and sealed export binds the v2 profile/header hashes; v1 artifacts cannot be resumed or consumed as v2. |
| INV-D04 | Every v2 ListCapture and ArticleDiscovery includes durable catalog ID/name provenance, and its count is selected-catalog-only. |
| INV-D05 | Historical completeness is evaluated solely from the selected catalog with v2 transcript tuples; cross-catalog rows cannot affect reach, order, duplicate or denominator decisions. |
| INV-D06 | Raw index bytes remain verbatim content-addressed evidence even when non-selected catalogs are ignored semantically. |
| INV-D07 | Existing Stage 1.6B storage guard, shared Stage 1.5 host lock, root limits, request rate limits, single writer and terminal/sealed-export predicates remain unchanged. |
| INV-D08 | Stage 1.5D/F/G and Stage 1.6A remain zero-diff and have no v2 runtime dependency. |
| INV-D09 | This Delta does not grant source-audit, PIT, market-data, replay, risk-veto, paper/live trading or execution authority. |
| INV-D10 | Schema drift follows the fixed probe/historical/live lifecycles; live drift always has a durable degraded checkpoint before terminal failure and never creates successful coverage. |
| INV-D11 | A v2 historical export is consumable only when its consumer independently verifies v2 profile, schema, catalog provenance and exact four-field transcript grammar. |

## 9. Verification Strategy

The future Plan must begin with RED tests and must prove:

1. A response with seven catalogs and `Delisting` at nonzero position is accepted only through `catalogId=161` + exact name, not `catalogs[0]`.
2. Top-level `data.articles` with missing selected catalog is rejected, even if it contains syntactically valid articles.
3. Missing, duplicate, wrong-ID, wrong-name, non-list `articles`, invalid `total`, invalid article `code`/`title`/`releaseDate`, a 10-digit seconds timestamp, float/string/bool timestamp, and selected-catalog order inversion all fail closed.
4. Empty valid selected catalog is accepted as a zero-row live `ListCapture.article_count = 0` but cannot complete historical reach.
5. v2 ListCapture/ArticleDiscovery persist exact catalog provenance and `article_count` is selected-catalog-only; no aggregate count is emitted.
6. Same raw response received on different pages/request sequences retains content/request identity rules within v2; a v1 profile artifact is rejected, not rehashed as v2.
7. Historical A/B stable selected-catalog transcripts complete only when both reach the range and their concatenated page sequence is globally non-increasing; selected-catalog duplicate/repeated page/cross-page inversion/mismatch/pending candidate each prevents terminal complete and sealed export.
8. Live and historical runners use the same selected-catalog extractor; no caller reads `data.articles`, `catalogs[0]`, or iterates all catalogs directly.
9. Probe stores the v2 source profile hash and selected catalog path/metadata only after index and detail validation; an index schema failure leaves no attestation file.
10. Live schema drift writes one bounded diagnostic, one degraded `ObserverCheckpoint v2`, then terminal failure without a ListCapture/candidate/complete export; a restart rejects that terminal root before any opener call.
11. Historical schema drift writes `incomplete_schema_failure`, final checkpoint/terminal failure when admitted, and never seals; a consumer rejects a forged complete manifest if its v2 coverage/transcript/catalog provenance is invalid.
12. Existing Stage 1.6B storage, no-network-without-flag, Stage 1.6A read-only compatibility, Stage 1.5 zero-diff and all false authority flag tests continue to pass.

Fixture policy: the Plan must replace the v1 shape fixture with a minimal fixture marked as a structural mirror of the 2026-08-21 read-only live diagnostic. It is a parser test input, not historical source evidence and not an authority grant. No fixture may represent an actual source-audit sample.

## 10. Rollout, Compatibility And Rollback

1. This Design authorizes no code change, local backfill, VPS probe or deployment.
2. A future implementation creates a fresh v2 source-profile attestation only after its tests and approved Plan pass.
3. Every v2 historical or live run uses a fresh root. No v1 root may be resumed, sealed, copied into a v2 export, or passed to Stage 1.6A.
4. Task 0 of the future Plan must inventory every local v1 attestation directory, historical/live root, checkpoint, terminal status and sealed export before implementation. A discovered v1 incomplete artifact remains non-consumable and preserved; it cannot be deleted, resumed or used to satisfy a v2 precondition.
5. Rollback is no Stage 1.6B process. It does not restart, alter or roll back Stage 1.5D/F.

## 11. Open Questions And Approval Boundary

No implementation-path open question remains for this Delta. The deliberate limitation is explicit: a future Binance futures-delisting notice categorized outside `Delisting` is out of v2 scope, not silently recovered from another catalog. Expanding that authority requires a new evidence-backed Design delta.

This Design delta may proceed to an Implementation Plan only after review approves the profile v2 boundary, unique catalog grammar, selected-catalog transcript semantics, v1 rejection and unchanged safety authorities.
