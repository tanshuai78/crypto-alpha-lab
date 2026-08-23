# Stage 1.6A Sealed-Export Historical Source-Audit Adapter Design v2

- **日期:** 2026-08-23
- **状态:** `design_approved`
- **Review Mode:** `closure_confirmation`
- **范围:** Stage 1.6A only；local / offline / read-only / historical audit
- **上游:** one completed Stage 1.6B historical sealed export
- **Supersedes:** `2026-08-22-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design_CN.md`
- **旧 Plan:** `superseded_unapproved_plan`；必须基于本 Design 重新生成
- **不授权:** PIT replay、market replay、risk-veto enforcement、paper/live trading、execution、alpha interpretation、Stage 1.5 修改、Stage 1.6B producer 修改或部署

---

## 0. 结论与 Final Claim

本 Design 只解决：

```text
one exact verified Stage 1.6B historical sealed export
-> frozen Stage 1.6A candidate population
-> verified observation/revision/raw lineage
-> canonical BAPI semantic reduction
-> complete parent outcomes + metrics
-> independently reproducible historical source-audit verdict
```

它不是 collector、retry/repair、历史 replay 或交易策略。

### 0.1 Final Claim

Stage 1.6A 只有在以下条件全部成立时，才允许一个 completed historical source-audit verdict 被消费：

1. exact caller-supplied sealed export 与实际消费 bytes 在 use time 可验证；
2. candidate population 只由权威 `ArticleDiscovery` 冻结，downstream outcome 不能改变 denominator；
3. 每个 candidate 都有完整 discovery -> observation -> revision -> raw lineage；
4. semantic fact 只来自 approved canonical-English BAPI payload；
5. structural corruption 与 denominator-visible source failure 严格分离；
6. 所有 valid upstream/semantic failure 都不能因失败而从 denominator 消失；
7. historical output 永远保持 non-PIT；
8. metrics 从 durable complete parent outcomes 重建，而不是从 success-only rows 推断；
9. completion authority 必须能从 exact source bytes 独立重算；producer 不能自我认证 final pass；
10. 即使 `source_audit_passed=true`，replay/risk/alpha/paper/live/execution authority 仍为 false。

### 0.2 Frozen safety flags

```text
RISK_LIVE_TRADING_ENABLED                = false
trade_signal_allowed                     = false
paper_trading_allowed                    = false
live_trading_allowed                     = false
execution_engine_allowed                 = false
alpha_interpretation_allowed             = false
execution_feasibility_claim_allowed      = false
risk_veto_candidate                      = false
replay_allowed                           = false
point_in_time_directional_replay_allowed = false
```

任何 output、summary、manifest、consumer 都不得升级这些权限。

---

## 1. Scope Freeze

### 1.1 In Scope

1. 读取一个 caller-supplied completed Stage 1.6B `historical_backfill` sealed export。
2. 建立 use-time verified in-memory snapshot。
3. 从 `ArticleDiscovery` 冻结 candidate manifest。
4. 验证 candidate 的 discovery/observation/revision/raw evidence chain。
5. 对 linked trusted canonical-English BAPI bytes 做既有 Stage 1.6A semantic/scope reduction。
6. 写新的 Stage 1.6A derived audit root。
7. 最后写 completion manifest，并由 completed consumer 从 exact source bytes 独立重算。

### 1.2 Explicit Non-Goals

禁止：network/HTTP/websocket/browser、Binance refetch/retry/repair、Stage 1.6B mutation/resume/reseal、Stage 1.5 read/write/import/runtime dependency、历史 price/L2/funding/OI/fee、MAE/MFE/net-edge、directional replay、risk integration、`SignalCandidate`、`TradeIntent`、paper/live execution、VPS deployment、config threshold change。

```text
permissions_changed         = false
persistent_source_changed   = false
Stage_1_6B_changed          = false
Stage_1_5_changed           = false
runtime_processes_changed   = false
deployment_contract_changed = false
new_local_derived_root      = true
new_completed_consumer      = true
```

若未来 Plan 需要把任何 `false` 改成 `true`，必须 STOP 并提交 Design delta。

---

## 2. Authority Basis 与 Reference Evidence

### 2.1 Authority order

```text
L0/L1 safety rules
> current configs/base.py
> approved parent Stage 1.6A source/schema/effective-time contract
> `2026-08-23` Stage 1.6B TerminalStatus field-contract correction
> `2026-08-23` Stage 1.6A adapter derived-artifact schema delta
> approved Stage 1.6B sealed-export/catalog contracts
> this Design v2
> superseded adapter Design/Plan
```

### 2.2 Reference export evidence（不是本轮 current-workspace re-verification）

2026-08-22 保存的 reference export：

```text
data/external_signal_shadow/stage1_6b/historical_backfill/
  hist_delisting_retry_20260822T041106Z/sealed_exports/
  3fbe8e92d83af929913ca16276df3cddf81b26b7327e476b19712870a7792247/
```

已记录事实：250 selected-catalog rows / 5 pages / 35 frozen candidate parents / 33 trusted-detail parents / 2 terminal `network_error` parents。两个 terminal article IDs：

```text
572715f2d96e47769ebbb967c2a6e445
5150d4f0ee1546d7ae6382ba7cda3ffe
```

因此若其余条件相同，source-integrity 上限为：

```text
33 / 35 = 0.942857142857... < 0.95
```

不得删除两个失败 parent 制造 33/33。

### 2.3 Future Plan preflight

任何代码变更前必须重新验证：export path/id、manifest hash、capture mode、source profile/schema、catalog id/name、completed-export terminal accounting、candidate/observation membership、trusted/nontrusted observation identities，以及当前 `configs/base.py` Stage 1.6A values。nontrusted identity 不是独立 per-observation terminal state；其 `detail_unavailable` authority 只能由 Section 6.3 certificate 给出。若 authority field 或 contract shape 改变，STOP；不得用 compatibility alias 绕过。

### 2.4 Confirmed Facts / Assumptions / Decisions / Open Questions

