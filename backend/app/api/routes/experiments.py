from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.ml.runtime import get_available_runtime
from app.repository import repository
from app.schemas import AnalysisResult, Experiment, ExperimentCreate, UploadSummary

router = APIRouter()
settings = get_settings()

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


def _experiment_artifact_dir(experiment_id: UUID) -> Path:
    artifact_dir = settings.data_dir / "experiments" / str(experiment_id) / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def _write_upload(uploaded_file: UploadFile, destination: Path) -> bool:
    total_size = 0
    try:
        with destination.open("wb") as output:
            while chunk := uploaded_file.file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > settings.max_upload_bytes:
                    return False
                output.write(chunk)
        with Image.open(destination) as image:
            image.verify()
    except (OSError, UnidentifiedImageError):
        return False
    finally:
        uploaded_file.file.close()
    return True


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

        destination = image_dir / f"{uuid4().hex[:12]}-{safe_name}"
        if _write_upload(uploaded_file, destination):
            accepted.append(safe_name)
        else:
            destination.unlink(missing_ok=True)
            rejected.append(safe_name)

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
def analyze_experiment(
    experiment_id: UUID,
    engine_id: Annotated[str, Query()] = "adaptive-segmentation-v1",
) -> AnalysisResult:
    experiment = _get_experiment_or_404(experiment_id)
    if experiment.image_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload at least one image before analysis",
        )

    try:
        engine, analyzer = get_available_runtime(engine_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    image_dir = _experiment_image_dir(experiment_id)
    image_paths = [
        path for path in sorted(image_dir.iterdir()) if path.suffix.lower() in ALLOWED_SUFFIXES
    ]
    repository.update_status(experiment_id, "analyzing")

    try:
        output = analyzer.analyze(
            image_paths,
            artifact_dir=_experiment_artifact_dir(experiment_id),
            artifact_url_prefix=f"{settings.api_v1_prefix}/experiments/{experiment_id}/artifacts",
        )
    except ValueError as error:
        repository.update_status(experiment_id, "failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    result = AnalysisResult(
        experiment_id=experiment_id,
        analysis_version=analyzer.version,
        engine=engine,
        image_count=len(output.image_results),
        metrics=output.metrics,
        image_results=output.image_results,
        artifacts=output.artifacts,
        warnings=output.warnings,
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


@router.get("/{experiment_id}/artifacts/{artifact_name}", response_class=FileResponse)
def get_artifact(experiment_id: UUID, artifact_name: str) -> FileResponse:
    _get_experiment_or_404(experiment_id)
    if Path(artifact_name).name != artifact_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact name")
    artifact_path = _experiment_artifact_dir(experiment_id) / artifact_name
    if not artifact_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return FileResponse(artifact_path, media_type="image/png", filename=artifact_name)
