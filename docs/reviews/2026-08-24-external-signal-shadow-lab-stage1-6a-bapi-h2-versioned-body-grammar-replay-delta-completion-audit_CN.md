# Stage 1.6A BAPI H2 Versioned Body Grammar Replay Delta Completion Audit Report (Re-Audit)

- **Date**: 2026-08-24
- **Audit Target Plan**: `docs/plans/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-implementation-plan_CN.md`
- **Plan SHA-256**: `a5d23924fc705d78d06e34425d613689a1d44029b1d58f8368e5a1fc2489b7f0`
- **H2 Design SHA-256**: `f31e9a64f42fcd1eccfab94efa5c9328fbdc154a9ae70880e359bfc701306987`
- **Implementation Baseline (BASE_SHA)**: `d1f7ee2d9d8eb37389feeed912ff13d34fba8e05`
- **Audit Skill**: `.agent/skills/audit-plan-completion`
- **Verdict**: `complete`

---

## 1. Executive Summary & Findings (Re-Audit)

### Prior Issues & Remediations Verification
- **P0 (Resolved)**: 在 `stage1_6a_sealed_export_adapter.py` 的 `reduce_verified_snapshot` 中，原代码曾混入额外改动并移除了 `zero_observations_for_candidate` 校验。现已严格返修恢复：
  - 当候选公告的 observation 集合为空时，严格抛出 `AdapterInputError(f"zero_observations_for_candidate: {aid}")`。
  - 不做任何未批准的控制记录复制或任意状态码扩散。
  - 自动化测试与独立断言均已证实该结构性拒绝严格生效。
- **P1 (Resolved)**: 修正了完成报告中关于 G2 候选总分母的文本描述。Durable summary 的 `metrics.candidate_total_denominator` 实际且准确记录为 **`35`**（35 个可信历史退市候选公告），带事件标的数为 **`44`**（`symbols_with_events=44`）。

### Findings Classification
- **P0 Safety / Scope Blockers**: 0
- **P1 Technical / Contract Defects**: 0
- **P2 Minor / Residual Notes**: 0

### Final Verdict: `complete`
所有计划内的 6 项任务（Task 0 ~ Task 5）、10 项设计不变量（INV-H2-01 ~ INV-H2-10）以及变更范围边界（Allowed Change Scope）均已 100% 严格执行与硬验证通过。

---

## 2. Scope Matrix

| Path | Category | Status | Provenance / Verification |
|---|---|---|---|
| `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py` | Allowed implementation | Modified | Implemented `GrammarPair`, `_GRAMMAR_RULES`, H2 parser, G2 reduction dispatch, restored frozen `zero_observations_for_candidate` check |
| `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py` | Allowed implementation | Modified | Implemented G2 writer gate, consumer pair admission & projection validation before source reduction |
| `scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py` | Allowed implementation | Modified | Passed `G2_GRAMMAR_PAIR` to `reduce_verified_snapshot` |
| `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py` | Allowed verification | Modified | Added G1 vs G2 grammar parsing, H2 tree normalization, REEF extraction, distinct semantic IDs, and zero-obs rejection tests |
| `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py` | Allowed verification | Modified | Added writer G1 rejection, consumer pair mismatch, projection mismatch, and unsupported pair tests |
| `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/h2_g2_remediated_20260824T061701Z` | Allowed runtime generated | Created after P0 remediation | Fresh local G2 audit root generated from the frozen sealed export and independently verified by consumer |
| `docs/plans/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-implementation-plan_CN.md` | Allowed documentation | Unchanged | Exact SHA `a5d23924fc705d78d06e34425d613689a1d44029b1d58f8368e5a1fc2489b7f0` |
| `docs/reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md` | Allowed documentation | Created | This completion audit artifact |
| `configs/base.py` | Affected-but-unchanged | Preserved | Zero diff from `BASE_SHA`; `RISK_LIVE_TRADING_ENABLED = False` |
| `src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py` | Affected-but-unchanged | Preserved | Zero diff from `BASE_SHA` |
| `src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py` | Affected-but-unchanged | Preserved | Zero diff from `BASE_SHA` |

---

## 3. Invariant & Task Execution Matrix

