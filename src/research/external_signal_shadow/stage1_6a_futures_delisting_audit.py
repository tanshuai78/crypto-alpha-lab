"""
Stage 1.6A USD-M Futures Delisting Core Audit Reducer, Schedule Fact Extractor, and Scope Classifier.
Design Reference: docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md
"""

import base64
import hashlib
import json
import re
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.research.external_signal_shadow.stage1_6a_futures_delisting_models import (
    BODY_NORMALIZATION_VERSION,
    CANDIDATE_DISCOVERY_RULE_VERSION,
    SEMANTIC_AUTHORITY_LOCALE,
SEMANTIC_AUTHORITY_VARIANT,
    SEMANTIC_EXTRACTOR_VERSION,
    AuditCandidateManifest,
    CandidateDiscoveryItem,
    CaptureMode,
    CaptureTimeStatus,
    ContractType,
    DelistingContract,
    EvidenceLocationKind,
    EvidencePointer,
    FactParseStatus,
    MarginFamily,
    OrderRestrictionType,
    ScheduleFact,
    SourceSurface,
    UnderlyingFamily,
    canonical_json_fingerprint,
    compute_delisting_contract_id,
    compute_detail_revision_id,
    compute_list_capture_id,
    compute_semantic_extraction_id,
)

UTC_DT_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


def parse_utc_timestamp_ms(dt_str: str) -> Optional[int]:
    """Parses a UTC datetime string (e.g. '2024-04-03 09:00:00' or '2024-04-03 09:00') into epoch ms."""
    cleaned = dt_str.strip()
    for fmt in UTC_DT_FORMATS:
        try:
            dt = datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None


def normalize_body_text(raw_bytes: bytes) -> str:
    """Normalizes raw HTML/JSON bytes into a clean, normalized UTF-8 string for evidence offsets."""
    text = raw_bytes.decode("utf-8", errors="replace")
    # Strip HTML tags simply
    text = re.sub(r"<[^>]+>", " ", text)
    # Unicode NFKC normalize
    text = unicodedata.normalize("NFKC", text)
    # Collapse multiple whitespace but keep newlines/structure sensible
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def validate_capture_metadata(
    source_url: str,
    source_surface: str,
    source_locale: str,
    request_variant: str,
    capture_mode: str,
) -> Tuple[bool, Optional[str]]:
    """Validates transport and source provenance constraints."""
    parsed_url = urllib.parse.urlparse(source_url)
    if parsed_url.scheme != "https":
        return False, f"Invalid scheme: {parsed_url.scheme}, expected https"
    if parsed_url.netloc not in ("www.binance.com", "binance.com"):
        return False, f"Invalid domain: {parsed_url.netloc}, expected official binance domain"
    expected_variants = {
        SourceSurface.ANNOUNCEMENT_INDEX.value: "canonical_binance_english_index",
        SourceSurface.ANNOUNCEMENT_DETAIL.value: SEMANTIC_AUTHORITY_VARIANT,
    }
    if source_surface not in expected_variants:
        return False, f"Invalid source surface: {source_surface}"
    if request_variant != expected_variants[source_surface]:
        return False, f"Invalid request variant for {source_surface}: {request_variant}"
    if source_locale != SEMANTIC_AUTHORITY_LOCALE:
        return False, f"Non-canonical locale: {source_locale}, expected en"
    if capture_mode != CaptureMode.HISTORICAL_BACKFILL.value:
        return False, f"capture_mode must be historical_backfill: {capture_mode}"
    return True, None


