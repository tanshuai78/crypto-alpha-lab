# External Signal Shadow Lab Stage 1.5D Live Event-Source Smoke Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** 实现 Stage 1.5D Binance `futures_contract_launch` live event-source smoke collector，验证真实公告源的稳定性、延迟、解析、去重与 first futures bar observation，不输出交易信号。

**Architecture:** 新增独立 `stage1_5d_live_event_source_*` research modules 与两个 scripts。Collector 分为 announcement poll loop 与 bounded first futures bar observer queue；所有网络请求必须显式 `--live-public-readonly`，数据写入 append-only JSONL 与 summary/review。Stage 1.5D 只做 source smoke，不做 replay、收益、paper/live、execution。

**Tech Stack:** Python 3.11、标准库 `urllib.request` / `urllib.parse`、JSON/JSONL、`configs/base.py`、pytest、ruff、`PYTHONPATH=src:.`。

---

## 0. 执行边界

```text
scope = live_event_source_smoke_only
primary_event_type = futures_contract_launch
source = binance_official_announcements_public_readonly
forward_return_allowed = false
replay_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
trade_signal_allowed = false
```

禁止新增或调用：

```text
TradeIntent
SignalCandidate for execution
order endpoint
account endpoint
wallet endpoint
api key
private websocket
position sizing
```

---

## 1. Upstream Evidence Gate

Implementation 必须先验证 Stage 1.5C.1 / 1.5C rerun 证据存在并匹配：

```text
Stage 1.5C.1 decision == stage1_5c1_price_coverage_ready_for_1_5c_rerun
Stage 1.5C top_level_decision == stage1_5c_replay_completed
Stage 1.5C research_result_valid == true
Stage 1.5C promising_cells includes at least one 12h futures launch long-attention cell
paper/live/execution/alpha flags == false
```

Promising cell matching rule:

```text
Accept if any promising_cells item splits by "|" into:
  event_type == futures_contract_launch
  signed_mode == futures_launch_long_attention_diagnostic
  entry_delay == 12h
  filter_group in any allowed Stage 1.5C group

Do not require exact G1 match.
Current accepted examples:
  futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay
  futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only
Reject:
  4h cells
  short_access cells
  mixed/unknown event_type cells
```

若不满足，runner / summary 必须输出：

```text
decision = stage1_5d_smoke_invalid
blocker = upstream_evidence_missing_or_invalid
```

不要继续 network polling。

---

## 2. Output Artifacts

Data artifacts, gitignored. Runner must use `--output-root` and write daily rotated JSONL streams under that root. The fixed summary path may be overwritten as latest state.

```text
data/external_signal_shadow/stage1_5d/live_event_source_smoke/raw_payloads/YYYY-MM-DD.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/YYYY-MM-DD.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/heartbeats/YYYY-MM-DD.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/request_manifest/YYYY-MM-DD.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json
```

Fixture / debug smoke must use an isolated output root:

```text
data/external_signal_shadow/stage1_5d/fixture_smoke/
```

Fixture artifacts must always set:

```json
{
  "fixture_run": true,
  "debug_short_run": true,
  "research_result_valid": false
}
```

Review document:

```text
docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md
```

---

## 3. Decision Taxonomy

Allowed decisions:

```text
stage1_5d_smoke_observation_in_progress
stage1_5d_operational_pass_event_detection_unvalidated
stage1_5d_event_detection_passed
stage1_5d_smoke_failed
stage1_5d_smoke_invalid
```

Rules:

```text
fixture/debug short run => smoke_observation_in_progress, research_result_valid=false
live observation_hours < 24h => smoke_observation_in_progress, research_result_valid=false
zero event + observation_hours >= 24h + stable polling => operational_pass_event_detection_unvalidated
>=1 valid futures launch event detected => event_detection_passed
public source reachable but parser/heartbeat/source quality fails => smoke_failed
safety violation / upstream evidence missing / domain redirect violation => smoke_invalid
```

Zero-event smoke must never be `event_detection_passed`.
Short live smoke must never be `stage1_5d_operational_pass_event_detection_unvalidated`.

---

## 4. Implementation Tasks

### Task 1: Add Stage 1.5D Config Constants

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`

**Step 1: Write failing config tests**

```python
from configs import base


