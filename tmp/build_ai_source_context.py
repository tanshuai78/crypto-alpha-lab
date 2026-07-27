#!/usr/bin/env python3
"""Generate searchable source-context packs for AI project review."""

from __future__ import annotations

import ast
import hashlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path.cwd().resolve()
OUT = ROOT / "_project_context" / "source_upload"
GENERATOR_VERSION = "2026-07-26.source-upload-v2"
EXCLUDED_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".worktrees",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return "unknown"
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else "unknown"


def git_metadata() -> dict[str, str]:
    status = run_git(["status", "--short"])
    return {
        "source_commit": run_git(["rev-parse", "HEAD"]),
        "source_branch": run_git(["branch", "--show-current"]),
        "worktree_dirty": "false" if status == "unknown" or status == "" else "true",
        "worktree_status_short": status if status != "" else "clean",
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_context_noise(path: Path) -> bool:
    return bool(EXCLUDED_PATH_PARTS.intersection(path.parts)) or path.suffix in EXCLUDED_SUFFIXES


def existing_files(patterns: Iterable[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        files.update(
            path for path in ROOT.glob(pattern)
            if path.is_file() and not is_context_noise(path)
        )
    return sorted(files)


def write_provenance(out) -> None:
    meta = git_metadata()
    out.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
    out.write(f"generator_version: {GENERATOR_VERSION}\n")
    out.write(f"source_commit: {meta['source_commit']}\n")
    out.write(f"source_branch: {meta['source_branch']}\n")
    out.write(f"worktree_dirty: {meta['worktree_dirty']}\n")
    out.write(
        "excluded_paths: __pycache__, .pytest_cache, .ruff_cache, .venv, "
        ".worktrees, *.pyc, *.pyo\n"
    )
    if meta["worktree_status_short"] not in {"clean", "unknown"}:
        out.write("worktree_status_short:\n")
        for line in meta["worktree_status_short"].splitlines():
            out.write(f"  {line}\n")
    out.write("\n")


def write_pack(name: str, patterns: list[str]) -> Path:
    paths = existing_files(patterns)
    target = OUT / name

    with target.open("w", encoding="utf-8") as out:
        out.write(f"# {name}\n\n")
        write_provenance(out)
        out.write("This is an AI context artifact, not an editable source file.\n\n")
        out.write(f"MATCHED_FILE_COUNT: {len(paths)}\n")
        out.write("INPUT_PATTERNS:\n")
        for pattern in patterns:
            out.write(f"- `{pattern}`\n")
        out.write("\n")

        for path in paths:
            rel = path.relative_to(ROOT)
            text = path.read_text(encoding="utf-8", errors="replace")
            out.write("\n")
            out.write("=" * 100 + "\n")
            out.write(f"BEGIN FILE: {rel}\n")
            out.write(f"SHA256: {sha256(path)}\n")
            out.write(f"LINES: {text.count(chr(10)) + 1}\n")
            out.write("=" * 100 + "\n\n")
            out.write(text)
            if not text.endswith("\n"):
                out.write("\n")
            out.write("\n")
            out.write("=" * 100 + "\n")
            out.write(f"END FILE: {rel}\n")
            out.write("=" * 100 + "\n")

    return target


def import_names(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return sorted(names)


def write_inventory() -> Path:
    target = OUT / "10_project_code_inventory_and_import_graph.md"
    paths = existing_files([
        "configs/**/*.py",
        "src/**/*.py",
        "scripts/**/*.py",
        "tests/**/*.py",
    ])

    with target.open("w", encoding="utf-8") as out:
        out.write("# Project Code Inventory and Import Graph\n\n")
        write_provenance(out)

        for path in paths:
            rel = path.relative_to(ROOT)
            text = path.read_text(encoding="utf-8", errors="replace")
            out.write(f"## `{rel}`\n\n")
            out.write(f"- SHA256: `{sha256(path)}`\n")
            out.write(f"- Lines: `{text.count(chr(10)) + 1}`\n")
            imports = import_names(path)
            out.write("- Imports:\n")
            if imports:
                for item in imports:
                    out.write(f"  - `{item}`\n")
            else:
                out.write("  - none / parse unavailable\n")
            out.write("\n")

    return target


def copy_latest(
    pattern: str,
    target_name: str,
    *,
    filter_noise_lines: bool = False,
) -> None:
    matches = sorted(
        (path for path in ROOT.glob(pattern) if path.is_file()),
        key=lambda path: path.stat().st_mtime,
    )
    if not matches:
        return
    source = matches[-1]
    target = OUT / target_name
    if not filter_noise_lines:
        shutil.copy2(source, target)
        return

    lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    filtered = [
        line for line in lines
        if "__pycache__" not in line
        and ".pytest_cache" not in line
        and ".ruff_cache" not in line
        and not line.rstrip().endswith((".pyc", ".pyo"))
    ]
    target.write_text("\n".join(filtered) + "\n", encoding="utf-8")


def clean_output_dir() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for path in OUT.iterdir():
        if path.is_file():
            path.unlink()


def main() -> None:
    clean_output_dir()

    fixed_files = {
        "01_README.md": ROOT / "README.md",
        "02_roadmap.md": ROOT / "docs/roadmap.md",
        "03_current-project-state_CN.md":
            ROOT / "docs/project-status/current-project-state_CN.md",
        "04_current-document-index_CN.md":
            ROOT / "docs/project-status/current-document-index_CN.md",
        "05_base.py": ROOT / "configs/base.py",
        "06_pyproject.toml": ROOT / "pyproject.toml",
        "07_Makefile.txt": ROOT / "Makefile",
        "11_run_stage1_5d_live_event_source_smoke_collector.py":
            ROOT / "scripts/external_signal_shadow/"
                   "run_stage1_5d_live_event_source_smoke_collector.py",
        "14_run_stage1_5f_live_depth_observer.py":
            ROOT / "scripts/external_signal_shadow/"
                   "run_stage1_5f_live_depth_observer.py",
    }

    for target_name, source in fixed_files.items():
        if source.exists():
            shutil.copy2(source, OUT / target_name)

    copy_latest(
        "_project_context/workspace_snapshot_*.txt",
        "08_latest_workspace_snapshot.txt",
        filter_noise_lines=True,
    )
    copy_latest(
        "_project_context/server_runtime_snapshot_*.txt",
        "09_latest_server_runtime_snapshot.txt",
    )

    write_inventory()

    write_pack(
        "12_stage1_5d_core_pack.md",
        [
            "src/research/external_signal_shadow/stage1_5d*.py",
        ],
    )
    write_pack(
        "13_stage1_5d_tests_pack.md",
        [
            "tests/research/external_signal_shadow/test_stage1_5d*.py",
            "tests/scripts/external_signal_shadow/"
            "test_run_stage1_5d_live_event_source_smoke_collector.py",
            "tests/fixtures/external_signal_shadow/stage1_5d/*.json",
        ],
    )
    write_pack(
        "15_stage1_5f_core_pack.md",
        [
            "src/research/external_signal_shadow/stage1_5f*.py",
        ],
    )
    write_pack(
        "16_stage1_5f_tests_pack.md",
        [
            "tests/research/external_signal_shadow/test_stage1_5f*.py",
            "tests/scripts/external_signal_shadow/"
            "test_run_stage1_5f_live_depth_observer.py",
            "tests/fixtures/external_signal_shadow/stage1_5f/**/*.json",
            "tests/fixtures/external_signal_shadow/stage1_5f/**/*.jsonl",
        ],
    )
    write_pack(
        "17_stage1_5g_code_and_tests_pack.md",
        [
            "src/research/external_signal_shadow/stage1_5g*.py",
            "scripts/external_signal_shadow/*stage1_5g*.py",
            "tests/research/external_signal_shadow/test_stage1_5g*.py",
            "tests/scripts/external_signal_shadow/test_*stage1_5g*.py",
        ],
    )
    write_pack(
        "18_stage1_5h_code_and_tests_pack.md",
        [
            "src/research/external_signal_shadow/stage1_5h*.py",
            "scripts/external_signal_shadow/*stage1_5h*.py",
            "tests/research/external_signal_shadow/test_stage1_5h*.py",
            "tests/scripts/external_signal_shadow/test_*stage1_5h*.py",
        ],
    )
    write_pack(
        "19_platform_safety_contract_pack.md",
        [
            "src/risk/*.py",
            "src/strategies/base.py",
            "src/execution/order_executor.py",
            "tests/risk/*.py",
            "tests/execution/*.py",
        ],
    )
    write_pack(
        "20_latest_runtime_evidence_pack.md",
        [
            "_project_context/runtime_evidence/**/*summary*.json",
            "_project_context/runtime_evidence/**/watermark.json",
            "_project_context/runtime_evidence/**/observer_state.jsonl",
            "_project_context/runtime_evidence/**/detail_retry_scheduler_state.json",
            "_project_context/runtime_evidence/**/*review*.md",
            "_project_context/runtime_evidence/**/package_manifest*.txt",
            "_project_context/runtime_evidence/**/*.tail*.jsonl",
            "_project_context/server_runtime_artifacts/**/*.json",
            "_project_context/server_runtime_artifacts/**/*.jsonl",
            "data/external_signal_shadow/stage1_5g/reviews/*/stage1_5g_live_depth_evidence_review_summary.json",
            "data/external_signal_shadow/stage1_5g/reviews/*/stage1_5g_quarantine_summary.json",
            "data/external_signal_shadow/stage1_5h/reports/*/stage1_5h_static_execution_proxy_report_summary.json",
            "data/external_signal_shadow/stage1_5h/reports/**/*.md",
        ],
    )

    created = sorted(path.name for path in OUT.iterdir() if path.is_file())
    print(f"Created {len(created)} permanent source files in {OUT}")
    for name in created:
        print(name)

    if len(created) > 20:
        raise RuntimeError(
            f"Permanent source set exceeds 20 files: {len(created)}"
        )


if __name__ == "__main__":
    main()
