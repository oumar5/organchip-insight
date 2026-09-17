import type { AnalysisResult, SegmentationImageAnalysis } from "../types";
import { formatDecimal, formatInteger, formatPercent, readableFilename } from "../lib/format";

interface SegmentationResultsProps {
  result: AnalysisResult;
}

export function SegmentationResults({ result }: SegmentationResultsProps) {
  const images = result.image_results.filter(
    (item): item is SegmentationImageAnalysis => item.analysis_type === "segmentation",
  );
  const version = encodeURIComponent(result.generated_at);

  return (
    <>
      <div className="overlay-grid">
        {images.map((image) => (
          <figure key={image.overlay_url}>
            <a
              className="overlay-link"
              href={`${image.overlay_url}?v=${version}`}
              target="_blank"
              rel="noreferrer"
              aria-label={`Ouvrir l’overlay de ${readableFilename(image.filename)} en taille réelle`}
            >
              <img
                src={`${image.overlay_url}?v=${version}`}
                alt={`Segmentation de ${readableFilename(image.filename)} : masque et contours superposés`}
              />
            </a>
            <figcaption>
              <div>
                <strong>{readableFilename(image.filename)}</strong>
                <span>{formatInteger(image.object_count)} composantes</span>
              </div>
              <small>
                Premier plan {image.foreground_polarity === "bright" ? "clair" : "sombre"} · seuil{" "}
                {formatDecimal(image.threshold)}
              </small>
            </figcaption>
          </figure>
        ))}
      </div>

      <div className="table-scroll">
        <table className="image-table">
          <caption>Mesures par image · composantes connexes du masque, pas des cellules validées</caption>
          <thead>
            <tr>
              <th scope="col">Image</th>
              <th scope="col">Composantes</th>
              <th scope="col">Surface segmentée</th>
              <th scope="col">Aire moyenne (px²)</th>
              <th scope="col">Aire médiane (px²)</th>
              <th scope="col">Diamètre équivalent (px)</th>
              <th scope="col">Seuil</th>
              <th scope="col">Premier plan</th>
            </tr>
          </thead>
          <tbody>
            {images.map((image) => (
              <tr key={image.filename}>
                <th scope="row">{readableFilename(image.filename)}</th>
                <td>{formatInteger(image.object_count)}</td>
                <td>{formatPercent(image.foreground_fraction)}</td>
                <td>{formatDecimal(image.mean_object_area)}</td>
                <td>{formatDecimal(image.median_object_area)}</td>
                <td>{formatDecimal(image.mean_equivalent_diameter)}</td>
                <td>{formatDecimal(image.threshold)}</td>
                <td>{image.foreground_polarity === "bright" ? "clair" : "sombre"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
