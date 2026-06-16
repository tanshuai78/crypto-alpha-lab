"""
src/research/external_signal_shadow/stage1_4a2_vendor.py
"""
import csv
import gzip
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from configs import base


@dataclass(frozen=True)
class VendorLiquidationAudit:
    vendor: str
    priority: str
    source_surface: str
    evidence_level: str
    evidence_urls: list[str]
    evidence_retrieved_at: str
    audit_time_ms: int
    sample_access_type: str
    payment_required_before_sample: bool
    sales_contact_required: bool
    api_key_required_for_sample: bool
    sample_file_available: bool
    sample_file_path: str | None
    sample_file_audited: bool
    sample_audit_row_count: int
    sample_audit_history_days: float
    explicit_user_approval_for_trial: bool
    explicit_user_approval_for_paid_sample: bool
    explicit_user_cost_approval: bool
    license_status: str
    license_allows_local_research: bool
    license_allows_backtesting: bool
    license_allows_local_storage: bool
    license_allows_derived_metrics: bool
    redistribution_forbidden: bool
    history_days_claimed: float
    history_days_verified_from_sample: float
    symbols_claimed: list[str]
    symbols_verified: list[str]
    exchange_scope: str
    binance_usdm_exact: bool
    includes_coin_margined: bool
    includes_usd_margined: bool
    multi_exchange_aggregate: bool
    exchange_filter_available: bool
    timestamp_resolution_ms: int
    side_available: bool
    side_semantics: str
    long_liquidation_mapping: str
    short_liquidation_mapping: str
    side_mapping_confidence: str
    notional_usd_available: bool
    price_available: bool
    quantity_available: bool
    exchange_field_available: bool
    symbol_field_available: bool
    timestamp_field_available: bool
    download_or_export_format: str
    source_granularity: str
    replay_anchor_policy: str
    available_at_policy_defined: bool
    field_mapping_status: str
    stage1_4a1_alignment_status: str
    cost_tier: str
    personal_investor_feasible_cost: bool
    estimated_cost_usd_per_month: float
    manual_notes: list[str]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VendorLiquidationAudit":
        # Check all expected fields are present
        required_fields = {
            "vendor", "priority", "source_surface", "evidence_level", "evidence_urls",
            "evidence_retrieved_at", "audit_time_ms", "sample_access_type",
            "payment_required_before_sample", "sales_contact_required", "api_key_required_for_sample",
            "sample_file_available", "sample_file_path", "sample_file_audited",
            "sample_audit_row_count", "sample_audit_history_days", "explicit_user_approval_for_trial",
            "explicit_user_approval_for_paid_sample", "explicit_user_cost_approval",
            "license_status", "license_allows_local_research", "license_allows_backtesting",
            "license_allows_local_storage", "license_allows_derived_metrics", "redistribution_forbidden",
            "history_days_claimed", "history_days_verified_from_sample", "symbols_claimed",
            "symbols_verified", "exchange_scope", "binance_usdm_exact", "includes_coin_margined",
            "includes_usd_margined", "multi_exchange_aggregate", "exchange_filter_available",
            "timestamp_resolution_ms", "side_available", "side_semantics", "long_liquidation_mapping",
            "short_liquidation_mapping", "side_mapping_confidence", "notional_usd_available",
            "price_available", "quantity_available", "exchange_field_available",
            "symbol_field_available", "timestamp_field_available", "download_or_export_format",
            "source_granularity", "replay_anchor_policy", "available_at_policy_defined",
            "field_mapping_status", "stage1_4a1_alignment_status", "cost_tier",
            "personal_investor_feasible_cost", "estimated_cost_usd_per_month", "manual_notes"
        }
        for field in required_fields:
            if field not in d:
                raise ValueError(f"Missing required field: {field}")

        # Allowed values validation
        vendor = d["vendor"]
        if vendor not in base.EXTERNAL_SIGNAL_STAGE1_4A2_VENDOR_ORDER:
            raise ValueError(f"vendor must be one of {base.EXTERNAL_SIGNAL_STAGE1_4A2_VENDOR_ORDER}")

        source_surface = d["source_surface"]
        allowed_source_surfaces = {
            "marketing_page", "official_api_docs", "pricing_page", "public_sample",
            "trial_export", "sales_reply", "manual_vendor_reply"
        }
        if source_surface not in allowed_source_surfaces:
            raise ValueError(f"source_surface must be in {allowed_source_surfaces}")

        evidence_level = d["evidence_level"]
        allowed_evidence_levels = {"marketing_page", "official_api_docs", "sample_schema", "sample_rows", "trial_export"}
        if evidence_level not in allowed_evidence_levels:
            raise ValueError(f"evidence_level must be in {allowed_evidence_levels}")

        sample_access_type = d["sample_access_type"]
        allowed_sample_access_types = {"public_sample", "free_trial", "sales_provided_sample", "paid_plan_required", "unknown"}
        if sample_access_type not in allowed_sample_access_types:
            raise ValueError(f"sample_access_type must be in {allowed_sample_access_types}")

        license_status = d["license_status"]
        allowed_license_statuses = {"clear", "unknown", "restricted", "disallowed"}
        if license_status not in allowed_license_statuses:
            raise ValueError(f"license_status must be in {allowed_license_statuses}")

        exchange_scope = d["exchange_scope"]
        allowed_exchange_scopes = {"binance_usdm", "multi_exchange", "aggregated_unknown"}
        if exchange_scope not in allowed_exchange_scopes:
            raise ValueError(f"exchange_scope must be in {allowed_exchange_scopes}")

        side_mapping_confidence = d["side_mapping_confidence"]
        allowed_side_confidences = {"verified", "inferred_from_official_docs", "unknown"}
        if side_mapping_confidence not in allowed_side_confidences:
            raise ValueError(f"side_mapping_confidence must be in {allowed_side_confidences}")

        source_granularity = d["source_granularity"]
        allowed_granularities = {"tick", "1m", "5m", "15m", "1h", "daily", "unknown"}
        if source_granularity not in allowed_granularities:
            raise ValueError(f"source_granularity must be in {allowed_granularities}")

        replay_anchor_policy = d["replay_anchor_policy"]
        allowed_policies = {"event_time_plus_lag", "bucket_end_plus_lag", "not_intraday_usable", "unknown"}
        if replay_anchor_policy not in allowed_policies:
            raise ValueError(f"replay_anchor_policy must be in {allowed_policies}")

        cost_tier = d["cost_tier"]
        allowed_cost_tiers = {"free", "low", "medium", "high", "enterprise_unknown"}
        if cost_tier not in allowed_cost_tiers:
            raise ValueError(f"cost_tier must be in {allowed_cost_tiers}")

        if not isinstance(d["evidence_urls"], list) or len(d["evidence_urls"]) == 0:
            raise ValueError("evidence_urls must be a non-empty list")

        if not d["evidence_retrieved_at"]:
            raise ValueError("evidence_retrieved_at must be non-empty")

        if not isinstance(d["manual_notes"], list):
            raise ValueError("manual_notes must be a list")

        if not isinstance(d["symbols_claimed"], list):
            raise ValueError("symbols_claimed must be a list")
        if not isinstance(d["symbols_verified"], list):
            raise ValueError("symbols_verified must be a list")

        if d["sample_file_available"]:
            if not d["sample_file_path"] or not isinstance(d["sample_file_path"], str):
                raise ValueError("sample_file_path must be a non-empty string when sample_file_available is true")
            # Explicit sample audit metadata fields must exist
            if d.get("sample_audit_row_count", 0) <= 0:
                raise ValueError("sample_audit_row_count must be > 0 when sample_file_available is true")
            if d.get("sample_audit_history_days", 0.0) <= 0.0:
                raise ValueError("sample_audit_history_days must be > 0.0 when sample_file_available is true")

        # Create instance
        return cls(
            vendor=vendor,
            priority=d["priority"],
            source_surface=source_surface,
            evidence_level=evidence_level,
            evidence_urls=list(d["evidence_urls"]),
            evidence_retrieved_at=d["evidence_retrieved_at"],
            audit_time_ms=d["audit_time_ms"],
            sample_access_type=sample_access_type,
            payment_required_before_sample=d["payment_required_before_sample"],
            sales_contact_required=d["sales_contact_required"],
            api_key_required_for_sample=d["api_key_required_for_sample"],
            sample_file_available=d["sample_file_available"],
            sample_file_path=d["sample_file_path"],
            sample_file_audited=d["sample_file_audited"],
            sample_audit_row_count=d["sample_audit_row_count"],
            sample_audit_history_days=d["sample_audit_history_days"],
            explicit_user_approval_for_trial=d["explicit_user_approval_for_trial"],
            explicit_user_approval_for_paid_sample=d["explicit_user_approval_for_paid_sample"],
            explicit_user_cost_approval=d["explicit_user_cost_approval"],
            license_status=license_status,
            license_allows_local_research=d["license_allows_local_research"],
            license_allows_backtesting=d["license_allows_backtesting"],
            license_allows_local_storage=d["license_allows_local_storage"],
            license_allows_derived_metrics=d["license_allows_derived_metrics"],
            redistribution_forbidden=d["redistribution_forbidden"],
            history_days_claimed=d["history_days_claimed"],
            history_days_verified_from_sample=d["history_days_verified_from_sample"],
            symbols_claimed=list(d["symbols_claimed"]),
            symbols_verified=list(d["symbols_verified"]),
            exchange_scope=exchange_scope,
            binance_usdm_exact=d["binance_usdm_exact"],
            includes_coin_margined=d["includes_coin_margined"],
            includes_usd_margined=d["includes_usd_margined"],
            multi_exchange_aggregate=d["multi_exchange_aggregate"],
            exchange_filter_available=d["exchange_filter_available"],
            timestamp_resolution_ms=d["timestamp_resolution_ms"],
            side_available=d["side_available"],
            side_semantics=d["side_semantics"],
            long_liquidation_mapping=d["long_liquidation_mapping"],
            short_liquidation_mapping=d["short_liquidation_mapping"],
            side_mapping_confidence=side_mapping_confidence,
            notional_usd_available=d["notional_usd_available"],
            price_available=d["price_available"],
            quantity_available=d["quantity_available"],
            exchange_field_available=d["exchange_field_available"],
            symbol_field_available=d["symbol_field_available"],
            timestamp_field_available=d["timestamp_field_available"],
            download_or_export_format=d["download_or_export_format"],
            source_granularity=source_granularity,
            replay_anchor_policy=replay_anchor_policy,
            available_at_policy_defined=d["available_at_policy_defined"],
            field_mapping_status=d["field_mapping_status"],
            stage1_4a1_alignment_status=d["stage1_4a1_alignment_status"],
            cost_tier=cost_tier,
            personal_investor_feasible_cost=d["personal_investor_feasible_cost"],
            estimated_cost_usd_per_month=d["estimated_cost_usd_per_month"],
            manual_notes=list(d["manual_notes"]),
        )


