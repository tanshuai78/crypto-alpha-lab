from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from src.research.external_signal_shadow.safety import canonical_json_dumps
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    write_stage1_5g_review_manifest,
)
from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import (
    Stage1_5HInputBundle,
    load_stage1_5h_inputs,
)

# New interfaces to be tested
try:
    from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import (
        build_stage1_5h_v2_event_bundle_reports,
        verify_stage1_5h_v2_event_bundle_manifest,
        write_stage1_5h_v2_event_bundle_reports,
    )
except ImportError:
    build_stage1_5h_v2_event_bundle_reports = None
    verify_stage1_5h_v2_event_bundle_manifest = None
    write_stage1_5h_v2_event_bundle_reports = None

GOVERNANCE_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md"
)


def event_symbol_id(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def tree_digest(root: Path) -> str:
    if not root.exists():
        return "MISSING"
    lines = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            lines.append(f"{p.relative_to(root).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}")
        elif p.is_dir():
            lines.append(f"{p.relative_to(root).as_posix()}:DIR")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def make_v2_bundle_fixture(
    tmp_path: Path,
    *,
    mutation: str | None = None,
    first_quality: dict[str, Any] | None = None,
    second_quality: dict[str, Any] | None = None,
) -> tuple[Stage1_5HInputBundle, list[str]]:
    root = tmp_path / "stage1_5g_run"
    root.mkdir(parents=True, exist_ok=True)

    id_a = event_symbol_id("event-a|AAAUSDT")
    id_b = event_symbol_id("event-a|BBBUSDT")
    ids = sorted([id_a, id_b])

    if mutation == "duplicate_id":
        ids = [id_a, id_a]
    elif mutation == "unsorted_id":
        ids = [ids[1], ids[0]]
    elif mutation == "unsafe_id_escape":
        ids = ["../escaped", id_b]
    elif mutation == "unsafe_id_upper":
        ids = [id_a.upper(), id_b]

    formal_hash = hashlib.sha256(canonical_json_dumps(ids).encode("utf-8")).hexdigest()
    source_sha = "46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918"

    review_payload = {
        "formal_completed_event_symbol_ids": ids,
        "schema_version": 2,
        "source_evidence_manifest_sha256": source_sha,
    }
    review_id = hashlib.sha256(canonical_json_dumps(review_payload).encode("utf-8")).hexdigest()

    q1 = first_quality or {
        "spread_bps_p50": 10.0,
        "spread_bps_p95": 20.0,
        "buy_slippage_bps_500usdt_p50": 5.0,
        "buy_slippage_bps_500usdt_p95": 15.0,
        "sell_slippage_bps_500usdt_p50": 5.0,
        "sell_slippage_bps_500usdt_p95": 15.0,
        "top_bid_depth_usdt_p05": 5000.0,
        "top_bid_depth_usdt_p50": 10000.0,
        "top_ask_depth_usdt_p05": 5000.0,
        "top_ask_depth_usdt_p50": 10000.0,
        "healthy_window_ratio": 1.0,
        "input_valid_rows": 720,
        "excluded_invalid_rows": 0,
        "blockers": [],
        "warnings": [],
    }
    q2 = second_quality or {
        "spread_bps_p50": 12.0,
        "spread_bps_p95": 22.0,
        "buy_slippage_bps_500usdt_p50": 6.0,
        "buy_slippage_bps_500usdt_p95": 16.0,
        "sell_slippage_bps_500usdt_p50": 6.0,
        "sell_slippage_bps_500usdt_p95": 16.0,
        "top_bid_depth_usdt_p05": 4000.0,
        "top_bid_depth_usdt_p50": 9000.0,
        "top_ask_depth_usdt_p05": 4000.0,
        "top_ask_depth_usdt_p50": 9000.0,
        "healthy_window_ratio": 1.0,
        "input_valid_rows": 719,
        "excluded_invalid_rows": 1,
        "blockers": [],
        "warnings": [],
    }

    sym_a = "AAAUSDT"
    sym_b = "BBBUSDT"

    per_symbol_metrics = {
        ids[0]: {
            "symbol": sym_a,
            "observed_snapshot_count": 720,
            "valid_snapshot_count_after_quarantine": 720,
            "invalid_book_row_count": 0,
            "book_availability_ratio": 1.0,
            "book_unavailable_ratio": 0.0,
            "invalid_book_ratio": 0.0,
            "first_valid_book_latency_ms": 0,
            "max_consecutive_invalid": 0,
            "max_consecutive_invalid_after_warmup": 0,
            "clean_depth_evidence_pass": True,
            "quarantined_depth_evidence_pass": False,
            "blockers": ["some_blocker"] if mutation == "upstream_blocker" else [],
            "warnings": [],
            "invalid_book_by_phase": {"launch_warmup": 0, "observation_initial": 0, "midrun": 0},
            "invalid_book_by_reason": {"launch_warmup_empty_book": 0, "observation_initial_empty_book": 0, "midrun_empty_book": 0, "crossed_or_negative_book": 0, "schema_invalid": 0},
            "quarantined_depth_quality": q1,
        },
        ids[1]: {
            "symbol": sym_b,
            "observed_snapshot_count": 720,
            "valid_snapshot_count_after_quarantine": 719,
            "invalid_book_row_count": 1,
            "book_availability_ratio": 719 / 720,
            "book_unavailable_ratio": 1 / 720,
            "invalid_book_ratio": 1 / 720,
            "first_valid_book_latency_ms": 60000,
            "max_consecutive_invalid": 1,
            "max_consecutive_invalid_after_warmup": 0,
            "clean_depth_evidence_pass": False,
            "quarantined_depth_evidence_pass": True,
            "blockers": [],
            "warnings": [],
            "invalid_book_by_phase": {"launch_warmup": 1 if mutation != "phase_total_mismatch" else 0, "observation_initial": 0, "midrun": 0},
            "invalid_book_by_reason": {"launch_warmup_empty_book": 1, "observation_initial_empty_book": 0, "midrun_empty_book": 0, "crossed_or_negative_book": 0, "schema_invalid": 0},
            "quarantined_depth_quality": q2,
        },
    }
    if mutation == "missing_authoritative_quality":
        per_symbol_metrics[ids[0]].pop("quarantined_depth_quality")
    elif mutation == "missing_required_quality_metric":
        per_symbol_metrics[ids[0]]["quarantined_depth_quality"].pop("spread_bps_p95")
    elif mutation == "nonnumeric_quality_metric":
        per_symbol_metrics[ids[0]]["quarantined_depth_quality"]["spread_bps_p95"] = "not-a-number"
    elif mutation == "missing_per_symbol_blockers":
        per_symbol_metrics[ids[0]].pop("blockers")

    event_level_decisions = [
        {"event_symbol_id": ids[0], "symbol": sym_a, "source_article_id": "" if mutation == "empty_source_article" else "art1", "event_id": "ev1", "state_status": "completed", "formal_completed": mutation != "formal_completed_false"},
        {"event_symbol_id": ids[1], "symbol": sym_b if mutation != "symbol_mismatch" else "WRONGUSDT", "source_article_id": "art1", "event_id": "ev1", "state_status": "completed", "formal_completed": True},
    ]
    if mutation == "duplicate_formal_identity":
        event_level_decisions.append(dict(event_level_decisions[0]))

    quarantine_summary = {
        "schema_version": 2,
        "stage1_5g_review_id": review_id,
        "source_evidence_manifest_sha256": source_sha,
        "formal_completed_event_symbol_ids_sha256": formal_hash,
        "clean_depth_evidence_pass": False if mutation != "clean_v2_input" else True,
        "quarantined_depth_evidence_pass": True if mutation != "clean_v2_input" else False,
        "formal_completed_symbol_count": 2 if mutation != "count_mismatch" else 3,
        "eligible_event_symbol_ids": ids,
        "per_symbol_expected_snapshot_count": 720,
        "total_expected_snapshot_count": 1440,
        "aggregate_observed_snapshot_count": 1440,
        "aggregate_valid_snapshot_count_after_quarantine": 1439,
        "aggregate_invalid_book_row_count": 1,
        "aggregate_book_availability_ratio": 1439 / 1440,
        "aggregate_book_unavailable_ratio": 1 / 1440,
        "aggregate_invalid_book_ratio": 1 / 1440,
        "first_valid_book_latency_ms": 60000,
        "max_consecutive_invalid": 1,
        "max_consecutive_invalid_after_warmup": 0,
        "per_symbol_quarantine_metrics": per_symbol_metrics,
        "blockers": [],
        "warnings": [],
    }

    summary = {
        "schema_version": 2,
        "stage1_5g_review_id": review_id if mutation != "identity_mismatch" else "wrong_review_id",
        "source_evidence_manifest_sha256": source_sha,
        "formal_completed_event_symbol_ids_sha256": formal_hash,
        "decision": "stage1_5g_depth_evidence_quarantined_pass" if mutation != "clean_v2_input" else "stage1_5g_depth_evidence_clean_pass",
        "allowed_next_action": "write_stage1_5h_design_only",
        "evidence_scope": "single_event",
        "clean_depth_evidence_pass": False if mutation != "clean_v2_input" else True,
        "quarantined_depth_evidence_pass": True if mutation != "clean_v2_input" else False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "execution_feasibility_claim_allowed": False,
        "formal_announcement_and_launch_count": 2,
        "reviewed_event_symbols": ids,
        "event_level_decisions": event_level_decisions,
        "blockers": [],
        "warnings": [],
        "quarantine": dict(quarantine_summary) if mutation != "projection_mismatch" else {**quarantine_summary, "formal_completed_symbol_count": 99},
        "depth_quality": {
            "depth_quality_input_mode": "quarantined_valid_rows",
            "depth_quality_input_row_count": 1439,
            "excluded_invalid_book_row_count": 1,
        },
    }

    valid_rows = []
    for _ in range(720):
        valid_rows.append({"event_symbol_id": ids[0], "symbol": sym_a, "best_bid": 100.0, "best_ask": 100.1, "spread_bps": 10.0, "buy_slippage_bps": 5.0, "sell_slippage_bps": 5.0, "top_bid_depth_usdt": 5000.0, "top_ask_depth_usdt": 5000.0})
    for _ in range(719):
        valid_rows.append({"event_symbol_id": ids[1], "symbol": sym_b, "best_bid": 200.0, "best_ask": 200.2, "spread_bps": 10.0, "buy_slippage_bps": 5.0, "sell_slippage_bps": 5.0, "top_bid_depth_usdt": 5000.0, "top_ask_depth_usdt": 5000.0})
    if mutation == "foreign_row":
        valid_rows.append({"event_symbol_id": "foreign_id_not_in_s", "symbol": "FOREIGN", "best_bid": 1.0, "best_ask": 1.1})
    elif mutation == "jsonl_symbol_mismatch":
        valid_rows[0]["symbol"] = "WRONGUSDT"

    invalid_rows = [
        {"event_symbol_id": ids[1], "symbol": sym_b, "quarantine_phase": "launch_warmup", "quarantine_reason": "launch_warmup_empty_book", "depth_status": "invalid"}
    ]

    summary_path = write_json(root / "stage1_5g_live_depth_evidence_review_summary.json", summary)
    quarantine_path = write_json(root / "stage1_5g_quarantine_summary.json", quarantine_summary)
    valid_rows_path = write_jsonl(root / "depth_quality_input_rows.jsonl", valid_rows)
    invalid_rows_path = write_jsonl(root / "quarantined_invalid_book_rows.jsonl", invalid_rows)

    write_stage1_5g_review_manifest(root, summary, {
        "summary": summary_path,
        "quarantine_summary": quarantine_path,
        "depth_quality_input_rows": valid_rows_path,
        "quarantined_invalid_book_rows": invalid_rows_path,
    })

    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=summary_path,
        quarantine_summary_path=quarantine_path,
        depth_quality_input_rows_path=valid_rows_path,
        quarantined_invalid_book_rows_path=invalid_rows_path,
        governance_review_path=GOVERNANCE_PATH,
    )
    return bundle, ids


