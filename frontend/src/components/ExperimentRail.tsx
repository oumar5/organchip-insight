import type { Experiment } from "../types";
import { imageCountLabel, statusLabels } from "../lib/format";

interface ExperimentRailProps {
  experiments: Experiment[];
  selectedId: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

export function ExperimentRail({ experiments, selectedId, busy, onSelect, onCreate }: ExperimentRailProps) {
  return (
    <aside className="rail" aria-label="Expériences">
      <div className="rail-heading">
        <strong>Expériences</strong>
        <span className="count-badge">{experiments.length}</span>
      </div>
      <button className="primary-button rail-create" type="button" disabled={busy} onClick={onCreate}>
        + Nouvelle expérience
      </button>
      <div className="experiment-list">
        {experiments.length === 0 && (
          <p className="rail-empty">Créez une première expérience pour commencer.</p>
        )}
        {experiments.map((experiment) => (
          <button
            className={`experiment-item ${experiment.id === selectedId ? "selected" : ""}`}
            key={experiment.id}
            onClick={() => onSelect(experiment.id)}
            disabled={busy}
            aria-current={experiment.id === selectedId ? "true" : undefined}
            type="button"
          >
            <span className={`status-dot ${experiment.status}`} aria-hidden="true" />
            <span className="experiment-copy">
              <strong>{experiment.name}</strong>
              <small>{imageCountLabel(experiment.image_count)} · {statusLabels[experiment.status]}</small>
            </span>
          </button>
        ))}
      </div>
      <p className="rail-footnote">Données locales : les images restent dans l’environnement de déploiement.</p>
    </aside>
  );
}
