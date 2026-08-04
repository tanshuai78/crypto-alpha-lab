
from research.external_signal_shadow.stage1_5f_schedule_revision_registry import (
    ScheduleRevisionRegistry,
    compute_revision_application_id,
)


def test_schedule_revision_registry_idempotency_and_replay(tmp_path):
    reg_file = tmp_path / "schedule_revision_registry.jsonl"
    reg = ScheduleRevisionRegistry(reg_file)

    app_id = compute_revision_application_id(
        stable_schedule_identity="binance|futures_contract_launch|art1|XYZUSDT",
        revision_id="rev-1",
        revision_payload_hash="hash1",
    )
    assert reg.is_applied(app_id) is False

    reg.record_revision(
        revision_application_id=app_id,
        status="revision_applied",
        stable_schedule_identity="binance|futures_contract_launch|art1|XYZUSDT",
        revision_id="rev-1",
        revision_payload_hash="hash1",
    )
    assert reg.is_applied(app_id) is True

    # Re-open registry from disk to test reload
    reg2 = ScheduleRevisionRegistry(reg_file)
    assert reg2.is_applied(app_id) is True


def test_schedule_revision_registry_records_orphaned_and_ambiguous(tmp_path):
    reg_file = tmp_path / "schedule_revision_registry.jsonl"
    reg = ScheduleRevisionRegistry(reg_file)

    app_id = compute_revision_application_id(
        stable_schedule_identity="binance|futures_contract_launch|art2|ABCUSDT",
        revision_id="rev-2",
        revision_payload_hash="hash2",
    )
    reg.record_revision(
        revision_application_id=app_id,
        status="revision_orphaned",
        stable_schedule_identity="binance|futures_contract_launch|art2|ABCUSDT",
        revision_id="rev-2",
        revision_payload_hash="hash2",
    )

    # Orphaned is recorded in file but not in applied_ids
    assert reg.is_applied(app_id) is False
    assert len(reg.records) == 1
    assert reg.records[0]["status"] == "revision_orphaned"