**Confirmed Facts**：当前 1.6B historical sealed export 的 `DetailObservationRecord` 没有 per-observation `terminal_reason`；`HistoricalCoverageRecord` 保存 terminal/pending/unattempted 的 aggregate accounting；`load_sealed_export()` 对 completed historical export 机械验证 terminal status、coverage completion predicate、terminal/pending/unattempted accounting 和 final checkpoint validity。`DetailObservationRecord` 也没有 `source_surface` 或 `source_locale`，但有 `request_headers_profile_sha256`；该两个字段只在 `DetailRevisionRecord` 上存在。

**Assumptions**：本 Design 信任已批准的 1.6B completed-export contract 和 `load_sealed_export()` 的 completion validation；不假设单次 `trust_validation_status=network_error` 自身能证明 terminal lifecycle。

**Decisions**：

1. `detail_unavailable` 的 terminal authority 是 Section 6.3 定义的 completed-export terminal-accounting certificate，不是 `HistoricalCoverage` 单独、也不是单条 nontrusted observation。
2. observation/revision linkage 只比较 observation 实际持有的字段；canonical surface/locale 由 linked revision 的 exact fields 证明。
3. adapter-specific/new projection artifacts 只使用 Section 5.4、Section 12.3-12.6 及 `2026-08-23 Stage 1.6A adapter derived-artifact schema delta` 的 exact schema；Plan 不得自行补字段、删字段或发明 alias。旧 fixture-only artifacts 不是本 adapter 的 output compatibility target。

**Root Cause / Core Issue**：旧 adapter documents 多轮局部 patch 后，将 aggregate historical completion、transport provenance 和 derived durable schema 分散在不同章节，造成 reducer 分支和 completed consumer 无法从同一 authority 集独立重建。本 v2 revision 只闭合这些既有 proof edges，不扩展 collector、network、PIT 或 trading scope。

**Open Questions**：N/A。若 future export 不再满足本 Design 的 completed-export terminal-accounting certificate 或 exact source-profile binding，必须 structural reject 并另写 Design delta；不得在 Plan 中猜测兼容规则。

---

## 3. Frozen Proof Graph

```text
PG-01 caller exact path -> one completed 1.6B historical sealed export
PG-02 sealed manifest -> single-read use-time verified authoritative bytes
PG-03 ArticleDiscovery -> frozen candidate population
PG-04 candidate -> non-empty complete DetailObservation membership
PG-05 trusted observation <-> DetailRevision <-> raw payload
PG-06 trusted raw BAPI -> canonical semantic authority
PG-07 first_list_capture_id -> exact first ListCapture/raw index -> publication corroboration
PG-08 semantic authority -> complete parent declaration -> child scope classification
PG-09 parent outcomes -> exact metric populations
PG-10 metrics + configs/base threshold snapshot -> candidate predicate
PG-11 durable artifacts -> pre-completion summary -> last-written completion manifest
PG-12 completed root + exact source export -> independent source-byte replay consumer
PG-13 rebuilt predicate -> constrained action only -> no replay/risk/alpha/trading authority
```

Proof graph 从本 Design 起冻结。未来 Plan 的 production behavior 必须能映射到 `PG-01..PG-13`；无法映射的新增行为属于 scope expansion。

---

## 4. Authority Matrix（唯一 authority registry）

| Fact / decision | Authority | Diagnostic / corroboration only | Forbidden substitute |
|---|---|---|---|
| input export | caller path + verified manifest `export_id` | directory name after equality check | glob/latest/scan/hardcoded export |
| input completion | existing 1.6B `load_sealed_export()` | operator note | terminal file/copied subset |
| candidate membership | authoritative `ArticleDiscovery` | discovery title | detail-success set/current-page rediscovery |
| first list link | `ArticleDiscovery.first_list_capture_id` | later captures | latest capture |
| observation identity | `request_observation_id` | request time | row position |
| nontrusted terminal accounting | completed-export terminal-accounting certificate | one nontrusted observation / `HistoricalCoverage` alone | inferred retry completion |
| detail trust | observation trust status + linked revision/raw | nontrusted retries | parser success/title |
| detail transport profile | exact observation header-profile hash + profile attestation + run contract | manifest profile ID alone | current header profile / URL inference |
| article identity | BAPI `data.code` | numeric `data.id` | title/array index |
| semantic facts | selected trusted raw BAPI `data.title/body/publishDate` | list title | current webpage/other locale/manual repair |
| publication fact | selected trusted `data.publishDate` | first-list `releaseDate` | later list/current page time |
| revision selection | max `(t_detail_trusted_ms, detail_raw_sha256)` | row order | mtime/filename |
| candidate denominator | frozen candidate manifest | none | success-only parents |
| thresholds | current `configs/base.py` | persisted threshold snapshot | Design literal/default |
| final pass truth | independently rebuilt predicate | persisted completion boolean after equality check | manifest boolean by itself |
| final action | mapping from rebuilt final pass | persisted action after equality check | operator-supplied action |
| PIT availability | none in this adapter | publication fact | extraction time/publication date as visibility |

### 4.1 Producer / writer / loader / consumer / reviewer impact matrix

| Role | This Design's contract | Permitted change | Explicitly forbidden |
|---|---|---|---|
| Stage 1.6B producer | provides one already sealed historical evidence bundle | none; existing completed-export certificate is trusted input | schema/collector/retry/reseal change |
| Stage 1.6A adapter writer | reduces one retained snapshot to a new fresh derived root | writes only Section 12 artifacts | source mutation, raw copy, network, resume |
| Stage 1.6A snapshot loader | validates input binding and Section 5.3 cross-record provenance | one `load_sealed_export()` call plus adapter-owned source-field checks | second latest/scan view or compatibility alias |
| Stage 1.6A completed consumer | independently reconstructs exact source snapshot and reducer result | rejects mismatch/non-consumable root | trusting final boolean/action without rebuild |
| reviewer / operator | supplies exact source export and performs read-only preflight | inspect/review only | manual source repair, terminal-state inference, deployment/trading permission |

---

## 5. Exact Input 与 Snapshot Contract

### 5.1 One explicit sealed export

Resolved source path 必须严格位于：

```text
<project-root>/data/external_signal_shadow/stage1_6b/historical_backfill/
  <run-id>/sealed_exports/<export-id>/
```

