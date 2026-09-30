# Stage 1.5G Cross-Root Event-Family Admission Implementation Plan

> **For Codex:** 只有本 Plan 经独立审核且用户发出绑定本文件 SHA-256 的实施批准语句后，才可按 `executing-plans` 逐 Task 实施。当前文档不授权 implementation、数据读取、receipt 生成、网络、replay、交易、commit、push、deployment 或 SSH。

**Goal:** 新增一个封闭的本地 Stage 1.5G cross-root admission producer：仅重跑两个冻结 Stage 1.5F root 的既有 production loader/reducer，写入可本地严格校验的 2-parent/8-symbol evidence-count receipt；它不授予 Gate 3 完成、Alpha、策略、执行或未来消费者权限。

**Architecture:** 新模块从自己的已解析 `__file__` 确定 project root；在验证 Task 0 外部 Plan authority、已批准 Design 和三个冻结上游文件的完整字节前，它不导入 `stage1_5g_live_depth_evidence_review`、`configs.base` 或 `safety`。导入后必须验证三个实际 module 的 `__file__`、`__spec__.origin` 和再次哈希均等于冻结 workspace bytes。随后按固定 `moonshot -> batch7` 顺序复用 `load_stage1_5g_inputs()` 与 `build_stage1_5g_review_summary()`，仅投影 formal completed children，再写入固定 schema 的 canonical JSON、确定性 Markdown 和 manifest-last receipt。CLI 仅接受 Task 0 authority packet、approval bindings 与 `RUN_ID`，不接受 root、output path、URL、stdin、glob 或环境默认输入。

**Tech Stack:** Python 3 标准库、既有 Stage 1.5G production loader/reducer、`canonical_json_dumps`、pytest、ruff、Git、`shasum`、`.agent/tools/anti_shortcut_scan.py`。不增加依赖、配置、服务、网络客户端或消费者。

---

## 1. Approved Design Binding

| Item | Exact value |
| --- | --- |
| Approved Design | `docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md` |
| Approved Design SHA-256 | `51a25377537dade47c7a234f93802aa445db75348f7e10b4e9c354888d4cefc7` |
| Expected Plan path | `docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md` |
| Approved Plan SHA-256 source | implementation authorization sentence, copied verbatim into `APPROVED_PLAN_SHA256` before Task 0; never derived from the current Plan or CLI caller |
| Design final claim | local historical-root count/integrity admission only; never Gate 3 completion, Alpha, event-family market conclusion, replay, execution or runtime claim |
| Required upstream 1.5G source SHA-256 | `596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d` |
| Required `configs/base.py` SHA-256 | `414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4` |
| Required `safety.py` SHA-256 | `1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d` |

Before any allowed source/test change, Task 0 must receive the external implementation-authorization binding below. It is the authority edge from the user's approved exact Plan SHA to this attempt; a Plan file plus a caller-selected matching hash is not authority.

```text
APPROVED_PLAN_PATH
APPROVED_PLAN_SHA256
```

The later local CLI must require the following exact regular-file bindings and the immutable Task 0 authority packet before it reads either root:

```text
--approved-design-path
--approved-design-sha256
--approved-plan-path
--approved-plan-sha256
--execution-baseline-dir
```

The CLI/core compares every supplied path/hash to the Task 0 authority packet, then rehashes the current files. Missing, symlinked, non-regular, wrong-path or mismatching approval bytes are `STOP=approved_authority_mismatch`; a mismatching Design pair is also `STOP=stage1_5g_cross_root_design_approval_mismatch`. This Plan does not itself authorize a receipt-producing invocation.

## Allowed Change Scope

### Allowed implementation paths

- `src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py`
- `scripts/external_signal_shadow/run_stage1_5g_cross_root_event_family_admission.py`

### Allowed verification paths

- `tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5g_cross_root_event_family_admission.py`

### Allowed documentation paths

- `docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md` (this Plan only; implementation does not mutate documentation)

### Allowed generated/runtime artifacts

- `data/external_signal_shadow/stage1_5g/event_family_admissions/<RUN_ID>/**` only after separate local execution authorization; generated only and not committed.
- pytest-only outputs below `tmp_path`; never durable project evidence.

### Affected but unchanged

- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
  - compatibility evidence: Task 1 real-root production loader/reducer test and Task 5 wiring test.
- `src/research/external_signal_shadow/safety.py`
  - compatibility evidence: Task 3 canonical-byte comparison with existing `canonical_json_dumps`.
- `configs/base.py`
  - compatibility evidence: Task 2 requires values exactly `3` and `2`, after frozen-byte admission.
- `scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py`, Stage 1.5D/1.5F producers, Stage 1.5H, existing reviews/data roots, all consumers, roadmap/status, VPS/runbook, `graphify-out/` and Git metadata.
  - compatibility evidence: Task 0 topology record and Task 6 scope/index proof; no consumer is wired.

