# Stage 1.5G N=3 跨根去重与产品机制分层准入 Design

## 1. 已确认事实

1. 旧 Stage 1.5G N=2 receipt 已独立完成，其输出位于 `data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z/`，并严格绑定 `2` 个 parent event、`8` 个 child symbol。该 receipt、其 producer/loader，以及 Stage 1.5H V3 receipt 都是本次 No-Touch。
2. 新 CT root 的本地 Stage 1.5G review 为 clean pass：`data/external_signal_shadow/stage1_5g/reviews/20261002T010000Z_ctusdt_review/stage1_5g_live_depth_evidence_review_summary.json`，SHA-256 为 `9f6a1e9797dbc42af3ce103ed231689adb0422ef1ab23768ca398eb8ec153c1c`。
3. CT root 的 root-level evidence manifest 是 `SHA256SUMS`，SHA-256 为 `f69efe25ea2efd03054372c41f882e2deb10e9842b890d71f60c19ce9b44f7db`；本地不存在名为 `stage1_5f_manifest.json` 的替代 artifact，不得虚构该路径。
4. 新 CT root 的正式 child projection 有八个 symbol：七个已有 Batch 7 child 加上 `CTUSDT`。其中 CT 的 exact identity 为：

```text
event_symbol_id = 88df6bae915fb096ea7fe92b4a92d22b3c5b7b268e999636ff062c3fd9989345
event_id        = 374345c5e4527ca0f061155796909acb385fbd084172f175bd8accb00cdbd963
source_article  = 6bd26adeb6f742fe88eb72faca183566
symbol          = CTUSDT
```

5. 因此，将整个 CT root 追加到旧 N=2 cohort 会重复计入 Batch 7。正确的新 receipt 必须只从该 root 投影 CT child，最终恰为 `3` 个 parent article / `3` 个 parent event / `9` 个 child symbol。
6. 三个 parent 的市场机制不相同：`CTUSDT` 是 standard crypto perpetual；`MOONSHOTUSDT` 是 pre-IPO equity perpetual；Batch 7 是同一公告下的 TradFi equity/ETF perpetual batch。它们可共同证明 L2 采集完整性，但不能被直接池化为同一产品机制下的流动性或成本结论。
7. 当前 `configs/base.py` 仍冻结 `EXTERNAL_SIGNAL_STAGE1_5G_MIN_EVENT_FAMILY_SAMPLE_REQUIRED = 3` 与 `EXTERNAL_SIGNAL_STAGE1_5G_MIN_SOURCE_ARTICLES_REQUIRED = 2`。本 Design 不修改配置、阈值、采集器或任何交易权限。

## 2. 核心问题与决定

### 2.1 核心问题

现有 N=2 producer 的输入成员、计数、schema、run-id grammar 和 strict loader 均精确绑定 N=2。原地扩展会让旧 receipt 的 producer/consumer contract 发生语义漂移。

此外，CT root 重复包含 Batch 7；只按 root 数量或 child 数量聚合，都会把同一 parent event 当成独立证据。若新 receipt 不把三种机制永久写入 parent ledger，未来 consumer 可能将不同价格形成机制的 child 直接求均值。

### 2.2 决定

新增一个独立、只读的 `Stage 1.5G N=3 regime-stratified admission` producer、strict loader、CLI、测试和 receipt namespace。它只接纳本节 3 的三条 exact input record，在 CT root 内执行唯一允许的 CT child projection，并输出带有冻结 product-regime ledger 的 N=3 receipt。

本 Design 不建立通用资产分类平台、不自动推断公告语义、不发现新 root，也不修改旧 N=2 或 1.5H V3 artifacts。任何未知 product regime 或第四个 parent 都不属于本 Design，必须新建 Design 与 receipt。

## 3. 冻结 Authority Packet

### 3.1 Upstream source contract

新 producer 在读取任一 source root 前，必须重算并要求下列 bytes 精确一致：

| Path | SHA-256 |
| --- | --- |
| `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py` | `596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d` |
| `configs/base.py` | `414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4` |
| `src/research/external_signal_shadow/safety.py` | `1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d` |

