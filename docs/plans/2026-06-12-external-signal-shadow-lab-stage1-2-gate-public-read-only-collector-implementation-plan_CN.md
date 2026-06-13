# External Signal Shadow Lab Stage 1.2 Gate Public Read-Only Collector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. For code changes use `test-driven-development`; before claiming completion use `verification-before-completion`.

**目标：** 实现一个 Gate 官方公开 REST 行情快照 collector，把 `BTC_USDT / ETH_USDT / SOL_USDT / XRP_USDT / DOGE_USDT` 的只读市场快照转换为 External Signal Shadow Lab Stage 1 raw JSONL，并通过现有 Stage 1 connector 输出 observation-only normalized events、summary 和中文 review。

**执行前状态：** `decision = approved_with_required_fixes`。本计划已吸收 review 修正：完整 price map schema、不修改 `run_file_backed_connector` 核心签名、拒绝 response pair mismatch、只允许 `/spot/tickers` safe path、review 必须同时读取 collector summary 和 connector summary、mock/live 参数互斥、`event_time_policy` 放在 metadata、显式验证不读取 env/secrets。

**架构：** 第一版只做 Gate public REST snapshot collector，不使用 Gate SDK、ccxt、API key、账户接口或 private endpoint。collector 逐 symbol 请求 `/spot/tickers?currency_pair=...`，生成 raw wrapper；然后复用 Stage 1 file-backed connector normalize，最终由 Stage 1.2 review 脚本输出基础设施结论。

**技术栈：** Python stdlib `urllib.request/json/time/datetime/hashlib`，现有 `configs/base.py`，现有 `research.external_signal_shadow` package，pytest fixture/mock HTTP response，真实联网必须显式 `--live-public-readonly`。

---

## 全局边界

本计划只验证公开只读 collector 基础设施，不验证 alpha。

硬边界：

- 不使用 API key。
- 不读取 `.env`、环境变量、secret 文件。
- 不使用 Gate SDK、ccxt、requests auth session。
- 不读取 `os.environ`、`.env`、`GATE_API_KEY`、`GATE_SECRET`。
- 不调用 private endpoint。
- 不读取账户、余额、仓位、订单。
- 不提交 order / cancel / transfer / swap。
- 不生成 directional shadow order。
- `cex_market_snapshot` 永远是 `observation_only`。
- `event_time_policy` 必须写在 `raw_payload.metadata.event_time_policy`，与 Stage 1 connector 现有读取口径保持一致。
- `event_density_alpha_valid = false`。
- `alpha_interpretation_allowed = false`。
- `exchange_paper_trading_allowed = false`。
- `execution_engine_allowed = false`。

真实 raw / normalized runtime data 必须被 `.gitignore` 忽略。

---

## Task 0：同步上下文与确认工作区

**Files:**

- Read: `docs/designs/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-design_CN.md`
- Read: `docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-connector-review_CN.md`
- Read: `docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-1-manual-payload-dry-run-review_CN.md`
- Read: `configs/base.py`
- Read: `.gitignore`

**Step 1: 确认 worktree**

Run:

```bash
git status --short --branch
pwd
```

Expected:

```text
branch = feature/external-signal-shadow-stage1
cwd contains .worktrees/external-signal-shadow-stage1
```

**Step 2: 确认 import convention**

Run:

```bash
PYTHONPATH=src uv run python - <<'PY'
import importlib
for name in [
    "research.external_signal_shadow.file_backed_connector",
    "research.external_signal_shadow.connector_summary",
    "research.external_signal_shadow.schemas",
]:
    importlib.import_module(name)
    print(f"IMPORT_OK {name}")
PY
```

Expected:

```text
IMPORT_OK research.external_signal_shadow.file_backed_connector
IMPORT_OK research.external_signal_shadow.connector_summary
IMPORT_OK research.external_signal_shadow.schemas
```

**Step 3: 检查 runtime data ignore**

Run:

```bash
git check-ignore data/external_signal_shadow/raw/gate_public_market_snapshot_collector/2026-06-12.jsonl || true
git check-ignore data/external_signal_shadow/normalized/stage1_2_gate_public_events.jsonl || true
```

Expected:

- 如果已有 ignore，命令输出路径。
- 如果没有输出，Task 1 先补 `.gitignore`。

---

## Task 1：补 `.gitignore` 与 Stage 1.2 配置

**Files:**

- Modify: `.gitignore`
- Modify: `configs/base.py`
- Create if missing: `tests/research/external_signal_shadow/__init__.py`
- Test: `tests/research/external_signal_shadow/test_gate_public_collector_config.py`

### Step 1: 准备测试目录

Run:

```bash
mkdir -p tests/research/external_signal_shadow
touch tests/research/external_signal_shadow/__init__.py
```

### Step 2: 写失败测试

Create `tests/research/external_signal_shadow/test_gate_public_collector_config.py`:

```python
from __future__ import annotations

from configs import base


def test_stage1_2_gate_config_is_public_readonly() -> None:
    assert base.EXTERNAL_SIGNAL_STAGE1_2_GATE_REST_BASE_URL == "https://api.gateio.ws/api/v4"
    assert base.EXTERNAL_SIGNAL_STAGE1_2_GATE_TICKERS_PATH == "/spot/tickers"
    assert base.EXTERNAL_SIGNAL_STAGE1_2_ALLOWED_GATE_PAIRS == (
        "BTC_USDT",
        "ETH_USDT",
        "SOL_USDT",
        "XRP_USDT",
        "DOGE_USDT",
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_2_TIMEOUT_SEC > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_2_MAX_RETRIES >= 0
    assert base.EXTERNAL_SIGNAL_STAGE1_2_RETRY_BACKOFF_SEC >= 0
    assert base.EXTERNAL_SIGNAL_STAGE1_2_INTER_REQUEST_DELAY_SEC >= 0
    assert "readonly" in base.EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT.lower()
```

