from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        msg = e.output.decode("utf-8", errors="replace")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{msg}") from e


def _is_git_repo() -> bool:
    try:
        _run(["git", "rev-parse", "--is-inside-work-tree"])
        return True
    except Exception:
        return False


def _has_staged_changes() -> bool:
    out = _run(["git", "diff", "--name-only", "--cached"])
    return bool(out.strip())


def _changed_files(base: str | None) -> list[str]:
    """
    Determine changed files.

    Priority:
    - if --base is provided: diff base...HEAD
    - else if staged changes exist: diff --cached
    - else: working tree diff
    """
    if base:
        out = _run(["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", f"{base}...HEAD"])
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    if _has_staged_changes():
        out = _run(["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "--cached"])
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    out = _run(["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"])
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _any_prefix(paths: Iterable[str], prefixes: Iterable[str]) -> bool:
    return any(any(p.startswith(pref) for pref in prefixes) for p in paths)


def _any_exact(paths: Iterable[str], exact: Iterable[str]) -> bool:
    s = set(paths)
    return any(x in s for x in exact)


@dataclass(frozen=True)
class GateRules:
    worklog_path: str = "docs/ai/WORKLOG.md"
    changelog_path: str = "docs/ai/CHANGELOG.md"
    adr_prefix: str = "docs/ai/adr/"
    adr_readme: str = "docs/ai/adr/README.md"

    # What counts as a "code change" for documentation gating?
    code_prefixes: tuple[str, ...] = ("src/", "scripts/")
    code_files: tuple[str, ...] = ("pyproject.toml", "docker-compose.yml")

    # What counts as an "architecture change" requiring an ADR?
    architecture_prefixes: tuple[str, ...] = ("src/core/", "src/agents/", "src/integrations/", "src/knowledge/")
    architecture_files: tuple[str, ...] = ("pyproject.toml", "docker-compose.yml")


def evaluate_gate(changed: list[str], rules: GateRules) -> tuple[bool, list[str]]:
    failures: list[str] = []

    has_code_change = _any_prefix(changed, rules.code_prefixes) or _any_exact(changed, rules.code_files)
    if not has_code_change:
        return True, []

    has_worklog = rules.worklog_path in changed
    has_changelog = rules.changelog_path in changed
    has_adr = any(p.startswith(rules.adr_prefix) and p != rules.adr_readme for p in changed)

    has_arch_change = _any_prefix(changed, rules.architecture_prefixes) or _any_exact(
        changed, rules.architecture_files
    )

    if not has_worklog:
        failures.append(f"Missing update: {rules.worklog_path}")
    if not has_changelog:
        failures.append(f"Missing update: {rules.changelog_path}")
    if has_arch_change and not has_adr:
        failures.append(f"Missing ADR update: add/modify a file under {rules.adr_prefix} (not README)")

    return len(failures) == 0, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="AORO documentation gate (CI-style).")
    parser.add_argument(
        "--base",
        help="Git base ref/sha to diff against (uses base...HEAD). In CI, set this to PR base SHA.",
        default=os.environ.get("DOCS_GATE_BASE"),
    )
    parser.add_argument("--show-changes", action="store_true", help="Print detected changed files.")
    args = parser.parse_args()

    if not _is_git_repo():
        print("docs_gate: not a git repo; skipping gate.")
        return 0

    changed = _changed_files(args.base)
    if args.show_changes:
        print("docs_gate: changed files:")
        for p in changed:
            print(f"- {p}")

    ok, failures = evaluate_gate(changed, GateRules())
    if ok:
        print("docs_gate: PASS")
        return 0

    print("docs_gate: FAIL")
    for f in failures:
        print(f"- {f}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


