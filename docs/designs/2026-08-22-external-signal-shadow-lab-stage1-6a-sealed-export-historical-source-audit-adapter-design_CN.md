# Stage 1.6A Sealed-Export Historical Source-Audit Adapter Design

- **Status:** `design_draft_for_review`
- **Date:** 2026-08-22
- **Scope:** Stage 1.6A only; local, read-only consumption of one completed Stage 1.6B historical sealed export
- **Supersedes:** No prior Design. This is a narrow implementation bridge for the approved Stage 1.6A source-audit contract and Stage 1.6B canonical-capture contracts.
- **Does not authorize:** point-in-time replay, risk-veto enforcement, paper trading, live trading, execution, alpha interpretation, Stage 1.5 changes, or Stage 1.6B VPS deployment.

## 1. Confirmed Facts

1. The current Stage 1.6A runner deliberately accepts only synthetic fixture JSONL under `tests/fixtures/external_signal_shadow/stage1_6a/`. It has no permitted path from a real Stage 1.6B capture to a real source-audit verdict.
2. Stage 1.6B has a completed local historical sealed export at:

   ```text
   data/external_signal_shadow/stage1_6b/historical_backfill/
     hist_delisting_retry_20260822T041106Z/sealed_exports/
     3fbe8e92d83af929913ca16276df3cddf81b26b7327e476b19712870a7792247/
   ```

   Its independent `load_sealed_export()` consumer has already verified the manifest, hashes, selected Delisting catalog provenance, historical two-sweep completion, terminal status, and requested range.
3. That export contains 250 catalog rows over five pages and 35 frozen title candidates. The 250 is the selected catalog page capacity within the requested 730-day range; it is not the source-audit candidate denominator.
4. Its `article_discoveries.jsonl` is the durable `candidate_discovery_rule_v1` result. The adapter must use it as the frozen candidate population, rather than rediscovering candidates from raw list pages or removing failed details after observing their outcome.
5. Local workspace verification on 2026-08-22 confirmed 35 candidate parents, 33 trusted details, and two terminal `network_error` observations (`572715f2d96e47769ebbb967c2a6e445`, `5150d4f0ee1546d7ae6382ba7cda3ffe`). Under the current 0.95 source-integrity threshold, `33 / 35 = 0.942857...`; the adapter must preserve that result if all other conditions are equal. It must not discard those two parents to manufacture a passing rate. The later Implementation Plan must repeat this exact preflight against the selected export and STOP if any export ID, manifest hash, count, failure identity, or terminal state differs.
6. A Stage 1.6B trusted detail payload is a Binance BAPI JSON envelope. The authoritative data for this adapter is in one same-hash payload:

   ```text
   data.code
   data.id                         # numeric diagnostic field only
   data.title
   data.body
   data.publishDate
   ```

   `data.body` is a string containing a serialized structured body tree, not a standalone HTML document. List titles and list bytes remain discovery evidence only; they are never semantic authority.
7. The existing 1.6A reducer, identity functions, metric definitions, completion-manifest convention, and config thresholds already exist. This Design reuses them where their contracts apply; it does not create another source collector, source-profile, candidate rule, or metric threshold.
8. The verified 1.6B `DetailRevisionRecord` contract in this workspace names its trusted-observation timestamp `t_detail_trusted_ms` (integer epoch-ms). It does not expose `revision_first_observed_at_ms`. The adapter must use the exact persisted field and Task 0 must STOP if the real export no longer has the expected v1 detail-revision schema.

## 2. Core Issue

Stage 1.6B can now produce an immutable, independently verified historical official-source export, but Stage 1.6A can only process a synthetic caller-provided capture bundle. Manually copying real BAPI payloads into fixture JSONL would destroy the 1.6B manifest boundary, permit incomplete or arbitrary inputs, and make the 1.6A metric denominator disputable.

The missing component is therefore a narrow, local, read-only adapter:

```text
one verified Stage 1.6B historical sealed export
  -> frozen candidate population + linked trusted detail revisions
  -> existing Stage 1.6A semantic/scope reducer
  -> a separate Stage 1.6A completed audit root
```

It is not a network connector, a Stage 1.6B retry mechanism, a live observer, or an event/replay engine.

## 3. Decisions

### 3.1 Use exactly one sealed export, not an arbitrary Stage 1.6B root

The new runner accepts exactly one required `--sealed-export <directory>` argument. The resolved directory must be below:

```text
<project-root>/data/external_signal_shadow/stage1_6b/historical_backfill/
  <run-id>/sealed_exports/<export-id>/
```

The path must not contain a symlink escape, must be a directory whose basename equals `sealed_export_manifest.export_id`, and must be passed to `load_sealed_export()` before any semantic record is derived or any output directory is created.

There is no glob, list, parent-root mode, `latest` mode, partial-root mode, or direct `--capture-bundle` compatibility path. A failed, active, unsealed, live-observed, wrong-profile, hash-invalid, or path-escaping input is rejected before output creation.

### 3.1.1 Completed-consumer source binding

The completed-audit consumer receives the source export explicitly; it never discovers one:

```python
load_completed_sealed_export_source_audit(
    output_root: Path,
    *,
    sealed_export: Path,
    project_root: Path,
) -> dict[str, Any]
```

The caller-supplied `sealed_export` must pass the same Section 3.1 resolved-path, family, symlink, basename, and `load_sealed_export()` validation as producer input. The completed consumer obtains this validation only by constructing one `VerifiedSealedExportSnapshot`; it must not call `load_sealed_export()` first and then construct a second snapshot. Before any replay, the consumer requires all of the following:

```text
sealed_export.basename == receipt.input_export_id
sha256(sealed_export/sealed_export_manifest.json) == receipt.input_manifest_sha256
verified manifest.export_id == receipt.input_export_id
verified manifest capture/profile/range/coverage fields == receipt fields
verified consumed authoritative artifact tuples == receipt.consumed_artifacts
```

The receipt deliberately contains no filesystem location. The consumer must not use a glob, `latest`, export-ID search, parent-root scan, hardcoded current export, or a non-authoritative location hint. A missing, wrong, or altered caller-supplied sealed export makes the local audit root non-consumable.

### 3.2 Preserve the existing fixture runner

`run_stage1_6a_futures_delisting_source_audit.py --fixture-run` remains fixture-only and unchanged in meaning. This Design requires a distinct real-input adapter runner, rather than weakening the fixture path boundary.

