# Stage 1.3 R10 历史证据再准入预核查 Design

**日期：** 2026-09-29  
**状态：** `draft_for_review`  
**类型：** 纯本地、只读的历史证据再准入预核查；不是 replay、回测、策略重开或数据采集。  
**关联审计：** `docs/reviews/2026-09-27-historical-alpha-methodology-audit_CN.md` 的 R10。  
**唯一交付：** 经批准的未来 Plan 可生成一个本地候选 receipt root。它不修改既有 Stage 1.3 summary、review、代码、配置、路线图或运行时状态。

## 1. Purpose and Final Claim

R10 发现 `volume_spike_1h` 与 `relative_strength_vs_btc` 的旧决策最后由 `median_net_return_not_positive` 阻断。成本后中位数非正不能单独推出成本后均值或期望值非正；因此旧叙述不得把该单一门禁扩大为“没有正收益结构”。

这不构成策略翻案。当前工作区只保存聚合 summary；当前文件系统检索仅发现 `reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json`，没有可识别的 Stage 1.3 raw bars、historical evidence manifest 或逐事件 ledger。`git log --all --name-only` 对相关路径也未显示这类 artifact。故当前状态仍是 `EVIDENCE_GAP`，不得补算任何均值、胜率、分位数、PnL、MAE、MFE 或 Alpha。

唯一允许的 Final Claim：

> R10 preflight 只能证明调用方已有的本地 bars 与 event ledger 是否逐字节匹配一个在旧 Stage 1.3 review 之前已存在于 Git history 的 historical evidence manifest，并且其结构与 PIT identity 是否可验证；它不得读取或计算 forward outcome。即使全部通过，结果也只允许提出一份独立、永久标记为 exploratory 的 expectancy Design，绝不构成正期望、Alpha、策略重开、replay、paper、live、execution 或网络授权。

`readmission_status` 仅可为：

| Status | Exact meaning | Route |
| --- | --- | --- |
| `eligible_for_exploratory_expectancy_design` | historical Git-anchored manifest、bars、event ledger、规则 identity 和 PIT event identity 全部通过；独立机会定义明确延后 | 仅可提议另一份经独立审查的 exploratory expectancy Design |
| `evidence_gap` | required historical anchor 或 event evidence 缺失，但已提供的 bytes 能安全结构化描述 | 保留 Stage 1.3 停止状态；不得补网、换源、调参或计算 outcome |

上述 status 是本 Design 专用的证据准入状态，不是 L2 的 `phenomenon_supported`、`alpha_candidate`、`alpha_validated`、`falsified` 或 `reconsider_under_expectancy_framework`。缺失不是 false，`eligible...` 也不是研究/运行授权。

## 2. Frozen Authority and Historical Admission Chain

未来 Plan 在读取任何候选 input、创建 staging root 或写 receipt 前，必须重算下列 authority bytes。任一 mismatch 必须 `STOP=stage1_3_r10_readmission_authority_mismatch`。

| Authority | Identity | SHA-256 / requirement | Use |
| --- | --- | --- | --- |
| Historical methodology audit | `docs/reviews/2026-09-27-historical-alpha-methodology-audit_CN.md` | `61ba2f7acb88b91db9f23a2f9f085bc493d52160d6ee411978573cb96d9f3ac4` | R10 scope and non-reopen boundary |
| Stage 1.3 review | `docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md` | `a404b54b141a5a18914c3b34ae5168e4565699d0929a324464cbca27e89546bf` | old venue, sample, gate and limitation facts |
| Stage 1.3 summary | `reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json` | `4c27cd2504e9b9660cf4c418fd80b4f00b91655c6adebce3ade36643178d51d5` | candidates and historical blocker facts |
| Old reducer | `src/research/external_signal_shadow/stage1_3_summary.py` | `6528259eee07e9a82f8bc2a6b3511d5822cf362944f745bd0f296c7977dd3276` | only final blocker was `median_net_return_not_positive` |
| Candidate detector | `src/research/external_signal_shadow/stage1_3_candidates.py` | `2c59224742a0041f2cbe2930f0b58e142155c9e0a9d134fd69181195219c10b6` | fixed candidate identity |
| Historical runner | `scripts/run_external_signal_shadow_stage1_3_candidate_discovery.py` | `f2ba0454cc8eae23afbb58d2ef7d1e091c4457830f932d9ac60f592405f7f080` | old input format only; preflight must not import/call it |
| L2 methodology | `.agent/rules/L2_Alpha_Research_Methodology.md` | `806314e860bbf94d0e4332377d8bf617471f31dfcb51ffab1b646220ba8aed27` | anti-hindsight and independent-unit policy |
| Historical review publication commit | Git commit `b122dc0700446990b43cc6fe9f613bf76bc8025c` | must exist and contain the review/summary bytes in §2.1; manifest commit must be its strict ancestor | v1 pre-outcome Git anchor boundary |

