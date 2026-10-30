---
description: Line-by-line review of the current diff for tax correctness, PII safety, the advisor gate and auth
argument-hint: "[base branch | file paths]"
allowed-tools: Bash(git diff:*), Bash(git status:*), Bash(git log:*), Read, Grep, Glob
---

# /review-diff — Line-by-Line Review

Review a change before it is committed. Assume it was written by an AI agent and may pass its tests while still being wrong. Report findings; do not edit files.

Target: $ARGUMENTS

## Step 1: Get the diff

- No arguments → `git diff` plus `git diff --cached`.
- A branch → `git diff <branch>...HEAD`.
- File paths → review those files in full.

## Step 2: Mark the review boundary first

Put **"Needs senior line-level review"** at the top of the report if the diff touches any of these:
- `backend/services/redaction_service.py`, `backend/services/ocr_service.py`, `backend/routers/upload.py` — PII redaction and document intake
- `backend/routers/advisor.py`, `backend/services/advisor_service.py`, `backend/database/queries.py` (`approved_insights_query`) — the advisor approval gate
- `backend/services/tax_engine.py`, `backend/services/scenario_engine.py`, `backend/services/benefit_engine.py`, `backend/rules/` — tax and money calculations
- `backend/middleware/`, `backend/routers/auth.py`, `backend/services/auth_service.py` — authentication, roles, rate limits
- `backend/prompts/` — LLM prompts (scope and injection rules)
- `backend/services/audit_service.py` — the audit trail

## Step 3: Review every changed line

Cite `file:line` for every finding.

**Tax and money**
- Calculations are deterministic code, never LLM output. The LLM may explain a number, not produce it.
- Rounding happens once, at the end, to the cent; no rounding inside loops or before summing.
- Bracket boundaries use the right comparison (`<` vs `<=`) — check income exactly at a threshold.
- A missing tax year or province raises or is flagged; it must not silently use 2024 or Ontario figures.
- New figures match the CRA source in `backend/knowledge_base/`.

**PII**
- Document data passes through `redaction_service` before it is stored, logged or sent to OpenAI (text and vision).
- No SIN, name, address, DOB or raw document text in logs, error messages, audit `detail`, LLM prompts or test fixtures (synthetic values only).
- No new parameter that defaults to `redact_pii=False` on a path that reaches an external call.

**Advisor gate**
- Nothing a customer sees bypasses `review_status == "APPROVED"`. New insight types go through the review queue.

**Auth and data access**
- Every route has an auth dependency (`get_current_user`, `require_advisor`), unless it is deliberately public.
- Any lookup by `profile_id`, `document_id` or `case_id` checks the record belongs to the caller (or the caller is an advisor). An integer ID with no ownership check is an IDOR bug.
- Rate limits stay on expensive routes (analysis, chat, stock research).

**LLM calls**
- Prompts follow the 8-field template (the post-edit hook checks this) and keep the SCOPE and SECURITY rules.
- Output is parsed defensively: invalid JSON, missing fields and code fences handled; no `eval`.
- Document text is treated as data, never as instructions.

**Frontend**
- API calls go through `frontend/src/services/api.js`; no hard-coded URLs or tokens.
- Unapproved insights are never rendered as final; loading and error states exist.

**Tests**
- New behaviour has tests: happy path, validation, wrong user (IDOR), boundaries, missing year/province, mocked LLM failure.

## Step 4: Report

1. Review boundary line, if it applies.
2. Findings, most severe first — **Blocker / Should fix / Nit** — with `file:line`, what is wrong, and a concrete failing input (e.g. "income = 55,867 exactly → taxed at the wrong rate").
3. Missing tests, as test cases.
4. Verdict: **Ready**, **Ready after fixes**, or **Needs senior review**.
