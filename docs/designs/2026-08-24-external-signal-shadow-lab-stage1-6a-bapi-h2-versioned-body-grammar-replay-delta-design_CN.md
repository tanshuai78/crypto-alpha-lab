# Stage 1.6A BAPI H2 Body Grammar And Versioned Replay Delta Design

**Status:** `design_draft_pending_review`
**Date:** 2026-08-24
**Artifact type:** narrow Design delta
**Implementation baseline:** `d1f7ee2d9d8eb37389feeed912ff13d34fba8e05`
**Parent authorities:**

- `2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md` (`SHA-256: 1cb90f89113ceda4d2037cb62d60b8a9f769f7d58c467ad0e515332bc13563fd`)
- `2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-adapter-derived-artifact-schema-delta-design_CN.md` (`SHA-256: 2572849bf7df9154170ebc28f9687315728566a7c9498153f346d61308aaeb34`)
- `2026-08-23-external-signal-shadow-lab-stage1-6b-terminal-status-field-contract-correction-design_CN.md` (`SHA-256: 4bc7bc60a5435f9d71735319eac0dc84bf655bd94bc5f065652545f472596aae`)

```text
design_p0 = pending_review
implementation_plan_allowed = false
implementation_allowed = false
deployment_allowed = false
RISK_LIVE_TRADING_ENABLED = false
```

## 1. Confirmed Facts

1. Stage 1.6A consumes one exact verified Stage 1.6B historical sealed export. It performs no collection, source substitution, threshold relaxation, PIT claim, replay, paper-trading, live-trading, execution, or alpha authorization.
2. Parent v2 Design Section 7.3 allows `table`, `tbody`, `tr`, and `td`; those tags are already present in the committed implementation. A table-grammar delta is therefore neither necessary nor authorized.
3. Parent v2 Design Section 7.3 allows `h3` and `h4`, but not `h2`. The committed `ALLOWED_TAGS` and `BLOCK_TAGS` have the same omission.
4. Real sealed export `e9ec315753ead7a975c8df87de8fc1670e8b8eb890376a16eca4bb44b2007734` contains trusted raw detail payload `5f9d2b632423e3d256ab6dd8221ce0809037c5772e8c123c6a66fdd49ea77e27` for article `572715f2d96e47769ebbb967c2a6e445`. The payload is a valid BAPI envelope and its body tree contains an `h2` node at `root.child[4]`.
5. The current legacy grammar pair (G1) reducer fail-closes that article as `body_parse_unresolved`. Its text explicitly states that Binance Futures will automatically settle and delist `REEFUSDT` at `2025-01-22 09:00 UTC` (`1737536400000`).
6. Two independent Stage 1.6B historical exports produced the same remaining body result. Both Stage 1.6A audits reached `34/35` source-integrity parents but only `29` historical events. The source-integrity ratio passes; the frozen `MIN_HISTORICAL_EVENTS = 30` gate does not.
7. A process-local, no-write simulation that adds only `h2` as an existing heading-block tag produces: trusted REEF parent, one in-scope `REEFUSDT` child, `35/35` source integrity, `30` historical events, `30` event days, and `44` symbols. This is evidence for the narrow change, not an approved durable result.
8. Existing completed Stage 1.6A Adapter v2 audit roots carry the legacy grammar pair G1: `body_normalization_version=stage1_6a_bapi_body_tree_v1` and `semantic_extractor_version=stage1_6a_extractor_v1`. A consumer that silently applies changed grammar to those roots would no longer reproduce their persisted projections.

## 2. Assumptions

1. The referenced local sealed export remains available for implementation preflight. If it is unavailable or its raw SHA differs, implementation stops; a substitute payload is not accepted.
2. The parent contracts, artifact schemas, metric definitions, threshold values, source profile, and sealed-export loader remain unchanged.
3. The delta is limited to deterministic local reduction of already sealed bytes. It does not require a new Stage 1.6B collection run.

## 3. Root Cause / Core Issue

The current grammar treats a valid BAPI heading node, `h2`, as unknown and therefore rejects the entire canonical body. This produces a false `body_parse_unresolved` result for an otherwise trusted, immutable source payload.

The defect must not be repaired by mutating `stage1_6a_bapi_body_tree_v1`: doing so changes the semantic interpretation of already completed Stage 1.6A Adapter v2 roots carrying G1 and breaks independent replay. The correction is a versioned grammar extension, not a permissive parser or a threshold exception.

## 4. Decisions

### 4.0 Exact Override / Authority Precedence

