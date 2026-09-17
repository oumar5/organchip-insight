import { useState } from "react";
import type { AnalysisEngine } from "../types";
import { engineKindLabel, engineStatusLabel, localizedEngine, localizedRuntimeText } from "../lib/format";
import { useI18n } from "../i18n";
import { Modal } from "./Modal";

interface EngineSelectorProps {
  engines: AnalysisEngine[];
  selectedEngineId: string;
  busy: boolean;
  onSelect: (id: string) => void;
}

export function EngineSelector({ engines, selectedEngineId, busy, onSelect }: EngineSelectorProps) {
  const { locale } = useI18n();
  const [detailsId, setDetailsId] = useState<string | null>(null);
  const details = engines.find((engine) => engine.id === detailsId) ?? null;
  const localizedDetails = details ? localizedEngine(details, locale) : null;

  return (
    <section className="card" aria-labelledby="engine-title">
      <div className="card-heading">
        <h2 id="engine-title">{locale === "fr" ? "Moteur" : "Engine"}</h2>
        <span className="card-meta">{locale === "fr" ? "Maturité et disponibilité affichées séparément" : "Maturity and availability shown separately"}</span>
      </div>
      <div className="engine-grid" role="radiogroup" aria-labelledby="engine-title">
        {engines.map((sourceEngine) => {
          const engine = localizedEngine(sourceEngine, locale);
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
                <span className={`engine-status status-${engine.status}`}>{engineStatusLabel(engine.status, locale)}</span>
                <span className="engine-desc">{engine.description}</span>
                <span className="engine-meta">
                  {engineKindLabel(engine.kind, locale)} · {engine.runnable ? (locale === "fr" ? "exécutable" : "runnable") : (locale === "fr" ? "indisponible" : "unavailable")}
                </span>
              </button>
              <button type="button" className="link-button" onClick={() => setDetailsId(engine.id)}>
                {locale === "fr" ? "Détails et limites" : "Details and limits"}
              </button>
            </div>
          );
        })}
        {engines.length === 0 && <p className="muted">{locale === "fr" ? "Registre indisponible." : "Registry unavailable."}</p>}
      </div>

      <Modal open={localizedDetails !== null} title={localizedDetails?.name ?? (locale === "fr" ? "Moteur" : "Engine")} onClose={() => setDetailsId(null)}>
        {localizedDetails && (
          <div className="engine-details">
            <p>{localizedDetails.description}</p>
            <dl className="kv">
              <dt>{locale === "fr" ? "Statut" : "Status"}</dt><dd>{engineStatusLabel(localizedDetails.status, locale)}</dd>
              <dt>{locale === "fr" ? "Type" : "Type"}</dt><dd>{engineKindLabel(localizedDetails.kind, locale)}</dd>
              <dt>{locale === "fr" ? "Entraînement local" : "Local training"}</dt><dd>{localizedDetails.training_required ? (locale === "fr" ? "requis" : "required") : (locale === "fr" ? "aucun" : "none")}</dd>
              <dt>{locale === "fr" ? "Disponibilité" : "Availability"}</dt><dd>{localizedDetails.runnable ? (locale === "fr" ? "exécutable ici" : "runnable here") : `${locale === "fr" ? "indisponible" : "unavailable"} : ${localizedRuntimeText(localizedDetails.unavailable_reason ?? (locale === "fr" ? "raison non précisée" : "reason not specified"), locale)}`}</dd>
            </dl>
            <h3>{locale === "fr" ? "Limites connues" : "Known limitations"}</h3>
            <ul>
              {localizedDetails.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
            </ul>
          </div>
        )}
      </Modal>
    </section>
  );
}
