import { request } from "./httpClient.js";

export function listSkills() {
  return request("/api/skills");
}

