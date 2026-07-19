import type { RepositoryIndex, RepositoryWorkspace } from "./repository-types";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed with status ${response.status}.`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function importGitHubRepository(repositoryUrl: string): Promise<RepositoryWorkspace> {
  return request("/api/v1/repositories/github", {
    method: "POST",
    body: JSON.stringify({ repository_url: repositoryUrl }),
  });
}

export function indexRepository(workspaceId: string): Promise<RepositoryIndex> {
  return request(`/api/v1/repositories/${workspaceId}/index`, { method: "POST" });
}

export function deleteRepository(workspaceId: string): Promise<void> {
  return request(`/api/v1/repositories/${workspaceId}`, { method: "DELETE" });
}

