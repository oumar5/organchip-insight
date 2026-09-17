import { useState } from "react";
import type { AnalysisEngine } from "../types";
import { engineKindLabels, engineStatusLabels } from "../lib/format";
import { Modal } from "./Modal";

interface EngineSelectorProps {
  engines: AnalysisEngine[];
  selectedEngineId: string;
  busy: boolean;
  onSelect: (id: string) => void;
}

export function EngineSelector({ engines, selectedEngineId, busy, onSelect }: EngineSelectorProps) {
  const [detailsId, setDetailsId] = useState<string | null>(null);
  const details = engines.find((engine) => engine.id === detailsId) ?? null;

  return (
    <section className="card" aria-labelledby="engine-title">
      <div className="card-heading">
        <h2 id="engine-title">Moteur</h2>
        <span className="card-meta">Maturité et disponibilité affichées séparément</span>
      </div>
      <div className="engine-grid" role="radiogroup" aria-labelledby="engine-title">
        {engines.map((engine) => {
          const selected = engine.id === selectedEngineId;
          return (
            <div className={`engine-option ${selected ? "selected" : ""} ${engine.runnable ? "" : "disabled"}`} key={engine.id}>
              <button
                type="button"
                role="radio"
                aria-checked={selected}
                disabled={busy || !engine.runnable}
                className="engine-choice"
                onClick={() => onSelect(engine.id)}
              >
                <span className="engine-name">{engine.name}</span>
                <span className={`engine-status status-${engine.status}`}>{engineStatusLabels[engine.status]}</span>
                <span className="engine-desc">{engine.description}</span>
                <span className="engine-meta">
                  {engineKindLabels[engine.kind]} · {engine.runnable ? "exécutable" : "indisponible"}
                </span>
              </button>
              <button type="button" className="link-button" onClick={() => setDetailsId(engine.id)}>
                Détails et limites
              </button>
            </div>
          );
        })}
        {engines.length === 0 && <p className="muted">Registre indisponible.</p>}
      </div>

      <Modal open={details !== null} title={details?.name ?? "Moteur"} onClose={() => setDetailsId(null)}>
        {details && (
          <div className="engine-details">
            <p>{details.description}</p>
            <dl className="kv">
              <dt>Statut</dt><dd>{engineStatusLabels[details.status]}</dd>
              <dt>Type</dt><dd>{engineKindLabels[details.kind]}</dd>
              <dt>Entraînement local</dt><dd>{details.training_required ? "requis" : "aucun"}</dd>
              <dt>Disponibilité</dt><dd>{details.runnable ? "exécutable ici" : `indisponible : ${details.unavailable_reason ?? "raison non précisée"}`}</dd>
            </dl>
            <h3>Limites connues</h3>
            <ul>
              {details.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
            </ul>
          </div>
        )}
      </Modal>
    </section>
  );
}
