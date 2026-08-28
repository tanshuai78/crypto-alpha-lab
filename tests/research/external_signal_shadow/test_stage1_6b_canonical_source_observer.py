"""Unit and reducer tests for Stage 1.6B live observer state machine and scheduling."""

import datetime
import hashlib
import io
import json
import shutil

import pytest

from configs import base
from src.research.external_signal_shadow.stage1_6b_canonical_source_client import (
    Stage16BCanonicalClient,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    CANDIDATE_DISCOVERY_RULE_VERSION,
    SOURCE_PROFILE_ID,
    CandidateLane,
    CandidateState,
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
    def __init__(
        self,
        body_bytes: bytes,
        status: int = 200,
        headers: dict = None,
        url: str = "https://www.binance.com",
    ):
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
    run_root = (
        tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / run_id
    )
    run_root.mkdir(parents=True, exist_ok=True)
    guard = Stage16BStorageGuard(
        output_root=run_root,
        disk_usage_func=lambda p: shutil._ntuple_diskusage(
            100 * 1024**3, 20 * 1024**3, 80 * 1024**3
        ),
    )

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
    return json.dumps(
        {
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
            },
        }
    ).encode("utf-8")


def test_observer_single_poll_lifecycle(tmp_path):
    """Verify one live poll discovers candidate, executes Lane A detail, writes revision and checkpoint."""
    run_root, guard = setup_observer(tmp_path, "run_poll_1")

    article_code = "a" * 32
    index_payload = make_index_catalog_payload(
        [
            {
                "code": article_code,
                "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
                "releaseDate": 1732000000000,
            }
        ]
    )

    detail_payload = json.dumps(
        {
            "code": "000000",
            "data": {
                "code": article_code,
                "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
                "body": "<p>Delisting notice body content</p>",
                "releaseDate": 1732000000000,
            },
        }
    ).encode("utf-8")

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
    assert (
        disc_data["notice_lineage_first_detected_at_ms"] == now_ms
    )  # Anchored live discovery time

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
    assert chk_data["schema_version"] == "stage1_6b_observer_checkpoint_v3"
    assert chk_data["last_index_poll_status"] == "trusted"
    assert chk_data["last_index_poll_coverage"] == "successful"
    assert chk_data["poll_seq"] == 1
    assert chk_data["pending_terminal_failure_reason"] is None
    assert (
        chk_data["candidate_states"][article_code]["terminal_reason"] == "trusted_detail_observed"
    )
    assert chk_data["candidate_states"][article_code]["first_attempt_ahead_count_at_admission"] == 0
    assert chk_data["candidate_states"][article_code]["first_attempt_deadline_poll_seq"] == 1
    date_str = datetime.datetime.fromtimestamp(now_ms / 1000.0, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%d"
    )
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
        assert (
            chk_data["stream_last_hashes"][stream_rel]
            == hashlib.sha256(stream_path.read_bytes().rstrip(b"\n").splitlines()[-1]).hexdigest()
        )


def test_observer_lane_a_precedence_and_lane_b_retry(tmp_path):
    """Verify Lane A priority over Lane B, and exponential backoff retry scheduling."""
    run_root, guard = setup_observer(tmp_path, "run_lanes")

    art_1 = "1" * 32
    art_2 = "2" * 32

    # Poll 1 index: contains art_1
    index_1 = make_index_catalog_payload(
        [{"code": art_1, "title": "Binance Futures Will Delist A", "releaseDate": 1732000000000}]
    )
    # Poll 2 index: contains art_1 and art_2
    index_2 = make_index_catalog_payload(
        [
            {"code": art_1, "title": "Binance Futures Will Delist A", "releaseDate": 1732000000000},
            {"code": art_2, "title": "Binance Futures Will Delist B", "releaseDate": 1732000000000},
        ]
    )

    # Detail fails for art_1 on poll 1, succeeds for art_2 on poll 2
    detail_fail = json.dumps({"code": "100000", "message": "temporary error"}).encode("utf-8")
    detail_art_2 = json.dumps(
        {
            "code": "000000",
            "data": {
                "code": art_2,
                "title": "Delist B",
                "body": "Body B",
                "releaseDate": 1732000000000,
            },
        }
    ).encode("utf-8")

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