### Forbidden

- Any mutation outside the paths above, including `configs/base.py`, existing 1.5G source, collectors, existing data/review roots, consumer code, deployment files, runtime configuration, roadmap/status documents and Git metadata.
- Network/VPS/SSH actions, data repair/download, third-root discovery, `SPCXUSD1`, raw orderbook aggregation, price/outcome/PnL/expectancy/replay/backtest analysis, Alpha/strategy/threshold/entry/exit/sizing claims, paper/live trading, execution, commit, push or deployment.
- Full-repository autofix/formatting, unscoped cleanup, `git reset`, `git checkout`, rebaseline, or deletion of pre-existing dirty/untracked paths.

A needed file outside this list is `STOP=BLOCKED_SCOPE_DRIFT`. If the frozen Design bytes, producer semantics, input identities, thresholds, receipt schema, lifecycle or permissions cannot be honored, `STOP=BLOCKED_SPEC_DRIFT`; do not reinterpret the contract or update a hash.

## 3. Frozen Input Packet And Canonical Positive Fixture

The producer contains exactly these ordered constants; it has no arbitrary-root registry, selection or extension mechanism:

| input key | stored summary / SHA-256 | source root / `SHA256SUMS` SHA-256 |
| --- | --- | --- |
| `moonshot` | `data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json` / `849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082` | `data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot` / `611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db` |
| `batch7` | `data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json` / `28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37` | `data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7` / `0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280` |

The only cross-boundary positive fixture is these exact workspace bytes. The core test calls the production loader/reducer on both roots; it cannot replace their summaries with hand-built dictionaries. Missing roots, changed stored summaries, altered manifests or non-clean recomputation are test failures/STOPs, not skips and not a reason to synthesize a positive input.

Temporary copies may be made only inside `tmp_path` for one mutation at a time. Synthetic payloads are allowed only to unit-test the newly owned summary/Markdown/manifest strict loader and atomic lifecycle after the real-root integration test is in place.

## 4. Authority Edge To Implementation Matrix

| Design authority/invariant | Implementation owner and proof | Fail-closed result |
| --- | --- | --- |
| external exact Plan authority | Task 0 captures externally supplied exact Plan path/SHA in immutable attempt authority; Tasks 1-6 and CLI rehash/recompare it before reads | `STOP=approved_authority_mismatch` |
| §2.1, `INV-15U-02` upstream bytes | Task 0 records hashes; Task 2 checks all three before lazy imports | `STOP=stage1_5g_cross_root_upstream_contract_drift` |
| §2.1 executed-module identity | Task 2 rejects preloaded/shadow modules and proves `__file__`/`__spec__.origin`/post-import bytes equal frozen paths; CWD mutation cannot redirect project-root paths | `STOP=stage1_5g_cross_root_upstream_module_origin_mismatch` |
| §2.2/§5.1, `INV-15U-01` two exact roots | Task 1 real-root fixture; Task 2 validates summary bytes, root type, production loader/reducer and stored/recomputed projection | `STOP=stage1_5g_cross_root_input_authority_mismatch` or `...root_not_clean` |
| §5.2, `INV-15U-03` parent-aware 2/2/8 reducer | Task 2 builds exact parent ledger and rejects duplicate article/event/child or threshold drift | `STOP=...parent_independence_mismatch`, `...child_identity_collision` or `...threshold_not_met` |
| §5.3, `INV-15U-05` fixed receipt projection | Task 3 owns exact schema/canonical JSON/literal Markdown/manifest-last; Task 4 re-derives each byte | `STOP=...publication_integrity_failure` or `...review_projection_mismatch` |
| `INV-15U-07` exact 13 false flags | Tasks 2/4 require exact key set and `type(value) is bool and value is False`; missing is not false | `STOP=...publication_integrity_failure` |
| `INV-15U-08` byte-authoritative lifecycle | Task 4 tests each write/fsync/rename failure and restart state; no state file/return code is consumed | `STOP=...publication_integrity_failure` |
| §5.3 staging identity | Task 3 owns only `.<RUN_ID>.staging.<pid>`; Task 4 writer-created stale staging/restart test verifies the same grammar | `STOP=...publication_integrity_failure` |
| `INV-15U-04` no metric selection/averaging | Task 2 receives only production formal projections and preserves all exact children; Task 5 AST/open-spy rejects a second raw-root reader | `STOP=stage1_5g_cross_root_input_authority_mismatch` |
| `INV-15U-06` no Gate 3/Alpha/economic promotion | Tasks 2-3 require only count status `sufficient`, `stage1_5g_gate3_complete=false`, and the fixed no-market schema/template | `STOP=stage1_5g_cross_root_publication_integrity_failure` |
| `INV-15U-09` no existing/future consumer authority | Tasks 0/5 prove no consumer wiring or consume mode; any consumption request is rejected instead of adding an extension point | `STOP=stage1_5g_cross_root_future_consumer_not_authorized` |
| `INV-15U-10` no independent/holdout/promotion interpretation | Tasks 2/4 retain two parents and forbid any status beyond the fixed local count receipt | `STOP=stage1_5g_cross_root_publication_integrity_failure` |
| §9/§10 negative obligations | Tasks 1-6 provide single-point RED mutation then full GREEN rerun | corresponding exact STOP; no receipt publication |
| pre-existing workspace provenance | Task 0 writes byte-sensitive path ledger; Task 6 independently recomputes it before review/audit | `STOP=BLOCKED_SCOPE_DRIFT` |
| review/completion ordering | Task 6 captures scanner actual RC and scope/index evidence, then independent code review, then fresh Completion Audit | `INCOMPLETE` until audit; no authority promotion |

