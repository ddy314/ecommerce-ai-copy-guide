# ecommerce-ai-copy-guide

> 面向电商运营的 AI 智能文案、导购推荐与客服工作台。项目采用前后端分离架构：前端基于 Vue 3 + Vite + Tailwind CSS，后端基于 Flask + SQLAlchemy + Redis，支持 PostgreSQL/SQLite 双数据库以及 DeepSeek/OpenAI/Mock AI 多模型切换。

---

## 1. 项目简介

`ecommerce-ai-copy-guide` 是一个面向电商场景的 AI 辅助运营系统，核心目标是用大模型能力帮助商家和普通用户完成商品文案生成、智能导购问答、评论情感分析、直播脚本生成、商品爬虫采集、订单与售后管理、智能客服等完整业务流程。

系统内置两种角色：

- **普通用户（user）**：浏览商品、加购下单、查看订单、联系客服、收藏商品。
- **商家管理员（merchant）**：管理商品上下架、管理订单与售后、维护知识库、查看营收数据、处理客服消息、管理普通用户。

后端启动时会自动初始化数据库表结构，并创建两个默认测试账号：

- 商家：`merchant / merchant123`
- 用户：`user / user123`

相关初始化逻辑见 `backend/app.py`：

```python
# backend/app.py
merchant = User(
    username="merchant",
    password_hash=hash_password("merchant123"),
    nickname="商家管理员",
    role="merchant",
)
user = User(
    username="user",
    password_hash=hash_password("user123"),
    nickname="测试用户",
    role="user",
)
```

### 主要功能列表

| 模块 | 功能说明 | 对应后端文件 |
|---|---|---|
| 认证中心 | 登录/注册/找回密码/资料修改/头像上传 | `backend/api/auth_routes.py` |
| AI 文案生成 | 输入商品信息，自动生成小红书、淘宝、抖音等不同风格文案 | `backend/api/routes.py` |
| 智能导购推荐 | 根据用户需求和预算推荐商品 | `backend/api/routes.py` |
| 导购问答 | 回答尺码、功能、搭配、售后等商品相关问题 | `backend/api/routes.py` |
| 跨商品关联推荐 | 基于用户偏好推荐关联商品 | `backend/api/routes.py` |
| 评论情感分析 | 自动分析评论情感倾向、关键词与改进建议 | `backend/api/routes.py` |
| 直播脚本生成 | 根据商品卖点一键生成直播/短视频脚本 | `backend/api/routes.py` |
| 商品管理 | 商品 CRUD、上下架、多图/视频、分类统计 | `backend/api/merchant_routes.py`、`backend/repositories/product_repo.py` |
| 订单管理 | 下单、支付、发货、退货、售后全流程 | `backend/api/user_routes.py`、`backend/models/shopping.py` |
| 智能客服 | 基于 RAG 知识库的商家客服问答 | `backend/api/customer_service_routes.py`、`backend/services/rag_service.py` |
| 商品爬虫 | 支持京东、苏宁等平台的商品数据采集 | `backend/crawler/` |
| 文件上传 | 头像、商品图/视频等静态资源服务 | `backend/app.py`、`backend/services/file_upload.py` |

---

## 2. 技术栈

| 层级 | 技术选型 | 说明 |
|---|---|---|
| 前端框架 | Vue 3 + TypeScript | 组合式 API，单文件组件 |
| 前端构建 | Vite 8 | 开发服务器与生产构建 |
| 前端样式 | Tailwind CSS 3 + PostCSS + Autoprefixer | 原子化 CSS |
| 前端图标 | @heroicons/vue | Heroicons SVG 图标 |
| 前端表格/截图 | xlsx、html2canvas | Excel 导出与页面截图 |
| 后端框架 | Flask 2/3 | Python Web 框架 |
| ORM | SQLAlchemy 2.x | 数据库模型与迁移兼容 |
| 数据库 | PostgreSQL / SQLite | 优先 PostgreSQL，无配置时降级 SQLite |
| 缓存 | Redis | 商品列表、详情、评论、统计缓存 |
| AI 接入 | DeepSeek / OpenAI / Mock | 未配置 API Key 时自动使用 Mock 服务 |
| 向量检索 | ChromaDB | RAG 知识库向量存储 |
| 爬虫 | Scrapy | 电商商品数据采集 |
| 文档导出 | openpyxl、python-docx | Excel/Word 导出 |
| 代码规范 | ruff | Python 代码检查与格式化 |
| 测试 | pytest | 单元与接口测试 |

