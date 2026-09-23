# 玑衡 AI（Jiheng AI）

> 上古先民以玑衡观测星辰、校准时序；我们以玑衡 Agent 观测财报、因子与市场信号，自动丈量市场规律，预判资产周期。

玑衡 AI 是一款对话式金融投研 Agent 移动应用（Flutter，iOS / Android），Slogan 为「你的智能金融操作系统」。以「一个输入框 + 三种模式（快速问答 / 深度研究 / 金融专家团）」承接投研意图，接入实时行情、研究数据与自动化金融 Agent 技能，产出带溯源、带风险提示的结构化分析与报告。定位为**研究辅助与投资教育工具**，不提供个股买卖建议。

核心模块：

- **对话三模式**：快速问答 / 深度研究 / 金融专家团（6 类专家角色协作）
- **技能广场**：36+ 官方技能 + 用户自建技能，封装可复用分析框架
- **报告库**：深度研究 / 公司研究 / 晨报等报告归档、查看与导出
- **定时任务与提醒**：定时任务 + 条件触发提醒，配合通知中心闭环

目标用户：买方/卖方研究员、投资顾问、组合经理与专业个人投资者。

## 目录结构

```text
Jiheng/
├── jiheng-java/                  # 业务 CRUD 服务（Spring Boot 3 + Java 21）
├── jiheng-python/                # Agent 服务（FastAPI + DeepSeek Harness）
├── industry_research_institute/  # 多行业行研 agent 集群 + 拉数作业（申万分类体系）
├── docs/                         # 产品文档：PRD、实施计划、原型、API 契约
├── deploy/                       # 部署配置（nginx 反向代理）
└── docker-compose.yml            # 本地/单机编排入口
```

## 架构

```
                ┌────────────┐
   client ───▶  │   nginx    │  :8088
                └─────┬──────┘
           ┌──────────┼───────────┐
     /api/ │                /chat/│ /health
           ▼                      ▼
   ┌───────────────┐      ┌───────────────┐
   │  jiheng-java  │◀────▶│ jiheng-python │
   │ (Spring Boot) │ HTTP │  (FastAPI)    │
   └───────┬───────┘      └───────┬───────┘
           │                      │
      Postgres                 Redis
      (业务数据)              (会话/缓存，两服务共用)
```

- **jiheng-java**：业务 CRUD 服务，负责鉴权（JWT）、用户画像、技能、报告、任务、通知、专家等模块，落地 PostgreSQL（Flyway 管理迁移），MyBatis-Plus 访问数据。
- **jiheng-python**：Agent 服务，基于 FastAPI + DeepSeek Harness 驱动对话、深度研究与工具调用（行情、新闻、搜索、技能包），通过内部 HTTP 调用 jiheng-java，SSE 推送流式事件。
- **nginx**：统一入口，`/api/` 转发 Java 服务，`/chat/` 与 `/health` 转发 Python 服务，`/internal/` 直接拒绝外部访问。
- **industry_research_institute**：独立的行业研究 agent 集群仓库，共享申万 2021 行业分类与财报/一致预期拉数作业，为各一级行业单独建模估值（详见其 [README](industry_research_institute/README.md)）。

## 技术栈

| 模块 | 技术栈 |
| --- | --- |
| jiheng-java | Java 21・Spring Boot 3.5・MyBatis-Plus・PostgreSQL・Flyway・Redis・JWT (jjwt) |
| jiheng-python | Python 3.11+・FastAPI・DeepSeek Harness (dsh)・httpx・Redis・SSE |
| industry_research_institute | Python・Postgres 拉数作业・申万 2021 行业分类 |
| 网关 | nginx |
| 编排 | Docker Compose |

## 快速开始

### 环境要求

- Docker / Docker Compose
- 本地开发另需：JDK 21 + Maven（jiheng-java），Python 3.11+（jiheng-python）

### 使用 Docker Compose 一键启动

在仓库根目录创建 `.env`（或通过 shell 导出），至少提供以下必填变量：

```bash
VR_PG_HOST=...
VR_PG_DATABASE=...
VR_PG_USER=...
VR_PG_PASSWORD=...
JWT_SECRET=...
SERVICE_TOKEN=...
JIHENG_DEEPSEEK_API_KEY=...
JIHENG_FINANCIAL_MCP_API_KEY=...
```

然后：

```bash
docker compose up --build
```

服务启动后统一从 `http://localhost`（nginx 默认监听 80 端口）访问：

- `http://localhost/api/...` → jiheng-java
- `http://localhost/chat/...` → jiheng-python（SSE，长连接）
- `http://localhost/health` → 健康检查

生产环境通过 `.github/workflows/deploy.yml` 自动部署到 Huawei Cloud（`DEPLOY_HOST` secret），同样走 80 端口，例如 `http://113.45.32.33/health`。

### 本地分别启动（开发调试）

```bash
# jiheng-java
cd jiheng-java
mvn spring-boot:run

# jiheng-python
cd jiheng-python
uv pip install -e ".[dev]"   # 或 pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

## 文档

- 产品需求文档（PRD）：[docs/玑衡AI 产品需求文档.md](docs/玑衡AI%20产品需求文档.md)
- 产品实施计划：[docs/玑衡AI 实施计划.md](docs/玑衡AI%20实施计划.md)
- 高保真原型：[docs/玑衡AI 原型.dc.html](docs/玑衡AI%20原型.dc.html)
- REST API 契约：[docs/api/rest_api_contract.md](docs/api/rest_api_contract.md)
- SSE 事件契约：[docs/api/sse_event_contract.md](docs/api/sse_event_contract.md)
- 错误码契约：[docs/api/error_code_contract.md](docs/api/error_code_contract.md)
- 行业研究院设计文档：[industry_research_institute/DESIGN.md](industry_research_institute/DESIGN.md)
