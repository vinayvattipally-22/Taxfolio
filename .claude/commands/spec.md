---
description: Turn a feature request into a reviewable spec with tax rules, edge cases and test cases — no code
argument-hint: <feature request>
allowed-tools: Read, Grep, Glob, Write
---

# /spec — Requirement → Spec

Turn the request into a spec a reviewer can approve **before any code is written**. Do not edit application code in this command.

Request: $ARGUMENTS

Follow these steps **in order**.

## Step 1: Find what already exists

- Backend: `backend/routers/` (thin HTTP layer), `backend/services/` (logic), `backend/rules/` (tax tables), `backend/prompts/` (LLM prompts), `backend/database/models.py`.
- Frontend: `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/services/api.js`.
- Tests: `backend/tests/`, `frontend/src/__tests__/`.
- List the files that will change.

## Step 2: Classify the change

Answer each, in the spec:
- **Who can call it?** Anonymous, any logged-in user (own data only), or advisor (`require_advisor`)?
- **Does it touch PII?** Anything from an uploaded document must go through `services/redaction_service.py` before storage or any external call.
- **Does it produce advice a customer sees?** Then it must go through the advisor review queue — no path that skips `review_status == "APPROVED"`.
- **Does it calculate money?** Then the number comes from deterministic code in `services/tax_engine.py` / `backend/rules/`, never from the LLM.
- **Which tax years and provinces?** Name them. Say what happens for a year or province with no data.

If any answer is unclear, list it under **Open questions** instead of guessing.

## Step 3: Write the spec

Write `docs/specs/<yyyy-mm-dd>-<short-slug>.md` with these sections:

1. **Goal** — one paragraph in the user's terms.
2. **Out of scope.**
3. **API contract** — method, path, auth dependency, request and response shape, status codes (400/401/403/404/409/422).
4. **Rules** — numbered, each testable. Tax rules cite the CRA source in `backend/knowledge_base/`.
5. **Acceptance criteria** — Given / When / Then.
6. **Edge cases** — always consider:
   - Money: rounding to the cent, bracket boundaries (exactly at a threshold, $1 above), zero and negative income, contribution limits hit exactly.
   - Years and provinces: a year not in `backend/rules/`, Quebec (separate provincial system), territories.
   - Documents: missing boxes, OCR misreads, two employers, duplicate upload of the same slip.
   - Requests: retries, double-submit, another user's `profile_id` (IDOR), expired token.
   - LLM: invalid JSON, prompt injection inside document text, timeouts.
7. **Test cases** — table: ID, layer (backend / frontend), type (happy / validation / auth / edge), input, expected result. Every rule and edge case maps to at least one test.
8. **Files to change.**
9. **Review boundary** — whether this needs senior line-level review (see CLAUDE.md), and why.
10. **Open questions.**

## Step 4: Hand back

Print the spec path and the open questions. Stop — implementation starts only after the user approves the spec.
