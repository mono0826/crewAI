# Crew 执行流程与模式

## 1. Crew 执行入口

CrewAI 的核心执行入口是 `Crew.kickoff()` 方法。

### 1.1 kickoff 方法签名

```python
def kickoff(
    self,
    inputs: dict[str, Any] | None = None,
    input_files: dict[str, FileInput] | None = None,
    from_checkpoint: CheckpointConfig | None = None,
) -> CrewOutput | CrewStreamingOutput:
```

**参数说明：**
- `inputs`: 传递给任务的输入参数字典
- `input_files`: 要处理的文件字典
- `from_checkpoint`: 从检查点恢复执行的配置

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

---

## 2. 两种执行模式

### 2.1 顺序执行 (Sequential Process)

顺序执行模式下，任务按定义顺序依次执行。每个任务完成后，其输出会作为上下文传递给下一个任务。

```python
def _run_sequential_process(self) -> CrewOutput:
    """Executes tasks sequentially and returns the final output."""
    return self._execute_tasks(self.tasks)
```

**特点：**
- 任务按定义顺序执行
- 前一个任务的输出作为后续任务的输入
- 适用于线性工作流
- 易于理解和调试

**示例场景：**
1. 研究 → 写作 → 编辑
2. 数据收集 → 数据处理 → 数据分析

### 2.2 分层执行 (Hierarchical Process)

分层执行模式下，创建一个管理器 Agent (Manager Agent) 来协调任务分配。Manager Agent 负责决定任务的执行顺序和分配。

```python
def _run_hierarchical_process(self) -> CrewOutput:
    """Creates and assigns a manager agent to complete the tasks."""
    self._create_manager_agent()  # 创建管理器代理
    return self._execute_tasks(self.tasks)
```

**特点：**
- 自动创建 Manager Agent
- Manager 决定任务分配
- 适用于复杂协作场景
- 支持动态任务分配

**Manager Agent 配置：**
```python
crew = Crew(
    agents=[agent1, agent2, agent3],
    tasks=[task1, task2, task3],
    process=Process.hierarchical,
    manager_agent=custom_manager  # 可选：自定义管理器
)
```

---

## 3. 任务执行机制

### 3.1 _execute_tasks 方法

```python
def _execute_tasks(self, tasks: list[Task]) -> CrewOutput:
    """执行任务列表"""
    results = []
    
    for task in tasks:
        # 检查任务依赖
        if task.context:
            # 将依赖任务的输出作为上下文
            context = self._get_task_outputs(task.context)
        
        # 执行任务
        result = task.execute_sync(
            context=context,
            inputs=self._inputs
        )
        
        results.append(result)
        
        # 检查是否为条件任务
        if isinstance(task, ConditionalTask):
            if not task.should_execute(result):
                continue
        
        # 更新共享上下文
        self._update_shared_context(task, result)
    
    return self._format_output(results)
```

### 3.2 任务依赖处理

```python
def _get_task_outputs(self, task_ids: list[str]) -> str:
    """获取依赖任务的输出"""
    outputs = []
    for task_id in task_ids:
        if task_id in self._task_outputs:
            outputs.append(self._task_outputs[task_id])
    return "\n\n".join(outputs)
```

### 3.3 上下文传递

任务之间通过上下文（Context）传递信息：

```python
task = Task(
    description="Analyze the research data",
    agent=agent,
    context=["research_task"]  # 依赖的任务ID
)
```

---

## 4. 异步执行

### 4.1 异步任务执行

CrewAI 支持异步任务执行以提高效率：

```python
async def execute_async(self) -> CrewOutput:
    """异步执行所有任务"""
    
    # 并行执行独立任务
    async_tasks = []
    for task in self.tasks:
        if not task.context:  # 无依赖的任务可以并行
            async_tasks.append(task.execute_async())
    
    # 等待所有任务完成
    results = await asyncio.gather(*async_tasks)
    
    return self._format_output(results)
```

### 4.2 异步配置

```python
crew = Crew(
    agents=agents,
    tasks=tasks,
    process=Process.sequential,
    async_execution=True  # 启用异步执行
)
```

---

## 5. 回调机制

### 5.1 执行回调

CrewAI 提供多种回调钩子：

```python
crew = Crew(
    agents=agents,
    tasks=tasks,
    # Kickoff 前回调
    before_kickoff_callbacks=[before_kickoff],
    # Kickoff 后回调
    after_kickoff_callbacks=[after_kickoff],
)

def before_kickoff(crew, output):
    """执行前回调"""
    print(f"Starting crew: {crew.name}")
    return output

def after_kickoff(crew, output):
    """执行后回调"""
    print(f"Completed crew: {crew.name}")
    return output
```

### 5.2 任务回调

```python
task = Task(
    description="Some task",
    agent=agent,
    # 任务完成回调
    callback=task_completed,
)

def task_completed(task, output, agent):
    """任务完成后调用"""
    print(f"Task completed: {task.description}")
    return output
```

---

## 6. 异常处理

### 6.1 重试机制

```python
crew = Crew(
    agents=agents,
    tasks=tasks,
    max_retries=3,  # 最大重试次数
    retry_delay=2,  # 重试延迟（秒）
)
```

### 6.2 错误处理流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Error Handling Flow                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
         ┌──────────────────────────────────────────────┐
         │            Exception Occurs                  │
         └──────────────────────────────────────────────┘
                        │                    │
                        ▼                    ▼
         ┌──────────────────────┐  ┌──────────────────────┐
         │   Retry Available    │  │   No Retry Left     │
         └──────────────────────┘  └──────────────────────┘
                        │                    │
                        ▼                    ▼
         ┌──────────────────────┐  ┌──────────────────────┐
         │  Wait & Retry        │  │  Log Error          │
         │  (max_retries)       │  │  Continue/Fail      │
         └──────────────────────┘  └──────────────────────┘
```

### 6.3 超时处理

```python
crew = Crew(
    agents=agents,
    tasks=tasks,
    timeout=300,  # 5分钟超时
)
```

---

## 7. 流式输出

### 7.1 流式配置

```python
from crewai import Crew, Streaming

crew = Crew(
    agents=agents,
    tasks=tasks,
    streaming=True  # 启用流式输出
)

# 迭代流式输出
for chunk in crew.kickoff():
    print(chunk, end="", flush=True)
```

### 7.2 流式回调

```python
def on_token(token):
    """每个 token 生成时调用"""
    print(token, end="", flush=True)

crew = Crew(
    agents=agents,
    tasks=tasks,
    stream_callback=on_token,
)
```

---

## 8. 检查点与恢复

### 8.1 检查点配置

```python
from crewai import CheckpointConfig

crew = Crew(
    agents=agents,
    tasks=tasks,
    checkpoint=CheckpointConfig(
        enabled=True,
        storage_path="./checkpoints",
        interval=10,  # 每10个任务保存一次
    )
)
```

### 8.2 从检查点恢复

```python
checkpoint = CheckpointConfig.load("./checkpoints/crew_state.json")
result = crew.kickoff(from_checkpoint=checkpoint)
```

---

## 9. 执行监控

### 9.1 日志配置

```python
import logging

logging.basicConfig(level=logging.DEBUG)

crew = Crew(
    agents=agents,
    tasks=tasks,
    verbose=True  # 详细输出
)
```

### 9.2 进度追踪

```python
from crewai import ProgressTracker

tracker = ProgressTracker()

@tracker.on("task_start")
def on_task_start(task):
    print(f"Starting: {task.description}")

@tracker.on("task_complete")
def on_task_complete(task, result):
    print(f"Completed: {task.description}")
