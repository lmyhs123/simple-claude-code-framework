from dataclasses import dataclass
from typing import Any, Protocol
'''
dataclass：用来定义简单数据对象，比如工具定义、工具结果。

Protocol：用来定义“只要长得像这个接口，就算一个 Tool”。

你可以把 Protocol 理解成 Python 里的接口约定。
'''


@dataclass(frozen=True)
class ToolDefinition:
    """Metadata for one tool exposed to the agent."""

    name: str
    description: str
    input_schema: dict[str, Any]
    '''
    这表示“一个工具对模型的说明书”。

    它包含：

    name：工具名，比如 read_file
    description：工具能做什么
    input_schema：工具需要什么输入
    为什么需要这个？

    因为模型不是 Python 程序员，它不知道你类里有哪些方法。你要把工具能力描述给模型:
    这里有一个 read_file 工具
    它可以读取文本文件
    你调用它时需要传 path
    这就是 ToolDefinition 的价值
    '''


@dataclass
class ToolResult:
    """Normalized result returned by any tool execution."""

    ok: bool
    content: str
    metadata: dict[str, Any] | None = None
'''
这是“工具执行结果”的统一格式。

无论是：

read_file
write_file
search_content
run_command
都统一返回：

ok：成功还是失败
content：结果文本
metadata：额外信息
'''

class Tool(Protocol):
    """Common interface for built-in and future external tools."""

    definition: ToolDefinition

    def invoke(self, input_data: dict[str, Any]) -> ToolResult:
        """Execute the tool and return normalized output."""
'''
这就是工具接口。

一个对象只要满足两个条件，就可以被当作工具：

有 definition
有 invoke(input_data)
'''
