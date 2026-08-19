# Stage 1.6A Binance USD-M Futures Delisting Source / Schema / Effective-Time Audit Implementation Plan

**日期:** 2026-08-18  
**状态:** `plan_draft_for_review`  
**Design 输入:** `docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md`  
**Design SHA-256:** `df0ca43518dcb975b437c25a843fa3127ed5f070a60207ae9166530bb50680ab`  
**Plan 编写基线 HEAD:** `2305628072fa6e1d2421e38150694acc78f76acf`  
**当前授权:** 仅编写和审核 Plan；`implementation_allowed = false`、`deployment_allowed = false`、`replay_allowed = false`。  
**安全模式:** `research_shadow_mode`；`RISK_LIVE_TRADING_ENABLED = False`。

## 1. 目标与完成边界

本计划实现一个**离线、显式输入、只读且 fixture/historical-contract-only** 的 Stage 1.6A source/schema/effective-time audit。它从冻结的原始 list/detail bytes 导出 candidate population、revision、semantic facts 和诊断性指标，写入独立 `stage1_6a` output root。

本计划刻意不实现公告网络抓取器。当前没有经过 provenance 审核的 Binance futures-delisting 原始样本，不能根据猜测的 BAPI/HTML schema 写生产网络连接器。因此本版本固定 `source_audit_real_run_allowed=false`、`point_in_time_source_validated=false`、`market_data_coverage_passed=false`：它不得把任意本地 bundle 升级成真实 source/PIT/coverage proof。后续若取得真实 canonical-English list/detail capture，必须在独立 Plan 中实现经过审核的 list parser、只读 connector 与 live collector；该 Plan 不得修改本计划定义的事实、身份或指标分母。

最终 artifact 必须明确写入 `implementation_scope=fixture_historical_contract_only` 与 `source_audit_real_run_allowed=false`。本 Plan 交付的是 source-audit 的 contract/reducer/storage 实现，不是一次真实 Binance source audit。

完成条件：

1. 相同 immutable capture bundle 重跑得到相同 identity、metrics、诊断 verdict 和 `allowed_next_action`。
2. `ListCapture`、`ArticleDiscovery`、`DetailRevision` 和 `SemanticExtraction` 的身份与首次观察时点分离且持久化。
3. 只有完整、可信、canonical-English-detail 证明的 `USD_M + PERPETUAL + crypto_asset` child 可成为 in-scope **contract** audit record；historical rows不具备 PIT evidence authority。
4. 40 个由 ListCapture 导出的冻结 candidate parent 中 30 个通过、10 个 detail unavailable 时，完整的 source-integrity rate 严格为 `30/40`。
5. fixture/historical-contract run 永远不能声明真实 `source_audit_passed`、point-in-time source validated 或 market-data coverage passed。
6. 只有存在 hash-verified `completion_manifest.status=complete` 的 root 才可被 `load_completed_audit()` 消费；所有 partial/crashed root 都只能诊断、不得重用。
7. 不读取、不写入、不重启 Stage 1.5D/F/G root；不产生任何 signal、replay、risk-veto enforcement、纸盘或实盘行为。

## 2. 已确认架构选择与 Preflight 证据

### 2.1 选择独立 Stage 1.6A 契约，而非扩展 Stage 1.5A

执行前已做的源码和拓扑证据：

| 现有对象 / 查询 | 证据 | 结论 |
|---|---|---|
| `RawSourcePayload` | `stage1_5a_source_audit_models.py` 只表达单个 raw input；Graphify 直系链路通向 1.5A loader、normalizer、summary、runner 和其 tests。 | 可借鉴 raw-hash 与只读模式；不修改、不作为 1.6A runtime schema。 |
| `NormalizedExternalEvent` | 1.5A normalizer 为单 symbol/event 生成 title-level `DELISTING`；Graphify 下游包括 1.5A summary/runner/tests。 | 无 parent/child completeness、detail revision 或 semantic extraction，不能承载本 Design。 |
| `load_or_fetch_payloads` | Graphify 显示其依赖 1.5A allowlist、generic source profiles 与 network caching。 | 不复用为 1.6A runtime dependency；本 Plan 不写网络 connector。 |
| `compute_payload_sha256` | 仅是 `hashlib.sha256` 薄包装，Graphify 下游均在 1.5A。 | 1.6A 直接使用 Python `hashlib`，避免跨阶段依赖。 |
| Stage 1.5D BAPI parser | 仅为 futures launch schema 和运行 root 服务。 | 不导入、不修改、不读取其 raw payload 或 live root。 |

