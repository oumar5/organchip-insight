from pathlib import Path
from typing import Protocol

from app.config import get_settings
from app.ml.pipeline import AdaptiveSegmentationAnalyzer, PipelineOutput
from app.ml.quality_classifier import load_quality_analyzer
from app.ml.registry import (
    ADAPTIVE_SEGMENTATION_ENGINE,
    EXPERIMENTAL_QUALITY_ENGINE,
    REGISTERED_ENGINES,
)
from app.schemas import AnalysisEngine


class InferenceAnalyzer(Protocol):
    version: str
    engine: AnalysisEngine

    def analyze(
        self,
        image_paths: list[Path],
        artifact_dir: Path,
        artifact_url_prefix: str,
    ) -> PipelineOutput: ...


ANALYZERS_BY_ENGINE_ID: dict[str, InferenceAnalyzer] = {
    ADAPTIVE_SEGMENTATION_ENGINE.id: AdaptiveSegmentationAnalyzer(),
}
RUNTIME_UNAVAILABLE_REASONS: dict[str, str] = {}


def _load_optional_quality_runtime() -> None:
    try:
        analyzer = load_quality_analyzer(get_settings().quality_model_dir)
    except (FileNotFoundError, ImportError, OSError, RuntimeError, ValueError) as error:
        RUNTIME_UNAVAILABLE_REASONS[EXPERIMENTAL_QUALITY_ENGINE.id] = str(error)
        return
    ANALYZERS_BY_ENGINE_ID[EXPERIMENTAL_QUALITY_ENGINE.id] = analyzer


_load_optional_quality_runtime()


def _validate_runtime_registry_contract() -> None:
    registered_engine_ids = [engine.id for engine in REGISTERED_ENGINES]
    registered_engines_by_id = {engine.id: engine for engine in REGISTERED_ENGINES}
    registered_ids = set(registered_engine_ids)
    available_ids = {
        engine.id for engine in REGISTERED_ENGINES if engine.status == "available"
    }
    runtime_ids = set(ANALYZERS_BY_ENGINE_ID)
    duplicate_registered_ids = {
        engine_id
        for engine_id in registered_ids
        if registered_engine_ids.count(engine_id) > 1
    }
    missing_runtime_ids = available_ids - runtime_ids
    unregistered_runtime_ids = runtime_ids - registered_ids
    mismatched_runtime_ids = {
        engine_id
        for engine_id, analyzer in ANALYZERS_BY_ENGINE_ID.items()
        if (
            (registered := registered_engines_by_id.get(engine_id)) is None
            or registered.model_dump(exclude={"runnable", "unavailable_reason"})
            != analyzer.engine.model_dump(exclude={"runnable", "unavailable_reason"})
        )
    }
    if (
        duplicate_registered_ids
        or missing_runtime_ids
        or unregistered_runtime_ids
        or mismatched_runtime_ids
    ):
        raise RuntimeError(
            "Inference registry/runtime mapping is inconsistent: "
            f"duplicates={sorted(duplicate_registered_ids)}, "
            f"missing={sorted(missing_runtime_ids)}, "
            f"unregistered={sorted(unregistered_runtime_ids)}, "
            f"mismatched={sorted(mismatched_runtime_ids)}"
        )


def list_inference_engines() -> list[AnalysisEngine]:
    _validate_runtime_registry_contract()
    engines: list[AnalysisEngine] = []
    for engine in REGISTERED_ENGINES:
        analyzer = ANALYZERS_BY_ENGINE_ID.get(engine.id)
        if analyzer is not None:
            engines.append(analyzer.engine)
            continue
        reason = RUNTIME_UNAVAILABLE_REASONS.get(engine.id)
        engines.append(
            engine.model_copy(
                update={
                    "runnable": False,
                    "unavailable_reason": reason,
                }
            )
        )
    return engines


def get_available_runtime(engine_id: str) -> tuple[AnalysisEngine, InferenceAnalyzer]:
    _validate_runtime_registry_contract()
    analyzer = ANALYZERS_BY_ENGINE_ID.get(engine_id)
    engine = analyzer.engine if analyzer is not None else None
    if engine is None or not engine.runnable:
        raise ValueError(f"Inference engine '{engine_id}' is not available")
    return engine, analyzer


def inference_ready() -> bool:
    try:
        _validate_runtime_registry_contract()
    except RuntimeError:
        return False
    return any(
        engine.runnable and engine.id in ANALYZERS_BY_ENGINE_ID
        for engine in list_inference_engines()
    )
