import { useEffect, useMemo, useState } from "react";
import { getExperimentResults } from "../api/client";
import type { AnalysisResult, Experiment } from "../types";
import { formatDecimal, formatMetric, metricLabel, metricUnit } from "../lib/format";
import { useI18n } from "../i18n";

interface ExperimentComparisonProps {
  currentExperiment: Experiment;
  currentResult: AnalysisResult;
  experiments: Experiment[];
}

function contextLabel(experiment: Experiment, locale: "fr" | "en"): string {
  const values = [
    experiment.chip_id ? `${locale === "fr" ? "puce" : "chip"} ${experiment.chip_id}` : "",
    experiment.well_id ? `${locale === "fr" ? "puits" : "well"} ${experiment.well_id}` : "",
    experiment.cell_line,
    experiment.culture_day === null ? "" : `${locale === "fr" ? "jour" : "day"} ${experiment.culture_day}`,
  ].filter(Boolean);
  return values.join(" · ") || (locale === "fr" ? "contexte non renseigné" : "context not provided");
}

function calibratedMeanArea(result: AnalysisResult): number | null {
  const value = result.metrics.mean_object_area;
  const scale = result.experiment_metadata.microns_per_pixel;
  return value === undefined || scale === null ? null : value * scale ** 2;
}

export function ExperimentComparison({
  currentExperiment,
  currentResult,
  experiments,
}: ExperimentComparisonProps) {
  const { locale } = useI18n();
  const [comparisonId, setComparisonId] = useState("");
  const [comparisonResult, setComparisonResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const candidates = useMemo(
    () => experiments.filter((item) => item.id !== currentExperiment.id && item.status === "complete"),
    [currentExperiment.id, experiments],
  );
  const comparisonExperiment = candidates.find((item) => item.id === comparisonId) ?? null;

  useEffect(() => {
    setComparisonId("");
    setComparisonResult(null);
    setError(null);
  }, [currentExperiment.id]);

  useEffect(() => {
    let active = true;
    setComparisonResult(null);
    setError(null);
    if (!comparisonId) return () => { active = false; };
    setLoading(true);
    getExperimentResults(comparisonId)
      .then((value) => { if (active) setComparisonResult(value); })
      .catch((requestError: Error) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [comparisonId]);

  const compatible = comparisonResult?.task === currentResult.task;
  const metricKeys = comparisonResult && compatible
    ? Object.keys(currentResult.metrics).filter((key) => key in comparisonResult.metrics)
    : [];
  const currentPhysicalArea = calibratedMeanArea(currentResult);
  const comparisonPhysicalArea = comparisonResult ? calibratedMeanArea(comparisonResult) : null;

  return (
    <section className="card comparison-card" aria-labelledby="comparison-title">
      <div className="card-heading">
        <div>
          <h2 id="comparison-title">{locale === "fr" ? "Comparer deux expériences" : "Compare two experiments"}</h2>
          <p className="card-meta comparison-intro">
            {locale === "fr"
              ? "Comparaison descriptive des résultats terminés. Elle ne constitue pas un test biologique entre groupes."
              : "Descriptive comparison of completed results. This is not a biological between-group test."}
          </p>
        </div>
        <label className="comparison-select">
          {locale === "fr" ? "Seconde expérience" : "Second experiment"}
          <select value={comparisonId} onChange={(event) => setComparisonId(event.target.value)}>
            <option value="">{locale === "fr" ? "Choisir…" : "Choose…"}</option>
            {candidates.map((experiment) => (
              <option key={experiment.id} value={experiment.id}>{experiment.name}</option>
            ))}
          </select>
        </label>
      </div>

      {candidates.length === 0 && (
        <p className="muted">
          {locale === "fr"
            ? "Analysez une seconde expérience pour activer la comparaison."
            : "Analyze a second experiment to enable comparison."}
        </p>
      )}
      {loading && <p className="muted" role="status">{locale === "fr" ? "Chargement de la comparaison…" : "Loading comparison…"}</p>}
      {error && <p className="comparison-error" role="alert">{error}</p>}
      {comparisonResult && comparisonExperiment && !compatible && (
        <p className="comparison-error" role="alert">
          {locale === "fr"
            ? "Les deux analyses n’ont pas la même tâche ; leurs métriques ne sont pas comparables."
            : "The analyses have different tasks, so their metrics cannot be compared."}
        </p>
      )}
      {comparisonResult && comparisonExperiment && compatible && (
        <>
          {currentResult.engine.id !== comparisonResult.engine.id && (
            <p className="comparison-warning">
              {locale === "fr"
                ? "Attention : les résultats proviennent de moteurs différents."
                : "Caution: results were produced by different engines."}
            </p>
          )}
          <div className="comparison-contexts">
            <div><strong>{currentExperiment.name}</strong><span>{contextLabel(currentExperiment, locale)}</span></div>
            <div><strong>{comparisonExperiment.name}</strong><span>{contextLabel(comparisonExperiment, locale)}</span></div>
          </div>
          <div className="table-scroll">
            <table className="image-table comparison-table">
              <caption>{locale === "fr" ? "Métriques communes aux deux analyses" : "Metrics shared by both analyses"}</caption>
              <thead>
                <tr>
                  <th scope="col">{locale === "fr" ? "Mesure" : "Metric"}</th>
                  <th scope="col">{currentExperiment.name}</th>
                  <th scope="col">{comparisonExperiment.name}</th>
                </tr>
              </thead>
              <tbody>
                {metricKeys.map((key) => (
                  <tr key={key}>
                    <th scope="row">{metricLabel(key, locale)}{metricUnit(key, locale) ? ` (${metricUnit(key, locale)})` : ""}</th>
                    <td>{formatMetric(key, currentResult.metrics[key], locale)}</td>
                    <td>{formatMetric(key, comparisonResult.metrics[key], locale)}</td>
                  </tr>
                ))}
                {(currentPhysicalArea !== null || comparisonPhysicalArea !== null) && (
                  <tr>
                    <th scope="row">{locale === "fr" ? "Aire moyenne calibrée (µm²)" : "Calibrated mean area (µm²)"}</th>
                    <td>{currentPhysicalArea === null ? "—" : formatDecimal(currentPhysicalArea, locale)}</td>
                    <td>{comparisonPhysicalArea === null ? "—" : formatDecimal(comparisonPhysicalArea, locale)}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {(currentResult.experiment_metadata.microns_per_pixel === null || comparisonResult.experiment_metadata.microns_per_pixel === null) && currentResult.task === "segmentation" && (
            <p className="comparison-warning">
              {locale === "fr"
                ? "Au moins une expérience n’est pas calibrée : les aires en pixels ne sont comparables que si l’acquisition possède la même échelle."
                : "At least one experiment is uncalibrated: pixel areas are comparable only when acquisition scale is identical."}
            </p>
          )}
        </>
      )}
    </section>
  );
}
