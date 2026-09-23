-- 前端个人中心展示字段的默认值：昵称、部门、数据权限。
-- 套餐、积分、语言、消息通知在 V1 已有默认值。

ALTER TABLE user_account ALTER COLUMN display_name SET DEFAULT '测试用户';
ALTER TABLE user_account ALTER COLUMN department SET DEFAULT '研究部';
ALTER TABLE user_account ALTER COLUMN data_scopes SET DEFAULT '行情 / 财报 / 公告';

UPDATE user_account SET display_name = '测试用户' WHERE display_name IS NULL OR display_name = '';
UPDATE user_account SET department = '研究部' WHERE department IS NULL OR department = '';
UPDATE user_account SET data_scopes = '行情 / 财报 / 公告' WHERE data_scopes IS NULL OR data_scopes = '';
UPDATE user_account SET plan = 'basic' WHERE plan IS NULL OR plan = '';
