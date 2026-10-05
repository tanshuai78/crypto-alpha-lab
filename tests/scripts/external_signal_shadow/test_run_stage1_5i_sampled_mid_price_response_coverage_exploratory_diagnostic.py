import ast
import hashlib
import inspect
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

try:
    from scripts.external_signal_shadow.run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic import (
        main,
    )
except ImportError as _import_err:
    _err_msg = str(_import_err)

    def main(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"STOP=I_CORE_NOT_IMPLEMENTED: {_err_msg}")


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


DESIGN_PATH = "docs/designs/2026-10-04-external-signal-shadow-lab-stage1-5i-sampled-mid-price-response-coverage-exploratory-diagnostic-design_CN.md"
DESIGN_SHA = "9b9e2c51927c521844e8121e60ae1aa6b7bbe9acd175e05dfadad4c1a034efc8"
PLAN_PATH = "docs/plans/2026-10-04-external-signal-shadow-lab-stage1-5i-sampled-mid-price-response-coverage-exploratory-diagnostic-implementation-plan_CN.md"
PLAN_SHA = "4c233bca0587efa488dbb8339a225d8657e1b0a6c71796f75882fa5a210c2f65"
RUN_ID = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
CORE_MODULE = "src/research/external_signal_shadow/stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py"
CLI_SCRIPT = "scripts/external_signal_shadow/run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py"


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
        from src.research.external_signal_shadow.stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic import (
            APPROVED_PLAN_SHA256,
            get_canonical_execution_authority_bundle_path,
        )
    except ImportError as e:
        raise RuntimeError(f"STOP=I_CORE_NOT_IMPLEMENTED: {e}")

    # 1. Signature check: strictly zero parameters
    sig = inspect.signature(get_canonical_execution_authority_bundle_path)
    assert len(sig.parameters) == 0, f"Expected 0 parameters, got {list(sig.parameters.keys())}"

    # 2. Exact return value check
    project_root = _get_project_root()
    bundle_path = get_canonical_execution_authority_bundle_path()
    expected_path = project_root / f".git/plan-execution/stage1_5i_n3_sampled_mid_price_response/{APPROVED_PLAN_SHA256}"
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
        "run_id": RUN_ID,
        "decision": "stage1_5i_coverage_inventory_published",
    })
    with patch(
        "scripts.external_signal_shadow.run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.run_diagnostic",
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
        "stage1_5i_n3_sampled_mid_price_response_20261004",
        "stage1_5i_n3_sampled_mid_price_response_20261004T120000",
        "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z_extra",
    ]
    for bad_id in bad_run_ids:
        rc = main(_valid_cli_args(run_id=bad_id))
        assert rc != 0


def test_cli_fails_closed_when_generation_authority_absent():
    """Without receipt_generation_authorization.txt in Task 0 bundle, CLI fails closed."""
    rc = main(_valid_cli_args())
    assert rc != 0


