# Stage 1.5J-B Replacement Receipt Rebind And Rule 17 Profile Implementation Plan R1

> **For executor:** Execute task-by-task under `.agent/workflows/execute-approved-plan.md`. Use RED -> minimal implementation -> GREEN for every behavior change. This Plan is documentation only until independently reviewed and explicitly approved by the user.

**Goal:** Build the bounded local Stage 1.5J-B descriptive receipt producer/strict loader and its separate Rule 17 structural verifier, using only the verified J-A replacement root and without network, receipt-generation, consumer, or trading authority.

**Architecture:** The J-B core first validates immutable J-A identity, v2 closure evidence, the J-A public strict loader result, and frozen `335/131/125/120/11/281/280/1/5` projections before opening a package. It then streams local verified `aggTrades` ZIP members, creates the exact J-B receipt contract in temporary tests only, and independently strict-loads/re-renders it. A separate stdlib Governance CLI validates literal J-B profile constants and sealed artifact bytes only; it does not import the core or parse Markdown semantics.

**Tech Stack:** Python 3 standard library (`argparse`, `csv`, `decimal`, `fcntl`, `hashlib`, `json`, `pathlib`, `zipfile`), existing public J-A strict loader, pytest, Ruff, and `.agent/tools/anti_shortcut_scan.py`.

## 0. Authority And Baseline

### Approved Design chain

```text
J-B parent Design
  docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md
  ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b

J-B replacement-receipt Rebind Delta
  docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md
  0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c

J-B Receipt Schema Authority Delta
  docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md
  f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25

Approved Governance J-B Rule 17 Profile Delta
  docs/designs/2026-10-11-governance-stage1-5j-b-receipt-rule17-profile-design-delta_CN.md
  a692a888e1a9ae6b66379045fc031c6075eb72ff99fc30d140dd671caaa1153b
```

**Planning `BASE_SHA`:** `d15ca4e0da75a61553ca1d5983249d85a4512bb5`.

The prior unapproved, blocked Plan at `docs/plans/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-implementation-plan_CN.md` is an immutable historical record. R1 is the only future execution candidate after its own review and user approval.

### R1 closure-revision control ledger

This revision consumes only the Closure Audit findings `P0-01..P0-06` and `P1-01..P1-03` against pre-revision Plan SHA `380b0ecc3c0938f100fc87bc64ac38a342b45892f9ea3eb1f1542bbaaa56dd71`. The proof graph, trust boundary, four approved Design contracts, `BASE_SHA`, implementation/test whitelist, generated-artifact whitelist, and all no-network/no-receipt/no-consumer/no-trading boundaries remain frozen.

**Mutable Set:** this Plan's Task 0-6 text, invariant map evidence cells, verification commands, stop matrix, and this control ledger. **No-Touch Set:** §0 Design SHA/path bindings, §2 Allowed Change Scope, J-A root/core/verifier/test identities, the exact 12-key J-B authority set, nine Design-frozen config literal values, profile ownership split, receipt/consumer/network/trading prohibitions, and the old blocked Plan.

| Finding | Impact cone and deterministic closure criterion |
| --- | --- |
| `P0-01` | Task 0 parses only the exact two-line implementation-authorization grammar; Tasks 1/5/6 mutate/revalidate it before any source change, integration, or completion conclusion. |
| `P0-02` | Task 0 freezes module-level `configs/base.py` assignment AST/value ledger; Tasks 2/5/6 permit exactly the nine named additions and no pre-existing assignment drift. |
| `P0-03` | Tasks 1/2/3 require J-A pre/import/post SHA plus `__file__`/`__spec__.origin` proof and a shadow-import RED probe before ZIP access. |
| `P0-04` | Task 1 tests eight-line parser bytes only under `tmp_path`, separately proves the canonical locator path without materializing authority there, and Task 3 drives the same public publication branch only through a process-local private test seam; canonical authority remains absent. |
| `P0-05` | Tasks 1/2/3 derive the outcome-blind multi-child and required-date fixtures from the full strict-loaded J-A root and compare production output with an independent test oracle. |
| `P0-06` | Tasks 1/2/5 prove every resource cap below/equal/above threshold, pre-open rejection, bounded streaming and no raw-trade retention. |
| `P1-01` | Task 0 queries only existing topology; the new-symbol query follows RED stubs in Task 1; exactly one `.git/plan-execution/stage1_5j_b/<APPROVED_PLAN_SHA256>/` tree is allowed. |
| `P1-02` | Tasks 1/3 execute adjacent compound mutations and prove the earlier frozen precedence gate wins without invoking the later sensitive operation. |
| `P1-03` | Tasks 0/5/6 persist and independently reproduce the J-A v2 verifier command, source SHA, actual RC, transcript hash, and strict-loader result. |

