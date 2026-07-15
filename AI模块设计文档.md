# AI 模块设计文档

## 1. AI 模块整体架构（Provider 模式）

整个 AI 服务采用**Provider（提供者）模式**进行抽象，核心思想是：上层业务只依赖统一的 `AIProvider` 接口，而具体的大模型实现（DeepSeek、OpenAI、Mock）通过工厂函数动态注入。这样做的好处是本地开发、测试、生产可以无缝切换，且新增模型时只需新增一个 Provider 类即可，无需改动业务代码。

接口定义位于 `backend/services/ai_provider.py`：

```python
class AIProvider(ABC):
    """AI 服务提供者接口"""

    @abstractmethod
    def generate_copy(self, payload: CopyGenerationRequest) -> dict: ...

    @abstractmethod
    def recommend(self, payload: GuideRecommendationRequest) -> dict: ...

    @abstractmethod
    def guide_qa(self, payload: GuideQARequest) -> dict: ...

    @abstractmethod
    def cross_recommend(self, payload: CrossRecommendRequest) -> dict: ...

    @abstractmethod
    def analyze_reviews(self, payload: ReviewAnalysisRequest) -> dict: ...

    @abstractmethod
    def generate_live_script(self, payload: LiveScriptRequest) -> dict: ...
```

工厂函数 `get_ai_provider()` 根据环境变量 `AI_PROVIDER` 决定实例化哪个实现：

```python
def get_ai_provider() -> AIProvider:
    provider = os.getenv("AI_PROVIDER", "deepseek").lower().strip()

    if provider == "openai":
        from backend.services.openai_provider import OpenAIProvider
        return OpenAIProvider()

    if provider in ("deepseek", ""):
        from backend.services.deepseek_provider import DeepSeekProvider
        from backend.services.ai_mock import MockAIService

        api_key = os.getenv("AI_API_KEY", "")
        if not api_key:
            logger.warning("未配置 AI_API_KEY，使用 Mock AI 作为备用")
            return MockAIService()

        try:
            return DeepSeekProvider()
        except Exception as e:
            logger.warning(f"初始化 DeepSeek 失败，使用 Mock AI 作为备用: {e}")
            return MockAIService()

    # mock 或其他未知值均回退 Mock
    from backend.services.ai_mock import MockAIService
    return MockAIService()
```

从这段代码可以看到：默认优先 DeepSeek；如果 `AI_API_KEY` 为空，则自动降级到 `MockAIService`；显式设置 `AI_PROVIDER=openai` 时走 OpenAI。所有降级路径都保证了服务可用性。

`backend/services/openai_provider.py` 是主要的真实模型实现，它使用 `openai` SDK 与模型交互，并在返回非 JSON 或调用失败时降级到 Mock：

```python
class OpenAIProvider(AIProvider):
    def __init__(self):
        api_key = os.getenv("AI_API_KEY", "")
        base_url = os.getenv("AI_BASE_URL", "")
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")

        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content or ""
```

`backend/services/deepseek_provider.py` 则直接继承 `OpenAIProvider`，仅固定 DeepSeek 的 endpoint 与默认模型：

```python
class DeepSeekProvider(OpenAIProvider):
    def __init__(self):
        os.environ.setdefault("AI_BASE_URL", "https://api.deepseek.com/v1")
        os.environ.setdefault("AI_MODEL", "deepseek-v4-pro")
        super().__init__()
```

`backend/services/ai_mock.py` 是**确定性规则实现**，不依赖任何外部 API，内部通过模板、情感词典、关键词映射完成文案生成、导购推荐、问答、评论分析、直播脚本等全部功能。它既是开发测试的 fallback，也是无网络环境下的兜底方案。

---

## 2. RAG 检索流程

RAG（Retrieval-Augmented Generation）是智能导购问答的核心。整个流程可以拆分为：**Query 解析 → 规则过滤（第一阶段） → 向量重排序（第二阶段） → 答案生成**。

### 2.1 Query 解析

当用户提问时，`RAGService` 首先做**多维度约束抽取**，而不是直接把原始问题扔进向量库。解析逻辑集中在 `backend/services/rag_service.py`：