必须从已验证模块调用 `load_stage1_5g_inputs()` 与 `build_stage1_5g_review_summary()`。分类 lineage 只可从同一次 `load_stage1_5g_inputs()` 返回的 `accepted_events` canonical bundle projection 中读取 `source_detail_url_normalized` 与 `source_anchor_contract_hash`，并须先通过同次 `build_stage1_5g_review_summary()` clean-pass reducer。不得手写 summary、直接打开 events/depth JSONL、复用旧 cross-root reducer，或绕过 upstream clean-pass reducer。

### 3.2 Exact input records

输入顺序、路径与 SHA 是 contract，不得 discovery、替换、补录或重排：

| input_key | stored summary / SHA-256 | source root / SHA256SUMS SHA-256 | allowed projected parent / child |
| --- | --- | --- | --- |
| `moonshot` | `data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json` / `849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082` | `data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot` / `611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db` | article `7379b99aa0f349a49c3b3feca1b4bbd6`; event `e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5`; `MOONSHOTUSDT` |
| `batch7` | `data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json` / `28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37` | `data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7` / `0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280` | article `0c6ea14ba89b451db6ec9ec364045d22`; event `d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0`; exact Batch 7 set in Section 3.3 |
| `ct_projection` | `data/external_signal_shadow/stage1_5g/reviews/20261002T010000Z_ctusdt_review/stage1_5g_live_depth_evidence_review_summary.json` / `9f6a1e9797dbc42af3ce103ed231689adb0422ef1ab23768ca398eb8ec153c1c` | `data/external_signal_shadow/local_evidence/20261001T074500Z_stage1_5f_ctusdt` / `f69efe25ea2efd03054372c41f882e2deb10e9842b890d71f60c19ce9b44f7db` | article `6bd26adeb6f742fe88eb72faca183566`; event `374345c5e4527ca0f061155796909acb385fbd084172f175bd8accb00cdbd963`; only `CTUSDT` |

For all inputs, recomputed summary must have `schema_version = 2`, `decision = stage1_5g_depth_evidence_clean_pass`, `clean_depth_evidence_pass = true`, no blockers, and all upstream false authority keys set to boolean `false`.

### 3.3 Exact CT re-projection and duplicate exclusion

The recomputed `ct_projection` root must have exactly these eight formal children, with no additional child:

```text
ACNUSDT, BWETUSDT, CRMLUSDT, MPUSDT, NKEUSDT, SECZUSDT, UNHUSDT, CTUSDT
```

The seven non-CT children must exactly equal the Batch 7 child identities already recomputed from the `batch7` input. The N=3 reducer may emit only the CT identity given in Section 1.4 from the `ct_projection` root. It must reject: a missing CT child; a CT parent mismatch; one changed Batch 7 duplicate; a ninth child; selecting an arbitrary clean child; or emitting any duplicated child.

This is a declared parent-aware re-projection, not a liquidity filter and not a selective outcome rule. It is necessary only because the newer source root contains a duplicate copy of an already-admitted parent event.

### 3.4 Frozen product-regime declarations

Each declaration is a conservative, Design-owned semantic label bound to the source article identity. `source_detail_url_normalized` and `source_anchor_contract_hash` are projected only from the canonical `accepted_events` bundle described in Section 3.1. The producer must also derive `https://www.binance.com/en/support/announcement/<parent_article_id>` and require exact URL equality. `source_anchor_contract_hash` is a frozen Stage 1.5 launch-anchor contract identity, not a claim that raw announcement page bytes are stored in this receipt. The declaration cannot establish price quality, phenomenon, Alpha, execution feasibility, or a future consumer permission.

