import type { ExperimentMetadata } from "../types";
import { useI18n } from "../i18n";

interface ExperimentMetadataFieldsProps {
  value: ExperimentMetadata;
  onChange: (value: ExperimentMetadata) => void;
}

function optionalNumber(value: string): number | null {
  return value === "" ? null : Number(value);
}

export function ExperimentMetadataFields({ value, onChange }: ExperimentMetadataFieldsProps) {
  const { locale } = useI18n();
  return (
    <fieldset className="metadata-fields">
      <legend>{locale === "fr" ? "Contexte expérimental" : "Experimental context"}</legend>
      <div className="form-grid">
        <label>
          {locale === "fr" ? "Identifiant de puce" : "Chip identifier"}
          <input
            maxLength={120}
            value={value.chip_id}
            onChange={(event) => onChange({ ...value, chip_id: event.target.value })}
            placeholder="chip-001"
          />
        </label>
        <label>
          {locale === "fr" ? "Puits" : "Well"}
          <input
            maxLength={80}
            value={value.well_id}
            onChange={(event) => onChange({ ...value, well_id: event.target.value })}
            placeholder="A01"
          />
        </label>
        <label>
          {locale === "fr" ? "Lignée / modèle" : "Cell line / model"}
          <input
            maxLength={120}
            value={value.cell_line}
            onChange={(event) => onChange({ ...value, cell_line: event.target.value })}
            placeholder={locale === "fr" ? "Lignée iPSC-01" : "iPSC line 01"}
          />
        </label>
        <label>
          {locale === "fr" ? "Jour de culture" : "Culture day"}
          <input
            type="number"
            min={0}
            max={3650}
            step={1}
            value={value.culture_day ?? ""}
            onChange={(event) => onChange({ ...value, culture_day: optionalNumber(event.target.value) })}
            placeholder="14"
          />
        </label>
      </div>
      <div className="calibration-fields">
        <label>
          {locale === "fr" ? "Échelle (µm/pixel)" : "Scale (µm/pixel)"}
          <input
            type="number"
            min="0.000001"
            max={1000}
            step="any"
            value={value.microns_per_pixel ?? ""}
            onChange={(event) => onChange({ ...value, microns_per_pixel: optionalNumber(event.target.value) })}
            placeholder="0.65"
          />
        </label>
        <label>
          {locale === "fr" ? "Source de calibration" : "Calibration source"}
          <input
            required={value.microns_per_pixel !== null}
            maxLength={240}
            value={value.calibration_source}
            onChange={(event) => onChange({ ...value, calibration_source: event.target.value })}
            placeholder={locale === "fr" ? "Métadonnées du microscope" : "Microscope metadata"}
          />
        </label>
      </div>
      <p className="form-scope-note">
        {locale === "fr"
          ? "L’échelle reste facultative, mais sa source est obligatoire. Sans calibration, les mesures restent en pixels."
          : "Scale is optional, but its source is required. Without calibration, measurements remain in pixels."}
      </p>
    </fieldset>
  );
}
