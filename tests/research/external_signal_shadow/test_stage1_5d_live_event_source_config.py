from configs import base


def test_stage1_5d_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_BASE_URL == "https://www.binance.com"
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_LIST_PATH
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_ANNOUNCEMENT_QUERY_PARAMS == {
        "type": "1",
        "pageNo": "1",
        "pageSize": "50",
    }
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_DOMAINS == ("binance.com", "www.binance.com")
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE == "futures_contract_launch"
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_ANNOUNCEMENT_DELAY_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DEFAULT_POLL_INTERVAL_SEC == 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_REQUEST_TIMEOUT_SEC == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RETRY_BUDGET == 2
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MIN_OPERATIONAL_OBSERVATION_HOURS == 24
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MIN_POLL_SUCCESS_RATE == 0.95
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_OBSERVATION_TIMEOUT_HOURS == 24
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_CHECK_BUDGET_PER_POLL >= 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RAW_PAYLOAD_RETENTION_DAYS >= 14
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MAX_RAW_PAYLOAD_BYTES_PER_DAY > 0


def test_stage1_5d_detail_fallback_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_REQUEST_TIMEOUT_SEC == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC == 3600


def test_stage1_5d_u_settlement_contract_config_constants():
    assert "U" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS
    assert "USDT" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS
    assert "U" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS
    assert "PERPETUAL" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES
    assert "TRADIFI_PERPETUAL" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES
    assert "PENDING_TRADING" in base.EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_EMITTABLE_SYMBOL_STATUSES == ("TRADING",)
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_GRACE_AFTER_LAUNCH_SEC >= 30 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_MAX_TOTAL_SEC >= 12 * 60 * 60


def test_stage1_5d_allows_usd1_futures_assets_for_exchangeinfo_validated_contracts():
    assert "USD1" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS
    assert "USD1" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS


def test_stage1_5d_transient_detail_fetch_max_age_config():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC == 86400


def test_stage1_5d_detail_scheduler_fairness_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS == 10 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS > 0


def test_stage1_5d_detail_scheduler_backoff_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC == 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC == 3600
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC >= base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_NEVER_ATTEMPTED_MAX_DEFER_SEC == 10 * 60


def test_stage1_5d_detail_endpoint_degraded_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD == 0.80
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE == 5
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC == 15 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEFERRED_MANIFEST_MIN_INTERVAL_SEC == 15 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION == 3


def validate_stage1_5d_v3_config_delta_for_plan(before: str, after: str) -> bool:
    import ast

    try:
        before_nodes = ast.parse(before).body
        after_nodes = ast.parse(after).body
    except Exception:
        return False

    if len(after_nodes) != len(before_nodes) + 1:
        return False

    metadata = "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION"
    clock_skew = "EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS"

    target_idx = None
    for idx, node in enumerate(before_nodes):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == metadata
        ):
            target_idx = idx
            break

    if target_idx is None:
        return False

    for b_node, a_node in zip(before_nodes[:target_idx], after_nodes[:target_idx]):
        if ast.dump(b_node, include_attributes=False) != ast.dump(a_node, include_attributes=False):
            return False

    b_meta = before_nodes[target_idx]
    a_meta = after_nodes[target_idx]
    if not (isinstance(b_meta, ast.Assign) and isinstance(a_meta, ast.Assign)):
        return False
    if len(b_meta.targets) != 1 or len(a_meta.targets) != 1:
        return False
    if not (isinstance(b_meta.targets[0], ast.Name) and isinstance(a_meta.targets[0], ast.Name)):
        return False
    if b_meta.targets[0].id != metadata or a_meta.targets[0].id != metadata:
        return False
    if not (isinstance(b_meta.value, ast.Constant) and b_meta.value.value == 2):
        return False
    if not (isinstance(a_meta.value, ast.Constant) and a_meta.value.value == 3):
        return False

    inserted = after_nodes[target_idx + 1]
    if not (isinstance(inserted, ast.Assign) and len(inserted.targets) == 1):
        return False
    if not (isinstance(inserted.targets[0], ast.Name) and inserted.targets[0].id == clock_skew):
        return False
    expected_skew_ast = ast.parse("x = 30 * 1000").body[0].value
    if ast.dump(inserted.value, include_attributes=False) != ast.dump(expected_skew_ast, include_attributes=False):
        return False

    for b_node, a_node in zip(before_nodes[target_idx + 1:], after_nodes[target_idx + 2:]):
        if ast.dump(b_node, include_attributes=False) != ast.dump(a_node, include_attributes=False):
            return False

    return True


def test_stage1_5d_v3_config_authorities_are_exact():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS == 30 * 1000


def test_validate_stage1_5d_v3_config_delta_for_plan_allows_only_frozen_delta():
    before = """\
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION = 2
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False
"""
    after = """\
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION = 3
EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS = 30 * 1000
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False
"""
    assert validate_stage1_5d_v3_config_delta_for_plan(before, after) is True
    assert validate_stage1_5d_v3_config_delta_for_plan(
        after, after.replace("30 * 1000", "30 * 1001")
    ) is False
    assert validate_stage1_5d_v3_config_delta_for_plan(
        after, after + "EXTRA = 1\n"
    ) is False
    assert validate_stage1_5d_v3_config_delta_for_plan(
        before, before
    ) is False


def test_stage1_5d_detail_degraded_recent_retry_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_ARTICLE_WINDOW_SEC == 3 * 60 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_INTERVAL_SEC == 10 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_BUDGET_PER_POLL == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_MAX_CYCLES == 6
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FALLBACK_MAX_URLS_PER_ARTICLE == 2


def test_stage1_5d_detail_overdue_retry_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_RETRY_BUDGET_PER_POLL == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_MIN_INTERVAL_SEC == 10 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_WARN_SEC == 30 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_HARD_WARN_SEC == 2 * 60 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_RETRY_BUDGET_PER_POLL > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL >= 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_HARD_WARN_SEC > base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_WARN_SEC


def test_stage1_5d_bapi_article_detail_source_config():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_DETAIL_PATH == "/bapi/composite/v1/public/cms/article/detail/query"
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_CODE_PATTERN == r"^[0-9a-fA-F]{32}$"
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES >= 500_000
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_JSON_DEPTH >= 20
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_NODE_COUNT >= 10_000
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_EXTRACTED_TEXT_CHARS >= 100_000
    assert (
        base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_SYMBOL_CANDIDATES
        == base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MAX_DETAIL_SOURCE_VARIANTS_PER_CYCLE >= 4
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_RETRY_INTERVAL_SEC > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_MAX_AGE_SEC >= 12 * 60 * 60


def test_bapi_launch_schedule_parser_config_defaults():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_SCHEDULE_LINE_LOOKAHEAD == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MAX_LAUNCH_TIME_DISAGREEMENT_MS == 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_NO_SYMBOL_RECHECK_INTERVAL_SEC >= 3600