### Step 2: 跑测试确认失败

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_gate_public_collector_config.py -q
```

Expected: FAIL，缺少 `EXTERNAL_SIGNAL_STAGE1_2_*` constants。

### Step 3: 修改 `.gitignore`

Ensure `.gitignore` contains:

```gitignore
data/external_signal_shadow/raw/
data/external_signal_shadow/normalized/
```

如果已有同等规则，不重复添加。

### Step 4: 修改 `configs/base.py`

Add constants with comments near existing External Signal Shadow constants:

```python
# Stage 1.2 Gate public REST base URL. Public-readonly only; no authenticated endpoints.
EXTERNAL_SIGNAL_STAGE1_2_GATE_REST_BASE_URL = "https://api.gateio.ws/api/v4"

# Stage 1.2 Gate spot ticker path. Safe path must remain public market data.
EXTERNAL_SIGNAL_STAGE1_2_GATE_TICKERS_PATH = "/spot/tickers"

# Stage 1.2 allowed Gate pairs. Keep small CEX majors only for first collector dry run.
EXTERNAL_SIGNAL_STAGE1_2_ALLOWED_GATE_PAIRS = (
    "BTC_USDT",
    "ETH_USDT",
    "SOL_USDT",
    "XRP_USDT",
    "DOGE_USDT",
)

# Stage 1.2 HTTP timeout for public readonly calls. Safe range: 5-30 seconds.
EXTERNAL_SIGNAL_STAGE1_2_TIMEOUT_SEC = 10.0

# Stage 1.2 retry count for public readonly calls. Safe range: 0-2; avoid API hammering.
EXTERNAL_SIGNAL_STAGE1_2_MAX_RETRIES = 1

# Stage 1.2 backoff between retry attempts. Safe range: 1-10 seconds.
EXTERNAL_SIGNAL_STAGE1_2_RETRY_BACKOFF_SEC = 2.0

# Stage 1.2 delay between per-symbol public calls. Safe range: 0.1-2.0 seconds; reduces 429 risk.
EXTERNAL_SIGNAL_STAGE1_2_INTER_REQUEST_DELAY_SEC = 0.3

# Stage 1.2 User-Agent. Identifies research-only readonly collector; not a trading client.
EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT = "crypto-alpha-lab-research-readonly/0.1"
```

### Step 5: 跑测试确认通过

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_gate_public_collector_config.py -q
```

Expected: PASS.

### Step 6: 检查 ignore 生效

Run:

```bash
git check-ignore data/external_signal_shadow/raw/gate_public_market_snapshot_collector/2026-06-12.jsonl
git check-ignore data/external_signal_shadow/normalized/stage1_2_gate_public_events.jsonl
```

Expected: both paths printed.

---

## Task 2：扩展 Stage 1 schema/event type whitelist

**Files:**

- Modify: `src/research/external_signal_shadow/schemas.py`
- Modify: `src/research/external_signal_shadow/file_backed_connector.py` if event whitelist is there
- Do not modify: `run_file_backed_connector` function signature
- Test: `tests/research/external_signal_shadow/test_stage1_2_cex_market_snapshot_schema.py`

### Step 1: 写失败测试

Create `tests/research/external_signal_shadow/test_stage1_2_cex_market_snapshot_schema.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from research.external_signal_shadow.file_backed_connector import run_file_backed_connector


def _wrapper(now_ms: int = 1781165880123) -> dict:
    return {
        "source": "gate_public_market_snapshot_collector",
        "source_vendor": "gate",
        "source_surface": "gate_api_v4_public_market_data",
        "source_capture_method": "public_rest_snapshot",
        "source_skill": "gate_public_market_snapshot_collector",
        "data_quality": "api_snapshot",
        "capture_id": "gate_public_market_snapshot_20260612_001",
        "captured_by": "script",
        "source_observed_at_ms": now_ms,
        "fetched_at_ms": now_ms,
        "available_at_ms": now_ms,
        "field_confidence": {
            "event_time_ms": "available_at_fallback",
            "symbol": "normalized",
            "score": "missing",
        },
        "raw_payload": {
            "event_type": "cex_market_snapshot",
            "chain": "cex",
            "symbol": "BTCUSDT",
            "event_time_ms": now_ms,
            "direction_hint": "unknown",
            "score_interpretation_allowed": False,
            "triple_barrier_directional_order_allowed": False,
            "alpha_interpretation_allowed": False,
            "metadata": {
                "gate_currency_pair": "BTC_USDT",
                "event_time_policy": "available_at_fallback",
                "triple_barrier_directional_order_allowed": False,
                "alpha_interpretation_allowed": False,
            },
        },
    }


def test_stage1_connector_allows_cex_market_snapshot_as_observation_only(tmp_path: Path) -> None:
    input_path = tmp_path / "raw.jsonl"
    price_map = tmp_path / "price_map.json"
    output_path = tmp_path / "events.jsonl"
    input_path.write_text(json.dumps(_wrapper()) + "\n")
    price_map.write_text(json.dumps({
        "cex:BTCUSDT": {
            "price_series_id": "BTCUSDT",
            "venue": "binance",
            "timeframe": "5m",
            "mapping_type": "direct_cex_symbol",
            "active": True,
        }
    }))

    summary = run_file_backed_connector(
        input_files=[str(input_path)],
        price_map_path=str(price_map),
        output_path=str(output_path),
        source="gate_public_market_snapshot_collector",
    )

    assert summary["emitted_event_count"] == 1
    event = json.loads(output_path.read_text().splitlines()[0])
    assert event["event_type"] == "cex_market_snapshot"
    assert event["direction_hint"] == "unknown"
    assert event["shadow_only"] is True
    assert event.get("notional_usd", 0.0) == 0.0
    assert event["metadata"]["event_time_policy"] == "available_at_fallback"
    assert event["metadata"]["triple_barrier_directional_order_allowed"] is False
    assert event["metadata"]["alpha_interpretation_allowed"] is False
```