必须：directory exists、no symlink escape、parent structure exact、basename == manifest `export_id`、`capture_mode=historical_backfill`、approved profile/schema、`load_sealed_export()` pass。每个 producer/consumer source-snapshot boundary 对 `load_sealed_export()` **exactly one call**；不得在同一 boundary 通过第二次 validator call 获得“更新后的”source view。禁止 glob/latest/parent scan/export-id search/active/unsealed/live root。

### 5.2 Accepted Stage 1.6B contract

```text
source_profile_id                 = binance_public_web_bapi_en_delisting_catalog_v2
SourceProfileProbeAttestation.schema_version = stage1_6b_source_profile_probe_attestation_v2
CaptureRunContract.schema_version = stage1_6b_capture_run_contract_v1
TerminalStatus.schema_version      = stage1_6b_terminal_status_v1
selected_catalog_id               = 161
selected_catalog_name             = Delisting
ListCapture.schema_version        = stage1_6b_list_capture_v2
ArticleDiscovery.schema_version   = stage1_6b_article_discovery_v2
DetailObservation.schema_version  = stage1_6b_detail_observation_v1
DetailRevision.schema_version     = stage1_6b_detail_revision_v1
HistoricalCoverage.schema_version = stage1_6b_historical_coverage_v2
checkpoint.schema_version         = stage1_6b_observer_checkpoint_v2
sealed export schema              = stage1_6b_sealed_export_v1
```

`TerminalStatusRecord` 的 exact terminal field 是 `terminal_reason`，按 `2026-08-23 Stage 1.6B TerminalStatus field-contract correction`；不做 schema guessing 或 `reason` compatibility alias。

### 5.3 Single-read use-time snapshot

1. 通过现有 `load_sealed_export()` 验证 completed-export certificate 的 generic completion contract；Stage 1.6A 不实现第二套 1.6B manifest/hash/coverage validator。
2. 根据 verified manifest 取得 expected artifact tuples，并一次读取 `capture_run_contract.json`、`source_profile_probe_attestation.json`、`observer_checkpoint.json`、`historical_coverage.json`、`terminal_status.json` 与实际 reducer 消费的 JSONL/raw artifacts；每一项校验 path confinement、byte length、SHA-256。
3. 解析 retained contract/attestation bytes，要求：`CaptureRunContract.run_id == checkpoint.run_id == HistoricalCoverage.run_id == TerminalStatus.run_id`；上述 four records 的 `capture_mode=historical_backfill` 与 `source_profile_id` 一致；attestation、manifest 与上述 records 的 `source_profile_id` 一致；`sha256(attestation bytes) == CaptureRunContract.source_profile_attestation_sha256 == checkpoint.source_profile_attestation_sha256 == HistoricalCoverage.source_profile_attestation_sha256`；attestation 的 catalog/profile/header authority 与 manifest 一致。manifest 与 attestation 没有 `run_id`，不得虚构该比较。
4. 每个 DetailObservation 的 `request_headers_profile_sha256 == attestation.request_headers_profile_sha256 == manifest.request_headers_profile_sha256`；不匹配是 whole-export structural reject。
5. parsing/reduction 只使用 retained bytes；snapshot 返回后不得 reopen consumed source path。
6. input snapshot + structural membership/linkage validation 全部通过后，才允许创建正式 Stage 1.6A output root。

关键分层：trusted raw BAPI bytes 在 snapshot layer 只做 path/hash/size/link verification；**invalid JSON 不能在这里 structural reject**。hash-valid trusted raw bytes 的 JSON/envelope 失败由 semantic reducer 转成 denominator-visible `malformed_bapi_envelope`。

### 5.4 Source receipt

`source_export_receipt.json` 只保存 binding，不复制 raw evidence：

```text
schema_version = stage1_6a_source_export_receipt_v1
artifact_profile_version = stage1_6a_sealed_export_source_audit_v2
input_export_id
input_manifest_sha256
capture_mode
source_profile_id
historical_range_from_ms
historical_range_to_ms
historical_coverage_sha256
capture_run_contract_sha256
source_profile_probe_attestation_sha256
consumed_artifacts[] = {relative_path, artifact_class, sha256, byte_length}
```

`consumed_artifacts` 排序 `(artifact_class, relative_path, sha256)`。Receipt 不保存 source filesystem location；future consumer 必须由 caller 再次明确提供 exact source export。

---

## 6. Candidate / Observation / Revision Lineage

### 6.1 Frozen denominator

Candidate key = `source_article_id`，membership 只来自全部 authoritative `ArticleDiscovery`，并在任何 detail availability、BAPI parse、mapping、classification、publication outcome 前冻结。downstream failure 不能删除 candidate。

### 6.2 Observation set must be total

对每个 frozen candidate：

```text
parent_observations MUST be non-empty
```

zero observations = incomplete upstream evidence = **whole-export structural reject**；不得因 Python `all([])` 被错分为 terminal `detail_unavailable`。

同时，每个 `DetailObservation.source_article_id` 必须属于 frozen candidate set；foreign observation structural reject。每条 observation 的 `request_observation_id` 必须 non-empty 且全局唯一；missing/duplicate structural reject。每个 candidate 的 observation set 必须 non-empty；trust aggregation 不得以 row order、request time 或 Python dict last-write-wins 决定。

### 6.3 Trust aggregation

```text
completed_export_terminal_accounting_certificate =
  load_sealed_export(export) passes
  AND terminal_status.status == complete
  AND terminal_status.terminal_reason == historical_backfill_complete
  AND historical_coverage_is_complete(HistoricalCoverage)
  AND HistoricalCoverage.candidate_terminal_count
      == HistoricalCoverage.frozen_candidate_count
  AND HistoricalCoverage.pending_candidate_count == 0
  AND HistoricalCoverage.unattempted_candidate_count == 0
  AND HistoricalCoverage.final_checkpoint_valid == true
  AND every frozen candidate has a non-empty, in-set observation membership

if >=1 trusted observation:
  trusted aggregate governs;
  nontrusted sibling retries do not downgrade parent

elif observation set non-empty
     AND completed_export_terminal_accounting_certificate passes:
  detail_authority_status = detail_unavailable
  parent remains denominator-visible

else:
  whole-export structural reject
```

