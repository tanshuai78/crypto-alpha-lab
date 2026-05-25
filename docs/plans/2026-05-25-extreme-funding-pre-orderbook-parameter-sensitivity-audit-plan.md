# Extreme Funding Pre-Orderbook Parameter Sensitivity Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在进入 `orderbook-aware replay` 前，对 Extreme Funding 的关键门槛做参数敏感性审计，回答“主阻塞在哪、放宽到什么程度才有候选、放宽后是否仍具备研究价值”。

**Architecture:** 不改 live/watchlist，不改 execution。新增 research-only 审计层：读取已构建的历史 basis-aware rows，按参数网格运行 Phase 1B candidate + Phase 1C shadow，输出可比较的结构化 summary 与决策 review。

**Tech Stack:** Python 3.11, pytest, dataclasses, JSON/JSONL, existing `candidate_builder` + `shadow_simulator`, reports under `reports/extreme_funding`。

---

## Task 1: Baseline Freeze（锁定当前基线）

**Files:**
- Read: `reports/extreme_funding/2026-05-25_basis_aware_candidate_*_summary.json`
- Read: `reports/extreme_funding/2026-05-25_basis_aware_shadow_*_summary.json`
- Read: `docs/reviews/2026-05-25-extreme-funding-historical-basis-aware-replay-review.md`
- Test: `tests/scripts/test_replay_extreme_funding_basis_aware_candidates.py`
- Test: `tests/scripts/test_simulate_extreme_funding_basis_aware_shadow.py`

**Step 1: 运行当前基线测试**

Run:
```bash
PYTHONPATH=src uv run pytest \
  tests/scripts/test_replay_extreme_funding_basis_aware_candidates.py \
  tests/scripts/test_simulate_extreme_funding_basis_aware_shadow.py \
  -q
```
Expected: PASS

**Step 2: 记录 baseline 快照**

Run:
```bash
python - <<'PY'
import glob,json
for p in sorted(glob.glob('reports/extreme_funding/2026-05-25_*summary.json')):
    d=json.load(open(p))
    print(p, d.get('candidate_count', d.get('shadow_trade_count')), d.get('status'))
PY
```
Expected: 打印基线值（后续对照必须引用）。

---

## Task 2: Add Audit Config Contract（参数网格契约）

**Files:**
- Modify: `configs/base.py`
- Test: `tests/test_extreme_funding_config.py`

**Step 1: 先写失败测试**

在 `tests/test_extreme_funding_config.py` 新增：
```python
def test_extreme_funding_sensitivity_audit_config_defined():
    assert base.EXTREME_FUNDING_SENSITIVITY_ANNUALIZED_GRID_PCT == (80.0, 100.0, 120.0)
    assert base.EXTREME_FUNDING_SENSITIVITY_MIN_INCOME_GRID_BPS == (30.0, 50.0, 70.0)
    assert base.EXTREME_FUNDING_SENSITIVITY_MAX_SLIPPAGE_GRID_BPS == (8.0, 10.0, 12.0)
    assert base.EXTREME_FUNDING_SENSITIVITY_EXPECTED_INTERVAL_GRID == (1, 2)
    assert base.EXTREME_FUNDING_SENSITIVITY_BASIS_ABSORPTION_GRID == (0.30, 0.50, 0.70)
```

**Step 2: 跑测试确认失败**

Run:
```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py::test_extreme_funding_sensitivity_audit_config_defined -q
```
Expected: FAIL

**Step 3: 增加配置常量**

在 `configs/base.py` 增加 5 组网格常量，并注释：
- `EXTREME_FUNDING_SENSITIVITY_ANNUALIZED_GRID_PCT`
- `EXTREME_FUNDING_SENSITIVITY_MIN_INCOME_GRID_BPS`
- `EXTREME_FUNDING_SENSITIVITY_MAX_SLIPPAGE_GRID_BPS`
- `EXTREME_FUNDING_SENSITIVITY_EXPECTED_INTERVAL_GRID`
- `EXTREME_FUNDING_SENSITIVITY_BASIS_ABSORPTION_GRID`

说明：
- `min_net_edge_bps` 不纳入网格，固定为策略底线 30 bps，仅观察分布不放宽。

**Step 4: 回归测试**

Run:
```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py -q
```
Expected: PASS

**Step 5: Commit**

```bash
git add configs/base.py tests/test_extreme_funding_config.py
git commit -m "test+feat: add extreme funding sensitivity parameter grid config"
```

---

## Task 3: Add Threshold Override Contract（去全局打桩）

**Files:**
- Modify: `src/strategies/extreme_funding/candidate_builder.py`
- Test: `tests/strategies/test_extreme_funding_candidate_builder.py`

**Step 1: 写失败测试（显式阈值注入）**

新增测试覆盖：
```python
def test_candidate_builder_accepts_explicit_threshold_overrides(): ...
def test_candidate_builder_default_behavior_unchanged_without_overrides(): ...
def test_candidate_builder_threshold_override_does_not_mutate_global_defaults(): ...
```

