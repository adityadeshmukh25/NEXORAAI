
import type {
  ApiList,
  Project,
  ProjectCreate,
  RequirementAnalysis,
  ArchitecturePlan,
  CodeGeneration,
  BackendHealth,
  OllamaStatus,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();

    let message = body || `Request failed: ${response.status}`;

    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || message;
    } catch {
      // Keep the original response text.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  health: () =>
    apiRequest<BackendHealth>("/api/health"),

  ollamaStatus: () =>
    apiRequest<OllamaStatus>("/api/ollama/status"),

  projects: () =>
    apiRequest<ApiList<Project>>("/api/projects"),

  createProject: (data: ProjectCreate) =>
    apiRequest<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  deleteProject: (projectId: number) =>
    apiRequest<void>(`/api/projects/${projectId}`, {
      method: "DELETE",
    }),

  requirements: (projectId: number) =>
    apiRequest<ApiList<RequirementAnalysis>>(
      `/api/projects/${projectId}/requirements`
    ),

  analyzeRequirements: (projectId: number, requirements: string) =>
    apiRequest<RequirementAnalysis>("/api/requirements/analyze", {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId,
        requirements,
      }),
    }),

  architecturePlans: (projectId: number) =>
    apiRequest<ApiList<ArchitecturePlan>>(
      `/api/architecture/projects/${projectId}`
    ),

  generateArchitecture: (requirementAnalysisId: number) =>
    apiRequest<ArchitecturePlan>("/api/architecture/generate", {
      method: "POST",
      body: JSON.stringify({
        requirement_analysis_id: requirementAnalysisId,
      }),
    }),

  codeGenerations: (projectId: number) =>
    apiRequest<ApiList<CodeGeneration>>(
      `/api/code-generation/projects/${projectId}`
    ),

  generateCode: (architecturePlanId: number, instructions?: string) =>
    apiRequest<CodeGeneration>("/api/code-generation/generate", {
      method: "POST",
      body: JSON.stringify({
        architecture_plan_id: architecturePlanId,
        instructions: instructions || null,
      }),
    }),
};
