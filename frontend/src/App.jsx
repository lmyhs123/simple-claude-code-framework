import { useEffect, useMemo, useState } from "react";
import { Boxes, MessageSquare, Send, Upload } from "lucide-react";

import { sendChatMessage } from "./api/chat.js";
import { getHealth } from "./api/httpClient.js";
import { createProject, listProjects } from "./api/projects.js";
import { listSkills } from "./api/skills.js";
import {
  createSession,
  listSessionMessages,
  listSessions,
} from "./api/sessions.js";

function App() {
  const [skills, setSkills] = useState([]);
  const [selectedSkill, setSelectedSkill] = useState("general");
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [statusText, setStatusText] = useState("准备就绪");
  const [isSending, setIsSending] = useState(false);

  const currentSkill = useMemo(
    () => skills.find((skill) => skill.key === selectedSkill),
    [skills, selectedSkill],
  );

  useEffect(() => {
    async function loadInitialData() {
      const [skillList, sessionList, projectList] = await Promise.all([
        listSkills(),
        listSessions(),
        listProjects(),
      ]);
      setSkills(skillList);
      setSessions(sessionList);
      setProjects(projectList);
      if (projectList.length > 0) {
        setActiveProject(projectList[0]);
      }
      if (skillList.length > 0) {
        setSelectedSkill(skillList[0].key);
      }
    }

    loadInitialData().catch(() => {
      setStatusText("初始化失败，请确认后端已启动");
    });
  }, []);

  async function checkBackend() {
    const result = await getHealth();
    setStatusText(`后端状态：${result.status}`);
  }

  async function handleCreateSession() {
    const session = await createSession({
      title: "新会话",
      skill_key: selectedSkill,
    });
    setSessions((current) => [session, ...current]);
    setActiveSession(session);
    setMessages([]);
    setStatusText("已创建新会话");
  }

  async function handleCreateProject() {
    const project = await createProject({
      name: "New Project",
      description: "一个 Claude Code-like agent workspace。",
      system_instruction: "请结合项目上下文回答，必要时说明不确定性。",
    });
    setProjects((current) => [project, ...current]);
    setActiveProject(project);
    setStatusText("已创建项目工作区");
  }

  async function handleSelectSession(session) {
    setActiveSession(session);
    setSelectedSkill(session.skill_key);
    const history = await listSessionMessages(session.id);
    setMessages(history);
    setStatusText(`已切换到：${session.title}`);
  }

  async function handleSendMessage(event) {
    event.preventDefault();
    const text = input.trim();
    if (!text || isSending) {
      return;
    }

    setIsSending(true);
    setStatusText("正在发送消息");

    try {
      let session = activeSession;
      if (!session) {
        session = await createSession({
          title: text.slice(0, 20),
          skill_key: selectedSkill,
        });
        setActiveSession(session);
        setSessions((current) => [session, ...current]);
      }

      const result = await sendChatMessage({
        session_id: session.id,
        message: text,
        skill_key: selectedSkill,
        project_id: activeProject?.id ?? null,
      });

      setMessages((current) => [
        ...current,
        result.user_message,
        result.assistant_message,
      ]);
      setInput("");
      setStatusText("回复已保存");
    } catch {
      setStatusText("发送失败，请确认后端已启动");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Boxes size={22} />
          <span>Simple Claude Code</span>
        </div>
        <button className="primary-button" onClick={handleCreateProject}>
          新建项目
        </button>
        <div className="project-list">
          {projects.map((project) => (
            <button
              className={
                activeProject?.id === project.id
                  ? "session-item active"
                  : "session-item"
              }
              key={project.id}
              onClick={() => setActiveProject(project)}
            >
              <span>{project.name}</span>
              <small>{project.description || "无说明"}</small>
            </button>
          ))}
        </div>
        <button className="primary-button" onClick={handleCreateSession}>
          新建会话
        </button>
        <div className="session-list">
          {sessions.map((session) => (
            <button
              className={
                activeSession?.id === session.id
                  ? "session-item active"
                  : "session-item"
              }
              key={session.id}
              onClick={() => handleSelectSession(session)}
            >
              <span>{session.title}</span>
              <small>{session.skill_key}</small>
            </button>
          ))}
        </div>
      </aside>

      <section className="chat-panel">
        <header className="panel-header">
          <MessageSquare size={20} />
          <span>{activeProject?.name ?? "AI 工作台"}</span>
        </header>

        <div className="mode-bar">
          <select
            value={selectedSkill}
            onChange={(event) => setSelectedSkill(event.target.value)}
          >
            {skills.map((skill) => (
              <option key={skill.key} value={skill.key}>
                {skill.name}
              </option>
            ))}
          </select>
          <button onClick={checkBackend}>检查后端</button>
        </div>

        <p className="mode-description">
          {currentSkill?.description ?? "请选择 skill"}
        </p>

        <div className="message-list">
          {messages.length === 0 ? (
            <div className="empty-note">还没有消息，可以直接输入问题开始。</div>
          ) : (
            messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <strong>{message.role === "user" ? "你" : "AI"}</strong>
                <p>{message.content}</p>
              </article>
            ))
          )}
        </div>

        <form className="input-row" onSubmit={handleSendMessage}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="输入问题、任务或让 AI 基于项目知识回答"
          />
          <button disabled={isSending} type="submit" title="发送">
            <Send size={18} />
          </button>
        </form>

        <div className="status-line">{statusText}</div>
      </section>

      <aside className="side-panel">
        <header className="panel-header">
          <Upload size={20} />
          <span>Knowledge</span>
        </header>
        <div className="empty-note">
          文件上传、解析、切片和检索会作为 memory / knowledge 层接入。
          具体场景能力会以 skill 形式挂载。
        </div>
      </aside>
    </main>
  );
}

export default App;
