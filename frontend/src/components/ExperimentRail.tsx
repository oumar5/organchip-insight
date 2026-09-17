import type { Experiment } from "../types";
import { imageCountLabel, statusLabel } from "../lib/format";
import { useI18n } from "../i18n";

interface ExperimentRailProps {
  experiments: Experiment[];
  selectedId: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

export function ExperimentRail({ experiments, selectedId, busy, onSelect, onCreate }: ExperimentRailProps) {
  const { locale } = useI18n();
  return (
    <aside className="rail" aria-label={locale === "fr" ? "Expériences" : "Experiments"}>
      <div className="rail-heading">
        <strong>{locale === "fr" ? "Expériences" : "Experiments"}</strong>
        <span className="count-badge">{experiments.length}</span>
      </div>
      <button className="primary-button rail-create" type="button" disabled={busy} onClick={onCreate}>
        {locale === "fr" ? "+ Nouvelle expérience" : "+ New experiment"}
      </button>
      <div className="experiment-list">
        {experiments.length === 0 && (
          <p className="rail-empty">{locale === "fr" ? "Créez une première expérience pour commencer." : "Create your first experiment to get started."}</p>
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
              <small>{imageCountLabel(experiment.image_count, locale)} · {statusLabel(experiment.status, locale)}</small>
            </span>
          </button>
        ))}
      </div>
      <p className="rail-footnote">{locale === "fr" ? "Données locales : les images restent dans l’environnement de déploiement." : "Local data: images remain in the deployment environment."}</p>
    </aside>
  );
}
