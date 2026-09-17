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

export interface ImageRecord {
  filename: string;
  display_name: string;
  size_bytes: number;
  preview_url: string;
  source_format: string;
  source_mode: string;
  source_bit_depth: number;
  width: number;
  height: number;
}

export interface UploadLimits {
  max_upload_bytes: number;
  max_image_pixels: number;
}

export interface AnalysisEngine {
  id: string;
  name: string;
  task: "segmentation" | "quality-classification";
  kind: "zero-training" | "pretrained" | "trained";
  status: "available" | "experimental" | "planned" | "license-review";
  runnable: boolean;
  unavailable_reason: string | null;
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
  | "quality_score"
  | "images_with_raw_score"
  | "images_outside_training_domain";

export interface AnalysisArtifact {
  filename: string;
  kind: "segmentation-overlay";
  media_type: string;
  url: string;
}

export interface SegmentationImageAnalysis {
  analysis_type: "segmentation";
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

export interface QualityImageAnalysis {
  analysis_type: "quality-classification";
  filename: string;
  source_acquisition_mode: "L" | "RGB" | "outside-training-domain";
  probability_good_raw: number | null;
  review_required: true;
  interpretation: "review-required" | "outside-training-domain";
}

export type ImageAnalysis = SegmentationImageAnalysis | QualityImageAnalysis;

export interface AnalysisResult {
  experiment_id: string;
  analysis_version: string;
  task: "segmentation" | "quality-classification";
  engine: AnalysisEngine;
  image_count: number;
  metrics: Record<string, number> & Partial<Record<KnownMetricKey, number>>;
  image_results: ImageAnalysis[];
  artifacts: AnalysisArtifact[];
  warnings: string[];
  provenance: Record<string, string>;
  generated_at: string;
}

export interface BenchmarkMetric {
  label: string;
  value: number;
  format: "decimal" | "percent" | "seconds" | "megabytes";
  interval_95_percent?: [number, number];
}

export interface BenchmarkRow {
  engine: string;
  status: string;
  metrics: BenchmarkMetric[];
}

export interface BenchmarkSection {
  id: string;
  title: string;
  scope: string;
  rows: BenchmarkRow[];
  decision: string;
}

export interface BenchmarkSummary {
  schema_version: number;
  generated_from: Array<{ path: string; sha256: string }>;
  sections: BenchmarkSection[];
}
