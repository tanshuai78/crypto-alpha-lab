# External Signal Shadow Lab Stage 1.5G Runtime Attestation Evidence Gate Hotfix Implementation Plan

> **For implementation agents:** Execute only after a Plan-review verdict of `Approve`, explicit user implementation authorization, and an external exact-byte approval record. Use `execute-approved-plan` task-by-task. This Plan is not implementation, VPS deployment, runtime, trading, paper-trading, or execution authority.

**Goal:** Close the Stage 1.5F -> 1.5G -> 1.5H runtime-attestation evidence chain without changing collection, quality-reducer, static-proxy, threshold, or trading semantics.

**Architecture:** Stage 1.5F writes the parent-required immutable process-start timestamp through its existing summary writer. Stage 1.5G first validates the sealed source manifest, then validates root-contract/summary authority before reducers, and writes a positive-only proof before sealing a v3 manifest. Stage 1.5H requires that proof on its existing v2 event-bundle path. Summary, quarantine and report schemas remain unchanged.

**Tech Stack:** Existing Python standard library (`hashlib`, `json`, `re`, `pathlib`, `time`), existing `canonical_json_dumps`, atomic writers, `pytest`, and `ruff`.

## Plan Status And Authority

- Date: 2026-09-08
- Plan status: `draft_for_review`
- Approved Design: `docs/designs/2026-09-08-external-signal-shadow-lab-stage1-5g-runtime-attestation-evidence-gate-hotfix-design_CN.md`
- Approved Design SHA-256: `f30414c4fc6693844c415e5cb395c1fb2f5258bf4e8ba8ea332e53c3e9f0e7df`
- `implementation_allowed=false`
- `deployment_allowed=false`
- `runtime_action_allowed=false`

The Design's in-file `draft_for_review` marker is frozen. The external SHA above is its approval authority. Before Task 1, external approval must provide `EXPECTED_APPROVED_STAGE1_5G_RUNTIME_ATTESTATION_GATE_HOTFIX_PLAN_SHA256`; the executor hashes this exact Plan and stops with `STOP=stage1_5g_runtime_attestation_gate_plan_bytes_not_authorized` on mismatch. Plan approval does not authorize code execution, commit, push, VPS synchronization, checkout, session action, root creation, or network access.

### Closure Revision Disposition

- P0-1 is adopted as an exact-producer proof requirement: Task 0 freezes the real runbook sealing command and Task 2 executes those bytes before calling the project verifier. The requested replacement with a hand-authored all-zero fixture is not adopted: the current frozen runbook command produces its own self-entry and `verify_source_evidence_manifest()` explicitly skips that entry. A generic self-hash/all-zero assertion would test a different producer grammar. If Task 0 finds that the real producer/verifier pair cannot satisfy the approved source contract, it stops for Rule-12 review rather than silently changing the contract.

## Global Constraints

- Rehash every Section 2 parent authority before RED and before completion audit. Names are not authority substitutes.
- Preserve `RISK_LIVE_TRADING_ENABLED = False` and every 1.5F/G/H trade, paper, live, execution, private/API-key, order, alpha and execution-feasibility flag as `False`.
- Do not change `configs/base.py`, thresholds, endpoints, storage budgets, Stage 1.5D collector, schedule-revision policy, source APIs, collection scheduling, runtime-proof algorithm, protected paths, sticky latch, historical roots, or historical 1.5G/1.5H artifacts.
- Positive cross-boundary tests must use the canonical 1.5F root-contract/summary writers and the exact Task-0-frozen `SHA256SUMS` operation extracted from the Stage 1.5F runbook. Its self-entry is interpreted only by the frozen project verifier, never by a generic `shasum -c` rule or a reimplemented placeholder rule. Negative fixtures make one declared mutation after canonical construction and regenerate the disposable manifest only when the test must reach a later gate.
- Reuse `canonical_json_dumps`, existing atomic writers, existing manifest writer and `_append_once`. Do not add serializers, adapters, registries, defaulting, coercion, fallback evidence, config, or dependencies.
- Stage 1.5G summary/quarantine stay `schema_version=2` and retain their review-ID formula. Only `stage1_5g_review_manifest.json` becomes v3.
- `stage1_5g_runtime_attestation_gate.json` is positive-only: source-authority failure, quality-invalid diagnostic closure, clean-only output and partial output produce neither a gate proof nor a consumer-eligible sealed v3 manifest. Existing v2 diagnostic evidence grammar remains intact unless the parent contract already omits it.

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- `scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py`
- `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`

Allowed verification paths:
- `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py`
- `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`
- `tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py`

Allowed documentation paths:
- `docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md`

Allowed generated/runtime artifacts:
- `data/external_signal_shadow/stage1_5g/reviews/<fresh-disposable-root>/**` - verification only, ignored and never committed
- `$(git rev-parse --git-path 'plan-execution/<fresh-run-id>')/**` - execution baseline, scanner ledger and audit handover evidence only; never committed

Affected but unchanged:
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
  - evidence: Task 5 preserves producer-disabled ordinary deployment and configured-enabled E0/E1/E2.
- `configs/base.py`
  - evidence: Tasks 0 and 6 assert L0 flags; Task 6 rejects config/index drift.
- Existing 1.5F root-contract writer, runtime-proof and sticky-latch logic in the allowed runner file
  - evidence: Task 1 changes only summary process-start propagation; Task 6 rejects root-contract/proof behavior drift.
- `scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py` and legacy 1.5H v1/N=1 path
  - evidence: Task 4 keeps legacy output historical-only and outside post-hotfix v2 admission.
- Historical `data/external_signal_shadow/**` roots
  - evidence: Tasks 0 and 6 freeze pre-existing bytes; tests use only `tmp_path`.

Forbidden:
- Any mutation outside the listed paths.
- Any edit to this approved Design or this Plan after external Plan approval.
- Any config/threshold/permission change; any 1.5D schema/collector change; any reducer formula, Stage 1.5G v2 schema/review-ID change, Stage 1.5H report/bundle schema change, or legacy CLI admission change.
- Full-repository formatter/autofix, `git clean`, reset, checkout of local work, source-root mutation, report overwrite, VPS/SSH/process action, network test, push, or implicit commit.

## Mandatory STOP Conditions

Stop and return to review if any condition holds:

- The approved Design or any Section 2 parent authority differs from its frozen SHA-256.
- Correct behavior requires a root-contract schema/proof/latch/1.5D/config/threshold/report/legacy change or an unlisted path.
- Positive test evidence cannot be generated by canonical 1.5F writers plus the frozen runbook `SHA256SUMS` command.
- A source-authority failure reaches watermark, event, coverage, raw, quarantine or depth-quality reducers; writes a proof/final manifest; or mutates source bytes.
- A v2/no-proof bundle reaches report generation, a partial output is consumable, or malformed boolean values are coerced/defaulted.
- Any test, focused lint, scope proof, authority check, safety check or `audit-plan-completion` verdict fails.

## Required Execution Governance

These gates are implementation prerequisites, not implementation authority.

