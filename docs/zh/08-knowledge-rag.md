# RAG 知识检索机制

## 1. Knowledge 概述

CrewAI 的 Knowledge 系统是基于 RAG（Retrieval Augmented Generation，检索增强生成）架构的知识检索系统。它允许 Agent 访问私有知识库，通过向量搜索找到相关信息，并将检索结果融入到 Agent 的上下文中。

---

## 2. 核心组件

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Knowledge System Architecture                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Knowledge Base                             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │   │
│  │  │  Document   │  │   Text      │  │   Structured Data     │ │   │
│  │  │  Loader     │  │   Splitter  │  │   (JSON, CSV, etc.)    │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Embedding Model                              │   │
│  │           (OpenAI, Cohere, HuggingFace, etc.)                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Vector Store                                 │   │
│  │              (LanceDB, Qdrant, Chroma, etc.)                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   Retrieval Flow                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │   │
│  │  │   Query      │  │  Semantic   │  │   Re-ranking           │ │   │
│  │  │   Processing │  │   Search    │  │   (Optional)           │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Knowledge 基类

### 3.1 类定义

```python
from crewai.knowledge import Knowledge

class Knowledge:
    """知识库基类"""
    
    def __init__(
        self,
        sources: list[Source] | None = None,
        embedder: BaseEmbedder | str | None = None,
        storage: StorageBackend | str | None = None,
        chunk_size: int = 2000,
        chunk_overlap: int = 200
    ):
        self.sources = sources or []
        self.embedder = self._setup_embedder(embedder)
        self.storage = self._setup_storage(storage)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
```

### 3.2 核心方法

| 方法 | 说明 |
|------|------|
| `load()` | 加载知识源 |
| `retrieve(query)` | 检索相关知识 |
| `add_source(source)` | 添加新知识源 |
| `search(query, top_k)` | 向量搜索 |

---

## 4. 知识源类型

### 4.1 文本源

```python
from crewai.knowledge.source.text_source import TextSource

# 从字符串加载
source = TextSource(
    content="Your knowledge content here",
    metadata={"category": "general", "source": "manual"}
)
```

### 4.2 文件源

```python
from crewai.knowledge.source.pdf_source import PDFSource
from crewai.knowledge.source.txt_source import TextFileSource
from crewai.knowledge.source.docx_source import DocxSource

# PDF 文件
pdf_source = PDFSource(
    file_path="./documents/report.pdf",
    metadata={"category": "report", "year": 2024}
)

# 文本文件
txt_source = TextFileSource(
    file_path="./documents/notes.txt"
)

# Word 文档
docx_source = DocxSource(
    file_path="./documents/article.docx"
)
```

### 4.3 结构化数据源

```python
from crewai.knowledge.source.json_source import JSONSource
from crewai.knowledge.source.csv_source import CSVSource

# JSON 数据
json_source = JSONSource(
    file_path="./data/products.json",
    value_key="description"  # 用于嵌入的字段
)

# CSV 数据
csv_source = CSVSource(
    file_path="./data/customers.csv",
    text_columns=["name", "email", "address"]
)
```

### 4.4 网页源

```python
from crewai.knowledge.source.web_source import WebSource

# 从 URL 加载
web_source = WebSource(
    urls=[
        "https://example.com/page1",
        "https://example.com/page2"
    ],
    metadata={"source": "website"}
)
```

---

## 5. 知识库创建

### 5.1 基础创建

```python
from crewai.knowledge import Knowledge
from crewai.knowledge.source import TextSource, PDFSource

# 创建知识库
knowledge = Knowledge(
    sources=[
        TextSource(
            content="CrewAI is a multi-agent collaboration framework...",
            metadata={"category": "documentation"}
        ),
        PDFSource(
            file_path="./docs/technical_manual.pdf"
        )
    ]
)

# 加载知识
knowledge.load()
```

### 5.2 使用 Embedder