This is the smallest safe change: synthetic tests retain their existing explicit provenance, while a real run has one separately testable 1.6B consumer boundary.

### 3.3 Reuse the one 1.6B consumer validator

The adapter imports and calls the existing `stage1_6b_canonical_source_storage.load_sealed_export()` exactly once for the input boundary. It must not reimplement manifest/hash, terminal, profile, catalog, or historical-coverage validation. The adapter may read only the authoritative files declared by the already verified manifest.

The adapter then performs its own linkage checks that are semantic-input specific:

```text
ArticleDiscovery(source_article_id)
  -> DetailObservation(same source_article_id, aggregated under Section 6.5)
  -> trusted DetailObservation(same source_article_id)
  -> DetailRevision(same source_article_id, same raw SHA-256)
  -> raw payload at the declared relative path
  -> BAPI envelope data.code == source_article_id
```

The following are **structural evidence-chain violations** and reject the entire input export before semantic derivation or output creation: a missing required authoritative stream; a frozen `ArticleDiscovery` candidate with no `DetailObservation`; a `DetailObservation.source_article_id` absent from the frozen candidate set; duplicate or missing stable `DetailObservation.request_observation_id`; a contradictory immutable article/observation/revision/raw provenance link; a trusted observation without its matching revision; a DetailRevision without at least one matching trusted observation; an observation/revision/raw SHA-256 or declared raw-path mismatch; or a parseable BAPI envelope whose present string `data.code` differs from `source_article_id`.

The following are instead **valid upstream or semantic parent outcomes**: an aggregate containing no trusted observation and only terminal non-trusted observations, and bytes whose trusted observation/revision/raw chain is linked but whose BAPI envelope/body cannot establish semantic authority. They remain denominator-visible diagnostic parents. A non-trusted retry observation never downgrades a parent that has at least one valid trusted observation. In particular, an absent or non-string `data.code` is a malformed-envelope outcome, while a present string `data.code` with the wrong value is structural corruption. This distinction keeps byte lineage fail-closed without treating Binance payload-quality failures as silently dropped candidates.

### 3.4 Bind use-time bytes to verified export bytes

`load_sealed_export()` validates a filesystem export at a point in time. The adapter must not subsequently reopen files and assume those are the same bytes. It creates an in-memory `VerifiedSealedExportSnapshot` in this exact order:

```text
1. manifest_dict = load_sealed_export(export_dir)
2. read sealed_export_manifest.json once; parse it and require equality with manifest_dict
3. retain its SHA-256 as input_manifest_sha256
4. build expected tuples from manifest_dict.authoritative_artifacts
5. for each authoritative artifact that the adapter will consume:
     read bytes exactly once
     require byte_count and SHA-256 equal the retained manifest tuple
     parse/derive only from that in-memory byte buffer
6. for a trusted raw detail payload:
     require consumed SHA-256 == manifest tuple SHA-256
     require consumed SHA-256 == DetailRevision.detail_raw_sha256
     parse that same buffer as the BAPI envelope; a present string data.code
     must equal source_article_id, while a missing/non-string data.code is a
     denominator-visible malformed-envelope outcome under Section 7.4
```

The snapshot consumes: `article_discoveries.jsonl`, `detail_observations/historical.jsonl`, `detail_revisions.jsonl`, the required selected-catalog list-capture/raw-index pairs, every linked trusted raw detail payload, and `historical_coverage.json` where required for receipt/corroboration. It does not parse a file after its bytes have been discarded or reopen it by path.

`source_export_receipt.json` records the exact consumed tuples, not an unqualified claim about the directory:

```text
input_export_id
input_manifest_sha256
capture_mode
source_profile_id
historical_range_from_ms
historical_range_to_ms
historical_coverage_sha256
consumed_artifacts = sorted tuples of:
  relative_path
  artifact_class
  sha256
  byte_length

sort key = (artifact_class, relative_path, sha256)
```

The receipt hashes are hashes of the buffers actually passed to parsing. This is use-time lineage validation, not a second implementation of the Stage 1.6B sealed-export completion predicate.

The adapter creates its output root only after the full snapshot succeeds. Any use-time hash/size/linkage failure therefore leaves no partial Stage 1.6A root.

### 3.5 Do not copy raw evidence

The Stage 1.6A output records only a `source_export_receipt.json` containing the exact input export ID, manifest SHA-256, input profile ID, historical range, and the Section 3.4 consumed-artifact tuple set. It does not copy raw index/detail bytes, BAPI envelopes, request manifests, or any Stage 1.6B control-plane artifact.

The sealed export remains the sole raw-evidence owner. A future reader must supply the exact preserved sealed-export path and verify the receipt against it under Section 3.1.1 before following evidence pointers. Missing or altered source export means the 1.6A audit root is not independently replayable and must be treated as non-consumable for any future evidence use.

### 3.6 Historical semantic extraction remains non-PIT

For every parent and child derived by this adapter:

```text
capture_mode                       = historical_backfill
semantic_extracted_at_ms           = actual local extraction time
notice_lineage_first_detected_at_ms = null
system_available_at_ms             = null
fact_available_at_ms               = null
capture_time_status                = historical_unknown
point_in_time_replay_eligible      = false
risk_veto_candidate                = false
```

`data.publishDate` may populate `source_published_at_ms` only as an asserted publication-time fact with `capture_time_status=historical_unknown`; it does not establish that the local system possessed the fact then.

### 3.7 A real source-audit verdict is permitted, but only for source quality

Unlike the fixture-only runner, this adapter's completed manifest is allowed to expose `source_audit_passed=true` only when every acceptance predicate in Section 8 passes. This means only that the real historical official-source sample meets the approved source-schema and sample-density thresholds.

Regardless of that verdict, every output must retain:

```text
point_in_time_source_validated             = false
market_data_coverage_passed                = false
replay_allowed                             = false
point_in_time_directional_replay_allowed   = false
risk_veto_candidate                        = false
trade_signal_allowed                       = false
paper_trading_allowed                      = false
live_trading_allowed                       = false
execution_engine_allowed                   = false
alpha_interpretation_allowed               = false
RISK_LIVE_TRADING_ENABLED                  = false
```

No 1.6A output may update a strategy, blacklist, notification, order path, or risk controller.

## 4. Scope and Non-Goals

### 4.1 In Scope