```python
price_limit = self._extract_price_constraint(question)
price_range = self._extract_price_range(question) if not price_limit else None
spec_constraints = self._extract_spec_constraints(question)
primary_kws = self._extract_primary_keywords(question)
detected_category = self._detect_category(question)
```

`_extract_primary_keywords` 从预置的 `CATEGORY_KEYWORDS` 映射表中提取商品核心词：

```python
def _extract_primary_keywords(self, question: str) -> list[str]:
    q_lower = question.lower()
    primary_kws = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in q_lower and len(kw) >= 2:
                primary_kws.append(kw)
    primary_kws = list(set(primary_kws))
    primary_kws.sort(key=len, reverse=True)
    return primary_kws
```

`_detect_category` 同样基于 `CATEGORY_KEYWORDS`，通过加权匹配避免跨分类误召回：

```python
def _detect_category(self, question: str) -> Optional[str]:
    q_lower = question.lower()
    best_category = None
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in q_lower:
                score += len(kw)
        if score > best_score:
            best_score = score
            best_category = category
    if best_score >= 2:
        return best_category
    return None
```

### 2.2 向量索引构建

向量索引服务在 `backend/services/vector_index.py` 中实现，使用 **ChromaDB** 做持久化向量存储，使用 **硅基流动（SiliconFlow）Embedding API** 生成向量，模型固定为 `BAAI/bge-large-zh-v1.5`。

```python
class VectorIndex:
    _instance: Optional["VectorIndex"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "VectorIndex":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
```

这是一个单例，线程安全。`build_index` 方法把商品信息拼接成文档文本后批量生成 Embedding：

```python
def build_index(self, products: list) -> int:
    ids = []
    documents = []
    metadatas = []

    for p in products:
        doc_parts = [p.name or ""]
        if p.selling_points: doc_parts.append(p.selling_points)
        if p.category: doc_parts.append(p.category)
        if p.brand: doc_parts.append(p.brand)
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

    embeddings = self._embed_batch(documents)

    for i in range(0, len(ids), batch_size):
        self._collection.upsert(
            ids=batch_ids,
            documents=batch_docs,
            embeddings=batch_emb,
            metadatas=batch_meta,
        )
```

`_embed_batch` 会把文本按 32 条一批调用 SiliconFlow API，每次返回 1024 维向量：

```python
def _embed_batch(self, texts: list[str]) -> list[list[float]]:
    all_embeddings = []
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = requests.post(
            f"{_SILICONFLOW_BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {_SILICONFLOW_API_KEY}"},
            json={"model": _EMBEDDING_MODEL, "input": batch, "encoding_format": "float"},
            proxies={"http": None, "https": None},
            timeout=60,
        )
        data = response.json()
        embeddings = [None] * len(batch)
        for item in data["data"]:
            embeddings[item["index"]] = item["embedding"]
        all_embeddings.extend(embeddings)
    return all_embeddings
```

### 2.3 两阶段检索

检索逻辑在 `_search_product_by_question` 中，分为多个优先级：

1. **精确商品名匹配**：如果用户粘贴了完整商品名，优先精确匹配。
2. **核心关键词 + 分类匹配**：用 `CATEGORY_KEYWORDS` 中的关键词做 `ilike` 查询，并限制分类。
3. **通用关键词 + 分类匹配**：如果核心关键词不足，使用 `_extract_keywords` 提取的通用词。
4. **全局关键词匹配**：去掉分类限制再做一次兜底。

```python
def _search_product_by_question(self, db, question: str) -> Optional[Product]:
    # 0. 精确商品名匹配
    exact_match = self._try_exact_product_match(db, question)
    if exact_match:
        return exact_match

    # 1. 核心关键词搜索
    primary_kws = self._extract_primary_keywords(question)
    detected_category = self._detect_category(question)

    if primary_kws:
        conditions = [Product.name.ilike(f"%{kw}%") for kw in primary_kws]
        if detected_category:
            results = list(db.execute(
                select(Product).where(
                    Product.category == detected_category,
                    or_(*conditions),
                ).limit(50)
            ).scalars().all())
        else:
            results = list(db.execute(
                select(Product).where(or_(*conditions)).limit(50)
            ).scalars().all())

        # 应用价格约束、规格约束
        results = self._apply_spec_filter(results, spec_constraints)

        if results:
            best = self._vector_rerank(question, results, primary_kws, spec_constraints)
            if best:
                return best
```

