"""向量索引服务 - 基于 ChromaDB + 硅基流动 Embedding API 的双阶段混合检索

双阶段检索策略：
  第一阶段：规则过滤（SQL ilike + 正则约束）→ 得到候选集
  第二阶段：向量排序（Embedding 余弦相似度）→ 对候选集语义排序

使用 ChromaDB 作为向量数据库，硅基流动 API (BAAI/bge-large-zh-v1.5) 生成 Embedding。
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

import chromadb
import requests

logger = logging.getLogger(__name__)

# ChromaDB 持久化目录
_CHROMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "chroma_db",
)

# 集合名称
_COLLECTION_NAME = "products"

# 硅基流动 Embedding API 配置
_SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "sk-lgdbbjgswowlmgzmcklglxowqphzmjfgfplybvmosoftycmy")
_SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
_EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"


class VectorIndex:
    """向量索引服务单例

    - 使用硅基流动 API 生成 Embedding（无需下载本地模型）
    - ChromaDB 持久化存储，重启不丢失
    - 线程安全（加锁保护写入操作）
    - 批量 Embedding 请求，减少 API 调用次数
    """

    _instance: Optional["VectorIndex"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "VectorIndex":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection = None
        self._initialized = True
        logger.info("VectorIndex 单例已创建（硅基流动 Embedding 模式）")

    def _ensure_client(self):
        """懒加载 ChromaDB 客户端"""
        if self._client is None:
            os.makedirs(_CHROMA_DIR, exist_ok=True)
            self._client = chromadb.PersistentClient(path=_CHROMA_DIR)
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"ChromaDB 已连接，集合 '{_COLLECTION_NAME}' 现有 {self._collection.count()} 条记录")

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """调用硅基流动 API 批量生成 Embedding

        BAAI/bge-large-zh-v1.5 输出 1024 维向量。
        单次请求最多 64 条文本。
        """
        all_embeddings = []
        batch_size = 32  # 每批 32 条，避免请求体过大

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = requests.post(
                    f"{_SILICONFLOW_BASE_URL}/embeddings",
                    headers={
                        "Authorization": f"Bearer {_SILICONFLOW_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": _EMBEDDING_MODEL,
                        "input": batch,
                        "encoding_format": "float",
                    },
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                # 按 index 排序确保顺序正确
                embeddings = [None] * len(batch)
                for item in data["data"]:
                    embeddings[item["index"]] = item["embedding"]
                all_embeddings.extend(embeddings)
            except Exception as e:
                logger.error(f"硅基流动 Embedding API 调用失败 (batch {i}): {e}")
                raise

        return all_embeddings

    def _embed_query(self, text: str) -> list[float]:
        """生成单条查询的 Embedding"""
        return self._embed_batch([text])[0]

    def build_index(self, products: list) -> int:
        """从商品列表构建/更新向量索引

        Args:
            products: Product 对象列表，需要 id, name, selling_points, category, brand 字段

        Returns:
            索引的文档数量
        """
        self._ensure_client()

        if not products:
            logger.warning("商品列表为空，跳过索引构建")
            return 0

        # 构建文档文本（拼接商品信息）
        ids = []
        documents = []
        metadatas = []

        for p in products:
            doc_parts = [p.name or ""]
            if p.selling_points:
                doc_parts.append(p.selling_points)
            if p.category:
                doc_parts.append(p.category)
            if p.brand:
                doc_parts.append(p.brand)
            doc = " | ".join(doc_parts)
            ids.append(str(p.id))
            documents.append(doc)
            metadatas.append({
                "product_id": p.id,
                "name": p.name or "",
                "category": p.category or "",
                "price": float(p.price or 0),
                "brand": p.brand or "",
            })

        # 调用硅基流动 API 批量生成 Embedding
        logger.info(f"正在调用硅基流动 API 生成 Embedding（{len(documents)} 条商品）...")
        embeddings = self._embed_batch(documents)
        logger.info("Embedding 生成完成")

        # 写入 ChromaDB（upsert 模式，自动去重）
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_emb = embeddings[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            self._collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                embeddings=batch_emb,
                metadatas=batch_meta,
            )

        count = self._collection.count()
        logger.info(f"向量索引构建完成，共 {count} 条记录")
        return count

    def search(
        self,
        query: str,
        candidate_ids: Optional[list[int]] = None,
        top_k: int = 10,
    ) -> list[dict]:
        """在候选集内做向量相似度搜索

        双阶段检索的第二阶段：对规则过滤后的候选集做语义排序。

        Args:
            query: 用户查询文本
            candidate_ids: 候选商品 ID 列表（第一阶段规则过滤的结果）。
                          如果为 None，则全局搜索。
            top_k: 返回前 K 个结果

        Returns:
            排序后的结果列表，每个元素包含:
            - product_id: 商品 ID
            - name: 商品名称
            - category: 分类
            - price: 价格
            - brand: 品牌
            - similarity: 相似度分数 (0~1，越高越相似)
        """
        self._ensure_client()

        if self._collection.count() == 0:
            logger.warning("向量索引为空，请先调用 build_index()")
            return []

        # 如果候选集为空，直接返回
        if candidate_ids is not None and len(candidate_ids) == 0:
            return []

        # 调用硅基流动 API 生成查询向量
        query_embedding = self._embed_query(query)

        # 构建查询过滤器
        where_filter = None
        if candidate_ids is not None and len(candidate_ids) > 0:
            id_list = [int(pid) for pid in candidate_ids]
            where_filter = {"product_id": {"$in": id_list}}

        # ChromaDB 查询
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, len(candidate_ids)) if candidate_ids else top_k,
            "include": ["metadatas", "distances"],
        }
        if where_filter:
            query_params["where"] = where_filter

        results = self._collection.query(**query_params)

        # 解析结果
        output = []
        if results and results.get("ids"):
            ids_batch = results["ids"][0]
            metas_batch = results["metadatas"][0]
            dists_batch = results["distances"][0]

            for idx in range(len(ids_batch)):
                meta = metas_batch[idx]
                dist = dists_batch[idx]
                # ChromaDB cosine distance: 0 = 完全相同, 2 = 完全相反
                # 转换为相似度: similarity = 1 - distance / 2
                similarity = max(0.0, 1.0 - dist / 2.0)
                output.append({
                    "product_id": meta.get("product_id"),
                    "name": meta.get("name", ""),
                    "category": meta.get("category", ""),
                    "price": meta.get("price", 0),
                    "brand": meta.get("brand", ""),
                    "similarity": round(similarity, 4),
                })

        return output

    def get_status(self) -> dict:
        """获取向量索引状态"""
        try:
            self._ensure_client()
            return {
                "initialized": True,
                "embedding_model": _EMBEDDING_MODEL,
                "embedding_provider": "硅基流动 SiliconFlow API",
                "collection": _COLLECTION_NAME,
                "count": self._collection.count(),
                "chroma_dir": _CHROMA_DIR,
            }
        except Exception as e:
            return {
                "initialized": False,
                "error": str(e),
            }

    def clear(self):
        """清空索引"""
        self._ensure_client()
        self._client.delete_collection(_COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("向量索引已清空")


# 全局单例
vector_index = VectorIndex()
