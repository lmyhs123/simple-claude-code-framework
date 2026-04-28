# Simple Claude Code Framework

简易版 Claude Code-like agent framework。

项目定位：

- 本地 Linux 可运行
- 支持 Web agent 工作台
- 支持多轮会话
- 支持 Project / Workspace
- 支持 skills / 助手模式
- 支持 memory / knowledge 层
- 支持 gateway 调度层
- 支持 model provider 抽象
- 后续支持 artifacts、audit、工具调用和更多 provider

课程复习助手只是一个样例 skill，不属于框架主线。

当前主链路：

```text
用户输入
-> frontend 工作台
-> backend api
-> gateway 总调度
-> context builder 组织上下文
-> model provider 生成回复
-> storage 保存会话和消息
```

## 后端启动

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 架构文档

```text
docs/architecture.md  分层架构说明
docs/module-map.md    架构概念和代码文件对应关系
docs/roadmap.md       后续开发路线
docs/api.md           当前 API 草案
```
