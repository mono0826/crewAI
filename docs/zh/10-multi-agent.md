# 多 Agent 通信协议

## 1. 通信机制概述

CrewAI 支持多种 Agent 间通信机制：

1. **内部委托** (Delegation): 同一 Crew 内 Agent 之间的任务委托
2. **A2A 协议**: 跨Crew/跨系统的 Agent 到 Agent 通信

---

## 2. 内部委托机制

### 2.1 委托工具

CrewAI 提供两种委托工具：

1. **DelegateWorkTool**: 将任务委托给其他 Agent
2. **AskQuestionTool**: 向其他 Agent 提问

```python
class DelegateWorkTool(BaseAgentTool):
    name: str = "Delegate work to coworker"
    description: str = "Delegate a specific task to another agent"
    
    def _execute(self, agent_name: str, task: str, context: str = None) -> str:
        # 1. 查找目标 Agent (大小写不敏感)
        agent = [a for a in self.agents 
                 if sanitize(a.role) == sanitize(agent_name)]
        
        if not agent:
            return f"Agent '{agent_name}' not found"
        
        selected_agent = agent[0]
        
        # 2. 创建任务
        task_with_agent = Task(
            description=task,
            agent=selected_agent,
            context=context
        )
        
        # 3. 执行任务
        return selected_agent.execute_task(task_with_agent, context)
```

### 2.2 委托流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│          Agent A 调用 "Delegate work to coworker" 工具                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  工具执行: DelegateWorkTool._execute()                                  │
│  - 查找目标 Agent (通过 role 匹配)                                     │
│  - 创建新 Task (description, agent=target_agent)                        │
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

### 2.3 启用委托

```python
# 允许 Agent 委托任务
agent = Agent(
    role="Team Leader",
    allow_delegation=True,  # 启用委托
    agents=[agent_b, agent_c]  # 可委托的 Agent 列表
)
```

---

## 3. A2A 协议 (Agent-to-Agent)

### 3.1 协议概述

A2A 是 Google 主导的开放协议，用于跨系统 Agent 通信。它提供了标准化的 Agent 发现、任务提交和结果获取机制。

### 3.2 核心组件

| 组件 | 文件位置 | 功能 |
|------|----------|------|
| `A2AWrapper` | `a2a/wrapper.py` | Agent 包装器 |
| `DelegationContext` | `a2a/wrapper.py` | 委托上下文 |
| `execute_a2a_delegation` | `a2a/utils/delegation.py` | A2A 委托执行 |

### 3.3 A2A 委托执行流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│              execute_a2a_delegation(endpoint, task_description, ...)  │
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
│     - Message(role="user", content=task_description)                 │
│     - 添加上下文、历史记录                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. 发送任务 (通过 A2A Client)                                         │
│     - a2a_client.send_message()                                       │
│     - 处理流式或非流式响应                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. 处理响应                                                           │
│     - 解析 TaskStateResult                                             │
│     - 提取结果或错误                                                   │
│     - 返回给调用者                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. A2A 客户端使用

### 4.1 创建 A2A 客户端

```python
from crewai.a2a import A2AClient

client = A2AClient(
    endpoint="http://remote-agent:8000",
    api_key="your-api-key"  # 可选
)
```

### 4.2 发送任务

```python
# 发送同步任务
response = client.send_message(
    message="Analyze this data and provide insights",
    context={"data": "..."}
)

print(response.result)
```

### 4.3 流式任务

```python
# 发送流式任务
for chunk in client.send_message_streaming(
    message="Generate a long report",
):
    print(chunk, end="", flush=True)
```

---

## 5. A2A 特性

### 5.1 认证支持

```python
# API Key 认证
client = A2AClient(
    endpoint="http://remote-agent:8000",
    api_key="your-api-key"
)

# Bearer Token 认证
client = A2AClient(
    endpoint="http://remote-agent:8000",
    token="your-bearer-token"
)

# OAuth2 认证
client = A2AClient(
    endpoint="http://remote-agent:8000",
    oauth2={
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "token_url": "https://auth.example.com/oauth/token"
    }
)
```

### 5.2 任务状态跟踪

```python
# 发送长时间运行任务
task_id = client.send_message(
    message="Process large dataset",
    wait_for_completion=False  # 不等待完成
)

# 检查任务状态
while True:
    status = client.get_task_status(task_id)
    print(f"Status: {status.state}")
    
    if status.state in ["completed", "failed"]:
        break
    
    time.sleep(5)

# 获取结果
result = client.get_task_result(task_id)
```

### 5.3 对话历史

```python
# 发送带历史的消息
response = client.send_message(
    message="Continue the analysis",
    history=[
        {"role": "user", "content": "First question"},
        {"role": "agent", "content": "First answer"}
    ]
)
```

