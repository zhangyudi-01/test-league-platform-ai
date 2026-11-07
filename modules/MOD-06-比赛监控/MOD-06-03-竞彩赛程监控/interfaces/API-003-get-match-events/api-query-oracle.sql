-- API-003 GET /sporttery/match-monitor/events
-- 状态：ready，仅覆盖测试方案 1～22 的合法参数场景；相关查询已在开发环境随自动化执行验证。
-- 方言：MySQL；参数顺序为 sportId、竞彩官方 matchId（均由当前请求获取）。
-- 只读：分别执行以下查询；不分页、不依赖服务实现或测试环境中的固定 ID。
-- DATETIME 按数据库记录的年月日时分秒比较，连接及接口时间语义需在实施时核验。

-- 事件列表预期；无匹配记录时，应用层将空结果转换为 data=[]。
SELECT event_id AS eventId,
       create_time AS eventTime,
       event_name AS title,
       reason_desc AS exceptionDetail
FROM sporttery_match_event
WHERE sport_id = %s
  AND source_id = %s
ORDER BY create_time DESC, event_id DESC;

-- 测试点 20：请求前后分别运行，比较同一完整范围的主键集合和所有选定字段。
SELECT event_id,
       event_name,
       reason_title,
       reason_desc,
       create_time,
       update_time
FROM sporttery_match_event
WHERE sport_id = %s
  AND source_id = %s
ORDER BY event_id;
