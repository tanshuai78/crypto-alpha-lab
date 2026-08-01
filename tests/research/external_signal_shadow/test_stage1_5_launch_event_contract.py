import json
from pathlib import Path

from src.research.external_signal_shadow.stage1_5_launch_event_contract import (
    build_formal_launch_event,
    classify_anchor_evidence,
    validate_formal_launch_event,
)


def test_validate_formal_launch_event_requires_full_v1_contract():
    invalid_row = {
        "event_id": "test_event_1",
        "symbol": "GRVTUSDT",
        # Missing formal_event_contract_version = 1
    }
    val = validate_formal_launch_event(invalid_row, "GRVTUSDT")
    assert not val["valid"]
    assert "formal_event_contract_version_missing_or_unsupported" in val["blockers"]


def test_validate_formal_launch_event_rejects_missing_per_symbol_anchor_contract():
    row = {
        "formal_event_contract_version": 1,
        "formal_event_consumable_by_stage1_5f": True,
        "source_contract_status": "formal_v1_valid",
        "symbol_identity_validation_status": "validated_by_exchangeinfo",
        "symbols": ["GRVTUSDT"],
        "launch_anchor_evidence_level": "exchangeinfo_fallback",
        "detail_fetch_attempted": True,
        "detail_fetch_status": "transient_unavailable",
        "detail_fetch_variant": "bapi_article_detail_query",
        "detail_confirmation_missing": True,
        "source_article_id": "20536b05b2a34b87a3bae99c45d0dc91",
        "stable_event_key": "binance_20536b05b2a34b87a3bae99c45d0dc91_GRVTUSDT",
        "event_id": "sha256_id",
        "parser_version": "stage1_5d_symbol_extraction_v3",
        "symbol_extraction_version": 3,
    }
    val = validate_formal_launch_event(row, "GRVTUSDT")
    assert not val["valid"]
    assert "symbol_effective_launch_time_missing_GRVTUSDT" in val["blockers"]


def test_classify_anchor_evidence_detail_confirmed():
    row = {
        "symbol_effective_launch_times_ms": {"GRVTUSDT": 1785501900000},
        "symbol_onboard_times_ms": {"GRVTUSDT": 1785501900000},
        "detail_fetch_attempted": True,
        "detail_fetch_status": "success",
        "detail_confirmation_missing": False,
    }
    res = classify_anchor_evidence(row, "GRVTUSDT")
    assert res["launch_anchor_evidence_level"] == "detail_confirmed" or res["launch_anchor_evidence_level"] == "detail_exchangeinfo_consensus"


def test_exchangeinfo_fallback_requires_auditable_detail_attempt():
    row = {
        "formal_event_contract_version": 1,
        "formal_event_consumable_by_stage1_5f": True,
        "source_contract_status": "formal_v1_valid",
        "symbol_identity_validation_status": "validated_by_exchangeinfo",
        "symbol_effective_launch_times_ms": {"GRVTUSDT": 1785501900000},
        "symbol_onboard_times_ms": {"GRVTUSDT": 1785501900000},
        "symbol_launch_time_candidates_ms": {"GRVTUSDT": 1785501900000},
        "symbol_effective_launch_time_sources": {"GRVTUSDT": "exchangeinfo_onboard_time"},
        "launch_anchor_validation_status": "valid",
        "launch_anchor_disagreement_ms": None,
        "launch_anchor_comparison_status": "single_source_exchangeinfo",
        "launch_anchor_evidence_level": "exchangeinfo_fallback",
        "detail_fetch_attempted": True,
        "detail_fetch_status": "transient_unavailable",
        "detail_fetch_variant": "bapi_detail_query",
        "detail_confirmation_missing": True,
        "source_article_id": "20536b05b2a34b87a3bae99c45d0dc91",
        "stable_event_key": "binance_20536b05b2a34b87a3bae99c45d0dc91_GRVTUSDT",
        "event_id": "sha256_id",
        "parser_version": "stage1_5d_symbol_extraction_v3",
        "symbol_extraction_version": 3,
        "symbols": ["GRVTUSDT"],
    }
    val = validate_formal_launch_event(row, "GRVTUSDT")
    assert val["valid"], f"Expected valid, got blockers: {val['blockers']}"


