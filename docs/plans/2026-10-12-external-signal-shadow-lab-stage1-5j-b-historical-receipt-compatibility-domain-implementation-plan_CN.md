# Stage 1.5J-B Historical Receipt Compatibility And Rule 17 v2 Implementation Plan

> **For executor:** 仅在独立 Plan Review 为 `RECOMMEND_APPROVE`、用户外部批准本 Plan、且两份绑定 Design 的外部批准字节都在执行 handoff 中提供后，才可按 `.agent/workflows/execute-approved-plan.md` 逐 Task 执行。所有行为改动遵循 RED -> minimal implementation -> GREEN。

**状态:** `draft_for_independent_review`  
**日期:** 2026-10-12  
**Planning BASE_SHA:** `d15ca4e0da75a61553ca1d5983249d85a4512bb5`  
**替代的 blocked Plan:** `docs/plans/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-implementation-plan-r1_CN.md` (`ce82883e3e7e17fb8b97c73116ee7f7d7b6a3fee01813013afe74ef252ebde42`)  
**Plan identity:** `APPROVED_PLAN_SHA256` 只可由未来用户对本候选 exact bytes 的实施批准提供；本 Plan 不自引用、不生成或推断该值。

**绑定 Domain Design:** `docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md`  
**绑定 Domain Design SHA-256:** `66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f`  
**绑定 Governance v2 Design:** `docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md`  
**绑定 Governance v2 Design SHA-256:** `8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454`

**Goal:** 在不改变 J-A 的前提下，恢复 J-A `configs/base.py` strict-loader compatibility，将九个 J-B 离线 measurement/resource constants 绑定到唯一的 stage-local source，完成 J-B domain producer/strict-loader 与独立 `stage1_5j_b_receipt_v2` Rule 17 verifier 的本地、无 receipt 的实施证明。

**Completion boundary:** 最强允许的实施审计结论是 `COMPLETE_PRE_RECEIPT_AUTHORIZATION`。它仅说明实现和临时测试根的机械验证完成；不创建或授予 receipt-generation authorization、J-B final root、closure evidence、consumer、network、Alpha、replay、signal、paper/live trading、execution、commit、push 或 deployment 权限。

---

## 0. Revision Control, Authority, And Scope

### 0.1 Closure-revision control packet

- **Pre-revision candidate SHA:** `74044e962b7bcefdba3dfa7b258f920fc0a42329afdc7a015c0a77db871fca23`.
- **Review mode:** Plan Closure Confirmation; previous OPEN finding `P1-02`, status target `CLOSED`.
- **Mutable Set:** this unapproved Plan's authority packet, scope, invariant matrix, Task 0-6 sequence, verification commands, and stop matrix.
- **No-Touch Set:** all Design bytes and frozen SHA bindings; J-A source/root/authority/v1/v2 verifier/tests/evidence; J-B v1 verifier/profile behavior; J-B parent/Rebind/Schema contracts; J-B measurement/reducer semantics; all twelve J-B false authority flags; `RISK_LIVE_TRADING_ENABLED=False`; network, receipt, consumer, trading, and deployment boundaries.
- **Impact cone:** external approval -> Task 0 ledger -> policy/base restoration -> J-A public loader plus J-A Rule 17 v2 -> canonical J-A-derived J-B temporary root -> domain loader plus J-B Rule 17 v2 -> code review CLOSED -> Completion Audit.

### 0.2 Frozen authority chain

| Authority | SHA-256 | Execution rule |
| --- | --- | --- |
| J-B parent Design | `ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b` | immutable inherited contract |
| J-B Rebind Delta | `0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c` | immutable inherited contract |
| J-B Schema Authority Delta | `f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25` | immutable inherited contract |
| Compatibility Domain Delta | `66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f` | require external Design approval bytes |
| Governance Rule 17 v2 Delta | `8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454` | require external Design approval bytes |

The Domain Design owns `AGENTS.md`, `configs/base.py`, the stage-local config, J-B core/CLI and their direct tests. The Governance v2 Design owns only `scripts/governance/verify_stage1_5j_b_receipt_schema.py`, its direct test, and its dedicated evidence tree. This Plan joins these already-separated authorities without letting either implementation import or replace the other.

### 0.3 External authority input contract

The executor must receive three immutable UTF-8/LF byte sequences from the user execution handoff, never manufacture their authority semantics:

1. Domain Design approval exactly binding the Domain path and `66f70...feed3f`.
2. Governance v2 Design approval exactly binding the Governance v2 path and `8bdfe...1454`.
3. Plan implementation approval exactly of this form after the final candidate SHA is known:

```text
我批准实施 Plan：docs/plans/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-domain-implementation-plan_CN.md（SHA-256: <APPROVED_PLAN_SHA256>）。
允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。
```

Task 0 parses each received input against its literal path/SHA and permission clause, recomputes the named bytes, then copies the received bytes unchanged with a SHA sidecar into evidence. It must not synthesize `IMPLEMENTATION_AUTHORIZED=true`, replace the user sentence with an equivalent local format, accept a caller-selected source, or create any authority record before these checks. Missing/malformed/unverifiable input is `STOP=implementation_authorization_missing` or `STOP=approved_authority_mismatch`.

### 0.4 Allowed change scope

**Allowed implementation paths:**

- `AGENTS.md`: exactly the three Domain-Design-frozen Historical Receipt Compatibility Exception substitutions.
- `configs/base.py`: delete only the proven legacy R1 comment/blank/nine-assignment block.
- `configs/stage1_5j_b_historical_aggtrades_launch_response.py`: create exactly the frozen 565-byte, nine-assignment module.
- `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py`.
- `scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py`.
- `scripts/governance/verify_stage1_5j_b_receipt_schema.py`: add only the v2 branch; v1 profile literals plus acceptance/rejection/RC behavior must remain equivalent under the Task 0 frozen v1 behavioral oracle.

**Allowed verification paths:**

- `tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py`.
- `tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py`.
- `tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py`: v2 direct tests only; v1 expectations remain unchanged.

**Allowed generated evidence only:**

- `.git/plan-execution/stage1_5j_b/<APPROVED_PLAN_SHA256>/**`.
- `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/<APPROVED_PLAN_SHA256>/**`.
- pytest-owned `tmp_path` trees.

The v2 canonical positive closure artifact `receipt_closure_evidence.json` is auditor-owned and is forbidden in both evidence trees during this Plan. A synthetic or temporary J-B root is never a receipt-generation authorization, final receipt, or closure artifact.

**Affected but unchanged:** J-A core/root/authority/v1/v2 verifier/tests/closure evidence; J-B v1 verifier/profile; all Design/Plan bytes; old blocked R1 Plan; all non-J-B user work. J-A verifier source/test SHA must remain respectively `7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473` and `b0865f2eaeca091e45bee3724840c349c63a12778dc2a64e855dab2c36c81ff6`.

**Forbidden:** any J-A or v1 mutation; generic registry/factory/plugin/config selector/override/alias/fallback; YAML/TOML; network/subprocess adapter; receipt-generation authorization; `data/external_signal_shadow/stage1_5j_b/**`; consumer/replay/signal/Alpha/trading work; commit/push/deployment/SSH; `git clean`, `git reset`, `git checkout`, or bulk formatter.

---

## 1. Complete Invariant-To-Task Matrix

Fixture terms are fixed for every row:

- **F-JA:** the actual `20261010T163500Z` J-A replacement root, first accepted by unchanged public J-A strict loader and J-A `stage1_5j_a_receipt_v2` verifier.
- **F-JB:** a `tmp_path` J-B sealed tree produced only by canonical J-B producer from F-JA, then strict-loaded by J-B domain loader.
- **F-V2:** a clearly labeled synthetic J-B sealed tree for Rule 17 v2 structural mechanics only; it is never domain-positive or closure evidence.