### 2.4 向量重排序

第一阶段召回候选集后，第二阶段调用 `_vector_rerank`。该方法使用 `vector_index.search()` 计算查询与候选商品的语义相似度，并结合关键词匹配度、评分做综合排序：

```python
def _vector_rerank(self, question, candidates, keywords, spec_constraints, detected_category=None):
    candidate_ids = [p.id for p in candidates]
    query_text = question
    if keywords:
        query_text = question + " " + " ".join(keywords[:3])

    vector_results = vector_index.search(
        query=query_text,
        candidate_ids=candidate_ids,
        top_k=len(candidates),
    )

    if vector_results:
        sim_map = {r["product_id"]: r["similarity"] for r in vector_results}

        def combined_score(p: Product) -> float:
            vec_sim = sim_map.get(p.id, 0.0)
            kw_score = 0.0
            name_lower = (p.name or "").lower()
            for kw in keywords:
                if kw.lower() in name_lower:
                    kw_score += len(kw) * 2.0
            for sc in spec_constraints:
                if sc.lower() in name_lower:
                    kw_score += 10.0
            if detected_category and p.category == detected_category:
                kw_score += 5.0
            rating_score = (p.rating or 0) * 0.1
            return vec_sim * 0.6 + min(kw_score, 30.0) * 0.3 + rating_score * 0.1

        candidates.sort(key=combined_score, reverse=True)
        return candidates[0]
```

如果向量服务不可用或索引为空，则降级为纯关键词加权排序，确保系统不会挂掉。

---

## 3. 知识库自动构建与维护

知识库模型定义在 `backend/models/knowledge_base.py`，包含两张表：

- `knowledge_entries`：商品知识条目，类型包括 `spec`、`faq`、`after_sale`、`policy` 等。
- `qa_records`：用户问答记录，用于后续统计分析和优化。

```python
class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    keywords: Mapped[str] = mapped_column(Text, nullable=True)
    vector_data: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class QARecord(Base):
    __tablename__ = "qa_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(50), default="auto")
    source: Mapped[str] = mapped_column(String(50), default="rag")
    helpful: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```

`RAGService.auto_build_from_product()` 实现了知识库的**自动构建**：当新增或更新商品时，系统会自动从商品的 `specs`、`selling_points` 生成对应的知识条目，并补充固定的售后政策条目：

```python
def auto_build_from_product(self, product: Product) -> int:
    count = 0
    with SessionLocal() as db:
        if product.specs:
            existing = db.execute(
                select(KnowledgeEntry).where(
                    KnowledgeEntry.product_id == product.id,
                    KnowledgeEntry.category == "spec",
                )
            ).scalar_one_or_none()
            if not existing:
                entry = KnowledgeEntry(
                    product_id=product.id,
                    category="spec",
                    title=f"{product.name} - 规格参数",
                    content=product.specs,
                    keywords=json.dumps(["规格", "参数", "尺寸"], ensure_ascii=False),
                )
                db.add(entry)
                count += 1

        if product.selling_points:
            existing = db.execute(
                select(KnowledgeEntry).where(
                    KnowledgeEntry.product_id == product.id,
                    KnowledgeEntry.category == "faq",
                )
            ).scalar_one_or_none()
            if not existing:
                entry = KnowledgeEntry(
                    product_id=product.id,
                    category="faq",
                    title=f"{product.name} - 核心卖点",
                    content=product.selling_points,
                    keywords=json.dumps(["卖点", "特点", "优势"], ensure_ascii=False),
                )
                db.add(entry)
                count += 1

        existing = db.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.product_id == product.id,
                KnowledgeEntry.category == "after_sale",
            )
        ).scalar_one_or_none()
        if not existing:
            entry = KnowledgeEntry(
                product_id=product.id,
                category="after_sale",
                title=f"{product.name} - 售后政策",
                content="支持7天无理由退换货，质量问题30天内包退换，提供一年质保服务。",
                keywords=json.dumps(["退换", "售后", "保修", "质保"], ensure_ascii=False),
            )
            db.add(entry)
            count += 1

        db.commit()
    return count
```

