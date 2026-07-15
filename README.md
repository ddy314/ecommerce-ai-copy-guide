# 电商 AI 商品文案生成与智能导购助手

> 课程项目 —— 基于真实电商数据的 AI 文案生成、智能导购、评论情感分析、直播脚本生成与订单客服管理系统。

---

## 项目简介

本项目面向电商运营场景，通过爬虫采集真实商品与评论数据，结合 PostgreSQL/SQLite 持久化、Redis 缓存与 AI 大模型，为商家和用户提供一站式运营与购物体验：

- **AI 文案生成**：标题、卖点、详情页文案、广告语一键生成，支持编辑与 TXT 下载
- **智能导购问答**：基于商品知识库 + RAG 的数据驱动推荐
- **评论情感分析**：情感分布、高频词、差评痛点、优化建议，支持 TXT 报告下载
- **直播脚本生成**：按直播时长自动分段，含互动问题，支持 TXT 下载
- **商家后台**：数据看板、商品 / 订单 / 用户 / 客服 / 知识库管理
- **用户前台**：商品浏览、立即购买、购物车、我的订单、收货地址、收藏、浏览记录、个人中心
- **AI 客服**：用户随时咨询，商家端可实时回复并查看 AI 辅助回答

系统默认优先使用 **DeepSeek** 大模型（需在 `.env` 配置 `AI_API_KEY`）；未配置或调用失败时自动降级为 **Mock AI**，无需外部 API 即可完整演示。

---

## 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Tailwind CSS | 响应式单页应用，Composition API |
| 后端 | Flask 3 + Pydantic 2 + SQLAlchemy 2 | RESTful API，自动降级 SQLite |
| 数据库 | PostgreSQL 16 / SQLite | 主库 PostgreSQL，未启动时自动降级 |
| 缓存 | Redis 7 | 热点数据缓存 |
| 爬虫 | Scrapy 2 | 京东商品与评论数据采集 |
| AI | DeepSeek / OpenAI / Mock AI | 文案、分析、推荐、客服 |
| 部署 | Docker + Docker Compose | 一键编排后端依赖服务 |

---

## 前置要求

- Windows / macOS / Linux
- Python 3.11+
- Node.js 18+
- PostgreSQL 16 + Redis 7（推荐用 Docker 一键启动）
- 可选：Docker Desktop（零基础推荐）

---

## 快速开始

### 方式一：Conda 本地运行（推荐开发调试）

#### 1. 安装 Miniconda

