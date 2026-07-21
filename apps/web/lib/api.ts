import type {
  ChatMessage,
  RepositoryChatResponse,
  RepositoryIndex,
  PullRequestAnalysisResponse,
  CIAnalysisResponse,
  RepositoryWorkspace,
} from "./repository-types";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      signal: init?.signal ?? AbortSignal.timeout(180_000),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new Error("The request timed out after three minutes. The repository may be too large; try a smaller one.");
    }
    throw new Error("The API could not be reached. Confirm the backend is running at the configured API URL.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new Error(formatApiError(body?.detail, response.status));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function formatApiError(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) => {
      if (!item || typeof item !== "object") return [];
      const value = item as { msg?: unknown; loc?: unknown };
      if (typeof value.msg !== "string") return [];
      const location = Array.isArray(value.loc) ? value.loc.at(-1) : null;
      return [`${typeof location === "string" ? `${location}: ` : ""}${value.msg}`];
    });
    if (messages.length) return messages.join(" ");
  }
  return `Request failed with status ${status}.`;
}

export function analyzeCIFailure(
  workspaceId: string,
  logs: string,
  workflowName?: string,
): Promise<CIAnalysisResponse> {
  return request(`/api/v1/repositories/${workspaceId}/ci-analysis`, {
    method: "POST",
    body: JSON.stringify({ logs, workflow_name: workflowName || null }),
  });
}

export function analyzePullRequest(
  workspaceId: string,
  diff: string,
  title?: string,
): Promise<PullRequestAnalysisResponse> {
  return request(`/api/v1/repositories/${workspaceId}/pull-request-analysis`, {
    method: "POST",
    body: JSON.stringify({ diff, title: title || null }),
  });
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

export function chatWithRepository(
  workspaceId: string,
  question: string,
  history: ChatMessage[],
): Promise<RepositoryChatResponse> {
  return request(`/api/v1/repositories/${workspaceId}/chat`, {
    method: "POST",
    body: JSON.stringify({ question, history }),
  });
}
