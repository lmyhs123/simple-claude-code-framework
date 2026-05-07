# 第二章 Tools 工具系统学习与开发日志

记录日期：2026-05-07  
项目路径：`D:\16604\course-ai-assistant`  
章节主题：让 mini Claude Code 具备最小工具能力。

## 0. 当前结论

第二章目前已经完成一个 MVP 版工具系统。

现在项目具备 6 个核心工具：

```text
read_file
search_files
search_content
write_file
edit_file
run_command
```

其中：

```text
read_file：已实现，支持按行读取。
search_files：已实现，支持按文件名/路径搜索。
search_content：已实现，支持搜索文本内容并返回 文件:行号:内容。
write_file：已实现保守版，默认不覆盖已有文件。
edit_file：已实现保守版，只允许 old_text -> new_text 精准替换。
run_command：已实现白名单版，只允许少数安全命令。
```

这一章的重点不是“立刻完全理解每个工具的内部源码”，而是先理解：

```text
Agent 为什么需要工具
每个工具负责什么
工具为什么要有安全边界
工具结果如何进入 AgentLoop
```

## 1. 为什么第二章做工具系统

第一章完成的是 Agent Loop：

```text
模型 -> 工具调用 -> 执行工具 -> 工具结果回填 -> 模型继续回答
```

但如果没有真实工具，Agent Loop 只能空转。

Claude Code-like agent 的核心能力不是“聊天”，而是能操作项目：

```text
找文件
搜代码
读文件
写文件
改文件
运行安全命令
```

所以第二章开始补工具系统。

## 2. 工具系统涉及的核心文件

本章主要改动和学习这些文件：

```text
backend/app/tools/base.py
backend/app/tools/registry.py
backend/app/tools/executor.py
backend/app/tools/builtin_tools.py
backend/app/model_providers/mock_provider.py
backend/app/core/config.py
backend/.env.example
```

各自职责：

```text
tools/base.py
定义工具的基本形状：ToolDefinition、ToolResult、Tool。

tools/registry.py
保存工具名到工具对象的映射。

tools/executor.py
根据 tool_name 找工具并执行。

tools/builtin_tools.py
实现内置工具。

mock_provider.py
提供教学触发词，比如 mock_tool_read、mock_tool_write。

core/config.py
增加 workspace 和工具安全相关配置。
```

## 3. 工具的基础抽象

工具系统底层有三个概念：

```text
ToolDefinition
ToolResult
Tool
```

### ToolDefinition

它是工具对模型的说明书。

包含：

```text
name：工具名
description：工具说明
input_schema：工具输入格式
```

模型不知道 Python 函数怎么写，所以我们必须告诉模型：

```text
这里有一个 read_file 工具。
它可以读取文件。
调用它需要 path。
```

### ToolResult

它是所有工具统一返回格式。

包含：

```text
ok：是否成功
content：结果文本
metadata：额外信息
```

统一格式的好处是：AgentLoop 不需要关心每个工具内部怎么返回，只需要统一处理 ToolResult。

### Tool

一个工具只需要满足：

```text
有 definition
有 invoke(input_data)
```

就可以被注册和执行。

## 4. workspace 安全边界

这一章最重要的安全改动是：工具只能访问 workspace 内路径。

新增配置：

```python
workspace_root: str = ".."
max_tool_file_size: int = 1_000_000
```

对应 `.env.example`：

```env
WORKSPACE_ROOT=".."
MAX_TOOL_FILE_SIZE=1000000
```

由于后端通常从：

```text
D:\16604\course-ai-assistant\backend
```

启动，所以：

```text
WORKSPACE_ROOT=".."
```

指向：

```text
D:\16604\course-ai-assistant
```

工具处理路径时，会做：

```text
输入 path/root
-> 转成绝对路径
-> 判断是否在 workspace 内
-> 不在 workspace 内就拒绝
```

测试过：

```text
backend/app/tools/base.py：允许
C:/Windows/win.ini：拒绝
```

这一步非常重要，因为 agent 工具越强，越需要边界。

## 5. read_file

用途：

```text
读取一个文本文件。
```

后来增强为：

```text
支持 start_line / end_line
返回内容带行号
默认最多读取 300 行
```

示例输入：

```json
{
  "path": "backend/app/tools/base.py",
  "start_line": 1,
  "end_line": 8
}
```

示例输出：

```text
1: from dataclasses import dataclass
2: from typing import Any, Protocol
3:
4: # dataclass：用来定义简单数据对象，比如工具定义、工具结果。
```

为什么要支持行范围：

```text
代码文件可能很大。
Agent 不应该每次读取整个文件。
更好的流程是：先 search_content 找位置，再 read_file 读取附近片段。
```

## 6. search_files

用途：

```text
按文件名或路径片段搜索文件。
```

示例：

```text
query = "loop.py"
```

结果：

```text
backend\app\agent\loop.py
```

