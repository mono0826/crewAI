# Agent 智能体系统

## 1. Agent 概述

Agent 是 CrewAI 中具备特定角色、目标和工具的 AI 智能体。每个 Agent 有自己的角色定义、目标、背包景（Backstory）和可用的工具集。

---

## 2. Agent 完整属性

### 2.1 属性列表

```python
class Agent(BaseModel):
    # 核心身份
    role: str                              # 角色名称
    goal: str                              # 目标描述
    backstory: str                         # 背景故事
    
    # 执行配置
    verbose: bool = False                  # 详细输出
    allow_delegation: bool = True          # 允许委托
    max_iterations: int = 15               # 最大迭代次数
    max RPM: int | None = None            # 每分钟请求数
    verbose: bool = False                  # 详细日志
    
    # 工具配置
    tools: list[BaseTool] = []            # 可用工具
    function_calling_llm: BaseLLM | None = None  # 函数调用 LLM
    
    # 记忆配置
    memory: bool = False                   # 启用记忆
    memory_scope: str | None = None       # 记忆作用域
    
    # LLM 配置
    llm: BaseLLM | str | None = None     # 语言模型
    prompt: str | None = None             # 自定义提示词
    
    # 响应格式
    response_format: type[BaseModel] | None = None  # 响应格式
```

### 2.2 核心属性详解

#### role - 角色名称

定义 Agent 在团队中的角色。

```python
agent = Agent(
    role="Research Analyst",
    ...
)
```

#### goal - 目标描述

Agent 试图达成的目标。

```python
agent = Agent(
    goal="Find and summarize the latest AI research papers",
    ...
)
```

#### backstory - 背景故事

Agent 的背景故事，用于塑造其行为风格和专业能力。

```python
agent = Agent(
    backstory="""
    You are a senior research analyst with 10 years of experience
    in artificial intelligence. You have published numerous papers
    and have deep knowledge of ML/AI trends.
    """
)
```

---

## 3. Agent 执行方法

### 3.1 execute_task 方法

```python
def execute_task(
    self,
    task: Task,
    context: str | None = None,
    inputs: dict[str, Any] | None = None
) -> TaskOutput:
    """执行任务的主方法"""
    
    # 1. 准备任务提示
    task_prompt = self._prepare_task_prompt(task, context, inputs)
    
    # 2. 处理知识检索
    if self.knowledge:
        retrieved_context = self.knowledge.retrieve(task_prompt)
        task_prompt = f"{task_prompt}\n\nRelevant context: {retrieved_context}"
    
    # 3. 执行任务
    result = self._execute(task_prompt)
    
    # 4. 处理结果
    return self._process_result(result, task)
```

### 3.2 任务执行流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Agent.execute_task()                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. 准备任务提示 (prepare_task_prompt)                                 │
│     - 构建系统提示                                                     │
│     - 合并角色、目标、背景                                              │
│     - 添加任务描述                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. 知识检索 (knowledge.retrieve)                                       │
│     - 从知识库检索相关内容                                               │
│     - 合并到提示中                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. 执行多轮对话 (invoke)                                               │
│     - 调用 LLM                                                         │
│     - 处理工具调用                                                     │
│     - 循环直到完成                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. 处理输出 (process_result)                                          │
│     - 格式化结果                                                       │
│     - 验证输出格式                                                     │
│     - 返回 TaskOutput                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Agent 工具箱

### 4.1 工具分配

```python
from crewai.tools import SerperDevTool, BrowserbaseTool

researcher = Agent(
    role="Research Analyst",
    goal="Research topics thoroughly",
    tools=[SerperDevTool(), BrowserbaseTool()]  # 分配工具
)
```

### 4.2 动态工具

```python
agent = Agent(
    role="Data Analyst",
    tools=[
        # 文件操作
        ReadFileTool(),
        WriteFileTool(),
        # 数据处理
        PythonTool(),
        # 自定义工具
        MyCustomTool(description="Custom tool description")
    ]
)
```

### 4.3 工具执行权限

```python
# 限制工具使用
agent = Agent(
    role="Assistant",
    allowed_tools=["search", "read"],  # 只允许使用这些工具
    forbidden_tools=["delete", "write"]  # 禁止使用这些工具
)
```

---

## 5. Agent 委托机制

### 5.1 委托配置

```python
agent = Agent(
    role="Team Leader",
    allow_delegation=True  # 允许委托任务给其他 Agent
)
```

### 5.2 委托工具

CrewAI 自动为可委托的 Agent 添加两个工具：

1. **DelegateWorkTool**: 委托工作给其他 Agent
2. **AskQuestionTool**: 向其他 Agent 提问

```python
# Agent 可以使用这些工具与其他 Agent 协作
leader = Agent(
    role="Project Manager",
    goal="Complete the project successfully",
    allow_delegation=True,
    agents=[designer, developer, tester]
)
```

### 5.3 委托执行流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   Agent Delegation Flow                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. Agent A 调用委托工具                                                │
│     "Delegate work to coworker"                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. 查找目标 Agent                                                     │
│     - 通过 role 匹配                                                   │
│     - 大小写不敏感                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. 创建新 Task                                                        │
│     Task(description=task, agent=target_agent)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. 执行任务                                                           │
│     target_agent.execute_task(task)                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. 返回结果给 Agent A                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Agent 内存系统