def test_stage1_5d_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_BASE_URL == "https://www.binance.com"
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_LIST_PATH
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_ANNOUNCEMENT_QUERY_PARAMS == {
        "type": "1",
        "pageNo": "1",
        "pageSize": "50",
    }
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_DOMAINS == ("binance.com", "www.binance.com")
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE == "futures_contract_launch"
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_ANNOUNCEMENT_DELAY_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DEFAULT_POLL_INTERVAL_SEC == 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_REQUEST_TIMEOUT_SEC == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RETRY_BUDGET == 2
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MIN_OPERATIONAL_OBSERVATION_HOURS == 24
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MIN_POLL_SUCCESS_RATE == 0.95
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_OBSERVATION_TIMEOUT_HOURS == 24
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_CHECK_BUDGET_PER_POLL >= 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RAW_PAYLOAD_RETENTION_DAYS >= 14
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MAX_RAW_PAYLOAD_BYTES_PER_DAY > 0
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py -q
```

Expected: fail because constants do not exist.

**Step 3: Add constants**

Append to `configs/base.py`:

```python
# ─── External Signal Shadow Lab Stage 1.5D: Live Event Source Smoke ────────

EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_BASE_URL = "https://www.binance.com"
EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_LIST_PATH = "/bapi/composite/v1/public/cms/article/list/query"
EXTERNAL_SIGNAL_STAGE1_5D_ANNOUNCEMENT_QUERY_PARAMS = {
    "type": "1",
    "pageNo": "1",
    "pageSize": "50",
}
EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_DOMAINS = ("binance.com", "www.binance.com")
EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE = "futures_contract_launch"
EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_ANNOUNCEMENT_DELAY_MS = 15 * 60 * 1000

EXTERNAL_SIGNAL_STAGE1_5D_DEFAULT_POLL_INTERVAL_SEC = 60
EXTERNAL_SIGNAL_STAGE1_5D_REQUEST_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_5D_RETRY_BUDGET = 2
EXTERNAL_SIGNAL_STAGE1_5D_MIN_OPERATIONAL_OBSERVATION_HOURS = 24
EXTERNAL_SIGNAL_STAGE1_5D_MIN_POLL_SUCCESS_RATE = 0.95
EXTERNAL_SIGNAL_STAGE1_5D_MAX_HEARTBEAT_GAP_COUNT = 1

EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_OBSERVATION_TIMEOUT_HOURS = 24
EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_POLL_INTERVAL_SEC = 60
EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_CHECK_BUDGET_PER_POLL = 3

EXTERNAL_SIGNAL_STAGE1_5D_RAW_PAYLOAD_RETENTION_DAYS = 14
EXTERNAL_SIGNAL_STAGE1_5D_REQUEST_MANIFEST_RETENTION_DAYS = 30
EXTERNAL_SIGNAL_STAGE1_5D_HEARTBEAT_RETENTION_DAYS = 30
EXTERNAL_SIGNAL_STAGE1_5D_MAX_RAW_PAYLOAD_BYTES_PER_DAY = 50_000_000
EXTERNAL_SIGNAL_STAGE1_5D_MAX_HEARTBEAT_ROWS_PER_DAY = 2_000
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py -q
```

Expected: pass.

---

### Task 2: Add Models

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5d_live_event_source_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_models.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5d_live_event_source_models import (
    LiveEventSourceDecision,
    LiveFuturesLaunchEvent,
    PollHeartbeat,
)


def test_decision_enum_values():
    assert LiveEventSourceDecision.OBSERVATION_IN_PROGRESS.value == "stage1_5d_smoke_observation_in_progress"
    assert LiveEventSourceDecision.OPERATIONAL_UNVALIDATED.value == "stage1_5d_operational_pass_event_detection_unvalidated"
    assert LiveEventSourceDecision.EVENT_DETECTION_PASSED.value == "stage1_5d_event_detection_passed"
    assert LiveEventSourceDecision.FAILED.value == "stage1_5d_smoke_failed"
    assert LiveEventSourceDecision.INVALID.value == "stage1_5d_smoke_invalid"


def test_live_event_defaults_are_non_trading():
    event = LiveFuturesLaunchEvent(
        event_id="e1",
        event_type="futures_contract_launch",
        source_name="binance_official_announcements",
        source_profile="binance_official_announcements_like_rows",
        title="Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract",
        symbols=("ABCUSDT",),
        base_assets=("ABC",),
        detected_at_ms=1000,
        available_at_ms=1000,
    )
    assert event.paper_trading_allowed is False
    assert event.live_trading_allowed is False
    assert event.execution_engine_allowed is False
    assert event.alpha_interpretation_allowed is False
    assert event.trade_signal_allowed is False
    assert event.replay_context_label_only is True


def test_heartbeat_has_poll_timing_fields():
    hb = PollHeartbeat(
        poll_started_at_ms=1000,
        poll_completed_at_ms=1100,
        configured_poll_interval_sec=60,
    )
    assert hb.poll_duration_ms == 100
    assert hb.configured_poll_interval_sec == 60
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_models.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement dataclasses / enum**

Classes:

```python
class LiveEventSourceDecision(Enum): ...

