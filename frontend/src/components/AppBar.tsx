export type Tab = "workspace" | "results" | "benchmarks";

interface AppBarProps {
  tab: Tab;
  onTab: (tab: Tab) => void;
  statusKind: "loading" | "ready" | "unavailable";
  statusLabel: string;
  resultAvailable: boolean;
}

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "workspace", label: "Espace de travail" },
  { id: "results", label: "Résultats" },
  { id: "benchmarks", label: "Benchmarks" },
];

export function AppBar({ tab, onTab, statusKind, statusLabel, resultAvailable }: AppBarProps) {
  return (
    <header className="appbar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-name">OrganChip <em>Insight</em></span>
      </div>
      <nav className="tabs" aria-label="Sections">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`tab ${tab === item.id ? "active" : ""}`}
            aria-current={tab === item.id ? "page" : undefined}
            onClick={() => onTab(item.id)}
          >
            {item.label}
            {item.id === "results" && resultAvailable && <span className="tab-dot" aria-label="résultat disponible" />}
          </button>
        ))}
      </nav>
      <div className={`system-status ${statusKind}`}>
        <span aria-hidden="true" /> {statusLabel}
      </div>
    </header>
  );
}