| Invariant / Task | Requirement | Code / Test Evidence | Status |
|---|---|---|---|
| **INV-H2-01** | Explicit grammar-pair SSOT | `stage1_6a_sealed_export_adapter.py:46-60`, `G1_GRAMMAR_PAIR`, `G2_GRAMMAR_PAIR` | Verified |
| **INV-H2-02** | Exact REEF H2 parsing | `stage1_6a_sealed_export_adapter.py:127-142`, `_extract_bapi_body_text_v2` parses `p/h2` children | Verified |
| **INV-H2-03** | Structural heading preservation | `p/h2` retains `\n\n` boundary separation; regex `\s*` handles variations | Verified |
| **INV-H2-04** | Fail-before-source consumer | `stage1_6a_sealed_export_adapter_storage.py:374-376`, validated before `load_verified_source_snapshot` | Verified |
| **INV-H2-04a** | Complete rejection taxonomy | `test_stage1_6a_sealed_export_adapter_storage.py:417-595`, spy confirms 0 calls to `load_verified_source_snapshot` | Verified |
| **INV-H2-05** | Production writer rejects G1 | `stage1_6a_sealed_export_adapter_storage.py:134-136`, raises `new_writer_requires_g2_grammar_pair` | Verified |
| **INV-H2-06** | Read-only G1 replay | `sealed_export_audit_e9ec315753ea_20260823T095847Z` replayed read-only: `PASS`, `source_audit_passed=False` | Verified |
| **INV-H2-07** | Pure historical backfill scope | No live, network, or Stage 1.6B mutation performed | Verified |
| **INV-H2-08** | All authority flags False | `h2_g2_remediated_20260824T061701Z/completion_manifest.json`, 12 authority flags all `False` | Verified |
| **INV-H2-09** | Manifest-last atomic write | `stage1_6a_sealed_export_adapter_storage.py:270-295`, tempdir -> rename atomically | Verified |
| **INV-H2-10** | Permitted Change Scope | Preflight provenance verified, zero out-of-scope files | Verified |
| **Task 0** | Preflight Provenance & Hashes | Passed 5 SHA-256 checks, 7 threshold checks, REEF raw hash check | Complete |
| **Task 1** | RED Grammar Pair & H2 Parser | Tests passed 100%, ruff 0 errors | Complete |
| **Task 2** | Reducer & Writer Wiring | `grammar_pair` threaded through reduction, storage writer gates G2, zero-obs check intact | Complete |
| **Task 3** | Consumer Validation Before Load | Fail-closed pair selection & projection checking verified | Complete |
| **Task 4** | Fresh G2 Audit Generation | G2 root generated: 35 trusted parents, 44 symbols with events, audit passed | Complete |
| **Task 5** | Scope Gate & Independent Audit | Scope gate `PASS`, regression suite 76 passed (100%) | Complete |

---

## 4. Fresh Verification Command Evidence

### 1. Test Suite & Linter
```bash
PYTHONPATH=src:. .venv/bin/pytest \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_audit.py -q
```
**Output**: `76 passed in 0.29s` (Exit Code: 0)

```bash
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py \
  src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py \
  scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py
```
**Output**: `All checks passed!` (Exit Code: 0)

### 2. Frozen G1 Read-Only Replay
```bash
python - data/external_signal_shadow/stage1_6a/sealed_export_source_audits/sealed_export_audit_e9ec315753ea_20260823T095847Z $REF_EXPORT
```
**Output**: `{'g1_replay': 'PASS', 'source_audit_passed': False}` (Exit Code: 0)

### 3. Fresh G2 Audit Metrics
- **Root**: `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/h2_g2_remediated_20260824T061701Z`
- **Candidate Denominator (`candidate_total_denominator`)**: `35`
- **Trusted Parents Count (`trusted_parents_count`)**: `35`
- **Classified Parents Count (`classified_parents_count`)**: `35`
- **Symbols Mapped Count (`symbols_mapped_count`)**: `35`
- **Historical Events Found (`historical_events_found`)**: `30`
- **Event Days (`event_days`)**: `30`
- **Symbols with Events (`symbols_with_events`)**: `44`
- **Source Integrity Pass Rate (`source_integrity_pass_rate`)**: `1.0` (35/35)
- **Symbol Mapping Pass Rate (`symbol_mapping_pass_rate`)**: `1.0` (35/35)
- **Event Type Classification Pass Rate (`event_type_classification_pass_rate`)**: `1.0` (35/35)
- **Forbidden Payload Count (`forbidden_payload_count`)**: `0`
- **Source Schema Integrity Passed**: `True`
- **Sample Sufficiency Passed**: `True`
- **Source Audit Evidence Candidate Passed**: `True`
- **Completion Manifest `source_audit_passed`**: `True`
- **Authority Flags**: All 12 flags strictly `False`

### 4. Independent G2 Completed Consumer
```bash
python - data/external_signal_shadow/stage1_6a/sealed_export_source_audits/h2_g2_remediated_20260824T061701Z $REF_EXPORT
```
**Output**: `{'g2_replay': 'PASS', 'source_audit_passed': True, 'candidate_total_denominator': 35}` (Exit Code: 0)

### 5. Final Scope Gate
```bash
git diff --check
python - $BASE_SHA /tmp/stage1_6a_h2_g2_provenance.json
```
**Output**: `{'scope_gate': 'PASS', 'implementation_changed_paths': ['docs/reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md', 'scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py', 'src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py', 'src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py', 'tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py', 'tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py']}`

---

## 5. Residual Risks & Next Actions

1. **Authority Boundary**: 本审计结果 `source_audit_passed = True` 仅代表 Stage 1.6A 历史退市源数据审计通过。`RISK_LIVE_TRADING_ENABLED` 依然严格保持 `False`。
2. **不允许自动上线/交易/回测**: 本阶段不代表允许 Live Trading、Paper Trading 或 Directional Replay。
3. **本次无需重跑 Stage 1.6B 历史回填**: H2 修补只改变 Stage 1.6A 对既有 sealed export 的 body grammar/reducer；返修后的 G2 root 已基于同一冻结 export 重新生成并由独立 consumer 验证。提交后仅需执行本报告第 4.4 节的只读 G2 completed-consumer 复核。
4. **如需扩大样本**: 这是新的 Stage 1.6B 历史采集 run，必须使用新的 run ID/root，独立封签后再交给 Stage 1.6A 审计；不得覆盖、合并或改写本报告引用的冻结 export。