1. Task 0 authenticates the externally approved exact Plan bytes. It must receive `EXPECTED_APPROVED_STAGE1_5G_RUNTIME_ATTESTATION_GATE_HOTFIX_PLAN_SHA256` from an external approval record; it must not infer, write or substitute the value.
2. Task 0 records a persistent `STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR` under Git metadata. Every later Task starts by importing that exact recorded directory and stops if it is missing, unreadable or refers to a different baseline `HEAD`.
3. Before RED for every cross-boundary Task, execute the Task-0 Contract Reality record for the actual model, serializer, atomic writer, loader/verifier, manifest grammar and runbook artifact that the Task consumes. A mismatch is classified only as `BLOCKED_IMPLEMENTATION_DEFECT`, `BLOCKED_SCOPE_DRIFT`, or `BLOCKED_SPEC_DRIFT`; no local default, fabricated positive fixture or alternate grammar is allowed.
4. After every Task GREEN/scope check and again in Task 6, run the exact Task-0-frozen `.agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"` command. A nonzero scanner process return code, any `ERROR`, changed scanner bytes, a new warning identity or an undispositioned warning is `STOP`. The external Task Execution Report contains the per-run command, scanner SHA-256, process return code, raw output and a per-warning Scanner Disposition Ledger.
5. The executor never audits its own completion. Task 6 uses the `Blind-First Independent Completion Audit` protocol: it freezes the worktree and gives an independent read-only `audit-plan-completion` auditor only the factual handover packet specified there. No worktree mutation follows that verdict.

After each Task GREEN, execute this Task-level scanner gate and append its factual result to the external Task Execution Report. This command deliberately captures the scanner process return code without a pipeline:

```bash
: "${STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR:?source Task 0 reopen-baseline.sh}"
BASELINE_DIR="$STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR"
BASE_SHA="$(cat "$BASELINE_DIR/head")"
test "$(shasum -a 256 .agent/tools/anti_shortcut_scan.py | awk '{print $1}')" = "$(awk '{print $1}' "$BASELINE_DIR/scanner.sha256")" || {
  echo STOP=anti_shortcut_scanner_bytes_changed >&2; exit 1;
}
TASK_LABEL="${TASK_LABEL:?set Task label}"
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA" > "$BASELINE_DIR/scanner-$TASK_LABEL.txt" 2>&1; then
  SCANNER_RC=0
else
  SCANNER_RC=$?
fi
cat "$BASELINE_DIR/scanner-$TASK_LABEL.txt"
printf '%s\n' "$SCANNER_RC" > "$BASELINE_DIR/scanner-$TASK_LABEL.exitcode"
test "$SCANNER_RC" -eq 0 || { echo STOP=anti_shortcut_scanner_nonzero >&2; exit 1; }
rg -n '^\[ERROR\]' "$BASELINE_DIR/scanner-$TASK_LABEL.txt" && { echo STOP=anti_shortcut_scanner_error >&2; exit 1; } || true
```

Any surviving `WARNING` is copied verbatim with its normalized identity into the external Scanner Disposition Ledger for that Task. The next Task may not start until each warning has a strict-contract justification; a missing ledger entry is `STOP=scanner_warning_undispositioned`.

## Invariant Map

| Invariant | Task | Mechanical proof | Fail-closed result |
|---|---|---|---|
| INV-01 authority | 0, 6 | approved Design plus six Section 2 SHA checks | `STOP=revision_authority_incomplete` |
| INV-02 F completion | 1, 2 | immutable positive start time, mutations reject | no promotion |
| INV-03 source binding | 2 | one identity/hash/source/time/UUID mutation | binding-invalid |
| INV-04 exact booleans | 2 | canonical values pass; negative values yield one precedence blocker | no coercion |
| INV-05 compromised root | 2 | read-only diagnostic rerun and source tree digest equality | invalid |
| INV-06 unchanged reducer | 3 | existing multi-symbol fixture has same v2 metrics/decision | no formula change |
| INV-07 durable proof | 3, 4 | gate/manifest mutation matrix | `stage1_5h_runtime_attestation_gate_missing_or_invalid` |
| INV-08 legacy rejection | 4 | v2/no-proof reject; v1 remains historical-only | no new report |
| INV-09 crash closure | 3 | interrupt before final manifest | no closed bundle |
| INV-10 zero writer | 5 | exact `/proc` static cases | checkout unreachable |
| INV-11 E0/E1/E2 | 5 | configured-enabled branch remains explicit | no simplified D -> F |
| INV-12 safety | 6 | config/output flags all false | STOP |

## Task 0: Freeze Authority, Worktree And Index Baseline

**Files:** none.

**Produces:** a non-repository baseline with immutable-authority hashes, pre-task interface discovery, `HEAD`, porcelain status, pre-existing dirty/untracked bytes and full Git-index snapshot.

1. Record the baseline before RED. The candidate Design and this Plan may be pre-existing untracked paths; record their hashes and do not rewrite them during implementation.

