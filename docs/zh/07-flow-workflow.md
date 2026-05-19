# Flow 工作流机制

## 1. Flow 概述

Flow 是 CrewAI 的工作流编排系统，支持复杂的条件分支、状态管理和并行执行。它允许创建更复杂的业务流程，而不仅仅是简单的顺序执行。

---

## 2. Flow 核心概念

### 2.1 Flow 类定义

```python
class Flow:
    """工作流基类"""
    
    def __init__(self):
        self._state = {}  # 工作流状态
        self._tasks = []  # 任务列表
        self._conditions = {}  # 条件映射
```

### 2.2 核心方法

| 方法 | 说明 |
|------|------|
| `add_task()` | 添加任务到工作流 |
| `add_condition()` | 添加条件分支 |
| `set_state()` | 设置状态 |
| `get_state()` | 获取状态 |
| `kickoff()` | 启动工作流 |

---

## 3. Flow 执行流程

### 3.1 流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Flow.kickoff()                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    initialize() - 初始化                                 │
│  - 初始化状态                                                          │
│  - 准备任务队列                                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      任务执行循环                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  1. 从队列获取下一个任务                                          │   │
│  │  2. 检查条件是否满足                                              │   │
│  │  3. 执行任务                                                      │   │
│  │  4. 更新状态                                                      │   │
│  │  5. 检查是否有新任务加入                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    collect_outputs() - 收集输出                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 状态管理

```python
class Flow:
    def set_state(self, key: str, value: Any):
        """设置状态"""
        self._state[key] = value
        
    def get_state(self, key: str, default: Any = None) -> Any:
        """获取状态"""
        return self._state.get(key, default)
        
    def update_state(self, updates: dict):
        """批量更新状态"""
        self._state.update(updates)
```

---

## 4. 条件分支 (Condition)

### 4.1 条件基础

```python
class Condition:
    """条件定义"""
    
    def __init__(
        self,
        name: str,
        condition_func: Callable[[dict], bool],
        true_task: str,
        false_task: str | None = None
    ):
        self.name = name
        self.condition_func = condition_func
        self.true_task = true_task
        self.false_task = false_task
```

### 4.2 条件函数

```python
def check_data_ready(state: dict) -> bool:
    """检查数据是否就绪"""
    return state.get("data_loaded", False)

def check_user_auth(state: dict) -> bool:
    """检查用户是否已认证"""
    return state.get("user", {}).get("authenticated", False)
```

### 4.3 添加条件

```python
flow.add_condition(
    name="data_ready",
    condition_func=check_data_ready,
    true_task="process_data",
    false_task="load_data"
)
```

---

## 5. 状态管理 (State)

### 5.1 状态定义

```python
from typing import TypedDict

class WorkflowState(TypedDict, total=False):
    """工作流状态类型"""
    data: dict
    user: dict
    results: list
    error: str | None
    completed: bool
```

### 5.2 状态初始化

```python
class MyFlow(Flow):
    def initialize(self):
        """初始化状态"""
        self.set_state("data", {})
        self.set_state("user", {})
        self.set_state("results", [])
        self.set_state("completed", False)
```

### 5.3 状态传递

```python
# 任务输出自动更新状态
task = Task(
    description="Process data",
    agent=agent,
    output_state_key="processed_data"  # 输出自动写入状态
)

# 任务输入从状态获取
task = Task(
    description="Analyze data",
    agent=agent,
    input_from_state="processed_data"  # 从状态读取输入
)
```

---

## 6. 完整 Flow 示例

### 6.1 简单流程

```python
from crewai.flow import Flow, listen, start

class SimpleFlow(Flow):
    @start()
    def generate_topic(self):
        """生成主题"""
        topic = "Artificial Intelligence in Healthcare"
        self.set_state("topic", topic)
        return topic
    
    @listen("generate_topic")
    def write_article(self, topic):
        """写文章"""
        task = Task(
            description=f"Write an article about {topic}",
            agent=writer
        )
        result = task.execute()
        self.set_state("article", result.result)
        return result
    
    @listen("write_article")
    def save_article(self, article):
        """保存文章"""
        # 保存逻辑
        return "Article saved successfully"

# 执行流程
flow = SimpleFlow()
result = flow.kickoff()
```

### 6.2 条件分支流程

```python
class ConditionalFlow(Flow):
    @start()
    def check_user(self):
        """检查用户状态"""
        user_authenticated = True  # 模拟
        self.set_state("user_authenticated", user_authenticated)
        return user_authenticated
    
    @listen("check_user")
    def route_user(self, authenticated: bool):
        """根据认证状态路由"""
        if authenticated:
            return "dashboard"
        else:
            return "login"
    
    @listen("route_user")
    def show_dashboard(self):
        """显示仪表板"""
        return "Welcome to Dashboard"
    
    @listen("route_user")
    def show_login(self):
        """显示登录页"""
        return "Please Login"

flow = ConditionalFlow()
result = flow.kickoff()
```

### 6.3 并行执行流程

