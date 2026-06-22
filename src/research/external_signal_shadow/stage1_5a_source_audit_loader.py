import datetime
import glob
import os
import time
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

from configs import base
from src.research.external_signal_shadow.stage1_5a_source_audit_models import (
    RawSourcePayload,
)
from src.research.external_signal_shadow.stage1_5a_source_audit_safety import (
    compute_payload_sha256,
    validate_domain_allowlist,
)


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Verify the redirect URL is in allowlist
        if not validate_domain_allowlist(
            newurl, base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_ALLOWED_DOMAINS
        ):
            raise ValueError(f"Redirect target domain for {newurl} is not in allowlist")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def load_local_fixture(
    file_path: str, source_name: str, source_profile: str
) -> RawSourcePayload:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fixture file not found: {file_path}")

    with open(file_path, "rb") as f:
        data = f.read()

    # Determine content_type
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".json":
        content_type = "application/json"
    elif ext == ".jsonl":
        content_type = "application/jsonl"
    elif ext in (".html", ".htm"):
        content_type = "text/html"
    else:
        content_type = "application/octet-stream"

    now_ms = int(time.time() * 1000)

    return RawSourcePayload(
        source_name=source_name,
        source_profile=source_profile,
        source_url=f"file://{os.path.abspath(file_path)}",
        source_parent_url=f"file://{os.path.dirname(os.path.abspath(file_path))}",
        raw_payload_bytes=data,
        collector_received_at_ms=now_ms,
        content_type=content_type,
        file_path=file_path,
    )


def fetch_source_url(
    url: str, source_name: str, source_profile: str
) -> RawSourcePayload:
    # 1. Check URL allowed domain
    if not validate_domain_allowlist(
        url, base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_ALLOWED_DOMAINS
    ):
        raise ValueError(f"URL domain is not in allowlist: {url}")

    # 2. Build opener with safe redirect handler
    opener = urllib.request.build_opener(SafeRedirectHandler)

    timeout = base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_REQUEST_TIMEOUT_SEC
    retry_budget = base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_RETRY_BUDGET

    last_error = None
    response_data = None
    final_url = url
    content_type = "application/json"

    # Retry loop
    for attempt in range(retry_budget + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "crypto-alpha-lab-research-readonly-source-audit/0.1"
                },
            )
            with opener.open(req, timeout=timeout) as response:
                response_data = response.read()
                final_url = response.geturl()
                content_type = response.info().get_content_type()
            break
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_error = e
            # Polite wait before retry
            if attempt < retry_budget:
                time.sleep(1.0)
        except Exception as e:
            last_error = e
            break

    if response_data is None:
        raise Exception(
            f"Failed to fetch source URL {url} after {retry_budget} retries. Last error: {last_error}"
        )

    # Double check final URL after redirects
    if not validate_domain_allowlist(
        final_url, base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_ALLOWED_DOMAINS
    ):
        raise ValueError(
            f"Redirect target domain {final_url} is not in allowlist after redirects"
        )

    now_ms = int(time.time() * 1000)

    return RawSourcePayload(
        source_name=source_name,
        source_profile=source_profile,
        source_url=final_url,
        source_parent_url=url,
        raw_payload_bytes=response_data,
        collector_received_at_ms=now_ms,
        content_type=content_type,
    )


def load_or_fetch_payloads(
    source_file: Optional[str] = None,
    source_url: Optional[str] = None,
    source_name: str = "binance_test",
    source_profile: str = "generic_json_announcement_rows",
    write_cache: bool = False,
    cache_dir_override: Optional[str] = None,
) -> Tuple[List[RawSourcePayload], bool, dict]:
    if source_file is not None and source_url is not None:
        raise ValueError("Cannot specify both source_file and source_url")

    payloads = []
    fixture_run = False
    metadata = {
        "raw_cache_written": False,
        "raw_cache_path": "",
        "network_result_not_deterministic": False,
        "collector_received_at_ms": None,
    }

    if source_file is not None:
        fixture_run = True
        # Resolve glob
        files = glob.glob(source_file)
        if not files:
            # If no glob match, check if it's a direct file path
            if os.path.exists(source_file):
                files = [source_file]
            else:
                raise FileNotFoundError(f"No files matched path/glob: {source_file}")
        for fp in sorted(files):
            payloads.append(load_local_fixture(fp, source_name, source_profile))

    elif source_url is not None:
        fixture_run = False
        payload = fetch_source_url(source_url, source_name, source_profile)
        payloads.append(payload)
        metadata["network_result_not_deterministic"] = True
        metadata["collector_received_at_ms"] = payload.collector_received_at_ms

        # Write cache if requested
        if write_cache:
            now = datetime.datetime.utcnow()
            date_str = now.strftime("%Y%m%d")
            base_dir = cache_dir_override or os.path.join(
                "data", "external_signal_shadow", "stage1_5a"
            )
            cache_dir = os.path.join(base_dir, "raw", date_str, source_name)
            os.makedirs(cache_dir, exist_ok=True)

            url_hash = compute_payload_sha256(source_url)[:8]
            ts = payload.collector_received_at_ms
            filename = f"{url_hash}_{ts}.dat"
            cache_path = os.path.join(cache_dir, filename)

            with open(cache_path, "wb") as f:
                f.write(payload.raw_payload_bytes)
            metadata["raw_cache_written"] = True
            metadata["raw_cache_path"] = cache_path

    else:
        raise ValueError("Must specify either source_file or source_url")

    return payloads, fixture_run, metadata
