# 模块映射表

这个文件说明架构概念和当前代码文件的对应关系。

## frontend

职责：网页工作台，负责项目列表、会话列表、聊天输入、消息展示。

当前文件：

```text
frontend/src/App.jsx
frontend/src/api/httpClient.js
frontend/src/api/projects.js
frontend/src/api/sessions.js
frontend/src/api/chat.js
frontend/src/api/skills.js
frontend/src/styles/globals.css
```

## backend api

职责：HTTP 接口层，只负责接收请求、校验数据、调用 service。

当前文件：

```text
backend/app/api/health.py
backend/app/api/projects.py
backend/app/api/sessions.py
backend/app/api/chat.py
backend/app/api/skills.py
```

## gateway

职责：AI 请求总调度层。

当前文件：

```text
backend/app/gateway/gateway.py
backend/app/gateway/context_builder.py
```

调用关系：

```text
api/chat.py
-> chat_service.py
-> gateway/gateway.py
-> gateway/context_builder.py
-> model_providers/provider_factory.py
-> model_providers/mock_provider.py
```

## project

职责：Claude Code-like Project / Workspace。

当前文件：

```text
backend/app/models/project.py
backend/app/schemas/project.py
backend/app/repositories/project_repository.py
backend/app/api/projects.py
frontend/src/api/projects.js
```

## memory / knowledge

职责：项目知识库，后续负责文件解析、切片和检索。

当前已有：

```text
backend/app/models/uploaded_file.py
backend/app/models/document_chunk.py
```

后续需要补：

```text
backend/app/api/files.py
backend/app/services/file_service.py
backend/app/services/knowledge_service.py
backend/app/utils/text_splitter.py
backend/app/utils/pdf_reader.py
```

## model provider

职责：统一模型调用。

当前文件：

```text
backend/app/model_providers/base.py
backend/app/model_providers/mock_provider.py
backend/app/model_providers/provider_factory.py
```

后续建议：

```text
backend/app/model_providers/deepseek_provider.py
backend/app/model_providers/openai_provider.py
backend/app/model_providers/claude_provider.py
```

## artifact

职责：保存和展示模型生成的产物。

当前状态：已有占位 service，尚未接入数据库和前端。

当前文件：

```text
backend/app/artifacts/artifact_service.py
```

后续建议：

```text
backend/app/models/artifact.py
backend/app/api/artifacts.py
frontend/src/components/ArtifactPanel.jsx
```

## audit

职责：记录 gateway 请求、检索、模型调用、错误和耗时。

当前状态：已有占位 service，尚未写入日志文件。

当前文件：

```text
backend/app/audit/audit_service.py
```

后续建议：

```text
backend/logs/gateway-audit.jsonl
```

## storage

职责：数据库、本地文件、日志。

当前文件：

```text
backend/app/core/database.py
backend/app/models/
backend/app/repositories/
backend/data/
backend/uploads/
```