注意：`requirements.txt` 中同时包含 `FastAPI` 与 `uvicorn`，但实际入口文件 `backend/app.py` 使用 Flask 构建并注册蓝图；项目根目录下还存在 `backend/fastapi_app.py`，可作为 FastAPI 的备用入口。

---

## 3. 目录结构

```
c:\Users\Jin\Desktop\ecommerce-ai-copy-guide-main
├── backend/
│   ├── api/                    # Flask 蓝图路由
│   │   ├── auth_routes.py      # 认证：登录/注册/找回密码/头像
│   │   ├── crawl_routes.py     # 爬虫任务接口
│   │   ├── customer_service_routes.py  # 智能客服
│   │   ├── merchant_routes.py  # 商家后台接口
│   │   ├── routes.py           # AI 文案/导购/评论/脚本/商品查询
│   │   └── user_routes.py      # 用户购物、订单、售后接口
│   ├── crawler/                # 电商爬虫实现
│   │   ├── crawl_manager.py
│   │   ├── jd_crawler.py
│   │   ├── suning_crawler.py
│   │   └── proxy_config.py
│   ├── docs/
│   │   └── openapi.py          # OpenAPI 文档蓝图
│   ├── models/                 # SQLAlchemy 数据模型
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── review.py
│   │   ├── shopping.py
│   │   ├── customer_service.py
│   │   ├── knowledge_base.py
│   │   ├── generation_task.py
│   │   └── recommendation_log.py
│   ├── repositories/           # 数据访问层
│   │   ├── product_repo.py
│   │   └── review_repo.py
│   ├── schemas/                # Pydantic 请求/响应模型
│   │   └── requests.py
│   ├── services/               # 业务服务层
│   │   ├── ai_provider.py      # AI 提供商路由
│   │   ├── ai_mock.py          # Mock AI 兜底服务
│   │   ├── deepseek_provider.py
│   │   ├── openai_provider.py
│   │   ├── rag_service.py      # RAG 客服
│   │   ├── vector_index.py
│   │   ├── auth_service.py     # 密码哈希、Token 生成
│   │   └── file_upload.py
│   ├── utils/                  # 工具函数
│   │   └── helpers.py
│   ├── __init__.py
│   ├── app.py                  # Flask 应用入口
│   ├── cache.py                # Redis 缓存封装
│   ├── config.py               # 配置读取
│   ├── database.py             # 数据库引擎、会话、迁移兼容
│   ├── fastapi_app.py          # FastAPI 备用入口
│   ├── seed_data.py            # 种子数据
│   └── test_api.py             # 后端接口测试
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/         # Vue 组件
│   │   │   ├── common/         # ChatWidget、NavBar、SideBar
│   │   │   ├── merchant/       # 商家后台页面
│   │   │   ├── user/           # 用户端页面
│   │   │   ├── ui/             # 通用 UI 组件
│   │   │   ├── CopyGenerator.vue
│   │   │   ├── GuideRecommender.vue
│   │   │   ├── LiveScriptGenerator.vue
│   │   │   ├── Login.vue
│   │   │   ├── ProductList.vue
│   │   │   └── ReviewAnalyzer.vue
│   │   ├── utils/
│   │   ├── App.vue
│   │   ├── api.ts              # 前端 API 封装
│   │   ├── main.ts
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── vite.config.ts
│   └── tsconfig*.json
├── tests/
│   └── test_api.py             # 项目级测试
├── .env.example                # 环境变量示例
├── requirements.txt            # Python 依赖
├── pyproject.toml              # Python 项目配置
├── docker-compose.yml          # Docker 编排
├── Dockerfile                  # 容器构建
├── ecommerce_ai.db             # 默认 SQLite 数据库（如已生成）
├── chroma_db/                  # ChromaDB 向量库
└── README.md                   # 本文件
```

