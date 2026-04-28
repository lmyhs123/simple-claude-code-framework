import { request } from "./httpClient.js";

export function createProject(data) {
  return request("/api/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function listProjects() {
  return request("/api/projects");
}
