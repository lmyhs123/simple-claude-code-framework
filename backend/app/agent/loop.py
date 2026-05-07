from dataclasses import dataclass

from app.core.config import settings
from app.model_providers.base import ModelProvider, ModelResponse
from app.skills.registry import Skill
from app.tools.base import ToolResult
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry

# 这个文件负责“Agent Loop”本身。
# 你可以把它理解成一个最小版执行引擎：
# - 接收已经准备好的 messages
# - 调用模型
# - 判断模型是否请求工具
# - 执行工具
# - 把工具结果追加回 messages
# - 最多重复若干次，直到模型给出最终回答


@dataclass
class AgentLoopResult:
    """Result of one agent turn."""

    final_text: str
    tool_results: list[ToolResult]


# 这里不要只返回一个字符串。
# Agent 系统除了最终回答，还要保留“过程结果”：
# - 调用了哪些工具
# - 工具返回了什么
# 这样后面做前端展示、调试、审计时才有依据。


class AgentLoop:
    """A simplified tutorial-aligned bounded agent loop.

    Current behavior:
    - accepts prepared model messages
    - calls the model provider
    - executes requested tool calls
    - appends tool results to messages
    - repeats up to settings.max_agent_steps
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        # loop 不自己写死工具列表，而是依赖外部传入 registry。
        # 这样以后新增工具时，不需要修改 loop 的主结构。
        self.tool_registry = tool_registry

        # registry 负责“有哪些工具”，executor 负责“怎么执行工具”。
        self.tool_executor = ToolExecutor(tool_registry)

    def run(
        self,
        *,
        messages: list[dict[str, str]],
        provider: ModelProvider,
        skill: Skill,
    ) -> AgentLoopResult:
        """Run one bounded agent turn."""
        # messages:
        # 这是已经准备好的上下文，不是 loop 自己去查数据库。
        #
        # provider:
        # loop 不关心具体是 mock、Claude 还是 OpenAI，它只调用统一接口。
        #
        # AgentLoopResult:
        # loop 不只返回文本，还保留了 tool_results 这个扩展位，
        # 为后面的工具循环、前端展示和审计做准备。

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

            if response.tool_call is None:
                return AgentLoopResult(
                    final_text="Model requested a tool, but no tool call was provided.",
                    tool_results=tool_results,
                )

            tool_result = self.tool_executor.execute(
                tool_name=response.tool_call.name,
                input_data=response.tool_call.input_data,
            )
            tool_results.append(tool_result)

            # 原来的 messages 不动；这里在副本 current_messages 末尾追加 tool 消息。
            # 下一轮 provider.generate(...) 会看到工具结果，再决定继续调用工具或给最终回答。
            current_messages.append(
                {
                    "role": "tool",
                    "content": self._format_tool_result(response, tool_result),
                }
            )

        return AgentLoopResult(
            final_text=(
                "Agent stopped because it reached the maximum number of steps: "
                f"{settings.max_agent_steps}"
            ),
            tool_results=tool_results,
        )

    def _format_tool_result(
        self,
        response: ModelResponse,
        tool_result: ToolResult,
    ) -> str:
        """Format one tool result as a message the model can read."""
        if response.tool_call is None:
            return "No tool call was requested."

        return (
            f"Tool name: {response.tool_call.name}\n"
            f"Tool input: {response.tool_call.input_data}\n"
            f"Tool success: {tool_result.ok}\n"
            f"Tool result:\n{tool_result.content}"
        )

    def _final_text_from_response(self, response: ModelResponse) -> str:
        """Convert the current structured model response into final text."""
        if response.text is not None:
            return response.text
        if response.tool_call is not None:
            return (
                "Model requested another tool call, but the loop did not execute it: "
                f"{response.tool_call.name}"
            )
        return "Model returned an empty response."
