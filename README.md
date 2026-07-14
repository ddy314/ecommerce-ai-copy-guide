# 电商 AI 商品文案生成与智能导购助手

> 课程项目 - 基于真实电商数据的 AI 文案生成与智能导购系统

## 项目简介

本项目是一个面向电商运营场景的 AI 助手系统，通过 Scrapy 爬虫从京东等购物平台实时抓取商品和评论数据，存储到 PostgreSQL 数据库，利用 Redis 缓存热点数据，接入 AI 大模型实现商品文案生成、智能导购推荐、评论情感分析和直播脚本生成四大核心功能。

## 技术架构

```
─────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + TypeScript)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │商品数据库 │ │文案生成  │ │智能导购  │ │评论分析  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  后端 (Flask + Pydantic)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │API 路由  │ │数据仓库  │ │AI 服务层 │ │缓存服务  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
─────────────────────────────────────────────────────────────┘
              │                    │                    │
              ▼                    ▼                    ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   PostgreSQL    │   │     Redis       │   │   Scrapy 爬虫   │
│  商品/评论存储   │   │   热点数据缓存   │   │  京东商品+评论   │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

## 技术栈

| 层次 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + TypeScript + Vite | 响应式界面，5个功能页面 |
| 后端 | Flask 3 + Pydantic 2 | RESTful API，结构化请求/响应 |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2 | 商品、评论、任务、推荐记录 |
| 缓存 | Redis 7 | 热点商品、文案结果、分析缓存 |
| 爬虫 | Scrapy 2 | 京东商品列表+评论爬取 |
| AI | OpenAI API / Mock | 文案生成、情感分析、推荐 |
| 部署 | Docker + Docker Compose | 一键编排全部服务 |
| 文档 | Swagger UI (OpenAPI 3) | 交互式 API 文档 |

## 核心功能

### 1. 商品数据库（真实数据）
- Scrapy 爬虫从京东实时抓取商品数据
- 支持按类目、关键词搜索浏览
- 商品详情含价格、品牌、评分、评论数
- PostgreSQL 持久化存储

### 2. 商品文案智能生成
- 基于 AI 大模型自动生成营销文案
- 输出：标题、卖点、详情页文案、广告语
- 支持多种语气：专业可信、轻松活泼、高端奢华、温馨亲切
- Redis 缓存生成结果，避免重复调用

### 3. 智能导购推荐
- 根据用户需求、预算生成个性化推荐
- 输出：首推商品、推荐理由、备选商品、购买建议
- 推荐记录持久化到数据库

### 4. 评论情感分析
- 从数据库加载真实商品评论
- AI 分析情感分布（正面/中性/负面）
- 提取高频关键词、差评痛点、优化建议
- 可视化展示分析结果

### 5. 直播脚本生成
- 根据商品信息和直播时长生成分段脚本
- 输出：开场引入、卖点讲解、互动转化
- 自动生成互动问题

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose（可选，用于数据库和缓存）

### 方式一：Docker 一键启动（推荐）

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 启动全部服务（PostgreSQL + Redis + 后端）
docker compose --profile app up --build -d

# 3. 初始化数据库表
docker compose exec backend python -c "from backend.database import init_db; init_db()"

# 4. 运行爬虫爬取商品数据
docker compose exec backend python run_crawler.py products

# 5. 启动前端
cd frontend && npm install && npm run dev
```

### 方式二：本地开发

#### 后端

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动 PostgreSQL 和 Redis（Docker）
docker compose up postgres redis -d

# 初始化数据库
python -c "from backend.database import init_db; init_db()"

# 启动后端服务
python -m flask --app backend.app run --host=0.0.0.0 --port=8000
```

#### 前端

```bash
cd frontend
npm install
npm run dev
```

#### 运行爬虫

```bash
# 爬取京东商品数据
python run_crawler.py products

# 爬取指定商品的评论
python run_crawler.py reviews 10001234,10005678

