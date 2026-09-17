import type {
  AnalysisEngine,
  BenchmarkMetric,
  ExperimentStatus,
  KnownMetricKey,
  QualityImageAnalysis,
} from "../types";

export type MetricFormat = "decimal" | "integer" | "percent" | "relative-index";

export interface MetricPresentation {
  label: string;
  format: MetricFormat;
  unit?: string;
}

export const metricPresentations: Record<KnownMetricKey, MetricPresentation> = {
  object_count_total: { label: "Composantes connexes", format: "integer" },
  objects_per_image: { label: "Composantes / image", format: "decimal" },
  mean_foreground_fraction: { label: "Surface segmentée", format: "percent" },
  mean_object_area: { label: "Surface moyenne", format: "decimal", unit: "pixels²" },
  mean_intensity: { label: "Intensité moyenne", format: "decimal", unit: "échelle 0–1" },
  mean_contrast: { label: "Contraste moyen", format: "decimal", unit: "échelle 0–1" },
  quality_score: {
    label: "Indice de contraste relatif",
    format: "relative-index",
    unit: "heuristique 0–1 · pas une probabilité",
  },
  images_with_raw_score: { label: "Images avec softmax brut", format: "integer" },
  images_outside_training_domain: { label: "Images hors domaine", format: "integer" },
};

const decimalFormatter = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });
const relativeIndexFormatter = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const percentFormatter = new Intl.NumberFormat("fr-FR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatDecimal(value: number): string {
  return decimalFormatter.format(value);
}

export function formatPercent(value: number): string {
  return percentFormatter.format(value);
}

export function formatInteger(value: number): string {
  return Math.round(value).toLocaleString("fr-FR");
}

export function formatMetric(key: string, value: number): string {
  const presentation = metricPresentations[key as KnownMetricKey];
  switch (presentation?.format) {
    case "integer":
      return formatInteger(value);
    case "percent":
      return formatPercent(value);
    case "relative-index":
      return relativeIndexFormatter.format(value);
    default:
      return formatDecimal(value);
  }
}

export function metricLabel(key: string): string {
  return metricPresentations[key as KnownMetricKey]?.label ?? key;
}

export function metricUnit(key: string): string {
  return metricPresentations[key as KnownMetricKey]?.unit ?? "";
}

export const statusLabels: Record<ExperimentStatus, string> = {
  draft: "Brouillon",
  ready: "Prêt",
  analyzing: "Analyse",
  complete: "Terminé",
  failed: "Échec",
};

export const engineStatusLabels: Record<AnalysisEngine["status"], string> = {
  available: "Disponible",
  experimental: "Expérimental",
  planned: "Planifié",
  "license-review": "Revue de licence",
};

export const engineKindLabels: Record<AnalysisEngine["kind"], string> = {
  "zero-training": "Pipeline déterministe",
  pretrained: "Modèle préentraîné",
  trained: "Modèle entraîné",
};

export const acquisitionModeLabels: Record<QualityImageAnalysis["source_acquisition_mode"], string> = {
  L: "Niveaux de gris (L)",
  RGB: "Couleur (RGB)",
  "outside-training-domain": "Hors du domaine d’entraînement",
};

const provenanceKeyLabels: Record<string, string> = {
  model_sha256: "SHA-256 du modèle ONNX",
  preprocessing_sha256: "SHA-256 du prétraitement",
  labels_sha256: "SHA-256 des étiquettes",
  selection_report_sha256: "SHA-256 du rapport de sélection",
  config_sha256: "SHA-256 de la configuration",
  output_semantics: "Sémantique de la sortie",
  selection_scope: "Périmètre de sélection",
};

const provenanceValueLabels: Record<string, string> = {
  "raw-softmax-positive-class-good-uncalibrated":
    "softmax brut de la classe « good », non calibré",
  "campaign-v2-validation-only": "sélection sur la validation campagne v2, test jamais ouvert",
};

export function provenanceLabel(key: string): string {
  return provenanceKeyLabels[key] ?? key.replaceAll("_", " ");
}

export function provenanceValue(value: string): string {
  return provenanceValueLabels[value] ?? value;
}

export function isHexDigest(value: string): boolean {
  return /^[0-9a-f]{64}$/i.test(value);
}

export function readableFilename(filename: string): string {
  return filename.replace(/^[a-f0-9]{12}-/, "");
}

export function imageCountLabel(count: number): string {
  return `${count} image${count > 1 ? "s" : ""}`;
}

const benchmarkFormatter = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

export function formatBenchmarkMetric(metric: BenchmarkMetric): string {
  if (metric.format === "percent") {
    return formatPercent(metric.value);
  }
  if (metric.format === "seconds") {
    return `${formatDecimal(metric.value)} s`;
  }
  if (metric.format === "megabytes") {
    return `${formatInteger(metric.value)} Mo`;
  }
  return benchmarkFormatter.format(metric.value);
}

export function formatBenchmarkInterval(interval: [number, number]): string {
  return `[${benchmarkFormatter.format(interval[0])} ; ${benchmarkFormatter.format(interval[1])}]`;
}