def load_vendor_audits_json(path: str | Path) -> list[VendorLiquidationAudit]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Root of audits JSON must be a list")
    return [VendorLiquidationAudit.from_dict(item) for item in data]


@dataclass(frozen=True)
class VendorAuditDecision:
    vendor: str
    decision: str
    primary_blocker: str | None
    next_action: str
    feasible_for_stage1_4a3_parser: bool
    partial_diagnostic_allowed: bool


def decide_vendor_audit(audit: VendorLiquidationAudit) -> VendorAuditDecision:
    # 1. evidence/sample gate
    if (audit.evidence_level in {"marketing_page", "official_api_docs", "sample_schema"}
            or not audit.sample_file_available
            or not audit.sample_file_path
            or not audit.sample_file_audited):
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="sample_not_available",
            next_action="request_sample_or_trial",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=False,
        )

    # 2. license gate
    if (audit.license_status not in {"clear"}
            or not audit.license_allows_local_research
            or not audit.license_allows_backtesting
            or not audit.license_allows_local_storage
            or not audit.license_allows_derived_metrics):
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="license_unclear_or_restricted",
            next_action="review_license_terms_or_contact_legal",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=audit.sample_file_available,
        )

    # 3. history_days gate
    if audit.history_days_verified_from_sample < base.EXTERNAL_SIGNAL_STAGE1_4A2_MIN_HISTORY_DAYS:
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="insufficient_history_days",
            next_action="request_longer_historical_sample_or_extend_collection",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=audit.sample_file_available,
        )

    # 4. symbol count gate
    if len(audit.symbols_verified) < base.EXTERNAL_SIGNAL_STAGE1_4A2_MIN_SYMBOLS_WITH_USABLE_DATA:
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="insufficient_symbols",
            next_action="request_expanded_symbol_coverage",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=audit.sample_file_available,
        )

    # 5. field gate
    if (not audit.side_available
            or not audit.notional_usd_available
            or not audit.symbol_field_available
            or not audit.timestamp_field_available):
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="missing_required_fields",
            next_action="request_complete_field_mapping",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=audit.sample_file_available,
        )

    # 6. side mapping confidence gate
    if audit.side_mapping_confidence not in {"verified", "inferred_from_official_docs"}:
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="side_mapping_uncertain",
            next_action="verify_side_mapping_via_manual_check",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=audit.sample_file_available,
        )

    # 7. timestamp/granularity/replay anchor gate
    if (audit.source_granularity == "daily"
            or audit.timestamp_resolution_ms > base.EXTERNAL_SIGNAL_STAGE1_4A2_MAX_TIMESTAMP_RESOLUTION_MS
            or audit.replay_anchor_policy in {"not_intraday_usable", "unknown"}):
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="granularity_not_suitable",
            next_action="request_intraday_resolution_data",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=audit.sample_file_available,
        )

    # 8. exchange scope / alignment gate
    if (not audit.binance_usdm_exact
            or audit.exchange_scope != "binance_usdm"
            or audit.stage1_4a1_alignment_status != "compatible"):
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="exchange_alignment_failed",
            next_action="align_exchange_scope_or_map_symbols",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=audit.sample_file_available,
        )

    # 9. cost gate
    if audit.sample_access_type == "paid_plan_required" and not audit.explicit_user_approval_for_paid_sample:
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="user_cost_decision_required",
            next_action="obtain_explicit_user_approval_for_paid_sample",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=audit.sample_file_available,
        )

    if audit.cost_tier in {"medium", "high", "enterprise_unknown"} and not audit.explicit_user_cost_approval:
        return VendorAuditDecision(
            vendor=audit.vendor,
            decision="vendor_liquidation_source_degraded",
            primary_blocker="user_cost_decision_required",
            next_action="obtain_explicit_user_cost_approval",
            feasible_for_stage1_4a3_parser=False,
            partial_diagnostic_allowed=audit.sample_file_available,
        )

    # 10. feasible
    return VendorAuditDecision(
        vendor=audit.vendor,
        decision="vendor_liquidation_source_feasible",
        primary_blocker=None,
        next_action="write_stage1_4a3_vendor_sample_parser_plan",
        feasible_for_stage1_4a3_parser=True,
        partial_diagnostic_allowed=True,
    )


