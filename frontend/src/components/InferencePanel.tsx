import type { AnalysisEngine, Experiment, UploadLimits, UploadSummary } from "../types";
import { engineStatusLabels, imageCountLabel } from "../lib/format";
import { EngineCatalog } from "./EngineCatalog";

interface InferencePanelProps {
  experiments: Experiment[];
  selectedExperiment: Experiment | null;
  engines: AnalysisEngine[];
  selectedEngine: AnalysisEngine | null;
  files: File[];
  uploadSummary: UploadSummary | null;
  uploadLimits: UploadLimits | null;
  uploadProgress: string | null;
  analysisProgress: string | null;
  busy: boolean;
  onSelectExperiment: (id: string) => void;
  onSelectEngine: (id: string) => void;
  onFilesChosen: (files: File[]) => void;
  onUpload: () => void;
  onAnalyze: () => void;
}

export function InferencePanel({
  experiments,
  selectedExperiment,
  engines,
  selectedEngine,
  files,
  uploadSummary,
  uploadLimits,
  uploadProgress,
  analysisProgress,
  busy,
  onSelectExperiment,
  onSelectEngine,
  onFilesChosen,
  onUpload,
  onAnalyze,
}: InferencePanelProps) {
  const runnableEngines = engines.filter((engine) => engine.runnable);
  const canAnalyze =
    !busy &&
    Boolean(selectedExperiment?.image_count) &&
    files.length === 0 &&
    Boolean(selectedEngine?.runnable);

  return (
    <article className="panel inference-panel" id="inference">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Analyse immédiate</p>
          <h2>Inférence sur vos images</h2>
        </div>
        <span className="panel-number" aria-hidden="true">02</span>
      </div>

      <div className="field-grid">
        <label>
          Expérience active
          <select
            value={selectedExperiment?.id ?? ""}
            disabled={busy}
            onChange={(event) => onSelectExperiment(event.target.value)}
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
            value={selectedEngine?.id ?? ""}
            disabled={busy}
            onChange={(event) => onSelectEngine(event.target.value)}
          >
            {runnableEngines.length === 0 && <option value="">Aucun moteur disponible</option>}
            {runnableEngines.map((engine) => (
              <option key={engine.id} value={engine.id}>
                {engine.name} — {engineStatusLabels[engine.status]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <EngineCatalog engines={engines} selectedEngineId={selectedEngine?.id ?? ""} />

      <label className="drop-zone">
        <span className="drop-icon" aria-hidden="true">⌁</span>
        <strong>Sélectionner les images de microscopie</strong>
        <small>PNG, JPEG ou TIFF monopage · couleur 8 bits ou gris 8/16 bits</small>
        <small>
          {uploadLimits
            ? `${uploadLimits.max_upload_bytes / 1024 / 1024} Mio par fichier · ${(uploadLimits.max_image_pixels / 1_000_000).toFixed(1)} mégapixels maximum`
            : "Chargement des limites d’import…"}
        </small>
        <span className="secondary-button">Choisir les fichiers</span>
        <input
          type="file"
          accept=".png,.jpg,.jpeg,.tif,.tiff"
          multiple
          disabled={busy}
          onChange={(event) => {
            onFilesChosen(Array.from(event.target.files ?? []));
            event.target.value = "";
          }}
        />
      </label>

      {files.length ? (
        <div className="file-list">
          {files.slice(0, 3).map((file, index) => (
            <div key={`${file.name}-${file.size}-${index}`}>
              <span className="file-icon" aria-hidden="true">IMG</span>
              <p>
                <strong>{file.name}</strong>
                <small>{(file.size / 1024 / 1024).toFixed(2)} Mo</small>
              </p>
            </div>
          ))}
          {files.length > 3 && <small>+ {files.length - 3} autre(s) image(s)</small>}
        </div>
      ) : selectedExperiment?.image_count ? (
        <p className="existing-files">✓ {imageCountLabel(selectedExperiment.image_count)} déjà disponible(s)</p>
      ) : null}

      {uploadSummary && (
        <div className="upload-summary" role="status">
          <strong>
            {uploadSummary.accepted_files.length} importé(s) · {uploadSummary.duplicate_files.length} déjà
            présent(s) · {uploadSummary.rejected_files.length} rejeté(s)
          </strong>
          {uploadSummary.rejected_files.length > 0 && (
            <ul>
              {uploadSummary.rejected_files.map((name, index) => (
                <li key={`${name}-${index}`}>
                  {name} : {uploadSummary.rejection_reasons[name] ?? "Fichier non pris en charge."}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <button
        className="secondary-button upload-button"
        disabled={busy || !selectedExperiment || !files.length || !uploadLimits}
        onClick={onUpload}
        type="button"
      >
        {uploadProgress ?? `Importer les images${files.length ? ` (${files.length})` : ""}`}
      </button>
      {files.length > 0 && (
        <p className="existing-files">Les fichiers sélectionnés doivent être importés avant l’analyse.</p>
      )}

      <button
        className="primary-button analyze-button"
        disabled={!canAnalyze}
        onClick={onAnalyze}
        type="button"
      >
        {analysisProgress ? (
          <><span className="spinner" aria-hidden="true" /> {analysisProgress}</>
        ) : busy ? (
          <><span className="spinner" aria-hidden="true" /> Traitement en cours…</>
        ) : (
          <>Lancer l’inférence <span aria-hidden="true">→</span></>
        )}
      </button>
      <p className="analysis-status" aria-live="polite">
        {analysisProgress ?? ""}
      </p>
    </article>
  );
}
