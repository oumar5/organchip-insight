import { useState } from "react";
import type { ImageRecord, UploadLimits, UploadSummary } from "../types";
import { imageCountLabel } from "../lib/format";

interface ImportPanelProps {
  files: File[];
  images: ImageRecord[];
  uploadSummary: UploadSummary | null;
  uploadLimits: UploadLimits | null;
  uploadProgress: { done: number; total: number } | null;
  busy: boolean;
  onFilesChosen: (files: File[]) => void;
  onUpload: () => void;
  onOpenImage: (index: number) => void;
}

export function ImportPanel({
  files,
  images,
  uploadSummary,
  uploadLimits,
  uploadProgress,
  busy,
  onFilesChosen,
  onUpload,
  onOpenImage,
}: ImportPanelProps) {
  const [dragging, setDragging] = useState(false);
  const limits = uploadLimits
    ? `${uploadLimits.max_upload_bytes / 1024 / 1024} Mio par image · ${(uploadLimits.max_image_pixels / 1_000_000).toFixed(0)} mégapixels max`
    : "Chargement des limites…";

  return (
    <section className="card" aria-labelledby="import-title">
      <div className="card-heading">
        <h2 id="import-title">Images</h2>
        <span className="card-meta">{imageCountLabel(images.length)} importée{images.length > 1 ? "s" : ""}</span>
      </div>

      <label
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragEnter={() => setDragging(true)}
        onDragLeave={() => setDragging(false)}
        onDrop={() => setDragging(false)}
      >
        <span className="dropzone-icon" aria-hidden="true">＋</span>
        <strong>Déposez vos images ici, plusieurs à la fois</strong>
        <small>PNG, JPEG ou TIFF monopage · gris 8/16 bits ou couleur 8 bits · {limits}</small>
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

      {files.length > 0 && (
        <div className="chip-row" aria-label="Fichiers sélectionnés">
          {files.slice(0, 8).map((file, index) => (
            <span className="chip" key={`${file.name}-${index}`}>{file.name}</span>
          ))}
          {files.length > 8 && <span className="chip chip-muted">+ {files.length - 8}</span>}
        </div>
      )}

      {uploadProgress && (
        <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={uploadProgress.total} aria-valuenow={uploadProgress.done} aria-label="Import en cours">
          <span style={{ width: `${Math.round((uploadProgress.done / Math.max(uploadProgress.total, 1)) * 100)}%` }} />
        </div>
      )}

      {uploadSummary && (
        <div className="upload-summary" role="status">
          <strong>
            {uploadSummary.accepted_files.length} importé(s) · {uploadSummary.duplicate_files.length} déjà présent(s) · {uploadSummary.rejected_files.length} rejeté(s)
          </strong>
          {uploadSummary.rejected_files.length > 0 && (
            <ul>
              {uploadSummary.rejected_files.map((name, index) => (
                <li key={`${name}-${index}`}>{name} : {uploadSummary.rejection_reasons[name] ?? "Fichier non pris en charge."}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <button
        className="primary-button"
        disabled={busy || files.length === 0 || !uploadLimits}
        onClick={onUpload}
        type="button"
      >
        {uploadProgress ? `Import ${uploadProgress.done} / ${uploadProgress.total}` : `Importer les images${files.length ? ` (${files.length})` : ""}`}
      </button>

      {images.length > 0 && (
        <ul className="gallery gallery-compact" aria-label="Images importées">
          {images.map((image, index) => (
            <li key={image.filename}>
              <button type="button" className="gallery-card" onClick={() => onOpenImage(index)}>
                <img src={image.preview_url} alt={`Aperçu de ${image.display_name}`} loading="lazy" />
                <span className="gallery-caption">
                  <strong>{image.display_name}</strong>
                  <span>{image.source_format} · {image.source_bit_depth} bits/canal</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