| Invariant | Owner / Tasks | Canonical positive fixture | Single-fact negative | Final gate |
| --- | --- | --- | --- | --- |
| `INV-JB-01` | domain core, T1/2/3/5 | F-JA exact root/source/import/loader | root, source SHA, origin, or artifact hash | J-B loader + audit |
| `INV-JB-02` | domain reducer, T2/3/5 | F-JB 131 parents/all gaps | omit one parent/child/gap | loader replay |
| `INV-JB-03` | domain reducer, T2/3/5 | F-JB required-date ledger | remove one verified package date | explicit gap state |
| `INV-JB-04` | domain reducer, T2/3/5 | F-JB order/Decimal/windows/counts | one tie/order/Decimal mutation | loader replay |
| `INV-JB-05` | domain reducer, T2/3/5 | F-JB source unit/median | one source or median mutation | loader replay |
| `INV-JB-06` | domain reducer, T2/3/5 | F-JB gap taxonomy | one gap -> negative-outcome rewrite | loader STOP |
| `INV-JB-07` | producer + loader, T3/5 | F-JB canonical tree/re-render | one schema/tree/review/manifest mutation | loader STOP |
| `INV-JB-08` | public entry/lifecycle, T2/3/5 | process-local public branch to `tmp_path` | one lifecycle state/collision/fsync failure | `final_only` only |
| `INV-JB-09` | domain producer, T2/5 | F-JB descriptive flags | one Alpha/cost/execution flag | authority false gate |
| `INV-JB-10` | auth parser/public entry, T2/3/5 | synthetic parser plus absent canonical path | one auth grammar field or canonical file appearance | no real authority/root |
| `INV-JB-11` | stream parser, T2/5 | F-JB bounded stream | one cap at above threshold | pre-open/pre-stage STOP |
| `INV-JB-12` | fixture selector, T2/5 | F-JA -> F-JB only | handcrafted/cropped positive input | provenance gate |
| `INV-JB-RB-01` | upstream admission, T0/1/2/5 | F-JA exact RUN_ID/four hashes | one root identity/hash | upstream authority STOP |
| `INV-JB-RB-02` | upstream closure gate, T0/1/5/6 | F-JA J-A v2 tuple and CLI RC 0 | one evidence/profile/verifier/sidecar field | governance-evidence STOP |
| `INV-JB-RB-03` | upstream projection, T1/2/5 | F-JA `335/131/125/120/11/281/280/1/5` | one projection literal | projection STOP |
| `INV-JB-RB-04` | producer + loader, T3/5 | F-JB exact `j_a_input` | one key/value mutation | loader STOP |
| `INV-JB-RB-05` | reducer + loader, T2/3/5 | F-JB `131/281/843/393` identities | one missing/duplicate ledger member | loader STOP |
| `INV-JB-RB-06` | authority boundary, T0/3/5/6 | F-JB validators RC 0 with flags false | one permission true | safety STOP |
| `INV-JB-SC-01` | producer/loader/v2, T3/4/5 | F-JB latest Domain path/SHA | rebind to Governance profile/old Delta | domain + v2 reject |
| `INV-JB-SC-02` | producer/loader/v2, T3/4/5 | F-JB all enum/nullability branches | one enum or conditional null | named schema STOP |
| `INV-JB-SC-03` | producer/loader/v2, T3/4/5 | F-JB unique `281/843/393` sets | one duplicate/missing/cross-row mismatch | identity gate |
| `INV-JB-SC-04` | producer/loader/v2, T2/3/5 | F-JA-derived source-state projection | one arbitrary state | projection gate |
| `INV-JB-SC-05` | producer/loader/v2, T3/4/5 | F-JB counts/scalars/ID arrays | one scalar/map/array relation | relation gate |
| `INV-JB-SC-06` | authority boundary, T0/5/6 | F-JB with all flags false | one permission true | safety gate |
| `INV-JB-HRC-01` | compatibility preflight, T0/1/5 | restored base SHA then F-JA loader | one base byte | pre-ZIP STOP |
| `INV-JB-HRC-02` | upstream admission, T1/2/5 | F-JA loader before any ZIP | loader failure | no ZIP open |
| `INV-JB-HRC-03` | config verifier, T2/5 | exact 565-byte stage module | source/import/origin/value/preload mutation | config STOP |
| `INV-JB-HRC-04` | producer/loader/parser, T3/5 | F-JB stage config pair | old base path, alias, or stale SHA | domain STOP |
| `INV-JB-HRC-05` | v2 verifier, T0/4/5/6 | F-JB + v2 RC 0 | v1-as-v2/profile tuple mutation | wrong-profile STOP |
| `INV-JB-HRC-06` | AGENTS/config policy, T1/2/5 | exact three substitutions/false flags | extra policy edit or forbidden config content | policy STOP |
| `INV-JB-HRC-07` | config verifier/core, T2/5 | all nine boundary uses | duplicate/base fallback/unused key | config STOP |
| `INV-JB-HRC-08` | no-touch ledger, T0/5/6 | before/after J-A inventory | one J-A byte change | no-touch STOP |
| `INV-GSI-JB-V2-01` | v2 CLI, T0/4/5 | F-V2 exact literal tuple | one profile/design tuple literal | RC 1/2 gate |
| `INV-GSI-JB-V2-02` | v2 verifier, T4/5 | F-V2 stdlib-only artifact validation | one forbidden import/read | isolation gate |
| `INV-GSI-JB-V2-03` | v2 verifier, T4/5 | F-V2/F-JB latest Domain pair | old Schema Authority pair | RC 1 |
| `INV-GSI-JB-V2-04` | v2 verifier, T4/5 | F-V2/F-JB stage config pair | path or SHA mutation | RC 1 |
| `INV-GSI-JB-V2-05` | closure boundary, T4/5/6 | F-V2 explicit v2 invocation | present v1 result as v2 | wrong-profile STOP |
| `INV-GSI-JB-V2-06` | integration/audit, T5/6 | F-JB domain RC 0 + v2 RC 0, false flags | either RC or one flag mutation | no closure/authority promotion |