@dataclass(frozen=True)
class LiveFuturesLaunchEvent: ...

@dataclass(frozen=True)
class PollHeartbeat: ...
```

Required fields include:

```text
source_published_at_ms_confidence
published_time_source
available_at_ms
first_futures_bar_status
stage1_5c_research_context_label
signal_strength_score = None
trade_signal_allowed = false
```

Summary-level fields required by later tasks:

```text
fixture_run
debug_short_run
observation_hours
research_result_valid
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_models.py -q
```

Expected: pass.

---

### Task 3: Add Upstream Evidence Gate

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5d_live_event_source_evidence.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_evidence.py`

**Step 1: Write failing tests**

```python
import json

import pytest

from src.research.external_signal_shadow.stage1_5d_live_event_source_evidence import validate_upstream_evidence


def test_validate_upstream_evidence_passes_required_decisions(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": ["futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is True
    assert result["blockers"] == []


def test_validate_upstream_evidence_accepts_g2_12h_long_attention_cell(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": ["futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is True
    assert result["matched_promising_cell"] == "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only"


def test_validate_upstream_evidence_rejects_non_12h_or_wrong_mode_cells(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [
            "futures_contract_launch|futures_launch_long_attention_diagnostic|4h|G2_price_coverage_only",
            "futures_contract_launch|futures_launch_short_access_diagnostic|12h|G2_price_coverage_only",
        ],
    }))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is False
    assert "missing_futures_launch_long_attention_12h_promising_cell" in result["blockers"]


def test_validate_upstream_evidence_blocks_missing_promising_cell(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    c.write_text(json.dumps({"top_level_decision": "stage1_5c_replay_completed", "research_result_valid": True, "promising_cells": []}))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is False
    assert "missing_futures_launch_long_attention_12h_promising_cell" in result["blockers"]


def test_validate_upstream_evidence_rejects_paper_live_flags(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": ["futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"],
        "paper_trading_allowed": True,
    }))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is False
    assert "unsafe_upstream_trading_flag" in result["blockers"]
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_evidence.py -q
```

Expected: fail.

**Step 3: Implement evidence validation**

Function:

```python
def validate_upstream_evidence(stage1_5c1_summary_path: str | Path, stage1_5c_summary_path: str | Path) -> dict: ...
```

Must return:

```json
{
  "upstream_evidence_valid": false,
  "blockers": [],
  "stage1_5c1_decision": "...",
  "stage1_5c_top_level_decision": "...",
  "matched_promising_cell": null
}
```

Implementation must parse `promising_cells` by `cell.split("|")`; do not use fragile exact-string matching except for the required field values listed in Section 1.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_evidence.py -q
```

Expected: pass.

---

### Task 4: Add Public Client Safety / Domain Redirect Checks

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py`

**Step 1: Write failing tests**

