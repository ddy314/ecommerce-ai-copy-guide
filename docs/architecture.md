# 系统架构与维护说明

本文档描述当前仓库中的实际实现。运行步骤优先参考根目录 [README](../README.md)，接口细节以 Flask 路由和 `/api/docs/openapi.json` 为准。

## 1. 系统边界

系统由一个 Vue 单页应用、一个 Flask API 服务、PostgreSQL 和 Redis 组成。开发环境可以不配置 PostgreSQL，此时后端使用 `instance/ecommerce_ai.db`；容器部署固定使用 PostgreSQL。

```text
浏览器
  └─ Nginx :8080
      ├─ /                -> Vue 静态文件
      ├─ /api/*           -> Flask :8000
      └─ /health          -> Flask :8000
                              ├─ PostgreSQL :5432
                              ├─ Redis :6379
                              └─ OpenAI 兼容接口 / Mock AI
```

## 2. 技术栈

| 层 | 实现 |
|---|---|
| 前端 | Vue 3、TypeScript、Vite 8、Tailwind CSS、Ant Design Vue、Motion for Vue |
| API | Flask 3、Pydantic 2、Gunicorn |
| 认证与跨域 | Flask-JWT-Extended、Werkzeug 密码哈希、Flask-CORS |
| 数据 | SQLAlchemy 2、Alembic、PostgreSQL 16；本地可使用 SQLite |
| 缓存 | Redis 7；不可用时业务逻辑回退到无缓存运行 |
| 爬虫 | Requests、Beautiful Soup |
| AI | OpenAI 兼容客户端或确定性 Mock 实现 |
| 部署 | Docker Compose、Nginx、Gunicorn |

## 3. 目录职责

```text
backend/
├── api/             # Flask 蓝图；按认证、用户、商家、客服、爬虫拆分
├── crawler/         # 京东/苏宁采集和任务管理
├── docs/            # OpenAPI JSON 与文档页面
├── models/          # SQLAlchemy 模型
├── schemas/         # Pydantic 请求/响应模型
├── services/        # AI、RAG、认证、上传等业务服务
├── app.py           # 应用工厂和唯一后端入口
├── config.py        # 环境变量配置
├── database.py      # Engine、Session 和兼容性 init_db
└── extensions.py    # JWT 与 CORS 扩展初始化
frontend/            # Vue 应用与 Nginx 镜像
migrations/          # Alembic 版本迁移
scripts/
├── start-backend.sh # 容器迁移 + Gunicorn 启动入口
└── maintenance/     # 人工运行的数据维护工具
tests/               # API、认证与配置测试
docs/
├── generated/       # 生成的静态报告
└── submission/      # 本地交付材料，不进入 Git
```

## 4. 后端启动过程

`backend.app:create_app()` 执行以下工作：

1. 从环境变量构造 `AppConfig`。
2. 绑定 Flask-JWT-Extended 和 Flask-CORS。
3. 注册健康检查、错误处理器和全部 API 蓝图。
4. 调用 `init_db()` 保证本地 SQLite 首次运行可用。
5. 若默认演示账号不存在则创建账号。

生产启动脚本会先运行 `alembic upgrade head`，再由 Gunicorn 加载 `backend.app:app`。结构变更必须新增 Alembic migration，不能把 `init_db()` 当作生产迁移工具。

蓝图在 `backend/api/__init__.py` 的 `BLUEPRINTS` 中集中注册：

- `api_bp`：AI 能力、商品、评论与统计。
- `auth_bp`：登录、注册、资料和头像。
- `merchant_bp`：商品、知识库、订单、用户和运营看板。
- `user_bp`：购物车、订单、地址、收藏、浏览历史和问答。
- `crawl_bp`：采集任务。
- `cs_bp`：用户与商家的客服会话。

## 5. 认证与权限

登录成功后，后端签发 24 小时有效的 Bearer JWT。受保护接口从 `Authorization: Bearer <token>` 读取凭据；商家接口还会验证 `role=merchant`。

密码只保存 Werkzeug `scrypt` 哈希。认证服务保留旧 SHA-256 密码格式的验证逻辑，仅用于兼容已有数据库；新密码不会再按旧格式写入。

生产环境必须设置至少 32 字符的随机 `JWT_SECRET`，并将 `CORS_ORIGINS` 限制为实际前端域名。

