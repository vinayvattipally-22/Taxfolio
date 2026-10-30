#!/usr/bin/env python3
"""PreToolUse guard for Claude Code in TaxFolio.

Keeps secrets and real taxpayer data out of the agent's context, and enforces the
repo's Git rules. Deny rules in settings.json cover the Read tool; this hook also
covers Bash (e.g. `cat .env`, `sqlite3 t4_analyzer.db`), which Read rules cannot see.

Exit codes:
    0  allow
    2  block — stderr is shown to Claude as the reason
"""

import json
import re
import sys
from pathlib import PurePosixPath

# Real secrets. `.env.example` is a template and stays readable.
SECRET_NAMES = {".env", ".env.local"}

# Real taxpayer data: uploaded T4/T5/NOA files, the app database, local sample sets.
DATA_DIRS = ("backend/uploads/", "uploads/", "sample_docs/", "test_data/")
DATA_SUFFIXES = (".db", ".db-journal", ".sqlite")

BASH_SECRET = re.compile(r"""(^|[\s/'"=<>(])\.env(\.local)?(?=$|[\s'";|&>)])""")
BASH_DATA = re.compile(r"(uploads/|sample_docs/|test_data/|\.db\b|\.db-journal\b|\bsqlite3\b)")

GIT_RULES = [
    (re.compile(r"--no-verify\b"), "Never use --no-verify. Fix the failing hook instead."),
    (
        re.compile(r"\bgit\s+add\s+(-A\b|--all\b|\.(\s|$))"),
        "Stage specific files, not `git add -A` / `git add .`.",
    ),
    (
        re.compile(r"\bgit\s+push\b.*(\s--force\b|\s-f\b|--force-with-lease)"),
        "Force-push is not allowed. Never rewrite published history.",
    ),
    (
        re.compile(r"\bgit\s+commit\b.*Co-Authored-By", re.IGNORECASE | re.DOTALL),
        "Commit messages must not include Co-Authored-By trailers.",
    ),
]


def normalize(path: str) -> str:
    """Return a lowercase, forward-slash version of a path for matching."""
    return path.replace("\\", "/").lower()


def is_protected_path(path: str) -> str | None:
    """Return why a path is off-limits, or None if it is fine."""
    norm = normalize(path)
    name = PurePosixPath(norm).name
    if name in SECRET_NAMES or (name.endswith(".env") and name != ".env.example"):
        return f"{name} holds secrets. Use .env.example for variable names."
    if any(f"/{d}" in f"/{norm.rstrip('/')}/" for d in DATA_DIRS):
        return "Uploaded and sample tax documents hold real PII (SIN, names, addresses)."
    if name.endswith(DATA_SUFFIXES):
        return f"{name} is the app database and holds taxpayer data."
    return None


def block(reason: str) -> None:
    """Print the reason for Claude and exit with the blocking code."""
    print(f"Blocked by .claude/hooks/guard_tool_use.py: {reason}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}

    if tool in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit", "Grep", "Glob"):
        path = (
            tool_input.get("file_path")
            or tool_input.get("notebook_path")
            or tool_input.get("path")
            or ""
        )
        reason = is_protected_path(path) if path else None
        if reason:
            block(reason + " Use the synthetic fixtures in backend/tests/ instead.")

    if tool == "Bash":
        command = tool_input.get("command") or ""
        if BASH_SECRET.search(command):
            block("This command touches .env. Read .env.example for variable names instead.")
        if BASH_DATA.search(normalize(command)):
            block(
                "This command touches uploaded documents or the app database, which hold "
                "real taxpayer PII. Use the synthetic fixtures in backend/tests/ instead."
            )
        for pattern, reason in GIT_RULES:
            if pattern.search(command):
                block(reason)

    sys.exit(0)


if __name__ == "__main__":
    main()
