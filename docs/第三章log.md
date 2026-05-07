# 第三章 log：System Prompt

## 1. 这一章学什么

第三章的主题是：

```text
System Prompt
```

它解决的问题是：

```text
模型为什么知道自己是一个 coding agent？
模型为什么知道要先读文件再改文件？
模型为什么知道工具失败后可以继续调整？
模型为什么知道要结合 project / skill / knowledge？
```

这些不是模型天生知道的。

后端需要把这些规则组织进 `system` 消息里。

## 2. System Prompt 在消息结构里的位置

模型调用一般会收到这样的 messages：

```python
messages = [
    {"role": "system", "content": "...系统规则..."},
    {"role": "user", "content": "...用户问题..."},
]
```

多轮对话时会变成：

```python
messages = [
    {"role": "system", "content": "...系统规则..."},
    {"role": "user", "content": "上一轮用户问题"},
    {"role": "assistant", "content": "上一轮模型回答"},
    {"role": "user", "content": "当前用户问题"},
]
```

其中：

```text
system：告诉模型身份、边界、规则
user：用户真正提出的问题
assistant：历史中的模型回答
tool：工具执行结果
```

你可以把 system prompt 理解成：

```text
这一轮模型思考前，必须先读的说明书。
```

## 3. 为什么要单独建 prompts/system_prompt.py

之前我们的 `context_builder.py` 里直接写了 system prompt：

```python
system_parts = [
    "你是 Simple Claude Code Framework 的通用 AI agent。",
    "...",
]
```

这能跑，但职责混在一起：

```text
context_builder 既负责拼 messages
又负责写 prompt 文案
```

第三章我们把它拆开：

```text
prompts/system_prompt.py
负责定义 system prompt

gateway/context_builder.py
负责把 system prompt、历史消息、用户问题、知识库片段拼成 messages
```

这样更接近 Claude Code-like 的结构：

```text
prompt 是行为规则层
context_builder 是上下文组装层
gateway 是总调度层
agent loop 是工具循环层
model provider 是模型接口层
```

## 4. 新增文件：prompts/__init__.py

文件位置：

```text
backend/app/prompts/__init__.py
```

内容：

```python
"""Prompt package for the mini Claude Code-like framework."""
```

这个文件的作用是：

```text
告诉 Python：prompts 是一个包。
```

有了它，我们可以写：

```python
from app.prompts.system_prompt import build_system_prompt
```

## 5. 新增文件：prompts/system_prompt.py

文件位置：

```text
backend/app/prompts/system_prompt.py
```

它现在包含五个核心部分：

```text
BASE_AGENT_PROMPT
WORK_RULES_PROMPT
TOOL_RULES_PROMPT
build_project_prompt()
build_skill_prompt()
build_system_prompt()
```

下面逐个拆。

## 6. BASE_AGENT_PROMPT

代码：

```python
BASE_AGENT_PROMPT = """你是 Mini Claude Code Framework 的 AI 编程助手。

你的定位：
- 你运行在一个本地项目工作台里。
- 你可以根据会话历史、项目说明、知识库片段和工具结果协助用户。
- 你优先给出清晰、稳妥、可执行的回答。
- 你不是单纯聊天机器人，而是一个能理解项目上下文的 agent。
"""
```

这段负责定义模型身份。

重点是最后一句：

```text
你不是单纯聊天机器人，而是一个能理解项目上下文的 agent。
```

这句话把普通聊天和 Claude Code-like agent 区分开：

```text
普通聊天：用户问什么，模型直接答什么
agent：用户问什么，模型要考虑项目、文件、知识、工具、历史
```

## 7. WORK_RULES_PROMPT

代码：

```python
WORK_RULES_PROMPT = """工作规则：
- 先理解用户目标，再决定是否需要工具。
- 能用简单方案解决时，不要引入复杂方案。
- 如果信息不足，先说明缺口，再给出下一步建议。
- 修改代码前，应先读取相关文件并理解上下文。
- 回答尽量使用中文，除非代码、命令或专有名词需要保留英文。
"""
```

这段负责约束工作方式。

它和我们项目的 MVP 原则一致：

```text
先跑通
再优化
简单稳定优先
```

其中最重要的是：

```text
修改代码前，应先读取相关文件并理解上下文。
```

这句话和第二章的 `read-before-edit + mtime 检查` 是配套的。

区别是：

```text
system prompt：告诉模型应该先读再改
tool guard：如果模型没先读，后端直接拒绝改
```

这就是 agent 系统里的“双保险”。

## 8. TOOL_RULES_PROMPT

代码：

```python
TOOL_RULES_PROMPT = """工具规则：
- read_file 用于读取文件内容，读取结果会包含文件的 mtime_ns。
- edit_file 用于精确替换文件内容，必须基于 read_file 返回的 mtime_ns 进行编辑。
- search_files 用于按文件名或路径搜索文件。
- search_content 用于在文本文件中搜索内容。
- write_file 用于创建或覆盖文本文件，覆盖已有文件时要谨慎。
- run_command 只能运行后端允许的安全命令。
- 工具失败不是系统崩溃，而是一次反馈；你可以根据失败原因调整下一步。
"""
```

