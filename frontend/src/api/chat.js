import { request } from "./httpClient.js";

export function sendChatMessage(data) {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