访问 [Miniconda 下载页](https://docs.conda.io/en/latest/miniconda.html) 安装 Python 3.11 版本。

#### 2. 创建并激活环境

```bash
conda create -n ecommerce-ai python=3.11 -y
conda activate ecommerce-ai
```

#### 3. 拉取代码

```bash
git clone https://github.com/ddy314/ecommerce-ai-copy-guide.git
cd ecommerce-ai-copy-guide
```

#### 4. 安装后端依赖

```bash
pip install -r requirements.txt
```

#### 5. 配置环境变量

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

默认 `.env` 已配置本地 PostgreSQL 与 Redis。AI 默认使用 DeepSeek，不配置 `AI_API_KEY` 时自动使用 Mock AI。

#### 6. 启动数据库与缓存（Docker）

```bash
docker compose up postgres redis -d
```

若无 Docker，请本地安装 PostgreSQL / Redis 并修改 `.env` 中的连接地址。

#### 7. 初始化数据库

```bash
python -c "from backend.database import init_db; init_db()"
```

该命令会自动建表，并为旧表结构追加缺失字段、规范化订单编号、哈希化残留明文密码。

#### 8. 启动后端

```bash
python -m flask --app backend.app run --host=0.0.0.0 --port=8000
```

#### 9. 启动前端

再开一个终端（同样需要 `conda activate ecommerce-ai`）：

```bash
cd frontend
npm install
npm run dev
```

#### 10. 访问系统

- 前端界面：http://localhost:5173
- 后端 API：http://localhost:8000
- 健康检查：http://localhost:8000/health

默认测试账号：

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 商家 | `merchant` | `merchant123` |
| 用户 | `user` | `user123` |

---

### 方式二：Docker Compose 一键部署

#### 1. 安装 Docker Desktop

- Windows/macOS：[Docker Desktop 下载](https://www.docker.com/products/docker-desktop)
- Linux：安装 Docker Engine 与 Docker Compose

#### 2. 配置并启动

```bash
copy .env.example .env
docker compose --profile app up --build -d
```

启动服务：

- `postgres`：PostgreSQL 数据库
- `redis`：Redis 缓存
- `backend`：Flask 后端服务

#### 3. 初始化数据库

```bash
docker compose exec backend python -c "from backend.database import init_db; init_db()"
```

#### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 即可使用。

#### 5. 常用命令

```bash
# 查看状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 停止服务
docker compose --profile app down

# 完全重建
docker compose --profile app up --build -d
```

---

## 接入真实 AI 模型（可选）

编辑项目根目录 `.env`：

```env
# 默认优先 DeepSeek（推荐）
AI_PROVIDER=deepseek
AI_API_KEY=sk-your-deepseek-api-key
AI_MODEL=deepseek-v4-pro

# 或继续使用 OpenAI
# AI_PROVIDER=openai
# AI_API_KEY=sk-your-api-key
# AI_MODEL=gpt-4o-mini
# AI_BASE_URL=https://your-proxy.com/v1
```

不配置 `AI_API_KEY` 时自动使用 Mock AI，所有 AI 功能均可正常演示。

---

## 核心功能

### 1. 商品数据库
- Scrapy 爬虫从京东抓取真实商品数据
- 支持分类筛选、关键词搜索、分页加载
- 商品详情含价格、品牌、评分、评论数、图片与视频

### 2. 文案智能生成
- 自动生成标题、卖点、详情页文案、广告语
- 支持多种语气：专业可信、轻松活泼、高端奢华、温馨亲切
- 支持手动输入商品信息、编辑生成结果、下载 TXT、一键导入商品管理并上架

### 3. 智能导购
- 根据用户需求、预算生成个性化推荐
- 输出首推商品、推荐理由、备选商品
- 支持商品知识库问答（RAG）

### 4. 评论情感分析
- 支持手动输入、文件上传、从数据库加载评论
- AI 分析情感分布、高频关键词、差评痛点、优化建议
- 支持 TXT 报告下载

### 5. 直播脚本生成
- 根据商品信息和直播时长生成分段脚本
- 输出开场引入、卖点讲解、互动转化、互动问题
- 支持下载 TXT

### 6. 商品与订单管理
- 商家端：卡片式商品管理、订单搜索分页、发货填单、取消订单、处理退换货
- 用户端：商品浏览、立即购买、购物车结算、我的订单、确认收货、评价、申请退换货、填写退货单号
- 订单号统一格式：`YYYYMMDDHHMMSS<商品展示ID><5位序号>`

### 7. 客服管理
- 用户端：随时联系 AI 智能客服，从商品详情页咨询可自动带入当前商品
- 商家端：会话列表、实时回复、AI 辅助回答、Markdown 渲染
- 客服头像与商家/用户真实头像保持一致并右对齐

### 8. 用户/商家个人中心
- 头像上传与资料编辑（支持 JPG/PNG/GIF/WebP，优先扩展名其次 MIME 类型校验）
- 收货地址管理
- 收藏、浏览记录、购物车、订单聚合展示
- 密码统一哈希存储，不保存明文

---

## 项目结构

```
.
├── backend/                    # 后端服务
│   ├── api/                    # API 路由
│   │   ├── auth_routes.py      # 认证/头像上传
│   │   ├── merchant_routes.py  # 商家管理
│   │   ├── user_routes.py      # 用户前台
│   │   ├── customer_service_routes.py
│   │   ├── routes.py           # 核心 AI 能力
│   │   └── crawl_routes.py     # 爬虫任务
│   ├── models/                 # 数据库模型
│   │   ├── product.py
│   │   ├── review.py
│   │   ├── shopping.py         # 购物车/订单
│   │   ├── user.py
│   │   ├── customer_service.py
│   │   └── knowledge_base.py
│   ├── services/               # AI 服务层
│   │   ├── ai_provider.py      # AI 提供者抽象与选择
│   │   ├── ai_mock.py          # Mock AI 实现
│   │   ├── deepseek_provider.py# DeepSeek 实现
│   │   ├── openai_provider.py  # OpenAI 实现
│   │   └── rag_service.py      # RAG 增强问答
│   ├── utils/                  # 通用工具
│   │   └── helpers.py          # 订单号生成等
│   ├── database.py             # 数据库连接、降级、迁移
│   ├── fastapi_app.py          # FastAPI 接口（已合并到 Flask）
│   ├── app.py                  # Flask 应用入口
│   └── config.py               # 配置管理
├── crawler/                    # Scrapy 爬虫
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   ├── CopyGenerator.vue
│   │   │   ├── ReviewAnalyzer.vue
│   │   │   ├── LiveScriptGenerator.vue
│   │   │   ├── GuideRecommender.vue
│   │   │   ├── merchant/       # 商家后台组件
│   │   │   └── user/           # 用户前台组件
│   │   │       ├── CheckoutModal.vue   # 统一结算弹窗
│   │   │       ├── ProductBrowse.vue
│   │   │       ├── ShoppingCart.vue
│   │   │       ├── UserProfile.vue
│   │   │       └── MyOrders.vue
│   │   ├── utils/              # 工具函数
│   │   │   └── avatar.ts       # 头像 URL 解析
│   │   ├── api.ts              # 前端 API 封装
│   │   ├── App.vue
│   │   └── main.ts
│   └── package.json
├── run_crawler.py              # 爬虫运行脚本
├── docker-compose.yml          # Docker 编排
├── Dockerfile
├── requirements.txt
├── .env.example
├── README.md
└── 项目技术文档.md
```

---

## 运行爬虫（可选）

```bash
# 爬取商品数据
python run_crawler.py products

# 爬取指定商品评论
python run_crawler.py reviews 10001234,10005678

# 初始化数据库并爬取商品
python run_crawler.py all
```

Docker 环境：

```bash
docker compose exec backend python run_crawler.py all
```

---

## 测试

```bash
# 后端测试
python -m pytest tests/ -v

# 前端构建测试
cd frontend && npm run build
```

---

## 常见问题

**Q：启动后端时报数据库连接错误？**

A：请确认 PostgreSQL 已启动且 `.env` 中 `DATABASE_URL` 配置正确。未配置或连接失败时，系统会自动降级为 SQLite。

**Q：头像上传成功但页面不显示？**

A：后端返回相对路径 `/uploads/avatars/xxx.jpg`，前端已统一使用 `resolveAvatarUrl()` 拼接 `API_BASE` 为完整 URL，请确认 `VITE_API_BASE_URL` 指向正确后端地址。

**Q：上传 JPG 仍提示格式错误？**

A：校验逻辑同时参考文件扩展名与 MIME 类型；若仍失败，请检查文件真实 MIME 类型是否为 `image/jpeg`。

**Q：前端页面空白或接口报错？**

A：确认后端已启动，并且 `frontend/.env` 或 `vite.config.ts` 中的代理指向 `http://localhost:8000`。

**Q：AI 功能没有真实结果？**

A：默认优先 DeepSeek，需配置 `AI_API_KEY`；未配置时自动使用 Mock AI，功能完整可演示。

**Q：客服页面 AI 头像位置不对？**

A：已统一将商家与 AI 消息右对齐，并优先使用真实头像。

---

## 许可证

MIT License
