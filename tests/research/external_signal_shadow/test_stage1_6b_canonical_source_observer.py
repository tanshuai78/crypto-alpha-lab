"""Unit and reducer tests for Stage 1.6B live observer state machine and scheduling."""

import datetime
import hashlib
import io
import json
import shutil

import pytest

from src.research.external_signal_shadow.stage1_6b_canonical_source_client import (
    Stage16BCanonicalClient,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    CANDIDATE_DISCOVERY_RULE_VERSION,
    SOURCE_PROFILE_ID,
    CandidateLane,
    CaptureMode,
    CaptureRunContract,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_observer import (
    ObserverSLAError,
    Stage16BObserver,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import (
    Stage16BStorageGuard,
    write_capture_run_contract,
)


class MockHTTPResponse:
    def __init__(self, body_bytes: bytes, status: int = 200, headers: dict = None, url: str = "https://www.binance.com"):
        self._body = io.BytesIO(body_bytes)
        self.status = status
        self.code = status
        self.headers = headers or {"Content-Type": "application/json"}
        self.url = url

    def read(self, amt=None):
        return self._body.read(amt)

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def geturl(self):
        return self.url

    def close(self):
        pass


def setup_observer(tmp_path, run_id="run_live_obs"):
    run_root = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    guard = Stage16BStorageGuard(output_root=run_root, disk_usage_func=lambda p: shutil._ntuple_diskusage(100*1024**3, 20*1024**3, 80*1024**3))

    contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id=run_id,
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256="dummy_att_sha",
        run_started_at_ms=1700000000000,
    )
    write_capture_run_contract(run_root, contract, guard, 0)
    return run_root, guard


def make_index_catalog_payload(articles):
    return json.dumps({
        "code": "000000",
        "data": {
            "catalogs": [
                {
                    "catalogId": 161,
                    "catalogName": "Delisting",
                    "total": max(len(articles), 400),
                    "articles": articles,
                }
            ]
        }
    }).encode("utf-8")


def test_observer_single_poll_lifecycle(tmp_path):
    """Verify one live poll discovers candidate, executes Lane A detail, writes revision and checkpoint."""
    run_root, guard = setup_observer(tmp_path, "run_poll_1")

    article_code = "a" * 32
    index_payload = make_index_catalog_payload([
        {
            "code": article_code,
            "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
            "releaseDate": 1732000000000
        }
    ])

    detail_payload = json.dumps({
        "code": "000000",
        "data": {
            "code": article_code,
            "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
            "body": "<p>Delisting notice body content</p>",
            "releaseDate": 1732000000000
        }
    }).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        elif "article/detail/query" in url:
            return MockHTTPResponse(detail_payload, url=url)
        raise ValueError(f"Unexpected url {url}")

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_poll_1",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    # Execute Poll 1
    now_ms = 1700000000000
    observer.execute_poll(now_ms=now_ms)

    # Verify discovery written
    disc_file = run_root / "article_discoveries.jsonl"
    assert disc_file.is_file()
    disc_lines = disc_file.read_text().strip().splitlines()
    assert len(disc_lines) == 1
    disc_data = json.loads(disc_lines[0])
    assert disc_data["source_article_id"] == article_code
    assert disc_data["source_catalog_id"] == 161
    assert disc_data["source_catalog_name"] == "Delisting"
    assert disc_data["discovery_rule_version"] == CANDIDATE_DISCOVERY_RULE_VERSION
    assert disc_data["notice_lineage_first_detected_at_ms"] == now_ms  # Anchored live discovery time

    # Verify detail observation & revision written
    rev_file = run_root / "detail_revisions.jsonl"
    assert rev_file.is_file()
    rev_lines = rev_file.read_text().strip().splitlines()
    assert len(rev_lines) == 1
    rev_data = json.loads(rev_lines[0])
    assert rev_data["source_article_id"] == article_code

    # Verify checkpoint written
    chk_file = run_root / "observer_checkpoint.json"
    assert chk_file.is_file()
    chk_data = json.loads(chk_file.read_text())
    assert chk_data["schema_version"] == "stage1_6b_observer_checkpoint_v2"
    assert chk_data["last_index_poll_status"] == "trusted"
    assert chk_data["last_index_poll_coverage"] == "successful"
    assert chk_data["poll_seq"] == 1
    assert chk_data["candidate_states"][article_code]["terminal_reason"] == "trusted_detail_observed"
    date_str = datetime.datetime.fromtimestamp(now_ms / 1000.0, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
    for stream_rel in (
        f"request_manifest/{date_str}.jsonl",
        f"list_captures/{date_str}.jsonl",
        "article_discoveries.jsonl",
        f"detail_observations/{date_str}.jsonl",
        "detail_revisions.jsonl",
        f"observer_heartbeats/{date_str}.jsonl",
    ):
        stream_path = run_root / stream_rel
        assert chk_data["stream_offsets"][stream_rel] == stream_path.stat().st_size
        assert chk_data["stream_last_hashes"][stream_rel] == hashlib.sha256(
            stream_path.read_bytes().rstrip(b"\n").splitlines()[-1]
        ).hexdigest()


def test_observer_lane_a_precedence_and_lane_b_retry(tmp_path):
    """Verify Lane A priority over Lane B, and exponential backoff retry scheduling."""
    run_root, guard = setup_observer(tmp_path, "run_lanes")

    art_1 = "1" * 32
    art_2 = "2" * 32

    # Poll 1 index: contains art_1
    index_1 = make_index_catalog_payload([{"code": art_1, "title": "Binance Futures Will Delist A", "releaseDate": 1732000000000}])
    # Poll 2 index: contains art_1 and art_2
    index_2 = make_index_catalog_payload([
        {"code": art_1, "title": "Binance Futures Will Delist A", "releaseDate": 1732000000000},
        {"code": art_2, "title": "Binance Futures Will Delist B", "releaseDate": 1732000000000},
    ])

    # Detail fails for art_1 on poll 1, succeeds for art_2 on poll 2
    detail_fail = json.dumps({"code": "100000", "message": "temporary error"}).encode("utf-8")
    detail_art_2 = json.dumps({"code": "000000", "data": {"code": art_2, "title": "Delist B", "body": "Body B", "releaseDate": 1732000000000}}).encode("utf-8")

    current_poll = [1]

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_1 if current_poll[0] == 1 else index_2, url=url)
        elif "article/detail/query" in url:
            if art_1 in url:
                return MockHTTPResponse(detail_fail, url=url)
            elif art_2 in url:
                return MockHTTPResponse(detail_art_2, url=url)
        raise ValueError(f"Unexpected url {url}")

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_lanes",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    # Poll 1: art_1 discovered and detail fails -> moves to Lane B
    observer.execute_poll(now_ms=1000)
    c1 = observer.candidate_states[art_1]
    assert c1.lane == CandidateLane.LANE_B.value
    assert c1.retry_cycle_count == 1
    assert c1.next_retry_at_ms == 1000 + 300 * 1000  # min interval 300s

    # Poll 2 at 1000 + 100s: art_2 is discovered (Lane A). Lane A must be chosen even though Lane B exists
    current_poll[0] = 2
    observer.execute_poll(now_ms=1000 + 100 * 1000)
    c2 = observer.candidate_states[art_2]
    assert c2.terminal_reason == "trusted_detail_observed"
    # art_1 is still Lane B and was not attempted in poll 2
    assert observer.candidate_states[art_1].detail_attempt_count == 1


def test_observer_lane_a_sla_exceeded_fails_closed(tmp_path):
    """Verify that unattempted Lane A candidate exceeding DETAIL_FIRST_ATTEMPT_MAX_POLLS triggers terminal SLA error."""
    run_root, guard = setup_observer(tmp_path, "run_sla")

    # Observer receives 3 new candidates in poll 1, but can only attempt 1 per poll
    articles = [
        {"code": f"{i}" * 32, "title": f"Binance Futures Will Delist {i}", "releaseDate": 1732000000000}
        for i in range(1, 4)
    ]
    index_payload = make_index_catalog_payload(articles)
    detail_payload = json.dumps({"code": "000000", "data": {"code": "1" * 32, "body": "ok", "releaseDate": 1732000000000}}).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        return MockHTTPResponse(detail_payload, url=url)

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_sla",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    # Poll 1: discovers 3 articles, attempts article 1
    observer.execute_poll(now_ms=1000)
    # Poll 2: attempts article 2
    observer.execute_poll(now_ms=2000)
    # Poll 3: (poll_seq=3, first_discovered_poll_seq=1, diff=2 >= DETAIL_FIRST_ATTEMPT_MAX_POLLS(2))
    # Article 3 was not attempted within 2 polls window -> raises SLA error
    with pytest.raises(ObserverSLAError, match="detail_first_attempt_sla_exceeded"):
        observer.execute_poll(now_ms=3000)


def test_observer_schema_drift_degraded_checkpoint_and_terminal_error(tmp_path):
    """Task 4.2 & 4.3: Live observer handles malformed selected catalog by writing manifest, degraded checkpoint, and raising schema drift error."""
    from src.research.external_signal_shadow.stage1_6b_canonical_source_observer import (
        Stage16BSchemaDriftError,
    )
    run_root, guard = setup_observer(tmp_path, "run_drift")

    # Index response with wrong catalog ID/name (schema drift)
    malformed_index = json.dumps({
        "code": "000000",
        "data": {
            "catalogs": [
                {"catalogId": 999, "catalogName": "WrongCatalog", "articles": [], "total": 0}
            ]
        },
    }).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        return MockHTTPResponse(malformed_index, url=req.get_full_url())

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_drift",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    now_ms = 1732000000000
    with pytest.raises(Stage16BSchemaDriftError, match="source_profile_schema_drift"):
        observer.execute_poll(now_ms=now_ms)

    # 1. No ListCapture rows
    date_str = datetime.datetime.fromtimestamp(now_ms / 1000.0, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
    lc_file = run_root / "list_captures" / f"{date_str}.jsonl"
    assert not lc_file.exists()

    # 2. No ArticleDiscovery rows
    disc_file = run_root / "article_discoveries.jsonl"
    assert not disc_file.exists()

    # 3. No candidate state progress
    assert len(observer.candidate_states) == 0

    # 4. Exactly one request_manifest row with validation_status=malformed_index_schema
    manifest_file = run_root / "request_manifest" / f"{date_str}.jsonl"
    assert manifest_file.is_file()
    m_lines = manifest_file.read_text().strip().splitlines()
    assert len(m_lines) == 1
    m_row = json.loads(m_lines[0])
    assert m_row["validation_status"] == "malformed_index_schema"
    assert m_row["monotonic_request_seq"] == 1

    # 5. Observer checkpoint v2 with degraded status and coverage
    chk_file = run_root / "observer_checkpoint.json"
    assert chk_file.is_file()
    chk_data = json.loads(chk_file.read_text())
    assert chk_data["schema_version"] == "stage1_6b_observer_checkpoint_v2"
    assert chk_data["last_index_poll_status"] == "malformed_index_schema"
    assert chk_data["last_index_poll_coverage"] == "degraded_not_successful"
    assert chk_data["stream_offsets"][f"request_manifest/{date_str}.jsonl"] == manifest_file.stat().st_size
