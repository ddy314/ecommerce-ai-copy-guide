# Ecommerce AI Copy Guide

电商 AI 商品文案生成与智能导购助手，小组作业项目初始化仓库。

## 项目目标

- 商品文案智能生成：标题、卖点、详情页文案、广告语，支持简洁、高端、活泼、专业等风格。
- 智能导购与推荐问答：回答尺码、功能、搭配等咨询，并根据偏好做跨商品推荐。
- 用户评论情感分析：识别好评、差评、吐槽点，并生成商品优化建议。
- 直播和短视频脚本生成：生成直播话术、产品讲解流程、互动问答脚本。

## 技术选型

- 开发语言：Python
- 后端框架：Flask
- 缓存：Redis
- 数据库：PostgreSQL
- AI 能力：多模态大模型、情感分析
- 数据采集：Scrapy
- 前端：Vue.js 或 React，用于 H5 和管理后台
- 部署环境：Linux / Docker
- 配置管理：Git

## 当前状态

本仓库当前只完成项目初始化和配置文件准备，暂不包含业务代码。

## 目录结构

```text
.
├── backend/          # 后端服务目录
├── frontend/         # H5 与管理后台目录
├── docs/             # 需求、设计、汇报材料
├── deploy/           # 部署相关配置
├── scripts/          # 辅助脚本
├── tests/            # 测试目录
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

## 本地环境规划

1. 安装 Docker 和 Docker Compose。
2. 复制 `.env.example` 为 `.env` 并按需修改。
3. 后续实现业务代码后，使用 Docker Compose 启动 PostgreSQL、Redis 和后端服务。

## 小组分工建议

- 后端与接口：Flask API、数据库模型、Redis 缓存。
- AI 模块：文案生成、导购问答、情感分析、脚本生成。
- 爬虫与数据：商品数据、评论数据抓取与清洗。
- 前端：H5 导购页面、管理后台。
- 文档与展示：需求说明、系统设计、Visio 图、PowerBI 展示。
