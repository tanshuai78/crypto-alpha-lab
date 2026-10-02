# Stage 1.5G N=3 跨根去重与产品机制分层准入 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 仅当本 Plan 经独立审核、用户以本文件 exact SHA-256 发送实施批准语句后，才允许实施。

**目标：** 新增一个只读、本地、独立于旧 N=2/1.5H V3 的 N=3 admission producer；它只重准入三条冻结根、从 CT root 唯一投影 `CTUSDT`、输出严格的 regime-separated receipt，且不生成任何研究、执行或运行时权限。

**最小架构：** 只创建一个 core、一个窄 CLI 和两份测试。core 直接调用已冻结的 production Stage 1.5G loader/reducer，使用 Python stdlib 与已有 `canonical_json_dumps`；它不建立产品分类 registry、root discovery、raw JSONL reader、通用 plugin/factory 或 consumer。旧 N=2 与 1.5H V3 保持不变。

**技术栈：** Python stdlib、现有 Stage 1.5G production review module、现有 `safety.canonical_json_dumps`、pytest、ruff、Git、`shasum`、`.agent/tools/anti_shortcut_scan.py`。不新增依赖、服务或网络访问。

---

## 1. Approved Design Binding

| 项目 | 冻结值 |
| --- | --- |
| Approved Design | `docs/designs/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-design_CN.md` |
| Approved Design SHA-256 | `81f7da45c882cc16430f57e4252e5530e457a95b7f36ff045d262ded9e755da0` |
| 本 Plan | `docs/plans/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-implementation-plan_CN.md` |
| Implementation authority | 只能来自用户未来逐字提供的两行 Plan 实施批准语句；其解析出的 Plan path/SHA 与 current Plan bytes 必须三方一致 |
| Frozen review module | `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py` / `596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d` |
| Frozen config | `configs/base.py` / `414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4` |
| Frozen serializer | `src/research/external_signal_shadow/safety.py` / `1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d` |

实施时的原始用户语句必须恰为下面两行，且 `<PLAN_SHA256>` 是本 Plan 审核通过后的 lowercase 64-hex digest：

```text
我批准实施 Plan：docs/plans/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-implementation-plan_CN.md（SHA-256: <PLAN_SHA256>）。
允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。
```

Task 0 必须把原始 UTF-8 bytes 写入唯一 canonical attempt bundle 的 `implementation_authorization.txt`，写出同一 bytes 的 `.sha256` sidecar 后才解析。仅从该 immutable record 得到 `approved_plan_path` 和 `approved_plan_sha256`；环境值只能与其精确比较，CLI/caller 绝不能选择或替换 attempt bundle。

`execution_authority.json` 必须是 sorted compact JSON，key set 恰为：

```text
project_root
base_sha
approved_design_path
approved_design_sha256
approved_plan_path
approved_plan_sha256
current_plan_sha256
```

每个 Task 开始/结束、core public entry、publication 前均重新验证：immutable statement/sidecar、authority JSON/sidecar、approved Design regular-file bytes、Plan regular-file bytes、路径、三方 Plan SHA 与 `HEAD == base_sha`。这些检查失败时为 `STOP=approved_authority_mismatch`，且不得读取 source root、导入 upstream 或创建 staging root。

### Local Receipt-Generation Authority (Separate, Future Only)

上述 implementation statement 只允许修改四个 source/test surfaces，绝不允许写入真实 final root。任何 public entry 或 CLI 在没有下列独立 authority 时，必须在读取 source root、创建 staging root 或调用 writer 之前返回：

```text
STOP=local_receipt_generation_not_authorized
```

未来若用户明确授权一次本地 receipt generation，必须逐字把以下两行写入唯一 canonical attempt bundle 内固定的 `receipt_generation_authorization.txt`，并以同 bytes 生成相邻的 `receipt_generation_authorization.sha256`：

```text
我批准本地生成 N=3 receipt：docs/plans/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-implementation-plan_CN.md（SHA-256: <PLAN_SHA256>）。
允许仅本地生成 receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。
```

该文件不是 executor 生成物，Task 0 时必须不存在；只可由后续明确用户授权写入。core 必须要求这两个文件均为 regular non-symlink files，sidecar 精确匹配、两行语法/Plan path/SHA 精确匹配 current Plan 和 immutable implementation authority，并且输出 parent 只能是 Design 固定 namespace。该 second authority 不改变 receipt 的十三个 false flags，也不授予 consumer、network、execution、paper/live、commit、push 或 deployment authority。

## 2. Allowed Change Scope

### Allowed implementation paths

- `src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py`
- `scripts/external_signal_shadow/run_stage1_5g_n3_regime_stratified_admission.py`

### Allowed verification paths

- `tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5g_n3_regime_stratified_admission.py`

### Allowed documentation paths

- 本 Plan 本身；实施阶段不得修改任何其它文档。

### Allowed generated/runtime artifacts

