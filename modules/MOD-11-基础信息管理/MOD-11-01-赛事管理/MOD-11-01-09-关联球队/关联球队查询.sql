-- ============================================================================
-- MOD-11-01-09 关联球队 · 第 13 轮冲刺（PBL-637：关联球队后名称回填规则优化）配套核验与造数 SQL
-- 适用环境：test2_newgoal (192.168.22.218:3306)
-- ============================================================================

-- 1. 查看数据中心球队表 m_team 各运动项目下北单全称/北单简称空值与非空分布
SELECT 
    sport_id,
    COUNT(*) AS total_teams,
    SUM(CASE WHEN (bd_team_name IS NULL OR bd_team_name = '') AND (bd_team_short_name IS NULL OR bd_team_short_name = '') THEN 1 ELSE 0 END) AS both_empty,
    SUM(CASE WHEN (bd_team_name IS NULL OR bd_team_name = '') AND (bd_team_short_name IS NOT NULL AND bd_team_short_name <> '') THEN 1 ELSE 0 END) AS only_full_empty,
    SUM(CASE WHEN (bd_team_name IS NOT NULL AND bd_team_name <> '') AND (bd_team_short_name IS NULL OR bd_team_short_name = '') THEN 1 ELSE 0 END) AS only_short_empty,
    SUM(CASE WHEN (bd_team_name IS NOT NULL AND bd_team_name <> '') AND (bd_team_short_name IS NOT NULL AND bd_team_short_name <> '') THEN 1 ELSE 0 END) AS both_filled
FROM m_team
GROUP BY sport_id;

-- 2. 查找可用于测试正向 4 字段回填的“北单全/简称双空”候选球队（足球 sport_id=1 / 篮球 sport_id=2）
-- 典型样本：team_id = 4148 ('Yongin City FC'), 4848 ('东部第七'), 6295 ('桑德维肯(1)'), 6472 ('奥尔堡(1)')
SELECT 
    team_id, sport_id, name_zh, short_name_zh, bd_team_name, bd_team_short_name, name_en,
    nami_id_match_status, beitai_id_match_status, create_account
FROM m_team
WHERE (bd_team_name IS NULL OR bd_team_name = '')
  AND (bd_team_short_name IS NULL OR bd_team_short_name = '')
  AND sport_id IN (1, 2)
ORDER BY team_id DESC
LIMIT 20;

-- 3. 查找实库中“球队全称(name_zh) != 北单全称(bd_team_name)”或“球队简称(short_name_zh) != 北单简称(bd_team_short_name)”的分离样本
-- 典型样本：
--   team_id = 7123 (sport_id=1)：name_zh='菲律宾(1)', short_name_zh='菲律宾(1)', bd_team_name='菲律宾亚运男足', bd_team_short_name='菲律宾亚运男足'
--   team_id = 3322 (sport_id=6)：name_zh='库德梅托娃/梅尔滕斯', short_name_zh='库德梅/梅尔滕斯', bd_team_name='库德梅托娃/梅尔滕斯', bd_team_short_name='库德梅托娃/梅尔'
-- 用途：用于精准验证用例 #9、#10、#11（分别撞击他队 name_zh、bd_team_name、short_name_zh、bd_team_short_name 时的静默跳过）
SELECT 
    team_id, sport_id, name_zh, short_name_zh, bd_team_name, bd_team_short_name
FROM m_team
WHERE bd_team_name IS NOT NULL AND bd_team_name <> ''
  AND (name_zh <> bd_team_name OR short_name_zh <> bd_team_short_name);

-- 4. 模拟条目 13.2 的当前运动项目下（不含当前球队）四字段唯一性预检 SQL
-- 使用时替换变量：@cur_sport_id, @cur_team_id, @input_bd_full_name, @input_bd_short_name
SET @cur_sport_id = 1;
SET @cur_team_id = 4148;
SET @input_bd_full_name = '菲律宾(1)';
SET @input_bd_short_name = '菲足测试';

SELECT 
    team_id,
    sport_id,
    name_zh,
    bd_team_name,
    short_name_zh,
    bd_team_short_name,
    CASE 
        WHEN name_zh = @input_bd_full_name THEN '冲突：与同运动项目其他球队的【球队全称(name_zh)】重名'
        WHEN bd_team_name = @input_bd_full_name THEN '冲突：与同运动项目其他球队的【北单全称(bd_team_name)】重名'
        WHEN short_name_zh = @input_bd_short_name THEN '冲突：与同运动项目其他球队的【球队简称(short_name_zh)】重名'
        WHEN bd_team_short_name = @input_bd_short_name THEN '冲突：与同运动项目其他球队的【北单简称(bd_team_short_name)】重名'
    END AS conflict_type
FROM m_team
WHERE sport_id = @cur_sport_id
  AND team_id <> @cur_team_id
  AND (
      name_zh = @input_bd_full_name 
      OR bd_team_name = @input_bd_full_name 
      OR short_name_zh = @input_bd_short_name 
      OR bd_team_short_name = @input_bd_short_name
  );

-- 5. 执行【关联】确认后的落库与四字段回填核验 SQL
-- 5.1 核验赛季球队关联表 r_season_team
SELECT 
    season_team_id, manual_competition_id, manual_season_id, manual_team_id, sport_id,
    season_bd_team_name, season_bd_team_short_name, naming_type, create_account, create_time, update_time
FROM r_season_team
ORDER BY season_team_id DESC
LIMIT 10;

-- 5.2 核验数据中心球队表 m_team 的 4 个名称字段（name_zh, bd_team_name, short_name_zh, bd_team_short_name）
SELECT 
    team_id, sport_id, name_zh, bd_team_name, short_name_zh, bd_team_short_name, update_account, update_time
FROM m_team
WHERE team_id IN (4148, 4848, 7123, 892);

-- 5.3 核验 Envers 审计表 audit_m_team 修订记录（验证回填触发时 revtype=1 的 4 字段同步快照）
SELECT 
    rev, revtype, team_id, sport_id, name_zh, bd_team_name, short_name_zh, bd_team_short_name, update_account, update_time
FROM audit_m_team
WHERE team_id = 4148
ORDER BY rev DESC
LIMIT 5;

-- 5.4 核验操作日志表 toto_operation_record（关联球队操作码 jcxxgl:ssgl:matchqd）
SELECT 
    record_id, operation_module, operation_type, operation_code, result, account_user, account, operation_time, error_detail
FROM toto_operation_record
WHERE operation_code = 'jcxxgl:ssgl:matchqd'
ORDER BY record_id DESC
LIMIT 10;
