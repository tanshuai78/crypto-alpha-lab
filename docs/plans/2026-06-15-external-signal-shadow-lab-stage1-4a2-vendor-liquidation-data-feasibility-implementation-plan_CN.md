# External Signal Shadow Lab Stage 1.4A.2 Vendor Liquidation Data Feasibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现一个 vendor liquidation 数据可行性审计管线，用本地审计记录、真实 sample 文件和可选 trial export 判断是否存在适合 Stage 1.4B 的 `>=90d` liquidation history source。

**Architecture:** 第一版只做本地、只读、sample-first 审计：人工整理 vendor docs / pricing / license / sample 信息为 JSON，再由 `stage1_4a2_vendor.py` 做 schema validation、sample file audit merge、decision gate、vendor ranking。脚本只读取本地文件并输出 summary/review，不联网、不读 API key、不采购、不做 replay；`sample_file_available=true` 必须绑定真实本地 sample 文件并通过 `audit_vendor_sample_file()`。

**Tech Stack:** Python stdlib dataclasses/json/csv/gzip/zipfile/pathlib, pytest, ruff, existing `src/research/external_signal_shadow/` research modules, existing `scripts/external_signal_shadow/` script layout.

---

## 0. 边界与不变量

本计划执行范围：

```text
scope = stage1_4a2_vendor_liquidation_data_feasibility_audit_only
purchase_allowed = false
api_key_in_code_allowed = false
auto_vendor_http_allowed = false
stage1_4b_candidate_replay_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
```

本阶段允许的输入：

```text
1. 人工整理的 vendor audit JSON 文件；
2. vendor 公开 sample / trial export 的本地文件；
3. 官方 docs / pricing / sales reply 的人工证据 URL 和 notes。
```

本阶段禁止：

```text
1. 自动访问 vendor 付费 API；
2. 读取 .env / secrets / API key；
3. 自动采购或注册付费计划；
4. 把 docs-only 判断成 feasible；
5. 生成收益回放或交易信号。
```

---

## Task 1: 配置与 `.gitignore` runtime data 保护

**Files:**

- Modify: `configs/base.py`
- Modify: `.gitignore`
- Test: `tests/research/external_signal_shadow/test_stage1_4a2_vendor_config.py`

**Step 1: 写配置测试**

Create `tests/research/external_signal_shadow/test_stage1_4a2_vendor_config.py`:

```python
from configs import base


def test_stage1_4a2_vendor_config_constants_exist() -> None:
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_VENDOR_ORDER == (
        "tardis_dev",
        "coinglass",
        "laevitas",
        "coinalyze",
        "coin_metrics_pro",
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MIN_HISTORY_DAYS == 90.0
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MIN_SYMBOLS_WITH_USABLE_DATA == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MAX_TIMESTAMP_RESOLUTION_MS == 60_000
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MIN_VENDOR_DATA_LAG_MS == 60_000
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_LOW_COST_MAX_USD_PER_MONTH == 50.0
    assert base.EXTERNAL_SIGNAL_STAGE1_4A2_MEDIUM_COST_MAX_USD_PER_MONTH == 200.0


def test_stage1_4a2_runtime_paths_are_gitignored() -> None:
    # Use subprocess rather than importing git internals.
    import subprocess

    sample_path = "data/external_signal_shadow/vendor_liquidation_samples/tardis_dev/sample.jsonl"
    result = subprocess.run(
        ["git", "check-ignore", sample_path],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    template_path = "docs/context/stage1_4a2_vendor_audit_template.json"
    assert template_path
```

**Step 2: 跑测试确认失败**

```bash
PYTHONPATH=. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_config.py -q
```

Expected: FAIL because constants do not exist and/or runtime path is not ignored.

**Step 3: 修改 `configs/base.py`**

Add a section near other External Signal constants. 每个常量必须有注释，不能裸写 magic number。

```python
# ─── External Signal Shadow Lab Stage 1.4A.2: Vendor Liquidation Audit ───

EXTERNAL_SIGNAL_STAGE1_4A2_VENDOR_ORDER = (
    "tardis_dev",
    "coinglass",
    "laevitas",
    "coinalyze",
    "coin_metrics_pro",
)
# Fixed first-pass vendor audit order. Do not expand the vendor list before this
# five-vendor audit is completed; otherwise the feasibility audit becomes open-ended.

EXTERNAL_SIGNAL_STAGE1_4A2_MIN_HISTORY_DAYS = 90.0
# Minimum verified liquidation sample history before a vendor can be considered feasible.
# Safe range: 90-180 days. Below 90d is insufficient for Stage 1.4B replay eligibility.

EXTERNAL_SIGNAL_STAGE1_4A2_MIN_SYMBOLS_WITH_USABLE_DATA = 3
# Minimum number of target symbols with usable sample rows.
# Safe range: 3-5. Fewer than 3 symbols makes source feasibility too concentrated.

EXTERNAL_SIGNAL_STAGE1_4A2_MAX_TIMESTAMP_RESOLUTION_MS = 60_000
# Coarsest timestamp resolution allowed for intraday Stage 1.4B replay candidates.
# 60s is acceptable for 15m/1h liquidation clusters; daily-only data is not.

EXTERNAL_SIGNAL_STAGE1_4A2_MIN_VENDOR_DATA_LAG_MS = 60_000
# Conservative minimum data availability lag when vendor samples do not provide true arrival time.
# Prevents replay anchoring on unavailable bucket-start timestamps.

EXTERNAL_SIGNAL_STAGE1_4A2_LOW_COST_MAX_USD_PER_MONTH = 50.0
# Maximum monthly cost considered low for personal research sample access.
# Above this, user cost approval is required before feasible can be claimed.

EXTERNAL_SIGNAL_STAGE1_4A2_MEDIUM_COST_MAX_USD_PER_MONTH = 200.0
# Maximum monthly cost considered medium. Costs above this or enterprise quote-only plans
# are degraded by default unless the user explicitly approves.
```

