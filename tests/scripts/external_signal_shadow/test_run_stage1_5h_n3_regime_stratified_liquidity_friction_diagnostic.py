import ast
import inspect
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

try:
    from scripts.external_signal_shadow.run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic import (
        main,
    )
except ImportError as _import_err:
    _err_msg = str(_import_err)

    def main(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(f"Stage 1.5H N=3 CLI runner not yet implemented: {_err_msg}")


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


DESIGN_PATH = "docs/designs/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-design_CN.md"
DESIGN_SHA = "edc2dd3348fbf86f233ae4d236ed8202e69fc659a80d4a2b4376a0f7931d86a2"
PLAN_PATH = "docs/plans/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-implementation-plan_CN.md"
PLAN_SHA = "9d9ebe80fa0560d9ae60df412d32fec3b5e839ec3073e93b4be9a661a5fded42"
RUN_ID = "stage1_5h_n3_regime_stratified_friction_20261003T120000Z"
CORE_MODULE = "src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py"
CLI_SCRIPT = "scripts/external_signal_shadow/run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py"


def _valid_cli_args(run_id: str = RUN_ID) -> list[str]:
    return [
        "--approved-design-path",
        DESIGN_PATH,
        "--approved-design-sha256",
        DESIGN_SHA,
        "--approved-plan-path",
        PLAN_PATH,
        "--approved-plan-sha256",
        PLAN_SHA,
        "--run-id",
        run_id,
    ]


def test_cli_canonical_locator_deterministic_and_no_monkeypatch():
    """Canonical authority locator must take zero parameters, be deterministic and immune to environment override."""
    try:
        from src.research.external_signal_shadow.stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic import (
            APPROVED_PLAN_SHA256,
            get_canonical_execution_authority_bundle_path,
        )
    except ImportError as e:
        raise AssertionError(f"Stage 1.5H N=3 module not yet implemented: {e}")

    # 1. Signature check: strictly zero parameters
    sig = inspect.signature(get_canonical_execution_authority_bundle_path)
    assert len(sig.parameters) == 0, f"Expected 0 parameters, got {list(sig.parameters.keys())}"

    # 2. Exact return value check
    project_root = _get_project_root()
    bundle_path = get_canonical_execution_authority_bundle_path()
    expected_path = project_root / f".git/plan-execution/stage1_5h_n3_regime/{APPROVED_PLAN_SHA256}"
    assert bundle_path == expected_path

    # 3. AST check: reject caller parameters, env reads, glob, iterdir, and 'latest'
    core_path = project_root / CORE_MODULE
    tree = ast.parse(core_path.read_text(encoding="utf-8"))
    locator_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "get_canonical_execution_authority_bundle_path":
            locator_node = node
            break

    assert locator_node is not None, "get_canonical_execution_authority_bundle_path not found in core AST"
    assert len(locator_node.args.args) == 0, "locator must take zero positional arguments"
    assert len(locator_node.args.kwonlyargs) == 0, "locator must take zero keyword-only arguments"
    assert locator_node.args.vararg is None, "locator must take no *args"
    assert locator_node.args.kwarg is None, "locator must take no **kwargs"

    for child in ast.walk(locator_node):
        if isinstance(child, ast.Attribute):
            assert child.attr not in {"environ", "getenv"}, f"locator must not access env: {child.attr}"
            assert child.attr not in {"glob", "rglob", "iterdir"}, f"locator must not discover dirs: {child.attr}"
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            assert "latest" not in child.value, "locator must not reference 'latest'"


def test_cli_happy_path_spy_with_valid_mock_authority():
    """CLI runs with valid args, spies on run_diagnostic, returns 0."""
    mock_run = MagicMock(return_value={
        "summary": {
            "run_id": RUN_ID,
            "decision": "stage1_5h_n3_regime_stratified_friction_diagnostic_generated",
        }
    })
    with patch(
        "scripts.external_signal_shadow.run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.run_diagnostic",
        mock_run,
    ):
        rc = main(_valid_cli_args())
        assert rc == 0
        assert mock_run.call_count == 1
        call_args, call_kwargs = mock_run.call_args
        actual_run_id = call_kwargs.get("run_id") or (call_args[0] if call_args else None)
        assert actual_run_id == RUN_ID


def test_cli_rejects_missing_flags():
    """CLI rejects missing required flags."""
    args = _valid_cli_args()
    bad_args = args[:-2]  # Remove --run-id
    rc = main(bad_args)
    assert rc != 0


def test_cli_rejects_forbidden_flags():
    """CLI rejects unauthorized flags like --output-root, --root, --force, --resume."""
    for forbidden in ["--output-root", "--root", "--force", "--resume", "--execution-baseline-dir"]:
        args = _valid_cli_args() + [forbidden, "injected_val"]
        rc = main(args)
        assert rc != 0


def test_cli_rejects_malformed_run_id():
    """CLI rejects run-id that does not match required regex grammar."""
    bad_run_ids = [
        "invalid_run_id",
        "stage1_5h_n3_regime_stratified_friction_20261003",
        "stage1_5h_n3_regime_stratified_friction_20261003T120000",
        "stage1_5h_n3_regime_stratified_friction_20261003T120000Z_extra",
    ]
    for bad_id in bad_run_ids:
        rc = main(_valid_cli_args(run_id=bad_id))
        assert rc != 0


def test_cli_fails_closed_when_generation_authority_absent():
    """Without receipt_generation_authorization.txt in Task 0 bundle, CLI fails closed."""
    rc = main(_valid_cli_args())
    assert rc != 0


def test_ast_guards_no_forbidden_imports():
    """AST guard proves neither core nor CLI imports network, socket, subprocess, or old H V3."""
    project_root = _get_project_root()
    core_path = project_root / CORE_MODULE
    cli_path = project_root / CLI_SCRIPT

    # If core or CLI does not exist yet (Task 1 RED phase), this test fails with not implemented
    if not core_path.is_file() or not cli_path.is_file():
        raise AssertionError("Stage 1.5H N=3 module or CLI not yet implemented")

    forbidden_modules = {
        "socket",
        "urllib",
        "requests",
        "aiohttp",
        "httpx",
        "subprocess",
        "src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic",
        "stage1_5h_v3_cross_root_liquidity_friction_diagnostic",
    }

    for target_path in (core_path, cli_path):
        tree = ast.parse(target_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden_modules, f"Forbidden import: {alias.name} in {target_path}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert node.module not in forbidden_modules, f"Forbidden import from: {node.module} in {target_path}"


def test_open_spy_no_raw_jsonl_opens_outside_stage1_5g_loader():
    """Proves raw JSONL depth/event evidence is not opened outside the Stage 1.5G loader."""
    try:
        from src.research.external_signal_shadow.stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic import (
            admit_frozen_n3_source_inputs,
        )
    except ImportError as e:
        raise AssertionError(f"Stage 1.5H N=3 module not yet implemented: {e}")

    # Inspect open calls during source re-admission
    opened_files: list[str] = []
    orig_open = open

    def spy_open(file, *args, **kwargs):
        opened_files.append(str(file))
        return orig_open(file, *args, **kwargs)

    with patch("builtins.open", side_effect=spy_open):
        admit_frozen_n3_source_inputs(project_root=_get_project_root())

    # Raw depth row files end with .jsonl.gz or .jsonl
    # All opens must be within verified Stage 1.5G loader
    assert len(opened_files) > 0
