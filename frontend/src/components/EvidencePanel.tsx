import type { AnalysisResult } from "../types";
import { isHexDigest, provenanceLabel, provenanceValue } from "../lib/format";

interface EvidencePanelProps {
  result: AnalysisResult;
}

export function EvidencePanel({ result }: EvidencePanelProps) {
  const isQuality = result.task === "quality-classification";
  const provenanceEntries = Object.entries(result.provenance);

  return (
    <aside className="evidence-panel" aria-labelledby="evidence-title">
      <div className="evidence-title">
        <span aria-hidden="true">i</span>
        <div>
          <strong id="evidence-title">Niveau de preuve</strong>
          <small>Exploration non validée</small>
        </div>
      </div>
      {isQuality ? (
        <p>
          <strong>Abstention systématique :</strong> ce démonstrateur n’attribue jamais
          automatiquement les classes bon ou mauvais. Le score affiché est un softmax brut non
          calibré, sélectionné sur la seule validation ; le test gelé n’a jamais été ouvert.
        </p>
      ) : (
        <p>Ces mesures décrivent les images. Elles ne constituent ni un diagnostic ni une conclusion biologique.</p>
      )}
      {typeof result.metrics.quality_score === "number" && (
        <p className="metric-method-note">
          <strong>Indice de contraste relatif :</strong> moyenne du contraste divisée par 0,20, puis
          plafonnée à 1. Il ne mesure ni l’exactitude de la segmentation ni une qualité biologique.
        </p>
      )}
      {result.task === "segmentation" && (
        <p className="metric-method-note">
          <strong>Comptage :</strong> chaque élément correspond à une composante connexe du masque.
          Il n’est pas validé comme cellule ou noyau sur les images OoC.
        </p>
      )}
      <h3>Points à vérifier</h3>
      <ul>
        {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
      </ul>
      <dl className="provenance-box">
        <dt>Moteur</dt>
        <dd>{result.engine.name}</dd>
        <dt>Images analysées</dt>
        <dd>{result.image_count}</dd>
        <dt>Tâche</dt>
        <dd>{isQuality ? "Contrôle qualité expérimental" : "Segmentation"}</dd>
        {provenanceEntries.map(([key, value]) => (
          <div className="provenance-entry" key={key}>
            <dt>{provenanceLabel(key)}</dt>
            <dd>{isHexDigest(value) ? <code>{value}</code> : provenanceValue(value)}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}