```python
from unittest.mock import patch

import pytest

from src.research.external_signal_shadow.stage1_5d_live_event_source_client import (
    build_announcement_list_url,
    fetch_public_json,
    host_allowed,
    validate_url_allowlist,
)


def test_host_allowlist_accepts_exact_and_subdomain():
    assert host_allowed("binance.com", ("binance.com",)) is True
    assert host_allowed("www.binance.com", ("binance.com",)) is True


def test_host_allowlist_rejects_suffix_spoofing():
    assert host_allowed("evilbinance.com", ("binance.com",)) is False
    assert host_allowed("binance.com.evil.com", ("binance.com",)) is False


def test_validate_url_rejects_disallowed_domain():
    with pytest.raises(ValueError, match="domain_not_allowed"):
        validate_url_allowlist("https://binance.com.evil.com/api", ("binance.com",))


def test_fetch_public_json_requires_live_flag():
    with patch("urllib.request.urlopen") as urlopen:
        with pytest.raises(PermissionError):
            fetch_public_json("https://www.binance.com/test", live_public_readonly=False)
        urlopen.assert_not_called()


def test_announcement_list_url_uses_configured_query_params():
    url = build_announcement_list_url(
        base_url="https://www.binance.com",
        path="/bapi/composite/v1/public/cms/article/list/query",
        query_params={"type": "1", "pageNo": "1", "pageSize": "50"},
    )
    assert url.startswith("https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?")
    assert "type=1" in url
    assert "pageNo=1" in url
    assert "pageSize=50" in url


def test_fetch_public_json_rejects_redirect_final_host_not_allowed():
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return "https://binance.com.evil.com/final"

        def read(self):
            return b'{"ok": true}'

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        with pytest.raises(ValueError, match="redirect_final_domain_not_allowed"):
            fetch_public_json("https://www.binance.com/test", live_public_readonly=True, timeout_sec=1.0)
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py -q
```

Expected: fail.

**Step 3: Implement client**

Functions:

```python
def build_announcement_list_url(base_url: str, path: str, query_params: dict[str, str]) -> str: ...
def host_allowed(host: str, allowed_domains: tuple[str, ...]) -> bool: ...
def validate_url_allowlist(url: str, allowed_domains: tuple[str, ...]) -> dict: ...
def fetch_public_json(url: str, live_public_readonly: bool, timeout_sec: float, retry_budget: int = 2) -> dict: ...
```

`fetch_public_json` must record:

```text
requested_url
final_url
requested_host
final_host
redirect_count
http_status
row_count / payload_size_bytes
error
```

Final redirected host must pass allowlist.
Both requested URL and final URL must be recorded in request manifest rows.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py -q
```

Expected: pass.

---

### Task 5: Add Parser / Symbol Extraction / Dedupe

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
    classify_event_type,
    dedupe_events,
    extract_futures_launch_symbols,
    normalize_live_event,
    parse_binance_announcement_payload,
)


def test_extract_symbols_from_binance_futures_launch_title():
    title = "Binance Futures Will Launch USDⓈ-Margined ZESTUSDT and BTWUSDT Perpetual Contracts"
    assert extract_futures_launch_symbols(title) == ["ZESTUSDT", "BTWUSDT"]


def test_classify_futures_launch_only():
    assert classify_event_type("Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract") == "futures_contract_launch"
    assert classify_event_type("Binance Will Delist ABC") == "ignored_event_type"


def test_normalize_event_available_at_uses_detected_when_source_time_low_confidence():
    row = normalize_live_event(
        raw={"title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract", "code": "abc"},
        source_parent_url="https://www.binance.com/en/support/announcement",
        detected_at_ms=10_000,
        source_published_at_ms=1_000,
        source_published_at_ms_confidence="low",
    )
    assert row["available_at_ms"] == 10_000
    assert row["historical_delay_comparison_allowed"] is False


def test_dedupe_uses_article_id_or_url_not_timestamp_only():
    a = {"source_article_id": "abc", "source_detail_url_normalized": "u1", "source_published_at_ms": 1, "stable_event_key": "k1"}
    b = {"source_article_id": "abc", "source_detail_url_normalized": "u1", "source_published_at_ms": 2, "stable_event_key": "k2"}
    rows = dedupe_events([a, b])
    assert len(rows) == 1


def test_parser_empty_articles_is_valid_zero_events():
    result = parse_binance_announcement_payload({"data": {"catalogs": [{"articles": []}]}})
    assert result["events"] == []
    assert result["source_format_drift"] is False
    assert result["schema_parse_error"] is False


def test_parser_marks_source_format_drift_when_catalogs_missing():
    result = parse_binance_announcement_payload({"data": {"items": []}})
    assert result["events"] == []
    assert result["source_format_drift"] is True
    assert result["source_format_drift_count"] == 1


def test_parser_marks_schema_parse_error_when_articles_not_list():
    result = parse_binance_announcement_payload({"data": {"catalogs": [{"articles": {"bad": "shape"}}]}})
    assert result["events"] == []
    assert result["schema_parse_error"] is True
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: fail.

**Step 3: Implement parser**

Functions:

```python
def classify_event_type(title: str) -> str: ...
def extract_futures_launch_symbols(title: str) -> list[str]: ...
def parse_binance_announcement_payload(payload: dict) -> dict: ...
def normalize_live_event(...) -> dict: ...
def dedupe_events(rows: list[dict]) -> list[dict]: ...
def build_stable_event_key(...): ...
def build_event_revision_hash(...): ...
```

Parser must distinguish:

```text
expected schema + empty articles list => valid zero events
raw payload has data but expected schema path missing => source_format_drift
articles exists but is not list => schema_parse_error
```

Do not silently convert unknown Binance payload shapes into clean zero-event output.

`normalize_live_event` must set:

```text
stage1_5c_research_context_label = futures_launch_long_attention_12h_close_price_replay_only
trade_signal_allowed = false
replay_context_label_only = true
paper/live/execution/alpha = false
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: pass.