The future invocation must also receive `APPROVED_DESIGN_PATH` and `APPROVED_DESIGN_SHA256` from the user approval sentence. Since a Design cannot self-hash, the reader verifies these external values before every input read. Missing/mismatch: `STOP=stage1_3_r10_readmission_design_approval_mismatch`.

### 2.1 Historical Evidence Admission Rule

A caller-created JSON sidecar, a matching filename, matching aggregate count, or a statement that data was collected historically has **zero** historical admission authority.

V1 accepts one admission mechanism only, chosen for minimal deterministic verification:

```text
Git blob already reachable from a commit that is an ancestor of b122dc...
    -> historical evidence manifest bytes
    -> exact hashes/lengths for bars and event ledger
    -> supplied local bars and event ledger
    -> structural/PIT identity checks
```

The boundary commit has a mechanical identity, not a descriptive label. Before testing an input manifest, the reader must prove these two exact bytes from the boundary tree:

```bash
test "$(git show b122dc0700446990b43cc6fe9f613bf76bc8025c:docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md | shasum -a 256 | awk '{print $1}')" = \
  a404b54b141a5a18914c3b34ae5168e4565699d0929a324464cbca27e89546bf
test "$(git show b122dc0700446990b43cc6fe9f613bf76bc8025c:reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json | shasum -a 256 | awk '{print $1}')" = \
  4c27cd2504e9b9660cf4c418fd80b4f00b91655c6adebce3ade36643178d51d5
```

The historical manifest is read with `git show <manifest_commit>:<manifest_git_path>`, not from a caller-writable filesystem sidecar. It must be **strictly before** the boundary commit:

```bash
git cat-file -e "$MANIFEST_COMMIT^{commit}"
test "$MANIFEST_COMMIT" != b122dc0700446990b43cc6fe9f613bf76bc8025c
git merge-base --is-ancestor "$MANIFEST_COMMIT" b122dc0700446990b43cc6fe9f613bf76bc8025c
```

A future invocation may omit both `--historical-manifest-git-commit` and `--historical-manifest-git-path`; that absence is `evidence_gap` and must never become eligibility. Supplying only one is invalid and must STOP. Supplying a non-ancestor, unreadable object, malformed manifest, or a manifest whose hashes conflict with supplied bytes is `STOP=stage1_3_r10_readmission_historical_anchor_invalid`.

Git object reachability and the authenticity of the existing repository history are the explicit local TCB. V1 does not claim that a local process can prove an external wall-clock timestamp or protect against a party that can rewrite the Git object database. Sealed roots or externally timestamped archives are not accepted in V1; supporting either requires a separate Design, not an ad-hoc parser branch.

## 3. Confirmed Facts and Current Evidence Gaps

