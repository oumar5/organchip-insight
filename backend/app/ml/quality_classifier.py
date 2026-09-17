"""Fail-closed ONNX inference for the experimental OoC quality demonstrator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError

from app.ml.image_io import validate_image
from app.ml.pipeline import PipelineOutput
from app.ml.registry import EXPERIMENTAL_QUALITY_ENGINE
from app.schemas import AnalysisEngine, QualityImageAnalysis

MODEL_SHA256 = "c2f7339255a5e525f659d94a47aa8eb02d1ef60ed832597b343b542a4ed694a2"
PREPROCESSING_SHA256 = "fe8e18d8bc76a0ed06a884ec5ff9936fe6a0e59b1dbc44abaf7c027e61d0c3bc"
LABELS_SHA256 = "89e2fa4c560898d5c72c8efc80beb1b0d016b3e8d3dce7bdc7b30a23ce4b03cd"
INPUT_SIZE = 448
INPUT_NAME = "images"
OUTPUT_NAME = "logits"
IMAGENET_MEAN = np.asarray((0.485, 0.456, 0.406), dtype=np.float32)
IMAGENET_STD = np.asarray((0.229, 0.224, 0.225), dtype=np.float32)


@dataclass(frozen=True, slots=True)
class QualityModelBundle:
    model_path: Path
    model_sha256: str = MODEL_SHA256
    preprocessing_sha256: str = PREPROCESSING_SHA256
    labels_sha256: str = LABELS_SHA256

    @property
    def provenance(self) -> dict[str, str]:
        return {
            "model_sha256": self.model_sha256,
            "preprocessing_sha256": self.preprocessing_sha256,
            "labels_sha256": self.labels_sha256,
            "output_semantics": "raw-softmax-positive-class-good-uncalibrated",
            "selection_scope": "campaign-v2-validation-only",
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Invalid JSON object: {path.name}")
    return value


def verify_quality_model_bundle(model_dir: Path) -> QualityModelBundle:
    """Verify the three frozen artifacts before importing ONNX Runtime."""
    model_dir = model_dir.resolve()
    paths = {
        "model": model_dir / "model.onnx",
        "preprocessing": model_dir / "preprocessing.json",
        "labels": model_dir / "labels.json",
    }
    missing = [path.name for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Bundle CNN incomplet : {', '.join(sorted(missing))}")

    expected = {
        "model": MODEL_SHA256,
        "preprocessing": PREPROCESSING_SHA256,
        "labels": LABELS_SHA256,
    }
    for name, path in paths.items():
        if _sha256(path) != expected[name]:
            raise ValueError(f"Empreinte SHA-256 inattendue pour {path.name}")

    preprocessing = _load_json(paths["preprocessing"])
    required_preprocessing = {
        "schema_version": 1,
        "color_mode": "grayscale_rgb",
        "input_name": INPUT_NAME,
        "input_size": INPUT_SIZE,
        "layout": "NCHW",
        "dtype": "float32",
        "resize": "preserve aspect ratio and pad to square",
        "pad_value": 0,
    }
    if any(preprocessing.get(key) != value for key, value in required_preprocessing.items()):
        raise ValueError("Le contrat de prétraitement CNN ne correspond pas au run autorisé")
    try:
        mean = np.asarray(preprocessing.get("mean"), dtype=np.float64)
        std = np.asarray(preprocessing.get("std"), dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError("La normalisation CNN est invalide") from error
    if (
        mean.shape != (3,)
        or std.shape != (3,)
        or not np.allclose(mean, IMAGENET_MEAN, atol=1e-7, rtol=0.0)
        or not np.allclose(std, IMAGENET_STD, atol=1e-7, rtol=0.0)
    ):
        raise ValueError("La normalisation CNN ne correspond pas au run autorisé")

    labels = _load_json(paths["labels"])
    if (
        labels.get("schema_version") != 1
        or labels.get("class_to_index") != {"bad": 0, "good": 1}
        or labels.get("positive_class") != "good"
        or labels.get("output_name") != OUTPUT_NAME
        or labels.get("threshold_selected_on") != "validation"
    ):
        raise ValueError("Le contrat de sortie CNN ne correspond pas au run autorisé")

    return QualityModelBundle(model_path=paths["model"])


def _source_acquisition_mode(source: Image.Image) -> str:
    if source.mode == "L":
        return "L"
    if source.mode == "RGB":
        return "RGB"
    return "outside-training-domain"


def _preprocess(source: Image.Image) -> np.ndarray:
    grayscale_rgb = source.convert("L").convert("RGB")
    width, height = grayscale_rgb.size
    scale = min(INPUT_SIZE / width, INPUT_SIZE / height)
    resized_width = min(INPUT_SIZE, max(1, round(width * scale)))
    resized_height = min(INPUT_SIZE, max(1, round(height * scale)))
    resized = grayscale_rgb.resize(
        (resized_width, resized_height),
        resample=Image.Resampling.BILINEAR,
    )
    canvas = Image.new("RGB", (INPUT_SIZE, INPUT_SIZE), color=(0, 0, 0))
    offset = ((INPUT_SIZE - resized_width) // 2, (INPUT_SIZE - resized_height) // 2)
    canvas.paste(resized, offset)
    array = np.asarray(canvas, dtype=np.float32) / 255.0
    array = (array - IMAGENET_MEAN) / IMAGENET_STD
    return np.transpose(array, (2, 0, 1))[None, ...].astype(np.float32, copy=False)


def _probability_good(logits: Any) -> float:
    values = np.asarray(logits, dtype=np.float64)
    if values.shape != (1, 2) or not np.isfinite(values).all():
        raise ValueError(f"Sortie ONNX inattendue : forme {values.shape}")
    shifted = values[0] - np.max(values[0])
    probabilities = np.exp(shifted) / np.exp(shifted).sum()
    return float(probabilities[1])


class ExperimentalQualityAnalyzer:
    """Expose a raw validation-selected score while always abstaining from a decision."""

    version = "ooc-quality-cnn-campaign-v2-gray448-onnx-1"

    def __init__(
        self,
        *,
        bundle: QualityModelBundle,
        session: Any,
        engine: AnalysisEngine,
    ) -> None:
        self.bundle = bundle
        self.session = session
        self.engine = engine

    def analyze(
        self,
        image_paths: list[Path],
        artifact_dir: Path,
        artifact_url_prefix: str,
    ) -> PipelineOutput:
        del artifact_dir, artifact_url_prefix
        image_results: list[QualityImageAnalysis] = []
        warnings = [
            "Démonstrateur expérimental : aucune décision automatique bon/mauvais n'est produite.",
            "Le softmax affiché est brut, non calibré et ne mesure pas une qualité biologique.",
            "Chaque image reste systématiquement « À vérifier ».",
        ]
        scored = 0
        outside_domain = 0

        for image_path in image_paths:
            try:
                with Image.open(image_path) as source:
                    validate_image(source)
                    acquisition_mode = _source_acquisition_mode(source)
                    if acquisition_mode == "outside-training-domain":
                        outside_domain += 1
                        image_results.append(
                            QualityImageAnalysis(
                                filename=image_path.name,
                                source_acquisition_mode="outside-training-domain",
                                probability_good_raw=None,
                                interpretation="outside-training-domain",
                            )
                        )
                        continue
                    tensor = _preprocess(source)
                logits = self.session.run([OUTPUT_NAME], {INPUT_NAME: tensor})[0]
                probability = _probability_good(logits)
            except (
                OSError,
                ValueError,
                Image.DecompressionBombError,
                UnidentifiedImageError,
            ) as error:
                warnings.append(f"Image non évaluée {image_path.name} : {error}")
                continue

            scored += 1
            image_results.append(
                QualityImageAnalysis(
                    filename=image_path.name,
                    source_acquisition_mode=acquisition_mode,
                    probability_good_raw=round(probability, 6),
                    interpretation="review-required",
                )
            )

        if not image_results:
            raise ValueError("Aucune image lisible n'est disponible pour le démonstrateur CNN")

        if outside_domain:
            warnings.append(
                f"{outside_domain} image(s) hors domaine L/RGB : aucun softmax calculé."
            )
        return PipelineOutput(
            metrics={
                "images_with_raw_score": float(scored),
                "images_outside_training_domain": float(outside_domain),
            },
            image_results=image_results,
            artifacts=[],
            warnings=warnings,
            provenance=self.bundle.provenance,
        )


def load_quality_analyzer(model_dir: Path) -> ExperimentalQualityAnalyzer:
    bundle = verify_quality_model_bundle(model_dir)
    try:
        import onnxruntime as ort
    except ImportError as error:
        raise RuntimeError("ONNX Runtime n'est pas installé") from error

    session = ort.InferenceSession(
        str(bundle.model_path),
        providers=["CPUExecutionProvider"],
    )
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if len(inputs) != 1 or inputs[0].name != INPUT_NAME:
        raise ValueError("Entrée ONNX incompatible avec le contrat autorisé")
    if len(outputs) != 1 or outputs[0].name != OUTPUT_NAME:
        raise ValueError("Sortie ONNX incompatible avec le contrat autorisé")

    runnable_engine = EXPERIMENTAL_QUALITY_ENGINE.model_copy(
        update={"runnable": True, "unavailable_reason": None}
    )
    return ExperimentalQualityAnalyzer(
        bundle=bundle,
        session=session,
        engine=runnable_engine,
    )
