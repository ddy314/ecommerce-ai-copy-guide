# 电商 AI 商品文案生成与智能导购助手

面向电商运营与购物场景的全栈课程项目，包含商品采集、AI 文案、智能导购、评论分析、直播脚本、订单售后、知识库和客服管理。

## 当前技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3、TypeScript、Vite 8、Tailwind CSS、Ant Design Vue、Motion for Vue |
| 后端 | Flask 3、Pydantic 2、SQLAlchemy 2、Flask-JWT-Extended、Flask-CORS |
| 数据 | PostgreSQL 16、Redis 7、Alembic；本地开发可使用 SQLite |
| AI | OpenAI 兼容接口或无需密钥的 Mock AI |
| 部署 | Docker Compose、Gunicorn、Nginx |

后端只有一个入口 `backend.app`；前端与后端在生产环境通过 Nginx 同源访问，不需要硬编码 API 地址。

## 功能

- 商家端：营收看板、商品/订单/用户管理、知识库、问答统计、客服会话。
- AI 工具：商品文案、导购推荐、评论情感分析、直播脚本。
- 用户端：商品浏览、购物车、订单、地址、收藏、评价、售后和智能问答。
- 数据采集：京东、苏宁商品与评论任务。
- 导出：运营看板 JPG、数据表 XLSX、评论分析报告。

## 一键启动（推荐）

要求 Docker Engine/Desktop 与 Docker Compose。

```bash
# 可选：需要真实 AI 或自定义密码时再创建
cp .env.example .env

docker compose up --build -d
docker compose ps
```

访问：

- 应用：<http://localhost:8081>
- 后端健康检查：<http://localhost:8000/health>
- API 文档：<http://localhost:8000/api/docs>

Compose 会启动 PostgreSQL、Redis、Flask/Gunicorn 和 Nginx。后端容器在启动前自动执行 `alembic upgrade head`。

常用命令：

```bash
docker compose logs -f backend  # 查看后端日志
docker compose up --build -d    # 重新构建
docker compose down             # 停止，保留数据库 volume
```

> `docker compose down -v` 会删除 PostgreSQL 数据，仅在确认不再需要数据时使用。

## 本地开发

要求：

- Python 3.11+
- Node.js `^20.19.0` 或 `>=22.12.0`
- 可选 PostgreSQL 16、Redis 7

### 1. 后端

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
```

快速演示可以不创建 `.env`：后端会使用 `instance/ecommerce_ai.db` 和 Mock AI。若需要 PostgreSQL、Redis 或真实 AI，再执行：

```bash
cp .env.example .env
docker compose up postgres redis -d
```

初始化并启动：

```bash
alembic upgrade head
python -m flask --app backend.app run --host=0.0.0.0 --port=8000
```

### 2. 前端

另开终端：

```bash
cd frontend
npm ci
npm run dev
```

访问 <http://localhost:5173>。Vite 自动把 `/api` 与 `/health` 转发到 8000；只有后端位于其他地址时才需要在 `frontend/.env.local` 配置 `VITE_API_BASE_URL`。

## 默认演示账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 商家 | `merchant` | `merchant123` |
| 用户 | `user` | `user123` |

默认账号只用于本地演示，不应直接用于公网部署。

## 配置

完整模板见 [.env.example](.env.example)。常用变量：

| 变量 | 用途 |
|---|---|
| `APP_PORT` / `WEB_PORT` | 后端与 Nginx 宿主机端口 |
| `POSTGRES_DB/USER/PASSWORD` | Compose PostgreSQL 配置 |
| `DATABASE_URL` | 本地运行时的数据库地址 |
| `REDIS_URL` | Redis 地址 |
| `JWT_SECRET` | JWT 签名密钥，生产必须替换为随机长字符串 |
| `CORS_ORIGINS` | 逗号分隔的跨域来源白名单 |
| `AI_PROVIDER` | `mock` 或 `openai` |
| `AI_API_KEY` / `AI_MODEL` | 真实 AI 服务凭据与模型 |
| `AI_BASE_URL` | 可选 OpenAI 兼容服务地址 |

真实 AI 示例：

```env
AI_PROVIDER=openai
AI_API_KEY=sk-your-api-key
AI_MODEL=gpt-4o-mini
# AI_BASE_URL=https://your-compatible-endpoint/v1
```

没有配置 API Key 时使用 Mock AI，核心流程仍可离线演示。

## 项目结构

```text
.
├── backend/
│   ├── api/                 # Flask 蓝图
│   ├── crawler/             # 采集任务
│   ├── docs/                # OpenAPI 文档
│   ├── models/              # SQLAlchemy 模型
│   ├── schemas/             # Pydantic 模型
│   ├── services/            # AI、RAG、认证、上传等服务
│   ├── app.py               # Flask 应用工厂与唯一入口
│   ├── database.py          # Engine / Session
│   └── extensions.py        # JWT / CORS
├── frontend/                # Vue 应用与前端镜像
├── migrations/              # Alembic migrations
├── scripts/                 # 容器启动和维护脚本
├── tests/                   # 后端自动化测试
├── docs/                    # 架构说明、生成报告、交付材料
├── docker-compose.yml
├── Dockerfile
├── requirements.txt         # 生产依赖
└── requirements-dev.txt     # 测试与静态检查依赖
```

进一步说明：

- [系统架构与维护说明](docs/architecture.md)
- [前端开发说明](frontend/README.md)
- [文档目录说明](docs/README.md)

## 数据库迁移

模型结构变化必须创建 Alembic migration：

```bash
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
alembic current
```

`backend.database.init_db()` 仅用于保证本地 SQLite 首次启动可用，不代替生产迁移。

## 爬虫

爬虫属于 Flask 后端，不需要单独启动第二套服务。商家登录后使用：

- `GET /api/crawl/preset-keywords`
- `POST /api/crawl/start`
- `GET /api/crawl/status/<task_id>`
- `GET /api/crawl/tasks`

目标网站结构或反爬规则变化时，采集结果可能需要重新适配。

## 验证

```bash
# 后端
python -m pytest -q
ruff check backend tests migrations scripts
python -m flask --app backend.app routes

# 数据库迁移
alembic upgrade head
alembic current

# 前端
cd frontend
npm run build
npm audit
cd ..

# 部署配置
docker compose config --quiet
```

## Git 与本地产物

以下内容已在 `.gitignore` 中排除：

- `.env`、虚拟环境、Node/Python 缓存和构建产物。
- SQLite、SQL/Dump 备份和运行日志。
- `backend/uploads/` 中的用户上传文件。
- `docs/submission/` 中的本地课程提交材料。
- `data/backups/` 中的数据库备份。

生成的静态技术报告统一放在 `docs/generated/`，维护脚本统一放在 `scripts/maintenance/`，不要在根目录新增临时文件。

## 许可证

本项目仅供课程教学与演示使用。
