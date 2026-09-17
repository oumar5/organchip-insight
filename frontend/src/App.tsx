import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  analyzeExperiment,
  createExperiment,
  experimentResultExportUrl,
  getBenchmarkSummary,
  getExperimentResults,
  listExperiments,
  listInferenceEngines,
  uploadImage,
  getUploadLimits,
} from "./api/client";
import type {
  AnalysisEngine,
  AnalysisResult,
  BenchmarkMetric,
  BenchmarkSummary,
  Experiment,
  ExperimentCreate,
  ExperimentStatus,
  KnownMetricKey,
  UploadSummary,
  UploadLimits,
} from "./types";

const initialForm: ExperimentCreate = {
  name: "",
  description: "",
  control_label: "Contrôle",
  treatment_label: "Traitement",
};

type MetricFormat = "decimal" | "integer" | "percent" | "relative-index";

interface MetricPresentation {
  label: string;
  format: MetricFormat;
  unit?: string;
}

const metricPresentations: Record<KnownMetricKey, MetricPresentation> = {
  object_count_total: { label: "Composantes connexes", format: "integer" },
  objects_per_image: { label: "Composantes / image", format: "decimal" },
  mean_foreground_fraction: { label: "Surface segmentée", format: "percent" },
  mean_object_area: { label: "Surface moyenne", format: "decimal", unit: "pixels²" },
  mean_intensity: { label: "Intensité moyenne", format: "decimal", unit: "échelle 0–1" },
  mean_contrast: { label: "Contraste moyen", format: "decimal", unit: "échelle 0–1" },
  quality_score: {
    label: "Indice de contraste relatif",
    format: "relative-index",
    unit: "heuristique 0–1 · pas une probabilité",
  },
  images_with_raw_score: { label: "Images avec softmax brut", format: "integer" },
  images_outside_training_domain: { label: "Images hors domaine", format: "integer" },
};

const decimalFormatter = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });
const relativeIndexFormatter = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const percentFormatter = new Intl.NumberFormat("fr-FR", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const statusLabels: Record<ExperimentStatus, string> = {
  draft: "Brouillon",
  ready: "Prêt",
  analyzing: "Analyse",
  complete: "Terminé",
  failed: "Échec",
};

const engineStatusLabels: Record<AnalysisEngine["status"], string> = {
  available: "Disponible",
  experimental: "Expérimental",
  planned: "Planifié",
  "license-review": "Revue de licence",
};

const engineKindLabels: Record<AnalysisEngine["kind"], string> = {
  "zero-training": "Pipeline déterministe",
  pretrained: "Modèle préentraîné",
  trained: "Modèle entraîné",
};

function formatMetric(key: string, value: number): string {
  const presentation = metricPresentations[key as KnownMetricKey];
  switch (presentation?.format) {
    case "integer":
      return Math.round(value).toLocaleString("fr-FR");
    case "percent":
      return percentFormatter.format(value);
    case "relative-index":
      return relativeIndexFormatter.format(value);
    default:
      return decimalFormatter.format(value);
  }
}

function readableFilename(filename: string): string {
  return filename.replace(/^[a-f0-9]{12}-/, "");
}

function formatBenchmarkMetric(metric: BenchmarkMetric): string {
  if (metric.format === "percent") {
    return percentFormatter.format(metric.value);
  }
  if (metric.format === "seconds") {
    return `${decimalFormatter.format(metric.value)} s`;
  }
  if (metric.format === "megabytes") {
    return `${Math.round(metric.value).toLocaleString("fr-FR")} Mo`;
  }
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  }).format(metric.value);
}

function formatBenchmarkInterval(interval: [number, number]): string {
  const formatter = new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });
  return `[${formatter.format(interval[0])} ; ${formatter.format(interval[1])}]`;
}

