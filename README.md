# 电商 AI 商品文案生成与智能导购助手

> 课程项目 - 基于真实电商数据的 AI 文案生成、智能导购、评论情感分析与直播脚本生成系统。

## 项目简介

本项目是一个面向电商运营场景的 AI 助手系统，通过 Scrapy 爬虫从京东等购物平台抓取商品和评论数据，存储到 PostgreSQL 数据库，利用 Redis 缓存热点数据，接入 AI 大模型实现以下功能：

- 商品文案智能生成
- 智能导购推荐
- 评论情感分析
- 直播脚本生成
- 商品/订单/客服管理

## 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Tailwind CSS | 响应式单页应用 |
| 后端 | Flask 3 + Pydantic 2 + SQLAlchemy 2 | RESTful API |
| 数据库 | PostgreSQL 16 | 商品、评论、订单、用户等持久化 |
| 缓存 | Redis 7 | 热点数据缓存 |
| 爬虫 | Scrapy 2 | 京东商品与评论爬取 |
| AI | OpenAI API / Mock | 文案、分析、推荐、客服回复 |
| 部署 | Docker + Docker Compose | 一键编排后端依赖服务 |

## 前置要求

- **Windows / macOS / Linux**
- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 16** 与 **Redis 7**（可用 Docker 一键启动）
- 可选：**Docker Desktop**（推荐零基础用户使用）

## 快速开始

### 方式一：Conda 本地运行（适合开发调试）

> 如果你完全零基础，请按以下步骤从 0 开始配置。

#### 1. 安装 Miniconda

