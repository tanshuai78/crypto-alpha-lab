import datetime
import json
import os
import shutil

from loguru import logger

from configs import base
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
    DepthSnapshot,
    EventSymbolState,
)


def load_latest_state_by_event_symbol_id(observer_state_jsonl: str) -> dict:
    # Advisory B: clean up temporary compacted file if it exists (indicating a crash before rename)
    tmp_file = observer_state_jsonl + ".compacted.tmp"
    if os.path.exists(tmp_file):
        try:
            logger.info(f"Advisory B: Discarding temp state file {tmp_file} on startup.")
            os.remove(tmp_file)
        except Exception as e:
            logger.warning(f"Failed to remove temp state file: {e}")

    latest = {}
    if not os.path.exists(observer_state_jsonl):
        return latest

    with open(observer_state_jsonl, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                state = EventSymbolState.from_dict(data)
                latest[state.event_symbol_id] = state
            except Exception as e:
                logger.warning(f"Failed to parse state row: {e}")
    return latest


def compact_observer_state_jsonl(observer_state_jsonl: str) -> None:
    latest = load_latest_state_by_event_symbol_id(observer_state_jsonl)
    if not latest:
        return

    dir_name = os.path.dirname(os.path.abspath(observer_state_jsonl))
    os.makedirs(dir_name, exist_ok=True)

    tmp_file = observer_state_jsonl + ".compacted.tmp"
    try:
        fd = os.open(tmp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        with os.fdopen(fd, "w") as f:
            for state in latest.values():
                f.write(json.dumps(state.to_dict()) + "\n")
                f.flush()
            os.fsync(fd)
    except Exception as e:
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass
        raise e

    # Write backup of the original state file
    if os.path.exists(observer_state_jsonl):
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{observer_state_jsonl}.{timestamp}.jsonl.bak"
        try:
            shutil.copy2(observer_state_jsonl, backup_file)
            logger.info(f"State file backed up to {backup_file}")
        except Exception as e:
            logger.warning(f"Failed to write backup of state file: {e}")

    # Atomic rename
    os.replace(tmp_file, observer_state_jsonl)

    try:
        parent_fd = os.open(dir_name, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except Exception:
        pass


def start_observation(event_symbol_row: dict, now_ms: int) -> EventSymbolState:
    window_end_ms = now_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS
    return EventSymbolState(
        event_symbol_id=event_symbol_row["event_symbol_id"],
        event_id=event_symbol_row["event_id"],
        symbol=event_symbol_row["symbol"],
        detected_at_ms=event_symbol_row["detected_at_ms"],
        observation_started_at_ms=now_ms,
        observation_window_end_ms=window_end_ms,
        status="active",
        depth_snapshot_count=0,
        last_snapshot_ms=0,
        max_gap_ms=0,
        coverage_ratio_pass=False,
        max_gap_pass=False,
        research_result_valid=False,
    )


def record_depth_snapshot(state: EventSymbolState, snapshot: DepthSnapshot) -> EventSymbolState:
    if state.status != "active":
        return state

    fetched_at = snapshot.fetched_at_ms
    count = state.depth_snapshot_count + 1
    last_ts = state.last_snapshot_ms

    if last_ts > 0:
        gap = fetched_at - last_ts
        max_gap = max(state.max_gap_ms, gap)
    else:
        max_gap = state.max_gap_ms

    return EventSymbolState(
        event_symbol_id=state.event_symbol_id,
        event_id=state.event_id,
        symbol=state.symbol,
        detected_at_ms=state.detected_at_ms,
        observation_started_at_ms=state.observation_started_at_ms,
        observation_window_end_ms=state.observation_window_end_ms,
        status=state.status,
        depth_snapshot_count=count,
        last_snapshot_ms=fetched_at,
        max_gap_ms=max_gap,
        coverage_ratio_pass=state.coverage_ratio_pass,
        max_gap_pass=state.max_gap_pass,
        research_result_valid=state.research_result_valid,
    )


def compute_snapshot_time_coverage(state: EventSymbolState, snapshots: list) -> dict:
    if not snapshots:
        return {
            "coverage_ratio_pass": False,
            "max_gap_pass": False,
            "max_gap_ms": 0,
            "research_result_valid": False,
        }

    sorted_snaps = sorted(snapshots, key=lambda s: s.fetched_at_ms)

    expected = int(base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS // (base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC * 1000))
    min_required = int(expected * base.EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COVERAGE_RATIO)

    count = len(sorted_snaps)
    count_pass = count >= min_required

    poll_interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC * 1000
    first_ts = sorted_snaps[0].fetched_at_ms
    last_ts = sorted_snaps[-1].fetched_at_ms

    first_boundary_pass = first_ts <= state.observation_started_at_ms + 2 * poll_interval_ms
    last_boundary_pass = last_ts >= state.observation_window_end_ms - 2 * poll_interval_ms

    max_gap = 0
    for i in range(1, len(sorted_snaps)):
        gap = sorted_snaps[i].fetched_at_ms - sorted_snaps[i - 1].fetched_at_ms
        if gap > max_gap:
            max_gap = gap

    max_gap_pass = max_gap <= base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_SNAPSHOT_GAP_MS

    coverage_ratio_pass = count_pass and first_boundary_pass and last_boundary_pass
    research_result_valid = coverage_ratio_pass and max_gap_pass

    return {
        "coverage_ratio_pass": coverage_ratio_pass,
        "max_gap_pass": max_gap_pass,
        "max_gap_ms": max_gap,
        "research_result_valid": research_result_valid,
    }


def finalize_observation_if_due(state: EventSymbolState, now_ms: int, snapshots: list) -> EventSymbolState:
    if state.status != "active":
        return state

    if now_ms < state.observation_window_end_ms:
        return state

    cov = compute_snapshot_time_coverage(state, snapshots)
    status = "completed" if cov["research_result_valid"] else "expired_without_depth"

    if not snapshots:
        status = "expired_without_depth"

    return EventSymbolState(
        event_symbol_id=state.event_symbol_id,
        event_id=state.event_id,
        symbol=state.symbol,
        detected_at_ms=state.detected_at_ms,
        observation_started_at_ms=state.observation_started_at_ms,
        observation_window_end_ms=state.observation_window_end_ms,
        status=status,
        depth_snapshot_count=len(snapshots),
        last_snapshot_ms=snapshots[-1].fetched_at_ms if snapshots else 0,
        max_gap_ms=cov["max_gap_ms"],
        coverage_ratio_pass=cov["coverage_ratio_pass"],
        max_gap_pass=cov["max_gap_pass"],
        research_result_valid=cov["research_result_valid"],
    )
