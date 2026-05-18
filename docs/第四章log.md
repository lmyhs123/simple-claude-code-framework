# 第四章 log：Model Provider

## 1. 这一章学什么

第四章学习的是：

```text
Model Provider
```

它解决的问题是：

```text
AgentLoop 怎么把 messages 和 tools 发给模型？
模型返回后，怎么统一变成框架能理解的 ModelResponse？
```

一句话：

```text
Model Provider 是 Harness 和大模型之间的适配层。
```

不同模型厂商的 API 格式不同，但我们的框架内部不应该到处写厂商细节。

所以我们用 provider 层把差异挡住。

## 2. 第四章后的完整链路

```html
用户输入
-> backend api 接收请求
-> gateway.run_gateway_turn()
-> 读取当前 session / project / skill
-> memory / knowledge 检索项目资料
-> context_builder.build_messages()
-> context_builder 调用 build_system_prompt()
-> system_prompt.py 生成 Harness / 工作规则 / 工具规则 / project / skill 规则
-> context_builder 把 system prompt 放进 messages[0]
-> context_builder 把 history 放进 messages 中间
-> context_builder 把 当前用户问题 + knowledge_context 放进最后一条 user message
-> gateway 创建 ToolRegistry
-> ToolRegistry 延迟注册工具 definitions + factories
-> gateway 通过 get_model_provider() 创建 ModelProvider
-> gateway 创建 AgentLoop
-> AgentLoop 从 ToolRegistry 读取 tools definitions
-> AgentLoop 调 provider.generate(messages, skill, tools)
-> ModelProvider 把 messages + tools 发给 mock 或真实模型
-> OpenAICompatibleProvider.generate()
-> 把框架 messages 转成 API messages
-> 把框架 tools definitions 转成 API tools
-> httpx POST 到 /chat/completions
-> API 返回 JSON
-> provider 调用 _parse_response() 解析 API 返回
-> 如果 JSON 里有 tool_calls，解析第一个 tool_call
-> 把 tool_calls 转成 ModelResponse(tool_call=ToolCall(...))
-> 如果 JSON 里没有 tool_calls，把 content 转成 ModelResponse(text=...)
-> 如果 ModelResponse.text 有内容：AgentLoop 返回最终回答
-> 如果 ModelResponse.tool_call 有内容：AgentLoop 调 ToolExecutor
-> ToolExecutor 从 ToolRegistry 获取工具
-> 如果工具尚未创建：ToolRegistry 用 factory 延迟创建工具
-> ToolExecutor 执行工具 invoke(input_data)
-> 工具返回 ToolResult
-> AgentLoop 把 ToolResult 追加为 role="tool" 的消息
-> AgentLoop 再次调用 provider.generate(...)
-> 模型基于工具结果继续回答或继续请求工具
-> 达到最终回答或 max_agent_steps 后返回
-> gateway 返回 final_text
-> backend api 保存 assistant 消息
-> frontend 渲染回答
```

第四章重点负责这一段：

```text
AgentLoop
-> provider.generate(messages, skill, tools)
-> ModelProvider
-> ModelResponse(text=...) 或 ModelResponse(tool_call=...)
```

## 3. 修改过的文件

第四章主要涉及：

```text
backend/app/model_providers/base.py
backend/app/model_providers/mock_provider.py
backend/app/model_providers/provider_factory.py
backend/app/model_providers/openai_compatible_provider.py
backend/app/agent/loop.py
```

其中：

```text
base.py
定义统一接口和统一返回格式。

mock_provider.py
本地假模型，用来教学和测试，不依赖真实 API。

provider_factory.py
根据配置选择当前使用哪个 provider。

openai_compatible_provider.py
真实 API provider 雏形，负责 OpenAI-compatible API 的输入输出适配。

loop.py
把工具 definitions 传给 provider。
```

## 4. base.py：统一模型层语言

文件位置：

```text
backend/app/model_providers/base.py
```

这个文件定义了三个核心概念：

```text
ToolCall
ModelResponse
ModelProvider
```

### 4.1 ToolCall

```python
@dataclass(frozen=True)
class ToolCall:
    name: str
    input_data: dict[str, Any]
```

它表示：

```text
模型请求调用一个工具。
```

例如：

```python
ToolCall(
    name="read_file",
    input_data={"path": "backend/app/agent/loop.py"},
)
```

### 4.2 ModelResponse

```python
@dataclass(frozen=True)
class ModelResponse:
    text: str | None = None
    tool_call: ToolCall | None = None
```

它表示模型的一次返回。

模型可能直接回答：

```python
ModelResponse(text="这是最终回答")
```

也可能请求工具：

```python
ModelResponse(tool_call=ToolCall(...))
```

这个属性：

```python
@property
def wants_tool(self) -> bool:
    return self.tool_call is not None
```

让 AgentLoop 可以判断：

```text
如果 wants_tool 为 True，就执行工具。
否则，把 text 当作最终回答。
```

### 4.3 ModelProvider

```python
class ModelProvider(Protocol):
    name: str

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        skill: Skill,
        tools: list[dict] | None = None,
    ) -> ModelResponse:
        ...
```

这是 provider 统一接口。

任何模型接入层，只要实现：

```text
name
generate(messages, skill, tools)
```

就能被 AgentLoop 使用。

## 5. AgentLoop 的变化

文件位置：

```text
backend/app/agent/loop.py
```

第四章让 AgentLoop 不只传 messages，还把工具定义传给模型：

