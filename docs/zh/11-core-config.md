# 核心配置参数

## 1. Crew 配置

### 1.1 Crew 类定义

```python
class Crew(BaseModel):
    # 必需字段
    tasks: list[Task]                          # 任务列表
    agents: list[BaseAgent]                    # Agent 列表
    
    # 执行模式
    process: Process = Process.sequential     # 执行模式
    verbose: bool = False                      # 详细输出
    
    # 内存和缓存
    memory: bool | Memory | None = None       # 记忆配置
    cache: bool = True                         # 缓存开关
    
    # 速度和限制
    max_rpm: int | None = None                # 每分钟最大请求数
    max_iterations: int | None = None         # 最大迭代次数
    
    # 规划
    planning: bool | None = None              # 启用任务规划
    
    # 回调
    before_kickoff_callbacks: list[Callable] = []   # 执行前回调
    after_kickoff_callbacks: list[Callable] = []    # 执行后回调
    
    # 其他
    name: str | None = None                   # Crew 名称
    config: dict[str, Any] | None = None      # 自定义配置
```

### 1.2 Process 枚举

```python
class Process(str, Enum):
    sequential = "sequential"     # 顺序执行
    hierarchical = "hierarchical" # 分层执行
```

### 1.3 配置示例

```python
crew = Crew(
    name="Research Crew",
    agents=[researcher, writer, editor],
    tasks=[research_task, write_task, edit_task],
    process=Process.sequential,
    memory=True,
    cache=True,
    verbose=True,
    max_rpm=60,
    planning=True
)
```

---

## 2. Agent 配置

### 2.1 Agent 类定义

```python
class Agent(BaseModel):
    # 核心身份
    role: str                              # 角色名称
    goal: str                              # 目标描述
    backstory: str                        # 背景故事
    
    # 执行控制
    verbose: bool = False                  # 详细输出
    allow_delegation: bool = True          # 允许委托
    max_iterations: int = 15               # 最大迭代次数
    max_rpm: int | None = None             # 每分钟请求数
    
    # 工具配置
    tools: list[BaseTool] = []             # 可用工具
    allowed_tools: list[str] | None = None  # 允许的工具
    forbidden_tools: list[str] | None = None # 禁止的工具
    
    # 记忆配置
    memory: bool = False                   # 启用记忆
    memory_scope: str | None = None       # 记忆作用域
    
    # LLM 配置
    llm: BaseLLM | str | None = None      # 语言模型
    function_calling_llm: BaseLLM | None = None  # 函数调用 LLM
    
    # 响应格式
    response_format: type[BaseModel] | None = None  # 响应格式
    
    # 代理配置
    max_step_iterations: int = 15         # 单步最大迭代
    
    # 自定义提示词
    prompt: str | None = None             # 系统提示词
```

### 2.2 配置示例

```python
from langchain_openai import ChatOpenAI

agent = Agent(
    role="Research Analyst",
    goal="Find and analyze the best information sources",
    backstory="""
        You are a senior research analyst with 10+ years of experience.
        You excel at finding accurate information quickly.
    """,
    verbose=True,
    allow_delegation=False,
    max_iterations=20,
    max_rpm=30,
    tools=[search_tool, scrape_tool],
    llm=ChatOpenAI(model="gpt-4"),
    memory=True,
    memory_scope="research_team"
)
```

---

## 3. Task 配置

### 3.1 Task 类定义

```python
class Task(BaseModel):
    # 核心属性
    description: str                       # 任务描述
    expected_output: str                   # 预期输出
    agent: BaseAgent | None = None        # 执行 Agent
    
    # 输出配置
    output_json: type[BaseModel] | None = None  # JSON 输出
    output_pydantic: type[BaseModel] | None = None  # Pydantic 输出
    output_file: str | None = None        # 输出文件
    
    # 执行控制
    async_execution: bool = False          # 异步执行
    context: list[Task] | list[str] = []   # 依赖任务
    
    # 回调和钩子
    callback: Callable | None = None      # 完成回调
    
    # 工具限制
    allowed_tools: list[str] | None = None  # 允许的工具
    forbidden_tools: list[str] | None = None # 禁止的工具
    
    # 条件执行
    condition: str | None = None           # 执行条件
    
    # 模板
    template: str | None = None            # 任务模板
    template_variables: dict[str, Any] = {}  # 模板变量
    
    # 状态
    config: dict[str, Any] = {}            # 任务配置
```

### 3.2 配置示例

```python
task = Task(
    description="Research AI trends and provide insights",
    expected_output="""
        A comprehensive report with:
        - Executive summary
        - Key trends (3-5 bullet points)
        - Future predictions
        - Sources
    """,
    agent=researcher,
    output_pydantic=ResearchReport,
    output_file="./output/report.md",
    async_execution=False,
    context=[previous_task],
    callback=on_task_complete
)
```

---

## 4. Memory 配置

### 4.1 Memory 类定义

```python
class Memory(BaseModel):
    # LLM 配置
    llm: BaseLLM | str = "gpt-4o-mini"     # 分析用 LLM
    
    # 存储配置
    storage: StorageBackend | str = "lancedb"  # 存储后端
    
    # 分数权重
    recency_weight: float = 0.3            # 时间权重
    semantic_weight: float = 0.5           # 语义权重
    importance_weight: float = 0.2        # 重要性权重
    
    # 时间配置
    recency_half_life_days: int = 30      # 时间半衰期
    
    # 置信度阈值
    confidence_threshold_high: float = 0.8   # 高置信度
    confidence_threshold_low: float = 0.5    # 低置信度
    
    # 探索配置
    exploration_budget: int = 1           # 探索轮数
    
    # 其他
    include_private: bool = True          # 包含私有记忆
    default_scope: str = "crew/default"   # 默认作用域
```