## 5. Task 0: Fresh Baseline, Approval, Input Presence And Scope Gates

**Files:**
- Create outside repository: one `EXECUTION_BASELINE_DIR` attempt bundle.
- Read only: approved Design, upstream packet, frozen summaries/roots and existing source/tests.

**Step 1: Capture a non-rebaselinable attempt bundle before any allowed-file change.**

```bash
set -euo pipefail
test -z "${EXECUTION_BASELINE_DIR+x}" || { echo 'STOP=execution_baseline_dir_already_set' >&2; exit 1; }
export EXECUTION_BASELINE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/stage1_5g_cross_root_admission.XXXXXX")"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
EXPECTED_PLAN_PATH="$PROJECT_ROOT/docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md"
: "${APPROVED_PLAN_PATH:?STOP=approved_authority_mismatch}"
: "${APPROVED_PLAN_SHA256:?STOP=approved_authority_mismatch}"
test "$APPROVED_PLAN_PATH" = "$EXPECTED_PLAN_PATH" || { echo 'STOP=approved_authority_mismatch' >&2; exit 1; }
test -f "$EXPECTED_PLAN_PATH" && test ! -L "$EXPECTED_PLAN_PATH" || { echo 'STOP=approved_authority_mismatch' >&2; exit 1; }
actual_plan_sha256="$(shasum -a 256 "$EXPECTED_PLAN_PATH" | awk '{print $1}')"
test "$actual_plan_sha256" = "$APPROVED_PLAN_SHA256" || { echo 'STOP=approved_authority_mismatch' >&2; exit 1; }
BASE_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/base_sha"
git status --short --untracked-files=all > "$EXECUTION_BASELINE_DIR/status_before.txt"
git diff --binary > "$EXECUTION_BASELINE_DIR/worktree_before.patch"
git diff --cached --binary > "$EXECUTION_BASELINE_DIR/index_before.patch"
git ls-files --others --exclude-standard | sort > "$EXECUTION_BASELINE_DIR/untracked_before.txt"
git diff --name-status "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/tracked_before.txt"
PYTHONPATH=src:. .venv/bin/python - "$EXECUTION_BASELINE_DIR" "$PROJECT_ROOT" "$BASE_SHA" \
  "$EXPECTED_PLAN_PATH" "$APPROVED_PLAN_SHA256" <<'PY'
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

bundle = Path(sys.argv[1]).resolve()
root = Path(sys.argv[2]).resolve()
base_sha = sys.argv[3]
plan_path = Path(sys.argv[4]).resolve()
plan_sha = sys.argv[5]
design_rel = "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md"
plan_rel = "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md"
design_path = root / design_rel
design_sha = "51a25377537dade47c7a234f93802aa445db75348f7e10b4e9c354888d4cefc7"

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def git_z(*args: str) -> set[str]:
    raw = subprocess.check_output(["git", *args], cwd=root)
    return {item.decode("utf-8") for item in raw.split(b"\0") if item}

if plan_path != root / plan_rel or plan_path.is_symlink() or sha256(plan_path) != plan_sha:
    raise SystemExit("STOP=approved_authority_mismatch")
if not design_path.is_file() or design_path.is_symlink() or sha256(design_path) != design_sha:
    raise SystemExit("STOP=stage1_5g_cross_root_design_approval_mismatch")
authority = {
    "approved_design_path": design_rel,
    "approved_design_sha256": design_sha,
    "approved_plan_path": plan_rel,
    "approved_plan_sha256": plan_sha,
    "base_sha": base_sha,
    "current_plan_sha256": sha256(plan_path),
    "project_root": str(root),
}
authority_bytes = json.dumps(authority, sort_keys=True, separators=(",", ":")).encode("utf-8")
(bundle / "execution_authority.json").write_bytes(authority_bytes)
(bundle / "execution_authority.sha256").write_text(sha256(bundle / "execution_authority.json") + "\n", encoding="utf-8")

paths = git_z("diff", "--name-only", "-z", base_sha)
paths |= git_z("diff", "--cached", "--name-only", "-z", base_sha)
paths |= git_z("ls-files", "--others", "--exclude-standard", "-z")
allowed = {
    "src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py",
    "scripts/external_signal_shadow/run_stage1_5g_cross_root_event_family_admission.py",
    "tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5g_cross_root_event_family_admission.py",
}
if paths & allowed:
    raise SystemExit("STOP=stage1_5g_cross_root_preexisting_allowed_path_dirty")
records = []
for relative_path in sorted(paths):
    path = root / relative_path
    try:
        path.relative_to(root)
        mode = path.lstat().st_mode
    except FileNotFoundError:
        records.append({"relative_path": relative_path, "object_type": "missing", "size_bytes": None, "sha256": None, "symlink_target": None})
        continue
    if stat.S_ISREG(mode):
        records.append({"relative_path": relative_path, "object_type": "regular_file", "size_bytes": path.stat().st_size, "sha256": sha256(path), "symlink_target": None})
    elif stat.S_ISLNK(mode):
        records.append({"relative_path": relative_path, "object_type": "symlink", "size_bytes": None, "sha256": None, "symlink_target": os.readlink(path)})
    else:
        raise SystemExit("STOP=stage1_5g_cross_root_preexisting_path_type_invalid")
ledger = bundle / "preexisting_path_ledger.jsonl"
ledger.write_text("".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records), encoding="utf-8")
(bundle / "preexisting_path_ledger.sha256").write_text(sha256(ledger) + "\n", encoding="utf-8")
for path in (bundle / "execution_authority.json", bundle / "execution_authority.sha256", ledger, bundle / "preexisting_path_ledger.sha256"):
    path.chmod(0o444)
PY
```

