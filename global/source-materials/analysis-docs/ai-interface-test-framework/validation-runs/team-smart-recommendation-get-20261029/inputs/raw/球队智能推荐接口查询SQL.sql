-- ============================================================================
-- 北单游戏运营系统 - 球队智能推荐查询接口交叉验证 SQL（最终版）
--
-- 对应接口：
--   GET /data-backend/relations/team/recommendations
--
-- 用途：
--   根据接口入参 teamId、currentDataSource，独立计算接口应返回的候选 data 数组。
--   本 SQL 只执行查询，不创建、更新或删除任何业务数据。
--
-- 使用方式：
--   1. 修改 Request_Params CTE 中的 team_id、current_data_source；
--   2. 执行整段 SQL；
--   3. 查询结果列与接口 data 元素字段一一对应。
--
-- current_data_source：
--   1 = 目标源为纳米，反查贝泰作为 A 基准源（贝泰 -> 纳米）
--   2 = 同兴暂不参与智能推荐，本 SQL 返回空结果
--   3 = 目标源为贝泰，反查纳米作为 A 基准源（纳米 -> 贝泰）
--
-- 已确认的业务/数据前提：
--   1. 足球固定 sport_id = 1；
--   2. 源赛季表 season_id 唯一；
--   3. r_basic_data 中 source_type + source_season_id 只映射一个人工赛季；
--   4. r_basic_data 不存在历史脏关系；
--   5. source_competition_id 不参与本查询的赛季映射；
--   6. 不过滤 A/B 源比赛状态；
--   7. 不过滤目标球队删除状态；
--   8. 已匹配候选不排除，仍返回并标记为不可选；
--   9. 贝泰有效开赛时间始终为 COALESCE(resumetime, match_gtm8_time)；
--  10. 纳米 match_time 是 Unix 秒级时间戳；
--  11. 所有 A 源球队的比赛合并后全局取最近 10 场，不是每队各取 10 场；
--  12. 不为同开赛时间增加次级排序键，业务已排除同队同时间参加两场比赛。
--
-- 注意：
--   1. 为保证 FROM_UNIXTIME 按北京时间解释，查询会把当前数据库会话时区设为 +08:00；
--   2. 本 SQL 负责计算成功响应中的 data，不模拟 CommonResult 的参数错误 code/message；
--   3. team_id 不存在、没有 A 源关系、没有比赛、没有赛季映射或没有候选时均查询为空；
--   4. current_data_source=2 时查询为空，对应接口成功响应 data=[]。
-- ============================================================================

SET SESSION time_zone = '+08:00';