```bash
set -euo pipefail
DESIGN=docs/designs/2026-09-08-external-signal-shadow-lab-stage1-5g-runtime-attestation-evidence-gate-hotfix-design_CN.md
PLAN=docs/plans/2026-09-08-external-signal-shadow-lab-stage1-5g-runtime-attestation-evidence-gate-hotfix-implementation-plan_CN.md
: "${EXPECTED_APPROVED_STAGE1_5G_RUNTIME_ATTESTATION_GATE_HOTFIX_PLAN_SHA256:?STOP=expected_approved_stage1_5g_runtime_attestation_gate_plan_sha256_missing}"
EXECUTION_RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
BASELINE_DIR="$(git rev-parse --git-path "plan-execution/$EXECUTION_RUN_ID")"
mkdir -p "$(dirname "$BASELINE_DIR")"
test ! -e "$BASELINE_DIR" || { echo STOP=execution_baseline_dir_not_fresh >&2; exit 1; }
mkdir "$BASELINE_DIR"

test "$(shasum -a 256 "$DESIGN" | awk '{print $1}')" = f30414c4fc6693844c415e5cb395c1fb2f5258bf4e8ba8ea332e53c3e9f0e7df || { echo STOP=approved_design_bytes_mismatch >&2; exit 1; }
test "$(shasum -a 256 docs/designs/2026-08-10-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-git-ancestry-attestation-design_CN.md | awk '{print $1}')" = 28cd9e55540a3eccfd24cca3598acdb7959d02407ff54edf1045765cba5b2f36 || { echo STOP=revision_authority_incomplete >&2; exit 1; }
test "$(shasum -a 256 docs/plans/2026-08-10-external-signal-shadow-lab-stage1-5d-1-5f-git-ancestry-attestation-implementation-plan_CN.md | awk '{print $1}')" = 65a47168af6f1e9ba11f8003cace93962a5986fafae53577996db360d4defe7e || { echo STOP=revision_authority_incomplete >&2; exit 1; }
test "$(shasum -a 256 docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-design-delta_CN.md | awk '{print $1}')" = 3528d4b5f90ee8b7bd142773b1c35a1a51b2ea09242224eaed2ab10df69c5c8b || { echo STOP=revision_authority_incomplete >&2; exit 1; }
test "$(shasum -a 256 docs/plans/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-implementation-plan_CN.md | awk '{print $1}')" = 47f9728b8a17e815e836fae837c038a0bc8ae06c6593d9ae0280741997b6da67 || { echo STOP=revision_authority_incomplete >&2; exit 1; }
test "$(shasum -a 256 docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-design-delta_CN.md | awk '{print $1}')" = ec936020cba1ca26a2709f02996ad70bcf05d9457bb1e741ac6d40685269f812 || { echo STOP=revision_authority_incomplete >&2; exit 1; }
test "$(shasum -a 256 docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md | awk '{print $1}')" = 7bf59a14a230da4071bde7acafc0b2022de52c313f47f389eadd293b162dacc4 || { echo STOP=revision_authority_incomplete >&2; exit 1; }

ACTUAL_PLAN_SHA256="$(shasum -a 256 "$PLAN" | awk '{print $1}')"
test "$ACTUAL_PLAN_SHA256" = "$EXPECTED_APPROVED_STAGE1_5G_RUNTIME_ATTESTATION_GATE_HOTFIX_PLAN_SHA256" || {
  echo STOP=stage1_5g_runtime_attestation_gate_plan_bytes_not_authorized >&2
  exit 1
}
git rev-parse HEAD > "$BASELINE_DIR/head"
printf '%s\n' "$ACTUAL_PLAN_SHA256" > "$BASELINE_DIR/approved_plan.sha256"
printf '%s\n' "$EXPECTED_APPROVED_STAGE1_5G_RUNTIME_ATTESTATION_GATE_HOTFIX_PLAN_SHA256" > "$BASELINE_DIR/expected_approved_plan.sha256"
git status --short --untracked-files=all > "$BASELINE_DIR/status.txt"
git ls-files -s -z | shasum -a 256 > "$BASELINE_DIR/index.sha256"
shasum -a 256 "$DESIGN" "$PLAN" > "$BASELINE_DIR/frozen_design_plan.sha256"
python3 - "$BASELINE_DIR" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def porcelain() -> dict[str, str]:
    raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    )
    records = raw.split(b"\0")
    out: dict[str, str] = {}
    index = 0
    while index < len(records) and records[index]:
        record = records[index]
        code = record[:2].decode("ascii")
        path = record[3:].decode("utf-8", "surrogateescape")
        out[path] = code
        index += 1
        if "R" in code or "C" in code:
            out[records[index].decode("utf-8", "surrogateescape")] = code
            index += 1
    return out


status = porcelain()
Path(sys.argv[1], "scope_baseline.json").write_text(
    json.dumps(
        {
            "status": status,
            "digest": {path: digest(Path(path)) for path in status},
        },
        sort_keys=True,
        indent=2,
    ) + "\n",
    encoding="utf-8",
)
PY
python3 - "$BASELINE_DIR" "$DESIGN" "$PLAN" <<'PY'
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


def porcelain() -> dict[str, str]:
    raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    )
    records = raw.split(b"\0")
    out, index = {}, 0
    while index < len(records) and records[index]:
        record = records[index]
        code = record[:2].decode("ascii")
        out[record[3:].decode("utf-8", "surrogateescape")] = code
        index += 1
        if "R" in code or "C" in code:
            out[records[index].decode("utf-8", "surrogateescape")] = code
            index += 1
    return out


def fingerprint(path: Path) -> dict[str, str | int | None]:
    if not path.exists() and not path.is_symlink():
        return {"type": "missing"}
    st = os.lstat(path)
    if stat.S_ISREG(st.st_mode):
        return {"type": "regular", "mode": st.st_mode, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    if stat.S_ISLNK(st.st_mode):
        return {"type": "symlink", "mode": st.st_mode, "target": os.readlink(path)}
    return {"type": "other", "mode": st.st_mode}


mutable = {
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py",
    "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py",
    "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py",
    "scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py",
    "src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py",
    "tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py",
    "tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py",
    "tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py",
    "tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py",
    "docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md",
}
status = porcelain()
overlap = sorted(set(status) & mutable)
if overlap:
    raise SystemExit("STOP=preexisting_dirty_overlap:" + ",".join(overlap))
Path(sys.argv[1], "scope_baseline_v2.json").write_text(
    json.dumps({"status": status, "fingerprint": {p: fingerprint(Path(p)) for p in status}}, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
PY
HISTORICAL_SOURCE_ROOT=data/external_signal_shadow/local_evidence/20260902T105158Z_stage1_5f
cat > "$BASELINE_DIR/fingerprint_historical_source.py" <<'PY'
import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import verify_source_evidence_manifest


def fingerprint(root: Path) -> dict:
    root = root.resolve()
    valid, manifest_sha256, blockers = verify_source_evidence_manifest(root)
    if not valid:
        raise SystemExit("STOP=historical_source_manifest_invalid:" + ",".join(blockers))
    inventory = []
    for path in sorted(root.rglob("*")):
        st = os.lstat(path)
        record = {"path": path.relative_to(root).as_posix(), "mode": st.st_mode}
        if stat.S_ISDIR(st.st_mode):
            inventory.append({**record, "type": "directory"})
        elif stat.S_ISREG(st.st_mode):
            inventory.append({**record, "type": "regular", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        else:
            raise SystemExit(f"STOP=historical_source_nonregular_path:{path}")
    return {"root": str(root), "manifest_sha256": manifest_sha256, "entry_count": len(inventory), "inventory": inventory}


parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("write", "check"))
parser.add_argument("baseline")
parser.add_argument("root")
args = parser.parse_args()
payload = fingerprint(Path(args.root))
baseline = Path(args.baseline)
if args.mode == "write":
    baseline.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
elif json.loads(baseline.read_text(encoding="utf-8")) != payload:
    raise SystemExit("STOP=historical_source_root_changed")
print("CHECK_OK=historical_source_root_" + args.mode)
PY
PYTHONPATH=src:. .venv/bin/python "$BASELINE_DIR/fingerprint_historical_source.py" write "$BASELINE_DIR/historical_source_root.json" "$HISTORICAL_SOURCE_ROOT"
SCANNER=.agent/tools/anti_shortcut_scan.py
test -f "$SCANNER" || { echo STOP=anti_shortcut_scanner_missing >&2; exit 1; }
shasum -a 256 "$SCANNER" > "$BASELINE_DIR/scanner.sha256"
if GIT_CONFIG_GLOBAL=/dev/null python3 "$SCANNER" --base-sha "$(cat "$BASELINE_DIR/head")" > "$BASELINE_DIR/scanner-baseline.txt" 2>&1; then
  SCANNER_BASELINE_RC=0
else
  SCANNER_BASELINE_RC=$?
fi
cat "$BASELINE_DIR/scanner-baseline.txt"
printf '%s\n' "$SCANNER_BASELINE_RC" > "$BASELINE_DIR/scanner-baseline.exitcode"
test "$SCANNER_BASELINE_RC" -eq 0 || { echo STOP=scanner_baseline_nonzero >&2; exit 1; }
printf 'export STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR=%q\n' "$BASELINE_DIR" > "$BASELINE_DIR/reopen-baseline.sh"
printf '%s\n' "$BASELINE_DIR" | tee "$BASELINE_DIR/path.txt"
```

2. Execute the Pre-RED Contract Reality Gate before any fixture or implementation. This is a read-only evidence capture, not permission to repair a mismatch. It freezes the actual canonical writer/loader/verifier topology, strict return shape and the exact pre-Task-5 runbook sealing command. The recorded command is the only command a Task 2 positive fixture may execute.