### Step 2: 跑测试确认失败

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_2_cex_market_snapshot_schema.py -q
```

Expected: FAIL，`cex_market_snapshot` unsupported 或 metadata 未保留。不要通过新增 `output_summary_path` 参数来修测试；核心 connector 只返回 summary，summary 文件写入仍由 CLI 负责。

### Step 3: 实现最小修改

Clarification: `data_quality == "api_snapshot"` does not trigger the strict manual-export provenance branch in `RawSkillPayload`. This is expected. Do not add manual provenance requirements to API snapshot payloads in this task.

Update allowed event types to include:

```python
"cex_market_snapshot"
```

Ensure emitted event metadata preserves:

```python
"triple_barrier_directional_order_allowed": False
"alpha_interpretation_allowed": False
```

Do not map it to any directional event. Do not change the `run_file_backed_connector(...)` signature unless all existing callers/tests are updated; preferred path is no signature change.

### Step 4: 跑测试确认通过

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_2_cex_market_snapshot_schema.py -q
```

Expected: PASS.

---

## Task 3：实现 Gate public collector 核心函数

**Files:**

- Create: `src/research/external_signal_shadow/gate_public_collector.py`
- Test: `tests/research/external_signal_shadow/test_gate_public_collector.py`

### Step 1: 写失败测试

Create `tests/research/external_signal_shadow/test_gate_public_collector.py`:

```python
from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from research.external_signal_shadow.gate_public_collector import (
    GateTickerResult,
    build_gate_ticker_url,
    build_raw_wrapper_from_ticker,
    normalize_gate_pair_to_symbol,
    parse_gate_ticker_payload,
    reject_private_endpoint_path,
)


def test_gate_symbol_normalization() -> None:
    assert normalize_gate_pair_to_symbol("BTC_USDT") == "BTCUSDT"
    assert normalize_gate_pair_to_symbol("BTC/USDT") == "BTCUSDT"
    assert normalize_gate_pair_to_symbol("btcusdt") == "BTCUSDT"


def test_collector_builds_public_url_only() -> None:
    url = build_gate_ticker_url("https://api.gateio.ws/api/v4", "/spot/tickers", "BTC_USDT")
    assert url == "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT"


@pytest.mark.parametrize(
    "path",
    [
        "/spot/orders",
        "/wallet/withdrawals",
        "/spot/accounts",
        "/futures/usdt/positions",
        "/margin/accounts",
        "/spot/candlesticks",
    ],
)
def test_collector_rejects_private_or_unsupported_paths(path: str) -> None:
    with pytest.raises(ValueError):
        reject_private_endpoint_path(path)


def test_parse_rejects_response_pair_mismatch() -> None:
    payload = [{
        "currency_pair": "ETH_USDT",
        "last": "100",
        "base_volume": "1",
        "quote_volume": "100",
        "change_percentage": "0",
    }]
    with pytest.raises(ValueError, match="pair mismatch"):
        parse_gate_ticker_payload(payload, "BTC_USDT")


def test_collector_preserves_numeric_raw_strings_and_parse_status() -> None:
    payload = [{
        "currency_pair": "BTC_USDT",
        "last": "65000.1",
        "base_volume": "123.45",
        "quote_volume": "8000000",
        "change_percentage": "1.23",
    }]
    result = parse_gate_ticker_payload(payload, "BTC_USDT")
    assert result.symbol == "BTCUSDT"
    assert result.metadata["last_price_raw"] == "65000.1"
    assert result.metadata["last_price_parse_ok"] is True
    assert result.metadata["quote_volume_raw"] == "8000000"
    assert result.metadata["quote_volume_parse_ok"] is True


def test_collector_tracks_numeric_parse_failures() -> None:
    payload = [{
        "currency_pair": "BTC_USDT",
        "last": "not-a-number",
        "base_volume": "123.45",
        "quote_volume": "8000000",
        "change_percentage": "1.23",
    }]
    result = parse_gate_ticker_payload(payload, "BTC_USDT")
    assert result.metadata["last_price_parse_ok"] is False
    assert result.numeric_parse_failure_count == 1


def test_collector_builds_readonly_raw_wrapper() -> None:
    result = GateTickerResult(
        gate_pair="BTC_USDT",
        symbol="BTCUSDT",
        metadata={
            "last_price_raw": "65000.1",
            "last_price_parse_ok": True,
            "base_volume_raw": "123.45",
            "base_volume_parse_ok": True,
            "quote_volume_raw": "8000000",
            "quote_volume_parse_ok": True,
            "change_percentage_raw": "1.23",
            "change_percentage_parse_ok": True,
        },
        response_field_names=("currency_pair", "last", "base_volume", "quote_volume", "change_percentage"),
        numeric_parse_failure_count=0,
    )
    wrapper = build_raw_wrapper_from_ticker(
        result,
        fetched_at_ms=1781165880123,
        collector_run_id="gate_public_market_snapshot_20260612T120000Z",
        collector_run_started_at_ms=1781165880000,
        collector_run_finished_at_ms=1781165880123,
        snapshot_sequence_id=1,
        api_status_code=200,
        api_latency_ms=123,
        api_response_hash="abc123",
        api_endpoint="/spot/tickers",
        api_query={"currency_pair": "BTC_USDT"},
        api_url="https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT",
    )

    assert wrapper["source"] == "gate_public_market_snapshot_collector"
    assert wrapper["source_capture_method"] == "public_rest_snapshot"
    assert wrapper["data_quality"] == "api_snapshot"
    assert wrapper["available_at_ms"] == 1781165880123
    assert wrapper["raw_payload"]["event_type"] == "cex_market_snapshot"
    assert wrapper["raw_payload"]["direction_hint"] == "unknown"
    assert wrapper["raw_payload"]["metadata"]["event_time_policy"] == "available_at_fallback"
    assert wrapper["raw_payload"]["metadata"]["source_url"].endswith("currency_pair=BTC_USDT")
    assert wrapper["raw_payload"]["triple_barrier_directional_order_allowed"] is False
    assert wrapper["raw_payload"]["alpha_interpretation_allowed"] is False
    assert wrapper["schedule_generated"] is True
```