`search_knowledge` 则用于在知识库中检索相关条目，相似度计算综合考虑关键词命中、标题命中、内容命中：

```python
def _calculate_similarity(self, question, question_keywords, entry):
    score = 0.0
    entry_text = f"{entry.title} {entry.content}"
    for kw in question_keywords:
        if kw in entry_text:
            score += 0.3
        if entry.keywords:
            entry_kws = json.loads(entry.keywords)
            if kw in entry_kws:
                score += 0.5
    if question in entry.content:
        score += 0.5
    for kw in question_keywords:
        if kw in entry.title:
            score += 0.2
    return score
```

每次问答完成后，系统都会写入 `QARecord`，并通过 `get_qa_stats` 统计问题类型分布、来源分布、热词等，为运营优化提供数据。

---

## 4. 问题分类（售前/售后/闲聊）与答案生成

`RAGService._detect_question_type()` 是问题分类的入口。虽然代码中没有直接叫“售前/售后/闲聊”，但实际分出来的类型覆盖了这三类场景：

- **售前咨询**：`recommend`（推荐）、`price`（价格/性价比）、`brand`（品牌）、`function`（功能/使用）、`size`（尺寸/规格）、`compare`（对比）。
- **售后问题**：`after_sale`（退换、保修、运费、发票、质保）。
- **闲聊/通用**：`general`（打招呼、无明确商品的问题）。

分类实现基于关键词匹配：

```python
def _detect_question_type(self, question: str) -> str:
    q = question.lower()

    if any(kw in q for kw in ["推荐", "有什么", "哪些", "哪个好", "求推荐", "适合", "建议买"]):
        return "recommend"

    if any(kw in q for kw in ["多少钱", "价格", "贵不贵", "便宜", "划算", "性价比", "预算", "值得", "值不值"]):
        return "price"

    if any(kw in q for kw in ["品牌", "牌子", "厂家", "生产商", "怎么样", "好不好"]):
        for brand in BRAND_KNOWLEDGE:
            if brand.lower() in q:
                return "brand"
        if any(kw in q for kw in ["品牌", "牌子"]):
            return "brand"

    if any(kw in q for kw in ["评价", "评论", "口碑", "好评", "差评", "评分", "几分", "怎么样"]):
        return "review"

    if any(kw in q for kw in ["对比", "比较", "哪个好", "区别", "差异", "vs"]):
        return "compare"

    if any(kw in q for kw in ["多高", "多大", "尺寸", "大小", "重量", "多重", "尺码", "码数", "规格", "容量"]):
        return "size"

    if any(kw in q for kw in ["功能", "作用", "怎么用", "使用", "操作", "安装", "材质", "材料", "面料", "续航", "电池", "充电", "防水", "效果"]):
        return "function"

    if any(kw in q for kw in ["退", "换", "售后", "保修", "运费", "发票", "质保"]):
        return "after_sale"

    return "general"
```

分类完成后，`_build_data_driven_answer` 根据类型调用对应的回答构建器：

```python
def _build_data_driven_answer(self, question, q_type, product, reviews, related):
    if q_type == "price":
        return self._answer_price(product, related, question)
    elif q_type == "recommend":
        return self._answer_recommend(product, related, question)
    elif q_type == "brand":
        return self._answer_brand(product, question)
    elif q_type == "function":
        return self._answer_function(product, reviews, question)
    elif q_type == "size":
        return self._answer_size(product, question)
    elif q_type == "review":
        return self._answer_review(product, reviews, question)
    elif q_type == "after_sale":
        return self._answer_after_sale(product, question)
    elif q_type == "compare":
        return self._answer_compare(product, related, question)
    else:
        return self._answer_general(product, reviews, related, question)
```