---

### Task 6: Add First Futures Bar Observer Queue

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5d_live_event_source_first_bar.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_first_bar.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5d_live_event_source_first_bar import (
    check_first_bar_for_event,
    fetch_first_bar_status_for_event,
    process_first_bar_queue,
)


def test_first_bar_found_at_or_after_detection():
    event = {"event_id": "e1", "symbols": ["ABCUSDT"], "detected_at_ms": 1_000}
    bars = {"ABCUSDT": [{"bar_start_ms": 900}, {"bar_start_ms": 1_800}]}
    updated = check_first_bar_for_event(event, bars, now_ms=2_000)
    assert updated["first_futures_bar_status"] == "found"
    assert updated["first_futures_bar_start_ms"] == 1_800


def test_first_bar_not_yet_available_before_timeout():
    event = {"event_id": "e1", "symbols": ["ABCUSDT"], "detected_at_ms": 1_000}
    updated = check_first_bar_for_event(event, {}, now_ms=2_000, timeout_ms=24 * 3600_000)
    assert updated["first_futures_bar_status"] == "not_yet_available"


def test_first_bar_all_bars_before_detection_is_not_yet_available():
    event = {"event_id": "e1", "symbols": ["ABCUSDT"], "detected_at_ms": 1_000}
    bars = {"ABCUSDT": [{"bar_start_ms": 100}, {"bar_start_ms": 900}]}
    updated = check_first_bar_for_event(event, bars, now_ms=2_000, timeout_ms=24 * 3600_000)
    assert updated["first_futures_bar_status"] == "not_yet_available"
    assert updated["first_futures_bar_start_ms"] is None


def test_first_bar_observer_budget_does_not_process_entire_queue():
    queue = [{"event_id": f"e{i}", "symbols": ["ABCUSDT"], "detected_at_ms": 0} for i in range(5)]
    processed, remaining = process_first_bar_queue(queue, bars_by_symbol={}, now_ms=1_000, budget=2)
    assert len(processed) == 2
    assert len(remaining) == 3


def test_first_bar_network_error_keeps_event_observable_without_blocking():
    event = {"event_id": "e1", "symbols": ["ABCUSDT"], "detected_at_ms": 1_000}
    result = fetch_first_bar_status_for_event(
        event=event,
        fetch_result={"ok": False, "error": "timeout", "request_manifest_row": {"error": "timeout"}},
        now_ms=2_000,
    )
    assert result["first_futures_bar_status"] == "network_error"
    assert result["request_manifest_rows"][0]["error"] == "timeout"
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_first_bar.py -q
```

Expected: fail.

**Step 3: Implement observer**

Must be bounded and non-blocking relative to announcement polling.

Functions:

```python
def check_first_bar_for_event(event: dict, bars_by_symbol: dict, now_ms: int, timeout_ms: int) -> dict: ...
def fetch_first_bar_status_for_event(event: dict, fetch_result: dict, now_ms: int) -> dict: ...
def process_first_bar_queue(queue: list[dict], bars_by_symbol: dict, now_ms: int, budget: int) -> tuple[list[dict], list[dict]]: ...
```

Live first-bar observation rules:

```text
Use public Binance USD-M exchangeInfo / klines only.
Reuse Stage 1.5C.1 public client semantics where practical.
Every first-bar network check writes request_manifest row.
network_error must not block announcement_poll_loop.
symbol_not_in_current_exchangeinfo => first_futures_bar_status = current_exchangeinfo_not_found
All bars before detected_at_ms => not_yet_available, not found.
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_first_bar.py -q
```

Expected: pass.

---

### Task 7: Add Storage / Rotation Utilities

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py`

