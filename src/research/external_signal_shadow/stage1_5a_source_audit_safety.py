import hashlib
import json
import urllib.parse
from typing import List, Union

from configs import base
from src.research.external_signal_shadow.stage1_5a_source_audit_models import (
    RawSourcePayload,
    SourceAuditFinding,
)

FORBIDDEN_KEYS = {
    "api_key",
    "secret",
    "private_key",
    "wallet_seed",
    "mnemonic",
    "authorization",
    "bearer",
    "access_token",
    "refresh_token",
    "cookie",
    "session",
    "csrf",
    "password",
    "passphrase",
    "signed_tx",
    "raw_tx",
    "order_request",
    "swap_request",
    "transfer_request",
    "wallet_private_key",
    "tx_payload",
}


def normalize_source_domain(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ""
    # Strip port if present
    if ":" in hostname:
        hostname = hostname.split(":")[0]
    return hostname.lower()


def validate_domain_allowlist(url: str, allowed_domains: tuple[str, ...]) -> bool:
    domain = normalize_source_domain(url)
    if not domain:
        return False
    for allowed in allowed_domains:
        allowed = allowed.lower()
        if domain == allowed or domain.endswith("." + allowed):
            return True
    return False


def compute_payload_sha256(payload: Union[bytes, str]) -> str:
    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    else:
        payload_bytes = payload
    return hashlib.sha256(payload_bytes).hexdigest()


def measure_json_depth(value: object) -> int:
    if isinstance(value, dict):
        if not value:
            return 1
        return 1 + max(measure_json_depth(v) for v in value.values())
    elif isinstance(value, list):
        if not value:
            return 0
        return max(measure_json_depth(v) for v in value)
    return 0


def detect_forbidden_payload_keys(value: object) -> List[str]:
    found_keys = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k.lower() in FORBIDDEN_KEYS:
                found_keys.append(k)
            found_keys.extend(detect_forbidden_payload_keys(v))
    elif isinstance(value, list):
        for item in value:
            found_keys.extend(detect_forbidden_payload_keys(item))
    # Deduplicate while preserving order
    seen = set()
    return [x for x in found_keys if not (x in seen or seen.add(x))]


def validate_source_resource_safety(
    raw_payload: RawSourcePayload,
) -> List[SourceAuditFinding]:
    findings = []

    # Check url domain
    if raw_payload.source_url.startswith("file://"):
        url_allowed = True
    else:
        url_allowed = validate_domain_allowlist(
            raw_payload.source_url,
            base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_ALLOWED_DOMAINS,
        )
    if not url_allowed:
        findings.append(
            SourceAuditFinding(
                rule_id="disallowed_domain",
                severity="veto",
                message=f"URL domain {normalize_source_domain(raw_payload.source_url)} is not in allowlist",
                finding_details={"source_name": raw_payload.source_name},
            )
        )

    # Check size
    if (
        len(raw_payload.raw_payload_bytes)
        > base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_MAX_PAYLOAD_BYTES
    ):
        findings.append(
            SourceAuditFinding(
                rule_id="payload_too_large",
                severity="veto",
                message=f"Payload size {len(raw_payload.raw_payload_bytes)} bytes exceeds limit {base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_MAX_PAYLOAD_BYTES}",
                finding_details={"source_name": raw_payload.source_name},
            )
        )

    # Try parsing JSON/JSONL
    try:
        payload_str = raw_payload.raw_payload_bytes.decode("utf-8", errors="replace")
        is_json = raw_payload.content_type == "application/json"
        is_jsonl = raw_payload.content_type == "application/jsonl"

        # Try parsing as single JSON document first
        parsed_ok = False
        if is_json or (not is_jsonl and payload_str.strip().startswith(("{", "["))):
            try:
                data = json.loads(payload_str)
                parsed_ok = True

                # Check depth
                depth = measure_json_depth(data)
                if depth > base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_MAX_JSON_DEPTH:
                    findings.append(
                        SourceAuditFinding(
                            rule_id="json_depth_exceeded",
                            severity="veto",
                            message=f"JSON depth {depth} exceeds max limit {base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_MAX_JSON_DEPTH}",
                            finding_details={"source_name": raw_payload.source_name},
                        )
                    )

                # Check forbidden keys
                forbidden_keys = detect_forbidden_payload_keys(data)
                if forbidden_keys:
                    findings.append(
                        SourceAuditFinding(
                            rule_id="forbidden_payload",
                            severity="veto",
                            message=f"Forbidden keys found in payload: {', '.join(forbidden_keys)}",
                            finding_details={"source_name": raw_payload.source_name},
                        )
                    )
            except json.JSONDecodeError as jde:
                if is_json:
                    raise jde
                else:
                    is_jsonl = True

        if (is_jsonl or (not is_json and payload_str.strip().startswith("{"))) and not parsed_ok:
            # Try line-by-line JSONL parsing
            lines = payload_str.strip().split("\n")
            for line_idx, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    line_data = json.loads(line)

                    # Check depth
                    depth = measure_json_depth(line_data)
                    if depth > base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_MAX_JSON_DEPTH:
                        findings.append(
                            SourceAuditFinding(
                                rule_id="json_depth_exceeded",
                                severity="veto",
                                message=f"JSON depth {depth} at line {line_idx+1} exceeds max limit {base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_MAX_JSON_DEPTH}",
                                finding_details={"source_name": raw_payload.source_name},
                            )
                        )

                    # Check forbidden keys
                    forbidden_keys = detect_forbidden_payload_keys(line_data)
                    if forbidden_keys:
                        findings.append(
                            SourceAuditFinding(
                                rule_id="forbidden_payload",
                                severity="veto",
                                message=f"Forbidden keys found in payload at line {line_idx+1}: {', '.join(forbidden_keys)}",
                                finding_details={"source_name": raw_payload.source_name},
                            )
                        )
                except json.JSONDecodeError as jde:
                    if is_jsonl:
                        raise jde
    except json.JSONDecodeError:
        findings.append(
            SourceAuditFinding(
                rule_id="schema_parse_error",
                severity="veto",
                message="Failed to parse JSON/JSONL payload",
                finding_details={"source_name": raw_payload.source_name},
            )
        )
    except Exception as e:
        findings.append(
            SourceAuditFinding(
                rule_id="safety_check_error",
                severity="veto",
                message=f"Error in safety check: {str(e)}",
                finding_details={"source_name": raw_payload.source_name},
            )
        )

    return findings