WITH
-- ----------------------------------------------------------------------------
-- 1. 接口入参：只需要修改这里
-- ----------------------------------------------------------------------------
Request_Params AS (
    SELECT
        CAST(36 AS SIGNED) AS team_id,
        CAST(1 AS SIGNED) AS current_data_source
),
-- ----------------------------------------------------------------------------
-- 2. 确定目标源 B 和反向基准源 A
--    current_data_source=2、非法值或 team_id 不存在时，不进入后续候选计算。
-- ----------------------------------------------------------------------------
Request_Context AS (
    SELECT
        p.team_id,
        p.current_data_source AS target_source_type,
        CASE p.current_data_source
            WHEN 1 THEN 3
            WHEN 3 THEN 1
        END AS base_source_type
    FROM Request_Params p
    INNER JOIN m_team mt
        ON mt.team_id = p.team_id
    WHERE p.current_data_source IN (1, 3)
),
-- ----------------------------------------------------------------------------
-- 3. 查询当前人工球队在 A 基准源中的全部历史源球队
-- ----------------------------------------------------------------------------
Base_Source_Teams AS (
    SELECT DISTINCT
        rt.source_team_id
    FROM r_team_data rt
    INNER JOIN Request_Context rc
        ON rc.team_id = rt.manual_team_id
       AND rc.base_source_type = rt.source_type
    WHERE rt.sport_id = 1
),
-- ----------------------------------------------------------------------------
-- 4. 汇总 A 源球队参加的全部比赛
--    a_role：1=主队，2=客队。
--    贝泰无论排序还是后续碰撞，都使用有效开赛时间 COALESCE。
--    EXISTS 可避免一场比赛的主客两队都位于历史球队集合时产生重复比赛行。
-- ----------------------------------------------------------------------------
A_Source_All_Matches AS (
    -- A 源为贝泰（current_data_source=1）
    SELECT
        bm.match_id,
        3 AS a_source_type,
        bm.season_id AS a_source_season_id,
        COALESCE(bm.resumetime, bm.match_gtm8_time) AS a_effective_match_time,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM Base_Source_Teams bst
                WHERE bst.source_team_id = bm.home_competitor_id
            ) THEN 1
            ELSE 2
        END AS a_role
    FROM beitai_football_match bm
    INNER JOIN Request_Context rc
        ON rc.base_source_type = 3
    WHERE EXISTS (
        SELECT 1
        FROM Base_Source_Teams bst
        WHERE bst.source_team_id = bm.home_competitor_id
           OR bst.source_team_id = bm.away_competitor_id
    )
    UNION ALL
    -- A 源为纳米（current_data_source=3）
    SELECT
        nm.match_id,
        1 AS a_source_type,
        nm.season_id AS a_source_season_id,
        FROM_UNIXTIME(nm.match_time) AS a_effective_match_time,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM Base_Source_Teams bst
                WHERE bst.source_team_id = nm.home_team_id
            ) THEN 1
            ELSE 2
        END AS a_role
    FROM nami_football_match nm
    INNER JOIN Request_Context rc
        ON rc.base_source_type = 1
    WHERE EXISTS (
        SELECT 1
        FROM Base_Source_Teams bst
        WHERE bst.source_team_id = nm.home_team_id
           OR bst.source_team_id = nm.away_team_id
    )
),
-- ----------------------------------------------------------------------------
-- 5. 所有 A 源球队比赛合并后，按有效开赛时间全局倒序取最近 10 场
--    按已确认需求，不增加 match_id 等同时间次级排序键。
-- ----------------------------------------------------------------------------
A_Source_Recent_10_Matches AS (
    SELECT
        match_id,
        a_source_type,
        a_source_season_id,
        a_effective_match_time,
        a_role
    FROM A_Source_All_Matches
    ORDER BY a_effective_match_time DESC
    LIMIT 10
),
-- ----------------------------------------------------------------------------
-- 6. 两段式赛季桥接
--    A(source_type + source_season_id + sport_id=1)
--      -> manual_season_id
--      -> B(source_type + manual_season_id + sport_id=1) 的 source_season_id 集合
--
--    不使用 source_competition_id。
--    DISTINCT 防止同一 A 比赛与同一 B 源赛季因重复等价映射被重复计分。
-- ----------------------------------------------------------------------------
Season_Bridge AS (
    SELECT DISTINCT
        a.match_id AS a_match_id,
        rc.target_source_type,
        a.a_effective_match_time,
        a.a_role,
        rd_b.source_season_id AS b_source_season_id
    FROM A_Source_Recent_10_Matches a
    INNER JOIN Request_Context rc
        ON 1 = 1
    INNER JOIN r_basic_data rd_a
        ON rd_a.source_type = a.a_source_type
       AND rd_a.sport_id = 1
       AND rd_a.source_season_id = a.a_source_season_id
    INNER JOIN r_basic_data rd_b
        ON rd_b.source_type = rc.target_source_type
       AND rd_b.sport_id = 1
       AND rd_b.manual_season_id = rd_a.manual_season_id
    WHERE rd_a.manual_season_id IS NOT NULL
      AND rd_b.source_season_id IS NOT NULL
),
-- ----------------------------------------------------------------------------
-- 7. 查询 B 目标源中同一秒、同一人工赛季的比赛，并按 A 的角色取 B 同侧球队
--    不过滤 B 源比赛状态，也不查询/过滤目标球队删除表。
-- ----------------------------------------------------------------------------
B_Source_Candidate_Hits AS (
    -- B 目标源为纳米
    SELECT
        sb.target_source_type,
        CASE sb.a_role
            WHEN 1 THEN nm.home_team_id
            WHEN 2 THEN nm.away_team_id
        END AS candidate_source_team_id
    FROM Season_Bridge sb
    INNER JOIN nami_football_match nm
        ON sb.target_source_type = 1
       AND nm.season_id = sb.b_source_season_id
       AND FROM_UNIXTIME(nm.match_time) = sb.a_effective_match_time
    UNION ALL
    -- B 目标源为贝泰
    SELECT
        sb.target_source_type,
        CASE sb.a_role
            WHEN 1 THEN bm.home_competitor_id
            WHEN 2 THEN bm.away_competitor_id
        END AS candidate_source_team_id
    FROM Season_Bridge sb
    INNER JOIN beitai_football_match bm
        ON sb.target_source_type = 3
       AND bm.season_id = sb.b_source_season_id
       AND COALESCE(bm.resumetime, bm.match_gtm8_time) = sb.a_effective_match_time
),
-- ----------------------------------------------------------------------------
-- 8. 候选球队计分：每命中一条 B 源比赛记录累加 1 次
-- ----------------------------------------------------------------------------
Candidate_Scores AS (
    SELECT
        target_source_type,
        candidate_source_team_id,
        COUNT(*) AS recommend_count
    FROM B_Source_Candidate_Hits
    GROUP BY
        target_source_type,
        candidate_source_team_id
),
-- ----------------------------------------------------------------------------
-- 9. 只保留并列最高分候选
-- ----------------------------------------------------------------------------
Highest_Score AS (
    SELECT MAX(recommend_count) AS max_recommend_count
    FROM Candidate_Scores
),
Top_Candidates AS (
    SELECT
        cs.target_source_type,
        cs.candidate_source_team_id,
        cs.recommend_count
    FROM Candidate_Scores cs
    INNER JOIN Highest_Score hs
        ON hs.max_recommend_count = cs.recommend_count
),
-- ----------------------------------------------------------------------------
-- 10. 目标源球队名称
--     纳米：全称/简称/英文名分别使用 name_zh/short_name_zh/name_en。
--     贝泰：全称和简称均使用 team_name；同一 team_id 可能有多赛事记录，先折叠。
-- ----------------------------------------------------------------------------
Beitai_Team_Info AS (
    SELECT
        team_id,
        MAX(team_name) AS team_name,
        MAX(team_name_en) AS team_name_en
    FROM beitai_football_team
    GROUP BY team_id
),
Target_Team_Info AS (
    SELECT
        1 AS source_type,
        nt.team_id AS source_team_id,
        nt.name_zh AS team_name_zh,
        nt.short_name_zh AS team_short_name_zh,
        nt.name_en AS team_name_en
    FROM nami_football_team nt
    UNION ALL
    SELECT
        3 AS source_type,
        bt.team_id AS source_team_id,
        bt.team_name AS team_name_zh,
        bt.team_name AS team_short_name_zh,
        bt.team_name_en AS team_name_en
    FROM Beitai_Team_Info bt
),
-- ----------------------------------------------------------------------------
-- 11. 查询候选当前匹配状态
--     正常业务数据中，一个 source_type + source_team_id 只对应一个人工球队。
--     按候选维度折叠可避免异常重复关系把同一候选扩成多行；若存在多个人工球队关系，
--     MIN 仅用于让交叉验证结果保持单行，仍应另行清理该业务脏数据。
-- ----------------------------------------------------------------------------
Candidate_Relations AS (
    SELECT
        rt.source_type,
        rt.source_team_id,
        MIN(rt.manual_team_id) AS manual_team_id
    FROM r_team_data rt
    INNER JOIN Top_Candidates tc
        ON tc.target_source_type = rt.source_type
       AND tc.candidate_source_team_id = rt.source_team_id
    WHERE rt.sport_id = 1
    GROUP BY
        rt.source_type,
        rt.source_team_id
)
-- ----------------------------------------------------------------------------
-- 12. 输出与接口 data 元素完全对应的字段
--     排序：中文简称正序；NULL/空简称最后；同简称按 sourceTeamId 升序。
-- ----------------------------------------------------------------------------
SELECT
    tc.target_source_type AS `sourceType`,
    tc.candidate_source_team_id AS `sourceTeamId`,
    ti.team_name_zh AS `teamNameZh`,
    ti.team_short_name_zh AS `teamShortNameZh`,
    ti.team_name_en AS `teamNameEn`,
    tc.recommend_count AS `recommendCount`,
    CASE
        WHEN cr.manual_team_id IS NULL THEN 0
        ELSE 1
    END AS `matchStatus`,
    CASE
        WHEN cr.manual_team_id IS NULL THEN 1
        ELSE 0
    END AS `checkStatus`,
    cr.manual_team_id AS `manualTeamId`
FROM Top_Candidates tc
LEFT JOIN Target_Team_Info ti
    ON ti.source_type = tc.target_source_type
   AND ti.source_team_id = tc.candidate_source_team_id
LEFT JOIN Candidate_Relations cr
    ON cr.source_type = tc.target_source_type
   AND cr.source_team_id = tc.candidate_source_team_id
ORDER BY
    CASE
        WHEN ti.team_short_name_zh IS NULL OR TRIM(ti.team_short_name_zh) = '' THEN 1
        ELSE 0
    END ASC,
    CASE
        WHEN ti.team_short_name_zh IS NULL OR TRIM(ti.team_short_name_zh) = '' THEN NULL
        ELSE CONVERT(ti.team_short_name_zh USING gbk)
    END ASC,
    tc.candidate_source_team_id ASC;