---

## 2. Task 0: Freeze External Inputs, Baseline, And No-Touch Evidence

**Files:** Write only the two allowed evidence trees after all corresponding preflight checks pass. Do not change source, tests, policy, or config in this Task.

1. Receive and validate the three external byte inputs in §0.3. Recompute both Design SHA values and final Plan SHA. Persist the received bytes byte-for-byte, their SHA sidecars, source label `received_external_handoff`, and an authority-record hash. No generated `IMPLEMENTATION_AUTHORIZED=true` surrogate is permitted.
2. Require `HEAD=d15ca4e0da75a61553ca1d5983249d85a4512bb5` and clean index. Capture `git status --short --untracked-files=all`, staged/unstaged name lists, tracked dirty patch bytes, and type/size/SHA for every pre-existing dirty or untracked path.
3. Persist an attribution ledger: every pre-existing non-whitelisted path must be byte-identical at Task 5/6; every pre-existing allowed path must have an explicit baseline-to-final Task attribution. Do not overwrite, clean, normalize, or rebaseline user work.
3a. Record blocked R1 Plan SHA `ce82883e3e7e17fb8b97c73116ee7f7d7b6a3fee01813013afe74ef252ebde42` and run the focused pre-remediation core suite before any mutation. Persist its exact argv, node IDs, stdout/stderr, actual RC, and transcript SHA as **non-completion evidence**. Require actual RC `1` and exactly `14 passed, 3 failed`; each of the three failures must be the known J-A `STOP=stage1_5j_a_authority_packet_invalid:disk_sha_mismatch:audited_config` compatibility blocker. A different count, node, or terminal failure is `BLOCKED_SPEC_DRIFT`; do not normalize, reinterpret, or continue from a different baseline.
4. Parse the current `configs/base.py` AST and persist ordered assignments. Prove its only delta versus `HEAD:configs/base.py` is exactly the legacy R1 comment/blank/nine-assignment block. Require `SHA256(HEAD:configs/base.py)=473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc`. Any extra current config diff is `BLOCKED_SCOPE_DRIFT`.
5. Freeze `AGENTS.md` preimage SHA `32c14c73071a6b15d66bad794d652357d4eca90eaa7e2ae3e35310f55abe49cf`, the exact three source occurrence counts, and required postimage SHA `06bb1e5c86a26b2ea3a76296ca11e8749092fff6168a4c6c2d921ed921eef620`.
6. Record recursive J-A replacement-root inventory and four top-level hashes: `manifest.json=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf`, `summary.json=722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b`, `review_CN.md=1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152`, `request_journal.jsonl=b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa`. Also validate the immutable J-A v2 closure evidence file and sidecar at `.git/plan-execution/governance_artifact_schema/ba362f2480c7872d39eede9254744d6e99216aa73134777658f9f81f05ba7881/evidence/v2_receipt_closure_evidence.json`: SHA `c0810b95dc94c740dbc41d55ce01d51d1bd7a09e382b292e156d2522d621e68b`, profile `stage1_5j_a_receipt_v2`, version `2`, verifier path/SHA, root/four hashes, observed loader/verifier RC `0`, status `receipt_closure_audited_positive`, and positive flag `true`.
7. Record J-A v2 verifier/test SHA values stated in §0.4. Run only its read-only CLI and retain exact argv, stdout/stderr, actual RC, and transcript SHA:

```bash
PYTHONPATH=src:. .venv/bin/python scripts/governance/verify_artifact_schema.py \
  --profile stage1_5j_a_receipt_v2 \
  --artifact-root data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
```

It must return `0`. Do not invoke the J-A public loader until Task 1 restores the base config bytes.
8. Before changing the J-B verifier, freeze its v1 behavioral oracle in the dedicated governance evidence tree: current v1 verifier/test SHA, sorted `pytest --collect-only` node IDs, actual focused pytest RC/stdout/stderr transcript SHA, and a v1 CLI result vector covering conformant, one contract violation, and unsupported-profile RC classes using its existing test fixtures. Task 4 must preserve every captured v1 node ID, outcome, RC, and diagnostic class.
9. Record unavailable `graphify` evidence, then use scoped `rg` to map current J-A loader/verifier symbols, J-B authority/parser/consumer paths and the nine constants. An actual unwhitelisted owner is `BLOCKED_SCOPE_DRIFT`.

---

## 3. Task 1: Policy-And-Compatibility Mutation Gate Before Tests

**Files:** `configs/base.py`, `AGENTS.md`, and Task 0 evidence only. This Task deliberately precedes test/source edits because the Domain Design requires the policy gate first.

1. Revalidate Task 0 external authority, ledger and exact config diff. Narrow-patch only the proven legacy R1 block; do not use history checkout/reset. Require `SHA256(configs/base.py)=473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc`.
2. Run the unchanged public J-A loader against the actual replacement root. It must succeed before ZIP access, J-B reducer, staging, J-B loader or J-B verifier invocation. Re-run the exact J-A v2 command from Task 0 and require actual RC `0`; record both transcripts and hashes.
3. Apply exactly the three Domain-Design substitutions to `AGENTS.md`, no other byte. Require postimage SHA `06bb1e5c86a26b2ea3a76296ca11e8749092fff6168a4c6c2d921ed921eef620` and prove every J-B authority flag plus `RISK_LIVE_TRADING_ENABLED` is literal `False`.

Any failure is before-test `STOP=stage1_5j_b_j_a_compatibility_base_config_mismatch`, `STOP=stage1_5j_b_config_exception_policy_violation`, or the public J-A STOP. It must not be bypassed by a synthetic J-A fixture.

---

## 4. Task 2: RED Tests From Canonical Upstream And Isolated v2 Mechanics

**Files:** only the three allowed direct test paths.

1. Derive every domain-positive test from F-JA. Assert exact J-A source origin/pre/post SHA, public loader result, immutable J-A closure evidence tuple/sidecar, J-A v2 CLI RC, four top-level hashes, and all nine projection values before any package is opened. Cover one-fact root/hash/closure-evidence/projection/source-origin mutations with the inherited Rebind STOP families.
2. Derive the outcome-blind multi-child fixture and independent test oracle only from F-JA. Cover required-date gap, anchor delay, missing horizon, physical tie order, Decimal serialization, equal-child median, percentiles/concentration, all gap retention, and the `131/281/843/393` identity relations.
3. Add exact conditional-nullability, enum, source-state, coverage/distribution and `j_a_input` one-fact mutations through the domain schema gate. A synthetic root, copied J-A authority packet, or arbitrary parent/child dictionary cannot be a positive fixture.
4. Add RED tests for the private fixed-path stage-config verifier: absent/symlink/nonregular/pre-SHA/import-origin/preloaded-module/public-name/value/post-SHA mutation; all nine boundary uses; base fallback/duplicate literal/unused key; exact stage-config authority pair; and AGENTS pre/post byte proof.
5. Test the receipt-generation parser only using synthetic `tmp_path` bytes. Separately prove the production canonical locator value and its absence. Test public-branch wiring only with private process-local reader/output seams that provide synthetic bytes and `tmp_path`; no valid canonical receipt authority is written.
6. Add execution-authority RED tests proving `verify_execution_authority()` accepts only the copied external handoff bytes and sidecar from Task 0, binds their SHA to its authority record, and rejects a legacy `IMPLEMENTATION_AUTHORIZED=true` surrogate, a locally generated equivalent, a missing source label, or any altered Design/Plan/permission clause. The test process may clone a bundle below `tmp_path`, but no test may create authority semantics at the canonical path.
7. Add all resource `below/equal/above` tests, pre-open `ZipFile.open()` proof, four lifecycle states, crash/fsync/collision/no-resume tests, and ordered two-fact precedence probes.
8. Add v2 verifier RED tests using only F-V2: literal profile/design/config tuples, unsupported profile RC `2`, v1-as-v2 rejection, import isolation, exact structural/schema/tree/key/enum/nullability/cardinality/authority mutations, and proof it never opens workspace config bytes or imports J-B source.

