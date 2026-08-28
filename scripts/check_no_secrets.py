"""Deterministically scan tracked files for likely-committed secrets.

Promotes AGENTS.md principle 5 ("비밀 정보는 생성·저장·커밋하지 않는다") from a
documentation-only rule to a checkable script. Detects common secret shapes
(cloud provider keys, LLM API keys, private key blocks, generic
password/token/secret assignments) and reports file:line with the matched
value redacted. It does not execute anything and does not talk to any
external service.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Values that look like a placeholder rather than a real secret. Checked
# case-insensitively against the matched value itself.
PLACEHOLDER_MARKERS = (
    "example",
    "changeme",
    "change_me",
    "your_",
    "youre_",
    "placeholder",
    "redacted",
    "<",  # e.g. <YOUR_API_KEY>
    "{{",  # templating
    "${",  # shell/CI variable expansion, not a literal secret
)

GENERIC_ASSIGNMENT_KEYS = (
    "api_key",
    "api-key",
    "apikey",
    "secret",
    "token",
    "password",
    "passwd",
    "pwd",
    "access_key",
    "private_key",
)


@dataclass(frozen=True)
class Pattern:
    code: str
    regex: re.Pattern[str]
    # Which regex group holds the secret-like value to redact/placeholder-check.
    # 0 means "the whole match".
    value_group: int = 0


def _build_patterns() -> tuple[Pattern, ...]:
    generic_keys = "|".join(re.escape(key) for key in GENERIC_ASSIGNMENT_KEYS)
    return (
        Pattern(
            "aws_access_key_id",
            re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        ),
        Pattern(
            "openai_style_key",
            re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        ),
        Pattern(
            "anthropic_style_key",
            re.compile(r"\bsk-ant-[A-Za-z0-9\-]{20,}\b"),
        ),
        Pattern(
            "slack_token",
            re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b"),
        ),
        Pattern(
            "github_token",
            re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
        ),
        Pattern(
            "private_key_block",
            re.compile(
                r"-----BEGIN ((RSA|EC|OPENSSH|DSA|PGP) )?PRIVATE KEY-----"
            ),
        ),
        Pattern(
            "generic_secret_assignment",
            re.compile(
                rf"(?i)\b(\w*(?:{generic_keys})\w*)\s*[:=]\s*[\"']([^\"'\s]{{8,}})[\"']"
            ),
            value_group=2,
        ),
    )


PATTERNS = _build_patterns()

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".jsonl",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".env",
    ".example",
    ".bat",
    ".ps1",
    ".sh",
    ".js",
    ".ts",
    ".html",
    ".css",
}

EXCLUDED_DIR_PARTS = {".git", "__pycache__", "node_modules"}


@dataclass(frozen=True)
class Finding:
    path: str
    line_number: int
    code: str
    redacted: str


_READABLE_LABEL_RE = re.compile(r"^[a-z]+(?:[-_][a-z]+)*$")


def _is_placeholder(value: str) -> bool:
    lowered = value.lower()
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        return True
    # Low-entropy values (all the same repeated char, e.g. "xxxxxxxx" or
    # "00000000") read as filler rather than a real secret.
    stripped = lowered.strip("-_")
    if stripped and len(set(stripped)) <= 2:
        return True
    # Pure lowercase word(s) joined by - or _, no digits/mixed case (e.g.
    # "evidence-token-two", "internal_tests_only") read as a human-chosen
    # label/fixture name rather than a generated secret.
    return bool(_READABLE_LABEL_RE.match(value))


def _is_env_var_name_reference(key: str) -> bool:
    """True for `SOMETHING_ENV = "SOMETHING"` — the variable holds the
    *name* of an environment variable, not a secret value."""
    normalized = key.strip().lower()
    return normalized == "env" or normalized.endswith("_env")


def _redact(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def scan_text(text: str, *, path: str = "<text>") -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern in PATTERNS:
            for match in pattern.regex.finditer(line):
                value = (
                    match.group(0)
                    if pattern.value_group == 0
                    else match.group(pattern.value_group)
                )
                if _is_placeholder(value):
                    continue
                if (
                    pattern.code == "generic_secret_assignment"
                    and _is_env_var_name_reference(match.group(1))
                ):
                    continue
                findings.append(
                    Finding(
                        path=path,
                        line_number=line_number,
                        code=pattern.code,
                        redacted=_redact(value),
                    )
                )
    return findings


def _should_skip(path: Path) -> bool:
    if any(part in EXCLUDED_DIR_PARTS for part in path.parts):
        return True
    return path.suffix.lower() not in TEXT_SUFFIXES


def _git_tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def _git_staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--cached", "--name-only"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def scan_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        if _should_skip(path) or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = str(path.resolve().relative_to(ROOT)).replace("\\", "/")
        findings.extend(scan_text(text, path=relative))
    return findings


# --- self-test ---------------------------------------------------------

_POSITIVE_FIXTURES: tuple[tuple[str, str], ...] = (
    ("aws_access_key_id", "aws_key = AKIAABCDEFGHIJKLMNOP"),
    (
        "openai_style_key",
        "OPENAI_API_KEY_LITERAL = sk-Tr7qLm2Zx9BpN4vKdC1sYh6e",
    ),
    (
        "anthropic_style_key",
        "ANTHROPIC_LITERAL = sk-ant-Qw3eRt7yUi2oPl9kJh5gFd8s",
    ),
    ("slack_token", "token = xoxb-19f3820561-h3jK9mQpLz2R"),
    ("github_token", "gh_pat = ghp_9mK3pQzL7xVbN2wRcT5jH8dYfA6sE4uG1oI0"),
    ("private_key_block", "-----BEGIN RSA PRIVATE KEY-----"),
    ("generic_secret_assignment", 'db_password = "hunter2hunter2"'),
)

_NEGATIVE_FIXTURES: tuple[str, ...] = (
    "ANTHROPIC_API_KEY is read from the environment, never committed.",
    'api_key = "YOUR_API_KEY_HERE"',
    'token = "<PASTE_TOKEN>"',
    'password = "${DB_PASSWORD}"',
    'secret = "changeme"',
    "이 저장소는 API 키를 커밋하지 않는다.",
    'TEAM_MANAGER_BOT_TOKEN_ENV = "TEAM_MANAGER_BOT_TOKEN"',
    'completionEvidenceToken = "evidence-token-two"',
    'MEMORY_PREVIEW_TOKEN_SUBSYSTEM_STATUS = "internal_tests_only"',
)


def _run_self_test() -> tuple[int, list[str]]:
    failures: list[str] = []
    checks = 0
    for expected_code, fixture in _POSITIVE_FIXTURES:
        checks += 1
        findings = scan_text(fixture, path="<fixture>")
        codes = {finding.code for finding in findings}
        if expected_code not in codes:
            failures.append(
                f"positive fixture missed {expected_code!r}: {fixture!r} -> {codes!r}"
            )
    for fixture in _NEGATIVE_FIXTURES:
        checks += 1
        findings = scan_text(fixture, path="<fixture>")
        if findings:
            failures.append(
                f"negative fixture false-positived: {fixture!r} -> {findings!r}"
            )
    return checks, failures


# --- CLI -----------------------------------------------------------------


def _print_findings(findings: list[Finding]) -> None:
    for finding in sorted(findings, key=lambda f: (f.path, f.line_number)):
        print(
            f"{finding.path}:{finding.line_number} [{finding.code}] {finding.redacted}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Scan only git-staged files instead of all tracked files.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run built-in positive/negative fixtures instead of scanning the repo.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        checks, failures = _run_self_test()
        print("check_no_secrets self-test")
        print(f"checks={checks}")
        print(f"failures={len(failures)}")
        if failures:
            print("status=FAIL")
            for failure in failures:
                print(f"ERROR {failure}")
            return 1
        print("status=PASS")
        return 0

    paths = _git_staged_files() if args.staged else _git_tracked_files()
    findings = scan_paths(paths)

    print("check_no_secrets scan")
    print(f"files_scanned={len(paths)}")
    print(f"findings={len(findings)}")
    if findings:
        print("status=FAIL")
        _print_findings(findings)
        return 1
    print("status=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
