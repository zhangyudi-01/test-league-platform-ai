-- API-005 POST /data-backend/sporttery/match-monitor/remark.
-- Status: ready for review; static design only, not executed against a DB.
-- MySQL / PyMySQL named binding; run each labelled SELECT independently.
-- Read-only: statements are SELECT only, with no locks or data side effects.
-- Preconditions: identify the approved test database and verify deployed DDL,
-- session charset utf8mb4, read-only account, visibility after commit, and
-- ownership of all test data. Never use credentials or real accounts here.
-- Parameters:
--   match_id: official sporttery match ID, from the request or owned fixture;
--             not the standard s_match ID; pass one ID at a time.
--   sport_id: 1 football or 2 basketball, chosen from the request/fixture.
--   remark_id: actual ID of one run-owned remark, not an assumed max ID.
-- Q1/Q2 run before and after as needed; Q3 is optional read-only audit
-- observation for run-owned IDs, never a requirement that an audit row exist.
-- DATETIME is timezone-naive; avoid inferring timezone or update-time changes.
-- Bind values via DB_CONN.get_asdict(sql, params); do not interpolate values.

-- Q1: official match existence by domain, including the other sport. Zero,
-- one or two rows are possible. The same number can identify two different
-- domain records. Query each target or comparison ID separately. The result
-- is data evidence, not a rule requiring a standard-match association.
SELECT
    1 AS sport_id,
    f.match_id
FROM sporttery_football_match AS f
WHERE f.match_id = %(match_id)s
UNION ALL
SELECT
    2 AS sport_id,
    b.match_id
FROM sporttery_basketball_match AS b
WHERE b.match_id = %(match_id)s;

-- Q2: capture every account and every remark type for one domain/match,
-- BEFORE and AFTER the operation, including zero rows. Compare snapshots by
-- remark_id; independently identify the current user's type=1 row from the
-- authenticated test context and exact fixture keys, not response contents.
-- New: one new target row with expected saved text; update/repeat: same ID,
-- exactly one target row. Error: selected target/other rows unchanged as
-- required by each test point; other types/accounts and other test-owned
-- domain/match snapshots remain unchanged where specified. Query each affected
-- domain and match separately. Do not assume all non-target rows belong to the
-- test. remark is returned unchanged for exact Unicode sequence comparison;
-- do not use SQL character counts as a grapheme or UTF-16-length oracle.
-- Stable ordering is solely for comparing snapshots, not an API ordering rule.
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

-- Q3: OPTIONAL inventory of audit history for a known run-owned remark_id.
-- Read only, and do not delete audit rows or shared revision metadata on the
-- basis of this query. An audit row, its count or revtype is not asserted by
-- API-005; audit/log retention and cleanup must be approved separately.
SELECT
    a.remark_id,
    a.rev,
    a.revtype,
    a.sport_id,
    a.remark_type,
    a.match_id,
    a.remark,
    a.create_account,
    a.update_account,
    a.create_time,
    a.update_time
FROM audit_sporttery_match_remark AS a
WHERE a.remark_id = %(remark_id)s
ORDER BY a.rev ASC;