```bash
: "${STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR:?source Task 0 reopen-baseline.sh}"
BASELINE_DIR="$STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR"
test "$(cat "$BASELINE_DIR/head")" = "$(git rev-parse HEAD)" || { echo STOP=baseline_head_changed >&2; exit 1; }
python3 - "$BASELINE_DIR" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

baseline = Path(sys.argv[1])
runbook = Path("docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md")
source_paths = {
    "f_model": Path("src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py"),
    "f_summary": Path("src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py"),
    "f_runner": Path("scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py"),
    "g_reviewer": Path("src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py"),
    "g_cli": Path("scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py"),
    "h_loader": Path("src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py"),
}
required_tokens = {
    "f_model": ["LiveDepthObserverSummary", "last_heartbeat_at_ms"],
    "f_summary": ["build_live_depth_observer_summary", "runtime_gate_context"],
    "f_runner": ["write_live_depth_observer_summary_atomically", "write_observer_root_contract_atomically"],
    "g_reviewer": ["verify_source_evidence_manifest", "write_stage1_5g_review_manifest", "verify_stage1_5g_review_manifest"],
    "g_cli": ["build_stage1_5g_review_summary"],
    "h_loader": ["_validate_v2_closed_artifact_paths"],
}
evidence = {}
for name, path in source_paths.items():
    text = path.read_text(encoding="utf-8")
    missing = [token for token in required_tokens[name] if token not in text]
    if missing:
        raise SystemExit(f"STOP=contract_reality_missing:{name}:{','.join(missing)}")
    evidence[name] = {"path": str(path), "pre_task0_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "tokens": required_tokens[name], "mutable_predecessor_output": name in {"f_model", "f_summary", "f_runner", "g_reviewer", "g_cli", "h_loader"}}
lines = runbook.read_text(encoding="utf-8").splitlines(keepends=True)
matches = [line for line in lines if 'find "$LOCAL_EVIDENCE_ROOT" -type f -exec shasum -a 256' in line]
if len(matches) != 1:
    raise SystemExit("STOP=contract_reality_runbook_sealing_command_ambiguous")
command = matches[0]
(baseline / "runbook_sha256sums_sealing_command.sh").write_text(command, encoding="utf-8")
(baseline / "runbook_sha256sums_sealing_command.sha256").write_text(hashlib.sha256(command.encode("utf-8")).hexdigest() + "\n", encoding="utf-8")
evidence["runbook_sha256sums_sealing_command"] = {"runbook": str(runbook), "sha256": hashlib.sha256(command.encode("utf-8")).hexdigest(), "command": command.rstrip("\n")}
(baseline / "contract_reality.json").write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
PY
```

The Task-0 SHA-256 values for `f_model`, `f_summary`, `f_runner`, `g_reviewer` and `g_cli` are discovery evidence only: those files are intentionally mutable predecessor outputs and must not be compared byte-for-byte after their authorized Task. Immutable parent authorities, scanner bytes and the Task-0-extracted runbook sealing command remain exact-SHA gates. Before RED, each consuming Task instead checks the preceding Task's named post-task interface record below. Each record is machine-generated JSON, immediately reloaded and asserted from `dataclasses.fields`, `inspect.signature`, canonical serializer/writer output and the focused task test result; prose, token presence or a self-reported test success is not evidence. If a canonical model/serializer/writer, strict loader/verifier, field type/null semantics, manifest grammar or runbook command differs from this Plan's assumptions, stop and record exactly one Rule-12 classification: `BLOCKED_IMPLEMENTATION_DEFECT`, `BLOCKED_SCOPE_DRIFT`, or `BLOCKED_SPEC_DRIFT`.

3. Run targeted impact discovery; Graphify is advisory and direct source wins.

```bash
graphify query 'build_live_depth_observer_summary' --budget 1000 || true
graphify query 'load_stage1_5g_inputs' --budget 1000 || true
graphify query 'verify_stage1_5g_review_manifest' --budget 1000 || true
rg -n 'consumer_process_started_at_ms|runtime_gate_context|verify_source_evidence_manifest|write_stage1_5g_review_manifest|verify_stage1_5g_review_manifest' \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py
```

**Expected:** exact bytes, canonical source topology, verifier return shape and runbook sealing command match the recorded Reality Gate. **STOP:** mismatch, hidden required consumer, pre-existing mutable overlap, scanner failure, index/worktree mutation, or any Rule-12 classification without review; do not workaround.

## Task 1: Add The Minimal Stage 1.5F Process-Start Field

**Design invariants:** INV-02, INV-12.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`

**Consumes:** `LiveDepthObserverSummary`, `build_live_depth_observer_summary()`, `runtime_gate_context`, atomic summary writer and the existing full runner fixture.

**Produces:** one positive integer `consumer_process_started_at_ms`, captured once before the first possible summary write in `_main`, passed through every summary context and unchanged across every atomic `live_depth_observer_summary.json` publication by that process.

1. Write the pure serialization RED test in `test_stage1_5f_live_depth_observer_summary.py` and the once-per-process RED test next to `test_task5_consumer_summary_models_and_atomic_writer` / `test_runtime_main_publishes_bound_consumer_proof_atomically`:

```python
def test_summary_serializes_process_start_from_runtime_context():
    summary = build_live_depth_observer_summary(
        # reuse exact neighboring valid arguments
        runtime_gate_context={"consumer_process_started_at_ms": 1_700_000_000_123},
    )
    assert summary.to_dict()["consumer_process_started_at_ms"] == 1_700_000_000_123


def test_runtime_main_keeps_one_process_start_across_summary_writes(tmp_path, monkeypatch):
    summaries = run_existing_runtime_main_fixture_and_capture_summaries(tmp_path, monkeypatch)
    starts = [row["consumer_process_started_at_ms"] for row in summaries]
    assert all(type(value) is int and value > 0 for value in starts)
    assert len(set(starts)) == 1
    for summary in summaries:
        start = summary["consumer_process_started_at_ms"]
        heartbeat = summary["last_heartbeat_at_ms"]
        assert type(start) is int and start > 0
        assert type(heartbeat) is int and heartbeat > 0
        assert start <= heartbeat
```

Use the existing full runner fixture setup; do not create a second fixture framework or hand-build an F root. Exercise the normal poll, bootstrap-watermark, invalid-1.5D, missing/unsafe-1.5E and storage-startup-failure writer paths. The capture must observe each atomic `live_depth_observer_summary.json` publication, not merely its final bytes; diagnostic-only `storage_failure_diagnostic.json` is not a consumer summary.

2. Run RED:

```bash
set -euo pipefail
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  -k 'process_start or runtime_main_publishes_bound_consumer_proof or task5_consumer_summary'
```

**Expected:** RED because the model/context has no field.

3. Implement only this propagation:

```python
# model
consumer_process_started_at_ms: int = 0

# summary builder
consumer_process_started_at_ms=runtime_gate_context.get("consumer_process_started_at_ms", 0)

# runner, once in _main before StorageGuard startup failure can publish a summary
consumer_process_started_at_ms = int(time.time() * 1000)

# every build_live_depth_observer_summary runtime_gate_context
"consumer_process_started_at_ms": consumer_process_started_at_ms,
```

Every early-exit summary writer, including `_build_storage_failure_summary()`, must receive that same process-start value and publish a positive `last_heartbeat_at_ms >= start` at the atomic publication boundary; normal poll summaries retain their actual heartbeat semantics. The implementation must use the existing writer/model path, not a second summary serializer. The legacy default is not acceptance. Task 2 rejects missing/zero/bool/non-integer start fields. Do not add the field to root contract, runtime proof input, state JSONL, watermark, 1.5D output, config or history.

4. Run GREEN and lint:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py -k 'process_start or runtime_main_publishes_bound_consumer_proof or task5_consumer_summary'
.venv/bin/python -m ruff check src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py
```

