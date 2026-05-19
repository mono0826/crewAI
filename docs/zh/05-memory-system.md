# Memory 长短期记忆系统

## 1. 记忆系统概述

CrewAI 的记忆系统是其核心特性之一，它允许 Agent 记住之前的交互、知识和上下文，从而提供更连贯和个性化的响应。

---

## 2. 记忆系统架构

### 2.1 核心组件

| 组件 | 文件位置 | 功能 |
|------|----------|------|
| `Memory` | `memory/unified_memory.py` | 统一内存接口 |
| `RecallFlow` | `memory/recall_flow.py` | 智能记忆检索流程 |
| `MemoryScope` | `memory/memory_scope.py` | 记忆作用域管理 |
| Storage Backend | `memory/storage/` | 存储后端实现 |

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Memory System                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Memory Interface                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │   │
│  │  │   .remember()   │  │  .recall()    │  │    .search()         │ │   │
│  │  │  (保存记忆)    │  │  (检索记忆)   │  │   (向量搜索)         │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│         ┌──────────────────────────┼──────────────────────────┐        │
│         │                          │                          │        │
│         ▼                          ▼                          ▼        │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐   │
│  │ Short-term  │          │   Recall    │          │   Vector    │   │
│  │  (Context)  │          │    Flow     │          │   Storage   │   │
│  └─────────────┘          └─────────────┘          └─────────────┘   │
│         │                          │                          │        │
│         └──────────────────────────┼──────────────────────────┘        │
│                                    │                                    │
│                                    ▼                                    │
│                    ┌─────────────────────────┐                         │
│                    │   Storage Backend       │                         │
│                    │  (LanceDB/Qdrant/etc.)  │                         │
│                    └─────────────────────────┘                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 记忆存储结构

### 3.1 MemoryRecord 数据结构

```python
class MemoryRecord(BaseModel):
    id: str                           # 唯一标识符
    content: str                     # 记忆内容
    scope: str                       # 作用域路径
    categories: list[str]            # 分类标签
    importance: float                # 重要性评分 (0-1)
    created_at: datetime             # 创建时间
    last_accessed_at: datetime       # 最后访问时间
    embedding: list[float]           # 向量嵌入
    metadata: dict[str, Any]         # 元数据
    private: bool                    # 私有标记
    source: str                      # 来源标识
```

### 3.2 记忆分类

| 分类 | 说明 | 优先级 |
|------|------|--------|
| **Conversation** | 对话记录 | 高 |
| **Knowledge** | 知识条目 | 高 |
| **Task** | 任务结果 | 中 |
| **User** | 用户信息 | 中 |
| **System** | 系统状态 | 低 |

---

## 4. 记忆存储机制

### 4.1 支持的存储后端

| 存储后端 | 说明 | 适用场景 |
|----------|------|----------|
| **LanceDB** | 默认高性能向量数据库 | 大规模向量检索 |
| **Qdrant** | 高性能向量数据库 | 需要远程部署 |
| **Chroma** | 轻量级向量存储 | 本地开发 |
| **自定义** | 通过 StorageBackend 接口 | 特殊需求 |

### 4.2 存储后端配置

```python
from crewai.memory.storage.lancedb import LanceDbStorage

# 使用 LanceDB
crew = Crew(
    agents=[agent],
    tasks=[task],
    memory=True,
    memory_storage=LanceDbStorage(
        path="./memory_db"
    )
)

# 使用 Qdrant
from crewai.memory.storage.qdrant import QdrantStorage

crew = Crew(
    agents=[agent],
    tasks=[task],
    memory=True,
    memory_storage=QdrantStorage(
        host="localhost",
        port=6333
    )
)
```

---

## 5. 记忆检索流程 (RecallFlow)

### 5.1 自适应深度检索

RecallFlow 使用自适应深度检索机制，根据查询复杂度动态调整检索深度。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         recall(query, depth="deep")                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              analyze_query_step() - LLM 分析查询                        │
│  - 短查询 (<200字符): 直接使用原始查询                                  │
│  - 长查询: LLM 提取关键词、时间过滤、建议作用域                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              filter_and_chunk() - 选择候选作用域                        │
│  - 基于 LLM 建议的作用域                                               │
│  - 或从存储中列出可用作用域                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              search_chunks() - 并行向量搜索                             │
│  - 在多个 (embedding, scope) 组合上并行搜索                            │
│  - 应用时间过滤和隐私过滤                                              │
│  - 计算复合相关性分数                                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              decide_depth() - 置信度路由                                 │
│  - 高置信度 (>=0.8): 直接返回结果                                       │
│  - 低置信度 (<0.5): 触发深度探索                                       │
│  - 复杂查询且置信度<0.7: 迭代深化                                      │
└─────────────────────────────────────────────────────────────────────────┘
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
          ┌──────────────────┐           ┌──────────────────┐
          │  return results  │           │  explore_deeper │
          └──────────────────┘           └──────────────────┘
                                                    │
                                                    ▼
                                        ┌─────────────────────────┐
                                        │  LLM 驱动的迭代探索     │
                                        │  (exploration_budget)   │
                                        └─────────────────────────┘