这里的 terminal conclusion 是 **parent-level completed-export certificate**：它证明 historical producer 已将 frozen candidate population terminally accounted，且没有 pending/unattempted candidate；它不声称任一单条 `network_error` observation 自身包含 terminal state。若 certificate 不成立，或 future source contract 不再支持该结论，whole-export structural reject。`HistoricalCoverage` 单独不是 terminal authority。

### 6.4 Bidirectional trusted linkage

每个 trusted observation 必须且只能匹配一个 logical `DetailRevision`，并匹配 observation 实际持有的 article/raw SHA/raw path/profile/variant/header-profile binding。linked revision 必须为 `source_surface=announcement_detail`、`source_locale=en`，并匹配 article/raw SHA/raw path/profile/variant；每个 `DetailRevision` 也必须至少由一个 trusted observation 支撑。不得比较 observation schema 中不存在的 surface/locale 字段。orphan、ambiguous、hash/path/article/profile/variant/header-profile mismatch、revision surface/locale mismatch、missing raw bytes 均 structural reject。

### 6.5 Logical revisions

相同 article + same trusted raw SHA = one logical revision；不同 raw SHA = distinct revisions。Selected parent revision = max `(t_detail_trusted_ms, detail_raw_sha256)`。只允许 persisted exact `t_detail_trusted_ms`；不得 alias 成其它 timestamp。

多 trusted revisions 若出现 incompatible symbol set、product classification 或 same schedule fact conflict：`parent_declaration_status=revision_conflicting`，mapping/classification fail/unresolved，no eligible child；禁止挑旧 revision 制造 completeness。若 source provenance/body authority 本身完整，revision conflict 不自动 fail source-integrity。

---

## 7. Canonical BAPI Semantic Contract

### 7.1 Same-payload authority

Selected trusted raw payload 的 semantic fields：

```text
data.code
data.id          # optional numeric diagnostic only
data.title
data.body
data.publishDate
```

`data.id` 不得作为 article identity；list title 只能 candidate discovery，不能提供 symbol/product/schedule/publication authority。

### 7.2 Envelope identity split

```text
data not object                         -> malformed_bapi_envelope
data.code absent/non-string            -> malformed_bapi_envelope
present string data.code != article_id -> WHOLE-EXPORT STRUCTURAL REJECT
```

缺失/shape failure 是 payload quality；明确指向另一 article 的 present identity 是 lineage contradiction。

### 7.3 Exact body grammar

`data.body` 必须是 string，并解析为：

```text
root:    exact keys {node,child}; node=root; child=array
element: keys subset {node,tag,attr,child}; node=element;
         tag in {a,br,em,h3,h4,li,p,span,strong,table,tbody,td,tr,u,ul};
         attr absent/object; child absent/array
text:    exact keys {node,text}; node=text; text=string
other:   body_parse_unresolved
```

额外 fail-closed：`br.child` 必须 absent 或 `[]`；non-empty `br.child` => `body_parse_unresolved`。

Traversal：child 按数组顺序；text emit text；`br` emit LF；`p,h3,h4,li,tr,td` 在 children 前后 emit LF；其它 allowed element transparent recursion。Normalization 固定：CRLF/CR→LF -> NFKC -> horizontal whitespace runs→single space -> trim spaces around LF -> LF runs→one LF -> strip edge space/LF。

```text
body_normalization_version = stage1_6a_bapi_body_tree_v1
semantic_extractor_version = stage1_6a_extractor_v1
```

未知 shape/tag/key 不得静默忽略；一律 `body_parse_unresolved`。

---

## 8. Publication Time 与 Historical Non-PIT

### 8.1 First-list chain is structural for every candidate

在任何 detail status branching 前，对**全部 candidate**验证：

```text
ArticleDiscovery.first_list_capture_id
-> exactly one ListCapture
-> declared raw-index tuple
-> catalog 161 / Delisting
-> same article code
-> valid releaseDate
```

missing/duplicate/mismatch/invalid releaseDate = whole-export structural reject，即使该 parent 后续是 terminal network error 或 malformed BAPI。

### 8.2 Publication authority

唯一 publication fact authority = selected trusted `data.publishDate`；first-list `releaseDate` 只 corroboration；later captures 只 diagnostic。

Valid epoch-ms：`type(value) is int`（bool 禁止）且 `1_000_000_000_000 <= value < 10_000_000_000_000`。

```text
publishDate invalid/unparseable:
  source_published_at_ms=null; no event_day;
  does NOT alone fail source_integrity

publishDate valid == valid first releaseDate:
  publication_time_status=present

publishDate valid != valid first releaseDate by >=1ms:
  publication_time_status=conflicting
  source_integrity_parent_pass=false
  no event_day
```

### 8.3 Historical honesty

所有 derived parent/child：

```text
capture_mode                        = historical_backfill
semantic_extracted_at_ms            = actual local extraction time
notice_lineage_first_detected_at_ms = null
system_available_at_ms              = null
fact_available_at_ms                = null
capture_time_status                 = historical_unknown
point_in_time_replay_eligible       = false
risk_veto_candidate                 = false
```

`source_published_at_ms` 只证明 source asserted publication fact，不证明系统当时已拥有事实。Offline T2 extraction/review 不得 retroactively upgrade T1 availability。

---

## 9. Parent / Child Scope

Eligible child iff：parent declaration complete AND `margin_family=USD_M` AND `contract_type=PERPETUAL` AND `underlying_family=crypto_asset`。

COIN-M、delivery、spot、margin/loan/convert、fully evidenced non-crypto/TradFi 等必须被显式 accounted 为 out-of-scope。Batch notice 的所有 declared children 必须 deterministically accounted；任一 child unresolved/corrupt => parent incomplete/unresolved => **no eligible child subset**。禁止 mixed batch cherry-pick。

---

## 10. Failure Matrix（structural vs denominator 的唯一权威）

