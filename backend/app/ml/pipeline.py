from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError
from skimage.filters import threshold_otsu
from skimage.measure import label, regionprops
from skimage.morphology import closing, disk, remove_small_holes, remove_small_objects
from skimage.segmentation import find_boundaries

from app.ml.image_io import read_image
from app.ml.registry import ADAPTIVE_SEGMENTATION_ENGINE
from app.schemas import AnalysisArtifact, ImageAnalysis, QualityImageAnalysis


@dataclass(frozen=True)
class PipelineOutput:
    metrics: dict[str, float]
    image_results: list[ImageAnalysis | QualityImageAnalysis]
    artifacts: list[AnalysisArtifact]
    warnings: list[str]
    provenance: dict[str, str]


@dataclass(frozen=True)
class SegmentationOutput:
    mask: np.ndarray
    labels: np.ndarray
    threshold: float
    polarity: str


class AdaptiveSegmentationAnalyzer:
    """Transparent zero-training inference for microscopy image exploration."""

    version = "adaptive-segmentation-1.1.0"
    engine = ADAPTIVE_SEGMENTATION_ENGINE

    @staticmethod
    def _normalize(grayscale: np.ndarray) -> np.ndarray:
        low, high = np.percentile(grayscale, (1.0, 99.0))
        if high <= low:
            return np.clip(grayscale, 0.0, 1.0)
        return np.clip((grayscale - low) / (high - low), 0.0, 1.0)

    @staticmethod
    def _choose_foreground(image: np.ndarray, threshold: float) -> tuple[np.ndarray, str]:
        candidates = {
            "bright": image > threshold,
            "dark": image < threshold,
        }

        def score(mask: np.ndarray) -> float:
            fraction = float(mask.mean())
            range_penalty = 0.0 if 0.005 <= fraction <= 0.60 else 10.0
            return range_penalty + abs(fraction - 0.18)

        polarity = min(candidates, key=lambda name: score(candidates[name]))
        return candidates[polarity], polarity

    @staticmethod
    def _clean_mask(mask: np.ndarray) -> np.ndarray:
        adaptive_min_size = max(9, min(256, int(mask.size * 0.00004)))
        cleaned = closing(mask, footprint=disk(1))
        cleaned = remove_small_objects(cleaned, max_size=adaptive_min_size - 1)
        return remove_small_holes(cleaned, max_size=adaptive_min_size - 1)

    def segment(self, grayscale: np.ndarray) -> SegmentationOutput:
        """Return the exact foreground mask used by the production inference path."""
        normalized = self._normalize(grayscale)
        threshold = float(threshold_otsu(normalized)) if np.ptp(normalized) > 0 else 0.5
        raw_mask, polarity = self._choose_foreground(normalized, threshold)
        mask = self._clean_mask(raw_mask)
        return SegmentationOutput(
            mask=mask,
            labels=label(mask, connectivity=2),
            threshold=threshold,
            polarity=polarity,
        )

    @staticmethod
    def _save_overlay(rgb: np.ndarray, labels: np.ndarray, destination: Path) -> None:
        overlay = rgb.astype(np.float32)
        foreground = labels > 0
        boundaries = find_boundaries(labels, mode="outer")
        overlay[foreground] = overlay[foreground] * 0.78 + np.array([32, 175, 132]) * 0.22
        overlay[boundaries] = np.array([255, 111, 74])
        Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8)).save(destination, "PNG")

    def analyze(
        self,
        image_paths: list[Path],
        artifact_dir: Path,
        artifact_url_prefix: str,
    ) -> PipelineOutput:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        intensities: list[float] = []
        contrasts: list[float] = []
        image_results: list[ImageAnalysis] = []
        artifacts: list[AnalysisArtifact] = []
        warnings = [
            "Inférence exploratoire : inspectez les overlays avant d'interpréter les mesures."
        ]

        stem_counts = Counter(path.stem for path in image_paths)
        for image_index, image_path in enumerate(image_paths, start=1):
            try:
                rgb, grayscale = read_image(image_path)
            except (
                OSError,
                ValueError,
                Image.DecompressionBombError,
                UnidentifiedImageError,
            ) as error:
                warnings.append(f"Image illisible {image_path.name} : {error}")
                continue

            segmentation = self.segment(grayscale)
            threshold = segmentation.threshold
            polarity = segmentation.polarity
            labels = segmentation.labels
            regions = regionprops(labels)
            areas = [float(region.area) for region in regions]
            diameters = [float(region.equivalent_diameter_area) for region in regions]

            overlay_filename = f"{image_path.stem}-overlay.png"
            if stem_counts[image_path.stem] > 1:
                source_suffix = image_path.suffix.lower().lstrip(".") or "image"
                overlay_filename = (
                    f"{image_path.stem}-{source_suffix}-{image_index:03d}-overlay.png"
                )
            overlay_path = artifact_dir / overlay_filename
            self._save_overlay(rgb, labels, overlay_path)
            overlay_url = f"{artifact_url_prefix}/{overlay_filename}"

            result = ImageAnalysis(
                filename=image_path.name,
                object_count=len(regions),
                foreground_fraction=round(float((labels > 0).mean()), 4),
                mean_object_area=round(float(np.mean(areas)) if areas else 0.0, 2),
                median_object_area=round(float(np.median(areas)) if areas else 0.0, 2),
                mean_equivalent_diameter=round(
                    float(np.mean(diameters)) if diameters else 0.0,
                    2,
                ),
                threshold=round(threshold, 4),
                foreground_polarity=polarity,
                overlay_url=overlay_url,
            )
            image_results.append(result)
            artifacts.append(
                AnalysisArtifact(
                    filename=overlay_filename,
                    kind="segmentation-overlay",
                    url=overlay_url,
                )
            )
            intensities.append(float(grayscale.mean()))
            contrasts.append(float(grayscale.std()))

            if not regions:
                warnings.append(f"Aucun objet détecté dans {image_path.name}.")

        if not image_results:
            raise ValueError("Aucune image lisible n'est disponible pour l'inférence")

        mean_intensity = float(np.mean(intensities))
        mean_contrast = float(np.mean(contrasts))
        total_objects = sum(result.object_count for result in image_results)
        quality_score = float(np.clip(mean_contrast / 0.20, 0.0, 1.0))

        if mean_intensity < 0.08:
            warnings.append("Le lot d'images semble fortement sous-exposé.")
        if mean_intensity > 0.92:
            warnings.append("Le lot d'images semble fortement surexposé.")
        if mean_contrast < 0.04:
            warnings.append("Le faible contraste peut réduire la fiabilité de la segmentation.")

        return PipelineOutput(
            metrics={
                "object_count_total": float(total_objects),
                "objects_per_image": round(total_objects / len(image_results), 2),
                "mean_foreground_fraction": round(
                    float(np.mean([item.foreground_fraction for item in image_results])),
                    4,
                ),
                "mean_object_area": round(
                    float(np.mean([item.mean_object_area for item in image_results])),
                    2,
                ),
                "mean_intensity": round(mean_intensity, 4),
                "mean_contrast": round(mean_contrast, 4),
                "quality_score": round(quality_score, 4),
            },
            image_results=image_results,
            artifacts=artifacts,
            warnings=warnings,
            provenance={},
        )