- `graphify-out/**` only after the required post-code AST-only `graphify update .`; it is ignored advisory output, must be recorded separately, and is never implementation source or evidence artifact.
- pytest `tmp_path` output and the canonical Git-metadata Task 0 attempt bundle are local verification evidence, not project artifacts.
- 只有另一条明确的 local receipt-generation authorization 才可写入 `data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/<RUN_ID>/**`；不得提交该产物。

### Affected but unchanged

- `docs/designs/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-design_CN.md`
  - authority evidence: Task 0 records its pre-existing untracked/tracked state and exact approved SHA; implementation never edits it.
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
  - compatibility evidence: Task 1 canonical fixture calls its actual `load_stage1_5g_inputs()` and `build_stage1_5g_review_summary()` for every frozen root; Task 5 verifies origin and SHA before/after import.
- `src/research/external_signal_shadow/safety.py`, `configs/base.py`
  - compatibility evidence: Task 1/2 validate their frozen bytes and Task 5 asserts `RISK_LIVE_TRADING_ENABLED=False`.
- `src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py`, its CLI/tests, and `data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z/`
  - compatibility evidence: Task 0 hashes/ledgers them as No-Touch; Task 6 asserts no diff or index change. N=3 never imports the N=2 reducer or loader.
- `src/research/external_signal_shadow/stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py`, its CLI/tests, and existing V3 receipt
  - compatibility evidence: Task 0/6 No-Touch diff proof and Task 5 AST proof that N=3 does not wire a future consumer.
- All Stage 1.5D/1.5F collection roots, VPS/runbooks, `docs/roadmap*`, `docs/project-status/*`, Git refs/remotes/index, and existing data roots.
  - compatibility evidence: Task 0 pre-existing ledger and Task 6 scope/index proof; no mutation is permitted.

### Forbidden

- Any mutation outside the exact paths above.
- Any edit of the approved Design, old N=2/1.5H V3 contract, source roots, configuration, thresholds, roadmap/status, collectors, VPS/runbooks, or existing receipt.
- Network, SSH, VPS action, download, root discovery, replay/backtest, raw orderbook recalculation, PnL/cost/liquidity/Alpha conclusion, paper/live trading, execution import, deployment, commit, or push.
- Full-repository autofix/format (`ruff check --fix .`), destructive cleanup (`git clean -fdx`, reset, checkout), rebaseline, or a caller-selected attempt bundle.

Any required non-whitelisted change is `STOP=BLOCKED_SCOPE_DRIFT`. A contradiction between this Plan/approved Design and the frozen actual source API is `STOP=BLOCKED_SPEC_DRIFT`; do not patch it with a fallback, fabricated record, changed hash, or altered interpretation.

## 3. Canonical Positive Fixture

The only cross-boundary positive fixture is the exact local evidence below. Tests must call the frozen upstream constructor/reducer on it; hand-built source summaries, accepted-event dictionaries, raw JSONL readers, mock upstream loaders, dynamic root discovery, and Section 3.5 BAPI payload reads are prohibited.

| input key | stored summary / SHA-256 | source root / `SHA256SUMS` SHA-256 | emitted parent/children |
| --- | --- | --- | --- |
| `moonshot` | `data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json` / `849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082` | `data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot` / `611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db` | article `7379b99aa0f349a49c3b3feca1b4bbd6`; event `e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5`; `MOONSHOTUSDT` |
| `batch7` | `data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json` / `28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37` | `data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7` / `0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280` | article `0c6ea14ba89b451db6ec9ec364045d22`; event `d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0`; exact seven-child Batch 7 set |
| `ct_projection` | `data/external_signal_shadow/stage1_5g/reviews/20261002T010000Z_ctusdt_review/stage1_5g_live_depth_evidence_review_summary.json` / `9f6a1e9797dbc42af3ce103ed231689adb0422ef1ab23768ca398eb8ec153c1c` | `data/external_signal_shadow/local_evidence/20261001T074500Z_stage1_5f_ctusdt` / `f69efe25ea2efd03054372c41f882e2deb10e9842b890d71f60c19ce9b44f7db` | article `6bd26adeb6f742fe88eb72faca183566`; event `374345c5e4527ca0f061155796909acb385fbd084172f175bd8accb00cdbd963`; only `CTUSDT` |

The CT source projection is exactly `ACNUSDT`, `BWETUSDT`, `CRMLUSDT`, `MPUSDT`, `NKEUSDT`, `SECZUSDT`, `UNHUSDT`, `CTUSDT`. The first seven must be exact identity-equal to independently recomputed Batch 7 children. The N=3 receipt must contain exactly `3` parent articles, `3` parent events, `9` unique `event_symbol_id`s, and `9` unique symbols.

The canonical final test receipt has RUN_ID grammar `^stage1_5g_n3_regime_stratified_admission_[0-9]{8}T[0-9]{6}Z$`; tests publish only into `tmp_path`. Its three artifacts are summary, review and manifest named exactly as approved Design Section 5.4. A receipt never becomes a runtime artifact in the repository under this Plan.

## 4. Design-to-Implementation Matrix

