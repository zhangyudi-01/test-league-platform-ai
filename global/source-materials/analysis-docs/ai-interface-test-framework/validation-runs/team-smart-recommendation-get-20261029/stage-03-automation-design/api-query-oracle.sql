-- Operation: GET /relations/team/recommendations (operationId: recommend)
-- Parameters: :team_id (m_team.team_id), :current_data_source (1 or 3)
-- Output: response data fields, one row per returned candidate; row order is unspecified.
-- Purpose: independent read-only oracle for the confirmed 13th-round rule.
-- Preconditions: MySQL 8+; execute against the test database; session time_zone must
-- match the API/database convention used for FROM_UNIXTIME (the verified baseline is +08:00).
-- No DML, DDL, session mutation, or fixed business IDs are used.
-- Time-window ties at a 5th/6th boundary are intentionally excluded from test data
-- because the confirmed requirement does not define a secondary selection key.
-- Validate response order separately against the confirmed Collator rule.

WITH
Request_Context AS (
    SELECT
        CAST(:team_id AS SIGNED) AS team_id,
        CAST(:current_data_source AS SIGNED) AS target_source_type,
        CASE CAST(:current_data_source AS SIGNED)
            WHEN 1 THEN 3
            WHEN 3 THEN 1
        END AS base_source_type
    FROM m_team mt
    WHERE mt.team_id = CAST(:team_id AS SIGNED)
      AND CAST(:current_data_source AS SIGNED) IN (1, 3)
),
Base_Source_Teams AS (
    SELECT DISTINCT rt.source_team_id
    FROM r_team_data rt
    JOIN Request_Context rc
      ON rc.team_id = rt.manual_team_id
     AND rc.base_source_type = rt.source_type
    WHERE rt.sport_id = 1
),
Eligible_A_Matches AS (
    SELECT
        bm.match_id,
        3 AS a_source_type,
        bm.season_id AS a_source_season_id,
        COALESCE(bm.resumetime, bm.match_gtm8_time) AS effective_time,
        CASE WHEN EXISTS (
            SELECT 1 FROM Base_Source_Teams bst
            WHERE bst.source_team_id = bm.home_competitor_id
        ) THEN 1 ELSE 2 END AS a_role
    FROM beitai_football_match bm
    JOIN Request_Context rc ON rc.base_source_type = 3
    JOIN r_basic_data rd
      ON rd.source_type = 3
     AND rd.sport_id = 1
     AND rd.source_season_id = bm.season_id
     AND rd.source_season_id IS NOT NULL
    WHERE EXISTS (
        SELECT 1 FROM Base_Source_Teams bst
        WHERE bst.source_team_id = bm.home_competitor_id
           OR bst.source_team_id = bm.away_competitor_id
    )

    UNION ALL

    SELECT
        nm.match_id,
        1 AS a_source_type,
        nm.season_id AS a_source_season_id,
        FROM_UNIXTIME(nm.match_time) AS effective_time,
        CASE WHEN EXISTS (
            SELECT 1 FROM Base_Source_Teams bst
            WHERE bst.source_team_id = nm.home_team_id
        ) THEN 1 ELSE 2 END AS a_role
    FROM nami_football_match nm
    JOIN Request_Context rc ON rc.base_source_type = 1
    JOIN r_basic_data rd
      ON rd.source_type = 1
     AND rd.sport_id = 1
     AND rd.source_season_id = nm.season_id
     AND rd.source_season_id IS NOT NULL
    WHERE EXISTS (
        SELECT 1 FROM Base_Source_Teams bst
        WHERE bst.source_team_id = nm.home_team_id
           OR bst.source_team_id = nm.away_team_id
    )
),
Past_Ranked AS (
    SELECT a.match_id, a.a_source_type, a.a_source_season_id,
           a.effective_time, a.a_role,
           ROW_NUMBER() OVER (ORDER BY effective_time DESC) AS window_rank
    FROM Eligible_A_Matches a
    WHERE effective_time <= NOW()
),
Future_Ranked AS (
    SELECT a.match_id, a.a_source_type, a.a_source_season_id,
           a.effective_time, a.a_role,
           ROW_NUMBER() OVER (ORDER BY effective_time ASC) AS window_rank
    FROM Eligible_A_Matches a
    WHERE effective_time > NOW()
),
Selected_A_Matches AS (
    SELECT match_id, a_source_type, a_source_season_id, effective_time, a_role
    FROM Past_Ranked
    WHERE window_rank <= 5
    UNION ALL
    SELECT match_id, a_source_type, a_source_season_id, effective_time, a_role
    FROM Future_Ranked
    WHERE window_rank <= 5
),
Season_Bridge AS (
    SELECT DISTINCT
        a.match_id AS a_match_id,
        rc.target_source_type,
        a.effective_time,
        a.a_role,
        rd_b.source_season_id AS b_source_season_id
    FROM Selected_A_Matches a
    JOIN Request_Context rc ON TRUE
    JOIN r_basic_data rd_a
      ON rd_a.source_type = a.a_source_type
     AND rd_a.sport_id = 1
     AND rd_a.source_season_id = a.a_source_season_id
     AND rd_a.source_season_id IS NOT NULL
    JOIN r_basic_data rd_b
      ON rd_b.source_type = rc.target_source_type
     AND rd_b.sport_id = 1
     AND rd_b.manual_season_id = rd_a.manual_season_id
     AND rd_b.source_season_id IS NOT NULL
    WHERE rd_a.manual_season_id IS NOT NULL
),
B_Candidate_Hits AS (
    SELECT sb.target_source_type,
           CASE sb.a_role WHEN 1 THEN nm.home_team_id ELSE nm.away_team_id END AS candidate_team_id
    FROM Season_Bridge sb
    JOIN nami_football_match nm
      ON sb.target_source_type = 1
     AND nm.season_id = sb.b_source_season_id
     AND FROM_UNIXTIME(nm.match_time) = sb.effective_time

    UNION ALL

    SELECT sb.target_source_type,
           CASE sb.a_role WHEN 1 THEN bm.home_competitor_id ELSE bm.away_competitor_id END AS candidate_team_id
    FROM Season_Bridge sb
    JOIN beitai_football_match bm
      ON sb.target_source_type = 3
     AND bm.season_id = sb.b_source_season_id
     AND COALESCE(bm.resumetime, bm.match_gtm8_time) = sb.effective_time
),
Candidate_Scores AS (
    SELECT target_source_type, candidate_team_id, COUNT(*) AS recommend_count
    FROM B_Candidate_Hits
    GROUP BY target_source_type, candidate_team_id
),
Top_Candidates AS (
    SELECT cs.target_source_type, cs.candidate_team_id, cs.recommend_count
    FROM Candidate_Scores cs
    WHERE cs.recommend_count = (SELECT MAX(recommend_count) FROM Candidate_Scores)
),
Beitai_Team_Info AS (
    SELECT team_id, MAX(team_name) AS team_name, MAX(team_name_en) AS team_name_en
    FROM beitai_football_team
    GROUP BY team_id
),
Target_Team_Info AS (
    SELECT 1 AS source_type, nt.team_id AS source_team_id,
           nt.name_zh AS team_name_zh,
           nt.short_name_zh AS team_short_name_zh,
           nt.name_en AS team_name_en
    FROM nami_football_team nt
    UNION ALL
    SELECT 3 AS source_type, bt.team_id,
           bt.team_name, bt.team_name, bt.team_name_en
    FROM Beitai_Team_Info bt
),
Candidate_Relations AS (
    SELECT rt.source_type, rt.source_team_id, MIN(rt.manual_team_id) AS manual_team_id
    FROM r_team_data rt
    JOIN Top_Candidates tc
      ON tc.target_source_type = rt.source_type
     AND tc.candidate_team_id = rt.source_team_id
    WHERE rt.sport_id = 1
    GROUP BY rt.source_type, rt.source_team_id
)
SELECT
    tc.target_source_type AS sourceType,
    tc.candidate_team_id AS sourceTeamId,
    ti.team_name_zh AS teamNameZh,
    ti.team_short_name_zh AS teamShortNameZh,
    ti.team_name_en AS teamNameEn,
    tc.recommend_count AS recommendCount,
    CASE WHEN cr.manual_team_id IS NULL THEN 0 ELSE 1 END AS matchStatus,
    CASE WHEN cr.manual_team_id IS NULL THEN 1 ELSE 0 END AS checkStatus,
    cr.manual_team_id AS manualTeamId
FROM Top_Candidates tc
LEFT JOIN Target_Team_Info ti
  ON ti.source_type = tc.target_source_type
 AND ti.source_team_id = tc.candidate_team_id
LEFT JOIN Candidate_Relations cr
  ON cr.source_type = tc.target_source_type
 AND cr.source_team_id = tc.candidate_team_id;
