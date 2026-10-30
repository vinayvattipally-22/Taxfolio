#!/usr/bin/env python3
"""PostToolUse checks for Claude Code in TaxFolio.

Runs after every Edit/Write on the file that was just changed.

Blocking (exit 2, stderr fed back to Claude):
  - Secret scan on any text file (OpenAI, Anthropic, AWS, Alpha Vantage-style keys,
    private keys).
  - Python syntax check on any .py file.
  - backend/prompts/*.py: every *_PROMPT dict must have all 8 prompt-template fields.

Advisory (exit 0, added to Claude's context):
  - backend/routers/*.py: routes with no auth dependency (possible IDOR).
  - backend/rules/*.py: `.get(tax_year, <default>)` silent year fallbacks.
"""

import ast
import json
import re
import sys
from pathlib import Path

SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "Anthropic API key"),
    (re.compile(r"sk-(proj-)?[A-Za-z0-9]{20,}"), "OpenAI API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key ID"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "private key"),
    (
        re.compile(r"(ALPHA_VANTAGE_API_KEY|OPENAI_API_KEY|SECRET_KEY)\s*=\s*['\"][^'\"\s]{12,}"),
        "hard-coded key assignment",
    ),
]

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".sh", ".ps1",
}  # fmt: skip

PROMPT_FIELDS = (
    "aiRole", "systemRole", "objective", "taskInstructions",
    "taskInput", "taskOutputFormat", "taskExample", "settingsJson",
)  # fmt: skip

AUTH_DEPENDENCIES = {"get_current_user", "get_current_user_optional", "require_advisor"}
PUBLIC_ROUTES = {"/register", "/login", "/health", "/token", "/refresh"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

problems: list[str] = []
notes: list[str] = []


def scan_secrets(path: Path, text: str) -> None:
    """Flag credential material written into a file."""
    for pattern, label in SECRET_PATTERNS:
        if pattern.search(text):
            problems.append(
                f"Possible {label} in {path.name}. Keys belong in .env (see .env.example), "
                "never in code, tests, docs or config."
            )


def parse_python(path: Path, text: str) -> ast.Module | None:
    """Parse Python source, recording a syntax error as a blocking problem."""
    try:
        return ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        problems.append(f"Syntax error in {path.name} line {exc.lineno}: {exc.msg}")
        return None


def check_prompt_template(path: Path, tree: ast.Module) -> None:
    """Every *_PROMPT dict must carry all 8 prompt-template fields."""
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not any(n.endswith("_PROMPT") or "_PROMPT_" in n for n in names):
            continue
        keys = {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
        missing = [f for f in PROMPT_FIELDS if f not in keys]
        if missing:
            problems.append(
                f"{path.name}: {names[0]} is missing prompt-template fields {missing}. "
                "See the llm-prompt skill."
            )


def _dependency_names(func: ast.AsyncFunctionDef | ast.FunctionDef) -> set[str]:
    """Names passed to Depends(...) in a route's parameters."""
    found: set[str] = set()
    for default in [*func.args.defaults, *func.args.kw_defaults]:
        if (
            isinstance(default, ast.Call)
            and isinstance(default.func, ast.Name)
            and default.func.id == "Depends"
            and default.args
            and isinstance(default.args[0], ast.Name)
        ):
            found.add(default.args[0].id)
    return found


def check_route_auth(path: Path, tree: ast.Module) -> None:
    """List routes in a router file that have no auth dependency."""
    open_routes: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not (
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Attribute)
                and dec.func.attr in HTTP_METHODS
                and dec.args
                and isinstance(dec.args[0], ast.Constant)
            ):
                continue
            route = str(dec.args[0].value)
            if route in PUBLIC_ROUTES:
                continue
            if not (_dependency_names(node) & AUTH_DEPENDENCIES):
                open_routes.append(f"{dec.func.attr.upper()} {route} ({node.name}, line {node.lineno})")
    if open_routes:
        notes.append(
            f"{path.name} has routes with no auth dependency — check each one is meant to be "
            "public and that it can't return another user's data by ID: " + "; ".join(open_routes)
        )


def check_year_fallbacks(path: Path, text: str) -> None:
    """Flag `.get(tax_year, default)` lookups that silently use another year's figures."""
    hits = [
        str(n)
        for n, line in enumerate(text.splitlines(), start=1)
        if re.search(r"\.get\(\s*tax_year\s*,", line)
    ]
    if hits:
        notes.append(
            f"{path.name} lines {', '.join(hits)} fall back silently when a tax year is missing. "
            "A missing year should raise or be flagged, not use another year's figures "
            "(see the tax-year-update skill)."
        )


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = event.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not file_path:
        sys.exit(0)

    path = Path(file_path)
    if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
        sys.exit(0)

    text = path.read_text(encoding="utf-8", errors="replace")
    norm = str(path).replace("\\", "/")
    scan_secrets(path, text)

    if path.suffix == ".py":
        tree = parse_python(path, text)
        if tree is not None:
            if "/backend/prompts/" in norm:
                check_prompt_template(path, tree)
            if "/backend/routers/" in norm:
                check_route_auth(path, tree)
        if "/backend/rules/" in norm:
            check_year_fallbacks(path, text)

    if problems:
        print("post_edit_checks failed:\n- " + "\n- ".join(problems), file=sys.stderr)
        sys.exit(2)
    if notes:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "post_edit_checks: " + " ".join(notes),
            }
        }
        print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