**Step 1: Write failing tests**

```python
import json

from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import (
    append_jsonl,
    build_daily_path,
    build_stream_paths,
    enforce_payload_budget,
)


def test_build_daily_path_includes_utc_date(tmp_path):
    path = build_daily_path(tmp_path, "events", 1710000000000)
    assert "events" in str(path)
    assert path.name.endswith(".jsonl")


def test_build_stream_paths_under_output_root(tmp_path):
    paths = build_stream_paths(tmp_path, timestamp_ms=1710000000000)
    assert paths["events"].parent.parent == tmp_path
    assert "events" in str(paths["events"])
    assert "raw_payloads" in str(paths["raw_payloads"])
    assert paths["summary"].name == "binance_futures_launch_smoke_summary.json"


def test_append_jsonl_writes_one_row(tmp_path):
    path = tmp_path / "events.jsonl"
    append_jsonl(path, {"a": 1})
    assert json.loads(path.read_text().strip()) == {"a": 1}


def test_enforce_payload_budget_blocks_large_day(tmp_path):
    path = tmp_path / "raw.jsonl"
    path.write_text("x" * 101)
    result = enforce_payload_budget(path, max_bytes=100)
    assert result["storage_budget_passed"] is False
    assert result["blocker"] == "max_raw_payload_bytes_per_day_exceeded"
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py -q
```

Expected: fail.

**Step 3: Implement storage helpers**

Functions:

```python
def build_daily_path(root: str | Path, stream_name: str, timestamp_ms: int) -> Path: ...
def build_stream_paths(output_root: str | Path, timestamp_ms: int) -> dict[str, Path]: ...
def append_jsonl(path: str | Path, row: dict) -> None: ...
def enforce_payload_budget(path: str | Path, max_bytes: int) -> dict: ...
```

No truncating existing files silently.

Runner must use `--output-root` and these stream paths. Do not mix fixed individual output paths with daily rotation in Stage 1.5D v1.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py -q
```

Expected: pass.

---

### Task 8: Add Summary Decision Engine

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5d_live_event_source_summary import build_smoke_summary


def test_short_live_smoke_is_observation_in_progress_not_operational_pass():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True, "heartbeat_gap": False}],
        events=[],
        request_manifest=[],
        fixture_run=False,
        debug_short_run=True,
        observation_hours=0.05,
    )
    assert summary["decision"] == "stage1_5d_smoke_observation_in_progress"
    assert summary["event_detection_validated"] is False
    assert summary["research_result_valid"] is False


def test_fixture_zero_event_smoke_marks_research_result_valid_false():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True, "heartbeat_gap": False}],
        events=[],
        request_manifest=[],
        fixture_run=True,
        debug_short_run=True,
        observation_hours=0.0,
    )
    assert summary["decision"] == "stage1_5d_smoke_observation_in_progress"
    assert summary["fixture_run"] is True
    assert summary["research_result_valid"] is False


def test_zero_event_24h_stable_polling_is_operational_unvalidated():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True, "heartbeat_gap": False} for _ in range(24)],
        events=[],
        request_manifest=[],
        fixture_run=False,
        debug_short_run=False,
        observation_hours=24.0,
    )
    assert summary["decision"] == "stage1_5d_operational_pass_event_detection_unvalidated"
    assert summary["event_detection_validated"] is False
    assert summary["research_result_valid"] is True


def test_event_detection_passed_requires_event_and_first_bar_status():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True, "heartbeat_gap": False}],
        events=[{"event_type": "futures_contract_launch", "symbol_parse_status": "parsed", "first_futures_bar_status": "found"}],
        request_manifest=[],
        fixture_run=False,
        debug_short_run=False,
        observation_hours=1.0,
    )
    assert summary["decision"] == "stage1_5d_event_detection_passed"
    assert summary["event_detection_validated"] is True
    assert summary["research_result_valid"] is True


def test_upstream_invalid_makes_smoke_invalid():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": False, "blockers": ["missing"]},
        heartbeats=[],
        events=[],
        request_manifest=[],
        fixture_run=False,
        debug_short_run=False,
        observation_hours=0.0,
    )
    assert summary["decision"] == "stage1_5d_smoke_invalid"
    assert "upstream_evidence_missing_or_invalid" in summary["blockers"]
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py -q
```

