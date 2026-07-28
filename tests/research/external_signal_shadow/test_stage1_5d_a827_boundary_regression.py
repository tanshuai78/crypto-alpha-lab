import json
from pathlib import Path

from configs import base
from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
    extract_symbol_candidates_from_bapi_article_payload,
    PARSER_VERSION,
    LAUNCH_SCHEDULE_PARSER_VERSION,
)
from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
    serialize_retry_articles,
    load_detail_retry_scheduler_state,
)
from src.risk.limits import RiskLimits


def test_a827_real_fixture_end_to_end_extraction():
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json")
    assert fixture_path.exists()
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    res = extract_symbol_candidates_from_bapi_article_payload(
        payload,
        max_symbols=30,
        title="Binance Futures Will Launch USDⓈ-Margin TMF, TBT and BITOU Perpetual Contracts with Up to 75x Leverage",
    )

    assert res["symbols"] == ["TMFUSDT", "TBTUSDT", "BITOUSDT"]
    assert res["parser_status"] == "parsed"
    assert res.get("symbol_parse_failed_reason") is None
    assert res["launch_schedule_parser_version"] == LAUNCH_SCHEDULE_PARSER_VERSION

    assert res["launch_time_resolution_status"] == "table_line_matched"

    launch_times = res["symbol_launch_times_ms"]
    assert len(launch_times) == 3
    assert launch_times["TMFUSDT"] == 1785159000000
    assert launch_times["TBTUSDT"] == 1785159300000
    assert launch_times["BITOUSDT"] == 1785159600000




def test_a827_strict_launch_anchor_policy_persisted_in_schema_v2(tmp_path):
    state = {
        "articles": {
            "a827": {
                "source_article_id": "a827",
                "parsed_candidate_symbols": ["TMFUSDT", "TBTUSDT", "BITOUSDT"],
                "last_bapi_parser_status": "parsed",
                "launch_anchor_policy": "bapi_multi_contract_strict",
                "required_launch_anchor_source": "detail_per_symbol_time_or_exchangeinfo_onboard",
                "symbol_launch_time_candidates_ms": {"TMFUSDT": 1784964600000, "TBTUSDT": 1784964600000, "BITOUSDT": 1784964600000},
            }
        },
        "endpoint_health": {},
    }
    serialized = serialize_retry_articles(state["articles"])
    assert serialized["a827"]["launch_anchor_policy"] == "bapi_multi_contract_strict"
    assert serialized["a827"]["required_launch_anchor_source"] == "detail_per_symbol_time_or_exchangeinfo_onboard"

    file_path = tmp_path / "detail_retry_scheduler_state.json"
    file_path.write_text(json.dumps({"metadata_version": 2, "articles": serialized, "endpoint_health": {}}))
    loaded = load_detail_retry_scheduler_state(tmp_path)
    assert loaded["articles"]["a827"]["launch_anchor_policy"] == "bapi_multi_contract_strict"


def test_live_trading_enabled_hard_invariant():
    assert RiskLimits.live_trading_enabled is False
