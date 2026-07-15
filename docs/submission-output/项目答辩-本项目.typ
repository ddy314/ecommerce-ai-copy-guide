#import "@preview/touying:0.7.4": *
#import themes.simple: *

#let navy = rgb("#17324D")
#let blue = rgb("#2563EB")
#let cyan = rgb("#0891B2")
#let mint = rgb("#0F766E")
#let amber = rgb("#D97706")
#let red = rgb("#B91C1C")
#let violet = rgb("#7C3AED")
#let ink = rgb("#172033")
#let muted = rgb("#64748B")
#let pale = rgb("#F1F5F9")
#let light-blue = rgb("#DBEAFE")
#let light-cyan = rgb("#E0F2FE")
#let light-mint = rgb("#D1FAE5")
#let light-amber = rgb("#FEF3C7")
#let light-red = rgb("#FEE2E2")
#let light-violet = rgb("#F3E8FF")

#set text(font: "Noto Sans CJK SC", fill: ink, size: 18pt)
#set heading(numbering: none)
#show strong: set text(fill: navy)

#let tag(body, fill: light-blue, color: blue) = box(
  fill: fill,
  stroke: color.lighten(38%),
  radius: 5pt,
  inset: (x: 9pt, y: 4pt),
  text(size: 13pt, weight: "bold", fill: color, body),
)

#let card(title, body, color: blue) = block(
  width: 100%,
  inset: 12pt,
  radius: 7pt,
  fill: white,
  stroke: color.lighten(56%),
  [#text(size: 17pt, weight: "bold", fill: color)[#title]
   #v(5pt)
   #text(size: 14pt, fill: ink)[#body]],
)

#let metric(value, label, color: blue) = block(
  width: 100%,
  inset: 11pt,
  radius: 7pt,
  fill: color.lighten(88%),
  stroke: color.lighten(58%),
  [#text(size: 25pt, weight: "bold", fill: color)[#value]
   #v(2pt)
   #text(size: 12.5pt, fill: muted)[#label]],
)

#let code-line(body) = block(
  width: 100%, inset: (x: 12pt, y: 7pt), radius: 5pt,
  fill: rgb("#0F172A"),
  text(font: "DejaVu Sans Mono", size: 12pt, fill: white, body),
)

#show: simple-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [电商 AI 商品文案生成与智能导购助手],
    subtitle: [系统架构与维护设计],
    author: [项目组（成员姓名待补充）],
    date: [2026-07-15],
  ),
)

#slide[
  #align(center + horizon)[
    #text(size: 13pt, weight: "bold", fill: cyan)[VUE · FLASK · POSTGRESQL · REDIS · AI]
    #v(10pt)
    #text(size: 34pt, weight: "bold", fill: navy)[电商 AI 商品文案生成与智能导购助手]
    #v(8pt)
    #text(size: 21pt, weight: "bold", fill: blue)[系统架构与维护设计]
    #v(22pt)
    #grid(
      columns: (1fr, 1fr, 1fr, 1fr), gutter: 10pt,
      tag([单页应用], fill: light-cyan, color: cyan),
      tag([分层 API], fill: light-blue, color: blue),
      tag([数据与缓存], fill: light-mint, color: mint),
      tag([AI Provider], fill: light-violet, color: violet),
    )
    #v(24pt)
    #text(size: 13.5pt, fill: muted)[项目组（成员姓名待补充） · 2026-07-15]
  ]
]

== 系统组成

#grid(
  columns: (1fr, 1fr, 1fr, 1fr), gutter: 10pt,
  metric([Vue 3], [浏览器单页应用], color: cyan),
  metric([Flask 3], [REST API 服务], color: blue),
  metric([PostgreSQL], [业务数据持久化], color: mint),
  metric([Redis 7], [重复生成缓存], color: amber),
)
#v(16pt)
#grid(
  columns: (1fr, 1fr), gutter: 16pt,
  [
    #text(size: 20pt, weight: "bold", fill: navy)[开发运行]
    #v(6pt)
    #text(size: 15pt)[Vue 由 Vite 提供开发服务器；Flask 运行在 8000；未设置数据库地址时使用 `instance/ecommerce_ai.db`。]
  ],
  [
    #text(size: 20pt, weight: "bold", fill: navy)[容器运行]
    #v(6pt)
    #text(size: 15pt)[Nginx 暴露 8081；Flask 由 Gunicorn 托管；PostgreSQL 与 Redis 由 Compose 编排。]
  ],
)

