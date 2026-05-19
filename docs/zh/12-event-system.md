# 事件系统

## 1. 事件系统概述

CrewAI 使用事件总线 (`crewai_event_bus`) 进行组件间通信，实现松耦合的事件驱动架构。

---

## 2. 事件类型

### 2.1 主要事件类型

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
| `TaskStartedEvent` | 任务开始 |
| `TaskCompletedEvent` | 任务完成 |
| `CrewStartedEvent` | Crew 开始执行 |
| `CrewCompletedEvent` | Crew 执行完成 |

### 2.2 事件基类

```python
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

class BaseEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    source: Optional[str] = None
    metadata: dict[str, Any] = {}
```

---

## 3. 事件监听

### 3.1 订阅事件

```python
from crewai.event_bus import crewai_event_bus

def on_memory_save(event):
    print(f"Memory save started: {event.memory_id}")

# 订阅事件
crewai_event_bus.subscribe(MemorySaveStartedEvent, on_memory_save)
```

### 3.2 事件处理函数

```python
def handle_tool_start(event: ToolUsageStartedEvent):
    """处理工具开始事件"""
    print(f"Tool {event.tool_name} started")
    print(f"Arguments: {event.arguments}")

def handle_tool_end(event: ToolUsageFinishedEvent):
    """处理工具完成事件"""
    print(f"Tool {event.tool_name} completed")
    print(f"Result: {event.result[:100]}...")
    print(f"Duration: {event.duration_ms}ms")

def handle_error(event: ToolUsageErrorEvent):
    """处理错误事件"""
    print(f"Error in {event.tool_name}: {event.error}")

# 注册处理函数
crewai_event_bus.subscribe(ToolUsageStartedEvent, handle_tool_start)
crewai_event_bus.subscribe(ToolUsageFinishedEvent, handle_tool_end)
crewai_event_bus.subscribe(ToolUsageErrorEvent, handle_error)
```

---

## 4. 事件发布

### 4.1 手动发布事件

```python
from crewai.event_bus import Event, crewai_event_bus

# 创建事件
event = ToolUsageStartedEvent(
    tool_name="search",
    arguments={"query": "AI trends"},
    source="research_agent"
)

# 发布事件
crewai_event_bus.emit(event)
```

### 4.2 事件工厂

```python
from crewai.event_bus import EventFactory

# 创建事件
event = EventFactory.create(
    "tool_usage_started",
    tool_name="search",
    arguments={"query": "AI"}
)

crewai_event_bus.emit(event)
```

---

## 5. 完整事件示例

### 5.1 任务执行监听

```python
from crewai import Crew, Agent, Task
from crewai.event_bus import crewai_event_bus
from crewai.events import TaskStartedEvent, TaskCompletedEvent

def track_task_execution():
    """任务执行追踪"""
    
    def on_task_start(event: TaskStartedEvent):
        print(f"🔵 Task Started: {event.task_description}")
        print(f"   Agent: {event.agent_role}")
        print(f"   Time: {event.timestamp}")
    
    def on_task_complete(event: TaskCompletedEvent):
        print(f"🟢 Task Completed: {event.task_description}")
        print(f"   Duration: {event.duration_ms}ms")
        print(f"   Output length: {len(event.output)} chars")
    
    def on_task_error(event):
        print(f"🔴 Task Error: {event.task_description}")
        print(f"   Error: {event.error}")
    
    # 注册事件处理
    crewai_event_bus.subscribe(TaskStartedEvent, on_task_start)
    crewai_event_bus.subscribe(TaskCompletedEvent, on_task_complete)
    crewai_event_bus.subscribe(TaskFailedEvent, on_task_error)

# 使用
track_task_execution()

crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()
```

### 5.2 工具调用追踪

```python
def track_tool_usage():
    """工具调用追踪"""
    
    total_calls = 0
    total_duration = 0
    errors = []
    
    def on_tool_start(event: ToolUsageStartedEvent):
        nonlocal total_calls
        total_calls += 1
        print(f"📦 [{total_calls}] {event.tool_name}")
    
    def on_tool_end(event: ToolUsageFinishedEvent):
        nonlocal total_duration
        total_duration += event.duration_ms
        print(f"   ✅ {event.duration_ms:.2f}ms")
    
    def on_error(event: ToolUsageErrorEvent):
        errors.append({
            "tool": event.tool_name,
            "error": event.error
        })
        print(f"   ❌ {event.error}")
    
    crewai_event_bus.subscribe(ToolUsageStartedEvent, on_tool_start)
    crewai_event_bus.subscribe(ToolUsageFinishedEvent, on_tool_end)
    crewai_event_bus.subscribe(ToolUsageErrorEvent, on_error)
    
    # 返回统计信息
    return {
        "total_calls": total_calls,
        "total_duration_ms": total_duration,
        "errors": errors
    }
```