For the Stage 1.6A sealed-export adapter only, this Delta supersedes Parent v2 at exactly these points:

1. Parent v2 Section 7.3's fixed G1 grammar/version contract is replaced by the supported G1/G2 pairs in Section 4.1. G1 retains the Parent v2 grammar, including its `h2` rejection. G2 has only the Section 4.2 `h2` addition.
2. Parent v2 Section 12.6's fixed-value constraints for `body_normalization_version` and `semantic_extractor_version` are replaced by the exact supported-pair set in Section 4.1. A completed root must persist one complete supported pair; it may not combine pair members.

All Parent v2 key sets, schema versions, `artifact_profile_version`, metrics, thresholds, authority flags, completion order, and safety semantics remain unchanged. Where this Delta is silent, Parent v2 remains authoritative. No other Parent v2 clause is superseded.

### 4.1 Versioned Grammar Pair

`G1` and `G2` below name only the body-normalization and semantic-extractor pair. They are not Stage 1.6A versions: the adapter artifact profile remains `stage1_6a_sealed_export_source_audit_v2` for both. The literal persisted strings retain their `v1`/`v2` suffixes.

The only supported pairs are:

| Pair | `body_normalization_version` | `semantic_extractor_version` | Body grammar |
|---|---|---|---|
| G1 legacy grammar pair | `stage1_6a_bapi_body_tree_v1` | `stage1_6a_extractor_v1` | Existing exact grammar; `h2` remains unknown and fail-closed. |
| G2 current grammar pair | `stage1_6a_bapi_body_tree_v2` | `stage1_6a_extractor_v2` | Exact G1 grammar plus `h2`; `h2` is a heading block. |

Mixed pairs, unknown values, absent values, or compatibility aliases are completed-consumer rejection conditions. A new writer emits G2 only. Before it loads or reduces source bytes, the completed consumer reads the verified persisted summary and completion manifest, requires their ordered pair to be equal and supported, then passes that one pair into the reducer. The reducer passes the same pair to every body parse, semantic-ID seed, semantic-extraction row, and non-null schedule-evidence pair. Grammar selection must not depend on mutable module-level current-writer defaults.

### 4.2 Exact G2 Grammar Delta

G2 adds only `h2` to the allowed `element.tag` set. It adds `h2` to the block set with the same pre-children and post-children LF emission used by `h3` and `h4`.

All other G1 rules remain exact and unchanged:

```text
root:    exact keys {node,child}; node=root; child=array
element: keys subset {node,tag,attr,child}; attr absent/object; child absent/array
text:    exact keys {node,text}; node=text; text=string
br:      child absent or [] only
unknown shape/tag/key: body_parse_unresolved
```

G2 allowed tags are exactly:

```text
{a,br,em,h2,h3,h4,li,p,span,strong,table,tbody,td,tr,u,ul}
```

G2 block tags are exactly:

```text
{h2,h3,h4,li,p,tr,td}
```

`table` and `tbody` remain transparent recursion. No table-cell interpretation, attribute interpretation, HTML entity policy, new schedule regex, or symbol inference is introduced.

### 4.3 Derived Artifact And Metric Consequences

No durable artifact key set, schema version, artifact profile version, metric formula, threshold, candidate denominator, source profile, or authority flag changes.

For one completed root, the pair in `stage1_6a_futures_delisting_source_audit_summary.json` equals the pair in `completion_manifest.json`, every `semantic_extractions.jsonl` row, and every non-null schedule-evidence pair. Any mismatch rejects completed consumption. A G2 output carries G2 in all of those existing version-valued fields. Because semantic IDs include both version strings, a G2 semantic extraction ID is distinct from a G1 ID for the same source revision. The old Stage 1.6A Adapter v2 root carrying G1 remains immutable and valid under G1 replay; a G2 audit is written to a new Stage 1.6A output root.

## 5. Scope / Non-Goals

### In scope

- Versioned G1/G2 canonical body normalization and semantic-extractor replay dispatch.
- One `h2` grammar addition and its exact LF behavior.
- G1 replay preservation, G2 write behavior, and independent-consumer version-pair rejection tests.
- Read-only real-export preflight using the frozen REEF payload identity and new G2 derived audit from an existing sealed export.
- The sealed-export adapter reducer and its completed-consumer storage loader, solely to implement the persisted-pair dispatch above.

### Explicit non-goals