== 系统边界与访问路径

#align(center)[#image("assets/system-architecture.png", width: 70%)]
#v(10pt)
#grid(
  columns: (1fr, 1fr, 1fr), gutter: 11pt,
  tag([/ · Vue 静态站点], fill: light-cyan, color: cyan),
  tag([API · Flask :8000], fill: light-blue, color: blue),
  tag([/health · 健康检查], fill: light-mint, color: mint),
)

== 技术栈分层

#text(size: 13.5pt)[#table(
  columns: (18%, 34%, 48%),
  inset: 8pt,
  stroke: rgb("#CBD5E1"),
  fill: (x, y) => if y == 0 { navy } else if calc.even(y) { pale } else { white },
  table.header(
    text(weight: "bold", fill: white)[层次],
    text(weight: "bold", fill: white)[主要技术],
    text(weight: "bold", fill: white)[职责],
  ),
  [前端], [Vue 3 · TypeScript · Vite 8], [页面组织、状态恢复、异步组件与交互],
  [UI], [Ant Design Vue · Tailwind · Motion], [标准控件、布局规则、动画反馈与主题],
  [API], [Flask 3 · Pydantic 2 · Gunicorn], [路由、参数校验、业务编排与生产托管],
  [安全], [JWT · Werkzeug · Flask-CORS], [身份、角色、密码哈希与来源控制],
  [数据], [SQLAlchemy · Alembic · PostgreSQL], [模型映射、会话管理与版本迁移],
  [智能], [Redis · OpenAI-compatible · Mock], [缓存、RAG 上下文与内容生成],
)]

== 目录职责

#grid(
  columns: (42%, 58%), gutter: 18pt,
  [
    #block(width: 100%, inset: 13pt, radius: 6pt, fill: rgb("#0F172A"))[
      #text(font: "DejaVu Sans Mono", size: 12pt, fill: white)[
        backend/api/  
        backend/models/  
        backend/services/  
        backend/crawler/  
        frontend/src/  
        migrations/  
        scripts/
      ]
    ]
  ],
  [
    #text(size: 14.5pt)[
      #strong[api]：按认证、用户、商家、客服、采集拆分蓝图。  
      #v(7pt)
      #strong[models]：SQLAlchemy 领域模型与关系。  
      #v(7pt)
      #strong[services]：AI、RAG、认证、上传等业务服务。  
      #v(7pt)
      #strong[crawler]：京东、苏宁采集和任务管理。  
      #v(7pt)
      #strong[frontend]：Vue 页面、组件、主题与 API 客户端。  
      #v(7pt)
      #strong[migrations]：Alembic 版本迁移。  
      #v(7pt)
      #strong[scripts]：启动与数据维护入口。
    ]
  ],
)

== 后端启动流程

#align(center)[#image("assets/backend-startup.png", width: 96%)]
#v(13pt)
#text(size: 15pt)[`backend.app:create_app()` 统一完成配置装载、扩展绑定、错误处理、数据库初始化、账号初始化和蓝图注册。]

== 应用工厂的职责边界

#grid(
  columns: (1fr, 1fr, 1fr), gutter: 12pt,
  card([配置], [从环境变量构造不可变的 AppConfig。], color: blue),
  card([框架扩展], [JWTManager 与 CORS 在创建应用时绑定。], color: cyan),
  card([基础设施], [健康检查、400/404/500 错误处理器。], color: mint),
)
#v(12pt)
#grid(
  columns: (1fr, 1fr, 1fr), gutter: 12pt,
  card([本地初始化], [init_db() 保障 SQLite 首次运行。], color: amber),
  card([账号初始化], [不存在时创建用户与商家账号。], color: violet),
  card([模块装配], [BLUEPRINTS 集中注册全部 API 域。], color: blue),
)

== API 蓝图组织

#align(center)[#image("assets/blueprint-map.png", width: 94%)]
#v(9pt)
#text(size: 15pt)[六个蓝图共享 `/api` 前缀；OpenAPI 页面由独立 `docs_bp` 提供。路由按业务域拆分，应用工厂只负责装配。]

== 分层调用关系

