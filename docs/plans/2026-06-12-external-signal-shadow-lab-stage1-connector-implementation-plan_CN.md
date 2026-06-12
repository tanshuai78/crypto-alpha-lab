# External Signal Shadow Lab Stage 1 Connector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Stage 1.0 fixture-only, file-backed external signal connector that converts raw skill/web/API payload JSONL into safe `ExternalSignalEvent`-compatible JSONL for Stage 0 shadow replay.

**Architecture:** Add connector-only research modules under `src/research/external_signal_shadow/`. The connector reads local raw payload fixtures, applies safety validation, time-availability checks, semantic deduplication, price mapping, quarantine/reject accounting, and writes normalized events plus a connector summary. Stage 1.0 does not call external APIs, does not use wallets, does not produce orders, and does not touch strategy/execution/risk modules.

**Tech Stack:** Python standard library, dataclasses, JSONL, SHA-256, pytest, existing `configs/base.py`, existing Stage 0 `ExternalSignalEvent` schema and Stage 0 replay script.

---

## 0. Non-Negotiable Boundaries

This plan implements Stage 1.0 only.

Do not implement:

- direct HTTP connector;
- browser scraping;
- wallet login;
- API key handling;
- exchange paper trading;
- CEX/DEX order placement;
- transaction signing;
- swap;
- copy-trading;
- ML model;
- parameter optimization;
- strategy module;
- execution module;
- live/paper trading adapter.

Do not modify these directories:

```text
src/strategies/
src/execution/
src/risk/
```

Allowed source directory:

```text
src/research/external_signal_shadow/
```

Implementation may mention commit checkpoints, but in this project **do not commit automatically unless the user explicitly asks**.

---

## 1. Stage 1.0 Required Semantics

The connector must enforce these semantics:

```text
raw payload event_time_ms = when the external event allegedly happened
fetched_at_ms / available_at_ms = when our system could know it existed
Stage 0 replay anchor = available_at_ms
```

Look-ahead prevention rule:

```text
available_at_ms < event_time_ms -> reject
source_latency_ms = available_at_ms - event_time_ms
source_latency_ms above threshold -> quarantine
```

Output event handoff rule:

```text
normalized ExternalSignalEvent.event_time_ms = available_at_ms
metadata.original_event_time_ms = original event_time_ms
metadata.available_at_ms = available_at_ms
metadata.source_latency_ms = source_latency_ms
```

This avoids changing Stage 0 while guaranteeing replay does not start before the signal was available.

---

## 1.1 Required Fixes Incorporated Before Coding

This plan incorporates the required review fixes before any implementation starts:

- Verify import convention first. This repository currently uses `src.research.*` imports in existing Stage 0 code and tests, so Stage 1.0 must use the same convention unless Task 0 proves otherwise.
- `shadow_only = true` must be asserted on every normalized event.
- Normalized events must not contain executable fields such as order, swap, wallet, or raw payload content.
- `RawSkillPayload` must include `data_quality` so latency policy is explicit rather than inferred from `source`.
- Summary decision must prioritize `safety_failure` before data/schema failures.
- CLI `--source` and wrapper `source` must match; mismatches are rejected as `source_mismatch`.
- `.gitignore` must exclude runtime raw/normalized external signal data.
- Connector classification precedence must be fixed before implementation so fixture counts do not drift between agents.

Classification precedence:

```text
1. parse_error -> rejected
2. source_mismatch -> rejected
3. forbidden_executable_payload -> rejected
4. required wrapper/schema invalid -> rejected or quarantined by explicit reason
5. available_at_ms < event_time_ms -> rejected
6. unsupported_event_type -> rejected
7. missing chain / missing asset -> quarantined
8. stale latency -> quarantined
9. price_mapping_unavailable -> quarantined
10. semantic duplicate -> deduped
11. emitted
```

Important: dedup runs after safety, schema, latency, and price mapping checks. An illegal duplicate must still be rejected or quarantined; dedup must not hide invalid payloads.

---

## 2. Expected Output Artifacts

Create source files:

```text
src/research/external_signal_shadow/safety.py
src/research/external_signal_shadow/price_mapping.py
src/research/external_signal_shadow/schemas.py
src/research/external_signal_shadow/file_backed_connector.py
src/research/external_signal_shadow/connector_summary.py
```

Create scripts:

```text
scripts/run_external_signal_shadow_stage1_connector.py
scripts/review_external_signal_shadow_stage1_connector.py
```

Create configs / fixtures:

```text
configs/external_signal_shadow_price_map.json
tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl
tests/fixtures/external_signal_shadow/stage1_price_map.json
```

Modify repo ignore policy:

```text
.gitignore
```

Create tests:

```text
tests/research/test_external_signal_shadow_stage1_safety.py
tests/research/test_external_signal_shadow_stage1_price_mapping.py
tests/research/test_external_signal_shadow_stage1_connector.py
tests/research/test_external_signal_shadow_stage1_summary.py
tests/scripts/test_run_external_signal_shadow_stage1_connector.py
tests/scripts/test_review_external_signal_shadow_stage1_connector.py
```

Create runtime outputs when script is run:

```text
data/external_signal_shadow/normalized/stage1_events.jsonl
reports/external_signal_shadow/connectors/stage1_connector_summary.json
docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-connector-review_CN.md
```

---

## 3. Config Constants

### Task 0: Verify import convention and existing Stage 0 helpers

**Files:**

- No file edits.

**Step 1: Run import convention probe**

```bash
PYTHONPATH=src uv run python - <<'PY'
import importlib

candidates = [
    "research.external_signal_shadow.models",
    "src.research.external_signal_shadow.models",
]

for name in candidates:
    try:
        importlib.import_module(name)
        print(f"IMPORT_OK {name}")
    except Exception as exc:
        print(f"IMPORT_FAIL {name}: {type(exc).__name__}: {exc}")
PY
```

Expected in the current repository:

```text
IMPORT_OK research.external_signal_shadow.models
IMPORT_OK src.research.external_signal_shadow.models
```

**Step 2: Choose import convention**

Use the existing repository convention:

```python
from src.research.external_signal_shadow...
```

Reason: existing Stage 0 code and tests already use `src.research.*`. Do not mix `research.*` and `src.research.*` in new Stage 1 files.

**Step 3: Verify existing Stage 0 helper availability**

