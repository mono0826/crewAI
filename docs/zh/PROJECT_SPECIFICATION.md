# CrewAI 项目说明书

## 概述

CrewAI 是一个多智能体协作框架，旨在让多个 AI Agent 能够协同工作来完成复杂任务。本文档详细说明了 CrewAI 核心模块的实现机制，包括任务执行流程、记忆系统、工具调用、多Agent通信协议等。

---

## 1. 整体执行流程

### 1.1 Crew 执行入口

CrewAI 的核心执行入口是 `Crew.kickoff()` 方法（定义在 `crewai/crew.py` 中）。

```python
def kickoff(
    self,
    inputs: dict[str, Any] | None = None,
    input_files: dict[str, FileInput] | None = None,
    from_checkpoint: CheckpointConfig | None = None,
) -> CrewOutput | CrewStreamingOutput:
```

### 1.2 执行流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Crew.kickoff()                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   prepare_kickoff() - 输入准备                          │
│  - 执行 before_kickoff_callbacks 回调                                   │
│  - 处理输入文件和上下文                                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
         ┌──────────────────────────────────────────────┐
         │           Process Mode Selection             │
         └──────────────────────────────────────────────┘
                        │                    │
                        ▼                    ▼
         ┌──────────────────────┐  ┌──────────────────────┐
         │  Process.sequential  │  │ Process.hierarchical  │
         └──────────────────────┘  └──────────────────────┘
                        │                    │
                        ▼                    ▼
         ┌──────────────────────┐  ┌──────────────────────┐
         │ _run_sequential_     │  │ _run_hierarchical_   │
         │     process()        │  │     process()        │
         └──────────────────────┘  └──────────────────────┘
                        │                    │
                        └─────────┬──────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      _execute_tasks()                                   │
│  - 依次执行每个任务                                                     │
│  - 处理条件任务 (ConditionalTask)                                      │
│  - 支持同步/异步任务执行                                               │
│  - 管理任务依赖和上下文传递                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Task.execute_sync() / execute_async()                │
│  - 调用 Agent 执行任务                                                 │
│  - 处理任务结果                                                        │
│  - 执行任务回调 (task_callback)                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent.execute_task()                                 │
│  - 准备任务提示                                                        │
│  - 处理知识检索                                                        │
│  - 调用 AgentExecutor 执行                                            │
│  - 处理超时和错误                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CrewAgentExecutor.invoke()                           │
│  - 构建消息列表                                                        │
│  - 调用 LLM 生成响应                                                   │
│  - 处理工具调用                                                        │
│  - 多轮对话循环直到完成                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 两种执行模式

#### 顺序执行 (Sequential Process)

顺序执行模式下，任务按定义顺序依次执行。每个任务完成后，其输出会作为上下文传递给下一个任务。

```python
def _run_sequential_process(self) -> CrewOutput:
    """Executes tasks sequentially and returns the final output."""
    return self._execute_tasks(self.tasks)
```

#### 分层执行 (Hierarchical Process)

分层执行模式下，创建一个管理器 Agent (Manager Agent) 来协调任务分配。Manager Agent 负责决定任务的执行顺序和分配。

```python
def _run_hierarchical_process(self) -> CrewOutput:
    """Creates and assigns a manager agent to complete the tasks."""
    self._create_manager_agent()  # 创建管理器代理
    return self._execute_tasks(self.tasks)
```

---

## 2. Memory 长短期记忆实现

### 2.1 记忆系统架构

CrewAI 的记忆系统由以下核心组件构成：

| 组件 | 文件位置 | 功能 |
|------|----------|------|
| `Memory` | `memory/unified_memory.py` | 统一内存接口 |
| `RecallFlow` | `memory/recall_flow.py` | 智能记忆检索流程 |
| `MemoryScope` | `memory/memory_scope.py` | 记忆作用域管理 |
| Storage Backend | `memory/storage/` | 存储后端实现 |

### 2.2 记忆存储结构

记忆记录使用 `MemoryRecord` 数据结构存储：

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

### 2.3 记忆存储机制

CrewAI 支持多种存储后端：

