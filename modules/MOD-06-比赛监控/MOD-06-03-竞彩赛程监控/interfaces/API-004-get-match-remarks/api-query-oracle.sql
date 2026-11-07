-- API-004 GET /sporttery/match-monitor/remarks: independent read-only oracle.
-- Status: user reviewed; not executed against any database.
-- Target: MySQL-compatible schema verified against the 2026-10-26 DDL snapshot.
-- Bind with PyMySQL named parameters, executing each labelled SELECT separately:
--   sport_id: request sport ID (1 football or 2 basketball).
--   match_id: request official match ID, not s_match ID.
-- Obtain both from the request or run-owned fixture; never persist credentials.
-- All statements are SELECT only; they have no intended data side effects.
-- DATETIME has no timezone; compare returned calendar components at seconds
-- precision. Do not infer any offset or conversion from the database session.
-- Current schema marks remark_id, sport_id, match_id, remark_type, remark,
-- create_account, create_time and update_time NOT NULL. Verify deployed DDL.

-- Q1: independently establish whether the official match exists in the
-- specified sport and whether a standard-match association exists. One row
-- means present; zero rows means absent. Neither sport is inferred from ID.
-- The DDL snapshot has no deletion flag; row absence is not proof of a
-- separate soft-delete status. Verify environment-specific semantics first.
SELECT
    1 AS sport_id,
    f.match_id,
    f.s_match_id
FROM sporttery_football_match AS f
WHERE %(sport_id)s = 1
  AND f.match_id = %(match_id)s
UNION ALL
SELECT
    2 AS sport_id,
    b.match_id,
    b.s_match_id
FROM sporttery_basketball_match AS b
WHERE %(sport_id)s = 2
  AND b.match_id = %(match_id)s;

-- Q2: retrieve the raw candidate records, not the implementation's sorted
-- DTO query. For an existing match derive the expected result independently:
-- use exact account identity from the authenticated test context; put the
-- current user's record first, sort other records by update_time then
-- remark_id ascending, and map fields in the test layer. No DISTINCT,
-- pagination, extra account filter, or artificial empty row is applied.
-- Zero rows for an existing match implies []; Q1 absent means expected error,
-- even when Q2 is empty or contains an orphan. SQL does not prove HTTP/auth.
SELECT
    r.remark_id,
    r.sport_id,
    r.match_id,
    r.remark,
    r.create_account,
    r.create_time,
    r.update_time
FROM sporttery_match_remark AS r
WHERE r.sport_id = %(sport_id)s
  AND r.match_id = %(match_id)s
  AND r.remark_type = 1;

-- Q3: before/after read-only snapshot of ALL remark types for the selected
-- sport and match, to detect inserts, removals and changes (test point 25).
-- Use the same parameters and compare all columns by remark_id, including
-- update_account and remark_type. Stable snapshot ordering is only for
-- comparison; it is not the endpoint's ordering rule.
SELECT
    r.remark_id,
    r.sport_id,
    r.remark_type,
    r.match_id,
    r.remark,
    r.create_account,
    r.update_account,
    r.create_time,
    r.update_time
FROM sporttery_match_remark AS r
WHERE r.sport_id = %(sport_id)s
  AND r.match_id = %(match_id)s
ORDER BY r.remark_id ASC;