| Condition | Whole export | Candidate denominator | Source numerator | Mapping/classification | Child |
|---|---|---:|---:|---|---|
| invalid/escaping path | REJECT | N/A | N/A | N/A | none |
| unsealed/wrong profile/catalog/coverage | REJECT | N/A | N/A | N/A | none |
| malformed required control JSON/JSONL | REJECT | N/A | N/A | N/A | none |
| zero observations | REJECT | N/A | N/A | N/A | none |
| foreign observation | REJECT | N/A | N/A | N/A | none |
| missing/duplicate observation identity | REJECT | N/A | N/A | N/A | none |
| broken first-list chain | REJECT | N/A | N/A | N/A | none |
| trusted obs/revision/raw mismatch/orphan/ambiguity | REJECT | N/A | N/A | N/A | none |
| raw path/hash/manifest mismatch | REJECT | N/A | N/A | N/A | none |
| present wrong string `data.code` | REJECT | N/A | N/A | N/A | none |
| nontrusted observation set + completed-export terminal-accounting certificate | ACCEPT | yes | fail | N/A | none |
| nontrusted observation set but terminal-accounting certificate absent/invalid | REJECT | N/A | N/A | N/A | none |
| trusted linked raw invalid JSON | ACCEPT | yes | fail | fail/N/A | none |
| malformed BAPI data/code shape | ACCEPT | yes | fail | fail/N/A | none |
| body grammar unresolved | ACCEPT | yes | fail | fail | none |
| publishDate unparseable only | ACCEPT | yes | unchanged by fact alone | normal rules | possible |
| publishDate/releaseDate conflict | ACCEPT | yes | fail | normal rules | no event-day authority |
| optional schedule fact missing/unparseable | ACCEPT | yes | unchanged by fact alone | completeness rules | only if complete |
| incomplete symbol/product declaration | ACCEPT | yes | per source predicate | fail/unresolved | none |
| multi-revision semantic conflict | ACCEPT | yes | may pass if source authority complete | fail/unresolved | none |
| trusted + terminal nontrusted sibling | ACCEPT | yes | trusted aggregate governs | normal | possible |
| crash before completion | partial root non-consumable | N/A | N/A | N/A | none |
| completed consumer mismatch | consumer rejects root | N/A | N/A | N/A | none |

Structural reject 产生 **no parent outcomes / no metrics / no summary / no completion manifest**。只要 upstream structural chain 完整，payload/semantic quality failure 就必须 denominator-visible，不能用“解析失败所以忽略”提高 rate。

---

## 11. Metrics 与 Verdict

### 11.1 Threshold SSOT

唯一 runtime authority = current `configs/base.py`。Expected approved historical gates：

```text
MIN_HISTORICAL_EVENTS              = 30
MIN_EVENT_DAYS                     = 10
MIN_SYMBOLS_WITH_EVENTS            = 3
MIN_SOURCE_INTEGRITY_RATIO         = 0.95
MIN_SYMBOL_MAPPING_RATIO           = 0.95
MIN_EVENT_TYPE_CLASSIFICATION_RATIO= 0.95
MAX_FORBIDDEN_PAYLOAD_COUNT        = 0
```

具体完整常量名必须沿用现有 `EXTERNAL_SIGNAL_STAGE1_6A_*`。Live-only `MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES` 不由本 historical adapter 消费/snapshot。Plan preflight 若发现 current config 与 approved parent contract 不一致，STOP；不得 hardcode fallback。

```text
audit_metric_definition_version = stage1_6a_audit_metric_v1
```

### 11.2 Metric populations

| Metric | Population |
|---|---|
| source integrity | numerator = parent outcome pass；denominator = **all frozen candidates** |
| symbol mapping | numerator = trusted-aggregate parents with complete declared contract set/all children accounted；denominator = trusted-aggregate candidate futures-delisting parents |
| event classification | numerator = trusted-aggregate parents deterministically in-scope or fully-accounted out-of-scope；denominator = all trusted-aggregate candidate parents |
| historical_events_found | distinct eligible parent article IDs；batch counts once |
| event_days | distinct UTC publication dates with `present` status among historical events；never settlement date |
| symbols_with_events | distinct eligible child canonical symbols |
| forbidden_payload_count | distinct Stage 1.6A forbidden-authority attempt observation identities |

Frozen `source_integrity_parent_pass`：canonical source bytes persisted in sealed export AND trusted canonical-English detail linked AND immutable provenance complete AND BAPI envelope/body establishes semantic authority AND no publication conflict。

必定 denominator-visible fail：`detail_unavailable`、`malformed_bapi_envelope`、`body_parse_unresolved`、`publication_time_conflicting`。

### 11.3 Candidate verdict

复用 parent Stage 1.6A predicate：

```text
source_schema_integrity_passed =
  canonical-English authority is present for every parent counted in historical_events_found
  AND source_integrity_pass_rate >= configured threshold
  AND symbol_mapping_pass_rate >= configured threshold
  AND event_type_classification_pass_rate >= configured threshold
  AND available_at_policy_defined == true
  AND forbidden_payload_count <= configured threshold

sample_sufficiency_passed =
  historical_events_found >= threshold
  AND event_days >= threshold
  AND symbols_with_events >= threshold

source_audit_evidence_candidate_passed =
  source_schema_integrity_passed AND sample_sufficiency_passed
```

本 historical adapter 的 `available_at_policy_defined=true` 只表示 null/`historical_unknown` policy 被机械执行，不表示 PIT validated。

---

## 12. Derived Persistence 与 Diagnostics

### 12.1 Fresh output root

```text
data/external_signal_shadow/stage1_6a/sealed_export_source_audits/<audit-run-id>/
```

禁止 overwrite/resume existing root。

### 12.2 Minimum artifacts

```text
source_export_receipt.json
audit_candidate_manifest.json
parent_audit_outcomes.jsonl
detail_revisions.jsonl
semantic_extractions.jsonl
delisting_notices.jsonl
delisting_contracts.jsonl
audit_diagnostics.jsonl
stage1_6a_futures_delisting_source_audit_summary.json
completion_manifest.json  # LAST
```

不复制任何 Stage 1.6B raw bytes/control-plane artifacts。

### 12.3 Exact adapter projection profile and parent outcome schema

adapter-specific artifacts `source_export_receipt.json`、`parent_audit_outcomes.jsonl`、`detail_revisions.jsonl`、`audit_diagnostics.jsonl`、summary 与 completion manifest 必须有 `artifact_profile_version=stage1_6a_sealed_export_source_audit_v2`，并遵从本 Design 的 exact schemas。`audit_candidate_manifest.json`、`semantic_extractions.jsonl`、`delisting_notices.jsonl`、`delisting_contracts.jsonl` 的 adapter-specific exact schemas 由 `2026-08-23 Stage 1.6A adapter derived-artifact schema delta` 冻结；本 adapter 不读取、迁移或重定义旧 fixture-only output。