### 4.2 完整配置示例

```python
memory = Memory(
    llm="gpt-4o-mini",
    storage="lancedb",
    recency_weight=0.3,
    semantic_weight=0.5,
    importance_weight=0.2,
    recency_half_life_days=30,
    confidence_threshold_high=0.8,
    confidence_threshold_low=0.5,
    exploration_budget=2,
    include_private=True,
    default_scope="my_project"
)
```

---

## 5. Tool 配置

### 5.1 Tool 基类

```python
class BaseTool(BaseModel):
    name: str                              # 工具名称
    description: str                       # 工具描述
    
    # 执行配置
    args_schema: type[BaseModel] | None = None  # 参数模式
    
    # 缓存配置
    cache_function: Callable | None = None  # 缓存函数
    
    # 超时配置
    timeout: int | None = None            # 超时时间(秒)
```

### 5.2 ToolUsage 配置

```python
class ToolUsage:
    _max_parsing_attempts: int = 3        # 最大重试次数
    _remember_format_after_usages: int = 3  # 格式记忆次数
```

### 5.3 工具配置示例

```python
from crewai.tools import SerperDevTool

search_tool = SerperDevTool(
    api_key="your-api-key",
    search_type="search",
    n_results=10,
    cache=True
)
```

---

## 6. Flow 配置

### 6.1 FlowConfig 类

```python
class FlowConfig(BaseModel):
    # 并行配置
    max_parallel_tasks: int = 5           # 最大并行任务数
    
    # 超时配置
    task_timeout: int = 300              # 单任务超时(秒)
    flow_timeout: int = 3600             # 流程超时(秒)
    
    # 重试配置
    max_retries: int = 3                 # 最大重试次数
    retry_delay: int = 2                 # 重试延迟(秒)
    
    # 缓存配置
    enable_cache: bool = True            # 启用缓存
    
    # 日志配置
    verbose: bool = False                # 详细输出
    log_level: str = "INFO"              # 日志级别
```

### 6.2 Flow 配置示例

```python
flow_config = FlowConfig(
    max_parallel_tasks=10,
    task_timeout=600,
    flow_timeout=7200,
    max_retries=3,
    retry_delay=5,
    enable_cache=True,
    verbose=True,
    log_level="DEBUG"
)
```

---

## 7. LLM 配置

### 7.1 OpenAI

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    max_tokens=2000,
    api_key="your-api-key"
)
```

### 7.2 Anthropic

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-3-opus-20240229",
    temperature=0.7,
    max_tokens=2000,
    anthropic_api_key="your-api-key"
)
```

### 7.3 本地 LLM (Ollama)

```python
from langchain_community.llms import Ollama

llm = Ollama(
    model="llama2",
    temperature=0.7
)
```

---

## 8. Embedder 配置

### 8.1 OpenAI Embedder

```python
from crewai.embeddings import OpenAIEmbedder

embedder = OpenAIEmbedder(
    model="text-embedding-3-small",
    api_key="your-api-key"
)
```

### 8.2 HuggingFace Embedder

```python
from langchain_community.embeddings import HuggingFaceEmbeddings

embedder = HuggingFaceEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2"
)
```

---

## 9. 存储配置

### 9.1 LanceDB

```python
from crewai.memory.storage.lancedb import LanceDbStorage

storage = LanceDbStorage(
    path="./memory_db",
    table_name="memories"
)
```

### 9.2 Qdrant

```python
from crewai.memory.storage.qdrant import QdrantStorage

storage = QdrantStorage(
    host="localhost",
    port=6333,
    collection="crewai_memory",
    api_key="your-api-key"  # 可选
)
```

### 9.3 Chroma

```python
from crewai.memory.storage.chroma import ChromaStorage

storage = ChromaStorage(
    persist_directory="./chroma_db",
    collection_name="crewai"
)
```

---

## 10. 全局配置

### 10.1 环境变量

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Default LLM
CREWAI_DEFAULT_LLM=openai/gpt-4
CREWAI_DEFAULT_EMBEDDER=openai/text-embedding-3-small

# Cache
CREWAI_CACHE_ENABLED=true

# Logging
CREWAI_LOG_LEVEL=INFO
```

### 10.2 配置文件

可以通过 YAML 或 JSON 配置文件设置默认参数：

```yaml
# crewai_config.yaml
llm:
  provider: openai
  model: gpt-4
  temperature: 0.7

embedder:
  provider: openai
  model: text-embedding-3-small

memory:
  storage: lancedb
  recency_weight: 0.3
  semantic_weight: 0.5
  importance_weight: 0.2

cache:
  enabled: true
  ttl: 3600
```

---

## 11. 配置优先级

配置优先级（从高到低）：

1. **代码中直接传入** - 最高优先级
2. **环境变量**
3. **配置文件**
4. **默认值** - 最低优先级

```python
# 最高优先级：代码传入
crew = Crew(
    agents=[agent],
    tasks=[task],
    max_rpm=30  # 覆盖配置文件的值
)
```