#align(center)[
  #grid(
    columns: (1fr, 34pt, 1fr, 34pt, 1fr, 34pt, 1fr), align: horizon,
    card([HTTP 路由], [解析请求、调用服务、返回 JSON。], color: blue),
    text(size: 25pt, fill: muted)[→],
    card([业务服务], [RAG、AI、认证、上传与采集管理。], color: cyan),
    text(size: 25pt, fill: muted)[→],
    card([模型与仓储], [SQLAlchemy 查询、事务与领域对象。], color: mint),
    text(size: 25pt, fill: muted)[→],
    card([基础设施], [PostgreSQL、Redis、外部 AI 接口。], color: amber),
  )
]
#v(16pt)
#block(width: 100%, inset: 13pt, radius: 7pt, fill: navy)[
  #text(size: 18pt, weight: "bold", fill: white)[依赖方向由接口层指向服务层和数据层，业务模块之间通过清晰职责协作]
]

== JWT 认证链路

#align(center)[#image("assets/auth-flow.png", width: 90%)]
#v(13pt)
#grid(
  columns: (1fr, 1fr), gutter: 14pt,
  card([身份校验], [`require_auth` 验证 Bearer JWT 并读取用户声明。], color: blue),
  card([角色校验], [`require_merchant` 在身份通过后检查 `role=merchant`。], color: amber),
)

== 密码、密钥与跨域

#grid(
  columns: (1fr, 1fr, 1fr), gutter: 12pt,
  card([密码存储], [新密码使用 Werkzeug scrypt 哈希；数据库不保存明文。], color: mint),
  card([兼容验证], [认证服务可读取旧 SHA-256 格式，但不会继续写入旧格式。], color: amber),
  card([JWT 密钥], [生产环境使用不少于 32 字符的随机 JWT_SECRET。], color: red),
)
#v(14pt)
#grid(
  columns: (1fr, 1fr), gutter: 14pt,
  [#text(size: 18pt, weight: "bold", fill: blue)[Token 规则] #v(5pt) #text(size: 14.5pt)[仅从 Authorization Header 读取；访问令牌有效期 24 小时。]],
  [#text(size: 18pt, weight: "bold", fill: cyan)[CORS 规则] #v(5pt) #text(size: 14.5pt)[仅覆盖 `/api/*`；允许来源由 CORS_ORIGINS 集中配置。]],
)

== 数据库连接选择

#align(center)[#image("assets/database-migration.png", width: 88%)]
#v(13pt)
#text(size: 15pt)[空 `DATABASE_URL` 使用 instance SQLite；PostgreSQL 地址统一使用 psycopg 3。容器环境固定连接 `postgres:5432`。]

== 数据库迁移策略

#grid(
  columns: (1fr, 1fr), gutter: 17pt,
  [
    #text(size: 21pt, weight: "bold", fill: blue)[开发数据库]
    #v(7pt)
    #text(size: 15pt)[`init_db()` 创建本地 SQLite 表，支持首次启动和轻量开发。]
    #v(12pt)
    #code-line([python -c "from backend.database import init_db; init_db()"])
  ],
  [
    #text(size: 21pt, weight: "bold", fill: mint)[结构迁移]
    #v(7pt)
    #text(size: 15pt)[数据库结构变化由 Alembic migration 表达，容器启动先执行 `upgrade head`。]
    #v(12pt)
    #code-line([alembic upgrade head])
  ],
)
#v(15pt)
#text(size: 14pt, fill: muted)[基线迁移 `0001_schema_baseline.py` 同时兼容空数据库和已有旧表。]

== 数据模型覆盖业务闭环

#grid(
  columns: (58%, 42%), gutter: 15pt,
  align(center + horizon, image("assets/data-relationships.png", width: 92%)),
  [
    #text(size: 14pt)[
      #tag([用户域], fill: light-blue, color: blue) 身份、地址、收藏、历史  
      #v(8pt)
      #tag([商品域], fill: light-mint, color: mint) 商品、评价、媒体  
      #v(8pt)
      #tag([交易域], fill: light-amber, color: amber) 购物车、订单、订单项  
      #v(8pt)
      #tag([知识域], fill: light-violet, color: violet) 知识条目、问答记录  
      #v(8pt)
      #tag([服务域], fill: light-red, color: red) 生成任务、客服消息
    ]
  ],
)

== 前端运行结构

#align(center)[#image("assets/frontend-runtime.png", width: 91%)]
#v(13pt)
#text(size: 15pt)[App.vue 恢复本地会话并按角色加载布局；业务页面通过 `defineAsyncComponent` 延迟加载。]

== 前端技术职责