它会忽略：

```text
.git
.venv
__pycache__
node_modules
dist
data
uploads
```

为什么先做它：

```text
Agent 想理解项目，第一步通常是先找到可能相关的文件。
```

## 7. search_content

用途：

```text
在项目文本文件里搜索内容。
```

返回格式：

```text
文件路径:行号:匹配行内容
```

示例：

```text
search_content: AgentLoop
```

可能返回：

```text
docs\第一章log.md:14: - `AgentLoop` 负责驱动模型回合。
```

为什么重要：

```text
Agent 经常不知道某个函数在哪。
search_content 可以帮它先定位，再用 read_file 读上下文。
```

## 8. write_file

用途：

```text
写入一个文本文件。
```

实现策略非常保守：

```text
只能写 workspace 内文件
只允许写支持的文本文件
内容不能超过 max_tool_file_size
默认不覆盖已有文件
必须 overwrite=true 才允许覆盖
自动创建父目录
```

为什么默认不覆盖：

```text
写文件是危险动作。
第一版宁可麻烦一点，也不要让 agent 误覆盖已有文件。
```

测试过：

```text
写 workspace 内新文件：成功
再次写同一个文件且 overwrite=false：拒绝
写 C:/Windows：拒绝
```

## 9. edit_file

用途：

```text
编辑已有文本文件。
```

第一版采用最简单可靠的方式：

```text
old_text -> new_text
```

输入：

```json
{
  "path": "backend/data/example.md",
  "old_text": "旧文本",
  "new_text": "新文本"
}
```

安全规则：

```text
old_text 必须存在
old_text 必须只出现一次
出现 0 次：拒绝
出现多次：拒绝
```

为什么这样设计：

```text
如果一个文件里有多个相同片段，agent 不一定知道该改哪个。
第一版拒绝模糊编辑，避免误改。
```

测试过：

```text
alpha
beta
gamma
```

替换：

```text
beta -> BETA
```

结果：

```text
alpha
BETA
gamma
```

## 10. run_command

用途：

```text
执行命令。
```

但这是最危险的工具，所以第一版只做白名单。

允许命令：

```text
git status
git --version
python --version
node --version
npm --version
```

安全策略：

```text
shell=False
命令必须完整匹配白名单
cwd 必须在 workspace 内
超时时间 10 秒
返回 stdout / stderr / returncode
```

测试过：

```text
git status：允许
dir：拒绝
cwd=C:/Windows：拒绝
```

为什么不开放任意命令：

```text
任意 shell 命令可以删除文件、改系统、泄露信息。
Claude Code-like 框架后续可以增强命令工具，但第一版必须先有边界。
```

## 11. mock provider 的教学触发词

因为现在还没接真实模型，所以我们用 mock provider 做教学触发。

当前触发词：

```text
mock_tool_read: <path>
mock_tool_search_files: <query>
mock_tool_search_content: <query>
mock_tool_write: <path>
<content>
mock_tool_edit: <path>
---
<old_text>
---
<new_text>
mock_tool_run: <command>
```

这些触发词只是教学用。

真实模型接入后，不会靠字符串触发，而是模型 API 返回真正的 tool call。

## 12. 当前工具链完整流程

以 `search_content` 为例：

```text
用户输入 mock_tool_search_content: AgentLoop
-> mock_provider 返回 ToolCall(name="search_content")
-> AgentLoop 发现 response.wants_tool
-> ToolExecutor 执行 search_content
-> search_content 返回 ToolResult
-> AgentLoop 把 ToolResult 追加成 tool message
-> mock_provider 第二次生成最终回答
```

也就是：

```text
模型意图
-> 工具执行
-> 工具结果
-> 回填上下文
-> 最终回答
```

## 13. 现在可以先不深挖实现细节

我们讨论过一个学习策略：

```text
你现在已经能明白这些工具是做什么的。
但还不完全懂内部怎么实现。
```

这是可以接受的。

当前阶段更重要的是先建立整体地图：

```text
AgentLoop 怎么驱动工具
工具有哪些
每个工具负责什么
工具为什么要有安全边界
工具结果怎么回到模型
```

内部细节可以后面按需回头拆：

```text
路径解析
文件遍历
文本搜索
精确替换
subprocess 安全执行
```

## 14. 第二章当前结论

第二章已经让 mini Claude Code 拥有了最小工具能力。

现在 agent 已经可以：

```text
找文件
搜内容
读文件片段
写新文件
精准替换文本
运行安全命令
```

这意味着项目已经从：

```text
会聊天的 Web AI 框架
```

进一步接近：

```text
能操作项目文件的 mini Claude Code 框架
```

## 15. 下一步建议

下一步建议不要马上继续堆工具，而是进入：

```text
真实 model provider
```

原因：

```text
现在 mock provider 只是用字符串触发工具。
真正的 Claude Code-like 行为，需要真实模型根据上下文自己决定是否调用工具。
```

