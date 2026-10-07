# Stage 1.5J-A Historical Archive Coverage Inventory Implementation Plan

> **For implementation agent:** 仅在本 Plan 获独立 Plan Review 通过并收到用户逐字实施批准语句后执行。按 Task 顺序执行；不得跳过 Task 0，不得生成真实 receipt、网络请求或任何交易相关动作。

**Goal:** 实现一个受单次未来网络授权约束的 Stage 1.5J-A historical archive coverage inventory producer、strict loader 和 CLI；实现阶段仅完成本地代码/测试/fixture，不发起网络或发布真实 receipt。

**Architecture:** 新 core 自行定位 project root、验证实施 authority、冻结 parser bytes 和 import origin，并且仅使用 parser 的 `classify_event_type()` / `extract_symbol_candidates_from_bapi_article_payload()`。后续获得独立网络授权时，唯一 `run_inventory(run_id)` 才能对固定 BAPI/archive URL grammar 执行无重定向的 read-only 请求；其 journal、archive verification、canonical summary/review/manifest 通过单一 parent flock 原子发布。预网络阶段实现 strict loader 并仅证明组件链路及结构性 fail-closed 行为；首次真实完整 receipt 的 positive-load 和单点语义变异闭环由独立 receipt closure audit 完成。

**Tech Stack:** Python 3.11 stdlib (`json`, `hashlib`, `urllib`, `zipfile`, `csv`, `fcntl`, `os`), existing frozen Stage 1.5D parser, pytest, ruff.

---

## 1. Authority Binding And Non-Goals

| Item | Exact value |
| --- | --- |
| Approved Design | `docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md` |
| Approved Design SHA-256 | `b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a` |
| Planning `BASE_SHA` | `d91574c292ff54a7b489a203dd1c166bb6bfba75` |
| Frozen parser | `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py` |
| Frozen parser SHA-256 | `7e0e696647acf158facbdd8d3d39351bbc68c33b039871f26f4a38bc75ad56e5` |
| Existing client | `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py` (unchanged; not imported) |
| Existing client SHA-256 at planning | `e9abedd30fa309191028e99692f894e2ac74b3aa2c4545ab841492ccc5d5734d` |

The user-approved Design does **not** authorize implementation yet. This Plan does not authorize receipt generation, network, VPS, SSH, replay, simulation, Alpha interpretation, signal generation, execution, paper/live trading, commit, push, deployment, or runtime action.

The approved Design fixes `catalog_row.code` as the raw catalog identity. `articleCode` is only the detail URL query parameter. Any observed upstream change to that grammar, parser API, frozen SHA, Design/Plan bytes, source fixture hashes, or declared schemas is `STOP=BLOCKED_SPEC_DRIFT`, with Rule-12 evidence packet: failed invariant, exact source bytes/path, minimal reproduction, and proposed Design delta.

The 1.5D client is deliberately affected-but-unchanged: its redirect/retry-oriented transport is broader than J-A's `no redirect`, zero-retry, journal-before-DNS contract. Reusing it would weaken the approved trust boundary. No existing code imports or consumes a J-A symbol at `BASE_SHA`; direct `rg` is the compatibility proof because current Graphify output has no J-A node and is stale for this new module.

### 1.1 Exact Implementation Authority Contract

Task 0 may create one local, create-once, non-symlink, project-contained bundle. Its implementation-authority packet consists of exactly these five regular files:

```text
.git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>/
  implementation_authorization.txt
  implementation_authorization.sha256
  execution_authority.json
  execution_authority.sha256
  base_sha
```

The bundle is fatal if it exists before Task 0, if this five-file authority packet has any missing or unexpected authority-file name, or if any packet entry/ancestor is not a regular non-symlink path. Task 0 may additionally create only `evidence/` for immutable baseline and final-gate evidence; the authority verifier must not treat evidence contents as authority. `implementation_authorization.txt` is exactly the two UTF-8, LF-terminated lines from the user approval:

```text
我批准实施 Plan：docs/plans/2026-10-06-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-implementation-plan_CN.md（SHA-256: <APPROVED_PLAN_SHA256>）。
允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action.
```