---

## 6. 事件过滤

### 6.1 条件过滤

```python
from crewai.event_bus import event_filter

# 只处理特定 Agent 的事件
def filter_by_agent(event: TaskCompletedEvent):
    return event.agent_role in ["Researcher", "Writer"]

# 使用过滤器
filtered_handler = event_filter(
    handler=on_task_complete,
    condition=filter_by_agent
)

crewai_event_bus.subscribe(TaskCompletedEvent, filtered_handler)
```

### 6.2 正则过滤

```python
import re

def match_task_pattern(event: TaskCompletedEvent):
    pattern = r"^(research|write|edit)"
    return re.match(pattern, event.task_description.lower())

crewai_event_bus.subscribe(TaskCompletedEvent, match_task_pattern)
```

---

## 7. 异步事件处理

### 7.1 异步监听器

```python
import asyncio

async def async_handler(event: TaskCompletedEvent):
    """异步事件处理"""
    await asyncio.sleep(1)  # 模拟异步操作
    print(f"Async processed: {event.task_description}")

# 注册异步处理
crewai_event_bus.subscribe_async(TaskCompletedEvent, async_handler)
```

### 7.2 事件批处理

```python
from collections import defaultdict
from crewai.event_bus import BatchHandler

class BatchProcessor(BatchHandler):
    def __init__(self, batch_size=10):
        self.batch_size = batch_size
        self.pending_events = defaultdict(list)
    
    def handle_batch(self, events: list[TaskCompletedEvent]):
        """处理事件批次"""
        results = [e.output for e in events]
        # 批量处理
        print(f"Batch processed: {len(events)} events")
    
    def batch_size_reached(self) -> bool:
        return len(self.pending_events) >= self.batch_size

processor = BatchProcessor()
crewai_event_bus.subscribe(TaskCompletedEvent, processor)
```

---

## 8. 自定义事件

### 8.1 定义事件

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class CustomEvent(BaseModel):
    """自定义事件"""
    event_type: str = "custom"
    timestamp: datetime = Field(default_factory=datetime.now)
    data: dict[str, Any] = {}
    source: str | None = None
```

### 8.2 发布自定义事件

```python
from crewai.event_bus import crewai_event_bus

# 发布事件
custom_event = CustomEvent(
    event_type="progress_update",
    data={"progress": 75, "status": "processing"},
    source="workflow"
)

crewai_event_bus.emit(custom_event)
```

---

## 9. 事件配置

### 9.1 全局配置

```python
from crewai.event_bus import EventBusConfig

config = EventBusConfig(
    max_handlers=100,              # 最大处理器数
    batch_size=50,                 # 批处理大小
    async_queue_size=1000,         # 异步队列大小
    retry_on_error=True,           # 错误重试
    max_retries=3,                 # 最大重试次数
    retry_delay_ms=1000            # 重试延迟
)

# 应用配置
crewai_event_bus.configure(config)
```

### 9.2 事件转发

```python
class EventForwarder:
    """事件转发器"""
    
    def __init__(self, target_url: str):
        self.target_url = target_url
    
    def forward(self, event: BaseEvent):
        # 发送到外部系统
        requests.post(
            f"{self.target_url}/events",
            json=event.dict()
        )

# 使用
forwarder = EventForwarder("http://monitoring:8080")
crewai_event_bus.subscribe(ToolUsageFinishedEvent, forwarder.forward)
```

---

## 10. 性能考虑

### 10.1 异步处理

```python
# 使用异步处理器避免阻塞主流程
crewai_event_bus.subscribe_async(
    TaskCompletedEvent,
    async_log_handler,
    queue_size=1000
)
```

### 10.2 事件过滤

```python
# 过滤不需要的事件以减少开销
def important_only(event: TaskCompletedEvent):
    return event.duration_ms > 5000  # 只处理耗时超过5秒的任务

crewai_event_bus.subscribe(TaskCompletedEvent, important_only)
```

---

## 11. 最佳实践

| 实践 | 说明 |
|------|------|
| 异步处理 | 使用 `subscribe_async` 处理耗时操作 |
| 事件过滤 | 只订阅需要的事件类型 |
| 错误处理 | 事件处理中捕获异常 |
| 资源清理 | 取消订阅不再需要的事件 |
| 批处理 | 高频事件使用批处理 |