建议下一章：

```text
第三章：Model Provider
```

目标：

```text
1. 理解 provider.generate(...) 怎么接真实模型。
2. 新增 OpenAI-compatible provider 或 DeepSeek provider。
3. 把真实模型返回转成 ModelResponse。
4. 后续再接真实 tool call 格式。
```

如果暂时没有 API key，也可以先做 provider 文件结构和配置，不急着真实联网。

## 16. 工具内部实现自学笔记

这一节是以后自学源码时看的。现在不要求一次全部吃透，但可以作为回头拆代码的地图。

核心源码在：

```text
backend/app/tools/builtin_tools.py
```

### 16.1 顶部常量

```python
IGNORED_DIRS = {...}
TEXT_EXTENSIONS = {...}
DEFAULT_MAX_RESULTS = 20
DEFAULT_MAX_READ_LINES = 300
COMMAND_TIMEOUT_SECONDS = 10
ALLOWED_COMMANDS = {...}
```

这些常量的作用：

```text
IGNORED_DIRS
搜索文件时跳过不该扫描的目录，比如 .git、node_modules、__pycache__。

TEXT_EXTENSIONS
定义哪些后缀算“可读文本文件”。

DEFAULT_MAX_RESULTS
搜索工具默认最多返回多少条。

DEFAULT_MAX_READ_LINES
read_file 默认最多读多少行。

COMMAND_TIMEOUT_SECONDS
命令执行最多等待多少秒。

ALLOWED_COMMANDS
run_command 的白名单。
```

这里体现了一个重要思想：

```text
工具不应该无限制工作。
搜索要有限制，读取要有限制，命令也要有限制。
```

### 16.2 路径解析：_resolve_workspace_path

```python
def _resolve_workspace_path(raw_path: str | None) -> Path:
    workspace = settings.workspace_path
    path_value = raw_path if isinstance(raw_path, str) and raw_path.strip() else "."
    path = Path(path_value)
    if not path.is_absolute():
        path = workspace / path
    return path.resolve()
```

它做了几件事：

```text
1. 读取 workspace 根目录。
2. 如果用户没传路径，就默认 "."。
3. 把字符串变成 Path 对象。
4. 如果是相对路径，就拼到 workspace 下面。
5. resolve() 得到最终绝对路径。
```

比如：

```text
backend/app/tools/base.py
```

会变成：

```text
D:\16604\course-ai-assistant\backend\app\tools\base.py
```

为什么要这样做：

```text
工具内部不能直接相信用户传进来的路径。
必须先规范化路径，后面才能判断它是否安全。
```

### 16.3 安全判断：_is_inside_workspace

```python
def _is_inside_workspace(path: Path) -> bool:
    try:
        path.relative_to(settings.workspace_path)
    except ValueError:
        return False
    return True
```

核心逻辑：

```text
如果 path 可以相对于 workspace_path 表示，
说明它在 workspace 里面。
否则 relative_to 会抛 ValueError。
```

例如：

```text
D:\16604\course-ai-assistant\backend\app\tools\base.py
```

在 workspace 内，允许。

```text
C:\Windows\win.ini
```

不在 workspace 内，拒绝。

这是文件工具最重要的安全边界。

### 16.4 搜索根目录：_get_root

```python
def _get_root(input_data: dict) -> tuple[Path | None, str | None]:
    root = _resolve_workspace_path(input_data.get("root"))
    if not _is_inside_workspace(root):
        return None, f"Path is outside workspace: {root}"
    return root, None
```

它专门给搜索工具用。

返回的是：

```text
(root, error)
```

如果安全：

```text
(Path(...), None)
```

如果不安全：

```text
(None, "Path is outside workspace...")
```

为什么不用直接抛异常：

```text
工具层更适合返回 ToolResult，而不是让异常一路炸到 AgentLoop。
```

### 16.5 限制搜索数量：_get_max_results

```python
def _get_max_results(input_data: dict) -> int:
    raw_value = input_data.get("max_results", DEFAULT_MAX_RESULTS)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = DEFAULT_MAX_RESULTS
    return max(1, min(value, 100))
```

它处理：

```text
用户没传 max_results
用户传了奇怪的值
用户传了过大的值
```

最终结果限制在：

```text
1 到 100
```

这样做是为了避免一次搜索返回太多内容，把模型上下文撑爆。

### 16.6 行号解析：_get_optional_line_number

```python
def _get_optional_line_number(input_data: dict, key: str) -> int | None:
    raw_value = input_data.get(key)
    if raw_value is None or raw_value == "":
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return max(1, value)
```

它用于：

```text
start_line
end_line
```

返回：

```text
有效数字 -> int
没传或非法 -> None
```

这样 `read_file` 可以优雅处理：

```text
只传 start_line
只传 end_line
两个都不传
传了非法值
```

### 16.7 遍历项目文件：_iter_project_files