- Stage 1.6B producer, source profile, probe, collection, retry, sealing, storage, or TerminalStatus changes.
- Table grammar changes; G1 already supports the approved table tags.
- Schema additions, artifact-profile bumps, candidate rule changes, threshold changes, source-export merging, or mutation of any sealed export.
- New parsing rules for `h1`, `h5`, unknown tags, table attributes, schedules, symbols, assets, or publication dates.
- Changes to `stage1_6a_futures_delisting_audit.py`, `stage1_6a_futures_delisting_models.py`, or their `BODY_NORMALIZATION_VERSION` / `SEMANTIC_EXTRACTOR_VERSION` constants. They are a separate fixture-audit contract and remain unchanged.
- PIT, replay permission, risk, paper, live, execution, trading, or deployment authorization.

## 6. Acceptance Invariants

| ID | Invariant |
|---|---|
| INV-H2-01 | G1 reduction is byte-for-byte behaviorally frozen: `h2` remains `body_parse_unresolved`; Stage 1.6A Adapter v2 roots carrying G1 rebuild with G1 only. |
| INV-H2-02 | G2 accepts only well-formed `h2` under the exact grammar and emits LF before and after its children. |
| INV-H2-03 | G2 has no tag expansion beyond `h2`; every other G1 unknown tag or malformed node remains `body_parse_unresolved`. |
| INV-H2-04 | Before source-byte reduction, a persisted summary and completion manifest must carry one exact supported version pair; mixed, unknown, absent, or mismatched pair values reject completed consumption with `AdapterInputError`. |
| INV-H2-04a | Within one completed root, the summary pair, completion-manifest pair, every semantic-extraction row pair, and every non-null schedule-evidence pair are equal. |
| INV-H2-05 | Where both pairs establish semantic authority for one selected detail revision, G2 semantic IDs are version-bound and cannot collide with G1 semantic IDs. |
| INV-H2-06 | Parent, revision, extraction, notice, contract, diagnostic, summary, receipt, and completion schemas remain their approved exact schemas. |
| INV-H2-07 | Existing Stage 1.6A Adapter v2 audit roots carrying G1 are read-only evidence. G2 writes only a new output root and never overwrites, relabels, or upgrades a G1 root. |
| INV-H2-08 | The REEF raw payload is admitted by G2 only when its existing BAPI envelope, article identity, provenance, and selected revision linkage all pass. |
| INV-H2-09 | For the frozen REEF payload, G2 produces an in-scope `REEFUSDT` perpetual child with settlement `1737536400000`, subject to all existing mapping and classification rules. |
| INV-H2-10 | All authority flags remain exactly false. A G2 source-audit result, even if true, grants no operational permission beyond the parent Design's design-only action mapping. |

## 7. Producer / Writer / Consumer / Reviewer Matrix

| Role | Contract impact |
|---|---|
| Stage 1.6B producer | None. It continues to provide immutable raw bytes and existing provenance. |
| Stage 1.6A writer | Selects G2 by default for new audit roots; emits the G2 pair into existing exact fields and seals completion manifest last. |
| Completed consumer | Reads persisted pair first; dispatches to G1 or G2 reducer; rejects unsupported/mixed pair before projection or metric comparison. |
| Existing Stage 1.6A Adapter v2 root carrying G1 | Read-only historical evidence; replays under G1 and is accepted only when its independently rebuilt verdict equals its persisted verdict. The currently referenced G1 roots are known to rebuild `false`. |
| Reviewer | Verifies the frozen raw identity, G1 replay stability, G2 REEF extraction, exact schemas, and all-false authority set. |

## 8. Data / State / Temporal Contract

```text
one verified sealed export
  -> source bytes and selected revision unchanged
  -> persisted grammar pair selects G1 or G2 reducer
  -> deterministic parent outcomes and projections
  -> independently rebuilt summary
  -> completion manifest last
```

The source is still historical evidence only:

```text
system_available_at_ms = null
fact_available_at_ms = null
capture_time_status = historical_unknown
point_in_time_replay_eligible = false
risk_veto_candidate = false
```

G2 does not reinterpret publication time, list-capture time, observation time, or any source availability time.

## 9. Failure Semantics

| Condition | Required behavior |
|---|---|
| G2 well-formed `h2` | Traverse as a heading block and continue existing normalization. |
| G1 `h2` | `body_parse_unresolved`; parent remains denominator-visible. |
| Unknown tag including `h1` or `h5` | `body_parse_unresolved`; no partial semantic output. |
| Malformed `h2` node, malformed child, extra key, invalid attr, or non-empty `br.child` | `body_parse_unresolved`; no partial semantic output. |
| Unsupported/mixed persisted version pair | Completed-consumer `AdapterInputError`; no acceptance claim. |
| Missing frozen REEF reference bytes during implementation preflight | STOP before implementation; do not substitute a different payload. |
| G2 output cannot reserve/write a required durable artifact | Follow parent manifest-last fail-closed behavior; no completed claim. |