```python
tool_definitions = self.tool_registry.list_definitions()
```

然后：

```python
response = provider.generate(
    messages=current_messages,
    skill=skill,
    tools=tool_definitions,
)
```

这一步非常重要。

因为真实模型想调用工具前，必须先知道：

```text
有哪些工具
工具名字是什么
工具描述是什么
工具参数 schema 是什么
```

这些信息来自：

```text
ToolRegistry.list_definitions()
```

## 6. provider_factory.py：模型供应商选择器

文件位置：

```text
backend/app/model_providers/provider_factory.py
```

核心函数：

```python
def get_model_provider() -> ModelProvider:
```

它根据配置选择 provider：

```python
if settings.model_provider == "mock":
    return MockModelProvider()
if settings.model_provider == "openai-compatible":
    return OpenAICompatibleProvider()
```

所以 gateway 不需要知道具体模型厂商。

gateway 只调用：

```python
provider = get_model_provider()
```

这样以后换模型时，主要改 provider 层，不用大改 gateway / loop / tools。

## 7. mock_provider.py：本地假模型

文件位置：

```text
backend/app/model_providers/mock_provider.py
```

它的核心函数也是：

```python
generate(...)
```

mock provider 不调用真实 API。

它根据用户文本里的教学触发器返回：

```text
普通文本
或者工具调用
```

例如：

```text
mock_tool_read: backend/app/agent/loop.py
```

会让 mock provider 返回：

```python
ModelResponse(
    tool_call=ToolCall(
        name="read_file",
        input_data={"path": "backend/app/agent/loop.py"},
    )
)
```

第四章还让它兼容：

```python
tools: list[dict] | None = None
```

但 mock 暂时不使用 tools。

这样做是为了让 mock provider 和真实 provider 接口一致。

## 8. openai_compatible_provider.py：真实 API 适配器

文件位置：

```text
backend/app/model_providers/openai_compatible_provider.py
```

这个文件是第四章最重要的真实 provider 雏形。

核心函数：

```python
generate(...)
```

它负责：

```text
1. 检查 MODEL_API_KEY 和 MODEL_NAME
2. 把框架 messages 转成 API messages
3. 把框架 tools definitions 转成 API tools
4. 用 httpx 请求 /chat/completions
5. 把 API 返回 JSON 解析成 ModelResponse
```

## 9. _normalize_messages()

辅助函数：

```python
def _normalize_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
```

它的作用是：

```text
把框架内部 messages 转成 OpenAI-compatible API 可接受的 messages。
```

尤其注意：

```python
if role == "tool":
    role = "user"
    content = f"Tool result:\n{content}"
```

这是一个 MVP 处理。

因为完整 OpenAI tool message 通常需要 tool_call_id。

我们现在先把工具结果作为普通上下文发回模型，保证链路简单稳定。

## 10. _normalize_tools()

辅助函数：

```python
def _normalize_tools(self, tools: list[dict]) -> list[dict]:
```

它把框架工具定义：

```python
{
    "name": "read_file",
    "description": "...",
    "input_schema": {...},
}
```

转成 OpenAI-compatible 工具格式：

```python
{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "...",
        "parameters": {...},
    },
}
```

这就是：

```text
框架 tools definitions -> API tools
```

## 11. _parse_response()

核心函数：

```python
def _parse_response(self, data: dict) -> ModelResponse:
```

它负责把 API 返回解析成框架统一格式。

如果 API 返回：

```python
{
    "choices": [
        {
            "message": {
                "content": "模型回答"
            }
        }
    ]
}
```

它返回：

```python
ModelResponse(text="模型回答")
```

如果 API 返回：

```python
{
    "choices": [
        {
            "message": {
                "tool_calls": [
                    {
                        "function": {
                            "name": "read_file",
                            "arguments": "{\"path\":\"xxx.py\"}"
                        }
                    }
                ]
            }
        }
    ]
}
```

它返回：

```python
ModelResponse(
    tool_call=ToolCall(
        name="read_file",
        input_data={"path": "xxx.py"},
    )
)
```

这是第四章真正打通工具调用的关键。

## 12. 换模型时要改哪里

如果以后接入新的模型，比如：

```text
Claude
DeepSeek
OpenAI Responses API
本地模型
```

通常不需要改：

```text
gateway
AgentLoop
ToolRegistry
ToolExecutor
Tools
Frontend
```

主要新增或修改一个 provider。

一个 provider 要负责三件事：

```text
1. 输入转换
   框架 messages + tools -> 厂商 API 格式

2. API 调用
   用 httpx 或 SDK 请求模型

3. 输出解析
   厂商返回 JSON -> ModelResponse(text=...) 或 ModelResponse(tool_call=...)
```

所以换模型不是只改：

```text
messages 转换
tools 转换
```

还必须改：

```text
返回结果解析
```

一句话：

```text
换模型时，主要换 provider；provider 负责输入转换、API 调用、输出解析。
```

## 13. 第四章总结

前三章我们有了：

```text
System Prompt：规定模型行为
AgentLoop：组织多步循环
Tools：执行真实动作
```

第四章补上：

```text
ModelProvider：连接大模型，并统一输入输出格式
```

所以现在 mini Claude Code 的核心链路更完整了：

```text
messages + tools
-> provider.generate(...)
-> ModelResponse(text=...) 或 ModelResponse(tool_call=...)
-> AgentLoop 决定结束或执行工具
```

第四章一句话总结：

```text
Model Provider 是模型适配层，它让框架不依赖某一个具体模型厂商。
```