def get_highest_data_quality_vendor(feasible_audits: list[VendorLiquidationAudit]) -> str | None:
    if not feasible_audits:
        return None
    # Filter for trial_export or sample_rows
    qualifying = [a for a in feasible_audits if a.evidence_level in {"trial_export", "sample_rows"}]
    if not qualifying:
        # Fallback to any feasible audit if none qualify
        qualifying = feasible_audits

    # We rank qualifying by:
    # 1. exact binance_usdm preferred: binance_usdm_exact is True
    # 2. history_days_verified_from_sample (higher is better)
    # 3. design order position (lower index is better)
    order_map = {name: idx for idx, name in enumerate(base.EXTERNAL_SIGNAL_STAGE1_4A2_VENDOR_ORDER)}

    def quality_key(a: VendorLiquidationAudit):
        # We want to maximize binance_usdm_exact and history_days_verified_from_sample, and minimize design order index
        return (
            not a.binance_usdm_exact, # False (0) comes before True (1), so exact is preferred
            -a.history_days_verified_from_sample, # larger history days comes first
            order_map.get(a.vendor, 999) # lower index comes first
        )

    sorted_quality = sorted(qualifying, key=quality_key)
    return sorted_quality[0].vendor


def build_vendor_feasibility_summary(audits: list[VendorLiquidationAudit]) -> dict[str, Any]:
    # Sort audits by design order
    order_map = {name: idx for idx, name in enumerate(base.EXTERNAL_SIGNAL_STAGE1_4A2_VENDOR_ORDER)}
    sorted_audits = sorted(audits, key=lambda a: order_map.get(a.vendor, 999))

    candidate_vendor_count = len(sorted_audits)

    # Compute decisions
    decisions = [decide_vendor_audit(a) for a in sorted_audits]
    feasible_audits = [a for a, dec in zip(sorted_audits, decisions) if dec.feasible_for_stage1_4a3_parser]
    feasible_vendor_count = len(feasible_audits)

    recommended_vendor_order = [a.vendor for a in sorted_audits]

    # Best vendor: first feasible vendor in design order
    best_vendor = feasible_audits[0].vendor if feasible_audits else None

    # Lowest cost usable vendor: feasible vendor with cost_tier in {"free", "low"}
    lowest_cost_usable_vendor = None
    for a in feasible_audits:
        if a.cost_tier in {"free", "low"}:
            lowest_cost_usable_vendor = a.vendor
            break

    # Highest data quality vendor
    highest_data_quality_vendor = get_highest_data_quality_vendor(feasible_audits)

    # Determine summary-level decision, blocker and next action
    if feasible_vendor_count > 0:
        decision = "vendor_liquidation_source_feasible"
        primary_blocker = None
        next_action = "write_stage1_4a3_vendor_sample_parser_plan"
    elif candidate_vendor_count > 0:
        decision = "vendor_liquidation_source_degraded"
        # Check if any candidate has a cost blocker
        has_cost_blocker = any(dec.primary_blocker == "user_cost_decision_required" for dec in decisions)
        if has_cost_blocker:
            primary_blocker = "user_cost_decision_required"
            next_action = "user_cost_decision_required"
        else:
            primary_blocker = "no_feasible_vendor_sample"
            next_action = "request_sample_or_trial_from_top_ranked_vendor_or_continue_live_collection"
    else:
        decision = "vendor_liquidation_source_unavailable"
        primary_blocker = "no_vendor_audits_available"
        next_action = "request_sample_or_trial_from_top_ranked_vendor_or_continue_live_collection"

    import dataclasses

    vendor_audits_payloads = [dataclasses.asdict(a) for a in sorted_audits]
    vendor_decisions_payloads = [dataclasses.asdict(d) for d in decisions]

    return {
        "decision": decision,
        "primary_blocker": primary_blocker,
        "candidate_vendor_count": candidate_vendor_count,
        "feasible_vendor_count": feasible_vendor_count,
        "recommended_vendor_order": recommended_vendor_order,
        "best_vendor": best_vendor,
        "lowest_cost_usable_vendor": lowest_cost_usable_vendor,
        "highest_data_quality_vendor": highest_data_quality_vendor,
        "purchase_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "stage1_4b_candidate_replay_allowed": False,
        "vendor_audits": vendor_audits_payloads,
        "vendor_decisions": vendor_decisions_payloads,
        "next_action": next_action,
    }