| Approved Design invariant | Implementation owner | RED proof then canonical GREEN proof | Required fail-closed outcome |
| --- | --- | --- | --- |
| `INV-15G-N3-01` exact inputs and canonical upstream producer | Tasks 1-2 core | single drift/missing input mutation fails before reducer; three real roots pass via actual upstream loader/reducer once each | `STOP=stage1_5g_n3_regime_input_authority_mismatch` |
| `INV-15G-N3-02` stored/recomputed clean-pass binding | Tasks 1-2 comparator | stored-summary hash, `SHA256SUMS`, clean flag, formal child projection or false-flag mutation rejects; exact stored/recomputed views match | `STOP=stage1_5g_n3_regime_input_authority_mismatch` |
| `INV-15G-N3-03` CT re-projection and duplicate exclusion | Tasks 1-2 reducer | missing/changed CT, changed duplicated Batch 7 child, ninth child, arbitrary clean child and duplicate emission reject; exact 8-source/1-emitted CT shape passes | `STOP=stage1_5g_n3_regime_ct_projection_mismatch` |
| `INV-15G-N3-04` 3/3/9 parent-aware identity | Tasks 1-2 reducer | one duplicate/missing article, event, symbol or event-symbol ID rejects; three parent clusters and nine unique children pass | `STOP=stage1_5g_n3_regime_parent_identity_mismatch` |
| `INV-15G-N3-05` frozen regime ledger | Tasks 1-2 schema validator | one changed/missing/extra/type-invalid regime field, parent, URL or anchor hash rejects; exact Design-owned declarations plus canonical accepted-event projection pass | `STOP=stage1_5g_n3_regime_classification_mismatch` |
| `INV-15G-N3-06`, `INV-15G-N3-10` no conclusion/consumer | Tasks 1, 2, 5 | forbidden aggregate/market/Alpha text and consumer import/entry point reject; AST proves no future consumer, no BAPI payload read | `STOP=stage1_5g_n3_regime_future_consumer_not_authorized` |
| `INV-15G-N3-07` exact schemas and false authority vector | Tasks 1-3 | one changed count/key/flag/type/Markdown byte or manifest metadata key/length/hash rejects; exact canonical bytes reload | `STOP=stage1_5g_n3_regime_publication_integrity_failure` |
| `INV-15G-N3-08` publication and recovery | Task 4 | every pre-rename failpoint remains staging-only; stale/malformed/mixed/symlink/collision/final corruption rejects; valid final reloads only after rename and parent fsync | `STOP=stage1_5g_n3_regime_publication_integrity_failure` and nonzero `POST_RENAME_DURABILITY_FAILURE` where applicable |
| `INV-15G-N3-09` No-Touch N=2 and V3 | Tasks 0, 5, 6 | topology and diff/index proof show no import, mutation or schema reuse; new N=3 paths only | `STOP=BLOCKED_SCOPE_DRIFT` |
| implementation vs local receipt-generation authority | Tasks 1, 2, 5 | absent/malformed generation record rejects before input/staging; valid future record reaches only fixed production parent and cannot change receipt flags | `STOP=local_receipt_generation_not_authorized` |
| approved authority, scope and L1 Rule 12 | Tasks 0, 5, 6 | immutable approval statement, baseline ledger, actual scanner/Graphify RC, independent code review, fresh Completion Audit | `STOP=approved_authority_mismatch`, `BLOCKED_IMPLEMENTATION_DEFECT`, `BLOCKED_SCOPE_DRIFT`, `BLOCKED_SPEC_DRIFT`, or `INCOMPLETE` |

## 5. Task 0: Immutable Authority, Baseline and Topology Gate

**Invariants:** authority edge for all `INV-*`; `INV-15G-N3-09`.

**Files:** Create exactly one canonical attempt bundle at `.git/plan-execution/stage1_5g_n3_regime/<APPROVED_PLAN_SHA256>/`. Read approved Design/Plan, frozen TCB and fixture metadata. Do not import source modules, modify files, create a N=3 receipt, or invoke a runtime producer.

1. Require caller-provided `EXECUTION_BASELINE_DIR` to be unset and reject any `--execution-baseline-dir` argument. Parse `IMPLEMENTATION_AUTHORIZATION_TEXT` in memory just far enough to validate its exact two-line grammar and obtain the expected relative Plan path/SHA. Require the external Plan path/SHA variables and current non-symlink Plan bytes to match it. From the project root and parsed Plan SHA, derive the only permitted locator:

   ```bash
   export EXECUTION_BASELINE_DIR="$(git rev-parse --git-path \
     "plan-execution/stage1_5g_n3_regime/$APPROVED_PLAN_SHA256")"
   ```

   Before `mkdir`, reject a symlink/non-directory in any existing ancestor below `.git/plan-execution`; require final canonical bundle path absent; create it once with `umask 077` and `mkdir` without `-p` on the final segment. Existing bundle, repeat Task 0, regeneration, rebaseline, reset, checkout or deletion is `STOP=approved_authority_mismatch`.
