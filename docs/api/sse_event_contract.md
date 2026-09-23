# SSE 事件契约（15 类事件）

> 玑衡AI Python Agent 服务 `POST /chat/stream` 流式对话事件协议
> 事件格式：`event: {type}\ndata: {json}\n\n`

## 事件类型总览

| 事件 | 阶段 | 说明 | 模式 |
|------|------|------|------|
| `start` | 0 | 对话开始，返回 correlation_id | 全部 |
| `stage` | 0-3 | 阶段切换通知 | 全部 |
| `tool_call` | 1 | 工具/技能调用开始 | 全部 |
| `tool_result` | 2 | 工具/技能调用结果 | 全部 |
| `reasoning_start` | 1 | 推理链开始 | deep/expert |
| `reasoning_end` | 2 | 推理链结束 | deep/expert |
| `message_chunk` | 3 | 正文流式分片（打字机） | quick |
| `intro` | 3 | 引言段 | 全部 |
| `section` | 3 | 结构化正文 Section | deep/expert |
| `table` | 3 | Key-Value 数据表 | 全部 |
| `risk` | 3 | 风险提示 | 全部 |
| `refs` | 3 | 溯源列表 | 全部 |
| `done` | - | 对话完成 | 全部 |
| `aborted` | - | 用户中断 | 全部 |
| `error` | - | 错误 | 全部 |

## 事件 Schema

### start
```json
{"correlation_id": "uuid", "conversation_id": "string", "mode": "quick|deep|expert", "expert": "string|null"}
```

### stage
```json
{"correlation_id": "uuid", "stage": 0, "description": "正在检索..."}
```

### tool_call
```json
{"correlation_id": "uuid", "call_id": "string", "tool_name": "聚合搜索", "tool_input": "query string", "is_skill": false}
```

### tool_result
```json
{"correlation_id": "uuid", "call_id": "string", "tool_name": "聚合搜索", "tool_result": "result text", "success": true}
```

### reasoning_start / reasoning_end
```json
{"correlation_id": "uuid", "part_id": "string"}
```

### message_chunk
```json
{"correlation_id": "uuid", "content": "partial text"}
```

### intro
```json
{"correlation_id": "uuid", "intro": "引言文本"}
```

### section
```json
{"correlation_id": "uuid", "title": "小标题", "para": "段落|null", "items": ["要点1", "要点2"]}
```

### table
```json
{"correlation_id": "uuid", "table_title": "表标题", "table_rows": [["key", "value"], ...]}
```

### risk
```json
{"correlation_id": "uuid", "risk": "以上分析仅供参考，不构成投资建议。"}
```

### refs
```json
{"correlation_id": "uuid", "ref_count": 3, "refs": [{"title": "来源标题", "tag": "数据", "date": "2026-09-22", "url": "https://..."}]}
```

### done
```json
{"correlation_id": "uuid", "message_id": "string|null"}
```

### aborted
```json
{"correlation_id": "uuid", "reason": "user_abort", "partial_content": "已渲染内容"}
```

### error
```json
{"correlation_id": "uuid", "code": "ERROR_CODE", "message": "错误描述"}
```

## 事件顺序约束

### 快速问答（quick）
```
start → stage{0} → tool_call → intro → tool_result → message_chunk* → table? → risk → refs → done
```

### 深度研究（deep）
```
start → stage{0} → reasoning_start → message_chunk* → reasoning_end → tool_call → tool_result → (多轮重复) → stage{3} → section* → table? → risk → refs → done
```

### 金融专家团（expert）
```
start → stage{0} → (同 deep 流程，加载专家专属系统提示与工具集) → done
```

## 中断与错误

- 用户中断：下发 `aborted` 事件后关闭 SSE 连接
- 服务端错误：下发 `error` 事件后关闭 SSE 连接
- 并发拒绝：`error{code:"CONVERSATION_BUSY"}`
- 守卫失败：重生成一次，仍失败回退通用回复（不下发 error，直接用回退内容继续流）