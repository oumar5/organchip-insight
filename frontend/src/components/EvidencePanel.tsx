import type { AnalysisResult } from "../types";
import { isHexDigest, localizedEngine, localizedRuntimeText, provenanceLabel, provenanceValue } from "../lib/format";
import { useI18n } from "../i18n";

interface EvidencePanelProps {
  result: AnalysisResult;
}

export function EvidencePanel({ result }: EvidencePanelProps) {
  const { locale } = useI18n();
  const isQuality = result.task === "quality-classification";
  const provenanceEntries = Object.entries(result.provenance);
  const engine = localizedEngine(result.engine, locale);

  return (
    <aside className="evidence-panel" aria-labelledby="evidence-title">
      <div className="evidence-title">
        <span aria-hidden="true">i</span>
        <div>
          <strong id="evidence-title">{locale === "fr" ? "Niveau de preuve" : "Evidence level"}</strong>
          <small>{locale === "fr" ? "Exploration non validée" : "Unvalidated exploration"}</small>
        </div>
      </div>
      {isQuality ? (
        <p>{locale === "fr"
          ? <><strong>Abstention systématique :</strong> ce démonstrateur n’attribue jamais automatiquement les classes bon ou mauvais. Le score affiché est un softmax brut non calibré, sélectionné sur la seule validation ; le test gelé n’a jamais été ouvert.</>
          : <><strong>Systematic abstention:</strong> this demonstrator never assigns good or bad classes automatically. The displayed score is an uncalibrated raw softmax selected on validation only; the frozen test has never been opened.</>}
        </p>
      ) : (
        <p>{locale === "fr" ? "Ces mesures décrivent les images. Elles ne constituent ni un diagnostic ni une conclusion biologique." : "These measurements describe the images. They are neither a diagnosis nor a biological conclusion."}</p>
      )}
      {typeof result.metrics.quality_score === "number" && (
        <p className="metric-method-note">
          <strong>{locale === "fr" ? "Indice de contraste relatif :" : "Relative contrast index:"}</strong>{" "}
          {locale === "fr" ? "moyenne du contraste divisée par 0,20, puis plafonnée à 1. Il ne mesure ni l’exactitude de la segmentation ni une qualité biologique." : "mean contrast divided by 0.20 and capped at 1. It measures neither segmentation accuracy nor biological quality."}
        </p>
      )}
      {result.task === "segmentation" && (
        <p className="metric-method-note">
          <strong>{locale === "fr" ? "Comptage :" : "Counting:"}</strong>{" "}
          {locale === "fr" ? "chaque élément correspond à une composante connexe du masque. Il n’est pas validé comme cellule ou noyau sur les images OoC." : "each item is a connected component of the mask. It has not been validated as a cell or nucleus on OoC images."}
        </p>
      )}
      <h3>{locale === "fr" ? "Points à vérifier" : "Review points"}</h3>
      <ul>
        {result.warnings.map((warning) => <li key={warning}>{localizedRuntimeText(warning, locale)}</li>)}
      </ul>
      <dl className="provenance-box">
        <dt>{locale === "fr" ? "Moteur" : "Engine"}</dt>
        <dd>{engine.name}</dd>
        <dt>{locale === "fr" ? "Images analysées" : "Analyzed images"}</dt>
        <dd>{result.image_count}</dd>
        <dt>{locale === "fr" ? "Tâche" : "Task"}</dt>
        <dd>{isQuality ? (locale === "fr" ? "Contrôle qualité expérimental" : "Experimental quality control") : "Segmentation"}</dd>
        {provenanceEntries.map(([key, value]) => (
          <div className="provenance-entry" key={key}>
            <dt>{provenanceLabel(key, locale)}</dt>
            <dd>{isHexDigest(value) ? <code>{value}</code> : provenanceValue(value, locale)}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}
