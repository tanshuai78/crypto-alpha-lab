from src.research.external_signal_shadow.stage1_5a_source_audit_models import (
    ExternalSignalEventType,
    ExternalSignalSourceAuditDecision,
    NormalizedExternalEvent,
    SourceProfile,
    TimestampQuality,
)


def test_enums_exist_and_contain_expected_values():
    # GIVEN / WHEN / THEN
    assert ExternalSignalSourceAuditDecision.PASSED.value == "source_audit_passed"
    assert ExternalSignalSourceAuditDecision.SPARSE.value == "source_audit_sparse_inconclusive"
    assert ExternalSignalSourceAuditDecision.FAILED.value == "source_audit_failed"

    assert ExternalSignalEventType.DELISTING.value == "exchange_delisting_notice"
    assert ExternalSignalEventType.FUTURES_LAUNCH.value == "futures_contract_launch"
    assert ExternalSignalEventType.MARGIN_ENABLE.value == "margin_enablement"
    assert ExternalSignalEventType.TRADING_PAIR_REMOVAL.value == "trading_pair_removal"
    assert (
        ExternalSignalEventType.TRADING_PAIR_ADDITION.value
        == "trading_pair_addition_for_existing_liquid_asset"
    )
    assert ExternalSignalEventType.EXCHANGE_STATUS.value == "major_exchange_status_event"
    assert ExternalSignalEventType.MAJOR_UNLOCK.value == "major_unlock_event"
    assert ExternalSignalEventType.TOKEN_EMISSION.value == "large_scheduled_token_emission"
    assert ExternalSignalEventType.NEW_COIN.value == "new_coin_listing"
    assert ExternalSignalEventType.WHALE_DEPOSIT.value == "whale_deposit"

    assert TimestampQuality.HIGH.value == "high"
    assert TimestampQuality.MEDIUM.value == "medium"
    assert TimestampQuality.LOW.value == "low"

    assert SourceProfile.GENERIC_JSON.value == "generic_json_announcement_rows"
    assert SourceProfile.BINANCE_API_ROWS.value == "binance_official_announcements_like_rows"
    assert SourceProfile.BINANCE_HTML.value == "binance_announcement_index_like_html"
    assert SourceProfile.OKX_API_ROWS.value == "okx_official_announcements_like_rows"
    assert SourceProfile.OKX_HTML.value == "okx_announcement_index_like_html"
    assert SourceProfile.UNLOCK_ROWS.value == "unlock_calendar_like_rows"


def test_normalized_event_fields():
    event = NormalizedExternalEvent(
        event_id="test-123",
        event_type=ExternalSignalEventType.DELISTING.value,
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        venue="binance",
        source_name="binance_announcements",
        source_domain="binance.com",
        source_url="https://binance.com/en/support/announcement/123",
        source_parent_url="https://binance.com/en/support/announcement/list",
        source_published_at_ms=1600000000000,
        event_time_ms=1600000000000,
        available_at_ms=1600000900000,
        collector_received_at_ms=1600000901000,
        raw_payload_hash="hash-123",
        event_payload_hash="event-hash-123",
        raw_payload_size_bytes=1024,
        detail_url_available=True,
        source_integrity_level="full_detail",
        schema_version="v1",
        source_timestamp_quality="high",
        historical_available_at_confidence="high",
        edited_page_risk=False,
        hindsight_risk=False,
        magnitude=1.0,
        base_asset_mapping_status="pass",
        trade_pair_mapping_status="pass",
        quarantine_reasons=[],
        replay_allowed=True,
        observation_only=False,
    )
    assert event.event_id == "test-123"
    assert event.replay_allowed is True
