-- API-002 GET /sporttery/match-monitor/live, SQL oracle: ready (static design).
-- MySQL 8; run statements separately with a read-only test-DB account.
-- This file is SELECT-only. It has NOT been executed against any database.
-- Parameters use PyMySQL positional %s; bind each statement independently.
-- P = request sportteryMatchId, S = the associated standard match id,
-- H = Beitai competitor id for Sporttery's home team, established from the
-- independent per-case team identity mapping, not from the response or
-- if_change alone. account = authenticated test user's configured account.
-- S and source ids come from statement 1 and are checked against fixture IDs.
-- Do not log account or credentials. No fixed IDs or wall-clock filters.
-- MySQL DATETIME values have no timezone: keep native values and compare
-- semantic date/time after the environment's serialization is verified.
-- No statement selects a latest/formal/audit winner, or modifies any row.

-- 1. Request association and raw team/direction facts. No row means P absent;
-- an existing row with standard_match_id NULL means unassociated. Additional
-- matchId validation is asserted directly against the request contract.
SELECT p.match_id AS sporttery_match_id, p.s_match_id AS standard_match_id,
       p.home_team_id AS sporttery_home_team_id,
       p.away_team_id AS sporttery_away_team_id, p.if_change,
       s.match_id AS found_standard_match_id, s.sport_id,
       s.home_team_id AS standard_home_team_id,
       s.away_team_id AS standard_away_team_id,
       s.nami_match_id, s.beitai_match_id,
       b.home_competitor_id AS beitai_home_team_id,
       b.away_competitor_id AS beitai_away_team_id
FROM sporttery_football_match AS p
LEFT JOIN s_match AS s ON s.match_id = p.s_match_id
LEFT JOIN beitai_football_match AS b ON b.match_id = s.beitai_match_id
WHERE p.match_id = %s;

-- 2. Nami source: one row maximum. No row, SQL NULL and [] are distinct
-- inputs but all map to [] in the response. Decode incidents as an ordered
-- JSON array, preserve NULL/missing element fields and map snake_case fields
-- to response fields. Source-home identity and Sporttery-home identity are
-- separately recorded in the controlled case: swap positions 1/2 and home/away scores
-- only when those identities differ; keep 0 and missing position unchanged.
SELECT n.match_id, n.incidents
FROM nami_football_match_live AS n
JOIN s_match AS s ON s.nami_match_id = n.match_id
WHERE s.match_id = %s;

-- 3. Beitai events. Bind [H, H, H, H, S]. Before comparing directional
-- fields, require H equals exactly one of the two distinct source team IDs;
-- otherwise the direction oracle is unavailable and the test must stop.
-- NULL team and unknown team are intentionally not assigned a position;
-- team=0 is neutral. No additional same-order tie breaker is contractual.
SELECT e.event_id AS eventId, e.match_id AS matchId, e.clock,
       e.order_id AS orderId, e.match_time AS matchTime,
       e.stoppage_time AS stoppageTime,
       e.stoppage_time_clock AS stoppageTimeClock,
       e.injury_time_announced AS injuryTimeAnnounced, e.period,
       e.event_type AS eventType, e.team, e.player_id1 AS playerId1,
       e.player_id2 AS playerId2, e.player_name1 AS playerName1,
       e.player_name2 AS playerName2, e.player_type1 AS playerType1,
       e.player_type2 AS playerType2, e.method, e.status,
       e.coord_x AS coordX, e.coord_y AS coordY, e.text,
       CASE WHEN %s = b.home_competitor_id THEN e.home_score
            ELSE e.away_score END AS homeScore,
       CASE WHEN %s = b.home_competitor_id THEN e.away_score
            ELSE e.home_score END AS awayScore,
       e.card_description AS cardDescription, e.event_time AS eventTime,
       e.create_time AS createTime, e.update_time AS updateTime,
       CASE WHEN e.team = 0 THEN 0
            WHEN e.team = b.home_competitor_id THEN
              CASE WHEN b.home_competitor_id = %s THEN 1 ELSE 2 END
            WHEN e.team = b.away_competitor_id THEN
              CASE WHEN b.away_competitor_id = %s THEN 1 ELSE 2 END
            ELSE NULL END AS position
FROM s_match AS s
JOIN beitai_football_match AS b ON b.match_id = s.beitai_match_id
JOIN beitai_football_event AS e ON e.match_id = b.match_id
WHERE s.match_id = %s
  AND e.event_type IN ('match_started', 'break_start', 'injury_time_shown',
                       'match_ended', 'red_card', 'yellow_card',
                       'yellow_red_card', 'substitution', 'score_change')
ORDER BY e.order_id IS NULL, e.order_id;
-- Correct binding order for statement 3: [H, H, H, H, S].

-- 4. Confirmation facts: return all rows, do not choose a row by recency.
-- For direction scenarios the fixture must ensure exactly one row for S.
SELECT m.batch_matchup_id, m.match_id, m.home_team_id, m.away_team_id,
       m.match_result_status, m.home_score, m.away_score,
       m.home_score_half, m.away_score_half, m.confirm_time
FROM bd_batch_matchup AS m
WHERE m.match_id = %s;

-- 5. Current-user audit facts; ensure at most one applicable record. The
-- account is a bound runtime parameter, never a literal in a saved asset.
SELECT c.check_id, c.check_source_id, c.check_type, c.check_status,
       c.check_result, c.bd_matchup_home_team_id, c.change_info
FROM event_match_check AS c
WHERE c.check_source_id = CAST(%s AS CHAR)
  AND c.check_type = 2 AND c.create_account = %s;

-- Test 47: snapshot statement 1 and raw Beitai event fields (including team,
-- home_score and away_score) before and after the request; compare by primary
-- keys, without masking NULL. Statement 3 is direction-adjusted, so it cannot
-- substitute for the raw-source comparison. The dedicated raw query is:
SELECT e.event_id, e.match_id, e.team, e.home_score, e.away_score
FROM beitai_football_event AS e
WHERE e.match_id = %s
ORDER BY e.event_id;