5. After GREEN, write `$BASELINE_DIR/post_task1_contract.json`. It records only the post-Task-1 consumer facts that Task 2 consumes: `LiveDepthObserverSummary` contains `consumer_process_started_at_ms` with its exact annotation/default; `build_live_depth_observer_summary()` retains `runtime_gate_context`; the existing atomic summary writer call surface remains present; and the Task 1 runner capture proves one positive start and `start <= heartbeat` for every published consumer summary. Task 2 RED reads and verifies this record plus the actual post-Task-1 interface facts. It must not compare the Task-1-modified files to Task-0 whole-file SHA-256 values.

**STOP:** a test needs a root-contract/proof/latch/config change or uses a default to promote a malformed root.

## Task 2: Make Stage 1.5G Manifest-First Source Authority Fail Closed

**Design invariants:** INV-02, INV-03, INV-04, INV-05, INV-12.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py`

**Consumes:** `verify_source_evidence_manifest()`, `_load_json_file()`, `Stage1_5GInputBundle`, `canonical_json_dumps()` and the existing invalid `finish()` branch.

**Produces:** loader fields for the verified source-manifest SHA, validated summary-only authority projection and exact blockers; all failures return invalid before existing reducers.

1. Before RED, source the baseline and validate the `post_task1_contract.json` facts against the actual post-Task-1 model, summary builder, atomic writer and runner test surface. This is the Task 2 predecessor contract; the Task-0 whole-file SHA records are not equality gates for Task-1-modified files.

2. Add a test-local source sealing helper. It must call production `write_observer_root_contract_atomically()` and `write_live_depth_observer_summary_atomically()` using a test storage guard, then execute the exact command bytes frozen by Task 0 from `runbook_sha256sums_sealing_command.sh`:

```python
def seal_disposable_stage1_5f_source_root(root: Path) -> None:
    command = Path(os.environ["STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR"]).joinpath(
        "runbook_sha256sums_sealing_command.sh"
    ).read_text(encoding="utf-8")
    subprocess.run(
        ["sh", "-c", command],
        env={**os.environ, "LOCAL_EVIDENCE_ROOT": str(root)},
        check=True,
    )
    assert verify_source_evidence_manifest(root)[0] is True
```

The helper derives contract hash with `canonical_json_dumps`; it cannot handcraft a positive root-contract/summary dictionary. Assert the resulting manifest contains exactly one `SHA256SUMS` entry and is accepted by `verify_source_evidence_manifest()`. Do not impose a generic self-hash or all-zero rule: the Task-0-frozen project verifier is the authority for its self-entry. Before GREEN, assert the current runbook command's SHA-256 still equals `runbook_sha256sums_sealing_command.sha256`; Task 5 must preserve this command byte-for-byte. A negative test performs one declared mutation and reseals only when it must reach the later authority gate.

Convert existing source-root-crossing loader/integrity fixtures to this helper. Keep tests that exercise a local reducer only on its existing local helper; do not bypass the new source-root gateway with a hand-built positive root.

3. Write RED tests for the exact matrix:

```python
@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("consumer_runtime_attestation_verified", False, "source_runtime_attestation_unverified"),
        ("consumer_runtime_attestation_verified", "false", "source_runtime_attestation_verified_field_invalid"),
        ("consumer_runtime_attestation_compromised", True, "source_runtime_attestation_compromised"),
        ("consumer_runtime_attestation_compromised", "false", "source_runtime_attestation_compromised_field_invalid"),
    ],
)
def test_runtime_gate_boolean_precedence(field, value, expected):
    bundle = load_stage1_5g_inputs(canonical_root_with_one_summary_mutation(field, value))
    result = build_summary_from(bundle)
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert result["blockers"] == [expected]
```

Also test: canonical triad passes; static false/false -> static-unverified only; valid static unequal -> binding-invalid only; static malformed -> static-field-invalid only; missing/null/int each triad value -> its field-invalid only; missing/zero/bool/after-heartbeat start; malformed UUID; root-contract hash and shared identity mismatch; source-D triple, root mode/schema mismatch; missing/unreadable contract; copied root at new path; and the known compromised root. Spy on `validate_evidence_integrity`, `compute_coverage_metrics`, `validate_raw_snapshot_integrity`, and `compute_raw_snapshot_quarantine_metrics`: every authority failure makes zero calls.

4. Run RED:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py -k 'runtime_attestation or source_authority or source_manifest'
```

5. Implement one validator in the existing module:

```python
def validate_stage1_5f_source_runtime_authority(
    *, stage1_5f_root: Path, summary: dict[str, Any], source_evidence_manifest_sha256: str
) -> tuple[dict[str, Any], list[str]]:
    """Return only a validated summary projection and sorted fail-closed blockers."""
```

`load_stage1_5g_inputs()` calls `verify_source_evidence_manifest(root)` before parsing summary/contract. Only when valid, parse each once, validate and attach the SHA/projection/blockers to the existing bundle, then load reducer inputs. The validator uses canonical root-contract JSON SHA, cross-artifact equality for root ID/startup SHA/runtime manifest SHA, exact shared static bool equality, summary-only UUID/start/heartbeat/runtime fields, and root-only schema/root-mode/source-D triple. Use `type(value) is bool` and the approved lowercase UUID/SHA grammars. Ignore root-contract extra mutable fields. Apply Section 5.4 exclusive precedence; no `.get(..., default)`, truthiness, coercion, Git, mtime, review-clock freshness or path-derived root ID.

Modify `build_stage1_5g_review_summary()` so any source manifest/runtime loader blocker returns existing invalid output before watermark/integrity/coverage/raw/quarantine reducers. Pass the loader's verified manifest SHA to `_with_stage1_5g_audit_fields()`; this preserves the v2 review-ID formula without rereading authority.

6. Run GREEN:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py -k 'runtime_attestation or source_authority or source_manifest'
```

7. After GREEN, write `$BASELINE_DIR/post_task2_contract.json` for Task 3: exact `Stage1_5GInputBundle` authority fields, `validate_stage1_5f_source_runtime_authority()` signature/return shape, manifest-first call ordering and the existing v2 summary/review-ID preservation result. Task 3 RED validates those post-Task-2 facts and must not compare Task-2-modified files to their Task-0 whole-file SHA-256 values.

8. Perform the known compromised-root diagnostic rerun only after taking a before snapshot from `historical_source_root.json`; direct output only to a fresh allowed disposable review root. Immediately compare the historical root's manifest SHA-256, directory/file entry count and every shared inventory record to Task 0, then repeat the same comparison in Task 6. This Plan neither reads nor writes historical 1.5G/1.5H reports; tests use `tmp_path`, and no path below `data/external_signal_shadow/local_evidence/` may be created, replaced or removed.

```bash
: "${STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR:?source Task 0 reopen-baseline.sh}"
BASELINE_DIR="$STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR"
HISTORICAL_SOURCE_ROOT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["root"])' "$BASELINE_DIR/historical_source_root.json")"
DIAGNOSTIC_OUT="data/external_signal_shadow/stage1_5g/reviews/$(date -u +%Y%m%dT%H%M%SZ)_runtime_gate_diagnostic"
test ! -e "$DIAGNOSTIC_OUT" || { echo STOP=diagnostic_output_root_exists >&2; exit 1; }
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py --stage1-5f-output-root "$HISTORICAL_SOURCE_ROOT" --output-root "$DIAGNOSTIC_OUT"
PYTHONPATH=src:. .venv/bin/python "$BASELINE_DIR/fingerprint_historical_source.py" check "$BASELINE_DIR/historical_source_root.json" "$HISTORICAL_SOURCE_ROOT"
```

**Expected:** canonical source passes; every negative has exactly the approved blocker; the known compromised root is invalid and its source inventory is unchanged. **STOP:** defaulting a missing field, reading runtime state from contract, recomputing source root ID from path, changing source bytes, changing the frozen sealing command, or accessing historical 1.5G/1.5H artifacts.

## Task 3: Seal Positive Gate Proof And Review Manifest V3

**Design invariants:** INV-06, INV-07, INV-09, INV-12.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Modify: `scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py`

**Produces:** exact v1 gate proof only for an authority-valid quarantined pass, and a final v3 manifest with exact five artifacts.

1. Before RED, validate `post_task2_contract.json` against the actual post-Task-2 bundle fields, validator signature/return shape and manifest-first loader behavior. This is the Task 3 predecessor contract; it deliberately replaces Task-0 whole-file SHA equality for Task-2-modified files.

2. Write RED tests using the existing quarantined-pass CLI fixture:

```python
EXPECTED_GATE_KEYS = {
    "schema_version", "source_runtime_attestation_gate_verified",
    "stage1_5g_review_id", "source_evidence_manifest_sha256",
    "consumer_process_instance_id", "consumer_root_id", "consumer_process_started_at_ms",
    "consumer_startup_commit_sha", "consumer_root_contract_sha256",
    "consumer_runtime_manifest_sha256", "consumer_static_attestation_verified",
    "consumer_runtime_attestation_verified", "consumer_runtime_attestation_compromised",
    "source_runtime_attestation_authority_sha256",
}