```python
def _iter_project_files(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path
```

它做的是递归遍历：

```text
从 root 开始找所有文件
跳过 IGNORED_DIRS
只返回文件，不返回目录
```

这里用了 `yield`。

你可以把 `yield` 理解成：

```text
一边找，一边吐出结果。
```

好处是：

```text
不用一次性把所有文件都放进列表。
搜索到足够结果后可以提前停止。
```

### 16.8 文本文件判断：_is_text_file

```python
def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS
```

它只用后缀名判断是不是文本文件。

第一版这样足够简单。

后续可以升级：

```text
检查 MIME 类型
尝试读取前几 KB 判断是否二进制
允许更多代码文件扩展名
```

## 17. read_file 内部逻辑

核心流程：

```text
1. 读取 path。
2. 校验 path 是否存在。
3. 校验 path 是否在 workspace 内。
4. 校验是否是文件。
5. 校验文件大小。
6. 校验是否是支持的文本文件。
7. 读取文本。
8. 根据 start_line / end_line 选择行。
9. 给每一行加行号。
10. 返回 ToolResult。
```

关键代码：

```python
lines = file_path.read_text(encoding="utf-8").splitlines()
total_lines = len(lines)
start_line = _get_optional_line_number(input_data, "start_line") or 1
end_line = _get_optional_line_number(input_data, "end_line")
```

如果没传 `end_line`：

```python
end_line = min(total_lines, start_line + DEFAULT_MAX_READ_LINES - 1)
```

也就是说：

```text
默认从 start_line 开始最多读 300 行。
```

加行号：

```python
content = "\n".join(
    f"{line_number}: {line}"
    for line_number, line in enumerate(selected_lines, start=start_line)
)
```

这对代码助手很重要，因为模型后续可以说：

```text
第 42 行附近有问题。
```

## 18. search_files 内部逻辑

核心流程：

```text
1. 读取 query。
2. 校验 query。
3. 获取安全 root。
4. 遍历 root 下文件。
5. 判断 query 是否出现在相对路径里。
6. 收集最多 max_results 条。
7. 返回匹配列表。
```

关键代码：

```python
for path in _iter_project_files(root):
    relative_path = str(path.relative_to(root))
    if query_lower in relative_path.lower():
        matches.append(relative_path)
```

这里用的是简单子串匹配。

例如：

```text
query = "loop.py"
```

可以匹配：

```text
backend\app\agent\loop.py
```

第一版不做复杂 glob 或正则，原因是：

```text
简单、稳定、容易理解。
```

## 19. search_content 内部逻辑

核心流程：

```text
1. 读取 query。
2. 校验 root。
3. 遍历文本文件。
4. 跳过太大的文件。
5. 按行读取。
6. 判断 query 是否出现在某一行。
7. 返回 文件路径:行号:内容。
```

关键代码：

```python
for line_number, line in enumerate(lines, start=1):
    if query_lower in line.lower():
        snippet = line.strip()
        relative_path = path.relative_to(root)
        matches.append(f"{relative_path}:{line_number}: {snippet}")
```

为什么返回行号：

```text
下一步可以用 read_file 精确读取附近片段。
```

典型流程：

```text
search_content("AgentLoop")
-> 找到 backend/app/agent/loop.py:30
-> read_file(path="backend/app/agent/loop.py", start_line=20, end_line=50)
```

这就是代码助手理解项目的基本动作。

## 20. write_file 内部逻辑

核心流程：

```text
1. 读取 path / content / overwrite。
2. 校验 path 和 content。
3. 校验内容大小。
4. 解析 workspace 内路径。
5. 校验文件类型。
6. 如果文件存在且 overwrite=false，拒绝。
7. 创建父目录。
8. 写入文本。
9. 返回写入路径和字节数。
```

关键安全点：

```python
if file_path.exists() and not overwrite:
    return ToolResult(
        ok=False,
        content="File already exists..."
    )
```

为什么默认不覆盖：

```text
写文件是危险动作。
第一版应该避免 agent 误覆盖用户文件。
```

写入：

```python
file_path.parent.mkdir(parents=True, exist_ok=True)
file_path.write_text(content, encoding="utf-8")
```

这里会自动创建父目录。

## 21. edit_file 内部逻辑

核心流程：

```text
1. 读取 path / old_text / new_text。
2. 校验输入。
3. 校验文件路径和类型。
4. 读取原文件。
5. 统计 old_text 出现次数。
6. 0 次：拒绝。
7. 多次：拒绝。
8. 正好 1 次：替换。
9. 检查新文件大小。
10. 写回文件。
```

关键代码：

```python
match_count = original.count(old_text)
if match_count == 0:
    return ToolResult(ok=False, content="old_text was not found in file")
if match_count > 1:
    return ToolResult(ok=False, content="old_text matched ... times")
```

为什么多次匹配要拒绝：

