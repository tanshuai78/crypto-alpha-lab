import json
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_6a_futures_delisting_audit import (
    classify_symbol_and_product,
    extract_candidates_from_list,
    extract_schedule_facts_from_body,
    normalize_body_text,
    process_capture_bundle,
    validate_capture_metadata,
)
from src.research.external_signal_shadow.stage1_6a_futures_delisting_models import (
    CaptureMode,
    FactParseStatus,
    MarginFamily,
    OrderRestrictionType,
    UnderlyingFamily,
)


def test_classify_symbol_and_product():
    # USD-M Crypto Perpetual
    sym, margin, ctype, under, in_scope = classify_symbol_and_product("MOBUSDT", "Perpetual Contract")
    assert sym == "MOBUSDT"
    assert margin == MarginFamily.USD_M
    assert under == UnderlyingFamily.CRYPTO_ASSET
    assert in_scope is True

    # COIN-M Perp
    sym, margin, ctype, under, in_scope = classify_symbol_and_product("BTCUSD_PERP", "COIN-M contract")
    assert margin == MarginFamily.COIN_M
    assert in_scope is False

    # Commodity Perp
    sym, margin, ctype, under, in_scope = classify_symbol_and_product("BRENTUSDT", "Oil Contract")
    assert under == UnderlyingFamily.COMMODITY
    assert in_scope is False

    # Unknown / unsupported
    sym, margin, ctype, under, in_scope = classify_symbol_and_product("RANDOMTOKEN", "Unknown")
    assert margin == MarginFamily.UNKNOWN
    assert in_scope is False


def test_normalize_body_text_and_evidence_spans():
    html = b"<html><body><h1>Title</h1><p>Automatic settlement at 2024-04-03 09:00 (UTC)</p></body></html>"
    norm = normalize_body_text(html)
    assert "<h1>" not in norm
    assert "Automatic settlement at 2024-04-03 09:00 (UTC)" in norm


def test_extract_schedule_facts_complete_and_unstated():
    body_complete = """
    Published on: 2024-04-01 08:00:00 (UTC)
    Binance Futures will conduct automatic settlement on USD-M MOBUSDT Perpetual Contract at 2024-04-03 09:00 (UTC).
    Starting from 2024-04-02 08:30 (UTC), users are only allowed to reduce their positions (Reduce-Only).
    Last normal trading will end at 2024-04-03 08:30 (UTC).
    """
    facts = extract_schedule_facts_from_body(
        body_complete, "rev_001", "raw_hash", "extract_001", CaptureMode.HISTORICAL_BACKFILL.value
    )

    assert facts["settlement_time"].fact_parse_status == FactParseStatus.PRESENT.value
    assert facts["settlement_time"].timestamp_ms == 1712134800000
    assert facts["settlement_time"].fact_available_at_ms is None # Explicit nullable per P1-A
    assert facts["settlement_time"].evidence is not None

    assert facts["order_restriction"].fact_parse_status == FactParseStatus.PRESENT.value
    assert facts["order_restriction"].order_restriction_type == OrderRestrictionType.REDUCE_ONLY_ONLY.value
    assert facts["order_restriction"].timestamp_ms == 1712046600000

    # Unstated restriction test
    body_unstated = """
    Binance Futures will close all positions and delist USD-M PNTUSDT Perpetual Contract at 2024-04-05 10:00 (UTC).
    """
    facts_unstated = extract_schedule_facts_from_body(
        body_unstated, "rev_002", "raw_hash_2", "extract_002", CaptureMode.HISTORICAL_BACKFILL.value
    )
    assert facts_unstated["order_restriction"].fact_parse_status == FactParseStatus.NOT_STATED.value
    assert facts_unstated["order_restriction"].order_restriction_type is None # Never inferred per INV-04
    assert facts_unstated["order_restriction"].timestamp_ms is None