每个 frozen candidate 恰有一条 `stage1_6a_parent_audit_outcome_v1`，exact keys：

```text
schema_version, artifact_profile_version, source_article_id, capture_mode,
semantic_extracted_at_ms, notice_lineage_first_detected_at_ms,
system_available_at_ms, fact_available_at_ms, capture_time_status,
point_in_time_replay_eligible, risk_veto_candidate,
detail_authority_status, selected_detail_revision_id,
source_integrity_parent_pass, source_published_at_ms, publication_time_status,
parent_declaration_status, mapping_status, classification_status,
eligible_child_count, diagnostic_codes
```

Exact enums：`detail_authority_status in {trusted, detail_unavailable, malformed_bapi_envelope, body_parse_unresolved}`；`publication_time_status in {not_evaluable, unparseable, present, conflicting}`；`parent_declaration_status in {not_evaluable, complete, incomplete, revision_conflicting, unresolved}`；`mapping_status in {not_evaluable, pass, fail}`；`classification_status in {not_evaluable, in_scope, out_of_scope, fail}`。`diagnostic_codes` 是 sorted unique string array；所有 historical/PIT fields 必须满足 Section 8.3。Structural reject 不允许产生 `linkage_rejected` 或任何 partial outcome row；它应在 output creation 前失败。

### 12.4 Derived revision projection exact schema

`detail_revisions.jsonl` 仅保存 derived audit projection，exact keys：

```text
schema_version, artifact_profile_version, source_article_id,
detail_revision_id, detail_raw_sha256, raw_payload_relative_path,
t_detail_trusted_ms, source_surface, source_locale, request_variant,
bapi_numeric_id, detail_authority_status, selected_for_parent
```

其中 `schema_version=stage1_6a_detail_revision_projection_v1`；它不是 raw source stream copy。

### 12.5 Diagnostics exact schema freeze

`audit_diagnostics.jsonl` **只**保存 Stage 1.6A 自己发生的 `forbidden_semantic_authority_attempt`。每一行 exact keys：

```text
schema_version, artifact_profile_version, diagnostic_type,
observation_identity, source_article_id, source_surface, source_locale,
request_variant, raw_payload_sha256, violation_class, attempted
```

`schema_version=stage1_6a_audit_diagnostic_v1`；`diagnostic_type=forbidden_semantic_authority_attempt`；`observation_identity` 的值必须是对应 upstream `DetailObservation.request_observation_id`，不得另造 identity；`attempted=true`。普通 network/malformed/publication/revision outcomes 只通过 Stage 1.6B evidence + `parent_audit_outcomes.diagnostic_codes` 表达。`forbidden_payload_count=count(distinct observation_identity)`；“被正确拒绝”本身不等于“尝试作为 semantic authority”。

### 12.6 Summary and completion exact authority schemas

所有 key set 都是 exact set；缺失或额外 key 均为 completed-consumer rejection。`threshold_snapshot` 的 exact keys 只能是：

```text
EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS
EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS
EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS
EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO
EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO
EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO
EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT
```

`metrics` 的 exact keys：

```text
candidate_total_denominator
trusted_parents_count
symbols_mapped_count
classified_parents_count
forbidden_payload_count
source_integrity_pass_rate
symbol_mapping_pass_rate
event_type_classification_pass_rate
historical_events_found
event_days
symbols_with_events
```

`authority_flags` 的 exact keys 与 required values：

```text
RISK_LIVE_TRADING_ENABLED, trade_signal_allowed, paper_trading_allowed,
live_trading_allowed, execution_engine_allowed, alpha_interpretation_allowed,
execution_feasibility_claim_allowed, risk_veto_candidate, replay_allowed,
point_in_time_directional_replay_allowed, point_in_time_source_validated,
market_data_coverage_passed
```

每个以上 key 的 value 必须 exact `false`。`source_audit_evidence_candidate_passed` 与 `source_audit_passed` 不属于 `authority_flags`。

Pre-completion summary 的 `schema_version=stage1_6a_source_audit_summary_v1`，exact top-level keys：

```text
schema_version
artifact_profile_version
audit_run_id
source_export_receipt_sha256
input_export_id
input_manifest_sha256
audit_metric_definition_version
candidate_discovery_rule_version
audit_candidate_manifest_sha256
body_normalization_version
semantic_extractor_version
threshold_snapshot
metrics
available_at_policy_defined
source_schema_integrity_passed
sample_sufficiency_passed
source_audit_evidence_candidate_passed
audit_summary_state
source_audit_passed
allowed_next_action
permitted_design_options
authority_flags
```

`candidate_discovery_rule_version=candidate_discovery_rule_v1`；`audit_candidate_manifest_sha256=SHA-256(exact persisted audit_candidate_manifest.json bytes)`。二者必须与 derived candidate manifest 的 profile/content 一致；summary 的 fixed pre-completion values 由 Section 13.1 定义。`completion_manifest.json` 的 `schema_version=stage1_6a_source_audit_completion_manifest_v1`，exact top-level keys：

```text
schema_version
artifact_profile_version
status
audit_run_id
source_export_receipt_sha256
input_export_id
input_manifest_sha256
audit_metric_definition_version
body_normalization_version
semantic_extractor_version
threshold_snapshot
metrics
available_at_policy_defined
source_schema_integrity_passed
sample_sufficiency_passed
source_audit_evidence_candidate_passed
source_audit_passed
allowed_next_action
permitted_design_options
authority_flags
authoritative_artifacts
completed_at_ms
```

`status=complete`。`authoritative_artifacts` 是按 `(relative_path, sha256)` 排序的 array；每一个 element exact keys 为：

```text
relative_path, sha256, byte_length
```

它必须列出 Section 12.2 中除 `completion_manifest.json` 外的全部 artifact，且逐一 hash/byte-length 匹配。`permitted_design_options` 只能是 `[]`，或按该固定顺序的 `[write_live_source_observation_design_only, write_ex_post_diagnostic_design_only]`；`allowed_next_action` 必须符合 Section 13.5 的 deterministic mapping。summary 与 completion 的 `metrics`、`threshold_snapshot`、`authority_flags` 适用上文 exact nested contracts。