```text
如果 old_text 出现多次，agent 不一定知道该改哪一处。
第一版拒绝模糊编辑，避免误改。
```

替换：

```python
updated = original.replace(old_text, new_text, 1)
```

虽然 `replace(..., 1)` 只替换一次，但前面已经确认只出现一次，所以这里是安全的。

## 22. run_command 内部逻辑

核心流程：

```text
1. 读取 command。
2. 用 shlex.split 拆成参数列表。
3. 检查是否在 ALLOWED_COMMANDS 白名单。
4. 校验 cwd 在 workspace 内。
5. subprocess.run 执行。
6. 捕获超时和命令不存在。
7. 返回 stdout / stderr / returncode。
```

关键代码：

```python
args = shlex.split(command)
```

它把：

```text
git status
```

拆成：

```python
["git", "status"]
```

白名单判断：

```python
if tuple(args) not in ALLOWED_COMMANDS:
    ...
```

这意味着必须完整匹配。

允许：

```text
git status
```

拒绝：

```text
git status --short
dir
rm -rf ...
```

执行命令：

```python
subprocess.run(
    args,
    cwd=cwd,
    capture_output=True,
    text=True,
    timeout=COMMAND_TIMEOUT_SECONDS,
    shell=False,
    check=False,
)
```

几个关键点：

```text
shell=False
不交给 shell 解释，降低注入风险。

timeout=10
避免命令卡死。

capture_output=True
捕获输出，而不是直接打印到终端。

check=False
即使命令返回非 0，也不要抛异常，而是把 returncode 放进 ToolResult。
```

这是一个非常保守的命令工具。

后续如果要更像 Claude Code，可以逐步加：

```text
命令确认机制
更细的白名单
只读命令和写命令分级
前端弹窗确认
命令审计日志
```

## 23. mock_provider 的工具触发器

现在 mock provider 里有一组教学触发器。

它们的作用不是正式功能，而是帮助我们在没有真实模型 API 时测试 AgentLoop。

例如：

```text
mock_tool_search_files: loop.py
```

会返回：

```python
ModelResponse(
    tool_call=ToolCall(
        name="search_files",
        input_data={...}
    )
)
```

AgentLoop 并不知道这是 mock 造出来的。

它只看到：

```text
模型请求调用 search_files
```

这就能测试完整工具链。

真实模型接入以后，这些触发器可以删除或保留为测试模式。

## 24. 如何以后继续自学工具源码

建议按这个顺序看：

```text
1. tools/base.py
   先看工具统一接口。

2. tools/registry.py
   看工具怎么注册和查找。

3. tools/executor.py
   看工具怎么被执行。

4. tools/builtin_tools.py 顶部 helper 函数
   看路径、安全、搜索限制。

5. ReadFileTool
   最容易理解。

6. SearchFilesTool / SearchContentTool
   看文件遍历和内容搜索。

7. WriteFileTool
   看写入保护。

8. EditFileTool
   看精准替换。

9. RunCommandTool
   最后看，因为它涉及 subprocess 和安全边界。
```

不要急着一次性看懂所有实现。

你可以每次只问一个问题：

```text
这个函数拿到什么输入？
它做了哪些校验？
它真正执行的动作是哪一行？
它返回什么 ToolResult？
```

这样慢慢拆，会很稳。

## 25. Python 语法自学补充

这一节专门解释第二章工具代码里出现的 Python 语法。

### 25.1 import

```python
import shlex
import subprocess
from pathlib import Path

from app.core.config import settings
from app.tools.base import ToolDefinition, ToolResult
```

含义：

```text
import shlex
导入 Python 标准库 shlex，用来安全地把命令字符串拆成参数列表。

import subprocess
导入 Python 标准库 subprocess，用来运行外部命令。

from pathlib import Path
导入 Path 类，用现代方式处理文件路径。

from app.core.config import settings
导入项目全局配置。

from app.tools.base import ToolDefinition, ToolResult
导入工具定义和工具结果类型。
```

为什么 `Path` 比字符串拼接更好：

```python
Path("backend") / "app" / "tools"
```

比：

```python
"backend" + "/" + "app" + "/" + "tools"
```

更安全，也更跨平台。

### 25.2 集合 set

```python
IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
}
```

这是一个 `set`。

特点：

```text
无序
元素不能重复
查找速度快
```

为什么这里用 set：

```python
part in IGNORED_DIRS
```

这种判断会很频繁，set 很适合做成员判断。

### 25.3 字典 dict

工具输入和 metadata 经常用字典：

```python
input_data: dict
metadata={"path": str(file_path)}
```

字典是：

```text
key -> value
```

比如：

```python
{
    "path": "backend/app/tools/base.py",
    "start_line": 1,
    "end_line": 8,
}
```

读取值：

```python
path = input_data.get("path")
```

为什么用 `.get()`：

```text
如果 key 不存在，返回 None，不会直接报错。
```