This stdlib-only Task 0 writer runs only in the attempt bundle, never in `src/` or a project script. Its immutable records are:

```text
execution_authority.json
execution_authority.sha256
preexisting_path_ledger.jsonl
preexisting_path_ledger.sha256
```

`execution_authority.json` has exactly `project_root`, `base_sha`, `approved_design_path`, `approved_design_sha256`, `approved_plan_path`, `approved_plan_sha256`, and `current_plan_sha256`; all path values are project-root-relative strings except `project_root`, and both Plan hashes equal the externally supplied `APPROVED_PLAN_SHA256`. Serialize it with sorted compact JSON, record its SHA-256 separately, then make both authority files read-only. The Task 0 helper must reject any authority-record rewrite or mismatch.

`preexisting_path_ledger.jsonl` is sorted by `relative_path`. It is built from the union of pre-existing tracked worktree-diff paths, staged-diff paths and untracked paths. Every record has exactly `relative_path`, `object_type`, `size_bytes`, `sha256`, and `symlink_target`: a regular file records non-negative size and its bytes hash; a symlink records its literal target and `sha256=null`; a pre-existing deletion records `object_type="missing"` with null metadata. Any other object type STOPs. The helper rejects an allowed implementation/test path that was already dirty or untracked because attribution would be ambiguous. Record the ledger SHA-256 separately and make both ledger files read-only.

The approved Design and Plan are currently pre-existing/untracked and must be preserved exactly; neither is implementation output. Do not require a clean worktree, overwrite either, or rerun Task 0 after a failure.

**Step 2: Verify exact authority/frozen inputs without raw-orderbook reads.**

```bash
shasum -a 256 \
  docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  configs/base.py \
  src/research/external_signal_shadow/safety.py \
  data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json \
  data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json \
  data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/SHA256SUMS \
  data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7/SHA256SUMS \
  | tee "$EXECUTION_BASELINE_DIR/frozen_hashes.txt"
```

Require exact equality to §§1/3; summaries must be non-symlink regular files and roots non-symlink directories. All relative inputs are resolved from `PROJECT_ROOT`, never process CWD. Mismatch stops before imports/writes with the Design-defined STOP.

**Step 3: Record topology without swallowing `rg` failures.**

```bash
set +e
rg -n -i 'cross[_ -]?root|event_family_admissions|stage1_5g_cross_root' \
  src scripts tests docs > "$EXECUTION_BASELINE_DIR/topology_discovery.txt"
rg_rc=$?
set -e
case "$rg_rc" in
  0|1) printf '%s\n' "$rg_rc" > "$EXECUTION_BASELINE_DIR/topology_discovery_rc" ;;
  *) echo 'STOP=stage1_5g_cross_root_topology_discovery_failed' >&2; exit 1 ;;
esac
```

`0` requires every hit classified; `1` means none; `>=2` is failure. Any existing/proposed consumer wiring is `STOP=stage1_5g_cross_root_future_consumer_not_authorized`.

**Step 4: Record safety/baseline stability.**