## 6. 数据库与迁移

数据库地址由 `DATABASE_URL` 控制：

- 未设置：`instance/ecommerce_ai.db`。
- `postgresql://...`：自动规范化为 psycopg 3 驱动地址。
- Compose：使用容器内 `postgres:5432`。

常用迁移命令：

```bash
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe_change"
```

首次基线迁移位于 `migrations/versions/0001_schema_baseline.py`，兼容空数据库和旧版已有表。PostgreSQL 不可用时不会悄悄切换到 SQLite，避免误写另一个数据库。

## 7. 前端架构

`App.vue` 负责恢复本地会话并按角色加载商家或用户布局。各业务页面通过 `defineAsyncComponent` 延迟加载，避免登录页下载完整后台代码。

界面约定：

- Ant Design Vue：表单、菜单、卡片、上传、消息反馈等标准交互。
- Tailwind CSS：页面布局、间距和响应式规则。
- Motion for Vue：登录、角色切换、页面进入退出和悬浮反馈。
- `theme.ts`：颜色、圆角、控件高度与动画参数的唯一主题入口。
- `api.ts`：通用 JSON 请求、错误处理和 API 基址。

开发时请求使用同源 `/api`，由 Vite 转发到 8000；生产环境由 Nginx 转发，因此不需要在镜像中写死后端地址。只有前后端跨域部署时才需要 `VITE_API_BASE_URL`。

导出功能按需加载：图片看板使用 `html2canvas`，XLSX 使用 `write-excel-file`。两者不会进入首屏执行路径。

## 8. AI、RAG 与缓存

AI 服务根据 `AI_PROVIDER` 选择提供者：

- 未配置或设置为 `mock`：返回可重复的演示结果，不依赖外网。
- 设置为 `openai`：读取 `AI_API_KEY`、`AI_MODEL` 和可选 `AI_BASE_URL`。

RAG 导购从商品数据构建候选上下文，再交给 AI 服务生成回答。Redis 用于减少重复生成；连接失败时请求仍可继续，只是不使用缓存。

## 9. 部署流程

```bash
cp .env.example .env       # 可选；正式环境必须修改密钥和密码
docker compose up --build -d
docker compose ps
docker compose logs -f backend
```

容器职责：

- `postgres`：持久化到 `postgres_data` volume。
- `redis`：缓存服务。
- `backend`：Alembic 后运行 Gunicorn，仅绑定宿主机 `127.0.0.1:8000`。
- `frontend`：Nginx 静态站点和反向代理，默认暴露 8080。

停止服务：

```bash
docker compose down
```

仅在明确需要删除数据库数据时使用 `docker compose down -v`。

## 10. 环境变量

| 变量 | 默认/用途 |
|---|---|
| `APP_ENV` | `development`；容器内为 `production` |
| `APP_PORT` | 后端宿主机端口，默认 8000 |
| `WEB_PORT` | Nginx 暴露端口，默认 8080 |
| `DATABASE_URL` | 本地数据库连接；空值使用 instance SQLite |
| `REDIS_URL` | Redis 连接地址 |
| `JWT_SECRET` | JWT 签名密钥；生产必须替换 |
| `CORS_ORIGINS` | 逗号分隔的允许来源 |
| `WEB_CONCURRENCY` | Gunicorn worker 数，默认 1 |
| `GUNICORN_THREADS` | 每个 worker 线程数，默认 4 |
| `AI_PROVIDER` | `mock` 或 `openai` |
| `AI_API_KEY` | 真实 AI 服务密钥 |
| `AI_MODEL` | 模型名称 |
| `AI_BASE_URL` | 可选 OpenAI 兼容地址 |

## 11. 验证清单

提交代码前执行：

```bash
python -m pytest -q
ruff check backend tests migrations scripts
alembic current
cd frontend
npm run build
npm audit
cd ..
docker compose config --quiet
```

快速运行检查：

```bash
curl http://localhost:8000/health
python -m flask --app backend.app routes
```

## 12. 已知边界

- OpenAPI 页面覆盖核心公共 AI 接口，并非所有商家和用户接口的完整契约；新增接口时应同步补充。
- 默认账号仅用于本地演示，不应保留在公网环境。
- 生成报告可能包含自带字体和压缩后的脚本，统一保存在 `docs/generated/`，不要放回项目根目录。
