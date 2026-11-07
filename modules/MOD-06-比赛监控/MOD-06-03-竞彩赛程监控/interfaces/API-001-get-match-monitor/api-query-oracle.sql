-- API-001 GET /sporttery/match-monitor：列表来源核对，SQL 状态 ready（尚未在数据库执行）。
-- MySQL 8.0+，只读；参数顺序：项目 JSON 数组、业务起始日、业务结束日。
-- 项目 JSON 例：[1,2]；测试层先按请求规则确定默认项目及上海业务日起止日，日期均为闭区间。
-- 仅适用于已确认的正常关联及同项目有效单跳替换，不为异常替换链定义预期。
-- 输出每个合格的竞彩源行及原始字段、计数、最新事件与直播字段；不保证返回顺序。
-- 测试层根据实施方案独立推导比分、排名、颜色、排序和响应结构；不得只按测试 ID 过滤全列表。
WITH request_params AS (
    SELECT CAST(%s AS JSON) AS sports, CAST(%s AS DATE) AS start_date,
           CAST(%s AS DATE) AS end_date
), selected_sports AS (
    SELECT DISTINCT j.sport_id
    FROM request_params p
    JOIN JSON_TABLE(p.sports, '$[*]' COLUMNS (sport_id INT PATH '$')) j ON TRUE
), source_matches AS (
    SELECT 1 AS sport_id, m.match_id, m.s_match_id, m.business_date, m.match_no,
           m.match_time, m.league_id, l.league_name,
           m.home_team_id, COALESCE(NULLIF(h.team_full_name, ''), h.team_name) AS home_name,
           m.away_team_id, COALESCE(NULLIF(a.team_full_name, ''), a.team_name) AS away_name,
           m.sell_status, m.if_change, m.half_score AS official_half,
           m.full_score AS official_full, NULL AS official_home, NULL AS official_away
    FROM sporttery_football_match m
    JOIN selected_sports sp ON sp.sport_id = 1
    CROSS JOIN request_params p
    LEFT JOIN sporttery_football_league l ON l.league_id = m.league_id
    LEFT JOIN sporttery_football_team h ON h.team_id = m.home_team_id
    LEFT JOIN sporttery_football_team a ON a.team_id = m.away_team_id
    WHERE m.business_date BETWEEN p.start_date AND p.end_date
    UNION ALL
    SELECT 2, m.match_id, m.s_match_id, m.business_date, m.match_no,
           m.match_time, m.league_id, l.league_name,
           m.home_team_id, COALESCE(NULLIF(h.team_full_name, ''), h.team_name),
           m.away_team_id, COALESCE(NULLIF(a.team_full_name, ''), a.team_name),
           m.sell_status, m.if_change, NULL, NULL, m.home_score, m.away_score
    FROM sporttery_basketball_match m
    JOIN selected_sports sp ON sp.sport_id = 2
    CROSS JOIN request_params p
    LEFT JOIN sporttery_basketball_league l ON l.league_id = m.league_id
    LEFT JOIN sporttery_basketball_team h ON h.team_id = m.home_team_id
    LEFT JOIN sporttery_basketball_team a ON a.team_id = m.away_team_id
    WHERE m.business_date BETWEEN p.start_date AND p.end_date
), event_stats AS (
    SELECT e.sport_id, e.source_id, COUNT(*) AS event_count
    FROM sporttery_match_event e
    JOIN source_matches m ON m.sport_id = e.sport_id AND m.match_id = e.source_id
    GROUP BY e.sport_id, e.source_id
), event_rank AS (
    SELECT e.sport_id, e.source_id, e.event_id, e.reason_title,
           ROW_NUMBER() OVER (PARTITION BY e.sport_id, e.source_id
                              ORDER BY e.update_time DESC, e.event_id DESC) AS rn
    FROM sporttery_match_event e
    JOIN source_matches m ON m.sport_id = e.sport_id AND m.match_id = e.source_id
), remark_stats AS (
    SELECT r.sport_id, r.match_id, COUNT(*) AS remark_count
    FROM sporttery_match_remark r
    JOIN source_matches m ON m.sport_id = r.sport_id AND m.match_id = r.match_id
    WHERE r.remark_type = 1
    GROUP BY r.sport_id, r.match_id
)
SELECT m.sport_id, m.match_id, m.business_date, m.match_no, m.match_time,
       m.league_id, m.league_name, m.home_team_id, m.home_name, m.away_team_id, m.away_name,
       m.sell_status, m.if_change, m.official_half, m.official_full,
       m.official_home, m.official_away,
       s.match_id AS effective_s_match_id, s.beitai_match_id, s.nami_match_id, s.tx_match_id,
       s.status_id, s.home_position, s.away_position,
       s.home_score_half, s.away_score_half, s.home_score, s.away_score,
       COALESCE(ec.event_count, 0) AS event_count, er.event_id AS latest_event_id,
       er.reason_title AS latest_reason_title, COALESCE(rc.remark_count, 0) AS remark_count,
       live.match_id AS live_match_id, live.status AS live_status,
       live.match_status AS live_match_status, live.match_clock, live.stoppage_clock
FROM source_matches m
LEFT JOIN s_match original ON original.match_id = m.s_match_id AND original.sport_id = m.sport_id
LEFT JOIN s_match s ON s.match_id = COALESCE(original.replace_id, original.match_id)
                   AND s.sport_id = m.sport_id
LEFT JOIN event_stats ec ON ec.sport_id = m.sport_id AND ec.source_id = m.match_id
LEFT JOIN event_rank er ON er.sport_id = m.sport_id AND er.source_id = m.match_id AND er.rn = 1
LEFT JOIN remark_stats rc ON rc.sport_id = m.sport_id AND rc.match_id = m.match_id
LEFT JOIN beitai_football_match_live live ON m.sport_id = 1 AND live.match_id = s.beitai_match_id;