Its sidecar is exactly `<lowercase-64-hex>  implementation_authorization.txt\n`. `base_sha` is exactly `d91574c292ff54a7b489a203dd1c166bb6bfba75\n`. `execution_authority.json` is canonical UTF-8 JSON with sorted keys, `,`/`:` separators and one trailing LF; its exact key set is `approved_design_path,approved_design_sha256,approved_plan_path,approved_plan_sha256,base_sha,current_plan_sha256,project_root`. It binds only approved Design/Plan identities, fixed baseline and resolved project root. Its sidecar is exactly `<lowercase-64-hex>  execution_authority.json\n`.

`verify_execution_authority()` validates this implementation contract only. It must not bind or derive core, CLI, config or parser SHA values. Those post-implementation identities belong exclusively to the separately user-authorized, Completion-Audit-bound `network_authorization.txt` specified by Design Section 3.1.

### 1.2 Closure Revision Ledger

| Finding | Origin | Impact cone | Plan repair / closure proof |
| --- | --- | --- | --- |
| P0-01 | A | implementation authority -> future network authority | exact bundle grammar above; no core/CLI/config/parser identity in implementation authority |
| P0-02 | A | baseline config -> J-A-only delta | byte-for-byte baseline plus one exact appended config block verifier |
| P0-03 | A | TDD red -> semantic gate | staged machine-readable RED ledger, no collection/import failure may discharge a node |
| P0-04 | A | authority -> public `run_inventory` -> request/writer | compositional Proof A request boundary + Proof B canonical pipeline + Proof C production-symbol identity |
| P0-05 | A | parent flock -> final/staging recovery | exact four-state same-`RUN_ID` matrix and immutable-final assertions |
| P1-01 | A | approved authority bytes | Plan/Design listed immutable; documentation mutation scope is `none` |
| P1-02 | A | review -> Completion Audit | review receipt binds snapshot SHA; exact handoff snapshot equality required |
| P1-03 | A | scanner evidence | single argv JSON is invoked, stdout/stderr/RC are preserved |
| P1-04 | A | topology baseline -> final scope | exact `rg` argv/RC/output and before/after classification |
| P0-06 (Spec Drift) | A | §7.1 component fixture -> §7.2 strict-loader closure | 预网络阶段仅有受限真实 fixture 的组件/结构证明；首次完整真实 receipt positive-load 后才以其 byte-identical copy 执行单点语义变异；禁止 synthetic catalog positive fixture |
| P0-07 (Authority Grammar) | A | user authorization text | implementation_authorization.txt 第二行末尾采用 ASCII 半角句点 `runtime action.`，与用户批准文本完全一致 |
| P0-08 (Test Writer Seam) | A | __all__ & public writer | 禁止在 __all__ 导出任何 test writer；禁止公开或测试函数在非生产受控路径写出可被识别为合法 receipt 的完整树 |
| P0-09 (Public Entrypoint Seam) | A | run_inventory & authority gate | run_inventory() 严禁读取模块全局 authority/transport/staging 变量；无磁盘 network_authorization.txt 时必须在任何网络或写入前 fail-closed |
| P0-10 (Production Root Cleanup) | A | test teardown | 严禁测试清理脚本删除生产根 data/external_signal_shadow/stage1_5j_a；测试仅清理自身 tmp_path |
| P0-11 (Proof B Component Seam) | A | Proof B component boundary | Proof B 仅验证真实 GRVT 字节通过 parser、checksum、ZIP/CSV validator 组件链路；严禁合成完整目录树、虚构 journal、虚构 authority 或断言 complete 收据 |

**Mutable Set:** this Plan's authority packet, scope, Task 0-6, Task 10 routing, gate and handoff prose only.
**No-Touch Set:** approved Design bytes, frozen parser/client, all existing Stage 1.5/1.6 modules and receipts, execution/risk configuration except the exact J-A config append block, active runtime/VPS state, and every authority permission value.

## Allowed Change Scope