def extract_candidates_from_list(
    list_record: Dict[str, Any],
) -> Tuple[AuditCandidateManifest, int]:
    """
    Extracts candidate articles from a list_capture record using candidate_discovery_rule_v1.
    Also computes broader candidate recall false negative diagnostic count using candidate_recall_probe_v1.
    """
    raw_b64 = list_record.get("raw_payload_base64", "")
    try:
        raw_bytes = base64.b64decode(raw_b64, validate=True)
    except Exception as exc:
        raise ValueError("Invalid base64 list payload") from exc

    list_raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    list_cap_id = compute_list_capture_id(
        list_record.get("source_surface", SourceSurface.ANNOUNCEMENT_INDEX.value),
        list_record.get("source_locale", SEMANTIC_AUTHORITY_LOCALE),
        list_record.get("request_variant", "canonical_binance_english_index"),
        list_raw_hash,
    )
    fetched_at_ms = list_record.get("fetched_at_ms")
    capture_mode = list_record.get("capture_mode", CaptureMode.HISTORICAL_BACKFILL.value)

    # Parse articles list
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed list payload") from exc
    if not isinstance(data, dict) or not isinstance(data.get("articles"), list):
        raise ValueError("List payload must contain an articles list")
    articles = data["articles"]

    manifest_items: List[CandidateDiscoveryItem] = []
    false_negatives = 0

    for item in articles:
        aid = str(item.get("id") or item.get("code") or item.get("article_id") or "")
        title = str(item.get("title") or "")
        if not aid or not title:
            continue

        norm_title = unicodedata.normalize("NFKC", title).lower()

        # Primary rule: both "binance futures" and "delist"
        is_candidate = "binance futures" in norm_title and "delist" in norm_title

        # Broader recall probe: "delist" or "removal"
        is_recall_hit = "delist" in norm_title or "removal" in norm_title

        if is_candidate:
            manifest_items.append(
                CandidateDiscoveryItem(
                    source_article_id=aid,
                    title=title,
                    first_list_capture_id=list_cap_id,
                    notice_lineage_first_detected_at_ms=fetched_at_ms if capture_mode == CaptureMode.LIVE_OBSERVED.value else None,
                    capture_mode=capture_mode,
                    discovery_rule_version=CANDIDATE_DISCOVERY_RULE_VERSION,
                )
            )
        elif is_recall_hit and "futures" in norm_title:
            false_negatives += 1

    # Deterministic sorting
    manifest_items.sort(key=lambda x: x.source_article_id)
    manifest_id = hashlib.sha256(
        f"{list_cap_id}|{CANDIDATE_DISCOVERY_RULE_VERSION}|{len(manifest_items)}".encode("utf-8")
    ).hexdigest()

    manifest_sha256 = canonical_json_fingerprint([i.to_dict() for i in manifest_items])

    manifest = AuditCandidateManifest(
        manifest_id=manifest_id,
        discovery_rule_version=CANDIDATE_DISCOVERY_RULE_VERSION,
        items=manifest_items,
        manifest_sha256=manifest_sha256,
    )
    return manifest, false_negatives


def find_evidence_span(
    normalized_body: str,
    pattern: str,
    detail_revision_id: str,
    detail_raw_sha256: str,
    semantic_extraction_id: str,
) -> Optional[EvidencePointer]:
    """Finds regex match in normalized body and returns EvidencePointer with exact UTF-8 byte bounds."""
    m = re.search(pattern, normalized_body, re.IGNORECASE)
    if not m:
        return None

    match_text = m.group(0)
    char_start = m.start()
    char_end = m.end()

    byte_start = len(normalized_body[:char_start].encode("utf-8"))
    byte_end = len(normalized_body[:char_end].encode("utf-8"))

    return EvidencePointer(
        detail_revision_id=detail_revision_id,
        detail_raw_sha256=detail_raw_sha256,
        semantic_extraction_id=semantic_extraction_id,
        semantic_extractor_version=SEMANTIC_EXTRACTOR_VERSION,
        body_normalization_version=BODY_NORMALIZATION_VERSION,
        location_kind=EvidenceLocationKind.NORMALIZED_TEXT_SPAN.value,
        location_value=pattern,
        normalized_body_utf8_byte_start=byte_start,
        normalized_body_utf8_byte_end=byte_end,
        excerpt=match_text,
    )