export default function App() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [engines, setEngines] = useState<AnalysisEngine[]>([]);
  const [benchmarkSummary, setBenchmarkSummary] = useState<BenchmarkSummary | null>(null);
  const [engineRegistryLoaded, setEngineRegistryLoaded] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEngineId, setSelectedEngineId] = useState("");
  const [form, setForm] = useState<ExperimentCreate>(initialForm);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadSummary, setUploadSummary] = useState<UploadSummary | null>(null);
  const [uploadLimits, setUploadLimits] = useState<UploadLimits | null>(null);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const resultRequest = useRef(0);
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
  const hasRunnableEngine = engines.some((engine) => engine.runnable);
  const inferenceStatus = !engineRegistryLoaded
    ? "loading"
    : hasRunnableEngine
      ? "ready"
      : "unavailable";
  const inferenceStatusLabel = !engineRegistryLoaded
    ? "Vérification de l’inférence…"
    : hasRunnableEngine
      ? "Inférence disponible"
      : "Inférence indisponible";

  async function refreshExperiments(preferredId?: string) {
    const items = await listExperiments();
    setExperiments(items);
    setSelectedId((currentId) => preferredId ?? currentId ?? items[0]?.id ?? null);
  }

  useEffect(() => {
    Promise.all([
      getUploadLimits().then(setUploadLimits),
      getBenchmarkSummary().then(setBenchmarkSummary),
      refreshExperiments(),
      listInferenceEngines()
        .then((items) => {
          setEngines(items);
          setSelectedEngineId((currentId) => {
            const currentEngine = items.find((engine) => engine.id === currentId);
            if (currentEngine?.runnable) {
              return currentId;
            }
            return items.find((engine) => engine.runnable)?.id ?? "";
          });
        })
        .finally(() => setEngineRegistryLoaded(true)),
    ]).catch((requestError: Error) => setError(requestError.message));
  }, []);

  useEffect(() => {
    const requestId = ++resultRequest.current;
    setResult(null);
    if (!selectedId) {
      return;
    }
    getExperimentResults(selectedId)
      .then((value) => { if (requestId === resultRequest.current) setResult(value); })
      .catch(() => { if (requestId === resultRequest.current) setResult(null); });
    return () => { resultRequest.current++; };
  }, [selectedId]);

  function selectExperiment(id: string) {
    if (id === selectedId) return;
    resultRequest.current++;
    setSelectedId(id);
    setResult(null);
    setFiles([]);
    setUploadSummary(null);
    setError(null);
  }

  async function handleUpload() {
    if (!selectedExperiment || !files.length || !uploadLimits) return;
    const pending = [...files];
    const summary: UploadSummary = {
      experiment_id: selectedExperiment.id, accepted_files: [], rejected_files: [],
      duplicate_files: [], rejection_reasons: {}, total_images: selectedExperiment.image_count,
    };
    setBusy(true);
    setError(null);
    setUploadSummary(null);
    resultRequest.current++;
    try {
      for (const [index, file] of pending.entries()) {
        setUploadProgress(`Import ${index + 1} / ${pending.length}`);
        if (file.size > uploadLimits.max_upload_bytes) {
          summary.rejected_files.push(file.name);
          summary.rejection_reasons[file.name] = "La taille dépasse la limite par fichier.";
        } else {
          const current = await uploadImage(selectedExperiment.id, file);
          summary.accepted_files.push(...current.accepted_files);
          summary.rejected_files.push(...current.rejected_files);
          summary.duplicate_files.push(...current.duplicate_files);
          Object.assign(summary.rejection_reasons, current.rejection_reasons);
          summary.total_images = current.total_images;
          if (current.accepted_files.length) setResult(null);
        }
        setFiles(pending.slice(index + 1));
        setUploadSummary({ ...summary });
      }
    } catch (requestError) {
      setError(`${(requestError as Error).message} Les imports déjà confirmés sont conservés. Vous pouvez reprendre les fichiers restants.`);
    } finally {
      setUploadProgress(null);
      try { await refreshExperiments(selectedExperiment.id); }
      catch (requestError) { setError((requestError as Error).message); }
      setBusy(false);
    }
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await createExperiment(form);
      selectExperiment(created.id);
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
    if (!selectedEngine?.runnable) {
      setError("Sélectionnez un moteur disponible avant l’analyse.");
      return;
    }
    if (files.length || selectedExperiment.image_count === 0) {
      setError("Importez les images sélectionnées avant de lancer l’analyse.");
      return;
    }

    setBusy(true);
    setError(null);
    resultRequest.current++;
    setResult(null);
    try {
      const analysis = await analyzeExperiment(selectedExperiment.id, selectedEngine.id);
      setResult(analysis);
      document.querySelector("#results")?.scrollIntoView({ behavior: "smooth" });
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      try { await refreshExperiments(selectedExperiment.id); }
      catch (requestError) { setError((requestError as Error).message); }
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
          <a className="nav-item" href="#benchmarks">
            <span>04</span> Benchmarks
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
                onClick={() => selectExperiment(experiment.id)}
                disabled={busy}
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
          <div className={`system-status ${inferenceStatus}`}>
            <span /> {inferenceStatusLabel}
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
            <p><strong>Analyser</strong><small>Moteur explicite</small></p>
          </div>
          <i />
          <div>
            <span className="intro-index">03</span>
            <p><strong>Vérifier</strong><small>Preuves et limites</small></p>
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
                  maxLength={120}
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  placeholder="Réponse au composé A"
                />
              </label>
              <label>
                Hypothèse ou objectif
                <textarea
                  maxLength={1000}
                  value={form.description}
                  onChange={(event) => setForm({ ...form, description: event.target.value })}
                  placeholder="Décrire la comparaison et le signal attendu…"
                />
              </label>
              <p className="form-scope-note">
                L’affectation témoin/traitement est masquée tant que chaque image ne peut pas être
                rattachée explicitement à un groupe expérimental.
              </p>
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
                  disabled={busy}
                  onChange={(event) => selectExperiment(event.target.value)}
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
                  disabled={busy}
                  onChange={(event) => setSelectedEngineId(event.target.value)}
                >
                  {!engines.some((engine) => engine.runnable) && (
                    <option value="">Aucun moteur disponible</option>
                  )}
                  {engines.filter((engine) => engine.runnable).map((engine) => (
                    <option
                      key={engine.id}
                      value={engine.id}
                    >
                      {engine.name} — {engineStatusLabels[engine.status]}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <section className="engine-catalog" aria-labelledby="engine-catalog-title">
              <div className="engine-catalog-heading">
                <strong id="engine-catalog-title">Moteur actif et candidats</strong>
                <small>La maturité scientifique et la disponibilité technique sont affichées séparément.</small>
              </div>
              <div className="engine-catalog-list">
                {engines.map((engine) => (
                  <article
                    className={`engine-card ${engine.id === selectedEngineId ? "selected" : ""}`}
                    key={engine.id}
                  >
                    <div className="engine-card-heading">
                      <strong>{engine.name}</strong>
                      <span className={`engine-status status-${engine.status}`}>
                        {engineStatusLabels[engine.status]}
                      </span>
                    </div>
                    <p>{engine.description}</p>
                    <small className="engine-meta">
                      {engineKindLabels[engine.kind]} · {engine.training_required ? "entraînement requis" : "sans entraînement local"} · {engine.runnable ? "exécutable" : "indisponible"}
                    </small>
                    {engine.unavailable_reason && (
                      <small className="engine-unavailable">Indisponible : {engine.unavailable_reason}</small>
                    )}
                    <ul>
                      {engine.limitations.map((limitation) => (
                        <li key={limitation}>{limitation}</li>
                      ))}
                    </ul>
                  </article>
                ))}
                {engines.length === 0 && (
                  <p className="engine-catalog-empty">Registre indisponible.</p>
                )}
              </div>
            </section>

            <label className="drop-zone">
              <span className="drop-icon" aria-hidden="true">⌁</span>
              <strong>Sélectionner les images de microscopie</strong>
              <small>PNG, JPEG ou TIFF monopage · couleur 8 bits ou gris 8/16 bits</small>
              <small>{uploadLimits ? `${uploadLimits.max_upload_bytes / 1024 / 1024} Mio par fichier · ${(uploadLimits.max_image_pixels / 1_000_000).toFixed(1)} mégapixels maximum` : "Chargement des limites d’import…"}</small>
              <span className="secondary-button">Choisir les fichiers</span>
              <input
                type="file"
                accept=".png,.jpg,.jpeg,.tif,.tiff"
                multiple
                disabled={busy}
                onChange={(event) => {
                  setFiles(Array.from(event.target.files ?? []));
                  setUploadSummary(null);
                  event.target.value = "";
                }}
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

            {uploadSummary && (
              <div className="upload-summary" role="status">
                <strong>{uploadSummary.accepted_files.length} importé(s) · {uploadSummary.duplicate_files.length} déjà présent(s) · {uploadSummary.rejected_files.length} rejeté(s)</strong>
                {uploadSummary.rejected_files.length > 0 && <ul>{uploadSummary.rejected_files.map((name, index) => <li key={`${name}-${index}`}>{name} : {uploadSummary.rejection_reasons[name] ?? "Fichier non pris en charge."}</li>)}</ul>}
              </div>
            )}

            <button
              className="secondary-button upload-button"
              disabled={busy || !selectedExperiment || !files.length || !uploadLimits}
              onClick={handleUpload}
              type="button"
            >
              {uploadProgress ?? `Importer les images${files.length ? ` (${files.length})` : ""}`}
            </button>
            {files.length > 0 && <p className="existing-files">Les fichiers sélectionnés doivent être importés avant l’analyse.</p>}

            <button
              className="primary-button analyze-button"
              disabled={busy || !selectedExperiment?.image_count || files.length > 0 || !selectedEngine?.runnable}
              onClick={handleAnalyze}
              type="button"
            >
              {busy && !uploadProgress ? <><span className="spinner" /> Traitement en cours…</> : <>Lancer l’inférence <span>→</span></>}
            </button>
          </article>
        </section>

        <section className="results-section" id="results">
          <div className="results-header">
            <div>
              <p className="section-kicker">Contrôle visuel obligatoire</p>
              <h2>Résultats et provenance</h2>
              {selectedExperiment && <p>Expérience : {selectedExperiment.name}</p>}
            </div>
            {result && (
              <div className="result-meta">
                <span>Pipeline {result.analysis_version}</span>
                <span>{new Date(result.generated_at).toLocaleString("fr-FR")}</span>
                <div className="result-actions" aria-label="Exporter les résultats">
                  <a href={experimentResultExportUrl(result.experiment_id, "json")}>Exporter JSON</a>
                  <a href={experimentResultExportUrl(result.experiment_id, "csv")}>Exporter CSV</a>
                </div>
              </div>
            )}
          </div>

          {!result ? (
            <div className="empty-results">
              <div className="empty-visual"><span /><span /><span /></div>
              <div>
                <h3>Les preuves apparaîtront ici</h3>
                <p>Lancez un moteur pour obtenir ses résultats, sa provenance et ses limites d’interprétation.</p>
              </div>
            </div>
          ) : (
            <div className="result-layout">
              <div className="result-main">
                <div className="metrics-grid">
                  {Object.entries(result.metrics).map(([key, value]) => (
                    <div className={`metric-card ${key === "object_count_total" ? "featured" : ""}`} key={key}>
                      <span>{metricPresentations[key as KnownMetricKey]?.label ?? key}</span>
                      <strong>{formatMetric(key, value)}</strong>
                      <small>{metricPresentations[key as KnownMetricKey]?.unit ?? ""}</small>
                    </div>
                  ))}
                </div>

                {result.task === "segmentation" ? (
                  <div className="overlay-grid">
                    {result.image_results.filter((item) => item.analysis_type === "segmentation").map((imageResult) => (
                      <figure key={imageResult.overlay_url}>
                        <img src={`${imageResult.overlay_url}?v=${encodeURIComponent(result.generated_at)}`} alt={`Segmentation de ${readableFilename(imageResult.filename)}`} />
                        <figcaption>
                          <div><strong>{readableFilename(imageResult.filename)}</strong><span>{imageResult.object_count} objets</span></div>
                          <small>Premier plan {imageResult.foreground_polarity === "bright" ? "clair" : "sombre"} · seuil {imageResult.threshold}</small>
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                ) : (
                  <div className="quality-result-list">
                    {result.image_results.filter((item) => item.analysis_type === "quality-classification").map((imageResult) => (
                      <article className="quality-result-card" key={imageResult.filename}>
                        <div>
                          <strong>{readableFilename(imageResult.filename)}</strong>
                          <small>Mode source : {imageResult.source_acquisition_mode}</small>
                        </div>
                        <div className="raw-score">
                          <span>Softmax brut « good »</span>
                          <strong>{imageResult.probability_good_raw === null ? "Non calculé" : decimalFormatter.format(imageResult.probability_good_raw)}</strong>
                          <small>Non calibré · aucune classe attribuée</small>
                        </div>
                        <span className="review-badge">À vérifier</span>
                      </article>
                    ))}
                  </div>
                )}
              </div>

              <aside className="evidence-panel">
                <div className="evidence-title">
                  <span>i</span>
                  <div><strong>Niveau de preuve</strong><small>Exploration non validée</small></div>
                </div>
                {result.task === "quality-classification" ? (
                  <p><strong>Abstention systématique :</strong> ce démonstrateur n’attribue jamais automatiquement les classes bon ou mauvais. Le score affiché est un softmax brut non calibré.</p>
                ) : (
                  <p>Ces mesures décrivent les images. Elles ne constituent ni un diagnostic ni une conclusion biologique.</p>
                )}
                {typeof result.metrics.quality_score === "number" && (
                  <p className="metric-method-note">
                    <strong>Indice de contraste relatif :</strong> moyenne du contraste divisée par 0,20,
                    puis plafonnée à 1. Il ne mesure ni l’exactitude de la segmentation ni une qualité biologique.
                  </p>
                )}
                {result.task === "segmentation" && (
                  <p className="metric-method-note">
                    <strong>Comptage :</strong> chaque élément correspond à une composante connexe
                    du masque. Il n’est pas validé comme cellule ou noyau sur les images OoC.
                  </p>
                )}
                <h3>Points à vérifier</h3>
                <ul>
                  {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                </ul>
                <div className="provenance-box">
                  <span>Moteur</span><strong>{result.engine.name}</strong>
                  <span>Images analysées</span><strong>{result.image_count}</strong>
                  <span>Tâche</span><strong>{result.task === "segmentation" ? "Segmentation" : "QC expérimental"}</strong>
                  {Object.entries(result.provenance).map(([key, value]) => (
                    <div className="provenance-entry" key={key}>
                      <span>{key}</span><code>{value}</code>
                    </div>
                  ))}
                </div>
              </aside>
            </div>
          )}
        </section>

        <section className="benchmark-section" id="benchmarks" aria-labelledby="benchmarks-title">
          <div className="benchmark-header">
            <div>
              <p className="section-kicker">Preuves externes versionnées</p>
              <h2 id="benchmarks-title">Comparaison des moteurs</h2>
            </div>
            <span className="benchmark-source-badge">Générée depuis les rapports</span>
          </div>

          {benchmarkSummary ? (
            <>
              <div className="benchmark-grid">
                {benchmarkSummary.sections.map((section) => (
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
                                  <small>
                                    IC 95 % {formatBenchmarkInterval(metric.interval_95_percent)}
                                  </small>
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
                  {benchmarkSummary.generated_from.map((source) => (
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

        <footer>
          <span>OrganChip Insight · prototype scientifique reproductible</span>
          <span>Aucune donnée clinique · aucune conclusion automatisée</span>
        </footer>
      </main>
    </div>
  );
}
