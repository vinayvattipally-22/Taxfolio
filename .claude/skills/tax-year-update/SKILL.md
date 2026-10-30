---
name: tax-year-update
description: >
  How to add or correct a tax year's figures in TaxFolio — federal and provincial brackets, basic
  personal amounts, CPP/EI maximums, RRSP/TFSA/FHSA limits and benefit thresholds — across
  backend/rules/, the CRA knowledge base and tests, without silent fallbacks. Use when a new tax
  year starts, when CRA publishes indexed figures, or when a year/province returns wrong numbers.
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(python -m pytest:*)
---

# Adding or updating a tax year

Annual tax law change is the #2 "what breaks first at scale" risk in the original system plan. Every figure here feeds customer-facing dollar amounts, so this change always needs senior line-level review.

## 1. Source the figures first

- Use CRA's published figures for the year (indexation release, payroll tables, TFSA/RRSP/FHSA limits). Record the source URL and date for each number.
- Never take a figure from an LLM's memory. If a figure can't be sourced, stop and list it as an open question.

## 2. Know where every year-dependent figure lives

| File | What | Current coverage |
|---|---|---|
| `backend/rules/federal_brackets.py` | 5 federal brackets, `FEDERAL_BASIC_PERSONAL_AMOUNT` | 2024, 2025 |
| `backend/rules/provincial_brackets.py` | Brackets for 13 jurisdictions | **2024 only — `tax_year` is ignored** |
| `backend/rules/cpp_ei_rates.py` | YMPE, YAMPE, max CPP / CPP2 / EI | per-year dicts |
| `backend/rules/contribution_limits.py` | RRSP, TFSA (annual + cumulative), FHSA, HBP | 2024, 2025 |
| `backend/rules/benefit_rates.py` | OAS clawback and other benefit thresholds | per-year dicts |
| `backend/knowledge_base/*.md` | CRA documents the LightRAG graph is built from | e.g. `federal_tax_brackets.md`, `rrsp_rules.md` |

Search for any others before editing: `Grep "2025"` across `backend/rules/` and `backend/services/`.

## 3. No silent fallbacks

Today most lookups do `DICT.get(tax_year, <2024 value>)`, and `get_federal_brackets()` returns 2024 brackets for any year except 2025. A 2021 T4 or a 2026 return is therefore taxed with the wrong year's figures, and nothing tells the user or advisor.

When you touch a lookup:
- A year with no data must **raise** (e.g. `UnsupportedTaxYearError`) or return a result marked `estimated_from_year=<year>` that the analysis pipeline flags for advisor review. Agree which with the user in the spec — don't pick silently.
- An unknown province code must raise, not default to Ontario.
- Keep one explicit `SUPPORTED_TAX_YEARS` source of truth and check it in one place.

The post-edit hook lists any `.get(tax_year, ...)` fallbacks left in a rules file after each edit.

## 4. Update the knowledge base

- Update the matching `backend/knowledge_base/*.md` files so the LightRAG answers agree with the rules tables.
- Re-ingest only when asked (`POST /api/knowledge/ingest` costs OpenAI calls), and only commit regenerated `backend/lightrag_data/` deliberately.

## 5. Tests

In `backend/tests/test_tax_engine.py` (and `test_benefit_engine.py` where benefits change), add for the new year:
- Federal tax at each bracket threshold: exactly at the threshold and $1 above.
- One worked example per changed province, with the calculation in a comment and the CRA source.
- CPP, CPP2 and EI at and above the maximum.
- RRSP/TFSA/FHSA limits used by the simulator.
- An unsupported year and an unknown province → raise or flag, as agreed.

Expected values are computed by hand from the CRA figures, never copied from the code's own output.

Run `cd backend && python -m pytest -q`.

## 6. Hand back

- List every figure changed, with old value → new value and source.
- State the fallback behaviour chosen in step 3.
- Run `/review-diff` and flag the change for senior review.