def extract_schedule_facts_from_body(
    normalized_body: str,
    detail_revision_id: str,
    detail_raw_sha256: str,
    semantic_extraction_id: str,
    capture_mode: str,
) -> Dict[str, ScheduleFact]:
    """Extracts settlement, reduce-only, and last trading facts from normalized announcement body."""
    facts: Dict[str, ScheduleFact] = {}
    cap_status = (
        CaptureTimeStatus.PRESENT.value
        if capture_mode == CaptureMode.LIVE_OBSERVED.value
        else CaptureTimeStatus.HISTORICAL_UNKNOWN.value
    )

    # 1. Published time
    pub_match = re.search(r"Published on:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)", normalized_body, re.IGNORECASE)
    if pub_match:
        pub_ts = parse_utc_timestamp_ms(pub_match.group(1))
        pub_ev = find_evidence_span(
            normalized_body,
            r"Published on:\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?",
            detail_revision_id,
            detail_raw_sha256,
            semantic_extraction_id,
        )
        facts["published_time"] = ScheduleFact(
            fact_parse_status=FactParseStatus.PRESENT.value if pub_ts else FactParseStatus.UNPARSEABLE.value,
            capture_time_status=cap_status,
            timestamp_ms=pub_ts,
            source_detail_revision_id=detail_revision_id,
            source_semantic_extraction_id=semantic_extraction_id,
            fact_available_at_ms=None,
            evidence=pub_ev,
        )
    else:
        facts["published_time"] = ScheduleFact(
            fact_parse_status=FactParseStatus.NOT_STATED.value,
            capture_time_status=cap_status,
            fact_available_at_ms=None,
        )

    # 2. Settlement time
    settle_pattern = r"(?:conduct automatic settlement|automatic settlement|close all positions and delist|will delist)[^\n\.\;]*?at\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*\(UTC\)"
    settle_match = re.search(settle_pattern, normalized_body, re.IGNORECASE)

    if settle_match:
        settle_ts = parse_utc_timestamp_ms(settle_match.group(1))
        settle_ev = find_evidence_span(
            normalized_body,
            settle_pattern,
            detail_revision_id,
            detail_raw_sha256,
            semantic_extraction_id,
        )
        facts["settlement_time"] = ScheduleFact(
            fact_parse_status=FactParseStatus.PRESENT.value if settle_ts else FactParseStatus.UNPARSEABLE.value,
            capture_time_status=cap_status,
            timestamp_ms=settle_ts,
            source_detail_revision_id=detail_revision_id,
            source_semantic_extraction_id=semantic_extraction_id,
            fact_available_at_ms=None,
            evidence=settle_ev,
        )
    else:
        facts["settlement_time"] = ScheduleFact(
            fact_parse_status=FactParseStatus.NOT_STATED.value,
            capture_time_status=cap_status,
            fact_available_at_ms=None,
        )

    # 3. Order restriction (Reduce-only)
    restr_pattern = r"(?:starting from|users are only allowed to reduce|reduce-only mode)[^\n\.\;]*?(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*\(UTC\)"
    restr_match = re.search(restr_pattern, normalized_body, re.IGNORECASE)
    if restr_match and ("reduce-only" in normalized_body.lower() or "not be able to open new positions" in normalized_body.lower()):
        restr_ts = parse_utc_timestamp_ms(restr_match.group(1))
        restr_ev = find_evidence_span(
            normalized_body,
            restr_pattern,
            detail_revision_id,
            detail_raw_sha256,
            semantic_extraction_id,
        )
        facts["order_restriction"] = ScheduleFact(
            fact_parse_status=FactParseStatus.PRESENT.value if restr_ts else FactParseStatus.UNPARSEABLE.value,
            capture_time_status=cap_status,
            timestamp_ms=restr_ts,
            order_restriction_type=OrderRestrictionType.REDUCE_ONLY_ONLY.value,
            source_detail_revision_id=detail_revision_id,
            source_semantic_extraction_id=semantic_extraction_id,
            fact_available_at_ms=None,
            evidence=restr_ev,
        )
    else:
        facts["order_restriction"] = ScheduleFact(
            fact_parse_status=FactParseStatus.NOT_STATED.value,
            capture_time_status=cap_status,
            order_restriction_type=None,  # Never inferred per INV-04
            fact_available_at_ms=None,
        )

    # 4. Last trading time
    last_pattern = r"(?:last normal trading|last trading time)[^\n\.\;]*?(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*\(UTC\)"
    last_match = re.search(last_pattern, normalized_body, re.IGNORECASE)
    if last_match:
        last_ts = parse_utc_timestamp_ms(last_match.group(1))
        last_ev = find_evidence_span(
            normalized_body,
            last_pattern,
            detail_revision_id,
            detail_raw_sha256,
            semantic_extraction_id,
        )
        facts["last_trading_time"] = ScheduleFact(
            fact_parse_status=FactParseStatus.PRESENT.value if last_ts else FactParseStatus.UNPARSEABLE.value,
            capture_time_status=cap_status,
            timestamp_ms=last_ts,
            source_detail_revision_id=detail_revision_id,
            source_semantic_extraction_id=semantic_extraction_id,
            fact_available_at_ms=None,
            evidence=last_ev,
        )
    else:
        facts["last_trading_time"] = ScheduleFact(
            fact_parse_status=FactParseStatus.NOT_STATED.value,
            capture_time_status=cap_status,
            fact_available_at_ms=None,
        )

    return facts


