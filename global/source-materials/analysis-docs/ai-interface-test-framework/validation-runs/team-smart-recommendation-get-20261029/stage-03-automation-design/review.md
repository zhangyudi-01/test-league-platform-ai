# Stage 3 Review: api-test-automation-design

## 2026-10-30 follow-up

The original review below incorrectly stated that the SQL contained no wildcard selection: it contained `a.*` and `cs.*`. These have been replaced with explicit columns. The plan now maps point 67 and blocks exact-time tests without a controlled service clock. A read-only literal probe showed that the database GBK collation and local Java Collator order `A/a` differently; the SQL now returns unordered candidate rows, while an independent ordering oracle remains blocked. The amended full SQL and plan remain unexecuted and await review.

## Result

**Status: PASS as an isolated design artifact; awaiting user review before implementation.**

## SQL oracle

- The oracle independently implements the confirmed eligibility-first, global past-five/future-five rule and then bridges seasons, matches same-second role candidates, counts hits, chooses all maxima, and emits the nine response fields.
- It uses named parameters and MySQL 8+ CTE/window-function syntax, performs only SELECT operations, has no DML/DDL/session mutation or SELECT *, and contains no old Top-10 selection.
- Manual/static inspection passed. It was not executed because the database version, DDL, timezone and schema are not available in this isolated run; those are explicit pre-execution checks, not claimed validation.

## Automation mapping

- All 66 final test points map to scenario data, a business generator family, assertions and cleanup. Mechanical coverage check found 66 points, 66 unique mappings, no missing points and no duplicate mapping.
- The plan follows the sample Excel-driven DataBff/generator workflow, distinguishes shared fixture data from per-case dynamic data, and specifies try/finally time restoration and exact reverse-order cleanup.
- The service-exception point is retained from the API contract but marked blocked unless isolated, recoverable fault injection is available.
- The referenced initialization Workbook is absent from the test repository, and table DDL/schema is not present in the inputs. This blocks safe fixture/SQL execution; the plan does not fabricate schema or authorize broad cleanup.
- The user-review gate remains: the plan is awaiting review and does not authorize implementation by itself.

## Isolation and verification

- No API call, database query/write, pytest, or Excel write was run.
- The target test submodule's initial Git status remains limited to .gitignore, apis/_data_bff.py, and settings.py; none were changed.
- All seven source files in input-hashes.json still match their initial SHA-256 values.
- All generated artifacts remain inside the validation run in test-league-platform-ai.

