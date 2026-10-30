---
description: Check, stage specific files and commit with a conventional message on a feature branch
argument-hint: "[optional summary hint]"
allowed-tools: Bash(python -m pytest:*), Bash(npx vitest run:*), Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git branch:*)
---

# /commit — Checked Commit

Hint: $ARGUMENTS

## Step 1: Branch check

`git branch --show-current`. If on `main`, stop and ask for a feature branch name.

## Step 2: Tests

Run the tests for the stacks that changed:
- Backend changed → `cd backend && python -m pytest -q`
- Frontend changed → `cd frontend && npx vitest run`

If anything fails, stop and report. Do not commit a red build.

## Step 3: Stage

- Show `git status`.
- Stage **specific files** by path. Never `git add -A` or `git add .`.
- Never stage `.env`, `*.db`, `backend/uploads/`, `sample_docs/`, `test_data/`, `scripts/`, or anything in `.gitignore`.
- Re-generated `backend/lightrag_data/` files are only committed if the change was a deliberate knowledge-base re-ingest — ask first.
- Show `git diff --cached --stat`.

## Step 4: Message

Format: `<type>(<scope>): <summary>` — imperative, at most 72 characters, no trailing period.
Types: `feat`, `fix`, `refactor`, `style`, `test`, `ci`, `docs`, `chore`.
Scopes: `tax-engine`, `rules`, `ocr`, `redaction`, `advisor`, `analysis`, `simulator`, `stocks`, `chat`, `auth`, `frontend`, `rag`, `claude`.

Rules:
- **No `Co-Authored-By` trailers.**
- Never `--no-verify`.
- Never amend a pushed commit — make a new one.

## Step 5: Commit

Show the message and run `git commit`. Do not push.
