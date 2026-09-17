import type { Experiment } from "../types";
import { imageCountLabel, statusLabels } from "../lib/format";

interface SidebarProps {
  experiments: Experiment[];
  selectedId: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
}

export function Sidebar({ experiments, selectedId, busy, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">
          <span />
        </div>
        <div>
          <strong>OrganChip</strong>
          <small>Insight</small>
        </div>
      </div>

      <nav aria-label="Navigation principale">
        <a className="nav-item" href="#workspace">
          <span>01</span> Expérience
        </a>
        <a className="nav-item" href="#inference">
          <span>02</span> Inférence
        </a>
        <a className="nav-item" href="#results">
          <span>03</span> Résultats
        </a>
        <a className="nav-item" href="#benchmarks">
          <span>04</span> Benchmarks
        </a>
      </nav>

      <div className="sidebar-section">
        <div className="sidebar-heading">
          <span>Expériences</span>
          <span className="count-badge">{experiments.length}</span>
        </div>
        <div className="experiment-list" role="list">
          {experiments.length === 0 && (
            <p className="sidebar-empty">Votre première expérience apparaîtra ici.</p>
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
                <small>{imageCountLabel(experiment.image_count)}</small>
              </span>
              <small>{statusLabels[experiment.status]}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="trust-card">
        <span className="trust-icon" aria-hidden="true">✓</span>
        <div>
          <strong>Données locales</strong>
          <p>Les images restent dans l’environnement où l’application est déployée.</p>
        </div>
      </div>
    </aside>
  );
}
