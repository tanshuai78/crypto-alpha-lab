# Stage 1.5H V2 Event-Bundle Per-Symbol Read-Only Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Any modification under `src/`, `scripts/`, or `tests/` requires this Plan's approval and explicit user authorization.

**Goal:** 为完整、manifest-bound 的 Stage 1.5G v2 quarantined bundle 生成每个 `event_symbol_id` 一份独立的本地只读 JSON/Markdown static-proxy report，以及一个不含聚合指标的 sealed event directory。

**Architecture:** 在现有 `stage1_5h_read_only_report_generator.py` 内新增最小的 v2 event-bundle validator、prepared-report builder、writer 和 manifest verifier；复用现有 `load_stage1_5h_inputs`、`verify_stage1_5g_review_manifest`、canonical JSON、static-proxy formula 与 blocker helper。新增独立 CLI，避免改变 legacy single-symbol CLI、其输出格式或其拒绝 multi-symbol 的行为。

**Tech Stack:** Python standard library (`dataclasses`, `hashlib`, `json`, `os`, `pathlib`, `tempfile`)、pytest、ruff；不新增依赖、网络、数据库、队列、并发、VPS 或交易接口。

## Global Constraints

- 只接受 `schema_version = 2`、`decision = stage1_5g_depth_evidence_quarantined_pass`、`clean_depth_evidence_pass = false`、`quarantined_depth_evidence_pass = true` 的完整 closed bundle。
- `raw_ids` 必须原样验证为 sorted、unique、64 位 lowercase hex；禁止 `set()`、sort 或任何 consumer-side repair。
- `event_level_decisions` 是唯一身份来源；JSONL 只验证 membership、symbol 与 count，不重算 quality metric，也不新增 raw-row duplicate gate。
- `per_symbol_quarantine_metrics[s].quarantined_depth_quality` 是唯一数值质量来源；`effective_friction_floor_bps = max(observed, configured)`，不得 double-count。
- 任一上游语义矛盾全局 reject；不得生成 partial authoritative bundle。
- JSON 是语义 authority；Markdown 是 deterministic projection；event directory 必须使用本 Plan 定义的 exact provenance/status schema，且不得聚合 spread、slippage、depth、availability、score 或 ranking。
- 输出 root 必须 fresh、local-only、且不在 Stage 1.5F source root 或 Stage 1.5G review root 内；final manifest 是唯一 seal authority。
- `execution_feasibility_claim_allowed`、`alpha_interpretation_allowed`、`trade_signal_allowed`、`paper_trading_allowed`、`live_trading_allowed`、`execution_engine_allowed`、`private_endpoint_allowed`、`api_key_allowed`、`order_endpoint_allowed` 必须始终为 `false`。
- 不修改 `configs/base.py`、Stage 1.5D/F/G producer、legacy Stage 1.5H CLI、历史 v1 artifact 或 runtime/VPS state。

---

## Plan Status

- **状态:** `draft_for_review`
- **Review Mode:** `closure_confirmation`
- **Implementation authorization:** `false`
- **Deployment authorization:** `false`
- **Runtime action:** 禁止。此 Plan 只定义实现，不得启动、停止或重启 Stage 1.5D/F/1.6D 进程。

## Frozen Authority

| Authority | SHA-256 |
| --- | --- |
| Approved Stage 1.5H v2 Design Delta | `ec936020cba1ca26a2709f02996ad70bcf05d9457bb1e741ac6d40685269f812` |
| Approved Stage 1.5H v2 Governance Review | `7bf59a14a230da4071bde7acafc0b2022de52c313f47f389eadd293b162dacc4` |
| Approved Stage 1.5G multi-symbol denominator Design Delta | `3528d4b5f90ee8b7bd142773b1c35a1a51b2ea09242224eaed2ab10df69c5c8b` |
| Legacy Stage 1.5H static-proxy Design | `fc6a3b5bff51d15531b4fb61c30b1d8d2ef899680bba4621f3f17e03b6002c42` |
| Legacy Stage 1.5H governance review | `8058bf63eda822b6e93c65dc41afb29230e47551f0aa7e4a85bf53c19d51a3e8` |
| Planning baseline commit | `551b1fa19ce6f8ec432dd59bb35b2dd0c329611b` |
| Frozen five-symbol Stage 1.5G review manifest | `35a1ce9dc0ad02738ab26e97c9fd36ef860d3533dc8626c2f527e7ff1f4ecdf0` |
| Frozen source evidence manifest | `46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918` |

The executor must stop if any authority SHA differs. The approved Plan SHA is intentionally absent in this draft. After review approval, record it outside the repository as `APPROVED_PLAN_SHA` and check it before Task 1.

## Allowed Change Scope

**Allowed implementation paths:**