#grid(
  columns: (1fr, 1fr), gutter: 15pt,
  card([Ant Design Vue], [表单、菜单、卡片、上传、弹窗和消息反馈。], color: blue),
  card([Tailwind CSS], [页面布局、间距、断点与响应式规则。], color: cyan),
)
#v(12pt)
#grid(
  columns: (1fr, 1fr), gutter: 15pt,
  card([Motion for Vue], [登录、角色切换、页面进入退出与悬浮反馈。], color: violet),
  card([theme.ts], [颜色、圆角、控件高度与动画参数的统一入口。], color: mint),
)

== 同源 API 请求路径

#align(center)[
  #grid(
    columns: (1fr, 38pt, 1fr, 38pt, 1fr), align: horizon,
    card([浏览器], [始终请求相对路径 `/api`。], color: blue),
    text(size: 26pt, fill: muted)[→],
    card([开发环境], [Vite 代理到 `localhost:8000`。], color: cyan),
    text(size: 26pt, fill: muted)[→],
    card([生产环境], [Nginx 代理到 `backend:8000`。], color: mint),
  )
]
#v(18pt)
#block(width: 100%, inset: 14pt, radius: 7pt, fill: pale, stroke: blue.lighten(58%))[
  #text(size: 16pt)[前端镜像不写死后端地址；只有前后端跨域部署时使用 `VITE_API_BASE_URL`。]
]

== 按需加载与导出

#grid(
  columns: (1fr, 1fr, 1fr), gutter: 12pt,
  card([业务页面], [`defineAsyncComponent` 按角色和页面加载代码。], color: blue),
  card([图片导出], [`html2canvas` 仅在导出看板图片时加载。], color: cyan),
  card([表格导出], [`write-excel-file` 仅在导出 XLSX 时加载。], color: mint),
)
#v(18pt)
#text(size: 17pt, weight: "bold", fill: navy)[首屏只包含登录与基础框架，后台页面和导出依赖不进入初始执行路径]

== AI Provider 选择

#grid(
  columns: (1fr, 1fr), gutter: 17pt,
  block(inset: 16pt, radius: 8pt, fill: light-cyan, stroke: cyan.lighten(45%))[
    #text(size: 22pt, weight: "bold", fill: cyan)[Mock]
    #v(8pt)
    #text(size: 15pt)[不依赖外网；输入相同则结果可重复；覆盖文案、推荐、问答、评论分析和直播脚本。]
  ],
  block(inset: 16pt, radius: 8pt, fill: light-blue, stroke: blue.lighten(45%))[
    #text(size: 22pt, weight: "bold", fill: blue)[OpenAI-compatible]
    #v(8pt)
    #text(size: 15pt)[读取 API Key、模型名称和可选 Base URL；业务层通过统一接口调用。]
  ],
)
#v(16pt)
#code-line([AI_PROVIDER=mock | openai])

== RAG 与缓存协作

#align(center)[#image("assets/ai-rag-cache.png", width: 94%)]
#v(12pt)
#text(size: 15pt)[RAG 从商品数据构建候选上下文；Redis 减少重复生成；Redis 连接失败时请求仍走完整业务链路。]

== AI 请求生命周期

#align(center)[#image("assets/ai-flow.png", width: 88%)]
#v(12pt)
#grid(
  columns: (1fr, 1fr, 1fr), gutter: 11pt,
  card([输入], [Pydantic 校验商品、需求和评论参数。], color: blue),
  card([生成], [商品与知识上下文交给 Provider。], color: violet),
  card([结果], [结构化输出写入任务与问答记录。], color: mint),
)

== 容器启动链路

#align(center)[#image("assets/deployment-flow.png", width: 94%)]
#v(12pt)
#text(size: 15pt)[Compose 等待 PostgreSQL 与 Redis 健康；后端执行迁移后启动 Gunicorn；Nginx 统一提供站点与 API。]

== 容器职责

#grid(
  columns: (1fr, 1fr), gutter: 14pt,
  card([postgres], [PostgreSQL 16；数据写入 `postgres_data` volume。], color: mint),
  card([redis], [Redis 7；为重复生成和热点数据提供缓存。], color: amber),
)
#v(11pt)
#grid(
  columns: (1fr, 1fr), gutter: 14pt,
  card([backend], [Alembic + Gunicorn；宿主机绑定 `127.0.0.1:8000`。], color: blue),
  card([frontend], [Nginx 静态站点与反向代理；默认端口 8081。], color: cyan),
)

== 环境变量分组