这不是重复造轮子：新模型至少需要 parent declaration、child accounting、list/detail/semantic 三类 identity、fact evidence pointer、immutable candidate denominator 和 historical/live capture-time 语义，均不属于现有 1.5A 单事件模型。

### 2.2 最小模块边界

| 模块 | 单一职责 | 不负责的事项 |
|---|---|---|
| `stage1_6a_futures_delisting_models.py` | 常量、枚举、dict contract validation 和 deterministic identity helpers。 | IO、网络、策略判断。 |
| `stage1_6a_futures_delisting_audit.py` | capture-bundle reducer、scope/classification、schedule fact evidence、metric populations。 | 文件写入、HTTP。 |
| `stage1_6a_futures_delisting_summary.py` | config-SSOT gate 与只读 summary/next action。 | 修正、补造或过滤输入。 |
| `stage1_6a_futures_delisting_storage.py` | output-root confined append/atomic JSON writes、artifact hash、completion manifest 与 completed-root reload。 | compaction、跨 root 迁移、Stage 1.5 IO。 |
| `run_stage1_6a_futures_delisting_source_audit.py` | CLI、input preflight、调用 reducer/summary、写独立 artifacts。 | 网络请求、持续 daemon、策略/执行。 |

使用 `dataclasses`、`hashlib`、`json`、`pathlib`、`base64`、`unicodedata` 和 `tempfile` 标准库；不新增第三方依赖、registry、factory、接口层、worker 或配置项。capture bundle 是一次性命令行输入，不新增“通用 source profile”配置。`ArticleDiscovery`、semantic facts、evidence pointers、coverage verdict 与 completion status 均为 reducer/output 所有，绝不接受 caller supplied authority。

## 3. Allowed Change Scope

Allowed implementation paths:

