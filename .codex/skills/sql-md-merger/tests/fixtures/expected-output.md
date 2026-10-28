# 自检模块 测试用例 SQL 汇总

> 共收录 3 条查询 SQL，来源于 `sql/sql-manifest.json`；SQL 正文逐字取自对应 .sql 文件，未做任何改写。已跳过非 SELECT 资产：SQL-TP003-WRITE-PREP。

## 索引

| 序号 | SQL 标题 | SQL-ID | 来源文件 | 类型 | 用途 |
| --- | --- | --- | --- | --- | --- |
| 1 | 按专用账号查询开奖监督平台的有效账号-角色-权限关系链 | `SQL-TP001-SELECT` | `SQL-TP001-SELECT.sql` | SELECT | 按专用账号查询开奖监督平台的有效账号-角色-权限关系链，用于核对查询入口权限 |
| 2 | 文件内注释标题优先验证 | `SQL-TP002-TITLE-OVERRIDE` | `SQL-TP002-TITLE-OVERRIDE.sql` | SELECT | unused purpose because file has -- title: comment |
| 3 | 清单字段核对查询 | `SQL-TP004-MANUAL-CN` | `SQL-TP004-MANUAL-CN.sql` | SELECT | fallback purpose |

## 1. 按专用账号查询开奖监督平台的有效账号-角色-权限关系链

- 来源文件：`SQL-TP001-SELECT.sql`
- SQL-ID：`SQL-TP001-SELECT`
- 语句类型：SELECT
- 数据闭包：DC-002
- 参数：`:ACCOUNT`（权限测试专用账号，示例 qa_user）
- 用途：按专用账号查询开奖监督平台的有效账号-角色-权限关系链，用于核对查询入口权限

```sql
-- :ACCOUNT = 权限测试专用账号；示例 qa_user
SELECT a.account_id, a.account, r.role_name
FROM toto_account AS a
WHERE a.account = :ACCOUNT;
```

## 2. 文件内注释标题优先验证

- 来源文件：`SQL-TP002-TITLE-OVERRIDE.sql`
- SQL-ID：`SQL-TP002-TITLE-OVERRIDE`
- 语句类型：SELECT
- 数据闭包：DC-001
- 用途：unused purpose because file has -- title: comment

```sql
-- title: 文件内注释标题优先验证
SELECT 1 FROM dual;
```

## 3. 清单字段核对查询

- 来源文件：`SQL-TP004-MANUAL-CN.sql`
- SQL-ID：`SQL-TP004-MANUAL-CN`
- 语句类型：SELECT
- 数据闭包：DC-001
- 参数：`:TASKID`（审核任务 ID，示例 30001）；`:OFFSET`（零基偏移量，示例 0）
- 用途：fallback purpose

```sql
-- :TASKID = 审核任务 ID；示例 30001
SELECT id, draw_year, draw_no
FROM notary_audit_batch
WHERE id = :TASKID
ORDER BY id DESC
LIMIT :OFFSET, 100;
```
