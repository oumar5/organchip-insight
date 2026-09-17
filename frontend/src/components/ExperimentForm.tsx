import type { FormEvent } from "react";
import type { ExperimentCreate } from "../types";

interface ExperimentFormProps {
  form: ExperimentCreate;
  busy: boolean;
  onChange: (form: ExperimentCreate) => void;
  onSubmit: (event: FormEvent) => void;
}

export function ExperimentForm({ form, busy, onChange, onSubmit }: ExperimentFormProps) {
  return (
    <article className="panel create-panel">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Nouvelle étude</p>
          <h2>Cadre expérimental</h2>
        </div>
        <span className="panel-number" aria-hidden="true">01</span>
      </div>

      <form onSubmit={onSubmit}>
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
          L’affectation témoin/traitement est masquée tant que chaque image ne peut pas être
          rattachée explicitement à un groupe expérimental.
        </p>
        <button className="primary-button" disabled={busy} type="submit">
          Créer l’expérience <span aria-hidden="true">→</span>
        </button>
      </form>
    </article>
  );
}
