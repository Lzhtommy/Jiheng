# 玑衡 AI（Jiheng AI）

> 上古先民以玑衡观测星辰、校准时序；我们以玑衡 Agent 观测财报、因子与市场信号，自动丈量市场规律，预判资产周期。

玑衡 AI 是一款对话式金融投研 Agent 移动应用（Flutter，iOS / Android），Slogan 为「你的智能金融操作系统」。以「一个输入框 + 三种模式（快速问答 / 深度研究 / 分析师）」承接投研意图，接入实时行情、研究数据与自动化金融 Agent 技能，产出带溯源、带风险提示的结构化分析与报告。定位为**研究辅助与投资教育工具**，不提供个股买卖建议。

核心模块：

- **对话三模式**：快速问答 / 深度研究 / 分析师（个股 / 行业 / 财报三类分析师角色），「分析师」模式可选开启「多 Agent 协作」，以任务树的形式拆解、执行、审核、汇总
- **玑衡 World**：内置离线 HTML5 情景模拟小游戏，当前已上线「采购之旅」新能源电池产业链场景，首页与「玑衡AI」对话页之间用渐进式过场动画切换
- **技能广场**：36 个官方技能 + 用户自建技能，封装可复用分析框架
- **报告库**：深度研究 / 公司研究 / 晨报等报告归档、查看与导出
- **对话历史与收藏**：侧边栏回看历史会话，答案要点本地收藏
- **定时任务与提醒**：定时任务（cron）已实现增删查；条件触发提醒仍是待完善的占位功能

目标用户：买方/卖方研究员、投资顾问、组合经理与专业个人投资者。

## 目录结构

```text
Jiheng/
├── jiheng_ai_flutter/            # 移动端 App（Flutter，iOS / Android），产品唯一入口
├── jiheng-java/                  # 业务 CRUD 服务（Spring Boot 3 + Java 21）
├── jiheng-python/                # Agent 服务（FastAPI，多 Agent 编排 + 工具调用）
├── industry_research_institute/  # 行业研究 agent 集群 + 拉数作业（申万 2021 分类体系，目前仅电子行业落地）
├── docs/                         # 产品文档：PRD、实施计划、API 契约
├── prototype/                    # 已被 Flutter App 取代的高保真 HTML 原型（历史参考）
├── deploy/                       # 部署配置（nginx 反向代理）
└── docker-compose.yml            # 本地/单机编排入口
```

## 架构

```
                ┌────────────┐
   client ───▶  │   nginx    │  :80
                └─────┬──────┘
           ┌──────────┼───────────┐
     /api/ │                /chat/│ /health
           ▼                      ▼
   ┌───────────────┐      ┌───────────────┐
   │  jiheng-java  │◀────▶│ jiheng-python │
   │ (Spring Boot) │ HTTP │  (FastAPI)    │
   └───────┬───────┘      └───────────────┘
           │
      Postgres
      (业务数据)
```

- **jiheng_ai_flutter**：Flutter 客户端，产品唯一入口。首页顶部可在「玑衡AI」（对话）与「玑衡World」（内置离线 HTML5 小游戏）之间切换；对话页支持三种模式、专家/分析师选择、多 Agent 协作图谱与时间线、技能开关、报告库、定时任务、通知中心、历史会话侧边栏与本地收藏。
- **jiheng-java**：业务 CRUD 服务。登录接口不接收手机号/验证码参数，直接按配置的默认账号（`15611437032`，黑客松阶段的简化鉴权）签发 JWT，验证码接口仅生成图形验证码用于展示、不参与校验；另负责用户画像、技能、报告、定时任务、通知、专家/分析师配置、**会话与对话历史持久化**等模块，落地 PostgreSQL（Flyway 管理迁移），MyBatis-Plus 访问数据，并对内暴露 `/internal/*` 接口供 jiheng-python 回调写入报告、通知与对话记录。
- **jiheng-python**：Agent 服务，基于 FastAPI 驱动三种对话模式——快速问答 / 深度研究 / 分析师共用同一套工具与合规链路，仅模型（`deepseek_model_quick` / `deepseek_model_deep`）、工具调用轮数与 reasoning_effort 按模式区分，**网关地址三种模式共用、并非分别配置**。「分析师」模式对应个股 / 行业 / 财报三类 SOP，可选开启多 Agent 协作：Planner 生成任务树，GraphExecutor 按研究→审核→撰写三阶段分层执行，并通过 SSE 推送协作图谱事件（`agent_graph`/`agent_status`/`agent_message`/`agent_output`/`phase`）。工具层覆盖行情与板块资金流（东方财富）、公告全文与公司日历（巨潮资讯网）、新闻政策、外部财报 MCP 网关；所有输出经 GuardChain（风险提示、溯源校验、禁用词过滤、AI 生成声明）强制校验后才返回。通过内部 HTTP 调用 jiheng-java，SSE 推送流式事件；深度研究任务使用进程内队列，重启后未执行的任务会丢失。
- **nginx**：统一入口，`/api/` 转发 Java 服务，`/chat/` 与 `/health` 转发 Python 服务，`/internal/` 直接拒绝外部访问。
- **industry_research_institute**：独立的行业研究 agent 集群仓库，与主产品（jiheng-java/python）暂未集成，也不调用估值路由引擎；共享申万 2021 行业分类与财报/一致预期拉数作业。目前仅**电子行业**集群（`clusters/electronics_research_agent`）落地，覆盖 7 个三级研究员槽位、17 只标的，默认关闭 LLM 叙事生成，仅产出结构化数据 + 草稿综述；其余申万一级行业尚为规划状态（详见其 [README](industry_research_institute/README.md)）。

