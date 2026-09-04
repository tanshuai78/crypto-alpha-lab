#!/usr/bin/env python3
"""AST-based differential anti-shortcut and anti-fabrication scanner.

Scans production Python files (or changed lines against a base commit) for
common LLM coding shortcuts, invented provenance, layering violations, and
suspicious fallback patterns.

Standard library only.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class Finding(NamedTuple):
    file_path: str
    line: int
    col: int
    rule_id: str
    severity: str  # "ERROR" | "WARNING"
    message: str
    code_snippet: str


PROVENANCE_AUTHORITY_KEYS: set[str] = {
    "source_request_observation_id",
    "source_detail_revision_id",
    "source_article_id",
    "detail_raw_sha256",
    "raw_payload_relative_path",
    "notice_key",
    "event_id",
    "supervisor_run_id",
    "run_id",
    "attestation_id",
    "step_a_projection_sha256",
    "step_a_attestation_sha256",
    "trust_validation_status",
    "capture_mode",
    "detail_revisions.jsonl",
    "detail_revisions",
}


def get_callable_name(node: ast.AST) -> str:
    """Extract full qualified callable name (e.g. hashlib.sha256, self.write_atomic_bytes)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = get_callable_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def parse_diff_hunks(diff_text: str) -> set[int]:
    changed_lines: set[int] = set()
    hunk_pattern = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    for line in diff_text.splitlines():
        match = hunk_pattern.match(line)
        if match:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            if count == 0:
                continue
            for line_no in range(start, start + count):
                changed_lines.add(line_no)
    return changed_lines


def get_worktree_changed_lines(base_sha: str, file_path: str) -> set[int] | None:
    """Return line numbers changed in working tree for file_path since base_sha."""
    if not base_sha:
        return None

    git_env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
    try:
        cmd = ["git", "diff", "-U0", base_sha, "--", file_path]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, env=git_env)
        if not res.stdout:
            untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard", "--", file_path],
                capture_output=True,
                text=True,
                check=True,
                env=git_env,
            )
            if untracked.stdout.strip():
                return None  # Entire new/untracked file
            return set()  # No diff in worktree vs base
        return parse_diff_hunks(res.stdout)
    except Exception:
        return None


def get_index_changed_lines(base_sha: str, file_path: str) -> set[int] | None:
    """Return line numbers changed in Git index (staged) for file_path since base_sha."""
    if not base_sha:
        return None

    git_env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
    try:
        cmd = ["git", "diff", "--cached", "-U0", base_sha, "--", file_path]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, env=git_env)
        if not res.stdout:
            return set()  # No staged diff vs base
        return parse_diff_hunks(res.stdout)
    except Exception:
        return None


class ShortcutVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, source_lines: list[str], is_src: bool):
        self.file_path = file_path
        self.source_lines = source_lines
        self.is_src = is_src
        self.findings: list[Finding] = []

    def _get_snippet(self, line: int) -> str:
        if 1 <= line <= len(self.source_lines):
            return self.source_lines[line - 1].strip()
        return ""

    def visit_Import(self, node: ast.Import) -> None:
        if self.is_src:
            for alias in node.names:
                if alias.name == "scripts" or alias.name.startswith("scripts."):
                    self.findings.append(Finding(
                        file_path=self.file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        rule_id="RULE-AST-01-LAYERING-VIOLATION",
                        severity="ERROR",
                        message="Production src module must not import from scripts layer",
                        code_snippet=self._get_snippet(node.lineno),
                    ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self.is_src and node.module:
            if node.module == "scripts" or node.module.startswith("scripts."):
                self.findings.append(Finding(
                    file_path=self.file_path,
                    line=node.lineno,
                    col=node.col_offset,
                    rule_id="RULE-AST-01-LAYERING-VIOLATION",
                    severity="ERROR",
                    message="Production src module must not import from scripts layer",
                    code_snippet=self._get_snippet(node.lineno),
                ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = get_callable_name(node.func)

        # 1. Check for .get(..., default) on dictionary lookups
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            if len(node.args) >= 2:
                key_arg = node.args[0]
                default_arg = node.args[1]
                key_str = key_arg.value if (isinstance(key_arg, ast.Constant) and isinstance(key_arg.value, str)) else ""
                is_authority_key = key_str in PROVENANCE_AUTHORITY_KEYS
                is_none_default = isinstance(default_arg, ast.Constant) and default_arg.value is None

                if is_authority_key and not is_none_default:
                    # Critical authority/provenance key cannot have synthetic fallback
                    self.findings.append(Finding(
                        file_path=self.file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        rule_id="RULE-AST-02-INVENTED-FALLBACK-DEFAULT",
                        severity="ERROR",
                        message=f"Invented fallback default for critical provenance/authority key '{key_str}'",
                        code_snippet=self._get_snippet(node.lineno),
                    ))
                elif isinstance(default_arg, ast.Constant) and isinstance(default_arg.value, (str, int)):
                    val_str = str(default_arg.value)
                    if re.match(r"^(req|rev)_[0-9]+$", val_str) or (
                        val_str in ("0", "") and any(s in key_str for s in ("id", "offset", "sha", "hash"))
                    ):
                        self.findings.append(Finding(
                            file_path=self.file_path,
                            line=node.lineno,
                            col=node.col_offset,
                            rule_id="RULE-AST-02-INVENTED-FALLBACK-DEFAULT",
                            severity="ERROR",
                            message=f"Suspicious invented default '{val_str}' for key '{key_str}' in .get() lookup",
                            code_snippet=self._get_snippet(node.lineno),
                        ))
                    elif self.is_src and not is_none_default:
                        self.findings.append(Finding(
                            file_path=self.file_path,
                            line=node.lineno,
                            col=node.col_offset,
                            rule_id="RULE-AST-02-DICT-GET-FALLBACK",
                            severity="WARNING",
                            message=f".get({key_str!r}, {val_str!r}) literal fallback requires justification in Task scanner disposition ledger",
                            code_snippet=self._get_snippet(node.lineno),
                        ))

        # 2. Check for .setdefault(...)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "setdefault":
            self.findings.append(Finding(
                file_path=self.file_path,
                line=node.lineno,
                col=node.col_offset,
                rule_id="RULE-AST-03-SETDEFAULT-MUTATION",
                severity="WARNING",
                message=".setdefault() detected; ensure authority fields are not mutated or defaulted",
                code_snippet=self._get_snippet(node.lineno),
            ))

        # 3. Check for sha256 / hashlib.sha256 hashing profile ID string instead of file bytes
        if "sha256" in func_name.lower() and len(node.args) >= 1:
            arg = node.args[0]
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "encode":
                target = arg.func.value
                target_str = ""
                if isinstance(target, ast.Name):
                    target_str = target.id.lower()
                elif isinstance(target, ast.Attribute):
                    target_str = target.attr.lower()
                if re.search(r"(pid|profile_?id|base_profile_?id)", target_str):
                    self.findings.append(Finding(
                        file_path=self.file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        rule_id="RULE-AST-04-FORGED-PROFILE-HASH",
                        severity="ERROR",
                        message=f"Forged profile hash detected: hashing profile ID string ('{target_str}') instead of actual attested profile content bytes",
                        code_snippet=self._get_snippet(node.lineno),
                    ))

        # 4. Check for write_atomic_bytes / write_bytes copying upstream attestation
        if any(func_name.endswith(suffix) for suffix in ("write_atomic_bytes", "write_bytes", "write_atomic_json")):
            all_args = list(node.args) + [kw.value for kw in node.keywords]
            for arg in all_args:
                arg_name = ""
                if isinstance(arg, ast.Name):
                    arg_name = arg.id.lower()
                elif isinstance(arg, ast.Attribute):
                    arg_name = f"{get_callable_name(arg.value)}.{arg.attr}".lower()
                if "attestation" in arg_name and any(k in arg_name for k in ("e_a", "upstream", "step_a")):
                    self.findings.append(Finding(
                        file_path=self.file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        rule_id="RULE-AST-05-FORGED-ATTESTATION-COPY",
                        severity="ERROR",
                        message="Direct copy of upstream attestation bytes into downstream attestation artifact",
                        code_snippet=self._get_snippet(node.lineno),
                    ))

        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        if isinstance(node.op, ast.Or) and len(node.values) >= 2:
            left = node.values[0]
            left_key = ""
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) and left.func.attr == "get":
                if left.args and isinstance(left.args[0], ast.Constant) and isinstance(left.args[0].value, str):
                    left_key = left.args[0].value
            elif isinstance(left, ast.Subscript) and isinstance(left.slice, ast.Constant) and isinstance(left.slice.value, str):
                left_key = left.slice.value

            last_val = node.values[-1]
            if isinstance(last_val, ast.Constant):
                val_str = str(last_val.value)
                if left_key in PROVENANCE_AUTHORITY_KEYS and last_val.value is not None:
                    self.findings.append(Finding(
                        file_path=self.file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        rule_id="RULE-AST-02-INVENTED-FALLBACK-DEFAULT",
                        severity="ERROR",
                        message=f"Invented fallback 'or {val_str!r}' on critical provenance/authority key '{left_key}'",
                        code_snippet=self._get_snippet(node.lineno),
                    ))
                elif re.match(r"^(req|rev)_[0-9]+$", val_str):
                    self.findings.append(Finding(
                        file_path=self.file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        rule_id="RULE-AST-02-INVENTED-FALLBACK-DEFAULT",
                        severity="ERROR",
                        message=f"Suspicious 'or {val_str!r}' invented fallback expression",
                        code_snippet=self._get_snippet(node.lineno),
                    ))
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        # Check for literal placeholder string constants in production code
        if isinstance(node.value, str):
            val_str = node.value
            if re.match(r"^(req|rev)_[0-9]+$", val_str):
                # If it's in src/, it's highly suspicious
                if self.is_src:
                    self.findings.append(Finding(
                        file_path=self.file_path,
                        line=node.lineno,
                        col=node.col_offset,
                        rule_id="RULE-AST-06-LITERAL-PROVENANCE-PLACEHOLDER",
                        severity="ERROR",
                        message=f"Literal placeholder '{val_str}' used in production src module",
                        code_snippet=self._get_snippet(node.lineno),
                    ))
        self.generic_visit(node)


def scan_source(
    content: str,
    display_path: str,
    changed_lines: set[int] | None,
    is_src: bool,
) -> list[Finding]:
    try:
        tree = ast.parse(content, filename=display_path)
    except SyntaxError as exc:
        return [
            Finding(
                file_path=display_path,
                line=exc.lineno or 1,
                col=exc.offset or 0,
                rule_id="RULE-AST-00-SCANNER-INTEGRITY",
                severity="ERROR",
                message=f"Syntax error prevents AST scan: {exc.msg}",
                code_snippet=exc.text.strip() if exc.text else "",
            )
        ]

    lines = content.splitlines()
    visitor = ShortcutVisitor(display_path, lines, is_src=is_src)
    visitor.visit(tree)

    if changed_lines is None:
        return visitor.findings

    # Filter findings to changed lines, but ALWAYS preserve integrity errors
    return [
        f for f in visitor.findings 
        if f.rule_id == "RULE-AST-00-SCANNER-INTEGRITY" or f.line in changed_lines
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AST-based differential anti-shortcut scanner (worktree and git index)"
    )
    parser.add_argument(
        "--base-sha",
        help="Base git commit SHA to compute differential changed lines against",
        default="",
    )
    parser.add_argument(
        "--all-lines",
        action="store_true",
        help="Scan all lines in target files, ignoring git diff",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific files to scan. If omitted, scans touched production files.",
    )
    args = parser.parse_args()

    git_env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"}
    try:
        repo_root = Path(
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                env=git_env,
            ).stdout.strip()
        ).resolve()
    except Exception:
        repo_root = Path.cwd().resolve()

    target_rel_paths: set[str] = set()
    if args.files:
        for f in args.files:
            p = Path(f).resolve()
            try:
                rel_p = str(p.relative_to(repo_root))
            except ValueError:
                rel_p = str(p)
            if p.suffix == ".py" or rel_p.endswith(".py"):
                target_rel_paths.add(rel_p)
    else:
        diff_base = args.base_sha if args.base_sha else "HEAD"

        # 1. Tracked worktree changes vs diff_base
        try:
            cmd = ["git", "diff", "--name-only", "-z", "--diff-filter=ACMR", diff_base]
            res = subprocess.run(cmd, capture_output=True, check=True, env=git_env)
            for raw_p in res.stdout.split(b"\x00"):
                if raw_p:
                    target_rel_paths.add(raw_p.decode("utf-8", errors="replace"))
        except subprocess.CalledProcessError as exc:
            print(f"Error: git diff failed: {exc}", file=sys.stderr)
            return 2

        # 2. Tracked staged index changes vs diff_base
        try:
            cmd = ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR", diff_base]
            res = subprocess.run(cmd, capture_output=True, check=True, env=git_env)
            for raw_p in res.stdout.split(b"\x00"):
                if raw_p:
                    target_rel_paths.add(raw_p.decode("utf-8", errors="replace"))
        except subprocess.CalledProcessError as exc:
            print(f"Error: git diff --cached failed: {exc}", file=sys.stderr)
            return 2

        # 3. Untracked files
        try:
            cmd = ["git", "ls-files", "-z", "--others", "--exclude-standard"]
            res = subprocess.run(cmd, capture_output=True, check=True, env=git_env)
            for raw_p in res.stdout.split(b"\x00"):
                if raw_p:
                    target_rel_paths.add(raw_p.decode("utf-8", errors="replace"))
        except subprocess.CalledProcessError as exc:
            print(f"Error: git ls-files failed: {exc}", file=sys.stderr)
            return 2

    # Filter target paths to python files under src/ and scripts/ (or explicit files)
    filtered_rel_paths: list[str] = []
    for p_str in sorted(target_rel_paths):
        if p_str.endswith(".py") and (
            bool(args.files) or p_str.startswith("src/") or p_str.startswith("scripts/")
        ):
            filtered_rel_paths.append(p_str)

    total_errors = 0
    total_warnings = 0

    for rel_path in filtered_rel_paths:
        is_src = rel_path.startswith("src/") or "/src/" in rel_path
        worktree_file = repo_root / rel_path
        worktree_content: str | None = None

        # A. Scan Worktree Representation (if file exists on disk)
        if worktree_file.is_file():
            try:
                worktree_content = worktree_file.read_text(encoding="utf-8")
                changed_lines = None if args.all_lines else get_worktree_changed_lines(args.base_sha, rel_path)
                if changed_lines is None or len(changed_lines) > 0:
                    findings = scan_source(worktree_content, str(worktree_file), changed_lines, is_src)
                    for f in findings:
                        prefix = "ERROR" if f.severity == "ERROR" else "WARN"
                        print(f"[{prefix}] {f.file_path}:{f.line}:{f.col} - {f.rule_id}: {f.message}")
                        if f.code_snippet:
                            print(f"        Line {f.line}: {f.code_snippet}")
                        if f.severity == "ERROR":
                            total_errors += 1
                        else:
                            total_warnings += 1
            except Exception as exc:
                print(f"[ERROR] {worktree_file}:1:0 - RULE-AST-00-SCANNER-INTEGRITY: Scanner could not read worktree file: {exc}")
                total_errors += 1

        # B. Scan Git Index Representation (if staged blob exists)
        try:
            cmd = ["git", "show", f":{rel_path}"]
            res = subprocess.run(cmd, capture_output=True, env=git_env)
            if res.returncode == 0:
                index_content = res.stdout.decode("utf-8", errors="replace")
                # If worktree content is identical to index content, skip re-scanning to avoid duplicate findings
                if worktree_content is None or index_content != worktree_content:
                    index_changed_lines = None if args.all_lines else get_index_changed_lines(args.base_sha, rel_path)
                    if index_changed_lines is None or len(index_changed_lines) > 0:
                        index_display = f"{rel_path} (git index / staged blob)"
                        findings = scan_source(index_content, index_display, index_changed_lines, is_src)
                        for f in findings:
                            prefix = "ERROR" if f.severity == "ERROR" else "WARN"
                            print(f"[{prefix}] {f.file_path}:{f.line}:{f.col} - {f.rule_id}: {f.message}")
                            if f.code_snippet:
                                print(f"        Line {f.line}: {f.code_snippet}")
                            if f.severity == "ERROR":
                                total_errors += 1
                            else:
                                total_warnings += 1
        except Exception as exc:
            print(f"[ERROR] {rel_path} (git index):1:0 - RULE-AST-00-SCANNER-INTEGRITY: Could not inspect staged blob: {exc}")
            total_errors += 1

    if total_errors > 0:
        print(
            f"\nAnti-shortcut scan failed: {total_errors} error(s), {total_warnings} warning(s).",
            file=sys.stderr,
        )
        return 1

    if total_warnings > 0:
        print(
            f"\nAnti-shortcut scan passed with {total_warnings} warning(s). All warnings require explicit disposition in Task ledger.",
            file=sys.stderr,
        )
    else:
        print("\nAnti-shortcut scan passed: clean.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
