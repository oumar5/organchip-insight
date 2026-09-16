from fastapi import APIRouter

from app.config import get_settings
from app.ml.runtime import list_inference_engines
from app.schemas import AnalysisEngine

router = APIRouter()


@router.get("/upload-limits")
def get_upload_limits() -> dict[str, int]:
    settings = get_settings()
    return {
        "max_upload_bytes": settings.max_upload_bytes,
        "max_image_pixels": settings.max_image_pixels,
    }


@router.get("/engines", response_model=list[AnalysisEngine])
def get_inference_engines() -> list[AnalysisEngine]:
    return list_inference_engines()
