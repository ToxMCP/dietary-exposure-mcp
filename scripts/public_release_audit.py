#!/usr/bin/env python3
"""Audit the repository tree and optional Git history before public release."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "CITATION.cff",
    "THIRD_PARTY_NOTICES.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    ".github/ISSUE_TEMPLATE/bug-report.yml",
    ".github/ISSUE_TEMPLATE/scientific-correction.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "docs/applicability_limits.md",
    "docs/releases/v0.1.0.md",
)
TEXT_SUFFIXES = {
    ".cff",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
LOCAL_PATH_PATTERN = re.compile(
    r"(?:file://)?(?:/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\[^\\]+\\)"
)
PERSONAL_EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@(gmail|hotmail|outlook|yahoo|icloud|live|protonmail|proton)\.(com|fr|me|net)",
    re.IGNORECASE,
)
ACTION_USES_PATTERN = re.compile(r"^\s*-\s+uses:\s+([^\s#]+)")
PINNED_ACTION_PATTERN = re.compile(r"^[^@]+@[0-9a-fA-F]{40}$")
GITLEAKS_CHECKSUM_PATTERN = re.compile(r'GITLEAKS_SHA256:\s*"[0-9a-fA-F]{64}"')


def _run_git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _candidate_paths() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    return [REPO_ROOT / item.decode("utf-8") for item in output.split(b"\0") if item]


def _violation(code: str, message: str, *, path: str | None = None, line: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"code": code, "message": message}
    if path is not None:
        result["path"] = path
    if line is not None:
        result["line"] = line
    return result


def _scan_public_text(paths: list[Path]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                if LOCAL_PATH_PATTERN.search(line):
                    violations.append(
                        _violation(
                            "personal_workstation_path",
                            "Tracked public text contains an absolute workstation path or local file URI.",
                            path=relative_path,
                            line=line_number,
                        )
                    )
                if PERSONAL_EMAIL_PATTERN.search(line):
                    violations.append(
                        _violation(
                            "personal_email",
                            "Tracked public text contains a personal-address email domain.",
                            path=relative_path,
                            line=line_number,
                        )
                    )
    return violations


def _validate_workflow_supply_chain() -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    workflow_paths = sorted((REPO_ROOT / ".github" / "workflows").glob("*.y*ml"))
    for workflow_path in workflow_paths:
        relative_path = workflow_path.relative_to(REPO_ROOT).as_posix()
        for line_number, line in enumerate(workflow_path.read_text(encoding="utf-8").splitlines(), start=1):
            match = ACTION_USES_PATTERN.match(line)
            if not match:
                continue
            action_ref = match.group(1)
            if action_ref.startswith(("./", "docker://")):
                continue
            if not PINNED_ACTION_PATTERN.fullmatch(action_ref):
                violations.append(
                    _violation(
                        "workflow_action_unpinned",
                        "Third-party GitHub Actions must use an immutable 40-character commit SHA.",
                        path=relative_path,
                        line=line_number,
                    )
                )

    security_workflow_path = REPO_ROOT / ".github" / "workflows" / "security.yml"
    security_workflow = security_workflow_path.read_text(encoding="utf-8")
    if not GITLEAKS_CHECKSUM_PATTERN.search(security_workflow) or "sha256sum --check" not in security_workflow:
        violations.append(
            _violation(
                "gitleaks_checksum_missing",
                "The downloaded Gitleaks archive must be verified against a pinned SHA-256 digest.",
                path=".github/workflows/security.yml",
            )
        )
    return violations


def _validate_public_metadata() -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for relative_path in REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).is_file():
            violations.append(
                _violation("required_public_file_missing", "Required public-release file is missing.", path=relative_path)
            )

    if violations:
        return violations

    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    citation = yaml.safe_load((REPO_ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    if citation.get("cff-version") != "1.2.0":
        violations.append(_violation("citation_schema", "CITATION.cff must use CFF 1.2.0.", path="CITATION.cff"))
    if citation.get("version") != project.get("version"):
        violations.append(
            _violation("citation_version", "CITATION.cff and pyproject.toml versions differ.", path="CITATION.cff")
        )
    if citation.get("license") != project.get("license"):
        violations.append(
            _violation("citation_license", "CITATION.cff and pyproject.toml licenses differ.", path="CITATION.cff")
        )
    if not citation.get("authors"):
        violations.append(_violation("citation_authors", "CITATION.cff has no author entity.", path="CITATION.cff"))

    for relative_path in (
        ".github/ISSUE_TEMPLATE/bug-report.yml",
        ".github/ISSUE_TEMPLATE/scientific-correction.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
    ):
        payload = yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            violations.append(_violation("github_form_yaml", "GitHub form must be a YAML object.", path=relative_path))

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for required_reference in (
        "CITATION.cff",
        "THIRD_PARTY_NOTICES.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "v0.1.0.md",
    ):
        if required_reference not in readme:
            violations.append(
                _violation(
                    "readme_public_reference",
                    f"README.md does not link {required_reference}.",
                    path="README.md",
                )
            )
    if "Private MCP server" in readme:
        violations.append(
            _violation("private_branding", "README.md still describes the server as private.", path="README.md")
        )
    for required_badge in (
        "actions/workflows/security.yml/badge.svg?branch=main",
        "actions/workflows/scientific-invariants.yml/badge.svg?branch=main",
        "github/v/release/ToxMCP/dietary-exposure-mcp?sort=semver",
    ):
        if required_badge not in readme:
            violations.append(
                _violation(
                    "readme_release_badge",
                    f"README.md is missing release badge marker: {required_badge}",
                    path="README.md",
                )
            )

    release_note = (REPO_ROOT / "docs/releases/v0.1.0.md").read_text(encoding="utf-8")
    for required_phrase in (
        "stable software release; screening only",
        "not a safety conclusion",
        "Publishing `v0.1.0` does not change those scientific states",
        "OpenFoodTox 3.0",
        "2,417",
        "0feb8e3e4f9852c2d102375dd89d814ed08407a602d699882cf48bdd7f3c8c90",
        "THIRD_PARTY_NOTICES.md",
    ):
        if required_phrase not in release_note:
            violations.append(
                _violation(
                    "release_note_boundary",
                    f"Release note is missing required boundary text: {required_phrase}",
                    path="docs/releases/v0.1.0.md",
                )
            )

    limitations = (REPO_ROOT / "docs/applicability_limits.md").read_text(encoding="utf-8")
    for required_phrase in ("review_required", "Safe-use checklist", "current primary authority output"):
        if required_phrase not in limitations:
            violations.append(
                _violation(
                    "limitations_boundary",
                    f"Limitations guide is missing required boundary text: {required_phrase}",
                    path="docs/applicability_limits.md",
                )
            )
    return [*violations, *_validate_workflow_supply_chain()]


def audit_current_tree() -> list[dict[str, Any]]:
    """Return current-tree public-release violations."""
    return [*_scan_public_text(_candidate_paths()), *_validate_public_metadata()]


def audit_history() -> list[dict[str, Any]]:
    """Return redacted history blockers without printing private values."""
    blockers: list[dict[str, Any]] = []
    email_output = _run_git("log", "--all", "--format=%ae%n%ce")
    personal_emails = {
        match.group(0).lower()
        for match in PERSONAL_EMAIL_PATTERN.finditer(email_output)
        if "users.noreply.github.com" not in match.group(0).lower()
    }
    if personal_emails:
        blockers.append(
            _violation(
                "historical_personal_email",
                f"Git history contains {len(personal_emails)} unique personal-address email(s).",
            )
        )

    process = subprocess.Popen(
        ["git", "log", "--all", "--format=", "--patch", "--no-ext-diff", "--text"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    assert process.stdout is not None
    local_path_lines = sum(1 for line in process.stdout if LOCAL_PATH_PATTERN.search(line))
    stderr = process.stderr.read() if process.stderr is not None else ""
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"git history scan failed: {stderr.strip()}")
    if local_path_lines:
        blockers.append(
            _violation(
                "historical_workstation_path",
                f"Git patch history contains {local_path_lines} line(s) with absolute workstation paths.",
            )
        )
    return blockers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true", help="Also scan all reachable Git history.")
    args = parser.parse_args()

    current_violations = audit_current_tree()
    history_blockers = audit_history() if args.history else []
    payload = {
        "status": "ok" if not current_violations and not history_blockers else "blocked",
        "currentTreeViolations": current_violations,
        "historyBlockers": history_blockers,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["status"] != "ok":
        sys.exit(1)


if __name__ == "__main__":
    main()
