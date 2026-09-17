from typing import Literal

from app.schemas import AnalysisEngine

Locale = Literal["fr", "en"]


def resolve_locale(accept_language: str | None) -> Locale:
    if not accept_language:
        return "fr"
    first = accept_language.split(",", 1)[0].strip().lower()
    return "en" if first.startswith("en") else "fr"


EXACT_ENGLISH: dict[str, str] = {
    "Expérience introuvable": "Experiment not found",
    "Une analyse est déjà en cours pour cette expérience.": (
        "An analysis is already running for this experiment."
    ),
    "Nom d’image invalide": "Invalid image name",
    "Image introuvable": "Image not found",
    "Importez au moins une image avant l’analyse": (
        "Upload at least one image before analysis"
    ),
    "Une analyse est déjà en cours.": "An analysis is already running.",
    "L’analyse a échoué. Les images importées sont conservées ; vous pouvez réessayer.": (
        "Analysis failed. Uploaded images were kept; you can try again."
    ),
    "Aucun résultat terminé pour les images actuelles": (
        "No completed result for the current images"
    ),
    "Résultat absent": "Result not found",
    "Nom d’artefact invalide": "Invalid artifact name",
    "Artefact introuvable": "Artifact not found",
    "Extension non prise en charge.": "Unsupported file extension.",
    "Image illisible, endommagée ou dimensions non prises en charge.": (
        "Unreadable or damaged image, or unsupported dimensions."
    ),
}


def translate_text(value: str, locale: Locale) -> str:
    if locale == "fr":
        return value
    exact = EXACT_ENGLISH.get(value)
    if exact:
        return exact
    if value.startswith("Aperçu impossible :"):
        return value.replace("Aperçu impossible :", "Preview failed:", 1)
    if value.startswith("Fichier trop volumineux :"):
        return value.replace("Fichier trop volumineux :", "File too large:", 1).replace(
            "Mio maximum", "MiB maximum"
        )
    return value


ENGINE_ENGLISH: dict[str, dict[str, object]] = {
    "adaptive-segmentation-v1": {
        "name": "Adaptive segmentation v1",
        "description": (
            "Local segmentation using Otsu thresholding, morphology, and connected "
            "components. It runs immediately without weights or training."
        ),
        "limitations": [
            "Exploratory result not validated for biological or clinical decisions.",
            "Separation of touching objects remains limited.",
            "Foreground is estimated automatically and must be reviewed visually.",
        ],
    },
    "ooc-quality-cnn-campaign-v2-gray448": {
        "name": "Campaign-v2 quality CNN — demonstrator",
        "description": (
            "ONNX demonstrator from run B selected on validation. It exposes the raw "
            "softmax only and requires human review for every image."
        ),
        "limitations": [
            "No automatic good/bad decision: every output is marked ‘Review required’.",
            "The raw softmax is neither calibrated nor a probability of biological quality.",
            "The RGB signal is modest and not distinguishable from validation-selection effects.",
            "The observed domain is limited to source acquisition modes L and RGB.",
        ],
    },
    "micro-sam-pretrained": {
        "name": "Pretrained µSAM",
        "description": (
            "Microscopy-focused engine integrated in an isolated benchmark environment."
        ),
        "limitations": [
            "Not enabled in the product path after the non-promotion decision.",
            "The BBBC038 benchmark fails two of the three preregistered criteria.",
            "Local CPU measurement: 36.7 s/image on average and 8.9 GB peak memory.",
            "External nuclear validation does not validate counting on OoC images.",
        ],
    },
    "cellpose-pretrained": {
        "name": "Pretrained Cellpose",
        "description": "Candidate general-purpose cell and nucleus segmentation engine.",
        "limitations": [
            "Disabled until weight-license compatibility is approved.",
            "Weight downloads and additional compute resources are required.",
        ],
    },
}


def localize_engine(engine: AnalysisEngine, locale: Locale) -> AnalysisEngine:
    if locale == "fr":
        return engine
    translation = ENGINE_ENGLISH.get(engine.id)
    if translation is None:
        return engine
    update = dict(translation)
    if engine.unavailable_reason:
        update["unavailable_reason"] = translate_text(engine.unavailable_reason, locale)
    return engine.model_copy(update=update)