---

## 4. 环境安装与启动

### 4.1 准备 Conda 环境

建议在项目根目录下创建并激活一个独立 Python 环境：

```powershell
# 创建环境（Python 3.12/3.13 均可，项目已验证 3.12/3.13）
conda create -n ecommerce-ai python=3.12 -y

# 激活环境
conda activate ecommerce-ai

# 安装后端依赖
pip install -r requirements.txt
```

### 4.2 配置环境变量

复制示例文件并根据实际情况修改：

```powershell
copy .env.example .env
```

`.env.example` 关键配置如下：

```env
# ===== 应用配置 =====
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000

# ===== 数据库配置 =====
DATABASE_URL=postgresql://ecommerce_ai:ecommerce_ai_password@localhost:5432/ecommerce_ai

# ===== Redis 配置 =====
REDIS_URL=redis://localhost:6379/0

# ===== AI 服务配置 =====
# 默认优先使用 DeepSeek；未配置 AI_API_KEY 或调用失败时自动使用 Mock AI
AI_PROVIDER=deepseek
AI_API_KEY=your-deepseek-api-key
AI_MODEL=deepseek-v4-pro
# AI_BASE_URL=https://api.deepseek.com/v1

# 也可选用 OpenAI
# AI_PROVIDER=openai
# AI_API_KEY=sk-your-api-key
# AI_MODEL=gpt-4o-mini
# AI_BASE_URL=https://your-proxy.com/v1
```

### 4.3 启动后端服务

在 Conda 环境激活状态下，从项目根目录执行：

```powershell
# 方式一：使用 Python 模块运行（推荐）
py -3 -m backend.app

# 方式二：直接运行文件
python backend/app.py
```

`backend/app.py` 的核心启动逻辑如下：

```python
# backend/app.py
app = create_app()

if __name__ == "__main__":
    config = AppConfig.from_env()
    logger.info(f"启动服务: {config.app_host}:{config.app_port}")
    app.run(host=config.app_host, port=config.app_port, debug=(config.app_env == "development"))
```

服务默认监听 `0.0.0.0:8000`，可通过环境变量 `APP_HOST` 与 `APP_PORT` 修改。首次启动会自动创建数据表，并在控制台输出如下日志：

```text
数据库表初始化完成
已创建默认商家账号: merchant / merchant123
已创建默认用户账号: user / user123
应用初始化完成，已注册全部蓝图: API + 认证 + 商家 + 用户 + 客服
```

### 4.4 启动前端服务

打开新的终端，进入 `frontend` 目录：

```powershell
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

`frontend/package.json` 中的脚本定义如下：

```json
{
  "name": "ecommerce-ai-copy-guide-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "html2canvas": "^1.4.1",
    "vue": "^3.5.39",
    "xlsx": "^0.18.5"
  },
  "devDependencies": {
    "@heroicons/vue": "^2.2.0",
    "@types/node": "^24.13.2",
    "@vitejs/plugin-vue": "^6.0.7",
    "@vue/tsconfig": "^0.9.1",
    "autoprefixer": "^10.5.2",
    "postcss": "^8.5.19",
    "tailwindcss": "^3.4.19",
    "typescript": "~6.0.2",
    "vite": "^8.1.1",
    "vue-tsc": "^3.3.5"
  }
}
```

`npm run dev` 默认会在 `http://localhost:5173` 启动前端开发服务器。前端 API 请求目标地址默认为 `http://localhost:8000`，若后端端口不同，请在 `frontend/src/api.ts` 中调整 `BASE_URL`。

---

## 5. 关键环境变量说明