# 初始化数据库 + 爬取商品
python run_crawler.py all
```

#### 接入真实 AI 模型

在 `.env` 文件中配置：

```env
AI_PROVIDER=openai
AI_API_KEY=sk-your-api-key
AI_MODEL=gpt-4o-mini
# 可选：使用国内镜像
AI_BASE_URL=https://your-proxy.com/v1
```

不配置则默认使用 Mock 服务，功能完整可演示。

### 访问地址

- 前端界面：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/api/docs
- 健康检查：http://localhost:8000/health

## 项目结构

```
.
├── backend/                    # 后端服务
│   ├── api/
│   │   └── routes.py          # API 路由（含数据查询接口）
│   ├── docs/
│   │   └── openapi.py         # Swagger API 文档
│   ├── models/                # 数据库模型
│   │   ├── product.py         # 商品表
│   │   ├── review.py          # 评论表
│   │   ├── generation_task.py # 生成任务表
│   │   └── recommendation_log.py # 推荐记录表
│   ├── repositories/          # 数据访问层
│   │   ├── product_repo.py    # 商品仓库
│   │   └── review_repo.py     # 评论仓库
│   ├── schemas/
│   │   └── requests.py        # 请求/响应模型
│   ├── services/              # AI 服务层
│   │   ├── ai_provider.py     # 服务抽象层
│   │   ├── ai_mock.py         # Mock 服务
│   │   └── openai_provider.py # OpenAI 接入
│   ├── app.py                 # Flask 应用入口
│   ├── cache.py               # Redis 缓存服务
│   ├── config.py              # 配置管理
│   └── database.py            # 数据库连接
├── crawler/                    # Scrapy 爬虫
│   ├── spiders/
│   │   ├── jd_spider.py       # 京东商品爬虫
│   │   └── jd_review_spider.py # 京东评论爬虫
│   ├── items.py               # 数据项定义
│   ├── pipelines.py           # 数据入库管道
│   └── settings.py            # 爬虫配置
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # 功能页面
│   │   │   ├── ProductList.vue      # 商品数据库
│   │   │   ├── CopyGenerator.vue    # 文案生成
│   │   │   ├── GuideRecommender.vue # 智能导购
│   │   │   ├── ReviewAnalyzer.vue   # 评论分析
│   │   │   ── LiveScriptGenerator.vue # 直播脚本
│   │   ├── api.ts             # API 服务层
│   │   ├── App.vue            # 主应用（含导航）
│   │   ── main.ts            # 入口
│   ── package.json
├── data/                       # 演示数据（备用）
├── docs/                       # 项目文档
│   ├── api-guide.md           # API 使用指南
│   ├── deployment.md          # 部署指南
│   ├── requirements/          # 需求文档
│   ├── design/                # 设计文档
│   └── plan/                  # 计划文档
├── tests/                      # 测试用例
├── run_crawler.py              # 爬虫运行脚本
├── docker-compose.yml          # Docker 编排
├── Dockerfile                  # 后端容器镜像
└── requirements.txt            # Python 依赖
```

## API 接口

### 业务 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/capabilities` | 能力清单 |
| POST | `/api/copy/generate` | 生成商品文案 |
| POST | `/api/guide/recommend` | 智能导购推荐 |
| POST | `/api/reviews/analyze` | 评论情感分析 |
| POST | `/api/scripts/live` | 直播脚本生成 |

### 数据查询 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/products` | 商品列表（支持搜索/分类） |
| GET | `/api/products/<id>` | 商品详情（含评论） |
| GET | `/api/products/<id>/reviews` | 商品评论列表 |

**完整 API 文档：** http://localhost:8000/api/docs

## 数据库模型

### products（商品表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| platform | VARCHAR(50) | 来源平台（jd/taobao） |
| product_id | VARCHAR(100) | 平台商品ID（唯一） |
| name | VARCHAR(500) | 商品名称 |
| category | VARCHAR(200) | 商品类目 |
| price | FLOAT | 价格 |
| brand | VARCHAR(200) | 品牌 |
| selling_points | TEXT | 卖点描述 |
| image_url | VARCHAR(500) | 主图URL |
| detail_url | VARCHAR(500) | 详情URL |
| specs | TEXT | 规格参数（JSON） |
| sales_count | INT | 销量 |
| rating | FLOAT | 评分 |
| review_count | INT | 评论数 |

### reviews（评论表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| product_id | INT | 关联商品（外键） |
| platform_review_id | VARCHAR(100) | 平台评论ID（唯一） |
| content | TEXT | 评论内容 |
| rating | INT | 评分（1-5） |
| user_name | VARCHAR(100) | 用户名 |

### generation_tasks（生成任务表）
记录每次 AI 生成的输入参数和输出结果。

### recommendation_logs（推荐记录表）
记录每次导购推荐的用户需求和推荐结果。

## 测试

```bash
# 后端测试
python -m pytest tests/ -v

# 前端构建测试
cd frontend && npm run build
```

## 课程展示建议

1. **数据展示**：先展示商品数据库页面，说明 Scrapy 爬虫从京东抓取了真实数据
2. **文案生成**：选择一个真实商品，演示 AI 生成文案的效果
3. **评论分析**：展示从数据库加载的真实评论，演示情感分析结果
4. **智能导购**：输入用户需求，演示推荐逻辑
5. **直播脚本**：选择商品生成直播话术
6. **技术架构**：展示架构图，说明 PostgreSQL + Redis + Scrapy + AI 的完整链路

## 后续扩展

- 接入更多电商平台（淘宝、拼多多）
- 实现定时爬取任务
- 添加用户认证和权限管理
- 实现文案/脚本导出功能（PDF/Word）
- 添加数据可视化看板（PowerBI / ECharts）
- 接入更多 AI 模型（文心一言、通义千问）

## 许可证

本课程项目仅供教学演示使用。
