export type ExperimentStatus =
  | "draft"
  | "ready"
  | "analyzing"
  | "complete"
  | "failed";

export interface Experiment {
  id: string;
  name: string;
  description: string;
  control_label: string;
  treatment_label: string;
  status: ExperimentStatus;
  image_count: number;
  created_at: string;
}

export interface ExperimentCreate {
  name: string;
  description: string;
  control_label: string;
  treatment_label: string;
}

export interface AnalysisResult {
  experiment_id: string;
  analysis_version: string;
  image_count: number;
  metrics: Record<string, number>;
  warnings: string[];
  generated_at: string;
}