---

## 13. Completion Authority 与 Completed Consumer

### 13.1 Pre-completion summary

在 completion manifest 前，summary 还必须满足 Section 12.6 exact schema：

```text
audit_summary_state                    = pre_completion
source_audit_evidence_candidate_passed = true|false
source_audit_passed                    = false
allowed_next_action                    = pending_completion
permitted_design_options               = []
```

### 13.2 Producer completion order

```text
verified source snapshot
-> reducer
-> durable derived artifacts
-> pre-completion summary
-> reread durable derived artifacts
-> rebuild all metric populations + candidate predicate
-> exact compare
-> completion_manifest.json atomic write LAST
```

Only completion manifest may persist final `source_audit_passed`、`allowed_next_action`、`permitted_design_options`；其 exact schema/hashes/bindings 必须满足 Section 12.6，并覆盖全部 authoritative derived artifacts、source receipt、input export ID/manifest SHA。

### 13.3 Independent completed consumer

Consumer 输入 = completed audit root + caller-supplied exact source export；禁止 source scan/latest/search。必须：verify local artifact hashes -> verify receipt/source binding -> reconstruct same source snapshot -> rerun structural + semantic reducer -> rebuild deterministic artifacts/metrics -> rebuild candidate predicate -> compare persisted authority projection。

核心规则：

```text
rebuilt_final_pass = evaluate rebuilt metrics/predicate
require completion_manifest.source_audit_passed == rebuilt_final_pass
expected_action/options = deterministic mapping(rebuilt_final_pass)
require persisted action/options == expected_action/options
```

**不得从 persisted final boolean 推导 rebuilt truth。** 即使 boolean + action/options 被一起改得内部自洽，只要不等于 source-byte rebuilt predicate，consumer 必须 reject。

### 13.4 Threshold drift

Summary snapshot 只保存本 adapter 实际消费的七个 historical config keys。Current-policy consumer 还必须要求 persisted snapshot == current `configs/base.py` values；不一致则拒绝 current-policy consumption。不得用新 threshold 静默改写旧 verdict，也不得用旧 threshold 冒充 current pass。若未来需要 multi-policy reinterpretation，另写 Design。

### 13.5 Final action mapping

```text
rebuilt_final_pass=false
-> source_audit_failed_or_inconclusive
-> permitted_design_options=[]

rebuilt_final_pass=true AND point_in_time_source_validated=false
-> write_live_source_observation_design_only
-> options=[write_live_source_observation_design_only,
            write_ex_post_diagnostic_design_only]
```

本 adapter 永远不授权 replay implementation、market-data pass、risk-veto enablement、paper/live/execution。

---

## 14. Lifecycle / Crash / Idempotency Matrix

| State/event | Required behavior |
|---|---|
| path/source/structural preflight fail | fail before output root |
| structural checks pass | create fresh output root |
| derived write fail | partial root non-consumable |
| crash before summary | non-consumable |
| crash after summary before manifest | summary remains pre-completion；non-consumable |
| completion write succeeds | may be offered to completed consumer |
| source export missing/mutated later | consumer rejects/non-consumable |
| derived artifact mutated | consumer rejects |
| final boolean/action mutated | rebuilt predicate/action comparison rejects |
| threshold changed | current-policy consumer rejects；no silent reinterpretation |
| rerun same source | new run-id；deterministic semantic projection must match |
| old partial audit root | no resume/repair；start fresh run-id |

第一版明确不实现 resume/checkpoint/recovery state machine；对 immutable source 重新跑新 root 比修复 partial root 更安全。

Determinism：same source bytes/profile/schema/extractor/normalizer/config => same candidate membership/hash、logical revision IDs、selected revisions、semantic IDs、parent outcome authority projection、notice/contract identities、metric populations、candidate/final action mapping。允许变化仅限 `audit_run_id`、local extraction time、write/completion timestamps；这些不得进入 semantic identity/metrics/PIT authority，只能通过 schema-defined run-metadata comparison projection 排除。

---

## 14.1 Compatibility / Migration / Rollback

旧的 2026-08-22 adapter Design 与其 unapproved Plan 是 superseded historical references，不是 compatibility target。既有 `run_stage1_6a_futures_delisting_source_audit.py --fixture-run` 和 Stage 1.6A fixture contract 保持 unchanged；本 adapter 使用独立 CLI、独立 output root 和 `artifact_profile_version=stage1_6a_sealed_export_source_audit_v2`，不读取/写入旧 fixture root。

第一版没有 artifact migration：旧或 partial adapter root 一律 non-consumable，不得 resume/repair/upgrade。rollback 是停止新 adapter invocation；已完成 root 保留为只读 evidence，不能授权 PIT/replay/risk/trading。因为本 Design 不部署进程、不改 config、不改 1.6B producer，所以没有 runtime rollback procedure。

---

## 15. TCB / Threat Boundary Freeze

### 15.1 Protected By This Design

wrong export/path escape/silent latest、manifest-artifact mismatch、TOCTOU source replacement、candidate denominator manipulation、zero-observation laundering、foreign observation contamination、observation/revision/raw mismatch、wrong-article BAPI identity、title/current-web semantic leakage、historical→PIT hindsight upgrade、partial batch cherry-pick、success-only metric self-certification、partial root mistaken complete、derived artifact mutation、final boolean/action self-certification、threshold silent reinterpretation。

### 15.2 Explicitly Trusted

Python interpreter + stdlib basic correctness、SHA-256 collision resistance、local filesystem basic read/atomic replace semantics、existing approved 1.6B `load_sealed_export()` correctness、existing approved Stage 1.6A identity/metric contracts where explicitly reused、`configs/base.py` SSOT、non-malicious local operator supplying project root + exact source path。

### 15.3 Out Of Scope

malicious root coherently rewriting source+manifest+audit+code、compromised kernel/filesystem/Python/stdlib、SHA-256 cryptographic break、host-level adversarial tampering、supply-chain compromise、malicious privileged operator defeating all local evidence coherently。