def test_v2_bundle_builds_exactly_one_prepared_report_per_formal_id(tmp_path):
    bundle, ids = make_v2_bundle_fixture(tmp_path)
    result = build_stage1_5h_v2_event_bundle_reports(bundle)
    assert result["decision"] == "stage1_5h_v2_event_bundle_reports_ready"
    assert result["event_symbol_ids"] == ids
    assert set(result["reports"]) == set(ids)
    assert all(row["execution_feasibility_claim_allowed"] is False for row in result["reports"].values())
    assert all(row["trade_signal_allowed"] is False for row in result["reports"].values())
    assert all(row["live_trading_allowed"] is False for row in result["reports"].values())
    assert all(row["paper_trading_allowed"] is False for row in result["reports"].values())


@pytest.mark.parametrize("mutation", [
    "clean_v2_input",
    "duplicate_id",
    "unsorted_id",
    "projection_mismatch",
    "foreign_row",
    "symbol_mismatch",
    "count_mismatch",
    "identity_mismatch",
    "upstream_blocker",
    "phase_total_mismatch",
    "unsafe_id_escape",
    "unsafe_id_upper",
    "jsonl_symbol_mismatch",
    "duplicate_formal_identity",
    "empty_source_article",
    "formal_completed_false",
    "missing_authoritative_quality",
    "missing_required_quality_metric",
    "nonnumeric_quality_metric",
    "missing_per_symbol_blockers",
])
def test_v2_bundle_rejects_closed_bundle_semantic_contradictions(tmp_path, mutation):
    bundle, _ = make_v2_bundle_fixture(tmp_path, mutation=mutation)
    result = build_stage1_5h_v2_event_bundle_reports(bundle)
    assert result["decision"] == "stage1_5h_v2_event_bundle_input_rejected"
    assert result["report_generation_allowed"] is False
    assert result["reports"] == {}