如果写：

```python
input_data["path"]
```

当没有 `path` 时会抛 `KeyError`。

工具层更适合温和返回：

```python
ToolResult(ok=False, content="input.path is required")
```

### 25.4 类型标注

例如：

```python
def _resolve_workspace_path(raw_path: str | None) -> Path:
```

意思是：

```text
raw_path 可以是 str，也可以是 None。
函数返回 Path。
```

再比如：

```python
def _get_root(input_data: dict) -> tuple[Path | None, str | None]:
```

意思是：

```text
返回一个 tuple。
第一个值可能是 Path 或 None。
第二个值可能是错误字符串或 None。
```

类型标注不是强制运行检查，但它能帮助：

```text
VS Code 提示
读代码的人理解
减少低级错误
```

### 25.5 tuple 返回多个值

```python
return root, None
```

这其实返回的是一个 tuple：

```python
(root, None)
```

使用时：

```python
root, error = _get_root(input_data)
```

这叫“解包”。

如果安全：

```python
root = Path(...)
error = None
```

如果失败：

```python
root = None
error = "Path is outside workspace..."
```

这种写法适合工具层，因为它不需要抛异常，而是把错误转成 `ToolResult`。

### 25.6 try / except

例如：

```python
try:
    value = int(raw_value)
except (TypeError, ValueError):
    value = DEFAULT_MAX_RESULTS
```

意思是：

```text
尝试把 raw_value 转成整数。
如果失败，就使用默认值。
```

为什么会失败：

```text
raw_value 是 None
raw_value 是 "abc"
raw_value 是奇怪对象
```

工具函数不能太脆弱。用户或模型传错参数时，最好返回可理解的错误，而不是让程序崩掉。

### 25.7 Path.resolve()

```python
return path.resolve()
```

`resolve()` 会把路径变成标准绝对路径。

例如：

```text
backend/app/tools/base.py
```

变成：

```text
D:\16604\course-ai-assistant\backend\app\tools\base.py
```

为什么重要：

```text
只有变成绝对路径，才能可靠判断它是不是在 workspace 内。
```

### 25.8 Path.relative_to()

```python
path.relative_to(settings.workspace_path)
```

如果 `path` 在 `workspace_path` 里面，它会返回相对路径。

如果不在里面，会抛 `ValueError`。

所以我们写：

```python
try:
    path.relative_to(settings.workspace_path)
except ValueError:
    return False
return True
```

这就是安全判断的核心。

### 25.9 yield

```python
def _iter_project_files(root: Path):
    for path in root.rglob("*"):
        ...
        yield path
```

`yield` 会让函数变成“生成器”。

普通 `return` 是：

```text
一次性返回结果，然后函数结束。
```

`yield` 是：

```text
每次吐出一个结果，函数状态保留，下一次继续。
```

为什么搜索文件适合 yield：

```text
项目文件可能很多。
我们不想一次性把所有文件放进列表。
找到 max_results 条以后就可以停止。
```

### 25.10 list.append()

```python
matches.append(relative_path)
```

意思是把一个元素加到列表末尾。

搜索工具里：

```python
matches: list[str] = []
```

然后每找到一个结果就：

```python
matches.append(...)
```

最后：

```python
"\n".join(matches)
```

把列表变成多行文本。

### 25.11 enumerate

```python
for line_number, line in enumerate(lines, start=1):
```

`enumerate` 会同时给你：

```text
索引
元素
```

这里用 `start=1`，是因为文件行号通常从 1 开始，不是从 0 开始。

例如：

```python
lines = ["a", "b"]
```

循环时得到：

```text
1, "a"
2, "b"
```

这就是为什么 `search_content` 能返回：

```text
path:line_number:content
```

### 25.12 字符串大小写搜索

```python
query_lower = query.lower()
if query_lower in line.lower():
```

这样做是为了忽略大小写。

例如：

```text
AgentLoop
agentloop
AGENTLOOP
```

都能匹配。

### 25.13 切片

```python
selected_lines = lines[start_line - 1 : end_line]
```

Python 切片规则：

```text
左闭右开
```

也就是说：

```python
lines[0:3]
```

取第 0、1、2 个元素，不取第 3 个。

因为用户输入的行号从 1 开始，而列表索引从 0 开始，所以：

```python
start_line - 1
```

### 25.14 join

```python
"\n".join(matches)
```

意思是用换行符把列表连接成一个字符串。

例如：

```python
["a", "b", "c"]
```

会变成：

```text
a
b
c
```

工具返回给模型时，通常更适合返回一段文本，而不是 Python 列表对象。

### 25.15 f-string

```python
f"File not found: {path}"
```

这是格式化字符串。

花括号里的变量会被替换成真实值。

例如：

```python
path = "a.py"
```

结果：

```text
File not found: a.py
```

代码里大量使用 f-string 来生成错误信息和工具结果。