```python
from crewai.embeddings import OpenAIEmbedder
from langchain_community.embeddings import HuggingFaceEmbeddings

# OpenAI Embeddings
knowledge = Knowledge(
    embedder=OpenAIEmbedder(
        model="text-embedding-3-small"
    ),
    sources=sources
)

# HuggingFace Embeddings (本地)
knowledge = Knowledge(
    embedder=HuggingFaceEmbeddings(
        model="sentence-transformers/all-MiniLM-L6-v2"
    ),
    sources=sources
)
```

### 5.3 使用 Vector Store

```python
from crewai.memory.storage.lancedb import LanceDbStorage
from crewai.memory.storage.qdrant import QdrantStorage

# LanceDB (默认)
knowledge = Knowledge(
    storage=LanceDbStorage(
        path="./knowledge_db"
    ),
    sources=sources
)

# Qdrant
knowledge = Knowledge(
    storage=QdrantStorage(
        host="localhost",
        port=6333,
        collection="my_knowledge"
    ),
    sources=sources
)
```

---

## 6. 检索流程详解

### 6.1 检索流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         knowledge.retrieve()                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              1. Query Processing                                        │
│  - 编码查询文本                                                         │
│  - 提取关键词                                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              2. Vector Search                                           │
│  - 在向量数据库中搜索相似文档                                           │
│  - 返回 top-k 结果                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              3. Re-ranking (Optional)                                   │
│  - 使用交叉编码器重新排序结果                                           │
│  - 提高相关性                                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              4. Context Formatting                                      │
│  - 格式化检索结果为上下文                                               │
│  - 添加来源信息                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    返回检索结果                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 检索代码

```python
def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
    """检索相关知识"""
    
    # 1. 编码查询
    query_embedding = self.embedder.embed(query)
    
    # 2. 向量搜索
    results = self.storage.search(
        query_embedding=query_embedding,
        top_k=top_k
    )
    
    # 3. 格式化结果
    return self._format_results(results)
```

---

## 7. 检索配置

### 7.1 分块配置

```python
knowledge = Knowledge(
    # 分块大小
    chunk_size=2000,        # 每个块的最大字符数
    chunk_overlap=200,      # 块之间的重叠字符数
    
    # 分块策略
    chunk_strategy="markdown",  # 或 "sentence", "recursive"
    
    sources=sources
)
```

### 7.2 检索配置

```python
knowledge = Knowledge(
    # 检索参数
    top_k=5,                    # 返回结果数量
    similarity_threshold=0.7,   # 相似度阈值
    enable_reranking=True,      # 启用重排序
    
    sources=ssources
)
```

### 7.3 完整配置

```python
knowledge = Knowledge(
    # 来源
    sources=[
        TextSource(content="..."),
        PDFSource(file_path="...")
    ],
    
    # Embedder
    embedder="openai",  # 或自定义
    
    # 存储
    storage="lancedb",
    storage_path="./vector_db",
    
    # 分块
    chunk_size=1500,
    chunk_overlap=150,
    
    # 检索
    top_k=3,
    similarity_threshold=0.75,
    enable_reranking=False
)
```

---

## 8. 在 Agent 中使用 Knowledge

### 8.1 基础集成

```python
from crewai import Agent, Knowledge

# 创建知识库
knowledge = Knowledge(
    sources=[...],
    embedder=OpenAIEmbedder()
)

# 创建 Agent 并关联知识库
researcher = Agent(
    role="Research Analyst",
    goal="Provide accurate information using knowledge base",
    knowledge=knowledge,  # 关联知识库
    tools=[search_tool]
)
```

### 8.2 多知识库

```python
# 多个知识库
knowledge_general = Knowledge(sources=general_sources)
knowledge_domain = Knowledge(sources=domain_sources)

agent = Agent(
    role="Expert",
    knowledge=[knowledge_general, knowledge_domain]
)
```

### 8.3 知识库缓存

```python
# 预加载知识库以提高性能
knowledge = Knowledge(
    sources=sources,
    embedder=embedder,
    storage=storage,
    preload=True  # 启动时加载
)

agent = Agent(
    role="Assistant",
    knowledge=knowledge
)
```

---