2. Require the fixed future `receipt_generation_authorization.txt` and its sidecar to be absent at baseline capture. Persist `IMPLEMENTATION_AUTHORIZATION_TEXT` verbatim to canonical `implementation_authorization.txt`; write a `shasum -a 256` sidecar; set both regular files read-only. Reject a symlink, malformed two-line grammar, changed permission line, wrong relative path, uppercase/non-hex SHA, sidecar mismatch, or an external `APPROVED_PLAN_PATH`/`APPROVED_PLAN_SHA256` that differs from parsed text.
3. Before any source/test edit, require Plan and Design to be regular non-symlink files under project root and hash them. Require the Design SHA in Section 1 and current Plan SHA equal the parsed user statement. Write/read-only `execution_authority.json` and its SHA sidecar using exactly the Section 1 key set.
4. Record `base_sha=$(git rev-parse HEAD)`, `git status --short --untracked-files=all`, tracked worktree diff, cached diff, index snapshot, sorted untracked list, and a sorted JSONL pre-existing path ledger for the union of tracked dirty/staged/untracked/missing paths. Each row records path, object type, size/SHA or literal symlink target. Record the currently pre-existing approved Design exactly as found; it must remain byte-identical. Refuse dirty/untracked state in the four allowed implementation/test paths.
5. Record hash/type/containment proof for Design, Plan, the three frozen TCB files, three stored summaries, three `SHA256SUMS` files, three source roots, and existing N=2/V3 source paths. Record a Task 0 baseline inventory for ignored `graphify-out/**` as sorted `relative_path<TAB>SHA256` regular-file rows and reject any graphify symlink. Separately record every ignored file outside `graphify-out/**` as sorted project-relative `path<TAB>type-or-SHA256` rows; it must remain byte-identical through Task 6. For Design Section 3.5, record only the literal `(parent_article_id, payload_sha256, design_review_evidence_already_verified=true)` triples from approved Design; do not locate, open, hash, contain, parse or make a runtime prerequisite of any BAPI payload.
6. Run targeted topology discovery for the new module name, N=3 namespace, N=2/H3 consumer paths and affected JSON keys. Preserve output and actual return code. Only `rg` RC `0` or `1` is valid; `>1` is `STOP=stage1_5g_n3_regime_topology_discovery_failed`. Classify every hit as `none`, `compatible_unchanged`, `BLOCKED_SCOPE_DRIFT`, or `BLOCKED_SPEC_DRIFT`. Graphify is advisory only; source/`rg` evidence determines the result.
7. At every later Task boundary, public core and CLI independently derive the canonical bundle from project root plus approved Plan SHA; neither reads `EXECUTION_BASELINE_DIR` from caller/environment nor accepts a bundle-path override. Re-hash all immutable attempt records, re-parse the authorization text, validate authority JSON schema, assert `HEAD == base_sha`, and compare new worktree/index paths against the ledger plus the exact whitelist. Any mismatch stops immediately; no downstream Task is attempted.

**Verification:** Save commands and actual exit codes in the canonical attempt bundle. Use this exact stdlib inventory at Task 0 and again in Task 6; it emits path plus digest and rejects a symlink:

```bash
graphify_inventory() {
  python3 - "$1" <<'PY'
from hashlib import sha256
from pathlib import Path
import sys

root = Path("graphify-out")
out = Path(sys.argv[1])
if not root.is_dir() or root.is_symlink():
    raise SystemExit("STOP=BLOCKED_IMPLEMENTATION_DEFECT:graphify_root")
rows = []
for path in sorted(root.rglob("*")):
    if path.is_symlink():
        raise SystemExit("STOP=BLOCKED_IMPLEMENTATION_DEFECT:graphify_symlink")
    if path.is_file():
        rows.append(f"{path.relative_to(root).as_posix()}\t{sha256(path.read_bytes()).hexdigest()}")
out.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
PY
}
graphify_inventory "$EXECUTION_BASELINE_DIR/graphify_task0_inventory.tsv"

ignored_non_graphify_inventory() {
  python3 - "$1" <<'PY'
from hashlib import sha256
from pathlib import Path
from subprocess import run
import sys

root = Path("graphify-out")
out = Path(sys.argv[1])
raw = run(
    ["git", "ls-files", "-z", "--others", "--ignored", "--exclude-standard"],
    check=True,
    capture_output=True,
).stdout
rows = []
for item in raw.split(b"\0"):
    if not item:
        continue
    path = Path(item.decode("utf-8"))
    if path == root or root in path.parents:
        continue
    if path.is_symlink():
        rows.append(f"{path.as_posix()}\tsymlink:{path.readlink().as_posix()}")
    elif path.is_file():
        rows.append(f"{path.as_posix()}\t{sha256(path.read_bytes()).hexdigest()}")
    else:
        raise SystemExit("STOP=BLOCKED_SCOPE_DRIFT:ignored_inventory_type")
out.write_text("\n".join(sorted(rows)) + ("\n" if rows else ""), encoding="utf-8")
PY
}
ignored_non_graphify_inventory "$EXECUTION_BASELINE_DIR/ignored_non_graphify_task0.tsv"
```

The topology command must explicitly preserve RC:

```bash
set +e
rg -n 'stage1_5g_n3_regime|n3_regime_stratified|stage1_5g_cross_root|stage1_5h_v3|bapi_article_detail' \
  src scripts tests docs data >"$EXECUTION_BASELINE_DIR/topology_discovery.txt"
rg_rc=$?
set -e
printf '%s\n' "$rg_rc" >"$EXECUTION_BASELINE_DIR/topology_discovery.rc"
case "$rg_rc" in 0|1) ;; *) echo 'STOP=stage1_5g_n3_regime_topology_discovery_failed' >&2; exit 1;; esac
```

**Expected result:** immutable baseline/authority records exist; approved Design and Plan may be tracked, untracked or dirty only exactly as recorded by the immutable Task 0 ledger and must remain byte-identical. The four allowed implementation/test paths have no pre-existing ownership ambiguity; index is unchanged; topology is classified. This Task cannot produce an N=3 receipt.

## 6. Task 1: RED Tests and Canonical Fixture

**Invariants:** `INV-15G-N3-01` through `-07`, `-10`.

**Files:** Create only the two allowed test files. Do not create production code before its corresponding RED test.

1. Add a fixture that invokes the frozen upstream `load_stage1_5g_inputs()` then `build_stage1_5g_review_summary()` for each of the three exact roots. It must assert schema `2`, `stage1_5g_depth_evidence_clean_pass`, `clean_depth_evidence_pass is True`, no blockers, exact stored/recomputed agreement, frozen summary/manifest SHA, and exactly one loader invocation per root. It must not create dictionaries standing in for the upstream bundle.
2. Add one-mutation RED cases for: frozen upstream byte drift; stored summary hash; `SHA256SUMS` hash; clean-pass false/blocker; source-root ancestor symlink; changed CT child; missing CT; ninth CT source child; changed Batch 7 duplicate; arbitrary CT-root child selection; duplicate/missing parent/article/event/symbol/event-symbol ID; config threshold drift; wrong/missing/extra/type-invalid regime field; wrong normalized URL/anchor hash; missing/true/extra authority flag; wrong count; extra summary key; forbidden market/Alpha/consumer wording.
3. Add strict receipt RED cases using a `tmp_path` receipt only through the private lifecycle helper: noncanonical JSON, manifest extra/missing metadata key, `byte_count` bool/zero/wrong value, hash mismatch, unlisted file, wrong input projection, wrong regime ledger, artifact/root/ancestor symlink, and Markdown byte/prose mutation. Each mutation is exactly one declared mutation unless the lifecycle state requires a compound final-plus-staging fixture.
4. Add AST/import/open-spy RED tests before core implementation. They must reject direct events/depth JSONL reader/glob/parser, network/exchange client, execution/paper/live imports, BAPI payload open, old N=2 reducer/loader import, and any current/future consumer call. Open-spy must prove source-root raw files are opened only by the verified upstream module.
5. Add public-entry/CLI RED tests that prove: no root/output/project/bundle override exists; public entry independently derives `.git/plan-execution/stage1_5g_n3_regime/<APPROVED_PLAN_SHA256>` and exactly `data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions`; implementation-only authority stops with `STOP=local_receipt_generation_not_authorized` before source/staging; malformed generation record also stops; and a valid future generation record reaches a spy on the fixed production-parent resolver without writing project data. Reject root, output, receipt, URL, resume, replay, network, `--execution-baseline-dir` and arbitrary consumer flags. Injecting an environment baseline path must have no effect.

Run and preserve RED evidence before Task 2:

```bash
set +e
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5g_n3_regime_stratified_admission.py \
  >"$EXECUTION_BASELINE_DIR/task1_red.log" 2>&1
red_rc=$?
set -e
printf '%s\n' "$red_rc" >"$EXECUTION_BASELINE_DIR/task1_red.rc"
test "$red_rc" -ne 0 || { echo 'STOP=stage1_5g_n3_regime_expected_red_not_observed' >&2; exit 1; }
```

**Expected result:** failure is only missing/unimplemented N=3 core/CLI behavior enumerated in `task1_red_expected_cases.txt`. Collection failure, a changed frozen authority, or unrelated pytest failure is `STOP=BLOCKED_SPEC_DRIFT`, not valid RED evidence.

## 7. Task 2: GREEN Minimal Admission Core

**Invariants:** `INV-15G-N3-01` through `-06`.

**Files:** Create `src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py`. Do not modify N=2/H3 or their helpers.