1. **LanceDB** (默认): 高性能向量数据库
2. **Qdrant**: 另一个向量数据库选项
3. **自定义后端**: 通过 `StorageBackend` 接口实现

### 2.4 记忆检索流程 (RecallFlow)

记忆检索采用 **自适应深度检索** 机制：

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
                                    │
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

### 2.5 复合相关性分数

RecallFlow 使用复合分数对记忆进行排序：

```python
def compute_composite_score(record, semantic_score, config):
    # 1. 语义相似度分数 (semantic_weight=0.5)
    semantic = semantic_score * config.semantic_weight
    
    # 2. 时间衰减分数 (recency_weight=0.3)
    # 半衰期: recency_half_life_days (默认30天)
    recency = calculate_recency(record.created_at, config) * config.recency_weight
    
    # 3. 重要性分数 (importance_weight=0.2)
    importance = record.importance * config.importance_weight
    
    return semantic + recency + importance
```

### 2.6 记忆保存机制

记忆保存采用 **异步非阻塞** 方式：

```python
def remember_many(self, contents: list[str], ...):
    # 编码管道在后台线程运行
    # 方法立即返回，不阻塞调用者
    future = self._submit_save(self._encode_batch, [...])
    # MemorySaveStartedEvent 立即发出
    # MemorySaveCompletedEvent 在保存完成后发出
```

---

## 3. Tool 调用与失败处理机制

### 3.1 工具调用流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│              ToolUsage.use(calling, tool_string)                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  _select_tool(tool_name) - 工具选择                                      │
│  - 使用相似度匹配 (SequenceMatcher)                                    │
│  - 阈值: 0.85                                                          │
│  - 如果找不到: 抛出 ToolSelectionErrorEvent                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  缓存检查 (ToolsHandler.cache)                                         │
│  - 读取缓存: cache.read(tool_name, input)                             │
│  - 命中: 直接返回缓存结果                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  工具执行 (await tool.ainvoke())                                       │
│  - 参数验证: _validate_tool_input()                                    │
│  - 指纹配置: _build_fingerprint_config()                              │
│  - 缓存函数检查: cache_function(arguments, result)                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  结果处理                                                              │
│  - 格式化结果: _format_result()                                        │
│  - 更新工具使用计数                                                    │
│  - 发出 ToolUsageFinishedEvent                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 失败处理机制

#### 工具选择失败

```python
def _select_tool(self, tool_name: str) -> Any:
    # 使用相似度匹配找到最相似的工具
    for tool in order_tools:
        if sanitized_tool == sanitized_input or ratio > 0.85:
            return tool
    
    # 抛出详细错误
    error = f"Action '{tool_name}' don't exist..."
    crewai_event_bus.emit(self, ToolSelectionErrorEvent(...))
    raise Exception(error)
```

#### 工具执行失败

```python
except Exception as e:
    self.on_tool_error(tool=tool, tool_calling=calling, e=e)
    self._run_attempts += 1
    
    if self._run_attempts > self._max_parsing_attempts:
        # 超过最大重试次数，返回错误并继续
        result = ToolUsageError(f"{error_message}").message
    else:
        # 重试
        should_retry = True
```

**重试配置：**
- 默认最大解析尝试次数: `_max_parsing_attempts = 3`
- 更大模型 (GPT-4, O1 等): `_max_parsing_attempts = 2`

### 3.3 循环检测与防止

#### Agent 执行循环 (Step Executor)

```python
def _execute_text_parsed(
    self,
    messages: list[LLMMessage],
    tool_calls_made: list[str],
    max_step_iterations: int = 15,  # 默认最大15次迭代
    ...
):
    """Execute step with a multi-turn loop."""
    
    for _ in range(max_step_iterations):
        # 1. 调用 LLM
        answer = self.llm.call(messages, ...)
        
        # 2. 解析响应
        formatted = process_llm_response(answer_str, use_stop_words)
        
        # 3. 如果是 AgentFinish (完成信号)
        if isinstance(formatted, AgentFinish):
            return str(formatted.output)
        
        # 4. 如果是 AgentAction (工具调用)
        if isinstance(formatted, AgentAction):
            tool_calls_made.append(formatted.tool)
            tool_result = self._execute_text_tool_with_events(formatted)
            # 添加观察消息，继续循环
            messages.append({"role": "assistant", "content": answer_str})
            messages.append(self._build_observation_message(tool_result))
            continue
        
        # 5. 直接返回文本答案
        return answer_str
    
    # 超过最大迭代次数，返回最后的工具结果
    return last_tool_result
```