```bash
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from configs.base import RISK_LIVE_TRADING_ENABLED
assert RISK_LIVE_TRADING_ENABLED is False
print('CHECK_OK=live_trading_disabled')
PY
test "$(git rev-parse HEAD)" = "$(cat "$EXECUTION_BASELINE_DIR/base_sha")"
```

**Expected:** all pass and no repository file changes. At each later Task start/end, the executor must: verify both immutable-record sidecar hashes; parse `execution_authority.json`; require expected relative Plan path and external approved Plan SHA; rehash current Plan/Design and require both unchanged; then compare `HEAD` to `base_sha`. A mismatch before any root read is `STOP=approved_authority_mismatch` (or `...head_drift` for HEAD). Preserve unexpected pre-existing changes and ask the user rather than attributing/rebaselining them.

## 6. Task 1: RED Production-Admission Contract Tests

**Files:**
- Create: `tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py`
- Read only: existing 1.5G source and test fixture helpers.

**Step 1: Write the real-root integration test first.**

Import frozen packet constants from the new module, call its public admission function, and assert all facts derive from actual source roots:

```python
assert result["formal_symbol_count"] == 8
assert result["distinct_source_article_count"] == 2
assert result["independent_parent_event_count"] == 2
assert result["cross_root_evidence_count_status"] == "sufficient"
assert result["stage1_5g_gate3_complete"] is False
assert result["authority_flags"] == EXPECTED_13_FALSE_FLAGS
assert [item["input_key"] for item in result["input_records"]] == ["moonshot", "batch7"]
```

Assert the two parent IDs and exact child-symbol sequences. In an isolated subprocess, use `sys.setprofile` code-object events to prove `load_stage1_5g_inputs()` then `build_stage1_5g_review_summary()` runs once per fixed root; do not pre-import/patch their module merely to count calls. The test may not inspect raw JSONL or patch returned production summaries.

**Step 2: Split negative cases by the gate they must actually reach.**

Cross-boundary authority tests retain the exact real roots and use one declared read/hash fault at a time: stored-summary byte corruption, `SHA256SUMS` digest corruption, missing source root/file, or production loader/runtime-attestation blocker. Each asserts the upstream authority STOP before the reducer is reached.

Reducer/comparator tests first obtain the actual verified in-memory admitted projection from the real-root positive fixture, then make a single local copy and invoke the owned pure function directly. They must not rewrite a root, `SHA256SUMS`, expected hash or production summary. The required cases are: stored/recomputed projection difference through `compare_admitted_projection()`; duplicate article/event; duplicate `event_symbol_id`; duplicate symbol; missing child through `build_cross_root_summary()`; and config not exactly `3`/`2` through the verified config projection. Each asserts its own downstream Design STOP, proving the test reaches its intended gate rather than an earlier input-authority failure.

**Step 3: Run RED.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py
```

**Expected:** fail only because the new module does not yet exist.

## 7. Task 2: GREEN Minimal Admission Core And Parent-Aware Reducer

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py`

**Step 1: Implement only shared trust-boundary functions.**

Keep top-level imports stdlib-only. Define one controlled exception carrying `STOP=stage1_5g_cross_root_<reason>`. Implement in order:

1. `_project_root_from_core_file()` derives project root from the new core module's resolved `__file__`; every Design/Plan, summary/root and output path is built from this root, never CWD.
2. `verify_execution_authority(execution_baseline_dir, supplied_approval_bindings)` verifies the Task 0 record/sidecar bytes, fixed relative paths, external Plan SHA, current Plan/Design bytes and base SHA before any root read. It returns a closed authority object; no caller-selected path/hash pair reaches the reducer directly.
3. `verify_frozen_upstream_contract()` checks non-symlink regular files and the three full-file hashes using project-root-relative expected paths.
4. `_import_verified_upstream()` has one private verified-module cache. On its first call it rejects any preloaded target module, then performs step 3, imports the production 1.5G module, `configs.base` and `safety` lazily, and requires every resolved `module.__file__` and `module.__spec__.origin` to equal its frozen path. It rehashes each actual module file before caching. On later calls, it requires `sys.modules[name] is cached_module`, then repeats origin/hash checks; a replacement/shadow/preloaded module is `STOP=stage1_5g_cross_root_upstream_module_origin_mismatch`. A missing expected callable/constant is `STOP=BLOCKED_SPEC_DRIFT`, never a local fallback.
5. `admit_frozen_cross_root_inputs()` verifies stored-summary bytes before parse; production-loads/reduces each fixed root; requires clean status, six inherited false flags, expected manifest, formal projection and exact expected child set.
6. `compare_admitted_projection()` is a pure owned comparator for already verified stored/recomputed projections; `build_cross_root_summary()` accepts only admitted projections, verifies two distinct articles/events, no child collisions, exact eight symbols and config exactly `3`/`2`, then outputs fixed counts and exact 13 false flags.