1. Implement the smallest direct module, resolving project root from its own `__file__`. Define fixed input records, fixed product-regime declarations, exact output namespace/RUN_ID grammar, exact STOP strings and strict non-symlink/containment/hash/type helpers. Do not add a registry, callback, extension point, optional root, glob, configurable label or consumer interface.
2. Implement `verify_execution_authority()` first. It must validate the immutable implementation text/sidecar, authority JSON/sidecar/key set, approved Design, current Plan and exact path/SHA bindings before returning an authority object. Implement `verify_local_receipt_generation_authority()` separately: it validates only the fixed future generation record/sidecar and exact grammar in Section 1, and public entry requires it before any source/staging work. Test mutation or absence must be detected before it reads an input record.
3. Implement verified lazy import of the Section 1 modules. Before and after import, bind every module to one expected project-relative path and hash; verify `__file__`, `__spec__.origin`, resolved containment and SHA. A preloaded shadow module must be rejected, not reused. Only after that call the real upstream loader/reducer exactly once per fixed root.
4. Implement the input comparator and reducer in the approved order `moonshot`, `batch7`, `ct_projection`. Compare stored/recomputed schema, clean decision, blockers, false vector, manifest SHA and ordered formal child projection. Require CT's eight source children, exact seven Batch 7 duplicate equality, and emit only exact CT identity. Require exact 3/3/9 identities before adding a parent ledger row.
5. Implement the Design-owned three-row product-regime ledger exactly. Derive official URL from re-admitted parent article and check it against the canonical accepted-event `source_detail_url_normalized`; project ordered `source_anchor_contract_hashes` only from that bundle. Never read/record the BAPI payload bytes and never accept a label from caller/CLI.
6. Implement pure in-memory summary construction with only the Section 5.2 key sets, scalars, ordered input records/parent ledger/product ledger, `stage1_5g_gate3_complete=false`, and exact thirteen boolean-false authority flags. Reject any aggregate metric, price/depth/slippage/cost/outcome field, pooled conclusion or consumer state.

Run the Task 1 suite after implementation and preserve actual RC `0` as `task2_green.rc`; a nonzero result is `STOP=BLOCKED_IMPLEMENTATION_DEFECT`.

## 8. Task 3: Strict Serialization, Loader and Human Projection

**Invariants:** `INV-15G-N3-05`, `-06`, `-07`.

**Files:** Modify only `src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py` and its existing Task 1 test file.

1. Use frozen `canonical_json_dumps` to serialize summary and manifest. Implement a literal deterministic Markdown renderer from the validated summary; it states only local structural re-admission, three parent/three event/nine child counts, mechanism-separated ledgers, `sufficient`, Gate 3 false and all prohibited authorities. Do not render product quality, liquidity, cost, execution feasibility or a pooled conclusion.
2. Implement a strict loader that checks before each `resolve()` and after containment: root/artifact/ancestor non-symlink status, final path under only the N=3 parent, exact final file set, canonical JSON bytes, exact summary/manifest key sets, metadata keys/types/hash/length, exact input projection, exact product ledger, exact false vector, and Markdown equality to the renderer.
3. Loader success returns only the validated receipt projection. It does not expose a consumer callback, offer a multi-regime aggregate, or make a consumer eligible. An attempted current/future consumer call always raises `STOP=stage1_5g_n3_regime_future_consumer_not_authorized`.
4. Turn every Task 1 strict-loader/Markdown mutation GREEN. Add no broad fixture: all cross-boundary positive data still comes from the canonical fixture.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py
```

**Expected result:** all summary/manifest/review positive and single-mutation negative tests pass; a corrupted receipt cannot return a valid projection.

## 9. Task 4: Atomic Publication, Crash and Restart Semantics

**Invariants:** `INV-15G-N3-07`, `INV-15G-N3-08`.

**Files:** Modify only the new core and its existing test file.

1. Implement a state classifier over the exact final parent and RUN_ID. It must inspect all matching siblings before resolving: `.<RUN_ID>.staging.<positive-decimal-pid>/` is the only well-formed staging grammar. Final absent/no sibling is fresh; final absent/one-or-more siblings is `staging_only`; valid final/no sibling is `receipt_published`; malformed/symlink/non-directory sibling, invalid final, or final plus any sibling is `corrupt_or_unknown`.
2. The writer uses one `fcntl.flock(LOCK_EX)` lock on the verified fixed final parent for its entire publication critical section: acquire lock -> classify final plus **all** matching siblings -> require fresh -> create only own staging -> write/fsync/atomic-stage summary, review, manifest last -> strict-load staged tree -> fsync staging -> reclassify under the same lock and require final absent, exactly own staging and zero foreign matching siblings -> atomic rename -> fsync final parent -> reclassify and require valid final plus zero matching staging -> strict final load -> return `receipt_published` -> release lock. It must not run an unlocked classifier or create a staging sibling before this lock. The private writer may accept an already-resolved `tmp_path` parent solely for lifecycle unit tests; it is not exported, environment-configurable, CLI-reachable or usable by public production entry.
3. Never overwrite, resume, delete, reuse a same RUN_ID, or infer completion from `state.*.json`. A pre-rename error leaves `staging_only` and nonzero. A post-rename/final-parent-fsync error is nonzero `POST_RENAME_DURABILITY_FAILURE`; a later process derives state only from exact current bytes.
4. Make every Task 1 lifecycle negative test GREEN with a single failpoint hook: after each staged artifact write/fsync, before rename, after rename, and after parent fsync. Cover stale sibling from another PID, malformed matching sibling, symlink final/root/ancestor, valid final, corrupt final, final-plus-staging, final collision, post-rename durability failure and a distinct fresh RUN_ID. Add a two-worker same-RUN_ID barrier test: at most one worker may return `receipt_published`; the other must fail closed on the resulting final state without creating/resuming staging. A pre-rename injected foreign-staging test must fail closed, and any final plus foreign staging is `corrupt_or_unknown`. Compound final-plus-staging is the only permitted compound mutation.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py \
  -k 'publication or lifecycle or symlink or manifest'
```

