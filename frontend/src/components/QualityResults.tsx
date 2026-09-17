import type { AnalysisResult, QualityImageAnalysis } from "../types";
import { acquisitionModeLabels, formatDecimal, readableFilename } from "../lib/format";

interface QualityResultsProps {
  result: AnalysisResult;
}

export function QualityResults({ result }: QualityResultsProps) {
  const images = result.image_results.filter(
    (item): item is QualityImageAnalysis => item.analysis_type === "quality-classification",
  );

  return (
    <div className="quality-result-list">
      {images.map((image) => (
        <article className="quality-result-card" key={image.filename}>
          <div className="quality-result-identity">
            <strong>{readableFilename(image.filename)}</strong>
            <small>Mode source : {acquisitionModeLabels[image.source_acquisition_mode]}</small>
          </div>
          <div className="raw-score">
            <span>Softmax brut « good », non calibré</span>
            <strong>
              {image.probability_good_raw === null ? "Non calculé" : formatDecimal(image.probability_good_raw)}
            </strong>
            <small>
              {image.interpretation === "outside-training-domain"
                ? "Image hors du domaine d’entraînement : aucun score"
                : "Aucune classe attribuée"}
            </small>
          </div>
          <span className="review-badge">À vérifier</span>
        </article>
      ))}
    </div>
  );
}