Allowed implementation paths:
- `configs/base.py`
- `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`
- `scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py`
- `tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/catalog_page_2.json`
- `tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/article_detail_20536b05b2a34b87a3bae99c45d0dc91.json`
- `tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/GRVTUSDT-aggTrades-2026-07-31.zip`
- `tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/GRVTUSDT-aggTrades-2026-07-31.zip.CHECKSUM`
- `tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/fixture_manifest.json`

Allowed documentation paths:
- none. The approved Design and approved Plan are immutable implementation authorities.

Allowed generated/runtime artifacts:
- `.git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>/**` (local authority/evidence bundle only; never committed)
- `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/**` (future separately authorized runtime only; must remain absent during this implementation)

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
  - compatibility evidence: SHA and pre/post-import `__file__` / `__spec__.origin` checks; the canonical fixture is parsed through its two approved entrypoints.
- `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
  - compatibility evidence: direct source inspection confirms its retry/redirect behavior is not imported into J-A.
- Stage 1.5G/H/I producer, loader, CLI, receipt and data roots
  - compatibility evidence: no J-A import or consumer wiring; J-A uses neither their runtime artifacts nor their loaders.

Forbidden:
- Any mutation outside the allowed paths.
- Any mutation of the approved Design, frozen parser/client, existing receipts, active collectors, execution/risk code, `RISK_LIVE_TRADING_ENABLED`, or VPS state.
- Any real HTTP/DNS/network action, receipt generation, replay, signal, paper/live action, commit, push, deployment, SSH, `ruff check --fix`, full-repository formatter, `git clean`, or unscoped deletion.
- Handcrafted positive catalog/detail/archive/checksum data, changed fixture names, source substitution, or a second public writer/runner.

## 2. Invariant-To-Task Map

| Design invariant | Implementation task | Mechanical proof / fail-closed condition |
| --- | --- | --- |
| INV-15J-A-01 | 2, 3 | two stable catalog scans, ordered `(pageNo, code, releaseDate, title)`, and sentinel mismatch -> `STOP=stage1_5j_a_catalog_completeness_unproven` |
| INV-15J-A-02 | 3, 4, post-network closure | reducer retains every denominator row/child status; complete-root count/status replay is proven only after a real receipt positive-load |
| INV-15J-A-03 | 1, 3 | parser SHA/origin before and after import; `catalog_row.code == URL articleCode == data.code` mismatch -> identity STOP |
| INV-15J-A-04 | 3 | full parser child list retained; only uppercase `USDT` forms archive identity; mixed suffix fixture verifies no silent deletion |
| INV-15J-A-05 | 2, 4 | fsynced intent before opener invocation; missing/duplicate/incoherent terminal record or crash staging -> no final receipt |
| INV-15J-A-06 | 3 | same-path checksum, one ZIP member, bounded streaming CSV and zero-row evidence gap; one-field mutation stops or gaps as specified |
| INV-15J-A-07 | 4, post-network closure | pre-network loader rejects malformed/incomplete trees; a positive-loaded complete receipt then proves journal/parser/package/count/render replay and each single semantic mutation STOP |
| INV-15J-A-08 | 3, 4, post-network closure | incomplete parent remains in reducer output; complete-root omission replay is proven only after a real receipt positive-load |
| INV-15J-A-09 | 1, 2, 5 | exact authority packet, one public `run_inventory(run_id)`, canonical locator, shared parent flock, no alternate public writer; missing future network authorization stops before DNS/HTTP |
| INV-15J-A-10 | 1, 5 | exact false authority map and AST/import/CLI guards reject price/PnL/Alpha/execution/replay/paper/live and downstream consumer paths |

## 3. Task 0: Immutable Baseline, Scope, Authority And Canonical Fixture

**Files:** create only the local `.git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>/` bundle and the five listed canonical fixture paths. Do not create source, tests, CLI, data roots, network authorization, or receipt.

1. Parse the user implementation approval sentence. Recompute the current Plan SHA-256 and require an exact match; require the approved Design path/SHA above and `git rev-parse HEAD == d91574c292ff54a7b489a203dd1c166bb6bfba75`. Any mismatch is `STOP=approved_authority_mismatch`; do not rewrite `base_sha` or substitute a later HEAD.
2. Capture `git status --short --untracked-files=all`, `git diff`, `git diff --cached`, and SHA-256 values for the approved Design, current `configs/base.py`, frozen parser/client, and every pre-existing untracked item. Save the exact current `configs/base.py` bytes and its SHA-256 as `evidence/configs_base.py` and `evidence/configs_base.py.sha256`; Task 6 must derive the permitted configuration delta from these bytes, never from a later Git state. The approved Design and `tmp/stage1_5j_a_canonical_fixture_capture/**` are pre-existing provenance inputs, not J-A implementation output; preserve them unchanged.
3. Create the authority bundle only if absent, as a regular non-symlink project-contained directory. Store precisely the Section 1.1 authority packet and only the Section 1.1 `evidence/` sibling. Verify the two-line approval grammar, both sidecar grammars, canonical JSON exact-key set, Design/Plan current bytes, fixed `base_sha`, and resolved project root immediately after writing. Do **not** create `network_authorization.txt`, its sidecar, a receipt-generation authority, or any generated J-A root.
4. Materialize the five fixture files as byte-identical copies of `tmp/stage1_5j_a_canonical_fixture_capture/`; do not copy a directory wholesale or use a network source. Recompute and require exactly:

```text
catalog_page_2.json                                      52973  2da6a1f5b80c82f2cd1ece1ca3fa3465a74f5bfe267d467ae93677b4825bd6b2
article_detail_20536b05b2a34b87a3bae99c45d0dc91.json     72478  c5d400781f7b94309131ee04adb8a617998d56a8f28e53407deaa80061e94ccd
GRVTUSDT-aggTrades-2026-07-31.zip                       1891845  6c6d2cf12075006f4999cfda6fb5a0cd0217c67a01971977d8737de19e834a85
GRVTUSDT-aggTrades-2026-07-31.zip.CHECKSUM                  100  6267ba25e6f12d7b09d3c064b60f1caf61fdf01c9165544f22ddc258ccc52b48
fixture_manifest.json                                      1239  2dd1e5c3cea9080ec0bee91c746f29339e31daf60d083b7b9598d59188fbcfd1
```

5. Independently parse the fixture catalog/detail with the frozen parser. Require `catalog_row.code == detail.data.code == 20536b05b2a34b87a3bae99c45d0dc91`, `futures_contract_launch`, exactly `GRVTUSDT`, `validated_by_exact_text`, and launch `1785501900000`. Require the CHECKSUM text to name the exact ZIP basename and digest. Any error is `STOP=stage1_5j_a_canonical_fixture_mismatch`.

6. Run and preserve the following exact topology inventory before any J-A source/test/config changes. Persist the canonical argv JSON array as `evidence/topology_before.argv.json`, plus stdout/stderr and actual return code as `evidence/topology_before.*`; return code `0` or `1` is evidence, while any other return code stops. Its output is classified against the allowlist in Section 1, not assumed empty.

```bash
rg --no-heading -n -e 'stage1_5j_a|run_inventory|historical_archive_coverage_inventory|EXTERNAL_SIGNAL_STAGE1_5J_A_' \
  src scripts tests configs
```

**Verification:** run the Task 0 verifier, then `git diff --cached --quiet`, `test ! -e data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory`, and a sorted path/sha ledger. Expected: all bindings exact, baseline config bytes sealed, index clean, no J-A data root, no network authorization.

## 4. Task 1: RED Trust-Boundary And Canonical Positive-Fixture Tests

**Files:** create the J-A core test and CLI test; use only the Task 0 fixture bytes.

1. Before each RED node, write `evidence/task1_red_ledger.json` as canonical JSON. Every entry has exactly `test_node_id`, `canonical_positive_fixture`, `required_preconditions_before_gate`, `single_mutation`, `target_gate`, and `expected_exact_stop`. The ledger must distinguish authority, catalog/archive and lifecycle stages; a collection error, import error, unexpected pass, unexpected xfail, or wrong exception is not RED evidence and stops Task 1.
2. Stage RED work so each completed production gate discharges only its own ledger entries: first the implementation-authority and false-permission tests, then canonical catalog/detail/archive identity and package tests, then journal/lifecycle and strict-loader structural tests. The canonical positive case loads the fixture manifest, recomputes all fixture digests/byte counts, parses actual catalog/detail through the frozen parser, streams the actual ZIP/CSV, and verifies the GRVT launch-window package. It is not a complete J-A receipt root. The RED ledger must not include full-root semantic-mutation nodes; §7.2 reserves those nodes for the first real receipt. Each stage must have zero collection errors and exact expected stops before its minimal implementation begins.
3. Write RED authority tests for missing/tampered implementation authorization, sidecar, Design/Plan bytes, malformed JSON/key set, symlink ancestor, malformed/reused run id, malformed future `network_authorization`, and absent network authorization. Parser/config/core/CLI SHA bindings are tested only in the network-authority gate, not implementation authority. Assert every public entry stops before any opener/DNS function is called.
4. Write one-mutation RED tests for catalog `code`, detail `data.code`, title classification, parser symbol/launch projection, CHECKSUM digest/basename, ZIP extra member, CSV header/row/timestamp, response byte cap, and fixture extra/renamed file. Each must reach the ledger-declared semantic gate; positive expected values may not call J-A reducer/serializer/loader helpers.
5. Add AST/open-spy RED tests: only the designated core may import its minimal stdlib transport dependencies; core may not import the old 1.5D client, scripts, requests/httpx/aiohttp, execution, replay, paper/live or strategy modules. CLI must accept only approval literals and `--run-id`; no root, URL, page, symbol, output, bundle, resume, consumer, or unsafe override argument.
6. Add lifecycle RED tests under `tmp_path`: the full same-`RUN_ID` matrix of `absent`, `staging_only`, `final_only`, and `final_plus_staging`; malformed staging, extra final file, root/ancestor symlink, pre-rename failure, post-rename parent-fsync failure, and two independently spawned writers synchronized before the shared parent lock. Only `absent` permits fresh publication. Every collision/recovery case preserves any pre-existing final bytes; at most one concurrent writer succeeds, with no overwrite or double publication.

**Verification:** run the focused tests per staged ledger and retain node-level failure output. Each intended node is either exact RED at its declared gate or GREEN only after that gate exists; all other test outcomes are fatal. No test performs HTTP/DNS.

## 5. Task 2: Minimal Core, Authority And Request-Journal State Machine

**Files:** create `configs/base.py` J-A-only constants and the J-A core; update the core test.

1. Add exactly the Section 3.2 J-A constants to `configs/base.py`, grouped under one Stage 1.5J-A comment block with the Design values. Task 6 must require `current_configs_base_bytes == evidence/configs_base.py bytes + exact approved J-A block bytes`; any reordered, edited, removed or unrelated configuration byte is `STOP=BLOCKED_SCOPE_DRIFT`. No existing threshold changes.
2. Implement the core exception, project-root locator, regular-file/ancestor-symlink/containment checks, SHA helpers, canonical JSON serializer, `fsync` helpers, and a zero-argument canonical authority-bundle locator. The public production function is exactly `run_inventory(run_id)`; no public writer/publisher function is exported. `__all__` exports strictly `["run_inventory", "verify_execution_authority", "verify_network_authorization", "load_verified_stage1_5j_a_historical_archive_coverage_root", "classify_stage1_5j_a_historical_archive_coverage_root_state"]`.
3. Implement `verify_execution_authority()` against only the Section 1.1 implementation approval text, sidecars, exact JSON key set, approved Design/Plan current bytes, baseline and resolved root; reject caller-controlled production root/bundle/output. It must not validate config/parser/core/CLI identities. Use private test seams only after canonical locator validation.
4. Implement `verify_network_authorization(run_id)` as a second, separate gate with the exact Design Section 3.1 line grammar and ordering. It validates the one future `RUN_ID`, Design/Plan/core/CLI/config/parser hashes and network profile before staging, DNS or opener invocation. It fails closed when absent during this Plan. `run_inventory(run_id)` must directly check the on-disk `network_authorization.txt` file and fail closed when absent; it must not consult or allow any mutable module globals, monkey-patches, or in-memory bypasses.
5. Implement the append-only request journal: under the one output-parent lock, atomically persist+fsync intent before opening a request; atomically persist raw bytes+fsync before exactly one terminal event. Enforce request caps, terminal combinations, contiguous IDs, no resume, and crash state classification.

**Verification:** rerun authority/journal RED tests to GREEN. Add an open-spy assertion that missing/tampered authority and every pre-network failure open no socket/HTTP request and create no staging/data output.

## 6. Task 3: Catalog, Detail, Archive And Coverage Reducer

**Files:** modify only the J-A core and its core test.

1. Implement the narrow no-redirect transport in the J-A core using stdlib only. Validate scheme, exact host, port 443, no credential/cookie/fragment/body, exact query order/keys, content byte caps, and exact final URL equality. It may be invoked only after both authority gates. It has zero retries and no fallback client.
2. Implement Scan A/B raw persistence and strict catalog grammar using `catalog_row.code`, non-bool `releaseDate`, title, cross-page order, two-pass tuple equality and sentinel. Retain every in-window denominator row before target selection. Any completeness failure publishes nothing.
3. Validate each target detail's exact envelope and identity, invoke only the two frozen parser entrypoints after pre/post import origin/SHA validation, preserve parser child order, and partition suffixes without deleting non-USDT children. Form daily archive identities only for `in_scope_usdt` children.
4. Implement same-path checksum parsing, one-member ZIP validation, bounded `ZipFile.open()` streaming, exact CSV grammar, and reducer facts. A zero post-launch row package becomes `archive_verified_zero_post_launch_rows`; bad checksum/ZIP/CSV is fatal; unavailable/persistently absent packages remain deterministic evidence gaps.
5. Keep coverage state descriptive: use only the Design enums and formulas. No price, return, MAE/MFE, PnL, fee, funding, Alpha, signal, execution, paper/live or consumer fields.

**Verification:** run canonical real-fixture tests and each one-mutation test. Expected: canonical GRVT chain reaches the verified package reducer; malformed identity/package fails at its declared gate; missing valid rows retains a coverage-gap row rather than deleting the parent.

## 7. Task 4: Sealed Receipt Grammar, Strict Loader And Recovery

**Files:** modify only the J-A core and its core test.

1. Implement the exact final tree, summary, review renderer and manifest schemas from Design Section 5.3. Serialize JSON canonically, bind every regular final-root file in the manifest, and write/re-read/hash-check artifacts before rename. `__all__` is strictly locked down to the five public symbols; no test-writer or publisher helper is exported, and no internal testing helper may write complete receipt trees to uncontrolled or non-isolated paths.
2. Implement `load_verified_stage1_5j_a_historical_archive_coverage_root()` and `classify_stage1_5j_a_historical_archive_coverage_root_state()` with only the Design's legal tree/state pairs. The loader independently replays journal projection, parser detail/child mapping, archive package references, coverage formulas, canonical JSON and rendered Markdown. It rejects extra/missing files, symlinks, noncanonical bytes, manifest mismatch, false-flag change, and any state/decision mismatch.
3. Hold one `fcntl.flock(LOCK_EX)` on the fixed output-parent directory from final/staging collision check through staging write, all file/directory fsyncs, rename, and final parent fsync. The same-run matrix is mandatory: `absent` permits one fresh attempt; `staging_only`, `final_only`, and `final_plus_staging` each stop without mutation. A post-rename fsync failure is a durability failure, never a clean receipt claim; a later run must observe `final_only` or `final_plus_staging` and must not republish.
4. Implement strict-loader structural tests that give it malformed or incomplete roots and require fail-closed rejection for missing/extra tree members, symlinks, noncanonical bytes, manifest mismatch, and illegal tree/state shapes. These tests must be labeled structural and must not assert that a semantic reduction gate was reached. Do not construct, relabel or infer a full catalog tree from the Section 8 fixture. Summary/review/enum/count formula, denominator/parent omission, duplicate journal terminal and authority-packet mutations are deferred to §7.2's receipt closure audit, after a real complete root has positive-loaded.

**Verification:** focused lifecycle/loader tests must pass: a synchronized dual-process same-`RUN_ID` test permits exactly one successful publish and forces the other writer, after acquiring the common parent lock, to stop on the existing final/staging state; `final_only` bytes remain identical; staging is nonconsumable after crash; and every declared structural loader input fails closed. Full-receipt strict-loader positive verification and the semantic mutation suite are explicitly deferred to §7.2's future production receipt closure audit.

## 8. Task 5: Narrow CLI And Production Wiring

**Files:** create the J-A CLI, modify J-A CLI test and core test only as needed for public integration.

1. Implement an argparse CLI accepting exactly `--approved-design-path`, `--approved-design-sha256`, `--approved-plan-path`, `--approved-plan-sha256`, and `--run-id`. It validates exact compiled literals, rejects extras before imports/authority work, and delegates only to `run_inventory(run_id)`.
2. **Proof A -- public authority/request boundary and fail-closed gate.** The public `run_inventory(run_id)` entrypoint must directly fail closed on absent `network_authorization.txt` on disk, raising `STOP=stage1_5j_a_network_unauthorized` before any socket, DNS, or staging directory operations. There are no module-level bypass globals, in-memory authority injections, or transport hooks in `run_inventory()`. Negative tests verify that public entrypoints fail closed without disk network authorization, and that setting arbitrary module attributes has no effect on this gate. Request URL formation, BAPI query grammar, and request-journal state machine transitions are verified as pure component tests using isolated `tmp_path` without touching `data/external_signal_shadow/stage1_5j_a`. Tests must never create, clean up, or delete paths under `data/external_signal_shadow/stage1_5j_a`, and no test fixture or teardown may call `shutil.rmtree` on production roots.
3. **Proof B -- real canonical GRVT component proof.** Directly feeds canonical GRVT fixture files into the production frozen-parser integration, checksum verifier, and ZIP/CSV streaming validator. Proves that the GRVT launch time (1785501900000) and first trade timestamp yield the exact 2335ms delay, and that extracted trade counts and status match expectations. Strictly prohibits constructing fake catalog scan trees (Scan A/B), synthetic request journals, fake authority packets, or publishing/asserting a fake `coverage_inventory_complete` receipt.
4. **Proof C -- production-symbol wiring identity.** Add AST/import-spy and direct reference assertions showing that `run_inventory` is directly wired to the verified production subcomponents (request admission, journal, parser, validator) without synthetic abstractions.
5. Assert absent local receipt-generation authority, absent network authorization on disk, all exact false authority flags, and `RISK_LIVE_TRADING_ENABLED is False`. An implementation-green test run is not receipt/network/runtime authorization.

**Verification:** run both J-A test files. Expected: CLI rejects malformed/extra values; the public `run_inventory` entrypoint fails closed on absent disk network authorization without any global bypasses; Proof A verifies fail-closed boundaries and pure request-admission without touching `data/`; Proof B verifies the unmodified canonical GRVT production pipeline without synthetic catalog pages or fake receipts; Proof C binds these production symbols to the public route. No J-A `data/` root exists.

## 9. Task 6: Final Gates, Review And Completion-Audit Handoff

**Files:** no additional tracked files. Local bundle evidence only.

1. Repeat Task 0 Design/Plan/base SHA, source hash, index, diff and untracked ledger. Verify `configs/base.py` byte-for-byte as `evidence/configs_base.py` plus the one exact Task 2 J-A block; any other configuration delta is `STOP=BLOCKED_SCOPE_DRIFT`. The only new tracked/untracked implementation paths may be the two J-A source paths, two test paths, five exact fixture files, and `configs/base.py`; the approved Design and Plan are immutable and cannot be implementation output. Any other change is `STOP=BLOCKED_SCOPE_DRIFT`.
2. Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
.venv/bin/ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py \
  scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
PYTHONPATH=src:. .venv/bin/python -c 'from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False'
```

3. Read and validate the baseline before scanner invocation. Persist `anti_shortcut_scan.argv.json` as the exact canonical JSON array, invoke that same argv, redirect both stdout/stderr to `anti_shortcut_scan.log`, and persist the actual process return code in `anti_shortcut_scan.rc`. An empty/missing/rebased value must stop before the scanner starts:

```bash
EXECUTION_BASELINE_DIR=".git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>"
scanner_base_sha="$(cat "$EXECUTION_BASELINE_DIR/base_sha")" || exit 1
test "$scanner_base_sha" = "d91574c292ff54a7b489a203dd1c166bb6bfba75" || exit 1
scanner_argv=(python3 .agent/tools/anti_shortcut_scan.py --base-sha "$scanner_base_sha")
python3 -c 'import json,sys; print(json.dumps(sys.argv[1:], separators=(",", ":")))' \
  "${scanner_argv[@]}" >"$EXECUTION_BASELINE_DIR/evidence/anti_shortcut_scan.argv.json"
set +e
"${scanner_argv[@]}" \
  >"$EXECUTION_BASELINE_DIR/evidence/anti_shortcut_scan.log" 2>&1
scanner_rc=$?
set -e
printf '%s\n' "$scanner_rc" >"$EXECUTION_BASELINE_DIR/evidence/anti_shortcut_scan.rc"
test "$scanner_rc" -eq 0 || exit 1
```

4. Run `git diff --check "$scanner_base_sha"` and `git diff --cached --check "$scanner_base_sha"`; preserve each exact argv, stdout/stderr and actual RC under `evidence/`. Both RCs must be `0`. Repeat the exact Task 0 `rg` command, preserving argv/stdout/stderr/RC as `evidence/topology_after.*`. Classify every before/after hit: any J-A hit outside the Section 1 source/script/test/config allowlist is `STOP=BLOCKED_SCOPE_DRIFT`; an unexpected non-J-A topology change is also scope drift.
5. Require actual RC `0` for pytest, ruff, risk assertion, scanner, both diff checks and the permitted topology command outcome. Preserve command output and a canonical `evidence/review_input_snapshot.json` + sidecar containing base/design/plan/source/config/fixture hashes, status/diff/index/untracked hashes, test/ruff/scanner/diff/topology argv and RCs, source-consumer topology classification, proof that no J-A data root or network authorization exists, and exactly these three pre-network closure facts: `full_receipt_strict_loader_positive_verified=false`, `full_receipt_semantic_mutation_suite_verified=false`, `deferred_to_receipt_closure_audit=true`. These are handoff facts only, not receipt schema/state or authority.
6. Run independent code review before Completion Audit. The reviewer must bind the snapshot SHA, exact fixture bytes, public `run_inventory` route, structural loader path, shared-lock race/crash behavior, authority isolation, scope/index ledger, the three deferred closure facts, and no-real-receipt proof. Before Completion Audit, recompute `evidence/completion_handoff_snapshot.json` using the identical schema and require byte-for-byte equality with the reviewer-bound snapshot; a mismatch is `STOP=code_review_snapshot_drift` and requires a new independent review. Fresh Completion Audit reruns its own scanner/probes; it does not accept executor summaries as evidence.

## 10. Completion Routing And Proof Limits

Implementation completion means only: source and tests are ready for independent audit, with no generated receipt and no outbound request. `coverage_inventory_complete` is a future deterministic data-coverage state, not `phenomenon_supported`, `alpha_candidate`, `falsified`, economic edge or execution feasibility.

If Completion Audit returns `COMPLETE`, the only optional subsequent operation is a separate user-signed network authorization for one exact `RUN_ID` and then-current completion-audited J-A core/CLI/config hashes. It remains public-read-only and grants no replay, Alpha interpretation, execution, paper/live, deployment, commit or push authority. After that one run, receipt closure audit must: (1) positive-load the first complete physical root; (2) make a byte-identical copy only after that positive load; (3) apply one mutation at a time to summary, review, enum, count formula, denominator/parent omission, duplicate journal terminal and authority packet, recomputing the manifest only where required; and (4) prove the exact intended strict-loader STOP for each. Until that audit closes, the root is not verified evidence for a future consumer. This routing creates no new receipt state or authority.