1. Read one complete Stage 1.6B `historical_backfill` sealed export on the local project filesystem.
2. Build the frozen 1.6A candidate manifest from 1.6B `ArticleDiscovery` rows, preserving every candidate parent in the denominator.
3. Decode and normalize only linked trusted canonical-English BAPI detail payloads, extract schedule facts, perform USD-M perpetual crypto scope classification, preserve batch completeness, and compute existing 1.6A metrics.
4. Persist a separate completed Stage 1.6A real-source audit root and issue a constrained source-audit verdict.
5. Provide deterministic synthetic fixtures that mirror the BAPI envelope and sealed-export linkage contract. The current real export is an operator evidence input, never a test fixture.

### 4.2 Explicit Non-Goals

1. No HTTP, websocket, browser, `urllib.request`, `requests`, `httpx`, `aiohttp`, `socket`, retry, polling, or VPS operation.
2. No modification, resume, seal, deletion, compaction, or reclassification of a Stage 1.6B root.
3. No source-profile probe, catalog discovery, detail refetch, or repair of the two terminal detail failures. A new 1.6B capture Design/operation is required for any future retry policy.
4. No Stage 1.5D/F/G read, write, import, restart, deployment, root binding, or runtime dependency.
5. No historical price/L2/funding/OI/fee collection, no MAE/drift/slippage/net-edge calculation, and no risk-veto enforcement.
6. No config threshold change. `configs/base.py` remains the existing threshold SSOT.

## 5. Producer, Adapter, and Consumer Contract

| Boundary | Producer / reader | Required authority | Forbidden substitute | Outcome on failure |
|---|---|---|---|---|
| B sealed input | Stage 1.6B historical producer | complete `sealed_export_manifest`, matching hashes, v2 profile/catalog, complete historical coverage | active root, terminal file alone, arbitrary copied files | reject before output creation |
| Candidate population | `article_discoveries.jsonl` | all distinct `source_article_id` rows, `candidate_discovery_rule_v1`, catalog v2 provenance | recomputing from raw pages, detail-success-only list, title filtering after outcome | reject malformed/mixed provenance; otherwise preserve failed candidates |
| Detail semantic authority | aggregated `DetailObservation` set, linked trusted observations, `DetailRevision`, and raw BAPI envelope | Section 6.5 observation aggregation; exact article ID, exact raw SHA, canonical `en`, expected detail variant | list title, other locale, current webpage, third party, inferred values | invalid linkage rejects export; parse failure is denominator-visible diagnostic |
| Semantic reducer | Stage 1.6A existing deterministic identities and scope rules | one canonical normalized BAPI body representation | external lookup, current exchange metadata, manual symbol edits | parent is unresolved/incomplete, no eligible child |
| Adapter output | new Stage 1.6A audit root | all artifact hashes plus completion manifest written last | summary claiming complete | partial root is non-consumable |
| Future reader | 1.6A completed-audit loader plus receipt verification | completed local audit and still-verifiable referenced sealed export | summary alone, source root name, operator claim | reject |

## 6. Data and Semantic Contract

### 6.1 Accepted source profile and schema versions

The only accepted input profile is:

```text
capture_mode                       = historical_backfill
source_profile_id                  = binance_public_web_bapi_en_delisting_catalog_v2
ListCapture.schema_version         = stage1_6b_list_capture_v2
ArticleDiscovery.schema_version    = stage1_6b_article_discovery_v2
DetailObservation.schema_version   = stage1_6b_detail_observation_v1
DetailRevision.schema_version      = stage1_6b_detail_revision_v1
HistoricalCoverage.schema_version  = stage1_6b_historical_coverage_v2
checkpoint.schema_version          = stage1_6b_observer_checkpoint_v2
sealed export schema               = stage1_6b_sealed_export_v1
```

The adapter does not accept v1 source-profile artifacts even if their JSON shape is superficially compatible. It delegates that check to `load_sealed_export()` and performs linkage checks before use.

### 6.2 Candidate manifest

`audit_candidate_manifest` is constructed from all unique authoritative `ArticleDiscovery` rows, sorted lexicographically by `source_article_id`. It includes:

```text
source_article_id
discovery_title                    # discovery evidence only
first_list_capture_id
discovery_rule_version
source_catalog_id = 161
source_catalog_name = Delisting
notice_lineage_first_detected_at_ms = null
capture_mode = historical_backfill
source_export_id
```

Duplicate rows for an article must be byte/field-equivalent for immutable discovery fields; otherwise the adapter rejects the input export. Membership is frozen before inspecting detail availability, body syntax, symbol extraction, mapping, or classification.

### 6.3 BAPI detail envelope extraction

For each trusted linked detail revision, the adapter parses the already verified in-memory JSON bytes and requires:

```text
top-level data                       is an object, otherwise malformed envelope
data.code                            if present as a string, exactly equals source_article_id;
                                     absent/non-string is malformed envelope
data.id                              is an optional numeric diagnostic field; never an identity key
data.title                           is a non-empty string
data.body                            is a string containing one valid structured body-tree JSON object
data.publishDate                     is an integer epoch-ms or explicitly unparseable
```

`data.body` has one exact `stage1_6a_bapi_body_tree_v1` grammar. A plain-text or HTML fallback, arbitrary recursive collection of JSON strings, and unordered dictionary traversal are forbidden:

```text
root node:
  exact keys: node, child
  node == "root"
  child is an array

element node:
  keys are a subset of: node, tag, attr, child
  node == "element"
  tag is one of:
    a, br, em, h3, h4, li, p, span, strong, table, tbody, td, tr, u, ul
  attr is absent or an object; it is opaque metadata and is never traversed
  child is absent or an array

text node:
  exact keys: node, text
  node == "text"
  text is a string

all other value/node/key/tag/child shapes:
  body_parse_unresolved
```

Traversal visits only `child` arrays in ascending array-index order. Only a text node's `text` string enters semantic text. Empty text emits nothing. A `br` node must have an absent or empty `child`; a non-empty `br.child` is `body_parse_unresolved`, rather than hidden text that is silently ignored. A valid `br` emits one newline and never recurses. The block tags `p`, `h3`, `h4`, `li`, `tr`, and `td` emit one newline immediately before and after their children; all other allowed elements recurse transparently. Empty allowed elements are valid and emit only their defined boundaries.

The resulting token stream is joined, then normalized in this exact order:

```text
1. replace CRLF/CR with LF
2. Unicode NFKC
3. replace every run of [space, tab, form-feed, vertical-tab] with one space
4. trim spaces adjacent to LF
5. replace every run of one or more LF with one LF
6. strip leading/trailing space and LF
```