**Step 4: 修改 `.gitignore`**

Ensure this line exists:

```gitignore
data/external_signal_shadow/vendor_liquidation_samples/
```

Do not ignore summary/review artifacts by default.

**Step 4.5: 预留 audit template 输出位置**

This plan will later create:

```text
docs/context/stage1_4a2_vendor_audit_template.json
```

This template is committed, unlike runtime sample files.

**Step 5: 跑测试确认通过**

```bash
PYTHONPATH=. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_config.py -q
```

Expected: PASS.

---

## Task 2: Vendor audit model 与 schema validation

**Files:**

- Create: `src/research/external_signal_shadow/stage1_4a2_vendor.py`
- Create: `tests/research/external_signal_shadow/stage1_4a2_vendor_fixtures.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a2_vendor_models.py`

**Step 1: 写失败测试**

First create `tests/research/external_signal_shadow/stage1_4a2_vendor_fixtures.py`:

```python
def base_vendor_audit_payload() -> dict:
    return {
        "vendor": "tardis_dev",
        "priority": "P1",
        "source_surface": "trial_export",
        "evidence_level": "trial_export",
        "evidence_urls": ["https://docs.tardis.dev/"],
        "evidence_retrieved_at": "2026-06-15",
        "audit_time_ms": 1781452800000,
        "sample_access_type": "free_trial",
        "payment_required_before_sample": False,
        "sales_contact_required": False,
        "api_key_required_for_sample": False,
        "sample_file_available": True,
        "sample_file_path": "data/external_signal_shadow/vendor_liquidation_samples/tardis_dev/sample.jsonl",
        "sample_file_audited": True,
        "sample_audit_row_count": 100,
        "sample_audit_history_days": 120.0,
        "explicit_user_approval_for_trial": False,
        "explicit_user_approval_for_paid_sample": False,
        "explicit_user_cost_approval": False,
        "license_status": "clear",
        "license_allows_local_research": True,
        "license_allows_backtesting": True,
        "license_allows_local_storage": True,
        "license_allows_derived_metrics": True,
        "redistribution_forbidden": True,
        "history_days_claimed": 180.0,
        "history_days_verified_from_sample": 120.0,
        "symbols_claimed": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "symbols_verified": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "exchange_scope": "binance_usdm",
        "binance_usdm_exact": True,
        "includes_coin_margined": False,
        "includes_usd_margined": True,
        "multi_exchange_aggregate": False,
        "exchange_filter_available": True,
        "timestamp_resolution_ms": 60_000,
        "side_available": True,
        "side_semantics": "long_short",
        "long_liquidation_mapping": "long_liquidation_usd",
        "short_liquidation_mapping": "short_liquidation_usd",
        "side_mapping_confidence": "verified",
        "notional_usd_available": True,
        "price_available": False,
        "quantity_available": False,
        "exchange_field_available": True,
        "symbol_field_available": True,
        "timestamp_field_available": True,
        "download_or_export_format": "jsonl",
        "source_granularity": "1m",
        "replay_anchor_policy": "bucket_end_plus_lag",
        "available_at_policy_defined": True,
        "field_mapping_status": "compatible",
        "stage1_4a1_alignment_status": "compatible",
        "cost_tier": "low",
        "personal_investor_feasible_cost": True,
        "estimated_cost_usd_per_month": 49.0,
        "manual_notes": [],
    }
```

Create `tests/research/external_signal_shadow/test_stage1_4a2_vendor_models.py`:

```python
import pytest

from tests.research.external_signal_shadow.stage1_4a2_vendor_fixtures import base_vendor_audit_payload
from research.external_signal_shadow.stage1_4a2_vendor import (
    VendorLiquidationAudit,
    load_vendor_audits_json,
)


def test_vendor_audit_model_accepts_complete_payload() -> None:
    audit = VendorLiquidationAudit.from_dict(base_vendor_audit_payload())
    assert audit.vendor == "tardis_dev"
    assert audit.evidence_level == "trial_export"


@pytest.mark.parametrize("bad_level", ["marketing", "docs", ""])
def test_vendor_audit_model_rejects_unknown_evidence_level(bad_level: str) -> None:
    payload = base_vendor_audit_payload()
    payload["evidence_level"] = bad_level
    with pytest.raises(ValueError, match="evidence_level"):
        VendorLiquidationAudit.from_dict(payload)


def test_vendor_audit_model_requires_license_split_fields() -> None:
    payload = base_vendor_audit_payload()
    del payload["license_allows_backtesting"]
    with pytest.raises(ValueError, match="license_allows_backtesting"):
        VendorLiquidationAudit.from_dict(payload)


def test_vendor_audit_model_rejects_unknown_source_surface() -> None:
    payload = base_vendor_audit_payload()
    payload["source_surface"] = "unknown_surface"
    with pytest.raises(ValueError, match="source_surface"):
        VendorLiquidationAudit.from_dict(payload)


def test_vendor_audit_model_requires_evidence_urls_and_date() -> None:
    payload = base_vendor_audit_payload()
    payload["evidence_urls"] = []
    with pytest.raises(ValueError, match="evidence_urls"):
        VendorLiquidationAudit.from_dict(payload)


def test_load_vendor_audits_json_supports_list_root(tmp_path) -> None:
    import json

    path = tmp_path / "audits.json"
    path.write_text(json.dumps([base_vendor_audit_payload()]), encoding="utf-8")
    audits = load_vendor_audits_json(path)
    assert len(audits) == 1
```

**Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_models.py -q
```

Expected: FAIL because module does not exist.

**Step 3: 实现 model**

Create `src/research/external_signal_shadow/stage1_4a2_vendor.py` with:

- `VendorLiquidationAudit` frozen dataclass.
- `from_dict()` strict validation.
- Enum-like allowed sets, but keep implementation simple with tuples/sets.
- `load_vendor_audits_json(path: str | Path) -> list[VendorLiquidationAudit]`.
- No network, no env reads.

Required validation:

```text
vendor must be one of EXTERNAL_SIGNAL_STAGE1_4A2_VENDOR_ORDER
source_surface in {marketing_page, official_api_docs, pricing_page, public_sample, trial_export, sales_reply, manual_vendor_reply}
evidence_level in {marketing_page, official_api_docs, sample_schema, sample_rows, trial_export}
sample_access_type in {public_sample, free_trial, sales_provided_sample, paid_plan_required, unknown}
license_status in {clear, unknown, restricted, disallowed}
exchange_scope in {binance_usdm, multi_exchange, aggregated_unknown}
side_mapping_confidence in {verified, inferred_from_official_docs, unknown}
source_granularity in {tick, 1m, 5m, 15m, 1h, daily, unknown}
replay_anchor_policy in {event_time_plus_lag, bucket_end_plus_lag, not_intraday_usable, unknown}
cost_tier in {free, low, medium, high, enterprise_unknown}
evidence_urls must be non-empty
evidence_retrieved_at must be non-empty
manual_notes must be list
symbols_claimed / symbols_verified must be list[str]
if sample_file_available=true:
  sample_file_path must be a non-empty string
  explicit sample audit metadata fields must exist
```

The payload factory must live in `tests/research/external_signal_shadow/stage1_4a2_vendor_fixtures.py`, not inside another test module.

**Step 4: 跑测试确认通过**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_models.py -q
```

Expected: PASS.

---

## Task 3: Vendor decision engine

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_4a2_vendor.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a2_vendor_decision.py`

**Step 1: 写 decision 测试**

Create `tests/research/external_signal_shadow/test_stage1_4a2_vendor_decision.py`:

```python
from tests.research.external_signal_shadow.stage1_4a2_vendor_fixtures import base_vendor_audit_payload
from research.external_signal_shadow.stage1_4a2_vendor import (
    VendorLiquidationAudit,
    decide_vendor_audit,
)


def _audit(**updates):
    payload = base_vendor_audit_payload()
    payload.update(updates)
    return VendorLiquidationAudit.from_dict(payload)


def test_docs_only_can_only_be_degraded_even_when_fields_look_good() -> None:
    decision = decide_vendor_audit(
        _audit(evidence_level="official_api_docs", sample_file_available=False)
    )
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "sample_not_available"
    assert decision.next_action == "request_sample_or_trial"


def test_no_sample_means_no_feasible() -> None:
    decision = decide_vendor_audit(_audit(sample_file_available=False))
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "sample_not_available"


def test_license_unknown_blocks_feasible() -> None:
    decision = decide_vendor_audit(_audit(license_status="unknown"))
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "license_unclear_or_restricted"


def test_missing_side_mapping_confidence_blocks_feasible() -> None:
    decision = decide_vendor_audit(_audit(side_mapping_confidence="unknown"))
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "side_mapping_uncertain"


def test_medium_cost_requires_user_decision() -> None:
    decision = decide_vendor_audit(
        _audit(
            cost_tier="medium",
            personal_investor_feasible_cost=False,
            estimated_cost_usd_per_month=120.0,
            explicit_user_cost_approval=False,
        )
    )
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "user_cost_decision_required"


def test_paid_plan_required_needs_explicit_user_approval() -> None:
    decision = decide_vendor_audit(
        _audit(
            sample_access_type="paid_plan_required",
            payment_required_before_sample=True,
            explicit_user_approval_for_paid_sample=False,
        )
    )
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "user_cost_decision_required"


def test_valid_sample_can_be_feasible() -> None:
    decision = decide_vendor_audit(_audit())
    assert decision.decision == "vendor_liquidation_source_feasible"
    assert decision.primary_blocker is None
```

**Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_decision.py -q
```

Expected: FAIL because `decide_vendor_audit` does not exist.

**Step 3: 实现 decision engine**

In `stage1_4a2_vendor.py` add:

```python
@dataclass(frozen=True)
class VendorAuditDecision:
    vendor: str
    decision: str
    primary_blocker: str | None
    next_action: str
    feasible_for_stage1_4a3_parser: bool
    partial_diagnostic_allowed: bool
```

Decision order must be deterministic:

```text
1. evidence/sample gate
2. license gate
3. history_days gate
4. symbol count gate
5. field gate: side/notional/symbol/timestamp
6. side mapping confidence gate
7. timestamp/granularity/replay anchor gate
8. exchange scope / alignment gate
9. cost gate
10. feasible
```

Important rules:

```text
marketing_page / official_api_docs / sample_schema cannot feasible.
sample_file_available=false cannot feasible.
sample_file_available=true but sample_file_path missing cannot feasible.
sample_file_available=true but sample_file_audited=false cannot feasible.
history_days_verified_from_sample < 90 cannot feasible.
source_granularity=daily cannot intraday feasible.
multi_exchange aggregate can be degraded-compatible partial diagnostic, not exact Binance USD-M claim.
cost_tier in {medium, high, enterprise_unknown} requires explicit_user_cost_approval=true.
sample_access_type=paid_plan_required requires explicit_user_approval_for_paid_sample=true.
```

Add these fields to `VendorLiquidationAudit` and validate them:

```text
sample_file_path
sample_file_audited
sample_audit_row_count
sample_audit_history_days
explicit_user_approval_for_trial
explicit_user_approval_for_paid_sample
explicit_user_cost_approval
```

**Step 4: 跑测试确认通过**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_decision.py -q
```

Expected: PASS.

---

## Task 4: Summary builder 与 vendor ranking

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_4a2_vendor.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a2_vendor_summary.py`

**Step 1: 写 summary 测试**

Create `tests/research/external_signal_shadow/test_stage1_4a2_vendor_summary.py`:

```python
from tests.research.external_signal_shadow.stage1_4a2_vendor_fixtures import base_vendor_audit_payload
from research.external_signal_shadow.stage1_4a2_vendor import (
    VendorLiquidationAudit,
    build_vendor_feasibility_summary,
)


def _audit(vendor: str, **updates):
    payload = base_vendor_audit_payload()
    payload["vendor"] = vendor
    payload.update(updates)
    return VendorLiquidationAudit.from_dict(payload)


def test_summary_outputs_recommended_vendor_order_and_safety_flags() -> None:
    summary = build_vendor_feasibility_summary([
        _audit("tardis_dev"),
        _audit("coinglass", evidence_level="official_api_docs", sample_file_available=False),
    ])
    assert summary["recommended_vendor_order"][:2] == ["tardis_dev", "coinglass"]
    assert summary["best_vendor"] == "tardis_dev"
    assert summary["purchase_allowed"] is False
    assert summary["paper_trading_allowed"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["alpha_interpretation_allowed"] is False
    assert summary["stage1_4b_candidate_replay_allowed"] is False


def test_summary_degraded_when_no_vendor_feasible() -> None:
    summary = build_vendor_feasibility_summary([
        _audit("coinglass", evidence_level="official_api_docs", sample_file_available=False),
    ])
    assert summary["decision"] == "vendor_liquidation_source_degraded"
    assert summary["feasible_vendor_count"] == 0
    assert summary["primary_blocker"] == "no_feasible_vendor_sample"


def test_summary_next_action_is_precise_for_paid_only_promising_vendor() -> None:
    summary = build_vendor_feasibility_summary([
        _audit(
            "tardis_dev",
            sample_access_type="paid_plan_required",
            payment_required_before_sample=True,
            explicit_user_approval_for_paid_sample=False,
            cost_tier="medium",
            personal_investor_feasible_cost=False,
        ),
    ])
    assert summary["decision"] == "vendor_liquidation_source_degraded"
    assert summary["next_action"] == "user_cost_decision_required"
```

**Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_summary.py -q
```

Expected: FAIL because summary builder does not exist.

**Step 3: 实现 summary builder**

Add `build_vendor_feasibility_summary(audits: list[VendorLiquidationAudit]) -> dict`.

Required output fields:

```text
decision
primary_blocker
candidate_vendor_count
feasible_vendor_count
recommended_vendor_order
best_vendor
lowest_cost_usable_vendor
highest_data_quality_vendor
purchase_allowed=false
paper_trading_allowed=false
live_trading_allowed=false
alpha_interpretation_allowed=false
stage1_4b_candidate_replay_allowed=false
vendor_audits
vendor_decisions
next_action
```

Ranking policy:

```text
1. Keep design order as default recommendation order.
2. best_vendor = first feasible vendor in design order.
3. lowest_cost_usable_vendor = feasible vendor with cost_tier in {free, low}; tie by design order.
4. highest_data_quality_vendor = feasible vendor with evidence_level in {trial_export, sample_rows}, highest history_days, exact binance_usdm preferred.
```

If no feasible vendor:

```text
decision = vendor_liquidation_source_degraded
primary_blocker = no_feasible_vendor_sample
next_action = request_sample_or_trial_from_top_ranked_vendor_or_continue_live_collection
```

If all vendors unavailable/unparseable:

```text
decision = vendor_liquidation_source_unavailable
primary_blocker = no_vendor_audits_available
```

**Step 4: 跑测试确认通过**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_summary.py -q
```

Expected: PASS.

---