### Step 2: 跑测试确认失败

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_gate_public_collector.py -q
```

Expected: FAIL，模块不存在。

### Step 3: 实现 `gate_public_collector.py`

Create `src/research/external_signal_shadow/gate_public_collector.py` with:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode


PRIVATE_PATH_MARKERS = (
    "/orders",
    "/accounts",
    "/wallet",
    "/withdraw",
    "/withdrawals",
    "/deposit",
    "/deposits",
    "/transfer",
    "/transfers",
    "/positions",
    "/position",
    "/loans",
    "/margin",
    "/sub_accounts",
)


@dataclass(frozen=True)
class GateTickerResult:
    gate_pair: str
    symbol: str
    metadata: dict[str, object]
    response_field_names: tuple[str, ...]
    numeric_parse_failure_count: int


def normalize_gate_pair_to_symbol(value: str) -> str:
    return value.replace("_", "").replace("/", "").upper()


def reject_private_endpoint_path(path: str) -> None:
    lowered = path.lower()
    if any(marker in lowered for marker in PRIVATE_PATH_MARKERS):
        raise ValueError(f"private endpoint path is not allowed: {path}")
    if lowered != "/spot/tickers":
        raise ValueError(f"unsupported public endpoint path: {path}")


def build_gate_ticker_url(base_url: str, path: str, gate_pair: str) -> str:
    reject_private_endpoint_path(path)
    return f"{base_url.rstrip('/')}{path}?{urlencode({'currency_pair': gate_pair})}"


def canonical_response_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_decimal_raw(value: object) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    raw = str(value)
    try:
        Decimal(raw)
    except InvalidOperation:
        return raw, False
    return raw, True


def parse_gate_ticker_payload(payload: object, gate_pair: str) -> GateTickerResult:
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"missing ticker payload for {gate_pair}")
    row = payload[0]
    if not isinstance(row, dict):
        raise ValueError(f"invalid ticker row for {gate_pair}")

    response_pair = str(row.get("currency_pair") or gate_pair)
    if normalize_gate_pair_to_symbol(response_pair) != normalize_gate_pair_to_symbol(gate_pair):
        raise ValueError(f"pair mismatch: requested {gate_pair}, got {response_pair}")
    symbol = normalize_gate_pair_to_symbol(response_pair)
    fields = tuple(sorted(str(key) for key in row.keys()))

    numeric_failures = 0
    metadata: dict[str, object] = {"gate_currency_pair": response_pair}
    field_map = {
        "last_price": "last",
        "base_volume": "base_volume",
        "quote_volume": "quote_volume",
        "change_percentage": "change_percentage",
    }
    for output_name, input_name in field_map.items():
        raw, ok = _parse_decimal_raw(row.get(input_name))
        metadata[f"{output_name}_raw"] = raw
        metadata[f"{output_name}_parse_ok"] = ok
        if not ok:
            numeric_failures += 1

    return GateTickerResult(
        gate_pair=gate_pair,
        symbol=symbol,
        metadata=metadata,
        response_field_names=fields,
        numeric_parse_failure_count=numeric_failures,
    )


def build_raw_wrapper_from_ticker(
    result: GateTickerResult,
    *,
    fetched_at_ms: int,
    collector_run_id: str,
    collector_run_started_at_ms: int,
    collector_run_finished_at_ms: int,
    snapshot_sequence_id: int,
    api_status_code: int,
    api_latency_ms: int,
    api_response_hash: str,
    api_endpoint: str,
    api_query: dict[str, str],
    api_url: str,
) -> dict[str, object]:
    metadata = dict(result.metadata)
    metadata["source_url"] = api_url
    return {
        "source": "gate_public_market_snapshot_collector",
        "source_vendor": "gate",
        "source_surface": "gate_api_v4_public_market_data",
        "source_capture_method": "public_rest_snapshot",
        "source_skill": "gate_public_market_snapshot_collector",
        "data_quality": "api_snapshot",
        "capture_id": collector_run_id,
        "captured_by": "script",
        "collector_run_id": collector_run_id,
        "collector_run_started_at_ms": collector_run_started_at_ms,
        "collector_run_finished_at_ms": collector_run_finished_at_ms,
        "snapshot_sequence_id": snapshot_sequence_id,
        "sampling_interval_sec": None,
        "schedule_generated": True,
        "source_observed_at_ms": fetched_at_ms,
        "fetched_at_ms": fetched_at_ms,
        "available_at_ms": fetched_at_ms,
        "api_endpoint": api_endpoint,
        "api_query": api_query,
        "api_status_code": api_status_code,
        "api_latency_ms": api_latency_ms,
        "api_response_hash": api_response_hash,
        "api_response_field_names": list(result.response_field_names),
        "field_confidence": {
            "event_time_ms": "available_at_fallback",
            "symbol": "normalized",
            "score": "missing",
        },
        "raw_payload": {
            "event_type": "cex_market_snapshot",
            "chain": "cex",
            "symbol": result.symbol,
            "event_time_ms": fetched_at_ms,
            "direction_hint": "unknown",
            "score_interpretation_allowed": False,
            "triple_barrier_directional_order_allowed": False,
            "alpha_interpretation_allowed": False,
            "metadata": {**metadata, "event_time_policy": "available_at_fallback"},
        },
    }
```