```bash
grep -n "def normalize_symbol" src/research/external_signal_shadow/models.py
```

Expected: helper exists. However, Stage 1 `price_mapping.py` should still define a small local `_normalize_symbol()` to avoid coupling price mapping to Stage 0 internals.

---

### Task 1: Add Stage 1 connector constants

**Files:**

- Modify: `configs/base.py`
- Test: `tests/research/test_external_signal_shadow_stage1_connector.py`

**Step 1: Write failing config test**

Create `tests/research/test_external_signal_shadow_stage1_connector.py` with:

```python
def test_external_signal_stage1_connector_config_constants_exist():
    from configs import base

    assert base.EXTERNAL_SIGNAL_CONNECTOR_EVENT_TIME_BUCKET_MS == 5 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_CONNECTOR_MAX_CEX_LATENCY_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_CONNECTOR_MAX_ONCHAIN_LATENCY_MS == 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_CONNECTOR_MAX_MANUAL_FIXTURE_LATENCY_MS == 24 * 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_CONNECTOR_VERSION == "stage1_v0"
    assert base.EXTERNAL_SIGNAL_CONNECTOR_SCHEMA_VERSION == "external_signal_event_v1"
```

**Step 2: Run failing test**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_connector.py::test_external_signal_stage1_connector_config_constants_exist -q
```

Expected: fail because constants do not exist.

**Step 3: Implement constants**

Append after the Stage 0 external signal constants in `configs/base.py`:

```python
# ─── Research: External Signal Shadow Lab Stage 1 Connector ──────────────────

EXTERNAL_SIGNAL_CONNECTOR_EVENT_TIME_BUCKET_MS = 5 * 60 * 1000
# Semantic dedup bucket width. Prevents repeated website/API refreshes from inflating event density.

EXTERNAL_SIGNAL_CONNECTOR_MAX_CEX_LATENCY_MS = 15 * 60 * 1000
# Maximum allowed latency for CEX / market rank payloads.

EXTERNAL_SIGNAL_CONNECTOR_MAX_ONCHAIN_LATENCY_MS = 60 * 60 * 1000
# Maximum allowed latency for on-chain / audit / holder payloads.

EXTERNAL_SIGNAL_CONNECTOR_MAX_MANUAL_FIXTURE_LATENCY_MS = 24 * 60 * 60 * 1000
# Maximum allowed latency for manual fixture payloads. Not alpha-valid.

EXTERNAL_SIGNAL_CONNECTOR_VERSION = "stage1_v0"
# Connector version written into normalized event metadata and summaries.

EXTERNAL_SIGNAL_CONNECTOR_SCHEMA_VERSION = "external_signal_event_v1"
# ExternalSignalEvent-compatible output schema version.
```

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_connector.py::test_external_signal_stage1_connector_config_constants_exist -q
```

Expected: pass.

---

### Task 1.1: Update `.gitignore` for runtime external signal data

**Files:**

- Modify: `.gitignore`

**Step 1: Inspect existing ignore rules**

```bash
grep -n "external_signal_shadow\\|data/" .gitignore || true
```

**Step 2: Add runtime data ignore rules if missing**

Append:

```gitignore
# External Signal Shadow Lab runtime data
data/external_signal_shadow/raw/
data/external_signal_shadow/normalized/
```

Do not ignore:

```text
tests/fixtures/external_signal_shadow/
reports/external_signal_shadow/connectors/stage1_connector_fixture_summary.json
docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-connector-review_CN.md
```

**Step 3: Verify ignore behavior**

```bash
git check-ignore data/external_signal_shadow/raw/example.jsonl
git check-ignore data/external_signal_shadow/normalized/stage1_events.jsonl
```

Expected: both paths are ignored.

---

## 4. Safety and Hashing Utilities

### Task 2: Implement canonical hash and forbidden payload policy

**Files:**

- Create: `src/research/external_signal_shadow/safety.py`
- Test: `tests/research/test_external_signal_shadow_stage1_safety.py`

**Step 1: Write failing tests**

Create `tests/research/test_external_signal_shadow_stage1_safety.py`:

```python
import pytest


def test_canonical_json_hash_ignores_dict_order_and_fetched_at_wrapper():
    from src.research.external_signal_shadow.safety import canonical_json_hash

    left = {"b": 2, "a": {"z": 1, "y": 2}}
    right = {"a": {"y": 2, "z": 1}, "b": 2}

    assert canonical_json_hash(left) == canonical_json_hash(right)


def test_canonical_json_hash_does_not_include_fetched_at_when_hashing_raw_payload():
    from src.research.external_signal_shadow.safety import canonical_json_hash

    raw_payload = {"token": "ABC", "score": 1.0}
    wrapper_1 = {"fetched_at_ms": 1000, "raw_payload": raw_payload}
    wrapper_2 = {"fetched_at_ms": 2000, "raw_payload": raw_payload}

    assert canonical_json_hash(wrapper_1["raw_payload"]) == canonical_json_hash(wrapper_2["raw_payload"])


def test_forbidden_policy_rejects_exact_secret_keys():
    from src.research.external_signal_shadow.safety import validate_no_executable_payload

    with pytest.raises(ValueError, match="private_key"):
        validate_no_executable_payload({"safe": {"private_key": "0xdead"}})


def test_forbidden_policy_rejects_path_patterns():
    from src.research.external_signal_shadow.safety import validate_no_executable_payload

    with pytest.raises(ValueError, match="swap.calldata"):
        validate_no_executable_payload({"swap": {"calldata": "0xabc"}})


def test_forbidden_policy_allows_analytics_keys():
    from src.research.external_signal_shadow.safety import validate_no_executable_payload

    validate_no_executable_payload(
        {
            "tx_count": 12,
            "tx_hash": "0xabc",
            "swap_count_24h": 7,
            "orderbook_imbalance": 0.12,
            "orderbook_depth_usd": 1_000_000,
        }
    )
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_safety.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement `safety.py`**

Create `src/research/external_signal_shadow/safety.py`:

```python
import hashlib
import json
from typing import Any

HARD_REJECT_EXACT_KEYS = {
    "private_key",
    "seed",
    "mnemonic",
    "signature",
    "signed_tx",
    "raw_tx",
    "api_key",
    "secret",
    "password",
    "passphrase",
    "order_request",
    "swap_request",
    "transfer_request",
    "wallet_seed",
    "wallet_private_key",
    "tx_payload",
}