## Task 5: Optional local sample row schema audit helper

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_4a2_vendor.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a2_vendor_sample_audit.py`

**Purpose:** 只做字段和时间覆盖审计，不做收益、不做回放。Sample parser 不需要覆盖所有 vendor 私有格式；第一版支持 `JSONL / JSON / CSV` 及其 `.gz` 压缩版本，必要时支持 `.zip` 中单文件样本。

**Step 1: 写 sample audit 测试**

Create `tests/research/external_signal_shadow/test_stage1_4a2_vendor_sample_audit.py`:

```python
from research.external_signal_shadow.stage1_4a2_vendor import audit_vendor_sample_file


def test_audit_vendor_sample_jsonl_detects_required_fields(tmp_path) -> None:
    path = tmp_path / "sample.jsonl"
    path.write_text(
        '\n'.join([
            '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"long_liquidation_usd":1000,"short_liquidation_usd":0}',
            '{"symbol":"ETHUSDT","exchange":"binance_usdm","timestamp":1704153600000,"long_liquidation_usd":0,"short_liquidation_usd":2000}',
        ]),
        encoding="utf-8",
    )
    result = audit_vendor_sample_file(path)
    assert result["row_count"] == 2
    assert result["symbol_field_available"] is True
    assert result["timestamp_field_available"] is True
    assert result["notional_usd_available"] is True
    assert result["side_available"] is True
    assert result["symbols_verified"] == ["BTCUSDT", "ETHUSDT"]