## 10. Persistence / Restart / Idempotency

This delta changes neither the output family nor the parent atomic-write protocol. The existing writer continues to emit all authoritative artifacts before `completion_manifest.json` and the completed consumer continues to reject incomplete roots.

G1 and G2 are separate audit roots. There is no in-place migration and no resume that changes a root's grammar pair. Re-running the same sealed export under G2 uses a distinct `audit_run_id` and output root; deterministic G2 projection bytes are expected for the same source and G2 pair, subject only to the parent Design's explicit `semantic_extracted_at_ms` comparison exclusion.

## 11. Compatibility / Migration / Rollback

| Case | Rule |
|---|---|
| Existing completed Stage 1.6A Adapter v2 root carrying G1 | Retain and consume only through G1 replay dispatch. |
| New audit root after delta | Emit G2 pair only. |
| G1 root presented as G2 or vice versa | Reject; no alias or auto-upgrade. |
| Rollback | Stop creating G2 roots. Existing G1 and G2 roots remain independently readable by their declared pair; never rewrite either. |

## 12. Evidence And Fixture Provenance

The implementation preflight must hash and verify this local immutable reference before code changes:

```text
source_export_id = e9ec315753ead7a975c8df87de8fc1670e8b8eb890376a16eca4bb44b2007734
source_article_id = 572715f2d96e47769ebbb967c2a6e445
detail_raw_sha256 = 5f9d2b632423e3d256ab6dd8221ce0809037c5772e8c123c6a66fdd49ea77e27
raw_relative_path = raw_payloads/detail/572715f2d96e47769ebbb967c2a6e445/5f9d2b632423e3d256ab6dd8221ce0809037c5772e8c123c6a66fdd49ea77e27.bin
```

Committed unit fixtures may be minimal synthetic BAPI body trees, but must be explicitly labeled synthetic. They prove grammar mechanics only. The real-export preflight proves the production-shaped payload and REEF semantic result; neither fixture type may replace the other.

## 13. Verification Strategy

Implementation Plan must begin RED and cover:

1. G1 parser rejects a valid `h2` body exactly as `body_parse_unresolved`.
2. G2 parser accepts a valid `h2` body and emits the exact block-newline result.
3. G2 rejects malformed `h2`, `h1`, `h5`, unknown tags, extra keys, invalid `attr`, invalid `child`, and non-empty `br.child`.
4. A completed Stage 1.6A Adapter v2 audit carrying G1 replays unchanged under G1 even when G2 is available; a G2 audit replays unchanged under G2; a consumer rejects every mixed/unknown/absent version pair before source-byte reduction.
5. Where both pairs establish semantic authority for one selected revision, G1 and G2 semantic IDs differ through their version-bound seed.
6. The frozen real export preflight proves G2 output has REEF `trusted`, `in_scope`, one eligible child, `REEFUSDT`, and settlement `1737536400000`.
7. The G2 real-export audit independently rebuilds to `35/35` source integrity, `30` historical events, `30` event days, `44` symbols, and retains all authority flags false.
8. Exact artifact schemas, storage confinement, manifest-last behavior, source-byte binding, and prior tamper tests remain GREEN.

## 14. Safety / Authority Boundary

```text
source_audit_passed may become true only through a new G2 audit root
!= point_in_time_source_validated
!= replay_allowed
!= paper_trading_allowed
!= live_trading_allowed
!= execution_engine_allowed
!= RISK_LIVE_TRADING_ENABLED
```

No Stage 1.5 process, VPS collector, market-data pipeline, risk process, or execution engine is modified or authorized by this delta.

## 15. Rollout

There is no deployment rollout in this delta. After implementation and independent completion audit, the only permitted operational validation is a new local G2 Stage 1.6A audit root consuming an existing exact sealed export. VPS collection remains out of scope.

## 16. Open Questions

N/A. The raw payload, exact missing tag, G1 replay requirement, G2 version names, block semantics, expected REEF result, and safety boundary are all fixed above.

## 17. Approval Boundary

This document authorizes no code change until Design review passes and the user explicitly approves it. The subsequent Implementation Plan must use this document and the three parent authorities as immutable inputs.
