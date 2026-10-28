-- 比赛进程信息-贝泰数据源-s-match/live 接口 beitaiLiveIncidents 验证 SQL
WITH latest_user_check AS (
    SELECT x.*
    FROM (
        SELECT
            emc.*,
            ROW_NUMBER() OVER (
                PARTITION BY emc.check_source_id
                ORDER BY emc.update_time DESC, emc.check_id DESC
            ) AS rn
        FROM event_match_check emc
        WHERE emc.create_account = 'zhangyudi'
          AND emc.check_type = 2
    ) x
    WHERE x.rn = 1
),
formal_matchup AS (
    SELECT x.*
    FROM (
        SELECT
            bm.*,
            ROW_NUMBER() OVER (
                PARTITION BY bm.match_id
                ORDER BY bm.update_time DESC, bm.batch_matchup_id DESC
            ) AS rn
        FROM bd_batch_matchup bm
        INNER JOIN bd_batch bb
                ON bb.batch_id = bm.batch_id
        WHERE bm.match_id = 64817
          AND bb.is_final_version = 1
          AND bb.batch_sale_status = 1
    ) x
    WHERE x.rn = 1
),
match_base AS (
    SELECT
        sm.match_id AS s_match_id,
        sm.beitai_match_id,
        sm.home_team_id AS sm_home_team_id,
        sm.away_team_id AS sm_away_team_id,
        bm.home_team_id AS bd_home_team_id,
        bm.away_team_id AS bd_away_team_id,
        bm.match_result_status,
        emc.check_id AS emc_check_id,
        emc.bd_matchup_home_team_id AS emc_bd_matchup_home_team_id,
        bfm.home_competitor_id AS beitai_home_team_id,
        bfm.away_competitor_id AS beitai_away_team_id,
        -- 接口最终展示主队：
        -- 1. 已确认：正式赛程主队
        -- 2. 已审核：审核记录中的北单主队
        -- 3. 未确认、未审核：s_match 主队
        CASE
            WHEN bm.match_result_status = 1 THEN bm.home_team_id
            WHEN emc.check_id IS NOT NULL
             AND emc.bd_matchup_home_team_id IS NOT NULL
            THEN emc.bd_matchup_home_team_id
            ELSE sm.home_team_id
        END AS display_home_team_id,
        -- 接口最终展示客队：
        -- 已确认直接取正式赛程客队；
        -- 已审核时，根据审核记录中的北单主队，从正式赛程中取另一方；
        -- 否则取 s_match 客队。
        CASE
            WHEN bm.match_result_status = 1 THEN bm.away_team_id
            WHEN emc.check_id IS NOT NULL
             AND emc.bd_matchup_home_team_id = bm.home_team_id
            THEN bm.away_team_id
            WHEN emc.check_id IS NOT NULL
             AND emc.bd_matchup_home_team_id = bm.away_team_id
            THEN bm.home_team_id
            ELSE sm.away_team_id
        END AS display_away_team_id
    FROM s_match sm
    INNER JOIN beitai_football_match bfm
            ON bfm.match_id = sm.beitai_match_id
    LEFT JOIN formal_matchup bm
           ON bm.match_id = sm.match_id
    LEFT JOIN latest_user_check emc
           ON emc.check_source_id = CAST(sm.match_id AS CHAR)
    WHERE sm.match_id = 64817
),
match_direction AS (
    SELECT
        mb.*,
        -- 是否需要按接口展示方向翻转贝泰事件：
        -- 因为 beitai_football_match 与 s_match 主客顺序一致，
        -- 所以只要接口展示主队 = s_match 客队，就说明相对贝泰源顺序发生翻转。
        CASE
            WHEN mb.display_home_team_id = mb.sm_away_team_id THEN 1
            ELSE 0
        END AS is_team_swapped
    FROM match_base mb
)
SELECT
    e.create_time AS createTime,
    e.update_time AS updateTime,
    e.event_id AS eventId,
    e.match_id AS matchId,
    e.clock,
    e.order_id AS orderId,
    e.match_time AS matchTime,
    e.stoppage_time AS stoppageTime,
    e.stoppage_time_clock AS stoppageTimeClock,
    e.injury_time_announced AS injuryTimeAnnounced,
    e.period,
    e.event_type AS eventType,
    e.team,
    e.player_id1 AS playerId1,
    e.player_id2 AS playerId2,
    e.player_name1 AS playerName1,
    e.player_name2 AS playerName2,
    e.player_type1 AS playerType1,
    e.player_type2 AS playerType2,
    e.method,
    e.status,
    e.coord_x AS coordX,
    e.coord_y AS coordY,
    e.text,
    -- 主客队互换时，接口展示比分也要互换
    CASE
        WHEN mb.is_team_swapped = 1 THEN e.away_score
        ELSE e.home_score
    END AS homeScore,
    CASE
        WHEN mb.is_team_swapped = 1 THEN e.home_score
        ELSE e.away_score
    END AS awayScore,
    e.card_description AS cardDescription,
    e.event_time AS eventTime,
    -- position：0-中立、1-主队、2-客队
    CASE
        WHEN e.team IS NULL OR e.team = 0 THEN 0
        -- 贝泰原主队事件
        WHEN e.team = mb.beitai_home_team_id THEN
            CASE
                WHEN mb.is_team_swapped = 1 THEN 2
                ELSE 1
            END
        -- 贝泰原客队事件
        WHEN e.team = mb.beitai_away_team_id THEN
            CASE
                WHEN mb.is_team_swapped = 1 THEN 1
                ELSE 2
            END
        -- 异常 team，既不是主队也不是客队，按中立兜底
        ELSE 0
    END AS position