- `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- `scripts/external_signal_shadow/review_stage1_5h_v2_event_bundle_per_symbol_report.py`

**Allowed verification paths:**

- `tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py`

**Allowed documentation paths:**

- none during implementation; this Plan and its authorities are immutable after approval.

**Allowed generated/runtime artifacts, never committed:**

- pytest `tmp_path` roots.
- `data/external_signal_shadow/stage1_5h/reports/stage1_5h_v2_plan_regression_*/**` generated only by Task 5 local regression.
- external baseline/provenance records and audit output.

**Affected but unchanged:**

- `scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py`
  - compatibility evidence: `tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py`.
- `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`
  - compatibility evidence: its complete test file remains green without edits.
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
  - compatibility evidence: reuse only `verify_stage1_5g_review_manifest`; `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py` remains green.
- `configs/base.py`
  - compatibility evidence: no threshold/config diff; existing static-proxy regression remains green.

**Forbidden:**

- Any mutation outside the allowlist, including Stage 1.5D/F/G writers, configs, legacy CLI/tests, Stage 1.6, documentation authorities, or historical/review evidence roots.
- Any threshold/taxonomy change, source artifact rewrite, migration, overwrite, delete, full-repository formatter/autofix, `git clean`, `git reset --hard`, or unrelated refactor.
- Any execution feasibility, alpha/PIT/replay conclusion, paper/live trading, exchange/private API, API-key, order-endpoint, VPS, process or deployment change.

## Change Map

| File | Responsibility | Required change |
| --- | --- | --- |
| `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py` | Existing local read-only input/metric helpers | Add v2 bundle-specific validation, per-symbol report preparation, root-confined writing, atomic final manifest and manifest verification. Preserve legacy public functions and outputs. |
| `scripts/external_signal_shadow/review_stage1_5h_v2_event_bundle_per_symbol_report.py` | New v2 command boundary | Parse exact closed-bundle/governance/root arguments; call new writer; return nonzero without final manifest on reject. |
| `tests/research/...v2_event_bundle_per_symbol_report.py` | Contract tests | Synthetic complete v2 bundle plus closed-bundle, identity, partition, status, static-proxy, persistence and safety tests. |
| `tests/scripts/...v2_event_bundle_per_symbol_report.py` | CLI contract tests | Success output layout, reject behavior and legacy isolation tests. |

## Invariant and Proof Coverage

| Design invariant | Plan task and evidence |
| --- | --- |
| INV-H2-01 governance authority | Tasks 0 and 2 validate exact new governance artifact/markers; legacy governance remains unaffected. |
| INV-H2-02 closed v2 quarantined input | Tasks 1--2 validate schema, decision, manifest, exact artifact paths/hashes and embedded/standalone canonical equality. |
| INV-H2-03 formal identity map | Tasks 1--2 validate `raw_ids`, UTF-8 canonical formal-ID hash and `event_level_decisions` exact mapping. |
| INV-H2-04 JSONL partitions | Tasks 1--2 validate member/symbol/count/phase/reason consistency; no duplicate-row gate. |
| INV-H2-05 static-proxy reuse | Tasks 1--2 reuse existing formula/blockers and compare v2 N=1 fields with legacy output. |
| INV-H2-06 global reject/status separation | Tasks 1--2 reject all upstream contradictions; report only legal static-proxy blockers. |
| INV-H2-07 one report per ID/no aggregate | Tasks 1 and 3 verify exact report set and non-aggregating directory. |
| INV-H2-08 path safety | Tasks 1 and 3 reject unsafe IDs, symlinks, collisions and root escapes. |
| INV-H2-09 manifest lifecycle | Tasks 1 and 3 test absent/incomplete/invalid/sealed roots and atomic manifest-last behavior. |
| INV-H2-10 JSON authority/Markdown projection | Tasks 1 and 3 check deterministic Markdown projection and forbidden authority terms. |
| INV-H2-11 legacy compatibility | Tasks 2 and 4 run existing generator/CLI suites unchanged and N=1 field equivalence. |
| INV-H2-12 all permissions false | Tasks 1--5 assert all new outputs and reject paths retain false safety fields. |

## Task 0: Authority, Baseline and Evidence Preflight

**Design invariants:** INV-H2-01, INV-H2-02, INV-H2-12.

**Files:** No repository file changes.

- [ ] **Step 1: Freeze authority, baseline and pre-existing worktree provenance outside the repository.**

```bash
set -euo pipefail
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export BASE_SHA="$(git rev-parse HEAD)"
git merge-base --is-ancestor 551b1fa19ce6f8ec432dd59bb35b2dd0c329611b "$BASE_SHA" || {
  echo 'STOP: planning baseline is not an ancestor of the implementation baseline' >&2
  exit 1
}
PLANNING_BASE_SHA=551b1fa19ce6f8ec432dd59bb35b2dd0c329611b
PROTECTED_BASELINE_PATHS=(
  configs/base.py
  src/research/external_signal_shadow/safety.py
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  scripts/external_signal_shadow/review_stage1_5h_v2_event_bundle_per_symbol_report.py \
  scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py
)
git diff --quiet "$PLANNING_BASE_SHA" HEAD -- "${PROTECTED_BASELINE_PATHS[@]}" || {
  echo 'STOP: protected implementation/compatibility surface drifted after planning baseline; re-inspect and re-plan' >&2
  exit 1
}
for path in "${PROTECTED_BASELINE_PATHS[@]}"; do
  test -z "$(git status --porcelain=v1 --untracked-files=all -- "$path")" || {
    echo "STOP: protected path is pre-existing dirty/untracked: $path" >&2
    exit 1
  }
done
export DESIGN=docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-design-delta_CN.md
export GOVERNANCE=docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md
export UPSTREAM_DESIGN=docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-design-delta_CN.md
export LEGACY_DESIGN=docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-static-execution-proxy-design_CN.md
export LEGACY_GOVERNANCE=docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md
export PLAN=docs/plans/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-implementation-plan_CN.md
test "$(shasum -a 256 "$DESIGN" | awk '{print $1}')" = ec936020cba1ca26a2709f02996ad70bcf05d9457bb1e741ac6d40685269f812
test "$(shasum -a 256 "$GOVERNANCE" | awk '{print $1}')" = 7bf59a14a230da4071bde7acafc0b2022de52c313f47f389eadd293b162dacc4
test "$(shasum -a 256 "$UPSTREAM_DESIGN" | awk '{print $1}')" = 3528d4b5f90ee8b7bd142773b1c35a1a51b2ea09242224eaed2ab10df69c5c8b
test "$(shasum -a 256 "$LEGACY_DESIGN" | awk '{print $1}')" = fc6a3b5bff51d15531b4fb61c30b1d8d2ef899680bba4621f3f17e03b6002c42
test "$(shasum -a 256 "$LEGACY_GOVERNANCE" | awk '{print $1}')" = 8058bf63eda822b6e93c65dc41afb29230e47551f0aa7e4a85bf53c19d51a3e8
: "${APPROVED_PLAN_SHA:?STOP: set exact approved Plan SHA after plan approval}"
test "$(shasum -a 256 "$PLAN" | awk '{print $1}')" = "$APPROVED_PLAN_SHA"
export PROVENANCE_DIR="${TMPDIR:-/tmp}/stage1_5h_v2_event_bundle_provenance_${BASE_SHA}"
mkdir -p "$PROVENANCE_DIR"
printf '%s\n' "$BASE_SHA" > "$PROVENANCE_DIR/base_sha"
git status --porcelain=v1 --untracked-files=all -z > "$PROVENANCE_DIR/status_before.z"
git diff > "$PROVENANCE_DIR/diff_before.patch"
git diff --cached > "$PROVENANCE_DIR/diff_cached_before.patch"
cat > "$PROVENANCE_DIR/capture_preexisting_paths.py" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def status_by_path() -> dict[str, str]:
    chunks = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all", "-z"]
    ).split(b"\0")
    rows: dict[str, str] = {}
    index = 0
    while index < len(chunks) - 1:
        row = chunks[index]
        index += 1
        status, path = row[:2].decode(), row[3:].decode()
        rows[path] = status
        if "R" in status or "C" in status:
            rows[chunks[index].decode()] = status
            index += 1
    return rows


def record(path, status):
    target = Path(path)
    try:
        target.lstat()
    except FileNotFoundError:
        return {"path": path, "status": status, "lstat_type": "missing"}
    if target.is_symlink():
        return {
            "path": path,
            "status": status,
            "lstat_type": "symlink",
            "symlink_target": os.readlink(target),
        }
    if target.is_file():
        return {
            "path": path,
            "status": status,
            "lstat_type": "regular",
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
    return {"path": path, "status": status, "lstat_type": "other"}


output = Path(sys.argv[1])
previous = Path(sys.argv[2]) if len(sys.argv) == 3 else None
statuses = status_by_path()
paths = (
    [row["path"] for row in json.loads(previous.read_text(encoding="utf-8"))]
    if previous is not None
    else sorted(statuses)
)
output.write_text(
    json.dumps([record(path, statuses.get(path)) for path in sorted(paths)], sort_keys=True, indent=2)
    + "\n",
    encoding="utf-8",
)
PY
python3 "$PROVENANCE_DIR/capture_preexisting_paths.py" \
  "$PROVENANCE_DIR/preexisting_path_records.json"
printf 'BASE_SHA=%s\nPROVENANCE_DIR=%s\n' "$BASE_SHA" "$PROVENANCE_DIR"
```

Expected: every SHA matches; preserve the printed `PROVENANCE_DIR` and export that exact value before Task 5. Preserve the raw status/diff snapshots as provenance only. `preexisting_path_records.json` is the exact immutable record for every pre-existing dirty/untracked path: path, porcelain status, lstat type, SHA-256 or symlink target. Do not require the full post-worktree diff to equal this snapshot. At completion, require only `preexisting_path_records.json` to be byte/type-identical; implementation changes are checked by the allowlist separately.

- [ ] **Step 2: Verify frozen local Stage 1.5G v2 evidence without writing anything.**

```bash
set -euo pipefail
ROOT=data/external_signal_shadow/stage1_5g/reviews/20260829T024637Z_local_recheck_551b1fa19ce6
PYTHONPATH=src:. .venv/bin/python - "$ROOT" <<'PY'
import hashlib, json, sys
from pathlib import Path
from src.research.external_signal_shadow.safety import canonical_json_dumps

root = Path(sys.argv[1])
expected = {
    'stage1_5g_review_manifest.json': '35a1ce9dc0ad02738ab26e97c9fd36ef860d3533dc8626c2f527e7ff1f4ecdf0',
    'stage1_5g_live_depth_evidence_review_summary.json': '0fde86685162b74d08751098075fd5ce74197176408da0a033d214270de2a425',
    'stage1_5g_quarantine_summary.json': '9f783c90015b068499a175061df20e12211469ff559a208ddffd3b12340c41d2',
    'depth_quality_input_rows.jsonl': '1af7418009c5c09375d3c0315b47fb87ff9192b92a0d6cf03248aff0747aec85',
    'quarantined_invalid_book_rows.jsonl': '44ac1a602787507e6178d2b05599e7b8b1f848c82eed2361f5fcb4c04a770bf3',
}
for name, digest in expected.items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
summary = json.loads((root / 'stage1_5g_live_depth_evidence_review_summary.json').read_text())
quarantine = json.loads((root / 'stage1_5g_quarantine_summary.json').read_text())
assert canonical_json_dumps(summary['quarantine']) == canonical_json_dumps(quarantine)
for row in (summary, quarantine, json.loads((root / 'stage1_5g_review_manifest.json').read_text())):
    assert row['stage1_5g_review_id'] == '0b059ce27b67a6221374602552a3f423bd4c07222e976526aadfe9b5f9ddfa50'
    assert row['source_evidence_manifest_sha256'] == '46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918'
    assert row['formal_completed_event_symbol_ids_sha256'] == '40a7584e5bd4a0ec88f7f3e7dbd24ae2249c2d002c426cbb47f688af52eda4aa'
assert summary['formal_completed_event_symbol_ids_sha256'] == '40a7584e5bd4a0ec88f7f3e7dbd24ae2249c2d002c426cbb47f688af52eda4aa'
print({'frozen_v2_evidence': 'PASS', 'formal_completed_symbol_count': quarantine['formal_completed_symbol_count']})
PY
```

Expected: `frozen_v2_evidence=PASS`, five formal completed symbols, no writes under source/review roots.

## Task 1: Write Failing V2 Closed-Bundle Contract Tests

**Design invariants:** INV-H2-02, INV-H2-03, INV-H2-04, INV-H2-05, INV-H2-06, INV-H2-08, INV-H2-10, INV-H2-12.

**Files:**

- Create: `tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py`
- Modify: none.

**Interfaces introduced by later tasks:**

```python
def build_stage1_5h_v2_event_bundle_reports(bundle: Stage1_5HInputBundle) -> dict[str, Any]: ...
def write_stage1_5h_v2_event_bundle_reports(
    *, bundle: Stage1_5HInputBundle, output_root: str | Path
) -> dict[str, Any]: ...
def verify_stage1_5h_v2_event_bundle_manifest(
    output_root: str | Path
) -> tuple[bool, list[str]]: ...
```

- [ ] **Step 1: Create one self-contained two-symbol v2 fixture factory.**

The fixture must create two 64-lowercase-hex IDs, sorted in producer order; two matching `event_level_decisions`; a main summary whose `quarantine` is canonical-equal to the standalone quarantine; metrics with `blockers=[]`; valid/invalid JSONL rows; and a v2 manifest written through existing `write_stage1_5g_review_manifest`.

```python
def event_symbol_id(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()

ids = sorted([event_symbol_id("event-a|AAAUSDT"), event_symbol_id("event-a|BBBUSDT")])
assert all(re.fullmatch(r"[0-9a-f]{64}", item) for item in ids)

formal_hash = hashlib.sha256(
    canonical_json_dumps(ids).encode("utf-8")
).hexdigest()
```

The fixture must use the repository's actual approved governance review, not a copied marker file: its resolved path and SHA-256 must match the Frozen Authority table. Add a negative test that a same-marker substitute at any other path rejects. This prevents a caller from manufacturing a lookalike governance artifact.

- [ ] **Step 2: Add failing validation tests.**

```python
def test_v2_bundle_builds_exactly_one_prepared_report_per_formal_id(tmp_path):
    bundle, ids = load_v2_bundle_fixture(tmp_path)
    result = build_stage1_5h_v2_event_bundle_reports(bundle)
    assert result["decision"] == "stage1_5h_v2_event_bundle_reports_ready"
    assert result["event_symbol_ids"] == ids
    assert set(result["reports"]) == set(ids)
    assert all(row["execution_feasibility_claim_allowed"] is False for row in result["reports"].values())

@pytest.mark.parametrize("mutation", ["clean_v2_input", "duplicate_id", "unsorted_id", "projection_mismatch", "foreign_row", "symbol_mismatch", "count_mismatch", "identity_mismatch", "upstream_blocker", "phase_total_mismatch"])
def test_v2_bundle_rejects_closed_bundle_semantic_contradictions(tmp_path, mutation):
    bundle = load_mutated_v2_bundle_fixture(tmp_path, mutation)
    result = build_stage1_5h_v2_event_bundle_reports(bundle)
    assert result["decision"] == "stage1_5h_v2_event_bundle_input_rejected"
    assert result["report_generation_allowed"] is False
    assert result["reports"] == {}


def test_v2_clean_bundle_uses_the_frozen_rejection_taxonomy(tmp_path):
    bundle = load_mutated_v2_bundle_fixture(tmp_path, "clean_v2_input")
    result = build_stage1_5h_v2_event_bundle_reports(bundle)
    assert "stage1_5h_v2_clean_bundle_not_authorized" in result["blockers"]
```

Add a separate test with two physically identical valid JSONL rows whose metric count is also two. It must not produce a new duplicate-row blocker. Add tests that unsafe IDs (`"../x"`, uppercase hex), symlinked input artifact and clean-v2 input all reject.

- [ ] **Step 3: Add failing N=1 semantic-equivalence and safety tests.**

```python
def test_v2_n1_prepared_report_matches_legacy_static_proxy_fields(tmp_path):
    legacy_bundle, v2_bundle = make_equivalent_legacy_and_v2_n1_fixtures(tmp_path)
    legacy = build_stage1_5h_report_summary(legacy_bundle)
    v2 = build_stage1_5h_v2_event_bundle_reports(v2_bundle)["reports"].values().__iter__().__next__()
    for key in ("static_proxy_metrics", "static_proxy_blockers", "required_next_evidence"):
        assert v2[key] == legacy[key]


def test_v2_reports_never_borrow_another_symbol_metrics_or_identity(tmp_path):
    bundle, ids = make_distinct_two_symbol_v2_fixture(
        tmp_path,
        first_quality={"spread_bps_p95": 2.0, "buy_slippage_bps_500usdt_p95": 3.0,
                       "sell_slippage_bps_500usdt_p95": 3.0, "book_availability_ratio": 0.99,
                       "invalid_book_row_count": 0},
        second_quality={"spread_bps_p95": 20.0, "buy_slippage_bps_500usdt_p95": 30.0,
                        "sell_slippage_bps_500usdt_p95": 30.0, "book_availability_ratio": 0.95,
                        "invalid_book_row_count": 2},
    )
    reports = build_stage1_5h_v2_event_bundle_reports(bundle)["reports"]
    identity_rows = {
        row["event_symbol_id"]: row
        for row in bundle.stage1_5g_summary["event_level_decisions"]
    }
    assert reports[ids[0]]["static_proxy_metrics"]["spread_bps_p95"] == 2.0
    assert reports[ids[1]]["static_proxy_metrics"]["spread_bps_p95"] == 20.0
    assert reports[ids[0]]["stage1_5h_static_proxy_status"] != reports[ids[1]]["stage1_5h_static_proxy_status"]
    for event_symbol_id in ids:
        row = reports[event_symbol_id]
        assert row["event_symbol_id"] == event_symbol_id
        assert row["symbol"] == identity_rows[event_symbol_id]["symbol"]
        assert row["source_article_id"] == identity_rows[event_symbol_id]["source_article_id"]
        assert row["stage1_5g_review_id"] == bundle.stage1_5g_summary["stage1_5g_review_id"]
        assert row["source_evidence_manifest_sha256"] == bundle.stage1_5g_summary["source_evidence_manifest_sha256"]
        assert row["formal_completed_event_symbol_ids_sha256"] == bundle.stage1_5g_summary["formal_completed_event_symbol_ids_sha256"]


def test_v2_markdown_projection_cannot_add_authority_terms(tmp_path):
    bundle, _ = load_v2_bundle_fixture(tmp_path)
    prepared = build_stage1_5h_v2_event_bundle_reports(bundle)
    markdown = prepared["reports"][prepared["event_symbol_ids"][0]]["markdown"]
    for term in ("SignalCandidate", "TradeIntent", "tradeable", "profitable", "buy instruction"):
        assert term not in markdown


def test_v2_rejects_invalid_input_when_python_optimization_is_enabled(tmp_path):
    paths = make_v2_bundle_fixture(tmp_path, mutation="foreign_row")
    command = [sys.executable, "-O", "-c", """
from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import build_stage1_5h_v2_event_bundle_reports, load_stage1_5h_inputs
import sys
bundle = load_stage1_5h_inputs(stage1_5g_summary_path=sys.argv[1], quarantine_summary_path=sys.argv[2], depth_quality_input_rows_path=sys.argv[3], quarantined_invalid_book_rows_path=sys.argv[4], governance_review_path=sys.argv[5])
raise SystemExit(build_stage1_5h_v2_event_bundle_reports(bundle)["decision"] != "stage1_5h_v2_event_bundle_input_rejected")
""", str(paths.summary), str(paths.quarantine), str(paths.valid_rows), str(paths.invalid_rows), str(paths.governance)]
    assert subprocess.run(command, check=False).returncode == 0
```

- [ ] **Step 4: Run RED.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py
```

Expected: collection/import failure because the three v2 interfaces do not yet exist. Do not modify legacy tests to make this fail.

## Task 2: Implement V2 Validator and Per-Symbol Prepared Reports

**Design invariants:** INV-H2-01, INV-H2-02, INV-H2-03, INV-H2-04, INV-H2-05, INV-H2-06, INV-H2-11, INV-H2-12.

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py`

**Consumes:** existing `Stage1_5HInputBundle`, `load_stage1_5h_inputs`, `canonical_json_dumps`, `verify_stage1_5g_review_manifest`, `_static_proxy_blockers`, and existing Stage 1.5H threshold constants.

**Produces:** `build_stage1_5h_v2_event_bundle_reports(bundle) -> dict[str, Any]` and no filesystem output.

- [ ] **Step 1: Implement shared v2 closed-artifact path validation without changing legacy behavior.**

Extract the exact root-relative manifest/path/hash checks currently inside `_v2_single_symbol_quarantine_view` into one private helper returning only validated root/manifest metadata or appending `stage1_5g_quarantine_v2_artifact_mismatch`. Both the existing v2 N=1 legacy path and the new v2 path must call it.

```python
def _validate_v2_closed_artifact_paths(
    bundle: Stage1_5HInputBundle, blockers: list[str]
) -> tuple[Path, dict[str, Any]] | None:
    required_paths = {
        "summary": bundle.stage1_5g_summary_path,
        "quarantine_summary": bundle.quarantine_summary_path,
        "depth_quality_input_rows": bundle.depth_quality_input_rows_path,
        "quarantined_invalid_book_rows": bundle.quarantined_invalid_book_rows_path,
    }
    # Require a regular, non-symlink manifest-bound path for every supplied artifact.
    # Resolve only after rejecting symlinks and reject any root escape or path mismatch.
```

Keep existing v2 N=1 return values and blockers byte/behavior compatible. Run its existing test file after this substep.

- [ ] **Step 2: Implement exact new-governance and v2 semantic validation.**

Add private helpers in the same module, not a new module or config:

```python
def _validate_v2_event_bundle_governance(
    bundle: Stage1_5HInputBundle, blockers: list[str]
) -> None: ...

def _validate_v2_event_bundle_inputs(
    bundle: Stage1_5HInputBundle, blockers: list[str]
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, dict[str, Any]]] | None: ...
```

The validator must require the repository's exact approved governance review path and SHA-256 `7bf59a14a230da4071bde7acafc0b2022de52c313f47f389eadd293b162dacc4`, then these approved marker lines: `scope = v2_event_bundle_per_symbol_read_only_report_generator`, `multi_symbol_per_symbol_reporting_allowed = true`, `cross_symbol_metric_aggregation_allowed = false`, `event_family_conclusion_allowed = false`, `cross_event_generalization_allowed = false`, all nine safety permissions false, `implementation_plan_allowed = true`, `implementation_allowed = false`, and `deployment_allowed = false`. It must reject the legacy governance artifact and any copied/same-marker substitute for this new path. The following pseudo-code is contract notation only: production validators must not use Python `assert`; every failed condition must append its frozen blocker, return the global reject result with `reports={}`, and perform no write. It must then perform this exact reducer order:

```python
summary = bundle.stage1_5g_summary
quarantine = bundle.quarantine_summary
def reject_input(blocker):
    _append_once(blockers, blocker)
    return None

if summary.get("schema_version") != 2 or quarantine.get("schema_version") != 2:
    return reject_input("stage1_5h_v2_event_bundle_input_rejected")
if summary.get("decision") != "stage1_5g_depth_evidence_quarantined_pass":
    return reject_input("stage1_5h_v2_event_bundle_input_rejected")
if summary.get("clean_depth_evidence_pass") is True:
    return reject_input("stage1_5h_v2_clean_bundle_not_authorized")
if summary.get("clean_depth_evidence_pass") is not False:
    return reject_input("stage1_5h_v2_event_bundle_input_rejected")
if summary.get("quarantined_depth_evidence_pass") is not True:
    return reject_input("stage1_5h_v2_event_bundle_input_rejected")
embedded_quarantine = summary.get("quarantine")
if not isinstance(embedded_quarantine, dict) or canonical_json_dumps(embedded_quarantine) != canonical_json_dumps(quarantine):
    return reject_input("stage1_5h_v2_event_bundle_input_rejected")

raw_ids = embedded_quarantine.get("eligible_event_symbol_ids")
if not isinstance(raw_ids, list) or not raw_ids or raw_ids != sorted(raw_ids):
    return reject_input("stage1_5h_v2_event_bundle_input_rejected")
if len(raw_ids) != len(set(raw_ids)):
    return reject_input("stage1_5h_v2_event_bundle_input_rejected")
if not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in raw_ids):
    return reject_input("stage1_5h_v2_event_bundle_input_rejected")
if hashlib.sha256(canonical_json_dumps(raw_ids).encode("utf-8")).hexdigest() != summary.get("formal_completed_event_symbol_ids_sha256"):
    return reject_input("stage1_5h_v2_event_bundle_input_rejected")
```

Validate `formal_completed_symbol_count`, exact metrics-key set, `event_level_decisions` one-to-one formal identity map, all JSONL rows, valid/invalid per-symbol counts, and phase/reason totals. Treat `metrics_s.blockers != []`, missing metric, foreign row, count mismatch, status inconsistency, unsafe path or identity mismatch as one global `stage1_5h_v2_event_bundle_input_rejected`; return `reports={}`.

Do not inspect `metrics_s.clean_depth_evidence_pass` or `metrics_s.quarantined_depth_evidence_pass`. Derive only:

```python
invalid_count = metrics_s["invalid_book_row_count"]
if not isinstance(invalid_count, int) or isinstance(invalid_count, bool) or invalid_count < 0:
    reject()
upstream_status = "clean" if invalid_count == 0 else "quarantined"
```

- [ ] **Step 3: Reuse one static-proxy calculation for legacy and v2 paths.**

Factor only the common calculation body so both paths use identical field names and formula; keep `_build_static_proxy_metrics(summary, quarantine)` as the legacy wrapper.

```python
def _build_static_proxy_metrics_from_quality(
    quality: dict[str, Any], *, depth_quality_input_mode: Any
) -> dict[str, Any]:
    buy_p95 = float(quality.get("buy_slippage_bps_500usdt_p95") or 0.0)
    sell_p95 = float(quality.get("sell_slippage_bps_500usdt_p95") or 0.0)
    observed = buy_p95 + sell_p95
    configured = float(base.EXTERNAL_SIGNAL_STAGE1_5H_CONSERVATIVE_ROUND_TRIP_COST_BPS)
    return {
        # Preserve all existing metric keys.
        "effective_friction_floor_bps": max(observed, configured),
        "cost_model_note": "effective_friction_floor_bps=max(observed_static_depth_friction_bps_p95, configured_conservative_round_trip_cost_bps); never sum them",
    }
```

For each validated `s`, pass only `metrics_s["quarantined_depth_quality"]` plus the existing summary input-mode metadata. Pass the same `metrics_s` to `_static_proxy_blockers`. Copy the existing four literal `required_next_evidence` items, retain invalid/availability/latency diagnostics, set `report_generation_status="generated"`, and set only `stage1_5h_static_proxy_status`/`stage1_5h_static_proxy_blockers` from legal static-proxy evaluation.

- [ ] **Step 4: Implement the prepared-bundle public result.**

```python
def build_stage1_5h_v2_event_bundle_reports(
    bundle: Stage1_5HInputBundle,
) -> dict[str, Any]:
    """Validate one v2 bundle and prepare independent in-memory reports only."""
    # On reject: decision, blockers, reports={}, report_generation_allowed=False,
    # and every v2 safety field false.
    # On success: ordered event_symbol_ids, identity-bound reports, no aggregate metrics,
    # and every v2 safety field false.
```

Use a v2-specific safety helper rather than changing `_base_safety_fields`; include all nine Design safety fields. Keep `build_stage1_5h_report_summary`, `validate_stage1_5h_governance`, `_v2_single_symbol_quarantine_view`, and `generate_stage1_5h_chinese_report` behavior-compatible.

- [ ] **Step 5: Run GREEN and legacy compatibility tests.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
```

Expected: all tests pass; legacy v1/v2 N=1 behavior is unchanged, while all new closed-bundle tests pass.

## Task 3: Write Root-Confined Reports and a Manifest-Last Sealed Bundle

**Design invariants:** INV-H2-07, INV-H2-08, INV-H2-09, INV-H2-10, INV-H2-12.

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py`

**Consumes:** Task 2 prepared result with `event_symbol_ids`, identity-bound report dicts and false safety fields.

**Produces:** `write_stage1_5h_v2_event_bundle_reports(...)` and `verify_stage1_5h_v2_event_bundle_manifest(...)`.

- [ ] **Step 1: Add failing persistence/lifecycle tests.**

```python
def test_v2_writer_seals_exact_reports_directory_and_manifest(tmp_path):
    bundle, ids = load_v2_bundle_fixture(tmp_path)
    root = tmp_path / "stage1_5h" / "reports" / "fresh"
    result = write_stage1_5h_v2_event_bundle_reports(bundle=bundle, output_root=root)
    assert result["decision"] == "stage1_5h_v2_event_bundle_reports_sealed"
    assert (root / "stage1_5h_event_bundle_manifest.json").is_file()
    assert set((root / "reports").glob("*.json")) == {root / "reports" / f"{item}.json" for item in ids}
    ok, blockers = verify_stage1_5h_v2_event_bundle_manifest(root)
    assert ok is True and blockers == []

@pytest.mark.parametrize("state", ["incomplete_without_manifest", "invalid_manifest", "sealed_root"])
def test_v2_writer_never_resumes_or_overwrites_existing_root(tmp_path, state):
    root = make_existing_v2_output_root(tmp_path, state)
    before = tree_digest(root)
    result = write_stage1_5h_v2_event_bundle_reports(bundle=load_v2_bundle_fixture(tmp_path)[0], output_root=root)
    assert result["decision"] == "stage1_5h_v2_event_bundle_output_rejected"
    assert tree_digest(root) == before
```

Add negative tests for a tampered report hash, extra manifest report key, report path escape, symlinked report directory and Markdown that differs from its deterministic renderer. Each must make `verify_stage1_5h_v2_event_bundle_manifest` return false.

Add one forced report-write failure test: after an otherwise valid prepared bundle reaches the first report write, raise `OSError`; assert the root contains no final manifest. It proves a report directory alone never becomes sealed authority.

Add an exact sealed-tree/output-authority test. For a two-symbol fixture, the final relative tree must be exactly `event_directory.json`, `stage1_5h_event_bundle_manifest.json`, `reports/`, and the two JSON/Markdown pairs. The verifier must reject any extra regular file, symlink or orphan temporary file. Assert every new report, directory, manifest and global reject result contains every v2 safety field with value `false`.

The event directory must use this exact schema, not a blacklist:

```python
EXPECTED_EVENT_DIRECTORY_KEYS = {
    "schema_version", "upstream", "event_symbol_ids", "reports",
    "execution_feasibility_claim_allowed", "alpha_interpretation_allowed",
    "trade_signal_allowed", "paper_trading_allowed", "live_trading_allowed",
    "execution_engine_allowed", "private_endpoint_allowed", "api_key_allowed",
    "order_endpoint_allowed",
}
EXPECTED_UPSTREAM_KEYS = {
    "stage1_5g_review_id", "source_evidence_manifest_sha256",
    "formal_completed_event_symbol_ids_sha256", "stage1_5g_review_manifest_sha256",
}
EXPECTED_DIRECTORY_REPORT_KEYS = {
    "json_relative_path", "json_sha256", "md_relative_path", "md_sha256",
    "upstream_stage1_5g_status", "stage1_5h_static_proxy_status",
}

assert set(directory) == EXPECTED_EVENT_DIRECTORY_KEYS
assert set(directory["upstream"]) == EXPECTED_UPSTREAM_KEYS
assert set(directory["reports"]) == set(ids)
assert all(set(row) == EXPECTED_DIRECTORY_REPORT_KEYS for row in directory["reports"].values())
```

The directory contains no market metric, score, rank, recommendation, event-family/cross-event conclusion, count summary or blocker taxonomy beyond this schema. JSON report, Markdown, directory and manifest must also reject the authority-expanding terms `aggregate_spread`, `aggregate_slippage`, `aggregate_depth`, `aggregate_availability`, `average`, `score`, `rank`, `tradeable`, `profitable`, `SignalCandidate`, `TradeIntent`.

- [ ] **Step 2: Implement root validation and deterministic rendering.**

```python
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_STAGE1_5H_V2_REPORTS_ROOT = (
    _PROJECT_ROOT
    / "data/external_signal_shadow/stage1_5h/reports"
)

def _validate_fresh_v2_output_root(output_root: Path) -> str | None:
    # Production root must be one direct, absent, non-symlink child of the fixed reports root.
    # Do not create or mutate either path here.

def _render_stage1_5h_v2_event_bundle_markdown(report: dict[str, Any]) -> str:
    # Render only fields already present in report JSON, in fixed order.
```

Production root validation must reject a symlinked `_STAGE1_5H_V2_REPORTS_ROOT`, then resolve it and require `output_root.parent.resolve() == reports_root`; require `output_root` itself not to exist or be a symlink, and reject any other parent. Unit tests must assert `_STAGE1_5H_V2_REPORTS_ROOT.resolve().relative_to(_PROJECT_ROOT.resolve())` succeeds, then may monkeypatch only `_STAGE1_5H_V2_REPORTS_ROOT` to a `tmp_path` reports directory. The production CLI may not override it. This is the Design's fixed persistent write boundary; do not add a second run-id grammar not present in the approved Design.

The renderer must never add a metric, blocker, recommendation or conclusion. Use direct child names `reports/<event_symbol_id>.json` and `.md` only after rechecking `^[0-9a-f]{64}$` and `relative_to(reports_dir)`.

- [ ] **Step 3: Implement write/verify contracts.**

```python
def write_stage1_5h_v2_event_bundle_reports(
    *, bundle: Stage1_5HInputBundle, output_root: str | Path
) -> dict[str, Any]:
    prepared = build_stage1_5h_v2_event_bundle_reports(bundle)
    if prepared["blockers"]:
        return prepared
    # Validate fresh root before mkdir. Write all report JSON/Markdown, then directory.
    # SHA-256 exact stored bytes. Write manifest to a same-directory temporary file,
    # close it, then os.replace(temp_path, manifest_path).

def verify_stage1_5h_v2_event_bundle_manifest(
    output_root: str | Path,
) -> tuple[bool, list[str]]:
    # Validate exact manifest schema, sorted S, required keys, direct non-symlink paths,
    # report/directory hashes, exact member set, exact sealed tree and false safety fields.
```

Manifest schema must be exactly `stage1_5h_v2_event_bundle_manifest_v1`, contain `bundle_status="sealed_read_only_bundle"`, upstream review/source/formal-ID/review-manifest hashes, sorted `event_symbol_ids`, one event-directory entry, one JSON/Markdown pair and status per ID, plus all safety flags. It must not self-hash. The verifier must require the event-directory exact schema above and reject an output tree with any entry beyond the final manifest, event directory, `reports/` and exactly two direct non-symlink report files for each ID. Define output identity as `SHA-256(manifest_path.read_bytes())` only after successful validation.

- [ ] **Step 4: Run GREEN.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py
```

Expected: valid fresh root seals exactly once; all incomplete/invalid/tampered/unsafe roots reject without mutation.

## Task 4: Add an Isolated V2 CLI and Preserve Legacy CLI Behavior

**Design invariants:** INV-H2-01, INV-H2-07, INV-H2-09, INV-H2-11, INV-H2-12.

**Files:**

- Create: `scripts/external_signal_shadow/review_stage1_5h_v2_event_bundle_per_symbol_report.py`
- Create: `tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py`

**Consumes:** Task 3 writer and the existing input loader.

**Produces:** a separate v2 local-only CLI; no changes to legacy CLI arguments or outputs.

- [ ] **Step 1: Write failing CLI tests.**

```python
def test_v2_cli_seals_only_under_explicit_fresh_output_root(tmp_path, monkeypatch):
    paths = make_v2_bundle_fixture(tmp_path)
    output_root = tmp_path / "stage1_5h" / "reports" / "fresh"
    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_v2_event_bundle_per_symbol_report.py",
        "--stage1-5g-summary", str(paths.summary),
        "--stage1-5g-quarantine-summary", str(paths.quarantine),
        "--depth-quality-input-rows", str(paths.valid_rows),
        "--quarantined-invalid-book-rows", str(paths.invalid_rows),
        "--governance-review", str(paths.governance),
        "--output-root", str(output_root),
    ])
    assert main() == 0
    assert (output_root / "stage1_5h_event_bundle_manifest.json").is_file()


def test_v2_cli_rejects_invalid_bundle_without_final_manifest(tmp_path, monkeypatch):
    # Supply a fixture with a foreign JSONL row and an explicit fresh output root.
    assert main() == 1
    assert not (output_root / "stage1_5h_event_bundle_manifest.json").exists()
```

- [ ] **Step 2: Implement the smallest separate CLI.**

```python
parser.add_argument("--stage1-5g-summary", required=True)
parser.add_argument("--stage1-5g-quarantine-summary", required=True)
parser.add_argument("--depth-quality-input-rows", required=True)
parser.add_argument("--quarantined-invalid-book-rows", required=True)
parser.add_argument("--governance-review", required=True)
parser.add_argument("--output-root", required=True)
```

Load inputs through existing `load_stage1_5h_inputs`, call only `write_stage1_5h_v2_event_bundle_reports`, print decision/blockers/sealed manifest path, and return `0` only when `decision == "stage1_5h_v2_event_bundle_reports_sealed"`. Do not add network calls, output-summary/output-review escape hatches, default root reuse, or a mode flag to the legacy CLI.

In CLI tests, monkeypatch `_STAGE1_5H_V2_REPORTS_ROOT` before calling `main()` so `tmp_path` is a permitted direct child. Add a production-boundary negative test with an otherwise valid bundle and `/tmp/outside-stage1-5h-reports`: it must return `1`, create no root and no final manifest.

- [ ] **Step 3: Run new and unchanged CLI suites.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py
```

Expected: new CLI accepts only sealed v2 path; old CLI remains byte/behavior compatible and still rejects multi-symbol v2 input.

## Task 5: Full Verification, Frozen-Bundle Regression and Completion Audit

**Design invariants:** INV-H2-01 through INV-H2-12.

**Files:** No repository file changes except the Task 5 generated local regression root.

- [ ] **Step 1: Run focused tests and lint only allowlisted paths.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  scripts/external_signal_shadow/review_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py
```

Expected: all tests and lint pass; no auto-fix command is permitted.

- [ ] **Step 2: Run the frozen five-symbol local-only regression after its hashes are rechecked.**

```bash
set -euo pipefail
ROOT=data/external_signal_shadow/stage1_5g/reviews/20260829T024637Z_local_recheck_551b1fa19ce6
OUT="data/external_signal_shadow/stage1_5h/reports/stage1_5h_v2_plan_regression_$(date -u +%Y%m%dT%H%M%SZ)"
PYTHONPATH=src:. .venv/bin/python - "$ROOT" <<'PY'
import hashlib, json, sys
from pathlib import Path
from src.research.external_signal_shadow.safety import canonical_json_dumps

root = Path(sys.argv[1])
expected = {
    'stage1_5g_review_manifest.json': '35a1ce9dc0ad02738ab26e97c9fd36ef860d3533dc8626c2f527e7ff1f4ecdf0',
    'stage1_5g_live_depth_evidence_review_summary.json': '0fde86685162b74d08751098075fd5ce74197176408da0a033d214270de2a425',
    'stage1_5g_quarantine_summary.json': '9f783c90015b068499a175061df20e12211469ff559a208ddffd3b12340c41d2',
    'depth_quality_input_rows.jsonl': '1af7418009c5c09375d3c0315b47fb87ff9192b92a0d6cf03248aff0747aec85',
    'quarantined_invalid_book_rows.jsonl': '44ac1a602787507e6178d2b05599e7b8b1f848c82eed2361f5fcb4c04a770bf3',
}
for name, digest in expected.items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
summary = json.loads((root / 'stage1_5g_live_depth_evidence_review_summary.json').read_text())
quarantine = json.loads((root / 'stage1_5g_quarantine_summary.json').read_text())
manifest = json.loads((root / 'stage1_5g_review_manifest.json').read_text())
assert canonical_json_dumps(summary['quarantine']) == canonical_json_dumps(quarantine)
for row in (summary, quarantine, manifest):
    assert row['stage1_5g_review_id'] == '0b059ce27b67a6221374602552a3f423bd4c07222e976526aadfe9b5f9ddfa50'
    assert row['source_evidence_manifest_sha256'] == '46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918'
    assert row['formal_completed_event_symbol_ids_sha256'] == '40a7584e5bd4a0ec88f7f3e7dbd24ae2249c2d002c426cbb47f688af52eda4aa'
print({'frozen_v2_evidence_recheck': 'PASS'})
PY
PYTHONPATH=src:. .venv/bin/python \
  scripts/external_signal_shadow/review_stage1_5h_v2_event_bundle_per_symbol_report.py \
  --stage1-5g-summary "$ROOT/stage1_5g_live_depth_evidence_review_summary.json" \
  --stage1-5g-quarantine-summary "$ROOT/stage1_5g_quarantine_summary.json" \
  --depth-quality-input-rows "$ROOT/depth_quality_input_rows.jsonl" \
  --quarantined-invalid-book-rows "$ROOT/quarantined_invalid_book_rows.jsonl" \
  --governance-review docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md \
  --output-root "$OUT"
PYTHONPATH=src:. .venv/bin/python - "$ROOT" "$OUT" <<'PY'
import hashlib
import json
import sys
from pathlib import Path
from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import verify_stage1_5h_v2_event_bundle_manifest

source_root, output_root = map(Path, sys.argv[1:])
ok, blockers = verify_stage1_5h_v2_event_bundle_manifest(output_root)
assert ok, blockers
source = json.loads((source_root / 'stage1_5g_live_depth_evidence_review_summary.json').read_text())
sealed = json.loads((output_root / 'stage1_5h_event_bundle_manifest.json').read_text())
reports = {
    event_symbol_id: json.loads((output_root / meta['json_relative_path']).read_text())
    for event_symbol_id, meta in sealed['reports'].items()
}
directory = json.loads((output_root / sealed['event_directory']['relative_path']).read_text())
frozen_ids = source['quarantine']['eligible_event_symbol_ids']
assert sealed['event_symbol_ids'] == frozen_ids
assert len(reports) == 5
assert sum(row['upstream_stage1_5g_status'] == 'clean' for row in reports.values()) == 3
assert sum(row['upstream_stage1_5g_status'] == 'quarantined' for row in reports.values()) == 2
for row in reports.values():
    for key in ('stage1_5g_review_id', 'source_evidence_manifest_sha256', 'formal_completed_event_symbol_ids_sha256'):
        assert row[key] == source[key]
safety = ('execution_feasibility_claim_allowed', 'alpha_interpretation_allowed', 'trade_signal_allowed', 'paper_trading_allowed', 'live_trading_allowed', 'execution_engine_allowed', 'private_endpoint_allowed', 'api_key_allowed', 'order_endpoint_allowed')
for payload in [*reports.values(), directory, sealed]:
    assert all(payload.get(key) is False for key in safety), payload
assert set(directory) == {
    'schema_version', 'upstream', 'event_symbol_ids', 'reports', *safety,
}
assert set(directory['upstream']) == {
    'stage1_5g_review_id', 'source_evidence_manifest_sha256',
    'formal_completed_event_symbol_ids_sha256', 'stage1_5g_review_manifest_sha256',
}
assert set(directory['reports']) == set(frozen_ids)
assert all(set(row) == {
    'json_relative_path', 'json_sha256', 'md_relative_path', 'md_sha256',
    'upstream_stage1_5g_status', 'stage1_5h_static_proxy_status',
} for row in directory['reports'].values())
forbidden = ('aggregate_spread', 'aggregate_slippage', 'aggregate_depth', 'aggregate_availability', 'average', 'score', 'rank', 'tradeable', 'profitable', 'SignalCandidate', 'TradeIntent')
assert not any(token in json.dumps([*reports.values(), directory, sealed], sort_keys=True) for token in forbidden)
manifest_sha256 = hashlib.sha256((output_root / 'stage1_5h_event_bundle_manifest.json').read_bytes()).hexdigest()
print({'stage1_5h_v2_frozen_bundle_regression': 'PASS', 'output_root': str(output_root), 'manifest_sha256': manifest_sha256})
PY
```

Expected: exactly five independent reports, one non-aggregating directory, valid sealed manifest, all safety fields false. This is local evidence only and must not be consumed by execution, alpha, paper or live systems.

- [ ] **Step 3: Enforce changed-path scope and complete the audit.**

```bash
set -euo pipefail
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
: "${PROVENANCE_DIR:?STOP: export the exact PROVENANCE_DIR printed by Task 0}"
test -d "$PROVENANCE_DIR" || { echo 'STOP: Task 0 provenance directory unavailable' >&2; exit 1; }
BASE_SHA="$(cat "$PROVENANCE_DIR/base_sha")"
DESIGN=docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-design-delta_CN.md
GOVERNANCE=docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md
UPSTREAM_DESIGN=docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-design-delta_CN.md
LEGACY_DESIGN=docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-static-execution-proxy-design_CN.md
LEGACY_GOVERNANCE=docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md
PLAN=docs/plans/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-implementation-plan_CN.md
test "$(shasum -a 256 "$DESIGN" | awk '{print $1}')" = ec936020cba1ca26a2709f02996ad70bcf05d9457bb1e741ac6d40685269f812
test "$(shasum -a 256 "$GOVERNANCE" | awk '{print $1}')" = 7bf59a14a230da4071bde7acafc0b2022de52c313f47f389eadd293b162dacc4
test "$(shasum -a 256 "$UPSTREAM_DESIGN" | awk '{print $1}')" = 3528d4b5f90ee8b7bd142773b1c35a1a51b2ea09242224eaed2ab10df69c5c8b
test "$(shasum -a 256 "$LEGACY_DESIGN" | awk '{print $1}')" = fc6a3b5bff51d15531b4fb61c30b1d8d2ef899680bba4621f3f17e03b6002c42
test "$(shasum -a 256 "$LEGACY_GOVERNANCE" | awk '{print $1}')" = 8058bf63eda822b6e93c65dc41afb29230e47551f0aa7e4a85bf53c19d51a3e8
: "${APPROVED_PLAN_SHA:?STOP: preserve the exact approved Plan SHA}"
test "$(shasum -a 256 "$PLAN" | awk '{print $1}')" = "$APPROVED_PLAN_SHA"
python3 - "$BASE_SHA" "$PROVENANCE_DIR/preexisting_path_records.json" <<'PY'
import json
import subprocess
import sys
allowed = {
    'src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py',
    'scripts/external_signal_shadow/review_stage1_5h_v2_event_bundle_per_symbol_report.py',
    'tests/research/external_signal_shadow/test_stage1_5h_v2_event_bundle_per_symbol_report.py',
    'tests/scripts/external_signal_shadow/test_review_stage1_5h_v2_event_bundle_per_symbol_report.py',
}
base_sha, records_path = sys.argv[1:]
roots = ['configs', 'src', 'scripts', 'tests', 'docs']
commands = [
    ['git', 'diff', '--name-only', base_sha, '--', *roots],
    ['git', 'diff', '--cached', '--name-only', base_sha, '--', *roots],
    ['git', 'diff', '--name-only', '--', *roots],
    ['git', 'ls-files', '--others', '--exclude-standard', '--', *roots],
]
changed = set()
for command in commands:
    changed.update(subprocess.check_output(command, text=True).splitlines())
preexisting = {row['path'] for row in json.loads(open(records_path, encoding='utf-8').read())}
task_owned = changed - preexisting
assert task_owned <= allowed, {'unexpected_changed_paths': sorted(task_owned - allowed)}
print({'allowed_changed_paths': sorted(task_owned), 'preexisting_paths_excluded': sorted(changed & preexisting)})
PY
git diff --check "$BASE_SHA"
git diff --cached --check "$BASE_SHA"
git diff --check
```

Run the Task 0 recorder against exactly its original path list, then require byte equality:

```bash
python3 "$PROVENANCE_DIR/capture_preexisting_paths.py" \
  "$PROVENANCE_DIR/preexisting_path_records_after.json" \
  "$PROVENANCE_DIR/preexisting_path_records.json"
cmp -s "$PROVENANCE_DIR/preexisting_path_records.json" \
  "$PROVENANCE_DIR/preexisting_path_records_after.json" || {
  echo 'STOP: a pre-existing dirty/untracked path changed' >&2
  exit 1
}
```

Before completion, run `.agent/skills/requesting-code-review` with `BASE_SHA`, current `HEAD`, the four allowlisted implementation/verification paths, and the approved Design/Plan invariants. Resolve every Critical or Important finding, then run `.agent/skills/audit-plan-completion` against this Plan. Completion is valid only with code-review findings resolved, audit verdict `complete`, a valid frozen-bundle manifest and all prior verification commands passing.

## Plan Self-Review

- **Coverage:** Every `INV-H2-01` through `INV-H2-12` maps to Tasks 0--5; no producer, threshold, legacy CLI, runtime or deployment action is included.
- **Compatibility:** Existing source call-site search shows only the legacy CLI/tests consume legacy public report functions. They remain unchanged and are explicit regression targets.
- **Ponytail:** One existing module receives the v2 trust-boundary logic; one separate CLI avoids changing the legacy interface. No new dependency, service, generic framework or config is introduced.
- **Open questions:** None that affect implementation. If implementation reveals an authority/schema/metric contradiction, stop and return to Design review; do not widen this Plan.

## Approval Gate

This Plan remains documentation only until a closure audit returns `Approve` and the user explicitly authorizes execution. Until then:

```text
implementation_allowed = false
deployment_allowed = false
```