| 变量名 | 默认值/示例 | 说明 |
|---|---|---|
| `APP_ENV` | `development` | 运行环境，`development` 会开启调试日志与 Flask debug 模式 |
| `APP_HOST` | `0.0.0.0` | 后端服务监听地址 |
| `APP_PORT` | `8000` | 后端服务监听端口 |
| `DATABASE_URL` | `postgresql://...` | 数据库连接串；留空或不配置则自动降级为 SQLite `sqlite:///./ecommerce_ai.db` |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串；不可用时会跳过缓存，不影响核心功能 |
| `AI_PROVIDER` | `deepseek` | AI 提供商，可选 `deepseek`、`openai` |
| `AI_API_KEY` | `your-deepseek-api-key` | 对应平台的 API Key；未配置时自动降级到 Mock AI |
| `AI_MODEL` | `deepseek-v4-pro` | 模型名称，例如 `gpt-4o-mini` |
| `AI_BASE_URL` | `https://api.deepseek.com/v1` | 自定义 API 基础地址，用于代理或私有部署 |

关于数据库降级逻辑，可参考 `backend/database.py`：

```python
# backend/database.py
def _resolve_database_url() -> str:
    configured_url = os.getenv("DATABASE_URL", "")

    if not configured_url:
        logger.info("未配置 DATABASE_URL，使用 SQLite: ./ecommerce_ai.db")
        return "sqlite:///./ecommerce_ai.db"

    if configured_url.startswith("sqlite"):
        return configured_url

    if configured_url.startswith("postgresql"):
        try:
            import psycopg2
            engine = create_engine(configured_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            logger.info("使用 PostgreSQL 数据库")
            return configured_url
        except ImportError:
            logger.warning("psycopg2 未安装，降级使用 SQLite: ./ecommerce_ai.db")
            return "sqlite:///./ecommerce_ai.db"
        except Exception as e:
            logger.warning(f"PostgreSQL 连接失败 ({e})，降级使用 SQLite: ./ecommerce_ai.db")
            return "sqlite:///./ecommerce_ai.db"

    return configured_url
```

---

## 6. 示例 API 调用

以下示例使用 `curl` 在 PowerShell 中执行，后端服务默认运行在 `http://localhost:8000`。

### 6.1 登录

#### 普通用户登录

```powershell
curl -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username": "user", "password": "user123", "role": "user"}'
```

#### 商家管理员登录

```powershell
curl -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username": "merchant", "password": "merchant123", "role": "merchant"}'
```

#### 登录成功响应示例

```json
{
  "message": "登录成功",
  "user": {
    "id": 2,
    "username": "user",
    "nickname": "测试用户",
    "role": "user",
    "avatar": null,
    "phone": null,
    "email": null,
    "is_active": true,
    "display_id": "2026071500000002",
    "created_at": "2026-07-15T08:00:00"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

登录接口核心代码见 `backend/api/auth_routes.py`：

```python
# backend/api/auth_routes.py
@auth_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"error": "invalid_input", "message": "账号和密码不能为空"}), 400

    with SessionLocal() as db:
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if not user:
            return jsonify({"error": "not_found", "message": "账号不存在"}), 404

        if not verify_password(password, user.password_hash):
            return jsonify({"error": "wrong_password", "message": "密码错误"}), 401

        if not user.is_active:
            return jsonify({"error": "disabled", "message": "账号已被禁用"}), 403

        if role and role != user.role:
            return jsonify({
                "error": "role_mismatch",
                "message": f"该账号是{'商家管理员' if user.role == 'merchant' else '普通用户'}，请切换身份登录"
            }), 403

        token = create_token(user.id, user.username, user.role)
        user_data = user.to_dict()
        user_data["token"] = token

        return jsonify({
            "message": "登录成功",
            "user": user_data,
            "token": token,
        })
