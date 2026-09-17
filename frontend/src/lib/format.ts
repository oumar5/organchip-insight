import type {
  AnalysisEngine,
  BenchmarkMetric,
  ExperimentStatus,
  KnownMetricKey,
  QualityImageAnalysis,
} from "../types";
import type { Locale } from "../i18n";

export type MetricFormat = "decimal" | "integer" | "percent" | "relative-index";

interface MetricPresentation {
  format: MetricFormat;
  labels: Record<Locale, string>;
  units?: Partial<Record<Locale, string>>;
}

const metricPresentations: Record<KnownMetricKey, MetricPresentation> = {
  object_count_total: { format: "integer", labels: { fr: "Composantes connexes", en: "Connected components" } },
  objects_per_image: { format: "decimal", labels: { fr: "Composantes / image", en: "Components / image" } },
  mean_foreground_fraction: { format: "percent", labels: { fr: "Surface segmentée", en: "Segmented area" } },
  mean_object_area: { format: "decimal", labels: { fr: "Surface moyenne", en: "Mean area" }, units: { fr: "pixels²", en: "pixels²" } },
  mean_intensity: { format: "decimal", labels: { fr: "Intensité moyenne", en: "Mean intensity" }, units: { fr: "échelle 0–1", en: "0–1 scale" } },
  mean_contrast: { format: "decimal", labels: { fr: "Contraste moyen", en: "Mean contrast" }, units: { fr: "échelle 0–1", en: "0–1 scale" } },
  quality_score: {
    format: "relative-index",
    labels: { fr: "Indice de contraste relatif", en: "Relative contrast index" },
    units: { fr: "heuristique 0–1 · pas une probabilité", en: "0–1 heuristic · not a probability" },
  },
  images_with_raw_score: { format: "integer", labels: { fr: "Images avec softmax brut", en: "Images with raw softmax" } },
  images_outside_training_domain: { format: "integer", labels: { fr: "Images hors domaine", en: "Out-of-domain images" } },
};

function localeTag(locale: Locale): "fr-FR" | "en-US" {
  return locale === "fr" ? "fr-FR" : "en-US";
}

export function formatDecimal(value: number, locale: Locale = "fr"): string {
  return new Intl.NumberFormat(localeTag(locale), { maximumFractionDigits: 2 }).format(value);
}

