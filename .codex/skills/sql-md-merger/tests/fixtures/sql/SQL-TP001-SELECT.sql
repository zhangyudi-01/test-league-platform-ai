-- :ACCOUNT = 权限测试专用账号；示例 qa_user
SELECT a.account_id, a.account, r.role_name
FROM toto_account AS a
WHERE a.account = :ACCOUNT;