def classify_symbol_and_product(
    raw_symbol_str: str,
    context_text: str,
) -> Tuple[str, MarginFamily, ContractType, UnderlyingFamily, bool]:
    """
    Classifies a symbol string into canonical_symbol, MarginFamily, ContractType, UnderlyingFamily.
    Returns: (canonical_symbol, margin_family, contract_type, underlying_family, is_in_scope)
    """
    sym = raw_symbol_str.strip().upper()
    ctx_upper = context_text.upper()

    # Check COIN-M: contains COIN-M in symbol or context mentions COIN-M with symbol, or symbol ends with USD / USD_PERP
    if "COIN-M" in sym or "USD_PERP" in sym or ("COIN-M" in ctx_upper and ("BTCUSD" in sym or "ETHUSD" in sym or sym.endswith("USD"))):
        return sym, MarginFamily.COIN_M, ContractType.PERPETUAL, UnderlyingFamily.CRYPTO_ASSET, False

    # TradFi / Commodity check
    if sym in ("BRENTUSDT", "WTIUSDT", "XAUUSDT", "XAGUSDT", "SPXUSDT", "NDXUSDT"):
        return sym, MarginFamily.USD_M, ContractType.PERPETUAL, UnderlyingFamily.COMMODITY, False

    if sym.endswith("USDT") or sym.endswith("USDC"):
        # USD-M Crypto Perpetual
        return sym, MarginFamily.USD_M, ContractType.PERPETUAL, UnderlyingFamily.CRYPTO_ASSET, True

    return sym, MarginFamily.UNKNOWN, ContractType.UNKNOWN, UnderlyingFamily.UNKNOWN, False