def test_observer_four_detail_burst_and_fifo_order(tmp_path):
    """Task 2.1: 4 reverse-order discoveries execute 1 index then 4 details in FIFO (poll, aid) order."""
    run_root, guard = setup_observer(tmp_path, "run_burst_4")

    # Discoveries in catalog in reverse order: d, c, b, a
    articles = [
        {
            "code": f"{letter}" * 32,
            "title": f"Binance Futures Will Delist {letter.upper()}",
            "releaseDate": 1732000000000,
        }
        for letter in ["d", "c", "b", "a"]
    ]
    index_payload = make_index_catalog_payload(articles)
    detail_payloads = {
        f"{letter}" * 32: json.dumps(
            {
                "code": "000000",
                "data": {
                    "code": f"{letter}" * 32,
                    "body": f"Body {letter}",
                    "releaseDate": 1732000000000,
                },
            }
        ).encode("utf-8")
        for letter in ["a", "b", "c", "d"]
    }

    requested_detail_order = []

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        elif "article/detail/query" in url:
            for aid, pl in detail_payloads.items():
                if aid in url:
                    requested_detail_order.append(aid)
                    return MockHTTPResponse(pl, url=url)
        raise ValueError(f"Unexpected url {url}")

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_burst_4",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    now_ms = 1700000000000
    chk = observer.execute_poll(now_ms=now_ms)

    # 1 index + 4 details executed sequentially in lexical order: a, b, c, d
    assert requested_detail_order == ["a" * 32, "b" * 32, "c" * 32, "d" * 32]

    # Ahead count and deadline check for all 4 candidates
    for idx, letter in enumerate(["a", "b", "c", "d"]):
        aid = letter * 32
        cand = observer.candidate_states[aid]
        assert cand.first_attempt_ahead_count_at_admission == idx
        assert cand.first_attempt_deadline_poll_seq == 1
        assert cand.terminal_reason == "trusted_detail_observed"
        assert cand.detail_attempt_count == 1

    assert chk.schema_version == "stage1_6b_observer_checkpoint_v3"
    assert chk.monotonic_request_seq == 5  # 1 index + 4 details


def test_observer_eight_discoveries_split_across_two_polls(tmp_path):
    """Task 2.2: 8 discoveries in poll 1: candidates 0..3 deadline poll 1, 4..7 deadline poll 2."""
    run_root, guard = setup_observer(tmp_path, "run_burst_8")

    articles = [
        {
            "code": f"{i:02d}" * 16,
            "title": f"Binance Futures Will Delist Token {i}",
            "releaseDate": 1732000000000,
        }
        for i in range(1, 10)  # 9 articles
    ]
    index_payload = make_index_catalog_payload(articles)

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        elif "article/detail/query" in url:
            return MockHTTPResponse(b'{"code":"000000","data":{"body":"ok"}}', url=url)
        raise ValueError(f"Unexpected url {url}")

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_burst_8",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    # Poll 1: 9 discoveries admitted. 4 details executed.
    observer.execute_poll(now_ms=1000)
    for i in range(1, 5):  # 1..4 (ahead 0..3)
        aid = f"{i:02d}" * 16
        c = observer.candidate_states[aid]
        assert c.first_attempt_ahead_count_at_admission == i - 1
        assert c.first_attempt_deadline_poll_seq == 1
        assert c.detail_attempt_count == 1
    for i in range(5, 9):  # 5..8 (ahead 4..7)
        aid = f"{i:02d}" * 16
        c = observer.candidate_states[aid]
        assert c.first_attempt_ahead_count_at_admission == i - 1
        assert c.first_attempt_deadline_poll_seq == 2
        assert c.detail_attempt_count == 0
    # 9th candidate (ahead 8 -> deadline 1 + 8//4 = 3)
    c9 = observer.candidate_states[f"{9:02d}" * 16]
    assert c9.first_attempt_ahead_count_at_admission == 8
    assert c9.first_attempt_deadline_poll_seq == 3
    assert c9.detail_attempt_count == 0

    # Poll 2: next 4 details executed (candidates 5..8)
    observer.execute_poll(now_ms=2000)
    for i in range(5, 9):
        aid = f"{i:02d}" * 16
        c = observer.candidate_states[aid]
        assert c.detail_attempt_count == 1
    assert observer.candidate_states[f"{9:02d}" * 16].detail_attempt_count == 0


