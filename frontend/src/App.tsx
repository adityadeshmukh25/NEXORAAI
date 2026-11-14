
import { useEffect, useState, type FormEvent } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Code2,
  Cpu,
  Database,
  FileCode2,
  FolderKanban,
  LayoutDashboard,
  Loader2,
  Network,
  Plus,
  RefreshCw,
  Server,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import { api } from "./services/api";

import type {
  Project,
  RequirementAnalysis,
  ArchitecturePlan,
  CodeGeneration,
  BackendHealth,
  OllamaStatus,
} from "./types/api";

type Page =
  | "Overview"
  | "Projects"
  | "Requirements"
  | "Architecture"
  | "Code Generation";

/**
 * Handles both API list response formats:
 * 1. { value: [...], Count: 1 }
 * 2. [...]
 */
function getList<T>(response: unknown): T[] {
  if (Array.isArray(response)) {
    return response as T[];
  }

  if (
    response !== null &&
    typeof response === "object" &&
    "value" in response
  ) {
    const value = (response as { value?: unknown }).value;

    if (Array.isArray(value)) {
      return value as T[];
    }
  }

  return [];
}

function sortByDate<T extends { created_at: string }>(items: T[]): T[] {
  return [...items].sort(
    (a, b) =>
      new Date(b.created_at).getTime() -
      new Date(a.created_at).getTime()
  );
}

const navigation: {
  label: Page;
  icon: typeof LayoutDashboard;
}[] = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Projects", icon: FolderKanban },
  { label: "Requirements", icon: ClipboardList },
  { label: "Architecture", icon: Network },
  { label: "Code Generation", icon: Code2 },
];

