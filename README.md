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

仓库包含金融 Agent 的 Java/Python 多服务代码；下方是其服务架构示意。根目录 `docker-compose.yml` 当前启动的是独立 World 演示后端（端口 `18000`），不会启动下方全部服务。

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

### 使用 Docker Compose 启动 World 演示后端

在仓库根目录运行：

```bash
docker compose up -d --build
```

服务映射到 `http://localhost:18000`，可打开：

- `http://localhost:18000/`：主页
- `http://localhost:18000/procurement-explore`：World 产业链走访
- `http://localhost:18000/docs`：API 文档

NPC 默认使用离线剧情。启用模型改写时，在 `.env` 中设置 `JIHENG_NPC_API_URL`、`JIHENG_NPC_API_KEY` 和 `JIHENG_NPC_MODEL`。

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

## Docker 部署

服务器安装 Docker 和 Docker Compose 后，在项目根目录运行：

```bash
docker compose up -d --build
```

服务默认监听容器内 `8000` 端口，并映射到服务器的 `18000` 端口。启动后打开：

- `http://服务器IP:18000/`
- `http://服务器IP:18000/docs`
- `http://服务器IP:18000/api/health`

常用命令：

```bash
docker compose logs -f backend
docker compose restart backend
docker compose down
```

如果要启用 NPC 模型改写，在服务器环境变量或项目根目录 `.env` 文件中配置：

```bash
JIHENG_NPC_API_URL=https://你的兼容接口/v1/chat/completions
JIHENG_NPC_API_KEY=你的密钥
JIHENG_NPC_MODEL=你的模型名
```

## 玑衡 World · 沉浸式产业链走访

`/procurement-explore` 是独立的网页体验：玩家以采购负责人的第一视角走访盐湖矿区、材料工坊、电芯城、车企港和储能灯塔，与 NPC 谈条件、收集卷轴，并从地图进入下一场景。可在仓库根目录安装 `requirements.txt` 后运行 `uvicorn app.main:app`，打开 <http://127.0.0.1:8000/procurement-explore>。

同一剧情也作为离线资源打包进 `jiheng_ai_flutter`，从 App 首页或侧边栏进入竖屏游戏页，不依赖手机访问电脑的 `127.0.0.1`。App 内默认使用编排好的剧情对话，进度保存在设备上；网页端在配置 `JIHENG_NPC_API_URL`、`JIHENG_NPC_API_KEY` 和 `JIHENG_NPC_MODEL` 后，可让兼容 Chat Completions 的模型改写 NPC 台词。模型不决定剧情状态。修改网页剧情或素材后，运行 `scripts/sync_world_assets.ps1` 同步到 Flutter 资源目录。

材料工坊是第一段深入打磨的谈判样例：玩家可查看批次台账、长协复印件和排产白板，再在「现价锁排产／季度核价／滚动采购计划」之间提出方案。缺少依据的方案会被坊主驳回；谈成的条件会改变电芯城的开场、口头条款与最终走访记录。现场对象是主要入口，预设问法收在「对话提示」里。

World 的人物、合同及数字均为虚构演示，不代表真实企业披露或投资建议。

从仓库根目录运行 `python -m pytest` 会执行 World 的测试；`jiheng-python` 是独立的 Python 包，应在其目录内运行自己的测试。Flutter 部分在安装 Flutter SDK 后于 `jiheng_ai_flutter` 目录运行 `flutter pub get` 和 `flutter test`。
材料工坊的剧情分支可用 `node --test tests/world_materials.test.cjs` 单独验证，无需 Flutter SDK。
