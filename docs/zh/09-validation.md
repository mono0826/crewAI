# 验证机制

## 1. 验证概述

CrewAI 提供多种验证机制来确保输入和输出的质量，包括 InputValidation（输入验证）和 OutputValidation（输出验证）。

---

## 2. 输入验证 (InputValidation)

### 2.1 基本使用

```python
from pydantic import BaseModel, Field
from crewai.utilities import InputValidator

class TaskInput(BaseModel):
    topic: str = Field(..., min_length=3, max_length=100)
    word_count: int = Field(..., ge=100, le=5000)
    style: str = Field(default="formal")

validator = InputValidator(schema=TaskInput)

# 验证输入
try:
    validated = validator.validate(
        {"topic": "AI", "word_count": 500}
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### 2.2 Agent 输入验证

```python
from crewai import Agent

agent = Agent(
    role="Writer",
    input_validator=TaskInput,  # 验证 Agent 输入
    tools=[]
)
```

### 2.3 自定义验证器

```python
from crewai.utilities import BaseValidator

class CustomInputValidator(BaseValidator):
    def validate(self, inputs: dict) -> dict:
        """自定义验证逻辑"""
        
        # 检查必需字段
        if "required_field" not in inputs:
            raise ValueError("Missing required_field")
        
        # 自定义业务规则
        if inputs.get("budget", 0) < inputs.get("min_budget", 0):
            raise ValueError("Budget must be greater than minimum")
        
        return inputs

validator = CustomInputValidator()
```

---

## 3. 输出验证 (OutputValidation)

### 3.1 Pydantic 模型验证

```python
from pydantic import BaseModel, Field
from crewai import Task

class ArticleSummary(BaseModel):
    title: str = Field(..., min_length=5)
    summary: str = Field(..., min_length=50, max_length=500)
    key_points: list[str] = Field(..., min_items=3)
    sentiment: str = Field(..., pattern="^(positive|negative|neutral)$")

task = Task(
    description="Summarize the article",
    agent=writer,
    output_pydantic=ArticleSummary  # 输出验证
)

result = task.execute()
# result.pydantic 是 ArticleSummary 验证后的对象
```

### 3.2 JSON Schema 验证

```python
from crewai import Task
import json

json_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
        "email": {"type": "string", "format": "email"}
    },
    "required": ["name", "email"]
}

task = Task(
    description="Extract user info",
    agent=extractor,
    output_json_schema=json_schema
)
```

### 3.3 自定义输出验证

```python
from crewai.utilities import OutputValidator

class CustomOutputValidator(OutputValidator):
    def validate(self, output: str) -> bool:
        """自定义输出验证"""
        
        # 检查输出长度
        if len(output) < 100:
            return False
        
        # 检查是否包含关键词
        required_keywords = ["conclusion", "summary"]
        if not any(kw in output.lower() for kw in required_keywords):
            return False
        
        return True
    
    def get_error_message(self) -> str:
        return "Output does not meet quality requirements"

task = Task(
    description="Write analysis",
    agent=analyzer,
    output_validator=CustomOutputValidator()
)
```

---

## 4. 任务级验证

### 4.1 任务输入验证

```python
from crewai import Task
from pydantic import BaseModel, Field

class TaskInputModel(BaseModel):
    query: str = Field(..., min_length=5)
    max_results: int = Field(default=10, ge=1, le=100)

task = Task(
    description="Search for information",
    agent=search_agent,
    input_schema=TaskInputModel,  # 任务输入验证
    input={"query": "AI trends", "max_results": 20}
)
```

### 4.2 任务输出验证

```python
class TaskOutputModel(BaseModel):
    results: list[dict]
    total_count: int
    query_time: float

task = Task(
    description="Search and return results",
    agent=search_agent,
    output_pydantic=TaskOutputModel
)
```

### 4.3 验证回调

```python
def validate_and_transform(inputs: dict) -> dict:
    """验证并转换输入"""
    # 清理数据
    inputs["query"] = inputs["query"].strip()
    inputs["query"] = inputs["query"].lower()
    return inputs

task = Task(
    description="Process data",
    agent=processor,
    input_preprocessor=validate_and_transform
)
```

---

## 5. Agent 级验证

### 5.1 Agent 输入验证

```python
agent = Agent(
    role="Researcher",
    input_validator={
        "query": {"type": "string", "minLength": 3},
        "depth": {"type": "string", "enum": ["shallow", "deep"]}
    }
)
```

### 5.2 Agent 输出验证

```python
class AgentResponse(BaseModel):
    content: str
    confidence: float = Field(..., ge=0, le=1)
    sources: list[str] = []

agent = Agent(
    role="Researcher",
    output_validator=AgentResponse
)
```

---

## 6. Crew 级验证

### 6.1 Crew 输入验证

```python
from crewai import Crew

crew = Crew(
    agents=[agent1, agent2],
    tasks=[task1, task2],
    input_validator={
        "user_request": {"type": "string", "minLength": 10},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]}
    }
)

result = crew.kickoff(inputs={
    "user_request": "Help me with...",
    "priority": "high"
})
```

### 6.2 Crew 输出验证

```python
class FinalOutput(BaseModel):
    summary: str
    recommendations: list[str]
    next_steps: list[str]

crew = Crew(
    agents=[...],
    tasks=[...],
    output_validator=FinalOutput
)
```

---

## 7. 验证结果处理

### 7.1 验证错误处理

```python
from crewai.exceptions import ValidationException