Expected: fail.

**Step 3: Implement summary**

Function:

```python
def build_smoke_summary(
    upstream_evidence: dict,
    heartbeats: list[dict],
    events: list[dict],
    request_manifest: list[dict],
    fixture_run: bool,
    debug_short_run: bool,
    observation_hours: float,
) -> dict: ...
```

Must include all safety flags false and:

```text
fixture_run
debug_short_run
observation_hours
research_result_valid
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py -q
```

Expected: pass.

---

### Task 9: Add Collector Orchestration

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5d_live_event_source_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_collector.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5d_live_event_source_collector import run_one_poll_cycle


def test_poll_cycle_parses_futures_launch_and_queues_first_bar():
    payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "abc",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }
    result = run_one_poll_cycle(
        payload=payload,
        detected_at_ms=1710000060000,
        source_parent_url="https://www.binance.com/en/support/announcement",
        first_bar_queue=[],
    )
    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "futures_contract_launch"
    assert len(result["first_bar_queue"]) == 1
    assert result["heartbeat"]["poll_success"] is True


def test_poll_cycle_zero_events_still_heartbeat_success():
    payload = {"data": {"catalogs": [{"articles": []}]}}
    result = run_one_poll_cycle(payload=payload, detected_at_ms=1710000060000, source_parent_url="https://www.binance.com", first_bar_queue=[])
    assert result["events"] == []
    assert result["heartbeat"]["poll_success"] is True


def test_poll_cycle_schema_drift_is_not_clean_zero_events():
    payload = {"data": {"items": []}}
    result = run_one_poll_cycle(payload=payload, detected_at_ms=1710000060000, source_parent_url="https://www.binance.com", first_bar_queue=[])
    assert result["events"] == []
    assert result["heartbeat"]["poll_success"] is False
    assert result["heartbeat"]["source_format_drift"] is True
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_collector.py -q
```

Expected: fail.

**Step 3: Implement one-cycle orchestration**

Function:

```python
def run_one_poll_cycle(payload: dict, detected_at_ms: int, source_parent_url: str, first_bar_queue: list[dict]) -> dict: ...
```

This function is pure-ish for testing: no network, no sleeping.
It must call `parse_binance_announcement_payload`; parser schema drift must become heartbeat failure, not clean zero-event success.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_collector.py -q
```

Expected: pass.

---

### Task 10: Add Runner CLI

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing tests**

```python
import json
from unittest.mock import patch

from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import main


def test_runner_requires_live_flag_without_fixture(tmp_path):
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--output-root", str(output_root),
        "--output-summary", str(summary),
    ]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 2
    s = json.loads(summary.read_text())
    assert s["decision"] == "stage1_5d_smoke_invalid"
    assert "missing_live_flag_or_fixture" in s["blockers"]


def test_runner_fixture_zero_event_operational_pass(tmp_path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({"data": {"catalogs": [{"articles": []}]}}))
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "fixture_smoke"
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": ["futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--fixture-json", str(fixture),
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["decision"] == "stage1_5d_smoke_observation_in_progress"
    assert s["fixture_run"] is True
    assert s["research_result_valid"] is False
    assert s["event_detection_validated"] is False
    assert (output_root / "heartbeats").exists()
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: fail.

**Step 3: Implement runner**

CLI must support:

```text
--live-public-readonly
--fixture-json
--poll-interval-sec
--max-polls
--max-seconds
--stage1-5c1-summary
--stage1-5c-summary
--output-root
--output-summary
```

Default real output root:

```text
data/external_signal_shadow/stage1_5d/live_event_source_smoke/
```

No network without `--live-public-readonly` unless `--fixture-json` is provided.
If neither `--fixture-json` nor `--live-public-readonly` is present, exit `2`, write `decision=stage1_5d_smoke_invalid`, and include blocker `missing_live_flag_or_fixture`. This failure mode must be checked before reading default upstream evidence paths, so tests are isolated from real local summaries.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: pass.

---

### Task 11: Add Review Generator

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing tests**

```python
import json
from unittest.mock import patch

from scripts.external_signal_shadow.review_stage1_5d_live_event_source_smoke_collector import main


