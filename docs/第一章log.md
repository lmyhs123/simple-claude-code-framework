# Chapter 01 Agent Loop 学习与开发日志

记录日期：2026-05-07  
项目路径：`D:\16604\course-ai-assistant`  
项目目标：按 `claude-code-from-scratch` 的思路，逐步实现一个 `mini Claude Code-like` 框架。

## 0. 当前结论

按我们当前“边学边实现”的标准，教程第 1 章 `Agent Loop` 已经完成了一个 MVP 版。

现在项目已经具备：

- `Gateway` 负责准备上下文。
- `AgentLoop` 负责驱动模型回合。
- `ModelProvider` 不再只返回字符串，而是返回结构化 `ModelResponse`。
- `ModelResponse` 可以表达最终文本，也可以表达工具调用请求。
- `ToolRegistry` 保存可用工具。
- `ToolExecutor` 执行工具。
- `AgentLoop` 可以执行工具，把工具结果追加回 `messages`。
- `AgentLoop` 可以最多循环 `settings.max_agent_steps` 次，避免无限循环。

当前仍然是教学版和骨架版，不是完整 Claude Code：

- 真实模型 API 还没有接入。
- 真实工具大多还是占位。
- 还没有复杂 tool schema 转换。
- 还没有 streaming。
- 还没有完整 audit / artifact。

## 1. 我们为什么从 Agent Loop 开始

一开始我们的项目更像一个 Web AI 助手框架：

```text
/api/chat
-> chat_service
-> gateway
-> model_provider
```

但参考教程的第一章核心不是数据库，也不是前端，而是：

```text
LLM -> tool call -> execute tool -> append result -> LLM -> final answer
```

所以我们把学习顺序调整为：

```text
先理解 Agent Loop
再理解工具系统
再扩展模型 provider
再补真实工具和真实模型
```

这个顺序更贴近 Claude Code 的核心：它不是普通聊天机器人，而是可以“思考、调用工具、继续思考”的 agent。

## 2. 当前核心文件

本章主要围绕这些文件学习和开发：

```text
backend/app/agent/loop.py
backend/app/gateway/gateway.py
backend/app/model_providers/base.py
backend/app/model_providers/mock_provider.py
backend/app/tools/base.py
backend/app/tools/registry.py
backend/app/tools/executor.py
backend/app/tools/builtin_tools.py
backend/app/core/config.py
```

每个文件的角色：

```text
loop.py
Agent Loop 主循环，负责驱动模型和工具调用。

gateway.py
总调度层，负责准备 project、history、knowledge、skill、tools、provider。

model_providers/base.py
定义模型 provider 的统一接口，以及 ModelResponse / ToolCall。

mock_provider.py
假模型，用来在没有真实 API 时验证主链路。

tools/base.py
定义工具的统一形状：ToolDefinition、ToolResult、Tool。

tools/registry.py
工具注册表，负责保存工具名到工具对象的映射。

tools/executor.py
工具执行器，通过 registry 找工具并调用 invoke。

tools/builtin_tools.py
内置工具集合，目前 read_file 可用，其余工具仍是占位。

core/config.py
配置中心，本章新增 max_agent_steps，用来限制 Agent Loop 最大步数。
```

## 3. 第一次重构：让 loop 接管模型调用

最开始的结构是：

```text
gateway -> provider.generate(...)
gateway -> loop.run(final_text)
```

这个结构的问题是：`AgentLoop` 只是包装最终文本，并没有真正驱动模型。

我们改成：

```text
gateway -> loop.run(messages, provider, skill)
loop -> provider.generate(...)
```

这样分工更清晰：

```text
gateway 负责准备材料
loop 负责驱动模型回合
```

对应代码在 `backend/app/gateway/gateway.py`：

```python
provider = get_model_provider()
loop = AgentLoop(tool_registry)
result = loop.run(messages=messages, provider=provider, skill=skill)
return result.final_text
```

对应代码在 `backend/app/agent/loop.py`：

```python
response = provider.generate(messages=messages, skill=skill)
```

这一点很重要，因为后面所有 tool call 循环都应该由 `AgentLoop` 管，而不是散落在 `gateway.py`。

