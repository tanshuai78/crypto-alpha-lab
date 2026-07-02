# Stage 1.5D U-Settlement Contract Symbol Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 Binance futures launch 公告中出现 `BTCU` / `ETHU` 这类 U-settled perpetual contract symbol 时，Stage 1.5D 错误推导为 `BTCUUSDT` / `ETHUUSDT` 并最终 terminal_failed，导致 Stage 1.5F 无法启动 live depth observation 的漏采问题。

**Architecture:** 在 Stage 1.5D detail fallback 中增加“原文 contract symbol + exchangeInfo 精确验证”路径。优先抽取原文完整合约符号，包括传统 `XXXUSDT/XXXUSDC` 和 Binance Futures `exchangeInfo` 中真实存在的非 quote-suffixed symbols（例如 `BTCU`, `ETHU`）；只有无法从 detail/table 得到真实 symbol 时，才保留 base-derived candidate。pending validation 的过期时间必须考虑公告中的 launch time/onboard time，不能在合约上架前提前判定失败。

**Tech Stack:** Python 3.12, pytest, stdlib `urllib`, existing Stage 1.5D parser/client/storage/runner, Binance USD-M public `exchangeInfo`, JSONL artifacts, `configs/base.py` centralized thresholds.

---

## 0. Incident Summary And Safety Boundaries

**Observed server evidence:**

```json
{
  "source_article_id": "25da4614ffff435fa28544b27fd33a39",
  "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
  "symbols": [],
  "symbol_extraction_source": "detail_base_asset_derived",
  "symbol_derivation_method": "base_asset_plus_quote",
  "symbol_validation_status": "rejected",
  "detail_fetch_status": "max_age_exceeded",
  "symbol_parse_status": "terminal_failed",
  "detected_at_ms": 1782889542209,
  "symbol_resolved_at_ms": 1782893183094
}
```

**Confirmed public exchangeInfo evidence:**

```text
BTCUUSDT missing
ETHUUSDT missing
BTCU FOUND  status=TRADING quoteAsset=U marginAsset=U onboardDate=2026-07-01T09:00:00Z
ETHU FOUND  status=TRADING quoteAsset=U marginAsset=U onboardDate=2026-07-01T10:00:00Z
```

**Root cause:**

```text
Stage 1.5D assumed base-asset-only launch text under USDⓈ/USDS/USD-M context should derive BASE + USDT.
That assumption is false for U-settled perpetual contracts. Binance Futures exchangeInfo uses symbols BTCU and ETHU directly, with quoteAsset=U and marginAsset=U.
```

**Secondary root cause:**

```text
The derived-candidate pending state expires after EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC = 3600.
For BTCU/ETHU, first_detected_at_ms was before onboardDate. The observer terminal-failed the event around 2026-07-01T08:06Z, before BTCU onboarded at 09:00Z and ETHU onboarded at 10:00Z.
```

**Safety boundaries:**

```text
scope = Stage 1.5D event-source symbol extraction only
server_replay_backfill_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

This plan must not mark the already missed BTCU/ETHU sample as valid 12h live depth evidence. That incident is parser/validation evidence only.

---

## Review Feedback Disposition

```text
decision = revised_for_required_fixes
```

Adopted required fixes:

```text
1. exchangeInfo validation must use structured symbol metadata, not only `set[str]`.
2. Pending validation must distinguish exchangeInfo-missing from present-but-not-emittable status.
3. exchangeInfo `onboardDate` is the highest-priority effective launch time when present.
4. U margin/quote asset allowlists must be explicit and separate.
5. Stage 1.5F compatibility must include raw-symbol depth endpoint behavior for U-settled symbols.
6. Server rollout notes are appendix only; local implementation completion must not include deployment.
7. Raw HTML/TXT string payloads are explicitly supported by `extract_symbol_candidates_from_detail_payload()`.
8. Launch time parsing must be UTC-explicit and must not use local-time-sensitive `time.mktime()`.
9. Candidate state will use `candidate_symbols`, not `derived_candidates`.
10. Summary counters are runner-maintained counters passed into `build_smoke_summary()`.
11. Stage 1.5D fixture mode must support exchangeInfo payload injection; otherwise BTCU/ETHU integration tests cannot validate without live network.
12. Stage 1.5F depth failure coverage must be a runnable test with concrete assertions, not a comment-only placeholder.
13. Pending validation state must persist exchangeInfo `onboardDate` metadata so `PRE_TRADING` / `PENDING_TRADING` expiry uses the right launch-time anchor.
```

Implementation choice for runner candidate state:

```text
Use Option A: rename `derived_candidates` to `candidate_symbols` for all candidate-validation paths.

All existing references must be updated together:
- max-age/expiry path currently checking `"derived_candidates" in state`
- max-retries path currently checking `"derived_candidates" not in state`
- pending validation path currently checking `"derived_candidates" in state`
- immediate post-detail validation path currently writing `state["derived_candidates"]`

Reason: `detail_contract_symbol` candidates are not derived symbols. Keeping `derived_candidates`
would preserve a misleading state name and increase future bug risk.
```

---

## 1. Desired Semantics

For Binance futures launch detail pages:

```text
1. Exact full-symbol path remains first priority:
   - Extract symbols already present as exact contract symbols in detail/body/table.
   - Supports traditional symbols: CAPUSDT, OUSDT, IPUSDC.
   - Adds support for exchangeInfo-validated non quote-suffixed symbols: BTCU, ETHU.