### Step 4: 跑测试确认通过

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_gate_public_collector.py -q
```

Expected: PASS.

---

## Task 4：实现 HTTP fetch 与 collector summary

**Files:**

- Modify: `src/research/external_signal_shadow/gate_public_collector.py`
- Test: `tests/research/external_signal_shadow/test_gate_public_collector_http.py`

### Step 1: 写失败测试

Create `tests/research/external_signal_shadow/test_gate_public_collector_http.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.external_signal_shadow.gate_public_collector import (
    collect_gate_public_snapshots_from_fetcher,
    write_failure_summary,
)


def _payload(pair: str) -> list[dict[str, str]]:
    return [{
        "currency_pair": pair,
        "last": "100.0",
        "base_volume": "10.0",
        "quote_volume": "1000.0",
        "change_percentage": "1.0",
    }]


def test_collect_gate_public_snapshots_writes_five_raw_payloads(tmp_path: Path) -> None:
    calls: list[str] = []

    def fetcher(url: str, timeout_sec: float, user_agent: str) -> tuple[int, object, int]:
        calls.append(url)
        pair = url.split("currency_pair=")[1]
        return 200, _payload(pair), 12

    output = tmp_path / "raw.jsonl"
    summary = collect_gate_public_snapshots_from_fetcher(
        gate_pairs=("BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT", "DOGE_USDT"),
        output_path=str(output),
        fetcher=fetcher,
        now_ms=lambda: 1781165880000,
    )

    assert len(calls) == 5
    assert output.exists()
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 5
    assert summary["collector_minimal_pass"] is True
    assert summary["http_success_count"] == 5
    assert summary["raw_payload_count"] == 5
    assert summary["api_key_used"] is False
    assert summary["private_endpoint_used"] is False
    assert summary["event_density_alpha_valid"] is False