def safe_validate(validator, data):
    """安全验证并处理错误"""
    try:
        return validator.validate(data)
    except ValidationException as e:
        # 记录错误
        logger.error(f"Validation error: {e}")
        # 返回默认值或重新抛出
        return None
    except Exception as e:
        # 处理其他错误
        raise
```

### 7.2 重试机制

```python
from crewai.utilities import RetryValidator

class RetryWithValidation(RetryValidator):
    def __init__(self, validator, max_retries=3):
        super().__init__(max_retries)
        self.validator = validator
    
    def validate_with_retry(self, data):
        for attempt in range(self.max_retries):
            try:
                return self.validator.validate(data)
            except ValidationError as e:
                if attempt == self.max_retries - 1:
                    raise
                # 记录并重试
                logger.warning(f"Validation failed, retrying: {e}")
        return None
```

---

## 8. 验证配置

### 8.1 全局验证配置

```python
from crewai import Config

# 全局验证设置
config = Config(
    validation={
        "strict_mode": True,           # 严格模式
        "fail_fast": False,             # 快速失败
        "log_errors": True             # 记录错误
    }
)
```

### 8.2 验证器工厂

```python
from crewai.utilities import ValidatorFactory

# 创建验证器
validator = ValidatorFactory.create(
    "pydantic",
    model=TaskInputModel
)

validator = ValidatorFactory.create(
    "json_schema",
    schema=json_schema
)

validator = ValidatorFactory.create(
    "custom",
    validator_class=CustomValidator
)
```

---

## 9. 验证最佳实践

### 9.1 输入验证建议

| 场景 | 建议 |
|------|------|
| 必填字段 | 使用 `Field(..., ...)` 标记 |
| 数值范围 | 使用 `ge`, `le` 约束 |
| 字符串格式 | 使用正则表达式 `pattern` |
| 枚举值 | 使用 `enum` 限制 |

### 9.2 输出验证建议

| 场景 | 建议 |
|------|------|
| 结构化输出 | 使用 Pydantic 模型 |
| 质量检查 | 使用自定义验证器 |
| 格式验证 | 使用 JSON Schema |

### 9.3 错误消息

```python
class DetailedValidator(BaseValidator):
    def validate(self, data: dict) -> dict:
        errors = []
        
        if not data.get("name"):
            errors.append("name is required")
        
        if data.get("age", 0) < 0:
            errors.append("age must be non-negative")
        
        if errors:
            raise ValidationError(
                message="Validation failed",
                errors=errors,
                data=data
            )
        
        return data
```

---

## 10. 示例

### 10.1 完整验证流程

```python
from pydantic import BaseModel, Field, validator
from crewai import Agent, Task, Crew
from crewai.utilities import InputValidator, OutputValidator

# 定义输入模型
class ResearchInput(BaseModel):
    topic: str = Field(..., min_length=5, max_length=100)
    depth: str = Field(default="medium", pattern="^(shallow|medium|deep)$")
    sources_count: int = Field(default=5, ge=1, le=20)

# 定义输出模型
class ResearchOutput(BaseModel):
    summary: str = Field(..., min_length=100)
    key_findings: list[str] = Field(..., min_items=3)
    sources: list[str]
    confidence: float = Field(..., ge=0, le=1)
    
    @validator("summary")
    def summary_must_be_meaningful(cls, v):
        if "error" in v.lower() or "failed" in v.lower():
            raise ValueError("Summary indicates failure")
        return v

# 创建任务
task = Task(
    description="Research {topic} in {depth} depth",
    input_schema=ResearchInput,
    output_pydantic=ResearchOutput,
    agent=researcher
)

# 执行
result = task.execute(
    inputs={
        "topic": "Artificial Intelligence trends",
        "depth": "deep",
        "sources_count": 10
    }
)

# 访问验证后的输出
validated_output: ResearchOutput = result.pydantic
print(validated_output.summary)
```

---

## 11. 自定义验证器示例

### 11.1 内容质量验证器

```python
class ContentQualityValidator(OutputValidator):
    def __init__(self, min_length=100, required_keywords=None):
        self.min_length = min_length
        self.required_keywords = required_keywords or []
    
    def validate(self, output: str) -> bool:
        # 长度检查
        if len(output) < self.min_length:
            return False
        
        # 关键词检查
        output_lower = output.lower()
        for keyword in self.required_keywords:
            if keyword.lower() not in output_lower:
                return False
        
        # 检查是否为错误消息
        error_indicators = ["error", "failed", "exception"]
        if any(indicator in output_lower for indicator in error_indicators):
            return False
        
        return True
    
    def get_error_message(self) -> str:
        return f"Output must be at least {self.min_length} chars and contain {self.required_keywords}"
```

### 11.2 数值范围验证器

```python
class NumericRangeValidator(InputValidator):
    def __init__(self, field: str, min_val: float, max_val: float):
        self.field = field
        self.min_val = min_val
        self.max_val = max_val
    
    def validate(self, inputs: dict) -> dict:
        value = inputs.get(self.field)
        
        if value is None:
            raise ValueError(f"{self.field} is required")
        
        if not isinstance(value, (int, float)):
            raise ValueError(f"{self.field} must be a number")
        
        if not (self.min_val <= value <= self.max_val):
            raise ValueError(
                f"{self.field} must be between {self.min_val} and {self.max_val}"
            )
        
        return inputs
```
