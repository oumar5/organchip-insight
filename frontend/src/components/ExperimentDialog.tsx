import type { FormEvent } from "react";
import type { ExperimentCreate } from "../types";
import { useI18n } from "../i18n";
import { Modal } from "./Modal";

interface ExperimentDialogProps {
  open: boolean;
  form: ExperimentCreate;
  busy: boolean;
  onChange: (form: ExperimentCreate) => void;
  onSubmit: (event: FormEvent) => void;
  onClose: () => void;
}

export function ExperimentDialog({ open, form, busy, onChange, onSubmit, onClose }: ExperimentDialogProps) {
  const { locale } = useI18n();
  return (
    <Modal open={open} title={locale === "fr" ? "Nouvelle expérience" : "New experiment"} onClose={onClose}>
      <form onSubmit={onSubmit} className="stack-form">
        <label>
          {locale === "fr" ? "Nom de l’expérience" : "Experiment name"}
          <input
            required
            minLength={2}
            maxLength={120}
            value={form.name}
            onChange={(event) => onChange({ ...form, name: event.target.value })}
            placeholder={locale === "fr" ? "Réponse au composé A" : "Response to compound A"}
          />
        </label>
        <label>
          {locale === "fr" ? "Hypothèse ou objectif" : "Hypothesis or objective"}
          <textarea
            maxLength={1000}
            value={form.description}
            onChange={(event) => onChange({ ...form, description: event.target.value })}
            placeholder={locale === "fr" ? "Décrire la comparaison et le signal attendu…" : "Describe the comparison and expected signal…"}
          />
        </label>
        <p className="form-scope-note">
          {locale === "fr"
            ? "L’affectation témoin/traitement viendra avec le rattachement de chaque image à un groupe."
            : "Control/treatment assignment will be added when each image is linked to a group."}
        </p>
        <div className="modal-actions">
          <button className="secondary-button" type="button" onClick={onClose}>{locale === "fr" ? "Annuler" : "Cancel"}</button>
          <button className="primary-button" disabled={busy} type="submit">{locale === "fr" ? "Créer l’expérience" : "Create experiment"}</button>
        </div>
      </form>
    </Modal>
  );
}
