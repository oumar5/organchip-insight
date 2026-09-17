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
  updateExperimentMetadata,
  uploadImage,
} from "./api/client";
import type {
  AnalysisEngine,
  AnalysisResult,
  BenchmarkSummary,
  Experiment,
  ExperimentCreate,
  ExperimentMetadata,
  ImageRecord,
  UploadLimits,
  UploadSummary,
} from "./types";
import { AppBar } from "./components/AppBar";
import type { Tab } from "./components/AppBar";
import { ExperimentRail } from "./components/ExperimentRail";
import { ExperimentDialog } from "./components/ExperimentDialog";
import { ExperimentMetadataDialog } from "./components/ExperimentMetadataDialog";
import { Stepper } from "./components/Stepper";
import type { StepState } from "./components/Stepper";
import { ImportPanel } from "./components/ImportPanel";
import { EngineSelector } from "./components/EngineSelector";
import { ResultsView } from "./components/ResultsView";
import { BenchmarkSection } from "./components/BenchmarkSection";
import { Lightbox } from "./components/Lightbox";
import type { LightboxItem } from "./components/Lightbox";
import { acquisitionModeLabel, formatDecimal, formatInteger, formatPercent, imageCountLabel, localizedEngine, localizedRuntimeText, readableFilename } from "./lib/format";
import { useI18n } from "./i18n";
import type { Locale } from "./i18n";

function initialForm(locale: Locale): ExperimentCreate {
  return {
    name: "",
    description: "",
    control_label: locale === "fr" ? "Contrôle" : "Control",
    treatment_label: locale === "fr" ? "Traitement" : "Treatment",
    chip_id: "",
    well_id: "",
    cell_line: "",
    culture_day: null,
    microns_per_pixel: null,
    calibration_source: "",
  };
}

function metadataFromExperiment(experiment: Experiment): ExperimentMetadata {
  return {
    chip_id: experiment.chip_id,
    well_id: experiment.well_id,
    cell_line: experiment.cell_line,
    culture_day: experiment.culture_day,
    microns_per_pixel: experiment.microns_per_pixel,
    calibration_source: experiment.calibration_source,
  };
}

const EMPTY_METADATA: ExperimentMetadata = {
  chip_id: "",
  well_id: "",
  cell_line: "",
  culture_day: null,
  microns_per_pixel: null,
  calibration_source: "",
};