A RED test that already passes without the required production behavior is `BLOCKED_IMPLEMENTATION_DEFECT`.

---

## 5. Task 3: GREEN Domain Config, Producer, Loader, And CLI

**Files:** stage config, J-B core/CLI, and their direct domain/CLI tests.

1. Create `configs/stage1_5j_b_historical_aggtrades_launch_response.py` as the exact 565-byte, ASCII, LF-only nine-line Domain-Design source with SHA `771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4`; no import/comment/helper/extra public name is allowed.
2. Implement one private fixed-path config verifier: canonical resolved path -> reject symlink/nonregular/byte/prehash -> invalidate caches/evict only exact module -> import -> exact `__file__`/`__spec__.origin` -> exact public names/types/values -> posthash -> return verified values. Retain only base `RISK_LIVE_TRADING_ENABLED=False`; do not add a registry, selector, dynamic override, alias, or fallback.
3. Apply every verified value exactly once to its frozen boundary: anchor delay, horizons, horizon lookback, ZIP compressed/CSV uncompressed/compression caps, stream chunk, root bytes and free space. Preserve `Decimal`, bounded `ZipFile.open()`, no raw retention and all parent/Rebind/Schema reducer semantics.
4. Replace the self-issued `IMPLEMENTATION_AUTHORIZED=true` parser with a verifier for the Task 0 copied external handoff bytes, their sidecar, declared external source label, Plan SHA, both Design approval bindings, and all denied permissions. It must not construct approval text, accept a locally generated equivalent, or create an authority record; public entry revalidates this bundle before every domain operation.
5. Require base SHA -> public J-A loader -> immutable J-A closure tuple -> J-A v2 verifier success -> verified stage config before any J-B package/reducer/staging path. Implement producer/strict loader authority pairs using the latest Domain Design and stage-config path/SHA; independently reject old `configs/base.py`, stale Domain, alias, changed config or changed value.
6. Implement/retain canonical J-B temporary serialization and strict-loader replay: exact `j_a_input`, source-state projection, `281/843/393` identities, exact schema/reducer/render/tree and `final_only` lifecycle. Domain loader never imports or delegates to Rule 17 verifier.
7. Production CLI only parses/delegates. It remains unauthorized when the real receipt authorization is absent. The test-only private seams cannot be public parameters, CLI options, environment variables, config, or persistent authority.

---

## 6. Task 4: GREEN Independent J-B Rule 17 v2 Verifier

**Files:** only `scripts/governance/verify_stage1_5j_b_receipt_schema.py` and its direct test, plus the dedicated governance evidence tree.

1. Preserve every frozen v1 literal and every Task 0 v1 behavioral-oracle node/outcome/RC/diagnostic class. Add only literal `stage1_5j_b_receipt_v2` profile/version `2` constants defined by the approved Governance v2 Design, including the latest Domain path/SHA and stage-config path/SHA.
2. The v2 verifier is stdlib-only and reads only its literal constants and artifact-root bytes. It cannot import J-B source/CLI/loader/tests, inspect `.git`, source/parse Design bytes dynamically, read workspace config, use socket/subprocess/network, auto-detect/fallback/alias profile, write or repair artifacts.
3. Implement exact v2 envelope, sealed-tree, canonical JSON, inherited schema/relation and persisted authority checks. A valid v2 contract violation returns RC `1`; unsupported/malformed invocation returns RC `2`. The verifier may validate F-V2 and F-JB structural bytes but cannot supply domain replay or closure evidence.
4. Before and after v2 implementation, recheck the J-A verifier/test SHA and run the exact J-A v2 CLI from Task 0 with an actual RC/transcript record; the J-A source remains no-touch. Record final J-B verifier source SHA, test SHA and actual CLI transcripts. Do not create `receipt_closure_evidence.json`, sidecar, final J-B root, or receipt authorization.