An unknown/ambiguous node is not ignored: it yields a denominator-visible `body_parse_unresolved` parent outcome and no eligible child. The adapter records:

```text
body_normalization_version = stage1_6a_bapi_body_tree_v1
semantic_extractor_version = stage1_6a_extractor_v1
```

The BAPI normalizer version is part of `semantic_extraction_id`; it does not overwrite the fixture normalizer version. `data.title` and the normalized `data.body` may be used only because both originate from the same trusted `DetailRevision` raw SHA-256.

`data.publishDate` evidence uses `location_kind=json_pointer`, `location_value=/data/publishDate`. Body-derived facts use `normalized_text_span` over the deterministic flattened body. The raw SHA-256 and revision ID are mandatory in both pointer types.

### 6.4 Publication-time authority and grammar

`source_published_at_ms` has one semantic-fact authority:

```text
authority = selected trusted DetailRevision.data.publishDate
```

`releaseDate` in the selected Delisting catalog is discovery/corroboration evidence only. Its sole adapter authority chain is:

```text
ArticleDiscovery.first_list_capture_id
  -> exactly one ListCapture.list_capture_id
  -> that ListCapture's declared raw index payload tuple
  -> selected catalog 161 / Delisting in that same hash-verified byte buffer
  -> same article.code == source_article_id
  -> releaseDate
```

Later list captures may be retained only as diagnostics; they must not replace, override, or create a conflict with the first-discovery `releaseDate`.

Both `data.publishDate` and a corroborating catalog `releaseDate` are valid epoch-ms only when:

```text
type(value) is int          # bool is forbidden even though bool subclasses int
AND 1_000_000_000_000 <= value < 10_000_000_000_000
```

If `data.publishDate` fails this grammar, set `source_published_at_ms.fact_parse_status=unparseable`, `source_published_at_ms=null`, and do not count the parent in `event_days`. This publication-fact status alone does not turn an otherwise linked and semantically parsed parent into a source-integrity failure. If both values are valid but differ by even one millisecond:

```text
source_published_at_ms.fact_parse_status = conflicting
publication_time_conflicting = true
source-integrity numerator for this parent = false
parent does not contribute to event_days
```

If `first_list_capture_id` is absent, duplicated, or missing from ListCapture; its raw index tuple does not link; the selected catalog lacks the matching article; or its `releaseDate` is invalid, the input snapshot is rejected because the candidate-discovery linkage is incomplete. A valid equal pair produces `fact_parse_status=present`, `timestamp_ms=data.publishDate`, and `capture_time_status=historical_unknown`.

### 6.5 Revision selection and conflict handling

Before aggregation, require an exact membership partition: every frozen candidate parent has a non-empty authoritative `DetailObservation` set, and every DetailObservation `source_article_id` belongs to the frozen `ArticleDiscovery` candidate set. A missing parent observation or foreign observation is structural incomplete upstream evidence and rejects the entire export; neither may be classified as `detail_unavailable` or silently ignored.

For each frozen candidate parent, then aggregate its entire authoritative `DetailObservation` set whose `source_article_id` equals the parent ID. Every observation must have a unique non-empty `request_observation_id`, the accepted source profile, and the expected detail request variant. `source_locale` is established by its linked `DetailRevision`; a DetailObservation cannot supply a locale substitute.

```text
trusted_observations
  = all parent observations where trust_validation_status == trusted

if trusted_observations is non-empty:
  parent transport-level detail authority = trusted
  every non-trusted parent observation is retained only as a diagnostic
  and cannot downgrade this parent to detail_unavailable

else if parent observations are non-empty
  and all parent observations are terminal non-trusted
  and no pending / unresolved observation exists:
  parent detail_authority_status = detail_unavailable

else:
  reject the input export as incomplete upstream historical evidence
```

For every trusted observation, require exactly one logical DetailRevision authority with the same `source_article_id`, `detail_raw_sha256`, `raw_payload_relative_path`, `request_variant`, `source_profile_id`, and canonical `source_locale=en`; its raw payload must be present in the verified snapshot and match the same SHA-256. Multiple trusted observations with the same raw SHA-256 share that one logical DetailRevision. Multiple distinct trusted raw SHA-256 values produce distinct DetailRevision rows. Every DetailRevision must conversely be backed by at least one trusted observation with the same article ID, raw SHA-256, raw path, request variant, and source profile. A missing match in either direction, an ambiguous logical revision, or an orphan DetailRevision is structural evidence-chain corruption and rejects the entire export before parent outcomes, metrics, or output creation. After this transport-level aggregation, the selected revision's envelope/body reduction determines the persisted `detail_authority_status` (`trusted`, `malformed_bapi_envelope`, or `body_parse_unresolved`).

Every linked trusted detail hash remains a distinct logical `DetailRevision`. After observation aggregation and bidirectional linkage validation, select one revision for the parent-level audit verdict deterministically by maximum `(t_detail_trusted_ms, detail_raw_sha256)`. `t_detail_trusted_ms` is the exact 1.6B persisted field, must be an integer epoch-ms, and is never substituted with `captured_at_ms`, a DetailObservation field, or an invented compatibility alias. Input order cannot affect the aggregation or selection.

If multiple trusted revisions for one parent produce incompatible declared symbol sets, product-family classification, or a conflicting value for the same present schedule fact, record `revision_conflicting` and fail that parent’s mapping/classification numerator. No revision is silently substituted to make the parent complete. The source-integrity numerator may still count it if trusted bytes/provenance are complete; the separate mapping/classification rates expose the semantic conflict.

### 6.6 Parent/child scope and completeness

The base Stage 1.6A rules remain exact:

```text
eligible child
IFF
parent declaration is complete
AND child is explicitly USD_M + PERPETUAL + crypto_asset
```

COIN-M, delivery, spot, margin, non-crypto, and fully evidenced out-of-scope children must be retained as accounted child records. A mixed batch remains eligible only when every declared child is deterministically accounted. Any unresolved or corrupt child makes the parent incomplete and prevents every child from becoming source-audit eligible.

## 7. Persistence, Idempotency, and Failure Semantics

### 7.1 Output root and artifacts

The new runner writes a fresh, local-only root:

```text
data/external_signal_shadow/stage1_6a/sealed_export_source_audits/<audit-run-id>/
```

