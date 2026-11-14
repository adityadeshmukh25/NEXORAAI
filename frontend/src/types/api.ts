
export interface ApiList<T> {
  value: T[];
  Count: number;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
}

export interface RequirementItem {
  id: string;
  title: string;
  description: string;
  priority: string;
}

export interface RequirementAnalysisResult {
  project_summary: string;
  functional_requirements: RequirementItem[];
  non_functional_requirements: {
    category: string;
    description: string;
  }[];
  suggested_modules: {
    name: string;
    description: string;
  }[];
  assumptions: string[];
  clarification_questions: string[];
  acceptance_criteria: string[];
  suggested_technology_stack: string[];
  out_of_scope: string[];
}

export interface RequirementAnalysis {
  id: number;
  project_id: number;
  original_requirements: string;
  analysis_result: RequirementAnalysisResult;
  created_at: string;
}

export interface ArchitectureComponent {
  name: string;
  description: string;
  technology: string;
  responsibilities: string[];
}

export interface ArchitectureResult {
  project_overview: string;
  system_architecture: {
    architecture_style: string;
    description: string;
    components: ArchitectureComponent[];
    communication_flow: string[];
  };
  database_design: {
    database_type: string;
    tables: {
      table_name: string;
      description: string;
      fields: {
        name: string;
        data_type: string;
        constraints: string[];
      }[];
    }[];
    relationships: {
      name: string;
      field1?: string | null;
      field2?: string | null;
    }[];
  };
  api_design: {
    base_path: string;
    endpoints: {
      method: string;
      endpoint: string;
      description: string;
      request_body?: string | null;
      response: string;
    }[];
  };
  project_structure: {
    directories: {
      path: string;
      description: string;
    }[];
  };
  technology_recommendations: {
    category: string;
    technology: string;
    reason: string;
  }[];
  development_roadmap: {
    phase: number;
    title: string;
    tasks: string[];
    estimated_effort: string;
  }[];
  security_recommendations: string[];
  scalability_recommendations: string[];
}

export interface ArchitecturePlan {
  id: number;
  project_id: number;
  requirement_analysis_id: number;
  architecture_result: ArchitectureResult;
  created_at: string;
}

export interface GeneratedFile {
  path: string;
  content: string;
  language: string;
  description: string;
}

export interface CodeGeneration {
  id: number;
  project_id: number;
  architecture_plan_id: number;
  status: string;
  summary: string | null;
  generated_files: GeneratedFile[];
  error_message: string | null;
  created_at: string;
}

export interface BackendHealth {
  status: string;
  application: string;
  version: string;
}

export interface OllamaStatus {
  connected: boolean;
  model: string;
  model_available: boolean;
  available_models: string[];
}