以价格类为例，`_answer_price` 不是简单返回价格，而是结合同类商品均价做性价比判断：

```python
def _answer_price(self, product, related, question):
    price = product.price or 0
    rating = product.rating or 5.0

    if related:
        avg_price = sum(p.price or 0 for p in related) / len(related)
        if price < avg_price * 0.8 and rating >= 4.5:
            value_assessment = f"这款商品定价 ¥{price:.0f}，低于同类均价 ¥{avg_price:.0f}，评分高达 {rating} 分，性价比非常突出！"
        elif price < avg_price:
            value_assessment = f"定价 ¥{price:.0f} 略低于同类均价 ¥{avg_price:.0f}，配合 {rating} 分的评分，性价比不错。"
        elif price > avg_price * 1.3:
            value_assessment = f"定价 ¥{price:.0f} 略高于同类均价 ¥{avg_price:.0f}，但评分 {rating} 分，如果您追求品质可以考虑。"
        else:
            value_assessment = f"定价 ¥{price:.0f}，处于同类商品正常价格区间，评分 {rating} 分，整体性价比合理。"
```

如果配置了真实 LLM，系统还会调用 `_generate_ai_answer` 或 `_generate_ai_answer_stream`，把商品信息、评论、推荐商品组装成上下文，让模型生成更自然的口语化回答。Prompt 示例：

```python
system_prompt = """你是一位专业的电商导购助手，擅长根据用户需求推荐合适的商品。
请基于提供的商品数据，用自然、亲切的语气回答用户问题。

要求：
1. 回答要口语化、有温度，像朋友聊天一样
2. 直接给出推荐商品的核心信息（名称、价格、评分）
3. 突出商品的卖点和优势
4. 如果有同类推荐，简要提及2-3个备选
5. 回答控制在200字以内，简洁有力
6. 不要编造数据，只使用提供的商品信息"""
```

---

## 5. 流式输出（SSE）实现

为了提升用户体验，AI 问答接口支持 SSE（Server-Sent Events）流式输出，前端可以实时看到文字逐个出现，而不是等待完整回答返回。

后端入口是 `backend/api/user_routes.py` 中的 `/user/qa/stream`：

```python
@user_bp.post("/user/qa/stream")
def qa_stream():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    product_id = _safe_int(data.get("product_id"))

    def generate():
        try:
            for event in rag_service.answer_question_stream(
                question=question,
                product_id=product_id,
                user_id=user_payload["user_id"],
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"SSE问答失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

流式生成的核心在 `RAGService.answer_question_stream()`：

```python
def answer_question_stream(self, question, product_id=None, user_id=None):
    q_type = self._detect_question_type(question)

    # 1. 检索商品与推荐
    product = ...
    related_products = ...
    reviews = ...

    # 2. 先推送结构化数据（商品卡片、推荐列表）
    if product:
        yield {"type": "product", "data": {...}}
    if related_products:
        yield {"type": "related", "data": [...]}

    # 3. 流式推送 AI 文本
    full_answer = ""
    if product:
        for text_chunk in self._generate_ai_answer_stream(
            question, q_type, product, reviews, related_products
        ):
            full_answer += text_chunk
            yield {"type": "text", "content": text_chunk}
    else:
        full_answer = self._build_no_match_answer(question, q_type)
        yield {"type": "text", "content": full_answer}

    # 4. 记录问答并结束
    # ... 写入 QARecord ...
    yield {"type": "done"}