```

### 6.2 获取商品列表

```powershell
curl -X GET "http://localhost:8000/api/products?page=1&page_size=10"
```

#### 响应示例

```json
{
  "total": 25,
  "page": 1,
  "page_size": 10,
  "total_pages": 3,
  "categories": ["手机", "笔记本电脑", "耳机"],
  "category_counts": {
    "手机": 12,
    "笔记本电脑": 8,
    "耳机": 5
  },
  "products": [
    {
      "id": 1,
      "platform": "manual",
      "product_id": "",
      "name": "示例智能手机",
      "category": "手机",
      "price": 2999.0,
      "original_price": 3299.0,
      "brand": "示例品牌",
      "selling_points": "高性能芯片、长续航、拍照清晰",
      "image_url": "",
      "image_urls": [],
      "videos": [],
      "detail_url": "",
      "source_url": "",
      "specs": "...",
      "sales_count": 0,
      "rating": 5.0,
      "review_count": 0,
      "display_id": "00001",
      "is_published": true,
      "created_at": "2026-07-15T08:00:00"
    }
  ]
}
```

商品列表接口核心代码见 `backend/api/routes.py`：

```python
# backend/api/routes.py
@api_bp.get("/products")
def list_products():
    category = request.args.get("category")
    keyword = request.args.get("keyword")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    limit = page_size
    offset = (page - 1) * page_size

    cache_key = f"products:list:{category or 'all'}:{keyword or ''}:{page}:{page_size}"
    cached = cache.get(cache_key)
    if cached:
        return jsonify(cached)

    with SessionLocal() as db:
        repo = ProductRepository(db)
        if keyword:
            products = repo.search(keyword, limit, offset)
            total = len(repo.search(keyword, limit=9999, offset=0))
        else:
            products = repo.list_all(category, limit, offset)
            total = repo.count(category)

        categories = repo.list_categories()
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
        category_counts = {cat: repo.count(cat) for cat in categories}

        result = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "categories": categories,
            "category_counts": category_counts,
            "products": [p.to_dict() for p in products],
        }

    cache.set(cache_key, result, ttl=1800)
    return jsonify(result)
```

### 6.3 获取商品详情

```powershell
curl -X GET http://localhost:8000/api/products/1
```

### 6.4 获取服务能力清单

```powershell
curl -X GET http://localhost:8000/api/capabilities
```

响应包含所有 AI 功能入口：

```json
{
  "mode": "mock",
  "provider": "AIMockProvider",
  "features": [
    {"key": "copy_generation", "name": "商品文案生成", "endpoint": "/api/copy/generate"},
    {"key": "shopping_guide", "name": "智能导购推荐", "endpoint": "/api/guide/recommend"},
    {"key": "guide_qa", "name": "智能导购问答", "endpoint": "/api/guide/qa"},
    {"key": "cross_recommend", "name": "跨商品关联推荐", "endpoint": "/api/guide/cross-recommend"},
    {"key": "review_analysis", "name": "评论情感分析", "endpoint": "/api/reviews/analyze"},
    {"key": "live_script", "name": "直播脚本生成", "endpoint": "/api/scripts/live"}
  ]
}
```

---

## 7. 健康检查

服务启动后，可访问健康检查接口确认状态：

```powershell
curl -X GET http://localhost:8000/health
```

`backend/app.py` 中定义了该接口：

```python
# backend/app.py
@app.get("/health")
def health() -> tuple[dict[str, object], int]:
    return {
        "status": "ok",
        "service": "ecommerce-ai-copy-guide",
        "version": "0.2.0",
        "runtime": app_config.public_summary(),
    }, 200
```

---

## 8. 开发提示

1. **端口冲突**：若 `8000` 或 `5173` 被占用，请分别修改 `.env` 中的 `APP_PORT` 与 `frontend/vite.config.ts` 中的 `server.port`。
2. **数据库**：本地开发可直接使用 SQLite，无需安装 PostgreSQL；生产环境建议使用 PostgreSQL 并正确配置 `DATABASE_URL`。
3. **Redis**：Redis 用于缓存商品列表、详情与评论数据，未启动 Redis 时系统会跳过缓存，仍可正常运行。
4. **AI Key**：未配置 `AI_API_KEY` 时，系统会自动调用 `backend/services/ai_mock.py` 返回示例文案，方便快速体验。

5. **静态资源**：上传的头像、商品图等文件保存在 `backend/uploads/`，通过 `/uploads/<path:filename>` 访问。
6. **跨域**：后端通过 `after_request` 统一添加 CORS 响应头，允许前端跨域访问。

---

## 9. 近期问题修复

### 9.1 AI 智能导购无法回答退换货问题

`backend/services/rag_service.py` 中的 `_build_no_match_answer` 现在会在未匹配到商品时识别售后关键词，直接返回平台通用售后政策：

```python
# backend/services/rag_service.py
if q_type == "after_sale" or any(kw in question for kw in ["退", "换", "售后", "保修", "质保", "运费", "发票"]):
    return (
        "平台售后政策如下：\n"
        "• 支持 7 天无理由退货（商品需保持完好、配件齐全）；\n"
        "• 支持 15 天无理由换货（同款同规格优先，库存不足时协商退款）；\n"
        "• 质量问题 30 天内包退换，运费由商家承担；\n"
        "• 非质量问题退货运费由买家承担；\n"
        "• 数码/家电类商品一般提供 1 年质保，具体以商品详情页为准；\n\n"
        "操作流程：进入「个人中心」→「我的订单」→选择对应订单→点击「申请售后」→填写原因并提交。\n"
        "如需人工介入，请在客服页面留言，商家会在工作时间内处理。"
    )