- `configs/base.py` - 仅新增 Design §7.4 列出的八个 `EXTERNAL_SIGNAL_STAGE1_6A_*` research-audit constants；不得修改任何既有 assignment。
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_summary.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py`
- `scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py`

Allowed verification paths:

- `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py`
- `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py`
- `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py`
- `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py`
- `tests/fixtures/external_signal_shadow/stage1_6a/**` - only bounded fixture captures plus a provenance manifest; all synthetic cases must say `fixture_origin=synthetic`.
- `tests/research/external_signal_shadow/test_stage1_5a_source_audit_models.py` - read-only compatibility regression only.
- `tests/research/external_signal_shadow/test_stage1_5a_source_audit_normalizer.py` - read-only compatibility regression only.
- `tests/research/external_signal_shadow/test_stage1_5a_source_audit_summary.py` - read-only compatibility regression only.
- `tests/scripts/external_signal_shadow/test_run_stage1_5a_historical_event_source_audit.py` - read-only compatibility regression only.

Allowed documentation paths:

- `docs/plans/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-implementation-plan_CN.md` - this Plan only; do not edit the approved Design during implementation.

Allowed generated/runtime artifacts:

- `data/external_signal_shadow/stage1_6a/**` - generated only, local-only, never committed.
- `.pytest_cache/**` - generated by pytest only, never committed.

Affected but unchanged:

- `src/research/external_signal_shadow/stage1_5a_source_audit_models.py`
  - compatibility evidence: four listed Stage 1.5A tests pass unchanged; Graphify confirms existing consumers remain confined to 1.5A.
- `src/research/external_signal_shadow/stage1_5a_source_audit_loader.py`
  - compatibility evidence: no Stage 1.6A import; static import test must reject it.
- `src/research/external_signal_shadow/stage1_5a_source_audit_normalizer.py`
  - compatibility evidence: no Stage 1.6A import; `test_stage1_5a_source_audit_normalizer.py` passes unchanged.
- `src/research/external_signal_shadow/stage1_5a_source_audit_summary.py`
  - compatibility evidence: `test_stage1_5a_source_audit_summary.py` passes unchanged.
- `scripts/external_signal_shadow/run_stage1_5a_historical_event_source_audit.py`
  - compatibility evidence: its runner tests pass unchanged.
- `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- `src/strategies/**`, `src/risk/**`, `src/execution/**`
  - compatibility evidence: Stage 1.6A static isolation test finds no import, call, output-path or CLI wiring to these paths.

Forbidden:

- Any mutation outside the exact allowed paths.
- Any Stage 1.5D/F/G root read/write, runtime process control, live collector restart, watermark change, or deployment instruction.
- Any HTTP request, web scraping, BAPI/HTML connector, retry loop, daemon, cron/tmux command or `--source-url` option.
- Caller-supplied `article_discovery`, `audit_candidate_manifest`, semantic fact, evidence pointer, derived identity, scope decision, `live_observed` provenance, coverage verdict or completion status.
- A `--output-summary` override, any write outside the resolved `--output-root`, or any production output root outside `data/external_signal_shadow/stage1_6a/`.
- Any replay, market return, MAE/MFE, net-edge, alpha, `SignalCandidate`, `TradeIntent`, risk-veto enforcement, paper trading, live trading or execution wiring.
- Any `configs/base.py` change other than the eight approved Stage 1.6A constants.
- `ruff check --fix .`, `ruff format .`, `git clean`, `git reset --hard`, global formatter/autofix, `graphify update`, or mutation of `graphify-out/**`.
- Treating a synthetic/local fixture as canonical official evidence or allowing it to set `source_audit_passed=true`.
- Allowing this no-connector implementation to set `point_in_time_source_validated=true` or `market_data_coverage_passed=true`.

## 4. Execution Preconditions and Stop Conditions

### 4.1 Execution preflight

Task 0 must run before creating any implementation file:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export BASE_SHA="$(git rev-parse HEAD)"
export DESIGN_SHA256="$(shasum -a 256 docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md | awk '{print $1}')"
export PLAN_SHA256="$(shasum -a 256 docs/plans/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-implementation-plan_CN.md | awk '{print $1}')"
export CONFIG_BASELINE_PATH="${TMPDIR:-/tmp}/stage1_6a-config-base-${BASE_SHA}.py"
git status --short --untracked-files=all
printf 'BASE_SHA=%s\nDESIGN_SHA256=%s\nPLAN_SHA256=%s\n' "$BASE_SHA" "$DESIGN_SHA256" "$PLAN_SHA256"
test "$DESIGN_SHA256" = "df0ca43518dcb975b437c25a843fa3127ed5f070a60207ae9166530bb50680ab"
cp configs/base.py "$CONFIG_BASELINE_PATH"
printf 'CONFIG_BASELINE_PATH=%s\n' "$CONFIG_BASELINE_PATH"
python3 - configs/base.py <<'PY'
import ast
import sys
from pathlib import Path

tree = ast.parse(Path(sys.argv[1]).read_text(encoding="utf-8"))
names = {
    node.targets[0].id
    for node in tree.body
    if isinstance(node, ast.Assign)
    and len(node.targets) == 1
    and isinstance(node.targets[0], ast.Name)
}
assert not {name for name in names if name.startswith("EXTERNAL_SIGNAL_STAGE1_6A_")}, (
    "STOP: Stage 1.6A config names already exist; revise the approved AST delta"
)
PY

graphify query 'RawSourcePayload'
graphify query 'NormalizedExternalEvent'
graphify query 'load_or_fetch_payloads'
graphify path 'run_stage1_5a_historical_event_source_audit.py' 'normalize_payload'

rg -n 'stage1_5a_source_audit|stage1_5d_live_event_source|stage1_5f_live_depth|SignalCandidate|TradeIntent' \
  src/research/external_signal_shadow scripts/external_signal_shadow
```

Record the output in the execution ledger, not in source code. The approved untracked Design and Plan are pre-existing work: record both SHA values above; do not delete, overwrite or count either as implementation output. If any other dirty/untracked path appears, preserve it and stop for user direction.

### 4.2 Mandatory stop conditions

Stop the batch and return to Design/Plan review if any condition is true:

1. A real canonical-English source payload schema is required, or the fixture-capture parser would need guessed Binance fields, before a separate connector/list-parser Plan is approved.
2. `RawSourcePayload` or another Stage 1.5A schema would need a behavioral modification, or a Stage 1.5D/F/G module becomes a required runtime dependency.
3. A requirement needs a network fetcher, live daemon, historical market data, replay metric, strategy/risk/execution consumer or new permission.
4. Any fixture lacks `fixture_origin`, raw bytes/hash, locale, request variant, source URL/domain or `historical_backfill` capture mode.
5. Any implementation could make this no-connector run report `source_audit_passed=true`, `point_in_time_source_validated=true`, `market_data_coverage_passed=true`, `replay_allowed=true` or an execution/alpha permission true.
6. A read-only Stage 1.5A regression fails and requires changing a Stage 1.5A contract to pass.
7. A shared config assignment outside the exact eight constants changes, or a new threshold is needed.
8. Targeted tests reveal an unplanned consumer or any test outside Allowed paths needs modification.

## 5. Invariant-to-Task Mapping

| Invariant | Production entry point / persistence | Tasks | Mechanical evidence |
|---|---|---|---|
| INV-01, INV-17 | `classify_delisting_child`, parent reducer | 2, 3 | USD-M crypto accepted; COIN-M/TradFi/spot/margin/unknown isolated tests. |
| INV-02, INV-13, INV-15, INV-16 | ListCapture-derived discovery/revision/extraction reducers; JSONL artifacts | 2, 4 | R1/R2 information-set, historical capture and parser-upgrade RED tests. |
| INV-03, INV-04 | schedule fact parser/evidence pointer validator | 3 | present/not_stated/unparseable/conflicting and no inferred reduction tests. |
| INV-05 | parent completeness reducer | 3 | mixed and incomplete batch all-or-none eligibility tests. |
| INV-06, INV-14 | deterministic identity functions; append-only artifact writer | 2, 4 | list-change, locale/variant, duplicate hash and changed-hash tests. |
| INV-07, INV-08 | coverage fail-closed reducer / summary | 5 | every coverage input is `not_evaluable`; no directional output keys test. |
| INV-09, INV-10, INV-12 | runner and static isolation test | 1, 6 | config safety assertion; no Stage 1.5/strategies/risk/execution imports or paths. |
| INV-11 | capture-bundle reload/replay; completion manifest | 4, 6 | identical completed-root IDs/verdict; partial root is rejected. |
| INV-18 | summary metric builder | 1, 5 | exact config tests; frozen denominator 30/40 and next-action matrix. |

## 6. Task Sequence

### Task 0 - Baseline, scope lock and fixture provenance skeleton

**Design invariants:** all; this task establishes their auditable baseline.  
**Files:** only the Plan during preflight; then allowed Stage 1.6A fixture directory and test files as needed by later RED tests.

1. Record `BASE_SHA`, full `git status`, Design SHA and exact Graphify outputs from §4.1.
2. Confirm `tests/fixtures/external_signal_shadow/stage1_6a/` does not contain a fixture whose provenance falsely claims official/live evidence. Create a compact `fixture_manifest.json` with per-file SHA-256, `fixture_origin` (`synthetic` or `frozen_official_capture`), and the fixed `capture_mode=historical_backfill`; it must explicitly prohibit interpreting any fixture as real source/PIT/coverage proof.
3. Define the one authoritative input format before parser code: a UTF-8 JSONL capture bundle containing **only** `list_capture` and `detail_observation` records. In this fixture/historical-contract implementation, the resolved `--capture-bundle` must be a regular file below resolved `tests/fixtures/external_signal_shadow/stage1_6a/`; `..` and symlink resolution must remain in that directory before the runner opens the file. `list_capture` provides raw list bytes plus transport metadata; the reducer parses its fixture-capture list representation, applies `candidate_discovery_rule_v1`, derives `ArticleDiscovery`, and freezes the manifest before it inspects any detail row. `detail_observation` provides only transport/source facts: `source_article_id`, `source_surface`, `source_locale`, `request_variant`, `source_url`, `raw_payload_base64`, `observed_at_ms`, `capture_mode`, and optional supplied raw SHA-256 for consistency checking. The reducer hashes decoded raw bytes, normalizes body text, derives semantic facts/evidence pointers and rejects contradictory raw hashes.
4. Explicitly forbid capture-bundle records/keys for `article_discovery`, `audit_candidate_manifest`, `settlement_time_ms`, `fact_parse_status`, normalized byte spans, excerpts, `semantic_extraction_id`, `source_audit_eligible`, `risk_veto_candidate`, `live_observed`, `market_data_coverage`, coverage pass flags, verdicts and completion status.
5. Add RED runner test cases for malformed JSONL, missing required provenance, unsupported locale/variant, invalid base64, invalid scheme/host/surface, a supplied derived-field injection, a supplied discovery subset/injection, an offline bundle claiming `live_observed`, any attempt to claim source/PIT/coverage pass, a Stage 1.5-root input path, `..` escape, and fixture-root symlink escape. Every rejected path must fail before the file is opened.
6. Add candidate-recall diagnostic fixture variants. The primary rule remains frozen; a broader diagnostic probe reports `candidate_discovery_false_negative_count`. It cannot add an article to the already frozen primary manifest. Any nonzero count makes this fixture/historical-contract audit inconclusive.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py -q
```

Expected before implementation: the new contract tests fail for missing runner/module behavior, not because unrelated tests are changed.

### Task 1 - Config SSOT and safety RED tests

**Design invariants:** INV-09, INV-18.  
**Files:** `configs/base.py`, `test_stage1_6a_futures_delisting_summary.py`, `test_run_stage1_6a_futures_delisting_source_audit.py`.

1. Write RED tests that import and assert the exact eight constants and values from Design §7.4:

```python
EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS == 30
EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS == 10
EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS == 3
EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO == 0.95
EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO == 0.95
EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO == 0.95
EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT == 0
EXTERNAL_SIGNAL_STAGE1_6A_MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES == 1
```

2. Add an AST regression test that requires the eight new names to be exactly-once top-level, single-target assignments and checks their exact values. Task 7 performs the separate execution-baseline comparison against the Task 0 snapshot, so the test never depends on a machine-local `/tmp` file.
3. Add static runner-output safety assertions: `RISK_LIVE_TRADING_ENABLED is False`; every output has `trade_signal_allowed`, `paper_trading_allowed`, `live_trading_allowed`, `execution_engine_allowed`, `alpha_interpretation_allowed`, `replay_allowed`, and `point_in_time_directional_replay_allowed` as `False`.
4. GREEN: add only the eight constants to `configs/base.py`, grouped under a Stage 1.6A research-audit comment. No timeout, URL, source-profile, fee, market-data or trading constant is permitted.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py -q
```

The final implementation check in Task 7 compares against the Task 0 AST snapshot; it must not require `configs/base.py` to be byte-identical because eight approved additions are expected.

### Task 2 - Identity and capture-bundle contract

**Design invariants:** INV-02, INV-06, INV-11, INV-13, INV-14, INV-16.  
**Files:** `stage1_6a_futures_delisting_models.py`, `stage1_6a_futures_delisting_audit.py`, matching model/audit tests and fixtures.

1. Write RED tests for canonical Unicode/case-folded title discovery **derived only from raw ListCapture**, frozen first discovery time, list identity, DetailRevision identity and SemanticExtraction identity. Test that list A/B/C plus supplied discovery A/B is rejected, list A/B plus injected C is rejected, and later parse success cannot alter the frozen A/B candidate denominator. Test exact formulas:

```text
detail_revision_id = sha256(source_article_id | source_surface | source_locale | request_variant | detail_raw_sha256)
semantic_extraction_id = sha256(detail_revision_id | semantic_extractor_version | body_normalization_version | canonical_fact_fingerprint)
```

`semantic_extracted_at_ms` and repeated-observation wall clock time must not enter either identity.
2. Add counterexamples: unrelated article changes only `ListCapture`; repeated same canonical detail hash preserves earliest `revision_first_observed_at_ms`; a changed canonical English hash creates a new DetailRevision; non-English or a different request variant cannot merge into canonical English revision lineage.
3. Implement dict-level validation and deterministic `json.dumps(..., sort_keys=True, separators=(',', ':'))` fingerprints. Validate `https` Binance official host and expected announcement source surface exactly; reject look-alike domains, plain HTTP, locale/variant mismatch, non-canonical semantic authority and all supplied derived-field injection rather than guessing.
4. Normalize and extract only from decoded raw detail bytes. Evidence pointers, normalized byte offsets, excerpts, `canonical_fact_fingerprint`, schedule facts and `semantic_extraction_id` are reducer outputs. Synthetic expected offsets/excerpts belong only in pytest expectations, never in a capture bundle.
5. Freeze historical-backfill semantics: `semantic_extracted_at_ms` is the actual current extraction time, while `system_available_at_ms=None`, `fact_available_at_ms=None`, `capture_time_status=historical_unknown`, and `point_in_time_replay_eligible=false`. Add a mechanical regression where old historical raw bytes parse successfully today and asserts precisely those values. This implementation accepts only `historical_backfill`; it rejects `live_observed` and never reports point-in-time validation.
6. Keep the R1/R2 11:00/13:00 case as a **pure reducer semantic/version contract only**: it proves that a version-selecting reducer does not expose R2 in an earlier information set. The historical runner must not emit PIT evidence, `system_available_at_ms`, or `fact_available_at_ms` from that test. A future attested live collector Plan alone may add the `live_observed` branch where validated `system_available_at_ms` is present.
7. Do not import `stage1_5a_source_audit_*` or Stage 1.5D/F modules. Use `hashlib`, `json`, `base64`, `unicodedata` and `urllib.parse` only. `urllib.request`, `requests`, `httpx`, `aiohttp` and `socket` are forbidden.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py -q
```

### Task 3 - Scope, batch completeness and schedule-fact reducer

**Design invariants:** INV-01, INV-03, INV-04, INV-05, INV-17.  
**Files:** `stage1_6a_futures_delisting_audit.py`, `test_stage1_6a_futures_delisting_audit.py`, bounded fixtures.

1. Write RED tests for accepted `USD_M + PERPETUAL + crypto_asset` child and each excluded family: COIN-M, TradFi perpetual, spot, margin, loan, Convert, pair-only and unknown underlying. `crypto_asset` requires positive canonical-English detail evidence; current exchangeInfo/symbol names/manual classifications are prohibited test inputs.
2. Write parent/child tests: single contract, complete homogeneous batch, complete mixed batch with known out-of-scope sibling, and incomplete batch. A mixed parent may yield in-scope children only after every declared child is accounted; a missing/ambiguous symbol or market fact yields no eligible subset.
3. Define and test schedule facts separately: `order_restriction_start`, `last_trading_time`, `settlement_time`, `final_hour_start`. Each record contains `fact_parse_status`, `capture_time_status`, DetailRevision ID, SemanticExtraction ID, `fact_available_at_ms`, and evidence pointer with normalized UTF-8 byte bounds. `present` requires all evidence; no restriction language means `not_stated` and `order_restriction_type=None`, never inferred.
4. Add the R1/R2 test: R1 extracted at 10:00 says settlement 18:00, R2 extracted at 12:00 says 20:00. The reducer’s 11:00 information set sees only R1; 13:00 can see R2.
5. GREEN with explicit enums/strings from Design only. No generic asset registry and no heuristic fallback.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py -q
```

### Task 4 - Isolated persistence and restart determinism

**Design invariants:** INV-02, INV-06, INV-11, INV-12, INV-13, INV-14, INV-15.  
**Files:** `stage1_6a_futures_delisting_storage.py`, `run_stage1_6a_futures_delisting_source_audit.py`, storage/runner tests.

1. Write RED storage/runner tests enforcing production `--output-root` as a new descendant of resolved `data/external_signal_shadow/stage1_6a/`; independently enforce `--capture-bundle` under the resolved Stage 1.6A fixture root defined in Task 0. The runner accepts only `--capture-bundle`, `--output-root` and explicit `--fixture-run`; it has no `--output-summary` override. Every persistent artifact path must resolve under the resolved output root; `..` traversal, symlink escape, existing root reuse and any Stage 1.5 data-plane input/output path are rejected. Tests use a temporary working directory that mirrors the production relative roots, not a relaxed production path rule.
2. Persist append-only JSONL artifacts for captures, reducer-derived discoveries, revisions, semantic extractions, notices/children, diagnostics and the frozen `audit_candidate_manifest`; write the fixed-name summary atomically at `<output_root>/stage1_6a_futures_delisting_source_audit_summary.json`. The summary may state only `audit_summary_state=pre_completion`; it must never state or imply authoritative `status=complete`. Artifact rows must include their identity, raw hash (when applicable), historical capture mode and source evidence. The manifest must be created before any detail parsing/classification and later records may only change result fields, never denominator membership.
3. Create `<output_root>/completion_manifest.json` atomically **last**. It is the sole durable authority allowed to contain `status=complete`, and contains `run_id`, capture-bundle SHA-256, candidate-manifest SHA-256, summary SHA-256, plus hashes/counts for every authoritative artifact **excluding completion_manifest itself**. `load_completed_audit(root)` accepts only a `status=complete` manifest whose recorded hashes verify; no manifest, malformed manifest, hash mismatch or incomplete root is rejected and preserved as diagnostic-only.
4. Simulate crashes after candidate manifest, detail revision, child artifact and summary but before completion manifest. Assert every partial root is rejected by `load_completed_audit`; specifically, a summary may exist after the final crash but is `pre_completion` and cannot claim complete. A complete root reloads deterministically. Rerun only in a new root; do not add same-root resume.
5. Write/reload/re-run the same immutable bundle. Assert byte-stable canonical row bodies where order is fixed, same manifest hash, same IDs, same earliest first-observed times, same populations and same diagnostic summary. A historical fixture remains `capture_time_status=historical_unknown` and cannot become point-in-time eligible after restart.
6. Do not implement retention, compaction, lock coordination, online migration, background recovery or a daemon. A one-shot audit root is sufficient for this stage.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py -q
```

### Task 5 - Metric populations, verdict decomposition and data-honesty gates

**Design invariants:** INV-07, INV-08, INV-13, INV-18.  
**Files:** `stage1_6a_futures_delisting_summary.py`, `test_stage1_6a_futures_delisting_summary.py`, `test_stage1_6a_futures_delisting_audit.py`.

1. Write RED tests for the frozen `stage1_6a_audit_metric_v1` definitions:
   - 40 immutable candidate parents, 30 complete/trusted and 10 detail unavailable -> `source_integrity_pass_rate == 30 / 40`, never `30 / 30`.
   - `historical_events_found` counts one parent article per batch; `symbols_with_events` counts distinct eligible child symbols; `event_days` uses UTC `source_published_at_ms` only when present, never settlement date.
   - Mapping rate is notice-level and one unaccounted declared child fails the numerator.
   - Classification rate leaves ambiguous/conflicting/unresolved trusted-detail parents in denominator and outside numerator.
   - rejected WAF/non-English payload is not forbidden; non-English/non-Binance payload used or attempted as semantic authority increments `forbidden_payload_count` and fails the gate.
2. Implement source-schema, sample-sufficiency, point-in-time source and market-coverage predicates independently. The `source_audit_passed` predicate must exclude point-in-time and market-coverage verdicts exactly as Design §7.3 specifies, but this no-connector implementation applies an immutable authority cap: `source_audit_passed=false`, `point_in_time_source_validated=false` and `market_data_coverage_passed=false` for every run. Diagnostic candidate predicate values may be reported under clearly separate `*_candidate` names only.
3. Reject any `market_data_coverage` bundle record or caller-supplied coverage boolean. Emit price/L2/funding/OI/fee coverage as `not_evaluable`, `market_data_coverage_passed=false`, and no coverage identity/hash claim. No caller input can advance `allowed_next_action` beyond `write_live_source_observation_design_only` / `source_audit_contract_fixture_only`.
4. Implement fixture/historical-contract override: summary must set `source_audit_passed=false`, `point_in_time_source_validated=false`, `market_data_coverage_passed=false`, `replay_allowed=false` and an inconclusive/contract-only next action even if rows numerically meet all thresholds.
5. Assert no directional return, MAE, MFE, PnL, fee estimate or alpha claim key is emitted.
6. Add next-action tests: failed/inconclusive source -> no replay Design; no-connector historical/fixture run -> only live-source observation design; hypothetical future all-prerequisites behavior may be unit-tested as a pure predicate but must not be reachable through this runner and never authorizes replay execution.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py -q
```

### Task 6 - Runner integration and explicit isolation proof

**Design invariants:** INV-08, INV-09, INV-10, INV-12, INV-18.  
**Files:** runner, runner tests, model/audit/summary tests.

1. Wire the one-shot runner with no network imports and no default source/output path. `--capture-bundle` and `--output-root` are required; capture bundle resolution is confined to the fixture root, production output is a new descendant of `data/external_signal_shadow/stage1_6a/`, and the summary filename is fixed within that root.
2. Include report fields: `implementation_scope=fixture_historical_contract_only`, `source_audit_real_run_allowed=false`, Design/metric version, capture-bundle hash, manifest hash, non-authoritative `audit_summary_state=pre_completion`, source/schema/sample/point-in-time/coverage diagnostic predicates, counts/denominators/numerators, `risk_veto_candidate=false`, all false safety flags, and an authority-capped `allowed_next_action`. Completion status is not a summary field.
3. Add a static AST/import/path regression covering every new Stage 1.6A production file. It must fail if it imports/calls Stage 1.5A/1.5D/F/G modules, `strategies`, `risk`, `execution`, `requests`, `httpx`, `aiohttp`, `socket`, `urllib.request`, or `subprocess`, or writes outside the resolved Stage 1.6A output root. `urllib.parse` is allowed only for URL validation and must not be used to open a network connection. The regression must also fail if output exposes `SignalCandidate`, `TradeIntent`, true execution/PIT/coverage authority flags, non-false `risk_veto_candidate`, a source URL CLI option, `--output-summary`, or caller-supplied derived evidence fields.
4. Run the fixture runner twice in separate temporary roots that satisfy the same fixture-input and `data/external_signal_shadow/stage1_6a/` output containment rules. Verify deterministic semantic identities and diagnostic metrics, a valid completion manifest, `fixture_run=true`, historical capture semantics, `risk_veto_candidate=false`, and all source/PIT/coverage/replay/execution authority false.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py -q
```

### Task 7 - Completion gate and independent audit preparation

**Design invariants:** all.  
**Files:** no new production or documentation files.

1. Run the complete approved suite, including read-only Stage 1.5A compatibility regressions:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_models.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_normalizer.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5a_historical_event_source_audit.py \
  -q

test "$(shasum -a 256 docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md | awk '{print $1}')" = "$DESIGN_SHA256"
test "$(shasum -a 256 docs/plans/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-implementation-plan_CN.md | awk '{print $1}')" = "$PLAN_SHA256"

.venv/bin/ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py \
  src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py \
  src/research/external_signal_shadow/stage1_6a_futures_delisting_summary.py \
  src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py \
  scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py

git diff --check "$BASE_SHA"
git diff --name-only "$BASE_SHA"
git diff --exit-code "$BASE_SHA" -- \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_models.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_normalizer.py \
  tests/research/external_signal_shadow/test_stage1_5a_source_audit_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5a_historical_event_source_audit.py
python3 - "$CONFIG_BASELINE_PATH" configs/base.py <<'PY'
import ast
import sys
from collections import Counter
from pathlib import Path

baseline = ast.parse(Path(sys.argv[1]).read_text(encoding="utf-8"))
current = ast.parse(Path(sys.argv[2]).read_text(encoding="utf-8"))
allowed = {
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS",
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS",
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS",
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO",
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO",
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO",
    "EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT",
    "EXTERNAL_SIGNAL_STAGE1_6A_MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES",
}

def name(node):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None

extra = [node for node in current.body if name(node) in allowed]
assert Counter(name(node) for node in extra) == Counter({key: 1 for key in allowed})
baseline_body = [node for node in baseline.body if name(node) not in allowed]
current_body = [node for node in current.body if name(node) not in allowed]
assert ast.dump(ast.Module(body=baseline_body, type_ignores=[]), include_attributes=False) == ast.dump(
    ast.Module(body=current_body, type_ignores=[]), include_attributes=False
), "STOP: configs/base.py changed outside the eight approved Stage 1.6A assignments"
PY
python3 - "$BASE_SHA" <<'PY'
import subprocess
import sys

base_sha = sys.argv[1]
allowed_exact = {
    "configs/base.py",
    "src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py",
    "src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py",
    "src/research/external_signal_shadow/stage1_6a_futures_delisting_summary.py",
    "src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py",
    "scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py",
    "tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py",
    "tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py",
    "tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_summary.py",
    "tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py",
    "docs/plans/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-implementation-plan_CN.md",
}
allowed_prefixes = ("tests/fixtures/external_signal_shadow/stage1_6a/",)
changed = subprocess.check_output(
    ["git", "diff", "--name-only", base_sha], text=True
).splitlines()
status = subprocess.check_output(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"], text=True
).splitlines()
untracked = [line[3:] for line in status if line.startswith("?? ")]
preexisting = {
    "docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md",
    "docs/plans/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-implementation-plan_CN.md",
}
all_paths = set(changed) | set(untracked)
unexpected = [p for p in sorted(all_paths) if p not in allowed_exact and not p.startswith(allowed_prefixes) and p not in preexisting]
assert not unexpected, f"STOP: changed paths outside Allowed Change Scope: {unexpected}"
PY
rg -n 'RISK_LIVE_TRADING_ENABLED\s*=\s*True|source_audit_passed\s*[:=]\s*True|point_in_time_source_validated\s*[:=]\s*True|market_data_coverage_passed\s*[:=]\s*True|risk_veto_candidate\s*[:=]\s*True|trade_signal_allowed\s*[:=]\s*True|paper_trading_allowed\s*[:=]\s*True|live_trading_allowed\s*[:=]\s*True|execution_engine_allowed\s*[:=]\s*True|alpha_interpretation_allowed\s*[:=]\s*True' \
  configs/base.py src/research/external_signal_shadow/stage1_6a_* scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py
```

2. The last `rg` must produce no match. The zero-diff compatibility command and exact scope script are hard gates; any unexpected file is a scope failure, not something to clean up automatically.
3. Invoke `audit-plan-completion` in a separate agent/session with `BASE_SHA`, Design SHA, `PLAN_SHA256`, scope matrix and actual command output. Completion is valid only on verdict `complete`.

## 7. Review Checklist Before Execution

This Plan must receive `Approve` from `reviewing-implementation-plans` and explicit user approval before coding. The reviewer must confirm:

1. Every allowed source/test/document/generated path is necessary and no wildcard exceeds a bounded fixture/output family.
2. The preflight Graphify findings support isolation rather than a missed consumer.
3. The Plan adds no live connector; `capture bundle` is an explicit, local input boundary, not a disguised fetcher.
4. Fixture success cannot prove a real source audit; both fixture and historical capture-time semantics remain fail-closed.
5. Metrics use frozen manifest membership and exact parent/child counting units, especially the `30/40` regression.
6. No code path reads or writes Stage 1.5 roots or imports strategy/risk/execution modules.
7. No new abstraction, dependency, threshold, worker, persistence compaction, or deployment task is speculative.

## 8. Handoff Contract

Before implementation, the executor records:

```text
BASE_SHA=<current HEAD immediately before code changes>
PLAN_SHA256=<sha256 of this approved Plan>
DESIGN_SHA256=df0ca43518dcb975b437c25a843fa3127ed5f070a60207ae9166530bb50680ab
preexisting_dirty_path=docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md
preexisting_dirty_path_sha256=df0ca43518dcb975b437c25a843fa3127ed5f070a60207ae9166530bb50680ab
```

The implementation may start only after Plan review is `Approve` and the user explicitly authorizes execution. It does not authorize a commit, deployment, live collector, replay, risk-veto enforcement or any change to Stage 1.5D/F runtime.