## 9. 知识库管理

### 9.1 添加知识

```python
# 添加新文档
knowledge.add_source(
    PDFSource(file_path="./new_document.pdf")
)
knowledge.load()

# 添加文本
knowledge.add_source(
    TextSource(
        content="New information to add",
        metadata={"category": "updates"}
    )
)
knowledge.load()
```

### 9.2 更新知识

```python
# 重新加载所有知识源
knowledge.reload()

# 更新特定文档
knowledge.update_source(
    source_id="doc_123",
    new_content="Updated content"
)
```

### 9.3 删除知识

```python
# 删除特定文档
knowledge.delete(source_id="doc_123")

# 清空知识库
knowledge.clear()

# 按条件删除
knowledge.delete_by_metadata(category="deprecated")
```

---

## 10. 检索结果处理

### 10.1 RetrievalResult 结构

```python
class RetrievalResult(BaseModel):
    content: str              # 检索到的内容
    metadata: dict            # 元数据
    similarity_score: float   # 相似度分数
    source: str               # 来源标识
    chunk_index: int          # 块索引
```

### 10.2 处理检索结果

```python
# 检索知识
results = knowledge.retrieve("What is CrewAI?")

# 处理结果
for result in results:
    print(f"Content: {result.content}")
    print(f"Source: {result.metadata.get('source')}")
    print(f"Score: {result.similarity_score}")
```

### 10.3 格式化上下文

```python
def format_context(results: list[RetrievalResult]) -> str:
    """将检索结果格式化为上下文"""
    context_parts = []
    
    for i, result in enumerate(results, 1):
        context_parts.append(
            f"[Source {i}]({result.source}):\n{result.content}"
        )
    
    return "\n\n".join(context_parts)
```

---

## 11. 示例

### 11.1 完整示例

```python
from crewai import Agent, Task
from crewai.knowledge import Knowledge
from crewai.knowledge.source import PDFSource, TextSource
from crewai.embeddings import OpenAIEmbedder

# 1. 创建知识库
knowledge = Knowledge(
    sources=[
        PDFSource(file_path="./docs/company_policy.pdf"),
        TextSource(
            content="Company mission: To revolutionize AI collaboration",
            metadata={"category": "mission"}
        )
    ],
    embedder=OpenAIEmbedder(model="text-embedding-3-small"),
    chunk_size=1000
)

# 2. 加载知识
knowledge.load()

# 3. 创建 Agent
researcher = Agent(
    role="Company Policy Expert",
    goal="Answer questions using company knowledge base",
    knowledge=knowledge
)

# 4. 创建任务
task = Task(
    description="What is the company's policy on remote work?",
    agent=researcher
)

# 5. 执行
result = task.execute()
```

### 11.2 自定义 Embedder

```python
from crewai.embeddings.base import BaseEmbedder

class CustomEmbedder(BaseEmbedder):
    def embed(self, texts: list[str]) -> list[list[float]]:
        # 自定义嵌入逻辑
        return self.model.encode(texts)
    
    def embed_query(self, query: str) -> list[float]:
        return self.embed([query])[0]

knowledge = Knowledge(
    sources=sources,
    embedder=CustomEmbedder()
)
```

---

## 12. 最佳实践

### 12.1 知识管理

| 场景 | 建议 |
|------|------|
| 大文档 | 使用 PDFSource，适当增大 chunk_size |
| 结构化数据 | 使用 JSON/CSV 源，指定 text_columns |
| 频繁更新 | 定期 reload() 或使用增量更新 |
| 大规模数据 | 考虑分布式存储如 Qdrant |

### 12.2 检索优化

- 调整 chunk_size 平衡上下文和精确度
- 使用相似度阈值过滤低相关结果
- 启用 re-ranking 提高结果质量

### 12.3 性能考虑

```python
# 使用缓存
knowledge = Knowledge(
    sources=sources,
    cache=True  # 启用结果缓存
)

# 预加载
knowledge.load()  # 预先加载，后续查询更快

# 批量处理
knowledge.add_source_batch(sources_list)
```
