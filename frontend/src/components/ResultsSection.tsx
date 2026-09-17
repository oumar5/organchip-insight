import type { AnalysisResult, Experiment } from "../types";
import { experimentResultExportUrl } from "../api/client";
import { formatMetric, metricLabel, metricUnit } from "../lib/format";
import { EvidencePanel } from "./EvidencePanel";
import { QualityResults } from "./QualityResults";
import { SegmentationResults } from "./SegmentationResults";

interface ResultsSectionProps {
  result: AnalysisResult | null;
  selectedExperiment: Experiment | null;
}

export function ResultsSection({ result, selectedExperiment }: ResultsSectionProps) {
  return (
    <section className="results-section" id="results" aria-labelledby="results-title">
      <div className="results-header">
        <div>
          <p className="section-kicker">Contrôle visuel obligatoire</p>
          <h2 id="results-title">Résultats et provenance</h2>
          {selectedExperiment && <p className="results-experiment">Expérience : {selectedExperiment.name}</p>}
        </div>
        {result && (
          <div className="result-meta">
            <span>Pipeline {result.analysis_version}</span>
            <span>{new Date(result.generated_at).toLocaleString("fr-FR")}</span>
            <div className="result-actions" aria-label="Exporter les résultats">
              <a href={experimentResultExportUrl(result.experiment_id, "json")}>Exporter JSON</a>
              <a href={experimentResultExportUrl(result.experiment_id, "csv")}>Exporter CSV</a>
            </div>
          </div>
        )}
      </div>

      {!result ? (
        <div className="empty-results">
          <div className="empty-visual" aria-hidden="true"><span /><span /><span /></div>
          <div>
            <h3>Les mesures apparaîtront ici</h3>
            <p>Lancez un moteur pour obtenir ses résultats, sa provenance et ses limites d’interprétation.</p>
          </div>
        </div>
      ) : (
        <div className="result-layout">
          <div className="result-main">
            <div className="metrics-grid">
              {Object.entries(result.metrics).map(([key, value]) => (
                <div className={`metric-card ${key === "object_count_total" ? "featured" : ""}`} key={key}>
                  <span>{metricLabel(key)}</span>
                  <strong>{formatMetric(key, value)}</strong>
                  <small>{metricUnit(key)}</small>
                </div>
              ))}
            </div>
            {result.task === "segmentation" ? (
              <SegmentationResults result={result} />
            ) : (
              <QualityResults result={result} />
            )}
          </div>
          <EvidencePanel result={result} />
        </div>
      )}
    </section>
  );
}