1. `RISK_LIVE_TRADING_ENABLED=False`; this Design changes no config or permission.
2. The old Stage 1.3 replay was `fixture_run=False`, `historical_venue=binance_proxy`, `venue_proxy_used=True`, using fixed spot symbols `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `XRPUSDT`, `DOGEUSDT`; the review records 180 days of 15m bars and 86,400 rows.
3. Stage 1.2 used Gate ticker data. A future R10 result based on Binance proxy cannot establish Gate venue parity or executability.
4. The historical runner accepts external JSONL bars then calculates candidates, forward metrics, 50 bps costs and random baselines. It is forbidden in this preflight path.
5. The two R10 candidates remain historical facts only:

| Candidate | Historical event count | Historical blocker | Historical post-50bps median |
| --- | ---: | --- | ---: |
| `volume_spike_1h` | 5,690 | `median_net_return_not_positive` | `-48.957880100499686` bps |
| `relative_strength_vs_btc` | 4,004 | `median_net_return_not_positive` | `-52.286317691692076` bps |

6. The summary's aggregate counts and outcomes cannot reconstruct rows, prove their source, prove PIT, or prove an independent unit.
7. Current `find data reports` and Git-path inspection find no identifiable historical raw bars, historical evidence manifest or event ledger for Stage 1.3. This is a current `EVIDENCE_GAP`, not proof that no such byte ever existed elsewhere.
8. `.venv/bin/python -m graphify query decide_stage1_3_summary` exits `1` with `No module named graphify`. Graphify is advisory only; no graph is generated or updated.

## 4. Scope and Non-Goals

### 4.1 Scope

A future approved Plan may add one local read-only preflight path that:

1. binds §2 authority and approval bytes;
2. structurally parses all supplied raw bars for integrity, without event-relative outcome logic;
3. reads a pre-existing Git-anchored manifest and byte-binds supplied bars/event ledger to it;
4. verifies pre-event event identity and PIT timestamp relations;
5. emits one local candidate receipt root with a deterministic `eligible...` or `evidence_gap` status; and
6. requires an independent Completion Audit before any future consumer may bind that receipt.

### 4.2 Non-Goals

- No HTTP, Binance/Gate/VPS access, cache access, raw-data collection, repair, substitution or source fallback.
- No import/call of the old runner, orchestrator, metrics, random baseline or cost code.
- No outcome calculation: no mean, median, win rate, quantile, PnL, return, baseline excess, MAE, MFE, Alpha or economic claim.
- No reconstruction of the historical event ledger from bars. Such reconstruction is a separate future exploratory Design.
- No independent-unit, parent/episode clustering, train/test split, confidence interval or promotion decision in this preflight.
- No changes to old summary/review, thresholds, cost, horizon, universe, config, strategy, runtime, roadmap or status documents.
- No paper/live/execution/replay/network/deployment/SSH/commit/push authority.

## 5. Decisions, Mutable Set and No-Touch Set

| Decision | Reason |
| --- | --- |
| Git-anchored historical manifest is the sole v1 admission mechanism | a fresh compatible sidecar cannot prove historical provenance; one mechanism is safer than a generic provenance framework |
| Entire bars file may be structurally parsed | hash/schema/timestamp integrity needs full-file validation; this is separated from any event-relative/outcome evaluation |
| Event ledger is required for eligibility but optional for an `evidence_gap` receipt | `missing != malformed`; absence is a safe evidentiary result, malformed supplied bytes are untrustworthy |
| Cross-symbol independent unit is deferred | same market episode may trigger multiple symbols; this Design must not prematurely count children as independent |
| Published receipt is tamper-evident, not cryptographically immutable authority | internal checksum detects accidental corruption only; future use requires external Completion Audit SHA binding |
| No input-root path is recorded | content identity is sufficient; root canonicalization would add an unnecessary second identity system |

**Mutable Set:** this unapproved Design and direct sibling sections needed to repair its authority, input, schema, state and validation contracts.

**No-Touch Set:** all historical artifacts and hashes in §2; Stage 1.3 candidate parameters; old reducer behavior; config; Stage 1.5/1.6; Route C1/B-Lite/Factor Lab conclusions; runtime/VPS docs; all permissions; and every implementation artifact. Any fix requiring a different historical anchor, new input source, network action or changed research rule must STOP and start a new Design.

## 6. Fixed Rule, Input and PIT Contract

### 6.1 Historical Rule Identity Only

Only these two candidate names are eligible for ledger admission:

| Candidate | Frozen historical identity |
| --- | --- |
| `volume_spike_1h` | complete 1h `quote_volume` >= 3.0x 7-day same-UTC-hour median; at least 5 samples |
| `relative_strength_vs_btc` | alt 1h return minus BTC 1h return > 1.5 sigma over 7-day spread history; at least 48 samples; BTC cannot emit it |

Shared identity: 15m bars; 60,000ms availability lag; one complete 15m entry delay; 4h horizon; 50bps historical round-trip stress cost; 500 symbol/hour random-baseline trials; five-symbol universe. These are identity facts only. Preflight does not invoke any calculation using their forward horizon, cost or trials.

### 6.2 CLI Inputs and Presence Triage

Only these flags exist. There is no `--input-root`, URL, glob, directory, stdin, environment default or automatic discovery.

| Flag | Presence | Contract |
| --- | --- | --- |
| `--bars-jsonl` | mandatory | existing local non-symlink regular file; complete raw 15m bars |
| `--historical-manifest-git-commit` and `--historical-manifest-git-path` | paired optional | pre-existing Git blob per §2.1; both absent is a gap, one absent is STOP |
| `--event-ledger-jsonl` | optional | existing local non-symlink regular file; required for eligibility, absence is a gap |

Presence reducer is exact:

| Condition | Action |
| --- | --- |
| bars absent, non-regular, symlinked, unreadable or structurally invalid | STOP; no final root |
| historical manifest flags both absent | record `historical_anchor_absent`; do not grant eligibility |
| one manifest flag absent, Git proof invalid, blob unreadable, schema invalid, or manifest mismatch | STOP; no final root |
| event ledger absent | record `event_ledger_absent`; do not grant eligibility |
| event ledger present but non-regular, malformed, has forbidden fields, or fails manifest/PIT identity | STOP; no final root |
| all supplied bytes valid but one or more absence reason exists | publish only `evidence_gap` receipt |
| all required bytes valid and no gap reason | publish only `eligible_for_exploratory_expectancy_design` receipt |

### 6.3 Exact Historical Manifest Schema

The Git blob must be UTF-8 JSON with exactly these keys and no extra keys:

```json
{
  "schema_version": 1,
  "historical_run_identity": "non-empty string",
  "historical_venue": "binance_proxy",
  "venue_proxy_used": true,
  "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"],
  "interval": "15m",
  "history_days": 180,
  "bar_count": 86400,
  "bars_sha256": "64 lowercase hex",
  "bars_byte_length": "positive integer",
  "event_ledger_sha256": "64 lowercase hex",
  "event_ledger_byte_length": "positive integer"
}
```

`historical_run_identity` is opaque and never interpreted as a date or permission. The supplied bars and event ledger must exactly match the two hash/length pairs. No fresh acquisition ledger, transformation record or caller metadata can amend this Git-anchored manifest.

### 6.4 Exact Event Ledger Schema

Each non-empty JSONL line must be an object with exactly these keys and no extra keys:

```json
{
  "candidate_name": "volume_spike_1h | relative_strength_vs_btc",
  "symbol": "BTCUSDT | ETHUSDT | SOLUSDT | XRPUSDT | DOGEUSDT",
  "source_bar_start_ms": "integer",
  "source_bar_end_ms": "integer",
  "event_available_at_ms": "integer"
}
```

All rows must be strictly ordered by `(candidate_name, symbol, event_available_at_ms)` and unique by the same tuple. `source_bar_end_ms - source_bar_start_ms` must be `900000`; `event_available_at_ms == source_bar_end_ms + 60000`; `(symbol, source_bar_start_ms, source_bar_end_ms)` must identify a supplied bar. There is no `metadata`, `diagnostic_metadata`, cluster id, price, volume, entry, exit, return, PnL, cost, MAE, MFE or arbitrary extra field.

### 6.5 Structural Reader Versus Outcome Evaluator

The structural reader may read every raw bar's OHLCV values only to construct `HistoricalBar`, validate its intrinsic constraints, count coverage and discard numeric values. It may retain only `(symbol, bar_start_ms, bar_end_ms)` as a time index for §6.4 identity checks.

The preflight evaluator must not:

```text
lookup a bar by event-relative forward offset
branch/aggregate raw values by event identity
calculate entry/exit/forward return/cost/PnL/MAE/MFE
log, serialize, print or expose raw price/volume values
```

Therefore parsing a complete historical file for byte/schema integrity is permitted; outcome evaluation is not. The two must be separate production call paths and the structural path must not import the old runner, orchestrator, metrics or baseline modules.

### 6.6 Independent-Unit Boundary

This Design deliberately makes no claim that an event row is independent. `relative_strength_vs_btc` rows across multiple alts can share one market episode. Receipt field `independent_unit_status` is always `deferred_to_future_exploratory_design`.

A later exploratory Design must define a cross-symbol episode/parent clustering rule before it reads outcomes. It must use the resulting episode, not raw rows, for any promotion/falsification statistics; the outcome-seen sample cannot promote beyond exploratory without a new independent validation sample.

## 7. Producer / Consumer / Authority Matrix

| Actor | Inputs / outputs | Authority | Prohibited action |
| --- | --- | --- | --- |
| Historical producer | pre-existing Git-anchored manifest and matching local backup bytes | only source identity, not Alpha | create a new sidecar to prove history |
| Structural reader | bars JSONL | schema/hash/time integrity | event-relative value access |
| Event identity reader | anchored event ledger plus time index | event/PIT identity | cluster/economic/outcome analysis |
| Receipt writer | validated facts only | writes one candidate receipt root | modifies source inputs or overwrites run root |
| Strict receipt loader | receipt, checksum and externally supplied expected hashes | validates exact audited bytes | trust checksum discovered from path as external authority |
| Completion Auditor | implementation and root bytes, read-only | binds published receipt SHA/length to external audit artifact | write/repair receipt or grant research/runtime authority |
| Future exploratory Design | audited receipt binding | may propose separate exploratory study | infer Alpha, execution or venue parity from preflight |

## 8. Receipt Schema and Authority Boundary

### 8.1 State x Artifact Matrix

`RUN_ID` is exactly:

```text
^stage1_3_r10_readmission_[0-9]{8}T[0-9]{6}Z$
```

For that exact value, the only permitted roots are:

```text
FINAL_ROOT=data/external_signal_shadow/stage1_3/r10_readmission_preflight/<RUN_ID>/
STAGING_ROOT=data/external_signal_shadow/stage1_3/r10_readmission_preflight/.<RUN_ID>.staging.<pid>/
```

The fixed parent may be created by the writer only after all input gates pass; once it exists, it must be a local non-symlink directory and be fsynced before staging creation. `STAGING_ROOT` and an existing `FINAL_ROOT` must each be local non-symlink directories. `FINAL_ROOT` must not exist before a fresh invocation; any pre-existing final root, wrong parent, symlink or duplicate `RUN_ID` is STOP. A strict loader recognizes only `FINAL_ROOT`, never `STAGING_ROOT`.

| State | Final root | Staging root | Consumer interpretation |
| --- | --- | --- | --- |
| `before_start` | absent | absent | no receipt |
| `staging` | absent | exact `STAGING_ROOT` from §8.1 (`.<RUN_ID>.staging.<pid>/`) only | never consumable |
| `receipt_published` | exact two-file final root with internally valid checksum | absent or irrelevant stale staging outside final grammar | locally published; not yet consumer-authorized |
| `corrupt_or_unknown` | wrong files, symlink, missing checksum, mismatch | any | STOP=`stage1_3_r10_readmission_receipt_invalid` |

A valid final root contains exactly:

```text
r10_readmission_receipt.json
SHA256SUMS
```

No resume exists: a new invocation uses a new `RUN_ID`; an existing final root always stops.

### 8.2 Exact Receipt Schema

Receipt JSON has exactly these top-level keys and no extras:

```json
{
  "schema_version": 1,
  "run_id": "stage1_3_r10_readmission_YYYYMMDDTHHMMSSZ",
  "readmission_status": "eligible_for_exploratory_expectancy_design | evidence_gap",
  "authority_packet": {},
  "historical_anchor": {},
  "input_identities": {},
  "candidate_scope": ["volume_spike_1h", "relative_strength_vs_btc"],
  "fixed_rule_identity": {},
  "pit_checks": {},
  "independent_unit_status": "deferred_to_future_exploratory_design",
  "evidence_gap_reasons": [],
  "authority_flags": {},
  "created_at_utc": "RFC3339 UTC Z"
}
```

Nested exact schemas:

| Field | Exact keys / values |
| --- | --- |
| `authority_packet` | `approved_design_sha256`, `historical_audit_sha256`, `stage1_3_review_sha256`, `stage1_3_summary_sha256`, `stage1_3_summary_code_sha256`, `stage1_3_candidates_code_sha256`, `stage1_3_runner_sha256`, `l2_sha256`, `historical_review_commit` (all §2 values) |
| `historical_anchor` | `status` = `anchored | absent`; `manifest_git_commit`, `manifest_git_path`, `manifest_blob_sha256`, `historical_run_identity` are all strings when anchored and all `null` when absent |
| `input_identities` | exact `bars` and `event_ledger`; each has `provided` bool, `sha256` string-or-null, `byte_length` positive-int-or-null, `matches_historical_manifest` bool; only §8.2.1 combinations are valid |
| `fixed_rule_identity` | `candidate_names` exact ordered array; `volume_spike_threshold=3`; `same_hour_min_samples=5`; `relative_strength_z_threshold=1.5`; `rolling_days=7`; `rolling_std_min_samples=48`; `bar_interval_ms=900000`; `availability_lag_ms=60000`; `entry_delay_bars=1`; `forward_horizon_hours=4`; `round_trip_cost_bps=50`; `random_baseline_trials=500`; `symbol_universe` exact ordered array |
| `pit_checks` | `bars_structural_status` = `valid`; `event_identity_status` = `valid | not_checked_event_ledger_absent`; `event_pit_status` = `valid | not_checked_event_ledger_absent`; `post_event_outcome_accessed=false` |

`evidence_gap_reasons` is a lexicographically sorted, duplicate-free subset of this exhaustive enum:

```text
historical_anchor_absent
event_ledger_absent
```

No other gap reason exists in V1. Malformed/conflicting supplied bytes are STOP conditions, not gap reasons.

Status matrix:

| Status | Anchor | Event ledger | PIT fields | Gap reasons |
| --- | --- | --- | --- | --- |
| `eligible_for_exploratory_expectancy_design` | `anchored` | provided/matches=true | both `valid` | exact empty array |
| `evidence_gap` | `absent` and/or event ledger not provided | permitted only if absent | `not_checked_event_ledger_absent` only when ledger absent | exact non-empty applicable enum subset |

#### 8.2.1 Input Identity Cross-Field Matrix

| Input / anchor state | `provided` | `sha256` | `byte_length` | `matches_historical_manifest` |
| --- | --- | --- | --- | --- |
| `bars`, any state | `true` | 64 lowercase hex | positive integer | `true` only when anchor is `anchored`; otherwise `false` |
| event ledger absent | `false` | `null` | `null` | `false` |
| event ledger present, anchor absent | `true` | 64 lowercase hex | positive integer | `false` |
| event ledger present, anchor anchored | `true` | 64 lowercase hex | positive integer | `true` |

Every other combination is `STOP=stage1_3_r10_readmission_receipt_invalid`. In particular, `eligible_for_exploratory_expectancy_design` requires both `bars.provided=true`, `bars.matches_historical_manifest=true`, `event_ledger.provided=true` and `event_ledger.matches_historical_manifest=true`.

### 8.3 Exact Deny Vector

`authority_flags` must have exactly these 19 bool keys, all `false`:

```text
RISK_LIVE_TRADING_ENABLED
alpha_interpretation_allowed
alpha_candidate_allowed
alpha_validated_allowed
network_collection_allowed
replay_allowed
point_in_time_directional_replay_allowed
private_api_allowed
authenticated_api_allowed
order_api_allowed
paper_trading_allowed
live_trading_allowed
execution_engine_allowed
execution_feasibility_claim_allowed
net_cost_or_profit_claim_allowed
deployment_allowed
ssh_allowed
commit_allowed
push_allowed
```

Missing, extra, non-bool or non-false values reject the receipt. Omission is never a deny state.

### 8.4 Publication, Crash and Downstream Binding

Writer sequence:

```text
validate -> serialize receipt -> fsync receipt -> write SHA256SUMS -> fsync files
-> atomic same-filesystem rename(staging_root, final_root) -> fsync final parent
```

Before rename, no final root is consumer-visible. After rename, a crash may leave a complete final root before the process returns. If the exact two-file final tree and its internal checksum validate, that root is `receipt_published`; otherwise it is `corrupt_or_unknown`. A process exit code, `state.*` file or absence of a Completion Audit is not part of publication state.

`SHA256SUMS` detects internal inconsistency only; it is not immutable historical authority. The local filesystem after publication remains inside the TCB. A future consumer must receive, from an approved future Design, all of:

```text
expected_receipt_sha256
expected_sha256sums_sha256
external_completion_audit_path
external_completion_audit_sha256
```

The independent read-only Completion Audit must bind those values, this Design/Plan SHA, `RUN_ID`, receipt status and historical anchor identity. No post-audit publisher is created. Path discovery plus a self-consistent checksum can never authorize a future consumer.

`future_consumer_allowed` is a separate authority predicate, not a publication lifecycle state:

```text
receipt_published
AND exact final receipt/SHA256SUMS bytes match externally supplied expected hashes
AND external Completion Audit path/SHA is valid and binds those exact bytes
```

### 8.5 Transition x Failure Matrix

| Transition | Failure | Required result |
| --- | --- | --- |
| `before_start -> staging` | path/input/authority failure | no final root; STOP, except valid absence triage may continue toward gap receipt |
| `staging -> receipt_published` | before rename/fsync failure | no final root; new RUN_ID required |
| `staging -> receipt_published` | crash after rename | exact final bytes plus internal checksum decide `receipt_published`; no resume writer |
| `receipt_published -> future consume` | audit/expected-hash missing or mismatch | root remains local evidence only; future consumer STOPs |
| any state | duplicate final RUN_ID, symlink, extra/missing file | STOP; never overwrite, repair or rebaseline |

## 9. Fail-Closed Reducer

1. Verify approved Design/Plan bytes, §2 authority, Git review commit and 19-key deny vector. Any failure: STOP.
2. Validate final run root absence, explicit flags and mandatory bars path. Invalid bars path: STOP.
3. Structurally parse all bars with `HistoricalBar` semantics; require five symbols, 15m interval, no duplicate starts, coverage >= 0.98, 86,400 bars and 180-day range. Retain only time index. Failure: STOP.
4. Apply manifest presence triage. Both manifest flags absent -> add `historical_anchor_absent`. Partial/invalid Git anchor -> STOP. Valid manifest -> verify exact bar hash/length and manifest schema; mismatch -> STOP.
5. Apply event-ledger presence triage. Absent -> add `event_ledger_absent`. Present -> verify exact schema and PIT identity. If anchor is `anchored`, also require its manifest hash/length match; if anchor is `absent`, set `matches_historical_manifest=false` and retain `historical_anchor_absent`. Any supplied-ledger parse/PIT failure, or any anchored hash/length mismatch: STOP.
6. If any gap reason exists, publish only an `evidence_gap` receipt. Otherwise publish only `eligible_for_exploratory_expectancy_design`.
7. A future strict loader may consume neither status unless §8.4 external audit binding is supplied and exact.

No reducer branch may infer historical provenance from new metadata, compatible values, old aggregate counts or current time.

## 10. Acceptance Invariant x Evidence Matrix

| ID | Invariant | Mechanical evidence |
| --- | --- | --- |
| INV-R10-01 | Only R10 two-candidate scope exists | exact candidate array and event-ledger candidate mutation rejection |
| INV-R10-02 | Fresh sidecars cannot prove historical evidence | boundary tree review/summary hashes must match §2; same-commit and non-ancestor anchor mutations STOP; unanchored compatible bars/ledger produces only `evidence_gap` |
| INV-R10-03 | Full-file structural parsing is not outcome evaluation | production import scan rejects runner/orchestrator/metrics/baseline; injected event-relative lookup fails scanner |
| INV-R10-04 | Missing differs from malformed | absent manifest/ledger produces the exact gap reason; malformed supplied counterpart STOPs |
| INV-R10-05 | PIT identity is pre-event only | exact event allowlist; injected outcome/extra key and timestamp mismatch each STOP |
| INV-R10-06 | Preflight does not overstate independence | receipt always has deferred status; no cluster count/claim is emitted |
| INV-R10-07 | Nested receipt schema and cross-field relations are exact | every missing/extra/type/status-matrix/cross-field mutation rejects, including eligible status with absent/unmatched bars |
| INV-R10-08 | Published root has realizable crash semantics | invalid RUN_ID/root/staging grammar rejects; injected pre-rename failure has no final root; injected post-rename crash is classified from final bytes and internal checksum, not process success or audit existence |
| INV-R10-09 | Self-consistent checksum is not external authority | loader without expected receipt/SHA256SUMS/audit bindings STOPs; replace both local files probe cannot pass bound loader |
| INV-R10-10 | No authority promotion | exact 19-key false vector; each omitted/extra/true mutation rejects |

## 11. Alpha Claim x Evidence Matrix

| Claim | This Design permits? | Required evidence / boundary |
| --- | --- | --- |
| Historical input identity is admissible | only `eligible...` | Git-anchored manifest plus exact local bytes and PIT identity |
| Market phenomenon exists | No | deferred; receipt has no outcome values |
| Statistical/economic edge | No | deferred to new exploratory L2 Design |
| Independent opportunity count | No | cross-symbol episode rule deferred to that Design |
| Alpha candidate / validated | No | preflight never emits either state |
| Replay/backtest | No | prohibited imports and outcome paths |
| Execution, paper or live permission | No | exact deny vector remains false |

The old outcome is permanently outcome-seen. A later analysis can only be exploratory and requires an independent validation sample for any promotion beyond that scope.

## 12. Future Plan Requirements

After independent Design review and explicit user approval, a Plan must include:

1. Task 0 authority, Git-anchor and live-trading false baseline checks before any input read/write.
2. One minimal read-only structural reader that reuses `HistoricalBar`; no old-runner import or duplicate bar semantics.
3. Canonical positive fixtures from the upstream `HistoricalBar` constructor and a Git-blob fixture factory. The fixture proves parser behavior, not historical provenance.
4. RED/GREEN negative mutations for every row in §10, including boundary commit tree mismatch, same-commit anchor, each §8.2.1 cross-field violation, root/staging grammar violation, post-rename crash and replacement of both receipt/checksum files.
5. Exact receipt/status schemas, strict loader binding and no-resume behavior.
6. Actual RC capture for `anti_shortcut_scan.py`, forbidden-import/network scanner, tests, `git diff --check`, scope/index proof, independent code review and fresh read-only Completion Audit.
7. No network, replay, configuration, strategy, runtime, deployment, SSH, commit or push action.

## 13. Open Questions

| Question | Blocking now? | Safe disposition |
| --- | --- | --- |
| Does a pre-review Git-anchored historical evidence manifest actually exist? | No for Design; yes for eligibility | current absence remains `evidence_gap` |
| Does a matching local event ledger backup exist? | No for Design; yes for eligibility | absence is `event_ledger_absent` |
| How should a cross-symbol market episode be clustered? | No | a later exploratory Design must freeze it before outcome access |
| Can Binance proxy findings transfer to Gate? | No | separate venue-parity/execution Design only |

## 14. Review Checklist

Reject this Design if it permits any of the following:

1. a newly written sidecar, matching count or compatible bars file to prove historical authority;
2. generic archive/sealed-root support without a new Design;
3. outcome calculation or event-relative forward-value access hidden inside structural parsing;
4. treating missing optional evidence as malformed, or malformed supplied evidence as a harmless gap;
5. treating symbol rows as independent market episodes;
6. an open nested receipt/ledger schema, path-derived input identity or self-checksum as external authority;
7. a claim that crash after successful rename leaves no final root;
8. `eligible...` as an Alpha, strategy, replay, execution, paper or live authorization.
