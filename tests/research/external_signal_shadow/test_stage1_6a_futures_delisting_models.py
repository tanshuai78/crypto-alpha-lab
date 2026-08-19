import hashlib

from src.research.external_signal_shadow.stage1_6a_futures_delisting_models import (
    CaptureTimeStatus,
    ContractType,
    FactParseStatus,
    MarginFamily,
    ScheduleFact,
    UnderlyingFamily,
    canonical_json_fingerprint,
    compute_delisting_contract_id,
    compute_detail_revision_id,
    compute_list_capture_id,
    compute_semantic_extraction_id,
)


def test_compute_list_capture_id():
    surface = "announcement_index"
    locale = "en"
    variant = "canonical_binance_english_index"
    raw_hash = hashlib.sha256(b"raw_list_bytes").hexdigest()

    lid = compute_list_capture_id(surface, locale, variant, raw_hash)
    expected = hashlib.sha256(f"{surface}|{locale}|{variant}|{raw_hash}".encode("utf-8")).hexdigest()
    assert lid == expected


def test_compute_detail_revision_id():
    aid = "1001"
    surface = "announcement_detail"
    locale = "en"
    variant = "canonical_binance_english_detail"
    raw_hash = hashlib.sha256(b"raw_detail_bytes").hexdigest()

    rev_id = compute_detail_revision_id(aid, surface, locale, variant, raw_hash)
    expected = hashlib.sha256(f"{aid}|{surface}|{locale}|{variant}|{raw_hash}".encode("utf-8")).hexdigest()
    assert rev_id == expected

    # Different locale or variant produces different revision ID
    diff_locale_id = compute_detail_revision_id(aid, surface, "zh-CN", variant, raw_hash)
    assert diff_locale_id != rev_id


def test_compute_semantic_extraction_id():
    rev_id = "rev_001"
    ext_ver = "stage1_6a_extractor_v1"
    norm_ver = "stage1_6a_norm_v1"
    fact_fp = canonical_json_fingerprint({"settle_ts": 1712000000000})

    extract_id = compute_semantic_extraction_id(rev_id, ext_ver, norm_ver, fact_fp)
    expected = hashlib.sha256(f"{rev_id}|{ext_ver}|{norm_ver}|{fact_fp}".encode("utf-8")).hexdigest()
    assert extract_id == expected


def test_compute_delisting_contract_id():
    aid = "1001"
    rev_id = "rev_001"
    symbol = "MOBUSDT"
    margin = MarginFamily.USD_M.value
    contract_type = ContractType.PERPETUAL.value
    underlying = UnderlyingFamily.CRYPTO_ASSET.value

    cid = compute_delisting_contract_id(aid, rev_id, symbol, margin, contract_type, underlying)
    expected = hashlib.sha256(f"{aid}|{rev_id}|{symbol}|{margin}|{contract_type}|{underlying}".encode("utf-8")).hexdigest()
    assert cid == expected


def test_schedule_fact_explicit_nullable_available_at_ms():
    """Verify ScheduleFact contains explicit nullable fact_available_at_ms per P1-A."""
    fact = ScheduleFact(
        fact_parse_status=FactParseStatus.PRESENT.value,
        capture_time_status=CaptureTimeStatus.HISTORICAL_UNKNOWN.value,
        timestamp_ms=1712134800000,
        fact_available_at_ms=None,
    )
    d = fact.to_dict()
    assert "fact_available_at_ms" in d
    assert d["fact_available_at_ms"] is None