HARD_REJECT_PATH_PATTERNS = {
    "wallet.private_key",
    "wallet.seed",
    "transaction.signed_payload",
    "transaction.raw_tx",
    "order.intent",
    "order.request",
    "swap.calldata",
    "swap.request",
    "transfer.request",
}

ALLOWED_ANALYTICS_KEYS = {
    "tx_count",
    "tx_hash",
    "swap_count_24h",
    "orderbook_imbalance",
    "orderbook_depth_usd",
}


def canonical_json_dumps(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_json_hash(payload: object) -> str:
    return hashlib.sha256(canonical_json_dumps(payload).encode("utf-8")).hexdigest()


def validate_no_executable_payload(payload: object) -> None:
    _walk(payload, path=())


def _walk(value: object, path: tuple[str, ...]) -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key).lower()
            child_path = (*path, key)
            dotted = ".".join(child_path)
            if key in HARD_REJECT_EXACT_KEYS and key not in ALLOWED_ANALYTICS_KEYS:
                raise ValueError(f"forbidden executable field: {dotted}")
            if dotted in HARD_REJECT_PATH_PATTERNS:
                raise ValueError(f"forbidden executable field: {dotted}")
            _walk(child, child_path)
    elif isinstance(value, list | tuple):
        for item in value:
            _walk(item, path)
```

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_safety.py -q
```

Expected: pass.

---

## 5. Price Mapping

### Task 3: Add explicit price mapping artifact and loader

**Files:**

- Create: `configs/external_signal_shadow_price_map.json`
- Create: `tests/fixtures/external_signal_shadow/stage1_price_map.json`
- Create: `src/research/external_signal_shadow/price_mapping.py`
- Test: `tests/research/test_external_signal_shadow_stage1_price_mapping.py`

**Step 1: Write failing tests**

Create `tests/research/test_external_signal_shadow_stage1_price_mapping.py`:

```python
import json


def test_price_mapping_loads_direct_cex_symbol(tmp_path):
    from src.research.external_signal_shadow.price_mapping import load_price_map, resolve_price_mapping

    path = tmp_path / "price_map.json"
    path.write_text(json.dumps({"cex:BTCUSDT": {"price_series_id": "BTCUSDT", "venue": "binance", "timeframe": "5m", "mapping_type": "direct_cex_symbol", "active": True}}))

    price_map = load_price_map(str(path))
    mapping = resolve_price_mapping(price_map, chain="cex", symbol="BTC/USDT", token_address=None)

    assert mapping.price_series_id == "BTCUSDT"
    assert mapping.mapping_type == "direct_cex_symbol"


def test_price_mapping_loads_token_proxy(tmp_path):
    from src.research.external_signal_shadow.price_mapping import load_price_map, resolve_price_mapping

    path = tmp_path / "price_map.json"
    path.write_text(json.dumps({"bsc:0xabc": {"price_series_id": "ABCUSDT", "venue": "binance", "timeframe": "5m", "mapping_type": "cex_symbol_proxy", "active": True}}))

    price_map = load_price_map(str(path))
    mapping = resolve_price_mapping(price_map, chain="bsc", symbol=None, token_address="0xABC")

    assert mapping.price_series_id == "ABCUSDT"


def test_price_mapping_unavailable_returns_none(tmp_path):
    from src.research.external_signal_shadow.price_mapping import load_price_map, resolve_price_mapping

    path = tmp_path / "price_map.json"
    path.write_text("{}")

    price_map = load_price_map(str(path))

    assert resolve_price_mapping(price_map, chain="bsc", symbol=None, token_address="0xmissing") is None


def test_price_mapping_ignores_inactive_entries(tmp_path):
    from src.research.external_signal_shadow.price_mapping import load_price_map, resolve_price_mapping

    path = tmp_path / "price_map.json"
    path.write_text(json.dumps({"cex:ETHUSDT": {"price_series_id": "ETHUSDT", "venue": "binance", "timeframe": "5m", "mapping_type": "direct_cex_symbol", "active": False}}))

    price_map = load_price_map(str(path))

    assert resolve_price_mapping(price_map, chain="cex", symbol="ETHUSDT", token_address=None) is None
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_price_mapping.py -q
```

Expected: fail because module does not exist.

**Step 3: Add fixture price map**

Create `tests/fixtures/external_signal_shadow/stage1_price_map.json`:

```json
{
  "cex:BTCUSDT": {
    "price_series_id": "BTCUSDT",
    "venue": "binance",
    "timeframe": "5m",
    "mapping_type": "direct_cex_symbol",
    "active": true
  },
  "cex:ETHUSDT": {
    "price_series_id": "ETHUSDT",
    "venue": "binance",
    "timeframe": "5m",
    "mapping_type": "direct_cex_symbol",
    "active": true
  },
  "bsc:0xabc": {
    "price_series_id": "ABCUSDT",
    "venue": "binance",
    "timeframe": "5m",
    "mapping_type": "cex_symbol_proxy",
    "active": true
  }
}
```

Create `configs/external_signal_shadow_price_map.json` with an empty object and comment-free JSON:

```json
{}
```

The real config artifact exists, but Stage 1.0 tests should use the fixture map.

**Step 4: Implement `price_mapping.py`**

Create `src/research/external_signal_shadow/price_mapping.py`:

```python
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PriceMapping:
    price_series_id: str
    venue: str
    timeframe: str
    mapping_type: str
    active: bool


def load_price_map(path: str) -> dict[str, PriceMapping]:
    payload = json.loads(Path(path).read_text())
    return {key.lower(): PriceMapping(**value) for key, value in payload.items()}


def _normalize_symbol(symbol: str | None) -> str | None:
    if symbol is None:
        return None
    normalized = symbol.replace("/", "").replace("-", "").replace("_", "").upper()
    return normalized or None


def canonical_asset_id(chain: str, symbol: str | None, token_address: str | None) -> str | None:
    normalized_chain = chain.lower()
    if normalized_chain == "cex":
        normalized_symbol = _normalize_symbol(symbol)
        return f"cex:{normalized_symbol}" if normalized_symbol else None
    if token_address:
        return f"{normalized_chain}:{token_address.lower()}"
    return None


def resolve_price_mapping(
    price_map: dict[str, PriceMapping],
    *,
    chain: str,
    symbol: str | None,
    token_address: str | None,
) -> PriceMapping | None:
    key = canonical_asset_id(chain, symbol, token_address)
    if key is None:
        return None
    mapping = price_map.get(key.lower())
    if mapping is None or not mapping.active:
        return None
    return mapping
```

