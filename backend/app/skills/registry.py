from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    key: str
    name: str
    description: str
    system_prompt: str


BUILTIN_SKILLS: dict[str, Skill] = {
    "general": Skill(
        key="general",
        name="通用 agent",
        description="默认 skill，适合日常问答、写作、分析和任务拆解。",
        system_prompt="你是一个耐心、清晰、可靠的通用 AI agent。",
    ),
    "course_review": Skill(
        key="course_review",
        name="课程复习 skill",
        description="样例 skill：帮助学生围绕课程资料梳理重点和复习思路。",
        system_prompt="你是课程复习 skill。请优先围绕课程资料总结重点，回答要清晰、分点、适合考前复习。",
    ),
    "document_summary": Skill(
        key="document_summary",
        name="文档总结 skill",
        description="通用 skill：帮助总结文档、笔记、资料和项目上下文。",
        system_prompt="你是文档总结 skill。请把资料内容整理成结构化摘要，突出主题、概念和结论。",
    ),
    "code_explainer": Skill(
        key="code_explainer",
        name="代码讲解 skill",
        description="通用 skill：帮助解释代码、算法和程序运行逻辑。",
        system_prompt="你是代码讲解 skill。请用清晰、可执行的方式解释代码逻辑、关键变量和常见错误。",
    ),
}

