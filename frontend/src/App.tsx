import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  analyzeExperiment,
  createExperiment,
  getBenchmarkSummary,
  getExperimentResults,
  getUploadLimits,
  listExperiments,
  listInferenceEngines,
  uploadImage,
} from "./api/client";
import type {
  AnalysisEngine,
  AnalysisResult,
  BenchmarkSummary,
  Experiment,
  ExperimentCreate,
  UploadLimits,
  UploadSummary,
} from "./types";
import { Sidebar } from "./components/Sidebar";
import { ExperimentForm } from "./components/ExperimentForm";
import { InferencePanel } from "./components/InferencePanel";
import { ResultsSection } from "./components/ResultsSection";
import { BenchmarkSection } from "./components/BenchmarkSection";
import { imageCountLabel } from "./lib/format";

const initialForm: ExperimentCreate = {
  name: "",
  description: "",
  control_label: "Contrôle",
  treatment_label: "Traitement",
};

export default function App() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [engines, setEngines] = useState<AnalysisEngine[]>([]);
  const [engineRegistryLoaded, setEngineRegistryLoaded] = useState(false);
  const [benchmarkSummary, setBenchmarkSummary] = useState<BenchmarkSummary | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEngineId, setSelectedEngineId] = useState("");
  const [form, setForm] = useState<ExperimentCreate>(initialForm);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadSummary, setUploadSummary] = useState<UploadSummary | null>(null);
  const [uploadLimits, setUploadLimits] = useState<UploadLimits | null>(null);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [analysisStartedAt, setAnalysisStartedAt] = useState<number | null>(null);
  const [analysisElapsed, setAnalysisElapsed] = useState(0);
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
  const inferenceStatus = !engineRegistryLoaded ? "loading" : hasRunnableEngine ? "ready" : "unavailable";
  const inferenceStatusLabel = !engineRegistryLoaded
    ? "Vérification de l’inférence…"
    : hasRunnableEngine
      ? "Inférence disponible"
      : "Inférence indisponible";
  const analysisProgress =
    analysisStartedAt !== null && selectedExperiment
      ? `Analyse de ${imageCountLabel(selectedExperiment.image_count)} · ${analysisElapsed} s`
      : null;

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
      .then((value) => {
        if (requestId === resultRequest.current) setResult(value);
      })
      .catch(() => {
        if (requestId === resultRequest.current) setResult(null);
      });
    return () => {
      resultRequest.current++;
    };
  }, [selectedId]);

  useEffect(() => {
    if (analysisStartedAt === null) {
      setAnalysisElapsed(0);
      return;
    }
    const timer = window.setInterval(() => {
      setAnalysisElapsed(Math.round((Date.now() - analysisStartedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [analysisStartedAt]);

  function selectExperiment(id: string) {
    if (id === selectedId) return;
    resultRequest.current++;
    setSelectedId(id);
    setResult(null);
    setFiles([]);
    setUploadSummary(null);
    setError(null);
  }

  function chooseFiles(chosen: File[]) {
    setFiles(chosen);
    setUploadSummary(null);
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
      setError(
        `${(requestError as Error).message} Les imports déjà confirmés sont conservés. Vous pouvez reprendre les fichiers restants.`,
      );
    } finally {
      setUploadProgress(null);
      try {
        await refreshExperiments(selectedExperiment.id);
      } catch (requestError) {
        setError((requestError as Error).message);
      }
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
    setAnalysisStartedAt(Date.now());
    try {
      const analysis = await analyzeExperiment(selectedExperiment.id, selectedEngine.id);
      setResult(analysis);
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      document.querySelector("#results")?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setAnalysisStartedAt(null);
      try {
        await refreshExperiments(selectedExperiment.id);
      } catch (requestError) {
        setError((requestError as Error).message);
      }
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <Sidebar experiments={experiments} selectedId={selectedId} busy={busy} onSelect={selectExperiment} />

      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">AI for life science · espace de travail</p>
            <h1>Des images de puces aux mesures traçables.</h1>
          </div>
          <div className={`system-status ${inferenceStatus}`}>
            <span aria-hidden="true" /> {inferenceStatusLabel}
          </div>
        </header>

        {error && (
          <div className="alert" role="alert">
            <strong>Action interrompue</strong>
            <span>{error}</span>
            <button onClick={() => setError(null)} type="button" aria-label="Fermer le message d’erreur">
              ×
            </button>
          </div>
        )}

        <section className="intro-strip" aria-label="Résumé du parcours">
          <div>
            <span className="intro-index" aria-hidden="true">01</span>
            <p><strong>Définir</strong><small>Contexte de l’étude</small></p>
          </div>
          <i aria-hidden="true" />
          <div>
            <span className="intro-index" aria-hidden="true">02</span>
            <p><strong>Analyser</strong><small>Moteur explicite</small></p>
          </div>
          <i aria-hidden="true" />
          <div>
            <span className="intro-index" aria-hidden="true">03</span>
            <p><strong>Vérifier</strong><small>Mesures et limites</small></p>
          </div>
          <div className="evidence-chip">Exploratoire · traçable</div>
        </section>

        <section className="workspace-grid" id="workspace">
          <ExperimentForm form={form} busy={busy} onChange={setForm} onSubmit={handleCreate} />
          <InferencePanel
            experiments={experiments}
            selectedExperiment={selectedExperiment}
            engines={engines}
            selectedEngine={selectedEngine}
            files={files}
            uploadSummary={uploadSummary}
            uploadLimits={uploadLimits}
            uploadProgress={uploadProgress}
            analysisProgress={analysisProgress}
            busy={busy}
            onSelectExperiment={selectExperiment}
            onSelectEngine={setSelectedEngineId}
            onFilesChosen={chooseFiles}
            onUpload={handleUpload}
            onAnalyze={handleAnalyze}
          />
        </section>

        <ResultsSection result={result} selectedExperiment={selectedExperiment} />

        <BenchmarkSection summary={benchmarkSummary} />

        <footer>
          <span>OrganChip Insight · prototype scientifique reproductible</span>
          <span>Aucune donnée clinique · aucune conclusion automatisée</span>
        </footer>
      </main>
    </div>
  );
}