def test_observer_lane_b_does_not_fill_unused_budget_when_lane_a_present(tmp_path):
    """Task 2.3: When Lane A has 1 candidate and Lane B has 2 due retries, only Lane A is executed."""
    run_root, guard = setup_observer(tmp_path, "run_lane_priority")

    art_b1 = "1" * 32
    art_b2 = "2" * 32
    art_a = "3" * 32

    # Poll 1: art_b1 and art_b2 fail and move to Lane B
    index_1 = make_index_catalog_payload(
        [
            {
                "code": art_b1,
                "title": "Binance Futures Will Delist 1",
                "releaseDate": 1732000000000,
            },
            {
                "code": art_b2,
                "title": "Binance Futures Will Delist 2",
                "releaseDate": 1732000000000,
            },
        ]
    )
    index_2 = make_index_catalog_payload(
        [
            {
                "code": art_b1,
                "title": "Binance Futures Will Delist 1",
                "releaseDate": 1732000000000,
            },
            {
                "code": art_b2,
                "title": "Binance Futures Will Delist 2",
                "releaseDate": 1732000000000,
            },
            {"code": art_a, "title": "Binance Futures Will Delist 3", "releaseDate": 1732000000000},
        ]
    )

    current_poll = [1]
    executed_details = []

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_1 if current_poll[0] == 1 else index_2, url=url)
        elif "article/detail/query" in url:
            for aid in [art_b1, art_b2, art_a]:
                if aid in url:
                    executed_details.append(aid)
                    if aid in [art_b1, art_b2]:
                        return MockHTTPResponse(b'{"code":"100000","message":"fail"}', url=url)
                    return MockHTTPResponse(b'{"code":"000000","data":{"body":"ok"}}', url=url)
        raise ValueError(f"Unexpected url {url}")

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_lane_priority",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    # Poll 1: art_b1 and art_b2 fail -> moved to Lane B
    observer.execute_poll(now_ms=1000)
    assert observer.candidate_states[art_b1].lane == CandidateLane.LANE_B.value
    assert observer.candidate_states[art_b2].lane == CandidateLane.LANE_B.value

    # Poll 2: at time where Lane B retries are due (1000 + 400s), but art_a is discovered (Lane A).
    # Lane A MUST be executed alone without Lane B filling the remaining 3 budget slots.
    current_poll[0] = 2
    executed_details.clear()
    observer.execute_poll(now_ms=1000 + 400 * 1000)

    assert executed_details == [art_a]
    assert observer.candidate_states[art_a].detail_attempt_count == 1
    assert observer.candidate_states[art_b1].detail_attempt_count == 1
    assert observer.candidate_states[art_b2].detail_attempt_count == 1


