# E-Commerce AI Copy Guide — AI Intelligent Service Layer

Production-quality AI service for an intelligent e-commerce assistant system.  
Built with **FastAPI + LangChain + FAISS + DeepSeek**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Backend (Flask)                     │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP / JSON
┌─────────────────────▼───────────────────────────────────┐
│                   AI Gateway (FastAPI)                   │
│                  gateway/router.py                       │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  Prompt Engine                           │
│            prompts/*.txt  +  PromptLoader                │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│               Knowledge Engine (RAG)                     │
│   DocumentLoader → TextSplitter → Embedding → FAISS     │
│                      → Retriever                         │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                 LLM Dispatcher                           │
│           BaseLLMProvider  →  DeepSeekProvider           │
│         (extensible: Qwen, OpenAI, Claude, …)           │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│               Business Services                          │
│  Title  │ Description │ Q&A(RAG) │ Sentiment │ Rec │ Live│
└─────────────────────────────────────────────────────────┘
```

**Key design principles:**

- **Never call LLM directly** — always through `LLMDispatcher` so providers are swappable.
- **Prompts as `.txt` files** — never hardcoded in Python.
- **SOLID** — each class has a single responsibility; dependency injection throughout.
- **Extensible** — reserved interfaces for Qwen, Llama, OpenAI, Claude, Milvus, ChromaDB, Redis.

---

## Folder Structure

```
ai_service/
├── app.py                     # FastAPI entrypoint + lifespan
├── config/
│   └── settings.py            # Pydantic Settings (reads .env)
├── gateway/
│   └── router.py              # API routes (/title, /chat, …)
├── llm/
│   ├── dispatcher.py          # LLMDispatcher (central router)
│   └── deepseek.py            # BaseLLMProvider + DeepSeekProvider
├── models/
│   ├── request.py             # Pydantic request schemas
│   └── response.py            # Pydantic response schemas
├── prompts/
│   ├── title.txt              # Product title generation template
│   ├── description.txt        # Product description template
│   ├── qa.txt                 # RAG Q&A template
│   ├── sentiment.txt          # Sentiment analysis template
│   └── livestream.txt         # Livestream script template
├── rag/
│   ├── embedding.py           # SentenceTransformer wrapper
│   ├── loader.py              # DocumentLoader + TextSplitter
│   ├── retriever.py           # High-level RAG orchestrator
│   └── vector_store.py        # FAISS IndexIDMap wrapper
├── services/
│   ├── copywriting.py         # TitleGenerator + DescriptionGenerator
│   ├── livestream.py          # LivestreamScriptGenerator
│   ├── qa.py                  # ShoppingAssistant (RAG)
│   ├── recommendation.py      # RecommendationEngine (embedding similarity)
│   └── sentiment.py           # SentimentAnalyser
└── utils/
    ├── logger.py              # Loguru configuration
    └── prompt_loader.py       # Template loader + variable interpolation
```

---

## Installation

### Prerequisites

- Python 3.11+
- Conda (recommended) or venv
- Git

### Setup

```bash
# 1. Clone
git clone <repo-url>
cd ecommerce-ai-copy-guide

# 2. Create & activate environment
conda create -n env_1 python=3.11 -y
conda activate env_1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env → set DEEPSEEK_API_KEY=sk-xxxxxxxx
```

### Install FAISS (alternative)

If `faiss-cpu` fails on Windows:

```bash
conda install -c conda-forge faiss-cpu
```

---

## Configuration

Edit `.env`:

| Variable | Default | Description |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | **Required.** Your DeepSeek API key |
| `BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible endpoint |
| `MODEL_NAME` | `deepseek-chat` | Model identifier |
| `LLM_TEMPERATURE` | `0.7` | Sampling temperature |
| `LLM_MAX_TOKENS` | `2048` | Max response tokens |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | SentenceTransformer model |
| `TOP_K` | `5` | Chunks retrieved per query |
| `CHUNK_SIZE` | `512` | Characters per text chunk |
| `SIMILARITY_THRESHOLD` | `0.65` | Minimum cosine similarity for recommendations |

---

## Usage

### Start the server

```bash
# Development (hot-reload)
uvicorn ai_service.app:app --host 0.0.0.0 --port 8000 --reload

# Or via Python
python -m ai_service.app
```

### API docs

Open [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger) or  
[http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc).

---

## API Reference

### 1. Product Title Generator

```http
POST /api/v1/title
```

**Request:**

```json
{
  "product_name": "无线蓝牙耳机",
  "features": "主动降噪 蓝牙5.3 30小时续航 IPX5防水",
  "category": "数码配件"
}
```

**Response:**

```json
{
  "titles": [
    "主动降噪无线蓝牙耳机 30小时超长续航",
    "IPX5防水运动耳机 蓝牙5.3畅快连接",
    "..."
  ]
}
```

---

### 2. Product Description Generator

```http
POST /api/v1/description
```

**Request:**

```json
{
  "product_name": "无线蓝牙耳机",
  "features": "主动降噪 蓝牙5.3",
  "specifications": "重量: 48g, 驱动单元: 13mm",
  "target_audience": "上班族、学生",
  "category": "数码配件"
}
```

**Response:**

```json
{
  "description": "## 产品概述\n\n这款无线蓝牙耳机…"
}
```

---

### 3. Intelligent Shopping Assistant (RAG)

```http
POST /api/v1/chat
```

**Prerequisite:** Call `/api/v1/ingest` first to load product data.

**Request:**

```json
{
  "question": "有没有适合跑步时戴的耳机？"
}
```

**Response:**

```json
{
  "answer": "根据您的需求，推荐以下几款运动耳机…",
  "has_relevant_info": true,
  "related_products": ["运动蓝牙耳机 Pro", "骨传导跑步耳机"],
  "sources": [{ "text": "…", "score": 0.9234 }]
}
```

---

### 4. Review Sentiment Analysis

```http
POST /api/v1/sentiment
```

**Request:**

```json
{
  "reviews": ["音质很棒，戴着也舒服", "续航不行，用了两天就没电了", "…"]
}
```

**Response:**

```json
{
  "positive_rate": "65.50%",
  "negative_rate": "12.30%",
  "neutral_rate": "22.20%",
  "total_count": 120,
  "key_complaints": ["续航不足", "佩戴不舒适"],
  "key_praises": ["音质出色", "性价比高"],
  "summary": "用户整体满意度较高，音质和性价比是最大的亮点…"
}
```

---

### 5. Product Recommendation

```http
POST /api/v1/recommend
```

**Prerequisite:** Same as `/chat` — products must be ingested first.

**Request:**

```json
{
  "product_name": "无线蓝牙耳机",
  "features": "主动降噪",
  "category": "数码配件",
  "top_n": 5
}
```

**Response:**

```json
{
  "recommendations": [
    { "product_name": "…", "similarity_score": 0.9234, "features": "…" },
    { "product_name": "…", "similarity_score": 0.8762, "features": "…" }
  ]
}
```

---

### 6. Livestream Script Generator

```http
POST /api/v1/livestream
```

**Request:**

```json
{
  "product_name": "无线蓝牙耳机",
  "features": "主动降噪 蓝牙5.3",
  "promotion": "限时特价199元，买一送一",
  "target_audience": "年轻上班族",
  "category": "数码配件"
}
```

**Response:**

```json
{
  "script": "## 1. 开场暖场（30秒）\n家人们晚上好！…",
  "estimated_total_duration": "4分30秒",
  "key_talking_points": ["主动降噪技术", "超高性价比"]
}
```

---

### Utility: Ingest Products

```http
POST /api/v1/ingest
```

Load product data into the RAG knowledge base. Accepts a JSON array of product objects.

```json
[
  {
    "name": "无线蓝牙耳机",
    "category": "数码配件",
    "description": "高品质无线蓝牙耳机",
    "features": "主动降噪 蓝牙5.3 30小时续航",
    "price": "299元"
  }
]
```

---

## Extensibility

### Swap LLM provider

Create a new class inheriting from `BaseLLMProvider`:

```python
from ai_service.llm.deepseek import BaseLLMProvider

class QwenProvider(BaseLLMProvider):
    def generate(self, prompt, **kwargs) -> str:
        # Custom implementation
        ...

# At runtime:
dispatcher.swap_provider(QwenProvider())
```

### Swap vector store

The `VectorStore` class can be replaced with a ChromaDB or Milvus adapter — implement the same interface (`add`, `search`, `save`, `load`, `count`).

---

## License

MIT
