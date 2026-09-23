-- 黑客松默认登录账号（手机号需与 app.default-phone 一致）
INSERT INTO user_account (phone, display_name, plan, status)
VALUES ('15611437032', '测试用户', 'basic', 'verified')
ON CONFLICT (phone) DO NOTHING;