def test_review_contains_decision_and_safety_flags(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_5d_smoke_observation_in_progress",
        "event_detection_validated": False,
        "fixture_run": True,
        "debug_short_run": True,
        "observation_hours": 0.0,
        "research_result_valid": False,
        "poll_count": 1,
        "new_futures_launch_event_count": 0,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "blockers": [],
    }))
    args = ["review_stage1_5d_live_event_source_smoke_collector.py", "--summary", str(summary), "--output-review", str(review)]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 0
    text = review.read_text()
    assert "stage1_5d_smoke_observation_in_progress" in text
    assert "event_detection_validated" in text
    assert "research_result_valid" in text
    assert "paper_trading_allowed" in text
    for forbidden in ["TODO", "TBD", "placeholder", "FIXME"]:
        assert forbidden not in text
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: fail.

**Step 3: Implement review generator**

Must include sections:

```text
Decision
Upstream Evidence Gate
Polling Health
Event Detection
First Futures Bar Observation
Safety Boundaries
Allowed Next Action
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: pass.

---

### Task 12: Real Smoke Run Procedure

**Step 1: Verify data paths are gitignored**

Create the parent directory before checking. This project already has a global `data/` ignore rule; this step confirms coverage, it should not add a new rule unless the check fails.

```bash
mkdir -p data/external_signal_shadow/stage1_5d/live_event_source_smoke
git check-ignore -v data/
git check-ignore -v data/external_signal_shadow/stage1_5d/live_event_source_smoke/
```

If any path is not ignored, update `.gitignore` before running.

**Step 2: Run fixture smoke first**

Create the fixture if it does not exist:

```bash
mkdir -p tests/fixtures/external_signal_shadow/stage1_5d
cat > tests/fixtures/external_signal_shadow/stage1_5d/binance_futures_launch_fixture.json <<'JSON'
{"data":{"catalogs":[{"articles":[{"code":"fixture-abc","title":"Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract","releaseDate":1710000000000}]}]}}
JSON
```

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  --fixture-json tests/fixtures/external_signal_shadow/stage1_5d/binance_futures_launch_fixture.json \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-root data/external_signal_shadow/stage1_5d/fixture_smoke \
  --output-summary data/external_signal_shadow/stage1_5d/fixture_smoke/binance_futures_launch_smoke_summary.json \
  --max-polls 1
```

Expected: exits 0 and writes summary with:

```text
fixture_run = true
debug_short_run = true
research_result_valid = false
decision = stage1_5d_smoke_observation_in_progress
```

**Step 3: Run short live public readonly smoke**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-root data/external_signal_shadow/stage1_5d/live_event_source_smoke \
  --output-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --poll-interval-sec 60 \
  --max-polls 3 \
  --live-public-readonly
```

Expected outcomes:

```text
api_key_used = false
private_endpoint_used = false
poll_count >= 1
summary decision is one of allowed decisions
zero new events in 3-poll smoke => stage1_5d_smoke_observation_in_progress
research_result_valid = false unless observation_hours >= 24 or event_detection_validated = true
```

**Step 4: Generate review**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_5d_live_event_source_smoke_collector.py \
  --summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --output-review docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md
```

---

## 5. Verification Commands

Run targeted tests:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_models.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_evidence.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_first_bar.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Run related Stage 1.5 regression tests:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_*.py \
  tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5c_external_catalyst_replay.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5c_external_catalyst_replay.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5c1_price_coverage_expansion.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5c1_price_coverage_expansion.py \
  -q
```

Run ruff:

```bash
PYTHONPATH=src:. uv run ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d* \
  tests/research/external_signal_shadow/test_stage1_5d_*.py \
  tests/scripts/external_signal_shadow/*stage1_5d*
```

Run safety grep:

```bash
! rg -n "TradeIntent|SignalCandidate|order_endpoint|account_endpoint|private_ws|apiKey|secret|position sizing" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d*
```

Expected: zero matches. If this command finds any match, stop and remove the execution/private-endpoint dependency.

---

## 6. Completion Criteria

Implementation is complete only when:

```text
all Stage 1.5D targeted tests pass
related Stage 1.5C / 1.5C.1 regression tests pass
ruff passes
fixture smoke writes valid summary/review
short live public readonly smoke writes manifest + heartbeat + summary
review contains no TODO/TBD/FIXME/placeholder
paper/live/execution/alpha flags are false
safety grep has zero matches for execution/private-endpoint terms
```

Do not commit automatically. End with:

```bash
git status --short
```

and list changed files for user review.
