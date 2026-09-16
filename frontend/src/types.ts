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

export interface UploadSummary {
  experiment_id: string;
  accepted_files: string[];
  rejected_files: string[];
  duplicate_files: string[];
  rejection_reasons: Record<string, string>;
  total_images: number;
}

export interface UploadLimits {
  max_upload_bytes: number;
  max_image_pixels: number;
}

export interface AnalysisEngine {
  id: string;
  name: string;
  kind: "zero-training" | "pretrained" | "trained";
  status: "available" | "experimental" | "planned" | "license-review";
  description: string;
  training_required: boolean;
  limitations: string[];
}

export type KnownMetricKey =
  | "object_count_total"
  | "objects_per_image"
  | "mean_foreground_fraction"
  | "mean_object_area"
  | "mean_intensity"
  | "mean_contrast"
  | "quality_score";

export interface AnalysisArtifact {
  filename: string;
  kind: "segmentation-overlay";
  media_type: string;
  url: string;
}

export interface ImageAnalysis {
  filename: string;
  object_count: number;
  foreground_fraction: number;
  mean_object_area: number;
  median_object_area: number;
  mean_equivalent_diameter: number;
  threshold: number;
  foreground_polarity: "bright" | "dark";
  overlay_url: string;
}

export interface AnalysisResult {
  experiment_id: string;
  analysis_version: string;
  engine: AnalysisEngine;
  image_count: number;
  metrics: Record<string, number> & Partial<Record<KnownMetricKey, number>>;
  image_results: ImageAnalysis[];
  artifacts: AnalysisArtifact[];
  warnings: string[];
  generated_at: string;
}