def test_v3_manifest_is_final_after_positive_gate_proof(tmp_path, monkeypatch):
    root = run_existing_quarantined_pass_cli_fixture(tmp_path, monkeypatch)
    assert set(load_json(root / "stage1_5g_runtime_attestation_gate.json")) == EXPECTED_GATE_KEYS
    assert load_json(root / "stage1_5g_review_manifest.json")["schema_version"] == 3
```

Cover proof self-hash/linkage/key/artifact mutations, v2 manifest and interruption after every artifact before manifest. Freeze the parent output matrix exactly:

```text
source-authority failure -> existing invalid-main-summary behavior only; no proof and no v3 manifest
quality-invalid diagnostic closure -> preserve its existing v2 diagnostic artifacts/manifest; no proof and never consumer-eligible
clean-only output -> preserve existing clean output; no proof and no v3 consumer bundle
authority-valid quarantined pass -> proof, then final v3 manifest
```

The test distinguishes `no v3 promotion manifest` from `no parent diagnostic manifest`; it must not delete or change any existing diagnostic evidence grammar. Re-run the existing multi-symbol golden fixture and assert v2 summary/quarantine/review-ID values are unchanged.

For semantic-linkage coverage, start from one canonical proof/manifest pair and mutate each copied authority field separately: `consumer_process_instance_id`, `consumer_root_id`, `consumer_process_started_at_ms`, `consumer_startup_commit_sha`, `consumer_root_contract_sha256`, `consumer_runtime_manifest_sha256`, `consumer_static_attestation_verified`, `consumer_runtime_attestation_verified`, `consumer_runtime_attestation_compromised`, `stage1_5g_review_id` and `source_evidence_manifest_sha256`. For each fixture, after the one semantic mutation: (1) recompute and rewrite the proof self-hash; (2) recompute that proof artifact's manifest `sha256`; (3) recompute that proof artifact's manifest `byte_count`; (4) preserve every unrelated proof, artifact and manifest field; and (5) assert the resulting manifest is structurally/hash/size valid before asserting Stage 1.5H rejection. The acceptance condition is `outer artifact closure = PASS` and `semantic proof-to-summary linkage = FAIL`; an outer hash or byte-count rejection does not satisfy this test.

3. Run RED:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py -k 'manifest or runtime_attestation_gate or quarantine'
```

4. Implement direct existing-module extensions:

```python
def write_stage1_5g_runtime_attestation_gate(
    review_output_root: Path, *, summary: dict[str, Any], source_authority: dict[str, Any]
) -> Path:
    # exact 14 keys; authority SHA is canonical JSON SHA after omitting only itself
```

The writer accepts only valid Task 2 projection plus `decision == "stage1_5g_depth_evidence_quarantined_pass"`, `quarantined_depth_evidence_pass is True`, `clean_depth_evidence_pass is False`. Upgrade existing manifest writer/verifier to `schema_version == 3`, exact five artifact entries and existing `relative_path`/`sha256`/`byte_count` grammar. The verifier validates proof keys, types, exact true/true/false triad, self-hash and summary linkage. Any manifest/proof failure maps to `stage1_5h_runtime_attestation_gate_missing_or_invalid`.

CLI order is fixed:

```text
reducers -> quarantine artifacts -> main summary -> markdown -> gate proof -> manifest last
```

No partial write can be a closed consumer bundle. Do not change summary/quarantine v2 schema, review ID, JSONL schema or formulas.

5. Run GREEN/lint:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
.venv/bin/python -m ruff check src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
```

6. After GREEN, write `$BASELINE_DIR/post_task3_contract.json` for Task 4. It records the exact v3 manifest schema, the five artifact-entry grammar including `relative_path`/`sha256`/`byte_count`, the gate-proof verifier signature/return mapping and the positive-only CLI order. Task 4 RED validates those facts against post-Task-3 source and canonical fixture output; it must not compare Task-3-modified files to Task-0 whole-file SHA-256 values.

**STOP:** v2 output changes, proof for clean/invalid data, manifest written before proof, or partial output accepted.

## Task 4: Require V3 Gate Proof In Stage 1.5H V2 Admission

**Design invariants:** INV-07, INV-08, INV-12.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py`

**Consumes:** existing adjacent-manifest discovery in `_validate_v2_closed_artifact_paths()` and Task 3 verifier.

1. Before RED, validate `post_task3_contract.json` against the actual v3 manifest verifier API and a canonical sealed fixture. This is the Task 4 predecessor contract; it must fail if a field/type/return mapping differs, but not merely because Task 3 correctly changed its source bytes.

2. Replace every positive cross-boundary v2 fixture in both 1.5H test modules with Task 3's canonical v3 writer path. Keep deliberately malformed legacy/v2 fixtures only for rejection assertions. Local pure proxy-metric tests may retain local structures only if they do not cross the 1.5G artifact boundary.

3. Add RED tests:

```python
def test_v2_loader_rejects_pre_hotfix_manifest_without_gate_proof(tmp_path):
    result = build_stage1_5h_v2_event_bundle_reports(canonical_v2_bundle_with_manifest_version(2, tmp_path))
    assert result["decision"] == "stage1_5h_v2_event_bundle_input_rejected"
    assert result["report_generation_allowed"] is False
    assert result["blockers"] == ["stage1_5h_runtime_attestation_gate_missing_or_invalid"]


def test_v2_loader_accepts_only_canonical_v3_quarantined_bundle(tmp_path):
    result = build_stage1_5h_v2_event_bundle_reports(canonical_task3_sealed_quarantined_bundle(tmp_path))
    assert result["decision"] == "stage1_5h_v2_event_bundle_reports_ready"
```

Test deleted/tampered/malformed/unlinked proof, unexpected proof key, proof hash mismatch and each v3 artifact hash mismatch. Confirm static-proxy outputs are unchanged after valid admission. Confirm legacy v1/N=1 never claims runtime-attested/post-hotfix ledger status.