**Step 5: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_price_mapping.py -q
```

Expected: pass.

---

## 6. Stage 1 Schemas

### Task 4: Add raw payload and connector item models

**Files:**

- Create: `src/research/external_signal_shadow/schemas.py`
- Test: `tests/research/test_external_signal_shadow_stage1_connector.py`

**Step 1: Add failing schema tests**

Append to `tests/research/test_external_signal_shadow_stage1_connector.py`:

```python
import pytest


def test_raw_skill_payload_requires_raw_payload_dict():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    with pytest.raises(ValueError, match="raw_payload"):
        RawSkillPayload.from_dict({"source": "fixture", "data_quality": "fixture", "source_skill": "fixture", "fetched_at_ms": 1000, "raw_payload": []})


def test_raw_skill_payload_defaults_available_at_to_fetched_at():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = RawSkillPayload.from_dict(
        {
            "source": "fixture",
            "source_skill": "fixture",
            "fetched_at_ms": 2000,
            "raw_payload": {"event_time_ms": 1000},
        }
    )

    assert payload.available_at_ms == 2000


def test_raw_skill_payload_has_explicit_data_quality_default():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = RawSkillPayload.from_dict(
        {
            "source": "fixture",
            "source_skill": "fixture",
            "fetched_at_ms": 2000,
            "raw_payload": {"event_time_ms": 1000},
        }
    )

    assert payload.data_quality == "unknown"
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_connector.py::test_raw_skill_payload_requires_raw_payload_dict tests/research/test_external_signal_shadow_stage1_connector.py::test_raw_skill_payload_defaults_available_at_to_fetched_at tests/research/test_external_signal_shadow_stage1_connector.py::test_raw_skill_payload_has_explicit_data_quality_default -q
```

Expected: fail because module does not exist.

**Step 3: Implement `schemas.py`**

Create `src/research/external_signal_shadow/schemas.py`:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawSkillPayload:
    source: str
    source_skill: str
    fetched_at_ms: int
    raw_payload: dict[str, Any]
    available_at_ms: int | None = None
    data_quality: str = "unknown"

    def __post_init__(self) -> None:
        if not isinstance(self.fetched_at_ms, int):
            raise ValueError("fetched_at_ms must be an integer Unix ms timestamp")
        if self.available_at_ms is not None and not isinstance(self.available_at_ms, int):
            raise ValueError("available_at_ms must be an integer Unix ms timestamp")
        if not isinstance(self.raw_payload, dict):
            raise ValueError("raw_payload must be a dict")
        if self.available_at_ms is None:
            object.__setattr__(self, "available_at_ms", self.fetched_at_ms)
        object.__setattr__(self, "data_quality", self.data_quality.lower())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RawSkillPayload":
        return cls(**payload)


@dataclass(frozen=True)
class ConnectorRecord:
    status: str
    raw_payload_hash: str | None = None
    event: dict[str, Any] | None = None
    reject_reasons: tuple[str, ...] = field(default_factory=tuple)
    quarantine_reasons: tuple[str, ...] = field(default_factory=tuple)
```

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_connector.py::test_raw_skill_payload_requires_raw_payload_dict tests/research/test_external_signal_shadow_stage1_connector.py::test_raw_skill_payload_defaults_available_at_to_fetched_at -q
```

Expected: pass.

---

## 7. File-Backed Connector Core

### Task 5: Implement normalization, dedup, latency, mapping, reject/quarantine

**Files:**

- Create: `src/research/external_signal_shadow/file_backed_connector.py`
- Test: `tests/research/test_external_signal_shadow_stage1_connector.py`

**Step 1: Add fixture payloads**

Create `tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl` with 11 payloads covering required paths:

```jsonl
{"source":"fixture","data_quality":"fixture","source_skill":"smart_money","fetched_at_ms":1700000060000,"raw_payload":{"event_type":"smart_money_inflow","chain":"cex","symbol":"BTC/USDT","event_time_ms":1700000000000,"score":90.0,"liquidity_usd":10000000.0,"metadata":{"spread_bps":2.0}}}
{"source":"fixture","data_quality":"fixture","source_skill":"token_audit","fetched_at_ms":1700000060000,"raw_payload":{"event_type":"token_audit_pass","chain":"bsc","token_address":"0xabc","event_time_ms":1700000000000,"score":70.0,"liquidity_usd":1200000.0}}
{"source":"fixture","data_quality":"fixture","source_skill":"smart_money","fetched_at_ms":1700000120000,"raw_payload":{"event_type":"smart_money_inflow","chain":"cex","symbol":"BTC/USDT","event_time_ms":1700000000000,"score":91.0,"liquidity_usd":10000000.0,"metadata":{"rank":1}}}
{"source":"fixture","data_quality":"fixture","source_skill":"unknown","fetched_at_ms":1700000060000,"raw_payload":{"event_type":"unsupported_alpha_magic","chain":"cex","symbol":"ETHUSDT","event_time_ms":1700000000000}}
{"source":"fixture","data_quality":"fixture","source_skill":"security","fetched_at_ms":1700000060000,"raw_payload":{"event_type":"smart_money_inflow","chain":"cex","symbol":"ETHUSDT","event_time_ms":1700000000000,"wallet":{"private_key":"0xdead"}}}
{"source":"fixture","data_quality":"fixture","source_skill":"bad","fetched_at_ms":1700000060000,"raw_payload":{"event_type":"smart_money_inflow","symbol":"ETHUSDT","event_time_ms":1700000000000}}
{"source":"fixture","data_quality":"fixture","source_skill":"bad","fetched_at_ms":1700000060000,"raw_payload":{"event_type":"smart_money_inflow","chain":"cex","event_time_ms":1700000000000}}
{"source":"fixture","data_quality":"fixture","source_skill":"token","fetched_at_ms":1700000060000,"raw_payload":{"event_type":"smart_money_inflow","chain":"bsc","token_address":"0xmissing","event_time_ms":1700000000000,"liquidity_usd":1000000.0}}
{"source":"fixture","data_quality":"fixture","source_skill":"stale","fetched_at_ms":1700090000000,"raw_payload":{"event_type":"smart_money_inflow","chain":"cex","symbol":"ETHUSDT","event_time_ms":1700000000000}}
{"source":"fixture","data_quality":"fixture","source_skill":"bad_time","fetched_at_ms":1699999999000,"raw_payload":{"event_type":"smart_money_inflow","chain":"cex","symbol":"ETHUSDT","event_time_ms":1700000000000}}
{"source":"fixture","data_quality":"fixture","source_skill":"bad_metadata","fetched_at_ms":1700000060000,"raw_payload":{"event_type":"smart_money_inflow","chain":"cex","symbol":"ETHUSDT","event_time_ms":1700000000000,"metadata":{"raw_payload":{"unsafe":"should_not_be_embedded"}}}}
```

**Step 2: Write failing connector tests**

Append to `tests/research/test_external_signal_shadow_stage1_connector.py`:

```python
import json
from pathlib import Path