## 4. 第二次重构：模型返回结构化结果

原来模型接口是：

```python
def generate(...) -> str
```

这只能表示：

```text
模型直接给出最终文本
```

但 Claude Code-like agent 需要模型可以表达：

```text
我要调用工具
```

所以我们在 `backend/app/model_providers/base.py` 新增：

```python
@dataclass(frozen=True)
class ToolCall:
    name: str
    input_data: dict[str, Any]


@dataclass(frozen=True)
class ModelResponse:
    text: str | None = None
    tool_call: ToolCall | None = None

    @property
    def wants_tool(self) -> bool:
        return self.tool_call is not None
```

现在 provider 返回：

```python
ModelResponse(text="最终回答")
```

或者：

```python
ModelResponse(
    tool_call=ToolCall(
        name="read_file",
        input_data={"path": "xxx.py"},
    )
)
```

这一步的核心理解：

```text
ModelProvider 不再只是返回一句话。
它返回的是“模型下一步想做什么”。
```

## 5. 第三步：理解 tools/base.py

`tools/base.py` 定义工具系统最底层的三个概念：

```python
ToolDefinition
ToolResult
Tool
```

### ToolDefinition

它是“工具对模型的说明书”：

```python
name: str
description: str
input_schema: dict[str, Any]
```

模型不知道 Python 类和函数是什么，所以必须通过 `ToolDefinition` 告诉模型：

```text
这里有一个工具，名字叫 read_file。
它可以读取文本文件。
调用它需要 path 参数。
```

### ToolResult

它是工具执行结果的统一格式：

```python
ok: bool
content: str
metadata: dict[str, Any] | None = None
```

统一格式的好处是：`AgentLoop` 不需要知道每个工具自己的返回习惯，只需要看：

```text
成功了吗？
结果文本是什么？
有没有额外信息？
```

### Tool Protocol

一个对象只要有：

```python
definition: ToolDefinition
invoke(input_data) -> ToolResult
```

就可以被当作工具。

## 6. 第四步：理解 ToolRegistry 和 ToolExecutor

`ToolRegistry` 是工具目录：

```text
工具名 -> 工具对象
```

例如：

```python
{
    "read_file": ReadFileTool(),
    "write_file": WriteFileTool(),
}
```

它负责：

- 注册工具。
- 防止重复工具名。
- 根据工具名查找工具。
- 列出工具定义，后续可以给模型看。

`ToolExecutor` 是执行器：

```python
tool = registry.get(tool_name)
return tool.invoke(input_data)
```

它负责：

- 找工具。
- 调用工具。
- 捕获异常。
- 返回统一 `ToolResult`。

这两个类让 `AgentLoop` 不必直接关心每个工具怎么实现。

## 7. 第五步：执行一次工具调用

在 `mock_provider.py` 里，我们先加了一个教学触发器：

```text
mock_tool_read: <path>
```

当用户输入包含这个内容时，mock provider 返回：

```python
ModelResponse(
    tool_call=ToolCall(
        name="read_file",
        input_data={"path": path},
    )
)
```

然后 `AgentLoop` 判断：

```python
if response.wants_tool:
    ...
```

并执行：

```python
tool_result = self.tool_executor.execute(
    tool_name=response.tool_call.name,
    input_data=response.tool_call.input_data,
)
```

这一步跑通了：

```text
模型请求工具
-> AgentLoop 识别 tool_call
-> ToolExecutor 执行 read_file
-> 返回 ToolResult
```

## 8. 第六步：工具结果回填 messages

只执行工具还不够。

真正的 Claude Code-like loop 需要：

```text
工具执行结果 -> 放回上下文 -> 模型继续生成最终回答
```

所以我们构造了新的 message：

```python
{
    "role": "tool",
    "content": self._format_tool_result(response, tool_result),
}
```

再追加到 `messages`：

```python
current_messages.append(...)
```

这一步的意义：

```text
模型第二次调用时，可以看到工具执行结果。
```

## 9. 第七步：bounded loop

如果模型一直请求工具，程序不能无限循环。

所以我们在 `core/config.py` 加了：

```python
max_agent_steps: int = 5
```

然后在 `AgentLoop.run()` 中使用：

