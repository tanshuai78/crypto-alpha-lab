import os

import pytest

from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import Watermark
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_watermark import (
    bootstrap_watermark_from_stage1_5d_events,
    event_is_post_watermark,
    get_stable_event_key,
    load_watermark,
    update_watermark_with_event,
    write_watermark_atomic,
)


def test_watermark_write_is_atomic(tmp_path):
    import shutil

    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    guard = StorageGuard(
        output_root=tmp_path,
        stage="1.5F",
        disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
    )
    target_path = tmp_path / "watermark.json"
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        seen_event_ids=["e1"],
        seen_source_article_ids=[],
        seen_stable_event_keys=[],
        updated_at_ms=2000,
    )
    res = write_watermark_atomic(str(target_path), w, storage_guard=guard)
    assert res["written"] is True
    assert os.path.exists(target_path)

    # Reload and check
    loaded = load_watermark(str(target_path))
    assert loaded.max_seen_detected_at_ms == 1000
    assert loaded.seen_event_ids == ["e1"]


def test_watermark_writer_requires_guard(tmp_path):
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        seen_event_ids=["e1"],
        seen_source_article_ids=[],
        seen_stable_event_keys=[],
        updated_at_ms=2000,
    )
    with pytest.raises(TypeError, match="storage_guard_required"):
        write_watermark_atomic(str(tmp_path / "watermark.json"), w, storage_guard=None)



def test_corrupted_watermark_makes_observer_invalid(tmp_path):
    target_path = tmp_path / "corrupted_watermark.json"
    # Write invalid json
    with open(target_path, "w") as f:
        f.write("{invalid_json:")

    with pytest.raises(ValueError) as excinfo:
        load_watermark(str(target_path))
    assert "corrupted" in str(excinfo.value).lower() or "json" in str(excinfo.value).lower()


def test_missing_watermark_requires_bootstrap_mode(tmp_path):
    target_path = tmp_path / "non_existent.json"
    with pytest.raises(FileNotFoundError):
        load_watermark(str(target_path))


def test_bootstrap_watermark_does_not_start_observation_for_existing_events():
    events = [
        {"event_id": "e1", "detected_at_ms": 1000, "source_article_id": "a1", "title": "t1", "source_name": "s1"},
        {"event_id": "e2", "detected_at_ms": 2000, "source_article_id": "a2", "title": "t2", "source_name": "s1"},
    ]
    w = bootstrap_watermark_from_stage1_5d_events(events)
    assert w.watermark_version == 1
    assert w.max_seen_detected_at_ms == 2000
    assert "e1" in w.seen_event_ids
    assert "e2" in w.seen_event_ids
    assert "a1" in w.seen_source_article_ids
    assert "a2" in w.seen_source_article_ids


def test_new_event_after_watermark_is_detected_as_post_watermark():
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        seen_event_ids=["e1"],
        seen_source_article_ids=[],
        seen_stable_event_keys=[],
        updated_at_ms=2000,
    )
    new_event = {"event_id": "e2", "detected_at_ms": 1001, "title": "t2", "source_name": "s1"}
    assert event_is_post_watermark(new_event, w) is True


def test_pre_watermark_event_is_counted_as_ignored_not_rejected_failure():
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        seen_event_ids=["e1"],
        seen_source_article_ids=[],
        seen_stable_event_keys=[],
        updated_at_ms=2000,
    )
    old_event = {"event_id": "e2", "detected_at_ms": 999, "title": "t2", "source_name": "s1"}
    assert event_is_post_watermark(old_event, w) is False


def test_event_same_detected_at_but_unseen_article_is_post_watermark():
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        seen_event_ids=["e1"],
        seen_source_article_ids=["a1"],
        seen_stable_event_keys=[],
        updated_at_ms=2000,
    )
    # same detected_at but new article
    event = {"event_id": "e2", "detected_at_ms": 1000, "source_article_id": "a2", "title": "t2", "source_name": "s1"}
    assert event_is_post_watermark(event, w) is True


def test_event_same_detected_at_and_seen_article_is_pre_watermark():
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        seen_event_ids=["e1"],
        seen_source_article_ids=["a1"],
        seen_stable_event_keys=[],
        updated_at_ms=2000,
    )
    # same detected_at and already seen article
    event = {"event_id": "e1", "detected_at_ms": 1000, "source_article_id": "a1", "title": "t1", "source_name": "s1"}
    assert event_is_post_watermark(event, w) is False


def test_update_watermark_with_event():
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        seen_event_ids=["e1"],
        seen_source_article_ids=["a1"],
        seen_stable_event_keys=[],
        updated_at_ms=2000,
    )
    event = {"event_id": "e2", "detected_at_ms": 1005, "source_article_id": "a2", "title": "t2", "source_name": "s1"}
    w2 = update_watermark_with_event(w, event)
    assert w2.max_seen_detected_at_ms == 1005
    assert "e2" in w2.seen_event_ids
    assert "a2" in w2.seen_source_article_ids


def test_stable_event_key_does_not_depend_on_detected_at_ms():
    event_a = {
        "source_name": "binance",
        "source_article_id": "article-1",
        "source_detail_url": "https://www.binance.com/en/support/announcement/article-1/",
        "source_published_at_ms": 1000,
        "title": "Launch ABCUSDT",
        "detected_at_ms": 2000,
    }
    event_b = {
        **event_a,
        "source_detail_url": "https://www.binance.com/en/support/announcement/article-1",
        "detected_at_ms": 3000,
    }

    assert get_stable_event_key(event_a) == get_stable_event_key(event_b)
