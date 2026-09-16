import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  analyzeExperiment,
  createExperiment,
  getExperimentResults,
  listExperiments,
  listInferenceEngines,
  uploadImages,
} from "./api/client";
import type {
  AnalysisEngine,
  AnalysisResult,
  Experiment,
  ExperimentCreate,
  ExperimentStatus,
} from "./types";

const initialForm: ExperimentCreate = {
  name: "",
  description: "",
  control_label: "Contrôle",
  treatment_label: "Traitement",
};

const metricLabels: Record<string, string> = {
  object_count_total: "Objets détectés",
  objects_per_image: "Objets / image",
  mean_foreground_fraction: "Surface segmentée",
  mean_object_area: "Surface moyenne",
  mean_intensity: "Intensité moyenne",
  mean_contrast: "Contraste moyen",
  quality_score: "Score qualité",
};

const statusLabels: Record<ExperimentStatus, string> = {
  draft: "Brouillon",
  ready: "Prêt",
  analyzing: "Analyse",
  complete: "Terminé",
  failed: "Échec",
};

function formatMetric(key: string, value: number): string {
  if (key === "mean_foreground_fraction" || key === "quality_score") {
    return `${(value * 100).toFixed(1)} %`;
  }
  if (key === "object_count_total") {
    return Math.round(value).toLocaleString("fr-FR");
  }
  return value.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

function readableFilename(filename: string): string {
  return filename.replace(/^[a-f0-9]{12}-/, "");
}

export default function App() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [engines, setEngines] = useState<AnalysisEngine[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEngineId, setSelectedEngineId] = useState("adaptive-segmentation-v1");
  const [form, setForm] = useState<ExperimentCreate>(initialForm);
  const [files, setFiles] = useState<FileList | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedExperiment = useMemo(
    () => experiments.find((experiment) => experiment.id === selectedId) ?? null,
    [experiments, selectedId],
  );
  const selectedEngine = useMemo(
    () => engines.find((engine) => engine.id === selectedEngineId) ?? null,
    [engines, selectedEngineId],
  );

  async function refreshExperiments(preferredId?: string) {
    const items = await listExperiments();
    setExperiments(items);
    setSelectedId((currentId) => preferredId ?? currentId ?? items[0]?.id ?? null);
  }

  useEffect(() => {
    Promise.all([refreshExperiments(), listInferenceEngines().then(setEngines)]).catch(
      (requestError: Error) => setError(requestError.message),
    );
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setResult(null);
      return;
    }
    getExperimentResults(selectedId)
      .then(setResult)
      .catch(() => setResult(null));
  }, [selectedId]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await createExperiment(form);
      setForm(initialForm);
      setResult(null);
      await refreshExperiments(created.id);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAnalyze() {
    if (!selectedExperiment) {
      setError("Créez ou sélectionnez une expérience avant l’analyse.");
      return;
    }
    const hasNewFiles = Boolean(files?.length);
    if (!hasNewFiles && selectedExperiment.image_count === 0) {
      setError("Ajoutez au moins une image de microscopie.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      if (files?.length) {
        await uploadImages(selectedExperiment.id, files);
      }
      const analysis = await analyzeExperiment(selectedExperiment.id, selectedEngineId);
      setResult(analysis);
      setFiles(null);
      await refreshExperiments(selectedExperiment.id);
      document.querySelector("#results")?.scrollIntoView({ behavior: "smooth" });
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
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
          <a className="nav-item active" href="#workspace">
            <span>01</span> Expérience
          </a>
          <a className="nav-item" href="#inference">
            <span>02</span> Inférence
          </a>
          <a className="nav-item" href="#results">
            <span>03</span> Résultats
          </a>
        </nav>

        <div className="sidebar-section">
          <div className="sidebar-heading">
            <span>Expériences</span>
            <span className="count-badge">{experiments.length}</span>
          </div>
          <div className="experiment-list">
            {experiments.length === 0 && (
              <p className="sidebar-empty">Votre première expérience apparaîtra ici.</p>
            )}
            {experiments.map((experiment) => (
              <button
                className={`experiment-item ${experiment.id === selectedId ? "selected" : ""}`}
                key={experiment.id}
                onClick={() => setSelectedId(experiment.id)}
                type="button"
              >
                <span className={`status-dot ${experiment.status}`} />
                <span className="experiment-copy">
                  <strong>{experiment.name}</strong>
                  <small>
                    {experiment.image_count} image{experiment.image_count > 1 ? "s" : ""}
                  </small>
                </span>
                <small>{statusLabels[experiment.status]}</small>
              </button>
            ))}
          </div>
        </div>

        <div className="trust-card">
          <span className="trust-icon">✓</span>
          <div>
            <strong>Données locales</strong>
            <p>Les images restent dans votre environnement.</p>
          </div>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">AI for life science · espace de travail</p>
            <h1>Transformer les images en preuves mesurables.</h1>
          </div>
          <div className="system-status">
            <span /> Inférence disponible
          </div>
        </header>

        {error && (
          <div className="alert" role="alert">
            <strong>Action interrompue</strong>
            <span>{error}</span>
            <button onClick={() => setError(null)} type="button" aria-label="Fermer">
              ×
            </button>
          </div>
        )}

        <section className="intro-strip" aria-label="Résumé du workflow">
          <div>
            <span className="intro-index">01</span>
            <p><strong>Définir</strong><small>Contexte et groupes</small></p>
          </div>
          <i />
          <div>
            <span className="intro-index">02</span>
            <p><strong>Segmenter</strong><small>Sans entraînement</small></p>
          </div>
          <i />
          <div>
            <span className="intro-index">03</span>
            <p><strong>Vérifier</strong><small>Overlays et métriques</small></p>
          </div>
          <div className="evidence-chip">Exploratoire · traçable</div>
        </section>

        <section className="workspace-grid" id="workspace">
          <article className="panel create-panel">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">Nouvelle étude</p>
                <h2>Cadre expérimental</h2>
              </div>
              <span className="panel-number">01</span>
            </div>

            <form onSubmit={handleCreate}>
              <label>
                Nom de l’expérience
                <input
                  required
                  minLength={2}
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  placeholder="Réponse au composé A"
                />
              </label>
              <label>
                Hypothèse ou objectif
                <textarea
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                  placeholder="Décrire la comparaison et le signal attendu…"
                />
              </label>
              <div className="two-columns">
                <label>
                  Groupe témoin
                  <input
                    value={form.control_label}
                    onChange={(event) => setForm({ ...form, control_label: event.target.value })}
                  />
                </label>
                <label>
                  Groupe traité
                  <input
                    value={form.treatment_label}
                    onChange={(event) => setForm({ ...form, treatment_label: event.target.value })}
                  />
                </label>
              </div>
              <button className="primary-button" disabled={busy} type="submit">
                Créer l’expérience <span>→</span>
              </button>
            </form>
          </article>

          <article className="panel inference-panel" id="inference">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">Analyse immédiate</p>
                <h2>Inférence sur vos images</h2>
              </div>
              <span className="panel-number">02</span>
            </div>

            <div className="field-grid">
              <label>
                Expérience active
                <select
                  value={selectedId ?? ""}
                  onChange={(event) => setSelectedId(event.target.value)}
                >
                  <option value="" disabled>Sélectionner une expérience</option>
                  {experiments.map((experiment) => (
                    <option key={experiment.id} value={experiment.id}>{experiment.name}</option>
                  ))}
                </select>
              </label>
              <label>
                Moteur
                <select
                  value={selectedEngineId}
                  onChange={(event) => setSelectedEngineId(event.target.value)}
                >
                  {engines.filter((engine) => engine.status === "available").map((engine) => (
                    <option key={engine.id} value={engine.id}>{engine.name}</option>
                  ))}
                </select>
              </label>
            </div>

            {selectedEngine && (
              <div className="engine-card">
                <div>
                  <span className="engine-pulse" />
                  <strong>{selectedEngine.name}</strong>
                  <small>Zéro entraînement</small>
                </div>
                <p>{selectedEngine.description}</p>
              </div>
            )}

            <label className="drop-zone">
              <span className="drop-icon" aria-hidden="true">⌁</span>
              <strong>Déposer les images de microscopie</strong>
              <small>PNG, JPEG ou TIFF · 25 Mo maximum par fichier</small>
              <span className="secondary-button">Choisir les fichiers</span>
              <input
                type="file"
                accept=".png,.jpg,.jpeg,.tif,.tiff"
                multiple
                onChange={(event) => setFiles(event.target.files)}
              />
            </label>

            {files?.length ? (
              <div className="file-list">
                {Array.from(files).slice(0, 3).map((file) => (
                  <div key={`${file.name}-${file.size}`}>
                    <span className="file-icon">IMG</span>
                    <p><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(2)} Mo</small></p>
                  </div>
                ))}
                {files.length > 3 && <small>+ {files.length - 3} autre(s) image(s)</small>}
              </div>
            ) : (
              selectedExperiment?.image_count ? (
                <p className="existing-files">✓ {selectedExperiment.image_count} image(s) déjà disponible(s)</p>
              ) : null
            )}

            <button
              className="primary-button analyze-button"
              disabled={busy || !selectedExperiment}
              onClick={handleAnalyze}
              type="button"
            >
              {busy ? <><span className="spinner" /> Analyse en cours…</> : <>Lancer l’inférence <span>→</span></>}
            </button>
          </article>
        </section>

        <section className="results-section" id="results">
          <div className="results-header">
            <div>
              <p className="section-kicker">Contrôle visuel obligatoire</p>
              <h2>Résultats et provenance</h2>
            </div>
            {result && (
              <div className="result-meta">
                <span>Pipeline {result.analysis_version}</span>
                <span>{new Date(result.generated_at).toLocaleString("fr-FR")}</span>
              </div>
            )}
          </div>

          {!result ? (
            <div className="empty-results">
              <div className="empty-visual"><span /><span /><span /></div>
              <div>
                <h3>Les preuves apparaîtront ici</h3>
                <p>Lancez l’inférence pour obtenir les contours, le comptage et les indicateurs qualité.</p>
              </div>
            </div>
          ) : (
            <div className="result-layout">
              <div className="result-main">
                <div className="metrics-grid">
                  {Object.entries(result.metrics).map(([key, value]) => (
                    <div className={`metric-card ${key === "object_count_total" ? "featured" : ""}`} key={key}>
                      <span>{metricLabels[key] ?? key}</span>
                      <strong>{formatMetric(key, value)}</strong>
                      <small>{key.includes("area") ? "pixels²" : key.includes("intensity") || key.includes("contrast") ? "échelle 0–1" : ""}</small>
                    </div>
                  ))}
                </div>

                <div className="overlay-grid">
                  {result.image_results.map((imageResult) => (
                    <figure key={imageResult.overlay_url}>
                      <img src={imageResult.overlay_url} alt={`Segmentation de ${readableFilename(imageResult.filename)}`} />
                      <figcaption>
                        <div><strong>{readableFilename(imageResult.filename)}</strong><span>{imageResult.object_count} objets</span></div>
                        <small>Premier plan {imageResult.foreground_polarity === "bright" ? "clair" : "sombre"} · seuil {imageResult.threshold}</small>
                      </figcaption>
                    </figure>
                  ))}
                </div>
              </div>

              <aside className="evidence-panel">
                <div className="evidence-title">
                  <span>i</span>
                  <div><strong>Niveau de preuve</strong><small>Exploration non validée</small></div>
                </div>
                <p>Ces mesures décrivent les images. Elles ne constituent ni un diagnostic ni une conclusion biologique.</p>
                <h3>Points à vérifier</h3>
                <ul>
                  {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                </ul>
                <div className="provenance-box">
                  <span>Moteur</span><strong>{result.engine.name}</strong>
                  <span>Images analysées</span><strong>{result.image_count}</strong>
                  <span>Entraînement local</span><strong>Aucun</strong>
                </div>
              </aside>
            </div>
          )}
        </section>

        <footer>
          <span>OrganChip Insight · prototype scientifique reproductible</span>
          <span>Aucune donnée clinique · aucune conclusion automatisée</span>
        </footer>
      </main>
    </div>
  );
}
