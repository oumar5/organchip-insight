import { useI18n } from "../i18n";

export type Tab = "workspace" | "results" | "benchmarks";

interface AppBarProps {
  tab: Tab;
  onTab: (tab: Tab) => void;
  statusKind: "loading" | "ready" | "unavailable";
  statusLabel: string;
  resultAvailable: boolean;
}

export function AppBar({ tab, onTab, statusKind, statusLabel, resultAvailable }: AppBarProps) {
  const { locale, setLocale, t } = useI18n();
  const tabs: Array<{ id: Tab; label: string }> = locale === "fr"
    ? [
        { id: "workspace", label: "Espace de travail" },
        { id: "results", label: "Résultats" },
        { id: "benchmarks", label: "Benchmarks" },
      ]
    : [
        { id: "workspace", label: "Workspace" },
        { id: "results", label: "Results" },
        { id: "benchmarks", label: "Benchmarks" },
      ];
  return (
    <header className="appbar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true" />
        <h1 className="brand-name">OrganChip <em>Insight</em></h1>
      </div>
      <nav className="tabs" aria-label={locale === "fr" ? "Sections" : "Sections"}>
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`tab ${tab === item.id ? "active" : ""}`}
            aria-current={tab === item.id ? "page" : undefined}
            onClick={() => onTab(item.id)}
          >
            {item.label}
            {item.id === "results" && resultAvailable && <span className="tab-dot" aria-label={locale === "fr" ? "résultat disponible" : "result available"} />}
          </button>
        ))}
      </nav>
      <div className="language-switch" role="group" aria-label={t("language.label")}>
        <button type="button" className={locale === "fr" ? "active" : ""} aria-pressed={locale === "fr"} onClick={() => setLocale("fr")}>FR</button>
        <button type="button" className={locale === "en" ? "active" : ""} aria-pressed={locale === "en"} onClick={() => setLocale("en")}>EN</button>
      </div>
      <div className={`system-status ${statusKind}`}>
        <span aria-hidden="true" /> {statusLabel}
      </div>
    </header>
  );
}
