import csv
import hashlib
import io
import json
import logging
from pathlib import Path
from threading import RLock
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.ml.image_io import validate_image
from app.ml.runtime import get_available_runtime
from app.repository import repository
from app.schemas import AnalysisResult, Experiment, ExperimentCreate, UploadSummary

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)
# Serialize uploads and analysis starts; inference runs outside this lock.
# The shipped deployment uses one API process. Multi-worker execution needs a job queue.
mutation_lock = RLock()

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


def _write_upload(uploaded_file: UploadFile, destination: Path) -> str:
    total_size = 0
    digest = hashlib.sha256()
    try:
        with destination.open("wb") as output:
            while chunk := uploaded_file.file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > settings.max_upload_bytes:
                    raise ValueError(
                        f"Fichier trop volumineux : {settings.max_upload_mb} Mio maximum."
                    )
                output.write(chunk)
                digest.update(chunk)
        with Image.open(destination) as image:
            validate_image(image, settings.max_image_pixels)
    finally:
        uploaded_file.file.close()
    return digest.hexdigest()


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
    try:
        with mutation_lock:
            return _store_images(experiment_id, files)
    finally:
        for uploaded_file in files:
            uploaded_file.file.close()


def _store_images(experiment_id: UUID, files: list[UploadFile]) -> UploadSummary:
    experiment = _get_experiment_or_404(experiment_id)
    if experiment.status == "analyzing":
        raise HTTPException(
            status_code=409, detail="Une analyse est déjà en cours pour cette expérience."
        )
    image_dir = _experiment_image_dir(experiment_id)
    accepted: list[str] = []
    rejected: list[str] = []
    duplicates: list[str] = []
    reasons: dict[str, str] = {}
    known_hashes: set[str] = set()
    for path in image_dir.iterdir():
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES:
            with path.open("rb") as source:
                known_hashes.add(hashlib.file_digest(source, "sha256").hexdigest())

    for uploaded_file in files:
        safe_name = Path(uploaded_file.filename or "unnamed").name
        if Path(safe_name).suffix.lower() not in ALLOWED_SUFFIXES:
            rejected.append(safe_name)
            reasons[safe_name] = "Extension non prise en charge."
            continue

        # Bound the UTF-8 filename, keeping the extension and uniqueness prefix.
        stem = Path(safe_name).stem.encode("utf-8")[:160].decode("utf-8", errors="ignore")
        stored_name = f"{uuid4().hex[:12]}-{stem}{Path(safe_name).suffix.lower()}"
        destination = image_dir / stored_name
        try:
            digest = _write_upload(uploaded_file, destination)
            if digest in known_hashes:
                destination.unlink(missing_ok=True)
                duplicates.append(safe_name)
            else:
                known_hashes.add(digest)
                accepted.append(safe_name)
        except (OSError, ValueError, Image.DecompressionBombError, UnidentifiedImageError) as error:
            destination.unlink(missing_ok=True)
            rejected.append(safe_name)
            reasons[safe_name] = (
                str(error)
                if isinstance(error, ValueError)
                else "Image illisible, endommagée ou dimensions non prises en charge."
            )

    total_images = len(
        [path for path in image_dir.iterdir() if path.suffix.lower() in ALLOWED_SUFFIXES]
    )
    if accepted:
        repository.update_image_count(experiment_id, total_images)
    return UploadSummary(
        experiment_id=experiment_id,
        accepted_files=accepted,
        rejected_files=rejected,
        total_images=total_images,
        duplicate_files=duplicates,
        rejection_reasons=reasons,
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
    with mutation_lock:
        if not repository.start_analysis(experiment_id):
            raise HTTPException(status_code=409, detail="Une analyse est déjà en cours.")

    try:
        image_paths = [
            path for path in sorted(image_dir.iterdir()) if path.suffix.lower() in ALLOWED_SUFFIXES
        ]
        output = analyzer.analyze(
            image_paths,
            artifact_dir=_experiment_artifact_dir(experiment_id),
            artifact_url_prefix=f"{settings.api_v1_prefix}/experiments/{experiment_id}/artifacts",
        )
        result = AnalysisResult(
            experiment_id=experiment_id,
            analysis_version=analyzer.version,
            task=engine.task,
            engine=engine,
            image_count=len(output.image_results),
            metrics=output.metrics,
            image_results=output.image_results,
            artifacts=output.artifacts,
            warnings=output.warnings,
            provenance=output.provenance,
        )
        repository.save_result(result)
        repository.update_status(experiment_id, "complete")
    except ValueError as error:
        repository.update_status(experiment_id, "failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except Exception as error:
        repository.update_status(experiment_id, "failed")
        logger.exception("Analysis failed for experiment %s", experiment_id)
        raise HTTPException(
            status_code=500,
            detail=(
                "L’analyse a échoué. Les images importées sont conservées ; vous pouvez réessayer."
            ),
        ) from error
    return result


@router.get("/{experiment_id}/results", response_model=AnalysisResult)
def get_results(experiment_id: UUID) -> AnalysisResult:
    return _result_or_404(experiment_id)


def _result_or_404(experiment_id: UUID) -> AnalysisResult:
    experiment = _get_experiment_or_404(experiment_id)
    if experiment.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun résultat terminé pour les images actuelles",
        )
    result = repository.get_result(experiment_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Résultat absent")
    return result


@router.get("/{experiment_id}/exports/results.json", response_class=Response)
def export_results_json(experiment_id: UUID) -> Response:
    result = _result_or_404(experiment_id)
    payload = json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)
    return Response(
        content=payload + "\n",
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="organchip-{experiment_id}-results.json"'
            )
        },
    )


@router.get("/{experiment_id}/exports/results.csv", response_class=Response)
def export_results_csv(experiment_id: UUID) -> Response:
    result = _result_or_404(experiment_id)
    rows = [item.model_dump(mode="json") for item in result.image_results]
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="organchip-{experiment_id}-image-results.csv"'
            )
        },
    )


@router.get("/{experiment_id}/artifacts/{artifact_name}", response_class=FileResponse)
def get_artifact(experiment_id: UUID, artifact_name: str) -> FileResponse:
    _get_experiment_or_404(experiment_id)
    if Path(artifact_name).name != artifact_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact name")
    artifact_path = _experiment_artifact_dir(experiment_id) / artifact_name
    if not artifact_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return FileResponse(artifact_path, media_type="image/png", filename=artifact_name)