| product_regime_id | parent article / normalized official URL | child count | declaration |
| --- | --- | --- | --- |
| `crypto_standard_perpetual` | `6bd26adeb6f742fe88eb72faca183566` / `https://www.binance.com/en/support/announcement/6bd26adeb6f742fe88eb72faca183566` | 1 | `underlying_economic_type = crypto_token`; `lifecycle_regime = standard`; `reference_market_availability = not_asserted`; `mark_price_regime = not_asserted` |
| `pre_ipo_equity_perpetual` | `7379b99aa0f349a49c3b3feca1b4bbd6` / `https://www.binance.com/en/support/announcement/7379b99aa0f349a49c3b3feca1b4bbd6` | 1 | `underlying_economic_type = equity`; `lifecycle_regime = pre_ipo`; `reference_market_availability = unavailable_pre_ipo`; `mark_price_regime = exchange_trade_derived` |
| `tradfi_equity_or_etf_perpetual_batch` | `0c6ea14ba89b451db6ec9ec364045d22` / `https://www.binance.com/en/support/announcement/0c6ea14ba89b451db6ec9ec364045d22` | 7 | `underlying_economic_type = tradfi_equity_or_etf`; `lifecycle_regime = standard`; `reference_market_availability = not_asserted`; `mark_price_regime = not_asserted` |

`not_asserted` means the receipt deliberately does not make a claim about that field. It is neither an inferred default nor an eligible value for a future consumer. This Design does not introduce an `unclassified` ingestion path because it discovers no inputs. A later new product must receive its own frozen input and Design; it cannot be silently added to this N=3 receipt.

### 3.5 Classification evidence provenance (Design review only)

The three declarations in Section 3.4 are approved against these exact, frozen Binance BAPI article-detail payload identities:

| parent_article_id | raw_bapi_detail_payload_sha256 | evidence_role |
| --- | --- | --- |
| `6bd26adeb6f742fe88eb72faca183566` | `99514345ff685fc6fc7f0a927c3deb0f19cd3aee816946fabec6e64f8196e2d6` | `design_review_only` |
| `7379b99aa0f349a49c3b3feca1b4bbd6` | `dd7b872ada6981557179d695a8f449e370415850317b15305d063f0db8bd44c0` | `design_review_only` |
| `0c6ea14ba89b451db6ec9ec364045d22` | `cde99bc0bfe48c23b4f6e66c727b032ca8c4f74d941ce0671c62d7abdb86aea9` | `design_review_only` |

These payloads are evidence for independent review of the semantic labels only. They are not N=3 producer inputs, runtime TCB members, receipt artifacts, manifest entries, or a future-consumer authority. The implementation consumes only the Section 3.1/3.2 authority chain and implements the approved Section 3.4 declarations exactly.

## 4. 范围与非目标

### 4.1 In scope

- 新的 local-only N=3 producer, strict loader, CLI, focused tests, and one generated receipt namespace.
- Exactly three frozen source roots, CT single-child re-projection, parent/child collision checking, and the Section 3.4 product-regime ledger.
- Atomic publication, crash/restart classification, deterministic JSON/Markdown projection, and a strict false authority vector.
- A future-consumer contract requiring explicit one-regime admission and prohibiting cross-regime pooled aggregation.

### 4.2 Explicit non-goals

- Do not change the old N=2 Stage 1.5G module, its loader, receipt, Design, Plan, or Completion Audit evidence.
- Do not modify Stage 1.5H V3, regenerate it as `V3.1`, or call its output an execution-cost floor.
- Do not modify Stage 1.5D/1.5F collection, VPS processes, network collection, `configs/base.py`, or existing data schemas.
- Do not automatically classify future products, create a registry/framework/plugin system, or claim these three labels exhaust Binance products.
- Do not calculate outcome, PnL, slippage, spread, liquidity, cost, threshold, expectancy, benchmark, trade signal, replay, paper/live trading, execution, deployment, commit, push, SSH, or runtime authority.

### 4.3 TCB and threat boundary

Trusted computing base: approved Design exact bytes; the Section 3.1 frozen Stage 1.5G review module, `configs/base.py`, and `safety.py` exact bytes; CPython `hashlib`/`json`/`pathlib`/`os` primitives; and the local OS/filesystem completing individual syscalls.

The producer/loader defends against accidental byte drift, malformed or corrupt artifacts, static symlink/path escape, stale or partial publication, process crash/restart, and caller-supplied substitution. It does not claim to defend privileged OS compromise, a malicious concurrent local actor exchanging paths between validation and use, or a SHA-256 collision. Those exclusions do not relax the required pre-resolve symlink checks, post-resolve containment checks, strict final-byte validation, or crash/restart state machine.

## 5. Producer, Loader and Receipt Contract