```

`_generate_ai_answer_stream` 通过 `stream=True` 调用 OpenAI SDK，并逐个 `yield` token：

```python
stream = client.chat.completions.create(
    model=model,
    messages=[...],
    temperature=0.7,
    max_tokens=500,
    stream=True,
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        yield chunk.choices[0].delta.content
```

前端 `frontend/src/components/common/ChatWidget.vue` 使用 `fetch + ReadableStream` 消费 SSE：

```typescript
const response = await fetch(`${API_BASE}/api/user/qa/stream`, {
  method: 'POST',
  headers: authHeaders(),
  body: JSON.stringify({ question: text }),
})

const reader = response.body.getReader()
const decoder = new TextDecoder()
let buffer = ''

while (true) {
  const { done, value } = await reader.read()
  if (done) break

  buffer += decoder.decode(value, { stream: true })
  const lines = buffer.split('\n')
  buffer = lines.pop() || ''

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6))
      if (event.type === 'product') {
        assistantMsg.product = event.data
      } else if (event.type === 'related') {
        assistantMsg.relatedProducts = event.data
      } else if (event.type === 'text') {
        assistantMsg.content += event.content
      }
      scrollToBottom()
    }
  }
}
```

SSE 事件类型包括：

- `product`：主推商品卡片数据。
- `related`：同类推荐商品列表。
- `text`：AI 生成的文本片段。
- `error`：发生错误时的消息。
- `done`：流结束标记。

---

## 6. 价格过滤、品牌匹配等业务规则

### 6.1 价格过滤

`RAGService` 支持从自然语言问题中解析多种价格约束：

```python
def _extract_price_constraint(self, question: str) -> Optional[float]:
    normalized = question.replace("一下", "以下")
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:元|块钱?|RMB|￥)\s*(?:以内|以下|内|之内)',
        r'(?:不超过|不高于|最多|预算)\s*(\d+(?:\.\d+)?)',
        r'(?:以内|以下|内|之内)\s*(\d+(?:\.\d+)?)\s*(?:元|块钱?)',
        r'(\d+(?:\.\d+)?)\s*[-~到]\s*\d+(?:\.\d+)?\s*(?:元|块钱?)',
        r'低于\s*(\d+(?:\.\d+)?)',
        r'小于\s*(\d+(?:\.\d+)?)',
    ]
    for pattern in patterns:
        m = re.search(pattern, normalized)
        if m:
            return float(m.group(1))
    return None
```

同时支持“左右”类模糊价格范围：

```python
def _extract_price_range(self, question: str) -> Optional[tuple[float, float]]:
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:元|块钱?|RMB|￥)\s*(?:左右|上下|差不多|前后)', normalized)
    if m:
        center = float(m.group(1))
        return (center * 0.7, center * 1.3)

    m = re.search(r'(?:左右|大约|大概|约|差不多)\s*(\d+(?:\.\d+)?)\s*(?:元|块钱?)', normalized)
    if m:
        center = float(m.group(1))
        return (center * 0.7, center * 1.3)

    m = re.search(r'(\d+(?:\.\d+)?)\s*[-~到]\s*(\d+(?:\.\d+)?)\s*(?:元|块钱?)', normalized)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    return None
```

提取到的价格约束会在候选召回和推荐阶段应用：

```python
if price_limit:
    price_filtered = [p for p in related_products if (p.price or 0) <= price_limit]
    if price_filtered:
        related_products = price_filtered
elif price_range:
    price_filtered = [p for p in related_products if price_range[0] <= (p.price or 0) <= price_range[1]]
    if price_filtered:
        related_products = price_filtered
```

### 6.2 品牌匹配

品牌信息可能来自商品 `brand` 字段，也可能需要从商品名中推断。`_get_real_brand` 实现了这一逻辑：

```python
def _get_real_brand(self, product: Product) -> str:
    brand = product.brand or ""
    if brand in ("苏宁自营", "", "无", "未知"):
        name = product.name or ""
        name_start = name[:20]

        if "/" in name_start:
            parts = name_start.split("/")
            for part in parts:
                for brand_key in BRAND_KNOWLEDGE:
                    if brand_key.lower() in part.lower():
                        return brand_key

        for brand_key in BRAND_KNOWLEDGE:
            if brand_key.lower() in name_start.lower():
                return brand_key
    return brand or "通用"