def test_consumer_rejects_invalid_evidence_level_field_combination():
    row = {
        "formal_event_contract_version": 1,
        "formal_event_consumable_by_stage1_5f": True,
        "launch_anchor_evidence_level": "detail_confirmed",
        "detail_fetch_attempted": False,  # Contradiction! detail_confirmed requires detail_fetch_attempted=True
    }
    val = validate_formal_launch_event(row, "GRVTUSDT")
    assert not val["valid"]
    assert "detail_confirmed_requires_detail_fetch_attempted" in val["blockers"]


def test_disagreement_and_comparison_status_must_be_consistent():
    row = {
        "formal_event_contract_version": 1,
        "formal_event_consumable_by_stage1_5f": True,
        "launch_anchor_disagreement_ms": 100000,  # 100s > 60s tolerance
        "launch_anchor_comparison_status": "consensus",  # Contradiction!
    }
    val = validate_formal_launch_event(row, "GRVTUSDT")
    assert not val["valid"]
    assert "launch_anchor_disagreement_conflict" in val["blockers"]


def test_builder_and_loader_use_same_contract_validator():
    raw_event = {
        "source_article_id": "20536b05b2a34b87a3bae99c45d0dc91",
        "title": "Binance Futures Will Launch USDⓈ-Margined GRVTUSDT Perpetual Contract (2026-07-31)",
        "detected_at_ms": 1785497559218,
        "source_published_at_ms": 1785497411662,
    }
    symbol_rows = [
        {
            "symbol": "GRVTUSDT",
            "effective_launch_time_ms": 1785501900000,
            "onboard_time_ms": 1785501900000,
            "launch_time_source": "bapi_detail_body",
            "identity_validation_status": "validated_by_exchangeinfo",
            "detail_fetch_attempted": True,
            "detail_fetch_status": "success",
            "detail_confirmation_missing": False,
        }
    ]
    diag = {
        "launch_anchor_disagreement_ms": None,
        "launch_anchor_comparison_status": "single_source_detail",
        "launch_anchor_evidence_level": "detail_confirmed",
    }
    formal_row = build_formal_launch_event(raw_event=raw_event, symbol_rows=symbol_rows, diagnostics=diag)
    val = validate_formal_launch_event(formal_row, "GRVTUSDT")
    assert val["valid"]
    assert formal_row["formal_event_contract_version"] == 1
    assert formal_row["formal_event_consumable_by_stage1_5f"] is True


def test_builder_preserves_detail_confirmation_missing_from_symbol_rows():
    raw_event = {
        "source_article_id": "20536b05b2a34b87a3bae99c45d0dc91",
        "title": "Binance Futures Will Launch USDⓈ-Margined GRVTUSDT Perpetual Contract (2026-07-31)",
        "detected_at_ms": 1785497559218,
    }
    symbol_rows = [
        {
            "symbol": "GRVTUSDT",
            "effective_launch_time_ms": 1785501900000,
            "onboard_time_ms": 1785501900000,
            "launch_time_source": "exchangeinfo_onboard_time",
            "detail_fetch_attempted": True,
            "detail_fetch_status": "transient_unavailable",
            "detail_confirmation_missing": True,
        }
    ]
    diag = {
        "launch_anchor_disagreement_ms": None,
        "launch_anchor_comparison_status": "single_source_exchangeinfo",
        "launch_anchor_evidence_level": "exchangeinfo_fallback",
    }
    formal_row = build_formal_launch_event(raw_event=raw_event, symbol_rows=symbol_rows, diagnostics=diag)
    assert formal_row["detail_confirmation_missing"] is True