### 5.1 Admission reducer sequence

The producer must execute in this order before creating a staging directory:

1. Re-verify all Section 3.1 upstream bytes before importing the production review module.
2. Before every `resolve()`, verify each stored review summary and every ancestor from project root is a regular non-symlink path; then verify its Section 3.2 SHA-256.
3. Before every `resolve()`, verify each source root and every ancestor from project root is a regular non-symlink directory; verify its `SHA256SUMS` exact SHA; invoke the production loader/reducer on that exact root.
4. Require stored and recomputed summary agreement on schema, decision, clean flag, source manifest SHA, formal completed child digest, and ordered formal-child projection.
5. Apply the exact membership contract for `moonshot`, `batch7`, then `ct_projection`; run Section 3.3 CT re-projection.
6. Require exactly `3` distinct parent article IDs, `3` distinct parent event IDs, `9` unique `event_symbol_id`, and `9` unique symbols.
7. Attach the only three Section 3.4 product-regime declarations, whose Design-review semantic provenance is Section 3.5, projecting URL and source-anchor hashes from the canonical accepted-event bundle, deriving each official URL from its re-admitted parent article ID, then checking URL, source-anchor hash, parent identity, child count, and product-regime field exactly. Do not read Section 3.5 payload bytes at runtime.
8. Require config values still equal `3` and `2`; then allow `formal_symbol_count = 9` and `distinct_source_article_count = 3`.

Any failure is fail-closed; no staging or final root may be created.

### 5.2 Canonical summary schema

`RUN_ID` must match:

```text
^stage1_5g_n3_regime_stratified_admission_[0-9]{8}T[0-9]{6}Z$
```

The final root is exactly:

```text
data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/<RUN_ID>/
```

The canonical summary has exactly these top-level keys:

```text
authority_flags
cross_root_evidence_count_status
decision
distinct_source_article_count
formal_symbol_count
independent_parent_event_count
input_records
parent_ledger
product_regime_ledger
run_id
schema_version
stage1_5g_gate3_complete
```

Required scalar values are:

```text
schema_version                     = 1
decision                           = stage1_5g_n3_regime_stratified_admission_pass
cross_root_evidence_count_status   = sufficient
formal_symbol_count                = 9
distinct_source_article_count      = 3
independent_parent_event_count     = 3
stage1_5g_gate3_complete           = false
```

`input_records` contains exactly the three ordered records from Section 3.2. Its `ct_projection` stored/recomputed formal projection retains all eight source children as evidence of the duplicate-exclusion check, while its emitted `parent_ledger` row contains only CT.

Every `parent_ledger` record has exactly:

```text
child_event_symbol_ids
child_symbols
parent_article_id
parent_event_id
product_regime_id
```

`product_regime_ledger` has exactly one declaration per `parent_article_id`, in `input_records` order. Each declaration has exactly:

```text
classification_status
lifecycle_regime
mark_price_regime
parent_article_id
product_regime_id
reference_market_availability
source_detail_url_normalized
source_anchor_contract_hashes
underlying_economic_type
```

`classification_status` must be `classified`. `source_anchor_contract_hashes` is a non-empty ordered lowercase-64-hex array in the parent child order and must equal the matching canonical accepted-event projection. No fallback, omitted field, extra key, type coercion, direct source-row read, or consumer supplied label is accepted. The product-regime ledger must be the deterministic projection of the three Design-owned declarations plus the one canonical upstream-bundle projection, not a CLI input.

The summary contains no raw snapshot, price, spread, slippage, depth, outcome, PnL, aggregate market metric, cost estimate, or conclusion.

### 5.3 Authority vector and regime-isolation contract

The receipt has exactly these thirteen boolean fields, all `false`:

```text
alpha_interpretation_allowed
commit_allowed
deployment_allowed
event_family_conclusion_allowed
execution_engine_allowed
execution_feasibility_claim_allowed
live_trading_allowed
network_collection_allowed
paper_trading_allowed
push_allowed
replay_allowed
ssh_allowed
trade_signal_allowed
```