FROM beitai_football_event e
INNER JOIN match_direction mb
        ON e.match_id = mb.beitai_match_id
WHERE e.event_type IN (
    'match_started',
    'break_start',
    'injury_time_shown',
    'match_ended',
    'red_card',
    'yellow_card',
    'yellow_red_card',
    'substitution',
    'score_change'
)
ORDER BY e.order_id ASC;

-- 比赛进程信息-贝泰数据源-s-match/live 接口 liveIncidents 验证 SQL
-- 数据源：nami_football_match_live.incidents
-- 参数1：@s_match_id 为接口入参 matchId，即 s_match.match_id
-- 参数2：@account 为当前登录账号，审核记录按账号取最新一条
SET @s_match_id = 56178;
SET @account = 'yudi';
WITH latest_user_check AS (
    SELECT x.*
    FROM (
        SELECT
            emc.*,
            ROW_NUMBER() OVER (
                PARTITION BY emc.check_source_id
                ORDER BY emc.update_time DESC, emc.check_id DESC
            ) AS rn
        FROM event_match_check emc
        WHERE emc.create_account = @account
          AND emc.check_type = 2
    ) x
    WHERE x.rn = 1
),
formal_matchup AS (
    SELECT x.*
    FROM (
        SELECT
            bm.*,
            ROW_NUMBER() OVER (
                PARTITION BY bm.match_id
                ORDER BY bm.update_time DESC, bm.batch_matchup_id DESC
            ) AS rn
        FROM bd_batch_matchup bm
        INNER JOIN bd_batch bb
                ON bb.batch_id = bm.batch_id
        WHERE bm.match_id = @s_match_id
          AND bb.is_final_version = 1
          AND bb.batch_sale_status = 1
    ) x
    WHERE x.rn = 1
),
match_base AS (
    SELECT
        sm.match_id AS s_match_id,
        sm.nami_match_id,
        sm.home_team_id AS sm_home_team_id,
        sm.away_team_id AS sm_away_team_id,
        bm.home_team_id AS bd_home_team_id,
        bm.away_team_id AS bd_away_team_id,
        bm.match_result_status,
        emc.check_id AS emc_check_id,
        emc.bd_matchup_home_team_id AS emc_bd_matchup_home_team_id,
        -- 接口最终展示主队：
        -- 1. 已确认：正式赛程主队
        -- 2. 已审核：审核记录中的北单主队
        -- 3. 未确认、未审核：s_match 主队
        CASE
            WHEN bm.match_result_status = 1 THEN bm.home_team_id
            WHEN emc.check_id IS NOT NULL
             AND emc.bd_matchup_home_team_id IS NOT NULL
            THEN emc.bd_matchup_home_team_id
            ELSE sm.home_team_id
        END AS display_home_team_id,
        -- 接口最终展示客队
        CASE
            WHEN bm.match_result_status = 1 THEN bm.away_team_id
            WHEN emc.check_id IS NOT NULL
             AND emc.bd_matchup_home_team_id = bm.home_team_id
            THEN bm.away_team_id
            WHEN emc.check_id IS NOT NULL
             AND emc.bd_matchup_home_team_id = bm.away_team_id
            THEN bm.home_team_id
            ELSE sm.away_team_id
        END AS display_away_team_id
    FROM s_match sm
    LEFT JOIN formal_matchup bm
           ON bm.match_id = sm.match_id
    LEFT JOIN latest_user_check emc
           ON emc.check_source_id = CAST(sm.match_id AS CHAR)
    WHERE sm.match_id = @s_match_id
),
match_direction AS (
    SELECT
        mb.*,
        -- nami_football_match_live.incidents.position 的 1/2 默认按源数据主客队方向；
        -- s_match 与纳米源数据主客顺序一致，因此展示主队 = s_match 客队时，需要翻转。
        CASE
            WHEN mb.display_home_team_id = mb.sm_away_team_id THEN 1
            ELSE 0
        END AS is_team_swapped
    FROM match_base mb
),
incident_detail AS (
    SELECT
        mb.is_team_swapped,
        jt.ord,
        jt.incident_time,
        jt.incident_type,
        jt.incident_second,
        jt.source_position,
        jt.player_name,
        jt.home_score,
        jt.away_score,
        jt.in_player_name,
        jt.out_player_name
    FROM match_direction mb
    INNER JOIN nami_football_match_live nfl
            ON nfl.match_id = mb.nami_match_id
    INNER JOIN JSON_TABLE(
        nfl.incidents,
        '$[*]' COLUMNS (
            ord FOR ORDINALITY,
            incident_time INT PATH '$.time' NULL ON EMPTY,
            incident_type INT PATH '$.type' NULL ON EMPTY,
            incident_second INT PATH '$.second' NULL ON EMPTY,
            source_position INT PATH '$.position' NULL ON EMPTY,
            player_name VARCHAR(255) PATH '$.player_name' NULL ON EMPTY,
            home_score INT PATH '$.home_score' NULL ON EMPTY,
            away_score INT PATH '$.away_score' NULL ON EMPTY,
            in_player_name VARCHAR(255) PATH '$.in_player_name' NULL ON EMPTY,
            out_player_name VARCHAR(255) PATH '$.out_player_name' NULL ON EMPTY
        )
    ) jt
)
SELECT
    i.incident_time AS time,
    i.incident_type AS type,
    i.incident_second AS second,
    -- position：0-中立、1-主队、2-客队
    CASE
        WHEN i.source_position IS NULL OR i.source_position = 0 THEN 0
        WHEN i.source_position = 1 THEN
            CASE
                WHEN i.is_team_swapped = 1 THEN 2
                ELSE 1
            END
        WHEN i.source_position = 2 THEN
            CASE
                WHEN i.is_team_swapped = 1 THEN 1
                ELSE 2
            END
        ELSE 0
    END AS position,
    i.player_name AS playerName,
    -- 主客队互换时，接口展示比分也要互换
    CASE
        WHEN i.is_team_swapped = 1 THEN i.away_score
        ELSE i.home_score
    END AS homeScore,
    CASE
        WHEN i.is_team_swapped = 1 THEN i.home_score
        ELSE i.away_score
    END AS awayScore,
    i.in_player_name AS inPlayerName,
    i.out_player_name AS outPlayerName
FROM incident_detail i
ORDER BY i.ord ASC;
