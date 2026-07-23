"""Transport-neutral recent milestone evidence for Jarvis Project Control.

The module parses bounded caller-supplied Git log text only. It does not run
Git, read files, persist state, grant approval, or perform an external call.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re


CONTRACT_TYPE = "jarvis_recent_milestone_evidence"
VERSION = "0.1"
REPOSITORY_ID = "jarvis-core"
MAX_COMMITS = 5
MAX_FILES_PER_COMMIT = 20
MAX_RAW_LOG_BYTES = 256_000
MAX_SUBJECT_CHARS = 160
MAX_PATH_CHARS = 300
RECORD_SEPARATOR = "\x1e"
FIELD_SEPARATOR = "\x1f"

_HASH_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")
_WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


class RecentMilestoneEvidenceError(ValueError):
    """Raised when recent-milestone evidence cannot be trusted for display."""


@dataclass(frozen=True, slots=True)
class RecentMilestoneCommit:
    """One bounded, display-only local commit observation."""

    hash: str
    short_hash: str
    subject: str
    changed_files: tuple[str, ...]
    changed_file_count: int
    files_truncated: bool
    is_head: bool
    protected_path_present: bool
    read_only: bool


@dataclass(frozen=True, slots=True)
class RecentMilestoneEvidence:
    """Immutable recent commit evidence bound to one observed repository HEAD."""

    contract_type: str
    version: str
    repository_id: str
    observed_head: str
    head_matches_latest_commit: bool
    commits: tuple[RecentMilestoneCommit, ...]
    read_only: bool


def _normalize_hash(value: str, field: str) -> str:
    if not isinstance(value, str) or _HASH_PATTERN.fullmatch(value) is None:
        raise RecentMilestoneEvidenceError(f"{field} must be a full lowercase Git hash")
    return value


def _normalize_subject(value: str) -> str:
    if not isinstance(value, str):
        raise RecentMilestoneEvidenceError("commit subject must be text")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise RecentMilestoneEvidenceError("commit subject contains a control character")
    normalized = " ".join(value.strip().split())
    if not normalized:
        normalized = "(no subject)"
    if len(normalized) > MAX_SUBJECT_CHARS:
        normalized = normalized[: MAX_SUBJECT_CHARS - 1].rstrip() + "…"
    return normalized


def _normalize_display_path(value: str) -> str:
    if not isinstance(value, str):
        raise RecentMilestoneEvidenceError("changed file path must be text")
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_PATH_CHARS:
        raise RecentMilestoneEvidenceError("changed file path is empty or too long")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise RecentMilestoneEvidenceError("changed file path contains a control character")
    if (
        normalized.startswith(("/", "\\"))
        or _WINDOWS_ABSOLUTE_PATTERN.match(normalized)
        or normalized == ".."
        or normalized.startswith(("../", "..\\"))
    ):
        raise RecentMilestoneEvidenceError("changed file path must be repository-relative")
    return normalized


def parse_recent_milestone_log(
    raw_log: str,
    observed_head: str,
) -> RecentMilestoneEvidence:
    """Parse fixed separator-based Git log output into immutable evidence."""

    if not isinstance(raw_log, str):
        raise RecentMilestoneEvidenceError("recent Git log must be text")
    try:
        raw_size = len(raw_log.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise RecentMilestoneEvidenceError("recent Git log must be valid UTF-8") from exc
    if raw_size > MAX_RAW_LOG_BYTES:
        raise RecentMilestoneEvidenceError("recent Git log exceeds the display limit")

    normalized_head = _normalize_hash(observed_head, "observed_head")
    chunks = raw_log.split(RECORD_SEPARATOR)
    if chunks[0].strip():
        raise RecentMilestoneEvidenceError("recent Git log has data before its first record")

    commits: list[RecentMilestoneCommit] = []
    seen_hashes: set[str] = set()
    for chunk in chunks[1:]:
        if not chunk.strip():
            continue
        lines = chunk.strip("\r\n").splitlines()
        header = lines[0]
        hash_value, separator, subject = header.partition(FIELD_SEPARATOR)
        if not separator:
            raise RecentMilestoneEvidenceError("recent Git log record header is malformed")
        normalized_hash = _normalize_hash(hash_value, "commit hash")
        if normalized_hash in seen_hashes:
            raise RecentMilestoneEvidenceError("recent Git log contains a duplicate commit")
        seen_hashes.add(normalized_hash)

        changed_paths = [
            _normalize_display_path(line)
            for line in lines[1:]
            if line.strip()
        ]
        if len(set(changed_paths)) != len(changed_paths):
            raise RecentMilestoneEvidenceError("recent Git log contains a duplicate changed path")
        visible_paths = tuple(changed_paths[:MAX_FILES_PER_COMMIT])
        commits.append(
            RecentMilestoneCommit(
                hash=normalized_hash,
                short_hash=normalized_hash[:7],
                subject=_normalize_subject(subject),
                changed_files=visible_paths,
                changed_file_count=len(changed_paths),
                files_truncated=len(changed_paths) > len(visible_paths),
                is_head=normalized_hash == normalized_head,
                protected_path_present="jarvis.bat" in changed_paths,
                read_only=True,
            )
        )
        if len(commits) > MAX_COMMITS:
            raise RecentMilestoneEvidenceError("recent Git log contains too many commits")

    if not commits:
        raise RecentMilestoneEvidenceError("recent Git log contains no commits")
    return RecentMilestoneEvidence(
        contract_type=CONTRACT_TYPE,
        version=VERSION,
        repository_id=REPOSITORY_ID,
        observed_head=normalized_head,
        head_matches_latest_commit=commits[0].hash == normalized_head,
        commits=tuple(commits),
        read_only=True,
    )


def recent_milestone_evidence_to_dict(
    evidence: RecentMilestoneEvidence,
) -> dict[str, object]:
    """Return a stable transport mapping for one normalized evidence object."""

    if not isinstance(evidence, RecentMilestoneEvidence):
        raise RecentMilestoneEvidenceError("evidence must be normalized first")
    return {
        "contract_type": evidence.contract_type,
        "version": evidence.version,
        "repository_id": evidence.repository_id,
        "observed_head": evidence.observed_head,
        "head_matches_latest_commit": evidence.head_matches_latest_commit,
        "commits": [
            {
                "hash": commit.hash,
                "short_hash": commit.short_hash,
                "subject": commit.subject,
                "changed_files": list(commit.changed_files),
                "changed_file_count": commit.changed_file_count,
                "files_truncated": commit.files_truncated,
                "is_head": commit.is_head,
                "protected_path_present": commit.protected_path_present,
                "read_only": commit.read_only,
            }
            for commit in evidence.commits
        ],
        "read_only": evidence.read_only,
    }


def serialize_recent_milestone_evidence(evidence: RecentMilestoneEvidence) -> str:
    """Serialize normalized evidence deterministically without modifying it."""

    return json.dumps(
        recent_milestone_evidence_to_dict(evidence),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
