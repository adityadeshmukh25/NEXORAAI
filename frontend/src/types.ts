export interface Project {
  id: number;
  name: string;
  description: string;
  tech_stack: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface OllamaStatus {
  connected: boolean;
  base_url: string;
  configured_model: string;
  model_available: boolean;
  installed_models: string[];
  message: string;
}

export interface HealthStatus {
  status: string;
  database: string;
  app: string;
}