The receipt proves only local structural re-admission of the three frozen inputs and their mechanism-separated parent ledger. `sufficient` is an operational sample-admission state only. It does not make Gate 3 complete, and it never grants Alpha, research conclusion, simulator, replay, execution, paper, live, network, deployment, commit, push, or SSH authority.

No existing consumer is wired by this Design. Any future consumer that elects to use this receipt must independently bind its Design to the exact receipt identity and strict loader, declare exactly one allowed `product_regime_id` for every aggregate, and STOP on a missing/unknown/unaccepted regime or an aggregate spanning more than one regime. Showing individual rows from several regimes without aggregation is permitted only when the future Design states that no pooled statistic or common market conclusion is formed.

### 5.4 Persistent lifecycle and crash recovery

After all Section 5.1 checks pass in memory, the writer classifies the requested `RUN_ID` before creating a staging root. A matching staging sibling is any direct final-parent child beginning `.<RUN_ID>.staging.`. A well-formed matching directory must be exactly `.<RUN_ID>.staging.<positive-decimal-pid>/`; a symlink, non-directory, or malformed matching sibling is `corrupt_or_unknown`.

| Pre-write state | Required action |
| --- | --- |
| Final absent and zero matching staging siblings | Fresh attempt may create only `.<RUN_ID>.staging.<pid>/`. |
| Final absent and one or more matching staging siblings | `staging_only`; STOP without resume, deletion, overwrite, or same-`RUN_ID` reuse. Only a fresh distinct `RUN_ID` may start. |
| Final present and zero matching staging siblings | Strictly classify final bytes: valid is `receipt_published`; invalid is `corrupt_or_unknown`. Never overwrite or resume either state. |
| Final present and one or more matching staging siblings | `corrupt_or_unknown`; STOP and never consume, delete, overwrite, or resume the mixed state. |

Each staged artifact uses a same-directory temporary file: write exact bytes, flush and file-`fsync`, then atomically rename it to its staged artifact name. The required order is:

1. `stage1_5g_n3_regime_stratified_admission_summary.json`
2. `stage1_5g_n3_regime_stratified_admission_review_CN.md`
3. `stage1_5g_n3_regime_stratified_admission_manifest.json` last
4. Strictly reload and validate the complete staged tree, then `fsync` the staging directory.
5. Atomically rename the staging root to the absent final root; an existing/colliding final root is STOP and must never be overwritten.
6. `fsync` the final parent directory, then strictly reload final bytes before returning `receipt_published`.

The manifest lists only `summary` and `review`, with exact `relative_path`, non-bool positive integer `byte_count`, and lowercase 64-hex `sha256`. It is canonical JSON and includes the exact input-record projection. Before every `resolve()`, the writer, state classifier, and strict loader reject a final/staging path, artifact, or ancestor symlink; after resolve, each path must remain contained in its declared project namespace. They reject unexpected file, malformed/noncanonical JSON, unlisted artifact, manifest byte/hash mismatch, wrong summary key set, wrong count, wrong product ledger, wrong false vector, or Markdown projection mismatch.

Any failure before final-root rename leaves `staging_only` and returns non-zero. Rename success followed by final-parent `fsync` failure returns non-zero `POST_RENAME_DURABILITY_FAILURE`; the writer must not delete or overwrite either root. A later invocation has no resume authority: it derives local state only from the pre-write table and strict final bytes.

## 6. Acceptance Invariants