def test_observer_subsequent_discovery_cannot_mutate_prior_deadline_or_jump_fifo(tmp_path):
    """Task 2.4: Subsequent discoveries append to FIFO queue and cannot alter prior deadlines."""
    run_root, guard = setup_observer(tmp_path, "run_fifo_immutability")

    arts_p1 = [
        {
            "code": f"1{i:031x}",
            "title": f"Binance Futures Will Delist P1_{i}",
            "releaseDate": 1732000000000,
        }
        for i in range(1, 7)
    ]
    arts_p2 = arts_p1 + [
        {
            "code": f"2{i:031x}",
            "title": f"Binance Futures Will Delist P2_{i}",
            "releaseDate": 1732000000000,
        }
        for i in range(1, 3)
    ]

    current_poll = [1]

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(
                make_index_catalog_payload(arts_p1 if current_poll[0] == 1 else arts_p2), url=url
            )
        elif "article/detail/query" in url:
            return MockHTTPResponse(b'{"code":"000000","data":{"body":"ok"}}', url=url)
        raise ValueError(f"Unexpected url {url}")

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_fifo_immutability",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    # Poll 1: 6 candidates. 4 attempted. Candidates 5 and 6 remain unattempted with ahead=4, 5 and deadline=2.
    observer.execute_poll(now_ms=1000)
    c5 = observer.candidate_states[f"1{5:031x}"]
    c6 = observer.candidate_states[f"1{6:031x}"]
    assert c5.first_attempt_ahead_count_at_admission == 4
    assert c5.first_attempt_deadline_poll_seq == 2
    assert c6.first_attempt_ahead_count_at_admission == 5
    assert c6.first_attempt_deadline_poll_seq == 2

    # Poll 2: 2 new candidates discovered. They must get ahead=6, 7 and deadline=2.
    current_poll[0] = 2
    observer.execute_poll(now_ms=2000)

    # Prior unattempted candidates retain their immutable admission values
    assert observer.candidate_states[f"1{5:031x}"].first_attempt_ahead_count_at_admission == 4
    assert observer.candidate_states[f"1{5:031x}"].first_attempt_deadline_poll_seq == 2
    assert observer.candidate_states[f"1{6:031x}"].first_attempt_ahead_count_at_admission == 5
    assert observer.candidate_states[f"1{6:031x}"].first_attempt_deadline_poll_seq == 2

    # New candidates from Poll 2 have ahead starting after existing unattempted (ahead=2, 3)
    c_p2_1 = observer.candidate_states[f"2{1:031x}"]
    c_p2_2 = observer.candidate_states[f"2{2:031x}"]
    assert c_p2_1.first_attempt_ahead_count_at_admission == 2
    assert c_p2_1.first_attempt_deadline_poll_seq == 2 + (2 // 4)  # 2 + 0 = 2
    assert c_p2_2.first_attempt_ahead_count_at_admission == 3
    assert c_p2_2.first_attempt_deadline_poll_seq == 2 + (3 // 4)  # 2 + 0 = 2


def test_observer_deadline_missed_raises_sla_error_with_code(tmp_path):
    """Task 2.5: Unattempted Lane A candidate exceeding deadline raises ObserverSLAError with code."""
    run_root, guard = setup_observer(tmp_path, "run_deadline_miss")

    art = "a" * 32
    index_payload = make_index_catalog_payload(
        [{"code": art, "title": "Binance Futures Will Delist A", "releaseDate": 1732000000000}]
    )

    def mock_opener(req, timeout=10.0):
        return MockHTTPResponse(index_payload, url=req.get_full_url())

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_deadline_miss",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    # Manually inject an unattempted candidate with deadline=1 at poll_seq=1
    observer.candidate_states[art] = CandidateState(
        source_article_id=art,
        first_discovered_poll_seq=1,
        first_discovered_at_ms=1000,
        lane=CandidateLane.LANE_A.value,
        detail_attempt_count=0,
        retry_cycle_count=0,
        first_attempt_at_ms=None,
        last_attempt_at_ms=None,
        next_retry_at_ms=None,
        terminal_reason=None,
        trusted_detail_revision_id=None,
        first_attempt_ahead_count_at_admission=0,
        first_attempt_deadline_poll_seq=1,
    )
    observer.poll_seq = 1  # Next poll will be poll_seq = 2 > deadline(1)

    with pytest.raises(ObserverSLAError) as exc_info:
        observer.execute_poll(now_ms=2000)

    assert exc_info.value.code == "detail_first_attempt_deadline_missed"


def test_observer_capacity_exceeded_raises_capacity_error_with_code(tmp_path, monkeypatch):
    """Task 2.6: Pending candidates exceeding capacity limit raises ObserverCapacityError with code."""
    from src.research.external_signal_shadow.stage1_6b_canonical_source_observer import (
        ObserverCapacityError,
    )

    run_root, guard = setup_observer(tmp_path, "run_cap")

    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES", 2)

    articles = [
        {
            "code": f"{i}" * 32,
            "title": f"Binance Futures Will Delist {i}",
            "releaseDate": 1732000000000,
        }
        for i in range(1, 5)  # 4 articles
    ]
    index_payload = make_index_catalog_payload(articles)

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        return MockHTTPResponse(b'{"code":"100000","message":"fail"}', url=url)

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_cap",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    with pytest.raises(ObserverCapacityError) as exc_info:
        observer.execute_poll(now_ms=1000)

    assert exc_info.value.code == "pending_detail_candidate_capacity_exceeded"


def test_observer_four_details_storage_guard_admitted_write_spy(tmp_path):
    """Task 2.9: Each of the 4 details independently admits raw payload, DetailObservation, and DetailRevision."""
    run_root, guard = setup_observer(tmp_path, "run_spy")

    admitted_calls = []
    orig_admitted_write = guard.admitted_write

    def spy_admitted_write(write_class, *args, **kwargs):
        admitted_calls.append(write_class)
        return orig_admitted_write(write_class, *args, **kwargs)

    guard.admitted_write = spy_admitted_write

    articles = [
        {
            "code": f"{letter}" * 32,
            "title": f"Binance Futures Will Delist {letter.upper()}",
            "releaseDate": 1732000000000,
        }
        for letter in ["a", "b", "c", "d"]
    ]
    index_payload = make_index_catalog_payload(articles)
    detail_payload = json.dumps(
        {"code": "000000", "data": {"code": "a" * 32, "body": "ok", "releaseDate": 1732000000000}}
    ).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        return MockHTTPResponse(detail_payload, url=url)

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_spy",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    observer.execute_poll(now_ms=1000)

    # Prove independent admissions for each detail
    normal_data_calls = [c for c in admitted_calls if c == "normal_data"]
    # 1 index manifest + 1 index raw + 1 list capture + 4 discoveries + 4 * (1 detail raw + 1 detail obs + 1 detail rev)
    assert len(normal_data_calls) >= 1 + 1 + 1 + 4 + (4 * 3)


def test_observer_dynamic_budget_monkeypatch_no_magic_number(tmp_path, monkeypatch):
    """Task 2.10: Monkeypatching base live detail budget changes selection and deadline batching."""
    run_root, guard = setup_observer(tmp_path, "run_dynamic_budget")

    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_6B_LIVE_MAX_DETAIL_REQUESTS_PER_POLL", 2)

    articles = [
        {
            "code": f"{letter}" * 32,
            "title": f"Binance Futures Will Delist {letter.upper()}",
            "releaseDate": 1732000000000,
        }
        for letter in ["a", "b", "c", "d"]
    ]
    index_payload = make_index_catalog_payload(articles)
    detail_payload = json.dumps(
        {"code": "000000", "data": {"code": "a" * 32, "body": "ok", "releaseDate": 1732000000000}}
    ).encode("utf-8")

    executed_details = []

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        elif "article/detail/query" in url:
            for letter in ["a", "b", "c", "d"]:
                if letter * 32 in url:
                    executed_details.append(letter * 32)
            return MockHTTPResponse(detail_payload, url=url)
        raise ValueError(f"Unexpected url {url}")

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_dynamic_budget",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    # Poll 1 with budget=2 should execute only 2 details (a, b) and assign deadlines (c, d deadline=2)
    observer.execute_poll(now_ms=1000)
    assert executed_details == ["a" * 32, "b" * 32]
    assert observer.candidate_states["c" * 32].first_attempt_deadline_poll_seq == 2
    assert observer.candidate_states["d" * 32].first_attempt_deadline_poll_seq == 2


def test_observer_failure_intent_checkpoint_writer(tmp_path):
    """Task 2.6 / Task 4: Observer writes failure-intent checkpoint with pending_terminal_failure_reason."""
    from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
        compute_live_v3_checkpoint_id,
    )

    run_root, guard = setup_observer(tmp_path, "run_intent")

    client = Stage16BCanonicalClient(live_public_readonly=True)
    observer = Stage16BObserver(
        run_root=run_root,
        run_id="run_intent",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_attestation_sha256="dummy_att_sha",
        guard=guard,
        client=client,
    )

    chk = observer.write_failure_intent_checkpoint(
        now_ms=1700000000000,
        failure_reason="detail_first_attempt_deadline_missed",
    )
    assert chk.schema_version == "stage1_6b_observer_checkpoint_v3"
    assert chk.pending_terminal_failure_reason == "detail_first_attempt_deadline_missed"
    chk_dict = chk.to_dict()
    assert chk.checkpoint_id == compute_live_v3_checkpoint_id(chk_dict)

    # Verify on-disk checkpoint
    chk_file = run_root / "observer_checkpoint.json"
    assert chk_file.is_file()
    disk_chk = json.loads(chk_file.read_text())
    assert disk_chk["pending_terminal_failure_reason"] == "detail_first_attempt_deadline_missed"
    assert disk_chk["checkpoint_id"] == chk.checkpoint_id


def test_observer_schema_drift_degraded_checkpoint_and_terminal_error(tmp_path):
    """Task 4.2 & 4.3: Live observer handles malformed selected catalog by writing manifest, degraded checkpoint, and raising schema drift error."""
    from src.research.external_signal_shadow.stage1_6b_canonical_source_observer import (
        Stage16BSchemaDriftError,
    )

    run_root, guard = setup_observer(tmp_path, "run_drift")

    # Index response with wrong catalog ID/name (schema drift)
    malformed_index = json.dumps(
        {
            "code": "000000",
            "data": {
                "catalogs": [
                    {"catalogId": 999, "catalogName": "WrongCatalog", "articles": [], "total": 0}
                ]
            },
        }
    ).encode("utf-8")

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
    with pytest.raises(Stage16BSchemaDriftError, match="source_profile_schema_drift") as exc_info:
        observer.execute_poll(now_ms=now_ms)
    assert exc_info.value.code == "source_profile_schema_drift"

    # 1. No ListCapture rows
    date_str = datetime.datetime.fromtimestamp(now_ms / 1000.0, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%d"
    )
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

    # 5. Observer checkpoint v3 with degraded status and coverage
    chk_file = run_root / "observer_checkpoint.json"
    assert chk_file.is_file()
    chk_data = json.loads(chk_file.read_text())
    assert chk_data["schema_version"] == "stage1_6b_observer_checkpoint_v3"
    assert chk_data["last_index_poll_status"] == "malformed_index_schema"
    assert chk_data["last_index_poll_coverage"] == "degraded_not_successful"
    assert (
        chk_data["stream_offsets"][f"request_manifest/{date_str}.jsonl"]
        == manifest_file.stat().st_size
    )
