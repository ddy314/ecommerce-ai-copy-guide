"""OpenAPI 文档生成模块"""
from __future__ import annotations

from flask import Blueprint, jsonify, render_template_string

docs_bp = Blueprint("docs", __name__)


def get_openapi_spec() -> dict:
    """生成 OpenAPI 3.0 规范文档"""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "电商 AI 商品文案生成与智能导购助手 API",
            "description": "提供商品文案生成、智能导购推荐、评论情感分析和直播脚本生成能力",
            "version": "0.1.0",
            "contact": {
                "name": "课程项目团队"
            }
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "本地开发服务器"
            }
        ],
        "paths": {
            "/health": {
                "get": {
                    "summary": "健康检查",
                    "description": "检查服务状态和配置信息",
                    "responses": {
                        "200": {
                            "description": "服务正常",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "ok"},
                                            "service": {"type": "string", "example": "ecommerce-ai-copy-guide"},
                                            "version": {"type": "string", "example": "0.1.0"},
                                            "runtime": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/capabilities": {
                "get": {
                    "summary": "获取能力清单",
                    "description": "返回当前可用的 AI 能力列表",
                    "responses": {
                        "200": {
                            "description": "能力清单",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "mode": {"type": "string", "example": "mock"},
                                            "features": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "key": {"type": "string"},
                                                        "name": {"type": "string"},
                                                        "endpoint": {"type": "string"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/copy/generate": {
                "post": {
                    "summary": "生成商品文案",
                    "description": "根据商品名称、目标人群、语气和卖点生成标题、卖点、详情页文案和广告语",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["product_name"],
                                    "properties": {
                                        "product_name": {
                                            "type": "string",
                                            "example": "云感护腰办公椅",
                                            "description": "商品名称"
                                        },
                                        "audience": {
                                            "type": "string",
                                            "example": "久坐办公人群",
                                            "description": "目标人群"
                                        },
                                        "tone": {
                                            "type": "string",
                                            "example": "专业可信",
                                            "description": "文案语气"
                                        },
                                        "selling_points": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "example": ["护腰支撑", "透气坐垫"],
                                            "description": "商品卖点列表"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "生成成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "product_name": {"type": "string"},
                                            "tone": {"type": "string"},
                                            "title": {"type": "string"},
                                            "selling_points": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            },
                                            "detail_copy": {"type": "string"},
                                            "ad_slogan": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "请求参数错误",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "error": {"type": "string"},
                                            "message": {"type": "string"},
                                            "details": {"type": "array"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/guide/recommend": {
                "post": {
                    "summary": "智能导购推荐",
                    "description": "根据用户需求、预算和候选商品生成推荐理由和购买建议",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["user_need"],
                                    "properties": {
                                        "user_need": {
                                            "type": "string",
                                            "example": "预算 300 元以内，送给经常加班的朋友",
                                            "description": "用户需求描述"
                                        },
                                        "budget": {
                                            "type": "string",
                                            "example": "300元以内",
                                            "description": "预算范围"
                                        },
                                        "products": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "example": ["高性价比基础款", "品质升级款"],
                                            "description": "候选商品列表"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "推荐成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "user_need": {"type": "string"},
                                            "budget": {"type": "string"},
                                            "recommended_product": {"type": "string"},
                                            "reason": {"type": "string"},
                                            "alternatives": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            },
                                            "guide_message": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/reviews/analyze": {
                "post": {
                    "summary": "评论情感分析",
                    "description": "分析商品评论的情感分布、关键词和痛点",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["reviews"],
                                    "properties": {
                                        "product_name": {
                                            "type": "string",
                                            "example": "示例商品",
                                            "description": "商品名称"
                                        },
                                        "reviews": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "example": ["这个产品很好用", "质量太差了"],
                                            "description": "评论列表"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "分析成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "product_name": {"type": "string"},
                                            "total": {"type": "integer"},
                                            "sentiment": {
                                                "type": "object",
                                                "properties": {
                                                    "positive": {"type": "integer"},
                                                    "neutral": {"type": "integer"},
                                                    "negative": {"type": "integer"}
                                                }
                                            },
                                            "top_keywords": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            },
                                            "pain_points": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            },
                                            "optimization_suggestions": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/scripts/live": {
                "post": {
                    "summary": "直播脚本生成",
                    "description": "根据商品信息和直播时长生成分段脚本和互动问题",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["product_name"],
                                    "properties": {
                                        "product_name": {
                                            "type": "string",
                                            "example": "云感护腰办公椅",
                                            "description": "商品名称"
                                        },
                                        "duration_minutes": {
                                            "type": "integer",
                                            "example": 5,
                                            "description": "直播时长（分钟）"
                                        },
                                        "tone": {
                                            "type": "string",
                                            "example": "热情自然",
                                            "description": "直播语气"
                                        },
                                        "highlights": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "example": ["护腰支撑", "透气坐垫"],
                                            "description": "商品亮点列表"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "生成成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "product_name": {"type": "string"},
                                            "duration_minutes": {"type": "integer"},
                                            "tone": {"type": "string"},
                                            "segments": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "minutes": {"type": "integer"},
                                                        "script": {"type": "string"}
                                                    }
                                                }
                                            },
                                            "interaction_questions": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


SWAGGER_UI_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API 文档 - 电商 AI 商品文案生成与智能导购助手</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.5/swagger-ui.css">
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }
        .header p {
            margin: 8px 0 0 0;
            opacity: 0.9;
            font-size: 14px;
        }
        #swagger-ui {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛍️ 电商 AI 商品文案生成与智能导购助手</h1>
        <p>API 文档 | 版本 0.1.0</p>
    </div>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            SwaggerUIBundle({
                url: "/api/docs/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true,
                showExtensions: true,
                showCommonExtensions: true
            });
        };
    </script>
</body>
</html>
"""


@docs_bp.route("/api/docs")
def swagger_ui():
    """Swagger UI 页面"""
    return render_template_string(SWAGGER_UI_HTML)


@docs_bp.route("/api/docs/openapi.json")
def openapi_json():
    """OpenAPI JSON 规范"""
    return jsonify(get_openapi_spec())