这段告诉模型：

```text
有哪些工具
每个工具大概干什么
工具调用失败时该怎么办
```

真实模型 provider 后面会把工具 schema 单独传给模型。

但 system prompt 里仍然写工具规则是有价值的，因为：

```text
schema 告诉模型工具参数长什么样
system prompt 告诉模型什么时候该用、怎么谨慎地用
```

## 9. build_project_prompt(project)

代码：

```python
def build_project_prompt(project: Project | None) -> str:
    """Build the project-specific part of the system prompt."""
    if project is None:
        return "当前项目：无\n项目说明：无\n项目自定义指令：无"

    return "\n".join(
        [
            f"当前项目：{project.name}",
            f"项目说明：{project.description or '无'}",
            f"项目自定义指令：{project.system_instruction or '无'}",
        ]
    )
```

这个函数负责把项目对象转成 prompt 文本。

参数：

```python
project: Project | None
```

意思是：

```text
project 要么是一个 Project 对象
要么是 None
```

为什么允许 None？

因为第一版里用户可能还没有选择项目。

如果没有项目，就返回：

```text
当前项目：无
项目说明：无
项目自定义指令：无
```

如果有项目，就把数据库里的项目字段拼进去。

## 10. build_skill_prompt(skill)

代码：

```python
def build_skill_prompt(skill: Skill) -> str:
    """Build the skill-specific part of the system prompt."""
    return "\n".join(
        [
            f"当前 skill：{skill.name}",
            f"skill 说明：{skill.description}",
            f"skill 指令：{skill.system_prompt}",
        ]
    )
```

这个函数负责把 skill 转成 prompt 文本。

这里要区分：

```text
system prompt：平台的总规则
skill prompt：某个模式/能力的局部规则
```

例如：

```text
通用 Agent
课程复习 Skill
文档总结 Skill
代码讲解 Skill
```

它们不应该替代基础 system prompt，而应该叠加在基础 system prompt 后面。

## 11. build_system_prompt(...)

代码：

```python
def build_system_prompt(*, skill: Skill, project: Project | None = None) -> str:
    """Build the full system prompt used by the model for one turn."""
    return "\n\n".join(
        [
            BASE_AGENT_PROMPT.strip(),
            WORK_RULES_PROMPT.strip(),
            TOOL_RULES_PROMPT.strip(),
            build_project_prompt(project),
            build_skill_prompt(skill),
        ]
    )
```

这是本章最核心的函数。

它把五块内容合成一个完整 system prompt：

```text
基础身份
工作规则
工具规则
项目指令
skill 指令
```

这里用：

```python
"\n\n".join([...])
```

意思是：

```text
用两个换行把每一大段连接起来。
```

这样模型看到的 prompt 更清楚。

这里还用了：

```python
BASE_AGENT_PROMPT.strip()
```

`strip()` 的作用是：

```text
去掉字符串开头和结尾多余的空白或换行。
```

## 12. 修改文件：gateway/context_builder.py

修改前：

```python
system_parts = [
    "你是 Simple Claude Code Framework 的通用 AI agent。",
    "...",
]
```

修改后：

```python
from app.prompts.system_prompt import build_system_prompt
```

然后：

```python
messages: list[dict[str, str]] = [
    {"role": "system", "content": build_system_prompt(skill=skill, project=project)}
]
```

这表示：

```text
context_builder 不再自己维护 prompt 文案。
它只调用 build_system_prompt() 拿到完整 system 内容。
```

职责更清楚。

## 13. 当前调用链

第三章完成后，消息构造链路是：

```text
gateway.run_gateway_turn()
-> build_messages()
-> build_system_prompt()
-> BASE_AGENT_PROMPT + WORK_RULES_PROMPT + TOOL_RULES_PROMPT
-> project prompt
-> skill prompt
-> messages[0] = system
-> messages[-1] = user
-> AgentLoop
-> ModelProvider
```

你要记住这条主线：

```text
模型不是直接收到用户问题。
模型收到的是：系统规则 + 历史上下文 + 用户问题 + 知识片段。
```

## 14. 第三章和前两章的关系

第一章：

```text
Agent Loop
负责多步循环：模型回复 -> 工具调用 -> 工具结果 -> 再问模型
```

第二章：

```text
Tools
负责给 agent 提供可执行能力，并做安全防护
```

第三章：

```text
System Prompt
负责告诉模型如何扮演这个 agent、什么时候用工具、怎么谨慎工作
```

三者合起来就是：

```text
System Prompt 规定行为
Agent Loop 组织过程
Tools 执行动作
```

这就是 mini Claude Code 的最小核心。
