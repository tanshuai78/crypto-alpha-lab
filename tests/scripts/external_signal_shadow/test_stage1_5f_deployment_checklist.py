import glob
from pathlib import Path


def test_stage1_5f_deployment_events_glob_contains_no_literal_backslash():
    path = Path("docs/reviews/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-schedule-priority-v2-deployment-checklist_CN.md")
    assert path.exists()
    text = path.read_text()
    assert "events/\\*.jsonl" not in text
    assert "events/*.jsonl" in text


def test_stage1_5f_events_glob_expansion(tmp_path):
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    f1 = events_dir / "2026-08-03.jsonl"
    f1.write_text("{}")

    pattern = str(events_dir / "*.jsonl")
    matched = glob.glob(pattern)
    assert len(matched) == 1
    assert matched[0] == str(f1)


def test_git_ancestry_attestation_deployment_checklist_content():
    path = Path("docs/reviews/2026-08-10-external-signal-shadow-lab-stage1-5d-1-5f-git-ancestry-attestation-deployment-checklist_CN.md")
    assert path.exists()
    text = path.read_text()
    assert "Section A: Current Disabled Deployment" in text
    assert "Section B: Future Enablement Reference" in text
    assert "events/*.jsonl" in text
    assert "events/\\*.jsonl" not in text
    assert "\nexit\n" not in text and "\nexit " not in text