def test_audit_vendor_sample_csv_detects_missing_side(tmp_path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text(
        "symbol,exchange,timestamp,notional_usd\nBTCUSDT,binance_usdm,1704067200000,1000\n",
        encoding="utf-8",
    )
    result = audit_vendor_sample_file(path)
    assert result["row_count"] == 1
    assert result["side_available"] is False


def test_audit_vendor_sample_file_computes_history_days(tmp_path) -> None:
    path = tmp_path / "sample.jsonl"
    path.write_text(
        '\n'.join([
            '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"long_liquidation_usd":1000,"short_liquidation_usd":0}',
            '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1712016000000,"long_liquidation_usd":500,"short_liquidation_usd":0}',
        ]),
        encoding="utf-8",
    )
    result = audit_vendor_sample_file(path)
    assert result["history_days"] >= 90.0


def test_audit_vendor_sample_file_rejects_daily_only_for_intraday(tmp_path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text(
        "symbol,exchange,timestamp,long_liquidation_usd,short_liquidation_usd\n"
        "BTCUSDT,binance_usdm,1704067200000,1000,0\n"
        "BTCUSDT,binance_usdm,1704153600000,0,2000\n",
        encoding="utf-8",
    )
    result = audit_vendor_sample_file(path)
    assert result["timestamp_resolution_ms"] >= 86_400_000
    assert result["intraday_usable"] is False


def test_audit_vendor_sample_file_supports_jsonl_gz(tmp_path) -> None:
    import gzip

    path = tmp_path / "sample.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(
            '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"long_liquidation_usd":1000,"short_liquidation_usd":0}\n'
        )
    result = audit_vendor_sample_file(path)
    assert result["row_count"] == 1
```

**Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_sample_audit.py -q
```

Expected: FAIL because helper does not exist.

**Step 3: 实现 helper**

Implement `audit_vendor_sample_file(path)`:

- Support `.jsonl`, `.json`, `.csv`, `.jsonl.gz`, `.json.gz`, `.csv.gz`, and optionally `.zip` with one inner data file.
- Read at most first 10_000 rows to avoid accidentally loading huge vendor files.
- Never write sample content to summary.
- Output only counts, field names, inferred symbols, timestamp min/max, history days.
- Do not infer side semantics as verified; only detect field presence.
- Compute `history_days`, `timestamp_resolution_ms`, and `intraday_usable`.
- Reject daily-only sample as intraday-feasible even if fields are complete.

Recognized side/notional patterns:

```text
side fields: side, liquidation_side, long_short, direction
long/short amount fields: long_liquidation_usd, short_liquidation_usd, longVolUsd, shortVolUsd
notional fields: notional_usd, liquidation_usd, amount_usd
price/quantity fields: price + quantity, price + qty
```

Also support audit-time checks:

```text
sample_file_path must exist
sample_file_path must be under data/external_signal_shadow/vendor_liquidation_samples/
sample_audit_row_count > 0
sample_audit_history_days derived from actual file, not manual JSON
```

**Step 4: 跑测试确认通过**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a2_vendor_sample_audit.py -q
```

Expected: PASS.

---

## Task 6: CLI summary generator

**Files:**

- Create: `scripts/external_signal_shadow/run_stage1_4a2_vendor_liquidation_data_feasibility.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_4a2_vendor_liquidation_data_feasibility.py`
- Fixture: `tests/fixtures/external_signal_shadow/stage1_4a2_vendor_audits_docs_only.json`
- Fixture: `tests/fixtures/external_signal_shadow/stage1_4a2_vendor_audits_with_sample.json`

**Step 1: 创建 fixture**

`tests/fixtures/external_signal_shadow/stage1_4a2_vendor_audits_docs_only.json` should include one docs-only CoinGlass audit where `sample_file_available=false`.

`tests/fixtures/external_signal_shadow/stage1_4a2_vendor_audits_with_sample.json` should include one feasible Tardis-like audit where `evidence_level=trial_export`, `sample_file_available=true`, `history_days_verified_from_sample=120`, and license fields are clear.

**Step 2: 写 CLI 测试**

Create `tests/scripts/external_signal_shadow/test_run_stage1_4a2_vendor_liquidation_data_feasibility.py`:

```python
import json

from tests.research.external_signal_shadow.stage1_4a2_vendor_fixtures import base_vendor_audit_payload
from scripts.external_signal_shadow.run_stage1_4a2_vendor_liquidation_data_feasibility import main


def test_cli_writes_degraded_summary_for_docs_only_fixture(tmp_path) -> None:
    output = tmp_path / "summary.json"
    rc = main([
        "--vendor-audits",
        "tests/fixtures/external_signal_shadow/stage1_4a2_vendor_audits_docs_only.json",
        "--output-summary",
        str(output),
    ])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "vendor_liquidation_source_degraded"
    assert summary["stage1_4b_candidate_replay_allowed"] is False


def test_cli_does_not_read_vendor_api_key_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TARDIS_API_KEY", "LEAK_CHECK")
    output = tmp_path / "summary.json"
    rc = main([
        "--vendor-audits",
        "tests/fixtures/external_signal_shadow/stage1_4a2_vendor_audits_with_sample.json",
        "--output-summary",
        str(output),
    ])
    assert rc == 0
    text = output.read_text(encoding="utf-8")
    assert "LEAK_CHECK" not in text
    summary = json.loads(text)
    assert summary["purchase_allowed"] is False


def test_feasible_requires_existing_sample_file_when_sample_file_available_true(tmp_path) -> None:
    payload = base_vendor_audit_payload()
    payload["sample_file_path"] = "data/external_signal_shadow/vendor_liquidation_samples/tardis_dev/missing.jsonl"
    payload["sample_file_audited"] = False
    audit_path = tmp_path / "audits.json"
    audit_path.write_text(json.dumps([payload]), encoding="utf-8")
    output = tmp_path / "summary.json"
    rc = main(["--vendor-audits", str(audit_path), "--output-summary", str(output)])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "vendor_liquidation_source_degraded"
    assert summary["primary_blocker"] == "sample_file_not_verified"


def test_sample_file_path_must_be_under_gitignored_vendor_sample_dir(tmp_path) -> None:
    bad_sample = tmp_path / "sample.jsonl"
    bad_sample.write_text(
        '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"long_liquidation_usd":1000,"short_liquidation_usd":0}\\n',
        encoding="utf-8",
    )
    payload = base_vendor_audit_payload()
    payload["sample_file_available"] = True
    payload["sample_file_path"] = str(bad_sample)
    payload["sample_file_audited"] = False
    audit_path = tmp_path / "audits.json"
    audit_path.write_text(json.dumps([payload]), encoding="utf-8")
    output = tmp_path / "summary.json"
    rc = main(["--vendor-audits", str(audit_path), "--output-summary", str(output)])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["primary_blocker"] == "sample_file_not_under_runtime_vendor_dir"


def test_sample_audit_conflict_blocks_feasible(tmp_path) -> None:
    runtime_dir = tmp_path / "data" / "external_signal_shadow" / "vendor_liquidation_samples" / "tardis_dev"
    runtime_dir.mkdir(parents=True)
    sample_path = runtime_dir / "sample.jsonl"
    sample_path.write_text(
        '{"symbol":"BTCUSDT","exchange":"binance_usdm","timestamp":1704067200000,"notional_usd":1000}\n',
        encoding="utf-8",
    )
    payload = base_vendor_audit_payload()
    payload["sample_file_path"] = str(sample_path)
    payload["side_available"] = True
    payload["sample_file_audited"] = False
    audit_path = tmp_path / "audits.json"
    audit_path.write_text(json.dumps([payload]), encoding="utf-8")
    output = tmp_path / "summary.json"
    rc = main([
        "--vendor-audits",
        str(audit_path),
        "--output-summary",
        str(output),
        "--sample-dir",
        str(tmp_path / "data" / "external_signal_shadow" / "vendor_liquidation_samples"),
    ])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["primary_blocker"] == "sample_audit_conflict"
```

**Step 3: 跑测试确认失败**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_4a2_vendor_liquidation_data_feasibility.py -q
```

Expected: FAIL because script does not exist.

**Step 4: 实现 CLI**

Script behavior:

```text
required args:
  --vendor-audits PATH
  --output-summary PATH

optional args:
  --sample-dir data/external_signal_shadow/vendor_liquidation_samples
```

Rules:

```text
- No network flags.
- No API key args.
- No env reads.
- If --vendor-audits missing or invalid, write failure summary and return non-zero.
- Output JSON with sort_keys=True and indent=2.
- If sample_file_available=true:
    sample_file_path must exist
    sample_file_path must be under data/external_signal_shadow/vendor_liquidation_samples/
    audit_vendor_sample_file() must run
    sample audit result must not conflict with manual audit JSON on symbols/timestamp/side/notional/history_days
```

Required CLI merge behavior:

```text
if sample_file_available=true and sample audit fails:
    decision = vendor_liquidation_source_degraded
    primary_blocker = sample_file_not_verified

if manual audit claims side/notional/timestamp fields but sample audit disproves them:
    decision = vendor_liquidation_source_degraded
    primary_blocker = sample_audit_conflict
```

Also create a committed template file:

```text
docs/context/stage1_4a2_vendor_audit_template.json
```

The CLI itself does not generate the template dynamically; implementation should add this static template file to help users build valid audit JSON.

Failure summary must include:

```json
{
  "decision": "vendor_liquidation_source_unavailable",
  "primary_blocker": "vendor_audit_input_missing_or_invalid",
  "purchase_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "alpha_interpretation_allowed": false,
  "stage1_4b_candidate_replay_allowed": false
}
```

**Step 5: 跑测试确认通过**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_4a2_vendor_liquidation_data_feasibility.py -q
```

Expected: PASS.

---

## Task 7: 中文 review generator

**Files:**

- Create: `scripts/external_signal_shadow/review_stage1_4a2_vendor_liquidation_data_feasibility.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_4a2_vendor_liquidation_data_feasibility.py`

**Step 1: 写 review 测试**

Create `tests/scripts/external_signal_shadow/test_review_stage1_4a2_vendor_liquidation_data_feasibility.py`:

```python
import json

from scripts.external_signal_shadow.review_stage1_4a2_vendor_liquidation_data_feasibility import main


def test_review_renders_vendor_table_and_recommendations(tmp_path) -> None:
    summary = {
        "decision": "vendor_liquidation_source_degraded",
        "primary_blocker": "no_feasible_vendor_sample",
        "recommended_vendor_order": ["tardis_dev", "coinglass"],
        "best_vendor": None,
        "lowest_cost_usable_vendor": None,
        "highest_data_quality_vendor": None,
        "purchase_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "stage1_4b_candidate_replay_allowed": False,
        "vendor_decisions": [
            {
                "vendor": "coinglass",
                "priority": "P2",
                "evidence_level": "official_api_docs",
                "sample_access_type": "unknown",
                "sample_file_available": False,
                "history_days_verified_from_sample": 0.0,
                "symbols_verified": [],
                "side_mapping_confidence": "unknown",
                "notional_usd_available": False,
                "timestamp_resolution_ms": None,
                "exchange_scope": "aggregated_unknown",
                "license_status": "unknown",
                "cost_tier": "enterprise_unknown",
                "decision": "vendor_liquidation_source_degraded",
                "primary_blocker": "sample_not_available",
                "next_action": "request_sample_or_trial",
            }
        ],
    }
    summary_path = tmp_path / "summary.json"
    review_path = tmp_path / "review.md"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    rc = main(["--summary", str(summary_path), "--output-review", str(review_path)])
    assert rc == 0
    text = review_path.read_text(encoding="utf-8")
    assert "Per-Vendor Audit Table" in text
    assert "sample_not_available" in text
    assert "recommended_vendor_order" in text
    assert "不允许推出" in text


def test_review_marks_docs_only_as_not_data_feasible(tmp_path) -> None:
    summary = {
        "decision": "vendor_liquidation_source_degraded",
        "primary_blocker": "sample_not_available",
        "recommended_vendor_order": ["coinglass"],
        "best_vendor": None,
        "lowest_cost_usable_vendor": None,
        "highest_data_quality_vendor": None,
        "purchase_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "stage1_4b_candidate_replay_allowed": False,
        "vendor_decisions": [
            {
                "vendor": "coinglass",
                "evidence_level": "official_api_docs",
                "decision": "vendor_liquidation_source_degraded",
                "primary_blocker": "sample_not_available",
                "next_action": "request_sample_or_trial",
            }
        ],
    }
    summary_path = tmp_path / "summary.json"
    review_path = tmp_path / "review.md"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    rc = main(["--summary", str(summary_path), "--output-review", str(review_path)])
    assert rc == 0
    text = review_path.read_text(encoding="utf-8")
    assert "docs-only feasibility smoke" in text
    assert "不能证明 vendor liquidation source 可用" in text
```

**Step 2: 跑测试确认失败**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_4a2_vendor_liquidation_data_feasibility.py -q
```

Expected: FAIL because script does not exist.

**Step 3: 实现 review script**

Output file must include:

```text
# External Signal Shadow Lab Stage 1.4A.2 Vendor Liquidation Data Feasibility Review

## 1. 结论
## 2. 本轮能证明什么 / 不能证明什么
## 3. Per-Vendor Audit Table
## 4. Recommended Vendor Order
## 5. Blockers And Next Actions
## 6. Safety Boundaries
```

Safety section must state:

```text
purchase_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
stage1_4b_candidate_replay_allowed = false
```

If every `vendor_decision.evidence_level` is `marketing_page` or `official_api_docs`, the review must explicitly say:

```text
this is docs-only feasibility smoke
it cannot prove vendor liquidation source availability
next action = request_sample_or_trial
```

**Step 4: 跑测试确认通过**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_4a2_vendor_liquidation_data_feasibility.py -q
```

Expected: PASS.

---

## Task 8: 生成 fixture summary/review smoke artifacts

**Files:**

- Create/Update: `reports/external_signal_shadow/stage1_4a2_vendor_liquidation_data_feasibility_summary.json`
- Create/Update: `docs/reviews/2026-06-15-external-signal-shadow-lab-stage1-4a2-vendor-liquidation-data-feasibility-review_CN.md`

**Step 1: 跑 docs-only fixture summary**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_4a2_vendor_liquidation_data_feasibility.py \
  --vendor-audits tests/fixtures/external_signal_shadow/stage1_4a2_vendor_audits_docs_only.json \
  --output-summary reports/external_signal_shadow/stage1_4a2_vendor_liquidation_data_feasibility_summary.json
```

Expected:

```text
summary decision = vendor_liquidation_source_degraded
primary_blocker = no_feasible_vendor_sample or sample_not_available
stage1_4b_candidate_replay_allowed = false
```

**Step 2: 生成 review**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_4a2_vendor_liquidation_data_feasibility.py \
  --summary reports/external_signal_shadow/stage1_4a2_vendor_liquidation_data_feasibility_summary.json \
  --output-review docs/reviews/2026-06-15-external-signal-shadow-lab-stage1-4a2-vendor-liquidation-data-feasibility-review_CN.md
```

Expected:

```text
review explains this is fixture/docs-only smoke unless real sample rows are supplied.
review does not claim vendor source feasible.
```

**Important:** This artifact is infrastructure evidence only. It cannot prove vendor data is actually available.

---

## Task 9: Verification suite

**Files:** all changed files.

**Step 1: Run focused tests**

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_config.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_models.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_decision.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_summary.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_sample_audit.py \
  tests/scripts/external_signal_shadow/test_run_stage1_4a2_vendor_liquidation_data_feasibility.py \
  tests/scripts/external_signal_shadow/test_review_stage1_4a2_vendor_liquidation_data_feasibility.py \
  -q
```

Expected: all pass.

**Step 2: Run External Signal Shadow suite**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow tests/scripts/external_signal_shadow -q
```

Expected: all pass.

**Step 3: Run ruff**

```bash
uv run ruff check \
  src/research/external_signal_shadow/stage1_4a2_vendor.py \
  scripts/external_signal_shadow/run_stage1_4a2_vendor_liquidation_data_feasibility.py \
  scripts/external_signal_shadow/review_stage1_4a2_vendor_liquidation_data_feasibility.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_config.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_models.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_decision.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_summary.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_sample_audit.py \
  tests/scripts/external_signal_shadow/test_run_stage1_4a2_vendor_liquidation_data_feasibility.py \
  tests/scripts/external_signal_shadow/test_review_stage1_4a2_vendor_liquidation_data_feasibility.py
```

Expected: all checks passed.

**Step 4: Optional full pytest**

```bash
PYTHONPATH=src:. uv run pytest -q
```

Expected: all pass. If full suite is slow, at minimum run focused + external signal suite + ruff and state full suite was not run.

---

## Task 10: Manual real-sample handoff after implementation

This task is not code. It defines how the user should use the implemented audit.

If user obtains a sample/trial export from a vendor, save it under ignored path:

```text
data/external_signal_shadow/vendor_liquidation_samples/{vendor}/
```

Then create/update a local audit JSON file, for example:

```text
data/external_signal_shadow/vendor_liquidation_samples/stage1_4a2_vendor_audits_real_sample.json
```

Run:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_4a2_vendor_liquidation_data_feasibility.py \
  --vendor-audits data/external_signal_shadow/vendor_liquidation_samples/stage1_4a2_vendor_audits_real_sample.json \
  --output-summary reports/external_signal_shadow/stage1_4a2_vendor_liquidation_data_feasibility_summary.json

PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_4a2_vendor_liquidation_data_feasibility.py \
  --summary reports/external_signal_shadow/stage1_4a2_vendor_liquidation_data_feasibility_summary.json \
  --output-review docs/reviews/2026-06-15-external-signal-shadow-lab-stage1-4a2-vendor-liquidation-data-feasibility-review_CN.md
```

Only if summary says:

```text
vendor_liquidation_source_feasible
```

then next action may become:

```text
write_stage1_4a3_vendor_sample_parser_plan
```

Still prohibited:

```text
Stage 1.4B candidate replay
paper trading
live trading
alpha interpretation
```

---

## Final Acceptance Checklist

- [ ] `configs/base.py` has Stage 1.4A.2 constants with comments.
- [ ] Vendor sample runtime path is gitignored.
- [ ] `VendorLiquidationAudit` validates all required evidence/license/access/exchange/side/cost fields.
- [ ] `sample_file_available=true` is bound to real `sample_file_path` and `audit_vendor_sample_file()`.
- [ ] `source_surface` is validated and evidence metadata is non-empty.
- [ ] Shared payload factory lives outside individual test modules.
- [ ] Docs-only and no-sample audits cannot be feasible.
- [ ] Paid sample / medium-high cost cannot be feasible without explicit user approval fields.
- [ ] Sample audit computes `history_days` and `timestamp_resolution_ms`.
- [ ] Gzipped sample inputs are supported.
- [ ] License unknown/restricted/disallowed cannot be feasible.
- [ ] Medium/high/enterprise cost cannot be feasible without explicit user approval.
- [ ] Review renders per-vendor table and recommendations.
- [ ] Review marks docs-only artifacts as not proving vendor data availability.
- [ ] Summary keeps all safety flags false.
- [ ] No script reads `.env`, secrets, or vendor API keys.
- [ ] Focused tests pass.
- [ ] External signal suite passes.
- [ ] Ruff passes.
