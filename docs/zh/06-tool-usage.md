# Tool 工具调用机制
> 对应文件: lib\crewai\src\crewai\tools\tool_usage.py
> 
## 1. 工具系统概述

CrewAI 的工具系统允许 Agent 与外部世界交互，执行搜索、计算、API 调用等各种操作。

---

## 2. 工具调用流程

### 2.1 完整流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│              tool_utils.execute_tool_and_check_finality                 |
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
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

### 2.2 工具选择算法

```python
def _select_tool(self, tool_name: str) -> Any:
    """使用相似度匹配选择工具"""
    
    # 标准化工具名称
    sanitized_input = sanitize(tool_name)
    
    # 遍历所有可用工具
    for tool in self.tools:
        sanitized_tool = sanitize(tool.name)
        
        # 精确匹配
        if sanitized_tool == sanitized_input:
            return tool
        
        # 相似度匹配
        ratio = SequenceMatcher(None, sanitized_tool, sanitized_input).ratio()
        if ratio > 0.85:  # 阈值
            return tool
    
    # 找不到工具
    error = f"Action '{tool_name}' don't exist..."
    crewai_event_bus.emit(self, ToolSelectionErrorEvent(...))
    raise Exception(error)
```

---

## 3. 工具缓存

### 3.1 缓存机制

```python
class ToolCache:
    """工具调用结果缓存"""
    
    def __init__(self):
        self._cache = {}  # (tool_name, input) -> result
    
    def read(self, tool_name: str, input: str) -> str | None:
        """读取缓存"""
        key = self._make_key(tool_name, input)
        return self._cache.get(key)
    
    def write(self, tool_name: str, input: str, result: str):
        """写入缓存"""
        key = self._make_key(tool_name, input)
        self._cache[key] = result
    
    def _make_key(self, tool_name: str, input: str) -> str:
        """生成缓存键"""
        return hash(f"{tool_name}:{input}")
```

### 3.2 缓存配置

```python
from crewai import Crew

crew = Crew(
    agents=[agent],
    tasks=[task],
    cache=True  # 启用缓存
)
```

### 3.3 自定义缓存函数

```python
def should_cache(arguments, result):
    """自定义缓存逻辑"""
    # 不缓存错误结果
    if "error" in result.lower():
        return False
    # 不缓存包含时间的结果
    if "timestamp" in arguments:
        return False
    return True

tool = CustomTool(
    cache_function=should_cache
)
```

---

## 4. 失败处理机制

### 4.1 重试配置

```python
class ToolUsage:
    _max_parsing_attempts: int = 3      # 默认最大解析尝试次数
    _remember_format_after_usages: int = 3  # 格式记忆次数
```

### 4.2 错误处理代码

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
    
    # 递归调用
    if should_retry:
        return self.use(calling=calling, tool_string=tool_string)
```

#### 几种错误类型（见ToolUsage._tool_calling）
（1）Tool工具名错误/不存在(ToolUsage._select_tool)

* 工具名不存在
```python
error = f"Action '{tool_name}' don't exist, these are the only available Actions:\n{self.tools_description}"
raise Exception(error)
```

* 工具名错误
```python
error = f"I forgot the Action name, these are the only available Actions: {self.tools_description}"
raise Exception(error)
```

（2）Tool 输入参数不对（ToolUsage._validate_tool_input）
> 输入参数：Json or Python literal
```python
error_message = (
            "Tool input must be a valid dictionary in JSON or Python literal format"
        )
raise Exception(error_message)
```

在返回 Tool 报错时，使用self._run_attempts计数，重复3次递归
```python
except Exception as e:
    self._run_attempts += 1
    if self._run_attempts > self._max_parsing_attempts:
        return ToolUsageError(
            f"{I18N_DEFAULT.errors('tool_usage_error').format(error=e)}\nMoving on then. {I18N_DEFAULT.slice('format').format(tool_names=self.tools_names)}"
        )
    return self._tool_calling(tool_string)
```

？这里有一个疑问，本身传进来的参数**tool_string**在第一轮解析的时候就已经报错了，那后面重复多次的意义在哪？可以直接返回给**LLM**进行才处理，不用在这里重复尝试。



### 4.3 重试策略

| 模型类型 | 默认重试次数 | 说明 |
|----------|-------------|------|
| GPT-4, O1 | 2 | 更大模型通常更准确 |
| 其他模型 | 3 | 标准重试次数 |

---

## 5. 循环检测与防止

```python
def _invoke_loop_react(self) -> AgentFinish:
    while not isinstance(formatted_answer, AgentFinish):
        try:
            if has_reached_max_iterations(self.iterations, self.max_iter):
                formatted_answer = handle_max_iterations_exceeded()
                break

            answer = get_llm_response()
        
        self.iterations += 1

    return formatted_answer

```

## 6. 内置工具

### 6.1 搜索工具

```python
from crewai.tools import SerperDevTool, SearchTool

# Serper Dev 搜索
search_tool = SerperDevTool(
    api_key="your-api-key",
    search_type="search"  # 或 "news", "images"
)