```

系统还维护了一份 `BRAND_KNOWLEDGE` 品牌知识库字典，覆盖数码、家居、美妆、母婴、宠物、运动等品牌：

```python
BRAND_KNOWLEDGE: dict[str, str] = {
    "华为": "华为是全球领先的ICT基础设施和智能终端提供商，产品涵盖手机、电脑、可穿戴设备等，以技术创新和高品质著称。",
    "Apple": "Apple（苹果）是全球知名科技公司，以iPhone、Mac、AirPods等产品闻名，注重设计美学和用户体验。",
    "欧莱雅": "欧莱雅（L'Oreal）是全球最大的化妆品集团之一，产品涵盖护肤、彩妆、染发等，以科研创新和高品质著称。",
    "飞鹤": "飞鹤乳业是中国领先的婴幼儿奶粉品牌，以新鲜生牛乳配方和适合中国宝宝体质著称。",
    "皇家": "皇家（ROYAL CANIN）是法国知名宠物食品品牌，以科学配方和精准营养著称，产品涵盖猫粮狗粮。",
    # ... 更多品牌
}
```

当用户问品牌相关问题时，`_answer_brand` 会先在知识库中查找：

```python
def _answer_brand(self, product: Product, question: str) -> str:
    brand = self._get_real_brand(product)

    brand_info = None
    for brand_key, info in BRAND_KNOWLEDGE.items():
        if brand_key.lower() in brand.lower() or brand.lower() in brand_key.lower():
            brand_info = info
            break

    parts = [f"「{product.name}」的品牌是{brand}。"]
    if brand_info:
        parts.append(f"\n品牌介绍：{brand_info}")
```

### 6.3 规格约束过滤

规格约束包括年龄段（如奶粉段数）、适用人群、服装尺码等。`_extract_spec_constraints` 从问题中提取这些关键词：

```python
def _extract_spec_constraints(self, question: str) -> list[str]:
    constraints = []

    age_patterns = [
        (r'0\s*[-~到]\s*(?:6|3)\s*个?月', ['1段', '0-6', '0~6', '0-3', '0~3', '新生儿', '初生']),
        (r'(?:6|3)\s*[-~到]\s*12\s*个?月', ['2段', '6-12', '6~12', '较大']),
        (r'1?\s*[-~到]\s*3?\s*岁', ['3段', '12-36', '12~36', '1-3', '幼儿']),
    ]
    for pattern, required_kws in age_patterns:
        if re.search(pattern, question):
            constraints.extend(required_kws)
            break

    audience_patterns = [
        (r'(?:老人|老年|长辈|爷爷|奶奶)', ['老人', '老年', '长辈', '中老年', '父母']),
        (r'(?:学生|学生党|宿舍|校园)', ['学生', '校园', '宿舍', '学生党']),
        (r'(?:儿童|小孩|孩子|幼儿|宝宝)', ['儿童', '小孩', '孩子', '幼儿', '宝宝', '婴儿']),
        (r'(?:孕妇|孕妈|怀孕)', ['孕妇', '孕妈', '怀孕', '妈咪']),
        (r'(?:男士|男人|男生)', ['男士', '男', '先生']),
        (r'(?:女士|女人|女生)', ['女士', '女', '小姐', '姑娘']),
    ]
    for pattern, required_kws in audience_patterns:
        if re.search(pattern, question):
            constraints.extend(required_kws)
            break

    size_patterns = [r'[Xx]+[LlSs]', r'\d+码', r'均码']
    for pattern in size_patterns:
        m = re.search(pattern, question)
        if m:
            constraints.append(m.group(0).upper())

    return constraints
```

`_apply_spec_filter` 对候选商品做过滤，要求商品名至少包含一个约束关键词；如果过滤后为空，则返回原始列表做降级：

```python
def _apply_spec_filter(self, products: list[Product], spec_constraints: list[str]) -> list[Product]:
    if not spec_constraints:
        return products
    filtered = []
    for p in products:
        name_lower = (p.name or "").lower()
        if any(c.lower() in name_lower for c in spec_constraints):
            filtered.append(p)
    return filtered if filtered else products
```

### 6.4 同类推荐规则

当系统找到主商品后，会基于同分类 + 商品类型关键词搜索同类推荐，并应用价格和规格约束：

```python
product_type_kws = []
product_name_lower = (product.name or "").lower()
for kw in primary_kws:
    if kw.lower() in product_name_lower:
        product_type_kws.append(kw)