The root must not exist before start, must resolve under the Stage 1.6A output parent, and must not be a symlink. It contains at minimum:

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
completion_manifest.json             # last atomic write
```

The receipt follows the exact consumed-artifact tuple grammar in Section 3.4. It deliberately contains no raw payload bytes.

The implementation must extend/reuse the existing Stage 1.6A `persist_audit_artifacts` / `load_completed_audit` atomic-write and completion-manifest convention. It must not add a second ad-hoc `Path.write_*` completion protocol; the only permitted adaptation is the explicit real-adapter artifact set in this section.

`parent_audit_outcomes.jsonl` has exactly one row for every frozen candidate parent. It persists the outcome needed to independently rebuild metric populations:

```text
schema_version                       # stage1_6a_parent_audit_outcome_v1
source_article_id
detail_authority_status             # trusted / detail_unavailable / malformed_bapi_envelope / body_parse_unresolved
selected_detail_revision_id         # null only when no trusted revision exists
source_integrity_parent_pass         # exact boolean, never inferred from absence
publication_time_status             # not_evaluable / present / unparseable / conflicting
parent_declaration_status           # complete / incomplete / revision_conflicting / unresolved
mapping_status                      # pass / fail / not_applicable
event_type_classification_status    # in_scope / fully_accounted_out_of_scope / unresolved
diagnostic_codes                    # deterministic sorted strings
```

This is a derived audit artifact, not a replacement for the sealed raw evidence. Its purpose is to make failure membership auditable instead of silently absent.

`linkage_rejected` is not a persisted parent status. Any structural linkage corruption rejects the input export before `parent_audit_outcomes.jsonl` exists, so no parent outcome, metric, summary, or completion manifest is produced.

`detail_revisions.jsonl` is an adapter-derived audit projection, not a verbatim copy of the 1.6B stream. Every row has exactly:

```text
schema_version                       # stage1_6a_derived_detail_revision_v1
source_article_id
detail_revision_id
detail_raw_sha256
raw_payload_relative_path
t_detail_trusted_ms
source_surface
source_locale
request_variant
bapi_numeric_id                      # null or integer diagnostic only
detail_authority_status
selected_for_parent                  # exact boolean
```

`audit_diagnostics.jsonl` contains only forbidden semantic-authority attempts and is the authoritative source of `forbidden_payload_count`. A forbidden semantic-authority attempt writes exactly one row with:

```text
schema_version                       # stage1_6a_audit_diagnostic_v1
diagnostic_type                       # forbidden_semantic_authority_attempt
observation_identity                 # exact upstream DetailObservation.request_observation_id
source_article_id
source_surface
source_locale
request_variant
raw_payload_sha256                   # null only when no bytes exist
violation_class
attempted = true
```

`forbidden_payload_count` is `count(distinct observation_identity)` among these rows. Terminal non-trusted retries, malformed envelope/body outcomes, publication conflicts, and revision conflicts are persisted only through the parent outcome's deterministic `diagnostic_codes`; they do not create an `audit_diagnostics.jsonl` row. The adapter must STOP before implementation if the imported trusted/untrusted DetailObservation schema has no stable `request_observation_id`; it must not collapse this metric to a parent boolean.

Both the pre-completion summary and `completion_manifest.json` carry `artifact_profile_version = stage1_6a_sealed_export_source_audit_v1`; completed consumers require an exact match.

### 7.2 Completion boundary

The writer atomically writes every authoritative derived artifact and a summary with:

```text
audit_summary_state                    = pre_completion
source_audit_evidence_candidate_passed = true | false
source_audit_passed                    = false
allowed_next_action                    = pending_completion
permitted_design_options               = []
```

It then writes `completion_manifest.json` last. The completion manifest hashes every listed derived artifact except itself, binds `source_export_receipt.json`, includes the input export ID and input manifest SHA-256, and is the only durable artifact permitted to carry:

```text
source_audit_passed = true | false
allowed_next_action
permitted_design_options
```

The completion-manifest values are written only after the producer has reread the durable derived artifacts, recomputed every metric population and candidate predicate, and checked exact equality with the pre-completion summary. A crash before this last write leaves no durable artifact carrying a final verdict or next-stage permission.

A local audit root is consumable only if all of the following are true:

```text
completion_manifest.status == complete
all derived artifact hashes verify
summary.audit_summary_state == pre_completion
summary does not claim status == complete
summary.source_audit_passed == false
receipt source export ID/hash match the completion manifest
caller-supplied source sealed export passes Section 3.1.1 receipt binding and load_sealed_export()
```

The adapter has no resume mode. A crash leaves a partial non-consumable output root. The operator preserves it for diagnosis or removes it only after confirming it is partial, then starts a new audit run ID from the same immutable export. This avoids adding checkpoint/reconciliation complexity to a short local pure-reducer operation.

### 7.3 Determinism

For the same sealed export, extractor version, normalizer version, and config thresholds, reruns must produce identical:

```text
candidate manifest membership and hash
detail revision IDs
semantic extraction IDs
notice/contract identities and statuses
metric numerator/denominator values
source-audit verdict and allowed next action
```

`audit_run_id`, completion time, and `semantic_extracted_at_ms` are run metadata and may differ. They are not identity inputs and cannot create point-in-time authority.

### 7.4 Fail-closed classification

| Condition | Adapter action |
|---|---|
| invalid path, incomplete/unsealed export, manifest/hash/profile/catalog/coverage failure | reject before output creation |
| missing authoritative required stream, malformed JSONL, duplicate discovery contradiction, candidate without an observation, observation for a non-candidate article, duplicate/missing observation identity, contradictory immutable provenance, trusted-observation/revision linkage mismatch, orphan revision, raw hash/path mismatch, or a present string BAPI `data.code` different from `source_article_id` | reject input export before semantic derivation |
| parent has no trusted observation and every observation is terminal non-trusted | retain parent in frozen denominator; emit `detail_unavailable`; fail source-integrity numerator |
| parent has one or more trusted observations plus any terminal non-trusted observation | retain failed observations only as diagnostics; trusted aggregate remains the parent detail authority |
| parent has pending/unresolved observation and no trusted observation | reject input export as incomplete upstream historical evidence |
| trusted raw payload is record/hash linked but has a malformed BAPI envelope/body, including absent/non-string `data.code`, or `body_parse_unresolved` | retain parent in frozen denominator; `source_integrity` numerator fails; mapping/classification numerators fail where the parent belongs; no eligible child |
| linked semantic body with `data.publishDate` outside epoch-ms grammar | retain parent; set publication fact `unparseable`, no `event_days` contribution; this status alone does not change source-integrity numerator membership |
| body authority is established, but one optional schedule fact is `unparseable` or `not_stated` | retain the explicit fact status; do not infer a value. This alone does not redefine the frozen source-integrity metric; mapping/classification follow their existing parent-completeness rules |
| body authority is established, but symbols/product declaration is unparseable or incomplete | retain parent and explicit diagnostic; source-integrity outcome follows the parent predicate in Section 8; no eligible child; mapping/classification numerator fails |
| partial batch declaration, revision conflict, unknown product fields | retain parent/children as unresolved; no partial eligible subset |
| output write/hash failure or crash before completion manifest | output is non-consumable; no verdict may be relied upon |

`forbidden_payload_count` changes only when the adapter emits the Section 7.1 durable `forbidden_semantic_authority_attempt` diagnostic for an actual attempted semantic-authority use outside the accepted trusted canonical detail boundary. Rejected malformed/untrusted input that is never used as authority is a failure/diagnostic, not an automatic forbidden-payload increment.

## 8. Metrics, Verdicts, and Authority

The existing `EXTERNAL_SIGNAL_STAGE1_6A_*` constants remain the only thresholds. This adapter implements the approved `stage1_6a_audit_metric_v1` definitions without changing numerator/denominator membership:

| Metric | Adapter population |
|---|---|
| `source_integrity_pass_rate` | numerator: frozen candidate parents satisfying `source_integrity_parent_pass`; denominator: every parent in the imported candidate manifest |
| `symbol_mapping_pass_rate` | numerator: trusted-aggregate candidate parents with a complete declared contract set and every child accounted; denominator: all trusted-aggregate candidate parents declaring candidate futures delisting |
| `event_type_classification_pass_rate` | numerator: trusted-aggregate candidate parents deterministically `in_scope` or fully accounted `out_of_scope`; denominator: all trusted-aggregate candidate parents |
| `historical_events_found` | distinct eligible parent `source_article_id`; one batch notice counts once |
| `event_days` | distinct UTC dates of present `source_published_at_ms` among `historical_events_found` parents; never settlement date |
| `symbols_with_events` | distinct eligible child `canonical_symbol` across `historical_events_found` parents |
| `forbidden_payload_count` | count of distinct durable `forbidden_semantic_authority_attempt.observation_identity` values in `audit_diagnostics.jsonl`; correctly rejected data is not counted merely for being rejected |

The frozen per-parent numerator predicate is:

```text
source_integrity_parent_pass
IFF
  canonical source bytes persisted
  AND trusted canonical-English detail linked
  AND immutable capture/provenance linkage complete
  AND canonical detail envelope/body parses successfully enough to establish
      the approved BAPI semantic-authority boundary
  AND publication_time_conflicting != true