Do not add a protocol, registry, callback, plugin, config setting, generic union API or consumer interface. Raw bundle objects/rows are not returned.

**Step 2: Add semantic guards.** Summary must enforce exact key sets/types, preserve all eight children under two parents, use `independent_parent_event_count=2`, and emit only:

```text
decision = stage1_5g_cross_root_event_family_admission_pass
cross_root_evidence_count_status = sufficient
stage1_5g_gate3_complete = false
```

It cannot include `event_family_conclusion_allowed=true`, market/depth, outcome/PnL/expectancy or execution authority.

**Step 3: Run GREEN/regression.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py
```

**Step 4: Add import/root-origin RED tests before declaring GREEN.** Run the real-root admission in an isolated subprocess with controlled `PYTHONPATH`; assert all three module `__file__`/`__spec__.origin` values match expected project-root paths and every frozen root/output is unchanged after `chdir(tmp_path)`. Inject a shadow or preloaded production/config/safety module and assert `...upstream_module_origin_mismatch` before any root read. A hand-built 1.5G substitute, upstream import before byte admission, CWD-relative root/output, or wrong module origin is a failed implementation.

**Expected:** all pass.

## 8. Task 3: Exact Receipt Schema, Deterministic Projection And Strict Loader

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py`

**Step 1: Add RED schema/projection tests.** A valid Task 2 summary must have exactly the 11 Design keys and canonical bytes; Markdown must equal §5.3 literal template byte-for-byte with LF/final LF; manifest has exactly four keys and only `summary`/`review`, correct relative paths/hash/length. Strict loader must reparse summary/manifest, rerender Markdown, recompute bytes and require exact 13 false bool keys.

Add single-point mutations for missing/extra/wrong-type summary/manifest key; missing/true/extra flag; changed path/hash/length; unlisted file; injected/whitespace-altered Markdown; invalid run ID; symlink artifact/root. All reject without `.get(..., False)` defaults.

**Step 2: Implement minimum closed writer/loader.** Add exact schema validation, `render_review(summary)`, `load_verified_cross_root_receipt(root)`, `classify_receipt_state(parent, run_id)`, and `publish_cross_root_receipt(summary, run_id)`. Production output parent is the project-root-derived private constant `data/external_signal_shadow/stage1_5g/event_family_admissions/`; tests may monkeypatch it to `tmp_path`, but CLI/public API cannot select it. The only matching staging grammar is a non-symlink regular directory in the same parent whose basename exactly matches `^\.<RUN_ID>\.staging\.[1-9][0-9]*$`, produced as `.<RUN_ID>.staging.<pid>` using the producer's positive decimal PID. No UUID, alternate prefix, nested temp directory or second grammar is allowed.

Validate run ID. Write summary/review by same-directory unique temporary regular files and `fsync`; write and strict-load manifest last; `fsync` staging dir; atomic `os.replace` complete directory; `fsync` final parent. Validate bytes before publication. No state file/PID/in-memory flag/return code is authoritative.

**Step 3: Run focused tests.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py
```

**Expected:** all schema/mutation tests pass without a `data/` write.

## 9. Task 4: Crash, Collision And Restart Recovery

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py`
- Modify only for deterministic test injection: `src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py`

**Step 1: Write lifecycle RED tests** with a private test-only failpoint after every temporary artifact write, file `fsync`, manifest write/validation, staging-dir `fsync`, rename and final-parent `fsync`.

| Fault position | Required result |
| --- | --- |
| admission/reducer before staging | `PRE_RENAME_STOP`; final and matching staging absent |
| temp/artifact/manifest/staging-fsync/rename fault | non-zero; final absent; staging if present is `staging_only` and non-consumable |
| rename succeeds then caller crash | strict loader alone marks valid final `receipt_published` |
| rename succeeds then parent-fsync fault | `POST_RENAME_DURABILITY_FAILURE`, non-zero; no delete/overwrite; strict loader decides published/corrupt |

Also test final collision, stale staging, malformed final and second same-`RUN_ID` call. The pre-rename writer failpoint must leave a writer-created basename matching the exact grammar. A fresh classifier invocation for the same `RUN_ID` must report `staging_only`; the same ID cannot restart; a fresh ID may proceed. No stale/corrupt root may be resumed/deleted/overwritten/consumed.

**Step 2: Implement only private no-op-default failpoint calls.** It is not a CLI flag, environment protocol or extension API. Preserve evidence; do not reuse staging.

**Step 3: Run lifecycle regression.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py
```

**Expected:** final bytes, not process status, define every restart state.

## 10. Task 5: Narrow CLI And Real Producer Wiring

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_5g_cross_root_event_family_admission.py`
- Create: `tests/scripts/external_signal_shadow/test_run_stage1_5g_cross_root_event_family_admission.py`
- Modify core only for one CLI entry function.

