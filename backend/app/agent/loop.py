from dataclasses import dataclass

from app.model_providers.base import ModelProvider, ModelResponse
from app.skills.registry import Skill
from app.tools.base import ToolResult
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry

# 这个文件负责“Agent Loop”本身。
# 你可以把它理解成一个最小版执行引擎：
# - 接收已经准备好的 messages
# - 调用模型
# - 后续再逐步扩展成“模型请求工具 -> 执行工具 -> 再回到模型”的循环


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
    """A simplified tutorial-aligned agent loop.

    Current behavior:
    - accepts prepared model messages
    - calls the model provider once
    - returns a structured result object

    Later we will extend this into:
    LLM -> tool call -> execute -> append result -> repeat
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
        '''
        messages
        这是已经准备好的上下文，不是 loop 自己去查数据库。

        provider
        loop 不关心具体是 mock、Claude 还是 OpenAI，它只调用统一接口。

        AgentLoopResult
        loop 不只返回文本，还保留了 tool_results 这个扩展位，为后面的工具循环做准备。
        '''
        
        """Run one minimal agent turn."""
        # 当前阶段：先让 loop 真正接管“调用模型”这一步。
        # 后续再把这里扩成：
        # 1. 调模型
        # 2. 判断是否要调用工具
        # 3. 执行工具
        # 4. 把工具结果追加回 messages
        # 5. 再调模型
        response = provider.generate(messages=messages, skill=skill)
        final_text = self._final_text_from_response(response)
        return AgentLoopResult(final_text=final_text, tool_results=[])

    def _final_text_from_response(self, response: ModelResponse) -> str:
        """Convert the current structured model response into final text.

        Tool calls are not executed yet. The next step in the tutorial will
        replace this fallback with real tool execution.
        """
        if response.text is not None:
            return response.text
        if response.tool_call is not None:
            return (
                "Model requested a tool call, but tool execution is not wired "
                f"yet: {response.tool_call.name}"
            )
        return "Model returned an empty response."
