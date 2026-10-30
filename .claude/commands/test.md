---
description: Run backend (pytest) and/or frontend (Vitest) tests, then diagnose failures to root cause
argument-hint: "[backend | frontend | path | -k expression]"
allowed-tools: Bash(python -m pytest:*), Bash(npx vitest run:*), Read, Grep, Glob
---

# /test — Run and Diagnose Tests

Arguments: $ARGUMENTS

## Step 1: Run

| Argument | Command |
|---|---|
| none | both rows below |
| `backend`, a `backend/tests/...` path, or `-k ...` | `cd backend && python -m pytest -q --tb=short [path or -k]` |
| `frontend` or a `frontend/src/...` path | `cd frontend && npx vitest run [path]` |

Backend tests use in-memory async SQLite and the `mock_openai` fixture in `backend/tests/conftest.py` — no API key, server or network needed. Frontend tests use Vitest + Testing Library (`frontend/src/__tests__/`).

If pytest or node_modules are missing, stop and give the install command (`pip install -r backend/requirements.txt`, `npm install` in `frontend/`). Do not install packages yourself.

Never run the manual scripts in `docs/dev/scripts/` here: they read real sample documents and make paid OpenAI calls.

## Step 2: Report

One line per stack: passed / failed / skipped / errors.

## Step 3: Diagnose each failure

1. Read the test and the code under test.
2. State the root cause with `file:line`.
3. Decide whether the **code** or the **test** is wrong, and why.

Rules:
- Never weaken an assertion, change an expected dollar amount, or add `skip`/`xfail` to get a pass. Expected tax figures come from CRA tables — if one looks wrong, show the calculation and ask.
- A test that passed only because a rule silently fell back to another tax year or to Ontario is a real bug. Report it.
- If a test would need a real OpenAI call, it is wrong: use `mock_openai`.

## Step 4: Propose fixes

List the fixes. Apply them only if the user asked, then re-run the failing tests, then the full suite for that stack.
