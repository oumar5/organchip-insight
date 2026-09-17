import type { BenchmarkSummary } from "../types";
import { formatBenchmarkInterval, formatBenchmarkMetric } from "../lib/format";

interface BenchmarkSectionProps {
  summary: BenchmarkSummary | null;
}

export function BenchmarkSection({ summary }: BenchmarkSectionProps) {
  return (
    <section className="benchmark-section" id="benchmarks" aria-labelledby="benchmarks-title">
      <div className="benchmark-header">
        <div>
          <p className="section-kicker">Mesures externes versionnées</p>
          <h2 id="benchmarks-title">Comparaison des moteurs</h2>
        </div>
        <span className="benchmark-source-badge">Générée depuis les rapports</span>
      </div>

      {summary ? (
        <>
          <div className="benchmark-grid">
            {summary.sections.map((section) => (
              <article className="benchmark-card" key={section.id}>
                <h3>{section.title}</h3>
                <p className="benchmark-scope">{section.scope}</p>
                <div className="benchmark-rows">
                  {section.rows.map((row) => (
                    <div className="benchmark-row" key={row.engine}>
                      <div className="benchmark-engine">
                        <strong>{row.engine}</strong>
                        <span>{row.status}</span>
                      </div>
                      <dl>
                        {row.metrics.map((metric) => (
                          <div key={metric.label}>
                            <dt>{metric.label}</dt>
                            <dd>{formatBenchmarkMetric(metric)}</dd>
                            {metric.interval_95_percent && (
                              <small>IC 95 % {formatBenchmarkInterval(metric.interval_95_percent)}</small>
                            )}
                          </div>
                        ))}
                      </dl>
                    </div>
                  ))}
                </div>
                <p className="benchmark-decision"><strong>Décision :</strong> {section.decision}</p>
              </article>
            ))}
          </div>
          <details className="benchmark-provenance">
            <summary>Provenance des chiffres</summary>
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
        <p className="benchmark-unavailable">Synthèse des benchmarks indisponible.</p>
      )}
    </section>
  );
}
