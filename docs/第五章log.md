# 第五章 log：Tool Calling 深化

## 1. 这一章学什么

第五章继续学习工具调用。

前面我们已经有：

```text
ToolDefinition
ToolRegistry
ToolExecutor
AgentLoop
ToolResult
```

但第五章要把工具调用从“能跑”推进到“更像 Claude Code 的 Harness 过程记录”。

这一章目前完成了三件事：

```text
1. 增加 ToolTrace：记录一次工具调用的完整轨迹。
2. 把工具结果消息改成 JSON observation。
3. 给 ToolExecutor 增加结构化错误类型。
```

一句话：

```text
模型请求工具，Harness 执行工具，并记录清楚这次动作发生了什么。
```

## 2. 第五章后的完整链路

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
-> 模型返回 ModelResponse
-> 如果 ModelResponse.text 有内容：AgentLoop 返回最终回答
-> 如果 ModelResponse.tool_call 有内容：AgentLoop 调 ToolExecutor
-> ToolExecutor 先检查 tool input 是否是 dict
-> ToolExecutor 从 ToolRegistry 获取工具
-> 如果工具不存在，返回 error_type="unknown_tool"
-> 如果工具尚未创建：ToolRegistry 用 factory 延迟创建工具
-> ToolExecutor 执行工具 invoke(input_data)
-> 如果工具内部抛异常，返回 error_type="tool_exception"
-> 工具返回 ToolResult
-> AgentLoop 把 ToolCall + ToolResult 保存成 ToolTrace
-> AgentLoop 把 ToolResult 格式化成 JSON observation
-> JSON observation 作为 role="tool" 消息追加回 current_messages
-> AgentLoop 再次调用 provider.generate(...)
-> 模型基于结构化工具结果继续回答或继续请求工具
-> 达到最终回答或 max_agent_steps 后返回 AgentLoopResult
-> AgentLoopResult 同时包含 final_text、tool_results、tool_traces
-> gateway 返回 final_text
-> backend api 保存 assistant 消息
-> frontend 渲染回答
```

## 3. ToolTrace：工具调用轨迹

修改文件：

```text
backend/app/agent/loop.py
```

新增：

```python
@dataclass
class ToolTrace:
    """One tool call plus its execution result."""

    tool_call: ToolCall
    result: ToolResult
```

它记录的是：

```text
模型请求了哪个工具
模型传了什么参数
工具执行是否成功
工具返回了什么内容
```

以前只有：

```python
tool_results: list[ToolResult]
```

它只能告诉我们：

```text
工具执行结果是什么
```

但不知道：

```text
这个结果来自哪个工具调用
```

所以现在 `AgentLoopResult` 变成：

```python
@dataclass
class AgentLoopResult:
    final_text: str
    tool_results: list[ToolResult]
    tool_traces: list[ToolTrace]