**Expected result:** only a strict final receipt is inspectable; every other state raises the approved publication STOP and leaves no silent recovery path.

## 10. Task 5: Narrow CLI, Wiring and Permission Isolation

**Invariants:** `INV-15G-N3-01`, `-06`, `-09`, `-10` and authority boundary.

**Files:** Create `scripts/external_signal_shadow/run_stage1_5g_n3_regime_stratified_admission.py`; modify only the new core/CLI tests as needed.

1. Expose only `--approved-design-path`, `--approved-design-sha256`, `--approved-plan-path`, `--approved-plan-sha256`, and `--run-id`. Core and CLI derive the canonical bundle from project root plus verified Plan SHA; they never accept or read an environment/caller-selected bundle directory. The separate generation authority is read only from its fixed name inside that bundle; it is not an arbitrary CLI path. Do not accept source/output/receipt/root/URL/resume/consumer/runtime or `--execution-baseline-dir` flags and do not let environment variables override provenance.
2. CLI calls the public production entry only after implementation authority verification; that entry derives and validates the exact Design output parent and requires the separate generation authority before source/staging work. CLI tests must spy that public wiring and production relative parent, then prove its absent generation record stops. Only the private lifecycle helper uses `tmp_path`; no CLI happy path receives an output override, invokes the project evidence producer, or creates a real N=3 data root.
3. Make Task 1 CLI/AST/open-spy checks GREEN. Verify no network/SSH/process/deployment/commit/push/replay/paper/live/execution import, no direct raw source reader, no BAPI payload open, and no N=2/H3 consumer wiring. Verify `RISK_LIVE_TRADING_ENABLED=False` from `configs.base`.
4. Test injected shadow-module origin, modified approval text, sidecar mutation, stale `base_sha`, caller-selected provenance directory, unexpected CLI flags and attempted future-consumer call. Each must stop before input or publication work.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5g_n3_regime_stratified_admission.py
```

**Expected result:** CLI can reach only public production wiring with no output override; absent/invalid generation authority stops before source or staging; private lifecycle tests alone use test-local output; every bypass attempt fails closed; all receipt authority flags remain false.

## 11. Task 6: Scope, Scanner, Review and Completion-Audit Handoff

**Invariants:** all; especially `INV-15G-N3-08` to `-10`.

**Files:** No additional repository files. Attempt-bundle logs only.

1. Re-run Task 0 integrity checks. Compare current tracked/cached/untracked state to its original ledger. The only new paths may be the two implementation and two test files. Approved Design/Plan pre-existing state must be unchanged; `git diff --cached` must stay empty. Do not repair unrelated drift.
2. Run focused tests and lint only the new paths:

   ```bash
   PYTHONPATH=src:. .venv/bin/python -m pytest -q \
     tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py \
     tests/scripts/external_signal_shadow/test_run_stage1_5g_n3_regime_stratified_admission.py
   .venv/bin/python -m ruff check \
     src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py \
     scripts/external_signal_shadow/run_stage1_5g_n3_regime_stratified_admission.py \
     tests/research/external_signal_shadow/test_stage1_5g_n3_regime_stratified_admission.py \
     tests/scripts/external_signal_shadow/test_run_stage1_5g_n3_regime_stratified_admission.py
   python3 -c "from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False"
   ```

3. Run scanner without mutating the workspace and persist its actual return code, rather than reporting a summary:

   ```bash
   set +e
   python3 .agent/tools/anti_shortcut_scan.py --base-sha "$(cat \"$EXECUTION_BASELINE_DIR/base_sha\")" \
     >"$EXECUTION_BASELINE_DIR/anti_shortcut_scan.log" 2>&1
   scanner_rc=$?
   set -e
   printf '%s\n' "$scanner_rc" >"$EXECUTION_BASELINE_DIR/anti_shortcut_scan.rc"
   test "$scanner_rc" -eq 0 || { echo 'STOP=BLOCKED_IMPLEMENTATION_DEFECT:anti_shortcut_scan' >&2; exit 1; }
   ```

4. After all code tests pass, run the project-installed AST-only Graphify command once. The current workspace supplies `graphify` through the installed CLI; `.venv/bin/python -m graphify` is not an available module and must not be substituted into an unexecutable gate. Reuse the Task 0 `graphify_inventory()` before and after, preserving actual RC and exact content inventories:

   ```bash
   graphify_inventory "$EXECUTION_BASELINE_DIR/graphify_before.tsv"
   set +e
   graphify update . >"$EXECUTION_BASELINE_DIR/graphify_update.log" 2>&1
   graphify_rc=$?
   set -e
   printf '%s\n' "$graphify_rc" >"$EXECUTION_BASELINE_DIR/graphify_update.rc"
   test "$graphify_rc" -eq 0 || { echo 'STOP=BLOCKED_IMPLEMENTATION_DEFECT:graphify_update' >&2; exit 1; }
   graphify_inventory "$EXECUTION_BASELINE_DIR/graphify_after.tsv"
   ignored_non_graphify_inventory "$EXECUTION_BASELINE_DIR/ignored_non_graphify_after.tsv"
   cmp -s "$EXECUTION_BASELINE_DIR/graphify_task0_inventory.tsv" \
     "$EXECUTION_BASELINE_DIR/graphify_before.tsv" \
     || { echo 'STOP=BLOCKED_SCOPE_DRIFT:graphify_preexisting_drift' >&2; exit 1; }
   cmp -s "$EXECUTION_BASELINE_DIR/ignored_non_graphify_task0.tsv" \
     "$EXECUTION_BASELINE_DIR/ignored_non_graphify_after.tsv" \
     || { echo 'STOP=BLOCKED_SCOPE_DRIFT:graphify_output_leak' >&2; exit 1; }
   set +e
   diff -u "$EXECUTION_BASELINE_DIR/graphify_before.tsv" \
     "$EXECUTION_BASELINE_DIR/graphify_after.tsv" \
     >"$EXECUTION_BASELINE_DIR/graphify_delta.diff"
   graphify_delta_rc=$?
   set -e
   case "$graphify_delta_rc" in
     0|1) ;;
     *) echo 'STOP=BLOCKED_IMPLEMENTATION_DEFECT:graphify_inventory_diff' >&2; exit 1 ;;
   esac
   ```

   `graphify_before.tsv` must equal the Task 0 inventory before update. Only this one `graphify update .` may mutate `graphify-out/**`; compare after to before and preserve its exact delta. Any Graphify mutation outside that ignored family is `STOP=BLOCKED_SCOPE_DRIFT`; it is advisory generated output and excluded from the four-file implementation diff.
5. Prove scope using `git diff --check`, `git diff --name-only`, `git diff --cached --name-only`, `git status --short --untracked-files=all`, and a ledger-aware comparison. Every pre-existing dirty/untracked entry outside `graphify-out/**` must be byte-identical to Task 0; `graphify-out/**` may differ only by the Task 6 recorded inventory delta. Index remains unchanged. No generated N=3 data artifact is permitted under this authorization.
6. Request independent code review with the exact four-file diff, exact Design/Plan identities, Task 0 authority/baseline digest, RED/GREEN logs, lifecycle race/negative-test list, actual scanner/Graphify RC and Graphify inventory delta, No-Touch proof and explicit note that no real receipt was generated. If the review has an open finding, classify and remediate only through the approved Rule-12 route, then rerun all affected gates.
7. Submit the current workspace, exact approved Plan, tests, scanner/Graphify actual RC, index/worktree evidence and source/consumer paths to a fresh independent Completion Audit. Do not accept the executor's test summary as completion evidence. `COMPLETE` means only implementation completion; it grants neither receipt generation, consumer use, commit, deployment, network, SSH, paper nor live authority.

## 12. Rule-12 Routing and Permission Boundary

| Condition | Mandatory route |
| --- | --- |
| A local implementation/test defect inside the four permitted paths | `BLOCKED_IMPLEMENTATION_DEFECT`; reproduce RED, apply the minimum fix, GREEN, rerun regressions. |
| A required helper/schema/consumer/config/document/data path is outside whitelist | `BLOCKED_SCOPE_DRIFT`; stop and revise Design/Plan before changing it. |
| Frozen upstream source API, approved Design, or Plan cannot all be true | `BLOCKED_SPEC_DRIFT`; assemble failed invariant, exact SSOT bytes/path, contradiction proof and proposed Design delta. |
| Approval/baseline record, SHA, Plan/Design bytes, HEAD, sidecar, input, symlink, final state or scanner gate mismatches | fail closed using its specified `STOP`; never rebaseline, overwrite, resume or substitute authority. |

All permission flags remain false. This Plan can prove only that the N=3 local admission implementation respects frozen lineage, de-duplication, mechanism separation and receipt integrity. It cannot prove a liquidity/cost conclusion, an Alpha, execution feasibility, a strategy decision, or authorization to generate/consume a receipt.

## 13. Plan Review Checklist

- Every `INV-15G-N3-01` through `-10` has an owner, canonical positive fixture, single-mutation negative proof, green proof and final gate in Section 4.
- The only new abstractions are the required core/CLI/strict loader; existing N=2 patterns and stdlib filesystem primitives are reused. No registry, generalized classifier or consumer is planned.
- `rg`/Graphify topology evidence is checked against actual source; N=2/H3 are explicitly compatible-and-unchanged, not silently omitted consumers.
- The Plan does not authorize implementation until a separate review/approval, and never authorizes receipt generation, runtime, network, SSH, commit, push, deployment, paper or live trading.
