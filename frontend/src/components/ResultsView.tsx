import type { AnalysisResult, Experiment, ImageRecord, QualityImageAnalysis, SegmentationImageAnalysis } from "../types";
import { experimentResultExportUrl } from "../api/client";
import {
  acquisitionModeLabel,
  formatDecimal,
  formatInteger,
  formatMetric,
  formatPercent,
  metricLabel,
  metricUnit,
  localizedEngine,
  readableFilename,
} from "../lib/format";
import { useI18n } from "../i18n";
import { EvidencePanel } from "./EvidencePanel";
import { ExperimentComparison } from "./ExperimentComparison";

interface ResultsViewProps {
  result: AnalysisResult | null;
  images: ImageRecord[];
  selectedExperiment: Experiment | null;
  experiments: Experiment[];
  onOpenImage: (index: number) => void;
  onGoToWorkspace: () => void;
}

function previewFor(images: ImageRecord[], filename: string): string | null {
  return images.find((image) => image.filename === filename)?.preview_url ?? null;
}

export function ResultsView({ result, images, selectedExperiment, experiments, onOpenImage, onGoToWorkspace }: ResultsViewProps) {
  const { locale, localeTag } = useI18n();
  if (!result) {
    return (
      <section className="card empty-state" aria-labelledby="results-title">
        <h2 id="results-title">{locale === "fr" ? "Résultats" : "Results"}</h2>
        <p>
          {selectedExperiment
            ? locale === "fr" ? `Aucune analyse terminée pour « ${selectedExperiment.name} ». Importez des images puis lancez un moteur.` : `No completed analysis for “${selectedExperiment.name}”. Upload images, then run an engine.`
            : locale === "fr" ? "Sélectionnez ou créez une expérience pour voir ses résultats." : "Select or create an experiment to view its results."}
        </p>
        <button className="primary-button" type="button" onClick={onGoToWorkspace}>{locale === "fr" ? "Aller à l’espace de travail" : "Go to workspace"}</button>
      </section>
    );
  }

  const version = encodeURIComponent(result.generated_at);
  const segmentation = result.image_results.filter(
    (item): item is SegmentationImageAnalysis => item.analysis_type === "segmentation",
  );
  const quality = result.image_results.filter(
    (item): item is QualityImageAnalysis => item.analysis_type === "quality-classification",
  );
  const engine = localizedEngine(result.engine, locale);

  return (
    <div className="results">
      <section className="card" aria-labelledby="results-title">
        <div className="card-heading">
          <div>
            <h2 id="results-title">{locale === "fr" ? "Résultats" : "Results"}</h2>
            <p className="results-experiment">
              {locale === "fr" ? "Expérience" : "Experiment"} : {selectedExperiment?.name ?? result.experiment_id} · {engine.name} · pipeline {result.analysis_version} ·{" "}
              {new Date(result.generated_at).toLocaleString(localeTag)}
            </p>
          </div>
          <div className="result-actions" aria-label={locale === "fr" ? "Exporter les résultats" : "Export results"}>
            <a className="secondary-button" href={experimentResultExportUrl(result.experiment_id, "json")}>{locale === "fr" ? "Exporter JSON" : "Export JSON"}</a>
            <a className="secondary-button" href={experimentResultExportUrl(result.experiment_id, "csv")}>{locale === "fr" ? "Exporter CSV" : "Export CSV"}</a>
          </div>
        </div>

        <div className="kpi-grid">
          {Object.entries(result.metrics).map(([key, value]) => (
            <div className={`kpi ${key === "object_count_total" ? "featured" : ""}`} key={key}>
              <span>{metricLabel(key, locale)}</span>
              <strong>{formatMetric(key, value, locale)}</strong>
              <small>{metricUnit(key, locale)}</small>
            </div>
          ))}
        </div>
      </section>

      {result.task === "segmentation" ? (
        <section className="card" aria-labelledby="gallery-title">
          <div className="card-heading">
            <h2 id="gallery-title">{locale === "fr" ? "Images segmentées" : "Segmented images"}</h2>
            <span className="card-meta">{locale === "fr" ? "Cliquez une image pour l’agrandir et comparer avec l’original" : "Select an image to enlarge it and compare it with the source"}</span>
          </div>
          <ul className="gallery" aria-label={locale === "fr" ? "Overlays de segmentation" : "Segmentation overlays"}>
            {segmentation.map((image, index) => (
              <li key={image.filename}>
                <button type="button" className="gallery-card" onClick={() => onOpenImage(index)}>
                  <img
                    src={`${image.overlay_url}?v=${version}`}
                    alt={`${locale === "fr" ? "Segmentation de" : "Segmentation of"} ${readableFilename(image.filename)}`}
                    loading="lazy"
                  />
                  <span className="gallery-caption">
                    <strong>{readableFilename(image.filename)}</strong>
                    <span>{formatInteger(image.object_count, locale)} {locale === "fr" ? "composantes" : "components"} · {formatPercent(image.foreground_fraction, locale)} {locale === "fr" ? "segmenté" : "segmented"}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <details className="table-details">
            <summary>{locale === "fr" ? "Tableau des mesures par image" : "Per-image measurements"}</summary>
            <div className="table-scroll">
              <table className="image-table">
                <caption>{locale === "fr" ? "Composantes connexes du masque, pas des cellules validées" : "Connected mask components, not validated cells"}</caption>
                <thead>
                  <tr>
                    <th scope="col">Image</th>
                    <th scope="col">{locale === "fr" ? "Composantes" : "Components"}</th>
                    <th scope="col">{locale === "fr" ? "Surface segmentée" : "Segmented area"}</th>
                    <th scope="col">{locale === "fr" ? "Aire moyenne (px²)" : "Mean area (px²)"}</th>
                    <th scope="col">{locale === "fr" ? "Aire médiane (px²)" : "Median area (px²)"}</th>
                    <th scope="col">{locale === "fr" ? "Diamètre équivalent (px)" : "Equivalent diameter (px)"}</th>
                    {result.experiment_metadata.microns_per_pixel !== null && <th scope="col">{locale === "fr" ? "Aire moyenne (µm²)" : "Mean area (µm²)"}</th>}
                    {result.experiment_metadata.microns_per_pixel !== null && <th scope="col">{locale === "fr" ? "Diamètre équivalent (µm)" : "Equivalent diameter (µm)"}</th>}
                    <th scope="col">{locale === "fr" ? "Seuil" : "Threshold"}</th>
                    <th scope="col">{locale === "fr" ? "Premier plan" : "Foreground"}</th>
                  </tr>
                </thead>
                <tbody>
                  {segmentation.map((image) => (
                    <tr key={image.filename}>
                      <th scope="row">{readableFilename(image.filename)}</th>
                      <td>{formatInteger(image.object_count, locale)}</td>
                      <td>{formatPercent(image.foreground_fraction, locale)}</td>
                      <td>{formatDecimal(image.mean_object_area, locale)}</td>
                      <td>{formatDecimal(image.median_object_area, locale)}</td>
                      <td>{formatDecimal(image.mean_equivalent_diameter, locale)}</td>
                      {result.experiment_metadata.microns_per_pixel !== null && <td>{formatDecimal(image.mean_object_area * result.experiment_metadata.microns_per_pixel ** 2, locale)}</td>}
                      {result.experiment_metadata.microns_per_pixel !== null && <td>{formatDecimal(image.mean_equivalent_diameter * result.experiment_metadata.microns_per_pixel, locale)}</td>}
                      <td>{formatDecimal(image.threshold, locale)}</td>
                      <td>{image.foreground_polarity === "bright" ? (locale === "fr" ? "clair" : "bright") : (locale === "fr" ? "sombre" : "dark")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </section>
      ) : (
        <section className="card" aria-labelledby="quality-title">
          <div className="card-heading">
            <h2 id="quality-title">{locale === "fr" ? "Images évaluées" : "Evaluated images"}</h2>
            <span className="card-meta">{locale === "fr" ? "Softmax brut non calibré · aucune classe attribuée" : "Uncalibrated raw softmax · no assigned class"}</span>
          </div>
          <ul className="gallery" aria-label={locale === "fr" ? "Images évaluées par le démonstrateur" : "Images evaluated by the demonstrator"}>
            {quality.map((image, index) => (
              <li key={image.filename}>
                <button type="button" className="gallery-card" onClick={() => onOpenImage(index)}>
                  {previewFor(images, image.filename) ? (
                    <img src={previewFor(images, image.filename) ?? undefined} alt={`${locale === "fr" ? "Aperçu de" : "Preview of"} ${readableFilename(image.filename)}`} loading="lazy" />
                  ) : (
                    <span className="gallery-placeholder" aria-hidden="true" />
                  )}
                  <span className="gallery-caption">
                    <strong>{readableFilename(image.filename)}</strong>
                    <span>
                      {image.probability_good_raw === null ? (locale === "fr" ? "Hors domaine · aucun score" : "Out of domain · no score") : `${locale === "fr" ? "Softmax brut" : "Raw softmax"} “good” ${formatDecimal(image.probability_good_raw, locale)} · ${locale === "fr" ? "non calibré" : "uncalibrated"}`}
                    </span>
                    <span className="review-badge">{locale === "fr" ? "À vérifier" : "Review required"}</span>
                    <span className="muted">{acquisitionModeLabel(image.source_acquisition_mode, locale)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {selectedExperiment && (
        <ExperimentComparison
          currentExperiment={selectedExperiment}
          currentResult={result}
          experiments={experiments}
        />
      )}

      <details className="card evidence-details" open>
        <summary>{locale === "fr" ? "Niveau de preuve, limites et provenance" : "Evidence level, limitations, and provenance"}</summary>
        <EvidencePanel result={result} />
      </details>
    </div>
  );
}