```

`tool_results` 保留是为了兼容已有代码。

`tool_traces` 是更完整的新结构。

## 4. ToolTrace 的核心实现逻辑

核心代码：

```python
tool_result = self.tool_executor.execute(
    tool_name=response.tool_call.name,
    input_data=response.tool_call.input_data,
)
tool_results.append(tool_result)
tool_traces.append(
    ToolTrace(
        tool_call=response.tool_call,
        result=tool_result,
    )
)
```

逻辑是：

```text
1. 模型返回 response.tool_call。
2. AgentLoop 把 tool_call 交给 ToolExecutor。
3. ToolExecutor 执行工具，返回 ToolResult。
4. 旧结构 tool_results 保存结果。
5. 新结构 tool_traces 保存 tool_call + tool_result。
```

你可以这样理解：

```text
ToolResult 是“结果”。
ToolTrace 是“证据链”。
```

未来做前端工具调用展示、audit 审计、debug 调试时，应该优先看 `tool_traces`。

## 5. JSON observation：工具结果回传给模型

修改文件：

```text
backend/app/agent/loop.py
```

核心函数：

```python
def _format_tool_result(...)
```

以前它返回松散文本：

```text
Tool name: todo_write
Tool input: {...}
Tool success: True
Tool result:
...
```

现在返回结构化 JSON：

```python
observation = {
    "type": "tool_result",
    "tool_name": response.tool_call.name,
    "tool_input": response.tool_call.input_data,
    "ok": tool_result.ok,
    "content": tool_result.content,
    "metadata": tool_result.metadata or {},
}
return json.dumps(
    observation,
    ensure_ascii=False,
    indent=2,
)
```

这段 JSON 会作为：

```python
{"role": "tool", "content": "...JSON..."}
```

追加回 `current_messages`。

然后下一轮：

```python
provider.generate(...)
```

模型就能看到这个工具结果。

## 6. 为什么 JSON observation 更好

松散文本的问题是：

```text
每个工具结果可能格式不同。
模型要自己猜哪一行是工具名、哪一行是结果。
前端也不方便解析。
audit 更难做结构化记录。
```

JSON observation 的好处是：

```text
字段固定
工具名固定在 tool_name
是否成功固定在 ok
返回内容固定在 content
额外信息固定在 metadata
```

例如：

```json
{
  "type": "tool_result",
  "tool_name": "todo_write",
  "tool_input": {
    "items": [
      {
        "content": "Make tool result structured",
        "status": "completed"
      }
    ]
  },
  "ok": true,
  "content": "Updated todo list...",
  "metadata": {
    "path": "D:\\16604\\.mini_claude\\todos.json",
    "count": 1
  }
}
```

这更接近 Harness 的 observation 思想：

```text
工具执行后，给模型一个清晰、稳定、可读取的观察结果。
```

## 7. ToolExecutor：结构化错误

修改文件：

```text
backend/app/tools/executor.py
```

以前 `ToolExecutor` 的错误比较简单：

```python
return ToolResult(ok=False, content=f"Unknown tool: {tool_name}")
```

现在增加了结构化 `metadata.error_type`。

目前有三类：

```text
invalid_tool_input
unknown_tool
tool_exception
```

## 8. invalid_tool_input

代码逻辑：

```python
if not isinstance(input_data, dict):
    return ToolResult(
        ok=False,
        content="Tool input must be an object.",
        metadata={
            "error_type": "invalid_tool_input",
            "tool_name": tool_name,
            "input_type": type(input_data).__name__,
        },
    )
```

它表示：

```text
模型传给工具的 input_data 不是字典。
```

工具统一要求：

```python
invoke(input_data: dict)
```

所以如果模型传的是字符串、列表、数字，就拒绝。

## 9. unknown_tool

代码逻辑：

```python
tool = self.registry.get(tool_name)
if tool is None:
    return ToolResult(
        ok=False,
        content=f"Unknown tool: {tool_name}",
        metadata={
            "error_type": "unknown_tool",
            "tool_name": tool_name,
        },
    )
```

它表示：

```text
模型请求了一个不存在的工具。
```

比如：

```text
delete_everything
```

如果这个工具没有注册，后端不会执行任何动作，只返回错误。

## 10. tool_exception

代码逻辑：

```python
try:
    return tool.invoke(input_data)
except Exception as exc:
    return ToolResult(
        ok=False,
        content=str(exc),
        metadata={
            "error_type": "tool_exception",
            "tool_name": tool_name,
            "exception_type": exc.__class__.__name__,
        },
    )
```

它表示：

```text
工具内部执行时抛异常。
```

注意：

```text
工具异常不会让整个 AgentLoop 崩溃。
```

而是被包装成 `ToolResult(ok=False)`。

然后这个错误会被 `_format_tool_result()` 转成 JSON observation，再回传给模型。

模型可以根据失败原因继续调整下一步。

## 11. 这一章目前的验证

已经验证：

```text
compileall 通过
todo_write 工具调用通过
tool_traces 能记录工具调用
JSON observation 能正确生成
unknown_tool 测试通过
invalid_tool_input 测试通过
```

## 12. 第五章目前总结

第五章目前把工具调用从：

```text
模型请求工具 -> 后端执行工具 -> 返回一段文本
```

推进到了：

```text
模型请求工具
-> ToolExecutor 执行并分类错误
-> AgentLoop 保存 ToolTrace
-> AgentLoop 生成 JSON observation
-> 模型读取结构化工具结果继续行动
```

一句话：

```text
Tool Calling 不只是“调用函数”，而是一套可记录、可解释、可恢复的 Harness 执行链路。
```