**关键参数：**
- `max_step_iterations`: 默认 15，限制单次 step 中的 LLM 调用次数
- `step_timeout`: 可选的步骤超时时间

---

## 4. 复杂任务规划机制

### 4.1 任务规划器 (CrewPlanner)

当启用 `planning=True` 时，CrewAI 会在执行前生成详细的任务计划。

```python
class CrewPlanner:
    def __init__(self, tasks: list[Task], planning_agent_llm: str | BaseLLM | None = None):
        self.tasks = tasks
        self.planning_agent_llm = planning_agent_llm or "gpt-4o-mini"
    
    def _handle_crew_planning(self) -> PlannerTaskPydanticOutput:
        # 1. 创建规划 Agent
        planning_agent = self._create_planning_agent()
        
        # 2. 创建任务摘要
        tasks_summary = self._create_tasks_summary()
        
        # 3. 创建规划任务
        planner_task = self._create_planner_task(...)
        
        # 4. 执行规划
        result = planner_task.execute_sync()
        
        return result.pydantic
```

### 4.2 规划流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Crew.planning = True                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CrewPlanner                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. 创建规划 Agent (role="Task Execution Planner")             │   │
│  │ 2. 生成任务摘要 (包含 agent role, goal, tools)                │   │
│  │ 3. 创建规划任务                                                │   │
│  │ 4. 执行规划任务 → 获取 PlannerTaskPydanticOutput              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    将计划添加到任务描述                                 │
│  每个任务获得详细的 step-by-step 执行计划                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 任务执行器 (Step Executor)

对于复杂任务，CrewAI 使用 `StepExecutor` 将任务分解为可执行的步骤：

```python
class StepExecutor:
    def execute(self, todo: TodoItem, context: StepExecutionContext,
                max_step_iterations: int = 15) -> StepResult:
        """执行单个 todo 项，使用多轮动作循环"""
        
        # 1. 构建消息
        messages = self._build_isolated_messages(todo, context)
        
        # 2. 执行多轮循环
        result_text = self._execute_native(
            messages,
            tool_calls_made,
            max_step_iterations=max_step_iterations,
            ...
        )
        
        return StepResult(success=True, result=result_text, ...)
```

---

## 5. 多 Agent 通信协议

### 5.1 通信机制概述

CrewAI 支持多种 Agent 间通信机制：

1. **内部委托** (Delegation): 同一 Crew 内 Agent 之间的任务委托
2. **A2A 协议**: 跨Crew/跨系统的 Agent 到 Agent 通信

### 5.2 内部委托机制

#### 委托工具

CrewAI 提供两种委托工具：

1. **DelegateWorkTool**: 将任务委托给其他 Agent
2. **AskQuestionTool**: 向其他 Agent 提问

```python
class DelegateWorkTool(BaseAgentTool):
    name: str = "Delegate work to coworker"
    
    def _execute(self, agent_name: str, task: str, context: str = None) -> str:
        # 1. 查找目标 Agent (大小写不敏感)
        agent = [a for a in self.agents 
                 if sanitize(a.role) == sanitize(agent_name)]
        
        # 2. 创建任务
        task_with_agent = Task(description=task, agent=selected_agent, ...)
        
        # 3. 执行任务
        return selected_agent.execute_task(task_with_agent, context)
```

#### 委托流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│          Agent A 调用 "Delegate work to coworker" 工具                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  工具执行: DelegateWorkTool._execute()                                  │
│  - 查找目标 Agent (通过 role 匹配)                                     │
│  - 创建新 Task (description, agent=target_agent)                       │
│  - 调用 selected_agent.execute_task(task)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Agent B 执行任务                                                       │
│  - 正常任务执行流程                                                     │
│  - 返回结果给 Agent A                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 A2A 协议 (Agent-to-Agent)

A2A 是 Google 主导的开放协议，用于跨系统 Agent 通信。