**Step 1: Write CLI RED tests.** It requires the four approval bindings, a regular non-symlink `--execution-baseline-dir` containing the Task 0 authority record/sidecars, and valid `--run-id`; rejects `--output-root`, arbitrary roots/inputs, URL/stdin/glob and malformed IDs. It must compare supplied Plan path/hash to the externally approved Task 0 Plan pair before input reads, reject a modified Plan with its own new matching hash, reject same-byte wrong path, and reject a Plan changed after Task 0. It calls core once, returns non-zero exact STOP on failure, writes only test-monkeypatched fixed parent, and has no network/old-review-renderer imports.

**Step 2: Implement minimal argparse CLI.** `main(argv=None) -> int` accepts only the six permitted inputs (four approval bindings, `--execution-baseline-dir`, `--run-id`), loads the Task 0 authority object, calls core once, prints receipt identity/status only after strict local reload and maps controlled STOP to non-zero. It exposes no `--verify`, `--consume`, `--resume`, output/root selection or future-consumer mode.

**Step 3: Add real wiring evidence.** AST assertion and `open` spy must prove only:

```text
CLI -> verified core -> load_stage1_5g_inputs -> build_stage1_5g_review_summary -> admitted projection -> receipt
```

The gate rejects any added direct `.jsonl` source reader/second raw-root open outside production loader, while permitting this module's stored-summary/manifest/receipt reads.

**Step 4: Run tests.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5g_cross_root_event_family_admission.py
```

**Expected:** all pass; tests only use `tmp_path` outputs and do not publish production receipt.

## 11. Task 6: Full Gates, Rule-12 Routing, Review And Completion Audit

**Step 1: Run local suite and scoped static check.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5g_cross_root_event_family_admission.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py

.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py \
  scripts/external_signal_shadow/run_stage1_5g_cross_root_event_family_admission.py \
  tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5g_cross_root_event_family_admission.py
```

**Step 2: Capture scanner actual RC/safety evidence.**

```bash
set +e
PYTHONPATH=src:. .venv/bin/python .agent/tools/anti_shortcut_scan.py --base-sha "$(cat "$EXECUTION_BASELINE_DIR/base_sha")"
scanner_rc=$?
set -e
printf '%s\n' "$scanner_rc" > "$EXECUTION_BASELINE_DIR/anti_shortcut_scan_rc"
if [ "$scanner_rc" -ne 0 ]; then
  echo 'STOP=anti_shortcut_scan_failed' >&2
  exit 1
fi

PYTHONPATH=src:. .venv/bin/python - <<'PY'
from configs.base import RISK_LIVE_TRADING_ENABLED
assert RISK_LIVE_TRADING_ENABLED is False
print('CHECK_OK=live_trading_disabled')
PY
```

The numeric `scanner_rc`, not an echoed summary, is evidence. Scan new source/CLI for network clients, subprocesses, replay imports, trade/strategy grants and raw `.jsonl` access outside production loader; any unapproved hit is normally `STOP=BLOCKED_SPEC_DRIFT`.

**Step 3: Prove scope/index/baseline integrity.**

