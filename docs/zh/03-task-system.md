# Task 任务系统详解

## 1. Task 概述

Task 是 CrewAI 中分配给 Agent 的具体工作单元。每个 Task 包含描述、预期输出、执行 Agent 等属性。

---

## 2. Task 完整属性

### 2.1 属性列表

```python
class Task(BaseModel):
    # 核心属性
    description: str                           # 任务描述
    expected_output: str                       # 预期输出格式
    agent: BaseAgent | None = None            # 执行的 Agent
    
    # 执行控制
    config: dict[str, Any] = {}                # 任务配置
    callback: Callable | None = None           # 完成回调
    context: list[Task] | list[str] = []      # 依赖任务
    
    # 输出控制
    output_json: type[BaseModel] | None = None # JSON 输出格式
    output_pydantic: type[BaseModel] | None = None  # Pydantic 模型输出
    output_file: str | None = None            # 输出文件路径
    
    # 条件执行
    condition: str | None = None               # 执行条件
    conditional: bool = False                  # 是否为条件任务
    
    # 异步执行
    async_execution: bool = False              # 是否异步执行
    
```

### 2.2 核心属性详解

#### description - 任务描述

任务的自然语言描述，告诉 Agent 需要完成什么。

```python
task = Task(
    description="Research the latest developments in quantum computing and summarize the key findings",
)
```

**最佳实践：**
- 描述要具体、清晰
- 包含所需的输出格式
- 说明任务的上下文和目标

#### expected_output - 预期输出

描述任务完成后的预期输出格式，帮助 Agent 生成符合要求的答案。

```python
task = Task(
    description="Write a blog post about AI",
    expected_output="""
    A well-structured blog post with:
    - Introduction (2-3 paragraphs)
    - Main content (3-4 sections)
    - Conclusion (1-2 paragraphs)
    - Total length: 1000-1500 words
    """
)
```

#### agent - 执行 Agent

- `agent`: 单个执行 Agent

```python
# 单个 Agent
task = Task(
    description="Research AI trends",
    agent=researcher
)
```

---

## 3. 任务模板 (Task Template)

### 3.1 模板语法

Task 支持模板变量，可以使用 `{{variable}}` 语法：

```python
task = Task(
    description="""
    Research {{topic}} and provide insights on:
    - Current state
    - Key players
    - Future trends
    """,
    template_variables={
        "topic": "artificial intelligence"
    },
    agent=researcher
)
```

### 3.2 动态模板变量

模板变量可以在执行时动态传入：

```python
# 定义任务时使用变量
task = Task(
    description="Write a {{length}} article about {{topic}}",
    template_variables={"length": "short", "topic": "AI"},
    agent=writer
)

# 执行时覆盖变量
crew.kickoff(inputs={"length": "detailed", "topic": "quantum computing"})
```

---

## 4. 任务依赖 (Dependencies)

### 4.1 context 属性

通过 `context` 属性指定任务依赖：

```python
# 任务 A：无依赖
research_task = Task(
    description="Research AI trends",
    agent=researcher
)

# 任务 B：依赖任务 A
write_task = Task(
    description="Write about research findings",
    agent=writer,
    context=[research_task]  # 依赖 research_task
)

# 任务 C：依赖任务 A 和 B
edit_task = Task(
    description="Edit the article",
    agent=editor,
    context=[research_task, write_task]
)
```

### 4.2 依赖执行流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Task Execution with Context                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. 检查 context 依赖                                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. 执行依赖任务（如未执行）                                            │
│     - research_task.execute()                                          │
│     - write_task.execute()                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. 收集依赖任务输出                                                    │
│     - research_task.output                                             │
│     - write_task.output                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. 构建上下文输入                                                      │
│     context = f"Previous tasks output: {outputs}"                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. 执行当前任务                                                        │
│     task.execute(context=context)                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. 条件任务 (Conditional Task)

### 5.1 条件任务定义

```python
from crewai import Task
from crewai.tasks.conditional_task import ConditionalTask
# 基于条件的任务执行
conditional_task = ConditionalTask(
    description="Handle error case",
    condition="if error_occurred",  # 条件表达式
    agent=error_handler
)

# 正常任务
normal_task = Task(
    description="Process normally",
    agent=processor
)
```

### 5.2 条件表达式

```python
# 基于输入的条件
ConditionalTask(
    description="Handle VIP user",
    condition="inputs.user_type == 'vip'",
    agent=vip_handler
)

# 基于前序任务输出的条件
ConditionalTask(
    description="Send notification",
    condition="previous_task.success == false",
    agent=notifier
)
```