Closure Confirmation 不得在没有 material scope expansion 的情况下继续向 TCB 内部深入；若要防这些威胁，另写 host/deployment attestation Design。

---

## 16. Acceptance Invariants

| ID | Invariant |
|---|---|
| INV-01 | 只消费一个 explicit caller-supplied、path-confined、completed historical sealed export；no scan/glob/latest。 |
| INV-02 | consumed authoritative bytes use-time hash/size verified and retained；trusted BAPI invalid JSON 不在 snapshot layer structural reject。 |
| INV-03 | ArticleDiscovery 在 downstream outcomes 前冻结完整 denominator；失败不能改变 membership。 |
| INV-04 | 每 candidate observation set 非空；每 observation 属于 candidate set且 identity 唯一，否则 export reject。 |
| INV-05 | `detail_unavailable` 只由 completed-export terminal-accounting certificate + non-empty no-trusted observation set 得出；单条 nontrusted observation 或 HistoricalCoverage alone 都不是 terminal authority。 |
| INV-06 | trusted observation <-> revision <-> raw evidence 双向闭合；observation header-profile、attestation、run contract、manifest 绑定一致；任何 orphan/ambiguous/hash/path/profile/variant/header/surface/locale mismatch reject。 |
| INV-07 | semantic authority 只来自同一 trusted canonical-English BAPI；`data.id` diagnostic-only；list title discovery-only。 |
| INV-08 | present wrong string `data.code` structural reject；missing/non-string code 或 invalid JSON 是 denominator-visible malformed parent。 |
| INV-09 | 所有 candidate 的 first-list chain 在 detail branching 前验证；publishDate authority，first releaseDate corroboration。 |
| INV-10 | detail_unavailable/malformed/body unresolved/publication conflict 均保留 denominator 并 fail source numerator。 |
| INV-11 | publishDate unparseable alone不自动 fail source integrity；missing/unparseable facts显式状态、禁止 inference。 |
| INV-12 | revision selection deterministic；semantic conflict不得 cherry-pick，mapping/classification fail/unresolved。 |
| INV-13 | parent/children 未全部 accounted 时不得输出 eligible subset。 |
| INV-14 | historical PIT fields保持 null/unknown；replay/risk/alpha/paper/live/execution authority exact false。 |
| INV-15 | 每 candidate 恰有一个 exact-schema durable parent outcome；metrics从完整 parent population rebuild；structural reject无 metric rows。 |
| INV-16 | summary 只有 candidate authority；completion manifest last-write 才有 final pass/action authority，且两者均满足 exact output schema。 |
| INV-17 | completed consumer 必须从 exact source bytes独立 rerun/rebuild；persisted final boolean不能建立 truth。 |
| INV-18 | final boolean + action/options 即使内部自洽，若与 rebuilt predicate/action mapping 不一致仍 reject。 |
| INV-19 | threshold SSOT only configs/base.py；snapshot只含七个 historical gates；drift不静默重解释。 |
| INV-20 | 不复制/修改 1.6B raw evidence；source export missing/mutated 后 completed root不可消费。 |
| INV-21 | same source/config/version 的 semantic projection deterministic；run metadata不进入 semantic identity/PIT authority。 |

---

## 17. Future Implementation Plan Boundary

新的 Plan 必须从本 Design 生成，而不是 patch 旧 Plan。至少用 TDD 证明：exact path/snapshot、control JSON vs raw BAPI parse separation、completed-export terminal-accounting certificate（valid certificate -> no-trusted parent is `detail_unavailable`; missing/invalid certificate -> structural reject）、synthetic 35/33/2 denominator regression、zero/foreign observation rejection、trusted invalid JSON malformed outcome、attestation/run-contract/manifest/observation header-profile mismatch rejection、bidirectional revision/raw linkage、revision `announcement_detail`/`en` binding、all-candidate first-list validation、`data.code` split、exact body grammar含 non-empty `br.child` rejection、publication conflict/unparseable rules、multi-revision conflict、no partial batch、one exact-schema parent outcome per candidate、diagnostic `observation_identity=request_observation_id` count regression、receipt/summary/completion exact-schema binding、pre-completion cap、manifest-last crash behavior、independent source-byte replay、flip final boolean reject、flip boolean+action/options reject、threshold drift reject、all safety flags false、no network/Stage1.5/execution/risk dependency。

Real reference export 必须只用于 read-only preflight/operation；不得复制成 committed fixture。Synthetic fixture 必须明确 provenance，不能假称 official frozen evidence。

Plan 禁止：patch superseded Plan、改 config thresholds、改 Stage 1.6B producer semantics、改 Stage 1.5、引入 network/resume/alternative authority/schema compatibility alias/current webpage repair。

---

## 18. Closure Audit Record

```text
review_mode = closure_audit
final_claim = one exact verified Stage 1.6B historical sealed export can be
              deterministically reduced into an independently verifiable
              Stage 1.6A historical source-quality verdict without hindsight,
              denominator manipulation, evidence-lineage ambiguity,
              producer self-certification, or downstream authority leakage.

proof_graph_frozen = true
trust_boundary_frozen = true
scope_frozen = true
runtime_evidence_independently_verified = false
  # 使用 2026-08-22 preserved reference evidence；Plan Task 0 必须重新 preflight。

design_p0 = 0
design_p1 = 0
earlier_closure_audit_miss = true
closure_escape_count = 2
implementation_plan_allowed = true
implementation_allowed = false
deployment_allowed = false

RISK_LIVE_TRADING_ENABLED = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

从本 Design 起，后续 revision/review 使用 `closure_confirmation`：只检查 `PG-01..PG-13` + frozen TCB、旧 blocker 是否闭合、revision 是否在图内制造 contradiction。无 material scope expansion 时若又发现本应在本次 Closure Audit 可见的新 design-level P0，必须标记 `earlier_closure_audit_miss=true` 并增加 `closure_escape_count`。目标：`closure_escape_count=0`。

---

## 19. Design Outcome

```text
design_decision = APPROVED
old_design = superseded_historical_reference
old_plan = superseded_unapproved_plan
next_action = write_and_review_new_implementation_plan
```

该 next action 仅允许写并审核新的 Implementation Plan；不构成代码实施、真实 adapter operation、部署或交易许可。
