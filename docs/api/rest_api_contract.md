# REST 接口契约

> 玑衡AI 后端 REST 接口清单（Java 业务服务 8080 + Python Agent 服务 8000）

## 1. 鉴权（auth）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/auth/captcha` | 获取图形验证码 | 否 |
| POST | `/api/v1/auth/sms` | 发送短信验证码 | 否 |
| POST | `/api/v1/auth/login` | 手机号+验证码登录 | 否 |
| POST | `/api/v1/auth/refresh` | 刷新 Token | 否（需 refresh_token） |
| POST | `/api/v1/auth/logout` | 登出 | 是 |

## 2. 用户资料（profile）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/profile` | 获取资料+统计 | 是 |
| PUT | `/api/v1/profile` | 编辑资料 | 是 |

## 3. 技能（skill）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/config/skills?version={v}` | 官方技能目录（304 缓存） | 是 |
| PUT | `/api/v1/skills/{skill_id}/enabled` | 开关同步 | 是 |
| POST | `/api/v1/skills` | 创建自建技能 | 是 |
| GET | `/api/v1/skills/custom` | 自建技能列表 | 是 |

## 4. 专家（expert）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/config/experts?version={v}` | 专家配置下发（304 缓存） | 是 |

## 5. 报告（report）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/reports?type={t}&page={p}&size={s}` | 报告列表 | 是 |
| GET | `/api/v1/reports/{report_id}` | 报告全文 | 是 |
| POST | `/api/v1/reports/{report_id}/export` | 导出（异步 202） | 是 |

## 6. 定时与提醒任务（task）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/tasks?type={t}` | 任务列表 | 是 |
| POST | `/api/v1/tasks` | 创建任务 | 是 |
| PUT | `/api/v1/tasks/{task_id}` | 更新任务 | 是 |
| DELETE | `/api/v1/tasks/{task_id}` | 删除任务 | 是 |

## 7. 通知（notify）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/v1/notifications?page={p}&size={s}` | 通知列表 | 是 |
| PUT | `/api/v1/notifications/{id}/read` | 标记已读 | 是 |
| PUT | `/api/v1/notifications/read-batch` | 批量已读 | 是 |

## 8. 埋点（events）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/events` | 批量上报 | 是 |

## 9. 服务间接口（internal，仅内网）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/internal/config/experts` | 专家配置（Python 读取） | Service Token |
| GET | `/internal/config/skills?user_id={uid}` | 用户技能配置 | Service Token |
| POST | `/internal/reports` | 报告归档回写 | Service Token |
| POST | `/internal/skills/{skill_id}/run` | 技能运行计数 | Service Token |
| POST | `/internal/notifications` | 通知创建 | Service Token |

## 10. 对话（chat，Python Agent 服务 8000）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/chat/stream` | SSE 流式对话 | JWT |
| POST | `/chat/abort` | 对话中断 | JWT |
| GET | `/trace/{trace_id}/replay` | trace 回放 | JWT |
| GET | `/health` | 健康检查 | 否 |