**Step 2: 跑测试确认失败**

Run:
```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_candidate_builder.py -q
```
Expected: FAIL

**Step 3: 最小实现**

在 `candidate_builder.py` 增加：
- `ExtremeFundingCandidateThresholds` dataclass（research-only override）
- `build_extreme_funding_candidate(row, thresholds=None)`

规则：
- `thresholds is None` 时，行为与当前版本一致（完全读取 `configs/base.py` 默认值）。
- `thresholds` 非空时，仅本次调用使用 override。
- 禁止 monkeypatch/module-level 打桩。

**Step 4: 回归测试**

Run:
```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_candidate_builder.py -q
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/strategies/extreme_funding/candidate_builder.py tests/strategies/test_extreme_funding_candidate_builder.py
git commit -m "test+refactor: add explicit candidate threshold overrides for research audit"
```

---

## Task 4: Add Sensitivity Core（研究核心）

**Files:**
- Create: `src/research/extreme_funding_parameter_sensitivity.py`
- Test: `tests/research/test_extreme_funding_parameter_sensitivity.py`

**Step 1: 写失败测试**

新增测试覆盖：
```python
def test_build_parameter_grid_cartesian_product_includes_basis_absorption(): ...
def test_candidate_sensitivity_outputs_assumption_level(): ...
def test_shadow_sensitivity_only_uses_accepted_candidates(): ...
def test_shadow_trade_count_never_exceeds_candidate_count(): ...
def test_sensitivity_summary_marks_depth_proxy_not_depth_aware(): ...
```

**Step 2: 跑测试确认失败**

Run:
```bash
PYTHONPATH=src uv run pytest tests/research/test_extreme_funding_parameter_sensitivity.py -q
```
Expected: FAIL

**Step 3: 实现核心模块**

实现：
- `SensitivityParamSet`：
  - `annualized_threshold_pct`
  - `min_expected_funding_income_bps`
  - `max_slippage_bps`
  - `expected_holding_intervals`
  - `basis_absorption_max_ratio`
  - `assumption_level`（`conservative_1_interval` / `optimistic_2_intervals`）
- `build_parameter_grid(...)`
- `run_candidate_sensitivity(rows, param_sets)`
- `run_shadow_sensitivity(rows, param_sets)`
- `build_sensitivity_report(...)`

硬规则：
- sensitivity 通过 `thresholds` 参数调用 candidate builder，不允许全局常量覆写。
- shadow 输入必须是“该参数组下 accepted candidates 对应 rows”。
- 输出必须包含：
  - `input_row_count`
  - `candidate_count`
  - `shadow_trade_count`
  - `candidate_rate`
  - `top_reject_reason`
  - `coverage_quality`
  - `depth_aware=false`

**Step 4: 回归测试**

Run:
```bash
PYTHONPATH=src uv run pytest tests/research/test_extreme_funding_parameter_sensitivity.py -q
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/research/extreme_funding_parameter_sensitivity.py tests/research/test_extreme_funding_parameter_sensitivity.py
git commit -m "test+feat: add extreme funding parameter sensitivity core with explicit thresholds"
```

---

## Task 5: Add Audit CLI（审计脚本）

**Files:**
- Create: `scripts/audit_extreme_funding_parameter_sensitivity.py`
- Test: `tests/scripts/test_audit_extreme_funding_parameter_sensitivity.py`

**Step 1: 写失败测试（CLI 契约）**

新增测试覆盖：
```python
def test_audit_cli_writes_candidate_and_shadow_json(tmp_path): ...
def test_audit_cli_handles_empty_input_with_status_flag(tmp_path): ...
def test_audit_cli_includes_decision_gate_fields(tmp_path): ...
```

**Step 2: 跑测试确认失败**

Run:
```bash
PYTHONPATH=src uv run pytest tests/scripts/test_audit_extreme_funding_parameter_sensitivity.py -q
```
Expected: FAIL

**Step 3: 实现 CLI**

输入：
- `--input`
- `--output-dir`
- `--tag`

输出：
- `reports/extreme_funding/<tag>_sensitivity_candidate_summary.json`
- `reports/extreme_funding/<tag>_sensitivity_shadow_summary.json`

并打印：
- candidate top reject reasons
- shadow top exit reasons
- each param set 的 `candidate_count` / `median_net_pnl_bps`

**Step 4: 回归测试**

