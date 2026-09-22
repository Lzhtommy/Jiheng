# 玑衡 AI（Jiheng）

面向个人的、可溯源的 A 股 AI 研究辅助工具 MVP。

> 本项目只呈现数据、研究线索和多空论证，不提供买卖时机、目标价或明确荐股。当前内置数据为可重复的演示数据，非实时行情，不构成投资建议。

## 当前能力

- 自然语言选股：将 `PE<25 且 ROE>15% 且现金流为正` 等问题拆成结构化条件；
- 可溯源个股诊断：展示估值、成长、现金流和每条结论对应的证据 ID；
- AI 衍生数据标识：把推断结果与硬数据分开，并显示推断公式和置信度；
- 多空辩论：Bull / Bear 基于同一证据集展开论证，并列出需要继续证伪的证据；
- 演示数据适配层：后续可接入 AKShare、Tushare、BaoStock 和巨潮公告，不改变上层 API。

## 本地运行

使用 Python 3.11 或更高版本：

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

打开 <http://127.0.0.1:8000/>。

## API

- `GET /api/health`：服务与数据模式；
- `POST /api/screen`：自然语言筛选；
- `GET /api/stocks/{code}/diagnosis`：个股诊断与证据链；
- `GET /api/stocks/{code}/debate`：多空辩论；
- `GET /docs`：交互式 API 文档。

运行测试：

```powershell
& .\.venv\Scripts\python.exe -m pytest
```

## 下一步

1. 接入 AKShare/BaoStock 的盘后真实数据并保留来源字段；
2. 接入巨潮公告，增加公告事件时间线；
3. 增加可配置的 OpenAI-compatible LLM，让模型只负责解释，不直接生成未经工具返回的数字；
4. 加入缓存、数据更新时间和接口失败降级。