---

## 6. 内部委托详解

### 6.1 委托工具实现

```python
class DelegateWorkTool(BaseAgentTool):
    name: str = "Delegate work to coworker"
    description: str = "Delegate a specific task to another agent in your team"
    
    def _execute(
        self,
        agent_name: str,
        task: str,
        context: str = None,
        tools: list[str] = None
    ) -> str:
        """委托任务给其他 Agent"""
        
        # 1. 查找目标 Agent
        target_agent = self._find_agent(agent_name)
        
        if not target_agent:
            return f"Error: Agent '{agent_name}' not found. Available agents: {[a.role for a in self.agents]}"
        
        # 2. 创建任务
        delegated_task = Task(
            description=task,
            agent=target_agent,
            context=context,
            tools=tools
        )
        
        # 3. 执行任务
        try:
            result = target_agent.execute_task(
                task=delegated_task,
                context=context
            )
            return f"Task delegated to {agent_name} completed:\n\n{result.result}"
        except Exception as e:
            return f"Error executing delegated task: {str(e)}"
    
    def _find_agent(self, name: str):
        """查找 Agent（大小写不敏感匹配）"""
        name_normalized = name.lower().strip()
        for agent in self.agents:
            if agent.role.lower().strip() == name_normalized:
                return agent
        return None
```

### 6.2 提问工具实现

```python
class AskQuestionTool(BaseAgentTool):
    name: str = "Ask a question to coworker"
    description: str = "Ask another agent a specific question"
    
    def _execute(
        self,
        agent_name: str,
        question: str,
        context: str = None
    ) -> str:
        """向其他 Agent 提问"""
        
        # 1. 查找目标 Agent
        target_agent = self._find_agent(agent_name)
        
        if not target_agent:
            return f"Error: Agent '{agent_name}' not found"
        
        # 2. 构建问题任务
        question_task = Task(
            description=f"Answer this question: {question}",
            context=context
        )
        
        # 3. 执行任务
        result = target_agent.execute_task(task=question_task)
        return result.result
```

---

## 7. Crew 间通信

### 7.1 创建 A2A Agent

```python
from crewai.a2a import A2AAgent

# 创建跨系统通信的 Agent
a2a_agent = A2AAgent(
    role="Remote Coordinator",
    goal="Coordinate with remote agents",
    endpoint="http://remote-crew-agent:8000",
    capabilities=["research", "analysis", "writing"]
)
```

### 7.2 使用 A2A Agent

```python
# 创建 Crew
crew = Crew(
    agents=[local_agent, a2a_agent],
    tasks=[task1, task2]
)
```

---

## 8. 消息格式

### 8.1 A2A 消息格式

```python
from crewai.a2a import Message, TextContent, MessageRole

# 创建消息
message = Message(
    role=MessageRole.USER,
    content=TextContent(
        text="Analyze the following data: ..."
    ),
    metadata={
        "priority": "high",
        "deadline": "2024-01-01"
    }
)
```

### 8.2 任务格式

```python
from crewai.a2a import Task, TaskParams

task = Task(
    message=message,
    params=TaskParams(
        execution_mode="async",
        callback_url="http://localhost/callback"
    )
)
```

---

## 9. 错误处理

### 9.1 委托错误处理

```python
def safe_delegate(tool, agent_name, task, context=None):
    """安全地委托任务"""
    try:
        result = tool._execute(
            agent_name=agent_name,
            task=task,
            context=context
        )
        
        # 检查返回的错误
        if "Error" in result:
            logger.error(f"Delegation failed: {result}")
            return None
            
        return result
        
    except Exception as e:
        logger.exception(f"Exception during delegation: {e}")
        return None
```

### 9.2 A2A 错误处理

```python
try:
    response = client.send_message(
        message="Process task",
        timeout=30
    )
except TimeoutError:
    print("Request timed out")
except AuthenticationError:
    print("Authentication failed")
except AgentNotFoundError:
    print("Remote agent not found")
except Exception as e:
    print(f"Error: {e}")
```

---

## 10. 最佳实践

### 10.1 委托设计

| 场景 | 建议 |
|------|------|
| 简单任务 | 直接执行，不委托 |
| 专业任务 | 委托给专业 Agent |
| 多步骤任务 | 创建子任务并委托 |

### 10.2 A2A 使用

| 场景 | 建议 |
|------|------|
| 远程 Crew | 使用 A2A 协议 |
| 跨组织协作 | 使用 A2A + OAuth2 |
| 本地测试 | 使用模拟 A2A Server |

### 10.3 错误处理

- 始终处理 Agent 未找到的情况
- 为长时间运行任务设置超时
- 记录委托日志以便调试