export function formatPercent(value: number, locale: Locale = "fr"): string {
  return new Intl.NumberFormat(localeTag(locale), {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatInteger(value: number, locale: Locale = "fr"): string {
  return Math.round(value).toLocaleString(localeTag(locale));
}

export function formatMetric(key: string, value: number, locale: Locale = "fr"): string {
  const presentation = metricPresentations[key as KnownMetricKey];
  if (presentation?.format === "integer") return formatInteger(value, locale);
  if (presentation?.format === "percent") return formatPercent(value, locale);
  if (presentation?.format === "relative-index") {
    return new Intl.NumberFormat(localeTag(locale), { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
  }
  return formatDecimal(value, locale);
}

export function metricLabel(key: string, locale: Locale = "fr"): string {
  return metricPresentations[key as KnownMetricKey]?.labels[locale] ?? key;
}

export function metricUnit(key: string, locale: Locale = "fr"): string {
  return metricPresentations[key as KnownMetricKey]?.units?.[locale] ?? "";
}

const experimentStatuses: Record<ExperimentStatus, Record<Locale, string>> = {
  draft: { fr: "Brouillon", en: "Draft" },
  ready: { fr: "Prêt", en: "Ready" },
  analyzing: { fr: "Analyse", en: "Analyzing" },
  complete: { fr: "Terminé", en: "Complete" },
  failed: { fr: "Échec", en: "Failed" },
};

export function statusLabel(status: ExperimentStatus, locale: Locale): string {
  return experimentStatuses[status][locale];
}

const engineStatuses: Record<AnalysisEngine["status"], Record<Locale, string>> = {
  available: { fr: "Disponible", en: "Available" },
  experimental: { fr: "Expérimental", en: "Experimental" },
  planned: { fr: "Planifié", en: "Planned" },
  "license-review": { fr: "Revue de licence", en: "License review" },
};

export function engineStatusLabel(status: AnalysisEngine["status"], locale: Locale): string {
  return engineStatuses[status][locale];
}

const engineKinds: Record<AnalysisEngine["kind"], Record<Locale, string>> = {
  "zero-training": { fr: "Pipeline déterministe", en: "Deterministic pipeline" },
  pretrained: { fr: "Modèle préentraîné", en: "Pretrained model" },
  trained: { fr: "Modèle entraîné", en: "Trained model" },
};

export function engineKindLabel(kind: AnalysisEngine["kind"], locale: Locale): string {
  return engineKinds[kind][locale];
}

const acquisitionModes: Record<QualityImageAnalysis["source_acquisition_mode"], Record<Locale, string>> = {
  L: { fr: "Niveaux de gris (L)", en: "Grayscale (L)" },
  RGB: { fr: "Couleur (RGB)", en: "Color (RGB)" },
  "outside-training-domain": { fr: "Hors du domaine d’entraînement", en: "Outside training domain" },
};

export function acquisitionModeLabel(mode: QualityImageAnalysis["source_acquisition_mode"], locale: Locale): string {
  return acquisitionModes[mode][locale];
}

const provenanceKeyLabels: Record<string, Record<Locale, string>> = {
  model_sha256: { fr: "SHA-256 du modèle ONNX", en: "ONNX model SHA-256" },
  preprocessing_sha256: { fr: "SHA-256 du prétraitement", en: "Preprocessing SHA-256" },
  labels_sha256: { fr: "SHA-256 des étiquettes", en: "Labels SHA-256" },
  selection_report_sha256: { fr: "SHA-256 du rapport de sélection", en: "Selection report SHA-256" },
  config_sha256: { fr: "SHA-256 de la configuration", en: "Configuration SHA-256" },
  output_semantics: { fr: "Sémantique de la sortie", en: "Output semantics" },
  selection_scope: { fr: "Périmètre de sélection", en: "Selection scope" },
};

const provenanceValueLabels: Record<string, Record<Locale, string>> = {
  "raw-softmax-positive-class-good-uncalibrated": {
    fr: "softmax brut de la classe « good », non calibré",
    en: "raw softmax for the ‘good’ class, uncalibrated",
  },
  "campaign-v2-validation-only": {
    fr: "sélection sur la validation campagne v2, test jamais ouvert",
    en: "selected on campaign-v2 validation only; frozen test never opened",
  },
};

export function provenanceLabel(key: string, locale: Locale): string {
  return provenanceKeyLabels[key]?.[locale] ?? key.replaceAll("_", " ");
}

export function provenanceValue(value: string, locale: Locale): string {
  return provenanceValueLabels[value]?.[locale] ?? value;
}

export function isHexDigest(value: string): boolean {
  return /^[0-9a-f]{64}$/i.test(value);
}

export function readableFilename(filename: string): string {
  return filename.replace(/^[a-f0-9]{12}-/, "");
}

export function imageCountLabel(count: number, locale: Locale = "fr"): string {
  if (locale === "en") return `${count} image${count === 1 ? "" : "s"}`;
  return `${count} image${count > 1 ? "s" : ""}`;
}

export function formatBenchmarkMetric(metric: BenchmarkMetric, locale: Locale): string {
  if (metric.format === "percent") return formatPercent(metric.value, locale);
  if (metric.format === "seconds") return `${formatDecimal(metric.value, locale)} s`;
  if (metric.format === "megabytes") return `${formatInteger(metric.value, locale)} MB`;
  return new Intl.NumberFormat(localeTag(locale), { minimumFractionDigits: 3, maximumFractionDigits: 3 }).format(metric.value);
}

export function formatBenchmarkInterval(interval: [number, number], locale: Locale): string {
  const formatter = new Intl.NumberFormat(localeTag(locale), { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  return `[${formatter.format(interval[0])}; ${formatter.format(interval[1])}]`;
}

const benchmarkTranslations: Record<string, string> = {
  "Premier plan microfluidique · BBBC019": "Microfluidic foreground · BBBC019",
  "13 images DIC externes avec masques binaires manuels. Comparaison à protocole identique ; ce jeu n'est pas le dataset OoC du concours.": "13 external DIC images with manual binary masks. Same-protocol comparison; this is not the competition OoC dataset.",
  "µSAM améliore le premier plan sur ce petit jeu externe, mais son coût CPU et le benchmark d'instances BBBC038 empêchent sa promotion.": "µSAM improves foreground segmentation on this small external set, but its CPU cost and the BBBC038 instance benchmark prevent promotion.",
  "Instances nucléaires · BBBC038": "Nuclear instances · BBBC038",
  "Audit zéro-shot pré-enregistré sur 12 images choisies pour leur diversité, pas une estimation de population sur les 670 images.": "Preregistered zero-shot audit on 12 images selected for diversity, not a population estimate over all 670 images.",
  "Ce résultat nucléaire externe ne valide pas le comptage de cellules sur les images OoC.": "This external nuclear result does not validate cell counting on OoC images.",
  "Premier plan d'organoïde · iOrganoAssay v1.1.0": "Organoid foreground · iOrganoAssay v1.1.0",
  "Validation externe pré-enregistrée sur les 28 triplets officiels BF/GT/Seg (14 contrôle, 14 DSS). Le masque cible un organoïde, pas toutes les instances du champ.": "Preregistered external validation on all 28 official BF/GT/Seg triplets (14 control, 14 DSS). The mask targets one organoid, not every instance in the field.",
  "Le résultat peut être présenté comme une preuve externe de segmentation d'organoïde. Il ne valide ni la segmentation OoC, ni une classification good/bad, ni un comptage cellulaire.": "The result supports external organoid segmentation evidence. It does not validate OoC segmentation, good/bad classification, or cell counting.",
  "Moteur produit": "Product engine",
  "Benchmark isolé": "Isolated benchmark",
  "Non promu · 2 critères sur 3 échouent": "Not promoted · 2 of 3 criteria failed",
  "Preuve externe · 3 critères sur 3 atteints": "External evidence · all 3 criteria met",
  "Temps / image": "Time / image",
  "Mémoire max.": "Peak memory",
  "Macro-F1 objet · IoU 0,50": "Object macro-F1 · IoU 0.50",
  "Macro-F1 objet · IoU 0,75": "Object macro-F1 · IoU 0.75",
  "Erreur comptage médiane": "Median counting error",
  "F1 contrôle": "Control F1",
};

export function benchmarkText(value: string, locale: Locale): string {
  return locale === "en" ? benchmarkTranslations[value] ?? value : value;
}

const engineTranslations: Record<string, { name: string; description: string; limitations: string[] }> = {
  "adaptive-segmentation-v1": {
    name: "Adaptive segmentation v1",
    description: "Local segmentation using Otsu thresholding, morphology, and connected components. It runs immediately without weights or training.",
    limitations: [
      "Exploratory result not validated for biological or clinical decisions.",
      "Separation of touching objects remains limited.",
      "Foreground is estimated automatically and must be reviewed visually.",
    ],
  },
  "ooc-quality-cnn-campaign-v2-gray448": {
    name: "Campaign-v2 quality CNN — demonstrator",
    description: "ONNX demonstrator from run B selected on validation. It exposes the raw softmax only and requires human review for every image.",
    limitations: [
      "No automatic good/bad decision: every output is marked ‘Review required’.",
      "The raw softmax is neither calibrated nor a probability of biological quality.",
      "The RGB signal is modest and not distinguishable from validation-selection effects.",
      "The observed domain is limited to source acquisition modes L and RGB.",
    ],
  },
  "cellpose-pretrained": {
    name: "Pretrained Cellpose",
    description: "Candidate general-purpose cell and nucleus segmentation engine.",
    limitations: ["Disabled until weight-license compatibility is approved.", "Weight downloads and additional compute resources are required."],
  },
  "micro-sam-pretrained": {
    name: "Pretrained µSAM",
    description: "Microscopy-focused engine integrated in an isolated benchmark environment.",
    limitations: [
      "Not enabled in the product path after the non-promotion decision.",
      "The BBBC038 benchmark fails two of the three preregistered criteria.",
      "Local CPU measurement: 36.7 s/image on average and 8.9 GB peak memory.",
      "External nuclear validation does not validate counting on OoC images.",
    ],
  },
};

export function localizedEngine(engine: AnalysisEngine, locale: Locale): AnalysisEngine {
  if (locale === "fr") return engine;
  const translated = engineTranslations[engine.id];
  return translated ? { ...engine, ...translated } : engine;
}

const runtimeTranslations: Array<[RegExp, string]> = [
  [/La taille dépasse la limite par image\.?/i, "The file exceeds the per-image size limit."],
  [/Fichier non pris en charge\.?/i, "Unsupported file."],
  [/Aucune analyse terminée/i, "No completed analysis"],
  [/Format d’image non pris en charge/i, "Unsupported image format"],
];

export function localizedRuntimeText(value: string, locale: Locale): string {
  if (locale === "fr") return value;
  for (const [pattern, replacement] of runtimeTranslations) {
    if (pattern.test(value)) return value.replace(pattern, replacement);
  }
  return value;
}
