import type { AnalysisResult, Experiment, ImageRecord, QualityImageAnalysis, SegmentationImageAnalysis } from "../types";
import { experimentResultExportUrl } from "../api/client";
import {
  acquisitionModeLabels,
  formatDecimal,
  formatInteger,
  formatMetric,
  formatPercent,
  metricLabel,
  metricUnit,
  readableFilename,
} from "../lib/format";
import { EvidencePanel } from "./EvidencePanel";

interface ResultsViewProps {
  result: AnalysisResult | null;
  images: ImageRecord[];
  selectedExperiment: Experiment | null;
  onOpenImage: (index: number) => void;
  onGoToWorkspace: () => void;
}

function previewFor(images: ImageRecord[], filename: string): string | null {
  return images.find((image) => image.filename === filename)?.preview_url ?? null;
}

export function ResultsView({ result, images, selectedExperiment, onOpenImage, onGoToWorkspace }: ResultsViewProps) {
  if (!result) {
    return (
      <section className="card empty-state" aria-labelledby="results-title">
        <h2 id="results-title">Résultats</h2>
        <p>
          {selectedExperiment
            ? `Aucune analyse terminée pour « ${selectedExperiment.name} ». Importez des images puis lancez un moteur.`
            : "Sélectionnez ou créez une expérience pour voir ses résultats."}
        </p>
        <button className="primary-button" type="button" onClick={onGoToWorkspace}>Aller à l’espace de travail</button>
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

  return (
    <div className="results">
      <section className="card" aria-labelledby="results-title">
        <div className="card-heading">
          <div>
            <h2 id="results-title">Résultats</h2>
            <p className="results-experiment">
              Expérience : {selectedExperiment?.name ?? result.experiment_id} · {result.engine.name} · pipeline {result.analysis_version} ·{" "}
              {new Date(result.generated_at).toLocaleString("fr-FR")}
            </p>
          </div>
          <div className="result-actions" aria-label="Exporter les résultats">
            <a className="secondary-button" href={experimentResultExportUrl(result.experiment_id, "json")}>Exporter JSON</a>
            <a className="secondary-button" href={experimentResultExportUrl(result.experiment_id, "csv")}>Exporter CSV</a>
          </div>
        </div>

        <div className="kpi-grid">
          {Object.entries(result.metrics).map(([key, value]) => (
            <div className={`kpi ${key === "object_count_total" ? "featured" : ""}`} key={key}>
              <span>{metricLabel(key)}</span>
              <strong>{formatMetric(key, value)}</strong>
              <small>{metricUnit(key)}</small>
            </div>
          ))}
        </div>
      </section>

      {result.task === "segmentation" ? (
        <section className="card" aria-labelledby="gallery-title">
          <div className="card-heading">
            <h2 id="gallery-title">Images segmentées</h2>
            <span className="card-meta">Cliquez une image pour l’agrandir et comparer avec l’original</span>
          </div>
          <ul className="gallery" aria-label="Overlays de segmentation">
            {segmentation.map((image, index) => (
              <li key={image.filename}>
                <button type="button" className="gallery-card" onClick={() => onOpenImage(index)}>
                  <img
                    src={`${image.overlay_url}?v=${version}`}
                    alt={`Segmentation de ${readableFilename(image.filename)}`}
                    loading="lazy"
                  />
                  <span className="gallery-caption">
                    <strong>{readableFilename(image.filename)}</strong>
                    <span>{formatInteger(image.object_count)} composantes · {formatPercent(image.foreground_fraction)} segmenté</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <details className="table-details">
            <summary>Tableau des mesures par image</summary>
            <div className="table-scroll">
              <table className="image-table">
                <caption>Composantes connexes du masque, pas des cellules validées</caption>
                <thead>
                  <tr>
                    <th scope="col">Image</th>
                    <th scope="col">Composantes</th>
                    <th scope="col">Surface segmentée</th>
                    <th scope="col">Aire moyenne (px²)</th>
                    <th scope="col">Aire médiane (px²)</th>
                    <th scope="col">Diamètre équivalent (px)</th>
                    <th scope="col">Seuil</th>
                    <th scope="col">Premier plan</th>
                  </tr>
                </thead>
                <tbody>
                  {segmentation.map((image) => (
                    <tr key={image.filename}>
                      <th scope="row">{readableFilename(image.filename)}</th>
                      <td>{formatInteger(image.object_count)}</td>
                      <td>{formatPercent(image.foreground_fraction)}</td>
                      <td>{formatDecimal(image.mean_object_area)}</td>
                      <td>{formatDecimal(image.median_object_area)}</td>
                      <td>{formatDecimal(image.mean_equivalent_diameter)}</td>
                      <td>{formatDecimal(image.threshold)}</td>
                      <td>{image.foreground_polarity === "bright" ? "clair" : "sombre"}</td>
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
            <h2 id="quality-title">Images évaluées</h2>
            <span className="card-meta">Softmax brut non calibré · aucune classe attribuée</span>
          </div>
          <ul className="gallery" aria-label="Images évaluées par le démonstrateur">
            {quality.map((image, index) => (
              <li key={image.filename}>
                <button type="button" className="gallery-card" onClick={() => onOpenImage(index)}>
                  {previewFor(images, image.filename) ? (
                    <img src={previewFor(images, image.filename) ?? undefined} alt={`Aperçu de ${readableFilename(image.filename)}`} loading="lazy" />
                  ) : (
                    <span className="gallery-placeholder" aria-hidden="true" />
                  )}
                  <span className="gallery-caption">
                    <strong>{readableFilename(image.filename)}</strong>
                    <span>
                      {image.probability_good_raw === null ? "Hors domaine · aucun score" : `Softmax brut « good » ${formatDecimal(image.probability_good_raw)} · non calibré`}
                    </span>
                    <span className="review-badge">À vérifier</span>
                    <span className="muted">{acquisitionModeLabels[image.source_acquisition_mode]}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <details className="card evidence-details" open>
        <summary>Niveau de preuve, limites et provenance</summary>
        <EvidencePanel result={result} />
      </details>
    </div>
  );
}
