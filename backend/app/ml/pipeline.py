from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError


class BaselineImageAnalyzer:
    """Transparent reference analysis used before model integration.

    These measurements are genuine image statistics, not simulated phenotype
    predictions. They provide a tested data path and a baseline for quality
    control while the competition dataset and trained models are being selected.
    """

    version = "image-qc-baseline-0.1.0"

    def analyze(self, image_paths: list[Path]) -> tuple[dict[str, float], list[str]]:
        intensities: list[float] = []
        contrasts: list[float] = []
        warnings: list[str] = []

        for image_path in image_paths:
            try:
                with Image.open(image_path) as image:
                    grayscale = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
            except (OSError, UnidentifiedImageError) as error:
                warnings.append(f"Unreadable image {image_path.name}: {error}")
                continue

            intensities.append(float(grayscale.mean()))
            contrasts.append(float(grayscale.std()))

        if not intensities:
            raise ValueError("No readable images are available for analysis")

        mean_intensity = float(np.mean(intensities))
        mean_contrast = float(np.mean(contrasts))
        quality_score = float(np.clip(mean_contrast / 0.20, 0.0, 1.0))

        if mean_intensity < 0.08:
            warnings.append("The image set appears strongly underexposed.")
        if mean_intensity > 0.92:
            warnings.append("The image set appears strongly overexposed.")
        if mean_contrast < 0.04:
            warnings.append("Low contrast may reduce segmentation reliability.")

        return (
            {
                "mean_intensity": round(mean_intensity, 4),
                "mean_contrast": round(mean_contrast, 4),
                "quality_score": round(quality_score, 4),
            },
            warnings,
        )