## 技术栈

| 模块 | 技术栈 |
| --- | --- |
| jiheng_ai_flutter | Flutter（Dart ≥3.4）・webview_flutter・flutter_secure_storage・flutter_markdown_plus |
| jiheng-java | Java 21・Spring Boot 3.5.6・MyBatis-Plus 3.5.8・PostgreSQL・Flyway・jjwt 0.12.6・Hutool（验证码）・Hashids |
| jiheng-python | Python 3.11+・FastAPI・httpx・sse-starlette（SSE）・Pydantic 2・MCP Python SDK（工具 schema）・PyMuPDF（公告 PDF 解析）・structlog |
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

可选变量（有默认值，用于按模式分别指定模型/网关，见 `docker-compose.yml`）：`JIHENG_DEEPSEEK_BASE_URL`、`JIHENG_DEEPSEEK_MODEL_QUICK`（快速问答）、`JIHENG_DEEPSEEK_MODEL_DEEP`（深度研究 / 分析师共用）。

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

- 产品介绍：[docs/玑衡AI 产品介绍.md](docs/玑衡AI%20产品介绍.md)
- 产品需求文档（PRD，v0.1 草稿）：[docs/玑衡AI 产品需求文档.md](docs/玑衡AI%20产品需求文档.md)
- 产品实施计划（v0.1 草稿）：[docs/玑衡AI 实施计划.md](docs/玑衡AI%20实施计划.md)
- 高保真原型（已被 Flutter App 取代，仅作历史参考）：[prototype/玑衡AI 原型.dc.html](prototype/玑衡AI%20原型.dc.html)
- REST API 契约：[docs/api/rest_api_contract.md](docs/api/rest_api_contract.md)
- SSE 事件契约：[docs/api/sse_event_contract.md](docs/api/sse_event_contract.md)
- 错误码契约：[docs/api/error_code_contract.md](docs/api/error_code_contract.md)
- 行业研究院设计文档：[industry_research_institute/DESIGN.md](industry_research_institute/DESIGN.md)

> PRD 与实施计划中"用户数据落地本地 SQLite"的描述已被实际实现取代——当前落地方案是 PostgreSQL + Flyway（见上方架构）。

## 术语表

| 术语 | 含义 |
| --- | --- |
| 分析师 / expert | 产品对外统一称"分析师"；数据库表与代码内部仍沿用 `expert` 命名（V6 迁移只改了展示名，未改表名），后端共 6 个专家配置，但仅**个股 / 行业 / 财报**三类配有多 Agent SOP 且在客户端可选 |
| 多 Agent 协作 / 协作图谱 | 「分析师」模式下的可选能力：Planner 生成任务树（根节点"首席分析师" + 子任务节点）→ GraphExecutor 按 research（并行取数）→ review（父节点审核、不合格打回重做）→ writing（逐层汇总、根节点流式产出）三阶段执行，节点状态含 pending/running/revising/submitted/approved/failed/done，消息类型为 派发（assign）/ 提交（submit）/ 打回（feedback）/ 通过（approve） |
| GuardChain | jiheng-python 中强制校验每条输出的过滤链：风险提示 / 引用溯源非空 / 数字类结论必须有来源 / 禁用词（买入、卖出、满仓等）/ AI 生成声明，全部通过后才允许返回 |
| 玑衡 World | App 内内置的离线 HTML5 情景模拟小游戏（`assets/game/`，通过 `WebViewController.loadFlutterAsset` 加载，非在线站点），当前旗舰场景「采购之旅」还原新能源电池产业链（盐湖矿 → 材料车间 → 电芯车间 → 下游港口） |
| internal API | jiheng-java 的 `/internal/*` 前缀接口，仅供 jiheng-python 内部回调（写报告/通知/对话记录、读取专家与技能配置），nginx 层对外直接拒绝 |
| Hashids | jiheng-java 对外暴露的用户 ID 是 Hashids 编码后的字符串，而非数据库自增主键 |
| 申万 2021 | industry_research_institute 使用的行业分类基准（31 个一级 / 134 个二级 / 346 个三级行业），目前仅电子行业（270000）一个一级分类落地了完整的研究 agent 集群 |
| 拉数作业 | industry_research_institute 中定时批量抓取行情、财报、一致预期等数据写入 Postgres 的脚本；产出会读取估值路由引擎维护的 `valuation_inputs`/`valuation_summary` 表，但只读不改，两套系统解耦 |
