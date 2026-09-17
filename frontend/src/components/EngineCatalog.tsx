import type { AnalysisEngine } from "../types";
import { engineKindLabels, engineStatusLabels } from "../lib/format";

interface EngineCatalogProps {
  engines: AnalysisEngine[];
  selectedEngineId: string;
}

export function EngineCatalog({ engines, selectedEngineId }: EngineCatalogProps) {
  return (
    <section className="engine-catalog" aria-labelledby="engine-catalog-title">
      <div className="engine-catalog-heading">
        <strong id="engine-catalog-title">Moteur actif et candidats</strong>
        <small>La maturité scientifique et la disponibilité technique sont affichées séparément.</small>
      </div>
      <div className="engine-catalog-list">
        {engines.map((engine) => (
          <article
            className={`engine-card ${engine.id === selectedEngineId ? "selected" : ""}`}
            key={engine.id}
          >
            <div className="engine-card-heading">
              <strong>{engine.name}</strong>
              <span className={`engine-status status-${engine.status}`}>
                {engineStatusLabels[engine.status]}
              </span>
            </div>
            <p>{engine.description}</p>
            <small className="engine-meta">
              {engineKindLabels[engine.kind]} ·{" "}
              {engine.training_required ? "entraînement requis" : "sans entraînement local"} ·{" "}
              {engine.runnable ? "exécutable" : "indisponible"}
            </small>
            {engine.unavailable_reason && (
              <small className="engine-unavailable">Indisponible : {engine.unavailable_reason}</small>
            )}
            <ul>
              {engine.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </article>
        ))}
        {engines.length === 0 && <p className="engine-catalog-empty">Registre indisponible.</p>}
      </div>
    </section>
  );
}