- `INV-15G-N3-01`: Exactly the Section 3.2 three inputs are re-admitted through the frozen production Stage 1.5G loader/reducer; summary prose, hand-built dicts, raw JSONL readers, discovery, substitution, and root fallback are forbidden.
- `INV-15G-N3-02`: Every input binds stored summary SHA, source-root `SHA256SUMS` SHA, production recomputation, formal-child projection, and clean-pass false flags before any cross-root operation.
- `INV-15G-N3-03`: CT root must re-admit its exact eight-child projection; only the exact CT child may be emitted from it, and its seven duplicated Batch 7 children must exactly match the independent Batch 7 input.
- `INV-15G-N3-04`: Parent ledger is exactly `3 articles / 3 events / 9 child symbols`; Batch 7 remains one parent cluster with seven children, and all child IDs/symbols are unique after CT projection.
- `INV-15G-N3-05`: The three product-regime declarations are exact, complete, deterministic, parent-bound, and conservative. Their Design-review semantic evidence identities are exactly Section 3.5; runtime declaration checks consume no raw payload. Each source URL and source-anchor hash must be projected from the canonical upstream bundle and agree with its parent/article grammar. An absent, unknown, extra, or changed regime field is fatal.
- `INV-15G-N3-06`: No cross-regime pooled metric, conclusion, cost, liquidity, Alpha, or execution assertion may enter summary, review, manifest, or receipt-derived consumer state.
- `INV-15G-N3-07`: Summary, deterministic Markdown, and manifest have the exact Section 5 schema; all thirteen authority flags exist and are boolean `false`.
- `INV-15G-N3-08`: Only `receipt_published` after staged-tree validation, atomic rename, final-parent `fsync`, and strict final-byte validation is locally inspectable. Partial, stale, mixed final/staging, corrupt, symlinked, collision, post-rename durability-failure, or failed states are never consumable or resumable.
- `INV-15G-N3-09`: Old N=2 1.5G and 1.5H V3 artifacts remain immutable and are not silently reinterpreted as N=3.
- `INV-15G-N3-10`: This Design creates no present consumer. A future receipt consumer must bind exact receipt bytes in its own approved Design and may aggregate one declared product regime only.

## 7. Contract Impact Matrix

| Role | Owner / artifact | Allowed responsibility | Forbidden responsibility |
| --- | --- | --- | --- |
| Upstream producer | Frozen Stage 1.5G review module | Verify source root and compute formal child projection | Trust stored summary alone or expose raw depth rows to new producer |
| New N=3 writer | New local source module | Re-admit three exact inputs, CT projection, regime ledger, atomic receipt publication | Edit old N=2 contract, choose liquidity winners, calculate metrics, or discover roots |
| New strict loader | New local source module | Validate full receipt schema, integrity, state, projection and regime ledger | Tolerant defaults, legacy-receipt reinterpretation, or consumer authorization |
| Design-review classification evidence | Section 3.5 frozen BAPI payload identities | Permit independent review of the approved semantic labels | Become a runtime input, receipt artifact, manifest entry, or consumer authority |
| Existing N=2 / 1.5H V3 artifacts | Existing code and receipts | Remain historical immutable evidence | Become N=3 input/output or accept new schema |
| Future consumer | None in this Design | Only after new Design binds exact receipt and one regime | Pool regimes, infer missing labels, or grant authority from this receipt |
| Reviewer | Independent Design/Plan/Completion Audit | Independently re-run source and strict receipt validation | Rely on generated Markdown alone |

## 8. Failure Semantics

| Condition | Required result |
| --- | --- |
| Upstream source/config/safety byte drift | `STOP=stage1_5g_n3_regime_upstream_contract_drift` |
| Stored summary, root, `SHA256SUMS`, clean recomputation, or formal projection mismatch | `STOP=stage1_5g_n3_regime_input_authority_mismatch` |
| CT eight-child shape, CT identity, or duplicate Batch 7 comparison fails | `STOP=stage1_5g_n3_regime_ct_projection_mismatch` |
| Parent/article/event/child collision or count differs from 3/3/9 | `STOP=stage1_5g_n3_regime_parent_identity_mismatch` |
| Product-regime declaration, URL, source-anchor hash, field, type, or parent mapping differs | `STOP=stage1_5g_n3_regime_classification_mismatch` |
| Config threshold drift | `STOP=stage1_5g_n3_regime_threshold_not_met` |
| Matching stale staging sibling, malformed staging sibling, or final/staging mixed state | `STOP=stage1_5g_n3_regime_publication_integrity_failure`; never consume, resume, delete, overwrite, or reuse that `RUN_ID` |
| Rename succeeds but final-parent `fsync` fails | `STOP=stage1_5g_n3_regime_publication_integrity_failure` with non-zero `POST_RENAME_DURABILITY_FAILURE`; never delete or overwrite; later state derives only from strict final bytes |
| Staging/final integrity, collision, symlink, manifest, projection, or other state failure | `STOP=stage1_5g_n3_regime_publication_integrity_failure` |
| Existing/future consumer use without its own exact binding and one-regime aggregation declaration | `STOP=stage1_5g_n3_regime_future_consumer_not_authorized` |