function formatDate(value?: string) {
  if (!value) return "Not available";

  return new Date(value).toLocaleString();
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();

  const color =
    normalized === "completed" ||
    normalized === "healthy" ||
    normalized === "connected"
      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      : normalized === "failed" ||
          normalized === "disconnected"
        ? "bg-red-500/10 text-red-400 border-red-500/20"
        : "bg-amber-500/10 text-amber-400 border-amber-500/20";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${color}`}
    >
      {status}
    </span>
  );
}

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
}: {
  title: string;
  value: string | number;
  description: string;
  icon: typeof LayoutDashboard;
}) {
  return (
    <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">{title}</p>
        <div className="rounded-xl bg-accent/10 p-2.5 text-accent-light">
          <Icon size={19} />
        </div>
      </div>

      <p className="mt-5 text-3xl font-semibold text-white">{value}</p>
      <p className="mt-2 text-xs text-gray-500">{description}</p>
    </div>
  );
}

function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-dark-700 bg-dark-900/60 p-10 text-center">
      <Sparkles className="mx-auto text-accent-light" size={30} />
      <h3 className="mt-4 font-semibold text-white">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-gray-400">
        {description}
      </p>
    </div>
  );
}

function App() {
  const [page, setPage] = useState<Page>("Overview");

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number>(0);

  const [requirements, setRequirements] = useState<RequirementAnalysis[]>([]);
  const [architectures, setArchitectures] = useState<ArchitecturePlan[]>([]);
  const [generations, setGenerations] = useState<CodeGeneration[]>([]);

  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [ollama, setOllama] = useState<OllamaStatus | null>(null);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");

  const [showCreateProject, setShowCreateProject] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");

  const [requirementText, setRequirementText] = useState("");
  const [generationInstructions, setGenerationInstructions] = useState("");

  const selectedProject = projects.find(
    (project) => project.id === selectedProjectId
  );

  const latestRequirement = requirements[0];
  const latestArchitecture = architectures[0];
  const latestGeneration = generations[0];

  async function loadProjects() {
    const response = await api.projects();

    const items = sortByDate(getList<Project>(response));

    setProjects(items);

    if (items.length > 0) {
      setSelectedProjectId((current) =>
        items.some((item) => item.id === current)
          ? current
          : items[0].id
      );
    } else {
      setSelectedProjectId(0);
    }
  }

  async function loadProjectData(projectId: number) {
    if (!projectId) {
      setRequirements([]);
      setArchitectures([]);
      setGenerations([]);
      return;
    }

    const [
      requirementResult,
      architectureResult,
      generationResult,
    ] = await Promise.all([
      api.requirements(projectId),
      api.architecturePlans(projectId),
      api.codeGenerations(projectId),
    ]);

    setRequirements(
      sortByDate(getList<RequirementAnalysis>(requirementResult))
    );

    setArchitectures(
      sortByDate(getList<ArchitecturePlan>(architectureResult))
    );

    setGenerations(
      sortByDate(getList<CodeGeneration>(generationResult))
    );
  }

  async function refreshAll() {
    setError("");

    try {
      await Promise.all([
        loadProjects(),
        refreshConnections(),
      ]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load dashboard"
      );
    }
  }

  async function refreshConnections() {
    const [healthResult, ollamaResult] = await Promise.allSettled([
      api.health(),
      api.ollamaStatus(),
    ]);

    setHealth(
      healthResult.status === "fulfilled" ? healthResult.value : null
    );

    setOllama(
      ollamaResult.status === "fulfilled" ? ollamaResult.value : null
    );
  }

  // Initial dashboard loading.
  useEffect(() => {
    let active = true;

    async function initialize() {
      try {
        const [
          projectResult,
          healthResult,
          ollamaResult,
        ] = await Promise.allSettled([
          api.projects(),
          api.health(),
          api.ollamaStatus(),
        ]);

        if (!active) return;

        if (projectResult.status === "fulfilled") {
          const items = sortByDate(
            getList<Project>(projectResult.value)
          );

          setProjects(items);

          if (items.length > 0) {
            setSelectedProjectId(items[0].id);
          }
        } else {
          setError(
            projectResult.reason instanceof Error
              ? projectResult.reason.message
              : "Could not load projects"
          );
        }

        setHealth(
          healthResult.status === "fulfilled"
            ? healthResult.value
            : null
        );

        setOllama(
          ollamaResult.status === "fulfilled"
            ? ollamaResult.value
            : null
        );
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to initialize dashboard"
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    initialize();

    const interval = window.setInterval(() => {
      refreshConnections();
    }, 10000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  // Load data whenever the selected project changes.
  useEffect(() => {
    let active = true;

    async function fetchSelectedProject() {
      if (!selectedProjectId) {
        setRequirements([]);
        setArchitectures([]);
        setGenerations([]);
        return;
      }

      try {
        const [
          requirementResult,
          architectureResult,
          generationResult,
        ] = await Promise.all([
          api.requirements(selectedProjectId),
          api.architecturePlans(selectedProjectId),
          api.codeGenerations(selectedProjectId),
        ]);

        if (!active) return;

        setRequirements(
          sortByDate(getList<RequirementAnalysis>(requirementResult))
        );

        setArchitectures(
          sortByDate(getList<ArchitecturePlan>(architectureResult))
        );

        setGenerations(
          sortByDate(getList<CodeGeneration>(generationResult))
        );
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load project information"
          );
        }
      }
    }

    fetchSelectedProject();

    return () => {
      active = false;
    };
  }, [selectedProjectId]);

  async function handleCreateProject(event: FormEvent) {
    event.preventDefault();

    if (projectName.trim().length < 2) {
      setError("Project name must contain at least 2 characters.");
      return;
    }

    setActionLoading(true);
    setError("");

    try {
      const created = await api.createProject({
        name: projectName.trim(),
        description: projectDescription.trim() || null,
      });

      await loadProjects();
      setSelectedProjectId(created.id);

      setProjectName("");
      setProjectDescription("");
      setShowCreateProject(false);
      setPage("Projects");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Project creation failed"
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDeleteProject(projectId: number) {
    const confirmed = window.confirm(
      "Delete this project? This operation may also affect its associated data."
    );

    if (!confirmed) return;

    setActionLoading(true);
    setError("");

    try {
      await api.deleteProject(projectId);
      await loadProjects();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Project deletion failed"
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function handleAnalyzeRequirements(event: FormEvent) {
    event.preventDefault();

    if (!selectedProjectId) {
      setError("Select a project first.");
      return;
    }

    if (requirementText.trim().length < 10) {
      setError("Requirements must contain at least 10 characters.");
      return;
    }

    setActionLoading(true);
    setError("");

    try {
      await api.analyzeRequirements(
        selectedProjectId,
        requirementText.trim()
      );

      setRequirementText("");
      await loadProjectData(selectedProjectId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Requirement analysis failed"
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function handleGenerateArchitecture() {
    if (!latestRequirement) {
      setError("Analyze requirements before generating architecture.");
      return;
    }

    setActionLoading(true);
    setError("");

    try {
      await api.generateArchitecture(latestRequirement.id);
      await loadProjectData(selectedProjectId);
      setPage("Architecture");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Architecture generation failed"
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function handleGenerateCode() {
    if (!latestArchitecture) {
      setError("Generate architecture before generating code.");
      return;
    }

    setActionLoading(true);
    setError("");

    try {
      await api.generateCode(
        latestArchitecture.id,
        generationInstructions
      );

      setGenerationInstructions("");
      await loadProjectData(selectedProjectId);
      setPage("Code Generation");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Code generation failed"
      );
    } finally {
      setActionLoading(false);
    }
  }

  const totalGeneratedFiles = generations.reduce(
    (total, item) => total + item.generated_files.length,
    0
  );

  return (
    <div className="min-h-screen bg-dark-950 text-gray-200">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 shrink-0 border-r border-dark-700 bg-dark-900 p-5 lg:flex lg:flex-col">
          <div className="mb-10 flex items-center gap-3">
            <div className="rounded-xl bg-accent p-2.5 text-white">
              <Cpu size={22} />
            </div>

            <div>
              <h1 className="font-bold text-white">NEXORA AI</h1>
              <p className="text-xs text-gray-500">Build Smarter. Ship Faster.</p>
            </div>
          </div>

          <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
            Workspace
          </p>

          <nav className="space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = page === item.label;

              return (
                <button
                  key={item.label}
                  onClick={() => {
                    setError("");
                    setPage(item.label);
                  }}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${
                    active
                      ? "bg-accent/15 text-accent-light"
                      : "text-gray-400 hover:bg-dark-800 hover:text-white"
                  }`}
                >
                  <Icon size={18} />
                  {item.label}
                  {active && <ChevronRight className="ml-auto" size={16} />}
                </button>
              );
            })}
          </nav>

          <div className="mt-auto rounded-xl border border-dark-700 bg-dark-800 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-white">
              <Activity size={17} className="text-emerald-400" />
              System status
            </div>

            <div className="mt-4 space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Backend</span>
                <span
                  className={
                    health?.status === "healthy"
                      ? "text-emerald-400"
                      : "text-red-400"
                  }
                >
                  {health?.status || "Offline"}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-gray-400">Ollama</span>
                <span
                  className={
                    ollama?.connected
                      ? "text-emerald-400"
                      : "text-red-400"
                  }
                >
                  {ollama?.connected ? "Connected" : "Offline"}
                </span>
              </div>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 border-b border-dark-700 bg-dark-950/90 px-5 py-4 backdrop-blur md:px-8">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-white">{page}</h2>
                <p className="mt-1 text-xs text-gray-500">
                  Build and manage software with AI agents
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <select
                  value={selectedProjectId || ""}
                  onChange={(event) =>
                    setSelectedProjectId(Number(event.target.value))
                  }
                  className="max-w-48 rounded-xl border border-dark-700 bg-dark-900 px-3 py-2 text-sm text-gray-200 outline-none focus:border-accent"
                >
                  <option value="">Select project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>

                <button
                  onClick={refreshAll}
                  title="Refresh dashboard"
                  className="rounded-xl border border-dark-700 bg-dark-900 p-2.5 text-gray-400 hover:text-white"
                >
                  <RefreshCw size={17} />
                </button>

                <button
                  onClick={() => setShowCreateProject(true)}
                  className="flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-600"
                >
                  <Plus size={17} />
                  New Project
                </button>
              </div>
            </div>
          </header>

          <div className="flex gap-2 overflow-x-auto border-b border-dark-700 bg-dark-900 px-4 py-3 lg:hidden">
            {navigation.map((item) => {
              const Icon = item.icon;

              return (
                <button
                  key={item.label}
                  onClick={() => setPage(item.label)}
                  className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-xs ${
                    page === item.label
                      ? "bg-accent/20 text-accent-light"
                      : "bg-dark-800 text-gray-400"
                  }`}
                >
                  <Icon size={15} />
                  {item.label}
                </button>
              );
            })}
          </div>

          <div className="space-y-6 p-5 md:p-8">
            {error && (
              <div className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300">
                <AlertCircle size={18} className="mt-0.5 shrink-0" />
                <span className="flex-1">{error}</span>
                <button onClick={() => setError("")}>
                  <X size={17} />
                </button>
              </div>
            )}

            {loading ? (
              <div className="flex items-center justify-center py-32 text-gray-400">
                <Loader2 className="mr-3 animate-spin" />
                Loading workspace...
              </div>
            ) : (
              <>
                {page === "Overview" && (
                  <section className="space-y-6">
                    <div className="rounded-2xl border border-accent/20 bg-gradient-to-r from-accent/15 to-dark-900 p-6 md:p-8">
                      <p className="text-sm font-medium text-accent-light">
                        NEXORA AI
                      </p>

                      <h3 className="mt-3 text-2xl font-bold text-white md:text-3xl">
                        Turn ideas into working software.
                      </h3>

                      <p className="mt-3 max-w-2xl text-sm leading-6 text-gray-400">
                        Analyze requirements, design architecture, generate
                        application code and review AI-generated fixes from
                        one workspace.
                      </p>

                      <button
                        onClick={() => setPage("Projects")}
                        className="mt-6 flex items-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-medium text-white hover:bg-violet-600"
                      >
                        Open projects
                        <ChevronRight size={17} />
                      </button>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                      <MetricCard
                        title="Total projects"
                        value={projects.length}
                        description="Projects stored in your backend"
                        icon={FolderKanban}
                      />

                      <MetricCard
                        title="Requirement analyses"
                        value={requirements.length}
                        description="Analyses for the selected project"
                        icon={ClipboardList}
                      />

                      <MetricCard
                        title="Architecture plans"
                        value={architectures.length}
                        description="Plans for the selected project"
                        icon={Network}
                      />

                      <MetricCard
                        title="Generated files"
                        value={totalGeneratedFiles}
                        description="Files across this project's generations"
                        icon={FileCode2}
                      />
                    </div>

                    <div className="grid gap-6 xl:grid-cols-2">
                      <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                        <h3 className="font-semibold text-white">
                          AI environment
                        </h3>

                        <div className="mt-5 space-y-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Server className="text-accent-light" size={19} />
                              <div>
                                <p className="text-sm text-white">FastAPI</p>
                                <p className="text-xs text-gray-500">
                                  Backend service
                                </p>
                              </div>
                            </div>

                            <StatusBadge
                              status={health?.status || "disconnected"}
                            />
                          </div>

                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Cpu className="text-accent-light" size={19} />
                              <div>
                                <p className="text-sm text-white">Ollama</p>
                                <p className="text-xs text-gray-500">
                                  {ollama?.model || "Model unavailable"}
                                </p>
                              </div>
                            </div>

                            <StatusBadge
                              status={
                                ollama?.connected ? "connected" : "disconnected"
                              }
                            />
                          </div>

                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Database className="text-accent-light" size={19} />
                              <div>
                                <p className="text-sm text-white">
                                  Project database
                                </p>
                                <p className="text-xs text-gray-500">
                                  SQLite / SQLAlchemy backend
                                </p>
                              </div>
                            </div>

                            <StatusBadge
                              status={
                                health?.status === "healthy"
                                  ? "healthy"
                                  : "unknown"
                              }
                            />
                          </div>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                        <h3 className="font-semibold text-white">
                          Selected project
                        </h3>

                        {selectedProject ? (
                          <div className="mt-5">
                            <h4 className="text-lg font-semibold text-accent-light">
                              {selectedProject.name}
                            </h4>

                            <p className="mt-2 text-sm text-gray-400">
                              {selectedProject.description ||
                                "No project description"}
                            </p>

                            <div className="mt-5 flex items-center justify-between">
                              <StatusBadge status={selectedProject.status} />
                              <span className="text-xs text-gray-500">
                                Created {formatDate(selectedProject.created_at)}
                              </span>
                            </div>
                          </div>
                        ) : (
                          <p className="mt-5 text-sm text-gray-400">
                            Create a project to get started.
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                      <h3 className="font-semibold text-white">
                        Development pipeline
                      </h3>

                      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        {[
                          {
                            title: "Requirements",
                            done: requirements.length > 0,
                            icon: ClipboardList,
                          },
                          {
                            title: "Architecture",
                            done: architectures.length > 0,
                            icon: Network,
                          },
                          {
                            title: "Code generation",
                            done: generations.length > 0,
                            icon: Code2,
                          },
                          {
                            title: "Code validation",
                            done: false,
                            icon: CheckCircle2,
                          },
                        ].map((step) => {
                          const Icon = step.icon;

                          return (
                            <div
                              key={step.title}
                              className="rounded-xl border border-dark-700 bg-dark-800 p-4"
                            >
                              <div className="flex items-center justify-between">
                                <Icon
                                  size={19}
                                  className={
                                    step.done
                                      ? "text-emerald-400"
                                      : "text-gray-500"
                                  }
                                />
                                {step.done ? (
                                  <CheckCircle2
                                    size={17}
                                    className="text-emerald-400"
                                  />
                                ) : (
                                  <span className="text-xs text-gray-500">
                                    Pending
                                  </span>
                                )}
                              </div>

                              <p className="mt-4 text-sm font-medium text-white">
                                {step.title}
                              </p>
                            </div>
                          );
                        })}
                      </div>

                      <p className="mt-4 text-xs text-gray-500">
                        Code validation is not inferred from code generation;
                        run the validation workflow to verify it.
                      </p>
                    </div>
                  </section>
                )}

                {page === "Projects" && (
                  <section className="space-y-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-white">
                          Your projects
                        </h3>
                        <p className="mt-1 text-sm text-gray-400">
                          Create and manage your software projects.
                        </p>
                      </div>

                      <button
                        onClick={() => setShowCreateProject(true)}
                        className="flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm text-white"
                      >
                        <Plus size={17} />
                        Create project
                      </button>
                    </div>

                    {projects.length === 0 ? (
                      <EmptyState
                        title="No projects yet"
                        description="Create your first project to start the AI development workflow."
                      />
                    ) : (
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {projects.map((project) => (
                          <div
                            key={project.id}
                            className={`rounded-2xl border bg-dark-900 p-5 ${
                              selectedProjectId === project.id
                                ? "border-accent/60"
                                : "border-dark-700"
                            }`}
                          >
                            <div className="flex items-start justify-between">
                              <div className="rounded-xl bg-accent/10 p-3 text-accent-light">
                                <FolderKanban size={21} />
                              </div>

                              <StatusBadge status={project.status} />
                            </div>

                            <h4 className="mt-5 font-semibold text-white">
                              {project.name}
                            </h4>

                            <p className="mt-2 min-h-10 text-sm text-gray-400">
                              {project.description || "No description"}
                            </p>

                            <p className="mt-4 text-xs text-gray-500">
                              Project ID: {project.id}
                            </p>

                            <p className="mt-1 text-xs text-gray-500">
                              {formatDate(project.created_at)}
                            </p>

                            <div className="mt-5 flex gap-2">
                              <button
                                onClick={() => {
                                  setSelectedProjectId(project.id);
                                  setPage("Requirements");
                                }}
                                className="flex-1 rounded-lg bg-accent px-3 py-2 text-xs font-medium text-white hover:bg-violet-600"
                              >
                                Open project
                              </button>

                              <button
                                disabled={actionLoading}
                                onClick={() =>
                                  handleDeleteProject(project.id)
                                }
                                className="rounded-lg border border-dark-700 px-3 py-2 text-gray-400 hover:border-red-500/50 hover:text-red-400"
                                title="Delete project"
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                )}

                {page === "Requirements" && (
                  <section className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-white">
                        Requirement analysis
                      </h3>
                      <p className="mt-1 text-sm text-gray-400">
                        Describe what your application should do. The AI will
                        analyze and organize the requirements.
                      </p>
                    </div>

                    {!selectedProject ? (
                      <EmptyState
                        title="Select a project"
                        description="Choose or create a project before submitting requirements."
                      />
                    ) : (
                      <>
                        <form
                          onSubmit={handleAnalyzeRequirements}
                          className="rounded-2xl border border-dark-700 bg-dark-900 p-5"
                        >
                          <label className="text-sm font-medium text-white">
                            Requirements for {selectedProject.name}
                          </label>

                          <textarea
                            value={requirementText}
                            onChange={(event) =>
                              setRequirementText(event.target.value)
                            }
                            rows={6}
                            maxLength={12000}
                            minLength={10}
                            placeholder="Example: Build an application where users can register, browse products, add products to a cart and place orders..."
                            className="mt-3 w-full resize-y rounded-xl border border-dark-700 bg-dark-800 p-4 text-sm text-gray-200 outline-none placeholder:text-gray-600 focus:border-accent"
                          />

                          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                            <span className="text-xs text-gray-500">
                              {requirementText.length}/12000 characters
                            </span>

                            <button
                              disabled={
                                actionLoading ||
                                requirementText.trim().length < 10
                              }
                              className="flex items-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {actionLoading && (
                                <Loader2 size={16} className="animate-spin" />
                              )}
                              Analyze with AI
                            </button>
                          </div>
                        </form>

                        {latestRequirement ? (
                          <div className="space-y-5">
                            <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <h4 className="font-semibold text-white">
                                  Analysis #{latestRequirement.id}
                                </h4>
                                <span className="text-xs text-gray-500">
                                  {formatDate(latestRequirement.created_at)}
                                </span>
                              </div>

                              <p className="mt-4 text-sm leading-6 text-gray-300">
                                {latestRequirement.analysis_result.project_summary}
                              </p>

                              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                                <MetricCard
                                  title="Functional requirements"
                                  value={
                                    latestRequirement.analysis_result
                                      .functional_requirements.length
                                  }
                                  description="Identified features"
                                  icon={ClipboardList}
                                />

                                <MetricCard
                                  title="Non-functional"
                                  value={
                                    latestRequirement.analysis_result
                                      .non_functional_requirements.length
                                  }
                                  description="Quality requirements"
                                  icon={Activity}
                                />

                                <MetricCard
                                  title="Suggested modules"
                                  value={
                                    latestRequirement.analysis_result
                                      .suggested_modules.length
                                  }
                                  description="Application modules"
                                  icon={Network}
                                />
                              </div>
                            </div>

                            <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                              <h4 className="font-semibold text-white">
                                Functional requirements
                              </h4>

                              <div className="mt-4 space-y-3">
                                {latestRequirement.analysis_result.functional_requirements.map(
                                  (item) => (
                                    <div
                                      key={item.id}
                                      className="rounded-xl border border-dark-700 bg-dark-800 p-4"
                                    >
                                      <div className="flex flex-wrap items-center justify-between gap-2">
                                        <p className="font-medium text-white">
                                          {item.id} — {item.title}
                                        </p>
                                        <StatusBadge status={item.priority} />
                                      </div>

                                      <p className="mt-2 text-sm text-gray-400">
                                        {item.description}
                                      </p>
                                    </div>
                                  )
                                )}
                              </div>
                            </div>

                            <div className="grid gap-5 xl:grid-cols-2">
                              <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                                <h4 className="font-semibold text-white">
                                  Suggested modules
                                </h4>

                                <div className="mt-4 space-y-3">
                                  {latestRequirement.analysis_result.suggested_modules.map(
                                    (module) => (
                                      <div key={module.name}>
                                        <p className="text-sm font-medium text-accent-light">
                                          {module.name}
                                        </p>
                                        <p className="mt-1 text-sm text-gray-400">
                                          {module.description}
                                        </p>
                                      </div>
                                    )
                                  )}
                                </div>
                              </div>

                              <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                                <h4 className="font-semibold text-white">
                                  Acceptance criteria
                                </h4>

                                <ul className="mt-4 space-y-3">
                                  {latestRequirement.analysis_result.acceptance_criteria.map(
                                    (criterion, index) => (
                                      <li
                                        key={index}
                                        className="flex gap-2 text-sm text-gray-400"
                                      >
                                        <CheckCircle2
                                          size={16}
                                          className="mt-0.5 shrink-0 text-emerald-400"
                                        />
                                        {criterion}
                                      </li>
                                    )
                                  )}
                                </ul>
                              </div>
                            </div>

                            <button
                              disabled={actionLoading}
                              onClick={handleGenerateArchitecture}
                              className="flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
                            >
                              Generate architecture
                              <ChevronRight size={17} />
                            </button>
                          </div>
                        ) : (
                          <EmptyState
                            title="No analysis yet"
                            description="Submit your application requirements above to get started."
                          />
                        )}
                      </>
                    )}
                  </section>
                )}

                {page === "Architecture" && (
                  <section className="space-y-6">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-white">
                          Architecture design
                        </h3>
                        <p className="mt-1 text-sm text-gray-400">
                          Generate and inspect your application's architecture.
                        </p>
                      </div>

                      <button
                        disabled={!latestRequirement || actionLoading}
                        onClick={handleGenerateArchitecture}
                        className="flex items-center gap-2 rounded-xl bg-accent px-4 py-3 text-sm text-white disabled:opacity-50"
                      >
                        {actionLoading && (
                          <Loader2 size={16} className="animate-spin" />
                        )}
                        Generate architecture
                      </button>
                    </div>

                    {!latestArchitecture ? (
                      <EmptyState
                        title="Architecture not generated"
                        description="Analyze requirements first, then generate the architecture plan."
                      />
                    ) : (
                      <>
                        <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <h4 className="font-semibold text-white">
                              Architecture plan #{latestArchitecture.id}
                            </h4>
                            <span className="text-xs text-gray-500">
                              {formatDate(latestArchitecture.created_at)}
                            </span>
                          </div>

                          <p className="mt-4 text-sm text-gray-300">
                            {latestArchitecture.architecture_result.project_overview}
                          </p>

                          <p className="mt-4 text-sm text-accent-light">
                            Style:{" "}
                            {
                              latestArchitecture.architecture_result
                                .system_architecture.architecture_style
                            }
                          </p>

                          <p className="mt-2 text-sm text-gray-400">
                            {
                              latestArchitecture.architecture_result
                                .system_architecture.description
                            }
                          </p>
                        </div>

                        <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                          <h4 className="font-semibold text-white">
                            System components
                          </h4>

                          <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                            {latestArchitecture.architecture_result.system_architecture.components.map(
                              (component) => (
                                <div
                                  key={component.name}
                                  className="rounded-xl border border-dark-700 bg-dark-800 p-4"
                                >
                                  <p className="font-semibold text-white">
                                    {component.name}
                                  </p>
                                  <p className="mt-1 text-xs text-accent-light">
                                    {component.technology}
                                  </p>
                                  <p className="mt-3 text-sm text-gray-400">
                                    {component.description}
                                  </p>
                                  <ul className="mt-3 space-y-1">
                                    {component.responsibilities.map(
                                      (responsibility) => (
                                        <li
                                          key={responsibility}
                                          className="text-xs text-gray-500"
                                        >
                                          • {responsibility}
                                        </li>
                                      )
                                    )}
                                  </ul>
                                </div>
                              )
                            )}
                          </div>
                        </div>

                        <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                          <h4 className="font-semibold text-white">
                            Database design
                          </h4>
                          <p className="mt-2 text-sm text-accent-light">
                            Database:{" "}
                            {
                              latestArchitecture.architecture_result
                                .database_design.database_type
                            }
                          </p>

                          <div className="mt-4 space-y-3">
                            {latestArchitecture.architecture_result.database_design.tables.map(
                              (table) => (
                                <details
                                  key={table.table_name}
                                  className="rounded-xl border border-dark-700 bg-dark-800 p-4"
                                >
                                  <summary className="cursor-pointer text-sm font-medium text-white">
                                    {table.table_name} — {table.description}
                                  </summary>

                                  <div className="mt-3 overflow-x-auto">
                                    <table className="w-full text-left text-xs">
                                      <thead className="text-gray-500">
                                        <tr>
                                          <th className="py-2">Field</th>
                                          <th>Data type</th>
                                          <th>Constraints</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {table.fields.map((field) => (
                                          <tr
                                            key={field.name}
                                            className="border-t border-dark-700 text-gray-300"
                                          >
                                            <td className="py-2">{field.name}</td>
                                            <td>{field.data_type}</td>
                                            <td>
                                              {field.constraints.join(", ") || "—"}
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                </details>
                              )
                            )}
                          </div>
                        </div>

                        <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                          <h4 className="font-semibold text-white">
                            Technology recommendations
                          </h4>

                          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                            {latestArchitecture.architecture_result.technology_recommendations.map(
                              (item, index) => (
                                <div
                                  key={`${item.category}-${index}`}
                                  className="rounded-xl bg-dark-800 p-4"
                                >
                                  <p className="text-xs text-gray-500">
                                    {item.category}
                                  </p>
                                  <p className="mt-1 font-medium text-accent-light">
                                    {item.technology}
                                  </p>
                                  <p className="mt-2 text-xs text-gray-400">
                                    {item.reason}
                                  </p>
                                </div>
                              )
                            )}
                          </div>
                        </div>

                        <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                          <h4 className="font-semibold text-white">
                            Generate application code
                          </h4>

                          <textarea
                            value={generationInstructions}
                            onChange={(event) =>
                              setGenerationInstructions(event.target.value)
                            }
                            rows={3}
                            placeholder="Optional instructions for the code generation agent..."
                            className="mt-4 w-full rounded-xl border border-dark-700 bg-dark-800 p-3 text-sm outline-none focus:border-accent"
                          />

                          <button
                            disabled={actionLoading}
                            onClick={handleGenerateCode}
                            className="mt-4 flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
                          >
                            <Code2 size={17} />
                            Generate code
                          </button>
                        </div>
                      </>
                    )}
                  </section>
                )}

                {page === "Code Generation" && (
                  <section className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-white">
                        Code generation
                      </h3>
                      <p className="mt-1 text-sm text-gray-400">
                        Review generated source files and generation status.
                      </p>
                    </div>

                    {!latestGeneration ? (
                      <EmptyState
                        title="No generated code"
                        description="Generate an architecture plan first, then use the code generation action to create application files."
                      />
                    ) : (
                      <>
                        <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <h4 className="font-semibold text-white">
                                Generation #{latestGeneration.id}
                              </h4>
                              <p className="mt-1 text-xs text-gray-500">
                                {formatDate(latestGeneration.created_at)}
                              </p>
                            </div>

                            <StatusBadge status={latestGeneration.status} />
                          </div>

                          <p className="mt-4 text-sm leading-6 text-gray-400">
                            {latestGeneration.summary || "No summary available"}
                          </p>

                          {latestGeneration.error_message && (
                            <div className="mt-4 rounded-xl bg-red-500/10 p-3 text-sm text-red-300">
                              {latestGeneration.error_message}
                            </div>
                          )}

                          <div className="mt-5 grid gap-3 sm:grid-cols-2">
                            <MetricCard
                              title="Generated files"
                              value={latestGeneration.generated_files.length}
                              description="Files in this generation"
                              icon={FileCode2}
                            />

                            <MetricCard
                              title="Generation status"
                              value={latestGeneration.status}
                              description="Status returned by backend"
                              icon={Activity}
                            />
                          </div>
                        </div>

                        <div className="rounded-2xl border border-dark-700 bg-dark-900 p-5">
                          <h4 className="font-semibold text-white">
                            Generated files
                          </h4>

                          <div className="mt-4 space-y-3">
                            {latestGeneration.generated_files.map(
                              (file, index) => (
                                <details
                                  key={`${file.path}-${index}`}
                                  className="rounded-xl border border-dark-700 bg-dark-800 p-4"
                                >
                                  <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-3">
                                    <span className="flex items-center gap-2 text-sm font-medium text-white">
                                      <FileCode2
                                        size={17}
                                        className="text-accent-light"
                                      />
                                      {file.path}
                                    </span>

                                    <span className="rounded-md bg-dark-700 px-2 py-1 text-xs text-gray-400">
                                      {file.language}
                                    </span>
                                  </summary>

                                  <p className="mt-3 text-xs text-gray-500">
                                    {file.description}
                                  </p>

                                  <pre className="mt-3 max-h-96 overflow-auto rounded-lg border border-dark-700 bg-dark-950 p-4 text-xs leading-5 text-gray-300">
                                    <code>{file.content}</code>
                                  </pre>
                                </details>
                              )
                            )}
                          </div>
                        </div>
                      </>
                    )}
                  </section>
                )}
              </>
            )}
          </div>
        </main>
      </div>

      {showCreateProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <form
            onSubmit={handleCreateProject}
            className="w-full max-w-lg rounded-2xl border border-dark-700 bg-dark-900 p-6 shadow-2xl"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">
                Create a project
              </h3>

              <button
                type="button"
                onClick={() => setShowCreateProject(false)}
                className="text-gray-400 hover:text-white"
              >
                <X size={20} />
              </button>
            </div>

            <label className="mt-6 block text-sm text-gray-300">
              Project name
            </label>

            <input
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              minLength={2}
              maxLength={200}
              required
              placeholder="My AI application"
              className="mt-2 w-full rounded-xl border border-dark-700 bg-dark-800 p-3 text-sm outline-none focus:border-accent"
            />

            <label className="mt-5 block text-sm text-gray-300">
              Description
            </label>

            <textarea
              value={projectDescription}
              onChange={(event) =>
                setProjectDescription(event.target.value)
              }
              rows={3}
              placeholder="Describe what you want to build..."
              className="mt-2 w-full rounded-xl border border-dark-700 bg-dark-800 p-3 text-sm outline-none focus:border-accent"
            />

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowCreateProject(false)}
                className="rounded-xl border border-dark-700 px-4 py-2.5 text-sm text-gray-300"
              >
                Cancel
              </button>

              <button
                disabled={actionLoading}
                className="flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
              >
                {actionLoading && (
                  <Loader2 size={16} className="animate-spin" />
                )}
                Create project
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default App;