export default function App() {
  const { locale } = useI18n();
  const [tab, setTab] = useState<Tab>("workspace");
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [engines, setEngines] = useState<AnalysisEngine[]>([]);
  const [engineRegistryLoaded, setEngineRegistryLoaded] = useState(false);
  const [benchmarkSummary, setBenchmarkSummary] = useState<BenchmarkSummary | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEngineId, setSelectedEngineId] = useState("");
  const [form, setForm] = useState<ExperimentCreate>(() => initialForm(locale));
  const [createOpen, setCreateOpen] = useState(false);
  const [metadataOpen, setMetadataOpen] = useState(false);
  const [metadataForm, setMetadataForm] = useState<ExperimentMetadata>(EMPTY_METADATA);
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
    ? locale === "fr" ? "Vérification de l’inférence…" : "Checking inference…"
    : hasRunnableEngine
      ? locale === "fr" ? "Inférence disponible" : "Inference available"
      : locale === "fr" ? "Inférence indisponible" : "Inference unavailable";

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
      setForm(initialForm(locale));
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
      setError(`${localizedRuntimeText((requestError as Error).message, locale)} ${locale === "fr" ? "Les imports déjà confirmés sont conservés ; reprenez les fichiers restants." : "Confirmed uploads were kept; resume with the remaining files."}`);
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

  async function handleMetadataUpdate(event: FormEvent) {
    event.preventDefault();
    if (!selectedExperiment) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateExperimentMetadata(selectedExperiment.id, metadataForm);
      setExperiments((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setResult(null);
      setMetadataOpen(false);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAnalyze() {
    if (!selectedExperiment) { setError(locale === "fr" ? "Créez ou sélectionnez une expérience avant l’analyse." : "Create or select an experiment before analysis."); return; }
    if (!selectedEngine?.runnable) { setError(locale === "fr" ? "Sélectionnez un moteur exécutable avant l’analyse." : "Select a runnable engine before analysis."); return; }
    if (files.length || selectedExperiment.image_count === 0) { setError(locale === "fr" ? "Importez les images sélectionnées avant de lancer l’analyse." : "Upload the selected images before starting analysis."); return; }
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
    const displayedEngine = selectedEngine ? localizedEngine(selectedEngine, locale) : null;
    return [
      { label: locale === "fr" ? "Importer les images" : "Upload images", hint: hasImages ? imageCountLabel(selectedExperiment?.image_count ?? 0, locale) : "PNG, JPEG, TIFF", state: hasImages ? "done" : "current" },
      { label: locale === "fr" ? "Choisir un moteur" : "Choose an engine", hint: displayedEngine?.name ?? (locale === "fr" ? "aucun moteur" : "no engine"), state: hasEngine ? (hasImages ? "done" : "todo") : hasImages ? "current" : "todo" },
      { label: locale === "fr" ? "Analyser" : "Analyze", hint: done ? (locale === "fr" ? "résultat disponible" : "result available") : (locale === "fr" ? "puis vérifier les résultats" : "then review the results"), state: done ? "done" : hasImages && hasEngine ? "current" : "todo" },
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
            { label: locale === "fr" ? "Format source" : "Source format", value: `${image.source_format} · ${image.source_mode} · ${image.source_bit_depth} ${locale === "fr" ? "bits/canal" : "bits/channel"}` },
            { label: locale === "fr" ? "Dimensions" : "Dimensions", value: `${image.width} × ${image.height} px` },
            { label: locale === "fr" ? "Taille" : "Size", value: `${(image.size_bytes / 1024 / 1024).toFixed(2)} ${locale === "fr" ? "Mo" : "MB"}` },
            { label: locale === "fr" ? "Aperçu" : "Preview", value: locale === "fr" ? "PNG 8 bits · affichage uniquement" : "8-bit PNG · display only" },
            { label: locale === "fr" ? "Analyse" : "Analysis", value: locale === "fr" ? "fichier source original" : "original source file" },
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
            { label: locale === "fr" ? "Format source" : "Source format", value: `${sourceImage.source_format} · ${sourceImage.source_mode} · ${sourceImage.source_bit_depth} ${locale === "fr" ? "bits/canal" : "bits/channel"}` },
            { label: locale === "fr" ? "Dimensions" : "Dimensions", value: `${sourceImage.width} × ${sourceImage.height} px` },
            { label: locale === "fr" ? "Aperçu" : "Preview", value: locale === "fr" ? "PNG 8 bits · affichage uniquement" : "8-bit PNG · display only" },
            { label: locale === "fr" ? "Analyse" : "Analysis", value: locale === "fr" ? "fichier source original" : "original source file" },
          ]
        : [];
      if (item.analysis_type === "segmentation") {
        const scale = result.experiment_metadata.microns_per_pixel;
        return {
          title: readableFilename(item.filename),
          original_url: original,
          overlay_url: `${item.overlay_url}?v=${version}`,
          facts: [
            ...sourceFacts,
            { label: locale === "fr" ? "Composantes connexes" : "Connected components", value: formatInteger(item.object_count, locale) },
            { label: locale === "fr" ? "Surface segmentée" : "Segmented area", value: formatPercent(item.foreground_fraction, locale) },
            { label: locale === "fr" ? "Aire moyenne (px²)" : "Mean area (px²)", value: formatDecimal(item.mean_object_area, locale) },
            { label: locale === "fr" ? "Diamètre équivalent (px)" : "Equivalent diameter (px)", value: formatDecimal(item.mean_equivalent_diameter, locale) },
            ...(scale === null ? [] : [
              { label: locale === "fr" ? "Aire moyenne (µm²)" : "Mean area (µm²)", value: formatDecimal(item.mean_object_area * scale ** 2, locale) },
              { label: locale === "fr" ? "Diamètre équivalent (µm)" : "Equivalent diameter (µm)", value: formatDecimal(item.mean_equivalent_diameter * scale, locale) },
            ]),
            { label: locale === "fr" ? "Seuil" : "Threshold", value: formatDecimal(item.threshold, locale) },
            { label: locale === "fr" ? "Premier plan" : "Foreground", value: item.foreground_polarity === "bright" ? (locale === "fr" ? "clair" : "bright") : (locale === "fr" ? "sombre" : "dark") },
          ],
        };
      }
      return {
        title: readableFilename(item.filename),
        original_url: original,
        overlay_url: null,
        facts: [
          ...sourceFacts,
          { label: locale === "fr" ? "Mode d’acquisition" : "Acquisition mode", value: acquisitionModeLabel(item.source_acquisition_mode, locale) },
          { label: locale === "fr" ? "Softmax brut « good » (non calibré)" : "Raw ‘good’ softmax (uncalibrated)", value: item.probability_good_raw === null ? (locale === "fr" ? "non calculé" : "not computed") : formatDecimal(item.probability_good_raw, locale) },
          { label: locale === "fr" ? "Décision" : "Decision", value: locale === "fr" ? "À vérifier · aucune classe attribuée" : "Review required · no assigned class" },
        ],
      };
    });
  }, [lightbox, images, locale, result]);

  const analysisLabel = analysisStartedAt !== null && selectedExperiment
    ? `${locale === "fr" ? "Analyse de" : "Analyzing"} ${imageCountLabel(selectedExperiment.image_count, locale)} · ${analysisElapsed} s`
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
          onCreate={() => { setForm(initialForm(locale)); setCreateOpen(true); }}
        />

        <main className="content">
          {error && (
            <div className="alert" role="alert">
              <strong>{locale === "fr" ? "Action interrompue" : "Action interrupted"}</strong>
              <span>{localizedRuntimeText(error, locale)}</span>
              <button className="icon-button" onClick={() => setError(null)} type="button" aria-label={locale === "fr" ? "Fermer le message d’erreur" : "Close error message"}>×</button>
            </div>
          )}

          {tab === "workspace" && (
            <>
              <div className="workspace-header">
                <div>
                  <label className="visually-hidden" htmlFor="active-experiment">{locale === "fr" ? "Expérience active" : "Active experiment"}</label>
                  <select id="active-experiment" className="experiment-select" value={selectedId ?? ""} disabled={busy} onChange={(event) => selectExperiment(event.target.value)}>
                    <option value="" disabled>{locale === "fr" ? "Sélectionner une expérience" : "Select an experiment"}</option>
                    {experiments.map((experiment) => (
                      <option key={experiment.id} value={experiment.id}>{experiment.name}</option>
                    ))}
                  </select>
                  {selectedExperiment?.description && <p className="muted">{selectedExperiment.description}</p>}
                  {selectedExperiment && (
                    <div className="experiment-context" aria-label={locale === "fr" ? "Contexte expérimental" : "Experimental context"}>
                      <div className="context-chips">
                        {selectedExperiment.chip_id && <span>{locale === "fr" ? "Puce" : "Chip"} · {selectedExperiment.chip_id}</span>}
                        {selectedExperiment.well_id && <span>{locale === "fr" ? "Puits" : "Well"} · {selectedExperiment.well_id}</span>}
                        {selectedExperiment.cell_line && <span>{locale === "fr" ? "Lignée" : "Model"} · {selectedExperiment.cell_line}</span>}
                        {selectedExperiment.culture_day !== null && <span>{locale === "fr" ? "Jour" : "Day"} · {selectedExperiment.culture_day}</span>}
                        {selectedExperiment.microns_per_pixel !== null && <span>{formatDecimal(selectedExperiment.microns_per_pixel, locale)} µm/pixel</span>}
                        {!selectedExperiment.chip_id && !selectedExperiment.well_id && !selectedExperiment.cell_line && selectedExperiment.culture_day === null && selectedExperiment.microns_per_pixel === null && (
                          <span>{locale === "fr" ? "Contexte non renseigné" : "Context not provided"}</span>
                        )}
                      </div>
                      <button
                        type="button"
                        className="text-button"
                        disabled={busy}
                        onClick={() => {
                          setMetadataForm(metadataFromExperiment(selectedExperiment));
                          setMetadataOpen(true);
                        }}
                      >
                        {locale === "fr" ? "Modifier les métadonnées" : "Edit metadata"}
                      </button>
                    </div>
                  )}
                </div>
                <Stepper steps={steps} />
              </div>

              {!selectedExperiment ? (
                <section className="card empty-state">
                  <h2>{locale === "fr" ? "Commencer" : "Get started"}</h2>
                  <p>{locale === "fr" ? "Créez une expérience, déposez vos images de microscopie, choisissez un moteur et lancez l’analyse." : "Create an experiment, upload microscopy images, choose an engine, and start analysis."}</p>
                  <button className="primary-button" type="button" onClick={() => setCreateOpen(true)}>{locale === "fr" ? "+ Nouvelle expérience" : "+ New experiment"}</button>
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
                        {analysisLabel ? <><span className="spinner" aria-hidden="true" /> {analysisLabel}</> : busy ? (locale === "fr" ? "Traitement en cours…" : "Processing…") : (locale === "fr" ? "Lancer l’analyse" : "Run analysis")}
                      </button>
                      <p className="muted launch-hint" aria-live="polite">
                        {analysisLabel ?? (files.length > 0
                          ? (locale === "fr" ? "Importez d’abord les images sélectionnées." : "Upload the selected images first.")
                          : selectedExperiment.image_count
                            ? locale === "fr" ? `${imageCountLabel(selectedExperiment.image_count, locale)} prête${selectedExperiment.image_count > 1 ? "s" : ""} pour l’analyse.` : `${imageCountLabel(selectedExperiment.image_count, locale)} ready for analysis.`
                            : locale === "fr" ? "Aucune image importée." : "No images uploaded.")}
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
              experiments={experiments}
              onOpenImage={(index) => setLightbox({ source: "results", index })}
              onGoToWorkspace={() => setTab("workspace")}
            />
          )}

          {tab === "benchmarks" && <BenchmarkSection summary={benchmarkSummary} />}

          <footer>
            <span>{locale === "fr" ? "OrganChip Insight · prototype scientifique reproductible" : "OrganChip Insight · reproducible scientific prototype"}</span>
            <span>{locale === "fr" ? "Aucune donnée clinique · aucune conclusion automatisée" : "No clinical data · no automated conclusion"}</span>
          </footer>
        </main>
      </div>

      <ExperimentDialog open={createOpen} form={form} busy={busy} onChange={setForm} onSubmit={handleCreate} onClose={() => setCreateOpen(false)} />
      <ExperimentMetadataDialog
        open={metadataOpen}
        value={metadataForm}
        busy={busy}
        onChange={setMetadataForm}
        onSubmit={handleMetadataUpdate}
        onClose={() => setMetadataOpen(false)}
      />
      <Lightbox items={lightboxItems} index={lightbox?.index ?? null} onClose={() => setLightbox(null)} onNavigate={(index) => setLightbox((current) => (current ? { ...current, index } : null))} />
    </div>
  );
}