#### A2A 核心组件

| 组件 | 文件位置 | 功能 |
|------|----------|------|
| `A2AWrapper` | `a2a/wrapper.py` | Agent 包装器 |
| `DelegationContext` | `a2a/wrapper.py` | 委托上下文 |
| `execute_a2a_delegation` | `a2a/utils/delegation.py` | A2A 委托执行 |

#### A2A 委托执行流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│              execute_a2a_delegation(endpoint, task_description, ...)    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. 获取 Agent Card                                                    │
│     - fetch_agent_card(endpoint)                                       │
│     - 获取远程 Agent 的能力描述                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. 构建请求消息                                                       │
│     - Message(role="user", content=task_description)                  │
│     - 添加上下文、历史记录                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. 发送任务 (通过 A2A Client)                                         │
│     - a2a_client.send_message()                                        │
│     - 处理流式或非流式响应                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. 处理响应                                                           │
│     - 解析 TaskStateResult                                              │
│     - 提取结果或错误                                                   │
│     - 返回给调用者                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

#### A2A 特性

- **认证支持**: 多种认证方案 (API Key, Bearer Token, OAuth2)
- **流式响应**: 支持 Server-Sent Events (SSE)
- **任务状态跟踪**: 支持长时间运行任务的状态查询
- **对话历史**: 支持多轮对话上下文传递

---

## 6. 核心配置参数

### 6.1 Crew 配置

```python
class Crew(BaseModel):
    name: str | None                          # Crew 名称
    tasks: list[Task]                         # 任务列表
    agents: list[BaseAgent]                   # Agent 列表
    process: Process = Process.sequential    # 执行模式
    memory: bool | Memory | ... = False       # 是否启用记忆
    cache: bool = True                        # 是否启用缓存
    verbose: bool = False                     # 详细输出
    max_rpm: int | None                       # 每分钟最大请求数
    planning: bool | None                     # 是否启用规划
```

### 6.2 Memory 配置

```python
class Memory(BaseModel):
    llm: BaseLLM | str = "gpt-4o-mini"       # 分析用 LLM
    storage: StorageBackend | str = "lancedb" # 存储后端
    recency_weight: float = 0.3               # 时间权重
    semantic_weight: float = 0.5              # 语义权重
    importance_weight: float = 0.2            # 重要性权重
    recency_half_life_days: int = 30          # 时间半衰期
    confidence_threshold_high: float = 0.8    # 高置信度阈值
    confidence_threshold_low: float = 0.5     # 低置信度阈值
    exploration_budget: int = 1               # 探索轮数
```

### 6.3 Tool 配置

```python
class ToolUsage:
    _max_parsing_attempts: int = 3            # 最大重试次数
    _remember_format_after_usages: int = 3    # 格式记忆次数
```

---

## 7. 事件系统

CrewAI 使用事件总线 (`crewai_event_bus`) 进行组件间通信：

### 7.1 主要事件类型

| 事件类型 | 触发时机 |
|----------|----------|
| `MemorySaveStartedEvent` | 开始保存记忆 |
| `MemorySaveCompletedEvent` | 保存记忆完成 |
| `MemoryQueryStartedEvent` | 开始查询记忆 |
| `MemoryQueryCompletedEvent` | 查询记忆完成 |
| `ToolUsageStartedEvent` | 开始使用工具 |
| `ToolUsageFinishedEvent` | 工具使用完成 |
| `ToolSelectionErrorEvent` | 工具选择错误 |
| `ToolUsageErrorEvent` | 工具执行错误 |

---

## 8. 总结

CrewAI 是一个功能完善的多智能体协作框架，其核心设计包括：

1. **灵活的流程控制**: 支持顺序和分层两种执行模式
2. **智能记忆系统**: 结合向量检索和 LLM 推理的自适应记忆机制
3. **健壮的错误处理**: 多层次的重试和错误恢复机制
4. **循环防止**: 通过 `max_step_iterations` 限制执行轮数
5. **多协议支持**: 内部委托和 A2A 协议的双轨通信机制

这些设计使得 CrewAI 能够有效地协调多个 AI Agent 完成复杂任务，同时保证系统的稳定性和可靠性。
