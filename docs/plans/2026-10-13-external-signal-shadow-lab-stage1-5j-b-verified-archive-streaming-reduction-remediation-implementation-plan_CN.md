# Stage 1.5J-B Verified Archive Streaming Reduction Remediation Implementation Plan

> **For executor:** 按 `.agent/workflows/execute-approved-plan.md`、`test-driven-development` 和本 Plan 的 Task 顺序执行；不得跳过 Task 0，且不得以测试通过替代跨边界审计。

**Goal:** 在不改变既有 `stage1_5j_b_receipt_v2` 持久化契约、Rule 17 v2 verifier 或任何交易权限的条件下，使 J-B producer 与 strict loader 对已准入的 J-A 原始 ZIP 归档进行确定性流式归约与回放校验。

**Architecture:** 仅扩展既有 J-B core 中的归档访问、CSV 流式解析和确定性 reducer；producer 使用该 shared TCB 生成现有三制品结构，strict loader 对同一已准入 J-A raw bytes 重放并逐项比较。测试中的独立 semantic oracle 只读取 canonical J-A raw fixture，不导入或调用 production kernel；既有 Rule 17 v2 verifier 保持独立且只作为持久化结构边界。

**Tech Stack:** Python 3、stdlib `zipfile` / `csv` / `decimal` / `pathlib` / `fcntl`、pytest、ruff、现有 J-A public loader、现有 Rule 17 v2 CLI。

---

## 0. Closure Revision Control, Authority, And Preconditions

### 0.1 Closure-revision packet

- **Pre-revision candidate SHA-256:** `216e4d6c50060172dc1c384994c28aa8a205c96bcb490b618795af9487c00d9b`
- **Review mode:** Plan Closure Audit; proof graph, trust boundary and scope are frozen.
- **Previous open set:** `P0-01..P0-08`, `P1-01..P1-02`.
- **Mutable revision sections:** Section 0 authority/template, Task 0 baseline gate, Task 1 fixture/oracle/RED gates, Task 2 raw/resource/network/legacy requirements, Task 4 durability matrix, Task 5 final scope gate, and Section 9 routing.
- **No-touch revision sections:** Goal, architecture, allowed-path whitelist, Design bindings, v2 persistent identity, all `INV-JB-RR-*` meanings, research boundary, permission denials, and every path outside this Plan document.
- **Impact cone:** immutable authority bytes -> Task-0 comparison gate -> canonical J-A root and copied negative fixtures -> producer/loader shared TCB -> oracle/v2/lifecycle tests -> final HEAD/scope/permission evidence -> independent review and Completion Audit.

This revision may make a stated gate mechanical, but must not create a new profile, authority flag, consumer, lifecycle owner, persistent field, or runtime permission. Any required change beyond the existing core/test/evidence whitelist is `STOP=material_scope_expansion_required`.

### 0.2 Authority and preconditions

- **Approved remediation Design:** `docs/designs/2026-10-13-external-signal-shadow-lab-stage1-5j-b-verified-archive-streaming-reduction-remediation-design-delta_CN.md`
- **Approved remediation Design SHA-256:** `7e305093027de1d7c9f3d3221aaa237def317c4033e4bed3e837697fe94c0a9d`
- **Parent J-B Design:** `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md` (`ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b`)
- **J-B Rebind Delta:** `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md` (`0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c`)
- **J-B Schema Authority Delta:** `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md` (`f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25`)
- **Existing Compatibility Domain Design:** `docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md` (`66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f`)
- **Existing Rule 17 v2 Design:** `docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md` (`8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454`)
- **Existing v2 persistent identity:** `stage1_5j_b_receipt_v2`; it remains the only J-B Rule 17 profile used by this Plan.
- **Frozen J-A replacement root top-level hashes:** `manifest.json=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf`, `summary.json=722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b`, `review_CN.md=1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152`, `request_journal.jsonl=b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa`.
- **Execution authorization requirement:** implementation starts only after an exact user Plan-implementation approval sentence is supplied. Task 0 recomputes this Plan's SHA-256 and requires equality with that sentence. Otherwise `STOP=approved_authority_mismatch`.
- **Current status:** draft Plan only. It grants no implementation, receipt-generation, network, consumer, replay, alpha, paper-trading, live-trading, execution, deployment, commit, push, SSH, or runtime authority.

The only legal implementation-approval packet is exactly two LF-terminated lines, with no leading/trailing whitespace or extra text:

```text
我批准实施 Plan：docs/plans/2026-10-13-external-signal-shadow-lab-stage1-5j-b-verified-archive-streaming-reduction-remediation-implementation-plan_CN.md（SHA-256: <APPROVED_REMEDIATION_PLAN_SHA256>）。
允许 implementation；不允许 commit、push、deployment、SSH、network、receipt generation、J-B consumer、replay、signal、paper trading、live trading、execution 或 runtime action。
```

`<APPROVED_REMEDIATION_PLAN_SHA256>` is supplied only by the user after Plan review. The executor must neither synthesize this packet nor accept the earlier two-line compatibility-Plan grammar. Missing, altered, reordered, or extra bytes are `STOP=implementation_authorization_grammar_invalid` or `STOP=approved_authority_mismatch`.

The remediation Design already freezes the research interpretation. This Plan implements only data-conformity mechanics. It must not introduce entry/exit rules, expectancy, PnL, alpha evaluation, a J-C stage, a consumer, or any trade signal.

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py`

Allowed documentation paths:
- `none`

Allowed generated/runtime artifacts:
- `.git/plan-execution/stage1_5j_b/<APPROVED_REMEDIATION_PLAN_SHA256>/**` — Task 0-7 ledgers, command transcripts, source hashes, reviewer request/receipt, and audit inputs only; no receipt-generation authorization and no `receipt_closure_evidence.json`.
- pytest-managed `tmp_path` / OS temporary directories — test-only; must be removed by pytest and may never be promoted to `data/`.

Affected but unchanged:
- `configs/base.py`
  - compatibility evidence: SHA-256 remains `473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc`; `RISK_LIVE_TRADING_ENABLED is False`.
- `configs/stage1_5j_b_historical_aggtrades_launch_response.py`
  - compatibility evidence: source SHA and exact nine literal offline constants are recorded and unchanged; core import/AST regression passes.
- `scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py`
  - compatibility evidence: public CLI delegation and missing/invalid authorization regression tests pass without source edits.
- `scripts/governance/verify_stage1_5j_b_receipt_schema.py`
- `tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py`
  - compatibility evidence: exact v2 source/test SHA ledger, `stage1_5j_b_receipt_v2` regression suite, and an isolated subprocess invocation of the exact verifier bytes with actual `RC=0` on the canonical temporary J-B artifact.
- `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`
- `scripts/governance/verify_artifact_schema.py`
- `tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py`
  - compatibility evidence: J-A source/test/verifier SHA ledger, unchanged public loader success, and actual `stage1_5j_a_receipt_v2` CLI `RC=0` against the exact replacement root.
- `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/**`
  - read-only canonical raw fixture only; no copy, write, extraction, sidecar regeneration, or network fallback.
- `data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261013T000000Z/**`
- `data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261013T040000Z/**`
  - immutable legacy diagnostic roots; neither may be an input, output, authorization target, or positive fixture.
- all approved Design/Plan bytes and existing J-B closure evidence
  - compatibility evidence: byte-identical before/after ledger.

Forbidden:
- Any mutation outside the allowed paths, including Design/Plan edits, J-A code/tests/root/raw bytes, configs, CLI, Rule 17 verifier/tests, old J-B roots, and existing closure evidence.
- Receipt-generation authorization creation or modification, production `data/external_signal_shadow/stage1_5j_b/**` publication, consumer invocation, network access, archive download, SSH, deployment, commit, push, paper/live trading, execution, replay/alpha promotion, or authority-flag change.
- `ZipFile.read`, `extract`, `extractall`, raw-trade persistence, a generic parser/config registry, a factory/plugin/alias, full-repository autofix, `git clean`, reset/checkout rollback, or a runtime import of a verifier script into `src/`.
- Changing any v2 key set, cardinality, enum, conditional nullability, canonical JSON rule, sealed-tree rule, authority-packet grammar, verifier boundary, or adding a v3 profile.

## 1. Invariant-To-Task Matrix

| Design invariant | Production / boundary owner | Task and mechanical proof | Fail-closed result |
|---|---|---|---|
| `INV-JB-RR-01` | J-A admission + J-B raw opener | Tasks 0, 2, 4; actual J-A loader/v2 CLI, logical package identity, ZIP and `.CHECKSUM` mutation | named J-A/J-B admission `STOP`; no ZIP open |
| `INV-JB-RR-02` | producer + loader reducer | Tasks 1-4; a canonical complete child becomes non-null only from raw stream; all gaps carry one re-playable reason | `STOP=stage1_5j_b_*` for projection/reducer contradiction |
| `INV-JB-RR-03` | shared raw parser/reducer | Tasks 1-3; header/time/Decimal/tie/date/horizon tests plus independent oracle | parser/reducer `STOP`, never synthetic gap |
| `INV-JB-RR-04` | producer streaming/publish path | Tasks 1, 2, 4, 5; validator-call proof, ZIP/CSV/ratio/root/free-space boundaries, one-package streaming AST/runtime guards, durability matrix | resource/stream/durability/collision `STOP`, no successful partial final root |
| `INV-JB-RR-05` | producer, loader, test-local oracle | Tasks 2-4; raw replay comparison and oracle source SHA evidence | mismatch/raw-open `STOP` |
| `INV-JB-RR-06` | legacy-admissibility boundary | Tasks 0, 1, 2 and 6; legacy hash/count equality plus exact two-root rejection while retaining diagnostic reads | `STOP=stage1_5j_b_legacy_root_not_admissible` |
| `INV-JB-RR-07` | core authorization and publisher | Tasks 0, 2, 5; update core's Plan SHA only to exact later approval and retain exact eight-key grammar | authorization/collision/staging `STOP` |
| `INV-JB-RR-08` | external audit boundary | Tasks 4, 6, 7; loader raw replay + independent oracle + unchanged v2 actual RC | no COMPLETE evidence from any single result |
| `INV-JB-RR-09` | config + serialized summary | Tasks 0 and 6; literal false authority flags and live switch regression | `STOP=stage1_5j_b_authority_flags_invalid` |
| `INV-JB-RR-10` | scope / routing | every task; scope/index/network scan | `BLOCKED_SCOPE_DRIFT` |

## 2. Task 0: Freeze Authority, Defect Baseline, And No-Touch State

**Invariants:** `INV-JB-RR-01`, `INV-JB-RR-06` through `INV-JB-RR-10`.

**Files:**
- Create only: `.git/plan-execution/stage1_5j_b/<APPROVED_REMEDIATION_PLAN_SHA256>/baseline/**`
- Read only: every authority, no-touch path, source, test, fixture, and legacy root named above.

1. Require the literal two-line implementation-approval packet in Section 0.2. Recompute this Plan's SHA-256, require its path/SHA and every denied permission clause to match, save the received bytes plus a sidecar in the Task-0 ledger, and stop before any mutation on mismatch: `STOP=approved_authority_mismatch` or `STOP=implementation_authorization_grammar_invalid`. The executor must not construct an equivalent approval packet.
2. Record `BASE_SHA=$(git rev-parse HEAD)`, `git status --short --untracked-files=all`, index status, tracked diff, and a path/type/size/SHA ledger for all pre-existing dirty or untracked paths. The currently pre-existing remediation Design must be attributed as user work, preserved byte-for-byte, and never claimed as Task output.
3. Compare, do not merely record, executable authority bytes before any RED test. Require exact disk equality to: pre-remediation J-B core `245ae39793d4f4ccfa972b5898aa9b0f53c34353facf21568fa7ebc9e020c2f4`; unchanged J-B CLI `e2edcacc6de247ef344b4fb576a4dd5124f7e293e32660f8b9cad5ae86f9f74c`; J-A core `250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18`; J-A verifier `7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473`; and J-B v2 verifier `442c527fb7f49d78eff4e13fd68e5fabfff12ba1e74089cd5e5133977cde90f1`.
4. Validate the canonical J-A closure-evidence file and sidecar at `.git/plan-execution/governance_artifact_schema/ba362f2480c7872d39eede9254744d6e99216aa73134777658f9f81f05ba7881/evidence/v2_receipt_closure_evidence.json` (`c0810b95dc94c740dbc41d55ce01d51d1bd7a09e382b292e156d2522d621e68b`), then require its profile/path/expected+observed RC/source-SHA tuple to equal the J-A values above. Likewise validate `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/ec5fbc3beeafd47ec42cdf12481751f41424fe3351a6c14845ebc0e5d5a8a319/evidence/receipt_closure_evidence.json` (`64db0ea5d36acce057e392c36b28d8fad213f1176f4659b85634496364cbca0f`) and require its v2 profile/verifier path/source SHA to equal the J-B values above. Record J-A/J-B verifier-test source SHA values only after these equality checks; because those test files are No-Touch, final bytes must equal the Task-0 ledger. Any mismatch is `BLOCKED_SPEC_DRIFT`; do not rebaseline.
5. Require the stage config's nine-key AST/literal contract and `configs/base.py` SHA equality. Any mismatch is `BLOCKED_SPEC_DRIFT`; do not rebaseline.
6. Record the two legacy J-B roots as **non-completion evidence** exactly:
   - `20261013T000000Z`: manifest `36df19595b503a5e4f385a8fc6a834dc0b0c41c5c85e6b4641dea96606dad96a`, summary `a61e75f55ca7bfaba930ca14e8002e8c46298cd35636f0d742685681f8196373`, review `9a926c51c72f9b797cf006cc5c6d3a645e4f64b96c220de50b52946682311393`.
   - `20261013T040000Z`: manifest `cdcf5dd23ea139e2d6fc7274c065d2c20c3f7df9e277cbf215460d06045b2974`, summary `eaf4130057f50af50aa9e40a958baab9e465f5ae646a605f8393a78b33aecca9`, review `45720b24591446183f10949e58d2399722461de1db9eb297028348e2ee4df5bb`.
   - For both roots record `child_horizon_complete=0/281` and `parent_horizon_complete=0/131` at each of `300000`, `3600000`, `14400000`; record source evidence from the pre-mutation core's all-gap producer block. Any difference is `BLOCKED_SCOPE_DRIFT` or `BLOCKED_SPEC_DRIFT`, never completion evidence.
7. Run, capture stdout/stderr and actual process RC for both immutable J-A gates before code/test mutation:
   ```bash
   PYTHONPATH=src:. .venv/bin/python - <<'PY'
from pathlib import Path
from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import load_verified_stage1_5j_a_historical_archive_coverage_root
root = Path("data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z")
load_verified_stage1_5j_a_historical_archive_coverage_root(root)
PY
   PYTHONPATH=src:. .venv/bin/python scripts/governance/verify_artifact_schema.py \
     --profile stage1_5j_a_receipt_v2 \
     --artifact-root data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
   ```
   Expected: both `RC=0`. A nonzero result is `BLOCKED_SPEC_DRIFT`; do not access a ZIP.
8. Run targeted topology discovery for the exact public helpers `admit_upstream_j_a_root`, `produce_stage1_5j_b_historical_aggtrades_launch_response`, `load_verified_stage1_5j_b_historical_aggtrades_launch_response_root`, and `run_stage1_5j_b_historical_aggtrades_launch_response`. `graphify` is currently unavailable; record that fact and use `rg` plus direct source inspection. Any verified affected consumer outside this Plan's whitelist is `BLOCKED_SCOPE_DRIFT`.
9. Confirm no production J-B root or receipt-generation authorization is created/changed by this Plan. Pre-existing legacy authorization/evidence is read-only provenance, not executable authority for tests.

**Verification:** all Task-0 ledger files have sidecars; both J-A gates have actual `RC=0`; `git diff --cached --quiet` has `RC=0`.

## 3. Task 1: RED Tests And Independent Oracle

**Invariants:** `INV-JB-RR-01` through `INV-JB-RR-05`, `INV-JB-RR-08`.

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py`
- Do not modify: production core until every required new remediation-behavior RED node identified below has failed for the current all-gap implementation with its expected reason. Existing regression and negative fail-closed tests may remain green.

1. Add one test-local semantic oracle that first calls the exact J-A public loader, resolves only the admitted package identities from that returned data, and independently streams the real ZIP bytes. The Class-A selection is deterministic: choose the lexicographically first J-A-complete `(source_article_id, symbol)` whose authenticated required package set yields one anchor and all three horizon selections; persist that identity in evidence. It must not import or call the production raw parser/reducer, use precomputed J-B output, write a fixture, or handcraft J-A provenance.
2. Make oracle independence mechanical before it is used as positive evidence: parse the oracle function body with `ast` and reject references/calls to the J-B module or every named production-TCB helper introduced by Task 2. In a separate test, monkeypatch every production parser/reducer entry to an immediate raising sentinel; the oracle must still calculate the same canonical result. Persist both gate results and the oracle source SHA in Task-5 evidence.
3. The oracle must independently calculate: physical CSV order, earliest post-launch anchor and tie, required UTC package dates, three horizon selections and latest same-time tie, closed-interval count/min/max, positive finite `Decimal` parsing and half-even eight-decimal serialization, parent median, distribution and concentration fields.
4. Write the canonical Class-A test first: real J-A root -> J-B producer to `tmp_path` -> J-B loader -> unchanged v2 verifier. Patch all network exits to immediate failure for this producer+loader run. Require at least one J-A-complete child/horizon and one parent horizon to be non-null, and exact equality to the independent oracle. Current all-gap implementation must fail this test.
5. Add an AST/import-boundary test that rejects `socket`, `http`, `urllib`, `requests`, `aiohttp`, websocket transports, or equivalent network-client imports/references in the J-B core. The positive integration in item 4 must patch socket/HTTP connection and URL-open exits to immediate failure, proving the canonical local raw path neither imports nor reaches a network fallback.
6. Add Class-B negative tests using a physically copied, isolated temporary tree with exactly one declared mutation of root/hash/checksum/raw bytes. A mutable fixture must never use a hard link, reflink with write-through behavior, symlink, or bind mount to any J-A artifact; hard links are permitted only for explicitly read-only files that the test proves it will never write. Require rejection at J-A admission before J-B parser/reducer access; never use this class as a positive fixture.
7. Add Class-C pure-seam tests with synthetic temporary ZIP/CSV only for header, UTF-8, timestamp order, nonpositive/nonfinite Decimal, required date, anchor/horizon tie, and canonical Decimal serialization. Test the existing `validate_zip_archive_package()` at reduced injected bounds for compressed ZIP bytes, CSV uncompressed bytes, and compression ratio; then prove the canonical producer/loader calls that validator before raw open by replacing it with an immediate failure. Add publisher boundary tests with injected root-size and filesystem-free-space values at both sides of the frozen limits. Each boundary must yield a named STOP with no final root. Assert the seam has no J-A authority and cannot call producer/loader positive path.
8. Add Class-D single-mutation persisted-artifact tests for child outcome, manifest, and rendered review projection. Require the J-B loader and/or unchanged v2 verifier to reject at a named gate.
9. Add a forced raw-open failure test for a canonical complete child. Patch only the raw stream seam to raise; producer and loader must stop with `stage1_5j_b_raw_reduction_not_executed` (or the more specific raw-open STOP), never emit `missing_horizon_trade`.
10. Add exact legacy-admissibility tests for both `20261013T000000Z` and `20261013T040000Z`: neither root/RUN_ID may enter Class-A producer, strict-loader verified-reduction admission, public runner, or remediation closure-positive evidence; each must reach `STOP=stage1_5j_b_legacy_root_not_admissible`. The tests may still run read-only diagnostic/v2 structural inspection separately, because that diagnostic use remains allowed by the Design.

**RED commands:**
```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
  -k 'canonical_raw_oracle or raw_reduction or stream_parser or raw_open'
```
**Expected before Task 2:** nonzero RC caused by every new remediation-behavior node (`canonical raw reduction`, `raw replay`, `forced raw-open`, `network hard-fail`, and resource/reducer wiring), with each expected node ID and reason recorded. Existing Class-B/C/D negative guards that already fail closed may and should remain green; do not weaken them merely to manufacture RED.

## 4. Task 2: Implement The Minimal Shared Streaming Reduction Kernel

**Invariants:** `INV-JB-RR-01` through `INV-JB-RR-04`, `INV-JB-RR-07`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py`
- Test: the Task-1 test file only.

1. Extend the existing J-A admission result handling, without changing J-A code, so the core consumes only authenticated logical package records whose root, path, regular-file/no-symlink status, manifest ZIP hash and `.CHECKSUM` are already bound by the admitted J-A result. Preserve the fixed J-A tuple check, core identity, four top-level hashes and `335/131/125/120/11/281/280/1/5` projection check before any ZIP access.
2. Reuse the existing `validate_zip_archive_package()` before every `ZipFile.open()` in both producer and loader; do not duplicate or weaken its `EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES=268435456`, `EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES=536870912`, and `EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO=64` checks. A false validation result is a structural named STOP before open, never a gap.
3. Implement a private, single-use streaming parser/reducer in the existing core. For each logical package, use one `ZipFile.open()` text stream with `EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES=65536` bounded reads; reject `read`, `extract`, `extractall`, raw trade persistence and concurrent package processing. Validate the expected header, UTF-8, positive finite price/quantity, nondecreasing transaction time, and original `agg_trade_id` order.
4. Keep only reducer state needed for the earliest valid launch anchor, the three target windows, inclusive count/min/max, and latest selected row at a timestamp. Do not add a registry, factory, generic archive interface, cache, or configurable alternate parser.
5. Enforce publisher resource ownership before staging: the temporary root must remain within `EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES=67108864` and the output filesystem must report at least `EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES=1073741824` free bytes. Test-injected boundary failure returns a named STOP before final publication; do not change the stage config values.
6. Apply the Design state matrix exactly: parent J-A gap inherits without raw access; a J-A-complete child missing reachable launch/post-launch data is an upstream projection schema contradiction; missing package, delay above `EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS`, or absent horizon trade maps only to its declared gap state; ZIP/checksum/header/encoding/timestamp/numeric/parser faults are structural STOPs.
7. Explicitly reject the two frozen legacy J-B RUN_IDs/roots from producer, public runner, strict-loader verified-reduction admission, and remediation closure-positive paths with `STOP=stage1_5j_b_legacy_root_not_admissible`. This does not prohibit direct read-only diagnostic inspection or the existing v2 structural verifier against their immutable historical bytes.
8. Quantize every persisted Decimal to `0.00000001` with `ROUND_HALF_EVEN`; derive complete parent rows only if every matching in-scope child is complete at that horizon. Any failed child makes the parent outcome null and preserves each failed-child reason; never median a remainder.
9. Replace only the existing all-gap producer projection with reducer-derived `child_rows`, `child_horizon_rows`, `parent_horizon_rows`, coverage counts and rendered review source. Keep existing v2 key sets, enum literals, nullability combinations, canonical JSON, atomic staging/rename path, and authority flags unchanged.
10. Update the core's implementation-approval parser and `PLAN_SHA` literal only from the exact Task-0 approved packet in Section 0.2. Keep the separate eight-key receipt-generation authorization grammar, key order, denial of `NETWORK_ALLOWED`, and test-only seam behavior unchanged. This Plan never creates an authorization file or uses one outside `tmp_path`.
11. Production code validates the recorded upstream verifier/evidence tuple, including the frozen J-A top-level hashes above, but does not execute a verifier process: Task 0, Task 5, Completion Audit and Receipt Closure Audit separately run the exact J-A verifier CLI and record its actual RC. The core must not import, call, shell out to, or treat `scripts/governance/verify_artifact_schema.py` or the J-B v2 verifier as a runtime fallback; it must also contain no network transport/fallback path.

**GREEN commands:**
```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
  -k 'canonical_raw_oracle or raw_reduction or stream_parser or raw_open'
```
**Expected:** `RC=0`; the class-A artifact has real non-null reducer output, while all declared malformed/raw-open cases fail closed.

## 5. Task 3: Make The Strict Loader Replay Raw Bytes

**Invariants:** `INV-JB-RR-02`, `INV-JB-RR-03`, `INV-JB-RR-05`, `INV-JB-RR-08`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py`

1. After existing sealed-tree, manifest, schema, authority-packet and J-A admission checks, make `load_verified_stage1_5j_b_historical_aggtrades_launch_response_root()` reopen the same admitted raw packages and run the Task-2 shared parser/reducer.
2. Compare every persisted child, child-horizon, parent-horizon, coverage-count, distribution/concentration and `review_CN.md` projection against the replay result. It must not trust persisted outcomes, producer memory, a producer cache, the Rule 17 verifier, or a legacy root.
3. Name each comparison failure with a stable J-B `STOP` that identifies the projection class; retain stronger preexisting sealed-tree/manifest gates where they occur earlier.
4. Add an internally self-consistent forged-receipt test: recompute manifest hashes after changing source state/outcomes coherently, then prove v2 may remain structurally conformant while the raw-replay loader fails. This proves the loader's raw boundary is not replaced by v2 structure validation.

**Verification:** run the focused loader/oracle/mutation tests. Expected `RC=0`; every forged artifact reaches the documented fail-closed owner.

## 6. Task 4: Preserve Publication And Exercise Lifecycle Boundaries

**Invariants:** `INV-JB-RR-04`, `INV-JB-RR-06`, `INV-JB-RR-07`, `INV-JB-RR-10`.

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py`
- Modify core only if a RED lifecycle test proves the existing atomic publisher violates the Design; no CLI change is authorized.

1. Re-run and extend the existing producer lifecycle tests against `tmp_path` only: absent root, staging-only collision (including a stale staging directory from a different PID), final-only collision, final-plus-staging collision, and two processes requesting the same RUN_ID. Require nonblocking parent `flock`, detection of every same-RUN staging reuse, per-file fsync, staging-directory fsync, atomic rename, parent-directory fsync and lock release.
2. Add one injected-failure test for each durability point: file `fsync`, staging-directory `fsync`, rename, and parent-directory `fsync`. For each node, record and assert the exact state matrix: producer returns/raises a named STOP and never reports success; before rename there is no final root and any retained staging root is non-consumable; rename failure leaves no final root and same RUN is blocked by stale-staging collision; parent-directory-fsync failure returns no success, leaves any post-rename final-only state in collision/quarantine rather than completion evidence, and the same RUN cannot be reused. Do not swallow these exceptions or turn them into a successful receipt.
3. Test the public runner only through its existing process-local `_TEST_RECEIPT_AUTH_FILE` and `_TEST_OUTPUT_ROOT` seam. The valid temporary authorization bytes must not be materialized at a canonical `.git/plan-execution/.../receipt_generation_authorization.txt` path, and no CLI argument may expose output/project root selection to production callers.
4. The public-wiring test must produce a `tmp_path` root from the actual admitted J-A root, strict-load it, and leave no `data/external_signal_shadow/stage1_5j_b` root or canonical authorization mutation. A second invocation with the same run id must fail closed.
5. Retain AST/runtime assertions that forbid whole-file ZIP extraction, raw persistence and network fallback. Do not add process-wide test capability, test-only production flags, or cleanup that removes user data.

**Verification:** focused lifecycle/public-wiring tests return `RC=0`; a deliberately precreated staging/final target has named STOP and no overwrite.

## 7. Task 5: Full Boundary Regression And Evidence Bundle

**Invariants:** all `INV-JB-RR-*`.

**Files:**
- Create only: `.git/plan-execution/stage1_5j_b/<APPROVED_REMEDIATION_PLAN_SHA256>/evidence/**`
- Read only: all affected-but-unchanged files.

1. Capture a class-A transcript with the full chain: actual J-A public loader -> actual J-A `stage1_5j_a_receipt_v2` verifier CLI -> J-B producer to temporary root -> J-B strict raw-replay loader -> existing J-B v2 verifier. For the last step, invoke the verifier CLI in an isolated temporary project containing byte-identical verifier bytes and the temporary artifact at its expected relative path; record original verifier SHA, copied-byte SHA equality, stdout/stderr and actual `RC=0`.
2. Persist the independent oracle PASS, canonical J-A root/run identity, logical package identity, oracle test source SHA, core SHA, CLI SHA, stage config path/SHA, this Design path/SHA, exact approved Plan SHA, J-B v2 Design/profile/verifier tuple, and the three temporary artifact hashes. This is implementation evidence only, not `receipt_closure_evidence.json` and not a receipt-generation authorization.
3. Run the complete tests and record actual results:
   ```bash
   PYTHONPATH=src:. .venv/bin/python -m pytest -q \
     tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
     tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py \
     tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py
   PYTHONPATH=src:. .venv/bin/python -m pytest -q \
     tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
     tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
   ```
   Expected: `RC=0`; any failure stops the Plan at its owning invariant.
4. Run quality, safety and scope gates, recording actual exit codes, especially scanner RC:
   ```bash
   .venv/bin/ruff check \
     src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py \
     tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
     scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py \
     tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py \
     scripts/governance/verify_stage1_5j_b_receipt_schema.py \
     tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py
   BASE_SHA=<Task-0 BASE_SHA>
   python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
   scanner_rc=$?
   printf 'scanner_rc=%s\n' "$scanner_rc"
   test "$scanner_rc" -eq 0
   git diff --check
   git diff --cached --check
   git diff --cached --quiet
   PYTHONPATH=src:. .venv/bin/python -c 'from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False'
   ```
5. Enforce the no-commit gate before any completion claim:
   ```bash
   test "$(git rev-parse HEAD)" = "$BASE_SHA"
   git diff --name-status "$BASE_SHA"
   git diff --cached --name-status "$BASE_SHA"
   git status --short --untracked-files=all
   ```
   Persist the union of tracked/staged/untracked paths and compare it to the Task-0 ownership ledger. Require an empty index; only the core, domain-test and Plan-evidence paths may differ; all affected-but-unchanged and user-preexisting paths retain exact bytes; all 12 J-B authority flags remain literal `False`; no network/socket activity, no real receipt root, and no canonical authorization was created. A HEAD mismatch is `STOP=commit_forbidden_head_changed`, not a clean baseline.

## 8. Task 6: Independent Review And Completion-Audit Handoff

**Invariants:** `INV-JB-RR-05`, `INV-JB-RR-08` through `INV-JB-RR-10`.

1. Request an independent code review only after Task 5 is green. Provide exact diff, Task-0 no-touch ledger, Class A-D results, raw-open regression, lifecycle matrix, source hashes, J-A verifier actual transcript, J-B v2 CLI transcript, semantic oracle source SHA/PASS, scanner actual RC and scope/index proof.
2. A reviewer finding that needs a non-whitelisted change is `BLOCKED_SCOPE_DRIFT`; a mismatch with immutable J-A semantics or existing v2 persistent contract is `BLOCKED_SPEC_DRIFT`. Do not repair by weakening a test, copying an authority packet, aliasing schema fields, or adding a fallback.
3. Only a review with no open P0/P1 may hand off to a fresh independent Completion Auditor using `.agent/skills/audit-plan-completion/SKILL.md`. The auditor must recompute all bytes and actual process RCs; executor reports are input, not proof.
4. Completion of this Plan does not authorize receipt generation. A future, separately approved, fresh single-run authorization and a fresh root would still require J-B loader raw replay, independent semantic oracle, existing v2 verifier and Receipt Closure Audit.

## 9. Rule-12 Routing And Stop Matrix

| Condition | Required route |
|---|---|
| approved Plan/Design/authority bytes, Task-0 baseline, J-A tuple/hash/projection, config SHA, legacy root ledger, or J-A verifier `RC=0` does not match | `STOP=approved_authority_mismatch` or `BLOCKED_SPEC_DRIFT`; do not mutate or rebaseline |
| any frozen core/verifier/evidence-sidecar byte mismatches its approved tuple before RED | `BLOCKED_SPEC_DRIFT`; do not record the drifted byte as a new baseline |
| a real J-A complete child cannot resolve only its admitted ZIP/`.CHECKSUM` package or parser behavior differs from the frozen contract | `BLOCKED_SPEC_DRIFT` with failed invariant, upstream source evidence, contradiction proof and proposed Design Delta |
| an existing core API was misunderstood, while required repair stays inside the two whitelisted source/test files and preserves the Design | `BLOCKED_IMPLEMENTATION_DEFECT`; repair through RED -> minimal fix -> GREEN |
| correct repair requires J-A/config/CLI/v2 verifier/test/Design/Plan/root/authorization changes or a new dependency | `BLOCKED_SCOPE_DRIFT`; stop before editing that path |
| fixture is missing and a handwritten CSV/hash/authority would be needed for Class-A positivity | `BLOCKED_SPEC_DRIFT`; no substitute fixture |
| a Class-B mutation would write through a hard link, symlink, bind mount, or non-isolated copy to the sealed J-A root | stop before mutation; recreate a physical isolated copy or `BLOCKED_SCOPE_DRIFT` if this cannot be done safely |
| ZIP/checksum/header/encoding/timestamp/Decimal/raw-open failure occurs | named `STOP=stage1_5j_b_*`; no `missing_horizon_trade` downgrade and no final artifact |
| validator/resource/root-free-space boundary fails, staging/final collision occurs, lock acquisition fails, or an injected durability node fails | named publication/resource `STOP`; preserve state evidence, do not overwrite/clean, and never report success |
| a test or production branch imports/reaches a network transport | named network-boundary test failure; stop as `BLOCKED_SCOPE_DRIFT` unless the source is demonstrably a local implementation defect inside the two whitelisted paths |
| scanner nonzero, HEAD differs from `BASE_SHA`, scope/index proof fails, authority flag is true, live switch is true, or a test writes a production J-B data root | stop; a HEAD mismatch is `STOP=commit_forbidden_head_changed`; otherwise classify as `BLOCKED_SCOPE_DRIFT` unless an approved invariant identifies a narrower source defect |

## 10. Completion Boundary

A future completion auditor may mark the implementation **COMPLETE** only if Tasks 0-6 have exact evidence and no open P0/P1. That verdict is limited to offline descriptive J-B archive-reduction implementation. It is not authorization for a production receipt, a consumer, a signal, alpha claim, replay claim, paper/live trading, execution, deployment, commit, or push.
