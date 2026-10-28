-- ==============================================================================
-- MOD-05-07 草稿管理列表页 配套数据核验与造数查询 SQL
-- 重点针对：PBL-618 快速关联球队--匹配纳米数据源（13轮冲刺 ✅ 需求）
-- 数据库：test2_newgoal (MySQL 8.0)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. 查询当前可用的草稿批次
-- ------------------------------------------------------------------------------
SELECT 
    b.batch_id,
    b.game_draw_id,
    d.draw_no,
    b.batch_no,
    b.status                  AS batch_status,
    b.is_lock                 AS is_lock,
    COUNT(m.matchup_draft_id) AS draft_match_count
FROM bd_batch b
LEFT JOIN bd_game_draw d ON b.game_draw_id = d.game_draw_id
LEFT JOIN bd_batch_matchup_draft m ON b.batch_id = m.batch_id
WHERE b.is_final_version = 0
GROUP BY b.batch_id, b.game_draw_id, d.draw_no, b.batch_no, b.status, b.is_lock
ORDER BY b.batch_id DESC
LIMIT 10;


-- ------------------------------------------------------------------------------
-- 2. 查找可添加进草稿、且主客队在当前赛季下未关联（r_season_team 无记录）的比赛样本
--    （添加进草稿后，球队名称旁展示未关联标识，点击可弹出快速关联球队弹窗）
-- ------------------------------------------------------------------------------
SELECT 
    s.match_id,
    s.sport_id,
    s.competition_id,
    s.season_id,
    s.home_team_id,
    ht.name_zh               AS home_name,
    ht.short_name_zh         AS home_short,
    ht.nami_id_match_status  AS home_nami_status,   -- 0=未匹配纳米(展示按钮), 1=已匹配纳米(隐藏按钮)
    rst_h.season_team_id     AS home_season_rel_id, -- NULL=未关联当前赛季
    s.away_team_id,
    at.name_zh               AS away_name,
    at.short_name_zh         AS away_short,
    at.nami_id_match_status  AS away_nami_status,
    rst_a.season_team_id     AS away_season_rel_id
FROM s_match s
INNER JOIN m_team ht ON s.home_team_id = ht.team_id
INNER JOIN m_team at ON s.away_team_id = at.team_id
LEFT JOIN r_season_team rst_h 
    ON s.season_id = rst_h.manual_season_id AND s.home_team_id = rst_h.manual_team_id
LEFT JOIN r_season_team rst_a 
    ON s.season_id = rst_a.manual_season_id AND s.away_team_id = rst_a.manual_team_id
WHERE s.season_id IS NOT NULL
  AND (rst_h.season_team_id IS NULL OR rst_a.season_team_id IS NULL)
ORDER BY s.match_id DESC
LIMIT 20;
-- 实库典型样本：
-- ① s_match.match_id = 116314 (season_id=402)：主队 6798 '克拉德诺'(nami=0 展示按钮)，客队 1309 '俄斯特拉发'(nami=1 隐藏按钮)
-- ② s_match.match_id = 116283 (season_id=359)：主队 716 '乌里扬诺夫斯克'(nami=1 隐藏按钮)，客队 7149 'FC Murom'(nami=0 展示按钮，且为纯英文简称)
-- ③ s_match.match_id = 116316 (season_id=418)：主队 7328 '汉威尔镇'(nami=0)，客队 7317 '布格斯'(nami=0)


-- ------------------------------------------------------------------------------
-- 3. 未匹配纳米且简称含纯英文、空格或特殊字符的球队样本（对应测试点 #7）
-- ------------------------------------------------------------------------------
SELECT 
    t.team_id,
    t.sport_id,
    t.name_zh,
    t.short_name_zh,
    t.bd_team_name,
    t.bd_team_short_name,
    t.nami_id_match_status,
    t.beitai_id_match_status
FROM m_team t
WHERE t.nami_id_match_status = 0
  AND t.short_name_zh REGEXP '[A-Za-z0-9.()/-]'
ORDER BY t.team_id DESC
LIMIT 15;
-- 实库典型样本：
-- 纯英文含空格：7149 ('FC Murom'), 5989 ('FC Levy Bereg Ki'), 7515 ('Gaziemir Gog Sy')
-- 含特殊字符 '/'：7512 ('拉姆/索尔兹伯里'), 7478 ('蒋欣玗/张帅')


-- ------------------------------------------------------------------------------
-- 4. 核验单支球队的纳米匹配状态与匹配关系明细（r_team_data）
-- ------------------------------------------------------------------------------
SELECT 
    t.team_id,
    t.name_zh,
    t.short_name_zh,
    t.nami_id_match_status,
    t.beitai_id_match_status,
    r.relation_id,
    r.source_type,     -- 1=纳米, 3=贝泰
    r.source_team_id,
    r.update_time
FROM m_team t
LEFT JOIN r_team_data r ON t.team_id = r.manual_team_id
WHERE t.team_id IN (6798, 1309, 7149, 7328);


-- ------------------------------------------------------------------------------
-- 5. 核验快速关联弹窗点击【确定】后的落库结果（r_season_team 与 m_team 回填）
-- ------------------------------------------------------------------------------
SELECT 
    rst.season_team_id,
    rst.manual_competition_id,
    rst.manual_season_id,
    rst.manual_team_id,
    rst.season_bd_team_name,
    rst.season_bd_team_short_name,
    rst.naming_type,
    t.name_zh            AS m_team_name_zh,
    t.short_name_zh      AS m_team_short_name_zh,
    t.bd_team_name       AS m_team_bd_name,
    t.bd_team_short_name AS m_team_bd_short_name
FROM r_season_team rst
INNER JOIN m_team t ON rst.manual_team_id = t.team_id
WHERE rst.manual_team_id = 7328
ORDER BY rst.season_team_id DESC;
