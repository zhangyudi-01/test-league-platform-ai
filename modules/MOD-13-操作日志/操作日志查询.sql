-- ==============================================================================
-- MOD-13 操作日志 配套数据核验与查询 SQL
-- 重点针对：PBL-639 第13轮操作日志新增 4 类操作记录与查询核验
-- 数据库：test2_newgoal (MySQL 8.0)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. 查询第13轮新增的 4 类操作日志记录（成功/失败落库核验）
-- ------------------------------------------------------------------------------
SELECT
    record_id,
    operation_module,
    operation_type,
    operation_code,
    result,
    account_user,
    account,
    operation_role_id,
    operation_role_name,
    operation_time,
    error_detail
FROM toto_operation_record
WHERE operation_type IN ('竞彩赛事匹配', '竞彩球队匹配', '竞彩赛程备注', '修改详情')
ORDER BY operation_time DESC, record_id DESC
LIMIT 50;


-- ------------------------------------------------------------------------------
-- 2. 按模块+操作类型分别核验新增日志（对应测试点 #1~#11、#14）
-- ------------------------------------------------------------------------------
-- 2.1 基础信息管理 - 竞彩赛事匹配
SELECT * FROM toto_operation_record
WHERE operation_module = '基础信息管理' AND operation_type = '竞彩赛事匹配'
ORDER BY operation_time DESC LIMIT 20;

-- 2.2 基础信息管理 - 竞彩球队匹配
SELECT * FROM toto_operation_record
WHERE operation_module = '基础信息管理' AND operation_type = '竞彩球队匹配'
ORDER BY operation_time DESC LIMIT 20;

-- 2.3 比赛监控 - 竞彩赛程备注
SELECT * FROM toto_operation_record
WHERE operation_module = '比赛监控' AND operation_type = '竞彩赛程备注'
ORDER BY operation_time DESC LIMIT 20;

-- 2.4 异常管理 - 修改详情
SELECT * FROM toto_operation_record
WHERE operation_module = '异常管理' AND operation_type = '修改详情'
ORDER BY operation_time DESC LIMIT 20;


-- ------------------------------------------------------------------------------
-- 3. 核验失败日志（result='失败' 及 error_detail 错误原因）
-- ------------------------------------------------------------------------------
SELECT
    record_id,
    operation_module,
    operation_type,
    result,
    account,
    operation_time,
    error_detail
FROM toto_operation_record
WHERE operation_type IN ('竞彩赛事匹配', '竞彩球队匹配', '竞彩赛程备注', '修改详情')
  AND result = '失败'
ORDER BY operation_time DESC
LIMIT 20;


-- ------------------------------------------------------------------------------
-- 4. 按操作账号精确查询核验（对应测试点 #15）
-- ------------------------------------------------------------------------------
SELECT
    record_id,
    operation_module,
    operation_type,
    result,
    account_user,
    account,
    operation_role_name,
    operation_time
FROM toto_operation_record
WHERE account = 'zhangyudi'
  AND operation_type IN ('竞彩赛事匹配', '竞彩球队匹配', '竞彩赛程备注', '修改详情')
ORDER BY operation_time DESC;


-- ------------------------------------------------------------------------------
-- 5. 按操作角色与操作时间范围查询核验（对应测试点 #16、#17）
-- ------------------------------------------------------------------------------
SELECT
    record_id,
    operation_module,
    operation_type,
    result,
    account_user,
    account,
    operation_role_name,
    operation_time
FROM toto_operation_record
WHERE operation_role_name = '全权限用户'
  AND operation_time BETWEEN '2026-10-27 00:00:00' AND '2026-10-27 23:59:59'
ORDER BY operation_time DESC;
