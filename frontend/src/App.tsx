import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  analyzeExperiment,
  createExperiment,
  getBenchmarkSummary,
  getExperimentResults,
  getUploadLimits,
  listExperiments,
  listImages,
  listInferenceEngines,
  uploadImage,
} from "./api/client";
import type {
  AnalysisEngine,
  AnalysisResult,
  BenchmarkSummary,
  Experiment,
  ExperimentCreate,
  ImageRecord,
  UploadLimits,
  UploadSummary,
} from "./types";
import { AppBar } from "./components/AppBar";
import type { Tab } from "./components/AppBar";
import { ExperimentRail } from "./components/ExperimentRail";
import { ExperimentDialog } from "./components/ExperimentDialog";
import { Stepper } from "./components/Stepper";
import type { StepState } from "./components/Stepper";
import { ImportPanel } from "./components/ImportPanel";
import { EngineSelector } from "./components/EngineSelector";
import { ResultsView } from "./components/ResultsView";
import { BenchmarkSection } from "./components/BenchmarkSection";
import { Lightbox } from "./components/Lightbox";
import type { LightboxItem } from "./components/Lightbox";
import { acquisitionModeLabels, formatDecimal, formatInteger, formatPercent, imageCountLabel, readableFilename } from "./lib/format";

const initialForm: ExperimentCreate = {
  name: "",
  description: "",
  control_label: "Contrôle",
  treatment_label: "Traitement",
};