4. Run RED then implement only `_validate_v2_closed_artifact_paths()` admission change: call upgraded verifier before existing source-of-truth checks and map every manifest/proof failure to exactly `stage1_5h_runtime_attestation_gate_missing_or_invalid`. Do not add CLI arguments: current adjacent-manifest/path containment is the binding. Preserve all existing v2 projection, proxy, rendering and output bundle logic.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py
.venv/bin/python -m ruff check src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py
```

**Expected:** only sealed v3 quarantined bundles reach existing report logic; every reject remains read-only with all flags false. **STOP:** static-proxy/report/bundle/legacy behavior needs modification or v2/no-proof becomes admissible.

## Task 5: Replace Runbook Writer Check With Exact /proc Gate

**Design invariants:** INV-10, INV-11, INV-12.

**Files:**
- Modify: `docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md`

**Produces:** one `set -euo pipefail` deployment block where checkout follows only an exact zero-writer `/proc` proof.

1. Add an inline standard-library Python inspector before checkout, enclosed in these exact unique runbook markers: `<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_BEGIN -->` and `<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_END -->`. For target `/root/crypto-alpha-lab`, it reads `/proc/<pid>/cwd` and NUL-delimited `/proc/<pid>/cmdline`, resolves relative argv paths against cwd, prints matching PID/cwd/argv and returns nonzero on inspection error. A writer matches only when cwd resolves to target and argv contains either exact resolved path:

```text
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
```

Do not use `grep`, `ps` parsing, session name, basename or `|| true` as zero-writer proof.

2. Replace split stop/checkout instructions with one `set -euo pipefail` deployment block, enclosed in `<!-- STAGE1_5D_1_5F_ZERO_WRITER_DEPLOYMENT_BEGIN -->` and `<!-- STAGE1_5D_1_5F_ZERO_WRITER_DEPLOYMENT_END -->`, using the fixed sequence:

```text
request D/F tmux stop
-> inspect once per second for at most 30 seconds
-> final exact count == 0
-> git fetch / checkout DEPLOY_COMMIT
-> assert HEAD == DEPLOY_COMMIT, clean protected worktree, new RUN_ID and fresh roots
```

Final nonzero count must print `STOP=stage1_5d_1_5f_writer_still_running`; checkout must be lexically after the successful final inspection in the same `set -euo pipefail` block. Keep producer-disabled ordinary restart. For separately authorized `configured_enabled=true`, keep parent E0 -> E1 -> E2 verbatim; no D -> F simplification.

3. The marked production fence must expose `inspect_writers(proc_root: Path, target_root: Path) -> list[dict[str, object]]`; production invokes it with `Path("/proc")`. The verification command reads the actual runbook, extracts only the bytes between the two inspector markers, compiles and executes those extracted bytes in an isolated namespace, then constructs a temporary fake proc tree. It asserts: both writer scripts in target cwd match; the same argv in a wrong cwd does not; an inaccessible process raises inspection failure; and a nonzero matching count takes the STOP branch before checkout. It must not access VPS `/proc`, stop sessions, import project code or reproduce the inspector in a second source string.

4. Verify text contract locally only:

```bash
: "${STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR:?source Task 0 reopen-baseline.sh}"
python3 - "$STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR" docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md <<'PY'
import hashlib
from pathlib import Path
import sys
baseline = Path(sys.argv[1])
text = Path(sys.argv[2]).read_text(encoding="utf-8")
for token in ("/proc/<pid>/cwd", "/proc/<pid>/cmdline", "run_stage1_5d_live_event_source_smoke_collector.py", "run_stage1_5f_live_depth_observer.py", "STOP=stage1_5d_1_5f_writer_still_running", "E0", "E1", "E2", "STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_BEGIN", "STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_END", "STAGE1_5D_1_5F_ZERO_WRITER_DEPLOYMENT_BEGIN", "STAGE1_5D_1_5F_ZERO_WRITER_DEPLOYMENT_END"):
    assert token in text, token
def extract(begin, end):
    start = text.index(begin) + len(begin)
    stop = text.index(end, start)
    return text[start:stop]
inspector = extract("<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_BEGIN -->", "<!-- STAGE1_5D_1_5F_ZERO_WRITER_INSPECTOR_END -->")
deployment = extract("<!-- STAGE1_5D_1_5F_ZERO_WRITER_DEPLOYMENT_BEGIN -->", "<!-- STAGE1_5D_1_5F_ZERO_WRITER_DEPLOYMENT_END -->")
assert "def inspect_writers" in inspector
compile(inspector.replace("```python", "").replace("```", ""), "runbook-inspector", "exec")
assert deployment.index("STOP=stage1_5d_1_5f_writer_still_running") < deployment.index('git checkout "$DEPLOY_COMMIT"')
assert "set -euo pipefail" in deployment
sealing = [line for line in text.splitlines(keepends=True) if 'find "$LOCAL_EVIDENCE_ROOT" -type f -exec shasum -a 256' in line]
assert len(sealing) == 1
assert hashlib.sha256(sealing[0].encode("utf-8")).hexdigest() == (baseline / "runbook_sha256sums_sealing_command.sha256").read_text().strip()
print("CHECK_OK=stage1_5d_1_5f_zero_writer_runbook_contract")
PY
```

The corresponding RED/GREEN test is an extracted-byte test, not this static check: it executes the compiled `inspect_writers` from the actual marked fence against the complete fake `/proc` matrix and extracts the actual deployment block into a temporary file for `bash -n`. It also asserts that the nonzero result branch precedes and guards checkout. Freeze the unchanged Task-0 `runbook_sha256sums_sealing_command.sha256` before and after this documentation edit.

**STOP:** any need for heuristic process matching, checkout before proof, E0/E1/E2 simplification or deployment action.

## Task 6: Final Regression, Safety, Scope And Completion Audit

**Design invariants:** INV-01 through INV-12.

All commands in this Task begin with:

```bash
: "${STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR:?source Task 0 reopen-baseline.sh}"
BASELINE_DIR="$STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR"
test -d "$BASELINE_DIR" || { echo STOP=baseline_dir_missing >&2; exit 1; }
test "$(git rev-parse HEAD)" = "$(cat "$BASELINE_DIR/head")" || { echo STOP=baseline_head_changed >&2; exit 1; }
```

1. Run focused suites and lint:

```bash
set -euo pipefail
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py
.venv/bin/python -m ruff check \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py
```

2. Rehash Task 0 authorities and prove L0 flags remain false:

```bash
set -euo pipefail
for authority in \
  'docs/designs/2026-09-08-external-signal-shadow-lab-stage1-5g-runtime-attestation-evidence-gate-hotfix-design_CN.md f30414c4fc6693844c415e5cb395c1fb2f5258bf4e8ba8ea332e53c3e9f0e7df' \
  'docs/designs/2026-08-10-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-git-ancestry-attestation-design_CN.md 28cd9e55540a3eccfd24cca3598acdb7959d02407ff54edf1045765cba5b2f36' \
  'docs/plans/2026-08-10-external-signal-shadow-lab-stage1-5d-1-5f-git-ancestry-attestation-implementation-plan_CN.md 65a47168af6f1e9ba11f8003cace93962a5986fafae53577996db360d4defe7e' \
  'docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-design-delta_CN.md 3528d4b5f90ee8b7bd142773b1c35a1a51b2ea09242224eaed2ab10df69c5c8b' \
  'docs/plans/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-implementation-plan_CN.md 47f9728b8a17e815e836fae837c038a0bc8ae06c6593d9ae0280741997b6da67' \
  'docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-design-delta_CN.md ec936020cba1ca26a2709f02996ad70bcf05d9457bb1e741ac6d40685269f812' \
  'docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md 7bf59a14a230da4071bde7acafc0b2022de52c313f47f389eadd293b162dacc4'
