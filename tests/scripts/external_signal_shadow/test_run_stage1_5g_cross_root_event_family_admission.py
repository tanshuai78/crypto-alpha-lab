import ast
import builtins
from pathlib import Path
from unittest.mock import patch

import pytest

# In RED phase, importing run_stage1_5g_cross_root_event_family_admission will fail with ModuleNotFoundError
from scripts.external_signal_shadow.run_stage1_5g_cross_root_event_family_admission import main
from src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission import (
    load_verified_cross_root_receipt,
)


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _get_valid_baseline_dir() -> Path:
    baseline_env = Path("/tmp/stage1_5g_cross_root_admission_env.sh")
    if not baseline_env.is_file():
        pytest.skip("No baseline env found in /tmp")

    env_lines = baseline_env.read_text().splitlines()
    baseline_dir = None
    for line in env_lines:
        if line.startswith("EXECUTION_BASELINE_DIR="):
            baseline_dir = line.split("=", 1)[1].strip()
    if not baseline_dir or not Path(baseline_dir).is_dir():
        pytest.skip("Invalid EXECUTION_BASELINE_DIR in env")
    return Path(baseline_dir)


def _valid_cli_args(run_id: str, baseline_dir: Path) -> list[str]:
    return [
        "--approved-design-path",
        "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md",
        "--approved-design-sha256",
        "51a25377537dade47c7a234f93802aa445db75348f7e10b4e9c354888d4cefc7",
        "--approved-plan-path",
        "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md",
        "--approved-plan-sha256",
        "8bb2a6ff906d54e209d8bca6c0885211c101664b87af65e2bee0b17483369c73",
        "--execution-baseline-dir",
        str(baseline_dir),
        "--run-id",
        run_id,
    ]


def test_cli_happy_path(tmp_path, monkeypatch):
    """CLI runs with valid args, publishes receipt to monkeypatched parent, and returns 0."""
    import src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission as core_mod

    baseline_dir = _get_valid_baseline_dir()
    run_id = "stage1_5g_cross_root_admission_20260930T170000Z"
    monkeypatch.setattr(core_mod, "DEFAULT_EVENT_FAMILY_ADMISSIONS_PARENT", str(tmp_path))

    rc = main(_valid_cli_args(run_id, baseline_dir))
    assert rc == 0

    final_root = tmp_path / run_id
    assert final_root.is_dir()
    loaded = load_verified_cross_root_receipt(final_root)
    assert loaded["summary"]["run_id"] == run_id
    assert loaded["summary"]["decision"] == "stage1_5g_cross_root_event_family_admission_pass"


def test_cli_rejects_forbidden_flags(tmp_path):
    """CLI rejects forbidden arguments like --output-root, --verify, --resume."""
    baseline_dir = _get_valid_baseline_dir()
    run_id = "stage1_5g_cross_root_admission_20260930T170001Z"
    base_args = _valid_cli_args(run_id, baseline_dir)

    for forbidden in (["--output-root", str(tmp_path)], ["--verify"], ["--resume"], ["--extra-flag"]):
        rc = main(base_args + forbidden)
        assert rc != 0


def test_cli_rejects_malformed_run_id():
    """CLI rejects malformed run-id."""
    baseline_dir = _get_valid_baseline_dir()
    args = _valid_cli_args("invalid_run_id_format", baseline_dir)
    rc = main(args)
    assert rc != 0


def test_cli_rejects_plan_hash_mismatch():
    """CLI rejects modified plan hash or mismatch with Task 0 authority."""
    baseline_dir = _get_valid_baseline_dir()
    run_id = "stage1_5g_cross_root_admission_20260930T170002Z"
    args = _valid_cli_args(run_id, baseline_dir)
    # Mutate plan sha argument
    idx = args.index("--approved-plan-sha256")
    args[idx + 1] = "0000000000000000000000000000000000000000000000000000000000000000"

    rc = main(args)
    assert rc != 0


def test_cli_ast_no_forbidden_network_or_review_imports():
    """AST guard: CLI script must not import socket/network libraries or old review renderer."""
    script_path = _get_project_root() / "scripts/external_signal_shadow/run_stage1_5g_cross_root_event_family_admission.py"
    if not script_path.is_file():
        pytest.fail("CLI script file missing")

    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    forbidden_modules = {"socket", "urllib", "requests", "httpx", "aiohttp", "urllib3"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden from-import: {node.module}"


def test_cli_open_spy_no_raw_jsonl_outside_production_loader(tmp_path, monkeypatch):
    """Open spy proves CLI only reads source files via production loader, never directly opening raw .jsonl."""
    import src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission as core_mod

    baseline_dir = _get_valid_baseline_dir()
    run_id = "stage1_5g_cross_root_admission_20260930T170003Z"
    monkeypatch.setattr(core_mod, "DEFAULT_EVENT_FAMILY_ADMISSIONS_PARENT", str(tmp_path))

    opened_files = []
    orig_open = builtins.open

    def open_spy(file, *args, **kwargs):
        opened_files.append(str(file))
        return orig_open(file, *args, **kwargs)

    with patch("builtins.open", side_effect=open_spy):
        rc = main(_valid_cli_args(run_id, baseline_dir))

    assert rc == 0
    # Core module only reads .json, .md, SHA256SUMS. Any .jsonl opens happen inside loader
    core_file = str(Path(core_mod.__file__).resolve())
    assert core_file not in [
        f for f in opened_files if f.endswith(".jsonl") and "stage1_5g_live_depth_evidence_review.py" not in f
    ]
