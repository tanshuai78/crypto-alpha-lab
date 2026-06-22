from src.research.external_signal_shadow.stage1_5a_source_audit_models import (
    ExternalSignalEventType,
    RawSourcePayload,
    SourceProfile,
    TimestampQuality,
)
from src.research.external_signal_shadow.stage1_5a_source_audit_normalizer import (
    normalize_payload,
)


def test_binance_html_profile_extracts_title_url_and_published_time_from_fixture():
    # GIVEN
    html_content = b"""
    <html>
      <body>
        <div class="title">Binance Will Delist DREP, MOB, PNT on 2024-04-03</div>
        <div class="time">2024-03-20 08:00:00</div>
        <a href="/en/support/announcement/drep-mob-pnt-delisting">Link</a>
      </body>
    </html>
    """
    payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile=SourceProfile.BINANCE_HTML.value,
        source_url="https://binance.com/announcements",
        source_parent_url="https://binance.com",
        raw_payload_bytes=html_content,
        collector_received_at_ms=1710921600000,
        content_type="text/html",
    )

    # WHEN
    events, metrics = normalize_payload(payload)

    # THEN
    assert len(events) == 3  # DREP, MOB, PNT
    assert events[0].event_type == ExternalSignalEventType.DELISTING.value
    assert events[0].symbol in ("DREPUSDT", "MOBUSDT", "PNTUSDT")
    assert events[0].base_asset in ("DREP", "MOB", "PNT")
    assert events[0].source_timestamp_quality == TimestampQuality.MEDIUM.value  # Extracted from html page time
    assert events[0].raw_payload_hash != events[0].event_payload_hash


def test_okx_html_profile_extracts_title_url_and_published_time_from_fixture():
    # GIVEN
    html_content = b"""
    <html>
      <body>
        <h1>OKX to Delist ABC and XYZ Trading Pairs on 2024-04-05</h1>
        <p>Published: 2024-03-22 09:00:00</p>
        <div class="detail-link"><a href="/help/okx-to-delist-pairs">Detail</a></div>
      </body>
    </html>
    """
    payload = RawSourcePayload(
        source_name="okx_announcements",
        source_profile=SourceProfile.OKX_HTML.value,
        source_url="https://okx.com/announcements",
        source_parent_url="https://okx.com",
        raw_payload_bytes=html_content,
        collector_received_at_ms=1711094400000,
        content_type="text/html",
    )

    # WHEN
    events, metrics = normalize_payload(payload)

    # THEN
    assert metrics["source_format_drift_count"] == 0
    assert len(events) == 2
    assert events[0].event_type == ExternalSignalEventType.DELISTING.value
    assert events[0].source_url == "/help/okx-to-delist-pairs"
    assert events[0].source_published_at_ms == 1711098000000
    assert {event.symbol for event in events} == {"ABCUSDT", "XYZUSDT"}


def test_normalizes_official_announcement_like_row():
    # GIVEN a JSON row from API
    row_bytes = b'{"title": "Binance Futures Will Launch USD-M YGG Permanent Contract", "time": 1710921600000, "url": "https://binance.com/announcement/ygg"}'
    payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile=SourceProfile.BINANCE_API_ROWS.value,
        source_url="https://binance.com/announcements",
        source_parent_url="https://binance.com",
        raw_payload_bytes=row_bytes,
        collector_received_at_ms=1710921605000,
        content_type="application/json",
    )

    # WHEN
    events, metrics = normalize_payload(payload)

    # THEN
    assert len(events) == 1
    assert events[0].event_type == ExternalSignalEventType.FUTURES_LAUNCH.value
    assert events[0].symbol == "YGGUSDT"
    assert events[0].base_asset == "YGG"
    assert events[0].available_at_ms == 1710921600000 + 15 * 60 * 1000
    assert events[0].source_timestamp_quality == TimestampQuality.HIGH.value