The cross-blocker order is deliberately: implementation authority -> config/input identity -> J-A import/strict-load/projection -> ZIP/resource work -> J-B authorization/schema/tree. Every later-stage proof must stop if an earlier ledger row fails.

**Closure-confirmation delta:** only `P0-04` is revised after the first revision. A parser fixture under `tmp_path`, an exact canonical-locator/absence assertion, and a process-local private public-branch seam replace temporary materialization of valid authority at the canonical path. No other ledger row is reopened.

## Allowed Change Scope

Allowed implementation paths:
- `configs/base.py`
- `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py`
- `scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py`
- `scripts/governance/verify_stage1_5j_b_receipt_schema.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py`
- `tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py`

Allowed documentation paths:
- none

Allowed generated/runtime artifacts:
- `.git/plan-execution/stage1_5j_b/<APPROVED_PLAN_SHA256>/**`
- `tmp_path` test trees only; they must be removed by pytest and must never be created under `data/`

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`
  - compatibility evidence: public `load_verified_stage1_5j_a_historical_archive_coverage_root()` positive-loads the exact replacement root before every positive J-B integration path.
- `scripts/governance/verify_artifact_schema.py`
- `tests/scripts/governance/test_verify_artifact_schema.py`
  - compatibility evidence: Task 0 records their exact SHA-256 values `7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473` and `b0865f2eaeca091e45bee3724840c349c63a12778dc2a64e855dab2c36c81ff6`; Task 6 rechecks them unchanged.
- `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/**`
  - compatibility evidence: before/after sorted path, byte-count, and SHA-256 inventory equality.

Forbidden:
- Any mutation outside the allowed paths, including all Design/Plan files and every J-A root/code/test/verifier byte.
- Network access, network authorization, raw-data download, final J-B root under `data/`, receipt-generation authorization, J-B consumption, replay, signal, PnL/cost/fee/slippage/funding computation, paper/live trading, execution, deployment, SSH, commit, or push.
- Full-repository autofix/formatter, unscoped cleanup, fallback/alias/normalization, or a new generic registry/factory.
- Modifying the J-A Rule 17 verifier to add J-B support.

## 1. Invariant-To-Task Map

| Invariant | Owner task | Mechanical proof and fail-closed result |
| --- | --- | --- |
| `INV-JB-01` | 0, 1, 2, 3 | Exact J-A root/core/import-origin/strict-load identity gate before ZIP access; mismatch is upstream-authority STOP. |
| `INV-JB-02` | 1, 2, 3 | Canonical parent ledger keeps all 131 identities and explicit gaps; omission/duplicate is loader STOP. |
| `INV-JB-03` | 1, 2 | Required-date proof precedes horizon search; unavailable package stays explicit gap. |
| `INV-JB-04` | 1, 2 | Physical ordering, tie-breaks, Decimal arithmetic, windows and trade counts have pure RED/GREEN tests. |
| `INV-JB-05` | 1, 2 | Source article remains the independent unit; equal-child median and complete-only distributions are recomputed. |
| `INV-JB-06` | 1, 2, 3 | All J-A/J-B gap reasons are persisted as gaps, never negative Alpha evidence. |
| `INV-JB-07` | 3 | Producer and strict loader independently enforce receipt/tree/schema/reducer/render. |
| `INV-JB-08` | 3, 5 | Parent flock, fsync, rename, collision and no-resume tests cover every lifecycle state. |
| `INV-JB-09` | 0, 1, 5, 6 | No PIT/execution/PnL/Alpha claim appears in fixture, artifact, flags or completion evidence. |
| `INV-JB-10` | 1, 3, 5, 6 | Missing or malformed separately authorized receipt bundle fails before output creation; only an ephemeral test authority reaches the public publication branch. |
| `INV-JB-11` | 1, 2, 3, 5, 6 | Bounded stream/no raw retention and every resource-cap threshold are exercised before opening/writing. |
| `INV-JB-12` | 0, 1, 5 | Only full strict-loaded J-A root supplies positive cross-boundary input. |
| `INV-JB-RB-01` | 0, 1, 2 | Exact replacement run/root/four artifacts reject every alternate identity. |
| `INV-JB-RB-02` | 0, 1, 2, 5, 6 | Exact J-A v2 closure evidence/sidecar/profile/verifier/status and durable actual-RC gate reject one-fact drift. |
| `INV-JB-RB-03` | 1, 2 | All nine rebound projection literals are asserted before package access. |
| `INV-JB-RB-04` | 3 | Exact sixteen-key `j_a_input` is produced and independently loader-checked. |
| `INV-JB-RB-05` | 1, 2, 3 | The 131/281/843/393 identities and three horizons persist unchanged. |
| `INV-JB-RB-06` | 0, 5, 6 | Upstream/verifier passes do not create receipt, consumer, Alpha or trading authority. |
| `INV-JB-SC-01` | 3, 4 | `approved_j_b_design` binds only the Schema Authority Delta path/SHA. |
| `INV-JB-SC-02` | 2, 3, 4 | Exact source/anchor/horizon enums and conditional fields are validated twice. |
| `INV-JB-SC-03` | 2, 3, 4 | Unique 281/843/393 Cartesian identity sets and cross-row joins are required. |
| `INV-JB-SC-04` | 2, 3, 4 | Strict-loaded J-A states map only to their approved source relations. |
| `INV-JB-SC-05` | 2, 3, 4 | Count/scalar/ratio/ID-array grammar preserves the rebound projection. |
| `INV-JB-SC-06` | 0, 5, 6 | Schema work cannot grant implementation/runtime/trading permissions. |
| `INV-GSI-JB-01` | 0, 4 | Literal profile/version/authority tuple and external approved-Design binding are required. |
| `INV-GSI-JB-02` | 4 | New verifier has source/import isolation and reads only literal constants plus artifact bytes. |
| `INV-GSI-JB-03` | 3, 4 | Domain authority remains Schema Delta while profile SHA remains external audit evidence. |
| `INV-GSI-JB-04` | 4 | Exact key/enum/nullability/tree/Cartesian mutation matrix reaches the verifier gate. |
| `INV-GSI-JB-05` | 3, 4 | Verifier checks review bytes only; loader owns semantic render. |
| `INV-GSI-JB-06` | 4, 5, 6 | Synthetic verifier pass cannot substitute strict-loader or closure evidence. |
| `INV-GSI-JB-07` | 5, 6 | Actual verifier/loader RCs and exact future closure identity are recorded, not inferred. |
| `INV-GSI-JB-08` | 4, 5 | CLI tests distinguish exact `0`/`1`/`2` paths. |

## 2. Task 0: Freeze Authority, Inputs, Scope, And Graph Topology

**Files:** Create only `.git/plan-execution/stage1_5j_b/<APPROVED_PLAN_SHA256>/**` after every preflight check passes. Read all approved Designs, current Plan, `configs/base.py`, J-A root, public J-A core, and J-A verifier/test bytes.

1. Accept implementation authority only when the supplied UTF-8 bytes equal exactly these two ASCII lines, in this order, each terminated by one `LF` and with no `CR`, whitespace, blank/extra line, alias, case variant, path parameter, shell expansion, or other byte:

```text
IMPLEMENTATION_AUTHORIZED=true
APPROVED_PLAN_SHA256=<APPROVED_PLAN_SHA256>
```

`<APPROVED_PLAN_SHA256>` means the lower-case 64-hex SHA-256 freshly computed from this exact R1 Plan at authorization time; it is not a free-form caller value. The action literal distinguishes this authority from a Design/Plan review approval. Recompute the Plan SHA and require equality to line 2; require current `HEAD` equals `d15ca4e0da75a61553ca1d5983249d85a4512bb5` and `git diff --cached --quiet` returns `0`. Recompute all four Design SHA values in §0. Any mismatch is `STOP=approved_authority_mismatch`; do not rebaseline, infer authority, or create a bundle.
2. Capture `git status --short --untracked-files=all`, unstaged/index diff name lists, and path/type/byte-count/SHA ledgers for every pre-existing dirty/untracked path. The current untracked Design/old-Plan candidates are pre-existing user work, not Task-induced work. Parse the pre-edit `configs/base.py` with Python `ast` and persist its source SHA plus an ordered module-level assignment ledger of `(ordinal, target-name, ast.dump(value, include_attributes=False))`. Any later difference outside Allowed Change Scope is `STOP=stage1_5j_b_scope_or_authority_violation`; never revert or overwrite it.
3. Record recursive J-A replacement-root inventory and its manifest/summary/review/journal hashes. Record the J-A v2 verifier source SHA, then run the public strict loader and the existing J-A v2 verifier while capturing exact argv, stdout, stderr, actual process RC, and SHA-256 of the combined transcript. Persist `j_a_strict_loader_result` and `j_a_v2_verifier_source_sha256`, `j_a_v2_verifier_actual_rc`, `j_a_v2_verifier_argv`, and `j_a_v2_verifier_transcript_sha256` in Task 0 evidence:

```bash
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from pathlib import Path
from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import load_verified_stage1_5j_a_historical_archive_coverage_root
root = Path("data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z")
assert load_verified_stage1_5j_a_historical_archive_coverage_root(root)["run_id"] == root.name
PY
PYTHONPATH=src:. .venv/bin/python scripts/governance/verify_artifact_schema.py \
  --profile stage1_5j_a_receipt_v2 \
  --artifact-root data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
```

Expected: both RC `0`; otherwise `STOP=stage1_5j_b_upstream_governance_evidence_invalid`.
4. Run targeted topology discovery only for existing J-A loader/verifier symbols, J-A output paths, `j_a_input`, `approved_j_b_design`, existing config assignment names, and existing potential consumers. If Graphify is unavailable/stale, record that fact and use targeted `rg`. A verified consumer requiring code changes outside scope is `BLOCKED_SCOPE_DRIFT`. Do not query future J-B names before their Task 1 RED stubs exist.
5. Only after steps 1-4 pass, create canonical Task 0 authority records and SHA sidecars. `implementation_authorization.txt` is byte-for-byte the exact two-line grammar from step 1 and its sidecar binds that file. `execution_authority.json` is canonical JSON with exactly `allowed_implementation_paths`, `allowed_verification_paths`, `approved_designs`, `approved_plan`, `base_sha`, `j_a_input`, `j_a_no_touch`, `risk_live_trading_enabled`, and `schema_version`; its nested objects contain only the path/SHA/value pairs stated in this Plan. Its values are mechanically derived from frozen Plan bytes, not from approval-text path arguments. It binds exact Plan/Design paths+SHA, `BASE_SHA`, J-A root/four artifacts, J-A core SHA, J-A v2 closure evidence/verifier identity and Task 0 actual-RC transcript binding, J-A verifier/test No-Touch SHA, the pre-edit config AST ledger SHA, and this whitelist. All permission fields and `RISK_LIVE_TRADING_ENABLED` expectations are `false`; it contains no run ID authorization or receipt-generation authority.

**Verification:** sidecars use `<64-hex><two spaces><basename>\n`; malformed implementation-authority byte grammar, malformed/missing/extra bundle entry, changed baseline, changed immutable input, changed pre-edit config AST ledger, or non-false safety flag stops before source/test changes.

## 3. Task 1: RED Tests From Canonical Upstream And Isolated Verifier Mechanics

**Files:** Create the three allowed test files only.

1. Write domain RED tests whose positive path begins with the real J-A replacement root and public J-A strict loader. Assert exact root/v2 evidence/core identities and all nine J-A projection values `335/131/125/120/11/281/280/1/5`; no handcrafted upstream receipt, parent, child, authority packet, ZIP or CSV may stand in for this fixture. Before importing J-A, tests freeze the canonical source SHA; after import they require both `module.__file__` and `module.__spec__.origin` to equal the canonical resolved J-A core path, then recompute the same source SHA before calling the public loader. Add an isolated shadow-import RED probe that places a same-named temporary module earlier on `sys.path` in a test-only child interpreter; it must `STOP` before ZIP access.
2. Add one-fact upstream negative probes using disposable `/tmp` or `tmp_path` hard-link clones of regular J-A root members. Unlink before rewriting a mutated top-level file, preserve the source inventory, and rebuild only the manifest/sidecar required to reach the named admission gate. Cover old run ID, each top-level hash, v2 evidence/profile/version/verifier/status/sidecar identity, and each changed `120/11/280/1/5` literal. Assert the exact Rebind Delta `STOP` family before a ZIP is opened.
3. Derive `canonical_multi_child_complete_fixture_v1` only after strict-loading the full J-A root: choose the lexicographically first `coverage_complete` `source_article_id` with at least two in-scope children where each child has a valid anchor and three selected horizon rows. The selector may inspect only header/field validity, package dates, timestamps, and physical row order; pass it metadata stripped of price/return/extrema/ranking values and assert it cannot inspect outcome data. In separate test-side code that does not call any reducer/statistic helper under test, stream the selected canonical package members and independently calculate child results, equal-child parent median, nearest-rank percentiles, and concentration. Compare that oracle with production output. Also derive the lexicographically first qualifying required-date-gap child from the full root; only if none exists may a single declared mutation of the derived package-membership view produce that negative fixture.
4. Add pure local unit rows only for internal deterministic algorithms: CSV header, physical ordering across dates, equal-timestamp last physical row, finite positive `Decimal`, fixed-point output, anchor delay, required-package gap, missing-horizon gap, equal-child median, nearest-rank distribution, and zero absolute-return denominator. These rows must not be called positive cross-boundary fixtures or replace the canonical fixture/oracle in step 3.
5. Add resource RED matrix tests: ZIP compressed bytes, CSV uncompressed bytes, compression ratio, J-B root bytes, and free bytes each at `below`, `equal`, and `above` their frozen cap. For every ZIP rejection, spy on `ZipFile.open()` and assert it was never called; for root/free-space rejection, assert no staging/final publication happens. Add AST/static RED checks rejecting `ZipFile.read`, `extract`, `extractall`, whole-file CSV/raw-trade accumulation, and any non-`Decimal` price arithmetic.
6. Add receipt-generation-authorization parser RED tests using only explicitly labeled synthetic bytes/files beneath `tmp_path`, never the canonical Task 0 `.git/plan-execution/stage1_5j_b/<APPROVED_PLAN_SHA256>/` location. Starting from the exact eight-line parent grammar, mutate exactly one binding or grammar fact per case: Design SHA, Plan SHA, RUN_ID, Core SHA, CLI SHA, Config SHA, J-A manifest SHA, `NETWORK_ALLOWED=false`, line order, missing/extra line, whitespace/CR/LF, and sidecar. Separately assert that the production locator returns exactly the frozen canonical relative path, while asserting no authority file or sidecar exists there. No test fixture may be reported as or materialized as a real receipt-generation authorization.
7. Add execution-authority RED tests that positive-load only the canonical Task 0 on-disk bundle and reject malformed implementation-authority grammar, one missing entry, one unexpected entry, changed Plan/Design/baseline SHA, malformed sidecar, false-to-true permission, changed config AST ledger, and caller-supplied alternate bundle/root. Revalidate the same authorization before integration/completion; this suite must not create a receipt-generation authorization.
8. After RED stubs exist, run the deferred targeted `rg`/Graphify-or-`rg` supplementary topology query for `verify_execution_authority`, `load_verified_stage1_5j_b_historical_aggtrades_launch_response_root`, `run_stage1_5j_b_historical_aggtrades_launch_response`, and `verify_stage1_5j_b_receipt_schema`; record the result without changing Task 0 baseline. Any new consumer outside scope is `BLOCKED_SCOPE_DRIFT`.
9. Add adjacent compound-state precedence RED probes: malformed J-B receipt authority plus wrong J-A source must stop at authority before import; wrong J-A source plus wrong projection must stop at source identity before strict-load/projection; wrong projection plus malformed ZIP must stop at projection before `ZipFile.open`; wrong reducer/schema plus wrong manifest/tree must stop at schema/reducer before manifest/tree. Each asserts the frozen earlier `STOP` and proves the later sensitive operation was not invoked.
10. Add verifier RED tests using a clearly named synthetic sealed J-B tree. It proves only the new verifier mechanics, never J-B semantic replay or closure. Start by requiring unsupported-profile/absent-module failure; then declare a single mutation per test for every profile tuple literal, key family, 12 authority flags, `j_a_input` literal, `120/11/131` literal, enum/nullability branch, identity/cardinality/order relation, byte/manifest/tree/symlink condition, review byte-safety condition, and CLI RC class.

**Verification:** each new test is RED because its production module/script is absent. Any synthetic fixture labeled production-positive, any selector reading outcome data, any parser accepting malformed authority bytes, or any resource reject after `ZipFile.open()` is `BLOCKED_IMPLEMENTATION_DEFECT`.

## 4. Task 2: GREEN J-B Core Admission, Streaming Measurement, And Domain Schema

**Files:** Create `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py`; modify `configs/base.py`; modify the research test.

1. Add only these Design-frozen config constants, preserving every existing setting including `RISK_LIVE_TRADING_ENABLED=False`. The post-edit module-level assignment AST ledger must equal the Task 0 ledger for every pre-existing assignment `(ordinal,name,value-AST)` and contain exactly these nine new names exactly once, with these exact value ASTs and no other addition, deletion, reorder, duplicate, or mutation:

```python
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS = 300_000
EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS = (300_000, 3_600_000, 14_400_000)
EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS = 60_000
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES = 268_435_456
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES = 536_870_912
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO = 64
EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES = 65_536
EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES = 67_108_864
EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES = 1_073_741_824
```

2. Implement a zero-argument `verify_execution_authority()` that validates only the Task 0 canonical implementation bundle, including the exact two-line implementation authorization grammar and current Plan SHA before any source/test behavior proceeds. Implement the private J-A admission gate in the frozen order: containment/no symlink -> evidence/sidecar canonicality -> J-A v2 closure tuple -> pre-import canonical J-A core SHA -> import exact module/symbol -> `module.__file__` and `module.__spec__.origin` both equal canonical resolved `J_A_CORE_PATH` -> post-import canonical J-A core SHA -> exact public J-A strict loader -> four artifact hashes -> state/decision -> nine projections. Each import/source failure stops before ZIP access. It returns only verified immutable input identity plus strict-loaded data; no caller-selected project root, `.get` fallback, script import, verifier import, shadow-import tolerance, or network path reaches the reducer.
3. Implement bounded ZIP/CSV stream parsing and the exact §3 measurement/reducer rules. Before `ZipFile.open()`, reject ZIP compressed bytes, CSV uncompressed bytes, or compression ratio that exceed their frozen caps. Before staging/publication, reject root-byte or free-space breaches without truncation or output. Use `ZipFile.open`, bounded `TextIOWrapper`/CSV iteration, and `Decimal`; prohibit `ZipFile.read`, extraction, whole-file materialization, float arithmetic, raw trade retention, concurrent package reads, or network retry/download. A missing required package remains the Design's explicit evidence gap.
4. Implement the approved Schema Authority Delta exact source-state projection, anchor/nullability rows, child/parent/horizon enums, Cartesian identities, canonical scalar grammar, coverage/distribution relations, and all 131 parent gaps. Do not defer a schema rule to the Governance verifier.

**Verification:** Task 1 domain tests are GREEN; the Task 0 config AST proof permits only the nine exact additions; every upstream/import/resource rejection occurs before its forbidden later action; imported production modules contain no network/socket/subprocess/execution imports; no `data/external_signal_shadow/stage1_5j_b` root exists.

## 5. Task 3: TDD J-B Receipt, Strict Loader, Atomic Lifecycle, And CLI

**Files:** Modify the J-B core/research test; create the J-B CLI and CLI test.

1. Add RED receipt/loader tests that derive a temporary J-B tree only via the Task 2 production reducer over the full strict-loaded J-A root and compare its multi-child median/percentile/concentration projection with Task 1's independent canonical-fixture oracle. Assert exact 16-key `j_a_input`, Schema Authority `approved_j_b_design` path/SHA, 131/281/843/393 ledgers, all false authority/research flags, canonical JSON, manifest, and byte-for-byte domain Markdown re-render. Mutate exactly one persisted schema/rebind/tree fact and assert the public loader's specific `STOP`.
2. Implement `load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(root)` as an independent domain loader: classify the four lifecycle states; accept `final_only` only; validate receipt authority, repeat the complete Task 2 upstream J-A admission/import-origin sequence, recompute reducer/Cartesian relations, validate manifest/tree, and re-render `review_CN.md`. It must not call the Governance verifier or accept verifier success as domain proof.
3. Implement the public production entry `run_stage1_5j_b_historical_aggtrades_launch_response(run_id)`. In production it resolves only the canonical receipt-generation-authorization location, parses its exact eight-line grammar including `NETWORK_ALLOWED=false`, and rejects because the real authorization is absent. The parser/wiring test must not write a valid file or sidecar there. Instead it monkeypatches only private module-local authorization-reader input and output-parent helpers in the current pytest process: the reader returns the `tmp_path` synthetic bytes/sidecar and the output helper returns a `tmp_path` descendant. These are not CLI arguments, environment/config values, public function parameters, or caller-selectable project/output roots. The same public entry must then invoke the formal parent `flock(LOCK_EX)` through collision check, staging write/fsync, directory fsync, atomic rename, and parent fsync. Private seams may publish only below `tmp_path`; they must use production serializer/reducer and canonical J-A input, and must disappear when the monkeypatch scope ends.
4. Add CLI RED then GREEN tests. The CLI imports core constants and delegates only to the public entry; it rejects mismatched Design/Plan/run ID/unknown argument, has no direct ZIP/tree/authorization construction, and cannot make network calls. Its unauthorised invocation must fail closed with no J-B root.
5. Add failure-injection tests in temporary output parents: shared parent lock exclusion; pre-rename `staging_only`; post-rename `final_only`; restart rejects every non-absent state; no overwrite/resume/cleanup; and fsync ordering. Do not make production root selection injectable.

**Verification:** research and CLI suites are GREEN; parser mutation matrix, exact canonical-locator/absence assertion, and process-local authorized-public-branch test pass; all temporary roots and synthetic authorization bytes are removed; real J-A root inventory is unchanged; the canonical receipt-generation authorization file and sidecar were absent throughout the suite and remain absent afterward.

## 6. Task 4: TDD Independent J-B Rule 17 Verifier

**Files:** Create `scripts/governance/verify_stage1_5j_b_receipt_schema.py`; modify its dedicated test.

1. Keep the synthetic verifier fixture separate from Task 3's real J-A-derived temporary receipt. It may provide a minimal structurally valid J-B tree, but tests must never name it a domain-positive receipt or use it for loader/closure proof.
2. Implement literal constants only for `stage1_5j_b_receipt_v1`, profile version `1`, all §4 authority tuples, all §5 exact key sets/enums/nullability/Cartesian relations, and the three fixed horizons. The script is stdlib-only and must not import any `src`, J-B CLI/loader/tests, J-A verifier, `.git`, dynamic Design/Plan data, sockets, subprocesses, or network APIs.
3. Implement read-only tree/manifest/canonical JSON validation, exact receipt-internal `approved_j_b_design` binding to the Schema Authority Delta, J-A rebind/projection literals, rows/relations, and reducer pair. For `review_CN.md`, implement only membership/hash/UTF-8/LF/NUL checks; reject any implementation that parses headings, tables, statistics or claims.
4. Implement strict CLI return behavior: `0` conformant profile, `1` contract violation after valid invocation, `2` invalid arguments/unsupported profile/non-relative traversal root/unavailable root before profile validation. No normalization, fallback, write, repair, or shell-out.

**Verification:** Task 1 verifier matrix is GREEN. AST/import tests prove isolation; a receipt that passes synthetic verifier mechanics cannot satisfy J-B strict-loader/closure assertions.

## 7. Task 5: Integration, Cross-Boundary Gates, And Actual Process RCs

**Files:** Read all allowed source/tests; create only allowed Task 0 evidence records.

1. Revalidate the exact two-line implementation authorization, its sidecar, all Task 0 authority records, and the config AST baseline before integration. Re-run the exact J-A v2 verifier CLI from Task 0 and persist its source SHA, argv, stdout/stderr transcript hash, actual RC, and public strict-loader result. Then run canonical J-B integration: public J-A strict-load -> J-B admission -> production reducer/serializer to `tmp_path` -> J-B strict loader -> independent J-B verifier. If public publication wiring is exercised, it uses only the Task 3 process-local private seam; the canonical receipt-authority path must remain absent before, during, and after every integration process. Record before/after J-A inventory, J-B temporary root hashes, both J-B validator actual RCs, J-B verifier source SHA, profile/version, and Design/Plan authority chain. It proves descriptive schema/transport only, never market outcome, Alpha, execution or admission.

```bash
PYTHONPATH=src:. .venv/bin/python scripts/governance/verify_stage1_5j_b_receipt_schema.py \
  --profile stage1_5j_b_receipt_v1 \
  --artifact-root "$TMP_J_B_ROOT"
```

Expected: actual RC `0` only after the J-B strict loader has accepted the same temporary root. `$TMP_J_B_ROOT` is a test-owned `tmp_path` descendant, never a `data/` root.
2. Run domain semantic mutations that the Governance verifier intentionally does not own (trade arithmetic, physical row/tie-break, required-date computation, Markdown render); assert J-B strict loader rejects them. Run structural mutations that both paths must reject (authority, state/schema, tree/hash). Re-run the four adjacent compound-state precedence probes from Task 1 against the public producer/loader paths and record the earlier exact `STOP` plus proof that the later import/loader/ZIP/manifest operation was not invoked. Every mutation changes one declared fact except these explicitly enumerated two-fact precedence probes.
3. Run bounded checks without `|| true`:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py
ruff check configs/base.py \
  src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py \
  scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py \
  scripts/governance/verify_stage1_5j_b_receipt_schema.py \
  tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py
PYTHONPATH=src:. .venv/bin/python .agent/tools/anti_shortcut_scan.py --base-sha d15ca4e0da75a61553ca1d5983249d85a4512bb5
scanner_rc=$?
printf 'scanner_rc=%s\n' "$scanner_rc"
test "$scanner_rc" -eq 0
git diff --check
git diff --cached --check
```

4. Recompute all Task 0 immutable ledgers. Parse `configs/base.py` again and require every pre-existing module-level assignment `(ordinal,name,value-AST)` is byte-for-byte equivalent at the AST-value level, exactly the nine approved J-B assignments are new and each appears once with its frozen value, and no other assignment was added/removed/renamed/reordered/mutated. Assert `RISK_LIVE_TRADING_ENABLED is False`, every 12 J-B authority flag is false, no socket/network/execution import/call exists, no final J-B root exists, the canonical receipt-generation authorization file and sidecar were never materialized, no scope path is unexpected, and index remains clean.

**Verification:** all actual RC values are `0`; the J-A v2 verifier transcript is durable evidence rather than an expected-RC narrative; nonzero scanner/ruff/test, authorization/config/root mutation, index mutation or unexpected path is `STOP=stage1_5j_b_scope_or_authority_violation`.

## 8. Task 6: Independent Review And Completion Audit

1. Independent reviewer receives exact approved Design/Plan hashes, the exact implementation-authorization bytes/sidecar and all three revalidation results, Task 0 authority bundle, current diff/index/untracked ledger, Graphify-or-rg topology record, canonical outcome-blind fixture provenance plus independent oracle, resource threshold/pre-open evidence, receipt-authorization parser bytes, canonical-locator/absence proof, process-local public-wiring proof, and proof that no process materialized canonical receipt authority, precedence-pair results, one-fact mutation results, J-A v2 source SHA/argv/transcript/actual-RC and strict-loader result, both J-B validator transcripts/RCs, J-A before/after inventory, config AST additive-only proof, scope proof, and scanner actual RC. Open P0/P1 is `STOP=stage1_5j_b_code_review_open_findings`.
2. Only after review closure, a fresh completion auditor follows `.agent/skills/audit-plan-completion/SKILL.md` and independently repeats the exact authorization grammar/sidecar, approval/baseline checks, config AST additive-only proof, J-A import-origin plus pre/post SHA gate, J-A v2 CLI with durable actual-RC record, production/loader/verifier paths, positive fixture lineage/independent oracle, false-GREEN and precedence-pair mutations, resource pre-open gates, atomic recovery, canonical receipt-authorization absence plus process-local-only wiring evidence, no-touch bytes, scope/index, actual scanner RC, and all safety flags.
3. Strongest allowed completion result is `COMPLETE_PRE_RECEIPT_AUTHORIZATION`. It does not authorize commit, push, deployment, SSH, network, receipt-generation, J-B consumption, replay, signal, Alpha claim, paper/live trading, or execution.

## 9. Stop And Escalation Matrix

| Condition | Route |
| --- | --- |
| Design/Plan/approval/baseline/immutable-input mismatch | `BLOCKED_SPEC_DRIFT`; do not rebaseline. |
| Needed source/test/document/runtime path is outside whitelist | `BLOCKED_SCOPE_DRIFT`; preserve evidence and request a new Plan. |
| Frozen contract violated inside allowed paths | `BLOCKED_IMPLEMENTATION_DEFECT`; repair only through a new RED case. |
| J-A root mutation, network use, final J-B root, receipt-generation authorization, or permission true | Immediate safety/scope stop; no compensating fallback. |
| Canonical receipt-generation authorization file or sidecar appears at any time, including during tests | Immediate safety/scope stop; retain evidence, remove no files, and do not treat a process-local seam as authority. |
| Existing J-A verifier/test SHA differs from Task 0 literal | `STOP=stage1_5j_b_j_a_no_touch_identity_mismatch`; do not modify or emulate J-A verifier. |
| J-B Governance verifier missing/nonzero/identity mismatch | `STOP=governance_j_b_v1_receipt_identity_evidence_mismatch`; do not substitute core/loader result. |

## 10. Explicit Non-Authorization

R1 is not implementation authority. Even a future approved implementation may only perform bounded local code/test/evidence work. It cannot authorize network, J-B receipt generation, J-B downstream consumption, Alpha/economic/execution claim, replay, signal, paper/live trading, execution, commit, push, deployment, or SSH.