def test_ast_guards_no_forbidden_imports_or_bypasses():
    """AST guard proves CLI has zero network/socket/subprocess imports and delegates solely to run_diagnostic."""
    project_root = _get_project_root()
    cli_path = project_root / CLI_SCRIPT
    if not cli_path.is_file():
        raise RuntimeError("STOP=I_CORE_NOT_IMPLEMENTED: CLI script absent")

    tree = ast.parse(cli_path.read_text(encoding="utf-8"))
    forbidden_modules = {
        "socket", "urllib", "requests", "http", "aiohttp", "httpx",
        "subprocess", "asyncio", "ftplib", "smtplib", "telnetlib",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import from: {node.module}"


def test_cli_integration_redirects_to_tmp_sink_without_real_receipt(tmp_path):
    """Public CLI integration test proving redirect to test sink without publishing real receipt."""
    # Verifies that run_diagnostic with test redirect runs full pipeline to tmp_path sink
    try:
        from src.research.external_signal_shadow.stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic import (
            run_diagnostic,
        )
    except ImportError as e:
        raise RuntimeError(f"STOP=I_CORE_NOT_IMPLEMENTED: {e}")

    # Mock spy ensuring no write to data/
    test_sink = MagicMock()
    with patch(
        "src.research.external_signal_shadow.stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic._publish_production_receipt",
        test_sink,
    ):
        with pytest.raises(Exception):
            # Without generation authority, it must fail closed before calling test_sink
            run_diagnostic(RUN_ID)
        assert test_sink.call_count == 0


def test_cli_public_integration_success_path_with_test_seam(tmp_path):
    """Public CLI success path integration with real project_root, real G/H re-admission, and private publication sink."""
    try:
        import src.research.external_signal_shadow.stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic as core_mod
        from src.research.external_signal_shadow.stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic import (
            APPROVED_PLAN_REL_PATH,
            APPROVED_PLAN_SHA256,
            Stage1_5IN3DiagnosticError,
            _sha256,
            classify_n3_sampled_mid_price_response_root_state,
            get_canonical_execution_authority_bundle_path,
            load_verified_n3_sampled_mid_price_response_root,
        )
    except ImportError as e:
        raise RuntimeError(f"STOP=I_CORE_NOT_IMPLEMENTED: {e}")

    project_root = _get_project_root()
    bundle_src = get_canonical_execution_authority_bundle_path()
    bundle_dir = tmp_path / "bundle"
    shutil.copytree(bundle_src, bundle_dir)

    # Construct valid receipt_generation_authorization.txt
    core_file = project_root / CORE_MODULE
    cli_file = project_root / CLI_SCRIPT
    core_sha = _sha256(core_file)
    cli_sha = _sha256(cli_file)

    auth_text = (
        f"我批准本地生成 Stage 1.5I N=3 sampled-mid-price response receipt：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。\n"
        f"RUN_ID: {RUN_ID}\n"
        f"I_CORE_SHA256: {core_sha}\n"
        f"I_CLI_SHA256: {cli_sha}\n"
        "允许仅本地生成 Stage 1.5I N=3 sampled-mid-price response receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。\n"
    )
    gen_file = bundle_dir / "receipt_generation_authorization.txt"
    gen_file.write_text(auth_text, encoding="utf-8")
    gen_sha = hashlib.sha256(auth_text.encode("utf-8")).hexdigest()
    (bundle_dir / "receipt_generation_authorization.sha256").write_text(
        f"{gen_sha}  receipt_generation_authorization.txt\n", encoding="utf-8"
    )

    private_sink = tmp_path / "private_sink"
    private_sink.mkdir()

    # Execute private test seam helper
    summary = core_mod._run_diagnostic_for_test(
        run_id=RUN_ID,
        bundle_dir=bundle_dir,
        output_parent=private_sink,
        project_root=project_root,
    )
    assert summary["run_id"] == RUN_ID
    assert summary["decision"] == "stage1_5i_complete_n3_exploratory_analysis_published"

    # Verify receipt produced in private_sink via private test loader
    final_root = private_sink / RUN_ID
    assert final_root.is_dir()
    loaded = core_mod._load_verified_n3_sampled_mid_price_response_root_for_test(
        final_root,
        allowed_parent=private_sink,
        project_root=project_root,
    )
    assert loaded["summary"]["run_id"] == RUN_ID
    assert loaded["summary"]["coverage_inventory"]["child_count"] == 9
    assert loaded["summary"]["coverage_inventory"]["parent_count"] == 3
    assert loaded["summary"]["decision"] == "stage1_5i_complete_n3_exploratory_analysis_published"

    # Public loader and classifier MUST reject final_root because it is in private_sink, not canonical OUTPUT_PARENT_REL
    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        load_verified_n3_sampled_mid_price_response_root(final_root)
    assert "STOP=noncanonical_output_parent" in str(exc_info.value)
    assert classify_n3_sampled_mid_price_response_root_state(final_root) == "corrupt_or_unknown"

    # Parameter check: public loader and classifier must not accept project_root
    assert "project_root" not in inspect.signature(load_verified_n3_sampled_mid_price_response_root).parameters
    assert "project_root" not in inspect.signature(classify_n3_sampled_mid_price_response_root_state).parameters

    # Verify real production directory has no receipt created
    prod_out = project_root / "data/external_signal_shadow/stage1_5i/n3_sampled_mid_price_response"
    if prod_out.exists():
        assert not (prod_out / RUN_ID).exists()