search_kws_for_related = product_type_kws if product_type_kws else primary_kws

if search_kws_for_related:
    search_kws_for_related.sort(key=len, reverse=True)
    top_kws = search_kws_for_related[:2]
    kw_filter = [Product.name.ilike(f"%{kw}%") for kw in top_kws]
    from sqlalchemy import and_ as sql_and
    related_products = list(db.execute(
        select(Product).where(
            Product.category == product.category,
            Product.id != product.id,
            sql_and(*kw_filter),
        ).order_by(Product.rating.desc()).limit(10)
    ).scalars().all())

    # 如果 AND 过滤结果太少，降级为 OR
    if len(related_products) < 2 and len(top_kws) > 1:
        kw_conditions = [Product.name.ilike(f"%{kw}%") for kw in top_kws]
        related_products = list(db.execute(
            select(Product).where(
                Product.category == product.category,
                Product.id != product.id,
                or_(*kw_conditions),
            ).order_by(Product.rating.desc()).limit(10)
        ).scalars().all())
```

推荐结果最终按评分降序，并截取前 5 个，前 3 个会随回答一起推送给前端展示为商品卡片。

---

## 7. 小结

本项目的 AI 模块围绕**智能导购问答**和**内容生成**两条主线展开：

- **Provider 模式**实现了模型实现的灵活切换与自动降级。
- **RAG 双阶段检索**（规则过滤 + 向量重排序）保证了召回准确率和语义排序质量。
- **知识库自动构建**把商品结构化信息沉淀为可检索、可统计的知识条目。
- **问题分类 + 模板/LLM 生成**让回答既基于真实数据，又具备自然语言温度。
- **SSE 流式输出**提升了前端交互体验。
- **价格、品牌、规格等业务规则**让推荐结果更贴近用户真实需求。

整个模块的设计原则是：**数据驱动、可降级、可扩展、可观测**。所有外部依赖（LLM、Embedding API）都有明确的 fallback 路径，所有问答行为都会落库便于后续分析优化。

---

## 8. 售后问题兜底与相关推荐抑制

### 8.1 售后问题分类

`_detect_question_type` 通过关键词将包含“退、换、售后、保修、运费、发票、质保”的问题统一标记为 `after_sale`：

```python
# backend/services/rag_service.py
# 售后类
if any(kw in q for kw in ["退", "换", "售后", "保修", "运费", "发票", "质保"]):
    return "after_sale"
```

这一分类贯穿后续检索、回答构建与响应组装全流程。

### 8.2 无商品匹配时的售后兜底

当数据库中没有匹配到具体商品时，`_build_no_match_answer` 不再返回通用的“未找到商品”提示，而是直接给出平台售后政策：

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

该兜底不依赖任何商品数据，因此即使向量索引、数据库查询均失败，也能给出稳定、可解释的回答。

### 8.3 命中商品时抑制无关推荐

当用户问题命中某商品且类型为 `after_sale` 时，`_answer_after_sale` 会返回该商品的售后说明。但此前返回的相关推荐列表可能包含与售后无关的商品，影响用户体验。修复方案是在 `answer_question` 组装响应前清空相关推荐：

```python
# backend/services/rag_service.py
# 售后/退换货问题只回答政策，不展示可能不相关的推荐商品
if q_type == "after_sale":
    related_products = []
```

由于 `related_info` 随后从 `related_products` 构建，前端收到的 `related_products` 为空数组，`ChatWidget.vue` 中的 `v-if="msg.relatedProducts && msg.relatedProducts.length"` 不会渲染商品卡片。

### 8.4 测试验证

售后兜底可通过直接调用问答接口验证：

```python
import requests
url = 'http://localhost:8000/api/user/qa/ask'
headers = {'Authorization': 'Bearer <token>', 'Content-Type': 'application/json'}
for q in ['如何退换货', '怎么退货', '换货流程', '售后保修']:
    r = requests.post(url, json={'question': q}, headers=headers)
    print(q, r.status_code, r.json()['answer'][:60])
```

预期所有问题均返回 200，且回答中包含“平台售后政策”。