### 25.16 bytes 长度

```python
len(content.encode("utf-8"))
```

这不是字符数，而是 UTF-8 编码后的字节数。

为什么不用：

```python
len(content)
```

因为中文字符在 UTF-8 里通常占多个字节。

文件大小限制应该按字节更准确。

### 25.17 subprocess.run

```python
completed = subprocess.run(
    args,
    cwd=cwd,
    capture_output=True,
    text=True,
    timeout=COMMAND_TIMEOUT_SECONDS,
    shell=False,
    check=False,
)
```

每个参数含义：

```text
args
命令参数列表，比如 ["git", "status"]。

cwd
命令在哪个目录运行。

capture_output=True
捕获 stdout 和 stderr。

text=True
输出按字符串处理，而不是 bytes。

timeout=10
超过 10 秒自动停止。

shell=False
不交给 shell 执行，降低注入风险。

check=False
命令失败时不抛异常，而是让我们自己读取 returncode。
```

执行结果对象里有：

```python
completed.stdout
completed.stderr
completed.returncode
```

### 25.18 shlex.split

```python
args = shlex.split(command)
```

它把命令字符串拆成参数列表。

例如：

```text
git status
```

变成：

```python
["git", "status"]
```

为什么不直接：

```python
command.split(" ")
```

因为 `shlex.split` 更懂命令行规则，比如引号。

不过第一版我们仍然只允许白名单命令，避免复杂风险。

### 25.19 shell=False 为什么重要

如果：

```python
shell=True
```

命令会交给系统 shell 解析。

这可能带来注入风险，比如：

```text
git status && 删除文件
```

第一版用：

```python
shell=False
```

再加白名单，安全很多。

### 25.20 metadata 的意义

每个工具除了 `content`，还可以返回：

```python
metadata={...}
```

例如：

```python
metadata={
    "path": str(file_path),
    "start_line": start_line,
    "end_line": end_line,
    "total_lines": total_lines,
}
```

`content` 是给模型读的主要文本。

`metadata` 是给系统、前端、审计日志用的结构化信息。

后续前端可以用 metadata 显示：

```text
读取了哪个文件
读取了第几行到第几行
工具是否成功
```

### 25.21 为什么工具失败也返回 ToolResult

例如：

```python
return ToolResult(ok=False, content="old_text was not found in file")
```

而不是直接：

```python
raise ValueError(...)
```

原因：

```text
工具失败是 agent 正常工作的一部分。
模型可以读取失败信息，然后换一种方式继续。
```

比如：

```text
old_text 找不到
-> 模型可以 search_content
-> 再决定怎么改
```

所以工具失败不一定是系统崩溃，而是一次可恢复的反馈。

## 26. 自学时可以问自己的 6 个问题

读任何一个工具时，都可以按这 6 个问题拆：

```text
1. 这个工具接收什么 input_data？
2. 它先做了哪些输入校验？
3. 它如何确认路径安全？
4. 它真正执行动作的是哪几行？
5. 它成功时返回什么 ToolResult？
6. 它失败时返回什么 ToolResult？
```

例如读 `edit_file`：

```text
1. 输入 path / old_text / new_text。
2. 校验三者类型。
3. 校验 path 在 workspace 内。
4. original.replace(old_text, new_text, 1) 是真正编辑动作。
5. 成功返回 Edited file。
6. 找不到 old_text 或匹配多次都返回 ok=False。
```

这样学，代码就不会散。

## 27. 第二章补充：read-before-edit + mtime 检查

这一节是对 `edit_file` 的安全补强。

之前的 `edit_file` 逻辑是：

```text
给 path / old_text / new_text
-> 读取文件
-> 确认 old_text 只出现一次
-> 替换成 new_text
-> 写回文件
```

这个版本已经比“直接覆盖整个文件”安全很多，但还有一个问题：

```text
如果模型读完文件之后，
你或另一个程序又改了这个文件，
模型再按旧内容去编辑，
就可能覆盖掉新的修改。
```

所以我们新增了一个机制：

```text
read_file 读取文件时，返回 metadata.mtime_ns
edit_file 修改文件时，必须传 expected_mtime_ns
edit_file 会比较当前文件 mtime_ns 和 expected_mtime_ns
如果不一致，说明文件被改过，拒绝编辑
```

### 27.1 mtime_ns 是什么

`mtime` 是 modified time，也就是“文件最后修改时间”。

`mtime_ns` 是纳秒级修改时间：

```python
file_path.stat().st_mtime_ns
```

这里有两个 Python 知识点：

```text
file_path.stat()
```

会读取文件的系统信息，比如大小、修改时间。

```text
st_mtime_ns
```

表示最后修改时间，单位是纳秒。

我们用它做一个轻量版“文件版本号”。

### 27.2 read_file 的变化

`ReadFileTool.invoke()` 成功时，现在 metadata 里会多返回：