Run:
```bash
PYTHONPATH=src uv run pytest tests/scripts/test_audit_extreme_funding_parameter_sensitivity.py -q
```
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/audit_extreme_funding_parameter_sensitivity.py tests/scripts/test_audit_extreme_funding_parameter_sensitivity.py
git commit -m "test+feat: add CLI for extreme funding parameter sensitivity audit"
```

---

## Task 6: Run DOGE/XRP Sensitivity Audit（真实样本审计）

**Files:**
- Generate: `reports/extreme_funding/2026-05-26_doge_sensitivity_candidate_summary.json`
- Generate: `reports/extreme_funding/2026-05-26_doge_sensitivity_shadow_summary.json`
- Generate: `reports/extreme_funding/2026-05-26_xrp_sensitivity_candidate_summary.json`
- Generate: `reports/extreme_funding/2026-05-26_xrp_sensitivity_shadow_summary.json`

**Step 1: DOGE**

```bash
PYTHONPATH=src uv run python scripts/audit_extreme_funding_parameter_sensitivity.py \
  --input reports/extreme_funding/2026-05-25_basis_rows_DOGEUSDT.jsonl \
  --output-dir reports/extreme_funding \
  --tag 2026-05-26_doge
```

**Step 2: XRP**

```bash
PYTHONPATH=src uv run python scripts/audit_extreme_funding_parameter_sensitivity.py \
  --input reports/extreme_funding/2026-05-25_basis_rows_XRPUSDT.jsonl \
  --output-dir reports/extreme_funding \
  --tag 2026-05-26_xrp
```

**Step 3: sanity check**

```bash
python - <<'PY'
import json,glob
for p in sorted(glob.glob('reports/extreme_funding/2026-05-26_*_sensitivity_*_summary.json')):
    d=json.load(open(p))
    print(p, d.get('status'), d.get('coverage_quality'), d.get('depth_aware'))
PY
```

Expected:
- `status=ok`
- `coverage_quality=historical_basis_proxy_not_depth_aware`
- `depth_aware=False`

---

## Task 7: Write Review With Hard Decision Gate（硬门文档）

**Files:**
- Create: `docs/reviews/2026-05-26-extreme-funding-parameter-sensitivity-audit-review.md`
- Modify: `docs/roadmap_CN.md`（只追加 next-step 决策）

**Step 1: 写 review（必须粘真实 JSON）**

必须回答：
1. baseline 参数下 `candidate_count` 是否 > 0
2. 放宽 `annualized_threshold` 是否显著改善
3. 放宽 `basis_absorption_max_ratio` 是否显著改善
4. `interval=2` 相对 `interval=1` 的增益是否只是乐观假设
5. reject 主因是否从 `annualized_funding_below_trade_threshold` 转移到 `basis_absorbed`/`net_edge_below_min`

**Step 2: 使用硬决策门**

进入 `orderbook-aware replay` 的最低条件（必须全部满足）：
- 在 `assumption_level=conservative_1_interval` 下 `candidate_count > 0`
- `median_net_pnl_bps > 20`
- `win_rate > 55%`
- 结果不依赖极端放宽（如 `annualized=80 + slippage=12 + basis_absorption=0.70` 的单点组合）
- `depth_aware=false` 保留，结论仅允许“进入 orderbook-aware replay”，不允许“进入 live”

若仅在 `optimistic_2_intervals` 或极端放宽下才有候选：
- 结论必须是“不进入 orderbook-aware replay，回到策略定义层”。

**Step 3: 防模板残留检查**

```bash
rg -n "TODO|TBD|粘贴|占位|PLAN_NEEDS_VALUE|UNRESOLVED" docs/reviews/2026-05-26-extreme-funding-parameter-sensitivity-audit-review.md
```
Expected: 无输出

**Step 4: 全量验证**

```bash
PYTHONPATH=src uv run pytest \
  tests/test_extreme_funding_config.py \
  tests/strategies/test_extreme_funding_candidate_builder.py \
  tests/research/test_extreme_funding_parameter_sensitivity.py \
  tests/scripts/test_audit_extreme_funding_parameter_sensitivity.py \
  tests/strategies/test_extreme_funding_shadow_simulator.py \
  -q
```
Expected: PASS

**Step 5: Commit**

```bash
git add docs/reviews/2026-05-26-extreme-funding-parameter-sensitivity-audit-review.md \
        docs/roadmap_CN.md \
        reports/extreme_funding/2026-05-26_*_sensitivity_*_summary.json
git commit -m "docs+report: add pre-orderbook extreme funding parameter sensitivity audit"
```

---

## Done Definition

完成标准：
- 参数网格包含 5 维：annualized / min_income / max_slippage / expected_intervals / basis_absorption。
- sensitivity 实现不使用全局常量打桩，必须走 `thresholds` 显式注入。
- shadow 严格只对 accepted candidates 运行，且 `shadow_trade_count == candidate_count`。
- DOGE/XRP 均产出 candidate + shadow sensitivity summary。
- review 使用硬决策门给出“进/不进 orderbook-aware replay”结论。
- 所有输出保留 `depth_aware=false` 与 `coverage_quality` 边界。

## 风险控制说明

- 本轮是 research 审计，不是策略放行。
- 禁止导入 `src/execution/`。
- 禁止新增 live 开关。
- 若只有极端放宽参数才出现候选，默认判定为“策略定义仍不稳”。

## 执行节奏

- Batch A: Task 1-2
- Batch B: Task 3-5
- Batch C: Task 6-7

每个 Batch 完成后先 review 再进入下一批，避免证据链漂移。
