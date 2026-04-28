# API 草案

当前已实现：

```text
GET /api/health
GET /api/skills
POST /api/projects
GET /api/projects
POST /api/sessions
GET /api/sessions
GET /api/sessions/{session_id}/messages
DELETE /api/sessions/{session_id}
POST /api/chat
```

`POST /api/chat` 会接收 `skill_key` 和可选的 `project_id`。
后端会通过 gateway 层读取项目、skill、历史消息和知识库上下文，再交给模型服务。
MVP 阶段模型服务仍然使用 mock 回复。

后续阶段将继续实现：

```text
POST /api/files/upload
GET /api/files
```
