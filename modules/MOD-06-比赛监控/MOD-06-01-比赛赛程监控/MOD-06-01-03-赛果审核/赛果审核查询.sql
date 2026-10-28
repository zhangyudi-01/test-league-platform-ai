-- 当前用户对每场比赛的最新一条赛果审核记录
SELECT
    x.*
FROM
    (
    SELECT
        emc.*,
        ROW_NUMBER() OVER (
            PARTITION BY emc.check_source_id
            ORDER BY emc.update_time DESC, emc.check_id DESC
        ) AS rn
    FROM
        event_match_check emc
    WHERE
        emc.create_account = 'zhangyudi' -- 当前登录用户
        AND emc.check_type = 2
    ) x
left join bd_batch_matchup bm ON x.check_source_id = CAST(bm.match_id AS CHAR)
WHERE
    x.rn = 1
and
    bm.batch_id IN (
	SELECT
		batch_id
	FROM
		bd_batch
	WHERE
		game_draw_id IN (SELECT game_draw_id FROM bd_game_draw WHERE draw_no = :draw_no)
		AND is_final_version = 1
		AND batch_sale_status = 1);

-- 查询同时存在足球、篮球、冰球、橄榄球的奖期
with select_sport as (
	SELECT
	    bm.game_draw_id,
	    GROUP_CONCAT(DISTINCT bm.sport_id ORDER BY bm.sport_id) AS sport_ids
	FROM
	    bd_batch_matchup bm
	WHERE
	    bm.sport_id IN (1, 13, 14, 2)
	GROUP BY
	    bm.game_draw_id
	HAVING
	    COUNT(DISTINCT bm.sport_id) = 4
	ORDER BY
	    bm.game_draw_id DESC)
SELECT bd.draw_no FROM bd_game_draw bd join select_sport ss on ss.game_draw_id = bd.game_draw_id ;


-- 查询足球运动项目纳米比分和比赛状态映射关系转换
-- 全场=home_scores[0]/away_scores[0]，半场=home_scores[1]/away_scores[1]（需求集成表）
SELECT
	CONCAT(JSON_UNQUOTE(JSON_EXTRACT(nm.home_scores, '$[1]')), ':',
	       JSON_UNQUOTE(JSON_EXTRACT(nm.away_scores, '$[1]')))       AS 半场比分,
	CONCAT(JSON_UNQUOTE(JSON_EXTRACT(nm.home_scores, '$[0]')), ':',
	       JSON_UNQUOTE(JSON_EXTRACT(nm.away_scores, '$[0]')))       AS 全场比分,
	CASE nm.status_id
		WHEN 0  THEN '待定'
		WHEN 1  THEN '未开赛'
		WHEN 2  THEN '比赛中'
		WHEN 3  THEN '比赛中'
		WHEN 4  THEN '比赛中'
		WHEN 5  THEN '比赛中'
		WHEN 7  THEN '比赛中'
		WHEN 8  THEN '完场'
		WHEN 9  THEN '推迟'
		WHEN 10 THEN '中断'
		WHEN 11 THEN '腰斩'
		WHEN 12 THEN '取消'
		WHEN 13 THEN '待定'
		ELSE '未知状态码'
	END                                                              AS 标准化比赛状态
FROM
	nami_football_match nm
WHERE
	nm.match_id = 4426646;


-- 查询冰球运动项目纳米比分和比赛状态映射关系转换
-- 全场=scores.ft（含105加时结束也仅取ft，不取ot，已确认）；冰球无半场比分
SELECT
	CONCAT(JSON_UNQUOTE(JSON_EXTRACT(nm.scores, '$.ft[0]')), ':',
	       JSON_UNQUOTE(JSON_EXTRACT(nm.scores, '$.ft[1]')))          AS 全场比分,
	CASE nm.status_id
		WHEN 0  THEN '待定'
		WHEN 1  THEN '未开赛'
		WHEN 30 THEN '比赛中'
		WHEN 31 THEN '比赛中'
		WHEN 32 THEN '比赛中'
		WHEN 331 THEN '比赛中'
		WHEN 332 THEN '比赛中'
		WHEN 6  THEN '比赛中'
		WHEN 10 THEN '比赛中'
		WHEN 8  THEN '比赛中'
		WHEN 13 THEN '比赛中'
		WHEN 100 THEN '完场'
		WHEN 105 THEN '完场'
		WHEN 110 THEN '完场'
		WHEN 14 THEN '推迟'
		WHEN 15 THEN '推迟'
		WHEN 17 THEN '中断'
		WHEN 19 THEN '腰斩'
		WHEN 16 THEN '取消'
		WHEN 99 THEN '待定'
		ELSE '未知状态码'
	END                                                              AS 标准化比赛状态
FROM
	nami_ice_hockey_match nm
WHERE
	nm.match_id = 5346900;


-- 查询橄榄球运动项目纳米比分和比赛状态映射关系转换
-- 全场=优先取scores.ot，为空时取scores.ft（已确认）；橄榄球无半场比分
SELECT
	CONCAT(
		COALESCE(JSON_UNQUOTE(JSON_EXTRACT(nm.scores, '$.ot[0]')),
		         JSON_UNQUOTE(JSON_EXTRACT(nm.scores, '$.ft[0]'))), ':',
		COALESCE(JSON_UNQUOTE(JSON_EXTRACT(nm.scores, '$.ot[1]')),
		         JSON_UNQUOTE(JSON_EXTRACT(nm.scores, '$.ft[1]'))))    AS 全场比分,
	CASE nm.status_id
		WHEN 0  THEN '待定'
		WHEN 1  THEN '未开赛'
		WHEN 44 THEN '比赛中'
		WHEN 45 THEN '比赛中'
		WHEN 46 THEN '比赛中'
		WHEN 47 THEN '比赛中'
		WHEN 331 THEN '比赛中'
		WHEN 332 THEN '比赛中'
		WHEN 333 THEN '比赛中'
		WHEN 6  THEN '比赛中'
		WHEN 10 THEN '比赛中'
		WHEN 100 THEN '完场'
		WHEN 105 THEN '完场'
		WHEN 14 THEN '推迟'
		WHEN 15 THEN '推迟'
		WHEN 17 THEN '中断'
		WHEN 19 THEN '腰斩'
		WHEN 16 THEN '取消'
		WHEN 99 THEN '待定'
		ELSE '未知状态码'
	END                                                              AS 标准化比赛状态
FROM
	nami_american_football_match nm
WHERE
	nm.match_id = 4791874;




















