# 错误码体系

> 玑衡AI 后端统一错误码 + HTTP 状态码映射

## 错误响应格式

```json
{"success": false, "code": "ERROR_CODE", "message": "错误描述"}
```

## 错误码清单

### 鉴权类（AUTH_*，HTTP 401/403）

| 错误码 | HTTP | 说明 |
|--------|------|------|
| `AUTH_TOKEN_MISSING` | 401 | 缺少认证令牌 |
| `AUTH_TOKEN_EXPIRED` | 401 | 认证令牌已过期 |
| `AUTH_TOKEN_INVALID` | 401 | 认证令牌无效 |
| `AUTH_SESSION_INVALID` | 401 | 会话已失效 |
| `AUTH_CAPTCHA_INVALID` | 400 | 图形验证码无效 |
| `AUTH_SMS_INVALID` | 400 | 短信验证码无效 |
| `AUTH_USER_NOT_FOUND` | 400 | 手机号或验证码不正确 |
| `AUTH_USER_LOCKED` | 403 | 用户已锁定 |
| `AUTH_USER_FROZEN` | 403 | 用户已冻结 |
| `AUTH_REFRESH_EXPIRED` | 401 | refresh_token 已过期 |
| `INTERNAL_TOKEN_INVALID` | 401 | 服务间认证失败 |

### 业务类（BIZ_*，HTTP 400/404/409）

| 错误码 | HTTP | 说明 |
|--------|------|------|
| `VALIDATION_ERROR` | 400 | 参数校验失败 |
| `SKILL_NOT_FOUND` | 404 | 技能不存在 |
| `SKILL_OFFICIAL_DELETE_FORBIDDEN` | 403 | 禁止删除官方技能 |
| `SKILL_OWNER_MISMATCH` | 403 | 非创建者无权修改 |
| `REPORT_NOT_FOUND` | 404 | 报告不存在 |
| `REPORT_EXPORT_FORBIDDEN` | 403 | 禁止导出他人私有报告 |
| `TASK_NOT_FOUND` | 404 | 任务不存在 |
| `TASK_CRON_INVALID` | 400 | cron 表达式无效 |
| `NOTIFICATION_NOT_FOUND` | 404 | 通知不存在 |
| `OPTIMISTIC_LOCK_CONFLICT` | 409 | 乐观锁冲突 |

### 对话类（CHAT_*，SSE error 事件）

| 错误码 | 说明 |
|--------|------|
| `CONVERSATION_BUSY` | 同一会话已有进行中对话 |
| `MODEL_SILENT_TIMEOUT` | 模型响应超时 |
| `GUARD_RETRY_EXHAUSTED` | 输出守卫重试耗尽，已回退 |
| `TOOL_EXECUTION_FAILED` | 工具执行失败 |
| `DEEP_RESEARCH_FAILED` | 深度研究执行失败 |

### 系统类（HTTP 500）

| 错误码 | HTTP | 说明 |
|--------|------|------|
| `INTERNAL_ERROR` | 500 | 服务内部错误 |