def test_collector_writes_failure_summary_on_network_error(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.json"
    write_failure_summary(
        output_summary_path=str(summary_path),
        failure_type="collector_network_failure",
        http_success_count=0,
        http_failure_count=5,
    )
    summary = json.loads(summary_path.read_text())
    assert summary["decision"] == "external_signal_collector_stage1_2_failed"
    assert summary["failure_type"] == "collector_network_failure"
    assert summary["api_key_used"] is False
    assert summary["private_endpoint_used"] is False
    assert summary["live_safe"] is False
```

### Step 2: 跑测试确认失败

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_gate_public_collector_http.py -q
```

Expected: FAIL，函数不存在。

### Step 3: 实现 HTTP/summary helper

Add to `gate_public_collector.py`:

- `default_fetch_json(url, timeout_sec, user_agent)` using `urllib.request.Request`.
- `collect_gate_public_snapshots_from_fetcher(...)` for tests and script.
- `write_failure_summary(...)`.
- Do not read environment variables.
- Do not import SDK/ccxt.
- Do not import `os` for environment reads, dotenv, or secrets.
- Add optional `inter_request_delay_sec` from config for live calls; default 0.3 seconds to reduce 429 risk.

Summary fields must include:

```python
{
    "decision": "external_signal_collector_stage1_2_passed" or "external_signal_collector_stage1_2_failed",
    "collector_version": "stage1_2_v0",
    "source": "gate_public_market_snapshot_collector",
    "network_mode": "mock" or "live_public_readonly",
    "collector_minimal_pass": bool,
    "http_success_count": int,
    "http_failure_count": int,
    "raw_payload_count": int,
    "numeric_parse_failure_count": int,
    "numeric_parse_failure_ratio": float,
    "api_key_used": False,
    "private_endpoint_used": False,
    "event_density_alpha_valid": False,
    "schedule_generated": True,
    "live_safe": False,
}
```

### Step 4: 跑测试确认通过

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_gate_public_collector_http.py -q
```

Expected: PASS.

---

## Task 5：实现 Stage 1.2 collector CLI

**Files:**

- Create: `scripts/collect_gate_public_market_snapshot_stage1_2.py`
- Test: `tests/research/external_signal_shadow/test_gate_public_collector_cli.py`
- Fixture: `tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json`

### Step 1: 创建 mock fixture

Create `tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json`:

```json
{
  "BTC_USDT": [{"currency_pair": "BTC_USDT", "last": "65000", "base_volume": "100", "quote_volume": "6500000", "change_percentage": "1.0"}],
  "ETH_USDT": [{"currency_pair": "ETH_USDT", "last": "3500", "base_volume": "1000", "quote_volume": "3500000", "change_percentage": "0.5"}],
  "SOL_USDT": [{"currency_pair": "SOL_USDT", "last": "150", "base_volume": "20000", "quote_volume": "3000000", "change_percentage": "2.1"}],
  "XRP_USDT": [{"currency_pair": "XRP_USDT", "last": "0.6", "base_volume": "5000000", "quote_volume": "3000000", "change_percentage": "-0.3"}],
  "DOGE_USDT": [{"currency_pair": "DOGE_USDT", "last": "0.12", "base_volume": "30000000", "quote_volume": "3600000", "change_percentage": "0.9"}]
}
```

### Step 2: 写失败测试

Create `tests/research/external_signal_shadow/test_gate_public_collector_cli.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts.collect_gate_public_market_snapshot_stage1_2 import main


def test_cli_rejects_mock_and_live_flag_together(tmp_path: Path) -> None:
    output = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    result = main([
        "--mock-response",
        "tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json",
        "--live-public-readonly",
        "--output",
        str(output),
        "--output-summary",
        str(summary),
    ])
    assert result != 0
    payload = json.loads(summary.read_text())
    assert payload["failure_type"] == "conflicting_mock_and_live_public_readonly"


def test_collector_does_not_read_api_key_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GATE_API_KEY", "SHOULD_NOT_BE_USED")
    monkeypatch.setenv("GATE_SECRET", "SHOULD_NOT_BE_USED")
    output = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    result = main([
        "--mock-response",
        "tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json",
        "--output",
        str(output),
        "--output-summary",
        str(summary),
    ])
    assert result == 0
    combined = output.read_text() + summary.read_text()
    assert "SHOULD_NOT_BE_USED" not in combined
    assert json.loads(summary.read_text())["api_key_used"] is False


def test_cli_requires_live_flag_or_mock_response(tmp_path: Path) -> None:
    output = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    result = main(["--output", str(output), "--output-summary", str(summary)])
    assert result != 0
    assert summary.exists()
    payload = json.loads(summary.read_text())
    assert payload["decision"] == "external_signal_collector_stage1_2_failed"
    assert payload["failure_type"] == "missing_mock_or_live_public_readonly_flag"


def test_cli_mock_response_writes_raw_jsonl(tmp_path: Path) -> None:
    output = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    result = main([
        "--mock-response",
        "tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json",
        "--output",
        str(output),
        "--output-summary",
        str(summary),
    ])
    assert result == 0
    assert output.exists()
    assert len(output.read_text().splitlines()) == 5
    summary_payload = json.loads(summary.read_text())
    assert summary_payload["collector_minimal_pass"] is True
    assert summary_payload["network_mode"] == "mock"
    assert summary_payload["event_density_alpha_valid"] is False
```

### Step 3: 跑测试确认失败

Run:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_gate_public_collector_cli.py -q
```

Expected: FAIL，script 不存在。

### Step 4: 实现 CLI

Create `scripts/collect_gate_public_market_snapshot_stage1_2.py`.

Requirements:

- Args:
  - `--mock-response PATH`
  - `--live-public-readonly`
  - `--output PATH`
  - `--output-summary PATH`
- Without `--mock-response` and without `--live-public-readonly`: write failure summary and return 2.
- With both `--mock-response` and `--live-public-readonly`: write failure summary `conflicting_mock_and_live_public_readonly` and return 2.
- With mock response: no network.
- With live flag: call `default_fetch_json`.
- Use config constants from `configs/base.py`.
- Create parent dirs.
- Return 0 only if collector minimal pass.

### Step 5: 跑测试确认通过

Run:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_gate_public_collector_cli.py -q
```

Expected: PASS.

---

## Task 6：把 Stage 1.2 raw 接入 Stage 1 connector summary

**Files:**

- Modify: `src/research/external_signal_shadow/connector_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_2_connector_summary.py`

### Step 1: 写失败测试

Create `tests/research/external_signal_shadow/test_stage1_2_connector_summary.py`:

```python
from __future__ import annotations

from research.external_signal_shadow.connector_summary import decide_stage1_connector_summary


def test_stage1_2_summary_sets_directional_replay_ready_false() -> None:
    summary = {
        "raw_payload_count": 5,
        "emitted_event_count": 5,
        "deduped_payload_count": 0,
        "quarantined_payload_count": 0,
        "rejected_payload_count": 0,
        "summary_accounting_ok": True,
        "output_file": "events.jsonl",
        "output_file_sha256": "abc",
        "live_trading_enabled": False,
        "exchange_paper_trading_allowed": False,
        "execution_engine_allowed": False,
        "research_shadow_replay_allowed": True,
        "wallet_required": False,
        "event_type_counts": {"cex_market_snapshot": 5},
        "direction_hint_counts": {"unknown": 5},
        "price_mapping_counts": {"mapped": 5},
        "source": "gate_public_market_snapshot_collector",
    }
    decision = decide_stage1_connector_summary(summary)
    assert decision["decision"] == "external_signal_connector_stage1_passed"
    assert decision["stage0_handoff_mode"] == "observation_only"
    assert decision["stage0_directional_replay_ready"] is False
    assert decision["stage0_observation_handoff_ready"] is True
    assert decision["event_density_alpha_valid"] is False
```

### Step 2: 跑测试确认失败

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_2_connector_summary.py -q
```

Expected: FAIL，字段缺失或 decision 不含 Stage 1.2 gate。

### Step 3: 实现 summary 扩展

Update `decide_stage1_connector_summary` or equivalent to:

- Detect `source == gate_public_market_snapshot_collector`. Do not infer Stage 1.2 solely from `event_type_counts`, because that can pollute other sources that later reuse event names.
- Force:
  - `stage0_handoff_mode = observation_only`
  - `stage0_directional_replay_ready = False`
  - `stage0_observation_handoff_ready = True` if connector passed and emitted count >= 5
  - `event_density_alpha_valid = False`
  - `triple_barrier_directional_order_allowed = False`
- Never set directional replay ready for snapshot events.

### Step 4: 跑测试确认通过

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_2_connector_summary.py -q
```

Expected: PASS.

---

## Task 7：实现 Stage 1.2 review 脚本

**Files:**

- Create: `scripts/review_external_signal_shadow_stage1_2_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_2_review_script.py`

### Step 1: 写失败测试

Create `tests/research/external_signal_shadow/test_stage1_2_review_script.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts.review_external_signal_shadow_stage1_2_collector import main


def test_review_blocks_handoff_when_connector_summary_missing(tmp_path: Path) -> None:
    collector_summary = tmp_path / "collector_summary.json"
    review = tmp_path / "review_CN.md"
    collector_summary.write_text(json.dumps({
        "decision": "external_signal_collector_stage1_2_passed",
        "collector_minimal_pass": True,
    }, ensure_ascii=False))
    result = main([
        "--collector-summary", str(collector_summary),
        "--output", str(review),
    ])
    assert result != 0
    assert "connector_summary_missing" in review.read_text()


def test_stage1_2_review_script_writes_chinese_review(tmp_path: Path) -> None:
    collector_summary = tmp_path / "collector_summary.json"
    connector_summary = tmp_path / "connector_summary.json"
    review = tmp_path / "review_CN.md"
    collector_summary.write_text(json.dumps({
        "decision": "external_signal_collector_stage1_2_passed",
        "collector_minimal_pass": True,
        "connector_minimal_pass": True,
        "stage0_observation_handoff_ready": True,
        "stage0_directional_replay_ready": False,
        "event_density_alpha_valid": False,
        "http_success_count": 5,
        "http_failure_count": 0,
        "raw_payload_count": 5,
        "unique_symbol_count": 5,
        "numeric_parse_failure_count": 0,
        "api_key_used": False,
        "private_endpoint_used": False,
    }, ensure_ascii=False))
    connector_summary.write_text(json.dumps({
        "decision": "external_signal_connector_stage1_passed",
        "connector_minimal_pass": True,
        "emitted_event_count": 5,
        "unique_symbol_count": 5,
        "stage0_handoff_mode": "observation_only",
        "stage0_observation_handoff_ready": True,
        "stage0_directional_replay_ready": False,
        "event_density_alpha_valid": False,
    }, ensure_ascii=False))

    result = main([
        "--collector-summary", str(collector_summary),
        "--connector-summary", str(connector_summary),
        "--output", str(review),
    ])
    assert result == 0
    text = review.read_text()
    assert "Stage 1.2" in text
    assert "公开只读" in text
    assert "不构成 alpha" in text
    assert "directional replay 不允许" in text
```

### Step 2: 跑测试确认失败

Run:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_2_review_script.py -q
```

Expected: FAIL，script 不存在。

### Step 3: 实现 review script

Create `scripts/review_external_signal_shadow_stage1_2_collector.py`.

Review script must require two summaries:

- `--collector-summary reports/.../stage1_2_gate_public_collector_summary.json`
- `--connector-summary reports/.../stage1_2_gate_public_connector_summary.json`

If connector summary is missing, review must set:

```text
connector_minimal_pass = false
failure_type = connector_summary_missing
stage0_observation_handoff_ready = false
```

Review must include:

- 结论。
- source identity。
- collector minimal pass。
- connector minimal pass。
- Stage 0 observation handoff status。
- Safety boundary。
- Explicit warning: `cex_market_snapshot` is schedule-generated observation, not alpha event。
- Explicit warning: no paper/live/directional order。

### Step 4: 跑测试确认通过

Run:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_2_review_script.py -q
```

Expected: PASS.

---

## Task 8：端到端 mock dry run

**Files:**

- Runtime output ignored: `data/external_signal_shadow/raw/gate_public_market_snapshot_collector/2026-06-12.jsonl`
- Runtime output ignored: `data/external_signal_shadow/normalized/stage1_2_gate_public_events.jsonl`
- Runtime report: `reports/external_signal_shadow/connectors/stage1_2_gate_public_collector_summary.json`
- Docs: `docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md`

### Step 1: 运行 mock collector

Run:

```bash
PYTHONPATH=src:. uv run python scripts/collect_gate_public_market_snapshot_stage1_2.py \
  --mock-response tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json \
  --output data/external_signal_shadow/raw/gate_public_market_snapshot_collector/2026-06-12.jsonl \
  --output-summary reports/external_signal_shadow/connectors/stage1_2_gate_public_collector_summary.json
```

Expected:

- raw JSONL written.
- summary written.
- `collector_minimal_pass = true`.
- `event_density_alpha_valid = false`.

### Step 2: 运行 Stage 1 connector normalize

Use existing Stage 1 connector script. If its current name differs, inspect `scripts/` and use the actual file-backed connector script. Expected command shape:

```bash
PYTHONPATH=src:. uv run python scripts/run_external_signal_shadow_stage1_connector.py \
  --input data/external_signal_shadow/raw/gate_public_market_snapshot_collector/2026-06-12.jsonl \
  --price-map configs/external_signal_shadow_price_map.json \
  --output data/external_signal_shadow/normalized/stage1_2_gate_public_events.jsonl \
  --output-summary reports/external_signal_shadow/connectors/stage1_2_gate_public_connector_summary.json \
  --source gate_public_market_snapshot_collector
```

Expected:

- normalized JSONL written.
- connector summary shows `external_signal_connector_stage1_passed`.
- `stage0_handoff_mode = observation_only`.
- `stage0_directional_replay_ready = false`.

### Step 3: 合并 collector + connector summary if needed

Review must consume both collector summary and connector summary. Collector-only summary is not sufficient for end-to-end pass. Do not fake connector pass in collector-only summary.

### Step 4: 生成中文 review

Run:

```bash
PYTHONPATH=src:. uv run python scripts/review_external_signal_shadow_stage1_2_collector.py \
  --collector-summary reports/external_signal_shadow/connectors/stage1_2_gate_public_collector_summary.json \
  --connector-summary reports/external_signal_shadow/connectors/stage1_2_gate_public_connector_summary.json \
  --output docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md
```

Expected: Chinese review written.

---

## Task 9：真实公开只读 dry run

**Files:**

- Runtime output ignored: `data/external_signal_shadow/raw/gate_public_market_snapshot_collector/YYYY-MM-DD.jsonl`
- Runtime report: `reports/external_signal_shadow/connectors/stage1_2_gate_public_collector_summary.json`
- Docs: `docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md`

### Step 1: 显式运行 live public readonly collector

Run only after mock E2E passes:

```bash
PYTHONPATH=src:. uv run python scripts/collect_gate_public_market_snapshot_stage1_2.py \
  --live-public-readonly \
  --output data/external_signal_shadow/raw/gate_public_market_snapshot_collector/2026-06-12.jsonl \
  --output-summary reports/external_signal_shadow/connectors/stage1_2_gate_public_collector_summary.json
```

Expected:

- network mode = `live_public_readonly`.
- `api_key_used = false`.
- `private_endpoint_used = false`.
- 5 public ticker payloads or safe failure summary.

### Step 2: 如果 live call 失败

Do not retry aggressively. Keep failure summary and review it.

Expected failure summary examples:

```json
{
  "decision": "external_signal_collector_stage1_2_failed",
  "failure_type": "collector_network_failure",
  "http_success_count": 0,
  "http_failure_count": 5,
  "api_key_used": false,
  "private_endpoint_used": false,
  "live_safe": false
}
```

### Step 3: 如果 live call 成功

Run Stage 1 connector and review as in Task 8.

---

## Task 10：Focused tests 与 lint

Run:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_gate_public_collector_config.py \
  tests/research/external_signal_shadow/test_stage1_2_cex_market_snapshot_schema.py \
  tests/research/external_signal_shadow/test_gate_public_collector.py \
  tests/research/external_signal_shadow/test_gate_public_collector_http.py \
  tests/research/external_signal_shadow/test_gate_public_collector_cli.py \
  tests/research/external_signal_shadow/test_stage1_2_connector_summary.py \
  tests/research/external_signal_shadow/test_stage1_2_review_script.py \
  -q
```

Expected: all pass.

Run external signal suite:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow -q
```

Expected: all pass.

Run static secret/env read check:

```bash
grep -R "os.environ\|dotenv\|GATE_API_KEY\|GATE_SECRET\|apiKey\|secret" \
  src/research/external_signal_shadow/gate_public_collector.py \
  scripts/collect_gate_public_market_snapshot_stage1_2.py && exit 1 || true
```

Expected: no matches.

Run scoped ruff:

```bash
uv run ruff check \
  src/research/external_signal_shadow \
  scripts/collect_gate_public_market_snapshot_stage1_2.py \
  scripts/review_external_signal_shadow_stage1_2_collector.py \
  tests/research/external_signal_shadow
```

Expected: no errors.

---

## Task 11：全量验证

Run:

```bash
PYTHONPATH=src:. uv run pytest -q
```

Expected: all tests pass.

If full suite is too slow or environment-dependent, record exact failure and run focused suites. Do not claim full verification if not run.

---

## Task 12：最终自查

Check git status:

```bash
git status --short
```

Expected tracked/untracked changes limited to:

- `configs/base.py`
- `.gitignore` if needed
- `src/research/external_signal_shadow/gate_public_collector.py`
- `src/research/external_signal_shadow/schemas.py` or connector whitelist file
- `src/research/external_signal_shadow/connector_summary.py`
- `scripts/collect_gate_public_market_snapshot_stage1_2.py`
- `scripts/review_external_signal_shadow_stage1_2_collector.py`
- `tests/research/external_signal_shadow/...`
- `tests/fixtures/external_signal_shadow/stage1_2_gate_tickers_mock.json`
- `reports/external_signal_shadow/connectors/stage1_2_gate_public_collector_summary.json` if fixture/mock summary is intended for commit
- `docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md`

Ensure ignored runtime data is not staged:

```bash
git status --short data/external_signal_shadow/raw data/external_signal_shadow/normalized
```

Expected: no output.

---

## Completion Criteria

Implementation is complete only if:

- `cex_market_snapshot` is accepted as observation-only.
- No directional shadow order can be generated from `cex_market_snapshot`.
- collector uses per-symbol public REST URL only.
- real network call requires `--live-public-readonly`.
- no SDK, ccxt, env secret, `.env`, private endpoint, account endpoint, or execution path is used.
- static grep confirms no `os.environ`, dotenv, `GATE_API_KEY`, `GATE_SECRET`, `apiKey`, or secret read path.
- review requires both collector summary and connector summary before handoff-ready conclusion.
- failure summary is written on network/rate-limit/parse failure.
- mock E2E passes.
- live public readonly dry run either passes or writes safe failure summary.
- Chinese review explicitly says this is not alpha, not paper, not live.
- focused tests pass.
- external signal test suite passes.
- full pytest is run, or any inability to run it is explicitly reported.