def process_capture_bundle(
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Core reducer processing an authoritative capture bundle.
    Derives list captures, discoveries, revisions, semantic extractions, notices, and child contracts.
    """
    list_records = [r for r in records if r.get("record_type") == "list_capture"]
    detail_records = [r for r in records if r.get("record_type") == "detail_observation"]

    if not list_records:
        raise ValueError("Capture bundle missing list_capture record")

    primary_list = list_records[0]
    is_valid_list, list_error = validate_capture_metadata(
        primary_list.get("source_url", ""),
        primary_list.get("source_surface", ""),
        primary_list.get("source_locale", ""),
        primary_list.get("request_variant", ""),
        primary_list.get("capture_mode", ""),
    )
    if not is_valid_list:
        raise ValueError(f"Invalid list_capture metadata: {list_error}")
    manifest, false_negatives = extract_candidates_from_list(primary_list)

    # Index details by source_article_id
    details_by_id: Dict[str, Dict[str, Any]] = {}
    revision_first_observed_at_ms: Dict[Tuple[str, str], Optional[int]] = {}
    for d in detail_records:
        aid = str(d.get("source_article_id", ""))
        if aid:
            details_by_id[aid] = d
            raw_payload_base64 = str(d.get("raw_payload_base64", ""))
            observation_time = d.get("observed_at_ms")
            key = (aid, raw_payload_base64)
            previous = revision_first_observed_at_ms.get(key)
            if previous is None or (observation_time is not None and observation_time < previous):
                revision_first_observed_at_ms[key] = observation_time

    # Process candidates
    detail_revisions: List[Dict[str, Any]] = []
    semantic_extractions: List[Dict[str, Any]] = []
    contracts: List[DelistingContract] = []
    notices: List[Dict[str, Any]] = []

    trusted_parents_count = 0
    symbols_mapped_count = 0
    classified_parents_count = 0
    forbidden_payloads = 0
    mixed_notice_count = 0
    out_of_scope_child_count = 0
    excluded_due_to_incomplete_parent = 0

    for item in manifest.items:
        aid = item.source_article_id
        detail = details_by_id.get(aid)

        if not detail:
            # Detail unavailable / WAF
            notices.append({
                "source_article_id": aid,
                "title": item.title,
                "status": "detail_unavailable",
                "source_audit_eligible": False,
                "child_count": 0,
            })
            continue

        # Validate transport & provenance
        is_valid_meta, meta_err = validate_capture_metadata(
            detail.get("source_url", ""),
            detail.get("source_surface", SourceSurface.ANNOUNCEMENT_DETAIL.value),
            detail.get("source_locale", SEMANTIC_AUTHORITY_LOCALE),
            detail.get("request_variant", SEMANTIC_AUTHORITY_VARIANT),
            detail.get("capture_mode", CaptureMode.HISTORICAL_BACKFILL.value),
        )

        if not is_valid_meta:
            raise ValueError(f"Invalid detail_observation metadata for {aid}: {meta_err}")

        raw_b64 = detail.get("raw_payload_base64", "")
        try:
            raw_bytes = base64.b64decode(raw_b64, validate=True)
        except Exception as exc:
            raise ValueError(f"Invalid base64 detail payload for {aid}") from exc

        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        supplied_sha256 = detail.get("supplied_detail_raw_sha256")
        if supplied_sha256 and supplied_sha256 != raw_sha256:
            forbidden_payloads += 1
            notices.append({
                "source_article_id": aid,
                "title": item.title,
                "status": "raw_hash_mismatch",
                "source_audit_eligible": False,
                "child_count": 0,
            })
            continue

        detail_rev_id = compute_detail_revision_id(
            aid,
            detail.get("source_surface", SourceSurface.ANNOUNCEMENT_DETAIL.value),
            detail.get("source_locale", SEMANTIC_AUTHORITY_LOCALE),
            detail.get("request_variant", SEMANTIC_AUTHORITY_VARIANT),
            raw_sha256,
        )

        detail_revisions.append({
            "detail_revision_id": detail_rev_id,
            "source_article_id": aid,
            "detail_raw_sha256": raw_sha256,
            "observed_at_ms": detail.get("observed_at_ms"),
            "revision_first_observed_at_ms": revision_first_observed_at_ms[(aid, raw_b64)],
            "capture_mode": detail.get("capture_mode"),
        })

        trusted_parents_count += 1

        # Normalize body and extract facts
        norm_body = normalize_body_text(raw_bytes)

        # Check symbols declared in title and body
        # Simple extraction: look for uppercase symbols ending with USDT/USDC or BTCUSD
        sym_matches = set(re.findall(r"\b([A-Z0-9]{2,10}(?:USDT|USDC|USD_PERP))\b", norm_body))

        # Also check title
        title_sym_matches = set(re.findall(r"\b([A-Z0-9]{2,10}(?:USDT|USDC|USD))\b", item.title))
        all_declared_syms = sym_matches | title_sym_matches

        # Check for unresolvable corrupted entities like [Corrupted Symbol Entity Error] or "???"
        is_corrupted = "corrupted symbol" in norm_body.lower() or "???" in item.title

        if not all_declared_syms or is_corrupted:
            # Incomplete parent
            excluded_due_to_incomplete_parent += 1
            notices.append({
                "source_article_id": aid,
                "title": item.title,
                "status": "incomplete_declared_symbols",
                "source_audit_eligible": False,
                "child_count": 0,
            })
            continue

        symbols_mapped_count += 1
        classified_parents_count += 1

        # Classify children
        child_records: List[DelistingContract] = []
        has_out_of_scope_sibling = False
        has_in_scope_child = False

        # First pass to compute semantic extraction fingerprint
        fact_fingerprint_dict = {
            "declared_symbols": sorted(list(all_declared_syms)),
            "body_sha256": hashlib.sha256(norm_body.encode("utf-8")).hexdigest(),
        }
        fact_fp = canonical_json_fingerprint(fact_fingerprint_dict)

        semantic_ext_id = compute_semantic_extraction_id(
            detail_rev_id,
            SEMANTIC_EXTRACTOR_VERSION,
            BODY_NORMALIZATION_VERSION,
            fact_fp,
        )

        semantic_extractions.append({
            "semantic_extraction_id": semantic_ext_id,
            "detail_revision_id": detail_rev_id,
            "semantic_extractor_version": SEMANTIC_EXTRACTOR_VERSION,
            "body_normalization_version": BODY_NORMALIZATION_VERSION,
            "canonical_fact_fingerprint": fact_fp,
            "semantic_extracted_at_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
            "system_available_at_ms": None,
            "capture_time_status": CaptureTimeStatus.HISTORICAL_UNKNOWN.value,
        })

        facts = extract_schedule_facts_from_body(
            norm_body,
            detail_rev_id,
            raw_sha256,
            semantic_ext_id,
            detail.get("capture_mode", CaptureMode.HISTORICAL_BACKFILL.value),
        )

        for sym in sorted(list(all_declared_syms)):
            c_sym, margin, c_type, under, in_scope = classify_symbol_and_product(sym, norm_body)
            cid = compute_delisting_contract_id(aid, detail_rev_id, c_sym, margin.value, c_type.value, under.value)

            if in_scope:
                has_in_scope_child = True
            else:
                has_out_of_scope_sibling = True
                out_of_scope_child_count += 1

            contract = DelistingContract(
                contract_id=cid,
                parent_article_id=aid,
                detail_revision_id=detail_rev_id,
                canonical_symbol=c_sym,
                margin_family=margin.value,
                contract_type=c_type.value,
                underlying_family=under.value,
                is_in_scope=in_scope,
                source_audit_eligible=in_scope,
                settlement_time=facts.get("settlement_time"),
                order_restriction=facts.get("order_restriction"),
                last_trading_time=facts.get("last_trading_time"),
            )
            child_records.append(contract)
            contracts.append(contract)

        if has_out_of_scope_sibling and has_in_scope_child:
            mixed_notice_count += 1

        notices.append({
            "source_article_id": aid,
            "title": item.title,
            "status": "complete_parent",
            "source_audit_eligible": has_in_scope_child,
            "child_count": len(child_records),
            "in_scope_child_count": sum(1 for c in child_records if c.is_in_scope),
            "published_at_ms": facts.get("published_time").timestamp_ms if facts.get("published_time") else None,
        })

    return {
        "manifest": manifest,
        "detail_revisions": detail_revisions,
        "semantic_extractions": semantic_extractions,
        "contracts": contracts,
        "notices": notices,
        "metrics_raw": {
            "candidate_total_denominator": len(manifest.items),
            "trusted_parents_count": trusted_parents_count,
            "symbols_mapped_count": symbols_mapped_count,
            "classified_parents_count": classified_parents_count,
            "forbidden_payload_count": forbidden_payloads,
            "candidate_discovery_false_negative_count": false_negatives,
            "mixed_notice_count": mixed_notice_count,
            "out_of_scope_child_count": out_of_scope_child_count,
            "usd_m_crypto_children_excluded_due_to_incomplete_parent_count": excluded_due_to_incomplete_parent,
        },
    }