```python
metadata={
    "path": str(file_path),
    "mtime_ns": file_path.stat().st_mtime_ns,
    "size": file_path.stat().st_size,
    "start_line": start_line,
    "end_line": end_line,
    "total_lines": total_lines,
}
```

这表示：

```text
我读到的不只是文本内容，
还读到了这个文件在当时的状态。
```

### 27.3 edit_file 的变化

`EditFileTool` 的输入 schema 现在要求多传：

```python
"expected_mtime_ns": {
    "type": "integer",
    "description": "mtime_ns returned by read_file..."
}
```

所以模型正确的工具调用顺序应该是：

```text
1. read_file({"path": "xxx.py"})
2. 从 read_file 的 metadata 里拿 mtime_ns
3. edit_file({
       "path": "xxx.py",
       "old_text": "...",
       "new_text": "...",
       "expected_mtime_ns": 上一步拿到的 mtime_ns
   })
```

如果模型跳过第一步，直接编辑，会得到：

```text
expected_mtime_ns is required. Call read_file first...
```

这就是“read-before-edit”。

### 27.4 为什么不是只靠 old_text

你可能会想：

```text
既然 old_text 必须精确匹配，为什么还要 mtime？
```

因为 old_text 只能证明：

```text
这段文本现在还在。
```

但它不能证明：

```text
文件其他地方没有被人改过。
```

mtime 检查可以发现“文件整体状态变了”。

这对 AI 编程助手很重要，因为它经常会：

```text
读文件
思考
调用工具
再写文件
```

中间可能发生别的修改。

### 27.5 这对应 Claude Code 的哪类能力

这对应的是代码编辑类 agent 的基础安全机制：

```text
不要在没读过最新文件的情况下修改文件。
```

更完整的版本还会做：

```text
读缓存
文件版本记录
patch 冲突检查
多 agent 并发写入保护
```

我们的 MVP 先做最稳、最容易理解的一层：

```text
mtime_ns 版本检查
```

## 28. 第二章补充：deferred tools 延迟加载

原来的工具注册方式是：

```python
tool_registry = ToolRegistry()
for tool in build_builtin_tools():
    tool_registry.register(tool)
```

这表示每一轮请求开始时，六个工具对象都会被创建。

现在改成：

```python
for definition, factory in build_builtin_tool_factories():
    tool_registry.register_deferred(definition, factory)
```

这里有两个概念：

```text
definition：工具说明书，给模型看。
factory：工具创建函数，真正调用时才执行。
```

### 28.1 为什么要延迟加载

现在我们的工具很轻，立即创建也没问题。

但真实 Claude Code-like 系统里，工具可能会很重，例如：

```text
浏览器工具
代码索引工具
语言服务器工具
远程执行工具
大型知识库检索工具
```

如果每一轮对话都提前创建所有工具，就会浪费时间和资源。

延迟加载的思想是：

```text
先告诉模型“你可以用哪些工具”
等模型真的点名要用某个工具时
再创建那个工具对象
```

### 28.2 ToolRegistry 内部怎么变了

现在 `ToolRegistry` 里有三份字典：

```python
self._tools: dict[str, Tool] = {}
self._definitions: dict[str, ToolDefinition] = {}
self._factories: dict[str, ToolFactory] = {}
```

它们分别表示：

```text
_tools：已经创建好的工具对象
_definitions：工具说明书
_factories：还没创建工具时保存的创建函数
```

`list_definitions()` 只读 `_definitions`：

```text
这样模型能看到工具列表，
但工具对象不一定已经创建。
```

`get(name)` 的逻辑变成：

```text
1. 如果 _tools 里已经有，直接返回
2. 如果没有，看 _factories 里有没有创建函数
3. 有的话，调用 factory() 创建工具
4. 把创建好的工具放进 _tools 缓存
5. 返回工具
```

这就是延迟加载。

### 28.3 Python 语法：Callable

代码里新增了：

```python
from collections.abc import Callable
```

以及：

```python
ToolFactory = Callable[[], Tool]
```

意思是：

```text
ToolFactory 是一种函数。
它不接收参数。
它返回一个 Tool。
```

例如：

```python
ReadFileTool
```

这个类本身就可以当作 factory 使用，因为调用：

```python
ReadFileTool()
```

会创建一个工具对象。

### 28.4 这一节完成后的工具调用链

现在工具调用链是：

```text
gateway
-> 注册工具 definition + factory
-> AgentLoop 把工具 definitions 给 provider
-> provider 决定要调用某个工具
-> ToolExecutor.execute(tool_name, input_data)
-> ToolRegistry.get(tool_name)
-> 如果工具还没创建，就 factory()
-> tool.invoke(input_data)
-> ToolResult 返回给 AgentLoop
```

你要抓住这一句：

```text
模型看到的是工具说明书，后端执行的是工具对象。
```

这也是 agent 系统里“模型”和“平台能力”分离的核心。