```

### 5.2 检索步骤详解

#### 步骤 1: 查询分析 (analyze_query_step)
> 涉及到对query复杂度的分析
> 当query文本长度小于250时，complexity="simple"
> 大于250时，使用LLM分析，返回复杂度，当LLM分析失败，采用兜底策略complexity="simple"

```python
def analyze_query_step(self, query: str) -> QueryAnalysis:
    """分析查询，提取关键信息"""
    
    if len(query) < 250:
        # 短查询直接使用
        return QueryAnalysis(
            keywords=[],
            suggested_scopes=[],
            complexity="simple", # 复杂度
            recall_queries=[self.state.query],
        )
    else:
        # 长查询使用 LLM 分析
        return analyze_query(query)
```

#### 步骤 2: 作用域过滤 (filter_and_chunk)

```python
def filter_and_chunk(self, analysis: QueryAnalysis) -> list[ScopeChunk]:
    """选择候选作用域"""
    
    if analysis.suggested_scopes:
        # 使用 LLM 建议的作用域
        scopes = analysis.suggested_scopes
    else:
        # 列出所有可用作用域
        scopes = self.storage.list_scopes()
    
    # 分组成作用域块
    return chunk_by_scope(scopes)
```

#### 步骤 3: 并行搜索 (search_chunks)

```python
def search_chunks(self, query: str, chunks: list[ScopeChunk]) -> list[MemoryRecord]:
    """并行向量搜索"""
    
    # 并行搜索多个作用域
    results = parallel_search(
        query=query,
        embedding_model=self.embedding_model,
        chunks=chunks,
        time_filter=analysis.time_filter,
        privacy_filter=True
    )
    
    # 计算复合相关性分数
    scored_results = [
        compute_composite_score(record, semantic_score, config)
        for record, semantic_score in results
    ]
    
    return sorted(scored_results, key=lambda x: x.score, reverse=True)
```

#### 步骤 4: 深度决策 (decide_depth)

```python
def decide_depth(self, confidence: float, query_complexity: str) -> str:
    """根据置信度决定检索深度"""
    
    if complexity == "complex" 且 confidence < 0.7 且 exploration_budget > 0:
        return "explore_deeper" # 迭代
    if confidence >= 0.8:
        return "synthesize"     
    if exploration_budget > 0 且 confidence < 0.5:
        return "explore_deeper"  
    
    return "synthesize"
```

---

## 6. 复合相关性分数

RecallFlow 使用复合分数对记忆进行排序，综合考虑语义相似度、时间衰减和重要性。

### 6.1 计算公式

```python
def compute_composite_score(record, semantic_score, config):
    # 1. 语义相似度分数 (semantic_weight=0.5)
    semantic = semantic_score * config.semantic_weight
    
    # 2. 时间衰减分数 (recency_weight=0.3)
    age_seconds = (datetime.utcnow() - record.created_at).total_seconds()
    age_days = max(age_seconds / 86400.0, 0.0)
    recency = 0.5 ** (age_days / config.recency_half_life_days)
    
    # 3. 重要性分数 (importance_weight=0.2)
    importance = record.importance * config.importance_weight
    
    return semantic + recency + importance
```

### 6.2 权重配置

```python
memory = Memory(
    # 分数权重配置
    semantic_weight=0.5,       # 语义相似度权重
    recency_weight=0.3,       # 时间衰减权重
    importance_weight=0.2,     # 重要性权重
    
    # 时间半衰期
    recency_half_life_days=30  # 30天后重要性减半
)
```

### 6.3 时间衰减曲线

```
重要性
    │
1.0 ┤  ●●●●●●●●●●
    │  ●●●●●●●●●
0.5 ┤  ●●●●●●●●
    │  ●●●●●●●
0.0 ┤  ●●●●●●
    └────────────── 时间 ──────────────▶
          0    30    60    90   120 天