---

## 7. Task 5: Integration, Provenance Equality, And Actual RCs

1. Revalidate all external inputs, Task 0 baseline, J-A inventory/verifier SHA, non-whitelisted dirty/untracked byte ledger, policy/base hashes, stage-config source/import identity and false flags.
2. Run the exact J-A v2 verifier command and public J-A loader again, record their actual RC/stdout/stderr/transcript SHA, then execute the sole positive integration chain:

```text
F-JA public strict loader + J-A v2 RC 0
-> verified stage config
-> canonical J-B producer to tmp_path
-> J-B domain strict loader RC 0
-> J-B v2 verifier CLI RC 0 on the same tmp_path root
```

The temp root is not closure evidence. Neither validator's success authorizes publication or any permission.
3. Run each one-fact domain and v2 mutation at its named gate, then the explicit two-fact precedence probes. Demonstrate J-B semantic mutations are caught by the domain loader even where the v2 verifier intentionally owns only structure.
4. Run without `|| true` and persist actual process RC:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py
ruff check configs/base.py \
  configs/stage1_5j_b_historical_aggtrades_launch_response.py \
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

5. Compare final state to Task 0 path-by-path. Every pre-existing non-whitelisted dirty/untracked path must have identical type/size/SHA and tracked patch bytes. Each pre-existing allowed path must have an attributable Task 1-4 diff only. Recompute J-A recursive inventory and v1/J-A verifier source/test hashes; require equality. Require index clean, no unexpected path, no canonical receipt authority or J-B data root, no network/socket/subprocess/execution call, `RISK_LIVE_TRADING_ENABLED=False`, and exactly the twelve J-B authority flags false.

---

## 8. Task 6: Independent Review Then Completion Audit

1. Request independent code review after all Task 5 gates. Review input must include: the three received external authority bytes/sidecars; Task 0 ledgers; all pre/post config/policy hashes; J-A loader/v2 verifier actual transcripts; F-JA/F-JB/F-V2 provenance; nine-boundary ledger; all mutation/lifecycle/resource/precedence results; v2 source SHA; J-A no-touch evidence; scope/index proof; and scanner actual RC.
2. Persist review artifact path/SHA and verdict. Required P0/P1 findings must equal zero before any Completion Audit begins. Any open finding is `STOP=stage1_5j_b_code_review_open_findings`.
3. Only then may a fresh independent auditor follow `.agent/skills/audit-plan-completion/SKILL.md`, independently re-run external-authority validation, J-A public loader, J-A v2 CLI, stage-config checks, F-JB domain loader, J-B v2 CLI, mutations, no-touch/provenance, scanner, scope/index and permission-absence gates. Executor summaries are not evidence.

---

## 9. Stop Matrix

| Condition | Required route |
| --- | --- |
| external Domain/v2/Plan approval absent, malformed, or byte/SHA mismatch | `STOP=implementation_authorization_missing` or `STOP=approved_authority_mismatch` |
| HEAD, approved Design/Plan identity, or immutable J-A tuple mismatch | `BLOCKED_SPEC_DRIFT`; never rebaseline |
| current base diff differs from exact proven R1 block | `BLOCKED_SCOPE_DRIFT` |
| needed owner/path outside whitelist or a pre-existing non-whitelisted byte changes | `BLOCKED_SCOPE_DRIFT` |
| frozen invariant cannot be met inside whitelist | `BLOCKED_IMPLEMENTATION_DEFECT`; add its RED proof in a replacement Plan |
| base/J-A loader/J-A v2 failure | preserve named upstream STOP; do not reach ZIP/reducer/staging |
| stage config/import/value/authority mismatch | `STOP=stage1_5j_b_config_authority_mismatch`; no fallback |
| v1 offered as v2 or absent/mismatched v2 tuple | `STOP=governance_j_b_wrong_profile_evidence` |
| J-A/v1 byte change, canonical receipt authorization, J-B data root, network, or permission promotion | immediate safety/scope stop; preserve evidence; do not normalize/delete |
| review has required open P0/P1 | `STOP=stage1_5j_b_code_review_open_findings` |

No compatibility mode, alias, dynamic source lookup, temporary clean worktree, generic config framework, or permission escalation is allowed.
