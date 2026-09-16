import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  analyzeExperiment,
  createExperiment,
  listExperiments,
  uploadImages,
} from "./api/client";
import type { AnalysisResult, Experiment, ExperimentCreate } from "./types";

const initialForm: ExperimentCreate = {
  name: "",
  description: "",
  control_label: "Control",
  treatment_label: "Treatment",
};

function formatMetric(key: string): string {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function App() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<ExperimentCreate>(initialForm);
  const [files, setFiles] = useState<FileList | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedExperiment = useMemo(
    () => experiments.find((experiment) => experiment.id === selectedId) ?? null,
    [experiments, selectedId],
  );

  async function refreshExperiments() {
    const items = await listExperiments();
    setExperiments(items);
    if (!selectedId && items.length > 0) {
      setSelectedId(items[0].id);
    }
  }

  useEffect(() => {
    refreshExperiments().catch((requestError: Error) => setError(requestError.message));
  }, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await createExperiment(form);
      setForm(initialForm);
      await refreshExperiments();
      setSelectedId(created.id);
      setResult(null);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAnalyze() {
    if (!selectedExperiment || !files || files.length === 0) {
      setError("Choose an experiment and at least one microscopy image.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await uploadImages(selectedExperiment.id, files);
      const analysis = await analyzeExperiment(selectedExperiment.id);
      setResult(analysis);
      await refreshExperiments();
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <div className="brand-mark" aria-hidden="true">
          OI
        </div>
        <div>
          <p className="eyebrow">AI4S · Reproducible microscopy intelligence</p>
          <h1>OrganChip Insight</h1>
          <p className="hero-copy">
            Turn microscopy images into traceable quality signals, phenotype evidence and
            experiment-ready reports.
          </p>
        </div>
        <div className="status-pill">
          <span /> Local-first
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="workspace-grid">
        <article className="panel create-panel">
          <div className="panel-heading">
            <div>
              <p className="step">01</p>
              <h2>Define the experiment</h2>
            </div>
            <span className="panel-tag">Metadata</span>
          </div>

          <form onSubmit={handleCreate}>
            <label>
              Experiment name
              <input
                required
                minLength={2}
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                placeholder="Drug response pilot"
              />
            </label>
            <label>
              Scientific objective
              <textarea
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
                placeholder="Compare cellular morphology after treatment..."
              />
            </label>
            <div className="two-columns">
              <label>
                Control
                <input
                  value={form.control_label}
                  onChange={(event) => setForm({ ...form, control_label: event.target.value })}
                />
              </label>
              <label>
                Treatment
                <input
                  value={form.treatment_label}
                  onChange={(event) => setForm({ ...form, treatment_label: event.target.value })}
                />
              </label>
            </div>
            <button className="primary-button" disabled={busy} type="submit">
              Create experiment
            </button>
          </form>
        </article>

        <article className="panel analysis-panel">
          <div className="panel-heading">
            <div>
              <p className="step">02</p>
              <h2>Analyze microscopy</h2>
            </div>
            <span className="panel-tag">Image QC baseline</span>
          </div>

          <label>
            Active experiment
            <select
              value={selectedId ?? ""}
              onChange={(event) => {
                setSelectedId(event.target.value);
                setResult(null);
              }}
            >
              <option value="" disabled>
                Select an experiment
              </option>
              {experiments.map((experiment) => (
                <option key={experiment.id} value={experiment.id}>
                  {experiment.name}
                </option>
              ))}
            </select>
          </label>

          <label className="drop-zone">
            <span className="drop-icon">+</span>
            <strong>Choose microscopy images</strong>
            <small>PNG, JPEG or TIFF · multiple files accepted</small>
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.tif,.tiff"
              multiple
              onChange={(event) => setFiles(event.target.files)}
            />
          </label>
          <p className="file-summary">
            {files?.length ? `${files.length} image(s) ready` : "No local image selected"}
          </p>

          <button
            className="primary-button"
            disabled={busy || !selectedExperiment}
            onClick={handleAnalyze}
          >
            {busy ? "Processing..." : "Run reproducible analysis"}
          </button>
        </article>

        <article className="panel results-panel">
          <div className="panel-heading">
            <div>
              <p className="step">03</p>
              <h2>Review the evidence</h2>
            </div>
            {result && <span className="panel-tag success">Complete</span>}
          </div>

          {!result ? (
            <div className="empty-state">
              <div className="cell-orbit" aria-hidden="true">
                <span />
              </div>
              <p>Results remain empty until a real image set is analyzed.</p>
            </div>
          ) : (
            <>
              <div className="metrics-grid">
                {Object.entries(result.metrics).map(([key, value]) => (
                  <div className="metric-card" key={key}>
                    <span>{formatMetric(key)}</span>
                    <strong>{value.toFixed(3)}</strong>
                  </div>
                ))}
              </div>
              <div className="provenance">
                <span>Pipeline</span>
                <code>{result.analysis_version}</code>
                <span>{result.image_count} images</span>
              </div>
              {result.warnings.length > 0 && (
                <ul className="warnings">
                  {result.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </>
          )}
        </article>
      </section>

      <footer>
        <span>Transparent baseline · No synthetic scientific claims</span>
        <span>Segmentation and phenotype models follow the dataset audit</span>
      </footer>
    </main>
  );
}