### 5.3 should_execute 方法

自定义条件逻辑：

```python
class CustomConditionalTask(ConditionalTask):
    def should_execute(self, previous_output: Any) -> bool:
        # 自定义条件判断逻辑
        if previous_output.error_count > 3:
            return True
        return False
```

---

## 6. 输出格式化

### 6.1 文本输出 (默认)

```python
task = Task(
    description="Summarize the article",
    agent=summarizer,
    expected_output="A concise summary in 3-5 sentences"
)
```

### 6.2 JSON 输出

```python
from pydantic import BaseModel

class ArticleSummary(BaseModel):
    title: str
    key_points: list[str]
    word_count: int
    sentiment: str

task = Task(
    description="Analyze the article",
    agent=analyzer,
    output_json=ArticleSummary
)

result = task.execute()
# result: ArticleSummary 对象
```

### 6.3 Pydantic 模型输出

```python
from pydantic import BaseModel, Field

class ResearchOutput(BaseModel):
    topic: str = Field(description="Research topic")
    findings: list[str] = Field(description="Key findings")
    sources: list[str] = Field(description="References")
    confidence: float = Field(description="Confidence score 0-1")

task = Task(
    description="Research the topic",
    agent=researcher,
    output_pydantic=ResearchOutput
)
```

### 6.4 文件输出

```python
task = Task(
    description="Generate report",
    agent=reporter,
    output_file="./output/report.md"  # 保存到文件
)
```

---

## 7. 任务回调

### 7.1 回调函数签名

```python
def task_callback(task: Task, result: Any, agent: Agent) -> Any:
    """
    任务完成后的回调函数
    
    Args:
        task: 完成任务对象
        result: 任务输出结果
        agent: 执行任务的 Agent
        
    Returns:
        处理后的结果
    """
    # 自定义处理逻辑
    print(f"Task '{task.description}' completed")
    return result
```

### 7.2 使用回调

```python
task = Task(
    description="Process data",
    agent=processor,
    callback=task_callback
)
```

### 7.3 常见回调用途

- **日志记录**: 记录任务执行情况
- **后处理**: 格式化或转换输出
- **状态更新**: 更新外部系统状态
- **错误处理**: 处理异常情况

---

## 8. 工具

```python
task = Task(
    description="Search and summarize",
    agent=researcher,
    tools=["search", "scrape", "summarize"]  # 只能使用这些工具
)
```

---

## 9. 异步任务

### 9.1 异步执行配置

```python
task = Task(
    description="Send notifications",
    agent=notifier,
    async_execution=True  # 异步执行
)
```

### 9.2 异步任务组

```python
# 多个独立任务可以并行执行
tasks = [
    Task(description="Task A", agent=agent1, async_execution=True),
    Task(description="Task B", agent=agent2, async_execution=True),
    Task(description="Task C", agent=agent3, async_execution=True),
]
```

---

## 10. 任务执行结果

### 10.1 TaskOutput 结构

```python
class TaskOutput(BaseModel):
    description: str                    # 任务描述
    name: str | None = None             # 任务名称
    expected_output: str                # 预期输出
    result: str                         # 实际输出
    pydantic: BaseModel | None = None   # Pydantic 输出
    json_dict: dict | None = None        # JSON 输出
    agent: BaseAgent | None = None      # 执行 Agent
```

### 10.2 访问结果

```python
crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()

# 访问各个任务输出
for task_output in result.tasks_output:
    print(f"Task: {task_output.description}")
    print(f"Result: {task_output.result}")
```

---

## 11. 任务模板示例

### 11.1 研究任务模板

```python
research_template = Task(
    description="""
    Research {{topic}} following these steps:
    
    1. Search for recent information on {{topic}}
    2. Identify key trends and developments
    3. Find authoritative sources
    4. Compile findings into a report
    """,
    expected_output="""
    A comprehensive research report including:
    - Executive summary
    - Key findings (bullet points)
    - Sources and references
    - Future outlook
    """,
    agent=researcher
)
```

### 11.2 内容创作模板

```python
content_template = Task(
    description="""
    Create {{content_type}} about {{subject}}.
    
    Target audience: {{audience}}
    Tone: {{tone}}
    Length: {{length}}
    """,
    expected_output="Well-structured content matching all requirements",
    agent=writer
)
```