do
  set -- $authority
  test "$(shasum -a 256 "$1" | awk '{print $1}')" = "$2" || {
    echo STOP=revision_authority_incomplete >&2
    exit 1
  }
done
ACTUAL_PLAN_SHA256="$(shasum -a 256 docs/plans/2026-09-08-external-signal-shadow-lab-stage1-5g-runtime-attestation-evidence-gate-hotfix-implementation-plan_CN.md | awk '{print $1}')"
test "$ACTUAL_PLAN_SHA256" = "$(cat "$BASELINE_DIR/approved_plan.sha256")" || { echo STOP=plan_bytes_changed_after_task0 >&2; exit 1; }
test "$ACTUAL_PLAN_SHA256" = "$(cat "$BASELINE_DIR/expected_approved_plan.sha256")" || { echo STOP=stage1_5g_runtime_attestation_gate_plan_bytes_not_authorized >&2; exit 1; }
python3 - <<'PY'
from configs import base
from src.risk.limits import RiskLimits
assert base.RISK_LIVE_TRADING_ENABLED is False
assert RiskLimits.live_trading_enabled is False
print("CHECK_OK=L0_permissions_false")
PY
git diff --check
git diff -- configs/base.py
git diff --cached -- configs/base.py
shasum -a 256 --check "$BASELINE_DIR/frozen_design_plan.sha256"
test "$(shasum -a 256 "$BASELINE_DIR/runbook_sha256sums_sealing_command.sh" | awk '{print $1}')" = "$(cat "$BASELINE_DIR/runbook_sha256sums_sealing_command.sha256")" || { echo STOP=frozen_runbook_sealing_command_record_corrupt >&2; exit 1; }
python3 - "$BASELINE_DIR" <<'PY'
import hashlib
import sys
from pathlib import Path
baseline = Path(sys.argv[1])
text = Path("docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md").read_text(encoding="utf-8")
matches = [line for line in text.splitlines(keepends=True) if 'find "$LOCAL_EVIDENCE_ROOT" -type f -exec shasum -a 256' in line]
assert len(matches) == 1
assert hashlib.sha256(matches[0].encode("utf-8")).hexdigest() == (baseline / "runbook_sha256sums_sealing_command.sha256").read_text().strip()
print("CHECK_OK=frozen_runbook_sealing_command_unchanged")
PY
HISTORICAL_SOURCE_ROOT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["root"])' "$BASELINE_DIR/historical_source_root.json")"
PYTHONPATH=src:. .venv/bin/python "$BASELINE_DIR/fingerprint_historical_source.py" check "$BASELINE_DIR/historical_source_root.json" "$HISTORICAL_SOURCE_ROOT"
```

3. Run this exact scope proof. It preserves every baseline dirty/untracked path outside the whitelist by both porcelain status and content digest, forbids any new/unlisted path, and freezes the entire Git index because this Plan has no staging authority:

```bash
python3 - "$BASELINE_DIR" <<'PY'
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

allowed = {
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py",
    "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py",
    "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py",
    "scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py",
    "src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py",
    "tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py",
    "tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py",
    "tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py",
    "tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py",
    "docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md",
}


def fingerprint(path: Path) -> dict[str, str | int | None]:
    if not path.exists() and not path.is_symlink():
        return {"type": "missing"}
    st = os.lstat(path)
    if stat.S_ISREG(st.st_mode):
        return {"type": "regular", "mode": st.st_mode, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    if stat.S_ISLNK(st.st_mode):
        return {"type": "symlink", "mode": st.st_mode, "target": os.readlink(path)}
    return {"type": "other", "mode": st.st_mode}


def porcelain() -> dict[str, str]:
    raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    )
    records = raw.split(b"\0")
    out: dict[str, str] = {}
    index = 0
    while index < len(records) and records[index]:
        record = records[index]
        code = record[:2].decode("ascii")
        path = record[3:].decode("utf-8", "surrogateescape")
        out[path] = code
        index += 1
        if "R" in code or "C" in code:
            out[records[index].decode("utf-8", "surrogateescape")] = code
            index += 1
    return out


baseline_dir = Path(sys.argv[1])
baseline = json.loads((baseline_dir / "scope_baseline_v2.json").read_text())
current_status = porcelain()
current_fingerprint = {path: fingerprint(Path(path)) for path in current_status}
for path in sorted(set(baseline["status"]) | set(current_status)):
    unchanged = (
        baseline["status"].get(path) == current_status.get(path)
        and baseline["fingerprint"].get(path) == current_fingerprint.get(path)
    )
    if not unchanged and path not in allowed:
        raise SystemExit(f"STOP=scope_or_preexisting_bytes_changed:{path}")
current_index = subprocess.check_output(["git", "ls-files", "-s", "-z"])
index_sha = hashlib.sha256(current_index).hexdigest()
expected_index_sha = (baseline_dir / "index.sha256").read_text().split()[0]
if index_sha != expected_index_sha:
    raise SystemExit("STOP=git_index_changed")
print("CHECK_OK=stage1_5g_runtime_attestation_gate_scope")
PY
```

4. Run the final scanner gate with `TASK_LABEL=final` using the Required Execution Governance command. Require scanner SHA equality, process return code `0`, no `ERROR`, no new normalized warning identity versus Task 0 and a complete external disposition for every surviving warning.

5. Freeze the final worktree before audit: record final `HEAD`, porcelain, `git diff --binary`, `git diff --cached --binary`, Git index SHA-256, current Plan SHA, Design SHA, scanner output/exit code, Task-0 baseline path and all verification commands/results in the external Task Execution Report. Then hand an independent read-only auditor only this factual packet:

```text
approved Plan path and exact SHA-256
approved Design path and exact SHA-256
BASE_SHA and Task-0 baseline directory
Allowed Change Scope
known unresolved blockers, if any
```

The executor must not include a completion claim, test-success narrative, invariant conclusion or recommendation. Under the `Blind-First Independent Completion Audit` protocol, the independent auditor runs `.agent/skills/audit-plan-completion` against current source, parent bytes, actual diff, tests and scanner evidence, then returns its provisional verdict. No executor or Plan-generated mutation is allowed after this handover or verdict. Only an independent `complete` verdict closes implementation; it does not authorize commit, VPS deployment, runtime or network activity.

**STOP:** failing test/lint/authority/safety/scope/index/scanner proof, changed config/historical byte/runbook sealing command, unlisted path, new permission, missing scanner ledger, unauthenticated Plan bytes, post-handoff mutation, or non-`complete` independent completion audit.

## Explicit Non-Claims

- This proves runtime provenance for future 1.5G quarantined-pass bundles only. It does not prove tradable alpha, execution feasibility, clean-only admission, family-level evidence or historical-root trustworthiness.
- A valid 1.5H report remains a read-only static proxy, not a `SignalCandidate`, `TradeIntent`, order, paper-trading result or live-trading authorization.
- Completion is not VPS deployment authorization. Deployment requires separate authorization, the Task 5 zero-writer gate and a fresh post-checkout root.