def test_timestamp_source_disagreement_increments_counter():
    # GIVEN a row with differing API publish time vs page publish time
    row_bytes = b'{"title": "Binance Will Delist MOB", "api_time": 1710921600000, "html_time": 1710921500000}'
    payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile=SourceProfile.BINANCE_API_ROWS.value,
        source_url="https://binance.com/announcements",
        source_parent_url="https://binance.com",
        raw_payload_bytes=row_bytes,
        collector_received_at_ms=1710921605000,
    )

    # WHEN
    events, metrics = normalize_payload(payload)

    # THEN
    assert metrics["timestamp_source_disagreement_count"] == 1


def test_low_timestamp_quality_becomes_observation_only():
    # GIVEN a row where time is missing and we infer it from url / system receipt (low quality)
    row_bytes = b'{"title": "Binance Will Delist MOB", "url": "https://binance.com/announcement/mob"}'
    payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile=SourceProfile.BINANCE_API_ROWS.value,
        source_url="https://binance.com/announcements",
        source_parent_url="https://binance.com",
        raw_payload_bytes=row_bytes,
        collector_received_at_ms=1710921605000,
    )

    # WHEN
    events, metrics = normalize_payload(payload)

    # THEN
    assert len(events) == 1
    assert events[0].source_timestamp_quality == TimestampQuality.LOW.value
    assert events[0].observation_only is True
    assert events[0].replay_allowed is False


def test_unlock_without_calendar_snapshot_is_observation_only():
    row_bytes = b'{"title": "Unlock event for DYDX", "symbol": "DYDX", "amount": 1000000}'
    payload = RawSourcePayload(
        source_name="defillama_unlocks",
        source_profile=SourceProfile.UNLOCK_ROWS.value,
        source_url="https://defillama.com/unlocks",
        source_parent_url="https://defillama.com",
        raw_payload_bytes=row_bytes,
        collector_received_at_ms=1710921605000,
    )
    events, metrics = normalize_payload(payload)
    assert len(events) == 1
    assert events[0].event_type == ExternalSignalEventType.MAJOR_UNLOCK.value
    assert events[0].observation_only is True
    assert events[0].hindsight_risk is True
    assert events[0].replay_allowed is False


def test_new_coin_listing_is_excluded():
    row_bytes = b'{"title": "Binance Will List New Coin TokenX", "time": 1710921600000}'
    payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile=SourceProfile.BINANCE_API_ROWS.value,
        source_url="https://binance.com/announcements",
        source_parent_url="https://binance.com",
        raw_payload_bytes=row_bytes,
        collector_received_at_ms=1710921605000,
    )
    events, metrics = normalize_payload(payload)
    assert len(events) == 1
    assert events[0].event_type == ExternalSignalEventType.NEW_COIN.value
    # new_coin_listing is observation-only
    assert events[0].observation_only is True
    assert events[0].replay_allowed is False


def test_ambiguous_symbol_mapping_is_quarantined():
    # GIVEN a row where symbol mapping is ambiguous (e.g. BTC vs WBTC, or token name matches multiple symbols)
    row_bytes = b'{"title": "Binance Will Delist PEPE", "symbol": "PEPE/WBTC/USDT"}'
    payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile=SourceProfile.BINANCE_API_ROWS.value,
        source_url="https://binance.com/announcements",
        source_parent_url="https://binance.com",
        raw_payload_bytes=row_bytes,
        collector_received_at_ms=1710921605000,
    )
    events, metrics = normalize_payload(payload)
    assert len(events) == 1
    assert "ambiguous_symbol" in events[0].quarantine_reasons
    assert events[0].replay_allowed is False


def test_unknown_event_type_is_quarantined_and_not_replay_allowed():
    row_bytes = (
        b'{"title": "Binance Announces Random Partnership With ABC", '
        b'"time": 1710921600000, "symbol": "ABC"}'
    )
    payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile=SourceProfile.BINANCE_API_ROWS.value,
        source_url="https://binance.com/announcements",
        source_parent_url="https://binance.com",
        raw_payload_bytes=row_bytes,
        collector_received_at_ms=1710921605000,
    )

    events, metrics = normalize_payload(payload)

    assert len(events) == 1
    assert events[0].event_type == "unknown"
    assert "unsupported_event_type" in events[0].quarantine_reasons
    assert events[0].observation_only is True
    assert events[0].replay_allowed is False
