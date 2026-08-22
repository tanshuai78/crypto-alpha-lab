# Stage 1.6B Delisting Catalog Delta Storage Consumer And Restart-Read Scope Amendment

**Status:** design draft for review
**Parent Base Design:** `docs/designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md`
**Parent Base Design SHA-256:** `83aaa473a9ddb287ee916eae4da327966daa7b0afd5c465f7cc883a06e4f6bc0`
**Parent Catalog Delta:** `docs/designs/2026-08-21-external-signal-shadow-lab-stage1-6b-delisting-catalog-index-schema-authority-delta-design_CN.md`
**Parent Catalog Delta SHA-256:** `1cf8c0f7af20c15f6cabcbbe0192a1cdcb036b5f62506fb15ce833e89ad070b4`

## 1. Purpose

The parent Catalog Delta Section 7 freezes `v2_historical_export_acceptance` at the local consumer boundary, and Section 6 requires v1 artifacts to be rejected before restart reconciliation/network admission. Their concrete read-path owners are `load_sealed_export()` and bounded reconciliation in `stage1_6b_canonical_source_storage.py`, but the parent Delta Section 3 omitted that path from its maximum whitelist.

This amendment resolves only that internal scope contradiction. It does not change source authority, catalog grammar, record identities, checkpoint/restart semantics, storage budgets, collector behavior or any permission.

## 2. Exact Scope Amendment

The parent Catalog Delta Section 3 implementation whitelist is amended by exactly one path:

```text
src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py
```

The only allowed purposes are:

1. An additive `load_sealed_export()` v2 historical consumer-acceptance check that independently validates the already hashed authoritative artifacts against the parent Delta Section 7 predicate.
2. A bounded, read-only v2 schema/profile preflight inside the existing restart reconciliation read path. Before it computes or writes a reconciliation checkpoint, it may reject a v1/mismatched checkpoint, root contract/attestation, or any parsed authoritative `ListCapture`/`ArticleDiscovery` record encountered in the existing bounded per-stream committed-prefix verification read.

The consumer check requires:

```text
v2 source_profile_id
v2 HistoricalCoverage schema and four-field transcript grammar
v2 ListCapture selected-catalog provenance
v2 ArticleDiscovery source-catalog provenance
v2 ObserverCheckpoint status/coverage grammar
```

For every parsed authoritative record encountered in that existing bounded committed-prefix verification batch, the restart preflight requires:

```text
ListCaptureRecord.schema_version == stage1_6b_list_capture_v2
ArticleDiscoveryRecord.schema_version == stage1_6b_article_discovery_v2
source_profile_id == binance_public_web_bapi_en_delisting_catalog_v2
ListCapture selected_catalog_id == 161
ListCapture selected_catalog_name == Delisting
ListCapture selected_catalog_total >= article_count
ArticleDiscovery source_catalog_id == 161
ArticleDiscovery source_catalog_name == Delisting
```

Any missing or mismatched predicate rejects before reconciliation-checkpoint write and before network/client construction. The restart preflight is not a root scan and does not migrate legacy data: it reuses only the existing bounded prefix/tail read batch, adds no second scan, and does not change reconciliation, checkpoint accounting or stream hash/offset algebra.

The corresponding existing verification path remains within the parent Delta's `tests/research/external_signal_shadow/test_stage1_6b_*.py` family:

```text
tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py
```

## 3. Explicitly Forbidden In That Path

No implementation under this amendment may modify:

```text
seal_export() copy, quota, temporary-file or rename semantics
Stage16BStorageGuard, shared lock, reserve, root-max or host-admission logic
root-path validation, checkpoint accounting, stream-offset/hash algebra or writer ownership
terminal-status producer semantics
any source request, parser, catalog selection or collector write behavior
configs/base.py, Stage 1.5, Stage 1.6A, risk, replay or trading code
```

`load_sealed_export()` remains a local read-only consumer. It must reject invalid v2 provenance; it must not repair, migrate, relabel or rewrite v1/v2 artifacts.

## 4. Required Proof

A future Implementation Plan must prove with RED tests that otherwise hash-valid artifacts are rejected when any required v2 profile/schema/transcript/provenance/checkpoint predicate is false, and that a valid v2 historical export is accepted without reparsing raw index payloads. It must separately prove that a bounded committed-prefix batch containing `[v1 ListCapture, v2 ListCapture]` or `[v1 ArticleDiscovery, v2 ArticleDiscovery]` rejects before reconciliation write or opener call, without mutating root bytes.

The Plan must also prove zero diff in every forbidden area above. No real source-profile probe, historical backfill, live observer, VPS action, source-audit pass, PIT/replay/risk/trading authority or runtime artifact is authorized by this amendment.

## 5. Acceptance Boundary

This amendment is complete only when review confirms that the implementation whitelist now matches the already frozen consumer/restart-read owners and remains limited to the listed read-only predicates. It may be referenced by an Implementation Plan only after approval.