```

---

## 7. 记忆保存机制

### 7.1 异步保存

记忆保存采用 **异步非阻塞** 方式，不影响主流程执行：

```python
def remember_many(self, contents: list[str], ...):
    # 编码管道在后台线程运行
    # 方法立即返回，不阻塞调用者
    future = self._submit_save(self._encode_batch, [...])
    
    # MemorySaveStartedEvent 立即发出
    # MemorySaveCompletedEvent 在保存完成后发出
```

### 7.2 批量保存

```python
# 批量保存记忆
memory.remember_many(
    contents=[
        "User asked about AI trends",
        "Discussed GPT-4 capabilities",
        "User prefers detailed explanations"
    ],
    scope="conversation/user_123",
    categories=["conversation", "preference"]
)
```

### 7.3 记忆重要性

```python
# 保存时指定重要性
memory.remember(
    content="Critical system error occurred",
    scope="system/errors",
    importance=0.9  # 高重要性
)

memory.remember(
    content="User said hello",
    scope="conversation/user_123",
    importance=0.1  # 低重要性
)
```

---

## 8. 记忆作用域

### 8.1 作用域概念

作用域（Scope）用于组织和管理记忆，支持层级结构：

```
root/
├── user_123/
│   ├── preferences/
│   ├── conversation/
│   └── knowledge/
├── agent_456/
│   ├── tasks/
│   └── context/
└── shared/
    └── team_knowledge/
```

### 8.2 作用域配置

```python
# 配置作用域
crew = Crew(
    agents=[agent],
    tasks=[task],
    memory=True,
    memory_scope="my_project"  # 项目作用域
)
```

### 8.3 Agent 作用域

```python
agent = Agent(
    role="Assistant",
    memory=True,
    memory_scope=f"agent/{agent.role}"  # Agent 专属作用域
)
```

---

## 9. 记忆配置详解

### 9.1 完整配置

```python
from crewai.memory import Memory, MemoryConfig

memory = Memory(
    # LLM 配置
    llm="gpt-4o-mini",
    
    # 存储后端
    storage="lancedb",  # 或 "qdrant", "chroma"
    
    # 分数权重
    recency_weight=0.3,
    semantic_weight=0.5,
    importance_weight=0.2,
    
    # 时间半衰期
    recency_half_life_days=30,
    
    # 置信度阈值
    confidence_threshold_high=0.8,
    confidence_threshold_low=0.5,
    
    # 探索预算
    exploration_budget=1,
    
    # 私有记忆
    include_private=True,
    
    # 默认作用域
    default_scope="crew/default"
)
```

### 9.2 配置项说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `llm` | "gpt-4o-mini" | 分析用 LLM |
| `storage` | "lancedb" | 存储后端 |
| `recency_weight` | 0.3 | 时间权重 |
| `semantic_weight` | 0.5 | 语义权重 |
| `importance_weight` | 0.2 | 重要性权重 |
| `recency_half_life_days` | 30 | 时间半衰期(天) |
| `confidence_threshold_high` | 0.8 | 高置信度阈值 |
| `confidence_threshold_low` | 0.5 | 低置信度阈值 |
| `exploration_budget` | 1 | 探索轮数 |

---

## 10. 记忆使用示例

### 10.1 启用 Crew 记忆

```python
crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[research_task, write_task, edit_task],
    memory=True,  # 启用记忆
    process=Process.sequential
)
```

### 10.2 手动保存记忆

```python
# Agent 执行后保存重要信息
result = agent.execute_task(task)

# 手动保存关键信息
crew.memory.remember(
    content=f"Task {task.description} completed with result: {result.result}",
    scope=f"crew/{crew.name}/tasks",
    importance=0.7
)
```

### 10.3 检索记忆

```python
# 在 Agent 执行时检索相关记忆
agent = Agent(
    role="Assistant",
    memory=True
)

# 自动检索：在执行任务时自动检索相关记忆
result = agent.execute_task(task)
# 检索结果会自动添加到任务提示中
```

---

## 11. 最佳实践

### 11.1 记忆策略

| 场景 | 建议 |
|------|------|
| 对话应用 | 启用记忆，高权重 |
| 分析任务 | 选择性记忆 |
| 一次性任务 | 禁用记忆 |

### 11.2 隐私考虑

```python
# 标记为私有记忆
memory.remember(
    content="User password reset requested",
    scope="user/private",
    private=True  # 不被其他 Agent 检索
)
```

### 11.3 记忆清理

```python
# 删除特定记忆
memory.forget(memory_id="memory_123")

# 清理作用域
memory.clear_scope("crew/project_abc")

# 清理过期记忆
memory.cleanup(older_than_days=90)
```