def test_process_capture_bundle_synthetic_fixture():
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    records = [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    result = process_capture_bundle(records)

    manifest = result["manifest"]
    metrics = result["metrics_raw"]
    contracts = result["contracts"]
    notices = result["notices"]

    assert len(manifest.items) == 6
    assert len(notices) == 6

    assert metrics["candidate_total_denominator"] == 6

    # 1007 is unavailable -> trusted_parents = 5 (1001, 1002, 1003, 1004, 1005)
    assert metrics["trusted_parents_count"] == 5

    # 1005 is incomplete batch -> symbols_mapped = 4 (1001, 1002, 1003, 1004)
    assert metrics["symbols_mapped_count"] == 4
    assert metrics["usd_m_crypto_children_excluded_due_to_incomplete_parent_count"] == 1

    # 1003 is mixed notice (USD-M BTCDOMUSDT + COIN-M BTCUSD)
    assert metrics["mixed_notice_count"] == 1
    assert metrics["out_of_scope_child_count"] == 1

    # Check contracts
    eligible_contracts = [c for c in contracts if c.source_audit_eligible]
    eligible_symbols = {c.canonical_symbol for c in eligible_contracts}
    assert "MOBUSDT" in eligible_symbols
    assert "DREPUSDT" in eligible_symbols
    assert "UNFIUSDT" in eligible_symbols
    assert "BTCDOMUSDT" in eligible_symbols
    assert "PNTUSDT" in eligible_symbols
    assert "BTCUSD" not in eligible_symbols


def test_revision_and_extraction_version_independence():
    """Verify that multiple revisions of the same article create distinct extraction identities."""
    body_r1 = "Binance Futures will delist USD-M MOBUSDT at 2024-04-03 09:00 (UTC)."
    body_r2 = "Binance Futures will delist USD-M MOBUSDT at 2024-04-03 12:00 (UTC)." # revised schedule

    facts_r1 = extract_schedule_facts_from_body(
        body_r1, "rev_001", "hash_r1", "extract_r1", CaptureMode.HISTORICAL_BACKFILL.value
    )
    facts_r2 = extract_schedule_facts_from_body(
        body_r2, "rev_002", "hash_r2", "extract_r2", CaptureMode.HISTORICAL_BACKFILL.value
    )

    assert facts_r1["settlement_time"].timestamp_ms == 1712134800000
    assert facts_r2["settlement_time"].timestamp_ms == 1712145600000
    assert facts_r1["settlement_time"].source_detail_revision_id == "rev_001"
    assert facts_r2["settlement_time"].source_detail_revision_id == "rev_002"


def test_capture_metadata_requires_exact_historical_source_contract():
    valid, reason = validate_capture_metadata(
        "https://www.binance.com/en/support/announcement/detail/1001",
        "announcement_detail",
        "en",
        "canonical_binance_english_detail",
        "historical_backfill",
    )
    assert valid is True
    assert reason is None

    for surface, variant, mode in (
        ("unexpected", "canonical_binance_english_detail", "historical_backfill"),
        ("announcement_detail", "unexpected", "historical_backfill"),
        ("announcement_detail", "canonical_binance_english_detail", "live_observed"),
    ):
        valid, _ = validate_capture_metadata(
            "https://www.binance.com/en/support/announcement/detail/1001",
            surface,
            "en",
            variant,
            mode,
        )
        assert valid is False


def test_reducer_rejects_untrusted_list_or_detail_metadata_before_derivation():
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    records = [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    invalid_list = [record.copy() for record in records]
    invalid_list[0]["request_variant"] = "unexpected"
    with pytest.raises(ValueError, match="Invalid list_capture metadata"):
        process_capture_bundle(invalid_list)

    invalid_detail = [record.copy() for record in records]
    next(record for record in invalid_detail if record.get("record_type") == "detail_observation")["capture_mode"] = "live_observed"
    with pytest.raises(ValueError, match="capture_mode must be historical_backfill"):
        process_capture_bundle(invalid_detail)


def test_candidate_rule_requires_binance_futures_and_delist():
    raw = b'{"articles":[{"id":"a","title":"Futures Will Delist A"}]}'
    manifest, _ = extract_candidates_from_list(
        {
            "raw_payload_base64": __import__("base64").b64encode(raw).decode("ascii"),
            "source_surface": "announcement_index",
            "source_locale": "en",
            "request_variant": "canonical_binance_english_index",
            "source_url": "https://www.binance.com/en/support/announcement/c-48",
            "capture_mode": "historical_backfill",
        }
    )
    assert manifest.items == []


def test_historical_semantic_extraction_persists_actual_extraction_time_without_pit_authority():
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    records = [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = process_capture_bundle(records)
    extraction = result["semantic_extractions"][0]

    assert isinstance(extraction["semantic_extracted_at_ms"], int)
    assert extraction["system_available_at_ms"] is None
    assert extraction["capture_time_status"] == "historical_unknown"


def test_repeated_detail_hash_preserves_earliest_revision_observation_time():
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    records = [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    duplicate = next(record.copy() for record in records if record.get("source_article_id") == "1001")
    duplicate["observed_at_ms"] = 1711929700000
    records.append(duplicate)

    result = process_capture_bundle(records)
    revision = next(row for row in result["detail_revisions"] if row["source_article_id"] == "1001")
    assert revision["revision_first_observed_at_ms"] == 1711929601001
