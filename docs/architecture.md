# Simple Claude Code Framework 架构说明

项目定位是简易版 Claude Code-like agent framework。

业务场景通过 skill 挂载。课程复习助手只是一个 sample skill，不属于框架主线。

## 总体分层

```text
frontend
  Web agent 工作台

backend api
  HTTP 接口层，负责接收前端请求和返回 JSON

gateway
  AI 请求总调度层，负责组合项目、会话、skill、知识库和模型调用

memory / knowledge
  项目知识库层，负责上传资料、解析文本、切片、检索

model provider
  统一模型调用层，负责屏蔽不同模型厂商差异

artifact
  结果产物层，后期用于保存代码、Markdown、HTML、文档等生成结果

audit
  审计日志层，后期用于记录请求、检索、模型调用、错误和耗时

storage
  存储层，包括 SQLite、本地 uploads、日志文件
```

## 核心请求链路

当前已经实现的是最小聊天链路：

```text
用户输入
-> frontend 工作台
-> POST /api/chat
-> chat_service 保存 user message
-> gateway/gateway.py 读取 project / session / skill / knowledge
-> gateway/context_builder.py 组织 messages
-> model_providers/mock_provider.py 生成 mock reply
-> chat_service 保存 assistant message
-> frontend 展示回复
```

后续接入 knowledge 后，链路会变成：

```text
用户输入
-> gateway/gateway.py
-> memory/knowledge_service.py 根据 project_id 检索 document_chunks
-> gateway/context_builder.py 把检索片段放入 messages
-> model_providers 调真实模型
-> 返回回答和引用来源
```

## Gateway 层

Gateway 是平台的大脑调度层。

它不直接负责 HTTP，也不直接负责数据库表定义，而是负责把一次 AI 请求需要的上下文收集起来。

当前文件：

```text
backend/app/gateway/gateway.py
backend/app/gateway/context_builder.py
```

当前职责：

- 读取当前 project
- 读取当前 session 的最近历史消息
- 读取当前 skill / assistant mode
- 调用 memory/knowledge_service.py 获取 knowledge_context
- 调用 context_builder 组装模型 messages
- 调用 model provider 生成回复

对标 `agent-rebuild`：

```text
packages/gateway/gateway.ts
packages/gateway/contextBuilder.ts
```

区别：

- `agent-rebuild` 是 CLI Gateway
- 本项目是 Web Gateway，前面有 FastAPI 和 React

## Project 层

Project 对应 Claude Code-like 框架里的 Project / Workspace。
在框架语境里，它代表一个 agent workspace。

一个 Project 后续应该拥有：

- 项目名称
- 项目说明
- 项目级 system instruction
- 项目会话
- 项目知识库文件
- 项目 artifacts

当前文件：

```text
backend/app/models/project.py
backend/app/api/projects.py
backend/app/schemas/project.py
backend/app/repositories/project_repository.py
frontend/src/api/projects.js
```

当前已实现：

- 创建 project
- 列出 project
- 聊天时可传入 project_id
- gateway 会读取 project 并放入上下文

下一步要完善：

- sessions 绑定 project_id
- uploaded_files 绑定 project_id
- document_chunks 绑定 project_id

## Memory / Knowledge 层

Memory / Knowledge 是 agent workspace 的知识与记忆层。

它负责：

- 上传文件
- 保存文件
- 解析 txt / md / pdf
- 文本切片
- 检索相关片段
- 返回引用来源

当前已有数据雏形：

```text
backend/app/models/uploaded_file.py
backend/app/models/document_chunk.py
```

当前还没实现：

```text
backend/app/api/files.py
backend/app/services/file_service.py
backend/app/utils/text_splitter.py
backend/app/utils/pdf_reader.py
```

当前已有占位：

```text
backend/app/memory/knowledge_service.py
```

对标 `agent-rebuild`：

```text
packages/memory/
workspace/MEMORY.md
workspace/memory/YYYY-MM-DD.md
workspace/sessions/*.jsonl
```

本项目第一版不要直接做复杂 hybrid search。推荐顺序：

```text
v1: 关键词 / LIKE 检索
v2: SQLite FTS5
v3: embedding
v4: FTS + vector hybrid search
v5: RRF 融合排序
```

## Model Provider 层

Model Provider 负责统一模型调用。

当前文件：

```text
backend/app/model_providers/base.py
backend/app/model_providers/mock_provider.py
backend/app/model_providers/provider_factory.py
```

当前状态：

- 只有 mock reply
- 接收 context_builder 生成的 messages
- 用于验证主链路

后续建议升级为：

```text
backend/app/model_providers/openai_provider.py
backend/app/model_providers/deepseek_provider.py
backend/app/model_providers/claude_provider.py
```

统一接口：

```text
generate(messages, temperature, model)
```

对标 `agent-rebuild`：

```text
packages/model/types.ts
packages/model/mockProvider.ts
packages/model/deepseekProvider.ts
```

## Artifact 层

Artifact 是生成结果产物层。

它对应 agent 可以独立保存和迭代的代码、文档、HTML、Markdown 等内容。

当前状态：

- 已有占位 service
- 尚未有数据库表和前端面板

后续建议新增：

```text
backend/app/models/artifact.py
backend/app/api/artifacts.py
frontend/src/components/ArtifactPanel.jsx
```

当前已有：

```text
backend/app/artifacts/artifact_service.py
```

建议第一版字段：

```text
id
project_id
session_id
message_id
artifact_type
title
content
created_at
updated_at
```

第一版只支持：

```text
markdown
code
html
```

## Audit 层

Audit 是请求过程记录层。

它用来回答这些问题：

- 用户问了什么
- 属于哪个 project / session
- 使用了哪个 skill
- 检索到了哪些 knowledge chunks
- 调用了哪个 model provider
- 是否失败
- 耗时多久

当前状态：

- 已有占位 service
- 后续建议先写入 JSONL 日志

后续建议新增：

```text
backend/logs/gateway-audit.jsonl
```

当前已有：

```text
backend/app/audit/audit_service.py
```

对标 `agent-rebuild`：

```text
packages/audit/
logs/gateway-audit.jsonl
```

## Storage 层

Storage 是所有持久化能力的统称。

当前包括：

```text
backend/data/app.db
backend/uploads/
SQLite tables:
  projects
  sessions
  messages
  uploaded_files
  document_chunks
```

当前文件：

```text
backend/app/core/database.py
backend/app/models/
backend/app/repositories/
```

后续会加入：

```text
artifacts
audit logs
knowledge indexes
embedding tables
```
