# Roadmap

这个路线图对标 `agent-rebuild`，但按 Simple Claude Code-like framework 的方向改造。

## 已完成

```text
frontend 工作台雏形
backend api 基础路由
sessions / messages
skills
projects
gateway 包
context_builder
memory 包占位
model_providers 包和 mock provider
artifacts 包占位
audit 包占位
SQLite storage
```

## 下一步：Project 关系补齐

目标：

```text
sessions 绑定 project_id
uploaded_files 绑定 project_id
document_chunks 绑定 project_id
```

原因：

Claude Code-like 框架的核心是 Project / Workspace。会话、文件、知识库、artifact 都应该属于某个 Project。

## 第二步：Memory / Knowledge v1

目标：

```text
POST /api/files/upload
GET /api/files
txt / md / pdf 文本提取
固定长度切片
document_chunks 入库
按 project_id 关键词检索
```

第一版检索只做简单关键词，不做 embedding。

## 第三步：Gateway 接入 Knowledge

目标：

```text
gateway/gateway.py 调用 memory/knowledge_service.py
context_builder 拼入 knowledge_context
chat response 返回 citations
```

## 第四步：Model Provider 抽象

目标：

```text
mock provider
DeepSeek provider
OpenAI-compatible provider
Claude provider
```

统一接口：

```text
generate(messages, temperature, model)
```

## 第五步：Artifact v1

目标：

```text
artifacts 表
ArtifactPanel
支持 markdown / code / html
```

第一版只保存和展示，不做复杂实时预览。

## 第六步：Audit v1

目标：

```text
gateway-audit.jsonl
记录 project_id / session_id / skill / model / citations / duration / error
```

## 第七步：Memory 升级

对标 `agent-rebuild/packages/memory`：

```text
SQLite FTS5
embedding
vector search
hybrid search
RRF
reindex
backfill embeddings
```

## 暂缓

这些先不做：

```text
MCP
Tool Registry
多 Agent
复杂权限
团队协作
自动工具调用循环
Docker sandbox
```

原因：它们属于更复杂的 Agent 基础设施，不是当前简易框架的第一优先级。