1. 访问 [Miniconda 下载页](https://docs.conda.io/en/latest/miniconda.html)。
2. 下载对应系统的 Python 3.11 安装包并安装。
3. 安装完成后，打开 **Anaconda Prompt**（Windows）或终端（macOS/Linux）。

#### 2. 创建并激活 Conda 环境

```bash
conda create -n ecommerce-ai python=3.11 -y
conda activate ecommerce-ai
```

#### 3. 下载项目代码

```bash
cd C:\Users\YourName\Desktop   # Windows 示例，可换成你的目录
git clone https://github.com/ddy314/ecommerce-ai-copy-guide.git
cd ecommerce-ai-copy-guide
```

如果电脑没有安装 Git，也可以直接下载 GitHub 页面上的 ZIP 压缩包并解压。

#### 4. 安装后端依赖

```bash
pip install -r requirements.txt
```

#### 5. 配置环境变量

```bash
# Windows（PowerShell）
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

默认 `.env` 已配置好本地 PostgreSQL 与 Redis 地址，没有配置 AI Key 时会自动使用 Mock AI，功能完整可演示。

#### 6. 启动数据库与缓存（Docker）

如果你已经安装 Docker：

```bash
docker compose up postgres redis -d
```

没有 Docker 的同学，需要本地安装 PostgreSQL 与 Redis，并修改 `.env` 中的连接地址。

#### 7. 初始化数据库

```bash
python -c "from backend.database import init_db; init_db()"
```

#### 8. 启动后端服务

```bash
python -m flask --app backend.app run --host=0.0.0.0 --port=8000
```

#### 9. 启动前端服务

再打开一个终端（同样需要 `conda activate ecommerce-ai`），执行：

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

### 方式二：Docker Compose 一键部署（推荐零基础用户）

#### 1. 安装 Docker Desktop

- Windows/macOS：下载 [Docker Desktop](https://www.docker.com/products/docker-desktop) 并安装。
- Linux：参考官方文档安装 Docker Engine 与 Docker Compose。

#### 2. 配置环境变量

```bash
copy .env.example .env
```

#### 3. 构建并启动全部服务

```bash
docker compose --profile app up --build -d
```

该命令会启动：

- `postgres`：PostgreSQL 数据库
- `redis`：Redis 缓存
- `backend`：Flask 后端服务

#### 4. 初始化数据库

```bash
docker compose exec backend python -c "from backend.database import init_db; init_db()"
```

#### 5. 启动前端

Docker Compose 目前主要编排后端依赖服务。前端开发服务器需要在本地启动：

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 即可使用。

#### 6. 常用 Docker 命令

```bash
# 查看服务状态
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

编辑项目根目录的 `.env` 文件：

```env
AI_PROVIDER=openai
AI_API_KEY=sk-your-api-key
AI_MODEL=gpt-4o-mini
# 国内镜像可配置
AI_BASE_URL=https://your-proxy.com/v1
```

不配置时默认使用 Mock 服务，所有 AI 功能均可正常演示。

---

## 核心功能

### 1. 商品数据库
- Scrapy 爬虫从京东抓取真实商品数据
- 支持分类筛选、关键词搜索
- 商品详情含价格、品牌、评分、评论数

### 2. 文案智能生成
- 基于 AI 自动生成标题、卖点、详情页文案、广告语
- 支持多种语气：专业可信、轻松活泼、高端奢华、温馨亲切

### 3. 智能导购
- 根据用户需求、预算生成个性化推荐
- 输出首推商品、推荐理由、备选商品

### 4. 评论情感分析
- 支持手动输入、文件上传、从数据库加载评论
- AI 分析情感分布、高频关键词、差评痛点、优化建议
- 支持下载 TXT 报告

### 5. 直播脚本生成
- 根据商品信息和直播时长生成分段脚本
- 输出开场引入、卖点讲解、互动转化、自动生成互动问题

### 6. 订单与售后管理
- 商家端：订单搜索、分页展示、发货填写快递单号、取消订单、处理退换货
- 用户端：我的订单、确认收货、评价、申请退换货、填写退货快递单号

### 7. 客服管理
- 用户可随时联系 AI 智能客服
- 商家端查看会话列表、回复用户
- AI 回复支持 Markdown 渲染

---

## 项目结构

```
.
├── backend/                    # 后端服务
│   ├── api/                    # API 路由
│   │   ├── auth_routes.py
│   │   ├── merchant_routes.py
│   │   ├── user_routes.py
│   │   ├── customer_service_routes.py
│   │   └── routes.py
│   ├── models/                 # 数据库模型
│   │   ├── product.py
│   │   ├── review.py
│   │   ├── shopping.py         # 购物车/订单模型
│   │   ├── user.py
│   │   └── customer_service.py
│   ├── services/               # AI 服务层
│   │   ├── ai_provider.py
│   │   ├── ai_mock.py
│   │   ├── openai_provider.py
│   │   └── rag_service.py
│   ├── database.py             # 数据库连接与迁移
│   ├── app.py                  # Flask 应用入口
│   └── config.py               # 配置管理
├── crawler/                    # Scrapy 爬虫
│   ├── spiders/
│   ├── items.py
│   ├── pipelines.py
│   └── settings.py
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   ├── ProductList.vue
│   │   │   ├── CopyGenerator.vue
│   │   │   ├── GuideRecommender.vue
│   │   │   ├── ReviewAnalyzer.vue
│   │   │   ├── LiveScriptGenerator.vue
│   │   │   ├── user/MyOrders.vue
│   │   │   └── merchant/OrderManage.vue
│   │   ├── App.vue
│   │   └── main.ts
│   └── package.json
├── run_crawler.py              # 爬虫运行脚本
├── docker-compose.yml          # Docker 编排
├── Dockerfile                  # 后端容器镜像
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
└── README.md
```

---

## 运行爬虫（可选）

```bash
# 爬取京东商品数据
python run_crawler.py products

# 爬取指定商品评论
python run_crawler.py reviews 10001234,10005678

# 初始化数据库并爬取商品
python run_crawler.py all
```

使用 Docker 时：

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

A：请确认 PostgreSQL 已启动，且 `.env` 中的 `DATABASE_URL` 配置正确。如果未安装 PostgreSQL，可删除或留空 `DATABASE_URL`，后端会自动降级为 SQLite。

**Q：前端页面空白或接口报错？**

A：请确认后端服务已启动，并且 `frontend/.env` 或 `vite.config.ts` 中的代理配置指向 `http://localhost:8000`。

**Q：AI 功能没有真实结果？**

A：默认使用 Mock AI。如需真实模型，请在 `.env` 中配置 `AI_PROVIDER`、`AI_API_KEY` 和 `AI_MODEL`。

---

## 许可证

本课程项目仅供教学演示使用。