def test_v2_clean_bundle_uses_the_frozen_rejection_taxonomy(tmp_path):
    bundle, _ = make_v2_bundle_fixture(tmp_path, mutation="clean_v2_input")
    result = build_stage1_5h_v2_event_bundle_reports(bundle)
    assert "stage1_5h_v2_clean_bundle_not_authorized" in result["blockers"]


def test_v2_two_identical_rows_with_matching_metric_count_does_not_produce_duplicate_row_blocker(tmp_path):
    bundle, ids = make_v2_bundle_fixture(tmp_path)
    result = build_stage1_5h_v2_event_bundle_reports(bundle)
    assert result["decision"] == "stage1_5h_v2_event_bundle_reports_ready"
    assert "duplicate_rows" not in result.get("blockers", [])


def test_v2_reports_never_borrow_another_symbol_metrics_or_identity(tmp_path):
    bundle, ids = make_v2_bundle_fixture(
        tmp_path,
        first_quality={"spread_bps_p50": 1.0, "spread_bps_p95": 2.0, "buy_slippage_bps_500usdt_p50": 2.0, "buy_slippage_bps_500usdt_p95": 3.0, "sell_slippage_bps_500usdt_p50": 2.0, "sell_slippage_bps_500usdt_p95": 3.0, "top_bid_depth_usdt_p05": 5000.0, "top_ask_depth_usdt_p05": 5000.0, "healthy_window_ratio": 1.0, "input_valid_rows": 720, "excluded_invalid_rows": 0, "blockers": [], "warnings": []},
        second_quality={"spread_bps_p50": 10.0, "spread_bps_p95": 20.0, "buy_slippage_bps_500usdt_p50": 20.0, "buy_slippage_bps_500usdt_p95": 30.0, "sell_slippage_bps_500usdt_p50": 20.0, "sell_slippage_bps_500usdt_p95": 30.0, "top_bid_depth_usdt_p05": 4000.0, "top_ask_depth_usdt_p05": 4000.0, "healthy_window_ratio": 1.0, "input_valid_rows": 719, "excluded_invalid_rows": 1, "blockers": [], "warnings": []},
    )
    reports = build_stage1_5h_v2_event_bundle_reports(bundle)["reports"]
    identity_rows = {row["event_symbol_id"]: row for row in bundle.stage1_5g_summary["event_level_decisions"]}

    assert reports[ids[0]]["static_proxy_metrics"]["spread_bps_p95"] == 2.0
    assert reports[ids[1]]["static_proxy_metrics"]["spread_bps_p95"] == 20.0
    assert reports[ids[0]]["upstream_stage1_5g_status"] == "clean"
    assert reports[ids[1]]["upstream_stage1_5g_status"] == "quarantined"

    for event_symbol_id in ids:
        row = reports[event_symbol_id]
        assert row["event_symbol_id"] == event_symbol_id
        assert row["symbol"] == identity_rows[event_symbol_id]["symbol"]
        assert row["source_article_id"] == identity_rows[event_symbol_id]["source_article_id"]
        assert row["stage1_5g_review_id"] == bundle.stage1_5g_summary["stage1_5g_review_id"]
        assert row["source_evidence_manifest_sha256"] == bundle.stage1_5g_summary["source_evidence_manifest_sha256"]
        assert row["formal_completed_event_symbol_ids_sha256"] == bundle.stage1_5g_summary["formal_completed_event_symbol_ids_sha256"]