### 6.1 内存配置

```python
agent = Agent(
    role="Researcher",
    memory=True,  # 启用内存
    memory_scope="research_agent"  # 作用域名称
)
```

### 6.2 记忆类型

| 类型 | 说明 | 配置 |
|------|------|------|
| **短期记忆** | 当前对话上下文 | 自动启用 |
| **长期记忆** | 跨会话记忆 | `memory=True` |
| **向量记忆** | 语义搜索 | `memory="vector"` |

### 6.3 记忆检索

```python
# 在 Agent 执行时自动检索相关记忆
agent = Agent(
    role="Assistant",
    memory=True,
    memory_config={
        "retrieval_query": "recent conversations about {topic}"
    }
)
```

---

## 7. 自定义 LLM

### 7.1 使用不同的 LLM

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# OpenAI
agent = Agent(
    role="Assistant",
    llm=ChatOpenAI(model="gpt-4")
)

# Anthropic
agent = Agent(
    role="Assistant",
    llm=ChatAnthropic(model="claude-3-opus")
)
```

### 7.2 本地 LLM

```python
from langchain_community.llms import Ollama

agent = Agent(
    role="Assistant",
    llm=Ollama(model="llama2")
)
```

### 7.3 函数调用 LLM

为工具调用使用专门的 LLM：

```python
agent = Agent(
    role="Assistant",
    llm=ChatOpenAI(model="gpt-4"),
    function_calling_llm=ChatOpenAI(model="gpt-3.5-turbo")  # 更轻量的模型
)
```

---

## 8. 响应格式

### 8.1 Pydantic 响应格式

```python
from pydantic import BaseModel

class ResponseFormat(BaseModel):
    summary: str
    confidence: float
    sources: list[str]

agent = Agent(
    role="Researcher",
    response_format=ResponseFormat
)

# Agent 输出会自动转换为 Pydantic 对象
result = agent.execute_task(task)
output: ResponseFormat = result.pydantic
```

### 8.2 JSON 响应格式

```python
agent = Agent(
    role="Data Analyst",
    response_format={"type": "json_object"}
)
```

---

## 9. Agent 池与选择

### 9.1 Agent 池

```python
from crewai import AgentPool

# 创建 Agent 池
pool = AgentPool(
    agents=[
        Agent(role="Researcher", ...),
        Agent(role="Writer", ...),
        Agent(role="Editor", ...),
    ]
)

# 动态选择最合适的 Agent
selected = pool.select_agent(
    task="Write about AI",
    criteria=["writing skill", "domain knowledge"]
)
```

### 9.2 Agent 选择策略

```python
# 基于任务描述自动选择
task = Task(
    description="Research latest AI trends",
    agents=[researcher, writer, editor]  # 自动选择最合适的
)
```

---

## 10. Agent 回调

### 10.1 执行回调

```python
def before_execution(agent, prompt):
    """执行前回调"""
    print(f"Agent {agent.role} starting execution")
    return prompt

def after_execution(agent, response):
    """执行后回调"""
    print(f"Agent {agent.role} completed")
    return response

agent = Agent(
    role="Assistant",
    before_agent_callback=before_execution,
    after_agent_callback=after_execution
)
```

### 10.2 错误回调

```python
def on_error(agent, error):
    """错误处理回调"""
    print(f"Error in {agent.role}: {error}")
    # 记录错误或执行恢复逻辑
    return {"recovered": True}

agent = Agent(
    role="Assistant",
    on_error_callback=on_error
)
```

---

## 11. Agent 示例

### 11.1 研究 Agent

```python
researcher = Agent(
    role="Senior Research Analyst",
    goal="Find and analyze the most relevant information on any given topic",
    backstory="""
    You are an experienced research analyst with a background in
    data science and machine learning. You excel at finding
    accurate information and synthesizing it into clear insights.
    """,
    tools=[
        SerperDevTool(),
        ScrapeWebsiteTool()
    ],
    verbose=True
)
```

### 11.2 编写 Agent

```python
writer = Agent(
    role="Content Writer",
    goal="Create engaging and accurate content based on research",
    backstory="""
    You are a professional content writer with expertise in
    technology and science topics. You write clear, engaging
    content that appeals to both technical and general audiences.
    """,
    verbose=True
)
```

### 11.3 编辑 Agent

```python
editor = Agent(
    role="Editor",
    goal="Ensure content is polished, accurate, and well-structured",
    backstory="""
    You are a meticulous editor with years of experience in
    proofreading and improving written content. You have a
    keen eye for detail and maintain high quality standards.
    """,
    verbose=True
)
```

---

## 12. 高级特性

### 12.1 最大迭代限制

```python
agent = Agent(
    role="Assistant",
    max_iterations=10,  # 限制最大迭代次数
    max_step_iterations=15  # 限制每步最大迭代
)
```

### 12.2 RPM 限制

```python
agent = Agent(
    role="Assistant",
    max_rpm=30  # 每分钟最多 30 次请求
)
```

### 12.3 自定义系统提示

```python
agent = Agent(
    role="Assistant",
    prompt="""
    You are a helpful AI assistant.
    Always provide step-by-step explanations.
    Use code blocks for any code you write.
    """
)
```