```python
for _step in range(settings.max_agent_steps):
    response = provider.generate(messages=current_messages, skill=skill)
    ...
```

这就是 bounded loop：

```text
有边界的 agent 循环
```

当前完整流程是：

```text
准备 messages
-> provider.generate(...)
-> 如果返回 text，结束
-> 如果返回 tool_call，执行工具
-> 把 ToolResult 追加成 tool message
-> 下一轮 provider.generate(...)
-> 最多重复 max_agent_steps 次
```

## 10. 当前 Agent Loop 的最终形态

当前最核心代码在 `backend/app/agent/loop.py`：

```python
current_messages = list(messages)
tool_results: list[ToolResult] = []

for _step in range(settings.max_agent_steps):
    response = provider.generate(messages=current_messages, skill=skill)
    if not response.wants_tool:
        final_text = self._final_text_from_response(response)
        return AgentLoopResult(
            final_text=final_text,
            tool_results=tool_results,
        )

    tool_result = self.tool_executor.execute(...)
    tool_results.append(tool_result)

    current_messages.append({
        "role": "tool",
        "content": self._format_tool_result(response, tool_result),
    })
```

一句话理解：

```text
每一轮都问模型：你要最终回答，还是要调用工具？
如果要工具，就执行工具，把结果放回上下文，然后进入下一轮。
```

## 11. 我们特别约定过的注释规则

开发过程中出现过一次问题：我曾经为了清理乱码，直接重写文件，导致你的学习注释被删掉。

后来我们明确约定：

```text
可以改代码。
可以改注释。
可以整理注释。
不能直接整批删除你的学习注释。
```

后续规则：

- 短解释用 `#`。
- 类和函数的正式说明用 docstring。
- 不建议用三引号字符串当普通注释。
- 如果注释乱码，只整理成正常中文，不删除原本学习意图。

## 12. 当前验证过的行为

普通聊天测试：

```text
POST /api/chat -> 200
```

工具调用测试：

```text
mock_tool_read: D:/16604/course-ai-assistant/backend/app/tools/base.py
```

验证结果：

```text
mock provider 返回 ToolCall(read_file)
AgentLoop 执行 read_file
ToolResult 被追加成 tool message
mock provider 第二次基于 tool message 返回最终回答
```

这说明：

```text
LLM -> tool call -> execute -> append result -> LLM final answer
```

这个最小闭环已经跑通。

## 13. 当前仍然存在的问题

### 1. GitHub 尚未同步

本地有未提交改动，GitHub 上还是旧版本。

当前需要后续执行：

```powershell
cd D:\16604\course-ai-assistant
git status
git add .
git commit -m "complete chapter 01 agent loop skeleton"
git push origin main
```

### 2. 终端中文显示乱码

PowerShell `Get-Content` 有时显示中文注释乱码。

但 Python 按 UTF-8 读取时，文件内容通常正常：

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "from pathlib import Path; print(Path('xxx.py').read_text(encoding='utf-8'))"
```

### 3. 真实模型还没接

当前 provider 是：

```text
MockModelProvider
```

还不是 OpenAI / Claude / DeepSeek。

### 4. 真实工具还没补完

目前：

```text
read_file 可用
write_file 占位
edit_file 占位
search_files 占位
search_content 占位
run_command 占位
```

## 14. 下一章建议

教程第 1 章 Agent Loop 到这里可以先收束。

下一步建议进入工具实现，优先顺序：

```text
1. search_files
2. search_content
3. read_file 安全限制
4. write_file
5. edit_file
6. run_command
```

原因：

```text
Claude Code-like agent 最小代码理解能力 =
找文件 + 搜内容 + 读文件
```

先把这三个补起来，agent 才能开始“理解项目”。

## 15. 一句话复盘

本章我们从普通聊天式调用，推进到了最小 Claude Code-like Agent Loop：

```text
gateway 准备上下文
-> AgentLoop 调模型
-> 模型返回 text 或 tool_call
-> ToolExecutor 执行工具
-> 工具结果回填 messages
-> AgentLoop 最多循环 N 步
-> 返回最终回答和工具过程结果
```

这就是 mini Claude Code 的第一块地基。
