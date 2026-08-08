import hashlib
import json
from pathlib import Path
from typing import Any

from configs import base
from src.research.external_signal_shadow.stage1_5_launch_anchor_contract import (
    validate_launch_anchor_contract,
)


def classify_revision_intent(detail_text: str, title: str = "") -> dict[str, Any]:
    text = (f"{title}\n{detail_text}").lower()

    # Maintenance or regular non-revision exclusions
    maint_keywords = [
        "system maintenance",
        "api maintenance",
        "system upgrade",
        "funding rate",
        "scheduled settlement",
        "perpetual futures trading system",
    ]
    if any(k in text for k in maint_keywords) and not ("postpon" in text or "reschedul" in text or "cancel" in text):
        return {"revision_intent": "not_revision", "reason": "maintenance_or_non_revision"}

    has_postpone = "postpon" in text or "delay" in text
    has_reschedule = "reschedul" in text or "new launch time" in text or "revised launch" in text
    has_cancel = "cancel" in text or "will not launch" in text

    if not (has_postpone or has_reschedule or has_cancel):
        return {"revision_intent": "not_revision", "reason": "no_revision_keywords"}

    if has_cancel and (has_postpone or has_reschedule) and ("simultaneously" in text or "both" in text):
        return {"revision_intent": "ambiguous_revision_intent", "reason": "contradictory_keywords"}

    if has_cancel and not has_reschedule:
        return {"revision_intent": "cancelled", "reason": "cancellation_detected"}

    if has_reschedule or (has_postpone and ("utc" in text or ":" in text)):
        return {"revision_intent": "rescheduled_with_new_anchor", "reason": "reschedule_detected"}

    if has_postpone:
        return {"revision_intent": "postponed_without_anchor", "reason": "postponement_without_new_anchor"}

    return {"revision_intent": "not_revision", "reason": "default_fallback"}


def classify_schedule_revision_candidates(detail_text: str, *, title: str = "", max_symbols: int = 30) -> list[dict[str, Any]]:
    res = classify_revision_intent(detail_text, title)
    intent = res["revision_intent"]
    if intent in ("not_revision", "ambiguous_revision_intent"):
        return []

    return [
        {
            "revision_intent": intent,
            "title": title,
            "detail_text_snippet": detail_text[:500],
            "classification_reason": res["reason"],
        }
    ]


def is_schedule_revision_listing_candidate(title: str) -> bool:
    """Keep only title cues that need trusted-detail confirmation."""
    return classify_revision_intent("", title)["revision_intent"] not in (
        "not_revision",
        "ambiguous_revision_intent",
    )


def build_formal_launch_identity_index_rows(
    launch_row: dict[str, Any],
    *,
    source_root_id: str = "",
    commit_sha: str = "",
    durable_at_ms: int = 0,
) -> list[dict[str, Any]]:
    source_article_id = str(launch_row.get("source_article_id") or "").strip()
    symbols = [str(s).strip().upper() for s in (launch_row.get("symbols") or []) if str(s).strip()]
    if not source_article_id or not symbols:
        return []

    index_rows = []
    for symbol in symbols:
        val = validate_launch_anchor_contract(launch_row, symbol, compatibility_mode=False)
        if not val["valid"]:
            continue

        published_at_ms = launch_row.get("source_published_at_ms") or launch_row.get("detected_at_ms") or 0
        stable_identity = f"binance|futures_contract_launch|{source_article_id}|{symbol}"
        index_rows.append(
            {
                "index_schema_version": 1,
                "supersedes_source_article_id": source_article_id,
                "source_article_id": source_article_id,
                "symbol": symbol,
                "stable_schedule_identity": stable_identity,
                "normalized_source_namespace": "binance",
                "source_transport": launch_row.get("source_transport", "binance_official_announcement"),
                "formal_event_contract_version": launch_row.get("formal_event_contract_version"),
                "source_anchor_contract_hash": (launch_row.get("symbol_source_anchor_contract_hashes") or {}).get(symbol),
                "official_schedule_anchor_ms": (launch_row.get("symbol_official_schedule_anchor_ms") or {}).get(symbol),
                "original_source_published_at_ms": published_at_ms,
                "identity_first_observed_at_ms": launch_row.get("detected_at_ms") or published_at_ms,
                "formal_row_durable_at_ms": durable_at_ms or published_at_ms,
                "source_root_id": source_root_id,
                "source_root_commit_sha": commit_sha,
                "commit_sha": commit_sha,
                "event_id": launch_row.get("event_id"),
                "payload_sha256": launch_row.get("detail_payload_hash"),
            }
        )
    return index_rows


