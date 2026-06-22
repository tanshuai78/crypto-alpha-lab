from src.research.external_signal_shadow.stage1_5a_source_audit_models import RawSourcePayload
from src.research.external_signal_shadow.stage1_5a_source_audit_safety import (
    compute_payload_sha256,
    detect_forbidden_payload_keys,
    measure_json_depth,
    normalize_source_domain,
    validate_domain_allowlist,
    validate_source_resource_safety,
)


def test_normalize_source_domain():
    assert normalize_source_domain("https://binance.com/en/support") == "binance.com"
    assert normalize_source_domain("http://www.binance.com/path?query=1") == "www.binance.com"
    assert normalize_source_domain("http://announcements.binance.com") == "announcements.binance.com"
    assert normalize_source_domain("binance.com") == "binance.com"


def test_validate_domain_allowlist():
    allowed = ("binance.com", "okx.com")

    # Valid
    assert validate_domain_allowlist("https://binance.com", allowed) is True
    assert validate_domain_allowlist("https://www.binance.com", allowed) is True
    assert validate_domain_allowlist("https://sub.okx.com/en", allowed) is True

    # Invalid / Spoofing
    assert validate_domain_allowlist("https://evil-binance.com", allowed) is False
    assert validate_domain_allowlist("https://binance.com.evil.io", allowed) is False
    assert validate_domain_allowlist("https://okx.com.co", allowed) is False


def test_measure_json_depth():
    assert measure_json_depth({"a": 1}) == 1
    assert measure_json_depth({"a": {"b": 2}}) == 2
    assert measure_json_depth({"a": [{"b": {"c": 3}}]}) == 3


def test_detect_forbidden_payload_keys():
    # Simple dict
    assert detect_forbidden_payload_keys({"api_key": "123"}) == ["api_key"]
    # Nested dict
    assert detect_forbidden_payload_keys({"data": {"nested": {"secret": "xyz"}}}) == ["secret"]
    # List of dicts
    assert detect_forbidden_payload_keys([{"normal": 1}, {"bearer": "token"}]) == ["bearer"]


def test_compute_payload_sha256():
    payload = b"hello world"
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert compute_payload_sha256(payload) == expected


def test_validate_source_resource_safety():
    # Valid payload
    payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile="generic_json_announcement_rows",
        source_url="https://binance.com/announcement",
        source_parent_url="https://binance.com",
        raw_payload_bytes=b'{"title": "Delisting notice"}',
        collector_received_at_ms=1600000000000,
    )
    findings = validate_source_resource_safety(payload)
    assert len(findings) == 0

    # Payload too large
    large_payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile="generic_json_announcement_rows",
        source_url="https://binance.com/announcement",
        source_parent_url="https://binance.com",
        raw_payload_bytes=b"x" * 3_000_000,  # 3MB > 2MB limit
        collector_received_at_ms=1600000000000,
    )
    findings = validate_source_resource_safety(large_payload)
    assert any(f.rule_id == "payload_too_large" for f in findings)

    # Allowed domain violation
    disallowed_payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile="generic_json_announcement_rows",
        source_url="https://evil-binance.com/announcement",
        source_parent_url="https://binance.com",
        raw_payload_bytes=b'{"title": "Delisting notice"}',
        collector_received_at_ms=1600000000000,
    )
    findings = validate_source_resource_safety(disallowed_payload)
    assert any(f.rule_id == "disallowed_domain" for f in findings)

    # Forbidden key presence
    forbidden_payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile="generic_json_announcement_rows",
        source_url="https://binance.com/announcement",
        source_parent_url="https://binance.com",
        raw_payload_bytes=b'{"title": "Delisting notice", "api_key": "secret_val"}',
        collector_received_at_ms=1600000000000,
    )
    findings = validate_source_resource_safety(forbidden_payload)
    assert any(f.rule_id == "forbidden_payload" for f in findings)

    # Deep JSON nesting
    deep_json = b'{"a":' * 10 + b"1" + b"}" * 10
    deep_payload = RawSourcePayload(
        source_name="binance_announcements",
        source_profile="generic_json_announcement_rows",
        source_url="https://binance.com/announcement",
        source_parent_url="https://binance.com",
        raw_payload_bytes=deep_json,
        collector_received_at_ms=1600000000000,
    )
    findings = validate_source_resource_safety(deep_payload)
    assert any(f.rule_id == "json_depth_exceeded" for f in findings)
