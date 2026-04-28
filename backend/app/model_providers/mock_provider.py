from app.skills.registry import Skill


class MockModelProvider:
    """A local fake model provider used before real API integration."""

    name = "mock"

    def generate(
        self,
        *,
        messages: list[dict[str, str]],
        skill: Skill,
    ) -> str:
        system_message = messages[0]["content"] if messages else ""
        user_message = messages[-1]["content"] if messages else ""
        history_count = max(0, len(messages) - 2)
        return (
            f"【{skill.name}】Gateway 已收到并组织好本次请求。\n\n"
            "当前仍然是 mock 模型回复，用来先跑通 Claude-like 平台主链路。\n\n"
            f"模型将收到的 system message：\n{system_message}\n\n"
            f"模型将收到的当前 user message：\n{user_message}\n\n"
            f"本次上下文包含 {history_count} 条历史消息。"
        )
