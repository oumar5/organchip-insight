from pathlib import Path
from typing import Protocol

from app.ml.pipeline import AdaptiveSegmentationAnalyzer, PipelineOutput
from app.ml.registry import ADAPTIVE_SEGMENTATION_ENGINE, REGISTERED_ENGINES
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
        if registered_engines_by_id.get(engine_id) is not analyzer.engine
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
    return list(REGISTERED_ENGINES)


def get_available_runtime(engine_id: str) -> tuple[AnalysisEngine, InferenceAnalyzer]:
    _validate_runtime_registry_contract()
    engine = next(
        (candidate for candidate in REGISTERED_ENGINES if candidate.id == engine_id),
        None,
    )
    analyzer = ANALYZERS_BY_ENGINE_ID.get(engine_id)
    if engine is None or engine.status != "available" or analyzer is None:
        raise ValueError(f"Inference engine '{engine_id}' is not available")
    return engine, analyzer


def inference_ready() -> bool:
    try:
        _validate_runtime_registry_contract()
    except RuntimeError:
        return False
    return any(
        engine.status == "available" and engine.id in ANALYZERS_BY_ENGINE_ID
        for engine in REGISTERED_ENGINES
    )
