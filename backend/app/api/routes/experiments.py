import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.ml.pipeline import BaselineImageAnalyzer
from app.repository import repository
from app.schemas import AnalysisResult, Experiment, ExperimentCreate, UploadSummary

router = APIRouter()
settings = get_settings()
analyzer = BaselineImageAnalyzer()

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _get_experiment_or_404(experiment_id: UUID) -> Experiment:
    experiment = repository.get(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment


def _experiment_image_dir(experiment_id: UUID) -> Path:
    image_dir = settings.data_dir / "experiments" / str(experiment_id) / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    return image_dir


@router.post("", response_model=Experiment, status_code=status.HTTP_201_CREATED)
def create_experiment(payload: ExperimentCreate) -> Experiment:
    return repository.create(payload)


@router.get("", response_model=list[Experiment])
def list_experiments() -> list[Experiment]:
    return repository.list()


@router.get("/{experiment_id}", response_model=Experiment)
def get_experiment(experiment_id: UUID) -> Experiment:
    return _get_experiment_or_404(experiment_id)


@router.post("/{experiment_id}/images", response_model=UploadSummary)
def upload_images(
    experiment_id: UUID,
    files: Annotated[list[UploadFile], File(...)],
) -> UploadSummary:
    _get_experiment_or_404(experiment_id)
    image_dir = _experiment_image_dir(experiment_id)
    accepted: list[str] = []
    rejected: list[str] = []

    for uploaded_file in files:
        safe_name = Path(uploaded_file.filename or "unnamed").name
        if Path(safe_name).suffix.lower() not in ALLOWED_SUFFIXES:
            rejected.append(safe_name)
            continue

        destination = image_dir / safe_name
        with destination.open("wb") as output:
            shutil.copyfileobj(uploaded_file.file, output)
        accepted.append(safe_name)

    total_images = len(
        [path for path in image_dir.iterdir() if path.suffix.lower() in ALLOWED_SUFFIXES]
    )
    repository.update_image_count(experiment_id, total_images)
    return UploadSummary(
        experiment_id=experiment_id,
        accepted_files=accepted,
        rejected_files=rejected,
        total_images=total_images,
    )


@router.post("/{experiment_id}/analyze", response_model=AnalysisResult)
def analyze_experiment(experiment_id: UUID) -> AnalysisResult:
    experiment = _get_experiment_or_404(experiment_id)
    if experiment.image_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload at least one image before analysis",
        )

    image_dir = _experiment_image_dir(experiment_id)
    image_paths = [
        path for path in sorted(image_dir.iterdir()) if path.suffix.lower() in ALLOWED_SUFFIXES
    ]
    repository.update_status(experiment_id, "analyzing")

    try:
        metrics, warnings = analyzer.analyze(image_paths)
    except ValueError as error:
        repository.update_status(experiment_id, "failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    result = AnalysisResult(
        experiment_id=experiment_id,
        analysis_version=analyzer.version,
        image_count=len(image_paths),
        metrics=metrics,
        warnings=warnings,
    )
    repository.save_result(result)
    repository.update_status(experiment_id, "complete")
    return result


@router.get("/{experiment_id}/results", response_model=AnalysisResult)
def get_results(experiment_id: UUID) -> AnalysisResult:
    _get_experiment_or_404(experiment_id)
    result = repository.get_result(experiment_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Results not found")
    return result
