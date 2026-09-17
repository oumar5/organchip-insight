import { useState } from "react";
import type { ImageRecord, UploadLimits, UploadSummary } from "../types";
import { imageCountLabel, localizedRuntimeText } from "../lib/format";
import { useI18n } from "../i18n";

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
  const { locale } = useI18n();
  const [dragging, setDragging] = useState(false);
  const limits = uploadLimits
    ? locale === "fr"
      ? `${uploadLimits.max_upload_bytes / 1024 / 1024} Mio par image · ${(uploadLimits.max_image_pixels / 1_000_000).toFixed(0)} mégapixels max`
      : `${uploadLimits.max_upload_bytes / 1024 / 1024} MiB per image · ${(uploadLimits.max_image_pixels / 1_000_000).toFixed(0)} megapixels max`
    : locale === "fr" ? "Chargement des limites…" : "Loading limits…";

  return (
    <section className="card" aria-labelledby="import-title">
      <div className="card-heading">
        <h2 id="import-title">Images</h2>
        <span className="card-meta">{locale === "fr" ? `${imageCountLabel(images.length, locale)} importée${images.length > 1 ? "s" : ""}` : `${imageCountLabel(images.length, locale)} imported`}</span>
      </div>

      <label
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragEnter={() => setDragging(true)}
        onDragLeave={() => setDragging(false)}
        onDrop={() => setDragging(false)}
      >
        <span className="dropzone-icon" aria-hidden="true">＋</span>
        <strong>{locale === "fr" ? "Déposez vos images ici, plusieurs à la fois" : "Drop multiple images here"}</strong>
        <small>{locale === "fr" ? "PNG, JPEG ou TIFF monopage · gris 8/16 bits ou couleur 8 bits" : "PNG, JPEG or single-page TIFF · 8/16-bit grayscale or 8-bit color"} · {limits}</small>
        <span className="secondary-button">{locale === "fr" ? "Choisir les fichiers" : "Choose files"}</span>
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
        <div className="chip-row" aria-label={locale === "fr" ? "Fichiers sélectionnés" : "Selected files"}>
          {files.slice(0, 8).map((file, index) => (
            <span className="chip" key={`${file.name}-${index}`}>{file.name}</span>
          ))}
          {files.length > 8 && <span className="chip chip-muted">+ {files.length - 8}</span>}
        </div>
      )}

      {uploadProgress && (
        <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={uploadProgress.total} aria-valuenow={uploadProgress.done} aria-label={locale === "fr" ? "Import en cours" : "Upload in progress"}>
          <span style={{ width: `${Math.round((uploadProgress.done / Math.max(uploadProgress.total, 1)) * 100)}%` }} />
        </div>
      )}

      {uploadSummary && (
        <div className="upload-summary" role="status">
          <strong>
            {locale === "fr"
              ? `${uploadSummary.accepted_files.length} importé(s) · ${uploadSummary.duplicate_files.length} déjà présent(s) · ${uploadSummary.rejected_files.length} rejeté(s)`
              : `${uploadSummary.accepted_files.length} imported · ${uploadSummary.duplicate_files.length} already present · ${uploadSummary.rejected_files.length} rejected`}
          </strong>
          {uploadSummary.rejected_files.length > 0 && (
            <ul>
              {uploadSummary.rejected_files.map((name, index) => (
                <li key={`${name}-${index}`}>{name} : {localizedRuntimeText(uploadSummary.rejection_reasons[name] ?? (locale === "fr" ? "Fichier non pris en charge." : "Unsupported file."), locale)}</li>
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
        {uploadProgress
          ? `${locale === "fr" ? "Import" : "Upload"} ${uploadProgress.done} / ${uploadProgress.total}`
          : `${locale === "fr" ? "Importer les images" : "Upload images"}${files.length ? ` (${files.length})` : ""}`}
      </button>

      {images.length > 0 && (
        <ul className="gallery gallery-compact" aria-label={locale === "fr" ? "Images importées" : "Imported images"}>
          {images.map((image, index) => (
            <li key={image.filename}>
              <button type="button" className="gallery-card" onClick={() => onOpenImage(index)}>
                <img src={image.preview_url} alt={`${locale === "fr" ? "Aperçu de" : "Preview of"} ${image.display_name}`} loading="lazy" />
                <span className="gallery-caption">
                  <strong>{image.display_name}</strong>
                  <span>{image.source_format} · {image.source_bit_depth} {locale === "fr" ? "bits/canal" : "bits/channel"}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