def load_valid_formal_launch_identity_index(
    index_path: Path | str,
    *,
    as_of_ms: int,
    snapshot_path: Path | str | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    path = Path(index_path)
    rows = []
    blockers = []
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if not row.get("supersedes_source_article_id") or not row.get("symbol"):
                    blockers.append("malformed_index_row")
                    continue
                rows.append(row)
        except Exception as exc:
            blockers.append(f"index_read_error:{exc}")

    if snapshot_path is not None:
        try:
            snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
            snapshot_rows = snapshot["rows"]
            source_root_ids = snapshot.get("source_root_ids") or [snapshot.get("source_root_id")]
            source_commit_shas = snapshot.get("source_root_commit_shas") or [snapshot.get("commit_sha")]
            if (
                snapshot.get("schema_version") != 1
                or not all(source_root_ids)
                or not all(source_commit_shas)
                or not isinstance(snapshot_rows, list)
            ):
                raise ValueError("snapshot_manifest_invalid")
            canonical = json.dumps(snapshot_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if hashlib.sha256(canonical).hexdigest() != snapshot.get("content_sha256"):
                raise ValueError("snapshot_content_hash_mismatch")
            for row in snapshot_rows:
                if not row.get("supersedes_source_article_id") or not row.get("symbol"):
                    raise ValueError("snapshot_row_invalid")
                if row.get("source_root_id") not in source_root_ids:
                    raise ValueError("snapshot_row_source_root_unapproved")
                row_commit_sha = row.get("source_root_commit_sha") or row.get("commit_sha")
                if row_commit_sha not in source_commit_shas:
                    raise ValueError("snapshot_row_commit_unapproved")
            rows.extend(snapshot_rows)
        except Exception as exc:
            blockers.append(f"snapshot_invalid:{exc}")

    for key_name in ("source_anchor_contract_hash", "official_schedule_anchor_ms"):
        seen: dict[tuple[str, str], Any] = {}
        for row in rows:
            key = (str(row.get("supersedes_source_article_id") or ""), str(row.get("symbol") or "").upper())
            value = row.get(key_name)
            if not key[0] or value is None:
                continue
            if key in seen and seen[key] != value:
                blockers.append("index_collision")
                break
            seen[key] = value
    event_ids: dict[str, str] = {}
    for row in rows:
        identity = str(row.get("stable_schedule_identity") or "")
        event_id = str(row.get("event_id") or "")
        if not identity or not event_id:
            continue
        if identity in event_ids and event_ids[identity] != event_id:
            blockers.append("index_collision")
            break
        event_ids[identity] = event_id

    if not rows and not blockers:
        blockers.append("index_file_not_found")

    return rows, list(dict.fromkeys(blockers))


def rebuild_missing_formal_launch_identity_index(
    *,
    events_dir: Path | str,
    index_path: Path | str,
    source_root_id: str,
    commit_sha: str,
) -> tuple[int, list[dict[str, Any]]]:
    """Recover missing current-root identity rows from durable launch events."""
    from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import append_jsonl

    existing_rows, blockers = load_valid_formal_launch_identity_index(index_path, as_of_ms=2**63 - 1)
    diagnostics = [{"reason": blocker} for blocker in blockers if blocker != "index_file_not_found"]
    existing_keys = {
        (str(row.get("supersedes_source_article_id") or ""), str(row.get("symbol") or "").upper())
        for row in existing_rows
    }
    rebuilt = 0
    for event_path in sorted(Path(events_dir).glob("*.jsonl")):
        try:
            durable_at_ms = int(event_path.stat().st_mtime * 1000)
            lines = event_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            diagnostics.append({"reason": "event_stream_read_error", "path": str(event_path), "error": str(exc)})
            continue
        for line_no, line in enumerate(lines, 1):
            try:
                launch_row = json.loads(line)
            except json.JSONDecodeError:
                diagnostics.append({"reason": "event_stream_malformed_json", "path": str(event_path), "line": line_no})
                continue
            if launch_row.get("event_type") != "futures_contract_launch":
                continue
            for index_row in build_formal_launch_identity_index_rows(
                launch_row,
                source_root_id=source_root_id,
                commit_sha=commit_sha,
                durable_at_ms=durable_at_ms,
            ):
                key = (index_row["supersedes_source_article_id"], index_row["symbol"])
                if key in existing_keys:
                    continue
                append_jsonl(index_path, index_row)
                existing_keys.add(key)
                rebuilt += 1
    return rebuilt, diagnostics


def load_emitted_revision_semantic_ids(events_dir: Path | str) -> set[str]:
    """Recover only durable v2 revision identities for restart idempotency."""
    emitted = set()
    for event_path in sorted(Path(events_dir).glob("*.jsonl")):
        try:
            lines = event_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("formal_schedule_revision_contract_version") != 2:
                continue
            semantic_id = str(row.get("revision_semantic_id") or "").strip()
            if semantic_id:
                emitted.add(semantic_id)
    return emitted


def link_schedule_revision_candidate(
    candidate: dict[str, Any],
    index_rows: list[dict[str, Any]],
    *,
    available_at_ms: int,
    lookback_days: int = 14,
) -> dict[str, Any]:
    link_level = candidate.get("link_level_candidate", "")
    if link_level == "L4_symbol_only":
        return {"link_status": "out_of_scope", "target_index_row": None, "reason": "L4_symbol_only_out_of_scope"}

    target_article = candidate.get("supersedes_source_article_id") or candidate.get("supersedes_article_id")
    target_symbol = str(candidate.get("symbol") or "").strip().upper()

    if not target_article:
        return {"link_status": "orphaned", "target_index_row": None, "reason": "missing_supersedes_article_id"}

    lookback_ms = lookback_days * 24 * 60 * 60 * 1000
    matches = []

    for row in index_rows:
        row_sym = str(row.get("symbol") or "").strip().upper()
        row_art = str(row.get("supersedes_source_article_id") or "").strip()
        pub_ms = int(row.get("original_source_published_at_ms") or 0)
        durable_ms = int(row.get("formal_row_durable_at_ms") or 0)

        if row_art == target_article and (not target_symbol or row_sym == target_symbol):
            if (
                pub_ms > 0
                and durable_ms > 0
                and pub_ms <= available_at_ms
                and durable_ms <= available_at_ms
                and (available_at_ms - pub_ms) <= lookback_ms
            ):
                matches.append(row)

    if len(matches) == 1:
        return {"link_status": "linked", "target_index_row": matches[0], "reason": "unique_identity_match"}
    elif len(matches) > 1:
        return {"link_status": "ambiguous", "target_index_row": None, "reason": "multiple_identity_matches"}
    else:
        return {"link_status": "orphaned", "target_index_row": None, "reason": "no_matching_identity_in_index"}


def build_revision_diagnostic(
    candidate: dict[str, Any],
    link: dict[str, Any],
    *,
    producer_decision_at_ms: int,
) -> dict[str, Any]:
    return {
        "diagnostic_type": "schedule_revision_producer_diagnostic",
        "producer_decision_at_ms": producer_decision_at_ms,
        "candidate": candidate,
        "link_result": link,
    }


def emit_schedule_revision_batch(
    batch_candidate: dict[str, Any],
    index_rows: list[dict[str, Any]],
    *,
    available_at_ms: int,
    lookback_days: int = 14,
    emitted_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from src.research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_schedule_revision_row,
        validate_schedule_revision_contract,
    )

    emitted_set = emitted_ids or set()
    source_article_id = batch_candidate.get("source_article_id", "")
    intent = batch_candidate.get("revision_intent", "not_revision")
    symbols = batch_candidate.get("symbols", [])
    symbol_candidates = batch_candidate.get("symbol_candidates", {})
    is_late_conflict = bool(batch_candidate.get("is_late_conflict", False))

    if intent in ("not_revision", "ambiguous_revision_intent"):
        return [], {"batch_status": "terminal_diagnostic", "reason": "invalid_intent", "is_late_conflict": is_late_conflict}

    prepared_rows = []

    for sym in symbols:
        sc = dict(symbol_candidates.get(sym, {}))
        sc.setdefault("symbol", sym)
        link = link_schedule_revision_candidate(sc, index_rows, available_at_ms=available_at_ms, lookback_days=lookback_days)
        if link["link_status"] != "linked":
            # All-symbols statement failure: if one symbol fails linking, fail entire batch!
            return [], {
                "batch_status": "terminal_diagnostic",
                "reason": "all_symbols_statement_failure",
                "failed_symbol": sym,
                "link_status": link["link_status"],
                "is_late_conflict": is_late_conflict,
            }

        target_row = link["target_index_row"]
        supersedes_article = target_row.get("supersedes_source_article_id", "")
        revised_anchor = sc.get("revised_anchor_ms")
        superseded_anchor = sc.get("superseded_anchor_ms")

        payload_hash = str(batch_candidate.get("payload_sha256") or batch_candidate.get("raw_payload_sha256") or "")
        if not payload_hash:
            return [], {
                "batch_status": "terminal_diagnostic",
                "reason": "revision_payload_hash_missing",
                "is_late_conflict": is_late_conflict,
            }
        semantic_id = hashlib.sha256(f"{source_article_id}|{sym}|{intent}|{revised_anchor}".encode()).hexdigest()
        payload_version_id = hashlib.sha256(f"{source_article_id}|{payload_hash}".encode()).hexdigest()
        observation_id = hashlib.sha256(f"{source_article_id}|{sym}|{payload_hash}|{available_at_ms}".encode()).hexdigest()
        if semantic_id in emitted_set:
            continue

        formal_row = build_formal_schedule_revision_row(
            source_article_id=source_article_id,
            supersedes_source_article_id=supersedes_article,
            symbol=sym,
            revised_anchor_ms=revised_anchor,
            superseded_anchor_ms=superseded_anchor,
            revision_intent=intent,
            link_status="linked",
            revision_id=semantic_id,
            revision_semantic_id=semantic_id,
            revision_application_id=semantic_id,
            revision_payload_version_id=payload_version_id,
            revision_observation_id=observation_id,
            revision_payload_hash=payload_hash,
            revision_available_at_ms=available_at_ms,
            provenance={"payload_sha256": payload_hash, "parser_version": "v2"},
        )
        val = validate_schedule_revision_contract(formal_row)
        if not val["valid"]:
            return [], {
                "batch_status": "terminal_diagnostic",
                "reason": "formal_contract_invalid",
                "blockers": val.get("blockers"),
                "is_late_conflict": is_late_conflict,
            }
        prepared_rows.append(formal_row)

    return prepared_rows, {
        "batch_status": "emitted" if prepared_rows else "already_emitted",
        "is_late_conflict": is_late_conflict,
        "emitted_row_count": len(prepared_rows),
    }