#text(size: 13.5pt)[#table(
  columns: (22%, 33%, 45%),
  inset: 8pt,
  stroke: rgb("#CBD5E1"),
  fill: (x, y) => if y == 0 { navy } else if calc.even(y) { pale } else { white },
  table.header(
    text(weight: "bold", fill: white)[分组],
    text(weight: "bold", fill: white)[变量],
    text(weight: "bold", fill: white)[作用],
  ),
  [应用], [APP_ENV · APP_PORT · WEB_PORT], [运行模式与服务端口],
  [数据库], [DATABASE_URL], [SQLite 或 PostgreSQL 连接],
  [缓存], [REDIS_URL], [Redis 连接地址],
  [安全], [JWT_SECRET · CORS_ORIGINS], [Token 签名与允许来源],
  [并发], [WEB_CONCURRENCY · GUNICORN_THREADS], [Gunicorn 进程与线程],
  [AI], [AI_PROVIDER · AI_API_KEY], [提供者选择与访问凭据],
  [模型], [AI_MODEL · AI_BASE_URL], [模型名称与兼容接口地址],
)]

== 端口与并发模型

#grid(
  columns: (1fr, 1fr, 1fr), gutter: 12pt,
  metric([8081], [Nginx 对外入口], color: cyan),
  metric([8000], [Flask / Gunicorn], color: blue),
  metric([5432], [PostgreSQL 容器], color: mint),
)
#v(14pt)
#grid(
  columns: (1fr, 1fr), gutter: 15pt,
  card([Gunicorn], [默认 1 个 worker，每个 worker 4 个线程。], color: blue),
  card([网络边界], [数据库与后端端口绑定 127.0.0.1；浏览器只访问 Nginx。], color: red),
)

== 健康检查与运行入口

#grid(
  columns: (1fr, 1fr), gutter: 15pt,
  [
    #text(size: 19pt, weight: "bold", fill: blue)[服务检查]
    #v(8pt)
    #code-line([curl http://localhost:8000/health])
    #v(7pt)
    #code-line([python -m flask --app backend.app routes])
  ],
  [
    #text(size: 19pt, weight: "bold", fill: mint)[容器检查]
    #v(8pt)
    #code-line([docker compose ps])
    #v(7pt)
    #code-line([docker compose logs -f backend])
  ],
)
#v(15pt)
#text(size: 15pt)[`/health` 返回服务版本、运行环境、数据库配置、Redis 配置和 AI Provider 摘要。]

== 运行与维护命令

#grid(
  columns: (1fr, 1fr), gutter: 16pt,
  [
    #text(size: 19pt, weight: "bold", fill: blue)[迁移]
    #v(7pt)
    #code-line([alembic upgrade head])
    #v(6pt)#code-line([alembic current])
    #v(6pt)#code-line([alembic revision --autogenerate])
  ],
  [
    #text(size: 19pt, weight: "bold", fill: cyan)[构建与配置]
    #v(7pt)
    #code-line([npm run build])
    #v(6pt)#code-line([docker compose config --quiet])
    #v(6pt)#code-line([ruff check backend tests migrations scripts])
  ],
)

== 架构特性

#grid(
  columns: (1fr, 1fr, 1fr), gutter: 12pt,
  card([清晰边界], [Nginx、API、数据、缓存和 AI 各自承担单一职责。], color: blue),
  card([环境一致], [开发与容器共享相同 API、模型和配置结构。], color: cyan),
  card([安全隔离], [JWT、角色校验、CORS 与本机端口绑定共同控制访问。], color: red),
)
#v(12pt)
#grid(
  columns: (1fr, 1fr, 1fr), gutter: 12pt,
  card([数据可迁移], [SQLAlchemy 负责映射，Alembic 负责结构版本。], color: mint),
  card([智能可替换], [Mock 与 OpenAI-compatible 共用 Provider 契约。], color: violet),
  card([缓存可降级], [Redis 不可用时业务请求仍能完成。], color: amber),
)

== 总结

#grid(
  columns: (1fr, 1fr, 1fr), gutter: 13pt,
  card([前端], [Vue 单页应用按角色加载，通过同源 `/api` 访问服务。], color: cyan),
  card([后端], [Flask 应用工厂装配蓝图、认证、数据与业务服务。], color: blue),
  card([基础设施], [PostgreSQL、Redis、Nginx 与 Gunicorn 由 Compose 协作。], color: mint),
)
#v(22pt)
#align(center)[
  #text(size: 29pt, weight: "bold", fill: navy)[分层清晰 · 配置集中 · 数据可迁移 · 服务可替换]
  #v(13pt)
  #tag([Q & A], fill: light-blue, color: blue)
]