```

The following always remain in the frozen candidate denominator and fail this numerator:

```text
detail_unavailable after the Section 6.5 aggregate has no trusted observation
WAF or untrusted detail only when the aggregate has no trusted observation
malformed detail envelope
body_parse_unresolved
publication_time_conflicting
```

Structural evidence-chain violations are not denominator outcomes: a missing required authoritative stream, contradictory immutable provenance, a trusted observation without a matching revision, observation/revision/raw SHA-256 or raw-path mismatch, or a parseable envelope with a wrong present string `data.code` rejects the entire input export. No metric or verdict may be produced from such an input.

For this metric, “parse failure” means failure to establish the canonical-detail semantic-authority boundary: missing/invalid BAPI envelope, invalid `data.code` shape, or `body_parse_unresolved`. It does not mean every individual fact with `fact_parse_status=unparseable`. After that body authority is established, `data.publishDate` or one optional schedule fact may be `not_stated` or `unparseable` without silently changing source-integrity membership; it remains an explicit fact-level status and cannot be inferred. Publication conflict still fails source integrity under the predicate above.

The summary serializes an exact `threshold_snapshot` containing only the seven historical source-audit constants consumed by this adapter: `EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS`, `EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS`, `EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS`, `EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO`, `EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO`, `EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO`, and `EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT`, plus `audit_metric_definition_version`. The live-only `EXTERNAL_SIGNAL_STAGE1_6A_MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES` is not consumed or snapshotted. The completion manifest hashes that summary. A consumer rejects if a snapshotted current config value no longer exactly matches, rather than silently reinterpreting a completed historical verdict.

The summary must distinguish predicates:

```text
source_schema_integrity_passed
sample_sufficiency_passed
source_audit_passed
point_in_time_source_validated
market_data_coverage_passed
```

The producer uses the exact approved Stage 1.6A predicate; `input_sealed_export_verified` is an input precondition, not a new term that changes that predicate:

```text
source_schema_integrity_passed
  = canonical English authority available for every eligible sample
    AND source_integrity_pass_rate >= configured threshold
    AND symbol_mapping_pass_rate >= configured threshold
    AND event_type_classification_pass_rate >= configured threshold
    AND available_at_policy_defined = true
    AND forbidden_payload_count <= configured threshold

sample_sufficiency_passed
  = historical_events_found >= configured threshold
    AND event_days >= configured threshold
    AND symbols_with_events >= configured threshold

source_audit_evidence_candidate_passed
  = source_schema_integrity_passed
    AND sample_sufficiency_passed

point_in_time_source_validated = false
market_data_coverage_passed    = false
risk_veto_candidate            = false
replay_allowed                 = false
```

For this historical adapter, `available_at_policy_defined=true` means the policy in Section 3.6 is mechanically applied: all system/fact availability fields are null with `historical_unknown`; it does not assert live availability.

The pre-completion summary serializes only `source_audit_evidence_candidate_passed` and keeps `source_audit_passed=false`. The last-written completion manifest may serialize the final `source_audit_passed` only after completion. A future consumer may accept an audit root only if it independently performs all of the following:

```text
1. verify local completion manifest and every derived artifact hash
2. validate the caller-supplied exact sealed-export path under Section 3.1.1, verify receipt grammar/binding, and reconstruct the Section 3.4 verified input snapshot
3. deterministically rerun candidate/import linkage, BAPI normalization,
   publication-time checks, semantic extraction, scope classification, and
   parent outcomes from the consumed in-memory source bytes
4. rebuild and exact-compare:
     candidate membership/count/hash
     source-integrity numerator and denominator
     mapping numerator and denominator
     classification numerator and denominator
     historical_events_found, event_days, symbols_with_events
     forbidden_payload_count
     parent outcomes, notice/contract identities and status rows