```

当问题命中商品且被识别为 `after_sale` 时，系统会在 `answer_question` 中清空相关推荐，避免给用户展示无关商品：

```python
# backend/services/rag_service.py
# 售后/退换货问题只回答政策，不展示可能不相关的推荐商品
if q_type == "after_sale":
    related_products = []
```

### 9.2 商家端客服回复 HTTP 500

问题根因是 `require_merchant` 返回的是 token payload 字典，原代码错误地按对象访问 `merchant.id`。修复方式是在 `backend/api/customer_service_routes.py` 中根据 `merchant["user_id"]` 查询真实的 `User` 对象，再用其 `id` 作为 `sender_id`：

```python
# backend/api/customer_service_routes.py
merchant_user = db.get(User, merchant["user_id"])
if not merchant_user:
    return jsonify({"error": "not_found", "message": "商家账号不存在"}), 404

msg = CustomerServiceMessage(
    user_id=user_id,
    product_id=product_id,
    sender_id=merchant_user.id,
    sender_role="merchant",
    content=content,
    is_read=True,
)
```

### 9.3 商家端用户删除失败

由于外键约束，删除存在订单、收藏、地址等关联数据的用户会直接失败。`backend/api/merchant_routes.py` 在删除用户前按顺序清理关联数据：

```python
# backend/api/merchant_routes.py
db.execute(delete(CartItem).where(CartItem.user_id == user_id))
db.execute(delete(UserFavorite).where(UserFavorite.user_id == user_id))
db.execute(delete(BrowseHistory).where(BrowseHistory.user_id == user_id))
db.execute(delete(UserAddress).where(UserAddress.user_id == user_id))
db.execute(delete(CustomerServiceMessage).where(CustomerServiceMessage.user_id == user_id))
db.execute(update(QARecord).where(QARecord.user_id == user_id).values(user_id=None))
db.execute(update(Review).where(Review.user_id == user_id).values(user_id=None))

order_ids = [row[0] for row in db.execute(select(Order.id).where(Order.user_id == user_id)).all()]
if order_ids:
    db.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
    db.execute(delete(Order).where(Order.id.in_(order_ids)))

db.delete(target_user)
db.commit()
```

同时前端 `UserManage.vue` 对删除按钮做了确认弹窗，删除成功后自动刷新列表：

```ts
// frontend/src/components/merchant/UserManage.vue
async function handleDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    const res = await fetch(`${API_BASE}/api/merchant/users/${deleteTarget.value.id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.message || '删除失败')
    }
    deleteTarget.value = null
    await fetchUsers()
  } catch (e) {
    alert(e instanceof Error ? e.message : '删除失败')
  } finally {
    deleting.value = false
  }
}
```

### 9.4 修复后验证命令

```powershell
# 后端语法检查
python -m py_compile backend/services/rag_service.py
python -m py_compile backend/api/customer_service_routes.py
python -m py_compile backend/api/merchant_routes.py

# 前端构建验证
cd frontend
npm run build
```

---

## 10. 测试

项目已内置 pytest 测试，可在 Conda 环境中运行：

```powershell
pytest tests/test_api.py
```

如需单独运行后端接口测试：

```powershell
pytest backend/test_api.py
```

---

以上即为本项目的完整说明，按顺序完成环境准备、依赖安装、前后端启动后即可在浏览器中访问 `http://localhost:5173` 进行体验。