## 9. L2 Research Boundary

This is evidence governance, not Alpha research. Required L2 fields are intentionally N/A:

| L2 item | Status |
| --- | --- |
| Alpha/economic mechanism | N/A; no market proposition is tested. |
| Claim level | Local input admission plus mechanism-separation only; not `phenomenon_supported`. |
| Independent unit | `parent_article_id` / `parent_event_id`; Batch 7 is one cluster, not seven independent opportunities. |
| PIT / hindsight | Fixed historical captures and existing official launch anchors only; no forward outcomes are read. |
| Outcome, PnL, cost, capacity, loss/MAE, tail, outlier, conditional Alpha | N/A; receipt carries no metrics. |
| Promotion / kill | N/A for Alpha. Invalid input is an evidence/contract failure, not negative expectancy. |
| Deferred claims | Any temporal microstructure, cross-exchange, cost, simulator, replay, execution, paper, or live claim requires a separate Design. |

## 10. Later Implementation Scope and Verification

The later Plan may whitelist only:

```text
src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py
scripts/external_signal_shadow/run_stage1_5g_n3_regime_stratified_admission.py
tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py
tests/scripts/external_signal_shadow/test_run_stage1_5g_n3_regime_stratified_admission.py
data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/<RUN_ID>/
```

Required evidence must include:

1. Independent Design review re-hashes the exact Section 3.5 payload bytes against their article IDs; runtime positive fixtures do not read those payloads.
2. Canonical runtime positive fixture invokes the actual upstream production loader/reducer for all three exact roots; no handcrafted cross-boundary input.
3. One-mutation RED tests for upstream SHA, stored summary SHA, source `SHA256SUMS`, non-clean recomputation, changed CT child, changed duplicated Batch 7 child, a ninth CT-root child, duplicate parent/article/event/symbol, wrong regime field, missing authority flag, wrong count, extra summary key, and injected Markdown market/Alpha text.
4. Strict-loader tests for artifact metadata key/length/hash, malformed canonical bytes, unlisted file, root/file/ancestor symlink, wrong manifest input projection, wrong regime ledger, and wrong Markdown projection.
5. Crash tests before/after each staged artifact, manifest-last publication, rename, and final-parent `fsync`; restart tests for stale matching siblings from another PID, malformed matching sibling, valid final, corrupt final, final-plus-staging mixed state, collision, post-rename durability failure, and a distinct fresh `RUN_ID`.
6. Production-wiring proof that no direct source-row reader bypasses the upstream loader/reducer and no runtime path opens a Section 3.5 payload, including AST/open-spy evidence where appropriate.
7. Actual anti-shortcut scanner return code, `RISK_LIVE_TRADING_ENABLED=False`, Git diff/index/worktree scope proof, independent code review, then fresh Completion Audit.

## 11. Open Questions

None blocking this Design. The three declarations are intentionally narrow and conservative; they are not a claim that every exchange product fits them. A fourth parent, a new product regime, raw-announcement archival expansion, cross-regime comparison, or any receipt consumer is deliberately deferred to a separate Design.

## 12. Design Self-Review and Handoff

- Mutable set: this new candidate document only.
- No-Touch set: all existing Stage 1.5D/1.5F collectors, `configs/base.py`, old N=2 1.5G source/CLI/tests/receipt, Stage 1.5H V3 source/CLI/tests/receipt, deployment and runtime artifacts.
- Permissions: `network_collection_allowed = false`; `trade_signal_allowed = false`; `paper_trading_allowed = false`; `live_trading_allowed = false`; `execution_engine_allowed = false`; `commit_allowed = false`; `push_allowed = false`; `deployment_allowed = false`; `ssh_allowed = false`.

Required sequence:

```text
independent Design review
-> user approval of exact Design bytes
-> Implementation Plan
-> independent Plan review
-> user implementation approval
-> implementation and verification
-> independent Completion Audit
```

This candidate grants no implementation, consumer, runtime, network, execution, paper, live, deployment, commit, push, or SSH authority.
