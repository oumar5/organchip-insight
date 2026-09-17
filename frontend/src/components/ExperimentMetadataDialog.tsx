import type { FormEvent } from "react";
import type { ExperimentMetadata } from "../types";
import { useI18n } from "../i18n";
import { ExperimentMetadataFields } from "./ExperimentMetadataFields";
import { Modal } from "./Modal";

interface ExperimentMetadataDialogProps {
  open: boolean;
  value: ExperimentMetadata;
  busy: boolean;
  onChange: (value: ExperimentMetadata) => void;
  onSubmit: (event: FormEvent) => void;
  onClose: () => void;
}

export function ExperimentMetadataDialog({
  open,
  value,
  busy,
  onChange,
  onSubmit,
  onClose,
}: ExperimentMetadataDialogProps) {
  const { locale } = useI18n();
  return (
    <Modal
      open={open}
      title={locale === "fr" ? "Métadonnées de l’expérience" : "Experiment metadata"}
      onClose={onClose}
    >
      <form onSubmit={onSubmit} className="stack-form">
        <ExperimentMetadataFields value={value} onChange={onChange} />
        <p className="form-warning">
          {locale === "fr"
            ? "Toute modification invalide le résultat courant afin que les exports restent traçables. Il faudra relancer l’analyse."
            : "Any change invalidates the current result so exports remain traceable. Analysis must be run again."}
        </p>
        <div className="modal-actions">
          <button className="secondary-button" type="button" onClick={onClose}>
            {locale === "fr" ? "Annuler" : "Cancel"}
          </button>
          <button className="primary-button" disabled={busy} type="submit">
            {locale === "fr" ? "Enregistrer" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