```python
class ParallelFlow(Flow):
    @start()
    def start_tasks(self):
        """启动并行任务"""
        self.set_state("tasks", ["task1", "task2", "task3"])
        return self.get_state("tasks")
    
    @listen("start_tasks", generate_tasks=True)
    def process_parallel(self, tasks: list):
        """并行处理多个任务"""
        results = []
        for task in tasks:
            result = self._process_single(task)
            results.append(result)
        return results
    
    @listen("process_parallel")
    def aggregate_results(self, results: list):
        """聚合结果"""
        return {"total": len(results), "results": results}

flow = ParallelFlow()
result = flow.kickoff()
```

---

## 7. Flow 装饰器

### 7.1 @start 装饰器

标记流程的起始任务：

```python
@start()
def initialize():
    """流程入口点"""
    pass
```

### 7.2 @listen 装饰器

监听任务完成事件：

```python
@listen("task_name")
def next_task(previous_output):
    """监听任务完成"""
    pass
```

### 7.3 @router 装饰器

根据条件路由到不同任务：

```python
@listen("check_status")
@router
def route_task(state: dict):
    """根据状态路由"""
    if state.get("status") == "ready":
        return "ready_task"
    else:
        return "pending_task"
```

---

## 8. Flow 状态持久化

### 8.1 保存状态

```python
flow = MyFlow()

# 执行流程
result = flow.kickoff()

# 获取最终状态
final_state = flow.get_state()

# 保存到文件
import json
with open("flow_state.json", "w") as f:
    json.dump(final_state, f)
```

### 8.2 从状态恢复

```python
# 从文件加载状态
with open("flow_state.json", "r") as f:
    saved_state = json.load(f)

# 创建流程并设置状态
flow = MyFlow()
flow.set_state(**saved_state)

# 继续执行
result = flow.kickoff()
```

---

## 9. Flow 错误处理

### 9.1 错误回调

```python
class RobustFlow(Flow):
    def handle_error(self, task_name: str, error: Exception):
        """处理任务错误"""
        self.set_state("error", str(error))
        self.set_state("error_task", task_name)
        
        # 可以选择重试或继续
        return "continue"  # 或 "retry" / "abort"
    
    @listen("main_task")
    def fallback(self, error):
        """错误后备处理"""
        return "Using cached data"

flow = RobustFlow(error_handler=handle_error)
```

### 9.2 重试机制

```python
flow = Flow(
    max_retries=3,
    retry_delay=2  # 秒
)
```

---

## 10. Flow 配置

### 10.1 完整配置

```python
from crewai.flow import FlowConfig

config = FlowConfig(
    # 并行任务数
    max_parallel_tasks=5,
    
    # 超时设置
    task_timeout=300,
    flow_timeout=3600,
    
    # 重试配置
    max_retries=3,
    retry_delay=2,
    
    # 缓存配置
    enable_cache=True,
    
    # 日志配置
    verbose=True,
    log_level="INFO"
)

flow = MyFlow(config=config)
```

### 10.2 配置说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_parallel_tasks` | 5 | 最大并行任务数 |
| `task_timeout` | 300 | 单任务超时(秒) |
| `flow_timeout` | 3600 | 流程超时(秒) |
| `max_retries` | 3 | 最大重试次数 |
| `retry_delay` | 2 | 重试延迟(秒) |
| `enable_cache` | True | 启用缓存 |

---

## 11. 高级特性

### 11.1 动态任务添加

```python
@listen("process_item")
def add_dependent_tasks(self, item):
    """根据处理结果动态添加任务"""
    if item.get("needs_review"):
        self.add_task(
            Task(description="Review item", agent=reviewer)
        )
```

### 11.2 状态依赖

```python
# 任务 B 等待任务 A 完成并更新状态
@listen("task_a")
def task_b(self, output_from_a):
    # 确保依赖状态已更新
    state_a = self.get_state("task_a_output")
    return process_b(state_a)
```

### 11.3 流程监控

```python
def on_task_start(task_name):
    print(f"Starting: {task_name}")

def on_task_complete(task_name, result):
    print(f"Completed: {task_name}")

flow = MyFlow(
    callbacks={
        "task_start": on_task_start,
        "task_complete": on_task_complete
    }
)
```

---

## 12. Flow 与 Crew 集成

### 12.1 在 Flow 中使用 Crew

```python
class CrewFlow(Flow):
    @start()
    def start_crew(self):
        """启动 Crew"""
        crew = Crew(
            agents=[researcher, writer],
            tasks=[task1, task2],
            process=Process.sequential
        )
        result = crew.kickoff()
        self.set_state("crew_result", result)
        return result
    
    @listen("start_crew")
    def post_process(self, result):
        """后处理 Crew 结果"""
        return f"Processed: {result}"

flow = CrewFlow()
result = flow.kickoff()
```

### 12.2 在 Crew 中使用 Flow

```python
# 创建 Flow
flow = MyFlow()

# 作为 Tool 使用
flow_tool = FlowTool(flow=flow)

# 添加到 Agent
agent = Agent(
    role="Orchestrator",
    tools=[flow_tool]
)
```