export default function App() {
  const [tab, setTab] = useState<Tab>("workspace");
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [engines, setEngines] = useState<AnalysisEngine[]>([]);
  const [engineRegistryLoaded, setEngineRegistryLoaded] = useState(false);
  const [benchmarkSummary, setBenchmarkSummary] = useState<BenchmarkSummary | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEngineId, setSelectedEngineId] = useState("");
  const [form, setForm] = useState<ExperimentCreate>(initialForm);
  const [createOpen, setCreateOpen] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [images, setImages] = useState<ImageRecord[]>([]);
  const [uploadSummary, setUploadSummary] = useState<UploadSummary | null>(null);
  const [uploadLimits, setUploadLimits] = useState<UploadLimits | null>(null);
  const [uploadProgress, setUploadProgress] = useState<{ done: number; total: number } | null>(null);
  const [analysisStartedAt, setAnalysisStartedAt] = useState<number | null>(null);
  const [analysisElapsed, setAnalysisElapsed] = useState(0);
  const [lightbox, setLightbox] = useState<{ source: "images" | "results"; index: number } | null>(null);
  const requestToken = useRef(0);
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
  const statusKind = !engineRegistryLoaded ? "loading" : hasRunnableEngine ? "ready" : "unavailable";
  const statusLabel = !engineRegistryLoaded
    ? "Vérification de l’inférence…"
    : hasRunnableEngine
      ? "Inférence disponible"
      : "Inférence indisponible";

  const refreshExperiments = useCallback(async (preferredId?: string) => {
    const items = await listExperiments();
    setExperiments(items);
    setSelectedId((currentId) => preferredId ?? currentId ?? items[0]?.id ?? null);
  }, []);

  const refreshImages = useCallback(async (experimentId: string) => {
    const token = ++requestToken.current;
    const records = await listImages(experimentId).catch(() => [] as ImageRecord[]);
    if (token === requestToken.current) setImages(records);
  }, []);

  useEffect(() => {
    Promise.all([
      getUploadLimits().then(setUploadLimits),
      getBenchmarkSummary().then(setBenchmarkSummary).catch(() => setBenchmarkSummary(null)),
      refreshExperiments(),
      listInferenceEngines()
        .then((items) => {
          setEngines(items);
          setSelectedEngineId((currentId) => {
            const currentEngine = items.find((engine) => engine.id === currentId);
            if (currentEngine?.runnable) return currentId;
            return items.find((engine) => engine.runnable)?.id ?? "";
          });
        })
        .finally(() => setEngineRegistryLoaded(true)),
    ]).catch((requestError: Error) => setError(requestError.message));
  }, [refreshExperiments]);

  useEffect(() => {
    const token = ++requestToken.current;
    setResult(null);
    setImages([]);
    if (!selectedId) return;
    getExperimentResults(selectedId)
      .then((value) => { if (token === requestToken.current) setResult(value); })
      .catch(() => { if (token === requestToken.current) setResult(null); });
    listImages(selectedId)
      .then((records) => { if (token === requestToken.current) setImages(records); })
      .catch(() => { if (token === requestToken.current) setImages([]); });
    return () => { requestToken.current++; };
  }, [selectedId]);

  useEffect(() => {
    if (analysisStartedAt === null) { setAnalysisElapsed(0); return; }
    const timer = window.setInterval(() => setAnalysisElapsed(Math.round((Date.now() - analysisStartedAt) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [analysisStartedAt]);

  function selectExperiment(id: string) {
    if (id === selectedId) return;
    setSelectedId(id);
    setFiles([]);
    setUploadSummary(null);
    setError(null);
    setTab("workspace");
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await createExperiment(form);
      setForm(initialForm);
      setCreateOpen(false);
      setFiles([]);
      setUploadSummary(null);
      setSelectedId(created.id);
      setTab("workspace");
      await refreshExperiments(created.id);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload() {
    if (!selectedExperiment || !files.length || !uploadLimits) return;
    const pending = [...files];
    const summary: UploadSummary = {
      experiment_id: selectedExperiment.id,
      accepted_files: [],
      rejected_files: [],
      duplicate_files: [],
      rejection_reasons: {},
      total_images: selectedExperiment.image_count,
    };
    setBusy(true);
    setError(null);
    setUploadSummary(null);
    try {
      for (const [index, file] of pending.entries()) {
        setUploadProgress({ done: index, total: pending.length });
        if (file.size > uploadLimits.max_upload_bytes) {
          summary.rejected_files.push(file.name);
          summary.rejection_reasons[file.name] = "La taille dépasse la limite par image.";
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
      setUploadProgress({ done: pending.length, total: pending.length });
    } catch (requestError) {
      setError(`${(requestError as Error).message} Les imports déjà confirmés sont conservés ; reprenez les fichiers restants.`);
    } finally {
      setUploadProgress(null);
      try {
        await refreshExperiments(selectedExperiment.id);
        await refreshImages(selectedExperiment.id);
      } catch (requestError) {
        setError((requestError as Error).message);
      }
      setBusy(false);
    }
  }

  async function handleAnalyze() {
    if (!selectedExperiment) { setError("Créez ou sélectionnez une expérience avant l’analyse."); return; }
    if (!selectedEngine?.runnable) { setError("Sélectionnez un moteur exécutable avant l’analyse."); return; }
    if (files.length || selectedExperiment.image_count === 0) { setError("Importez les images sélectionnées avant de lancer l’analyse."); return; }
    setBusy(true);
    setError(null);
    setResult(null);
    setAnalysisStartedAt(Date.now());
    try {
      const analysis = await analyzeExperiment(selectedExperiment.id, selectedEngine.id);
      setResult(analysis);
      setTab("results");
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setAnalysisStartedAt(null);
      try { await refreshExperiments(selectedExperiment.id); } catch (requestError) { setError((requestError as Error).message); }
      setBusy(false);
    }
  }

  const steps: Array<{ label: string; hint: string; state: StepState }> = (() => {
    const hasImages = (selectedExperiment?.image_count ?? 0) > 0;
    const hasEngine = Boolean(selectedEngine?.runnable);
    const done = Boolean(result);
    return [
      { label: "Importer les images", hint: hasImages ? imageCountLabel(selectedExperiment?.image_count ?? 0) : "PNG, JPEG, TIFF", state: hasImages ? "done" : "current" },
      { label: "Choisir un moteur", hint: selectedEngine?.name ?? "aucun moteur", state: hasEngine ? (hasImages ? "done" : "todo") : hasImages ? "current" : "todo" },
      { label: "Analyser", hint: done ? "résultat disponible" : "puis vérifier les résultats", state: done ? "done" : hasImages && hasEngine ? "current" : "todo" },
    ];
  })();

  const lightboxItems: LightboxItem[] = useMemo(() => {
    if (!lightbox) return [];
    if (lightbox.source === "images") {
      return images.map((image) => ({
        title: image.display_name,
        original_url: image.preview_url,
        overlay_url: null,
        facts: [
          { label: "Format source", value: `${image.source_format} · ${image.source_mode} · ${image.source_bit_depth} bits/canal` },
          { label: "Dimensions", value: `${image.width} × ${image.height} px` },
          { label: "Taille", value: `${(image.size_bytes / 1024 / 1024).toFixed(2)} Mo` },
          { label: "Aperçu", value: "PNG 8 bits · affichage uniquement" },
          { label: "Analyse", value: "fichier source original" },
        ],
      }));
    }
    if (!result) return [];
    const version = encodeURIComponent(result.generated_at);
    return result.image_results.map((item) => {
      const sourceImage = images.find((image) => image.filename === item.filename);
      const original = sourceImage?.preview_url ?? null;
      const sourceFacts = sourceImage
        ? [
            { label: "Format source", value: `${sourceImage.source_format} · ${sourceImage.source_mode} · ${sourceImage.source_bit_depth} bits/canal` },
            { label: "Dimensions", value: `${sourceImage.width} × ${sourceImage.height} px` },
            { label: "Aperçu", value: "PNG 8 bits · affichage uniquement" },
            { label: "Analyse", value: "fichier source original" },
          ]
        : [];
      if (item.analysis_type === "segmentation") {
        return {
          title: readableFilename(item.filename),
          original_url: original,
          overlay_url: `${item.overlay_url}?v=${version}`,
          facts: [
            ...sourceFacts,
            { label: "Composantes connexes", value: formatInteger(item.object_count) },
            { label: "Surface segmentée", value: formatPercent(item.foreground_fraction) },
            { label: "Aire moyenne (px²)", value: formatDecimal(item.mean_object_area) },
            { label: "Diamètre équivalent (px)", value: formatDecimal(item.mean_equivalent_diameter) },
            { label: "Seuil", value: formatDecimal(item.threshold) },
            { label: "Premier plan", value: item.foreground_polarity === "bright" ? "clair" : "sombre" },
          ],
        };
      }
      return {
        title: readableFilename(item.filename),
        original_url: original,
        overlay_url: null,
        facts: [
          ...sourceFacts,
          { label: "Mode d’acquisition", value: acquisitionModeLabels[item.source_acquisition_mode] },
          { label: "Softmax brut « good » (non calibré)", value: item.probability_good_raw === null ? "non calculé" : formatDecimal(item.probability_good_raw) },
          { label: "Décision", value: "À vérifier · aucune classe attribuée" },
        ],
      };
    });
  }, [lightbox, images, result]);

  const analysisLabel = analysisStartedAt !== null && selectedExperiment
    ? `Analyse de ${imageCountLabel(selectedExperiment.image_count)} · ${analysisElapsed} s`
    : null;

  return (
    <div className="app">
      <AppBar tab={tab} onTab={setTab} statusKind={statusKind} statusLabel={statusLabel} resultAvailable={result !== null} />

      <div className="layout">
        <ExperimentRail
          experiments={experiments}
          selectedId={selectedId}
          busy={busy}
          onSelect={selectExperiment}
          onCreate={() => { setForm(initialForm); setCreateOpen(true); }}
        />

        <main className="content">
          {error && (
            <div className="alert" role="alert">
              <strong>Action interrompue</strong>
              <span>{error}</span>
              <button className="icon-button" onClick={() => setError(null)} type="button" aria-label="Fermer le message d’erreur">×</button>
            </div>
          )}

          {tab === "workspace" && (
            <>
              <div className="workspace-header">
                <div>
                  <label className="visually-hidden" htmlFor="active-experiment">Expérience active</label>
                  <select id="active-experiment" className="experiment-select" value={selectedId ?? ""} disabled={busy} onChange={(event) => selectExperiment(event.target.value)}>
                    <option value="" disabled>Sélectionner une expérience</option>
                    {experiments.map((experiment) => (
                      <option key={experiment.id} value={experiment.id}>{experiment.name}</option>
                    ))}
                  </select>
                  {selectedExperiment?.description && <p className="muted">{selectedExperiment.description}</p>}
                </div>
                <Stepper steps={steps} />
              </div>

              {!selectedExperiment ? (
                <section className="card empty-state">
                  <h2>Commencer</h2>
                  <p>Créez une expérience, déposez vos images de microscopie, choisissez un moteur et lancez l’analyse.</p>
                  <button className="primary-button" type="button" onClick={() => setCreateOpen(true)}>+ Nouvelle expérience</button>
                </section>
              ) : (
                <div className="workspace-grid">
                  <ImportPanel
                    files={files}
                    images={images}
                    uploadSummary={uploadSummary}
                    uploadLimits={uploadLimits}
                    uploadProgress={uploadProgress}
                    busy={busy}
                    onFilesChosen={(chosen) => { setFiles(chosen); setUploadSummary(null); }}
                    onUpload={handleUpload}
                    onOpenImage={(index) => setLightbox({ source: "images", index })}
                  />
                  <div className="workspace-side">
                    <EngineSelector engines={engines} selectedEngineId={selectedEngineId} busy={busy} onSelect={setSelectedEngineId} />
                    <section className="card launch-card">
                      <button
                        className="primary-button launch-button"
                        disabled={busy || !selectedExperiment.image_count || files.length > 0 || !selectedEngine?.runnable}
                        onClick={handleAnalyze}
                        type="button"
                      >
                        {analysisLabel ? <><span className="spinner" aria-hidden="true" /> {analysisLabel}</> : busy ? "Traitement en cours…" : "Lancer l’analyse"}
                      </button>
                      <p className="muted launch-hint" aria-live="polite">
                        {analysisLabel ?? (files.length > 0 ? "Importez d’abord les images sélectionnées." : selectedExperiment.image_count ? `${imageCountLabel(selectedExperiment.image_count)} prête${selectedExperiment.image_count > 1 ? "s" : ""} pour l’analyse.` : "Aucune image importée.")}
                      </p>
                    </section>
                  </div>
                </div>
              )}
            </>
          )}

          {tab === "results" && (
            <ResultsView
              result={result}
              images={images}
              selectedExperiment={selectedExperiment}
              onOpenImage={(index) => setLightbox({ source: "results", index })}
              onGoToWorkspace={() => setTab("workspace")}
            />
          )}

          {tab === "benchmarks" && <BenchmarkSection summary={benchmarkSummary} />}

          <footer>
            <span>OrganChip Insight · prototype scientifique reproductible</span>
            <span>Aucune donnée clinique · aucune conclusion automatisée</span>
          </footer>
        </main>
      </div>

      <ExperimentDialog open={createOpen} form={form} busy={busy} onChange={setForm} onSubmit={handleCreate} onClose={() => setCreateOpen(false)} />
      <Lightbox items={lightboxItems} index={lightbox?.index ?? null} onClose={() => setLightbox(null)} onNavigate={(index) => setLightbox((current) => (current ? { ...current, index } : null))} />
    </div>
  );
}