def test_v2_markdown_projection_cannot_add_authority_terms(tmp_path):
    bundle, _ = make_v2_bundle_fixture(tmp_path)
    prepared = build_stage1_5h_v2_event_bundle_reports(bundle)
    markdown = prepared["reports"][prepared["event_symbol_ids"][0]]["markdown"]
    for term in ("SignalCandidate", "TradeIntent", "tradeable", "profitable", "buy instruction"):
        assert term not in markdown


def test_v2_governance_rejects_lookalike_or_wrong_path_governance(tmp_path):
    bundle, _ = make_v2_bundle_fixture(tmp_path)
    fake_gov = tmp_path / "fake_governance.md"
    fake_gov.write_text(GOVERNANCE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    bundle_fake = load_stage1_5h_inputs(
        stage1_5g_summary_path=bundle.stage1_5g_summary_path,
        quarantine_summary_path=bundle.quarantine_summary_path,
        depth_quality_input_rows_path=bundle.depth_quality_input_rows_path,
        quarantined_invalid_book_rows_path=bundle.quarantined_invalid_book_rows_path,
        governance_review_path=fake_gov,
    )
    result = build_stage1_5h_v2_event_bundle_reports(bundle_fake)
    assert result["decision"] == "stage1_5h_v2_event_bundle_input_rejected"
    assert "governance_approval_missing" in result["blockers"]


def test_v2_writer_seals_exact_reports_directory_and_manifest(tmp_path, monkeypatch):
    import src.research.external_signal_shadow.stage1_5h_read_only_report_generator as mod
    reports_root = tmp_path / "reports_root"
    reports_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "_STAGE1_5H_V2_REPORTS_ROOT", reports_root)

    bundle, ids = make_v2_bundle_fixture(tmp_path)
    out = reports_root / "fresh_run_1"
    result = write_stage1_5h_v2_event_bundle_reports(bundle=bundle, output_root=out)
    assert result["decision"] == "stage1_5h_v2_event_bundle_reports_sealed"

    ok, blockers = verify_stage1_5h_v2_event_bundle_manifest(out)
    assert ok is True
    assert blockers == []

    manifest = json.loads((out / "stage1_5h_event_bundle_manifest.json").read_text())
    assert set(manifest) == {
        "schema_version", "bundle_status", "upstream", "event_symbol_ids",
        "event_directory", "reports",
        "execution_feasibility_claim_allowed", "alpha_interpretation_allowed",
        "trade_signal_allowed", "paper_trading_allowed", "live_trading_allowed",
        "execution_engine_allowed", "private_endpoint_allowed", "api_key_allowed",
        "order_endpoint_allowed",
    }
    assert set(manifest["upstream"]) == {
        "stage1_5g_review_id", "source_evidence_manifest_sha256",
        "formal_completed_event_symbol_ids_sha256", "stage1_5g_review_manifest_sha256",
    }
    assert all(set(item) == {
        "json_relative_path", "json_sha256", "md_relative_path", "md_sha256",
        "upstream_stage1_5g_status", "stage1_5h_static_proxy_status",
    } for item in manifest["reports"].values())
    for event_symbol_id in ids:
        report = json.loads((out / "reports" / f"{event_symbol_id}.json").read_text())
        assert report["stage1_5h_static_proxy_status"] == (
            "within_limits" if not report["stage1_5h_static_proxy_blockers"] else "blocked"
        )

    manifest["unexpected"] = True
    (out / "stage1_5h_event_bundle_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    ok, blockers = verify_stage1_5h_v2_event_bundle_manifest(out)
    assert ok is False
    assert blockers == ["stage1_5h_v2_event_bundle_manifest_invalid"]


def test_v2_verifier_rejects_semantically_inconsistent_status_or_manifest_types(tmp_path, monkeypatch):
    import src.research.external_signal_shadow.stage1_5h_read_only_report_generator as mod

    reports_root = tmp_path / "reports_root"
    reports_root.mkdir()
    monkeypatch.setattr(mod, "_STAGE1_5H_V2_REPORTS_ROOT", reports_root)
    bundle, ids = make_v2_bundle_fixture(tmp_path)
    out = reports_root / "fresh_run"
    write_stage1_5h_v2_event_bundle_reports(bundle=bundle, output_root=out)

    manifest_path = out / "stage1_5h_event_bundle_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    event_symbol_id = ids[0]
    report_path = out / "reports" / f"{event_symbol_id}.json"
    report = json.loads(report_path.read_text())
    report["stage1_5h_static_proxy_status"] = "within_limits"
    report_bytes = json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8")
    report_path.write_bytes(report_bytes)
    markdown_path = out / "reports" / f"{event_symbol_id}.md"
    markdown_bytes = (mod._render_stage1_5h_v2_event_bundle_markdown(report) + "\n").encode("utf-8")
    markdown_path.write_bytes(markdown_bytes)
    manifest["reports"][event_symbol_id]["json_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    manifest["reports"][event_symbol_id]["md_sha256"] = hashlib.sha256(markdown_bytes).hexdigest()
    directory_path = out / "event_directory.json"
    directory = json.loads(directory_path.read_text())
    directory["reports"][event_symbol_id]["json_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    directory["reports"][event_symbol_id]["md_sha256"] = hashlib.sha256(markdown_bytes).hexdigest()
    directory["reports"][event_symbol_id]["stage1_5h_static_proxy_status"] = "within_limits"
    directory_bytes = json.dumps(directory, indent=2, ensure_ascii=False).encode("utf-8")
    directory_path.write_bytes(directory_bytes)
    manifest["event_directory"]["sha256"] = hashlib.sha256(directory_bytes).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    ok, blockers = verify_stage1_5h_v2_event_bundle_manifest(out)
    assert ok is False
    assert blockers == ["stage1_5h_v2_event_bundle_manifest_invalid"]

    manifest["reports"] = None
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    ok, blockers = verify_stage1_5h_v2_event_bundle_manifest(out)
    assert ok is False
    assert blockers == ["stage1_5h_v2_event_bundle_manifest_invalid"]


def test_v2_writer_rejects_symlinked_reports_root(tmp_path, monkeypatch):
    import src.research.external_signal_shadow.stage1_5h_read_only_report_generator as mod

    target = tmp_path / "reports_target"
    target.mkdir()
    reports_root = tmp_path / "reports_link"
    reports_root.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(mod, "_STAGE1_5H_V2_REPORTS_ROOT", reports_root)

    bundle, _ = make_v2_bundle_fixture(tmp_path)
    result = write_stage1_5h_v2_event_bundle_reports(
        bundle=bundle, output_root=reports_root / "fresh_run"
    )
    assert result["decision"] == "stage1_5h_v2_event_bundle_output_rejected"
    assert result["blockers"] == ["output_root_outside_authorized_reports_root"]
    assert not (target / "fresh_run").exists()


@pytest.mark.parametrize("state", ["incomplete_without_manifest", "invalid_manifest", "sealed_root"])
def test_v2_writer_never_resumes_or_overwrites_existing_root(tmp_path, monkeypatch, state):
    import src.research.external_signal_shadow.stage1_5h_read_only_report_generator as mod
    reports_root = tmp_path / "reports_root"
    reports_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mod, "_STAGE1_5H_V2_REPORTS_ROOT", reports_root)

    out = reports_root / f"existing_{state}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "some_file.txt").write_text("existing content\n", encoding="utf-8")
    if state == "invalid_manifest":
        (out / "stage1_5h_event_bundle_manifest.json").write_text("{}", encoding="utf-8")

    before = tree_digest(out)
    bundle, _ = make_v2_bundle_fixture(tmp_path)
    result = write_stage1_5h_v2_event_bundle_reports(bundle=bundle, output_root=out)
    assert result["decision"] == "stage1_5h_v2_event_bundle_output_rejected"
    assert tree_digest(out) == before
