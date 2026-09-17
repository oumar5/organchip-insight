import type { FormEvent } from "react";
import type { ExperimentCreate } from "../types";
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
  return (
    <Modal open={open} title="Nouvelle expérience" onClose={onClose}>
      <form onSubmit={onSubmit} className="stack-form">
        <label>
          Nom de l’expérience
          <input
            required
            minLength={2}
            maxLength={120}
            value={form.name}
            onChange={(event) => onChange({ ...form, name: event.target.value })}
            placeholder="Réponse au composé A"
          />
        </label>
        <label>
          Hypothèse ou objectif
          <textarea
            maxLength={1000}
            value={form.description}
            onChange={(event) => onChange({ ...form, description: event.target.value })}
            placeholder="Décrire la comparaison et le signal attendu…"
          />
        </label>
        <p className="form-scope-note">
          L’affectation témoin/traitement viendra avec le rattachement de chaque image à un groupe.
        </p>
        <div className="modal-actions">
          <button className="secondary-button" type="button" onClick={onClose}>Annuler</button>
          <button className="primary-button" disabled={busy} type="submit">Créer l’expérience</button>
        </div>
      </form>
    </Modal>
  );
}