def test_file_backed_connector_fixture_accounting(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    assert summary["raw_payload_count"] == 11
    assert summary["summary_accounting_ok"] is True
    assert summary["raw_payload_count"] == (
        summary["emitted_event_count"]
        + summary["deduped_payload_count"]
        + summary["quarantined_payload_count"]
        + summary["rejected_payload_count"]
    )
    assert summary["emitted_event_count"] == 2
    assert summary["deduped_payload_count"] == 1
    assert summary["quarantined_payload_count"] >= 4
    assert summary["rejected_payload_count"] >= 3
    assert output.exists()


def test_connector_rejects_forbidden_nested_keys(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(tmp_path / "events.jsonl"),
        source="fixture",
    )

    assert summary["reject_reason_counts"]["forbidden_executable_payload"] == 1


def test_connector_dedupes_semantic_duplicate(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(tmp_path / "events.jsonl"),
        source="fixture",
    )

    assert summary["deduped_payload_count"] == 1


def test_connector_quarantines_missing_price_mapping(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(tmp_path / "events.jsonl"),
        source="fixture",
    )

    assert summary["quarantine_reason_counts"]["price_mapping_unavailable"] == 1


def test_connector_uses_available_at_for_replay_handoff(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    events = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
    assert events
    for event in events:
        assert event["event_time_ms"] == event["metadata"]["available_at_ms"]
        assert event["metadata"]["available_at_ms"] >= event["metadata"]["original_event_time_ms"]
        assert event["metadata"]["source_latency_ms"] >= 0


def test_normalized_events_are_shadow_only_and_non_executable(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    events = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
    assert events
    for event in events:
        assert event["shadow_only"] is True
        assert event.get("notional_usd", 0.0) == 0.0
        assert "order" not in event
        assert "swap" not in event
        assert "wallet" not in event
        assert "raw_payload" not in event.get("metadata", {})


def test_connector_rejects_source_mismatch(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    payload = {
        "source": "binance_web3",
        "source_skill": "smart_money",
        "fetched_at_ms": 1700000060000,
        "raw_payload": {
            "event_type": "smart_money_inflow",
            "chain": "cex",
            "symbol": "BTCUSDT",
            "event_time_ms": 1700000000000,
        },
    }
    input_path = tmp_path / "payloads.jsonl"
    input_path.write_text(json.dumps(payload) + "\n")

    summary = run_file_backed_connector(
        input_files=[str(input_path)],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(tmp_path / "events.jsonl"),
        source="fixture",
    )

    assert summary["reject_reason_counts"]["source_mismatch"] == 1


def test_event_id_is_stable_across_repeated_runs(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    kwargs = {
        "input_files": ["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        "price_map_path": "tests/fixtures/external_signal_shadow/stage1_price_map.json",
        "source": "fixture",
    }
    run_file_backed_connector(output_path=str(first), **kwargs)
    run_file_backed_connector(output_path=str(second), **kwargs)

    assert first.read_text() == second.read_text()


def test_connector_does_not_write_raw_payload_to_metadata(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    events = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
    assert events
    assert all("raw_payload" not in event["metadata"] for event in events)


def test_normalized_events_are_stage0_compatible(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector
    from src.research.external_signal_shadow.models import load_events_jsonl

    output = tmp_path / "events.jsonl"
    run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="fixture",
    )

    events = load_events_jsonl(str(output))
    assert len(events) == 2
```

**Step 3: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_connector.py -q
```

Expected: fail because `file_backed_connector.py` does not exist.

**Step 4: Implement minimal connector**

Create `src/research/external_signal_shadow/file_backed_connector.py`.

Required functions:

```python
def run_file_backed_connector(
    *,
    input_files: list[str],
    price_map_path: str,
    output_path: str,
    source: str,
) -> dict: ...
```

Implementation requirements:

- Load JSONL lines as `RawSkillPayload`.
- Reject wrapper/source mismatch: `wrapper.source != source` -> `source_mismatch`.
- Validate raw payload with `validate_no_executable_payload`.
- Compute `raw_payload_hash = canonical_json_hash(raw_payload)`.
- Extract `event_type`, `chain`, `symbol`, `token_address`, `event_time_ms`, `available_at_ms`.
- Use `available_at_ms = wrapper.available_at_ms or wrapper.fetched_at_ms`.
- Reject if `available_at_ms < event_time_ms`.
- Quarantine if latency exceeds threshold:
  - `wrapper.data_quality == "fixture"`: `EXTERNAL_SIGNAL_CONNECTOR_MAX_MANUAL_FIXTURE_LATENCY_MS`
  - `chain == "cex"`: `EXTERNAL_SIGNAL_CONNECTOR_MAX_CEX_LATENCY_MS`
  - otherwise: `EXTERNAL_SIGNAL_CONNECTOR_MAX_ONCHAIN_LATENCY_MS`
- Reject unsupported event types.
- Quarantine missing chain / missing asset / missing price mapping.
- Reject if raw payload tries to put `raw_payload` inside metadata.
- Build `semantic_dedup_key` from source, source_skill, chain, canonical asset id, event_type, 5m event bucket, direction_hint.
- Dedup using semantic key, not raw hash.
- Generate `event_id = sha256(semantic_dedup_key)[:24]`.
- Write normalized events as JSONL.
- Include `metadata.original_event_time_ms`, `metadata.available_at_ms`, `metadata.source_latency_ms`, `metadata.semantic_dedup_key`, `metadata.raw_payload_hash`, `metadata.connector_version`, `metadata.schema_version`, `metadata.price_series_id`, `metadata.price_mapping_type`.
- Set normalized `event_time_ms = available_at_ms`.
- Set `shadow_only = True`.
- Set `notional_usd = 0.0` unless the payload contains a purely informational notional field; never use notional as order size.
- Do not include `raw_payload` inside normalized event metadata.
- Do not include `order`, `swap`, `wallet`, `trade_intent`, or executable request objects in normalized events.

Event type to direction mapping:

```python
EVENT_TYPE_DIRECTION = {
    "smart_money_inflow": "long",
    "whale_accumulation": "long",
    "market_rank_surge": "unknown",
    "liquidity_expansion": "unknown",
    "token_audit_pass": "unknown",
    "smart_money_outflow": "avoid",
    "whale_distribution": "avoid",
    "token_audit_warning": "avoid",
    "liquidity_contraction": "avoid",
    "meme_lifecycle_event": "unknown",
    "cex_market_tape_anomaly": "unknown",
}
```

**Step 5: Verify connector tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_connector.py -q
```

Expected: pass.

---

## 8. Connector Summary Decision

### Task 6: Add summary decision and accounting validation

**Files:**

- Create: `src/research/external_signal_shadow/connector_summary.py`
- Test: `tests/research/test_external_signal_shadow_stage1_summary.py`

**Step 1: Write failing summary tests**

Create `tests/research/test_external_signal_shadow_stage1_summary.py`:

```python

def _summary(**overrides):
    payload = {
        "raw_payload_count": 3,
        "emitted_event_count": 1,
        "deduped_payload_count": 1,
        "quarantined_payload_count": 1,
        "rejected_payload_count": 0,
        "summary_accounting_ok": True,
        "live_trading_enabled": False,
        "exchange_paper_trading_allowed": False,
        "execution_engine_allowed": False,
        "research_shadow_replay_allowed": True,
        "wallet_required": False,
        "output_file": "events.jsonl",
        "output_file_sha256": "abc",
        "latency_p50_ms": 1000,
        "latency_p95_ms": 2000,
    }
    payload.update(overrides)
    return payload


def test_stage1_summary_passes_infrastructure_even_without_pnl():
    from src.research.external_signal_shadow.connector_summary import decide_stage1_connector_summary

    result = decide_stage1_connector_summary(_summary())

    assert result["decision"] == "external_signal_connector_stage1_passed"
    assert result["failure_type"] == "connector_completed"
    assert result["live_safe"] is False


def test_stage1_summary_fails_when_accounting_not_conservative():
    from src.research.external_signal_shadow.connector_summary import decide_stage1_connector_summary

    result = decide_stage1_connector_summary(_summary(summary_accounting_ok=False))

    assert result["decision"] == "external_signal_connector_stage1_failed"
    assert result["failure_type"] == "summary_accounting_failure"


def test_stage1_summary_fails_when_execution_flags_are_unsafe():
    from src.research.external_signal_shadow.connector_summary import decide_stage1_connector_summary

    result = decide_stage1_connector_summary(_summary(exchange_paper_trading_allowed=True))

    assert result["failure_type"] == "safety_failure"


def test_stage1_summary_prioritizes_safety_failure():
    from src.research.external_signal_shadow.connector_summary import decide_stage1_connector_summary

    result = decide_stage1_connector_summary(
        _summary(exchange_paper_trading_allowed=True, emitted_event_count=0)
    )

    assert result["failure_type"] == "safety_failure"


def test_stage1_summary_fails_when_no_events_emitted():
    from src.research.external_signal_shadow.connector_summary import decide_stage1_connector_summary

    result = decide_stage1_connector_summary(_summary(emitted_event_count=0, raw_payload_count=1, deduped_payload_count=0, quarantined_payload_count=1))

    assert result["failure_type"] == "schema_failure"
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_summary.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement `connector_summary.py`**

Create `src/research/external_signal_shadow/connector_summary.py`:

```python
def decide_stage1_connector_summary(summary: dict) -> dict:
    decision = "external_signal_connector_stage1_passed"
    failure_type = "connector_completed"
    primary_blocker = None

    if _unsafe_flags(summary):
        failure_type = "safety_failure"
        primary_blocker = "unsafe_runtime_flag"
    elif summary.get("raw_payload_count", 0) <= 0:
        failure_type = "data_failure"
        primary_blocker = "missing_raw_payloads"
    elif summary.get("summary_accounting_ok") is not True:
        failure_type = "summary_accounting_failure"
        primary_blocker = "accounting_invariant_failed"
    elif not summary.get("output_file") or not summary.get("output_file_sha256"):
        failure_type = "replay_handoff_failure"
        primary_blocker = "missing_output_file_or_hash"
    elif summary.get("emitted_event_count", 0) <= 0:
        failure_type = "schema_failure"
        primary_blocker = "no_emitted_events"

    if failure_type != "connector_completed":
        decision = "external_signal_connector_stage1_failed"

    return {
        **summary,
        "decision": decision,
        "failure_type": failure_type,
        "primary_blocker": primary_blocker,
        "live_safe": False,
        "exchange_paper_trading_allowed": False,
        "execution_engine_allowed": False,
        "research_shadow_replay_allowed": True,
        "alpha_interpretation_allowed": False,
    }


def _unsafe_flags(summary: dict) -> bool:
    return any(
        summary.get(flag) is not expected
        for flag, expected in {
            "live_trading_enabled": False,
            "exchange_paper_trading_allowed": False,
            "execution_engine_allowed": False,
            "research_shadow_replay_allowed": True,
            "wallet_required": False,
        }.items()
    )
```

**Step 4: Integrate in connector**

Update `run_file_backed_connector` to pass its raw summary through `decide_stage1_connector_summary` before returning/writing summary.

**Step 5: Verify**

```bash
PYTHONPATH=src uv run pytest tests/research/test_external_signal_shadow_stage1_summary.py tests/research/test_external_signal_shadow_stage1_connector.py -q
```

Expected: pass.

---

## 9. CLI Runner

### Task 7: Add Stage 1 connector CLI

**Files:**

- Create: `scripts/run_external_signal_shadow_stage1_connector.py`
- Test: `tests/scripts/test_run_external_signal_shadow_stage1_connector.py`

**Step 1: Write failing CLI tests**

Create `tests/scripts/test_run_external_signal_shadow_stage1_connector.py`:

```python
import json


def test_run_stage1_connector_writes_summary_and_events(tmp_path):
    from scripts.run_external_signal_shadow_stage1_connector import main

    output_events = tmp_path / "events.jsonl"
    output_summary = tmp_path / "summary.json"

    result = main(
        [
            "--input",
            "tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl",
            "--price-map",
            "tests/fixtures/external_signal_shadow/stage1_price_map.json",
            "--output-events",
            str(output_events),
            "--output-summary",
            str(output_summary),
            "--source",
            "fixture",
        ]
    )

    assert result == 0
    assert output_events.exists()
    assert output_summary.exists()
    summary = json.loads(output_summary.read_text())
    assert summary["decision"] == "external_signal_connector_stage1_passed"


def test_run_stage1_connector_rejects_external_api_flag(tmp_path):
    from scripts.run_external_signal_shadow_stage1_connector import main

    result = main(
        [
            "--input",
            "tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl",
            "--price-map",
            "tests/fixtures/external_signal_shadow/stage1_price_map.json",
            "--output-events",
            str(tmp_path / "events.jsonl"),
            "--output-summary",
            str(tmp_path / "summary.json"),
            "--source",
            "fixture",
            "--external-api",
        ]
    )

    assert result == 1


def test_run_stage1_connector_outputs_are_stage0_compatible(tmp_path):
    from scripts.run_external_signal_shadow_stage1_connector import main
    from src.research.external_signal_shadow.models import load_events_jsonl

    output_events = tmp_path / "events.jsonl"
    output_summary = tmp_path / "summary.json"
    result = main(
        [
            "--input",
            "tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl",
            "--price-map",
            "tests/fixtures/external_signal_shadow/stage1_price_map.json",
            "--output-events",
            str(output_events),
            "--output-summary",
            str(output_summary),
            "--source",
            "fixture",
        ]
    )

    assert result == 0
    assert load_events_jsonl(str(output_events))
```

**Step 2: Run failing CLI tests**

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_external_signal_shadow_stage1_connector.py -q
```

Expected: fail because script does not exist.

**Step 3: Implement CLI script**

Create `scripts/run_external_signal_shadow_stage1_connector.py`:

```python
import argparse
import json
from pathlib import Path

from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--price-map", required=True)
    parser.add_argument("--output-events", required=True)
    parser.add_argument("--output-summary", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--external-api", action="store_true")
    args = parser.parse_args(argv)

    if args.external_api:
        return 1

    try:
        summary = run_file_backed_connector(
            input_files=args.input,
            price_map_path=args.price_map,
            output_path=args.output_events,
            source=args.source,
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return 1

    output_summary = Path(args.output_summary)
    output_summary.parent.mkdir(parents=True, exist_ok=True)
    output_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"Written events: {args.output_events}")
    print(f"Written summary: {args.output_summary}")
    print(f"  decision: {summary['decision']}")
    print(f"  failure_type: {summary['failure_type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_external_signal_shadow_stage1_connector.py -q
```

Expected: pass.

---

## 10. Review Generator

### Task 8: Add Stage 1 connector review script

**Files:**

- Create: `scripts/review_external_signal_shadow_stage1_connector.py`
- Test: `tests/scripts/test_review_external_signal_shadow_stage1_connector.py`

**Step 1: Write failing review tests**

Create `tests/scripts/test_review_external_signal_shadow_stage1_connector.py`:

```python
import json


def test_review_stage1_connector_writes_markdown(tmp_path):
    from scripts.review_external_signal_shadow_stage1_connector import main

    summary = tmp_path / "summary.json"
    output = tmp_path / "review.md"
    summary.write_text(
        json.dumps(
            {
                "decision": "external_signal_connector_stage1_passed",
                "failure_type": "connector_completed",
                "raw_payload_count": 11,
                "emitted_event_count": 2,
                "deduped_payload_count": 1,
                "quarantined_payload_count": 5,
                "rejected_payload_count": 3,
                "summary_accounting_ok": True,
                "latency_p50_ms": 60_000,
                "latency_p95_ms": 60_000,
                "live_trading_enabled": False,
                "exchange_paper_trading_allowed": False,
                "execution_engine_allowed": False,
                "research_shadow_replay_allowed": True,
                "wallet_required": False,
                "reject_reason_counts": {"forbidden_executable_payload": 1},
                "quarantine_reason_counts": {"price_mapping_unavailable": 1},
            }
        )
    )

    result = main(["--summary", str(summary), "--output", str(output)])

    assert result == 0
    text = output.read_text()
    assert "External Signal Shadow Lab Stage 1 Connector Review" in text
    assert "不是 alpha 通过" in text
    assert "available_at_ms" in text
```

**Step 2: Run failing test**

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_review_external_signal_shadow_stage1_connector.py -q
```

Expected: fail because script does not exist.

**Step 3: Implement review script**

Create `scripts/review_external_signal_shadow_stage1_connector.py`.

The markdown must include:

- conclusion;
- scope;
- accounting summary;
- latency semantics;
- safety boundaries;
- reject/quarantine breakdowns;
- failure type;
- what cannot be concluded;
- next action.

Must explicitly state:

```text
本轮不是 alpha 通过；不是 paper/live 准入；不允许下单；不允许接钱包。
Stage 0 replay handoff uses available_at_ms, not original event_time_ms.
```

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_review_external_signal_shadow_stage1_connector.py -q
```

Expected: pass.

---

## 11. End-to-End Fixture Run

### Task 9: Run Stage 1.0 fixture pipeline and generate artifacts

**Files:**

- Runtime output: `data/external_signal_shadow/normalized/stage1_events.jsonl`
- Runtime output: `reports/external_signal_shadow/connectors/stage1_connector_summary.json`
- Runtime output: `docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-connector-review_CN.md`

**Step 1: Run connector**

```bash
PYTHONPATH=src uv run python scripts/run_external_signal_shadow_stage1_connector.py \
  --input tests/fixtures/external_signal_shadow/stage1_skill_payloads.jsonl \
  --price-map tests/fixtures/external_signal_shadow/stage1_price_map.json \
  --output-events data/external_signal_shadow/normalized/stage1_events.jsonl \
  --output-summary reports/external_signal_shadow/connectors/stage1_connector_summary.json \
  --source fixture
```

Expected:

```text
Written events: data/external_signal_shadow/normalized/stage1_events.jsonl
Written summary: reports/external_signal_shadow/connectors/stage1_connector_summary.json
  decision: external_signal_connector_stage1_passed
  failure_type: connector_completed
```

**Step 2: Generate review**

```bash
PYTHONPATH=src uv run python scripts/review_external_signal_shadow_stage1_connector.py \
  --summary reports/external_signal_shadow/connectors/stage1_connector_summary.json \
  --output docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-connector-review_CN.md
```

Expected:

```text
Written: docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-connector-review_CN.md
```

**Step 3: Inspect summary invariant**

```bash
jq '{decision, failure_type, raw_payload_count, emitted_event_count, deduped_payload_count, quarantined_payload_count, rejected_payload_count, summary_accounting_ok, latency_p50_ms, latency_p95_ms}' reports/external_signal_shadow/connectors/stage1_connector_summary.json
```

Expected:

```json
{
  "decision": "external_signal_connector_stage1_passed",
  "failure_type": "connector_completed",
  "raw_payload_count": 11,
  "emitted_event_count": 2,
  "deduped_payload_count": 1,
  "summary_accounting_ok": true
}
```

Exact quarantine/reject counts may differ if implementation classifies some invalid payloads more strictly, but the accounting invariant must hold.

---

## 12. Stage 0 Handoff Compatibility Check

### Task 10: Verify normalized events can be loaded by Stage 0

**Files:**

- No new file required.

**Step 1: Run loader check**

```bash
PYTHONPATH=src uv run python - <<'PY'
from src.research.external_signal_shadow.models import load_events_jsonl

events = load_events_jsonl('data/external_signal_shadow/normalized/stage1_events.jsonl')
assert events
for event in events:
    assert event.event_time_ms == event.metadata['available_at_ms']
    assert event.metadata['available_at_ms'] >= event.metadata['original_event_time_ms']
print(f'loaded_events={len(events)}')
PY
```

Expected:

```text
loaded_events=2
```

**Step 2: Do not run Stage 0 replay unless price bars are supplied**

Stage 1.0 only normalizes external events. Stage 0 replay still needs price bars. Do not fake price bars in the connector just to make replay pass.

---

## 13. Verification Suite

### Task 11: Run focused and broad verification

**Step 1: Focused Stage 1 tests**

```bash
PYTHONPATH=src uv run pytest \
  tests/research/test_external_signal_shadow_stage1_safety.py \
  tests/research/test_external_signal_shadow_stage1_price_mapping.py \
  tests/research/test_external_signal_shadow_stage1_connector.py \
  tests/research/test_external_signal_shadow_stage1_summary.py \
  tests/scripts/test_run_external_signal_shadow_stage1_connector.py \
  tests/scripts/test_review_external_signal_shadow_stage1_connector.py \
  -q
```

Expected: all pass.

**Step 2: Existing Stage 0 regression tests**

```bash
PYTHONPATH=src uv run pytest \
  tests/research/test_external_signal_shadow_models.py \
  tests/research/test_external_signal_shadow_risk_guard.py \
  tests/research/test_external_signal_shadow_cusum.py \
  tests/research/test_external_signal_shadow_triple_barrier.py \
  tests/research/test_external_signal_shadow_replay.py \
  tests/research/test_external_signal_shadow_summary.py \
  tests/scripts/test_run_external_signal_shadow_stage0.py \
  tests/scripts/test_review_external_signal_shadow_stage0.py \
  -q
```

Expected: all pass.

**Step 3: Ruff check changed Python files**

```bash
PYTHONPATH=src uv run ruff check \
  src/research/external_signal_shadow \
  scripts/run_external_signal_shadow_stage1_connector.py \
  scripts/review_external_signal_shadow_stage1_connector.py \
  tests/research/test_external_signal_shadow_stage1_safety.py \
  tests/research/test_external_signal_shadow_stage1_price_mapping.py \
  tests/research/test_external_signal_shadow_stage1_connector.py \
  tests/research/test_external_signal_shadow_stage1_summary.py \
  tests/scripts/test_run_external_signal_shadow_stage1_connector.py \
  tests/scripts/test_review_external_signal_shadow_stage1_connector.py
```

Expected: `All checks passed!`

**Step 4: Full test suite if time permits**

```bash
PYTHONPATH=src uv run pytest -q
```

Expected: all pass.

---

## 14. Completion Checklist

Before reporting completion, verify:

- `available_at_ms` exists in normalized event metadata.
- normalized `event_time_ms` equals `available_at_ms` for Stage 0 handoff.
- original event time is preserved as `metadata.original_event_time_ms`.
- `source_latency_ms` is calculated and summarized.
- `raw_payload_hash` does not include `fetched_at_ms`.
- `semantic_dedup_key` does not include `raw_payload_hash`.
- summary accounting invariant holds.
- forbidden nested keys are rejected.
- analytics keys such as `tx_count` and `swap_count_24h` are allowed.
- missing price mapping quarantines the payload.
- no code was added under `src/strategies/`, `src/execution/`, or `src/risk/`.
- no direct HTTP connector was implemented.
- no wallet / signing / order / swap / copy-trade path exists.
- `live_trading_enabled = false`.
- `exchange_paper_trading_allowed = false`.
- `execution_engine_allowed = false`.
- `research_shadow_replay_allowed = true`.

---

## 15. Expected Final Decision

If all gates pass, expected Stage 1.0 review conclusion:

```text
decision = external_signal_connector_stage1_passed
failure_type = connector_completed
live_safe = false
exchange_paper_trading_allowed = false
execution_engine_allowed = false
research_shadow_replay_allowed = true
alpha_interpretation_allowed = false
next_action = choose_one_real_read_only_source_for_manual_payload_dry_run
```

This still does **not** mean external skills have alpha. It only means the file-backed connector infrastructure is safe enough to accept manually exported read-only payloads into the research shadow pipeline.
