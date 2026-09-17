import type { BenchmarkSummary } from "../types";
import { benchmarkText, formatBenchmarkInterval, formatBenchmarkMetric } from "../lib/format";
import { useI18n } from "../i18n";

interface BenchmarkSectionProps {
  summary: BenchmarkSummary | null;
}

export function BenchmarkSection({ summary }: BenchmarkSectionProps) {
  const { locale } = useI18n();
  return (
    <section className="benchmark-section" id="benchmarks" aria-labelledby="benchmarks-title">
      <div className="benchmark-header">
        <div>
          <p className="section-kicker">{locale === "fr" ? "Mesures externes versionnées" : "Versioned external measurements"}</p>
          <h2 id="benchmarks-title">{locale === "fr" ? "Comparaison des moteurs" : "Engine comparison"}</h2>
        </div>
        <span className="benchmark-source-badge">{locale === "fr" ? "Générée depuis les rapports" : "Generated from reports"}</span>
      </div>

      {summary ? (
        <>
          <div className="benchmark-grid">
            {summary.sections.map((section) => (
              <article className="benchmark-card" key={section.id}>
                <h3>{benchmarkText(section.title, locale)}</h3>
                <p className="benchmark-scope">{benchmarkText(section.scope, locale)}</p>
                <div className="benchmark-rows">
                  {section.rows.map((row) => (
                    <div className="benchmark-row" key={row.engine}>
                      <div className="benchmark-engine">
                        <strong>{row.engine}</strong>
                        <span>{benchmarkText(row.status, locale)}</span>
                      </div>
                      <dl>
                        {row.metrics.map((metric) => (
                          <div key={metric.label}>
                            <dt>{benchmarkText(metric.label, locale)}</dt>
                            <dd>{formatBenchmarkMetric(metric, locale)}</dd>
                            {metric.interval_95_percent && (
                              <small>{locale === "fr" ? "IC 95 %" : "95% CI"} {formatBenchmarkInterval(metric.interval_95_percent, locale)}</small>
                            )}
                          </div>
                        ))}
                      </dl>
                    </div>
                  ))}
                </div>
                <p className="benchmark-decision"><strong>{locale === "fr" ? "Décision :" : "Decision:"}</strong> {benchmarkText(section.decision, locale)}</p>
              </article>
            ))}
          </div>
          <details className="benchmark-provenance">
            <summary>{locale === "fr" ? "Provenance des chiffres" : "Metric provenance"}</summary>
            <ul>
              {summary.generated_from.map((source) => (
                <li key={source.path}>
                  <span>{source.path}</span>
                  <code>{source.sha256}</code>
                </li>
              ))}
            </ul>
          </details>
        </>
      ) : (
        <p className="benchmark-unavailable">{locale === "fr" ? "Synthèse des benchmarks indisponible." : "Benchmark summary unavailable."}</p>
      )}
    </section>
  );
}