```bash
test "$(git rev-parse HEAD)" = "$(cat "$EXECUTION_BASELINE_DIR/base_sha")"
cmp -s "$EXECUTION_BASELINE_DIR/execution_authority.sha256" <(shasum -a 256 "$EXECUTION_BASELINE_DIR/execution_authority.json" | awk '{print $1}') \
  || { echo 'STOP=approved_authority_mismatch' >&2; exit 1; }
cmp -s "$EXECUTION_BASELINE_DIR/preexisting_path_ledger.sha256" <(shasum -a 256 "$EXECUTION_BASELINE_DIR/preexisting_path_ledger.jsonl" | awk '{print $1}') \
  || { echo 'STOP=BLOCKED_SCOPE_DRIFT' >&2; exit 1; }
git diff --cached --binary > "$EXECUTION_BASELINE_DIR/index_after.patch"
cmp -s "$EXECUTION_BASELINE_DIR/index_before.patch" "$EXECUTION_BASELINE_DIR/index_after.patch" \
  || { echo 'STOP=BLOCKED_SCOPE_DRIFT' >&2; exit 1; }
git status --short --untracked-files=all > "$EXECUTION_BASELINE_DIR/status_after.txt"
PYTHONPATH=src:. .venv/bin/python - "$EXECUTION_BASELINE_DIR" <<'PY'
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

bundle = Path(sys.argv[1]).resolve()
authority = json.loads((bundle / "execution_authority.json").read_text(encoding="utf-8"))
root = Path(authority["project_root"]).resolve()
allowed = {
    "src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py",
    "scripts/external_signal_shadow/run_stage1_5g_cross_root_event_family_admission.py",
    "tests/research/external_signal_shadow/test_stage1_5g_cross_root_event_family_admission.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5g_cross_root_event_family_admission.py",
}

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def record(relative_path: str) -> dict:
    path = root / relative_path
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return {"relative_path": relative_path, "object_type": "missing", "size_bytes": None, "sha256": None, "symlink_target": None}
    if stat.S_ISREG(mode):
        return {"relative_path": relative_path, "object_type": "regular_file", "size_bytes": path.stat().st_size, "sha256": sha256(path), "symlink_target": None}
    if stat.S_ISLNK(mode):
        return {"relative_path": relative_path, "object_type": "symlink", "size_bytes": None, "sha256": None, "symlink_target": os.readlink(path)}
    raise SystemExit("STOP=BLOCKED_SCOPE_DRIFT")

ledger = [json.loads(line) for line in (bundle / "preexisting_path_ledger.jsonl").read_text(encoding="utf-8").splitlines()]
if [record(item["relative_path"]) for item in ledger] != ledger:
    raise SystemExit("STOP=BLOCKED_SCOPE_DRIFT")
if sha256(root / authority["approved_plan_path"]) != authority["approved_plan_sha256"]:
    raise SystemExit("STOP=approved_authority_mismatch")
if sha256(root / authority["approved_design_path"]) != authority["approved_design_sha256"]:
    raise SystemExit("STOP=approved_authority_mismatch")
def git_z(*args: str) -> set[str]:
    raw = subprocess.check_output(["git", *args], cwd=root)
    return {item.decode("utf-8") for item in raw.split(b"\0") if item}

current_paths = git_z("diff", "--name-only", "-z", authority["base_sha"])
current_paths |= git_z("diff", "--cached", "--name-only", "-z", authority["base_sha"])
current_paths |= git_z("ls-files", "--others", "--exclude-standard", "-z")
baseline_paths = {item["relative_path"] for item in ledger}
if current_paths - baseline_paths - allowed:
    raise SystemExit("STOP=BLOCKED_SCOPE_DRIFT")
print("CHECK_OK=preexisting_ledger_and_authority_unchanged")
PY
```

This is an exact byte-sensitive re-read, not a `git status` comparison: every pre-existing regular file, symlink or deletion must match Task 0's canonical ledger, including the pre-existing Design and Plan bytes. Only the four allowed source/test paths may be new/changed. The current Plan and Design must also equal Task 0's externally bound hashes. No new index mutation is permitted. Unexpected mutation is `STOP=BLOCKED_SCOPE_DRIFT`; never reset/checkout/rebaseline.

**Step 4: Rule-12 routing and order.**

| Observation | Required route |
| --- | --- |
| frozen Design/Plan/upstream/input bytes mismatch, or required producer API/schema differs | `STOP=BLOCKED_SPEC_DRIFT`; return to Design, do not update a frozen hash |
| required file outside §2 scope or existing consumer wiring | `STOP=BLOCKED_SCOPE_DRIFT` |
| allowed-path test/scanner/writer defect | RED -> minimum fix -> GREEN -> repeat all Task 6 gates |
| pre-existing workspace/index/HEAD drift | stop, preserve Task 0 evidence, ask user; never attribute/rebaseline |
| all gates green | invoke `requesting-code-review` for exact four-file diff; resolve OPEN findings and rerun Task 6; then fresh read-only `audit-plan-completion` |

Independent code review precedes Completion Audit. Nothing in this Plan authorizes commit, push, network, runtime receipt generation, deployment, SSH, paper/live trading or execution.

## 12. Completion Criteria

Implementation may be presented for Completion Audit only when:

1. The Task 0 externally approved Plan path/SHA, Design binding, authority sidecars and byte-sensitive pre-existing ledger remain exact through every Task and final scope gate.
2. Actual executed upstream module objects have the frozen `__file__`/`__spec__.origin`/post-import bytes, and exact `moonshot`/`batch7` roots are independently re-admitted via their reviewed production loader/reducer to yield only 2 articles, 2 parents, 8 symbols and 13 false flags.
3. Every trust-boundary mutation stops at its intended authority gate, and every copied admitted-projection mutation reaches and rejects at its intended comparator/reducer gate.
4. Strict loader re-derives canonical summary, manifest and deterministic Markdown without raw/depth/economic/Alpha content; writer-created stale staging matches `.<RUN_ID>.staging.<pid>` and is non-consumable on fresh classification.
5. CLI compares approval bindings to the immutable Task 0 authority before reads and derives its sole output root from valid `RUN_ID`.
6. Full pytest, scoped ruff, actual scanner RC `0`, safety assertion, byte-sensitive ledger/index/worktree and HEAD checks pass.
7. Independent code review and fresh Completion Audit have no OPEN required finding.

`COMPLETE` means only this local implementation contract is complete. It never grants receipt execution, Gate 3 completion, consumer, Alpha, network, execution, paper/live trading, commit, push, deployment or SSH authority.