def _line_generator(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            yield from f
    elif suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            name = z.namelist()[0]
            with z.open(name, "r") as f_bytes:
                import io
                f = io.TextIOWrapper(f_bytes, encoding="utf-8")
                yield from f
    else:
        with open(path, "r", encoding="utf-8") as f:
            yield from f


def _parse_timestamp_to_ms(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if val > 5e10:
            return float(val)
        else:
            return float(val) * 1000.0
    if isinstance(val, str):
        try:
            f_val = float(val)
            if f_val > 5e10:
                return f_val
            else:
                return f_val * 1000.0
        except ValueError:
            pass
        import datetime
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
        ):
            try:
                dt = datetime.datetime.strptime(val, fmt)
                return dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000.0
            except ValueError:
                continue
    return None


def _load_rows_from_file(path: Path) -> list[dict]:
    import json
    import zipfile

    name_lower = path.name.lower()
    is_gz = name_lower.endswith(".gz")
    is_zip = name_lower.endswith(".zip")

    if is_gz:
        stem = path.stem
        is_csv = stem.lower().endswith(".csv")
    elif is_zip:
        with zipfile.ZipFile(path) as z:
            inner_name = z.namelist()[0].lower()
            is_csv = inner_name.endswith(".csv")
    else:
        is_csv = name_lower.endswith(".csv")

    rows = []
    if is_csv:
        lines = []
        for line in _line_generator(path):
            lines.append(line)
            if len(lines) >= 10005:
                break
        reader = csv.DictReader(lines)
        for r in reader:
            rows.append(dict(r))
            if len(rows) >= 10000:
                break
    else:
        first_char = ""
        lines_gen = _line_generator(path)
        try:
            first_line = next(lines_gen, "").strip()
            if first_line:
                first_char = first_line[0]
        except StopIteration:
            pass

        lines_gen = _line_generator(path)
        if first_char == "[":
            content = "".join(list(lines_gen))
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    rows = data[:10000]
                elif isinstance(data, dict):
                    rows = [data]
            except Exception:
                pass
        else:
            for line in lines_gen:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    rows.append(json.loads(line_str))
                except Exception:
                    continue
                if len(rows) >= 10000:
                    break
    return rows


def audit_vendor_sample_file(path: str | Path) -> dict[str, Any]:
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Sample file not found: {path}")

    # Check path restriction: must be under data/external_signal_shadow/vendor_liquidation_samples/
    # (except for pytest tmp directories)
    if "vendor_liquidation_samples" not in str(path) and "tmp" not in str(path) and "pytest" not in str(path):
        raise ValueError("sample_file_not_under_runtime_vendor_dir")

    rows = _load_rows_from_file(path)
    row_count = len(rows)
    if row_count == 0:
        return {
            "row_count": 0,
            "symbol_field_available": False,
            "timestamp_field_available": False,
            "notional_usd_available": False,
            "side_available": False,
            "symbols_verified": [],
            "history_days": 0.0,
            "timestamp_resolution_ms": 0,
            "intraday_usable": False,
        }

    # Inspect keys across rows to find field availability
    symbol_keys = {"symbol", "ticker", "instid", "instrument_id", "instrument"}
    timestamp_keys = {"timestamp", "time", "date", "ts", "event_time"}
    side_keys = {"side", "liquidation_side", "long_short", "direction"}
    notional_keys = {"notional_usd", "liquidation_usd", "amount_usd", "volume_usd", "notional", "amount"}
    long_amount_keys = {"long_liquidation_usd", "longvolusd"}
    short_amount_keys = {"short_liquidation_usd", "shortvolusd"}
    price_keys = {"price", "px", "last_price"}
    qty_keys = {"quantity", "qty", "amount_qty", "sz", "size"}

    # We check if any key exists in the first row
    first_row_keys = {k.lower() for k in rows[0].keys()}

    symbol_field_available = any(k in symbol_keys for k in first_row_keys)
    timestamp_field_available = any(k in timestamp_keys for k in first_row_keys)

    side_available = (
        any(k in side_keys for k in first_row_keys) or
        (any(k in long_amount_keys for k in first_row_keys) and any(k in short_amount_keys for k in first_row_keys))
    )

    notional_usd_available = (
        any(k in notional_keys for k in first_row_keys) or
        (any(k in long_amount_keys for k in first_row_keys) and any(k in short_amount_keys for k in first_row_keys)) or
        (any(k in price_keys for k in first_row_keys) and any(k in qty_keys for k in first_row_keys))
    )

    # Collect symbols and timestamps
    symbols_set = set()
    timestamps = []

    # Identify which key maps to symbol and timestamp
    sym_key = next((k for k in rows[0].keys() if k.lower() in symbol_keys), None)
    ts_key = next((k for k in rows[0].keys() if k.lower() in timestamp_keys), None)

    for r in rows:
        if sym_key and sym_key in r:
            sym_val = str(r[sym_key]).strip().upper()
            if sym_val:
                symbols_set.add(sym_val)
        if ts_key and ts_key in r:
            ts_ms = _parse_timestamp_to_ms(r[ts_key])
            if ts_ms is not None:
                timestamps.append(ts_ms)

    symbols_verified = sorted(list(symbols_set))

    history_days = 0.0
    timestamp_resolution_ms = 0
    intraday_usable = False

    if len(timestamps) >= 2:
        sorted_ts = sorted(timestamps)
        min_ts = sorted_ts[0]
        max_ts = sorted_ts[-1]
        history_days = float((max_ts - min_ts) / (24 * 60 * 60 * 1000))

        diffs = [sorted_ts[i+1] - sorted_ts[i] for i in range(len(sorted_ts)-1)]
        positive_diffs = [d for d in diffs if d > 0]
        if positive_diffs:
            timestamp_resolution_ms = int(min(positive_diffs))
            intraday_usable = (timestamp_resolution_ms <= base.EXTERNAL_SIGNAL_STAGE1_4A2_MAX_TIMESTAMP_RESOLUTION_MS)

    return {
        "row_count": row_count,
        "symbol_field_available": symbol_field_available,
        "timestamp_field_available": timestamp_field_available,
        "notional_usd_available": notional_usd_available,
        "side_available": side_available,
        "symbols_verified": symbols_verified,
        "history_days": history_days,
        "timestamp_resolution_ms": timestamp_resolution_ms,
        "intraday_usable": intraday_usable,
    }