5. recompute source_schema_integrity_passed,
   sample_sufficiency_passed, and source_audit_evidence_candidate_passed
   from rebuilt metrics and the persisted threshold snapshot
6. require:
     summary.source_audit_passed == false
     summary.source_audit_evidence_candidate_passed == rebuilt candidate predicate
     completion_manifest.source_audit_passed == rebuilt candidate predicate
```

This is not producer self-certification: persisted summary rates alone never establish acceptance. Producer completion is `verified input bytes -> derived artifacts -> pre-completion candidate summary -> completion manifest`; consumer acceptance is `hashed artifacts + exact source bytes -> independent reducer replay -> exact metric comparison -> completion authority`.

The pre-completion summary always has `allowed_next_action=pending_completion` and `permitted_design_options=[]`. Only a valid completed consumer may rely on these final `completion_manifest` fields:

```text
source_audit_passed = true
  AND point_in_time_source_validated = false
  -> allowed_next_action = write_live_source_observation_design_only
     permitted_design_options = [write_live_source_observation_design_only,
                                 write_ex_post_diagnostic_design_only]

source_audit_passed = false
  -> allowed_next_action = source_audit_failed_or_inconclusive
     permitted_design_options = []
```

`market_data_coverage` is not permitted by this adapter because `point_in_time_source_validated=false`; it remains gated by the Parent Stage 1.6A verdict table. Neither branch authorizes replay or trading. The current export is expected to be capable of meeting the parent/day/sample shape thresholds (35 candidate parent dates), but its two failed details may make `source_integrity_pass_rate` fail the 0.95 threshold. The real adapter run, not this Design, is the authority for the final values.

## 9. Acceptance Invariants

- **INV-01 Exact input authority:** The adapter reads one path-validated, completed 1.6B historical sealed export, calls `load_sealed_export()`, and derives only from the Section 3.4 single-read in-memory verified snapshot.
- **INV-02 Frozen denominator and observation membership:** Every imported `ArticleDiscovery` parent remains in the source-integrity denominator regardless of detail outcome, but it must have at least one authoritative DetailObservation; every DetailObservation must belong to that frozen candidate set. Missing or foreign observation evidence rejects the input rather than changing denominator membership.
- **INV-03 No title semantics:** List titles establish candidate membership only. All semantic facts, symbols, and classifications come from the linked trusted canonical-English BAPI detail payload.
- **INV-04 Same-payload linkage:** A semantic record’s article ID, detail revision ID, raw SHA-256, BAPI `data.code`, title/body, and evidence pointers belong to one linked payload. BAPI `data.id` is diagnostic-only and cannot be used as an article identity.
- **INV-05 Historical honesty:** Historical extraction timestamps never populate `system_available_at_ms`, `fact_available_at_ms`, or a first-detected timestamp; every such record is replay-ineligible.
- **INV-06 Batch integrity:** No incomplete/mixed/unresolved parent can emit an eligible child subset.
- **INV-07 Real audit is narrow:** A true source-audit verdict is allowed only through the explicit metric predicates; it grants no PIT, market-data, risk-veto, alpha, paper, or execution authority. A historical pass may authorize only the Parent-allowed live-source-observation or ex-post-diagnostic Design action.
- **INV-08 Immutable evidence ownership:** The adapter does not mutate or copy raw Stage 1.6B evidence. Its receipt pins one export ID, one manifest hash, and the exact consumed artifact tuple set.
- **INV-09 Output completion truth:** Only `completion_manifest.json` can claim local audit completion, final `source_audit_passed`, or final next-stage permission; it is written last after a durable-artifact metric rebuild and all derived artifact hashes exist. A pre-completion summary always has `source_audit_passed=false`, `allowed_next_action=pending_completion`, and no permitted option.
- **INV-10 Stage isolation:** The adapter performs no network I/O and has no Stage 1.5 path, import, process, or data-plane dependency.
- **INV-11 Config SSOT:** Existing `EXTERNAL_SIGNAL_STAGE1_6A_*` values determine source-audit predicates. This work adds no threshold, alias, or hidden override.
- **INV-12 Deterministic replay of artifacts:** Same verified sealed input and same extractor/normalizer/config produce the same identities, metric populations, and verdict; run metadata does not change authority.
- **INV-13 Publication-fact singularity:** `DetailRevision.data.publishDate` is the only `source_published_at_ms` authority. Catalog `releaseDate` is exact-equality corroboration only; invalid or conflicting values never enter `event_days`.
- **INV-14 Independent completed consumer:** A completed audit is accepted only when its caller-supplied exact sealed-export path passes Section 3.1.1 receipt binding, then the consumer replays the deterministic adapter from hashed source bytes and exact-compares all persisted metric populations and final authority fields.

## 10. Verification Strategy

The Implementation Plan must begin with RED tests and preserve all existing fixture-run tests. It must add at least:

1. Task 0 preflight against the selected real export: exact export ID and manifest SHA, `load_sealed_export()` success, complete manifest artifact-tuple topology, 35 candidate parents, 33 trusted detail parents, two terminal failures with the two Section 1 IDs, 33 `stage1_6b_detail_revision_v1` rows using exact `t_detail_trusted_ms`, and no pending candidate. Any difference is STOP, not an adapter adjustment.
2. A minimal synthetic v2 historical sealed export that passes `load_sealed_export()` and is accepted only through the new adapter runner.
3. Use-time mutation test: validate an export, mutate a subsequently consumed artifact, then require use-time hash rejection before any semantic derivation or output write. A trusted raw detail must be parsed from the one buffer whose hash matches both the manifest tuple and `DetailRevision.detail_raw_sha256`.
4. A valid BAPI envelope whose body uses every accepted v1 node/tag shape and whose `data.publishDate` / corroborating `releaseDate` create deterministic JSON-pointer/text-span evidence and a `stage1_6a_bapi_body_tree_v1` semantic identity. Unknown node, unknown tag, arbitrary string-valued metadata, non-array `child`, non-string text, and a non-empty `br.child` must yield `body_parse_unresolved`, not be silently traversed; an empty valid text string emits nothing.
5. Publication grammar and first-discovery tests: missing, null, bool, zero, negative, seconds, float, strings, and >= 10^13 `publishDate` are `unparseable`, set no publication timestamp, and do not enter `event_days`; they are not malformed-envelope rejection and do not alone fail source integrity. Accept only the fixed epoch-ms range as `present`. Resolve corroborating `releaseDate` only through `ArticleDiscovery.first_list_capture_id`; mutation of a later list capture cannot affect the result. An invalid/missing first-capture chain rejects the export, while valid `publishDate != releaseDate` is conflicting, fails that parent source-integrity numerator, and excludes it from `event_days`.
6. Rejection before output creation for an arbitrary 1.6B root, a partial/unsealed export, `..` escape, symlink escape, mismatched export directory ID, or a Stage 1.5 path.
7. Rejection before semantic derivation for an artifact hash mismatch, legacy profile/schema, article-discovery catalog mismatch, trusted observation without a revision, observation/revision raw-hash mismatch, or a present string `data.code != source_article_id`. A paired acceptance test must prove that a numeric `data.id` differing from the UUID-like article ID remains valid when `data.code` matches.
8. A denominator test with 35 frozen candidates, 33 trusted details, and two terminal failures: source integrity is exactly `33 / 35`, not `33 / 33`.
9. A record/hash-linked trusted detail with a malformed envelope, and a separate one with `body_parse_unresolved`: each parent remains in the frozen denominator, fails the source-integrity numerator and applicable mapping/classification numerators, and emits no eligible child.
10. An established body authority with one optional schedule fact `unparseable`: retain the explicit fact status without inventing a value or silently redefining `source_integrity_parent_pass`.
11. A multi-revision parent conflict: all revisions persist, but mapping/classification does not silently choose a passing revision.
12. Historical time assertions: extraction time is present, while `system_available_at_ms`, `fact_available_at_ms`, and first-detected time are null and `capture_time_status=historical_unknown`.
13. Completion authority/crash tests: before completion manifest, summary has `source_audit_passed=false`, `allowed_next_action=pending_completion`, and no option; only the last manifest may contain final truthy authority or final action. Producer must rebuild all metrics, including distinct forbidden observation attempts, from durable derived bytes before writing it. Every crash before it is rejected.
14. Completed-consumer tamper tests: a producer summary with `1.0` instead of recomputed `33 / 35`, a changed parent outcome, changed contract status, missing denominator member, mismatched receipt tuple, or wrong final manifest boolean must all reject despite valid local file hashes.
15. DetailObservation aggregation tests: `network_error -> trusted` and `trusted -> network_error` both yield a trusted parent; a non-empty terminal `[network_error]` observation set yields `detail_unavailable`; two trusted observations sharing one raw SHA yield one logical DetailRevision; two trusted observations with distinct raw SHA values yield two revisions and then use Section 6.5 selection/conflict rules; an orphan DetailRevision with no matching trusted observation rejects the entire export before output creation.
16. Completed-consumer source-binding tests: a wrong caller-supplied export path, a path whose basename differs from the receipt ID, a matching-ID export with a mismatched manifest hash, and a consumed-tuple mismatch must all reject without globbing or scanning. Only the same exact verified export used by the producer may replay; monkeypatch `load_sealed_export()` and require exactly one call while the completed consumer builds its one verified snapshot.
17. Exact predicate parity: the adapter's source-schema/sample predicates equal the approved `stage1_6a_audit_metric_v1` formulas, including `available_at_policy_defined=true`; no approximate variant or extra metric gate is permitted.
18. Task 0 compatibility gate: verify that `load_sealed_export()` returns a manifest dictionary equal to the parsed `sealed_export_manifest.json`. If this is not true, STOP and use an equivalent manifest-authority comparison without modifying any Stage 1.6B storage path.
19. Version dispatch: the completed consumer accepts only exact supported `body_normalization_version=stage1_6a_bapi_body_tree_v1`, `semantic_extractor_version=stage1_6a_extractor_v1`, and `audit_metric_definition_version=stage1_6a_audit_metric_v1`; an unknown or mismatched version rejects rather than silently applying current semantics.
20. Static isolation: new adapter modules/runner contain no network clients or trading/strategy/risk/execution imports, and Stage 1.5 files have zero diff.
21. A read-only integration test against a generated temporary sealed-export fixture, never the user's real local export.
22. Observation-membership and diagnostic persistence tests: a candidate with zero observations and an observation for a non-candidate article each reject the export before output creation; ordinary terminal/malformed/conflict diagnostic codes appear only in the parent outcome, while `audit_diagnostics.jsonl` contains only `forbidden_semantic_authority_attempt` rows and counts their distinct observation identities.

## 11. Future Operation and Rollout

This Design authorizes no automatic run and no VPS operation. After Design review and an approved Implementation Plan:

1. Implement and test the local adapter.
2. Run it once against the already verified local export `3fbe...92247` using a fresh Stage 1.6A output root.
3. Load and verify the resulting local completion manifest and receipt.
4. Treat a failed source-audit verdict as an honest result. Do not alter the frozen export or drop failed candidates. Any desired historical recollection/refetch is a separate 1.6B operational/design decision.
5. Keep the Stage 1.6B VPS live-observation deployment separate. It is not a prerequisite for this historical source audit and does not change the historical result’s non-PIT status.

Rollback is a no-op: the adapter creates only a new local Stage 1.6A output root. It never changes the sealed export or runtime collectors. A partial adapter output is non-consumable and may be preserved for diagnosis.

## 12. Allowed Future Implementation Scope

The later Implementation Plan may modify only the minimum paths needed for this adapter:

```text
src/research/external_signal_shadow/stage1_6a_futures_delisting_*.py
scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py
tests/research/external_signal_shadow/test_stage1_6a_*.py
tests/scripts/external_signal_shadow/test_run_stage1_6a_sealed_export_source_audit.py
tests/fixtures/external_signal_shadow/stage1_6a_sealed_export_adapter/
docs/plans/2026-08-22-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-implementation-plan_CN.md
```

`configs/base.py`, every Stage 1.5 path, all Stage 1.6B producer/client/observer/storage paths, and the existing fixture-runner semantics are read-only unless a later approved Design explicitly expands scope.

## 13. Open Questions

None that changes the implementation path. The actual pass/fail metric values, real BAPI template variations, and whether a future complete recollection is worthwhile are runtime audit results, not design branches. They fail closed through the defined diagnostics and verdict predicates.

## 14. Design Completion Gate

This Design is ready for independent review. Implementation planning is allowed only after review approval. Implementation, local operation, VPS deployment, replay, risk-veto enforcement, and all trading authority remain disallowed until separately approved by the relevant gates.