2. Base-derived path is fallback only:
   - Candidate BASE + USDT is allowed only as unverified pending candidate.
   - It may be emitted only after exact exchangeInfo validation.
   - It must never override or replace a contract symbol explicitly present in detail/table.

3. U-settled symbols:
   - If detail/table shows BTCU and exchangeInfo contains symbol=BTCU, emit BTCU.
   - Do not derive BTCUUSDT unless exchangeInfo contains BTCUUSDT.
   - event metadata must show the extraction path clearly.

4. Pending validation:
   - If candidates are not yet in exchangeInfo but launch time/onboard time is in the future, keep pending with status `pending_exchangeinfo_missing`.
   - If candidates are in exchangeInfo but status is not emittable yet, keep pending with status `pending_pre_trading`.
   - Do not terminal_fail before launch_time + configured grace buffer.

5. Stage 1.5F:
   - 1.5F may consume BTCU/ETHU only if its own exchangeInfo refresh confirms the symbol exists and the depth endpoint returns public orderbook data.
   - 1.5F must request depth with raw symbol `BTCU`, not rewritten `BTCUUSDT`.
```

Recommended event metadata for exact non quote-suffixed symbols:

```json
{
  "symbol_extraction_source": "detail_contract_symbol",
  "symbol_derivation_method": "none",
  "quote_derivation_source": "exchange_info",
  "symbol_validation_status": "validated",
  "symbol_exchangeinfo": {
    "BTCU": {
      "status": "TRADING",
      "contractType": "PERPETUAL",
      "quoteAsset": "U",
      "marginAsset": "U",
      "onboardDate": 1782896400000
    }
  },
  "symbol_onboard_times_ms": {"BTCU": 1782896400000},
  "symbol_effective_launch_times_ms": {"BTCU": 1782896400000},
  "launch_time_source": "exchange_info",
  "symbol_parse_status": "parsed"
}
```

Recommended metadata for rejected pre-validation candidates:

```json
{
  "symbol_extraction_source": "detail_contract_symbol_candidate",
  "symbol_derivation_method": "none",
  "quote_derivation_source": null,
  "symbol_validation_status": "pending_validation",
  "symbol_parse_status": "pending_retry"
}
```

No persisted `events/*.jsonl` row may contain `symbol_validation_status = "unverified"` with `symbol_parse_status = "parsed"`.

---

## Task 1: Add Config Constants For U-Settlement And Validation Grace

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`

**Step 1: Add failing config tests**

Add tests asserting these constants exist and have safe values:

```python
def test_stage1_5d_u_settlement_contract_config_constants():
    from configs import base

    assert "U" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS
    assert "USDT" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS
    assert "U" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES == ("PERPETUAL",)
    assert "PENDING_TRADING" in base.EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_EMITTABLE_SYMBOL_STATUSES == ("TRADING",)
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_GRACE_AFTER_LAUNCH_SEC >= 30 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_MAX_TOTAL_SEC >= 12 * 60 * 60
```

**Step 2: Run the failing test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py::test_stage1_5d_u_settlement_contract_config_constants \
  -q
```

Expected: FAIL because constants are missing.

**Step 3: Add constants**

Add near Stage 1.5D config in `configs/base.py`:

```python
EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS = ("USDT", "USDC", "U")
# Public Binance USD-M futures margin/settlement assets allowed for event-symbol validation.

EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS = ("USDT", "USDC", "U")
# Public Binance USD-M futures quote assets allowed for event-symbol validation.

EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES = ("PERPETUAL",)
# Only perpetual futures launch events are valid for Stage 1.5D/1.5F handoff.

EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES = ("TRADING", "PENDING_TRADING", "PRE_TRADING")
# Statuses that may keep a candidate in validation/pending state.

EXTERNAL_SIGNAL_STAGE1_5D_EMITTABLE_SYMBOL_STATUSES = ("TRADING",)
# Only these statuses may emit parsed event-symbol rows for Stage 1.5F.

EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_GRACE_AFTER_LAUNCH_SEC = 30 * 60
# Keep pre-launch symbol validation pending until launch time plus this grace buffer.

EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_MAX_TOTAL_SEC = 12 * 60 * 60
# Absolute upper bound for pending validation to avoid unbounded retry state.
```

**Step 4: Verify**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  -q
```

Expected: PASS.

---

## Task 2: Add Parser Tests For U-Settled Contract Symbol Candidates

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`
- Modify later: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`

**Step 1: Add failing tests**

Add tests:

```python
def test_detail_extracts_u_settled_contract_symbols_from_table_text():
    detail = """
    Binance Futures will launch the following perpetual contract(s) as below:
    2026-07-01 09:00 (UTC): BTCU Perpetual Contract with up to 100x leverage
    2026-07-01 10:00 (UTC): ETHU Perpetual Contract with up to 100x leverage
    USDⓈ-M Perpetual Contract
    BTCU
    ETHU
    Settlement Asset
    U (United Stables)
    U (United Stables)
    """

    result = extract_symbol_candidates_from_detail_payload(detail, max_symbols=30, title="Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)")

    assert result["symbols"] == ["BTCU", "ETHU"]
    assert result["symbol_extraction_source"] == "detail_contract_symbol"
    assert result["symbol_derivation_method"] == "none"
    assert result["symbol_validation_status"] == "requires_exchange_info_validation"


def test_detail_contract_symbol_path_prefers_btcu_over_btcuusdt_derivation():
    detail = "USDⓈ-M Perpetual Contract BTCU ETHU Settlement Asset U U"
    title = "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)"

    result = extract_symbol_candidates_from_detail_payload(detail, max_symbols=30, title=title)

    assert result["symbols"] == ["BTCU", "ETHU"]
    assert "BTCUUSDT" not in result["symbols"]
    assert "ETHUUSDT" not in result["symbols"]


def test_detail_contract_symbol_candidate_does_not_collect_table_labels():
    detail = """
    USDⓈ-M Perpetual Contract
    BTCU
    ETHU
    Launch Time
    Underlying Asset
    Settlement Asset
    Minimum Notional Value
    Capped Funding Rate
    """

    result = extract_symbol_candidates_from_detail_payload(detail, max_symbols=30, title="Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts")

    assert result["symbols"] == ["BTCU", "ETHU"]
```

**Step 2: Run tests and verify failure**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_detail_extracts_u_settled_contract_symbols_from_table_text \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_detail_contract_symbol_path_prefers_btcu_over_btcuusdt_derivation \
  -q
```

Expected: FAIL because parser currently returns derived `BTCUUSDT`/`ETHUUSDT` or misses U-settled contract symbols.

---

## Task 3: Implement Contract-Symbol Candidate Extraction Before Base+Quote Derivation

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Implementation rules:**

```text
0. `extract_symbol_candidates_from_detail_payload(payload, max_symbols, title=None)` already supports raw `str` payloads.
   Do not wrap HTML/TXT fixtures unless a test specifically needs nested JSON traversal.
1. Keep exact XXXUSDT/XXXUSDC regex as first priority.
2. Add a contract-symbol candidate path before BASE+USDT derivation.
3. Candidate path scans only short launch/detail table windows.
4. Candidate must appear near one of:
   - "Perpetual Contract"
   - "USDⓈ-M Perpetual Contract"
   - "USDS-M Perpetual Contract"
   - "Settlement Asset"
5. Candidate token constraints:
   - uppercase alnum
   - 2 to 30 chars
   - not in stopwords/table labels
   - not pure date/time/numeric token
6. Candidate path returns requires_exchange_info_validation, not parsed/validated.
```

Add stopwords/table labels:

```python
CONTRACT_SYMBOL_CANDIDATE_STOPWORDS = BASE_ASSET_STOPWORDS | {
    "LAUNCH", "TIME", "UNDERLYING", "PROJECT", "INFO", "TICK", "SIZE", "MINIMUM",
    "NOTIONAL", "VALUE", "CAPPED", "FUNDING", "RATE", "FEE", "FREQUENCY",
    "EVERY", "EIGHT", "HOURS", "MAXIMUM", "LEVERAGE", "TRADING", "MODE",
    "SUPPORTED", "UNITED", "STABLES", "UTC"
}
```

Implementation sketch:

```python
def extract_contract_symbol_candidates_from_detail_text(text: str, max_symbols: int) -> list[str]:
    windows = _find_contract_symbol_candidate_windows(text)
    out = []
    seen = set()
    for window in windows:
        for token in re.findall(r"\b[A-Z][A-Z0-9]{1,29}\b", window):
            if token in CONTRACT_SYMBOL_CANDIDATE_STOPWORDS:
                continue
            if token.isdigit():
                continue
            if token not in seen:
                seen.add(token)
                out.append(token)
            if len(out) >= max_symbols:
                return out
    return out
```

`extract_symbol_candidates_from_detail_payload()` order becomes:

```text
1. exact full symbols ending USDT/USDC -> validated_by_exact_text
2. contract-symbol candidates like BTCU/ETHU -> requires_exchange_info_validation
3. base+USDT derived candidates -> unverified
4. empty
```

For U-settled candidate path return:

```python
{
    "symbols": ["BTCU", "ETHU"],
    "symbol_extraction_source": "detail_contract_symbol",
    "symbol_derivation_method": "none",
    "quote_derivation_source": None,
    "symbol_validation_status": "requires_exchange_info_validation",
}
```

**Verify:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  -q
```

Expected: PASS.

---

## Task 4: Add Structured ExchangeInfo Validation Helper Tests

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify later: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`

**Problem:**

`active_symbols: set[str]` is insufficient for U-settled symbols. A symbol without `USDT/USDC` suffix must be validated with exchangeInfo metadata:

```text
contractType
status
quoteAsset
marginAsset
onboardDate
```

**Step 1: Add failing structured validation tests**

Add tests for the expected helper:

```python
def test_exchangeinfo_validation_accepts_trading_u_settled_perpetual_symbols():
    exchangeinfo_by_symbol = {
        "BTCU": {
            "symbol": "BTCU",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "quoteAsset": "U",
            "marginAsset": "U",
            "onboardDate": 1782896400000,
        },
        "ETHU": {
            "symbol": "ETHU",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "quoteAsset": "U",
            "marginAsset": "U",
            "onboardDate": 1782900000000,
        },
    }

    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU", "ETHU"],
        exchangeinfo_by_symbol=exchangeinfo_by_symbol,
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782896400000,
    )

    assert result["validated_symbols"] == ["BTCU", "ETHU"]
    assert result["pending_symbols"] == []
    assert result["rejected_symbols"] == []
    assert result["symbol_onboard_times_ms"] == {"BTCU": 1782896400000, "ETHU": 1782900000000}
    assert result["symbol_exchangeinfo"]["BTCU"]["quoteAsset"] == "U"


def test_exchangeinfo_validation_rejects_non_perpetual_contract():
    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU"],
        exchangeinfo_by_symbol={"BTCU": {"symbol": "BTCU", "contractType": "CURRENT_QUARTER", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U"}},
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782896400000,
    )

    assert result["validated_symbols"] == []
    assert result["rejected_symbols"] == ["BTCU"]
    assert result["rejection_reasons"]["BTCU"] == "exchange_info_disallowed_contract_type"


def test_exchangeinfo_validation_rejects_disallowed_margin_asset():
    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU"],
        exchangeinfo_by_symbol={"BTCU": {"symbol": "BTCU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "BUSD"}},
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782896400000,
    )

    assert result["validated_symbols"] == []
    assert result["rejected_symbols"] == ["BTCU"]
    assert result["rejection_reasons"]["BTCU"] == "exchange_info_disallowed_margin_asset"


def test_exchangeinfo_validation_does_not_accept_symbol_string_only_without_metadata():
    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU"],
        exchangeinfo_by_symbol={"BTCU": {}},
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782896400000,
    )

    assert result["validated_symbols"] == []
    assert result["rejected_symbols"] == ["BTCU"]
    assert result["rejection_reasons"]["BTCU"] == "exchange_info_incomplete_metadata"


def test_candidate_symbol_present_but_status_pending_does_not_emit_before_onboard_plus_grace():
    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU"],
        exchangeinfo_by_symbol={"BTCU": {"symbol": "BTCU", "contractType": "PERPETUAL", "status": "PRE_TRADING", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000}},
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782892800000,
    )

    assert result["validated_symbols"] == []
    assert result["pending_symbols"] == ["BTCU"]
    assert result["pending_reasons"]["BTCU"] == "exchange_info_symbol_status_not_trading_prelaunch"
```

**Step 2: Run and verify failure**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_exchangeinfo_validation_accepts_trading_u_settled_perpetual_symbols \
  -q
```

Expected: FAIL if helper is missing or still accepts only `set[str]`.

**Step 3: Implement helper**

In `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` add:

```python
def validate_candidate_symbols_against_exchangeinfo(
    candidates: list[str],
    exchangeinfo_by_symbol: dict[str, dict],
    allowed_margin_assets: tuple[str, ...],
    allowed_quote_assets: tuple[str, ...],
    allowed_contract_types: tuple[str, ...],
    validatable_statuses: tuple[str, ...],
    emittable_statuses: tuple[str, ...],
    now_ms: int,
) -> dict:
    ...
```

Return shape:

```python
{
    "validated_symbols": ["BTCU", "ETHU"],
    "pending_symbols": [],
    "rejected_symbols": [],
    "pending_reasons": {},
    "rejection_reasons": {},
    "symbol_exchangeinfo": {
        "BTCU": {
            "status": "TRADING",
            "contractType": "PERPETUAL",
            "quoteAsset": "U",
            "marginAsset": "U",
            "onboardDate": 1782896400000,
        }
    },
    "symbol_onboard_times_ms": {"BTCU": 1782896400000},
}
```

Validation rules:

```text
1. Missing from exchangeInfo -> pending_exchangeinfo_missing.
2. Missing required metadata -> rejected / exchange_info_incomplete_metadata.
3. contractType not in allowed_contract_types -> rejected / exchange_info_disallowed_contract_type.
4. marginAsset not in allowed_margin_assets -> rejected / exchange_info_disallowed_margin_asset.
5. quoteAsset not in allowed_quote_assets -> rejected / exchange_info_disallowed_quote_asset.
6. status in emittable_statuses -> validated.
7. status in validatable_statuses but not emittable_statuses -> pending_pre_trading.
8. unknown status -> rejected / exchange_info_unrecognized_status.
```

**Step 4: Build structured exchangeInfo cache once per poll**

Replace `get_active_symbols()` with `get_exchangeinfo_by_symbol()` or update it to return:

```python
exchangeinfo_by_symbol: dict[str, dict]
ex_ok: bool
```

The per-poll cache must still be computed once and shared by first-bar checks and detail candidate validation.
Compute `exchangeinfo_by_symbol` before both first-bar processing and `detail_retry_state` candidate validation.
Both consumers must read from the same cache object and must not mutate it.

Required fixture-mode behavior:

```text
1. `get_exchangeinfo_by_symbol()` must not return an unconditional empty dict in fixture mode.
2. If `args.fixture_json` contains top-level `exchangeInfoPayload`, parse it as a Binance USD-M exchangeInfo mock.
3. If `exchangeInfoPayload` is present and valid, return `(exchangeinfo_by_symbol, True)`.
4. If `exchangeInfoPayload` is absent in fixture mode, return `({}, False)` and keep candidates pending or fixture_failed according to the test scenario.
5. Fixture-mode exchangeInfo parsing must not perform live network calls.
6. Write a request_manifest row with `source_type = "fixture_exchangeinfo"` or an equivalent fixture marker so review can distinguish fixture data from live public exchangeInfo.
```

Fixture shape for integration tests:

```json
{
  "exchangeInfoPayload": {
    "symbols": [
      {
        "symbol": "BTCU",
        "contractType": "PERPETUAL",
        "status": "TRADING",
        "quoteAsset": "U",
        "marginAsset": "U",
        "onboardDate": 1782896400000
      }
    ]
  },
  "data": {
    "catalogs": []
  }
}
```

Add a fixture integration test:

```python
def test_fixture_mode_exchangeinfo_payload_enables_candidate_validation_without_network(tmp_path, monkeypatch):
    fixture = {
        "exchangeInfoPayload": {
            "symbols": [
                {"symbol": "BTCU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000},
                {"symbol": "ETHU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782900000000},
            ]
        },
        "data": {"catalogs": [{"articles": [{
            "code": "25da4614ffff435fa28544b27fd33a39",
            "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
            "releaseDate": 1782830702782,
            "detailPayload": "USDⓈ-M Perpetual Contract BTCU ETHU Settlement Asset U U",
        }]}]},
    }

    def fail_network(*args, **kwargs):
        raise AssertionError("fixture mode must not call live network")

    monkeypatch.setattr("urllib.request.urlopen", fail_network)
    # Write fixture JSON, run one collector poll in fixture mode, then assert parsed BTCU/ETHU event.
```

**Verify:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: PASS.

---

## Task 5: Preserve Extraction Source During Validation

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Problem:**

Current runner treats all non `validated_by_exact_text` extraction as derived candidates. That is too coarse. `detail_contract_symbol` is not base-derived; it is exact candidate from source text that still needs exchangeInfo confirmation.

**Step 1: Add failing fixture test**

Create a fixture payload with one article:

```python
payload = {
    "exchangeInfoPayload": {
        "symbols": [
            {"symbol": "BTCU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000},
            {"symbol": "ETHU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782900000000},
        ]
    },
    "data": {"catalogs": [{"articles": [{
        "code": "25da4614ffff435fa28544b27fd33a39",
        "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
        "releaseDate": 1782830702782,
        "detailPayload": "USDⓈ-M Perpetual Contract BTCU ETHU Settlement Asset U U",
    }]}]}
}
```

Mock exchangeInfo payload contains:

```json
{
  "symbols": [
    {"symbol": "BTCU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U"},
    {"symbol": "ETHU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U"}
  ]
}
```

Expected event row:

```python
assert event["symbols"] == ["BTCU", "ETHU"]
assert event["symbol_extraction_source"] == "detail_contract_symbol"
assert event["symbol_derivation_method"] == "none"
assert event["quote_derivation_source"] == "exchange_info"
assert event["symbol_validation_status"] == "validated"
assert event["symbol_parse_status"] == "parsed"
```

**Step 2: Implement metadata preservation**

When `extraction_res["symbol_validation_status"] == "requires_exchange_info_validation"`, store:

```python
state["candidate_symbols"] = extraction_res["symbols"]
state["symbol_extraction_source"] = extraction_res["symbol_extraction_source"]
state["symbol_derivation_method"] = extraction_res["symbol_derivation_method"]
state["quote_derivation_source"] = "exchange_info"
state["symbol_validation_status"] = "pending_exchangeinfo_missing"
state["symbol_launch_times_ms"] = extraction_res.get("symbol_launch_times_ms", {})
state["symbol_onboard_times_ms"] = {}
effective_launch = build_effective_launch_times_ms(
    candidate_symbols=state["candidate_symbols"],
    symbol_onboard_times_ms=state["symbol_onboard_times_ms"],
    symbol_launch_times_ms=state["symbol_launch_times_ms"],
    source_published_at_ms=article.get("releaseDate") or 0,
    first_detected_at_ms=state["first_detected_at_ms"],
)
state["symbol_effective_launch_times_ms"] = effective_launch["symbol_effective_launch_times_ms"]
state["launch_time_source"] = effective_launch["launch_time_source"]
```

Use `candidate_symbols` everywhere. Do not keep `derived_candidates`.

```text
Required migration points in `run_stage1_5d_live_event_source_smoke_collector.py`:
1. max-age/expiry path currently checking `"derived_candidates" in state`
2. max-retries path currently checking `"derived_candidates" not in state`
3. pending validation path currently checking `"derived_candidates" in state`
4. immediate post-detail validation path currently writing `state["derived_candidates"]`
5. both validation list comprehensions currently reading `state["derived_candidates"]`
```

The post-detail branch should write `state["candidate_symbols"] = extraction_res["symbols"]`.
The pending branch should check `if "candidate_symbols" in state:`.

**Step 3: Ensure emitted parsed row is not unverified**

On success:

```python
"symbol_validation_status": "validated"
"quote_derivation_source": "exchange_info"
"symbol_exchangeinfo": validation_result["symbol_exchangeinfo"]
"symbol_onboard_times_ms": validation_result["symbol_onboard_times_ms"]
"symbol_effective_launch_times_ms": effective_launch_times
"launch_time_source": "exchange_info"
```

On pending status after exchangeInfo validation:

```python
state["symbol_exchangeinfo"] = validation_result.get("symbol_exchangeinfo", {})
state["symbol_onboard_times_ms"] = validation_result.get("symbol_onboard_times_ms", {})
effective_launch = build_effective_launch_times_ms(
    candidate_symbols=state["candidate_symbols"],
    symbol_onboard_times_ms=state["symbol_onboard_times_ms"],
    symbol_launch_times_ms=state.get("symbol_launch_times_ms", {}),
    source_published_at_ms=state.get("source_published_at_ms", 0),
    first_detected_at_ms=state["first_detected_at_ms"],
)
state["symbol_effective_launch_times_ms"] = effective_launch["symbol_effective_launch_times_ms"]
state["launch_time_source"] = effective_launch["launch_time_source"]

if validation_result["pending_symbols"]:
    state["symbol_validation_status"] = "pending_pre_trading" if any(
        reason == "exchange_info_symbol_status_not_trading_prelaunch"
        for reason in validation_result.get("pending_reasons", {}).values()
    ) else "pending_exchangeinfo_missing"
```

This is required because `PRE_TRADING` / `PENDING_TRADING` symbols can already expose `onboardDate`.
That `onboardDate` must drive expiry instead of the older flat 3600s detail max-age.

**Verify:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: PASS.

---

## Task 6: Parse Launch Times, Onboard Times, And Extend Pending Validation Window

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Effective launch time priority:**

```text
1. exchangeInfo.onboardDate by symbol
2. detail parsed launch time by symbol
3. article releaseDate / source_published_at_ms
4. first_detected_at_ms + legacy max age
```

Use per-symbol effective launch times, not only a single latest detail time.

**Step 1: Add parser tests for UTC launch time extraction**

Add:

```python
def test_extract_launch_times_from_detail_payload_for_btcu_ethu_uses_utc_epoch_ms():
    detail = """
    2026-07-01 09:00 (UTC): BTCU Perpetual Contract with up to 100x leverage
    2026-07-01 10:00 (UTC): ETHU Perpetual Contract with up to 100x leverage
    """

    result = extract_symbol_candidates_from_detail_payload(detail, max_symbols=30, title="Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)")

    assert result["symbol_launch_times_ms"]["BTCU"] == 1782896400000
    assert result["symbol_launch_times_ms"]["ETHU"] == 1782900000000
```

**UTC requirement:**

```text
Implement launch time parsing with explicit UTC timezone handling.
Allowed: datetime(..., tzinfo=timezone.utc), datetime.fromisoformat(...).replace(tzinfo=timezone.utc), calendar.timegm().
Forbidden: time.mktime(), naive datetime.timestamp(), or any local-time-sensitive conversion.
```

**Step 2: Implement launch time extraction**

Add helper:

```python
def extract_symbol_launch_times_ms(text: str, symbols: list[str]) -> dict[str, int]:
    # Match lines like: 2026-07-01 09:00 (UTC): BTCU Perpetual Contract
    # Return UTC epoch ms by symbol.
```

Return field from `extract_symbol_candidates_from_detail_payload()`:

```python
"symbol_launch_times_ms": {"BTCU": 1782896400000, "ETHU": 1782900000000}
```

For payloads without parseable launch time, return `{}`.

**Step 3: Add effective launch time helper tests**

Add runner helper tests:

```python
def test_effective_launch_time_prefers_exchangeinfo_onboard_date_over_detail_time():
    result = build_effective_launch_times_ms(
        candidate_symbols=["BTCU"],
        symbol_onboard_times_ms={"BTCU": 1782896400000},
        symbol_launch_times_ms={"BTCU": 1782892800000},
        source_published_at_ms=1782830702782,
        first_detected_at_ms=1782889542209,
    )

    assert result["symbol_effective_launch_times_ms"] == {"BTCU": 1782896400000}
    assert result["launch_time_source"] == "exchange_info"


def test_effective_launch_time_falls_back_to_detail_when_onboard_missing():
    result = build_effective_launch_times_ms(
        candidate_symbols=["BTCU"],
        symbol_onboard_times_ms={},
        symbol_launch_times_ms={"BTCU": 1782896400000},
        source_published_at_ms=1782830702782,
        first_detected_at_ms=1782889542209,
    )

    assert result["symbol_effective_launch_times_ms"] == {"BTCU": 1782896400000}
    assert result["launch_time_source"] == "detail"
```

**Step 4: Add runner pending-window tests**

Add test where:

```text
first_detected_at_ms = 2026-07-01T07:05:42Z
candidate_symbols = BTCU, ETHU
current now = 2026-07-01T08:06:23Z
launch times = 09:00Z and 10:00Z
exchangeInfo does not yet contain BTCU/ETHU
```

Expected:

```text
events/*.jsonl has no terminal_failed row yet
retry_state remains pending
symbol_validation_status = pending_exchangeinfo_missing
pre_launch_validation_deferred_count increments
```

Add test where symbol exists but status is not emittable:

```text
exchangeInfo contains BTCU status=PRE_TRADING contractType=PERPETUAL quoteAsset=U marginAsset=U onboardDate=09:00Z
now < onboardDate + grace
```

Expected:

```text
events/*.jsonl has no parsed row yet
retry_state remains pending
symbol_validation_status = pending_pre_trading
symbol_parse_failed_reason is not terminal
symbol_onboard_times_ms contains BTCU onboardDate from exchangeInfo
symbol_effective_launch_times_ms uses BTCU onboardDate, not first_detected_at_ms + max age
```

Add terminal expiry tests:

```text
1. missing from exchangeInfo after effective_launch_time + grace -> terminal_failed / exchange_info_symbol_missing_after_grace
2. present but not TRADING after effective_launch_time + grace -> terminal_failed / exchange_info_symbol_status_not_trading_after_grace
```

**Step 5: Implement candidate-aware expiry function**

Add helper in runner:

```python
def should_expire_candidate_validation(state: dict, now_ms: int) -> bool:
    first_detected_at_ms = state["first_detected_at_ms"]
    absolute_max_ms = first_detected_at_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_MAX_TOTAL_SEC * 1000

    effective_launch_times = state.get("symbol_effective_launch_times_ms") or {}
    if effective_launch_times:
        latest_effective_launch_ms = max(effective_launch_times.values())
        launch_grace_ms = latest_effective_launch_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_GRACE_AFTER_LAUNCH_SEC * 1000
        return now_ms > min(absolute_max_ms, launch_grace_ms)

    legacy_max_age_ms = first_detected_at_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC * 1000
    return now_ms > min(absolute_max_ms, legacy_max_age_ms)
```

Replace current raw age check for candidate states:

```python
if age_sec > max_age_limit:
```

with candidate-aware logic:

```python
has_candidate_symbols = bool(state.get("candidate_symbols"))
if has_candidate_symbols:
    expire = should_expire_candidate_validation(state, now_ms)
else:
    expire = age_sec > max_age_limit
```

**Step 6: Propagate timing metadata into parsed events**

On validated event emission, include:

```python
norm_event["symbol_launch_times_ms"] = state.get("symbol_launch_times_ms", {})
norm_event["symbol_onboard_times_ms"] = validation_result.get("symbol_onboard_times_ms", {})
norm_event["symbol_effective_launch_times_ms"] = effective_launch_times["symbol_effective_launch_times_ms"]
norm_event["launch_time_source"] = effective_launch_times["launch_time_source"]
```

Also persist the same timing metadata in retry state while the candidate is still pending:

```python
state["symbol_onboard_times_ms"] = validation_result.get(
    "symbol_onboard_times_ms",
    state.get("symbol_onboard_times_ms", {}),
)
state["symbol_effective_launch_times_ms"] = effective_launch_times["symbol_effective_launch_times_ms"]
state["launch_time_source"] = effective_launch_times["launch_time_source"]
```

This applies to:

```text
1. pending_exchangeinfo_missing path when exchangeInfo is unavailable or symbol is absent.
2. pending_pre_trading path when exchangeInfo contains symbol metadata but status is not yet TRADING.
3. validated path before emitting parsed event.
4. terminal expiry path so diagnostics show which launch-time anchor was used.
```

**Verify:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: PASS.

---

## Task 7: Add Stage 1.5F Compatibility And Depth Request Tests For U-Settled Symbols

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py` if this test file exists; otherwise add depth-client tests to the existing Stage 1.5F client test file.
- Possibly modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Possibly modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py`

**Step 1: Add loader compatibility test**

Add a Stage 1.5D event row:

```python
row = {
    "event_id": "evt-btcu-ethu",
    "event_type": "futures_contract_launch",
    "detected_at_ms": 1782896400000,
    "source_article_id": "25da4614ffff435fa28544b27fd33a39",
    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
    "symbols": ["BTCU", "ETHU"],
    "symbol_extraction_source": "detail_contract_symbol",
    "symbol_validation_status": "validated",
    "paper_trading_allowed": False,
    "live_trading_allowed": False,
    "execution_engine_allowed": False,
    "alpha_interpretation_allowed": False,
}
```

Expected:

```python
flatten_event_symbols([row]) -> two rows: BTCU, ETHU
classify_event_symbol_eligibility(... exchangeinfo symbols includes BTCU/ETHU ...) -> eligible
```

**Step 2: Add depth request raw-symbol test**

Add:

```python
def test_1_5f_u_settled_symbol_depth_request_uses_raw_symbol_btcu_not_btcusdt():
    request = build_depth_url("BTCU", limit=100)

    assert "symbol=BTCU" in request
    assert "BTCUUSDT" not in request
```

Use the existing `build_depth_url()` helper in `src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py`.

**Step 3: Add depth failure handling test**

Add:

```python
import urllib.error

from src.research.external_signal_shadow.stage1_5f_live_depth_observer_client import (
    fetch_depth_snapshot,
)


def test_1_5f_records_depth_symbol_validation_failure_without_crashing(monkeypatch):
    def mock_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://fapi.binance.com/fapi/v1/depth?symbol=BTCU&limit=100",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    result = fetch_depth_snapshot("BTCU", live_public_readonly=True)

    assert result["ok"] is False
    assert result["error"] == "http_error_400"
    assert result["manifest_row"]["requested_path"] == "/fapi/v1/depth"
    assert result["manifest_row"]["http_status"] == 400
    assert result["manifest_row"]["error"] == "http_error_400"
```

Expected state/summary behavior:

```text
observation_status = failed_depth_symbol_validation or rejected_depth_symbol_not_found
research_result_valid = false
execution_feasibility_claim_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

**Step 4: Verify**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py \
  -q
```

If `test_stage1_5f_live_depth_observer_client.py` does not exist, run the actual file where Stage 1.5F client tests were added.

Expected: PASS.

---

## Task 8: Update Summary/Diagnostics For Candidate Validation Expiry

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py`

**Required summary fields:**

```json
{
  "candidate_validation_pending_count": 0,
  "candidate_validation_success_count": 0,
  "candidate_validation_expired_count": 0,
  "u_settlement_symbol_extracted_count": 0,
  "pre_launch_validation_deferred_count": 0
}
```

**Rules:**

```text
1. candidate_validation_pending_count increments for candidate symbols waiting for exchangeInfo.
2. candidate_validation_success_count increments when BTCU/ETHU-style candidates validate and emit parsed event.
3. candidate_validation_expired_count increments only after candidate-aware expiry.
4. pre_launch_validation_deferred_count increments when candidate is missing from exchangeInfo but now < launch_time + grace.
```

**Counter ownership:**

```text
These counters must be maintained by the runner and passed through the existing `counters` dict into `build_smoke_summary()`.
Do not rely on summary-only event scanning for these fields.

Reason: current `detail_symbol_extracted_count` fallback scans only `symbol_extraction_source == "detail"`;
new U-settled rows use `symbol_extraction_source == "detail_contract_symbol"` and would be missed by old fallback logic.
```

Runner counter mapping:

```text
candidate_validation_pending_count:
  increment when validation_result.pending_symbols is non-empty and no terminal expiry occurs.

candidate_validation_success_count:
  increment when validation_result.validated_symbols is non-empty and a parsed event row is emitted.

candidate_validation_expired_count:
  increment when should_expire_candidate_validation(...) returns true and terminal_failed is emitted.

u_settlement_symbol_extracted_count:
  increment by len(validated_symbols) when any validated exchangeInfo row has quoteAsset == "U" or marginAsset == "U".

pre_launch_validation_deferred_count:
  increment when pending reason is pending_exchangeinfo_missing or pending_pre_trading and now is before effective_launch_time + grace.
```

**Verify:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: PASS.

---

## Task 9: Regression For No Unsafe API Usage

**Files:**
- No code changes unless grep finds unsafe patterns.

Run:

```bash
rg -n "apiKey\s*=|api_key\s*=|secret\s*=|from .*TradeIntent|TradeIntent\(|from .*SignalCandidate|SignalCandidate\(|order_endpoint\s*=\s*True|private_ws|create_order|cancel_order|fetch_balance|withdraw|transfer|requests\.post|httpx\.post|ccxt|wallet|private_key|signed_tx|raw_tx|order_request|swap_request" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d* \
  tests/research/external_signal_shadow/test_stage1_5d_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py || true
```

Expected: no unsafe hits. Explicit `*_allowed = false` and `*_used = false` safety fields are allowed.

---

## Task 10: Run Full Relevant Regression Suite

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

If `test_stage1_5f_live_depth_observer_client.py` does not exist, replace it with the actual Stage 1.5F client test file created in Task 7.

Expected:

```text
all tests pass
```

If any test fails, stop and inspect root cause before changing more code.

---

## Task 11: Local Fixture Smoke For BTCU/ETHU

**Files:**
- Create if needed: `tests/fixtures/external_signal_shadow/stage1_5d_btcu_ethu_u_settlement_fixture.json`
- Create if needed: `tests/fixtures/external_signal_shadow/stage1_5d_exchangeinfo_u_settlement_fixture.json`

Run a one-poll local fixture smoke that exercises:

```text
1. announcement title BTCU/ETHU
2. detail body/table contains BTCU/ETHU and launch times
3. mock exchangeInfo contains BTCU/ETHU status=TRADING quoteAsset=U marginAsset=U
4. output event row has symbols=["BTCU", "ETHU"]
```

Expected event row must contain:

```json
{
  "symbols": ["BTCU", "ETHU"],
  "symbol_extraction_source": "detail_contract_symbol",
  "symbol_validation_status": "validated",
  "symbol_parse_status": "parsed",
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "alpha_interpretation_allowed": false
}
```

Do not use live public endpoints in this fixture smoke.

---

## Appendix A: Future Server Rollout Notes

This appendix is not part of local implementation completion.

**Do not deploy until Tasks 1-11 pass locally and code review is accepted.**

After local tests pass and code review is accepted, use a separate deployment checklist:

1. Sync code to server with data excluded.
2. Start a new Stage 1.5D output root; do not reuse previous `_7d_hotfix` root because it already contains terminal_failed BTCU/ETHU evidence.
3. Bootstrap a new Stage 1.5F output root from the new Stage 1.5D root.
4. Start a new Stage 1.5F observer.

Recommended names:

```bash
STAGE1_5D_EVENTS_OUT=data/external_signal_shadow/stage1_5d/live_event_source_continuous_YYYYMMDDTHHMMSSZ_7d_u_settlement_hotfix
STAGE1_5F_OUT=data/external_signal_shadow/stage1_5f/live_depth_observer_7d_u_settlement_hotfix
```

Post-deploy checks:

```bash
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json"
wc -l "$STAGE1_5F_OUT"/heartbeat/*.jsonl 2>/dev/null || true
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20
wc -l "$STAGE1_5D_EVENTS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/events/*.jsonl 2>/dev/null || true
```

Expected initial state:

```text
1.5D heartbeats increasing
1.5F heartbeats increasing
post_watermark_events_accepted may be 0 until a new post-watermark launch arrives
no blocker
stage1_5e_context_missing = false
request_success_rate >= 0.95
failed_requests_count = 0 or small transient count
```

---

## Completion Criteria

Implementation is complete only when all are true:

```text
1. BTCU/ETHU fixture emits symbols=["BTCU", "ETHU"], not BTCUUSDT/ETHUUSDT.
2. U-settled symbols validate through exchangeInfo before parsed event emission.
3. Structured exchangeInfo validation rejects non-PERPETUAL, disallowed margin/quote assets, incomplete metadata, and unknown statuses.
4. `PENDING_TRADING` / `PRE_TRADING` candidates remain pending and are not emitted to Stage 1.5F.
5. No parsed persisted event row contains symbol_validation_status=unverified.
6. Pending validation does not expire before effective_launch_time + configured grace buffer.
7. effective_launch_time uses exchangeInfo onboardDate before detail launch time.
8. Stage 1.5F loader accepts BTCU/ETHU rows and still relies on exchangeInfo before depth collection.
9. Stage 1.5F depth request uses raw symbol BTCU/ETHU, not BTCUUSDT/ETHUUSDT.
10. Stage 1.5F depth client handles symbol-invalid HTTP errors without crashing and records manifest diagnostics.
11. Fixture mode can validate BTCU/ETHU through `exchangeInfoPayload` without live network.
12. Existing USDT/USDC futures launch extraction tests still pass.
13. Safety grep has no unsafe private/trading API hits.
14. No trade, paper trade, execution engine, alpha, or execution-feasibility proof flags are enabled.
```

## Non-Goals

```text
1. Do not backfill BTCU/ETHU as valid 12h live depth evidence.
2. Do not infer execution feasibility from current BTCU/ETHU depth.
3. Do not start paper/live trading.
4. Do not expand 1.5D into a full Binance announcement crawler beyond the current page-1 smoke/continuous source scope.
5. Do not alter Stage 1.5C replay interpretation.
```
