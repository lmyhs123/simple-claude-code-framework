import { request } from "./httpClient.js";

export function createSession(data) {
  return request("/api/sessions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function listSessions() {
  return request("/api/sessions");
}

export function listSessionMessages(sessionId) {
  return request(`/api/sessions/${sessionId}/messages`);
}