# 通用搜索
search = SearchTool()
```

### 6.2 网页抓取

```python
from crewai.tools import BrowserbaseTool, ScrapeWebsiteTool

# Browserbase
browser = BrowserbaseTool(
    api_key="your-api-key"
)

# 网站抓取
scraper = ScrapeWebsiteTool()
```

### 6.3 文件操作

```python
from crewai.tools import FileReadTool, FileWriteTool

# 读取文件
read_tool = FileReadTool(
    file_path="data.txt"
)

# 写入文件
write_tool = FileWriteTool(
    file_path="output.txt"
)
```

### 6.4 代码执行

```python
from crewai.tools import PythonTool

# Python 代码执行
python_tool = PythonTool()

# 执行代码
result = python_tool.execute(code="print('Hello World')")
```

### 6.5 自定义工具

```python
from crewai.tools import BaseTool
from pydantic import Field

class MyCustomTool(BaseTool):
    name: str = "my_custom_tool"
    description: str = "Description of what the tool does"
    
    def _execute(self, param1: str = Field(description="Parameter 1")):
        """工具执行逻辑"""
        return f"Processed: {param1}"

# 使用自定义工具
tool = MyCustomTool()
```

---

## 7. 工具类型详解

### 7.1 AgentTool - Agent 操作工具

```python
from crewai.tools import DelegateWorkTool, AskQuestionTool

# 委托工作
delegate_tool = DelegateWorkTool(agents=agents)

# 提问
ask_tool = AskQuestionTool(agents=agents)
```

### 7.2 Tool - 基础工具

```python
from crewai import Tool

# 创建工具
tool = Tool.from_function(
    name="calculator",
    description="Perform calculations",
    func=lambda x: eval(x)
)

# 或使用装饰器
@tool("calculator", description="Perform calculations")
def calculate(expression: str) -> str:
    return str(eval(expression))
```

---

## 8. 工具配置

### 8.1 工具超时

```python
tool = CustomTool(
    timeout=30  # 30秒超时
)
```

### 8.2 工具重试

```python
tool = CustomTool(
    max_retries=3,
    retry_delay=1  # 重试延迟（秒）
)
```

### 8.3 工具错误处理

```python
from crewai.tools import ToolOutput

def custom_error_handler(error: Exception) -> ToolOutput:
    """自定义错误处理"""
    return ToolOutput(
        result=f"Error: {str(error)}",
        tool_name="custom_tool",
        success=False
    )

tool = CustomTool(
    error_handler=custom_error_handler
)
```

---

## 9. 工具验证

### 9.1 输入验证

```python
class ValidatedTool(BaseTool):
    name: str = "validated_tool"
    description: str = "Tool with input validation"
    
    def _execute(self, param: str = Field(...)):
        # 验证输入
        if not param or len(param) < 3:
            raise ValueError("参数长度必须至少为3")
        
        return f"Processed: {param}"
```

### 9.2 输出验证

```python
def validate_output(output: str) -> bool:
    """验证工具输出"""
    # 检查输出格式
    if not output:
        return False
    # 检查输出长度
    if len(output) > 10000:
        return False
    return True

tool = CustomTool(
    output_validator=validate_output
)
```

---

## 10. 工具事件系统

### 10.1 事件类型

| 事件类型 | 触发时机 |
|----------|----------|
| `ToolUsageStartedEvent` | 开始使用工具 |
| `ToolUsageFinishedEvent` | 工具使用完成 |
| `ToolSelectionErrorEvent` | 工具选择错误 |
| `ToolUsageErrorEvent` | 工具执行错误 |

### 10.2 监听工具事件

```python
from crewai.event_bus import crewai_event_bus

def on_tool_start(tool_name, arguments):
    print(f"Starting tool: {tool_name}")

def on_tool_end(tool_name, result):
    print(f"Tool {tool_name} completed")

crewai_event_bus.subscribe(ToolUsageStartedEvent, on_tool_start)
crewai_event_bus.subscribe(ToolUsageFinishedEvent, on_tool_end)
```

---

## 11. 工具示例

### 11.1 完整工具示例

```python
from crewai import Agent
from crewai.tools import BaseTool, Tool
from pydantic import Field
import requests

class WeatherTool(BaseTool):
    name: str = "get_weather"
    description: str = "Get weather information for a location"
    
    def _execute(
        self,
        location: str = Field(description="City name"),
        units: str = Field(default="celsius", description="Temperature units")
    ) -> str:
        """获取天气信息"""
        # 这里应该是实际的 API 调用
        return f"Weather in {location}: 22°C, Sunny"

# 使用工具
weather_tool = WeatherTool()

agent = Agent(
    role="Weather Assistant",
    goal="Provide accurate weather information",
    tools=[weather_tool]
)
```

### 11.2 工具链示例

```python
# 创建工具链
search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()
summarize_tool = SummarizeTool()

# 组合使用
researcher = Agent(
    role="Researcher",
    tools=[search_tool, scrape_tool, summarize_tool]
)
```
